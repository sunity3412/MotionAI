"""기술 인식 → IPSF 채점을 위한 기술 프로파일 (docs/research/폴스포츠-지식.md 보고서 5·6).

IPSF 심사는 '기술 조건부'다: 같은 굽은 무릎이 Attitude(의도)면 정답, Pencil(직선
요구)이면 감점. 따라서 채점 전에 '무슨 기술인지' + '각 관절이 펴져야 하는지'를 알아야
한다. 이 모듈은 그 정보를 담는 TechniqueProfile 과, 그것을 만드는 TechniqueRecognizer
프로토콜을 정의한다.

인식 층은 swappable: 지금은 보수적 FallbackRecognizer(모르면 깎지 않음), 나중엔
도메인 분류기(Pole-arina식) 또는 Gemini 비디오 어댑터로 교체. 채점 층(dimensions.py)은
프로토콜만 의존하므로 어댑터를 갈아끼워도 변경 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Protocol

import numpy as np

from .skeleton import JOINT_KEYS

if TYPE_CHECKING:
    # Plan 08-03 신설 — Phase 8 Layer 2 가 본 필드 reuse (recognizer 중복 호출
    # 영구 차단, REVIEWS R6). lazy import (TYPE_CHECKING) — 본 모듈은 judging
    # 패키지 의존 0 유지.
    from ..judging.gemini_moment_extractor import KeyMoment

# 관절 기대 상태 — line(신전) 채점이 이 값으로 갈린다.
JOINT_EXTEND = "extend"    # 완전 신전(≈180°) 요구 → 부족분이 라인 감점
JOINT_BENT_OK = "bent_ok"  # 의도적 굽힘 허용 → 라인 감점 대상 아님
JOINT_CONTACT = "contact"  # 그립/접촉 관절 → 라인 평가 제외

# fallback 이 '명백히 펴려는' 관절만 EXTEND 로 추론할 때 쓰는 신전 영역 임계.
_EXTENSION_ZONE_DEG = 150.0

# ── 스플릿 라인 요소 (quick-260925-nnt) ─────────────────────────────────────────────────────────────
# 동작이 끝날 때 두 다리를 **1자로 쫙** 벌려야 하는 기준 동작(IPSF split-line). belle 2026-09-25 power-spin
# 봉인 정답: "다리 벌림이 다르다 = 1자로 쫙 벌려졌는가, 조금만 벌려졌는가". 여기 든 동작만 split_phase(마지막 국면
# 사이각 중앙값, 정은지 상대)가 `split_angle` 감점 seed 를 낸다 — 비-스플릿 동작(kip-up 등)에서 2D 사이각이
# 위양성을 내던 06-27 사고 재발 방지(belle #1 = 위양성 0). 인식기의 required_split_deg 와 OR 로 게이트.
# 값 = 기준 doc motionId(referenceMotionId). 이 표에 넣는 것은 "그 동작이 스플릿 요소다"라는 도메인 선언이지
# 영상별 조절이 아니다 — 검증은 정타(같은 테이크, 부족분 ≈ 0)와 봉인 시험지에서.
SPLIT_LINE_ELEMENTS: frozenset[str] = frozenset({"ref-power-spin"})
# 신전 평가 대상 사지(팔꿈치/무릎). 어깨/고관절은 '폄' 의미가 모호해 제외.
_EXTENSION_JOINTS = ("left_elbow", "right_elbow", "left_knee", "right_knee")


@dataclass(frozen=True)
class TechniqueProfile:
    """인식 층이 채점 층에 넘기는 기술 정보.

    joint_expectations 에 없는 관절은 평가 제외(BENT_OK 와 동일 취급).
    """

    name: str  # 표시용 기술명("미상" 가능)
    category: str  # flexibility | strength | spin | transition | unknown
    joint_expectations: dict[str, str]  # JOINT_KEYS → JOINT_EXTEND/BENT_OK/CONTACT
    required_split_deg: float | None = None  # 스플릿/수평 요구 각(없으면 None)
    requires_hold: bool = True  # 완성포즈 2초 유지 평가 여부
    is_symmetric: bool = False  # 좌우 대칭이 기대되는 기술인지(폴은 대부분 False)
    # Path H production 정합 (2026-06-05): Gemini KeyMoments 의 hold timestamp →
    # (start_frame, end_frame) tuple.
    #
    # ★ quick-260920-ra8 (belle 승인, 2026-09-20) — **이 값은 현재 채점에 닿지 않는다.**
    # `dimensions._select_window` 가 국면 힌트를 버리고 기하 창(분산 최소)만 쓰도록
    # 바뀌었다. 이유: 인식기가 같은 영상에 hold 를 8.0초(정답)와 1.0초(진입부)로
    # 번갈아 답해 정은지 정타에 leg_extension -20 위양성을 냈다(5회 중 2회).
    # 필드와 산출 경로는 **되살릴 때를 위해 남긴다** — 국면 인식이 고쳐지면 여기가
    # 다시 꽂히는 자리다. 지우지 말고, 쓴다고 가정하지도 말 것.
    # 근거 = .planning/quick/260920-cac-concurrency-contamination-fix/260920-cac-SUMMARY.md §17
    hold_window: tuple[int, int] | None = None
    # C2 fix (2026-06-08, Plan 06-02 reviews) + R1 fix (2026-06-08 round-2).
    # Gemini canonical motion name 을 reference 컬렉션 lookup 의 stable key 로
    # 박제. None 가능 (FallbackRecognizer / Gemini low_confidence / unregistered
    # path 등). 위치 = dataclass 맨 끝 (hold_window 뒤) — R1 fix: default 있는
    # 필드는 non-default 필드 뒤에 와야 dataclass import 거부 회피. Plan 06-02
    # 의 mode3-first Gemini fallback path 가 본 필드를 사용해
    # firestore_admin.get_reference_motion(motion_id) exact-match 수행.
    motion_id: str | None = None
    # Plan 08-03 신설 (REVIEWS R6 정합) — Phase 8 Layer 2 가 본 필드 reuse
    # (GeminiTechniqueRecognizer 가 추출 후 박제, force_signals.py 가 reuse —
    # 신규 GeminiMomentExtractor singleton 영구 차단). frozen dataclass 정합으로
    # tuple 사용. None = Gemini 미호출 또는 추출 실패 path (FallbackRecognizer
    # 등) — Phase 8 Layer 2 가 본 필드 None 시 Layer 1 단독 + warning
    # 'layer2_unavailable' 자동 박제.
    key_moments: tuple["KeyMoment", ...] | None = None

    def expects_extension(self, joint_key: str) -> bool:
        return self.joint_expectations.get(joint_key) == JOINT_EXTEND


class TechniqueRecognizer(Protocol):
    """영상/관절각 → TechniqueProfile. 구현체는 swappable (Fallback/Gemini/Pole-arina).

    분석-로컬 인자 규약 (2026-09-20, 동시 분석 오염 수리):
      분석마다 달라지는 값은 **전부 키워드 인자**로 받는다. 인스턴스 속성에 담으면
      안 된다. 이유 = 구현체가 모듈 전역 싱글턴으로 재사용된다(pipeline/app.py 의
      `_RECOGNIZER`). 속성에 쓰고 나중에 읽으면 그 사이의 포즈 추론 구간(실측 warm
      51.3초 / cold 176.6초)에 다른 분석이 덮어쓴다 — 예외 0, 로그 0, 숫자는 멀쩡한
      채로 **남의 동작 기준으로 채점**된다. 선례 = `preuploaded_handle`(27-04).

      · motion_hint: 이 분석이 질의할 motion id. None = 인식기 자체 분류("auto").
      · unregistered_hook: 미등록 동작 수집 콜백 (keyword, video_hash) -> None.
        caller uid 를 클로저로 물고 오므로 분석마다 다른 객체다.
    """

    def recognize(
        self,
        angles,
        frames=None,
        *,
        preuploaded_handle=None,
        motion_hint: str | None = None,
        unregistered_hook: Callable[[str, str], None] | None = None,
    ) -> TechniqueProfile: ...


class FallbackRecognizer:
    """인식 모델 없이 보수적으로 프로파일을 만든다.

    철학: **모르면 깎지 않는다(위양성 방지).** 홀딩 대표 포즈에서 명백히 신전
    영역(≥150°)에 든 팔꿈치/무릎만 EXTEND 로 보고, 굽은 사지는 BENT_OK(의도일 수
    있음). 대칭 가정 안 함(폴 동작은 비대칭이 정상). 진짜 기술별 기대치는 Gemini/
    Pole-arina 어댑터가 들어오면 채워진다.
    """

    def recognize(
        self,
        angles,
        frames=None,
        *,
        preuploaded_handle=None,
        motion_hint: str | None = None,
        unregistered_hook: Callable[[str, str], None] | None = None,
    ) -> TechniqueProfile:
        # 27-04: preuploaded_handle 는 Gemini 어댑터 전용 — Fallback 은 영상 미사용이라 무시.
        # 2026-09-20: motion_hint / unregistered_hook 도 Gemini 전용 — Fallback 은
        # 기하만 보고 판단하므로 질의도 미등록 수집도 하지 않는다. graceful 무시.
        a = np.asarray(angles, dtype=float)
        if a.ndim == 2 and a.shape[0] > 0:
            rep = np.mean(a, axis=0)
        else:
            rep = np.zeros(len(JOINT_KEYS))
        expectations: dict[str, str] = {}
        for i, key in enumerate(JOINT_KEYS):
            if key in _EXTENSION_JOINTS and i < rep.shape[0]:
                expectations[key] = (
                    JOINT_EXTEND if float(rep[i]) >= _EXTENSION_ZONE_DEG else JOINT_BENT_OK
                )
            else:
                expectations[key] = JOINT_BENT_OK
        return TechniqueProfile(
            name="미상",
            category="unknown",
            joint_expectations=expectations,
            required_split_deg=None,
            requires_hold=True,
            is_symmetric=False,
        )
