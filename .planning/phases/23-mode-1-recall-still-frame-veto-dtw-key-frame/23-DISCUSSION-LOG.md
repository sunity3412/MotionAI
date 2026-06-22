# Phase 23: Mode 1 결함 recall 복구 — still-frame veto + 기준선 정량화 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-22
**Phase:** 23-mode-1-recall-still-frame-veto-dtw-key-frame
**Areas discussed:** Mode 1 입력 형태, 칸/층 정량화 표현 + v1 범위, 정렬 신뢰도 낮을 때 동작, 증상→root cause 묶음 깊이

---

## Mode 1 입력 형태

| Option | Description | Selected |
|--------|-------------|----------|
| 학생+정은지 frame 나란히 | 학생 worst-pose + DTW 매칭 정은지 same-pose frame side-by-side. reference 비교 유지 + v7.0 프롬프트 정합 | ✓ |
| 학생 단일 frame만 IPSF 평가 | 스파이크 방식, 비교 없이. recall은 되나 정은지 기준점 의미 약화 | |
| 비교 우선 + 단일 폴백 | 기본 나란히, 신뢰도 낮으면 단일 IPSF | |

**User's choice:** 학생+정은지 frame 나란히 (추천)
**Notes:** Mode 1 = 정은지 기준 비교가 본 설계. 상대 편차 포착 + 기존 `_COMPARISON_PROMPT` 정합.

---

## 칸/층 정량화 표현 + v1 범위

| Option | Description | Selected |
|--------|-------------|----------|
| 각도수치+몸상대 칸/층 텍스트, 시각오버레이 바로후속 | v1=관절각 직접수치 + 거리 몸-상대 칸/층 텍스트; 화살표/칸 시각 오버레이는 fault_zoom 확대비교 위에 후속 | ✓ |
| v1부터 시각 화살표+칸 오버레이 풀 | 확대비교 이미지에 처음부터 풀 시각화. UI 작업량 큼 | |
| 각도 수치만 먼저 | 거리 정량화 전체를 후속 phase로 | |

**User's choice:** 각도수치+몸상대 칸/층 텍스트, 시각오버레이 바로후속 (추천)
**Notes:** 절대 cm 금지(단일 카메라 스케일 모호). 칸 정의 = 정은지 도달치 100%(N칸) 대비 학생 비율.

---

## 정렬 신뢰도 낮을 때 동작 (시작점/템포 상이)

| Option | Description | Selected |
|--------|-------------|----------|
| 다중프레임 union → 그래도 낮으면 veto 보류+표시 | worst-pose ±윈도우 다중프레임 union, 그래도 낮으면 veto 보류 + "신뢰도 낮음" 표시. 거짓결함 방지 | ✓ |
| 항상 ±윈도우 다중프레임 | 단일프레임 의존 줄임. 단일프레임 상세 recall 이점 희석 우려 | |
| 전체영상 veto로 폴백 | 기존 방식. 그게 상체 놓치는 원인이라 폴백 품질 낮음 | |

**User's choice:** 다중프레임 union → 그래도 낮으면 veto 보류+표시 (추천)
**Notes:** `MotionMatch.distance` 게이팅. 객관성·위양성 게이트 — 오정렬에서 거짓결함 fabrication 금지.

---

## 증상→root cause 묶음 깊이

| Option | Description | Selected |
|--------|-------------|----------|
| Gemini 추론, 기존 원인섹션에 '~로 보임' 가설 | 결함군→root cause(힘/폴밀착) 추론, dual-coach 원인 섹션, 단정 금지 가설. 프롬프트 추가만 | ✓ |
| 룰기반 매핑 | 결함셋→정해진 원인 문구. brittle, 창발 못 담음 | |
| v1은 증상만, 원인 후속 | 증상 시각 그룹핑만, 원인 코칭 후속 phase | |

**User's choice:** Gemini 추론, 기존 원인섹션에 '~로 보임' 가설 (추천)
**Notes:** belle 도메인 — 폴 자세는 힘/밀착이 root, 고개젖힘·삐뚤어짐은 동반 증상(창발). 사람-라벨 원인 ground truth 금지.

## Claude's Discretion

- key-frame 선별 알고리즘, ±윈도우 크기, 부위 분할 경계(머리/그립 추가), N-sample 수, 캐시 키 input_granularity 반영, 호출수 bound — 게이트 준수 하에 구현 재량.

## Deferred Ideas

- 화살표+칸/층 시각 오버레이 풀 구현 → v1.1.
- 자체 비전 모델 파인튜닝 → Phase 22.
- reference 셀프 등록 → Phase 21.
- AQA part-aware contrastive 점수 모델 → 라벨셋 확보 후 중장기.
