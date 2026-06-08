"""Task 4 (Plan 06-03 — C5 + R7 fix). 양 스크립트 dry-run 통합 검증.

박제 정신:
  - C5 (2026-06-08 reviews MEDIUM): Task 5 (실 실행 checkpoint) 의 blast radius
    1차 검증 — 양 스크립트의 --dry-run path 가 실제로 동작함을 자동 증명.
  - R7 fix (2026-06-08 round-2): seed-reference-body-profile.mjs 의 dry-run path
    가 Firebase init 호출 전 early return — ADC 미설정 환경에서도 안전.
    validation 이 Firebase init 보다 먼저 실행됨을 증명.
  - Test 2 + Test 4 = R7 fix 핵심 검증.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2].parent
FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "test_reference_body_data.json"
)
EXTRACT_SCRIPT = PROJECT_ROOT / "backend" / "scripts" / "extract_reference_body_profiles.py"
SEED_SCRIPT = PROJECT_ROOT / "app" / "scripts" / "seed-reference-body-profile.mjs"

NODE_AVAILABLE = shutil.which("node") is not None


# ── Test 1: Python extract --dry-run via in-process main (subprocess 회피) ──


def test_extract_dry_run_outputs_json_to_stdout_without_writing(
    monkeypatch, capsys, tmp_path
):
    """Test 1 — Python extract 스크립트의 --dry-run path.

    S3/RTMW/measure_body_profile 을 monkeypatch 로 stub. dependency injection 이
    아니므로 모듈 자체를 import 한 뒤 내부 함수 monkeypatch — subprocess 회피.
    exit 0 (return 정상) + stdout 에 "motions" + 출력 파일 미생성.
    """
    # PYTHONPATH 정합 — sunity_shared layer.
    sys.path.insert(
        0,
        str(PROJECT_ROOT / "backend" / "shared" / "python"),
    )

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "extract_reference_body_profiles", EXTRACT_SCRIPT
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # boto3 → mock s3 client.
    class _FakeS3:
        def download_file(self, bucket, key, target):
            Path(target).write_bytes(b"\x00")

    fake_boto = type(
        "FakeBoto3",
        (),
        {"client": staticmethod(lambda *a, **kw: _FakeS3())},
    )
    monkeypatch.setitem(sys.modules, "boto3", fake_boto)

    # Stub heavy adapters — measure_one 자체를 stub 으로 교체.
    def _fake_measure_one(motion_id, video_path, extractor, rtmw_engine):
        return {
            "bodyNormalizationProfile": {
                "estimatedHeightScale": 1.0,
                "armScale": 1.0,
                "legScale": 1.0,
                "torsoScale": 1.0,
                "shoulderHipRatio": 1.0,
                "confidence": 0.8,
                "warnings": [],
            },
            "bodyComparisonSourcePose": None,
        }

    monkeypatch.setattr(mod, "_measure_one", _fake_measure_one)
    monkeypatch.setattr(mod, "_download_video", lambda *a, **kw: None)

    # frame_extractor + rtmw_engine 인스턴스화는 main() 내부의 lazy import.
    # 둘 다 fake 로 교체 — main() 안의 `from ... import` 를 sys.modules 로 우회.
    import types

    class _FakeExtractor:
        def __init__(self, *a, **kw):
            pass

    fake_fe = types.ModuleType("sunity_shared.analysis.frame_extractor")
    fake_fe.FfmpegFrameExtractor = _FakeExtractor
    monkeypatch.setitem(
        sys.modules,
        "sunity_shared.analysis.frame_extractor",
        fake_fe,
    )

    class _FakeRTMW:
        def __init__(self, *a, **kw):
            pass

        def estimate(self, frames, pole):
            return []

    fake_rtmw_module = types.ModuleType(
        "sunity_shared.analysis.pose_engines.rtmw.rtmw_engine"
    )
    fake_rtmw_module.RTMWPoseEngine = _FakeRTMW
    monkeypatch.setitem(
        sys.modules,
        "sunity_shared.analysis.pose_engines.rtmw.rtmw_engine",
        fake_rtmw_module,
    )

    # env — AWS_DEFAULT_REGION 필수.
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-2")

    # argv 주입.
    output_path = tmp_path / "should-not-exist.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "extract_reference_body_profiles.py",
            "--bucket",
            "test-bucket",
            "--output",
            str(output_path),
            "--dry-run",
            "--motion-ids",
            "test-motion",
        ],
    )

    mod.main()

    captured = capsys.readouterr()
    # stdout 에 JSON ("motions" 포함).
    assert "motions" in captured.out
    parsed = json.loads(captured.out)
    assert "motions" in parsed
    assert "test-motion" in parsed["motions"]

    # 출력 파일 미생성.
    assert not output_path.exists()


# ── Test 2 (R7 fix): seed dry-run works without ADC, Firebase init 호출 0 ──


@pytest.mark.skipif(not NODE_AVAILABLE, reason="node CLI not available")
def test_seed_dry_run_works_without_adc_no_firebase_init():
    """Test 2 (R7 fix 핵심).

    GOOGLE_APPLICATION_CREDENTIALS / GCLOUD_PROJECT 등 ADC 환경변수 모두 비운
    상태에서 dry-run 실행. exit 0 + stdout 에 `"dryRun":true` 포함 + stderr 에
    `Could not load the default credentials` 또는 `applicationDefault` 관련
    에러 메시지 부재.
    """
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in (
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CLOUD_PROJECT",
            "GCLOUD_PROJECT",
        )
    }
    # 명시적 비우기.
    env["GOOGLE_APPLICATION_CREDENTIALS"] = ""
    env["GOOGLE_CLOUD_PROJECT"] = ""

    result = subprocess.run(
        [
            "node",
            str(SEED_SCRIPT),
            "--profiles",
            str(FIXTURE_PATH),
            "--dry-run",
        ],
        env=env,
        capture_output=True,
        timeout=30,
    )
    stdout = result.stdout.decode()
    stderr = result.stderr.decode()
    assert result.returncode == 0, (
        f"dry-run should exit 0, got {result.returncode}. stderr={stderr}"
    )
    assert '"dryRun"' in stdout and "true" in stdout
    # R7 핵심: Firebase init 호출 부재 — ADC 에러 메시지 stderr 부재.
    assert "Could not load the default credentials" not in stderr
    assert "Could not load the default credentials" not in stdout
    # applicationDefault 모듈 에러 부재.
    assert "applicationDefault" not in stderr


# ── Test 3: real-run path는 별도 mock Firebase 필요 — integration mark ──


@pytest.mark.skip(
    reason=(
        "real-run path 는 Firebase Admin emulator 또는 별도 mock npm package "
        "필요. Test 4 (R7 schema before init) 가 R7 fix 핵심을 직접 증명."
    )
)
def test_seed_real_run_calls_batch_commit_when_dry_run_absent():
    """Test 3 — mock-Firebase-Admin 환경 또는 emulator 에서 batch.commit() 호출 검증."""
    pass


# ── Test 4 (R7 fix): malformed fixture + dry-run → schema error before init ──


@pytest.mark.skipif(not NODE_AVAILABLE, reason="node CLI not available")
def test_seed_dry_run_validates_schema_before_early_return(tmp_path):
    """Test 4 (R7 fix 핵심).

    malformed fixture (estimatedHeightScale 누락) + --dry-run + ADC 미설정.
    exit non-zero + stderr 에 schema validation 에러. Firebase init 호출 부재
    (ADC 에러 메시지 부재) → validation 이 Firebase init 보다 먼저 실행됨을 증명.
    """
    # malformed fixture 생성.
    bad = json.loads(FIXTURE_PATH.read_text())
    del bad["motions"]["test-motion"]["bodyNormalizationProfile"][
        "estimatedHeightScale"
    ]
    bad_path = tmp_path / "bad_reference_body_data.json"
    bad_path.write_text(json.dumps(bad))

    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in (
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CLOUD_PROJECT",
            "GCLOUD_PROJECT",
        )
    }
    env["GOOGLE_APPLICATION_CREDENTIALS"] = ""

    result = subprocess.run(
        [
            "node",
            str(SEED_SCRIPT),
            "--profiles",
            str(bad_path),
            "--dry-run",
        ],
        env=env,
        capture_output=True,
        timeout=30,
    )
    stdout = result.stdout.decode()
    stderr = result.stderr.decode()
    assert result.returncode != 0, (
        f"malformed fixture should exit non-zero, got {result.returncode}"
    )
    # schema 에러 메시지 — "estimatedHeightScale" 또는 "필수 필드 누락" 출력.
    combined = stdout + stderr
    assert (
        "estimatedHeightScale" in combined
        or "필수 필드 누락" in combined
        or "필드 누락" in combined
    ), f"schema validation error 메시지 부재. stdout={stdout!r} stderr={stderr!r}"
    # R7 핵심: Firebase init 호출 부재.
    assert "Could not load the default credentials" not in combined
    assert "applicationDefault" not in stderr


# ── Test 5: extract real-run writes file when --dry-run absent ──


def test_extract_real_run_writes_file_when_dry_run_absent(
    monkeypatch, tmp_path
):
    """Test 5 — mock 환경에서 --dry-run 없이 output 파일 생성.

    Test 1 과 동일 stub 구조. --dry-run 없이 실행 시 args.output 경로에 파일 생성.
    """
    sys.path.insert(
        0,
        str(PROJECT_ROOT / "backend" / "shared" / "python"),
    )

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "extract_reference_body_profiles_realrun", EXTRACT_SCRIPT
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class _FakeS3:
        def download_file(self, bucket, key, target):
            Path(target).write_bytes(b"\x00")

    fake_boto = type(
        "FakeBoto3",
        (),
        {"client": staticmethod(lambda *a, **kw: _FakeS3())},
    )
    monkeypatch.setitem(sys.modules, "boto3", fake_boto)

    def _fake_measure_one(motion_id, video_path, extractor, rtmw_engine):
        return {
            "bodyNormalizationProfile": {
                "estimatedHeightScale": 1.0,
                "armScale": 1.0,
                "legScale": 1.0,
                "torsoScale": 1.0,
                "shoulderHipRatio": 1.0,
                "confidence": 0.8,
                "warnings": [],
            },
            "bodyComparisonSourcePose": None,
        }

    monkeypatch.setattr(mod, "_measure_one", _fake_measure_one)
    monkeypatch.setattr(mod, "_download_video", lambda *a, **kw: None)

    import types

    class _FakeExtractor:
        def __init__(self, *a, **kw):
            pass

    fake_fe = types.ModuleType("sunity_shared.analysis.frame_extractor")
    fake_fe.FfmpegFrameExtractor = _FakeExtractor
    monkeypatch.setitem(
        sys.modules,
        "sunity_shared.analysis.frame_extractor",
        fake_fe,
    )

    class _FakeRTMW:
        def __init__(self, *a, **kw):
            pass

        def estimate(self, frames, pole):
            return []

    fake_rtmw_module = types.ModuleType(
        "sunity_shared.analysis.pose_engines.rtmw.rtmw_engine"
    )
    fake_rtmw_module.RTMWPoseEngine = _FakeRTMW
    monkeypatch.setitem(
        sys.modules,
        "sunity_shared.analysis.pose_engines.rtmw.rtmw_engine",
        fake_rtmw_module,
    )

    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-2")

    output_path = tmp_path / "reference-body-data.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "extract_reference_body_profiles.py",
            "--bucket",
            "test-bucket",
            "--output",
            str(output_path),
            "--motion-ids",
            "test-motion",
        ],
    )

    mod.main()

    assert output_path.exists()
    payload = json.loads(output_path.read_text())
    assert "motions" in payload
    assert "test-motion" in payload["motions"]
