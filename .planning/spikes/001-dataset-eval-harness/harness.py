"""Phase 4 spike 4-way 비교 entry — synthetic smoke test 로 harness 동작 검증.

실제 4-way 실행은 002a/b/c/d 에서 각 path 별 RTMW 재추론 결과를 PathOutput 으로
wrap 해서 evaluate_4way 호출. spike 001 단계에서는 random fixture 로 harness 가
동작하는지만 확인 (depth over speed — surprising finding 발견 시 metric 보강).

실행:
    python harness.py
"""
from __future__ import annotations

import json

import numpy as np

from dataset import JEONGEUNJI_5
from ipsf_criteria import ALL_CRITERIA, PHASE4_EVAL_AXIS_MAPPING
from metrics import PathOutput, evaluate_4way


def make_synthetic_path(
    path_name: str,
    video_id: str,
    motion_category: str,
    seed: int,
    n_frames: int = 60,
    fps: float = 30.0,
    base_confidence: float = 0.7,
) -> PathOutput:
    """smoke test fixture — random joints + confidence."""
    rng = np.random.default_rng(seed)
    joints = rng.normal(loc=0.0, scale=0.2, size=(n_frames, 17, 3))
    # leg 가 split 되도록 hip/knee/ankle 강제 박제 (axis_a 동작 검증용)
    joints[:, 11] = np.array([-0.15, 0.0, 0.0])  # hip_l
    joints[:, 12] = np.array([+0.15, 0.0, 0.0])  # hip_r
    joints[:, 13] = np.array([-0.55, -0.3, 0.0])  # knee_l
    joints[:, 14] = np.array([+0.55, -0.3, 0.0])  # knee_r
    joints[:, 15] = np.array([-0.95, -0.6, 0.0])  # ank_l
    joints[:, 16] = np.array([+0.95, -0.6, 0.0])  # ank_r

    # path 별 confidence 시뮬: rtmw_mirror = baseline (낮음), AI 합성 path = 높음
    if path_name == "rtmw_mirror":
        conf = rng.uniform(0.2, 0.9, size=(n_frames, 17))
    elif path_name == "higgsfield":
        conf = rng.uniform(0.4, 0.95, size=(n_frames, 17))  # 합성 view ↑
    elif path_name == "smplx_render":
        conf = rng.uniform(0.5, 0.97, size=(n_frames, 17))  # 자체 path ↑
    elif path_name == "magicman":
        conf = rng.uniform(0.45, 0.96, size=(n_frames, 17))
    else:
        conf = np.full((n_frames, 17), base_confidence)

    return PathOutput(
        path_name=path_name,
        joint_sequence=joints,
        confidence_sequence=conf,
        fps=fps,
        video_id=video_id,
        motion_category=motion_category,
    )


def smoke_test() -> None:
    """harness 가 4-way 비교 + 3 axis 산출 + IPSF mapping 출력하는지 확인."""
    print("=" * 60)
    print("Spike 001: dataset-eval-harness smoke test")
    print("=" * 60)

    # 정은지 je-03 (split) 영상 fixture
    meta = JEONGEUNJI_5[2]
    print(f"\n[Dataset] {meta.video_id} | {meta.motion_category} | {meta.motion_name_studio}")
    print(f"  notes: {meta.notes}")

    # 4-way path output fixture
    outputs = {
        "rtmw_mirror": make_synthetic_path("rtmw_mirror", meta.video_id, meta.motion_category, seed=1),
        "higgsfield": make_synthetic_path("higgsfield", meta.video_id, meta.motion_category, seed=2),
        "smplx_render": make_synthetic_path("smplx_render", meta.video_id, meta.motion_category, seed=3),
        "magicman": make_synthetic_path("magicman", meta.video_id, meta.motion_category, seed=4),
    }

    # split frame 박제 (synthetic 에서는 전체 frame split 가정)
    split_frames = list(range(0, 60, 5))  # 12 frames
    criterion_frames = {
        "fully_extended": list(range(0, 60, 3)),
        "twist_alignment": list(range(20, 40)),
    }

    report = evaluate_4way(
        outputs=outputs,
        split_frame_indices=split_frames,
        criterion_frames=criterion_frames,
        baseline_path_name="rtmw_mirror",
    )

    print("\n[Axis A] split angle 일관성 (IPSF Page 19)")
    for path, rate in report.axis_a.items():
        print(f"  {path:15s}  pass rate = {rate:.3f}")

    print("\n[Axis B] occlusion 보완 (IPSF Page 10/94/106)")
    for path, m in report.axis_b.items():
        print(
            f"  {path:15s}  occlusion={m['occlusion_frame_rate']:.3f}  "
            f"reduction={m['rate_reduction_pct']:+6.1f}%  "
            f"ipsf_savings={m['estimated_ipsf_savings_pts']:.2f}pts"
        )

    print("\n[Axis C] IPSF criterion 만족도")
    for path, m in report.axis_c.items():
        print(f"  {path:15s}  {m}")

    print("\n[Phase 4 평가 axis ↔ IPSF mapping]")
    for axis, criteria in PHASE4_EVAL_AXIS_MAPPING.items():
        print(f"  {axis}")
        for c in criteria:
            crit = ALL_CRITERIA[c]
            print(f"    └ {crit.name} | source: {crit.source_ref}")

    print("\n[Verdict 후보] (smoke test 결과는 fixture 라 production verdict 아님)")
    print("  - axis_a: smplx_render / higgsfield / magicman 모두 동일 (synthetic = 결정형)")
    print("  - axis_b: AI 합성 path 들이 baseline 대비 occlusion frame rate 감소")
    print("  - axis_c: capability check 만 — 실 데이터 필요")

    # JSON 출력 (CI / 후속 분석용)
    report_dict = {
        "video_id": report.video_id,
        "motion_category": report.motion_category,
        "axis_a": report.axis_a,
        "axis_b": report.axis_b,
        "axis_c": report.axis_c,
        "notes": report.notes,
    }
    with open("smoke_report.json", "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2, ensure_ascii=False)
    print("\n✓ smoke_report.json 박제")


if __name__ == "__main__":
    smoke_test()
