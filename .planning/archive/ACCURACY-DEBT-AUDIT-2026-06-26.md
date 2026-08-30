# 분석 정확도 부채 감사 (2026-06-26) — 내일 작업 리스트

## ▶▶ 내일 이 프롬프트 하나 붙여넣고 시작 (belle)
```
.planning/ACCURACY-DEBT-AUDIT-2026-06-26.md 읽고 P1(recognizer 미등록 → 객관 IPSF 채점)부터
끝까지 닫아라. 순서: (1) eval 게이트 강화(정타 잔차 깨끗 + 미보유/above-cutoff 민감도)를
/gsd-quick 으로 먼저 → (2) /gsd-debug 로 recognizer 미등록 근본(코드 갭 vs IPSF 데이터 부재)
못박기 → (3) NotebookLM IPSF 노트북(id 96b061e8-bb7c-41c5-8606-8ceef2ce1aa3 "IPSF Rules
and Advanced Strength Pole Moves Guide")에서 동작별 객관 기하 요건 소싱(curve-fit 금지) →
(4) recognizer 등록 + 객관 채점(extension/line) wiring → (5) pod 재-sweep 으로
"정타 오염 사라지고 kip-up 잡히는지" 끝까지 검증. 어떤 것도 다음 phase/자체학습으로 미루지 말 것.
설치 필요한 도구 있으면 먼저 말해라(belle 가 설치).
```
**준비 확인됨**: NotebookLM MCP 인증 OK + IPSF 노트북 접근 가능 → 설치할 것 없음(있으면 위 프롬프트가 먼저 물어봄). Pod 는 새로 띄우면 pip 재부트스트랩(아래 P3 메모) + `git pull` 먼저.

---


> belle 요청: "어떤 phase에서 처리했어야 할 문제가 터졌는지 싹 정리. 채점만 문제인지." → 내일 이 파일 읽고 하나씩 처리.
> **철칙: 아래 모든 부채는 지금 그 자체로 닫는다. 어떤 것도 "자체 학습 한 다음에"로 넘기지 않는다.** (자체 학습은 belle가 하고 싶어하는 완전 별도 트랙 — 이 부채들과 무관하게 따로 진행. 부채 fix를 자체 학습 뒤로 미루는 근거로 절대 쓰지 말 것.)

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

## P3 — 토대 의존성 (지금 처리. "자체 학습 다음에" 금지)

- [ ] **Gemini 의존 축소 — 지금 할 수 있는 것**: recognizer/채점이 Gemini 판단에 기대는 부분을 **객관 IPSF 측정(P1)**으로 옮겨 의존을 줄인다(파인튜닝 불가라도 의존 면적은 지금 줄일 수 있음). recognizer 자체도 FallbackRecognizer/프롬프트 개선으로 "미등록" 줄이기 가능. ([[finetune-open-model-phase22]]는 belle의 별도 트랙 — 이 항목을 거기로 미루지 않음)
- [ ] Gemini 크레딧/키 운영 취약 ([[gemini-credits-depleted-2026-06-20]]) — 충전/모니터링은 지금 처리
- [ ] **RTMW 가중치 = 검증용 한정** ([[rtmw-clean-weight-release-gate]]) — 상업 출시 전 clean weight 교체 필수(라이선스). 출시 결정 시점에 belle가 처리(파일럿 검증엔 OK, 출시 전 게이트)

## P4 — 표시/출시 (의식적 보류, 덜 급함)

- [ ] granular 한글 관절 라벨(왼무릎) 앱 render 매핑 (오늘 백엔드만 완료)
- [ ] Mode 3 zoom / 3D 뷰어 ([[fault-zoom-compare-and-phase24-true3d]])
- [ ] 결제(RevenueCat)·셀프서비스 reference 등록 — 파일럿 의도적 제외(OK)

---

## ★ 끝난 줄 알았으나 목표 미달 (false-close) — 재오픈 대상
"완료"로 마킹됐지만 그 phase가 약속한 **정확도 목표는 미달**. belle 분노의 핵심.

| Phase | 마킹 | 약속 | 실제 (오늘 확정) | false-close 이유 |
|---|---|---|---|---|
| **19** | 완료(6/18) | 점수 위양성 **근본 수정** + 일반화 | 위양성/오염 그대로(kip-up FP, 정타 14~18°) | 핵심 목표 미달인데 완료 처리 |
| **18** | "verdict closed" | eval 검증 셋 | **kip-up 100/100 위양성을 "known"으로 받고 닫음** + 게이트 "fault<success"=약함 | 위양성 묵인 + 약한 게이트 |
| **5** | "5/5 PASS" | Gemini 기술 인식기 | 등재 5개만 분류, 나머지 "미등록" | scope 과소 |
| **20** | 미완(부분구현) | kip-up 위양성 ≤50 해소 | 미해결 | 진짜 미완 |
| **24** | 진행중 | 투명 감점 채점 | 기계적으론 돌지만 깨진 토대(미등록) 위 | 토대 미해결 |

→ 공통 뿌리 = **P1(recognizer IPSF 등록) + 약한 eval 게이트**. 19·18·5가 안 닫고 넘겨서 20·24가 그 위에 쌓임 → 오늘 한꺼번에 드러남.

## 남은 phase ↔ 문제 매핑 (ROADMAP `[ ]` 기준)
- **Phase 15** (미완) = recognizer IPSF 등록 부채의 **원래 주인** → P1
- **Phase 20** (미완, 부분구현) = 채점 위양성 해소 목표 → P1 뿌리에 막힘 (24가 흡수/대체 중)
- **Phase 24** (진행중) = 채점 본체, 오늘 ①② done but 깨진 토대 위 → P1
- **Phase 10** (미완) = 부상 위험 신호 = 별도 기능(정확도 무관, 독립)
- **Phase 22** (미완) = 자체 비전 모델 = belle 별도 트랙
→ **남은 정확도 phase 3개(15·20·24)가 전부 같은 뿌리(P1)에 막혀 있음.** 채점이 안 끝나는 이유 = Phase 15가 안 끝나서.

## ★ 내일 시작법 + GSD 명령 추천
**`/gsd-debug`로 시작 — 투자처를 정확히.**
1. **`/gsd-debug`**: "recognizer가 power-spin/pdshape/kip-up을 왜 '미등록' 반환하나 — 빠진 게 **코드 로직**인가 **IPSF 도메인 데이터**인가?" (persist 상태 → 조사하다 또 미루는 재발 패턴 차단)
   - 코드 갭 → 그 세션에서 fix
   - **IPSF 도메인 데이터 부재 → `/gsd-discuss-phase 15`**로 belle IPSF 요건 입력 후 등록 (debug 단독 불가 — IPSF 요건은 코드에 없는 belle 도메인 지식)
2. **eval 게이트 강화**는 그 전/병행으로 **`/gsd-quick`** ("정타 잔차 깨끗 + 미보유/above-cutoff 민감도"). 게이트 약하면 fix 검증 불가 → false-close 재발.
3. 절대: 어떤 것도 "다음 phase/자체 학습 다음에"로 미루지 않기.

## 자체 학습 트랙 (belle 별도 — 부채와 분리)
belle가 하고 싶어하는 별개 작업 ([[finetune-open-model-phase22]]). **위 부채들과 독립이며, 어떤 부채도 이 트랙을 이유로 미루지 않는다.** belle가 착수 시점을 별도로 정함. 여기 적는 이유는 분리해서 추적하기 위함이지, 부채의 해법으로 두기 위함이 아님.

## 권장 순서 (내일)
1. **P1** = 본작업. recognizer IPSF 등록 → 객관 채점 → 같은 데이터로 "정타 오염 사라지고 kip-up 잡히는지" 끝까지 검증 (미루지 않기)
2. **P2** = P1과 같은 "객관 기준 + 검증 게이트" 설계로 함께
3. **P3** = 지금 할 수 있는 의존 축소(객관 측정으로 이전) + 크레딧 운영. RTMW 라이선스는 출시 전 게이트
4. P4 = 틈틈이

---
*저장: 2026-06-26 · 작성=오늘 pod 진단·검증 기반 · 내일 이 파일부터 읽고 시작*
