"""reactivate_new6_motions 스크립트 단위 테스트.

Phase 17 Plan 07 Task 1 — 신규 6 motion 자동 재활성화 스크립트의
정상/dry-run/graceful failure 경로 + extract_reference_angles 의 RTMW engine
swap 검증 (3차 R-B4 정합 — pipeline private `_RTMWNlfCompat` adapter import 0건).
"""

from __future__ import annotations

import importlib
import io
import json
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


@pytest.fixture
def reactivate_module(monkeypatch):
    """reactivate_new6_motions 모듈 fresh import — module-level side-effect 없도록.

    스크립트는 boto3/firebase_admin 같은 heavy dep 을 lazy import 박제 — 테스트가
    monkeypatch 로 차단해도 모듈 import 자체는 통과.
    """
    if "reactivate_new6_motions" in sys.modules:
        del sys.modules["reactivate_new6_motions"]
    mod = importlib.import_module("reactivate_new6_motions")
    return mod


def test_new6_motion_ids_match_seed_script(reactivate_module):
    """NEW6_MOTION_IDS = 정은지 추가 영상 6 motion (seed-reference-motions.mjs 박힘).

    UAT 2026-06-12 박은 신규 6 motion (학원 통용명) — seed script 의
    `// 정은지 추가 영상 6 motion (2026-06-12 belle 결정...)` 주석 아래 list 와 1:1.
    """
    expected = {
        "ref-kip-up",
        "ref-peter-pan",
        "ref-power-spin",
        "ref-elbow-twist-sister",
        "ref-pdshape",
        "ref-combo",
    }
    assert set(reactivate_module.NEW6_MOTION_IDS) == expected
    assert len(reactivate_module.NEW6_MOTION_IDS) == 6


def test_dry_run_mode_does_not_call_endpoint(monkeypatch, reactivate_module, capsys):
    """--dry-run 박혀 있으면 endpoint 호출 0회 + Firestore 갱신 0회."""
    calls: list[dict] = []

    def fake_call(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return {"motionId": "x", "routingBranch": "branch_1_ipsf"}

    monkeypatch.setattr(reactivate_module, "_post_auto_register", fake_call)
    monkeypatch.setattr(
        reactivate_module,
        "_fetch_reference_doc",
        lambda motion_id: {"videoS3Key": f"reference/{motion_id}.mp4"},
    )

    exit_code = reactivate_module.run(
        motion_ids=["ref-kip-up", "ref-peter-pan"],
        dry_run=True,
        endpoint_url="https://example/reference/auto-register",
        id_token="fake-token",
    )

    assert exit_code == 0
    assert calls == [], "dry-run 박혔는데 endpoint 호출됨"
    captured = capsys.readouterr().out
    assert "DRY-RUN" in captured or "dry-run" in captured


def test_normal_mode_calls_endpoint_per_motion(monkeypatch, reactivate_module):
    """정상 mode — motion 마다 endpoint 1회 호출 + STUDIO_ALIAS_OVERRIDES 반영."""
    monkeypatch.setattr(
        reactivate_module,
        "STUDIO_ALIAS_OVERRIDES",
        {"ref-kip-up": "킵업", "ref-peter-pan": "피터팬"},
    )
    calls: list[dict] = []

    def fake_call(*, endpoint_url, id_token, s3_key, studio_alias, override_motion_id):
        calls.append(
            {
                "endpoint_url": endpoint_url,
                "id_token": id_token,
                "s3_key": s3_key,
                "studio_alias": studio_alias,
                "override_motion_id": override_motion_id,
            }
        )
        return {
            "motionId": override_motion_id,
            "routingBranch": "branch_2_studio",
            "reviewRequired": True,
        }

    monkeypatch.setattr(reactivate_module, "_post_auto_register", fake_call)
    monkeypatch.setattr(
        reactivate_module,
        "_fetch_reference_doc",
        lambda motion_id: {"videoS3Key": f"reference/{motion_id}.mp4"},
    )

    exit_code = reactivate_module.run(
        motion_ids=["ref-kip-up", "ref-peter-pan"],
        dry_run=False,
        endpoint_url="https://example/reference/auto-register",
        id_token="fake-token",
    )

    assert exit_code == 0
    assert len(calls) == 2
    # STUDIO_ALIAS_OVERRIDES 의 alias 가 endpoint body 에 박힘.
    kip = next(c for c in calls if c["override_motion_id"] == "ref-kip-up")
    peter = next(c for c in calls if c["override_motion_id"] == "ref-peter-pan")
    assert kip["studio_alias"] == "킵업"
    assert peter["studio_alias"] == "피터팬"
    assert kip["s3_key"] == "reference/ref-kip-up.mp4"


def test_graceful_failure_continues(monkeypatch, reactivate_module, capsys):
    """endpoint 1건 실패 → 나머지 motion 은 계속 진행 (graceful)."""
    monkeypatch.setattr(reactivate_module, "STUDIO_ALIAS_OVERRIDES", {})

    def flaky_call(*, override_motion_id, **_):
        if override_motion_id == "ref-pdshape":
            raise RuntimeError("simulated 500 from Gemini")
        return {
            "motionId": override_motion_id,
            "routingBranch": "branch_3_auto",
            "reviewRequired": True,
        }

    monkeypatch.setattr(reactivate_module, "_post_auto_register", flaky_call)
    monkeypatch.setattr(
        reactivate_module,
        "_fetch_reference_doc",
        lambda motion_id: {"videoS3Key": f"reference/{motion_id}.mp4"},
    )

    exit_code = reactivate_module.run(
        motion_ids=[
            "ref-kip-up",
            "ref-pdshape",  # 실패 박제
            "ref-combo",
        ],
        dry_run=False,
        endpoint_url="https://example/reference/auto-register",
        id_token="fake-token",
    )

    # graceful — 일부 실패 시 exit code 1 박제 (caller 가 retry 판단).
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "ref-kip-up" in out
    assert "ref-pdshape" in out
    assert "ref-combo" in out  # 실패 다음 motion 진행됨 박제.
    assert "FAIL" in out or "실패" in out


# ── 3차 R-B4 정합 — extract_reference_angles.py 의 RTMW direct path 박제 검증 ────


def test_extract_reference_angles_uses_rtmw_engine_directly():
    """extract_reference_angles.py 가 RTMWPoseEngine 을 직접 박제했는지 source-level 검증.

    3차 R-B4 박제: pipeline 의 private `_RTMWNlfCompat` adapter 박제 X (script
    context 가 pipeline module side-effect 끌고 오는 거 차단). 운영 path 정합 =
    RTMWPoseEngine + PoleAxis(vertical_fallback) + measure_body_profile +
    to_coco17_array 직접 박제.
    """
    src_path = _REPO / "scripts" / "extract_reference_angles.py"
    src = src_path.read_text(encoding="utf-8")

    # RTMW direct import 박힘.
    assert "RTMWPoseEngine" in src, (
        "extract_reference_angles.py 가 RTMWPoseEngine 박제 X — Phase 17 Plan 07 swap 미완"
    )
    assert re.search(
        r"from\s+sunity_shared\.analysis\.pose_engines\.rtmw\.rtmw_engine\s+import\s+RTMWPoseEngine",
        src,
    ), "RTMWPoseEngine 의 정식 import path 박제 X"
    # helper 박제.
    assert "to_coco17_array" in src, "to_coco17_array helper 박제 X"
    assert "measure_body_profile" in src, "measure_body_profile helper 박제 X"
    assert "PoleAxis" in src, "PoleAxis (vertical_fallback) 박제 X"

    # pipeline private adapter 박제 0건 (운영 path 정합 + side-effect 차단).
    assert "_RTMWNlfCompat" not in src, (
        "pipeline 의 private `_RTMWNlfCompat` adapter 가 박힘 — script context 는 "
        "RTMWPoseEngine 직접 박제 (3차 R-B4 정합)"
    )

    # NLF 박제 흔적은 legacy 주석 박제로만 보존 — active import line 박혀있으면 fail.
    active_import_lines = [
        ln
        for ln in src.splitlines()
        if "NlfPoseEstimator" in ln and not ln.lstrip().startswith("#")
    ]
    assert not active_import_lines, (
        f"NlfPoseEstimator 가 active import 라인에 박힘: {active_import_lines!r}"
    )
