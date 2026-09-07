---
id: 260907-itk
slug: step-0
description: Step 0 관절 좌표 학습 필요 판정 — 사전 기준 박제 후 두 측정
date: 2026-09-07
status: in-progress
must_haves:
  truths:
    - 사전 기준이 측정보다 먼저 커밋된다
    - 판정은 교차표의 다섯 칸 중 하나로만 나온다
    - 명부 정정(8면 → 5면)은 눈에게 재질의 없이 메타데이터만 고친다
  artifacts:
    - .planning/quick/260907-itk-step-0/evidence/STEP0-PREREGISTRATION.md
    - .planning/quick/260907-itk-step-0/evidence/roster_corrected.json
    - .planning/quick/260907-itk-step-0/evidence/measure_b_vote.json
    - .planning/quick/260907-itk-step-0/evidence/measure_a_mediapipe.json
    - .planning/quick/260907-itk-step-0/evidence/STEP0-VERDICT.md
  key_links:
    - .planning/quick/260906-n2j-stage-1-advisory/evidence/panel_center_v2_live.json
    - .planning/quick/260906-n2j-stage-1-advisory/evidence/crop_logs_n2j.txt
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
---

# Step 0 — 관절 좌표 학습이 필요한가

belle 09-06 지시("그 학습 라인도 만드는게 좋겠네")에 대한 **착수 전 측정**.
학습 라인을 짓기 전에 두 가지를 재서, 학습이 아예 필요 없는 경로를 먼저 배제한다.

belle 09-07 확인: 좌표 라인은 눈 플라이휠과 달리 **라벨이 저절로 안 쌓인다**
(사람이 관절을 찍어야 한다). 그래서 이 두 측정은 "학습이 필요한가"인 동시에
**"라벨을 기계가 만들 수 있는가"** 를 묻는다.

## Task 1 — 명부 정정

- files: `evidence/roster_corrected.json`, `evidence/fix_roster.py`
- action: `panel_center_eye_measure_v2.py` 의 크롭로그 조회 실패를 고친 사본으로
  09-06 측정본을 재분류한다. **눈에게 다시 묻지 않는다** — `vertex_centered` 메타데이터만 복구.
- verify: 정정 집계가 ok 16 / not_center_anchored 15 / mismatch 5 이고,
  빠지는 3면이 크롭 로그에서 `vertex_centered=False` 로 확인된다.
- done: `roster_corrected.json` 커밋됨.

## Task 2 — 사전 기준 박제

- files: `evidence/STEP0-PREREGISTRATION.md`
- action: 임계·판정 규칙·교차표·사전 예측·한계를 적고 커밋한다.
- verify: 커밋 시각이 Task 3·4 산출물의 mtime 보다 앞선다.
- done: 커밋됨. **그 전에는 아무것도 측정하지 않는다.**

## Task 3 — 측정 B (다중 프레임 다수결, Firestore 전용)

- files: `evidence/measure_b_vote.py`, `evidence/measure_b_vote.json`
- action: 대상 5면 + 대조군 13면에 대해 이웃 표본 중앙값을 내고 저장 좌표와의 거리를 잰다.
  학생 걸음 ±2 / 기준 걸음 ±1 은 **하드코딩하지 않고 표본 구조를 검사해 정한다.**
- verify: 구조 검사(홀수 중점 여부)가 두 쪽에서 반대 결과를 낸다. 모델 재실행 0회.
- done: 면별 행이 JSON 으로 나온다.

## Task 4 — 측정 A (MediaPipe 대조)

- files: `evidence/measure_a_mediapipe.py`, `evidence/measure_a_mediapipe.json`
- action: 크롭 로그의 인덱스 원장으로 프레임을 뽑아 MediaPipe IMAGE 모드로 재고,
  픽셀에서 거리를 잰다. 대조군 13면 필수.
- verify: 대조군 DISAGREE 수가 기록된다(A 의 반증자).
- done: 면별 행이 JSON 으로 나온다.

## Task 5 — 판정

- files: `evidence/STEP0-VERDICT.md`
- action: 교차표의 한 칸으로 판정한다. 사전 예측과 실제 결과를 나란히 적는다.
- verify: 판정 문장이 사전 기준의 문구를 그대로 인용한다.
- done: belle 보고 = 된다/반쪽/안된다 한 줄 + 다음 한 걸음.
