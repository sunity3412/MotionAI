"""Phase 2 R&D — two-profile gap math + report (RTMW-native after 2026-06-08 scope correction).

2026-06-08 belle scope correction (supersedes v5 §4 + Task 5b):
  RTMW pivot ([[rtmw-free-stack-pivot]]) 가 NLF/SMPL-X 의존을 영구 제거했으므로,
  v5 §4 의 "NLF→SMPL-X β BodyNormalizationProfile 갭" 비교는 폐기. SMPL-X 는
  paid commercial license (PS:License 1.0) 로 사내 평가에서도 last-resort 만.

  본 모듈은 다음 둘만 책임:
    1. load_rtmw_profiles(path, videos) — RTMW keypoint dump → {video: Profile}
    2. compute_profile_gap(profiles_a, profiles_b) — 두 profile dict 의 gap 계산

  재사용 시나리오 (Phase 2 이후):
    - student RTMW Profile vs reference (정은지) RTMW Profile 갭 보고서
    - sweep v1.5 (Phase 1 ROADMAP §1) 5영상 RTMW 측정 자체검증 (load_rtmw_profiles)

CLI: `python -m backend.research.evaluations.compare_body_profile \\
        --profiles-a-dir <RTMW dump dir A> --profiles-b-dir <RTMW dump dir B> \\
        --videos ref-foxtop ref-invert ... --output <json path>`

HIGH-3 v3 박제 유지: graceful-empty — 비존재/빈 dir → {}.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile


# ── helper: PoseFrame factory for RTMW keypoint dumps ────────────────────


def _load_rtmw_pose_frames_from_dump(dump_path: Path) -> list:
    """Pod 산출 RTMW keypoint dump (list[dataclasses.asdict(PoseFrame)]) → list[PoseFrame].

    extract_rtmw_body_profile_keypoints.py 가 산출한 JSON 형식 정합.
    """
    from sunity_shared.analysis.pose_frame import (
        Keypoint3D,
        Keypoint3DAligned,
        PoleAxis,
        PoseFrame,
    )

    raw_frames = json.loads(dump_path.read_text(encoding="utf-8"))
    frames: list[PoseFrame] = []
    for r in raw_frames:
        kp3d = {}
        for name, kp in r.get("keypoints_3d", {}).items():
            conf = float(kp["confidence"])
            kp3d[name] = Keypoint3D(
                x=float(kp["x"]),
                y=float(kp["y"]),
                z=float(kp["z"]),
                confidence=conf,
                uncertainty_proxy=float(kp.get("uncertainty_proxy", 1.0 - conf)),
            )
        aligned = {
            name: Keypoint3DAligned(x=float(kp["x"]), y=float(kp["y"]), z=float(kp["z"]))
            for name, kp in r.get("keypoints_3d_pole_aligned", {}).items()
        }
        pa = None
        if r.get("pole_axis") is not None:
            ax = r["pole_axis"]["axis_vector"]
            pa = PoleAxis(
                axis_vector=(float(ax[0]), float(ax[1]), float(ax[2])),
                confidence_level=r["pole_axis"]["confidence_level"],
                source=r["pole_axis"]["source"],
                frame_index=r["pole_axis"].get("frame_index"),
            )
        frames.append(
            PoseFrame(
                frame_index=int(r["frame_index"]),
                timestamp_ms=int(r["timestamp_ms"]),
                raw_landmarks_33={},
                keypoints_3d=kp3d,
                keypoints_3d_pole_aligned=aligned,
                keypoints_2d=None,
                pole_extension_landmarks=None,
                pole_axis=pa,
                reliability=r.get("reliability", "low"),
                body_shape=None,
            )
        )
    return frames


def load_rtmw_profiles(path: Path, videos: list[str]) -> dict:
    """RTMW keypoint dump dir → {video: BodyNormalizationProfile}.

    HIGH-3 v3 graceful: 비존재 / 빈 dir → {}.
    """
    from sunity_shared.analysis.body_normalization_measurer import measure_body_profile

    if not path.exists() or not path.is_dir():
        return {}
    result: dict = {}
    for video in videos:
        dump_path = path / f"{video}.json"
        if not dump_path.exists():
            continue
        try:
            frames = _load_rtmw_pose_frames_from_dump(dump_path)
            result[video] = measure_body_profile(frames)
        except Exception:  # noqa: BLE001 — R&D throwaway, skip on error
            continue
    return result


# ── gap 계산 ────────────────────────────────────────────────────────────


_NUMERIC_SCALE_FIELDS = (
    "estimated_height_scale",
    "arm_scale",
    "leg_scale",
    "torso_scale",
    "shoulder_hip_ratio",
)

_GAP_TOLERANCE = 0.05  # 5% 이내 — RTMW pivot 후에도 동일 휴리스틱


def compute_profile_gap(
    profiles_a: dict, profiles_b: dict
) -> dict:
    """per-video 5 numeric scale 필드 abs diff + aggregate mean diff + verdict.

    2026-06-08 scope correction: 입력은 임의의 두 profile dict (RTMW vs RTMW
    가 active path). v5 의 RTMW vs SMPL-X 비교는 폐기.

    Returns:
      {
        "per_video": {video: {field: abs_diff}},
        "aggregate": {field: mean_abs_diff},
        "verdict": "within_5pct_tolerance" | "gap_too_wide",
      }
    """
    common = sorted(set(profiles_a.keys()) & set(profiles_b.keys()))
    per_video: dict = {}
    field_sums: dict = {f: [] for f in _NUMERIC_SCALE_FIELDS}

    for video in common:
        a = profiles_a[video]
        b = profiles_b[video]
        diffs = {}
        for f in _NUMERIC_SCALE_FIELDS:
            diff = abs(getattr(a, f) - getattr(b, f))
            diffs[f] = diff
            field_sums[f].append(diff)
        per_video[video] = diffs

    aggregate = {
        f: (sum(vals) / len(vals)) if vals else float("nan")
        for f, vals in field_sums.items()
    }

    all_within = (
        all(d <= _GAP_TOLERANCE for d in aggregate.values())
        if aggregate
        else False
    )
    verdict = "within_5pct_tolerance" if all_within else "gap_too_wide"

    return {
        "per_video": per_video,
        "aggregate": aggregate,
        "verdict": verdict,
        "videos_compared": common,
    }


# ── 보고서 출력 ──────────────────────────────────────────────────────────


def _write_markdown(gap: dict, output_path: Path) -> None:
    md_path = output_path.with_suffix(".md")
    lines = [
        "# RTMW BodyNormalizationProfile gap report",
        "",
        f"- Verdict: **{gap['verdict']}**",
        f"- Videos compared: {len(gap['videos_compared'])}",
        "",
        "## Aggregate (mean abs diff)",
        "",
        "| Field | Mean abs diff |",
        "|-------|---------------|",
    ]
    for f, v in gap["aggregate"].items():
        lines.append(f"| {f} | {v:.4f} |")
    lines.append("")
    lines.append("## Per-video")
    lines.append("")
    for video, diffs in gap["per_video"].items():
        lines.append(f"### {video}")
        for f, v in diffs.items():
            lines.append(f"- {f}: {v:.4f}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "두 RTMW BodyNormalizationProfile dict 의 gap 보고서. "
            "2026-06-08 RTMW pivot 정합 — SMPL-X 비교 폐기."
        )
    )
    parser.add_argument(
        "--rtmw-keypoints-dir",
        type=Path,
        required=True,
        help="RTMW keypoint dump 디렉터리 A (extract_rtmw_body_profile_keypoints 산출).",
    )
    parser.add_argument(
        "--rtmw-keypoints-dir-b",
        type=Path,
        required=True,
        help="RTMW keypoint dump 디렉터리 B (비교 대상).",
    )
    parser.add_argument(
        "--videos",
        nargs="+",
        required=True,
        help="비교할 motion ID 리스트 (예: ref-foxtop ref-invert).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="JSON 보고서 출력 경로. Markdown 은 동일 stem + .md.",
    )
    args = parser.parse_args(argv)

    profiles_a = load_rtmw_profiles(args.rtmw_keypoints_dir, args.videos)
    profiles_b = load_rtmw_profiles(args.rtmw_keypoints_dir_b, args.videos)
    gap = compute_profile_gap(profiles_a, profiles_b)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(gap, indent=2, sort_keys=True), encoding="utf-8"
    )
    _write_markdown(gap, args.output)
    print(f"[OK] body profile gap report: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
