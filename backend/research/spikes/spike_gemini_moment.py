"""Gemini key moment + IPSF criteria 비교 spike (Plan 01-13 T-3).

목적:
  Plan 12 dominant (a) frame-mean 한계의 해결 path 를 end-to-end 검증한다 —
  Gemini 가 영상에서 phase 별 key moment 시점을 추출 → 해당 frame 의 측정 각도를
  Plan 15 `GeometricCriterion` 과 비교 → 갭 / 감점 / minimum 미달 점검.

본 spike 는 운영 코드 / 기존 spike (spike_rtmpose, sweep_rtmpose, 등) 0줄 수정.
운영 코드 진입은 Plan 14 통과 후 별 plan 책임.

두 mode:
  · `report-only` — stub KeyMoment + stub angles 로 moment_dimensions 만 검증.
                    로컬 실행 가능 (Pod / Gemini API / mmpose / MotionBERT 의존성 0).
  · `live`        — belle Pod 에서 실 Gemini API 호출 + RTMPose+MB pipeline 실행.
                    spike_rtmpose 의 helper (_resolve_video / _extract_frames / ...) 재사용.

empty criteria 가드:
  load_grouped_criteria 결과의 entry 수 == 0 이면 Plan 15 IPSF 라벨링 미진입으로
  판단해 RuntimeError. ref-climb 같은 의도된 빈 템플릿은 motion 인자에 사용하지 말 것.

출력:
  --out 경로에 JSON + sibling .md 동시 저장. KeyMoment / per-joint gap / minimum_failures
  / Plan 14 게이트 통과 여부 박제.

요구사항:
  · REQUIREMENTS.md POSE-01 + SCORE-01.
  · 01-15-SUMMARY decisions §3 (D-14 게이트 baseline = IPSF gap ≤ tolerance_full).
  · memory: analysis-objectivity-no-human-scores (사람 점수 라벨링 0건).

실행 (report-only, 로컬):

  PYTHONPATH=backend/shared/python:. python3 -m backend.research.spikes.spike_gemini_moment \\
    --mode report-only \\
    --motion ref-invert \\
    --out backend/research/spikes/reports/spike_gemini_moment_$(date +%Y%m%d_%H%M).json

실행 (live, belle Pod 전용):

  cd /workspace/SunityMotion && git pull --ff-only origin main
  export GEMINI_API_KEY=$(aws ssm get-parameter --name /sunity/motion/gemini-api-key \\
    --with-decryption --query 'Parameter.Value' --output text --region ap-northeast-2)

  python3 -m backend.research.spikes.spike_gemini_moment \\
    --mode live \\
    --motion ref-invert \\
    --bucket sunity-motion-pilot-videos \\
    --gemini-model gemini-2.5-pro \\
    --rtmpose-config /workspace/rtmpose_weights/rtmpose-l_8xb256-420e_coco-256x192.py \\
    --rtmpose-checkpoint /workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth \\
    --motionbert-root /workspace/MotionBERT \\
    --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin \\
    --out backend/research/spikes/reports/spike_gemini_moment_live_$(date +%Y%m%d_%H%M).json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Plan 13 게이트 임계 — Plan 14 sweep 진입 기대.
PLAN_14_MINIMUM_FAILURE_LIMIT = 0   # minimum 미달 entry 0 건 = Plan 14 통과 후보.
PLAN_14_LINE_SCORE_TARGET = 60      # line 차원 60 이상 = pilot 신뢰 기준 (보수 추정).
PLAN_14_ANGLE_SCORE_TARGET = 60     # angle 차원 60 이상.

DEFAULT_FPS = 9.0  # spike_rtmpose / spike_motionbert frame extractor 와 동일.
_REPORTS_DIRNAME = "reports"
_REFERENCE_VIDEO_PREFIX = "reference"


# ────────────────────────────── CLI ──────────────────────────────


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Gemini key moment + IPSF criteria 비교 spike (Plan 01-13). "
            "report-only mode = 로컬 stub 검증, live mode = belle Pod 실 호출."
        )
    )
    p.add_argument(
        "--mode",
        choices=("report-only", "live"),
        default="report-only",
        help="report-only = stub 입력 (로컬 OK). live = Gemini + RTMPose+MB 실행 (Pod 전용).",
    )
    p.add_argument(
        "--motion",
        required=True,
        help="기준 동작 ID (예: ref-invert). Plan 15 IPSF 라벨링이 진입된 motion 이어야 함.",
    )
    p.add_argument(
        "--bucket",
        default="sunity-motion-pilot-videos",
        help="live mode 의 S3 버킷 (영상 다운로드).",
    )
    p.add_argument(
        "--gemini-model",
        default="gemini-2.5-pro",
        help="Gemini 모델 명 (live mode 만 사용).",
    )
    p.add_argument(
        "--rtmpose-config",
        default=None,
        help="live mode RTMPose config (.py). Pod 경로.",
    )
    p.add_argument(
        "--rtmpose-checkpoint",
        default=None,
        help="live mode RTMPose 가중치 (.pth). Pod 경로.",
    )
    p.add_argument(
        "--motionbert-root",
        default="/workspace/MotionBERT",
        help="live mode MotionBERT 저장소 경로.",
    )
    p.add_argument(
        "--motionbert-weights",
        default=None,
        help="live mode MotionBERT best_epoch.bin 경로.",
    )
    p.add_argument(
        "--score-threshold",
        type=float,
        default=0.3,
        help="RTMPose keypoint score threshold (live mode).",
    )
    p.add_argument(
        "--fps",
        type=float,
        default=DEFAULT_FPS,
        help="영상 fps — frame_index 후처리에 사용 (live mode).",
    )
    p.add_argument(
        "--out",
        default=None,
        help="결과 JSON 경로. 미지정 시 backend/research/spikes/reports/spike_gemini_moment_<UTC>.json.",
    )
    return p


def _default_out_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]  # backend/research/spikes → backend
    reports = repo_root / "research" / "spikes" / _REPORTS_DIRNAME
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    return reports / f"spike_gemini_moment_{stamp}.json"


# ─────────────────── empty criteria 가드 ───────────────────


def _flatten_grouped_count(grouped: dict) -> int:
    return sum(len(v) for v in grouped.values())


def _assert_criteria_present(motion: str, grouped: dict) -> None:
    """grouped 전체 entry 0 건이면 Plan 15 미진입 → RuntimeError 명확 메시지."""
    total = _flatten_grouped_count(grouped)
    if total == 0:
        raise RuntimeError(
            f"motion={motion} 의 GeometricCriterion 이 0건 — Plan 15 IPSF 라벨링 미진입. "
            f"belle 라벨링이 완료된 motion 만 본 spike 입력 가능. "
            f"빈 템플릿 (예: ref-climb IPSF Climbs 카테고리) 은 의도된 빈 list 이므로 "
            f"본 spike scope 외. 다른 motion 선택 또는 Plan 15 T-5 belle 라벨링 진행."
        )


# ─────────────────── report-only mode (stub) ───────────────────


def _build_report_only_stub() -> dict:
    """Pod 의존 없이 moment_dimensions + GeminiMomentExtractor.validate 흐름을 검증할 stub.

    stub angles: T=20 프레임, 8 joints. frame 10 에서 양쪽 무릎 신전 175°, 어깨 신전 178°.
    stub KeyMoment: hold frame=10. 측정 dict 와 criteria 매칭 확인용.
    """
    import numpy as np

    from sunity_shared.analysis.skeleton import JOINT_KEYS

    angles = np.full((20, len(JOINT_KEYS)), 170.0)
    angles[10, JOINT_KEYS.index("left_knee")] = 175.0
    angles[10, JOINT_KEYS.index("right_knee")] = 175.0
    angles[10, JOINT_KEYS.index("left_shoulder")] = 178.0
    return {"angles": angles, "frame_index": 10, "fps": DEFAULT_FPS}


def _run_report_only(motion: str) -> dict:
    """stub 입력으로 measure_moment_angles + score_moment 흐름 검증.

    실 Gemini / mmpose / torch 의존성 0 — 로컬 smoke 가능.
    Plan 15 criteria 가 비어있는 motion (ref-climb) 은 RuntimeError.
    """
    from sunity_shared.judging import (
        KeyMoment,
        load_grouped_criteria,
        measure_moment_angles,
        score_moment,
    )
    from sunity_shared.judging.geometric_criterion import VALID_MOMENT_KEYS

    grouped = load_grouped_criteria(motion)
    _assert_criteria_present(motion, grouped)

    stub = _build_report_only_stub()
    angles = stub["angles"]
    fi = stub["frame_index"]
    fps = stub["fps"]

    # stub KeyMoment — caller (실 Gemini) 가 응답한다고 가정한 hold 시점.
    stub_moment = KeyMoment(
        motion=motion,
        moment_key="hold",
        timestamp_seconds=fi / fps,
        frame_index=fi,
        confidence=0.85,
        source_response_excerpt='{"moments":[{"moment_key":"hold"}]} (report-only stub)',
    )
    stub_moment.validate()

    per_moment: list[dict] = []
    for mkey in VALID_MOMENT_KEYS:
        moment_criteria = grouped.get(mkey, [])
        if not moment_criteria:
            continue
        # stub 은 hold 시점만 제공 — 다른 phase 는 hold 와 동일 frame 사용 (스모크 단순성).
        # 실 live mode 는 Gemini 가 phase 별 시점을 따로 반환.
        joint_keys = tuple(c.joint_key for c in moment_criteria)
        measured = measure_moment_angles(
            angles, frame_index=stub_moment.frame_index, joint_keys=joint_keys
        )
        score = score_moment(measured, moment_criteria)
        per_moment.append(
            _serialize_moment_result(stub_moment, mkey, measured, score)
        )

    return {
        "mode": "report-only",
        "motion": motion,
        "moments": per_moment,
        "gate": _evaluate_plan_14_gate(per_moment),
    }


def _serialize_moment_result(
    key_moment: "object",  # KeyMoment - 순환 import 피하려고 type 만 docstring 으로 박제
    moment_key: str,
    measured: dict[str, float],
    score: dict,
) -> dict:
    """score_moment dict 를 JSON-serializable 으로 변환 (CriteriaGap dataclass → dict)."""
    per_joint = [
        asdict(gap) if is_dataclass(gap) else gap for gap in score["per_joint"]
    ]
    return {
        "moment_key": moment_key,
        "key_moment": {
            "motion": key_moment.motion,  # type: ignore[attr-defined]
            "moment_key": key_moment.moment_key,  # type: ignore[attr-defined]
            "timestamp_seconds": key_moment.timestamp_seconds,  # type: ignore[attr-defined]
            "frame_index": key_moment.frame_index,  # type: ignore[attr-defined]
            "confidence": key_moment.confidence,  # type: ignore[attr-defined]
        },
        "measured_angles": measured,
        "line": score["line"],
        "angle": score["angle"],
        "criteria_count": score["criteria_count"],
        "minimum_failures": score["minimum_failures"],
        "per_joint": per_joint,
    }


def _evaluate_plan_14_gate(per_moment: list[dict]) -> dict:
    """Plan 14 진입 게이트 판정.

      · minimum_failures 0 건 across all moments.
      · 각 moment 의 line/angle 점수가 임계값 (60) 이상.
    """
    total_minimum_failures = sum(
        len(m["minimum_failures"]) for m in per_moment
    )
    line_scores = [m["line"] for m in per_moment if m["line"] is not None]
    angle_scores = [m["angle"] for m in per_moment if m["angle"] is not None]

    line_pass = (
        all(s >= PLAN_14_LINE_SCORE_TARGET for s in line_scores) if line_scores else False
    )
    angle_pass = (
        all(s >= PLAN_14_ANGLE_SCORE_TARGET for s in angle_scores) if angle_scores else False
    )
    minimum_pass = total_minimum_failures <= PLAN_14_MINIMUM_FAILURE_LIMIT

    if not per_moment:
        verdict = "no_criteria"
    elif minimum_pass and line_pass and angle_pass:
        verdict = "plan_14_gate_pass"
    elif not minimum_pass:
        verdict = "minimum_requirement_fail"
    else:
        verdict = "below_target_score"

    return {
        "total_minimum_failures": total_minimum_failures,
        "line_pass": line_pass,
        "angle_pass": angle_pass,
        "minimum_pass": minimum_pass,
        "verdict": verdict,
        "thresholds": {
            "minimum_failure_limit": PLAN_14_MINIMUM_FAILURE_LIMIT,
            "line_score_target": PLAN_14_LINE_SCORE_TARGET,
            "angle_score_target": PLAN_14_ANGLE_SCORE_TARGET,
        },
    }


# ─────────────────── live mode (belle Pod 전용) ───────────────────


def _run_live(args: argparse.Namespace) -> dict:
    """live mode — Gemini + RTMPose+MB 실행. 헬퍼는 spike_rtmpose 그대로 호출 (무수정)."""
    if not args.rtmpose_config or not args.rtmpose_checkpoint:
        raise RuntimeError(
            "live mode 는 --rtmpose-config / --rtmpose-checkpoint 모두 필요. "
            "Pod 경로 (예: /workspace/rtmpose_weights/...) 지정 필요."
        )
    if not args.motionbert_weights:
        raise RuntimeError(
            "live mode 는 --motionbert-weights 필요 "
            "(예: /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin)."
        )

    motion = args.motion

    # spike_rtmpose 헬퍼 lazy import — mmpose / torch / numpy 등 무거운 의존성 격리.
    from .spike_rtmpose import (  # type: ignore
        _extract_frames,
        _h36m17_to_coco17_subset,
        _load_motionbert,
        _resolve_video,
        _run_motionbert_inference,
        _run_rtmpose_2d,
    )
    from sunity_shared.analysis.features import compute_joint_angles, joint_uncertainty
    from sunity_shared.analysis.temporal import temporal_fill

    from sunity_shared.judging import (
        GeminiMomentExtractor,
        assign_frame_indices,
        load_grouped_criteria,
        measure_moment_angles,
        score_moment,
    )

    grouped = load_grouped_criteria(motion)
    _assert_criteria_present(motion, grouped)

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        video = _resolve_video(None, motion, args.bucket, tmp_dir)
        frames = _extract_frames(video)
        T = frames.shape[0]

        log.info("RTMPose 2D — %d frames", T)
        rtmpose_kp, image_size, avg_rtm_score = _run_rtmpose_2d(
            frames,
            args.rtmpose_config,
            args.rtmpose_checkpoint,
        )

        # spike_rtmpose 의 H36M 17 변환은 보존 — lift 입력만 사용.
        from .rtmpose_to_h36m17 import convert_rtmpose_coco17_to_h36m17  # type: ignore

        h36m_2d = convert_rtmpose_coco17_to_h36m17(
            rtmpose_kp, image_size, score_threshold=args.score_threshold
        )

        model, device = _load_motionbert(args.motionbert_root, args.motionbert_weights)
        h36m_xyz = _run_motionbert_inference(model, device, h36m_2d)
        coco17_array = _h36m17_to_coco17_subset(h36m_xyz)

        angles = compute_joint_angles(coco17_array)
        filled = temporal_fill(angles, uncertainty=joint_uncertainty(coco17_array))

        # Gemini key moment 추출.
        extractor = GeminiMomentExtractor(model_name=args.gemini_model)
        raw_moments = extractor.extract_key_moments(video, motion)
        filled_moments = assign_frame_indices(
            raw_moments, fps=args.fps, frames_total=T
        )

        per_moment: list[dict] = []
        for m in filled_moments:
            moment_criteria = grouped.get(m.moment_key, [])
            if not moment_criteria:
                # 라벨링 entry 0건 phase — skip (다른 phase 가 채워질 수 있음).
                log.info(
                    "moment_key=%s: criteria 0건 → skip (Plan 15 미라벨링)", m.moment_key
                )
                continue
            joint_keys = tuple(c.joint_key for c in moment_criteria)
            measured = measure_moment_angles(
                filled, frame_index=m.frame_index, joint_keys=joint_keys
            )
            score = score_moment(measured, moment_criteria)
            per_moment.append(_serialize_moment_result(m, m.moment_key, measured, score))

        return {
            "mode": "live",
            "motion": motion,
            "frames_total": T,
            "fps": args.fps,
            "avg_rtm_score": round(float(avg_rtm_score), 4),
            "moments": per_moment,
            "gate": _evaluate_plan_14_gate(per_moment),
        }


# ─────────────────── 출력 ───────────────────


def _generate_markdown(result: dict) -> str:
    lines: list[str] = [
        "# Spike: Gemini key moment + IPSF criteria (Plan 01-13)",
        "",
        f"생성: {result.get('generated_at', 'N/A')}",
        f"mode: `{result.get('mode', 'N/A')}`",
        f"motion: `{result.get('motion', 'N/A')}`",
        "",
        "## Plan 14 진입 게이트",
        "",
    ]

    gate = result.get("gate", {})
    lines.append(f"verdict: `{gate.get('verdict', 'N/A')}`")
    lines.append("")
    lines.append("| 항목 | 값 | 임계 | 통과 |")
    lines.append("|---|---|---|---|")
    th = gate.get("thresholds", {})
    lines.append(
        f"| minimum 미달 entry | {gate.get('total_minimum_failures', 'N/A')} "
        f"| ≤ {th.get('minimum_failure_limit', 'N/A')} "
        f"| {gate.get('minimum_pass', False)} |"
    )
    lines.append(
        f"| line 차원 | (per-moment) "
        f"| ≥ {th.get('line_score_target', 'N/A')} "
        f"| {gate.get('line_pass', False)} |"
    )
    lines.append(
        f"| angle 차원 | (per-moment) "
        f"| ≥ {th.get('angle_score_target', 'N/A')} "
        f"| {gate.get('angle_pass', False)} |"
    )

    lines.append("")
    lines.append("## per-moment 결과")
    lines.append("")
    lines.append("| moment | frame_idx | criteria_count | line | angle | min_fail |")
    lines.append("|---|---|---|---|---|---|")
    for m in result.get("moments", []):
        km = m.get("key_moment", {})
        lines.append(
            f"| {m.get('moment_key', 'N/A')} "
            f"| {km.get('frame_index', 'N/A')} "
            f"| {m.get('criteria_count', 'N/A')} "
            f"| {m.get('line') if m.get('line') is not None else 'N/A'} "
            f"| {m.get('angle') if m.get('angle') is not None else 'N/A'} "
            f"| {len(m.get('minimum_failures', []))} |"
        )

    lines.append("")
    lines.append("## per-joint gap (각 moment 상세)")
    lines.append("")
    for m in result.get("moments", []):
        lines.append(f"### {m.get('moment_key', 'N/A')}")
        lines.append("")
        lines.append("| joint | measured | target | gap | beyond_tol | deduction | min_met | score |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for g in m.get("per_joint", []):
            lines.append(
                f"| {g.get('joint_key', 'N/A')} "
                f"| {g.get('measured_angle', 'N/A'):.1f} "
                f"| {g.get('angle_target', 'N/A'):.1f} "
                f"| {g.get('gap', 'N/A'):.1f} "
                f"| {g.get('beyond_tolerance', 'N/A'):.1f} "
                f"| {g.get('deduction', 'N/A'):.2f} "
                f"| {g.get('minimum_met', 'N/A')} "
                f"| {g.get('score', 'N/A')} |"
            )
        lines.append("")
    return "\n".join(lines)


def run_spike(args: argparse.Namespace) -> dict:
    if args.mode == "report-only":
        result = _run_report_only(args.motion)
    else:
        result = _run_live(args)

    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["motion"] = args.motion

    out = Path(args.out) if args.out else _default_out_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    log.info("JSON: %s", out)
    md = out.with_suffix(".md")
    with open(md, "w", encoding="utf-8") as f:
        f.write(_generate_markdown(result))
    log.info("Markdown: %s", md)
    return result


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_arg_parser().parse_args()
    try:
        run_spike(args)
    except RuntimeError as exc:
        log.error("spike 실패: %s", exc)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    sys.exit(main())
