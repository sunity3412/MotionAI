"""갭 root cause 디버그 spike (Plan 01-12).

Plan 11 sweep verdict `gap_too_wide_blocked` 후속 — Plan 11 5영상 sweep 에서
영상별 갭 (RTMPose+MB - NLF) 의 방향+크기가 영상마다 다름 (+31, +16, +17, +5, -1).
단일 요인으로 설명 불가 → 5개 가설 frame-level trace 로 dominant 원인 박제.

Plan 11 vs Plan 12 역할 분리:
  - Plan 11 debug_dimensions: line/angle 차원 N/A 원인 (FallbackRecognizer 한계)
  - Plan 12 본 모듈: 갭 자체 (overall 점수 차이) 의 원인 5개 가설 trace

5개 가설 정의 (Plan 12 PLAN <context> 표):

  (a) Frame-mean 한계 — overall 이 frame 평균이라 두 엔진이 "같은 의미있는
      시점" 을 보지 않음. live mode 에서 두 (T, J) 행렬 frame별 차이 dump.

  (b) RTMPose headdown/거꾸로 자세 약점 — COCO 학습 분포 부족. ref-invert
      22점 회귀와 직접 연관. live mode 에서 frame-by-frame avg_rtm_score
      분포 + headdown frame 식별 + 그 구간 score 분포.

  (c) NLF baseline 영상별 편차 — NLF 점수가 ref-climb 58, ref-sideway-spin
      81 으로 23점 차이. report-only mode 에서 sweep_report JSON 으로
      nlf_overall_range / nlf_dim_variance 계산. live 시 NaN rate 추가.

  (d) RTMPose ↔ NLF keypoint 매핑 차이 — rtmpose_to_h36m17 derive (hip/
      spine/thorax/neck_nose/head 보간) vs NLF skeleton 의 같은 17 joint
      정의가 다름. 로컬 (Pod 의존 X) — 두 chain 정의 비교.

  (e) 두 엔진 3D pose 분포 차이 — RTMPose+MB 의 3D xyz vs NLF 의 3D xyz
      가 같은 frame 에서 다름. live mode 에서 root-relative 17 joint
      Euclidean distance.

mode 분리:
  - report-only: (c) 부분 + (d) 전체 + spike_vs_sweep — Pod 의존 X
  - live: (a)(b)(c)(e) frame-level — Pod 영상 처리 필요

본 모듈은 mmpose / torch / NLF 를 모듈 로드 시점에 import 하지 않는다 —
live mode 진입 시 helper 내부에서 lazy import. report-only 와 모든 테스트는
mmpose 없이 로컬 실행 가능.

Plan 12 scope_limits:
  - 운영 코드 무수정 (functions/, runpod_inference/, shared/pose_lifters,
    dimensions.py, technique.py)
  - 기존 spike (spike_rtmpose, sweep_rtmpose, debug_dimensions,
    rtmpose_to_h36m17) 무수정 — append-only.
  - mmpose / numpy 추가 install 금지.
  - HybrIK / Gemini API / AlphaPose 도입 금지.
  - 실제 fix 는 Plan 13/14 책임 — 본 모듈은 trace + verdict 박제만.

실행 (report-only mode, 로컬 OK):

  python3 -m backend.research.spikes.debug_gap_root_cause \\
    --mode report-only \\
    --sweep-report backend/research/spikes/reports/sweep_rtmpose_20260601_0411.json \\
    --spike-report backend/research/spikes/reports/spike_rtmpose_20260601_0223.json \\
    --out backend/research/spikes/reports/debug_gap_$(date +%Y%m%d_%H%M).json

실행 (live mode, belle Pod 전용):

  python3 -m backend.research.spikes.debug_gap_root_cause \\
    --mode live \\
    --motions ref-invert ref-sideway-spin \\
    --bucket sunity-motion-pilot-videos \\
    --rtmpose-config /workspace/rtmpose_weights/rtmpose-l_8xb256-420e_coco-256x192.py \\
    --rtmpose-checkpoint /workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth \\
    --motionbert-root /workspace/MotionBERT \\
    --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin \\
    --sweep-report backend/research/spikes/reports/sweep_rtmpose_20260601_0411.json \\
    --out backend/research/spikes/reports/debug_gap_live_$(date +%Y%m%d_%H%M).json
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

import numpy as np

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


# ── 상수: 가설 verdict 임계 (rationale 주석 포함) ─────────────────────────────

# 가설 (a): frame-mean 한계 — frame별 mean joint angle 차이 평균값 기준.
# 두 엔진이 같은 자세를 보면 평균 5° 이내, 30° 이상이면 frame-mean averaging
# 으로 점수가 다르게 나옴이 확실. NLF/RTMPose+MB 모두 동일 frame 의 같은
# 자세를 본다는 가정 하 평균 disagreement 가 크면 (a) strong.
HYPOTHESIS_A_STRONG_DEG = 20.0
HYPOTHESIS_A_WEAK_DEG = 8.0

# 가설 (b): RTMPose headdown 약점 — headdown 구간 평균 keypoint score 가
# 전체 평균보다 0.1 이상 낮으면 strong. Plan 10 avg_rtm_score 0.4382 baseline
# 대비 headdown 구간이 0.3 이하면 명확한 약점.
HYPOTHESIS_B_HEADDOWN_SCORE_DROP = 0.10
HYPOTHESIS_B_STRONG_HEADDOWN_SCORE = 0.30

# 가설 (c): NLF baseline 영상별 편차 — Plan 11 sweep 실데이터 ref-climb 58,
# ref-sideway-spin 81 차이 23 → strong 임계 20. 같은 score function 인데
# 영상마다 20점 이상 다르면 NLF 자체 영상별 편차 존재.
HYPOTHESIS_C_STRONG_OVERALL_RANGE = 20.0
HYPOTHESIS_C_WEAK_OVERALL_RANGE = 10.0

# 가설 (d): keypoint 매핑 차이 — JOINT_KEYS / 정의 chain 자체가 다르면 strong.
# 두 chain 모두 8 joint angle 만 비교하므로 angle 정의 mismatch 가 있으면
# strong (구조적 차이).

# 가설 (e): 두 엔진 3D pose 분포 차이 — root-relative Euclidean distance
# 평균. 0.3 (정규화 단위) 이상이면 strong, 0.15 이하이면 두 path 거의 일치.
HYPOTHESIS_E_STRONG_DISTANCE = 0.30
HYPOTHESIS_E_WEAK_DISTANCE = 0.15

# spike_vs_sweep verdict 임계 — ms/frame 이 1.5x 이상 차이 + 같은 영상 +
# frames_total 동일 → GPU warmup cold-start 가설. frames_total 다름 →
# frame extractor 비결정성. 둘 다 → 양쪽 모두.
SPIKE_VS_SWEEP_MS_RATIO_THRESHOLD = 1.5

# Plan 08 MP+MB ref-invert overall (Plan 08 SUMMARY 영상별 표 행 4).
# 본 모듈은 SUMMARY 파일을 직접 파싱하지 않고 상수로 박제 — 변경 시
# Plan 08 SUMMARY 영상별 표 확인 후 갱신.
PLAN_08_MP_MB_REF_INVERT_OVERALL = 92.0


# ── argparse parser ───────────────────────────────────────────────────────────


def _default_out_path() -> Path:
    """기본 출력 경로 (UTC timestamp)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return Path("backend/research/spikes/reports") / f"debug_gap_{ts}.json"


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI argparse parser 빌더 (smoke 테스트 재사용 위해 분리).

    Plan 12 T-1-5 CLI surface — 12 args.
    """
    parser = argparse.ArgumentParser(
        description=(
            "갭 root cause 디버그 spike (Plan 01-12). "
            "5개 가설 (a-e) frame-level trace + ref-invert 22점 회귀 박제 + "
            "Plan 10 spike vs Plan 11 sweep 비일관성 박제."
        )
    )
    parser.add_argument(
        "--mode",
        choices=["report-only", "live"],
        default="report-only",
        help=(
            "report-only (기본): sweep_report JSON 만 분석 — Pod 의존 X. "
            "live: 영상 처리 추가 — belle Pod 전용 (mmpose + torch + GPU)."
        ),
    )
    parser.add_argument(
        "--sweep-report",
        required=True,
        help="Plan 11 sweep_rtmpose 결과 JSON 경로 (1차 입력, 필수).",
    )
    parser.add_argument(
        "--spike-report",
        default=None,
        help=(
            "Plan 10 spike_rtmpose 결과 JSON 경로 (선택). "
            "있으면 ref-sideway-spin spike_vs_sweep 비일관성 trace 활성화."
        ),
    )
    parser.add_argument(
        "--motions",
        nargs="+",
        default=None,
        help=(
            "live mode 분석 대상 영상 리스트 (예: ref-invert ref-sideway-spin). "
            "report-only mode 에서는 무시됨."
        ),
    )
    parser.add_argument(
        "--bucket",
        default="sunity-motion-pilot-videos",
        help="S3 버킷 (live mode). 기본: sunity-motion-pilot-videos.",
    )
    parser.add_argument(
        "--rtmpose-config",
        default=None,
        help="RTMPose config (.py) 경로 (live mode 필수).",
    )
    parser.add_argument(
        "--rtmpose-checkpoint",
        default=None,
        help="RTMPose pretrained 가중치 (.pth) 경로 (live mode 필수).",
    )
    parser.add_argument(
        "--motionbert-root",
        default="/workspace/MotionBERT",
        help="MotionBERT 저장소 루트 (live mode).",
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
        help="RTMPose keypoint score 컷 (live mode, 기본 0.3 — Plan 10 과 동일).",
    )
    parser.add_argument(
        "--det-model",
        default="none",
        help="사람 detector. 'none' (기본) = single-person 우회 (Plan 10 default).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help=(
            "JSON 결과 저장 경로. None 이면 "
            "backend/research/spikes/reports/debug_gap_<UTC>.json 자동 생성. "
            ".md sibling 도 같이 생성."
        ),
    )
    return parser


# ── 가설 (a): frame-mean 한계 (live mode) ────────────────────────────────────


def trace_hypothesis_a(
    lifter_angles: np.ndarray, nlf_angles: np.ndarray
) -> dict[str, Any]:
    """가설 (a) Frame-mean 한계 trace — 두 (T, J) 행렬 frame별 차이.

    두 엔진의 compute_joint_angles 출력은 같은 shape (T, J=8). 각 frame 에서
    joint 평균 절대각 차이를 계산해 평균 disagreement / peak frame 박제.

    Args:
        lifter_angles: RTMPose+MB chain 의 (T, J) 행렬 (도 단위).
        nlf_angles: NLF chain 의 (T, J) 행렬 (도 단위).

    Returns:
        {frame_count, joint_disagreement_per_frame, mean_disagreement,
         peak_disagreement_frame_idx, verdict}
    """
    lifter = np.asarray(lifter_angles, dtype=float)
    nlf = np.asarray(nlf_angles, dtype=float)

    if lifter.shape != nlf.shape:
        # 영상별 frame 수가 다르면 짧은 쪽에 맞춰 truncate
        min_T = min(lifter.shape[0], nlf.shape[0])
        lifter = lifter[:min_T]
        nlf = nlf[:min_T]

    if lifter.ndim != 2 or nlf.ndim != 2:
        raise ValueError(
            f"angles 형상은 (T, J) 이어야 합니다. lifter={lifter.shape}, "
            f"nlf={nlf.shape}"
        )

    # frame별 joint 평균 절대각 차이 (NaN-safe)
    diff = np.abs(lifter - nlf)  # (T, J)
    with np.errstate(invalid="ignore"):
        per_frame = np.nanmean(diff, axis=1)  # (T,)

    # 전체 NaN frame 처리 — peak 계산 시 제외
    valid = ~np.isnan(per_frame)
    if not np.any(valid):
        mean_disagreement = float("nan")
        peak_idx = -1
    else:
        mean_disagreement = float(np.nanmean(per_frame))
        # NaN 마스킹 후 argmax
        masked = np.where(valid, per_frame, -np.inf)
        peak_idx = int(np.argmax(masked))

    if np.isnan(mean_disagreement):
        verdict = "inconclusive"
    elif mean_disagreement >= HYPOTHESIS_A_STRONG_DEG:
        verdict = "strong"
    elif mean_disagreement >= HYPOTHESIS_A_WEAK_DEG:
        verdict = "weak"
    else:
        verdict = "rejected"

    return {
        "frame_count": int(lifter.shape[0]),
        "joint_disagreement_per_frame": [
            float(x) if not np.isnan(x) else None for x in per_frame.tolist()
        ],
        "mean_disagreement": (
            None if np.isnan(mean_disagreement) else round(mean_disagreement, 2)
        ),
        "peak_disagreement_frame_idx": peak_idx,
        "verdict": verdict,
        "thresholds": {
            "strong_deg": HYPOTHESIS_A_STRONG_DEG,
            "weak_deg": HYPOTHESIS_A_WEAK_DEG,
        },
    }


# ── 가설 (b): RTMPose headdown 약점 (live mode) ──────────────────────────────


def trace_hypothesis_b(
    rtmpose_kp: np.ndarray,
    score_threshold: float = 0.3,
) -> dict[str, Any]:
    """가설 (b) RTMPose headdown/거꾸로 자세 약점 trace.

    Args:
        rtmpose_kp: (T, 17, 3) RTMPose 출력 — x_pixel, y_pixel, score.
                    spike_rtmpose._run_rtmpose_2d 의 첫 번째 반환값.
        score_threshold: NaN drop 임계 (기본 0.3).

    Returns:
        {score_histogram: 5 bins [0-0.2, 0.2-0.4, ...],
         frame_mean_scores: per-frame mean score list,
         nan_drop_rate: < threshold keypoint 비율,
         headdown_frame_count, headdown_frame_indices,
         headdown_avg_score, overall_avg_score,
         verdict}
    """
    kp = np.asarray(rtmpose_kp, dtype=float)
    if kp.ndim != 3 or kp.shape[1] != 17 or kp.shape[2] < 3:
        raise ValueError(
            f"rtmpose_kp 형상은 (T, 17, 3) 이어야 합니다. 받음: {kp.shape}"
        )

    T = kp.shape[0]
    scores = kp[:, :, 2]  # (T, 17)

    # frame별 평균 score
    with np.errstate(invalid="ignore"):
        frame_mean = np.nanmean(scores, axis=1)  # (T,)
    valid_frames = ~np.isnan(frame_mean)
    overall_avg = (
        float(np.nanmean(frame_mean)) if np.any(valid_frames) else float("nan")
    )

    # histogram 5 bins
    bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    hist, _ = np.histogram(frame_mean[valid_frames], bins=bins)
    histogram = {
        "bins": bins,
        "counts": [int(c) for c in hist.tolist()],
    }

    # NaN drop rate — keypoint 단위 score < threshold 비율
    total_kp = int(np.sum(~np.isnan(scores)))
    if total_kp > 0:
        nan_drop_count = int(np.sum(scores < score_threshold))
        nan_drop_rate = nan_drop_count / total_kp
    else:
        nan_drop_rate = float("nan")

    # headdown 추정 — COCO 17 의 hip y 와 shoulder y 비교.
    # COCO idx: nose=0, L_shoulder=5, R_shoulder=6, L_hip=11, R_hip=12.
    # y 좌표가 image-space (top=0, bottom=H) 라 hip_y < shoulder_y 는
    # 카메라 기준 hip 이 더 위 = 거꾸로 자세.
    COCO_L_SHOULDER, COCO_R_SHOULDER = 5, 6
    COCO_L_HIP, COCO_R_HIP = 11, 12

    shoulder_y = (kp[:, COCO_L_SHOULDER, 1] + kp[:, COCO_R_SHOULDER, 1]) / 2.0
    hip_y = (kp[:, COCO_L_HIP, 1] + kp[:, COCO_R_HIP, 1]) / 2.0

    with np.errstate(invalid="ignore"):
        # hip 이 shoulder 위 (y 더 작음) = headdown 자세
        headdown_mask = hip_y < shoulder_y  # NaN 비교는 False
    headdown_indices = [
        int(i) for i in range(T) if bool(headdown_mask[i])
    ]
    headdown_count = len(headdown_indices)

    if headdown_count > 0:
        headdown_scores = frame_mean[headdown_mask]
        headdown_avg = float(np.nanmean(headdown_scores))
    else:
        headdown_avg = None

    # verdict
    if np.isnan(overall_avg):
        verdict = "inconclusive"
    elif (
        headdown_count >= 5
        and headdown_avg is not None
        and (overall_avg - headdown_avg) >= HYPOTHESIS_B_HEADDOWN_SCORE_DROP
        and headdown_avg <= HYPOTHESIS_B_STRONG_HEADDOWN_SCORE
    ):
        verdict = "strong"
    elif (
        headdown_count >= 5
        and headdown_avg is not None
        and (overall_avg - headdown_avg) >= HYPOTHESIS_B_HEADDOWN_SCORE_DROP
    ):
        verdict = "weak"
    elif headdown_count == 0:
        verdict = "rejected"  # 거꾸로 자세 자체가 없으므로 가설 적용 불가
    else:
        verdict = "weak" if (overall_avg - (headdown_avg or overall_avg)) > 0 else "rejected"

    return {
        "score_histogram": histogram,
        "frame_mean_scores": [
            float(x) if not np.isnan(x) else None for x in frame_mean.tolist()
        ],
        "nan_drop_rate": (
            None if np.isnan(nan_drop_rate) else round(nan_drop_rate, 4)
        ),
        "headdown_frame_count": headdown_count,
        "headdown_frame_indices": headdown_indices[:50],  # cap dump
        "headdown_avg_score": (
            None if headdown_avg is None else round(headdown_avg, 4)
        ),
        "overall_avg_score": (
            None if np.isnan(overall_avg) else round(overall_avg, 4)
        ),
        "verdict": verdict,
        "thresholds": {
            "headdown_score_drop": HYPOTHESIS_B_HEADDOWN_SCORE_DROP,
            "strong_headdown_score": HYPOTHESIS_B_STRONG_HEADDOWN_SCORE,
            "score_threshold": score_threshold,
        },
    }


# ── 가설 (c): NLF baseline 영상별 편차 (report-only OK) ──────────────────────


def trace_hypothesis_c(sweep_report: dict) -> dict[str, Any]:
    """가설 (c) NLF baseline 영상별 편차 trace — sweep JSON 만 입력.

    Args:
        sweep_report: Plan 11 sweep_rtmpose 결과 JSON 파싱 dict.

    Returns:
        {nlf_overall_range: [min, max], nlf_overall_variance, motions_count,
         nlf_dim_variance: per dimension list, nlf_nan_rate_per_joint: None
         (report-only), verdict}
    """
    motions = sweep_report.get("motions") or []
    nlf_overalls: list[float] = []
    dim_collect: dict[str, list[float]] = {"stability": [], "line": [], "angle": []}

    for entry in motions:
        nlf = entry.get("nlf") or {}
        overall = nlf.get("overall")
        if overall is not None:
            nlf_overalls.append(float(overall))
        for dim in dim_collect.keys():
            v = nlf.get(dim)
            if v is not None:
                dim_collect[dim].append(float(v))

    if not nlf_overalls:
        return {
            "nlf_overall_range": None,
            "nlf_overall_variance": None,
            "motions_count": 0,
            "nlf_dim_variance": {},
            "nlf_nan_rate_per_joint": None,
            "nan_rate_note": "sweep JSON 만 입력 — joint별 NaN rate 미산출.",
            "verdict": "inconclusive",
        }

    nlf_min = float(min(nlf_overalls))
    nlf_max = float(max(nlf_overalls))
    nlf_range = round(nlf_max - nlf_min, 2)
    nlf_var = float(np.var(nlf_overalls)) if len(nlf_overalls) > 1 else 0.0

    dim_variance = {}
    for dim, vals in dim_collect.items():
        if len(vals) >= 2:
            dim_variance[dim] = {
                "values": [round(v, 2) for v in vals],
                "variance": round(float(np.var(vals)), 4),
                "range": round(max(vals) - min(vals), 2),
            }
        else:
            dim_variance[dim] = {
                "values": [round(v, 2) for v in vals],
                "variance": None,
                "range": None,
            }

    if nlf_range >= HYPOTHESIS_C_STRONG_OVERALL_RANGE:
        verdict = "strong"
    elif nlf_range >= HYPOTHESIS_C_WEAK_OVERALL_RANGE:
        verdict = "weak"
    else:
        verdict = "rejected"

    return {
        "nlf_overall_range": [round(nlf_min, 2), round(nlf_max, 2)],
        "nlf_overall_span": nlf_range,
        "nlf_overall_variance": round(nlf_var, 4),
        "motions_count": len(nlf_overalls),
        "nlf_dim_variance": dim_variance,
        "nlf_nan_rate_per_joint": None,
        "nan_rate_note": (
            "sweep JSON 만 입력 — joint별 NaN rate 미산출. "
            "live mode 에서 (T, J) NLF 행렬 dump 추가 시 산출 가능."
        ),
        "verdict": verdict,
        "thresholds": {
            "strong_range": HYPOTHESIS_C_STRONG_OVERALL_RANGE,
            "weak_range": HYPOTHESIS_C_WEAK_OVERALL_RANGE,
        },
    }


# ── 가설 (d): keypoint 매핑 차이 (로컬 OK) ───────────────────────────────────


def trace_hypothesis_d() -> dict[str, Any]:
    """가설 (d) RTMPose ↔ NLF keypoint 매핑 차이 trace — Pod 의존 X.

    두 chain 의 정의 비교:
      - RTMPose chain: rtmpose_to_h36m17.H36M_JOINT_NAMES (17 joint, H3.6M
        ordering) — 12 직접 매핑 + 5 derive (hip/spine/thorax/neck_nose/head).
        MotionBERT 출력은 이 ordering 의 xyz.
      - NLF chain: sunity_shared.analysis.skeleton.KEYPOINT_NAMES (17, COCO
        ordering, ViTPose 동일). features.compute_joint_angles 는 8 joint
        angle 만 사용 (skeleton.JOINT_KEYS).

    중요: 점수 계산 시 두 path 의 (T, J=8) angle matrix 가 비교되므로,
    매핑 차이가 angle 계산에 영향을 주는 것은 8 joint 가 사용하는 12 keypoint
    (양쪽 어깨/팔꿈치/손목/엉덩이/무릎/발목) 의 좌표 정의. RTMPose chain 은
    이 12 keypoint 를 COCO → H36M ordering 으로 복사한 후 _h36m17_to_coco17_subset
    으로 다시 COCO ordering 으로 복원하므로, 12 limb joint 의 정의는 일치해야
    함 (face/derive joint 만 NaN).

    그럼에도 본 trace 가 가치 있는 이유 — RTMPose chain 의 두 ordering 변환
    과정에서 derive joint 와 H36M-only joint (hip/spine/thorax/neck_nose/head)
    가 NLF skeleton 의 동일 인덱스 joint 와 어떻게 다른지 박제. 향후 (Plan 13)
    moment-based scoring 에서 spine/thorax 같은 derive joint 가 angle 계산에
    포함되면 mismatch 가 점수에 직접 영향.

    Returns:
        {rtmpose_chain_joints: H36M 17 + COCO subset 12,
         nlf_chain_joints: COCO 17 + JOINT_ANGLES 8,
         joint_definition_diff: [{idx, rtmpose_chain, nlf_chain, equal}],
         angle_chain_keys: 8 joint key (양쪽 동일 가정),
         verdict}
    """
    from .rtmpose_to_h36m17 import H36M_JOINT_NAMES  # noqa: PLC0415

    from sunity_shared.analysis.skeleton import (  # noqa: PLC0415
        KEYPOINT_NAMES,
        JOINT_KEYS,
        JOINT_ANGLES,
    )

    # RTMPose chain 의 17 joint (H36M ordering)
    rtmpose_chain = list(H36M_JOINT_NAMES)
    # NLF chain 의 17 joint (COCO ordering, ViTPose 동일)
    nlf_chain = list(KEYPOINT_NAMES)

    diff_rows = []
    for i in range(17):
        r = rtmpose_chain[i]
        n = nlf_chain[i]
        diff_rows.append(
            {
                "idx": i,
                "rtmpose_chain": r,
                "nlf_chain": n,
                "equal": (r == n),
            }
        )

    # 두 chain 의 joint 이름이 byte-for-byte 동일하면 의심해야 — H36M ordering
    # vs COCO ordering 이 일치할 가능성은 매우 낮다. equal=True 가 모든 행이면
    # verdict 를 inconclusive 로 두고 코드 점검 권고.
    all_equal = all(row["equal"] for row in diff_rows)
    any_diff = any(not row["equal"] for row in diff_rows)

    angle_keys_match = list(JOINT_KEYS) == list(JOINT_ANGLES.keys())

    if all_equal:
        verdict = "inconclusive"
        note = (
            "두 chain 의 17 joint 이름이 모두 일치 — H36M vs COCO ordering 이 "
            "같을 수 없으므로 모듈 import 또는 ordering 확인 필요."
        )
    elif any_diff:
        # 매핑 차이 존재 — 이게 8 joint angle 계산에 영향 주는지 별개
        verdict = "strong"
        note = (
            "두 chain 의 17 joint ordering 이 다름 — RTMPose chain 은 H36M "
            "ordering, NLF chain 은 COCO ordering. spike_rtmpose 의 "
            "_h36m17_to_coco17_subset 가 12 limb joint 만 COCO ordering 으로 "
            "복원하므로 angle 계산 (8 joint) 자체는 일치해야 함. derive joint "
            "(hip/spine/thorax/neck_nose/head) 가 angle scoring 에 들어가면 "
            "mismatch 가 점수에 영향."
        )
    else:
        verdict = "rejected"
        note = "두 chain ordering 일치 — keypoint 매핑 차이 가설 기각."

    return {
        "rtmpose_chain_joints": rtmpose_chain,
        "nlf_chain_joints": nlf_chain,
        "joint_definition_diff": diff_rows,
        "angle_chain_keys": list(JOINT_KEYS),
        "angle_chain_keys_match": angle_keys_match,
        "diff_count": sum(1 for row in diff_rows if not row["equal"]),
        "verdict": verdict,
        "note": note,
    }


# ── 가설 (e): 두 엔진 3D pose 분포 차이 (live mode) ──────────────────────────


def trace_hypothesis_e(
    lifter_coco17_xyz: np.ndarray, nlf_coco17_xyz: np.ndarray
) -> dict[str, Any]:
    """가설 (e) 두 엔진 3D pose 분포 차이 trace.

    같은 영상 같은 frame 의 두 엔진 (T, 17, 3) xyz 를 root-relative 로 정규화한 후
    17 joint frame별 mean Euclidean distance.

    Args:
        lifter_coco17_xyz: (T, 17, 3) — RTMPose+MB 의 _h36m17_to_coco17_subset
            출력 xyz (마지막 채널 uncertainty 제외).
        nlf_coco17_xyz: (T, 17, 3) — NLF estimator 의 (T, 17, 4) 에서 xyz.

    Returns:
        {mean_per_frame, overall_mean_distance, peak_frame_idx, verdict}
    """
    lifter = np.asarray(lifter_coco17_xyz, dtype=float)
    nlf = np.asarray(nlf_coco17_xyz, dtype=float)

    if lifter.ndim != 3 or lifter.shape[1] != 17 or lifter.shape[2] < 3:
        raise ValueError(f"lifter_coco17_xyz 형상 오류: {lifter.shape}")
    if nlf.ndim != 3 or nlf.shape[1] != 17 or nlf.shape[2] < 3:
        raise ValueError(f"nlf_coco17_xyz 형상 오류: {nlf.shape}")

    lifter = lifter[:, :, :3]
    nlf = nlf[:, :, :3]

    # frame count 정렬
    min_T = min(lifter.shape[0], nlf.shape[0])
    lifter = lifter[:min_T]
    nlf = nlf[:min_T]

    # root-relative — hip center (COCO L_HIP=11, R_HIP=12 평균)
    L_HIP, R_HIP = 11, 12
    lifter_root = (lifter[:, L_HIP] + lifter[:, R_HIP]) / 2.0  # (T, 3)
    nlf_root = (nlf[:, L_HIP] + nlf[:, R_HIP]) / 2.0  # (T, 3)

    lifter_rel = lifter - lifter_root[:, np.newaxis, :]
    nlf_rel = nlf - nlf_root[:, np.newaxis, :]

    # frame별 17 joint Euclidean distance 평균
    diff = lifter_rel - nlf_rel  # (T, 17, 3)
    with np.errstate(invalid="ignore"):
        dist_per_joint = np.linalg.norm(diff, axis=2)  # (T, 17)
        per_frame = np.nanmean(dist_per_joint, axis=1)  # (T,)

    valid = ~np.isnan(per_frame)
    if not np.any(valid):
        overall_mean = float("nan")
        peak_idx = -1
    else:
        overall_mean = float(np.nanmean(per_frame))
        masked = np.where(valid, per_frame, -np.inf)
        peak_idx = int(np.argmax(masked))

    if np.isnan(overall_mean):
        verdict = "inconclusive"
    elif overall_mean >= HYPOTHESIS_E_STRONG_DISTANCE:
        verdict = "strong"
    elif overall_mean >= HYPOTHESIS_E_WEAK_DISTANCE:
        verdict = "weak"
    else:
        verdict = "rejected"

    return {
        "mean_per_frame": [
            float(x) if not np.isnan(x) else None for x in per_frame.tolist()
        ],
        "overall_mean_distance": (
            None if np.isnan(overall_mean) else round(overall_mean, 4)
        ),
        "peak_frame_idx": peak_idx,
        "verdict": verdict,
        "thresholds": {
            "strong_distance": HYPOTHESIS_E_STRONG_DISTANCE,
            "weak_distance": HYPOTHESIS_E_WEAK_DISTANCE,
        },
    }


# ── ref-invert 22점 회귀 박제 ───────────────────────────────────────────────


def trace_ref_invert_regression(
    sweep_report: dict, hypothesis_b_result: dict | None = None
) -> dict[str, Any]:
    """ref-invert MP+MB 92 → RTMPose+MB 70 의 22점 회귀 박제.

    Args:
        sweep_report: Plan 11 sweep_rtmpose JSON 결과.
        hypothesis_b_result: live mode (b) trace 결과 (있으면 headdown 가설 강도 추가).

    Returns:
        {motion: ref-invert, plan_08_mp_mb_overall, plan_11_rtmpose_mb_overall,
         delta, hypothesis_b_summary}
    """
    motions = sweep_report.get("motions") or []
    ref_invert = next(
        (m for m in motions if m.get("motion") == "ref-invert"), None
    )

    plan_11_overall = None
    if ref_invert is not None:
        rmb = ref_invert.get("rtmpose_mb") or {}
        plan_11_overall = rmb.get("overall")

    delta = None
    if plan_11_overall is not None:
        delta = round(plan_11_overall - PLAN_08_MP_MB_REF_INVERT_OVERALL, 2)

    b_summary = None
    if hypothesis_b_result is not None:
        b_summary = {
            "verdict": hypothesis_b_result.get("verdict"),
            "headdown_frame_count": hypothesis_b_result.get(
                "headdown_frame_count"
            ),
            "headdown_avg_score": hypothesis_b_result.get("headdown_avg_score"),
            "overall_avg_score": hypothesis_b_result.get("overall_avg_score"),
        }

    return {
        "motion": "ref-invert",
        "plan_08_mp_mb_overall": PLAN_08_MP_MB_REF_INVERT_OVERALL,
        "plan_11_rtmpose_mb_overall": plan_11_overall,
        "delta": delta,
        "hypothesis_b_summary": b_summary,
        "note": (
            "Plan 08 MP+MB 영상별 표 행 4 (ref-invert) overall 92 vs Plan 11 "
            "RTMPose+MB sweep ref-invert overall. delta < -15 면 회귀 박제 강."
        ),
    }


# ── spike_vs_sweep 비일관성 박제 ─────────────────────────────────────────────


def trace_spike_vs_sweep(
    spike_report: dict, sweep_report: dict, motion: str = "ref-sideway-spin"
) -> dict[str, Any]:
    """Plan 10 spike vs Plan 11 sweep 같은 영상 비일관성 trace.

    Args:
        spike_report: Plan 10 spike_rtmpose 단일 영상 JSON.
        sweep_report: Plan 11 sweep_rtmpose 5영상 JSON.
        motion: 비교 대상 motion (기본 ref-sideway-spin).

    Returns:
        {motion, spike_frames, sweep_frames, spike_overall, sweep_overall,
         spike_msper, sweep_msper, frames_differ, msper_ratio, verdict}

    verdict 분류 (T-2-4):
      - frames 동일 + ms/frame 비율 >= 1.5 → "gpu_warmup"
      - frames 다름 + ms/frame 비율 < 1.5 → "frame_extractor"
      - frames 다름 + ms/frame 비율 >= 1.5 → "both"
      - 둘 다 거의 동일 → "consistent"
    """
    spike_frames = spike_report.get("frames_total")
    spike_lifter = spike_report.get("lifter") or {}
    spike_overall = spike_lifter.get("overall")
    spike_msper = spike_lifter.get("ms_per_frame")
    spike_avg_score = spike_lifter.get("avg_rtm_score")

    sweep_motions = sweep_report.get("motions") or []
    sweep_entry = next(
        (e for e in sweep_motions if e.get("motion") == motion), None
    )

    sweep_frames = None
    sweep_overall = None
    sweep_msper = None
    sweep_avg_score = None
    if sweep_entry is not None:
        sweep_frames = sweep_entry.get("frames_total")
        rmb = sweep_entry.get("rtmpose_mb") or {}
        sweep_overall = rmb.get("overall")
        sweep_msper = rmb.get("ms_per_frame")
        sweep_avg_score = rmb.get("avg_score")

    frames_differ = (
        spike_frames is not None
        and sweep_frames is not None
        and spike_frames != sweep_frames
    )

    msper_ratio = None
    msper_differ = False
    if spike_msper and sweep_msper and sweep_msper > 0:
        msper_ratio = round(float(spike_msper) / float(sweep_msper), 3)
        msper_differ = (
            msper_ratio >= SPIKE_VS_SWEEP_MS_RATIO_THRESHOLD
            or msper_ratio <= 1.0 / SPIKE_VS_SWEEP_MS_RATIO_THRESHOLD
        )

    if frames_differ and msper_differ:
        verdict = "both"
    elif frames_differ:
        verdict = "frame_extractor"
    elif msper_differ:
        verdict = "gpu_warmup"
    elif spike_frames is not None and sweep_frames is not None:
        verdict = "consistent"
    else:
        verdict = "inconclusive"

    overall_diff = None
    if spike_overall is not None and sweep_overall is not None:
        overall_diff = round(float(sweep_overall) - float(spike_overall), 2)

    return {
        "motion": motion,
        "spike_frames": spike_frames,
        "sweep_frames": sweep_frames,
        "frames_differ": frames_differ,
        "spike_overall": spike_overall,
        "sweep_overall": sweep_overall,
        "overall_diff": overall_diff,
        "spike_msper": spike_msper,
        "sweep_msper": sweep_msper,
        "msper_ratio": msper_ratio,
        "msper_differ": msper_differ,
        "spike_avg_score": spike_avg_score,
        "sweep_avg_score": sweep_avg_score,
        "verdict": verdict,
        "thresholds": {
            "msper_ratio_threshold": SPIKE_VS_SWEEP_MS_RATIO_THRESHOLD,
        },
    }


# ── 가설별 verdict 합산 + Plan 13/14 권고 ────────────────────────────────────


def aggregate_recommendation(
    hypotheses_result: dict[str, Any],
    spike_vs_sweep: dict[str, Any] | None,
    ref_invert: dict[str, Any] | None,
) -> dict[str, Any]:
    """5 가설 verdict 합산 → Plan 13 path + Plan 14 게이트 기대.

    Plan 13 path 분류:
      - standard: (a) strong 단독 또는 (a)+약한 (b)/(c) → Plan 13 표준 진입
      - + hybrik_spike: (b) strong (ref-invert headdown) → Plan 13 + HybrIK 비교군
      - + nlf_re-spike: (c) strong (NLF baseline 편차) → Plan 13 + NLF 재검토
      - + rtmpose_to_h36m17_correction: (d) strong → derive joint 보정 spike
      - + multi_engine_averaging: (e) strong → lift path 신뢰도 약함

    Plan 14 gate expectation:
      - "expected to pass": (a) strong 단독 → frame-mean 만 원인
      - "additional spike required": (b)(c)(d)(e) 중 strong 존재
      - "inconclusive": 가설 다수 weak → Plan 14 결과로 사후 검증
    """
    verdicts = {
        k: (hypotheses_result.get(k) or {}).get("verdict")
        for k in ["a", "b", "c", "d", "e"]
    }

    paths = ["standard"]
    if verdicts.get("b") == "strong":
        paths.append("+ hybrik_spike")
    if verdicts.get("c") == "strong":
        paths.append("+ nlf_re-spike")
    if verdicts.get("d") == "strong":
        paths.append("+ rtmpose_to_h36m17_correction")
    if verdicts.get("e") == "strong":
        paths.append("+ multi_engine_averaging")

    plan_13_path = " ".join(paths)

    if verdicts.get("a") == "strong" and not any(
        verdicts.get(k) == "strong" for k in ["b", "c", "d", "e"]
    ):
        plan_14_gate = "expected to pass"
        rationale = (
            "(a) strong 단독 — frame-mean averaging 이 dominant 원인. Plan 13 "
            "key moment 만 평가로 갭 ≤5 회복 기대."
        )
    elif any(verdicts.get(k) == "strong" for k in ["b", "c", "d", "e"]):
        plan_14_gate = "additional spike required"
        rationale = (
            "(b)/(c)/(d)/(e) 중 strong 존재 — Plan 13 단독으로는 회복 어려움. "
            "후속 spike 필요."
        )
    elif all(
        v in ("rejected", "inconclusive", None) for v in verdicts.values()
    ):
        plan_14_gate = "inconclusive"
        rationale = (
            "모든 가설 rejected/inconclusive — 단일 원인 식별 실패. Plan 12.5 "
            "(추가 trace) 또는 Plan 13 진입 후 사후 검증."
        )
    else:
        plan_14_gate = "inconclusive"
        rationale = (
            "가설 다수 weak — 혼합 원인. Plan 13 진입 + Plan 14 결과로 어느 "
            "가설이 dominant 였는지 사후 verdict."
        )

    return {
        "verdicts": verdicts,
        "plan_13_path": plan_13_path,
        "plan_14_gate_expectation": plan_14_gate,
        "rationale": rationale,
        "spike_vs_sweep_verdict": (
            (spike_vs_sweep or {}).get("verdict") if spike_vs_sweep else None
        ),
        "ref_invert_delta": (ref_invert or {}).get("delta") if ref_invert else None,
    }


# ── live mode helper (lazy import 만 — 모듈 로드 시점 의존 X) ────────────────


def _run_live_for_motion(
    motion: str,
    bucket: str,
    rtmpose_config: str,
    rtmpose_checkpoint: str,
    motionbert_root: str,
    motionbert_weights: str,
    score_threshold: float,
    det_model: str,
) -> dict[str, Any]:
    """live mode 영상 1개 처리 — spike_rtmpose internal helper 재사용.

    재사용:
      - spike_rtmpose._resolve_video (S3 download)
      - spike_rtmpose._extract_frames (FfmpegFrameExtractor)
      - spike_rtmpose._run_rtmpose_2d (RTMPose 2D)
      - spike_rtmpose._load_motionbert + _run_motionbert_inference
      - spike_rtmpose._h36m17_to_coco17_subset
      - sunity_shared.analysis.pose_estimator.NlfPoseEstimator (운영 NLF)
      - sunity_shared.analysis.features.compute_joint_angles
      - sunity_shared.analysis.temporal.temporal_fill

    Returns:
        {motion, frames_total, hypothesis_a, hypothesis_b, hypothesis_e}
        + 영상별 NLF angles (T, J) NaN rate 도 (c) 보강용으로 dump.
    """
    from .spike_rtmpose import (  # noqa: PLC0415
        _resolve_video,
        _extract_frames,
        _run_rtmpose_2d,
        _load_motionbert,
        _run_motionbert_inference,
        _h36m17_to_coco17_subset,
    )
    from .rtmpose_to_h36m17 import convert_rtmpose_coco17_to_h36m17  # noqa: PLC0415

    from sunity_shared.analysis.features import (  # noqa: PLC0415
        compute_joint_angles,
        joint_uncertainty,
    )
    from sunity_shared.analysis.pose_estimator import NlfPoseEstimator  # noqa: PLC0415
    from sunity_shared.analysis.temporal import temporal_fill  # noqa: PLC0415

    log.info("=== live trace motion=%s ===", motion)

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        video_path = _resolve_video(None, motion, bucket, tmp_dir)
        frames = _extract_frames(video_path)
        T = len(frames)

        # RTMPose+MB chain
        rtmpose_kp, image_size, avg_score = _run_rtmpose_2d(
            frames, rtmpose_config, rtmpose_checkpoint, det_model=det_model
        )
        h36m_2d = convert_rtmpose_coco17_to_h36m17(
            rtmpose_kp,
            image_size=image_size,
            score_threshold=score_threshold,
            use_score_as_conf=False,
        )

        model, device = _load_motionbert(motionbert_root, motionbert_weights)
        h36m_xyz = _run_motionbert_inference(model, device, h36m_2d)
        lifter_coco17_array = _h36m17_to_coco17_subset(h36m_xyz)  # (T, 17, 4)

        angles_lifter = compute_joint_angles(lifter_coco17_array)
        filled_lifter = temporal_fill(
            angles_lifter, uncertainty=joint_uncertainty(lifter_coco17_array)
        )

        # NLF chain (운영 NLF estimator 그대로)
        nlf_estimator = NlfPoseEstimator()
        nlf_kp = nlf_estimator.estimate(frames)  # (T, 17, 4)
        angles_nlf = compute_joint_angles(nlf_kp)
        filled_nlf = temporal_fill(
            angles_nlf, uncertainty=joint_uncertainty(nlf_kp)
        )

        # 가설 trace
        h_a = trace_hypothesis_a(filled_lifter, filled_nlf)
        h_b = trace_hypothesis_b(rtmpose_kp, score_threshold=score_threshold)
        h_e = trace_hypothesis_e(
            lifter_coco17_array[:, :, :3], nlf_kp[:, :, :3]
        )

        # NLF NaN rate per joint (가설 c 보강)
        nlf_nan_rate = (
            np.mean(np.isnan(angles_nlf), axis=0).tolist()
            if angles_nlf.size
            else None
        )

        return {
            "motion": motion,
            "frames_total": T,
            "image_size": list(image_size),
            "avg_rtm_score": round(float(avg_score), 4),
            "hypothesis_a": h_a,
            "hypothesis_b": h_b,
            "hypothesis_e": h_e,
            "nlf_nan_rate_per_joint": (
                [round(float(v), 4) for v in nlf_nan_rate]
                if nlf_nan_rate is not None
                else None
            ),
        }


# ── 메인 ──────────────────────────────────────────────────────────────────────


def run_debug(
    sweep_report_path: str | Path,
    mode: str = "report-only",
    spike_report_path: str | Path | None = None,
    motions: list[str] | None = None,
    bucket: str = "sunity-motion-pilot-videos",
    rtmpose_config: str | None = None,
    rtmpose_checkpoint: str | None = None,
    motionbert_root: str = "/workspace/MotionBERT",
    motionbert_weights: str | None = None,
    score_threshold: float = 0.3,
    det_model: str = "none",
    out: str | Path | None = None,
) -> dict[str, Any]:
    """디버그 trace 메인 — mode 분기.

    report-only:
      - 가설 (c) sweep JSON 분석
      - 가설 (d) 두 chain joint 정의 비교 (Pod 의존 X)
      - spike_vs_sweep (spike_report_path 있을 시)
      - ref-invert 회귀 박제 (hypothesis_b 없이)

    live:
      - 위 항목 + 영상별 (a)(b)(e) trace + (c) NaN rate 보강
    """
    sweep_report_path = Path(sweep_report_path)
    if not sweep_report_path.exists():
        raise FileNotFoundError(f"sweep_report 없음: {sweep_report_path}")

    with open(sweep_report_path, encoding="utf-8") as f:
        sweep_report = json.load(f)

    spike_report = None
    if spike_report_path is not None:
        spike_report_path = Path(spike_report_path)
        if not spike_report_path.exists():
            raise FileNotFoundError(f"spike_report 없음: {spike_report_path}")
        with open(spike_report_path, encoding="utf-8") as f:
            spike_report = json.load(f)

    generated_at = datetime.now(timezone.utc).isoformat()

    # 가설 (c) — sweep JSON 만으로
    h_c = trace_hypothesis_c(sweep_report)
    # 가설 (d) — 로컬
    h_d = trace_hypothesis_d()

    # 영상별 live trace (a)(b)(e)
    per_motion_live: dict[str, Any] = {}
    h_a_aggregate = {"verdict": "inconclusive", "note": "live mode 미실행"}
    h_b_aggregate = {"verdict": "inconclusive", "note": "live mode 미실행"}
    h_e_aggregate = {"verdict": "inconclusive", "note": "live mode 미실행"}

    if mode == "live":
        if not motions:
            raise ValueError("live mode 는 --motions 필수입니다.")
        if not rtmpose_config or not rtmpose_checkpoint:
            raise ValueError(
                "live mode 는 --rtmpose-config + --rtmpose-checkpoint 필수입니다."
            )

        if motionbert_weights is None:
            motionbert_weights = str(
                Path(motionbert_root) / "checkpoint" / "pose3d"
                / "FT_MB_lite_MB_ft_h36m_global_lite" / "best_epoch.bin"
            )

        a_verdicts: list[str] = []
        b_verdicts: list[str] = []
        e_verdicts: list[str] = []

        for motion in motions:
            try:
                live_result = _run_live_for_motion(
                    motion=motion,
                    bucket=bucket,
                    rtmpose_config=rtmpose_config,
                    rtmpose_checkpoint=rtmpose_checkpoint,
                    motionbert_root=motionbert_root,
                    motionbert_weights=motionbert_weights,
                    score_threshold=score_threshold,
                    det_model=det_model,
                )
            except Exception as exc:  # noqa: BLE001 — 영상 단위 실패는 계속
                log.exception("[%s] live trace 실패", motion)
                per_motion_live[motion] = {
                    "motion": motion,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                continue

            per_motion_live[motion] = live_result
            a_verdicts.append(
                (live_result.get("hypothesis_a") or {}).get("verdict")
                or "inconclusive"
            )
            b_verdicts.append(
                (live_result.get("hypothesis_b") or {}).get("verdict")
                or "inconclusive"
            )
            e_verdicts.append(
                (live_result.get("hypothesis_e") or {}).get("verdict")
                or "inconclusive"
            )

        # aggregate — strong 1개라도 있으면 strong, weak 1개 이상이면 weak
        def _aggregate(verdicts: list[str]) -> dict[str, Any]:
            if not verdicts:
                return {"verdict": "inconclusive", "per_motion": verdicts}
            if "strong" in verdicts:
                v = "strong"
            elif "weak" in verdicts:
                v = "weak"
            elif all(x == "rejected" for x in verdicts):
                v = "rejected"
            else:
                v = "inconclusive"
            return {"verdict": v, "per_motion": verdicts}

        h_a_aggregate = _aggregate(a_verdicts)
        h_b_aggregate = _aggregate(b_verdicts)
        h_e_aggregate = _aggregate(e_verdicts)

    # ref-invert regression (가설 b 결과 있으면 ref-invert per-motion 에서 pull)
    ref_invert_b = None
    if "ref-invert" in per_motion_live:
        ref_invert_b = per_motion_live["ref-invert"].get("hypothesis_b")
    ref_invert = trace_ref_invert_regression(sweep_report, ref_invert_b)

    # spike_vs_sweep — spike_report 있을 때만
    spike_vs_sweep = None
    if spike_report is not None:
        spike_vs_sweep = trace_spike_vs_sweep(spike_report, sweep_report)

    # 최종 hypotheses 결과 — aggregate + per_motion
    hypotheses_result = {
        "a": {**h_a_aggregate, "per_motion": {
            m: (per_motion_live[m] or {}).get("hypothesis_a")
            for m in per_motion_live
            if "error" not in per_motion_live[m]
        }} if mode == "live" else h_a_aggregate,
        "b": {**h_b_aggregate, "per_motion": {
            m: (per_motion_live[m] or {}).get("hypothesis_b")
            for m in per_motion_live
            if "error" not in per_motion_live[m]
        }} if mode == "live" else h_b_aggregate,
        "c": h_c,
        "d": h_d,
        "e": {**h_e_aggregate, "per_motion": {
            m: (per_motion_live[m] or {}).get("hypothesis_e")
            for m in per_motion_live
            if "error" not in per_motion_live[m]
        }} if mode == "live" else h_e_aggregate,
    }

    recommendation = aggregate_recommendation(
        hypotheses_result, spike_vs_sweep, ref_invert
    )

    result = {
        "generated_at": generated_at,
        "mode": mode,
        "input": {
            "sweep_report": str(sweep_report_path),
            "spike_report": (
                str(spike_report_path) if spike_report_path else None
            ),
            "motions": motions or [],
        },
        "hypotheses": hypotheses_result,
        "ref_invert_regression": ref_invert,
        "spike_vs_sweep": spike_vs_sweep,
        "recommendation": recommendation,
        "per_motion_live": per_motion_live if mode == "live" else None,
    }

    # JSON + Markdown dump
    out_path = Path(out) if out is not None else _default_out_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log.info("JSON 결과: %s", out_path)

    md_path = out_path.with_suffix(".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(generate_markdown(result))
    log.info("Markdown 결과: %s", md_path)

    _print_summary(result)
    return result


# ── Markdown 보고서 ───────────────────────────────────────────────────────────


def _fmt(v: Any) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def generate_markdown(debug_result: dict) -> str:
    """가설별 verdict + ref-invert 회귀 + spike_vs_sweep + 권고 Markdown.

    Plan 12 T-3-2 명세.
    """
    inp = debug_result.get("input") or {}
    hyp = debug_result.get("hypotheses") or {}
    rec = debug_result.get("recommendation") or {}
    ref_inv = debug_result.get("ref_invert_regression") or {}
    svs = debug_result.get("spike_vs_sweep")

    lines = [
        "# Debug: 갭 root cause (Plan 01-12)",
        "",
        f"생성: {debug_result.get('generated_at', 'N/A')}",
        f"mode: `{debug_result.get('mode', 'N/A')}`",
        f"sweep_report: `{inp.get('sweep_report', 'N/A')}`",
        f"spike_report: `{inp.get('spike_report', 'N/A')}`",
        f"motions: {inp.get('motions', [])}",
        "",
        "## 1. 5가설 verdict 요약",
        "",
        "| 가설 | 설명 | verdict |",
        "|---|---|---|",
        f"| (a) frame-mean 한계 | 두 엔진 frame별 각도 차이 | {(hyp.get('a') or {}).get('verdict', 'N/A')} |",
        f"| (b) RTMPose headdown 약점 | 거꾸로 자세 keypoint 신뢰도 | {(hyp.get('b') or {}).get('verdict', 'N/A')} |",
        f"| (c) NLF baseline 편차 | 영상별 NLF 점수 변동 | {(hyp.get('c') or {}).get('verdict', 'N/A')} |",
        f"| (d) keypoint 매핑 차이 | 두 chain joint 정의 | {(hyp.get('d') or {}).get('verdict', 'N/A')} |",
        f"| (e) 두 엔진 3D 분포 차이 | root-relative xyz 거리 | {(hyp.get('e') or {}).get('verdict', 'N/A')} |",
        "",
    ]

    # 가설 (a) per-motion (live)
    a = hyp.get("a") or {}
    if a.get("per_motion") and isinstance(a["per_motion"], dict):
        lines += [
            "### (a) per-motion",
            "",
            "| 모션 | mean_disagreement (도) | peak_frame | verdict |",
            "|---|---|---|---|",
        ]
        for motion, data in a["per_motion"].items():
            if not data:
                continue
            lines.append(
                f"| {motion} | {_fmt(data.get('mean_disagreement'))} | "
                f"{_fmt(data.get('peak_disagreement_frame_idx'))} | "
                f"{data.get('verdict', 'N/A')} |"
            )
        lines.append("")

    # 가설 (b) per-motion
    b = hyp.get("b") or {}
    if b.get("per_motion") and isinstance(b["per_motion"], dict):
        lines += [
            "### (b) per-motion",
            "",
            "| 모션 | overall_avg_score | headdown_frame_count | headdown_avg_score | nan_drop_rate | verdict |",
            "|---|---|---|---|---|---|",
        ]
        for motion, data in b["per_motion"].items():
            if not data:
                continue
            lines.append(
                f"| {motion} | {_fmt(data.get('overall_avg_score'))} | "
                f"{_fmt(data.get('headdown_frame_count'))} | "
                f"{_fmt(data.get('headdown_avg_score'))} | "
                f"{_fmt(data.get('nan_drop_rate'))} | "
                f"{data.get('verdict', 'N/A')} |"
            )
        lines.append("")

    # 가설 (c) 박제
    c = hyp.get("c") or {}
    lines += [
        "### (c) NLF baseline 편차 박제",
        "",
        f"- NLF overall range: {c.get('nlf_overall_range')} (span {c.get('nlf_overall_span')})",
        f"- variance: {c.get('nlf_overall_variance')}",
        f"- motions_count: {c.get('motions_count')}",
        "",
    ]

    # 가설 (d) joint diff
    d = hyp.get("d") or {}
    lines += [
        "### (d) keypoint chain 정의 diff",
        "",
        f"- diff_count: {d.get('diff_count')} / 17",
        f"- angle_chain_keys_match: {d.get('angle_chain_keys_match')}",
        f"- note: {d.get('note', '')}",
        "",
    ]

    # 가설 (e) per-motion
    e = hyp.get("e") or {}
    if e.get("per_motion") and isinstance(e["per_motion"], dict):
        lines += [
            "### (e) per-motion",
            "",
            "| 모션 | overall_mean_distance | peak_frame | verdict |",
            "|---|---|---|---|",
        ]
        for motion, data in e["per_motion"].items():
            if not data:
                continue
            lines.append(
                f"| {motion} | {_fmt(data.get('overall_mean_distance'))} | "
                f"{_fmt(data.get('peak_frame_idx'))} | "
                f"{data.get('verdict', 'N/A')} |"
            )
        lines.append("")

    # ref-invert 회귀 표
    lines += [
        "## 2. ref-invert 22점 회귀 박제",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        f"| Plan 08 MP+MB ref-invert overall | {ref_inv.get('plan_08_mp_mb_overall')} |",
        f"| Plan 11 RTMPose+MB ref-invert overall | {ref_inv.get('plan_11_rtmpose_mb_overall')} |",
        f"| delta | {ref_inv.get('delta')} |",
        "",
    ]
    if ref_inv.get("hypothesis_b_summary"):
        b_sum = ref_inv["hypothesis_b_summary"]
        lines += [
            "### ref-invert 가설 (b) headdown summary",
            "",
            f"- verdict: {b_sum.get('verdict')}",
            f"- headdown_frame_count: {b_sum.get('headdown_frame_count')}",
            f"- headdown_avg_score: {b_sum.get('headdown_avg_score')}",
            f"- overall_avg_score: {b_sum.get('overall_avg_score')}",
            "",
        ]

    # spike_vs_sweep
    lines += [
        "## 3. Plan 10 spike vs Plan 11 sweep 비일관성",
        "",
    ]
    if svs is None:
        lines += ["- spike_report 입력 없음 — 비교 생략.", ""]
    else:
        lines += [
            f"motion: `{svs.get('motion')}`",
            "",
            "| 항목 | spike (Plan 10) | sweep (Plan 11) | diff |",
            "|---|---|---|---|",
            f"| frames_total | {svs.get('spike_frames')} | {svs.get('sweep_frames')} | "
            f"frames_differ={svs.get('frames_differ')} |",
            f"| overall | {_fmt(svs.get('spike_overall'))} | {_fmt(svs.get('sweep_overall'))} | "
            f"{_fmt(svs.get('overall_diff'))} |",
            f"| ms_per_frame | {_fmt(svs.get('spike_msper'))} | {_fmt(svs.get('sweep_msper'))} | "
            f"ratio={svs.get('msper_ratio')} |",
            f"| avg_score | {_fmt(svs.get('spike_avg_score'))} | {_fmt(svs.get('sweep_avg_score'))} | — |",
            "",
            f"verdict: **{svs.get('verdict')}**",
            "",
        ]

    # 권고
    lines += [
        "## 4. Plan 13 / Plan 14 진입 권고",
        "",
        f"- plan_13_path: `{rec.get('plan_13_path')}`",
        f"- plan_14_gate_expectation: **{rec.get('plan_14_gate_expectation')}**",
        f"- rationale: {rec.get('rationale', '')}",
        "",
        "### verdicts 합산",
        "",
        "| 가설 | verdict |",
        "|---|---|",
    ]
    for k in ["a", "b", "c", "d", "e"]:
        v = (rec.get("verdicts") or {}).get(k)
        lines.append(f"| ({k}) | {v} |")
    lines.append("")

    return "\n".join(lines) + "\n"


def _print_summary(debug_result: dict) -> None:
    rec = debug_result.get("recommendation") or {}
    hyp = debug_result.get("hypotheses") or {}
    print()
    print("=== debug_gap_root_cause 결과 ===")
    print(f"  mode: {debug_result.get('mode')}")
    print()
    print(f"  {'가설':<35}  verdict")
    print(f"  {'-'*35}  {'-'*12}")
    descriptions = {
        "a": "frame-mean 한계",
        "b": "RTMPose headdown 약점",
        "c": "NLF baseline 편차",
        "d": "keypoint 매핑 차이",
        "e": "두 엔진 3D 분포 차이",
    }
    for k in ["a", "b", "c", "d", "e"]:
        v = (hyp.get(k) or {}).get("verdict", "N/A")
        desc = f"({k}) {descriptions[k]}"
        print(f"  {desc:<35}  {v}")
    print()
    print(f"  plan_13_path: {rec.get('plan_13_path')}")
    print(f"  plan_14_gate: {rec.get('plan_14_gate_expectation')}")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    run_debug(
        sweep_report_path=args.sweep_report,
        mode=args.mode,
        spike_report_path=args.spike_report,
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
