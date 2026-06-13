"""Phase 4 Wave 1 — SynthesisResult dataclass + SynthesisAdapter Protocol +
identify_occlusion_targets + merge_with_temporal (POSE-03 D-08 R1 R2 R6).

Wave 4 추가 (04-04): VideoGenerationAdapter Protocol — Stage 4 영상 생성
plug-in 슬롯. Omni Vertex GA 후 활성화 예정 (D-30, D-31). 현재 stub 만 존재.
파일 하단에 SynthesisAdapter 와 분리된 Protocol 로 추가됨 — 두 어댑터는
입출력 시그니처가 다르므로 별도 인터페이스로 박제.

박제 정신:
  · R2 fix: all-zero array 를 실패 sentinel 로 쓰지 않는다. 실패 → status='failed'
    + joints=None + confidence=None. 성공 → status='applied'|'partial' + joints/conf
    non-None. skipped → joints/conf 가 무엇이든 (보통 None) merge 시도 0.
  · R1 non-scoring 하드월: 본 모듈의 출력은 KeypointReport / aiSynthesisMeta /
    joints3d 에만 흐른다. DTW/kismam/IPSF 의 DTW/kismam 입력 에 절대 mutate 되지
    않는다. 본 파일 어디서도 DTW/kismam/IPSF 입력 행렬 / temporal 의 mask 함수를
    import 하지 않는다 (acceptance grep gate 정합).
  · R6 fix: identify_occlusion_targets 는 (T,17) keypoint confidence + scene flags
    + phase boundaries 를 직접 소비한다. temporal 모듈의 (T,J) 2차원 각도 전용
    mask 함수는 (T,17,3) 형상 전달 시 ValueError 를 raise — 재사용 금지
    (temporal.py:65-66 참조).

연관 계약 (3-way lockstep):
  · sunity_shared.models.SYNTHESIS_WARNING_CODES — public warning enum frozenset.
  · docs/contract.md §9.8 — Phase 4 신설 2개 (ai_synthesis_failed /
    ai_synthesis_partial).
  · app/src/types/analysis.ts SynthesisWarningCode + AiSynthesisMeta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

import numpy as np


@dataclass(frozen=True)
class SynthesisResult:
    """Phase 4 합성 어댑터 단일 반환 타입 (R2 fix — zeros sentinel 폐기).

    필드:
      status: 'applied' / 'partial' / 'skipped' / 'failed' 4-way enum.
        - applied: 모든 대상 관절을 합성 완료. joints/confidence non-None.
        - partial: 일부 관절만 합성 (indeterminate 응답). joints/confidence non-None
          이지만 confidence == 0.0 인 위치가 다수.
        - skipped: 합성 미수행 (SYNTHESIS_ENABLED=0 또는 G4 reference guard 또는
          occlusion mask 가 비어 있음). joints/confidence 보통 None.
        - failed: 어댑터 호출 실패 (API error / parse error / exception). joints/
          confidence 반드시 None.
      joints: (T, 17, 3) float ndarray 또는 None. all-zero array 를 실패 sentinel
        로 쓰지 않는다 (R2 fix).
      confidence: (T, 17) float ndarray 또는 None. 위 joints 와 동일 invariant.
      warnings: raw reason tuple. adapter 측 (예: 'gemini_api_error',
        'gemini_parse_error', 'exception', 'g4_reference_guard') 또는 pipeline 측
        public mapping ('ai_synthesis_failed' / 'ai_synthesis_partial') 누적.
      meta: 감사 정보 dict (modelId / modelVersion / promptHash / framesConsidered /
        framesSynthesized / geminiCalls / framesSkipped / framesFailed / estCostUsd
        등). pipeline 이 aiSynthesisMeta 로 매핑.
    """

    status: Literal["applied", "partial", "skipped", "failed"]
    joints: np.ndarray | None = None
    confidence: np.ndarray | None = None
    warnings: tuple[str, ...] = ()
    meta: dict = field(default_factory=dict)


class SynthesisAdapter(Protocol):
    """가림 관절 합성 어댑터 Protocol (R2 fix — SynthesisResult 반환).

    구현체:
      · GeminiViewReasoner (Stage 1 PRIMARY, gemini_view_reasoner.py)
      · CylindricalMeshAdapter (Stage 3 backend, 04-03 박제 예정)
      · OmniVertexAdapter (Stage 4 Wave 4 stub, 04-04 박제)

    합성 output 은 영구 non-scoring — DTW/kismam/IPSF DTW/kismam 입력 에 절대 흐르지
    않는다 (R1 하드월). pipeline 의 merge_with_temporal 가 KeypointReport 의
    data/confidence 또는 joints3d 표시용 경로로만 합성 좌표를 흘려보낸다.
    """

    def synthesize_occluded_joints(
        self,
        joint_sequence: np.ndarray,      # (T, 17, 3) 1차 RTMW
        confidence_sequence: np.ndarray, # (T, 17) keypoint confidence
        occlusion_mask: np.ndarray,      # (T, 17) bool 합성 대상
        scene_findings: dict,            # scene_finder FindingFlags dict
    ) -> SynthesisResult:
        """합성 시도 → SynthesisResult. (zeros, zeros) tuple / None 반환 금지."""
        ...


def identify_occlusion_targets(
    keypoint_confidence: np.ndarray,
    scene_flags: dict,
    phase_boundaries: list,
    threshold: float = 0.3,
) -> np.ndarray:
    """Phase 4 전용 occlusion target detector — confidence + scene + phase 결합.

    입력:
      keypoint_confidence: (T, 17) float — RTMW keypoint score. 일부 layout 에서
        (T, 17, 3) joints 와 같이 들어올 수 있어 ndim==3 인 경우 마지막 축의
        ``max`` 를 confidence 로 간주한다 (호환).
      scene_flags: scene_finder.find_scene_flags 결과 dict (occlusion_severe /
        camera_angle_problematic 등 boolean flag 다수).
      phase_boundaries: PhaseBoundary list (start_frame_idx / end_frame_idx /
        confidence 등). 빈 list 허용.
      threshold: per-frame per-joint confidence 임계값 (default 0.3). A1 초기
        보수값 — Spike 001 evaluate_4way 후 belle 와 튜닝.

    반환:
      (T, 17) bool ndarray — True = 합성 후보 frame/joint.

    R6 fix:
      본 함수는 temporal 모듈의 (T,J) 2차원 angle 전용 mask 함수를 재사용하지
      않는다. 그 mask 함수는 (T, J=8) 2차원 각도 행렬 전용이고 (T, 17, 3)
      형상 전달 시 ``ValueError: angles 는 (T,J) 2차원이어야 합니다.`` 를
      raise 한다 (temporal.py:65-66). 본 함수는 keypoint confidence (T, 17)
      를 직접 소비한다.

    D-04 트리거 결합 (mask_a | mask_b | mask_c):
      (a) per-frame per-joint confidence < threshold
      (b) scene_flags.occlusion_severe=True → 전체 frame 의 일부 joint cluster
          (sholder/elbow/wrist/hip/knee/ankle, COCO-17 idx 5~16) True
      (c) phase 경계 frame ± 2 frame 신호 (TBD Wave 3 보강, 현재 placeholder)
    """
    conf = np.asarray(keypoint_confidence)
    if conf.ndim == 3:
        # (T, 17, 3) 형상이 confidence 로 잘못 전달된 경우 — 마지막 축 max 로 축약.
        conf = conf.max(axis=-1)
    if conf.ndim != 2:
        raise ValueError(
            "identify_occlusion_targets: keypoint_confidence 는 (T, 17) 2차원 "
            f"필요. 받은 형상={conf.shape}"
        )

    # (a) per-frame per-joint confidence < threshold.
    mask_a = conf < float(threshold)

    # (b) scene_flags.occlusion_severe=True → 본체 joint cluster True (얼굴 keypoint
    # 0~4 는 제외 — 가림 신호 의미 낮음).
    mask_b = np.zeros_like(mask_a, dtype=bool)
    if scene_flags is not None and bool(scene_flags.get("occlusion_severe")):
        mask_b[:, 5:17] = True

    # (c) phase boundary 신호 — Wave 1 시점 placeholder (빈 mask). Wave 3 가
    # PhaseBoundary 와 결합 시 채움. 본 함수가 phase_boundaries 인자를 받되
    # 사용하지 않는 사실을 명시.
    _ = phase_boundaries  # 향후 확장 자리. 사용하지 않음을 명시 (R6 fix 안내).
    mask_c = np.zeros_like(mask_a, dtype=bool)

    return mask_a | mask_b | mask_c


def merge_with_temporal(
    primary_joints: np.ndarray,
    primary_conf: np.ndarray,
    synth_result: SynthesisResult,
    synthesis_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """1차 RTMW + 합성 결과 confidence 가중 병합 (R2 fix — SynthesisResult 입력).

    status 분기 (R2 fix):
      · 'failed' / 'skipped' → primary 그대로 반환. joints/conf 가 None 인 경우
        merge 시도조차 없다.
      · 'applied' / 'partial' → synthesis_mask & (synth_conf > primary_conf) 인
        frame/joint 만 교체.

    R1 non-scoring 하드월:
      본 함수가 반환한 (joints, conf) 는 KeypointReport / aiSynthesisMeta 에만
      흐른다. DTW/kismam/IPSF 의 DTW/kismam 입력 에 절대 흘려보내지 않는다 — pipeline
      측 wiring 책임 (D-18 Anti-Pattern 박제, RESEARCH.md Pitfall 7).

    Anti-Pattern (D-18):
      픽셀 합성 X — Gemini 는 좌표 추정만. 본 함수가 받는 합성 joints 도 좌표
      ndarray 이지 이미지 합성 결과가 아니다.
    """
    primary_joints = np.asarray(primary_joints)
    primary_conf = np.asarray(primary_conf)

    if synth_result.status in ("failed", "skipped"):
        # joints / conf 가 None 이므로 merge 시도조차 하지 않는다 (R2 fix).
        return primary_joints.copy(), primary_conf.copy()

    if synth_result.joints is None or synth_result.confidence is None:
        # status 가 applied/partial 인데 joints/conf 가 None 인 잘못된 어댑터 구현
        # 방어. primary 유지로 graceful — 합성 결과를 신뢰할 수 없다.
        return primary_joints.copy(), primary_conf.copy()

    synth_joints = np.asarray(synth_result.joints)
    synth_conf = np.asarray(synth_result.confidence)
    mask = np.asarray(synthesis_mask, dtype=bool)

    merged_joints = primary_joints.copy()
    merged_conf = primary_conf.copy()

    # synthesis_mask 가 True 이고 합성 confidence 가 primary 보다 높은 위치만 교체.
    # RESEARCH.md Pattern 2 박제.
    better = mask & (synth_conf > primary_conf)
    if better.any():
        merged_joints[better] = synth_joints[better]
        merged_conf[better] = synth_conf[better]

    return merged_joints, merged_conf


# ---------------------------------------------------------------------------
# Phase 4 Wave 4 — Stage 4 영상 생성 plug-in slot (POSE-03 D-30 D-31).
#
# Stage 4 활성화 시 예상 비용: Omni $2-6/10초 영상, Veo 3.1 Vertex Public Preview
# (가격 변동 가능). 조건부 트리거 (occluded frame 만) 전용. D-28 박제.
# 비교 기준선 (PRIMARY 채널): Gemini Vision reasoning $0.12/video.
# ---------------------------------------------------------------------------


@runtime_checkable
class VideoGenerationAdapter(Protocol):
    """Stage 4 영상 생성 어댑터 Protocol (D-30 D-31 stub 박제).

    SynthesisAdapter (좌표 추정) 와 별도 인터페이스 — 입출력 시그니처가 다르다.
    SynthesisAdapter: (T,17,3) joints 입력 → SynthesisResult (좌표) 출력.
    VideoGenerationAdapter: (T,H,W,3) RGB frames + camera delta → (T',H,W,3) 합성
    프레임 출력. 픽셀 합성 결과는 향후 SynthesisResult 로 래핑되어 pipeline 의
    KeypointReport / aiSynthesisMeta 채널로만 흘러야 한다 (R1 non-scoring 하드월).

    구현체 (Wave 4 시점 stub):
      · OmniVertexAdapter (Gemini Omni via Vertex AI, D-30/D-31 — Vertex GA 후 활성화)
      · VeoAdapter (Veo 3.1 Vertex Public Preview, D-27 PoC 대상)

    @runtime_checkable 데코레이터:
      isinstance(obj, VideoGenerationAdapter) 구조적 서브타입 체크 지원.
      test_protocol_structural_subtyping 단위 테스트 게이트 정합 (04-04 Task 2).
    """

    def generate_virtual_view(
        self,
        frames: np.ndarray,                                 # (T, H, W, 3) RGB uint8 입력 프레임
        target_camera_delta: tuple[float, float, float],    # (pan_deg, tilt_deg, roll_deg)
    ) -> np.ndarray:
        """가상 카메라 이동 합성 프레임 (T', H, W, 3) RGB uint8 반환.

        target_camera_delta = (pan_deg, tilt_deg, roll_deg) — 픽셀 합성 X.
        향후 Omni 의 conversational edit prompt 파라미터로 변환될 자리.
        실패/미구현 시 NotImplementedError raise.
        """
        ...


__all__ = [
    "SynthesisResult",
    "SynthesisAdapter",
    "VideoGenerationAdapter",
    "identify_occlusion_targets",
    "merge_with_temporal",
]
