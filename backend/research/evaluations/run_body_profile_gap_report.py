"""단일 audited orchestrator — belle Pod 의 한 줄 명령 (HIGH-2 v5 박제).

[[user-beginner-stepwise]] 정합: belle console 작업 = 두 줄
  (1) `python -m backend.research.evaluations.run_body_profile_gap_report \\
        --videos ref-foxtop ... --date YYYYMMDD`
  (2) `git add ... && git commit ...`

내부 phase (belle 개입 0):
  [1/4 RTMW extract]    extract_rtmw_body_profile_keypoints
  [2/4 SMPL-X joints]   extract_smplx_joints_from_video (Pod env 만, HIGH-1 v5)
  [3/4 joints→profile]  load_smplx_joints + smplx_joints_to_body_profile
  [4/4 gap report]      compare_body_profile.compute_profile_gap → JSON + MD

각 phase stdout progress 로깅. 실패 시 actionable Korean error.

HIGH-1 v5: joints-based path 박제 (β-only fake 영구 폐기).

LOW-1 v3 박제: 모든 `python -m` 은 repo root.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]


def _check_pod_env() -> int:
    """Pod env 박제 검증. 미설정 시 Korean stderr + exit 2.

    필수: RUNPOD_AUTH_TOKEN, NLF_MODEL_PATH, SMPLX_MODEL_PATH.
    """
    missing: list[str] = []
    for var in ("RUNPOD_AUTH_TOKEN", "NLF_MODEL_PATH", "SMPLX_MODEL_PATH"):
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        msg = (
            "Pod env 미설정 — 다음 환경변수가 필요합니다: "
            + ", ".join(missing)
            + ". belle 의 RunPod pod env 박제 후 재실행하세요."
        )
        print(msg, file=sys.stderr)
        return 2
    return 0


def _run_subprocess(args: list[str], phase_label: str) -> int:
    print(f"{phase_label} {' '.join(args)}")
    try:
        result = subprocess.run(args, cwd=_REPO_ROOT, check=False)
        return result.returncode
    except FileNotFoundError as e:
        print(f"{phase_label} 실패: {e}", file=sys.stderr)
        return 3


def _run_extract_rtmw(videos: list[str], date: str, reports_root: Path) -> int:
    output_dir = reports_root / f"sweep_rtmw_{date}" / "keypoints"
    output_dir.mkdir(parents=True, exist_ok=True)
    args = [
        sys.executable,
        "-m",
        "backend.research.evaluations.extract_rtmw_body_profile_keypoints",
        "--videos",
        *videos,
        "--output-dir",
        str(output_dir),
    ]
    return _run_subprocess(args, "[1/4 RTMW extract]")


def _run_extract_smplx_joints(
    videos: list[str], date: str, reports_root: Path
) -> int:
    output_dir = reports_root / f"smplx_joints_{date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    args = [
        sys.executable,
        "-m",
        "backend.research.evaluations.extract_smplx_joints_from_video",
        "--videos",
        *videos,
        "--output-dir",
        str(output_dir),
    ]
    return _run_subprocess(args, "[2/4 SMPL-X joints extract]")


def _run_joints_to_profile(date: str, reports_root: Path) -> int:
    """in-process 변환 — smplx_joints_to_body_profile 호출."""
    print("[3/4 joints→profile]")
    from backend.research.evaluations.smplx_joints_to_body_profile import (
        load_smplx_joints,
        smplx_joints_to_body_profile,
    )

    joints_dir = reports_root / f"smplx_joints_{date}"
    out_dir = reports_root / f"smplx_profiles_{date}"
    out_dir.mkdir(parents=True, exist_ok=True)

    joints_dict = load_smplx_joints(joints_dir)
    if not joints_dict:
        print(
            f"[3/4 joints→profile] joints dir 비어있음: {joints_dir}",
            file=sys.stderr,
        )
        return 0  # graceful — extract phase 가 graceful exit 했을 가능성

    for video, joints in joints_dict.items():
        profile = smplx_joints_to_body_profile(joints)
        out_path = out_dir / f"{video}.json"
        out_path.write_text(
            json.dumps(
                {
                    "estimated_height_scale": profile.estimated_height_scale,
                    "arm_scale": profile.arm_scale,
                    "leg_scale": profile.leg_scale,
                    "torso_scale": profile.torso_scale,
                    "shoulder_hip_ratio": profile.shoulder_hip_ratio,
                    "confidence": profile.confidence,
                    "warnings": profile.warnings,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    return 0


def _run_compare(date: str, reports_root: Path, videos: list[str]) -> int:
    rtmw_dir = reports_root / f"sweep_rtmw_{date}" / "keypoints"
    smplx_dir = reports_root / f"smplx_joints_{date}"
    output = reports_root / f"body_profile_gap_{date}.json"
    args = [
        sys.executable,
        "-m",
        "backend.research.evaluations.compare_body_profile",
        "--rtmw-keypoints-dir",
        str(rtmw_dir),
        "--smplx-joints-dir",
        str(smplx_dir),
        "--videos",
        *videos,
        "--output",
        str(output),
    ]
    return _run_subprocess(args, "[4/4 gap report]")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Single audited orchestrator for Phase 2 ROADMAP §4 (HIGH-2 v5)."
    )
    parser.add_argument(
        "--videos",
        nargs="+",
        required=True,
        help="비교 영상 motion ID 리스트.",
    )
    parser.add_argument(
        "--date",
        required=True,
        help="실행 날짜 (YYYYMMDD) — 보고서 path 박제.",
    )
    parser.add_argument(
        "--reports-root",
        type=Path,
        default=Path("backend/research/evaluations/reports"),
        help="보고서 root 디렉터리 (default repo root 기준).",
    )
    args = parser.parse_args(argv)

    reports_root = args.reports_root
    if not reports_root.is_absolute():
        reports_root = _REPO_ROOT / reports_root

    # Pod env 검증
    rc = _check_pod_env()
    if rc != 0:
        return rc

    # 4 phase 순차
    for phase_fn, label in (
        (lambda: _run_extract_rtmw(args.videos, args.date, reports_root), "RTMW extract"),
        (lambda: _run_extract_smplx_joints(args.videos, args.date, reports_root), "SMPL-X joints"),
        (lambda: _run_joints_to_profile(args.date, reports_root), "joints→profile"),
        (lambda: _run_compare(args.date, reports_root, args.videos), "gap report"),
    ):
        rc = phase_fn()
        if rc != 0:
            print(
                f"phase '{label}' 실패 (exit {rc}). 위 로그 확인 후 재시도.",
                file=sys.stderr,
            )
            return rc

    print(
        f"[OK] body profile gap report: "
        f"{reports_root / f'body_profile_gap_{args.date}.json'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
