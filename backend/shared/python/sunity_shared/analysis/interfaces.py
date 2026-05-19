"""무거운 모델/외부 의존성 경계 (프로토콜 + #7-follow stub).

알고리즘 코어(features/motiondtw/kismam/assemble)는 모델 무관·검증됨.
아래 어댑터는 AWS 컨테이너·가중치·Cerebras 키 준비 후 구현(#7-follow):
  - FrameExtractor : 영상 → 프레임 (ffmpeg)
  - PoseEstimator  : 프레임 → keypoints (YOLO11 인체 → ViTPose-S 17점)
  - CoachWriter    : Top-3 편차 → 자연어 코칭 (Cerebras LLM)

CoachWriter 만 graceful: 미구현 시 빈 dict → assemble 이 수치 기반 폴백 문장
사용(가짜 수치 생성 아님 — 실제 편차값으로 서술). FrameExtractor/PoseEstimator
는 결과를 위조할 수 없으므로 명시적 NotImplementedError.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np


class FrameExtractor(Protocol):
    def extract(self, local_video_path: str) -> np.ndarray:
        """영상 경로 → 프레임 배열. (구현: ffmpeg, #7-follow)"""
        ...


class PoseEstimator(Protocol):
    def estimate(self, frames: np.ndarray) -> np.ndarray:
        """프레임 → keypoints (T,17,3=x,y,conf). 인체 미감지 시 NoHumanError."""
        ...


class CoachWriter(Protocol):
    def write(self, context: dict) -> dict:
        """{joint_key: 코칭문장}. 미구현/실패 시 {} 반환 허용."""
        ...


class NoHumanError(Exception):
    """프레임에서 사람을 찾지 못함 → contract no_human 으로 매핑."""


# ── #7-follow 까지의 stub ────────────────────────────────────────────
class NotImplementedFrameExtractor:
    def extract(self, local_video_path: str) -> np.ndarray:
        raise NotImplementedError(
            "FrameExtractor 미구현(#7-follow): ffmpeg 프레임 추출. "
            "Lambda 컨테이너 패키징 전환 시 구현."
        )


class NotImplementedPoseEstimator:
    def estimate(self, frames: np.ndarray) -> np.ndarray:
        raise NotImplementedError(
            "PoseEstimator 미구현(#7-follow): YOLO11→ViTPose-S. "
            "모델 가중치 + 컨테이너 준비 후 구현."
        )


class FallbackCoachWriter:
    """Cerebras 미연결 동안의 무해한 폴백 — 문장 생성을 assemble 폴백에 위임."""

    def write(self, context: dict) -> dict:
        return {}
