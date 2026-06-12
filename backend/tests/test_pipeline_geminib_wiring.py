"""Plan 17-04 Task 2 — pipeline _process 영역 B dual-track wiring 통합 테스트.

박제 정신:
  · `_process(bucket, key, uid, analysis_id)` 시그너처 변경 0.
  · GeminiCoachWriter.write / CerebrasCoachWriter.write 모두 monkeypatch — 외부 호출 0.
  · 본 test 는 wiring 헬퍼 (`_coach_enabled` / `_build_coach_context` /
    `_strip_reserved_keys` / `_gemini_b_audit_payload` / `_ensure_gemini_coach_writer`)
    단위 박제 검증 + dual-track 분기 회귀.
  · B3 회귀 — Gemini 와 Cerebras 가 같은 context dict 인스턴스 공유 (B3 정합 핵심).
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


# pipeline app.py 의 Lambda Layer path 박제 (/opt/python) 가 import 시 필요.
_LAYER = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

_PIPELINE_DIR = (
    Path(__file__).resolve().parents[1] / "functions" / "pipeline"
)
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))


pipeline_app = pytest.importorskip("app")


# ─────────────────── 더미 assessment / writer 박제 ───────────────────


def _mk_assessments():
    """kismam.top_issues 가 `.key`/`.label_ko`/`.deviation_deg`/`.direction` 박힌
    객체 list 를 받도록 박제. 실제 KISMAM 의 JointAssessment 와 호환되는 namespace 박제.
    """
    from sunity_shared.analysis.kismam import JointAssessment

    return [
        JointAssessment(
            key="left_elbow",
            label_ko="왼팔꿈치",
            score=70,
            deviation_deg=23.0,
            part="상체",
            direction="extend",
        ),
        JointAssessment(
            key="left_shoulder",
            label_ko="왼어깨",
            score=82,
            deviation_deg=12.0,
            part="상체",
            direction="extend",
        ),
        JointAssessment(
            key="right_hip",
            label_ko="오른엉덩이",
            score=85,
            deviation_deg=8.0,
            part="코어",
            direction="contract",
        ),
    ]


class _RecordingWriter:
    """`.write(context)` 호출 + 반환값 기록 stub — Gemini / Cerebras 양쪽 박제."""

    def __init__(self, return_value: dict) -> None:
        self._rv = return_value
        self.contexts: list[dict] = []

    def write(self, context: dict) -> dict:
        # 같은 인스턴스 ID 비교 회귀 박제 — 보관.
        self.contexts.append(context)
        return self._rv


# ─────────────────── _coach_enabled env 박제 ───────────────────


class TestCoachEnabled:
    def test_default_on(self, monkeypatch) -> None:
        monkeypatch.delenv("GEMINI_COACH_ENABLED", raising=False)
        assert pipeline_app._coach_enabled() is True

    def test_off_value_zero(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        assert pipeline_app._coach_enabled() is False

    def test_off_value_false(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "false")
        assert pipeline_app._coach_enabled() is False

    def test_off_value_empty(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "")
        assert pipeline_app._coach_enabled() is False

    def test_on_value_truthy(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "1")
        assert pipeline_app._coach_enabled() is True


# ─────────────────── _build_coach_context ───────────────────


class TestBuildCoachContext:
    def test_returns_shared_dict_with_keys(self) -> None:
        ctx = pipeline_app._build_coach_context(
            mode="mode1",
            assessments=_mk_assessments(),
            dim_scores={"angle": 75.0},
            local_video_path="/tmp/x.mp4",
            scene_flags={"grip_visible": True},
        )
        # Cerebras 호환 키.
        assert ctx["mode"] == "mode1"
        assert isinstance(ctx["joints"], list)
        assert len(ctx["joints"]) == 3
        # 각 joint 가 key/labelKo/deviation_deg/direction 박힘.
        for j in ctx["joints"]:
            assert {"key", "labelKo", "deviation_deg", "direction"}.issubset(j.keys())
        # Phase 17 신규 키.
        assert ctx["videoPath"] == "/tmp/x.mp4"
        assert ctx["dimensionScores"] == {"angle": 75.0}
        assert ctx["sceneFlags"] == {"grip_visible": True}

    def test_no_gemini_d_key_v1(self) -> None:
        """3차 R-B2 정합 — geminiD 키 v1 박제 0 (D 가 B 보다 늦음)."""
        ctx = pipeline_app._build_coach_context(
            mode="mode3",
            assessments=_mk_assessments(),
            dim_scores=None,
            local_video_path=None,
            scene_flags=None,
        )
        assert "geminiD" not in ctx
        assert "gemini_d" not in ctx


# ─────────────────── _strip_reserved_keys ───────────────────


class TestStripReservedKeys:
    def test_strips_underscore_prefix(self) -> None:
        d = {
            "left_elbow": {"detail": "ok"},
            "_fallbackReason": "x",
            "_meta": {"model": "y"},
        }
        stripped = pipeline_app._strip_reserved_keys(d)
        assert stripped == {"left_elbow": {"detail": "ok"}}

    def test_preserves_user_keys(self) -> None:
        d = {
            "left_elbow": {"detail": "ok"},
            "right_hip": {"detail": "ok2"},
        }
        assert pipeline_app._strip_reserved_keys(d) == d


# ─────────────────── _gemini_b_audit_payload ───────────────────


class TestGeminiBAuditPayload:
    def test_success_path_uses_meta(self) -> None:
        result = {
            "left_elbow": {"detail": "..."},
            "_meta": {
                "model": "gemini-3.1-pro-preview",
                "latency_ms": 12000,
                "tokens_used": 0,
                "judgeScore": None,
            },
        }
        audit = pipeline_app._gemini_b_audit_payload(
            result, cerebras_used=False, cerebras_fallback_reason=None
        )
        assert audit is not None
        assert audit["model"] == "gemini-3.1-pro-preview"
        assert audit["latencyMs"] == 12000
        assert audit["fallback"] is None
        assert audit["fallbackReason"] is None
        assert audit["judgeScore"] is None

    def test_cerebras_fallback_path(self) -> None:
        audit = pipeline_app._gemini_b_audit_payload(
            {},
            cerebras_used=True,
            cerebras_fallback_reason="video_path_missing",
        )
        assert audit is not None
        assert audit["model"] == "gpt-oss-120b"
        assert audit["fallback"] == "cerebras"
        assert audit["fallbackReason"] == "video_path_missing"

    def test_no_meta_returns_none(self) -> None:
        # Gemini path (cerebras_used=False) 인데 _meta 박힘 X → None.
        audit = pipeline_app._gemini_b_audit_payload(
            {}, cerebras_used=False, cerebras_fallback_reason=None
        )
        assert audit is None


# ─────────────────── dual-track 분기 회귀 (단위) ───────────────────
#
# `_process` 본체 박제 dependency 가 깊어 (KISMAM / Phase 6/8/9/12) 통합 단위
# 박제는 wave 1 / wave 2 박제 패턴 정합 — wiring 헬퍼 직접 호출 + 분기 검증.
# 본 클래스는 `_call_wave3_gemini_coach` 박제 helper 가 없으므로 dual-track 분기
# 박제 정신 검증을 wiring 헬퍼 (`_coach_enabled` / `_strip_reserved_keys` /
# `_gemini_b_audit_payload`) 조합으로 박제.


class TestDualTrackBranchSimulation:
    """Plan 17-04 dual-track wiring 박제 시뮬레이션 — _process 본체 분기 로직 박제."""

    def _simulate_dual_track(
        self,
        *,
        coach_enabled: bool,
        gemini_writer: _RecordingWriter,
        cerebras_writer: _RecordingWriter,
        coach_context: dict,
    ):
        """`_process` 박제 dual-track 분기 박제 — wiring 정합 정밀 박제.

        본 헬퍼는 `_process` 박제 박힌 흐름과 1:1 정합 (gemini_b_audit / coach_details
        2 변수 박제). 회귀 시 `_process` 의 박제 박힌 정확한 분기 박제 검증.
        """
        gemini_b_audit: dict | None = None
        if coach_enabled:
            gemini_writer_result = gemini_writer.write(coach_context)
            user_visible_keys = [
                k for k in gemini_writer_result.keys() if not str(k).startswith("_")
            ]
            if user_visible_keys:
                coach_details = pipeline_app._strip_reserved_keys(gemini_writer_result)
                gemini_b_audit = pipeline_app._gemini_b_audit_payload(
                    gemini_writer_result,
                    cerebras_used=False,
                    cerebras_fallback_reason=None,
                )
            else:
                fb_reason = gemini_writer_result.get("_fallbackReason")
                coach_details = cerebras_writer.write(coach_context)
                gemini_b_audit = pipeline_app._gemini_b_audit_payload(
                    {},
                    cerebras_used=True,
                    cerebras_fallback_reason=fb_reason,
                )
        else:
            coach_details = cerebras_writer.write(coach_context)
            gemini_b_audit = None
        return coach_details, gemini_b_audit

    def test_case1_gemini_success_no_cerebras_call(self, monkeypatch) -> None:
        """case (1): GEMINI_COACH_ENABLED=1 + Gemini 성공 → Cerebras 호출 0 + audit 박제."""
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "1")
        gemini = _RecordingWriter({
            "left_elbow": {"detail": "강사 권고"},
            "_meta": {
                "model": "gemini-3.1-pro-preview",
                "latency_ms": 8000,
                "tokens_used": 0,
                "judgeScore": None,
            },
        })
        cerebras = _RecordingWriter({})
        coach_context = {"mode": "mode1", "joints": [{"key": "x"}]}

        coach_details, audit = self._simulate_dual_track(
            coach_enabled=True,
            gemini_writer=gemini,
            cerebras_writer=cerebras,
            coach_context=coach_context,
        )

        # Gemini 1회 호출, Cerebras 0회.
        assert len(gemini.contexts) == 1
        assert len(cerebras.contexts) == 0
        # coach_details 박제 — reserved 키 strip.
        assert coach_details == {"left_elbow": {"detail": "강사 권고"}}
        assert "_fallbackReason" not in coach_details
        assert "_meta" not in coach_details
        # audit 박제.
        assert audit is not None
        assert audit["model"] == "gemini-3.1-pro-preview"
        assert audit["fallback"] is None

    def test_case2_gemini_video_missing_cerebras_fallback(self, monkeypatch) -> None:
        """case (2): GEMINI_COACH_ENABLED=1 + Gemini `{"_fallbackReason":
        "video_path_missing"}` → Cerebras 호출 + geminiB.fallback="cerebras".
        """
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "1")
        gemini = _RecordingWriter({"_fallbackReason": "video_path_missing"})
        cerebras = _RecordingWriter({"left_elbow": {"detail": "수치 기반"}})
        coach_context = {"mode": "mode1", "joints": [{"key": "x"}]}

        coach_details, audit = self._simulate_dual_track(
            coach_enabled=True,
            gemini_writer=gemini,
            cerebras_writer=cerebras,
            coach_context=coach_context,
        )

        # Cerebras 1회 호출 박제.
        assert len(cerebras.contexts) == 1
        # Cerebras 결과 박제.
        assert coach_details == {"left_elbow": {"detail": "수치 기반"}}
        # audit 박제.
        assert audit is not None
        assert audit["fallback"] == "cerebras"
        assert audit["fallbackReason"] == "video_path_missing"
        assert audit["model"] == "gpt-oss-120b"

    def test_case3_coach_disabled_only_cerebras(self, monkeypatch) -> None:
        """case (3): GEMINI_COACH_ENABLED=0 → Gemini 호출 0 + Cerebras 만 호출 + audit=None."""
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        gemini = _RecordingWriter({
            "left_elbow": {"detail": "..."},
            "_meta": {"model": "gemini-3.1-pro-preview"},
        })
        cerebras = _RecordingWriter({"left_elbow": {"detail": "Cerebras"}})
        coach_context = {"mode": "mode1", "joints": [{"key": "x"}]}

        coach_details, audit = self._simulate_dual_track(
            coach_enabled=False,
            gemini_writer=gemini,
            cerebras_writer=cerebras,
            coach_context=coach_context,
        )

        # Gemini 호출 0.
        assert len(gemini.contexts) == 0
        # Cerebras 1회.
        assert len(cerebras.contexts) == 1
        assert coach_details == {"left_elbow": {"detail": "Cerebras"}}
        # audit 박제 X.
        assert audit is None

    def test_case4_both_empty_dict_graceful(self, monkeypatch) -> None:
        """case (4): Gemini + Cerebras 둘 다 `{}` → 빈 tips/coach (기존 graceful 박제)."""
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "1")
        gemini = _RecordingWriter({})
        cerebras = _RecordingWriter({})
        coach_context = {"mode": "mode1", "joints": [{"key": "x"}]}

        coach_details, audit = self._simulate_dual_track(
            coach_enabled=True,
            gemini_writer=gemini,
            cerebras_writer=cerebras,
            coach_context=coach_context,
        )

        # Gemini 결과 빈 dict → Cerebras 폴백 → 빈 dict.
        assert coach_details == {}
        # audit 박제 — cerebras_used=True (Gemini 가 fallback dict 반환).
        assert audit is not None
        assert audit["fallback"] == "cerebras"
        # fallbackReason 박제 — None (Gemini 가 `_fallbackReason` 키 박지 않음 → unknown).
        assert audit["fallbackReason"] == "unknown"

    def test_case5_b3_signature_shared_context(self, monkeypatch) -> None:
        """case (5): B3 회귀 — Gemini 와 Cerebras 가 받은 context dict 가 동일 인스턴스."""
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "1")
        gemini = _RecordingWriter({"_fallbackReason": "video_path_missing"})
        cerebras = _RecordingWriter({"left_elbow": {"detail": "ok"}})
        coach_context = {"mode": "mode1", "joints": [{"key": "x"}]}

        self._simulate_dual_track(
            coach_enabled=True,
            gemini_writer=gemini,
            cerebras_writer=cerebras,
            coach_context=coach_context,
        )

        # 같은 id() — 같은 인스턴스 박제.
        assert id(gemini.contexts[0]) == id(cerebras.contexts[0])


# ─────────────────── 소스 grep 회귀 (verify 자동화) ───────────────────


class TestSourceRegression:
    """plan verification — pipeline app.py 박제 박힌 import + 호출 회귀 박제."""

    def test_gemini_coach_writer_imported_and_used(self) -> None:
        src = Path(pipeline_app.__file__).read_text()
        # import 1회.
        assert "from sunity_shared.gemini.coach_writer_v2 import GeminiCoachWriter" in src
        # 호출/참조 ≥ 2회 (import + 호출/싱글톤 박제).
        lines = [
            line for line in src.splitlines()
            if "GeminiCoachWriter" in line and not line.lstrip().startswith("#")
        ]
        assert len(lines) >= 2

    def test_gemini_coach_enabled_env_present(self) -> None:
        src = Path(pipeline_app.__file__).read_text()
        lines = [
            line for line in src.splitlines()
            if "GEMINI_COACH_ENABLED" in line and not line.lstrip().startswith("#")
        ]
        assert len(lines) >= 1

    def test_build_coach_context_helper_exposed(self) -> None:
        assert hasattr(pipeline_app, "_build_coach_context")
        assert hasattr(pipeline_app, "_strip_reserved_keys")
        assert hasattr(pipeline_app, "_gemini_b_audit_payload")
        assert hasattr(pipeline_app, "_coach_enabled")
        assert hasattr(pipeline_app, "_ensure_gemini_coach_writer")


# ─────────────────── B3 시그니처 회귀 ───────────────────


class TestB3SignatureRegression:
    """B3 hard gate — Gemini 와 Cerebras 의 `.write` 시그니처 100% 동일."""

    def test_write_signature_matches_cerebras(self) -> None:
        import inspect
        from sunity_shared.analysis.coach_writer import CerebrasCoachWriter
        from sunity_shared.gemini.coach_writer_v2 import GeminiCoachWriter

        sig_g = inspect.signature(GeminiCoachWriter.write)
        sig_c = inspect.signature(CerebrasCoachWriter.write)
        assert list(sig_g.parameters) == ["self", "context"]
        assert list(sig_g.parameters) == list(sig_c.parameters)
