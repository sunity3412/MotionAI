---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: "15"
subsystem: judging-data
type: data-collection
tags:
  - judge-data-01
  - ipsf
  - objective-baseline
  - geometric-criterion
  - pending_belle_labeling

dependency_graph:
  requires:
    - 01-11  # gap_too_wide_blocked verdict — NLF baseline 부적합 박제
    - 01-12  # (c) NLF baseline 편차 strong / (d) keypoint chain mismatch strong → NLF 갭 baseline 폐기 결정
  provides:
    - "sunity_shared.judging 모듈 (GeometricCriterion frozen dataclass + IPSF 객관성 가드 6항목)"
    - "load_criteria / load_grouped_criteria — YAML 로더 + motion/moment/joint/path 박제 오류 메시지"
    - "5영상 빈 YAML 템플릿 (Plan 08/10/11 sweep 일관성 유지) — belle 라벨링 (T-5) 대기"
    - "backend/judging_data/README.md — 데이터 수집 가이드 (IPSF 단일 기준 + 사람 점수 금지 박제)"
    - "23 smoke 테스트 (schema 11 + loader 12) — mmpose/torch/NLF/numpy 미import"
  affects:
    - 01-13  # Gemini key moment + criteria — 본 plan GeometricCriterion 을 입력 data 로 사용 (시점 → criteria lookup)
    - 01-14  # 5영상 재검증 sweep — D-14 게이트 baseline 갱신 = 측정 각도 ↔ IPSF angle_target 갭 ≤ tolerance_full
    - "Wave 3 진입 게이트 — NLF 갭 baseline 영구 폐기, IPSF 객관 임계값 갭 단일 기준"

tech_stack:
  added:
    - "pyyaml>=6 (backend/requirements-dev.txt) — YAML 로더 의존성. Lambda 런타임 미사용 (judging 패키지는 채점 데이터 스키마 전용, runtime 진입은 Plan 13 책임)."
  patterns:
    - "frozen dataclass + validate() — IPSF 객관성 가드 6항목 (tolerance > 0 / deduction > 0 / target ∈ [0,360] / 0 ≤ minimum ≤ target / source_ref 비어있지 않음 / moment_key ∈ {setup,hold,peak,release})"
    - "YAML phase 키 → moment_key 매핑 (setup_moment / hold_moment / peak_moment / release_moment → setup / hold / peak / release). Plan 13 Gemini key moment 분류와 동일 enum."
    - "오류 메시지 박제 = motion / moment_key / joint_key / 파일 경로 — belle 라벨링 디버그 편의"
    - "데이터 vs 코드 분리 — sunity_shared/judging/ 은 스키마+로더, IPSF 수치는 모두 backend/judging_data/criteria/*.yaml 에서만 (executor 가 수치 추정 금지)"

key_files:
  created:
    - backend/shared/python/sunity_shared/judging/__init__.py
    - backend/shared/python/sunity_shared/judging/geometric_criterion.py
    - backend/shared/python/sunity_shared/judging/loader.py
    - backend/judging_data/README.md
    - backend/judging_data/criteria/ref-climb.yaml
    - backend/judging_data/criteria/ref-foxtop-split.yaml
    - backend/judging_data/criteria/ref-foxtop.yaml
    - backend/judging_data/criteria/ref-invert.yaml
    - backend/judging_data/criteria/ref-sideway-spin.yaml
    - backend/tests/test_geometric_criterion_schema.py
    - backend/tests/test_geometric_criterion_loader.py
    - .planning/phases/01-poseengine-mediapipe-nlf-r-d/01-15-SUMMARY.md
  modified:
    - backend/requirements-dev.txt   # pyyaml>=6 추가 (judging YAML 로더 의존성)

decisions:
  - "belle 결정 박제 (2026-06-01, Plan 12 verdict 적재 후) — AI 분석 객관성 절대. 사람 점수 라벨링 (belle/강사/심사자) ground truth path 어떤 형식이든 영구 금지 (순위 / 3단계 / 100점 / 4단계 등 전부). 객관 임계값 수치 라벨링 (target / tolerance / deduction / minimum) 은 OK. memory `analysis-objectivity-no-human-scores`."
  - "채점/게이트 baseline = IPSF Code of Points 단일 기준 박제. 한국폴스포츠협회 (KPSA) 도 IPSF 따름. POSA / 미국연맹 / 학원 자체 기준 등 다른 단체 기준 도입 영구 금지. memory `judging-baseline-ipsf-code-of-points`."
  - "Plan 12 verdict (c) NLF baseline 편차 strong (span 23, var 60.56) + (d) keypoint chain 17/17 다름 → NLF 갭 baseline 영구 폐기. 본 plan = 후속 IPSF 객관 임계값 baseline 도입의 첫 단계 (스키마 + 로더 + 빈 템플릿)."
  - "executor 가 IPSF 수치 직접 추정 / 생성 영구 금지. 5영상 YAML 은 빈 템플릿만 (모든 phase 빈 list). 실 수치는 belle (또는 강사 검토 — 선택) 가 IPSF 규정 lookup 으로 채움 (T-5)."
  - "스키마 6항목 가드 박제 — source_ref 빈 문자열 우회를 ValueError ('객관 인용 의무화') 로 차단. moment_key VALID_MOMENT_KEYS={setup,hold,peak,release} 외 값 차단. minimum > target 차단. Plan 01-13 Gemini key moment 분류와 enum 동일하여 향후 lookup 손쉬움."
  - "PyYAML 추가 — backend/requirements-dev.txt 에만 (테스트/로컬 로더). Lambda function 별 requirements.txt 무수정. sunity_shared Lambda Layer 는 현재 runtime 에서 judging 패키지 import 안 함 (Plan 13 에서 runtime 진입 결정). 향후 runtime 진입 시 PyYAML 을 sunity_shared layer 로 이전 (별 plan)."
  - "5영상 = Plan 08/10/11 sweep 일관성 — ref-climb / ref-foxtop-split / ref-foxtop / ref-invert / ref-sideway-spin. 추가 동작 임계값은 별 plan."
  - "D-14 게이트 baseline 변경 박제 — 기존 'RTMPose+MB 측정 ↔ NLF 측정 갭 ≤ 5' (NLF noise 큼 부적합) → **'RTMPose+MB 측정 각도 ↔ IPSF GeometricCriterion angle_target 갭 ≤ tolerance_full' (객관 임계값, IPSF 기본 ±20°)**. Plan 14 sweep 게이트 갱신은 Plan 13 PLAN 수립 시 동시 박제."

requirements_completed: []
# JUDGE-DATA-01 = belle 라벨링 (T-5) 완료 후 1차 충족. POSE-01 = Plan 13/14 완료 후 평가.
# 본 plan = 스키마 + 빈 템플릿 + 데이터 수집 인프라만, 미충족.

metrics:
  duration: "~50 min executor (T-1 ~ T-4 + 23 smoke 테스트 + README + SUMMARY) — belle 라벨링 (T-5) 별도"
  completed_date: "pending_belle_labeling (belle 가 5영상 IPSF 수치 채움 후 'labeled' 갱신)"
  tasks_completed: 4
  tasks_total: 5
  files_created: 12
  files_modified: 1
---

# Phase 01 Plan 15: IPSF GeometricCriterion 데이터 수집 — pending belle labeling

**One-liner:** Plan 12 verdict (NLF baseline 부적합 strong) 후속 — belle 메타 원칙 (분석 객관성 절대 + IPSF Code of Points 단일 기준) 박제 후 JUDGE-DATA-01 v1 평행 진행 첫 진입. NLF 갭 baseline 영구 폐기 + IPSF 객관 임계값 baseline 도입의 첫 단계 (스키마 + 로더 + 빈 템플릿 + 객관성 가드 6항목 + 23 smoke 테스트). 실 수치 라벨링은 belle (T-5) — executor 는 IPSF 수치 추정 영구 금지.

---

## TL;DR

| 항목 | 내용 |
|---|---|
| **Verdict** | **`pending_belle_labeling`** (스키마 + 로더 + 빈 템플릿 완료, IPSF 수치 belle 라벨링 대기) |
| **단계 도달** | T-1 ~ T-4 완료. T-5 belle 5영상 IPSF 수치 라벨링 대기 |
| **scope** | 데이터 수집 인프라 — 스키마 / 로더 / 검증 / 빈 템플릿만. 점수 계산 / Gemini key moment / 측정값 비교는 Plan 13 책임 |
| **신규 파일** | 12 (judging 모듈 3 + README 1 + 5영상 YAML 5 + 테스트 2 + SUMMARY 1) |
| **수정 파일** | 1 (requirements-dev.txt — pyyaml>=6 추가) |
| **단위 테스트** | 23 PASS (schema 11 + loader 12, 0.06s, mmpose/torch/NLF/numpy 미import) |
| **만든 커밋** | 4 (judging 모듈 / YAML 템플릿 + README / 테스트 / SUMMARY) |
| **운영 코드 수정** | 0 (functions / runpod_inference / shared/analysis / shared/pose_lifters / dimensions.py / technique.py / FallbackRecognizer 모두 무수정) |
| **기존 spike 수정** | 0 (Plan 07/08/10/11/12 spike + 5영상 sweep 모두 무수정) |
| **다음 행동** | belle T-5 라벨링 → SUMMARY status `labeled` 갱신 → `/gsd:plan-phase 1 --plan 13` 진입 (Gemini key moment + criteria, Plan 15 데이터 입력) |

---

## T-1 — `sunity_shared.judging` 모듈 (스키마 + 로더)

### 모듈 구조

```
backend/shared/python/sunity_shared/judging/
  __init__.py                     # GeometricCriterion / load_criteria / load_grouped_criteria 재노출 + 핵심 원칙 docstring
  geometric_criterion.py
    VALID_MOMENT_KEYS = ('setup', 'hold', 'peak', 'release')
    @dataclass(frozen=True) class GeometricCriterion
      motion / moment_key / joint_key / angle_target /
      tolerance_full / deduction_per_step / minimum_requirement / source_ref
      validate() — 6항목 가드
  loader.py
    DEFAULT_CRITERIA_DIR = backend/judging_data/criteria/
    _YAML_PHASE_KEYS — setup_moment/hold_moment/peak_moment/release_moment → moment_key
    load_criteria(motion, base_dir=None) → list[GeometricCriterion]
    load_grouped_criteria(motion, base_dir=None) → dict[moment_key, list[GeometricCriterion]]
    _read_yaml — PyYAML safe_load + 명확한 ImportError/ValueError
    _entry_to_criterion — 필수 키 누락 + 타입 변환 + validate() 실패 메시지에 path 박제
```

### `GeometricCriterion.validate()` 객관성 가드 6항목

| # | 가드 | 위반 시 메시지 핵심 |
|---|---|---|
| 1 | `tolerance_full > 0` | `tolerance_full` + motion/moment/joint |
| 2 | `deduction_per_step > 0` | `deduction_per_step` + motion/moment/joint |
| 3 | `0 ≤ angle_target ≤ 360` | `angle_target` + 실 값 |
| 4 | `0 ≤ minimum_requirement ≤ angle_target` | `minimum_requirement > angle_target` 명시 |
| 5 | `source_ref.strip()` 비어있지 않음 | "객관 인용 의무화" |
| 6 | `moment_key ∈ VALID_MOMENT_KEYS` | 4 유효 값 박제 ({setup,hold,peak,release}) |

핵심 박제: 가드 5 (source_ref) 는 사람 점수 라벨링 우회 방지의 1차 차단선. belle 가 점수만 적고 IPSF 인용을 생략한 entry 는 로더 단계에서 거부.

### 오류 메시지 박제 패턴

모든 ValueError 에 `motion={}` `moment={}` `joint={}` 박제 + 파일 path. belle 라벨링 시 어느 entry 가 문제인지 즉시 식별 가능.

## T-2 — 5영상 YAML 빈 템플릿 + judging_data README

### 5영상 파일

```
backend/judging_data/criteria/
  ref-climb.yaml
  ref-foxtop-split.yaml
  ref-foxtop.yaml
  ref-invert.yaml
  ref-sideway-spin.yaml
```

각 파일 헤더 코멘트:

- IPSF Code of Points 기반 GeometricCriterion (JUDGE-DATA-01)
- 작성 가이드 = backend/judging_data/README.md
- 사람 점수 라벨링 금지 — 객관 임계값 수치만
- memory 박제: analysis-objectivity-no-human-scores, judging-baseline-ipsf-code-of-points

본문 = `motion`, `source` (TBD by belle), `criteria` 4 phase 키 모두 빈 list. **executor 가 IPSF 수치 추정/생성 금지** — T-5 belle 라벨링으로만 채움.

### `backend/judging_data/README.md` 8 섹션

1. 단일 기준 = IPSF Code of Points (KPSA 도 IPSF 따름, POSA/미국연맹 도입 금지)
2. 사람 점수 라벨링 영구 금지 (형식 불문, belle 가 채우는 값은 IPSF 객관 임계값 수치만)
3. IPSF 기본 객관 수치 표 (tolerance ±20°, -0.2점 감점, 4대 섹션, pointed feet)
4. YAML 스키마 + invert hold left/right knee 180° / tolerance 20° 예시
5. belle 라벨링 절차 (IPSF 규정 lookup → hold_moment 우선 → source_ref 인용)
6. 강사 협업 옵션 (선택, belle 단독 OK)
7. 검증 명령 (`python3 -m pytest backend/tests/test_geometric_criterion_loader.py -v`)
8. 다른 동작 추가 — 별 plan, 본 plan 스코프 밖

## T-3 — 23 smoke 테스트 (mmpose/torch/NLF 미import)

### `test_geometric_criterion_schema.py` — TestValidate (11 케이스)

- valid (IPSF invert hold target 180° / tolerance 20°) PASS
- tolerance 0 / 음수 → "tolerance" ValueError
- deduction 0 → "deduction_per_step" ValueError
- target 음수 / >360 → "angle_target" ValueError
- minimum > target → "minimum_requirement" ValueError
- source_ref `""` / 공백 / 탭 → "객관 인용|source_ref" ValueError (parametrize × 3)
- moment_key `"invalid_moment"` → ValueError + 4 valid 값 메시지 박제 확인

### `test_geometric_criterion_loader.py` — 3 클래스 12 케이스

`TestLoadEmptyTemplates` (6):
- 5영상 빈 템플릿 load (parametrize) → 모두 `[]` PASS
- `DEFAULT_CRITERIA_DIR` 가 `backend/judging_data/criteria/` 로 풀리는지

`TestLoadErrors` (4):
- 누락 motion → `FileNotFoundError` + motion 이름 + "belle 라벨링" 안내
- malformed YAML (top-level list) → `ValueError` + 파일 경로 박제
- 필수 키 누락 entry → `ValueError` + motion / "hold" 식별
- validate 실패 (source_ref `""`) → `ValueError` + motion / "hold" / "right_elbow" 박제

`TestLoadBelleSimulatedFixture` (2):
- belle 라벨링 시뮬 fixture (invert setup left_shoulder + hold left/right knee) → load + validate PASS, 3 entries
- `load_grouped_criteria` → 4 phase 키 모두 존재, hold 2 / setup 1 / peak·release 빈 list

### 실행 결과

```
23 passed in 0.06s
```

`/Users/kimtaesung/Dev/SunityMotion/backend/.venv/bin/python3 -m pytest backend/tests/test_geometric_criterion_schema.py backend/tests/test_geometric_criterion_loader.py -v`

기존 backend 테스트 회귀 없음 (321 passed, 13 skipped, 2 pre-existing collection error 무관).

## T-4 — 본 SUMMARY + Plan 13 / 14 / Wave 3 진입 게이트 갱신

본 SUMMARY 내 decisions / D-14 baseline 변경 박제 (frontmatter).

---

## T-5 — belle IPSF 수치 라벨링 (autonomous: false)

**현재 status = `pending_belle_labeling`**.

### 절차 (PLAN T-5-1 그대로)

1. `backend/judging_data/README.md` 가이드 숙독.
2. `docs/research/폴스포츠-지식.md` IPSF 4대 섹션 (line 70) + tolerance 20° (line 311) + 동작별 IPSF 규정 lookup.
3. 5영상 각각의 YAML (`backend/judging_data/criteria/ref-*.yaml`) `hold_moment` 우선 채우기 (필요 시 `setup_moment` / `peak_moment` / `release_moment`).
4. 각 entry `source_ref` 에 IPSF Code of Points 정확한 섹션 인용 (예: "IPSF Code of Points 2024 §4.2.1 invert family knee extension").
5. **점수 직접 매기지 말 것** — target angle / tolerance / deduction / minimum 객관 임계값만. tolerance 가 IPSF 규정에서 동작군별로 명시되어 있으면 그 값 사용 (기본 20°).
6. 강사 협업은 선택 — belle 단독 가능. 강사도 점수 라벨링 X, IPSF 인용만.

### 검증

```bash
python3 -m pytest backend/tests/test_geometric_criterion_loader.py -v
```

5영상 다 PASS = belle 라벨링 정합.

### 라벨링 완료 후

- 본 SUMMARY status `pending_belle_labeling` → `labeled` 갱신 (수치 라벨링 commit + frontmatter 수정).
- JUDGE-DATA-01 1차 충족 (REQUIREMENTS.md 갱신은 Plan 13 PLAN 진입 시 동시 박제).
- Plan 13 진입 게이트 통과.

---

## 핵심 결정 박제 (frontmatter decisions 와 중복, 본문 명시)

### 1. AI 분석 객관성 절대 원칙 (memory: analysis-objectivity-no-human-scores)

belle / 강사 / 심사자 누구도 점수를 매기는 ground truth path 작성 영구 금지. 형식 불문 (순위 / 3단계 / 100점 / 4단계 등). 객관 임계값 수치 라벨링은 OK (target / tolerance / deduction / minimum). 본 plan validate() 가드 5 (source_ref 비어있지 않음) 가 1차 차단선.

### 2. 채점 baseline = IPSF Code of Points 단일 기준 (memory: judging-baseline-ipsf-code-of-points)

한국폴스포츠협회 (KPSA) 도 IPSF 따름. POSA / 미국연맹 / 학원 자체 기준 도입 영구 금지. 본 plan source_ref 가 IPSF 인용 의무화. README 1번 섹션에 영구 박제.

### 3. NLF 갭 baseline 폐기 → IPSF 객관 임계값 baseline 도입

Plan 12 (c) verdict 강함 (span 23, var 60.56) + (d) verdict 강함 (17/17 chain 다름) 으로 NLF baseline 신뢰도 약점 확정. 본 plan 부터 D-14 게이트 baseline = **측정 각도 ↔ IPSF GeometricCriterion `angle_target` 갭 ≤ `tolerance_full`**.

Plan 14 게이트 갱신은 Plan 13 PLAN 수립 시 동시 박제 (Plan 13 가 Plan 15 데이터 입력 받아 측정값 비교 함수 도입).

### 4. executor 가 IPSF 수치 직접 추정 영구 금지

YAML 빈 템플릿만. 실 수치는 belle 라벨링. executor 가 placeholder 수치 (180.0 / 20.0 등) 라도 채우면 객관성 위반 (출처 미상 ground truth).

---

## Plan 13 / 14 / Wave 3 진입 게이트 갱신

### Plan 13 (Gemini key moment + criteria) 입력 = 본 plan 데이터

- Plan 13 PLAN 작성 시 본 plan `sunity_shared.judging.load_grouped_criteria(motion)` 호출 패턴 박제.
- Gemini 가 영상에서 key moment 시점 추출 → 시점의 moment_key (`setup` / `hold` / `peak` / `release`) 분류 → 해당 phase 의 `GeometricCriterion` lookup → 측정 각도 ↔ `angle_target` 갭 산출 → 감점 = `max(0, |gap| - tolerance_full) × deduction_per_step` 식.
- `minimum_requirement` 미달 = 동작 실패 게이트.

### Plan 14 (5영상 재검증 sweep) D-14 게이트 갱신

- **신규 baseline**: 5영상 sweep 측정 각도 ↔ 본 plan `angle_target` 갭 ≤ `tolerance_full` (전 phase × 전 joint).
- 기존 baseline (NLF 갭 ≤ 5) 영구 폐기.
- 단, `minimum_requirement` 미달 entry 가 있으면 해당 영상은 동작 실패 처리 (정은지 5영상은 IPSF 기준 합격 가정 → 모든 minimum 통과 기대).

### Wave 3 진입 게이트

- 본 plan T-5 belle 라벨링 완료 (status `labeled`)
- Plan 13 PLAN 작성 (Gemini key moment + criteria 측정값 비교)
- Plan 14 sweep D-14 IPSF baseline 통과
- POSE-01 (REQUIREMENTS.md) 충족 평가 시점.

---

## Self-Check: PASSED

- 신규 파일 12개 모두 worktree (`/Users/kimtaesung/Dev/SunityMotion/.claude/worktrees/agent-a3a3be7c110dd9a7d/`) 존재.
- 수정 파일 1개 (requirements-dev.txt) worktree 에서 `pyyaml>=6` 추가 확인.
- commit 4개 (judging 모듈 / YAML 템플릿 + README / 테스트 / SUMMARY) 모두 `worktree-agent-a3a3be7c110dd9a7d` 브랜치 head 에서 검증.
- 23 smoke 테스트 PASS (0.06s, mmpose/torch/NLF/numpy 미import).
- 기존 backend 테스트 회귀 없음 (321 PASS, 13 skip — 2 pre-existing collection error 는 본 plan 변경과 무관).
- 운영 코드 0줄 수정. 기존 spike 0줄 수정.
- T-5 belle 수치 라벨링 미진입 (autonomous: false, executor 가 IPSF 수치 추정 영구 금지 박제).
- 사람 점수 라벨링 0건. 이모지 0건.
