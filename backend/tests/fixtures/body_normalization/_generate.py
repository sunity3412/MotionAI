"""5종 synthetic PoseFrame fixture 생성기 (HIGH-2 v1→v2 + MEDIUM-3 v5 박제).

멱등 (seed=42) — 두 번 실행해도 byte-identical JSON 산출.

MEDIUM-3 v5 박제 (Convention):
  image y-down 픽셀 좌표. 직립 = mid_shoulder.y < mid_hip.y (어깨가 화면 위쪽 = y 작음).
  인버트 = mid_shoulder.y > mid_hip.y (어깨가 화면 아래쪽).
  PoleAxis.axis_vector 부호는 inversion verdict 와 무관 — measurer 가 y-order
  직접 비교. axis_vector 는 모든 fixture 가 default (0.0, 1.0, 0.0) 유지.

5 fixture:
  normal_pose      — T=60, 직립, 정상 confidence.
  inverted_pose    — T=60, 인버트 (y swap), conf 0.6~0.8.
  occluded_leg     — T=60, knee conf<0.3 in 70% frame.
  short_clip       — T=20, 정상 형태이나 frame 수 부족.
  asymmetric_pose  — T=60, 좌 conf>0.9 in 90%, 우 conf>0.9 in 50%.

RTMW adapter 경유 박제 (HIGH-2 v1→v2 정신 보존):
  본 모듈은 production adapter `convert_rtmw_keypoints_to_coco17_and_pole_ext`
  를 schema-drift 검증 목적으로 import. 5 fixture 자체는 synthetic PoseFrame
  으로 직접 생성하되 (실 RTMW 133 좌표 패턴은 belle Pod sweep 산출물로 v1.5
  promote — MEDIUM-2 v4 deferral), adapter 시그너처가 깨지면 본 import 가
  실패해 fixture 생성도 차단된다.

TODO(post-pilot, MEDIUM-2 v4): belle Pod Step (a) 산출 keypoint dump landing
  후 실 영상 fixture 1종 promote — ROADMAP success criterion 1 v1.5 closure.

CLI: `python -m tests.fixtures.body_normalization._generate --check`.
  --check: byte-identical 재생성 검증 (멱등성).
  미지정:  JSON 5종 산출.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

# CLI 단독 실행 (`python -m tests.fixtures.body_normalization._generate`) 시
# sys.path 에 backend/shared/python 주입. pytest 경유 (conftest.py) 는 자동.
_LAYER = Path(__file__).resolve().parents[3] / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

import numpy as np

# HIGH-2 v1→v2 박제: production RTMW adapter import (schema drift 검증).
# convert_rtmw_keypoints_to_coco17_and_pole_ext 시그너처가 깨지면 본 import 가 실패.
from sunity_shared.analysis.adapters.rtmw_133_to_coco17 import (  # noqa: F401, E402
    convert_rtmw_keypoints_to_coco17_and_pole_ext,
)
from sunity_shared.analysis.pose_frame import (  # noqa: E402
    Keypoint3D,
    Keypoint3DAligned,
    PoleAxis,
    PoseExtensionLandmark,
    PoseFrame,
)


_FIXTURES_DIR = Path(__file__).parent

# 인체 평균 비율 (image pixel, y-down).
_TORSO = 200.0
_UPPER_ARM = 120.0
_FOREARM = 110.0
_THIGH = 180.0
_SHANK = 160.0
_SHOULDER = 140.0
_HIP = 100.0

# Canonical default pole_axis (모든 fixture 공유 — MEDIUM-3 v5: axis_vector 무관).
_DEFAULT_AXIS_VECTOR: tuple[float, float, float] = (0.0, 1.0, 0.0)


def _make_pole_axis() -> PoleAxis:
    """모든 fixture 가 default (0,1,0). MEDIUM-3 v5 — inversion 판정은 y-order 만."""
    return PoleAxis(
        axis_vector=_DEFAULT_AXIS_VECTOR,
        confidence_level="medium",
        source="vertical_fallback",
        frame_index=None,
    )


def _kp(x: float, y: float, z: float, conf: float) -> Keypoint3D:
    """Keypoint3D 헬퍼. uncertainty_proxy = 1 - conf."""
    conf = max(0.0, min(1.0, conf))
    return Keypoint3D(
        x=float(x),
        y=float(y),
        z=float(z),
        confidence=conf,
        uncertainty_proxy=1.0 - conf,
    )


def _aligned(kp: Keypoint3D) -> Keypoint3DAligned:
    return Keypoint3DAligned(x=kp.x, y=kp.y, z=kp.z)


def _build_frame(
    *,
    frame_index: int,
    timestamp_ms: int,
    inverted: bool,
    rng: np.random.RandomState,
    left_conf: float,
    right_conf: float,
    knee_conf: float | None = None,
) -> PoseFrame:
    """단일 PoseFrame 합성 (image y-down).

    base layout (직립, y-down):
      shoulder_y = 100 (위)
      hip_y      = 100 + torso = 300
      elbow_y    = shoulder_y + upper_arm
      wrist_y    = elbow_y + forearm
      knee_y     = hip_y + thigh
      ankle_y    = knee_y + shank

    inverted = True 시 y 좌표 swap (shoulder.y vs hip.y).
    """
    # 좌우 x 위치
    cx = 500.0
    left_shoulder_x = cx - _SHOULDER / 2
    right_shoulder_x = cx + _SHOULDER / 2
    left_hip_x = cx - _HIP / 2
    right_hip_x = cx + _HIP / 2

    # base y-coords (image y-down: 작은 값 = 화면 위쪽)
    shoulder_y_top = 100.0
    hip_y_bottom = shoulder_y_top + _TORSO
    elbow_y = shoulder_y_top + _UPPER_ARM
    wrist_y = elbow_y + _FOREARM
    knee_y = hip_y_bottom + _THIGH
    ankle_y = knee_y + _SHANK

    if inverted:
        # MEDIUM-3 v5: y swap. inverted = mid_shoulder.y > mid_hip.y.
        # shoulder 가 hip 아래쪽 (y 큼). elbow/wrist 도 그에 맞춰 아래로.
        shoulder_y_new = hip_y_bottom + 50.0  # 어깨가 hip 아래
        hip_y_new = shoulder_y_top + 50.0  # hip 가 shoulder 위
        shoulder_y_top = shoulder_y_new
        hip_y_bottom = hip_y_new
        # elbow/wrist 도 shoulder 아래 (y 증가 방향).
        elbow_y = shoulder_y_top + _UPPER_ARM
        wrist_y = elbow_y + _FOREARM
        # knee/ankle 은 hip 위 (y 감소 방향).
        knee_y = hip_y_bottom - _THIGH
        ankle_y = knee_y - _SHANK

    # 미세 노이즈 (각 좌표 ±1px). seed-derived 결정적.
    def _n() -> float:
        return float(rng.uniform(-1.0, 1.0))

    # COCO-17 17 keypoints
    keypoints_3d: dict[str, Keypoint3D] = {}

    # face (5) — 합리적 conf
    nose_x = cx + _n()
    nose_y = shoulder_y_top - 50.0 + _n()
    face_conf = (left_conf + right_conf) / 2
    keypoints_3d["nose"] = _kp(nose_x, nose_y, 0.0, face_conf)
    keypoints_3d["left_eye"] = _kp(cx - 15 + _n(), nose_y - 10 + _n(), 0.0, face_conf)
    keypoints_3d["right_eye"] = _kp(cx + 15 + _n(), nose_y - 10 + _n(), 0.0, face_conf)
    keypoints_3d["left_ear"] = _kp(cx - 25 + _n(), nose_y + _n(), 0.0, face_conf)
    keypoints_3d["right_ear"] = _kp(cx + 25 + _n(), nose_y + _n(), 0.0, face_conf)

    # shoulders
    keypoints_3d["left_shoulder"] = _kp(
        left_shoulder_x + _n(), shoulder_y_top + _n(), 0.0, left_conf
    )
    keypoints_3d["right_shoulder"] = _kp(
        right_shoulder_x + _n(), shoulder_y_top + _n(), 0.0, right_conf
    )

    # elbows
    keypoints_3d["left_elbow"] = _kp(
        left_shoulder_x + _n(), elbow_y + _n(), 0.0, left_conf
    )
    keypoints_3d["right_elbow"] = _kp(
        right_shoulder_x + _n(), elbow_y + _n(), 0.0, right_conf
    )

    # wrists
    keypoints_3d["left_wrist"] = _kp(
        left_shoulder_x + _n(), wrist_y + _n(), 0.0, left_conf
    )
    keypoints_3d["right_wrist"] = _kp(
        right_shoulder_x + _n(), wrist_y + _n(), 0.0, right_conf
    )

    # hips
    keypoints_3d["left_hip"] = _kp(
        left_hip_x + _n(), hip_y_bottom + _n(), 0.0, left_conf
    )
    keypoints_3d["right_hip"] = _kp(
        right_hip_x + _n(), hip_y_bottom + _n(), 0.0, right_conf
    )

    # knees — occluded_leg fixture 의 경우 knee_conf override
    k_conf_l = knee_conf if knee_conf is not None else left_conf
    k_conf_r = knee_conf if knee_conf is not None else right_conf
    keypoints_3d["left_knee"] = _kp(
        left_hip_x + _n(), knee_y + _n(), 0.0, k_conf_l
    )
    keypoints_3d["right_knee"] = _kp(
        right_hip_x + _n(), knee_y + _n(), 0.0, k_conf_r
    )

    # ankles
    keypoints_3d["left_ankle"] = _kp(
        left_hip_x + _n(), ankle_y + _n(), 0.0, k_conf_l
    )
    keypoints_3d["right_ankle"] = _kp(
        right_hip_x + _n(), ankle_y + _n(), 0.0, k_conf_r
    )

    # pole-aligned: 본 fixture 는 좌표 동일 (pole 정렬 무시 — measurer 가 keypoints_3d 만 사용)
    keypoints_3d_pole_aligned = {
        name: _aligned(kp) for name, kp in keypoints_3d.items()
    }

    # pole extensions (foot landmarks) — minimal
    pole_ext: dict[str, PoseExtensionLandmark] = {
        "left_heel": PoseExtensionLandmark(
            x=keypoints_3d["left_ankle"].x,
            y=keypoints_3d["left_ankle"].y + (5.0 if not inverted else -5.0),
            z=0.0,
            confidence=k_conf_l,
        ),
        "right_heel": PoseExtensionLandmark(
            x=keypoints_3d["right_ankle"].x,
            y=keypoints_3d["right_ankle"].y + (5.0 if not inverted else -5.0),
            z=0.0,
            confidence=k_conf_r,
        ),
    }

    # frame-level reliability (대충 conf 기반)
    mean_conf = (left_conf + right_conf) / 2
    reliability = "high" if mean_conf >= 0.7 else "medium" if mean_conf >= 0.4 else "low"

    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        raw_landmarks_33={},
        keypoints_3d=keypoints_3d,
        keypoints_3d_pole_aligned=keypoints_3d_pole_aligned,
        keypoints_2d=None,
        pole_extension_landmarks=pole_ext,
        pole_axis=_make_pole_axis(),
        reliability=reliability,
        body_shape=None,  # RTMW path
        raw_keypoints_133=None,  # RTMW path 의 원본 보존은 fixture 범위 외
    )


def _round_floats(obj: Any, ndigits: int = 4) -> Any:
    """Recursive float rounding — fixture size 압축 + 멱등성 안정."""
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, list):
        return [_round_floats(v, ndigits) for v in obj]
    if isinstance(obj, dict):
        return {k: _round_floats(v, ndigits) for k, v in obj.items()}
    return obj


def _frame_to_dict(frame: PoseFrame) -> dict[str, Any]:
    """dataclasses.asdict + axis_vector tuple → list 변환 + float 압축."""
    d = dataclasses.asdict(frame)
    # axis_vector tuple → list (JSON 직렬화)
    if d.get("pole_axis") is not None:
        ax = d["pole_axis"]["axis_vector"]
        d["pole_axis"]["axis_vector"] = list(ax)
    # body_shape None — 그대로
    return _round_floats(d, ndigits=4)


def _generate_fixture(
    name: str,
    *,
    num_frames: int,
    seed: int,
    inverted: bool = False,
    left_conf_dist: tuple[float, float] = (0.85, 0.95),
    right_conf_dist: tuple[float, float] = (0.85, 0.95),
    occluded_knee: bool = False,
) -> list[dict[str, Any]]:
    """단일 fixture frame list 생성."""
    rng = np.random.RandomState(seed)
    frames: list[PoseFrame] = []
    for i in range(num_frames):
        # confidence sampling
        left_conf = float(rng.uniform(*left_conf_dist))
        right_conf = float(rng.uniform(*right_conf_dist))
        knee_conf = None
        if occluded_knee:
            # 70% 의 frame 에서 knee conf<0.3
            if rng.uniform(0, 1) < 0.7:
                knee_conf = float(rng.uniform(0.1, 0.3))
        # Asymmetric — right side 만 50% 에서 conf 낮춤
        if name == "asymmetric_pose":
            if rng.uniform(0, 1) < 0.5:
                right_conf = float(rng.uniform(0.2, 0.5))
        frame = _build_frame(
            frame_index=i,
            timestamp_ms=int(i * 1000 / 30),  # ~30fps
            inverted=inverted,
            rng=rng,
            left_conf=left_conf,
            right_conf=right_conf,
            knee_conf=knee_conf,
        )
        frames.append(frame)
    return [_frame_to_dict(f) for f in frames]


_FIXTURES_CONFIG = {
    "normal_pose": dict(
        num_frames=60,
        seed=42,
        inverted=False,
        left_conf_dist=(0.85, 0.95),
        right_conf_dist=(0.85, 0.95),
    ),
    "inverted_pose": dict(
        num_frames=60,
        seed=43,
        inverted=True,
        left_conf_dist=(0.6, 0.8),
        right_conf_dist=(0.6, 0.8),
    ),
    "occluded_leg": dict(
        num_frames=60,
        seed=44,
        inverted=False,
        left_conf_dist=(0.85, 0.95),
        right_conf_dist=(0.85, 0.95),
        occluded_knee=True,
    ),
    "short_clip": dict(
        num_frames=20,
        seed=45,
        inverted=False,
        left_conf_dist=(0.85, 0.95),
        right_conf_dist=(0.85, 0.95),
    ),
    "asymmetric_pose": dict(
        num_frames=60,
        seed=46,
        inverted=False,
        left_conf_dist=(0.9, 0.95),
        right_conf_dist=(0.9, 0.95),
    ),
}


def _dump_all() -> dict[str, bytes]:
    """모든 fixture JSON 생성 → 파일명: bytes dict."""
    out: dict[str, bytes] = {}
    for name, kwargs in _FIXTURES_CONFIG.items():
        frames = _generate_fixture(name, **kwargs)
        path_name = f"{name}_pose_frames.json"
        # 멱등성 + size budget — sort_keys=True + compact separators.
        # 각 fixture <200KB 목표 (plan §verify).
        text = json.dumps(frames, sort_keys=True, separators=(",", ":"))
        out[path_name] = text.encode("utf-8")
    return out


def _hashes(payload: dict[str, bytes]) -> dict[str, str]:
    return {k: hashlib.sha256(v).hexdigest() for k, v in payload.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate 5 synthetic PoseFrame fixtures.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Idempotency check — generate twice, assert byte-identical.",
    )
    args = parser.parse_args(argv)

    payload = _dump_all()

    if args.check:
        payload2 = _dump_all()
        h1 = _hashes(payload)
        h2 = _hashes(payload2)
        if h1 != h2:
            print(f"FAIL: not idempotent. {h1} != {h2}", file=sys.stderr)
            return 1
        print(f"OK: {len(payload)} fixtures idempotent.")
        return 0

    for fname, data in payload.items():
        out_path = _FIXTURES_DIR / fname
        out_path.write_bytes(data)
        print(f"WROTE {out_path} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
