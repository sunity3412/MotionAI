"""앵커 부위 확인 — 카드를 내보내기 전에 앵커 좌표가 제목의 부위인지 기계 눈으로 본다 (quick-260906-j8g).

2026-09-06 실측 (09-03 라이브 6문서 36패널 — 관절 좌표에 짧은 변 18% 무마킹 크롭을 붙여
기계 눈에 "무슨 부위냐"를 3회 최빈으로 물음): **좌표 OK 15 / 좌표 틀림 14 / 못 읽음 7**.
신뢰도가 못 거른다 — conf 0.872 가 판독불가, 0.749 가 무릎 자리에 손, 0.743 이 팔꿈치 자리에
허벅지, 0.637 이 어깨 자리에 얼굴. 붕괴 검사도 못 거른다 — f4j 가 붕괴 패널 14→4 로 줄였는데
감점 카드 눈 불일치는 4→4 그대로(옮긴 프레임의 좌표도 틀리기 때문). 카드 크롭(짧은 변 42%)은
몸 절반이 들어와 틀린 좌표를 가린다(클라임 오른무릎: 카드 감사 ok 인데 좌표는 팔).
진단 확정본: .planning/quick/260906-f4j-gated-card-collapse-frame-skip/evidence/ROOT-CAUSE.md

belle 09-03 규칙 1 — "멈춤 구간마다 사진 1장, 검사는 표시만 정한다". 그래서 확인 실패는
창 안 다른 건전 프레임(최대 2)으로 옮기고, 그래도 실패면 **사진은 남기고 그 측 표시만
생략**한다. 어느 결과도 카드를 없애지 않는다.

층 분리: card_photo_audit = 판정(순수, numpy 0) / card_gates = 눈·크롭·프레임 후보·상태기계 /
pipeline = 처분(이동·suppress). 눈 호출은 전부 가로챈다(monkeypatch·대본 ask) — 네트워크 0.
fixture(_mk/MEMBERS)는 test_gated_frame_skips_collapse.py 사본 — 같은 붕괴/정상 프레임 형상.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np
import pytest

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import card_gates as cg  # noqa: E402
from sunity_shared.analysis import card_photo_audit as cpa  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

JOINTS = ["left_shoulder", "right_shoulder", "left_hip", "right_hip",
          "left_knee", "right_knee", "left_elbow", "right_elbow"]
MEMBERS = ("right_elbow", "right_shoulder")
EXP_KNEE = frozenset({"knee", "thigh", "foot"})


def _clean_frame(seed: float):
    """좌표가 흩어진 정상 프레임."""
    return [[0.30 + 0.07 * i, 0.20 + 0.09 * i + seed] for i in range(len(JOINTS))]


def _collapsed_frame():
    """폴 위 한 세로선 — x 동일 (08-10 실측 패턴)."""
    return [[0.532, 0.30 + 0.04 * i] for i in range(len(JOINTS))]


def _report(frames: list[list[list[float]]], confs: list[list[float]]) -> dict:
    return {
        "joints": JOINTS, "fps": 9.0, "frames": len(frames),
        "data": [c for f in frames for p in f for c in p],
        "confidence": [c for row in confs for c in row],
        "version": "test",
    }


def _mk(kind_by_frame, conf_by_frame):
    frames = [(_collapsed_frame() if k == "x" else _clean_frame(0.01 * i))
              for i, k in enumerate(kind_by_frame)]
    confs = [[c] * len(JOINTS) for c in conf_by_frame]
    return _report(frames, confs)


# ── card_photo_audit — 순수 판정 ─────────────────────────────────────────────


def test_modal_token_same_rule_as_audit_script() -> None:
    """파이프라인 앵커 확인과 감사 스크립트가 같은 최빈 규칙 — 어휘 안 토큰만 표, 동률·표 0 = unclear."""
    assert cpa.modal_token(["knee", "knee", "elbow"]) == "knee"
    assert cpa.modal_token(["knee", "elbow"]) == "unclear"          # 동률 = fail-closed
    assert cpa.modal_token(["unclear", "error"]) == "unclear"       # 못 읽음은 표가 아니다
    assert cpa.modal_token(["unclear", "unclear", "hip"]) == "hip"
    assert cpa.modal_token(["bent", "bent", "bent"]) == "unclear"   # 어휘 밖 = 표 아님
    assert cpa.modal_token([]) == "unclear"
    # mark_part 어휘에서만 no_mark 가 표다 (표시가 없다는 관측)
    assert cpa.modal_token(["no_mark", "no_mark", "neck"]) == "neck"
    assert cpa.modal_token(["no_mark", "no_mark", "neck"], cpa.MARK_VOCAB) == "no_mark"


def test_anchor_verdict_four_outcomes() -> None:
    """ok / mismatch / unreadable(눈이 못 본 것은 틀린 게 아니다) / no_expectation(감사 불가) — 서로 배타."""
    assert cpa.anchor_verdict("knee", EXP_KNEE) == "ok"
    assert cpa.anchor_verdict("elbow", EXP_KNEE) == "mismatch"
    for tok in ("unclear", "error", None, "zzz"):
        assert cpa.anchor_verdict(tok, EXP_KNEE) == "unreadable", tok
    assert cpa.anchor_verdict("knee", frozenset()) == "no_expectation"
    assert cpa.anchor_verdict("zzz", frozenset()) == "no_expectation"
    assert cpa.ANCHOR_VERDICTS == ("ok", "mismatch", "unreadable", "no_expectation")


# ── card_gates 상수 — 측정값 그대로, 새 튜닝 0 ────────────────────────────────


def test_constants_are_measurement_values_and_defaults_reuse_them() -> None:
    """0.18 = 36패널 측정에 쓴 값 / 재확인 상한 2 / 3회 최빈 — 기본 인자가 그 객체를 가리킨다."""
    assert cg.ANCHOR_CHECK_CROP_FRAC == 0.18
    assert cg.ANCHOR_CHECK_MAX_RETRY == 2
    assert cg.ANCHOR_CHECK_ROUNDS == 3
    assert (inspect.signature(cg.part_crop).parameters["frac"].default
            is cg.ANCHOR_CHECK_CROP_FRAC)
    p = inspect.signature(cg.anchor_retry_frames).parameters
    assert p["radius"].default is fz._MOMENT_ANCHOR_RADIUS_WIDE  # noqa: SLF001
    assert p["limit"].default is cg.ANCHOR_CHECK_MAX_RETRY


# ── part_crop — 무마킹 좁은 정사각 ───────────────────────────────────────────


def _frame(h: int, w: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


def test_part_crop_is_unmarked_square_of_short_side_fraction() -> None:
    """200x300 프레임, (150,100) → 한 변 round(200*0.18)=36, 픽셀이 원본과 완전 동일(링 0)."""
    frame = _frame(200, 300)
    crop = cg.part_crop(frame, (150.0, 100.0))
    assert crop.mode == "RGB" and crop.size == (36, 36)
    assert np.array_equal(np.asarray(crop), frame[82:118, 132:168])


def test_part_crop_clamps_at_borders_without_shrinking() -> None:
    """경계 좌표는 클램프 — 변이 줄지 않고 프레임 안으로 민다(mark_crop 과 같은 식)."""
    frame = _frame(200, 300)
    tl = cg.part_crop(frame, (0.0, 0.0))
    assert tl.size == (36, 36) and np.array_equal(np.asarray(tl), frame[0:36, 0:36])
    br = cg.part_crop(frame, (299.0, 199.0))
    assert br.size == (36, 36) and np.array_equal(np.asarray(br), frame[164:200, 264:300])


def test_part_crop_tiny_frame_still_has_side_at_least_one() -> None:
    """아주 작은 프레임(10x10)도 예외 없이 변 >= 1 — 축소본 폴백에서 크롭이 0 이 되면 안 된다."""
    crop = cg.part_crop(_frame(10, 10), (5.0, 5.0))
    assert crop.size[0] >= 1 and crop.size[0] == crop.size[1]


# ── eye_part_token — 조기 종료 최빈 (eye_judge 대본, 네트워크 0) ─────────────


def _scripted_part_eye(monkeypatch, script: list[str]) -> list[dict]:
    calls: list[dict] = []

    def fake(crop, claim, *, api_key, expected_limb=None, joint_kind=None,
             model=cg.DEFAULT_C_MODEL, timeout_s=60.0):
        i = len(calls)
        calls.append({"claim": claim, "expected_limb": expected_limb,
                      "joint_kind": joint_kind, "api_key": api_key, "model": model})
        tok = script[i]   # 대본 밖 호출 = IndexError → 조기 종료 실패가 드러난다
        return {"observed": tok, "limb": "other", "match": tok in cg.PART_TOKENS,
                "confidence": 0.9, "reason": f"r{i}:{tok}"}

    monkeypatch.setattr(cg, "eye_judge", fake)
    return calls


@pytest.mark.parametrize("script,observed,n", [
    (["knee", "knee"], "knee", 2),                       # 2표면 3회 최빈과 결과 동일 → 조기 종료
    (["knee", "elbow", "knee"], "knee", 3),
    (["knee", "elbow", "thigh"], "unclear", 3),          # 동률 = unclear
    (["unclear", "unclear", "unclear"], "unclear", 3),   # 못 읽음은 표가 아니라 조기 종료 안 됨
    (["error", "knee", "knee"], "knee", 3),
])
def test_eye_part_token_modal_with_early_stop(monkeypatch, script, observed, n) -> None:
    """운영 질문(claim=part, 힌트·기대 0) 그대로, 표만 여기서 센다 — 뒤집을 수 없으면 멈춘다."""
    calls = _scripted_part_eye(monkeypatch, script)
    res = cg.eye_part_token("crop", api_key="k")
    assert res["observed"] == observed
    assert res["calls"] == n and len(calls) == n
    assert res["tokens"] == script[:n]
    for c in calls:
        assert c["claim"] == "part"
        assert c["expected_limb"] is None and c["joint_kind"] is None   # 기대가 새면 감사 전제가 깨진다
        assert c["api_key"] == "k" and c["model"] == cg.DEFAULT_C_MODEL
    if observed != "unclear":
        assert res["reason"] == f"r{script.index(observed)}:{observed}"   # 최빈 토큰 첫 응답


def test_eye_part_token_rejects_even_rounds(monkeypatch) -> None:
    """홀수만 — 동률 방지 (eye_judge_majority 관례)."""
    _scripted_part_eye(monkeypatch, ["knee"] * 4)
    with pytest.raises(ValueError):
        cg.eye_part_token("crop", api_key="k", rounds=2)


# ── anchor_retry_frames — 창 안 건전 후보 ≤2, _frame_usable 공유 ─────────────


def test_retry_frames_nearest_first_minus_before_plus_skipping_collapsed() -> None:
    """앵커 3±1 붕괴 → d=2 에서 −d 먼저: [1, 5] (결정론 순회 = 창 승급 관례)."""
    kinds = ["o", "o", "x", "x", "x", "o", "o"]
    rep = _mk(kinds, [0.9] * len(kinds))
    assert cg.anchor_retry_frames(rep, 3, MEMBERS, n_frames=len(kinds)) == [1, 5]


def test_retry_frames_limit_two_and_anchor_excluded() -> None:
    """전부 성해도 앵커 자신 제외·상한 2 — 후보가 5+ 있어도 [2, 4]."""
    rep = _mk(["o"] * 7, [0.9] * 7)
    assert cg.anchor_retry_frames(rep, 3, MEMBERS, n_frames=7) == [2, 4]


def test_retry_frames_skips_out_of_range() -> None:
    """앵커 0 — −1 은 없고 스킵, [1, 2]."""
    rep = _mk(["o"] * 5, [0.9] * 5)
    assert cg.anchor_retry_frames(rep, 0, MEMBERS, n_frames=5) == [1, 2]


def test_retry_frames_all_collapsed_is_empty() -> None:
    """건전 후보 0 = 빈 목록 — 호출측은 앵커에서 곧장 suppress 로 간다."""
    rep = _mk(["x"] * 5, [0.9] * 5)
    assert cg.anchor_retry_frames(rep, 2, MEMBERS, n_frames=5) == []


def test_retry_frames_excludes_undrawable_same_as_frame_usable() -> None:
    """비붕괴여도 conf 0.3(그릴 수 없음)은 제외 — 판정 함수는 fault_zoom._frame_usable 한 개."""
    rep = _mk(["o"] * 5, [0.9, 0.3, 0.9, 0.3, 0.9])
    assert cg.anchor_retry_frames(rep, 2, MEMBERS, n_frames=5) == [0, 4]
    for i in (1, 3):
        assert fz._frame_usable(rep, i, MEMBERS, 9.0, 9.0, 5) is False  # noqa: SLF001


# ── verify_anchor_side — 순수 상태기계 (눈·좌표·프레임은 ask 주입) ──────────


def _ask_script(script: dict[int, str | tuple[str, int]]):
    """대본 {frame: token | (token, calls)} → ask. 대본에 없는 프레임 = None(판정 불가)."""
    asked: list[int] = []

    def ask(frame_idx: int):
        asked.append(frame_idx)
        v = script.get(frame_idx)
        if v is None:
            return None
        tok, calls = (v, 1) if isinstance(v, str) else v
        return {"observed": tok, "calls": calls}

    return ask, asked


def test_verify_pass_on_anchor_asks_once() -> None:
    """좌표가 맞으면 통과 — 재확인 후보가 있어도 안 묻는다."""
    ask, asked = _ask_script({30: "knee", 29: "knee"})
    out = cg.verify_anchor_side(anchor_idx=30, expected=EXP_KNEE,
                                retry_frames=[29, 31], ask=ask)
    assert out.action == "pass" and out.frame_idx == 30
    assert out.trail == ((30, "knee", "ok"),)
    assert out.eye_calls == 1 and asked == [30]


def test_verify_mismatch_then_moved_to_first_passing_candidate() -> None:
    """앵커 틀림 → 가까운 후보부터, 통과하면 그 프레임으로 이동하고 나머지는 안 묻는다."""
    ask, asked = _ask_script({30: "elbow", 29: "knee", 31: "knee"})
    out = cg.verify_anchor_side(anchor_idx=30, expected=EXP_KNEE,
                                retry_frames=[29, 31], ask=ask)
    assert out.action == "moved" and out.frame_idx == 29
    assert asked == [30, 29] and out.eye_calls == 2
    assert out.trail == ((30, "elbow", "mismatch"), (29, "knee", "ok"))


def test_verify_all_fail_suppresses_but_keeps_anchor_frame() -> None:
    """그래도 실패면 suppressed — frame_idx 는 앵커(사진은 그 멈춤 그대로, 표시만 생략)."""
    ask, asked = _ask_script({30: "elbow", 29: "hand", 31: "elbow"})
    out = cg.verify_anchor_side(anchor_idx=30, expected=EXP_KNEE,
                                retry_frames=[29, 31], ask=ask)
    assert out.action == "suppressed" and out.frame_idx == 30
    assert asked == [30, 29, 31] and out.eye_calls == 3
    assert out.trail == ((30, "elbow", "mismatch"), (29, "hand", "mismatch"),
                         (31, "elbow", "mismatch"))


def test_verify_retry_cap_is_owned_by_the_function() -> None:
    """호출측이 후보 5개를 줘도 앵커+2 = 정확히 3회 — 비용 상한은 순수 함수가 소유."""
    ask, asked = _ask_script({f: "elbow" for f in (30, 29, 31, 28, 32, 27)})
    out = cg.verify_anchor_side(anchor_idx=30, expected=EXP_KNEE,
                                retry_frames=[29, 31, 28, 32, 27], ask=ask)
    assert out.action == "suppressed" and asked == [30, 29, 31]


def test_verify_unbound_when_no_expectation_or_anchor_unaskable() -> None:
    """expected 빈 집합 = 0회 / ask(anchor) None(좌표·프레임·키 부재) = 비구속 — 감사 불가는 불일치가 아니다."""
    ask, asked = _ask_script({30: "elbow"})
    out = cg.verify_anchor_side(anchor_idx=30, expected=frozenset(),
                                retry_frames=[29], ask=ask)
    assert out.action == "unbound" and out.frame_idx == 30
    assert out.eye_calls == 0 and out.trail == () and asked == []
    ask2, asked2 = _ask_script({})
    out2 = cg.verify_anchor_side(anchor_idx=30, expected=EXP_KNEE,
                                 retry_frames=[29], ask=ask2)
    assert out2.action == "unbound" and asked2 == [30] and out2.eye_calls == 0


def test_verify_unreadable_anchor_passes_and_unreadable_candidate_is_skipped() -> None:
    """눈이 못 본 것은 틀린 게 아니다 — 앵커 unclear = pass; 후보 unclear 는 다음 후보로."""
    ask, asked = _ask_script({30: "unclear"})
    out = cg.verify_anchor_side(anchor_idx=30, expected=EXP_KNEE,
                                retry_frames=[29, 31], ask=ask)
    assert out.action == "pass" and out.frame_idx == 30
    assert out.trail == ((30, "unclear", "unreadable"),) and asked == [30]
    ask, asked = _ask_script({30: "elbow", 29: "unclear", 31: "knee"})
    out = cg.verify_anchor_side(anchor_idx=30, expected=EXP_KNEE,
                                retry_frames=[29, 31], ask=ask)
    assert out.action == "moved" and out.frame_idx == 31 and asked == [30, 29, 31]


def test_verify_none_candidate_consumes_retry_budget_without_a_call() -> None:
    """후보 ask None 은 호출 0 으로 스킵하되 상한을 소모한다 — 28 은 안 묻고 suppressed."""
    ask, asked = _ask_script({30: "elbow", 31: "elbow", 28: "knee"})
    out = cg.verify_anchor_side(anchor_idx=30, expected=EXP_KNEE,
                                retry_frames=[29, 31, 28], ask=ask)
    assert out.action == "suppressed" and asked == [30, 29, 31]
    assert out.eye_calls == 2   # 29 는 호출 0


def test_verify_sums_calls_reported_by_ask_cache_hits_count_zero() -> None:
    """eye_calls = ask 가 보고한 calls 합 — 캐시 적중(0)은 더해지지 않는다."""
    ask, _asked = _ask_script({30: ("elbow", 0), 29: ("knee", 2)})
    out = cg.verify_anchor_side(anchor_idx=30, expected=EXP_KNEE,
                                retry_frames=[29], ask=ask)
    assert out.action == "moved" and out.eye_calls == 2


def test_outcome_cannot_drop_a_card() -> None:
    """action 4종 어느 것도 방출을 바꾸지 않는다 — emit/drop 류 필드 자체가 없다 (belle 09-03 규칙 1)."""
    assert cg.ANCHOR_ACTIONS == ("pass", "moved", "suppressed", "unbound")
    assert set(cg.AnchorCheckOutcome.__dataclass_fields__) == {
        "action", "frame_idx", "trail", "eye_calls",
    }
