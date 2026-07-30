# 33-G — 승인 목업(라운드7) 전수 대조표

**작성:** 2026-07-30 (대조 완료). **목적:** belle 확인 ② 반려의 근본원인(목업 대비 대조 누락) 방지 —
승인 목업 `mockups/index.html`(7R, belle 승인 2026-07-29)에서 스펙을 전수 추출하고 현 구현과
1:1 대조. **belle의 §9 발견 12건은 부분 목록**(belle: "다 찾은 게 아니라 보다가 중단")이므로
이 표가 수리의 정본 작업 목록이다. 완료 판정 = 수리 후 같은 표 재채점, 전 항목 PASS.

**대조 방법:** 목업 1191줄 전독(주석·CSS·JS 데이터 포함) → 스펙 26항목 추출 → 구현 코드
표적 대조(DeductionDetailSheet.tsx·DefectIllustration.tsx 전독 + result.tsx/VideoCompare.tsx/
KeypointOverlay.tsx/deductionLabels.ts/fault_zoom.py 표적 grep·정독). §9 매핑 병기.

**집계: FAIL 6 · PARTIAL 9 · PASS 9 · 확인보류 2** (+ §9-2 표현결함 6 FAIL). belle 12건 외
신규 발견 = 부위 칩 부재(S3), 시트 구조가 record 단위(S6), basis/method/proof/facing 전무(S7),
어휘 잔재 3곳(S12), F-6 유력 가설 반증.

## A. 스펙 전수 대조 (승인 목업 → 현 구현)

### ① 기본 화면 (자세 비교 카드)

| # | 스펙 (목업 근거) | 현 구현 | 판정 |
|---|---|---|---|
| S1 | 마커 = **항목 단위 그룹**(다리 1 + 어깨 1 + 참고 점선 1), 경계 = kp 실좌표 bounding. 관절 원 나열 금지 (2R#1) | 다리(스플릿 4관절)만 그룹(quick-260705-r6v, `result.tsx:2345`), 그 외 = 관절별 번호 점. 어깨 그룹 없음 | **PARTIAL** |
| S2 | 실선 = 감점 / **점선 = 참고**, "감점은 되지 않지만 회전·힘에 영향" 프레임 전 표면 통일 (3R#3) | 참고(advisory) 점 존재하나 점선 원 형태·프레임 문구 통일 미확인 | **PARTIAL** |
| S3 | 그룹 마커 + **부위 칩**(다리/어깨/참고: 손) 탭 → ② 상세 | 번호 점 탭 → 시트 존재(`result.tsx:2354` 진입점 3). **부위 칩 버튼 없음** | **PARTIAL** |
| S4 | 저신뢰 구간 그룹 자동 생략 | conf 게이트 생략 존재(`KeypointOverlay.tsx:694` focusBounds null, relaxed anchor 생략) | PASS |
| S5 | 기본 화면 새 문장 0 (D-05) | (시뮬 렌더로 확인 — 코드 grep 판정 불가) | 보류 |

### ② 부위 상세 시트

| # | 스펙 (목업 근거) | 현 구현 | 판정 |
|---|---|---|---|
| S6 | **부위 단위 시트**: 칩 → 크롭 페어 → **paircap "내 자세 · 실 1.7초 / 기준 · 실 3.07초"**(기준측 초 필수, 6R) → onecap 마킹 설명 1줄 → 결함 블록 N개(다리 = 고칠 것 1·2) → facing → 일러스트 | **record 단위 시트**(부위에 결함 2개면 시트 2개). paircap 텍스트 초 없음 — 초는 PNG 베이크(`_stamp_time`)+일반 안내문 1줄. onecap 없음 (`DeductionDetailSheet.tsx` 전독) | **PARTIAL** |
| S7 | 블록 요소: **"고칠 것 N — 항목 (−N점)" 번호 헤더**(4R#2) · **basis "어디서 재나요"**(5R#2) · **method 정직 라벨**(5R#3) · numnote 수치 강등 · **proof 증거 3컷**(초 캡션+pnote) · **facing "두 사진이 달라 보이는 이유"** | 번호 헤더 없음(시트 제목 = ①+criterion 라벨). **basis·method·proof·facing 전부 앱에 없음**(전 소스 grep 0건). 수치 강등만 유사 구현(근거 박스 D-09) | **FAIL** |
| S8 | **각도 표시 베이크(어깨류)** — 두 패널 동일: 팔 선+옆구리 선+호 r16, **꼭짓점=겨드랑이**(학생 = shoulder→hip t=0.15 kp 규칙 / 기준 = **모션당 1회 수동 앵커 주석**, 4R·7R#2) | **구현됨** (quick-260730-l7t) — `_draw_joint_angle` + `build_angle_bake_spec` + `ANGLE_BAKE_MAP`(접미사 키잉 4계열) + `_ARMPIT_T=0.15`. 기하 = 팔 64/옆구리 85/호 r16 (`_OUT=360` 이라 승인본 px 1:1), 흰 halo 아래 + 브랜드 코어 위, **호는 흰 단색**(승인 자산 픽셀 실측). 앵커 주석 = `reference_anchors.py` + `judging_data/reference_anchors/`(ref-power-spin 시딩). known-answer 테스트 = 겨드랑이 (200,262) + 실측 사이각 139.8° | **부분 PASS** — 힙류 자동 성립·어깨류 주석 시 성립(스위프 실증), **무릎·팔꿈치류는 8kp 기준으로 원리적 미성립** → §C-4 (아래 잔여 ①②) |
| S9 | **crop 중심 = criterion 꼭짓점 관절 정중앙**, 같은 배율 (4R#1). region 인접 매핑 금지 | **PASS** (quick-260730-l7t) — `criterion_vertex_xy` 단일 출처 + `_crop_box_centered`(안쪽 shift 0) + `_render_crop_padded`(흰 패딩) + 카드당 1회 산출 공용 한 변 `_CRITERION_CROP_FRAC=220/360`. region 상수 3개는 crop 중심 결정에서 강등(멤버·캡션 보조). 인접 매핑 `elbow→hand` 제거(백엔드 `_KISMAM_TO_KEYPOINT` + 앱 `KEYPOINT_FROM_ANGLE_KEY` 동시). 실 7R 학생 프레임 재현 = 프레이밍이 승인 좌 패널과 일치, `user_side_px==ref_side_px==220` | **PASS** (M-2 해소, 단 정중앙 적용 범위 = 단일 관절 각도 카드 — L-10) |
| S10 | 다리류 벌림각 렌더(두 선+사이각, `has_split_angle_record` 게이트) | `_draw_leg_angle:1213`·`_draw_side_leg_angle:1252` 존재. **단 12관절 doc 에서 조용히 생략됨** — `REGION_MEMBERS["legs"]`(hips+knees, ankle 미포함 = 8관절 시절 정의)가 crop bbox 를 정하는데 `_leg_line_pts` 는 **ankle 우선**이라 벌림이 큰 스플릿에서 ankle 이 crop 밖 → `_pt_in_crop` 탈락 → 원 마커 폴백. 실측 = out y 465/486 vs 허용 396 (quick-260730-l7t 스위프). **이 플랜 무관 pre-existing**(관련 함수 전부 무수정 + legacy 해시 변경 0) | **PARTIAL** (구 PASS 는 코드 존재만 확인한 판정 — 12관절 doc 실측 미검증. 근본원인·수리 후보 = quick-260730-l7t `deferred-items.md` D-1, §C-4 에서 실 doc 판정) |
| S11 | 어깨류 기준 프레임 = DTW 실측 순간 (표시용 인덱스 금지, 5R#4) | DTW 짝 ± 4.0s 포즈 거리 탐색 구현(`fault_zoom.py:399-448`, belle #3 반영) | PASS |
| S12 | **화면 어휘 게이트** — "국면·신전·재신전·완성도" 화면 금지, 방향 큐 = 33-A1 사지 방향 데이터 (7R#1) | phrasebook 쪽은 33-13 반영. **잔재 3곳**: `deductionLabels.ts:424` "다리 신전(펴짐)" 라벨, `DimensionDetailModal.tsx:94` "완성도 기준으로", `loading.tsx:68,72` 팁 "완성도" | **PARTIAL** |
| S13 | 일러스트 = **그 항목의 부위·장면과 일치**(불변식 ②) — 불일치 부착 금지 | motionId 키잉 **동작당 1장을 모든 항목에 공통 부착**(`DefectIllustration.tsx:26-33` VERIFIED_ILLUSTRATIONS). 항목별 적합성 판정 코드 없음 → 어깨 항목에 다리 일러스트 | **FAIL** (= M-5) |

### ③ 최악 케이스 원칙

| # | 스펙 | 현 구현 | 판정 |
|---|---|---|---|
| S14 | 가림 → 안 가려진 프레임 캡처 | `select_confident_frame:314`·`select_confident_index:364` 존재, crop 앵커 적용(33-12) | PASS |
| S15 | 결측/저신뢰 → 전신 폴백+마커 생략, 환각 드로잉 금지 | relaxed anchor 생략 게이트·focusBounds null 존재. **각도 표시는 both-or-neither 대칭 게이트 구현**(quick-260730-l7t) — user·ref 스펙 둘 다 성립할 때만 두 패널에 그리고, 한쪽 미달이면 양쪽 모두 원 마커. 스위프 110카드 **비대칭 0**. 원 마커/스켈레톤 계열 대칭은 앱측(§C-2) 잔존 | **PARTIAL → 각도 표시분 PASS** (M-4 각도 축 해소, 마커 축은 §C-2) |
| S16 | 기준 대응 실패 → 전신 폴백 + 정직 캡션 | `DeductionDetailSheet.tsx:232` refMatchFailed 캡션 | PASS |
| S17 | 역립 = "위 다리·훅 무릎" 지칭 (IN-01) | IN-01 완료(25b3cf0) — estimatedArea 강등 | PASS |

### ④ 영상 위 표시

| # | 스펙 | 현 구현 | 판정 |
|---|---|---|---|
| S18 | 상태전이: 재생 → 음성 중(정지+dim+강조+자막+"잠시 멈춤" 라벨) → 재개 | 33-13 구현 + F-1/F-2 수리(6adbfe4). dim·라벨 존재(`VideoCompare.tsx:506-702`) | PASS |
| S19 | 강조 = jointKeys 그룹 위, kp 게이트 통과 → **모양 선(가시 구간만)** / 미달 → **부위 원**, **pulse 1.4s** | **원(bounds circle)만**(`KeypointOverlay.tsx:696-708`). 모양 선 분기 없음. **pulse/Animated 0건**(전 오버레이 소스) | **FAIL** (= M-3+§9 원만 표시) |
| S20 | 재생바 cuedot = 항목 마커, 탭 → 항목 이동 | `VideoCompare.tsx:195,1273` 틱+탭 이동(33-13 D-13) | PASS |
| S21 | 자막 = 목표 선행 카피 (4R#3) | phrasebook 목표-선행 54건(33-13 fda716d~) | PASS |
| S22 | 멈춤 컷 = 결함 텍스트 서술 순간 (불변식 ①: record 실측 창 안) | 틱 = 측정 시점(buildDeductionTicks) 기반이나 멈춤 프레임=재생 위치 — 실측 창 앵커 보장 여부 실기기/시뮬 검증 필요 | 보류 |
| S23 | 음성 중 우상단 **일러스트 동반**(illu-float, 3R 확정 B안) | **없음** — VideoCompare에 일러스트 코드 0건 | **FAIL** |

### 일러스트 (A-7)

| # | 스펙 | 현 구현 | 판정 |
|---|---|---|---|
| S24 | 생성 규칙 = 국면 완성 프레임 → i2i(후보 1 스타일 앵커) → 검수 4게이트 | 6동작 에셋 존재(`assets/illustrations/`), 규칙은 33-14 기록. 미완 4동작 fail-closed | PASS (재생성은 deferred) |
| S25 | 불변식 ② 장면-일러스트 일치 — 항목 국면·부위 키잉 | S13과 동일 — 판정 코드 없음, 동작당 1장 | **FAIL** (S13에 흡수) |
| S26 | 렌더 = 3:4 원본 그대로 (M-6) | `DefectIllustration.tsx:63` aspectRatio 3/4 (원본 720×964, cover 미세크롭 ~0.4%) — 코드상 정합. **belle #11 "빈 배경 프레임"의 실체 재현 필요**(에셋 구도 or 다른 표면) | **PARTIAL** (재현 확인) |

## B. 목업 밖 구현·표현 결함 (§9-2)

| # | 발견 | 수리 방향 | 판정 |
|---|---|---|---|
| F-3 | 자세 비교(참고하세요) 페어 다른 순간 — ref = 대표 프레임 | **백엔드분 PASS** (quick-260730-l7t) — 근본원인 확정: 앱이 `refFrameIdx / rep.fps` 로 초를 추정해 rep(18fps) ↔ video(9fps) 타임베이스 불일치를 그대로 먹었다. 백엔드가 `userVideoSec`/`refVideoSec` 를 방출한다(`_stamp_time` 과 동일 산출, 기준측은 `ref_display_frame_index` 보정 경유, ref 대응 실패 시 미방출). 3-way lockstep = `analysis.ts` + `contract.md §11.8` + 파이프라인 매퍼. **앱 렌더(참고코너/paircap 초 표기)는 §C-2** | 백엔드 PASS / 앱 잔여 |
| F-4 | 100점 헤드라인 폰트 이탈 + 카피 어색 | 요약 카피 빌더 `result.tsx:475-505` 계열 — 조립식 제거·길이 통제·재작성 | FAIL |
| F-5 | 슬라이더 기호 불명 | `GoalGaugeBar.tsx` — 현재 점 마커·허용 밴드에 시각 라벨 없음(a11y 라벨만 `:90`). 라벨 명시 | FAIL |
| F-6 | 실기기 음성 무음 | **§9 유력 가설 반증** — `audioCue.ts:93` `playsInSilentMode: true` 이미 설정. 원인 재조사 필요(setAudioModeAsync 호출 시점·플레이어 수명·실기기 조건) | FAIL (원인 미상) |
| F-7 | 자세히 보기 "확 내려감" | D-17 앵커 스크롤 — 전환 표현 조정(D-05 순서, Claude 재량) | FAIL |
| F-8 | 상시 그룹 마커 | `result.tsx:1484` "skeletonVisible 무관 상시 렌더" — **제거**(D-42), 음성 큐 강조+스켈레톤 토글만 | FAIL |

## C. 수리 순서 (확정)

1. **백엔드** (`fault_zoom.py`): S9 crop 중심 criterion 관절 정중앙化(region 폐기/보조화) → S8 각도 베이크(학생 kp 규칙 — 어깨 외 무릎/팔꿈치/힙 계열 선-쌍 확장 정의) + 기준 앵커 주석 스키마·소비 → F-3 참고코너 페어 DTW 프레임. 기준 앵커 데이터 = 11모션 × criterion 수동 주석 1회(Claude 작업, 프레임 열람 기반).
2. **앱**: S7 시트 블록 요소(번호 헤더·basis·method·proof·facing) + S6 부위 단위 재구성·paircap 초·onecap → S19 강조 선/원 분기 + pulse(마커 전반 M-3) → S13 일러스트 장면일치 판정(33-A1 국면 표 × record 부위, fail-closed) → S23 illu-float → S1~S3 그룹 마커·부위 칩 → S12 어휘 잔재 → F-4~F-8 (F-8 = 상시 마커 제거).
3. **재채점**: 이 표 전 항목 PASS + **등재 10동작 일반화 스위프** + 시뮬 렌더 (보류 2건 S5·S22 여기서 판정).
4. **Pod 재스위프**(crop·각도 베이크 전수 재생성 — belle greenlight, D-30) → 일괄 OTA → belle 확인 ③ 1회.

## C-1 완료 기록 (백엔드, quick-260730-l7t — 2026-07-30)

**재채점 근거 = 산출물.** 등재 10동작 스위프(`.planning/quick/260730-l7t-.../sweep_angle_crop.py`)
110카드 + 생성 PNG 직접 열람 + legacy 무회귀 해시.

| 지표 | 수치 |
|---|---|
| 동작 / 카드 | 10 (criteria glob 파생, 하드코딩 0) / 110 |
| 방출 / 미방출 | 90 / 20 (미방출 전건 = `angle_vs_reference__{left,right}_elbow` — 기준 8kp 에 elbow 부재 → D-12 ② drop = L-6 fail-closed) |
| 정중앙 crop | 60 (단일 관절 각도 카드 전건). `user_side_px == ref_side_px == shared_side_px` 전건 일치 |
| 각도 베이크 | 21 drawn (힙류 20 + `ref-power-spin` 어깨 1) / 39 `omitted:ref_gate` / 30 `omitted:unmapped`(split·다관절) |
| 각도 비대칭 카드 | **0** (both-or-neither 게이트) |
| 동작명 분기 | **0** (`fault_zoom.py` grep, 주석 제외) |
| legacy/advisory/mode3 PNG 해시 | 9케이스 **변경 0** |
| `backend/tests` 회귀 | **0** (작업 시작 커밋 6ff667a 대비 FAILED/ERROR node ID 58건 완전 동일) |

**데이터 키잉 실증 (D-41).** 어깨 카드 10동작 대조 — `ref-power-spin` 만 `drawn`, 나머지 9동작은
`omitted:ref_gate`. 코드는 하나인데 거동이 **모션별 앵커 주석 데이터**로만 갈린다.

**열람한 PNG (D-40 — 코드 통과 ≠ 완료).** 승인 자산 `belle_shoulder_pair_dtwmatch_r7.png` 와
나란히 대조:
1. `sweep_out/ref-power-spin__angle_vs_reference__left_shoulder.png` — 두 패널 동일 기하(꼭짓점 정중앙 + 위=사지 선 + 아래=몸통 선 + 꼭짓점 안쪽 흰 호), 승인본 구조 일치.
2. `sweep_out/ref-invert__angle_vs_reference__left_hip.png` — 힙류 자동 성립분, 두 패널 동일.
3. `sweep_out/ref-foxtop-split__split_angle.png` — 다리 카드(원 마커 폴백 = S10 PARTIAL 실체).
4. `sweep_out/ref-kip-up__angle_vs_reference__left_shoulder.png` — 미주석 동작, **양측** 원 마커(비대칭 0).
5. `sweep_out/anchored/ref-climb__angle_vs_reference__left_elbow.png` — 무효 대입(vertex==limb) → degenerate 거부, 양측 원 마커.
6. 실 7R 학생 프레임(`belle_still_f017`) 재현 카드 — 프레이밍이 승인 좌 패널과 일치(`user_side_px=ref_side_px=220`), 마커 = 패널 정중앙.

⚠ 스위프의 keypointReport 는 **합성 좌표**(기준 영상이 로컬에 없음)라 선이 실 사지 위에 앉는지는
검증 대상이 아니다 — 기하·대칭·정중앙·배율만 판정했다. **해부학적 정합은 §C-4 Pod 재스위프**에서
실 doc 좌표로 판정한다.

### §C-1 잔여 이관

| # | 항목 | 이관 | 근거 |
|---|---|---|---|
| ① | 9모션 × criterion 앵커 주석 **값** 채우기 | §C-4 (Pod) | 기준 프레임 실물 열람 필요 (L-9). 절차 = `judging_data/reference_anchors/README.md` |
| ② | **무릎·팔꿈치류 각도 베이크는 주석으로 복귀 불가** | §C-4 (기준 라이브러리 12kp 재처리) | 스위프 실증: 무릎은 사지 방향점이 ankle 인데 8kp 에 없고 대체 가능한 관절도 없다. 팔꿈치는 `elbow←hand` 대입 시 vertex==limb 로 degenerate. 즉 **L-7 의 "주석이 채워질 때까지"는 어깨류에만 참**이고 무릎·팔꿈치는 12kp 재처리가 조건 |
| ③ | S10 다리 사이각 12관절 doc 생략 | §C-4 판정 후 별 플랜 | pre-existing, 근본원인 확정 = `deferred-items.md` D-1 |
| ④ | 앱: region-first 조인 강등 · paircap 초 렌더 · 시트 재구성 · 참고코너 페어 | §C-2 | L-8 — 본 플랜은 값 방출까지 |
| ⑤ | crop 전수 재생성 · OTA · belle 확인 ③ | §C-4 / D-45 | 일괄 1회 원칙 |

*스펙 원본 = mockups/index.html 전독. 결정 = 33-CONTEXT.md D-39~D-45. §9 = 33-PHASE-GATE-EVIDENCE.md.*
*C-1 재채점 = quick-260730-l7t (2026-07-30). 자체 도출 결정 L-1~L-11 = 그 플랜 SUMMARY.*
