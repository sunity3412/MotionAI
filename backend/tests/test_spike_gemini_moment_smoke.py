"""spike_gemini_moment 스모크 테스트 (Plan 01-13 T-3).

검증:
  · build_arg_parser — 필수/옵션 인자, default 값.
  · _default_out_path — backend/research/spikes/reports/ 아래 경로.
  · _assert_criteria_present — empty criteria (ref-climb 의도된 빈 list) RuntimeError.
  · report-only mode — Plan 15 ref-invert 1차 박제 데이터로 e2e 검증 (JSON + MD sibling 출력).
  · _evaluate_plan_14_gate — 게이트 verdict 분기 (pass / minimum_fail / below_target / no_criteria).

모든 테스트는 numpy + PyYAML 만 의존 (mmpose / torch / Gemini SDK / boto3 미import).
report-only 는 Plan 15 ref-invert 라벨링 fixture (5 hold entries) 가 디스크에 있으면 실행.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.research.spikes import spike_gemini_moment as spike


# ─────────────────── CLI ───────────────────


class TestCli:
    def test_mode_default_is_report_only(self) -> None:
        parser = spike.build_arg_parser()
        args = parser.parse_args(["--motion", "ref-invert"])
        assert args.mode == "report-only"

    def test_motion_required(self) -> None:
        parser = spike.build_arg_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])  # --motion 없으면 argparse SystemExit

    def test_default_gemini_model(self) -> None:
        parser = spike.build_arg_parser()
        args = parser.parse_args(["--motion", "ref-invert"])
        assert args.gemini_model == "gemini-2.5-pro"

    def test_default_fps(self) -> None:
        parser = spike.build_arg_parser()
        args = parser.parse_args(["--motion", "ref-invert"])
        assert args.fps == spike.DEFAULT_FPS == 9.0


class TestDefaultOutPath:
    def test_default_path_under_reports(self) -> None:
        out = spike._default_out_path()
        assert out.name.startswith("spike_gemini_moment_")
        assert out.suffix == ".json"
        assert out.parent.name == "reports"
        assert out.parent.parent.name == "spikes"


# ─────────────────── empty criteria 가드 ───────────────────


class TestEmptyCriteriaGuard:
    def test_empty_grouped_raises(self) -> None:
        # Plan 15 ref-climb 케이스 시뮬레이션 — 4 phase 모두 빈 list
        from sunity_shared.judging.geometric_criterion import VALID_MOMENT_KEYS

        grouped = {k: [] for k in VALID_MOMENT_KEYS}
        with pytest.raises(RuntimeError, match="Plan 15 IPSF 라벨링 미진입"):
            spike._assert_criteria_present("ref-climb", grouped)

    def test_non_empty_passes(self) -> None:
        from sunity_shared.judging import GeometricCriterion
        from sunity_shared.judging.geometric_criterion import VALID_MOMENT_KEYS

        c = GeometricCriterion(
            motion="ref-invert",
            moment_key="hold",
            joint_key="left_knee",
            angle_target=180.0,
            tolerance_full=20.0,
            deduction_per_step=0.2,
            minimum_requirement=130.0,
            source_ref="IPSF stub",
        )
        grouped = {k: [] for k in VALID_MOMENT_KEYS}
        grouped["hold"] = [c]
        # no raise
        spike._assert_criteria_present("ref-invert", grouped)


# ─────────────────── _evaluate_plan_14_gate ───────────────────


class TestPlan14Gate:
    def test_empty_returns_no_criteria(self) -> None:
        gate = spike._evaluate_plan_14_gate([])
        assert gate["verdict"] == "no_criteria"
        assert gate["total_minimum_failures"] == 0

    def test_full_pass(self) -> None:
        per_moment = [
            {
                "line": 80,
                "angle": 75,
                "minimum_failures": [],
            }
        ]
        gate = spike._evaluate_plan_14_gate(per_moment)
        assert gate["verdict"] == "plan_14_gate_pass"
        assert gate["line_pass"] is True
        assert gate["angle_pass"] is True
        assert gate["minimum_pass"] is True

    def test_minimum_failure_blocks(self) -> None:
        per_moment = [
            {
                "line": 80,
                "angle": 75,
                "minimum_failures": ["left_knee"],
            }
        ]
        gate = spike._evaluate_plan_14_gate(per_moment)
        assert gate["verdict"] == "minimum_requirement_fail"
        assert gate["minimum_pass"] is False

    def test_below_target_score(self) -> None:
        per_moment = [
            {
                "line": 50,  # below 60
                "angle": 75,
                "minimum_failures": [],
            }
        ]
        gate = spike._evaluate_plan_14_gate(per_moment)
        assert gate["verdict"] == "below_target_score"
        assert gate["line_pass"] is False


# ─────────────────── report-only mode (e2e) ───────────────────


@pytest.fixture
def _ref_invert_labeled() -> bool:
    """Plan 15 ref-invert 1차 박제가 디스크에 있는지 확인 (5 hold entries)."""
    try:
        from sunity_shared.judging import load_grouped_criteria

        grouped = load_grouped_criteria("ref-invert")
    except Exception:
        return False
    return any(len(v) > 0 for v in grouped.values())


class TestReportOnlyMode:
    def test_runs_when_labeled(
        self, _ref_invert_labeled: bool, tmp_path: Path
    ) -> None:
        """ref-invert 가 belle 1차 박제됐을 때 report-only e2e 실행 + JSON+MD 출력 sibling 박제."""
        if not _ref_invert_labeled:
            pytest.skip("ref-invert criteria 가 비어있음 — Plan 15 라벨링 진입 후 PASS 예상.")

        # 직접 args 만들어 run_spike 호출 (argparse path 우회)
        import argparse

        out_json = tmp_path / "out.json"
        args = argparse.Namespace(
            mode="report-only",
            motion="ref-invert",
            bucket="dummy",
            gemini_model="gemini-2.5-pro",
            rtmpose_config=None,
            rtmpose_checkpoint=None,
            motionbert_root=None,
            motionbert_weights=None,
            score_threshold=0.3,
            fps=9.0,
            out=str(out_json),
        )
        result = spike.run_spike(args)

        # JSON 파일 + MD sibling 둘 다 존재
        assert out_json.exists()
        out_md = out_json.with_suffix(".md")
        assert out_md.exists()

        # 결과 정합
        assert result["mode"] == "report-only"
        assert result["motion"] == "ref-invert"
        assert "gate" in result
        assert "moments" in result
        # 1 moment (hold) 분석되어야 함 (ref-invert 1차 박제는 hold 만)
        hold_moments = [m for m in result["moments"] if m["moment_key"] == "hold"]
        assert len(hold_moments) == 1
        # 기대 개수는 yaml 에서 유도한다 — 숫자를 박으면 criteria 가 늘 때마다 낡는다
        # (2026-08-28: ref-invert hold 가 5 → 6 으로 늘었는데 테스트만 5 로 남아 실패).
        import yaml as _yaml

        _yaml_path = (
            Path(__file__).resolve().parents[1]
            / "judging_data" / "criteria" / "ref-invert.yaml"
        )
        _expected = len(
            _yaml.safe_load(_yaml_path.read_text(encoding="utf-8"))["criteria"]["hold_moment"]
        )
        assert hold_moments[0]["criteria_count"] == _expected
        assert len(hold_moments[0]["per_joint"]) == _expected
        # JSON-deserialize round-trip
        loaded = json.loads(out_json.read_text(encoding="utf-8"))
        assert loaded["motion"] == "ref-invert"

    def test_ref_climb_empty_criteria_raises(self, tmp_path: Path) -> None:
        """ref-climb 의도된 빈 list — run_spike 호출 시 명확한 RuntimeError."""
        import argparse

        args = argparse.Namespace(
            mode="report-only",
            motion="ref-climb",
            bucket="dummy",
            gemini_model="gemini-2.5-pro",
            rtmpose_config=None,
            rtmpose_checkpoint=None,
            motionbert_root=None,
            motionbert_weights=None,
            score_threshold=0.3,
            fps=9.0,
            out=str(tmp_path / "out.json"),
        )
        with pytest.raises(RuntimeError, match="Plan 15 IPSF 라벨링 미진입"):
            spike.run_spike(args)


# ─────────────────── live mode 가드 ───────────────────


class TestLiveModeGuards:
    def test_live_missing_rtmpose_config_raises(self, tmp_path: Path) -> None:
        import argparse

        args = argparse.Namespace(
            mode="live",
            motion="ref-invert",
            bucket="dummy",
            gemini_model="gemini-2.5-pro",
            rtmpose_config=None,  # 누락
            rtmpose_checkpoint=None,
            motionbert_root=None,
            motionbert_weights="x",
            score_threshold=0.3,
            fps=9.0,
            out=str(tmp_path / "out.json"),
        )
        with pytest.raises(RuntimeError, match="rtmpose-config"):
            spike._run_live(args)

    def test_live_missing_motionbert_weights_raises(self, tmp_path: Path) -> None:
        import argparse

        args = argparse.Namespace(
            mode="live",
            motion="ref-invert",
            bucket="dummy",
            gemini_model="gemini-2.5-pro",
            rtmpose_config="x",
            rtmpose_checkpoint="y",
            motionbert_root="/workspace/MotionBERT",
            motionbert_weights=None,  # 누락
            score_threshold=0.3,
            fps=9.0,
            out=str(tmp_path / "out.json"),
        )
        with pytest.raises(RuntimeError, match="motionbert-weights"):
            spike._run_live(args)
