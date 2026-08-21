---
phase: quick-260821-gb7
plan: 01
subsystem: app-illustration
tags: [illustration, how-overlay, baked-ghost, kip-up, belle-approved]
requires:
  - ".planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/out/ref-kip-up--leg__ghost-stage20-1.jpg (belle 08-21 승인 원본)"
  - ".planning/quick/260821-fe9-20-a-vs-b/compose_b.py + meta.json (승인 실물 기하·좌표)"
provides:
  - "킵업 다리 부위 상세 시트에 승인 잔상 그림 + 앱 렌더 화살표·수치 문장 (B 방식)"
  - "illustrationHow 판별 union (rotate/baked) — 잔상 구움 에셋 배선 경로"
affects: [DeductionDetailSheet 표시 결과 (코드 무접촉)]
tech-stack:
  added: []
  patterns: ["HowAnchors/HowOverlay 판별 union", "에셋별 종횡비 override 맵 (데이터)"]
key-files:
  created:
    - app/src/lib/__tests__/illustrationHow.test.ts
  modified:
    - app/assets/illustrations/ref-kip-up--leg.jpg
    - app/src/lib/illustrationHow.ts
    - app/src/lib/illustrationScene.ts
    - app/src/components/DefectIllustration.tsx
decisions:
  - "잔상 = 그림에 구움(승인 바이트 무재인코딩), 화살표·문장 = 앱 렌더 — belle 08-21 B 방식"
  - "구 rotate 앵커는 새 그림에 무효라 폐기 (한 에셋에 앵커 두 벌 금지), rotate 기계는 로직 무변경 보존"
  - "baked 수치 문장 pill 은 dirPill 상속 + padding 축소·바닥 밀착 (시뮬 실측 — 화살표 가림 수리)"
metrics:
  duration: "약 15분 (2026-08-21T02:52Z ~ 03:07Z)"
  completed: "2026-08-21"
  tasks: 3
  tests: "198 중 197 통과 (기지 실패 1건만)"
---

# Quick 260821-gb7: 킵업 20-1 승인 그림 실배선 (belle 08-21) Summary

승인 잔상 그림(exq stage20-1)을 md5 동일 바이트로 싣고, 코랄 곡선 화살표 2개(잔상 발→
같은 쪽 실선 발)와 "N° 정도 더 벌리세요" 문장을 앱이 compose_b 기하 그대로 그린다 —
시뮬 실렌더로 승인 실물과 같은 겉모습 확인.

## 완료 내용 (belle 승인 4항목)

| # | 항목 | 구현 |
|---|------|------|
| BELLE-0821-1 | 승인 그림 배선 | `ref-kip-up--leg.jpg` = exq stage20-1 바이트 (md5 `7715a287…` 동일, 재인코딩 0) |
| BELLE-0821-2 | 화살표·표기 앱 렌더 (B) | `BakedHowLayer`: quadratic bezier `M from Q ctrl to` + 접선 화살촉 (compose_b `_arrow` 이식) |
| BELLE-0821-3 | 수치 문장 하단 중앙 | "N° 정도 더 벌리세요" 1곳, N = 학생 측정값 반올림 ("좁다" 금지) |
| BELLE-0821-4 | 회전복사 비활성 | `HOW_ANCHORS['ref-kip-up--leg']` = kind 'baked' (clip/pivot 등 회전 재료 없음) |

- fail-closed 유지: 미등록 asset / unit≠deg / 값 없음 / delta<3° / non-finite → 오버레이 null,
  그림은 표시 (단위 테스트 봉인).
- 장면 표: ref-kip-up × leg → `ref-kip-up--leg`, provenance 를 승인 사실로 갱신.
- 에셋별 종횡비 override 맵 (896x1200 = 1200/896) — 카드 기하와 buildHowOverlay aspect 동일값.
- 다른 19장 에셋·장면 무접촉 (커밋 범위 = 플랜 files_modified 5개뿐, `git diff --stat` 확인).

## 시뮬 실증 — 완료 (실렌더 캡처)

**캡처: `.planning/quick/260821-gb7-20-1-belle-08-21/how_card_20-1.png`**

- 경로: iPhone 16 Pro 시뮬레이터 + Metro 신선 번들(1424 modules) → 기록 탭 →
  킵업 26.07.30 (80점, 프로 비교) → "다리 스플릿 각도" → 다리 부위 상세 시트.
- 실데이터: split_angle record 50°→0° (차이형) → 문장 "50° 정도 더 벌리세요".
- 확인 사항: 잔상 포함 승인 그림 표시 + 곡선 화살표 2개(잔상 발→실선 발, 좌 하강·우 상승
  방향까지 승인 실물 `fe9 out/ref-kip-up--leg__B-overlay20-1.png` 과 일치) + 하단 중앙 문장 pill,
  화살표 가림 없음 (zoom 대조 `scratchpad/sim_card_zoom2.png`).
- 시뮬레이터·Metro 는 belle 확인용으로 켜 둠 (시뮬 UDID 873D7CB3, Metro :8081).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - 시각 결함] baked 수치 문장 pill 이 화살표 몸통을 가림**
- **Found during:** Task 3 (시뮬 실렌더 1차 캡처)
- **Issue:** 시트 카드가 작아(약 189pt 폭) dirPill 원형(padding 14/6 + bottom 3.5%)이
  곡선 화살표 몸통을 덮음 — 승인 실물은 문장이 화살표 아래 여백에 있고, 화살표(잔상 발→
  실선 발)가 이 문법의 핵심이라 가려지면 안 됨
- **Fix:** baked 전용 `bakedDirPill` (padding 10/3, bottom h*0.01) — 색·타이포는
  dirPill/dirText 토큰 상속. 재캡처로 화살표 전체 노출 확인
- **Files modified:** app/src/components/DefectIllustration.tsx
- **Commit:** 8e39d9b5

## Commits

| Hash | Type | 내용 |
|------|------|------|
| 2fbd1da1 | test | baked 오버레이·fail-closed·장면 배선 실패 테스트 (RED 3/4 실패 확인) |
| 3c1e92ac | feat | 승인 에셋 교체 + illustrationHow 판별 union + 장면 표 배선 (GREEN) |
| b5cef123 | feat | DefectIllustration baked 렌더 분기 + 종횡비 override |
| 8e39d9b5 | fix | baked pill 화살표 가림 수리 (시뮬 실측) |

## TDD Gate Compliance

test(2fbd1da1) → feat(3c1e92ac) 순서 준수. RED 에서 신규 축 3/4 실패 확인 후 GREEN.

## 검증 게이트

- `npm run typecheck`: 통과
- `node --test app/src/lib/__tests__/*.test.ts`: 198 중 197 통과 — 실패 1건은 기지
  (illustrationScene test 8, `ref-pdshape/arm` provenance '실물 열람' 부재, 08-18 이전부터).
  기준선 194/193+1 → 198/197+1 (신규 4축 전부 통과, 회귀 0)
- 에셋 md5: 번들 = 승인 원본 (`7715a287b28affb0cc5f6e5003326bb6`)
- 커밋 diff 범위: 플랜 files_modified 5개뿐 — kip-up 외 에셋·장면 무변경
- OTA 미발행 (`eas update` 실행 0) — belle 시뮬 확인 후 별도 결정

## 이연 (범위 밖 — 플랜 명기)

- 발전 캡션 ("저번보다 더 벌어졌어요") = 직전 분석 조회 + 노이즈 문턱 측정 필요

## Known Stubs

없음 — 데이터 배선 전부 실측 record 기반, 플레이스홀더 0.

## Self-Check: PASSED

파일 7종(에셋·lib·테스트·컴포넌트·캡처·SUMMARY) 전부 존재, 커밋 4건(2fbd1da1·3c1e92ac·b5cef123·8e39d9b5) git log 확인.
