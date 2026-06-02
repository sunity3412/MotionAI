"""RTMW3DPoseEngine — 옵션 A 어댑터 stub (Plan 01-22 비선택, R&D 격리 대상).

D-18 옵션 A: 단일 카메라 3D path = RTMW3D 직접 사용 (rtmlib RTMW3D 변형).
  RTMW 133 → (x, y, z, score) 단일 추론 → RTMW133ToCOCO17Adapter → PoseFrame.

본 파일 = belle = "approved: option_b" (2026-06-03, 본 plan
`three_d_path_decision.md` §5 박제) 으로 인해 옵션 A 비선택. 따라서
NotImplementedError stub 유지. 본 모듈은 plan 24 R&D 격리 대상 — plan 24 가
`backend/research/pose_engines/` 트리로 이동 또는 stub 잔존 결정.

PoseEngine Protocol 호환 (D-24):
  estimate(frames: np.ndarray, pole_axis: PoleAxis) → list[PoseFrame]
  호출자는 본 엔진과 RTMWPoseEngine/MediaPipePoseEngine 을 동일 인터페이스로 사용.

H-2 박제: rtmlib/mmpose/mmcv module-level import 0. 모든 heavy import 는
  create_with_inferencer 팩토리 또는 estimate() 내 lazy.

D-25 박제: __init__ 가 weights_manifest 의 RTMW3D entry (production_eligible=true)
  확인 후 LicenseViolationError 가드. Plan 21 RTMWPoseEngine 의 _load_eligible_weight
  와 동일 정책 — 단, "name" 필드가 "rtmw3d" prefix 포함 entry 만 허용.

Plan 22 Task 1 (현재 상태):
  - 클래스 + Protocol 시그니처 박제 완료.
  - __init__ 가 manifest 검사 통과 가능 (LicenseViolationError 정상 raise 동작).
  - estimate() 는 NotImplementedError raise — 옵션 A 미선택 stub.
  - Task 2 (belle 결정 = option_a) 후 실 구현 진행.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from ...pose_frame import PoseFrame, PoleAxis
from .rtmw_engine import LicenseViolationError

# rtmlib/mmpose/mmcv 은 module-level import 금지 (H-2 박제).
# 인스턴스화 시점 (create_with_inferencer) 또는 estimate() 내부에서만 lazy import.

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

_DEFAULT_MANIFEST_PATH = Path(__file__).parent / "weights_manifest.json"

# 옵션 A 가중치 식별자 (manifest entry name prefix)
_RTMW3D_NAME_PREFIX = "rtmw3d"


# ── RTMW3DPoseEngine (stub) ───────────────────────────────────────────────

class RTMW3DPoseEngine:
    """rtmlib RTMW3D 단일 카메라 3D 어댑터 (옵션 A, PoseEngine Protocol 구현 stub).

    Plan 22 Task 1 단계 = stub. estimate() 호출 시 NotImplementedError.
    Task 2 belle = "option_a" 응답 후 실 구현:
      1. rtmlib lazy import (Wholebody 의 3D variant 또는 RTMW3D ONNX runtime).
      2. (T, 133, 3) keypoints + (T, 133) scores 산출.
      3. RTMW133ToCOCO17Adapter 로 PoseFrame (z 채움) 변환.
      4. pole_axis 보존 (H-3).
      5. 전 프레임 미감지 시 NoHumanError.

    DI 패턴: create_with_inferencer(inferencer, manifest_path) — 단위 테스트용
    (Plan 21 RTMWPoseEngine 와 동일 패턴).
    """

    def __init__(
        self,
        manifest_path: Path | None = None,
        target_fps: int = 30,
    ) -> None:
        """RTMW3DPoseEngine 초기화 — manifest gate 검증 (D-25).

        Plan 22 Task 1: __init__ 자체는 manifest 검사 통과 가능하지만,
        production_eligible RTMW3D entry 가 없으면 LicenseViolationError raise.
        현재 `weights_manifest.json` 의 `rtmw3d-x-384x288` 는
        `production_eligible: false` (Plan 20 audit) — belle 가 옵션 A 채택 +
        가중치 승급 결정 후에야 RTMW3DPoseEngine() 인스턴스화 성공.

        Args:
            manifest_path: weights_manifest.json 경로. None 이면 기본 경로 사용.
            target_fps: 영상 target FPS.

        Raises:
            LicenseViolationError: production_eligible=true 인 RTMW3D 가중치 0개.
            FileNotFoundError: manifest 파일 없음.
            NotImplementedError: rtmlib RTMW3D 추론자 초기화 미구현 (옵션 A 미선택 stub).
        """
        resolved = Path(manifest_path) if manifest_path else _DEFAULT_MANIFEST_PATH
        selected_weight = _load_eligible_rtmw3d_weight(resolved)
        log.info(
            "RTMW3DPoseEngine init weight=%s input_size=%s",
            selected_weight["name"],
            selected_weight.get("input_size"),
        )

        # 옵션 A 미선택 stub — rtmlib RTMW3D 추론자 초기화 미구현.
        # Task 2 belle = "option_a" 후 본 분기 제거 + rtmlib lazy import 진행.
        raise NotImplementedError(
            "RTMW3DPoseEngine 은 옵션 A 미선택 stub 상태입니다 "
            "(Plan 01-22 Task 1). belle 가 three_d_path_decision.md §5 에 "
            "`selected: option_a` 박제 후 Task 2 에서 본 __init__ 의 rtmlib "
            "lazy import + RTMW3D inferencer 초기화를 구현하세요. "
            f"manifest selected weight: {selected_weight['name']}"
        )

    @classmethod
    def create_with_inferencer(
        cls,
        inferencer: Any,
        manifest_path: Path | str | None = None,
        target_fps: int = 30,
    ) -> "RTMW3DPoseEngine":
        """DI factory — 단위 테스트가 mock inferencer 주입 (옵션 A stub).

        Plan 22 Task 1: factory 도 manifest 검사는 통과시키되, 인스턴스 반환은
        가능 (estimate() 호출 시점에 NotImplementedError raise). Task 2 belle
        = "option_a" 응답 후 실 구현 진행 시 본 factory 가 단위 테스트 진입점.

        Args:
            inferencer: callable(frames_batch) → (keypoints_3d, scores)
                        — rtmlib RTMW3D mock. 출력 형식: ((N, 133, 3), (N, 133)).
            manifest_path: weights_manifest.json 경로.
            target_fps: 영상 target FPS.
        """
        resolved = Path(manifest_path) if manifest_path else _DEFAULT_MANIFEST_PATH
        selected_weight = _load_eligible_rtmw3d_weight(resolved)

        instance = cls.__new__(cls)
        instance._inferencer = inferencer
        instance._selected_weight = selected_weight
        instance._target_fps = target_fps
        return instance

    def estimate(
        self,
        frames: np.ndarray,
        pole_axis: PoleAxis,
    ) -> list[PoseFrame]:
        """프레임 시퀀스 → list[PoseFrame] (RTMW3D 직접 3D, z 채움).

        Plan 22 Task 1 stub: NotImplementedError raise.
        Task 2 belle = "option_a" 응답 후 실 구현:
          1. for t in range(T): inferencer(frames[t]) → ((1, 133, 3), (1, 133)).
          2. RTMW133ToCOCO17Adapter 가 z 좌표 채워서 PoseFrame 변환.
          3. 전 프레임 미감지 시 NoHumanError.

        Args:
            frames: (T, H, W, 3) RGB uint8 배열.
            pole_axis: PoleDetector 산출 PoleAxis (D-10/H-3).

        Returns:
            list[PoseFrame] — len = T (실 구현 후).

        Raises:
            NotImplementedError: 옵션 A 미선택 stub (Plan 22 Task 1 현재 상태).
        """
        raise NotImplementedError(
            "RTMW3DPoseEngine.estimate() 는 옵션 A 미선택 stub 입니다 "
            "(Plan 01-22 Task 1). belle 가 three_d_path_decision.md §5 에 "
            "`selected: option_a` 박제 후 Task 2 에서 본 메서드의 RTMW3D 추론 "
            "+ RTMW133ToCOCO17Adapter 변환 흐름을 구현하세요. "
            f"입력 형상: frames={frames.shape}, pole_axis={pole_axis!r}."
        )


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────

def _load_eligible_rtmw3d_weight(manifest_path: Path) -> dict:
    """manifest 로드 → production_eligible=true + name prefix='rtmw3d' entry 선택.

    D-25 hard gate (옵션 A 한정): production_eligible=true + name 이 "rtmw3d"
    로 시작하는 entry 가 0개면 LicenseViolationError. 현재 manifest 의
    `rtmw3d-x-384x288` 은 production_eligible=false 박제 — belle 가 옵션 A
    선택 + 가중치 승급 결정 (`belle_decision` 블록 + production_eligible=true)
    후에야 본 함수 통과 가능.

    Returns:
        첫 번째 production_eligible=true 인 RTMW3D entry.

    Raises:
        LicenseViolationError: eligible RTMW3D 가중치 0개.
        FileNotFoundError: manifest 파일 없음.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"weights_manifest.json 없음: {manifest_path}. "
            "Plan 01-20 산출 파일 확인."
        )

    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    eligible = [
        w
        for w in manifest.get("weights", [])
        if w.get("production_eligible") is True
        and isinstance(w.get("name"), str)
        and w["name"].lower().startswith(_RTMW3D_NAME_PREFIX)
    ]
    if not eligible:
        raise LicenseViolationError(
            f"weights_manifest.json 에 production_eligible=true 인 RTMW3D "
            f"(name prefix='{_RTMW3D_NAME_PREFIX}') 가중치 없음. "
            f"D-25 라이선스 게이트 실패. manifest: {manifest_path}. "
            "Plan 01-22 Task 2 (belle 옵션 A 선택 + 가중치 승급 결정) 완료 여부 확인."
        )

    selected = eligible[0]
    log.info(
        "RTMW3DPoseEngine weight selected name=%s license_status=%s",
        selected.get("name"),
        selected.get("license_status"),
    )
    return selected
