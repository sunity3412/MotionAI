"""Plan 17-04 Task 1 — GeminiCoachWriter 단위 테스트.

박제 정신:
  · Plan 17-04 — 영역 B Coach 정상 호출 + 강사 보조 톤 schema 강제 + 부위별 용어 +
    blocklist + retry + Cerebras 폴백 신호 (`{}` 또는 `{"_fallbackReason": ...}` reserved
    key only — 2차 R-W4 정합 None 반환 박제 0).
  · GeminiVisionCall.call 은 monkeypatch 로 stub — 외부 네트워크 호출 0.
  · CoachPayload Pydantic schema 인스턴스를 stub 가 직접 반환 → _coach_payload_to_dict
    변환 + _validate_tone 후처리 검증.
  · firestore_admin.complete_analysis(gemini_b=...) Firestore mock 의 set payload 에
    `geminiB` 박힘 검증.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from sunity_shared.gemini import coach_writer_v2
from sunity_shared.gemini.coach_writer_v2 import GeminiCoachWriter
from sunity_shared.gemini.schemas import (
    CoachCause,
    CoachDetail2,
    CoachPayload,
    JointCoaching,
)


# ─────────────────── 더미 GeminiVisionCall stub ───────────────────


class _StubCall:
    """GeminiVisionCall 대체 — schema/model/prompt/... 인자 기록 + call() 결과 박제.

    `coach_writer_v2._build_call()` 가 `GeminiVisionCall(**kwargs)` 형태로 호출하므로
    callable 로 동작한다. 인스턴스 하나가 다회 호출되며 각 호출마다 `init_kwargs` /
    `call_paths` 누적.
    """

    def __init__(self, results: list[Any]) -> None:
        # 호출마다 results 의 다음 값 반환 (retry 시뮬레이션). 모두 소진되면 마지막 값 유지.
        self._results = list(results)
        self._idx = 0
        self.init_kwargs_list: list[dict[str, Any]] = []
        self.call_paths: list[str] = []
        # prompt 박제 추적 (호출별).
        self.prompts: list[str] = []
        self.last_init_kwargs: dict[str, Any] = {}

    def __call__(self, *args: Any, **kwargs: Any) -> "_StubCall":
        self.init_kwargs_list.append(dict(kwargs))
        self.last_init_kwargs = dict(kwargs)
        # coach_writer_v2 가 인스턴스 생성 후 .prompt = ... mutate.
        # __call__ 가 self 를 반환하므로 self.prompt 가 set 가능.
        self.prompt = kwargs.get("prompt", "")
        self.model = kwargs.get("model", "")
        return self

    def call(self, video_path: str, *, preuploaded_handle: Any = None) -> Any:
        # 27-04: 실 GeminiVisionCall.call 이 preuploaded_handle keyword 를 수용하므로 stub 도 정합.
        self.call_paths.append(video_path)
        self.preuploaded_handles = getattr(self, "preuploaded_handles", [])
        self.preuploaded_handles.append(preuploaded_handle)
        self.prompts.append(getattr(self, "prompt", ""))
        idx = min(self._idx, len(self._results) - 1)
        result = self._results[idx]
        self._idx += 1
        # exception class 박제는 raise — instance / None / Pydantic instance 는 return.
        if isinstance(result, BaseException):
            raise result
        if isinstance(result, type) and issubclass(result, BaseException):
            raise result("stub raise")
        return result


def _patch_call(monkeypatch, stub: _StubCall) -> None:
    monkeypatch.setattr(coach_writer_v2, "GeminiVisionCall", stub)


# ─────────────────── 헬퍼: 강사 보조 톤 통과 payload 박제 ───────────────────


def _ok_payload() -> CoachPayload:
    """강사 보조 톤 통과 — 부위별 용어 ('고관절' / '코어') + 3 어휘 ('강사' / '함께' / '확인')."""
    causes = [
        CoachCause(
            title="고관절 가동범위 제한",
            explanation="고관절 굴곡 가동범위가 부족해 골반이 따라옵니다.",
            fix="강사와 함께 영상으로 좌우 차이 확인 후 햄스트링 스트레칭을 박으세요.",
        ),
        CoachCause(
            title="코어 안정성 부족",
            explanation="코어 호흡 패턴이 끊겨 상체가 흔들립니다.",
            fix="중립 코어로 5초 호흡 — 강사와 함께 영상 확인 권고.",
        ),
        CoachCause(
            title="견갑 안정화",
            explanation="견갑 안정화가 늦어 어깨가 으쓱하는 패턴입니다.",
            fix="강사와 함께 시연 영상을 확인하면서 견갑 하방회전을 박으세요.",
        ),
    ]
    detail2 = CoachDetail2(causes=causes)
    joint = JointCoaching(
        joint_key="left_elbow",
        detail="강사와 함께 영상을 확인하면서 팔꿈치 접근 각도를 박으세요.",
        detail2=detail2,
    )
    return CoachPayload(joints=[joint])


def _payload_missing_body_term() -> CoachPayload:
    """부위별 용어 14개 모두 부재 — _validate_tone 의 1번 항목 실패."""
    causes = [
        CoachCause(
            title="허리 펴기",
            explanation="허리를 펴세요.",
            fix="강사와 함께 영상으로 확인.",
        ),
        CoachCause(
            title="자세 정렬",
            explanation="자세를 똑바로 정렬하세요.",
            fix="강사와 함께 영상으로 확인.",
        ),
        CoachCause(
            title="호흡",
            explanation="호흡을 자연스럽게 하세요.",
            fix="강사와 함께 영상으로 확인.",
        ),
    ]
    return CoachPayload(
        joints=[
            JointCoaching(
                joint_key="left_elbow",
                detail="강사와 함께 영상을 확인하면서 박으세요.",
                detail2=CoachDetail2(causes=causes),
            )
        ]
    )


def _payload_missing_coach_word() -> CoachPayload:
    """coach_note 3 어휘 중 '강사' 누락 — _validate_tone 의 2번 항목 실패."""
    causes = [
        CoachCause(
            title="고관절 한계",
            explanation="고관절 가동이 모자랍니다.",
            fix="햄스트링 스트레칭으로 보완.",
        ),
        CoachCause(
            title="코어 끊김",
            explanation="코어 호흡 패턴이 끊깁니다.",
            fix="브리딩 5회 박제 권고.",
        ),
        CoachCause(
            title="견갑 안정화",
            explanation="견갑 안정화가 늦습니다.",
            fix="아래로 끌어내려 박제.",
        ),
    ]
    return CoachPayload(
        joints=[
            JointCoaching(
                joint_key="left_elbow",
                detail="팔꿈치를 부드럽게 박으세요.",
                detail2=CoachDetail2(causes=causes),
            )
        ]
    )


def _payload_blocklist_match() -> CoachPayload:
    """blocklist '이렇게 하세요' 매치 — _validate_tone 의 3번 항목 실패."""
    causes = [
        CoachCause(
            title="고관절",
            explanation="고관절 가동 부족 — 이렇게 하세요.",
            fix="강사와 함께 영상 확인.",
        ),
        CoachCause(
            title="코어",
            explanation="코어 호흡 — 강사와 함께 영상 확인.",
            fix="강사와 함께 영상 확인.",
        ),
        CoachCause(
            title="견갑",
            explanation="견갑 안정화 — 강사와 함께 영상 확인.",
            fix="강사와 함께 영상 확인.",
        ),
    ]
    return CoachPayload(
        joints=[
            JointCoaching(
                joint_key="left_elbow",
                detail="강사와 함께 영상 확인하세요.",
                detail2=CoachDetail2(causes=causes),
            )
        ]
    )


def _video(tmp_path) -> str:
    p = tmp_path / "user.mp4"
    p.write_bytes(b"fake-mp4")
    return str(p)


def _context(tmp_path, joints_override: list[dict] | None = None) -> dict:
    """coach_context 박제 — Plan 17-04 _build_coach_context 출력 정합."""
    return {
        "mode": "mode1",
        "joints": joints_override
        if joints_override is not None
        else [
            {
                "key": "left_elbow",
                "labelKo": "왼팔꿈치",
                "deviation_deg": 23.0,
                "direction": "extend",
            },
            {
                "key": "left_shoulder",
                "labelKo": "왼어깨",
                "deviation_deg": 12.0,
                "direction": "extend",
            },
        ],
        "videoPath": _video(tmp_path),
        "dimensionScores": {"angle": 75.0, "line": 80.0},
        "sceneFlags": {
            "grip_visible": True,
            "backbend_present": False,
            "occlusion_severe": False,
            "camera_angle_problematic": False,
        },
    }


# ─────────────────── 테스트 ───────────────────


class TestSuccessPath:
    """case (1): context 정상 + videoPath 박제 → joint dict 반환 + 부위별 용어 + 3어휘 통과."""

    def test_returns_joint_dict_with_meta(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall([_ok_payload()])
        _patch_call(monkeypatch, stub)
        # 기본 model = gemini-3.1-pro-preview (DEFAULT_B_MODEL).
        monkeypatch.delenv("GEMINI_B_MODEL_OVERRIDE", raising=False)
        monkeypatch.delenv("GEMINI_B_MODEL", raising=False)

        writer = GeminiCoachWriter()
        result = writer.write(_context(tmp_path))

        # _fallbackReason 박제 X — 성공 path.
        assert "_fallbackReason" not in result
        # joint 키 ≥ 1.
        joint_keys = [k for k in result.keys() if not k.startswith("_")]
        assert joint_keys == ["left_elbow"]
        entry = result["left_elbow"]
        assert "detail" in entry
        assert "detail2" in entry
        assert "causes" in entry["detail2"]
        assert 3 <= len(entry["detail2"]["causes"]) <= 5
        # reserved _meta 박힘.
        assert "_meta" in result
        meta = result["_meta"]
        assert meta["model"] == "gemini-3.1-pro-preview"
        assert isinstance(meta["latency_ms"], int)
        assert meta["judgeScore"] is None
        # GeminiVisionCall init kwargs 박제.
        assert stub.last_init_kwargs["schema"] is CoachPayload
        assert stub.last_init_kwargs["model"] == "gemini-3.1-pro-preview"
        assert stub.last_init_kwargs["temperature"] == 0.4
        assert stub.last_init_kwargs["max_output_tokens"] == 12000
        assert stub.last_init_kwargs["thinking_budget"] == 4096
        assert stub.last_init_kwargs["enforce_object_guard"] is True
        # call 1회만 — retry 미발동.
        assert len(stub.call_paths) == 1


class TestBodyTermMissing:
    """case (2): 부위별 용어 누락 stub → 1회 retry 후 `{"_fallbackReason": "tone_validation_failed"}`."""

    def test_retry_then_tone_fallback(self, tmp_path, monkeypatch) -> None:
        # 2회 모두 부위별 용어 누락 payload — retry 후 fallback dict.
        stub = _StubCall([
            _payload_missing_body_term(),
            _payload_missing_body_term(),
        ])
        _patch_call(monkeypatch, stub)

        writer = GeminiCoachWriter()
        result = writer.write(_context(tmp_path))

        assert result == {"_fallbackReason": "tone_validation_failed"}
        # retry 1회 — 총 2회 호출.
        assert len(stub.call_paths) == 2


class TestCoachWordMissing:
    """case (3): coach_note '강사' 누락 → 1회 retry 후 fallback dict."""

    def test_retry_then_tone_fallback(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall([
            _payload_missing_coach_word(),
            _payload_missing_coach_word(),
        ])
        _patch_call(monkeypatch, stub)

        writer = GeminiCoachWriter()
        result = writer.write(_context(tmp_path))

        assert result == {"_fallbackReason": "tone_validation_failed"}
        assert len(stub.call_paths) == 2


class TestBlocklistMatch:
    """case (4): blocklist '이렇게 하세요' 매치 → 1회 retry 후 fallback dict."""

    def test_retry_then_tone_fallback(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall([
            _payload_blocklist_match(),
            _payload_blocklist_match(),
        ])
        _patch_call(monkeypatch, stub)

        writer = GeminiCoachWriter()
        result = writer.write(_context(tmp_path))

        assert result == {"_fallbackReason": "tone_validation_failed"}
        assert len(stub.call_paths) == 2


class TestGeminiNone:
    """case (5): GeminiVisionCall.call() → None (api_key 미설정 등) →
    `{"_fallbackReason": "gemini_none"}`.
    """

    def test_call_none_returns_gemini_none_fallback(
        self, tmp_path, monkeypatch
    ) -> None:
        # 2회 모두 None — retry 후 fallback.
        stub = _StubCall([None, None])
        _patch_call(monkeypatch, stub)

        writer = GeminiCoachWriter()
        result = writer.write(_context(tmp_path))

        assert result == {"_fallbackReason": "gemini_none"}
        assert len(stub.call_paths) == 2


class TestVideoPathMissing:
    """case (6): context["videoPath"]=None → 즉시 `{"_fallbackReason": "video_path_missing"}`.

    Gemini 호출 0 — Cerebras 폴백 신호.
    """

    def test_no_video_path_immediate_fallback(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall([_ok_payload()])
        _patch_call(monkeypatch, stub)

        ctx = _context(tmp_path)
        ctx["videoPath"] = None

        writer = GeminiCoachWriter()
        result = writer.write(ctx)

        assert result == {"_fallbackReason": "video_path_missing"}
        # Gemini 호출 0.
        assert stub.call_paths == []

    def test_no_video_path_key_immediate_fallback(
        self, tmp_path, monkeypatch
    ) -> None:
        """context 에 videoPath 키 자체가 없는 경우도 동일 — 즉시 fallback."""
        stub = _StubCall([_ok_payload()])
        _patch_call(monkeypatch, stub)

        ctx = _context(tmp_path)
        ctx.pop("videoPath")

        writer = GeminiCoachWriter()
        result = writer.write(ctx)

        assert result == {"_fallbackReason": "video_path_missing"}
        assert stub.call_paths == []


class TestContextMissingJoints:
    """case (7): context 에 mode/joints 없음 → `{}` (Cerebras 와 동일 graceful).

    coach_writer.py L121~123 정합 — `context.get("joints")` falsy 시 `{}`.
    """

    def test_no_joints_returns_empty_dict(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall([_ok_payload()])
        _patch_call(monkeypatch, stub)

        writer = GeminiCoachWriter()
        result = writer.write({"mode": "mode1", "videoPath": _video(tmp_path)})

        # 빈 dict — _fallbackReason 박제 X (graceful skip — Cerebras 와 동일).
        assert result == {}
        # Gemini 호출 0.
        assert stub.call_paths == []

    def test_empty_joints_returns_empty_dict(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall([_ok_payload()])
        _patch_call(monkeypatch, stub)

        writer = GeminiCoachWriter()
        result = writer.write({
            "mode": "mode1",
            "joints": [],
            "videoPath": _video(tmp_path),
        })

        assert result == {}
        assert stub.call_paths == []


class TestRetryRecovery:
    """추가 회귀 — 1회 실패 후 2회째 성공 시 정상 dict 반환."""

    def test_first_fail_second_succeeds(self, tmp_path, monkeypatch) -> None:
        # 1회: tone 실패, 2회: 정상.
        stub = _StubCall([_payload_missing_coach_word(), _ok_payload()])
        _patch_call(monkeypatch, stub)

        writer = GeminiCoachWriter()
        result = writer.write(_context(tmp_path))

        # 성공 path — _fallbackReason 박제 X.
        assert "_fallbackReason" not in result
        assert "left_elbow" in result
        assert len(stub.call_paths) == 2


class TestScenarioHint:
    """sceneFlags 가 prompt 에 hint 로 박힘 (occlusion_severe / backbend_present)."""

    def test_scene_flags_inject_hint_into_prompt(
        self, tmp_path, monkeypatch
    ) -> None:
        stub = _StubCall([_ok_payload()])
        _patch_call(monkeypatch, stub)

        ctx = _context(tmp_path)
        ctx["sceneFlags"] = {
            "grip_visible": False,
            "backbend_present": True,
            "occlusion_severe": True,
            "camera_angle_problematic": False,
        }
        writer = GeminiCoachWriter()
        writer.write(ctx)

        # prompt 에 hint 박힘.
        assert "장면 단서" in stub.prompts[0]
        assert "가시성" in stub.prompts[0]
        assert "백벤드" in stub.prompts[0] or "흉추" in stub.prompts[0]

    def test_vision_fault_root_cause_reaches_prompt(
        self, tmp_path, monkeypatch
    ) -> None:
        """23-02 Task 5 (MED-2): visionFault root-cause 가 실제 프롬프트 payload 에 도달 (graceful 무시 아님)."""
        stub = _StubCall([_ok_payload()])
        _patch_call(monkeypatch, stub)

        ctx = _context(tmp_path)
        ctx["visionFault"] = {
            "rootCauseHypotheses": [
                {"text": "코어 힘이 부족해 골반이 처진 것으로 보임",
                 "faultKey": {"part_scope": "core", "side": "unknown",
                              "keypoint_set": "hip", "fault_kind": "extension_or_alignment"},
                 "supportCount": 2},
            ],
        }
        writer = GeminiCoachWriter()
        writer.write(ctx)

        # 최종 tip 이 아니라 prompt 빌드 단계에서 root-cause 텍스트 도달 (false-pass 방지).
        assert "코어 힘이 부족해 골반이 처진 것으로 보임" in stub.prompts[0]
        assert "원인 단서" in stub.prompts[0]

    def test_no_vision_fault_no_root_cause_in_prompt(
        self, tmp_path, monkeypatch
    ) -> None:
        """visionFault 부재 시 원인 단서 섹션 미주입 (기존 동작 불변)."""
        stub = _StubCall([_ok_payload()])
        _patch_call(monkeypatch, stub)

        ctx = _context(tmp_path)  # visionFault 키 없음.
        writer = GeminiCoachWriter()
        writer.write(ctx)
        assert "비전 분석 원인 단서" not in stub.prompts[0]


class TestCausalChainDirective:
    """quick-260704-fwb — 처방 구조 (원인 기전 사슬) 지시가 시스템/유저 프롬프트에 포함."""

    def test_system_instruction_has_chain_rule_and_state_ban(self) -> None:
        instr = coach_writer_v2._COACH_SYSTEM_INSTRUCTION
        # (a) 기전 사슬 지시.
        assert "무엇 때문에" in instr
        assert "무너지" in instr
        # (b) 상태-서술-금지.
        assert "상태 서술만 있는 explanation" in instr
        # low-deviation 가이드와 공존 (기존 라인 유지).
        assert "low-deviation" in instr
        # 객관성 가드 유지.
        assert "절대 금지: 점수" in instr

    def test_chain_rule_reaches_prompt(self, tmp_path, monkeypatch) -> None:
        """_COACH_SYSTEM_INSTRUCTION prefix 경유 — 실제 Gemini 프롬프트에 지시 도달."""
        stub = _StubCall([_ok_payload()])
        _patch_call(monkeypatch, stub)

        writer = GeminiCoachWriter()
        writer.write(_context(tmp_path))

        assert "무엇 때문에" in stub.prompts[0]
        assert "상태 서술만 있는 explanation" in stub.prompts[0]

    def test_vision_fault_hint_promoted_to_chain_start(
        self, tmp_path, monkeypatch
    ) -> None:
        """visionFault 가설이 '원인 사슬 출발점' 지시로 승격 ('참고' 힌트 아님)."""
        stub = _StubCall([_ok_payload()])
        _patch_call(monkeypatch, stub)

        ctx = _context(tmp_path)
        ctx["visionFault"] = {
            "rootCauseHypotheses": [{"text": "코어 힘이 부족해 골반이 처진 것으로 보임"}],
        }
        writer = GeminiCoachWriter()
        writer.write(ctx)

        assert "출발점" in stub.prompts[0]

    def test_vision_fault_absent_prompt_unchanged(
        self, tmp_path, monkeypatch
    ) -> None:
        """(c) visionFault 부재 — 원인 단서 섹션 미주입 + 크래시 0 (graceful 불변)."""
        stub = _StubCall([_ok_payload()])
        _patch_call(monkeypatch, stub)

        writer = GeminiCoachWriter()
        writer.write(_context(tmp_path))

        assert "비전 분석 원인 단서" not in stub.prompts[0]
        assert "출발점" not in stub.prompts[0]


class TestFirestoreAdminGeminiBKwarg:
    """firestore_admin.complete_analysis(gemini_b=...) Firestore set payload 에 `geminiB` 박힘."""

    def test_complete_analysis_accepts_gemini_b_kwarg(self, monkeypatch) -> None:
        from sunity_shared import firestore_admin

        captured: dict[str, Any] = {}

        class _FakeDoc:
            def set(self, payload, merge=True):  # noqa: D401
                captured["payload"] = payload

        monkeypatch.setattr(firestore_admin, "_doc", lambda _p: _FakeDoc())

        gemini_b_payload = {
            "model": "gemini-3.1-pro-preview",
            "latencyMs": 12000,
            "tokensUsed": 0,
            "judgeScore": None,
            "fallback": None,
            "fallbackReason": None,
            "causes": [
                {"title": "고관절 가동", "explanation": "고관절 굴곡 제한", "fix": "강사 권고"},
            ],
            "coachNote": "강사와 함께 영상으로 확인.",
        }

        firestore_admin.complete_analysis(
            "uid-x",
            "an-x",
            result={"overall": 80},
            gemini_b=gemini_b_payload,
        )

        payload = captured["payload"]
        assert "geminiB" in payload
        assert payload["geminiB"] == gemini_b_payload

    def test_complete_analysis_gemini_b_none_omits_field(self, monkeypatch) -> None:
        """gemini_b=None 시 Firestore payload 에 geminiB 박힘 X."""
        from sunity_shared import firestore_admin

        captured: dict[str, Any] = {}

        class _FakeDoc:
            def set(self, payload, merge=True):  # noqa: D401
                captured["payload"] = payload

        monkeypatch.setattr(firestore_admin, "_doc", lambda _p: _FakeDoc())

        firestore_admin.complete_analysis(
            "uid-x",
            "an-x",
            result={"overall": 80},
            gemini_b=None,
        )

        assert "geminiB" not in captured["payload"]


class TestB3SignatureRegression:
    """B3 hard gate — `inspect.signature(GeminiCoachWriter.write).parameters` 가
    `CerebrasCoachWriter.write` 와 100% 동일.
    """

    def test_signature_matches_cerebras(self) -> None:
        import inspect
        from sunity_shared.analysis.coach_writer import CerebrasCoachWriter

        sig_gemini = inspect.signature(GeminiCoachWriter.write)
        sig_cerebras = inspect.signature(CerebrasCoachWriter.write)
        assert list(sig_gemini.parameters) == ["self", "context"]
        assert list(sig_cerebras.parameters) == ["self", "context"]
        # 양쪽 정확히 같은 파라미터 이름 + 갯수.
        assert list(sig_gemini.parameters) == list(sig_cerebras.parameters)
