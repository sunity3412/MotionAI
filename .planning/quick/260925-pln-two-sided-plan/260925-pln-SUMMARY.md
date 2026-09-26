---
quick_id: 260925-pln
slug: two-sided-plan
date: 2026-09-26
status: complete
commit: 6481e56f
mode: inline
---

# 260925-pln SUMMARY — 양면 플랫폼 기획안 초안 v0.1 (2026-09-26)

## 한 줄
기획안 초안 v0.1 이 나왔다(`260925-pln-PLAN-two-sided.md`, 12절 + 결정 요청 §A). **belle 판정 대기.** 코드 0줄.

## 한 것 (관측)
1. **인계서 §4 파일 대조** — 서브에이전트 보고였던 줄 전부를 파일 열어 확인. 서술은 전부 맞았다.
   정정 3: RuntimeError 줄 8904 → 8905 · `motionThumbs.ts` 는 `app/src/constants/` · auto-register 가 쓰는 필드 위치(`firestore_admin.py:2368-2430`).
   미확인 1 닫힘: mode1 의 yaml 키 = Gemini 가 낸 이름의 canonical(`gemini_technique_recognizer.py:325-355`), `referenceMotionId` 는 프롬프트 힌트(`pipeline/app.py:8670-8673, 8875-8880`).
   대조 안 한 것 1: 기준 버전 구조(`versions/{v}` · `_release.activeCandidate`) → 기획안 §11-3 [미확인].
2. **기획안 초안** — 인계서 §5.3 골격 그대로. ★ 끝 그림 먼저(역할 4 · 돈 · 권리 · 공급자↑→수요자↑ 고리), 실증은 그 안의 구간(단계 0~4). 숫자는 시장조사 §0 [확인] 10건만. 관측/진단 분리, 표식 대장 §12.
   새로 넣은 설계 초안 2(내 판단, belle 미승인): "강사를 대체하는 AI 가 아니라 강사의 기준을 복제하는 AI"(§1-2, 강사 거부 이유 5 에 구조로 답함) · 기술 사전과 기준 인스턴스 분리(§7-2).
3. **belle 결정 요청 §A** — Q1 같은 앱 공급자 모드 / Q2 링크 + 뒤쪽 자동화 4칸 / Q3 "강사 먼저" 한 칸 / Q4 놓을 곳 / Q5 `--mark-holdout`. 판정 형식(○×).

## 안 한 것
- 09-18 상태 보드 아티팩트에 09-25·09-26 항목 반영(인계서 §5-5) — 아직.
- belle 읽기용 페이지 — Q4 판정 뒤에.
- push — 이번 세션 커밋 2개(6481e56f + docs) 미푸시. Pod 작업 없음.
- 봉인 시험지 2회 — 정은지 영상 대기(이 기획안보다 먼저).

## 다음 세션 착수
`260925-pln-HANDOFF.md` ★절 → 기획안 §A 의 belle 판정 → ○ 는 §10 단계표로, × 는 해당 절 재작성. 코드는 §10 순서(단계 0 봉인 시험지 → 단계 1 파일럿 깨는 것 4 → 단계 2 공급자 링크, belle 승인 뒤)를 넘지 않는다.

## 09-26 2차 — 벤치마킹 매칭 §B (belle "벤치마킹해서 우리 앱에 가장 잘 어울리는 것을 적용한다")
- 기획안 §A 바로 아래 §B 신설: B-1 결정 5건의 벤치 · B-2 설계 항목 17건의 벤치 · B-3 벤치 없는 것 6건(창조하는 자리).
- NotebookLM 원문 인용 5회로 [확인] 승격(시장조사 정본 §F): Skillest/Onform 같은 앱 · CoachNow 전용 공간 · Trainera 화이트라벨 · Lessonface 15%/4% · SwingSmith one priority fix · AI Golf School root-cause+drill · SAGES shared mental model · C-SATS 하위 5명 동일 식별 · PDA progress videos · X-Pole TV "all you see are instructors' names" · 폴댄스 강사 셀프 등록 도구 소스 없음.
- 관측 하나가 §A 를 보강했다: 강사만 보이는 홈은 X-Pole TV 가 실패했다 → Q3 는 "강사 칸 + 그 강사의 동작 목록" 이 한 몸.
- 판정에 새로 들어간 것: 학원이 데려온 수강생은 수수료 낮게(Lessonface 형) — §1-4 초안, belle 미승인.

## 09-26 3차 — belle 판정 9건 반영
- §A: Q1 ○ · Q2 ○ + 공급자 마이페이지(§7-4) · Q3 ○ · Q4 내 결정(리포 정본, 페이지는 v1 뒤) · Q5 "학습은 끊김 없이"(§10-2) · D1 ○ · D2 설명(§7-2) · D3 추천·귀속 기획(§C-2, 권장 = 코드 입력 + 양쪽 크레딧, 지급은 첫 분석 뒤) · D4 ○ 월정액은 학원 부가기능 때만(§C-3).
- belle 추가 지시: 수익은 크레딧 개념(결정 기록 리포·메모리에 없음 → belle 말이 정본, §C-4) · 지출을 같이(§C-1 원가표: GPU 만 확정, Gemini 단가 미실측 — usage_metadata 미박제).
- NotebookLM 인용 1회 추가 → 시장조사 §F-6(Lessonface·Skillest 티어·Metafy·Virtu·italki·Ringle·Polesphere·Uscreen·쿠폰 3).
- 메모리 2건 신설(proposals-must-be-benchmarked · belle-260926-plan-verdicts-credits-cost-learning) + 재학습 메모리 갱신.
- 남은 belle ○×: holdout 정책 · 크레딧 단위/만료 · 추천 크레딧 숫자.

## 09-26 4차 — 원가 실측 + 상품 구조 초기 버전 확정
- Gemini 원가 실측: 분석 1건 7회 호출(코드 대조), 영상 토큰 103/초(count_tokens 실측), 공개 단가 → 약 $0.25~0.55. 거부권 4회(pro, thinking 무제한)가 절반 이상. GPU 는 Pod 정책·하루 건수 표. 총원가 800~3,900원(§C-1).
- §C-5 상품 구조(무료 3회 · 기본 1 · 상세 2 · 강사 리뷰 · 모션팩 · 학원 묶음 · 정산) + 손익표 → **belle "실증까진 돈을 받을 순 없으니 초기 버전엔 이렇게 결정"** → §C-6 초기 버전 확정(실증 = 무료, 실증 뒤 과금, Pod 온디맨드 전제).
- 봉인 시험지 용어 한 줄(§2-4). 시장조사 §G 단가 출처.
- 남은 belle ○×: holdout 정책(§10-2) · 크레딧 만료 · 모션팩 2단/묶음 · 추천 크레딧 숫자.
- 5차(09-26 밤): belle ○ — 크레딧 무만료 · 모션팩 = 크레딧 묶음 + 귀속 수강생에게 강사 모션팩 개방 · 추천 크레딧 수강생 2/강사 2. holdout 정책은 "봉인 시험지" 용어가 안 닿아 대기.
- 6차: belle ○ holdout 정책("시험 영상은 배우지 않는다, 나머지는 전부 배운다") + 용어 확정 **시험 영상 / 연습 영상**(구 봉인 시험지). 정은지 실수 6편 = 연습 영상 → 학습. TRAINING-DUE 게이트 4 갱신. 09-26 ○× 전부 닫힘, 미결은 정산 비율뿐.
