---
phase: quick-260821-fe9
plan: 01
subsystem: illustration
tags: [gemini, pil, kip-up, how-illustration, arrow-grammar, belle-gate]
requires:
  - "260821-exq out/ref-kip-up--leg__ghost-stage20-1.jpg (읽기 전용 소스)"
  - "260809 generate.py 승인 레시피 (무변경 재사용)"
  - "260818-nnm HOW_GUIDE['ghost'] (08-18 belle '가' 통과 변형)"
provides:
  - "A(그림에 굽기) 2장 + B(앱 오버레이 합성) 2장 — belle A/B 판정 재료"
  - "B 발 좌표 4점 meta.json — 나중 배선 앵커 메타 재료"
  - "PREDICTION.md — belle 판정 원문 + 생성 전 예측 + 실물 자평 (장부 6전째)"
affects: []
tech-stack:
  added: []
  patterns: ["importlib spec_from_file_location 승인 레시피 재사용", "PIL 2배 슈퍼샘플 곡선 오버레이"]
key-files:
  created:
    - .planning/quick/260821-fe9-20-a-vs-b/PREDICTION.md
    - .planning/quick/260821-fe9-20-a-vs-b/generate_arrow20.py
    - .planning/quick/260821-fe9-20-a-vs-b/compose_b.py
    - .planning/quick/260821-fe9-20-a-vs-b/meta.json
    - .planning/quick/260821-fe9-20-a-vs-b/out/ (A 2장 jpg + B 2장 png + prompt_A_arrow20.txt)
  modified: []
decisions:
  - "B 표기 2안(화살표 근처)의 패드 우측 가장자리 잘림 → x 클램프 수리 후 재합성 (플랜의 '실물 보고 조정' 범위)"
metrics:
  duration: "8분"
  completed: "2026-08-21"
---

# Quick 260821-fe9: 20 계열 화살표 A/B 실물 대조 Summary

킵업 20 계열에 화살표를 넣는 두 길(A 굽기 vs B 오버레이)을 둘 다 실물로 제작 —
자평 기준 A 는 시작점·잔상 폭 0/2, B 는 좌표 4/4 명중으로 내 픽 = B-1 (belle 판정 전).

## 해낸 것

- **Task 1 (9ed63148)**: PREDICTION.md — belle 08-21 판정 원문(오타 포함) 박제,
  예측 축 3개(A 시작점 위반 1/2 · belle 픽 = B · B 좌표 4/4), 자(화살표 문법이
  "지금 → 목표"로 읽히는가), 장부 5전 1승·6전째 + 직전 판(exq) 불일치 명기.
  **out/ 생성 전에 커밋** — 예측 박제 게이트 준수.
- **Task 2**: `generate_arrow20.py` — exq 하네스 구조 복사(승인 레시피 무변경,
  표준 라이브러리만, skip-existing 재시도), GUIDE 는 HOW_GUIDE["ghost"] 에 3수정
  (잔상 20 서술 치환 / 분리 절 추가 / 화살표 절 강화: 잔상 발 정확 출발 +
  "NEVER start at the pole" + "짧아도 맞다" + NO text). A 2장 생성 성공 (1회 실행).
- **Task 3 (c6dea279)**: 발 좌표 4점을 3배 확대+격자로 눈으로 잡음
  (ghostL 213,1043 / solidL 110,1015 / ghostR 645,1035 / solidR 742,990) →
  `compose_b.py` 로 B 2장 합성(코랄 곡선 화살표 2개 + 소형 표기 1곳, 2배 슈퍼샘플)
  → meta.json → 실물 게이트(4장 전부 Read) → 자평 박제 → 전체 커밋.

## 실물 게이트 결과 (자평 요지)

| 장 | 판정 |
|---|---|
| A-arrow20-1 | 시작점 근접(발에서 ~30px 안쪽, 폴 출발 아님) / 잔상 폭 40 급 (20 수준 위반) / 텍스트 0 |
| A-arrow20-2 | **시작점 위반 — 폴 하단 중앙 출발 (08-18 반려 패턴 재현)** / 잔상 폭 40 급 / 텍스트 0 |
| B-overlay20-1 | 좌표 4/4 명중, 표기 하단 중앙, 한글 정상 — **내 픽** |
| B-overlay20-2 | 좌표 4/4 명중, 표기 화살표 근처, 1차 잘림 수리 후 정상 |

예측 대조: ①A 시작점 위반 1/2 → **적중** (엄격 기준으론 0/2 준수).
②belle 픽 = B → 판정 전, 내 픽 유지. ③B 좌표 4/4 → **적중**.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] B-2 표기 패드 우측 가장자리 잘림**
- **Found during:** Task 3 실물 게이트 (1차 합성 확인)
- **Issue:** 2안 표기 x = 잔상 오른발 +24px 로 두자 패드 우측이 이미지 경계(896px)에 잘림
- **Fix:** 텍스트 폭 계산 후 `x = min(원위치, w - tw - 여백)` 클램프, 재합성으로 잘림 0 확인
- **Files modified:** compose_b.py
- **Commit:** c6dea279 (플랜이 "실물 보고 조정 가능"으로 허용한 범위)

## 범위 준수

- app/ 변경 0, 260821-exq dir(40/60 아카이브) 변경 0 — 기계 확인 (D-01, D-05)
- Gemini 키: SSM → 환경변수로만, 파일·로그·커밋 유입 0 (T-fe9-01)
- 신규 패키지 0 — A 는 표준 라이브러리, B 는 기설치 Pillow 12.2.0 (T-fe9-SC)
- belle 판정용 아티팩트 게시·배선·40/60 재제작은 범위 밖 (오케스트레이터/후속 몫)

## Commits

| Task | Commit | 내용 |
|---|---|---|
| 1 | 9ed63148 | docs: A/B 화살표 예측 박제 + belle 판정 원문 (생성 전) |
| 2+3 | c6dea279 | feat: A 2장 + B 합성 2장 + meta.json + 자평 박제 (플랜 명세의 통합 커밋) |

## Next

- belle 에게 A 2장 + B 2장을 나란히 게시해 A/B 판정 (장부 6전째 채점)
- B 채택 시: meta.json coords 를 앵커 메타로 승격하는 배선 플랜 (별도 라운드, 승인 후)

## Self-Check: PASSED
