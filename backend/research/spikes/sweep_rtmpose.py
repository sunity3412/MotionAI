"""RTMPose + MotionBERT 5영상 sweep 하네스 (Plan 01-11).

Plan 10 = ref-sideway-spin 단일 영상 STRONG_PASS (overall 72.0). Plan 11 =
같은 spike 를 Plan 08 5영상 (ref-climb / ref-foxtop-split / ref-foxtop /
ref-invert / ref-sideway-spin) 에 회귀 실행해서 RTMPose+MB 가 4영상에서도
PASS 유지하는지 확인 + 게이트 룰 verdict (5/5, 4/5, 3/5) 박제.

본 모듈은 Plan 10 `spike_rtmpose.run_spike` 를 영상 list 로 wrapping 만 함.
2D 추출 / lift / 점수 계산 chain 은 그대로 — 코드 1벌 원칙 (분기 0).

라이선스: 운영 코드베이스 (Sunity AI Coach) 와 동일.

판정 기준 (T-3 게이트 룰 검토 결과 반영):
  - D-15① overall ≥ 70 영상 수가 5/5 → "Strong pass — Wave 3 진입"
  - 4/5 → "Conditional pass — 4/5 수용 + Wave 3 진입, Phase 5 우선순위 ↑"
  - 3/5 이하 → "Regression — Plan 12 추가 검토 (HybrIK 또는 MP+MB 유지)"
  - 별도: line/angle 5영상 모두 N/A 면 Phase 5 Gemini 통합 우선순위 박제

실행 (belle Pod, mmpose 1.3.2 / numpy 1.26.4 / detector 우회 default):

  cd /workspace/SunityMotion && git pull --ff-only origin main
  python3 -m backend.research.spikes.sweep_rtmpose \\
    --motions ref-climb ref-foxtop-split ref-foxtop ref-invert ref-sideway-spin \\
    --bucket sunity-motion-pilot-videos \\
    --rtmpose-config /workspace/rtmpose_weights/rtmpose-l_8xb256-420e_coco-256x192.py \\
    --rtmpose-checkpoint /workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth \\
    --motionbert-root /workspace/MotionBERT \\
    --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin \\
    --score-threshold 0.3 \\
    --det-model none \\
    --out backend/research/spikes/reports/sweep_rtmpose_$(date +%Y%m%d_%H%M).json

예상 소요: 5영상 × ~2분/영상 = ~10분 (lifter 37ms/frame, NLF 665ms/frame).

로컬 실행 금지 — Pod 전용 (mmpose Linux wheel + CUDA GPU 필수).
모듈 import 자체는 로컬에서도 가능 (mmpose/torch 는 run_spike 내부에서 lazy import).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


# ── 상수 ──────────────────────────────────────────────────────────────────────

# Plan 08 5영상 set — Plan 11 sweep 기본 대상.
DEFAULT_MOTIONS: tuple[str, ...] = (
    "ref-climb",
    "ref-foxtop-split",
    "ref-foxtop",
    "ref-invert",
    "ref-sideway-spin",
)

# D-15① overall ≥ 70 영상 수로 verdict 분기.
STRONG_PASS_THRESHOLD = 70.0


# ── argparse parser ───────────────────────────────────────────────────────────


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI argparse parser 빌더 (smoke 테스트 재사용 위해 분리).

    9개 CLI argument 노출 (Plan 11 T-1-5 명시):
      --motions, --bucket, --rtmpose-config, --rtmpose-checkpoint,
      --motionbert-root, --motionbert-weights, --score-threshold,
      --det-model, --out
    """
    parser = argparse.ArgumentParser(
        description=(
            "RTMPose + MotionBERT 5영상 sweep (Plan 01-11). "
            "Plan 10 spike_rtmpose 단일 영상 logic 을 list 로 wrapping."
        )
    )
    parser.add_argument(
        "--motions",
        nargs="+",
        default=list(DEFAULT_MOTIONS),
        help=(
            "분석할 motion_id 리스트 (S3 reference/{motion}.mp4). "
            f"기본: {' '.join(DEFAULT_MOTIONS)} (Plan 08 5영상 set)."
        ),
    )
    parser.add_argument(
        "--bucket",
        default="sunity-motion-pilot-videos",
        help="S3 버킷 이름 (기본: sunity-motion-pilot-videos)",
    )
    parser.add_argument(
        "--rtmpose-config",
        required=False,
        default=None,
        help="RTMPose config (.py) 파일 경로. Pod 실행 시 필수.",
    )
    parser.add_argument(
        "--rtmpose-checkpoint",
        required=False,
        default=None,
        help="RTMPose pretrained 가중치 (.pth) 경로. Pod 실행 시 필수.",
    )
    parser.add_argument(
        "--motionbert-root",
        default="/workspace/MotionBERT",
        help="MotionBERT 저장소 루트 (기본: /workspace/MotionBERT)",
    )
    parser.add_argument(
        "--motionbert-weights",
        default=None,
        help=(
            "MotionBERT 가중치 경로. None 이면 "
            "{root}/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin"
        ),
    )
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=0.3,
        help="RTMPose keypoint score 임계값 (기본 0.3, Plan 10 과 동일).",
    )
    parser.add_argument(
        "--det-model",
        default="none",
        help=(
            "사람 detector. 'none' (기본) = single-person 우회 모드 "
            "(Plan 10 commit f019070). 또는 mmpose alias / mmdet config 경로."
        ),
    )
    parser.add_argument(
        "--out",
        default=None,
        help=(
            "JSON 결과 저장 경로. None 이면 "
            "backend/research/spikes/reports/sweep_rtmpose_<UTC>.json 자동 생성."
        ),
    )
    return parser


# ── sweep 실행 ───────────────────────────────────────────────────────────────


def _default_out_path() -> Path:
    """기본 출력 경로 (UTC timestamp)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return Path("backend/research/spikes/reports") / f"sweep_rtmpose_{ts}.json"


def _extract_per_motion(motion: str, spike_result: dict) -> dict[str, Any]:
    """단일 영상 spike 결과 → sweep 집계용 dict.

    Plan 11 T-1-2 요구 필드:
      overall, stability, line, angle, avg_score, ms_per_frame,
      nlf_overall, nlf_stability, nlf_line, nlf_angle, gap_overall
    """
    lifter = spike_result.get("lifter", {}) or {}
    nlf = spike_result.get("nlf", {}) or {}
    gap = spike_result.get("gap", {}) or {}
    lifter_dims = lifter.get("dimensions", {}) or {}
    nlf_dims = nlf.get("dimensions", {}) or {}

    return {
        "motion": motion,
        "rtmpose_mb": {
            "overall": lifter.get("overall"),
            "stability": lifter_dims.get("stability"),
            "line": lifter_dims.get("line"),
            "angle": lifter_dims.get("angle"),
            "ms_per_frame": lifter.get("ms_per_frame"),
            "avg_score": lifter.get("avg_rtm_score"),
        },
        "nlf": {
            "overall": nlf.get("overall"),
            "stability": nlf_dims.get("stability"),
            "line": nlf_dims.get("line"),
            "angle": nlf_dims.get("angle"),
            "ms_per_frame": nlf.get("ms_per_frame"),
        },
        "gap": {
            "overall": gap.get("overall"),
        },
        "verdict": spike_result.get("verdict"),
        "frames_total": spike_result.get("frames_total"),
    }


def _verdict_from_counts(passed: int, total: int) -> str:
    """D-15① ≥70 영상 수 → sweep verdict label."""
    if passed == total and total >= 1:
        return f"{passed}/{total} STRONG_PASS"
    if passed == total - 1 and total >= 2:
        return f"{passed}/{total} CONDITIONAL_PASS"
    if passed >= 1:
        return f"{passed}/{total} REGRESSION"
    return f"{passed}/{total} FAIL"


def run_sweep(
    motions: list[str],
    bucket: str,
    rtmpose_config: str | None,
    rtmpose_checkpoint: str | None,
    motionbert_root: str,
    motionbert_weights: str | None,
    score_threshold: float = 0.3,
    det_model: str = "none",
    out: str | Path | None = None,
    spike_fn: Callable[..., dict] | None = None,
) -> dict[str, Any]:
    """5영상 sweep 실행.

    Args:
        motions: 분석할 motion_id 리스트.
        bucket: S3 버킷.
        rtmpose_config / rtmpose_checkpoint: RTMPose config + 가중치 경로 (Pod 필수).
        motionbert_root / motionbert_weights: MotionBERT 경로.
        score_threshold: RTMPose keypoint score 컷.
        det_model: detector alias 또는 "none" (single-person 우회).
        out: 결과 저장 경로 (.json + .md sibling). None 이면 UTC timestamp 로 생성.
        spike_fn: 영상 단위 spike 함수 — 테스트에서 monkeypatch 가능.
                  None 이면 spike_rtmpose.run_spike 를 lazy import.

    Returns:
        sweep summary dict — JSON 으로 dump 된 것과 동일 형식.
    """
    if not motions:
        raise ValueError("motions 리스트는 비어있을 수 없습니다.")

    if spike_fn is None:
        # lazy import — mmpose/torch 가 모듈 로드 시점에 들어오지 않도록 함.
        from .spike_rtmpose import run_spike as spike_fn  # noqa: PLC0415

    generated_at = datetime.now(timezone.utc).isoformat()
    log.info("=== sweep_rtmpose start motions=%s ===", motions)

    per_motion_results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for motion in motions:
        log.info("--- sweep [%s] start ---", motion)
        try:
            spike_result = spike_fn(
                motion=motion,
                bucket=bucket,
                rtmpose_config=rtmpose_config,
                rtmpose_checkpoint=rtmpose_checkpoint,
                motionbert_root=motionbert_root,
                motionbert_weights=motionbert_weights,
                video_path=None,
                det_model=det_model,
                score_threshold=score_threshold,
                out=None,  # 영상별 JSON dump 는 sweep 가 통합 dump 로 대체.
            )
        except Exception as exc:  # noqa: BLE001 — 영상 단위 실패는 sweep 계속
            log.exception("[%s] spike 실행 실패", motion)
            per_motion_results.append({
                "motion": motion,
                "error": f"{type(exc).__name__}: {exc}",
                "rtmpose_mb": None,
                "nlf": None,
                "gap": None,
                "verdict": "error",
            })
            failures.append({"motion": motion, "error": str(exc)})
            continue

        per_motion_results.append(_extract_per_motion(motion, spike_result))
        log.info("--- sweep [%s] done ---", motion)

    # 게이트 verdict 자동 계산 (D-15① ≥70 기준)
    total = len(motions)
    passed = 0
    for entry in per_motion_results:
        rmb = entry.get("rtmpose_mb") or {}
        overall = rmb.get("overall")
        if overall is not None and overall >= STRONG_PASS_THRESHOLD:
            passed += 1
    verdict = _verdict_from_counts(passed, total)

    # line / angle N/A 개수 (Phase 5 우선순위 판단용)
    line_na = sum(
        1 for e in per_motion_results
        if (e.get("rtmpose_mb") or {}).get("line") is None
    )
    angle_na = sum(
        1 for e in per_motion_results
        if (e.get("rtmpose_mb") or {}).get("angle") is None
    )

    summary = {
        "total": total,
        "passed": passed,
        "verdict": verdict,
        "line_na_count": line_na,
        "angle_na_count": angle_na,
        "strong_pass_threshold": STRONG_PASS_THRESHOLD,
        "failures": failures,
    }

    sweep_result = {
        "generated_at": generated_at,
        "detector": "rtmpose-l",
        "lifter": "motionbert_lite",
        "score_threshold": score_threshold,
        "det_model": det_model,
        "rtmpose_config": rtmpose_config,
        "rtmpose_checkpoint": rtmpose_checkpoint,
        "motionbert_root": motionbert_root,
        "motionbert_weights": motionbert_weights,
        "motions": per_motion_results,
        "summary": summary,
    }

    # JSON + Markdown dump
    out_path = Path(out) if out is not None else _default_out_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sweep_result, f, ensure_ascii=False, indent=2)
    log.info("JSON 결과: %s", out_path)

    md_path = out_path.with_suffix(".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(generate_markdown(sweep_result))
    log.info("Markdown 결과: %s", md_path)

    _print_summary(sweep_result)
    return sweep_result


# ── Markdown 출력 ────────────────────────────────────────────────────────────


def _fmt(v: Any) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, (int, float)):
        return f"{float(v):.1f}"
    return str(v)


def generate_markdown(sweep_result: dict) -> str:
    """5영상 sweep 결과 → Markdown 보고서.

    포맷 (Plan 11 T-1-3):
      | 모션 | RTMPose+MB | NLF | gap | D-15① ≥70 | line | angle |
    """
    summary = sweep_result.get("summary", {}) or {}
    motions = sweep_result.get("motions", []) or []

    lines = [
        "# Sweep: RTMPose + MotionBERT 5영상 회귀 (Plan 01-11)",
        "",
        f"생성: {sweep_result.get('generated_at', 'N/A')}",
        f"detector: `{sweep_result.get('detector', 'N/A')}` "
        f"(det_model=`{sweep_result.get('det_model', 'N/A')}`)",
        f"lifter: `{sweep_result.get('lifter', 'N/A')}`",
        f"score_threshold: {sweep_result.get('score_threshold', 'N/A')}",
        "",
        "## 5영상 종합표",
        "",
        "| 모션 | RTMPose+MB | NLF | gap | D-15① ≥70 | line | angle |",
        "|---|---|---|---|---|---|---|",
    ]

    for entry in motions:
        motion = entry.get("motion", "?")
        if entry.get("error"):
            lines.append(
                f"| {motion} | ERROR | — | — | — | — | — |"
            )
            continue
        rmb = entry.get("rtmpose_mb") or {}
        nlf = entry.get("nlf") or {}
        gap = entry.get("gap") or {}
        overall = rmb.get("overall")
        d15_pass = "PASS" if (overall is not None and overall >= STRONG_PASS_THRESHOLD) else "FAIL"
        lines.append(
            f"| {motion} | {_fmt(overall)} | {_fmt(nlf.get('overall'))} | "
            f"{_fmt(gap.get('overall'))} | {d15_pass} | "
            f"{_fmt(rmb.get('line'))} | {_fmt(rmb.get('angle'))} |"
        )

    lines += [
        "",
        "## 차원 상세",
        "",
        "| 모션 | overall | stability | line | angle | avg_score | ms/frame |",
        "|---|---|---|---|---|---|---|",
    ]
    for entry in motions:
        motion = entry.get("motion", "?")
        if entry.get("error"):
            lines.append(f"| {motion} | ERROR | — | — | — | — | — |")
            continue
        rmb = entry.get("rtmpose_mb") or {}
        lines.append(
            f"| {motion} | {_fmt(rmb.get('overall'))} | "
            f"{_fmt(rmb.get('stability'))} | {_fmt(rmb.get('line'))} | "
            f"{_fmt(rmb.get('angle'))} | {_fmt(rmb.get('avg_score'))} | "
            f"{_fmt(rmb.get('ms_per_frame'))} |"
        )

    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    verdict = summary.get("verdict", "unknown")
    line_na = summary.get("line_na_count", 0)
    angle_na = summary.get("angle_na_count", 0)

    lines += [
        "",
        "## 게이트 verdict",
        "",
        f"- D-15① overall ≥ {STRONG_PASS_THRESHOLD} 통과: **{passed} / {total}**",
        f"- 자동 분류: **{verdict}**",
        f"- line N/A 영상: {line_na} / {total}",
        f"- angle N/A 영상: {angle_na} / {total}",
        "",
        "## 분류 기준 (Plan 11 T-1-4)",
        "",
        "| 결과 | passed/total | belle 응답 | 다음 행동 |",
        "|---|---|---|---|",
        "| Strong pass | 5/5 | `approved, proceed to Wave 3` | Plan 04 / Plan 05 진입 |",
        "| Conditional pass | 4/5 | `accept limitation, proceed to Wave 3 with known gap` "
        "| Plan 04/05 진입 + Phase 5 우선순위 ↑ |",
        "| Regression | 3/5 이하 | `regression in RTMPose, evaluate path` "
        "| Plan 12 추가 검토 (HybrIK 또는 MP+MB 유지) |",
        "| line/angle 전부 N/A 차단 | — | `Wave 3 보류, Phase 5 선행` | Phase 5 Gemini 통합 우선 |",
        "",
    ]

    failures = summary.get("failures") or []
    if failures:
        lines += ["## 실패 영상", ""]
        for fail in failures:
            lines.append(f"- `{fail.get('motion')}`: {fail.get('error')}")
        lines.append("")

    return "\n".join(lines) + "\n"


def _print_summary(sweep_result: dict) -> None:
    """stdout 5영상 표 + verdict 출력."""
    summary = sweep_result.get("summary", {}) or {}
    motions = sweep_result.get("motions", []) or []

    print()
    print("=== sweep_rtmpose 결과 ===")
    print(f"  detector: rtmpose-l (det_model={sweep_result.get('det_model')})")
    print(f"  영상 수: {summary.get('total', 0)}")
    print()
    print(
        f"  {'모션':<22}  {'RTMPose+MB':>11}  {'NLF':>8}  "
        f"{'gap':>6}  {'D-15①':>7}  {'line':>6}  {'angle':>6}"
    )
    print(
        f"  {'-'*22}  {'-'*11}  {'-'*8}  {'-'*6}  "
        f"{'-'*7}  {'-'*6}  {'-'*6}"
    )
    for entry in motions:
        motion = entry.get("motion", "?")
        if entry.get("error"):
            print(f"  {motion:<22}  {'ERROR':>11}  {'—':>8}  {'—':>6}  {'—':>7}  {'—':>6}  {'—':>6}")
            continue
        rmb = entry.get("rtmpose_mb") or {}
        nlf = entry.get("nlf") or {}
        gap = entry.get("gap") or {}
        overall = rmb.get("overall")
        d15_pass = "PASS" if (overall is not None and overall >= STRONG_PASS_THRESHOLD) else "FAIL"
        print(
            f"  {motion:<22}  {_fmt(overall):>11}  {_fmt(nlf.get('overall')):>8}  "
            f"{_fmt(gap.get('overall')):>6}  {d15_pass:>7}  "
            f"{_fmt(rmb.get('line')):>6}  {_fmt(rmb.get('angle')):>6}"
        )

    print()
    print(f"  passed: {summary.get('passed', 0)} / {summary.get('total', 0)}")
    print(f"  verdict: {summary.get('verdict', 'unknown')}")
    print(
        f"  line N/A: {summary.get('line_na_count', 0)} / {summary.get('total', 0)}  "
        f"angle N/A: {summary.get('angle_na_count', 0)} / {summary.get('total', 0)}"
    )
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI 진입점."""
    parser = build_arg_parser()
    args = parser.parse_args()

    run_sweep(
        motions=args.motions,
        bucket=args.bucket,
        rtmpose_config=args.rtmpose_config,
        rtmpose_checkpoint=args.rtmpose_checkpoint,
        motionbert_root=args.motionbert_root,
        motionbert_weights=args.motionbert_weights,
        score_threshold=args.score_threshold,
        det_model=args.det_model,
        out=args.out,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    main()
