"""측정 신뢰도 frame-by-frame trace spike (Plan 01-16).

Plan 01-13 verdict `measurement_unreliable_blocked` (2026-06-01) 후속 path A —
ref-invert hold frame 88 단일 frame 측정 결과 = 정은지 (폴스포츠 세계챔피언) invert
split peak hold 자세에서 right_shoulder 18.2도 / left_hip 54.9도 / right_knee 73도
같은 인체학적 비정상 + 5/5 minimum fail. 동일 영상 Plan 08 (MP+MB) frame-mean overall
92 / Plan 11 (RTMPose+MB) frame-mean overall 70 / Plan 13 (RTMPose+MB) hold frame 88
5/5 fail = 4-5배 cross-engine inconsistency. 각도 컨벤션 (compute_joint_angles inner
angle 0-180도, 180도 = 완전 신전) IPSF target 일치 확인됨 — 컨벤션 미스매치 아님.
측정값 자체가 root cause.

본 spike 의 4 가설 trace path (Plan 13 SUMMARY 박제):

| # | 가설                                              | trace path                                         |
|---|---------------------------------------------------|----------------------------------------------------|
| (a) | Gemini frame_idx=88 정확도 — hold 정점 아닌 transition | hold_window (88±5) 평균 vs frame 88 단일 비교       |
| (b) | RTMPose+MB lift 단일 frame 좌우 noise 폭주          | RTMPose+MB frame 별 |L-R| 비대칭 trace, 평균 baseline |
| (c) | lifter occlusion 자세 좌우 keypoint 헷갈림           | RTMPose+MB vs MP+MB 좌우 매핑 swap detection       |
| (d) | RTMPose+MB lift 자체가 invert family 부적합          | RTMPose+MB vs MP+MB frame-by-frame 각도 disagreement |

단일 카메라 단독 박제 — memory `single-camera-first-multi-view-last.md` (2026-06-01)
영구 자동 제외. 본 spike / 권고 / 분기 어디서도 추가 view 옵션 0건. belle 명시
지시 시에만 재진입.

NLF 호출 0 — Plan 12 (c) verdict 후 영구 폐기 (memory `license-blocklist-pose.md` +
Plan 13 박제). 본 spike 의 측정 비교군 = RTMPose+MB + MediaPipe+MB 두 path 만.

라이선스:
  MediaPipe                : Apache 2.0
  MotionBERT               : MIT
  RTMPose / mmpose / mmcv  : Apache 2.0
  본 spike                 : 운영 코드베이스 라이선스와 동일

운영 코드 / Plan 13 모듈 / Plan 15 데이터 / 기존 spike 8개 모두 무수정 (PLAN 16
must_haves 박제). 본 spike 는 함수 import + 호출만 (spike_rtmpose / mediapipe_to_h36m17 /
spike_motionbert / 공유 features / temporal / skeleton). Gemini SDK 호출 0 (frame_idx=88
박제 상수만 사용).

8 angle joints (skeleton.JOINT_KEYS = left/right × elbow/shoulder/hip/knee) 만 trace —
derive joint (hip center/spine/thorax/neck_nose/head) 미사용. Plan 12 (d) verdict
(RTMPose H36M ordering vs NLF COCO ordering 17/17 다름) 회피 유지.

실행 — report-only mode (로컬 OK, mmpose/torch/mediapipe 미설치 환경):
  python3 -m backend.research.spikes.spike_measurement_trace \\
    --mode report-only --motion ref-invert

실행 — live mode (belle Pod 전용, ref-invert 단독, ~5분):
  python3 -m backend.research.spikes.spike_measurement_trace \\
    --mode live --motion ref-invert --frame-index 88 --hold-window 5 \\
    --rtmpose-config /workspace/rtmpose_weights/rtmpose-l_8xb256-420e_coco-256x192.py \\
    --rtmpose-checkpoint /workspace/rtmpose_weights/rtmpose-l_simcc-coco_pt-aic-coco_420e-256x192-1352a4d2_20230127.pth \\
    --motionbert-root /workspace/MotionBERT \\
    --motionbert-weights /workspace/MotionBERT/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# skeleton 만 모듈-load 시점 import — features / temporal 은 함수 본문에서 import
# (numpy 만 필요, heavy deps 0). spike_rtmpose / mediapipe_to_h36m17 /
# spike_motionbert 는 live helper 안에서 lazy import (모듈-load 시점 mmpose / torch /
# mediapipe import 0 유지).
from sunity_shared.analysis.skeleton import JOINT_KEYS


# ── 4 가설 verdict 임계 (모듈 상수, rationale) ──────────────────────────────────

# (a) Gemini frame_idx 정확도 — frame 88 단일과 hold_window (88±5) 11 frame 평균
# 의 8 joint 평균 절대 차이. >=30도 면 단일 frame sampling 이 직접 원인.
HYPOTHESIS_A_FRAME_VS_WINDOW_STRONG_DEG = 30.0
HYPOTHESIS_A_WEAK_DEG = 10.0

# (b) RTMPose+MB 단일 lift 좌우 noise — 영상 전체 4 pair |L - R| 평균. >=40도 면
# Plan 13 frame 88 의 left vs right delta 60-70도 와 직접 일치.
HYPOTHESIS_B_LR_ASYMMETRY_STRONG_DEG = 40.0
HYPOTHESIS_B_WEAK_DEG = 15.0

# (c) lifter occlusion 자세 좌우 keypoint 헷갈림 — RTMPose+MB 와 MP+MB 두 path
# 에서 좌/우 joint 의 부호 (L > R vs L < R) 가 반대인 frame 비율. >=0.30 (30%)
# 면 occlusion 자세에서 좌우 매핑 swap 빈발.
HYPOTHESIS_C_LR_SWAP_FRAME_RATIO_STRONG = 0.30
HYPOTHESIS_C_WEAK_RATIO = 0.10

# (d) RTMPose+MB vs MP+MB cross-engine — frame 별 8 joint 평균 disagreement.
# >=30도 면 두 lift 가 invert family 에서 불일치 (Plan 12 (e) 두 엔진 3D 분포
# strong distance 220+ 와 직접 연결).
HYPOTHESIS_D_CROSS_ENGINE_DISAGREEMENT_STRONG_DEG = 30.0
HYPOTHESIS_D_WEAK_DEG = 10.0

# Plan 13 박제 입력 — Gemini key moment frame_idx (ref-invert hold).
PLAN_13_FRAME_INDEX = 88
# hold_window = frame ±5 (11 frame). dimensions.py 의 hold_window 동등.
PLAN_13_HOLD_WINDOW = 5

# Cross-engine inconsistency baseline (Plan 08 / Plan 11 frame-mean overall).
PLAN_08_MP_MB_REF_INVERT_OVERALL = 92.0
PLAN_11_RTMPOSE_MB_REF_INVERT_OVERALL = 70.0

# 기본 motion — Plan 15 1차 박제된 유일 motion (ref-invert 5 hold entries).
DEFAULT_MOTION = "ref-invert"

# Engine tag string — JSON top-level engines dict 키와 일관.
ENGINE_RTMPOSE_MB = "rtmpose_mb"
ENGINE_MEDIAPIPE_MB = "mediapipe_mb"


# ── 4 LR pair tuple (skeleton.JOINT_KEYS 8 joint 와 정합) ─────────────────────

# 8 angle joint 를 좌우 4 쌍으로 묶는다 — Plan 16 must_haves "8 angle joints 만"
# 박제. 인덱스는 skeleton.JOINT_KEYS 순서 기준 — 모듈 로드 시 정합 검증.
LR_PAIRS: tuple[tuple[str, str], ...] = (
    ("left_elbow", "right_elbow"),
    ("left_shoulder", "right_shoulder"),
    ("left_hip", "right_hip"),
    ("left_knee", "right_knee"),
)


def _assert_lr_pair_integrity() -> None:
    """LR_PAIRS 가 skeleton.JOINT_KEYS 8 joint 와 정합인지 module-load 시 검증.

    정합이 깨지면 본 spike 의 좌우 비대칭 / cross-engine swap 결과가 의미를
    잃으므로 fail-loud. Plan 12 (d) keypoint mapping 회피와 같은 패턴.
    """
    flat = tuple(j for pair in LR_PAIRS for j in pair)
    if set(flat) != set(JOINT_KEYS):
        raise RuntimeError(
            "LR_PAIRS 와 skeleton.JOINT_KEYS 정합 깨짐 — "
            f"LR_PAIRS flat={flat}, JOINT_KEYS={JOINT_KEYS}"
        )
    if len(flat) != len(JOINT_KEYS):
        raise RuntimeError(
            "LR_PAIRS 가 8 joint 를 정확히 4 쌍으로 덮지 않음 — "
            f"len={len(flat)} vs JOINT_KEYS={len(JOINT_KEYS)}"
        )


_assert_lr_pair_integrity()


# ── argparse parser ───────────────────────────────────────────────────────────


def _default_out_path() -> Path:
    """기본 출력 경로 (UTC ISO 8601 timestamp, reports/ 아래)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("backend/research/spikes/reports") / f"spike_measurement_trace_{ts}.json"


def build_arg_parser() -> argparse.ArgumentParser:
    """CLI argparse parser 빌더 (smoke 테스트 재사용 위해 분리).

    Plan 16 T-1-5 CLI surface — 10 args. report-only 모드는 mmpose / torch /
    mediapipe 미설치 환경에서도 e2e 동작 (stub angles fixture). live 모드는
    belle Pod 전용 — ref-invert 단독 ~5분 (RTMPose+MB ~3분 + MP+MB ~2분).
    """
    parser = argparse.ArgumentParser(
        description=(
            "측정 신뢰도 frame-by-frame trace spike (Plan 01-16). "
            "Plan 13 verdict measurement_unreliable_blocked 후속 path A — "
            "ref-invert 단독 + RTMPose+MB / MP+MB 두 lift path + 4 가설 (a/b/c/d) verdict."
        )
    )
    parser.add_argument(
        "--mode",
        choices=["report-only", "live"],
        default="report-only",
        help=(
            "report-only (기본): stub angles fixture e2e — mmpose/torch/mediapipe 미import. "
            "live: belle Pod 전용 — 두 lift path 직렬 실행 ~5분."
        ),
    )
    parser.add_argument(
        "--motion",
        default=DEFAULT_MOTION,
        help=(
            f"motion_id (S3: reference/<motion>.mp4). 기본: {DEFAULT_MOTION} "
            "— Plan 15 1차 박제된 유일 motion (5 hold entries)."
        ),
    )
    parser.add_argument(
        "--frame-index",
        type=int,
        default=PLAN_13_FRAME_INDEX,
        help=(
            f"hold 시점 frame index. 기본: {PLAN_13_FRAME_INDEX} "
            "(Plan 13 Gemini moment 결과 박제 — ref-invert hold)."
        ),
    )
    parser.add_argument(
        "--hold-window",
        type=int,
        default=PLAN_13_HOLD_WINDOW,
        help=(
            f"frame_index 주변 ±N frame 평균 윈도우. 기본: {PLAN_13_HOLD_WINDOW} "
            "(dimensions.py hold_window 동등, 11 frame)."
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
        help="MotionBERT 저장소 루트 경로 (live mode).",
    )
    parser.add_argument(
        "--motionbert-weights",
        default=None,
        help=(
            "MotionBERT 가중치 경로 (live mode 필수). None 이면 "
            "{root}/checkpoint/pose3d/FT_MB_lite_MB_ft_h36m_global_lite/best_epoch.bin"
        ),
    )
    parser.add_argument(
        "--out",
        default=None,
        help=(
            "JSON 결과 저장 경로. None 이면 "
            "backend/research/spikes/reports/spike_measurement_trace_<UTC>.json 자동 생성. "
            ".md sibling 도 같이 생성."
        ),
    )
    return parser


# ── 두 lift path 골격 분기 (helper 함수는 T-2/T-3/T-4 에서 추가) ────────────────


def run_trace(args: argparse.Namespace) -> dict[str, Any]:
    """본 spike 의 진입점 — argparse 결과 받아 두 lift path trace 수행.

    골격 (T-1):
      - report-only mode: stub angles fixture 두 set (RTMPose+MB / MP+MB) 생성 →
        T-2/T-3 helper 호출 → JSON dict 반환.
      - live mode: lazy import spike_rtmpose / mediapipe_to_h36m17 / spike_motionbert →
        두 lift path 직렬 실행 → 동일 helper chain.

    본 함수 본체는 T-4 에서 stub fixture + helper chain 완성. T-1 단계에서는
    골격 + live mode guard 만 박제 (rtmpose-config / rtmpose-checkpoint /
    motionbert-weights 누락 시 ValueError).
    """
    if args.mode == "live":
        # live mode guard — Pod 전용 인자 누락 시 fail-loud (belle 가 빠뜨려도
        # mmpose 가 늦게 폭발하는 대신 진입 단계에서 멈춤).
        missing = []
        if args.rtmpose_config is None:
            missing.append("--rtmpose-config")
        if args.rtmpose_checkpoint is None:
            missing.append("--rtmpose-checkpoint")
        if args.motionbert_weights is None and not args.motionbert_root:
            missing.append("--motionbert-weights")
        if missing:
            raise ValueError(
                f"live mode 필수 인자 누락: {', '.join(missing)}. "
                "belle Pod 절차 README Plan 16 섹션 참조."
            )

    # T-4 가 완성 — T-1 단계에서는 진입 가능성만 박제.
    raise NotImplementedError(
        "run_trace 본체는 T-4 에서 완성됩니다. T-1 = CLI + 모듈 상수 박제."
    )


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    """CLI 진입점 — T-4 에서 JSON dump + sibling Markdown 출력 완성."""
    parser = build_arg_parser()
    args = parser.parse_args()
    run_trace(args)  # T-4 가 완성
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
