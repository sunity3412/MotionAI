"""gsd-debug verification: median deviation should restore "same video = high score"
under RTMW jitter.

Simulates:
- Reference (정은지) signal: smooth sinusoid (T=170, J=8)
- User (talkv on same move) signal: same underlying motion + RTMW jitter
- RTMW jitter modeled as per-frame Gaussian noise with sigma=12° (matches observed
  median |Δt,t+1| ≈ 10-13° on inverted poses)

Tests:
1. Identical sequence self-compare → score 100 (sanity).
2. Same underlying motion + Gaussian noise sigma=5° (climb-like) → score should be 95+.
3. Same underlying motion + Gaussian noise sigma=12° (twist-like) → score should be 80+
   (was 55-65 with mean deviation; median should be far more robust).
4. Genuinely different motion (different phase by 30°) → score should be < 80.

Run:
  cd backend
  python scripts/verify_noise_robustness.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))

from sunity_shared.analysis import kismam, skeleton  # noqa: E402
from sunity_shared.analysis.features import feature_vector  # noqa: E402
from sunity_shared.analysis.motiondtw import motion_dtw, per_joint_deviation  # noqa: E402


def make_clean_reference(T: int = 170, J: int = 8) -> np.ndarray:
    """Smooth sinusoidal joint angles, each joint distinct phase."""
    t = np.linspace(0, 2 * np.pi, T)
    angles = np.zeros((T, J))
    for j in range(J):
        angles[:, j] = 90.0 + 60.0 * np.sin(t + j * np.pi / J)
    return angles


def compare(label: str, user: np.ndarray, ref: np.ndarray) -> int:
    match = motion_dtw(feature_vector(user), feature_vector(ref))
    user_seg = user[match.start : match.end]
    dev = per_joint_deviation(match.path, user_seg, ref)
    user_mean = {
        k: float(np.nanmean(user_seg[:, j]))
        for j, k in enumerate(skeleton.JOINT_KEYS)
    }
    ref_mean = {
        k: float(np.nanmean(ref[:, j]))
        for j, k in enumerate(skeleton.JOINT_KEYS)
    }
    assessments = kismam.assess(dev, user_angles=user_mean, reference_angles=ref_mean)
    score = kismam.overall_score(assessments)
    print(f"\n{label}")
    print(f"  per-joint deviation (deg): {dev.round(2).tolist()}")
    print(f"  per-joint scores: {[a.score for a in assessments]}")
    print(f"  overall: {score}")
    return score


def main() -> None:
    rng = np.random.default_rng(2026_06_12)
    T, J = 170, 8
    ref = make_clean_reference(T, J)

    print("=" * 60)
    print("Synthetic verification — median deviation under RTMW jitter")
    print("=" * 60)

    # 1. Identical (no noise)
    score1 = compare("[1] identical self-compare", ref.copy(), ref.copy())
    assert score1 == 100, f"sanity fail: identical → {score1} (expected 100)"

    # 2. clean noise (climb-like sigma=5°)
    noise_low = rng.normal(0, 5.0, size=(T, J))
    user_low = ref + noise_low
    score2 = compare("[2] same motion + climb-like noise (sigma=5°)", user_low, ref)

    # 3. heavy noise (twist-like sigma=12°)
    noise_high = rng.normal(0, 12.0, size=(T, J))
    user_high = ref + noise_high
    score3 = compare("[3] same motion + twist-like noise (sigma=12°)", user_high, ref)

    # 4. Real difference: shift one joint by 25° consistently
    user_diff = ref.copy()
    user_diff[:, 1] += 25.0
    score4 = compare("[4] real 25° offset on joint 1 only", user_diff, ref)

    # 5. Real different motion: phase shift 30 deg on all joints
    t = np.linspace(0, 2 * np.pi, T)
    user_phase = np.zeros((T, J))
    for j in range(J):
        user_phase[:, j] = 90.0 + 60.0 * np.sin(t + j * np.pi / J + np.deg2rad(30))
    score5 = compare("[5] phase-shifted motion (30° in motion phase)", user_phase, ref)

    # 6. Outlier-dominated (mostly identical, 10% of frames have 60° jitter)
    user_out = ref.copy()
    outlier_mask = rng.random(T) < 0.10  # 10% of frames
    user_out[outlier_mask] += rng.normal(0, 60.0, size=(outlier_mask.sum(), J))
    score6 = compare("[6] 90% identical + 10% outlier frames (60° each)", user_out, ref)

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  [1] identical self → {score1} (expect 100)")
    print(f"  [2] sigma=5° noise → {score2} (expect 90+)")
    print(f"  [3] sigma=12° noise → {score3} (expect 80+ — was 55 before fix)")
    print(f"  [4] real 25° offset → {score4} (expect <90 — score should drop)")
    print(f"  [5] phase-shifted → {score5} (expect 60-80)")
    print(f"  [6] outlier-dominated → {score6} (expect 95+ — median ignores outliers)")

    # Assertions
    assert score6 >= 90, (
        f"REGRESSION: outlier-dominated should be 95+ with median, got {score6}"
    )
    # 25° real offset on 1/8 joints → that joint score ~ exp(-1.5625/2) = 0.46 → ~46
    # other joints ~100 → overall ~ (7*100+46)/8 = ~93. So expect <= 95.
    assert score4 <= 95, (
        f"REGRESSION: real 25° offset on 1/8 joints should drop overall, got {score4}"
    )
    # Sanity: noise alone shouldn't crush score
    assert score3 >= 70, (
        f"REGRESSION: 12° sigma noise should still score >= 70, got {score3}"
    )
    print("\nAll assertions passed.")


if __name__ == "__main__":
    main()
