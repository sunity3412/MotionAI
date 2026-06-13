"""Spike 002d 실행 — 현 운영 stack 의 baseline 정확도 박제.

Spike 001 (eval harness) 의 PathOutput 형식으로 wrap → axis_a/b/c 산출 비교 기준점.

실제 RTMW 호출은 RunPod 위임 박제. local skeleton 단계 = synthetic confidence
fixture 로 baseline 의 약점 (occlusion-prone phase 의 낮은 confidence) 시뮬레이션.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

# Spike 001 의 metrics 모듈 재사용
sys.path.insert(
    0, str(Path(__file__).parent.parent / "001-dataset-eval-harness")
)
from metrics import PathOutput, evaluate_4way  # noqa: E402


def make_baseline_rtmw_only_path() -> PathOutput:
    """
    현 운영 stack 의 baseline 시뮬레이션.

    핵심 특성:
    - occlusion-prone phase (회전 / 거꾸로 매달림 / 측면) 에서 confidence ↓
    - 좌우 mirror augmentation 만 적용 (이미 운영 중인 가벼운 후처리)
    - 시간축 보간 (temporal.py 의 confidence 가중 평균)
    """
    n_frames = 60
    rng = np.random.default_rng(seed=42)

    # 정은지 je-04 (페어 스핀, motion_category="spin") 시뮬
    # 회전 phase = frame 20~40 = occlusion 빈번 → confidence ↓
    confidence = np.full((n_frames, 17), 0.7)
    confidence[20:40, [11, 12, 13, 14]] = rng.uniform(
        0.15, 0.35, size=(20, 4)
    )  # hip/knee occlusion
    confidence[10:25, [9, 10]] = rng.uniform(0.20, 0.40, size=(15, 2))  # wrist occlusion

    # joint sequence — 시뮬
    joints = rng.normal(loc=0.0, scale=0.1, size=(n_frames, 17, 3))
    # 회전 동작 fixture (yaw spin)
    for t in range(n_frames):
        angle = t * 6.0 * np.pi / 180.0  # 360° / 60 frame
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        joints[t, 11] = [-0.1 * cos_a, 1.0, -0.1 * sin_a]
        joints[t, 12] = [+0.1 * cos_a, 1.0, +0.1 * sin_a]
        joints[t, 13] = [-0.4 * cos_a, 1.0, -0.4 * sin_a]
        joints[t, 14] = [+0.4 * cos_a, 1.0, +0.4 * sin_a]

    return PathOutput(
        path_name="rtmw_mirror",
        joint_sequence=joints,
        confidence_sequence=confidence,
        fps=30.0,
        video_id="je-04",
        motion_category="spin",
        notes=[
            "현 운영 stack baseline (RTMW + 좌우 mirror + temporal.py)",
            "occlusion phase 시뮬: frame 20~40 hip/knee, frame 10~25 wrist",
            "회전 동작 (페어 스핀) 시뮬",
        ],
    )


def smoke_test() -> None:
    print("=" * 60)
    print("Spike 002d: rtmw-mirror-baseline smoke test")
    print("=" * 60)

    baseline = make_baseline_rtmw_only_path()
    print(f"\n[Baseline 박제]")
    print(f"  video_id: {baseline.video_id}")
    print(f"  motion: {baseline.motion_category}")
    print(f"  fps: {baseline.fps}")
    print(f"  notes:")
    for note in baseline.notes:
        print(f"    - {note}")

    # confidence 분포
    print(f"\n[Confidence 분포]")
    print(f"  mean: {baseline.confidence_sequence.mean():.3f}")
    print(f"  min:  {baseline.confidence_sequence.min():.3f}")
    print(f"  max:  {baseline.confidence_sequence.max():.3f}")
    print(f"  < 0.3 frame rate: {np.mean(baseline.confidence_sequence < 0.3):.3f}")

    # occlusion-prone phase 박제
    print(f"\n[Occlusion-prone phase 박제]")
    for f_start, f_end, joints_idx, label in [
        (20, 40, [11, 12, 13, 14], "spin phase - hip/knee occlusion"),
        (10, 25, [9, 10], "wrist occlusion phase"),
    ]:
        rate = np.mean(
            baseline.confidence_sequence[f_start:f_end, joints_idx] < 0.3
        )
        print(f"  frame {f_start}~{f_end} joints {joints_idx} ({label})")
        print(f"    → confidence < 0.3 rate: {rate:.3f}")

    # 1-way 평가 (baseline only — full 4-way 는 002b RunPod 결과와 함께)
    outputs = {"rtmw_mirror": baseline}
    split_frames = []  # spin motion → split frames N/A
    criterion_frames = {
        "fully_extended": list(range(0, 60, 5)),
        "twist_alignment": list(range(20, 40)),
    }

    report = evaluate_4way(
        outputs=outputs,
        split_frame_indices=split_frames,
        criterion_frames=criterion_frames,
        baseline_path_name="rtmw_mirror",
    )

    print(f"\n[Baseline 자기 자신 평가 (axis_a 미적용 — split motion 아님)]")
    print(f"  axis_b occlusion_frame_rate: {report.axis_b['rtmw_mirror']['occlusion_frame_rate']:.3f}")
    print(f"  axis_c twist_alignment: {report.axis_c['rtmw_mirror']['twist_alignment']:.3f}")
    print(f"  axis_c fully_extended: {report.axis_c['rtmw_mirror']['fully_extended']:.3f}")

    # IPSF 추정 감점 (baseline 의 약점 정량화)
    occlusion_count = float(np.sum(baseline.confidence_sequence < 0.3)) / 5.0
    ipsf_penalty = occlusion_count * 0.5  # IPSF Page 10/94/106
    print(f"\n[IPSF Page 10/94/106 추정 감점 (baseline)]")
    print(f"  occurrence (rough) = {occlusion_count:.1f}")
    print(f"  estimated penalty = -{ipsf_penalty:.2f} pts")
    print(f"  → 002b cylindrical mesh path 가 이 감점을 절감 → 정량화 대상")

    # 박제
    spike_report = {
        "spike": "002d-rtmw-mirror-baseline",
        "purpose": "현 운영 stack 의 IPSF 채점 약점 정량화 + 002b 대비 baseline 박제",
        "baseline_path": baseline.path_name,
        "video_id": baseline.video_id,
        "motion_category": baseline.motion_category,
        "occlusion_frame_rate": float(np.mean(baseline.confidence_sequence < 0.3)),
        "estimated_ipsf_penalty_pts": ipsf_penalty,
        "axis_b_baseline": report.axis_b,
        "axis_c_baseline": report.axis_c,
        "notes": [
            "Spike 001 PathOutput 재사용 — eval harness 호환 검증 ✓",
            "회전 동작 시뮬: 운영 stack 의 spin phase 약점 박제",
            "실 운영 stack 결과는 RunPod 위임 (별도 task)",
        ],
    }
    with open("spike_report.json", "w") as f:
        json.dump(spike_report, f, indent=2)
    print("\n✓ spike_report.json 박제")


if __name__ == "__main__":
    smoke_test()
