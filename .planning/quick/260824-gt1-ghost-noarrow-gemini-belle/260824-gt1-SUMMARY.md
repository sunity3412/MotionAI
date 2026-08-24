---
phase: quick-260824-gt1
plan: 01
subsystem: illustration-assets
tags: [ghost-noarrow, power-spin, gemini, measure-first, prediction-gate]
requires: []
provides:
  - "파워스핀 다리 ghost-noarrow 잔상 후보 4장 (belle 판정 전, 배선 없음)"
  - "leg_extension·split_angle 실사용 record 방향·크기 분포 실측"
  - "meta.json — 파일명→criterion→실측 deficit 매핑 + LLM 사용 기록"
affects: [belle-판정(오케스트레이터), 승인 시 후속 배선 태스크]
tech-stack:
  added: []
  patterns: [importlib 승인 레시피 재사용(D-02), 예측 사전 박제 git 증명, Read 실물 게이트]
key-files:
  created:
    - .planning/quick/260824-gt1-ghost-noarrow-gemini-belle/measure_powerspin_leg.mjs
    - .planning/quick/260824-gt1-ghost-noarrow-gemini-belle/PREDICTION.md
    - .planning/quick/260824-gt1-ghost-noarrow-gemini-belle/generate_ghost_powerspin.py
    - .planning/quick/260824-gt1-ghost-noarrow-gemini-belle/meta.json
    - .planning/quick/260824-gt1-ghost-noarrow-gemini-belle/out/ (이미지 4장 + prompt 사본 2)
  modified: []
decisions:
  - "잔상 오류 유형 2개 확정 = 실측이 가른 leg_extension(무릎 굽음)·split_angle(스플릿 좁음) — 유형당 2장 (D-01)"
  - "GUIDE 파워스핀 치환에 잔상-폴 분리 절 추가 (도립 신규 위험 축 방어 — D-03 공통 절은 문자 그대로 유지)"
  - "split_angle 2장 = 방향 역전으로 자평 탈락 — 추천은 leg_extension-1·-2 만"
metrics:
  duration: "~16분"
  completed: "2026-08-24"
  tasks: 3
  gemini_calls: 4
---

# Quick 260824-gt1: 파워스핀 다리 ghost-noarrow 잔상 후보 Summary

**One-liner:** 실사용 감점 미커버 1위(파워스핀 다리)의 "어떻게" 잔상 후보 4장을 Firestore 실측 유래 오류 자세로 생성 — D-03 표기 0은 4/4 성립, split_angle 2장은 방향 역전(exq 동일 실패 모드)으로 자평 탈락, 추천 leg_extension 2장.

## 실측 요지 (criterion 별 — Task 1, Firestore 읽기 전용)

| criterion | n | 방향 | median |
|---|---|---|---|
| leg_extension | 10 | 부족 10 / 초과 0 (baseline 180 = 완전 신전) | signed −39.09° / \|delta\| 39.03° (이봉: 4건은 ~100.6° 굽음) |
| split_angle | 9 | 초과 9 / 부족 0 — 단 record 형태가 다름 (baseline 0 / measured 30.00 **9건 전건 동일** = 양자화 값, 앱 발화 문구 기준 좁음 방향) | 30.00° |

- 표본 = 실사용 done doc 182 중 ref-power-spin 18 (코퍼스 uid 109·doc 38 제외).
- 오케스트레이터 08-24 관측(10건/9건)과 건수 **정확 일치**.
- PII: select() 필드 마스크 5필드만, uid 6자 절단, bodyProfile·URL 미수집. 쓰기 메서드 grep 0.

## 산출물

- **예측 박제 커밋 `33cf94f2`** (실측+예측+하네스, out/ 부재 상태) → **생성물 커밋 `e916acd5`** — git 이력 순서가 예측 사전 박제의 증거.
- out/ 이미지 4장: `ghost-leg_extension-{1,2}.jpg`, `ghost-split_angle-{1,2}.jpg` + `prompt_{type}.txt` 2본 (전 본 "NO arrows"·"NO text" 절 포함, grep -L 0행).
- meta.json: 파일명→criterion→실측 deficit(39.03 / 30.0) 매핑 + model·호출 수.

## 실물 게이트 결과 (전 장 Read — PREDICTION.md 자평 절에 박제)

- D-03 표기(화살표·수치·텍스트·빨간 표시) 위반 **0/4**. 두 번째 사람 오독 **0/4**.
- **방향 역전 = split_angle 2/2 탈락** — 잔상이 실선보다 목표(수직 스플릿)에 가깝게 그려짐 (exq stage40-1 과 같은 실패 모드). 관측: 형상 범주가 다른 오류(굽음↔곧음)는 2/2 성립, 각도 크기 차이만 있는 오류(좁음↔벌어짐)에서만 역전.
- 추천: `ghost-leg_extension-1`(1순위 — 입력 프레임 방위 일치) · `ghost-leg_extension-2`(2순위 — 몸통 방위가 입력 프레임과 다름). split_angle 유형은 이번 산출로는 제시 실물 없음.
- 예측 대조(장부 7전째): 쓸 만한 장 총수 2/4 적중, 분포(유형당 1 예측 → 실제 2+0)·실패 모드(역전 0 예측 → 2건) 빗나감.
- belle 판정란은 비워 둠 (D-05 — 판정은 오케스트레이터가 대화로).

## LLM 사용 (보고 규율)

- **Gemini 실호출 4건** — 모델 `gemini-3-pro-image` (generateContent, 텍스트 프롬프트 ~3.9KB + 입력 이미지 2장/호출, 출력 이미지 1장/호출). 재시도 0 (4/4 1회 성공).
- **비용 추정**: 이미지 출력 4장 기준 약 $0.5~1.0 수준 (정확 단가 미대조 — 추정 표기).
- **학습 전송 0**: 호출은 추론(생성)뿐 — 프로젝트 학습 파이프라인(플라이휠/SFT)에 유입된 데이터 0, 유료 API 정책상 Google 측 학습 사용 없음. 키는 SSM→환경변수로만 주입, 파일·로그·커밋에 키 문자열 0.

## Deviations from Plan

**1. [Rule 3 - 오케스트레이터 제약 우선] Task 3 커밋 목록에서 PLAN.md 제외**
- Task 3 은 PLAN.md 포함 커밋 + quick dir 미커밋 잔여 0 을 지시하나, 오케스트레이터 제약("docs artifacts 커밋 금지 — docs 커밋은 오케스트레이터 몫")이 우선. PLAN.md·SUMMARY.md 는 미커밋 상태로 남김 — quick dir 잔여는 이 두 docs 파일뿐(태스크 산출물은 전량 커밋).

**2. [Rule 3 - 생성 부산물 정리] `__pycache__/` 제거**
- py_compile/importlib 드라이런이 만든 gt1 디렉터리의 bytecode 캐시를 삭제 (커밋 대상 아님). 260809 디렉터리의 기존 캐시(08-16 산)는 무접촉.

**3. [결정 기록] GUIDE 치환에 잔상-폴 분리 절 1문장 추가**
- 도립 자세라 잔상 윗다리가 폴과 평행한 신규 위험 축(플랜 예측 절 명시)에 대응해 "each ghost leg must stay clearly distinct from the pole, never blending into the pole or doubling the pole line" 추가. D-03 공통 유지 절(NO arrows…, motion trail)은 문자 그대로 보존 — 킵업 전용 절의 파워스핀 기하 개작 범위 내 판단.

## Known Stubs

없음 — 이 태스크는 배선 없는 판정용 실물 생성이 목적이며 (D-05), 앱 코드 무접촉.

## Threat Flags

없음 — 신규 표면 0 (threat register T-gt1-01~04 전부 플랜 대로 이행: 읽기 전용 + 필드 마스크 + 키 환경변수 + 출력 quick dir 한정).

## Self-Check: PASSED

- FOUND: measure_powerspin_leg.mjs / PREDICTION.md / generate_ghost_powerspin.py / meta.json / out/*.jpg 4장 + prompt 2본
- FOUND: commit 33cf94f2 (생성 전) → e916acd5 (생성물) — 이력 순서 성립
- app/ porcelain 0행 · 쓰기 메서드 grep 0 · prompt "NO arrows"/"NO text" 누락 0행
