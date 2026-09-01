---
phase: quick-260901-wbo
plan: 01
subsystem: pipeline-deferred-stages
tags: [coach-defer, loading-time, contract-lockstep, firestore-partial-update]
requires: [phase-27-fault-zoom-deferred, phase-32-coach-audio-deferred]
provides:
  - coachStatus 계약 3중 미러 (contract.md + models.py + analysis.ts)
  - firestore_admin.update_analysis_coach_text (field-path 부분 갱신, 5필드 화이트리스트)
  - pipeline _run_deferred_coach_text 사후 스테이지 (coach_dual + coach_hook)
  - 앱 coachPending placeholder + 진행률 3상수 재보정
affects: [next-pod-e2e, next-app-build]
key-files:
  created:
    - backend/tests/quick_260901_wbo/conftest.py
    - backend/tests/quick_260901_wbo/test_coach_text_contract.py
    - backend/tests/quick_260901_wbo/test_coach_text_deferred.py
  modified:
    - docs/contract.md
    - backend/shared/python/sunity_shared/models.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - backend/functions/pipeline/app.py
    - app/src/types/analysis.ts
    - app/src/app/analysis/result.tsx
    - app/src/app/analysis/loading.tsx
metrics:
  duration: ~25m (2026-09-01T14:36Z ~ 15:00Z)
  tasks: 3/3
  commits: [957cd46c, ff94bdb2, 59692c93]
completed: 2026-09-01
---

# quick-260901-wbo: 코칭 문장 사후 분리 (로딩 단축) Summary

**coach_dual(실측 43.1s) + hook Gemini 콜(~14s)을 complete_analysis 사후
_run_deferred_coach_text 스테이지로 이동 — status 'done' 도착이 코칭 작성을
기다리지 않는다 (fault_zoom D-06 패턴 미러: pending 마커 + field-path 부분 갱신 +
앱 placeholder).**

## 태스크별 결과

| # | 태스크 | 커밋 | 게이트 실측 |
|---|--------|------|------------|
| 1 | 계약 3중 미러 + update_analysis_coach_text | 957cd46c | 신규 계약 테스트 13건 PASS, tsc 0 |
| 2 | coach_dual+hook 사후 스테이지 이동 | ff94bdb2 | 전체 스위트 **4572 passed / 0 failed** (기준선 4548 + 신규 24) |
| 3 | 앱 placeholder + 진행률 재보정 | 59692c93 | tsc 0 · node --test **212 passed / 0 failed** · 시뮬 구 doc 렌더 무회귀 스크린샷 |

## 구현 요지

- **complete 시점**: coach_details={} 고정 → tips 는 수치 폴백(detail2 부재)으로
  항상 유효(required 필드 불변, 구 앱 하위호환). hook 은 canned 부착(기존 except
  폴백과 동일 코드 — "분석 절대 실패 안 함" 보존). `result["coachStatus"]='pending'`
  마커(mode1·mode3 무조건) + complete `gemini_b=None`.
- **사후 스테이지** (`_run_deferred_coach_text`, complete 직후 · coach_audio 앞):
  coach_dual 13-C 듀얼트랙(재시도·cross-fill·audit) 로직 무수정 이동 + coach_hook
  별도 계측 신설. 성공 → `update_analysis_coach_text(done, tips 재조립분,
  hook Gemini 승격분, geminiB)` + in-memory result 동기 갱신
  ([[partial-field-writes-invisible-to-inmemory-doc]] 갑주). 양쪽 writer 실패 →
  FAILED + both_failed audit, tips 미전송(수치 폴백 잔존 = 최후 바닥). 재raise 0.
- **체커 warning 1 이행**: hook field-path 는 complete 에 전달된
  force_pattern_inference_dict / body_comparison_report_dict 가 비-None 일 때만
  전송 (동기 attach 조건 미러) + update_analysis_coach_text 쪽도 None hook 은
  payload 생략 — `.update()` 중간 map stub 리포트 생성 차단. 테스트 (b′) 포함.
- **체커 info 이행**: `_force_findings`/`_body_findings` 기본값 [] 호이스팅
  (force_signals_report 미산출 경로에서도 바인딩 보장).
- **앱**: `coachStatus==='pending' && !timedOut(180s)` 에서만 코칭 팁 섹션
  placeholder 카드 1장 (ActivityIndicator brand + "AI 코치가 교정 문장을 작성하고
  있어요", 토큰만). legacy(부재)/done/failed/상한초과 = 기존 tips 렌더 그대로.
  onSnapshot 구독 재사용 — 신규 폴링 0. primaryFault·coachCommentHook 소비부 무접촉.
- **진행률**: PROGRESS_PCT(8/16/30/42/48) + PROGRESS_CEIL(15/28/40/47/97) +
  creep 2500→1500ms — 총 파이프라인 ~60s 기대로 재배분, comparison 2분 기어오름
  제거 (단조 로직/creep 메커니즘 무변경, done 전 100 도달 금지 불변).

## Deviations from Plan

**1. [Rule 2] _run_deferred_coach_text 시그니처에 kwarg 2개 추가**
- **Found during:** Task 2
- **Issue:** 계획 명세 시그니처(result/assessments/coach_context/force_findings/
  body_findings/uid/analysis_id/timings_ms)로는 체커 warning 1 이 요구하는
  "리포트가 doc 에 실렸을 때만 hook 전송" 판정이 불가능 — complete_analysis 가
  리포트를 payload 에만 부착하고 in-memory result 에는 싣지 않는다.
- **Fix:** `force_pattern_inference_dict` / `body_comparison_report_dict` kwarg
  추가 (complete 에 전달된 바로 그 dict — hook 전송 게이트 + in-memory hook 동기
  갱신 대상). docstring 에 사유 명기.
- **Commit:** ff94bdb2

**2. [검증 보조] 시뮬 구 doc 확보를 위해 Firestore doc 1건 복사**
- **Found during:** Task 3 (3) 시뮬 눈검증
- **Issue:** 직전 quick 태스크들(my-tab 로그아웃 테스트)이 시뮬 익명 세션을
  로그아웃시켜 현재 게스트 uid 에 분석 기록 0건 — 구 doc 결과 화면을 열 수 없었다.
- **Fix:** firebase-admin 으로 기존 done 분석(코칭 detail2 3건, coachStatus 부재)
  1건을 시뮬 게스트 uid 로 복사:
  `users/k9fQlhw2Picwql31ooLlmmAcwbm2/analyses/wbo-legacy-0e53101b`
  (원본 users/8fPsUnXWNiOW9Y6cawCMcHGVb6z1/analyses/0e53101b…, 08-31 파워스핀 60점).
  검증 전용 — 다음 Pod E2E 의 구/신 doc 교차 확인에도 재사용 가능. 불필요 시
  해당 doc 삭제로 원복. 임시 복사 스크립트는 실행 후 삭제(리포 무접촉).
  ⚠ 이 doc 은 평가/검증 사본 — 사용자 행동 데이터로 읽지 말 것.

## 시뮬레이터 눈검증 (iPhone 16 Pro, iOS 18.6, dev build + 현재 번들)

screens/ 11장. 핵심 = `90-coaching-tips-legacy.png`:
구 doc(coachStatus 부재, 파워스핀 mode1 60점) 결과 화면에서 "코칭 팁" 섹션이
코칭 3카드(왼쪽 어깨 자세각/왼쪽 무릎 신전/왼쪽 고관절 가동 — cue 배지 + 코칭
문장 + "자세히 ›" detail2 링크) 전부 **종전대로** 렌더 — placeholder 미표시,
크래시 0. Metro 로그 에러 0 (playback-url 400 은 복사 doc 의 비정규 analysisId
형식 때문 — graceful 강등 경로 정상 작동, 본 변경과 무관).

## 검증 실측 (전부 이번 실행에서 직접 실행)

- 백엔드: `.venv/bin/python -m pytest tests` → **4572 passed, 20 skipped, 0 failed**
- 앱: `npx tsc --noEmit` → 0 에러 / `node --test "src/lib/__tests__/*.test.*"` → **212 passed / 0 failed**
- 계약 3중 미러: contract.md coachStatus 절 + models.COACH_STATUSES +
  analysis.ts coachStatus? 세 곳 동시 존재 (한 커밋 957cd46c)
- 소스 게이트 테스트: _process 에서 pending 마커 < complete 순서 + coach 동기 산출
  (assemble_dual_coach_sections/_gemini_b_audit_payload/GeminiCoachHookWriter) 소멸 증명

## 검증 불가 항목 — 완료 주장 금지 (다음 Pod E2E)

**pending→채움 라이브 검증은 이 실행에서 불가능했다** (Pod 미기동 — 분석 실행
경로 없음). 아래는 다음 Pod 기동 때 확인할 것 (Pod 는 기동 시 git pull 로 이
코드 수령, 앱은 다음 빌드 1.2.2+):

- [ ] 신규 분석 1건: status 'done' 이 coach_dual 이전에 도착하는지 실측
      (timingsMs 에 coach_dual/coach_hook 부재 + complete 조기 도착)
- [ ] 앱 placeholder → 코칭 텍스트 자동 승격 (onSnapshot 재렌더) 육안 확인
- [ ] Pod 로그에 coach_dual / coach_hook 사후 스테이지 stage_timing 라인
- [ ] geminiB audit 이 사후 부분 갱신으로 doc 에 실리는지
- [ ] 구 앱(1.2.1) + 신 doc: 수치 폴백 즉시 표시 → 코칭 승격 (크래시 0)
- [ ] 신 앱 + 구 doc: 즉시 표시 무회귀 (시뮬로 1차 확인 완료 — 실기기 재확인)
- [ ] (병행 가능) 파워스핀·킵업 페어 라이브 E2E 재실행 (08-31 이월분)

## Known Stubs

None — placeholder 는 coachStatus='pending' 신 doc 에서만 발동하는 실배선이며,
데이터 소스(onSnapshot)와 해제 경로(done/failed/타임아웃) 전부 배선 완료.

## Self-Check: PASSED

- 파일: 신규 3(tests) + 수정 7 전부 존재 확인 (grep 실측)
- 커밋: 957cd46c / ff94bdb2 / 59692c93 git log 존재 확인
- 게이트: 백엔드 0 failed · tsc 0 · node 0 failed — 전부 이번 실행에서 직접 실행
- 미검증 항목은 위 "검증 불가" 절에 정직 기재 (통과 주장 0)
