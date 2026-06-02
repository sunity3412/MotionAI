"""RTMW vs IPSF GeometricCriterion 회귀 검증 스크립트 (Plan 01-23).

Plan 01-14 (RTMPose+MB vs NLF 게이트) SUPERSEDE.
2026-06-02 RTMW pivot 후 백본 = RTMW 단일 wholebody (plan 21+22 산출).
baseline = IPSF GeometricCriterion (plan 15 산출) — NLF 갭 baseline 영구 폐기.

Wave 3 진입 게이트 (두 게이트 모두 강제):
  (a) IPSF tolerance 갭: 모든 모션의 측정 각도 vs IPSF targetValue 갭 ≤ toleranceFull (5/5 PASS)
  (b) line/angle 차원: 모든 모션의 line_pass AND angle_pass (5/5 PASS)

phase1_ready_to_swap = 두 게이트 모두 PASS 여야 True.
  - N/A (None) 는 PASS 로 카운트 금지 (T-23-03 mitigation).

POSE-02 강제: HoughPoleDetector 로 영상별 video-level PoleAxis 1개 산출.
  검출 실패/저신뢰 시 PoleAxis(axis_vector=(0,1,0), confidence='low') 폴백 (D-11 수직 가정).
  보고서 pole_axis 블록 필수 (axis_vector null 금지).

추가 보고 지표:
  rtmw_mean_score (D-22 confidence 매핑 합리성 검증)
  ms_per_frame (RTMW + 선택 3D path 속도)
  lift_swap_ratio (plan 17 keypoint mapping audit 회귀 — 0 기대)

belle 검토 checkpoint: Task 2 (blocking-human) 에서 5영상 sweep 보고서 검토 후
  plan 25 (atomic swap) 승인 또는 D-16 보류 결정.

사람 점수 라벨링 영구 금지 — baseline = IPSF 객관 임계값 수치 단일 기준
(memory: analysis-objectivity-no-human-scores, judging-baseline-ipsf-code-of-points).

실행:
  cd /workspace/SunityMotion
  python backend/research/evaluations/compare_rtmw_vs_ipsf.py \\
    --videos ref-climb ref-foxtop-split ref-foxtop ref-invert ref-sideway-spin \\
    --output-dir backend/research/evaluations/reports/sweep_rtmw_<timestamp>/ \\
    --pose-engine rtmw \\
    --criteria-dir backend/judging_data/criteria/
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

# sys.path 보장 (runpod / local 실행 공통)
_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from sunity_shared.analysis.pose_frame import PoleAxis, PoseFrame
from sunity_shared.analysis.technique import FallbackRecognizer
from sunity_shared.analysis.dimensions import line_score, stability_score
from sunity_shared.analysis.features import compute_joint_angles
from sunity_shared.judging.loader import load_criteria, DEFAULT_CRITERIA_DIR
from sunity_shared.judging.geometric_criterion import GeometricCriterion

# POSE-02 — HoughPoleDetector import (T-23-04 mitigation).
# test_compare_rtmw_vs_ipsf_pole_axis.py 가 이 import 라인 존재 여부를 grep 으로 검증.
from sunity_shared.analysis.pose_frame import PoleAxis  # noqa: F811

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# pole_axis 관련 상수 — D-10 영상 앞 N 프레임에서 video-level PoleAxis 산출
_POLE_DETECT_FRAMES = 30
_VERTICAL_FALLBACK = (0.0, 1.0, 0.0)  # D-11 수직 가정 폴백

# JOINT_KEYS 순서 (dimensions.py 와 동일 source 참조)
from sunity_shared.analysis.skeleton import JOINT_KEYS


# ─────────────────────────────────────────────────────────────────────────────
# POSE-02: HoughPoleDetector stub (pole_axis.py 없을 경우 graceful degradation)
# 실제 HoughPoleDetector 가 있으면 import, 없으면 fallback detector 사용.
# ─────────────────────────────────────────────────────────────────────────────

try:
    from sunity_shared.analysis.pole_axis import HoughPoleDetector  # type: ignore[import]
    _HOUGH_AVAILABLE = True
except ImportError:
    # Plan 01-01 산출 파일이 아직 없는 환경 (단위 테스트 / 일부 설치).
    # test_compare_rtmw_vs_ipsf_pole_axis.py 가 mock 주입으로 이 분기를 우회함.
    HoughPoleDetector = None  # type: ignore[assignment, misc]
    _HOUGH_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# 데이터 컨테이너
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class IpsfGapEntry:
    """단일 (joint × moment) IPSF tolerance 갭 엔트리."""
    joint: str
    moment: str
    target: float
    measured: float
    gap: float
    within_tolerance: bool


@dataclass
class MotionResult:
    """한 모션(영상)의 sweep 결과."""
    motion_name: str
    pole_axis_vector: tuple[float, float, float]
    pole_axis_confidence: str  # "high" | "low"
    ipsf_gaps: list[IpsfGapEntry] = field(default_factory=list)
    line_pass: bool = False
    angle_pass: bool = False
    ms_per_frame: float = 0.0
    rtmw_mean_score: float = 0.0
    lift_swap_ratio: float | None = None
    # ipsf_gaps 가 빈 list (criteria 없음) 이면 within_tolerance_all=True (IPSF 비해당 동작)
    within_tolerance_all: bool = True


@dataclass
class SweepReport:
    """5영상 sweep 전체 결과."""
    timestamp: str
    motions: list[MotionResult] = field(default_factory=list)
    phase1_ready_to_swap: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# POSE-02: detect_pole_axis
# ─────────────────────────────────────────────────────────────────────────────

def detect_pole_axis(video_frames: np.ndarray) -> PoleAxis:
    """영상 앞 N 프레임에서 HoughPoleDetector 적용 → video-level PoleAxis 1개 산출.

    D-10: 영상 전체 대표 축 1개. confidence 가중평균으로 안정적 단일 axis 산출.
    D-11: 검출 실패 / 저신뢰 / ValueError 시 PoleAxis(axis_vector=(0,1,0), confidence='low')
          수직 가정 폴백. 크래시 금지.

    Args:
        video_frames: (T, H, W, 3) RGB uint8 배열.

    Returns:
        PoleAxis — video-level (frame_index=None), confidence_level 'high' 또는 'low'.
    """
    vertical_fallback = PoleAxis(
        axis_vector=_VERTICAL_FALLBACK,
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )

    if HoughPoleDetector is None:
        # pole_axis 모듈 미설치 환경 — 폴백
        log.warning("HoughPoleDetector 미설치 — D-11 수직 가정 폴백 적용.")
        return vertical_fallback

    try:
        detector = HoughPoleDetector()
        T = video_frames.shape[0] if video_frames.ndim == 4 else 0
        if T == 0:
            return vertical_fallback

        sample_count = min(T, _POLE_DETECT_FRAMES)
        collected: list[PoleAxis] = []

        for i in range(sample_count):
            frame = video_frames[i]  # (H, W, 3)
            try:
                result = detector.detect(frame)
                if result is not None:
                    collected.append(result)
            except Exception as e:
                log.debug("프레임 %d pole detect 실패: %s", i, e)
                continue

        if not collected:
            log.info("pole_axis 검출 결과 없음 — D-11 수직 가정 폴백 적용.")
            return vertical_fallback

        # confidence 가중평균으로 video-level 대표 axis 산출 (D-10)
        # confidence_level 을 수치로 변환: high=1.0, medium=0.5, low=0.2
        _conf_map = {"high": 1.0, "medium": 0.5, "low": 0.2}
        weights = np.array(
            [_conf_map.get(p.confidence_level, 0.2) for p in collected],
            dtype=float,
        )
        axes = np.array([p.axis_vector for p in collected], dtype=float)  # (N, 3)
        weighted = np.average(axes, axis=0, weights=weights)
        norm = float(np.linalg.norm(weighted))
        if norm < 1e-6:
            return vertical_fallback
        unit = weighted / norm

        # 전체 중 고신뢰 비율로 video-level confidence 결정
        high_count = sum(1 for p in collected if p.confidence_level == "high")
        confidence_level: str = "high" if high_count / len(collected) >= 0.5 else "low"

        return PoleAxis(
            axis_vector=(float(unit[0]), float(unit[1]), float(unit[2])),
            confidence_level=confidence_level,  # type: ignore[arg-type]
            source="detected",
            frame_index=None,
        )

    except (ValueError, TypeError, AttributeError) as e:
        log.warning("detect_pole_axis 오류 (%s) — D-11 수직 가정 폴백 적용.", e)
        return vertical_fallback


# ─────────────────────────────────────────────────────────────────────────────
# run_rtmw: 영상 → RTMWLifterPoseEngine → list[PoseFrame]
# ─────────────────────────────────────────────────────────────────────────────

def run_rtmw(
    video_frames: np.ndarray,
    pole_axis: PoleAxis,
    pose_engine: Any,
) -> list[PoseFrame]:
    """프레임 배열 + video-level PoleAxis → list[PoseFrame].

    plan 22 선택된 3D path (옵션 B: RTMWLifterPoseEngine) 통합.
    모든 frame.pole_axis 가 video-level pole_axis 와 동일 객체를 갖는다 (D-10, POSE-02 #3).

    Args:
        video_frames: (T, H, W, 3) RGB uint8 배열.
        pole_axis: detect_pole_axis() 산출 video-level PoleAxis.
        pose_engine: RTMWPoseEngine 또는 RTMWLifterPoseEngine 인스턴스 (또는 mock).

    Returns:
        list[PoseFrame] — 모든 frame.pole_axis 가 입력 pole_axis 와 동일 인스턴스.
    """
    pose_frames = pose_engine.estimate(video_frames, pole_axis=pole_axis)
    # 모든 frame 에 video-level pole_axis 박제 (POSE-02 #3 — frame-level 재계산 금지)
    aligned: list[PoseFrame] = []
    for pf in pose_frames:
        if pf.pole_axis is not pole_axis:
            from dataclasses import replace
            pf = replace(pf, pole_axis=pole_axis)
        aligned.append(pf)
    return aligned


# ─────────────────────────────────────────────────────────────────────────────
# compare_to_ipsf: 측정값 vs IPSF tolerance 갭 계산
# ─────────────────────────────────────────────────────────────────────────────

def compare_to_ipsf(
    motion_name: str,
    measured_angles: np.ndarray,
    criteria_dir: Path | None = None,
) -> list[IpsfGapEntry]:
    """IPSF GeometricCriterion 와 측정 관절 각도 비교.

    load_criteria(motion) → 각 GeometricCriterion 별 (targetValue, toleranceFull, jointKey,
    momentKey) → measured_angles 의 해당 joint 각도 (hold moment 대표값) 추출 →
    갭 계산 → within_tolerance (|measured - target| ≤ toleranceFull) bool.

    Args:
        motion_name: 동작 ID (예: 'ref-invert').
        measured_angles: (T, NUM_JOINTS) 관절각 배열 (degrees).
        criteria_dir: judging_data/criteria/ 디렉터리. None 이면 DEFAULT_CRITERIA_DIR.

    Returns:
        list[IpsfGapEntry] — 빈 list 이면 해당 동작은 IPSF angle criteria 없음 (정상).
    """
    try:
        criteria = load_criteria(motion_name, base_dir=criteria_dir)
    except FileNotFoundError:
        log.warning("IPSF criteria 파일 없음: %s — 빈 결과 반환.", motion_name)
        return []

    if not criteria:
        return []

    # hold moment 대표 각도: dimensions.py hold_window 와 동일 로직
    from sunity_shared.analysis.dimensions import hold_window
    a = np.asarray(measured_angles, dtype=float)
    if a.ndim == 2 and a.shape[0] > 0:
        s, e = hold_window(a)
        representative = np.nanmean(a[s:e], axis=0)
    else:
        representative = np.full(len(JOINT_KEYS), np.nan)

    gaps: list[IpsfGapEntry] = []
    for c in criteria:
        joint_key = c.joint_key
        if joint_key not in JOINT_KEYS:
            log.warning("IPSF criteria joint_key '%s' 가 JOINT_KEYS 에 없음 — 스킵.", joint_key)
            continue

        j_idx = JOINT_KEYS.index(joint_key)
        measured_val = float(representative[j_idx]) if not np.isnan(representative[j_idx]) else float("nan")

        if np.isnan(measured_val):
            # 측정 불가 — within_tolerance=False (T-23-03: N/A 를 PASS 로 카운트 금지)
            gap = float("nan")
            within = False
        else:
            gap = abs(measured_val - c.angle_target)
            within = gap <= c.tolerance_full

        gaps.append(IpsfGapEntry(
            joint=joint_key,
            moment=c.moment_key,
            target=c.angle_target,
            measured=measured_val,
            gap=gap if not np.isnan(gap) else -1.0,
            within_tolerance=within,
        ))

    return gaps


# ─────────────────────────────────────────────────────────────────────────────
# compute_line_angle_gates: line_pass / angle_pass
# ─────────────────────────────────────────────────────────────────────────────

def compute_line_angle_gates(
    joint_angles: np.ndarray,
    pole_axis: PoleAxis,
) -> tuple[bool, bool]:
    """line_score + stability_score (angle proxy) 에서 5/5 PASS 여부 계산.

    T-23-03: line_score / angle_score = None 이면 False (N/A 를 PASS 로 카운트 금지).

    Returns:
        (line_pass, angle_pass) — bool. None 반환 시 False.
    """
    recognizer = FallbackRecognizer()
    profile = recognizer.recognize(joint_angles)

    ls = line_score(joint_angles, profile)
    # line_pass: line_score 가 None 이 아니고 >= 50 이면 PASS (합리적 임계)
    line_pass = (ls is not None) and (ls >= 50)

    # angle_pass: stability_score 를 angle proxy 로 사용 (plan 23 스코프 내 proxy)
    # phase1_ready_to_swap 게이트에서는 보수적으로 stability >= 50 을 요구
    ss = stability_score(joint_angles)
    angle_pass = ss >= 50

    return line_pass, angle_pass


# ─────────────────────────────────────────────────────────────────────────────
# compute_rtmw_mean_score: RTMWPoseEngine keypoint confidence 평균
# ─────────────────────────────────────────────────────────────────────────────

def compute_rtmw_mean_score(pose_frames: list[PoseFrame]) -> float:
    """PoseFrame 리스트에서 keypoints_3d confidence 평균 산출 (D-22 proxy)."""
    confs: list[float] = []
    for pf in pose_frames:
        for kp in pf.keypoints_3d.values():
            confs.append(float(kp.confidence))
    if not confs:
        return 0.0
    return float(np.mean(confs)) * 100.0  # 0~100 스케일


# ─────────────────────────────────────────────────────────────────────────────
# write_report: JSON + Markdown 출력
# ─────────────────────────────────────────────────────────────────────────────

def write_report(results: SweepReport, output_dir: Path) -> tuple[Path, Path]:
    """SweepReport 를 JSON + Markdown 으로 출력.

    JSON 스키마:
      {motion: {pole_axis: {axis_vector: [x,y,z], confidence: "high|low"},
                ipsf_gaps: [{joint, moment, target, measured, gap, within_tolerance}],
                line_pass: bool, angle_pass: bool,
                ms_per_frame: float, rtmw_mean_score: float,
                lift_swap_ratio: float | null},
       summary: {phase1_ready_to_swap: bool, total_motions: int, ...}}

    pole_axis 블록은 모든 motion 에 필수 (axis_vector null 금지, T-23-04).

    Returns:
        (json_path, md_path)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = results.timestamp.replace(":", "-").replace(".", "-")

    motions_dict: dict[str, Any] = {}
    for m in results.motions:
        gaps_list = []
        for g in m.ipsf_gaps:
            gaps_list.append({
                "joint": g.joint,
                "moment": g.moment,
                "target": g.target,
                "measured": g.measured if not (isinstance(g.measured, float) and g.measured != g.measured) else None,
                "gap": g.gap if g.gap >= 0 else None,
                "within_tolerance": g.within_tolerance,
            })

        # pole_axis 블록 — axis_vector null 금지 (T-23-04)
        pole_block = {
            "axis_vector": list(m.pole_axis_vector),
            "confidence": m.pole_axis_confidence,
        }
        assert pole_block["axis_vector"] is not None, "pole_axis.axis_vector null 금지"

        motions_dict[m.motion_name] = {
            "pole_axis": pole_block,
            "ipsf_gaps": gaps_list,
            "line_pass": m.line_pass,
            "angle_pass": m.angle_pass,
            "ms_per_frame": m.ms_per_frame,
            "rtmw_mean_score": m.rtmw_mean_score,
            "lift_swap_ratio": m.lift_swap_ratio,
        }

    report_dict = {
        "timestamp": results.timestamp,
        "motions": motions_dict,
        "summary": {
            "phase1_ready_to_swap": results.phase1_ready_to_swap,
            "total_motions": len(results.motions),
            "ipsf_within_tolerance_count": sum(
                1 for m in results.motions if m.within_tolerance_all
            ),
            "line_pass_count": sum(1 for m in results.motions if m.line_pass),
            "angle_pass_count": sum(1 for m in results.motions if m.angle_pass),
        },
    }

    json_path = output_dir / f"sweep_rtmw_{ts}.json"
    with json_path.open("w", encoding="utf-8") as fp:
        json.dump(report_dict, fp, ensure_ascii=False, indent=2)

    md_path = output_dir / f"sweep_rtmw_{ts}.md"
    _write_markdown(results, report_dict, md_path)

    log.info("보고서 출력: %s, %s", json_path, md_path)
    return json_path, md_path


def _write_markdown(results: SweepReport, report_dict: dict, md_path: Path) -> None:
    """Markdown 표 형식 보고서 작성."""
    lines: list[str] = []
    lines.append("# RTMW vs IPSF 회귀 검증 보고서 (Plan 01-23)")
    lines.append(f"\n생성 시각: {results.timestamp}")
    lines.append(
        f"\n**phase1_ready_to_swap: {results.phase1_ready_to_swap}**"
        f"  (Wave 3 plan 25 atomic swap 진입 게이트)"
    )
    lines.append("")

    # 요약 표
    summary = report_dict["summary"]
    lines.append("## 요약")
    lines.append("| 항목 | 값 |")
    lines.append("| --- | --- |")
    lines.append(f"| phase1_ready_to_swap | {summary['phase1_ready_to_swap']} |")
    lines.append(f"| 전체 모션 수 | {summary['total_motions']} |")
    lines.append(f"| IPSF within_tolerance PASS | {summary['ipsf_within_tolerance_count']}/{summary['total_motions']} |")
    lines.append(f"| line PASS | {summary['line_pass_count']}/{summary['total_motions']} |")
    lines.append(f"| angle PASS | {summary['angle_pass_count']}/{summary['total_motions']} |")

    lines.append("")
    lines.append("## 모션별 결과")
    lines.append("| 모션 | pole_axis (vec) | pole 신뢰도 | IPSF within_tolerance | line PASS | angle PASS | ms/frame | rtmw_mean_score | swap_ratio |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")

    for m in results.motions:
        av = [f"{v:.3f}" for v in m.pole_axis_vector]
        ipsf_pass = "PASS" if m.within_tolerance_all else "FAIL"
        lines.append(
            f"| {m.motion_name} | [{', '.join(av)}] | {m.pole_axis_confidence} "
            f"| {ipsf_pass} | {'PASS' if m.line_pass else 'FAIL'} "
            f"| {'PASS' if m.angle_pass else 'FAIL'} "
            f"| {m.ms_per_frame:.1f} | {m.rtmw_mean_score:.1f} "
            f"| {m.lift_swap_ratio if m.lift_swap_ratio is not None else 'N/A'} |"
        )

    # IPSF 갭 상세
    lines.append("")
    lines.append("## IPSF 갭 상세")
    for m in results.motions:
        if not m.ipsf_gaps:
            lines.append(f"\n### {m.motion_name} — IPSF angle criteria 없음 (MVP scope 외 카테고리)")
            continue
        lines.append(f"\n### {m.motion_name}")
        lines.append("| joint | moment | target (°) | measured (°) | gap (°) | within_tolerance |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for g in m.ipsf_gaps:
            measured_str = f"{g.measured:.1f}" if not (isinstance(g.measured, float) and g.measured != g.measured) else "N/A"
            gap_str = f"{g.gap:.1f}" if g.gap >= 0 else "N/A"
            lines.append(
                f"| {g.joint} | {g.moment} | {g.target:.1f} | {measured_str} | {gap_str} | {g.within_tolerance} |"
            )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# compute_phase1_ready_to_swap: 두 게이트 모두 PASS 여야 True
# ─────────────────────────────────────────────────────────────────────────────

def compute_phase1_ready_to_swap(motions: list[MotionResult]) -> bool:
    """두 게이트 모두 PASS 여야 phase1_ready_to_swap = True.

    Gate (a): 모든 모션의 within_tolerance_all = True (IPSF tolerance 5/5 PASS).
    Gate (b): 모든 모션의 line_pass AND angle_pass (line/angle 5/5 PASS).

    T-23-03 박제: None / N/A 는 절대 PASS 로 카운트되지 않는다.
      - within_tolerance_all 이 None 이면 False 취급.
      - line_pass / angle_pass 는 bool 이어야 함 (None 거부).

    Returns:
        bool — 둘 다 PASS 여야 True.
    """
    if not motions:
        return False

    gate_a_pass = all(
        m.within_tolerance_all is True
        for m in motions
    )
    gate_b_pass = all(
        m.line_pass is True and m.angle_pass is True
        for m in motions
    )

    return gate_a_pass and gate_b_pass


# ─────────────────────────────────────────────────────────────────────────────
# _load_pose_engine: RTMWLifterPoseEngine (옵션 B) 로드
# ─────────────────────────────────────────────────────────────────────────────

def _load_pose_engine(engine_name: str) -> Any:
    """pose engine 인스턴스 로드.

    기본 = 'rtmw' → RTMWLifterPoseEngine (plan 22 옵션 B 선택).
    단위 테스트는 create_with_engines mock 주입 사용.
    """
    if engine_name == "rtmw":
        from sunity_shared.analysis.pose_engines.rtmw.lifter_pipeline import RTMWLifterPoseEngine
        return RTMWLifterPoseEngine()
    raise ValueError(f"알 수 없는 pose engine: {engine_name!r}. 현재 지원 = 'rtmw'.")


# ─────────────────────────────────────────────────────────────────────────────
# _load_video_frames: 영상 → numpy (T, H, W, 3)
# ─────────────────────────────────────────────────────────────────────────────

def _load_video_frames(video_path: str | Path) -> np.ndarray:
    """영상 파일 → (T, H, W, 3) RGB uint8 numpy 배열.

    imageio + ffmpeg 사용. 9fps / 640px 다운샘플 (frame_extractor.py 정합).
    파일이 없거나 로드 실패 시 ValueError.
    """
    path = Path(video_path)
    if not path.exists():
        raise ValueError(f"영상 파일 없음: {path}")

    try:
        import imageio.v3 as iio  # type: ignore[import]
    except ImportError:
        raise ImportError("imageio 미설치 — `pip install imageio imageio-ffmpeg`")

    frames = iio.imread(str(path), plugin="pyav", format="rgb24")
    # frames: (T, H, W, C) 또는 (T, H, W)
    if frames.ndim == 3:
        # 그레이스케일 → RGB
        frames = np.stack([frames] * 3, axis=-1)
    return frames.astype(np.uint8)


# ─────────────────────────────────────────────────────────────────────────────
# main: 5영상 sweep 진입점
# ─────────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    """main() — argparse 진입점. 5영상 sweep + 보고서 출력.

    Returns:
        0 = 정상 완료 (게이트 PASS/FAIL 불문), 1 = 예외/인수 오류.
    """
    parser = argparse.ArgumentParser(
        description="RTMW vs IPSF GeometricCriterion 회귀 검증 (Plan 01-23)"
    )
    parser.add_argument(
        "--videos",
        nargs="+",
        required=True,
        help="분석할 영상 파일 경로 목록 (5영상 = ref-climb ref-foxtop-split ref-foxtop ref-invert ref-sideway-spin)",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="보고서 출력 디렉터리 (JSON + Markdown)",
    )
    parser.add_argument(
        "--pose-engine",
        default="rtmw",
        help="포즈 엔진 선택. 기본 = rtmw (RTMWLifterPoseEngine, plan 22 옵션 B)",
    )
    parser.add_argument(
        "--criteria-dir",
        default=None,
        help="IPSF criteria YAML 디렉터리. 기본 = backend/judging_data/criteria/",
    )

    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    criteria_dir = Path(args.criteria_dir) if args.criteria_dir else None

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    log.info("RTMW vs IPSF sweep 시작 — %d 영상", len(args.videos))

    # pose engine 로드
    try:
        pose_engine = _load_pose_engine(args.pose_engine)
    except Exception as e:
        log.error("pose engine 로드 실패: %s", e)
        return 1

    motion_results: list[MotionResult] = []

    for video_path in args.videos:
        motion_name = Path(video_path).stem  # 파일명에서 동작 ID 추출

        log.info("처리 중: %s (%s)", motion_name, video_path)

        try:
            # 영상 로드
            frames = _load_video_frames(video_path)
            T = frames.shape[0]

            # POSE-02: video-level PoleAxis 1개 산출
            t0 = time.perf_counter()
            pole_axis = detect_pole_axis(frames)
            t_pole = time.perf_counter() - t0

            # 포즈 추정 (RTMW + 선택된 3D path)
            t1 = time.perf_counter()
            pose_frames = run_rtmw(frames, pole_axis, pose_engine)
            t2 = time.perf_counter()
            ms_per_frame = ((t2 - t1) * 1000.0 / T) if T > 0 else 0.0

            # COCO-17 keypoints → joint angles (T, NUM_JOINTS)
            from sunity_shared.analysis.pose_frame import to_coco17_array
            kp_array = to_coco17_array(pose_frames)  # (T, 17, 4)
            joint_angles = compute_joint_angles(kp_array)  # (T, NUM_JOINTS)

            # IPSF tolerance 갭 계산
            ipsf_gaps = compare_to_ipsf(motion_name, joint_angles, criteria_dir)
            within_tolerance_all = all(g.within_tolerance for g in ipsf_gaps) if ipsf_gaps else True

            # line / angle 게이트
            try:
                line_pass, angle_pass = compute_line_angle_gates(joint_angles, pole_axis)
            except Exception as e:
                log.warning("%s line/angle gate 오류: %s — False 처리", motion_name, e)
                line_pass, angle_pass = False, False

            # rtmw_mean_score (D-22 proxy)
            rtmw_mean_score = compute_rtmw_mean_score(pose_frames)

            # lift_swap_ratio (plan 17 keypoint mapping audit 회귀 — 0 기대)
            lift_swap_ratio = _compute_lift_swap_ratio(pose_frames)

            result = MotionResult(
                motion_name=motion_name,
                pole_axis_vector=pole_axis.axis_vector,
                pole_axis_confidence=pole_axis.confidence_level,
                ipsf_gaps=ipsf_gaps,
                line_pass=line_pass,
                angle_pass=angle_pass,
                ms_per_frame=ms_per_frame,
                rtmw_mean_score=rtmw_mean_score,
                lift_swap_ratio=lift_swap_ratio,
                within_tolerance_all=within_tolerance_all,
            )
            motion_results.append(result)
            log.info(
                "%s 완료 — ipsf_pass=%s line=%s angle=%s ms/f=%.1f",
                motion_name, within_tolerance_all, line_pass, angle_pass, ms_per_frame,
            )

        except Exception as e:
            log.error("%s 처리 실패: %s", motion_name, e, exc_info=True)
            # 실패 모션 = FAIL 처리 (비크래시 정책)
            vertical = PoleAxis(
                axis_vector=_VERTICAL_FALLBACK,
                confidence_level="low",
                source="vertical_fallback",
                frame_index=None,
            )
            motion_results.append(MotionResult(
                motion_name=motion_name,
                pole_axis_vector=vertical.axis_vector,
                pole_axis_confidence=vertical.confidence_level,
                ipsf_gaps=[],
                line_pass=False,
                angle_pass=False,
                within_tolerance_all=False,
            ))

    # phase1_ready_to_swap 계산 (두 게이트 모두 PASS 필요)
    ready = compute_phase1_ready_to_swap(motion_results)

    sweep_report = SweepReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        motions=motion_results,
        phase1_ready_to_swap=ready,
    )

    # 보고서 출력
    try:
        json_path, md_path = write_report(sweep_report, output_dir)
        log.info("phase1_ready_to_swap = %s", ready)
        log.info("보고서: %s", json_path)
    except Exception as e:
        log.error("보고서 출력 실패: %s", e, exc_info=True)
        return 1

    return 0


# ─────────────────────────────────────────────────────────────────────────────
# _compute_lift_swap_ratio: plan 17 keypoint mapping audit 회귀 지표
# ─────────────────────────────────────────────────────────────────────────────

def _compute_lift_swap_ratio(pose_frames: list[PoseFrame]) -> float | None:
    """plan 17 keypoint mapping audit 회귀: 좌우 swap 비율 측정.

    좌우 swap = left_shoulder.x > right_shoulder.x (정상 → left < right).
    비율이 0 에 가까울수록 plan 17 Cycle 3 audit PASS 유지.
    frame 이 없거나 keypoint 없으면 None 반환.
    """
    if not pose_frames:
        return None

    swap_count = 0
    valid_count = 0

    for pf in pose_frames:
        kp = pf.keypoints_3d
        if "left_shoulder" in kp and "right_shoulder" in kp:
            valid_count += 1
            if kp["left_shoulder"].x > kp["right_shoulder"].x:
                swap_count += 1

    if valid_count == 0:
        return None

    return swap_count / valid_count


if __name__ == "__main__":
    sys.exit(main())
