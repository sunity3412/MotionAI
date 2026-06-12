"""Phase 17 Wave 4 — 영역 A Reference 자동 등록 (Gemini 3.1 Pro Vision).

박제 정신:
  · 17-RESEARCH §9 Wave 4 + AI-SPEC §1b "What Domain Experts Evaluate Against" 영역 A
    정합. 정은지 영상 path 입력 → Gemini Pro Vision → IPSF 명칭 + clipRange +
    checkpointJoints + confidence 자동 산출. ReferenceRegistration Pydantic schema
    가 결과 검증.
  · 학원 용어 3분기 라우팅 (메모리 [[studio-term-3branch-system]] 직격):
      - branch_1_ipsf: Gemini A 출력 motion_name_ipsf 가 ipsf_whitelist.json 의
        ipsf_name / aka_ko / aka_en 중 하나와 정규화 후 정확 매치. → isActive=true.
      - branch_2_studio: studio_alias 인자가 studio_branch2_aliases.json 의
        studio_alias_ko 와 정규화 후 정확 매치 (정은지 학원 통용 비등재 동작).
        → isActive=true, championPersonalAlias 박힘.
      - branch_3_auto: 위 둘 다 미매치 — G3 guardrail 발동, review_required=True,
        inactiveReason="ipsf_whitelist_miss". belle 검수 큐 진입 (Plan 06 alert).
  · G3 guardrail = AI-SPEC §1b "IPSF Code of Points 명칭/Criteria 정합" + "학원 용어
    3분기 매핑 정확도" 둘 다 직격. LLM 이 fabrication 한 IPSF 코드 ("F999") 가
    reference DB 에 영구 박히는 path 차단 — 화이트리스트 외 = isActive=false 강제.
  · Graceful 폴백: GeminiVisionCall.call() None 반환 시 (api key 미설정 / 4xx / schema
    검증 실패) 본 함수도 None 반환. caller (Lambda handler) 가 500 server_error 반환.
  · resolve_model("A", env_override=...) 단일 source (3차 R-B1 정합). raw default
    string 박제 0.

후속 plan 정합:
  · Plan 07 reactivate script 가 STUDIO_ALIAS_OVERRIDES dict 박제 — motion_id ↔
    studio_alias 매핑 (reference doc 의 studioAlias field 가 seed 에 없음 검증).
  · 본 모듈은 Lambda handler (reference-auto-register/app.py) 가 단일 entry point.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

from .client import GeminiVisionCall
from .config import resolve_model
from .schemas import ReferenceRegistration


log = logging.getLogger(__name__)


# ─────────────────── 영역 A 호출 설정 (AI-SPEC §4) ───────────────────
#
# Pro preview default — temperature 0.1 (객관 분류), max_output_tokens 2048
# (motion_name + clipRange + checkpointJoints 8 entry + confidence 충분),
# thinking_budget=-1 (3.x default-on thinking). AI-SPEC §4 표 영역 A 정합.

_TEMPERATURE: float = 0.1
_MAX_OUTPUT_TOKENS: int = 2048
_THINKING_BUDGET: int = -1


# ─────────────────── G3 guardrail token ───────────────────

_G3_INACTIVE_REASON: str = "ipsf_whitelist_miss"

_BRANCH_1_IPSF: str = "branch_1_ipsf"
_BRANCH_2_STUDIO: str = "branch_2_studio"
_BRANCH_3_AUTO: str = "branch_3_auto"


# ─────────────────── Reference prompt (한국어) ───────────────────
#
# AI-SPEC §1b "What Domain Experts Evaluate Against" 의 IPSF Criteria 항목 + 학원 용어
# 3분기 라우팅 정의를 박는다. 객관성 헌장 ([[analysis-objectivity-no-human-scores]])
# 정합 — 좌표 / 점수 / 사람 판단 어휘 영구 금지. GeminiVisionCall 의
# enforce_object_guard=True (G1 가드) 가 raw text 차원에서 이를 한번 더 강제.

_REFERENCE_PROMPT: str = (
    "당신은 폴스포츠 동작 영상의 IPSF (International Pole Sports Federation) "
    "Code of Points 2025-2027 기반 객관적 동작 인식기입니다.\n"
    "주어진 영상의 기준 동작 (정은지 선수 reference 영상) 을 관찰하고 다음 필드만 "
    "JSON 으로 반환하세요.\n"
    "절대 금지: 점수/등급/잘했다/훌륭/완벽 등 사람 판단 어휘, 좌표 (x= / y=).\n"
    "\n"
    "필드 정의:\n"
    "1) motion_name_ipsf: IPSF CoP 2025-2027 등재 공식 영문명 (예: 'Butterfly', "
    "'Inverted Crucifix', 'Scorpio'). IPSF 미등재 학원 통용 동작이면 가장 가까운 "
    "영문 묘사 (예: 'Foxtop Combo', 'Sideway Spin'). 존재하지 않는 코드 fabrication "
    "절대 금지 — 모르면 묘사적 영문명.\n"
    "2) motion_name_ko: 한국어 통용명 (예: '버터플라이', '인버티드 크루시픽스', "
    "'폭스탑').\n"
    "3) clip_start_seconds: 동작 hold (peak 자세) 가 시작되는 timestamp (초, 0 이상).\n"
    "4) clip_end_seconds: 동작 hold 가 끝나는 timestamp (초, 0 이상).\n"
    "5) checkpoint_joints: 채점 분기 관절 1~8개. 각 entry 의 joint_key 는 8개 박제 "
    "(left/right elbow/shoulder/hip/knee) 중 하나, expectation 은 EXTEND (완전 신전), "
    "BENT_OK (의도된 굴곡), CONTACT (폴 접촉) 중 하나. 해당 동작의 Compulsory Criteria "
    "와 일치해야 함 (예: Butterfly = 양 무릎 EXTEND).\n"
    "6) confidence: 본인 인식 신뢰도 0.0~1.0.\n"
)


def _resolve_a_model() -> str:
    """env 박제 → resolve_model('A', env_override=...) 단일 source.

    우선순위:
      1. GEMINI_A_MODEL (alias)
      2. DEFAULT_A_MODEL ('gemini-3.1-pro-preview')

    Raises:
      ValueError: override 가 ALLOWED_MODELS 박제 외 (예: 'gemini-2.5-*' / plain Pro).
        graceful X — caller hard fail 인지.
    """
    return resolve_model("A", env_override=os.environ.get("GEMINI_A_MODEL"))


# ─────────────────── Fixture loading (JSON, lazy + cached) ───────────────────

_WHITELIST_PATH = Path(__file__).parent / "ipsf_whitelist.json"
_STUDIO_ALIAS_PATH = Path(__file__).parent / "studio_branch2_aliases.json"

_ipsf_whitelist_cache: list[dict] | None = None
_studio_aliases_cache: list[dict] | None = None


def _load_ipsf_whitelist() -> list[dict]:
    """ipsf_whitelist.json 의 entries list 로드. 모듈 단위 캐시 박제."""
    global _ipsf_whitelist_cache
    if _ipsf_whitelist_cache is None:
        with _WHITELIST_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        _ipsf_whitelist_cache = list(data.get("entries", []))
    return _ipsf_whitelist_cache


def _load_studio_branch2_aliases() -> list[dict]:
    """studio_branch2_aliases.json 의 entries list 로드. 모듈 단위 캐시 박제."""
    global _studio_aliases_cache
    if _studio_aliases_cache is None:
        with _STUDIO_ALIAS_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        _studio_aliases_cache = list(data.get("entries", []))
    return _studio_aliases_cache


# ─────────────────── Normalization + slug ───────────────────

_NORMALIZE_STRIP_RE = re.compile(r"[\s\-_]+")
_SLUG_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _normalize_name(s: str | None) -> str:
    """대소문자/공백/하이픈/underscore/NFKC 정규화. 매칭 비교 전 양쪽 거친다."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.strip().lower()
    s = _NORMALIZE_STRIP_RE.sub("", s)
    return s


def _slug(s: str | None) -> str:
    """소문자 + ascii + hyphen slug. Firestore doc id 정합. 한글은 제거되므로
    한국어만 박힌 경우 'ref' fallback prefix 박힘 (caller 가 override 박제 권장)."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s).lower()
    s = _SLUG_NON_ALNUM_RE.sub("-", s)
    s = s.strip("-")
    return s


# ─────────────────── Branch routing ───────────────────


def _match_ipsf_whitelist(motion_name_ipsf: str) -> dict | None:
    """ipsf_whitelist.json 의 entry 와 정규화 후 정확 매치 — ipsf_name / aka_ko /
    aka_en 셋 중 하나라도 매치 시 entry 반환. 미매치 None.
    """
    needle = _normalize_name(motion_name_ipsf)
    if not needle:
        return None
    for entry in _load_ipsf_whitelist():
        if _normalize_name(entry.get("ipsf_name")) == needle:
            return entry
        for aka in entry.get("aka_ko", []) or []:
            if _normalize_name(aka) == needle:
                return entry
        for aka in entry.get("aka_en", []) or []:
            if _normalize_name(aka) == needle:
                return entry
    return None


def _match_studio_alias(studio_alias: str | None) -> dict | None:
    """studio_branch2_aliases.json 의 entry 와 정규화 후 정확 매치. None / 미매치 → None."""
    if not studio_alias:
        return None
    needle = _normalize_name(studio_alias)
    for entry in _load_studio_branch2_aliases():
        if _normalize_name(entry.get("studio_alias_ko")) == needle:
            return entry
    return None


def _decide_motion_id(
    *,
    override_motion_id: str | None,
    ipsf_entry: dict | None,
    studio_entry: dict | None,
    motion_name_ipsf: str,
    studio_alias: str | None,
) -> str:
    """motion_id 결정 우선순위:
      1. override_motion_id (caller 박제)
      2. ipsf_entry 의 ipsf_code (정확 매치 시) 또는 ipsf_name slug
      3. studio_alias slug
      4. motion_name_ipsf slug
      5. fallback 'ref-auto-<timestamp_ms>'

    Firestore doc id 정합 — slug 가 비면 fallback. caller 가 override_motion_id 박제로
    seed-reference-motions 의 motionId 와 명시 정합 권장.
    """
    if override_motion_id:
        return override_motion_id
    if ipsf_entry:
        code = ipsf_entry.get("ipsf_code")
        if code:
            return f"ref-{_slug(code)}"
        name_slug = _slug(ipsf_entry.get("ipsf_name"))
        if name_slug:
            return f"ref-{name_slug}"
    if studio_entry:
        # 분기 2 — 한글 alias 는 slug 산출 시 빈 string 될 수 있으므로
        # championPersonalAlias 영문도 시도, 그 후 fallback.
        for cand in (
            studio_entry.get("champion_personal_alias"),
            studio_entry.get("studio_alias_ko"),
        ):
            s = _slug(cand)
            if s:
                return f"ref-{s}"
    # motion_name_ipsf slug (Gemini 출력 영문명) — 분기 3 fallback path.
    s = _slug(motion_name_ipsf)
    if s:
        return f"ref-{s}"
    # studio_alias 도 시도.
    s = _slug(studio_alias)
    if s:
        return f"ref-{s}"
    # 최종 — caller 가 override 안 박았고 영문 입력 0 인 edge case.
    # idempotent 깨짐 — 후속 호출 시 다른 motion_id. 도메인 정합 X 이므로 graceful 박제.
    return f"ref-auto-{int(time.time() * 1000)}"


def _route_branch(
    *,
    ipsf_entry: dict | None,
    studio_entry: dict | None,
) -> tuple[str, bool, str | None]:
    """(routing_branch, review_required, inactive_reason) 박제.

    분기 결정:
      · IPSF 매치 → branch_1_ipsf, review_required=False, inactive_reason=None.
      · IPSF 미매치 + studio_alias 매치 → branch_2_studio, review_required=False,
        inactive_reason=None.
      · 둘 다 미매치 → branch_3_auto, review_required=True (G3),
        inactive_reason='ipsf_whitelist_miss'.

    분기 우선순위 — IPSF 매치가 분기 2 보다 우선 X (NotebookLM citation: 학원 통용
    호칭이 IPSF 코드의 변형인 경우, IPSF 매치도 가능). 단 본 구현에서는 IPSF 매치
    를 우선 — Gemini A 가 직접 인식한 IPSF 명칭 이 화이트리스트 매치되면 1순위.
    studio_alias 는 belle 의 명시 hint — IPSF 미매치 시 진입.
    """
    if ipsf_entry is not None:
        return (_BRANCH_1_IPSF, False, None)
    if studio_entry is not None:
        return (_BRANCH_2_STUDIO, False, None)
    return (_BRANCH_3_AUTO, True, _G3_INACTIVE_REASON)


# ─────────────────── Public entry point ───────────────────


def extract_reference_metadata(
    video_path: str,
    studio_alias: str | None = None,
    override_motion_id: str | None = None,
) -> dict[str, Any] | None:
    """영상 path → reference 자동 등록 dict 박제 (graceful 폴백).

    Args:
      video_path: 로컬 영상 path (Lambda /tmp). caller 가 이미 S3 download 박은 path.
      studio_alias: belle 가 reference 등록 시 박은 학원 통용 alias hint (예: '폭스탑').
        None 이면 분기 2 라우팅 시도 안 함 — IPSF 매치 또는 G3 fallback 만.
      override_motion_id: Firestore doc id 강제 박제 (Plan 07 reactivate script 가
        seed 의 motionId 와 정합 박제 시 사용). None 이면 ipsf_code / slug 기반 자동.

    Returns:
      dict 또는 None (Gemini 호출 graceful 폴백 시). dict 키:
        motion_id (str): Firestore reference doc id (예: 'ref-b201' or 'ref-foxtop').
        motion_name_ipsf (str): Gemini A 출력 영문명.
        motion_name_ko (str): Gemini A 출력 한국어명.
        clip_range (dict): {'clip_start_seconds', 'clip_end_seconds'}.
        checkpoint_joints (list[dict]): JointKeyLiteral expectation entry.
        routing_branch (str): 'branch_1_ipsf' / 'branch_2_studio' / 'branch_3_auto'.
        review_required (bool): G3 fallback 시 True (belle 검수 필요).
        inactive_reason (str | None): G3 fallback 시 'ipsf_whitelist_miss', 그 외 None.
        confidence (float): Gemini A 자체 신뢰도.
        model (str): 호출 model string (audit).
        registered_at (int): ms timestamp (audit).
        raw_response (dict): Gemini A schema validated 원본 (audit + 재구성 가능).
        champion_personal_alias (str | None): 분기 2 시 정은지 통용 호칭 (audit).

    Raises:
      ValueError: resolve_model 가 ALLOWED_MODELS 박제 외 model 거부 (graceful X).
        또는 GeminiVisionCall 의 G1 guardrail (점수/판단 어휘) 매치.
    """
    model = _resolve_a_model()
    call = GeminiVisionCall(
        schema=ReferenceRegistration,
        model=model,
        prompt=_REFERENCE_PROMPT,
        temperature=_TEMPERATURE,
        max_output_tokens=_MAX_OUTPUT_TOKENS,
        thinking_budget=_THINKING_BUDGET,
        enforce_object_guard=True,
    )

    start = time.monotonic()
    try:
        parsed: ReferenceRegistration | None = call.call(video_path)
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)

    if parsed is None:
        log.info(
            "extract_reference_metadata graceful skip model=%s latency_ms=%d "
            "(api_key 미설정 / 4xx / schema 검증 실패)",
            model,
            latency_ms,
        )
        return None

    # 분기 라우팅 박제.
    ipsf_entry = _match_ipsf_whitelist(parsed.motion_name_ipsf)
    studio_entry = _match_studio_alias(studio_alias)
    routing_branch, review_required, inactive_reason = _route_branch(
        ipsf_entry=ipsf_entry,
        studio_entry=studio_entry,
    )

    # motion_id 박제.
    motion_id = _decide_motion_id(
        override_motion_id=override_motion_id,
        ipsf_entry=ipsf_entry,
        studio_entry=studio_entry,
        motion_name_ipsf=parsed.motion_name_ipsf,
        studio_alias=studio_alias,
    )

    # 결과 payload 박제. raw_response 는 schema validated dict (Firestore 박힘 audit).
    result: dict[str, Any] = {
        "motion_id": motion_id,
        "motion_name_ipsf": parsed.motion_name_ipsf,
        "motion_name_ko": parsed.motion_name_ko,
        "clip_range": {
            "clip_start_seconds": float(parsed.clip_start_seconds),
            "clip_end_seconds": float(parsed.clip_end_seconds),
        },
        "checkpoint_joints": [
            {"joint_key": cj.joint_key, "expectation": cj.expectation}
            for cj in parsed.checkpoint_joints
        ],
        "routing_branch": routing_branch,
        "review_required": review_required,
        "inactive_reason": inactive_reason,
        "confidence": float(parsed.confidence),
        "model": model,
        "registered_at": int(time.time() * 1000),
        "latency_ms": latency_ms,
        # raw_response — flat dict scalar / list[dict-of-scalars] 정합.
        # firestore_admin._validate_flat_dict_no_nested_array 통과 가능.
        "raw_response": parsed.model_dump(),
        # 분기 2 audit — championPersonalAlias 박힘.
        "champion_personal_alias": (
            studio_entry.get("champion_personal_alias")
            if studio_entry is not None
            else None
        ),
        # ipsf_code audit — 분기 1 시 박힘.
        "ipsf_code": (
            ipsf_entry.get("ipsf_code") if ipsf_entry is not None else None
        ),
    }
    return result


__all__ = ["extract_reference_metadata"]
