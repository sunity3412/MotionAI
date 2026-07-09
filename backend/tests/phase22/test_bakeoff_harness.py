"""Phase 22 bake-off 계측 함수 pod-free 검증 (22-05 Task 3).

run_bakeoff 의 4축 계측 함수를 **직접 import**해 모델 호출 없이 순수 로직만 검증한다
(GPU/네트워크/Pod 0). bake-off 계측의 수학이 Pod 실행 전에 확정되면, Pod 시간이
순수 추론에만 쓰인다. score_coaching 은 judge 를 주입 가능 callable 로 두어 mock 으로
블라인드성을 검증한다(모델명 미포함).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

_BACKEND = Path(__file__).resolve().parents[2]
_RUN_BAKEOFF = _BACKEND / "evals" / "phase22" / "run_bakeoff.py"


def _load_harness():
    """run_bakeoff.py 를 spec 으로 로드(자체 sys.path 주입 — schema import 포함)."""
    spec = importlib.util.spec_from_file_location("rb_harness", _RUN_BAKEOFF)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rb = _load_harness()


# ── Test 1: score_grounding — 동일 좌표 L2=0, 알려진 오프셋 정확한 L2 ──────────
def test_grounding_identical_coords_is_zero():
    coords = np.array([[100.0, 200.0], [50.0, 75.0], [10.0, 20.0]])
    assert rb.score_grounding(coords, coords) == 0.0


def test_grounding_known_offset_exact_l2():
    truth = np.array([[0.0, 0.0], [10.0, 10.0], [20.0, 20.0]])
    # 전 관절 (3,4) 오프셋 → 관절별 L2 = 5.0 → 평균 5.0.
    pred = truth + np.array([3.0, 4.0])
    assert rb.score_grounding(pred, truth) == pytest.approx(5.0)


def test_grounding_ignores_nan_occluded_joints():
    truth = np.array([[0.0, 0.0], [10.0, 10.0]])
    pred = np.array([[3.0, 4.0], [np.nan, np.nan]])  # 2번 관절 가려짐.
    # 유효 관절(0번)만 계측 → L2 = 5.0.
    assert rb.score_grounding(pred, truth) == pytest.approx(5.0)


def test_grounding_shape_mismatch_raises():
    with pytest.raises(ValueError):
        rb.score_grounding(np.zeros((3, 2)), np.zeros((4, 2)))


# ── Test 2: score_json — 파싱/EM/정렬·누락·여분 감지 ─────────────────────────
def _valid_report():
    # REPORT_KEYS 순서(알파벳): coaching, corrected_coords, faults, segments,
    # svg_spec, time_anchors.
    return {k: None for k in rb.schema.REPORT_KEYS}


def test_json_valid_report_parse_and_exact_match():
    res = rb.score_json(_valid_report())
    assert res["parse"] == 1.0
    assert res["exact_match"] == 1.0
    assert res["cer"] == 0.0


def test_json_missing_key_detected():
    raw = _valid_report()
    del raw["faults"]  # 키 누락.
    res = rb.score_json(raw)
    assert res["parse"] == 1.0
    assert res["exact_match"] == 0.0
    assert res["cer"] > 0.0


def test_json_extra_key_detected():
    raw = _valid_report()
    raw["overall_score"] = 88  # 여분(스키마 밖) 키 — score 계열은 특히 금지.
    res = rb.score_json(raw)
    assert res["exact_match"] == 0.0


def test_json_order_violation_detected():
    # 전 키 존재하나 알파벳 정렬 위반(철칙 2) → EM 0.
    raw = {
        "time_anchors": None,
        "coaching": None,
        "corrected_coords": None,
        "faults": None,
        "segments": None,
        "svg_spec": None,
    }
    assert list(raw.keys()) != sorted(raw.keys())  # 전제: 정렬 안 됨.
    res = rb.score_json(raw)
    assert res["exact_match"] == 0.0


def test_json_non_dict_is_parse_failure():
    res = rb.score_json("모델이 JSON 대신 산문 출력")
    assert res["parse"] == 0.0
    assert res["exact_match"] == 0.0
    assert res["cer"] == 1.0


# ── Test 3: score_temporal — 함정 정방향 답 0점, CircularEval 전 조합만 1점 ───
def test_temporal_forward_answer_on_trap_is_zero():
    # 함정(역재생) 정답 = 'is_trap' 인데 정방향 제출 → 언어 프라이어 shortcut → 0.
    assert rb.score_temporal("forward", "is_trap") == 0.0


def test_temporal_circulareval_all_match_is_one():
    assert rb.score_temporal(["is_trap", "is_trap", "is_trap"], "is_trap") == 1.0


def test_temporal_circulareval_any_mismatch_is_zero():
    assert rb.score_temporal(["is_trap", "forward"], "is_trap") == 0.0


def test_temporal_empty_predictions_is_zero():
    assert rb.score_temporal([], "is_trap") == 0.0


# ── Test 4: score_coaching judge 블라인드 (모델명/후보명 미포함) ───────────────
def test_coaching_judge_prompt_has_no_model_names():
    prompt = rb.build_judge_prompt("무릎을 15도 더 펴면 스플릿 각도가 산다")
    lowered = prompt.lower()
    for banned in ("qwen", "internvl", "gemini", "candidate", "후보", "model_a", "model_b"):
        assert banned.lower() not in lowered, f"judge 프롬프트에 식별자 누출: {banned}"


def test_coaching_uses_injected_judge_callable():
    calls = {}

    def mock_judge(prompt: str) -> str:
        calls["prompt"] = prompt
        return "4"  # 블라인드 채점 결과.

    score = rb.score_coaching("정타 대비 팔꿈치가 20도 덜 펴짐", mock_judge)
    assert score == pytest.approx(4.0)
    assert "코칭 피드백" in calls["prompt"]  # 실제로 프롬프트가 전달됨.


def test_coaching_out_of_range_judge_is_nan():
    assert np.isnan(rb.score_coaching("x", lambda _p: "9"))  # 1~5 밖.
    assert np.isnan(rb.score_coaching("x", lambda _p: "설명만 있고 숫자 없음"))


# ── Test 5: manifest 4 타입 파싱 + synthetic_grounding 만 grounding 라우팅 ────
def test_manifest_loads_all_four_types():
    manifest = rb.load_manifest()
    by_type = rb.items_by_type(manifest)
    assert {"real", "hard_negative", "synthetic_grounding", "trap"} <= set(by_type)


def test_grounding_routing_only_synthetic_track():
    manifest = rb.load_manifest()
    g = rb.grounding_items(manifest)
    assert len(g) > 0
    assert all(r["type"] == "synthetic_grounding" for r in g)
    # real/hard_negative/trap 는 grounding 계측 대상 아님.
    non_synth = [r for r in manifest["items"] if r["type"] != "synthetic_grounding"]
    assert all(r not in g for r in non_synth)


def test_svg_wellformed_observation():
    # F2 관측치 — 유효 svg_spec = 1.0, target_angle_deg 비수치/구조 위반 = 0.0.
    good = {"force_vector": [1, 0], "ideal_trajectory": [[0, 0]], "target_angle_deg": 175}
    assert rb.score_svg_wellformed(good) == 1.0
    bad = {"force_vector": [1, 0], "ideal_trajectory": [[0, 0]], "target_angle_deg": "약 175도"}
    assert rb.score_svg_wellformed(bad) == 0.0
    assert rb.score_svg_wellformed(None) == 0.0
