"""spot_check — 감점 카드 문장↔영상 일치 스팟체크 어댑터 (Plan 32-13, D-22/D-23).

목적 (32-CONTEXT D-22/D-23 + 리뷰 blocker 5):
  분석이 방출한 감점 카드 문장(statusLine/cueLine — 승인 문구집 32-05 골격)과
  summaryPraise.headline(백엔드 방출 — 앱이 렌더하는 바로 그 문장)이 영상의 실제
  자세와 명백히 모순되는지 분석 **사후** 스테이지에서 검수한다. 불일치(mismatch)로
  판정된 record 만 hiddenRecordIds 로 방출 — 앱이 해당 감점 카드를 표면에서 숨긴다
  ("틀린 말을 내보내느니 안 보여줌", D-23). 점수·verdict·감점 tally 는 절대
  건드리지 않는다 (판정 권한 = 숨김만, T-32-30).

멀티모달 스모크 실측 (2026-07-22, power-spin fault fixture 프레임 4장 + 실 record
문장 — 판정 모델 확정 기록):
  · gemini-omni-flash-preview: generate_content **400 INVALID_ARGUMENT
    "This model only supports Interactions API"** — 텍스트 판정·response_schema
    경로 자체가 없음(영상 생성 전용). 형식 불충족 → 탈락.
  · gemini-3.1-pro-preview (채택 — 플랜 지정 폴백, 검증된 vision 경로):
    strict JSON 준수, 판별력 실증 — 실결함 문장 2건 match / 조작 거짓 문장(그립
    이탈) mismatch / praise 부재 not_given. 11.9~14.6s, 토큰 in ~4.9K / out ~240.
  · gemini-3.5-flash (참고 — 비용 레버): 동일 verdict·동일 형식 준수, 5.6~6.6s.
    env GEMINI_SPOTCHECK_MODEL 로 재배포 없이 스왑 가능.

보수 판정 원칙 (T-32-30 — 과숨김 방지):
  · mismatch 는 프레임에서 **명백히 반증**되는 경우에만. 불확실 = uncertain = 표시.
  · 프레임 서브셋은 영상 일부만 담음 — 부재 증거는 반증이 아니다(프롬프트 명시).
  · '기준' = IPSF 절대 자세 기준(무릎 완전 신전 180° 등)임을 프롬프트가 정의 —
    1차 스모크에서 이 정의 없이는 절대-기준 문장까지 전부 uncertain 으로 판정
    무력화됨을 실측(스모크 1차 vs 2차). 비교-측정 record(deviationSource !=
    ipsf_absolute)는 프레임만으로 반증 불가 → uncertain 규칙을 프롬프트에 명시.

graceful (SP-3 — 완료된 분석 훼손 금지):
  · 키 부재/SDK 실패 → status 'skipped', API/파싱 실패 → status 'failed'.
    두 경우 모두 hiddenRecordIds 빈 배열(전 카드 표시 유지 — fail-open,
    contract.md §12.8 표시 정책). raise 0.

비용·상한 (분석당 1콜 고정):
  · records 상한 SPOTCHECK_MAX_RECORDS(8) — 감점 큰 순. 초과분은 미판정 통과
    (verdicts 에 미포함 = uncertain 취급 = 표시).
  · 프레임 입력 = 분석에 이미 쓰인 9fps 프레임의 대표 서브셋(record 당 최대 2,
    전체 상한 8 — 호출측 pipeline `_build_spot_check_video_ref` 산출).
  · 타임아웃 = 기존 vision wall 예산 env(GEMINI_MAX_VETO_WALL_S) 재사용.

캐시 없음 (의도): 스팟체크 입력(그 분석의 프레임+그 분석의 문장)은 분석마다
고유해 교차-분석 캐시 적중이 구조적으로 0 이다. SPOTCHECK_PROMPT_VERSION 은
방출 payload 의 감사 필드 + 프롬프트 변경 시 bump 규율(Pitfall 8 — 판정 분포
해석의 버전 경계)로 유지한다.

lazy-import (gemini_vision_scorer 관례): google.genai 는 top-level import 금지 —
_ensure_client()/판정 함수 내부에서만.

보안 (T-20-06 동형): GEMINI_API_KEY 절대 로그 금지. 프레임 바이트 미로그.
"""

from __future__ import annotations

import json
import logging
import os

log = logging.getLogger(__name__)

# ─────────────────── 버전·상한 상수 ───────────────────
#
# 프롬프트(_build_prompt) 또는 build_spot_check_schema() 구조 변경 시 반드시 bump
# (Pitfall 8 — 방출 doc 의 promptVersion 으로 판정 분포의 버전 경계를 감사).
SPOTCHECK_PROMPT_VERSION = "v1.0"
SPOTCHECK_SCHEMA_VERSION = "v1.0"

# 판정 모델 — env GEMINI_SPOTCHECK_MODEL 주입(재배포 없이 스왑), 기본값 = 스모크
# 확정값(헤더 기록). [[gemini-latest-model-versions]] suffix(-preview) 필수.
DEFAULT_SPOTCHECK_MODEL = (
    os.environ.get("GEMINI_SPOTCHECK_MODEL", "").strip() or "gemini-3.1-pro-preview"
)

# 분석당 판정 record 상한 (감점 큰 순 — 초과분 미판정 통과).
SPOTCHECK_MAX_RECORDS = 8
# 프레임 예산 — record 당 최대 2, 전체 상한 8 (호출측 frame builder 가 소비).
SPOTCHECK_FRAMES_PER_RECORD = 2
SPOTCHECK_MAX_FRAMES = 8
SPOTCHECK_MIN_FRAMES = 4
# 타임아웃 — 기존 vision wall 예산 env 재사용 (Pod start_server.sh 300s 박제).
_SPOTCHECK_TIMEOUT_S = float(os.environ.get("GEMINI_MAX_VETO_WALL_S", "120.0"))

# verdict enum — models.SPOT_CHECK_VERDICTS 와 lockstep.
VERDICT_MATCH = "match"
VERDICT_MISMATCH = "mismatch"
VERDICT_UNCERTAIN = "uncertain"
_ALLOWED_VERDICTS = (VERDICT_MATCH, VERDICT_MISMATCH, VERDICT_UNCERTAIN)

# verdicts[].reason 상한 (contract.md §12.8 — 감사용, 사용자 비노출).
_REASON_MAX_LEN = 120

# 모듈 캐시 싱글톤 (recognizer/gemini_vision_scorer 패턴).
_CLIENT = None


# ─────────────────── client (lazy — top-level genai import 금지) ───────────────────


def _ensure_client():
    """google.genai Client lazy-init + 모듈 캐시 싱글톤.

    키 로드는 gemini_vision_scorer._load_api_key 재사용 (env GEMINI_API_KEY 우선,
    미설정 시 SSM — 단일 출처, 키 절대 미로그).

    Raises:
      RuntimeError: 키 부재/SDK 미설치/client 생성 실패 — 호출자(run_spot_check)가
        graceful 'skipped' 로 변환.
    """
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    try:
        from google import genai  # lazy — top-level import 금지

        from .gemini_vision_scorer import _load_api_key  # 키 로드 단일 출처

        api_key = _load_api_key()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY 부재")
        _CLIENT = genai.Client(api_key=api_key)
    except Exception as exc:  # noqa: BLE001 - 키/SDK/생성 실패는 graceful 변환용
        raise RuntimeError(f"Gemini client 생성 실패: {exc}") from exc
    return _CLIENT


# ─────────────────── strict 응답 스키마 (자유 텍스트 파싱 금지) ───────────────────


def build_spot_check_schema() -> dict:
    """response_schema — verdict enum 3값 + praiseVerdict(not_given 포함) strict JSON.

    점수/일치율/평점 필드 0 ([[analysis-objectivity-no-human-scores]] 정합 —
    스팟체크는 문장-영상 일치 판정만, 점수 산출 절대 금지).
    """
    return {
        "type": "object",
        "properties": {
            "verdicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "recordId": {"type": "string"},
                        "verdict": {
                            "type": "string",
                            "enum": list(_ALLOWED_VERDICTS),
                        },
                        "reason": {"type": "string"},
                    },
                    "required": ["recordId", "verdict", "reason"],
                },
            },
            "praiseVerdict": {
                "type": "string",
                "enum": list(_ALLOWED_VERDICTS) + ["not_given"],
            },
            "praiseReason": {"type": "string"},
        },
        "required": ["verdicts", "praiseVerdict"],
    }


# ─────────────────── 판정 대상 선별 (순수 — 호출측 프레임 예산과 공유) ───────────────────


def select_judged_records(records) -> list:
    """판정 대상 record 선별 — recordId 필수 + 판정할 문장 보유 + 감점 큰 순 상한 8.

    · recordId 없는 record(legacy 형상) = 스킵 (판정도 숨김도 안 함 — fail-open 정합).
    · statusLine/cueLine 둘 다 없는 record = 판정할 문장이 없어 스킵.
    · |points| 내림차순 정렬 후 SPOTCHECK_MAX_RECORDS 절삭 — 초과분은 'uncertain'
      미판정 통과 (verdicts 미포함 = 표시 유지).

    순수 함수 — pipeline 의 프레임 예산 산정과 어댑터 내부 선별이 같은 결과를
    공유한다 (단일 출처).
    """
    if not isinstance(records, list):
        return []
    candidates = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        record_id = rec.get("recordId")
        if not isinstance(record_id, str) or not record_id:
            continue
        status_line = rec.get("statusLine")
        cue_line = rec.get("cueLine")
        has_sentence = (isinstance(status_line, str) and status_line) or (
            isinstance(cue_line, str) and cue_line
        )
        if not has_sentence:
            continue
        candidates.append(rec)

    def _abs_points(rec: dict) -> float:
        try:
            return abs(float(rec.get("points", 0.0)))
        except (TypeError, ValueError):
            return 0.0

    candidates.sort(key=_abs_points, reverse=True)
    return candidates[:SPOTCHECK_MAX_RECORDS]


# ─────────────────── 프롬프트 (보수 판정 — 스모크 2차 실측 형태) ───────────────────

_PROMPT_HEADER = """당신은 폴스포츠 코칭 앱의 결과 문장 검수자입니다. 아래는 한 수강생의 연습 영상에서 추출한 대표 프레임들과, 자동 분석이 이 영상에 대해 생성한 감점 안내 문장들입니다.

각 문장이 프레임에 보이는 실제 자세와 명백히 모순되는지 검수하세요.

용어 정의:
- 문장 속 '기준'은 폴스포츠 심사의 절대 자세 기준(예: 무릎 완전 신전 180°, 스플릿 180°)을 뜻합니다. 다른 영상과의 비교가 아니므로 프레임만으로 판정할 수 있습니다.
- 단, '(비교 측정)' 표시가 붙은 문장은 기준 영상/지난 영상과의 비교 측정이라 현재 프레임만으로 반증할 수 없으므로 'uncertain'.

판정 규칙 (보수적으로):
- 'mismatch'는 프레임에서 명백히 반증되는 경우에만 부여합니다. (예: "무릎이 덜 펴져 있다"인데 모든 프레임에서 무릎이 완전히 펴져 있음)
- 프레임은 영상의 일부 순간만 담습니다. 프레임만으로 확인 불가하거나 애매하면 반드시 'uncertain'.
- 문장이 프레임과 부합하면 'match'.
- reason 은 한국어 1문장, 120자 이내.

감점 안내 문장:"""


def _record_prompt_line(rec: dict) -> str:
    """record 1건 → 프롬프트 줄. 문장은 문구집 골격 그대로 (변형 0 — D-11)."""
    record_id = rec.get("recordId", "")
    status_line = rec.get("statusLine") or ""
    cue_line = rec.get("cueLine") or ""
    sentence = status_line if status_line else cue_line
    tail = f" / 행동 안내: {cue_line}" if (status_line and cue_line) else ""
    # 비교-측정 record 는 프레임 반증 불가 마커 (ipsf_absolute 만 프레임 판정 대상).
    marker = (
        ""
        if rec.get("deviationSource") == "ipsf_absolute"
        else " (비교 측정)"
    )
    return f"- [{record_id}] {sentence}{tail}{marker}"


def _build_prompt(judged: list, praise_headline: str | None) -> str:
    lines = [_PROMPT_HEADER]
    lines.extend(_record_prompt_line(rec) for rec in judged)
    if not judged:
        lines.append("- (감점 문장 없음 — verdicts 는 빈 배열로 응답)")
    lines.append(
        "\n잘한 점 문장 (같은 규칙으로 praiseVerdict 판정. 문장이 '없음'이면 'not_given'):"
    )
    lines.append(f"- {praise_headline}" if praise_headline else "- 없음")
    lines.append("\nJSON 으로만 응답하세요.")
    return "\n".join(lines)


# ─────────────────── 핵심 어댑터 ───────────────────


def _base_payload(status: str) -> dict:
    """no-op payload — hiddenRecordIds 빈 배열 = 전 카드 표시 유지 (fail-open)."""
    return {
        "status": status,
        "hiddenRecordIds": [],
        "verdicts": [],
        "praiseMismatch": False,
        "model": DEFAULT_SPOTCHECK_MODEL,
        "promptVersion": SPOTCHECK_PROMPT_VERSION,
    }


def run_spot_check(video_ref, records, praise_headline=None) -> dict:
    """감점 카드 문장 + praise 헤드라인 ↔ 프레임 일치 스팟체크 (분석당 1콜 고정).

    Args:
      video_ref: [{"label": str, "imageBytes": bytes, "mime": str}] — 분석에 이미
        쓰인 9fps 프레임의 대표 서브셋 (호출측 pipeline 이 JPEG 인코딩해 전달.
        gemini_vision_scorer inline-bytes 미디어 경로 재사용 — 업로드/폴링 0).
      records: deductionBreakdown.records (dict list — recordId 없는 record 는
        스킵, 상한 8 은 select_judged_records 가 적용).
      praise_headline: result.summaryPraise.headline (백엔드 방출 단일 원천 —
        앱이 렌더하는 바로 그 문장. 같은 호출에 문장 1개 추가 = 추가 API 콜 0).

    Returns:
      {status('done'|'skipped'|'failed'), hiddenRecordIds(list[str]),
       verdicts(list[{recordId, verdict, reason}]), praiseMismatch(bool),
       model(str), promptVersion(str)} — 항상 dict, raise 0 (SP-3).
      · 'done' + 빈 hiddenRecordIds = 검수 통과(숨길 것 없음).
      · 'skipped'(키/클라이언트 불가·프레임 부재) / 'failed'(API·파싱 실패) =
        no-op — 전 카드 표시 유지.
    """
    judged = select_judged_records(records)
    praise = (
        praise_headline
        if isinstance(praise_headline, str) and praise_headline.strip()
        else None
    )

    # 검수할 문장이 하나도 없으면 호출 자체가 불필요 — vacuous 'done' (비용 0).
    if not judged and praise is None:
        return _base_payload("done")

    try:
        client = _ensure_client()
    except Exception as exc:  # noqa: BLE001 - 키/SDK 부재 = graceful no-op
        log.warning("spot_check client 사용 불가 — skipped (graceful): %s", exc)
        return _base_payload("skipped")

    frames = [
        f
        for f in (video_ref or [])
        if isinstance(f, dict) and isinstance(f.get("imageBytes"), (bytes, bytearray))
    ]
    if not frames:
        log.warning("spot_check 프레임 입력 없음 — skipped (판정 불가)")
        return _base_payload("skipped")

    try:
        from google.genai import types as genai_types  # lazy — top-level 금지

        parts = []
        for f in frames:
            label = f.get("label")
            if isinstance(label, str) and label:
                parts.append(label)
            parts.append(
                genai_types.Part.from_bytes(
                    data=bytes(f["imageBytes"]),
                    mime_type=str(f.get("mime") or "image/jpeg"),
                )
            )
        parts.append(_build_prompt(judged, praise))

        config = genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=build_spot_check_schema(),
            temperature=0.0,
            max_output_tokens=2048,
            http_options=genai_types.HttpOptions(
                timeout=int(_SPOTCHECK_TIMEOUT_S * 1000)
            ),
        )
        response = client.models.generate_content(
            model=DEFAULT_SPOTCHECK_MODEL, contents=parts, config=config
        )
        text = getattr(response, "text", "") or ""
        doc = json.loads(text)
    except Exception as exc:  # noqa: BLE001 - API/파싱 실패 = graceful no-op
        log.warning("spot_check 호출 실패 — failed (graceful no-op): %s", exc)
        return _base_payload("failed")

    # ── 보수 후처리 — 보낸 recordId 만 인정, 누락/오염 = uncertain(표시) ──
    raw_verdicts: dict[str, dict] = {}
    for item in doc.get("verdicts") or []:
        if not isinstance(item, dict):
            continue
        rid = item.get("recordId")
        if isinstance(rid, str) and rid:
            raw_verdicts[rid] = item

    verdicts: list[dict] = []
    hidden: list[str] = []
    for rec in judged:
        rid = rec["recordId"]
        item = raw_verdicts.get(rid)
        verdict = VERDICT_UNCERTAIN
        reason = "모델 응답 누락 — 미판정 통과"
        if item is not None:
            v = item.get("verdict")
            if v in _ALLOWED_VERDICTS:
                verdict = v
            raw_reason = item.get("reason")
            if isinstance(raw_reason, str) and raw_reason:
                reason = raw_reason[:_REASON_MAX_LEN]
        verdicts.append({"recordId": rid, "verdict": verdict, "reason": reason})
        if verdict == VERDICT_MISMATCH:
            hidden.append(rid)

    praise_mismatch = praise is not None and doc.get("praiseVerdict") == VERDICT_MISMATCH

    return {
        "status": "done",
        "hiddenRecordIds": hidden,
        "verdicts": verdicts,
        "praiseMismatch": bool(praise_mismatch),
        "model": DEFAULT_SPOTCHECK_MODEL,
        "promptVersion": SPOTCHECK_PROMPT_VERSION,
    }
