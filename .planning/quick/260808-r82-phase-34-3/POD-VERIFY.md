# Phase 34 수술 ① — belle-FAIL 측 align_quality Pod 검증 절차 (명시 이월)

quick-260808-r82 Task 3 의 캘리브레이션은 **PASS 측(승인 5편)만 로컬 완료**했다.
belle-FAIL 측(doc `127a2a90c1d74c62ad61270eb3fe5625`, 08-08 pdshape 반려)의
align_quality 판정은 이 문서의 절차로 **다음 Pod 세션에서** 실행한다.

## 왜 로컬 불가인가 (CPU 대체 금지)

belle 08-08 영상의 render-side align(`compare_align.build_align`)은 rtmlib RTMW
**GPU 재추출**로만 생산된다. CPU align 은 GPU align 과 다르다 — 실측: 리그 E 판정이
CPU 13% vs GPU 28% 로 갈린 이력(quick-260808-jix 라운드). CPU 로 재현해 FAIL/PASS 를
단정하면 판정 대상이 다른 산출물이 된다. **CPU 로 갈음하지 말 것.**

## 절차

1. **Pod 부트스트랩** — memory 절차(`current-pod-oibw6614x0rzay.md` 재생성 절,
   GPU 모델 명시 요청 — 4090 우선 EU-RO-1, `pod-request-include-gpu-model`).
   기존 Network Volume 재사용. 부팅 후 리포 pull (HEAD 에 quick-260808-r82 포함 확인:
   `git log --oneline | grep "수술 ①"`).
2. **입력 회수** — Firestore `users/csKWYvI3WCPYPysNQ9KkWecaUvq1/analyses/127a2a90c1d74c62ad61270eb3fe5625`
   에서 `videoKey`(uploads/{uid}/… — belle 업로드 원본)와 `referenceMotionId` 를 읽고,
   S3 `sunity-motion-pilot-videos` 에서 user 영상 + `reference/{refId}.mp4` 다운로드.
   records = 같은 doc `result.deductionBreakdown.records`.
3. **GPU build_align 실행** —
   ```
   RTMW_DEVICE=cuda python3 - <<'PY'
   import json, sys
   sys.path.insert(0, "backend/shared/python")
   from pathlib import Path
   from sunity_shared.analysis import compare_align
   records = json.load(open("belle_doc.json"))["result"]["deductionBreakdown"]["records"]
   align = compare_align.build_align(
       Path("user.mp4"), Path("ref.mp4"), records, Path("/workspace/p34_verify"))
   json.dump(align, open("/workspace/p34_verify/align.json", "w"))
   ok, lines = compare_align.align_quality(align)
   print("\n".join(lines)); print("VERDICT:", "PASS" if ok else "FAIL")
   PY
   ```
4. **기대 = FAIL.** 반려 실측 근거: records 2건이 이탈 국면(atVideoSec 17.56/17.78s)
   + 짝 ref 가 종점 아티팩트(16.4~16.6/16s) + 파이프라인 low_global_confidence.
   기대대로 FAIL 이면 게이트가 belle 반려 케이스를 정확히 걸러낸 것 — 결과 라인
   (지표=값 임계=값)을 이 파일에 추기하고 종결.
5. **PASS 로 나오면** 임계 재캘리브레이션 라운드를 연다 — 단 **승인 5편 전건 PASS
   유지 조건 하에서만** 조정(`backend/tests/phase35/test_align_quality_calibration.py`
   가 릴리스 게이트). 조정 근거·새 실측값을 `compare_align.py` 상수 주석과 이 파일에
   추기. fixture 1건에 임계를 맞추는 curve-fit 금지 — 실패 축(커버리지/거리)의
   구조 원인을 먼저 확인한다.
6. **회계** — 같은 Pod 에서 belle doc 재분석(신 파이프라인 — 수술 ②③ 포함)을 돌리면
   `phase34_rescore_harness.py` 회계 표와 실 doc records 이동을 대조할 수 있다
   (측정 순간이 이탈 국면 밖으로 나왔는지 — 수술 ② 의 실지 검증).

## 참고 임계 (2026-08-08 승인 5편 캘리브레이션)

| 지표 | 임계 | 승인 최악 실측 | 마진 |
|---|---|---|---|
| 신뢰 커버리지 (user·ref 각각) | >= 0.88 | 0.9441 (pdshapefault ref) | 결측률 2.0배 |
| 자세거리 median | <= 6.3 | 3.125 (elbow) | 2.0배 |
| 자세거리 p85 | <= 11.0 | 5.490 (elbow) | 2.0배 |
