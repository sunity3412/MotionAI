# 분석 정확도 부채 감사 (2026-06-26) — 내일 작업 리스트

> belle 요청: "어떤 phase에서 처리했어야 할 문제가 터졌는지 싹 정리. 채점만 문제인지." → 내일 이 파일 읽고 하나씩 처리.
> **북극성(belle 목표): 우리 자체 학습 모델** ([[finetune-open-model-phase22]]). 아래 부채들이 "정확도를 빌리거나 흉내내는" 현 구조의 한계 — 자체 학습이 이걸 대체하는 종착지다.

---

## 결론 (한 줄)
**채점만의 문제가 아니다.** 터진 본체는 **Phase 15 부채(미등록 동작 IPSF 등록)**이고, **Mode 3에 같은 종류 부채**(검증 게이트 없이 아무 동작 97점)가 잠복. 토대 의존성(Gemini 닫힘, RTMW 검증용 라이선스)이 정확도 상한·출시를 묶고 있음.

---

## 오늘 완료·push 된 것 (현 상태)
- ① granular reference-relative seed (commits abef36a/811e3f9/6682c63/c958ff3) — 미등록 동작도 per-joint 항목별 감점 방출. **단 이게 "정은지 따라하기"를 강화 → 오염을 표면화시킴(아래 P1).**
- ② visibility=0.0 배선 fix (81e7f56) — Gemini 경로 회복(low_alignment→window_union).
- pod 검증 sweep 통과(변별 4/5, 정타 100, 결정성 OK) — kip-up만 FAIL.
- HEAD = e44bee2 + (이 audit 커밋).

---

## P1 — 분석/채점 정확도 (본체, Phase 15 부채) ★최우선

- [ ] **recognizer가 동작별 IPSF 기하 요건을 등록하게 만들기** (주인=**Phase 15**, [[phase15-recognizer-student-video-line-none]]에서 발견 후 "데모 5개 우선"으로 미룸)
  - 증상(오늘 확정): `profile_move="미등록"` → `expects_extension=NONE` → IPSF-절대 기준 부재 → **정은지-따라하기 폴백**
  - 폐해: "정은지 대비 편차"가 **기술 결함 ≠ 그냥 다른 사람**을 못 가림. elbow-twist/pdshape 정타가 정은지와 14~18° 어긋남(체형/스타일) → 오염 → 임계 못 내림 → **kip-up fault(18°) 미검출(100/100)**
  - 데이터 근거: DTW 거리 ↔ 정타 편차 비례 (kip-up 6.5→4°, elbow-twist 42.9→18°). 임계 민감도표: kip-up 잡으려 tol≤15°로 내리면 elbow/pdshape 정타가 위양성으로 터짐 → **절대 임계로는 원천 불가**
  - **진짜 fix 방향**: 채점을 **객관 IPSF 기하 기준**(이 관절이 실제 180° 펴졌나 / 라인이 곧은가)으로 — 정은지 각도 흉내 아님. extension_deviation/line_score 경로는 코드에 이미 있음, recognizer 등록만 되면 켜짐.
  - belle 도메인 필요: IPSF 요건은 [[notebook-lm-pole-sports]]/belle 기준으로 정의해야 함(임의 정의=curve-fit 금지 [[scoring-redesign-must-generalize-no-overfit]])
- [ ] **kip-up 미검출** (Phase 23 [[phase23-pod-eval-gate-fail-2026-06-24]]에서 flagged) — P1 닫히면 "kip-up IPSF 요건 충족?"로 객관 판정 가능한지 검증
- [ ] **약한 eval 게이트 강화**: "fault<success"(운 좋으면 통과)에서 **"정타 잔차가 깨끗한가"**로

## P2 — Mode 3 정확도 게이트 (P1과 같은 종류, 다른 곳)

- [ ] **Mode 3 검증 게이트 부재** ([[mode3-scoring-basis-unknown-move-gate]]) — Mode3는 **미보유 동작도 무비판 97점** 출력(not_pole 게이트는 Mode1 전용). P1과 동일한 "아무거나 점수 줌" 문제 → P1 고쳐도 이거 안 고치면 실증에서 또 터짐
- [ ] Mode 3 점수 근거 화면 미표시

## P3 — 토대 의존성 (정확도 상한·출시 묶음) → 자체 학습으로 가는 길

- [ ] **Gemini = 닫힌 모델** ([[finetune-open-model-phase22]]) — 파인튜닝 불가 → 정확도 개선 한계. recognizer+coach+vision 전부 Gemini 의존. **= belle가 원하는 "자체 학습 모델"이 정확히 이걸 대체.** Phase 22에 오픈모델 전환 계획만 있고 미실행. 학습셋은 Phase 20~21 동안 적재 예정이었음
- [ ] Gemini 크레딧/키 운영 취약 ([[gemini-credits-depleted-2026-06-20]])
- [ ] **RTMW 가중치 = 검증용 한정** ([[rtmw-clean-weight-release-gate]]) — 상업 출시 전 clean weight 교체 필수(라이선스). 측정 백본이 출시 막힘

## P4 — 표시/출시 (의식적 보류, 덜 급함)

- [ ] granular 한글 관절 라벨(왼무릎) 앱 render 매핑 (오늘 백엔드만 완료)
- [ ] Mode 3 zoom / 3D 뷰어 ([[fault-zoom-compare-and-phase24-true3d]])
- [ ] 결제(RevenueCat)·셀프서비스 reference 등록 — 파일럿 의도적 제외(OK)

---

## 자체 학습 모델과의 연결 (belle 목표)
P1(객관 IPSF 측정 + 라벨)과 P3(Gemini 탈피)이 **자체 학습의 토대**다:
- 자체 모델이 할 일 = "무슨 동작 + 무엇이 틀렸나"(recognizer가 지금 못 하는 것) + 비전 판정(지금 Gemini)
- 즉 P1·P3을 닫는 것 = 자체 학습으로 가는 직선 경로. 부채 처리가 belle 목표의 우회가 아니라 활주로.

## 권장 순서 (내일)
1. **P1** = 본작업. recognizer IPSF 등록 → 객관 채점 → 같은 데이터로 "정타 오염 사라지고 kip-up 잡히는지" 끝까지 검증 (미루지 않기)
2. **P2** = P1과 같은 "객관 기준 + 검증 게이트" 설계로 함께
3. **P3** = belle 도메인/출시 결정 + 자체 학습 착수 시점 논의
4. P4 = 틈틈이

---
*저장: 2026-06-26 · 작성=오늘 pod 진단·검증 기반 · 내일 이 파일부터 읽고 시작*
