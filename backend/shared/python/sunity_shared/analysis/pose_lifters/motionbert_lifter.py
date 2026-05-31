"""MotionBERT 3D Lifter 어댑터.

Plan 01-08: spike_motionbert.py 의 _load_motionbert + _run_motionbert_inference 를
production grade 로 승격. torch lazy import 유지 — 모듈 load 시 torch 불필요.

라이선스:
  MotionBERT: Apache 2.0 (https://github.com/Walter0807/MotionBERT/blob/main/LICENSE)
  상업적 사용, 수정, 배포 모두 허용. 저작권 고지 필요.

DSTformer 파라미터 박제 (MB_ft_h36m_global_lite.yaml — Lite config):
  dim_in=3, dim_out=3, dim_feat=256, dim_rep=512, depth=5, num_heads=8
  mlp_ratio=4, num_joints=17, maxlen=243, att_fuse=True
  norm_layer: 명시 금지 — DSTformer 기본값(nn.LayerNorm)을 사용해야 함.
  (None 명시 시 Block.__init__ norm1_s=None(dim) TypeError — Plan 07 commit c164700 박제)

환경변수:
  MOTIONBERT_ROOT    — MotionBERT 저장소 클론 경로 (기본: /workspace/MotionBERT)
  MOTIONBERT_WEIGHTS — 사전학습 가중치 경로 (기본: {root}/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin)
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)

# MotionBERT lite config 하이퍼파라미터 상수
_DIM_IN = 3
_DIM_OUT = 3
_DIM_FEAT = 256
_DIM_REP = 512
_DEPTH = 5
_NUM_HEADS = 8
_MLP_RATIO = 4
_NUM_JOINTS = 17
_MAXLEN = 243  # DSTformer 최대 시퀀스 길이

# 기본 환경변수 이름
_ENV_MOTIONBERT_ROOT = "MOTIONBERT_ROOT"
_ENV_MOTIONBERT_WEIGHTS = "MOTIONBERT_WEIGHTS"

# Pod 기본 경로
_DEFAULT_ROOT = "/workspace/MotionBERT"
_DEFAULT_WEIGHTS_RELPATH = (
    "checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin"
)


class MotionBertLifter:
    """MediaPipe 2D keypoints → MotionBERT 3D lift 어댑터.

    (T, 17, 2|3) H3.6M 17-joint 2D 좌표 → (T, 17, 3) 3D 복원.

    torch + DSTformer는 lazy import — 모듈 load 시점엔 torch 없이 OK.
    인스턴스화 시점에 motionbert_root/weights_path 유효성 검증만 수행.
    실제 모델 load는 첫 lift() 호출 시점으로 지연 (lazy load).

    단위 테스트: torch mock 주입 시 _model, _device 직접 설정 가능.
    """

    def __init__(
        self,
        motionbert_root: str | None = None,
        weights_path: str | None = None,
        device: str | None = None,
    ) -> None:
        """MotionBertLifter 초기화.

        Args:
            motionbert_root: MotionBERT 저장소 루트 경로.
                             None이면 MOTIONBERT_ROOT 환경변수 → 기본값 순서로 fallback.
            weights_path: 사전학습 가중치 (best_epoch.bin) 경로.
                          None이면 MOTIONBERT_WEIGHTS 환경변수 → motionbert_root 기반 기본값 순서.
            device: 'cuda' | 'cpu' | None (None이면 CUDA 가용 시 자동 선택).
        """
        # 경로 결정 (env fallback)
        self._root = (
            motionbert_root
            or os.environ.get(_ENV_MOTIONBERT_ROOT)
            or _DEFAULT_ROOT
        )
        self._weights = (
            weights_path
            or os.environ.get(_ENV_MOTIONBERT_WEIGHTS)
            or str(Path(self._root) / _DEFAULT_WEIGHTS_RELPATH)
        )
        self._device_str = device

        # 가중치 파일 존재 검증 (인스턴스화 시점 — 조기 실패)
        if not Path(self._weights).exists():
            raise FileNotFoundError(
                f"MotionBERT 가중치 파일 없음: {self._weights!r}. "
                f"Pod에서 scp로 배치하거나 {_ENV_MOTIONBERT_WEIGHTS} 환경변수를 설정하세요. "
                "setup.sh 섹션 '3. MotionBERT 체크포인트' 참조."
            )

        # 모델은 첫 lift() 호출 시 lazy load
        self._model = None
        self._device = None

    @classmethod
    def create_with_model(
        cls,
        model: object,
        device: object,
    ) -> "MotionBertLifter":
        """DI factory — 단위 테스트가 mock model/device 주입.

        weights 파일 존재 검증 skip. 테스트 환경에서 안전하게 사용.
        """
        instance = cls.__new__(cls)
        instance._root = _DEFAULT_ROOT
        instance._weights = "/mock/best_epoch.bin"
        instance._device_str = None
        instance._model = model
        instance._device = device
        return instance

    def _ensure_loaded(self) -> None:
        """모델이 아직 load되지 않았으면 lazy load 수행."""
        if self._model is not None:
            return

        # sys.path에 motionbert_root 추가 (MotionBERT 저장소 구조: lib/model/DSTformer.py)
        if self._root not in sys.path:
            sys.path.insert(0, self._root)

        import torch  # noqa: PLC0415

        # device 결정
        if self._device_str is not None:
            device = torch.device(self._device_str)
        else:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        log.info("MotionBertLifter device: %s", device)

        # DSTformer import (MotionBERT 저장소 구조)
        try:
            from lib.model.DSTformer import DSTformer  # type: ignore[import]  # noqa: PLC0415
        except ImportError as e:
            raise RuntimeError(
                f"MotionBERT DSTformer import 실패. "
                f"motionbert_root 경로를 확인하세요: {self._root!r}. "
                f"저장소 구조: lib/model/DSTformer.py 필요. 원인: {e}"
            ) from e

        # DSTformer 초기화 (Lite config — MB_ft_h36m_global_lite.yaml 기준).
        # norm_layer 는 명시하지 않는다 — DSTformer 기본값 nn.LayerNorm 을 사용해야 한다.
        # (None 명시 시 Block.__init__ norm1_s=None(dim) TypeError — Plan 07 commit c164700 박제)
        # att_fuse=True 는 lite config 기본값.
        model = DSTformer(
            dim_in=_DIM_IN,
            dim_out=_DIM_OUT,
            dim_feat=_DIM_FEAT,
            dim_rep=_DIM_REP,
            depth=_DEPTH,
            num_heads=_NUM_HEADS,
            mlp_ratio=_MLP_RATIO,
            maxlen=_MAXLEN,
            num_joints=_NUM_JOINTS,
            att_fuse=True,
        )

        # checkpoint 로드 — 구조 3가지 처리
        checkpoint = torch.load(self._weights, map_location=device)
        if isinstance(checkpoint, dict):
            if "model_pos" in checkpoint:
                state_dict = checkpoint["model_pos"]
            elif "model" in checkpoint:
                state_dict = checkpoint["model"]
            else:
                state_dict = checkpoint
        else:
            state_dict = checkpoint

        model.load_state_dict(state_dict, strict=False)
        model.to(device)
        model.eval()

        self._model = model
        self._device = device
        log.info("MotionBERT loaded from %s (device=%s)", self._weights, device)

    def lift(self, landmarks_2d: np.ndarray) -> np.ndarray:
        """H3.6M 17-joint 2D → 3D 복원.

        sliding window (최대 243 프레임) 기반 청크 추론.
        T < 243: 끝 프레임 복제 패딩 후 추론 → 패딩 제거.
        T > 243: 청크 단위 처리.

        Args:
            landmarks_2d: (T, 17, 2|3) — H3.6M 17-joint 2D 좌표.
                          세 번째 채널(confidence)이 있어도 xy 채널만 사용.
                          NaN은 0.0으로 대체 (미감지 프레임).

        Returns:
            (T, 17, 3) — 3D 복원 좌표 (MotionBERT 출력 스케일).
        """
        # 입력 형상 검증 — torch import 전에 수행 (미설치 환경에서도 안전)
        arr = np.asarray(landmarks_2d, dtype=np.float32)
        if arr.ndim != 3 or arr.shape[1] != _NUM_JOINTS or arr.shape[2] < 2:
            raise ValueError(
                f"landmarks_2d 형상은 (T, 17, 2|3) 이어야 합니다. "
                f"받은 형상: {arr.shape}"
            )

        # 모델 로드 (DI factory로 주입된 경우 skip)
        self._ensure_loaded()

        # torch는 모델/텐서 연산 직전에만 import — lazy import 유지
        import torch  # noqa: PLC0415

        T = arr.shape[0]

        # (T, 17, 2|3) → (T, 17, 3) — 채널 2개면 z=0 패딩
        if arr.shape[2] == 2:
            z_pad = np.zeros((T, _NUM_JOINTS, 1), dtype=np.float32)
            h36m_input = np.concatenate([arr, z_pad], axis=2)
        else:
            h36m_input = arr[:, :, :3].copy()

        # NaN → 0.0 (미감지 프레임 처리)
        h36m_input = np.nan_to_num(h36m_input, nan=0.0)

        results_3d: list[np.ndarray] = []

        for start in range(0, T, _MAXLEN):
            end = min(start + _MAXLEN, T)
            chunk = h36m_input[start:end]  # (chunk_T, 17, 3)
            chunk_T = chunk.shape[0]

            # 패딩 (끝 프레임 복제) → (MAXLEN, 17, 3)
            if chunk_T < _MAXLEN:
                pad_len = _MAXLEN - chunk_T
                pad = np.tile(chunk[-1:], (pad_len, 1, 1))
                chunk_padded = np.concatenate([chunk, pad], axis=0)
            else:
                chunk_padded = chunk

            # (1, MAXLEN, 17, 3) tensor
            tensor = torch.tensor(
                chunk_padded[np.newaxis, ...], dtype=torch.float32
            ).to(self._device)

            with torch.no_grad():
                # DSTformer forward: (B, T, J, C) → (B, T, J, 3)
                out = self._model(tensor)  # (1, MAXLEN, 17, 3)

            out_np = out.squeeze(0).cpu().numpy()  # (MAXLEN, 17, 3)
            results_3d.append(out_np[:chunk_T])    # 패딩 제거

        return np.concatenate(results_3d, axis=0)  # (T, 17, 3)
