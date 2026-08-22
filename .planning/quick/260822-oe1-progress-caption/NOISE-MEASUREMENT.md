# 발전 캡션 노이즈 문턱 측정 (quick-260822-oe1 Task 1)

측정 대상: 같은 실력이 찍은 분석 사이에서 편차(delta = |baseline − measured|)가
얼마나 요동하는가. 이 요동보다 작은 "개선"은 발전이 아니라 노이즈이므로
캡션("저번보다 더 벌어졌어요")을 붙이면 안 된다 (BELLE-0821-P3/P4).

## 판정 규칙 (측정 전 박제)

이 섹션은 **측정 실행 전에 커밋**된다 (measure-first — fe9 PREDICTION.md 선례,
recommend-only-after-measuring). 측정 후 이 규칙을 소급 수정하지 않는다.

### 표본 수집 대상

- Firestore `users/*/analyses` **읽기 전용** 순회.
- 대상 doc = `status == 'done'` AND `result.deductionBreakdown.records` 가
  비어있지 않은 배열.
- doc 당 추출 튜플 = (uid, analysisId, mode, referenceMotionId(mode1 만),
  createdAt, fileName, anglesFrames, criterion별 delta).
- criterion별 delta = `unit === 'deg'` 인 record 중 **criterion 정확 일치 첫
  record** 의 `|baselineValue − measuredValue|` (Task 2 `extractCriterionMeasure`
  와 같은 선택 규칙 — 측정과 소비가 같은 record 를 봐야 한다). 비유한값 record
  는 건너뛴다 (fail-closed 미러).
- **PII (T-oe1-01):** bodyProfile·영상 URL·키는 읽지도 출력하지도 않는다
  (Firestore `select()` 필드 마스크로 필요 필드만 fetch). 산출물의 uid 는
  앞 6자 + `…` 절단.

### 노이즈 페어 정의

- **(a) 같은-영상 재분석 페어:** 같은 uid + 같은 fileName(비어있지 않음) +
  같은 anglesFrames + **같은 mode** (mode1 이면 같은 referenceMotionId 까지 —
  baseline 소스가 다르면 delta 비교가 성립하지 않는다). 그룹 내 모든 무순서
  doc 짝. 두 doc 모두 createdAt ≥ 2026-08-09T00:00:00+09:00 (결정론 ON,
  quick-260809-i0q) 이면 `deterministic`, 아니면 `historical` 로 분류.
- **(b) 48h 세션 페어:** 같은 (uid, referenceMotionId) 의 done mode1 분석을
  createdAt 오름차순 정렬 후 **인접 연속 짝** 중 간격 ≤ 48시간인 것.
  세션 내 실력 변화 ≈ 소, 나머지 = 촬영·RTMW·측정창 요동.
- (a) 로 잡힌 짝(같은 analysisId 무순서 짝)은 (b) 에서 제외 — 이중 계상 금지.

### 표본 값

- 각 페어에서 **두 doc 모두에 있는 criterion** 마다
  `|Δdelta| = ||base−meas|_i − |base−meas|_j|` 1건.
- 풀링 = (a)+(b) 전체 표본 합집합.

### 문턱 산출

- `threshold_deg = max(1, ceil(P95(풀링된 |Δdelta| 분포)))`.
- P95 = nearest-rank: 오름차순 정렬 후 index `max(0, ceil(0.95·N) − 1)` 의 값.

### 최소 표본 요건

- **표본을 1건 이상 낸 페어 ≥ 5개.** 미달이면 `threshold_deg: null` 로 박제 —
  수치를 지어내지 않는다. null 이면 Task 2 배선은 캡션 **전면 비활성**
  (fail-closed)으로 나가고, SUMMARY 가 belle 결정 항목으로 올린다.

### 예측 (사전 박제 — 측정 후 자평)

- `deterministic` 분류 (a) 페어의 |Δdelta| ≈ 0 (< 0.5°) 일 것이다 — 08-09
  결정론 ON 이후 같은 영상 재분석은 채점 완전 재현이 실측된 바 있다
  (quick-260809-i0q E2E 2회, 편차 5건 소수점까지 동일).

## 측정 결과

측정 시각: 2026-08-22T08:47:33Z · 실행 = `measure_noise.mjs` (읽기 전용,
select() 필드 마스크 — bodyProfile·영상 URL 미수집, uid 6자 절단)

- 전체 done doc: 972 / deg record 보유 doc (표본 후보): 356
- (a) 같은-영상 페어: 59 (deterministic 1페어 / historical 58페어)
- (b) 48h 세션 페어: 248
- **표본을 낸 페어: 282 (최소 요건 5 충족)** / |Δdelta| 표본: 1017

criterion 별 |Δdelta| 분포 (deg):

| criterion | n | min | median | P95 | max |
|-----------|---|-----|--------|-----|-----|
| angle_vs_reference__left_elbow | 108 | 0.00 | 0.00 | 5.20 | 11.86 |
| angle_vs_reference__left_hip | 100 | 0.00 | 0.00 | 2.17 | 11.30 |
| angle_vs_reference__left_knee | 82 | 0.00 | 0.00 | 5.36 | 8.53 |
| angle_vs_reference__left_shoulder | 201 | 0.00 | 0.00 | 13.94 | 46.92 |
| angle_vs_reference__right_elbow | 138 | 0.00 | 0.00 | 3.43 | 21.02 |
| angle_vs_reference__right_hip | 55 | 0.00 | 0.00 | 0.22 | 6.12 |
| angle_vs_reference__right_knee | 55 | 0.00 | 0.00 | 2.40 | 7.08 |
| angle_vs_reference__right_shoulder | 120 | 0.00 | 0.00 | 4.20 | 24.71 |
| leg_extension | 55 | 0.00 | 0.04 | 61.61 | 61.65 |
| split_angle | 103 | 0.00 | 0.00 | 20.00 | 20.00 |

페어 종류별 풀링 분포 (deg):

| kind | n | min | median | P95 | max |
|------|---|-----|--------|-----|-----|
| deterministic | 5 | 0.00 | 0.00 | 0.00 | 0.00 |
| historical | 106 | 0.00 | 1.06 | 20.31 | 61.65 |
| session48h | 906 | 0.00 | 0.00 | 5.71 | 57.57 |

### 규칙 적용 산출 과정

- 풀링 전체: n=1017, min=0.00, median=0.00, **P95=11.60**, max=61.65
- `threshold_deg = max(1, ceil(11.60)) = 12`
- 페어 요건: 282 ≥ 5 → 유효.

### 예측 대비 실측 자평

- 예측 적중: deterministic (a) 페어(1페어, 표본 5건)의 |Δdelta| = 전부 0.00
  (< 0.5°) — 결정론 ON 재분석은 편차가 완전 재현된다는 예측 그대로.

### 관측 (규칙 소급 수정 없음 — belle 참고용)

- split_angle 의 |Δdelta| 는 0 아니면 20 (vision 측정이 20° 단위 양자화) —
  분포 P95 = 20. 풀링 문턱 12 로는 split 의 한 스텝(20°) 개선이 캡션 대상이
  된다. 이 20° 스텝이 실력 변화인지 측정 양자화 요동인지는 풀링 규칙이 구분
  못 한다 — 사전 박제 규칙(풀링 P95)을 그대로 적용했고, criterion 별 문턱
  전환 여부는 belle 결정 항목으로 SUMMARY 에 올린다.
- leg_extension P95 61.61 은 keypoint 포화 계열 이상치로 보인다 (관측만).

threshold_deg: 12
