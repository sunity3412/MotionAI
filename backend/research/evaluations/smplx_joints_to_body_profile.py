"""SMPL-X joints → BodyNormalizationProfile 변환 (pure NumPy, R&D 격리).

HIGH-1 v5 박제 (REVIEWS.md plan_revision v4):
  v4 의 weights-free β→profile 단축 변환은 과학적 fake — SMPL-X β 는
  shapedirs + joint regressor + template mesh 없이 body geometry 산출 불가.
  v5 는 이미 fitted joints 를 입력으로 받아 pure NumPy 변환. CI 단위 테스트
  가능 (합성 joints), Pod 실행은 extract_smplx_joints_from_video.py 가 산출한
  실 joints 입력.

D-02-04 박제: NLF/SMPL-X import 본 파일에서 X — joints array 만 다룸.

본 모듈은 segment 거리 계산 (SMPL-X joint mapping 기반) → torso-relative
ratios → BodyNormalizationProfile 7 필드 산출. Task 3 measurer (RTMW) 와
동일한 ratio 산식 (입력만 SMPL-X joints).

CLI: `python -m backend.research.evaluations.smplx_joints_to_body_profile --joints-dir <path>`
  (debug 용 — 보고서 산출은 compare_body_profile.py 가 담당).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# numpy 는 표준 dep — 즉시 import.
import numpy as np

# sunity_shared 는 backend/shared/python — `python -m` 경로에서 자동 path 아님.
# argparse --help 등 lightweight CLI 가 sunity_shared 부재 환경에서 (CI) 도 작동하도록
# lazy import.
if TYPE_CHECKING:
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile  # noqa: F401


# ── SMPL-X joint name → index mapping (SMPL-X 표준 NJ=55 의 부분집합) ─────
# SMPL-X 공식 spec 기반 — implementor 가 Pod 환경에서 확인 후 박제.
# 본 변환에 필요한 joints 만 정의.
SMPLX_JOINT_INDICES: dict[str, int] = {
    "pelvis": 0,
    "left_hip": 1,
    "right_hip": 2,
    "spine1": 3,
    "left_knee": 4,
    "right_knee": 5,
    "spine2": 6,
    "left_ankle": 7,
    "right_ankle": 8,
    "spine3": 9,
    "neck": 12,
    "left_collar": 13,
    "right_collar": 14,
    "head": 15,
    "left_shoulder": 16,
    "right_shoulder": 17,
    "left_elbow": 18,
    "right_elbow": 19,
    "left_wrist": 20,
    "right_wrist": 21,
}


# ── 변환 함수 ────────────────────────────────────────────────────────────


def _flatten_to_single_frame(joints: np.ndarray) -> np.ndarray:
    """(NJ,3) → 그대로 / (T,NJ,3) → axis=0 mean."""
    if joints.ndim == 2:
        return joints
    if joints.ndim == 3:
        return joints.mean(axis=0)
    raise ValueError(f"joints must be (NJ,3) or (T,NJ,3), got {joints.shape}")


def _distance(joints: np.ndarray, a: str, b: str) -> float:
    ia = SMPLX_JOINT_INDICES[a]
    ib = SMPLX_JOINT_INDICES[b]
    diff = joints[ia] - joints[ib]
    return float(np.linalg.norm(diff))


def _safe_positive(v: float, fallback: float = 1.0) -> float:
    if not math.isfinite(v) or v <= 0.0:
        return fallback
    return v


def smplx_joints_to_body_profile(joints: np.ndarray) -> "BodyNormalizationProfile":
    """SMPL-X joints `(NJ,3)` 또는 `(T,NJ,3)` → BodyNormalizationProfile.

    HIGH-1 v5 핵심: 본 함수는 NLF/SMPL-X import 0 — joints array 만 입력.

    pure NumPy 산식 — Task 3 measurer 와 동일 (좌우 평균 + torso-relative).
    """
    # lazy import — CLI --help 가 sunity_shared 부재 환경에서도 작동.
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    j = _flatten_to_single_frame(np.asarray(joints, dtype=float))

    # segment 거리 (좌우 각각)
    l_upper_arm = _distance(j, "left_shoulder", "left_elbow")
    r_upper_arm = _distance(j, "right_shoulder", "right_elbow")
    l_forearm = _distance(j, "left_elbow", "left_wrist")
    r_forearm = _distance(j, "right_elbow", "right_wrist")
    l_thigh = _distance(j, "left_hip", "left_knee")
    r_thigh = _distance(j, "right_hip", "right_knee")
    l_shank = _distance(j, "left_knee", "left_ankle")
    r_shank = _distance(j, "right_knee", "right_ankle")

    upper_arm = (l_upper_arm + r_upper_arm) / 2
    forearm = (l_forearm + r_forearm) / 2
    thigh = (l_thigh + r_thigh) / 2
    shank = (l_shank + r_shank) / 2

    # torso: shoulder_mid ↔ hip_mid
    l_sh = j[SMPLX_JOINT_INDICES["left_shoulder"]]
    r_sh = j[SMPLX_JOINT_INDICES["right_shoulder"]]
    l_hp = j[SMPLX_JOINT_INDICES["left_hip"]]
    r_hp = j[SMPLX_JOINT_INDICES["right_hip"]]
    shoulder_mid = (l_sh + r_sh) / 2
    hip_mid = (l_hp + r_hp) / 2
    torso = float(np.linalg.norm(shoulder_mid - hip_mid))

    shoulder_width = float(np.linalg.norm(l_sh - r_sh))
    hip_width = float(np.linalg.norm(l_hp - r_hp))

    # ratios (Task 3 measurer 와 동일 산식)
    arm_scale = (upper_arm + forearm) / torso if torso > 0 else float("nan")
    leg_scale = (thigh + shank) / torso if torso > 0 else float("nan")
    torso_scale = 1.0
    shoulder_hip_ratio = (
        shoulder_width / hip_width if hip_width > 0 else float("nan")
    )
    estimated_height_scale = (
        (arm_scale if math.isfinite(arm_scale) else 0.0)
        + (leg_scale if math.isfinite(leg_scale) else 0.0)
        + 1.0
    ) / 3.0

    # MEDIUM-2 v5 정합: strictly positive 보장.
    arm_scale = _safe_positive(arm_scale, 1.0)
    leg_scale = _safe_positive(leg_scale, 1.0)
    torso_scale = _safe_positive(torso_scale, 1.0)
    shoulder_hip_ratio = _safe_positive(shoulder_hip_ratio, 1.0)
    estimated_height_scale = _safe_positive(estimated_height_scale, 1.0)

    return BodyNormalizationProfile(
        estimated_height_scale=estimated_height_scale,
        arm_scale=arm_scale,
        leg_scale=leg_scale,
        torso_scale=torso_scale,
        shoulder_hip_ratio=shoulder_hip_ratio,
        confidence=1.0,  # SMPL-X fitted joints 가정
        warnings=[],
    )


# ── joints loader ───────────────────────────────────────────────────────


def load_smplx_joints(path: Path) -> dict[str, np.ndarray]:
    """SMPL-X joints dir → {video_name: joints np.ndarray}.

    각 `<video>.json` 파일은 joints array (list of lists) 형태로 산출 (Pod
    extract_smplx_joints_from_video.py 산출).

    HIGH-3 v3 graceful: 비존재 dir / 빈 dir → {} (raise X).
    """
    if not path.exists() or not path.is_dir():
        return {}
    result: dict[str, np.ndarray] = {}
    for json_path in sorted(path.glob("*.json")):
        try:
            raw = json.loads(json_path.read_text(encoding="utf-8"))
            arr = np.asarray(raw, dtype=float)
            video_name = json_path.stem
            result[video_name] = arr
        except Exception:  # noqa: BLE001 — R&D throwaway
            continue
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SMPL-X joints → BodyNormalizationProfile 변환 (debug CLI, HIGH-1 v5)."
    )
    parser.add_argument(
        "--joints-dir",
        type=Path,
        required=True,
        help="SMPL-X joints JSON dir.",
    )
    args = parser.parse_args(argv)

    joints_dict = load_smplx_joints(args.joints_dir)
    out: dict[str, dict] = {}
    for video, joints in joints_dict.items():
        profile = smplx_joints_to_body_profile(joints)
        out[video] = {
            "estimated_height_scale": profile.estimated_height_scale,
            "arm_scale": profile.arm_scale,
            "leg_scale": profile.leg_scale,
            "torso_scale": profile.torso_scale,
            "shoulder_hip_ratio": profile.shoulder_hip_ratio,
            "confidence": profile.confidence,
            "warnings": profile.warnings,
        }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
