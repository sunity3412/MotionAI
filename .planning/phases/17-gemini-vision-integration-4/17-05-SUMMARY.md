---
phase: 17-gemini-vision-integration-4
plan: 05
subsystem: api
tags: [gemini, lambda, sam, firestore, reference, ipsf, vision]

requires:
  - phase: 17-gemini-vision-integration-4
    provides: GeminiVisionCall 베이스 + ReferenceRegistration Pydantic schema + resolve_model('A') 단일 source + G1 객관성 가드
provides:
  - POST /reference/auto-register endpoint — 정은지 영상 S3 key → Gemini Pro Vision → IPSF 명칭/clipRange/checkpointJoints 자동 산출 → Firestore reference/{motionId} 박제
  - 분기 1/2/3 라우팅 — IPSF whitelist 매치 (branch_1_ipsf) / studio_alias 매치 (branch_2_studio) / 둘 다 미매치 G3 fallback (branch_3_auto, isActive=false, review_required=True)
  - ipsf_whitelist.json fixture (14 entry — Butterfly/Cupid/Deadlift/Inverted Crucifix/Scorpio 등 IPSF CoP 2025-2027 등재 코드 + 13+ AKA 매핑)
  - studio_branch2_aliases.json fixture (5 entry — 폭스탑/폭스탑 스플릿/사이드웨이 스핀/엘보 트위스트 시스터/피터팬, championPersonalAlias 박힘)
  - set_reference_motion_with_gemini idempotent helper — 기존 doc 의 isActive/inactiveReason 보존 (belle 검수 결과 유지)
affects: [17-06 production launch validation, 17-07 reactivate 신규 6 motion]

tech-stack:
  added:
    - "google-genai>=1.0,<2.0 (per-function requirements — Pro Vision 호출)"
    - "pydantic>=2.5,<3.0 (per-function requirements — ReferenceRegistration schema)"
  patterns:
    - "JSON fixture 박제 (belle 후속 PR 로 entry 추가) — Python 코드 변경 없이 IPSF 화이트리스트 확장"
    - "3분기 라우팅 (메모리 [[studio-term-3branch-system]] 직격) — IPSF 매치 우선 → studio_alias 매치 → G3 fallback"
    - "Idempotent Firestore upsert — exists snap 박혀있으면 belle 검수 결과 보존, G3 trigger 만 inactiveReason audit 갱신"
    - "S3 download → /tmp 박제 (AI-SPEC §3 Pitfall #2 — presigned URL 직접 X)"
    - "Lambda Timeout 240s — Files API 폴링 upper bound 120s + Pro 호출 + cold start jitter 여유 (WARN-2 정합)"

key-files:
  created:
    - "backend/shared/python/sunity_shared/gemini/reference_extractor.py (extract_reference_metadata + 분기 라우팅)"
    - "backend/shared/python/sunity_shared/gemini/ipsf_whitelist.json (14 IPSF entry + AKA)"
    - "backend/shared/python/sunity_shared/gemini/studio_branch2_aliases.json (5 학원 통용 entry)"
    - "backend/functions/reference-auto-register/app.py (Lambda handler)"
    - "backend/functions/reference-auto-register/requirements.txt (firebase-admin/google-genai/pydantic)"
    - "backend/tests/gemini/test_reference_extractor.py (15 케이스)"
    - "backend/tests/test_reference_auto_register_handler.py (12 케이스)"
  modified:
    - "backend/template.yaml (ReferenceAutoRegisterFunction resource + HttpApi route + LogGroup)"
    - "backend/shared/python/sunity_shared/firestore_admin.py (set_reference_motion_with_gemini idempotent helper)"
    - "backend/shared/python/sunity_shared/gemini/__init__.py (extract_reference_metadata re-export)"

key-decisions:
  - "Lambda Timeout 240s (Plan 1차 박혀있던 120s 가 폴링 자체로 timeout 예산 소진 — WARN-2 정합)"
  - "resolve_model('A', env_override=GEMINI_A_MODEL) 단일 source 박제 — raw default string 박제 0 (R-B1 정합)"
  - "Firebase Auth + BELLE_UID env 화이트리스트 이중 인증 — env 미설정 시 강제 403 reject (조용한 통과 금지)"
  - "분기 라우팅 우선순위 — IPSF 매치(분기 1) > studio_alias 매치(분기 2) > G3 fallback(분기 3). Gemini A 가 직접 인식한 IPSF 명칭 매치를 1순위"
  - "Firestore idempotent — exists snap 박혀있으면 isActive/inactiveReason 기존 보존, G3 trigger 시 inactiveReason 만 audit 갱신 (belle 검수 결과 유지)"
  - "motion_id 결정 — override > ipsf_code > studio championPersonalAlias slug > motion_name_ipsf slug. Firestore doc id 정합 + seed 정합 (Plan 07 reactivate script 가 override_motion_id 박제)"
  - "STUDIO_ALIAS_OVERRIDES mapping 은 Plan 07 reactivate script 책임 — Plan 05 본체는 studio_alias 인자만 받는 함수 박제 (seed-reference-motions.mjs 의 reference doc 에 studioAlias 박혀있지 않음 검증)"

patterns-established:
  - "Pattern 1: JSON fixture + Python 로더 함수 (`_load_ipsf_whitelist`/`_load_studio_branch2_aliases`) — belle 후속 PR 진입점"
  - "Pattern 2: `_normalize_name` (NFKC + lowercase + 공백/하이픈 제거) + 정확 매치 비교 — 'Inverted-Thigh HOLD' / 'inverted thigh hold' 둘 다 매치"
  - "Pattern 3: `_decide_motion_id` 5 단계 fallback chain — override > IPSF code > studio alias slug > motion_name slug > timestamp"
  - "Pattern 4: 사용자 facing 응답에서 routing_branch / review_required / inactive_reason 박힘 — belle 가 즉시 검수 흐름 진입 가능"

requirements-completed: [VISION-01]

duration: 26 min
completed: 2026-06-12
---

# Phase 17 Plan 05: Reference 자동 등록 Endpoint Summary

**POST /reference/auto-register Lambda 박제 — 정은지 영상 S3 key → Gemini 3.1 Pro Vision → IPSF whitelist 분기 라우팅 + G3 guardrail + idempotent Firestore upsert.**

## Performance

- **Duration:** ~26 min
- **Started:** 2026-06-12T02:42:00Z (approx)
- **Completed:** 2026-06-12T03:08:00Z
- **Tasks:** 2/2
- **Files created:** 7
- **Files modified:** 3

## Accomplishments

- **POST /reference/auto-register endpoint** 신설 박제 — Firebase Auth + BELLE_UID 이중 인증, S3 download → /tmp, extract_reference_metadata 호출, idempotent Firestore upsert. Plan 의 ROADMAP Success #1 "정은지 영상 업로드 → Gemini Vision 이 IPSF 명칭 매칭 + clipRange + checkpoint joint 자동 산출" 직격.
- **분기 1/2/3 라우팅 + G3 guardrail** — IPSF whitelist 14 entry + studio alias 5 entry 정규화 매치. G3 (둘 다 미매치) trigger 시 review_required=True + inactiveReason="ipsf_whitelist_miss" 강제 박힘. AI-SPEC §1b "IPSF Code of Points 명칭/Criteria 정합" + "학원 용어 3분기 매핑 정확도" 둘 다 직격.
- **Idempotent Firestore upsert** — set_reference_motion_with_gemini(idempotent=True) 가 기존 doc 의 isActive/inactiveReason 보존 (belle 검수 결과 유지). T-17-25 mitigation 박힘.
- **27 케이스 단위/통합 테스트** 통과 — 외부 네트워크 호출 0 (monkeypatch 만), 분기 라우팅 + graceful fallback + idempotent + 인증 + S3 + Gemini failure 전부 커버.

## Task Commits

1. **Task 1: extract_reference_metadata + 분기 1/2/3 + G3 guardrail + 화이트리스트 fixture** — `639742c` (feat)
2. **Task 2: 신규 Lambda + Firebase Auth + SAM template + Firestore idempotent helper** — `6b75a0b` (feat)

## Files Created

- `backend/shared/python/sunity_shared/gemini/reference_extractor.py` — extract_reference_metadata + 분기 라우팅 + motion_id slug 박제. resolve_model('A', env_override=GEMINI_A_MODEL) 단일 source.
- `backend/shared/python/sunity_shared/gemini/ipsf_whitelist.json` — IPSF CoP 2025-2027 등재 코드 + AKA 매핑 14 entry. belle 후속 PR 진입점 (~120 entry 까지 확장 path 박힘).
- `backend/shared/python/sunity_shared/gemini/studio_branch2_aliases.json` — 한국 폴스포츠 학원 통용 비등재 동작 5 entry. championPersonalAlias 박힘.
- `backend/functions/reference-auto-register/app.py` — Lambda handler. Firebase Auth + BELLE_UID 화이트리스트 + S3 download → /tmp + extract_reference_metadata 호출 + Firestore idempotent upsert.
- `backend/functions/reference-auto-register/requirements.txt` — firebase-admin / google-genai / pydantic (boto3 는 Lambda 런타임 제공).
- `backend/tests/gemini/test_reference_extractor.py` — 15 케이스. 분기 1/2/3 + graceful None + idempotent + override + env override + ALLOWED_MODELS hard fail.
- `backend/tests/test_reference_auto_register_handler.py` — 12 케이스. happy / studio_alias passthrough / 401 / 403 / 400 / 404 / 500 / idempotent 2회 + firestore_admin helper 4 케이스.

## Files Modified

- `backend/template.yaml` — ReferenceAutoRegisterFunction resource + POST /reference/auto-register HttpApi route + LogGroup. Timeout 240s / MemorySize 512MB / env BELLE_UID + GEMINI_A_MODEL / s3:GetObject reference/* 만 / ssm:GetParameter 명시 ARN.
- `backend/shared/python/sunity_shared/firestore_admin.py` — set_reference_motion_with_gemini 신설. idempotent=True 박힘 시 기존 doc 의 isActive/inactiveReason 보존 + merge=True 박힘. G3 trigger 시 inactiveReason audit 갱신.
- `backend/shared/python/sunity_shared/gemini/__init__.py` — extract_reference_metadata re-export.

## Test Output

```
backend/tests/gemini/test_reference_extractor.py: 15 passed
backend/tests/test_reference_auto_register_handler.py: 12 passed
backend/tests/gemini/ (full): 111 passed (0 regression)
backend/tests/gemini/ + handler + firestore_admin_gemini_cache: 137 passed
sam validate -t backend/template.yaml --lint: PASS (valid SAM Template)
```

## Verification Gates

- `grep -c "ReferenceAutoRegisterFunction" backend/template.yaml` = **1** (resource 정의 박힘)
- `grep -n "reference/auto-register" backend/template.yaml` = **2** (HttpApi route Path + 주석)
- `grep -c "def set_reference_motion_with_gemini" backend/shared/python/sunity_shared/firestore_admin.py` = **1**
- `ipsf_whitelist.json` entries: **14** (≥13 박제 요구 충족)
- `studio_branch2_aliases.json` entries: **5** (≥3 박제 요구 충족)
- G3 회귀: test_reference_extractor.py `TestBranch3AutoG3Guardrail::test_unknown_motion_triggers_g3` → routing_branch="branch_3_auto" + review_required=True + inactive_reason="ipsf_whitelist_miss" 통과.
- Idempotent 회귀: test_reference_auto_register_handler.py `TestIdempotent::test_two_calls_same_motion_id_pass_idempotent_true` → 2회 호출 모두 idempotent=True + motion_id="ref-butterfly" 박힘 통과.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test stub lambda 시그너처 불일치 fix**
- **Found during:** Task 2 GREEN phase
- **Issue:** `lambda **kw: None` 가 positional argument (`motion_id`) reject — TypeError.
- **Fix:** `lambda *a, **kw: None` 로 변경 (positional + keyword 둘 다 박제).
- **Files modified:** `backend/tests/test_reference_auto_register_handler.py` (단일 라인)
- **Commit:** Task 2 commit 박힘 (`6b75a0b`)

**2. [Rule 2 - Critical] requirements.txt 의 firebase-admin/pydantic 박힘 결정**
- **Found during:** Task 2 implementation
- **Issue:** Plan 본체에 "Layer 박혀있는 firebase-admin/pydantic/boto3 제외" 박혀있었으나, backend/shared/python/requirements.txt 확인 결과 Layer 는 numpy 만 박힘. firebase-admin / pydantic 은 per-function 박제.
- **Fix:** requirements.txt 에 firebase-admin + pydantic 박힘. boto3 만 제외 (Lambda 런타임 제공).
- **Files modified:** `backend/functions/reference-auto-register/requirements.txt`
- **Why critical:** firebase-admin 없으면 Lambda import 실패 (auth.py / firestore_admin 의존). Plan 의도 (deps minimize) 와 실제 Layer 상태 정합 박혀있음.
- **Commit:** Task 2 commit (`6b75a0b`)

### Plan-Driven (Pre-planned, Not Deviation)

- **STUDIO_ALIAS_OVERRIDES**: Plan 본체에 "Plan 05 자체는 endpoint 만 — STUDIO_ALIAS_OVERRIDES 는 Plan 07 reactivate script 에서 박제" 박혀있어서 본 plan 의 reference_extractor 는 `studio_alias` 인자만 받는다 (mapping 박제 X). 이미 plan 정합.

## Known Stubs

없음. 모든 path 가 실 동작 박힘 — Gemini 호출이 graceful fallback (None 반환) 시 500 server_error 반환은 의도된 design (caller 재시도 가능 path).

## Threat Surface (Plan threat_model 정합 확인)

| Threat ID | Mitigation 박혔는지 검증 |
|-----------|-------------------------|
| T-17-22 (Spoofing) | Firebase ID token (verify_request) + BELLE_UID env 화이트리스트 이중 인증 박힘. 401/403 unit test 통과. |
| T-17-23 (Tampering — IPSF 환각) | G3 guardrail — ipsf_whitelist.json 매치 강제. 미매치 시 routing_branch="branch_3_auto" + isActive=false + reviewRequired=True 박힘. 회귀 테스트 통과. |
| T-17-24 (Info Disclosure) | accept — reference bucket 의 정은지 영상은 belle 가 박은 자산, IAM 권한으로 격리. |
| T-17-25 (Tampering — 검수 결과 덮어쓰기) | set_reference_motion_with_gemini(idempotent=True) — 기존 doc 의 isActive/inactiveReason 보존. 단위 테스트 4 케이스 통과. |
| T-17-26 (Repudiation — audit) | gemini_a.raw_response + registered_at + model + latency_ms 모두 Firestore reference/{motionId}.geminiA 박힘 audit. |
| T-17-27 (DoS) | accept — belle 1인 호출, HTTP API 기본 throttling 정합. |

## Self-Check: PASSED

- Files created: 7/7 박힘 (find/ls 확인).
- Files modified: 3/3 박힘 (git diff 확인).
- Task 1 commit `639742c`: 박힘 (git log 확인).
- Task 2 commit `6b75a0b`: 박힘 (git log 확인).
- 27 케이스 테스트 통과 (Task 1: 15 + Task 2: 12).
- 137 케이스 regression suite 통과 (gemini/ + handler + firestore_admin_gemini_cache).
- sam validate --lint PASS.
- 모든 verification grep 통과.
