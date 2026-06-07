"""Pod-only — RTMW 133 wholebody → PoseFrame JSON dump CLI.

HIGH-4 v3 박제 (REVIEWS.md):
  belle Pod 에서 5영상 → RTMW keypoint dump → `<output_dir>/<motion_id>.json`.
  v1.5 sweep — ROADMAP success criterion 1 real RTMW coverage 의 입력.

D-02-04 박제: RTMW import (rtmlib) 는 본 파일 함수 body 안 lazy.

LOW-1 v3 박제: 실행 경로 = repo root.
  python -m backend.research.evaluations.extract_rtmw_body_profile_keypoints \\
    --videos ref-foxtop ref-invert --output-dir reports/sweep_rtmw_<date>/keypoints/
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import tempfile
from pathlib import Path


def _load_video_frames(motion_id: str, video_source: str = "s3"):
    """영상 frame 추출 (Pod-only). S3 default."""
    # pragma: no cover — Pod 환경 의존
    import boto3
    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor

    s3 = boto3.client("s3")
    bucket = os.environ.get("VIDEO_BUCKET", "sunity-motion-pilot-videos")
    key = f"reference/{motion_id}.mp4"
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name
    s3.download_file(bucket, key, tmp_path)
    extractor = FfmpegFrameExtractor()
    return extractor.extract(tmp_path)


def _detect_pole_axis():
    """Phase 2 R&D — vertical fallback PoleAxis."""
    from sunity_shared.analysis.pose_frame import PoleAxis

    return PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )


def extract(motion_id: str, output_dir: Path) -> Path:
    """1 영상 → RTMW keypoints → list[PoseFrame] → JSON dump.

    Pod-only. CI 환경에선 RTMW model weights / rtmlib 없으면 graceful raise.
    """
    # lazy import — RTMW Pod-only
    from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine

    frames = _load_video_frames(motion_id)
    engine = RTMWPoseEngine()
    pole = _detect_pole_axis()
    pose_frames = engine.estimate(frames, pole)

    out_path = output_dir / f"{motion_id}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # dataclasses.asdict + axis_vector tuple → list
    dumped = []
    for pf in pose_frames:
        d = dataclasses.asdict(pf)
        if d.get("pole_axis") is not None:
            d["pole_axis"]["axis_vector"] = list(d["pole_axis"]["axis_vector"])
        dumped.append(d)

    out_path.write_text(json.dumps(dumped, indent=2), encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pod-only RTMW keypoint dump CLI (HIGH-4 v3)."
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
        help="keypoint JSON 출력 디렉터리.",
    )
    parser.add_argument(
        "--video-source",
        default="s3",
        choices=("s3", "local"),
        help="영상 소스 — Pod default S3.",
    )
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for motion_id in args.videos:
        try:
            extract(motion_id, args.output_dir)
        except Exception as e:  # noqa: BLE001 — Pod 환경 의존 graceful
            print(f"motion={motion_id} 추출 실패: {e}", file=sys.stderr)
            # CI 환경: RTMW model weights / rtmlib 부재 시 exit 0 graceful
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
