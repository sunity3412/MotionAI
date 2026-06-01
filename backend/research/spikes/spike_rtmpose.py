"""RTMPose 2D + MotionBERT 3D lift 스파이크 하네스 (Plan 01-10).

Plan 01-08 5영상 회귀에서 ref-sideway-spin 만 64점 (목표 70) fail.
1차 가설: MediaPipe 가 정면 학습 편향이라 측면 keypoint 분포가 좁아져
MotionBERT lift 의 측면 z 복원이 약함. RTMPose-l (Apache 2.0, COCO 학습) 은
정면+측면+occlusion 분포가 더 균등 — 2D detector 단계만 교체해 측면 보강을
검증.

본 spike 는 Plan 01-07 `spike_motionbert.py` 패턴을 그대로 따른다.
바뀐 것은 2D detector (MediaPipe → RTMPose) 하나뿐이며,
MotionBERT lift / 점수 계산 chain / NLF baseline 은 동일.

라이선스:
  MMPose / mmcv / mmengine / mmdet: Apache 2.0
    https://github.com/open-mmlab/mmpose/blob/main/LICENSE
  RTMPose-l checkpoint: Apache 2.0 (download.openmmlab.com)
  MotionBERT: Apache 2.0 (Plan 01-07 박제됨)
  본 spike: 운영 코드베이스 라이선스와 동일

판정 기준 (Plan 01-10 frontmatter):
  Strong pass: overall >= 70 → Plan 11 작성 (5영상 sweep + Wave 3 진입)
  Weak signal: 60 ≤ overall < 70 → 다른 checkpoint / HybrIK 시도
  실패:        overall < 60 → 4/5 수용 (sideway-spin known limitation)

실행 (RunPod /workspace/SunityMotion, Plan 08 setup 상태 가정):
  pip install -U openmim
  mim install mmengine "mmcv>=2.0" mmdet mmpose
  mim download mmpose --config rtmpose-l_8xb256-420e_coco-256x192 \\
    --dest /workspace/rtmpose_weights/

  python3 -m backend.research.spikes.spike_rtmpose \\
    --motion ref-sideway-spin \\
    --bucket sunity-motion-pilot-videos \\
    --rtmpose-config /workspace/rtmpose_weights/rtmpose-l_8xb256-420e_coco-256x192.py \\
    --rtmpose-checkpoint /workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth \\
    --motionbert-root /workspace/MotionBERT \\
    --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin \\
    --out backend/research/spikes/reports/spike_rtmpose_$(date +%Y%m%d_%H%M).json

의존성 (RunPod GPU Pod 전용):
  - mmpose + mmengine + mmcv + mmdet (Apache 2.0, mim install)
  - MotionBERT 저장소 + best_epoch.bin (Plan 08 setup 완료 시 이미 존재)
  - torch + CUDA GPU (MotionBERT 추론)
  - boto3 + AWS 자격증명 (S3 영상 다운로드)
  - sunity_shared (PYTHONPATH 필요)

로컬 실행 금지 — mmpose Linux wheel 만 지원, GPU 필수.
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

from .rtmpose_to_h36m17 import (
    DEFAULT_SCORE_THRESHOLD,
    convert_rtmpose_coco17_to_h36m17,
)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# ── 판정 기준 상수 (Plan 01-10) ────────────────────────────────────────────────

STRONG_PASS_OVERALL = 70.0   # ≥ 70 → Plan 11 진행
WEAK_SIGNAL_OVERALL = 60.0   # 60~70 → 다른 checkpoint

# S3 기준 모션 영상 키 경로 (Plan 07/08 spike 와 동일)
_REFERENCE_VIDEO_PREFIX = "reference"


# ── S3 다운로드 ───────────────────────────────────────────────────────────────


def _download_s3(s3_key: str, bucket: str, dest: Path) -> None:
    """S3 → 로컬 경로 다운로드 (Plan 07 spike_motionbert 동일)."""
    import boto3  # Pod 환경에서 제공

    s3 = boto3.client("s3")
    log.info("downloading s3://%s/%s -> %s", bucket, s3_key, dest)
    s3.download_file(bucket, s3_key, str(dest))


def _resolve_video(
    video_path: str | None,
    motion: str | None,
    bucket: str,
    tmp_dir: Path,
) -> str:
    """로컬 경로 또는 S3 key → 로컬 파일 경로."""
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
    """영상 → (T, H, W, 3) RGB uint8. FfmpegFrameExtractor (9fps / 640px).

    Plan 07/08 spike 와 동일 — sunity_shared.analysis.frame_extractor.
    """
    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor

    extractor = FfmpegFrameExtractor()
    frames = extractor.extract(video_path)
    log.info(
        "frames extracted T=%d shape=%s",
        len(frames),
        frames.shape if hasattr(frames, "shape") else "list",
    )
    return np.asarray(frames, dtype=np.uint8)


# ── RTMPose 2D 추출 ───────────────────────────────────────────────────────────


def _run_rtmpose_2d(
    frames: np.ndarray,
    rtmpose_config: str,
    rtmpose_checkpoint: str,
    det_model: str = "rtmdet-nano",
) -> tuple[np.ndarray, tuple[int, int], float]:
    """RTMPose-l 로 COCO-17 키포인트 추출.

    Args:
        frames: (T, H, W, 3) RGB uint8.
        rtmpose_config: RTMPose config 파일 경로 (.py) 또는 이름.
            예: '/workspace/rtmpose_weights/rtmpose-l_8xb256-420e_coco-256x192.py'
        rtmpose_checkpoint: pretrained 가중치 .pth 경로.
        det_model: 사람 detector alias. 기본 'rtmdet-nano' (RTMPose 표준 stack).
            top-down pose estimator 는 detector → crop → pose 의 흐름이며
            mmpose 의 MMPoseInferencer 가 둘을 자동 wire 한다.

    Returns:
        (rtmpose_kp, image_size, avg_score):
          rtmpose_kp: (T, 17, 3) - x_pixel, y_pixel, score. 미감지 프레임은 NaN.
          image_size: (W, H) - 첫 프레임 픽셀 크기 (좌표 정규화용).
          avg_score: 검출 프레임 keypoint score 평균.
    """
    try:
        from mmpose.apis import MMPoseInferencer
    except ImportError as e:
        raise RuntimeError(
            "mmpose 미설치. RunPod 에서 다음 명령으로 설치 후 재시도:\n"
            "  pip install -U openmim\n"
            '  mim install mmengine "mmcv>=2.0" mmdet mmpose\n'
            f"원인: {e}"
        ) from e

    log.info(
        "MMPoseInferencer init config=%s ckpt=%s det=%s",
        rtmpose_config, rtmpose_checkpoint, det_model,
    )

    inferencer = MMPoseInferencer(
        pose2d=rtmpose_config,
        pose2d_weights=rtmpose_checkpoint,
        det_model=det_model,
        det_cat_ids=[0],  # COCO 'person' class
    )

    T = len(frames)
    H, W = frames.shape[1], frames.shape[2]
    image_size = (int(W), int(H))

    # 출력 (T, 17, 3) — x, y pixel, score. 미감지 NaN.
    rtmpose_kp = np.full((T, 17, 3), np.nan, dtype=float)
    detected = 0

    for t in range(T):
        # MMPoseInferencer 는 한 장씩 ndarray 입력 가능 (BGR/RGB 자동 처리).
        # 영상 프레임을 그대로 전달하면 generator 가 1 batch dict 반환.
        try:
            gen = inferencer(frames[t])
            result = next(gen)
        except StopIteration:
            continue

        preds = result.get("predictions", [])
        # preds: list[list[dict]] — batch x instances
        if not preds or not preds[0]:
            continue

        # 첫 번째 instance (가장 confident person) 사용.
        # multi-person 영상은 본 spike 범위 밖.
        inst = preds[0][0]
        kp_xy = np.asarray(inst.get("keypoints", []), dtype=float)
        kp_score = np.asarray(inst.get("keypoint_scores", []), dtype=float)

        if kp_xy.ndim != 2 or kp_xy.shape != (17, 2):
            log.warning("frame %d: unexpected keypoints shape %s", t, kp_xy.shape)
            continue
        if kp_score.shape != (17,):
            log.warning("frame %d: unexpected scores shape %s", t, kp_score.shape)
            continue

        detected += 1
        rtmpose_kp[t, :, 0] = kp_xy[:, 0]
        rtmpose_kp[t, :, 1] = kp_xy[:, 1]
        rtmpose_kp[t, :, 2] = kp_score

    log.info("RTMPose detected %d / %d frames", detected, T)
    if detected == 0:
        raise RuntimeError("RTMPose: 전 프레임 미감지. 영상/모델 확인.")

    # avg_score: 검출 프레임 keypoint score 평균 (NaN 무시).
    avg_score = float(np.nanmean(rtmpose_kp[:, :, 2]))
    return rtmpose_kp, image_size, avg_score


# ── MotionBERT 추론 (Plan 07 spike 와 동일 로직 — Pod 전용) ───────────────────


def _load_motionbert(motionbert_root: str, weights_path: str):
    """MotionBERT 모델 로드. motionbert_root 를 sys.path 에 추가."""
    if motionbert_root not in sys.path:
        sys.path.insert(0, motionbert_root)

    import torch  # noqa: PLC0415

    try:
        from lib.model.DSTformer import DSTformer  # type: ignore[import]
    except ImportError as e:
        raise RuntimeError(
            "MotionBERT 저장소 구조를 찾지 못했습니다. "
            f"--motionbert-root 가 올바른지 확인하세요: {motionbert_root}. "
            f"원인: {e}"
        ) from e

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info("MotionBERT device: %s", device)

    # DSTformer 설정 (FT_MB_lite_MB_ft_h36m_global_lite). norm_layer 명시 금지
    # (Plan 07 c164700 commit 박제 — DSTformer 기본 nn.LayerNorm 사용).
    model = DSTformer(
        dim_in=3,
        dim_out=3,
        dim_feat=256,
        dim_rep=512,
        depth=5,
        num_heads=8,
        mlp_ratio=4,
        maxlen=243,
        num_joints=17,
        att_fuse=True,
    )

    checkpoint = torch.load(weights_path, map_location=device)
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


def _run_motionbert_inference(model, device, h36m_2d: np.ndarray) -> np.ndarray:
    """MotionBERT 추론: (T, 17, 2|3) → (T, 17, 3=xyz).

    Plan 07 spike_motionbert._run_motionbert_inference 와 동일.
    sliding window MAXLEN=243, 짧은 영상 끝 프레임 복제 패딩.
    """
    import torch  # noqa: PLC0415

    T = h36m_2d.shape[0]
    MAXLEN = 243

    # (T, 17, 2) → (T, 17, 3) z=0 패딩
    if h36m_2d.shape[2] == 2:
        z_pad = np.zeros((T, 17, 1), dtype=float)
        h36m_input = np.concatenate([h36m_2d, z_pad], axis=2)
    else:
        h36m_input = h36m_2d[:, :, :3].copy()

    # NaN → 0 (미감지 프레임)
    h36m_input = np.nan_to_num(h36m_input, nan=0.0)

    results_3d = []
    for start in range(0, T, MAXLEN):
        end = min(start + MAXLEN, T)
        chunk = h36m_input[start:end]
        chunk_T = chunk.shape[0]

        if chunk_T < MAXLEN:
            pad_len = MAXLEN - chunk_T
            pad = np.tile(chunk[-1:], (pad_len, 1, 1))
            chunk_padded = np.concatenate([chunk, pad], axis=0)
        else:
            chunk_padded = chunk

        tensor = torch.tensor(
            chunk_padded[np.newaxis, ...], dtype=torch.float32
        ).to(device)

        with torch.no_grad():
            out = model(tensor)  # (1, MAXLEN, 17, 3)

        out_np = out.squeeze(0).cpu().numpy()
        results_3d.append(out_np[:chunk_T])

    return np.concatenate(results_3d, axis=0)  # (T, 17, 3)


# ── H36M 17 → COCO-17 subset (Plan 07 spike 와 동일 로직) ─────────────────────


def _h36m17_to_coco17_subset(h36m_xyz: np.ndarray) -> np.ndarray:
    """H3.6M 17-joint (T, 17, 3) → COCO-17 (T, 17, 4=xyz+uncertainty) 부분 매핑.

    Plan 01-08 production `pose_lifters/mediapipe_to_h36m17.h36m17_to_coco17_subset`
    와 동일 매핑. 본 spike 가 production lifter 를 import 하지 않고 자체 구현하는
    이유: production 코드 무수정 원칙 + spike 격리.

    12 limb joint 매핑, face 5개 (nose, eyes, ears) NaN. features.compute_joint_angles
    는 limb joint 만 사용하므로 face NaN 은 점수 계산에 영향 없음.
    """
    xyz = np.asarray(h36m_xyz, dtype=float)
    if xyz.ndim != 3 or xyz.shape[1] != 17 or xyz.shape[2] < 3:
        raise ValueError(f"h36m_xyz 형상 오류: {xyz.shape}, expect (T, 17, 3)")

    T = xyz.shape[0]
    out = np.full((T, 17, 4), np.nan, dtype=float)
    out[:, :, 3] = 1.0  # uncertainty default 1.0

    # (H36M idx, COCO idx) — Plan 08 production 어댑터와 동일
    pairs = (
        (11, 5),   # l_shoulder
        (14, 6),   # r_shoulder
        (12, 7),   # l_elbow
        (15, 8),   # r_elbow
        (13, 9),   # l_wrist
        (16, 10),  # r_wrist
        (4, 11),   # l_hip
        (1, 12),   # r_hip
        (5, 13),   # l_knee
        (2, 14),   # r_knee
        (6, 15),   # l_ankle (l_foot)
        (3, 16),   # r_ankle (r_foot)
    )
    for h36m_idx, coco_idx in pairs:
        out[:, coco_idx, 0] = xyz[:, h36m_idx, 0]
        out[:, coco_idx, 1] = xyz[:, h36m_idx, 1]
        out[:, coco_idx, 2] = xyz[:, h36m_idx, 2]
        out[:, coco_idx, 3] = 0.0

    return out


# ── NLF baseline (Plan 07 spike 와 동일) ─────────────────────────────────────


def _run_nlf_baseline(frames: np.ndarray) -> dict:
    """NLF 엔진 baseline 점수 — compare_engines._run_nlf 동일 경로."""
    from sunity_shared.analysis.features import compute_joint_angles, joint_uncertainty
    from sunity_shared.analysis.pose_estimator import NlfPoseEstimator
    from sunity_shared.analysis.temporal import temporal_fill

    estimator = NlfPoseEstimator()
    kp_array = estimator.estimate(frames)  # (T, 17, 4)

    angles = compute_joint_angles(kp_array)
    filled = temporal_fill(angles, uncertainty=joint_uncertainty(kp_array))
    return _score_from_angles(filled)


# ── 점수 계산 (Plan 07 spike 와 동일) ────────────────────────────────────────


def _score_from_angles(angles: np.ndarray) -> dict:
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
    motion: str | None,
    bucket: str,
    rtmpose_config: str,
    rtmpose_checkpoint: str,
    motionbert_root: str,
    motionbert_weights: str | None,
    video_path: str | None = None,
    det_model: str = "rtmdet-nano",
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    out: str | None = None,
) -> dict:
    """RTMPose 2D + MotionBERT 3D lift 스파이크 단일 영상 실행.

    Plan 07 `spike_motionbert.run_spike` 와 동일 구조 — 2D detector 만 교체.
    """
    if motionbert_weights is None:
        motionbert_weights = str(
            Path(motionbert_root) / "checkpoint" / "pose3d"
            / "FT_MB_lite_MB_ft_h36m_global_lite" / "best_epoch.bin"
        )

    log.info("=== spike_rtmpose start motion=%s ===", motion or video_path)
    generated_at = datetime.now(timezone.utc).isoformat()

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        # 1. 영상 취득
        resolved_video = _resolve_video(video_path, motion, bucket, tmp_dir)

        # 2. 프레임 추출
        frames = _extract_frames(resolved_video)
        T = len(frames)

        # 3. 폴 축 검출 (현재 미사용 — Plan 07 spike 와 동일하게 호출만)
        from sunity_shared.analysis.pole.detector import HoughPoleDetector  # noqa: PLC0415
        _pole_axis = HoughPoleDetector().detect(frames)

        # ── RTMPose + MotionBERT 경로 ───────────────────────────────────────

        log.info("--- RTMPose 2D 추출 ---")
        t0 = time.perf_counter()

        rtmpose_kp, image_size, avg_rtm_score = _run_rtmpose_2d(
            frames, rtmpose_config, rtmpose_checkpoint, det_model=det_model
        )
        # (T, 17, 3 pixel+score) → H3.6M 17 정규화 (T, 17, 2)
        h36m_2d = convert_rtmpose_coco17_to_h36m17(
            rtmpose_kp,
            image_size=image_size,
            score_threshold=score_threshold,
            use_score_as_conf=False,
        )

        t_rtm = time.perf_counter() - t0
        log.info(
            "RTMPose 2D: %.1f ms total, %.2f ms/frame, avg_score=%.4f",
            t_rtm * 1000, t_rtm * 1000 / T, avg_rtm_score,
        )

        log.info("--- MotionBERT 로드 + 추론 ---")
        t1 = time.perf_counter()

        model, device = _load_motionbert(motionbert_root, motionbert_weights)
        h36m_xyz = _run_motionbert_inference(model, device, h36m_2d)
        coco17_array = _h36m17_to_coco17_subset(h36m_xyz)

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

        # ── NLF baseline ─────────────────────────────────────────────────────

        log.info("--- NLF baseline ---")
        t_nlf_start = time.perf_counter()
        try:
            nlf_scores = _run_nlf_baseline(frames)
            nlf_ms_per_frame = (time.perf_counter() - t_nlf_start) * 1000 / T
        except Exception:
            log.exception("NLF baseline 실패 — 결과에 null 기록")
            nlf_scores = {"overall": None, "dimensions": {}}
            nlf_ms_per_frame = None

        # ── 갭 + 판정 ─────────────────────────────────────────────────────────

        lifter_overall = lifter_scores["overall"]
        if lifter_overall is not None and lifter_overall >= STRONG_PASS_OVERALL:
            verdict = "strong_pass"
        elif lifter_overall is not None and lifter_overall >= WEAK_SIGNAL_OVERALL:
            verdict = "weak_signal"
        else:
            verdict = "fail"

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
            "detector": "rtmpose-l",
            "rtmpose_config": rtmpose_config,
            "rtmpose_checkpoint": rtmpose_checkpoint,
            "score_threshold": score_threshold,
            "image_size": list(image_size),
            "lifter": {
                "engine": "rtmpose_2d+motionbert",
                "overall": round(lifter_overall, 2) if lifter_overall is not None else None,
                "dimensions": {
                    k: round(v, 2) for k, v in lifter_scores["dimensions"].items()
                },
                "ms_per_frame": round(lifter_ms_per_frame, 2),
                "avg_rtm_score": round(avg_rtm_score, 4),
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

        md_path = out_path.with_suffix(".md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(_generate_markdown(result))
        log.info("Markdown 결과: %s", md_path)

    _print_summary(result)
    return result


def _generate_markdown(result: dict) -> str:
    lines = [
        "# Spike: RTMPose 2D + MotionBERT 3D Lift (Plan 01-10)",
        "",
        f"생성: {result.get('generated_at', 'N/A')}",
        f"모션: `{result.get('motion', 'N/A')}`",
        f"프레임: {result.get('frames_total', 'N/A')}",
        f"detector: `{result.get('detector', 'N/A')}`",
        f"RTMPose config: `{result.get('rtmpose_config', 'N/A')}`",
        f"score_threshold: {result.get('score_threshold', 'N/A')}",
        f"image_size: {result.get('image_size', 'N/A')}",
        "",
        "## 점수 비교",
        "",
        "| 항목 | RTMPose+MotionBERT | NLF baseline | 갭 |",
        "|------|--------------------|--------------|-----|",
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
        f"- RTMPose+MotionBERT: {_fmt(lifter.get('ms_per_frame'))} ms/frame",
        f"- NLF baseline: {_fmt(nlf.get('ms_per_frame'))} ms/frame",
        f"- RTMPose avg_score: {lifter.get('avg_rtm_score', 'N/A')}",
        "",
        "## 판정",
        "",
    ]

    verdict = result.get("verdict", "unknown")
    thresholds = result.get("thresholds", {})
    if verdict == "strong_pass":
        lines.append(
            f"**Strong pass** — overall >= {thresholds.get('strong_pass_overall')}. "
            "Plan 11 작성 (5영상 sweep + 게이트 룰 재정의 + Wave 3 진입)."
        )
    elif verdict == "weak_signal":
        lines.append(
            f"**Weak signal** — overall {thresholds.get('weak_signal_overall')}~"
            f"{thresholds.get('strong_pass_overall')}. 다른 checkpoint / HybrIK 시도."
        )
    else:
        lines.append(
            f"**실패** — overall < {thresholds.get('weak_signal_overall')}. "
            "측면 보강 포기, 4/5 수용 (Plan 11 별경로)."
        )

    lines += [
        "",
        "## belle 다음 행동",
        "",
        "아래 중 하나로 응답:",
        '- "approved, proceed to Plan 11" — overall ≥ 70 → 5영상 sweep + Wave 3 진입',
        '- "try other checkpoint" — 60~70 → RTMPose-x 또는 384x288 해상도',
        '- "try HybrIK" — 측면 약함 확인 시 path 전환 (Option A, MIT)',
        '- "accept limitation, proceed to Plan 11 with 4/5 rule" — sideway-spin 보강 포기',
    ]

    return "\n".join(lines) + "\n"


def _print_summary(result: dict) -> None:
    lifter = result.get("lifter", {})
    nlf = result.get("nlf", {})
    gap = result.get("gap", {})
    verdict = result.get("verdict", "unknown")

    def _f(v):
        return f"{v:.1f}" if v is not None else "N/A"

    print()
    print("=== spike_rtmpose 결과 ===")
    print(f"  모션: {result.get('motion', 'N/A')}")
    print(f"  프레임: {result.get('frames_total', 'N/A')}")
    print(f"  detector: {result.get('detector', 'N/A')}")
    print()
    print(f"  {'항목':<12}  {'RTMPose+MB':>12}  {'NLF':>8}  {'갭':>6}")
    print(f"  {'-'*12}  {'-'*12}  {'-'*8}  {'-'*6}")
    print(f"  {'overall':<12}  {_f(lifter.get('overall')):>12}  {_f(nlf.get('overall')):>8}  {_f(gap.get('overall')):>6}")
    for dim in ["stability", "line", "angle"]:
        l_v = lifter.get("dimensions", {}).get(dim)
        n_v = nlf.get("dimensions", {}).get(dim)
        g_v = gap.get("dimensions", {}).get(dim)
        print(f"  {dim:<12}  {_f(l_v):>12}  {_f(n_v):>8}  {_f(g_v):>6}")
    print()
    print(f"  ms/frame (lifter): {_f(lifter.get('ms_per_frame'))}")
    print(f"  ms/frame (NLF):    {_f(nlf.get('ms_per_frame'))}")
    print(f"  avg_rtm_score:     {lifter.get('avg_rtm_score', 'N/A')}")
    print()
    print(f"  판정: {verdict.upper()}")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(
        description="RTMPose 2D + MotionBERT 3D lift 스파이크 (Plan 01-10)."
    )

    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--motion", type=str, help="motion_id (S3: reference/{motion}.mp4)")
    src.add_argument("--video", type=str, dest="video_path", help="로컬 영상 파일 경로")

    parser.add_argument(
        "--bucket",
        default="sunity-motion-pilot-videos",
        help="S3 버킷 이름 (기본: sunity-motion-pilot-videos)",
    )
    parser.add_argument(
        "--rtmpose-config",
        required=True,
        help="RTMPose config (.py) 파일 경로 또는 mmpose 이름",
    )
    parser.add_argument(
        "--rtmpose-checkpoint",
        required=True,
        help="RTMPose pretrained 가중치 (.pth) 경로",
    )
    parser.add_argument(
        "--det-model",
        default="rtmdet-nano",
        help="사람 detector alias (기본: rtmdet-nano)",
    )
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=DEFAULT_SCORE_THRESHOLD,
        help=f"RTMPose keypoint score 임계값, 미만은 NaN 처리 (기본: {DEFAULT_SCORE_THRESHOLD})",
    )
    parser.add_argument(
        "--motionbert-root",
        default="/workspace/MotionBERT",
        help="MotionBERT 저장소 루트 경로",
    )
    parser.add_argument(
        "--motionbert-weights",
        default=None,
        help="MotionBERT 가중치 경로 (기본: {root}/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin)",
    )
    parser.add_argument("--out", default=None, help="JSON 결과 저장 경로")

    args = parser.parse_args()

    run_spike(
        motion=args.motion,
        bucket=args.bucket,
        rtmpose_config=args.rtmpose_config,
        rtmpose_checkpoint=args.rtmpose_checkpoint,
        motionbert_root=args.motionbert_root,
        motionbert_weights=args.motionbert_weights,
        video_path=args.video_path,
        det_model=args.det_model,
        score_threshold=args.score_threshold,
        out=args.out,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    main()
