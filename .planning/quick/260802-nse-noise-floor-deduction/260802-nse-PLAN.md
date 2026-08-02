---
phase: quick-260802-nse
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/measurement_error.py
  - backend/tests/test_measurement_error.py
  - backend/shared/python/sunity_shared/analysis/deduction_engine.py
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/models.py
  - app/src/types/analysis.ts
  - docs/contract.md
  - backend/tests/test_noise_floor_suppression.py
  - backend/evals/realfixture/replay.py
  - .planning/quick/260802-nse-noise-floor-deduction/legacy_baseline.py
  - .planning/quick/260802-nse-noise-floor-deduction/noise_floor_effect.json
autonomous: true
requirements: [NSE-01, NSE-02, NSE-03]
user_setup: []

must_haves:
  truths:
    - "감점 record 가 주장하는 '이 관절은 허용치를 넘는다'가 그 값의 측정 불확실도 안에서 성립하지 않으면 그 record 는 방출되지 않는다"
    - "문턱은 임의 상수가 아니라 record 가 보고한 median 을 만든 바로 그 표본에서 유도되고, 테스트가 그 유도를 되읽어 잠근다"
    - "불확실도를 구할 수 없는 criterion 은 종전대로 감점한다 (fail-closed) — window 경로·reach·split·fallback 전부"
    - "점수는 오직 올라가거나 그대로다 — 억제는 record 를 지울 뿐 새 record 를 만들지 않는다"
    - "지워진 감점은 사라지지 않고 그 크기와 이유가 doc 에 남아 이동분을 산술로 재구성할 수 있다"
    - "실 doc 4건의 점수·record 수·카드 수 이동이 전건 표로 산출되고, 각 이동이 지워진 감점 합과 일치한다"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/measurement_error.py"
      provides: "정렬 차이 표본에서 median 의 분포무관 신뢰구간 (numpy 외 의존 0)"
      contains: "def median_ci"
    - path: "backend/tests/test_measurement_error.py"
      provides: "신뢰수준의 정의적 성질(커버리지) + 최소표본 유도 + window 경로 구조적 fail-closed 를 되읽는 게이트"
    - path: "backend/tests/test_noise_floor_suppression.py"
      provides: "기본 off byte-동일 / 단조 상승 / activated 집합 불변 / 억제 내역 재구성 게이트"
    - path: ".planning/quick/260802-nse-noise-floor-deduction/noise_floor_effect.json"
      provides: "실 doc 4건 전/후 점수·record·카드 + 억제 record 별 wouldBePoints"
  key_links:
    - from: "backend/functions/pipeline/app.py::_build_deduction_measured_deviations"
      to: "deduction_engine.tally"
      via: "measurement_error out-param → measurement_error kwarg"
      pattern: "measurement_error"
    - from: "backend/shared/python/sunity_shared/analysis/deduction_engine.py"
      to: "DeductionBreakdown.suppressed_records"
      via: "record 방출 직전 억제 + 내역 보존"
      pattern: "suppressedRecords"
---

<objective>
감점 record 가 하는 주장은 하나다 — **"이 관절의 편차가 허용치를 넘는다."** 그 주장을
그 값 자신의 측정 불확실도로 검정해서, 불확실도 안에서 성립하지 않는 주장은 방출하지
않는다.

belle 실기기 (kip-up 어깨): `measuredValue 20.67 / tolerance 20 / deviation 0.67 /
points -0.8`. *"에러라기보다는 대응이 필요."*

Purpose: 저신뢰 측정의 산물이 점수와 카드에 그대로 실려 있다. elbow-twist 실 doc 은
감점 −36.9 전부가 8관절에서 나오고, 그중 여섯이 허용치를 0.4~3.2도 넘긴 것들이다.
이 doc 은 시스템이 스스로 `attributionReliability.unreliable=true` 를 붙인 doc 이고,
그 게이트의 서명이 정확히 **"8관절이 허용치를 조금씩 균일하게 넘는다"** 이다.

Output: 순수 통계 모듈 1개 + 엔진 억제 seam + 억제 내역 계약 필드 + 실 doc 4건 효과 표.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@.planning/STATE.md
@backend/shared/python/sunity_shared/analysis/deduction_engine.py
@backend/shared/python/sunity_shared/analysis/motiondtw.py
@backend/shared/python/sunity_shared/analysis/moment.py
@backend/evals/realfixture/replay.py
@.planning/quick/260802-czw-keypoint-fixture-keypointreport-joints3d/260802-czw-SUMMARY.md
</context>

---

## 방법 선택 — 왜 이것이고 왜 저것들이 아닌가

**결정: 그 값을 만든 바로 그 표본의 순서통계에서 얻는 median 의 분포무관(부호검정)
신뢰구간.** 판정은 `구간하한 L > tolerance` 이면 감점, `L ≤ tolerance` 이면 방출 안 함.

`per_joint_deviation` 이 내놓는 값은 DTW 정렬 경로 각 스텝의 `|Δ각도|` 를 모은 열의
median 이다. 그 열이 곧 표본이고, 표본이 있으므로 불확실도는 유도된다.

**해석적 근사(`1.253σ/√N`)를 쓰지 않는 이유 — 그 자신이 자기모순이다.**
`motiondtw.py:201-212` 가 median 을 택한 근거를 이미 적어 뒀다: 분포가 두껍고 p99 이
35~50도에 이르는 outlier frame 이 다수라 mean 이 끌려간다. σ 는 바로 그 outlier 가
지배하는 통계량이다. median 이 무시하려고 고른 것으로 median 의 오차를 재는 셈이 된다.
정규성 가정도 그 문장과 정면으로 충돌한다.

**부트스트랩을 쓰지 않는 이유.** 프로덕션에 난수 시드라는 새 임의 상수가 들어오고
결정성이 시드에 매달린다. 스칼라 median 하나에 대해 정확한 순서통계 구간보다 나은
정확도를 주지도 않는다.

**순서통계를 쓰는 이유.** 정확(이항, 점근 근사 0) · 분포무관 · 결정적(난수 0) ·
`np.median` 이 이미 하는 정렬 한 번 · 그리고 **구간의 양 끝이 실제로 관측된 `|Δ|` 값**
이다 — 외삽한 숫자가 아니다.

**신뢰수준 = 양측 95%.** record 는 "허용치를 넘는다"는 **단정**을 하고 있고, 단정을
세우는 관례 수준이 95% 다. 이 수준은 fixture 를 보고 고르는 것이 아니다 (아래
hard invariant 3).

**알려진 한계 — 독립 가정 위반, 그리고 그 편향의 방향.** DTW 경로 스텝은 독립이 아니다
(같은 학생 프레임을 여러 스텝이 가리키고 인접 프레임은 상관이 크다). 유효 표본수는 N
보다 작고, 따라서 이 구간은 **참 95% 구간보다 좁다**. 좁은 구간 → 하한이 높음 →
**덜 억제** = 종전대로 감점하는 쪽. 편향이 fail-closed 방향이다. 이번 사이클에서
자기상관 보정을 넣지 않는다 — 그것이야말로 새 튜닝 상수다. 모듈 독스트링에 이 한계와
방향을 적는다.

## 관절별인가 전역인가 — 재현성과 적응성의 맞바꿈

**결정: record 단위 적응적.** 각 record 의 구간은 그 record 의 값을 만든 표본에서만
나온다. 코퍼스 표도, 저장된 관절별 상수도 없다.

- **왜 적응적인가:** 억제 대상은 *이 측정*의 주장이다. *이 측정*의 불확실도가 그
  주장의 유일하게 옳은 잣대다. 실측상 관절별 구간폭이 크게 다르다(같은 doc 안에서도
  hw 0.43 ~ 7.01) — 전역 상수 하나는 어느 관절에도 맞지 않는다.
- **왜 고정표가 아닌가:** 코퍼스에서 뽑은 관절별 표는 그 코퍼스에 맞춘 상수 묶음이고
  (임의 상수 금지 위반), 포즈 모델·fps·기준 영상이 바뀔 때마다 re-fit 이 필요하다.
- **Phase 34 "같은 자세면 같은 점수" 와의 관계 — 숨기지 않고 적는다.** 구간은
  `(path, user_seg, reference_angles)` 의 **순수 함수**다. 같은 입력 → 같은 구간 →
  같은 점수(결정성 유지). 다만 *같은 자세를 더 흔들리게 촬영*하면 구간이 넓어져 억제가
  더 걸릴 수 있다. 이것은 새 분산원이 아니다 — 그 촬영은 이미 오늘도 다른 편차값을
  낸다. 이 사이클은 그 분산이 **감점으로 새는 것**을 막는 쪽이다. Phase 34 가
  이 seam 을 재검토 대상으로 삼을 수 있도록 SUMMARY 에 명시한다.

## 적용 지점 — 왜 엔진의 record 방출 직전인가

| 후보 | 판정 |
|---|---|
| md 생산(builder)에서 키를 안 내보낸다 | **금지.** `activated` 집합이 바뀌고 cross-exclusion(`deduction_engine.py:296-311`)의 입력이 바뀐다. `leg_extension` 이 비활성화되면 그것이 claim 하던 `angle_vs_reference__{무릎}` 이 **되살아나** record 가 늘 수 있다 → 점수가 내려간다 → hard invariant 3 위반 |
| `_criterion_deduction` 의 `over = max(0, d - tol)` 을 `- floor` 로 | **금지.** 모든 감점의 **크기**를 깎는다. 그것이 밴드다(belle "밴드 금지") |
| **record 방출 직전 (`records.append` 앞)** | **채택.** `activated`/cross-exclusion 은 byte-불변, 살아남는 record 의 `points` 도 byte-불변. 문턱은 오직 **방출 여부**만 가른다 |

## deviationSource 별 처분 — 여섯 갈래 전부 명시

| criterion / source | 표본 | 처분 |
|---|---|---|
| `angle_vs_reference__{jk}` — DTW 경로 | 정렬 스텝 `\|Δ\|` 열 (N=100~330 관측) | **적용** |
| `angle_vs_reference__{jk}` — window 경로 | 최대 5 프레임 | **fail-closed.** 이유 둘: (a) 최소표본 미달(아래) (b) 추정량 자체가 다르다 — 학생 window median 과 기준 window median 의 **차**이지 차이의 median 이 아니다 |
| `split_angle` | 없음 (vision 주입 추정 또는 peak) | **fail-closed** |
| `leg_extension` / `arm_extension` / `line` (ipsf_absolute) | 다른 추정량(`dimensions._select_window` 창 집계) | **이번 사이클 범위 밖 → fail-closed.** 별도 유도가 필요하다. 한계로 기록 |
| `body_relative_reach` | 시계열 없음 | **fail-closed** |
| `dimension_overall_fallback` | 편차가 아니라 whole-score | **fail-closed** |

**window 경로 fail-closed 는 우연이 아니라 구조다.** 양측 95% 분포무관 median 구간이
존재하려면 `2^-N ≤ α/2`, 즉 `N ≥ ceil(log2(2/α)) = 6`. `features.window_median_angle_deltas`
의 `window` 기본값 2 → 최대 `2*2+1 = 5` 표본. **방법 자신이 "이 median 은 못 묶는다"고
선언한다** → 25-01 pointed 경로 무회귀가 설계로 보장된다. 테스트는 이 6도 5도 리터럴로
쓰지 않고 `α` 와 `inspect` 로 읽은 기본값에서 유도해 대조한다.

---

<hard_invariants>
1. **점수는 오직 올라가거나 그대로.** 억제는 record 를 지울 뿐 만들지 않는다.
2. **모든 이동이 산술로 설명된다.** `Σexec_after == Σexec_before − Σ wouldBePoints`,
   `final_after == max(scoreFloor, round(100 + executionCappedTotal + criticalTotal))`.
   설명 못 하는 이동이 하나라도 있으면 실패다.
3. **신뢰수준은 fixture 를 보고 고치지 않는다.** 95% 는 착수 전에 고정한다. 효과 표가
   기대와 다르게 나오면 그것은 **보고할 발견**이지 돌릴 손잡이가 아니다. 수준을 바꾸고
   싶으면 멈추고 belle 에게 근거와 함께 묻는다.
4. **밴드 아님.** 살아남은 record 의 `points` 는 종전과 byte-동일하다. 문턱은 방출
   여부만 가른다.
5. **fail-closed.** 구간을 못 구하면 종전대로 감점한다. "못 구했다"를 "감점 0"으로
   번역하지 않는다.
6. **동작명 분기 0.** 규칙은 criterion id 와 표본만 본다. 엔진은 관절 이름조차 파싱하지
   않는다(criterion id 로 조회).
7. **기본 off = byte-동일.** 새 인자 미전달 시 산출은 이 사이클 이전과 완전히 같다.
</hard_invariants>

---

## 착수 전 실측 (오케스트레이터가 계획 중 잰 값 — 기대값 아님)

`backend/.venv/bin/python` + `motiondtw.motion_dtw` 로 실 fixture 4건의 DTW 열을
직접 만들어 잰 것이다. **`replay.py` 는 `app._deviation_against` 를 타므로 산출이
미세하게 다를 수 있다** (probe 에서 pdshape `right_knee` med 19.86 vs 저장
`measuredValue` 20.19). 아래 숫자는 **설계가 성립하는지 확인한 근거**이지 테스트에
박을 기대값이 아니다. 실측은 Task 3 이 하네스로 다시 낸다.

| fixture | record | d | CI95 하한 | 처분 |
|---|---|---|---|---|
| elbow-twist (final 63) | `right_elbow` 30.29 | 26.99 | 감점 유지 −12.4 |
| | `right_shoulder` 29.22 | 25.40 | 감점 유지 −11.1 |
| | `left_elbow` 23.15 | 20.52 | 감점 유지 −3.8 |
| | `right_knee` 22.14 | 18.52 | **억제** −2.6 |
| | `left_hip` 21.86 | 19.66 | **억제** −2.2 |
| | `left_knee` 21.81 | 18.93 | **억제** −2.2 |
| | `right_hip` 21.72 | 18.55 | **억제** −2.1 |
| | `left_shoulder` 20.41 | 16.91 | **억제** −0.5 |
| kip-up (final 79) | `left_shoulder` 20.67 | 16.70 | **억제** −0.8 (belle 이 지목한 그 record) |
| | `split_angle` (vision) | — | fail-closed 유지 −20 |
| pdshape (final 100) | `right_knee` 20.19 | 11.97 | **억제** −0.2 |
| power-spin (final 60) | `left_shoulder` 30.67 | 24.83 | 감점 유지 −12.8 |
| | `leg_extension` (ipsf_absolute) | — | fail-closed 유지 −20 |

**관측된 성질:** elbow-twist 에서 살아남는 셋(양 팔꿈치 + 오른어깨)이 그 동작의 실제
결함이고, 지워지는 다섯이 정확히 "8관절 균일 소폭 초과" 서명이다.

**68% 수준도 함께 재봤다 (선택을 숨기지 않기 위해 기록).** 68% 에서는 elbow-twist 에서
`left_shoulder` 하나만 억제되고 네 관절(hip/knee)은 하한이 20 을 아슬하게 넘어 살아남는다.
**95% 를 고른 근거는 이 표가 아니라 "단정을 세우는 관례 수준"이다** (hard invariant 3).

---

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 측정 불확실도 모듈 — 표본에서 median 구간을 유도하고, 그 유도를 테스트가 되읽는다</name>
  <files>
backend/shared/python/sunity_shared/analysis/measurement_error.py,
backend/tests/test_measurement_error.py,
.planning/quick/260802-nse-noise-floor-deduction/legacy_baseline.py,
.planning/quick/260802-nse-noise-floor-deduction/pytest_before.txt
  </files>
  <behavior>
- `median_ci_order_index(n, alpha)` — 양측 `1-alpha` 분포무관 구간을 주는 1-indexed
  순서통계 k. 정확 이항 꼬리 `Σ_{i<k} C(n,i) / 2^n ≤ alpha/2` 를 만족하는 최대 k,
  없으면 `None`. 정규 근사 금지.
- `median_ci(sample, alpha=CI_ALPHA)` — 유한값만 추려 정렬 후 `(L, U)`. 표본이
  최소크기 미만이거나 유한값 0이면 `None` (fail-closed).
- `per_joint_median_ci(path, A_user_seg, A_ref, alpha=CI_ALPHA)` —
  `{joint_index: (L, U)}`. `path` 빈 값 → `{}`. 어떤 관절이든 구간 부재면 키 부재.
- **커버리지(수준의 정의적 성질):** 참 median 을 아는 합성 표본을 반복 생성해 구간이
  참값을 덮는 비율이 `1-alpha` 이상. 정규·두꺼운꼬리(라플라스/혼합) 둘 다에서 성립
  (분포무관임을 실증). 테스트 안에서만 고정 시드 사용 — 프로덕션 난수 0.
- **최소표본이 유도된다:** 모든 `n < ceil(log2(2/CI_ALPHA))` 에서
  `median_ci_order_index(n, CI_ALPHA) is None`, 그 값 이상에서 not-None.
  경계값을 리터럴로 쓰지 않고 `CI_ALPHA` 에서 계산해 대조.
- **window 경로가 구조적으로 미달임을 되읽는다:**
  `inspect.signature(features.window_median_angle_deltas).parameters["window"].default`
  로 기본 window 를 읽어 최대 표본수 `2*w+1` 을 계산하고, 그것이 최소표본 미만임을
  단언. 숫자 5·6 을 손으로 쓰지 않는다.
- **값과의 정합:** 같은 `(path, A_user_seg, A_ref)` 에 대해 모든 관절에서
  `L ≤ motiondtw.per_joint_deviation(...)[j] ≤ U` (구간이 자기가 묶는 값을 실제로 묶는다).
- **fail-closed:** 빈 path / 전부 NaN 열 / 표본 미달 → 키 부재 또는 `None`.
  예외를 던지지 않는다.
  </behavior>
  <action>
착수 기준선을 먼저 잡는다 (되돌아볼 수 없는 것부터).
`set -o pipefail` 아래 `BASE=$(git rev-parse HEAD)` 를 SUMMARY 에 적고,
`PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests` 를
`pytest_before.txt` 로 캡처한다 (착수 시점 관측치 = 59 failed / 3842 passed; 다르면
그 값을 그대로 기준선으로 쓰고 차이를 SUMMARY 에 적는다).
`.planning/quick/260731-f5h-.../legacy_baseline.py` 를 이 quick 디렉터리로 복사해
`--capture` 를 돌려 카드 PNG 해시 기준선을 만든다 (변경 후에는 캡처가 불가능하다).

그 다음 `measurement_error.py` 를 새로 만든다. **numpy 외 의존 0** —
boto3/firestore/네트워크 import 금지 (`deduction_engine` 과 같은 규율).
`motiondtw.per_joint_deviation` 은 **한 글자도 건드리지 않는다** — 그 함수 소스의
SHA-256 이 `backend/tests/phase33/test_m3_alignment_only.py` 에 박제돼 있다.
`per_joint_representative_frames` 가 만든 선례대로 같은 `diffs` 순회를 sibling 으로
복제한다 (중복이지만 박제를 우회하지 않고 통과하는 유일한 길).

`CI_ALPHA` 는 값 옆에 **왜 이 수준인지**를 적는다: record 가 "허용치를 넘는다"는
단정을 하고 있고 95% 는 단정을 세우는 관례 수준이라는 것. fixture 에서 유도한 값이
아니라는 것을 명시하고, 커버리지 테스트가 그 수준의 **정의적 성질**을 검증한다는 것을
가리킨다 (`moment.RECORD_VALUE_DECIMALS` 가 엔진 출력에서 자릿수를 되읽는 선례와
같은 종류의 잠금이다).

모듈 독스트링에 위 "방법 선택" 절의 요지를 적는다 — 해석적 근사가
`motiondtw.py:201-212` 와 자기모순인 이유, 부트스트랩을 버린 이유, 그리고
**독립 가정 위반과 그 편향이 fail-closed 방향이라는 것**. 한계를 숨기지 않는다.

주석·독스트링은 한국어, `quick-260802-nse` 인용. **`9.0` 같은 fps 리터럴과 `ref-` 로
시작하는 동작명 문자열을 새 독스트링에 쓰지 않는다.** 이모지 금지.
  </action>
  <verify>
    <automated>set -o pipefail; PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/test_measurement_error.py backend/tests/phase33/test_m3_alignment_only.py 2>&1 | tail -5</automated>
  </verify>
  <done>
`test_measurement_error.py` 전건 통과 + `per_joint_deviation` SHA-256 박제 게이트 통과.
`pytest_before.txt` 와 `legacy_baseline_before.json` 이 리포에 존재한다.
`grep -n "1.253\|bootstrap\|random\|seed" measurement_error.py` 가 프로덕션 코드에서
0건 (테스트 파일의 시드는 허용).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 억제 seam — 엔진 방출 직전에서 가르고, 지워진 감점을 doc 에 남긴다</name>
  <files>
backend/shared/python/sunity_shared/analysis/deduction_engine.py,
backend/functions/pipeline/app.py,
backend/shared/python/sunity_shared/models.py,
app/src/types/analysis.ts,
docs/contract.md,
backend/tests/test_noise_floor_suppression.py
  </files>
  <behavior>
- **기본 off byte-동일:** `tally(..., measurement_error=None)` 산출이 이 사이클 이전과
  키·값 모두 같다 (`suppressedRecords` 키 자체가 없다). 기존 record 방출 경로를 태우는
  테스트가 하나도 안 깨진다.
- **억제 규칙:** `measurement_error[cid] = (L, U)` 가 있고 `L <= crit["tolerance"]` 면
  그 record 를 방출하지 않는다. `L > tolerance` 면 종전과 완전히 같은 `points` 로 방출.
- **단조 상승:** 같은 입력에 대해 `final(with) >= final(without)` 이 항상 성립하고,
  `records(with) ⊆ records(without)` (부분집합 — 새 record 0). 합성 입력 다수로 검증.
- **activated 불변:** `measurement_error` 유무와 무관하게 cross-exclusion 결과가 같다
  (억제된 criterion 이 claim 하던 관절이 되살아나지 않는다).
- **fail-closed:** dict 에 키가 없는 criterion, `(L,U)` 가 `None`/비유한/형상불량,
  `measurement_error` 자체가 None → 전부 종전대로 감점.
- **억제 내역 재구성:** `suppressedRecords[]` 각 항목의 `wouldBePoints` 합이
  `executionRawTotal(without) − executionRawTotal(with)` 과 0.1 단위로 일치.
- **flat scalar only:** 항목 값에 dict/list 0 (Firestore nested-array 금지).
- **빌더 md 불변:** `measurement_error_out` 전달 유무와 무관하게 반환 md 가 키·값 모두
  같다 (`measured_at_out`/`seed_audit_out` 과 정확히 같은 보장).
  </behavior>
  <action>
**엔진** (`deduction_engine.py`):
`tally(...)` 에 keyword-only `measurement_error=None` 추가. record 루프에서
`_criterion_deduction` 이후·`records.append` **직전**에 억제 판정을 넣는다 —
`over <= 0.0` dead-zone 다음 자리다. 억제 시 `DeductionRecord` 를 만들지 않고 억제
항목만 모은다. `_two_track_final` 은 손대지 않는다 (억제된 record 는 애초에 리스트에
없으므로 산식이 그대로 성립한다).

`DeductionBreakdown` 에 `suppressed_records: tuple = ()` 를 default 필드로 추가하고
`to_dict()` 는 **비어 있으면 키를 생략**한다 — `rawPoints`/`capApplied`/`executionCap`
가 이미 만든 additive-optional 패턴 그대로 (구 doc·구 앱 무영향).

억제 항목 키 (flat scalar 8종):
`criterion` / `measuredValue` / `tolerance` / `intervalLow` / `intervalHigh` /
`sampleSize` / `wouldBePoints`(signed-negative, per-record 상한 적용 후 값 =
방출됐다면 들어갔을 그 값) / `ruleId`(`"deviation_within_measurement_error"`).
`wouldBePoints` 가 있어야 belle 의 "투명 합산" 이 유지된다 — 얼마를 왜 빼지 않았는지
doc 만 보고 되짚을 수 있다.

**엔진은 관절 이름을 파싱하지 않는다.** `measurement_error` 를 criterion id 로만
조회한다 (동작명 분기 0, hard invariant 6).

**빌더** (`app.py::_build_deduction_measured_deviations`):
`measurement_error_out=None` out-param 추가. `dtw_by_joint` 를 만드는 그 `try` 블록
안(같은 `path`/`user_seg`/`reference_angles` 를 이미 손에 쥔 자리)에서
`measurement_error.per_joint_median_ci` 를 부르고, **`_emit_reference_relative` 가 True
를 돌려준 DTW-fallback 관절에 한해** `measurement_error_out[f"angle_vs_reference__{jk}"]`
에 기록한다. window 경로 관절에는 기록하지 않는다 (추정량이 다르다 — 위 표 참조).
실패는 예외가 아니라 **항목 부재**로만 반영한다 (fail-closed).
**md 는 절대 mutate 하지 않는다** — 독스트링의 byte-동일 보증 문장에 이 out-param 을
함께 적는다.

**배선:** `_apply_vision_veto`(2791) → `_apply_vision_veto_from_context`(2915) →
`tally`(3036) 로 `measured_deviations`/`baseline_kind` 와 나란히 `measurement_error`
를 넘긴다. 호출부 6092 에서 빌더의 out-param dict 를 전달. mode3 경로(2977)와
legacy 경로(2874)에는 넘기지 않는다 — 그쪽엔 기준 DTW 표본이 없다(fail-closed).

**계약 3자 미러:**
- `models.py` — `DEDUCTION_BREAKDOWN_OPTIONAL_KEYS` 에 `"suppressedRecords"` 추가 +
  `SUPPRESSED_RECORD_KEYS` 신설, 주석에 "방출되지 않은 감점의 내역"임을 명시.
- `app/src/types/analysis.ts` — `DeductionBreakdown` 에 optional 필드 + 항목 인터페이스.
  **렌더링은 이 사이클 범위 밖** (belle 승인 없는 표시 추가 금지) — 타입만 미러.
- `docs/contract.md` §10 — 억제 규칙·키 표·fail-closed 6갈래·재구성 항등식을 적는다.
  `final` 산식 문장은 손대지 않는다 (산식은 안 바뀐다).

**깨지는 테스트를 무르게 고치지 않는다.** 기본 off 라 대부분 안 깨져야 정상이다.
그래도 깨지면 (a) 어느 테스트가 (b) 왜 깨졌는지 (c) 기대값을 바꾸는 게 왜 옳은지를
SUMMARY 에 근거와 함께 적는다. 숨기지 않는다.
  </action>
  <verify>
    <automated>set -o pipefail; PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/test_noise_floor_suppression.py backend/tests/test_deduction_two_track.py backend/tests/test_pipeline_deduction_seam.py backend/tests/test_deduction_seed_pointed_merge.py backend/tests/test_mode3_tally_seam.py backend/tests/test_record_measured_at.py backend/tests/test_attribution_reliability_marker.py 2>&1 | tail -8 && (cd app && npm run typecheck 2>&1 | tail -3)</automated>
  </verify>
  <done>
`test_noise_floor_suppression.py` 전건 통과. 기존 tally/seam 테스트 무회귀.
`npm run typecheck` 통과. `docs/contract.md`·`models.py`·`analysis.ts` 세 곳에
`suppressedRecords` 가 존재한다 (`grep -c` 로 3/3).
  </done>
</task>

<task type="auto">
  <name>Task 3: 실 doc 4건에서 이동을 수치로 — 무엇이 왜 얼마나 움직였나</name>
  <files>
backend/evals/realfixture/replay.py,
.planning/quick/260802-nse-noise-floor-deduction/noise_floor_effect.json,
.planning/quick/260802-nse-noise-floor-deduction/legacy_baseline.json,
.planning/quick/260802-nse-noise-floor-deduction/pytest_after.txt
  </files>
  <action>
`replay.py` 에 새 인자를 배선한다 — 하네스가 프로덕션 경로를 재현하는 것이 존재
이유이므로 배선하지 않으면 하네스가 프로덕션과 갈라진다.
`--noise-floor` 플래그로 억제 on/off 를 가르고, **기본은 off** 로 둔다.
`--recon-only` 의 exit code 규약은 그대로다 (RECON 은 저장된 07-31 doc 을 재현하는
것이므로 반드시 off 로 돈다 — 억제를 켜고 RECON 을 돌리면 억제된 record 가 MISSING 으로
찍혀 게이트 의미가 뒤집힌다).

`--noise-floor-report` 로 **같은 fixture 를 두 번**(off/on) 돌려 `noise_floor_effect.json`
을 낸다. 처리 변수는 억제 하나뿐이다.

**산출에 반드시 들어갈 것 (전건, fixture 4건 × 항목):**

| 축 | 내용 |
|---|---|
| 점수 | `final` before / after / delta |
| record | 개수 before / after + 억제된 criterion 목록 |
| 카드 | `faultZoomComparisons` 장수 before / after + 사라진/생긴 카드의 criterion |
| 억제 내역 | criterion 별 `measuredValue` / `tolerance` / `intervalLow` / `intervalHigh` / `sampleSize` / `wouldBePoints` |
| 재구성 | `Σ wouldBePoints` 와 `executionRawTotal` 차이의 일치 여부, `final` 항등식 성립 여부 |
| fail-closed | 구간이 없어 종전대로 감점한 criterion 목록과 그 이유 코드 |
| 표시 연쇄 | 감점 시트 행 수 before / after + 요약·"오늘의 교정" 이 가리키는 record 의 before / after |

**연쇄를 확인하고 적는다 — record 가 사라지면 그것에 매달린 것이 전부 사라진다.**
`deductionBreakdown.records[]` 는 네 곳으로 흘러간다:
`fault_zoom.criterion_units_from_records`(백엔드 — crop 출생) →
`app/src/lib/deductionSheet.ts`(감점 시트 행) →
`app/src/lib/deductionLabels.ts::matchZoomForDeductionRecord`(행↔카드 조인) →
`app/src/lib/summarySource.ts`(요약 문장·"오늘의 교정").

**특히 `summarySource.ts:240` 은 `sort((a,b) => a.points - b.points)[0]` 로 가장 큰
감점 record 를 헤드라인으로 뽑는다.** 억제가 항상 작은 record 만 지우는 것은 아니다 —
편차가 크지만 구간이 넓은 record 가 지워지고 더 작은 record 가 살아남는 조합이 원리적으로
가능하다. 그러면 **헤드라인 문장이 바뀐다.** 효과 표에 before/after 헤드라인 record 를
넣어 그런 일이 일어났는지 수치로 답한다. 일어났다면 고치지 말고 **belle 확인 대상으로
보고**한다 (표시 정책 변경은 이 사이클 범위 밖).

음성은 별도 record 소비처가 아니라 요약 문장을 읽는 경로다 — 헤드라인이 안 바뀌면
음성도 안 바뀐다. 실기기 발화 확인은 `<human-check>` 로 분리한다 (F-6 음성 무음은
이미 아는 미해결이므로 여기서 시간을 쓰지 않는다).

**elbow-twist 63 이 어디로 가는지 반드시 포함한다.** 그 fixture 는 RECON 8/8 MATCH 인
유일한 다-record fixture 라 판정 자격이 있는 유일한 건이다 (czw SUMMARY). kip-up 의
`split_angle` 과 power-spin 의 `leg_extension` 은 애초에 재현되지 않는 record 이므로
(czw Deviation 1·2), 그 fixture 의 before/after 는 **재현된 record 범위 안에서만**
읽는다는 것을 산출물 `limits` 에 적는다 — 저장 doc 의 79/60 과 직접 비교하지 않는다.

**내려가는 케이스가 하나라도 있으면 멈춘다.** hard invariant 1 위반이고 설계 오류다.
숫자를 맞추지 말고 원인을 SUMMARY 에 적고 belle 에게 보고한다.

**설명 안 되는 이동이 하나라도 있으면 멈춘다.** 재구성 항등식이 안 맞으면 그것이
결함이다.

**부수 관측 (고치지 말고 기록만):** `attributionReliability` 마커는 md 기준
`over_tol_count` 로 발화하고 md 는 안 바뀌므로 **그대로 발화한다**. 억제 후 남은 3
record 에도 "AI 공부중" 강등이 계속 붙는다. 이 마커를 재계산하는 것은 별도 표시
결정이라 이 사이클 범위 밖이다 — SUMMARY 에 후속 판단 대상으로 적는다.

**회귀 게이트 3종:**
1. `pytest_after.txt` 를 `pytest_before.txt` 와 **FAILED/ERROR node ID diff** 로 대조.
   신규 실패 0 이 목표. 있으면 node ID 와 원인을 표로 적는다.
2. `legacy_baseline.py --verify` — 카드 PNG 해시. 이 사이클은 `fault_zoom.py` 를
   건드리지 않으므로 `match: true` 가 기대다. 바뀌면 **무엇이 바뀌었는지** 적는다.
3. `git diff $BASE --stat` 으로 손댄 파일이 `files_modified` 를 넘지 않는지 확인.

**GPU·Pod·Gemini·Firestore 쓰기 0.** 하네스의 죽는 스텁을 그대로 쓴다.
실기기 확인은 아래 `<human-check>` 로 분리한다.
  </action>
  <verify>
    <automated>set -o pipefail; backend/.venv/bin/python backend/evals/realfixture/replay.py --recon-only 2>&1 | tail -3; backend/.venv/bin/python backend/evals/realfixture/replay.py --noise-floor-report --out .planning/quick/260802-nse-noise-floor-deduction/noise_floor_effect.json 2>&1 | tail -20 && backend/.venv/bin/python .planning/quick/260802-nse-noise-floor-deduction/legacy_baseline.py --verify 2>&1 | tail -3</automated>
    <automated>set -o pipefail; PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests 2>&1 | tail -3 &gt; .planning/quick/260802-nse-noise-floor-deduction/pytest_after.txt; cat .planning/quick/260802-nse-noise-floor-deduction/pytest_after.txt</automated>
    <human-check>belle 실기기 — kip-up 어깨 `20.67 / 20 / -0.8` 카드가 사라졌는지, elbow-twist 결과 화면에서 남은 감점 항목이 팔꿈치·어깨 쪽으로 좁혀졌는지. OTA 발행은 belle 확인 후 별도 결정.</human-check>
  </verify>
  <done>
`noise_floor_effect.json` 에 fixture 4건 전건 표가 있고, 모든 점수 delta 가 `>= 0`
이며, 모든 delta 가 `Σ wouldBePoints` 로 설명된다. `--recon-only` exit code 가 착수
시점과 같다(1 — 저장 doc 재현 자격은 안 바뀐다). `legacy_baseline.py --verify` 결과와
pytest FAILED/ERROR node ID diff 가 SUMMARY 에 수치로 기록돼 있다.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|---|---|
| 없음 (신규) | 신규 네트워크 엔드포인트·인증 경로·외부 입력 0. 계산은 이미 신뢰경계 안에 있는 각도 행렬에서만 일어난다 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|---|---|---|---|---|
| T-nse-01 | Tampering | `deduction_engine.tally` 억제 seam — 점수를 바꾸는 코드 | mitigate | 기본 off byte-동일 + 단조 상승(부분집합) 불변식 테스트 + `activated` 집합 불변 테스트. 억제가 점수를 **내릴** 경로가 존재하지 않음을 합성 입력으로 증명 |
| T-nse-02 | Information disclosure | `suppressedRecords` 가 Firestore doc 에 기록됨 | accept | 전부 수치(도·개수·점수)와 criterion id. PII·좌표·영상 식별자 0. 기존 `records[]` 와 같은 민감도 |
| T-nse-03 | Denial of service | `per_joint_median_ci` 가 DTW 경로마다 열 정렬 | accept | O(N log N), 관측 N ≤ 330 · 8관절. 기존 `per_joint_representative_frames` 가 이미 같은 순회를 한 번 더 한다 |
| T-nse-SC | Tampering | npm/pip/cargo install | n/a | **신규 의존성 0** — numpy 는 이미 있는 것. 설치 태스크가 없으므로 package legitimacy 게이트 비대상 |
</threat_model>

<verification>
- `set -o pipefail` 아래 `BASE=$(git rev-parse HEAD)` 고정 후 `git diff $BASE`.
- 백엔드 전체: `PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests`
  (⚠ `cd backend && .venv/bin/python -m pytest` 는 수집에서 중단돼 0개 실행 = 거짓 통과.
  절대 그 형태로 돌리지 않는다.) 착수 관측치 59 failed / 3842 passed 와 **node ID diff**.
- 앱: `cd app && npm run typecheck`.
- 카드 무회귀: `legacy_baseline.py --capture`(Task 1) → `--verify`(Task 3).
- 실 doc 효과: `replay.py --noise-floor-report`. GPU·Pod·Gemini 0.
</verification>

<success_criteria>
1. `20.67 / 20 / -0.8` 유형의 record 가 방출되지 않고, 그 이유와 크기가 doc 에 남는다.
2. 문턱이 상수 표가 아니라 그 값을 만든 표본에서 유도되고, 테스트가 유도(커버리지 성질 +
   최소표본 + window 구조적 미달)를 되읽어 잠근다.
3. 실 doc 4건의 점수·record·카드 이동이 전건 표로 산출되고 **전부 상승 또는 불변**이며,
   각 이동이 `Σ wouldBePoints` 로 설명된다. elbow-twist 63 의 행선지가 표에 있다.
4. 구간을 못 구하는 5갈래(window/split/ipsf_absolute/reach/fallback)가 종전대로 감점한다.
5. 살아남은 record 의 `points` 가 byte-불변 (밴드 아님).
6. 신규 의존성 0, 동작명 분기 0, GPU/Pod/Gemini 호출 0.
</success_criteria>

<output>
Create `.planning/quick/260802-nse-noise-floor-deduction/260802-nse-SUMMARY.md` when done.

SUMMARY 에 반드시 포함:
- 착수/종료 pytest 수치와 **FAILED node ID diff** (요약 문장이 아니라 대조 결과)
- 실 doc 4건 전/후 표 (`noise_floor_effect.json` 을 **직접 열어 읽은 값**)
- 깨진 테스트가 있다면 어느 것이 왜 깨졌고 기대값을 바꾼 근거
- 재보지 않은 것 목록 — 실기기·mode3·ipsf_absolute 경로·`attributionReliability` 재계산
- Phase 34 앞으로 넘기는 것: 적응적 구간과 "같은 자세면 같은 점수" 의 잔여 긴장
</output>
