---
phase: 05-gemini
plan: "01"
subsystem: backend-ml-recognizer
status: complete
wave: 1
completed_at: 2026-06-04
duration_minutes: 12
requirements:
  - SCORE-01
tags:
  - technique-recognizer
  - gemini-adapter
  - lazy-import
  - 3-case-fallback
  - reject-patterns
dependency_graph:
  requires:
    - .planning/phases/05-gemini/05-00-SUMMARY.md
    - backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py
    - backend/shared/python/sunity_shared/analysis/technique.py
    - backend/shared/python/sunity_shared/judging/loader.py
  provides:
    - GeminiTechniqueRecognizer (TechniqueRecognizer Protocol 구현)
    - classify_motion_name (production)
    - REGISTERED_MOTIONS (frozenset, D-01)
    - DEFAULT_GEMINI_MODEL = "gemini-3.1-pro" (D-13)
    - GeminiMomentExtractor._last_raw_response / _last_motion_name
  affects:
    - Plan 5-02 (TechniqueCache wiring — unregistered_hook + cache 호출처)
    - Plan 5-03 (pipeline swap — _process 안 GeminiTechniqueRecognizer 주입)
    - Plan 5-04 (Pod requirements + google-genai install)
    - Plan 5-05 (5영상 sweep --recognizer gemini)
tech-stack:
  added: []
  patterns:
    - lazy import (google.genai / boto3 / firebase_admin / technique_cache)
    - Protocol-based adapter (TechniqueRecognizer)
    - dataclass(frozen=True) + dataclasses.replace (category override)
    - production-first / spike-second (B2 fix — spike → production)
    - graceful degrade (3-case fallback + try/except hook + yaml lookup fallback)
    - source-grep lazy import 검증 (다른 테스트 sys.modules 오염 회피)
key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py
    - backend/shared/python/sunity_shared/analysis/gemini_motion_classifier.py
    - backend/research/spikes/spike_gemini_motion_classify.py
    - backend/tests/test_gemini_technique_recognizer.py
    - backend/tests/test_gemini_motion_classifier.py
    - backend/tests/test_gemini_motion_classify_spike.py
    - backend/tests/fixtures/gemini_responses/ko_invert.json
    - backend/tests/fixtures/gemini_responses/en_foxtop.json
    - backend/tests/fixtures/gemini_responses/ipsf_split.json
    - backend/tests/fixtures/gemini_responses/unregistered.json
    - backend/tests/fixtures/gemini_responses/multi_word.json
  modified:
    - backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py
    - backend/tests/test_gemini_moment_extractor.py
decisions:
  - D-13 적용 — DEFAULT_GEMINI_MODEL = "gemini-3.1-pro" (3.0 박제 폐기)
  - classify_motion_name 반환 = (canonical, scope_status) — adapter 가 position 1 ("unregistered") 로 D-09 case 3 분기. unregistered 시 position 0 = raw_name 보존
  - B3 fix 시그너처 박제 — unregistered_hook(keyword, video_hash). video_path 미노출 (TERM-DATA-01 분기 3 schema + PII 보호)
  - yaml lookup 실패 시 = 8관절 BENT_OK fallback (PyYAML 미설치 환경에서도 어댑터 분석 흐름 차단 X)
  - lazy import 검증 = source grep (sys.modules 검사가 아닌 module source line 검사 — 다른 테스트가 google.genai import 후의 sys.modules 오염 회피)
metrics:
  duration_minutes: 12
  tasks_completed: 3
  files_created: 11
  files_modified: 2
  tests_added: 62
  tests_passing: 122
commits:
  - 37f72d5 (Task 1)
  - ea80ac1 (Task 2)
  - b86fb0d (Task 3)
---

# Phase 05 Plan 01: GeminiTechniqueRecognizer 어댑터 + 3-case fallback + spike Summary

GeminiMomentExtractor (Plan 01-13 spike 박제) 를 TechniqueRecognizer Protocol 어댑터로 wrap. production wiring 진입 + 3-case fallback (API 실패 / Low conf / 미등록) + reject patterns 2차 가드 + motion_name 정규화 production 모듈 신설.

## Tasks Completed

| Task | 내용 | Commit | Test Count |
|------|------|--------|------------|
| 1 | spike + production classifier + 5 fixture | 37f72d5 | 21 |
| 2 | GeminiTechniqueRecognizer 어댑터 + extractor B5/W3 박제 | ea80ac1 | (구현) |
| 3 | adapter + classifier 단위 테스트 (W4 fix) | b86fb0d | 41 |

**전체 단위 테스트:** 122 PASS (Plan 5-01 scope 4 파일 + 기존 extractor 52 + technique 13)

## Open Question 결과 박제

### Open Question 1 — motion_name 응답 형태

**박제 path** = 정규화 production 모듈 `gemini_motion_classifier.classify_motion_name(raw)` 가 5영상 scope 로 흡수.

| 응답 형태 | 박제 path | 단위 시험 |
|---|---|---|
| 한국어 (학원 통용, 분기 1) | alias table 정확 매치 → canonical | TestKoreanAlias 5 PASS |
| 영어 (공식 / IPSF / 폴-arina) | alias table 정확 매치 → canonical | TestEnglishAlias 5 PASS |
| IPSF code prefix (예: "IPSF §4.2 Inverted Split (code XYZ)") | substring 매치 (긴 매치 우선) → canonical | TestSubstringMatch 3 PASS |
| 정확 canonical ID 직접 (예: "ref-invert") | Step 1 정확 매치 | TestExactMatch 6 PASS |
| 5영상 scope 외 (예: "Aerial Yogi") | (raw_name, "unregistered") 반환 → 어댑터 D-09 case 3 분기 | TestUnregistered 4 PASS |
| 한국어 multi-word (예: "기본 사이드웨이 스핀 시연") | substring 매치 (긴 매치 우선) | TestSubstringMatch 1 PASS |

**박제 정신 정합:**
- D-01 5영상 scope (REGISTERED_MOTIONS frozenset) 박제
- [[studio-term-3branch-system]] 분기 1 (학원 통용 한국어) 매핑 = 분기 2 (정은지 reference) yaml lookup 보호
- adapter 가 `scope_status == "unregistered"` 로 D-09 case 3 분기 — position 1 박제

### Open Question 2 — google-genai response_schema + video file 작동 검증

**박제 path** = spike `_run_live` 가 try/except 로 response_schema 작동/미작동 동적 분기.

- `use_response_schema=True` + 작동: `response.parsed` 직접 사용 (Pydantic 모델)
- `use_response_schema=True` + 미작동 (SDK 미지원): prompt-only fallback (Plan 01-13 박제 path)
- `use_response_schema=False`: prompt-only path (기존 박제)

**박제:** 출력 JSON 에 `response_schema_used` / `response_schema_worked` / `fallback_used` 박제 — Plan 5-05 belle Pod 실측 시 작동 여부 박제 결정.

**Stub mode 단위 시험 = response_schema 미사용 path** (fixture injection). live mode 는 belle Pod (Plan 5-05) 책임.

## 3-case fallback 박제 (D-09)

| Case | Trigger | Profile category | joint_expectations | 단위 시험 |
|---|---|---|---|---|
| 1 (API 실패) | RuntimeError / ValueError from extractor | `"api_failure"` | FallbackRecognizer 위임 (8관절 채워짐) | TestApiFailurePath 3 PASS |
| 2 (Low conf) | mean confidence < 0.5 (default) | `"low_confidence"` | `{}` (Page 9 단독 채점) | TestLowConfidencePath 2 PASS |
| 3 (미등록) | `scope_status == "unregistered"` | `"unregistered"` | `{}` + `unregistered_hook(keyword, video_hash)` 호출 | TestUnregisteredPath 3 PASS |
| 정상 | recognized + mean conf ≥ threshold | `"recognized"` | yaml hold_moment EXTEND/BENT_OK | TestRecognizedPath + TestJointExpectationsFromYaml 3 PASS |

**graceful degrade 박제:** 모든 fallback path 가 `TechniqueProfile` 반환 — 분석 흐름 차단 X.

## DEFAULT_GEMINI_MODEL 갱신 (D-13)

- `gemini-2.5-pro` → `gemini-3.1-pro` (belle 2026-06-04 확정)
- 박제 위치: `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py:DEFAULT_GEMINI_MODEL`
- 단위 시험 갱신: `test_default_model_constant` + `TestDefaultModel.test_default_model_is_gemini_3_1_pro`
- 3.0 폐기, 3.5 Flash = 후속 비용 분석 plan (deferred)

## B/W fix 적용 박제 (plan-checker iter 1+2)

| Fix | 내용 | 박제 |
|---|---|---|
| B2 | spike → production import (역방향 금지) | `spike_gemini_motion_classify.py` 가 `sunity_shared.analysis.gemini_motion_classifier.classify_motion_name` import. 단위 시험: TestKoreanAlias 등이 production 함수 직접 호출. |
| B3 | unregistered_hook 시그너처 = (keyword, video_hash) | 어댑터 `_compute_video_hash` 호출 → hook(raw_motion_name, video_hash). 단위 시험: `test_unregistered_hook_called_with_keyword_and_video_hash` — `args[1] != "/tmp/fake.mp4"` 검증. |
| B5 | extractor._last_raw_response 박제 → 어댑터 2차 가드 도달 | extractor `_call_gemini` 응답 직후 attribute 박제. 어댑터 `_adapter_reject_guard` 가 attribute 검사. 단위 시험: `test_coordinate_in_raw_response_triggers_value_error` PASS. |
| W1 | spike prompt 텍스트에 좌표/score/점수 keyword 0건 | `TestPromptText` 3 + `TestAdapterPromptHygiene` 2 모두 PASS. |
| W3 | DEFAULT_GEMINI_MODEL + raw_response/motion_name attribute 명시 박제 | extractor.py 갱신 2건 (D-13 상수 + 2 dataclass field). grep `gemini-3.1-pro` = 2 / grep `_last_raw_response\|_last_motion_name` = 5. |
| W4 | 테스트 별 task 분리 (Task 3 신설) | Task 3 = 단위 시험 신설 41건 (adapter 22 + classifier 19). |

## reject patterns 2차 가드 (D-08, [[analysis-objectivity-no-human-scores]])

- **1차** (extractor layer): `gemini_moment_extractor._enforce_no_coordinate_or_score` — 19 reject patterns (좌표 7 + 점수 5 + 판단 7).
- **2차** (어댑터 layer): `gemini_technique_recognizer._adapter_reject_guard` — extractor 의 `_last_raw_response` 를 다시 검사.
- **다중 방어 박제 정신:** extractor 가 미래에 reject patterns 변경되어도 어댑터는 자체 가드 유지.
- **단위 시험 박제:** 좌표 (`x=120`) / 점수 (`85점`) 응답이 어댑터 layer 에서 ValueError 발생 — 2차 가드 도달 검증.

## 박제 spec 정합 확인

| Decision | 박제 위치 | 검증 |
|---|---|---|
| D-04 (1회 호출 → 기술명 + 4단계 라벨 + timestamp) | `_call_extractor` → KeyMoment list | TestRecognizedPath |
| D-05 (v1 채점 = hold moment 만 활성) | `_build_profile` 가 hold_moment criteria 만 소비 | TestJointExpectationsFromYaml |
| D-08 (Gemini = 라벨러만, yaml 수치 source 박제 보호) | `_build_profile` 가 yaml `load_grouped_criteria` 만 read | adapter source 검사 — yaml write path 0 |
| D-09 (3-case fallback) | `recognize()` Step 4 / 6 / 7 | TestApiFailurePath + TestLowConfidencePath + TestUnregisteredPath |
| D-13 (model = gemini-3.1-pro) | `DEFAULT_GEMINI_MODEL` 상수 | TestDefaultModel |
| D-16 (lazy import) | google.genai / boto3 / firebase_admin / technique_cache 모두 함수 내부 | TestLazyImport source grep |

## Deviations from Plan

### Rule 2 — Auto-add missing critical functionality

**1. [Rule 2 - Defensive] yaml lookup 실패 graceful fallback**
- **Found during:** Task 2 어댑터 구현
- **Issue:** Plan 의 `_build_profile` 는 `load_grouped_criteria` 호출만 명시. PyYAML 미설치 환경 (로컬 dev, Lambda cold start 일부) 에서 ImportError 또는 yaml 파일 누락 시 분석 흐름 차단 가능.
- **Fix:** `try / except (FileNotFoundError, ImportError, ValueError)` → 8관절 BENT_OK fallback + log warning. yaml lookup 실패해도 adapter 가 TechniqueProfile 반환 (분석 차단 X).
- **Files modified:** `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py`
- **Commit:** ea80ac1
- **박제 정신:** D-09 graceful degrade (3-case fallback 정신 적용 확장).

**2. [Rule 2 - Defensive] technique_cache 미신설 graceful no-op**
- **Found during:** Task 2 어댑터 구현
- **Issue:** Plan 은 `from .technique_cache import compute_video_hash` 박제 명시. 그러나 technique_cache.py 는 Plan 5-02 책임 — Plan 5-01 시점에 미존재 → ImportError.
- **Fix:** `_compute_video_hash(frames)` 함수가 ImportError 잡고 빈 문자열 반환 + log debug. Plan 5-02 신설 후 자동 활성.
- **Files modified:** `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py`
- **Commit:** ea80ac1
- **박제 정신:** [[mvp-simple-pilot-quality]] "구조만 열어두기" 정합.

**3. [Rule 2 - Test infra] frames=None safety**
- **Found during:** Task 3 test 작성 (edge case 검증)
- **Issue:** frames (video_uri) 가 None 일 때 extractor 호출 시 Gemini File API 가 fail. Plan 은 frames=None 처리 명시 X.
- **Fix:** Step 2 에 `if frames is None` 가드 박제 → FallbackRecognizer 위임 + category="api_failure". 단위 시험에서 frames="/tmp/fake.mp4" stub 으로 우회.
- **Files modified:** `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py`
- **Commit:** ea80ac1

### Test approach divergence (no rule violation)

**1. lazy import 검증 = source grep (sys.modules 검사 X)**
- **Found during:** Task 1 spike test 작성
- **Issue:** Plan 박제 `sys.modules grep` — 그러나 pytest 가 다른 테스트 (extractor 등) 에서 google.genai / boto3 를 이미 import 한 후라면 spike 단위 시험에서 sys.modules 가 오염 → false negative.
- **Approach:** module source code 직접 grep — 어댑터 / spike top-level (들여쓰기 0) 에 `from google` / `import boto3` / `from firebase_admin` 박제 X 만 검증. lazy import 박제 정신 그대로 박제.
- **Files:** `test_gemini_motion_classify_spike.py:TestLazyImport` + `test_gemini_technique_recognizer.py:TestLazyImport`
- **박제 정신:** D-16 lazy import 정신 그대로 박제, 단위 시험 robust 박제 강화.

## Self-Check

다음 자동 검증을 수행했습니다:

```bash
# 파일 존재 확인
[ -f backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py ] && echo FOUND
[ -f backend/shared/python/sunity_shared/analysis/gemini_motion_classifier.py ] && echo FOUND
[ -f backend/research/spikes/spike_gemini_motion_classify.py ] && echo FOUND
[ -f backend/tests/test_gemini_technique_recognizer.py ] && echo FOUND
[ -f backend/tests/test_gemini_motion_classifier.py ] && echo FOUND
[ -f backend/tests/test_gemini_motion_classify_spike.py ] && echo FOUND
ls backend/tests/fixtures/gemini_responses/ | wc -l  # 5

# 커밋 존재 확인
git log --oneline --all | grep -q "37f72d5" && echo FOUND
git log --oneline --all | grep -q "ea80ac1" && echo FOUND
git log --oneline --all | grep -q "b86fb0d" && echo FOUND

# 통합 단위 시험
pytest backend/tests/test_gemini_moment_extractor.py \
       backend/tests/test_gemini_motion_classify_spike.py \
       backend/tests/test_gemini_motion_classifier.py \
       backend/tests/test_gemini_technique_recognizer.py
# → 122 passed
```

## Self-Check: PASSED

## 후속 작업 박제

- **Plan 5-02 (TechniqueCache + technique_cache.py 신설)**: 본 plan 의 `_compute_video_hash` ImportError graceful fallback 자동 활성 + unregistered_hook Firestore wiring.
- **Plan 5-03 (pipeline swap)**: `_process` 안 GeminiTechniqueRecognizer 주입 + FallbackRecognizer 교체.
- **Plan 5-04 (Pod requirements)**: `google-genai` install + setup.sh 갱신.
- **Plan 5-05 (5영상 sweep `--recognizer gemini`)**: D-01 게이트 (정은지 reference 4/4 PASS + ref-climb out-of-scope counted) 실증.
- **D-10 low_confidence_threshold 박제 갱신**: 5영상 sweep 실측 confidence 분포 기반 (Plan 5-05 후).

## 박제 정신 정합 검증

| 박제 정신 | 정합 |
|---|---|
| [[feedback-analysis-first]] "분석 정확도 우선" | OK — Gemini = 라벨러만, yaml source 박제 보호 (D-08) |
| [[analysis-objectivity-no-human-scores]] "사람 점수 X, 객관 측정값 OK" | OK — reject patterns 2차 가드 박제 |
| [[mvp-simple-pilot-quality]] "구조만 열어두기" | OK — cache / unregistered_hook = None default + technique_cache ImportError no-op |
| [[gap-and-line-angle-mandatory-gates]] "강등/우회 금지" | OK — 3-case fallback = graceful degrade (Page 9 단독 채점 박제, 강등 X) |
| [[studio-term-3branch-system]] 분기 1 alias 매핑 | OK — 한국어/영어 20+ alias + substring 매치 |
| [[gsd-pod-work-push-first]] commit + push | OK — Task 1/2/3 모두 atomic commit |
| [[runpod-gpu-env]] Pod 환경 박제 | N/A — 본 plan = 로컬 단위 시험만, live mode = Plan 5-05 |

## Known Stubs

본 plan = 단위 시험 박제 only. 의도된 stub:
- **`unregistered_hook=None` default**: Plan 5-02 Firestore wiring 전 = no-op. 의도된 박제 (D-09 case 3 박제 path 보장).
- **`cache=None` default**: Plan 5-02 TechniqueCache wiring 전 = no-op. 의도된 박제.
- **`_compute_video_hash` ImportError graceful "" 반환**: Plan 5-02 technique_cache 신설 전 = 의도된 박제.

위 3 stub 모두 Plan 5-02 가 자동 활성 — 의도된 ✓ ([[mvp-simple-pilot-quality]] 구조만 열어두기 박제 정신 정합).

---

*Plan 5-01 종료: 2026-06-04*
*다음 = Plan 5-02 (TechniqueCache + Firestore wiring) 또는 Wave 1 평행 plan*
