---
phase: quick-260821-exq
plan: 01
subsystem: illustration
tags: [ghost-noarrow, kip-up, gemini, belle-gate]
requires: []
provides:
  - "ghost-noarrow 3단계(20/40/60) 잔상 6장 — belle 판정용 실물"
  - "meta.json stage→deficit→파일명 매핑 (배선 재료)"
affects: []
tech-stack:
  added: []
  patterns: ["importlib.spec_from_file_location 로 승인 레시피 재사용 (L-4 무변경)"]
key-files:
  created:
    - .planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/generate_ghost3.py
    - .planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/PREDICTION.md
    - .planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/meta.json
    - .planning/quick/260821-exq-3-ghost-noarrow-20-40-60-belle/out/ (이미지 6장 + 프롬프트 3개)
  modified: []
decisions:
  - "탈락 stage40-1 사유 = 방향 역전(잔상이 실선보다 넓음) — 예측에 없던 실패 모드로 기록"
metrics:
  duration: "약 8분"
  completed: "2026-08-21"
---

# Quick 260821-exq: 3단계 ghost-noarrow 잔상 (20/40/60) Summary

킵업 다리 ghost-noarrow 잔상을 deficit 3단계(20°/40°/60°)로 스테이지당 2장씩
총 6장 생성 — 6장 전부 표기 0(D-03) 유지, 내 눈 5/6 사용 가능, belle 판정 대기.

## 해낸 것

- **Task 1** (71fbd72f): `generate_ghost3.py` — 260809 generate.py 를 importlib 로
  로드해 승인 레시피(PROMPT 골격·익명·의상·프레이밍) 무변경 재사용, 260818-nnm
  `HOW_GUIDE["ghost-noarrow"]` 원문에서 잔상 다리 서술 절만 3단계 치환.
  PREDICTION.md 예측(축 3개 + 장부 5전째) 포함 — **out/ 이미지가 생기기 전에 커밋**
  (예측 박제 게이트 준수, git 이력으로 증명 가능).
- **Task 2** (f5c2716c 에 포함): Gemini 키를 SSM→환경변수로만 주입해 6장 전부
  1차 시도에 생성 성공 (재시도 0). `out/prompt_stage{20,40,60}.txt` 3개 저장,
  3개 전부 "NO arrows" 절 확인. `meta.json` = stage→deficitDeg(20/40/60)→실존
  파일명 매핑.
- **Task 3** (f5c2716c): **6장 전부 Read 도구로 직접 열어** 자평을 PREDICTION.md 에
  박제 — 예측 대조표 + 스테이지별 추천/탈락 사유 + "내 눈" 단서.

## 자평 요지 (belle 판정 전 — 상세는 PREDICTION.md)

- D-03 스크린: 6장 전부 화살표·수치·텍스트·빨간 표시 **0**. 두 번째 사람 오독 **0**.
- 쓸 만한 장 **5/6** (예측 4/6). 유일한 탈락 = `stage40-1`: 잔상 다리가 실선보다
  **더 벌어져**(거의 수평) "지금→목표" 방향이 역전 — 예측에 없던 실패 모드.
- 추천 세트: `stage20-1` / `stage40-2` / `stage60-2` — 나란히 놓으면 "약간 좁음 →
  절반 → 거의 모음" 단계가 읽히나, 20↔40 간격이 40↔60 보다 좁아 보이는 불균등 계단.
- 예측 성적: 축① 부분 적중(간격 압축 위험 실재, 실패 형태는 다름) / 축② 빗나감
  (stage60 합쳐짐 0건 — 비관 과대) / 축③ 1장 비관 + 실패 모드 오예측.

## 커밋

| 커밋 | 내용 |
|---|---|
| 71fbd72f | docs: 예측 박제 + 하네스 (생성 전 — 게이트 커밋) |
| f5c2716c | feat: 이미지 6장 + 프롬프트 3개 + meta.json + 자평 |
| 79025fd | docs: PLAN.md 박제 (Task 3 verify 의 quick dir 잔여 0 충족) |

## Deviations from Plan

**1. [Rule 3 - 블로킹] PLAN.md 커밋 추가**
- **발견 시점:** Task 3 verify
- **문제:** PLAN.md 가 미추적 상태라 "quick dir 미커밋 잔여 0" verify 가 실패
- **처리:** PLAN.md 는 금지 목록(SUMMARY/STATE)에 없어 docs 커밋(79025fd)으로 박제
  (260818-muy 선례와 동일)
- **파일:** 260821-exq-PLAN.md

그 외 플랜 그대로 실행. 인증 게이트 없음, 재시도 없음, app/ 변경 0.

## 다음 (범위 밖 — 오케스트레이터/belle 몫)

- belle 판정용 아티팩트 게시 (추천 3장 + 탈락 3장, 세트 나란히 보기)
- 승인 시: meta.json 기반 앱 배선 (학생 값→가까운 스테이지 선택 로직) — 별도 태스크
- 반려 시: 탈락 사유(특히 stage40 방향 역전)를 프롬프트 절로 보강 후 재도전

## Known Stubs

없음 — 이 태스크는 배선 없는 판정용 실물 생성이 목표 그 자체 (D-05 배선 금지).

## Self-Check: PASSED

- generate_ghost3.py / PREDICTION.md / meta.json / out/ 6장+3프롬프트: FOUND
- 커밋 71fbd72f, f5c2716c, 79025fd: FOUND (예측 커밋이 생성물 커밋에 선행)
- app/ 변경: 0 (D-05)
