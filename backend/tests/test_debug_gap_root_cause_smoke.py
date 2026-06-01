"""debug_gap_root_cause 5 가설 디버그 spike 스모크 테스트 (Plan 01-12).

mmpose / torch / boto3 / NLF 의존 없이 로컬 실행. 본 모듈은 가설 (c)/(d) 와
spike_vs_sweep / JSON shape / CLI 파싱만 검증한다. live mode 의 (a)(b)(e)
trace 함수는 별도 단위 입력을 만들어 직접 호출하지 않으면 mmpose 가 필요해
지므로 본 스모크에서는 다루지 않는다 (Plan 12 README live mode 절차에서
belle Pod 실행으로 검증).

테스트 범위 (Plan 12 T-4-2):
  1. CLI 파싱 — build_arg_parser defaults / required 동작.
  2. 가설 (c) trace — stub sweep JSON 입력 시 nlf_overall_range 정확 계산.
  3. 가설 (d) joint diff — 두 chain 정의 차이 검출.
  4. spike_vs_sweep — verdict 3 분기 (gpu_warmup / frame_extractor / both) 검증.
  5. JSON output shape — top-level + hypotheses 키 + .md sibling 생성.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.research.spikes.debug_gap_root_cause import (
    build_arg_parser,
    run_debug,
    trace_hypothesis_c,
    trace_hypothesis_d,
    trace_spike_vs_sweep,
)


# ── helper: stub sweep JSON ───────────────────────────────────────────────────


def _make_stub_sweep_report() -> dict:
    """Plan 11 sweep 실제 NLF overall 값 [58, 63, 64, 65, 81] 모사 stub."""
    return {
        "generated_at": "2026-06-01T04:11:00+00:00",
        "detector": "rtmpose-l",
        "lifter": "motionbert_lite",
        "score_threshold": 0.3,
        "det_model": "none",
        "motions": [
            {
                "motion": "ref-climb",
                "frames_total": 198,
                "rtmpose_mb": {
                    "overall": 89.0,
                    "stability": 89.0,
                    "line": None,
                    "angle": None,
                    "ms_per_frame": 21.0,
                    "avg_score": 0.45,
                },
                "nlf": {
                    "overall": 58.0,
                    "stability": 58.0,
                    "line": None,
                    "angle": None,
                    "ms_per_frame": 665.0,
                },
                "gap": {"overall": 31.0},
            },
            {
                "motion": "ref-foxtop-split",
                "frames_total": 180,
                "rtmpose_mb": {
                    "overall": 79.0,
                    "stability": 79.0,
                    "line": None,
                    "angle": None,
                    "ms_per_frame": 21.0,
                    "avg_score": 0.46,
                },
                "nlf": {
                    "overall": 63.0,
                    "stability": 63.0,
                    "line": None,
                    "angle": None,
                    "ms_per_frame": 665.0,
                },
                "gap": {"overall": 16.0},
            },
            {
                "motion": "ref-foxtop",
                "frames_total": 192,
                "rtmpose_mb": {
                    "overall": 81.0,
                    "stability": 81.0,
                    "line": None,
                    "angle": None,
                    "ms_per_frame": 21.0,
                    "avg_score": 0.46,
                },
                "nlf": {
                    "overall": 64.0,
                    "stability": 64.0,
                    "line": None,
                    "angle": None,
                    "ms_per_frame": 665.0,
                },
                "gap": {"overall": 17.0},
            },
            {
                "motion": "ref-invert",
                "frames_total": 175,
                "rtmpose_mb": {
                    "overall": 70.0,
                    "stability": 70.0,
                    "line": None,
                    "angle": None,
                    "ms_per_frame": 21.0,
                    "avg_score": 0.42,
                },
                "nlf": {
                    "overall": 65.0,
                    "stability": 65.0,
                    "line": None,
                    "angle": None,
                    "ms_per_frame": 665.0,
                },
                "gap": {"overall": 5.0},
            },
            {
                "motion": "ref-sideway-spin",
                "frames_total": 100,
                "rtmpose_mb": {
                    "overall": 80.0,
                    "stability": 80.0,
                    "line": None,
                    "angle": None,
                    "ms_per_frame": 21.0,
                    "avg_score": 0.40,
                },
                "nlf": {
                    "overall": 81.0,
                    "stability": 81.0,
                    "line": None,
                    "angle": None,
                    "ms_per_frame": 665.0,
                },
                "gap": {"overall": -1.0},
            },
        ],
        "summary": {
            "total": 5,
            "passed": 5,
            "verdict": "5/5 STRONG_PASS",
            "line_na_count": 5,
            "angle_na_count": 5,
        },
    }


def _make_stub_spike_report_p10() -> dict:
    """Plan 10 ref-sideway-spin 단일 spike 결과 모사 (overall 72, ms/frame 37).

    Plan 11 sweep ref-sideway-spin (overall 80, ms/frame 21) 와 비교 시
    frames_total 동일 + ms/frame ratio 37/21 ≈ 1.76 (>= 1.5) → gpu_warmup.
    """
    return {
        "generated_at": "2026-06-01T02:23:00+00:00",
        "motion": "ref-sideway-spin",
        "frames_total": 100,
        "detector": "rtmpose-l",
        "rtmpose_config": "/dev/null",
        "rtmpose_checkpoint": "/dev/null",
        "score_threshold": 0.3,
        "image_size": [640, 1136],
        "lifter": {
            "engine": "rtmpose_2d+motionbert",
            "overall": 72.0,
            "dimensions": {
                "stability": 72.0,
                "line": None,
                "angle": None,
            },
            "ms_per_frame": 37.0,
            "avg_rtm_score": 0.4382,
        },
        "nlf": {
            "engine": "nlf",
            "overall": 81.0,
            "dimensions": {"stability": 81.0, "line": None, "angle": None},
            "ms_per_frame": 665.0,
        },
        "gap": {"overall": -9.0, "dimensions": {"stability": -9.0}},
        "verdict": "strong_pass",
    }


# ── 1. CLI 파싱 ───────────────────────────────────────────────────────────────


class TestCliParsing:
    """build_arg_parser defaults + required 검증."""

    def test_mode_default_is_report_only(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--sweep-report", "/tmp/sweep.json"])
        assert args.mode == "report-only"

    def test_sweep_report_required(self):
        parser = build_arg_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_out_default_resolves_to_reports_dir(self):
        # default 가 None 이지만 run_debug 내부의 _default_out_path 가
        # backend/research/spikes/reports/ 로 떨어지는지 확인.
        from backend.research.spikes.debug_gap_root_cause import (
            _default_out_path,
        )

        path = _default_out_path()
        assert path.parent.parts[-3:] == (
            "backend",
            "research",
            "spikes",
        ) or "backend/research/spikes/reports" in str(path)
        assert "debug_gap" in path.name
        assert path.suffix == ".json"


# ── 2. 가설 (c) trace ────────────────────────────────────────────────────────


class TestHypothesisC:
    """sweep JSON 입력 → nlf_overall_range / variance 정확 계산."""

    def test_nlf_overall_range_matches_stub(self):
        stub = _make_stub_sweep_report()
        result = trace_hypothesis_c(stub)
        # stub NLF overall: [58, 63, 64, 65, 81] → min=58, max=81
        assert result["nlf_overall_range"] == [58.0, 81.0]
        assert result["nlf_overall_span"] == 23.0
        # variance > 0 (모든 값이 같지 않음)
        assert result["nlf_overall_variance"] > 0
        assert result["motions_count"] == 5

    def test_verdict_strong_when_range_exceeds_threshold(self):
        # span 23 > HYPOTHESIS_C_STRONG_OVERALL_RANGE (20) → strong
        stub = _make_stub_sweep_report()
        result = trace_hypothesis_c(stub)
        assert result["verdict"] == "strong"


# ── 3. 가설 (d) joint diff ───────────────────────────────────────────────────


class TestHypothesisD:
    """두 chain joint 정의 비교 — H36M vs COCO ordering 차이 검출."""

    def test_returns_diff_rows_with_expected_shape(self):
        result = trace_hypothesis_d()
        rows = result["joint_definition_diff"]
        assert isinstance(rows, list)
        assert len(rows) == 17

        for row in rows:
            assert "idx" in row
            assert "rtmpose_chain" in row
            assert "nlf_chain" in row
            assert "equal" in row
            assert isinstance(row["equal"], bool)

    def test_at_least_one_row_is_different(self):
        # H36M ordering (hip/r_hip/r_knee/...) vs COCO ordering (nose/L_eye/...)
        # 첫 행부터 다름이 보장돼야 함. 만약 모든 행이 동일하면 fail loud.
        result = trace_hypothesis_d()
        rows = result["joint_definition_diff"]
        diff_count = sum(1 for r in rows if not r["equal"])
        assert diff_count >= 1, (
            "두 chain (RTMPose H36M ordering vs NLF COCO ordering) joint 이름이 "
            "byte-for-byte 모두 같다는 결과 — 본 spike 의 전제 (서로 다른 chain) "
            "가 깨졌으므로 import 또는 모듈 ordering 점검 필요. "
            "(rtmpose_to_h36m17.H36M_JOINT_NAMES vs skeleton.KEYPOINT_NAMES)"
        )


# ── 4. spike_vs_sweep verdict ────────────────────────────────────────────────


class TestSpikeVsSweep:
    """3 분기 verdict (gpu_warmup / frame_extractor / both) 검증."""

    def test_gpu_warmup_when_frames_same_msper_differs(self):
        # spike ms/frame 37, sweep ms/frame 21 → ratio 1.76 >= 1.5
        # frames_total 100 == 100 → frames_differ False
        spike = _make_stub_spike_report_p10()
        sweep = _make_stub_sweep_report()
        result = trace_spike_vs_sweep(spike, sweep, motion="ref-sideway-spin")
        assert result["verdict"] == "gpu_warmup"
        assert result["frames_differ"] is False
        assert result["msper_differ"] is True

    def test_frame_extractor_when_frames_differ_msper_similar(self):
        # spike frames=100, sweep frames=200 (frames differ)
        # spike msper=22, sweep msper=21 (ratio ~1.05, < 1.5)
        spike = _make_stub_spike_report_p10()
        spike["frames_total"] = 100
        spike["lifter"]["ms_per_frame"] = 22.0

        sweep = _make_stub_sweep_report()
        # ref-sideway-spin 의 frames 를 200 으로
        for entry in sweep["motions"]:
            if entry["motion"] == "ref-sideway-spin":
                entry["frames_total"] = 200
                entry["rtmpose_mb"]["ms_per_frame"] = 21.0

        result = trace_spike_vs_sweep(spike, sweep, motion="ref-sideway-spin")
        assert result["verdict"] == "frame_extractor"
        assert result["frames_differ"] is True
        assert result["msper_differ"] is False

    def test_both_when_frames_differ_and_msper_differs(self):
        spike = _make_stub_spike_report_p10()
        spike["frames_total"] = 100
        spike["lifter"]["ms_per_frame"] = 37.0

        sweep = _make_stub_sweep_report()
        for entry in sweep["motions"]:
            if entry["motion"] == "ref-sideway-spin":
                entry["frames_total"] = 200
                entry["rtmpose_mb"]["ms_per_frame"] = 21.0

        result = trace_spike_vs_sweep(spike, sweep, motion="ref-sideway-spin")
        assert result["verdict"] == "both"
        assert result["frames_differ"] is True
        assert result["msper_differ"] is True


# ── 5. JSON output shape ─────────────────────────────────────────────────────


class TestJsonShape:
    """report-only run_debug → JSON top-level keys + .md sibling."""

    def test_json_shape_and_md_sibling(self, tmp_path: Path):
        sweep_path = tmp_path / "sweep.json"
        sweep_path.write_text(
            json.dumps(_make_stub_sweep_report()), encoding="utf-8"
        )

        spike_path = tmp_path / "spike.json"
        spike_path.write_text(
            json.dumps(_make_stub_spike_report_p10()), encoding="utf-8"
        )

        out_path = tmp_path / "debug_gap.json"
        result = run_debug(
            sweep_report_path=sweep_path,
            mode="report-only",
            spike_report_path=spike_path,
            out=out_path,
        )

        # top-level
        for key in (
            "generated_at",
            "mode",
            "input",
            "hypotheses",
            "ref_invert_regression",
            "spike_vs_sweep",
            "recommendation",
        ):
            assert key in result, f"top-level key missing: {key}"

        # hypotheses sub-keys
        for k in ("a", "b", "c", "d", "e"):
            assert k in result["hypotheses"], (
                f"hypothesis {k} missing in hypotheses dict"
            )

        # JSON file 도 dump 됐는지 + .md sibling 존재
        assert out_path.exists()
        md_path = out_path.with_suffix(".md")
        assert md_path.exists()

        # JSON 다시 로드 가능
        with open(out_path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["mode"] == "report-only"
        assert "recommendation" in loaded

        md_text = md_path.read_text(encoding="utf-8")
        # 가설별 verdict 요약 표 헤더
        assert "5가설 verdict 요약" in md_text
        # spike_vs_sweep 섹션
        assert "spike vs Plan 11 sweep" in md_text
