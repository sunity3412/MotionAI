# ADR-0001: PoseEngine 인터페이스 추상화 + RTMW 무료 스택 pivot (2026-06-02)

## Status

**Accepted** — 2026-06-02 (belle 결정). Plan 01-19 (Phase 1 Wave 1) 에서 박제.

본 ADR 은 PoseEngine 인터페이스를 backend-agnostic 으로 박제하고, 운영 백본을
**MediaPipe + MotionBERT → RTMW 133 wholebody (Apache-2.0)** 로 전환한다. NLF/SMPL-X
의존을 영구히 제거하되 R&D 격리 path 는 보존하여 매출 검증 후 옵션 업그레이드를
가능케 한다.

본 시리즈의 첫 ADR — 후속 결정은 ADR-0002 이후로 추가.

## Context

### Phase 1 의 원래 path 와 실측 한계

Phase 1 의 원래 목표는 NLF (3D HMR, 비상업 라이선스) 운영 백본을 **MediaPipe BlazePose
Heavy** 로 교체하고 NLF 는 R&D 격리하는 것이었다 (`01-CONTEXT.md` D-01 ~ D-08).
그러나 다음 사실들이 누적되며 path 가 부적합으로 판정되었다:

- **Plan 06 단독 MediaPipe 점수 평균 22.8** — 단독 MP 2D 만으로는 폴스포츠 측면/
  접힘 자세의 정확도가 무너짐.
- **Plan 08 MP + MotionBERT lifter** 로 평균 81.2 (3.5배 회복) 까지 갔으나
  ref-sideway-spin 64점 (D-15① ≥70 FAIL) — 측면 자세 약점.
- **Plan 09 spike 결정** — AlphaPose 가 라이선스 검사에서 비상업 (SJTU
  Noncommercial) 으로 차단됨 ([[license-blocklist-pose]] 박제). RTMPose (Apache-2.0)
  로 spike 재시작.
- **Plan 10 (RTMPose + MotionBERT) STRONG_PASS** — ref-sideway-spin 72점.
- **Plan 11 5영상 sweep 결과 `gap_too_wide_blocked`** — D-15① 5/5 PASS 였으나
  D-14 (NLF gap ≤5) 2/5 PASS, line/angle 0/5 PASS. 평균 |gap| 14점.
  belle 결정: "갭은 어떻게든 줄여야 한다. Gemini 든 다른 수단이든 가리지 말고" +
  "라인과 각도도 계획에 들어가야 한다." → D-14 강등 거부. Plan 12 (root cause
  debug spike) / Plan 13 (Gemini key moment + criteria extractor) / Plan 14
  (재검증 sweep) 신설.
- **Plan 12 NLF baseline 부적합** — NLF gap baseline 자체가 위양성/위음성을
  내포하여 비교 기준으로 신뢰 불가. IPSF GeometricCriterion 으로 baseline 전환
  결정 ([[judging-baseline-ipsf-code-of-points]] 박제).

### 라이선스 위생 — NLF / SMPL-X 의존 제거 필요성

- **NLF (Neural Localizer Fields)**: Max Planck PS:License 1.0 비상업
  ([[license-blocklist-pose]]). 상업 라이선스 별도 클리어 필요
  (`info@max-planck-innovation.de`).
- **SMPL-X**: 동일 Max Planck 비상업. 상업 license_clearance 미완 상태.
- **AlphaPose**: SJTU Noncommercial Research Only.
- **VideoPose3D**: CC-BY-NC.
- 상업 OK 화이트리스트: **MediaPipe (Apache 2.0)**, **MotionBERT (Apache 2.0)**,
  **HybrIK (MIT)**, **MMPose RTMPose/HRNet (Apache 2.0)**, Microsoft HRNet (MIT).

NLF/SMPL-X 가 제품 코드에 남아 있는 한 라이선스 게이트가 매번 출시를 차단한다.

### belle 지시 (2026-06-02, `/Users/kimtaesung/Downloads/Sunity_v1_개발지시_RTMW무료스택.md`)

> "v1 은 rtmlib RTMW (133 키포인트 wholebody, Apache-2.0) 단일 백본. 3D 는
> 단일 카메라 RTMW3D / monocular 리프팅, 멀티 카메라 Pose2Sim. 체형 정규화는
> SMPL-X 없이 segment 길이 비율. NLF/SMPL-X 의존 영구 제거 — 매출 검증 후
> 옵션 업그레이드. PoseEngine 인터페이스 추상화 필수 — 다운스트림 분석 레이어
> 재작성 금지. 대량 코딩 전 (a) 모듈 구조 (b) PoseEngine 인터페이스 (c) 공통
> 타입 먼저 제안 + 질문."

### Plan 18 (multi-engine averaging spike) on hold

기존 plan 18 은 RTMPose + MotionBERT 와 NLF baseline 두 lift path 의 평균을
spike 하려 했으나, RTMW 단일 wholebody 백본 pivot 으로 두 path 자체가 운영에서
빠진다. **on hold** 처리 (abandoned 아님). RTMW 통합 후 의미 재평가.
([[plan-18-on-hold-rtmw-pivot]] 박제)

## Decision

### D-17 (운영 백본 = RTMW 133 wholebody Apache-2.0)

운영 백본을 **rtmlib RTMW 133 키포인트 wholebody (Apache-2.0)** 로 확정한다.
MediaPipe BlazePose Heavy 는 운영 백본에서 제외 (R&D 비교군 또는 폐기 — Plan 24
에서 처리). D-01 / D-02 / D-03 (MediaPipe variant·API·world landmarks 선택) 을
supersede.

### D-18 (3D 산출)

단일 카메라는 **RTMW3D 또는 monocular 리프팅** (RTMW + MotionBERT 류). 멀티
카메라는 **Pose2Sim** (스포츠 특화 무료). 단일 카메라 우선,
[[single-camera-first-multi-view-last]] 정책에 따라 occlusion/측정오류 해결 시
다각도는 자동 제외.

### D-19 (체형 정규화 — SMPL-X 없이 segment 비율)

체형 정규화 표현은 **SMPL-X 없이 세그먼트 길이 비율** 만으로 구성:
`estimated_height_scale / arm_scale / leg_scale / torso_scale / shoulder_hip_ratio
+ confidence + warnings`. 파라미터형 메시(SMPL-X β / shape_params / betas) 는
**영구히 contract 에 도입하지 않는다**. Plan 01-19 에서 `BodyNormalizationProfile`
dataclass 박제.

### D-20 (원본 RTMW 133 풀 키포인트 저장)

원본 저장은 **RTMW 133 풀 키포인트**. COCO-17 으로 떨궈 저장하지 않는다.
스코어링/분석 계약은 **COCO-17 + 폴 확장 (toe/heel/grip)** 유지 (다운스트림 무수정).
어댑터 `RTMW133ToCOCO17Adapter` + 폴 확장 추출은 Plan 01-21 에서 구현.
`MediaPipe33ToCOCO17Adapter` 는 운영에 사용하지 않음. D-04 supersede.

### D-21 (POSE_ENGINE config 플래그 + body_shape nullable)

엔진 선택 config 플래그 `POSE_ENGINE = RTMW | NLF_SMPLX`. `NLF_SMPLX` 는 R&D 비공개
평가 전용. 기본값 = `RTMW`. `PoseFrame.body_shape` 필드 nullable
(RTMW 운영 path = `None`, NLF_SMPLX R&D path = `BodyNormalizationProfile` 채움).
Plan 01-19 에서 contract 박제.

### D-22 (Confidence = RTMW score)

Confidence 변환식은 RTMW 의 키포인트 score(0~1) 로 매핑 — `confidence = rtmw_score`,
`uncertainty_proxy = 1 - confidence`. MediaPipe 의 visibility/presence 두 필드 가정은
제거 (RTMW 단일 score). D-05 의 사용처·규칙·고객 리포트 정책 (기술 용어 노출 금지)
은 그대로 유지. D-05 변환식만 supersede.

### D-23 (NLF/MediaPipe R&D 격리 위치)

`NlfPoseEngine` 위치 = `backend/research/pose_engines/nlf/` 유지 (제품 패키지
`sunity_shared` 밖). RTMW 는 제품 운영 백본이므로 `sunity_shared/analysis/pose_engines/rtmw/`
로 들어옴 (Plan 01-21 신설). MediaPipe 코드 (Plan 02·03 결과물) 는 폐기 또는 R&D
격리 — 운영 import 경로에서 제거 (Plan 01-24 에서 처리). D-06 / D-07 supersede.

### D-24 (PoseEngine 인터페이스 추상화 필수 — 다운스트림 무수정 보장)

`PoseEngine` Protocol + `PoseFrame` 공통 계약 + `BodyNormalizationProfile` 공통 입력.
모든 다운스트림 분석 레이어 (`features` / `temporal` / `motiondtw` / `kismam` /
`dimensions` / `assemble` / `technique`) 는 **인터페이스에만 의존**. RTMW → NLF →
SMPL-X 도입 시 **구현체만 교체**, 다운스트림 재작성 금지. **본 ADR 의 핵심 약속.**

belle 명시: "대량 코딩 전 모듈 구조 / PoseEngine 인터페이스 / 공통 타입 먼저
제안 + 질문 단계" — 인터페이스 합의 전 RTMW 코드 직진 금지. Plan 01-19 통과가
Plan 01-21 (RTMW 통합) 진입 게이트.

본 결정의 운영 강제 — Plan 01-19 의 `test_pose_engine_protocol_backend_agnostic`
가 `interfaces.py` 의 rtmlib/mediapipe/torch/ultralytics 직접 import 부재를
AST 로 검증 (T-19-01 mitigation).

### D-25 (라이선스 위생 — RTMW 가중치 데이터셋 확인)

RTMW 코드 자체는 Apache-2.0 이지만 **모델 가중치별 학습 데이터 상업 사용 가능
여부 확인 필수** (일부 wholebody 가중치 데이터셋 제약 가능). 고객 대면/상업
배포 전 가중치 라이선스 확정 + 박제. Plan 01-20 에서 `weights_manifest.json`
+ belle 검토 checkpoint. [[license-blocklist-pose]] 유효 (RTMPose OK 박제 그대로).

## Consequences

### Positive

- **라이선스 비용 0원** — RTMW (Apache-2.0) + MotionBERT (Apache-2.0) + Pose2Sim
  (무료). v1 시연/파일럿 진행에 라이선스 게이트 없음.
- **다운스트림 분석 레이어 무수정 보장** — `features`/`temporal`/`motiondtw`/
  `kismam`/`dimensions`/`assemble`/`technique` 7개 모듈은 `PoseEngine` Protocol +
  `PoseFrame` + `BodyNormalizationProfile` 에만 의존. RTMW → NLF_SMPLX 재swap 시
  코드 재작성 없음.
- **매출 검증 후 NLF/SMPL-X 옵션 업그레이드 가능** — `POSE_ENGINE` 플래그만
  swap (D-21). R&D 격리 path 보존되어 비교 평가 가능.
- **IPSF 베이스라인과 정합** — Plan 12 verdict 따라 NLF gap baseline 폐기,
  IPSF GeometricCriterion 으로 baseline 전환 ([[judging-baseline-ipsf-code-of-points]]).
  사람 점수 라벨링 영구 금지는 그대로 유지 ([[analysis-objectivity-no-human-scores]]).
- **Apache-2.0 안전** — 출시 시 라이선스 분쟁 리스크 0.

### Negative

- **기존 plan 01-02/01-03/01-07/01-08/01-10/01-11/01-16/01-17 의 MediaPipe +
  MotionBERT/RTMPose 코드 일부가 R&D 격리 대상** — Plan 01-24 에서 처리. 작성된
  코드는 폐기되지 않고 R&D 측에 보존.
- **Plan 04/05 supersede 필요** — Plan 04 (NLF R&D 격리) 와 Plan 05 (atomic swap)
  의 대상이 NLF → RTMW 로 바뀜. Plan 24 (NLF + MediaPipe + 비선택 3D path R&D
  격리) + Plan 25 (NLF→RTMW atomic swap) 가 supersede.
- **Plan 14 supersede 필요** — Plan 14 (5영상 재검증 sweep, RTMPose+MB+lifter
  baseline) 는 RTMW + IPSF baseline 으로 대상 변경. Plan 23 가 supersede.
- **Plan 18 on hold** — multi-engine averaging spike 의 averaging target 두
  path 가 메인 백본에서 빠짐. RTMW pivot 후 의미 재평가
  ([[plan-18-on-hold-rtmw-pivot]]).
- **RTMW3D / monocular 리프팅 path 결정 미정** — Plan 22 에서 옵션 A (RTMW3D
  직접) vs 옵션 B (RTMW + MotionBERT lifter) belle checkpoint.
- **가중치 라이선스 audit 추가 작업** — Plan 20 에서 `weights_manifest.json`
  작성 + belle 검토 게이트 필요.

## Implementation Plan

Phase 1 신규 plan 표 (Wave 1 ~ Wave 6, gap_closure 마킹):

| Plan | Wave | 책임 |
|------|------|------|
| **01-19** | 1 | **(본 ADR)** PoseEngine Protocol 보강 + `BodyNormalizationProfile` (D-19) + `PoseFrame.body_shape` nullable (D-21) + TS/Python/contract.md 3-way lockstep + ADR-0001 박제. **다운스트림 무수정 게이트** (D-24). |
| 01-20 | 1 | rtmlib RTMW 가중치 라이선스 audit (D-25) + `weights_manifest.json` + belle 검토 checkpoint. |
| 01-21 | 2 | rtmlib RTMW 133 wholebody 통합 + `RTMW133ToCOCO17Adapter` + `POSE_ENGINE` config (D-17/D-20/D-21/D-22/D-24/D-25). |
| 01-22 | 3 | 단일 카메라 3D path 결정 — 옵션 A (RTMW3D 직접) vs 옵션 B (RTMW + MotionBERT lifter) belle checkpoint (D-18). |
| 01-23 | 4 | RTMW vs IPSF GeometricCriterion 5영상 회귀 검증 sweep — Wave 5 진입 게이트 (IPSF tolerance + line/angle 5/5 PASS). Plan 14 supersede. |
| 01-24 | 5 | NLF + MediaPipe + 비선택 3D path R&D 격리 (D-23) + `.samignore` + import 차단 단위 테스트. Plan 04 supersede + 확장. |
| 01-25 | 6 | `pipeline/app.py` + RunPod atomic swap NLF → RTMW (D-08/D-21/D-23/D-24) + belle Pod end-to-end 검증. Plan 05 supersede. |

Plan 01-19 통과 = Plan 01-21 진입 게이트 (D-24 belle 명시).

## Future Reversibility

NLF / SMPL-X 의 상업 라이선스가 클리어되고 (Max Planck Innovation
`info@max-planck-innovation.de` 채널 belle 평행 진행 중) 매출이 정당화되는 시점에
`POSE_ENGINE` config 플래그를 `RTMW` → `NLF_SMPLX` 로 swap 가능. 절차:

1. NLF / SMPL-X 상업 라이선스 클리어 완료 + 박제 (memory 또는 신규 ADR).
2. `backend/research/pose_engines/nlf/` 의 `NlfPoseEngine` 어댑터를 `PoseEngine`
   Protocol 에 맞춰 갱신 (이미 RTMW pivot 시점에 Protocol 호환 유지 확인됨).
3. `POSE_ENGINE=NLF_SMPLX` 플래그로 swap. SMPL-X β 가 필요한 경우 R&D 어댑터
   내부에서만 사용하고, 다운스트림에 노출되는 정규화 표현은 항상
   `BodyNormalizationProfile` (segment 비율) 로 변환되어야 한다 (D-24 핵심 약속).
4. 회귀 검증 — 본 ADR 의 plan 01-23 sweep 절차 재실행.

**다운스트림 무수정 보장 (D-24)** — features/temporal/motiondtw/kismam/dimensions/
assemble/technique 모듈은 본 swap 으로 인해 단 한 줄도 변경되지 않아야 한다.
변경이 필요하면 그것은 D-24 위반이며 새 ADR 로 재논의해야 한다.

## References

### Context / Decisions / Memory

- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-CONTEXT.md` §decisions
  D-17 ~ D-25 (본 결정의 원본 9건).
- `.planning/ROADMAP.md` Phase 1 — RTMW pivot 반영 본문 + Success Criteria 7건.
- `.planning/REQUIREMENTS.md` POSE-01 / POSE-02.
- `/Users/kimtaesung/Downloads/Sunity_v1_개발지시_RTMW무료스택.md` — belle 직접
  지시문 (본 pivot 의 source of truth).
- memory [[rtmw-free-stack-pivot]] — 2026-06-02 belle 결정 박제.
- memory [[plan-18-on-hold-rtmw-pivot]] — multi-engine averaging spike 보류.
- memory [[license-blocklist-pose]] — AlphaPose/NLF/SMPL-X/VideoPose3D 차단.
- memory [[analysis-objectivity-no-human-scores]] — 사람 점수 라벨링 영구 금지.
- memory [[judging-baseline-ipsf-code-of-points]] — IPSF baseline 단일 기준.
- memory [[lifter-mp-motionbert-decision]] — RTMW pivot 으로 재평가 대상.

### Related Plans (Phase 1)

- Plan 01-15 (IPSF baseline 결정) — 사람 점수 라벨링 영구 금지 박제.
- Plan 01-11 sweep verdict `gap_too_wide_blocked` — RTMW pivot 의 직접 트리거.
- Plan 01-12 (NLF baseline 부적합 verdict) — IPSF 전환의 근거.
- Plan 01-04 / 01-05 / 01-14 — supersede 대상 (Plan 01-24/25/23 가 대체).
- Plan 01-18 — on hold (RTMW 통합 후 의미 재평가).

### License References

- https://is.mpg.de/ps/code — NLF/SMPL-X 입수처 (PS:License 1.0 비상업)
- https://smpl-x.is.tue.mpg.de — SMPL-X 공식
- `info@max-planck-innovation.de` — NLF/SMPL-X 상업 라이선스 채널 (belle 평행 진행)
- https://github.com/open-mmlab/mmpose — RTMW (Apache-2.0). 가중치별 학습
  데이터셋 라이선스는 Plan 01-20 audit.

---

*ADR 작성: 2026-06-02 (Plan 01-19 Task 3).*
*형식: Michael Nygard ADR 템플릿 (Title / Status / Context / Decision /
Consequences / Implementation Plan / Future Reversibility / References).*
