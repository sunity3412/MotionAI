"""MediaPipe 2D + MotionBERT 3D lift 스파이크 하네스.

Plan 01-07: ref-foxtop-split 1개 영상으로 MP+MotionBERT stability/line 점수를
NLF baseline 대비 측정한다.

목적:
  Plan 01-06에서 MediaPipe world_landmarks의 z 노이즈가 인버트/측면 자세에서
  stability를 NLF 대비 28~50점 깎는 구조 한계를 확인했다.
  본 스파이크는 MediaPipe 2D 키포인트(신뢰도 높음)는 채용하되 z를 MotionBERT로
  재구성해 stability 회복 가능성을 검증한다.

라이선스:
  MotionBERT: Apache 2.0 (https://github.com/Walter0807/MotionBERT/blob/main/LICENSE)
  HybrIK (백업 후보): MIT (https://github.com/Jeff-sjtu/HybrIK)

판정 기준:
  Strong pass: stability >= 55, overall >= 60  → Plan 08 본 통합 진행
  Weak signal: stability 40~55               → HybrIK 등 백업 lifter 시도
  실패:         stability < 40               → Path A(튜닝) 또는 Path D(NLF 유지) 재고

실행 방법 (RunPod /workspace/SunityMotion):
  python3 -m backend.research.spikes.spike_motionbert \\
    --motion ref-foxtop-split \\
    --bucket sunity-motion-pilot-videos \\
    --motionbert-root /workspace/MotionBERT \\
    --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/MB_train_h36m/best_epoch.bin \\
    --out backend/research/spikes/reports/spike_motionbert_$(date +%Y%m%d).json

의존성 (RunPod에서만 실행):
  - mediapipe (x86_64 Linux wheel만 지원)
  - MotionBERT 저장소 clone + 사전학습 가중치 (~120MB)
  - torch + CUDA GPU (MotionBERT 추론)
  - AWS S3 자격증명 (영상 다운로드)
  - sunity_shared (PYTHONPATH 필요)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .mediapipe_to_h36m17 import convert_mp33_to_h36m17, h36m17_to_coco17_subset

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# ── 판정 기준 상수 ────────────────────────────────────────────────────────────

STRONG_PASS_STABILITY = 55.0   # stability >= 55 → Plan 08 진행
WEAK_SIGNAL_STABILITY = 40.0   # stability 40~55 → HybrIK 시도
STRONG_PASS_OVERALL = 60.0     # overall >= 60 (strong pass 추가 기준)
WEAK_SIGNAL_OVERALL = 45.0     # overall 45~60 (weak signal)

# S3 기준 모션 영상 키 경로
_REFERENCE_VIDEO_PREFIX = "reference"


# ── S3 다운로드 ───────────────────────────────────────────────────────────────


def _download_s3(s3_key: str, bucket: str, dest: Path) -> None:
    """S3에서 영상 다운로드. tempfile 경로에만 저장 (T-1-03 패턴)."""
    import boto3  # Lambda 런타임 또는 Pod 환경 제공

    s3 = boto3.client("s3")
    log.info("downloading s3://%s/%s → %s", bucket, s3_key, dest)
    s3.download_file(bucket, s3_key, str(dest))


def _resolve_video(
    video_path: str | None,
    motion: str | None,
    bucket: str,
    tmp_dir: Path,
) -> str:
    """로컬 경로 또는 S3 키 → 로컬 파일 경로 반환."""
    if video_path is not None:
        if not Path(video_path).exists():
            raise FileNotFoundError(f"영상 파일 없음: {video_path}")
        return video_path

    if motion is None:
        raise ValueError("--video 또는 --motion 중 하나는 필수입니다.")

    s3_key = f"{_REFERENCE_VIDEO_PREFIX}/{motion}.mp4"
    local_path = tmp_dir / f"{motion}.mp4"
    _download_s3(s3_key, bucket, local_path)
    return str(local_path)


# ── 프레임 추출 ───────────────────────────────────────────────────────────────


def _extract_frames(video_path: str) -> np.ndarray:
    """영상 → (T, H, W, 3) RGB uint8. FfmpegFrameExtractor (9fps / 640px)."""
    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor

    extractor = FfmpegFrameExtractor()
    frames = extractor.extract(video_path)
    log.info("frames extracted T=%d shape=%s", len(frames), frames.shape if hasattr(frames, "shape") else "list")
    return np.asarray(frames, dtype=np.uint8)


# ── MediaPipe 2D 추출 ─────────────────────────────────────────────────────────


def _run_mediapipe_2d(
    frames: np.ndarray,
    model_path: str | None = None,
    target_fps: float = 9.0,
) -> tuple[np.ndarray, float]:
    """MediaPipe PoseLandmarker → normalized_landmarks (T, 33, 3=x,y,visibility).

    Returns:
        (mp_lm, avg_conf): mp_lm shape (T, 33, 3), avg_conf float.

    normalized_landmarks를 사용하는 이유: world_landmarks의 z는 인버트/측면
    자세에서 노이즈가 크다 (Plan 01-06 D-16 보류 근거). 2D만 채용해 z는
    MotionBERT가 별도 학습된 가중치로 재구성한다.
    """
    import os

    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
    except ImportError as e:
        raise RuntimeError(
            "mediapipe 미설치. RunPod x86_64 환경에서 실행하세요. "
            f"원인: {e}"
        ) from e

    # 모델 경로 결정
    if model_path is None:
        model_path = os.environ.get("MEDIAPIPE_POSE_MODEL_PATH", "")
    if not model_path or not Path(model_path).exists():
        # Pod 기본 경로 시도
        pod_default = "/workspace/models/pose_landmarker_heavy.task"
        if Path(pod_default).exists():
            model_path = pod_default
        else:
            raise RuntimeError(
                f"pose_landmarker_heavy.task 없음: {model_path!r}. "
                "MEDIAPIPE_POSE_MODEL_PATH env 또는 --mediapipe-model 인자 필요."
            )

    options = mp_vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=model_path),
        running_mode=mp_vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_segmentation_masks=False,
    )
    landmarker = mp_vision.PoseLandmarker.create_from_options(options)

    T = len(frames)
    # normalized_landmarks: x, y in [0,1], visibility in [0,1]
    mp_lm = np.full((T, 33, 3), np.nan, dtype=float)
    detected = 0

    for t in range(T):
        timestamp_ms = int(t * 1000 / target_fps)
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=frames[t])
        result = landmarker.detect_for_video(img, timestamp_ms)

        if not result.pose_landmarks:
            continue

        detected += 1
        for j, lm in enumerate(result.pose_landmarks[0]):
            mp_lm[t, j, 0] = lm.x           # normalized x
            mp_lm[t, j, 1] = lm.y           # normalized y
            mp_lm[t, j, 2] = lm.visibility  # confidence proxy

    log.info("MediaPipe detected %d / %d frames", detected, T)
    if detected == 0:
        raise RuntimeError("MediaPipe: 전 프레임 미감지. 영상을 확인하세요.")

    # avg_conf: 감지된 프레임의 limb joint visibility 평균
    limb_mp_indices = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
    valid_mask = ~np.isnan(mp_lm[:, 0, 0])  # 프레임 감지 여부
    avg_conf = float(np.nanmean(mp_lm[valid_mask][:, limb_mp_indices, 2]))

    return mp_lm, avg_conf


# ── MotionBERT 추론 ───────────────────────────────────────────────────────────


def _load_motionbert(motionbert_root: str, weights_path: str):
    """MotionBERT 모델 로드. motionbert_root를 sys.path에 추가한다."""
    if motionbert_root not in sys.path:
        sys.path.insert(0, motionbert_root)

    import torch  # noqa: PLC0415

    # MotionBERT 저장소 구조: lib/model/DSTformer.py
    try:
        from lib.model.DSTformer import DSTformer  # type: ignore[import]
    except ImportError as e:
        raise RuntimeError(
            f"MotionBERT 저장소 구조를 찾지 못했습니다. "
            f"--motionbert-root가 올바른지 확인하세요: {motionbert_root}. "
            f"원인: {e}"
        ) from e

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info("MotionBERT device: %s", device)

    # DSTformer 설정 (MotionBERT H3.6M 기본 설정 — README 참조)
    model = DSTformer(
        dim_in=3,
        dim_out=3,
        dim_feat=256,
        dim_rep=512,
        depth=5,
        num_heads=8,
        mlp_ratio=4,
        norm_layer=None,
        maxlen=243,
        num_joints=17,
    )

    checkpoint = torch.load(weights_path, map_location=device)
    # checkpoint 구조: {'model_pos': state_dict} 또는 직접 state_dict
    if "model_pos" in checkpoint:
        state_dict = checkpoint["model_pos"]
    elif "model" in checkpoint:
        state_dict = checkpoint["model"]
    else:
        state_dict = checkpoint

    model.load_state_dict(state_dict, strict=False)
    model.to(device)
    model.eval()
    log.info("MotionBERT loaded from %s", weights_path)
    return model, device


def _run_motionbert_inference(
    model,
    device,
    h36m_2d: np.ndarray,
) -> np.ndarray:
    """MotionBERT 추론: (T, 17, 2|3) → (T, 17, 3=xyz).

    MotionBERT는 sliding window(최대 243 프레임)를 사용하므로 T가 243 이하면
    패딩 후 전체 배치로 추론한다. 긴 영상은 청크 단위로 처리.

    Args:
        h36m_2d: (T, 17, 2|3) — H3.6M 17-joint 2D 좌표 (+ optional confidence).

    Returns:
        (T, 17, 3) — 3D 복원 좌표 (MotionBERT 출력 스케일).
    """
    import torch  # noqa: PLC0415

    T = h36m_2d.shape[0]
    MAXLEN = 243  # MotionBERT 최대 시퀀스 길이

    # (T, 17, 2) 또는 (T, 17, 3) → (T, 17, 3) — 채널이 2개면 z=0 패딩
    if h36m_2d.shape[2] == 2:
        z_pad = np.zeros((T, 17, 1), dtype=float)
        h36m_input = np.concatenate([h36m_2d, z_pad], axis=2)
    else:
        h36m_input = h36m_2d[:, :, :3].copy()

    # NaN을 0으로 대체 (미감지 프레임)
    h36m_input = np.nan_to_num(h36m_input, nan=0.0)

    results_3d = []

    # 청크 단위 처리
    for start in range(0, T, MAXLEN):
        end = min(start + MAXLEN, T)
        chunk = h36m_input[start:end]  # (chunk_T, 17, 3)
        chunk_T = chunk.shape[0]

        # 패딩 (첫/끝 프레임 복제) → (MAXLEN, 17, 3)
        if chunk_T < MAXLEN:
            pad_len = MAXLEN - chunk_T
            # 끝에 마지막 프레임 복제
            pad = np.tile(chunk[-1:], (pad_len, 1, 1))
            chunk_padded = np.concatenate([chunk, pad], axis=0)
        else:
            chunk_padded = chunk

        # (1, MAXLEN, 17, 3) → tensor
        tensor = torch.tensor(
            chunk_padded[np.newaxis, ...], dtype=torch.float32
        ).to(device)

        with torch.no_grad():
            # DSTformer forward: (B, T, J, C) → (B, T, J, 3)
            out = model(tensor)  # (1, MAXLEN, 17, 3)

        out_np = out.squeeze(0).cpu().numpy()  # (MAXLEN, 17, 3)
        results_3d.append(out_np[:chunk_T])    # 패딩 제거

    xyz_3d = np.concatenate(results_3d, axis=0)  # (T, 17, 3)
    return xyz_3d


# ── NLF baseline ─────────────────────────────────────────────────────────────


def _run_nlf_baseline(frames: np.ndarray) -> dict:
    """NLF 엔진으로 baseline 점수 산출.

    compare_engines.py _run_nlf 와 동일 경로 — Wave 2 시점 옛 위치 import.
    GPU 필수: NLF는 CUDA 없으면 NaN 발산.
    """
    from sunity_shared.analysis.features import compute_joint_angles, joint_uncertainty
    from sunity_shared.analysis.pose_estimator import NlfPoseEstimator  # noqa: PLC0415 — Wave 2 옛 위치
    from sunity_shared.analysis.temporal import temporal_fill

    estimator = NlfPoseEstimator()
    kp_array = estimator.estimate(frames)  # (T, 17, 4)

    angles = compute_joint_angles(kp_array)
    filled_angles = temporal_fill(angles, uncertainty=joint_uncertainty(kp_array))

    return _score_from_angles(filled_angles)


# ── 점수 계산 ─────────────────────────────────────────────────────────────────


def _score_from_angles(angles: np.ndarray) -> dict:
    """관절각 배열 → 점수 payload.

    compare_engines._score_from_angles와 동일 체인
    (absolute_dimension_scores → overall_from_dimensions). 수정 금지.
    """
    from sunity_shared.analysis import dimensions, technique

    profile = technique.FallbackRecognizer().recognize(angles)

    try:
        dim_scores = dimensions.absolute_dimension_scores(angles, profile)
    except Exception:
        log.exception("차원 점수 계산 실패")
        dim_scores = {}

    try:
        overall = dimensions.overall_from_dimensions(dim_scores)
    except Exception:
        log.exception("종합 점수 계산 실패")
        overall = 0.0

    return {
        "overall": float(overall),
        "dimensions": {k: float(v) for k, v in dim_scores.items()},
    }


# ── 주요 함수 ─────────────────────────────────────────────────────────────────


def run_spike(
    motion: str | None = None,
    bucket: str = "sunity-motion-pilot-videos",
    video_path: str | None = None,
    motionbert_root: str = "/workspace/MotionBERT",
    motionbert_weights: str | None = None,
    mediapipe_model: str | None = None,
    out: str | None = None,
) -> dict:
    """MediaPipe 2D + MotionBERT 3D lift 스파이크 단일 영상 실행.

    Args:
        motion: motion_id (S3에서 reference/{motion}.mp4 로 다운로드).
        bucket: S3 버킷 이름.
        video_path: 로컬 영상 경로 (motion 대신 직접 경로 지정 시).
        motionbert_root: MotionBERT 저장소 루트 경로.
        motionbert_weights: 사전학습 가중치 경로.
                            None이면 motionbert_root/checkpoint/pose3d/MB_train_h36m/best_epoch.bin.
        mediapipe_model: pose_landmarker_heavy.task 경로 (None이면 Pod 기본 경로).
        out: 결과 JSON 저장 경로 (None이면 stdout 출력만).

    Returns:
        결과 dict (JSON 직렬화 가능):
          lifter: {overall, dimensions, ms_per_frame, avg_mp_conf}
          nlf:    {overall, dimensions, ms_per_frame}
          gap:    {overall_gap, dimension_gaps}
          verdict: "strong_pass" | "weak_signal" | "fail"
          generated_at: ISO 8601 UTC
          motion: motion_id
    """
    if motionbert_weights is None:
        motionbert_weights = str(
            Path(motionbert_root) / "checkpoint" / "pose3d"
            / "MB_train_h36m" / "best_epoch.bin"
        )

    log.info("=== spike_motionbert start motion=%s ===", motion or video_path)
    generated_at = datetime.now(timezone.utc).isoformat()

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        # 1. 영상 취득
        resolved_video = _resolve_video(video_path, motion, bucket, tmp_dir)

        # 2. 프레임 추출
        frames = _extract_frames(resolved_video)
        T = len(frames)

        # 3. 폴 축 검출
        from sunity_shared.analysis.pole.detector import HoughPoleDetector  # noqa: PLC0415
        _pole_axis = HoughPoleDetector().detect(frames)

        # ── MediaPipe + MotionBERT 경로 ────────────────────────────────────

        log.info("--- MediaPipe 2D 추출 ---")
        t0 = time.perf_counter()

        mp_lm, avg_mp_conf = _run_mediapipe_2d(frames, mediapipe_model)
        # (T, 33, 3=x,y,vis) → H3.6M 17 (T, 17, 3=x,y,vis)
        h36m_2d = convert_mp33_to_h36m17(mp_lm, use_visibility_as_conf=True)

        t_mp = time.perf_counter() - t0
        log.info("MediaPipe 2D: %.1f ms total, %.2f ms/frame", t_mp * 1000, t_mp * 1000 / T)

        log.info("--- MotionBERT 로드 + 추론 ---")
        t1 = time.perf_counter()

        model, device = _load_motionbert(motionbert_root, motionbert_weights)
        h36m_xyz = _run_motionbert_inference(model, device, h36m_2d)  # (T, 17, 3)
        # H3.6M 17 → COCO-17 (T, 17, 4=xyz+uncertainty)
        coco17_array = h36m17_to_coco17_subset(h36m_xyz)

        t_mb = time.perf_counter() - t1
        log.info("MotionBERT: %.1f ms total, %.2f ms/frame", t_mb * 1000, t_mb * 1000 / T)

        # 점수 계산
        from sunity_shared.analysis.features import compute_joint_angles, joint_uncertainty  # noqa: PLC0415
        from sunity_shared.analysis.temporal import temporal_fill  # noqa: PLC0415

        angles_lifter = compute_joint_angles(coco17_array)
        filled_lifter = temporal_fill(angles_lifter, uncertainty=joint_uncertainty(coco17_array))
        lifter_scores = _score_from_angles(filled_lifter)

        t_lifter_total = time.perf_counter() - t0
        lifter_ms_per_frame = t_lifter_total * 1000 / T

        # ── NLF baseline ──────────────────────────────────────────────────

        log.info("--- NLF baseline ---")
        t_nlf_start = time.perf_counter()

        try:
            nlf_scores = _run_nlf_baseline(frames)
            nlf_ms_per_frame = (time.perf_counter() - t_nlf_start) * 1000 / T
        except Exception:
            log.exception("NLF baseline 실패 — 결과에 null 기록")
            nlf_scores = {"overall": None, "dimensions": {}}
            nlf_ms_per_frame = None

        # ── 갭 계산 + 판정 ────────────────────────────────────────────────

        lifter_stability = lifter_scores["dimensions"].get("stability")
        lifter_overall = lifter_scores["overall"]

        if lifter_stability is not None and lifter_stability >= STRONG_PASS_STABILITY and lifter_overall >= STRONG_PASS_OVERALL:
            verdict = "strong_pass"
        elif lifter_stability is not None and lifter_stability >= WEAK_SIGNAL_STABILITY:
            verdict = "weak_signal"
        else:
            verdict = "fail"

        # 차원별 갭 (lifter - NLF)
        dimension_gaps = {}
        for dim_key in ["stability", "line", "angle"]:
            l_val = lifter_scores["dimensions"].get(dim_key)
            n_val = nlf_scores["dimensions"].get(dim_key) if nlf_scores["dimensions"] else None
            if l_val is not None and n_val is not None:
                dimension_gaps[dim_key] = round(l_val - n_val, 2)
            else:
                dimension_gaps[dim_key] = None

        overall_gap = None
        if lifter_overall is not None and nlf_scores["overall"] is not None:
            overall_gap = round(lifter_overall - nlf_scores["overall"], 2)

        result = {
            "generated_at": generated_at,
            "motion": motion or video_path,
            "frames_total": T,
            "lifter": {
                "engine": "mediapipe_2d+motionbert",
                "overall": round(lifter_overall, 2) if lifter_overall is not None else None,
                "dimensions": {
                    k: round(v, 2) for k, v in lifter_scores["dimensions"].items()
                },
                "ms_per_frame": round(lifter_ms_per_frame, 2),
                "avg_mp_conf": round(avg_mp_conf, 4),
            },
            "nlf": {
                "engine": "nlf",
                "overall": round(nlf_scores["overall"], 2) if nlf_scores["overall"] is not None else None,
                "dimensions": {
                    k: round(v, 2) for k, v in nlf_scores["dimensions"].items()
                } if nlf_scores["dimensions"] else {},
                "ms_per_frame": round(nlf_ms_per_frame, 2) if nlf_ms_per_frame is not None else None,
            },
            "gap": {
                "overall": overall_gap,
                "dimensions": dimension_gaps,
            },
            "verdict": verdict,
            "thresholds": {
                "strong_pass_stability": STRONG_PASS_STABILITY,
                "weak_signal_stability": WEAK_SIGNAL_STABILITY,
                "strong_pass_overall": STRONG_PASS_OVERALL,
                "weak_signal_overall": WEAK_SIGNAL_OVERALL,
            },
        }

    # 출력
    if out is not None:
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        log.info("JSON 결과: %s", out_path)

        # Markdown 요약
        md_path = out_path.with_suffix(".md")
        md = _generate_markdown(result)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        log.info("Markdown 결과: %s", md_path)

    # 표준 출력 요약
    _print_summary(result)

    return result


def _generate_markdown(result: dict) -> str:
    """결과 dict → Markdown 보고서."""
    lines = [
        "# Spike: MediaPipe 2D + MotionBERT 3D Lift",
        "",
        f"생성: {result.get('generated_at', 'N/A')}",
        f"모션: `{result.get('motion', 'N/A')}`",
        f"프레임: {result.get('frames_total', 'N/A')}",
        "",
        "## 점수 비교",
        "",
        "| 항목 | MP+MotionBERT | NLF baseline | 갭 |",
        "|------|-------------|------------|-----|",
    ]

    lifter = result.get("lifter", {})
    nlf = result.get("nlf", {})
    gap = result.get("gap", {})

    def _fmt(v):
        return f"{v:.1f}" if v is not None else "N/A"

    lines.append(
        f"| overall | {_fmt(lifter.get('overall'))} | {_fmt(nlf.get('overall'))} | {_fmt(gap.get('overall'))} |"
    )
    for dim in ["stability", "line", "angle"]:
        l_v = lifter.get("dimensions", {}).get(dim)
        n_v = nlf.get("dimensions", {}).get(dim)
        g_v = gap.get("dimensions", {}).get(dim)
        lines.append(f"| {dim} | {_fmt(l_v)} | {_fmt(n_v)} | {_fmt(g_v)} |")

    lines += [
        "",
        "## 추론 시간",
        "",
        f"- MP+MotionBERT: {_fmt(lifter.get('ms_per_frame'))} ms/frame",
        f"- NLF baseline: {_fmt(nlf.get('ms_per_frame'))} ms/frame",
        f"- MediaPipe avg_conf: {lifter.get('avg_mp_conf', 'N/A')}",
        "",
        "## 판정",
        "",
    ]

    verdict = result.get("verdict", "unknown")
    thresholds = result.get("thresholds", {})
    if verdict == "strong_pass":
        lines.append(
            f"**Strong pass** — stability >= {thresholds.get('strong_pass_stability')}, "
            f"overall >= {thresholds.get('strong_pass_overall')}. Plan 08 본 통합 진행."
        )
    elif verdict == "weak_signal":
        lines.append(
            f"**Weak signal** — stability {thresholds.get('weak_signal_stability')}~"
            f"{thresholds.get('strong_pass_stability')}. HybrIK 등 백업 lifter 시도."
        )
    else:
        lines.append(
            f"**실패** — stability < {thresholds.get('weak_signal_stability')}. "
            "Path A(튜닝) 또는 Path D(NLF 유지) 재고."
        )

    lines += [
        "",
        "## belle 다음 행동",
        "",
        "아래 중 하나를 응답하세요:",
        '- "approved, proceed to Plan 08" — strong pass. Plan 08 본 통합 작성 + Wave 3 진입.',
        '- "try HybrIK" — weak signal. HybrIK으로 spike 재실행.',
        '- "hold + reconsider path A" — 실패. Path A(튜닝) 또는 Path D(NLF 유지) 재고.',
        '- "hold + commercial license" — Path D. Max Planck Innovation 컨택.',
    ]

    return "\n".join(lines) + "\n"


def _print_summary(result: dict) -> None:
    """표준 출력에 요약 출력."""
    lifter = result.get("lifter", {})
    nlf = result.get("nlf", {})
    gap = result.get("gap", {})
    verdict = result.get("verdict", "unknown")

    def _f(v):
        return f"{v:.1f}" if v is not None else "N/A"

    print()
    print("=== spike_motionbert 결과 ===")
    print(f"  모션: {result.get('motion', 'N/A')}")
    print(f"  프레임: {result.get('frames_total', 'N/A')}")
    print()
    print(f"  {'항목':<12}  {'MP+MotionBERT':>14}  {'NLF baseline':>12}  {'갭':>6}")
    print(f"  {'-'*12}  {'-'*14}  {'-'*12}  {'-'*6}")
    print(f"  {'overall':<12}  {_f(lifter.get('overall')):>14}  {_f(nlf.get('overall')):>12}  {_f(gap.get('overall')):>6}")
    for dim in ["stability", "line", "angle"]:
        l_v = lifter.get("dimensions", {}).get(dim)
        n_v = nlf.get("dimensions", {}).get(dim)
        g_v = gap.get("dimensions", {}).get(dim)
        print(f"  {dim:<12}  {_f(l_v):>14}  {_f(n_v):>12}  {_f(g_v):>6}")
    print()
    print(f"  ms/frame (lifter): {_f(lifter.get('ms_per_frame'))}")
    print(f"  ms/frame (NLF):    {_f(nlf.get('ms_per_frame'))}")
    print(f"  avg_mp_conf:       {lifter.get('avg_mp_conf', 'N/A')}")
    print()
    print(f"  판정: {verdict.upper()}")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI 진입점.

    실행 예시 (RunPod /workspace/SunityMotion):
      python3 -m backend.research.spikes.spike_motionbert \\
        --motion ref-foxtop-split \\
        --bucket sunity-motion-pilot-videos \\
        --motionbert-root /workspace/MotionBERT \\
        --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/MB_train_h36m/best_epoch.bin \\
        --out backend/research/spikes/reports/spike_motionbert_$(date +%Y%m%d).json
    """
    parser = argparse.ArgumentParser(
        description="MediaPipe 2D + MotionBERT 3D lift 스파이크 (Plan 01-07)."
    )

    # 영상 소스 (둘 중 하나 필수)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--motion",
        type=str,
        help="motion_id (S3: reference/{motion}.mp4 자동 다운로드)",
    )
    src.add_argument(
        "--video",
        type=str,
        dest="video_path",
        help="로컬 영상 파일 경로 (--motion 대신 직접 지정)",
    )

    parser.add_argument(
        "--bucket",
        default="sunity-motion-pilot-videos",
        help="S3 버킷 이름 (기본: sunity-motion-pilot-videos)",
    )
    parser.add_argument(
        "--motionbert-root",
        default="/workspace/MotionBERT",
        help="MotionBERT 저장소 루트 경로",
    )
    parser.add_argument(
        "--motionbert-weights",
        default=None,
        help="사전학습 가중치 경로 (기본: {root}/checkpoint/pose3d/MB_train_h36m/best_epoch.bin)",
    )
    parser.add_argument(
        "--mediapipe-model",
        default=None,
        help="pose_landmarker_heavy.task 경로 (기본: Pod /workspace/models/)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="JSON 결과 저장 경로 (기본: stdout 출력만)",
    )

    args = parser.parse_args()

    run_spike(
        motion=args.motion,
        bucket=args.bucket,
        video_path=args.video_path,
        motionbert_root=args.motionbert_root,
        motionbert_weights=args.motionbert_weights,
        mediapipe_model=args.mediapipe_model,
        out=args.out,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    main()
