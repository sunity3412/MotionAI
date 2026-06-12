"""정은지 reference 영상 → RTMW 파이프라인 → reference angles JSON (GPU 필요).

mode1 비교가 시뮬레이션 점수가 아닌 실 점수가 나오려면 reference 모션 각각에
대해 angles 시퀀스가 Firestore reference/{motionId}.angles 에 저장돼야 한다
(backend/functions/pipeline/app.py:95 가 그 필드를 읽음).

Phase 17 Plan 07: RTMW engine swap (운영 pipeline 정합 — pipeline 의 private
NLF-호환 어댑터 estimate_with_profile 와 1:1 흐름). NLF path 는 R&D 격리
(memory ml-pose-3d-pivot). 3차 R-B4 정합 — pipeline private adapter import X.
script context 는 pipeline interface compat 불필요 → RTMWPoseEngine 을
직접 박는다 (Lambda module side-effect = FRAME_EXTRACTOR, boto3 client,
RunPod env 등 끌고 오는 거 차단).

이 스크립트는 RunPod GPU 에서 1회 실행:
  1. S3 sunity-motion-pilot-videos/reference/{motionId}.mp4 다운로드
  2. 운영 파이프라인 정합 (FfmpegFrameExtractor → RTMWPoseEngine +
     PoleAxis(vertical_fallback) + measure_body_profile + to_coco17_array →
     compute_joint_angles → temporal_fill) 적용
  3. 결과를 단일 JSON 파일에 저장 — belle 이 로컬로 가져와 시드 스크립트에 투입

사용 (RunPod 등 CUDA 환경):
  cd backend
  pip install boto3                                # (Pod 에 없을 때만)
  export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_DEFAULT_REGION=ap-northeast-2
  python scripts/extract_reference_angles.py --out reference-angles.json

CPU 환경에서는 RTMW inferencer 가 매우 느리므로 GPU 권장.
"""

from __future__ import annotations

import argparse
import dataclasses
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
from sunity_shared.analysis.body_normalization_measurer import (  # noqa: E402
    measure_body_profile,
)
from sunity_shared.analysis.features import (  # noqa: E402
    compute_joint_angles,
    joint_uncertainty,
)
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402
# Phase 17 Plan 07: RTMW engine swap (운영 pipeline 정합 — pipeline 의 private
# NLF-호환 어댑터 estimate_with_profile 와 1:1 흐름). NLF path 는 R&D 격리
# (memory ml-pose-3d-pivot). 3차 R-B4 정합 — pipeline private adapter import X.
from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import (  # noqa: E402
    RTMWPoseEngine,
)
from sunity_shared.analysis.pose_frame import PoleAxis, to_coco17_array  # noqa: E402
from sunity_shared.analysis.temporal import occluded_mask, temporal_fill  # noqa: E402

# Firestore reference 와 1:1 — 명칭 정정(2026-05-22) 이후 정은지 5개 motionId.
# Phase 17 (UAT 2026-06-12) 신규 6 motion 박제 박힘 — reactivate_new6_motions.py
# 가 별도 entry. 본 list 는 정은지 reference set (기본).
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

# RTMW vertical pole_axis fallback (pipeline 의 private NLF-호환 어댑터 박은
# default 와 동일). reference 영상은 학원 환경 — 폴 거의 항상 수직.
# PoleDetector 호출 비용 회피.
_VERTICAL_POLE_AXIS = PoleAxis(
    axis_vector=(0.0, 1.0, 0.0),
    confidence_level="low",
    source="vertical_fallback",
    frame_index=None,
)


def _download_video(s3_client, motion_id: str, target: Path) -> None:
    key = f"{S3_PREFIX}/{motion_id}.mp4"
    print(f"  S3 download s3://{S3_BUCKET}/{key} → {target.name}")
    s3_client.download_file(S3_BUCKET, key, str(target))


def _rtmw_estimate_to_coco17(
    engine: RTMWPoseEngine, frames: np.ndarray
) -> np.ndarray:
    """RTMW pose estimation → COCO-17 (T,17,4) — pipeline 운영 adapter 정합.

    pipeline 의 private NLF-호환 어댑터 estimate_with_profile
    (functions/pipeline/app.py:797) 의 흐름을 1:1 박제: estimate →
    measure_body_profile → body_shape 주입 → to_coco17_array.
    compute_joint_angles 는 4번째 채널 (uncertainty_proxy) 무시하고 x/y/z 만
    사용 — body_shape 주입 효과는 angles 출력에 직접 박지 않지만 운영 path 와
    동일 인스턴스 상태 유지 = 회귀 0.
    """
    pose_frames = engine.estimate(frames, _VERTICAL_POLE_AXIS)
    profile = measure_body_profile(pose_frames)
    pose_frames_with_profile = [
        dataclasses.replace(pf, body_shape=profile) for pf in pose_frames
    ]
    return to_coco17_array(pose_frames_with_profile)


def _extract_one(
    motion_id: str,
    video_path: Path,
    extractor: FfmpegFrameExtractor,
    engine: RTMWPoseEngine,
) -> dict:
    t0 = time.time()
    frames = extractor.extract(str(video_path))
    keypoints = _rtmw_estimate_to_coco17(engine, frames)
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
    # Phase 17 Plan 07: RTMWPoseEngine direct (pipeline private NLF-호환
    # 어댑터 박제 X). rtmlib inferencer 가 CUDA 사용 가능하면 GPU, 아니면 CPU
    # fallback (NaN 발산은 NLF 만의 문제 — RTMW 는 CPU 에서도 동작하나 매우 느림).
    engine = RTMWPoseEngine()

    result_motions: dict[str, dict] = {}
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for motion_id in args.motions:
            print(f"\n[{motion_id}]")
            video_path = td_path / f"{motion_id}.mp4"
            _download_video(s3, motion_id, video_path)
            result_motions[motion_id] = _extract_one(
                motion_id, video_path, extractor, engine
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
