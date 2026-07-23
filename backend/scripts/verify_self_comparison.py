"""정은지 영상 self-comparison — mode1 비교 알고리즘 정밀도 검증.

목적:
  결과 화면의 71점/145°→168° 는 모두 시뮬레이션(app/src/lib/simulatedResult.ts).
  진짜 NLF 파이프라인이 작동하는지 — DTW 정렬·KISMAM 점수·관절 각도 가이드가
  정밀하게 산출되는지 검증하려면 사용자 영상 → NLF 추출 → reference 와 비교가
  필요한데 백엔드 GPU 인프라(#7-follow 유닛 4)는 미완. 그 사이 검증 방법 =
  정은지 영상 자체를 "사용자 영상"으로 가정해 self-comparison.

  같은 영상이므로 알고리즘이 정상이면 ~100점이 나와야 한다.
  - --quick   : reference-angles.json 만으로 self-DTW (NLF 재실행 안 함, 100점 자명)
                  DTW+KISMAM 파이프라인 자체의 sanity. 로컬 CPU 에서 즉시.
  - 기본(풀)  : S3 영상 → NLF 재추출 → reference 와 비교. NLF stochasticity 가
                  거의 0 이면 95+ 점. GPU 필요(RunPod).

사용:
  cd backend
  # 로컬 quick (RunPod 불필요):
  python scripts/verify_self_comparison.py \
    --reference scripts/reference-angles.json \
    --out scripts/self-comparison-quick.json \
    --quick

  # 풀 NLF (RunPod GPU):
  pip install boto3  # Pod 에 없으면
  export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
  export AWS_DEFAULT_REGION=ap-northeast-2
  export CUDA_VISIBLE_DEVICES=0
  python scripts/verify_self_comparison.py \
    --reference scripts/reference-angles.json \
    --out scripts/self-comparison.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))

from sunity_shared.analysis import kismam, skeleton  # noqa: E402
from sunity_shared.analysis.features import (  # noqa: E402
    compute_joint_angles,
    feature_vector,
    joint_uncertainty,
)
from sunity_shared.analysis.motiondtw import motion_dtw, per_joint_deviation  # noqa: E402

MOTION_IDS = [
    "ref-sideway-spin",
    "ref-climb",
    "ref-invert",
    "ref-foxtop",
    "ref-foxtop-split",
]

S3_BUCKET = "sunity-motion-pilot-videos"
S3_PREFIX = "reference"


def _safe(v: float | None) -> float | None:
    """JSON 직렬화 안전: NaN/inf → None. 외 round(_,2)."""
    if v is None:
        return None
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return round(float(v), 2)


def _extract_angles_from_s3(s3_client, motion_id: str, extractor, estimator) -> np.ndarray:
    """S3 영상 → NLF → (T,J) 각도. extract_reference_angles.py 와 동일 흐름."""
    from sunity_shared.analysis.temporal import temporal_fill

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
        key = f"{S3_PREFIX}/{motion_id}.mp4"
        print(f"  S3 download s3://{S3_BUCKET}/{key}")
        s3_client.download_file(S3_BUCKET, key, tmp.name)
        frames = extractor.extract(tmp.name)
    keypoints = estimator.estimate(frames)
    raw_angles = compute_joint_angles(keypoints)
    unc = joint_uncertainty(keypoints)
    filled = temporal_fill(raw_angles, unc)
    if not np.isfinite(filled).all():
        filled = np.nan_to_num(filled, nan=0.0, posinf=0.0, neginf=0.0)
    return filled


def _compare(angles_user: np.ndarray, angles_ref: np.ndarray) -> dict:
    """user vs reference angles → mode1 점수 + 관절 디테일 (백엔드 pipeline 과 동일 로직)."""
    match = motion_dtw(feature_vector(angles_user), feature_vector(angles_ref))
    user_seg = angles_user[match.start : match.end]
    deviation = per_joint_deviation(match.path, user_seg, angles_ref)

    # 평균 각도(관절키→deg). KISMAM 의 current/target 가이드 채움.
    user_mean = {
        k: float(np.nanmean(user_seg[:, j]))
        for j, k in enumerate(skeleton.JOINT_KEYS)
    }
    ref_mean = {
        k: float(np.nanmean(angles_ref[:, j]))
        for j, k in enumerate(skeleton.JOINT_KEYS)
    }

    assessments = kismam.assess(
        deviation,
        user_angles=user_mean,
        reference_angles=ref_mean,
    )
    return {
        "similarity": kismam.overall_score(assessments),
        "partScores": kismam.part_scores(assessments),
        "dtwDistance": _safe(match.distance),
        "dtwPathLength": len(match.path),
        "userSegment": [int(match.start), int(match.end)],
        "joints": [
            {
                "key": a.key,
                "labelKo": a.label_ko,
                "score": a.score,
                "deviationDeg": _safe(a.deviation_deg),
                "currentAngle": _safe(a.current_angle),
                "targetAngle": _safe(a.target_angle),
                "signedDeltaDeg": _safe(a.signed_delta_deg),
                "direction": a.direction,
                "part": a.part,
            }
            for a in assessments
        ],
        "topIssues": [
            {
                "key": a.key,
                "labelKo": a.label_ko,
                "score": a.score,
                "deviationDeg": _safe(a.deviation_deg),
            }
            for a in kismam.top_issues(assessments, n=3)
        ],
    }


def _load_reference_angles(path: Path) -> dict[str, np.ndarray]:
    payload = json.loads(path.read_text())
    out: dict[str, np.ndarray] = {}
    for mid, m in payload["motions"].items():
        out[mid] = np.asarray(m["angles"], dtype=float)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reference",
        type=Path,
        required=True,
        help="extract_reference_angles.py 출력 JSON 경로",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("self-comparison.json"),
        help="결과 출력 경로",
    )
    parser.add_argument(
        "--motions",
        nargs="+",
        default=MOTION_IDS,
        help="검증할 motionId 부분집합 (기본 5개 전부)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="NLF 재추출 없이 angles=reference (알고리즘 sanity, 로컬 OK)",
    )
    parser.add_argument(
        "--reference-version",
        type=str,
        default=None,
        help=(
            "candidate reference 버전을 flip 없이 소비 (33-17 concern 3, R-3). "
            "SUNITY_SHADOW_REFERENCE_VERSION 을 세팅해 firestore_admin.get_reference_motion "
            "이 reference/{id}/versions/{v} 를 read-only overlay 로 읽게 한다 — reference-as-"
            "student 경로가 production top-level 을 건드리지 않고 candidate 를 검증."
        ),
    )
    args = parser.parse_args()

    # 33-17: shadow reference 버전 주입 (get_reference_motion 을 타는 하위 호출용).
    if args.reference_version:
        os.environ["SUNITY_SHADOW_REFERENCE_VERSION"] = args.reference_version
        print(
            f"shadow reference version = {args.reference_version} "
            "(read-only overlay, production top-level 무변형)"
        )

    refs = _load_reference_angles(args.reference)
    missing = [m for m in args.motions if m not in refs]
    if missing:
        print(f"reference JSON 에 motionId 없음: {missing}", file=sys.stderr)
        sys.exit(1)

    s3 = extractor = estimator = None
    if args.quick:
        print("=== QUICK 모드 (NLF 재추출 없음, angles_user = angles_ref) ===")
        print("    100 점에 가까우면 DTW+KISMAM 자체는 정상.\n")
    else:
        try:
            import boto3
        except ImportError:
            print("boto3 없음. pip install boto3 후 재시도.", file=sys.stderr)
            sys.exit(1)
        region = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION")
        if not region:
            print("AWS_DEFAULT_REGION 환경변수 필요 (예: ap-northeast-2).", file=sys.stderr)
            sys.exit(1)

        from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
        from sunity_shared.analysis.pose_estimator import NlfPoseEstimator

        s3 = boto3.client("s3", region_name=region)
        extractor = FfmpegFrameExtractor()
        estimator = NlfPoseEstimator()
        print(f"NLF device = {estimator._device}")
        if str(estimator._device) == "cpu":
            print(
                "⚠ NLF CPU — 결과 NaN. CUDA 환경에서 다시 실행하거나 --quick.",
                file=sys.stderr,
            )
            sys.exit(2)

    results: dict[str, dict] = {}
    for motion_id in args.motions:
        print(f"\n[{motion_id}]")
        ref_angles = refs[motion_id]

        if args.quick:
            user_angles = ref_angles.copy()
        else:
            t0 = time.time()
            user_angles = _extract_angles_from_s3(s3, motion_id, extractor, estimator)
            print(
                f"  NLF 재추출 frames={user_angles.shape[0]} {time.time() - t0:.1f}s"
            )

        t0 = time.time()
        cmp = _compare(user_angles, ref_angles)
        cmp["userFrames"] = int(user_angles.shape[0])
        cmp["referenceFrames"] = int(ref_angles.shape[0])
        dtw_d = cmp["dtwDistance"]
        dtw_s = f"{dtw_d:.4f}" if dtw_d is not None else "n/a"
        print(
            f"  비교 {time.time() - t0:.2f}s · similarity={cmp['similarity']}점 "
            f"· parts={cmp['partScores']} · DTW={dtw_s}"
        )
        for it in cmp["topIssues"]:
            print(f"    top: {it['labelKo']:8s} dev={it['deviationDeg']:>6.2f}°  score={it['score']}")
        results[motion_id] = cmp

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "mode": "quick" if args.quick else "full-nlf",
        "jointKeys": list(skeleton.JOINT_KEYS),
        "referenceFile": str(args.reference),
        "results": results,
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n완료 → {args.out} ({args.out.stat().st_size / 1024:.1f} KB)")

    print("\n=== 요약 ===")
    sims = [r["similarity"] for r in results.values()]
    avg = sum(sims) / len(sims) if sims else 0
    print(f"평균 similarity : {avg:.1f} 점")
    print(f"최저 similarity : {min(sims) if sims else 0} 점")
    print(f"최고 similarity : {max(sims) if sims else 0} 점")
    for mid, r in results.items():
        print(f"  {mid:25s}  {r['similarity']:3d}점  parts={r['partScores']}")


if __name__ == "__main__":
    main()
