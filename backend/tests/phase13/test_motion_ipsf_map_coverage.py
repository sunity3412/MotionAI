"""Phase 13-B Task 2 — motion_ipsf_map 전수 cover + 안전 기본 + 키 계약.

belle 2026-06-16 STANDARD guard ("새 영상이 들어와도 동작은 동작"):
  1. seed 의 11 motion_id 전부 lookup_motion_branch → non-unknown copyBranch.
  2. 임의의 UNKNOWN/uncurated id → copyBranch="branch2_eunji_reference" 안전 기본
     (raise 아님, DECISION 2).
  3. angleFixtureKey 키 계약 (HIGH-1):
     - ipsf_registered_fixture → registered_move_angles.angles[key] 존재
     - eunji_measured_yaml → criteria/{key}.yaml 존재
     - no_angle_criterion → angleFixtureKey is null
  4. 직교성 회귀 (BLOCKER-1): ref-invert = branch1 + eunji_measured_yaml.

11-id 진실원 = seed-reference-motions.mjs MOTIONS (단일 진실원 파싱). 12번째 동작이
라이브러리에 추가되면 본 테스트가 surface 한다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from sunity_shared.analysis import assemble
from sunity_shared.analysis.assemble import MotionBranchInfo

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SEED_PATH = _REPO_ROOT / "app" / "scripts" / "seed-reference-motions.mjs"
_REGISTERED_ANGLES_PATH = _REPO_ROOT / "backend" / "data" / "registered_move_angles.json"
_CRITERIA_DIR = _REPO_ROOT / "backend" / "judging_data" / "criteria"

_NON_UNKNOWN = {"branch1_ipsf_registered", "branch2_eunji_reference"}


def _seeded_motion_ids() -> list[str]:
    """seed-reference-motions.mjs MOTIONS 의 motionId 전수 (단일 진실원).

    MOTIONS 배열의 `motionId: 'ref-...'` 항목만 추출 (OBSOLETE_MOTION_IDS 제외).
    """
    text = _SEED_PATH.read_text(encoding="utf-8")
    # `motionId: 'ref-foo'` 라인만 — OBSOLETE_MOTION_IDS 는 문자열 배열이라 `motionId:`
    # 접두가 없으므로 자연 제외.
    return re.findall(r"motionId:\s*'([^']+)'", text)


def test_seed_has_eleven_motions():
    ids = _seeded_motion_ids()
    assert len(ids) == 11, f"seed MOTIONS 11 기대, got {len(ids)}: {ids}"
    assert len(set(ids)) == 11, "중복 motionId"


@pytest.mark.parametrize("motion_id", _seeded_motion_ids())
def test_every_seeded_motion_resolves_non_unknown(motion_id: str):
    info = assemble.lookup_motion_branch(motion_id)
    assert isinstance(info, MotionBranchInfo)
    assert info.copyBranch in _NON_UNKNOWN, (
        f"{motion_id} → {info.copyBranch} (unknown ship 금지)"
    )
    assert info.sourceNote.strip(), f"{motion_id} sourceNote 비어있음"
    assert info.angleSource, f"{motion_id} angleSource 누락"


@pytest.mark.parametrize("motion_id", _seeded_motion_ids())
def test_angle_fixture_key_contract(motion_id: str):
    info = assemble.lookup_motion_branch(motion_id)
    if info.angleSource == "ipsf_registered_fixture":
        registered = json.loads(
            _REGISTERED_ANGLES_PATH.read_text(encoding="utf-8")
        )
        assert info.angleFixtureKey in registered["angles"], (
            f"{motion_id} angleFixtureKey={info.angleFixtureKey} not in registered_move_angles"
        )
    elif info.angleSource == "eunji_measured_yaml":
        assert info.angleFixtureKey is not None
        yaml_path = _CRITERIA_DIR / f"{info.angleFixtureKey}.yaml"
        assert yaml_path.exists(), f"{motion_id} → {yaml_path} 부재"
    elif info.angleSource == "no_angle_criterion":
        assert info.angleFixtureKey is None, (
            f"{motion_id} no_angle_criterion 인데 angleFixtureKey 가 non-null (HIGH-1)"
        )


def test_unknown_id_safe_defaults_to_branch2():
    # belle DECISION 2 — uncurated id → branch2 안전 기본 (raise/fail-closed 아님).
    info = assemble.lookup_motion_branch("ref-future-zzz")
    assert isinstance(info, MotionBranchInfo)
    assert info.copyBranch == "branch2_eunji_reference"
    assert info.ipsfCode is None  # IPSF 주장 안 함
    assert info.angleFixtureKey is None  # 가짜 각도 키 미주입


def test_none_id_safe_defaults_to_branch2():
    info = assemble.lookup_motion_branch(None)
    assert info.copyBranch == "branch2_eunji_reference"


def test_orthogonality_ref_invert_branch1_with_eunji_angle():
    # BLOCKER-1 직교성 회귀 — 단일 boolean 으로 환원 불가 증명.
    info = assemble.lookup_motion_branch("ref-invert")
    assert info.copyBranch == "branch1_ipsf_registered"
    assert info.angleSource == "eunji_measured_yaml"
    assert info.angleFixtureKey == "ref-invert"


def test_ref_climb_branch1_no_angle_criterion():
    info = assemble.lookup_motion_branch("ref-climb")
    assert info.copyBranch == "branch1_ipsf_registered"
    assert info.angleSource == "no_angle_criterion"
    assert info.angleFixtureKey is None


def test_lookup_returns_dataclass_instance_not_dict():
    info = assemble.lookup_motion_branch("ref-foxtop")
    assert isinstance(info, MotionBranchInfo)
    assert not isinstance(info, dict)
