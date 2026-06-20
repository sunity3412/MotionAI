"""v2 비전 거부권 순수 코어 단위테스트 (Phase 20-01, D-01/D-02/D-05 + HIGH-3).

이 모듈은 vision_veto.py 의 안전 성질을 코드로 못 박는다:
  - D-01 하향 전용: apply_downward_cap 은 점수를 절대 올리지 않는다 (위양성 재발 차단).
  - D-02 curve-fit 금지: SEVERITY_CAP 의 moderate/major 는 placeholder(None) 이며,
    실 수치는 20-04 의 generalization eval 에서만 도출된다.
  - HIGH-3 fail-closed: SEVERITY_CAP_PROVENANCE 가 데이터(주석 아님)로 박제되어,
    sensitivity_manifest_sha256 가 부재/TODO 인 동안 cap 을 채우면 가드가 거부한다.
  - D-05 worst-pose: key_moments(hold/peak) 재사용 — IPSF phase 평균 거부.

전부 pod-free 순수 단위테스트 (numpy 외 의존 0). PYTHONPATH=shared/python.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# PYTHONPATH=backend/shared/python 컨벤션 (test_pipeline_mode3 정합) 보강.
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import vision_veto  # noqa: E402

_SEVERITIES = (None, "minor", "moderate", "major", "unknown")


def test_downward_only_property():
    """∀ (overall ∈ 0..100, severity) 에 대해 출력 ≤ 입력 (D-01 코어 invariant).

    비전은 점수를 절대 올리지 않는다. minor/None/unknown 은 불변 (cap 미적용).
    moderate/major 는 현재 placeholder(None) 이므로 역시 불변 — cap 이 채워져도
    invariant(≤ 입력)는 깨지지 않아야 한다.
    """
    for overall in range(0, 101):
        for severity in _SEVERITIES:
            out = vision_veto.apply_downward_cap(overall, severity)
            assert out <= overall, (
                f"apply_downward_cap({overall}, {severity!r}) = {out} > {overall} "
                "— 비전이 점수를 올렸다 (D-01 위반)"
            )
            if severity in (None, "minor", "unknown"):
                assert out == overall, (
                    f"severity={severity!r} 는 점수를 깎으면 안 된다 (정타 보존)"
                )


def test_minor_no_cap():
    """minor / None / 미지 severity → 입력 그대로 (정타 95~100 보존, D-01)."""
    for overall in (95, 96, 97, 98, 99, 100):
        assert vision_veto.apply_downward_cap(overall, "minor") == overall
        assert vision_veto.apply_downward_cap(overall, None) == overall
        assert vision_veto.apply_downward_cap(overall, "does_not_exist") == overall
    # minor cap 은 미적용(None) 또는 무캡(>=100) 이어야 한다.
    minor_cap = vision_veto.SEVERITY_CAP["minor"]
    assert minor_cap is None or minor_cap >= 100


def test_cap_lowers_for_major():
    """major cap 이 수치로 확정되면 overall=100 이 그 값으로 내려간다.

    D-02 정합 — cap 수치 자체는 단언하지 않는다. placeholder(None) 인 동안은
    cap 미적용(불변)을, 수치가 채워지면 min 동작만 단언한다.
    """
    major_cap = vision_veto.SEVERITY_CAP["major"]
    if major_cap is None:
        # 아직 도출 전 — cap 미적용(불변)이 정답.
        assert vision_veto.apply_downward_cap(100, "major") == 100
    else:
        assert vision_veto.apply_downward_cap(100, "major") == min(100, major_cap)
        # cap 보다 낮은 입력은 더 내려가지 않는다 (min 동작).
        assert vision_veto.apply_downward_cap(major_cap - 1, "major") == major_cap - 1


def test_severity_cap_no_curve_fit_marker():
    """moderate/major 가 placeholder(None) 이거나 provenance 가 phase20 출처 (D-02 가드)."""
    moderate = vision_veto.SEVERITY_CAP["moderate"]
    major = vision_veto.SEVERITY_CAP["major"]
    provenance_ok = (
        vision_veto.SEVERITY_CAP_PROVENANCE.get("source") == "phase20_sensitivity"
    )
    assert (moderate is None and major is None) or provenance_ok, (
        "SEVERITY_CAP moderate/major 가 채워졌다면 provenance source 는 "
        "phase20_sensitivity 여야 한다 (6페어 curve-fit 금지, D-02)"
    )


def test_provenance_is_data_not_comment():
    """SEVERITY_CAP_PROVENANCE 가 module dict(주석 아님)로 존재 (HIGH-3).

    주석 grep 이 아니라 import 한 dict 를 직접 검사한다.
    """
    prov = vision_veto.SEVERITY_CAP_PROVENANCE
    assert isinstance(prov, dict)
    assert {"source", "sensitivity_manifest_sha256", "phase18_pairs_used_for_derivation"} <= set(
        prov.keys()
    )
    assert prov["source"] == "phase20_sensitivity"
    # 6페어는 회귀 검증 전용 — derive 입력 아님. 영구 False.
    assert prov["phase18_pairs_used_for_derivation"] is False


def test_cap_fill_requires_real_manifest_sha():
    """moderate/major cap 이 채워지면 manifest sha 도 실 sha 여야 한다 (HIGH-3 fail-closed).

    수치 cap + (TODO/None sha) 모순 시 FAIL — curve-fit fail-closed 인코딩.
    현재 상태: cap=None + sha=None → 일관 → PASS. 20-04 가 sha 채운 뒤에만 cap 가능.
    """
    prov = vision_veto.SEVERITY_CAP_PROVENANCE
    sha = prov.get("sensitivity_manifest_sha256")
    sha_is_real = isinstance(sha, str) and sha not in ("", "TODO")
    cap_filled = any(
        vision_veto.SEVERITY_CAP[k] is not None for k in ("moderate", "major")
    )
    if cap_filled:
        assert sha_is_real, (
            "moderate/major cap 이 채워졌는데 sensitivity_manifest_sha256 가 "
            f"실 sha 가 아니다 (sha={sha!r}) — curve-fit fail-closed 위반 (HIGH-3)"
        )


def _km(moment_key: str, ts: float):
    """KeyMoment 호환 가짜 객체 (moment_key/timestamp_seconds 속성만 사용)."""
    return SimpleNamespace(moment_key=moment_key, timestamp_seconds=ts)


def test_worst_pose_prefers_hold():
    """hold > peak > 전체 우선순위로 key_moments 재사용, None/빈 → None (D-05)."""
    # hold + peak 혼재 → hold 우선 (가장 이른 hold).
    p = SimpleNamespace(
        key_moments=(_km("setup", 0.0), _km("peak", 3.0), _km("hold", 5.0), _km("hold", 7.0))
    )
    assert vision_veto.worst_pose_timestamp(p) == 5.0

    # hold 없음 → peak.
    p2 = SimpleNamespace(key_moments=(_km("setup", 1.0), _km("peak", 4.0), _km("peak", 2.0)))
    assert vision_veto.worst_pose_timestamp(p2) == 2.0

    # hold/peak 둘 다 없음 → 첫 moment (가장 이른).
    p3 = SimpleNamespace(key_moments=(_km("setup", 6.0), _km("release", 2.0)))
    assert vision_veto.worst_pose_timestamp(p3) == 2.0

    # key_moments None / 빈 / 속성 부재 → None (graceful).
    assert vision_veto.worst_pose_timestamp(SimpleNamespace(key_moments=None)) is None
    assert vision_veto.worst_pose_timestamp(SimpleNamespace(key_moments=())) is None
    assert vision_veto.worst_pose_timestamp(SimpleNamespace()) is None


def test_worst_pose_no_new_moment_call():
    """worst_pose_timestamp 가 profile.key_moments 만 읽고 외부 호출 0 (순수).

    소스에 Gemini/네트워크 import 가 0 임을 검증 (모듈은 순수 코어).
    """
    src = Path(vision_veto.__file__).read_text(encoding="utf-8")
    for forbidden in ("genai", "google", "requests", "boto3", "firestore"):
        assert f"import {forbidden}" not in src, (
            f"vision_veto.py 가 {forbidden} 를 import — 순수 모듈 위반"
        )
    # 올림 경로 0 — max( 금지 (min 만 허용).
    assert "max(" not in src, "vision_veto.py 에 max( 가 있다 — 하향-전용 위반 (D-01)"
