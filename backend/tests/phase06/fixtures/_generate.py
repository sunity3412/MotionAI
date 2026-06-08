"""Phase 6 fixture 생성기 (one-shot, 합성 데이터).

본 스크립트는 6 fixture JSON 을 합성 데이터로 박제. 일회 실행 — 결과 JSON 만
commit. 본 스크립트 자체도 commit (재현성 박제).

산식 (합성 데이터 생성 규칙):
- RTMW COCO-17 17 keypoint dict 형식 정합 (skeleton.KEYPOINT_NAMES)
- 직립 기준 자세 = 어깨 (430/570, 100), 골반 (450/550, 300), 무릎 (450/550, 480),
  발목 (450/550, 640), 팔꿈치 (430/570, 220), 손목 (430/570, 330)
- pole_axis = vertical fallback (0, 1, 0)
- 모든 좌표는 image-y-down 픽셀, z=0 (2D 픽셀 + 깊이 0)

NotebookLM 인용:
- §1.4 정규화 효과 (MPJPE 237 → PA-MPJPE 91, 60%+ 위양성 거리 오차 제거)
- §1.5 OFF 조건 (60° + 150px hard threshold)
- §3.4 split 위양성 (hip→knee 라인만, toe-to-toe 금지)
- §4.2 temporal variance 5-10% 임계
- 2026-06-08 Codex Direct Review R5 (high dispersion fixture)
"""

from __future__ import annotations

import json
import math
from pathlib import Path


KEYPOINT_NAMES = (
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)


def _kp(x: float, y: float, z: float = 0.0, conf: float = 0.95) -> dict:
    return {
        "x": float(x),
        "y": float(y),
        "z": float(z),
        "confidence": float(conf),
        "uncertainty_proxy": float(1.0 - conf),
    }


def _kp_aligned(x: float, y: float, z: float = 0.0) -> dict:
    return {"x": float(x), "y": float(y), "z": float(z)}


def _pole_axis_vertical() -> dict:
    return {
        "axis_vector": [0.0, 1.0, 0.0],
        "confidence_level": "medium",
        "source": "vertical_fallback",
        "frame_index": None,
    }


def make_upright_frame(
    frame_index: int,
    timestamp_ms: int,
    *,
    scale: float = 1.0,
    cx: float = 500.0,
    cy_top: float = 100.0,
    confidence: float = 0.95,
    shoulder_half_width: float = 70.0,
    hip_half_width: float = 50.0,
    torso_len: float = 200.0,
    upper_arm_len: float = 120.0,
    forearm_len: float = 110.0,
    thigh_len: float = 180.0,
    shank_len: float = 160.0,
    twist_shoulder_deg: float = 0.0,
    twist_hip_deg: float = 0.0,
    arm_swing_offset_px: float = 0.0,
    head_offset_xy: tuple[float, float] = (0.0, 0.0),
) -> dict:
    """직립 자세 단일 frame 합성.

    scale: 전체 픽셀 좌표 ↔ origin (cx, cy_top) 기준 스케일. 1.0 = 기본 (160cm pro 기준 추정).
    twist_*: Twist 자세를 위한 어깨/골반 좌우 회전 (단순 좌우 폭 비율 조정).
    arm_swing_offset_px: temporal variance 용 팔 길이 변동 픽셀.
    """
    # apply scale
    sw = shoulder_half_width * scale
    hw = hip_half_width * scale
    torso = torso_len * scale
    ua = upper_arm_len * scale + arm_swing_offset_px
    fa = forearm_len * scale
    th = thigh_len * scale
    sh = shank_len * scale

    # twist: shoulder y 변동으로 좌우 폭 비율 표현
    sw_left = sw * (1.0 + math.sin(math.radians(twist_shoulder_deg)) * 0.3)
    sw_right = sw * (1.0 - math.sin(math.radians(twist_shoulder_deg)) * 0.3)
    hw_left = hw * (1.0 + math.sin(math.radians(twist_hip_deg)) * 0.3)
    hw_right = hw * (1.0 - math.sin(math.radians(twist_hip_deg)) * 0.3)

    head_y = cy_top + head_offset_xy[1]
    head_x = cx + head_offset_xy[0]

    ls_x, ls_y = cx - sw_left, cy_top
    rs_x, rs_y = cx + sw_right, cy_top
    lh_x, lh_y = cx - hw_left, cy_top + torso
    rh_x, rh_y = cx + hw_right, cy_top + torso

    le_x, le_y = ls_x, ls_y + ua
    re_x, re_y = rs_x, rs_y + ua
    lw_x, lw_y = le_x, le_y + fa
    rw_x, rw_y = re_x, re_y + fa
    lk_x, lk_y = lh_x, lh_y + th
    rk_x, rk_y = rh_x, rh_y + th
    la_x, la_y = lk_x, lk_y + sh
    ra_x, ra_y = rk_x, rk_y + sh

    kp3d = {
        "nose": _kp(head_x, head_y, conf=0.92),
        "left_eye": _kp(head_x - 15, head_y - 10, conf=0.92),
        "right_eye": _kp(head_x + 15, head_y - 10, conf=0.92),
        "left_ear": _kp(head_x - 25, head_y + 1, conf=0.92),
        "right_ear": _kp(head_x + 25, head_y + 1, conf=0.92),
        "left_shoulder": _kp(ls_x, ls_y, conf=confidence),
        "right_shoulder": _kp(rs_x, rs_y, conf=confidence),
        "left_elbow": _kp(le_x, le_y, conf=confidence),
        "right_elbow": _kp(re_x, re_y, conf=confidence),
        "left_wrist": _kp(lw_x, lw_y, conf=confidence),
        "right_wrist": _kp(rw_x, rw_y, conf=confidence),
        "left_hip": _kp(lh_x, lh_y, conf=confidence),
        "right_hip": _kp(rh_x, rh_y, conf=confidence),
        "left_knee": _kp(lk_x, lk_y, conf=confidence),
        "right_knee": _kp(rk_x, rk_y, conf=confidence),
        "left_ankle": _kp(la_x, la_y, conf=confidence),
        "right_ankle": _kp(ra_x, ra_y, conf=confidence),
    }
    kp3d_aligned = {
        name: _kp_aligned(v["x"], v["y"], v["z"]) for name, v in kp3d.items()
    }

    return {
        "frame_index": frame_index,
        "timestamp_ms": timestamp_ms,
        "keypoints_3d": kp3d,
        "keypoints_3d_pole_aligned": kp3d_aligned,
        "keypoints_2d": None,
        "pole_extension_landmarks": None,
        "pole_axis": _pole_axis_vertical(),
        "reliability": "high",
        "raw_landmarks_33": {},
        "raw_keypoints_133": None,
        "body_shape": None,
    }


def make_lying_frame(frame_index: int, timestamp_ms: int) -> dict:
    """누운 자세 (foreshortening). 어깨-골반 픽셀 거리 ~100px.

    누운 자세 → 카메라 시선과 평행, torso 가 픽셀 평면에서 단축.
    """
    cx, cy = 500.0, 400.0
    # torso 픽셀 거리 = 100 (직립 200 의 50%)
    # 어깨 (450, 380) <-> 골반 (550, 380) 대신
    # 어깨 (495, 380) <-> 골반 (495, 480) 의 단축 형태 — 픽셀 100px
    ls_y, rs_y = cy - 5, cy - 5
    lh_y, rh_y = cy + 95, cy + 95

    kp3d = {
        "nose": _kp(cx, cy - 60, conf=0.85),
        "left_eye": _kp(cx - 10, cy - 70, conf=0.85),
        "right_eye": _kp(cx + 10, cy - 70, conf=0.85),
        "left_ear": _kp(cx - 20, cy - 60, conf=0.85),
        "right_ear": _kp(cx + 20, cy - 60, conf=0.85),
        "left_shoulder": _kp(cx - 50, ls_y, conf=0.85),
        "right_shoulder": _kp(cx + 50, rs_y, conf=0.85),
        "left_elbow": _kp(cx - 80, ls_y + 60, conf=0.80),
        "right_elbow": _kp(cx + 80, rs_y + 60, conf=0.80),
        "left_wrist": _kp(cx - 100, ls_y + 110, conf=0.80),
        "right_wrist": _kp(cx + 100, rs_y + 110, conf=0.80),
        "left_hip": _kp(cx - 40, lh_y, conf=0.85),
        "right_hip": _kp(cx + 40, rh_y, conf=0.85),
        "left_knee": _kp(cx - 40, lh_y + 100, conf=0.80),
        "right_knee": _kp(cx + 40, rh_y + 100, conf=0.80),
        "left_ankle": _kp(cx - 40, lh_y + 180, conf=0.80),
        "right_ankle": _kp(cx + 40, rh_y + 180, conf=0.80),
    }
    kp3d_aligned = {
        name: _kp_aligned(v["x"], v["y"], v["z"]) for name, v in kp3d.items()
    }
    return {
        "frame_index": frame_index,
        "timestamp_ms": timestamp_ms,
        "keypoints_3d": kp3d,
        "keypoints_3d_pole_aligned": kp3d_aligned,
        "keypoints_2d": None,
        "pole_extension_landmarks": None,
        "pole_axis": _pole_axis_vertical(),
        "reliability": "medium",
        "raw_landmarks_33": {},
        "raw_keypoints_133": None,
        "body_shape": None,
    }


def make_split_frame(
    frame_index: int, timestamp_ms: int, *, leg_length: float
) -> dict:
    """split 자세 (다리 좌우로 벌림). hip→knee 각도는 동일, toe→toe Euclidean 다름.

    leg_length: 다리 (hip→knee→ankle) 픽셀 길이. short vs long 변형 시 다름.
    """
    cx, cy_top = 500.0, 100.0
    sw, hw = 70.0, 50.0
    torso = 200.0
    upper = 120.0
    fore = 110.0

    # split — 다리가 좌우로 175° 벌림 (각도 175 from vertical down).
    # split angle from vertical = 87.5° each side → leg goes mostly horizontal.
    leg_angle_deg = 87.5
    rad = math.radians(leg_angle_deg)
    dx = math.sin(rad) * leg_length
    dy = math.cos(rad) * leg_length  # small downward

    ls_x, ls_y = cx - sw, cy_top
    rs_x, rs_y = cx + sw, cy_top
    lh_x, lh_y = cx - hw, cy_top + torso
    rh_x, rh_y = cx + hw, cy_top + torso

    le_x, le_y = ls_x, ls_y + upper
    re_x, re_y = rs_x, rs_y + upper
    lw_x, lw_y = le_x, le_y + fore
    rw_x, rw_y = re_x, re_y + fore

    # left leg goes left, right leg goes right (knee then ankle continues in same direction)
    lk_x = lh_x - dx
    lk_y = lh_y + dy
    rk_x = rh_x + dx
    rk_y = rh_y + dy
    la_x = lk_x - dx
    la_y = lk_y + dy
    ra_x = rk_x + dx
    ra_y = rk_y + dy

    kp3d = {
        "nose": _kp(cx, cy_top - 50, conf=0.92),
        "left_eye": _kp(cx - 15, cy_top - 60, conf=0.92),
        "right_eye": _kp(cx + 15, cy_top - 60, conf=0.92),
        "left_ear": _kp(cx - 25, cy_top - 49, conf=0.92),
        "right_ear": _kp(cx + 25, cy_top - 49, conf=0.92),
        "left_shoulder": _kp(ls_x, ls_y, conf=0.95),
        "right_shoulder": _kp(rs_x, rs_y, conf=0.95),
        "left_elbow": _kp(le_x, le_y, conf=0.95),
        "right_elbow": _kp(re_x, re_y, conf=0.95),
        "left_wrist": _kp(lw_x, lw_y, conf=0.95),
        "right_wrist": _kp(rw_x, rw_y, conf=0.95),
        "left_hip": _kp(lh_x, lh_y, conf=0.95),
        "right_hip": _kp(rh_x, rh_y, conf=0.95),
        "left_knee": _kp(lk_x, lk_y, conf=0.95),
        "right_knee": _kp(rk_x, rk_y, conf=0.95),
        "left_ankle": _kp(la_x, la_y, conf=0.95),
        "right_ankle": _kp(ra_x, ra_y, conf=0.95),
    }
    kp3d_aligned = {
        name: _kp_aligned(v["x"], v["y"], v["z"]) for name, v in kp3d.items()
    }
    return {
        "frame_index": frame_index,
        "timestamp_ms": timestamp_ms,
        "keypoints_3d": kp3d,
        "keypoints_3d_pole_aligned": kp3d_aligned,
        "keypoints_2d": None,
        "pole_extension_landmarks": None,
        "pole_axis": _pole_axis_vertical(),
        "reliability": "high",
        "raw_landmarks_33": {},
        "raw_keypoints_133": None,
        "body_shape": None,
    }


def make_sprawled_frame(frame_index: int, timestamp_ms: int) -> dict:
    """팔/다리가 어깨너비 대비 매우 넓게 펼쳐진 X/T 자세 (R5 fix).

    C_s / shoulder_width >= 3.0 보장 — shoulder_width 작게 (정면에서 어깨 폭만)
    + wrist/ankle 가 매우 넓게 펼쳐져 centroid 에서 멀어진 형태.

    shoulder_width = 80px (정면 90도 회전한 듯한 좁은 어깨).
    wrist 가 cx ± 500px (centroid 에서 ~500 떨어짐).
    ankle 가 cx ± 400px.
    """
    cx, cy_top = 500.0, 200.0
    # shoulder_width 를 작게 (40px each side = 80px width).
    sw = 40.0
    hw = 30.0
    torso = 200.0

    ls_x, ls_y = cx - sw, cy_top
    rs_x, rs_y = cx + sw, cy_top
    lh_x, lh_y = cx - hw, cy_top + torso
    rh_x, rh_y = cx + hw, cy_top + torso

    # 팔이 양옆으로 매우 넓게 펼침 — wrist 가 centroid 에서 ~500px
    le_x, le_y = ls_x - 200, ls_y + 20
    re_x, re_y = rs_x + 200, rs_y + 20
    lw_x, lw_y = ls_x - 500, ls_y + 40
    rw_x, rw_y = rs_x + 500, rs_y + 40

    # 다리도 좌우로 넓게 (split-like) — ankle 가 centroid 에서 ~400px
    lk_x, lk_y = lh_x - 150, lh_y + 80
    rk_x, rk_y = rh_x + 150, rh_y + 80
    la_x, la_y = lk_x - 250, lk_y + 80
    ra_x, ra_y = rk_x + 250, rk_y + 80

    kp3d = {
        "nose": _kp(cx, cy_top - 50, conf=0.92),
        "left_eye": _kp(cx - 15, cy_top - 60, conf=0.92),
        "right_eye": _kp(cx + 15, cy_top - 60, conf=0.92),
        "left_ear": _kp(cx - 25, cy_top - 49, conf=0.92),
        "right_ear": _kp(cx + 25, cy_top - 49, conf=0.92),
        "left_shoulder": _kp(ls_x, ls_y, conf=0.92),
        "right_shoulder": _kp(rs_x, rs_y, conf=0.92),
        "left_elbow": _kp(le_x, le_y, conf=0.90),
        "right_elbow": _kp(re_x, re_y, conf=0.90),
        "left_wrist": _kp(lw_x, lw_y, conf=0.88),
        "right_wrist": _kp(rw_x, rw_y, conf=0.88),
        "left_hip": _kp(lh_x, lh_y, conf=0.92),
        "right_hip": _kp(rh_x, rh_y, conf=0.92),
        "left_knee": _kp(lk_x, lk_y, conf=0.90),
        "right_knee": _kp(rk_x, rk_y, conf=0.90),
        "left_ankle": _kp(la_x, la_y, conf=0.88),
        "right_ankle": _kp(ra_x, ra_y, conf=0.88),
    }
    kp3d_aligned = {
        name: _kp_aligned(v["x"], v["y"], v["z"]) for name, v in kp3d.items()
    }
    return {
        "frame_index": frame_index,
        "timestamp_ms": timestamp_ms,
        "keypoints_3d": kp3d,
        "keypoints_3d_pole_aligned": kp3d_aligned,
        "keypoints_2d": None,
        "pole_extension_landmarks": None,
        "pole_axis": _pole_axis_vertical(),
        "reliability": "high",
        "raw_landmarks_33": {},
        "raw_keypoints_133": None,
        "body_shape": None,
    }


def gen_fixture_160cm_pro_vs_140cm_student() -> dict:
    """동일 직립 자세, scale 만 다름. 30 frame each list."""
    pro_frames = [
        make_upright_frame(i, i * 33, scale=1.0) for i in range(30)
    ]
    student_frames = [
        make_upright_frame(i, i * 33, scale=0.875) for i in range(30)
    ]
    return {
        "pro_frames": pro_frames,
        "student_frames": student_frames,
        "metadata": {
            "pro_height_cm": 160,
            "student_height_cm": 140,
            "scale_ratio": 0.875,
            "rationale": (
                "NotebookLM Notebook 1 §1.4 — 정규화 효과 (MPJPE 237 → "
                "PA-MPJPE 91, 60% 위양성 거리 오차 제거). 북극성 use case."
            ),
        },
    }


def gen_fixture_lefty_vs_righty_twist() -> dict:
    """Twist 자세 (어깨 +30° / 골반 -30°). 10 frame.

    intentional_asymmetry=True — IPSF Twist 요건 (감점 X).
    좌우 폭 비율 1.3 vs 0.77 표현.
    """
    frames = [
        make_upright_frame(
            i,
            i * 33,
            twist_shoulder_deg=30.0,
            twist_hip_deg=-30.0,
        )
        for i in range(10)
    ]
    return {
        "frames": frames,
        "metadata": {
            "intentional_asymmetry": True,
            "expected_shoulder_hip_ratio": 1.3,
            "rationale": (
                "NotebookLM Notebook 3 §3.2 — IPSF Twist 의도적 좌우 비대칭 "
                "(요건, 감점 X)."
            ),
        },
    }


def gen_fixture_foreshortening_lying_pose() -> dict:
    """카메라 시선 평행 누운 자세. 15 frame. 어깨-골반 픽셀 거리 ~100px."""
    frames = [make_lying_frame(i, i * 33) for i in range(15)]
    return {
        "frames": frames,
        "metadata": {
            "shoulder_hip_pixel_distance_avg": 100,
            "torso_camera_angle_deg": 30,
            "rationale": (
                "NotebookLM Notebook 1 §1.5 — foreshortening 60° hard "
                "threshold + 150px 어깨-골반 픽셀 거리 임계."
            ),
        },
    }


def gen_fixture_unstable_arm_swing() -> dict:
    """빠른 팔 swing + 다리 swing. 30 frame.

    좌측 팔/다리 segment 의 길이 픽셀 표준편차 / 평균 = ~15% (Notebook §4.2
    임계 10% 초과). 5 핵심 segment 모두에 swing 적용 — confidence 산출의
    average path 트리거.
    """
    frames = []
    for i in range(30):
        offset = 25.0 + 25.0 * math.sin(i * 0.5)
        # upper_arm + forearm + thigh + shank + torso 모두 변동
        frames.append(
            make_upright_frame(
                i,
                i * 33,
                upper_arm_len=120.0 + offset,
                forearm_len=110.0 + offset * 0.8,
                thigh_len=180.0 + offset * 1.0,
                shank_len=160.0 + offset * 0.9,
                torso_len=200.0 + offset * 0.5,
            )
        )
    return {
        "frames": frames,
        "metadata": {
            "arm_temporal_variance_ratio": 0.15,
            "rationale": (
                "NotebookLM Notebook 4 §4.2 — temporal variance 10% 임계 "
                "초과. confidence 하향 트리거. 5 핵심 segment 모두 swing."
            ),
        },
    }


def gen_fixture_split_angle_hipline() -> dict:
    """split 다리 자세 두 변형. short_leg vs long_leg.

    hip→knee 각도 동일 (175°), toe→toe Euclidean 다름.
    leg_length 만 다름.
    """
    short_leg_frames = [
        make_split_frame(i, i * 33, leg_length=120.0) for i in range(15)
    ]
    long_leg_frames = [
        make_split_frame(i, i * 33, leg_length=200.0) for i in range(15)
    ]
    # toe→toe euclidean: short = 2 * 2 * leg_length * sin(87.5°) ~ 479
    # long ~ 799 — 차이 > 100px (split 위양성 회피 검증용)
    return {
        "short_leg_frames": short_leg_frames,
        "long_leg_frames": long_leg_frames,
        "metadata": {
            "hip_knee_angle_deg": 175,
            "toe_to_toe_distance_short_px": 200,
            "toe_to_toe_distance_long_px": 350,
            "rationale": (
                "NotebookLM Notebook 3 §3.4 — split 위양성 회피. hip→knee "
                "라인 각도만 사용, toe-to-toe Euclidean 절대 금지."
            ),
        },
    }


def gen_fixture_high_dispersion_arms_sprawled() -> dict:
    """R5 fix 신규. 팔/다리가 어깨너비 대비 매우 넓게 펼쳐진 자세.

    C_s / shoulder_width 평균 >= 3.0 (DISPERSION_BASELINE 1.5 의 2배+).
    high dispersion → high penalty 의 자연 방향 검증용.
    """
    frames = [make_sprawled_frame(i, i * 33) for i in range(15)]
    return {
        "frames": frames,
        "metadata": {
            "expected_dispersion_ratio": 3.2,
            "expected_spatial_dispersion_penalty": 1.0,
            "rationale": (
                "R5 fix (2026-06-08 round-2 reviews) — DISPERSION_BASELINE "
                "1.5 의 2배 이상 (penalty=1.0). high dispersion → high "
                "penalty 의 자연 방향 검증용."
            ),
        },
    }


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    fixtures = {
        "fixture_160cm_pro_vs_140cm_student.json": gen_fixture_160cm_pro_vs_140cm_student(),
        "fixture_lefty_vs_righty_twist.json": gen_fixture_lefty_vs_righty_twist(),
        "fixture_foreshortening_lying_pose.json": gen_fixture_foreshortening_lying_pose(),
        "fixture_unstable_arm_swing.json": gen_fixture_unstable_arm_swing(),
        "fixture_split_angle_hipline.json": gen_fixture_split_angle_hipline(),
        "fixture_high_dispersion_arms_sprawled.json": gen_fixture_high_dispersion_arms_sprawled(),
    }
    for name, data in fixtures.items():
        out = out_dir / name
        out.write_text(json.dumps(data, indent=None, separators=(",", ":")), encoding="utf-8")
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
