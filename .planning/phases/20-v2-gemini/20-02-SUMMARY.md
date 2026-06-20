---
phase: 20-v2-gemini
plan: 02
subsystem: analysis-adapter
tags: [vision-veto, gemini, objectivity, determinism, adapter-boundary, lazy-import, tdd, pytest]

# Dependency graph
requires:
  - phase: 20-v2-gemini (20-01)
    provides: apply_downward_cap(overall, severity) — VisionVerdict.severity 가 먹이는 하향 cap 코어
  - phase: 19-vision-hybrid (D-05 spike)
    provides: spike_vision_grounding_pair.py — build_schema/_SCORE_PATTERN/upload_and_wait/temp 패턴 출발점
  - phase: 05 (technique_cache)
    provides: compute_video_hash(SHA256) + Firestore-backed cache 저장 구조 (VisionVetoCache 가 모방, 키는 전용)
provides:
  - "assess_fault_severity(local_video_path, at_seconds=None) -> VisionVerdict | None — 결함-심각도 어댑터 (score 0)"
  - "VisionVerdict(primary_fault, severity, differences) — severity enum 만 apply_downward_cap 입력"
  - "build_schema() — no-score/no-overall response_schema (객관성 introspection 가드 대상)"
  - "VisionVetoCache — 전용 키(video_hash,model,PROMPT_VERSION,SCHEMA_VERSION,input_granularity,at_seconds_bucket)"
  - "PROMPT_VERSION/SCHEMA_VERSION 상수 — bump 시 stale verdict 자동 무효화"
affects: [20-03-pipeline-wiring, 20-04-derive-caps-eval]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "객관성 = 구조적 내성검사: build_schema()/dataclasses.fields 로 score/overall/rating/점수 0 단언 (raw grep 아님)"
    - "결정론 = prompt/schema-versioned 전용 캐시: PROMPT_VERSION/SCHEMA_VERSION 을 키에 박아 bump 시 자동 cache-miss"
    - "adapter-boundary = 토글 미소유: analysis core 가 pipeline 을 import 하지 않고 feature 토글 helper 를 정의/복제하지 않음 (drift 차단)"

key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py
    - backend/tests/test_gemini_vision_scorer.py
  modified: []

key-decisions:
  - "severity = differences 중 최악 라벨(_dominant_severity, minor<moderate<major) — 지배 결함 1개가 overall 을 끌어내려야 (D-05 worst-pose 정합). 유효 severity 0개면 None(graceful)"
  - "VisionVetoCache.build_key 가 PROMPT_VERSION/SCHEMA_VERSION 을 globals() 경유로 읽음 — 테스트 monkeypatch 와 실 bump 모두 즉시 키에 반영(stale 무효화 검증 가능)"
  - "docstring 에서 forbidden 토글 심볼 리터럴(GEMINI_VISION_VETO_ENABLED 등) 제거 — test_adapter_does_not_own_toggle 의 raw-source 단언과 충돌 회피, 정확 심볼 부재는 AST+소스 가드가 단언"

patterns-established:
  - "Versioned-cache stale 무효화: 버전 상수를 캐시 키에 포함 + docstring 에 'prompt/schema 변경 시 bump' 명시로 비결정론 차단"
  - "adapter graceful-None boundary: 키/SDK/업로드/API/파싱 실패 전부 None + WARNING (raise 0) — 분석 흐름 비차단(Pitfall 5)"

requirements-completed: [SCORE-08, TRUST-06, TRUST-08]

# Metrics
duration: ~18min
completed: 2026-06-20
---

# Phase 20 Plan 02: Gemini 결함-심각도 어댑터 Summary

**Gemini Vision 으로 결함 종류/위치/severity enum 만 산출하는 어댑터 — 점수는 절대 안 냄(객관성 introspection 가드), temp 0 + prompt/schema-versioned 전용 VisionVetoCache 로 결정론, 토글 미소유로 adapter-boundary 보존. severity 는 20-01 apply_downward_cap 에 먹여 하향 cap 으로만 변환 → 비전이 점수를 올려 위양성을 재발시키는 경로 0. pod-free 15 mocked 테스트 GREEN.**

## Performance

- **Duration:** ~18 min
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files created:** 2

## Accomplishments

- **TRUST-08 객관성 (MEDIUM-1, 구조적 내성검사):** `build_schema()['properties']` 를 재귀 순회해 forbidden {score, overall, rating, 점수} 0 + spike 의 `overall_qualitative`(spike:217) **복사 금지** 단언(raw grep 아님 — import 한 schema dict 직접 순회). `VisionVerdict` 데이터클래스 필드 = {primary_fault, severity, differences} 정확(score 속성 영구 부재, `dataclasses.fields` 단언).
- **TRUST-08 leak-guard:** `_SCORE_PATTERN`(spike:233 재사용)이 "NN점/NN/100/NN%/100/100" 누출을 거부 — 응답 raw_text 에 매칭 시 verdict 폐기(None) + WARNING. 상수의 *존재* 는 객관성 위반 아님(내성검사는 schema/dataclass 만 검사).
- **TRUST-06 결정론 (MEDIUM-2):** `temperature=0.0`(spike 0.1→0) + 전용 `VisionVetoCache` 키 = (video_hash, model, PROMPT_VERSION, SCHEMA_VERSION, input_granularity, at_seconds_bucket). 같은 키 2회 → Gemini 1회(2번째 캐시) + verdict 동일. `PROMPT_VERSION`/`SCHEMA_VERSION` bump 시 같은 video_hash 라도 cache-miss → 재호출(stale 무효화). recognizer 의 (video_hash, model, yaml_version) 키 재사용 0.
- **iter2 non-blocking:** `input_granularity`('whole') 를 캐시 키에 명시 포함 — whole-video verdict 와 future frame-input verdict 키 충돌 0.
- **adapter-boundary (iter2 MEDIUM-1):** 어댑터가 `backend.functions.pipeline` import 0 + `_gemini_vision_veto_enabled` 정의 0 + `GEMINI_VISION_VETO_ENABLED` env 미참조(소스+AST 단언). 토글은 pipeline(20-03) 단독 소유 — toggle drift no-op 버그 재발 차단. analysis core import-light 보존.
- **B4 no-redownload:** caller `local_video_path` 만 사용 — boto3.client 호출 시 AssertionError 로 실패시키는 테스트가 S3 재다운로드/RTMW 재실행 0 단언.
- **graceful (Pitfall 5):** 키 부재/client 실패/업로드 실패/API 실패/파싱 실패 → 전부 None + WARNING(raise 0).
- **lazy-import (D-16):** google.genai 는 top-level import 0 — `_ensure_client()`/`_upload_video()`/`_call_gemini()` 함수 내부에서만. 모듈 캐시 싱글톤(recognizer 패턴).

## Task Commits

TDD 사이클 (test → feat):

1. **Task 1 (RED): 실패 테스트** - `1a61f25` (test) — gemini_vision_scorer 미존재 → ImportError
2. **Task 1 (GREEN): 어댑터 구현** - `558a8ed` (feat) — 15 passed

**Plan metadata:** (this commit) (docs: complete plan)

## Files Created/Modified

- `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py` — Gemini 결함-심각도 어댑터: VisionVerdict(no-score) + build_schema(no-score/no-overall) + _SCORE_PATTERN leak-guard + PROMPT_VERSION/SCHEMA_VERSION + 전용 VisionVetoCache(prompt/schema/granularity 키) + assess_fault_severity(graceful None, B4 no-redownload, 토글 미소유) + lazy-import google.genai.
- `backend/tests/test_gemini_vision_scorer.py` — 11 behavior(parametrize 포함 15 testcase) mocked-Gemini 단위테스트: schema/dataclass 내성검사 no-score + no-overall_qualitative + _SCORE_PATTERN 누출 거부(in-response) + severity enum + 캐시 결정론 + PROMPT_VERSION 무효화 + input_granularity 키 + graceful no-key + no-redownload + adapter-does-not-own-toggle(소스+AST).

## Decisions Made

- **severity 산출 = differences 최악 라벨:** Gemini 응답에 top-level severity 가 없으므로 `_dominant_severity` 가 differences[].severity 중 최악(minor<moderate<major)을 선택 — D-05 "지배 결함 1개가 overall 을 끌어내림" 정합. 유효 severity 0개면 None(graceful, 무의미 verdict 차단).
- **build_key 가 버전 상수를 globals() 경유로 읽음:** module-level 상수를 직접 참조하면 monkeypatch(테스트) 가 반영 안 됨. `globals()["PROMPT_VERSION"]` 로 읽어 테스트의 stale-무효화 검증 + 실 bump 모두 즉시 키에 반영.
- **docstring 에서 forbidden 토글 리터럴 제거:** `test_adapter_does_not_own_toggle` 가 raw-source 에 `GEMINI_VISION_VETO_ENABLED`/`backend.functions.pipeline`/`_gemini_vision_veto_enabled` 0건을 단언하므로, 설명용 docstring 에서 이 리터럴을 "vision veto 토글 env" / "pipeline 함수" 로 치환. 정확 심볼 부재는 AST+소스 가드가 단언(가드가 의미대로 작동).

## Deviations from Plan

None — plan 의 단일 TDD task 를 작성된 대로(RED→GREEN) 실행. 위 "Decisions Made" 3항목은 plan 의도 범위 내 구현 디테일(severity 집계 룰 = D-05 정합 / 캐시 키 monkeypatch 반영 / docstring 리터럴 = 가드 정합)이며 scope 변경 아님.

## Issues Encountered

**GREEN 1차 실행 시 test_adapter_does_not_own_toggle 1건 실패:** 모듈 docstring 이 toggle/pipeline 심볼을 설명용으로 리터럴 언급 → raw-source 단언이 매칭. docstring 리터럴을 치환해 해소(정확 심볼 부재는 유지). 나머지 14 testcase 는 1차부터 GREEN.

**전체 backend suite 의 pre-existing 실패 50건 (격리 — 본 plan 무관):** 20-01-SUMMARY 와 동일 — `test_pipeline_geminic_wiring.py`/`geminid` 등의 별도 미완 기능 실패 + 11 collection error(optional dep). 본 plan 신규 모듈 `gemini_vision_scorer.py` 는 **어느 기존 모듈에도 import 되지 않으며**(coupling 0, grep 확인), 따라서 NEW 회귀 0.

## Verification Results

- `cd backend && PYTHONPATH=shared/python python3 -m pytest tests/test_gemini_vision_scorer.py -q` → **15 passed** (11 behavior, parametrize 포함; 전부 mocked — 실 Gemini API/Pod 미호출)
- 객관성 (introspection): build_schema() 재귀 properties 에 score/overall/rating/점수 0 + overall_qualitative 0; VisionVerdict 필드 = {primary_fault, severity, differences}
- 결정론: 같은 키 2회 → Gemini 1회 + temperature=0.0 호출 인자; PROMPT_VERSION bump → cache-miss 재호출; input_granularity 키 포함
- adapter-boundary grep: `backend.functions.pipeline`/`_gemini_vision_veto_enabled`/`GEMINI_VISION_VETO_ENABLED` **0건**
- lazy-import grep: top-level `import google`/`from google` **0건** (함수 내부 lazy only)
- 캐시 키 grep: PROMPT_VERSION/SCHEMA_VERSION/input_granularity 포함(18 hit), recognizer yaml_version 키 재사용 0 (docstring 의 1 hit = "재사용 금지" 명시)
- coupling: gemini_vision_scorer 를 import 하는 기존 모듈 0건 → NEW 회귀 0 (pre-existing 50 failed 는 격리)
- Pod 무관 (전부 pod-free 단위테스트). 실 결정론(cache-warm byte-identity)은 20-04 Pod sweep 검증.
- 신규 패키지 0 (google-genai 기존 production 사용)

## User Setup Required

None — 기존 GEMINI_API_KEY(SSM `/sunity/motion/gemini-api-key`) 재사용, 신규 시크릿/패키지 0. 본 plan 은 mocked 단위테스트라 실 키 불필요(실 호출은 20-03 wiring + 20-04 Pod sweep).

## Next Phase Readiness

- **20-03 (pipeline wiring):** `assess_fault_severity` → VisionVerdict.severity → 20-01 `apply_downward_cap` 합성 자리 준비. **토글(GEMINI_VISION_VETO_ENABLED)은 pipeline 이 단독 소유** — 어댑터는 토글 미참조이므로 pipeline 이 게이트 + audit 필드(visionVeto) + silent no-op 차단 책임. worst_pose_timestamp(20-01) 를 at_seconds 로 전달.
- **20-04 (derive_caps eval):** 실 결정론(cache-warm byte-identity) + severity↔cap 일반화는 Pod sweep 에서 검증. SEVERITY_CAP moderate/major 채움 + sensitivity_manifest_sha256 갱신은 20-04 책임(20-01 fail-closed 가드 통과 조건).
- **블로커:** 없음 (pod-free, 후속 plan 진입 가능).

---
*Phase: 20-v2-gemini*
*Completed: 2026-06-20*

## Self-Check: PASSED

- gemini_vision_scorer.py FOUND
- test_gemini_vision_scorer.py FOUND
- 20-02-SUMMARY.md FOUND
- commits 1a61f25 (RED test) + 558a8ed (GREEN feat) FOUND
