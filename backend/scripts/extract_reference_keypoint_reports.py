"""Phase 12 hotfix (2026-06-11) — 정은지 reference referenceKeypointReport 산출.

belle UAT 1차 결과 5번 (정은지 측 KeypointOverlay 안 그려짐) fix.
33-04 (C+M3 substrate): 기본 motion 11종 + 기본 fps 9.0 (candidate 재추출본 정합).
백필 본류는 backfill_reference_downstream.py 가 live pose 로 keypointReport/
referenceKeypointReport 를 candidate 버전에 직접 MERGE 한다 — 본 스크립트는 standalone
재산출/디버그 경로로 9fps 라벨을 유지한다.

Pod GPU 전용 (RTMW 의존). S3 → frame extract → RTMW pose → build_keypoint_report
→ JSON. 로컬에서 seed-reference-motions.mjs --keypoint-reports 로 Firestore merge.

Usage (Pod):
  cd /workspace/SunityMotion/backend
  source pod.env
  export PYTHONPATH=$PWD:$PWD/shared/python
  python scripts/extract_reference_keypoint_reports.py \
      --out /workspace/reference-keypoint-reports.json

Output JSON format (seed-reference-motions.mjs §loadKeypointReportsPayload 정합):
  {
    "motions": {
      "<motion_id>": {
        "version", "joints", "frames", "fps",
        "data", "confidence", "reliability",
        "axisData", "axisMask", "warnings"
      }, ...
    }
  }
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import boto3
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "shared" / "python"))

from sunity_shared.analysis.assemble import build_keypoint_report  # noqa: E402
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402
from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import (  # noqa: E402
    RTMWPoseEngine,
)
from sunity_shared.analysis.pose_frame import PoleAxis  # noqa: E402


# Firestore reference doc id 와 동기 유지. 33-04 (C+M3 substrate) — 11종 전체 기본값.
# 원본 5(Plan 06-03) + 후속 6. keypointReport 는 candidate 9fps 로 산출한다.
MOTION_IDS = [
    # 원본 5
    "ref-sideway-spin",
    "ref-climb",
    "ref-invert",
    "ref-foxtop",
    "ref-foxtop-split",
    # 후속 6
    "ref-combo",
    "ref-elbow-twist-sister",
    "ref-kip-up",
    "ref-pdshape",
    "ref-peter-pan",
    "ref-power-spin",
]

S3_BUCKET = "sunity-motion-pilot-videos"
S3_PREFIX = "reference"


def _camel_case_report(report) -> dict:
    """KeypointReport dataclass → seed JSON 형식 (camelCase axisData / axisMask)."""
    return {
        "version": report.version,
        "joints": list(report.joints),
        "frames": int(report.frames),
        "fps": float(report.fps),
        "data": list(report.data),
        "confidence": list(report.confidence),
        "reliability": list(report.reliability),
        "axisData": list(report.axis_data),
        "axisMask": list(report.axis_mask),
        "warnings": list(report.warnings),
    }


_DEFAULT_POLE = PoleAxis(
    axis_vector=(0.0, 1.0, 0.0),
    confidence_level="low",
    source="vertical_fallback",
)


def _process_motion(
    motion_id: str,
    s3: "boto3.client",  # type: ignore[name-defined]
    extractor: FfmpegFrameExtractor,
    engine: RTMWPoseEngine,
    target_fps: float,
    s3_prefix: str,
) -> dict:
    """1 motion → KeypointReport dict (camelCase)."""
    key = f"{s3_prefix}/{motion_id}.mp4"
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        local_path = Path(tmp.name)
    try:
        print(f"  [{motion_id}] S3 download s3://{S3_BUCKET}/{key}", flush=True)
        s3.download_file(S3_BUCKET, key, str(local_path))

        print(f"  [{motion_id}] frame extract ({target_fps:g} fps)", flush=True)
        frames = extractor.extract(str(local_path))

        print(
            f"  [{motion_id}] RTMW pose estimate ({frames.shape[0]} frame)",
            flush=True,
        )
        pose_frames = engine.estimate(frames, _DEFAULT_POLE)

        print(f"  [{motion_id}] build_keypoint_report", flush=True)
        report = build_keypoint_report(pose_frames, fps=target_fps)
        if report is None:
            raise RuntimeError(f"build_keypoint_report 반환 None — {motion_id}")

        return _camel_case_report(report)
    finally:
        try:
            local_path.unlink()
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/workspace/reference-keypoint-reports.json"),
        help="Output JSON path",
    )
    parser.add_argument(
        "--motions",
        nargs="+",
        default=MOTION_IDS,
        help="Override motion id list (default = MOTION_IDS).",
    )
    parser.add_argument(
        "--target-fps",
        type=float,
        default=9.0,
        help=(
            "Target sampling fps. 33-04 (C+M3 substrate) — default 9.0 으로 변경 "
            "(candidate 9fps 재추출본 정합). 구 18.0 은 학생 경로(9fps)와 기질 비대칭을 "
            "만들던 값 — ref-student-substrate-gap M1 해소. keypointReport.fps 라벨 = 9.0."
        ),
    )
    parser.add_argument(
        "--s3-prefix",
        type=str,
        default=S3_PREFIX,
        help=f"S3 prefix (default '{S3_PREFIX}'). fixtures/ 같은 다른 prefix 사용 시 명시.",
    )
    args = parser.parse_args()

    s3 = boto3.client("s3")
    extractor = FfmpegFrameExtractor(target_fps=args.target_fps)
    print("RTMW 엔진 init (가중치 로드 ~30초)...", flush=True)
    engine = RTMWPoseEngine()
    print("RTMW init 완료", flush=True)

    payload: dict = {"motions": {}}
    t_start = time.time()
    for motion_id in args.motions:
        t0 = time.time()
        try:
            payload["motions"][motion_id] = _process_motion(
                motion_id, s3, extractor, engine, args.target_fps, args.s3_prefix
            )
            print(f"  [{motion_id}] OK ({time.time() - t0:.1f}s)")
        except Exception as exc:  # noqa: BLE001
            print(f"  [{motion_id}] FAIL — {exc}", file=sys.stderr)
            # 일부 실패해도 다른 motion 결과는 박제 (R2 partial backfill 정신).
            continue

    print(
        f"\n총 {len(payload['motions'])}/{len(args.motions)} motion 박제 "
        f"({time.time() - t_start:.1f}s)"
    )

    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"  → {args.out}")
    return 0 if payload["motions"] else 1


if __name__ == "__main__":
    sys.exit(main())
