"""GeminiTechniqueRecognizer — TechniqueRecognizer Protocol 의 Gemini 어댑터.

Plan 5-01 (2026-06-04). Plan 01-13 spike `GeminiMomentExtractor` 를 wrap.

박제 정신:
  · D-04: 1회 호출 → 기술명 + 4단계 라벨 + timestamp.
  · D-05: v1 채점 = hold moment 라벨만 활성. setup/peak/release = Firestore 박제만.
  · D-08: Gemini = 라벨러만, yaml 수치 (정은지 reference 측정값) source 박제 보호.
  · D-09: 3-case fallback (API 실패 / Low conf / 미등록).
  · D-13: model = gemini-3.1-pro 단일.
  · D-16: lazy import (google.genai / boto3 / firebase_admin / technique_cache).
  · [[analysis-objectivity-no-human-scores]] reject patterns 2차 가드 박제.

3-case fallback (D-09):
  case 1 (API 실패):     RuntimeError 시 FallbackRecognizer 위임 + category="api_failure"
  case 2 (Low conf):     mean confidence < threshold → joint_expectations={} + category="low_confidence"
  case 3 (미등록):       scope_status == "unregistered" → joint_expectations={} + category="unregistered"
                          + unregistered_hook(raw_motion_name, video_hash) 호출 (B3 fix)

reject patterns 2차 가드:
  extractor 가 1차로 _enforce_no_coordinate_or_score 통과시키지만, 어댑터 layer 가
  raw_text (_last_raw_response) 를 다시 검사 — 다중 방어. extractor 가 미래에 reject
  patterns 변경되어도 어댑터는 자체 가드 유지.

unregistered_hook 시그너처 (B3 fix):
  (keyword: str, video_hash: str) -> None
  · video_path 노출 X (PII 보호 — TERM-DATA-01 분기 3 schema 정합).
  · hook 실패 시 try/except 로 분석 흐름 계속 (D-09 case 3 graceful degrade).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from typing import Any, Callable

from .gemini_motion_classifier import REGISTERED_MOTIONS, classify_motion_name
from .skeleton import JOINT_KEYS
from .technique import (
    JOINT_BENT_OK,
    JOINT_CONTACT,
    JOINT_EXTEND,
    FallbackRecognizer,
    TechniqueProfile,
    TechniqueRecognizer,
)

log = logging.getLogger(__name__)


# Plan 5-01 박제 — 본 어댑터의 reject patterns 2차 가드 분기 (D-08).
# extractor 가 1차 (gemini_moment_extractor._enforce_no_coordinate_or_score),
# 어댑터가 2차. lazy import 로 D-16 정합.
def _adapter_reject_guard(text: str, *, context: str) -> None:
    """어댑터 layer 2차 가드 — _enforce_no_coordinate_or_score 재호출.

    text 가 비어있으면 noop (extractor 가 빈 응답 RuntimeError 처리).
    """
    if not text:
        return
    from sunity_shared.judging.gemini_moment_extractor import (
        _enforce_no_coordinate_or_score,
    )

    _enforce_no_coordinate_or_score(text, context=context)


def _compute_video_hash(video_path: Any) -> str:
    """video_hash 산출 (B3 fix — PII 미노출).

    Plan 5-02 의 technique_cache.compute_video_hash 가 신설되면 그 함수를 사용.
    아직 미신설 (Plan 5-02 책임) → ImportError 시 빈 문자열 반환 + warning.
    """
    if video_path is None:
        return ""
    try:
        from .technique_cache import compute_video_hash  # type: ignore[import-not-found]
    except ImportError:
        # Plan 5-02 신설 전 — graceful no-op. unregistered_hook 는 hash 없이 호출.
        log.debug(
            "technique_cache.compute_video_hash 미신설 (Plan 5-02) — video_hash=''"
        )
        return ""
    try:
        return compute_video_hash(video_path)
    except Exception as exc:  # noqa: BLE001 - hash 산출 실패는 분석 흐름 차단 X
        log.warning("compute_video_hash 실패 (분석 계속): %s", exc)
        return ""


@dataclass
class GeminiTechniqueRecognizer:
    """Gemini multimodal video → TechniqueProfile (4단계 라벨 + 기술명).

    Fields:
      extractor: GeminiMomentExtractor (lazy init). 단위 테스트에서 mock 주입.
      cache: TechniqueCache (Plan 5-02 신설). None = no-cache. 단위 테스트에서 mock.
      fallback: TechniqueRecognizer — API 실패 시 위임. None = FallbackRecognizer().
      low_confidence_threshold: D-09 case 2 임계. D-10 박제 (5영상 sweep 실측 후 갱신).
      motion_query_hint: extractor 호출 시 motion query 박제. None = "auto".
      unregistered_hook: D-09 case 3 Firestore 트리거 (B3 fix: (keyword, video_hash)).
    """

    extractor: Any = None  # GeminiMomentExtractor (lazy)
    cache: Any = None  # TechniqueCache (Plan 5-02), default None = no-cache
    fallback: TechniqueRecognizer | None = None
    low_confidence_threshold: float = 0.5  # D-10 박제 — 5영상 sweep 후 갱신
    motion_query_hint: str | None = None  # None = Gemini 자체 분류, str = caller hint
    unregistered_hook: Callable[[str, str], None] | None = None  # B3 fix 시그너처

    def __post_init__(self) -> None:
        if self.fallback is None:
            self.fallback = FallbackRecognizer()

    def recognize(self, angles: Any, frames: Any = None) -> TechniqueProfile:
        """3-case fallback + reject patterns 2차 가드 + joint_expectations 빌드.

        Args:
          angles: 관절각 행렬 (T, J=8). FallbackRecognizer 위임 시 사용.
          frames: video_uri (str) — Gemini File API 입력 path. None 시 Gemini 호출 skip
                   + FallbackRecognizer 위임 (api_failure path).

        Returns:
          TechniqueProfile — category ∈ {"recognized", "api_failure", "low_confidence",
          "unregistered"}. dimensions.py 가 joint_expectations 만 소비 (D-08).
        """
        # Step 1: cache hit (Plan 5-02 wiring 전 = 항상 miss).
        if self.cache is not None and frames is not None:
            try:
                cached = self.cache.lookup(frames)
                if cached is not None:
                    log.info("GeminiTechniqueRecognizer cache hit")
                    return self._profile_from_cache(cached)
            except Exception as exc:  # noqa: BLE001 - cache 실패는 분석 흐름 차단 X
                log.warning("cache.lookup 실패 (분석 계속): %s", exc)

        # Step 2: frames 없으면 Gemini 호출 불가 → FallbackRecognizer 위임 (api_failure).
        if frames is None:
            log.info("frames=None — Gemini 호출 skip, FallbackRecognizer 위임")
            profile = self.fallback.recognize(angles, frames=frames)
            return replace(profile, category="api_failure")

        # Step 3: extractor lazy init.
        if self.extractor is None:
            from sunity_shared.judging import GeminiMomentExtractor

            self.extractor = GeminiMomentExtractor()

        # Step 4: Gemini 호출 (D-09 case 1 fallback).
        try:
            response_text, moments, raw_motion_name = self._call_extractor(frames)
        except (RuntimeError, ValueError) as exc:
            log.warning("Gemini API 실패 — FallbackRecognizer 위임: %s", exc)
            profile = self.fallback.recognize(angles, frames=frames)
            return replace(profile, category="api_failure")

        # Step 5: reject patterns 2차 가드 (D-08 박제 정신,
        # [[analysis-objectivity-no-human-scores]]).
        _adapter_reject_guard(
            response_text, context="GeminiTechniqueRecognizer.recognize"
        )

        # Step 6: low confidence (D-09 case 2).
        if moments:
            mean_conf = sum(m.confidence for m in moments) / len(moments)
        else:
            mean_conf = 0.0
        if mean_conf < self.low_confidence_threshold:
            log.info(
                "Gemini low conf=%.2f < %.2f — Page 9 단독 채점 path",
                mean_conf,
                self.low_confidence_threshold,
            )
            return TechniqueProfile(
                name="신뢰도 낮음",
                category="low_confidence",
                joint_expectations={},
                required_split_deg=None,
                requires_hold=True,
                is_symmetric=False,
            )

        # Step 7: motion 정규화 + 미등록 (D-09 case 3).
        canonical, scope_status = self._classify_motion(raw_motion_name)
        if scope_status == "unregistered":
            log.info(
                "Gemini motion 미등록='%s' — Page 9 단독 + 자동 수집 trigger",
                raw_motion_name,
            )
            if self.unregistered_hook is not None:
                # B3 fix — hook 에 video_hash 전달 (video_path 박제 X, PII 미노출).
                video_hash = _compute_video_hash(frames)
                try:
                    self.unregistered_hook(raw_motion_name, video_hash)
                except Exception:  # noqa: BLE001 - hook 실패는 분석 흐름 차단 X
                    log.exception("unregistered_hook 실패 (분석 계속)")
            return TechniqueProfile(
                name=f"미등록: {raw_motion_name}",
                category="unregistered",
                joint_expectations={},
                required_split_deg=None,
                requires_hold=True,
                is_symmetric=False,
            )

        # Step 8: 정상 — KeyMoment → joint_expectations 변환 (D-05 hold 라벨만 활성).
        profile = self._build_profile(canonical, moments)

        # Step 9: cache store.
        if self.cache is not None and frames is not None:
            try:
                self.cache.store(
                    frames,
                    {
                        "motion": canonical,
                        "moments": [_serialize_moment(m) for m in moments],
                        "joint_expectations": profile.joint_expectations,
                        "model": "gemini-3.1-pro",
                    },
                )
            except Exception as exc:  # noqa: BLE001 - cache 실패는 분석 흐름 차단 X
                log.warning("cache.store 실패 (분석 결과 반환): %s", exc)

        return profile

    # ───────────────────────── 내부 helper ─────────────────────────

    def _call_extractor(self, frames: Any) -> tuple[str, list, str]:
        """extractor 호출 + 응답 raw text + KeyMoment list + raw motion name 반환.

        extractor 는 _last_raw_response / _last_motion_name attribute 박제 (B5/W3 fix).
        spike 결과에서 Gemini 가 motion_name 응답 X 인 path 박제 시 motion_query_hint
        로 대체.
        """
        motion_query = self.motion_query_hint or "auto"
        moments = self.extractor.extract_key_moments(
            video_uri=frames,
            motion=motion_query,
        )
        raw_text = getattr(self.extractor, "_last_raw_response", "") or ""
        raw_motion_name = (
            getattr(self.extractor, "_last_motion_name", "") or motion_query
        )
        return raw_text, list(moments), raw_motion_name

    def _classify_motion(self, raw_name: str) -> tuple[str, str]:
        """production 정규화 path (B2 fix).

        spike 가 본 production 함수를 import (역방향 금지). Pod/Lambda runtime 에서
        backend/research/spikes/ 경로 의존 0.
        """
        return classify_motion_name(raw_name)

    def _build_profile(self, motion: str, moments: list) -> TechniqueProfile:
        """KeyMoment[hold] + yaml hold_moment criteria → joint_expectations dict.

        D-08 박제 — Gemini = 라벨러만. yaml 의 hold_moment criteria 가 등재된 관절 =
        EXTEND, 미등재 = BENT_OK. ref-climb yaml = hold_moment 빈 list → 8관절 모두
        BENT_OK. 정은지 reference 측정값 (Plan 5-00 박제) 가 yaml angle_target source.

        yaml lookup 실패 (FileNotFoundError / ImportError) 시 → 8관절 BENT_OK
        fallback (분석 흐름 차단 X). 로그 warning.
        """
        try:
            from sunity_shared.judging.loader import load_grouped_criteria

            criteria_by_moment = load_grouped_criteria(motion)
            hold_criteria = criteria_by_moment.get("hold_moment", []) or criteria_by_moment.get(
                "hold", []
            )
            # Path K (2026-06-05, 함정 25 fix): yaml hold_criteria 의 extension_class 박제
            # 정합. EXTEND 박제 관절만 line 채점 대상 (180° 신전 deficit). BENT_OK 박제 관절
            # 은 line 채점 out_of_scope (부분 굽힘 의도된 자세). 박제 정신 [[ipsf-5-track-scoring]]
            # 의 "신전 완전성" 평가 정의 정합.
            extend_joints = {
                c.joint_key for c in hold_criteria if c.extension_class == "EXTEND"
            }
        except (FileNotFoundError, ImportError, ValueError) as exc:
            log.warning(
                "yaml lookup 실패 (motion=%s, 8관절 BENT_OK fallback): %s",
                motion,
                exc,
            )
            extend_joints = set()

        expectations: dict[str, str] = {}
        for joint_key in JOINT_KEYS:
            expectations[joint_key] = (
                JOINT_EXTEND if joint_key in extend_joints else JOINT_BENT_OK
            )

        # Path H production 정합 (2026-06-05): Gemini KeyMoments[hold] 의 timestamp →
        # frame_index 변환 후 hold_window 박제. dimensions.line_score / stability_score
        # 가 자동 추출 (분산 최소 sub-window) 대신 이 윈도우 사용.
        # 사용자 영상의 standing setup/dismount frame 잡힘 위양성 박제 정신 정합.
        # 박제: hold KeyMoment 가 여러 개면 첫/마지막 timestamp 로 박제. 1개면 ±2초 박제.
        hold_window_tuple: tuple[int, int] | None = None
        hold_moments = [m for m in moments if m.moment_key == "hold"]
        if hold_moments:
            fps = 9.0  # frame_extractor.py target_fps (박제 정신 정합)
            ts_list = sorted(m.timestamp_seconds for m in hold_moments)
            if len(ts_list) >= 2:
                start_sec, end_sec = ts_list[0], ts_list[-1]
            else:
                # 단일 hold moment = ±2초 window 박제
                start_sec = max(0.0, ts_list[0] - 2.0)
                end_sec = ts_list[0] + 2.0
            hold_window_tuple = (int(round(start_sec * fps)), int(round(end_sec * fps)))

        return TechniqueProfile(
            name=motion,
            category="recognized",
            joint_expectations=expectations,
            required_split_deg=None,
            requires_hold=True,
            is_symmetric=False,
            hold_window=hold_window_tuple,
        )

    def _profile_from_cache(self, cached: dict) -> TechniqueProfile:
        """cache hit 시 dict → TechniqueProfile 복원."""
        return TechniqueProfile(
            name=cached.get("motion", "cached"),
            category="recognized",
            joint_expectations=cached.get("joint_expectations", {}),
            required_split_deg=None,
            requires_hold=True,
            is_symmetric=False,
        )


def _serialize_moment(m: Any) -> dict:
    """KeyMoment → JSON-serializable dict (cache.store payload)."""
    return {
        "moment_key": getattr(m, "moment_key", ""),
        "timestamp_seconds": getattr(m, "timestamp_seconds", 0.0),
        "confidence": getattr(m, "confidence", 0.0),
        "frame_index": getattr(m, "frame_index", 0),
    }
