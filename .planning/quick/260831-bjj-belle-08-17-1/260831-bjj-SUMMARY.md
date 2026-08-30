---
phase: quick-260831-bjj-belle-08-17-1
plan: 01
subsystem: ml-analysis
tags: [numpy, posture-axes, coach-writer, cerebras, gemini, mode1]

requires:
  - phase: 23-eval-frame-specific
    provides: coach_context visionFault 주입 선례 + reference_angles_for_veto 배선 자리
  - phase: quick-260808-r82
    provides: side_match joints3d sentinel 규약 (0,0,0 = NaN 저장분) + 관측 블록 graceful 규율
provides:
  - features.py 자세 축 순수 함수 3종 (head_spine_alignment_series / torso_uprightness_series / posture_axis_summary) + POSTURE_DELTA_SIGNIFICANT_DEG=5.0
  - pipeline mode1 배선 — _reference_keypoints_coco17(sentinel 복원+재배열) + _compute_posture_axes + coach_context postureAxes 키
  - 양 coach writer(Cerebras+Gemini) 인과형 한국어 렌더 — format_posture_axis_lines 단일 출처
  - 피터팬 실데이터 방향 검증 PASS 증거 (peterpan-axes-verdict.txt)
affects: [mode1-analysis, coach-writer, 34-analysis-generalization, discovery-eye-first]

tech-stack:
  added: []
  patterns:
    - "자세 축 = 기준-학생 델타만 제품 사용 (절대값은 촬영 규약 의존 — 양쪽 상쇄, 동작명 분기 0)"
    - "발화 판정 단일 출처: features.posture_axis_summary 산출값만 소비, 렌더는 format_posture_axis_lines 양 writer 공유"
    - "학생 열위 방향만 발화 (결함 코칭 목적 — uprightness delta>0 / headSpine delta<0)"

key-files:
  created:
    - backend/tests/test_posture_axes.py
    - .planning/quick/260831-bjj-belle-08-17-1/verify_peterpan_axes.py
    - .planning/quick/260831-bjj-belle-08-17-1/peterpan-axes-verdict.txt
  modified:
    - backend/shared/python/sunity_shared/analysis/features.py
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/analysis/coach_writer.py
    - backend/shared/python/sunity_shared/gemini/coach_writer_v2.py
    - backend/tests/test_coach_writer.py
    - backend/tests/gemini/test_coach_writer_v2.py

key-decisions:
  - "귀중점(코 아님)으로 머리 중심 근사 — 코는 돌출 말단이라 측면 고개 판정 왜곡"
  - "significant 임계 5.0° — RTMW jitter 계열(±2프레임 median 흡수 대상)과 같은 규모 아래는 잡음, 실측 재조정 여지 명기"
  - "median 요약 (max_split peak 논리와 반대) — 자세 축은 지속 품질 신호라 한 프레임 jitter 오염 차단"
  - "발화 방향 게이트 — 학생 우위(더 꼿꼿/더 1자)면 미발화: 교정 지시가 성립하지 않음"
  - "렌더 formatter 를 analysis.coach_writer 에 public(format_posture_axis_lines)으로 두고 gemini writer 가 import — 발화 로직 중복 0 (B3 정합)"

patterns-established:
  - "2D 입력 수용은 자세 축 2종만 (_posture_xyz z=0 패딩) — 기존 3채널 요구 함수 무접촉 (과잉 일반화 금지)"

requirements-completed: ["CONTINUE-2026-08-31 내일 첫 작업 #1 — belle 08-17 판독 축 구현"]

duration: 12min
completed: 2026-08-31
---

# Quick Task 260831-bjj: belle 08-17 판독 축 구현 Summary

**belle 08-17 판독 축 2종(상체 꼿꼿함·머리-척추 1자)을 COCO17 좌표 순수 함수로 구현하고 mode1 기준-학생 델타를 양 coach writer 프롬프트에 인과형 한국어로 조건부 주입 — 피터팬 실데이터 사전 박제 예측 PASS (ref 10.75° < user 20.59°, 기준이 더 꼿꼿)**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-30T23:27:12Z
- **Completed:** 2026-08-30T23:38:55Z (UTC; KST 2026-08-31)
- **Tasks:** 3/3
- **Files modified:** 9 (code 6 + planning 증거 3)

## Accomplishments

- **축 2종이 코드에 존재**: `head_spine_alignment_series`(골반중점-어깨중점-귀중점, 180°=1자), `torso_uprightness_series`(척추벡터 vs y-down up, 0°=수직 꼿꼿), `posture_axis_summary`(nanmedian, delta=student-reference, |delta|>=5.0 significant). 순수 numpy, NaN 전파, `_angle_deg` 재사용, (T,17,2|3|4) 수용. 동작명 분기 0 — grep 실측 확인(동작명은 스펙 인용 주석에만 존재, 실행 코드 분기 0건).
- **mode1 배선**: `_reference_keypoints_coco17` 이 ref doc flat joints3d 를 전-0 sentinel→NaN 복원 + KEYPOINT_NAMES 재배열로 (T,17,3) 복원, `_compute_posture_axes` 가 전체 try/except graceful 로 요약 dict 산출(threat T-quick-01 mitigate 적용). mode1 a_ref 확보 직후 산출, mode3 는 None 유지. 점수 경로 진입 0.
- **양 writer 조건부 렌더**: `format_posture_axis_lines` 단일 출처(Cerebras 소유, Gemini import — 발화 판정 중복 0). significant + 학생 열위 방향(uprightness delta>0 / headSpine delta<0)일 때만 인과형 지시("상체를 세워 꼿꼿하게 만들면 동작 전체 라인이 산다" / "고개를 들어 머리와 척추가 1자가 되게") + "N° 정도" 보조 수치. None/미발화 시 프롬프트 byte-불변 — 테스트로 증명.
- **피터팬 실데이터 방향 검증 PASS (사전 박제)**: 예측 부등식(ref uprightness median < user)을 실행 전 박제 → 실측 ref 10.75° / user 20.59°, delta +9.84° significant. belle 원문 "상체의 꼿꼿해짐"(기준이 더 꼿꼿) 방향 일치. headSpine 은 관측만(delta +5.98° = 학생이 더 1자 → 방향 게이트상 피터팬에서 미발화 — 정합. 그 축 정답지는 elbow 건). 증거 = `peterpan-axes-verdict.txt`.
- **무회귀**: 전체 4528 passed / 0 failed / 20 skipped (기준선 4496 + 신규 32). Firestore 스키마 변경 0.

## Task Commits

TDD 태스크라 test → feat 쌍 커밋:

1. **Task 1: 자세 축 순수 함수** — `7aed6ff7` (test RED) → `2cc49f91` (feat GREEN)
2. **Task 2: mode1 배선 + 양 writer 렌더** — `848de873` (test RED) → `c5b2fe6c` (feat GREEN)
3. **Task 3: 피터팬 방향 검증** — 코드 변경 0 (증거 파일은 .planning — 오케스트레이터 docs 커밋 대상)

## Files Created/Modified

- `backend/shared/python/sunity_shared/analysis/features.py` — 축 함수 3종 + `_posture_xyz` + `POSTURE_DELTA_SIGNIFICANT_DEG`
- `backend/functions/pipeline/app.py` — `_reference_keypoints_coco17` / `_compute_posture_axes` / `_build_coach_context(posture_axes=)` / _process mode1 배선
- `backend/shared/python/sunity_shared/analysis/coach_writer.py` — `format_posture_axis_lines` + `_build_prompt(posture_axes=)` + write 전달
- `backend/shared/python/sunity_shared/gemini/coach_writer_v2.py` — 같은 formatter import 렌더
- `backend/tests/test_posture_axes.py` — 축 방향/입력 수용/NaN/요약 + 배선 테스트 28건
- `backend/tests/test_coach_writer.py`, `backend/tests/gemini/test_coach_writer_v2.py` — significant 렌더 / byte-불변 / 방향 게이트
- `.planning/quick/260831-bjj-belle-08-17-1/verify_peterpan_axes.py` + `peterpan-axes-verdict.txt` — 사전 박제 검증 스크립트 + 증거

## Decisions Made

frontmatter key-decisions 참조. 전부 plan 이 지정한 근거를 따랐고 신규 재량 결정 없음.

## Deviations from Plan

None - plan executed exactly as written.

(참고: Gemini 렌더의 "발화 로직 두 곳 중복 금지" 요구를 formatter 공유 import 로 구현 — plan 의 "판정 부호·significant 는 posture_axis_summary 산출값만 소비" 지시의 가장 직접적인 이행이며 구조 변경 아님. analysis.coach_writer 는 stdlib+phrasebook 만 의존해 순환 import 0.)

## Known Stubs

None — 축 계산부터 프롬프트 렌더까지 전 구간 배선 완료, 실데이터 검증까지 통과. 하드코딩 빈 값/placeholder 0.

## Threat Flags

없음 — 신규 네트워크 endpoint/auth 경로/스키마 변경 0. threat register 의 T-quick-01(mitigate) 은 `_compute_posture_axes` 전체 try/except graceful 로 적용, T-quick-SC(accept) 는 신규 패키지 설치 0 으로 성립.

## Issues Encountered

None.

## Next Phase Readiness

- mode1 분석이 belle 이 실제로 보는 축을 코칭에 반영한다 — 다음 Pod 기동 시 실제 mode1 E2E 에서 프롬프트 주입분이 코칭 문장으로 나오는지 실기 확인 가치 있음 (Pod 필요, 이번 스코프 밖).
- headSpine 축의 방향 정답지는 elbow r02cand03 건 — elbow 계열 align 데이터가 생기면 같은 사전 박제 방식으로 검증 가능.
- significant 임계 5.0° 는 구조 유도값 — 실데이터 델타 분포가 쌓이면 재조정 여지 (fixture curve-fit 금지 규율 유지).
- CONTINUE-2026-08-31 의 나머지 착수 항목(꼬리 5건 삼진 분류)은 본 태스크 스코프 밖.

## Self-Check

- [x] backend/tests/test_posture_axes.py 존재
- [x] features.py 에 `def head_spine_alignment_series` 존재
- [x] app.py 에 `postureAxes` 존재
- [x] peterpan-axes-verdict.txt 존재 (사전 박제 예측 + PASS)
- [x] 커밋 7aed6ff7 / 2cc49f91 / 848de873 / c5b2fe6c 존재
- [x] 전체 테스트 4528 passed / 0 failed

---
*Phase: quick-260831-bjj-belle-08-17-1*
*Completed: 2026-08-31*
