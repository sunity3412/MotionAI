"""Phase 9 ForcePatternFinding canned KO interpretation mapping (D-09-D2 / D-09-D3).

Stateless singleton — caller-controlled input 0. force_pattern.py 가
`force_pattern_canned_text` / `joint_hint_for` / `fallback_body` lookup helper
호출. Phase 7 copy_templates.py 패턴 1:1 mirror — AST grep gate
(test_force_pattern_copy_no_forbidden.py) 가 단정 표현 회귀 차단.

박제 메모리 정합:
  - [[no-baekje-filler]]: canned 본문 안 '박제' 단어 0 회 (belle 검수 단계 확인).
  - [[mode3-progress-not-similarity]]: '%일치' / '유사도' 단어 X.
  - [[feedback-analysis-first]]: 가능성 언어 + 부위별 원인.
  - [[feedback-no-echo-confirm]]: AI = 강사 보조 도구 톤.

R2 회귀 차단 — force_pattern_copy.py 는 force_pattern.py 를 runtime import 하지
않는다. 역방향이면 import cycle. 따라서 ForceSourceSignal / ModeContext 는
local Literal alias 로 duplicate 박제하고, lockstep test 가 force_pattern.py 의
frozenset 과 1:1 일치를 강제한다.

R8/R9 narrowing — MappingProxyType wrap 은 `_FORCE_PATTERN_COPY` 에만 적용.
`_MODE_PREFIX` 와 `_JOINT_HINT_BY_SIGNAL` 은 plain dict 유지 (작은 lookup +
caller-controlled input 표면 X). 18 canned 본문이 high-value invariant.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Literal, Mapping

# Type hint 호환만 보장 — runtime import 0 (cycle 차단).
if TYPE_CHECKING:  # pragma: no cover - type-only
    from .force_pattern import ForceSourceSignal as _FSS_Type  # noqa: F401
    from .force_pattern import ModeContext as _MC_Type  # noqa: F401


ForceSourceSignal = Literal[
    "axis_tilt",
    "pelvis_drop",
    "late_contact",
    "high_jitter",
    "high_jerk",
    "abnormal_release",
]
"""6 source signal Literal alias (force_pattern.py 와 lockstep)."""

ModeContext = Literal["mode1", "mode3_first", "mode3_progress"]
"""3 mode context Literal alias (force_pattern.py 와 lockstep)."""


# ── Mode prefix (D-09-D2) — trailing space + comma 포함 ──────────────────
#
# 각 _FORCE_PATTERN_COPY 본문은 _MODE_PREFIX[mode_context] 로 시작해야 한다
# (test_mode_prefix_consistency_invariant 가 강제).

_MODE_PREFIX: dict[ModeContext, str] = {
    "mode1": "정은지 선수 기준 패턴과 비교했을 때, ",
    "mode3_first": "이번 첫 분석에서, ",
    "mode3_progress": "지난 영상 대비, ",
}


# ── 18 canned KO interpretation (D-09-D2) ────────────────────────────────
#
# 6 sourceSignal × 3 modeContext = 18 entry. 각 본문 톤 = research §10.1 가능성
# 언어 + 부위별 원인 어휘 + 강사 보조 톤. belle 박제 검수는 follow-up.
#
# Body 작성 금기 (D-09-D3 — AST gate 차단):
#   - '박제' 단어 ([[no-baekje-filler]])
#   - '%일치' / '유사도' ([[mode3-progress-not-similarity]])
#   - 8 forbidden substring + 2 regex (근육 힘 방향.*확정 / \d+%\s*감점)

_FORCE_PATTERN_COPY_DATA: dict[tuple[ForceSourceSignal, ModeContext], str] = {
    # axis_tilt — 코어 / 중심축 / 척추 라인 / 고정 감각
    ("axis_tilt", "mode1"): (
        "정은지 선수 기준 패턴과 비교했을 때, 중심축이 흔들리며 코어 고정이 "
        "약해지는 흐름으로 보여요."
    ),
    ("axis_tilt", "mode3_first"): (
        "이번 첫 분석에서, 척추 라인이 한쪽으로 기울면서 중심축 잡기가 어려운 "
        "흐름이 나타나요."
    ),
    ("axis_tilt", "mode3_progress"): (
        "지난 영상 대비, 중심축이 더 흔들리며 코어 고정 감각을 다시 점검해 볼 "
        "수 있어요."
    ),
    # pelvis_drop — 골반 / 좌우 비대칭 / 상체 보상 / 고관절 안정
    ("pelvis_drop", "mode1"): (
        "정은지 선수 기준 패턴과 비교했을 때, 골반이 한쪽으로 내려가며 상체가 "
        "보상하는 흐름이 보여요."
    ),
    ("pelvis_drop", "mode3_first"): (
        "이번 첫 분석에서, 좌우 골반 높이가 어긋나며 고관절 안정에 부담이 가는 "
        "흐름이 나타나요."
    ),
    ("pelvis_drop", "mode3_progress"): (
        "지난 영상 대비, 골반 좌우 비대칭이 커지며 상체 보상 흐름을 다시 점검해 "
        "볼 수 있어요."
    ),
    # late_contact — 내전근 / 다리 접촉 / 레그락 타이밍 / 코어-허벅지 연결
    ("late_contact", "mode1"): (
        "정은지 선수 기준 패턴과 비교했을 때, 다리 접촉 타이밍이 늦어지며 "
        "내전근 연결이 풀리는 흐름으로 보여요."
    ),
    ("late_contact", "mode3_first"): (
        "이번 첫 분석에서, 레그락 진입 타이밍이 늦어 코어와 허벅지 연결이 "
        "약해지는 흐름이 나타나요."
    ),
    ("late_contact", "mode3_progress"): (
        "지난 영상 대비, 다리 접촉 타이밍이 더 늦어지며 내전근 활성을 다시 "
        "점검해 볼 수 있어요."
    ),
    # high_jitter — 유지 근력 / 호흡 / 떨림 / 안정성 (부위 불명확)
    ("high_jitter", "mode1"): (
        "정은지 선수 기준 패턴과 비교했을 때, 자세 유지 중 떨림이 늘어 유지 "
        "근력과 호흡 흐름을 살펴볼 만해요."
    ),
    ("high_jitter", "mode3_first"): (
        "이번 첫 분석에서, 정지 구간에서 잔떨림이 보이며 안정성이 흔들리는 "
        "흐름이 나타나요."
    ),
    ("high_jitter", "mode3_progress"): (
        "지난 영상 대비, 자세 유지 떨림이 더 늘어나며 유지 근력 흐름을 다시 "
        "점검해 볼 수 있어요."
    ),
    # high_jerk — 힘 전달 부드러움 / 가속 변화 / 균일성 (부위 불명확)
    ("high_jerk", "mode1"): (
        "정은지 선수 기준 패턴과 비교했을 때, 동작 가속 변화가 거칠어지며 힘 "
        "전달이 균일하지 않은 흐름으로 보여요."
    ),
    ("high_jerk", "mode3_first"): (
        "이번 첫 분석에서, 움직임 가속이 급변하며 힘이 부드럽게 이어지지 않는 "
        "흐름이 나타나요."
    ),
    ("high_jerk", "mode3_progress"): (
        "지난 영상 대비, 힘 전달 부드러움이 줄어들며 동작 흐름의 균일성을 "
        "다시 점검해 볼 수 있어요."
    ),
    # abnormal_release — 광배 / 견갑 / hold 중 접촉 / 그립 안정
    ("abnormal_release", "mode1"): (
        "정은지 선수 기준 패턴과 비교했을 때, 정지 구간에서 그립이 풀리며 "
        "광배 연결이 약해지는 흐름으로 보여요."
    ),
    ("abnormal_release", "mode3_first"): (
        "이번 첫 분석에서, hold 구간에서 접촉이 풀리며 견갑 안정이 흔들리는 "
        "흐름이 나타나요."
    ),
    ("abnormal_release", "mode3_progress"): (
        "지난 영상 대비, 정지 구간 그립 안정이 약해지며 광배 연결을 다시 "
        "점검해 볼 수 있어요."
    ),
}

_FORCE_PATTERN_COPY: Mapping[tuple[ForceSourceSignal, ModeContext], str] = (
    MappingProxyType(_FORCE_PATTERN_COPY_DATA)
)
"""18 canned (sourceSignal × modeContext) → KO 1 sentence. R9 — runtime mutation
차단 위해 MappingProxyType wrap. lookup helper 가 강제 사용."""


# ── jointHint 부위 어휘 (Assumption A3 / D-09-D1) ─────────────────────────

_JOINT_HINT_BY_SIGNAL: dict[ForceSourceSignal, str | None] = {
    "axis_tilt": "코어",
    "pelvis_drop": "고관절",
    "late_contact": "내전근",
    "abnormal_release": "광배",
    "high_jerk": None,
    "high_jitter": None,
}
"""6 signal → 부위 키워드 (또는 None — 부위 불명확)."""


# ── 0-finding fallback body (D-09-B4 / Open Q 3) ─────────────────────────

_FALLBACK_BODY: str = (
    "이 영상에서는 분명한 힘 흐름 이슈 신호가 보이지 않습니다. 강사와 함께 "
    "확인하는 것을 권장해요."
)
"""findings 0 개일 때 단일 fallback body. mode 분기 X (Open Q 3 — 신호 없을 때
mode prefix 도 가능성 언어로 의미가 약해지므로 단일 본문 박제)."""


# ── 금지 표현 (D-09-D3 / RESEARCH Pitfall 7) ──────────────────────────────

FORBIDDEN_PHRASES_RESEARCH: tuple[str, ...] = (
    "광배 N% 부족",
    "근력이 부족",
    "전완 힘이 약",
    "이 자세는 틀렸",
    "AI가 정확히 측정",
    "부상 위험 확정",
    "힘이 정확히",
    "프로보다 못합",
)
"""8 substring forbidden (research §10.2 6종 + Phase 9 신규 2 substring)."""

FORBIDDEN_PHRASES_PHASE9_REGEX: tuple[str, ...] = (
    r"근육 힘 방향.*확정",
    r"\d+%\s*감점",
)
"""2 regex forbidden (D-09-D3 신규).

`근육 힘 방향.*확정` — 조사 변형 (이/은/만 등) catch. SC#4 단정 표현 가드.
`\\d+%\\s*감점` — 수치 단독 감점 노출 차단 ([[mode3-progress-not-similarity]]).
"""


# ── Lookup helpers (3 public) ─────────────────────────────────────────────


def force_pattern_canned_text(
    source_signal: ForceSourceSignal, mode_context: ModeContext
) -> str:
    """Return canned KO 1-sentence interpretation. D-09-D2.

    Caller 가 force_pattern.py 의 Literal alias 와 lockstep 인 source_signal /
    mode_context 만 전달 (Literal type check 가 caller-controlled input 검증).
    KeyError 발생 시 enum drift 회귀 — lockstep test 가 차단.
    """
    return _FORCE_PATTERN_COPY[(source_signal, mode_context)]


def joint_hint_for(source_signal: ForceSourceSignal) -> str | None:
    """Return 부위 어휘 hint (Assumption A3). None when 부위 불명확."""
    return _JOINT_HINT_BY_SIGNAL[source_signal]


def fallback_body() -> str:
    """D-09-B4 / Open Q 3 — 0 finding 시 단일 fallback body."""
    return _FALLBACK_BODY


__all__ = [
    "ForceSourceSignal",
    "ModeContext",
    "FORBIDDEN_PHRASES_RESEARCH",
    "FORBIDDEN_PHRASES_PHASE9_REGEX",
    "force_pattern_canned_text",
    "joint_hint_for",
    "fallback_body",
]
