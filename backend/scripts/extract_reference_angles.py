"""정은지 5영상 → NLF 파이프라인 → reference angles JSON (GPU 필요).

mode1 비교가 시뮬레이션 점수가 아닌 실 점수가 나오려면 reference 모션 각각에
대해 angles 시퀀스가 Firestore reference/{motionId}.angles 에 저장돼야 한다
(backend/functions/pipeline/app.py:95 가 그 필드를 읽음).

이 스크립트는 RunPod GPU 에서 1회 실행:
  1. S3 sunity-motion-pilot-videos/reference/{motionId}.mp4 5개 다운로드
  2. 어제 검증한 동일 파이프라인 (FfmpegFrameExtractor → NlfPoseEstimator →
     compute_joint_angles → temporal_fill) 적용
  3. 결과를 단일 JSON 파일에 저장 — belle 이 로컬로 가져와 시드 스크립트에 투입

사용 (RunPod 등 CUDA 환경):
  cd backend
  pip install boto3                                # (Pod 에 없을 때만)
  export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_DEFAULT_REGION=ap-northeast-2
  python scripts/extract_reference_angles.py --out reference-angles.json

CPU 환경에서는 NLF 가 NaN 만 출력하므로 의미 없다(어제 검증 메모 참조).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))

from sunity_shared.analysis import skeleton  # noqa: E402
from sunity_shared.analysis.features import (  # noqa: E402
    compute_joint_angles,
    joint_uncertainty,
)
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402
from sunity_shared.analysis.pose_estimator import NlfPoseEstimator  # noqa: E402
from sunity_shared.analysis.temporal import occluded_mask, temporal_fill  # noqa: E402

# Firestore reference 와 1:1 — 명칭 정정(2026-05-22) 이후 5개 motionId.
# seed-reference-motions.mjs MOTIONS 와 항상 동기 유지.
MOTION_IDS = [
    "ref-sideway-spin",
    "ref-climb",
    "ref-invert",
    "ref-foxtop",
    "ref-foxtop-split",
]

S3_BUCKET = "sunity-motion-pilot-videos"
S3_PREFIX = "reference"


def _download_video(s3_client, motion_id: str, target: Path) -> None:
    key = f"{S3_PREFIX}/{motion_id}.mp4"
    print(f"  S3 download s3://{S3_BUCKET}/{key} → {target.name}")
    s3_client.download_file(S3_BUCKET, key, str(target))


def _extract_one(
    motion_id: str,
    video_path: Path,
    extractor: FfmpegFrameExtractor,
    estimator: NlfPoseEstimator,
) -> dict:
    t0 = time.time()
    frames = extractor.extract(str(video_path))
    keypoints = estimator.estimate(frames)
    raw_angles = compute_joint_angles(keypoints)
    unc = joint_uncertainty(keypoints)
    mask = occluded_mask(raw_angles, unc)
    filled = temporal_fill(raw_angles, unc)
    T = int(filled.shape[0])

    # 폐색 보간 프레임 수를 관절별로 기록 (디버깅·검증용).
    occluded = {
        skeleton.JOINT_KEYS[j]: int(mask[:, j].sum()) for j in range(skeleton.NUM_JOINTS)
    }

    # 1MB Firestore 한도 안전 — float32 로 잘라 정밀도 살리고 용량 줄임.
    # 각도 단위(도)는 소수 둘째 자리면 충분.
    angles_rounded = np.round(filled.astype(np.float64), 2)
    if not np.isfinite(angles_rounded).all():
        # 불가피한 NaN 이 남아 있으면 0 으로 치환 — 백엔드가 numpy asarray 후 NaN
        # 만나면 점수 계산이 깨짐. temporal_fill 이 이미 보간했으므로 보통은 0개.
        nan_count = int((~np.isfinite(angles_rounded)).sum())
        print(f"  ⚠ NaN/inf {nan_count} 잔여 → 0.0 치환 (보간 한계)")
        angles_rounded = np.nan_to_num(angles_rounded, nan=0.0, posinf=0.0, neginf=0.0)

    print(
        f"  frames={T}  추출 {time.time() - t0:.1f}s  "
        f"폐색 보간: {sum(occluded.values())} (관절별 합)"
    )
    return {
        "numFrames": T,
        "occludedFrames": occluded,
        "angles": angles_rounded.tolist(),  # (T, 8) → JSON 직렬화
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("reference-angles.json"),
        help="결과 JSON 출력 경로",
    )
    parser.add_argument(
        "--motions",
        nargs="+",
        default=MOTION_IDS,
        help="추출할 motionId 부분집합 (디버그용). 기본은 5개 전부.",
    )
    args = parser.parse_args()

    # boto3 는 Lambda 런타임엔 항상 있지만 RunPod 베이스 이미지엔 없을 수 있다.
    try:
        import boto3
    except ImportError:
        print("boto3 없음. pip install boto3 후 재시도.", file=sys.stderr)
        sys.exit(1)

    region = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION")
    if not region:
        print("AWS_DEFAULT_REGION 환경변수 필요 (예: ap-northeast-2).", file=sys.stderr)
        sys.exit(1)

    s3 = boto3.client("s3", region_name=region)
    extractor = FfmpegFrameExtractor()
    estimator = NlfPoseEstimator()
    print(f"NLF device = {estimator._device}")
    if str(estimator._device) == "cpu":
        print(
            "⚠ NLF 가 CPU 로 잡힘 — 결과가 NaN 으로 발산해 시드에 쓸 수 없음.\n"
            "  CUDA 환경에서 다시 실행 필요.",
            file=sys.stderr,
        )
        sys.exit(2)

    result_motions: dict[str, dict] = {}
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for motion_id in args.motions:
            print(f"\n[{motion_id}]")
            video_path = td_path / f"{motion_id}.mp4"
            _download_video(s3, motion_id, video_path)
            result_motions[motion_id] = _extract_one(
                motion_id, video_path, extractor, estimator
            )

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "jointKeys": list(skeleton.JOINT_KEYS),
        "numJoints": skeleton.NUM_JOINTS,
        "motions": result_motions,
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False))
    size_kb = args.out.stat().st_size / 1024
    print(
        f"\n완료. 결과 → {args.out} ({size_kb:.1f} KB) — "
        f"motions={len(result_motions)} jointKeys={skeleton.JOINT_KEYS}"
    )
    print(
        "belle: 이 파일을 로컬로 받아 app/scripts/seed-reference-motions.mjs 옆에 두고\n"
        "       cd app && npm run seed:reference -- --angles ../backend/scripts/reference-angles.json"
    )


if __name__ == "__main__":
    main()
