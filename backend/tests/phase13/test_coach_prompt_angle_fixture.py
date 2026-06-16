"""Phase 13-B Task 3 — coach_writer 프롬프트 동작/분기/정의각도 주입 (criteria 7).

- _build_prompt(motion_name/branch/angle_fixture) → 정의 각도 인용. None → 기존 회귀.
- _SYSTEM 에 임의 수치 금지 + 180° 일반화 금지 가드.
- HIGH-3 NON-180: NON-180 값 그대로 인용, 180° 치환 0.
- WARNING-1: pipeline _load_coach_angle_fixture(ref-foxtop) → criteria/ref-foxtop.yaml
  로드 (ref-ref-foxtop.yaml 시도 0).
- HIGH-1: ref-climb(no_angle_criterion) → angle_fixture=None + "fixture 없음" 라인.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from sunity_shared.analysis import assemble
from sunity_shared.analysis import coach_writer

_JOINTS = [
    {"key": "left_shoulder", "labelKo": "왼 어깨", "deviation_deg": 12.0, "direction": "down"},
]


# ── _build_prompt (pure) ──────────────────────────────────────────────────────


def test_system_prompt_has_arbitrary_number_and_180_guard():
    assert "임의 수치" in coach_writer._SYSTEM
    assert "180" in coach_writer._SYSTEM
    assert "일반화" in coach_writer._SYSTEM


def test_build_prompt_none_is_backward_compatible():
    base = coach_writer._build_prompt(_JOINTS)
    injected = coach_writer._build_prompt(
        _JOINTS, motion_name=None, branch=None, angle_fixture=None
    )
    assert base == injected
    # 동작 컨텍스트 prefix 가 없음 (회귀).
    assert "동작:" not in base


def test_build_prompt_injects_motion_and_non_180_angles():
    # NON-180 정의 각도 — 180° 로 치환되면 안 됨 (HIGH-3).
    fixture = {
        "left_shoulder": {"angle": 110.0, "isExtension": False},
        "left_elbow": {"angle": 25.0, "isExtension": False},
        "left_knee": {"angle": 180.0, "isExtension": True},
    }
    prompt = coach_writer._build_prompt(
        _JOINTS,
        motion_name="아이샤",
        branch="branch1_ipsf_registered",
        angle_fixture=fixture,
    )
    assert "아이샤" in prompt
    # NON-180 값이 그대로 인용됨.
    assert "110" in prompt
    assert "25" in prompt
    # 180° 로 일반화 금지 — 110/25 가 180 으로 치환되지 않음.
    assert "110.0°" in prompt or "110°" in prompt


def test_build_prompt_branch2_no_world_standard_phrase():
    prompt = coach_writer._build_prompt(
        _JOINTS,
        motion_name="폭스탑",
        branch="branch2_eunji_reference",
        angle_fixture={"left_shoulder": {"angle": 139.0, "isExtension": False}},
    )
    assert "정은지 선수 기준" in prompt
    assert "세계 심사 기준" not in prompt
    # 분기2 프롬프트에 180° 일반화 카피가 없음.
    assert not re.search(r"180\s*°\s*신전", prompt)


def test_build_prompt_no_fixture_emits_absent_line():
    prompt = coach_writer._build_prompt(
        _JOINTS, motion_name="클라임", branch="branch1_ipsf_registered", angle_fixture=None
    )
    assert "관절 각도 fixture 가 없습니다" in prompt


# ── pipeline _load_coach_angle_fixture (WARNING-1 / HIGH-1) ───────────────────

_PIPELINE_DIR = Path(__file__).resolve().parents[2] / "functions" / "pipeline"
_LAYER = Path(__file__).resolve().parents[2] / "shared" / "python"
for _p in (str(_LAYER), str(_PIPELINE_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

pipeline_app = pytest.importorskip("app")


def test_load_fixture_eunji_yaml_no_double_prefix():
    # WARNING-1: ref-foxtop → criteria/ref-foxtop.yaml (ref-ref-foxtop.yaml 시도 0).
    branch_info = assemble.lookup_motion_branch("ref-foxtop")
    assert branch_info.angleSource == "eunji_measured_yaml"
    fixture = pipeline_app._load_coach_angle_fixture(branch_info)
    assert isinstance(fixture, dict) and fixture
    # ref-foxtop.yaml L19-20 left_shoulder angle_target=139.02.
    assert "left_shoulder" in fixture
    assert round(fixture["left_shoulder"]["angle"], 1) == 139.0


def test_load_fixture_no_angle_criterion_is_none():
    # HIGH-1: ref-climb(no_angle_criterion) → None (가짜 각도 0).
    branch_info = assemble.lookup_motion_branch("ref-climb")
    assert branch_info.angleSource == "no_angle_criterion"
    assert pipeline_app._load_coach_angle_fixture(branch_info) is None


def test_load_fixture_unknown_safe_default_is_none():
    # 미지 id → branch2 안전 기본 (angleSource=unavailable) → fixture None.
    branch_info = assemble.lookup_motion_branch("ref-future-zzz")
    assert pipeline_app._load_coach_angle_fixture(branch_info) is None


def test_no_angle_path_prompt_has_no_injected_numbers():
    # ref-climb fixture=None → 프롬프트가 "fixture 없음" + 어떤 각도 숫자도 미주입.
    branch_info = assemble.lookup_motion_branch("ref-climb")
    fixture = pipeline_app._load_coach_angle_fixture(branch_info)
    prompt = coach_writer._build_prompt(
        _JOINTS,
        motion_name=branch_info.officialName,
        branch=branch_info.copyBranch,
        angle_fixture=fixture,
    )
    assert "관절 각도 fixture 가 없습니다" in prompt
    # HIGH-1: 가짜 per-joint 각도 fixture 라인 (`- <joint>: <num>°`) 미주입.
    # (branch1 컨텍스트 카피의 일반 "180° 신전" 문구는 fixture 값이 아니라 분기 설명.)
    assert not re.search(r"-\s*\w+:\s*\d", prompt)
