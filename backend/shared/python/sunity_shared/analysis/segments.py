"""구간별 점수 — 공유 베이스 / 확장 구간 분리 평가 (reference-motions.md §7).

일부 기술은 다른 기술의 베이스 구간을 공유한다
(ref-invert → ref-foxtop → ref-foxtop-split).
DTW 정렬 경로를 reference 의 baseUntilS 시점 기준으로 베이스/확장으로 나눠
각 구간 KISMAM 점수를 따로 낸다 → 학생이 어느 단계에서 막혔는지 보임.

contract.md §4 SegmentScores = { base, extension, baseMotionId, baseMotionName }.
"""

from __future__ import annotations

import numpy as np

from . import kismam
from .motiondtw import per_joint_deviation


def ref_boundary_frame(clip_range: dict, base_until_s: float, ref_len: int) -> int:
    """reference angles 시퀀스에서 베이스/확장 경계 프레임 인덱스.

    reference angles 는 execStartS~landEndS 구간 프레임(reference-motions.md §4).
    baseUntilS(절대 시점)를 그 구간 내 비율로 환산 — fps 불필요.
    """
    exec_start = float(clip_range.get("execStartS", 0.0))
    land_end = float(clip_range.get("landEndS", 0.0))
    span = land_end - exec_start
    if span <= 0 or ref_len <= 0:
        return ref_len
    frac = (float(base_until_s) - exec_start) / span
    return max(0, min(ref_len, round(frac * ref_len)))


def split_path_by_ref(path, ref_boundary: int):
    """DTW 정렬 경로를 ref 인덱스 기준 분할. ref_idx < boundary → 베이스."""
    base = [(u, r) for (u, r) in path if r < ref_boundary]
    ext = [(u, r) for (u, r) in path if r >= ref_boundary]
    return base, ext


def segment_scores(
    ref: dict, base_motion_name: str, path, user_seg, a_ref,
    ref_start: int = 0, nr_full: int | None = None,
) -> dict | None:
    """베이스 공유 기술이면 베이스/확장 구간 KISMAM 점수 dict, 아니면 None.

    ref              : reference 기술 문서 (sharedBaseMotionId/baseUntilS/clipRange)
    base_motion_name : 베이스 기술 이름 (Firestore 조회는 호출자 책임 — 순수성 유지)
    path             : motion_dtw 정렬 경로 [(user_idx, ref_local_idx)...] (window-local)
    user_seg         : 사용자 동작 구간 각도 (T_seg, J)
    a_ref            : **windowed** reference 각도 (T_win, J) = A_ref[ref_start:ref_end]
    ref_start        : window 시작(전체 ref 프레임 인덱스). 통째면 0.
    nr_full          : 전체 reference 길이(경계 산출용). None 이면 len(a_ref)(=통째 가정).

    33-M3-SPEC.md §5.1 — path 가 window-local 이므로 base/확장 경계도 window-local 로
    시프트한다: boundary_win = boundary_full - ref_start. ref_start=0·nr_full=len(a_ref)
    이면 현행(pre-M3)과 동일 동작(하위호환).
    """
    base_id = ref.get("sharedBaseMotionId")
    base_until_s = ref.get("baseUntilS")
    clip = ref.get("clipRange")
    if not base_id or base_until_s is None or not clip:
        return None

    a_ref = np.asarray(a_ref, dtype=float)
    nr_full = len(a_ref) if nr_full is None else int(nr_full)
    boundary_full = ref_boundary_frame(clip, base_until_s, nr_full)
    boundary = boundary_full - int(ref_start)  # window-local 경계
    if boundary <= 0 or boundary >= len(a_ref):
        return None  # 한쪽 구간이 비면 분할이 의미 없음 (§2.2 통과 시 항상 만족)

    base_path, ext_path = split_path_by_ref(path, boundary)
    if not base_path or not ext_path:
        return None

    base_dev = per_joint_deviation(base_path, user_seg, a_ref)
    ext_dev = per_joint_deviation(ext_path, user_seg, a_ref)
    return {
        "base": kismam.overall_score(kismam.assess(base_dev)),
        "extension": kismam.overall_score(kismam.assess(ext_dev)),
        "baseMotionId": base_id,
        "baseMotionName": base_motion_name,
    }
