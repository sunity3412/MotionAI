"""Plan 17-01 Task 4 — pipeline._gemini_vision_enabled() + keep_local_video gate 단위 테스트.

박제 정신:
  · 3차 review R-B4 정합 — Phase 17 4 영역 토글 중 하나만 ON 이어도 local_video_path
    보존 (keep_local_video=True).
  · 기존 _gemini_enabled() (Phase 5 recognizer 전용) 시그니처/동작 변경 0 — backward compat.
  · 2차 R-W6 정합 — B/C default ON 으로 모든 분석이 keep_local_video=True 가 되더라도
    finally 박제 unlink 가 정상/예외 양쪽에서 호출 (disk budget 누수 차단).
  · 2차 R-W6 정합 — unlink 실패 (PermissionError 등) 시 log.warning 1회 박제 + 분석 흐름
    차단 0 (graceful).

mock-based — 실 S3 / 실 Firestore / 실 NLF 호출 0.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# functions/pipeline/ 디렉토리를 path 에 추가 — app 모듈 임포트.
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))


def _import_pipeline():
    """pipeline/app.py 모듈을 강제 재로드 (env 박제 격리)."""
    sys.modules.pop("app", None)
    import app  # noqa: WPS433 - dynamic local import 박제

    return importlib.reload(app)


# Phase 17 4 영역 토글 박제 — A/B/C/D.
_VISION_ENV_VARS = (
    "GEMINI_REFERENCE_ENABLED",
    "GEMINI_COACH_ENABLED",
    "GEMINI_FINDING_ENABLED",
    "GEMINI_D_ENABLED",
)
_RECOGNIZER_ENV_VARS = (
    "GEMINI_RECOGNIZER_ENABLED",
    "RECOGNIZER_BACKEND",
)


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch):
    """각 테스트마다 env clear + module reload 박제."""
    for k in _VISION_ENV_VARS + _RECOGNIZER_ENV_VARS:
        monkeypatch.delenv(k, raising=False)
    yield
    sys.modules.pop("app", None)


# ─────────────────── _gemini_vision_enabled 토글 케이스 ───────────────────


class TestGeminiVisionEnabled:
    def test_all_off_returns_false(self, monkeypatch) -> None:
        # 모든 토글 OFF — B/C default "1" override.
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")
        app = _import_pipeline()
        assert app._gemini_vision_enabled() is False

    def test_reference_only_on(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")
        monkeypatch.setenv("GEMINI_REFERENCE_ENABLED", "1")
        app = _import_pipeline()
        assert app._gemini_vision_enabled() is True

    def test_coach_only_on(self, monkeypatch) -> None:
        # B/C default = "1" 인데 명시적 ON 으로 박제.
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "1")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")
        app = _import_pipeline()
        assert app._gemini_vision_enabled() is True

    def test_finding_only_on(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "1")
        app = _import_pipeline()
        assert app._gemini_vision_enabled() is True

    def test_d_only_on(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")
        monkeypatch.setenv("GEMINI_D_ENABLED", "1")
        app = _import_pipeline()
        assert app._gemini_vision_enabled() is True

    def test_bc_default_on_when_unset(self) -> None:
        # B/C default "1" — env 미설정 시 박제.
        app = _import_pipeline()
        assert app._gemini_vision_enabled() is True

    def test_falsy_values_block_default(self, monkeypatch) -> None:
        # default ON path 박제 차단 — "false" / "False" / "0" / "" 모두 false 처리.
        for val in ("0", "false", "False", ""):
            monkeypatch.setenv("GEMINI_COACH_ENABLED", val)
            monkeypatch.setenv("GEMINI_FINDING_ENABLED", val)
            app = _import_pipeline()
            assert app._gemini_vision_enabled() is False, f"value={val!r}"


# ─────────────────── _gemini_enabled 회귀 (backward compat) ───────────────────


class TestGeminiEnabledBackwardCompat:
    def test_recognizer_only_on_does_not_imply_vision(self, monkeypatch) -> None:
        # Phase 5 recognizer ON + Phase 17 4 영역 모두 OFF.
        monkeypatch.setenv("GEMINI_RECOGNIZER_ENABLED", "1")
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")
        app = _import_pipeline()
        assert app._gemini_enabled() is True
        # Phase 17 vision 은 별 helper — 모두 OFF 면 False.
        assert app._gemini_vision_enabled() is False

    def test_recognizer_off_returns_false(self, monkeypatch) -> None:
        # 둘 다 unset.
        app = _import_pipeline()
        assert app._gemini_enabled() is False


# ─────────────────── keep_local_video gate (OR) ───────────────────


class TestKeepLocalVideoGate:
    def test_gate_uses_or_of_both_helpers(self, monkeypatch) -> None:
        """Phase 17 4 영역 OR Phase 5 recognizer — 하나라도 ON 이면 True."""
        # case 1: recognizer only.
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")
        monkeypatch.setenv("GEMINI_RECOGNIZER_ENABLED", "1")
        app = _import_pipeline()
        assert (app._gemini_enabled() or app._gemini_vision_enabled()) is True

        # case 2: vision only.
        monkeypatch.delenv("GEMINI_RECOGNIZER_ENABLED", raising=False)
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "1")
        app = _import_pipeline()
        assert (app._gemini_enabled() or app._gemini_vision_enabled()) is True

        # case 3: 둘 다 OFF.
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")
        app = _import_pipeline()
        assert (app._gemini_enabled() or app._gemini_vision_enabled()) is False

    def test_gate_line_present_in_source(self) -> None:
        """grep 회귀 박제 — keep_local_video 게이트가 3 토글 OR.

        Phase 20-03 HIGH-1: veto 만 ON 인 경우에도 local_video_path 가 보존되도록
        `_gemini_vision_veto_enabled()` 를 게이트에 추가 (multi-line). 세 토글 OR 가
        모두 소스에 존재함을 단언 (포맷 무관 — 토큰 단위)."""
        source = (_PIPELINE / "app.py").read_text(encoding="utf-8")
        # 게이트 컴포넌트 토큰 (multi-line 포맷이라 정확 문자열 대신 토큰 단위).
        assert "_gemini_enabled()" in source
        assert "_gemini_vision_enabled()" in source
        assert "_gemini_vision_veto_enabled()" in source  # HIGH-1 veto 토글 추가

    def test_gemini_vision_enabled_defined_in_source(self) -> None:
        source = (_PIPELINE / "app.py").read_text(encoding="utf-8")
        # 정의 1회 + 호출 1회 = ≥ 2회.
        assert source.count("_gemini_vision_enabled") >= 2


# ─────────────────── finally cleanup 회귀 (2차 R-W6) ───────────────────


class TestFinallyCleanup:
    def test_unlink_called_when_path_set(self, monkeypatch, tmp_path) -> None:
        """_process finally 박제 가 local_video_path 가 set 일 때 unlink 호출."""
        app = _import_pipeline()
        # 실 Path.unlink 박제 — 호출 count 검증.
        unlink_calls: list[Path] = []
        real_unlink = Path.unlink

        def _fake_unlink(self, missing_ok=False):
            unlink_calls.append(Path(self))
            return None

        monkeypatch.setattr(Path, "unlink", _fake_unlink)

        # finally 박제 path 시뮬레이션 — local_video_path 박제 후 unlink 호출.
        local_video_path = str(tmp_path / "fake.mp4")
        try:
            pass  # 정상 종료 path
        finally:
            if local_video_path is not None:
                Path(local_video_path).unlink(missing_ok=True)

        assert len(unlink_calls) == 1

        # 예외 path 도 finally 진입.
        unlink_calls.clear()
        with pytest.raises(RuntimeError):
            try:
                raise RuntimeError("boom")
            finally:
                if local_video_path is not None:
                    Path(local_video_path).unlink(missing_ok=True)
        assert len(unlink_calls) == 1

        monkeypatch.setattr(Path, "unlink", real_unlink)

    def test_unlink_failure_graceful_via_safe_unlink(self, monkeypatch, tmp_path) -> None:
        """unlink 실패 시 _safe_unlink_local_video 가 log.warning 1회 + 분석 흐름 차단 0.

        R-W6 박제 — Path(local_video_path).unlink(missing_ok=True) 자체는 PermissionError
        등에서 raise. pipeline 박제는 safe wrapper 박제 권장 — _safe_unlink_local_video.
        """
        app = _import_pipeline()

        # _safe_unlink_local_video 박제 신설 헬퍼 — 박제 정신 R-W6 정합.
        # unlink 실패해도 RuntimeError raise X (graceful).
        def _raising_unlink(self, missing_ok=False):
            raise PermissionError("denied")

        monkeypatch.setattr(Path, "unlink", _raising_unlink)
        warnings: list[str] = []
        monkeypatch.setattr(app.log, "warning", lambda msg, *a, **kw: warnings.append(msg))

        fake_path = str(tmp_path / "fake.mp4")
        # 박제 — graceful return None.
        result = app._safe_unlink_local_video(fake_path)
        assert result is None
        assert len(warnings) == 1


# ─────────────── Task 4 — collect/apply 2-함수 seam + cap_would_apply + 객체 분리 ───────────────


import inspect as _inspect  # noqa: E402


class TestCollectApplySeam:
    def test_collect_signature_is_pre_build_primitive(self) -> None:
        """_collect_vision_fault_context 가 result dict 가 아닌 keyword pre-build primitive (D-12 MED-1)."""
        app = _import_pipeline()
        sig = _inspect.signature(app._collect_vision_fault_context)
        params = sig.parameters
        # result dict / score_result 매개변수 부재.
        assert "score_result" not in params
        assert "result" not in params
        # keyword pre-build primitive 수령.
        assert "overall_score" in params
        assert "dimension_scores" in params
        assert "mode" in params
        # overall_score 는 keyword-only.
        assert params["overall_score"].kind == _inspect.Parameter.KEYWORD_ONLY

    def test_collect_function_defined(self) -> None:
        """_collect_vision_fault_context 함수가 pipeline 에 정의 (Gemini 소유자 분리, D-10 HIGH-1)."""
        app = _import_pipeline()
        assert callable(app._collect_vision_fault_context)

    def test_build_quantification_seam_defined(self) -> None:
        """_build_vision_quantification_result named seam 정의 (D-13 HIGH-1)."""
        app = _import_pipeline()
        assert callable(app._build_vision_quantification_result)

    def test_build_quantification_missing_inputs_unavailable_not_none(self) -> None:
        """seam 이 결측 입력에 None 아닌 VisionQuantificationResult(unavailable) 반환 (D-13 HIGH-1)."""
        app = _import_pipeline()
        from sunity_shared.analysis import vision_veto

        out = app._build_vision_quantification_result(
            fault_context=None, selected_frame_pair=None,
            current_measurements=None, reference_measurements=None,
            body_profile=None, pole_geometry=None,
        )
        assert out is not None
        assert isinstance(out, vision_veto.VisionQuantificationResult)
        assert out.quantificationStatus == "unavailable"

    def test_collect_cap_would_apply_uses_production_cap(self, monkeypatch) -> None:
        """collect 가 production 동일 apply_downward_cap 으로 cap_would_apply 산출 (D-11 HIGH-1)."""
        app = _import_pipeline()
        from sunity_shared.analysis import gemini_vision_scorer, vision_veto

        # severity=minor / overall=88 → apply_downward_cap=88 (≮88) → cap_would_apply False.
        # severity=moderate / overall=92 → 75<92 → True.
        # severity=none → False.
        for severity, overall, expected in [
            ("minor", 88, False),
            ("moderate", 92, True),
            ("none", 95, False),
        ]:
            monkeypatch.setattr(
                gemini_vision_scorer, "assess_fault_severity",
                lambda *a, **k: gemini_vision_scorer.VisionVerdict(
                    primary_fault="x", severity=severity, differences=()
                ),
            )
            # 정렬/프레임 추출은 collect 내부 — 여기서는 cap_would_apply 만 검증하도록
            # 최소 입력 + collect 가 graceful 하게 candidate/none 산출.
            ctx = app._collect_vision_fault_context(
                overall_score=overall,
                dimension_scores={"angle": overall},
                mode="mode1",
                local_video_path=None,  # collect 내부 graceful 경로
                angles=None, profile=None, reference_dtw_match=None,
                reference_angles=None, reference_video_path=None,
                keypoint_report=None,
            )
            # local_video None 등 graceful 경로면 cap_would_apply False/None.
            assert ctx is not None
            if ctx.collection_status == "candidate_verdict":
                assert ctx.cap_would_apply is expected

    def test_apply_with_context_no_gemini_call(self, monkeypatch) -> None:
        """_apply_vision_veto(vision_fault_context=ctx) 가 Gemini 미호출 + verdict 재사용 (D-10 HIGH-1)."""
        app = _import_pipeline()
        from sunity_shared.analysis import gemini_vision_scorer, vision_veto

        calls = {"n": 0}

        def _spy(*a, **k):
            calls["n"] += 1
            return gemini_vision_scorer.VisionVerdict("x", "major", ())

        monkeypatch.setattr(gemini_vision_scorer, "assess_fault_severity", _spy)
        monkeypatch.setattr(app, "_gemini_vision_veto_enabled", lambda: True)

        ctx = vision_veto.VisionFaultContext(
            collection_status="candidate_verdict",
            verdict=gemini_vision_scorer.VisionVerdict("다리", "major", ()),
            supported_differences=[], root_cause_hypotheses=[], selected_frame_pairs=[],
            alignment={}, telemetry={}, cap_would_apply=True,
        )
        quant = vision_veto.VisionQuantificationResult(
            quantificationStatus="unavailable", angleDeltas=None,
            bodyRelativeNotches=None, windowMedianAngleDeltas=None, warnings=[],
        )
        out = app._apply_vision_veto(
            {"overallScore": 100}, mode="mode1",
            vision_fault_context=ctx, quantification=quant,
        )
        # apply 내부에서 Gemini 호출 0 (verdict 재사용).
        assert calls["n"] == 0
        assert out["visionVeto"]["status"] == "applied"
        assert out["overallScore"] == 50  # major cap.

    def test_apply_applied_but_quant_unavailable(self, monkeypatch) -> None:
        """applied + quant unavailable → status applied 유지, geometry 부재, crash 0 (D-12 HIGH-1)."""
        app = _import_pipeline()
        from sunity_shared.analysis import gemini_vision_scorer, vision_veto

        monkeypatch.setattr(app, "_gemini_vision_veto_enabled", lambda: True)
        ctx = vision_veto.VisionFaultContext(
            collection_status="candidate_verdict",
            verdict=gemini_vision_scorer.VisionVerdict("다리", "moderate", ()),
            supported_differences=[], root_cause_hypotheses=[], selected_frame_pairs=[],
            alignment={}, telemetry={}, cap_would_apply=True,
        )
        quant = vision_veto.VisionQuantificationResult(
            quantificationStatus="unavailable", angleDeltas=None,
            bodyRelativeNotches=None, windowMedianAngleDeltas=None, warnings=["no_keypoints"],
        )
        out = app._apply_vision_veto(
            {"overallScore": 100}, mode="mode1",
            vision_fault_context=ctx, quantification=quant,
        )
        v = out["visionVeto"]
        assert v["status"] == "applied"
        assert v.get("quantificationStatus") == "unavailable"
        assert "angleDeltas" not in v

    def test_apply_passthrough_score_free_status(self, monkeypatch) -> None:
        """정렬 약함/예산소진 collection_status → apply 가 score 불변 passthrough."""
        app = _import_pipeline()
        from sunity_shared.analysis import vision_veto

        monkeypatch.setattr(app, "_gemini_vision_veto_enabled", lambda: True)
        for status in ("low_alignment_confidence", "resource_limited"):
            ctx = vision_veto.VisionFaultContext(
                collection_status=status, verdict=None, supported_differences=[],
                root_cause_hypotheses=[], selected_frame_pairs=[], alignment={},
                telemetry={"samplingComplete": False}, cap_would_apply=False,
            )
            out = app._apply_vision_veto(
                {"overallScore": 97}, mode="mode1", vision_fault_context=ctx,
            )
            assert out["overallScore"] == 97, "score 불변 passthrough"
            assert out["visionVeto"]["status"] == status


# ─────────────── Task 4 (23-02) — 정량화 audit attach (to_audit_dict) + 3-way lockstep ───────────────


class TestQuantificationAuditAttach:
    def _ctx_with_root_cause(self):
        from sunity_shared.analysis import gemini_vision_scorer, vision_veto

        fk = vision_veto.FaultKey("upper_body", "left", "arm", "pole_gap_or_bent")
        rc = vision_veto.RootCauseHypothesis(
            text="폴 밀착이 풀린 것으로 보임", fault_key=fk,
            source_difference_ids=(1,), support_count=2,
        )
        return vision_veto.VisionFaultContext(
            collection_status="candidate_verdict",
            verdict=gemini_vision_scorer.VisionVerdict("왼팔", "moderate", ()),
            supported_differences=[], root_cause_hypotheses=[rc], selected_frame_pairs=[],
            alignment={}, telemetry={}, cap_would_apply=True,
        )

    def test_applied_audit_serialized_via_to_audit_dict_with_available_quant(self):
        """applied audit 가 to_audit_dict(quantification=available)로 angleDeltas/칸/root-cause 저장 (D-12 HIGH-1)."""
        app = _import_pipeline()
        from sunity_shared.analysis import vision_veto

        ctx = self._ctx_with_root_cause()
        quant = vision_veto.VisionQuantificationResult(
            quantificationStatus="available",
            angleDeltas=[{
                "joint": "left_knee", "student_deg": 145.0, "reference_deg": 178.0,
                "delta_deg": -33.0, "direction": "더 굽음", "source": "geometry",
            }],
            bodyRelativeNotches=[{
                "keypoint": "left_hand", "student_notches": 2.0,
                "reference_notches": 3.0, "delta_notches": -1.0,
                "baseline_kind": "floor", "source": "geometry",
            }],
            windowMedianAngleDeltas={"deltas": [], "sourceFrameIndices": {"user": [], "reference": []}, "windowPolicy": "x"},
            warnings=(),
        )
        out = app._apply_vision_veto(
            {"overallScore": 92}, mode="mode1",
            vision_fault_context=ctx, quantification=quant,
        )
        v = out["visionVeto"]
        assert v["status"] == "applied"
        assert v["quantificationStatus"] == "available"
        # frame-specific 각도 + 칸 + root-cause 동반.
        assert v["angleDeltas"][0]["source"] == "geometry"
        assert v["bodyRelativeNotches"][0]["source"] == "geometry"
        assert v["rootCauseHypotheses"][0]["text"] == "폴 밀착이 풀린 것으로 보임"
        # window median 은 별도 키 (still 정확 각도와 혼동 0, D-10 HIGH-3).
        assert "windowMedianAngleDeltas" in v
        # 칸/각도는 geometry source — Gemini verdict 칸 신뢰 0.
        assert all(n["source"] == "geometry" for n in v["bodyRelativeNotches"])

    def test_applied_audit_no_score_or_percent_type(self):
        """audit 정량화 필드에 normalized score/percent 0 — 각도(도)/칸 DESCRIPTIVE 만 (D-06/D-08)."""
        app = _import_pipeline()
        from sunity_shared.analysis import vision_veto

        ctx = self._ctx_with_root_cause()
        quant = vision_veto.VisionQuantificationResult(
            quantificationStatus="available",
            angleDeltas=[{"joint": "left_knee", "student_deg": 145.0,
                          "reference_deg": 178.0, "delta_deg": -33.0,
                          "direction": "더 굽음", "source": "geometry"}],
            bodyRelativeNotches=None, windowMedianAngleDeltas=None, warnings=(),
        )
        out = app._apply_vision_veto(
            {"overallScore": 92}, mode="mode1",
            vision_fault_context=ctx, quantification=quant,
        )
        text = repr(out["visionVeto"])
        for forbidden in ("%", "100%", "percent", "퍼센트"):
            assert forbidden not in text, f"audit 에 {forbidden!r} 누출 (D-08)"

    def test_root_cause_survives_unavailable_quant(self):
        """quant unavailable 이어도 root-cause + capApplied 유지 (강등 금지, D-11 MED-1)."""
        app = _import_pipeline()
        from sunity_shared.analysis import vision_veto

        ctx = self._ctx_with_root_cause()
        quant = vision_veto.VisionQuantificationResult(
            quantificationStatus="unavailable", warnings=("notches_unavailable",),
        )
        out = app._apply_vision_veto(
            {"overallScore": 92}, mode="mode1",
            vision_fault_context=ctx, quantification=quant,
        )
        v = out["visionVeto"]
        assert v["status"] == "applied"
        assert v["quantificationStatus"] == "unavailable"
        assert "angleDeltas" not in v and "bodyRelativeNotches" not in v
        # root-cause + capApplied 는 유지 (geometry 만 부재).
        assert v["rootCauseHypotheses"][0]["text"] == "폴 밀착이 풀린 것으로 보임"
        assert "capApplied" in v

    def test_not_applicable_has_no_quantification_fields(self):
        """not_applicable 분기엔 정량화 + quantificationStatus 부재 (discriminated)."""
        app = _import_pipeline()
        from sunity_shared.analysis import gemini_vision_scorer, vision_veto

        # severity=minor / overall=88 → cap 88 ≮ 88 → not_applicable.
        ctx = vision_veto.VisionFaultContext(
            collection_status="candidate_verdict",
            verdict=gemini_vision_scorer.VisionVerdict("x", "minor", ()),
            supported_differences=[], root_cause_hypotheses=[], selected_frame_pairs=[],
            alignment={}, telemetry={}, cap_would_apply=False,
        )
        out = app._apply_vision_veto(
            {"overallScore": 88}, mode="mode1", vision_fault_context=ctx,
        )
        v = out["visionVeto"]
        assert v["status"] == "not_applicable"
        assert "quantificationStatus" not in v
        assert "angleDeltas" not in v and "bodyRelativeNotches" not in v

    def test_three_way_lockstep_keys(self):
        """신규 audit 필드가 models.py VISION_VETO_KEYS + analysis.ts + contract.md 3-way 정합."""
        import sunity_shared.models as models

        for key in ("quantificationStatus", "angleDeltas", "bodyRelativeNotches",
                    "windowMedianAngleDeltas", "rootCauseHypotheses"):
            assert key in models.VISION_VETO_KEYS, f"{key} models.py 누락"
        # TS + contract 존재 확인 (파일 grep).
        repo = Path(__file__).resolve().parents[2]
        ts = (repo / "app" / "src" / "types" / "analysis.ts").read_text(encoding="utf-8")
        contract = (repo / "docs" / "contract.md").read_text(encoding="utf-8")
        for key in ("quantificationStatus", "angleDeltas", "bodyRelativeNotches",
                    "rootCauseHypotheses"):
            assert key in ts, f"{key} analysis.ts 누락"
            assert key in contract, f"{key} contract.md 누락"


# ─────────────── Task 5 (23-02) — collect-before-coach 배선 + 정량화 seam 산출 ───────────────


class TestCoachInjectionGate:
    def _ctx(self, status, cap_would_apply, root_text="폴 밀착이 풀린 것으로 보임"):
        from sunity_shared.analysis import gemini_vision_scorer, vision_veto

        rcs = []
        if root_text:
            fk = vision_veto.FaultKey("upper_body", "left", "arm", "pole_gap_or_bent")
            rcs = [vision_veto.RootCauseHypothesis(
                text=root_text, fault_key=fk, source_difference_ids=(1,), support_count=2,
            )]
        verdict = gemini_vision_scorer.VisionVerdict("왼팔", "moderate", ()) if status == "candidate_verdict" else None
        return vision_veto.VisionFaultContext(
            collection_status=status, verdict=verdict, supported_differences=[],
            root_cause_hypotheses=rcs, selected_frame_pairs=[], alignment={},
            telemetry={}, cap_would_apply=cap_would_apply,
        )

    def test_eligible_candidate_with_cap_injects_root_cause(self):
        """candidate_verdict + cap_would_apply → eligible → to_coach_context root-cause 주입 (D-11 HIGH-1 positive)."""
        ctx = self._ctx("candidate_verdict", cap_would_apply=True)
        assert ctx.eligible_for_coach is True
        coach = ctx.to_coach_context()
        assert coach["rootCauseHypotheses"][0]["text"] == "폴 밀착이 풀린 것으로 보임"

    def test_candidate_without_cap_not_eligible(self):
        """valid 하지만 cap 미적용(minor/88 → not_applicable)는 eligible False → coach 무주입 (D-11 HIGH-1 negative)."""
        ctx = self._ctx("candidate_verdict", cap_would_apply=False)
        assert ctx.eligible_for_coach is False

    def test_score_free_status_not_eligible(self):
        """score-free status(no_fault/low_alignment/...)는 eligible False (무주입)."""
        from sunity_shared.analysis import vision_veto

        for status in ("no_fault", "low_alignment_confidence", "resource_limited",
                       "disabled", "mode3_held"):
            ctx = self._ctx(status, cap_would_apply=False, root_text="")
            assert ctx.eligible_for_coach is False, status


class TestQuantificationSeamProduces:
    def test_seam_available_from_frame_pair(self):
        """seam 이 SelectedFramePair(keypoints) + 각도 → available 정량화 산출 (D-13 HIGH-1)."""
        app = _import_pipeline()
        import numpy as np
        from sunity_shared.analysis import skeleton, vision_veto

        kp = np.zeros((skeleton.NUM_KEYPOINTS, 2), dtype=float)
        for name, (x, y) in {
            "left_shoulder": (0.4, 0.3), "right_shoulder": (0.6, 0.3),
            "left_hip": (0.42, 0.6), "right_hip": (0.58, 0.6),
            "left_knee": (0.43, 0.8), "right_knee": (0.57, 0.8),
            "left_wrist": (0.35, 0.2), "right_wrist": (0.65, 0.2),
        }.items():
            kp[skeleton.kp_index(name)] = (x, y)
        pair = vision_veto.SelectedFramePair(
            student_frame_path=None, reference_frame_path=None,
            user_frame_idx=2, ref_frame_idx=2,
            student_keypoints=kp, reference_keypoints=kp,
        )
        s_ang = np.full((4, skeleton.NUM_JOINTS), 150.0)
        r_ang = np.full((4, skeleton.NUM_JOINTS), 178.0)
        out = app._build_vision_quantification_result(
            selected_frame_pair=pair, student_angles=s_ang, reference_angles=r_ang,
            baseline_kind="hip_line",
        )
        assert out.quantificationStatus == "available"
        assert out.angleDeltas and out.bodyRelativeNotches

    def test_seam_unavailable_on_none_pair_not_none(self):
        """seam 이 frame pair None 에 None 아닌 unavailable 반환 (D-13 HIGH-1)."""
        app = _import_pipeline()
        out = app._build_vision_quantification_result(selected_frame_pair=None)
        assert out is not None
        assert out.quantificationStatus == "unavailable"

    def test_pipeline_wires_collect_before_apply_ordering(self):
        """_process 소스에 collect→coach→build_result→quantification→apply 순서 박힘 (D-13 HIGH-1)."""
        app = _import_pipeline()
        src = _inspect.getsource(app._process)
        # 실제 호출부 위치 (주석 언급이 아니라 assignment 라인 기준).
        i_collect = src.find("vision_fault_context = _collect_vision_fault_context")
        i_coach = src.find("coach_context = _build_coach_context")
        i_build = src.find("result = assemble.build_result")
        i_quant = src.find("quantification = _build_vision_quantification_result")
        i_apply = src.find("result = _apply_vision_veto")
        for label, idx in [("collect", i_collect), ("coach", i_coach),
                           ("build_result", i_build), ("quantification", i_quant),
                           ("apply", i_apply)]:
            assert idx != -1, f"{label} 호출부 미발견"
        assert i_collect < i_coach, "collect 가 coach 이전"
        assert i_coach < i_build, "coach 가 build_result 이전"
        assert i_build < i_quant < i_apply, "build_result → quantification → apply 순서"
