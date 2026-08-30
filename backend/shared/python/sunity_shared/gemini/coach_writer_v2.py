"""Phase 17 Wave 3 (RESEARCH §9 표기) — 영역 B 코칭 멘트 (Gemini Pro Vision).

박제 정신:
  · 17-RESEARCH §9 Wave 3 + AI-SPEC §5 E4 정합. RTMW 8 관절 deviation 수치 + 영상 결합
    → causes 3~5 + injuryRisk + coachNote 산출.
  · **B3 시그니처 hard gate**: `.write(context: dict) -> dict` —
    `sunity_shared.analysis.coach_writer.CerebrasCoachWriter.write` (L107) 와 100% 동일.
    `_process` 가 단일 `_build_coach_context()` 헬퍼로 양 writer 공유. inspect.signature 회귀
    박제 (test_pipeline_geminib_wiring.py).
  · CerebrasCoachWriter 와 dual-track — env `GEMINI_COACH_ENABLED=1` (default) 시 Gemini
    우선, 본 writer 가 graceful 폴백 시 caller (pipeline) 가 Cerebras 로 swap.
  · 반환 dict — 2차 R-W4 정합 **None 반환 박제 0**:
      - 성공: `{joint_key: {"detail": str, "detail2": {"causes": [...], "injuryRisk": str|None,
                                                     "coachNote": str}}}` (joint 키 ≥ 1)
      - 실패/graceful skip: `{}` 또는 `{"_fallbackReason": "<reason>"}` (reserved key only).
        `_process` 가 `_` prefix 키 strip 후 `assemble.build_result` 에 전달 — user-visible
        result 에 leak 0 (Codex B3 + WARNING-3 정합).
  · 강사 보조 톤 schema 강제 (E4 dimension AI-SPEC §5 박제):
      - 부위별 용어 14개 화이트리스트 — 각 cause.explanation 에 1개 이상 포함 강제.
      - coach_note 에 "강사" + "함께" + "확인" 3 단어 동시 포함 강제.
      - blocklist ("이렇게 하세요" / "틀렸습니다" / "당신은") 매치 시 ValueError.
    실패 시 1회 retry — 2회 실패 시 `{"_fallbackReason": "tone_validation_failed"}`.
  · B4 hard gate — caller 의 `local_video_path` (context["videoPath"]) 만 사용. boto3 S3
    download / pose estimate 재실행 0. video_path 누락 시 `{"_fallbackReason":
    "video_path_missing"}` (Cerebras 폴백 — text-only 코칭).

2026-06-12 e2e Issue #1 fix:
  · 이전: `_COACH_SYSTEM_INSTRUCTION` 정의만 박혀있고 호출처 0 → Gemini 가 자유 형식 응답
    → 부위별 용어/coach_note 3어휘 누락 → v4 e2e 에서 tone_validation_failed.
  · 변경: prompt 박힘 system instruction prefix + 14 용어 강제 라인 (각 cause 마다 박혀야)
    + coach_note 3 어휘 ("강사" "함께" "확인") 동시 박힘 강제 라인 + low-deviation 케이스
    "차이가 작아도 잠재 원인" 박힘 가이드. validator 박힘 그대로 유지 (강사 신뢰 hard gate).
  · 객관성 가드 ([[analysis-objectivity-no-human-scores]]) 그대로 — 점수/판단 어휘 금지.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Callable

from .client import GeminiVisionCall
from .config import resolve_model
from .schemas import CoachPayload

# quick-260831-bjj — belle 08-17 판독 축(postureAxes) 렌더는 Cerebras 와 단일 출처
# 공유 (발화 판정 로직 두 곳 중복 금지 — B3 정합. analysis.coach_writer 는 순수
# stdlib+phrasebook 이라 순환 import 0).
from sunity_shared.analysis.coach_writer import format_posture_axis_lines

# Phase 17 Plan 06B — Phoenix span event 박제 (TELEMETRY_OK gate).
try:
    from sunity_shared.eval import TELEMETRY_OK
except ImportError:  # pragma: no cover
    TELEMETRY_OK = False

if TELEMETRY_OK:
    try:
        from opentelemetry import trace as _otel_trace

        _tracer = _otel_trace.get_tracer(__name__)
    except ImportError:  # pragma: no cover
        _tracer = None
else:
    _tracer = None


log = logging.getLogger(__name__)


# ─────────────────── 강사 보조 톤 schema 박제 (E4 dimension) ───────────────────
#
# 부위별 용어 화이트리스트 14개 — PROJECT.md "고관절/후굴/코어/내전근" 4개 +
# 강사 설문조사 docs 의 부위 용어 확장. 각 cause.explanation 에 1개 이상 포함 강제.

_BODY_PART_TERMS: tuple[str, ...] = (
    "고관절",
    "후굴",
    "코어",
    "내전근",
    "외회전",
    "햄스트링",
    "견갑",
    "엉덩이 굴곡",
    "회전근개",
    "요추",
    "흉추",
    "슬괵",
    "장요근",
    "대퇴직근",
)

# coach_note 에 동시 포함되어야 하는 3 어휘 — "강사 보조 톤" 강제.
# PROJECT.md "AI = 강사 보조 도구" 포지셔닝 정합.
_COACH_NOTE_REQUIRED_WORDS: tuple[str, ...] = ("강사", "함께", "확인")

# 단정/지시형 어휘 blocklist — 강사 대체 톤 금지 (AI-SPEC §1 critical failure mode 3).
_TONE_BLOCKLIST_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"이렇게\s*하세요"),
    re.compile(r"잘못됐습니다"),
    re.compile(r"틀렸습니다"),
    re.compile(r"당신은"),
)


# ─────────────────── reserved key prefix (audit only) ───────────────────
#
# `_fallbackReason` / `_meta` 같은 `_` prefix 키는 `_process` 가
# `assemble.build_result` 입력 직전 strip (user-visible result 에 leak 0).
# Firestore audit (top-level `geminiB`) 에만 박힌다.

_FB_REASON_KEY: str = "_fallbackReason"
_META_KEY: str = "_meta"

# graceful fallback reason 박제 — caller (pipeline) 가 Cerebras 폴백 swap 시 audit.
_FB_VIDEO_PATH_MISSING: str = "video_path_missing"
_FB_GEMINI_NONE: str = "gemini_none"
_FB_TONE_VALIDATION_FAILED: str = "tone_validation_failed"


# ─────────────────── 영역 B 호출 설정 (AI-SPEC §4) ───────────────────
#
# Pro preview — temperature 0.4 (coach_writer.py L132 정합 — 한국어 자연어 다양성),
# max_output_tokens 8000 (2026-06-12 fix: 8 관절 × causes 3~5 × 부위별 용어 + coach_note
#   3 어휘 강제 박힘 박힘 → 2500 박힘 truncate 박혀 JSON 깨짐. 8000 으로 박힘).
# thinking_budget 2048 (Pro thinking 활용 — 원인 추론 깊이; output token 박힘 박힘
#   thinking budget 박힘 살짝 박힘).

_TEMPERATURE: float = 0.4
_MAX_OUTPUT_TOKENS: int = 12000
_THINKING_BUDGET: int = 4096


# ─────────────────── prompt 박제 (한국어, 강사 보조 톤 강제) ───────────────────
#
# 객관성 헌장 ([[analysis-objectivity-no-human-scores]]) 정합 — 점수/판단 어휘 영구
# 금지. enforce_object_guard=True (G1 가드) 가 raw text 차원에서 한번 더 강제.
#
# 2026-06-12 fix — prompt 박힘 prefix 박혀 강제 라인 박힘 박힘. 이전엔 정의만 박혀
# 사용 X.

_COACH_SYSTEM_INSTRUCTION: str = (
    "당신은 폴스포츠 강사를 보조하는 코칭 AI 입니다. 강사를 대체하지 않습니다.\n"
    "사용자에게 단정형/지시형 (이렇게 하세요 / 틀렸습니다 / 당신은 ...) 으로 말하지 마세요.\n"
    "항상 원인 → 해결 순서로 작성하고, 마지막은 '강사와 함께 영상 확인 권고' 로 마무리하세요.\n"
    "\n"
    "[필수 어휘 규칙 — 미준수 시 응답 reject]\n"
    "1. 각 cause.explanation 에는 다음 부위별 용어 중 하나 이상을 반드시 포함:\n"
    "   고관절, 후굴, 코어, 내전근, 외회전, 햄스트링, 견갑, 엉덩이 굴곡, 회전근개,\n"
    "   요추, 흉추, 슬괵, 장요근, 대퇴직근.\n"
    "   ('어깨/팔/다리/허리' 같은 일반 용어 만으로는 부족 — 위 14개 중 1개 박혀야 함).\n"
    "2. 각 관절의 detail 또는 첫 번째 cause.fix 에 '강사 / 함께 / 확인' 3 단어 가\n"
    "   동시에 포함된 한 문장 박혀야 함 (예: '정확한 자세는 강사와 함께 영상 확인 권고').\n"
    "\n"
    "[원인 기전 사슬 규칙]\n"
    "각 cause.explanation 은 '무엇 때문에(원인) → 무엇이 무너지는지(결과 기전)' 사슬로\n"
    "작성 (예: '왼팔 위치가 불안정해 상체 지지가 무너지고, 그로 인해 균형이 흐트러질 수 있어요').\n"
    "상태 서술만 있는 explanation (예: '상체가 흐트러졌어요') 금지 — 원인과 무너지는 결과를\n"
    "반드시 연결.\n"
    "각 cause.fix 는 그 원인일 경우의 구체 연습/교정 방법 (자세 큐, 반복 방법) 으로 작성.\n"
    "\n"
    "[low-deviation 케이스 가이드]\n"
    "deviation 수치가 작더라도 (1~5도) '양호함/완벽함/문제없음' 같은 평가 어휘 금지.\n"
    "그 자세에서 발생 가능한 잠재 원인 (예: 견갑 안정성, 회전근개 활성, 코어 긴장 등) 을\n"
    "원인으로 박아 explanation 을 채우세요. '차이가 작다 = 분석 X' 박힘 박힘.\n"
    "\n"
    "절대 금지: 점수 / 등급 / x= / y= / 좌표 / 잘했다 / 훌륭 / 완벽 / 양호.\n"
)


def _format_vision_fault_lines(vision_fault: dict | None) -> list[str]:
    """23-02 Task 5 (D-10 HIGH-1): to_coach_context() 의 vision-fault → causes 프롬프트 라인.

    coach gate(eligible_for_coach)는 pipeline 이 이미 판단 — 여기 도달한 vision_fault 는
    주입 대상이다. rootCauseHypotheses(support-gated, "~로 보임" 가설형, D-13 MED-1)를
    causes 원인 사슬의 **출발점** 지시로 렌더한다 (quick-260704-fwb — '참고' 힌트에서
    승격). 빈/None → 빈 list (기존 동작 불변).
    """
    if not vision_fault:
        return []
    hyps = vision_fault.get("rootCauseHypotheses") or []
    if not hyps:
        return []
    lines = [
        "",
        "[비전 분석 원인 단서] (이 가설을 causes 원인 사슬의 출발점으로 사용 — "
        "'~로 보임' 가설형):",
    ]
    for h in hyps:
        text = str((h or {}).get("text", "")).strip()
        if text:
            lines.append(f"- {text}")
    return lines if len(lines) > 2 else []


def _build_prompt(
    joints: list[dict],
    scene_flags: dict | None = None,
    vision_fault: dict | None = None,
    posture_axes: dict | None = None,
) -> str:
    """8 관절 deviation 수치 + scene_flags hint → user prompt 박제.

    Args:
      joints: context["joints"] — [{key, labelKo, deviation_deg, direction}, ...].
        coach_writer.py L69~74 패턴 정합.
      scene_flags: context["sceneFlags"] — Plan 17-02 영역 C 출력 dict 또는 None.
        occlusion_severe / backbend_present 가 True 면 prompt 에 hint 한 줄 박는다.
      vision_fault: context["visionFault"] — 23-02 to_coach_context() 의 vision-fault
        (support-gated rootCauseHypotheses). causes 섹션 원인 단서로 렌더.
      posture_axes: context["postureAxes"] — quick-260831-bjj belle 08-17 판독 축
        (mode1 기준-학생 델타). Cerebras 와 같은 발화 규칙(format_posture_axis_lines
        단일 출처) — None/전부 미발화 시 프롬프트 byte-불변.

    Returns:
      Korean prompt string — Gemini Pro 호출 user 메시지.
      (2026-06-12 fix — `_COACH_SYSTEM_INSTRUCTION` prefix 박혀 어휘 규칙 강제).
    """
    lines = [
        f"- {j['key']} ({j.get('labelKo', '')}): 기준 대비 평균 "
        f"{round(float(j.get('deviation_deg', 0)))}도 차이"
        + (f", 방향 {j['direction']}" if j.get("direction") else "")
        for j in joints
    ]
    hint_parts: list[str] = []
    if scene_flags is not None:
        if scene_flags.get("occlusion_severe"):
            hint_parts.append("영상 일부 신체가 가려져 있어 관련 부위 가시성에 제한이 있습니다.")
        if scene_flags.get("backbend_present"):
            hint_parts.append("백벤드(등 젖힘) 동작이 관찰됩니다 — 흉추/요추 단서를 우선 살피세요.")
    hint = ("\n\n[장면 단서]\n" + "\n".join(hint_parts)) if hint_parts else ""

    # 23-02 Task 5 — 비전 결함 root-cause 를 causes 섹션 힌트로 명시 주입 (graceful 무시 아님).
    vision_lines = _format_vision_fault_lines(vision_fault)
    vision_block = ("\n\n" + "\n".join(vision_lines)) if vision_lines else ""

    # quick-260831-bjj — belle 08-17 판독 축. 발화 0건이면 빈 블록 = byte-불변.
    posture_lines = format_posture_axis_lines(posture_axes)
    posture_block = ("\n" + "\n".join(posture_lines)) if posture_lines else ""

    return (
        _COACH_SYSTEM_INSTRUCTION
        + "\n"
        + "다음 8 관절의 deviation 수치와 영상을 함께 관찰해 한국어 코칭을 생성하세요.\n"
        "각 관절에 대해 detail (카드 본문 한 줄) + detail2 (causes 정확히 3개 + injury_risk + coach_note) 를\n"
        "모두 박으세요. 수치는 보조 — 원인 (왜 그런 자세가 되는지) 이 핵심입니다.\n"
        "\n"
        "관절 deviation:\n"
        + "\n".join(lines)
        + hint
        + vision_block
        + posture_block
        + "\n\nJSON 으로만 응답하세요. 다른 텍스트 / 마크다운 / 주석 금지.\n"
    )


# ─────────────────── 결과 정규화 / 후처리 검증 ───────────────────


def _coach_payload_to_dict(payload: CoachPayload) -> dict[str, dict]:
    """CoachPayload (Pydantic) → `{joint_key: {"detail", "detail2": {...}}}`.

    Cerebras coach_writer.py L136~139 의 `_normalize_entry` 출력 포맷 정합. camelCase
    키 (`injuryRisk`, `coachNote`) 박제 — `assemble.build_result` 가 그대로 소비.
    """
    out: dict[str, dict] = {}
    for jc in payload.joints:
        causes_list: list[dict] = [
            {
                "title": c.title,
                "explanation": c.explanation,
                "fix": c.fix,
            }
            for c in jc.detail2.causes
        ]
        out[jc.joint_key] = {
            "detail": jc.detail,
            "detail2": {
                "causes": causes_list,
                # injuryRisk 는 CoachDetail2 에 없음 (Plan 17-01 schema) — Cerebras 와의
                # 호환을 위해 None 박제 (assemble 이 키 없어도 graceful).
                "injuryRisk": None,
                # coachNote 도 schema 에 없음 — prompt 가 모델에게 박지만 schema 강제 X.
                # 본 patch 는 explanation 기반 후처리 검증 (_validate_tone) 후 detail
                # 의 마지막 줄에서 추출 박제 X — Cerebras 와 동일 graceful (None 박제).
                "coachNote": None,
            },
        }
    return out


def _validate_tone(coach_dict: dict[str, dict]) -> None:
    """강사 보조 톤 schema 후처리 검증 — 실패 시 ValueError raise.

    검증 항목 (각 joint 마다):
      1. 부위별 용어 14개 중 1개 이상이 모든 causes 전반에 포함 — explanation/fix/title
         어디든 1개라도 매치하면 PASS (joint 단위, cause 단위 X — 자연스러운 한국어
         박제 가능성 박제).
      2. coach_note (detail 마지막 줄 또는 explanation 첫 줄 결합) 에 "강사" + "함께"
         + "확인" 3 단어 동시 포함 — 본 plan 박제 시 detail + 모든 cause.fix 결합 텍스트
         에서 검증 (Pydantic schema 에 coach_note 필드 박제 X — 후처리 검증).
      3. 단정/지시형 blocklist 매치 시 ValueError.

    Raises:
      ValueError: 검증 실패 (caller 가 1회 retry).
    """
    if not coach_dict:
        raise ValueError("tone_validation: empty coach dict")

    for joint_key, entry in coach_dict.items():
        detail2 = entry.get("detail2") or {}
        causes: list[dict] = detail2.get("causes") or []
        if not causes:
            raise ValueError(
                f"tone_validation: joint={joint_key} causes 0건"
            )

        # explanation/fix/title 결합 텍스트 — 부위별 용어 + blocklist 검증 source.
        combined_explanation = " ".join(
            str(c.get("explanation", "")) for c in causes
        )
        combined_all = " ".join(
            f"{c.get('title', '')} {c.get('explanation', '')} {c.get('fix', '')}"
            for c in causes
        )
        full_text = (entry.get("detail") or "") + " " + combined_all

        # 1) 부위별 용어 — explanation 결합 텍스트에 최소 1개.
        if not any(term in combined_explanation for term in _BODY_PART_TERMS):
            raise ValueError(
                f"tone_validation: joint={joint_key} 부위별 용어 14개 중 1개도 없음 "
                f"(generic 어휘만 — 강사 신뢰 차단)"
            )

        # 2) coach_note 3 어휘 — full_text (detail + cause 전체) 에서 동시 검증.
        if not all(word in full_text for word in _COACH_NOTE_REQUIRED_WORDS):
            missing = [w for w in _COACH_NOTE_REQUIRED_WORDS if w not in full_text]
            raise ValueError(
                f"tone_validation: joint={joint_key} coach_note 필수 어휘 누락 "
                f"missing={missing} (강사 보조 톤 강제 — AI-SPEC §5 E4 dimension)"
            )

        # 3) blocklist 단정/지시형 어휘.
        for pat in _TONE_BLOCKLIST_PATTERNS:
            m = pat.search(full_text)
            if m:
                raise ValueError(
                    f"tone_validation: joint={joint_key} blocklist 매치 "
                    f"pattern='{pat.pattern}' match='{m.group(0)}' — "
                    f"강사 대체 톤 금지 (AI-SPEC §1)"
                )


def _attach_coach_note(coach_dict: dict[str, dict]) -> None:
    """detail 의 마지막 문장이 강사 보조 톤 3어휘를 포함하면 coachNote 로 박제.

    schema 에 coach_note 필드가 없으므로, 후처리로 detail 또는 cause.fix 의 마지막
    문장 (강사/함께/확인 포함) 을 detail2.coachNote 로 박제 — `assemble.build_result`
    가 user-visible 카드에 박을 수 있게.
    """
    for entry in coach_dict.values():
        detail2 = entry.get("detail2")
        if not isinstance(detail2, dict):
            continue
        if detail2.get("coachNote"):
            continue
        # 우선순위: detail 마지막 문장 → 첫 cause.fix 마지막 문장.
        candidates: list[str] = []
        detail = entry.get("detail")
        if isinstance(detail, str) and detail.strip():
            candidates.append(detail.strip())
        causes = detail2.get("causes") or []
        for c in causes:
            fx = c.get("fix")
            if isinstance(fx, str) and fx.strip():
                candidates.append(fx.strip())
        for cand in candidates:
            sentences = [s.strip() for s in re.split(r"[.!?\n]", cand) if s.strip()]
            for s in reversed(sentences):
                if all(w in s for w in _COACH_NOTE_REQUIRED_WORDS):
                    detail2["coachNote"] = s
                    break
            if detail2.get("coachNote"):
                break


# ─────────────────── GeminiCoachWriter 본체 ───────────────────


def _resolve_b_model() -> str:
    """env 박제 → resolve_model('B', env_override=...) 단일 source.

    우선순위:
      1. GEMINI_B_MODEL_OVERRIDE (emergency manual override)
      2. GEMINI_B_MODEL (alias)
      3. DEFAULT_B_MODEL (값은 config 가 owner)
    """
    env_override = (
        os.environ.get("GEMINI_B_MODEL_OVERRIDE")
        or os.environ.get("GEMINI_B_MODEL")
    )
    return resolve_model("B", env_override=env_override)


class GeminiCoachWriter:
    """영역 B 코칭 멘트 — `CerebrasCoachWriter` 와 100% 동일 `write(context: dict)` 시그니처.

    Args (생성자):
      api_key_loader: None = 기본 (GeminiVisionCall 의 `_default_api_key_loader`).
        caller 가 override 가능 (테스트에서 사용).
      model: None = `_resolve_b_model()` (`GEMINI_B_MODEL_OVERRIDE` → `GEMINI_B_MODEL`
        → `DEFAULT_B_MODEL`). caller 가 명시 박제 가능 (운영 강제 override).

    Method:
      write(context: dict) -> dict — Cerebras 와 동일 시그니처 (B3 hard gate).
    """

    def __init__(
        self,
        api_key_loader: Callable[[], str] | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key_loader = api_key_loader
        # model 은 lazy 박제 — env 가 호출 시점에 박혔을 수 있음 (테스트 monkeypatch).
        self._model_override = model

    def _build_call(self) -> GeminiVisionCall:
        """GeminiVisionCall 인스턴스화 — Plan 17-04 must_haves 의 param 박제 정합."""
        model = self._model_override or _resolve_b_model()
        kwargs: dict[str, Any] = dict(
            schema=CoachPayload,
            model=model,
            prompt="",  # 실제 prompt 는 call() 직전 _build_prompt 로 박제 — 본 객체 재사용 0.
            temperature=_TEMPERATURE,
            max_output_tokens=_MAX_OUTPUT_TOKENS,
            thinking_budget=_THINKING_BUDGET,
            enforce_object_guard=True,
        )
        if self._api_key_loader is not None:
            kwargs["api_key_loader"] = self._api_key_loader
        return GeminiVisionCall(**kwargs)

    def write(self, context: dict) -> dict:
        """**B3 hard gate 시그니처** — `CerebrasCoachWriter.write(context: dict) -> dict` 와 100% 동일.

        preuploaded_handle (27-04): GeminiFileSession 핸들은 **context dict 의
        `preuploadedHandle` 키**로 전달한다 (write() 시그니처는 B3 hard gate 상 self/context
        고정 — videoPath/sceneFlags/visionFault 와 동일한 context-확장 패턴). 주입 시 retry
        각 attempt 가 재업로드 없이 generate 만 반복한다 (Pitfall 8 해소 — 과거엔 attempt
        마다 1회용 GeminiVisionCall 이 업로드+finally delete 를 반복). 소유권 = 세션(client.py
        가 주입 시 finally delete skip). 미주입(None)이면 기존 attempt-당 업로드+delete 폴백
        (client.py 경로라 누수 0). Cerebras write 는 이 키를 무시(text-only, graceful).

        context dict keys:
          기존 (Cerebras 와 공유):
            mode: str
            joints: list[{key, labelKo, deviation_deg, direction}]
          Phase 17 신규 (Gemini 전용, Cerebras 는 graceful 무시):
            videoPath: str | None — local_video_path
            dimensionScores: dict | None
            sceneFlags: dict | None — Plan 17-02 영역 C 출력 dict

        Returns:
          성공: `{joint_key: {"detail", "detail2": {"causes", "injuryRisk", "coachNote"}}}`
            + reserved 키 (`_meta`) — `_process` 가 audit 박제 + strip.
          실패/graceful:
            `{}` (joints 키 누락 — Cerebras 와 동일 graceful) 또는
            `{"_fallbackReason": "video_path_missing" | "gemini_none" | "tone_validation_failed"}`.

          **2차 R-W4 정합 — None 반환 박제 0**.
        """
        # ── (1) context 기본 검증 — Cerebras 와 동일 graceful (`{}`).
        joints = context.get("joints")
        if not joints:
            return {}

        # ── (2) videoPath 누락 — Cerebras 폴백 신호 (text-only coach 는 Cerebras 책임).
        video_path = context.get("videoPath")
        if not video_path:
            return {_FB_REASON_KEY: _FB_VIDEO_PATH_MISSING}

        scene_flags = context.get("sceneFlags") or None
        vision_fault = context.get("visionFault") or None
        # quick-260831-bjj — belle 08-17 판독 축 (mode1 만 채워짐, 없으면 None graceful).
        posture_axes = context.get("postureAxes") or None
        # 27-04: 세션 핸들 (없으면 None → 기존 attempt-당 업로드 폴백). retry 는 이 핸들을
        # 재사용해 generate 만 반복 — 재업로드 0 (Pitfall 8). client.py 가 소유권=세션이면
        # finally delete skip.
        preuploaded_handle = context.get("preuploadedHandle")
        prompt = _build_prompt(
            joints,
            scene_flags=scene_flags,
            vision_fault=vision_fault,
            posture_axes=posture_axes,
        )

        # ── (3) Gemini 호출 + 후처리 검증 retry 1회.
        last_exc: ValueError | None = None
        for attempt in (1, 2):
            call = self._build_call()
            call.prompt = prompt  # dataclass 필드 mutate — 본 객체는 1회용.

            start = time.monotonic()
            try:
                parsed: CoachPayload | None = call.call(
                    video_path, preuploaded_handle=preuploaded_handle
                )
            except Exception as exc:  # noqa: BLE001 - graceful skip
                log.warning(
                    "GeminiCoachWriter call raise (attempt=%d): %s", attempt, exc
                )
                if attempt == 2:
                    return {_FB_REASON_KEY: _FB_GEMINI_NONE}
                continue
            finally:
                latency_ms = int((time.monotonic() - start) * 1000)

            if parsed is None:
                # GeminiVisionCall 가 graceful None (api_key 미설정 / 4xx / schema 검증
                # 실패). retry 1회 — 본 writer 박제 retry 는 client retry 와 별개.
                if attempt == 2:
                    return {_FB_REASON_KEY: _FB_GEMINI_NONE}
                continue

            coach_dict = _coach_payload_to_dict(parsed)
            _attach_coach_note(coach_dict)

            try:
                _validate_tone(coach_dict)
            except ValueError as exc:
                log.warning(
                    "GeminiCoachWriter tone_validation 실패 (attempt=%d): %s",
                    attempt,
                    exc,
                )
                last_exc = exc
                if attempt == 2:
                    # Phase 17 Plan 06B — G2 span event 박제 (TELEMETRY_OK gate).
                    if TELEMETRY_OK and _tracer is not None:
                        current_span = _otel_trace.get_current_span()
                        current_span.add_event("guardrail.G2.tone_validation_fallback", attributes={"gemini.model": call.model, "gemini.retry_count": attempt, "gemini.fallback_reason": _FB_TONE_VALIDATION_FAILED})
                    return {_FB_REASON_KEY: _FB_TONE_VALIDATION_FAILED}
                continue

            # 성공 path — reserved _meta 박제 (Firestore audit 입력).
            coach_dict[_META_KEY] = {
                "model": call.model,
                "latency_ms": latency_ms,
                "judgeScore": None,  # F1 flywheel 후속 채움
                "tokens_used": 0,  # GeminiVisionCall 시그니처 확장 시 박힘
            }
            return coach_dict

        # for loop 도달 X (이중 안전망) — last_exc 가 있으면 tone fallback, 아니면 gemini none.
        if last_exc is not None:
            return {_FB_REASON_KEY: _FB_TONE_VALIDATION_FAILED}
        return {_FB_REASON_KEY: _FB_GEMINI_NONE}


__all__ = ["GeminiCoachWriter"]
