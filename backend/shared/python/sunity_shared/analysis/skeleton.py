"""17 keypoint(COCO/ViTPose) 골격 정의 + 관절각 + 파트 그룹.

contract.md §4 partScores 키 = 상체/코어/하체 (design.md §8). JointScore.key
는 아래 관절명, labelKo 는 한글 라벨.
"""

from __future__ import annotations

# COCO 17 keypoint 순서 (ViTPose 출력과 동일 인덱스)
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
NUM_KEYPOINTS = len(KEYPOINT_NAMES)
_IDX = {name: i for i, name in enumerate(KEYPOINT_NAMES)}


def kp_index(name: str) -> int:
    return _IDX[name]


# 관절각: vertex 에서 (a-vertex) 와 (c-vertex) 사이 각. (a, vertex, c)
# key = JointScore.key (contract). 폴스포츠 자세 평가에 의미 있는 8개.
JOINT_ANGLES: dict[str, tuple[str, str, str]] = {
    "left_elbow": ("left_shoulder", "left_elbow", "left_wrist"),
    "right_elbow": ("right_shoulder", "right_elbow", "right_wrist"),
    "left_shoulder": ("left_elbow", "left_shoulder", "left_hip"),
    "right_shoulder": ("right_elbow", "right_shoulder", "right_hip"),
    "left_hip": ("left_shoulder", "left_hip", "left_knee"),
    "right_hip": ("right_shoulder", "right_hip", "right_knee"),
    "left_knee": ("left_hip", "left_knee", "left_ankle"),
    "right_knee": ("right_hip", "right_knee", "right_ankle"),
}
# 특징벡터/점수에서 항상 이 순서를 사용
JOINT_KEYS = tuple(JOINT_ANGLES.keys())
NUM_JOINTS = len(JOINT_KEYS)

JOINT_LABEL_KO: dict[str, str] = {
    "left_elbow": "왼쪽 팔꿈치",
    "right_elbow": "오른쪽 팔꿈치",
    "left_shoulder": "왼쪽 어깨",
    "right_shoulder": "오른쪽 어깨",
    "left_hip": "왼쪽 고관절",
    "right_hip": "오른쪽 고관절",
    "left_knee": "왼쪽 무릎",
    "right_knee": "오른쪽 무릎",
}

# 파트 그룹 (design.md §8: 상체/코어/하체). contract partScores 키와 동일 문자열.
PART_UPPER = "상체"
PART_CORE = "코어"
PART_LOWER = "하체"
PARTS = (PART_UPPER, PART_CORE, PART_LOWER)

JOINT_TO_PART: dict[str, str] = {
    "left_elbow": PART_UPPER,
    "right_elbow": PART_UPPER,
    "left_shoulder": PART_UPPER,
    "right_shoulder": PART_UPPER,
    "left_hip": PART_CORE,
    "right_hip": PART_CORE,
    "left_knee": PART_LOWER,
    "right_knee": PART_LOWER,
}
