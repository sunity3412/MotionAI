# split_angle 플립 교차표 (quick-260824-bxf Task 1)

목적: split_angle 의 20° 스텝이 실력 변화가 아니라 측정 요동(같은 영상이
재분석마다 delta 0 ↔ 20 으로 플립)이라는 근거를 원장 파일로 박제한다.
08-22 세션(quick-260822-oe1)에서 구두 실측만 되고 파일이 없던 건의 원장화 —
문턱값 자체는 이미 커밋된 NOISE-MEASUREMENT.md 의 P95 표에서 유도되며,
이번 재실측 수치로 바꾸지 않는다.

## 판정 규칙 (측정 전 박제)

이 섹션은 **측정 실행 전에 커밋**된다 (measure-first —
`.planning/quick/260822-oe1-progress-caption/NOISE-MEASUREMENT.md` 선례).
측정 후 이 규칙을 소급 수정하지 않는다. 기존 NOISE-MEASUREMENT.md 도
수정하지 않는다 (소급 수정 금지).

### 문턱 일반화 규칙 (belle 2026-08-24 승인)

- `threshold_c = max(전역 12, ceil(P95_c) + 1)` — "split 은 21" 은 숫자 예외가
  아니라 이 규칙의 산출이다.
- 전역 12 와 P95_c 의 출처 = `.planning/quick/260822-oe1-progress-caption/NOISE-MEASUREMENT.md`
  (측정일 2026-08-22, 페어 282 / |Δdelta| 표본 1017 / 풀링 P95 11.60 →
  max(1, ceil) = 12; split_angle 행 n=103, P95=20.00 — 값이 0 아니면 20 인
  20° 양자화).
- 규칙 적용 산출: split_angle → max(12, ceil(20.00) + 1) = **21**.
- **이 문턱값들(기본 12 / split_angle 21)은 이미 커밋된 08-22 P95 표에서
  유도된다. 이번 재실측 수치가 무엇이 나와도 문턱을 바꾸지 않는다** —
  재실측의 목적은 "20° 스텝 = 측정 요동" 근거(같은-영상 플립 교차표)의
  원장화이지 문턱 재산출이 아니다.

### 교차표 정의

- 페어 모집단 = measure_noise.mjs (quick-260822-oe1) 와 **동일한 페어 구성
  규칙**:
  - **(a) 같은-영상 재분석 페어:** 같은 uid + 같은 fileName(비어있지 않음) +
    같은 anglesFrames + 같은 mode (mode1 이면 같은 referenceMotionId 까지).
    그룹 내 모든 무순서 doc 짝. 두 doc 모두 createdAt ≥
    2026-08-09T00:00:00+09:00 (결정론 ON, quick-260809-i0q) 이면
    `deterministic`, 아니면 `historical`.
  - **(b) 48h 세션 페어:** 같은 (uid, referenceMotionId) 의 done mode1 분석을
    createdAt 오름차순 정렬 후 인접 연속 짝 중 간격 ≤ 48시간. (a) 로 잡힌
    짝(같은 analysisId 무순서 짝)은 제외 — 이중 계상 금지.
- 그중 **두 doc 모두 split_angle 의 delta 를 보유**한 페어만 표본. delta =
  `unit === 'deg'` 이고 criterion 정확 일치인 **첫 유효 record** 의
  `|baselineValue − measuredValue|` (비유한값 record 는 건너뜀 — fail-closed
  미러, measure_noise.mjs / Task 2 `extractCriterionMeasure` 와 같은 선택 규칙).

### 산출

- 페어 종류별(same-video historical / same-video deterministic / session48h)
  **(delta_i, delta_j) 값 조합 교차표** — 무순서 조합 (min, max), 값은 소수
  2자리 표기, 조합별 페어 수.
- **플립 비율** = delta_i ≠ delta_j (정확 부등) 인 페어 수 / 해당 종류 전체
  페어 수.
- **split_angle |Δdelta| 분포** = 전체 + 종류별 n / min / median / P95 / max
  (P95 = nearest-rank: 오름차순 정렬 후 index `max(0, ceil(0.95·N) − 1)` —
  measure_noise.mjs 와 동일).

### 예측 (사전 박제 — 측정 후 자평)

08-22 세션 구두 실측 (원장 없음 — 이번 작업의 이유):

- 같은-영상 **historical** 페어 플립 비율 ≈ **36.4% 부근**.
- 같은-영상 **deterministic** 페어 플립 = **0** (결정론 ON 재분석은 채점 완전
  재현 — quick-260809-i0q E2E 실측).
- **48h 세션** 페어 플립 = **0**.

**산출이 예측과 달라도 그대로 박제한다 (수치 조작 금지). 규칙·코드
문턱(12/21)은 그대로 두고, 불일치는 SUMMARY 관측 항목으로 belle 에 보고한다.**

### 관측 노트 (결정 아님)

규칙을 08-22 표의 타 criterion 에 기계 적용하면
left_shoulder(P95 13.94) → 15, leg_extension(P95 61.61 — keypoint 포화
이상치 관측) → 63 이 나온다. 그러나 belle 승인 범위 = "기본 12 + split_angle
21" 이고, 현재 캡션 소비 경로(progressSentence 보유 앵커 =
`ref-kip-up--leg`)의 criterion 은 split_angle 뿐이다 — 타 criterion
오버라이드는 belle 결정 없이 추가하지 않는다 (짜맞추기 방지).

### PII (T-bxf-01) · 쓰기 금지 (T-bxf-02)

- Firestore **읽기 전용** — get / listDocuments 만. set / update / delete 호출 0.
- `select()` 필드 마스크로 mode / status / createdAt / fileName / anglesFrames /
  result.comparison.referenceMotionId / result.deductionBreakdown.records 만
  fetch — bodyProfile·영상 URL·키는 읽지도 출력하지도 않는다. 산출물의 uid 는
  앞 6자 + `…` 절단.
- 실행 = 같은 디렉터리 `measure_split_flip.mjs` (재측정 도구).

## 측정 결과

측정 시각: 2026-08-23T23:47:12.976Z · 실행 = `measure_split_flip.mjs`
(읽기 전용, select() 필드 마스크 — bodyProfile·영상 URL 미수집, uid 6자 절단)

- 전체 done doc: 972
- deg record 보유 doc (페어 모집단): 356
- split_angle delta 보유 doc: 91
- (a) 같은-영상 페어: 59 (deterministic 1 / historical 58)
- (b) 48h 세션 페어: 248
- **두 doc 모두 split_angle 보유 페어 (표본): 103**

### 페어 종류별 (delta_i, delta_j) 값 조합 교차표

**same-video historical** (페어 55):

| delta 조합 (min, max) | 페어 수 | 플립 |
|----------------------|--------|------|
| 30.00 | 30.00 | 20 | - |
| 30.00 | 40.00 | 5 | O |
| 30.00 | 50.00 | 20 | O |
| 40.00 | 50.00 | 4 | O |
| 50.00 | 50.00 | 6 | - |

- 플립 비율: 29/55 = **52.7%**

**same-video deterministic** (페어 0):

- 표본 0

**session48h** (페어 48):

| delta 조합 (min, max) | 페어 수 | 플립 |
|----------------------|--------|------|
| 25.00 | 25.00 | 6 | - |
| 25.00 | 40.00 | 2 | O |
| 30.00 | 30.00 | 18 | - |
| 30.00 | 40.00 | 2 | O |
| 40.00 | 40.00 | 4 | - |
| 40.00 | 50.00 | 2 | O |
| 45.00 | 50.00 | 1 | O |
| 50.00 | 50.00 | 13 | - |

- 플립 비율: 7/48 = **14.6%**

### split_angle |Δdelta| 분포 (deg)

| kind | n | min | median | P95 | max |
|------|---|-----|--------|-----|-----|
| same-video historical | 55 | 0.00 | 10.00 | 20.00 | 20.00 |
| same-video deterministic | 0 | - | - | - | - |
| session48h | 48 | 0.00 | 0.00 | 10.00 | 15.00 |
| 전체 | 103 | 0.00 | 0.00 | 20.00 | 20.00 |

### 예측 대비 자평

예측 3건 중 적중 0건 — historical 플립 52.7% (예측 ≈36.4%), session48h 플립
14.6% (예측 0), deterministic 은 표본 0 이라 검증 불가 (08-22 의 deterministic
1페어는 두 doc 모두 split_angle 보유가 아니었다). 08-22 구두 실측의 수치는
재현되지 않았다 — 원장 없는 구두 수치를 예측으로 세운 대가를 그대로 박제한다
(수치 조작 0, 규칙·문턱 12/21 불변).

### 관측 (규칙 소급 수정 없음 — belle 참고용)

- **전체 |Δdelta| 분포(n=103, median 0.00, P95 20.00, max 20.00)는 08-22
  NOISE-MEASUREMENT.md 의 split_angle 행과 정확히 일치** — 문턱 유도
  `max(12, ceil(20.00)+1) = 21` 의 재료는 재현됐다. 어긋난 것은 플립 비율의
  종류별 배분(구두 수치)뿐이다.
- delta 값 자체는 25/30/40/45/50 — **5° 단위 양자화**다. 08-22 관측 노트의
  "0 아니면 20" 은 delta 가 아니라 |Δdelta| 요약(P95·max)에서 온 과단순화였다.
  같은-영상 최대 요동 = 20° (30↔50) 는 실측으로 성립 — "20° 한 스텝 요동"
  이라는 문턱 21 의 근거는 유지된다.
- session48h 플립 7/48 (14.6%, |Δdelta| 5~15°) — 세션 내 실력 변화와 측정
  요동이 섞인 값(예측이 놓친 축). 전부 문턱 21 미만이라 캡션 오발동 없음.

