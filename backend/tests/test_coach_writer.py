"""Cerebras CoachWriter prompt-building 단위테스트 (23-02 Task 5, D-10 HIGH-1 + MED-2).

vision-fault root-cause(to_coach_context() 의 visionFault 키)가 실제 _build_prompt
출력(causes 섹션)에 렌더되는지 검증한다. 키 주입만으로는 graceful 무시되어 false-pass
되므로(MED-2), 최종 tip 이 아니라 **prompt 빌드 단계**를 직접 inspect 한다.

PYTHONPATH=backend/shared/python 컨벤션.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import coach_writer  # noqa: E402


_JOINTS = [
    {"key": "left_knee", "labelKo": "왼쪽 무릎", "deviation_deg": 30.0, "direction": "굽음"},
]


def test_build_prompt_renders_vision_fault_root_cause():
    """_build_prompt 가 visionFault root-cause 텍스트를 causes 참고 섹션에 렌더 (BLOCKER fix)."""
    vision_fault = {
        "rootCauseHypotheses": [
            {"text": "폴 밀착이 풀린 것으로 보임",
             "faultKey": {"part_scope": "upper_body", "side": "left",
                          "keypoint_set": "arm", "fault_kind": "pole_gap_or_bent"},
             "supportCount": 2},
        ],
    }
    prompt = coach_writer._build_prompt(_JOINTS, vision_fault=vision_fault)
    assert "폴 밀착이 풀린 것으로 보임" in prompt
    assert "가능한 원인" in prompt


def test_build_prompt_without_vision_fault_unchanged():
    """visionFault 부재 시 원인 섹션 미주입 (기존 동작 불변)."""
    prompt = coach_writer._build_prompt(_JOINTS)
    assert "비전 분석이 관찰한 가능한 원인" not in prompt


def test_build_prompt_empty_root_cause_no_section():
    """rootCauseHypotheses 빈 list → 원인 섹션 미주입 (graceful)."""
    prompt = coach_writer._build_prompt(_JOINTS, vision_fault={"rootCauseHypotheses": []})
    assert "비전 분석이 관찰한 가능한 원인" not in prompt


def test_format_vision_fault_lines_skips_blank_text():
    """빈 text 가설은 라인에서 제외 (slop 0)."""
    lines = coach_writer._format_vision_fault_lines(
        {"rootCauseHypotheses": [{"text": ""}, {"text": "힘 부족으로 보임"}]}
    )
    joined = "\n".join(lines)
    assert "힘 부족으로 보임" in joined
    # 빈 text 는 '- ' 단독 라인으로 새지 않는다.
    assert "- \n" not in joined and not joined.endswith("- ")


# ── quick-260704-fwb — 처방 구조 (원인 기전 사슬 + 구체 처방) 프롬프트 가드 ──


def test_system_prompt_enforces_causal_chain():
    """(a) 기전 사슬 지시 라인이 시스템 프롬프트에 포함."""
    assert "무엇 때문에" in coach_writer._SYSTEM
    assert "무너지" in coach_writer._SYSTEM
    # fix = 구체 행동 지시.
    assert "구체 행동 지시" in coach_writer._SYSTEM


def test_system_prompt_bans_state_only_narration():
    """(b) 상태-서술-금지 라인 포함 (상태 서술 단독 explanation 차단)."""
    assert "상태 서술만 있는 문장 금지" in coach_writer._SYSTEM
    # 기존 fabrication 가드 유지 (측정 안 된 수치/부위 생성 금지).
    assert "임의 수치" in coach_writer._SYSTEM
    assert "측정되지 않은 수치나 부위" in coach_writer._SYSTEM


def test_build_prompt_without_vision_fault_no_new_sections():
    """(c) vision_fault 없는 입력 — 유저 프롬프트에 비전/실측 섹션 미주입 (graceful 불변)."""
    prompt = coach_writer._build_prompt(_JOINTS)
    assert "비전 분석" not in prompt
    assert "실측 관찰" not in prompt
    # 기존 구조 유지.
    assert "left_knee" in prompt
    assert "JSON 형식" in prompt


def test_vision_hint_promoted_to_chain_start():
    """rootCauseHypotheses 가 '원인 사슬 출발점' 지시로 승격 ('참고' 힌트 아님)."""
    prompt = coach_writer._build_prompt(
        _JOINTS,
        vision_fault={"rootCauseHypotheses": [{"text": "코어 힘 부족으로 보임"}]},
    )
    assert "코어 힘 부족으로 보임" in prompt
    assert "출발점" in prompt


def test_build_prompt_renders_supported_differences_as_evidence():
    """supportedDifferences 서술 텍스트가 실측 근거 라인으로 렌더."""
    vision_fault = {
        "rootCauseHypotheses": [{"text": "코어 힘 부족으로 보임"}],
        "supportedDifferences": [
            {"body_part": "왼쪽 다리", "fault_state": "스플릿 각도가 기준보다 좁음",
             "correct_state": "양다리를 곧게 펴 벌림"},
        ],
    }
    prompt = coach_writer._build_prompt(_JOINTS, vision_fault=vision_fault)
    assert "스플릿 각도가 기준보다 좁음" in prompt
    assert "실측 관찰" in prompt
    assert "양다리를 곧게 펴 벌림" in prompt


def test_build_prompt_supported_differences_absent_no_crash():
    """(d) supportedDifferences 부재 시 크래시 0 + 실측 섹션 미주입 (기존 동작 불변)."""
    vision_fault = {"rootCauseHypotheses": [{"text": "힘 부족으로 보임"}]}
    prompt = coach_writer._build_prompt(_JOINTS, vision_fault=vision_fault)
    assert "힘 부족으로 보임" in prompt
    assert "실측 관찰" not in prompt


def test_build_prompt_malformed_supported_differences_graceful():
    """supportedDifferences 형상 불일치 (non-dict / 빈 필드) — 크래시 0, 유효분만 렌더."""
    vision_fault = {
        "rootCauseHypotheses": [{"text": "힘 부족으로 보임"}],
        "supportedDifferences": ["not-a-dict", None, {"body_part": "팔"}, 42],
    }
    prompt = coach_writer._build_prompt(_JOINTS, vision_fault=vision_fault)
    assert "힘 부족으로 보임" in prompt
    # fault_state 없는 항목은 렌더 X → 실측 섹션 자체 미주입.
    assert "실측 관찰" not in prompt


# ── quick-260831-bjj — belle 08-17 판독 축(postureAxes) 프롬프트 렌더 ──


_SIG_POSTURE = {
    "uprightness": {"studentDeg": 25.0, "referenceDeg": 10.0,
                    "deltaDeg": 15.0, "significant": True},
    "headSpine": {"studentDeg": 160.0, "referenceDeg": 175.0,
                  "deltaDeg": -15.0, "significant": True},
}


def test_build_prompt_renders_significant_posture_axes():
    """significant + 학생 열위 방향 → 인과형 지시 + 'N° 정도' 보조 수치 렌더."""
    prompt = coach_writer._build_prompt(_JOINTS, posture_axes=_SIG_POSTURE)
    assert "자세 축 실측" in prompt
    assert "상체를 세워" in prompt          # 인과형 지시 (상태 서술 단독 금지)
    assert "고개를 들어" in prompt          # belle elbow 원문 방향
    assert "15° 정도" in prompt             # 수치는 보조 (N° 정도 문법)


def test_build_prompt_posture_none_byte_identical():
    """postureAxes None → 프롬프트 byte-불변 (zero behavior change)."""
    assert coach_writer._build_prompt(_JOINTS, posture_axes=None) == \
        coach_writer._build_prompt(_JOINTS)
    assert "자세 축 실측" not in coach_writer._build_prompt(_JOINTS)


def test_build_prompt_posture_insignificant_byte_identical():
    """전부 insignificant → byte-불변 (잡음 델타는 지시로 승격하지 않는다)."""
    insig = {
        "uprightness": {"studentDeg": 12.0, "referenceDeg": 10.0,
                        "deltaDeg": 2.0, "significant": False},
        "headSpine": None,
    }
    assert coach_writer._build_prompt(_JOINTS, posture_axes=insig) == \
        coach_writer._build_prompt(_JOINTS)


def test_build_prompt_posture_student_better_direction_not_rendered():
    """학생 우위 방향(uprightness delta<0 / headSpine delta>0) → 미발화.

    결함 코칭 목적 — 기준 우위 전제. 학생이 더 꼿꼿/더 1자면 교정 지시가 성립하지
    않으므로 렌더하지 않는다 (프롬프트 byte-불변).
    """
    student_better = {
        "uprightness": {"studentDeg": 5.0, "referenceDeg": 20.0,
                        "deltaDeg": -15.0, "significant": True},
        "headSpine": {"studentDeg": 178.0, "referenceDeg": 165.0,
                      "deltaDeg": 13.0, "significant": True},
    }
    assert coach_writer._build_prompt(_JOINTS, posture_axes=student_better) == \
        coach_writer._build_prompt(_JOINTS)


def test_write_passes_posture_axes_to_prompt(monkeypatch):
    """CerebrasCoachWriter.write 가 context['postureAxes'] 를 _build_prompt 에 전달."""
    captured = {}

    def _spy_build_prompt(joints, **kwargs):
        captured["posture_axes"] = kwargs.get("posture_axes")
        return "stub-prompt"

    monkeypatch.setattr(coach_writer, "_build_prompt", _spy_build_prompt)

    class _FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    class _Msg:
                        content = '{"left_knee": {"detail": "x"}}'

                    class _Choice:
                        message = _Msg()

                    class _Resp:
                        choices = [_Choice()]

                    return _Resp()

    writer = coach_writer.CerebrasCoachWriter.__new__(coach_writer.CerebrasCoachWriter)
    writer._model = "gpt-oss-120b"
    writer._client = _FakeClient()
    writer.write({"mode": "mode1", "joints": _JOINTS, "postureAxes": _SIG_POSTURE})
    assert captured["posture_axes"] == _SIG_POSTURE


def test_write_passes_vision_fault_to_prompt(monkeypatch):
    """CerebrasCoachWriter.write 가 context['visionFault'] 를 _build_prompt 에 전달 (실제 호출 경로)."""
    captured = {}

    def _spy_build_prompt(joints, **kwargs):
        captured["vision_fault"] = kwargs.get("vision_fault")
        return "stub-prompt"

    monkeypatch.setattr(coach_writer, "_build_prompt", _spy_build_prompt)

    class _FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    class _Msg:
                        content = '{"left_knee": {"detail": "x"}}'

                    class _Choice:
                        message = _Msg()

                    class _Resp:
                        choices = [_Choice()]

                    return _Resp()

    writer = coach_writer.CerebrasCoachWriter.__new__(coach_writer.CerebrasCoachWriter)
    writer._model = "gpt-oss-120b"
    writer._client = _FakeClient()
    ctx = {
        "mode": "mode1",
        "joints": _JOINTS,
        "visionFault": {"rootCauseHypotheses": [{"text": "코어 약화로 보임"}]},
    }
    writer.write(ctx)
    assert captured["vision_fault"] == {"rootCauseHypotheses": [{"text": "코어 약화로 보임"}]}
