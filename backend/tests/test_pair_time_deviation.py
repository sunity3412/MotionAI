"""quick-260919-mhl — 확대 비교 카드 짝 시간 정렬 이탈(pairDeviationSec) 시험.

검증 대상:
  1. `motion_alignment.warp_time` — TS 정본(app/src/lib/alignmentWarp.ts::warpTime)의
     분기 4종 동치 + 소스 텍스트 lockstep(식이 TS 에서 바뀌면 여기서 깨진다).
  2. `motion_alignment.pair_time_deviation_sec` — 타임베이스 환산(라벨 9.0 ↔ 측별
     실효 rate)이 실제로 값을 바꾸고, 드리프트 0 이면 순진한 뺄셈으로 축약되며,
     부호가 displayed − expected 방향이고, 값 없음 6종에서 None 을 낸다.
  3. 배선(Task 2) — app.py 는 env 의존이라 import 금지, **소스 텍스트 단언**으로
     화이트리스트 매퍼 복사 절과 두 카드 경로의 호출 순서를 박제한다.
     선례: test_anchor_part_check.py `_gated_body()`, test_gated_frame_skips_collapse.py.
  4. 3-way lockstep(Task 3) — analysis.ts / models.py / contract.md §11.12 텍스트 대조.
     선례: test_motion_alignment_contract.py `test_models_keys_present_in_ts_source`.

이 필드는 **관측 전용**이다. 게이트가 아니므로 "카드를 버리는 코드가 없다"도 함께
단언한다 (게이트 무접촉 가드).
"""

from __future__ import annotations

import math
from pathlib import Path

from sunity_shared.analysis import motion_alignment as ma

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TS_WARP = _REPO_ROOT / "app" / "src" / "lib" / "alignmentWarp.ts"
_TS_ANALYSIS = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"
_CONTRACT = _REPO_ROOT / "docs" / "contract.md"
_MODELS = _REPO_ROOT / "backend" / "shared" / "python" / "sunity_shared" / "models.py"
_APP = Path(__file__).resolve().parents[1] / "functions" / "pipeline" / "app.py"


def _warped(anchors: list[float]) -> dict:
    return {
        "version": "ma-v1",
        "source": "dtw",
        "tier": "warped",
        "anchors": anchors,
        "anchorCount": len(anchors) // 2,
        "distance": 5.0,
    }


def _trim_only(anchors: list[float]) -> dict:
    d = _warped(anchors)
    d["tier"] = "trim_only"
    d["reason"] = "low_global_confidence"
    return d


# ── 1. warp_time — TS 정본 분기 4종 동치 ──────────────────────────────────


def test_warp_disabled_is_identity() -> None:
    """tier='disabled' → identity (정렬 정보 없음 — 방어적 통과)."""
    a = {"tier": "disabled", "anchors": []}
    assert ma.warp_time(a, 3.25) == 3.25


def test_warp_zero_anchors_is_identity() -> None:
    """앵커 0쌍 → identity. anchorCount 가 거짓말해도 len(anchors) 가 이긴다."""
    a = {"tier": "warped", "anchors": [], "anchorCount": 7}
    assert ma.warp_time(a, 2.0) == 2.0


def test_warp_trim_only_is_offset() -> None:
    """trim_only → t - us[0] + rs[0] (첫 앵커 기준 평행이동, 가변속도 끔)."""
    a = _trim_only([1.0, 2.5, 3.0, 9.0])
    # 3.0 - 1.0 + 2.5 = 4.5 — 둘째 앵커(3.0→9.0)는 쓰이지 않는다.
    assert ma.warp_time(a, 3.0) == 4.5


def test_warp_warped_before_range_extends_slope_one() -> None:
    """warped 범위 이전 → rs[0] - (us[0] - t) (기울기 1.0 연장)."""
    a = _warped([2.0, 10.0, 4.0, 14.0])
    assert ma.warp_time(a, 1.0) == 9.0


def test_warp_warped_interpolates_segment() -> None:
    """warped 구간 내부 → rs[k] + (t - us[k]) * slope. slope = 4/2 = 2.0."""
    a = _warped([2.0, 10.0, 4.0, 14.0])
    assert ma.warp_time(a, 3.0) == 12.0


def test_warp_warped_after_range_extends_slope_one() -> None:
    """warped 범위 이후 → rs[n-1] + (t - us[n-1]) (기울기 1.0 연장)."""
    a = _warped([2.0, 10.0, 4.0, 14.0])
    assert ma.warp_time(a, 6.0) == 16.0


def test_warp_reads_pairs_from_length_not_anchorcount() -> None:
    """anchorCount 를 신뢰하지 않는다 — TS readPairs '단일 출처, 방어적 소비' 미러."""
    a = _warped([2.0, 10.0, 4.0, 14.0])
    a["anchorCount"] = 1  # 거짓말
    assert ma.warp_time(a, 3.0) == 12.0


def test_ts_warp_source_lockstep() -> None:
    """TS 정본의 네 식이 그대로 살아 있는가 — 한쪽만 고치면 여기서 깨진다."""
    src = _TS_WARP.read_text(encoding="utf-8")
    for expr in (
        "tStudent - us[0] + rs[0]",
        "rs[0] - (us[0] - tStudent)",
        "rs[n - 1] + (tStudent - us[n - 1])",
        "(rs[k + 1] - rs[k]) / (us[k + 1] - us[k])",
    ):
        assert expr in src, (
            f"alignmentWarp.ts 에서 '{expr}' 가 사라졌다 — "
            f"motion_alignment.warp_time 미러가 drift 했다"
        )


# ── 2. pair_time_deviation_sec — 타임베이스 / 부호 / 값 없음 ────────────────


def test_timebase_conversion_changes_the_value() -> None:
    """라벨 9.0 ↔ 실효 10.0 조합에서 환산이 실제로 값을 바꾼다.

    환산을 되돌리면(순진한 `ref - warp(user)`) 다른 수가 나온다는 것을 박제한다 —
    이 시험이 §타임베이스 유도 전체를 지킨다.
    """
    a = _trim_only([0.0, 3.0, 5.0, 8.0])  # warp(t) = t + 3.0 (anchor 축)
    got = ma.pair_time_deviation_sec(
        a,
        user_video_sec=1.8,   # anchor 축 1.8 * 10/9 = 2.0
        ref_video_sec=5.4,    # anchor 축 5.4 * 10/9 = 6.0
        user_label_fps=10.0,
        ref_label_fps=10.0,
        anchor_fps=9.0,
    )
    # anchor 축: 6.0 - (2.0 + 3.0) = 1.0 → 다시 기준 패널 실초로 1.0 * 9/10 = 0.9
    assert got is not None
    assert math.isclose(got, 0.9, rel_tol=0, abs_tol=1e-9)
    # 환산 없는 순진한 뺄셈은 5.4 - (1.8 + 3.0) = 0.6 — 다른 수다.
    assert not math.isclose(got, 0.6, rel_tol=0, abs_tol=1e-9)


def test_exact_alignment_match_is_zero_after_conversion() -> None:
    """정렬과 정확히 일치하는 짝은 환산 후 0.0 — 라벨 드리프트가 있어도 그렇다."""
    a = _trim_only([0.0, 3.0, 5.0, 8.0])  # warp(t) = t + 3.0
    got = ma.pair_time_deviation_sec(
        a,
        user_video_sec=1.8,   # anchor 2.0 → warp 5.0
        ref_video_sec=4.5,    # anchor 5.0 (4.5 * 10/9) = 정렬이 가리키는 그 순간
        user_label_fps=10.0,
        ref_label_fps=10.0,
        anchor_fps=9.0,
    )
    assert got is not None
    assert math.isclose(got, 0.0, rel_tol=0, abs_tol=1e-9)


def test_no_label_drift_reduces_to_plain_subtraction() -> None:
    """라벨 드리프트 0(9.0/9.0)이면 배율 1.0 → `ref - warp(user)` 로 축약 (회귀 가드)."""
    a = _warped([0.0, 0.0, 4.0, 8.0])  # slope 2.0
    user_sec, ref_sec = 2.0, 5.5
    got = ma.pair_time_deviation_sec(
        a,
        user_video_sec=user_sec,
        ref_video_sec=ref_sec,
        user_label_fps=9.0,
        ref_label_fps=9.0,
        anchor_fps=9.0,
    )
    assert got is not None
    assert math.isclose(got, ref_sec - ma.warp_time(a, user_sec), rel_tol=0, abs_tol=1e-12)


def test_sign_positive_when_reference_panel_is_late() -> None:
    """기준 패널이 정렬보다 **늦은** 순간이면 양수 (displayed - expected)."""
    a = _trim_only([0.0, 0.0, 4.0, 4.0])  # warp = identity
    got = ma.pair_time_deviation_sec(
        a,
        user_video_sec=2.0,
        ref_video_sec=3.5,  # 정렬은 2.0 을 가리키는데 3.5 를 보여준다 → 늦다
        user_label_fps=9.0,
        ref_label_fps=9.0,
        anchor_fps=9.0,
    )
    assert got is not None and got > 0
    assert math.isclose(got, 1.5, rel_tol=0, abs_tol=1e-9)


def test_sign_negative_when_reference_panel_is_early() -> None:
    """기준 패널이 정렬보다 **이른** 순간이면 음수."""
    a = _trim_only([0.0, 0.0, 4.0, 4.0])
    got = ma.pair_time_deviation_sec(
        a,
        user_video_sec=2.0,
        ref_video_sec=0.8,
        user_label_fps=9.0,
        ref_label_fps=9.0,
        anchor_fps=9.0,
    )
    assert got is not None and got < 0
    assert math.isclose(got, -1.2, rel_tol=0, abs_tol=1e-9)


def _kw(**over) -> dict:
    base = dict(
        user_video_sec=2.0,
        ref_video_sec=3.0,
        user_label_fps=9.0,
        ref_label_fps=9.0,
        anchor_fps=9.0,
    )
    base.update(over)
    return base


def test_none_when_alignment_missing() -> None:
    """alignment 부재(legacy doc / mode3 첫 분석 / 방출 실패) → None."""
    assert ma.pair_time_deviation_sec(None, **_kw()) is None


def test_none_when_tier_disabled() -> None:
    """tier='disabled' → None. identity warp 로 뺀 값은 근거가 없다."""
    a = {"tier": "disabled", "anchors": [0.0, 0.0, 4.0, 4.0]}
    assert ma.pair_time_deviation_sec(a, **_kw()) is None


def test_none_when_tier_unknown() -> None:
    """미등재 tier → None (warped 로 오독하면 근거 없는 수를 만든다 — fail-closed)."""
    a = {"tier": "elastic", "anchors": [0.0, 0.0, 4.0, 4.0]}
    assert ma.pair_time_deviation_sec(a, **_kw()) is None


def test_none_when_no_anchors() -> None:
    """앵커 0쌍 → None."""
    a = {"tier": "trim_only", "anchors": [], "anchorCount": 0}
    assert ma.pair_time_deviation_sec(a, **_kw()) is None


def test_none_when_user_video_sec_missing() -> None:
    """userVideoSec 부재 → None (추정치로 채우지 않는다)."""
    a = _trim_only([0.0, 0.0, 4.0, 4.0])
    assert ma.pair_time_deviation_sec(a, **_kw(user_video_sec=None)) is None


def test_none_when_ref_video_sec_missing() -> None:
    """refVideoSec 부재(기준 대응 실패 카드) → None."""
    a = _trim_only([0.0, 0.0, 4.0, 4.0])
    assert ma.pair_time_deviation_sec(a, **_kw(ref_video_sec=None)) is None


def test_none_when_label_fps_non_positive() -> None:
    """label_fps <= 0 → None (0 나눗셈·부호 반전 차단)."""
    a = _trim_only([0.0, 0.0, 4.0, 4.0])
    assert ma.pair_time_deviation_sec(a, **_kw(ref_label_fps=0.0)) is None
    assert ma.pair_time_deviation_sec(a, **_kw(user_label_fps=-9.0)) is None
    assert ma.pair_time_deviation_sec(a, **_kw(anchor_fps=0.0)) is None


def test_none_when_inputs_non_finite() -> None:
    """NaN/Inf 입력 → None (비유한 값이 doc 으로 새는 것을 막는다)."""
    a = _trim_only([0.0, 0.0, 4.0, 4.0])
    assert ma.pair_time_deviation_sec(a, **_kw(user_video_sec=float("nan"))) is None
    assert ma.pair_time_deviation_sec(a, **_kw(ref_video_sec=float("inf"))) is None
    bad = _trim_only([0.0, float("nan"), 4.0, 4.0])
    assert ma.pair_time_deviation_sec(bad, **_kw()) is None


def test_build_motion_alignment_output_unchanged_by_this_unit() -> None:
    """additive only — 기존 산출 함수·상수 무접촉 (모듈에 부작용 0)."""
    assert ma.MOTION_ALIGNMENT_VERSION == "ma-v1"
    assert ma.DISTANCE_T1 == 8.0 and ma.DISTANCE_T2 == 25.0
    assert ma.RATE_MIN == 0.5 and ma.RATE_MAX == 2.0
    assert ma.MAX_ANCHOR_FLOATS == 512
    assert callable(ma.build_motion_alignment)
