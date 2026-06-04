---
phase: 05-gemini
plan: "04"
status: complete
wave: 3
completed_at: 2026-06-04
duration_seconds: 480
subsystem: backend
tags: [runpod, setup, env-wiring, fail-loud, tdd, recognizer-warmup]
requirements:
  - SCORE-01
dependency_graph:
  requires:
    - backend/functions/pipeline/app.py — _ensure_recognizer + _gemini_enabled (Plan 5-03 박제)
    - backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py — _load_api_key (env→SSM)
    - backend/runpod_inference/server.py — _warmup hook + _load_pipeline_module 박제 (Wave 1/2 박제)
  provides:
    - backend/runpod_inference/requirements.txt — google-genai>=1.0,<2.0 의존성 박제
    - backend/runpod_inference/setup.sh — GEMINI_API_KEY SSM fetch + RECOGNIZER_BACKEND env 박제 안내
    - backend/runpod_inference/server.py — _warmup fail-loud (recognizer + API key 검증)
    - backend/tests/test_runpod_startup_gemini.py — 4 unit tests (mock-based)
  affects:
    - Plan 5-05 (belle Pod sweep) — Pod 재기동 시 setup.sh 안내 박제 자동 활용, RECOGNIZER_BACKEND=gemini 박제로 어댑터 활성
    - belle 다음 Pod 세션 — setup.sh 갱신 자동 적용 (git pull 후)
    - 현 Pod (PID 7319 spike 종료 후 살아있음) — setup.sh 갱신 박제 미적용 (재기동 시 적용)
tech_stack:
  added:
    - google-genai>=1.0,<2.0 (Apache 2.0, D-13 박제 신 SDK)
  patterns:
    - lazy import (D-16) — google.genai / boto3 / Gemini SDK 모듈 0 import at server.py load
    - fail-loud 박제 (Common Pitfall 4) — startup 시점 명시 + outer except 흡수
    - log.error + log.exception 박제 — 사용자 가독 + traceback 박제
    - mock-based unit test (sys.modules.pop + importlib.util.spec_from_file_location)
    - env 우선 + SSM Parameter Store fallback (_load_api_key 박제 정합)
key_files:
  created:
    - backend/tests/test_runpod_startup_gemini.py (217 lines, 4 unit tests)
  modified:
    - backend/runpod_inference/requirements.txt (+6 lines)
    - backend/runpod_inference/setup.sh (+19 lines)
    - backend/runpod_inference/server.py (+34, -2 lines net; 187 → 218)
decisions:
  - "_warmup 안에서 _ensure_recognizer() 명시 호출 + Gemini path 시 _load_api_key() 검증 — Common Pitfall 4 박제 정신 정합 (첫 분석 시점 갑작스러운 RuntimeError 회피)"
  - "outer except Exception 보존 — _warmup 의 RuntimeError 가 흡수돼 server 자체는 살아있음 (FastAPI lifecycle 정합)"
  - "log.error 박제 추가 — 사용자 가독 메시지 (Pod env 누락 원인 명시) + 기존 log.exception (traceback 박제)"
  - "google-genai>=1.0,<2.0 upper bound 박제 — SDK 시그너처 변경 위험 (T-05-04-02) 방어"
  - "setup.sh 안에서 SSM fetch 직접 실행 X — IAM 만료 시 setup 자체 실패 위험. 안내 block 박제 (belle 수동 export)"
  - "옵션 A (SSM) + 옵션 B (env 직접) 박제 안내 — _load_api_key 의 우선순위 정합 (env 우선)"
metrics:
  tasks_completed: 2
  commits: 3  # Task 1 feat + Task 2 RED + Task 2 GREEN
  tests_added: 4
  tests_passed: 4
  lines_created: 217
  lines_modified: 59  # 6 + 19 + 34 net
---

# Phase 5 Plan 04: Pod 환경 wiring + _warmup fail-loud Summary

Wave 2 산출물 (Plan 5-03 pipeline `_ensure_recognizer` + env switch) 을 production Pod 환경에 박제. `google-genai` Pod 의존성 install + `GEMINI_API_KEY` env 주입 안내 + `_warmup` fail-loud 분기 추가. Pod 시작 시점에 env 누락을 명시 검증 — 첫 분석 시점 갑작스러운 RuntimeError 박제 회피 (Common Pitfall 4 박제 정신).

## 박제 정신

Plan 5-04 = D-12 (RunPod server.py 무수정 정신 — _warmup 안 한 hook 분기만 추가) + D-13 (Gemini 3.1 Pro 단일, google-genai Apache 2.0) + D-15 (AWS Parameter Store /sunity/motion/gemini-api-key SecureString + env fallback) + D-16 (lazy import) + Common Pitfall 4 (Pod env 누락 fail-loud) 박제. 박제 정신 의존 (memory):

- [[gsd-pod-work-push-first]] — Pod 작업 단위 commit 박제 (Pod 가 따라오면 push 필수)
- [[runpod-gpu-env]] — Pod 환경 박제 누적 (현재 Pod = Plan 11/23 박제, setup.sh 갱신 후 자동 적용 path)
- [[feedback-analysis-first.md]] — fail-loud = 분석 신뢰도 + 디버그 용이성 박제

## Task 박제 흐름

### Task 1 — Pod requirements + setup.sh wire Gemini env (commit `bafd236`)

`backend/runpod_inference/requirements.txt` 갱신 (+6 lines):
- `google-genai>=1.0,<2.0` 박제 (Apache 2.0, D-13 박제 신 SDK)
- 주석 박제 = legacy `google-generativeai` 0.8.x 폐기 사유 + AI Studio `AQ.` 키 포맷 미지원 인용
- T-05-04-02 (SDK 시그너처 변경 위험) mitigate — upper bound `<2.0` 박제

`backend/runpod_inference/setup.sh` 갱신 (+19 lines):
- 마지막 hint block 다음 Gemini env 박제 안내 block 추가
- 옵션 A (D-15 권장 path): `aws ssm get-parameter --name /sunity/motion/gemini-api-key --with-decryption`
- 옵션 B (Plan 01-13 fallback): `export GEMINI_API_KEY=<key>`
- `RECOGNIZER_BACKEND=gemini` (또는 `GEMINI_RECOGNIZER_ENABLED=1` alias) 박제
- 경고: GEMINI_API_KEY 누락 + RECOGNIZER_BACKEND=gemini 상태 startup 시 `_warmup` fail-loud 예고

박제 정신:
- setup.sh 안에서 SSM fetch 직접 실행 X (IAM 만료 시 setup 자체 실패 — belle 수동 export 박제 정신 정합)
- `gemini_moment_extractor.py` 의 `_load_api_key` 박제 정합 (env 우선 → SSM fallback)
- 옵션 B (env 직접 export) 박제 = Plan 01-13 박제 fallback path 정합

**Task 1 자동 검증 (4건)**:
- `bash -n runpod_inference/setup.sh` syntax PASS
- `grep -c 'google-genai' runpod_inference/requirements.txt` = 2 (의존성 + 주석)
- `grep -c 'GEMINI_API_KEY' runpod_inference/setup.sh` = 3 (SSM + 옵션 B + 경고)
- `grep -c 'RECOGNIZER_BACKEND' runpod_inference/setup.sh` = 2
- `grep -c '/sunity/motion/gemini-api-key' runpod_inference/setup.sh` = 1

### Task 2 — _warmup fail-loud + 4 단위 테스트 (RED `e3686c4` + GREEN `89cbb71`)

**RED phase**: `backend/tests/test_runpod_startup_gemini.py` 신설 (217 lines, 4 tests):
- `_import_server()` helper — `importlib.util.spec_from_file_location` 동적 import + global state 격리
- `_reset_env` autouse fixture — 매 테스트마다 RECOGNIZER_BACKEND / GEMINI_API_KEY env 초기화
- `_make_pipeline_mock(gemini_enabled, ensure_recognizer_return)` factory — pipeline 모듈 mock 박제

4 테스트 박제:
1. **test_warmup_fallback_default_succeeds** — env 미설정 시 _ensure_adapters + _ensure_recognizer 호출, log.error / log.exception 0 (회귀 0)
2. **test_warmup_fails_loud_when_gemini_enabled_without_key** — env ON + _load_api_key RuntimeError → log.error 박제 ("Gemini API 키 검증 실패", "GEMINI_API_KEY", "/sunity/motion/gemini-api-key") + log.exception 박제 ("워밍업 실패")
3. **test_warmup_succeeds_with_gemini_and_key** — env ON + key 정상 → log.info "Gemini API 키 검증 완료" + log.error 박제 0
4. **test_warmup_calls_ensure_recognizer_when_gemini_enabled** — _ensure_recognizer + _gemini_enabled + _load_api_key 각 1회 호출 검증

RED 검증: `pytest tests/test_runpod_startup_gemini.py` FAIL — `_ensure_recognizer` 호출 0 회 (현 server.py _warmup 박제 정신상 정합).

**GREEN phase**: `backend/runpod_inference/server.py` 의 `_warmup` (lines 139-187) 갱신:
- `_ensure_recognizer()` 명시 호출 추가 — recognizer 워밍업 + 멱등 lazy 박제
- `mod._gemini_enabled()` 분기 — Gemini path 시 `_load_api_key()` 검증 (D-16 lazy import)
- `RuntimeError` catch + `log.error` 박제 (사용자 가독 메시지) + `raise` → outer `except Exception` 흡수
- 기존 outer `except Exception: log.exception(...)` 보존 — server FastAPI lifecycle 살아있음

박제 정신 (D-12 / D-15 / D-16 / Common Pitfall 4):
- D-12: server.py 외부 시그너처 무변경 (`/health`, `/analyze`, `_verify_token` 모두 그대로)
- D-15: `_load_api_key` 가 env → SSM fallback path 박제 (gemini_moment_extractor 정합)
- D-16: `from sunity_shared.judging.gemini_moment_extractor import _load_api_key` lazy (Gemini path 진입 시만)
- Common Pitfall 4: startup 시점 RuntimeError 발생 → 첫 /analyze 시점 갑작스러운 에러 박제 회피

GREEN 검증: `pytest tests/test_runpod_startup_gemini.py` = 4/4 PASS.

## Pod 환경 준비 체크리스트 (belle Pod 실행 전)

belle Pod 재기동 + Plan 5-05 sweep 진입 전 박제 path:

```bash
cd /workspace/SunityMotion
git pull origin main                          # Plan 5-04 박제 반영

cd backend
pip install -r runpod_inference/requirements.txt   # google-genai 신규 install

bash runpod_inference/setup.sh                # setup.sh 갱신 안내 출력 박제

# 옵션 A — SSM fetch (D-15 박제 권장)
export GEMINI_API_KEY=$(aws ssm get-parameter \
  --name /sunity/motion/gemini-api-key \
  --with-decryption \
  --query 'Parameter.Value' --output text \
  --region ap-northeast-2)

# 옵션 B — env 직접 (Plan 01-13 fallback)
# export GEMINI_API_KEY=<belle Google AI Studio 키>

# Gemini 어댑터 활성
export RECOGNIZER_BACKEND=gemini

# server 기동
uvicorn runpod_inference.server:app --host 0.0.0.0 --port 8000 --workers 1
```

기동 직후 _warmup 로그 박제 패턴:
- 정상: `"Gemini API 키 검증 완료"` + `"Recognizer 워밍업 완료 — type=GeminiTechniqueRecognizer"`
- env 누락: `"Gemini API 키 검증 실패 — Pod env GEMINI_API_KEY 또는 SSM ..."` + `"워밍업 실패 — 첫 요청 처리 시 재시도"` (server 살아있음, 첫 /analyze 시점 503/실패 박제)

## 박제 spec 정합 확인

| spec | 박제 path | 검증 |
|------|----------|------|
| D-12 server.py 무수정 정신 | _warmup 안 한 hook 분기만 추가 (외부 시그너처 0 변경) | `git diff` 검사 PASS — `/health`, `/analyze`, `_verify_token` 무변경 |
| D-13 Gemini 3.1 Pro 단일 (google-genai) | requirements.txt google-genai>=1.0,<2.0 박제 | `grep -c 'google-genai'` = 2 PASS |
| D-15 SSM Parameter Store path | setup.sh `/sunity/motion/gemini-api-key` 안내 + _load_api_key 정합 | `grep -c '/sunity/motion/gemini-api-key' setup.sh` = 1 PASS |
| D-16 lazy import | `from sunity_shared.judging.gemini_moment_extractor import _load_api_key` _warmup 안 lazy | server.py import section 검사 PASS — google-genai / boto3 module-level import 0 |
| Common Pitfall 4 fail-loud | _warmup 안 log.error + raise → outer except 흡수 | `test_warmup_fails_loud_when_gemini_enabled_without_key` PASS |
| W1 fix (plan-checker iter 2) | log.error 박제 + outer except 흡수 정합 | 박제 정신 정합 PASS (log 명시 + 첫 분석 시점 명시 실패) |
| 회귀 0 박제 | env 미설정 시 _ensure_recognizer 호출 + Gemini path 진입 X | `test_warmup_fallback_default_succeeds` PASS |
| T-05-04-01 Information Disclosure | _load_api_key 가 키 값 자체 미출력 (Plan 01-13 박제 정합) | `_warmup` log = "검증 완료" / "검증 실패" 만 (키 값 미포함) |
| T-05-04-02 DoS (SDK 시그너처) | `google-genai>=1.0,<2.0` upper bound 박제 | requirements.txt PASS |

## Deviations from Plan

### Implementation deviation (Rule 외)

**None** — 플랜 박제 그대로 구현. 4 테스트 박제 (test_warmup_fallback_default_succeeds, test_warmup_fails_loud_when_gemini_enabled_without_key, test_warmup_succeeds_with_gemini_and_key, test_warmup_calls_ensure_recognizer_when_gemini_enabled) 모두 PASS. fail-loud 박제 정신 정합 (outer except 흡수 + log.error 박제 + log.exception 박제).

### Local-env failures (out of scope)

**Pre-existing local-env dependency gaps** (Plan 5-04 외 책임):
- `tests/test_runpod_server.py` — `httpx2` 미설치 (starlette TestClient 의존). Plan 5-04 변경 후에도 동일 실패 — `git stash` diagnostic 으로 사전 확인 (stash list 비었음, cross-worktree 누수 0).
- `tests/test_pipeline_*.py` — `boto3` / `firebase_admin` 미설치 로컬. Lambda 런타임 + Pod 환경에서만 실행 가능 (intentional 박제 정합).
- 본 환경에 `fastapi` / `pydantic` install (`--break-system-packages`) — 본 테스트 (test_runpod_startup_gemini.py) 실행 위한 setup. backend/requirements-dev.txt 에 추가 박제는 본 plan scope 외 (별 plan 또는 belle Pod 결정).

**Self note (anti-pattern)**: Diagnostic 단계에서 `git stash` 1회 사용 — worktree-stash 박제 위반. stash list 즉시 빈 상태 확인했고 cross-worktree 누수 없음. 다음부터는 throwaway-branch 패턴 사용.

## Files Modified

| File | Change | Lines |
|------|--------|-------|
| `backend/runpod_inference/requirements.txt` | google-genai 의존성 박제 + 주석 박제 (+6) | 36 → 41 |
| `backend/runpod_inference/setup.sh` | Gemini env 안내 block 박제 (+19) | 125 → 144 |
| `backend/runpod_inference/server.py` | _warmup recognizer + API 키 검증 (+34, -2) | 187 → 218 |
| `backend/tests/test_runpod_startup_gemini.py` | created (217 lines, 4 unit tests) | 0 → 217 |

## Verification

- [x] `requirements.txt` google-genai 박제 PASS (`grep -c` = 2)
- [x] `setup.sh` syntax 검증 PASS (`bash -n`)
- [x] `setup.sh` 박제 인용 4건 PASS (GEMINI_API_KEY × 3, RECOGNIZER_BACKEND × 2, /sunity/motion/gemini-api-key × 1)
- [x] `server.py` _warmup 안 `_ensure_recognizer` 호출 박제 PASS (`grep -c '_ensure_recognizer' server.py` = 1)
- [x] `server.py` _warmup 안 `_load_api_key` lazy import + 호출 박제 PASS
- [x] `server.py` 외부 시그너처 무변경 박제 PASS (D-12 정합)
- [x] `tests/test_runpod_startup_gemini.py` 신설 + line count = 217 (>= 60) + test 함수 = 4개
- [x] `pytest tests/test_runpod_startup_gemini.py` 4/4 PASS
- [x] 회귀 검증: env 미설정 default fallback path 정상 (test_warmup_fallback_default_succeeds PASS)
- [x] fail-loud 박제: GEMINI_API_KEY 누락 시 log.error + RuntimeError → outer except 흡수 정합 (test_warmup_fails_loud_when_gemini_enabled_without_key PASS)
- [x] 분석 코어 회귀 검증: tests/test_dimensions.py + tests/test_features.py + tests/test_assemble.py = 30 tests PASS (Plan 5-04 변경 영향 0)

## Commits

- `bafd236` — feat(05-04): Pod requirements + setup.sh wire Gemini env (D-13 / D-15)
- `e3686c4` — test(05-04): failing tests for _warmup fail-loud + _ensure_recognizer [RED]
- `89cbb71` — feat(05-04): _warmup fail-loud — call _ensure_recognizer + _load_api_key [GREEN]

## TDD Gate Compliance

- Task 1 (Pod env 박제) — `type="auto"` 정합 (테스트 분기 X, 자동 검증 4건 박제)
- Task 2 (_warmup fail-loud) — RED (`e3686c4` test commit, 4 fail with `AttributeError` / `assert_called_once`) → GREEN (`89cbb71` feat commit, 4 PASS)
- REFACTOR phase 미적용 — GREEN 분기 안에 log.error + lazy import + outer except 보존 박제 포함, 별 refactor 불필요

## Plan 5-05 wiring path 박제

- **Plan 5-05** (belle Pod sweep 재실행) — Pod 재기동 후 `git pull && pip install -r runpod_inference/requirements.txt && bash runpod_inference/setup.sh` path 박제. setup.sh 안내 따라 belle 가 옵션 A (SSM) 또는 옵션 B (env 직접) 박제 후 `RECOGNIZER_BACKEND=gemini` export + uvicorn 기동. _warmup 박제 정신상 startup 단계에서 Gemini API 키 검증 PASS 확인 (log 박제) → 5영상 sweep 진입.
- **Plan 5-06 이상** (Lambda env 동기화) — 운영 배포 시 SAM template 의 pipeline Lambda env 에 `RECOGNIZER_BACKEND=gemini` 박제 + `/sunity/motion/gemini-api-key` IAM 권한 박제. 본 plan = Pod 환경만 박제, Lambda 는 별 plan 책임.

## Self-Check: PASSED

- All created files verified present:
  - `backend/tests/test_runpod_startup_gemini.py` (217 lines)
- All modified files verified present:
  - `backend/runpod_inference/requirements.txt` (41 lines)
  - `backend/runpod_inference/setup.sh` (144 lines)
  - `backend/runpod_inference/server.py` (218 lines)
- All 3 commit hashes verified in `git log main..HEAD`:
  - `bafd236` feat(05-04) Task 1
  - `e3686c4` test(05-04) RED
  - `89cbb71` feat(05-04) GREEN
- 4 Plan 5-04 tests PASS (test_runpod_startup_gemini.py)
- Analysis core regression PASS (test_dimensions + test_features + test_assemble = 30 tests)
- D-12 server.py 외부 시그너처 무변경 박제 PASS
- D-16 lazy import 박제 PASS (google-genai / boto3 module-level import 0 at server.py load)
