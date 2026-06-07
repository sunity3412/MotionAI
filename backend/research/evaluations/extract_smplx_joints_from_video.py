"""Pod-only — NLF → SMPL-X β fit → SMPL-X model → joints `(T, NJ, 3)` JSON 산출.

HIGH-1 v5 박제 (REVIEWS.md plan_revision v4):
  joints 산출이 closure 조건 — β-only pure-math 변환 fake 폐기. 본 스크립트는
  Pod 환경에서만 의미 — NLF + SMPL-X model weights 필요.

D-02-04 박제: NLF/SMPL-X import 본 파일에서만 — sunity_shared 무관.
PS:License 1.0 비상업 (SMPL-X model weights).

CI 환경 graceful exit:
  SMPLX_MODEL_PATH 미설정 / weights 부재 → exit 0 + 한국어 안내 메시지.

CLI: `python -m backend.research.evaluations.extract_smplx_joints_from_video \\
        --videos ref-foxtop ref-invert --output-dir reports/smplx_joints_<date>/`
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any


def _load_nlf_engine(model_path: str):
    """lazy import NLF — Pod 환경에서만 호출."""
    # pragma: no cover — Pod 환경 의존
    import torch  # noqa: F401

    return torch.jit.load(model_path, map_location="cuda")


def _load_smplx_model(model_path: str):
    """lazy import smplx model — Pod 환경에서만 호출."""
    # pragma: no cover — Pod 환경 의존
    import smplx  # noqa: F401

    return smplx.create(model_path)


def _extract_nlf_keypoints_per_frame(video_frames, nlf_engine):  # pragma: no cover
    """NLF inference per-frame → keypoints `(T, J, 3)`."""
    raise NotImplementedError("Pod-only path — belle 가 NLF inference 박제")


def _fit_smplx_beta(nlf_keypoints_3d, smplx_model):  # pragma: no cover
    """NLF 3D keypoints → SMPL-X β `(10,)` fit. Pod-only."""
    raise NotImplementedError("Pod-only path — belle 가 SMPL-X β fitting 박제")


def _render_smplx_joints(beta, smplx_model):  # pragma: no cover
    """SMPL-X β + mean pose → joints `(T, NJ, 3)`. Pod-only."""
    raise NotImplementedError("Pod-only path — belle 가 SMPL-X rendering 박제")


def extract_smplx_joints(
    motion_id: str,
    output_dir: Path,
    nlf_engine,
    smplx_model,
):  # pragma: no cover — Pod-only
    """1 영상 → NLF → β → joints JSON 산출 → `output_dir/{motion_id}.json`."""
    # Pod 환경에서 belle 가 박제. CI 에선 main() 의 graceful exit path 가 차단.
    raise NotImplementedError(
        f"Pod-only flow — motion={motion_id}. belle 가 NLF→SMPL-X β→joints 박제."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pod-only NLF→SMPL-X joints extractor (HIGH-1 v5)."
    )
    parser.add_argument(
        "--videos",
        nargs="+",
        required=True,
        help="추출할 motion ID 리스트.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="joints JSON 출력 디렉터리.",
    )
    parser.add_argument(
        "--video-source",
        default="s3",
        choices=("s3", "local"),
        help="영상 소스 — Pod default S3.",
    )
    parser.add_argument(
        "--nlf-model-path",
        default=os.environ.get("NLF_MODEL_PATH", ""),
        help="NLF TorchScript 경로 (env NLF_MODEL_PATH).",
    )
    parser.add_argument(
        "--smplx-model-path",
        default=os.environ.get("SMPLX_MODEL_PATH", ""),
        help="SMPL-X model weights 경로 (env SMPLX_MODEL_PATH).",
    )
    args = parser.parse_args(argv)

    # CI graceful exit — SMPL-X weights 미설정.
    if not args.smplx_model_path or not Path(args.smplx_model_path).exists():
        print(
            "SMPL-X weights 미설정 — CI 환경에선 정상. Pod 환경에선 "
            "SMPLX_MODEL_PATH 박제 필요.",
            file=sys.stderr,
        )
        return 0

    # NLF 도 동일 graceful
    if not args.nlf_model_path or not Path(args.nlf_model_path).exists():
        print(
            "NLF_MODEL_PATH 미설정 — Pod 환경에선 박제 필요.",
            file=sys.stderr,
        )
        return 0

    # Pod-only path (CI 도달 X)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    nlf = _load_nlf_engine(args.nlf_model_path)
    smplx = _load_smplx_model(args.smplx_model_path)
    for motion_id in args.videos:
        try:
            extract_smplx_joints(motion_id, args.output_dir, nlf, smplx)
        except NotImplementedError as e:
            print(f"motion={motion_id} 박제 미완 — {e}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
