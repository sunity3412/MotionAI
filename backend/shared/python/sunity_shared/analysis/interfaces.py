"""무거운 모델/외부 의존성 경계 (프로토콜 + 어댑터 위치).

알고리즘 코어(features/temporal/motiondtw/kismam/assemble)는 모델 무관·검증됨.
아래 어댑터가 코어와 무거운 의존성을 잇는다 — 구현은 같은 디렉터리 모듈:
  - FrameExtractor : 영상 → 프레임 (ffmpeg)         → frame_extractor.py
  - PoseEstimator  : 프레임 → 3D keypoints (NLF)    → pose_estimator.py
  - CoachWriter    : Top-3 편차 → 자연어 코칭 (LLM)  → coach_writer.py

CoachWriter 만 graceful: 키 미설정·실패 시 빈 dict → assemble 이 수치 기반
폴백 문장 사용(가짜 수치 생성 아님 — 실제 편차값으로 서술).
"""

from __future__ import annotations

from typing import Protocol

import numpy as np


class FrameExtractor(Protocol):
    def extract(self, local_video_path: str) -> np.ndarray:
        """영상 경로 → 프레임 배열 (T,H,W,3) RGB uint8."""
        ...


class PoseEstimator(Protocol):
    def estimate(self, frames: np.ndarray) -> np.ndarray:
        """프레임 → 3D keypoints (T,17,4=x,y,z,uncertainty). 미감지 시 NoHumanError."""
        ...


class CoachWriter(Protocol):
    def write(self, context: dict) -> dict:
        """{joint_key: 코칭문장}. 키 미설정/실패 시 {} 반환 허용."""
        ...


class NoHumanError(Exception):
    """프레임에서 사람을 찾지 못함 → contract no_human 으로 매핑."""


class NotPoleMotionError(Exception):
    """mode1 비교 시 KISMAM similarity 가 임계값(models.NOT_POLE_SIMILARITY_THRESHOLD)
    미만 → 비폴 영상으로 추정. contract not_pole_motion 으로 매핑 (belle P1 #8).
    위양성 방지를 위해 보수적 임계값 채택 — 시연 데이터로 튜닝."""


class FallbackCoachWriter:
    """Cerebras 미연결 시의 무해한 폴백 — 문장 생성을 assemble 폴백에 위임."""

    def write(self, context: dict) -> dict:
        return {}
