"""GeminiTechniqueRecognizer — TechniqueRecognizer Protocol 의 Gemini 어댑터.

Plan 5-01 (2026-06-04). Plan 01-13 spike `GeminiMomentExtractor` 를 wrap.

박제 정신:
  · D-04: 1회 호출 → 기술명 + 4단계 라벨 + timestamp.
  · D-05: v1 채점 = hold moment 라벨만 활성. setup/peak/release = Firestore 박제만.
  · D-08: Gemini = 라벨러만, yaml 수치 (정은지 reference 측정값) source 박제 보호.
  · D-09: 3-case fallback (API 실패 / Low conf / 미등록).
  · D-13: model 단일 — 문자열은 gemini/config.py 가 owner (여기 박지 않는다).
  · D-16: lazy import (google.genai / boto3 / firebase_admin / technique_cache).
  · [[analysis-objectivity-no-human-scores]] reject patterns 2차 가드 박제.

3-case fallback (D-09):
  case 1 (API 실패):     RuntimeError 시 FallbackRecognizer 위임 + category="api_failure"
  case 2 (Low conf):     mean confidence < threshold → joint_expectations={} + category="low_confidence"
  case 3 (미등록):       scope_status == "unregistered" → joint_expectations={} + category="unregistered"
                          + unregistered_hook(raw_motion_name, video_hash) 호출 (B3 fix)

reject patterns 2차 가드:
  extractor 가 1차로 _enforce_no_coordinate_or_score 통과시키지만, 어댑터 layer 가
  raw_text 를 다시 검사 — 다중 방어. extractor 가 미래에 reject patterns 변경되어도
  어댑터는 자체 가드 유지. raw_text 는 extractor 의 **반환값**으로 받는다
  (2026-09-20 이전에는 `_last_raw_response` 사이드카 속성이었다 — 동시 분석 오염).

분석-로컬 인자 규약 (2026-09-20 동시 분석 오염 수리):
  이 인식기는 pipeline/app.py 의 모듈 전역 싱글턴(`_RECOGNIZER`)으로 재사용된다.
  예전에는 caller 가 `motion_query_hint` / `unregistered_hook` 을 **속성에 써 두고**
  recognize() 가 나중에 읽었는데, 그 사이에 프레임 추출 + RTMW 추론(실측 warm 51.3초 /
  cold 176.6초)이 통째로 끼어 있었다. Pod 은 `--workers 1` + BackgroundTasks(스레드풀)
  이고 Lambda 는 ReservedConcurrentExecutions 가 없으므로, 학원처럼 동시 업로드가
  들어오면 그 창에서 B 가 A 의 값을 덮어쓴다 → A 가 **B 의 동작 이름으로** 채점되고
  예외도 로그도 남지 않는다. 지금은 둘 다 recognize() 의 키워드 인자다.

unregistered_hook 시그너처 (B3 fix):
  (keyword: str, video_hash: str) -> None
  · video_path 노출 X (PII 보호 — TERM-DATA-01 분기 3 schema 정합).
  · hook 실패 시 try/except 로 분석 흐름 계속 (D-09 case 3 graceful degrade).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field, replace
from typing import Any, Callable

from .gemini_motion_classifier import REGISTERED_MOTIONS, classify_motion_name
from .skeleton import JOINT_KEYS
from .technique_cache import _active_model_name  # 모델명 단일 출처 (raw string 금지)
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


def _moment_field(m: Any, key: str, default: Any) -> Any:
    """moment 필드 추출 — KeyMoment 객체(속성)와 cache dict(키) 양쪽 허용.

    33-A4 수리 공통 accessor: 신선 경로는 KeyMoment dataclass, 캐시 경로는
    _serialize_moment 가 저장한 dict. 두 표현을 같은 코드로 읽는다.
    """
    if isinstance(m, dict):
        return m.get(key, default)
    return getattr(m, key, default)


def _hold_window_from_moments(moments: Any) -> tuple[int, int] | None:
    """KeyMoments[hold] timestamp → (start_frame, end_frame) hold 창.

    ★★ quick-260920-ra8 (belle 승인, 2026-09-20) — **이 함수의 산출을 지금 아무도
    채점에 쓰지 않는다.** `dimensions._select_window` 가 국면 힌트를 버리고 기하 창만
    쓴다. 아래 33-A4 서술은 그때의 의도이고, 지금은 이력이다. 호출은 남아 있으므로
    `[정정 2026-09-20]` 여기 "소비처가 0"이라고 적었던 것은 **틀렸다.**
    EXTEND 채점(`_select_window`)은 더 이상 이 값을 안 보지만,
    **흔들림 채점(`dimensions._select_stability_window`, dimensions.py:366)은 아직 읽는다.**
    그리고 mode3 는 core 차원(angle/line)이 없어 종합이 stability 단독이므로
    (`overall_from_dimensions`), 이 국면 힌트가 **mode3 점수에 그대로 닿는다.**
    같은 영상 5벌에서 hold 가 8.0초/1.0초로 이봉, 2/5 오답이었다(quick-260920-ra8).
    profile.hold_window 에 값은 계속 실리고 EXTEND 쪽 소비처만 0 이다 —
    "국면 게이트가 걸려 있다"고 읽지 말 것.
      끊은 이유(Pod 실측): 같은 영상을 캐시 우회로 5번 물으니 hold 가 8.0초(정답)와
      1.0초(진입부)로 갈리고 중간값이 없었다. 1.0초를 받은 2/5 에서 정은지 정타가
      leg_extension -20 을 맞았다. 부수로 아래 `fps = 9.0` 하드코딩도 실측 rate(~9.96)
      와 어긋난다 — 되살릴 때 같이 고칠 자리다.
    근거 = .planning/quick/260920-cac-concurrency-contamination-fix/260920-cac-SUMMARY.md §17

    ── 이하 33-A4 당시 서술 (이력) ───────────────────────────────────────────
    33-A4 수리 (33-A4-PHASE-EVIDENCE §5) — yaml hold_moment 스코프를 시간축에
    구현하는 유일한 장치가 profile.hold_window 인데, 종전에는 캐시 히트 경로
    (_profile_from_cache)가 이 필드를 복원하지 않아 국면 게이트가 소실 →
    dimensions._select_window 가 국면 무관 분산 최소 자동 창으로 폴백했다.
    이제 신선 경로(_build_profile)와 캐시 경로 모두 본 함수 하나만 호출
    ("분기 0, 코드 1벌"). 특정 동작(motion) 분기 없음 — 전 동작 공통.

    박제: hold moment 2개 이상 = 첫/마지막 timestamp, 1개 = ±2초 창, 0개 = None.
    """
    if not moments:
        return None
    fps = 9.0  # frame_extractor.py target_fps (박제 정신 정합)
    try:
        ts_list = sorted(
            float(_moment_field(m, "timestamp_seconds", 0.0))
            for m in moments
            if str(_moment_field(m, "moment_key", "")) == "hold"
        )
    except (TypeError, ValueError) as exc:
        # graceful — 캐시 dict 의 timestamp 가 비수치면 자동 창 폴백 (분석 차단 X).
        log.warning("hold_window 산출 실패 (자동 창 폴백): %s", exc)
        return None
    if not ts_list:
        return None
    if len(ts_list) >= 2:
        start_sec, end_sec = ts_list[0], ts_list[-1]
    else:
        # 단일 hold moment = ±2초 window 박제
        start_sec = max(0.0, ts_list[0] - 2.0)
        end_sec = ts_list[0] + 2.0
    return (int(round(start_sec * fps)), int(round(end_sec * fps)))


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
      unregistered_hook: D-09 case 3 수집 콜백의 **인스턴스 기본값** (합성 시점 상수).
        분석마다 달라지는 값(caller uid 를 문 클로저)은 여기가 아니라
        recognize(unregistered_hook=...) 로 넘긴다 — 인자가 기본값을 이긴다.

    설정은 생성 시점, 분석별 값은 recognize() 인자 (2026-09-20, 모듈 docstring 참조).
    생성 이후의 속성 대입은 __setattr__ 이 막는다.
    """

    extractor: Any = None  # GeminiMomentExtractor (lazy)
    cache: Any = None  # TechniqueCache (Plan 5-02), default None = no-cache
    fallback: TechniqueRecognizer | None = None
    low_confidence_threshold: float = 0.5  # D-10 박제 — 5영상 sweep 후 갱신
    unregistered_hook: Callable[[str, str], None] | None = None  # 합성 시점 기본값
    # extractor lazy init 직렬화. 이 인스턴스는 전역 싱글턴이라 두 분석이 동시에
    # Step 3 에 진입할 수 있고, 락이 없으면 한쪽이 만든 인스턴스가 버려지면서
    # 캐시가 쪼개진다. _ensure_recognizer 의 double-checked locking 과 같은 규율.
    _extractor_lock: Any = field(
        default_factory=threading.Lock, init=False, repr=False, compare=False
    )
    _frozen: bool = field(default=False, init=False, repr=False, compare=False)

    # 생성 이후 대입을 막을 이름 (2026-09-20 동시 분석 오염 수리).
    #   motion_query_hint — 필드 자체가 폐기됐다. 비-frozen dataclass 는 선언되지 않은
    #     이름에도 대입이 **조용히 성공**하므로, 그냥 지우면 옛 호출자가 말없이 no-op 이
    #     된다. 그건 이 수리가 없앤 고장과 같은 종류다 — 그래서 큰 소리로 막는다.
    #   unregistered_hook — 합성 시점 상수로는 정당하다. 위험한 건 분석마다 갈아끼우는
    #     쓰기이고(caller uid 클로저), 그것만 막는다.
    _WRITE_ONCE_ATTRS = frozenset({"motion_query_hint", "unregistered_hook"})

    def __setattr__(self, name: str, value: Any) -> None:
        if name in GeminiTechniqueRecognizer._WRITE_ONCE_ATTRS and getattr(
            self, "_frozen", False
        ):
            raise AttributeError(
                f"{name} 은(는) 생성 이후 대입할 수 없다 "
                "(2026-09-20 동시 분석 오염 수리 — 이 인식기는 전역 싱글턴이라 "
                "쓰기와 읽기 사이의 포즈 추론 구간에서 다른 분석이 덮어쓴다). "
                f"recognize(..., {name.replace('motion_query_hint', 'motion_hint')}=...) "
                "키워드 인자로 넘겨라."
            )
        object.__setattr__(self, name, value)

    def __post_init__(self) -> None:
        if self.fallback is None:
            self.fallback = FallbackRecognizer()
        self._frozen = True

    def recognize(
        self,
        angles: Any,
        frames: Any = None,
        *,
        preuploaded_handle: Any = None,
        motion_hint: str | None = None,
        unregistered_hook: Callable[[str, str], None] | None = None,
    ) -> TechniqueProfile:
        """3-case fallback + reject patterns 2차 가드 + joint_expectations 빌드.

        Args:
          angles: 관절각 행렬 (T, J=8). FallbackRecognizer 위임 시 사용.
          frames: video_uri (str) — Gemini File API 입력 path. None 시 Gemini 호출 skip
                   + FallbackRecognizer 위임 (api_failure path).
          preuploaded_handle: GeminiFileSession File API 핸들(keyword-only, 27-04). 주입 시
                   moment extractor 가 업로드/폴링/delete 를 skip 하고 핸들 재사용 — 소유권=세션.
                   None 이면 기존 self-upload (byte-동일). Fallback 위임 경로엔 영향 0.
          motion_hint: 이 분석이 질의할 motion id (keyword-only, 2026-09-20).
                   None = Gemini 자체 분류("auto"). mode1 은 referenceMotionId, mode3 은 None.
                   **호출 스택을 벗어나지 않는다** — 동시 분석이 섞일 수 없는 이유.
          unregistered_hook: D-09 case 3 수집 콜백 (keyword, video_hash) -> None
                   (keyword-only, 2026-09-20). caller uid 를 클로저로 물고 오므로 분석마다
                   다른 객체다. None 이면 인스턴스 기본값(self.unregistered_hook) 사용,
                   그것도 None 이면 수집 skip.

        Returns:
          TechniqueProfile — category ∈ {"recognized", "api_failure", "low_confidence",
          "unregistered"}. dimensions.py 가 joint_expectations 만 소비 (D-08).
        """
        # 이 분석이 Gemini 에 던질 질의. 캐시 키와 프롬프트가 **같은 값**을 써야 한다 —
        # 2026-09-20 이전에는 캐시가 영상만 키로 잡아서, 같은 영상을 다른 질의로 분석하면
        # 앞 질의의 답을 물려받았다(같은 mode3 분석이 이력에 따라 100 점도 0 점도 됐다).
        motion_query = motion_hint or "auto"

        # Step 1: cache hit (질의별 — 다른 질의의 답은 히트가 아니다).
        if self.cache is not None and frames is not None:
            try:
                cached = self.cache.lookup(frames, motion_query=motion_query)
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

        # Step 3: extractor lazy init (double-checked locking — 전역 싱글턴이라
        # 두 분석이 동시에 여기 들어올 수 있다. 락이 없으면 한쪽 인스턴스가 버려지고
        # moment 캐시가 쪼개진다. _ensure_recognizer 와 같은 규율, 2026-09-20).
        if self.extractor is None:
            with self._extractor_lock:
                if self.extractor is None:
                    from sunity_shared.judging import GeminiMomentExtractor

                    self.extractor = GeminiMomentExtractor()

        # Step 4: Gemini 호출 (D-09 case 1 fallback).
        try:
            response_text, moments, raw_motion_name = self._call_extractor(
                frames,
                motion_query=motion_query,
                preuploaded_handle=preuploaded_handle,
            )
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
                motion_id=None,  # C2 fix — low_confidence path 의 motion_id 는 None
            )

        # Step 7: motion 정규화 + 미등록 (D-09 case 3).
        canonical, scope_status = self._classify_motion(raw_motion_name)
        if scope_status == "unregistered":
            log.info(
                "Gemini motion 미등록='%s' — Page 9 단독 + 자동 수집 trigger",
                raw_motion_name,
            )
            effective_hook = (
                unregistered_hook
                if unregistered_hook is not None
                else self.unregistered_hook
            )
            if effective_hook is not None:
                # B3 fix — hook 에 video_hash 전달 (video_path 박제 X, PII 미노출).
                video_hash = _compute_video_hash(frames)
                try:
                    effective_hook(raw_motion_name, video_hash)
                except Exception:  # noqa: BLE001 - hook 실패는 분석 흐름 차단 X
                    log.exception("unregistered_hook 실패 (분석 계속)")
            return TechniqueProfile(
                name=f"미등록: {raw_motion_name}",
                category="unregistered",
                joint_expectations={},
                required_split_deg=None,
                requires_hold=True,
                is_symmetric=False,
                motion_id=None,  # C2 fix — unregistered path 의 motion_id 는 None
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
                        # 실제로 이 산출을 만든 모델을 기록한다. 2026-08-28 까지
                        # "gemini-3.1-pro"(suffix 누락 = config 금지형) 로 박혀 있어
                        # 캐시 라벨이 실호출 모델과 달랐다 — 어떤 모델이 만든
                        # 판정인지 추적 불가.
                        "model": getattr(
                            self.extractor, "model_name", _active_model_name()
                        ),
                    },
                    motion_query=motion_query,
                )
            except Exception as exc:  # noqa: BLE001 - cache 실패는 분석 흐름 차단 X
                log.warning("cache.store 실패 (분석 결과 반환): %s", exc)

        return profile

    # ───────────────────────── 내부 helper ─────────────────────────

    def _call_extractor(
        self, frames: Any, *, motion_query: str, preuploaded_handle: Any = None
    ) -> tuple[str, list, str]:
        """extractor 호출 + 응답 raw text + KeyMoment list + raw motion name 반환.

        2026-09-20 — 전부 **반환값**으로 받는다. 예전에는 extractor 의
        `_last_raw_response` / `_last_motion_name` 사이드카 속성을 Gemini 왕복 **뒤에**
        getattr 로 되읽었고, extractor 인스턴스가 프로세스에 1개뿐이라 그 창에서 다른
        분석이 덮어쓸 수 있었다. `_last_motion_name` 은 애초에 이 함수가 넘긴
        motion_query 를 되받는 왕복이었을 뿐이다 (extractor 는 Gemini 의 자체 분류명을
        그 필드에 넣은 적이 없다 — 쓰기 지점이 `self._last_motion_name = motion` 하나뿐).
        preuploaded_handle(27-04) 은 그대로 전달 — 세션 핸들 재사용.
        """
        moments, raw_text = self.extractor.extract_key_moments_with_response(
            video_uri=frames,
            motion=motion_query,
            preuploaded_handle=preuploaded_handle,
        )
        return raw_text or "", list(moments), motion_query

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
        # 33-A4 수리: 창 계산은 _hold_window_from_moments 공통 함수로 이동 —
        # 캐시 히트 경로(_profile_from_cache)와 코드 1벌 공유.
        hold_window_tuple = _hold_window_from_moments(moments)

        return TechniqueProfile(
            name=motion,
            category="recognized",
            joint_expectations=expectations,
            required_split_deg=None,
            requires_hold=True,
            is_symmetric=False,
            hold_window=hold_window_tuple,
            motion_id=motion,  # C2 fix — canonical motion 이 곧 motion_id (stable key)
            # Plan 08-03 신설 (REVIEWS R6) — Phase 8 Layer 2 가 본 필드 reuse
            # (recognizer 중복 호출 영구 차단). frozen dataclass 정합으로 tuple.
            key_moments=tuple(moments) if moments else None,
        )

    def _profile_from_cache(self, cached: dict) -> TechniqueProfile:
        """cache hit 시 dict → TechniqueProfile 복원.

        C2 fix — cache 의 motion key 도 canonical name 이므로 motion_id 로 복원.
        cache 에 motion 키 없으면 motion_id = None.

        Plan 08-03 (REVIEWS Cycle 2 §3 MEDIUM) — cache 의 moments list 박제 round-trip
        검증 박제. cache hit 시 key_moments None 으로 박제되어 Layer 2 가 silently
        비활성되는 박제 영구 차단. cached["moments"] 가 list[dict] 박제이면 KeyMoment
        dataclass 로 복원 후 tuple 박제. 빈 list 또는 키 누락 시 None (Layer 2 자동
        graceful fallback + warning 'layer2_unavailable').

        33-A4 수리 (33-A4-PHASE-EVIDENCE §5 끊긴 지점 1) — hold_window 복원 추가.
        종전에는 캐시 히트 시 hold_window=None 으로 남아 yaml hold_moment 국면
        게이트가 소실 → 분산 최소 자동 창 폴백(국면 무관). 이제 신선 경로와 동일한
        _hold_window_from_moments 로 cached["moments"] raw dict 에서 직접 산출 —
        KeyMoment 복원(Layer 2) 실패와 독립적으로 국면 게이트가 살아남는다.
        """
        # REVIEWS Cycle 2 §3 MEDIUM — TechniqueCache round-trip key_moments 박제.
        key_moments_tuple: tuple | None = None
        cached_moments = cached.get("moments")
        if cached_moments:
            try:
                # lazy import — D-16 정합 (cache hit path 만 활성).
                from sunity_shared.judging.gemini_moment_extractor import KeyMoment

                restored: list = []
                for entry in cached_moments:
                    if not isinstance(entry, dict):
                        continue
                    restored.append(
                        KeyMoment(
                            motion=cached.get("motion", ""),
                            moment_key=str(entry.get("moment_key", "")),
                            timestamp_seconds=float(entry.get("timestamp_seconds", 0.0)),
                            frame_index=int(entry.get("frame_index", 0)),
                            confidence=float(entry.get("confidence", 0.0)),
                            source_response_excerpt=str(
                                entry.get("source_response_excerpt", "")
                            ),
                        )
                    )
                if restored:
                    key_moments_tuple = tuple(restored)
            except (ImportError, ValueError, TypeError) as exc:
                # graceful — cache 의 moments 가 신/구 schema 혼재 시 Layer 2
                # 자동 비활성 (warning 'layer2_unavailable'). 분석 흐름 차단 X.
                log.warning(
                    "TechniqueCache key_moments 복원 실패 (Layer 2 비활성 graceful): %s",
                    exc,
                )
                key_moments_tuple = None

        return TechniqueProfile(
            name=cached.get("motion", "cached"),
            category="recognized",
            joint_expectations=cached.get("joint_expectations", {}),
            required_split_deg=None,
            requires_hold=True,
            is_symmetric=False,
            # 33-A4 수리 — 신선 경로와 동일 함수로 국면 게이트 복원 (raw dict 입력).
            hold_window=_hold_window_from_moments(cached_moments),
            motion_id=cached.get("motion"),  # C2 fix
            key_moments=key_moments_tuple,
        )


def _serialize_moment(m: Any) -> dict:
    """KeyMoment → JSON-serializable dict (cache.store payload).

    Plan 08-03 (REVIEWS Cycle 2 §3 MEDIUM) — source_response_excerpt 박제 추가.
    TechniqueCache round-trip 시 KeyMoment 복원 박제 정합 (Phase 8 Layer 2 reuse
    가 cache hit path 도 함께 활성 박제).
    """
    return {
        "moment_key": getattr(m, "moment_key", ""),
        "timestamp_seconds": getattr(m, "timestamp_seconds", 0.0),
        "confidence": getattr(m, "confidence", 0.0),
        "frame_index": getattr(m, "frame_index", 0),
        "source_response_excerpt": getattr(m, "source_response_excerpt", ""),
    }
