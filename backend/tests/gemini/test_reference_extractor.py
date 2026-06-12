"""Plan 17-05 Task 1 — extract_reference_metadata 단위 테스트.

박제 정신:
  · Plan 17-05 박제 — 영역 A (Reference 자동 등록) 분기 라우팅 + G3 guardrail +
    graceful 폴백 + idempotent motion_id.
  · AI-SPEC §1b "학원 용어 3분기 라우팅 정확도" 직격 — 13+ AKA / 분기 2 학원 통용 /
    그 외 G3 fallback 의 3 케이스.
  · GeminiVisionCall.call 은 monkeypatch 로 stub — 외부 네트워크 호출 0.
  · resolve_model 경로 박제 — GEMINI_A_MODEL 가 override path. ALLOWED_MODELS
    (gemini-3.1-pro-preview / gemini-3.5-flash) 만 통과.
"""

from __future__ import annotations

from typing import Any

import pytest

from sunity_shared.gemini import reference_extractor
from sunity_shared.gemini.schemas import (
    CheckpointJoint,
    ReferenceRegistration,
)


# ─────────────────── 더미 GeminiVisionCall stub ───────────────────


class _StubCall:
    """GeminiVisionCall 대체 — schema/model/prompt/... 인자 기록 + call() 결과 박제."""

    def __init__(self, result: Any) -> None:
        self.result = result
        self.init_kwargs: dict[str, Any] = {}
        self.call_paths: list[str] = []

    def __call__(self, *args: Any, **kwargs: Any) -> "_StubCall":
        # dataclass(...) 호출 박제 — init kwargs 저장 후 self 반환.
        self.init_kwargs = dict(kwargs)
        return self

    def call(self, video_path: str) -> Any:  # noqa: D401
        self.call_paths.append(video_path)
        return self.result


def _video(tmp_path, name: str = "ref.mp4") -> str:
    p = tmp_path / name
    p.write_bytes(b"fake-mp4")
    return str(p)


def _ok_registration(
    motion_name_ipsf: str = "Butterfly",
    motion_name_ko: str = "버터플라이",
    clip_start: float = 1.5,
    clip_end: float = 8.0,
    checkpoint_joints: list[dict] | None = None,
    confidence: float = 0.85,
) -> ReferenceRegistration:
    if checkpoint_joints is None:
        checkpoint_joints = [
            {"joint_key": "left_knee", "expectation": "EXTEND"},
            {"joint_key": "right_knee", "expectation": "EXTEND"},
        ]
    return ReferenceRegistration.model_validate(
        dict(
            motion_name_ipsf=motion_name_ipsf,
            motion_name_ko=motion_name_ko,
            clip_start_seconds=clip_start,
            clip_end_seconds=clip_end,
            checkpoint_joints=checkpoint_joints,
            confidence=confidence,
        )
    )


def _patch_call(monkeypatch, stub: _StubCall) -> None:
    monkeypatch.setattr(reference_extractor, "GeminiVisionCall", stub)


# ─────────────────── Fixture content 박제 검증 ───────────────────


class TestFixtureContents:
    """ipsf_whitelist.json / studio_branch2_aliases.json 초기 박제 검증."""

    def test_ipsf_whitelist_has_at_least_13_entries(self) -> None:
        wl = reference_extractor._load_ipsf_whitelist()
        # AI-SPEC §1b — 13+ AKA 매핑 (Butterfly/Cupid/Deadlift 등) 박제.
        assert len(wl) >= 13, f"ipsf_whitelist entry < 13: {len(wl)}"
        # 각 entry 가 ipsf_name 필드 박힘.
        for e in wl:
            assert "ipsf_name" in e and e["ipsf_name"]

    def test_studio_branch2_aliases_has_3_entries(self) -> None:
        aliases = reference_extractor._load_studio_branch2_aliases()
        # 메모리 [[studio-term-3branch-system]] — 폭스탑/폭스탑 스플릿/사이드웨이 스핀 박제.
        assert len(aliases) >= 3
        keys = {a["studio_alias_ko"] for a in aliases}
        assert "폭스탑" in keys
        assert "폭스탑 스플릿" in keys
        assert "사이드웨이 스핀" in keys


# ─────────────────── 분기 1: IPSF 매치 ───────────────────


class TestBranch1Ipsf:
    """Gemini A 출력 motion_name_ipsf 가 화이트리스트 매치 → branch_1_ipsf."""

    def test_ipsf_exact_match_routes_branch_1(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall(
            _ok_registration(
                motion_name_ipsf="Butterfly",
                motion_name_ko="버터플라이",
            )
        )
        _patch_call(monkeypatch, stub)

        result = reference_extractor.extract_reference_metadata(
            _video(tmp_path),
            studio_alias=None,
        )

        assert result is not None
        assert result["routing_branch"] == "branch_1_ipsf"
        assert result["review_required"] is False
        assert result["motion_name_ipsf"] == "Butterfly"
        # G3 inactiveReason 박힘 X (분기 1 = active).
        assert result.get("inactive_reason") is None
        # 결과 dict 의 motion_id 정합.
        assert result["motion_id"]
        # clip_range / checkpoint_joints 박힘.
        assert "clip_range" in result
        assert result["clip_range"]["clip_start_seconds"] == 1.5
        assert result["clip_range"]["clip_end_seconds"] == 8.0
        assert len(result["checkpoint_joints"]) == 2

    def test_ipsf_case_insensitive_normalize(self, tmp_path, monkeypatch) -> None:
        """대소문자/공백/하이픈 정규화 — 'inverted-thigh hold' 같은 변형도 매치."""
        stub = _StubCall(
            _ok_registration(
                motion_name_ipsf="Inverted-Thigh HOLD",
                motion_name_ko="허벅지 홀드",
            )
        )
        _patch_call(monkeypatch, stub)

        result = reference_extractor.extract_reference_metadata(
            _video(tmp_path),
            studio_alias=None,
        )

        assert result is not None
        assert result["routing_branch"] == "branch_1_ipsf"
        assert result["review_required"] is False


# ─────────────────── 분기 2: studio_alias 매치 ───────────────────


class TestBranch2Studio:
    """studio_alias 가 분기 2 화이트리스트 매치 → branch_2_studio."""

    def test_foxtop_routes_branch_2(self, tmp_path, monkeypatch) -> None:
        # Gemini 가 IPSF 미등재 호칭 출력해도 — studio_alias 가 분기 2 entry 면 우선.
        stub = _StubCall(
            _ok_registration(
                motion_name_ipsf="Foxtop Combo",  # IPSF 미등재
                motion_name_ko="폭스탑",
            )
        )
        _patch_call(monkeypatch, stub)

        result = reference_extractor.extract_reference_metadata(
            _video(tmp_path),
            studio_alias="폭스탑",
        )

        assert result is not None
        assert result["routing_branch"] == "branch_2_studio"
        assert result["review_required"] is False
        # championPersonalAlias audit 박힘.
        assert result.get("champion_personal_alias") == "버터플라이 콤보"
        # 분기 2 = active.
        assert result.get("inactive_reason") is None


# ─────────────────── 분기 3: G3 fallback ───────────────────


class TestBranch3AutoG3Guardrail:
    """IPSF 미매치 + studio_alias 미매치 → branch_3_auto + review_required=True."""

    def test_unknown_motion_triggers_g3(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall(
            _ok_registration(
                motion_name_ipsf="UnregisteredMove99",  # 화이트리스트 외
                motion_name_ko="미등재 동작",
            )
        )
        _patch_call(monkeypatch, stub)

        result = reference_extractor.extract_reference_metadata(
            _video(tmp_path),
            studio_alias=None,
        )

        assert result is not None
        assert result["routing_branch"] == "branch_3_auto"
        assert result["review_required"] is True
        # G3 박제 — inactiveReason='ipsf_whitelist_miss'.
        assert result["inactive_reason"] == "ipsf_whitelist_miss"

    def test_unknown_motion_with_unmatched_studio_alias(
        self, tmp_path, monkeypatch
    ) -> None:
        """studio_alias 가 분기 2 entry 도 아니고 IPSF 매치 안 됨 → 분기 3."""
        stub = _StubCall(
            _ok_registration(
                motion_name_ipsf="Some Custom Move",
                motion_name_ko="커스텀",
            )
        )
        _patch_call(monkeypatch, stub)

        result = reference_extractor.extract_reference_metadata(
            _video(tmp_path),
            studio_alias="알수없는 동작",
        )

        assert result is not None
        assert result["routing_branch"] == "branch_3_auto"
        assert result["review_required"] is True
        assert result["inactive_reason"] == "ipsf_whitelist_miss"


# ─────────────────── Graceful 폴백 ───────────────────


class TestGracefulFallback:
    """GeminiVisionCall.call → None 시 전체 None 반환 (caller 는 500 반환 path)."""

    def test_call_none_returns_none(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall(result=None)
        _patch_call(monkeypatch, stub)

        result = reference_extractor.extract_reference_metadata(
            _video(tmp_path),
            studio_alias=None,
        )

        assert result is None


# ─────────────────── Idempotent motion_id ───────────────────


class TestIdempotentMotionId:
    """같은 입력 2회 호출 시 같은 motion_id 박힘."""

    def test_same_input_same_motion_id(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall(
            _ok_registration(
                motion_name_ipsf="Butterfly",
                motion_name_ko="버터플라이",
            )
        )
        _patch_call(monkeypatch, stub)

        result_a = reference_extractor.extract_reference_metadata(
            _video(tmp_path),
            studio_alias=None,
        )
        result_b = reference_extractor.extract_reference_metadata(
            _video(tmp_path),
            studio_alias=None,
        )

        assert result_a is not None and result_b is not None
        assert result_a["motion_id"] == result_b["motion_id"]

    def test_override_motion_id_takes_precedence(self, tmp_path, monkeypatch) -> None:
        """override_motion_id 박힘 시 slug 산출 무시하고 그대로 박힘 (Firestore 호환)."""
        stub = _StubCall(
            _ok_registration(
                motion_name_ipsf="Butterfly",
                motion_name_ko="버터플라이",
            )
        )
        _patch_call(monkeypatch, stub)

        result = reference_extractor.extract_reference_metadata(
            _video(tmp_path),
            studio_alias=None,
            override_motion_id="ref-foxtop",
        )

        assert result is not None
        assert result["motion_id"] == "ref-foxtop"

    def test_branch_2_uses_studio_alias_in_motion_id(
        self, tmp_path, monkeypatch
    ) -> None:
        """override 없으면 분기 2 = studio_alias slug 기반 motion_id."""
        stub = _StubCall(
            _ok_registration(
                motion_name_ipsf="Foxtop Combo",
                motion_name_ko="폭스탑",
            )
        )
        _patch_call(monkeypatch, stub)

        result = reference_extractor.extract_reference_metadata(
            _video(tmp_path),
            studio_alias="폭스탑",
        )

        assert result is not None
        assert result["routing_branch"] == "branch_2_studio"
        # slug 산출 — 한글 alias 가 살아있는지 또는 audit-friendly slug 인지 박힘.
        assert result["motion_id"]


# ─────────────────── GeminiVisionCall 인자 박제 ───────────────────


class TestGeminiCallInit:
    """Gemini A 호출 시 schema/model/temperature/thinking_budget 박제 정합."""

    def test_uses_reference_registration_schema(
        self, tmp_path, monkeypatch
    ) -> None:
        stub = _StubCall(
            _ok_registration(
                motion_name_ipsf="Butterfly",
                motion_name_ko="버터플라이",
            )
        )
        _patch_call(monkeypatch, stub)

        reference_extractor.extract_reference_metadata(
            _video(tmp_path),
            studio_alias=None,
        )

        # ReferenceRegistration schema 박힘.
        assert stub.init_kwargs.get("schema") is ReferenceRegistration
        # AI-SPEC §4 영역 A — temperature 0.1, max_output_tokens 2048.
        assert stub.init_kwargs.get("temperature") == 0.1
        assert stub.init_kwargs.get("max_output_tokens") == 2048
        # enforce_object_guard=True 박제 (G1 정합).
        assert stub.init_kwargs.get("enforce_object_guard") is True

    def test_default_model_is_pro_preview(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall(
            _ok_registration(
                motion_name_ipsf="Butterfly",
                motion_name_ko="버터플라이",
            )
        )
        _patch_call(monkeypatch, stub)
        monkeypatch.delenv("GEMINI_A_MODEL", raising=False)

        reference_extractor.extract_reference_metadata(
            _video(tmp_path),
            studio_alias=None,
        )

        assert stub.init_kwargs.get("model") == "gemini-3.1-pro-preview"

    def test_env_override_path(self, tmp_path, monkeypatch) -> None:
        """GEMINI_A_MODEL=gemini-3.5-flash 박힘 시 fallback 박제 (resolve_model)."""
        stub = _StubCall(
            _ok_registration(
                motion_name_ipsf="Butterfly",
                motion_name_ko="버터플라이",
            )
        )
        _patch_call(monkeypatch, stub)
        monkeypatch.setenv("GEMINI_A_MODEL", "gemini-3.5-flash")

        reference_extractor.extract_reference_metadata(
            _video(tmp_path),
            studio_alias=None,
        )

        assert stub.init_kwargs.get("model") == "gemini-3.5-flash"

    def test_disallowed_model_raises(self, tmp_path, monkeypatch) -> None:
        """ALLOWED_MODELS 박제 외 → resolve_model ValueError (graceful X)."""
        stub = _StubCall(
            _ok_registration(
                motion_name_ipsf="Butterfly",
                motion_name_ko="버터플라이",
            )
        )
        _patch_call(monkeypatch, stub)
        monkeypatch.setenv("GEMINI_A_MODEL", "gemini-2.5-pro")

        with pytest.raises(ValueError, match="ALLOWED_MODELS"):
            reference_extractor.extract_reference_metadata(
                _video(tmp_path),
                studio_alias=None,
            )
