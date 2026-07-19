"""목표 각도 화살표 + CorrectedPoseTarget 기하 테스트 (Phase 31-03, D-11/D-12).

리뷰 B-02 / 2차 리뷰 B2-01·H2-03 이 요구한 불변식을 golden 으로 고정한다:
  · 화살표 endpoint = reference 3점 정합 기하 (감점 record 수치 미유입)
  · 미러 반사 = full-body topology parity 단독 결정 — "가까운 후보" 휴리스틱이면
    실패하는 adversarial fixture 포함 (H2-03)
  · parity 불명 / ref 대응 실패 / 미선언 관절 / 저신뢰 / 미세 delta → 생략
  · CorrectedPoseTarget.target_deg = DTW matched reference 3점 내각만

순수 — PIL/numpy 외 의존 0 (S3/네트워크/firestore import 금지).
"""

from __future__ import annotations

import inspect
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

# 정사각 프레임 + 전체 crop → crop-px = 정규화 * _OUT (검산이 자명한 좌표계).
_W = _H = 200
_SIDE = 200
_CROP_CTX = (0, 0, _SIDE, _W, _H)
_SCALE = fz._OUT / _SIDE  # 정규화 1.0 → crop px _OUT


def _px(nx: float, ny: float) -> tuple[int, int]:
    """정규화 → 기대 crop px (_to_crop_px 와 동일 반올림/clamp)."""
    return (
        max(0, min(fz._OUT - 1, int(round(nx * _W * _SCALE)))),
        max(0, min(fz._OUT - 1, int(round(ny * _H * _SCALE)))),
    )


def _report(frames: list[dict[str, tuple[float, float]]], fps: float = 9.0,
            conf: float = 0.9) -> dict:
    """프레임별 {관절: (x,y)} → 합성 keypointReport (flat data + confidence).

    프레임에 없는 관절은 NaN 좌표 + conf 0.0 (결측/저신뢰 경로 검증용).
    """
    joints = sorted({k for f in frames for k in f})
    nj = len(joints)
    data: list[float] = []
    confidence: list[float] = []
    for f in frames:
        for j in joints:
            xy = f.get(j)
            if xy is None:
                data += [float("nan"), float("nan")]
                confidence.append(0.0)
            else:
                data += [float(xy[0]), float(xy[1])]
                confidence.append(conf)
    return {
        "joints": joints,
        "frames": len(frames),
        "fps": fps,
        "data": data,
        "confidence": confidence,
    }


def _torso(sign: int = 1) -> dict[str, tuple[float, float]]:
    """어깨/힙 4점 — sign=+1 이면 right_* 가 화면 오른쪽(정상), -1 이면 반대(미러)."""
    return {
        "left_shoulder": (0.5 - 0.12 * sign, 0.30),
        "right_shoulder": (0.5 + 0.12 * sign, 0.30),
        "left_hip": (0.5 - 0.10 * sign, 0.50),
        "right_hip": (0.5 + 0.10 * sign, 0.50),
    }


def _expected_endpoint(
    u_prox, u_vert, ref_prox, ref_vert, ref_dist, mirrored: bool
) -> tuple[int, int]:
    """독립 검산 — 복소수 산술로 2D similarity 를 다시 푼 golden.

    모듈 구현(실수 산술)과 다른 형식으로 계산해 tautology 를 피한다.
    """
    def c(p):
        return complex(p[0] * _W, p[1] * _H)

    rp, rv, rd = c(ref_prox), c(ref_vert), c(ref_dist)
    if mirrored:
        axis = rv.real
        rp = complex(2 * axis - rp.real, rp.imag)
        rd = complex(2 * axis - rd.real, rd.imag)
        rv = complex(axis, rv.imag)
    up, uv = c(u_prox), c(u_vert)
    z = (uv - up) / (rv - rp)
    t = up + z * (rd - rp)
    return _px(t.real / _W, t.imag / _H)


# ─────────────── (a) 좌/우 무릎 endpoint golden ───────────────


def _knee_case(side: str, mirrored_ref: bool = False):
    """굽은 무릎(user) vs 펴진 무릎(reference) 한 쌍.

    hip 은 몸통 keypoint 이기도 하므로 torso 가 정한 좌표를 그대로 쓰고 knee/ankle
    만 그 hip 기준 offset 으로 얹는다 (torso 를 덮어쓰면 parity 판정이 깨진다).
    """
    hip, knee, ankle = f"{side}_hip", f"{side}_knee", f"{side}_ankle"
    u_frame = dict(_torso(1))
    uh = u_frame[hip]
    u_frame[knee] = (uh[0], uh[1] + 0.20)
    u_frame[ankle] = (uh[0] + 0.12, uh[1] + 0.32)   # 굽음
    r_frame = dict(_torso(-1 if mirrored_ref else 1))
    rh = r_frame[hip]
    r_frame[knee] = (rh[0], rh[1] + 0.20)
    r_frame[ankle] = (rh[0], rh[1] + 0.42)          # 곧게 폄
    pts = {
        "u": (uh, u_frame[knee], u_frame[ankle]),
        "r": (rh, r_frame[knee], r_frame[ankle]),
    }
    return _report([u_frame]), _report([r_frame]), (hip, knee, ankle), pts


def test_knee_arrow_endpoint_matches_reference_geometry():
    for side in ("left", "right"):
        u_rep, r_rep, (hip, knee, ankle), pts = _knee_case(side)
        spec = fz._build_arrow_spec(
            knee, u_rep, 0, r_rep, 0, False, _CROP_CTX
        )
        assert spec.omit_reason is None, f"{side}: 정상 케이스인데 생략됨"
        assert spec.mirror_parity == "same"
        assert spec.source_kind == "reference_pose"
        # user/ref 의 (hip, knee) 가 동일 → 정합 변환 = 항등 → 목표 = reference ankle.
        want = _px(*pts["r"][2])
        got = spec.target_endpoint_px
        assert abs(got[0] - want[0]) <= 2 and abs(got[1] - want[1]) <= 2, (
            f"{side}: endpoint {got} != {want} (±2px)"
        )
        assert spec.user_distal_px == _px(*pts["u"][2])
        assert spec.vertex == knee and spec.proximal == hip and spec.distal == ankle


def test_arrow_endpoint_tracks_rotated_and_scaled_reference():
    """도립·스케일 반전 기하 — 사용자 세그먼트가 뒤집혀도 정합이 따라간다."""
    u_frame = dict(_torso(1))
    # 사용자: 무릎이 엉덩이보다 위(도립), 세그먼트 길이도 reference 의 절반.
    u_frame.update({
        "left_hip": (0.50, 0.70),
        "left_knee": (0.50, 0.60),
        "left_ankle": (0.58, 0.56),
    })
    r_frame = dict(_torso(1))
    r_frame.update({
        "left_hip": (0.30, 0.30),
        "left_knee": (0.30, 0.50),
        "left_ankle": (0.30, 0.70),
    })
    u_rep, r_rep = _report([u_frame]), _report([r_frame])
    spec = fz._build_arrow_spec("left_knee", u_rep, 0, r_rep, 0, False, _CROP_CTX)
    assert spec.omit_reason is None
    want = _expected_endpoint(
        (0.50, 0.70), (0.50, 0.60), (0.30, 0.30), (0.30, 0.50), (0.30, 0.70),
        mirrored=False,
    )
    got = spec.target_endpoint_px
    assert abs(got[0] - want[0]) <= 2 and abs(got[1] - want[1]) <= 2
    # 도립이므로 목표는 사용자 무릎 위쪽(y 감소 방향)으로 이어져야 한다.
    assert got[1] < spec.user_vertex_px[1]


# ─────────────── (c) mirrored parity ───────────────


def test_mirrored_parity_detected_and_reflection_applied():
    u_rep, r_rep, (_hip, knee, _ankle), pts = _knee_case("left", mirrored_ref=True)
    spec = fz._build_arrow_spec(knee, u_rep, 0, r_rep, 0, False, _CROP_CTX)
    assert spec.mirror_parity == "mirrored"
    assert spec.omit_reason is None
    want = _expected_endpoint(
        pts["u"][0], pts["u"][1], pts["r"][0], pts["r"][1], pts["r"][2],
        mirrored=True,
    )
    got = spec.target_endpoint_px
    assert abs(got[0] - want[0]) <= 2 and abs(got[1] - want[1]) <= 2


def test_frame_mirror_parity_pure_cases():
    same = fz._frame_mirror_parity(
        {k: v for k, v in _torso(1).items()}, {k: v for k, v in _torso(1).items()}
    )
    mirrored = fz._frame_mirror_parity(
        {k: v for k, v in _torso(1).items()}, {k: v for k, v in _torso(-1).items()}
    )
    assert same == "same" and mirrored == "mirrored"


# ─────────────── (c') H2-03 adversarial: 가까운 후보가 오답 ───────────────


def test_mirrored_parity_wins_even_when_wrong_candidate_is_closer():
    """H2-03 golden — 목표 교정이 커서 '틀린 반사 후보'가 현재 distal 에 더 가깝다.

    거리 기반 구현이면 가까운(틀린) 후보를 골라 실패하고, parity 기반이면 통과한다.
    """
    # 사용자 몸통은 오른쪽 향(+1), reference 는 미러(-1) → parity = 'mirrored'.
    u_frame = dict(_torso(1))
    u_frame.update({
        "left_hip": (0.50, 0.40),
        "left_knee": (0.50, 0.60),
        # 현재 발끝이 화면 왼쪽으로 크게 접혀 있다 (큰 결함).
        "left_ankle": (0.24, 0.66),
    })
    r_frame = dict(_torso(-1))
    r_frame.update({
        "left_hip": (0.50, 0.40),
        "left_knee": (0.50, 0.60),
        # reference(미러 좌표계)의 발끝은 화면 왼쪽 — 반사하면 오른쪽으로 간다.
        "left_ankle": (0.30, 0.80),
    })
    u_rep, r_rep = _report([u_frame]), _report([r_frame])
    spec = fz._build_arrow_spec("left_knee", u_rep, 0, r_rep, 0, False, _CROP_CTX)
    assert spec.mirror_parity == "mirrored"
    assert spec.omit_reason is None

    correct = _expected_endpoint(
        (0.50, 0.40), (0.50, 0.60), (0.50, 0.40), (0.50, 0.60), (0.30, 0.80),
        mirrored=True,
    )
    wrong = _expected_endpoint(
        (0.50, 0.40), (0.50, 0.60), (0.50, 0.40), (0.50, 0.60), (0.30, 0.80),
        mirrored=False,
    )
    user_distal = spec.user_distal_px
    d_correct = math.dist(correct, user_distal)
    d_wrong = math.dist(wrong, user_distal)
    assert d_wrong < d_correct, (
        "fixture 전제 붕괴 — 틀린 후보가 더 가까워야 adversarial 이 성립한다 "
        f"(correct={d_correct:.1f}, wrong={d_wrong:.1f})"
    )
    got = spec.target_endpoint_px
    assert abs(got[0] - correct[0]) <= 2 and abs(got[1] - correct[1]) <= 2, (
        "parity 가 아니라 '가까운 후보'를 골랐다 (H2-03 회귀)"
    )


# ─────────────── (c'') parity 불명 → 생략 ───────────────


def test_shoulder_hip_disagreement_yields_parity_unknown_omission():
    """어깨는 오른쪽 향, 힙은 왼쪽 향 — topology 불일치 → 판정 불가 → 생략."""
    u_frame = {
        "left_shoulder": (0.38, 0.30),
        "right_shoulder": (0.62, 0.30),
        "left_hip": (0.60, 0.50),   # 힙만 부호 반대 (어깨와 불일치)
        "right_hip": (0.40, 0.50),
        "left_knee": (0.40, 0.60),
        "left_ankle": (0.52, 0.72),
    }
    r_frame = dict(_torso(1))
    r_frame.update({
        "left_hip": (0.40, 0.40), "left_knee": (0.40, 0.60),
        "left_ankle": (0.40, 0.82),
    })
    u_rep, r_rep = _report([u_frame]), _report([r_frame])
    spec = fz._build_arrow_spec("left_knee", u_rep, 0, r_rep, 0, False, _CROP_CTX)
    assert spec.omit_reason == "parity_unknown"
    assert spec.mirror_parity == "unknown"
    assert spec.target_endpoint_px is None


def test_parity_unknown_when_torso_separation_degenerate():
    """정면/측면 경계(좌우 분리 ~0) → 부호가 노이즈 → 판정 불가."""
    flat = {
        "left_shoulder": (0.500, 0.30), "right_shoulder": (0.505, 0.30),
        "left_hip": (0.500, 0.50), "right_hip": (0.505, 0.50),
        "left_knee": (0.40, 0.60), "left_ankle": (0.52, 0.72),
    }
    r_frame = dict(_torso(1))
    r_frame.update({
        "left_hip": (0.40, 0.40), "left_knee": (0.40, 0.60),
        "left_ankle": (0.40, 0.82),
    })
    spec = fz._build_arrow_spec(
        "left_knee", _report([flat]), 0, _report([r_frame]), 0, False, _CROP_CTX
    )
    assert spec.omit_reason == "parity_unknown"


# ─────────────── (d) omission 계열 + 드로잉 0 ───────────────


def _blank() -> Image.Image:
    return Image.new("RGB", (fz._OUT, fz._OUT), (255, 255, 255))


def _pixels(img: Image.Image) -> np.ndarray:
    return np.asarray(img).copy()


def test_omissions_draw_nothing_and_leave_pixels_untouched():
    u_rep, r_rep, (_h, knee, _a), pts = _knee_case("left")
    cases = {
        "ref_match_failed": fz._build_arrow_spec(
            knee, u_rep, 0, r_rep, 0, True, _CROP_CTX
        ),
        "unmapped_joint": fz._build_arrow_spec(
            "nose", u_rep, 0, r_rep, 0, False, _CROP_CTX
        ),
    }
    # 저신뢰: reference 좌표는 유한하지만 confidence 가 _KP_CONF_MIN 미만.
    low_frame = dict(_torso(1))
    low_frame["left_knee"] = pts["r"][1]
    low_frame["left_ankle"] = pts["r"][2]
    cases["low_confidence"] = fz._build_arrow_spec(
        knee, u_rep, 0, _report([low_frame], conf=0.2), 0, False, _CROP_CTX
    )
    # 미세 delta: reference 형상 == user 형상 → 목표 == 현재 위치.
    cases["negligible_delta"] = fz._build_arrow_spec(
        knee, u_rep, 0, u_rep, 0, False, _CROP_CTX
    )

    for reason, spec in cases.items():
        assert spec.omit_reason == reason, f"{reason} 기대, got {spec.omit_reason}"
        assert spec.target_endpoint_px is None
        img = _blank()
        before = _pixels(img)
        assert fz._draw_target_arrow(img, spec) is False
        assert np.array_equal(_pixels(img), before), f"{reason}: 픽셀이 변했다"


def test_degenerate_segment_omitted():
    """proximal 과 vertex 가 겹치면 정합 변환 미정의 → 생략."""
    u_frame = dict(_torso(1))
    u_frame.update({
        "left_hip": (0.40, 0.60), "left_knee": (0.40, 0.60),
        "left_ankle": (0.52, 0.72),
    })
    r_frame = dict(_torso(1))
    r_frame.update({
        "left_hip": (0.40, 0.40), "left_knee": (0.40, 0.60),
        "left_ankle": (0.40, 0.82),
    })
    spec = fz._build_arrow_spec(
        "left_knee", _report([u_frame]), 0, _report([r_frame]), 0, False, _CROP_CTX
    )
    assert spec.omit_reason == "degenerate_segment"


# ─────────────── (e) edge clamp ───────────────


def test_endpoint_clamped_into_canvas():
    """목표가 crop 밖으로 나가도 좌표는 [0,_OUT-1] 안 (캔버스 밖 방어)."""
    u_frame = dict(_torso(1))
    u_frame.update({
        "left_hip": (0.50, 0.50), "left_knee": (0.50, 0.55),
        "left_ankle": (0.52, 0.60),
    })
    r_frame = dict(_torso(1))
    # reference distal 이 proximal→vertex 대비 극단적으로 멀다 → 목표가 프레임 밖.
    r_frame.update({
        "left_hip": (0.50, 0.50), "left_knee": (0.50, 0.55),
        "left_ankle": (0.50, 3.50),
    })
    spec = fz._build_arrow_spec(
        "left_knee", _report([u_frame]), 0, _report([r_frame]), 0, False, _CROP_CTX
    )
    assert spec.omit_reason is None
    for pt in (spec.target_endpoint_px, spec.user_distal_px, spec.user_vertex_px):
        assert 0 <= pt[0] <= fz._OUT - 1 and 0 <= pt[1] <= fz._OUT - 1


# ─────────────── (f) record 비의존 (T-31-10) ───────────────


def test_arrow_geometry_never_touches_deduction_records():
    """기하 경로가 감점 record 를 인자로도, 필드로도 읽지 않는다 (리뷰 B-02)."""
    params = set(inspect.signature(fz._build_arrow_spec).parameters)
    for banned in ("records", "record", "deduction", "breakdown"):
        assert not any(banned in p for p in params), (
            f"_build_arrow_spec 이 감점 record 를 인자로 받는다: {params}"
        )
    forbidden = ("measuredValue", "baselineValue", "deviation", "rawPoints")
    for fn in (
        fz._build_arrow_spec,
        fz._draw_target_arrow,
        fz._frame_mirror_parity,
        fz._facing_sign,
        fz.joint_inner_angle_deg,
    ):
        src = inspect.getsource(fn)
        for token in forbidden:
            assert token not in src, (
                f"{fn.__name__} 이 채점 record 수치 필드 '{token}' 를 참조한다"
            )


# ─────────────── (g) 정상 spec → 드로잉 ───────────────


def test_valid_spec_draws_within_expected_bbox():
    u_rep, r_rep, (_h, knee, _a), _pts = _knee_case("left")
    spec = fz._build_arrow_spec(knee, u_rep, 0, r_rep, 0, False, _CROP_CTX)
    img = _blank()
    before = _pixels(img)
    assert fz._draw_target_arrow(img, spec) is True
    after = _pixels(img)
    assert not np.array_equal(after, before), "정상 spec 인데 픽셀이 안 변했다"
    ys, xs = np.where(np.any(after != before, axis=2))
    x0, y0 = spec.user_distal_px
    x1, y1 = spec.target_endpoint_px
    pad = max(6, int(fz._OUT * 0.05)) + 8  # 마커 반지름 + 선 두께 여유
    assert xs.min() >= min(x0, x1) - pad and xs.max() <= max(x0, x1) + pad
    assert ys.min() >= min(y0, y1) - pad and ys.max() <= max(y0, y1) + pad
    # 브랜드 컬러만 사용 (design.md — 하드코딩 금지, _BRAND 단일 출처).
    changed = after[ys, xs]
    assert {tuple(c) for c in changed} <= {fz._BRAND}


# ─────────────── joint_inner_angle_deg 단일 출처 ───────────────


def test_joint_inner_angle_deg_known_answers():
    assert abs(fz.joint_inner_angle_deg((0, 1), (0, 0), (1, 0)) - 90.0) < 1e-6
    assert abs(fz.joint_inner_angle_deg((0, 10), (0, 0), (0, -10)) - 180.0) < 1e-6
    assert abs(fz.joint_inner_angle_deg((0, 10), (0, 0), (0, 10)) - 0.0) < 1e-6
    assert math.isnan(fz.joint_inner_angle_deg((0, 0), (0, 0), (1, 0)))
