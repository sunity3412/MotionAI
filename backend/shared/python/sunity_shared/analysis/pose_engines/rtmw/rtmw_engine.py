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
import time
from pathlib import Path
from typing import Any

import numpy as np

from ...interfaces import NoHumanError
from ...pose_frame import PoseFrame, PoleAxis
from ...adapters.rtmw_133_to_coco17 import convert_rtmw_keypoints_to_coco17_and_pole_ext
from .ort_determinism import deterministic_inference_session

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

# 박제 함정 (2026-06-06): OpenMMLab CDN 글로벌 만료 (download.openmmlab.com → expired.hichina.com).
# rtmlib 의 det 디폴트 자동 다운로드가 fail. det=None 박제해도 rtmlib 가 default detector 강제 로드.
# Fix = YOLOX onnx 절대 path 를 env var 로 박제 — BaseTool 이 os.path.exists() 검사로
# 다운로드 skip. mirror = HuggingFace hr16/yolox-onnx/yolox_m.onnx (Apache-2.0, 97MB).
# 미박제 시 None 폴백 → 다음 Pod 재생성 시 동일 함정 재현.
_YOLOX_DET_ENV = "YOLOX_ONNX_PATH"

# 32-15 (D-22): PR 인버전 2-pass 조건부 보정 게이트 — 코드 기본 off.
# "1"/"true" 일 때만 estimate 가 1차 추론 후 인버전 검출→조건부 2차 추론을 수행.
# 제한 통합 게이트(32-15 Task 2) 통과 후에만 Pod start_server.sh 에서 on.
_PR_INVERSION_ENV = "PR_INVERSION_ENABLED"


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
        # 박제 함정 (2026-06-06): det=None 박제해도 rtmlib 가 default detector 강제 자동
        # 다운로드 (OpenMMLab CDN 만료로 fail). YOLOX_ONNX_PATH 절대 path 박제 → skip.
        yolox_onnx_path = os.environ.get(_YOLOX_DET_ENV)
        # Phase 25 근본원인 #2 (cold/warm 비결정): env RTMW_DETERMINISTIC=1 (eval
        # 전용) 이면 onnxruntime CUDA EP 의 비결정 요소(EXHAUSTIVE conv algo
        # 벤치마크 등)를 세션 생성 시점에 고정한다. rtmlib 0.0.15 BaseTool 은
        # sess_options/provider options 주입구가 없어 이 구간에서만
        # ort.InferenceSession 을 patch 한다 — Wholebody 가 det(YOLOX)+pose(RTMW)
        # 세션을 둘 다 이 구간에서 생성하므로 두 세션 모두 커버. env 미설정 =
        # patch 0 (프로덕션 byte-동일). 한계: CUDA EP 완전 bitwise 결정론은
        # 미보장 — ort_determinism.py docstring 참조 (잔여 변동은 pod 실측 판단).
        with deterministic_inference_session() as det_active:
            self._inferencer = RTMWWholebody(
                det=yolox_onnx_path,  # None 이면 rtmlib default (OpenMMLab CDN 의존 — 만료됨)
                det_input_size=(640, 640),  # yolox_m 표준 input
                pose=rtmw_onnx_path,
                to_openpose=False,
                backend="onnxruntime",
                device=rtmw_device,
            )
        if det_active:
            log.info("RTMWPoseEngine deterministic mode ON (RTMW_DETERMINISTIC=1, eval 전용)")
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

        32-15 (D-22): 1차 추론 완료 후 PR 인버전 2-pass 조건부 훅.
        PR_INVERSION_ENABLED env (코드 기본 off) + 지속 인버전 검출 시에만
        워프 2차 추론으로 좌표 교체 — 미검출/off 경로는 1차 결과 그대로
        (바이트 동일 — 비인버전 무회귀의 구조 보장).

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
        raw_first = self._infer_raw(frames)
        pose_frames, detected_count = self._build_pose_frames(raw_first, W, H, pole_axis)

        if detected_count == 0:
            raise NoHumanError(
                f"RTMW 전 프레임 미감지 ({T}개 중 0개). "
                "영상에 사람이 없거나 카메라 각도를 확인하세요."
            )

        # 32-15 PR 인버전 2-pass 조건부 훅 — 1차 추론 "후" 삽입 (순환 의존 0).
        return self._maybe_second_pass_inversion(
            frames, raw_first, pose_frames, pole_axis, W, H
        )

    def _infer_raw(
        self, frames: np.ndarray
    ) -> list[tuple[np.ndarray, np.ndarray] | None]:
        """프레임별 RTMW 원시 추론 — (kps_133 (133,3) float32, scores_133) 또는 미감지 None.

        기존 estimate 루프에서 추론부만 분리 (32-15) — 호출 순서·인원 선택·
        z 패딩 전부 동일 (byte-equivalent). 2-pass 가 워프 프레임에 재사용한다.
        """
        out: list[tuple[np.ndarray, np.ndarray] | None] = []
        for t in range(len(frames)):
            # rtmlib inferencer 호출 — (keypoints, scores) 반환.
            # rtmlib Wholebody 0.0.15 는 단일 (H,W,3) frame 만 받음 — batch 미지원.
            # output = ((N,133,2or3), (N,133)) — N 명 사람.
            result = self._inferencer(frames[t])
            kps_batch, scores_batch = result  # (N, 133, 2/3), (N, 133)

            if kps_batch is None or len(kps_batch) == 0:
                out.append(None)  # 미감지 → PoseFrame.empty (build 단계)
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
            out.append((kps_3d, scores))
        return out

    def _build_pose_frames(
        self,
        raw: list[tuple[np.ndarray, np.ndarray] | None],
        image_width: int,
        image_height: int,
        pole_axis: PoleAxis,
    ) -> tuple[list[PoseFrame], int]:
        """원시 추론 결과 → list[PoseFrame] + 감지 프레임 수 (기존 변환부 분리, 32-15)."""
        pose_frames: list[PoseFrame] = []
        detected_count = 0
        for t, entry in enumerate(raw):
            timestamp_ms = int(t * 1000 / self._target_fps)
            if entry is None:
                pose_frames.append(
                    PoseFrame.empty(
                        frame_index=t,
                        timestamp_ms=timestamp_ms,
                        pole_axis=pole_axis,
                    )
                )
                continue
            kps_3d, scores = entry
            detected_count += 1
            pf = convert_rtmw_keypoints_to_coco17_and_pole_ext(
                keypoints_133=kps_3d,
                scores_133=scores.astype(np.float32),
                image_width=image_width,
                image_height=image_height,
                frame_index=t,
                timestamp_ms=timestamp_ms,
                pole_axis=pole_axis,
            )
            pose_frames.append(pf)
        return pose_frames, detected_count

    def _maybe_second_pass_inversion(
        self,
        frames: np.ndarray,
        raw_first: list[tuple[np.ndarray, np.ndarray] | None],
        pose_frames_first: list[PoseFrame],
        pole_axis: PoleAxis,
        image_width: int,
        image_height: int,
    ) -> list[PoseFrame]:
        """PR 인버전 2-pass 조건부 훅 (32-15, D-22 — spike 006 −58% 근거).

        구조 (리뷰 blocker 6 해소 — 순환 의존 0, 좌표계 불변):
          검출 입력 = 1차 추론 결과 → 참일 때만 1차 kpts 평활 중심 워프 →
          워프 프레임 2차 추론 → 좌표 H⁻¹ 역변환(원본 프레임 공간 복원) 교체.
          신뢰도는 2차 것. 프레임 단위 fail-safe(비유한/범위 이탈/2차 미감지 →
          1차 유지). 거짓/off/실패 경로 전부 1차 결과 그대로 (바이트 동일).

        게이트: PR_INVERSION_ENABLED env — 코드 기본 off (제한 통합 게이트 통과
        후에만 Pod env 로 on. 게이트 실패 시 off 유지 = phase 안전 마감 경로).
        """
        if os.environ.get(_PR_INVERSION_ENV, "").strip().lower() not in ("1", "true"):
            return pose_frames_first

        # 순수 유틸 lazy import (어댑터 관례) — off 경로 import 비용 0.
        from ...inversion_warp import (  # noqa: PLC0415
            build_homography,
            detect_inversion,
            smooth_centers,
            unwarp_frame_keypoints,
            unwarp_points,
            warp_frames,
        )

        T = len(raw_first)
        kxy = np.full((T, 133, 2), np.nan)
        ks = np.zeros((T, 133))
        for t, entry in enumerate(raw_first):
            if entry is not None:
                kxy[t] = entry[0][:, :2]
                ks[t] = entry[1]

        det = detect_inversion(kxy, ks)
        log.info(
            "pr_inversion detect is_inverted=%s ratio=%.3f run=%d valid=%d/%d",
            det.is_inverted, det.inverted_ratio, det.longest_run_frames,
            det.valid_frames, det.total_frames,
        )
        if not det.is_inverted:
            return pose_frames_first  # 미검출 = 기존 경로 그대로 (안전 기본 분기)

        t0 = time.perf_counter()
        centers = smooth_centers(kxy, ks)
        if centers is None:
            log.warning("pr_inversion centers unavailable — 1차 결과 유지")
            return pose_frames_first

        homographies = [
            build_homography(centers[t], image_width, image_height) for t in range(T)
        ]
        try:
            warped = warp_frames(np.asarray(frames), homographies)
        except Exception:  # noqa: BLE001 - cv2 부재/워프 실패 → 1차 유지 (graceful)
            log.exception("pr_inversion warp 실패 — 1차 결과 유지")
            return pose_frames_first

        raw_second = self._infer_raw(warped)

        merged = list(raw_first)
        replaced = 0
        for t in range(T):
            # 1차 미감지 프레임은 교체 대상 아님 — 검출·중심의 근거가 없던 프레임.
            if raw_first[t] is None or raw_second[t] is None:
                continue
            kps2, scores2 = raw_second[t]
            # 채점층(COCO body 17) 기준 유효성 판정 — 비유한/범위 대탈출 → 1차 유지.
            body_back, ok = unwarp_frame_keypoints(
                homographies[t], kps2[:17, :2], image_width, image_height
            )
            if not ok:
                continue
            # 나머지 116(발·얼굴·손) 도 원본 공간 복원 — raw 보존층 좌표계 일치.
            rest_back = unwarp_points(homographies[t], kps2[17:, :2])
            if not np.all(np.isfinite(rest_back)):
                continue  # 전량 유한일 때만 교체 (공간 혼합 금지 — 보수 폴백)
            kps_new = kps2.copy()
            kps_new[:17, :2] = body_back
            kps_new[17:, :2] = rest_back
            merged[t] = (kps_new, scores2)  # 신뢰도 = 2차 것 (플랜)
            replaced += 1

        second_pass_ms = int((time.perf_counter() - t0) * 1000)
        log.info(
            "pr_inversion applied=true replaced=%d/%d second_pass_ms=%d",
            replaced, T, second_pass_ms,
        )
        if replaced == 0:
            return pose_frames_first

        pose_frames_second, _ = self._build_pose_frames(
            merged, image_width, image_height, pole_axis
        )
        return pose_frames_second


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
