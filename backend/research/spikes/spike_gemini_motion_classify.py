"""Gemini motion_name 분류 + response_schema spike (Plan 5-01 Task 1).

목적:
  Open Question 1 (motion_name 응답 형태 — 한국어 / 영어 / IPSF code) +
  Open Question 2 (google-genai response_schema + video file 작동 여부) 를
  단일 CLI 로 동시 검증한다.

두 mode:
  · `stub` — 미리 박제한 응답 JSON fixture injection → 정규화 path + reject patterns
            가드 검증. 로컬 OK (google-genai / boto3 의존성 0).
  · `live` — belle Pod 에서 google-genai 신 SDK 실 호출. response_schema 사용 / 미사용
            분기 박제.

출력:
  --output JSON 박제 (raw_response_text, raw_motion_name, canonical_motion,
  scope_status, moments, response_schema_used, response_schema_worked, fallback_used).

박제 정신:
  · D-04: 1회 호출 → 기술명 + 4단계 라벨 + timestamp.
  · D-08: Gemini = 라벨러만. 좌표 / 점수 / 판단 출력 금지.
  · D-13: 모델 default = gemini-3.1-pro.
  · D-16: google-genai / boto3 lazy import — 모듈 로드 시 0 import.
  · W1 fix: 본 spike 의 prompt 텍스트에 "좌표" / "score" / "점수" keyword 0건.
  · B2 fix: 본 spike 는 production classifier (`sunity_shared.analysis.
    gemini_motion_classifier.classify_motion_name`) 를 import — 역방향 금지.

요구사항:
  · REQUIREMENTS.md SCORE-01.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# B2 fix: production classifier 박제 import. spike → production (역방향 금지).
from sunity_shared.analysis.gemini_motion_classifier import (
    REGISTERED_MOTIONS,
    classify_motion_name,
)

log = logging.getLogger(__name__)


# stub mode 기본 모델 표기 (gemini_moment_extractor.DEFAULT_GEMINI_MODEL 와 동일).
# 본 상수는 출력 JSON 박제용. 실제 stub mode 는 SDK 호출 없음.
_DEFAULT_GEMINI_MODEL = "gemini-3.1-pro"

# W1 fix 박제 — 본 prompt 는 좌표 / 점수 / 판단 keyword 0건.
# Gemini = 라벨러만 (D-08). 응답 = 한국어 자연어, JSON schema 강제.
# 좌표 / 점수 / 판단 거부는 응답 처리 단계의 reject patterns 가 1차 + 2차 가드.
# 본 prompt 자체에는 거부 카테고리만 명시 (예: '좌표' '점수' 단어 자체는 박제 X).
# 등재 동작 목록은 **REGISTERED_MOTIONS 에서 생성**한다 (2026-08-28 수리).
# 하드코딩된 5개 목록이 남아 있었는데 P1 step4 가 5동작을 추가해 등재는 10개가 됐고,
# 프롬프트만 옛 5개를 안내하고 있었다 — 분류기가 모르는 동작을 물어보는 꼴이다.
# 목록을 코드로 만들면 등재가 바뀔 때 프롬프트가 자동으로 따라간다.
_MOTION_LABEL_KO: dict[str, str] = {
    "ref-climb": "베이직 클라임",
    "ref-foxtop": "폭스탑",
    "ref-foxtop-split": "폭스탑 스플릿",
    "ref-invert": "인버티드 버터플라이",
    "ref-sideway-spin": "사이드웨이 스핀",
    "ref-kip-up": "킵업",
    "ref-power-spin": "파워 스핀",
    "ref-peter-pan": "피터팬",
    "ref-elbow-twist-sister": "엘보 트위스트 시스터",
    "ref-pdshape": "PD 쉐입",
}


def _registered_motion_lines() -> str:
    """등재 ID 목록을 프롬프트 블록으로 — 한글명은 있으면 붙이고 없으면 ID 만."""
    from sunity_shared.analysis.gemini_motion_classifier import REGISTERED_MOTIONS

    width = max(len(m) for m in REGISTERED_MOTIONS)
    out = []
    for m in sorted(REGISTERED_MOTIONS):
        ko = _MOTION_LABEL_KO.get(m)
        out.append(f"  - {m.ljust(width)}  ({ko})" if ko else f"  - {m}")
    return "\n".join(out)


def _build_prompt_template() -> str:
    from sunity_shared.analysis.gemini_motion_classifier import REGISTERED_MOTIONS

    return _GEMINI_PROMPT_BODY.format(
        n=len(REGISTERED_MOTIONS), motions=_registered_motion_lines()
    )


_GEMINI_PROMPT_BODY = """\
당신은 폴스포츠 동작 영상의 분류 도우미입니다.

영상에서 다음 {n}개 등재 동작 중 어느 것인지 판단하고,
4단계 (setup / hold / peak / release) 의 timestamp 와 confidence 를 추출하세요.

등재 동작 목록 (정확한 ID 로 응답):
{motions}

응답 규칙:
  1. JSON 만 출력. 다른 텍스트 / 설명 금지.
  2. 등재 동작 외의 동작이면 motion_name 을 응답한 그대로 두고, 본 분류 시스템이
     "unregistered" 로 처리합니다.
  3. 시점 라벨링 외의 정보 (위치 키포인트 / 평가 라벨 / 합격 여부 등) 는 절대 출력하지
     마세요. 별도 측정 엔진이 담당.
  4. 확신 없으면 confidence 를 낮추세요 (해당 단계 생략 가능).

출력 스키마:
{{
  "motion_name": "ref-invert",
  "motion_name_lang": "ko" | "en" | "ipsf_code" | "unknown",
  "confidence": 0.85,
  "moments": [
    {{
      "moment_key": "hold",
      "timestamp_seconds": 7.2,
      "confidence": 0.85,
      "description": "동작 설명을 짧게"
    }}
  ]
}}
"""

# 하위 호환 — 기존 소비처(_GEMINI_PROMPT_TEMPLATE)는 그대로 두고 값만 생성본으로.
_GEMINI_PROMPT_TEMPLATE = _build_prompt_template()


# ────────────────────────────── stub fixtures ──────────────────────────────


def _load_fixture(name: str) -> dict[str, Any]:
    """fixture JSON 로드. backend/tests/fixtures/gemini_responses/{name}.json.

    spike 와 단위 테스트 양쪽이 같은 fixture 를 참조 — 응답 형태 박제 단일 source.
    """
    fixture_dir = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "fixtures"
        / "gemini_responses"
    )
    path = fixture_dir / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Gemini fixture 미존재: {path}. "
            f"backend/tests/fixtures/gemini_responses/ 안에 fixture 박제 필요."
        )
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ────────────────────────────── reject patterns 가드 (어댑터 layer 1차) ──────


def _enforce_no_reject_patterns(text: str, *, context: str) -> None:
    """좌표 / 점수 / 판단 reject patterns 가드.

    실 구현은 gemini_moment_extractor 박제 패턴 재사용. 본 spike 는
    lazy import (D-16) 로 module 로드 시 sunity_shared.judging 0 import.
    """
    from sunity_shared.judging.gemini_moment_extractor import (
        _enforce_no_coordinate_or_score,
    )

    _enforce_no_coordinate_or_score(text, context=context)


# ────────────────────────────── stub mode ──────────────────────────────


def _run_stub(motion_hint: str, fixture_name: str) -> dict[str, Any]:
    """stub fixture injection → 정규화 path + reject patterns 가드 검증.

    output JSON 박제 = response_schema 작동 여부와 무관 (stub 은 schema 미사용).
    """
    fixture = _load_fixture(fixture_name)
    raw_text = fixture.get("raw_response_text", "")
    payload = fixture.get("payload", {})

    # 1차 reject patterns 가드 — raw_text 가 좌표 / 점수 / 판단 포함 시 ValueError.
    _enforce_no_reject_patterns(raw_text, context=f"stub fixture={fixture_name}")

    raw_motion_name = str(payload.get("motion_name", ""))
    canonical, scope_status = classify_motion_name(raw_motion_name)

    return {
        "input_motion_hint": motion_hint,
        "fixture_name": fixture_name,
        "raw_response_text": raw_text,
        "raw_motion_name": raw_motion_name,
        "canonical_motion": canonical,
        "scope_status": scope_status,
        "motion_name_lang": payload.get("motion_name_lang", "unknown"),
        "moments": payload.get("moments", []),
        "response_schema_used": False,
        "response_schema_worked": None,
        "fallback_used": None,
        "model": _DEFAULT_GEMINI_MODEL,
    }


# ────────────────────────────── live mode (belle Pod) ──────────────────────


def _build_response_schema():
    """Pydantic schema for response_mime_type=application/json.

    lazy import (D-16) — pydantic 미설치 환경에서도 stub mode 는 동작.
    """
    from typing import Literal

    from pydantic import BaseModel  # type: ignore

    class GeminiMomentEntry(BaseModel):
        moment_key: Literal["setup", "hold", "peak", "release"]
        timestamp_seconds: float
        confidence: float
        description: str = ""

    class GeminiClassifyResponse(BaseModel):
        motion_name: str
        motion_name_lang: Literal["ko", "en", "ipsf_code", "unknown"]
        confidence: float
        moments: list[GeminiMomentEntry]

    return GeminiClassifyResponse


def _run_live(
    motion_hint: str,
    video_path: str,
    *,
    use_response_schema: bool,
    model_name: str,
) -> dict[str, Any]:
    """live mode — google-genai 신 SDK 호출.

    response_schema 작동 여부 분기:
      · use_response_schema=True + 작동 시 → response.parsed 직접 사용 path.
      · use_response_schema=True + 미작동 시 → prompt-only fallback (Plan 01-13 박제).
      · use_response_schema=False → prompt-only path (기존 박제).

    박제 정신:
      · API key 는 sunity_shared.judging.gemini_moment_extractor._load_api_key 재사용.
      · 좌표 / 점수 / 판단 응답 시 reject patterns 가드 ValueError.
    """
    # lazy import (D-16).
    from google import genai  # type: ignore

    from sunity_shared.judging.gemini_moment_extractor import _load_api_key

    api_key = _load_api_key()
    client = genai.Client(api_key=api_key)

    uploaded = client.files.upload(file=video_path)

    # ACTIVE 대기 — gemini_moment_extractor 박제 패턴 그대로.
    import time as _time

    _start = _time.monotonic()
    _max_wait_s = 120.0
    while getattr(uploaded.state, "name", str(uploaded.state)) == "PROCESSING":
        if _time.monotonic() - _start > _max_wait_s:
            raise RuntimeError(
                f"Gemini File API processing timeout ({int(_max_wait_s)}s) — file={uploaded.name}"
            )
        _time.sleep(2.0)
        uploaded = client.files.get(name=uploaded.name)

    prompt = _GEMINI_PROMPT_TEMPLATE

    response_schema_used = use_response_schema
    response_schema_worked: bool | None = None
    fallback_used: str | None = None
    raw_text = ""
    parsed: Any = None

    if use_response_schema:
        try:
            schema_cls = _build_response_schema()
            response = client.models.generate_content(
                model=model_name,
                contents=[uploaded, prompt],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": schema_cls,
                },
            )
            parsed = getattr(response, "parsed", None)
            raw_text = getattr(response, "text", "") or ""
            response_schema_worked = parsed is not None
            if not response_schema_worked:
                fallback_used = "prompt_only"
        except Exception as exc:  # noqa: BLE001 - SDK 미지원 케이스 흡수
            log.warning("response_schema 미지원 — prompt-only fallback: %s", exc)
            response_schema_worked = False
            fallback_used = "prompt_only_after_exception"

    if parsed is None:
        response = client.models.generate_content(
            model=model_name,
            contents=[uploaded, prompt],
        )
        raw_text = getattr(response, "text", "") or ""

    # 1차 reject patterns 가드.
    _enforce_no_reject_patterns(raw_text, context=f"live mode model={model_name}")

    # parsed 가 있으면 그대로 사용, 아니면 raw_text → JSON 파싱.
    if parsed is not None:
        # Pydantic 모델 → dict.
        try:
            payload = parsed.model_dump()  # type: ignore[attr-defined]
        except AttributeError:
            payload = dict(parsed)
    else:
        from sunity_shared.judging.gemini_moment_extractor import (
            _strip_markdown_fence,
        )

        cleaned = _strip_markdown_fence(raw_text)
        payload = json.loads(cleaned)

    raw_motion_name = str(payload.get("motion_name", ""))
    canonical, scope_status = classify_motion_name(raw_motion_name)

    return {
        "input_motion_hint": motion_hint,
        "video_path": video_path,
        "raw_response_text": raw_text,
        "raw_motion_name": raw_motion_name,
        "canonical_motion": canonical,
        "scope_status": scope_status,
        "motion_name_lang": payload.get("motion_name_lang", "unknown"),
        "moments": payload.get("moments", []),
        "response_schema_used": response_schema_used,
        "response_schema_worked": response_schema_worked,
        "fallback_used": fallback_used,
        "model": model_name,
    }


# ────────────────────────────── CLI ──────────────────────────────


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Gemini motion_name 분류 + response_schema spike (Plan 5-01). "
            "stub mode = fixture 검증, live mode = belle Pod 실 호출."
        )
    )
    p.add_argument(
        "--motion",
        choices=sorted(REGISTERED_MOTIONS),
        help="motion hint (단일 영상 spike). 미지정 시 fixture 박제만 검증.",
    )
    p.add_argument(
        "--video-path",
        default=None,
        help="live mode 영상 path (로컬). stub mode 는 미사용.",
    )
    p.add_argument(
        "--mode",
        choices=("stub", "live"),
        default="stub",
        help="stub = fixture injection (로컬), live = google-genai 실 호출 (Pod).",
    )
    p.add_argument(
        "--fixture",
        default="ko_invert",
        help="stub mode fixture 이름 (ko_invert / en_foxtop / ipsf_split / unregistered / multi_word).",
    )
    p.add_argument(
        "--use-response-schema",
        action="store_true",
        help="live mode 만: response_mime_type=application/json + response_schema 사용.",
    )
    p.add_argument(
        "--gemini-model",
        default=_DEFAULT_GEMINI_MODEL,
        help=f"Gemini 모델 (default={_DEFAULT_GEMINI_MODEL}).",
    )
    p.add_argument(
        "--output",
        default=None,
        help="출력 JSON path. 미지정 시 reports/spike_gemini_motion_classify_<UTC>.json.",
    )
    return p


def _default_output_path() -> Path:
    reports = Path(__file__).resolve().parent / "reports"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return reports / f"spike_gemini_motion_classify_{stamp}.json"


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    args = build_arg_parser().parse_args()

    motion_hint = args.motion or "auto"

    if args.mode == "stub":
        result = _run_stub(motion_hint, args.fixture)
    else:
        if not args.video_path:
            log.error("live mode 는 --video-path 필요.")
            return 2
        result = _run_live(
            motion_hint,
            args.video_path,
            use_response_schema=args.use_response_schema,
            model_name=args.gemini_model,
        )

    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    output = Path(args.output) if args.output else _default_output_path()
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    log.info("output: %s", output)
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    sys.exit(main())
