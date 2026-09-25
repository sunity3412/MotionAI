"""평가셋 분리 점검(backend/scripts/eval_split_check.py) 순수 부분 — 37-DATA-SPEC 규칙 6.
단언: (1) 봉인 시험지 영상 → 짝 → 같은 인물·세션 클립까지 평가 그룹 (2) 연습 문제로 빠진 영상도 평가(정답 공개) (3) L1/L2/L3 분류
(4) 인물 1명이면 보고서가 '인물 분리 불가'를 적는다 (5) holdout 행은 학습 후보가 아니다."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("eval_split_check", Path(__file__).resolve().parents[1] / "scripts" / "eval_split_check.py")
esc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(esc)

H = lambda c: c * 64  # noqa: E731


def _clips():
    return [
        {"video_hash": H("a"), "subject_id": "sub_je", "capture": {"session": "2026-06-17"}, "s3_key": "fixtures/phase15/ps/correct.mp4"},
        {"video_hash": H("b"), "subject_id": "sub_je", "capture": {"session": "2026-06-17"}, "s3_key": "fixtures/phase15/ps/fault.mp4"},
        {"video_hash": H("c"), "subject_id": "sub_je", "capture": {"session": "2026-06-17"}, "s3_key": "fixtures/phase15/climb/fault.mp4"},
        {"video_hash": H("d"), "subject_id": "sub_s01", "capture": {"session": "2026-10-05"}, "s3_key": "fixtures/intake/d.mov"},
        {"video_hash": H("e"), "subject_id": "sub_je", "capture": {"session": "2026-10-05"}, "s3_key": "fixtures/intake/e.mov"},
    ]


def _pairs():
    return [{"correct_hash": H("a"), "fault_hash": H("b")}]


def _sealed():
    return [{"rows": [{"video_hash": H("d")}], "practice": [{"video_hash": H("b")}]}]


def test_eval_groups_expand_by_pair_and_session():
    ev = esc.eval_groups(_clips(), _pairs(), _sealed())
    assert ev["hashes"] == {H("d"), H("b"), H("a")}                # 시험지 d + 연습 b + 짝 a
    assert ev["groups"] == {("sub_s01", "2026-10-05"), ("sub_je", "2026-06-17")}
    assert {c["video_hash"] for c in ev["clips"]} == {H("a"), H("b"), H("c"), H("d")}  # c 는 같은 세션이라 평가
    assert ev["subjects"] == {"sub_je", "sub_s01"}


def test_leak_levels():
    ev = esc.eval_groups(_clips(), _pairs(), _sealed())
    manifest = [
        {"s3_key": "fixtures/phase15/ps/fault.mp4", "holdout": None},        # L1 평가 영상 자체
        {"s3_key": "fixtures/phase15/climb/fault.mp4", "holdout": None},     # L1 (같은 세션 클립도 평가 클립)
        {"s3_key": "fixtures/intake/e.mov", "holdout": None},                # L3 같은 인물 다른 세션
        {"s3_key": "reference/ref-kip-up.mp4", "holdout": None},             # L3 reference = sub_je
        {"s3_key": "fixtures/phase15/ps/correct.mp4", "holdout": "sealed_eval"},  # holdout 은 후보 아님
        {"s3_key": "youtube/x.mp4", "holdout": None},                        # 무관
    ]
    leaks = esc.find_leaks(manifest, _clips(), ev, eligible=lambda r: not r.get("holdout") and bool(r.get("s3_key")))
    assert leaks["L1_same_file"] == ["fixtures/phase15/ps/fault.mp4", "fixtures/phase15/climb/fault.mp4"]
    assert leaks["L2_same_session"] == []
    assert leaks["L3_same_subject"] == ["fixtures/intake/e.mov", "reference/ref-kip-up.mp4"]


def test_report_states_single_subject_limit_and_verdict():
    ev = esc.eval_groups(_clips()[:3], _pairs(), [{"rows": [{"video_hash": H("c")}], "practice": []}])
    md = esc.render_report(ev, {"L1_same_file": [], "L2_same_session": [], "L3_same_subject": ["reference/ref-x.mp4"]}, 10, now="t")
    assert "인물 분리 불가" in md and "세션 분리 OK" in md
    md2 = esc.render_report(ev, {"L1_same_file": ["fixtures/phase15/climb/fault.mp4"], "L2_same_session": [], "L3_same_subject": []}, 10, now="t")
    assert "누수" in md2
