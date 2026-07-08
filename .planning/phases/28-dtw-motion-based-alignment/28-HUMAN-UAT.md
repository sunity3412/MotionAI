---
status: partial
phase: 28-dtw-motion-based-alignment
source: [28-08-PLAN.md Task 5]
started: 2026-07-08T13:15:31Z
updated: 2026-07-08T13:15:31Z
channel: preview
ota_group: 577ac5e9-2816-4d9b-bd9f-559aa74b8213
ota_commit: b6a14a8
---

## Current Test

[awaiting human testing — preview 채널 OTA 수신 빌드(TestFlight #27 계열)에서 확인. batch UAT (phase 31 이후 합동) 적립분. production OTA(Task 6)는 이 확인 approved 전까지 미발행.]

## Context (재분석 doc)

Task 3 재분석 = power-spin **fault** fixture 1건 (uid `phase28eval` / analysisId `powerspinFaultAlign1783516096`, mode1 vs ref-power-spin). 결과 = status done / overallScore 52 (문서화된 결정론 baseline 과 일치 — 채점 무접촉) / DOC_CHECK_OK.

**중요 caveat — 이 재분석 doc 의 tier = `disabled` (reason=low_global_confidence, DTW distance 60.13 > T2=25.0).** fault 영상(학생이 틀리게 수행)은 reference(정은지 정타)와 전역 DTW 유사도가 낮아 워핑을 끄고 legacy 동기 재생으로 폴백하는 **설계된 안전 동작**(tier 사다리: ≤8.0→warped / ≤25.0→trim_only / else→disabled). 따라서 **이 doc 에서는 워핑이 아니라 "disabled" tier 배지 + 기존 동기 재생**이 보인다. 워핑(tier=warped) 체감은 학생이 reference 를 근접히 따라간 doc(실제 학생 시연 or correct fixture)에서 확인 필요. 워핑 경로 자체는 28-04/05/06 단위검증 완료.

## Tests

### 1. 비교 재생 정렬 체감 (D-01 / A2)

expected: 비교 재생 시 정은지가 학생 동작을 중반 템포까지 따라온다(D-01 체감). rate 구간 경계에서 stutter(끊김) 없이 부드럽게 재생. (tier=warped doc 기준 — disabled doc 은 legacy 동기 재생.)
result: [pending]

### 2. 스크럽/재시작 동기 유지 (Pitfall 7)

expected: 스크럽하거나 재시작한 직후에도 두 영상 동기가 유지된다. 보정 seek 이 연발되며 튀는 현상 없음.
result: [pending]

### 3. tier 배지 카피 (D-02 사다리)

expected: 결과 화면에 tier 배지가 표시된다 (warped / trim_only / disabled 중 해당 doc 의 tier). 재분석한 power-spin fault doc 은 "disabled" 배지가 정상.
result: [pending]

### 4. legacy 재분석 유도 배너 (D-05)

expected: 정렬 정보 없는 기존(legacy) 분석 doc 을 열면 "다시 분석하면 자동 구간 맞춤이 적용돼요" 배너 + 재분석 CTA 라우팅이 뜬다.
result: [pending]

### 5. 확대비교 카드 정합 (D2 종결 / D-04)

expected: 확대비교 카드에서 정은지 측이 학생과 같은 동작 순간을 보여준다(D2 크롭 이탈 종결). 실패(전신 붕괴) 카드는 "전신 화면" 캡션.
result: [pending]

### 6. mode3 second+ 확대카드 시각 정합 (CR-01 fix 확인)

expected: mode3 두 번째 이상 분석의 확대비교 카드에서 이전 영상 측이 학생과 같은 동작 순간을 보여준다 (리뷰 CR-01: prev 9fps angles vs 18fps 업샘플 keypointReport 도메인 fix — f814b23). 결과 화면 진입→이탈 반복 시 크래시 없음(WR-05 released-player 가드).
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps

- 재분석 doc(power-spin fault) = tier disabled → 워핑(tier=warped) 체감은 별도 doc 필요. "1건만" 제약(pipeline-not-concurrency-safe-eval-serial) 준수로 이 게이트에서는 warped doc 미생성. 워핑 경로는 단위검증(28-04/05/06)으로 커버.
