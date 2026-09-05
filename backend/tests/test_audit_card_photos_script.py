"""audit_card_photos 스크립트의 순수 헬퍼 테스트 (quick-260905-mvm) — 네트워크·Firestore 0.

modal_token(토큰 다수결·동률 fail-closed) / split_panels(fault_zoom._compose 기하 복원) /
parse_pairs(입력 형식). 눈 호출·문서 읽기는 스크립트 실행(라이브 검증)의 몫.
"""

from __future__ import annotations

import argparse
import io

import pytest
from PIL import Image

import audit_card_photos as acp


def test_modal_token_majority_and_ties():
    assert acp.modal_token(["knee", "knee", "elbow"]) == "knee"
    assert acp.modal_token(["thigh"]) == "thigh"
    assert acp.modal_token(["knee", "elbow"]) == "unclear"           # 동률 = fail-closed
    assert acp.modal_token(["unclear", "unclear", "error"]) == "unclear"
    assert acp.modal_token(["unclear", "unclear", "hip"]) == "hip"    # 못 읽음은 표가 아니다
    assert acp.modal_token(["bent", "bent", "bent"]) == "unclear"     # 어휘 밖 = 못 읽음
    assert acp.modal_token([]) == "unclear"


def _png(w: int, h: int) -> bytes:
    img = Image.new("RGB", (w, h), (255, 255, 255))
    # 왼쪽 패널 빨강, 오른쪽 패널 파랑 — 이등분이 어느 쪽을 잘랐는지 픽셀로 확인
    left_w = h if w - 2 * h >= 0 else w // 2
    for x in range(w):
        for y in range(0, h, max(1, h // 8)):
            img.putpixel((x, y), (255, 0, 0) if x < left_w else (0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_split_panels_recovers_compose_gap():
    """_compose 형상(정사각 2 + gap 6) → 각 패널 정사각, gap 픽셀은 어느 쪽에도 안 들어간다."""
    user, ref = acp.split_panels(_png(360 * 2 + 6, 360))
    assert user.size == (360, 360) and ref.size == (360, 360)
    assert user.getpixel((359, 0)) == (255, 0, 0)
    assert ref.getpixel((0, 0)) == (0, 0, 255)


def test_split_panels_falls_back_to_halves_on_unknown_shape():
    user, ref = acp.split_panels(_png(800, 300))   # gap 200 > 상한 → 단순 이등분
    assert user.size == (400, 300) and ref.size == (400, 300)
    user, ref = acp.split_panels(_png(500, 300))   # gap 음수 → 단순 이등분
    assert user.size == (250, 300) and ref.size == (250, 300)


def test_parse_pairs_forms():
    ns = argparse.Namespace(uid="u1", analysis_id="a1", pairs="u2:a2, u3:a3,")
    assert acp.parse_pairs(ns) == [("u1", "a1"), ("u2", "a2"), ("u3", "a3")]
    with pytest.raises(SystemExit):
        acp.parse_pairs(argparse.Namespace(uid=None, analysis_id=None, pairs="bad"))
    with pytest.raises(SystemExit):
        acp.parse_pairs(argparse.Namespace(uid=None, analysis_id=None, pairs=""))


# ── 2단 판정 (quick-260905-ota) — 표시 질의는 1단 탈락 + 표시 있는 패널에만 ───────

from sunity_shared.analysis import card_gates as cg  # noqa: E402
from sunity_shared.analysis import card_photo_audit as cpa  # noqa: E402


def test_modal_token_vocab_for_mark_part():
    """mark_part 다수결은 no_mark 도 표로 센다 — part 어휘에서는 못 읽음."""
    votes = ["no_mark", "no_mark", "neck"]
    assert acp.modal_token(votes, cpa.MARK_VOCAB) == "no_mark"
    assert acp.modal_token(votes) == "neck"                       # 기본(part) 어휘: no_mark 는 표 아님
    assert acp.modal_token(["no_mark", "neck"], cpa.MARK_VOCAB) == "unclear"   # 동률
    assert acp._CLAIM_VOCAB == {"part": cpa.PART_VOCAB, "mark_part": cpa.MARK_VOCAB}


def test_judge_panel_passes_claim_and_uses_claim_vocab(monkeypatch):
    calls: list[str] = []
    answers = iter(["no_mark", "no_mark", "shoulder"])

    def fake_eye_judge(panel, claim, *, api_key, model, **_kw):
        calls.append(claim)
        return {"observed": next(answers), "limb": "other", "match": True,
                "confidence": 0.5, "reason": "r"}

    monkeypatch.setattr(cg, "eye_judge", fake_eye_judge)
    out = acp.judge_panel(object(), api_key="k", model="m", rounds=3, claim="mark_part")
    assert calls == ["mark_part"] * 3
    assert out["claim"] == "mark_part" and out["observed"] == "no_mark"
    assert out["votes"] == {"no_mark": 2, "shoulder": 1}
    with pytest.raises(ValueError):
        acp.judge_panel(object(), api_key="k", model="m", rounds=1, claim="bent")


def _side_of(panel) -> str:
    """테스트용 패널 식별 — _png 가 왼쪽을 빨강, 오른쪽을 파랑으로 칠한다."""
    return "user" if panel.getpixel((0, 0)) == (255, 0, 0) else "ref"


def test_audit_doc_two_tier_flow_offline(monkeypatch):
    """카드 3장 오프라인 흐름 — 2단은 1단 탈락+표시 패널에만, 결말은 adjudicate/card_verdict.

    [0] 오른어깨: user 정중앙 shoulder(통과), ref 정중앙 neck + 표시 있음 → 2단 → shoulder
        → ok by mark. 카드 ok.
    [1] 오른팔꿈치: user 정중앙 back_waist + userMarked=False → 2단 없이 확정(by none),
        ref elbow 통과. 카드 mismatch.
    [2] 참고 왼골반(criterion 없음): user thigh 통과, ref knee + 표시 → 2단 → knee
        → mark_elsewhere. 카드 mismatch.
    """
    doc = {"referenceMotionId": "ref-x", "result": {"faultZoomComparisons": [
        {"joint": "right_shoulder", "criterion": "angle_vs_reference__right_shoulder",
         "tier": "confirmed", "imageUrl": "u0", "userMarked": True, "refMarked": True},
        {"joint": "right_elbow", "criterion": "angle_vs_reference__right_elbow",
         "tier": "confirmed", "imageUrl": "u1", "userMarked": False, "refMarked": True},
        {"joint": "left_hip", "criterion": None, "tier": "advisory", "imageUrl": "u2"},
    ]}}
    center = {  # (card, side) → 1단 토큰
        (0, "user"): "shoulder", (0, "ref"): "neck",
        (1, "user"): "back_waist", (1, "ref"): "elbow",
        (2, "user"): "thigh", (2, "ref"): "knee",
    }
    mark = {(0, "ref"): "shoulder", (2, "ref"): "knee"}
    card_no = {"n": -1}
    calls: list[tuple[int, str, str]] = []

    def fake_fetch(card, **_kw):
        card_no["n"] += 1
        return _png(360 * 2 + 6, 360)

    def fake_eye_judge(panel, claim, *, api_key, model, **_kw):
        key = (card_no["n"], _side_of(panel))
        calls.append((key[0], key[1], claim))
        tok = center[key] if claim == "part" else mark[key]
        return {"observed": tok, "limb": "other", "match": True,
                "confidence": 0.9, "reason": "r"}

    monkeypatch.setattr(acp.fa, "get_analysis", lambda uid, aid: doc)
    monkeypatch.setattr(acp, "fetch_png", fake_fetch)
    monkeypatch.setattr(cg, "eye_judge", fake_eye_judge)

    rows = acp.audit_doc("u", "a", api_key="k", model="m", rounds=3, dump_dir=None)
    assert [r["verdict"] for r in rows] == ["ok", "mismatch", "mismatch"]
    # 2단 호출은 정확히 두 패널(카드 0 ref, 카드 2 ref) × 3회 — 표시 없는 카드 1 user 는 0회
    tier2 = [c for c in calls if c[2] == "mark_part"]
    assert tier2 == [(0, "ref", "mark_part")] * 3 + [(2, "ref", "mark_part")] * 3
    assert len([c for c in calls if c[2] == "part"]) == 3 * 2 * 3
    assert rows[0]["refAdj"] == {"ok": True, "by": "mark", "reason": "mark_in_expected"}
    assert rows[0]["userAdj"]["by"] == "center" and rows[0]["userMark"] is None
    assert rows[1]["userAdj"] == {"ok": False, "by": "none",
                                  "reason": "no_mark_and_center_elsewhere"}
    assert rows[1]["userMark"] is None and rows[1]["mismatch"] is True
    assert rows[2]["refAdj"] == {"ok": False, "by": "mark", "reason": "mark_elsewhere"}
    assert rows[2]["refMark"]["observed"] == "knee"
    # 1단 대조(audit_card)는 그대로 실려 mvm 로그와 대조 가능
    assert rows[0]["audit"] == {"userOk": True, "refOk": False, "flags": ["ref:mark_mismatch"]}


def test_fmt_side():
    adj = {"ok": True, "by": "mark", "reason": "mark_in_expected"}
    assert acp._fmt_side({"observed": "neck"}, {"observed": "shoulder"}, adj) == \
        "neck→shoulder True/mark:mark_in_expected"
    adj = {"ok": False, "by": "none", "reason": "no_mark_and_center_elsewhere"}
    assert acp._fmt_side({"observed": "back_waist"}, None, adj) == \
        "back_waist→- False/none:no_mark_and_center_elsewhere"
