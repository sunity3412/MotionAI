# Phase 25 — Pod 6페어 Serial Sweep Evidence

> **상태: PENDING — sweep 미실행 (스켈레톤).** 25-04 Task 1(harness/게이트)은 완료·커밋됨.
> Task 3(Pod sweep)은 orchestrator 가 실행 후 이 문서를 완성한다.

## Task 2 체크포인트 기록 — Gemini 크레딧 (해소됨)

- **belle 확인 (2026-07-04): 자동결제 설정 확인 — 크레딧 OK.** cold sweep 36 pro call
  + 멤버당 영상 2 업로드 분량 감당 가능. blocking 대기 불필요 상태로 해소.
- 잔여 방침: sweep 중 429/resource_limited 발생 시 fail-closed 중단 후 belle 보고
  (T-25-10, [[gemini-credits-depleted-2026-06-20]]).

## 실행 조건 (Task 3)

- Pod lsx9kedqsdk1e3 (OD-3 — 살아있음, 재생성 불필요). 로컬 25-01~04 커밋 push →
  pod `git pull` 동기화 → HEAD 확인 → `/health` 확인.
- SERIAL 필수 ([[pipeline-not-concurrency-safe-eval-serial]]). 진행 중 분석과 겹침 금지.
- 커맨드: `backend/evals/phase25/README.md` §Pod sweep (cold → warm → assert_gates).

## 게이트 결과표 (PENDING)

| Gate | 결과 | 비고 |
|---|---|---|
| success_100 (6페어 success == 100) | PENDING | 260702-o0c 재발 금지 |
| pointed_only_window (window ⊆ pointed 전 멤버) | PENDING | SCORE-15 구조 assert |
| kipup_upper_structure (a<baseline / b 상체 record / c pointed) | PENDING | phase24 baseline 88 대비 방향 |
| fault_no_regression (5 fault <= phase24 baseline + climb not_pole) | PENDING | 무퇴행 방향 비교 |
| cold_warm_determinism (verdict/breakdown 동일) | PENDING | warm = 캐시 hit, Gemini 0 call |
| phase24 상속 7 게이트 | PENDING | traceability~sensitivity |

## 6페어 score 표 (PENDING)

| motion | fault (p24 → p25) | success (p24 → p25) | verdict |
|---|---|---|---|
| power-spin | 60 → ? | 100 → ? | ? |
| peter-pan | 79 → ? | 100 → ? | ? |
| elbow-twist-sister | 62 → ? | 100 → ? | ? |
| pdshape | 58 → ? | 100 → ? | ? |
| kip-up | 88 → ? (**<88 + 상체 record 구조 assert**) | 100 → ? | ? |
| climb | not_pole → not_pole 유지? | not_pole → not_pole 유지? | ? |

## 짚기-FP 관측 (최초 관측치 — 게이트 아님, OD-2) (PENDING)

- success 멤버별 Gemini 짚은 관절 목록 + 상체 짚기 빈도 (`pointingFpObservation` 섹션 전사).

## kip-up 구조 assert 상세 (PENDING)

- 상체(shoulder/elbow) angle_vs_reference record + seedObservation.{pointed, window_joints}.
- F(260704-fz4) advisory→confirmed 승격 관측: vision-확인 관절이 confirmed 티어로 나오는지.

## cold/warm 결정론 + 캐시 (PENDING)

- cold: 캐시 전량 miss (PROMPT v10.1 + agg3 bump) — Gemini call 수 기록.
- warm: 캐시 hit (Gemini 0 call) — verdict/breakdown 동일성.

## Follow-up (belle) (PENDING)

- zoom 카드 재생성 여부 + 육안 확인 (25-03 산출 PNG — S3 `zoom_`/`zoom_adv_` 키).
- kip-up 점수 도메인 판정 (88~50 사이 자리 찾음 확인).

## FAIL 시 방침 (박제)

점수 짜맞추기 수정 금지 — 게이트별 원인 분석을 이 문서에 기록하고 구조 원인
(짚기 미발화/과확장/캐시)만 후속 대상으로 박제 후 belle 판단 요청.
