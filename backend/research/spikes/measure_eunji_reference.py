"""정은지 reference 영상 5개 hold moment 6관절 각도 측정 spike (Plan 5-00 Task 1).

목적:
  NotebookLM IPSF Code of Points 2024-2025 lookup (2026-06-04, `05-IPSF-LOOKUP.md` 박제)
  결과 = 현 5영상 yaml hold_moment angle_target=180° / tolerance=±20° / minimum=160° 박제는
  IPSF source 박제 X. belle 박제 결정 (D-17) = Phase 5 첫 plan 책임으로 yaml source 를
  "정은지 reference 측정값 (분기 2 path)" 로 정정. 본 spike 는 그 정정 작업의 source
  측정값 산출 = 5영상 × hold moment frame mean × 6관절 angle 박제.

박제 정신:
  - D-17 (yaml source 정정 작업 = Phase 5 첫 plan 책임)
  - D-18 (tolerance 룰 = 측정값 ±15°, minimum 룰 = 측정값 - 25° — belle 승인 시 변경 가능)
  - D-19 (ref-invert Body Position 차원 = 별 phase 책임)
  - D-20 (ref-climb 이동 횟수 차원 = 별 phase 책임)
  - 05-IPSF-LOOKUP.md (옵션 가+다) — scope 5영상 유지 + yaml source 정은지 reference 박제
  - [[analysis-objectivity-no-human-scores]] — 정은지 reference 객관 측정값 박제 OK
  - [[studio-term-3branch-system]] 분기 2 — "한국 학원 통용 + 정은지 reference 비등재 동작"
  - [[gap-and-line-angle-mandatory-gates]] — 강등/우회 X, 다른 객관 기준 박제
  - D-16 lazy import — boto3 / torch / mmpose / imageio 모듈 로드 시 0 import

산출:
  measurements.json (5영상 × 6관절 × {target, tolerance, minimum, hold_window, raw}) 박제 →
  Task 3 에서 yaml 5개 hold_moment 정정 source.

ref-climb 특수 처리:
  IPSF Transitions & Climbs 카테고리 = angle 차원 채점 X (이동 횟수 채점).
  hold_window 측정 skip + joints={} + ipsf_source="IPSF Transitions & Climbs" 박제.
  yaml hold_moment 빈 list 유지가 정합 (D-20: 이동 횟수 차원 별 phase 책임).

실행 (belle Pod, Task 2 checkpoint 안 — RTMW Pod 환경 + hold timestamps JSON 박제 후):

  cd /workspace/SunityMotion && git pull --ff-only origin main

  # RTMW Pod env 박제 (Plan 11/23 박제 이미 적용됨)
  export RTMW_ONNX_PATH=/workspace/rtmw_weights/.../end2end.onnx
  export AWS_ACCESS_KEY_ID=<...>
  export AWS_SECRET_ACCESS_KEY=<...>
  export AWS_DEFAULT_REGION=ap-northeast-2

  # belle 가 미리 박제한 hold timestamp JSON (5영상 × {hold_start_sec, hold_end_sec})
  cat > /workspace/eunji_hold_timestamps.json <<EOF
  {
    "ref-foxtop": {"hold_start_sec": 4.0, "hold_end_sec": 7.0},
    "ref-foxtop-split": {"hold_start_sec": 5.0, "hold_end_sec": 8.0},
    "ref-invert": {"hold_start_sec": 3.0, "hold_end_sec": 5.0},
    "ref-sideway-spin": {"hold_start_sec": 6.0, "hold_end_sec": 8.5},
    "ref-climb": {"hold_start_sec": 0.0, "hold_end_sec": 0.0}
  }
  EOF

  python3 -m backend.research.spikes.measure_eunji_reference \\
    --motion all \\
    --bucket sunity-motion-pilot-videos \\
    --hold-timestamps-json /workspace/eunji_hold_timestamps.json \\
    --output backend/research/evaluations/reports/eunji_reference_measurements/measurements.json

로컬 단위 검증 (B6 fix — Task 1 verify, Task 2 belle 박제 전):

  PYTHONPATH=backend/shared/python:. python3 -c "
  import sys
  sys.path.insert(0, '.')
  import research.spikes.measure_eunji_reference as m
  assert hasattr(m, 'main')
  assert 'boto3' not in sys.modules
  assert 'torch' not in sys.modules
  assert 'mmpose' not in sys.modules
  print('import + lazy OK')
  "
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# numpy 만 module-level (analysis core 의존성 — Lambda fail-fast 안전).
import numpy as np

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# ── 박제 정신 상수 ────────────────────────────────────────────────────────

# S3 기준 모션 영상 키 경로 (Plan 07/08/10/11 spike 와 동일).
_REFERENCE_VIDEO_PREFIX = "reference"

# FfmpegFrameExtractor target FPS (frame_extractor.py 박제, 9 fps / 640px).
DEFAULT_FPS = 9.0

# 5영상 박제 motion 목록.
ALL_MOTIONS = (
    "ref-climb",
    "ref-foxtop",
    "ref-foxtop-split",
    "ref-invert",
    "ref-sideway-spin",
)

# 6관절 측정 대상 (skeleton.JOINT_KEYS 8관절 중 hold_moment 박제 대상).
# left/right shoulder + left/right hip + left/right knee. 팔꿈치는 hold_moment 박제 X
# (현 yaml 5개 모두 팔꿈치 entry 없음 — Plan 01-15 박제 정신 정합).
MEASURED_JOINTS = (
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
)

# D-18 박제 룰 (2026-06-04 belle 승인 대기 — Task 2 checkpoint 에서 변경 가능).
# 변경 시 tolerance_rule_version 박제 갱신 + measurements.json 재생성 필수.
TOLERANCE_RULE_VERSION = "D-18-2026-06-04"
TOLERANCE_FULL_DEG = 15.0  # 측정값 ± 15° (D-18 박제)
MINIMUM_OFFSET_DEG = 25.0  # 측정값 - 25° (D-18 박제)

# ref-climb 특수 처리 박제 — IPSF Transitions & Climbs 카테고리 (D-20 별 phase 책임).
REF_CLIMB_IPSF_SOURCE = "IPSF Transitions & Climbs"
REF_CLIMB_IPSF_NOTE = (
    "Climbs 카테고리 = 이동 횟수 채점 (D-20 별 phase 책임), angle 채점 X — "
    "yaml hold_moment 빈 list 유지 (의도). NotebookLM IPSF lookup 2026-06-04 "
    "결과 박제 (05-IPSF-LOOKUP.md §1)."
)

# fallback hold timestamp 박제 정신 (B6 fix):
# hold timestamps JSON 미설정 시 영상 길이의 중간 30% 구간 박제 (단위 검증 path).
_FALLBACK_HOLD_FRACTION = 0.3
_FALLBACK_HOLD_CENTER = 0.5


# ── CLI ─────────────────────────────────────────────────────────────────


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI 인자 박제 (D-17 + D-18 박제 정신)."""
    p = argparse.ArgumentParser(
        description=(
            "정은지 reference 영상 5개 hold moment 6관절 angle 측정 spike "
            "(Plan 5-00 Task 1). NotebookLM IPSF lookup 2026-06-04 결과 = "
            "yaml source 정정 작업 (D-17). RTMW Pod 환경 전용 실행."
        )
    )
    p.add_argument(
        "--motion",
        choices=(*ALL_MOTIONS, "all"),
        default="all",
        help="측정 대상 motion. 'all' = 5영상 sweep (default).",
    )
    p.add_argument(
        "--bucket",
        default="sunity-motion-pilot-videos",
        help="S3 bucket (default: sunity-motion-pilot-videos).",
    )
    p.add_argument(
        "--hold-timestamps-json",
        default=None,
        help=(
            "belle 가 박제한 hold timestamp JSON 파일 경로. "
            "schema = {motion: {hold_start_sec: float, hold_end_sec: float}}. "
            "미설정 시 --hold-timestamps-default-fallback 박제 필요 (B6 fix)."
        ),
    )
    p.add_argument(
        "--hold-timestamps-default-fallback",
        action="store_true",
        help=(
            "B6 fix 박제 — Task 1 단위 검증 시점 (belle 박제 전) 영상 길이 중간 30% "
            "fallback 박제. default False (belle 박제 hold timestamps JSON 우선)."
        ),
    )
    p.add_argument(
        "--output",
        default=(
            "backend/research/evaluations/reports/"
            "eunji_reference_measurements/measurements.json"
        ),
        help="측정 결과 JSON 출력 경로.",
    )
    p.add_argument(
        "--video-path",
        default=None,
        help="S3 우회용 로컬 영상 경로 (선택). 1 motion 실행 시만 의미.",
    )
    p.add_argument(
        "--window-size",
        type=int,
        default=None,
        help=(
            "hold_window frame 수 override. 미설정 시 hold 지속시간 × DEFAULT_FPS "
            "자동 계산 (D-18 박제)."
        ),
    )
    return p


# ── S3 다운로드 (D-16 lazy import) ────────────────────────────────────────


def _download_s3(s3_key: str, bucket: str, dest: Path) -> None:
    """S3 → 로컬 경로 다운로드 (Plan 07/08/10/11 spike 박제 패턴).

    D-16 박제 정신: boto3 는 함수 내부 lazy import — 로컬 단위 검증에서 0 import.
    """
    import boto3  # noqa: PLC0415 — Pod 환경 lazy import (D-16 박제)

    s3 = boto3.client("s3")
    log.info("downloading s3://%s/%s -> %s", bucket, s3_key, dest)
    s3.download_file(bucket, s3_key, str(dest))


def _resolve_video(
    motion: str,
    video_path: str | None,
    bucket: str,
    tmp_dir: Path,
) -> str:
    """로컬 경로 또는 S3 key → 로컬 파일 경로 (spike_rtmpose.py 박제 패턴)."""
    if video_path is not None:
        if not Path(video_path).exists():
            raise FileNotFoundError(f"영상 파일 없음: {video_path}")
        return video_path

    s3_key = f"{_REFERENCE_VIDEO_PREFIX}/{motion}.mp4"
    local_path = tmp_dir / f"{motion}.mp4"
    _download_s3(s3_key, bucket, local_path)
    return str(local_path)


# ── 프레임 추출 (D-16 lazy import) ────────────────────────────────────────


def _extract_frames(video_path: str) -> np.ndarray:
    """영상 → (T, H, W, 3) RGB uint8. FfmpegFrameExtractor (9fps / 640px).

    D-16 박제 정신: frame_extractor 가 imageio 를 내부 lazy import — 본 함수
    호출 시점에서만 imageio 로드. Plan 07/08 spike 박제 패턴 그대로.
    """
    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: PLC0415

    extractor = FfmpegFrameExtractor()
    frames = extractor.extract(video_path)
    log.info(
        "frames extracted T=%d shape=%s",
        len(frames),
        frames.shape if hasattr(frames, "shape") else "list",
    )
    return np.asarray(frames, dtype=np.uint8)


# ── RTMW pose → angles 산출 (D-16 lazy import) ───────────────────────────


def _compute_rtmw_angles(frames: np.ndarray) -> np.ndarray:
    """RTMW wholebody pose 산출 → (T, 8) joint angles 도.

    D-16 박제 정신: rtmlib / torch / mmpose / RTMWPoseEngine 은 함수 내부
    lazy import. PoseEngine Protocol 박제 패턴 (D-12 Pod 안 1pass) 정합.
    Plan 01-23 박제 RTMW Pod env (RTMW_ONNX_PATH 등) 사전 설정 가정.

    Returns:
        angles: (T, NUM_JOINTS=8) 도. JOINT_KEYS 순서 (skeleton.py 박제).
            미감지 프레임은 NaN — temporal 보간 책임 외부 (본 spike 는 raw 박제).
    """
    # PoseEngine Protocol 박제 (RTMWPoseEngine 인스턴스화 시점 lazy import).
    from sunity_shared.analysis.features import compute_joint_angles  # noqa: PLC0415
    from sunity_shared.analysis.pose_engines import RTMWPoseEngine  # noqa: PLC0415
    from sunity_shared.analysis.pose_frame import (  # noqa: PLC0415
        PoleAxis,
        to_coco17_array,
    )

    log.info("RTMWPoseEngine init (lazy import 박제) — Pod 환경 의존성 로드")
    engine = RTMWPoseEngine(target_fps=int(DEFAULT_FPS))

    # 폴 축은 본 spike scope 외 — HoughPoleDetector 미설치 (Plan 23 박제).
    # 수직 폴백 (axis_vector=(0, 1, 0), confidence=low) 사용.
    pole_axis = PoleAxis.vertical_fallback()

    pose_frames = engine.estimate(frames, pole_axis)
    keypoints = to_coco17_array(pose_frames)  # (T, 17, 4=xyz+uncertainty)
    angles = compute_joint_angles(keypoints)  # (T, NUM_JOINTS=8) 도
    log.info(
        "joint angles computed shape=%s (skeleton.JOINT_KEYS 순서)",
        angles.shape,
    )
    return angles


# ── hold_window 측정 (D-17 + D-18 박제 정신) ─────────────────────────────


def _measure_hold_window(
    angles: np.ndarray,
    hold_start_sec: float,
    hold_end_sec: float,
    fps: float = DEFAULT_FPS,
    window_size_override: int | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    """hold 구간 frame indices 산출 → 6관절 mean angle 측정.

    Args:
        angles: (T, NUM_JOINTS=8) 관절각도 (skeleton.JOINT_KEYS 순서).
        hold_start_sec: hold moment 시작 시각 (초).
        hold_end_sec: hold moment 종료 시각 (초).
        fps: frame extractor target FPS (default = 9.0).
        window_size_override: hold_window frame 수 override (선택).

    Returns:
        (joint_means, window_meta):
          joint_means: {joint_name: mean_angle_deg} — 6 entries (MEASURED_JOINTS).
          window_meta: {start_sec, end_sec, start_frame, end_frame, fps}.

    박제 정신 (D-17):
        hold 구간 frame mean 산출 = 정은지 reference 측정값 박제 source.
        NaN 무시 (np.nanmean) — RTMW 미감지 프레임 흡수.
        팔꿈치 entry 박제 X (yaml hold_moment 6관절만 박제 — Plan 01-15 정합).
    """
    from sunity_shared.analysis.skeleton import JOINT_KEYS  # noqa: PLC0415

    T, num_joints = angles.shape
    if num_joints != len(JOINT_KEYS):
        raise ValueError(
            f"angles 형상 (T, NUM_JOINTS) = (T, {len(JOINT_KEYS)}) 이어야 함. "
            f"실제 = {angles.shape}. skeleton.JOINT_KEYS 박제 정합 확인."
        )

    start_frame = max(0, int(round(hold_start_sec * fps)))
    end_frame = min(T, int(round(hold_end_sec * fps)))
    if window_size_override is not None:
        # window_size override 시 hold_start_sec 기준 + window_size frames.
        end_frame = min(T, start_frame + max(1, window_size_override))
    if end_frame <= start_frame:
        raise ValueError(
            f"hold_window 무효: start={start_frame} end={end_frame} T={T} "
            f"hold_start_sec={hold_start_sec} hold_end_sec={hold_end_sec}. "
            "belle 박제 hold timestamps JSON 확인 (Task 2 checkpoint)."
        )

    window = angles[start_frame:end_frame]  # (W, 8)
    # NaN 무시 mean — RTMW 미감지 프레임 흡수.
    joint_means: dict[str, float] = {}
    for joint in MEASURED_JOINTS:
        idx = JOINT_KEYS.index(joint)
        values = window[:, idx]
        valid = values[~np.isnan(values)]
        if len(valid) == 0:
            # 전 프레임 RTMW 미감지 — measurement_unreliable 박제 path
            # (belle Task 2 검토 시 root cause 분석 후 재실행 책임).
            joint_means[joint] = float("nan")
        else:
            joint_means[joint] = float(np.mean(valid))

    window_meta = {
        "start_sec": float(hold_start_sec),
        "end_sec": float(hold_end_sec),
        "start_frame": int(start_frame),
        "end_frame": int(end_frame),
        "fps": float(fps),
        "window_frames": int(end_frame - start_frame),
    }
    return joint_means, window_meta


# ── D-18 tolerance 룰 박제 ────────────────────────────────────────────────


def _apply_tolerance_rule(measured_deg: float) -> dict[str, float]:
    """D-18 박제 룰 적용 — 측정값 → (target, tolerance, minimum).

    D-18 (2026-06-04 박제, belle 승인 대기):
      angle_target       = measured_deg (측정값 그대로 박제)
      tolerance_full     = TOLERANCE_FULL_DEG (±15°)
      minimum_requirement = measured_deg - MINIMUM_OFFSET_DEG (측정값 - 25°)

    Task 2 belle 검토 후 룰 변경 시 본 함수 박제 갱신 + measurements.json 재생성 +
    tolerance_rule_version 박제 새 값.
    """
    if measured_deg != measured_deg:  # NaN check (X != X iff X is NaN)
        return {
            "measured_deg": float("nan"),
            "angle_target": float("nan"),
            "tolerance_full": TOLERANCE_FULL_DEG,
            "minimum_requirement": float("nan"),
        }
    return {
        "measured_deg": float(measured_deg),
        "angle_target": float(measured_deg),
        "tolerance_full": float(TOLERANCE_FULL_DEG),
        "minimum_requirement": float(measured_deg - MINIMUM_OFFSET_DEG),
    }


# ── hold timestamps 박제 로딩 (B6 fix) ────────────────────────────────────


def _load_hold_timestamps(
    hold_timestamps_json: str | None,
    use_fallback: bool,
) -> dict[str, dict[str, float]]:
    """belle 박제 hold timestamps JSON 로딩 또는 fallback 박제.

    B6 fix (2026-06-04 revision):
      Task 1 verify 가 Task 2 belle 산출물 (hold timestamps) 요구 시 순환 의존 →
      --hold-timestamps-default-fallback 박제로 단위 검증 path 박제 (영상 길이 중간
      30% 구간 fallback). belle 박제 hold timestamps JSON 우선.

    Returns:
        {motion: {hold_start_sec: float, hold_end_sec: float}} dict.
        fallback mode 시 빈 dict 반환 — _measure_one_motion 에서 영상 길이로 계산.
    """
    if hold_timestamps_json is not None:
        path = Path(hold_timestamps_json)
        if not path.exists():
            raise FileNotFoundError(
                f"hold timestamps JSON 없음: {path}. "
                "Task 2 belle 박제 작업 (5영상 × hold_start_sec/hold_end_sec) 확인."
            )
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        log.info("hold timestamps 박제 로드 = %s", path)
        return data

    if not use_fallback:
        raise RuntimeError(
            "--hold-timestamps-json 또는 --hold-timestamps-default-fallback 박제 필요. "
            "B6 fix (2026-06-04 revision) 박제 정신: belle 박제 hold timestamps 우선, "
            "fallback 박제는 Task 1 단위 검증 path 만 사용."
        )

    log.info(
        "hold timestamps fallback 박제 활성 (B6 fix) — 영상 길이 중간 %.0f%% 박제",
        _FALLBACK_HOLD_FRACTION * 100,
    )
    return {}


def _fallback_hold_window(num_frames: int, fps: float) -> dict[str, float]:
    """영상 길이 중간 30% 구간 fallback 박제 (B6 fix)."""
    if num_frames < 2:
        # 영상 짧음 → 전체 사용 (단위 검증 path 보호).
        return {"hold_start_sec": 0.0, "hold_end_sec": max(1, num_frames) / fps}
    total_sec = num_frames / fps
    half_window = total_sec * _FALLBACK_HOLD_FRACTION / 2.0
    center = total_sec * _FALLBACK_HOLD_CENTER
    return {
        "hold_start_sec": max(0.0, center - half_window),
        "hold_end_sec": min(total_sec, center + half_window),
    }


# ── 단일 motion 측정 ──────────────────────────────────────────────────────


def _measure_one_motion(
    motion: str,
    video_path: str | None,
    bucket: str,
    hold_timestamps: dict[str, dict[str, float]],
    use_fallback: bool,
    window_size_override: int | None,
    tmp_dir: Path,
) -> dict[str, Any]:
    """단일 motion 측정 → measurements JSON 단일 entry 박제.

    ref-climb 특수 처리: IPSF Transitions & Climbs 카테고리 박제 (D-20 별 phase 책임) →
    hold_window 측정 skip + joints={} + ipsf_source 박제.
    """
    measured_at = datetime.now(timezone.utc).isoformat()

    # ref-climb 특수 처리 (NotebookLM IPSF lookup 2026-06-04 박제, 05-IPSF-LOOKUP.md §1).
    if motion == "ref-climb":
        log.info(
            "ref-climb 특수 처리 — IPSF Transitions & Climbs 카테고리 (D-20 별 phase 책임). "
            "hold_window 측정 skip + joints={} + ipsf_source 박제."
        )
        return {
            "motion": motion,
            "video_path": None,
            "hold_window": None,
            "joints": {},
            "tolerance_rule_version": TOLERANCE_RULE_VERSION,
            "source": (
                "정은지 reference 측정값 (분기 2 path) — ref-climb 은 IPSF Climbs "
                "카테고리 = angle 채점 X, hold_window 측정 skip"
            ),
            "ipsf_source": REF_CLIMB_IPSF_SOURCE,
            "ipsf_source_note": REF_CLIMB_IPSF_NOTE,
            "measured_at_utc": measured_at,
        }

    # 영상 확보 + 프레임 추출 + RTMW pose → angles.
    resolved_video = _resolve_video(motion, video_path, bucket, tmp_dir)
    frames = _extract_frames(resolved_video)
    angles = _compute_rtmw_angles(frames)

    # hold timestamps 박제 결정 (belle JSON 우선, fallback B6 fix).
    if motion in hold_timestamps:
        ts = hold_timestamps[motion]
    elif use_fallback:
        ts = _fallback_hold_window(num_frames=angles.shape[0], fps=DEFAULT_FPS)
        log.info(
            "motion=%s fallback hold_window 박제 (B6 fix) = %s",
            motion, ts,
        )
    else:
        raise RuntimeError(
            f"motion={motion} hold timestamps 박제 부재. "
            "belle 박제 JSON 또는 --hold-timestamps-default-fallback 박제 필요."
        )

    joint_means, window_meta = _measure_hold_window(
        angles=angles,
        hold_start_sec=ts["hold_start_sec"],
        hold_end_sec=ts["hold_end_sec"],
        fps=DEFAULT_FPS,
        window_size_override=window_size_override,
    )

    joints_payload: dict[str, dict[str, float]] = {}
    for joint, mean_deg in joint_means.items():
        joints_payload[joint] = _apply_tolerance_rule(mean_deg)

    return {
        "motion": motion,
        "video_path": resolved_video,
        "hold_window": window_meta,
        "joints": joints_payload,
        "tolerance_rule_version": TOLERANCE_RULE_VERSION,
        "source": (
            "정은지 reference 측정값 (분기 2 path) — RTMW wholebody + "
            "hold_window mean (D-18 박제 룰)"
        ),
        "ipsf_source": None,
        "ipsf_source_note": (
            "NotebookLM IPSF Code of Points 2024-2025 lookup 2026-06-04 결과 "
            "IPSF source 박제 X (05-IPSF-LOOKUP.md). yaml source = 분기 2 path "
            "(studio-term-3branch-system)."
        ),
        "measured_at_utc": measured_at,
    }


# ── main ─────────────────────────────────────────────────────────────────


def _setup_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )


def main(argv: list[str] | None = None) -> int:
    """5영상 측정 sweep 또는 단일 motion 측정 → measurements.json 박제."""
    _setup_logging()
    args = build_arg_parser().parse_args(argv)

    if args.motion == "all":
        motions = list(ALL_MOTIONS)
    else:
        motions = [args.motion]

    hold_timestamps = _load_hold_timestamps(
        hold_timestamps_json=args.hold_timestamps_json,
        use_fallback=args.hold_timestamps_default_fallback,
    )

    log.info(
        "Plan 5-00 spike 박제 시작 — 5영상 정은지 reference 측정 (D-17/D-18). "
        "motions=%s bucket=%s output=%s tolerance_rule=%s",
        motions, args.bucket, args.output, TOLERANCE_RULE_VERSION,
    )

    results: dict[str, Any] = {
        "tolerance_rule_version": TOLERANCE_RULE_VERSION,
        "tolerance_full_deg": TOLERANCE_FULL_DEG,
        "minimum_offset_deg": MINIMUM_OFFSET_DEG,
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_path": "분기 2 (studio-term-3branch-system) — 정은지 reference 측정값",
        "ipsf_lookup_ref": "05-IPSF-LOOKUP.md (NotebookLM 2026-06-04)",
        "motions": {},
    }

    with tempfile.TemporaryDirectory(prefix="eunji_measure_") as tmp:
        tmp_dir = Path(tmp)
        for motion in motions:
            log.info("─── motion=%s 측정 시작 ───", motion)
            try:
                entry = _measure_one_motion(
                    motion=motion,
                    video_path=args.video_path if len(motions) == 1 else None,
                    bucket=args.bucket,
                    hold_timestamps=hold_timestamps,
                    use_fallback=args.hold_timestamps_default_fallback,
                    window_size_override=args.window_size,
                    tmp_dir=tmp_dir,
                )
                results["motions"][motion] = entry
                log.info("motion=%s 측정 완료 — joints=%d", motion, len(entry["joints"]))
            except Exception as exc:  # noqa: BLE001
                log.exception("motion=%s 측정 실패: %s", motion, exc)
                results["motions"][motion] = {
                    "motion": motion,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "measured_at_utc": datetime.now(timezone.utc).isoformat(),
                }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    log.info("measurements 박제 완료 → %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
