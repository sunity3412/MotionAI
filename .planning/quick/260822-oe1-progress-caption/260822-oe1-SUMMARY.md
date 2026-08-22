---
phase: quick-260822-oe1
plan: 01
subsystem: app-illustration
tags: [progress-caption, how-overlay, kip-up, noise-threshold, measure-first]
requires:
  - "quick-260821-gb7 (킵업 20-1 승인 그림 + baked 오버레이 배선)"
  - ".planning/quick/260822-oe1-progress-caption/NOISE-MEASUREMENT.md (Task 1 실측)"
provides:
  - "킵업 다리 상세 시트 수치 문장 아래 발전 캡션 '저번보다 더 벌어졌어요' (belle 08-21 원문)"
  - "노이즈 문턱 실측 산출물 + 재측정 도구 (measure_noise.mjs)"
  - "progressCaption 순수 lib (직전 분석 선택 / record 추출 / 캡션 판정)"
affects: [결과 화면 다리 부위 상세 시트 표시 (DeductionDetailSheet 코드 무접촉)]
tech-stack:
  added: []
  patterns:
    - "measure-first: 판정 규칙 커밋 → 측정 → 산출값만 소비 (문턱 상수 출처 주석)"
    - "캡션 문구 단일 소스 = HOW_ANCHORS progressSentence (데이터 opt-in, 코드 분기 0)"
key-files:
  created:
    - .planning/quick/260822-oe1-progress-caption/NOISE-MEASUREMENT.md
    - .planning/quick/260822-oe1-progress-caption/measure_noise.mjs
    - app/src/lib/progressCaption.ts
    - app/src/lib/__tests__/progressCaption.test.ts
    - .planning/quick/260822-oe1-progress-caption/sim_progress_caption.png
    - .planning/quick/260822-oe1-progress-caption/sim_no_caption_baseline.png
  modified:
    - app/src/lib/illustrationHow.ts
    - app/src/components/DefectIllustration.tsx
    - app/src/app/analysis/result.tsx
decisions:
  - "threshold_deg = 12 — 사전 박제 규칙(풀링 P95) 그대로. 측정 후 소급 수정 0"
  - "캡션은 오버레이 게이트 뒤 카드 아래 Text — 오버레이 안 두 번째 pill 금지 (gb7 화살표 가림 전례)"
  - "직전 분석 조회 = useMyAnalyses({doneOnly}) 재사용 — 신규 Firestore 쿼리 0"
metrics:
  duration: "약 20분 (2026-08-22T08:43Z ~ 09:03Z)"
  completed: "2026-08-22"
  tasks: 3
  tests: "208 중 207 통과 (기지 실패 1건만 — 기준선 198/197+1 에서 신규 10축 전부 통과, 회귀 0)"
---

# Quick 260822-oe1: 발전 캡션 배선 (belle 08-21 "저번보다 더 벌어졌어요") Summary

같은 동작(mode1 referenceMotionId 동일) 직전 done 분석 대비 편차가 실측 노이즈
문턱(12°) 이상 줄었을 때만, 킵업 다리 상세 시트의 수치 문장 아래에 belle 화법
원문 캡션이 붙는다 — 시뮬 실렌더로 표시/미표시 양면 실증 완료.

## 실행한 것 (실측·실행으로 성립)

### Task 1 — 노이즈 문턱 측정 (measure-first)

- **git 순서 준수**: 판정 규칙 커밋 `73927250` → 측정 결과 커밋 `5458fd8f`
  (규칙이 수치보다 먼저 — 측정 후 규칙 소급 수정 0).
- 실측 (Firestore 읽기 전용, select 필드 마스크): done doc 972 / deg record
  보유 356 / 페어 282 (같은-영상 59 + 48h 세션 248 중 표본 기여분) /
  |Δdelta| 표본 1017 → **풀링 P95 = 11.60 → threshold_deg = 12**.
- 예측 적중: 결정론 ON(08-09 이후) 같은-영상 페어 표본 5건 전부 |Δdelta| = 0.00.
- 쓰기 API 호출 0 · PII 산출물 유입 0 (uid 6자 절단, bodyProfile·URL 미수집).

### Task 2 — 캡션 배선 (TDD)

- RED `80fdc3d1` (모듈 부재로 전체 FAIL 확인) → GREEN `acb663fa` → 배선 `e7de632a`.
- `progressCaption.ts`: `findPreviousComparable` / `extractCriterionMeasure` /
  `buildProgressCaption` — fail-closed 전 축 (문턱 null·prev 없음·unit·non-finite·
  미달·악화·앵커 부적격) 테스트 봉인. 문턱·앵커는 테스트 주입용 마지막 인자.
- `PROGRESS_NOISE_THRESHOLD_DEG = 12` — 출처 주석이 NOISE-MEASUREMENT.md
  (측정일·페어 수·P95)를 가리킨다. null 이면 전면 비활성 의미도 주석 명기.
- `HOW_ANCHORS['ref-kip-up--leg'].progressSentence = '저번보다 더 벌어졌어요'`
  (BELLE-0821-P2 원문, 단일 소스 — 사본 0). 다른 에셋은 필드 부재 = 자동 미대상.
- `DefectIllustration`: `prevHow` prop — **오버레이(수치 문장)가 있을 때만**
  판정, 캡션은 카드 아래 Text (theme 토큰 typography.caption + textMid).
- `result.tsx`: `useMyAnalyses({doneOnly:true})` 무조건 호출(M-04),
  illustrationSlot 클로저에서 mode1 만 직전 doc → primaryCriterion record.
- **DeductionDetailSheet.tsx diff 0 · buildHowOverlay 로직 diff 0** (git 확인).

### Task 3 — 전량 회귀 + 시뮬 실증 (양면)

- 전량 게이트: `npm run typecheck` 통과 + `node --test` **208 중 207 통과** —
  실패 1건은 기지(illustrationScene test 8, ref-pdshape/arm provenance,
  08-18 이전부터). 기준선 198/197+1 → 208/207+1, 회귀 0.
- 변경 범위 = 플랜 files_modified + 캡처 2장뿐 (`git diff --stat` 확인).
- 시뮬 실렌더 (iPhone 16 Pro 873D7CB3 + Metro 신선 번들 1425 modules):
  - **(b) 캡션 미표시** `sim_no_caption_baseline.png`: 직전 분석 없음 →
    캡션 없음, gb7 승인 겉모습(그림+화살표 2개+"50° 정도 더 벌리세요" pill)
    그대로 — 육안 대조 일치.
  - **(a) 캡션 표시** `sim_progress_caption.png`: 시뮬 uid 아래에만 직전 doc
    시드(split_angle 70°→0°, createdAt −1일, fileName 'test-progress-oe1.mp4')
    → 개선 20° ≥ 문턱 12° → 수치 문장 아래 **"저번보다 더 벌어졌어요"** 표시.
  - 시드 doc 캡처 후 삭제 (시뮬 uid assert 통과 후에만 — belle uid `csKWYv…`
    쓰기 0) → 캡션 live 소멸 재확인 = 시뮬 계정 상태 복원, 잔류 0.
- **OTA 미발행** (`eas update` 실행 0) — 시뮬·Metro 는 belle 확인용으로 켜 둠.

## 미실증 항목 (정직 구분)

- belle 실기기·실계정 화면 확인 — 시뮬 실증까지만 (verify-ui-on-simulator-before-ota).
- 문턱 미만(0 < 개선 < 12°) 케이스의 시뮬 실렌더 — 단위 테스트로만 봉인
  (시뮬 실증은 표시/직전없음 양면).
- 킵업 외 에셋은 progressSentence 미등재 = 캡션 자동 미대상 (설계 의도, 미실증 아님).

## belle 결정 대기 항목

1. **split_angle 20° 양자화**: 실측에서 split_angle 의 요동은 0 아니면 20
   (vision 측정 양자화). 풀링 문턱 12 로는 split 한 스텝(20°) 개선이 캡션
   대상이 되는데, 이것이 실력 변화인지 측정 요동인지 풀링 규칙은 구분 못 한다.
   criterion 별 문턱(예: split_angle 전용 상향) 전환 여부 = belle 판단.
   (사전 박제 규칙을 그대로 적용했고 소급 수정하지 않았다 — NOISE-MEASUREMENT.md 관측 절.)
2. **OTA 발행 여부** — 시뮬 확인 후 별도 결정.

## Deviations from Plan

없음 — 플랜 그대로 실행. (Task 3 캡션 미표시 증거를 `sim_no_caption_baseline.png`
로 별도 저장한 것만 추가 — 플랜의 "양면 실증" 요구를 파일로 남긴 것.)

## Commits

| Hash | Type | 내용 |
|------|------|------|
| 73927250 | docs | 판정 규칙 사전 박제 (측정 실행 전 커밋) |
| 5458fd8f | chore | 실측 스크립트 + 측정 결과 — threshold_deg 12 |
| 80fdc3d1 | test | 발전 캡션 판정 실패 테스트 (RED) |
| acb663fa | feat | progressCaption lib + 앵커 progressSentence (GREEN) |
| e7de632a | feat | DefectIllustration prevHow + result.tsx 배선 |
| 3902fd81 | chore | 시뮬 실증 캡처 양면 |

## TDD Gate Compliance

test(80fdc3d1) → feat(acb663fa) 순서 준수. RED 에서 모듈 부재로 전체 FAIL 확인 후 GREEN 14/14.

## Known Stubs

없음 — 캡션 데이터 배선 전부 실측 record·실측 문턱 기반, 플레이스홀더 0.

## Self-Check: PASSED

파일 7종(측정 산출물·스크립트·캡처 2장·lib·테스트·SUMMARY) 전부 존재, 커밋 6건
(73927250·5458fd8f·80fdc3d1·acb663fa·e7de632a·3902fd81) git log 확인.
