"""motion_alignment 사다리 재배치 + 첫 anchor sanity 단위 테스트 — Phase 32 (D-16).

수리(32-RESEARCH §수리 #1): 저신뢰(distance > DISTANCE_T2) DTW 결과를 disabled 로
버리지 않고 tier='trim_only' + reason='low_global_confidence' 로 방출해 sanity 검증된
anchors(동작 비교 "시작점 맞춤")를 보존한다. 계약 변경 0 (trim_only 는 이미
MOTION_ALIGNMENT_TIERS enum 에 존재). 진짜 degenerate 3종(invalid_fps/empty_path/
insufficient_anchors)과 첫 anchor 가 범위 밖/non-finite 인 이상치만 disabled 로 남는다.

채점 무접촉 — 순수 함수 계약만 검증. AWS/Pod 불필요.
인용: 32-CONTEXT D-16.
"""

from __future__ import annotations

import math

from sunity_shared.analysis import motion_alignment
from sunity_shared.analysis.motiondtw import MotionMatch


def _match(path, distance, start=0, end=None):
    """합성 MotionMatch 빌더 (test_motion_alignment.py 선례 복제).

    end 미지정 시 path 의 최대 user_local + 1 로 구간 끝 추정."""
    if end is None:
        end = start + (max((i for i, _ in path), default=-1) + 1) if path else start
    # 33-M3-SPEC.md §1.1 — 합성 매치는 전체-기준 정렬(ref_start=0, ref_end=max ref+1).
    _ref_end = (max((r for _, r in path), default=-1) + 1) if path else 0
    return MotionMatch(
        start=start, end=end, ref_start=0, ref_end=_ref_end,
        distance=distance, path=list(path),
    )


def _pairs(result):
    """flat anchors → [(u0,r0),(u1,r1),...] 재조립."""
    a = result["anchors"]
    return [(a[k], a[k + 1]) for k in range(0, len(a), 2)]


# ── Test 1: 저신뢰(distance > T2) → trim_only + anchors 보존 (D-16 본체) ─────────


def test_low_confidence_emits_trim_only_with_anchors():
    """distance > DISTANCE_T2 (pairs >= 2, 첫 anchor sane) → tier 'trim_only',
    reason 'low_global_confidence', anchors 비어 있지 않음.

    구 동작은 disabled(빈 anchors) — 시작점 맞춤을 통째로 버렸다. D-16 수리로
    저신뢰도 anchors 를 보존한다."""
    path = [(i, i) for i in range(18)]  # 기울기 1.0, 첫 anchor (0,0) sane
    r = motion_alignment.build_motion_alignment(
        _match(path, distance=motion_alignment.DISTANCE_T2 + 5.0),
        user_fps=9.0,
        ref_fps=9.0,
    )
    assert r is not None
    assert r["tier"] == "trim_only"
    assert r["reason"] == "low_global_confidence"
    assert len(r["anchors"]) >= 4  # 최소 2쌍 보존 (validator 역불변식 충족)
    assert r["anchorCount"] == len(r["anchors"]) // 2


# ── Test 2: 진짜 degenerate 3종은 disabled + 빈 anchors 유지 ───────────────────


def test_degenerate_three_kinds_stay_disabled():
    """empty_path / invalid_fps / insufficient_anchors → tier 'disabled',
    anchors == [] (D-16 이후에도 이 3종만 disabled)."""
    # empty_path
    r_empty = motion_alignment.build_motion_alignment(
        _match([], distance=3.0), user_fps=9.0, ref_fps=18.0
    )
    assert r_empty["tier"] == "disabled"
    assert r_empty["anchors"] == []
    assert r_empty["reason"] == "empty_path"

    # invalid_fps
    path = [(i, i) for i in range(10)]
    r_fps = motion_alignment.build_motion_alignment(
        _match(path, distance=2.0), user_fps=0.0, ref_fps=18.0
    )
    assert r_fps["tier"] == "disabled"
    assert r_fps["anchors"] == []
    assert r_fps["reason"] == "invalid_fps"

    # insufficient_anchors (단일-시각 path → 앵커 < 2쌍)
    r_insuff = motion_alignment.build_motion_alignment(
        _match([(0, 3)], distance=2.0), user_fps=9.0, ref_fps=18.0
    )
    assert r_insuff["tier"] == "disabled"
    assert r_insuff["anchors"] == []
    assert r_insuff["reason"] == "insufficient_anchors"


# ── Test 3: 기존 사다리(warped / trim_only) 무회귀 ────────────────────────────


def test_ladder_warped_and_existing_trim_only_unchanged():
    """distance <= T1 ∧ slopes_ok → 'warped'; T1 < distance <= T2 → 'trim_only'.

    D-16 은 else(distance > T2) 분기만 바꾼다 — 기존 사다리 두 단계는 불변."""
    path = [(i, i) for i in range(18)]  # 기울기 1.0 (클램프 내)

    r_warp = motion_alignment.build_motion_alignment(
        _match(path, distance=motion_alignment.DISTANCE_T1 - 3.0),
        user_fps=9.0,
        ref_fps=9.0,
    )
    assert r_warp["tier"] == "warped"

    mid = (motion_alignment.DISTANCE_T1 + motion_alignment.DISTANCE_T2) / 2
    r_trim = motion_alignment.build_motion_alignment(
        _match(path, distance=mid), user_fps=9.0, ref_fps=9.0
    )
    assert r_trim["tier"] == "trim_only"
    assert r_trim["reason"] == "low_global_confidence"


# ── Test 4: trim_only 방출(신규 저신뢰 포함)이 validator 를 통과 ──────────────


def test_trim_only_emissions_pass_firestore_validator():
    """저신뢰 신규 trim_only + 기존 trim_only 방출 dict 가
    firestore_admin._validate_motion_alignment 를 예외 없이 통과 (역불변식 충족)."""
    from sunity_shared import firestore_admin

    path = [(i, i) for i in range(18)]

    r_low = motion_alignment.build_motion_alignment(
        _match(path, distance=motion_alignment.DISTANCE_T2 + 5.0),
        user_fps=9.0,
        ref_fps=9.0,
    )
    assert r_low["tier"] == "trim_only"
    firestore_admin._validate_motion_alignment(r_low)  # raise 0

    mid = (motion_alignment.DISTANCE_T1 + motion_alignment.DISTANCE_T2) / 2
    r_mid = motion_alignment.build_motion_alignment(
        _match(path, distance=mid), user_fps=9.0, ref_fps=9.0
    )
    assert r_mid["tier"] == "trim_only"
    firestore_admin._validate_motion_alignment(r_mid)


# ── Test 5: 첫 anchor sanity — 범위 밖 첫 anchor 는 degenerate 로 낙하 ─────────


def test_low_confidence_out_of_range_first_anchor_falls_to_degenerate():
    """저신뢰 경로에서 첫 anchor u0 < 0 (start 음수) → trim_only 가 아니라 기존
    degenerate 경로(disabled + insufficient_anchors)로 낙하.

    리뷰 MEDIUM: 이상치 offset(garbage)이 trim 기준으로 쓰이는 것을 차단한다."""
    path = [(i, i) for i in range(18)]
    # start=-2 → 첫 grid abs_frame=-2 → u0 = -2/9 < 0 (범위 밖).
    r = motion_alignment.build_motion_alignment(
        _match(path, distance=30.0, start=-2, end=16),
        user_fps=9.0,
        ref_fps=9.0,
    )
    assert r is not None
    assert r["tier"] == "disabled", "범위 밖 첫 anchor 는 trim_only 로 방출 금지"
    assert r["anchors"] == []
    assert r["reason"] == "insufficient_anchors"  # 신규 reason enum 0 (기존 값 재사용)


# ── Test 6: 정상 저신뢰 방출의 첫 anchor 파생 오프셋이 duration 이하 ──────────


def test_low_confidence_first_anchor_offset_within_max_duration():
    """정상 저신뢰 trim_only 방출의 첫 anchor 쌍 (u0, r0) 파생 오프셋 |r0 - u0| 가
    max(user_duration, ref_duration) 이하 (sanity 가드가 보장하는 경계 속성).

    끝프레임까지 shift 된 path 로 오프셋을 비자명하게 만든 뒤 확인한다."""
    # ref 를 +3 프레임 shift → 첫 anchor 오프셋 비자명(0 아님)하되 범위 내.
    path = [(i, i + 3) for i in range(15)]
    user_fps = ref_fps = 9.0
    r = motion_alignment.build_motion_alignment(
        _match(path, distance=30.0), user_fps=user_fps, ref_fps=ref_fps
    )
    assert r["tier"] == "trim_only"
    pairs = _pairs(r)
    u0, r0 = pairs[0]
    assert r0 - u0 != 0.0, "shift 로 오프셋이 비자명해야 테스트 의미 있음"
    # user 끝프레임 = 14 → user_dur = 14/9 ; ref 최대 인덱스 = 17 → ref_dur = 17/9.
    user_dur = 14 / user_fps
    ref_dur = 17 / ref_fps
    assert abs(r0 - u0) <= max(user_dur, ref_dur) + 1e-9
    # 첫 anchor 자체도 각 타임라인 [0, duration] 안 (sanity 가드 대칭 확인).
    assert 0.0 <= u0 <= user_dur + 1e-9 and math.isfinite(u0)
    assert 0.0 <= r0 <= ref_dur + 1e-9 and math.isfinite(r0)
