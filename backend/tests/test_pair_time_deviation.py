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


# ── 3. 배선 source 단언 — app.py 는 env 의존이라 import 금지, 텍스트로 읽는다 ─────
# (선례 test_anchor_part_check.py `_gated_body()` / test_gated_frame_skips_collapse.py)

_ATTACH = "_attach_pair_time_deviation("
_UPLOAD = "_fault_zoom_upload_items("


def _app_src() -> str:
    return _APP.read_text(encoding="utf-8")


def _app_code() -> str:
    """주석 줄 제거본 — 주석에 든 단어가 카운트 단언을 무효화하지 않게."""
    return "\n".join(
        ln for ln in _app_src().splitlines() if not ln.lstrip().startswith("#")
    )


def _func_body(name: str) -> str:
    """`def <name>(` 부터 다음 컬럼0 `def ` 직전까지."""
    src = _app_src()
    start = src.index(f"def {name}(")
    end = src.index("\ndef ", start + 1)
    return src[start:end]


def test_mapper_copies_pair_deviation_to_item() -> None:
    """화이트리스트 매퍼가 값을 doc item 까지 흘린다 — 여기 없으면 영영 못 본다."""
    body = _func_body("_fault_zoom_upload_items")
    assert 'item["pairDeviationSec"] = float(_dev)' in body
    assert 'isinstance(_dev, (int, float)) and not isinstance(_dev, bool)' in body
    # tier 동반 필드도 같은 매퍼를 통과해야 한다 (값만 실리면 새 거짓 라벨).
    assert 'item["pairDeviationTier"] = _dev_tier' in body


def test_render_path_attaches_before_upload_mapper() -> None:
    """stage-1 + advisory 경로: 부착 호출이 업로드 매퍼 호출보다 앞선다."""
    body = _func_body("_render_fault_zoom")
    assert _ATTACH in body, "_render_fault_zoom 에 짝 이탈 부착 호출 없음"
    assert body.index(_ATTACH) < body.index(_UPLOAD), (
        "부착이 업로드 매퍼보다 뒤면 값이 doc 에 실리지 않는다"
    )


def test_render_path_covers_both_confirmed_and_advisory() -> None:
    """advisory 카드도 doc 에 남는다 — 한쪽만 실으면 구멍을 설명할 수 없다."""
    body = _func_body("_render_fault_zoom")
    call = body[body.index(_ATTACH):body.index(_UPLOAD)]
    assert "comps + adv_comps" in call


def test_gated_path_attaches_before_upload_mapper() -> None:
    """게이트-상속 경로: 부착 호출이 업로드 매퍼 호출보다 앞선다."""
    body = _func_body("_run_gated_card_inherit")
    assert _ATTACH in body, "_run_gated_card_inherit 에 짝 이탈 부착 호출 없음"
    assert body.index(_ATTACH) < body.index(_UPLOAD), (
        "부착이 업로드 매퍼보다 뒤면 값이 doc 에 실리지 않는다"
    )


def _executable_body(name: str) -> str:
    """함수 본문에서 docstring 과 주석 줄을 뺀 실행 코드만 — 설명문의 숫자가
    '리터럴 금지' 단언을 무효화하지 않게 한다."""
    body = _func_body(name)
    # docstring 은 첫 `"""` 부터 그 다음 `"""` 까지.
    first = body.index('"""')
    second = body.index('"""', first + 3)
    code = body[second + 3:]
    return "\n".join(
        ln for ln in code.splitlines() if not ln.lstrip().startswith("#")
    )


def test_anchor_fps_is_single_source_not_literal() -> None:
    """anchors 분모는 `_pipeline_frame_fps()` 단일 출처 — 리터럴 9.0 금지 (I1)."""
    code = _executable_body("_attach_pair_time_deviation")
    assert "anchor_fps = float(_pipeline_frame_fps())" in code
    assert "9.0" not in code, "anchor_fps 를 리터럴로 박으면 단일 출처가 깨진다"


def test_attach_is_graceful_and_never_kills_a_card() -> None:
    """어떤 실패도 카드를 죽이지 않는다 — try/except + log.exception (사후 스테이지 규율)."""
    body = _func_body("_attach_pair_time_deviation")
    assert "try:" in body and "except Exception:" in body
    assert "log.exception(" in body
    # 카드를 지우거나 거르는 연산이 없다 (관측 전용).
    for banned in ("del ", ".pop(", ".remove(", "return []"):
        assert banned not in body, f"부착 헬퍼에 카드 제거 연산 '{banned}' 존재"


# ── 게이트 무접촉 가드 ────────────────────────────────────────────────────


def test_no_code_gates_cards_on_pair_deviation() -> None:
    """pairDeviationSec 을 기준으로 카드를 버리거나 게이트하는 코드가 없다.

    이 필드는 관측 전용이다 — 통과선은 belle 판정 대기라 임계 비교가 있으면 안 된다.
    """
    code = _app_code()
    for banned in (
        "pairDeviationSec >",
        "pairDeviationSec <",
        "pairDeviationSec >=",
        "pairDeviationSec <=",
        "abs(pairDeviation",
        "PAIR_DEVIATION_MAX",
    ):
        assert banned not in code, f"관측 전용 필드에 임계 비교 '{banned}' 등장"


def test_existing_pair_gate_surface_unchanged() -> None:
    """종전 짝 게이트 축(PAIR_POSE_MAX / pairState)의 코드 표면이 그대로다.

    이번 단위는 **축을 교체하지 않는다** — 자세 지표 제거·임계 변경은 belle 판정 대기.
    숫자가 움직이면 누군가 게이트를 건드린 것이다.
    """
    code = _app_code()
    assert code.count("PAIR_POSE_MAX") == 2
    assert code.count("pair_state") == 1
    assert code.count("pairState") == 3
    assert 'c["pairState"] = decision.pair_state' in code


# ── 4. 3-way lockstep 텍스트 대조 ─────────────────────────────────────────
# (선례 test_motion_alignment_contract.py::test_models_keys_present_in_ts_source)


def test_ts_contract_declares_pair_deviation() -> None:
    """analysis.ts FaultZoomComparison 에 두 optional 필드가 등재돼 있다."""
    src = _TS_ANALYSIS.read_text(encoding="utf-8")
    assert "pairDeviationSec?: number;" in src
    assert "pairDeviationTier?: 'warped' | 'trim_only';" in src


def test_ts_contract_warns_against_app_side_estimation() -> None:
    """앱이 두 초를 빼서 추정하지 말라는 경고가 살아 있다 (§11.8 F-3 재발 방지)."""
    src = _TS_ANALYSIS.read_text(encoding="utf-8")
    block = src[src.index("pairDeviationSec?: number;") - 2200:
                src.index("pairDeviationSec?: number;")]
    assert "추정하지 말 것" in block
    assert "11.8" in block


def test_contract_md_has_section_11_12() -> None:
    """contract.md 에 §11.12 절이 존재하고 두 필드를 담는다."""
    src = _CONTRACT.read_text(encoding="utf-8")
    assert "### §11.12 FaultZoomComparison.pairDeviationSec" in src
    assert "pairDeviationTier" in src


def test_contract_md_marks_section_provisional_and_ungated() -> None:
    """§11.12 는 잠정이고 게이트가 아니라는 것을 절 안에서 못 박는다."""
    src = _CONTRACT.read_text(encoding="utf-8")
    sec = src[src.index("### §11.12"):src.index("## §12.")]
    assert "잠정(provisional)" in sec
    assert "게이트가 아니다" in sec
    assert "belle 눈으로 재검증되지 않았다" in sec


def test_contract_md_records_reproduction_failure_not_a_baseline() -> None:
    """인계서 §6 4행 표는 '재현 실패 — 기준값 아님' 딱지와 함께만 실린다.

    크기뿐 아니라 **순서도** 일치하지 않는다는 사실이 절 안에 있어야 한다 —
    "순서는 보존된다"는 서술은 실측으로 반증됐다([[handoff-observation-not-diagnosis]]).
    """
    src = _CONTRACT.read_text(encoding="utf-8")
    sec = src[src.index("### §11.12"):src.index("## §12.")]
    assert "재현 실패 — 기준값 아님" in sec
    assert "크기뿐 아니라 순서도 일치하지 않는다" in sec
    assert "순서는 보존된다" not in sec


def test_contract_md_does_not_create_a_third_section_11_11() -> None:
    """기존 §11.11 중복 2건은 그대로 두고, 세 번째 충돌을 만들지 않는다."""
    src = _CONTRACT.read_text(encoding="utf-8")
    assert src.count("### §11.11") == 2
    assert src.count("### §11.12") == 1


def test_models_comment_block_mentions_pair_deviation() -> None:
    """models.py 의 FAULT_ZOOM_STATUS 주석 블록이 신규 item 필드를 기록한다."""
    src = _MODELS.read_text(encoding="utf-8")
    block = src[src.index("# ── fault_zoom 사후 분리 상태"):
                src.index("FAULT_ZOOM_STATUS_PENDING = ")]
    assert "pairDeviationSec" in block
    assert "pairDeviationTier" in block
    assert "§11.12" in block
