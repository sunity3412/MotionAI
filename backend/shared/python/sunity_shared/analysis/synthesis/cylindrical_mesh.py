"""Stage 3' CylindricalMeshAdapter — Spike 002b VALIDATED-SKELETON 이관.

SynthesisAdapter Protocol (D-18 SECONDARY). license: trimesh MIT + pyrender MIT +
numpy BSD. SMPL-X 의존 0 (D-20 박제). Wave 3a = mesh build + render artifact
smoke gate (정확도 주장 0). 실 RTMW 재추론 → Wave 3b (test_evaluate_4way.py
@integration).

박제 정신 (POSE-03 D-07 / D-18 / D-20 / R1 / R2):
  · SynthesisAdapter Protocol (04-01 신설) 의 2번째 구현체 — GeminiViewReasoner
    (PRIMARY) 와 동일 시그너처. SynthesisResult 반환 — None / (zeros, zeros)
    tuple sentinel 영구 금지 (R2 fix).
  · G4 가드 (최우선): scene_findings["is_reference"]=True → SynthesisResult(
    status="skipped", warnings=("g4_reference_guard",)) — defense-in-depth
    (pipeline + adapter 양측, 04-CONTEXT code_context).
  · R1 non-scoring 하드월: 본 어댑터의 합성 결과는 KeypointReport +
    aiSynthesisMeta + joints3d 흐름에만 흐른다. DTW/kismam/IPSF 채점 입력 행렬에
    절대 mutate 되지 않는다 (RESEARCH Pitfall 7).
  · Wave 3a placeholder boost (+0.15) 는 pipeline 연결 검증용 임시값이며 scoring
    promote 근거가 아니다 (calibration-source-hard-gate). 실 RunPod 재추론
    결과만 scoring gate 진입 허용 — Wave 3b (test_evaluate_4way.py @integration).

Spike 002b 출처:
  · .planning/spikes/002b-cylindrical-mesh-virtual-render/mesh_builder.py
  · .planning/spikes/002b-cylindrical-mesh-virtual-render/render.py
"""
# SMPL-X 절대 금지 — D-20 박제 (belle 명시 완전 최후의 보류, $7,300/yr)
# RTMW 3D scoring matrix mutate 0 — 합성 결과는 KeypointReport + aiSynthesisMeta 만 영향 (RESEARCH Pitfall 7, R1 non-scoring 하드월)
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import numpy as np
import trimesh

# EGL 초기화 순서 박제 — virtual_renderer (pyrender import) 보다 먼저 (RESEARCH
# Pitfall 3). virtual_renderer 모듈 상단도 동일 setdefault 박제이지만,
# import 순서 보호 목적으로 여기에서도 한 번 더 명시.
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")

from sunity_shared.analysis.synthesis.interfaces import SynthesisResult
from sunity_shared.analysis.synthesis.virtual_renderer import (
    PYRENDER_AVAILABLE,
    render_12_views_safe,
)


log = logging.getLogger(__name__)


# ── RTMW COCO-17 joint index 박제 (Spike 002b mesh_builder.py 그대로) ──────────
NOSE = 0
EYE_L, EYE_R = 1, 2
EAR_L, EAR_R = 3, 4
SHO_L, SHO_R = 5, 6
ELB_L, ELB_R = 7, 8
WRI_L, WRI_R = 9, 10
HIP_L, HIP_R = 11, 12
KNE_L, KNE_R = 13, 14
ANK_L, ANK_R = 15, 16


# ── Segment 박제 (13 body part) ──────────────────────────────────────────────
@dataclass(frozen=True)
class Segment:
    name: str
    joint_a: int                  # 시작 joint
    joint_b: int                  # 끝 joint
    radius: float                 # cylinder radius (m, 평균 성인 기준)


SEGMENTS: list[Segment] = [
    # head : ear_center → nose 방향 박제 (간단화)
    Segment("head", EYE_L, NOSE, radius=0.10),
    # torso : 어깨 중심 → 골반 중심 (별도 처리)
    Segment("torso", SHO_L, HIP_L, radius=0.15),  # placeholder — _add_torso 에서 실제 처리
    # arms
    Segment("upper_arm_l", SHO_L, ELB_L, radius=0.05),
    Segment("lower_arm_l", ELB_L, WRI_L, radius=0.04),
    Segment("upper_arm_r", SHO_R, ELB_R, radius=0.05),
    Segment("lower_arm_r", ELB_R, WRI_R, radius=0.04),
    # legs
    Segment("upper_leg_l", HIP_L, KNE_L, radius=0.08),
    Segment("lower_leg_l", KNE_L, ANK_L, radius=0.06),
    Segment("upper_leg_r", HIP_R, KNE_R, radius=0.08),
    Segment("lower_leg_r", KNE_R, ANK_R, radius=0.06),
]


def _cylinder_between(
    a: np.ndarray,
    b: np.ndarray,
    radius: float,
    segments_circle: int = 12,
) -> trimesh.Trimesh:
    """두 점 사이를 잇는 cylinder mesh 생성."""
    direction = b - a
    length = float(np.linalg.norm(direction))
    if length < 1e-6:
        return trimesh.Trimesh()
    midpoint = (a + b) / 2
    # default cylinder 는 z 축 정렬
    cyl = trimesh.creation.cylinder(radius=radius, height=length, sections=segments_circle)
    # z 축 → direction 으로 회전
    z = np.array([0.0, 0.0, 1.0])
    direction_n = direction / length
    axis = np.cross(z, direction_n)
    axis_norm = np.linalg.norm(axis)
    if axis_norm > 1e-6:
        axis = axis / axis_norm
        angle = float(np.arccos(np.clip(np.dot(z, direction_n), -1.0, 1.0)))
        rot = trimesh.transformations.rotation_matrix(angle, axis)
        cyl.apply_transform(rot)
    cyl.apply_translation(midpoint)
    return cyl


def build_humanoid_mesh(joints: np.ndarray) -> trimesh.Trimesh:
    """(17, 3) RTMW COCO-17 3D joint → cylindrical humanoid mesh 박제.

    Spike 002b mesh_builder.py 이관. SMPL-X 의존 0 (D-20).

    Returns:
        trimesh.Trimesh: 합쳐진 single mesh
    """
    if joints.shape != (17, 3):
        raise ValueError(f"joints shape (17,3) 필요, got {joints.shape}")

    parts: list[trimesh.Trimesh] = []

    # head — ear center 기준 sphere 박제 (cylinder 보다 자연스러움)
    ear_center = (joints[EAR_L] + joints[EAR_R]) / 2
    head_top = ear_center + np.array([0.0, 0.18, 0.0])
    parts.append(_cylinder_between(ear_center, head_top, radius=0.10))

    # torso — 어깨 중심 → 골반 중심 (대형 cylinder)
    sho_center = (joints[SHO_L] + joints[SHO_R]) / 2
    hip_center = (joints[HIP_L] + joints[HIP_R]) / 2
    parts.append(_cylinder_between(sho_center, hip_center, radius=0.15))

    # 나머지 segment
    for seg in SEGMENTS:
        if seg.name in ("head", "torso"):
            continue  # 위에서 박제 완료
        cyl = _cylinder_between(joints[seg.joint_a], joints[seg.joint_b], radius=seg.radius)
        parts.append(cyl)

    # joint sphere — 어깨/팔꿈치 등 joint marker (시각화 도움)
    for j in [SHO_L, SHO_R, ELB_L, ELB_R, HIP_L, HIP_R, KNE_L, KNE_R]:
        sphere = trimesh.creation.icosphere(subdivisions=2, radius=0.06)
        sphere.apply_translation(joints[j])
        parts.append(sphere)

    combined = trimesh.util.concatenate(parts)
    return combined


# ── Wave 3a placeholder boost 박제 ─────────────────────────────────────────────
_PLACEHOLDER_CONFIDENCE_BOOST: float = 0.15


class CylindricalMeshAdapter:
    """Stage 3' SECONDARY 경로 합성 어댑터 (D-18) — Spike 002b VALIDATED-SKELETON 이관.

    SynthesisAdapter Protocol 구현체. GeminiViewReasoner (PRIMARY) 가 indeterminate
    반환하거나 비용 손절 발동 시 mesh render fallback 으로 occlusion 보완 정확도를
    추가로 확보한다.

    Wave 3a 단계 (현재):
      mesh build + 12-view render artifact smoke gate 만 박제. _rerun_rtmw_on_views
      는 primary joints 그대로 반환 + +0.15 boosted confidence 임시 반환 (Wave 3b
      실 구현 전 pipeline 연결 검증용). 정확도 주장 0.

    Wave 3b 단계 (test_evaluate_4way.py @integration, RunPod 필요):
      12-view render artifact → 실 RTMW 재추론 → PathOutput wrapping →
      evaluate_4way axis_b rate_reduction_pct 실 검증 (calibration-source-hard-gate).

    R1 non-scoring 하드월:
      synthesize_occluded_joints 반환값은 KeypointReport + aiSynthesisMeta +
      joints3d 흐름에만 흐른다. DTW/kismam/IPSF 채점 입력 행렬에 절대 mutate
      되지 않는다 (RESEARCH Pitfall 7).
    """

    # TODO(Wave 3b): _rerun_rtmw_on_views 에 실제 RTMW 추론 파이프라인 연결.
    # +0.15 boosted confidence 는 pipeline 연결 검증용 임시값이며 scoring promote
    # 근거 아님 (calibration-source-hard-gate).

    def __init__(
        self,
        *,
        render_width: int = 256,
        render_height: int = 256,
    ) -> None:
        self._render_width = render_width
        self._render_height = render_height

    def synthesize_occluded_joints(
        self,
        joint_sequence: np.ndarray,      # (T, 17, 3) 1차 RTMW
        confidence_sequence: np.ndarray, # (T, 17) keypoint confidence
        occlusion_mask: np.ndarray,      # (T, 17) bool 합성 대상
        scene_findings: dict,            # scene_finder FindingFlags dict (또는 빈 dict)
    ) -> SynthesisResult:
        """Stage 3' mesh render 합성 — Wave 3a smoke 단계 (정확도 주장 0).

        처리 흐름:
          (1) G4 가드: scene_findings["is_reference"]=True → status="skipped"
              + warnings=("g4_reference_guard",) (zeros sentinel 금지, R2 fix).
          (2) 합성 필요 frame 없음(mask 전부 False) → status="skipped" 조기 반환.
          (3) occluded frame 별: build_humanoid_mesh → render_12_views_safe →
              _rerun_rtmw_on_views (Wave 3a placeholder, Wave 3b 실 구현).
          (4) Wave 3a placeholder: status="applied" + primary joints +
              boosted confidence (occluded 위치 +0.15 cap 1.0) + meta
              {synthesisPath: "cylindrical_smoke_placeholder"} — scoring promote
              근거 아님 (R1 non-scoring 하드월).

        예외 (Wave 3a 단계 모든 except):
          log.exception → SynthesisResult(status="failed",
          warnings=("exception",)) — D-07 graceful degrade, zeros sentinel 금지.
        """
        # (1) G4 가드 — defense-in-depth 박제. pipeline 측 _call_synthesis_adapter
        # 가 이미 차단하지만, 04-CONTEXT code_context 정신대로 adapter 자체에도
        # 명시.
        try:
            scene = scene_findings or {}
            if scene.get("is_reference", False):
                log.info(
                    "CylindricalMeshAdapter — is_reference=True G4 guard skip "
                    "(reference 영상은 합성 대상 0, occlusion FP 가드)"
                )
                return SynthesisResult(
                    status="skipped",
                    warnings=("g4_reference_guard",),
                )

            mask = np.asarray(occlusion_mask, dtype=bool)
            if not mask.any():
                # (2) 비용 0 조기 종료 — 합성 대상 frame 없음.
                return SynthesisResult(status="skipped")

            primary_joints = np.asarray(joint_sequence)
            primary_conf = np.asarray(confidence_sequence)

            if primary_joints.ndim != 3 or primary_joints.shape[1:] != (17, 3):
                raise ValueError(
                    "joint_sequence 형상 (T, 17, 3) 필요, "
                    f"got {primary_joints.shape}"
                )
            if primary_conf.shape != primary_joints.shape[:2]:
                raise ValueError(
                    "confidence_sequence 형상 (T, 17) 필요, "
                    f"got {primary_conf.shape}"
                )
            if mask.shape != primary_conf.shape:
                raise ValueError(
                    "occlusion_mask 형상 (T, 17) 필요, "
                    f"got {mask.shape}"
                )

            # (3) occluded frame 별 mesh build + 12-view render (Wave 3a smoke).
            # frames_synthesized 메타 카운터 박제. 실제 RTMW 재추론은 Wave 3b.
            frames_occluded: list[int] = np.where(mask.any(axis=1))[0].tolist()
            framesSynthesized = 0
            for f_idx in frames_occluded:
                frame_joints = primary_joints[f_idx]
                # build_humanoid_mesh — Spike 002b 이관 (SMPL-X 미사용).
                mesh = build_humanoid_mesh(frame_joints)
                # render_12_views_safe — PYRENDER_AVAILABLE False 시 dummy 12장.
                _views = render_12_views_safe(
                    mesh,
                    width=self._render_width,
                    height=self._render_height,
                )
                if len(_views) != 12:
                    raise RuntimeError(
                        f"render_12_views_safe 12장 기대, got {len(_views)}"
                    )
                framesSynthesized += 1

            # (4) Wave 3a placeholder — _rerun_rtmw_on_views 실 구현은 Wave 3b.
            boosted_joints, boosted_conf = self._rerun_rtmw_on_views(
                primary_joints=primary_joints,
                primary_conf=primary_conf,
                occlusion_mask=mask,
            )

            meta: dict[str, Any] = {
                "synthesisPath": "cylindrical_smoke_placeholder",
                "adapter": "CylindricalMeshAdapter",
                "renderBackend": "pyrender_egl" if PYRENDER_AVAILABLE else "dummy_fallback",
                "framesConsidered": int(primary_joints.shape[0]),
                "framesSynthesized": int(framesSynthesized),
                "viewCount": 12,
                "wave": "3a_smoke_placeholder",
                "notes": (
                    "Wave 3a placeholder boost (+0.15) — scoring promote 근거 아님. "
                    "실 RTMW 재추론 + accuracy gate 는 Wave 3b @integration."
                ),
            }
            return SynthesisResult(
                status="applied",
                joints=boosted_joints,
                confidence=boosted_conf,
                meta=meta,
            )

        except Exception:  # noqa: BLE001 — D-07 graceful degrade 박제
            log.exception("CylindricalMeshAdapter 합성 실패 — graceful degrade")
            return SynthesisResult(
                status="failed",
                warnings=("exception",),
            )

    # ── private helpers ──────────────────────────────────────────────────────

    def _rerun_rtmw_on_views(
        self,
        *,
        primary_joints: np.ndarray,
        primary_conf: np.ndarray,
        occlusion_mask: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Wave 3a placeholder — primary joints 그대로 + boosted conf 임시 반환.

        Wave 3b 실 구현 예정:
          12-view render artifact 를 RunPod RTMW 추론기에 재투입 → 12 view 별
          joint 추정치 → confidence-weighted aggregate → SynthesisResult.joints/
          confidence 산출. 이 때 산출된 confidence 만 scoring gate 진입 가능.

        Wave 3a placeholder:
          primary joints 변경 없음. occlusion_mask=True 위치에서만 confidence
          +0.15 (cap 1.0) 적용 — pipeline 연결 검증용 임시값이며 scoring promote
          근거 아님 (calibration-source-hard-gate, R1 non-scoring 하드월).
        """
        log.warning(
            "RTMW rerun not wired — Wave 3b RunPod task 에서 구현 예정 "
            "(test_evaluate_4way.py @integration 확인)"
        )
        boosted_joints = primary_joints.copy()
        boosted_conf = primary_conf.copy()
        # occluded 위치만 boost — non-occluded 는 그대로.
        mask = np.asarray(occlusion_mask, dtype=bool)
        if mask.any():
            boosted_conf[mask] = np.minimum(
                boosted_conf[mask] + _PLACEHOLDER_CONFIDENCE_BOOST,
                1.0,
            )
        return boosted_joints, boosted_conf


__all__ = [
    "CylindricalMeshAdapter",
    "build_humanoid_mesh",
    "Segment",
    "SEGMENTS",
]
