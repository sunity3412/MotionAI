---
phase: quick-260901-wbo
verified: 2026-09-02T00:20:00Z
status: human_needed
score: 6/6 must-haves verified
overrides_applied: 0
human_verification:
  - test: "다음 Pod 기동 시 신규 분석 1건 라이브 E2E — status 'done' 이 coach_dual 이전 도착 실측 (timingsMs 에 coach_dual/coach_hook 부재 + complete 조기 도착), Pod 로그에 coach_dual/coach_hook 사후 stage 라인, geminiB 사후 부분 갱신 doc 착지"
    expected: "complete 가 ~57s 앞당겨지고 코칭 텍스트가 사후 부분 갱신으로 도착"
    why_human: "Pod 미기동 상태 — 실분석 실행 경로 없음 (GPU 필수). SUMMARY 도 완료 주장 없이 이월 명시"
  - test: "앱 placeholder → 코칭 텍스트 자동 승격 육안 확인 (신규 분석 결과 화면에서 '작성 중' 카드 → onSnapshot 재렌더로 코칭 카드 교체)"
    expected: "coachStatus pending 동안 placeholder 1장, done 부분 갱신 도착 시 자동 채움 (폴링 0)"
    why_human: "라이브 pending doc 은 Pod 실분석에서만 생성됨 — grep/시뮬로 재현 불가"
  - test: "구 앱(1.2.1) + 신 doc 교차 확인 — 수치 폴백 tips 즉시 표시 → 코칭 승격, 크래시 0"
    expected: "구 앱이 coachStatus 를 몰라도 required tips(수치 폴백)로 정상 렌더"
    why_human: "실기기 구 버전 앱 필요 — 정적 검증 범위 밖"
  - test: "구 doc 결과 화면 렌더 무회귀 스크린샷 belle 확인 (screens/90-coaching-tips-legacy.png — PLAN Task 3 human-check 이월)"
    expected: "legacy doc(coachStatus 부재)에서 코칭 3카드 종전대로 렌더 — placeholder 미표시"
    why_human: "belle 확인용 아티팩트 (verifier 는 스크린샷을 직접 열어 3카드+cue 배지+자세히 링크 렌더를 확인 완료 — 최종 승인만 인간 몫)"
---

# quick-260901-wbo: 코칭 문장 사후 분리 (로딩 단축) Verification Report

**Goal:** coach_dual(43s)+hook(~14s)을 complete_analysis 사후 스테이지로 이동 — coachStatus 계약 3중 미러 + 부분 갱신 + 앱 placeholder + 진행률 재보정. 커밋 957cd46c / ff94bdb2 / 59692c93 (main).
**Verified:** 2026-09-02T00:20:00Z
**Status:** human_needed (자동 검증 전부 PASS — 라이브 E2E 는 다음 Pod 기동 몫)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | status 'done' 이 coach_dual+hook 이전 도착 | ✓ VERIFIED | 소스 게이트 테스트 `test_process_source_gate_pending_before_complete` 직접 실행 PASS — pending 마커(app.py:8224) < complete_analysis(:8227) < `_run_deferred_coach_text`(:8276), 동기 경로에서 `assemble_dual_coach_sections`/`_gemini_b_audit_payload`/`GeminiCoachHookWriter` 소멸(전 발생처가 :4267~4338 사후 함수 내부뿐), complete `gemini_b=None`(:8243). 라이브 실측은 Pod E2E(human) |
| 2 | 신 doc pending → placeholder → onSnapshot 자동 채움 | ✓ VERIFIED | result.tsx:1648 `coachPending = result.coachStatus === 'pending' && !coachPendingTimedOut`, :3215 렌더 분기(placeholder 카드 ↔ displayTips.map), 기존 useAnalysisDoc onSnapshot 구독 재사용(신규 폴링 0). 라이브 채움은 Pod E2E(human) |
| 3 | coachStatus 없는 구 doc 즉시 표시 (렌더 무회귀) | ✓ VERIFIED | 필드 부재 → `coachPending` 자연 false → 기존 tips 렌더. 시뮬 스크린샷 90-coaching-tips-legacy.png 직접 열어 확인 — legacy doc(파워스핀 60점)에서 코칭 3카드(cue 배지+문장+자세히 링크) 종전대로 렌더, placeholder 미표시 |
| 4 | 구 앱 + 신 doc 크래시 없음 (tips 수치 폴백 + canned hook) | ✓ VERIFIED | `test_complete_tips_are_numeric_fallback_shape` PASS (coach_details={} → tips 3건, detail2 부재, 수치 폴백 문구). hook 은 complete 시점에 `build_canned_hook` 으로 항상 부착(app.py:7920~7947). complete_analysis 는 result 키 whitelist 없음 — scalar coachStatus 통과(faultZoomStatus 선례 동형). 실기기 교차는 Pod E2E(human) |
| 5 | 사후 스테이지 실패 시 done 유지 + 수치 폴백 잔존 | ✓ VERIFIED | `_run_deferred_coach_text` 전 경로 재raise 0 (외곽 except → FAILED 마킹 시도, 마킹 write 실패도 log.exception 만 — app.py:4416~4436). 테스트 `test_both_writers_failed_marks_failed_without_tips` / `test_stage_exception_marks_failed_no_reraise` / `test_failed_marking_write_exception_swallowed` PASS — FAILED 시 tips 미전송(수치 폴백 잔존) |
| 6 | 진행률 comparison 2분 기어오름 제거 | ✓ VERIFIED | loading.tsx PROGRESS_PCT(8/16/30/42/48/100/0) + PROGRESS_CEIL(15/28/40/47/97/100/0) + PROGRESS_CREEP_MS 2500→1500 — 계획 명세와 값 일치. 구 229.6s 서술은 "코칭 동기 시절 값이라 폐기" 로 명시된 역사 각주로만 잔존(:87), 새 근거(ea975e6e 실측 + 사후화 반영) 주석 교체 확인 |

**Score:** 6/6 truths verified (라이브 E2E 항목은 계획 자체가 "이 계획에서 완료 주장 금지"로 스코프 밖 — human 항목으로 이월)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/shared/python/sunity_shared/models.py` | COACH_STATUS_* + COACH_STATUSES | ✓ VERIFIED | :663~670, FAULT_ZOOM_STATUSES 블록 미러 서술(:648~662) — PIPELINE_SEQUENCE 추가 금지 명기 |
| `backend/shared/python/sunity_shared/firestore_admin.py` | update_analysis_coach_text | ✓ VERIFIED | :1625~, status enum 강제 + field-path `.update()` 5필드 화이트리스트 + None hook payload 생략(stub-map 가드 writer 측) + `_validate_coach_tips`(:1548) |
| `backend/functions/pipeline/app.py` | _run_deferred_coach_text (complete 뒤·coach_audio 앞) | ✓ VERIFIED | :4196~4436 본체(coach_dual+coach_hook _stage), 호출부 :8276 — coach_audio(:8298) **앞**. 동기 경로 coach_details={} 고정(:7614) + canned hook(:7917~) + findings [] 호이스팅(:7882~7883) |
| `docs/contract.md` | coachStatus 절 (faultZoomStatus 미러) | ✓ VERIFIED | :506~531, 사후 변경 경계(D-03) 5 field-path 명기 + lockstep 3면 지목 |
| `app/src/types/analysis.ts` | coachStatus?: TS 미러 | ✓ VERIFIED | :938 `coachStatus?: 'pending' | 'done' | 'failed'` — faultZoomStatus(:928) 인접, Python lockstep 주석 |
| `app/src/app/analysis/result.tsx` | COACH_PENDING_TIMEOUT_MS + placeholder | ✓ VERIFIED | :145 `180_000` + 근거 주석, :1634~1649 effect(updatedAt 재무장, 상한 초과 즉시 폴백), :3215 렌더 분기 |
| `app/src/app/analysis/loading.tsx` | 재보정 PROGRESS_PCT/CEIL | ✓ VERIFIED | 계획 명세 값과 일치 (위 truth 6) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| pipeline app.py | result.coachStatus | complete 직전 pending 마커 | ✓ WIRED | :8224 `result["coachStatus"] = models.COACH_STATUS_PENDING` — mode1·mode3 공통 경로, faultZoomStatus 선례 동형 |
| _run_deferred_coach_text | update_analysis_coach_text | 사후 부분 갱신 | ✓ WIRED | done(:4402 — tips+force_hook+body_hook+gemini_b) / both-failed(:4372) / 예외 FAILED(:4425). 3중 계약 5필드 전부 커버 |
| result.tsx | result.coachStatus | useAnalysisDoc onSnapshot | ✓ WIRED | 기존 구독 재사용 — `coachStatus === 'pending'` 게이트(:1637, :1649), 신규 폴링 0 |

### Data-Flow / Guard Trace (Level 4)

| Check | Status | Evidence |
|-------|--------|----------|
| stub-map 가드 (caller 측) | ✓ | app.py:4367~4370 — `force_pattern_inference_dict is None` → `force_hook_camel = None` (body 동형), complete 에 전달된 바로 그 dict 로 판정 (Deviation 1 kwarg 2개가 이 판정을 가능케 함 — 합리적 계획 이탈) |
| stub-map 가드 (writer 측) | ✓ | firestore_admin: hook None → 해당 field-path payload 생략 — `.update()` 중간 map 자동 생성 차단, docstring 에 사유 명기. 테스트 `test_body_hook_omitted_when_report_absent` PASS |
| in-memory result 동기 갱신 | ✓ | app.py:4408~4409 (tips/coachStatus), :4411~4415 (hook — complete 에 전달된 dict 직접 교체). [[partial-field-writes-invisible-to-inmemory-doc]] 갑주 확인 |
| 사후 D-03 경계 | ✓ | update_analysis_coach_text payload 는 result.coachStatus/result.tips/hook 2 field-path/geminiB/updatedAt 뿐 — 점수·records 접촉 0 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 신규 테스트 24건 | `.venv/bin/python -m pytest tests/quick_260901_wbo -q` | 24 passed in 0.41s | ✓ PASS |
| 백엔드 전체 스위트 | `.venv/bin/python -m pytest tests -q` | **4572 passed, 20 skipped, 0 failed** (46.7s) — SUMMARY 주장과 일치, 채점 기준선 무손상 | ✓ PASS |
| 앱 typecheck | `npx tsc --noEmit` | 0 에러 (exit 0) | ✓ PASS |
| 앱 node 테스트 | `node --test src/lib/__tests__/*.test.*` | 212 passed / 0 failed | ✓ PASS |
| 커밋 실존 | `git show --stat 957cd46c ff94bdb2 59692c93` | 3건 전부 main 에 존재, diffstat 이 SUMMARY key-files 와 일치 | ✓ PASS |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| (없음) | 3커밋 추가 라인 전수 grep — TBD/FIXME/XXX/HACK/PLACEHOLDER 0 | - | - |

참고: 앱의 "작성 중" 카드는 스텁이 아니라 계약된 pending 상태 표현물 — 데이터 소스(onSnapshot)·해제 경로(done/failed/180s 상한) 전부 배선 확인.

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| quick-260901-wbo (계약 3중 미러 + 사후 스테이지 + placeholder + 진행률) | ✓ SATISFIED | 위 truths 1~6 + artifacts 7종 전부 |

### Human Verification Required

#### 1. 다음 Pod E2E — 라이브 사후 분리 실측
**Test:** Pod 기동(git pull 수령) 후 신규 분석 1건 — timingsMs 에 coach_dual/coach_hook 부재 + complete 조기 도착 + Pod 로그 사후 stage 라인 + geminiB 사후 착지.
**Expected:** 'done' 이 ~57s 앞당겨 도착, 코칭은 부분 갱신으로 후속 도착.
**Why human:** Pod 미기동 — 실분석 실행 경로 없음 (GPU 필수). SUMMARY 가 정직하게 미완 이월.

#### 2. 앱 placeholder → 코칭 승격 육안
**Test:** 위 분석의 결과 화면에서 "AI 코치가 교정 문장을 작성하고 있어요" 카드 → 자동 교체 확인.
**Expected:** pending 동안 placeholder 1장, done 도착 시 onSnapshot 재렌더.
**Why human:** 라이브 pending doc 은 실분석에서만 생성.

#### 3. 구 앱(1.2.1) + 신 doc 교차
**Test:** 구 버전 실기기로 신 doc 열기.
**Expected:** 수치 폴백 tips 즉시 표시 → 코칭 승격, 크래시 0.
**Why human:** 실기기 구 버전 필요.

#### 4. 구 doc 렌더 무회귀 스크린샷 belle 확인 (PLAN human-check 이월)
**Test:** screens/90-coaching-tips-legacy.png 확인.
**Expected:** legacy doc 코칭 3카드 종전 렌더.
**Why human:** belle 승인용 아티팩트 — verifier 는 스크린샷 실물을 직접 열어 렌더 무회귀를 확인 완료.

### Gaps Summary

갭 없음. SUMMARY 주장 대 코드 실물 불일치 0건 — 특히 (1) "다음 Pod E2E" 이월 항목이 완료로 둔갑하지 않았고(체크박스 미체크 + "완료 주장 금지" 명기), (2) Deviation 1(kwarg 2개 추가)은 stub-map 가드를 성립시키기 위한 필연적 이탈로 코드·docstring·테스트가 정합, (3) Deviation 2(검증용 Firestore doc 복사 wbo-legacy-0e53101b)는 검증 전용으로 명시됨 — 사용자 행동 데이터로 읽지 말 것 각주까지 부착. 자동 검증 전 게이트 PASS — 남은 것은 Pod 기동이 필요한 라이브 E2E 4항목(위 human 절)뿐.

---

_Verified: 2026-09-02T00:20:00Z_
_Verifier: Claude (gsd-verifier)_
