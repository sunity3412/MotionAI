"""RTMW onnxruntime 결정론 모드 — Phase 25 근본원인 #2 (cold/warm 프로세스 간 비결정).

문제: Pod sweep 에서 cold/warm 두 프로세스 실행 간 점수가 2~5점 흔들림
(power-spin 52/54, peter-pan 83/79, elbow-twist 69/66, kip-up 99/100).
Gemini 는 캐시돼 결정적 → 원인은 GPU RTMW 키포인트의 미세 변동이 tol 20°
경계 관절의 angle_vs_reference criterion 활성을 flip 시키는 것.

주 원인 (onnxruntime 1.19.2 CUDA EP 기준 근거):
  · cudnn_conv_algo_search 기본값 = EXHAUSTIVE — 세션 초기화 시
    cudnnFindConvolutionForwardAlgorithmEx 로 conv algo 를 **실측 벤치마크**로
    선택한다. 벤치마크는 GPU 상태/타이밍 의존 → 프로세스(cold/warm)마다 다른
    algo 가 선택될 수 있고, algo 가 다르면 부동소수 연산 순서가 달라져 출력이
    미세하게 달라진다. RTMW/YOLOX 는 conv-heavy 백본이라 이것이 1순위 용의자.
    → "DEFAULT" 로 고정: cuDNN IMPLICIT_PRECOMP_GEMM 단일 algo (forward 경로
    결정적 algo) 를 항상 사용 — 벤치마크 자체가 사라져 run-to-run algo flip 제거.
  · cuBLAS GEMM: split-K reduction 이 workspace 크기에 따라 비결정 경로를 탈 수
    있다 → CUBLAS_WORKSPACE_CONFIG=:4096:8 (CUDA 10.2+ 공식 재현성 설정, PyTorch
    deterministic 모드가 요구하는 것과 동일) 를 세션 생성 전에 주입.
  · CPU fallback 노드의 멀티스레드 reduction 순서 → intra/inter_op 스레드 1 고정.
  · session config "session.use_deterministic_compute"=1 — ORT 가 결정적 커널
    변형을 제공하는 op 에서 그것을 선택하도록 요청 (best-effort, 미지원 op 무시).

한계 정직성 (요구 5): CUDA EP 는 완전한 bitwise 결정론을 **보장하지 않는다**.
위 설정으로 알려진 최대 변동원(EXHAUSTIVE algo 벤치마크, cuBLAS split-K)을
제거하지만, 일부 fused/atomic 기반 커널의 잔여 비결정 가능성은 남는다.
잔여 변동 여부는 pod cold/warm 실측(phase25 *_warm.json 비교)으로 판단한다.

주입 경로: rtmlib 0.0.15 BaseTool.__init__ 은
    ort.InferenceSession(path_or_bytes=onnx_model, providers=[providers])
로 세션을 직접 생성하며 sess_options / provider options 주입구가 **없다**
(rtmlib/tools/base.py L70-81 확인). 따라서 유일한 실경로는 Wholebody 생성
구간에서만 onnxruntime.InferenceSession 을 patch 하는 것 — rtmlib 은
함수 내부에서 `import onnxruntime as ort` 후 속성 조회하므로 module attribute
patch 가 호출 시점에 반영된다. Wholebody 는 det(YOLOX)+pose(RTMW) 세션을
둘 다 이 구간에서 만들므로 한 번의 patch 로 두 세션 모두 커버된다.

게이트: env RTMW_DETERMINISTIC=1 일 때만 활성 (eval 전용). 미설정 시
context manager 는 아무것도 건드리지 않고 onnxruntime import 조차 하지 않는다
— 프로덕션 경로 byte-동일 (요구 2). EXHAUSTIVE 벤치마크 생략으로 활성 시
오히려 세션 초기화가 빨라질 수 있으나, 고정 algo 가 최속이 아닐 수 있어
추론 처리량은 소폭 낮아질 수 있다 — eval 전용이므로 허용.

유닛 테스트: 순수 함수(apply_deterministic_provider_options /
configure_session_options)와 fake ort module 주입으로 GPU/onnxruntime 없이 검증
(backend/tests/test_rtmw_ort_determinism.py).
"""

from __future__ import annotations

import contextlib
import logging
import os
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

log = logging.getLogger(__name__)

# env 게이트 — "1" 만 활성 (eval 전용). run_sweep(phase25) 가 스스로 설정한다.
RTMW_DETERMINISTIC_ENV = "RTMW_DETERMINISTIC"

# cuBLAS split-K reduction 재현성 (CUDA 10.2+ 공식). 세션(=cublas handle) 생성
# 전에 설정돼야 효과 — deterministic_inference_session() 진입 시 setdefault.
_CUBLAS_WORKSPACE_ENV = "CUBLAS_WORKSPACE_CONFIG"
_CUBLAS_WORKSPACE_DETERMINISTIC = ":4096:8"

# onnxruntime 1.19.2 CUDA EP provider options — 결정론 고정.
# cudnn_conv_algo_search=DEFAULT 가 핵심 (모듈 docstring 근거).
# do_copy_in_default_stream=1 은 1.19 기본값이지만 명시 고정 (스트림 분리 race 차단).
# cudnn_conv_use_max_workspace=1 도 1.19 기본값 — algo 선택 입력(workspace)을
# 명시 고정해 버전/env 에 따른 흔들림 방지.
DETERMINISTIC_CUDA_PROVIDER_OPTIONS: dict[str, str] = {
    "cudnn_conv_algo_search": "DEFAULT",
    "do_copy_in_default_stream": "1",
    "cudnn_conv_use_max_workspace": "1",
}

# ORT session config — 결정적 커널 변형 요청 (best-effort).
_DETERMINISTIC_COMPUTE_KEY = "session.use_deterministic_compute"


def deterministic_enabled(env: Mapping[str, str] | None = None) -> bool:
    """env RTMW_DETERMINISTIC == "1" 여부 (기본 os.environ, 테스트 주입 가능)."""
    src: Mapping[str, str] = env if env is not None else os.environ
    return src.get(RTMW_DETERMINISTIC_ENV, "") == "1"


def apply_deterministic_provider_options(providers: Sequence[Any]) -> list[Any]:
    """providers 리스트에서 CUDAExecutionProvider 항목에만 결정론 옵션 주입 (순수 함수).

    rtmlib 이 넘기는 두 형태 모두 처리:
      · "CUDAExecutionProvider" (문자열 — device 기본)
      · ("CUDAExecutionProvider", {"device_id": N}) (tuple — 'cuda:N' 경로)
    기존 옵션(device_id 등)은 보존하되 결정론 키는 우리 값이 우선.
    CPU 등 다른 provider 는 무접촉.
    """
    out: list[Any] = []
    for entry in providers:
        if entry == "CUDAExecutionProvider":
            out.append(("CUDAExecutionProvider", dict(DETERMINISTIC_CUDA_PROVIDER_OPTIONS)))
        elif (
            isinstance(entry, tuple)
            and len(entry) == 2
            and entry[0] == "CUDAExecutionProvider"
        ):
            merged = {**dict(entry[1] or {}), **DETERMINISTIC_CUDA_PROVIDER_OPTIONS}
            out.append(("CUDAExecutionProvider", merged))
        else:
            out.append(entry)
    return out


def configure_session_options(sess_options: Any) -> Any:
    """SessionOptions 에 결정론 설정 적용 (duck-typed — 테스트는 stub 주입).

    · intra/inter_op 스레드 1 — CPU fallback 노드의 멀티스레드 부동소수
      reduction 순서 비결정 제거.
    · session.use_deterministic_compute=1 — 결정적 커널 변형 요청 (best-effort;
      add_session_config_entry 미보유 구현체는 조용히 skip).
    """
    sess_options.intra_op_num_threads = 1
    sess_options.inter_op_num_threads = 1
    add_entry = getattr(sess_options, "add_session_config_entry", None)
    if callable(add_entry):
        add_entry(_DETERMINISTIC_COMPUTE_KEY, "1")
    return sess_options


@contextlib.contextmanager
def deterministic_inference_session(ort_module: Any | None = None) -> Iterator[bool]:
    """RTMW_DETERMINISTIC=1 일 때만 ort.InferenceSession 을 patch 하는 구간 CM.

    yield 값 = 결정론 모드 활성 여부.
    env 미설정: 아무것도 건드리지 않음 — onnxruntime import 조차 없음 (요구 2:
    프로덕션 byte-동일). 활성: 구간 내 생성되는 모든 InferenceSession 에
    결정론 sess_options + CUDA EP provider options 주입, 구간 종료 시 원복
    (예외 시에도 finally 원복 — 구간 밖 다른 onnxruntime 사용자 무영향).

    Args:
        ort_module: 테스트용 fake onnxruntime module 주입. None 이면 lazy import.
    """
    if not deterministic_enabled():
        yield False
        return

    if ort_module is None:
        import onnxruntime as ort_module  # noqa: PLC0415 — env 게이트 뒤 lazy

    # cuBLAS 재현성 env 는 cublas handle 생성(= 아래 구간의 세션 생성) 전에 주입.
    # setdefault — 운영자가 명시적으로 다른 값을 준 경우 존중.
    os.environ.setdefault(_CUBLAS_WORKSPACE_ENV, _CUBLAS_WORKSPACE_DETERMINISTIC)

    original_cls = ort_module.InferenceSession

    def _patched_inference_session(*args: Any, **kwargs: Any) -> Any:
        providers = kwargs.get("providers")
        if providers is not None:
            kwargs["providers"] = apply_deterministic_provider_options(providers)
        sess_options = kwargs.get("sess_options")
        if sess_options is None:
            sess_options = ort_module.SessionOptions()
        kwargs["sess_options"] = configure_session_options(sess_options)
        return original_cls(*args, **kwargs)

    ort_module.InferenceSession = _patched_inference_session
    log.info(
        "RTMW deterministic mode ON — CUDA EP options=%s, threads=1, %s=1, %s=%s",
        DETERMINISTIC_CUDA_PROVIDER_OPTIONS,
        _DETERMINISTIC_COMPUTE_KEY,
        _CUBLAS_WORKSPACE_ENV,
        os.environ.get(_CUBLAS_WORKSPACE_ENV),
    )
    try:
        yield True
    finally:
        ort_module.InferenceSession = original_cls
