---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: 25
status: closed-substantively-done
closed: 2026-08-31
closed_by: quick/260831-c3l-6-summary (미실행 꼬리 삼진 분류)
basis: "belle 2026-08-30 두 목적 — Mode1 잘 분석되는가 / Mode3 발전 확인되는가"
---

# 01-25 SUMMARY (closure stub — 실행 없이 닫음)

## 원 플랜 목표

pipeline/app.py 의 NLF 참조를 RTMWPoseEngine + 선택된 3D path 로 atomic swap (NLF 참조 0, heavy import lazy, poleAxis 메타 보존) + RunPod server/setup/README 갱신.

## 처분

**실질 완료 (closed-substantively-done).** swap 의 실체(파이프라인이 RTMW 를 소비)는 이 플랜 밖 경로로 완료됐다 — pipeline/app.py 주석에 "Plan 25 atomic swap (2026-06-05): NlfPoseEstimator → _RTMWNlfCompat (RTMW 기반)" 이 박혀 있고 실제 추론 호출이 RTMW 싱글턴을 쓴다. 잔여는 표기 정리뿐이라 두 목적에 기여 없음.

## 실측 (2026-08-31, 이 스텁 작성 시 직접 확인)

```
$ grep -n '_RTMW_ENGINE\|RTMWNlfCompat' backend/functions/pipeline/app.py
222:# RTMW engine singleton. _POSE_ESTIMATOR (RTMWNlfCompat) 는 NLF interface 호환용
226:_RTMW_ENGINE = None  # type: ignore[var-annotated]
1262:class _RTMWNlfCompat:
1327:    Plan 25 atomic swap (2026-06-05): NlfPoseEstimator → _RTMWNlfCompat (RTMW 기반,
1330:    Plan 06-02 R3 fix: _RTMW_ENGINE singleton 추가 — _extract_video_analysis_inputs
1333:    global _FRAME_EXTRACTOR, _POSE_ESTIMATOR, _COACH_WRITER, _RTMW_ENGINE, _POLE_DETECTOR
1338:        _POSE_ESTIMATOR = _RTMWNlfCompat()
1339:    if _RTMW_ENGINE is None:
1341:        # _POSE_ESTIMATOR (RTMWNlfCompat) 의 _engine attribute 가 RTMWPoseEngine.
1342:        _RTMW_ENGINE = _POSE_ESTIMATOR._engine  # type: ignore[attr-defined]
1519:            pose_frames = _RTMW_ENGINE.estimate(frames, default_pole)

$ grep -c -i nlf backend/functions/pipeline/app.py
16
```

## 관측과 해석

- 관측: 파이프라인은 RTMW 싱글턴(`_RTMW_ENGINE`)으로 추론한다 (line 1519). NLF interface 호환 shim(`_RTMWNlfCompat`)이 유지되고 있다.
- 관측: 플랜 must_have "NLF 참조 0" 은 미충족 — 파일 내 nlf 언급 16건 (독스트링·주석·호환 shim 이름). swap 은 이 플랜의 "참조 0 + 테스트 9종" 규격이 아니라 2026-06-05 별도 경로(호환 shim 방식)로 이뤄졌다.
- 관측: 이 스텁은 플랜 Task 2 (RunPod requirements/setup/README 의 NLF 잔여 0) 와 Task 3 (belle Pod E2E checkpoint) 의 항목별 대조를 하지 않았다 — 사후 실측 기반 관측이지 완료 검증서가 아니다.
- 내 해석: 잔존 NLF 언급은 표기 문제이며 동작 문제 아님 — 실 추론 경로는 RTMW 이고, RTMW 운영은 이후 수개월의 실사용(예: 2026-06-15 reference 11개 RTMW 재처리 belle 승인)으로 실증돼 왔다.
