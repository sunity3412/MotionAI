# climb·climbfault·combo 발굴 스윕 — 발굴/침묵 시트 (quick-260821-ls0)

**이 페이지는 판정 재료다 — 판정은 belle 몫이다.** belle 08-21 지시("climb·combo
스윕 돌려놔")의 이행이다. 08-14 ehz 발굴 일반화 하네스(`discover_sweep.py`)에
3동작을 **정식 등재**(c3m SUMMARY 가 박제한 다음 사이클 절차)하고 스윕을
그대로 돌렸다. 새 하네스 발명 0, 임계 재튜닝 0.

**결과 = 3동작 전건 침묵.** 세 동작 모두 커밋된 P35 doc 의
`deductionBreakdown.records` 가 **0건**이라 발굴이 돌 감점 record 자체가 없다.
침묵을 실행 수치로 증명한다 — 후보를 억지로 성립시키지 않았고, record 소스를
다른 필드로 대체 발명하지 않았다.

---

## 1. 기계 증명 요지

- **정식 등재 (커밋 661169e3)** — `discover_sweep.py` `SWEEP_JOBS` 3행 +
  `RECORD_INVENTORY` 3행 **순수 추가**(diff `-`행 0). S3 키/motion_id 정본 =
  `backend/scripts/p35_extract_align.py` JOBS + c3m `verify_source_gate.py`:
  climb(`fixtures/phase15/climb/correct.mp4`/ref-climb),
  climbfault(`fixtures/phase15/climb/fault.mp4`/ref-climb),
  combo(`fixtures/phase15/combo/correct.mp4`/ref-combo).
- **기존 5동작 무회귀 (채택본 재현, 비파괴)** — 등재 후 pdshapefault 를
  `--fetch --scan --pairsheet` 재실행 → 재생성 `candidates.json` 이 HEAD 커밋본과
  **dict 동등**(meta.generated 타임스탬프만 제외) + stills **48/48 md5 동일**
  (개별 32 + PAIR 16). belle 채택 순간 r00/cand17B(u16.4667/r15.1333)·
  r03/cand13B(u12.8667/r12.40) 행 동일. 비교 후 evidence 는 git restore 로
  원복(덮어쓴 채 남기지 않음). Gemini 를 부르는 `--render` 재현은 하지 않았다 —
  눈 memo 가 빈 새 세션에서 실호출·채택 카드 덮어쓰기 위험이 있어 스캔 층
  byte-재현 + `--check` 로 갈음.
- **RECORD_INVENTORY 등재값 = 실행 시점 재실측** (커밋 P35 doc.json 직접 판독,
  2026-08-21): climb `records` 길이 **0** / climbfault `deductionBreakdown` 키
  자체 **부재** / combo `records: []` **0**. 플래너 실측(0/0/0)과 등재값 일치.
- **소스 게이트 3/3 PASS** (record 스캔 **전**에 판정) — P35 doc/align 실물 +
  align 스키마 11필드 + S3 read-only 영상 다운로드 + fps 교차검증.
  **"로컬 불가 — Pod 필요"로 떨어진 동작 0건.**

  | 동작 | align fps 라벨 | 프레임수/길이 (학생/기준) | 실효 fps (학생/기준) | 클립 (학생/기준) | 판정 |
  |---|---|---|---|---|---|
  | climb | 15.0 | 15.006 / 15.006 | 9.963 / 9.963 | 119f 7.93s / 119f 7.93s | PASS |
  | climbfault | 15.0 | 14.943 / 15.006 | 9.963 / 9.963 | 91f 6.09s / 119f 7.93s | PASS |
  | combo | 15.0 | 15.005 / 15.000 | 9.997 / 9.990 | 930f 61.98s / 930f 62.0s | PASS |

- **record 커버리지** — 3동작 recordCount 0/0/0 = 인벤토리 0/0/0 대조 일치.
  8동작 전체 `--check` PASS (records 13/13 — 기존 5동작 13 + 신규 3동작 0).
- **기계 눈 호출 0회** — 후보 0 이라 `machine_eye` 호출·Gemini 키 주입 자체가
  발생하지 않았다 (`eye_calls.log` 생성 0 — 하네스는 호출 시에만 로그를 만든다).
  `--pairsheet`(0장)·`--eye`(대상 0)·`--render`(eye_verdicts 부재로 생략)까지
  스테이지는 전부 실행했다.
- **실물 게이트** — 생성된 stills/짝시트/카드 **0장 = 열 실물 없음** (evidence/
  VISUAL-REVIEW.md 에 명기, 대상 부재를 통과로 치장하지 않음).
- **제약** — backend/ diff 0, S3 GET only(업로드 0), Firestore 쓰기 0(refmotion·
  대조 읽기만), Pod 무접촉, 채점 무접촉.

---

## 2. 동작별 1행 요약

| 동작 | 커밋 doc (계보) | score | deductionBreakdown | record | 스캔 | 후보 | 눈 | 결과 |
|---|---|---|---|---|---|---|---|---|
| climb | p35newclimb1786871026 (r7k 재생성본) | 100 | 존재, `records` 길이 0 | 0 | 실행 (돌 record 없음) | 0 | 0회 | **침묵** |
| climbfault | p35newclimbfault1786871285 (r7k 재생성본) | 86 | **키 자체 부재** (Firestore 원본 대조 완료 — 원본도 부재) | 0 | 실행 (돌 record 없음) | 0 | 0회 | **침묵** |
| combo | p35newcombo1786857699 (c3m 생성본) | 100 | 존재, `records: []` | 0 | 실행 (돌 record 없음) | 0 | 0회 | **침묵** |

전표 = `.planning/quick/260814-ehz-5/evidence/{climb,climbfault,combo}/candidates.json`

---

## 3. 침묵 증명 — climb (record 0)

- 커밋 doc = r7k(260816-r7k-ref-climb-replace) 재생성본. `overallScore` **100**,
  `deductionBreakdown.records` 길이 **0**. correct.mp4 가 기준 대비 감점 record 를
  하나도 만들지 않은 클린 패턴이다 (c3m combo 슬롯과 동형).
- 발굴 하네스의 record 소스는 `deductionBreakdown.records` 뿐이다 — 돌 record 가
  0 이므로 홀드 스캔·claim 유도·짝 탐색은 시작 자체가 없다. 소스 게이트와 fps
  교차검증은 전부 PASS 로 실행됐다 (등재는 유효, 재료가 없을 뿐).
- 참고 (관측): c3m(08-16) 시점의 climb doc 은 score 60 / records 3 이었으나,
  ref-climb.mp4 영상 교체 후 r7k 가 재생성한 현행 커밋본은 score 100 / records 0
  이다. 커밋본이 정본이므로 이번 스윕은 현행본 기준으로 돌았다.

## 4. 침묵 증명 — climbfault (record 0, Firestore 원본 대조 완료)

- 커밋 doc = r7k 재생성본. `overallScore` **86** 인데 `result.deductionBreakdown`
  **키 자체가 없다**.
- **Firestore 원본 대조 (Task 1, 읽기만):**
  `users/fvcNXzEqKjgqVxRPVSj1iwFnIpn2/analyses/p35newclimbfault1786871285` 실조회
  결과 — doc 존재, `result.deductionBreakdown` **원본에도 부재(None)**,
  overallScore 86 동일. **판정 = 스냅샷 결손 아님, 진짜 침묵.** 커밋 스냅샷은
  원본을 충실히 반영한다 (r7k 회수 과정의 필드 결손 가능성은 기각).
- `faultZoomComparisons` 2건(right_shoulder deficit 19.8도 · right_knee deficit
  15.3도, 둘 다 kind=deficit/tier=confirmed, userVideoSec 2.208)이 존재하지만
  이것은 **fault_zoom deficit 층으로 감점 record 와 별개 층**이다 — 하네스의
  record 소스로 쓰지 않는다 (대체 발명 금지, 플랜 명기).
- 관측만 박제 (진단 아님): 감점 86점(dimensionScores angle 86/stability 93)이
  있는데 감점 record 층이 비어 있는 이유는 이 사이클에서 **검증하지 않았다** —
  r7k 생성 경로의 산출 특성인지 여부는 미검증 항목이다 (§6 한계 4).

## 5. 침묵 증명 — combo (record 0)

- 커밋 doc = c3m(260816-c3m) 생성본. `overallScore` **100**,
  `deductionBreakdown.records: []` — c3m SUMMARY 가 이미 "클린 correct 영상 패턴
  (기존 pdshape 슬롯과 동형)"으로 박제한 그대로다.
- 62s/930프레임 클립 전체가 소스 게이트·fps 교차검증을 통과했다 — 재료(감점
  record)만 없다.

---

## 6. 한계·미결 (정직 박제)

1. **이 사이클은 판정 재료 생산만이다.** 운영 방출 아님. 반영이 필요해지는
   경우에도 belle 판정 후 별건이다.
2. **침묵의 의미는 "발굴 실패"가 아니라 "발굴 재료 부재"다.** ehz 의
   elbow/peterpan 침묵(재료는 있는데 눈이 전부 기각)과 층이 다르다 — 이번 3동작은
   스캔이 돌 감점 record 가 0 이라 게이트·눈까지 갈 것이 없었다.
3. **fault 영상인데 발굴 0 인 동작은 climbfault 뿐이다.** correct 영상 2건
   (climb·combo)의 record 0 은 클린 패턴으로 자연스럽지만, climbfault 는
   score 86 으로 감점이 있는데 record 층이 비어 있다 — 발굴로 회복할 재료가
   구조적으로 없는 상태다.
4. **climbfault 의 "감점 있음 + record 층 부재" 원인은 미검증.** 이번 사이클은
   Firestore 원본 대조로 "스냅샷 결손 아님"까지만 확정했다. r7k 생성 경로에서
   record 가 왜 비었는지(생성 특성인지, 다른 감점 경로인지)는 별건 조사 사항
   이다 — 여기서 진단을 관측처럼 적지 않는다.
5. **faultZoomComparisons 2건은 이번 스윕 산출물이 아니다** — climbfault doc 에
   원래 있던 별개 층 데이터이며, 참고 관측으로만 §4 에 박제했다.

## 7. belle 판정 대기 항목

판정 요청이 아니다 — 재료가 준비돼 있다는 사실만 적는다 (belle 이 볼 때 보면
된다).

| # | 항목 | 재료 |
|---|---|---|
| 1 | 3동작 침묵(발굴 0 — 추천 없음)을 옳은 침묵으로 볼 것인가 | §3~§5 + candidates.json 3건 |
| 2 | climbfault "감점 86 + record 층 부재" 를 별건 조사 의제로 세울 것인가 | §4 관측 + Firestore 대조 결과 |
| 3 | climbfault 의 faultZoomComparisons 2건(별개 층)을 발굴 축으로 다룰지 여부 — 다룬다면 record 소스 확장은 새 설계가 필요 | §4 |

사전 박제(동작별 추천 3행)는 belle 판정 **전에** 커밋된다 —
[wif DISCOVERY-LEDGER.md](../260813-wif-knee-discovery/DISCOVERY-LEDGER.md)
승격 실적 장부 행 9~11.
