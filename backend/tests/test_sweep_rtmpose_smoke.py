"""sweep_rtmpose 5영상 sweep 하네스 smoke 테스트 (Plan 01-11).

mmpose / torch / boto3 의존 없이 로컬 실행. 단일 영상 spike 함수를 stub 로
주입해 sweep 의 iteration + 집계 + JSON 형식만 검증한다.

테스트 범위 (Plan 11 README 명시):
  1. CLI argparse parser default 값 (motions, det-model, score-threshold, bucket)
  2. 5영상 iteration — stub spike_fn 으로 결정적 결과 → verdict 자동 계산
  3. JSON 출력 shape — motions[] / summary / 필수 키 존재
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.research.spikes.sweep_rtmpose import (
    DEFAULT_MOTIONS,
    STRONG_PASS_THRESHOLD,
    build_arg_parser,
    run_sweep,
)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────


def _stub_spike(overall: float, *, line=None, angle=None):
    """run_spike 모양의 stub — 인자 무시하고 고정 overall 반환."""

    def _fn(
        *,
        motion,
        bucket,
        rtmpose_config,
        rtmpose_checkpoint,
        motionbert_root,
        motionbert_weights,
        video_path=None,
        det_model=None,
        score_threshold=0.3,
        out=None,
    ):
        return {
            "generated_at": "2026-06-01T00:00:00+00:00",
            "motion": motion,
            "frames_total": 198,
            "detector": "rtmpose-l",
            "lifter": {
                "engine": "rtmpose_2d+motionbert",
                "overall": overall,
                "dimensions": {
                    "stability": overall,
                    "line": line,
                    "angle": angle,
                },
                "ms_per_frame": 37.0,
                "avg_rtm_score": 0.45,
            },
            "nlf": {
                "engine": "nlf",
                "overall": 80.0,
                "dimensions": {
                    "stability": 80.0,
                    "line": None,
                    "angle": None,
                },
                "ms_per_frame": 665.0,
            },
            "gap": {
                "overall": round(overall - 80.0, 2),
                "dimensions": {"stability": round(overall - 80.0, 2)},
            },
            "verdict": "strong_pass" if overall >= STRONG_PASS_THRESHOLD else "fail",
        }

    return _fn


# ── 1. CLI argparse defaults ─────────────────────────────────────────────────


class TestCliDefaults:
    """build_arg_parser 가 Plan 11 T-1-5 명세대로 default 를 노출하는지 확인."""

    def test_motions_default_is_plan_08_5video_set(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.motions == [
            "ref-climb",
            "ref-foxtop-split",
            "ref-foxtop",
            "ref-invert",
            "ref-sideway-spin",
        ]
        # DEFAULT_MOTIONS 상수와 일치
        assert list(DEFAULT_MOTIONS) == args.motions

    def test_det_model_default_is_none(self):
        # Plan 10 commit f019070 (single-person 우회 default)
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.det_model == "none"

    def test_score_threshold_default_is_0_3(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.score_threshold == 0.3

    def test_bucket_default(self):
        parser = build_arg_parser()
        args = parser.parse_args([])
        assert args.bucket == "sunity-motion-pilot-videos"

    def test_motions_override(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--motions", "ref-invert", "ref-foxtop"])
        assert args.motions == ["ref-invert", "ref-foxtop"]

    def test_det_model_override(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--det-model", "rtmdet-nano"])
        assert args.det_model == "rtmdet-nano"


# ── 2. 5영상 iteration + verdict 자동 계산 ───────────────────────────────────


class TestSweepIteration:
    """spike_fn stub 으로 5영상 iteration + verdict 분기 검증."""

    def test_5_of_5_strong_pass(self, tmp_path: Path):
        out = tmp_path / "sweep.json"
        result = run_sweep(
            motions=list(DEFAULT_MOTIONS),
            bucket="sunity-motion-pilot-videos",
            rtmpose_config="/dev/null",
            rtmpose_checkpoint="/dev/null",
            motionbert_root="/workspace/MotionBERT",
            motionbert_weights="/dev/null",
            score_threshold=0.3,
            det_model="none",
            out=out,
            spike_fn=_stub_spike(overall=80.0),
        )
        assert len(result["motions"]) == 5
        assert result["summary"]["total"] == 5
        assert result["summary"]["passed"] == 5
        assert "5/5 STRONG_PASS" in result["summary"]["verdict"]

        md_text = out.with_suffix(".md").read_text(encoding="utf-8")
        assert "5/5 STRONG_PASS" in md_text or "STRONG_PASS" in md_text

    def test_4_of_5_conditional_pass(self, tmp_path: Path):
        out = tmp_path / "sweep.json"

        # 4영상 80, ref-sideway-spin 64 (Plan 08 MP+MB regression 패턴)
        def _mixed_spike(**kwargs):
            motion = kwargs["motion"]
            if motion == "ref-sideway-spin":
                return _stub_spike(overall=64.0)(**kwargs)
            return _stub_spike(overall=80.0)(**kwargs)

        result = run_sweep(
            motions=list(DEFAULT_MOTIONS),
            bucket="sunity-motion-pilot-videos",
            rtmpose_config="/dev/null",
            rtmpose_checkpoint="/dev/null",
            motionbert_root="/workspace/MotionBERT",
            motionbert_weights="/dev/null",
            out=out,
            spike_fn=_mixed_spike,
        )
        assert result["summary"]["passed"] == 4
        assert "4/5 CONDITIONAL_PASS" in result["summary"]["verdict"]
        md_text = out.with_suffix(".md").read_text(encoding="utf-8")
        assert "CONDITIONAL_PASS" in md_text

    def test_iteration_calls_spike_fn_per_motion(self, tmp_path: Path):
        calls: list[str] = []

        def _track_spike(**kwargs):
            calls.append(kwargs["motion"])
            return _stub_spike(overall=80.0)(**kwargs)

        out = tmp_path / "sweep.json"
        run_sweep(
            motions=["ref-climb", "ref-invert"],
            bucket="sunity-motion-pilot-videos",
            rtmpose_config="/dev/null",
            rtmpose_checkpoint="/dev/null",
            motionbert_root="/workspace/MotionBERT",
            motionbert_weights="/dev/null",
            out=out,
            spike_fn=_track_spike,
        )
        assert calls == ["ref-climb", "ref-invert"]

    def test_empty_motions_raises(self, tmp_path: Path):
        with pytest.raises(ValueError):
            run_sweep(
                motions=[],
                bucket="sunity-motion-pilot-videos",
                rtmpose_config="/dev/null",
                rtmpose_checkpoint="/dev/null",
                motionbert_root="/workspace/MotionBERT",
                motionbert_weights="/dev/null",
                out=tmp_path / "empty.json",
                spike_fn=_stub_spike(overall=80.0),
            )


# ── 3. JSON 출력 shape ────────────────────────────────────────────────────────


class TestJsonShape:
    """dump 된 JSON 의 top-level / motions[] / summary 키 존재 확인."""

    def test_json_shape(self, tmp_path: Path):
        out = tmp_path / "sweep.json"
        run_sweep(
            motions=list(DEFAULT_MOTIONS),
            bucket="sunity-motion-pilot-videos",
            rtmpose_config="/dev/null",
            rtmpose_checkpoint="/dev/null",
            motionbert_root="/workspace/MotionBERT",
            motionbert_weights="/dev/null",
            out=out,
            spike_fn=_stub_spike(overall=80.0),
        )

        with open(out, encoding="utf-8") as f:
            data = json.load(f)

        # top-level
        for key in (
            "generated_at",
            "detector",
            "lifter",
            "score_threshold",
            "det_model",
            "motions",
            "summary",
        ):
            assert key in data, f"top-level key missing: {key}"

        # motions[] entries
        assert isinstance(data["motions"], list)
        assert len(data["motions"]) == 5
        first = data["motions"][0]
        for key in ("motion", "rtmpose_mb", "nlf", "gap"):
            assert key in first, f"motion entry key missing: {key}"

        # rtmpose_mb sub-keys
        for key in ("overall", "stability", "line", "angle", "avg_score", "ms_per_frame"):
            assert key in first["rtmpose_mb"], (
                f"rtmpose_mb sub-key missing: {key}"
            )

        # nlf sub-keys
        for key in ("overall", "stability", "line", "angle", "ms_per_frame"):
            assert key in first["nlf"], f"nlf sub-key missing: {key}"

        # summary
        for key in ("total", "passed", "verdict", "line_na_count", "angle_na_count"):
            assert key in data["summary"], f"summary key missing: {key}"

    def test_md_sibling_created(self, tmp_path: Path):
        out = tmp_path / "sweep.json"
        run_sweep(
            motions=["ref-climb"],
            bucket="sunity-motion-pilot-videos",
            rtmpose_config="/dev/null",
            rtmpose_checkpoint="/dev/null",
            motionbert_root="/workspace/MotionBERT",
            motionbert_weights="/dev/null",
            out=out,
            spike_fn=_stub_spike(overall=80.0),
        )
        assert out.exists()
        md = out.with_suffix(".md")
        assert md.exists()
        text = md.read_text(encoding="utf-8")
        # Plan 11 T-1-3 표 헤더
        assert "RTMPose+MB" in text
        assert "D-15① ≥70" in text
