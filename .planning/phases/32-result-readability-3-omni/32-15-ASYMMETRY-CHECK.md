# 32-15 비대칭 점검 — pdshape fault 58→46 판별

**belle 지시:** "비대칭 가능성이 안좋은 쪽이라면 확실히 점검하고 넘어가"
**실측일:** 2026-07-22 / Pod `rbpnmxhbfoeg35` (RTX 4090) + 로컬 shadow 재채점
**프로덕션 영향:** 0 — Firestore 기록 0건, 기준모션 문서 무접촉, JSON 산출만
**디버그 세션:** `.planning/debug/ref-student-substrate-gap.md`

---

## 판정 요약

**(A) "결함 정확 포착" 단독이 아니다. (B) 기준모션 비대칭 기여가 실재하고, 크기가 −12점 전부를 설명한다.**

더 나아가 이번 점검은 −12 보다 큰 문제를 드러냈다:
**인버전 2동작(pdshape·elbow-twist)의 `angle_vs_reference__*` 편차 바닥값이 tol 20° 에 육박해,
점수가 자세 품질이 아니라 추출 기질 잡음에 지배된다.**

---

## 1. 감점 귀속 — 점수가 통째로 기준모션에 의존

pdshape fault 감점 7건 **전부** `deviationSource: reference_relative`
(`angle_vs_reference__{joint}`, tolerance 20°, slope 1.2). 절대(IPSF) 기준 감점 **0건**.
→ (B) 가설이 구조적으로 배제되지 않는다.

## 2. 기준모션 실측 — (B) 의 전제 성립

| 항목 | ref-pdshape | ref-elbow-twist | ref-power-spin (대조군) |
|---|---|---|---|
| 역위 프레임 비율 | **67.2%** | 50.8% | 2.0% |
| 등록 메모 | "시작 시점에 이미 인버전 + 회전 상태" | — | — |
| 추출 시점·기질 | 2026-06-12 `phase4_v1` · target 18fps | 동일 | 동일 |
| PR 보정 | **미적용** | 미적용 | (검출 안 됨) |

인버전 검출 임계(15%)를 크게 넘는다 → 오늘 PR 경로로 재추출하면 **검출·보정 대상**이다.
즉 현재 두 동작은 **학생만 보정 / 기준은 무보정** 상태로 비교되고 있다.

### 2-1. 전수 계측 (2026-07-22 추가 · 11종 전부)

위 3종만으로는 재처리 위험도를 매길 수 없어 **reference 11종 전수**를 계측했다
(Firestore `joints3d` 프록시, Pod 미사용·읽기 전용 — `ref_inversion_survey2.py`).
판정 = `inversion_warp.detect_inversion` 과 동일 AND 조건 (ratio ≥ 0.15 **AND** run ≥ 5).

**★ 선행 계측 방법 정정 (M8)**: `asym_analysis.py` 는 `joints3d[:, :2]` 를 고정 사용했다.
그런데 11 doc 은 같은 `space='pole_aligned'` 인데도 **패딩 축이 2갈래**다 —
원본 5(`anglesBackbone=rtmw-x-384-bukuroo-2026-06-06`)는 **(x, 0, y)**,
후속 6(`anglesExtractedBy=rtmw-x-384-direct-2026-06-12`)은 **(x, y, 0)**.
따라서 `[:, :2]` 는 원본 5 에서 (x, 0) 이 되어 margin 이 항상 0 이 된다.
v2 는 doc 별로 항등 0 축을 패딩으로 판정해 남은 두 축을 (수평, 수직)으로 쓴다.
검증 3중 — ①기측정 3종을 소수 3자리까지 재현 ②y-down 규약만 정상 5종을 비검출로 분류
③`ref-invert` 28.0%/run13 이 `inversion_warp` docstring 의 spike 실측 **0.289/run18** 과 독립 일치.

| motion | 계보 | frames | 역위비율 | run | 검출 | 상태 |
|---|---|---|---|---|---|---|
| **ref-pdshape** | direct | 237 | **67.2%** | 30 | **YES** | 기측정 |
| **ref-foxtop-split** | bukuroo | 485 | **57.4%** | 44 | **YES** | **신규** |
| **ref-foxtop** | bukuroo | 426 | **56.5%** | 34 | **YES** | **신규** |
| **ref-elbow-twist-sister** | direct | 329 | **50.8%** | 19 | **YES** | 기측정 |
| **ref-combo** | direct | 931 | **32.0%** | 28 | **YES** | **신규** |
| **ref-invert** | bukuroo | 260 | **28.0%** | 13 | **YES** | **신규** |
| ref-peter-pan | direct | 130 | 4.6% | 1 | no | 기측정 |
| ref-climb | bukuroo | 257 | 2.7% | 2 | no | 신규 |
| ref-power-spin | direct | 159 | 2.0% | 1 | no | 기측정 |
| ref-kip-up | direct | 118 | 0.9% | 1 | no | 기측정 |
| ref-sideway-spin | bukuroo | 298 | 0.7% | 1 | no | 신규 |

**PR 영향 기준모션은 2종이 아니라 11종 중 6종이다** — 기존 인지의 3배.
`foxtop` · `foxtop-split` · `combo` · `invert` 4종이 새로 드러났고, 이 중 climb 을 뺀
전부가 **phase25eval fixture 미보유** → 재처리 후 채점 회귀를 정량 검증할 수단이 없다.
상세 위험도 표·완화책은 `.planning/debug/ref-student-substrate-gap.md` `## 재처리 위험도 표`.

## 3. 기질 불일치 전체 목록 (코드 확정)

| # | 축 | 기준모션 | 학생 | 채점 영향 |
|---|---|---|---|---|
| M1 | target_fps | **18.0** | **9.0** | 시퀀스 밀도 1.5배 |
| M2 | 실효 fps vs 라벨 | 실효 **15.0** / 라벨 **18.0** | 실효 **10.0** / 라벨 **9.0** | `step=max(1,round(src/target))` 정수 양자화 |
| M3 | `find_action_segment` | — | — | `nu<=nr` → **12/12 멤버에서 무력화** |
| M4 | window median 창 | 2프레임 = **0.133s** | 2프레임 = **0.200s** | 초 단위 비대칭 (잠재) |
| M5 | 파이프라인 코드 | `phase4_v1` @06-12 | HEAD | **좌표→각도 수학 동일** (git log 검증) |
| M6 | `PR_INVERSION_ENABLED` | off | on | 인버전 동작에서 학생만 보정 (**영향 기준모션 6종** — §2-1) |
| M8 | joints3d 축 레이아웃 | **2갈래** (x,0,y) / (x,y,0) | (x,y,0) | **채점 무관**(채점 입력은 `angles`). 오버레이·fault zoom·keypointReport 만 영향 — 앱 `pickVerticalAxis` 가 흡수 중 |

**M2 실효 fps 근거 3중:** ①ref-elbow-twist 329프레임/15.0 = 21.93s ≈ `clipRange.landEndS` 21.9
②선행 세션 ffprobe 실측 ref-climb 257프레임/17.078s = **15.05fps** ③재추출 프레임비 237/159 = 1.491 ≈ 3/2.

**M3 가 가장 조용하고 큰 결함이다.** `motiondtw.find_action_segment` 는 학생 시퀀스가 기준보다
짧으면 클립 통째를 반환한다. 기준이 1.5배 조밀하므로 12/12 멤버 전부 이 분기에 걸린다 —
"준비/대기 제거" 1단계가 mode1 에서 **한 번도 발동한 적이 없다.**

## 4. 재현 검증 — 20/20

5동작(climb = comparison gate, 점수 없음) × fault/success × PRoff/PRon = 20 멤버 전부
production `overallScore` 를 `_deviation_against` 코어 + 감점 산식으로 ±1.5 내 재현.
→ shadow 재채점 방법이 전수에서 유효 (기존 6/6 → 20/20 확대).

## 5. 핵심 지표 — success 위양성 여유

**여유 = tol(20°) − max(관절 편차).** 음수 = 이미 위양성 감점 발동.
사람 점수 라벨 불필요한 객관 지표.

| success 멤버 | A 현행 | B 밀도 정규화 | C 기준 PRon 재추출 |
|---|---|---|---|
| kip-up | **+15.8°** | +14.4° | 미측정 |
| peter-pan | **+10.5°** | +7.6° | 미측정 |
| power-spin | **+9.0°** | +4.7° | 미측정 |
| elbow-twist | **+0.2°** | −0.5° | **+0.3°** |
| pdshape | **−1.2°** | +0.1° | **+4.5°** |

**비인버전 3동작 편차 바닥 2.7~7.3° vs 인버전 2동작 14.8~18.0° — 3배.**
이 격차가 기질 아티팩트의 정량 지표다. 현행에서 pdshape success 는 이미 위양성 감점이 발동해
100 이 아닌 99 다 (32-15-SUMMARY 가 "엘리트 밴드 내"로 기록한 그 −1.4).

## 6. 옵션별 shadow 재채점 (PR on 학생 · Firestore write 0)

| 동작 | A 현행 f/s | B 밀도 정규화 f/s | C 기준 PRon 재추출 f/s |
|---|---|---|---|
| power-spin | 55 / 100 | 55.6 / 100 | 미측정 (PR 미검출) |
| peter-pan | 79 / 100 | 74.0 / 100 | 미측정 |
| elbow-twist | 65 / 100 | 61.5 / 100 | 64.4 / 100 |
| pdshape | **46** / 99 | **57.2** / 100 | **21.8** / 100 |
| kip-up | 80 / 100 | 80.0 / 100 | 미측정 |

**pdshape fault 는 밀도만 맞춰도 46 → 57.2 로 되돌아온다.** 즉 −12 하락의 대부분이
학생 결함이 아니라 기질 비대칭이다.

## 7. 안정성 — pdshape 는 ±30점 요동

밀도비 r 을 1.00→0.50 으로 스윕:

| r | 1.00 | 0.90 | 0.80 | 0.75 | 0.70 | 0.667 | 0.60 | 0.55 | 0.50 |
|---|---|---|---|---|---|---|---|---|---|
| power-spin fault | 55.2 | 55.5 | 55.5 | 54.6 | 55.3 | 55.6 | 54.8 | 53.0 | 53.3 |
| peter-pan fault | 78.8 | 81.4 | 77.5 | 74.9 | 73.5 | 74.0 | 74.9 | 75.3 | 78.7 |
| elbow-twist fault | 65.1 | 70.1 | 71.9 | 61.0 | 62.8 | 61.5 | 56.4 | 54.6 | 52.9 |
| **pdshape fault** | 46.2 | 50.0 | 53.9 | 56.6 | 54.3 | **57.2** | **27.0** | 44.7 | 33.5 |
| kip-up fault | 80.0 | 80.0 | 80.0 | 80.0 | 80.0 | 80.0 | 80.0 | 80.0 | 80.0 |

success 5동작은 r ≥ 0.667 전 구간에서 100 유지.

**pdshape 요동 원인 규명:** 결측 0%, DTW path 정상(uniqU = 전 프레임) → 결측·정렬 붕괴 기각.
실제 원인은 **감점 7개 관절이 전부 20~33° 구간(tol 20° 경계)에 밀집**해 있어, 기질을 조금만
흔들어도 관절들이 dead-zone 을 동시에 넘나드는 것. 7관절 × ±5° × slope 1.2 = ±42점의 잠재 진폭.

**정규화 방향 대칭성:** 기준 다운샘플 vs 학생 업샘플 결과 차 —
power-spin 1.3 / peter-pan 0.7 / elbow-twist 1.1 / kip-up 0.0 ‖ **pdshape 11.7**.
밀도 정규화는 4동작에서 well-posed, pdshape 에서만 방향 의존.

## 8. 기각된 해법

- **기준모션을 `clipRange.execStartS~landEndS` 로 자르기** — 역효과. 기준만 자르면 학생 준비
  구간이 정렬할 곳을 잃어 여유가 악화: pdshape success −1.2°→**−14.5°**, elbow-twist +0.2°→**−3.5°**.
  M3 를 함께 풀지 않는 한 단독 적용 금지.
- **"기준모션에 PR 만 적용"** — 초안의 "14.0 급락·동작별 방향 반대" 는 8관절 나이브 재채점의 산물.
  production record 집합을 고정한 충실 재채점에서는 방향이 일관된다
  (success 여유 증가 + fault 분리 확대). 다만 elbow-twist 여유는 +0.3° 로 여전히 위태롭다.

## 9. 권고

1. **phase 32 는 현 상태(PR on)로 마감 가능** — 32-16 전수 스윕에서 비검출 8멤버 바이트 동일,
   관측된 회귀 0. PR 보정 자체는 개선이다(학생 좌표 boneCV −62.8~−92.8%).
2. **단, pdshape fault 46 을 "결함 정확 포착"으로 서술하지 말 것** — §6 실측대로 −12 의 대부분이
   기질 비대칭이다. 32-15-SUMMARY 판독 정정 완료.
3. **기준모션 기질 정합은 별도 phase** — 손대려면 PR 만이 아니라 fps·segment 탐색까지 함께 풀고
   reference 11종 전수 재검증이 필요하다.

## 10. belle 방향 결정 (2026-07-22)

**C + M3 동시 해소** 확정. belle 원문 "제대로 고치자".
A(현상 유지)·B(밀도 정규화) 모두 기각 — B 기각 근거는 elbow-twist 여유 +0.2°→**−0.5°** 악화 +
M6(기준 무보정) 잔존으로 **같은 자리로 돌아온다**는 것.

작업 단위 분해 · 재처리 위험도 표(11종) · 롤백 설계 · 성공 판정 기준 · elbow-twist 처방 경로는
**`.planning/debug/ref-student-substrate-gap.md`** 에 인계 문서로 확정 기록 (status `awaiting_phase`).
착수 시점은 belle 이 TestFlight 1.1.0 UAT 를 마친 뒤 별도로 정한다 — **Pod 무접촉 유지**.

## 산출물

- Pod: `/workspace/eval32/asym/ref_proff.json`, `ref_pron.json` (기준모션 재추출 PR off/on)
- 로컬 shadow 스크립트: `asym_analysis.py` / `symmetric_rescore.py` / `isolate_confounds.py` /
  `substrate_audit.py` / `substrate_rescore.py` / `substrate_sensitivity.py` / `pdshape_instability.py`
- 재사용 read-only 계측: `backend/scripts/measure_reference_fps.py`
