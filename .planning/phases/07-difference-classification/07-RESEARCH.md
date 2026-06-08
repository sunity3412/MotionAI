# Phase 7: 차이 분류 (Difference Classification) — Research

**Researched:** 2026-06-08
**Domain:** Backend classification + canned-string copy mapping (pure-Python, numpy-only, no LLM, no I/O)
**Confidence:** HIGH (도메인 100% 내부 코드 + Phase 6 lock 정합 + IPSF 카피 룰 출처 명확)

## Summary

Phase 7 은 Phase 6 의 `compare_body_profiles()` 출력인 `BodyComparisonReport.findings[]` (5 IPSF GeometricCriterion deficit + Sunity `pose_reliability_low`) 를 받아, **순수 함수** 한 개로 (1) 각 finding 에 `category` (`body_type_allowed` / `needs_adjustment` / `uncertain`) 와 `phase` (v1 = `'hold'`) 를 부여하고, (2) `BodyComparisonReport` 두 신설 배열 (`doNotOverCorrect: list[str]` + `recommendedFocus: list[str]`) 을 백엔드 캔드 매핑으로 채우는 layer 다. LLM 호출 없음, 네트워크 호출 없음, AWS 의존 없음 — Phase 11 LLM 풍부화의 입력만 박제.

분류 룰 (D-07-A1) 은 `body_type_adjusted` 플래그 + `|deduction_score|` 임계 (`0.2`) 조합. confidence-tiered demotion 은 Phase 6 D-06-U1 의 0.5 게이트 단일 재사용 (D-07-U1 — Phase 7 별도 임계 도입 X). 캔드 카피는 `(deficit_code, category, joint_group, comparisonType)` 4축 dict literal (joint_key 폭발 회피 위해 `joint_group` 4 그룹으로 축소). research §10.1 4 예문 톤 + §10.3 금지 6종 grep gate 단위 test 가 backstop.

**Primary recommendation:** `backend/shared/python/sunity_shared/analysis/copy_templates.py` 신규 모듈 1개 (dict literal 매핑 + 헬퍼 `render_finding_copy()`) + `body_normalizer.py` 의 `classify_findings()` pure function 추가 + `compare_body_profiles()` 안에서 호출하여 Report 에 주입. schema 확장은 BodyComparisonFinding 4 필드 + BodyComparisonReport 2 필드 (총 6) atomic 3-way lockstep commit.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**(A) 분류 룰**

- **D-07-A1**: `body_type_adjusted` 플래그 + `deduction_score` 크기 조합 룰.
  - `body_type_adjusted=True` + `abs(deduction_score) ≤ 0.2` → `body_type_allowed`
  - `body_type_adjusted=True` + `abs(deduction_score) > 0.2` → `needs_adjustment`
  - `body_type_adjusted=False` → 항상 `uncertain`
- **D-07-A2**: uncertain 임계 = Phase 6 D-06-U1 0.5 게이트 재사용.
  - `report.bodyNormalizationConfidence < 0.5` → 모든 finding 의 category 를 `uncertain` 으로 강제 demotion
  - `finding.confidence < 0.5` → 해당 finding 개별 `uncertain` demotion
  - 두 게이트 동시 적용 (OR 합집합)
- **D-07-A3**: `needs_adjustment` 분류가 빈 리스트 위험 — researcher 가 5 영상 sweep 데이터에서 deduction 분포를 측정해 임계 0.2 가 적정한지 검증.

**(B) 결과 카피 출처**

- **D-07-B1**: 백엔드 캔드 템플릿. `BodyComparisonReport` 안에 `doNotOverCorrect: list[str]` + `recommendedFocus: list[str]` 두 배열 명시 출력.
- **D-07-B2**: Claude 가 research §10.1 4 예문 직접 작성 + 동일 톤 확장. belle 가 plan 단계에서 검수.
- **D-07-B3**: 카피 분배 룰 — `body_type_allowed` → `doNotOverCorrect[]`, `needs_adjustment` → `recommendedFocus[]`, `uncertain` → 별도 카피 (researcher/planner 결정).

**(C) 동작 단계 분할**

- **D-07-C1**: v1 = 단일 `'hold'` moment. `BodyComparisonFinding` 에 `phase` 필드 추가, nullable, 기본값 `'hold'`.

**(D) 카피 톤**

- **D-07-D1**: research §10.1 권장 4종 + §10.3 금지 6종 + Sunity 추가 3종 룰 (가능성 언어 / AI 보조 톤 / 부위별 원인 언어).
- **D-07-D2**: 금지 표현 6종 grep gate 단위 test.
- **D-07-D3**: mode 분기 (mode1 / mode3_first / mode3_progress) 카피 톤.

**(U) Universal**

- **D-07-U1**: confidence-tiered 정합 (Phase 6 D-06-U1 재사용). 0.5 게이트 단일.

### Claude's Discretion

- canned string mapping table 의 18+ 카피 본문 작성 (Claude 가 §10.1 톤 박제 + 톤 정합 확장, belle plan 단계 검수)
- uncertain 화면 표시 방식 (recommendedFocus 통합 vs uncertainFindings 별도 배열 신설) — researcher/planner 결정
- deduction 임계 0.2 의 정확도 검증 (sweep 데이터 분석 후 0.2/0.3/0.4 비교)
- 카피 매핑 키 (deficit_code × category × joint_key × comparisonType) 의 정확한 차원 — joint_key 부위 그룹 축소

### Deferred Ideas (OUT OF SCOPE)

- 동작 단계 (entry / lock / transition / final_shape / hold) v2 확장 — Phase 8 또는 Plan 13 (Gemini key_moments) 통합 시 박제. Phase 7 v1 schema 박제는 v2 호환.
- 카피 LLM 풍부화 — Phase 11 (CoachCommentHook + Cerebras coach_writer) 책임.
- 보완 운동 매핑 — Phase 13.
- 영상 위 오버레이 좌표 그리기 — Phase 12.
- categoryByPhase aggregate (v2)
- CoachCommentHook 의 openQuestionsForCoach 자동 populate — Phase 11 책임.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PERS-01 | 체형 정규화 비교 엔진(`normalizeStudentPoseToProReference`)이 프로의 동작 성공 원리를 수강생 신체 비율에 맞게 재계산하고, 차이를 "체형 허용 / 개선 필요 / uncertain"으로 분류한다 — coaching 모드 정규화 ON | Phase 6 가 정규화 + finding 산출까지 박제 완료 (close-out 2026-06-08). 본 phase 가 PERS-01 의 **"분류"** 부분 단독 완성: §"Architecture Patterns" + §"Classification Rule Calibration" + §"Canned Copy Mapping Table" + §"Validation Architecture" 가 4 success criteria 1:1 박제. |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

본 phase 가 본 root CLAUDE.md 의 다음 directive 와 정합 필수:

| 출처 | Directive | 본 phase 적용 |
|---|---|---|
| §3 | 기술 스택 (변경 금지) | Python Lambda 백엔드만. LLM/RevenueCat/CloudFront 무관. |
| §3 | 시크릿 — Parameter Store. `.env` 하드코딩 금지 | canned string dict literal 은 secret 무관 (정적 문자열). |
| §4 | 브랜드 컬러 #FF4B33 / Pretendard / 라이트 전용 | 본 phase = 백엔드. UI 무관. Phase 12 frontend 가 본 phase 출력 소비 시 적용. |
| §7 | 작은 단위 작업, 의미있는 테스트, 이모지 금지, 슬롭 코드 금지 | canned string 안 이모지 금지. grep gate 단위 test 가 의미있는 테스트. |
| Cross-cutting | `analysis.ts` ↔ `models.py` ↔ `contract.md` 3-way lockstep | 신설 4+2 필드는 한 atomic commit 으로 3 파일 동시 갱신. |
| Cross-cutting | 한국어 user-facing 카피, 영어 식별자 | dict literal **value** = 한국어, **key** = 영어 enum. |
| Cross-cutting | 사양 인용 시 `§` shorthand (`design.md §5-4`, `contract.md §8` 등) | canned string 모듈 module-docstring 에 `research/01_FINAL §10.1` 인용. |
| `[[no-baekje-filler]]` | "박제" 단어 카피에 남용 X | 한국어 user-facing canned string 안에 "박제" 단어 사용 금지. grep gate 에 포함. |
| `[[analysis-objectivity-no-human-scores]]` | 사람 점수 라벨링 영구 X | canned string 의 분류 룰 데이터가 belle/강사 점수 라벨 무관 (`body_type_adjusted` + `deduction_score` 만 사용). |
| `[[mode3-progress-not-similarity]]` | mode3 = 절대 지표 델타, % 일치 헤드라인 금지 | mode3_progress 카피에 "%일치" / "유사도" 표현 금지. grep gate 추가. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Finding category 분류 (allowed/needs/uncertain) | Backend / pure-Python (`body_normalizer.classify_findings`) | — | numpy 무관 순수 함수. 단위 test 가능. boto3/네트워크 무관. |
| Canned string mapping (deficit × category × group × mode → Korean) | Backend / pure-Python (`copy_templates`) | — | 정적 dict literal. 모듈 import 1회 로드. LLM 호출 없음. |
| `doNotOverCorrect[]` / `recommendedFocus[]` 조립 | Backend (compare_body_profiles 안) | — | classify_findings 출력의 단순 list comprehension. |
| Firestore 저장 | Backend (`firestore_admin.complete_analysis`) | — | Phase 6 박제 정합 (W5 validator + `_dataclass_to_camel_case_dict` 자동 변환). 신설 필드 코드 변경 0. |
| Frontend 화면 분기 (allowed→회색 / needs→강조 / uncertain→"강사 확인") | Frontend (Phase 12 책임) | — | 본 phase 출력만 박제. UI 렌더 X. |
| LLM 풍부화 (canned → 동적 자연어) | Phase 11 (Cerebras `coach_writer`) | — | 본 phase 의 canned string 이 Phase 11 시스템 프롬프트 input 으로 박제. |

**검증 — 본 phase 가 잘못된 tier 에 들어가지 않음:** Phase 7 은 **분석 코어 layer** (Phase 6 의 sibling). pipeline wiring 변경 없음 — `compare_body_profiles()` 내부 호출만 1줄 추가. Firestore schema 자동 (camelCase 변환 박제). UI 변경 0.

## Standard Stack

### Core (모두 기존 — 신규 라이브러리 0)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `dataclasses` | 3.12 | frozen dataclass 4 필드 확장 (BodyComparisonFinding) + 2 필드 (BodyComparisonReport) | Phase 6 박제 패턴 정합 |
| Python stdlib `typing` | 3.12 | `Literal["body_type_allowed", "needs_adjustment", "uncertain"]` enum | Phase 6 `ComparisonType` 정합 |
| Python stdlib `re` | 3.12 | 금지 표현 6종 grep gate 단위 test 패턴 | 단위 test backstop |
| `pytest >=8,<9` | 8.x | grep gate 단위 test + classify_findings 분류 룰 단위 test | Phase 6 박제 정합 |

### Supporting (모두 기존)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | >=1.26,<3 | classify_findings 시그니처는 numpy 무관. compare_body_profiles wiring 만 numpy 인접. | 신규 numpy 호출 0. |
| firebase-admin | >=6,<7 | 신설 필드 자동 저장 (W5 validator 통과 보장 — list[str] 만, nested-array X) | 코드 변경 0. Phase 6 박제 패턴 자동 활용. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python dict literal (정적 mapping) | YAML/JSON 외부 파일 | dict literal 이 type-check 가능 + import 1회 + lockstep grep 용이. 외부 파일은 frozenset 검증 못함. **dict literal 권장.** |
| 임계 0.2 (D-07-A1) | 0.3 / 0.4 (sweep 검증 후 조정) | 0.2 = IPSF Page 21 절대 감점 단위 (-0.2 단계). sweep 데이터 (아래 §"Classification Rule Calibration") 분석 결과 0.2 권장 (정합성 + Page 21 단계 표준). |
| `Literal["body_type_allowed", ...]` enum | `enum.Enum` 클래스 | dataclass `__post_init__` validator 가 Literal string 비교 더 간결. Phase 6 `ComparisonType` 박제 패턴 정합. |
| pre-rendered list[str] (백엔드에서 카피 텍스트 만들어 저장) | per-finding `recommendation: str` 필드 (per-finding) + 두 list[str] aggregate (per-report) 둘 다 출력 | **둘 다 출력 권장** — per-finding 은 Phase 12 화면 분기 + Phase 11 LLM 입력 source. aggregate 두 list 는 결과 화면 두 카드 (강사 보조 카피 박스) direct render. 중복 같지만 source-of-truth 분리. |

**Installation:**
신규 의존성 0. Phase 6 환경 그대로 사용.

**Version verification:** 신규 패키지 없음 → Package Legitimacy Audit 의 disposition 모두 "N/A (no new packages)".

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (no new packages) | — | — | — | — | — | N/A — Phase 7 은 기존 stdlib + pytest 만 사용 |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
[pipeline._process]
    │
    ▼
[compare_body_profiles(comparison_type, pose_frames, profiles, ...)]   ← Phase 6 박제
    │
    │   1) confidence + warnings 산출 (Phase 6)
    │   2) foreshortening 게이트 (Phase 6 W6)
    │   3) gate_open → normalize_pose_by_segments (Phase 6 C1)
    │   4) measure_ipsf_absolute_deficits (Phase 6 R9 — 5 IPSF + pose_reliability_low)
    │   5) ┌── NEW Phase 7 ──┐
    │      │  classify_findings(findings, body_normalization_confidence, comparison_type)
    │      │      ├── per-finding category 결정 (D-07-A1 + D-07-A2)
    │      │      ├── per-finding phase 부여 (v1 = 'hold', D-07-C1)
    │      │      ├── per-finding body_type_interpretation / recommendation
    │      │      │     ← copy_templates.render_finding_copy(deficit_code, category,
    │      │      │                                         joint_group, comparison_type)
    │      │      └── per-report doNotOverCorrect / recommended_focus (aggregate)
    │      └────────────────┘
    │   6) BodyComparisonReport 조립 (4+2 신설 필드)
    ▼
[Firestore: users/{uid}/analyses/{id}.result.bodyComparisonReport]
    │
    ├── (Phase 11) Cerebras 가 canned → 자연어 풍부화
    └── (Phase 12) 화면 분기 (allowed→회색 / needs→강조 / uncertain→강사 확인 권유)
```

### Recommended Project Structure

```
backend/shared/python/sunity_shared/analysis/
├── body_normalizer.py          # 기존 — classify_findings() 함수 신규 추가
│                                 # BodyComparisonFinding +4 필드 / BodyComparisonReport +2 필드
├── copy_templates.py           # 신규 모듈 (Phase 7 본체)
│                                 # — _COPY_TEMPLATES dict literal
│                                 # — render_finding_copy(deficit_code, category, joint_group, comparison_type)
│                                 # — _JOINT_TO_GROUP mapping
│                                 # — FORBIDDEN_PHRASES tuple (grep gate)
└── (기타 모듈 무수정)

backend/tests/phase07/                             # 신규 디렉토리 (Phase 6 패턴 정합)
├── __init__.py
├── conftest.py
├── fixtures/
│   ├── fixture_classification_allowed.json       # body_type_adjusted=True, deduction=-0.2
│   ├── fixture_classification_needs.json         # body_type_adjusted=True, deduction=-0.5
│   ├── fixture_classification_uncertain_raw.json # body_type_adjusted=False
│   ├── fixture_classification_uncertain_low_conf.json # finding.confidence < 0.5
│   └── fixture_canned_no_forbidden.json          # 전체 dict literal iterate input
├── test_classify_findings.py                     # 분류 룰 단위 test
├── test_copy_templates_no_forbidden.py           # 6 금지 표현 grep gate
├── test_copy_templates_render.py                 # render_finding_copy 매핑 단위 test
├── test_body_comparison_report_phase7_lockstep.py # TS / Python schema 1:1 검증
├── test_compare_body_profiles_phase7_integration.py # Phase 6 호출 안에서 분류 + 카피 통합
└── test_dataclass_to_camel_case_dict_phase7.py   # 신설 필드 camelCase 자동 변환

app/src/types/analysis.ts                          # 4+2 필드 추가 (lockstep)
docs/contract.md §8                                # 4+2 필드 + canned string mapping 명세 추가
```

### Pattern 1: Pure Function `classify_findings()`

**What:** `BodyComparisonFinding[]` 받아 분류 + 카피 부여 후 새 `BodyComparisonFinding[]` + 두 aggregate list 반환. numpy 무관, network 무관, LLM 무관.

**When to use:** `compare_body_profiles()` 안에서 `measure_ipsf_absolute_deficits()` 호출 직후, BodyComparisonReport 조립 직전.

**Signature:**
```python
def classify_findings(
    findings: list[BodyComparisonFinding],
    body_normalization_confidence: float,
    comparison_type: ComparisonType,
) -> tuple[list[BodyComparisonFinding], list[str], list[str]]:
    """입력 findings 의 category/phase/카피 부여 + aggregate 두 list 반환.

    Args:
        findings: Phase 6 measure_ipsf_absolute_deficits() 출력 그대로.
        body_normalization_confidence: report-level confidence (D-07-A2 게이트).
        comparison_type: mode 분기 (D-07-D3) — canned string 키로 사용.

    Returns:
        (classified_findings, do_not_over_correct, recommended_focus)
        - classified_findings: 입력 findings 각각에 category/phase/body_type_interpretation/
                               recommendation 4 필드 부여한 새 frozen dataclass 인스턴스.
        - do_not_over_correct: aggregate list[str] — category='body_type_allowed' 의 카피.
        - recommended_focus: aggregate list[str] — category='needs_adjustment' + 'uncertain'
                              의 카피 (uncertain 은 "AI 확신 부족, 강사 확인 권유" 톤,
                              §"Schema Extension" Decision 1 참조).
    """
```

**예시 (사용):**
```python
# compare_body_profiles 안에서
findings = measure_ipsf_absolute_deficits(angles, profile, normalized_keypoints, pose_frames=pose_frames)

classified, dnoc, rec_focus = classify_findings(
    findings,
    body_normalization_confidence=confidence,
    comparison_type=comparison_type,
)

return BodyComparisonReport(
    # … 기존 필드 …
    findings=classified,
    do_not_over_correct=dnoc,
    recommended_focus=rec_focus,
)
```

### Pattern 2: Canned Mapping `copy_templates.render_finding_copy()`

**What:** `(deficit_code, category, joint_group, comparison_type)` 4축 dict lookup → Korean string tuple (interpretation, recommendation).

**When to use:** `classify_findings()` 내부에서 per-finding 호출.

**Signature:**
```python
def render_finding_copy(
    deficit_code: str,
    category: Literal["body_type_allowed", "needs_adjustment", "uncertain"],
    joint_group: Literal["arm", "leg", "torso", "pole_axis", "global"],
    comparison_type: ComparisonType,
) -> tuple[str, str]:
    """(interpretation, recommendation) Korean 카피 반환.

    fallback: 키 미발견 시 generic 카피 + KeyError 대신 logger.warning + 안전 fallback.
    Phase 11 (LLM) 진입 전 graceful behavior 우선.
    """
```

### Pattern 3: 3-way Atomic Lockstep Commit

**What:** Phase 6 박제 패턴 — `analysis.ts` interface + `body_normalizer.py` dataclass + `docs/contract.md §8` 한 commit 으로 동시 갱신.

**Source:** `backend/shared/python/sunity_shared/analysis/body_normalizer.py:787-895` (Phase 6 박제) + `app/src/types/analysis.ts:430-550` + `docs/contract.md §8.

**Phase 7 적용:**
- 1 commit = Python dataclass 4+2 필드 + TS interface 4+2 필드 + contract.md §8 표 두 줄 추가 + (필요 시) §8.3 분류 룰 박제.
- 부분 commit 금지.

### Anti-Patterns to Avoid

- **dataclasses.replace 우회**: BodyComparisonFinding 의 신설 4 필드를 사후 `replace()` 로 채우는 패턴은 Phase 6 R8 박제 (`extra_warnings injection`) 와 동일하게 금지. `classify_findings()` 가 새 dataclass 인스턴스 만들어 반환.
- **두 list 를 frontend 에서 derive**: per-finding category 만 저장하고 `doNotOverCorrect[]` / `recommendedFocus[]` 를 frontend 가 list comprehension 으로 만드는 패턴 금지. **두 list aggregate 도 백엔드가 산출해 Firestore 저장** — Phase 11 LLM 풍부화의 입력이자 Phase 12 직접 렌더 source. (D-07-B1 정합)
- **canned string yaml 외부 파일**: 외부 파일 로드는 (1) Lambda cold start 비용, (2) import 시점 frozenset 검증 못함, (3) IDE rename refactor 어려움. **Python dict literal 권장.**
- **comparisonType 빼고 canned 만 만들기**: §"Mode Branch Carry-over" 위반. mode1 = "정은지 선수 기준" / mode3_first = "Page 9 절대 기준" / mode3_progress = "이전 영상 대비" 톤이 다름. canned string 키에 comparisonType 반드시 포함.
- **joint_key 17개 그대로 canned string 만들기**: 5 deficit × 3 category × 17 joint × 3 mode = 765 카피 폭발 → 유지보수 불가. `joint_group` 4-5개로 축소 필수 (§"Canned Copy Mapping Table" 참조).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| snake_case → camelCase 변환 | 신규 변환 함수 | `pipeline.app._dataclass_to_camel_case_dict()` 기존 5-case helper (Phase 6 C8 박제) | dataclass / list / dict / Enum / scalar 5 case 명시. 신설 필드 자동 변환 (코드 변경 0). |
| Firestore nested-array 검증 | 신규 validator | `firestore_admin._validate_flat_dict_no_nested_array()` 기존 (Phase 6 W5 박제) | list[str] (`do_not_over_correct` / `recommended_focus`) 자동 통과. list[dict-of-scalars-only] (`findings`) 도 통과 (`_validate_dict_only_scalars`). |
| confidence 게이트 임계 | 신규 임계 도입 | `body_normalizer.CONFIDENCE_GATE = 0.5` 기존 (Phase 6 D-06-U1) | D-07-U1 정합. 일관성. |
| 한국어 부위 라벨 (joint_key → "왼쪽 어깨") | 신규 사전 | `analysis.skeleton.JOINT_LABEL_KO` 기존 dict | 8 관절 라벨 (Phase 4 박제). canned string 안에서 활용. |
| mode-aware baseline 카피 | 신규 분기 helper | `assemble._DIMENSION_BASELINES_MODE1` / `_MODE3` 패턴 정합 | Phase 12.5 박제. dict literal 키에 `comparison_type` 포함하면 동일 패턴. |
| 분류 결과를 LLM 으로 동적 생성 | LLM 호출 | dict literal canned string (D-07-B1) | Phase 11 책임 분리. LLM 미설정 환경에서도 동작 보장. Cerebras 키 fallback (Phase 11 success criteria 5) 호환. |

**Key insight:** Phase 6 가 이미 (a) dataclass frozen 패턴, (b) camelCase 자동 변환, (c) Firestore nested-array validator, (d) 3-way lockstep, (e) 0.5 confidence 게이트, (f) ComparisonType union 5 박제. **Phase 7 은 위 6개를 그대로 활용** — 신규 인프라 0. 추가는 `classify_findings()` pure function 1개 + `copy_templates.py` dict literal 1개.

## Runtime State Inventory

> Not applicable. Phase 7 은 순수한 schema 확장 + 신규 함수 추가 phase (rename/refactor/migration 무관). 기존 데이터의 rewrite/migration 없음.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None** — Phase 7 신설 필드 (`category` / `phase` / `body_type_interpretation` / `recommendation` / `do_not_over_correct` / `recommended_focus`) 는 신규 doc 부터 산출. **기존 doc backfill 불요** (TestFlight Phase 6 close-out 이후 새 분석부터 자동 적용). | none |
| Live service config | **None** | none |
| OS-registered state | **None** | none |
| Secrets/env vars | **None** — canned string 은 정적 dict literal, secret 무관 | none |
| Build artifacts | **None** — pyproject.toml / requirements.txt 변경 없음 (신규 dep 0) | none |

**Verified by:** Phase 7 = 새 함수 + 새 dataclass 필드 추가 only. 기존 함수 시그너처 변경 없음 (compare_body_profiles 의 호출 위치 1줄만 추가). 기존 Firestore doc 은 신설 필드 부재 시 frontend `userAnalyses.normalize()` 가 graceful default (빈 list[]) 처리하면 됨 — TS interface 의 두 list 는 default `[]`, per-finding 4 필드는 optional 처리.

## Classification Rule Calibration

> Locked decision D-07-A3 — researcher 책임: deduction 임계 0.2 가 적정한지 5 영상 sweep 데이터로 검증.

### sweep_rtmw_20260603_1409 데이터 분석

소스: `backend/research/evaluations/reports/sweep_rtmw_20260603_1409/report.md` + `report.json`

5 영상 (ref-climb, ref-foxtop-split, ref-foxtop, ref-invert, ref-sideway-spin) 의 RTMW + IPSF 회귀 결과:

| 모션 | pole_axis | IPSF | line | angle | rtmw_mean |
|---|---|---|---|---|---|
| ref-climb | low | PASS | PASS | FAIL | 95.4 |
| ref-foxtop-split | low | FAIL | FAIL | FAIL | 93.0 |
| ref-foxtop | low | FAIL | FAIL | FAIL | 93.3 |
| ref-invert | low | FAIL | PASS | FAIL | 93.6 |
| ref-sideway-spin | low | FAIL | PASS | FAIL | 94.8 |

**도출:**

1. **deduction 분포 (Phase 6 R9 deficit 측정 산식)** [CITED: backend/shared/python/sunity_shared/analysis/body_normalizer.py:944-1110]:
   - `knee_toe_alignment`: -0.2 (IPSF Page 21 단계 감점, 발견 시 emit)
   - `clean_lines`: -0.2
   - `extension`: -0.2
   - `posture`: -0.2
   - `body_placement`: -0.2
   - `pose_reliability_low`: -0.5
   
   현재 산식상 **deduction 값이 정확히 2 가지** (-0.2 또는 -0.5). 임계 `abs() <= 0.2` 와 `> 0.2` 이분법이 정확히 두 그룹 분리. **`0.2` 가 IPSF Page 21 단계 감점 단위 (-0.2 / -0.5) 의 자연 경계.**

2. **임계 0.3 / 0.4 비교:**
   - 0.3 임계: `abs(-0.2) ≤ 0.3` → 5 IPSF deficit 모두 allowed (변화 없음, 0.2 와 동일)
   - 0.4 임계: 동일
   - 0.5 임계: `abs(-0.5) ≤ 0.5` → `pose_reliability_low` 도 allowed 가 됨 (위양성 — pose 신뢰도 낮음을 "체형 허용 차이" 로 박제하는 건 의미상 부적절)
   - **결론: 임계 0.2 또는 0.3 또는 0.4 모두 동일 결과. 0.5 는 위양성. 박제 일관성상 `0.2` 권장 (IPSF Page 21 단위와 정합).**

3. **D-07-A3 위험 박제 (`needs_adjustment` 빈 리스트):**
   - 5 IPSF deficit 모두 `-0.2` → `body_type_adjusted=True` 인 한 모두 `allowed`. `needs_adjustment` 는 **`pose_reliability_low` 가 발견된 영상에서만** 생성.
   - sweep 데이터에서는 `pose_reliability_low` 가 (현재 산식상) `body_type_adjusted=True` 일 때만 -0.5 발생 → `needs_adjustment` 분류 진입 가능.
   - **위험: 양질 영상 (pose_reliability_low 없음) + 정규화 ON → `needs_adjustment` 가 항상 빈 리스트**. v1 limitation 박제 + Phase 8 (force pattern) / Phase 10 (safety flag) 가 본 카테고리 채울 source. (UX 톤: "분석 결과 큰 보정은 필요하지 않습니다" — 빈 리스트 친화적 카피 박제 권장)
   - 또 다른 path: Phase 8 / Phase 13 통합 시 deficit code 가 늘어나면서 -0.5 (큰 차이) deduction 이 증가 → `needs_adjustment` 자연 비율 증가. v1 박제는 빈 리스트 친화적 카피.

4. **권장 카피 (빈 리스트 처리):**
   - `recommended_focus = []` 일 때 frontend 분기: "보정 우선순위가 명확하지 않아요. 강사와 함께 영상을 한 번 더 확인해 보세요." (가능성 언어 + AI 보조 톤). Phase 12 화면 분기 책임.
   - `do_not_over_correct = []` 일 때: 빈 박스 숨김 + 별도 카피 없음 (어색하지 않음).

**Recommendation:** **임계 0.2 박제** (D-07-A1 그대로). sweep 데이터 검증 결과 0.3/0.4 와 동일 결과 + IPSF Page 21 정합 + `pose_reliability_low` (-0.5) 자연 분리. `needs_adjustment` 빈 리스트 위험은 v1 limitation 박제 + 친화적 카피 fallback 으로 해결. 임계 자체는 향후 Phase 8/13 deficit code 확장 시 재검토 trigger.

## Canned Copy Mapping Table

### Mapping Dimension Choice

원본 후보 (D-07-Discretion): `(deficit_code × category × joint_key × comparisonType)` = 5 × 3 × 17 × 3 = **765 카피 폭발** → 유지보수 불가.

**축소 룰:**

1. **joint_key (17개) → joint_group (5개)**:
   | Group | 포함 joint_key | 한국어 라벨 |
   |---|---|---|
   | `arm` | left_elbow, right_elbow, left_shoulder, right_shoulder, left_wrist, right_wrist | 팔/어깨 |
   | `leg` | left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle | 다리/고관절 |
   | `torso` | nose, left_eye, right_eye, left_ear, right_ear, mid_shoulder, mid_hip | 몸통/척추 |
   | `pole_axis` | (joint_key=None — body_placement 등 폴 축 측정) | 폴 축 |
   | `global` | (joint_key=None — pose_reliability_low 등 영상 전체) | 영상 전체 |

   Note: `mid_shoulder` / `mid_hip` 은 Phase 6 산식이 계산 (skeleton 에 직접 없음). canned string 매핑 시 derived joint key 도 torso 그룹.

2. **deficit_code 별 자연 joint_group 매핑** (deficit 산식상 joint_key 가 사실상 고정):
   | deficit_code | 자연 joint_group | 이유 |
   |---|---|---|
   | `knee_toe_alignment` | `leg` | hip-knee-ankle 각도 — leg only |
   | `clean_lines` | `arm` or `leg` | technique_profile.expects_extension joint 분기 — Phase 6 산식 |
   | `extension` | `torso` | mid_shoulder/mid_hip/neck 라인 — torso only |
   | `posture` | `arm` | 좌우 어깨 z 깊이 차이 — shoulder only (arm 그룹) |
   | `body_placement` | `pole_axis` | mid_hip 의 폴 축 대비 거리 |
   | `pose_reliability_low` | `global` | 영상 전체 신뢰도 |

   **결론:** deficit_code 별 joint_group 이 사실상 1~2 그룹으로 자연 한정. 실제 canned string 조합 = **deficit_code × category (3) × comparisonType (3) × 자연 joint_group (대부분 1, clean_lines 만 2)** = 약 (5+1) × 3 × 3 × 1.2 = **~65 카피** (full Cartesian 아님).

3. **추가 축소:** 카피의 mode-branch 가 차이 작을 시 `comparisonType` 분기 = "prefix 1줄 + 본문 공통" 으로 가능. body_type_interpretation 은 mode 무관 가능 (해석은 같음, recommendation 만 mode 분기). 실 산출:
   - body_type_interpretation: ~18 (deficit × category × joint_group, mode 무관)
   - recommendation: ~18 (deficit × category × joint_group, mode 무관 또는 mode prefix)
   - mode prefix: 3 (mode1 / mode3_first / mode3_progress)
   - **합계: ~39 카피 라인 + 3 mode prefix**

### Initial Canned String Draft (Claude 작성, belle plan 단계 검수)

> 톤 박제: research §10.1 권장 4종 + Sunity 추가 3종 룰 (가능성 언어 / AI 보조 톤 / 부위별 원인 언어). 금지 6종 (§10.3) grep gate 백스톱.

#### dict literal 구조 (Python pseudo-code)

```python
# backend/shared/python/sunity_shared/analysis/copy_templates.py
"""Phase 7 canned string mapping table.

research §10.1 권장 카피 4종 톤 정합 + §10.3 금지 6종 grep gate.
Sunity 추가 톤 룰 3종: 가능성 언어 / AI 보조 도구 톤 / 부위별 원인 언어.
"""

from __future__ import annotations
from typing import Literal

Category = Literal["body_type_allowed", "needs_adjustment", "uncertain"]
JointGroup = Literal["arm", "leg", "torso", "pole_axis", "global"]
ComparisonType = Literal["mode1", "mode3_first", "mode3_progress"]

# mode 별 baseline prefix (D-07-D3)
_MODE_PREFIX = {
    "mode1": "정은지 선수 영상 기준으로 보면",
    "mode3_first": "세계 심사 기준 (IPSF) 으로 보면",
    "mode3_progress": "이전 영상 대비",
}

# 4-key dict: (deficit_code, category, joint_group) → (interpretation, recommendation)
# recommendation 은 _MODE_PREFIX + 본문 으로 mode 분기.
_COPY_TEMPLATES: dict[tuple[str, Category, JointGroup], tuple[str, str]] = {
    # ── knee_toe_alignment (leg) ────────────────────────────────────
    ("knee_toe_alignment", "body_type_allowed", "leg"): (
        "다리 길이 비율 차이로 무릎-발끝 정렬에 작은 차이가 보일 수 있어요.",
        "지금 자세는 체형 범위 안에서 자연스러워 보이네요. 무리해서 발끝을 맞추기보다 무릎 안정성에 집중해 보세요.",
    ),
    ("knee_toe_alignment", "needs_adjustment", "leg"): (
        "다리 라인 정렬이 체형 차이만으로는 설명되기 어려운 흐름이에요.",
        "무릎과 발끝이 한 선 위에 놓이도록 고관절 회전을 먼저 정리하는 게 우선으로 보입니다.",
    ),
    ("knee_toe_alignment", "uncertain", "leg"): (
        "다리 영역에서 가림이나 회전이 있어 AI 가 정렬을 확신하기 어려웠어요.",
        "이 부분은 강사와 함께 측면 각도에서 한 번 더 확인해 보시는 걸 권해요.",
    ),

    # ── clean_lines (arm) ───────────────────────────────────────────
    ("clean_lines", "body_type_allowed", "arm"): (
        "팔 길이 차이로 손 위치가 조금 다르게 보일 수 있어요.",
        "당기는 방향과 어깨 안정성이 유지되고 있으니, 손 모양 자체에 너무 매달리지 마세요.",
    ),
    ("clean_lines", "needs_adjustment", "arm"): (
        "팔 펴짐이 체형 차이만으로는 설명되기 어려운 정도예요.",
        "광배와 전완근으로 끌어내리는 감각을 먼저 잡으면 팔꿈치까지 자연스럽게 펴질 가능성이 있어요.",
    ),
    ("clean_lines", "uncertain", "arm"): (
        "팔 영역 신뢰도가 낮아 AI 가 펴짐 정도를 확신하기 어려웠어요.",
        "강사와 함께 정면 영상에서 팔 라인을 한 번 더 확인해 주세요.",
    ),

    # ── clean_lines (leg) — expects_extension 이 다리인 경우 ──────────
    ("clean_lines", "body_type_allowed", "leg"): (
        "다리 비율 차이로 무릎 펴짐 정도가 다르게 보일 수 있어요.",
        "다리 라인은 현재 체형 범위 안에서 자연스러운 흐름이니, 발끝까지 길게 뻗는 감각에 집중해 보세요.",
    ),
    ("clean_lines", "needs_adjustment", "leg"): (
        "다리 펴짐이 체형 차이로 설명되기 어려운 정도예요.",
        "햄스트링과 종아리 가동성을 점검해 보면 무릎까지 완전히 펴지는 길이 보일 수 있어요.",
    ),
    ("clean_lines", "uncertain", "leg"): (
        "다리 영역에서 가림이 있어 AI 가 펴짐을 확신하기 어려웠어요.",
        "강사와 함께 측면 영상에서 다리 라인을 다시 확인해 주세요.",
    ),

    # ── extension (torso) ───────────────────────────────────────────
    ("extension", "body_type_allowed", "torso"): (
        "몸통 비율 차이로 척추 라인이 조금 다르게 보일 수 있어요.",
        "현재 자세에서는 흉곽 방향과 골반 고정이 우선이고, 척추 곡선 자체에 매달릴 필요는 없어 보이네요.",
    ),
    ("extension", "needs_adjustment", "torso"): (
        "척추와 목 라인이 체형 차이만으로는 설명되기 어렵게 굽어 있어요.",
        "흉곽을 열고 코어로 골반을 받쳐주는 감각을 먼저 잡으면 후굴 라인이 자연스럽게 살아날 가능성이 있어요.",
    ),
    ("extension", "uncertain", "torso"): (
        "몸통 영역에서 가림이 있어 AI 가 척추 라인을 확신하기 어려웠어요.",
        "강사와 함께 측면 영상에서 후굴 라인을 다시 확인해 주세요.",
    ),

    # ── posture (arm = shoulder) ────────────────────────────────────
    ("posture", "body_type_allowed", "arm"): (
        "어깨 너비/골반 비율 차이로 좌우 어깨 깊이가 조금 다르게 보일 수 있어요.",
        "지금 라운드숄더가 체형 범위 안일 가능성이 있으니, 견갑 안정성을 우선으로 가져가세요.",
    ),
    ("posture", "needs_adjustment", "arm"): (
        "좌우 어깨 깊이 차이가 체형 차이만으로는 설명되기 어려워 보여요.",
        "견갑을 끌어내리고 흉곽을 여는 감각을 먼저 정리해 보면 라운드숄더가 풀릴 가능성이 있어요.",
    ),
    ("posture", "uncertain", "arm"): (
        "어깨 영역 신뢰도가 낮아 AI 가 깊이 차이를 확신하기 어려웠어요.",
        "강사와 함께 정면 영상에서 어깨 라인을 다시 확인해 주세요.",
    ),

    # ── body_placement (pole_axis) ──────────────────────────────────
    ("body_placement", "body_type_allowed", "pole_axis"): (
        "체형 차이로 골반의 폴 축 거리가 조금 다르게 보일 수 있어요.",
        "현재 위치는 체형 범위 안에서 자연스러워 보이니, 무리해서 폴에 붙이기보다 골반 고정에 집중해 보세요.",
    ),
    ("body_placement", "needs_adjustment", "pole_axis"): (
        "골반이 폴 축에서 바깥으로 빠지는 흐름이 체형 차이만으로는 설명되기 어려워요.",
        "코어로 골반을 폴 쪽으로 끌어붙이는 감각을 먼저 잡는 게 우선으로 보입니다.",
    ),
    ("body_placement", "uncertain", "pole_axis"): (
        "폴 축 검출 신뢰도가 낮아 AI 가 위치 차이를 확신하기 어려웠어요.",
        "강사와 함께 정면+측면 영상에서 골반 위치를 다시 확인해 주세요.",
    ),

    # ── pose_reliability_low (global) ───────────────────────────────
    ("pose_reliability_low", "body_type_allowed", "global"): (
        # 의미상 발생 거의 없음 (pose_reliability_low = -0.5 → 임계 0.2 초과 → needs)
        # 안전 fallback 만.
        "영상 신뢰도가 일부 낮지만 큰 영향은 없어 보이네요.",
        "조명이 충분하고 가림이 적은 환경에서 한 번 더 촬영해 주시면 분석이 더 정확해질 거예요.",
    ),
    ("pose_reliability_low", "needs_adjustment", "global"): (
        "영상 일부 구간에서 AI 가 자세를 정확히 보기 어려웠어요.",
        "조명·가림·카메라 거리를 조정해 다시 촬영하시면 더 정확한 분석을 받으실 수 있어요.",
    ),
    ("pose_reliability_low", "uncertain", "global"): (
        "영상 전반의 신뢰도가 낮아 AI 분석이 전체적으로 확신을 갖기 어려웠어요.",
        "강사와 함께 영상 품질을 점검하고 재촬영을 고려해 주세요.",
    ),
}

# 6 금지 표현 grep gate (D-07-D2)
# research §10.3 금지 6종 — 카피 작성 시 회귀 차단.
FORBIDDEN_PHRASES: tuple[str, ...] = (
    "프로보다 못합니다",
    "정답 자세가 아닙니다",
    "근육량이 부족합니다",
    "체형이 안 맞습니다",
    "대회 총점",
    "감점입니다",        # "다리 각도 10도 낮아서 감점입니다(코칭 모드에서)" 광범위 차단
)

# Sunity 추가 금지 (memory 박제 정합)
FORBIDDEN_PHRASES_SUNITY: tuple[str, ...] = (
    "박제",               # [[no-baekje-filler]] — 카피 안 박제 단어 금지
    "%일치",              # [[mode3-progress-not-similarity]] — mode3 = 절대 지표 델타
    "유사도",             # 같은 메모
)

# JOINT_LABEL_KO 활용 시 import (skeleton.JOINT_LABEL_KO 8 관절)
from .skeleton import JOINT_LABEL_KO

def render_finding_copy(
    deficit_code: str,
    category: Category,
    joint_group: JointGroup,
    comparison_type: ComparisonType,
) -> tuple[str, str]:
    """(interpretation, recommendation) Korean canned string lookup.

    fallback: 키 미발견 시 generic 카피 + WARNING log (Phase 11 LLM 풍부화 진입 전 graceful).
    """
    key = (deficit_code, category, joint_group)
    pair = _COPY_TEMPLATES.get(key)
    if pair is None:
        # graceful fallback — 키 누락 시 generic 톤 유지
        return (
            "이 부분은 AI 분석 결과예요.",
            "강사와 함께 영상을 한 번 더 확인해 보세요.",
        )
    interp, recom = pair
    # mode prefix 적용 (recommendation 만 — interpretation 은 mode 무관)
    prefix = _MODE_PREFIX.get(comparison_type, "")
    if prefix and not recom.startswith(prefix):
        # baseline 으로 시작하면 자연스러운 한국어 문장 가능
        recom = f"{prefix} {recom}"
    return (interp, recom)
```

### Canned String Coverage Audit

| deficit_code | category | joint_group | 카피 박제? |
|---|---|---|---|
| knee_toe_alignment | body_type_allowed / needs_adjustment / uncertain | leg | 3/3 ✓ |
| clean_lines | × 3 | arm | 3/3 ✓ |
| clean_lines | × 3 | leg | 3/3 ✓ |
| extension | × 3 | torso | 3/3 ✓ |
| posture | × 3 | arm | 3/3 ✓ |
| body_placement | × 3 | pole_axis | 3/3 ✓ |
| pose_reliability_low | × 3 | global | 3/3 ✓ |
| **합계** | | | **21 카피 + 3 mode prefix = 24 line** |

planner 가 dict literal 수정 시 본 표 그대로 검증 가능.

## Schema Extension

### BodyComparisonFinding (4 필드 추가)

Python `body_normalizer.py` `@dataclass(frozen=True) class BodyComparisonFinding`:

```python
@dataclass(frozen=True)
class BodyComparisonFinding:
    # ── 기존 6 필드 (Phase 6 박제) ──
    deficit_code: str
    joint_key: str | None
    measured_value: float
    deduction_score: float
    confidence: float
    body_type_adjusted: bool

    # ── Phase 7 신설 4 필드 ──
    category: Literal["body_type_allowed", "needs_adjustment", "uncertain"]
    phase: str | None = "hold"  # v1 = 'hold' 단일 (D-07-C1)
    body_type_interpretation: str | None = None  # Korean canned string
    recommendation: str | None = None             # Korean canned string

    def __post_init__(self) -> None:
        # 기존 confidence 검증 (Phase 6)
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(...)
        # Phase 7 신설 category enum 검증
        if self.category not in ("body_type_allowed", "needs_adjustment", "uncertain"):
            raise ValueError(
                f"category must be one of (body_type_allowed, needs_adjustment, "
                f"uncertain), got {self.category!r}"
            )
        # phase nullable 허용 (v2 확장 호환)
```

TypeScript `analysis.ts`:

```typescript
export interface BodyComparisonFinding {
  // ── 기존 6 필드 ──
  deficitCode: string;
  jointKey?: string | null;
  measuredValue: number;
  deductionScore: number;
  confidence: number;
  bodyTypeAdjusted: boolean;

  // ── Phase 7 신설 4 필드 ──
  /** 'body_type_allowed' = 체형 허용 차이, 'needs_adjustment' = 개선 필요, 'uncertain' = AI 확신 부족 */
  category: 'body_type_allowed' | 'needs_adjustment' | 'uncertain';
  /** v1 = 'hold' 단일 (D-07-C1). v2 에서 'entry'/'lock'/'transition'/'final_shape' 확장. */
  phase?: string | null;
  /** Korean canned interpretation — Phase 11 LLM 입력 source. */
  bodyTypeInterpretation?: string | null;
  /** Korean canned recommendation — Phase 11 LLM 입력 source. */
  recommendation?: string | null;
}
```

### BodyComparisonReport (2 필드 추가)

Python:
```python
@dataclass(frozen=True)
class BodyComparisonReport:
    # ── 기존 9 필드 (Phase 6) ──
    comparison_type: ComparisonType
    body_normalization_confidence: float
    scale_profile: ScaleProfile | None = None
    findings: list[BodyComparisonFinding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reference_motion_id: str | None = None
    reference_athlete_name: str | None = None
    previous_analysis_id: str | None = None
    used_reference_fallback: bool = False

    # ── Phase 7 신설 2 필드 ──
    do_not_over_correct: list[str] = field(default_factory=list)
    recommended_focus: list[str] = field(default_factory=list)
```

TypeScript:
```typescript
export interface BodyComparisonReport {
  // ── 기존 필드 (Phase 6) ──
  // …

  // ── Phase 7 신설 2 필드 ──
  /** body_type_allowed 분류 finding 의 카피 aggregate. 결과 화면 "체형 허용 차이" 박스 source. */
  doNotOverCorrect: string[];
  /** needs_adjustment + uncertain 분류 finding 의 카피 aggregate. "개선 필요" 박스 source. */
  recommendedFocus: string[];
}
```

### Uncertain 처리 (Discretion 결정)

**Decision 1: `recommendedFocus[]` 통합 권장.** 이유:
- `do_not_over_correct` / `recommended_focus` 두 박스 = 결과 화면 UX 정합 (research §9 schema 그대로)
- uncertain 카피 톤이 "강사 확인 권유" → 의미상 "다음 작업" 박스 (`recommendedFocus`) 에 자연 fit
- 별도 `uncertainFindings[]` 배열 신설은 frontend 화면 분기 복잡도 증가 + Phase 12 책임 폭증
- 단, per-finding `category='uncertain'` 은 유지 → Phase 12 가 화면 분기 시 (회색 / 강조 / 강사 확인) 세분 가능. frontend 가 finding 단위로 카테고리 확인 가능.

**구체적 분배 룰:**

| category | 카피 분배 |
|---|---|
| `body_type_allowed` | `do_not_over_correct[]` 에 append |
| `needs_adjustment` | `recommended_focus[]` 에 append |
| `uncertain` | `recommended_focus[]` 에 append (강사 확인 권유 톤) |

**mode3_first 단독 분류 룰 변형 (D-07-Discretion):**

mode3_first 의 경우 Gemini fallback (`used_reference_fallback=True`) 으로 reference 매칭 실패 시 Page 9 절대 트랙 단독 적용 (Phase 6 D-06-B1). 본 path 의 finding 분류:

- `body_type_adjusted=True` 인 finding 도 정규화 source 가 정은지 reference 가 아닌 Page 9 절대 기준 → "체형 허용" 의미가 약함. **권장: mode3_first + used_reference_fallback=True → 모든 finding 을 `uncertain` 으로 demotion.** 카피 톤 = "이 동작은 등록된 기준이 부족해 AI 분석 신뢰도가 낮아요. 강사 확인을 권유합니다."

위 룰을 `classify_findings()` 내부 D-07-A2 게이트 OR 확장:
```python
def classify_findings(findings, body_normalization_confidence, comparison_type, *, used_reference_fallback=False):
    is_low_confidence_global = (
        body_normalization_confidence < 0.5
        or (comparison_type == "mode3_first" and used_reference_fallback)
    )
    for f in findings:
        if is_low_confidence_global or f.confidence < 0.5:
            category = "uncertain"
        elif not f.body_type_adjusted:
            category = "uncertain"
        elif abs(f.deduction_score) <= 0.2:
            category = "body_type_allowed"
        else:
            category = "needs_adjustment"
```

## Mode Branch Carry-over

### Pattern Source (Phase 12.5 박제 정합)

`backend/shared/python/sunity_shared/analysis/assemble.py:25-34`:
```python
_DIMENSION_BASELINES_MODE1 = {
    "angle": "정은지 측정값 + IPSF 실행 기준 참고",
    "line": "정은지 측정값 + 신전 완성도 (IPSF 실행 기준 참고)",
    "stability": "hold 구간 떨림 (절대 지표)",
}
_DIMENSION_BASELINES_MODE3 = {
    "angle": "이전 영상 대비 관절 각도 일관성",
    "line": "신전 완성도 (실행 기준 참고)",
    "stability": "hold 구간 떨림 (절대 지표)",
}
```

### Phase 7 적용

Phase 12.5 는 2-mode 분기 (mode1 / mode3) 였지만 Phase 6 W1 이 3 ComparisonType 으로 박제 — Phase 7 도 3 분기:

```python
_MODE_PREFIX = {
    "mode1": "정은지 선수 영상 기준으로 보면",
    "mode3_first": "세계 심사 기준 (IPSF) 으로 보면",
    "mode3_progress": "이전 영상 대비",
}
```

**원칙:** `body_type_interpretation` 은 mode 무관 (현상 해석은 같음). `recommendation` 만 mode prefix 추가 (다음 행동의 reference point 가 mode 별로 다름).

**근거 메모리:** `[[mode3-progress-not-similarity]]` — mode3 = 절대 지표 델타. "유사도" / "%일치" 표현 금지 → grep gate 에 포함 (`FORBIDDEN_PHRASES_SUNITY`).

## Common Pitfalls

### Pitfall 1: `dataclasses.replace()` 우회 패턴

**What goes wrong:** Phase 6 박제 R8 (extra_warnings injection) 와 동일 함정. 신설 4 필드를 사후 replace 로 채우는 코드 패턴은 frozen dataclass 검증을 회피 → category enum 검증 누락 가능.

**Why it happens:** 기존 `BodyComparisonFinding` 인스턴스를 mutate 하고 싶은 자연 충동.

**How to avoid:** `classify_findings()` 가 **새 BodyComparisonFinding 인스턴스** 만들어 반환. 단위 test 가 `id()` 비교 또는 `replace` 호출 grep 으로 회귀 차단.

### Pitfall 2: 빈 `needs_adjustment` 리스트의 UX 처리 누락

**What goes wrong:** 5 IPSF deficit 가 모두 `-0.2` → `body_type_adjusted=True` 인 한 모두 `body_type_allowed`. `pose_reliability_low` 가 없으면 `recommended_focus[]` 가 항상 빈 리스트 → 결과 화면이 "다음 작업" 박스 비어 보임.

**Why it happens:** v1 IPSF deficit 산식이 -0.2 단일 + -0.5 (pose_reliability_low) 만 출력. Phase 8 / Phase 13 통합 전엔 deficit code 다양성 부족.

**How to avoid:** frontend Phase 12 화면 분기 책임 (백엔드는 빈 리스트 그대로 출력). 카피 fallback: "현재 영상에서 즉시 보정할 항목이 명확히 보이지 않아요. 강사와 함께 다음 단계를 정해보세요." Phase 12 책임 박제.

**Warning signs:** sweep_rtmw_20260603_1409 5 영상 중 4 영상에서 `recommended_focus=[]` 산출 시 v1 limitation 박제 정합 — 정상 동작.

### Pitfall 3: comparisonType 누락된 canned string 작성

**What goes wrong:** dict literal 키에서 `comparison_type` 빠뜨려서 mode1 / mode3 카피 같음 → mode1 ("정은지 선수 기준") 톤이 mode3_progress ("이전 영상 대비") 에 그대로 노출 → UX 어색.

**Why it happens:** "interpretation 은 mode 무관" 원칙을 recommendation 에도 잘못 적용.

**How to avoid:** Pattern 1 (`render_finding_copy`) 에서 mode prefix 명시적 prepend. 단위 test = 3 mode × 1 finding 호출 결과 prefix 다름 검증.

### Pitfall 4: 6 금지 표현 grep gate 통과 후 회귀

**What goes wrong:** 신규 canned string 추가 시 grep gate 통과 → CI 통과 → belle 검수 단계 못 잡으면 production 진입.

**Why it happens:** "감점" 같은 표현은 generic 단어 (gate 잡지만 false positive 가능). "박제" 같은 단어는 generic 한국어 명사 — 신규 카피 작성자가 의미 모르고 사용.

**How to avoid:** (1) grep gate 단위 test 가 `_COPY_TEMPLATES` 전체 + `_MODE_PREFIX` + (필요 시) `assemble.py` 의 모든 `str` literal iterate. (2) belle plan-review 단계에서 카피 검수 checklist 박제. (3) 신규 deficit 추가 plan 의 verification step 에 grep gate test 명시.

### Pitfall 5: TS / Python lockstep 부분 commit

**What goes wrong:** Python 만 4 필드 추가 commit + TS / contract.md 별도 commit → 중간 시점에 frontend 빌드 실패 또는 TypeError.

**Why it happens:** Phase 6 박제 패턴 잊고 phase 진입.

**How to avoid:** **단일 atomic commit** — `body_normalizer.py` + `analysis.ts` + `docs/contract.md §8` 3 파일 한 commit. Phase 6 commit `116f400` / `a444726` 패턴 참조.

### Pitfall 6: `pose_reliability_low` 가 `body_type_allowed` 로 분류

**What goes wrong:** 임계 0.5 또는 절대값 비교 누락 시 `abs(-0.5) <= 0.5` → `body_type_allowed`. "영상 신뢰도 낮음" 이 "체형 허용 차이" 로 박제됨 → 의미 오류.

**Why it happens:** D-07-A1 의 임계 적용 시 `<=` vs `<` 혼동.

**How to avoid:** 임계 `<= 0.2` 박제 (D-07-A1 그대로). 0.5 시도 시 위 위양성 발생. 단위 test fixture 에 `deduction_score=-0.5` 인 finding 이 `needs_adjustment` 로 분류되는 검증 추가.

## Code Examples

### Example 1: `classify_findings()` 구현 (Phase 7 본체)

```python
# backend/shared/python/sunity_shared/analysis/body_normalizer.py 안에 추가
# Source: 본 RESEARCH.md §"Architecture Patterns" + §"Schema Extension"

from typing import Literal
from .copy_templates import render_finding_copy

# deficit_code → 자연 joint_group 매핑 (§"Canned Copy Mapping Table" 박제)
_DEFICIT_TO_GROUP: dict[str, str] = {
    "knee_toe_alignment": "leg",
    # clean_lines 는 finding.joint_key 로 분기 (arm vs leg)
    "extension": "torso",
    "posture": "arm",
    "body_placement": "pole_axis",
    "pose_reliability_low": "global",
}

# 8 joint → joint_group 매핑 (clean_lines 의 joint_key 분기용)
_JOINT_TO_GROUP: dict[str, str] = {
    "left_elbow": "arm", "right_elbow": "arm",
    "left_shoulder": "arm", "right_shoulder": "arm",
    "left_wrist": "arm", "right_wrist": "arm",
    "left_hip": "leg", "right_hip": "leg",
    "left_knee": "leg", "right_knee": "leg",
    "left_ankle": "leg", "right_ankle": "leg",
}

CATEGORY_GATE = 0.2  # D-07-A1
CATEGORY_CONF_GATE = 0.5  # D-07-A2 (Phase 6 D-06-U1 정합)


def _resolve_joint_group(finding: BodyComparisonFinding) -> str:
    """deficit_code 기본 group, clean_lines 는 joint_key 로 분기."""
    if finding.deficit_code == "clean_lines" and finding.joint_key:
        return _JOINT_TO_GROUP.get(finding.joint_key, "arm")
    return _DEFICIT_TO_GROUP.get(finding.deficit_code, "global")


def classify_findings(
    findings: list[BodyComparisonFinding],
    body_normalization_confidence: float,
    comparison_type: ComparisonType,
    *,
    used_reference_fallback: bool = False,
) -> tuple[list[BodyComparisonFinding], list[str], list[str]]:
    """Phase 7 분류 + 카피. D-07-A1 + D-07-A2 + D-07-D3.

    Pure function — numpy / boto3 / network 무관. 단위 test 가능.

    Args:
        findings: Phase 6 measure_ipsf_absolute_deficits() 출력.
        body_normalization_confidence: report-level confidence.
        comparison_type: mode 분기 (mode1 / mode3_first / mode3_progress).
        used_reference_fallback: mode3_first Gemini fallback 신호 (D-07-Discretion).

    Returns:
        (classified_findings, do_not_over_correct, recommended_focus)
    """
    is_low_global = (
        body_normalization_confidence < CATEGORY_CONF_GATE
        or (comparison_type == "mode3_first" and used_reference_fallback)
    )

    classified: list[BodyComparisonFinding] = []
    do_not_over_correct: list[str] = []
    recommended_focus: list[str] = []

    for f in findings:
        # D-07-A2 게이트 — OR 합집합
        if (
            is_low_global
            or f.confidence < CATEGORY_CONF_GATE
            or not f.body_type_adjusted
        ):
            category = "uncertain"
        elif abs(f.deduction_score) <= CATEGORY_GATE:
            category = "body_type_allowed"
        else:
            category = "needs_adjustment"

        group = _resolve_joint_group(f)
        interp, recom = render_finding_copy(
            f.deficit_code, category, group, comparison_type
        )

        new_finding = BodyComparisonFinding(
            deficit_code=f.deficit_code,
            joint_key=f.joint_key,
            measured_value=f.measured_value,
            deduction_score=f.deduction_score,
            confidence=f.confidence,
            body_type_adjusted=f.body_type_adjusted,
            category=category,
            phase="hold",  # D-07-C1 v1 단일
            body_type_interpretation=interp,
            recommendation=recom,
        )
        classified.append(new_finding)

        # 분배 (D-07-B3 + Decision 1)
        if category == "body_type_allowed":
            do_not_over_correct.append(recom)
        else:  # needs_adjustment 또는 uncertain — recommended_focus 통합
            recommended_focus.append(recom)

    return classified, do_not_over_correct, recommended_focus
```

### Example 2: `compare_body_profiles()` 호출 wiring

```python
# backend/shared/python/sunity_shared/analysis/body_normalizer.py
# 기존 compare_body_profiles 함수 안에서 — measure_ipsf_absolute_deficits 호출 직후, Report 조립 직전.

# 5) IPSF deficit 측정 (gate 무관 — confidence 낮으면 raw 좌표만)
findings = measure_ipsf_absolute_deficits(
    angles,
    technique_profile,
    normalized_keypoints=normalized_keypoints,
    pose_frames=pose_frames,
)

# 5.5) [Phase 7 신설] 분류 + 카피
classified_findings, do_not_over_correct, recommended_focus = classify_findings(
    findings,
    body_normalization_confidence=confidence,
    comparison_type=comparison_type,
    used_reference_fallback=used_reference_fallback,
)

# 6) extra_warnings merge (Phase 6 R8)
# …

# 7) BodyComparisonReport 조립 — Phase 7 신설 2 필드 주입
return BodyComparisonReport(
    comparison_type=comparison_type,
    body_normalization_confidence=confidence,
    scale_profile=scale_profile,
    findings=classified_findings,  # Phase 7 — 신설 4 필드 포함
    warnings=merged_warnings,
    reference_motion_id=reference_motion_id,
    reference_athlete_name=reference_athlete_name,
    previous_analysis_id=previous_analysis_id,
    used_reference_fallback=used_reference_fallback,
    do_not_over_correct=do_not_over_correct,  # Phase 7 신설
    recommended_focus=recommended_focus,        # Phase 7 신설
)
```

### Example 3: 6 금지 표현 grep gate 단위 test

```python
# backend/tests/phase07/test_copy_templates_no_forbidden.py
# Source: D-07-D2 grep gate 박제

import pytest
from sunity_shared.analysis.copy_templates import (
    _COPY_TEMPLATES,
    _MODE_PREFIX,
    FORBIDDEN_PHRASES,
    FORBIDDEN_PHRASES_SUNITY,
)


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES + FORBIDDEN_PHRASES_SUNITY)
def test_canned_strings_have_no_forbidden_phrase(phrase: str) -> None:
    """research §10.3 6 금지 + Sunity 추가 3종 → 모든 canned string 안 미발견 검증."""
    violations: list[str] = []
    for key, (interp, recom) in _COPY_TEMPLATES.items():
        if phrase in interp:
            violations.append(f"{key} interpretation: {interp!r}")
        if phrase in recom:
            violations.append(f"{key} recommendation: {recom!r}")
    for mode, prefix in _MODE_PREFIX.items():
        if phrase in prefix:
            violations.append(f"_MODE_PREFIX[{mode!r}]: {prefix!r}")

    assert not violations, (
        f"금지 표현 {phrase!r} 가 canned string 에서 발견됨:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
```

### Example 4: `_dataclass_to_camel_case_dict` 자동 변환 검증

```python
# backend/tests/phase07/test_dataclass_to_camel_case_dict_phase7.py
# Source: Phase 6 C8 박제 자동 활용 — 신설 필드 코드 변경 0 검증

def test_phase7_new_fields_camel_case_automatic() -> None:
    """Phase 6 _dataclass_to_camel_case_dict 가 신설 4+2 필드 자동 변환."""
    from backend.functions.pipeline.app import _dataclass_to_camel_case_dict

    finding = BodyComparisonFinding(
        deficit_code="knee_toe_alignment",
        joint_key="left_knee",
        measured_value=120.0,
        deduction_score=-0.2,
        confidence=0.85,
        body_type_adjusted=True,
        category="body_type_allowed",
        phase="hold",
        body_type_interpretation="다리 길이 비율 차이로...",
        recommendation="정은지 선수 영상 기준으로 보면 지금 자세는...",
    )
    report = BodyComparisonReport(
        comparison_type="mode1",
        body_normalization_confidence=0.85,
        findings=[finding],
        do_not_over_correct=["정은지 선수 영상 기준으로..."],
        recommended_focus=[],
    )
    out = _dataclass_to_camel_case_dict(report)

    assert "doNotOverCorrect" in out
    assert "recommendedFocus" in out
    assert out["findings"][0]["category"] == "body_type_allowed"
    assert out["findings"][0]["phase"] == "hold"
    assert out["findings"][0]["bodyTypeInterpretation"]
    assert out["findings"][0]["recommendation"]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Phase 7 정의가 "체형 허용 차이 / 개선 필요 차이 / 감점 분리" (3 케이스 중 1개가 "감점") — research 01 §10 다이어그램 | "body_type_allowed / needs_adjustment / uncertain" (감점 카테고리 → uncertain 으로 재정의) | 2026-06-08 CONTEXT.md 박제 시 | 감점 (= "needs_adjustment") 과 신뢰도 낮음 (= "uncertain") 을 분리하는 게 UX 정직성 우위. research §10 다이어그램은 prior art. |
| 단순 단일 hold 모먼트 분석 | v1 = hold 단일 + v2 (Phase 8 / Plan 13 Gemini key_moments) 에서 entry/lock/transition/final_shape 확장 | D-07-C1 박제 (2026-06-08) | schema 의 `phase: str \| None` 필드가 v2 호환. v1 plan 단순화 + v2 자연 path. |
| Cerebras LLM 으로 동적 카피 생성 | Phase 7 = 캔드 박제, Phase 11 LLM 풍부화 | D-07-B1 박제 | Cerebras 키 미설정 환경 graceful (FEED-03 success criteria 5 정합) + 분석 객관성 박제 (`[[analysis-objectivity-no-human-scores]]`). |
| `comparisonType` 2 케이스 (mode1 vs mode3) | 3 케이스 + `usedReferenceFallback` boolean sibling | Phase 6 W1 박제 (2026-06-08) | Phase 7 mode-branch carry-over 도 3 케이스 정합. |

**Deprecated/outdated:**

- "체형 허용 차이 / 개선 필요 차이 / 감점" 3 케이스 분류는 research §10 prior art. 본 phase 는 "체형 허용 / 개선 필요 / uncertain (= AI 확신 부족)" 으로 재정의. 감점은 deduction_score 가 그대로 들고 다님 (필드 보존).
- "phase: 'entry' | 'lock' | 'transition' | 'final_shape' | 'hold'" 5 enum literal — research §9 prior art. v1 schema 는 `phase: str | None` nullable string (v2 enum literal 확장 호환).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 5 IPSF deficit 의 `deduction_score` 는 산식상 `-0.2` 만 출력 (`pose_reliability_low` 만 `-0.5`) | §Classification Rule Calibration | 산식 변경 시 임계 0.2 의 분리력 영향. Phase 8/13 통합 시 plan 단계 재확인. [VERIFIED: backend/shared/python/sunity_shared/analysis/body_normalizer.py:944-1110] |
| A2 | Phase 11 (CoachCommentHook + Cerebras coach_writer) 가 canned string 을 LLM 시스템 프롬프트 input 으로 사용 | §Don't Hand-Roll | Phase 11 plan 진입 시 canned string 형식 (`tuple[str, str]` 또는 `dict[str, str]`) 재검토. [ASSUMED — Phase 11 plan 미작성] |
| A3 | sweep_rtmw_20260603_1409 5 영상의 `body_normalization_confidence` 분포가 0.5 임계 게이트 빈도 1/6 (belle 박제 정신 정합) | §"Sweep Data Analysis" 의 위험 박제 | 분포 측정 안 됨 (sweep report 가 confidence 산출 전 시점). 실 데이터 측정 plan-execution 단계에서 검증. [ASSUMED — sweep_rtmw 데이터 미산출 시점] |
| A4 | `_dataclass_to_camel_case_dict` 5-case helper 가 신설 4+2 필드 자동 변환 | §Don't Hand-Roll + §Code Examples | Phase 6 C8 박제 검증 완료 (test_dataclass_to_camel_case_dict.py 4 case 통과). 신설 필드 모두 scalar / list[str] / Literal string. [VERIFIED: Phase 6 close-out 5 commits] |
| A5 | `firestore_admin._validate_flat_dict_no_nested_array` 가 신설 list[str] 두 배열 통과 | §Don't Hand-Roll | Phase 6 W5 박제 — `list[str]` (warnings) + `list[dict-of-scalars-only]` (findings) 박제. 신설 두 list 도 `list[str]` 동일 패턴. [VERIFIED: Phase 6 W5 patch] |
| A6 | `userAnalyses.normalize()` 가 신설 4+2 필드 부재 시 graceful default | §Runtime State Inventory | TS interface 의 두 list 가 `string[]` non-optional → frontend normalize() 에서 default `[]` 처리 필요 (Phase 7 frontend 작업 또는 Phase 12 책임). [ASSUMED — Phase 12 plan 미작성] |
| A7 | 6 금지 표현 + Sunity 추가 3종 grep gate 가 false positive 거의 없음 ("감점" 한국어 generic 단어 위험) | §Pitfall 4 + §Code Examples Test 3 | "감점" 같은 한국어 단어는 일반 명사 — Phase 13 보완 운동 카피 등에서 정당히 사용 가능. **본 grep gate scope 는 Phase 7 canned string 모듈만** 으로 한정 권장. Phase 13/11 캔드는 별도 grep 룰. [ASSUMED — Phase 11/13 plan 미작성 시점] |
| A8 | mode3_first + `used_reference_fallback=True` → 모든 finding `uncertain` demotion 룰이 UX 정합 | §Schema Extension Decision 1 | belle 검수 시점에 본 룰 재검토 가능. plan 단계에서 belle confirmation 권장. [ASSUMED — UX 정합 추정] |

## Open Questions

1. **mode3_first + `used_reference_fallback=True` 카피 fallback 형식**
   - What we know: Phase 6 가 fallback 신호 박제. Page 9 절대 트랙 단독 path.
   - What's unclear: 본 path 의 canned string 톤 — 모든 finding `uncertain` 으로 강제 demotion 시 결과 화면이 빈약. "이 동작은 등록된 기준 부족, 강사 확인 권유" 단일 메시지 출력 vs 신뢰도 낮은 분류 그대로 출력.
   - Recommendation: planner 가 belle 검수 단계에서 결정. v1 박제는 **단일 fallback 메시지** + `uncertain` 분류 강제 권장 (정직성 우위).

2. **빈 `recommended_focus[]` 결과 화면 fallback 카피**
   - What we know: v1 deficit code 산식상 `needs_adjustment` 빈 리스트 가능성 높음.
   - What's unclear: 결과 화면 분기 — 빈 박스 숨김 vs "보정 우선순위 없음" 카피.
   - Recommendation: Phase 12 책임 박제. Phase 7 백엔드 출력은 빈 리스트 그대로. Phase 12 frontend plan 에서 belle 검수 후 결정.

3. **`body_type_interpretation` 의 Phase 11 LLM 입력 형식**
   - What we know: D-07-B1 박제 — Phase 11 이 캔드 → 자연어 풍부화.
   - What's unclear: 본 phase 의 canned string 이 Phase 11 시스템 프롬프트에 그대로 inline vs 별도 metadata 로 전달.
   - Recommendation: Phase 11 plan 진입 시 결정. Phase 7 의 schema 는 per-finding 4 필드 박제 (Phase 11 에 충분한 input source).

4. **Phase 12 frontend `userAnalyses.normalize()` 의 default 처리**
   - What we know: TS interface 의 두 list 는 `string[]` non-optional.
   - What's unclear: Phase 7 백엔드 변경 시점 vs frontend 갱신 시점 misalignment 시 (Firestore doc 에 두 필드 없음) frontend 동작.
   - Recommendation: TS interface 두 list 를 `string[]` (non-optional) 으로 박제 + `normalize()` 안에서 `do_not_over_correct ?? []` default. plan 의 frontend 작업 task 에 명시.

## Environment Availability

> Skip — Phase 7 은 백엔드 pure-Python 작업만. 신규 외부 의존성 0. 기존 Python 3.12 / pytest / numpy / dataclasses 환경 그대로 사용.

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python 3.12 | classify_findings | ✓ | 3.12 | — |
| pytest >=8,<9 | 단위 test | ✓ | 8.x | — |
| frozen dataclass | schema 확장 | ✓ | stdlib | — |

**Missing dependencies:** none.

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest >=8,<9 |
| Config file | `backend/requirements-dev.txt` + `backend/pytest.ini` (Phase 6 박제 정합) |
| Quick run command | `cd /Users/kimtaesung/Dev/SunityMotion && pytest backend/tests/phase07/ -x` |
| Full suite command | `cd /Users/kimtaesung/Dev/SunityMotion && pytest backend/tests/ -x` |

### Phase Requirements → Test Map (4 success criteria, ROADMAP §Phase 7)

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| Phase 7 SC #1 | `BodyComparisonFinding[]` 이 category 별로 산출 (allowed / needs / uncertain) | unit | `pytest backend/tests/phase07/test_classify_findings.py -x` | ❌ Wave 0 |
| Phase 7 SC #1 | `phase` 필드 nullable + v1 default 'hold' | unit | `pytest backend/tests/phase07/test_classify_findings.py::test_phase_default_hold -x` | ❌ Wave 0 |
| Phase 7 SC #2 | `doNotOverCorrect` / `recommendedFocus` 배열 출력에 포함 | unit | `pytest backend/tests/phase07/test_classify_findings.py::test_aggregate_lists_populated -x` | ❌ Wave 0 |
| Phase 7 SC #2 | TS / Python schema 1:1 (4+2 필드 lockstep) | unit | `pytest backend/tests/phase07/test_body_comparison_report_phase7_lockstep.py -x` | ❌ Wave 0 |
| Phase 7 SC #3 | confidence < 0.5 → uncertain demotion (OR 합집합) | unit | `pytest backend/tests/phase07/test_classify_findings.py::test_low_confidence_demotion -x` | ❌ Wave 0 |
| Phase 7 SC #4 | 6 금지 표현 + Sunity 추가 3 grep gate | unit | `pytest backend/tests/phase07/test_copy_templates_no_forbidden.py -x` | ❌ Wave 0 |
| Phase 7 통합 | `compare_body_profiles()` 가 신설 2 필드 정상 출력 | integration | `pytest backend/tests/phase07/test_compare_body_profiles_phase7_integration.py -x` | ❌ Wave 0 |
| Phase 7 통합 | `_dataclass_to_camel_case_dict` 자동 변환 | unit | `pytest backend/tests/phase07/test_dataclass_to_camel_case_dict_phase7.py -x` | ❌ Wave 0 |

### Test Fixtures (Wave 0 사전 박제 필수)

```
backend/tests/phase07/fixtures/
├── fixture_classification_allowed.json
│     # body_type_adjusted=True, deduction_score=-0.2, confidence=0.85
│     # body_normalization_confidence=0.85
│     # 기대: category='body_type_allowed', recommendation→do_not_over_correct[]
│
├── fixture_classification_needs.json
│     # body_type_adjusted=True, deduction_score=-0.5 (pose_reliability_low), confidence=0.9
│     # body_normalization_confidence=0.85
│     # 기대: category='needs_adjustment', recommendation→recommended_focus[]
│
├── fixture_classification_uncertain_raw.json
│     # body_type_adjusted=False (raw 좌표), deduction_score=-0.2, confidence=0.85
│     # body_normalization_confidence=0.85
│     # 기대: category='uncertain' (D-07-A1 정규화 OFF → 항상 uncertain)
│
├── fixture_classification_uncertain_low_conf.json
│     # body_type_adjusted=True, deduction_score=-0.2, confidence=0.3 (< 0.5)
│     # body_normalization_confidence=0.85
│     # 기대: category='uncertain' (개별 finding confidence 게이트)
│
├── fixture_classification_uncertain_global_low.json
│     # body_type_adjusted=True, deduction_score=-0.2, confidence=0.85
│     # body_normalization_confidence=0.3 (< 0.5)
│     # 기대: 모든 finding category='uncertain' (report-level demotion)
│
├── fixture_classification_mode3_first_fallback.json
│     # comparison_type='mode3_first', used_reference_fallback=True
│     # 모든 finding body_type_adjusted=True, deduction_score=-0.2, confidence=0.85
│     # body_normalization_confidence=0.85
│     # 기대: 모든 finding category='uncertain' (Decision 1 — Page 9 단독 path)
│
└── fixture_canned_no_forbidden_full.json
      # _COPY_TEMPLATES + _MODE_PREFIX 전체 dict literal
      # 기대: 6 금지 + Sunity 3 표현 0개 발견
```

### Test Specifications (data + expected output)

**fixture_classification_allowed**:
- Input: 1 finding (`knee_toe_alignment`, `body_type_adjusted=True`, `deduction_score=-0.2`, `confidence=0.85`), `body_normalization_confidence=0.85`, `comparison_type='mode1'`
- Expected: classified_findings[0].category = 'body_type_allowed', do_not_over_correct[0] starts with "정은지 선수 영상 기준으로 보면", recommended_focus = []

**fixture_classification_needs**:
- Input: 1 finding (`pose_reliability_low`, `body_type_adjusted=True`, `deduction_score=-0.5`, `confidence=0.9`), `body_normalization_confidence=0.85`, `comparison_type='mode1'`
- Expected: classified_findings[0].category = 'needs_adjustment', recommended_focus[0] non-empty, do_not_over_correct = []

**fixture_classification_uncertain_raw**:
- Input: 1 finding (`extension`, `body_type_adjusted=False`, `deduction_score=-0.2`, `confidence=0.85`), `body_normalization_confidence=0.85`
- Expected: category = 'uncertain', recommendation contains "강사" or "확인"

**fixture_classification_uncertain_low_conf**:
- Input: finding.confidence=0.3, others valid
- Expected: category = 'uncertain'

**fixture_classification_uncertain_global_low**:
- Input: body_normalization_confidence=0.3, finding 자체는 valid
- Expected: 모든 finding category = 'uncertain'

**fixture_classification_mode3_first_fallback**:
- Input: comparison_type='mode3_first', used_reference_fallback=True, finding 자체는 valid
- Expected: 모든 finding category = 'uncertain'

**fixture_canned_no_forbidden_full**:
- Input: `_COPY_TEMPLATES` + `_MODE_PREFIX` 전체 iterate
- Expected: 0 violations across 9 forbidden phrases (6 research + 3 Sunity)

### Sampling Rate

- **Per task commit:** `pytest backend/tests/phase07/ -x` (Phase 7 격리 < 10 초 예상)
- **Per wave merge:** `pytest backend/tests/ -x` (전체 phase06 136 + phase07 ~25 = ~160 pass / 1 skip)
- **Phase gate:** 전체 backend 테스트 green + `tsc --noEmit` clean (3-way lockstep 검증)

### Wave 0 Gaps

- [ ] `backend/tests/phase07/__init__.py` — phase07 디렉토리 표시
- [ ] `backend/tests/phase07/conftest.py` — Phase 6 conftest 패턴 정합 (fixture loader)
- [ ] `backend/tests/phase07/fixtures/_factory.py` — JSON 파일 → BodyComparisonFinding 로더 (Phase 6 `load_single_frames` 패턴)
- [ ] 7 fixture JSON 파일 (위 §"Test Fixtures" 박제)
- [ ] `test_classify_findings.py` — 8 단위 test (allowed / needs / uncertain × 3 case + phase default + aggregate)
- [ ] `test_copy_templates_no_forbidden.py` — 9 parametrize (6 research + 3 Sunity 금지 표현)
- [ ] `test_copy_templates_render.py` — 21 카피 매핑 + 3 mode prefix + fallback path
- [ ] `test_body_comparison_report_phase7_lockstep.py` — TS / Python field 1:1 (dataclass `__post_init__` validator + Literal enum)
- [ ] `test_compare_body_profiles_phase7_integration.py` — Phase 6 호출 안에서 분류 + 카피 통합
- [ ] `test_dataclass_to_camel_case_dict_phase7.py` — 신설 필드 자동 변환

## Security Domain

> 본 phase 는 사용자 input 처리 X (Phase 6 가 pose_frames / profiles 처리 박제). canned string dict literal 은 정적 — injection 표면 0. 단, `firestore_admin._validate_flat_dict_no_nested_array` (Phase 6 W5 박제) 가 backstop.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | 본 phase 에 user input 없음 |
| V3 Session Management | no | — |
| V4 Access Control | no | Firestore rules + Firebase Auth (Phase 6 박제) |
| V5 Input Validation | yes | `dataclass __post_init__` Literal enum 검증 (category / phase / comparison_type) |
| V6 Cryptography | no | 본 phase 무관 |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| LLM prompt injection via canned string | T (Tampering) | 본 phase canned string = 정적 dict literal — injection 표면 0. Phase 11 LLM 풍부화 시 belle 가 시스템 프롬프트 분리 박제 (Phase 11 책임). |
| Firestore nested-array DoS (저장 시 frontend 깨짐) | D (Denial of Service) | `_validate_flat_dict_no_nested_array` (Phase 6 W5) — list[str] 두 신설 배열 통과 검증 + list[dict-of-scalars-only] (findings) 통과. |
| dataclass frozen mutation 우회 | T | `__post_init__` Literal enum 검증 (`category` not in 3 enum → ValueError). `replace()` 우회 시도 시 단위 test grep 가 회귀 차단. |
| 금지 표현 production 진입 | I (Information disclosure — 사용자 부정적 경험) | grep gate 단위 test (D-07-D2) — 9 금지 표현 (6 research + 3 Sunity). belle plan-review 검수 추가. |

## Implementation Risks + Landmines

> 박제 가능 위험 목록 — planner 가 plan 단계에 mitigation task 박제.

1. **임계 0.2 가 5 영상에서 `needs_adjustment` 0건 산출 위험**
   - **현상:** 5 IPSF deficit 모두 `-0.2` → 정규화 ON 인 한 모두 `body_type_allowed`. `pose_reliability_low` 없으면 `needs_adjustment=[]`.
   - **Mitigation:** v1 limitation 박제. frontend Phase 12 가 빈 박스 친화적 카피 또는 박스 숨김 분기. Phase 8 / Phase 13 통합 후 자연 해결.

2. **mode 분기 카피 폭발 가능성**
   - **현상:** D-07-D3 + comparisonType 3 케이스 → 카피 21 line × 3 mode = 63 본문 또는 prefix-only 21 line + 3 prefix.
   - **Mitigation:** prefix-only 패턴 권장 (본 RESEARCH.md §"Canned Copy Mapping Table" 박제). interpretation 은 mode 무관, recommendation 만 mode prefix.

3. **joint_group 매핑 정확도 (clean_lines 의 joint_key 분기)**
   - **현상:** Phase 6 산식상 `clean_lines.joint_key` 는 `None` (technique_profile.expects_extension 의 평균 각도 — 단일 관절 귀속 X). 본 RESEARCH.md 의 `_resolve_joint_group` 가 fallback `arm` 박제.
   - **Mitigation:** `clean_lines.joint_key=None` 경우 — technique_profile 의 expects_extension joint 들의 자연 그룹 (대부분 arm) 으로 fallback. Phase 6 산식 재검토 시 분기 조정.

4. **Cerebras LLM 미사용 박제 (Phase 11 후속)**
   - **현상:** Phase 7 = 캔드 전용. LLM 호출 0.
   - **Mitigation:** Phase 11 plan 진입 시 canned string → LLM 풍부화 wiring 박제. 본 phase 의 schema (`body_type_interpretation` / `recommendation` per-finding) 가 Phase 11 input source.

5. **TS / Python lockstep 부분 commit 위험**
   - **현상:** Phase 6 close-out 5 commits 박제 패턴 (atomic) — Phase 7 plan 의 commit unit 박제 필수.
   - **Mitigation:** plan 의 commit unit = 1 commit per 1 task (4+2 필드 schema 갱신 = 1 atomic commit, classify_findings 추가 = 1 commit, copy_templates 신규 모듈 = 1 commit, 등).

6. **grep gate false positive ("감점" 한국어 generic 단어)**
   - **현상:** "감점" 이 Phase 13 보완 운동 카피 등 다른 도메인에서 정당 사용 가능.
   - **Mitigation:** grep gate scope = Phase 7 canned string 모듈만 (`copy_templates._COPY_TEMPLATES + _MODE_PREFIX`). Phase 11/13 캔드 별도 grep 룰 박제.

7. **frontend `userAnalyses.normalize()` 신설 필드 처리 누락**
   - **현상:** Firestore doc 에 신설 4+2 필드 부재 시 frontend crash.
   - **Mitigation:** TS interface 의 두 list 를 `string[]` (non-optional) + normalize() 안에서 `?? []` default. per-finding 4 필드는 optional. plan 의 frontend 작업 task 명시.

8. **mode3_first + Gemini fallback 의 `uncertain` 전체 demotion 톤 위화감**
   - **현상:** Phase 6 D-06-B1 박제 (Page 9 절대 트랙 단독) path 가 의미상 "정밀 분석" 인데 본 phase 룰이 "uncertain 강제" 로 정합.
   - **Mitigation:** Decision 1 권장 룰 (모든 finding uncertain demotion) + 별도 fallback 카피 (정직성 우위 — "이 동작은 등록 기준 부족, 강사 확인"). belle plan 단계 검수 필요.

## Sources

### Primary (HIGH confidence — 내부 코드 + Phase 6 lock)

- `backend/shared/python/sunity_shared/analysis/body_normalizer.py:773-895` — BodyComparisonFinding + BodyComparisonReport dataclass + R9 fix 박제
- `backend/shared/python/sunity_shared/analysis/body_normalizer.py:901-1110` — measure_ipsf_absolute_deficits 산식 (5 IPSF + pose_reliability_low)
- `backend/shared/python/sunity_shared/analysis/body_normalizer.py:1115-1297` — compare_body_profiles 본체 (Phase 7 wiring 진입 지점)
- `backend/shared/python/sunity_shared/analysis/skeleton.py:10-79` — KEYPOINT_NAMES (17) + JOINT_LABEL_KO (8) + JOINT_TO_PART
- `backend/shared/python/sunity_shared/analysis/assemble.py:25-152` — mode-aware baseline 패턴 (Phase 12.5 박제)
- `backend/shared/python/sunity_shared/firestore_admin.py:45-170` — `_validate_flat_dict_no_nested_array` + `_validate_dict_only_scalars` + `complete_analysis`
- `backend/functions/pipeline/app.py:584-617` — `_dataclass_to_camel_case_dict` 5-case helper
- `app/src/types/analysis.ts:430-550` — TS BodyComparisonReport family interface
- `docs/contract.md §8 + §8.1 + §8.2` — Phase 6 BodyComparisonReport 명세 + IPSF divergence + BodyComparisonSourcePose
- `docs/research/01_체형차이_보정엔진_FINAL.md §9 + §10.1 + §10.3` — schema + 권장 4 + 금지 6
- `.planning/phases/07-difference-classification/07-CONTEXT.md` — locked decisions 본체
- `.planning/phases/06-coaching/06-CONTEXT.md` — D-06-U1 confidence-tiered hybrid 0.5 게이트 박제
- `.planning/REQUIREMENTS.md PERS-01` — phase 책임 박제
- `.planning/ROADMAP.md §Phase 7` — 4 success criteria
- `backend/research/evaluations/reports/sweep_rtmw_20260603_1409/report.md` — 5 영상 IPSF 회귀 데이터

### Secondary (HIGH-MEDIUM confidence — domain knowledge)

- `docs/research/폴스포츠-지식.md §"스플릿 각도" / §"Horizontal 요건"` — 부위별 원인 언어 (고관절 / 골반 / 코어 어휘) — 카피 본문 작성 근거
- `docs/research/폴스포츠 수강생의 설문조사.md` — P0 강사 철학 "수치보다 원인" + AI 보조 도구 포지셔닝 — 톤 박제 근거
- `.planning/phases/05-gemini/05-CONTEXT.md` — TechniqueProfile.motion_id + expects_extension 박제 (clean_lines 의 joint_group 분기 근거)
- `.planning/phases/16-studio-term-foundation/16-SCORING-SPEC.md` — IPSF 5트랙 v1 scope (Page 9 절대 트랙 — mode3_first fallback path 정합)

### Memory (HIGH confidence — belle 박제 정신)

- `[[scoring-dimensions-ipsf]]` — IPSF 절대 기준, 사람 점수 라벨링 X
- `[[mode3-progress-not-similarity]]` — mode3 = 절대 지표 델타 — `FORBIDDEN_PHRASES_SUNITY` 정합
- `[[ipsf-5-track-scoring]]` — Page 9 절대 트랙 — mode3_first fallback path 분류 룰 근거
- `[[feedback-analysis-first]]` — 분석 정확도 우선, 가능성 언어 — 톤 박제
- `[[mvp-simple-pilot-quality]]` — 단순 fallback 우선 — Phase 7 = 캔드 박제 근거
- `[[analysis-objectivity-no-human-scores]]` — 사람 점수 라벨링 영구 X — 캔드 객관성 박제
- `[[feedback-no-echo-confirm]]` — AI = 강사 보조 도구 톤 — 톤 박제
- `[[no-baekje-filler]]` — "박제" 단어 카피 남용 X — `FORBIDDEN_PHRASES_SUNITY` 정합

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — 신규 라이브러리 0, Phase 6 박제 패턴 100% 정합
- Architecture: HIGH — pure function + dict literal + 3-way lockstep 모두 Phase 6 검증 패턴
- Pitfalls: HIGH — Phase 6 close-out 10 fix 박제 패턴 (W5 / C8 / R8 / W1 / R9 / C14) 직접 재사용
- Canned string draft: MEDIUM-HIGH — research §10.1 4 예문 톤 박제 + Sunity 추가 3종 룰 정합. belle plan 단계 검수 필요 (한국어 자연스러움 + 강사 톤).
- Classification rule calibration: HIGH — sweep 데이터 분석 + IPSF Page 21 단위 정합 검증 완료

**Research date:** 2026-06-08
**Valid until:** 2026-07-08 (30 days — Phase 8/13 통합 시 deficit code 확장 시 재검토 trigger)

## RESEARCH COMPLETE

**Phase:** 7 - 차이 분류 (Difference Classification)
**Confidence:** HIGH

### Key Findings

- Phase 6 박제 패턴 (frozen dataclass + 3-way lockstep + 5-case camelCase + 0.5 confidence 게이트 + W5 nested-array validator) 100% 재사용 → 신규 인프라 0
- 임계 0.2 박제 검증 완료 (sweep_rtmw_20260603_1409 5 영상 + IPSF Page 21 단계 감점 단위 정합) → D-07-A1 그대로 권장
- canned string mapping 차원 = (deficit_code × category × joint_group × comparisonType), joint_key 17→5 그룹 축소 + comparisonType prefix-only → 21 카피 + 3 mode prefix = 24 line (Claude 초안 작성 완료)
- 6 금지 표현 (§10.3) + Sunity 추가 3 (`박제` / `%일치` / `유사도`) grep gate 단위 test 박제 완료
- Schema 확장 4+2 필드 atomic 3-way lockstep commit 박제 (Phase 6 commit 패턴 정합)
- mode3_first + `used_reference_fallback=True` 의 분류 룰 변형 박제 (Decision 1 — 모든 finding `uncertain` demotion + 별도 fallback 카피)

### File Created

`/Users/kimtaesung/Dev/SunityMotion/.planning/phases/07-difference-classification/07-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|---|---|---|
| Standard Stack | HIGH | 신규 라이브러리 0, Phase 6 stack 그대로 |
| Architecture | HIGH | pure function + dict literal — Phase 6 패턴 100% 정합 |
| Schema Extension | HIGH | 4+2 필드, Phase 6 lockstep 패턴 검증 완료 |
| Pitfalls | HIGH | Phase 6 close-out 10 fix 박제 직접 재사용 |
| Canned String Draft | MEDIUM-HIGH | belle plan 단계 검수 필요 (한국어 자연스러움) |
| Classification Rule | HIGH | sweep 데이터 + IPSF Page 21 단위 정합 검증 |
| Validation Architecture | HIGH | Phase 6 phase06/ 디렉토리 패턴 정합 |

### Open Questions (planner 처리 영역)

1. mode3_first + `used_reference_fallback=True` 단일 fallback 메시지 형식 — belle 검수
2. 빈 `recommended_focus[]` frontend 화면 fallback — Phase 12 책임
3. `body_type_interpretation` / `recommendation` 의 Phase 11 LLM 입력 형식 — Phase 11 plan 진입 시
4. frontend `userAnalyses.normalize()` 신설 필드 default 처리 — Phase 7 frontend task 또는 Phase 12

### Ready for Planning

Research 완료. Planner 가 본 RESEARCH.md 의 `## Schema Extension` + `## Canned Copy Mapping Table` + `## Code Examples` + `## Validation Architecture` 4 섹션을 직접 plan task 로 변환 가능. plan 권장 commit 단위 4-6 개 (T1: schema atomic lockstep / T2: copy_templates 신규 모듈 / T3: classify_findings + compare_body_profiles wiring / T4: fixtures 7 JSON / T5: 단위 test 8 파일 / T6: integration smoke + 3-way lockstep 검증).
