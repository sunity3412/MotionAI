"""정은지 5영상 메타데이터 박제 + 신규 영상 확장 슬롯.

Spike 단계에서는 fixture (Firestore reference_motions 에서 로드된 메타) 사용.
실제 4-way 비교 시 RunPod 분석 결과 (각 path 별 RTMW 재추론) 를 PathOutput 으로 wrap.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VideoMeta:
    """정은지 5영상 + 신규 영상 메타."""
    video_id: str
    motion_category: str           # IPSF compatible: invert / backbend / split / spin / pose
    motion_name_studio: str        # 학원 통용 명칭
    motion_name_ipsf: str | None   # IPSF Code (없으면 None — 학원 자체 동작)
    is_reference: bool             # True = 정은지 reference
    notes: list[str]


# ── 정은지 5영상 (Phase 17 G4 / Phase 8.1 axis severity 케이스) ─────────────────
# motion_name_ipsf 은 NLM 박제 결과 — 후속 plan 에서 cross-check 권장.

JEONGEUNJI_5 = [
    VideoMeta(
        video_id="je-01",
        motion_category="invert",
        motion_name_studio="에어쇼",  # placeholder — Phase 16 studio term 박제
        motion_name_ipsf=None,
        is_reference=True,
        notes=["Phase 17 G4 occlusion FP 후보", "거꾸로 매달림 자세"],
    ),
    VideoMeta(
        video_id="je-02",
        motion_category="backbend",
        motion_name_studio="제이드 스플릿",
        motion_name_ipsf="Jade Split",
        is_reference=True,
        notes=["Phase 8.1 axis severity high → low fix 정합 영상"],
    ),
    VideoMeta(
        video_id="je-03",
        motion_category="split",
        motion_name_studio="에어쇼 스플릿",
        motion_name_ipsf="Aerial Split",
        is_reference=True,
        notes=["IPSF Page 19 split angle all perspectives 정합 case"],
    ),
    VideoMeta(
        video_id="je-04",
        motion_category="spin",
        motion_name_studio="페어 스핀",
        motion_name_ipsf="Pair Spin",
        is_reference=True,
        notes=["회전 동작 occlusion 빈번 — Phase 4 trigger 후보 D-04.d"],
    ),
    VideoMeta(
        video_id="je-05",
        motion_category="pose",
        motion_name_studio="앵글 포지션",
        motion_name_ipsf=None,
        is_reference=True,
        notes=["기본 포징 — baseline reference"],
    ),
]


def get_dataset() -> list[VideoMeta]:
    """Spike 평가에 사용할 영상 메타 list. 신규 영상 추가 시 여기서 확장."""
    return list(JEONGEUNJI_5)


def get_by_motion_category(category: str) -> list[VideoMeta]:
    return [v for v in get_dataset() if v.motion_category == category]
