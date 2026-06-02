"""RTMW 133 wholebody keypoint 인덱스 표 (Plan 01-21 Task 1).

출처: COCO-WholeBody 표준 (mmpose projects/rtmw/configs + rtmlib README).
body 17 + foot 6 + face 68 + hand 42 = 133 총계.

참조:
  - https://github.com/jin-s13/COCO-WholeBody (표준 정의)
  - https://github.com/Tau-J/rtmlib (rtmlib RTMW 구현)
  - mmpose projects/rtmw — RTMW 133 wholebody SimCC 모델

RTMW 133 키포인트 순서 = COCO-WholeBody v1 표준:
  0-16:   body 17개 (COCO-17 표준 순서)
  17-22:  foot 6개 (left/right big_toe, small_toe, heel)
  23-90:  face 68개 (WFLW 68-point face landmark)
  91-111: left hand 21개 (root + 5 finger × 4 joint = 21)
  112-132: right hand 21개 (root + 5 finger × 4 joint = 21)

D-20 박제: plan 01-21 — RTMW 133 원본 보존 + COCO-17 + 폴 확장.
"""

from __future__ import annotations

# ── 총수 상수 ─────────────────────────────────────────────────────────────
RTMW_133 = 133

# ── body 17 (COCO-17 표준 순서, indices 0-16) ─────────────────────────────
# skeleton.py KEYPOINT_NAMES 와 동일 순서 강제
_BODY_17: dict[str, int] = {
    "nose":            0,
    "left_eye":        1,
    "right_eye":       2,
    "left_ear":        3,
    "right_ear":       4,
    "left_shoulder":   5,
    "right_shoulder":  6,
    "left_elbow":      7,
    "right_elbow":     8,
    "left_wrist":      9,
    "right_wrist":     10,
    "left_hip":        11,
    "right_hip":       12,
    "left_knee":       13,
    "right_knee":      14,
    "left_ankle":      15,
    "right_ankle":     16,
}

# ── foot 6 (COCO-WholeBody foot, indices 17-22) ───────────────────────────
# 순서: left big_toe, left small_toe, left heel, right big_toe, right small_toe, right heel
_FOOT_6: dict[str, int] = {
    "left_big_toe":    17,
    "left_small_toe":  18,
    "left_heel":       19,
    "right_big_toe":   20,
    "right_small_toe": 21,
    "right_heel":      22,
}

# ── face 68 (WFLW 68-point, indices 23-90) ───────────────────────────────
# mmpose COCO-WholeBody face landmarks (순서: 턱선/눈썹/코/눈/입/동공 순)
_FACE_68: dict[str, int] = {f"face_{i}": 23 + i for i in range(68)}

# ── left hand 21 (COCO-WholeBody hand, indices 91-111) ───────────────────
# 순서: wrist(root) + thumb(4) + index(4) + middle(4) + ring(4) + little(4)
# 각 손가락: cmc/mcp → mcp/pip → ip/dip → tip (thumb: cmc,mcp,ip,tip; others: mcp,pip,dip,tip)
# [CITED: https://github.com/jin-s13/COCO-WholeBody/blob/master/data_format.md]
_LEFT_HAND_21: dict[str, int] = {
    "left_hand_root":           91,   # wrist (hand root)
    "left_thumb_cmc":           92,
    "left_thumb_mcp":           93,
    "left_thumb_ip":            94,
    "left_thumb_tip":           95,
    "left_index_finger_mcp":    96,
    "left_index_finger_pip":    97,
    "left_index_finger_dip":    98,
    "left_index_finger_tip":    99,
    "left_middle_finger_mcp":  100,
    "left_middle_finger_pip":  101,
    "left_middle_finger_dip":  102,
    "left_middle_finger_tip":  103,
    "left_ring_finger_mcp":    104,
    "left_ring_finger_pip":    105,
    "left_ring_finger_dip":    106,
    "left_ring_finger_tip":    107,
    "left_little_finger_mcp":  108,
    "left_little_finger_pip":  109,
    "left_little_finger_dip":  110,
    "left_little_finger_tip":  111,
}

# ── right hand 21 (COCO-WholeBody hand, indices 112-132) ─────────────────
_RIGHT_HAND_21: dict[str, int] = {
    "right_hand_root":            112,
    "right_thumb_cmc":            113,
    "right_thumb_mcp":            114,
    "right_thumb_ip":             115,
    "right_thumb_tip":            116,
    "right_index_finger_mcp":    117,
    "right_index_finger_pip":    118,
    "right_index_finger_dip":    119,
    "right_index_finger_tip":    120,
    "right_middle_finger_mcp":   121,
    "right_middle_finger_pip":   122,
    "right_middle_finger_dip":   123,
    "right_middle_finger_tip":   124,
    "right_ring_finger_mcp":     125,
    "right_ring_finger_pip":     126,
    "right_ring_finger_dip":     127,
    "right_ring_finger_tip":     128,
    "right_little_finger_mcp":   129,
    "right_little_finger_pip":   130,
    "right_little_finger_dip":   131,
    "right_little_finger_tip":   132,
}

# ── 최종 통합 인덱스 표 ───────────────────────────────────────────────────
RTMW_KEYPOINT_INDICES: dict[str, int] = {
    **_BODY_17,    # 17 entries (0-16)
    **_FOOT_6,     # 6 entries (17-22)
    **_FACE_68,    # 68 entries (23-90)
    **_LEFT_HAND_21,   # 21 entries (91-111)
    **_RIGHT_HAND_21,  # 21 entries (112-132)
}

# ── 불변식 검증 (모듈 로드 시 1회) ──────────────────────────────────────
assert len(RTMW_KEYPOINT_INDICES) == 133, (
    f"RTMW_KEYPOINT_INDICES 총 개수 = {len(RTMW_KEYPOINT_INDICES)}, 133 이어야 함"
)
assert len(set(RTMW_KEYPOINT_INDICES.values())) == 133, (
    "RTMW_KEYPOINT_INDICES 인덱스 중복 있음 (0~132 각 1회 허용)"
)
