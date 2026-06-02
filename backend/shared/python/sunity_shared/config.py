"""sunity_shared 런타임 설정 (Plan 01-21 Task 2).

POSE_ENGINE 환경변수 → get_pose_engine() 팩토리.

D-21 박제: POSE_ENGINE = 'RTMW' (기본) 또는 'NLF_SMPLX' (R&D 전용).
T-21-03 mitigation: 운영 환경에서 'NLF_SMPLX' 설정 시 경고 로그.
  (실제 차단은 plan 25 의 pipeline atomic swap 이 POSE_ENGINE=RTMW 강제)

사용:
  from sunity_shared.config import get_pose_engine
  engine_key = get_pose_engine()  # 'RTMW' 또는 'NLF_SMPLX'
"""

from __future__ import annotations

import logging
import os
from typing import Literal

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# D-21 박제: 유효한 POSE_ENGINE 값 집합
_VALID_POSE_ENGINES: frozenset[str] = frozenset({"RTMW", "NLF_SMPLX"})

# 기본값 = RTMW (운영 백본, D-17/D-21)
_DEFAULT_POSE_ENGINE = "RTMW"


def get_pose_engine() -> Literal["RTMW", "NLF_SMPLX"]:
    """POSE_ENGINE 환경변수 → 현재 활성 pose engine key 반환.

    D-21 박제:
      - POSE_ENGINE 미설정 → 'RTMW' (기본값, 운영 백본)
      - POSE_ENGINE='NLF_SMPLX' → 'NLF_SMPLX' (R&D 전용)

    T-21-03 mitigation:
      - NLF_SMPLX 선택 시 경고 로그 (운영 오설정 감지용)

    Returns:
        'RTMW' 또는 'NLF_SMPLX'

    Raises:
        ValueError: 유효하지 않은 POSE_ENGINE 값.
    """
    value = os.getenv("POSE_ENGINE", _DEFAULT_POSE_ENGINE).strip().upper()

    if value not in _VALID_POSE_ENGINES:
        raise ValueError(
            f"POSE_ENGINE='{value}' 는 유효하지 않음. "
            f"허용값: {sorted(_VALID_POSE_ENGINES)}. "
            "운영 환경: POSE_ENGINE=RTMW (기본). R&D 전용: POSE_ENGINE=NLF_SMPLX."
        )

    if value == "NLF_SMPLX":
        log.warning(
            "POSE_ENGINE=NLF_SMPLX 선택됨. R&D 전용 경로 — 운영 배포 시 확인 필요 (T-21-03)."
        )

    return value  # type: ignore[return-value]
