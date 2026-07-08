"""build_motion_alignment 계약 테스트 — Phase 28 Wave 0 (RED, 최종 계약). AWS 불필요.

28-02 가 구현할 `sunity_shared.analysis.motion_alignment.build_motion_alignment`
(MotionMatch → 초 단위 앵커 + tier dict) 의 계약을 **구현 전에** 고정한다.
모듈 부재 동안 이 파일은 collection error(ModuleNotFoundError) 로 실패한다 = 의도된 RED.

**기대값은 처음부터 최종 계약**(degenerate = tier 'disabled' 방출, legacy 필드 부재와
구별)으로 작성한다 — 28-02 의 GREEN 이 이 테스트를 다시 고치는 churn 금지 (리뷰 MEDIUM-2,
28-02 W3 스펙과 동일). 초 단위 방출은 fps 도메인 함정(28-RESEARCH Pitfall 1: user 9fps
vs ref 18fps) 회귀 가드. 채점 무접촉 — 순수 함수 계약만 검증.

인용: 28-CONTEXT D-01(초 단위 앵커+구간 가변속도) / D-02(tier 사다리) / D-03(임계 재사용).
"""

from __future__ import annotations

from sunity_shared.analysis import motion_alignment  # RED: 28-02 구현 전 collection error
from sunity_shared.analysis.motiondtw import MotionMatch


def _match(path, distance, start=0, end=None):
    """합성 MotionMatch 빌더 (motiondtw.MotionMatch 직접 생성).

    end 미지정 시 path 의 최대 user_local + 1 로 구간 끝 추정 (path 없으면 start)."""
    if end is None:
        end = start + (max((i for i, _ in path), default=-1) + 1) if path else start
    return MotionMatch(start=start, end=end, distance=distance, path=list(path))


def _pairs(result):
    """flat anchors → [(u0,r0),(u1,r1),...] 로 재조립 (계약 소비 형상)."""
    a = result["anchors"]
    return [(a[k], a[k + 1]) for k in range(0, len(a), 2)]


# ── 1. None vs degenerate — 최종 계약 (리뷰 MEDIUM-2, W3) ──────────────────────


def test_none_match_returns_none():
    """match=None → None (유일한 None 케이스 — 정렬 컨텍스트 부재 = 필드 미방출 legacy).

    28-CONTEXT D-05: legacy doc 은 필드 자체가 부재. degenerate(아래)는 방출된다."""
    assert (
        motion_alignment.build_motion_alignment(None, user_fps=9.0, ref_fps=18.0)
        is None
    )


def test_empty_path_emits_disabled():
    """match 존재 + path=[] → tier 'disabled', reason 'empty_path' 방출 (W3 최종 계약).

    degenerate=disabled 방출이 legacy 필드 부재와 구분되는 계약 — '재분석하면 적용'
    과약속 배너 루프 차단 (리뷰 MEDIUM-2)."""
    r = motion_alignment.build_motion_alignment(
        _match([], distance=3.0), user_fps=9.0, ref_fps=18.0
    )
    assert r is not None
    assert r["tier"] == "disabled"
    assert r["reason"] == "empty_path"
    assert r["anchors"] == []
    assert r["anchorCount"] == 0
    # version/source/distance 키 존재 (배지 렌더 계약).
    assert "version" in r and "source" in r and "distance" in r


def test_invalid_fps_emits_disabled():
    """user_fps<=0 또는 ref_fps<=0 → tier 'disabled', reason 'invalid_fps' (W3 최종 계약)."""
    path = [(i, i) for i in range(10)]
    for uf, rf in ((0.0, 18.0), (9.0, 0.0), (-1.0, 18.0)):
        r = motion_alignment.build_motion_alignment(
            _match(path, distance=2.0), user_fps=uf, ref_fps=rf
        )
        assert r is not None
        assert r["tier"] == "disabled"
        assert r["reason"] == "invalid_fps"
        assert r["anchors"] == []


def test_insufficient_anchors_emits_disabled():
    """유효 path 인데 앵커 < 2쌍 → tier 'disabled', reason 'insufficient_anchors' (W3).

    단일-시각 path(1 entry)는 앵커 1개 → warp 역전 방지 위해 방출 안 함(disabled)."""
    r = motion_alignment.build_motion_alignment(
        _match([(0, 3)], distance=2.0), user_fps=9.0, ref_fps=18.0
    )
    assert r is not None
    assert r["tier"] == "disabled"
    assert r["reason"] == "insufficient_anchors"
    assert r["anchors"] == []


# ── 2. 초 단위 + fps 변환 (Pitfall 1 회귀 가드) ───────────────────────────────


def test_seconds_domain_and_fps_conversion():
    """user 9fps / ref 18fps identity-in-time path → 앵커가 인덱스 아닌 초, uSec≈rSec.

    28-RESEARCH Pitfall 1: path ref_idx 는 18fps 공간 — 초로 변환하면 uSec=i/9,
    rSec=2i/18=i/9 로 동일. 인덱스로 방출하면 정은지 시각이 2배로 튄다."""
    path = [(i, 2 * i) for i in range(18)]  # user_local i, ref_idx 2i (18fps)
    r = motion_alignment.build_motion_alignment(
        _match(path, distance=1.0), user_fps=9.0, ref_fps=18.0
    )
    assert r is not None
    seg_seconds = 17 / 9.0
    for u, ref in _pairs(r):
        # identity-in-time: 각 앵커 uSec ≈ rSec (허용오차 1 프레임 = 1/9s).
        assert abs(u - ref) <= 1.0 / 9.0 + 1e-9
        # 초 단위 증거: 인덱스면 ref 가 최대 34 까지 튄다 — 초면 구간초+1 이내.
        assert u <= seg_seconds + 1.0
        assert ref <= seg_seconds + 1.0


# ── 3. 단조성 ────────────────────────────────────────────────────────────────


def test_anchors_strictly_monotonic():
    """앵커 u 좌표 strictly increasing, r 좌표 non-decreasing (비단조 쌍 제거)."""
    path = [(i, i) for i in range(18)]
    r = motion_alignment.build_motion_alignment(
        _match(path, distance=1.0), user_fps=9.0, ref_fps=9.0
    )
    pairs = _pairs(r)
    assert len(pairs) >= 2
    us = [u for u, _ in pairs]
    rs = [ref for _, ref in pairs]
    assert all(us[k] < us[k + 1] for k in range(len(us) - 1))
    assert all(rs[k] <= rs[k + 1] for k in range(len(rs) - 1))


# ── 4. 결정론 ────────────────────────────────────────────────────────────────


def test_deterministic():
    """동일 입력 2회 호출 → dict 동일 (==)."""
    path = [(i, i) for i in range(18)]
    m = _match(path, distance=1.0)
    a = motion_alignment.build_motion_alignment(m, user_fps=9.0, ref_fps=9.0)
    b = motion_alignment.build_motion_alignment(
        _match(path, distance=1.0), user_fps=9.0, ref_fps=9.0
    )
    assert a == b


# ── 5. identity 기울기 1.0 ────────────────────────────────────────────────────


def test_identity_slope_is_one_and_warped():
    """user_fps==ref_fps, identity path → 전 구간 기울기 1.0 ± 1e-6, tier 'warped'.

    28-CONTEXT D-02 tier 1: distance ≤ 8.0 AND 기울기 클램프 내 → 풀 워핑."""
    path = [(i, i) for i in range(18)]
    r = motion_alignment.build_motion_alignment(
        _match(path, distance=1.0), user_fps=9.0, ref_fps=9.0
    )
    assert r["tier"] == "warped"
    pairs = _pairs(r)
    for k in range(len(pairs) - 1):
        du = pairs[k + 1][0] - pairs[k][0]
        dr = pairs[k + 1][1] - pairs[k][1]
        assert du > 0
        assert abs(dr / du - 1.0) <= 1e-6


# ── 6. tier 경계 (D-02/D-03) ─────────────────────────────────────────────────


def test_tier_distance_boundaries():
    """distance 임계 사다리 (vision_veto _ALIGN_GLOBAL_T1=8.0/T2=25.0 재사용).

    8.0 → warped(경계 포함) / 8.1 → trim_only(reason 존재) / 25.0 → trim_only /
    25.1 → disabled. clean slope(=1.0) 로 rate clamp 는 통과 → tier 는 distance 만 결정."""
    path = [(i, i) for i in range(18)]  # 기울기 1.0 (클램프 내)

    r80 = motion_alignment.build_motion_alignment(
        _match(path, distance=8.0), user_fps=9.0, ref_fps=9.0
    )
    assert r80["tier"] == "warped"

    r81 = motion_alignment.build_motion_alignment(
        _match(path, distance=8.1), user_fps=9.0, ref_fps=9.0
    )
    assert r81["tier"] == "trim_only"
    assert r81.get("reason")  # 강등 사유 존재

    r250 = motion_alignment.build_motion_alignment(
        _match(path, distance=25.0), user_fps=9.0, ref_fps=9.0
    )
    assert r250["tier"] == "trim_only"

    r251 = motion_alignment.build_motion_alignment(
        _match(path, distance=25.1), user_fps=9.0, ref_fps=9.0
    )
    assert r251["tier"] == "disabled"


def test_rate_clamp_violation_downgrades_to_trim_only():
    """distance=1.0(낮음)인데 ref 가 user 3배 속도 → 기울기 클램프 초과 → trim_only.

    28-CONTEXT D-02 tier 2: 기울기 [0.5,2.0] 밖 = 가변속도 끔(안전 모드).
    reason == 'rate_clamp_exceeded'."""
    path = [(i, 3 * i) for i in range(18)]  # 기울기 3.0 > RATE_MAX(2.0)
    r = motion_alignment.build_motion_alignment(
        _match(path, distance=1.0), user_fps=9.0, ref_fps=9.0
    )
    assert r["tier"] == "trim_only"
    assert r["reason"] == "rate_clamp_exceeded"


# ── 7. flat 계약 ─────────────────────────────────────────────────────────────


def test_flat_contract_keys_and_shape():
    """반환 dict 키 == {version, source, tier, anchors, anchorCount, distance}(+opt reason),
    anchors flat list[number] (중첩 0), anchorCount == len(anchors)//2."""
    path = [(i, i) for i in range(18)]
    r = motion_alignment.build_motion_alignment(
        _match(path, distance=1.0), user_fps=9.0, ref_fps=9.0
    )
    required = {"version", "source", "tier", "anchors", "anchorCount", "distance"}
    assert required <= set(r.keys())
    assert set(r.keys()) <= required | {"reason"}
    assert isinstance(r["anchors"], list)
    for v in r["anchors"]:
        assert isinstance(v, (int, float))  # flat scalar — 중첩 배열 금지
        assert not isinstance(v, bool)
    assert len(r["anchors"]) % 2 == 0
    assert r["anchorCount"] == len(r["anchors"]) // 2


# ── 8. 앵커 길이 상한 ─────────────────────────────────────────────────────────


def test_anchor_count_upper_bound():
    """300초 합성 path → len(anchors) <= 512 (step 자동 확대), 앵커는 여전히 단조.

    28-RESEARCH Pitfall 2: analyses 대형 배열 = Firestore 40k index-entry 위험 →
    앵커 다운샘플 상한. 긴 영상에서 step 확대 허용."""
    path = [(i, i) for i in range(2700)]  # 2700 frames / 9fps = 300s
    r = motion_alignment.build_motion_alignment(
        _match(path, distance=1.0), user_fps=9.0, ref_fps=9.0
    )
    assert len(r["anchors"]) <= 512
    us = [u for u, _ in _pairs(r)]
    assert all(us[k] < us[k + 1] for k in range(len(us) - 1))
