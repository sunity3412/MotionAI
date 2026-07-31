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
| S1 | 마커 = **항목 단위 그룹**(다리 1 + 어깨 1 + 참고 점선 1), 경계 = kp 실좌표 bounding. 관절 원 나열 금지 (2R#1) | 다리(스플릿 4관절)만 그룹(quick-260705-r6v, `result.tsx:2345`), 그 외 = 관절별 번호 점. 어깨 그룹 없음 | **부분 PASS** (2단위 렌더확인 — 그룹 경계+번호 배지, 개별 관절 원 나열 0. 병합 배지는 도달 불가로 미확인) |
| S2 | 실선 = 감점 / **점선 = 참고**, "감점은 되지 않지만 회전·힘에 영향" 프레임 전 표면 통일 (3R#3) | 참고(advisory) 점 존재하나 점선 원 형태·프레임 문구 통일 미확인 | **미검증** (2단위 코드 반영. 참고 관절 doc 도달 불가 + 재생 필요 → 실기기 확인 ③) |
| S3 | 그룹 마커 + **부위 칩**(다리/어깨/참고: 손) 탭 → ② 상세 | 번호 점 탭 → 시트 존재(`result.tsx:2354` 진입점 3). **부위 칩 버튼 없음** | **PASS** (2단위 렌더확인 — 부위 칩 3개 = 감점 부위 3개, 칩→해당 시트, 1단위 구조 회귀 0) |
| S4 | 저신뢰 구간 그룹 자동 생략 | conf 게이트 생략 존재(`KeypointOverlay.tsx:694` focusBounds null, relaxed anchor 생략) | PASS |
| S5 | 기본 화면 새 문장 0 (D-05) | (시뮬 렌더로 확인 — 코드 grep 판정 불가) | 보류 |

### ② 부위 상세 시트

| # | 스펙 (목업 근거) | 현 구현 | 판정 |
|---|---|---|---|
| S6 | **부위 단위 시트**: 칩 → 크롭 페어 → **paircap "내 자세 · 실 1.7초 / 기준 · 실 3.07초"**(기준측 초 필수, 6R) → onecap 마킹 설명 1줄 → 결함 블록 N개(다리 = 고칠 것 1·2) → facing → 일러스트 | **부위 단위로 재구성됨** (quick-260730-py1, `deductionSheet.buildRegionSheetView`). **시뮬 렌더 확인(오케스트레이터)**: 시트 제목 "어깨 부위 상세", 순서 = 칩 → 크롭 페어 → paircap 좌우 → onecap 1줄 → 블록 → 일러스트 = 승인 순서 일치. **한 부위 2감점 = 시트 1개·블록 2개**를 임시 doc(어깨 좌+우)으로 실증 — "고칠 것 2 — 왼쪽 어깨 (−8.9점)" / "고칠 것 3 — 오른쪽 어깨 (−5.1점)", 각 블록이 자기 basis·cue·method 보유(병합 0). 번호 = 전역 마커 번호. ⚠ **paircap 초는 미검증** — 렌더 가능한 doc 4건이 전부 §C-1 백엔드 변경 이전 산출이라 `userVideoSec`/`refVideoSec` 필드 자체가 없다(Firestore 조회로 확인). 앱은 rep 인덱스 재계산 없이 폴백 = 올바른 거동이나 **초가 실제로 찍히는지는 §C-4 Pod 재산출 doc 에서 판정** | **부분 PASS** (구조·블록 N개 PASS / 초 표기 미검증) |
| S7 | 블록 요소: **"고칠 것 N — 항목 (−N점)" 번호 헤더**(4R#2) · **basis "어디서 재나요"**(5R#2) · **method 정직 라벨**(5R#3) · numnote 수치 강등 · **proof 증거 3컷**(초 캡션+pnote) · **facing "두 사진이 달라 보이는 이유"** | **번호 헤더·basis·method·numnote 신설·렌더 확인**(quick-260730-py1 + 시뮬). 헤더 = 브랜드 틴트 바(카드 좌우 끝까지), 1감점 부위는 번호 절 생략·2감점은 번호 부여. basis "어디서 재나요:" 회색 박스(굵은 문두가 `<b>` 문자열 노출 없이 중첩 Text 로 렌더). method "측정 방법 —" 틸 박스. numnote 블록 맨 뒤 작은 회색. **미달 2축(의도적 fail-closed, 날조 금지)**: ① **proof 3컷 = 자리 자체를 두지 않음** — 백엔드가 카드당 PNG 1장만 방출하고 "좋았던/감점/마무리" 분류는 doc 에 없는 측정 판단이라 앱이 만들면 판정 날조(M-10) ② **basis 구간 축 부재** — 창 인덱스→초 변환에 필요한 fps 가 앱에 없고, 인덱스를 나눠 초를 추정한 것이 F-3 근본원인이라 반복 금지(M-7). **facing 은 렌더 미확인**(어깨 항목에서 해당 위치까지 확인 못 함) | **PARTIAL** (4축 PASS / proof·basis구간 = §C-4 백엔드 방출 대기 / facing 미검증) |
| S8 | **각도 표시 베이크(어깨류)** — 두 패널 동일: 팔 선+옆구리 선+호 r16, **꼭짓점=겨드랑이**(학생 = shoulder→hip t=0.15 kp 규칙 / 기준 = **모션당 1회 수동 앵커 주석**, 4R·7R#2) | **구현됨** (quick-260730-l7t) — `_draw_joint_angle` + `build_angle_bake_spec` + `ANGLE_BAKE_MAP`(접미사 키잉 4계열) + `_ARMPIT_T=0.15`. 기하 = 팔 64/옆구리 85/호 r16 (`_OUT=360` 이라 승인본 px 1:1), 흰 halo 아래 + 브랜드 코어 위, **호는 흰 단색**(승인 자산 픽셀 실측). 앵커 주석 = `reference_anchors.py` + `judging_data/reference_anchors/`(ref-power-spin 시딩). known-answer 테스트 = 겨드랑이 (200,262) + 실측 사이각 139.8° | **부분 PASS** — 힙류 자동 성립·어깨류 주석 시 성립(스위프 실증), **무릎·팔꿈치류는 8kp 기준으로 원리적 미성립** → §C-4 (아래 잔여 ①②) |
| S9 | **crop 중심 = criterion 꼭짓점 관절 정중앙**, 같은 배율 (4R#1). region 인접 매핑 금지 | **PASS** (quick-260730-l7t) — `criterion_vertex_xy` 단일 출처 + `_crop_box_centered`(안쪽 shift 0) + `_render_crop_padded`(흰 패딩) + 카드당 1회 산출 공용 한 변 `_CRITERION_CROP_FRAC=220/360`. region 상수 3개는 crop 중심 결정에서 강등(멤버·캡션 보조). 인접 매핑 `elbow→hand` 제거(백엔드 `_KISMAM_TO_KEYPOINT` + 앱 `KEYPOINT_FROM_ANGLE_KEY` 동시). 실 7R 학생 프레임 재현 = 프레이밍이 승인 좌 패널과 일치, `user_side_px==ref_side_px==220` | **PASS** (M-2 해소, 단 정중앙 적용 범위 = 단일 관절 각도 카드 — L-10) |
| S10 | 다리류 벌림각 렌더(두 선+사이각, `has_split_angle_record` 게이트) | `_draw_leg_angle:1213`·`_draw_side_leg_angle:1252` 존재. **단 12관절 doc 에서 조용히 생략됨** — `REGION_MEMBERS["legs"]`(hips+knees, ankle 미포함 = 8관절 시절 정의)가 crop bbox 를 정하는데 `_leg_line_pts` 는 **ankle 우선**이라 벌림이 큰 스플릿에서 ankle 이 crop 밖 → `_pt_in_crop` 탈락 → 원 마커 폴백. 실측 = out y 465/486 vs 허용 396 (quick-260730-l7t 스위프). **이 플랜 무관 pre-existing**(관련 함수 전부 무수정 + legacy 해시 변경 0) | **PARTIAL** (구 PASS 는 코드 존재만 확인한 판정 — 12관절 doc 실측 미검증. 근본원인·수리 후보 = quick-260730-l7t `deferred-items.md` D-1, §C-4 에서 실 doc 판정) |
| S11 | 어깨류 기준 프레임 = DTW 실측 순간 (표시용 인덱스 금지, 5R#4) | DTW 짝 ± 4.0s 포즈 거리 탐색 구현(`fault_zoom.py:399-448`, belle #3 반영) | PASS |
| S12 | **화면 어휘 게이트** — "국면·신전·재신전·완성도" 화면 금지, 방향 큐 = 33-A1 사지 방향 데이터 (7R#1) | phrasebook 쪽은 33-13 반영. **잔재 3곳**: `deductionLabels.ts:424` "다리 신전(펴짐)" 라벨, `DimensionDetailModal.tsx:94` "완성도 기준으로", `loading.tsx:68,72` 팁 "완성도" | **코드 PASS / 시트 렌더 일부 미확인** (4단위 — 33-G 가 적은 3곳이 아니라 **7파일 16곳**이 실측. `screenVocabulary.test.ts` 가 app/src 72파일 상시 스캔, 금지어는 `phrasebook.json` 직접 읽어 복제 0. 백엔드 게이트도 `terminology_map.json` 까지 스코프 확장 — 구 게이트가 phrasebook 3섹션만 봐서 "완성도"가 살아남던 구조적 구멍. 앱 소스 잔재 grep **0**(오케스트레이터 재확인). 결과 화면 렌더 확인함. **부위 시트 용어줄은 화면으로 못 봄**) |
| S13 | 일러스트 = **그 항목의 부위·장면과 일치**(불변식 ②) — 불일치 부착 금지 | motionId 키잉 **동작당 1장을 모든 항목에 공통 부착**(`DefectIllustration.tsx:26-33` VERIFIED_ILLUSTRATIONS). 항목별 적합성 판정 코드 없음 → 어깨 항목에 다리 일러스트 | **PASS** (3단위 렌더확인 — 어깨 시트 일러스트 **미부착**, 다리 시트 **부착**. 장면 토큰 = 에셋 6장 실물 열람으로 부여, 6장 전부 `leg` 단독이라 어깨·팔은 전 동작 미부착. M-5 해소) |

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
| S19 | 강조 = jointKeys 그룹 위, kp 게이트 통과 → **모양 선(가시 구간만)** / 미달 → **부위 원**, **pulse 1.4s** | **원(bounds circle)만**(`KeypointOverlay.tsx:696-708`). 모양 선 분기 없음. **pulse/Animated 0건**(전 오버레이 소스) | **미검증** (2단위 코드 반영 — `Animated.loop`·선/원 분기 존재. **시뮬이 재생 중 화면을 캡처에 못 담아** 확인 불가 → 실기기 확인 ③) |
| S20 | 재생바 cuedot = 항목 마커, 탭 → 항목 이동 | `VideoCompare.tsx:195,1273` 틱+탭 이동(33-13 D-13) | PASS |
| S21 | 자막 = 목표 선행 카피 (4R#3) | phrasebook 목표-선행 54건(33-13 fda716d~) | PASS |
| S22 | 멈춤 컷 = 결함 텍스트 서술 순간 (불변식 ①: record 실측 창 안) | 틱 = 측정 시점(buildDeductionTicks) 기반이나 멈춤 프레임=재생 위치 — 실측 창 앵커 보장 여부 실기기/시뮬 검증 필요 | 보류 |
| S23 | 음성 중 우상단 **일러스트 동반**(illu-float, 3R 확정 B안) | **없음** — VideoCompare에 일러스트 코드 0건 | **미검증** (3단위 코드 반영 + P-14 기준면 교정. 음성 큐 중에만 표시 → 재생 필요 → 실기기 확인 ③) |

### 일러스트 (A-7)

| # | 스펙 | 현 구현 | 판정 |
|---|---|---|---|
| S24 | 생성 규칙 = 국면 완성 프레임 → i2i(후보 1 스타일 앵커) → 검수 4게이트 | 6동작 에셋 존재(`assets/illustrations/`), 규칙은 33-14 기록. 미완 4동작 fail-closed | PASS (재생성은 deferred) |
| S25 | 불변식 ② 장면-일러스트 일치 — 항목 국면·부위 키잉 | S13과 동일 — 판정 코드 없음, 동작당 1장 | **PASS** (S13 과 동일 판정 코드로 해소) |
| S26 | 렌더 = 3:4 원본 그대로 (M-6) | `DefectIllustration.tsx:63` aspectRatio 3/4 (원본 720×964, cover 미세크롭 ~0.4%) — 코드상 정합. **belle #11 "빈 배경 프레임"의 실체 재현 필요**(에셋 구도 or 다른 표면) | **판정 완료 — 에셋 구도 귀결** (cover 크롭 0.417% = 렌더 경로 정합. 에셋의 82~89%가 빈 스튜디오 배경이라 "빈 프레임"으로 읽힌다. 렌더 억지 수정(`contain` 전환) 안 함 — **에셋 재생성 시 구도 교정**이 답. belle #11 의 1차 원인이던 S13 불일치는 닫힘) |

## B. 목업 밖 구현·표현 결함 (§9-2)

| # | 발견 | 수리 방향 | 판정 |
|---|---|---|---|
| F-3 | 자세 비교(참고하세요) 페어 다른 순간 — ref = 대표 프레임 | **백엔드분 PASS** (quick-260730-l7t) — 근본원인 확정: 앱이 `refFrameIdx / rep.fps` 로 초를 추정해 rep(18fps) ↔ video(9fps) 타임베이스 불일치를 그대로 먹었다. 백엔드가 `userVideoSec`/`refVideoSec` 를 방출한다(`_stamp_time` 과 동일 산출, 기준측은 `ref_display_frame_index` 보정 경유, ref 대응 실패 시 미방출). 3-way lockstep = `analysis.ts` + `contract.md §11.8` + 파이프라인 매퍼. **앱 코드분 PASS**(quick-260730-py1) — `compareFrames.(userIdx|refIdx) / fps` 초 추정 2곳 제거(grep 2→0, 오케스트레이터 재확인), `pickCompareFrames` 가 카드의 `userSec`/`refSec` 를 그대로 운반, 초 미방출 doc 은 실프레임 대신 스켈레톤 폴백. ⚠ **렌더 미검증** — 렌더 가능한 doc 4건이 전부 초 필드 이전 산출이라 참고코너 페어가 확대 크롭과 같은 순간인지 화면으로 확인 불가 → §C-4 재산출 doc 에서 판정 | 백엔드 PASS · 앱 코드 PASS / **렌더 미검증** |
| F-4 | 100점 헤드라인 폰트 이탈 + 카피 어색 | 요약 카피 빌더 `result.tsx:475-505` 계열 — 조립식 제거·길이 통제·재작성 | **PASS** (4단위 렌더 확인 — pdshape 100점 doc 헤드라인 "이 부분은 기준에 맞게 잘 해냈어요" 2줄 이내, 100점 배지와 겹침 0. 근본원인은 앱이 아니라 백엔드였다: `phrasebook.py:223` 이 terminology 전문을 따옴표로 붙여 ~50자를 만들어 `bodyLg 24/700` 상자를 이탈시켰다(belle 인용 문자열과 일치). 뿌리(조립 제거·완성 문장) + 앱(>24자 강등) + `numberOfLines={2}` 3겹) |
| F-5 | 슬라이더 기호 불명 | `GoalGaugeBar.tsx` — 현재 점 마커·허용 밴드에 시각 라벨 없음(a11y 라벨만 `:90`). 라벨 명시 | **미검증** (4단위 코드 반영 — 게이지 기호 라벨. 감점 있는 doc 의 게이지 화면까지 도달 못 함) |
| F-6 | 실기기 음성 무음 | **§9 유력 가설 반증** — `audioCue.ts:93` `playsInSilentMode: true` 이미 설정. 원인 재조사 필요(setAudioModeAsync 호출 시점·플레이어 수명·실기기 조건) | **FAIL 유지 — 원인 미상** (§9 유력 가설 `playsInSilentMode` 는 이미 반증. 4단위 재조사에서 세션 쓰기 순서 경합을 파일:줄로 실증했으나(`expo-video` 두 플레이어가 `muted=true` 로 큐 1회당 최대 4회 세션 재작성) **증거가 반증도 했다** — 양쪽 카테고리가 `.playback` 으로 수렴해 무음 스위치 축을 설명 못 한다. 코드는 후보 완화 1건만 `후보(미확정)` 라벨+되돌리는 법과 함께. **PASS 주장 0.** 후보 5건 순위표 + belle 실기기 분기 절차(첫 분기 = "큐 시점에 영상이 멈추는가") = 4단위 SUMMARY) |
| F-7 | 자세히 보기 "확 내려감" | D-17 앵커 스크롤 — 전환 표현 조정(D-05 순서, Claude 재량) | **미검증** (4단위 코드 반영 — 자세히보기 앵커 전환. 화면 확인 못 함) |
| F-8 | 상시 그룹 마커 | `result.tsx:1484` "skeletonVisible 무관 상시 렌더" — **제거**(D-42), 음성 큐 강조+스켈레톤 토글만 | **PASS** (2단위 렌더확인 — 토글 OFF 에서 마커 0, 마커 자리 탭해도 시트 안 열림 = 안 보이는 탭 0) |

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

## C-2 1단위 기록 (앱 시트, quick-260730-py1 — 2026-07-30)

범위 = S7 블록 요소 + S6 부위 단위 재구성 + F-3 앱분. 나머지 §C-2(S19 pulse · S1~S3 칩 ·
S13 일러스트 · S23 illu-float · S12 어휘 · F-4~F-8)는 다음 단위.

**렌더 확인은 오케스트레이터가 직접 수행**(실행자 도구에 시뮬레이터 없음 — 자기 렌더 검증 금지
구조). 증거 = `.planning/quick/260730-py1-.../sim_evidence/` 스크린샷 11장 + 임시 doc 생성·삭제
스크립트. iPhone 16 Pro 시뮬, Metro 디버그 빌드(OTA 미발행, D-45).

| 케이스 | 판정 | 근거 |
|---|---|---|
| 부위 2감점 = 시트 1개·블록 2개 | **PASS** | 임시 doc(어깨 좌+우)에서 "고칠 것 2/3" 두 블록, 각자 점수·basis·cue·method 보유. belle "무릎 피는 거 하나 어디 갔냐"의 구조 해소 |
| 1감점 부위 = 번호 절 생략 | **PASS** | 킵업 어깨 시트 헤더 "고칠 것 — 왼쪽 어깨(…) (−16.2점)" 번호 없음 |
| 블록 번호 = 전역 마커 번호 | **PASS** | 2·3 부여(1 = 팔꿈치 record). 영상 점·내역 행·블록 단일 소스 |
| basis / method / numnote | **PASS** | 회색·틸 박스 + 맨 뒤 작은 회색. 굵은 문두 `<b>` 문자열 노출 0 |
| 순서·레이아웃·크래시 | **PASS** | 승인 순서 일치, 카드 테두리 내 잘림 0, 시트 열림/닫힘 크래시 0, 이모지 0 |
| **paircap 초 표기** | **미검증** | 렌더 가능 doc 4건 전부 §C-1 이전 산출 → `userVideoSec`/`refVideoSec` 필드 부재(Firestore 조회 확인). 앱은 재계산 없이 폴백(올바름) |
| **F-3 참고코너 페어** | **미검증** | 같은 이유. 코드측 초 추정 제거는 grep 확인 |
| facing · estimatedArea 시트 | **미검증** | 해당 위치·doc 까지 확인 못 함 |
| LogBox 경고 배너 | **미해결** | 결과 화면에서 배너 출현. 디바이스 로그엔 시뮬 오디오·securityd 노이즈만 있어 JS 경고 내용 미확인(Metro stdout = 타 세션 프로세스). 레이아웃·크래시 영향은 관찰되지 않음 |

**한 번 오판했다가 정정한 것(기록):** 임시 doc 이 목록 최상단이 아니어서 킵업 시트를 임시 doc 으로
오인해 "두 감점이 병합됐다 = 결함"으로 판단할 뻔했다. 표시 점수(−16.2)가 그 doc 의 어떤 감점
합과도 맞지 않아 Firestore 를 조회해 doc 을 특정하고 철회했다. **화면만 보고 결함을 단정하지 않고
데이터로 doc 을 특정할 것.**

## C-2 2단위 기록 (마커·강조, quick-260730-szk — 2026-07-30)

범위 = S19 · S1 · S2 · S3 · F-8. 렌더 확인은 오케스트레이터 직접 수행(실행자 도구에 시뮬 없음).
증거 = `.planning/quick/260730-szk-.../sim_evidence/`. iPhone 16 Pro, Metro 디버그 빌드, OTA 미발행.

| 행 | 이전 | 재채점 | 내가 확인한 근거 |
|---|---|---|---|
| **F-8** | FAIL | **PASS** | 토글 OFF에서 두 영상 패널이 완전히 깨끗(스켈레톤·그룹 경계·번호 배지·빨강/주황 점 **전부 0**). 종전에는 `skeletonVisible` 무관 상시 렌더였다. 마커가 있던 자리를 탭해도 시트가 열리지 않음 = **안 보이는 탭 0** |
| **S1** | PARTIAL | **부분 PASS** | 토글 ON에서 2배 확대 확인 — **부위 그룹 경계(원) + 번호 배지 ①②**, 경계 안 멤버 관절에 **개별 빨강 원 나열 0**(흰 스켈레톤 점만). 어깨 그룹이 생겼다(FAIL 사유 해소). ⚠ **병합 배지(`2·3`)는 미확인** — 한 부위 2감점 doc(엘보 60)이 faultZoom 카드 0장이라 도달 못 함 |
| **S3** | PARTIAL | **PASS** | 부위 칩 **3개(팔·어깨·다리) = 감점 3건의 부위와 일치**. 다리 칩 탭 → "다리 부위 상세" 시트가 열리고 1단위 블록 구조(크롭·paircap·onecap·번호 헤더) 그대로 = 회귀 0. 칩 라벨과 시트 제목이 같은 단어 |
| **S19** | FAIL | **미검증** | pulse(1.4s)와 선/원 분기 모두 **재생 구동 실패로 확인 못 함**. 시도: 처음으로 → 재생 탭 후 0.3초 간격 16프레임 연속 캡처 → **16장 전부 동일**(brand 픽셀 0, 영상 평균 불변) = 영상이 진행하지 않았다. 코드는 들어갔으나(`Animated.loop`·`useNativeDriver: true`·`loop.stop()` 존재) **화면으로 못 봤으므로 PASS 주장 안 함** |
| **S2** | PARTIAL | **미검증** | 참고(advisory) 관절이 있는 doc 에 도달하지 못해 점선/실선 구분과 문형 단일화를 확인 못 함 |

**S20·S18 회귀**: 재생바 ①②③ 틱이 그대로 보인다(S20 표면 생존). S18 의 정지·dim·"잠시 멈춤"은
재생이 안 돼 **미확인**.

**1단위 미해결 항목 종결 — LogBox 경고 정체 확인.** Metro 를 직접 잡고 stdout 을 캡처해 읽었다:
`WARN The `allowsFullscreen` prop is deprecated ... Use `fullscreenOptions` instead` **2건**(영상 뷰 2개).
`expo-video` API deprecation 이고 마커·시트와 무관한 **기존 경고**다. 이번에 `Animated` 를 도입했는데
**`useNativeDriver` 계열 신규 경고 0건** — 새 경고를 얹지 않았다.

**소견(이 단위 산출).** `KeypointOverlay.tsx` 에 흰색 hex 리터럴이 **10 → 12** 로 2개 늘었다.
`colors.textWhite` 토큰이 있으므로 app/CLAUDE.md 하드코딩 금지에 어긋난다. 기존 10개도 같은 상태라
파일 전체를 토큰으로 바꾸는 편이 맞지만, 렌더 검증 직전에 SVG 렌더 12곳을 건드리는 위험이 커
**다음 단위에서 일괄 교체** 대상으로 남겼다.

**N-19 판정 보류.** 실행자가 스위프로 찾은 경계 중첩(`arm_extension` 투영이 `shoulder+arm` 복합
부위를 만들어 `shoulder` 부위와 겹침, 10/10 동작)은 **해당 doc 렌더에 도달 못 해 시각 판정 불가**.
2R#1 재발 여부는 §C-4 재산출 doc 에서 판정.

*C-2 2단위 = quick-260730-szk (2026-07-30). 자체 도출 결정 N-1~N-20 = 그 플랜/SUMMARY.*

*스펙 원본 = mockups/index.html 전독. 결정 = 33-CONTEXT.md D-39~D-45. §9 = 33-PHASE-GATE-EVIDENCE.md.*
*C-1 재채점 = quick-260730-l7t (2026-07-30). 자체 도출 결정 L-1~L-11 = 그 플랜 SUMMARY.*
*C-2 1단위 = quick-260730-py1 (2026-07-30). 자체 도출 결정 M-1~M-21 = 그 플랜/SUMMARY.*
