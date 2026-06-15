# 정은지 기준 모션 촬영 가이드 (Reference Capture Guide)

> Phase 14 SC#3 산출물. 정은지 세션의 권장 촬영 조건을 문서화해 기준 모션 등록 정확도가
> **재현 가능**하도록 한다. 본 가이드는 등록 운영자(belle/촬영 담당)를 위한 것이며, 단일
> 영상이 곧 학생 입력과 동일 조건의 v1 baseline 임을 전제로 한다 (D-03).

---

## 0. 핵심 원칙 (먼저 읽을 것)

- **단일시점이 v1 baseline 이다.** reference 도 학생과 **동일하게 단일시점 기준**으로 계산한다
  (D-03). 학생 입력 조건과 reference 조건을 맞춰 비대칭(reference 만 다각도)으로 인한 위양성을
  회피한다.
- **다각도는 권장이되 필수는 아니다.** 다각도 촬영 프로토콜은 본 문서의 **가이드(doc-only)** 로만
  남긴다. 다각도 영상이 없어도 시스템은 graceful 하게 동작하며, 다각도가 부재하면 confidence 를
  낮게 표기한다 (`captureViews=1` → low-confidence flag, SC#4 정합).
- **다각도 직접 촬영은 최후 수단이다.** 단일시점 + (Phase 4) AI 가상 다각도 합성 path 가 정확도
  한계에 부딪힐 때만 다중 시점 직접 업로드를 고려한다 ([[single-camera-first-multi-view-last]] /
  [[camera-angle-ai-single-view-synth]]). 현재 파일럿은 단일시점으로 통일한다 (D-03/D-05).

---

## 1. 시점 수 (Views)

| 항목 | v1 권장 | 비고 |
|------|---------|------|
| 기본 시점 | **단일시점 1개** (정면 우선) | 학생 입력과 동일 조건. `captureViews=1` 로 등록. |
| 다각도 | 선택 (정면 + 측면 권장) | 부재 시 graceful + confidence 낮게 표기. |

- 등록 시 `captureViews` 필드는 측정에 사용한 실제 시점 수다. v1 백필은 모든 reference 를
  `captureViews=1` 로 등록한다 (단일시점 baseline).
- 다각도를 촬영했더라도 v1 분석 경로는 단일시점만 소비한다. 다각도는 향후 path(AI 합성/다중 시점
  융합) 가 활성화될 때를 위한 자료로만 보관한다.

---

## 2. 앵글 (Camera Angle)

폴(pole) 추적·관절 측정 오류와 occlusion 을 최소화하기 위한 권장값:

- **폴 수직 정렬:** 폴이 프레임 안에서 **수직(세로)** 으로 곧게 보이도록 카메라를 정렬한다. 폴이
  기울어 보이면 axis(중심축) 측정과 contact metric 이 흔들린다.
- **카메라 높이:** 동작 구간의 **중심 높이**(대략 골반~가슴 라인)에 카메라를 둔다. 너무 낮거나
  높으면 원근 왜곡으로 관절 각도가 과/소측정된다.
- **거리:** 동작 전 구간에서 **전신 + 폴 전체**가 프레임 안에 들어오는 최소 거리. 클로즈업 금지
  (관절 잘림 = 측정 불가).
- **정면성:** 정면(또는 동작이 가장 잘 드러나는 단일 각도)을 기본으로 한다. 비스듬한 사각(斜角)은
  좌우 occlusion 을 키운다.

---

## 3. 촬영 조건 (Capture Conditions)

- **프레임율 하한:** 분석은 9 fps 로 다운샘플하므로 원본은 **최소 24~30 fps** 이상 권장(빠른 회전/
  전이 구간 모션 보존).
- **해상도 하한:** 전신이 충분한 픽셀로 잡히도록 **720p 이상** 권장. 저해상도는 keypoint
  confidence 를 떨어뜨린다.
- **조명:** 균일하고 충분한 조명. 역광·강한 그림자·과노출 금지(실루엣만 남으면 keypoint 신뢰도 하락).
- **전신 프레이밍:** 머리~발끝 + 손/발 접촉 지점이 동작 전 구간 프레임 안에 유지되어야 한다.
- **폴 전체 가시:** 폴의 상·하단이 프레임 안에 보이도록(중심축 추정 안정화). 폴이 프레임 밖으로
  나가면 수직 폴백(vertical fallback)으로 처리되어 contact 계열 신호가 graceful 하게 비워진다.
- **배경:** 단색·저잡음 배경 권장(인물 분리·추적 정확도 향상).

---

## 4. 단일시점 한계와 confidence 표기 정책 (D-03 / SC#4)

- 단일시점은 깊이(depth)·좌우 occlusion 에서 본질적 한계가 있다. 시스템은 이를 **숨기지 않고**
  confidence 로 표기한다.
- `captureViews=1` (단일시점) 인 reference 는 **low-confidence flag** 를 동반한다. 폴 라인이
  검출되지 않으면(vertical fallback, `line=None`) contact/거리 계열 metric 은 graceful 하게
  `None` + `pole_line_missing` warning 으로 처리되고 예외를 던지지 않는다(SC#4).
- 다각도 영상이 추가되어 측정 신뢰도가 올라가면 confidence 표기도 그에 맞춰 상향한다(향후 path).

---

## 5. 기준 모션 force 필드 caveat (Phase 15 필독, R4-2)

- 본 reference 의 **force 필드(forceDirectionPattern)** 는 `motion_id=None`(fallback/null) 로
  생성된다. 즉 known-reference contact/boost 의미(선택된 referenceMotionId 기반 force semantics)가
  **발동하지 않은** 상태로 등록된다 (REFERENCE_V1_FORCE_CONFIG).
- 따라서 **Phase 15 (Mode 1 비교 경로) 는 reference 가 selected-referenceMotionId force semantics 를
  썼다고 가정하면 안 된다.** reference force 필드는 "reference-v1 pinned config 산출"로 취급한다.
- 학생 `_process` 는 env 기반 preflight gate 를 전달하므로(env flip 시 force-signal confidence 가
  갈라짐), reference 와 학생의 force 산출은 "동일 함수, 다른 config" 임을 인지해야 한다 (R2/R4-2).

---

## 6. 등록 절차 요약 (운영자용)

> Pod GPU 에서 실행. CPU 에서는 NLF/RTMW 가 NaN 으로 발산하므로 반드시 Pod 에서 실행한다.

1. **사전 게이트 (no S3/RTMW)** — credential + 11-doc completeness 확인:

   ```bash
   python backend/scripts/backfill_reference_downstream.py --check-firestore \
     --motions ref-climb,ref-foxtop,ref-foxtop-split,ref-invert,ref-sideway-spin,\
   ref-combo,ref-elbow-twist-sister,ref-kip-up,ref-pdshape,ref-peter-pan,ref-power-spin
   ```

   11개 전부 `activeVersion + angles + anglesJointKeys + anglesFrames` + frame-count sanity 를
   통과해야 exit 0. 하나라도 누락이면 비싼 S3/RTMW 전에 fail-fast 한다 (R2-3/R3-2).

2. **백필 compute (Pod)** — STORED phase4_v1 angles 에서 meanAngles/EXTEND 산출 + RTMW 1회
   재추론으로 bodyNormalizationProfile/forceDirectionPattern 산출. 먼저 `--dry-run` 으로 split
   JSON 을 확인한 뒤 real-run 으로 fixture 를 쓴다(11-id all-or-nothing, R5):

   ```bash
   python backend/scripts/backfill_reference_downstream.py --bucket sunity-motion-pilot-videos \
     --output /workspace/reference-downstream-backfill.json
   ```

3. **ADD-only 시드 (로컬)** — fixture 의 `seedPayload` 만 읽어 4필드 + captureViews 를 merge.
   dry-run 우선:

   ```bash
   cd app
   node scripts/seed-reference-downstream.mjs --input ../reference-downstream-backfill.json --dry-run
   node scripts/seed-reference-downstream.mjs --input ../reference-downstream-backfill.json
   node scripts/seed-reference-downstream.mjs --input ../reference-downstream-backfill.json --verify
   ```

   기본 동작은 누락 필드만 채우는 repair-missing 이고, 기존 valid 필드를 덮어쓰려면 `--force` 를
   준다. `activeVersion`/`angles`/`joints3d`(active pose) 는 어떤 경로에서도 건드리지 않는다(D-02).

---

*Phase: 14-reference-motion-registration · SC#3*
*단일시점 baseline (D-03) · 다각도 doc-only 가이드 · motion_id=None force-config caveat (R4-2)*
