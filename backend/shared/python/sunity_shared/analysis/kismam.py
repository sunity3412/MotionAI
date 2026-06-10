"""KISMAM — 관절 편차(도) → 0~100 점수 + 파트 점수 + Top-3 교정포인트.

ml_CLAUDE.md:
  1. Z-score: 정상 범위(관절별 허용 편차 tol) 대비 벗어난 정도 z = dev/tol
  2. 가중치: 관절별 weight (폴스포츠 중요도)
  3. Top-3: 점수 낮은(편차 큰) 관절 3개를 코칭 포인트로

점수 매핑: score = 100·exp(-½·z²) — Z-score 가우시안 감쇠.
  z=0→100, z=1(tol)→61, z=2→14, z=3→1. 단조·평활.
모든 점수는 0~100 정수 (contract.md §0).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from .skeleton import (
    JOINT_KEYS,
    JOINT_LABEL_KO,
    JOINT_TO_PART,
    PARTS,
)


# Phase 12 Wave 0A R2/R4 (Codex 직접 리뷰 2026-06-10) — target_angle 산출 출처.
# mode1 = 정은지 measured / mode3_progress = 이전 영상 measured /
# mode3_first 의 extension-required joint = IPSF 180° / 그 외 = 기준 없음.
# 3-way lockstep: app/src/types/analysis.ts JointScore.targetSource (4 enum) +
# docs/contract.md §JointScore.
TargetSource = Literal[
    "reference_motion",
    "previous_analysis",
    "extension_requirement",
    "unavailable",
]

# 허용 편차(도) = Z-score 스케일. dev 가 이만큼 벗어나면 z=1 (점수 ~61).
# IPSF Code of Points 는 관절 각도/스플릿에 20도 허용 오차를 적용
# (docs/research/pole-aerial-sports.md §4) — 이를 단일 기준으로 채택.
# 관절별 중요도 차등은 tolerance 가 아니라 checkpoint weight 로 표현한다.
_IPSF_TOLERANCE_DEG = 20.0
DEFAULT_TOLERANCE_DEG: dict[str, float] = {k: _IPSF_TOLERANCE_DEG for k in JOINT_KEYS}
DEFAULT_WEIGHT: dict[str, float] = {k: 1.0 for k in JOINT_KEYS}

# 교정 포인트 제목 시드 (관절 → 코칭 초점). assemble.build_tips 가
# `f"{a.label_ko} {COACHING_FOCUS[a.key]}"` 박제 시 사용 — JOINT_LABEL_KO 에
# 이미 부위 한글이 포함되므로 (예: "오른쪽 어깨") COACHING_FOCUS 값에서는
# 부위 키워드 (어깨/팔꿈치/고관절/무릎) 를 제외해서 박제 — 미박제 시 중복 발현
# (예: "오른쪽 어깨 어깨 안정성", 2026-06-06 belle 스크린샷 박제).
COACHING_FOCUS: dict[str, str] = {
    "left_elbow": "정렬",
    "right_elbow": "정렬",
    "left_shoulder": "안정성",
    "right_shoulder": "안정성",
    "left_hip": "가동",
    "right_hip": "가동",
    "left_knee": "신전",
    "right_knee": "신전",
}


# 관절 종류별 (delta<0 일 때, delta>0 일 때) 방향 라벨.
# delta = current_angle - target_angle (deg). 음수 → 사용자 각도가 작음 → 첫 라벨.
# 도메인 컨벤션은 #7-follow ML 단에서 정밀화. 여기선 폴스포츠 코칭에 흔한 표현 기본값.
JOINT_DIRECTION_PAIRS: dict[str, tuple[str, str]] = {
    "left_knee": ("extend", "flex"),
    "right_knee": ("extend", "flex"),
    "left_elbow": ("extend", "flex"),
    "right_elbow": ("extend", "flex"),
    "left_hip": ("open", "close"),
    "right_hip": ("open", "close"),
    "left_shoulder": ("raise", "lower"),
    "right_shoulder": ("raise", "lower"),
}


def _direction_for(joint_key: str, signed_delta_deg: float) -> str | None:
    pair = JOINT_DIRECTION_PAIRS.get(joint_key)
    if pair is None or signed_delta_deg == 0:
        return None
    return pair[0] if signed_delta_deg < 0 else pair[1]


def score_from_deviation(
    deviation_deg: float, tolerance_deg: float = _IPSF_TOLERANCE_DEG
) -> int:
    """편차(도) → 0~100 점수 (가우시안 감쇠 z=dev/tol). assess 와 동일 매핑.
    차원 점수(dimensions.py)도 이 함수를 공유해 점수 스케일을 일관되게 유지한다."""
    z = float(deviation_deg) / max(tolerance_deg, 1e-6)
    return max(0, min(100, int(round(100.0 * float(np.exp(-0.5 * z * z))))))


@dataclass(frozen=True)
class JointAssessment:
    key: str
    label_ko: str
    score: int          # 0~100
    deviation_deg: float  # 절대값 (KISMAM Z-score 입력)
    part: str           # 상체/코어/하체
    # 구조화 가이드 (옵셔널) — assess() 가 user/reference 각도를 받으면 채워짐.
    # 없으면 None, contract.md JointScore 옵셔널 필드와 동일 의미.
    current_angle: float | None = None
    target_angle: float | None = None
    signed_delta_deg: float | None = None
    direction: str | None = None
    # Phase 12 Wave 0A R2/R4 (Codex 직접 리뷰 2026-06-10): target 산출 출처.
    # assemble.build_joints 가 camelCase 'targetSource' 로 JointScore 에 export.
    target_source: TargetSource | None = None


def assess(
    deviation_deg,
    tolerance: dict | None = None,
    user_angles: dict | None = None,
    reference_angles: dict | None = None,
    target_source: TargetSource | None = None,
) -> list[JointAssessment]:
    """관절별 편차(JOINT_KEYS 순서, 길이 NUM_JOINTS) → JointAssessment 목록.

    user_angles/reference_angles 가 주어지면(관절키→평균각도 dict) 각 관절에
    current/target/signed_delta/direction 을 함께 채운다. 없으면 None.

    Phase 12 Wave 0A R2/R4 (Codex 직접 리뷰 2026-06-10):
      target_source 가 주어지면 모든 JointAssessment 의 target_source 박제.
      mode3 first 의 non-extension joint (= reference_angles 에 key 없음) →
      target_source='unavailable', target_angle=None 자동 분기 (extension_requirement
      caller 의 의도 = 'extension 안 필요한 관절은 기준 없음').
    """
    dev = np.asarray(deviation_deg, dtype=float)
    if dev.shape != (len(JOINT_KEYS),):
        raise ValueError(f"deviation 길이는 {len(JOINT_KEYS)} 이어야 합니다.")
    tol = {**DEFAULT_TOLERANCE_DEG, **(tolerance or {})}
    ua = user_angles or {}
    ra = reference_angles or {}
    out = []
    for i, key in enumerate(JOINT_KEYS):
        score = score_from_deviation(dev[i], tol[key])
        cur = ua.get(key)
        tgt = ra.get(key)
        if cur is not None and tgt is not None:
            signed = float(cur) - float(tgt)
            direction = _direction_for(key, signed)
            joint_target_source = target_source
        else:
            cur = tgt = signed = direction = None
            # mode3 first 의 extension_requirement caller: 해당 관절이 reference_angles
            # 에 없다 = expects_extension(joint) == False → 기준 없음.
            joint_target_source = (
                "unavailable"
                if target_source == "extension_requirement"
                else target_source
            )
        out.append(
            JointAssessment(
                key=key,
                label_ko=JOINT_LABEL_KO[key],
                score=score,
                deviation_deg=float(dev[i]),
                part=JOINT_TO_PART[key],
                current_angle=cur,
                target_angle=tgt,
                signed_delta_deg=signed,
                direction=direction,
                target_source=joint_target_source,
            )
        )
    return out


def part_scores(assessments: list[JointAssessment]) -> dict[str, int]:
    """상체/코어/하체 평균 점수 (contract partScores 키)."""
    out: dict[str, int] = {}
    for part in PARTS:
        vals = [a.score for a in assessments if a.part == part]
        out[part] = int(round(sum(vals) / len(vals))) if vals else 0
    return out


def overall_score(
    assessments: list[JointAssessment], weight: dict | None = None
) -> int:
    """가중 평균 종합 점수 0~100 (KISMAM)."""
    w = {**DEFAULT_WEIGHT, **(weight or {})}
    num = sum(a.score * w[a.key] for a in assessments)
    den = sum(w[a.key] for a in assessments)
    return int(round(num / den)) if den else 0


def top_issues(
    assessments: list[JointAssessment], n: int = 3
) -> list[JointAssessment]:
    """점수 낮은(편차 큰) 순 상위 n. 동점이면 편차 큰 순."""
    return sorted(
        assessments, key=lambda a: (a.score, -a.deviation_deg)
    )[:n]
