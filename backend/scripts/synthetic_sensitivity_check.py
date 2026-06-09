#!/usr/bin/env python3
"""Plan 08.1-02 Task 2.5 — synthetic sensitivity check.

Why (C-M3, iteration 2):
  정은지 25/25 'low' 만 acceptance 면 "threshold 너무 높아 아무것도 안 잡힘"
  위험. negative evidence 동시 검증 = metric validity 증명.

5 synthetic case (yaml load → shoulder/hip cutoffs):
  1. Just above medium: shoulder=medium_cutoff+1, hip=0 → expected 'medium'
  2. Just below medium: shoulder=medium_cutoff-1, hip=0 → expected 'low'
  3. At boundary: shoulder=medium_cutoff, hip=0 → expected 'low' (boundary-low rule)
  4. Above high: shoulder=high_cutoff+1, hip=0 → expected 'high'
  5. Hip high: shoulder=0, hip=hip_high_cutoff+10 → expected 'high'

5/5 PASS exit 0, 1개라도 FAIL exit 1 + stdout 표 출력.
SWEEP-EVIDENCE §11 박제 source.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "shared" / "python"))

from sunity_shared.analysis.force_signals import (  # noqa: E402
    _max_severity,
    _severity_from_tilt,
)

YAML_PATH = BACKEND / "judging_data" / "tilt_thresholds.yaml"


def _load_thresholds() -> tuple[tuple[float, float], tuple[float, float]]:
    data = yaml.safe_load(YAML_PATH.read_text())
    s = data["shoulder_tilt"]["operational_cutoff"]
    h = data["hip_tilt"]["operational_cutoff"]
    return (
        (float(s["medium_cutoff_deg"]), float(s["high_cutoff_deg"])),
        (float(h["medium_cutoff_deg"]), float(h["high_cutoff_deg"])),
    )


def _case_severity(
    shoulder_deg: float | None,
    hip_deg: float | None,
    shoulder_th: tuple[float, float],
    hip_th: tuple[float, float],
) -> str:
    """compute_axis_deviation 의 severity 산출 path 와 동일 — _max_severity."""
    return _max_severity(
        _severity_from_tilt(shoulder_deg, shoulder_th),
        _severity_from_tilt(hip_deg, hip_th),
    )


def main() -> int:
    shoulder_th, hip_th = _load_thresholds()
    sh_med, sh_high = shoulder_th
    hp_med, hp_high = hip_th

    cases = [
        ("Just above medium", sh_med + 1.0, 0.0, "medium"),
        ("Just below medium", sh_med - 1.0, 0.0, "low"),
        ("At boundary", sh_med, 0.0, "low"),  # boundary-low rule
        ("Above high", sh_high + 1.0, 0.0, "high"),
        ("Hip high", 0.0, hp_high + 10.0, "high"),
    ]

    print(f"\n[sensitivity] shoulder cutoffs: medium={sh_med:.2f}° high={sh_high:.2f}°")
    print(f"[sensitivity] hip cutoffs:      medium={hp_med:.2f}° high={hp_high:.2f}°\n")

    fmt = "| {:<22} | {:>14} | {:>10} | {:<18} | {:<18} | {:<5} |"
    print(fmt.format("Case", "shoulder (deg)", "hip (deg)", "Expected", "Observed", "PASS"))
    print(fmt.format("-" * 22, "-" * 14, "-" * 10, "-" * 18, "-" * 18, "-" * 5))

    failures = 0
    for name, sh, hp, expected in cases:
        observed = _case_severity(sh, hp, shoulder_th, hip_th)
        passed = observed == expected
        if not passed:
            failures += 1
        print(
            fmt.format(
                name,
                f"{sh:.2f}",
                f"{hp:.2f}",
                expected,
                observed,
                "OK" if passed else "FAIL",
            )
        )

    print()
    if failures:
        print(f"[sensitivity] FAIL — {failures}/{len(cases)} cases mismatched")
        return 1
    print(f"[sensitivity] PASS — {len(cases)}/{len(cases)} cases matched expected severity")
    return 0


if __name__ == "__main__":
    sys.exit(main())
