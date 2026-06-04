---
phase: 05-gemini
plan: "00"
status: complete
wave: 0
completed_at: 2026-06-04
requirements:
  - SCORE-01
files_modified:
  - backend/research/spikes/measure_eunji_reference.py
  - backend/research/evaluations/reports/eunji_reference_measurements/measurements.json
  - backend/judging_data/criteria/ref-foxtop.yaml
  - backend/judging_data/criteria/ref-foxtop-split.yaml
  - backend/judging_data/criteria/ref-invert.yaml
  - backend/judging_data/criteria/ref-sideway-spin.yaml
commits:
  - 82fa0db  # Task 1: measure_eunji_reference.py spike 신설
  - 114e106  # fix: PoleAxis 직접 생성자 (vertical_fallback() 클래스메서드 부재)
  - 3edfb1b  # Task 2: 정은지 reference 측정값 5영상 박제 (measurements.json)
  - 570093c  # Task 3: yaml 4개 source 분기 2 path 정정
---

# Plan 5-00 Summary: yaml source 정은지 reference 정정 (D-17/D-18 박제)

## 박제 정신

Plan 23 sweep verdict `phase1_ready_to_swap=False` (2026-06-03) 의 root cause 3 (AKA 매핑 vs yaml criteria 정합 미검증) 의 실증 fix.

NotebookLM IPSF Code of Points 2024-2025 lookup (05-IPSF-LOOKUP.md) 결과 박제:
- 5영상 yaml hold_moment 의 IPSF 직접 박제 source 박제 X 확인 (ref-climb = Transitions & Climbs angle 차원 X / ref-foxtop·foxtop-split·sideway-spin = IPSF 미등재 / ref-invert = Body Position 차원만)
- 박제 [[gap-and-line-angle-mandatory-gates.md]] "강등/우회 금지" 정신 = 게이트 정의 정확화 (강등 X)
- 박제 [[studio-term-3branch-system.md]] 분기 2 = "한국 학원 통용 + 정은지 reference 비등재 동작" 정합 → yaml source 정은지 reference 측정값 박제 path

## Task 박제 흐름

### Task 1 — spike 신설 (commit `82fa0db`)
`backend/research/spikes/measure_eunji_reference.py` (625 lines) 박제:
- 5영상 S3 download → RTMW wholebody pose (133 keypoints) → COCO-17 변환 → joint angle 산출 → hold_window mean → JSON 박제
- D-18 박제 룰 적용: `tolerance_full=15°`, `minimum_requirement=measured-25°` (tolerance_rule_version 박제)
- ref-climb 특수 처리: hold_window 측정 skip, `joints={}`, `ipsf_source="IPSF Transitions & Climbs"` 박제 (D-20 별 phase)
- D-16 박제 정신 정합: boto3 / torch / mmpose / imageio 모듈 로드 시 0 import (lazy import)
- B6 fix: `--hold-timestamps-default-fallback` flag 박제 (Task 1 단위 검증 path 보호)

### fix — PoleAxis 직접 생성자 (commit `114e106`)
`PoleAxis.vertical_fallback()` 클래스메서드 부재 발견 (Pod 1차 실행 시 AttributeError).
fix = `@dataclass(frozen=True)` 직접 생성자 호출:
```python
PoleAxis(axis_vector=(0.0, 1.0, 0.0), confidence_level="low", source="vertical_fallback", frame_index=None)
```

### Task 2 — belle Pod 측정 + 박제 (commit `3edfb1b`)
**belle blocking-human checkpoint** — Pod 환경 재설치 (mmpose + RTMW weights + boto3 + ffmpeg) + AWS 키 export + spike 실행.

Pod 환경 박제 갱신 ([[runpod-gpu-env.md]] 정정): belle 매 세션 새 Pod = 환경 재설치 자동화 필수 (이전 박제 "Pod 살아있음" 정신 정정).

자동화 wrapper script `/workspace/run_eunji_spike.sh` 박제 (Pod):
- PYTHONPATH=backend/shared/python:. 박제 (B-fix: sunity_shared ImportError 방지)
- RTMW_ONNX_PATH + AWS_DEFAULT_REGION 자동 export
- 검증 step (ONNX 존재 + key length) + nohup background 실행

측정 결과 (`measurements.json`, RTMW @9fps, hold window mean):

| 모션 | hold | left_shoulder | right_shoulder | left_hip | right_hip | left_knee | right_knee |
|---|---|---|---|---|---|---|---|
| ref-climb | skip | — | — | — | — | — | — |
| ref-foxtop | 15~21s | 139.02 | 74.31 | 127.46 | 78.69 | 151.99 | 147.25 |
| ref-foxtop-split | 11~13s | 42.12 | 62.57 | 125.54 | 106.45 | 144.05 | 78.92 |
| ref-invert | 6~10s | 28.35 | 21.05 | 55.90 | 71.72 | 136.97 | 138.12 |
| ref-sideway-spin | 7~11s | 58.82 | 142.11 | 145.28 | 144.96 | 162.51 | 159.08 |

**hold_timestamps 박제 path** = `docs/reference-motions.md` §5 박제 데이터 자동 매핑 (belle 별도 시청 X — orchestrator 가 직접 매칭).

### Task 3 — yaml 4개 정정 (commit `570093c`)
yaml `angle_target` / `tolerance_full` / `minimum_requirement` / `source_ref` 모두 정은지 reference 측정값 박제로 갱신. ref-climb yaml = 이미 정합 박제 (빈 list + D-20 주석) → 변경 없음.

## belle 박제 답변 (2026-06-04)

| 항목 | 박제 |
|---|---|
| (A) 측정값 인체학적 정합 | **yes** (B 박제 = 0~180° 코사인 관절 사이각 이해 OK) |
| (B) tolerance ±15° | **유지** |
| (C) D-18 minimum 룰 | **유지** (음수 박제 = Phase 5 Gemini 자동 BENT_OK 라벨링 신호) |
| (D) D-19 ref-invert Body Position 차원 별 phase | **OK** |
| (E) D-20 ref-climb 이동 횟수 차원 별 phase | **OK** |

## 핵심 박제 (downstream Plan 5-01~5-05 의 source)

1. **yaml source = 정은지 reference 측정값** (분기 2 path 박제). IPSF source 박제 X 명시.
2. **D-18 tolerance/minimum 룰**: tolerance=15° / minimum=measured-25° (음수 박제 OK).
3. **작은 측정값 (예: ref-invert shoulder 21°) = Phase 5 Gemini 자동 BENT_OK 라벨링 신호** = dimensions.py 채점 제외. D-08 박제 정신 정합.
4. **ref-climb = 별 phase (D-20)** = 이동 횟수 차원 추가 필요. v1 ref-climb = 채점 영역 외 (out-of-scope PASS counted, D-01 게이트 분기).
5. **ref-invert Body Position 차원 (D-19)** = 별 phase (Phase 8 또는 신설). v1 = 관절 angle 박제만.
6. **Pod 환경 자동화 박제** ([[runpod-gpu-env.md]] 갱신): 매 세션 새 Pod = 환경 재설치 매번 + wrapper script path 박제.

## 게이트 통과 박제

Phase 5 D-01 게이트 = "정은지 reference 측정값 기준 채점 영역 모션 N/N PASS + out-of-scope counted as PASS".
- 채점 영역 = ref-foxtop / ref-foxtop-split / ref-invert / ref-sideway-spin (4영상)
- out-of-scope = ref-climb (D-20)
- 게이트 = "4영상 angle 4/4 PASS + ref-climb out-of-scope PASS counted" = 사실상 4/4 PASS 목표.

본 게이트 검증 = Plan 5-05 (sweep `--recognizer gemini` + belle Pod sweep verdict).

## Wave 0 종료 박제 — Wave 1 진입 조건 모두 충족

- ✅ yaml source 정정 (4 yaml + ref-climb 정합 박제)
- ✅ measurements.json 박제 (5영상)
- ✅ belle (A)~(E) 박제 답변
- ✅ Pod 환경 박제 (mmpose + RTMW + wrapper script)
- ✅ commit + push (`82fa0db` / `114e106` / `3edfb1b` / `570093c`)

Wave 1 (Plan 5-01 GeminiTechniqueRecognizer + Plan 5-02 TechniqueCache 평행) 진입 가능.

## 박제 정신 정합 검증

| 박제 정신 | 정합 |
|---|---|
| [[feedback-analysis-first.md]] "분석 정확도 우선, 비용 하한 구독료 수준" | ✅ measured 정확도 유지 + Gemini 통합 후 자동 BENT_OK |
| [[analysis-objectivity-no-human-scores.md]] "사람 점수 라벨링 X, 객관 측정값 OK" | ✅ 정은지 reference = 객관 측정값 박제 |
| [[studio-term-3branch-system.md]] 분기 2 = "한국 학원 통용 + 정은지 reference 비등재 동작" | ✅ yaml source = 분기 2 path 명시 |
| [[gap-and-line-angle-mandatory-gates.md]] "강등/우회 금지" | ✅ 게이트 정의 정확화 (강등 X) |
| [[mvp-simple-pilot-quality.md]] "구조만 열어두기" | ✅ peak/release 빈 list 유지 (v2 자동 활성 path) |
| [[gsd-pod-work-push-first.md]] Pod 작업 commit + push | ✅ 모든 commit push 완료 |
| [[runpod-gpu-env.md]] (갱신 박제) | ✅ 매 세션 새 Pod 박제 + wrapper script path |
| [[notebook-lm-pole-sports.md]] IPSF CoP lookup | ✅ 05-IPSF-LOOKUP.md 박제 활용 |

## 후속 작업 박제 (Phase 5 외)

- ref-invert Body Position Inverted 차원 추가 (D-19 별 phase)
- ref-climb 이동 횟수 + grip 안정성 차원 추가 (D-20 별 phase)
- setup/peak/release yaml 박제 (v2 path, JUDGE-DATA-01 belle/강사 협업)
- AKA 매핑 13개 + 분기 2 정은지 reference 비등재 동작 확장 (Phase 16 또는 별 plan)

---

*Plan 5-00 종료: 2026-06-04*
*다음 = Wave 1 (Plan 5-01 + Plan 5-02 평행)*
