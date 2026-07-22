---
slug: ref-student-substrate-gap
status: awaiting_phase
trigger: 기준모션(reference)과 학생 분석이 서로 다른 추출 기질(fps·파이프라인 버전·PR 인버전 보정 여부) 위에서 비교되어 mode1 점수를 신뢰할 수 없다. phase 32-15 PR 보정 production on 후 pdshape fault 58→46 (−12) 이 결함 정확 포착인지 기준모션 비대칭 아티팩트인지 belle 판별 지시에서 출발.
created: 2026-07-22
updated: 2026-07-22
---

# ref-student-substrate-gap

## Symptoms

- **Expected**: mode1 점수는 학생 자세 품질만 반영해야 한다. 기준모션(정은지)과 학생은 동일한 추출 기질 위에서 비교돼야 하고, 추론 경로가 개선되면 점수는 안정적으로 수렴해야 한다.
- **Actual**: 기준모션은 2026-06-12 `phase4_v1` · **18fps** 로 pinned 추출된 좌표, 학생은 오늘 파이프라인 **9fps** + PR 인버전 보정으로 분석된다. 인버전 동작(pdshape·elbow-twist)에서 **학생만 보정되고 기준은 무보정**이라 그 차이가 학생의 "편차"로 계상된다.
- **Error messages**: 없음 (수치 신뢰성 문제 — 크래시·예외 아님)
- **Timeline**: PR 인버전 보정을 production on 한 32-15(2026-07-22)에 표면화. 다만 fps·파이프라인 버전 비대칭은 그 이전부터 존재(기준모션 추출 2026-06-12, phase 27 에서 학생 경로가 9fps Flash extractor 로 전환).
- **Reproduction**: phase25eval fixture 스윕 — `users/phase25eval/analyses/pdshapeFault{runId}` 기준선 `1784676884`(PR off) vs `1784683741`(PR on) 비교. 로컬 재채점 스크립트로 기준모션 각도만 교체하면 재현.

## Evidence (2026-07-22 밤 실측 — 재조사 불필요, 재현 검증 6/6 통과)

- timestamp: 2026-07-22 / **criterion 귀속**: pdshape fault 감점 7건 **전부** `deviationSource=reference_relative`
  (`angle_vs_reference__{joint}`, tol 20°, slope 1.2). 절대(IPSF) 감점 **0건** → 점수가 통째로 기준모션 좌표에 의존.
- timestamp: 2026-07-22 / **기준모션 인버전 실측**: ref-pdshape 역위 프레임 **67.2%**, ref-elbow-twist **50.8%**,
  대조군 ref-power-spin **2.0%**. 검출 임계 15% 를 크게 상회 → 오늘 PR 경로로 재추출하면 보정 대상.
  ref-pdshape 등록 메모: "영상 시작 시점에 이미 인버전 + 회전 상태".
- timestamp: 2026-07-22 / **PR 보정이 기준모션 각도를 움직이는 양**(같은 재추출 경로·env 만 상이):
  pdshape 평균 **4.07°** (left_elbow **+11.0°**), elbow-twist 평균 **2.84°**.
  학생 pdshape left_elbow 편차 증가분 **+8.6°**(24.45→33.02) 와 **같은 자릿수** → −12 의 상당 부분이 기준 미보정 기여.
- timestamp: 2026-07-22 / **★ 근본 비대칭 (PR 이전부터 존재)**: stored ref-pdshape = 237프레임 @ **18fps**,
  오늘 재추출 = 159프레임 @ **9fps**. 같은 학생 영상 점수 stored 58 vs 재추출 67.7 → **stored 재현 불가**.
  ref-elbow-twist 329 @18fps → 220 @9fps 동일 양상.
- timestamp: 2026-07-22 / **대칭 재채점 시도**(기준도 PR on): pdshape fault 47.6→**14.0**(−33.6),
  elbow-twist fault 60.9→**64.4**(+3.5). **동작마다 방향 반대·크기 큼** → "기준모션에 PR 만 적용" 은 해결책이 아님.
- timestamp: 2026-07-22 / **재현 검증**: 운영 기준모션으로 파이프라인 코어(`_deviation_against` = motion_dtw →
  per_joint_deviation) + 감점 산식 재현 시 58.0 / 46.2 / 100 / 98.6 / 66.0 / 65.1 → 실제 doc 점수와 **6/6 일치**.
- timestamp: 2026-07-22 / **선행 세션 연관**: `.planning/debug/keypoint-drift-fps-label.md`(status: fixed) 가
  같은 fps 뿌리를 다룸 — `FfmpegFrameExtractor` 의 `step = max(1, round(src_fps/target_fps))` 정수 양자화로
  **실효 fps ≠ target_fps**. 기준(target 18) 과 학생(target 9→upsample 18) 이 서로 다른 실효 fps 를 갖는다.

## Evidence — 2단계 (2026-07-22 심야, 기질 목록 확정 + shadow 재채점)

- timestamp: 2026-07-22 / **기질 불일치 전체 목록 확정 (코드 실측)** — 아래 `## 기질 불일치 목록` 표.
  핵심: 파이프라인 코드 버전 차이는 **거의 없다**(좌표→각도 수학 동일, git log 검증).
  실질 축은 (M1) target_fps 18 vs 9, (M2) 라벨 fps ≠ 실효 fps (양쪽 다 오라벨·방향 다름),
  (M3) `find_action_segment` 상시 무력화, (M4) window ±2 프레임의 초 단위 비대칭, (M6) PR env.
- timestamp: 2026-07-22 / **재현 검증 6/6 → 20/20 확대**: 5동작(climb 제외) × fault/success × PRoff/PRon
  20 멤버 전부 production `overallScore` 를 full-path `per_joint_deviation` + 감점 산식으로 ±1.5 내 재현.
  → shadow 재채점 방법이 5동작 전수에서 유효. (`substrate_rescore.py`)
- timestamp: 2026-07-22 / **★ M3 실측**: `find_action_segment` 가 `nu <= nr` 이면 학생 클립 통째 반환.
  **12/12 멤버 전부 `nu <= nr`** → mode1 에서 "동작 구간 탐색(준비/대기 제거)" 1단계가 **한 번도 발동한 적 없다**.
  기준이 학생보다 1.5배 조밀하기 때문 (초 길이는 학생이 더 긴 경우도 `nu < nr`).
- timestamp: 2026-07-22 / **★ M2 실효 fps 확정**: 기준 실효 = 15.0fps (라벨 18.0 = +20% 오라벨).
  근거 3중 — ①ref-elbow-twist 329프레임/15.0 = 21.93s ≈ `clipRange.landEndS` 21.9
  ②선행 세션 실측 ref-climb 257프레임 / ffprobe 17.078s = **15.05fps**
  ③재추출 프레임비 237/159 = 1.491 ≈ step9/step18 = 3/2 (src 30fps).
  학생 실효 = 10.0fps (라벨 9.0 = −10% 오라벨). **밀도비 = 10/15 = 0.667**.
- timestamp: 2026-07-22 / **★ 위양성 여유 실측** (= tol 20° − max 관절편차, success 멤버):
  kip-up **+15.8°** · peter-pan **+10.5°** · power-spin **+9.0°** ‖ elbow-twist **+0.2°** · pdshape **−1.2°**.
  → 인버전 2동작의 success 는 이미 tol 경계에 붙어 있고 pdshape 는 **이미 위양성 감점이 발동 중**(99점).
  비인버전 3동작의 편차 바닥(2.7~7.3°)과 인버전 2동작(14.8~18.0°)이 **3배 차이** — 기질 아티팩트의 정량 지표.
- timestamp: 2026-07-22 / **pdshape 불안정성 원인 규명**: 결측 0%·DTW path 정상(uniqU=전 프레임) →
  H1(결측)·H2(정렬 붕괴) 기각. 실제 원인 = **7개 관절이 전부 20~33° 구간(tol 20° 경계)에 몰려 있어**
  기질을 미세 조정하면 관절들이 dead-zone 을 동시에 넘나든다. 밀도비 스윕 r=1.00→0.50 에서
  pdshape fault 46→57→27→45→34 로 **±30점 요동**. 다른 4동작은 ±5점 내.
- timestamp: 2026-07-22 / **정규화 방향 대칭성 검사**: 기준 다운샘플 vs 학생 업샘플 결과 차이 —
  power-spin 1.3 / peter-pan 0.7 / elbow-twist 1.1 / kip-up 0.0 ‖ **pdshape 11.7**.
  → 밀도 정규화는 4동작에서 well-posed, pdshape 에서만 방향 의존.
- timestamp: 2026-07-22 / **shadow 재채점 3안 비교** (PR on 학생 기준, 산출물 `substrate_rescore.json` /
  `substrate_sensitivity.json`) — 아래 `## 옵션별 실측` 표.

## Evidence — 3단계 (2026-07-22, belle 방향 결정 후 · reference 11종 전수 계측)

- timestamp: 2026-07-22 / **★ M8 신규 발견 — reference 라이브러리 내부 좌표축 레이아웃이 2갈래**.
  11 doc 전부 `space='pole_aligned'` · `coordDim=3` 인데 **패딩 축이 서로 다르다**:
  · 원본 5 (`anglesBackbone=rtmw-x-384-bukuroo-2026-06-06`): axis1 ≡ 0 → 레이아웃 **(x, 0, y)**, 수직 = axis2
  · 후속 6 (`anglesExtractedBy=rtmw-x-384-direct-2026-06-12`): axis2 ≡ 0 → 레이아웃 **(x, y, 0)**, 수직 = axis1
  즉 reference 라이브러리는 **추출 계보 2종**(bukuroo 06-06 / direct 06-12)이 한 컬렉션에 공존한다.
  → 이것이 phase 31 앱 `pickVerticalAxis` 가 존재하는 이유(소비 측에서 이미 흡수 중).
  채점 입력은 `angles` 라 **현행 점수에는 직접 영향 없음**. 단 joints3d 소비 경로
  (오버레이·fault zoom crop·keypointReport)는 축 분기에 의존한다 → C 재처리 시 11종이
  단일 레이아웃으로 수렴하므로 **소비 측 회귀 검증 필요**(아래 성공 판정 4항).
  (`ref_axis_probe.py`)
- timestamp: 2026-07-22 / **★ 이전 역위비율 측정의 적용 범위 정정**. `asym_analysis.py` 는
  `joints3d[:, :2]` 를 고정 사용 — 후속 6 에는 맞고 **원본 5 에는 (x, 0) 이 되어 margin 이 항상 0**.
  v1 전수 계측이 원본 5 를 전부 "0.0%" 로 낸 것은 **축 아티팩트**였다. v2(`ref_inversion_survey2.py`)
  는 doc 별로 항등 0 축을 패딩으로 판정해 남은 두 축을 (수평, 수직)으로 쓴다.
  검증 3중: ①기측정 3종(pdshape 67.2 / elbow-twist 50.8 / power-spin 2.0) **소수 3자리까지 재현**
  ②y-down 규약이 정상 동작 5종을 전부 비검출로 분류(y-up 규약은 climb 를 96.9% 역위로 판정 → 기각)
  ③`ref-invert` 28.0% / run 13 이 `inversion_warp` docstring 의 spike 실측 **invert 0.289 / run 18**
  과 독립적으로 일치.
- timestamp: 2026-07-22 / **★ 인버전 전수 결과 — PR 영향 기준모션이 2종이 아니라 6종**.
  `detect_inversion` AND 조건(ratio ≥ 0.15 AND longest_run ≥ 5) 프록시 적용 시 **11종 중 6종 검출**:
  pdshape 67.2% · foxtop-split 57.4% · foxtop 56.5% · elbow-twist-sister 50.8% · combo 32.0% · invert 28.0%.
  기존에 알던 2종(pdshape·elbow-twist) 외에 **foxtop · foxtop-split · combo · invert 4종이 추가**.
  → M6(기준 무보정) 노출 면적이 알려진 것의 3배. 전수 표는 아래 `## 재처리 위험도 표`.
- timestamp: 2026-07-22 / **프록시 한계 명시**: `detect_inversion` 의 실제 입력은 1차 추론
  **픽셀 (x,y) + per-keypoint score** 다. 위 계측은 저장된 `pole_aligned` joints3d(신뢰도 없음,
  폴 수직 정렬 회전이 이미 적용됨)를 쓴 **프록시**다. 확정 판정은 재추출 시 `detect_inversion`
  로그로만 가능 → 재처리 Task 에 로그 수집을 필수 항목으로 넣었다.
  또한 `INVERSION_MIN_RUN=5` 는 9fps 캘리브레이션값인데 위 run 수치는 15fps 실효 기준이라
  프레임 수가 ~1.5배 부풀어 있다. 9fps 환산해도 검출 6종은 최소 run 8.7 (invert) 로 임계 5 를
  상회 → **결론은 fps 환산에 강건**.
- timestamp: 2026-07-22 / **M3 수정 파급 실측**: `motion_dtw` 프로덕션 호출부는 **3곳** —
  `pipeline/app.py:1770`(mode1 채점 본류), `pipeline/app.py:4015`, `analysis/safety_flags.py:245`.
  `find_action_segment` 를 고치면 **safety_flags 의 정렬도 함께 바뀐다**(safety_flags 는 의도적으로
  같은 motion_dtw 를 재계산 — D-07). → M3 수정은 채점뿐 아니라 **안전 플래그 회귀 검증 동반 필수**.
- timestamp: 2026-07-22 / **백업 규모 실측**: reference 11 doc 전량 JSON 직렬화 = **7,751,098 B (7.4 MiB)**.
  최대 ref-combo 1.62 MiB, 최소 ref-kip-up 0.25 MiB. 단일 파일 백업으로 충분(청크 불요).
  11종 전부 `isActive=True` · `activeVersion=pipelineVersion='phase4_v1'` · `keypointReport.fps=18.0` ·
  `anglesFrames == joints3dFrames == keypointReport.frames` (11/11 일치).

## 기질 불일치 목록 (코드 확정)

| # | 축 | 기준모션 | 학생 | 채점 영향 |
|---|---|---|---|---|
| M1 | target_fps | **18.0** (`reprocess_reference_motions_phase4.py:428` default) | **9.0** (`FfmpegFrameExtractor.__init__` default = `_pipeline_frame_fps()` 단일 출처) | 시퀀스 밀도 1.5배 |
| M2 | 실효 fps vs 라벨 | 실효 **15.0** / 라벨 **18.0** (+20%) | 실효 **10.0** / 라벨 **9.0** (−10%) | `step=max(1,round(src/target))` 정수 양자화. 채점은 라벨 미사용(길이만) — 라벨 오차는 표시 경로 |
| M3 | `find_action_segment` | — | — | `nu<=nr` → 학생 클립 통째. **12/12 멤버 무력화**. 준비/대기 프레임이 편차에 상시 포함 |
| M4 | window median 창 | `window=2` 프레임 = **0.133s** | `window=2` 프레임 = **0.200s** | `features.window_median_angle_deltas` 가 양쪽에 같은 *프레임* 수 적용 → 초 단위 비대칭. fault 멤버에 windowMedianAngleDeltas 존재(잠재 활성) |
| M5 | 파이프라인 코드 | `phase4_v1` @2026-06-12 | HEAD | **좌표→각도 수학 동일** — `pose_frame.py`/`temporal.py`/`skeleton.py`/`body_normalization_measurer.py` 커밋 0, `features.py` 는 가산만(`joint_angles`·`feature_vector` 무변경), 양쪽 다 `RTMWPoseEngine` |
| M6 | `PR_INVERSION_ENABLED` | **off** (당시 미존재) | **on** (32-15 production) | 인버전 동작에서 학생만 좌표 보정 |
| M7 | `RTMW_DETERMINISTIC` | 미존재 | eval=1 | 재현성 축 (점수 편향 아님) |
| M8 | joints3d 축 레이아웃 | **2갈래**: 원본 5 = (x,0,y) 수직 axis2 / 후속 6 = (x,y,0) 수직 axis1 | (x,y,0) 단일 | **채점 무관**(채점 입력은 `angles`). joints3d 소비 경로(오버레이·fault zoom·keypointReport)만 영향 — 앱 `pickVerticalAxis` 가 이미 흡수 중. C 재처리 시 단일 레이아웃 수렴 → 소비 측 회귀 검증 대상 |

## 옵션별 실측 (PR on 학생 · 5동작 · shadow · Firestore write 0)

| 동작 | A 현행 fault/success | B 밀도정규화 fault/success | C 기준 PRon 재추출 fault/success |
|---|---|---|---|
| power-spin | 55 / 100 (여유 +9.0°) | 55.6 / 100 (+4.7°) | 미측정 (PR 미검출 → M1만 작동) |
| peter-pan | 79 / 100 (+10.5°) | 74.0 / 100 (+7.6°) | 미측정 (동상) |
| elbow-twist | 65 / 100 (**+0.2°**) | 61.5 / 100 (**−0.5°**) | 64.4 / 100 (**+0.3°**) |
| pdshape | 46 / 99 (**−1.2°**) | 57.2 / 100 (+0.1°) | 21.8 / 100 (**+4.5°**) |
| kip-up | 80 / 100 (+15.8°) | 80.0 / 100 (+14.4°) | 미측정 (동상) |

주: 괄호 = success 위양성 여유(tol 20° − max 편차). 점수는 production record 집합을 고정한 채
`angle_vs_reference__*` 항목만 재산출한 값 — **shadow 방법은 신규 record 를 만들 수 없다**(vision-pointed
게이트 재현 불가). 그래서 B 의 elbow-twist success 는 여유가 −0.5° 인데도 100 으로 표시된다 —
**점수보다 여유 수치가 정직한 지표.**

## Eliminated

- hypothesis: "pdshape 58→46 은 순수하게 결함을 정확히 포착한 결과" — **기각(단독 원인 아님)**.
  기준모션 무보정 기여가 같은 자릿수(+11.0° vs +8.6°)로 실재. 밀도만 맞춰도 57.2 로 되돌아온다.
- hypothesis: "기준모션에 PR 보정만 적용하면 대칭이 회복된다" — **부분 정정**.
  초안의 "대칭 조건 14.0 · 동작별 방향 반대" 는 8관절 나이브 재채점의 산물. production record 집합을
  고정한 충실 재채점으로는 pdshape fault **21.8** / success **100** (여유 −1.2°→**+4.5°**),
  elbow-twist fault 64.4 / success 100 (여유 +0.2°→+0.3°) — **방향은 반대가 아니라 일관되게
  "success 여유 증가 + fault 분리 확대"**. 다만 elbow-twist 여유는 여전히 +0.3° 로 위태롭다.
- hypothesis: "기준모션이 준비 구간을 포함해 편차가 부풀려진다 — `clipRange.execStartS~landEndS` 로
  자르면 해소" — **기각(역효과)**. 기준만 자르면 학생 준비 구간이 정렬할 곳을 잃어 여유가 악화:
  pdshape success −1.2°→**−14.5°**, elbow-twist success +0.2°→**−3.5°**, kip-up fault +1.0°→−10.6°.
  M3(segment 탐색 무력화)를 함께 풀지 않는 한 단독 적용 금지.
- hypothesis: "pdshape 요동은 결측/DTW 정렬 붕괴 탓" — **기각**. 결측 0%, DTW path uniqU = 전 프레임.
  실제 원인은 7개 관절이 tol 20° 경계(20~33°)에 밀집한 구조.

## Current Focus

status: **awaiting_phase** — 조사 종결. 이 세션의 산출물은 코드 수정이 아니라 아래 인계 문서다.

decision (belle, 2026-07-22): **C + M3 동시 해소**. belle 원문 "제대로 고치자".
A(현상 유지)·B(비교 시점 밀도 정규화) 모두 기각. 근거는 `## Resolution` 참조.

next_action: **신규 phase 착수** (`/gsd-plan-phase`). 착수 시점은 belle 이 TestFlight 1.1.0 UAT
를 마친 뒤 별도로 정한다. 이 debug 세션에서는 더 이상 실행하지 않는다.
이 파일의 `## 인계 — C+M3 실행 계획` 이 그대로 phase 의 SEED 다.

---

## Resolution

### root_cause (확정)

**mode1 점수는 학생 자세 품질이 아니라 기준↔학생 추출 기질 차이에 지배되고 있다.**

pdshape fault 감점 7건이 **전부** `deviationSource=reference_relative` — 절대(IPSF) 감점 0건.
즉 점수가 통째로 기준모션 좌표에 의존하는 구조인데, 그 기준모션이 학생과 다른 기질 위에 있다.

**실제 인과 축 (M1·M2·M3·M6) 과 각각의 채점 영향:**

| 축 | 인과 여부 | 채점 영향 (실측) |
|---|---|---|
| **M1** target_fps 18 vs 9 | **인과 (주축)** | 시퀀스 밀도 1.5배 차 → M3 를 상시 발동시키는 원인. **밀도만 맞춰도 pdshape fault 46 → 57.2** (−12 하락분의 대부분이 여기서 복원) |
| **M2** 실효 fps ≠ 라벨 (기준 15.0/라벨 18.0, 학생 10.0/라벨 9.0) | **인과 (M1 의 실제 크기 결정)** | 실효 밀도비 = 10/15 = **0.667**. 라벨은 채점에 미사용(길이만) → 라벨 오차 자체는 표시 경로 문제. 단 **M1 의 진짜 배율이 2.0 이 아니라 1.5** 임을 확정 |
| **M3** `find_action_segment` 무력화 | **인과 (독립 축)** | `nu <= nr` 분기로 **12/12 멤버 전부** 학생 클립 통째 사용 → "준비/대기 제거" 1단계가 mode1 에서 **한 번도 발동한 적 없음**. 준비 프레임이 편차에 상시 포함. M1 해소만으로는 안 풀림 — 밀도를 맞추면 오히려 `nu ≈ nr` 이라 여전히 경계 |
| **M6** `PR_INVERSION_ENABLED` 기준 off / 학생 on | **인과 (인버전 동작 한정)** | PR 보정이 기준 각도를 움직이는 양 pdshape 평균 **4.07°**(left_elbow **+11.0°**), elbow-twist 2.84°. 학생 pdshape left_elbow 편차 증가분 **+8.6°** 과 **같은 자릿수** → −12 의 상당 부분이 기준 무보정 기여. **전수 계측 결과 노출 기준모션은 2종이 아니라 6종** |
| **M4** window median 창 (0.133s vs 0.200s) | **잠재 (현재 비활성)** | fault 멤버에 `windowMedianAngleDeltas` 존재하나 현행 감점 경로 미소비. M1 해소 시 자동 정렬됨 |
| **M5** 파이프라인 코드 버전 | **인과 아님 (기각)** | 좌표→각도 수학 동일. `pose_frame.py`/`temporal.py`/`skeleton.py`/`body_normalization_measurer.py` 커밋 0, 양쪽 다 `RTMWPoseEngine`. **당초 의심축이었으나 실측으로 소거** |
| **M7** `RTMW_DETERMINISTIC` | **인과 아님** | 재현성 축, 점수 편향 아님 |
| **M8** joints3d 축 레이아웃 2갈래 | **채점 인과 아님 / 신규 발견** | 채점 입력은 `angles` 라 무관. joints3d 소비 경로(오버레이·fault zoom·keypointReport)만 영향 |

**귀결 (기질 아티팩트의 정량 지표):**
비인버전 3동작의 편차 바닥 2.7~7.3° vs 인버전 2동작 14.8~18.0° — **3배**.
tol 20° 대비 success 위양성 여유가 pdshape **−1.2°**(이미 위양성 감점 발동, 99점),
elbow-twist **+0.2°**(경계에 붙음). 그 결과 pdshape 는 밀도비를 미세 조정하는 것만으로
fault 점수가 **±30점 요동**한다(감점 7관절이 전부 20~33° 의 tol 경계에 밀집).

### 기각된 대안과 근거

**A (현상 유지) 기각** — belle 원문 "제대로 고치자".
- pdshape success 는 **이미** 위양성 감점이 발동 중(99점, −1.4). 방치하면 자세가 완벽한
  엘리트 영상이 계속 감점된다.
- pdshape fault 46 을 "결함 정확 포착"으로 서술할 수 없다(§6 실측: −12 의 대부분이 기질).
  즉 A 는 **틀린 숫자를 옳다고 부르는 선택**이다.
- pdshape ±30점 요동이 남는다 → 점수 신뢰성(Core Value)과 정면 충돌.

**B (비교 시점 밀도 정규화) 기각** — 증상만 덮고 같은 자리로 돌아온다.
- **elbow-twist success 여유가 +0.2° → −0.5° 로 악화**(양수→음수, 위양성 감점 진입).
  pdshape 를 살리려고 elbow-twist 를 죽이는 교환이다.
- **M6(기준 무보정)가 그대로 잔존** — 인버전 기준모션 6종이 계속 무보정 좌표로 비교된다.
  밀도를 맞춰도 PR 비대칭은 남으므로, 다음 PR 관련 변경 때 **같은 조사를 처음부터 다시** 하게 된다.
- 밀도 정규화는 pdshape 에서만 **방향 의존**(기준 다운샘플 vs 학생 업샘플 차 11.7 —
  다른 4동작은 0.0~1.3). well-posed 하지 않은 연산을 채점 본류에 넣는 셈.
- B 는 M3 도 풀지 못한다(`nu ≈ nr` 경계로 옮길 뿐).

**C 단독(M3 미해소) 도 불가** — 이미 실측으로 기각된 항목과 같은 뿌리.
기준만 `clipRange.execStartS~landEndS` 로 자르면 학생 준비 구간이 정렬할 곳을 잃어
pdshape success −1.2° → **−14.5°** 로 급악화. **C 는 반드시 M3 와 함께 간다.**

### fix

**미적용.** 이 세션은 문서화 전용(operator `goal: document_and_close`).
코드 변경 0 · Firestore write 0 · Pod 무접촉 · 임계값 재fit 0.
실행 계획은 아래 `## 인계 — C+M3 실행 계획`, 착수는 별도 phase.

### verification

조사 자체의 검증은 완료:
- 재현 검증 **20/20** — 5동작 × fault/success × PRoff/PRon 전 멤버의 production `overallScore`
  를 full-path `per_joint_deviation` + 감점 산식으로 ±1.5 내 재현.
- 역위 계측 v2 는 기측정 3종을 소수 3자리까지 재현 + `ref-invert` 가 spike 독립 실측
  (0.289/run18)과 일치 → 계측 방법 자체가 교차 검증됨.

### files_changed

- `.planning/debug/ref-student-substrate-gap.md` (본 파일 — 인계 문서)
- `.planning/phases/32-result-readability-3-omni/32-15-ASYMMETRY-CHECK.md` (11종 전수 표 + M8 정정 반영)

---

## 재처리 위험도 표 (reference 11종 전수 · Firestore joints3d 프록시 계측)

계측: `ref_inversion_survey2.py` (읽기 전용, Pod 미사용).
판정 = `inversion_warp.detect_inversion` 과 동일 AND 조건 (ratio ≥ 0.15 **AND** longest_run ≥ 5).

| # | motion | 계보 | frames | 역위비율 | 최장 run | 검출(>15%+run≥5) | 사전 측정 상태 | 예상 재처리 영향 | 위험도 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **ref-pdshape** | direct 06-12 | 237 | **67.2%** | 30 | **YES** | 기측정 | PR 보정 + 밀도 → 각도 평균 4.07° 이동(left_elbow +11.0°). success 여유 −1.2°→+4.5° 개선, fault 46→21.8 | **높음** (±30점 요동 이력) |
| 2 | **ref-foxtop-split** | bukuroo 06-06 | 485 | **57.4%** | 44 | **YES** | **미측정** | PR 신규 발동. fixture 없음 → 채점 영향 **미지** | **높음** (미측정 + 최장 클립군) |
| 3 | **ref-foxtop** | bukuroo 06-06 | 426 | **56.5%** | 34 | **YES** | **미측정** | PR 신규 발동. fixture 없음 → 채점 영향 **미지** | **높음** (미측정) |
| 4 | **ref-elbow-twist-sister** | direct 06-12 | 329 | **50.8%** | 19 | **YES** | 기측정 | PR 평균 2.84° 이동. success 여유 +0.2°→+0.3° — **개선폭이 거의 없음** | **높음** (여유 위태, §elbow-twist 처방 경로) |
| 5 | **ref-combo** | direct 06-12 | 931 | **32.0%** | 28 | **YES** | **미측정** | PR 신규 발동. **최장 클립(931f)** + RTMW 비결정성 이력 보유(백필 gate 가 23.43°→0.193° 요동 경험) | **높음** (미측정 + 재현성 이력) |
| 6 | **ref-invert** | bukuroo 06-06 | 260 | **28.0%** | 13 | **YES** | **미측정** | PR 신규 발동. spike 006 에서 invert 계열 boneCV 1.16→0.489(−58%) 개선 실측 → **개선 기대 근거 있음** | 중 (미측정이나 spike 선례 존재) |
| 7 | ref-peter-pan | direct 06-12 | 130 | 4.6% | 1 | no | 기측정(fixture) | PR 미발동. M1 밀도만 변화 | 낮음 |
| 8 | ref-power-spin | direct 06-12 | 159 | 2.0% | 1 | no | 기측정(fixture) | PR 미발동. spike 실측상 power-spin 은 **PR 적용 시 오히려 파괴**(1.03→7.0) — 미검출 유지가 정답 | 낮음 (단 오검출 시 치명 → run 조건 확인 필수) |
| 9 | ref-climb | bukuroo 06-06 | 257 | 2.7% | 2 | no | **미측정** | PR 미발동. M1 밀도만 변화. mode1 comparison gate 전용(점수 없음) | 낮음 |
| 10 | ref-sideway-spin | bukuroo 06-06 | 298 | 0.7% | 1 | no | **미측정** | PR 미발동. M1 밀도만 변화 | 낮음 |
| 11 | ref-kip-up | direct 06-12 | 118 | 0.9% | 1 | no | 기측정(fixture) | PR 미발동. 현행 여유 +15.8° 로 가장 안전 | 낮음 |

**요약**
- **미측정 6종 = ref-climb · ref-foxtop · ref-foxtop-split · ref-invert · ref-sideway-spin · ref-combo.**
  이번에 전부 계측 완료. 그중 **4종(foxtop · foxtop-split · invert · combo)이 인버전 검출 양성**.
- **PR 영향 기준모션 = 11종 중 6종** (기존 인지 2종의 3배). M6 노출 면적이 예상보다 훨씬 넓다.
- **fixture 미보유 4종(foxtop · foxtop-split · invert · combo · climb 중 climb 제외)** 은
  재처리 후 채점 영향을 **회귀 테스트로 검증할 수단이 현재 없다** → 아래 R-3 위험 참조.

### 미측정 위험 (재처리 착수 전 반드시 인지할 것)

- **R-1 프록시 한계**: 위 역위비율은 저장된 `pole_aligned` joints3d 기반이다. `detect_inversion`
  의 실제 입력은 1차 추론 **픽셀 (x,y) + score**. pole_aligned 는 폴 수직 정렬 회전이 이미
  적용된 좌표라 픽셀 공간과 margin 이 다를 수 있다. → **재추출 시 `detect_inversion` 로그를
  반드시 수집**해 이 표와 대조(Task 1 산출물).
- **R-2 run 임계의 fps 의존**: `INVERSION_MIN_RUN=5` 는 9fps 캘리브레이션. 위 run 은 15fps 실효
  기준이라 ~1.5배 부풀어 있다. 9fps 환산 최소값은 invert 8.7 로 임계 상회 → 결론은 강건하나,
  **경계 동작(power-spin run 1, peter-pan run 1)이 재추출에서 run 5 를 넘지 않는지 확인 필요**.
  power-spin 이 오검출되면 spike 실측대로 추적이 파괴된다(boneCV 1.03 → 7.0).
- **R-3 검증 수단 부재**: foxtop · foxtop-split · invert · combo 는 phase25eval **fixture 가 없다**.
  재처리 후 채점 회귀를 정량 확인할 수 없다. → 재처리 전에 이 4종에 대한 fixture(정은지
  success 영상 최소 1개씩)를 확보하거나, **self-comparison 검증**(기준 영상 자체를 학생으로
  투입 → 만점 근처 기대, `verify_self_comparison.py` 기보유)으로 대체할 것.
- **R-4 ref-combo 재현성**: 백필 gate 이력상 ref-combo 는 동일 영상·동일 코드에서 실행 간
  23.43° → 0.193° 편차를 낸 전례가 있다(단일 프레임 L/R swap 류). 931 프레임 최장 클립.
  → **재처리는 `RTMW_DETERMINISTIC=1` 로 실행하고 2회 반복해 편차를 기록**할 것.
- **R-5 M8 소비 측 회귀**: 재처리하면 원본 5종의 축 레이아웃이 (x,0,y) → (x,y,0) 으로 바뀐다.
  앱 `pickVerticalAxis` 가 흡수하도록 설계돼 있으나 **실기기 확인 없이는 단정 금지**
  ([[verify-ui-on-simulator-before-ota]]). 오버레이·fault zoom crop 을 원본 5종에 대해 육안 확인.
- **R-6 pdshape dead-zone**: 감점 7관절이 tol 20° 경계(20~33°)에 밀집한 구조는 재처리로
  완화될 뿐 **소멸하지 않는다**. 재처리 후에도 pdshape 는 기질 미세 변화에 민감할 수 있다.
  → 성공 판정은 "점수 값"이 아니라 **"여유(margin) 부호와 크기"** 로 볼 것.

---

## 인계 — C+M3 실행 계획

> 이 절이 신규 phase 의 SEED 다. 순서를 지킬 것 — 각 Task 는 앞 Task 의 산출물을 전제한다.

### Task 0 — 백업 (착수 전 필수 · 무조건 선행)

아래 `## 롤백 설계` 전량 실행. 백업 JSON 이 없으면 **어떤 write 도 금지**.

### Task 1 — 기준모션 11종 재추출 (Pod 필요)

- 실행: `backend/scripts/reprocess_reference_motions_phase4.py`
  - `--motions` 에 **11종 전부 명시** (default 5-subset 금지 — [[reference-library-phase4-all11]])
  - `--target-fps 9.0` ← **M1 해소의 핵심.** 기존 default 18.0 을 학생 경로
    (`FfmpegFrameExtractor` = `_pipeline_frame_fps()`)와 일치시킨다
  - `--no-flip` 로 **먼저 버전만 쓰고 active 포인터는 flip 하지 않는다** (단계적 배포)
  - env: `PR_INVERSION_ENABLED=1` (M6 해소), `RTMW_DETERMINISTIC=1` (R-4)
- **산출물로 `detect_inversion` 로그를 반드시 수집** — 위 위험도 표와 대조 (R-1 해소).
- 2회 반복 실행해 ref-combo 편차 기록 (R-4).
- **주의**: `--target-fps` 변경은 `REFERENCE_TARGET_FPS = 18.0`(backfill 상수)과
  stored-vs-rerun angle gate 의 frame-count 정합 전제를 깨뜨린다 → Task 2 에서 함께 조정.

### Task 2 — 다운스트림 백필 (Task 1 산출 angles 를 source 로)

Task 1 이 `angles`/`joints3d` 를 바꾸면 **거기서 파생된 필드가 전부 stale** 이 된다.
백필 대상 (전부 새 angles 기준으로 재산출):

| 필드 | 산출 스크립트 | source | 비고 |
|---|---|---|---|
| `meanAngles` | `backfill_reference_downstream.py` | **새** stored angles 의 nanmean | 재추론 X |
| `techniqueProfile` | 동상 | `FallbackRecognizer().recognize(새 angles)` | 재추론 X |
| `bodyNormalizationProfile` | 동상 | `measure_body_profile(live pose_frames)` | 재추론 필요 |
| `forceDirectionPattern` | 동상 | `infer_force_direction_pattern(force_signals(live frames))` | 재추론 필요 |
| `keypointReport` | `extract_reference_keypoint_reports.py` | 새 frames/fps | **fps 라벨 9.0 으로 갱신** — 현행 11/11 이 18.0 |
| `referenceKeypointReport` | 동상 | 동상 | mode1 소비 경로 |
| `bodyComparisonSourcePose` | 재확인 필요 | 새 pose | 11 doc 전부 보유 — 누락 시 비교 화면 깨짐 |

- **`REFERENCE_TARGET_FPS = 18.0`(backfill_reference_downstream.py) 을 9.0 으로 동반 수정**해야
  stored-vs-rerun angle gate 가 frame-count mismatch 로 abort 하지 않는다.
- `REFERENCE_V1_FORCE_CONFIG`(pinned) 는 **유지** — 이번 변경 축이 아니다
  ([[reference-v1-pinned-force-config]]).
- gate 임계 `MEAN_EPSILON_DEG=0.1` / `P99_EPSILON_DEG=1.0` **재fit 금지**.
  gate 가 걸리면 임계를 올리지 말고 원인을 조사할 것.

### Task 3 — M3 수정 (`find_action_segment`)

`motiondtw.py:83` `if nu <= nr: return 0, nu` 가 12/12 무력화의 원인.
Task 1 로 밀도가 맞으면 `nu ≈ nr` 이 되어 **여전히 경계에 걸린다** → 별도 수정 필요.

- 수정 방향(구현은 phase 에서 결정): `nu < nr` 일 때도 **기준 쪽을 학생 길이에 맞춰 창을
  잡거나**, 짧은 쪽 기준으로 양방향 슬라이딩. 어느 쪽이든 "준비/대기 제거" 1단계가
  실제로 발동해야 한다.
- **파급 3곳** — `pipeline/app.py:1770`(mode1 채점 본류), `pipeline/app.py:4015`,
  `analysis/safety_flags.py:245`. safety_flags 는 의도적으로 같은 `motion_dtw` 를 재계산하므로
  (D-07) **안전 플래그 회귀 검증이 동반 필수**.
- 기존 테스트 `backend/tests/test_motiondtw.py:39,45` 가 현행 동작을 고정하고 있다 → 함께 갱신.
- **선행 조건**: Task 1·2 완료 후. M3 를 먼저 고치면 기준이 여전히 1.5배 조밀해
  다른 국면으로 이동할 뿐이다.

### Task 4 — 전수 재검증

- **6동작 fixture 동일 빈도** — kip-up 편중 금지 ([[verify-all-fixtures-not-kipup-only]]).
- **eval 은 SERIAL** — 파이프라인 동시 호출은 오염 ([[pipeline-not-concurrency-safe-eval-serial]]).
- fixture 미보유 4종(foxtop·foxtop-split·invert·combo)은 **self-comparison**
  (`verify_self_comparison.py`)으로 대체 검증 (R-3).
- 원본 5종 오버레이·fault zoom 실기기 육안 확인 (R-5, M8 레이아웃 전환).
- 판정은 아래 `## 성공 판정 기준` 전항 충족.

### Task 5 — active 포인터 flip + 앱 배포

- Task 4 전항 PASS 후에만 `--no-flip` 해제 / flip 스크립트 실행.
- 롤백 경로(`rollback_reference_motions_phase4.py` 기보유 + Task 0 백업) 대기 상태 유지.

---

## 롤백 설계

### 백업 (Task 0 — 어떤 write 보다 먼저)

- **대상**: `reference/{id}` 11 doc **전량**(top-level 전 필드, 부분 백업 금지).
  실측 규모 = 7,751,098 B (**7.4 MiB**) — 단일 파일로 충분.
- **경로**: `.planning/debug/backups/reference-11-preC-{YYYYMMDD-HHMMSS}.json`
  (git 커밋 금지 — 7.4 MiB 바이너리성 데이터. `.gitignore` 확인 후 **로컬 + S3 이중 보관**:
  `s3://sunity-motion-pilot-videos/backups/reference-11-preC-{ts}.json`)
- **백업 명령** (읽기 전용, 신규 스크립트 1개 — phase 에서 작성):

```bash
cd backend && PYTHONPATH=shared/python:. FIREBASE_SA_PATH=../firebase-sa.json \
  python3 scripts/backup_reference_docs.py \
    --motions ref-climb ref-foxtop ref-foxtop-split ref-invert ref-sideway-spin \
              ref-combo ref-elbow-twist-sister ref-kip-up ref-pdshape \
              ref-peter-pan ref-power-spin \
    --out ../.planning/debug/backups/reference-11-preC-$(date +%Y%m%d-%H%M%S).json
```

- **백업 무결성 게이트** (복원 가능성을 백업 시점에 증명):
  1. 11/11 doc 존재 · `isActive=True` · `activeVersion='phase4_v1'`
  2. doc 별 `anglesFrames == joints3dFrames == keypointReport.frames` (현행 11/11 일치 확인됨)
  3. `angles`/`joints3d` 배열 길이 = `frames × len(keys) × dim` 정합
  4. 전 doc SHA-256 해시를 백업 파일 헤더에 기록
  → 하나라도 실패하면 **재처리 착수 금지**.

### 복원 절차

1. **즉시 차단**: `PR_INVERSION_ENABLED=0` 으로 Pod env 되돌리고 서버 재기동 —
   신규 분석이 새 기준을 소비하지 않게 한다.
2. **active 포인터 우선 복구**: `backend/scripts/rollback_reference_motions_phase4.py` 로
   `activeVersion` 을 `phase4_v1` 로 되돌린다. 버전드 문서가 남아 있으면 이것만으로 복구된다.
3. **top-level mirror 복구**: 2 로 부족하면(= 재처리가 top-level 을 덮어썼으면) 백업 JSON 에서
   doc 별 전 필드를 `set(merge=False)` 로 **통째 복원**. 부분 `update` 금지 —
   재처리가 추가한 신규 필드가 남아 혼종 상태가 된다.
4. **검증**: 복원 직후 `backend/scripts/measure_reference_fps.py` 재실행 →
   11/11 `fps=18.0` · `anglesFrames == keypointReport.frames` 복귀 확인.
5. **채점 재현 확인**: phase25eval fixture 1종(pdshape) 재분석 → 백업 시점 점수(fault 46 / success 99)
   재현되면 복원 완료.
6. **M3 코드 롤백**: Task 3 커밋 `git revert` (코드는 독립 롤백 가능 — 데이터와 분리).

### 롤백 트리거 (하나라도 해당 시 즉시 복원)

- 성공 판정 기준 중 **여유 부호 조건**이 어느 fixture 에서든 음수
- 원본 5종 오버레이/fault zoom 이 실기기에서 깨짐 (M8 전환 회귀)
- ref-combo 2회 실행 편차가 `P99_EPSILON_DEG` 초과
- 안전 플래그(safety_flags) 위양성/위음성 신규 발생

---

## 성공 판정 기준

C+M3 는 아래 **전항 충족 시에만** PASS. 하나라도 실패하면 롤백.

1. **success 위양성 여유 전항 양수** — 6동작 fixture 의 success 멤버 전부에서
   `여유 = tol(20°) − max(관절 편차) > 0`.
   현행 기준선: kip-up +15.8° · peter-pan +10.5° · power-spin +9.0° ‖ **elbow-twist +0.2°** ·
   **pdshape −1.2°**. → **pdshape 가 음수→양수로 전환되는 것이 이 작업의 최소 성립 조건.**
2. **fault/success 분리가 현행 이상** — 동작별 `(success 점수 − fault 점수)` 가 현행 이상.
   현행: power-spin 45 · peter-pan 21 · elbow-twist 35 · pdshape 53 · kip-up 20.
   (점수 절대값이 아니라 **분리 폭**으로 판정 — 절대값은 감점 산술의 귀결이며
   [[score-spec-95-100-elite-vision-fix]] 상 일괄 상한을 두지 않는다)
3. **인버전/비인버전 편차 바닥 격차 축소** — 현행 3배(비인버전 2.7~7.3° vs 인버전 14.8~18.0°).
   재처리 후 인버전 2동작의 편차 바닥이 유의하게 내려가야 한다.
   기질 아티팩트 제거의 **직접 지표** — 사람 라벨 불요 ([[analysis-objectivity-no-human-scores]]).
4. **M8 소비 측 무회귀** — 원본 5종(climb·foxtop·foxtop-split·invert·sideway-spin)의
   오버레이·fault zoom crop 이 실기기에서 정상. 축 레이아웃 전환 회귀 0.
5. **M3 발동 확인** — `find_action_segment` 가 실제로 구간을 잘라내는 멤버가 존재
   (현행 12/12 무력화 → 0/12 무력화가 목표는 아니나, **"한 번도 발동 안 함"은 해소**되어야 함).
6. **안전 플래그 무회귀** — safety_flags 위양성/위음성 신규 0 (M3 파급).
7. **pdshape 안정성** — 밀도비 스윕 없이도 재분석 2회 반복 시 점수 편차가 현행 ±30점보다
   유의하게 작을 것.
8. **임계값 재fit 0** — tol 20° · slope 1.2 · cap 90 · `MEAN_EPSILON_DEG` · `P99_EPSILON_DEG`
   전부 불변으로 위 조건 충족 ([[calibration-source-hard-gate]],
   [[scoring-redesign-must-generalize-no-overfit]]).

---

## elbow-twist 처방 경로 (belle 지시 · 지금 belle 에게 묻지 않음)

**belle 원문**: "계속파 이건 이전부터 뭐 확인은 계속하는데 어떻게 하라는건지..."
→ 지적의 핵심은 **"매번 확인만 하고 처방이 안 정해진 채 넘어간 것"**. 그래서 지금 질문하지 않고
**처방 경로를 미리 확정해 박제**한다.

**현황**: elbow-twist success 여유 **+0.2°** (tol 경계에 붙음).
C 조건(기준 PR on 재추출)에서도 **+0.3°** — 개선폭이 사실상 0.
B(밀도 정규화)에서는 **−0.5°** 로 악화. 즉 **어떤 옵션으로도 해소되지 않는 유일한 동작**이다.

**처방 경로 (확정)**

1. elbow-twist 를 **C+M3 작업의 측정 대상에 포함**한다 (Task 4 전수 재검증에 포함, 제외 금지).
2. 재처리 후 여유를 재측정한다.
   - **여유가 충분히 양수(≥ +2.0°)로 회복** → 해소. 추가 조치 없음. belle 에게 결과만 보고.
   - **여유가 여전히 위태(< +2.0°)** → belle 에게 **단 하나의 질문**만 올린다:

     > 정은지 **정상 영상**과 **기준 영상**을 나란히 놓고 — **같은 동작으로 보이십니까?**

     (점수·수치·각도 제시 금지. 영상 2개만 나란히. belle 은 폴스포츠인이 아니므로
     촬영·기술 판단을 요구하지 않고 **육안 동일성**만 묻는다.)

3. **답에 따른 분기 (미리 확정 — 추가 질문 없이 바로 실행)**
   - **"같아 보인다"** → 기술적 원인을 계속 추적한다. 다음 조사 축은 이미 좁혀져 있다:
     elbow-twist 는 역위비율 50.8% / run 19 로 검출은 확실한데 PR 보정이 각도를 2.84° 밖에
     못 움직인다(pdshape 는 4.07°). **PR 보정이 이 동작에서 덜 듣는 이유**가 다음 가설 —
     회전(twist) 성분이 PR 의 순수 위상회전 모델(H=K·R·K⁻¹)로 흡수되지 않을 가능성.
   - **"달라 보인다"** → **기준 영상 교체**. 정은지 정상 영상 중 해당 기술을 다시 촬영/선별해
     `ref-elbow-twist-sister` 를 재등록한다. 이 경우 기술 추적은 중단(원인이 데이터였으므로).

4. 어느 분기든 **belle 에게 두 번째 질문을 만들지 않는다.** 분기 실행 결과만 보고한다.

---

## 이 세션에서 하지 않은 것 (경계 명시)

- 코드 변경 **0** (`backend/`·`app/` 무접촉)
- Firestore write **0** (reference 컬렉션 read-only get 만)
- Pod `rbpnmxhbfoeg35` **무접촉** — 서버 정지 없음, `start_server.sh` env 무변경.
  belle TestFlight 1.1.0 UAT 를 위해 프로덕션 분석 경로 유지.
- 임계값 재fit **0**
- 기준모션 재추출 **미실행** (절차만 문서화 — 착수 시점은 belle 이 UAT 후 결정)

## Constraints (반드시 지킬 것)

- 운영 reference 문서 11종 **belle 승인 없이 덮어쓰기 금지** (pinned 정책 `reference-v1-pinned-force-config`). 측정·검증은 shadow/JSON 으로.
- 채점 코어(각도·감점 산식) **임계값 재fit 금지** (`calibration-source-hard-gate`, `scoring-redesign-must-generalize-no-overfit`). 보유 fixture curve-fit 금지.
- Pod = `rbpnmxhbfoeg35` (RTX 4090, 가동 중, /health 200). SSH `root@213.173.103.168 -p 11713`.
  **파이프라인 동시 호출 금지 — eval 은 SERIAL** (`pipeline-not-concurrency-safe-eval-serial`).
- 검증은 **kip-up 편중 금지, 6동작 전 fixture 동일 빈도** (`verify-all-fixtures-not-kipup-only`).
- belle 이 TestFlight 1.1.0 UAT 진행 중 — **프로덕션 분석 경로를 끊지 말 것** (Pod 서버 정지·env 변경 시 사전 고지).
- 점수 관련 결론은 사람 점수 라벨링 ground truth 사용 금지 (`analysis-objectivity-no-human-scores`).

## 기존 산출물 (재사용)

- Pod: `/workspace/eval32/asym/ref_proff.json`, `/workspace/eval32/asym/ref_pron.json` (기준모션 재추출 PR off/on)
- 로컬 스크립트(scratchpad): `asym_analysis.py`(좌표 기질·역위비율) / `symmetric_rescore.py`(대칭 재채점·재현검증) / `isolate_confounds.py`(재추출 드리프트 vs PR 효과 분리)
- 분석 초안: scratchpad `32-15-ASYMMETRY-CHECK-draft.md` → `.planning/phases/32-result-readability-3-omni/32-15-ASYMMETRY-CHECK.md` 편입 완료
- 2단계 스크립트(scratchpad): `substrate_audit.py` / `substrate_rescore.py` / `substrate_sensitivity.py` /
  `pdshape_instability.py` — 전부 읽기 전용, Firestore write 0, Pod 미사용
- 2단계 JSON: `substrate_audit.json` / `substrate_rescore.json` / `substrate_sensitivity.json`
- 재사용 가능 read-only 계측: `backend/scripts/measure_reference_fps.py` (11 doc fps 라벨 전수 = 18.0)
- 3단계 스크립트(scratchpad, 읽기 전용·Pod 미사용):
  · `ref_inversion_survey.py` — v1 전수 계측 (**축 아티팩트 있음, 원본 5종 결과 무효**. 보존은 이력용)
  · `ref_axis_probe.py` — pole_aligned 축 레이아웃 2갈래 규명 (M8 근거)
  · `ref_inversion_survey2.py` — **v2 축 보정 전수 계측 (위험도 표의 근거, 이것을 재사용할 것)**
  · `ref_margin_dist.py` — 역위 margin 분위 분포 (임계 경계 동작 식별)
- 3단계 JSON: `ref_inversion_survey.json`(v1, 무효) / `ref_inversion_survey2.json`(**v2, 유효**)
- 롤백 기보유 스크립트: `backend/scripts/rollback_reference_motions_phase4.py`
- 자기비교 검증 기보유: `backend/scripts/verify_self_comparison.py` (fixture 미보유 4종 대체 검증용)
