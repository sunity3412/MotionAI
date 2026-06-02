"""무거운 모델/외부 의존성 경계 (프로토콜 + 어댑터 위치).

알고리즘 코어(features/temporal/motiondtw/kismam/assemble)는 모델 무관·검증됨.
아래 어댑터가 코어와 무거운 의존성을 잇는다 — 구현은 같은 디렉터리 모듈:
  - FrameExtractor : 영상 → 프레임 (ffmpeg)         → frame_extractor.py
  - PoseEstimator  : 프레임 → 3D keypoints (NLF)    → pose_estimator.py  (DEPRECATED)
  - PoseEngine     : 프레임 → list[PoseFrame] (신규) → pose_engines/ 디렉터리
  - CoachWriter    : Top-3 편차 → 자연어 코칭 (LLM)  → coach_writer.py

CoachWriter 만 graceful: 키 미설정·실패 시 빈 dict → assemble 이 수치 기반
폴백 문장 사용(가짜 수치 생성 아님 — 실제 편차값으로 서술).

Phase 1 변경:
  PoseEngine Protocol 추가 (Plan 01-02 Task 1).
  estimate(frames, pole_axis) -> list[PoseFrame] 시그니처 강제.
  RESEARCH §Pattern 1 / D-04 / REVIEWS H-3 (pole_axis 인자 전달) 박제.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import numpy as np

if TYPE_CHECKING:
    from .pose_frame import PoleAxis, PoseFrame


class FrameExtractor(Protocol):
    def extract(self, local_video_path: str) -> np.ndarray:
        """영상 경로 → 프레임 배열 (T,H,W,3) RGB uint8."""
        ...


# DEPRECATED: PoseEngine으로 마이그레이션 중 (Phase 1 D-04). 신규 코드는 PoseEngine 사용.
class PoseEstimator(Protocol):
    def estimate(self, frames: np.ndarray) -> np.ndarray:
        """프레임 → 3D keypoints (T,17,4=x,y,z,uncertainty). 미감지 시 NoHumanError."""
        ...


class PoseEngine(Protocol):
    """프레임 시퀀스 → PoseFrame 리스트. 미감지 시 NoHumanError.

    PoseEstimator(구버전, DEPRECATED) 를 대체하는 신규 Protocol.
    RESEARCH §Pattern 1 / D-04 / D-05 / D-12 / REVIEWS H-3 (pole_axis 인자) 박제.

    RTMW pivot 박제 (2026-06-02, Plan 01-19 / D-17~D-25):

      D-17: 운영 백본 = rtmlib RTMW 133 wholebody (Apache-2.0).
            본 Protocol 은 RTMW 와 NLF_SMPLX 양쪽을 모두 만족해야 함 —
            구현체만 교체 가능하도록 backend-agnostic 으로 유지.
      D-20: 원본 저장은 RTMW 133 풀 키포인트, 스코어링 계약은 COCO-17 + 폴 확장.
            어댑터(`RTMW133ToCOCO17Adapter` 등) 가 변환을 담당하며 본 Protocol
            반환은 어댑터 결과인 PoseFrame.
      D-21: PoseFrame.body_shape 는 nullable —
            RTMW path = None, NLF_SMPLX path = BodyNormalizationProfile 채움.
      D-24: 본 모듈은 어떤 백본 구현체(rtmlib/mediapipe/torch/ultralytics) 도
            직접 import 하지 않는다. 다운스트림 분석 레이어
            (features/temporal/motiondtw/kismam/dimensions/assemble/technique)
            는 본 Protocol 에만 의존하며, 백본 변경 시 재작성 금지.

    PoseFrame 은 raw 33 landmarks (저장은 항상) + COCO-17 derived (스코어링용) +
    폴 확장 (toe/heel/grip) + pole-aligned 좌표 (D-12) +
    visibility/presence/confidence/uncertainty_proxy (D-05) 모두 포함.

    pole_axis 인자: 영상 전체 평균 축 (D-10). PoleDetector 에서 산출돼 엔진으로
    주입. 엔진이 pole alignment 까지 직접 책임지면 어댑터별 로직 중복 방지
    (H-3 박제).

    구현체 위치:
      backend/shared/python/sunity_shared/analysis/pose_engines/  (운영)
      backend/research/pose_engines/                              (R&D 격리)
    """

    def estimate(
        self,
        frames: np.ndarray,       # (T,H,W,3) RGB uint8
        pole_axis: "PoleAxis",    # PoleDetector 산출 (D-10/D-11)
    ) -> "list[PoseFrame]":
        """프레임 시퀀스 → list[PoseFrame]. 전 프레임 미감지 시 NoHumanError."""
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
