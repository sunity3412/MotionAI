"""Plan 08.1-01 Wave 1 Task 2 — 정은지 sweep tilt 분포 → tilt_thresholds.yaml.

schema_v2 (calibration_method='elite_p100_plus_margin') 박제. P100 + margin 방식
(P90 폐기, Codex iteration 2 C-H2 정합). nested operational_cutoff 박제.

source 분기 (--source-type):
  - firestore (default) — Phase 8 inherited sweep_phase8_1780986673
  - repo-artifact — .planning/phases/08.1-axis-metric-redesign/08.1-CALIBRATION-SOURCE.json
  - wave2-explicit — Wave 2 자기 sweep 재calibrate. --allow-recalibrate 명시 강제
    (circular threshold chasing 차단)

preflight hard gate (C-H3 정합):
  - 25 axisMetric instance 모두 non-null shoulderTilt + non-null hipTilt
  - 'phase_8_1_wave_0_transitional' 부재 (Pod 재배포 완료 검증)
  - 'tilt_unavailable' 부재
  위반 시 RuntimeError + 명시 메시지.

D-04 future re-run entry point (W11 정합) — belle 가 정은지 추가 영상 확보 시 본
script 재실행 → yaml update + commit. zero-code-change (value-only) — schema
변경 시는 별도 plan 박제 schema_version bump.

usage:
    PYTHONPATH=backend/shared/python python backend/scripts/calibrate_tilt_thresholds.py \\
      --sweep-uid sweep_phase8_1780986673 \\
      --source-type firestore

per Plan 08.1-01 must_haves Step 1 (Task 2).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

SCHEMA_VERSION = 2
CALIBRATION_METHOD = "elite_p100_plus_margin"
CALIBRATION_VERSION = "1.1"
IPSF_TOLERANCE_DEG = 20.0
IPSF_MAJOR_FAULT_DEG = 40.0
IPSF_SOURCE_REF = (
    "NotebookLM citation 9 Page 87 Glossary + "
    "Aerial Pole CoP Page 63 S55 Iron X (±20°)"
)


def _load_records(args) -> list[dict]:
    """Source 분기 load — 5 doc record 표준 형태 (id + data dict)."""
    if args.source_type == "firestore":
        from sunity_shared import firestore_admin

        fs = firestore_admin._db()
        docs = list(fs.collection(f"users/{args.sweep_uid}/analyses").stream())
        return [{"doc_id": d.id, "data": d.to_dict() or {}} for d in docs]
    if args.source_type == "repo-artifact":
        if not args.source_path:
            raise RuntimeError("--source-path required for repo-artifact source")
        return json.loads(Path(args.source_path).read_text())
    if args.source_type == "wave2-explicit":
        if not args.allow_recalibrate:
            raise RuntimeError(
                "wave2-explicit requires --allow-recalibrate "
                "(circular threshold chasing 차단)"
            )
        from sunity_shared import firestore_admin

        fs = firestore_admin._db()
        docs = list(fs.collection(f"users/{args.sweep_uid}/analyses").stream())
        return [{"doc_id": d.id, "data": d.to_dict() or {}} for d in docs]
    raise ValueError(f"unknown source_type={args.source_type!r}")


def _preflight_calibration_source(records: list[dict]) -> list[str]:
    """C-H3 hard gate — 25 non-null + transitional 부재 검증. doc_ids 반환.

    Raises:
        RuntimeError: 위반 시 명시 메시지 with 위반 doc_id.
    """
    if len(records) != 5:
        raise RuntimeError(
            f"expected 5 docs (5 videos), got {len(records)}"
        )
    doc_ids: list[str] = []
    for r in records:
        d = r["data"]
        ax = ((d.get("result") or {}).get("forceSignalsReport") or {}).get(
            "axisMetrics"
        ) or []
        if len(ax) != 5:
            raise RuntimeError(
                f"expected 5 phases per doc, got {len(ax)} in {r['doc_id']}"
            )
        for m in ax:
            if m.get("shoulderTilt") is None:
                raise RuntimeError(
                    f"null shoulderTilt in {r['doc_id']} "
                    f"(Wave 0 stub 또는 미배포 sweep)"
                )
            if m.get("hipTilt") is None:
                raise RuntimeError(f"null hipTilt in {r['doc_id']}")
            warns = m.get("warnings") or []
            if "phase_8_1_wave_0_transitional" in warns:
                raise RuntimeError(
                    f"transitional warning in {r['doc_id']} (Pod 재배포 미완)"
                )
            if "tilt_unavailable" in warns:
                raise RuntimeError(f"tilt_unavailable in {r['doc_id']}")
        doc_ids.append(r["doc_id"])
    return doc_ids


def _extract_tilts(records: list[dict]) -> tuple[list[float], list[float]]:
    """25 data point (5 videos × 5 phases) shoulder/hip tilt 추출.

    Wave 1 본체 의 산출 정합 — 값은 이미 unsigned [0, 90] (C-M1 정합).
    """
    shoulder_vals: list[float] = []
    hip_vals: list[float] = []
    for r in records:
        ax = (
            (r["data"].get("result") or {}).get("forceSignalsReport") or {}
        ).get("axisMetrics") or []
        for m in ax:
            shoulder_vals.append(float(m["shoulderTilt"]))
            hip_vals.append(float(m["hipTilt"]))
    return shoulder_vals, hip_vals


def _percentiles(vals: list[float]) -> dict[str, float]:
    """P25/P50/P75/P90/P100 산출."""
    return {
        "p25": float(np.percentile(vals, 25)),
        "p50": float(np.percentile(vals, 50)),
        "p75": float(np.percentile(vals, 75)),
        "p90": float(np.percentile(vals, 90)),
        "p100": float(np.max(vals)),
    }


def _compute_operational_cutoff(
    dist: dict[str, float], margin_deg: float
) -> tuple[float, float]:
    """P100 + margin → medium / high cutoff (Codex C-H2 정합).

    medium_cutoff_deg = max(P100 + margin, ipsf_tolerance.tolerance_deg)
    high_cutoff_deg = max(medium * 1.5, ipsf_tolerance.major_fault_deg)
    """
    medium = max(dist["p100"] + margin_deg, IPSF_TOLERANCE_DEG)
    high = max(medium * 1.5, IPSF_MAJOR_FAULT_DEG)
    return float(medium), float(high)


def _build_yaml_data(
    *,
    sweep_uid: str,
    sample_size: int,
    doc_ids: list[str],
    margin_deg: float,
    shoulder_dist: dict[str, float],
    hip_dist: dict[str, float],
    shoulder_cutoff: tuple[float, float],
    hip_cutoff: tuple[float, float],
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "calibration_method": CALIBRATION_METHOD,
        "calibration_version": CALIBRATION_VERSION,
        "calibrated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "sweep_uid": sweep_uid,
            "sample_size": sample_size,
            "source_doc_ids": doc_ids,
            "null_tilt_verified": True,
            "margin_deg": margin_deg,
        },
        "shoulder_tilt": {
            "distribution": shoulder_dist,
            "operational_cutoff": {
                "medium_cutoff_deg": shoulder_cutoff[0],
                "high_cutoff_deg": shoulder_cutoff[1],
            },
        },
        "hip_tilt": {
            "distribution": hip_dist,
            "operational_cutoff": {
                "medium_cutoff_deg": hip_cutoff[0],
                "high_cutoff_deg": hip_cutoff[1],
            },
        },
        "ipsf_tolerance": {
            "source_ref": IPSF_SOURCE_REF,
            "tolerance_deg": IPSF_TOLERANCE_DEG,
            "major_fault_deg": IPSF_MAJOR_FAULT_DEG,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="정은지 sweep tilt 분포 → tilt_thresholds.yaml (Plan 08.1-01 Wave 1 Task 2)"
    )
    parser.add_argument("--sweep-uid", default="sweep_phase8_1780986673")
    parser.add_argument(
        "--source-type",
        choices=["firestore", "repo-artifact", "wave2-explicit"],
        default="firestore",
    )
    parser.add_argument("--source-path")
    parser.add_argument(
        "--output-path",
        default="backend/judging_data/tilt_thresholds.yaml",
    )
    parser.add_argument("--margin-deg", type=float, default=5.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-recalibrate", action="store_true")
    args = parser.parse_args()

    records = _load_records(args)
    doc_ids = _preflight_calibration_source(records)

    shoulder_vals, hip_vals = _extract_tilts(records)
    s_dist = _percentiles(shoulder_vals)
    h_dist = _percentiles(hip_vals)
    s_cutoff = _compute_operational_cutoff(s_dist, args.margin_deg)
    h_cutoff = _compute_operational_cutoff(h_dist, args.margin_deg)

    yaml_data = _build_yaml_data(
        sweep_uid=args.sweep_uid,
        sample_size=len(shoulder_vals),
        doc_ids=doc_ids,
        margin_deg=args.margin_deg,
        shoulder_dist=s_dist,
        hip_dist=h_dist,
        shoulder_cutoff=s_cutoff,
        hip_cutoff=h_cutoff,
    )

    print(
        f"sweep_uid={args.sweep_uid}  source_type={args.source_type}  "
        f"n={len(shoulder_vals)}"
    )
    print(
        f"shoulder dist={s_dist}  -> medium={s_cutoff[0]:.2f}° "
        f"high={s_cutoff[1]:.2f}°"
    )
    print(
        f"hip      dist={h_dist}  -> medium={h_cutoff[0]:.2f}° "
        f"high={h_cutoff[1]:.2f}°"
    )

    if not args.dry_run:
        out = Path(args.output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            yaml.safe_dump(yaml_data, f, sort_keys=False, default_flow_style=False)
        print(f"WROTE {out}")
    else:
        print("DRY RUN — yaml 미저장.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
