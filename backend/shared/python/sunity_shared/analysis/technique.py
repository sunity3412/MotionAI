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
from typing import Protocol

import numpy as np

from .skeleton import JOINT_KEYS

# 관절 기대 상태 — line(신전) 채점이 이 값으로 갈린다.
JOINT_EXTEND = "extend"    # 완전 신전(≈180°) 요구 → 부족분이 라인 감점
JOINT_BENT_OK = "bent_ok"  # 의도적 굽힘 허용 → 라인 감점 대상 아님
JOINT_CONTACT = "contact"  # 그립/접촉 관절 → 라인 평가 제외

# fallback 이 '명백히 펴려는' 관절만 EXTEND 로 추론할 때 쓰는 신전 영역 임계.
_EXTENSION_ZONE_DEG = 150.0
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
    # (start_frame, end_frame) tuple. dimensions.line_score / stability_score 가
    # 자동 추출 (분산 최소 sub-window) 대신 이 윈도우 사용 (None = 자동 추출 fallback).
    # 사용자 영상의 standing setup/dismount frame 잡힘 위양성 박제 정신 정합 fix.
    hold_window: tuple[int, int] | None = None
    # C2 fix (2026-06-08, Plan 06-02 reviews) + R1 fix (2026-06-08 round-2).
    # Gemini canonical motion name 을 reference 컬렉션 lookup 의 stable key 로
    # 박제. None 가능 (FallbackRecognizer / Gemini low_confidence / unregistered
    # path 등). 위치 = dataclass 맨 끝 (hold_window 뒤) — R1 fix: default 있는
    # 필드는 non-default 필드 뒤에 와야 dataclass import 거부 회피. Plan 06-02
    # 의 mode3-first Gemini fallback path 가 본 필드를 사용해
    # firestore_admin.get_reference_motion(motion_id) exact-match 수행.
    motion_id: str | None = None

    def expects_extension(self, joint_key: str) -> bool:
        return self.joint_expectations.get(joint_key) == JOINT_EXTEND


class TechniqueRecognizer(Protocol):
    """영상/관절각 → TechniqueProfile. 구현체는 swappable (Fallback/Gemini/Pole-arina)."""

    def recognize(self, angles, frames=None) -> TechniqueProfile: ...


class FallbackRecognizer:
    """인식 모델 없이 보수적으로 프로파일을 만든다.

    철학: **모르면 깎지 않는다(위양성 방지).** 홀딩 대표 포즈에서 명백히 신전
    영역(≥150°)에 든 팔꿈치/무릎만 EXTEND 로 보고, 굽은 사지는 BENT_OK(의도일 수
    있음). 대칭 가정 안 함(폴 동작은 비대칭이 정상). 진짜 기술별 기대치는 Gemini/
    Pole-arina 어댑터가 들어오면 채워진다.
    """

    def recognize(self, angles, frames=None) -> TechniqueProfile:
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
