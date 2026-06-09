---
title: Phase 8 Pre-flight Label Spec — Layer-1 25-timestamp validation gate
author: belle (운영) + plan 08-00 박제
created: 2026-06-09
phase: 08-jerk-jitter
gate_role: Plan 08-03 Task 3 manual checkpoint 진입 차단 해소
---

# Phase 8 Pre-flight Label Spec — Layer-1 25-timestamp 검증

> **belle 운영 작업 박제** — 본 spec 은 Layer-1 motion-agnostic 휴리스틱의 5 phase
> boundary 산출 정확도를 belle 의 수동 라벨링으로 검증한다. PASS 시 Layer 1
> confidence='medium' 승급, FAIL 시 confidence='low' 강제. 분석 pipeline 자체는
> 영향 0 — FAIL 시 unwind path 는 Plan 08-03 의 env unset 으로 graceful degrade.
>
> per REVIEWS Cycle 1 R4 blocker 해소.

## §1 목적

Plan 08-02 에 박제될 Layer-1 motion-agnostic 휴리스틱 (entry / lock / transition /
final_shape / hold 5 phase boundary 산출 함수) 의 정확도를 belle 의 수동 라벨링과
대조해 검증한다. 사람 점수 라벨링이 아니라 **시각 (timestamp_ms) 라벨링** —
[[analysis-objectivity-no-human-scores]] 정합.

이 gate 는 Layer-1 의 confidence 박제 source 가 된다:
- ≥80% 일치 (delta_ms ≤ 200ms) → PASS → Layer 1 confidence='medium' 승급
- < 80% → FAIL → Layer 1 confidence='low' 강제 + warning
  'preflight_label_gate_failed' 박제

## §2 라벨링 범위

| 차원 | 값 | 개수 |
|---|---|---|
| Reference 영상 | ref-invert / ref-foxtop / ref-foxtop-split / ref-climb / ref-sideway-spin | 5 |
| Phase boundary | entry_start / lock_start / transition_start / final_shape_start / hold_start | 5 |
| 합계 timestamp | 5 × 5 | **25** |

motion_id 매핑은 belle 의 학원 용어 매핑 (3-branch system, [[studio-term-3branch-system]])
정합. 본 spec 의 video_id 는 backend `reference` Firestore 컬렉션의 doc id 와 정합.

## §3 라벨링 방법

1. belle 가 본 디렉토리의 `preflight_label_template.csv` 를 spreadsheet (Google
   Sheets 또는 Excel) 로 import.
2. 각 row (영상 × phase boundary 조합) 별로:
   - 영상을 시청 후 해당 phase boundary 의 시작 시점 (timestamp_ms) 박제 →
     `timestamp_ms_belle` 컬럼.
   - Plan 08-02 의 Layer-1 산출 timestamp_ms 박제 → `timestamp_ms_layer1` 컬럼
     (researcher 가 Pod sweep 결과 제공).
3. `delta_ms = abs(timestamp_ms_belle - timestamp_ms_layer1)` 산출 (수동 또는
   spreadsheet 자동).
4. `agreed = 'yes' if delta_ms <= 200 else 'no'` 박제.

## §4 PASS / FAIL 기준

| 기준 | 값 |
|---|---|
| 일치 임계 | delta_ms ≤ 200ms |
| PASS 비율 | 25 row 중 agreed='yes' 가 **≥ 80%** (20/25 이상) |

PASS 시:
- Layer 1 confidence='medium' 승급 박제 (Plan 08-02 의 산출 함수가 본 confidence
  필드 박제).
- Plan 08-03 Task 3 manual checkpoint 통과 → Layer 2 (Gemini key_moments) wiring
  활성 진입 가능 (D-08-E3 정합).

FAIL 시:
- Layer 1 confidence='low' 강제 + warning `'preflight_label_gate_failed'` 박제.
- Plan 08-02 의 산출 함수가 본 confidence 필드 강제 'low'.
- §6 unwind path 적용.

## §5 입력 파일

본 디렉토리의 `preflight_label_template.csv`:
```
video_id,motion_id,phase,timestamp_ms_belle,timestamp_ms_layer1,delta_ms,agreed
```

header 1줄 + 25 row (5영상 × 5 phase) 박제. belle 가 4 컬럼 (timestamp_ms_belle /
timestamp_ms_layer1 / delta_ms / agreed) 채워 PASS/FAIL 판정.

## §6 FAIL 시 unwind path

Plan 08-03 Task 3 manual checkpoint 가:
- `RECOGNIZER_BACKEND` env unset (Phase 5 Gemini 기술 인식기 비활성화)
- `FORCE_SIGNALS_LAYER2_ENABLED` env unset (Plan 08-02 Layer 2 wiring 비활성화)

으로 force_signals 산출 차단 가능 (D-08-E3 정합). 분석 pipeline 자체는 영향 0
— Layer 1 confidence='low' 박제로 downstream (Plan 08-02 dimensions /
contact_points 산출 / Phase 9 force pattern 추론) 가 보수적 추론.

[[mvp-simple-pilot-quality]] 정합 — 구조만 열어두기. 임계값 조정/재라벨링은 v1.5
후속 plan 박제.

## §7 재실행

Plan 08-02 의 Layer-1 threshold (발 vertical / 폴 거리 / keypoint 변화율 cutoff)
박제 재조정 후 본 gate 재실행 가능:
1. researcher 가 Plan 08-02 threshold 갱신.
2. researcher 가 5영상 sweep 재실행 → `timestamp_ms_layer1` 갱신.
3. belle 가 `delta_ms` + `agreed` 재산출.
4. PASS/FAIL 재판정.

belle 의 `timestamp_ms_belle` 라벨 자체는 영상이 변경되지 않는 한 재라벨링 불요
(영상 자체의 phase boundary 시각은 객관적 사실 — 라벨러의 주관 점수 아님).

## §8 박제 메모

- per REVIEWS Cycle 1 R4 blocker (Layer-1 5-phase 미검증) 해소.
- per REVIEWS Cycle 1 R5 (validation gate 운영 docs 미박제) 해소.
- per D-08-E3 (Layer 2 wiring 박제 + pre-flight spike 별 plan 신설 X) 정합.
- per Recommended Next Steps §6 (Plan 08-00 박제 pre-flight gate 신설) 정합.
- per [[analysis-objectivity-no-human-scores]] — phase boundary 시각 라벨링 ≠
  사람 점수 라벨링 (시각은 객관적 사실, 수치 score 아님).
- per [[mvp-simple-pilot-quality]] — 구조만 열어두기, FAIL 시 graceful degrade.

---

*최초 작성: 2026-06-09 — Plan 08-00 Task 3 박제. belle 운영 작업 진입 차단 해소.*
