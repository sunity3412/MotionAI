"""Phase 7 canned string mapping table.

research §10.1 권장 카피 4종 톤 정합 + §10.3 금지 6종 grep gate. Sunity 추가 톤 룰
3종: 가능성 언어 ("~로 보이네요") / AI = 강사 보조 도구 톤 / 부위별 원인 언어
(고관절·코어·내전근 등). per D-07-B2 + D-07-D1.

iteration 2 (2026-06-08) cross-AI review fix:
- CR-01: render_finding_copy(used_reference_fallback: bool = False) — fallback path
  시 mode prefix 결합 없는 단일 카피 (None, str) 반환. fixture #6 exact match.
- CR-02: 12 global keys 추가 — joint_key=None 으로 emit 되는 4 deficit
  (clean_lines / extension / posture / body_placement) × 3 category 박제.
  pose_reliability_low 는 기존 global 유지. 총 21 → 33 카피.
- WR-03: _EMPTY_FOCUS_FALLBACK 상수 — Plan 02 classify_findings 가 recommended_focus[]
  빈 list 일 때 활용.

per Plan 07-01 Task 2 + .planning/phases/07-difference-classification/07-RESEARCH.md
§"Canned Copy Mapping Table" + §"Initial Canned String Draft".

박제 메모리 정합:
  - [[no-baekje-filler]]: canned string 안 "박제" 단어 금지 — FORBIDDEN_PHRASES_SUNITY.
  - [[mode3-progress-not-similarity]]: "%일치"/"유사도" 금지 — FORBIDDEN_PHRASES_SUNITY.
  - [[feedback-no-echo-confirm]]: AI = 강사 보조 도구 톤.
  - [[feedback-analysis-first]]: 부위별 원인 언어 (수치 단독 X).
  - [[ipsf-5-track-scoring]]: mode3_first Page 9 단독 path fallback (CR-01).
"""

from __future__ import annotations

import logging
from typing import Literal

from .skeleton import JOINT_LABEL_KO  # noqa: F401 — Phase 11 LLM 풍부화 layer 활용 박제


_log = logging.getLogger(__name__)


# ── Type aliases ────────────────────────────────────────────────────────

Category = Literal["body_type_allowed", "needs_adjustment", "uncertain"]
JointGroup = Literal["arm", "leg", "torso", "pole_axis", "global"]
ComparisonType = Literal["mode1", "mode3_first", "mode3_progress"]


# ── Mode prefix (D-07-D3) ───────────────────────────────────────────────

# recommendation 앞에 prepend. interpretation 은 mode 무관 (현상 해석은 같음 — D-07-D3).
_MODE_PREFIX: dict[ComparisonType, str] = {
    "mode1": "정은지 선수 영상 기준으로 보면",
    "mode3_first": "세계 심사 기준 (IPSF) 으로 보면",
    "mode3_progress": "이전 영상 대비",
}


# ── CR-01 fix: used_reference_fallback=True path 의 단일 fallback 카피 ──

# mode3_first + Gemini 매칭 실패 시 — Page 9 절대 트랙 단독 적용 (D-06-B1).
# deficit 별 해석 X (None) + 단일 recommendation 문장.
# fixture #6 expected.recommendation 과 exact match 필수.
_USED_REFERENCE_FALLBACK_RECOMMENDATION: str = (
    "이 동작은 기준 영상이 없어, AI 가 IPSF 절대 기준만으로 분석했어요. "
    "강사와 함께 확인 권유드려요."
)


# ── WR-03 fix: recommended_focus[] 빈 list 일 때 fallback (Plan 02 활용) ─

_EMPTY_FOCUS_FALLBACK: str = (
    "현재 영상에서 즉시 보정할 항목이 명확히 보이지 않아요. "
    "강사와 함께 다음 단계를 정해보세요."
)


# ── Canned templates: (deficit_code, category, joint_group) → (interpretation, recommendation) ──

# CR-02 fix: 33 카피 (21 기존 + 12 신규 global).
#   기존 21:
#     knee_toe_alignment × 3 × leg = 3
#     clean_lines × 3 × arm = 3
#     clean_lines × 3 × leg = 3
#     extension × 3 × torso = 3
#     posture × 3 × arm = 3
#     body_placement × 3 × pole_axis = 3
#     pose_reliability_low × 3 × global = 3
#   신규 12 (joint_key=None emit 케이스 대응 — Phase 6 line 1027/1056/1076/1102):
#     clean_lines × 3 × global = 3
#     extension × 3 × global = 3
#     posture × 3 × global = 3
#     body_placement × 3 × global = 3
#
# 톤 룰 (research §10.1 + Sunity 추가 D-07-D1):
#   - 가능성 언어 ("~로 보이네요" / "~일 가능성이 있어요")
#   - AI = 강사 보조 도구 ("강사와 함께 확인 권유")
#   - 부위별 원인 (고관절·후굴·코어·내전근·전완근·광배·흉곽·골반·견갑)
_COPY_TEMPLATES: dict[tuple[str, Category, JointGroup], tuple[str, str]] = {
    # ── knee_toe_alignment (leg) ─────────────────────────────────────
    ("knee_toe_alignment", "body_type_allowed", "leg"): (
        "다리 길이 비율 차이로 무릎-발끝 정렬에 작은 차이가 보일 수 있어요.",
        "지금 자세는 체형 범위 안에서 자연스러워 보이네요. 무리해서 발끝을 맞추기보다 무릎 안정성에 집중해 보세요.",
    ),
    ("knee_toe_alignment", "needs_adjustment", "leg"): (
        "다리 라인 정렬이 체형 차이만으로는 설명되기 어려운 흐름이에요.",
        "무릎과 발끝이 한 선 위에 놓이도록 고관절 회전을 먼저 정리하는 게 우선으로 보입니다.",
    ),
    ("knee_toe_alignment", "uncertain", "leg"): (
        "다리 영역에서 가림이나 회전이 있어 AI 가 정렬을 확신하기 어려웠어요.",
        "이 부분은 강사와 함께 측면 각도에서 한 번 더 확인해 보시는 걸 권해요.",
    ),
    # ── clean_lines (arm) ────────────────────────────────────────────
    ("clean_lines", "body_type_allowed", "arm"): (
        "팔 길이 차이로 손 위치가 조금 다르게 보일 수 있어요.",
        "당기는 방향과 어깨 안정성이 유지되고 있으니, 손 모양 자체에 너무 매달리지 마세요.",
    ),
    ("clean_lines", "needs_adjustment", "arm"): (
        "팔 펴짐이 체형 차이만으로는 설명되기 어려운 정도예요.",
        "광배와 전완근으로 끌어내리는 감각을 먼저 잡으면 팔꿈치까지 자연스럽게 펴질 가능성이 있어요.",
    ),
    ("clean_lines", "uncertain", "arm"): (
        "팔 영역 신뢰도가 낮아 AI 가 펴짐 정도를 확신하기 어려웠어요.",
        "강사와 함께 정면 영상에서 팔 라인을 한 번 더 확인해 주세요.",
    ),
    # ── clean_lines (leg) — expects_extension 이 다리 ─────────────────
    ("clean_lines", "body_type_allowed", "leg"): (
        "다리 비율 차이로 무릎 펴짐 정도가 다르게 보일 수 있어요.",
        "다리 라인은 현재 체형 범위 안에서 자연스러운 흐름이니, 발끝까지 길게 뻗는 감각에 집중해 보세요.",
    ),
    ("clean_lines", "needs_adjustment", "leg"): (
        "다리 펴짐이 체형 차이로 설명되기 어려운 정도예요.",
        "햄스트링과 종아리 가동성을 점검해 보면 무릎까지 완전히 펴지는 길이 보일 수 있어요.",
    ),
    ("clean_lines", "uncertain", "leg"): (
        "다리 영역에서 가림이 있어 AI 가 펴짐을 확신하기 어려웠어요.",
        "강사와 함께 측면 영상에서 다리 라인을 다시 확인해 주세요.",
    ),
    # ── clean_lines (global) — CR-02 fix, joint_key=None emit ─────────
    ("clean_lines", "body_type_allowed", "global"): (
        "팔과 다리 비율 차이로 전체 라인이 조금 다르게 보일 수 있어요.",
        "전반적인 펴짐 흐름은 체형 범위 안에서 자연스러워 보이네요. 무리하기보다 호흡과 안정성에 집중해 보세요.",
    ),
    ("clean_lines", "needs_adjustment", "global"): (
        "팔과 다리 라인이 곧게 펴진 모양에서 체형 차이만으로 설명되기 어렵게 벗어나 보여요.",
        "광배와 햄스트링 가동성을 함께 점검하면 전체 라인이 자연스럽게 살아날 가능성이 있어요.",
    ),
    ("clean_lines", "uncertain", "global"): (
        "전반적인 펴짐 정도를 AI 가 확신하기 어려웠어요.",
        "강사와 함께 정면과 측면 각도에서 라인을 다시 확인해 주세요.",
    ),
    # ── extension (torso) ────────────────────────────────────────────
    ("extension", "body_type_allowed", "torso"): (
        "몸통 비율 차이로 척추 라인이 조금 다르게 보일 수 있어요.",
        "현재 자세에서는 흉곽 방향과 골반 고정이 우선이고, 척추 곡선 자체에 매달릴 필요는 없어 보이네요.",
    ),
    ("extension", "needs_adjustment", "torso"): (
        "척추와 목 라인이 체형 차이만으로는 설명되기 어렵게 굽어 있어요.",
        "흉곽을 열고 코어로 골반을 받쳐주는 감각을 먼저 잡으면 후굴 라인이 자연스럽게 살아날 가능성이 있어요.",
    ),
    ("extension", "uncertain", "torso"): (
        "몸통 영역에서 가림이 있어 AI 가 척추 라인을 확신하기 어려웠어요.",
        "강사와 함께 측면 영상에서 후굴 라인을 다시 확인해 주세요.",
    ),
    # ── extension (global) — CR-02 fix ───────────────────────────────
    ("extension", "body_type_allowed", "global"): (
        "전체적인 신전 라인이 체형 비율 차이로 다르게 보일 수 있어요.",
        "지금 흐름은 체형 범위 안에서 자연스러워 보이니, 흉곽 방향과 골반 고정에 집중해 보세요.",
    ),
    ("extension", "needs_adjustment", "global"): (
        "전체적인 신전 라인이 체형 차이만으로는 설명되기 어렵게 짧아진 흐름이에요.",
        "코어로 골반을 받치고 흉곽을 여는 감각을 먼저 정리하면 신전이 자연스럽게 살아날 가능성이 있어요.",
    ),
    ("extension", "uncertain", "global"): (
        "전체 신전 라인을 AI 가 확신하기 어려웠어요.",
        "강사와 함께 측면 영상에서 신전 흐름을 다시 확인해 주세요.",
    ),
    # ── posture (arm = shoulder) ─────────────────────────────────────
    ("posture", "body_type_allowed", "arm"): (
        "어깨 너비/골반 비율 차이로 좌우 어깨 깊이가 조금 다르게 보일 수 있어요.",
        "지금 라운드숄더가 체형 범위 안일 가능성이 있으니, 견갑 안정성을 우선으로 가져가세요.",
    ),
    ("posture", "needs_adjustment", "arm"): (
        "좌우 어깨 깊이 차이가 체형 차이만으로는 설명되기 어려워 보여요.",
        "견갑을 끌어내리고 흉곽을 여는 감각을 먼저 정리해 보면 라운드숄더가 풀릴 가능성이 있어요.",
    ),
    ("posture", "uncertain", "arm"): (
        "어깨 영역 신뢰도가 낮아 AI 가 깊이 차이를 확신하기 어려웠어요.",
        "강사와 함께 정면 영상에서 어깨 라인을 다시 확인해 주세요.",
    ),
    # ── posture (global) — CR-02 fix ─────────────────────────────────
    ("posture", "body_type_allowed", "global"): (
        "좌우 어깨 깊이 차이가 체형 비율로 작게 보일 수 있어요.",
        "현재 자세는 체형 범위 안에서 자연스러워 보이니, 견갑 안정성에 집중해 보세요.",
    ),
    ("posture", "needs_adjustment", "global"): (
        "좌우 어깨 깊이 차이가 체형 차이만으로는 설명되기 어려운 흐름이에요.",
        "견갑과 흉곽을 함께 정리해 보면 좌우 균형이 자연스럽게 잡힐 가능성이 있어요.",
    ),
    ("posture", "uncertain", "global"): (
        "좌우 어깨 깊이를 AI 가 확신하기 어려웠어요.",
        "강사와 함께 정면 영상에서 어깨 라인을 다시 확인해 주세요.",
    ),
    # ── body_placement (pole_axis) ───────────────────────────────────
    ("body_placement", "body_type_allowed", "pole_axis"): (
        "체형 차이로 골반의 폴 축 거리가 조금 다르게 보일 수 있어요.",
        "현재 위치는 체형 범위 안에서 자연스러워 보이니, 무리해서 폴에 붙이기보다 골반 고정에 집중해 보세요.",
    ),
    ("body_placement", "needs_adjustment", "pole_axis"): (
        "골반이 폴 축에서 바깥으로 빠지는 흐름이 체형 차이만으로는 설명되기 어려워요.",
        "코어로 골반을 폴 쪽으로 끌어붙이는 감각을 먼저 잡는 게 우선으로 보입니다.",
    ),
    ("body_placement", "uncertain", "pole_axis"): (
        "폴 축 검출 신뢰도가 낮아 AI 가 위치 차이를 확신하기 어려웠어요.",
        "강사와 함께 정면+측면 영상에서 골반 위치를 다시 확인해 주세요.",
    ),
    # ── body_placement (global) — CR-02 fix ──────────────────────────
    ("body_placement", "body_type_allowed", "global"): (
        "몸통 위치가 폴 축에서 체형 비율 차이로 조금 다르게 보일 수 있어요.",
        "현재 위치는 체형 범위 안에서 자연스러워 보이니, 골반 고정 감각에 집중해 보세요.",
    ),
    ("body_placement", "needs_adjustment", "global"): (
        "몸통 위치가 폴 축에서 체형 차이만으로는 설명되기 어렵게 벗어나 있어요.",
        "코어로 골반을 폴 쪽으로 끌어붙이는 감각을 먼저 정리하면 위치가 안정될 가능성이 있어요.",
    ),
    ("body_placement", "uncertain", "global"): (
        "몸통 위치 차이를 AI 가 확신하기 어려웠어요.",
        "강사와 함께 정면+측면 영상에서 위치를 다시 확인해 주세요.",
    ),
    # ── pose_reliability_low (global) ────────────────────────────────
    # 의미상 발생 거의 없음 (deduction -0.5 → 임계 0.2 초과 → needs_adjustment 자연).
    # body_type_allowed 는 안전 fallback 만.
    ("pose_reliability_low", "body_type_allowed", "global"): (
        "영상 신뢰도가 일부 낮지만 큰 영향은 없어 보이네요.",
        "조명이 충분하고 가림이 적은 환경에서 한 번 더 촬영해 주시면 분석이 더 정확해질 거예요.",
    ),
    ("pose_reliability_low", "needs_adjustment", "global"): (
        "영상 일부 구간에서 AI 가 자세를 정확히 보기 어려웠어요.",
        "조명·가림·카메라 거리를 조정해 다시 촬영하시면 더 정확한 분석을 받으실 수 있어요.",
    ),
    ("pose_reliability_low", "uncertain", "global"): (
        "영상 전반의 신뢰도가 낮아 AI 분석이 전체적으로 확신을 갖기 어려웠어요.",
        "강사와 함께 영상 품질을 점검하고 재촬영을 고려해 주세요.",
    ),
}


# ── Forbidden phrases (grep gate — D-07-D2) ─────────────────────────────

# research §10.3 금지 6종 — 카피 회귀 차단.
FORBIDDEN_PHRASES: tuple[str, ...] = (
    "프로보다 못합",
    "정답 자세가 아닙",
    "근육량이 부족",
    "체형이 안 맞",
    "대회 총점",
    "감점입니다",
)

# Sunity 추가 금지 (memory 박제 정합) — 3종.
FORBIDDEN_PHRASES_SUNITY: tuple[str, ...] = (
    # NOTE — 본 tuple 항목은 forbidden literal. AST 기반 grep gate 가 본 tuple
    # 자체는 검사 scope 밖으로 두고, _COPY_TEMPLATES + _MODE_PREFIX 의 string
    # constant 만 iterate. tuple 항목으로 두기 위해 본 모듈 헤더 docstring 안의
    # 단어는 (3-quote 안에 있고 dict literal 안에 있지 않으므로) 게이트 무관.
    "박제",  # [[no-baekje-filler]] — canned 안 "박제" 단어 금지
    "%일치",  # [[mode3-progress-not-similarity]] — mode3 = 절대 지표 델타
    "유사도",  # 동일
)


# ── render_finding_copy (D-07-D3 + CR-01 fix) ───────────────────────────


def render_finding_copy(
    deficit_code: str,
    category: Category,
    joint_group: JointGroup,
    comparison_type: ComparisonType,
    *,
    used_reference_fallback: bool = False,
) -> tuple[str | None, str]:
    """(interpretation, recommendation) Korean canned string lookup.

    Args:
        deficit_code: BodyComparisonFinding.deficit_code 6 enum 중 하나.
        category: 분류 결과 — body_type_allowed / needs_adjustment / uncertain.
        joint_group: arm / leg / torso / pole_axis / global. Plan 02 의
            _resolve_joint_group 결과.
        comparison_type: mode1 / mode3_first / mode3_progress (W1 정합).
        used_reference_fallback: keyword-only. True 시 deficit 별 해석 무시 +
            단일 unprefixed 카피 반환 (CR-01 fix path — fixture #6 정합).

    Returns:
        (interpretation, recommendation):
            interpretation = Korean canned string 또는 None (CR-01 fallback path).
            recommendation = Korean canned string. mode prefix prepended (단,
                fallback path 에서는 prepend 안 함).

    fallback (default path): 키 미발견 시 generic 카피 + WARNING log.
    """
    # CR-01 fix path — mode3_first + Gemini 매칭 실패 시 Page 9 단독 적용.
    # deficit / category / joint_group / comparison_type 입력 무관 단일 fallback.
    # interpretation = None (deficit 별 해석 X). recommendation = unprefixed.
    if used_reference_fallback:
        return (None, _USED_REFERENCE_FALLBACK_RECOMMENDATION)

    # 기본 path — _COPY_TEMPLATES lookup.
    key = (deficit_code, category, joint_group)
    pair = _COPY_TEMPLATES.get(key)
    if pair is None:
        # graceful fallback — 키 누락 시 generic 톤 유지 (Phase 11 LLM 풍부화 전).
        _log.warning(
            "render_finding_copy: key not found key=%r — graceful fallback",
            key,
        )
        return (
            "이 부분은 AI 분석 결과예요.",
            "강사와 함께 영상을 한 번 더 확인해 보세요.",
        )

    interp, recom = pair
    # mode prefix — recommendation 만 prepend (interpretation 은 mode 무관 — D-07-D3).
    prefix = _MODE_PREFIX.get(comparison_type, "")
    if prefix and not recom.startswith(prefix):
        recom = f"{prefix} {recom}"
    return (interp, recom)


__all__ = (
    "Category",
    "JointGroup",
    "ComparisonType",
    "FORBIDDEN_PHRASES",
    "FORBIDDEN_PHRASES_SUNITY",
    "_EMPTY_FOCUS_FALLBACK",
    "render_finding_copy",
)
