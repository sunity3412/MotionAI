"""Phase 4 spike 4-way 비교 평가 metric — 3 axis (a)(b)(c).

각 metric 은 IPSF criterion (ipsf_criteria.py) 위에 산출. 사람 점수 라벨링 X.
입력 = 4-way 각 path 의 RTMW joint output (확정 형식 = sunity_shared.PoseFrame 호환).
출력 = path 별 3 axis 점수 + IPSF criterion 만족 frame rate.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ipsf_criteria import (
    ALL_CRITERIA,
    FULLY_EXTENDED,
    HOLD_TIME,
    PRESENTATION,
    SPIN_ROTATION,
    SPLIT_ANGLE,
    TWIST_ALIGNMENT,
    PHASE4_EVAL_AXIS_MAPPING,
)


# ── 입력 형식 박제 ─────────────────────────────────────────────────────────────
# 4-way 각 path 의 output 을 통일된 dataclass 로 wrap.

@dataclass
class PathOutput:
    """4-way 비교 각 path 의 출력."""
    path_name: str                          # "higgsfield" / "smplx_render" / "magicman" / "rtmw_mirror"
    joint_sequence: np.ndarray              # (T, J, 3) — T frames, J joints, xyz
    confidence_sequence: np.ndarray         # (T, J) — RTMW score 0~1
    fps: float
    video_id: str                           # 정은지 5영상 id 또는 신규
    motion_category: str                    # "invert" / "backbend" / "split" / "spin" / "pose"
    notes: list[str] = field(default_factory=list)  # path 별 처리 메타 (e.g. "synthesized 8 views")


# ── (a) 가상 카메라 앵글 변환 정확도 ────────────────────────────────────────────
# IPSF Page 19: split angle 은 어떤 perspective 에서도 동일해야 함.
# 평가: 영상 내 split frame 의 angle 일관성 (path 들 간 분산).

def axis_a_angle_transform_accuracy(
    outputs: dict[str, PathOutput],
    split_frame_indices: list[int],
) -> dict[str, float]:
    """
    Given split frame 의 angle 측정, 4-way path 간 일관성 평가.

    핵심 IPSF 정의:
    "The split angle must remain the same from all angles/perspectives"
    (CoP 2024-2025 Page 19)

    Returns: path 별 IPSF tolerance 안에 들어가는 frame rate.
    """
    if not split_frame_indices:
        return {p: float("nan") for p in outputs}

    results: dict[str, float] = {}
    for path_name, out in outputs.items():
        pass_count = 0
        for f_idx in split_frame_indices:
            if f_idx >= out.joint_sequence.shape[0]:
                continue
            # 양 무릎-엉덩이 vector 사이 각도 = split angle (3D)
            # joint index 는 RTMW COCO-17 기준 (hip=11/12, knee=13/14)
            hip_l = out.joint_sequence[f_idx, 11]
            hip_r = out.joint_sequence[f_idx, 12]
            knee_l = out.joint_sequence[f_idx, 13]
            knee_r = out.joint_sequence[f_idx, 14]
            v_l = knee_l - hip_l
            v_r = knee_r - hip_r
            cos_t = np.dot(v_l, v_r) / (np.linalg.norm(v_l) * np.linalg.norm(v_r) + 1e-9)
            angle = math.degrees(math.acos(np.clip(cos_t, -1.0, 1.0)))
            # split angle target=180°. FULLY_EXTENDED tolerance ±20°.
            if abs(angle - FULLY_EXTENDED.target) <= FULLY_EXTENDED.tolerance:
                pass_count += 1
        results[path_name] = pass_count / max(len(split_frame_indices), 1)
    return results


# ── (b) AI 가상 뷰 합성 품질 — occlusion 보완 정도 ──────────────────────────────
# IPSF Page 10/94/106: poor presentation (occlusion) = -0.5점 / 발생.
# 평가: confidence < threshold frame rate 가 baseline 대비 얼마나 감소했는지.

def axis_b_synthesis_quality(
    outputs: dict[str, PathOutput],
    baseline_path_name: str = "rtmw_mirror",
    occlusion_threshold: float = 0.3,
) -> dict[str, dict[str, float]]:
    """
    occlusion frame rate 감소율 + 추정 IPSF 감점 절감 점수.

    metric:
    - occlusion_frame_rate: confidence < threshold frame 비율 (path 별)
    - rate_reduction: baseline path 대비 감소율 (%)
    - estimated_ipsf_savings: 보완된 occlusion frame × PRESENTATION.deduction (=0.5)
    """
    if baseline_path_name not in outputs:
        return {p: {"err": float("nan")} for p in outputs}

    baseline = outputs[baseline_path_name]
    baseline_rate = float(
        np.mean(baseline.confidence_sequence < occlusion_threshold)
    )

    results: dict[str, dict[str, float]] = {}
    for path_name, out in outputs.items():
        path_rate = float(np.mean(out.confidence_sequence < occlusion_threshold))
        reduction = (baseline_rate - path_rate) / (baseline_rate + 1e-9) * 100
        # 보완된 occlusion 발생 frame 수 (rough 추정 — 5 frame = 1 occurrence 가정)
        baseline_occ_count = float(np.sum(baseline.confidence_sequence < occlusion_threshold))
        path_occ_count = float(np.sum(out.confidence_sequence < occlusion_threshold))
        compensated_occurrences = max(0.0, (baseline_occ_count - path_occ_count) / 5.0)
        # IPSF Page 10/94/106: poor presentation = -0.5점 / 발생
        ipsf_savings = compensated_occurrences * PRESENTATION.deduction

        results[path_name] = {
            "occlusion_frame_rate": path_rate,
            "rate_reduction_pct": reduction,
            "estimated_ipsf_savings_pts": ipsf_savings,
        }
    return results


# ── (c) RTMW 재추론 pose 정확도 향상 — IPSF criterion 만족도 ────────────────────
# 여러 criterion (fully_extended / twist / hold / spin) 의 frame-wise 만족 여부.

def axis_c_pose_accuracy_lift(
    outputs: dict[str, PathOutput],
    criterion_frames: dict[str, list[int]],  # criterion 이름 → 적용 가능 frame index
) -> dict[str, dict[str, float]]:
    """
    Returns: path 별 criterion 별 만족률 (0~1).

    criterion_frames 예:
      {"fully_extended": [10, 11, 12], "twist_alignment": [40, 41], ...}
    """
    results: dict[str, dict[str, float]] = {p: {} for p in outputs}

    for path_name, out in outputs.items():
        # fully_extended — 양 다리 평균 펴짐
        if "fully_extended" in criterion_frames:
            sats = []
            for f_idx in criterion_frames["fully_extended"]:
                if f_idx >= out.joint_sequence.shape[0]:
                    continue
                hip_l, knee_l, ank_l = (
                    out.joint_sequence[f_idx, 11],
                    out.joint_sequence[f_idx, 13],
                    out.joint_sequence[f_idx, 15],
                )
                v1 = hip_l - knee_l
                v2 = ank_l - knee_l
                cos_t = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
                angle = math.degrees(math.acos(np.clip(cos_t, -1.0, 1.0)))
                sats.append(angle >= FULLY_EXTENDED.fail_threshold)
            results[path_name]["fully_extended"] = float(np.mean(sats)) if sats else float("nan")

        # twist_alignment — 어깨 ↔ 골반 방향 차이 (yaw)
        if "twist_alignment" in criterion_frames:
            sats = []
            for f_idx in criterion_frames["twist_alignment"]:
                if f_idx >= out.joint_sequence.shape[0]:
                    continue
                sho = out.joint_sequence[f_idx, 6] - out.joint_sequence[f_idx, 5]
                pel = out.joint_sequence[f_idx, 12] - out.joint_sequence[f_idx, 11]
                # xz 평면 각도 차이 (yaw)
                ang_sho = math.degrees(math.atan2(sho[2], sho[0]))
                ang_pel = math.degrees(math.atan2(pel[2], pel[0]))
                diff = abs((ang_sho - ang_pel + 180) % 360 - 180)
                # twist 가 detect 되는 yaw 차이 = 30° 이상 (IPSF Page 87 정성적 기준 → 휴리스틱)
                sats.append(diff >= 30.0)
            results[path_name]["twist_alignment"] = float(np.mean(sats)) if sats else float("nan")

        # hold_time, spin_rotation 은 시간축 metric — 별도 frame 단위 검증 X.
        # 박제만: path output 의 fps × time 계산은 path 외부에서 시퀀스 분석 필요.
        results[path_name]["hold_time_capable"] = float(out.fps >= 24.0)  # smoke check
        results[path_name]["spin_rotation_capable"] = float(
            out.joint_sequence.shape[0] / max(out.fps, 1.0) >= 2.0
        )

    return results


# ── Composite — 4-way 비교 종합 ─────────────────────────────────────────────────

@dataclass
class EvalReport:
    video_id: str
    motion_category: str
    axis_a: dict[str, float]
    axis_b: dict[str, dict[str, float]]
    axis_c: dict[str, dict[str, float]]
    notes: list[str] = field(default_factory=list)


def evaluate_4way(
    outputs: dict[str, PathOutput],
    split_frame_indices: list[int],
    criterion_frames: dict[str, list[int]],
    baseline_path_name: str = "rtmw_mirror",
    occlusion_threshold: float = 0.3,
) -> EvalReport:
    """4-way 비교 한 영상 평가."""
    if not outputs:
        raise ValueError("outputs 가 비어있음 — 4-way path 결과 필요")
    sample = next(iter(outputs.values()))
    return EvalReport(
        video_id=sample.video_id,
        motion_category=sample.motion_category,
        axis_a=axis_a_angle_transform_accuracy(outputs, split_frame_indices),
        axis_b=axis_b_synthesis_quality(outputs, baseline_path_name, occlusion_threshold),
        axis_c=axis_c_pose_accuracy_lift(outputs, criterion_frames),
        notes=[
            f"baseline={baseline_path_name}",
            f"occlusion_threshold={occlusion_threshold}",
            "IPSF source: NotebookLM CoP 2024-2025 query 2026-06-13",
        ],
    )
