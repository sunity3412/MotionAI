"""Gemini multimodal key moment 추출기 (Plan 01-13 T-1).

목적:
  Plan 12 dominant 가설 (a) frame-mean 한계 (mean disagreement 45-52도) 해결의 1단계.
  Gemini 2.5 Pro 가 폴 동작 영상에서 phase 별 key moment 시점 (setup / hold / peak /
  release) 을 추출 → 그 시점의 측정 각도가 Plan 15 IPSF `GeometricCriterion` 과 비교됨.

설계 원칙 (변경 금지):
  · Gemini 는 자연어 번역 + 시점 분류만 — 좌표 / 점수 / 판단 절대 출력 금지.
    (memory: analysis-objectivity-no-human-scores)
  · 응답에 좌표 (x=, y=, kp[)·점수 (점수 / score / out of)·심사 판단 키워드 detect 시 ValueError.
  · API 키는 AWS Parameter Store `/sunity/motion/gemini-api-key` (SecureString) 또는 env
    `GEMINI_API_KEY` — `.env` 하드코딩 금지 (CLAUDE.md §3).
  · `google.generativeai` / `boto3` lazy import — 모듈 로드 시점 0 import 로 로컬 테스트 가능.
  · moment_key enum = `VALID_MOMENT_KEYS` (`setup`, `hold`, `peak`, `release`) — Plan 15
    GeometricCriterion 과 동일 enum.

사용처:
  · `backend/research/spikes/spike_gemini_moment.py` (Plan 01-13 T-3 CLI).
  · 운영 코드 진입은 Plan 14 통과 후 별 plan 책임 (본 plan = 데이터 path 박제).

요구사항:
  · REQUIREMENTS.md SCORE-01 (기술 인식기 Gemini 어댑터, 좌표·판단 출력 금지).
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from .geometric_criterion import VALID_MOMENT_KEYS

log = logging.getLogger(__name__)

# AWS SSM Parameter Store 경로 — STATE.md 2026-06-01 박제됨.
GEMINI_API_KEY_PARAM_NAME = "/sunity/motion/gemini-api-key"

# 기본 Gemini 모델 — STATE.md "Phase 5 권장 모델" 인용.
DEFAULT_GEMINI_MODEL = "gemini-2.5-pro"

# Gemini 응답이 좌표·점수·판단을 출력하지 못하도록 거부할 패턴.
# memory: analysis-objectivity-no-human-scores — 출력은 시점/분류만, 점수·좌표 금지.
_COORDINATE_REJECT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bx\s*[:=]\s*-?\d", re.IGNORECASE),
    re.compile(r"\by\s*[:=]\s*-?\d", re.IGNORECASE),
    re.compile(r"\bz\s*[:=]\s*-?\d", re.IGNORECASE),
    re.compile(r"keypoint", re.IGNORECASE),
    re.compile(r"\bkp\s*\[", re.IGNORECASE),
    re.compile(r"좌표"),
    re.compile(r"픽셀"),
    re.compile(r"pixel", re.IGNORECASE),
)

_SCORE_REJECT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bscore\s*[:=]\s*\d", re.IGNORECASE),
    re.compile(r"점수"),
    re.compile(r"\d+\s*점\b"),
    re.compile(r"out\s+of\s+\d+", re.IGNORECASE),
    re.compile(r"\b\d{1,3}\s*/\s*\d{2,3}\b"),  # "85/100" 형태
)

_JUDGMENT_REJECT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"심사"),
    re.compile(r"\bjudgment\b", re.IGNORECASE),
    re.compile(r"\bjudging\b", re.IGNORECASE),
    re.compile(r"\bverdict\b", re.IGNORECASE),
    re.compile(r"\bfail(?:ed|ure)?\b", re.IGNORECASE),
    re.compile(r"\bpass(?:ed)?\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class KeyMoment:
    """단일 key moment 시점 — Gemini 분류 결과의 객관 핵심.

    frozen=True — 한번 추출된 시점이 런타임에 변경되지 않도록 불변.

    Fields:
      motion: 기준 동작 ID (sweep 5영상 ref-* 와 동일).
      moment_key: VALID_MOMENT_KEYS 중 하나 (setup / hold / peak / release).
      timestamp_seconds: 영상 시작점 기준 시간 (초). 0 이상.
      frame_index: T 프레임 시퀀스에서의 정수 인덱스. 0 이상.
      confidence: Gemini 자체 confidence (0.0~1.0). 점수 아님 — 분류 자체의 신뢰도.
      source_response_excerpt: Gemini 원본 응답 발췌 (디버그/감사 목적, 좌표/점수 미포함).
    """

    motion: str
    moment_key: str
    timestamp_seconds: float
    frame_index: int
    confidence: float
    source_response_excerpt: str

    def validate(self) -> None:
        """객관성 가드. 위반 시 명확한 한국어 ValueError."""
        if self.moment_key not in VALID_MOMENT_KEYS:
            raise ValueError(
                f"KeyMoment.moment_key 부정확. 유효 값 = {VALID_MOMENT_KEYS}. "
                f"motion={self.motion} moment_key={self.moment_key!r}"
            )
        if self.timestamp_seconds < 0:
            raise ValueError(
                f"KeyMoment.timestamp_seconds 는 0 이상이어야 합니다. "
                f"motion={self.motion} moment={self.moment_key} "
                f"timestamp_seconds={self.timestamp_seconds}"
            )
        if self.frame_index < 0:
            raise ValueError(
                f"KeyMoment.frame_index 는 0 이상이어야 합니다. "
                f"motion={self.motion} moment={self.moment_key} "
                f"frame_index={self.frame_index}"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"KeyMoment.confidence 는 [0.0, 1.0] 범위여야 합니다. "
                f"motion={self.motion} moment={self.moment_key} "
                f"confidence={self.confidence}"
            )
        _enforce_no_coordinate_or_score(
            self.source_response_excerpt,
            context=f"motion={self.motion} moment={self.moment_key}",
        )


def _enforce_no_coordinate_or_score(text: str, *, context: str) -> None:
    """Gemini 응답이 좌표·점수·판단을 포함하지 않는지 정규식 가드.

    SCORE-01 + memory analysis-objectivity-no-human-scores 1차 차단선.
    위반 패턴 발견 시 어떤 카테고리인지 메시지에 명시한다.
    """
    if not text:
        return  # 빈 응답은 별도 경로에서 처리 (필수 필드 누락 ValueError).
    for pat in _COORDINATE_REJECT_PATTERNS:
        m = pat.search(text)
        if m:
            raise ValueError(
                f"Gemini 응답에 좌표 출력이 포함됨 ({context}): "
                f"패턴='{pat.pattern}' 매치='{m.group(0)}'. "
                f"Gemini 역할은 시점 분류 + 자연어 번역만 — 좌표 출력 금지 "
                f"(REQUIREMENTS.md SCORE-01, memory analysis-objectivity-no-human-scores)."
            )
    for pat in _SCORE_REJECT_PATTERNS:
        m = pat.search(text)
        if m:
            raise ValueError(
                f"Gemini 응답에 점수 라벨링이 포함됨 ({context}): "
                f"패턴='{pat.pattern}' 매치='{m.group(0)}'. "
                f"사람 점수 ground truth 영구 금지 "
                f"(memory analysis-objectivity-no-human-scores)."
            )
    for pat in _JUDGMENT_REJECT_PATTERNS:
        m = pat.search(text)
        if m:
            raise ValueError(
                f"Gemini 응답에 심사 판단이 포함됨 ({context}): "
                f"패턴='{pat.pattern}' 매치='{m.group(0)}'. "
                f"심사 판단은 IPSF GeometricCriterion + 측정값 비교로만 — Gemini 금지 "
                f"(REQUIREMENTS.md SCORE-01)."
            )


def _load_api_key() -> str:
    """Gemini API 키 로드. 우선순위:

      1. env `GEMINI_API_KEY` — Pod / 로컬 dev 편의용 (CLI export).
      2. AWS SSM Parameter Store `/sunity/motion/gemini-api-key` (SecureString) — Lambda 기본.

    둘 다 없으면 RuntimeError. `.env` 하드코딩 금지 (CLAUDE.md §3).
    boto3 는 lazy import — 1번 경로 사용 시 AWS 의존성 없이 동작.
    """
    inline = os.environ.get("GEMINI_API_KEY")
    if inline:
        log.debug("Gemini API 키 로드: env GEMINI_API_KEY")
        return inline

    param_name = os.environ.get("GEMINI_API_KEY_PARAM_NAME", GEMINI_API_KEY_PARAM_NAME)
    try:
        import boto3  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            f"Gemini API 키가 env (`GEMINI_API_KEY`) 에 없고 boto3 도 설치되지 않음. "
            f"AWS Parameter Store `{param_name}` fetch 불가. "
            f"CLI 실행 시 `export GEMINI_API_KEY=...` 또는 boto3 설치 후 IAM 권한 부여 필요."
        ) from exc

    try:
        ssm = boto3.client("ssm")
        resp = ssm.get_parameter(Name=param_name, WithDecryption=True)
        value = resp["Parameter"]["Value"]
    except Exception as exc:
        raise RuntimeError(
            f"Gemini API 키 fetch 실패 — env `GEMINI_API_KEY` 미설정 + "
            f"AWS Parameter Store `{param_name}` 조회 실패: {exc}. "
            f"belle Pod 에서 `aws ssm get-parameter --name {param_name} --with-decryption` "
            f"수동 확인 권장."
        ) from exc

    if not value or not value.strip():
        raise RuntimeError(
            f"Gemini API 키가 비어있음 ({param_name}). "
            f"belle Google AI Studio 에서 키 재발급 후 Parameter Store 갱신 필요."
        )
    log.debug("Gemini API 키 로드: SSM %s", param_name)
    return value


# Gemini 에 보낼 프롬프트 — 좌표·점수·판단 출력 금지를 명시.
# JSON 만 응답하도록 강제 (Gemini Structured Output 미사용 — SDK 버전 의존성 줄임).
_GEMINI_PROMPT_TEMPLATE = """\
당신은 폴스포츠 동작 영상의 phase 분석 도우미입니다.

영상에서 동작 `{motion}` 의 phase 별 key moment 시점만 추출해주세요.
phase 종류는 정확히 다음 4가지입니다 (다른 값 사용 금지):
  - setup    동작 진입 직전 준비 자세
  - hold     동작이 완성되어 정지한 시점 (가장 중요)
  - peak     동작의 최대 신전·균형 시점 (hold 와 다를 수 있음)
  - release  동작에서 벗어나기 시작하는 시점

응답 규칙:
  1. JSON 만 출력. 다른 텍스트 / 설명 금지.
  2. 각 phase 가 영상에 존재하면 1건만 추출 (가장 대표 시점).
  3. 좌표 / 키포인트 / 점수 / 심사 판단 절대 출력 금지.
     (좌표·점수는 별도 측정 엔진이 담당, Gemini 는 시점 분류만)
  4. 확신 없으면 해당 phase 는 생략.

출력 스키마:
{{
  "moments": [
    {{
      "moment_key": "hold",
      "timestamp_seconds": 7.2,
      "confidence": 0.85,
      "description": "동작 설명을 짧게 (좌표/점수 금지)"
    }}
  ]
}}
"""


@dataclass
class GeminiMomentExtractor:
    """Gemini multimodal key moment 추출기.

    구조:
      · `__init__` 시점에 SDK / API 키 로드 0 — `extract_key_moments` 첫 호출 시 lazy.
      · 같은 영상의 재호출 결과는 `_cache` 에 보관 (Pod 비용/시간 절감).
      · `_cache` 는 `(video_uri, motion, model_name)` 키.

    테스트 가능성:
      · `_call_gemini` 만 override 하면 SDK 실호출 없이 단위 테스트 가능.
      · `model_name` / `api_key_loader` 를 인자로 받아 의존성 주입.
    """

    model_name: str = DEFAULT_GEMINI_MODEL
    api_key_loader: callable = field(default=_load_api_key)  # type: ignore[assignment]
    _cache: dict[tuple[str, str, str], list[KeyMoment]] = field(
        default_factory=dict, init=False, repr=False
    )

    def extract_key_moments(
        self,
        video_uri: str,
        motion: str,
    ) -> list[KeyMoment]:
        """video_uri (로컬 path 또는 file:// URI) 에서 motion 의 key moment list 추출.

        반환 list 는 frame_index 미정 (추출 시점에는 timestamp 만). caller (spike)
        가 영상 fps + frame 수로 frame_index 채워서 `validate()` 수행 — 본 메서드는
        timestamp 만 보장하는 1차 추출.

        Raises:
          ValueError: Gemini 응답이 좌표/점수/판단 포함, 스키마 위반, moment_key invalid.
          RuntimeError: API 키 로드 실패, SDK import 실패, 네트워크 실패.
        """
        cache_key = (video_uri, motion, self.model_name)
        if cache_key in self._cache:
            log.debug("KeyMoment 캐시 hit: %s", cache_key)
            return list(self._cache[cache_key])

        raw_response = self._call_gemini(video_uri, motion)
        moments = _parse_gemini_response(motion, raw_response)
        # frame_index 는 호출자가 후처리 — 본 메서드는 timestamp만 신뢰.
        # validate() 도 호출자가 frame_index 채운 뒤 수행.
        self._cache[cache_key] = list(moments)
        return moments

    def _call_gemini(self, video_uri: str, motion: str) -> str:
        """Gemini 실 호출. SDK 는 lazy import — 단위 테스트는 본 메서드 override.

        반환은 raw 응답 텍스트 (JSON). 파싱은 `_parse_gemini_response` 가 담당.

        2026-06-01: legacy `google-generativeai` (0.8.x) 는 새 AI Studio 키 포맷
        (`AQ.` prefix, 2025-말 갱신) 인식 못 함 — discovery endpoint 가
        ACCESS_TOKEN_TYPE_UNSUPPORTED 반환. 신 SDK `google-genai` (Client 기반,
        v1 endpoint) 사용. 설치: `pip install google-genai`.
        """
        try:
            from google import genai  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "google-genai 미설치 — Pod 에 `pip install google-genai` 필요. "
                "(2026-06-01 박제: legacy `google-generativeai` 는 새 AI Studio "
                "`AQ.` 키 포맷 미지원). 로컬 단위 테스트에서는 `_call_gemini` "
                "를 override 하세요."
            ) from exc

        api_key = self.api_key_loader()
        client = genai.Client(api_key=api_key)

        # 영상 업로드 — Gemini File API.
        # video_uri 가 로컬 path 면 upload, http(s) 면 fetch (Pod 측 boto3 presigned 가 일반적).
        if video_uri.startswith("http://") or video_uri.startswith("https://"):
            # 단순 보존 — Pod 가 보통 presigned URL 을 직접 받지 못해 로컬 path 권장.
            raise RuntimeError(
                "Gemini File API 는 로컬 path 만 지원 — Pod 가 S3 영상을 먼저 다운로드 후 "
                "로컬 경로를 video_uri 로 전달해야 합니다 "
                "(spike_rtmpose 의 `_resolve_video` 패턴 그대로)."
            )

        uploaded = client.files.upload(file=video_uri)
        prompt = _GEMINI_PROMPT_TEMPLATE.format(motion=motion)
        response = client.models.generate_content(
            model=self.model_name,
            contents=[uploaded, prompt],
        )
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError(
                "Gemini 응답이 비어있음 — model='%s' video='%s' motion='%s'."
                % (self.model_name, video_uri, motion)
            )
        return text


def _parse_gemini_response(motion: str, raw_text: str) -> list[KeyMoment]:
    """Gemini raw 응답 (JSON 텍스트) → KeyMoment list (frame_index=0 placeholder).

    Gemini 가 markdown fence (```json ... ```) 로 응답하는 경우도 흡수.
    응답에 좌표/점수/판단 포함 시 `_enforce_no_coordinate_or_score` 가 ValueError 던짐.

    `frame_index` 는 본 함수에서 0 으로 채움 — caller (spike) 가 fps 로 후처리.
    `validate()` 는 caller 가 frame_index 채운 후 수행.
    """
    _enforce_no_coordinate_or_score(raw_text, context=f"motion={motion}")

    cleaned = _strip_markdown_fence(raw_text)
    try:
        payload: Any = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Gemini 응답 JSON 파싱 실패 (motion={motion}): {exc}. "
            f"raw_excerpt='{raw_text[:200]}'"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError(
            f"Gemini 응답 최상위가 dict 가 아님 (motion={motion}): type={type(payload).__name__}."
        )
    raw_moments = payload.get("moments")
    if not isinstance(raw_moments, list):
        raise ValueError(
            f"Gemini 응답 'moments' 키가 list 가 아님 (motion={motion}): "
            f"type={type(raw_moments).__name__}."
        )

    result: list[KeyMoment] = []
    for entry in raw_moments:
        result.append(_entry_to_key_moment(motion, entry, raw_text=raw_text))
    return result


def _entry_to_key_moment(motion: str, entry: Any, *, raw_text: str) -> KeyMoment:
    """단일 응답 entry → KeyMoment (frame_index=0 placeholder)."""
    if not isinstance(entry, dict):
        raise ValueError(
            f"Gemini 'moments' entry 가 dict 가 아님 (motion={motion}): entry={entry!r}."
        )
    required = {"moment_key", "timestamp_seconds", "confidence"}
    missing = required - entry.keys()
    if missing:
        raise ValueError(
            f"Gemini 'moments' entry 필수 키 누락 (motion={motion}): "
            f"누락={sorted(missing)} entry={entry!r}."
        )

    description = entry.get("description", "")
    if description:
        # description 도 좌표/점수/판단 가드 통과해야 함.
        _enforce_no_coordinate_or_score(
            str(description),
            context=f"motion={motion} description",
        )

    moment_key = str(entry["moment_key"])
    if moment_key not in VALID_MOMENT_KEYS:
        raise ValueError(
            f"Gemini 응답 moment_key 부정확 (motion={motion}): "
            f"value={moment_key!r}. 유효 값 = {VALID_MOMENT_KEYS}."
        )

    try:
        timestamp = float(entry["timestamp_seconds"])
        confidence = float(entry["confidence"])
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Gemini 응답 타입 변환 실패 (motion={motion} moment={moment_key}): {exc}"
        ) from exc

    excerpt = raw_text[:240]  # 디버그 보존, 좌표/점수는 이미 가드 통과
    moment = KeyMoment(
        motion=motion,
        moment_key=moment_key,
        timestamp_seconds=timestamp,
        frame_index=0,  # caller 가 fps 로 후처리
        confidence=confidence,
        source_response_excerpt=excerpt,
    )
    # caller 가 frame_index 채운 후 validate() 호출 — 본 함수는 timestamp 만 검증.
    if moment.timestamp_seconds < 0:
        raise ValueError(
            f"Gemini 응답 timestamp_seconds 음수 (motion={motion} moment={moment_key}): "
            f"{moment.timestamp_seconds}"
        )
    if not (0.0 <= moment.confidence <= 1.0):
        raise ValueError(
            f"Gemini 응답 confidence 범위 위반 [0,1] (motion={motion} moment={moment_key}): "
            f"{moment.confidence}"
        )
    return moment


def _strip_markdown_fence(text: str) -> str:
    """Gemini 가 ```json ... ``` 로 감싼 응답에서 fence 제거."""
    t = text.strip()
    if t.startswith("```"):
        # 첫 줄 (```json) 제거
        nl = t.find("\n")
        if nl == -1:
            return t
        body = t[nl + 1 :]
        if body.endswith("```"):
            body = body[: -len("```")]
        return body.strip()
    return t


def assign_frame_indices(
    moments: Iterable[KeyMoment],
    *,
    fps: float,
    frames_total: int,
) -> list[KeyMoment]:
    """timestamp_seconds → frame_index 변환. caller 가 fps + frames_total 알면 호출.

    `frame_index = clamp(round(timestamp * fps), 0, frames_total - 1)`.
    변환 후 각 entry 의 `validate()` 수행 — moment_key / timestamp / frame_index /
    confidence 가드 일관 점검.

    Args:
      moments: KeyMoment iterable (`extract_key_moments` 결과).
      fps: 영상 fps (spike_rtmpose 의 frame extractor 와 동일 — 9.0 기본).
      frames_total: (T, J=8) angle 행렬의 T.

    Returns:
      validate() 통과한 frame_index 채워진 KeyMoment list.

    Raises:
      ValueError: fps <= 0 / frames_total <= 0 / validate 실패.
    """
    if fps <= 0:
        raise ValueError(f"fps 는 0 보다 커야 합니다: fps={fps}")
    if frames_total <= 0:
        raise ValueError(f"frames_total 은 0 보다 커야 합니다: frames_total={frames_total}")

    result: list[KeyMoment] = []
    for m in moments:
        idx = int(round(m.timestamp_seconds * fps))
        idx = max(0, min(idx, frames_total - 1))
        filled = KeyMoment(
            motion=m.motion,
            moment_key=m.moment_key,
            timestamp_seconds=m.timestamp_seconds,
            frame_index=idx,
            confidence=m.confidence,
            source_response_excerpt=m.source_response_excerpt,
        )
        filled.validate()
        result.append(filled)
    return result
