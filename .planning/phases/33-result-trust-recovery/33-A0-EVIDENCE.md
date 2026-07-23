# 33-A0 — 분석 출력 정확성 확인 게이트 (D-04 BLOCKING)

**작성:** 2026-07-23 (Claude 실측 판정, belle 질문 아님 — D-01/D-04)
**목적:** 6동작 전수로 "짚은 부위(pointed) vs 활성 항목(shown) vs 실측 결함 부위(measured)"를
대조하여 phase 33 범위를 분기한다. 어긋남 큼 → C+M3 substrate 트랙을 phase 33 에 편입(HALT).
어긋남 작음 → 표현 계층(33-02+)만 진행. **판정은 측정으로, belle 로 추정 아님(D-04).**
**무접촉:** 채점/분석 산식 0 수정(D-20). 새 Pod 추론 0 — 보유 데이터만(committed sweep + belle 실 doc 덤프).

## 데이터 출처 (무엇을 열어서 확인했는가 — D-19)

| 소스 | 경로 | 무엇 |
|---|---|---|
| Committed baseline sweep | `backend/evals/phase25/baseline/phase25_sweep_report.json` (2026-07-05 run7, 12 member) | pointed(`visionVeto.faultJoints`) / shown(`activatedCriteria`) / measured(`seedObservation.window_joints,fallback_joints`) 전수 |
| belle 실 doc 덤프 | `dump_analysis_doc.py` → uid `csKWYvI3WCPYPysNQ9KkWecaUvq1` / analysis `071df9f894d64d1696f106e613f51f5c` (`ref-power-spin`, `파워스핀(잘못된예시).mp4`, mode1, overall 51, 2026-07-22 crop) | 위 3 필드 + `faultZoomComparisons[]` 전수 |
| Crop PNG 전수(눈으로 엶) | `/tmp/a0_pngs/crop_00_left_shoulder.png`, `crop_01_left_hip.png`, `crop_02_left_hand.png` | 실제 합성 crop 3장 — 학생/기준 쌍, 마커, 배지, 국면 |

> **틀리면 걸리는 장치(D-18):** 아래 표는 스크립트가 원문 방출한 값을 그대로 옮겼다. 빈/결측은
> `empty`/`null`로 표기하고 조작하지 않는다. `seedObservation`이 belle 실 doc 에서 통째로 부재하면
> "measured 없음"으로 노출한다 — `except: pass`로 삼키지 않는다.

---

## A. 6동작 전수 대조 표 (짚은 부위 vs 활성 항목 vs 실측)

베이스라인 sweep(12 member = 6동작 × correct/fault). success 멤버는 감점 0(clean)이라
pointed/shown 모두 비어 있는 게 정상 — fault 멤버가 대조의 본체다.

| 동작 / 멤버 | 짚은 부위 (pointed = faultJoints) | 활성 항목 (shown = criterion) | 실측 (measured = window→fallback) | 세 집합 정합? |
|---|---|---|---|---|
| **power-spin / fault** | LK, RK, LH, RH | a_v_r\_\_LH, a_v_r\_\_LS, a_v_r\_\_RH, leg_extension | **window=empty** → fallback=[LE,RE,LS,RS,LH,RH] | ✗ shown 에 LS(어깨) 있으나 pointed 엔 없음. measured 공백 |
| power-spin / success | null | (없음) | window=empty | — (clean, 정상) |
| **peter-pan / fault** | null | a_v_r\_\_LS, a_v_r\_\_RE, a_v_r\_\_RK | **window=empty** → fallback=8관절 | ✗ pointed 통째로 null 인데 3항목 shown |
| peter-pan / success | null | (없음) | window=empty | — (clean, 정상) |
| **elbow-twist-sister / fault** | LK, RK, LH, RH | a_v_r × 7 (LE,LH,LK,LS,RE,RK,RS) | **window=empty** → fallback=8관절 | ✗ pointed=4(다리·엉덩이) vs shown=7(팔꿈치·어깨 포함). 크게 초과 |
| elbow-twist-sister / success | null | (없음) | window=empty | — (clean, 정상) |
| **pdshape / fault** | null | a_v_r × 8 (전관절) | **window=empty** → fallback=8관절 | ✗ pointed=null 인데 8항목 shown |
| pdshape / success | null | (없음) | window=empty | — (clean, 정상) |
| **kip-up / fault** | left_hand, LS, RS, LH, RH, LK, RK (7) | a_v_r\_\_LS, a_v_r\_\_RS, split_angle | **window=[LS,RS,LK,RK]** (유일하게 채워짐) → fallback=[LE,RE,LH,RH] | ✗ pointed(7) ⊋ measured(4) ⊋ shown(어깨2+split). 3집합 전부 다름 |
| kip-up / success | null | (없음) | window=empty | — (clean, 정상) |
| **climb / fault** | null | null | null | ⊘ status=`comparison`(mode3) — 채점 substrate 부재. 대체 검증 필요(D-23) |
| climb / success | null | null | null | ⊘ status=`comparison`(mode3) — 채점 substrate 부재. 대체 검증 필요(D-23) |
| **belle 실 doc (ref-power-spin fault, mode1, 2026-07-22)** | LS, RS, LH, RH, LK, RK (6) | leg_extension, split_angle, a_v_r\_\_LS | **`seedObservation` 통째로 null** (window/fallback 둘 다 없음) | ✗ pointed=6(전 사지) vs shown=3(다리·split·왼어깨). measured 통째 부재 |

**약어:** L/R=left/right, S=shoulder, E=elbow, H=hip, K=knee. `a_v_r`=`angle_vs_reference`.

### 표에서 즉시 읽히는 사실
1. **실측(measured window_joints)이 사실상 없다.** fault 멤버 5개 중 kip-up 1개만 window 가 채워짐.
   belle 실 doc 은 `seedObservation` 자체가 통째로 부재. 즉 "실측 결함 부위"라는 대조 기준선이
   **존재하지 않는다** → pointed 가 맞는지 확인할 실측이 없다.
2. **pointed 와 shown 이 서로 다른 집합이다.** power-spin(shown 에 어깨, pointed 엔 없음),
   elbow-twist(pointed 4 vs shown 7), pdshape·peter-pan(pointed null 인데 shown 다수),
   kip-up(3집합 모두 다름). 어느 fault 멤버도 세 집합이 정합하지 않는다.
3. **climb 은 채점 경로가 없다**(mode3 comparison) — fixture 있으나 substrate 부재로 전수 대조 불가.
   D-23 대체 검증(belle 실 mode3 doc 또는 재분석) 필요로 명시.

---

## B. belle 실 doc crop PNG 3장 — 눈으로 확인 (D-19 전수)

3장 모두 실제로 열어 확인했다. 파일: `/tmp/a0_pngs/crop_{00,01,02}_*.png`
(스크립트 `--download-pngs`로 presigned URL 에서 디스크로 내려받음). 세 카드 모두
`userFrameIdx=34 / refFrameIdx=90` (같은 프레임 쌍).

| Crop | joint / region / tier | 배지(구움) | 눈으로 본 것 |
|---|---|---|---|
| crop_00 | left_shoulder / arms / confirmed (55°) | "55°" PNG 픽셀에 구움 | 좌=학생, 우=기준(정은지). **마커(빨간 원)는 학생 겨드랑이에만, 기준측 표시 0**(결함①). 두 몸의 **국면이 명백히 다름** — 학생은 수평 인버전, 정은지는 완전히 다른 방향의 인버전(결함④). 배율도 다름(결함②) |
| crop_01 | left_hip / legs / confirmed (30°) | "30°" 구움 | 좌=학생, 우=기준. **빨간 선(마커) 학생 허벅지에만, 기준측 0**(결함①). 국면 또 어긋남 — 학생 수평, 정은지 수직 인버전에 다리 접힘(결함④). crop_00 과 **같은 프레임 쌍(34/90)**(결함③) |
| crop_02 | left_hand / — / advisory (26°) | "26°" 구움 | 좌=학생, 우=기준. 학생 손(폴 그립)에 빨간 원, 기준측 0(결함①). tier=advisory → 앱 시트 join 에서 **미노출**(결함⑧). left_hand 는 pointed(faultJoints)에도 shown(criterion)에도 **없는** 관절 |

### 결함⑤(항목↔크롭 오연결) 구조 확인
belle 실 doc 의 `split_angle` record 는 `source: "vision"`이다(덤프 원문 확인).
`deductionLabels.ts:236`에 의해 `source==='vision'` record 는 keypoint 를
**faultJoints 전체**(=[LS,RS,LH,RH,LK,RK])로 투영한다. `result.tsx` `selectedZoom` 은
region 교차 첫 카드를 반환하므로, "다리 스플릿" 항목이 **첫 카드인 left_shoulder(arms) crop**
에 붙는다. 즉 다리 결함이 어깨 크롭에 걸린다 — 결함⑤가 belle 실 doc 데이터에서 구조적으로 재현됨.

### 이 산출물이 틀렸다면 어떻게 알았을까
pointed/shown/measured 세 집합과 crop joint 를 나란히 원문 방출했다. 만약 pointing 이
맞았다면 세 집합이 수렴하고 crop 의 기준측 포즈가 학생과 같은 국면이어야 한다. 실제로는
세 집합이 전부 어긋나고(A절), crop 의 기준(정은지) 프레임이 눈으로 봐도 다른 국면이다(B절).
즉 틀림이 집합 불일치 + 국면 불일치로 **눈에 드러난다**.

---

## C. D-04 분기 판정

### 왜 empty-measured 를 "정합"으로 세면 안 되는가 (Pitfall 3)
실측 substrate(`window_joints`)가 비면 pointed·measured 가 같은 `fallback_joints` 상위집합으로
붕괴해 "우연히 겹쳐" 보인다. 그러나 이는 정합이 아니라 **측정 기반 자체가 없다는 신호**다
(`ref-student-substrate-gap.md`: ref 18fps 인버전보정 vs student 9fps 비대칭 +
`find_action_segment` 비활성). 33-RESEARCH Pitfall 3 은 "empty-window 를 aligned 로 세지 말 것,
그 자체가 C+M3 편입을 지지하는 어긋남 신호"라고 못박았다.

### 판정 근거 (측정)
1. **실측 결함 부위가 사실상 부재** — fault 5개 중 4개 window=empty, belle 실 doc `seedObservation`
   통째 null. 짚은 부위를 검증할 기준선이 없다 → Pitfall 3 에 따라 어긋남 신호.
2. **pointed vs shown 전 fault 멤버 불일치** — 어느 멤버도 세 집합이 정합하지 않음(A절).
3. **crop 국면 어긋남(눈)** — belle 실 doc 3장 모두 기준(정은지) 프레임이 학생과 다른 국면.
   이는 표현(캡션/조인트-정확 join/문구)으로 못 고친다. **기준 프레임 자체가 틀린 순간**이면
   crop 을 예쁘게 붙여도 "틀린 것을 예쁘게 보여주는 것"(D-03) 이 된다. = ref↔student 정합(C+M3) 문제.
4. **결함⑤ 구조 재현** — split(vision) → faultJoints 전체 투영 → 어깨 크롭 오연결.

### 판정

**어긋남 큼**

세 집합(pointed/shown/measured)이 전 fault 멤버에서 불일치하고, 대조 기준선인 실측(window_joints)이
사실상 부재하며(belle 실 doc 은 seedObservation 통째 null), belle 실 doc crop 3장을 실제로 열어보니
기준(정은지) 프레임이 학생과 다른 국면으로 쌍지어져 있다(국면 어긋남 = ref↔student substrate 결함).
이는 표현 계층(joint-exact join·캡션·phrasebook)으로 치유되지 않는 **분석 substrate 문제**다.

### 분기 결과 (BRANCH CONTROL, D-04)

**이 phase 는 여기서 HALT 한다.** 33-02+ 표현 계층 플랜으로 진행하지 않는다.
planner 로 돌아가 **C+M3 substrate 트랙(`.planning/debug/ref-student-substrate-gap.md`)을
phase 33 에 편입**한 뒤, 어떤 표현 작업보다 먼저 ref↔student 정합(기준 프레임 국면 대응 +
실측 window substrate 복원)을 해결해야 한다. 이 분기는 belle 질문이 아니라 실측 판정이다(D-01/D-04).

**단, D-20 준수:** C+M3 편입은 채점 산식/임계값 변경이 아니라 substrate(프레임 정합·window 측정)
복원 트랙이다. re-plan 시에도 채점 math 무접촉 원칙은 유지된다.
