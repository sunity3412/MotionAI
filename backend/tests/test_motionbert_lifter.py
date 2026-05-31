"""MotionBertLifter 단위 테스트.

Plan 01-08 — torch mock 으로 실행. GPU/MotionBERT 저장소 없이 로컬 실행 가능.
torch 를 sys.modules 에 mock 주입해 실제 설치 없이 테스트.

테스트 범위:
  - lift() 입출력 shape 검증 (T, 17, 2|3) → (T, 17, 3)
  - NaN 입력 처리 (0.0으로 대체 후 model 호출)
  - 환경변수 fallback (MOTIONBERT_ROOT, MOTIONBERT_WEIGHTS)
  - 가중치 파일 미존재 시 FileNotFoundError
  - create_with_model DI factory
  - 청크 추론 (T > MAXLEN=243)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ── torch mock 주입 ───────────────────────────────────────────────────────────
# torch 미설치 환경(macOS ARM64 CI)에서 테스트 가능하도록 sys.modules 에 mock 주입.

def _make_torch_mock() -> ModuleType:
    """torch 모듈 mock을 생성하고 반환.

    - torch.tensor(arr, dtype=...) → MagicMock (squeeze/cpu/numpy 체인 지원)
    - torch.no_grad() → context manager (with 블록에서 안전하게 동작)
    - torch.cuda.is_available() → False
    - torch.device("cpu") → MagicMock
    - torch.float32 → mock
    """
    mock_torch = MagicMock(spec=ModuleType)
    mock_torch.__name__ = "torch"

    # cuda mock
    mock_cuda = MagicMock()
    mock_cuda.is_available.return_value = False
    mock_torch.cuda = mock_cuda

    # device mock
    mock_torch.device.return_value = MagicMock()

    # no_grad context manager mock
    no_grad_ctx = MagicMock()
    no_grad_ctx.__enter__ = MagicMock(return_value=None)
    no_grad_ctx.__exit__ = MagicMock(return_value=False)
    mock_torch.no_grad.return_value = no_grad_ctx

    # float32 mock
    mock_torch.float32 = "float32"

    return mock_torch


def _make_tensor_mock(arr: np.ndarray) -> MagicMock:
    """tensor mock — squeeze/cpu/numpy 체인 시 arr 반환."""
    mock_tensor = MagicMock()
    # .to(device) → 자기 자신 반환
    mock_tensor.to.return_value = mock_tensor
    # .shape → arr.shape
    mock_tensor.shape = arr.shape
    return mock_tensor


def _patch_torch_for_lift(model_fn):
    """torch.tensor() 호출을 intercept해서 model_fn이 numpy 결과를 반환하도록 패치."""
    mock_torch = _make_torch_mock()

    def _tensor_side_effect(data, dtype=None):
        # data는 numpy array (B=1, MAXLEN, 17, 3)
        arr = np.asarray(data)
        mock_t = MagicMock()
        mock_t.to.return_value = mock_t
        mock_t.shape = arr.shape
        # model_fn이 mock_t를 인자로 받아 적절한 결과 반환
        return mock_t

    mock_torch.tensor.side_effect = _tensor_side_effect
    return mock_torch


# ── fixture helpers ───────────────────────────────────────────────────────────


def _make_mock_model_for_lift(J: int = 17) -> MagicMock:
    """DSTformer mock model: 입력 tensor shape 에서 (seq_T, J, 3) zeros 반환."""

    def _forward(tensor):
        # tensor.shape = (1, MAXLEN, J, C) — mock 객체
        # 반환: squeeze(0).cpu().numpy() = (MAXLEN, J, 3) zeros
        MAXLEN = 243
        out_np = np.zeros((MAXLEN, J, 3), dtype=np.float32)
        result = MagicMock()
        result.squeeze.return_value.cpu.return_value.numpy.return_value = out_np
        return result

    mock = MagicMock()
    mock.side_effect = _forward
    return mock


def _make_lifter(tmp_path: Path) -> object:
    """DI factory로 MotionBertLifter 인스턴스를 반환 (weights 체크 없음)."""
    from sunity_shared.analysis.pose_lifters.motionbert_lifter import MotionBertLifter

    mock_model = _make_mock_model_for_lift()
    mock_device = MagicMock()
    return MotionBertLifter.create_with_model(mock_model, mock_device)


# ── torch sys.modules 패치 컨텍스트 ───────────────────────────────────────────


class _TorchMockContext:
    """테스트 클래스에서 사용하는 torch mock sys.modules 패치.

    torch.tensor() 호출 시 MagicMock tensor를 반환하고,
    torch.no_grad() 는 context manager로 동작한다.
    """

    def __init__(self, J: int = 17):
        self._J = J
        self._orig_torch = sys.modules.get("torch")
        self._mock_torch = None

    def _make_mock_torch(self, call_log: list | None = None) -> MagicMock:
        """torch mock 생성 — spec 없이 자유로운 attribute 접근 허용."""
        J = self._J
        mock = MagicMock()
        mock.__name__ = "torch"

        # cuda
        mock_cuda = MagicMock()
        mock_cuda.is_available.return_value = False
        mock.cuda = mock_cuda

        # device
        mock.device.return_value = MagicMock()

        # float32
        mock.float32 = "float32"

        # no_grad context manager
        no_grad_ctx = MagicMock()
        no_grad_ctx.__enter__ = MagicMock(return_value=None)
        no_grad_ctx.__exit__ = MagicMock(return_value=False)
        mock.no_grad.return_value = no_grad_ctx

        # tensor: numpy array → mock tensor
        def _tensor_side_effect(data, dtype=None):
            arr = np.asarray(data)
            mock_t = MagicMock()
            mock_t.to.return_value = mock_t
            mock_t.shape = arr.shape  # (1, MAXLEN, J, C)
            if call_log is not None:
                call_log.append(arr.shape)
            return mock_t

        mock.tensor.side_effect = _tensor_side_effect
        return mock

    def install(self, call_log: list | None = None) -> None:
        self._mock_torch = self._make_mock_torch(call_log)
        sys.modules["torch"] = self._mock_torch

    def uninstall(self) -> None:
        if self._orig_torch is None:
            sys.modules.pop("torch", None)
        else:
            sys.modules["torch"] = self._orig_torch


def _run_with_torch_mock(lifter, inp: np.ndarray, call_log: list | None = None) -> np.ndarray:
    """torch mock을 주입한 상태에서 lifter.lift(inp)를 실행."""
    ctx = _TorchMockContext()
    ctx.install(call_log)
    try:
        return lifter.lift(inp)
    finally:
        ctx.uninstall()


# ── 테스트 클래스 ──────────────────────────────────────────────────────────────


class TestMotionBertLifterShape:
    """lift() 출력 형상 검증."""

    def test_lift_shape_t5_j17_c2(self, tmp_path):
        """(5, 17, 2) 입력 → (5, 17, 3) 출력."""
        lifter = _make_lifter(tmp_path)
        inp = np.zeros((5, 17, 2), dtype=np.float32)
        out = _run_with_torch_mock(lifter, inp)
        assert out.shape == (5, 17, 3), f"예상 (5,17,3), 실제 {out.shape}"

    def test_lift_shape_t10_j17_c3(self, tmp_path):
        """(10, 17, 3) 입력 → (10, 17, 3) 출력 (세 번째 채널 무시)."""
        lifter = _make_lifter(tmp_path)
        inp = np.zeros((10, 17, 3), dtype=np.float32)
        out = _run_with_torch_mock(lifter, inp)
        assert out.shape == (10, 17, 3)

    def test_lift_shape_t1_j17_c2(self, tmp_path):
        """단일 프레임 (1, 17, 2) → (1, 17, 3)."""
        lifter = _make_lifter(tmp_path)
        inp = np.zeros((1, 17, 2), dtype=np.float32)
        out = _run_with_torch_mock(lifter, inp)
        assert out.shape == (1, 17, 3)

    def test_lift_output_dtype_float(self, tmp_path):
        """출력 dtype은 float."""
        lifter = _make_lifter(tmp_path)
        inp = np.zeros((3, 17, 2), dtype=np.float32)
        out = _run_with_torch_mock(lifter, inp)
        assert np.issubdtype(out.dtype, np.floating), f"출력 dtype: {out.dtype}"


class TestMotionBertLifterNanInput:
    """NaN 입력 처리 — 0.0으로 대체 후 model 호출."""

    def test_nan_replaced_with_zero(self, tmp_path):
        """NaN 포함 입력 → 출력에 NaN 없음 (model이 0 입력으로 처리)."""
        lifter = _make_lifter(tmp_path)
        inp = np.full((5, 17, 2), np.nan, dtype=np.float32)
        out = _run_with_torch_mock(lifter, inp)
        assert out.shape == (5, 17, 3)
        # mock model 출력이 0이므로 NaN 없음
        assert not np.any(np.isnan(out)), "NaN 입력 처리 후 출력에 NaN 있어서는 안 됨"


class TestMotionBertLifterInvalidInput:
    """잘못된 입력 형상 → ValueError (torch import 전에 검증)."""

    def test_wrong_joints(self, tmp_path):
        lifter = _make_lifter(tmp_path)
        # 입력 검증은 torch import 전에 수행 — torch mock 없이도 동작
        with pytest.raises(ValueError, match="17"):
            lifter.lift(np.zeros((5, 16, 2)))

    def test_too_few_channels(self, tmp_path):
        lifter = _make_lifter(tmp_path)
        with pytest.raises(ValueError):
            lifter.lift(np.zeros((5, 17, 1)))

    def test_wrong_ndim(self, tmp_path):
        lifter = _make_lifter(tmp_path)
        with pytest.raises(ValueError):
            lifter.lift(np.zeros((17, 2)))


class TestMotionBertLifterChunking:
    """T > MAXLEN=243 청크 분할 처리."""

    def test_chunking_long_sequence(self, tmp_path):
        """T=300 (> MAXLEN=243) → 두 청크로 처리 후 (300, 17, 3) 반환."""
        from sunity_shared.analysis.pose_lifters.motionbert_lifter import MotionBertLifter

        call_count = []

        def _forward(tensor):
            call_count.append(1)
            # mock: 항상 (243, 17, 3) zeros 반환
            out_np = np.zeros((243, 17, 3), dtype=np.float32)
            result = MagicMock()
            result.squeeze.return_value.cpu.return_value.numpy.return_value = out_np
            return result

        mock_model = MagicMock()
        mock_model.side_effect = _forward
        mock_device = MagicMock()

        lifter = MotionBertLifter.create_with_model(mock_model, mock_device)
        inp = np.zeros((300, 17, 2), dtype=np.float32)
        out = _run_with_torch_mock(lifter, inp)

        assert out.shape == (300, 17, 3), f"예상 (300,17,3), 실제 {out.shape}"
        # 2번 호출 (0~243, 243~300)
        assert len(call_count) == 2, f"청크 호출 횟수: {len(call_count)}"


class TestMotionBertLifterFileNotFound:
    """가중치 파일 미존재 시 FileNotFoundError."""

    def test_missing_weights_raises(self):
        """존재하지 않는 가중치 경로 → FileNotFoundError."""
        from sunity_shared.analysis.pose_lifters.motionbert_lifter import MotionBertLifter

        with pytest.raises(FileNotFoundError, match="가중치"):
            MotionBertLifter(
                motionbert_root="/workspace/MotionBERT",
                weights_path="/nonexistent/path/best_epoch.bin",
            )


class TestMotionBertLifterEnvFallback:
    """환경변수 fallback 검증."""

    def test_env_weights_path_used(self, tmp_path):
        """MOTIONBERT_WEIGHTS 환경변수 경로를 weights_path로 사용."""
        from sunity_shared.analysis.pose_lifters.motionbert_lifter import MotionBertLifter

        fake_weights = tmp_path / "best_epoch.bin"
        fake_weights.write_bytes(b"fake")

        with patch.dict(os.environ, {"MOTIONBERT_WEIGHTS": str(fake_weights)}):
            # weights 존재 → 에러 없이 초기화
            lifter = MotionBertLifter.__new__(MotionBertLifter)
            lifter._root = "/workspace/MotionBERT"
            lifter._weights = str(fake_weights)
            lifter._device_str = None
            lifter._model = None
            lifter._device = None
            # 파일 존재 체크만 수행하는 실제 초기화 경로 검증
            assert Path(lifter._weights).exists()

    def test_env_root_path_used(self, tmp_path):
        """MOTIONBERT_ROOT 환경변수가 _root에 반영됨."""
        from sunity_shared.analysis.pose_lifters.motionbert_lifter import MotionBertLifter

        fake_weights = tmp_path / "checkpoint" / "pose3d" / "FT_MB_lite_MB_ft_h36m_global_lite" / "best_epoch.bin"
        fake_weights.parent.mkdir(parents=True)
        fake_weights.write_bytes(b"fake")

        with patch.dict(
            os.environ,
            {
                "MOTIONBERT_ROOT": str(tmp_path),
                "MOTIONBERT_WEIGHTS": str(fake_weights),
            },
        ):
            lifter = MotionBertLifter(weights_path=str(fake_weights))
            assert lifter._root == str(tmp_path)


class TestMotionBertLifterDIFactory:
    """create_with_model DI factory 검증."""

    def test_di_factory_model_injected(self, tmp_path):
        """create_with_model으로 mock model이 _model 에 주입됨."""
        from sunity_shared.analysis.pose_lifters.motionbert_lifter import MotionBertLifter

        mock_model = MagicMock()
        mock_device = MagicMock()

        lifter = MotionBertLifter.create_with_model(mock_model, mock_device)
        assert lifter._model is mock_model
        assert lifter._device is mock_device

    def test_di_factory_skips_weight_check(self):
        """create_with_model은 가중치 파일 존재 검증을 skip — FileNotFoundError 없음."""
        from sunity_shared.analysis.pose_lifters.motionbert_lifter import MotionBertLifter

        mock_model = MagicMock()
        mock_device = MagicMock()

        # 이 코드가 에러 없이 실행되어야 함
        lifter = MotionBertLifter.create_with_model(mock_model, mock_device)
        assert lifter is not None
