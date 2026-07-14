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


# ── 22-07 게이트 비대칭 마스크 fix — 공통 가시 마스크 + 가림 복원 분리 ──────────
def test_grounding_visible_from_common_mask():
    """visible_from 지정 시 교란입력의 가시 관절만 계측(보정/무보정 공정 비교)."""
    truth = np.array([[0.0, 0.0], [10.0, 10.0], [20.0, 20.0]])
    # 교란입력: 관절2 가려짐(NaN). 관절0/1 은 가시.
    perturbed = np.array([[3.0, 4.0], [13.0, 14.0], [np.nan, np.nan]])
    # 모델 보정본: 관절2 를 복원(값 채움, 큰 오차).
    pred = np.array([[0.0, 0.0], [10.0, 10.0], [90.0, 90.0]])
    # 공통 가시 마스크(관절0/1)에서만 계측 → 관절2 복원 오차 미포함, 보정 L2 = 0.
    assert rb.score_grounding(pred, truth, visible_from=perturbed) == pytest.approx(0.0)
    # 무보정도 같은 마스크 → 관절0/1 의 교란 L2 = 5.0.
    assert rb.score_grounding(perturbed, truth, visible_from=perturbed) == pytest.approx(5.0)


def test_grounding_occluded_restored_isolated():
    """가림 복원 L2 는 교란입력에서 가려진 관절만 별도 계측."""
    truth = np.array([[0.0, 0.0], [10.0, 10.0], [20.0, 20.0]])
    perturbed = np.array([[3.0, 4.0], [13.0, 14.0], [np.nan, np.nan]])
    pred = np.array([[0.0, 0.0], [10.0, 10.0], [23.0, 24.0]])  # 관절2 복원 오차 5.
    assert rb.score_grounding_occluded(pred, truth, perturbed) == pytest.approx(5.0)


def test_grounding_occluded_none_returns_nan():
    """가림 관절이 없으면 복원 L2 계측 대상 없음 → NaN."""
    truth = np.array([[0.0, 0.0], [10.0, 10.0]])
    perturbed = np.array([[3.0, 4.0], [13.0, 14.0]])  # 가림 0.
    pred = np.array([[0.0, 0.0], [10.0, 10.0]])
    assert np.isnan(rb.score_grounding_occluded(pred, truth, perturbed))


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


# ── aligned 프롬프트 모드 (quick-260714-hv4) — 계측-학습 양식 정렬 ─────────────
def test_aligned_user_text_matches_training_format():
    """Test 1 — aligned user 텍스트 = build_jsonl._rtmw_text + _TASK_INSTRUCTION
    문자 단위 동일 (import 재사용 — 복사 검출)."""
    from datagen import build_jsonl

    rows = [
        {"frame": 0, "left_knee": [500, 500, 0.9]},
        {"frame": 9, "left_knee": None},
    ]
    msgs = rb.build_aligned_report_messages(rows, [])
    texts = [c["text"] for c in msgs[-1]["content"] if c.get("type") == "text"]
    assert len(texts) == 1
    expected = build_jsonl._rtmw_text(rows) + build_jsonl._TASK_INSTRUCTION
    assert texts[0] == expected
    # 문자열 복사본이 아니라 build_jsonl 모듈 객체 재사용 (단일 진실).
    assert rb._TASK_INSTRUCTION is build_jsonl._TASK_INSTRUCTION
    assert rb._rtmw_text is build_jsonl._rtmw_text


def test_aligned_no_system_no_motion_line_media_first():
    """Test 2 — system 롤 0건, 동작명 라인 없음, content = media 먼저 → text 마지막."""
    rows = [{"frame": 0, "left_knee": [1, 2, 0.9]}]
    media = [{"type": "video_url", "video_url": {"url": "file:///tmp/x.mp4"}}]
    msgs = rb.build_aligned_report_messages(rows, media)
    assert all(m.get("role") != "system" for m in msgs)
    assert len(msgs) == 1 and msgs[0]["role"] == "user"
    content = msgs[0]["content"]
    assert content[0]["type"] == "video_url"  # media 먼저.
    assert content[-1]["type"] == "text"      # text 마지막.
    assert "분석 대상 동작" not in content[-1]["text"]
    # media 없으면 text 단독 (합성 트랙 좌표 단독 정상 폴백).
    only_text = rb.build_aligned_report_messages(rows, [])
    assert [c["type"] for c in only_text[0]["content"]] == ["text"]


def test_legacy_report_messages_unchanged():
    """Test 3 — 기본(legacy) 메시지 조립 불변: system 존재 + _REPORT_TASK_TEXT +
    동작명 라인 + text 먼저 (opt-in 이 기존 동작을 못 건드림)."""
    rows = [{"frame": 0, "left_knee": [1, 2, 0.9]}]
    msgs = rb.build_report_messages(rows, ["aGVsbG8="], "kip-up", "zero")
    assert msgs[0]["role"] == "system"
    user_text = msgs[-1]["content"][0]["text"]
    assert msgs[-1]["content"][0]["type"] == "text"  # legacy 는 text 먼저.
    assert "분석 대상 동작: kip-up." in user_text
    assert rb._REPORT_TASK_TEXT in user_text


def test_argparse_defaults_prompt_mode_legacy_rp1(monkeypatch):
    """Test 4 — --prompt-mode 기본 legacy(env 폴백) / --repetition-penalty 기본 1.0."""
    monkeypatch.delenv("BAKEOFF_PROMPT_MODE", raising=False)
    args = rb._build_parser().parse_args([])
    assert args.prompt_mode == "legacy"
    assert args.repetition_penalty == 1.0
    assert args.media == "auto"
    # env BAKEOFF_PROMPT_MODE 폴백.
    monkeypatch.setenv("BAKEOFF_PROMPT_MODE", "aligned")
    assert rb._build_parser().parse_args([]).prompt_mode == "aligned"
    # 명시 플래그가 env 를 이긴다.
    assert rb._build_parser().parse_args(["--prompt-mode", "legacy"]).prompt_mode == "legacy"


def test_svg_wellformed_observation():
    # F2 관측치 — 유효 svg_spec = 1.0, target_angle_deg 비수치/구조 위반 = 0.0.
    good = {"force_vector": [1, 0], "ideal_trajectory": [[0, 0]], "target_angle_deg": 175}
    assert rb.score_svg_wellformed(good) == 1.0
    bad = {"force_vector": [1, 0], "ideal_trajectory": [[0, 0]], "target_angle_deg": "약 175도"}
    assert rb.score_svg_wellformed(bad) == 0.0
    assert rb.score_svg_wellformed(None) == 0.0
