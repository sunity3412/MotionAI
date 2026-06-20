"""v2 비전 거부권 순수 코어 단위테스트 (Phase 20-01/20-04, D-01/D-02/D-05 + HIGH-3).

이 모듈은 vision_veto.py 의 안전 성질을 코드로 못 박는다:
  - D-01 하향 전용: apply_downward_cap 은 점수를 절대 올리지 않는다 (위양성 재발 차단).
  - D-02 curve-fit 금지: SEVERITY_CAP 은 6페어에 curve-fit 되지 않는다 — 20-04 는
    spec-anchored(belle 스펙 + IPSF severity 의미) 로 cap 을 박는다. 6페어는 회귀
    검증 전용이며 derive 입력이 절대 아니다 (phase18_pairs_used_for_derivation==False).
  - HIGH-3 fail-closed (method-aware): SEVERITY_CAP_PROVENANCE 가 데이터(주석 아님)로
    박제된다. method=="sensitivity_derived" + cap 채움 → 실 sha 강제. method==
    "spec_anchored" → sha 없이 cap 가능하되 spec_basis 데이터가 출처를 박제.
    어떤 method 든 phase18 6페어 curve-fit 은 영구 fail-closed.
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

_SEVERITIES = (None, "none", "minor", "moderate", "major", "unknown")


def test_downward_only_property():
    """∀ (overall ∈ 0..100, severity) 에 대해 출력 ≤ 입력 (D-01 코어 invariant).

    비전은 점수를 절대 올리지 않는다. None/none/unknown 은 불변 (cap 미적용, 정타 보존).
    minor/moderate/major 는 cap 이 채워져도 min-only 이므로 invariant(≤ 입력)는 절대
    깨지지 않아야 한다 (하향 전용).
    """
    for overall in range(0, 101):
        for severity in _SEVERITIES:
            out = vision_veto.apply_downward_cap(overall, severity)
            assert out <= overall, (
                f"apply_downward_cap({overall}, {severity!r}) = {out} > {overall} "
                "— 비전이 점수를 올렸다 (D-01 위반)"
            )
            # None/none/unknown(미지 키) 만 무캡 — 정타 보존. minor 는 Phase 20 부터
            # 90 cap 이 붙으므로 무캡 목록에서 제외.
            if severity in (None, "none", "unknown"):
                assert out == overall, (
                    f"severity={severity!r} 는 점수를 깎으면 안 된다 (정타 보존)"
                )


def test_none_no_cap():
    """none / None / 미지 severity → 입력 그대로 (정타 95~100 보존, D-01).

    Phase 20: 무캡은 'none'(정타) 와 None/미지 키 뿐. minor 는 90 cap 으로 이동.
    """
    for overall in (95, 96, 97, 98, 99, 100):
        assert vision_veto.apply_downward_cap(overall, "none") == overall
        assert vision_veto.apply_downward_cap(overall, None) == overall
        assert vision_veto.apply_downward_cap(overall, "does_not_exist") == overall
    # none cap 은 미적용(None) — 정타 무캡 보존.
    assert vision_veto.SEVERITY_CAP["none"] is None


def test_minor_caps_at_90():
    """minor → 90 cap (Phase 20 robustify — 미세하지만 실재하는 결함 천장 해제).

    100 → 90 으로 내려가지만, 90 미만 입력은 더 내려가지 않는다 (min-only).
    정타(none)는 무캡으로 100 보존 — minor 와 none 의 차이를 명시 박제.
    """
    assert vision_veto.SEVERITY_CAP["minor"] == 90
    assert vision_veto.apply_downward_cap(100, "minor") == 90
    assert vision_veto.apply_downward_cap(95, "minor") == 90
    assert vision_veto.apply_downward_cap(90, "minor") == 90
    assert vision_veto.apply_downward_cap(85, "minor") == 85  # cap 미만 불변 (min-only)
    # 대조 — 정타(none)는 여전히 무캡 → 100 보존.
    assert vision_veto.apply_downward_cap(100, "none") == 100


def test_cap_lowers_for_major():
    """major cap=50, moderate cap=75 으로 spec-anchored 확정 (20-04, belle 스펙).

    major → overall=100 이 50 으로 내려간다 (belle 스펙 "잘못된 동작 ≤50").
    moderate → overall=100 이 75 로 내려간다 (IPSF moderate-fault 원칙적 상한).
    cap 보다 낮은 입력은 더 내려가지 않는다 (min-only). cap 수치가 미래에 바뀌어도
    min 동작 자체는 불변이어야 하므로 수치 단언과 min 동작 단언을 함께 둔다.
    """
    # spec-anchored 확정값 단언 (20-04).
    assert vision_veto.SEVERITY_CAP["major"] == 50
    assert vision_veto.SEVERITY_CAP["moderate"] == 75

    # major: 100 → 50, 그리고 cap 미만 입력은 불변 (min-only).
    assert vision_veto.apply_downward_cap(100, "major") == 50
    assert vision_veto.apply_downward_cap(49, "major") == 49
    assert vision_veto.apply_downward_cap(50, "major") == 50

    # moderate: 100 → 75, 그리고 cap 미만 입력은 불변 (min-only).
    assert vision_veto.apply_downward_cap(100, "moderate") == 75
    assert vision_veto.apply_downward_cap(74, "moderate") == 74
    assert vision_veto.apply_downward_cap(75, "moderate") == 75


def test_severity_cap_no_curve_fit_marker():
    """cap 이 채워졌으면 출처가 데이터로 박제되고 6페어 curve-fit 이 아님 (D-02 가드).

    spec_anchored 모드: spec_basis 가 cap 근거(belle 스펙)를 데이터로 박제하고,
    phase18 6페어는 derive 입력이 아니다. sensitivity_derived 모드: source 가
    phase20 sensitivity 출처여야 한다. 어떤 경우든 6페어 curve-fit 은 금지.
    """
    moderate = vision_veto.SEVERITY_CAP["moderate"]
    major = vision_veto.SEVERITY_CAP["major"]
    prov = vision_veto.SEVERITY_CAP_PROVENANCE
    method = prov.get("method")
    cap_filled = moderate is not None or major is not None

    if cap_filled:
        # 6페어 curve-fit 은 어떤 method 든 영구 금지.
        assert prov.get("phase18_pairs_used_for_derivation") is False, (
            "cap 이 채워졌는데 phase18 6페어를 derive 입력으로 썼다 (curve-fit, D-02)"
        )
        if method == "spec_anchored":
            spec_basis = prov.get("spec_basis")
            assert isinstance(spec_basis, str) and spec_basis.strip(), (
                "spec_anchored 모드에서 cap 이 채워졌다면 spec_basis 가 출처를 "
                "데이터로 박제해야 한다 (주석 아님, D-02)"
            )
        elif method == "sensitivity_derived":
            assert prov.get("source") == "phase20_sensitivity", (
                "sensitivity_derived 모드 cap 의 source 는 phase20_sensitivity 여야 한다"
            )
        else:
            raise AssertionError(
                f"cap 이 채워졌는데 provenance.method 가 미지값이다: {method!r}"
            )


def test_provenance_is_data_not_comment():
    """SEVERITY_CAP_PROVENANCE 가 module dict(주석 아님)로 존재 (HIGH-3).

    주석 grep 이 아니라 import 한 dict 를 직접 검사한다. method/spec_basis 포함.
    """
    prov = vision_veto.SEVERITY_CAP_PROVENANCE
    assert isinstance(prov, dict)
    assert {
        "method",
        "source",
        "spec_basis",
        "sensitivity_manifest_sha256",
        "phase18_pairs_used_for_derivation",
    } <= set(prov.keys())
    assert prov["method"] in ("spec_anchored", "sensitivity_derived")
    # spec_anchored(현재) → spec_basis 가 belle 스펙 출처를 데이터로 박제.
    if prov["method"] == "spec_anchored":
        assert isinstance(prov["spec_basis"], str)
        assert "≤50" in prov["spec_basis"], (
            "spec_basis 가 belle 스펙 '잘못된 동작 ≤50' 출처를 명시해야 한다"
        )
    # 6페어는 회귀 검증 전용 — derive 입력 아님. 영구 False (INVARIANT).
    assert prov["phase18_pairs_used_for_derivation"] is False


def test_phase18_pairs_never_derivation_input():
    """6 deliberate-fault 페어는 영구히 derive 입력이 아니다 (INVARIANT, 어떤 method 든).

    6페어는 known-answer 회귀 게이트 전용. cap 활성화 모드와 무관하게 이 값은
    영구 False — True 가 되면 단일 선수 curve-fit 으로 일반화가 깨진다 (D-02).
    """
    prov = vision_veto.SEVERITY_CAP_PROVENANCE
    assert prov["phase18_pairs_used_for_derivation"] is False


def test_cap_fill_requires_real_manifest_sha():
    """method-aware fail-closed: sensitivity_derived cap 은 실 sha 강제 (HIGH-3).

    - method=="sensitivity_derived" + cap 채움 → sensitivity_manifest_sha256 가
      실 sha 여야 한다 (TODO/None 금지). 원래 HIGH-3 fail-closed 보존.
    - method=="spec_anchored" → cap 을 sha 없이 채울 수 있되, spec_basis 가
      반드시 존재하고 phase18 6페어가 derive 입력이 아니어야 한다.
    어떤 method 든 6페어 curve-fit 은 영구 fail-closed.
    """
    prov = vision_veto.SEVERITY_CAP_PROVENANCE
    method = prov.get("method")
    sha = prov.get("sensitivity_manifest_sha256")
    sha_is_real = isinstance(sha, str) and sha not in ("", "TODO")
    cap_filled = any(
        vision_veto.SEVERITY_CAP[k] is not None for k in ("moderate", "major")
    )

    # 6페어 curve-fit 은 모든 경로에서 금지 (method 불문).
    assert prov.get("phase18_pairs_used_for_derivation") is False, (
        "phase18 6페어가 derive 입력으로 표시됨 — curve-fit fail-closed 위반"
    )

    if not cap_filled:
        return

    if method == "sensitivity_derived":
        assert sha_is_real, (
            "sensitivity_derived cap 이 채워졌는데 sensitivity_manifest_sha256 가 "
            f"실 sha 가 아니다 (sha={sha!r}) — curve-fit fail-closed 위반 (HIGH-3)"
        )
    elif method == "spec_anchored":
        spec_basis = prov.get("spec_basis")
        assert isinstance(spec_basis, str) and spec_basis.strip(), (
            "spec_anchored cap 이 채워졌는데 spec_basis 가 없다 — 출처 박제 위반"
        )
    else:
        raise AssertionError(
            f"cap 이 채워졌는데 provenance.method 가 미지값이다: {method!r}"
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
