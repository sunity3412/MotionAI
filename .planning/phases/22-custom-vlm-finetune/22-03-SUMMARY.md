---
phase: 22-custom-vlm-finetune
plan: 03
subsystem: infra
tags: [firestore, shadow-logging, pii, distillation, gemini, vlm]

# Dependency graph
requires:
  - phase: 05-gemini-caching
    provides: "store_gemini_cache top-level 컬렉션 + nested-array 사전검증 + ms epoch 패턴"
  - phase: 06-firestore-flat-storage
    provides: "_validate_flat_dict_no_nested_array 범용 validator ([[firestore-nested-array-flat]])"
provides:
  - "firestore_admin.store_vlm_shadow(video_hash, role, payload) — shadow 로깅 단일 진입점"
  - "vlm_shadow/{video_hash} top-level 컬렉션 계약(roles.veto/recognizer/coach deep-merge 누적)"
  - "D-12 PII 키 재귀 거부 helper(_reject_pii_keys) — T-22-07 mitigation"
affects: [22-03-Task2-pipeline-wiring, 22-04-distillation, 22-09-shadow-comparison]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "shadow 로깅 helper: role별 set(merge=True) deep-merge 누적 + created_at 첫 기록 보존(선행 read)"
    - "PII 거부: normalize(lowercase+영숫자) 정확매칭 재귀 denylist — 도메인 스칼라 오탐 0"

key-files:
  created:
    - backend/tests/phase22/test_shadow_wiring.py
  modified:
    - backend/shared/python/sunity_shared/firestore_admin.py

key-decisions:
  - "PII 통제는 화이트리스트(allow-list) 대신 정규화 denylist — 측정 스칼라가 open-ended라 allow-list 열거 비현실적, 실제 D-12 불변식('사용자 식별자 금지')을 denylist로 강제"
  - "created_at 첫 기록 보존은 set(merge=True) 단독으로 불가 → 선행 doc.get() read로 기존 시각 유지(set_reference_motion_with_gemini 선례)"

patterns-established:
  - "vlm_shadow/{video_hash} = gemini_cache 형제 top-level 컬렉션, firestore.rules catch-all default-deny로 클라이언트 접근 차단"

requirements-completed: []  # FT-03/FT-05는 Task 2(배선)·Task 4(Pod 실측) 완료 후 마감 — 본 세션 미완

# Metrics
duration: ~12min
completed: 2026-07-09
---

# Phase 22 Plan 03: Gemini Shadow 로깅 helper (Task 1 부분 실행) Summary

**firestore_admin.store_vlm_shadow — 역할별(veto/recognizer/coach) Gemini 판정을 vlm_shadow/{video_hash}에 flat/ms-epoch/merge/PII-금지 규율로 복제 저장하는 단일 helper (TDD, mocked Firestore).**

> **부분 실행 고지:** 본 세션은 22-03의 **Task 1 (로컬 helper + 단위테스트)만** 실행했다. Task 2 (pipeline app.py 배선 — production 판정 경로 변형), Task 3 (Pod 변형 blocking checkpoint), Task 4 (Pod 배포 + shadow 스모크 + 피크 VRAM 실측)는 **belle-gated + 라이브 GPU Pod 필요**로 후속 세션 이월. **22-03은 IN-PROGRESS** (ROADMAP 미완료 유지).

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-07-09
- **Tasks:** 1 of 4 (Task 1만 — 나머지 3 belle-gated/Pod 이월)
- **Files modified:** 2 (helper 1 modified + test 1 created)

## Accomplishments
- `store_vlm_shadow(video_hash, role, payload)` helper 추가 — vlm_shadow/{video_hash} top-level 컬렉션에 `{ video_hash, created_at, updated_at, roles: {veto, recognizer, coach} }` 구조로 `set(merge=True)` deep-merge 누적.
- role 검증(veto/recognizer/coach), 빈 video_hash reject.
- D-12 PII 키 재귀 거부(`_reject_pii_keys`) — uid/email/userId/phoneNumber 등 식별자 저장 전 차단 (T-22-07 mitigation).
- nested-array 사전 차단 — 기존 `_validate_flat_dict_no_nested_array` 재사용 ([[firestore-nested-array-flat]]).
- created_at 첫 기록 보존 + updated_at ms epoch 갱신.
- 12종 단위테스트 GREEN, Firestore client 전부 mock (실 Firestore/네트워크/Pod 미접촉).

## Task Commits

TDD (test → feat):

1. **Task 1 RED: store_vlm_shadow 실패 테스트** - `f1f2d5b` (test)
2. **Task 1 GREEN: store_vlm_shadow helper 구현** - `f295d1e` (feat)

_REFACTOR 없음 — 구현이 처음부터 clean._

## Files Created/Modified
- `backend/shared/python/sunity_shared/firestore_admin.py` - `_VLM_SHADOW_COLLECTION`, `_VLM_SHADOW_ROLES`, `_VLM_SHADOW_PII_KEYS`, `_normalize_pii_key`, `_reject_pii_keys`, `store_vlm_shadow` 추가 (기존 store_gemini_cache/record_unregistered_keyword 뒤).
- `backend/tests/phase22/test_shadow_wiring.py` - helper 12종 테스트 (mocked Firestore stub + deep-merge/ms-epoch 모사 + PII/nested-array/role/누적 검증).

## Acceptance Criteria (Task 1)
- [x] test_shadow_wiring.py helper 테스트 GREEN — `pytest backend/tests/phase22/test_shadow_wiring.py -k "store_vlm_shadow or helper"` → 12 passed.
- [x] `grep -c store_vlm_shadow firestore_admin.py` ≥ 1 (매치 1, def 라인). nested-array 검증 경로 존재(`_validate_flat_dict_no_nested_array` 호출).
- [x] firestore.rules에서 vlm_shadow 클라이언트 접근 차단 — **근거: firestore.rules 마지막 catch-all 블록** `match /{document=**} { allow read, write: if false; }` (users/·reference/ 밖 컬렉션은 전부 default-deny). vlm_shadow는 backend Admin SDK 전용 (T-22-08 mitigated).
- [x] 전체 phase22 스위트 무회귀 — 67 passed / 2 skipped (skip 2는 기존 pre-existing).

## Decisions Made
- **PII 통제 = 정규화 denylist (allow-list 아님).** 플랜 Test 3 문언은 "화이트리스트 키만 허용"이나 허용 카테고리("측정 스칼라", "frame 인덱스류")가 open-ended라 엄격 allow-list 열거가 비현실적. 실제 위협(T-22-07 = "uid/식별자 키 거부")과 D-12 불변식을 정규화(lowercase+영숫자) 정확매칭 재귀 denylist로 강제. 정확매칭이라 motionName/jointName 등 도메인 키 오탐 0 (test_store_vlm_shadow_allows_domain_scalars로 회귀 방어). 보수적으로 bare `name`도 거부 목록에 포함(식별자 캐리어 위험) — shadow payload는 도메인 특화 키를 써야 함.
- **created_at 보존 = 선행 read.** set(merge=True) 단독으로는 재호출 시 created_at을 덮어씀. set_reference_motion_with_gemini 선례대로 doc.get()으로 기존 시각을 읽어 유지.

## Deviations from Plan

### 계획 대비 축소 실행 (범위 게이트, 코드 일탈 아님)
- **Task 2/3/4 미실행 (의도적).** Task 2 = pipeline/app.py의 production 판정 경로 변형(belle blocking gate), Task 3 = Pod 변형 승인 checkpoint, Task 4 = 라이브 GPU Pod 배포 + VRAM 실측. 본 세션은 명시적으로 **로컬 helper만** 실행하도록 지시받음. 22-03-BASELINE-FAILED.txt / 22-POD-VRAM.md는 Pod 필요로 미생성.

### Task 1 내부 구현 조정
- **[Rule 2 - 보안] PII allow-list → 정규화 denylist 재해석.** 위 Decisions 참조. T-22-07 mitigation을 실제로 강제하기 위한 선택 (사유: allow-list는 open-ended 측정 스칼라를 거부해 실사용 불가). 코드/테스트로 강제.
- **nested-array validator 재사용.** 플랜은 "store_gemini_cache의 nested-array 사전검증을 helper로 재사용/복사"를 지시. 인라인 moments 루프보다 일반화된 기존 `_validate_flat_dict_no_nested_array`를 재사용 — 더 철저(list-of-list TypeError)하고 중복 코드 0.

**Total deviations:** 1 재해석(보안 강화, 코드/테스트 강제) + 1 재사용 선택. 범위 축소는 지시된 게이트에 따른 것으로 scope creep 아님.

## Known Stubs
없음. helper는 완결 — payload를 실제로 검증·저장한다. (production 배선이 아직 이 helper를 호출하지 않는 것은 Task 2 스코프이며, helper 자체는 stub 아님.)

## Threat Flags
없음 (신규 보안 표면 없음 — vlm_shadow는 계획된 T-22-07/T-22-08에 이미 등재, 둘 다 본 helper에서 mitigate).

## Index-Exemption 주의 (후속)
대형 (T,J) 배열이 shadow payload에 flat list로 실릴 경우 Firestore 40k index-entry 한도에 걸릴 수 있다 ([[firestore-index-entry-limit]]). 현재 helper는 flat만 강제(nested reject)하고 index 면제는 강제하지 않음 — Task 2 배선에서 실제 payload 크기 확정 시 `gcloud firestore indexes fields update --disable-indexes` 면제 필요 여부를 재평가할 것 (04-05 reference 컬렉션 선례와 동일 절차).

## Issues Encountered
없음.

## Next Phase Readiness
- **Task 1 완료** — pipeline 배선(Task 2)이 `store_vlm_shadow(video_hash, role, payload)` 계약을 그대로 import할 수 있다.
- **belle-gated 이월:** Task 2(production 판정 경로 변형), Task 3(Pod 변형 blocking checkpoint), Task 4(Pod 배포 + VRAM 실측)는 라이브 GPU Pod + belle 승인 필요. 후속 세션에서 (0) full-suite baseline 캡처 → app.py VLM_SHADOW_LOG 토글 배선 → Pod 스모크 → nvidia-smi 피크 VRAM 순으로 재개.
- **22-03 IN-PROGRESS 유지** — ROADMAP 미완료.

## Self-Check: PASSED
- FOUND: backend/tests/phase22/test_shadow_wiring.py
- FOUND: backend/shared/python/sunity_shared/firestore_admin.py (store_vlm_shadow)
- FOUND: commit f1f2d5b (test)
- FOUND: commit f295d1e (feat)

---
*Phase: 22-custom-vlm-finetune*
*Completed (Task 1 only): 2026-07-09*
