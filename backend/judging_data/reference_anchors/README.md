# 기준(reference) 각도 앵커 주석 — 스키마 계약 + 주석 절차

**소유 코드:** `backend/shared/python/sunity_shared/analysis/reference_anchors.py`
**소비 코드:** `backend/shared/python/sunity_shared/analysis/fault_zoom.py` (각도 베이크 S8)
**성격:** **display 전용, 채점 무접촉 (D-44).** 이 디렉터리의 어떤 값도
`deductionBreakdown`·veto·게이트에 유입되지 않는다. 점수는 이 파일들과 무관하게 동일하다.

## 왜 이 데이터가 필요한가

승인 목업 7R (`mockups/index.html` 780-814행, "A-5(33-12) 구현 지시" 4R 확정):

> 기준 라이브러리는 **11개 동작으로 고정**(phase4_v1 pinned)이라, 기준 쪽 각도 앵커
> (어깨·팔꿈치·엉덩이 방향점)는 **기준 모션당 1회 수동 주석**으로 달아 앵커 데이터로
> 저장하면 끝 — A-5 는 이 저장된 앵커를 읽어 그리기만 하면 돼요. 학생 쪽은 지금처럼
> conf 게이트 통과 keypoint 자동 드로잉.

학생 패널은 keypointReport 12관절(32-14)로 각도 기하가 자동 성립한다. 기준 패널은
`phase4_v1` = **legacy 8관절**(shoulder/hip/knee/hand 좌우)이라 `elbow`·`ankle` 이
아예 없다. 그 부재 관절을 런타임에 추정하면 환각 드로잉이 되므로, 사람이 1회 판정한
**대입 선언**을 데이터로 둔다.

## 왜 정적 좌표가 아니라 "관절 대입 선언"인가 (L-5)

정적 좌표(예: `left_elbow: [147, 222]`)는 **주석한 그 프레임에서만** 유효하다. 그런데
기준 패널의 표시 프레임은 DTW 실측 순간(S11)이라 **학생마다 다르다**. 주석 프레임과
표시 프레임이 어긋나면 좌표가 몸 밖에 뜬다 — 목업 6R 기각과 같은 실패 모드
("각·호가 몸통 위쪽에 떠 보임").

대입 선언(`left_elbow: left_hand`)은 실 keypoint 를 따라가므로 **어느 프레임에서도**
유효하다. 부수 효과로 임의 픽셀을 지시하는 경로 자체가 없어져 환각 드로잉이
원리적으로 0이다 (T-l7t-01 Tampering mitigate).

## 스키마

파일 = `backend/judging_data/reference_anchors/{motion_id}.yaml`

```yaml
motion: ref-power-spin          # 필수. 파일명(stem)과 일치해야 함 — 불일치 = 전체 드롭
annotated: "2026-07-30"         # 주석 날짜
source: "무엇을 열어 확인했는지"  # 사람이 실제로 본 근거 (프레임/자산 경로 명시)
criteria:
  angle_vs_reference__left_shoulder:      # criterion id (감점 record 의 criterion)
    joint_substitutions:
      left_elbow: left_hand               # 단일 관절 대입
      # 또는:
      # left_ankle: {midpoint: [left_knee, left_hip]}   # 두 관절 중점 대입
    note: "근거 — 필수"                    # 근거 없는 주석 금지
```

### 검증 규칙 (로더가 강제)

| 위반 | 결과 |
|---|---|
| 파일 미존재 / 빈 파일 / yaml 파싱 실패 / PyYAML 미설치 | `{}` (예외 0) |
| `motion` 필드 ≠ 파일명 | **전체 드롭** (오배치 주석 유입 차단) |
| `criteria` 가 dict 아님 | 전체 드롭 |
| criterion 항목이 dict 아님 / `note` 공백 / `joint_substitutions` 부재 | **그 항목만 드롭** + 경고 로그 |
| 관절명이 `keypoint_frame._KEYPOINT_NAMES` 밖 (오타) | **그 대입만 드롭**, 나머지 유지 |

허용 관절명 = `left/right_shoulder`, `left/right_hip`, `left/right_knee`,
`left/right_hand`, `left/right_ankle`, `left/right_elbow` (12개, `keypoint_frame` 단일 출처).

### 런타임 우선순위

1. 기준 report 가 그 관절을 **신뢰 좌표(conf ≥ 0.5)로 보유** → report 우선. 대입은 무시.
2. 부재/저신뢰 → 대입 선언 경유. 대입 소스 관절도 conf 게이트를 통과해야 한다.
3. 둘 다 실패 → `None`. 그러면 **양쪽 패널 모두 각도를 그리지 않는다**(대칭 게이트 —
   한쪽만 그리면 M-4 비대칭 재발). 인접 관절로 대체하지 않는다 (L-6).

## 잔여 모션 주석 절차

주석 값을 채우려면 **기준 프레임 실물을 열어봐야** 한다 (S3 다운로드 + 프레임 추출).
로컬에는 기준 영상이 없으므로 이 작업은 **§C-4 Pod 재스위프에 이관**되어 있다(L-9).
절차:

1. 기준 영상 S3 키 확인 — `reference/{motion_id}.mp4` (버킷 `sunity-motion-pilot-videos`).
2. 파이프라인과 동일 그리드로 프레임 추출 — `FfmpegFrameExtractor(target_fps=9.0, max_side=640)`.
3. 그 모션 doc 의 `windowMedianAngleDeltas.sourceFrameIndices.reference` 창(= DTW 실측
   순간) 중심 프레임을 골라 **확대 열람**한다. 표시 프레임은 학생마다 달라지므로
   "이 국면에서 대입이 성립하는가"를 판정하는 것이지 좌표를 적는 것이 아니다.
4. 부재 관절(`elbow`/`ankle`)의 대입 유효성을 판정한다:
   - `elbow ← hand`: **팔이 그 국면에서 펴져 있어야** 성립. 굽어 있으면 넣지 않는다.
   - `ankle ← knee`: **다리가 그 국면에서 펴져 있어야** 성립.
   - 애매하면 **넣지 않는다** (fail-closed — 각도 미표시가 틀린 각도보다 낫다).
5. yaml 에 기록. `source` 에 무엇을 열었는지, `note` 에 판정 근거(추적 좌표·내각 추정)를
   숫자로 남긴다. 관찰과 다른 주석 날조 금지.
6. 검증 = 그 모션의 criterion 카드 PNG 를 실제로 생성해 **열어보고** 선이 팔/옆구리를
   따라가는지 승인 자산(`belle_shoulder_pair_dtwmatch_r7.png`)과 나란히 대조한다.

## 등재 동작 체크리스트

**단일 출처 = `backend/judging_data/criteria/*.yaml` glob** (아래 목록은 그 glob 산출의
스냅샷 — 하드코딩이 아니다. 동작이 추가되면 glob 에 자동 등장한다).

```bash
python3 -c "import pathlib; print(*sorted(p.stem for p in \
pathlib.Path('backend/judging_data/criteria').glob('*.yaml')), sep='\n')"
```

2026-07-30 스냅샷 (10 동작):

| # | motion_id | 앵커 주석 |
|---|-----------|----------|
| 1 | `ref-climb` | 미주석 → §C-4 |
| 2 | `ref-elbow-twist-sister` | 미주석 → §C-4 |
| 3 | `ref-foxtop` | 미주석 → §C-4 |
| 4 | `ref-foxtop-split` | 미주석 → §C-4 |
| 5 | `ref-invert` | 미주석 → §C-4 |
| 6 | `ref-kip-up` | 미주석 → §C-4 |
| 7 | `ref-pdshape` | 미주석 → §C-4 |
| 8 | `ref-peter-pan` | 미주석 → §C-4 |
| 9 | `ref-power-spin` | **주석 완료** (승인 7R 근거, `angle_vs_reference__left_shoulder`) |
| 10 | `ref-sideway-spin` | 미주석 → §C-4 |

기준 라이브러리 자체는 11개 동작(phase4_v1 active)이며 `ref-combo` 등 criteria 미등재
동작은 채점 criterion 이 없어 criterion 카드도 생기지 않는다 → 앵커 주석 대상 아님.

**미주석 = 조용한 누락이 아니다.** 그 모션의 어깨/무릎/팔꿈치 계열 criterion 카드는
각도 표시 없이 기존 원 마커로 폴백한다 (양측 대칭). 잔여 9모션 주석 값 채우기 =
`33-G-MOCKUP-DIFF.md` §C-4 이관 항목.
