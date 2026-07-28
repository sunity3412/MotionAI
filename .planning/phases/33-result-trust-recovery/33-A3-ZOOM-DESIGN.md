---
phase: 33-result-trust-recovery
plan: 10
title: A-3 확대비교(fault-zoom) 재설계 조사 — 판정 기준 고정 + 근거 3갈래 + 옵션 + seam #1 결정
status: complete
authored: 2026-07-28
requirements: [D-05, D-07, D-12, D-18, D-19, D-24]
consumers: [33-11 (A-4 목업 — 탭-상세 초점), A-5 (구현 — seam 결정 소비)]
substrate: "candidate phase33-cm3-run1 (33-17 shadow resolver 경로) — flip(33-07)은 belle 결정(2026-07-28)으로 A-트랙 뒤 이연. 데이터 한계 강은 candidate(9fps 재추출) 기준"
locked_upstream:
  - "belle 설계 확정 (2026-07-28, faultzoom debug 종결): 기본 화면 = 프레이밍 D(세로 패널 캡처, 인물 bbox fit, 폴 포함, 잡힌 관절 전부 마커) / 부위 탭 → 상세(확대 크롭 + 감점근거 글 + facing 설명 흡수 + A-7 일러스트 슬롯, Ochy 패턴). 본 문서는 이 확정을 재론하지 않고 그 위에 조사를 얹는다 (재발산 금지)."
sources:
  - ".planning/phases/33-result-trust-recovery/33-CONTEXT.md D-05/D-07/D-08/D-12/D-24 (판정 기준 원문)"
  - ".planning/phases/33-result-trust-recovery/33-A1-MOTION-STANDARDS.md ④열 (동작별 어디를·어느 순간 — 도메인 강)"
  - ".planning/debug/resolved/faultzoom-same-frame-crops.md (벤치마크·프레이밍 실험·facing 프로브·belle 확정 — 선행사례/데이터한계 강 확정분)"
  - "backend/shared/python/sunity_shared/analysis/fault_zoom.py (직접 열람: _side_crop:975, _to_rep_idx:196, select_confident_frame:209, select_pose_matched_pair:526, ref_display_frame_index:668, _matched_ref_frame:715, _mark:1083, build_fault_zoom_comparisons:1745)"
  - ".planning/phases/33-result-trust-recovery/33-A0-EVIDENCE.md (pointed/shown/measured 3집합 대조 — seam 결정 근거)"
  - "NotebookLM 폴스포츠 노트북 96b061e8 query 1건 (2026-07-28): 강사 교정 방식 + IPSF 심판 관찰 방식"
  - "app/src/lib/deductionLabels.ts:221-240 (projectDeductionRecordKeypoints) + app/src/app/analysis/result.tsx:1325 (selectedZoom, 구 :1215)"
---

# 33-A3-ZOOM-DESIGN — 확대비교 재설계 조사

> **읽기 순서 규약 (D-24):** 1절 판정 기준이 **조사·옵션보다 먼저 고정**됐다. 2절 이후의
> 모든 채택/기각은 1절 기준으로만 판정한다 — 취향 논쟁 금지. 이 문서 이후 A-4(목업)·
> A-5(구현)는 1절 기준과 4절 seam 결정을 재론하지 않는다.

## 1. 판정 기준 (D-07 — 고정, 이후 불변)

33-CONTEXT.md D-07 원문 그대로 박제한다. 목업·구현의 합격선이며, 아래 6개 전부 동급이다.

> **D-07** 판정 기준 6개:
> ① 3초 안에 어디가 문제인지 짚기
> ② 두 사진에서 무엇이 다른지 가리키기(글자 없이 형태만으로면 최상)
> ③ 그래서 뭘 하라는지 전달(단 D-05 순서를 지킨 결과여야 함)
> ④ 최악 데이터에서도 안 무너짐
> ⑤ 틀렸을 때 틀린 줄 알 수 있음(표시는 자기 근거를 밝힘 — 무슨 관절·어느 순간)
> ⑥ 화면이 전보다 단순해짐(요소·문장 수가 늘었으면 실패). ⑥은 ①~⑤와 동급.

**보조 제약 (판정에 함께 적용):**

- **D-05 해법 순서**: ① 없앤다 → ② 자명하게(같은 크기·같은 순간·같은 표시) → ③ 최후에
  한 줄. 새 문장 최대 1줄, 새 라벨·배지·범례 금지. 옵션은 표시를 **줄이거나 답을 붙이거나**
  둘 중 하나여야 한다.
- **D-08 최악 데이터 목록 (고정)**: 가림(다른 신체·폴에 관절 가려짐) / 거꾸로(인버전) /
  회전 중 모션블러 / 프레임 밖 잘림 / 좌표 결측 구간. 좋은 케이스만으로 그린 목업은 무효.
- **D-12 카드 불변식**: 두 사진은 같은 순간·같은 배율·같은 표시. 캡션이 무엇을 견주는
  중인지 한 문장. 안 되면 그 카드는 내보내지 않는다.

## 2. 근거 3갈래

### 2(a) 도메인 — 강사/심판은 무엇을 어떻게 짚는가

#### 동작별 "어디를 · 어느 순간" (33-A1 표 ④열 — 크롭이 잘라야 할 것)

| 동작 | 어디를 (부위) | 어느 순간 |
|---|---|---|
| ref-power-spin | 양 무릎 + 위·아래 다리 라인 + 양 견갑 | hold 7.1~10.2s (f71~f92). 진입 펌핑 구간은 크롭 대상 아님 |
| ref-peter-pan | 신전 다리 무릎 + hook 무릎 굽힘각 + 위 그립 어깨 | hold 회전 중 peak 4s 전후 (f18~f54) |
| ref-elbow-twist-sister | 윗다리 무릎·수직 라인 + 엘보 그립 팔 + hook 무릎 | 메인 hold 9.5~17.5s, peak 13s (f99~f117) |
| ref-pdshape | hook 측 무릎·고관절 + folded 다리 무릎 각 + 척추 비대칭 정렬 | 메인 hold 3.5~11.5s, peak 8s (f54 부근) |
| ref-kip-up | 양 어깨 + 스트래들 폭(양 고관절), 무릎은 보조 | 스윙~후방 통과 3~5.5s, peak 4s (f27~f50) |
| ref-climb | 양 무릎 X자 접촉부 + 주 그립 어깨 | hook 잠금 순간 peak 5s (f45 부근) |
| ref-invert | 양 고관절 외전 + 양 무릎 + 좌우 대칭 | 인버트 스플릿 hold 6~10s, peak 7s (f63 부근) |
| ref-foxtop | 위(왼)다리 라인 + 양 무릎 + 주 그립 견갑 | 수직 스플릿 15~21s, peak 18s (f164~f183) |
| ref-foxtop-split | 양 다리 벌림각 + 신전측 무릎 + hook 무릎 | 채점 피크 11~13s (f99~f117) |
| ref-sideway-spin | 자유 다리 무릎·고관절 신전 + 주 그립 어깨 (척추 아치는 UNVERIFIED — 키포인트 부재) | 회전 peak 9s±2s (f63~f99) |

읽히는 패턴: 강사가 짚는 것은 언제나 **"특정 부위 + 특정 순간(hold/peak)"** 쌍이다.
전 구간·전신을 뭉뚱그려 짚는 동작이 하나도 없다.

#### 학원 관용구 → 화면 은유 매핑 (새 표기법 발명 0 — D-09)

| 학원에서 통하는 방식 | 화면 은유 (확정 설계에서의 자리) |
|---|---|
| 손으로 부위를 짚어줌 | 마커 원 — D 캡처의 **잡힌 관절 전부** (대표 1개 아님, belle 확정) |
| 시범과 나란히 보기 | [학생\|기준] 나란히 쌍 — 탭-상세의 확대 크롭 |
| 시범(정은지가 이렇게) | 기준 패널 + A-7 일러스트 슬롯 (탭-상세) |
| "왜 안 되는지" 말로 설명 | 탭-상세의 감점근거 글 (facing 잔재도 여기서 글로 흡수 — belle A) |
| 거울 | 학생 본인 영상 재생 (비교 관용구 아님 — 동작비교 뷰 소관) |

#### NotebookLM 실측 (2026-07-28 query, 노트북 96b061e8)

- **강사 지도 방식(거울/손짚기/나란히/시범)은 출처 문헌에 구체적 방법론으로 부재** —
  문헌은 강사 트레이닝 과정에 "역학적 해부학 원리를 활용한 티칭법 + 스포팅 기법"이
  교육된다는 수준만 기재. 위 매핑 표의 관용구는 A-1 ③열과 같은 한계(현장 리서치
  `docs/research/폴스포츠 수강생의 설문조사.md` + 기존 문서 어휘의 재조합)를 지니며,
  파일럿에서 강사 실사용 방식이 수집되면 갱신한다 (D-18 — 한계 명시).
- **IPSF 심판의 관찰 방식은 상세히 문서화돼 있고, 크롭 설계에 직결된다:**
  1. **Fixed Position** — 심판은 진입/진출 과도기를 배제하고 "목표 포지션을 명확하게
     고정(Fix)한 시점부터" 측정한다. hold 최소 2초. → 크롭 순간 = hold/peak 창
     (④열의 순간 지정과 정확히 일치).
  2. **신체 영역 다이어그램** — 심판은 실루엣이 아니라 해부학적 경계선("발목뼈에서
     골반뼈까지", "손목에서 어깨까지")으로 신체를 **잘라서** 독립 계측한다.
  3. **Criteria 텍스트 1:1 대조** — 감점 근거는 요소표의 접촉 부위/팔·그립 자세/몸
     자세를 선수 신체와 1:1로 대조해 나온다. → **심판의 관찰 자체가 criterion-키
     구조**다. 크롭이 "그 criterion 이 계측한 부위·순간"을 잘라야 도메인 관용구를
     옮긴 것이 된다 (4절 seam 결정의 도메인 근거).
  4. 심판석 단일 시점 관찰 + 가림 시 Poor presentation −0.5 / 180° 스플릿은 전 각도
     검증(3D rule) — 단일 카메라 앱이 재현 불가한 부분은 단정하지 말아야 한다
     ([[camera-angle-scoring-stretch-reference-corner]] 정합).

**도메인 강 결론:** 강사도 심판도 "부위(해부학 경계) + 순간(고정된 hold)"으로 짚는다.
확대비교가 보여줄 것은 (criterion 이 가리키는 부위, 그 감점이 측정된 순간)의 쌍이며,
전신 실루엣 비교나 임의 순간 비교는 도메인 관용구가 아니다.

### 2(b) 선행 사례 — 자세 비교 관용구 (debug 벤치마크 확정분 — 재조사 금지)

**벤치마크 사실 (2026-07-28 완료분, faultzoom debug):** V1 Golf / OnForm / Sportsbox AI /
Ochy / coach.ly 조사 — 선두 앱 중 **자동 관절 타이트 크롭을 기본 표시로 쓰는 곳 0.**
표준 = 전신 + 선·각·원 드로잉으로 시선 유도 + 탭 상세(progressive disclosure, Ochy).
폴 도메인 직접 선례 부재. 폴 = 수직 기준선이라 관절 크롭은 "폴 대비 라인" 맥락을
제거한다 (IPSF line 채점도 전신 라인 기준).

**관용구별 강/약 (같은 순간·같은 배율 자세 diff 관점) + 데이터 한계 판정:**

| 관용구 | 잘 보여주는 것 | 못 보여주는 것 | 판정 (근거는 2(c)) |
|---|---|---|---|
| 나란히 (side-by-side) | 두 자세의 형태 차이를 각자 온전한 픽셀로. 프레이밍이 좌표 오차에 둔감 | 미세한 겹침 차이 (시선이 왕복해야 함) | **VALID** — 현행 `_compose` 유지. 탭-상세의 관용구 |
| 반투명 겹침 (overlay) | 정합만 되면 차이가 즉시 드러남 | 정합이 깨지면 차이가 아니라 노이즈를 보여줌 | **INVALID** — facing 신호 부재 + 역립 환각으로 정합 보장 불가 (2(c)-5·6) |
| 슬라이더 와이프 | 겹침과 동일 (인터랙티브) | 겹침과 동일 전제(픽셀 정합) + 저해상 업스케일에서 경계 뭉개짐 | **INVALID** — 겹침과 동일 사유 (2(c)-1·5) |
| 유령 실루엣 (ghost) | 이상적 자세를 학생 프레임 위에 반투명 스켈레톤으로 | 스켈레톤이 틀리면 자신 있게 틀린 형상을 그림 | **INVALID** — 8관절(척추·발목 무) + 역립 환각 관절 (2(c)-6·9, D-07 ⑤ 위반) |
| 각도호 (angle arc) | 벌림각의 시각 언어 (숫자 없이) | 벌림 아닌 결함(신전·facing)엔 오독 유발 | **VALID-게이트** — split_angle record 있을 때만 + 학생 측만 (기존 게이트 A/B 유지) |
| 궤적선 (trajectory) | 시간에 걸친 이동 경로 | 회전 동작에서 궤적이 자기겹침 + keypoint flicker 로 선이 요동 | **INVALID** — 시간 안정 track 부재 (2(c)-6), D-07 ① 실패 |
| 마커 원 | "여기를 봐" 손짚기의 직역 | 마커만으론 "뭘 하라"는 없음 (글/일러스트가 보완) | **VALID** — conf 게이트 + valid crop 앵커에서만 (기존) |

### 2(c) 데이터 한계 — 백엔드가 실제로 줄 수 있는 것 (fault_zoom.py 직접 열람, D-19)

무엇을 열어 확인했나: `fault_zoom.py` 의 `_side_crop:975`(3단 강하), `_to_rep_idx:196`
(fps 변환 단일 출처), `select_confident_frame:209`(window 내 conf argmax),
`select_pose_matched_pair:526`(궤적 평균 쌍 매칭), `ref_display_frame_index:668`
(rep↔video 타임베이스 매핑), `_matched_ref_frame:715`(DTW 대응), `_mark:1083`(마커 원,
배지 제거 후), `build_fault_zoom_comparisons:1745`(본체 + 폴백 사슬)을 이 세션에서
직접 읽었다. 상수: `_CROP_FRAC 0.42` / `_OUT 360` / `_KP_CONF_MIN 0.5` /
`_POSE_SEARCH_SECONDS 4.0` / `_POSE_TRAJ_RADIUS 2` / `_POSE_MIN_COMMON_JOINTS 4`.

1. **소스 해상도 640px 고정** — frame_extractor 는 긴 변 640(세로영상 360×640)으로
   추출한다. 단일 관절 크롭 = 짧은 변 × `_CROP_FRAC`(0.42) ≈ 151px 를 `_OUT`(360)으로
   **2.4× 업스케일** (debug 실측). 확대할수록 열화, 덜 확대할수록 선명 — "더 크게
   확대"류 옵션은 물리적으로 손해다. 프레이밍 D(1.6×)가 현행 A(2.4×)보다 선명한
   이유이자, 와이프/픽셀합성류가 INVALID 인 이유의 절반.
2. **crop bbox 신뢰성 = 3단 강하** — `_side_crop`: valid(멤버 관절 conf ≥
   `_KP_CONF_MIN` 0.5 → 관절 앵커에 마커 원) → relaxed(저신뢰-유한 좌표 중심, **앵커
   생략** = 오인 방지) → full(좌표 결측 → 전신 폴백, 마커 없음). 저신뢰 구간에서
   크롭 중심이 엉뚱한 부위(뒤통수)가 될 수 있어 마커가 게이트된다. **옵션은 "마커가
   항상 있다"를 전제할 수 없다** — relaxed/full 폴백 상태를 D-08 최악 케이스로 그려야
   한다.
3. **fps 공간이 3종** — ① 9fps frames 배열(비디오 렌더 소스) ② user keypointReport
   (`report['fps']`) ③ ref keypointReport. 모든 인덱스는 `_to_rep_idx:196` 단일 공식으로
   라우팅한다(중복 공식 금지). candidate substrate(phase33-cm3-run1)는 ref 를 **9fps 로
   재추출**해 ref rep 공간과 frames 공간이 정합(`ref_display_frame_index` 매핑 배율
   1.0 = identity)이지만, **mode3 는 잔존 함정** — 지난 사용자 doc 의 prev angles 는
   9fps 저장인데 keypointReport 만 18fps upsample 이라 방출측이 `dtw_ref_fps=9.0` 을
   명시해야 한다 (미지정 = 절반 시각 오독, 파일럿 D2 재현). 옵션이 mode3 를 다룰 때
   이 경로를 우회할 수 없다.
4. **DTW 대응 실패 폴백 = 정직 전략** — `_matched_ref_frame:715` 가 None 이면 ref
   **전신 폴백 + refMatch='failed'** (build:1854-1899). 시간비례 근사로 엉뚱한 pose 를
   확대하는 것을 금지한 설계다(오도 0, 정보 보존). 앱은 `refMatch==='failed'` 캡션으로
   실패를 밝힌다 — D-07 ⑤(자기 근거)를 코드가 이미 지키는 지점. 옵션도 "대응 실패
   시 무엇을 보여줄지"를 정직 폴백으로 설계해야 한다.
5. **facing(몸통 장축 회전)은 원리적 부재** — 같은-포즈 쌍 매칭
   (`select_pose_matched_pair:526`)은 ±2프레임 궤적 평균으로 환각 keypoint 를 자연
   강등하지만, 같은 반회전 내 ~20° 토르소 회전(가슴 카메라쪽 vs 폴쪽)은 8관절 2D
   기하가 구분 못 한다 — facing 프로브 실측: 어깨/골반 x-순서 부호가 학생·오답·GT
   3자 동일, 거리 격차 36.2%, 게이트 시뮬 카드 이동 0. **fix 미적용 확정, belle A =
   탭-상세 글로 흡수.** 어떤 옵션도 "facing 까지 같은 프레임"을 전제하면 INVALID.
6. **역립 구간 keypoint 환각 + 좌우 귀속 불신** — 역립에서 무릎 keypoint 가 conf
   0.68~0.70 으로 얼굴 위치에 찍히는 환각 실측. kismam per-joint 좌우 귀속은
   `attributionReliability.unreliable=true` (IN-01 — visibility 0.51, overTolJointCount 8)
   로 강등된다. **옵션은 역립에서 좌/우 라벨("왼무릎이")을 단정할 수 없다** — 기능
   역할 지칭(위 다리/훅 무릎)만 가능 (33-09 큐 작성 규칙과 동일).
7. **좌표 결측 구간 실재** — candidate 판독에서 골격 전체가 한 점으로 붕괴(span<30px)한
   프레임이 존재한다 (A-1 검증 노트). 크롭 앵커/드로잉 대상에서 제외돼 3단 강하의
   full 폴백으로 떨어진다. D-08 "좌표 결측"은 가설이 아니라 실측이다.
8. **veto 다관절 동시 지적 시 카드 1장 붕괴** — faultJoints 4관절(legs 묶음)이 카드
   1장 + 대표 마커 1개로 뭉치면 나머지 관절 지적이 화면에서 숨는다 (belle 무릎 질문
   실측: 채점은 [LK,RK,LH,RH] 전부 잡았는데 left_knee 마커 1개만 표시). → **D 캡처
   마커는 잡힌 관절 전부** (belle 확정, 재론 금지). 카드 나열형 옵션은 이 붕괴를
   구조적으로 반복한다.
9. **spine_mid 부재** — 8관절 이름공간에 척추가 없어 아치 곡률(sideway-spin)을
   측정도 크롭 근거 제시도 못 한다 (A-1 UNVERIFIED). 아치를 그리는 옵션은 근거 없는
   표시 = D-18 짝 없는 표시 금지에 걸린다.

**틀리면 걸리는 장치 (D-18):** 이 절이 그 장치다 — 백엔드가 못 주는 데이터를 그린
옵션(겹침·와이프·유령·궤적·아치 드로잉·facing 동일 전제)은 목업 전에 여기서 INVALID 로
걸렸다. A-4 목업이 이 절과 모순되는 표시를 그리면 이 문서 대조로 즉시 반증된다.
