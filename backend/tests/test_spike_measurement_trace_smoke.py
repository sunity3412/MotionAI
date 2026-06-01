"""spike_measurement_trace 스모크 테스트 (Plan 01-16 T-4).

검증 (mmpose / torch / mediapipe 미import — 로컬 실행 OK):
  - build_arg_parser: CLI default 값 (mode / motion / frame_index / hold_window)
  - _default_out_path: backend/research/spikes/reports/ 아래 + UTC ISO 8601 형식
  - report-only mode end-to-end: stub angles → JSON shape + sibling .md
  - 4 가설 verdict 분기 (stub angles 로 dominant 강제)
  - live mode guards: rtmpose-config 누락 시 ValueError
  - live helper 시그너처 통합 검증: spike_rtmpose / spike_motionbert /
    mediapipe_to_h36m17 의 호출 함수 존재 (Plan 13 belle Pod 발견 차단).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from backend.research.spikes import spike_measurement_trace as trace


# ─────────────────── TestCli ───────────────────


class TestCli:
    def test_mode_default_is_report_only(self) -> None:
        parser = trace.build_arg_parser()
        args = parser.parse_args([])
        assert args.mode == "report-only"

    def test_motion_default(self) -> None:
        parser = trace.build_arg_parser()
        args = parser.parse_args([])
        assert args.motion == trace.DEFAULT_MOTION == "ref-invert"

    def test_frame_index_default(self) -> None:
        parser = trace.build_arg_parser()
        args = parser.parse_args([])
        assert args.frame_index == trace.PLAN_13_FRAME_INDEX == 88

    def test_hold_window_default(self) -> None:
        parser = trace.build_arg_parser()
        args = parser.parse_args([])
        assert args.hold_window == trace.PLAN_13_HOLD_WINDOW == 5


# ─────────────────── TestDefaultOutPath ───────────────────


class TestDefaultOutPath:
    def test_default_path_under_reports(self) -> None:
        out = trace._default_out_path()
        assert out.name.startswith("spike_measurement_trace_")
        assert out.suffix == ".json"
        assert out.parent.name == "reports"
        assert out.parent.parent.name == "spikes"
        # UTC ISO 8601: <prefix>_20260601T123456Z.json
        stem = out.stem
        assert stem.endswith("Z"), f"stem {stem} should end with Z (UTC)"


# ─────────────────── TestReportOnlyMode ───────────────────


class TestReportOnlyMode:
    def test_json_top_level_keys(self, tmp_path: Path) -> None:
        """stub fixture → JSON top-level keys 9개."""
        out = tmp_path / "report.json"
        parser = trace.build_arg_parser()
        args = parser.parse_args(["--out", str(out)])
        rc = trace.main_with_args(args) if hasattr(trace, "main_with_args") else None
        # main_with_args 미존재 시 sys.argv override 로 main 호출
        if rc is None:
            import sys
            saved = sys.argv[:]
            try:
                sys.argv = [
                    "prog",
                    "--mode",
                    "report-only",
                    "--motion",
                    "ref-invert",
                    "--out",
                    str(out),
                ]
                trace.main()
            finally:
                sys.argv = saved

        assert out.exists()
        with open(out, encoding="utf-8") as f:
            d = json.load(f)
        # 필수 top-level keys (PLAN 16 T-4 acceptance)
        for k in (
            "generated_at",
            "mode",
            "motion",
            "frame_index",
            "hold_window",
            "engines",
            "cross_engine",
            "verdicts",
            "baseline_inconsistency",
        ):
            assert k in d, f"missing top-level key: {k}"
        # engines 안에 두 엔진 모두
        assert trace.ENGINE_RTMPOSE_MB in d["engines"]
        assert trace.ENGINE_MEDIAPIPE_MB in d["engines"]

    def test_sibling_md_created(self, tmp_path: Path) -> None:
        out = tmp_path / "report.json"
        import sys

        saved = sys.argv[:]
        try:
            sys.argv = [
                "prog",
                "--mode",
                "report-only",
                "--motion",
                "ref-invert",
                "--out",
                str(out),
            ]
            trace.main()
        finally:
            sys.argv = saved

        md = out.with_suffix(".md")
        assert md.exists(), f"sibling .md 미생성: {md}"
        md_text = md.read_text(encoding="utf-8")
        # 9 섹션 모두 존재
        for section in (
            "# Spike: Measurement Trace",
            "## (2) RTMPose+MB trace",
            "## (3) MP+MB trace",
            "## (4) 좌우 비대칭",
            "## (5) Cross-engine disagreement",
            "## (6) 좌우 swap detection",
            "## (7) 4 가설 verdict 매트릭스",
            "## (8) next_path_recommendation",
            "## (9) Plan 08 / Plan 11 / Plan 13",
        ):
            assert section in md_text, f"섹션 누락: {section}"
        # multi-view 키워드 0건 (memory filename 인용 제외)
        non_memory_lines = [
            line for line in md_text.splitlines() if "single-camera-first-multi-view-last" not in line
        ]
        for line in non_memory_lines:
            for k in ("multi-view", "multi camera", "다각도"):
                assert k not in line, f"금지 키워드 발견: {k} in {line}"


# ─────────────────── TestVerdictBranches ───────────────────


class TestVerdictBranches:
    def test_dominant_a_branch_path_d_or_b_light(self) -> None:
        """가설 (a) 만 dominant → next_path_recommendation 에 'path D 조기' 또는 'window 평균'."""
        ta, tb, tc, td = (
            {"mean_disagreement_deg": 35.0},
            {"overall_mean_abs_lr_deg": 5.0},
            {"swap_frame_ratio": 0.05},
            {"overall_mean_disagreement_deg": 5.0},
        )
        out = trace.aggregate_verdicts(ta, tb, tc, td)
        assert out["dominant"] == ["a"]
        assert "path D" in out["next_path_recommendation"] or "window 평균" in out["next_path_recommendation"]

    def test_dominant_b_branch_path_b(self) -> None:
        ta, tb, tc, td = (
            {"mean_disagreement_deg": 5.0},
            {"overall_mean_abs_lr_deg": 50.0},
            {"swap_frame_ratio": 0.05},
            {"overall_mean_disagreement_deg": 5.0},
        )
        out = trace.aggregate_verdicts(ta, tb, tc, td)
        assert out["dominant"] == ["b"]
        assert "path B" in out["next_path_recommendation"]

    def test_all_rejected_branch_path_d_formal(self) -> None:
        ta, tb, tc, td = (
            {"mean_disagreement_deg": 5.0},
            {"overall_mean_abs_lr_deg": 5.0},
            {"swap_frame_ratio": 0.05},
            {"overall_mean_disagreement_deg": 5.0},
        )
        out = trace.aggregate_verdicts(ta, tb, tc, td)
        assert out["dominant"] == []
        assert "path D 정식 진입" in out["next_path_recommendation"]


# ─────────────────── TestLiveModeGuards ───────────────────


class TestLiveModeGuards:
    def test_live_mode_missing_rtmpose_config(self) -> None:
        """live mode + rtmpose-config 누락 → ValueError."""
        parser = trace.build_arg_parser()
        args = parser.parse_args(
            [
                "--mode",
                "live",
                "--motion",
                "ref-invert",
                # rtmpose-config / rtmpose-checkpoint 누락
            ]
        )
        with pytest.raises(ValueError, match="rtmpose-config"):
            trace.run_trace(args)


# ─────────────────── TestLiveHelperSignatures ───────────────────


class TestLiveHelperSignatures:
    """Plan 13 belle Pod 발견 (joint_uncertainty import / _run_rtmpose_2d kwargs /
    SDK / File API ACTIVE) 같은 시그너처 불일치 차단.

    본 테스트는 mmpose / torch / mediapipe 없이 ast 정합만 점검 — 로컬 OK.
    """

    def test_all_required_functions_exist(self) -> None:
        found = trace.assert_live_helper_signatures()
        # 4 모듈 모두 발견
        assert "spike_rtmpose" in found
        assert "rtmpose_to_h36m17" in found
        assert "mediapipe_to_h36m17" in found
        assert "spike_motionbert" in found
        # 본 spike 가 호출하는 모든 함수 박제
        assert "_run_rtmpose_2d" in found["spike_rtmpose"]
        assert "_load_motionbert" in found["spike_rtmpose"]
        assert "_run_motionbert_inference" in found["spike_rtmpose"]
        assert "_h36m17_to_coco17_subset" in found["spike_rtmpose"]
        assert "_resolve_video" in found["spike_rtmpose"]
        assert "_extract_frames" in found["spike_rtmpose"]
        assert "convert_rtmpose_coco17_to_h36m17" in found["rtmpose_to_h36m17"]
        assert "convert_mp33_to_h36m17" in found["mediapipe_to_h36m17"]
        assert "h36m17_to_coco17_subset" in found["mediapipe_to_h36m17"]
        assert "_run_mediapipe_2d" in found["spike_motionbert"]
