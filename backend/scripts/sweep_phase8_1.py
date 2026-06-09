#!/usr/bin/env python3
"""Phase 8.1 sweep CLI — 정은지 reference 5 영상 재sweep.

iteration 2 hygiene 박제 (C-M5):
  - epoch ms timestamps (Firestore evidence 정합)
  - commit hash 기록 (sweepCommitHash field)
  - tilt_thresholds.yaml checksum (sha256, thresholdChecksum field)
  - threshold version 검증 (schema_version=2 + calibration_method='elite_p100_plus_margin' 강제)
  - --allow-fallback flag (명시 fallback 모드 시만 version check 우회)
  - sweep_temp/ S3 객체 일괄 cleanup (lifecycle policy 대신 명시 삭제)
  - sourceLabel = 'sweep_phase8_1:<name>' 단순 유지 (metadata 는 별도 scalar fields)

CLI:
    python backend/scripts/sweep_phase8_1.py --sweep-uid sweep_phase8_1_<epoch_ms>

Codex iteration 3 정합 — 어떤 _process 실패 시 exit 1 + failures JSON dump.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

import boto3
import yaml

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "shared" / "python"))

YAML_PATH = BACKEND / "judging_data" / "tilt_thresholds.yaml"


def _load_pipeline():
    """Lazy-load pipeline module so --dry-run path can run without GPU/ffmpeg deps."""
    spec = importlib.util.spec_from_file_location(
        "sunity_pipeline_app", BACKEND / "functions" / "pipeline" / "app.py"
    )
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)
    pipeline._ensure_adapters()
    return pipeline


def _epoch_ms() -> int:
    return int(time.time() * 1000)


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(BACKEND.parent), text=True
    ).strip()


def _yaml_metadata(allow_fallback: bool) -> dict:
    """yaml schema_version + calibration_method 검증 + checksum 산출."""
    if not YAML_PATH.exists():
        if allow_fallback:
            return {
                "thresholdChecksum": None,
                "thresholdCalibrationMethod": "fallback",
                "thresholdCalibrationVersion": "fallback",
            }
        raise RuntimeError(
            f"tilt_thresholds.yaml not found at {YAML_PATH}. "
            "Run calibrate_tilt_thresholds.py first or pass --allow-fallback."
        )
    raw = YAML_PATH.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    data = yaml.safe_load(raw)
    schema_version = int(data.get("schema_version", 0))
    method = str(data.get("calibration_method", ""))
    if not allow_fallback:
        if schema_version != 2:
            raise RuntimeError(
                f"tilt_thresholds.yaml schema_version={schema_version}, "
                "iteration 2 requires schema_version=2 (run calibrate_tilt_thresholds.py)."
            )
        if method != "elite_p100_plus_margin":
            raise RuntimeError(
                f"tilt_thresholds.yaml calibration_method={method!r}, "
                "expected 'elite_p100_plus_margin'."
            )
    return {
        "thresholdChecksum": checksum,
        "thresholdCalibrationMethod": method,
        "thresholdCalibrationVersion": str(data.get("calibration_version", "")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8.1 sweep CLI (iteration 2)")
    parser.add_argument("--sweep-uid", required=True)
    parser.add_argument(
        "--videos",
        default="ref-invert,ref-climb,ref-foxtop,ref-foxtop-split,ref-sideway-spin",
    )
    parser.add_argument("--bucket", default="sunity-motion-pilot-videos")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-fallback", action="store_true",
        help="bypass tilt_thresholds.yaml version check (fallback test only)",
    )
    parser.add_argument(
        "--skip-cleanup", action="store_true",
        help="skip sweep_temp/ S3 cleanup (debug only)",
    )
    args = parser.parse_args()

    videos = [v.strip() for v in args.videos.split(",") if v.strip()]

    commit_hash = _git_head()
    metadata = _yaml_metadata(args.allow_fallback)

    print(
        f"[setup] sweep_uid={args.sweep_uid} videos={len(videos)} "
        f"commit={commit_hash[:8]} method={metadata['thresholdCalibrationMethod']}",
        flush=True,
    )
    if args.dry_run:
        print("[dry-run] no S3 copy / no Firestore write / no _process", flush=True)
        return 0

    from sunity_shared import firestore_admin as fa, models  # noqa: E402
    pipeline = _load_pipeline()
    s3 = boto3.client("s3")
    db = fa._db()

    written_keys: list[str] = []
    failures: list[dict] = []
    for i, name in enumerate(videos, start=1):
        analysis_id = uuid.uuid4().hex
        new_key = f"sweep_temp/{args.sweep_uid}/{analysis_id}.mp4"
        print(f"\n[sweep {i}/{len(videos)}] {name} -> {analysis_id}", flush=True)

        # 1. Copy S3
        s3.copy_object(
            Bucket=args.bucket,
            CopySource={"Bucket": args.bucket, "Key": f"reference/{name}.mp4"},
            Key=new_key,
        )
        written_keys.append(new_key)

        # 2. Firestore doc — sourceLabel 단순 유지 + metadata 는 별도 scalar fields
        doc_ref = (
            db.collection("users").document(args.sweep_uid)
            .collection("analyses").document(analysis_id)
        )
        doc_ref.set({
            "analysisId": analysis_id,
            "uid": args.sweep_uid,
            "mode": models.MODE_SELF,
            "status": models.STATUS_QUEUED,
            "videoKey": new_key,
            "videoFormat": "mp4",
            "fileSizeBytes": 0,
            "sweepCreatedAtMs": _epoch_ms(),
            "sourceLabel": f"sweep_phase8_1:{name}",
            "sweepCommitHash": commit_hash,
            **metadata,
        })

        # 3. _process direct call — failures collected for non-zero exit
        try:
            pipeline._process(args.bucket, new_key, args.sweep_uid, analysis_id)
            print("  _process OK", flush=True)
        except Exception as exc:  # noqa: BLE001
            failure = {
                "video": name,
                "analysisId": analysis_id,
                "error": f"{type(exc).__name__}: {exc}",
            }
            failures.append(failure)
            print(f"  _process FAILED: {failure['error']}", flush=True)

    # 4. sweep_temp/ S3 cleanup (lifecycle policy 대신 명시 삭제)
    if not args.skip_cleanup and written_keys:
        s3.delete_objects(
            Bucket=args.bucket,
            Delete={"Objects": [{"Key": k} for k in written_keys]},
        )
        print(
            f"\n[cleanup] deleted {len(written_keys)} S3 objects under sweep_temp/",
            flush=True,
        )

    # 5. exit code — iteration 3 정합 (Codex HIGH: 어떤 _process 라도 실패 시 non-zero)
    if failures:
        print(
            json.dumps({"failures": failures}, ensure_ascii=False, indent=2),
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
