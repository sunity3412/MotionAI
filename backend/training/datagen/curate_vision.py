"""Gemini Vision 다운로드-전 선별 게이트 (belle 2026-07-09 채택, 22-02 Task 1).

수백 후보를 저장하기 전에 "깨끗한 단일인물 폴 클립인가 / 어떤 동작인가 / 정타·fault
버킷 / 저장 가치"를 판정해 쓰레기 저장을 차단한다. **점수는 절대 내지 않는다** —
모델은 짚기·버킷까지만, 점수는 Phase 24 감점 엔진(불변식 [[scoring-must-be-
transparent-deduction-tally]]). verdict schema 에 score/severity 필드는 영구 부재.

구조 (coach_writer lazy-import + graceful no-op 전례):
  · 순수 판정 로직: normalize_verdict(raw) / decide(verdict) -> KeepDecision.
    네트워크·Gemini 무관. 테스트가 이것만 검증(Gemini 미호출).
  · Gemini I/O 어댑터: VisionGate.gate(video_id, url_or_path) -> verdict.
    유튜브 = URL 직접 전달(네이티브 인제스트, 다운로드 불필요), 로컬/IG = File API.
    verdict 를 vision_verdicts.json 에 video_id 키로 캐시(재호출 0 = 과금 방어 T-22-07).
    키 미설정 시 graceful — gate 가 "unknown" verdict(다운로드 보류) 반환, 크래시 금지.

과금·비가역이므로 실 gate 실행 = Task 3 belle greenlight. 이 모듈은 Task 1 에서
순수 로직만 테스트한다.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

# ── verdict schema (알파벳 정렬, score/severity 부재 — 모델은 점수를 내지 않는다) ──
VERDICT_KEYS: tuple[str, ...] = (
    "bucket",              # "정타" | "fault" | None (숫자 점수 아님 — 이진 버킷만).
    "keep",                # bool — 저장 가치.
    "move_guess",          # str | None — 동작 추정.
    "reason",              # str — 저장/폐기 사유(서술).
    "single_person_pole",  # bool — 깨끗한 단일인물 폴 클립 여부.
)

VALID_BUCKETS: tuple[str, ...] = ("정타", "fault")

# 점수/severity 계열 필드 — verdict 에 절대 등장 금지 (불변식 가드).
BANNED_VERDICT_FIELDS: tuple[str, ...] = (
    "score", "severity", "overall", "points", "rating", "grade",
)

# Gemini 키 = Parameter Store (coach_writer CEREBRAS_KEY_PARAM 전례). .env 하드코딩 금지.
GEMINI_KEY_PARAM_ENV = "GEMINI_KEY_PARAM"
GEMINI_KEY_ENV = "GOOGLE_API_KEY"  # 로컬 폴백.
# gemini-latest-model-versions: Flash = gemini-3.5-flash (2.5 금지).
GEMINI_MODEL = "gemini-3.5-flash"

VERDICT_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "vision_verdicts.json"

_GATE_PROMPT = (
    "너는 폴스포츠 학습셋 큐레이터다. 이 영상이 학습 코퍼스에 저장할 가치가 있는지 "
    "판정한다. 다음만 JSON 으로 답한다(다른 텍스트·마크다운·주석 금지):\n"
    '{"single_person_pole": bool, "keep": bool, "move_guess": "동작명 또는 null", '
    '"bucket": "정타" 또는 "fault" 또는 null, "reason": "저장/폐기 사유 한 줄"}\n'
    "규칙: 단일 인물이 폴에서 수행하는 깨끗한 클립만 keep=true. 다인·후프·오버레이 "
    "과다·전신 잘림·비폴은 keep=false. bucket 은 정타(공식대회 수준)/fault(교정 대상) "
    "이진 판정만 — 점수·severity·숫자 등급은 절대 내지 않는다(짚기까지만)."
)


@dataclass(frozen=True)
class KeepDecision:
    """decide() 순수 판정 결과. status: keep|reject|unknown."""

    keep: bool
    bucket: str | None
    move_guess: str | None
    reason: str
    status: str  # "keep" | "reject" | "unknown"


# ---------------------------------------------------------------------------
# 순수 판정 로직 (Gemini 무관 — 테스트 대상).
# ---------------------------------------------------------------------------
def _parse_json_lenient(text: str) -> dict:
    """Gemini 응답을 관대하게 JSON 파싱. 마크다운 펜스/여분 텍스트 방어.

    response_mime_type=application/json 이 대개 순수 JSON 을 주지만 가끔 ```json
    펜스나 앞뒤 설명이 붙는다. 첫 { ~ 마지막 } 구간만 추출해 파싱. 순수(네트워크 무관).
    """
    s = (text or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # "Extra data"(다중 객체)·앞뒤 잡텍스트 → 첫 { 부터 raw_decode 로 첫 객체만.
        idx = s.find("{")
        if idx == -1:
            raise
        obj, _ = json.JSONDecoder().raw_decode(s[idx:])
        return obj


def normalize_verdict(raw: dict | None) -> dict:
    """모델 raw 출력 → VERDICT_KEYS 화이트리스트 정규화.

    · VERDICT_KEYS 밖 키(특히 score/severity)는 통과하지 않는다 — 불변식 가드.
    · bucket 은 VALID_BUCKETS enum 강제(밖 값 → None; 숫자 점수 유입 차단).
    · 결측 키는 None(bool 필드는 False) 고정, 알파벳 정렬 재방출. 순수.
    """
    raw = raw or {}
    out: dict = {}
    for key in VERDICT_KEYS:
        val = raw.get(key)
        if key in ("keep", "single_person_pole"):
            out[key] = bool(val)
        elif key == "bucket":
            out[key] = val if val in VALID_BUCKETS else None
        elif key == "move_guess":
            out[key] = str(val) if val not in (None, "") else None
        else:  # reason
            out[key] = str(val) if val is not None else ""
    return {k: out[k] for k in sorted(out)}


def decide(verdict: dict | None) -> KeepDecision:
    """정규화된 verdict → KeepDecision. 순수 — Gemini 미호출.

    keep=true 이고 단일인물 폴이며 bucket 이 유효할 때만 저장(status=keep).
    verdict 가 None/빈값(키 미설정 graceful) → status=unknown(다운로드 보류).
    """
    if not verdict:
        return KeepDecision(
            keep=False, bucket=None, move_guess=None,
            reason="verdict 없음(Gemini 키 미설정 또는 선별 미실행) — 다운로드 보류",
            status="unknown",
        )
    v = normalize_verdict(verdict)
    if v["keep"] and v["single_person_pole"] and v["bucket"] in VALID_BUCKETS:
        return KeepDecision(
            keep=True, bucket=v["bucket"], move_guess=v["move_guess"],
            reason=v["reason"] or "단일인물 폴 클립 저장 가치 확인", status="keep",
        )
    return KeepDecision(
        keep=False, bucket=v["bucket"], move_guess=v["move_guess"],
        reason=v["reason"] or "단일인물 폴 아님/저장 가치 미달 — 폐기", status="reject",
    )


# ---------------------------------------------------------------------------
# Gemini I/O 어댑터 (Task 3 실행 — lazy-import, graceful).
# ---------------------------------------------------------------------------
def _load_api_key() -> str | None:
    """Parameter Store(우선) 또는 GOOGLE_API_KEY(로컬 폴백). 미설정 시 None."""
    param_name = os.environ.get(GEMINI_KEY_PARAM_ENV)
    if param_name:
        try:
            import boto3

            ssm = boto3.client("ssm")
            return ssm.get_parameter(Name=param_name, WithDecryption=True)[
                "Parameter"
            ]["Value"]
        except Exception:  # noqa: BLE001
            log.exception("Gemini 키 로드 실패 (Parameter Store)")
            return None
    return os.environ.get(GEMINI_KEY_ENV) or None


class VisionGate:
    """Gemini Vision 선별 어댑터. 키 미설정 시 graceful(gate → unknown verdict)."""

    def __init__(self, cache_path: Path | None = None) -> None:
        self._cache_path = cache_path or VERDICT_CACHE_PATH
        self._cache = self._load_cache()
        self._client = None
        api_key = _load_api_key()
        if not api_key:
            return  # graceful — gate() 가 unknown 반환.
        try:
            from google import genai  # google-genai SDK (Task 3 환경).

            self._client = genai.Client(api_key=api_key)
        except Exception:  # noqa: BLE001
            log.exception("Gemini 클라이언트 초기화 실패 — 선별 보류")
            self._client = None

    @property
    def ready(self) -> bool:
        """Gemini 클라이언트 초기화 여부(키 설정 + SDK 로드). False 면 gate 는 unknown."""
        return self._client is not None

    def _load_cache(self) -> dict:
        try:
            return json.loads(self._cache_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — 캐시 부재/손상은 빈 캐시로 시작.
            return {}

    def _save_cache(self) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def gate(self, video_id: str, url_or_path: str) -> dict:
        """후보 → verdict(정규화). 캐시 히트 시 재호출 0(과금 방어 T-22-07).

        키 미설정/클라이언트 없음 → unknown verdict(다운로드 보류, 크래시 금지).
        유튜브 URL 은 Gemini 네이티브 인제스트, 로컬/IG 경로는 File API (Task 3 배선).
        """
        if video_id in self._cache:
            return self._cache[video_id]
        if self._client is None:
            return normalize_verdict(None)  # graceful unknown (keep=False).
        try:
            raw = self._call_gemini(url_or_path)
            verdict = normalize_verdict(raw)
        except Exception:  # noqa: BLE001
            log.exception("Gemini 선별 실패 — unknown 보류")
            verdict = normalize_verdict(None)
        self._cache[video_id] = verdict
        self._save_cache()
        return verdict

    def _call_gemini(self, url_or_path: str) -> dict:
        """실 Gemini 호출 (Task 3 belle greenlight 후에만 도달). URL vs 파일 분기."""
        from google.genai import types

        if url_or_path.startswith("http"):
            contents = [
                types.Content(parts=[
                    types.Part(file_data=types.FileData(file_uri=url_or_path)),
                    types.Part(text=_GATE_PROMPT),
                ])
            ]
        else:
            uploaded = self._client.files.upload(file=url_or_path)
            # 업로드 직후 파일은 PROCESSING — ACTIVE 될 때까지 폴링(File API 계약).
            for _ in range(40):
                state = getattr(uploaded.state, "name", str(uploaded.state))
                if state == "ACTIVE":
                    break
                if state == "FAILED":
                    raise RuntimeError("File API 처리 실패(FAILED)")
                time.sleep(1)
                uploaded = self._client.files.get(name=uploaded.name)
            else:
                raise RuntimeError("File API ACTIVE 타임아웃")
            contents = [uploaded, _GATE_PROMPT]
        resp = self._client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config={"response_mime_type": "application/json"},
        )
        return _parse_json_lenient(resp.text)
