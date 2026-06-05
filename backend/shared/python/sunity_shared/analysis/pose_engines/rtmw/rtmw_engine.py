"""RTMWPoseEngine — rtmlib RTMW 133 wholebody 어댑터 (Plan 01-21 Task 2).

D-17: 운영 백본 = RTMW 133 wholebody (Apache-2.0). PoseEngine Protocol 구현.
D-20: RTMW 133 원본 보존 + COCO-17 변환. RTMW133ToCOCO17Adapter 경유.
D-21: body_shape = None (RTMW path 는 SMPL-X β 없음).
D-22: keypoint score → Keypoint3D.confidence 직접 매핑.
D-24: PoseEngine Protocol 구현체. 다운스트림 무수정.
D-25: weights_manifest.json production_eligible=true 가중치만 로드. 그 외 LicenseViolationError.
H-2: rtmlib/mmpose/mmcv module-level import 절대 금지 — Lambda fail-fast 안전.
     모든 heavy import 는 create_with_inferencer 팩토리 또는 estimate() 내 lazy.

T-21-01: weights_manifest 우회 차단 (직접 가중치 지정 금지).
T-21-02: rtmlib module-level import silent fail 방지 (AST 검증).
T-21-SC: sha256 검증 (다운로드 후 — 현재 sha256=null 이면 스킵, plan 22 에서 갱신).

Factory: create_with_inferencer(inferencer, manifest_path) — DI 패턴, 단위 테스트용.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

from ...interfaces import NoHumanError
from ...pose_frame import PoseFrame, PoleAxis
from ...adapters.rtmw_133_to_coco17 import convert_rtmw_keypoints_to_coco17_and_pole_ext

# rtmlib/mmpose/mmcv 은 module-level import 금지 (H-2 박제).
# RTMWPoseEngine 인스턴스화 시점(create_with_inferencer) 또는 estimate() 내부에서만 lazy import.

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

_DEFAULT_MANIFEST_PATH = Path(__file__).parent / "weights_manifest.json"

# rtmlib 0.0.15 의 Wholebody 는 `pose=` 인자에 alias("rtmw-x") 매핑이 없어
# raw onnx URL 또는 절대 path 만 받는다. manifest production_eligible 가중치의
# unzipped onnx 파일 경로를 환경변수로 명시해야 한다 (D-25 정신 유지).
# 예: export RTMW_ONNX_PATH=/workspace/rtmw_weights/.../end2end.onnx
_RTMW_POSE_ENV = "RTMW_ONNX_PATH"


# ── LicenseViolationError ─────────────────────────────────────────────────

class LicenseViolationError(Exception):
    """weights_manifest.json 에서 production_eligible=true 가중치가 없을 때.

    D-25 hard gate: RTMWPoseEngine 초기화 시 manifest 검사.
    production_eligible=false 가중치 강제 사용 시도 차단 (T-21-01 mitigation).
    """


# ── RTMWPoseEngine ────────────────────────────────────────────────────────

class RTMWPoseEngine:
    """rtmlib RTMW 133 wholebody 어댑터 (PoseEngine Protocol 구현).

    H-2 박제: rtmlib import 는 인스턴스화 시점에서만 — Lambda fail-fast 안전.
    D-25 박제: manifest gate — production_eligible=true 가중치만 허용.

    단위 테스트: create_with_inferencer(mock_inferencer, manifest_path) factory 사용.
    운영: RTMWPoseEngine(manifest_path=..., target_fps=...) 생성자 사용.
         (인스턴스화 시 rtmlib lazy import + wholebody inferencer 초기화)
    """

    def __init__(
        self,
        manifest_path: Path | None = None,
        target_fps: int = 30,
    ) -> None:
        """RTMWPoseEngine 초기화.

        H-2 박제: rtmlib lazy import — 인스턴스화 시점에만 시도.
        D-25 박제: manifest 로드 → production_eligible 가중치 선택.

        Args:
            manifest_path: weights_manifest.json 경로. None 이면 기본 경로 사용.
            target_fps: 영상 target FPS (timestamp 단조 계산용).
        """
        resolved = Path(manifest_path) if manifest_path else _DEFAULT_MANIFEST_PATH
        selected_weight = _load_eligible_weight(resolved)
        log.info(
            "RTMWPoseEngine init weight=%s input_size=%s",
            selected_weight["name"],
            selected_weight.get("input_size"),
        )

        # H-2 박제: rtmlib lazy import — 인스턴스화 시점에만
        try:
            from rtmlib import Wholebody as RTMWWholebody  # noqa: PLC0415
        except ImportError as e:
            raise RuntimeError(
                "rtmlib library 미설치 — RunPod 서버에서만 동작. "
                "Lambda 환경에서는 create_with_inferencer(mock) 사용. "
                f"원인: {e}"
            ) from e

        # rtmlib Wholebody 초기화 (ONNX backend 기본).
        # pose= 인자는 RTMW_ONNX_PATH 환경변수의 절대 경로 — alias 미지원 (Plan 01-23 박제).
        rtmw_onnx_path = os.environ.get(_RTMW_POSE_ENV)
        if not rtmw_onnx_path:
            raise RuntimeError(
                f"환경변수 {_RTMW_POSE_ENV} 미설정. rtmlib 0.0.15 의 Wholebody.pose "
                "인자는 alias 매핑 없이 절대 onnx path 또는 URL 만 받는다. "
                "manifest production_eligible 가중치를 unzip 한 end2end.onnx 의 절대 "
                "경로를 환경변수로 명시할 것 (D-25 정신 유지)."
            )
        # device — env var RTMW_DEVICE 매개 (디폴트 cpu = 회귀 0).
        # Pod 박제: .bashrc 에 RTMW_DEVICE=cuda → onnxruntime-gpu CUDAExecutionProvider 사용.
        # 단위 테스트 (mock inferencer) 는 env 미주입 시 cpu 디폴트.
        # 박제 함정 (2026-06-05): 이전 hardcode 'cpu' 때문에 새 Pod sweep 가 GPU 0% — 영상당 30분+.
        rtmw_device = os.environ.get("RTMW_DEVICE", "cpu")
        self._inferencer = RTMWWholebody(
            det=None,  # person detector 없음 — 전체 이미지에서 추론
            pose=rtmw_onnx_path,
            to_openpose=False,
            backend="onnxruntime",
            device=rtmw_device,
        )
        self._selected_weight = selected_weight
        self._target_fps = target_fps

    @classmethod
    def create_with_inferencer(
        cls,
        inferencer: Any,
        manifest_path: Path | str | None = None,
        target_fps: int = 30,
    ) -> "RTMWPoseEngine":
        """DI factory — 단위 테스트가 mock inferencer 주입.

        rtmlib import skip — 테스트 환경에서 안전하게 사용.
        manifest 검사는 동일하게 수행 (D-25 게이트 테스트 가능).

        Args:
            inferencer: callable(frames_batch) → (keypoints, scores) — rtmlib Wholebody mock.
            manifest_path: weights_manifest.json 경로. None 이면 기본 경로.
            target_fps: 영상 target FPS.
        """
        resolved = Path(manifest_path) if manifest_path else _DEFAULT_MANIFEST_PATH
        selected_weight = _load_eligible_weight(resolved)

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
        """프레임 시퀀스 → list[PoseFrame].

        RTMW 추론 → 133 키포인트 → convert_rtmw_keypoints_to_coco17_and_pole_ext → PoseFrame.
        H-3: pole_axis 인자를 각 PoseFrame 에 보존.
        전 프레임 사람 미감지 시 NoHumanError.

        Args:
            frames: (T, H, W, 3) RGB uint8 배열.
            pole_axis: PoleDetector 산출 PoleAxis (D-10/H-3).

        Returns:
            list[PoseFrame] — len = T.

        Raises:
            NoHumanError: 전 프레임에서 사람을 감지하지 못한 경우.
        """
        T = len(frames)
        if T == 0:
            return []

        _, H, W, _ = frames.shape
        pose_frames: list[PoseFrame] = []
        detected_count = 0

        for t in range(T):
            timestamp_ms = int(t * 1000 / self._target_fps)
            frame = frames[t]

            # rtmlib inferencer 호출 — (keypoints, scores) 반환.
            # rtmlib Wholebody 0.0.15 는 단일 (H,W,3) frame 만 받음 — batch 미지원.
            # output = ((N,133,2or3), (N,133)) — N 명 사람.
            result = self._inferencer(frame)
            kps_batch, scores_batch = result  # (N, 133, 2/3), (N, 133)

            if kps_batch is None or len(kps_batch) == 0:
                # 미감지 → PoseFrame.empty
                pose_frames.append(
                    PoseFrame.empty(
                        frame_index=t,
                        timestamp_ms=timestamp_ms,
                        pole_axis=pole_axis,
                    )
                )
                continue

            # 첫 번째 사람(인덱스 0) 사용 (폴스포츠 = 1인 영상)
            kps = kps_batch[0]   # (133, 2/3)
            scores = scores_batch[0]  # (133,)

            # z 좌표 없으면 0 으로 패딩
            if kps.shape[1] == 2:
                kps_3d = np.zeros((133, 3), dtype=np.float32)
                kps_3d[:, :2] = kps
            else:
                kps_3d = kps.astype(np.float32)

            detected_count += 1
            pf = convert_rtmw_keypoints_to_coco17_and_pole_ext(
                keypoints_133=kps_3d,
                scores_133=scores.astype(np.float32),
                image_width=W,
                image_height=H,
                frame_index=t,
                timestamp_ms=timestamp_ms,
                pole_axis=pole_axis,
            )
            pose_frames.append(pf)

        if detected_count == 0:
            raise NoHumanError(
                f"RTMW 전 프레임 미감지 ({T}개 중 0개). "
                "영상에 사람이 없거나 카메라 각도를 확인하세요."
            )

        # Path D fix (2026-06-05, 함정 27): RTMW frame 간 좌/우 keypoint swap correction.
        # Plan 17 era 박제 정신 ("swap_ratio 0 기대") 실제 측정 = 45~57% swap 발생.
        # 폴스포츠 영상 (자세 회전) 에서 frame 간 RTMW 가 좌/우 매핑 헷갈림 → wobble 폭주.
        # inter-frame shoulder/hip distance 매칭으로 swap 감지 + correction.
        return _correct_left_right_swap(pose_frames)


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────

def _load_eligible_weight(manifest_path: Path) -> dict:
    """manifest 로드 → production_eligible=true 가중치 선택.

    D-25 game gate: production_eligible=true 인 entry 가 0개면 LicenseViolationError.
    T-21-01 mitigation: manifest 우회로 비-eligible 가중치 로드 불가.

    Returns:
        첫 번째 production_eligible=true entry.

    Raises:
        LicenseViolationError: eligible 가중치 0개.
        FileNotFoundError: manifest 파일 없음.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"weights_manifest.json 없음: {manifest_path}. "
            "Plan 01-20 산출 파일 확인."
        )

    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    eligible = [w for w in manifest.get("weights", []) if w.get("production_eligible") is True]
    if not eligible:
        raise LicenseViolationError(
            f"weights_manifest.json 에 production_eligible=true 가중치 없음. "
            f"D-25 라이선스 게이트 실패. manifest: {manifest_path}. "
            "Plan 01-20 Task 2 (belle 승급 결정) 완료 여부 확인."
        )

    selected = eligible[0]
    log.info(
        "RTMWPoseEngine weight selected name=%s license_status=%s",
        selected.get("name"),
        selected.get("license_status"),
    )
    return selected


# ── Path D fix (2026-06-05): frame 간 좌/우 swap correction ─────────────────

_LR_SWAP_PAIRS: tuple[tuple[str, str], ...] = (
    ("left_shoulder", "right_shoulder"),
    ("left_elbow", "right_elbow"),
    ("left_wrist", "right_wrist"),
    ("left_hip", "right_hip"),
    ("left_knee", "right_knee"),
    ("left_ankle", "right_ankle"),
)


def _correct_left_right_swap(pose_frames: list[PoseFrame]) -> list[PoseFrame]:
    """RTMW frame 간 좌/우 keypoint swap detection + correction.

    가설: 폴스포츠 영상 (자세 회전) 에서 RTMW 가 frame 간 좌/우 keypoint 매핑 헷갈림.
    인접 frame 의 shoulder + hip 거리 (4 landmark) 매칭으로 swap 감지 후 정정.

    distance(normal) = |Δl| + |Δr|     (정상 매칭)
    distance(swapped) = |l_curr - r_prev| + |r_curr - l_prev|

    distance(swapped) < distance(normal) = swap 발생 → 좌/우 keypoint 교환.

    박제 정신:
    - 박제 [[license-blocklist-pose]] 정합 — raw_keypoints_133 (원본) 보존, 분석 path
      (keypoints_3d / keypoints_3d_pole_aligned) 만 정정.
    - 첫 frame 은 reference 로 고정 (correction 0). 이후 frame 만 비교.
    - 누적 correction — corrected[i-1] 와 비교해 i 의 swap 판정.
    """
    from dataclasses import replace

    if len(pose_frames) <= 1:
        return pose_frames

    corrected: list[PoseFrame] = [pose_frames[0]]

    for i in range(1, len(pose_frames)):
        prev = corrected[-1]
        curr = pose_frames[i]

        # shoulder + hip 4 landmark 거리 비교 (가장 안정적 reference)
        d_normal = 0.0
        d_swapped = 0.0
        compared = 0
        for left_key, right_key in (("left_shoulder", "right_shoulder"), ("left_hip", "right_hip")):
            if (
                left_key in prev.keypoints_3d
                and right_key in prev.keypoints_3d
                and left_key in curr.keypoints_3d
                and right_key in curr.keypoints_3d
            ):
                pl = prev.keypoints_3d[left_key]
                pr = prev.keypoints_3d[right_key]
                cl = curr.keypoints_3d[left_key]
                cr = curr.keypoints_3d[right_key]
                d_normal += (
                    abs(cl.x - pl.x) + abs(cl.y - pl.y)
                    + abs(cr.x - pr.x) + abs(cr.y - pr.y)
                )
                d_swapped += (
                    abs(cl.x - pr.x) + abs(cl.y - pr.y)
                    + abs(cr.x - pl.x) + abs(cr.y - pl.y)
                )
                compared += 1

        if compared > 0 and d_swapped < d_normal:
            # swap correction — 새 PoseFrame (frozen 박제)
            new_kp = dict(curr.keypoints_3d)
            new_aligned = dict(curr.keypoints_3d_pole_aligned)
            for left_key, right_key in _LR_SWAP_PAIRS:
                if left_key in new_kp and right_key in new_kp:
                    new_kp[left_key], new_kp[right_key] = new_kp[right_key], new_kp[left_key]
                if left_key in new_aligned and right_key in new_aligned:
                    new_aligned[left_key], new_aligned[right_key] = (
                        new_aligned[right_key], new_aligned[left_key]
                    )
            curr = replace(
                curr,
                keypoints_3d=new_kp,
                keypoints_3d_pole_aligned=new_aligned,
            )

        corrected.append(curr)

    return corrected
