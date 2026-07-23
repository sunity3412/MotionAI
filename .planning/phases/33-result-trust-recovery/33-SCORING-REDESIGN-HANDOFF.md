---
title: Phase 33 인수인계 — 채점 산식 IPSF 감점-상한 재설계로 PIVOT
status: handoff
created: 2026-07-24
owner: belle 결정 대기 (설계는 내일 시작)
blocks: [33-07 flip, 33-08~33-16 표현트랙 중 점수 의존 부분, 33-16 UAT]
---

# 내일 여기서 시작 — 새 세션 필독

> **한 줄:** Phase 33 Wave 6(33-06 재검증) 도중, substrate는 잘 됐지만 **채점 산식이 관절별 감점을 무제한 누적해 다관절 결함을 0점으로 뭉갠다**는 결함을 발견. belle이 **"IPSF 기준 감점 상한 도입(채점 산식 재설계)"** 을 결정. 이건 phase 33의 "채점 산식 무접촉(D-20/D-29)" 대전제를 belle이 의도적으로 뒤집는 것. **다음 = 채점 재설계를 spec부터 제대로(먼저), 그 다음 33 나머지(표현·flip·UAT).**

## ★ 새 세션이 하지 말아야 할 딴소리 (박제)

1. **"D-20/D-29 채점 무접촉이니 산식 건드리면 안 된다"** — belle이 2026-07-24 명시적으로 이 전제를 뒤집었다. 채점 산식(감점 상한)을 **바꾸는 게 이제 과업**이다. [[scoring-ipsf-deduction-cap-no-zero-pileup]]
2. **"33-06 통과했으니 flip(33-07) 가자"** — 33-06은 gate2 FAIL + 채점 결함 발견으로 **판정 보류**. flip은 채점 재설계 완료까지 **금지**.
3. **"gate2(separation floor)만 빼면 된다"** — belle이 이미 기각. separation floor는 fixture별 curve-fit + Gemini 변동 내포라 **판정 지표에서 폐기**. [[judgment-must-not-fixate-on-recent-fixture]]
4. **"elbow-twist만 고치면 된다"** — 이건 elbow 고유 문제가 아니라 **채점 산식 전반**(감점 상한 부재). 다관절 결함 있는 모든 영상에 해당. elbow에 매몰 금지.
5. **substrate를 다시 하자** — 재추출(33-03)·백필(33-04)·M3(33-05)는 **잘 됐고 그대로 유지**. 버리지 말 것.

## 지금까지 완료 (Wave 1–5, 커밋·SUMMARY 있음, main push 완료)

| Wave | 플랜 | 상태 | 핵심 |
|------|------|------|------|
| 1 | 33-01 | ✅ | A-0 게이트 |
| 2 | 33-02/17/18/19/20 | ✅ | 백업·candidate staging·release manifest·M3 spec·coverage matrix (worktree 병합) |
| 3 | 33-03 | ✅ | 11 reference @9fps+PR인버전 → candidate `phase33-cm3-run1`(+run2). R-1 6/6·R-2·R-4(Δ0) PASS. active=phase4_v1 불변 |
| 4 | 33-04 | ✅ | candidate-aware 백필 11/11. Firestore index 면제 2건 추가(versions+reference `referenceKeypointReport`, `--disable-indexes`, belle 옵션 B) |
| 5 | 33-05 | ✅ | M3 정렬 구현(paired range/coverage floor). 채점 산식 byte-unchanged 확인 |
| 6 | 33-06 | ⚠️ **판정 보류** | 재검증 실행됨(7/8 PASS). gate2(separation) 폐기 + **채점 결함 발견 → 재설계 pivot** |

- main HEAD 인수인계 시점: `eb08e87` 이후 (33-05까지 push됨). 33-06 증거 커밋 `984e014`.
- ROADMAP: 33-06은 **complete 마크 안 함**(재설계 필요). 33-07~16 미착수.

## 핵심 발견 (근거 데이터)

**elbow-twist 못한 영상 = overallScore 0.** 재분석(Pod, candidate shadow) 결과:
- dimensionScores: `{angle: 58, stability: 73}` ← 각도 차원은 58점인데
- deductionBreakdown: baseline 100 − (8관절 감점 누적) = **−11.4 → 하한 0**

8관절 감점 (규칙 = `(측정편차 − tol 20°) × slope 1.2`):
| 관절 | 편차 | 초과 | 감점 |
|---|--:|--:|--:|
| 왼어깨 35.1 / 오른어깨 36.1 | | 15.1/16.1 | −18.1 / −19.3 |
| 왼팔꿈치 34.4 / 오른팔꿈치 26.8 | | 14.3/6.8 | −17.2 / −8.2 |
| 왼엉덩이 33.6 / 오른엉덩이 26.7 | | 13.6/6.7 | −16.3 / −8.1 |
| 왼무릎 30.4 / 오른무릎 29.8 | | 10.4/9.8 | −12.5 / −11.7 |
| **합** | | | **−111.4** → 0 |

**belle 육안:** 실패 영상은 실제로 다관절 결함 많음(다리 안 펴짐·팔 안쪽·정렬 처짐, 캡처 확인). 하지만 **"0점은 과하다"** = 우리 자체 angle 58 + IPSF 상한과도 어긋남.

**우리 vs IPSF (NotebookLM 96b061e8 조회):**
- 우리: 관절당 무제한 누적 → 0.
- IPSF Code of Points 2025-2027: 실행 감점은 **연기 전체 총합 상한 −25.0** (자세별/관절별 아님). 결함당 −0.1 per time. routine 최하 0. 완전신전 미달 요소는 **미인정(요소 0) + 실행 감점 이중**.
- IPSF 전체 배점: Compulsory 11(or 18) + Bonus 25 + Artistic 20 − Deduction(상한 25). 총점 만점 ~56~63.
- ※ "우리 최하 75점"은 오답이었음 — IPSF −25는 IPSF 스케일 값, 우리 0~100에 직접 대입 불가.

## belle 결정 + 설계 골격

**결정:** IPSF 기준 감점 상한 도입. "IPSF로 가야 공감을 준다"(0점 뭉침 = 이탈).

**설계 2축 (IPSF 대응):**
| IPSF | 우리 | 재설계 |
|---|---|---|
| 실행 감점(라인/자세) 총합 상한 −25 | angle 차원(관절 편차) | **총합 상한 도입** — 자세별 아닌 **동작 전체 감점 합**에 캡 |
| 완전신전 미인정(요소 0) | line 차원(다리 신전) | 치명 트랙 유지(IPSF도 요소 0) |

**★ 미정 = 내일 belle과 정할 핵심 숫자:** IPSF −25(IPSF 스케일)를 **우리 0~100 스케일에서 상한 몇 점으로** 옮길지. 비율 환산 vs 우리 독자 기준. 이게 설계의 중심.

## 다음 순서 (belle 승인함)

1. **채점 재설계를 먼저 제대로** — `/gsd-discuss-phase` 급 설계. spec: 상한 값·스케일 매핑·완전신전 치명 트랙 분리·전 fixture 영향.
2. **6 fixture 전수 재검증** (elbow만 아님): 잘한 영상 100 유지 / 다관절 결함 IPSF 합리점수 / 변별 유지. **overfit·fixture 매몰 금지** [[scoring-redesign-must-generalize-no-overfit]] [[judgment-must-not-fixate-on-recent-fixture]].
3. 그 다음에야 33 나머지(표현 A-1~A-7 중 점수 의존분 → flip 33-07 → UAT 33-16).

**의존성:** 결함 시각화(크롭 위치·일러스트)는 채점과 독립(병렬 가능). 점수 표시·flip·UAT는 채점 재설계 **후**.

## Pod 상태 — TERMINATED

- `k508k3lut0o3f1` 는 **belle이 2026-07-24 terminate함** (과금 절약). D-30 "all Pods terminated" 상태로 복귀.
- **Network Storage Volume(MooseFS)은 생존** — 코드 `/workspace/SunityMotion`, weights, 그리고 재설계 검증 데이터 `/workspace/_s4_out.json`(12 member 감점), `/workspace/_s4_driver.py`, `/workspace/_etw_bd2.py` 모두 남아 있음.
- **내일 채점 재설계 spec/코드 단계는 Pod 불필요.** 6 fixture 전수 **재검증 단계에서만** 새 Pod 필요 → belle GPU greenlight + 새 Pod 생성(EU-RO-1 4090 Network Storage) 후 bootstrap 절차 [[current-pod-k508k3lut0o3f1]] 재사용(그 파일의 접속정보는 죽음, 절차만 유효).

## 진행 규칙 (belle, 이번 세션)

- 웨이브 끝날 때마다 품질 자평 후 진행 [[report-wave-quality-before-next-wave]].
- fixture 매몰 금지(최근 만진 게 문제로 나오면 overfit 의심) [[judgment-must-not-fixate-on-recent-fixture]].
- 얼렁뚱땅 예외처리 금지 — 제대로. 산출물 직접 열어 확인 [[open-the-artifact-before-claiming-done]].
