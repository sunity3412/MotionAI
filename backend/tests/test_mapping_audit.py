"""Plan 01-17 T-1 mapping audit 단위 테스트.

검증 (numpy-only, mmpose / torch / mediapipe import 0):
  - rtmpose_to_h36m17.direct_map 13 tuple 의 좌우 정합
  - mediapipe_to_h36m17.direct_map 13 tuple 의 좌우 정합
  - mediapipe_to_h36m17.H36M_TO_COCO17_LIMB_PAIRS 12 tuple 의 좌우 정합
  - spike_rtmpose._h36m17_to_coco17_subset 사본 pairs 가 공유 pairs 와 set equality
  - skeleton.JOINT_ANGLES 8 entry 자체 정합 (left_* 의 a/vertex/c 모두 left_*, right 동일)
  - canonical fixture → detect_lr_swap swap_frame_ratio = 0 (verdict blocked/no-static-mapping-defect)
  - intentional swap fixture → detect_lr_swap swap_frame_ratio ≥ 0.30 (detect 자체 정합)

Plan 17 T-1 hard abort branch 박제 — 5 canonical assertion 모두 PASS 시 audit
report `mapping_audit_01-17.md` 의 verdict = blocked/no-static-mapping-defect,
T-2 mapping edits prohibited.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import numpy as np
import pytest

from backend.research.spikes import (
    mediapipe_to_h36m17 as mp_lift,
    rtmpose_to_h36m17 as rtm_lift,
    spike_measurement_trace as trace,
)
from sunity_shared.analysis.skeleton import JOINT_ANGLES, JOINT_KEYS, KEYPOINT_NAMES


# ── Canonical expected tuple 박제 (audit 기준) ────────────────────────────────


# RTMPose: (COCO idx, H36M idx) — 13 tuple, 좌우 정합 + nose → head central.
# 출처: rtmpose_to_h36m17.py:206-220 (직접 인용, audit 보고서 §2 표).
EXPECTED_RTMPOSE_DIRECT_MAP: tuple[tuple[int, int], ...] = (
    (12, 1),   # _COCO_R_HIP   → _H36M_R_HIP
    (14, 2),   # _COCO_R_KNEE  → _H36M_R_KNEE
    (16, 3),   # _COCO_R_ANKLE → _H36M_R_FOOT
    (11, 4),   # _COCO_L_HIP   → _H36M_L_HIP
    (13, 5),   # _COCO_L_KNEE  → _H36M_L_KNEE
    (15, 6),   # _COCO_L_ANKLE → _H36M_L_FOOT
    (0, 10),   # _COCO_NOSE    → _H36M_HEAD (central)
    (5, 11),   # _COCO_L_SHOULDER → _H36M_L_SHOULDER
    (7, 12),   # _COCO_L_ELBOW    → _H36M_L_ELBOW
    (9, 13),   # _COCO_L_WRIST    → _H36M_L_WRIST
    (6, 14),   # _COCO_R_SHOULDER → _H36M_R_SHOULDER
    (8, 15),   # _COCO_R_ELBOW    → _H36M_R_ELBOW
    (10, 16),  # _COCO_R_WRIST    → _H36M_R_WRIST
)

# MediaPipe: (MP idx, H36M idx) — 13 tuple. 출처: mediapipe_to_h36m17.py:184-198.
EXPECTED_MEDIAPIPE_DIRECT_MAP: tuple[tuple[int, int], ...] = (
    (24, 1),   # _MP_R_HIP   → _H36M_R_HIP
    (26, 2),   # _MP_R_KNEE  → _H36M_R_KNEE
    (28, 3),   # _MP_R_ANKLE → _H36M_R_FOOT
    (23, 4),   # _MP_L_HIP   → _H36M_L_HIP
    (25, 5),   # _MP_L_KNEE  → _H36M_L_KNEE
    (27, 6),   # _MP_L_ANKLE → _H36M_L_FOOT
    (0, 10),   # _MP_NOSE    → _H36M_HEAD
    (11, 11),  # _MP_L_SHOULDER → _H36M_L_SHOULDER
    (13, 12),  # _MP_L_ELBOW    → _H36M_L_ELBOW
    (15, 13),  # _MP_L_WRIST    → _H36M_L_WRIST
    (12, 14),  # _MP_R_SHOULDER → _H36M_R_SHOULDER
    (14, 15),  # _MP_R_ELBOW    → _H36M_R_ELBOW
    (16, 16),  # _MP_R_WRIST    → _H36M_R_WRIST
)

# 공유 H36M → COCO 12 tuple. 출처: mediapipe_to_h36m17.py:128-141.
EXPECTED_H36M_TO_COCO17_LIMB_PAIRS: tuple[tuple[int, int], ...] = (
    (11, 5),   # l_shoulder
    (14, 6),   # r_shoulder
    (12, 7),   # l_elbow
    (15, 8),   # r_elbow
    (13, 9),   # l_wrist
    (16, 10),  # r_wrist
    (4, 11),   # l_hip
    (1, 12),   # r_hip
    (5, 13),   # l_knee
    (2, 14),   # r_knee
    (6, 15),   # l_foot → left_ankle
    (3, 16),   # r_foot → right_ankle
)


# COCO-17 좌우 인덱스 (좌우 정합 판정용)
_COCO_LEFT_INDICES: set[int] = {1, 3, 5, 7, 9, 11, 13, 15}
_COCO_RIGHT_INDICES: set[int] = {2, 4, 6, 8, 10, 12, 14, 16}

# MediaPipe 33 좌우 인덱스 (좌우 정합 판정용)
_MP_LEFT_INDICES: set[int] = {1, 2, 3, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31}
_MP_RIGHT_INDICES: set[int] = {4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32}

# H36M 17 좌우 인덱스 (좌우 정합 판정용)
_H36M_LEFT_INDICES: set[int] = {4, 5, 6, 11, 12, 13}
_H36M_RIGHT_INDICES: set[int] = {1, 2, 3, 14, 15, 16}


def _coco_side(idx: int) -> str | None:
    if idx in _COCO_LEFT_INDICES:
        return "L"
    if idx in _COCO_RIGHT_INDICES:
        return "R"
    return None  # central / unused


def _mp_side(idx: int) -> str | None:
    if idx in _MP_LEFT_INDICES:
        return "L"
    if idx in _MP_RIGHT_INDICES:
        return "R"
    return None


def _h36m_side(idx: int) -> str | None:
    if idx in _H36M_LEFT_INDICES:
        return "L"
    if idx in _H36M_RIGHT_INDICES:
        return "R"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# TestRtmposeDirectMap
# ─────────────────────────────────────────────────────────────────────────────


class TestRtmposeDirectMap:
    """rtmpose_to_h36m17.py direct_map 13 tuple canonical 검증.

    Audit report §2 표 와 1:1 대응. Plan 16 left_elbow swap_ratio 1.00 root cause
    후보 #1 가 static defect 인지 박제.
    """

    def test_direct_map_tuple_set_matches_canonical(self) -> None:
        """source code 의 direct_map 13 tuple 이 canonical expected 와 정확 일치."""
        source = Path(rtm_lift.__file__).read_text(encoding="utf-8")
        # direct_map = [ (...), (...), ... ] 추출
        match = re.search(
            r"direct_map\s*=\s*\[(.*?)\]",
            source,
            flags=re.DOTALL,
        )
        assert match is not None, "rtmpose_to_h36m17.direct_map 정의를 찾을 수 없음"
        block = match.group(1)
        # AST 로 안전 평가 — 상수 이름을 정수로 치환한 사본을 만든다.
        # rtmpose_to_h36m17 모듈에서 상수값을 가져온다.
        ns = {k: getattr(rtm_lift, k) for k in dir(rtm_lift) if k.startswith("_COCO_") or k.startswith("_H36M_")}
        evaluated = eval("[" + block + "]", {"__builtins__": {}}, ns)  # noqa: S307 - 한정 상수만 노출
        actual = tuple(tuple(p) for p in evaluated)
        assert actual == EXPECTED_RTMPOSE_DIRECT_MAP, (
            f"rtmpose direct_map mismatch — expected {EXPECTED_RTMPOSE_DIRECT_MAP}, "
            f"actual {actual}"
        )
        # 13 row 박제
        assert len(actual) == 13

    def test_each_pair_preserves_left_right_side(self) -> None:
        """13 tuple 각 row 가 COCO 의 좌측 → H36M 의 좌측, 우측 → 우측 (central 예외)."""
        for coco_idx, h36m_idx in EXPECTED_RTMPOSE_DIRECT_MAP:
            coco_side = _coco_side(coco_idx)
            h36m_side = _h36m_side(h36m_idx)
            if coco_side is None or h36m_side is None:
                # central (예: nose → head). 둘 다 None 이어야 함.
                assert coco_side is None and h36m_side is None, (
                    f"central mismatch: COCO {coco_idx} side={coco_side}, "
                    f"H36M {h36m_idx} side={h36m_side}"
                )
                continue
            assert coco_side == h36m_side, (
                f"side mismatch at (COCO {coco_idx} {coco_side}) → "
                f"(H36M {h36m_idx} {h36m_side})"
            )

    def test_runtime_conversion_preserves_asymmetric_sentinel(self) -> None:
        """asymmetric sentinel → convert_rtmpose_coco17_to_h36m17 호출 후 좌우 보존."""
        # 17 keypoint, T=1, score=0.9 (>= 0.3 threshold)
        kp = np.zeros((1, 17, 3), dtype=float)
        # 좌우 별 고유 좌표 (정규화된 [0,1])
        # COCO indices 5/7/9 = left shoulder/elbow/wrist
        kp[0, 5, :2] = (0.10, 0.20)  # left_shoulder
        kp[0, 7, :2] = (0.11, 0.21)  # left_elbow
        kp[0, 9, :2] = (0.12, 0.22)  # left_wrist
        kp[0, 6, :2] = (0.90, 0.80)  # right_shoulder
        kp[0, 8, :2] = (0.91, 0.81)  # right_elbow
        kp[0, 10, :2] = (0.92, 0.82)  # right_wrist
        kp[0, :, 2] = 0.9
        out = rtm_lift.convert_rtmpose_coco17_to_h36m17(kp)
        # H36M l_elbow = 12, r_elbow = 15
        assert out[0, 12, 0] == pytest.approx(0.11), "l_elbow.x 보존 실패"
        assert out[0, 12, 1] == pytest.approx(0.21), "l_elbow.y 보존 실패"
        assert out[0, 15, 0] == pytest.approx(0.91), "r_elbow.x 보존 실패"
        assert out[0, 15, 1] == pytest.approx(0.81), "r_elbow.y 보존 실패"


# ─────────────────────────────────────────────────────────────────────────────
# TestMediapipeDirectMap
# ─────────────────────────────────────────────────────────────────────────────


class TestMediapipeDirectMap:
    """mediapipe_to_h36m17.py direct_map 13 tuple canonical 검증."""

    def test_direct_map_tuple_set_matches_canonical(self) -> None:
        source = Path(mp_lift.__file__).read_text(encoding="utf-8")
        match = re.search(
            r"direct_map\s*=\s*\[(.*?)\]",
            source,
            flags=re.DOTALL,
        )
        assert match is not None, "mediapipe_to_h36m17.direct_map 정의를 찾을 수 없음"
        block = match.group(1)
        ns = {k: getattr(mp_lift, k) for k in dir(mp_lift) if k.startswith("_MP_") or k.startswith("_H36M_")}
        evaluated = eval("[" + block + "]", {"__builtins__": {}}, ns)  # noqa: S307
        actual = tuple(tuple(p) for p in evaluated)
        assert actual == EXPECTED_MEDIAPIPE_DIRECT_MAP, (
            f"mediapipe direct_map mismatch — expected {EXPECTED_MEDIAPIPE_DIRECT_MAP}, "
            f"actual {actual}"
        )
        assert len(actual) == 13

    def test_each_pair_preserves_left_right_side(self) -> None:
        for mp_idx, h36m_idx in EXPECTED_MEDIAPIPE_DIRECT_MAP:
            mp_side = _mp_side(mp_idx)
            h36m_side = _h36m_side(h36m_idx)
            if mp_side is None or h36m_side is None:
                # nose(0) → head(10). 둘 다 None 이어야 함.
                assert mp_side is None and h36m_side is None, (
                    f"central mismatch: MP {mp_idx} side={mp_side}, "
                    f"H36M {h36m_idx} side={h36m_side}"
                )
                continue
            assert mp_side == h36m_side, (
                f"side mismatch at (MP {mp_idx} {mp_side}) → "
                f"(H36M {h36m_idx} {h36m_side})"
            )

    def test_runtime_conversion_preserves_asymmetric_sentinel(self) -> None:
        """33 landmark sentinel → convert_mp33_to_h36m17 호출 후 좌우 보존."""
        lm = np.zeros((1, 33, 2), dtype=float)
        # MP 13/14 = left/right elbow
        lm[0, 13, :] = (0.11, 0.21)  # left_elbow
        lm[0, 14, :] = (0.91, 0.81)  # right_elbow
        # 필요한 보조 keypoint (visibility / NaN propagation 회피용 baseline)
        for idx in (0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28):
            if idx not in (13, 14):
                lm[0, idx, :] = (0.5, 0.5)
        out = mp_lift.convert_mp33_to_h36m17(lm)
        assert out[0, 12, 0] == pytest.approx(0.11), "l_elbow.x 보존 실패"
        assert out[0, 12, 1] == pytest.approx(0.21), "l_elbow.y 보존 실패"
        assert out[0, 15, 0] == pytest.approx(0.91), "r_elbow.x 보존 실패"
        assert out[0, 15, 1] == pytest.approx(0.81), "r_elbow.y 보존 실패"


# ─────────────────────────────────────────────────────────────────────────────
# TestSharedLimbPairs
# ─────────────────────────────────────────────────────────────────────────────


class TestSharedLimbPairs:
    """공유 H36M_TO_COCO17_LIMB_PAIRS + spike_rtmpose private copy 정합."""

    def test_h36m_to_coco17_limb_pairs_matches_canonical(self) -> None:
        actual = tuple(mp_lift.H36M_TO_COCO17_LIMB_PAIRS)
        assert actual == EXPECTED_H36M_TO_COCO17_LIMB_PAIRS, (
            f"H36M_TO_COCO17_LIMB_PAIRS mismatch — "
            f"expected {EXPECTED_H36M_TO_COCO17_LIMB_PAIRS}, actual {actual}"
        )
        assert len(actual) == 12

    def test_each_pair_preserves_left_right_side(self) -> None:
        for h36m_idx, coco_idx in EXPECTED_H36M_TO_COCO17_LIMB_PAIRS:
            h36m_side = _h36m_side(h36m_idx)
            coco_side = _coco_side(coco_idx)
            assert h36m_side is not None and coco_side is not None, (
                f"limb pair는 좌우 indexed: H36M {h36m_idx} / COCO {coco_idx}"
            )
            assert h36m_side == coco_side, (
                f"side mismatch at (H36M {h36m_idx} {h36m_side}) → "
                f"(COCO {coco_idx} {coco_side})"
            )

    def test_spike_rtmpose_private_copy_matches_shared_pairs(self) -> None:
        """spike_rtmpose._h36m17_to_coco17_subset 의 pairs 가 공유 pairs 와 set equality."""
        # spike_rtmpose 모듈을 import 하지 않고 source 에서 추출 (mmpose 의존 회피).
        spike_path = Path("backend/research/spikes/spike_rtmpose.py")
        source = spike_path.read_text(encoding="utf-8")
        # 함수 _h36m17_to_coco17_subset 내부 — `pairs = (` 부터 balanced 파싱.
        idx = source.find("def _h36m17_to_coco17_subset")
        assert idx >= 0, "spike_rtmpose._h36m17_to_coco17_subset 정의를 찾을 수 없음"
        body = source[idx:]
        anchor = body.find("pairs = (")
        assert anchor >= 0, "pairs = ( 시작 위치를 찾을 수 없음"
        # 'pairs = (' 다음 위치부터 시작 — depth 1 에서 시작
        start = anchor + len("pairs = (")
        depth = 1
        pos = start
        while pos < len(body) and depth > 0:
            ch = body[pos]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            pos += 1
        # depth 가 0 으로 떨어진 직전이 닫는 ')'. pos-1 이 ')' 의 인덱스.
        assert depth == 0, "pairs (...) 의 닫는 ')' 를 찾을 수 없음"
        block = body[start : pos - 1]
        evaluated = eval("(" + block + ")", {"__builtins__": {}}, {})  # noqa: S307
        actual = tuple(tuple(p) for p in evaluated)
        # set equality (공유 pairs 와 정확히 동일한 12 tuple 집합)
        assert set(actual) == set(EXPECTED_H36M_TO_COCO17_LIMB_PAIRS), (
            f"spike_rtmpose private copy 가 공유 pairs 와 다름 — "
            f"actual={set(actual)}, expected={set(EXPECTED_H36M_TO_COCO17_LIMB_PAIRS)}"
        )
        assert len(actual) == 12


# ─────────────────────────────────────────────────────────────────────────────
# TestJointAnglesSelfConsistency
# ─────────────────────────────────────────────────────────────────────────────


class TestJointAnglesSelfConsistency:
    """skeleton.JOINT_ANGLES 8 entry 의 (a, vertex, c) 자체 정합."""

    def test_vertex_matches_key(self) -> None:
        """JOINT_ANGLES[key] = (a, vertex, c) 에서 vertex == key 박제."""
        for key, (a, vertex, c) in JOINT_ANGLES.items():
            assert vertex == key, (
                f"JOINT_ANGLES['{key}'] vertex='{vertex}' must equal key='{key}'"
            )

    def test_left_right_self_consistency(self) -> None:
        """left_* key 면 a/vertex/c 모두 left_*, right_* 동일."""
        for key, (a, vertex, c) in JOINT_ANGLES.items():
            if key.startswith("left_"):
                for name in (a, vertex, c):
                    assert name.startswith("left_"), (
                        f"JOINT_ANGLES['{key}']: '{name}' must start with 'left_'"
                    )
            elif key.startswith("right_"):
                for name in (a, vertex, c):
                    assert name.startswith("right_"), (
                        f"JOINT_ANGLES['{key}']: '{name}' must start with 'right_'"
                    )
            else:
                pytest.fail(f"unexpected JOINT_ANGLES key: '{key}'")

    def test_eight_entries_cover_four_pairs(self) -> None:
        """JOINT_ANGLES = 8 entry, left/right 4 쌍 (elbow/shoulder/hip/knee)."""
        assert len(JOINT_ANGLES) == 8
        assert set(JOINT_ANGLES.keys()) == set(JOINT_KEYS)
        # 4 쌍 정합
        pairs = (
            ("left_elbow", "right_elbow"),
            ("left_shoulder", "right_shoulder"),
            ("left_hip", "right_hip"),
            ("left_knee", "right_knee"),
        )
        flat = tuple(j for pair in pairs for j in pair)
        assert set(flat) == set(JOINT_KEYS)

    def test_referenced_keypoints_in_skeleton(self) -> None:
        """JOINT_ANGLES 의 a/vertex/c 가 모두 skeleton.KEYPOINT_NAMES 에 존재."""
        kp_set = set(KEYPOINT_NAMES)
        for key, (a, vertex, c) in JOINT_ANGLES.items():
            for name in (a, vertex, c):
                assert name in kp_set, (
                    f"JOINT_ANGLES['{key}']: '{name}' not in skeleton.KEYPOINT_NAMES"
                )


# ─────────────────────────────────────────────────────────────────────────────
# TestStaticMappingAbortGate
# ─────────────────────────────────────────────────────────────────────────────


def _build_canonical_angle_matrices_via_pipeline(
    T: int = 20,
) -> tuple[np.ndarray, np.ndarray]:
    """canonical pipeline 으로 두 (T, 8) angle matrix 산출.

    좌우 좌표가 모두 고유한 asymmetric COCO/MP keypoint sentinel 을 두 변환 path
    각각에 통과시킨 후 features.compute_joint_angles 로 (T, 8) angle matrix
    추출. 양 path 모두 동일 semantic 입력 → 양 path 출력 부호가 동일 → swap = 0.
    """
    from sunity_shared.analysis.features import compute_joint_angles

    rng = np.random.default_rng(seed=20260601)

    # COCO 17 keypoint 좌우 고유 좌표 (T frame)
    # 좌측 shoulder/elbow/wrist/hip/knee/ankle 모두 (0.1~0.4) 범위
    # 우측 동일 joint 모두 (0.6~0.9) 범위
    coco_kp = np.zeros((T, 17, 3), dtype=float)
    coco_kp[:, :, 2] = 0.9  # score >= 0.3 threshold
    # frame 별 약간의 변동 (jitter) — swap detection 의 NaN/zero edge 회피
    jitter = rng.uniform(-0.005, 0.005, size=(T, 17, 2))
    for t in range(T):
        # left side (COCO 5, 7, 9, 11, 13, 15)
        coco_kp[t, 5, :2] = (0.20 + jitter[t, 5, 0], 0.30 + jitter[t, 5, 1])
        coco_kp[t, 7, :2] = (0.22 + jitter[t, 7, 0], 0.50 + jitter[t, 7, 1])
        coco_kp[t, 9, :2] = (0.24 + jitter[t, 9, 0], 0.70 + jitter[t, 9, 1])
        coco_kp[t, 11, :2] = (0.30 + jitter[t, 11, 0], 0.55 + jitter[t, 11, 1])
        coco_kp[t, 13, :2] = (0.32 + jitter[t, 13, 0], 0.75 + jitter[t, 13, 1])
        coco_kp[t, 15, :2] = (0.34 + jitter[t, 15, 0], 0.95 + jitter[t, 15, 1])
        # right side (COCO 6, 8, 10, 12, 14, 16) — 좌측과 다른 좌표
        coco_kp[t, 6, :2] = (0.80 + jitter[t, 6, 0], 0.32 + jitter[t, 6, 1])
        coco_kp[t, 8, :2] = (0.78 + jitter[t, 8, 0], 0.48 + jitter[t, 8, 1])
        coco_kp[t, 10, :2] = (0.76 + jitter[t, 10, 0], 0.68 + jitter[t, 10, 1])
        coco_kp[t, 12, :2] = (0.70 + jitter[t, 12, 0], 0.57 + jitter[t, 12, 1])
        coco_kp[t, 14, :2] = (0.72 + jitter[t, 14, 0], 0.77 + jitter[t, 14, 1])
        coco_kp[t, 16, :2] = (0.74 + jitter[t, 16, 0], 0.97 + jitter[t, 16, 1])
        coco_kp[t, 0, :2] = (0.50, 0.10)  # nose

    # MP 33 landmark — COCO 와 동일 semantic 좌표 (left/right 좌표가 동일하도록 박제)
    mp_lm = np.zeros((T, 33, 2), dtype=float)
    for t in range(T):
        # left side (MP 11, 13, 15, 23, 25, 27) — COCO 와 동일 좌표
        mp_lm[t, 11, :] = coco_kp[t, 5, :2]
        mp_lm[t, 13, :] = coco_kp[t, 7, :2]
        mp_lm[t, 15, :] = coco_kp[t, 9, :2]
        mp_lm[t, 23, :] = coco_kp[t, 11, :2]
        mp_lm[t, 25, :] = coco_kp[t, 13, :2]
        mp_lm[t, 27, :] = coco_kp[t, 15, :2]
        # right side (MP 12, 14, 16, 24, 26, 28)
        mp_lm[t, 12, :] = coco_kp[t, 6, :2]
        mp_lm[t, 14, :] = coco_kp[t, 8, :2]
        mp_lm[t, 16, :] = coco_kp[t, 10, :2]
        mp_lm[t, 24, :] = coco_kp[t, 12, :2]
        mp_lm[t, 26, :] = coco_kp[t, 14, :2]
        mp_lm[t, 28, :] = coco_kp[t, 16, :2]
        mp_lm[t, 0, :] = coco_kp[t, 0, :2]

    # RTMPose path: convert_rtmpose_coco17_to_h36m17 → h36m17_to_coco17_subset (3D)
    # but the 2D rtmpose path produces (T, 17, 2) H36M coords; we need (T, 17, 3) xyz
    # to feed h36m17_to_coco17_subset. 본 sentinel 은 z=0 으로 박제 (compute_joint_angles
    # 는 (T, 17, 4=xyz+conf) 입력 받음).
    h36m_rtm = rtm_lift.convert_rtmpose_coco17_to_h36m17(coco_kp)  # (T, 17, 2)
    h36m_rtm_xyz = np.concatenate([h36m_rtm, np.zeros((T, 17, 1))], axis=-1)  # (T, 17, 3)
    coco17_rtm = mp_lift.h36m17_to_coco17_subset(h36m_rtm_xyz)  # (T, 17, 4)
    rtm_angles = compute_joint_angles(coco17_rtm)  # (T, 8)

    # MediaPipe path: convert_mp33_to_h36m17 → h36m17_to_coco17_subset
    h36m_mp = mp_lift.convert_mp33_to_h36m17(mp_lm)  # (T, 17, 2)
    h36m_mp_xyz = np.concatenate([h36m_mp, np.zeros((T, 17, 1))], axis=-1)  # (T, 17, 3)
    coco17_mp = mp_lift.h36m17_to_coco17_subset(h36m_mp_xyz)  # (T, 17, 4)
    mp_angles = compute_joint_angles(coco17_mp)  # (T, 8)

    return rtm_angles, mp_angles


class TestStaticMappingAbortGate:
    """5 canonical assertion 모두 PASS → abort verdict + intentional swap fixture detect."""

    def test_all_five_canonical_sources_match_expected(self) -> None:
        """5 mapping source 모두 canonical → mapping_edits_allowed = False 박제."""
        canonical_results = {
            "rtmpose_direct_map": True,  # 위 TestRtmposeDirectMap 통과 가정
            "mediapipe_direct_map": True,  # TestMediapipeDirectMap 통과 가정
            "h36m_to_coco17_limb_pairs": (
                tuple(mp_lift.H36M_TO_COCO17_LIMB_PAIRS)
                == EXPECTED_H36M_TO_COCO17_LIMB_PAIRS
            ),
            "joint_angles_self_consistent": all(
                v == k and a.startswith(k.split("_")[0]) and c.startswith(k.split("_")[0])
                for k, (a, v, c) in JOINT_ANGLES.items()
            ),
        }
        # spike_rtmpose 사본 (source 추출, balanced 파싱)
        spike_path = Path("backend/research/spikes/spike_rtmpose.py")
        source = spike_path.read_text(encoding="utf-8")
        idx = source.find("def _h36m17_to_coco17_subset")
        assert idx >= 0
        body = source[idx:]
        anchor = body.find("pairs = (")
        assert anchor >= 0
        start = anchor + len("pairs = (")
        depth = 1
        pos = start
        while pos < len(body) and depth > 0:
            ch = body[pos]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            pos += 1
        block = body[start : pos - 1]
        evaluated = eval("(" + block + ")", {"__builtins__": {}}, {})  # noqa: S307
        canonical_results["spike_rtmpose_private_copy"] = (
            set(tuple(p) for p in evaluated) == set(EXPECTED_H36M_TO_COCO17_LIMB_PAIRS)
        )
        # 5 source 모두 canonical → verdict = blocked/no-static-mapping-defect
        assert all(canonical_results.values()), (
            f"canonical assertion 일부 실패: {canonical_results}"
        )

    def test_canonical_pipeline_asymmetric_sentinel_swap_zero(self) -> None:
        """canonical pipeline + asymmetric sentinel → detect_lr_swap = 0 박제.

        Plan 17 T-1 step 7 — canonical mapping 인 stub fixture 에서 두 lift path
        가 동일 sentinel 을 받으면 detect_lr_swap = 0.0 (swap 없음). 이것이
        static mapping defect 가 아님을 보조 증명.
        """
        rtm_angles, mp_angles = _build_canonical_angle_matrices_via_pipeline(T=20)
        result = trace.detect_lr_swap(rtm_angles, mp_angles)
        # swap_frame_ratio (4 pair 평균) ≤ 0.05
        assert result["swap_frame_ratio"] <= 0.05, (
            f"canonical pipeline 에서 swap_frame_ratio = {result['swap_frame_ratio']} "
            f"(expected ≤ 0.05)"
        )
        # swap_frame_ratio_per_pair 4 pair 모두 ≤ 0.05
        for pair_name, ratio in result["swap_frame_ratio_per_pair"].items():
            assert ratio <= 0.05, (
                f"canonical pipeline pair {pair_name} swap_ratio = {ratio} "
                f"(expected ≤ 0.05)"
            )

    def test_intentional_swap_fixture_detected(self) -> None:
        """의도적 swap mutation → detect_lr_swap elbow pair ratio ≥ 0.30 박제.

        detect 함수 자체 정합 검증 — swap 이 존재할 때 ratio 가 정상 작동.
        """
        rtm_angles, mp_angles = _build_canonical_angle_matrices_via_pipeline(T=20)
        # mp_angles 의 left_elbow (col 0) 와 right_elbow (col 1) 를 의도적으로 교환.
        # JOINT_KEYS 순서: left_elbow=0, right_elbow=1, left_shoulder=2, right_shoulder=3,
        #                  left_hip=4, right_hip=5, left_knee=6, right_knee=7
        mp_swapped = mp_angles.copy()
        mp_swapped[:, [0, 1]] = mp_swapped[:, [1, 0]]
        result = trace.detect_lr_swap(rtm_angles, mp_swapped)
        # elbow pair swap_ratio 가 임계 0.30 이상으로 detected
        assert (
            result["swap_frame_ratio_per_pair"]["left_elbow_vs_right_elbow"] >= 0.30
        ), (
            f"intentional swap mutation detect 실패 — elbow swap_ratio = "
            f"{result['swap_frame_ratio_per_pair']['left_elbow_vs_right_elbow']} "
            f"(expected ≥ 0.30)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TestAuditReportArtifacts
# ─────────────────────────────────────────────────────────────────────────────


class TestAuditReportArtifacts:
    """audit 보고서 mapping_audit_01-17.md 의 핵심 섹션 + verdict 존재."""

    # 파일 기준 절대 경로 — 2026-08-28 수리. 상대 경로("backend/research/...")는
    # pytest 를 리포 루트에서 돌릴 때만 맞고 backend/ 에서 돌리면 못 찾는다
    # (실행 위치가 판정을 바꾸면 그건 테스트가 아니다). __file__ = backend/tests/*.py.
    REPORT_PATH = (
        Path(__file__).resolve().parents[1]
        / "research" / "spikes" / "reports" / "mapping_audit_01-17.md"
    )

    def test_audit_report_exists(self) -> None:
        assert self.REPORT_PATH.exists(), (
            f"audit 보고서 누락: {self.REPORT_PATH}"
        )
        assert self.REPORT_PATH.stat().st_size > 0

    def test_audit_report_has_static_mapping_verdict_section(self) -> None:
        text = self.REPORT_PATH.read_text(encoding="utf-8")
        assert "## (7) Static Mapping Verdict" in text
        assert "blocked/no-static-mapping-defect" in text

    def test_audit_report_has_t2_eligibility_section(self) -> None:
        text = self.REPORT_PATH.read_text(encoding="utf-8")
        assert "## (9) T-2 Eligibility" in text
        assert "eligible: false" in text
        assert "mapping_edits_allowed: false" in text

    def test_audit_report_no_multiview_keywords(self) -> None:
        """본문 (heading 제외) 에 multi-view / 다각도 / multi camera 0건."""
        text = "\n".join(
            line for line in self.REPORT_PATH.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        )
        matches = re.findall(r"multi.view|다각도|multi camera", text, flags=re.IGNORECASE)
        assert len(matches) == 0, f"multi-view 키워드 발견: {matches}"


# ─────────────────────────────────────────────────────────────────────────────
# Sanity: numpy/skeleton 외 heavy import 0
# ─────────────────────────────────────────────────────────────────────────────


def test_no_heavy_imports_in_this_module() -> None:
    """본 테스트 모듈이 mmpose / torch / mediapipe 를 import 하지 않음 박제."""
    src = Path(__file__).read_text(encoding="utf-8")
    # 코멘트 제거
    src_no_comment = "\n".join(
        line for line in src.splitlines() if not line.lstrip().startswith("#")
    )
    forbidden_patterns = [r"^\s*import\s+mmpose", r"^\s*from\s+mmpose",
                         r"^\s*import\s+torch", r"^\s*from\s+torch\b",
                         r"^\s*import\s+mediapipe", r"^\s*from\s+mediapipe"]
    for pat in forbidden_patterns:
        matches = re.findall(pat, src_no_comment, flags=re.MULTILINE)
        assert len(matches) == 0, f"forbidden import pattern: {pat} → {matches}"
