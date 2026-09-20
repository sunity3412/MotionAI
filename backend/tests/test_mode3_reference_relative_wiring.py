"""mode3 기준 축 배선 — 플래그 OFF 는 종전 그대로, ON 은 기준 각도로 감점한다.

왜 이 시험이 있나 (quick-260920-m3r, belle 2026-09-20)
──────────────────────────────────────────────────────
belle: *"mode3 학생 비교는 틀리고 맞고가 아니라 발전해냐 안했냐겠지?"*

mode3 종합점수는 지금 **떨림 단독**이다. 동작을 모른다고 보아 line 차원이 구조적으로
안 생기고, 이전 영상 대비 유사도는 종합에서 일부러 뺐다 — 발전하면 못하던 과거의 나와
덜 비슷해져 점수가 역전되기 때문이다([[mode3-overall-exclude-angle-similarity]]).
그래서 mode3 에는 움직이지 않는 잣대가 없다. 기준 선수 각도가 그 잣대다.

이 배선은 **학생 영상으로 검증되기 전**이라 기본 OFF 다. 그래서 시험이 두 가지를 건다:
  1. OFF 면 산출이 종전과 같다 — 켜지 않은 채 머지해도 라이브가 안 움직인다
  2. ON 이면 실제로 기준 각도가 감점에 들어가고, **라벨이 그 사실을 말한다**

2번이 중요한 이유: 절대트랙 라벨(`recognized_motion_absolute`)을 단 채 기준 비교
점수를 내면 화면이 채점 출처를 틀리게 말한다 — TRUST-03 이 막으려던 바로 그것이다.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "shared" / "python"))


def _load_app():
    spec = importlib.util.spec_from_file_location(
        "pipeline_app_m3r", _ROOT / "functions" / "pipeline" / "app.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


app = _load_app()

from sunity_shared.analysis import assemble  # noqa: E402


# ── 1. 플래그 ─────────────────────────────────────────────────────────────────

def test_flag_defaults_off(monkeypatch):
    """기본 OFF — env 미설정이면 배선이 안 돈다.

    학생 영상이 이 축을 한 번도 안 탔다. 켜는 것은 세 관문(같은 기준에 일관되게
    붙나 / 강사 ○× 와 방향이 맞나 / 카메라 각도 변화를 견디나) 뒤다.
    """
    monkeypatch.delenv("MODE3_REFERENCE_RELATIVE_ENABLED", raising=False)
    assert app._mode3_reference_relative_enabled() is False


@pytest.mark.parametrize("raw,expected", [
    ("1", True), ("true", True), ("TRUE", True),
    ("0", False), ("false", False), ("", False),
])
def test_flag_falsy_set_matches_house_convention(monkeypatch, raw, expected):
    """falsy set 은 리포 관례(`_SYNTHESIS_FALSY`)와 같은 것을 쓴다 — 새 규칙 0."""
    monkeypatch.setenv("MODE3_REFERENCE_RELATIVE_ENABLED", raw)
    assert app._mode3_reference_relative_enabled() is expected


# ── 2. 라벨이 산출을 따라간다 ────────────────────────────────────────────────

def test_basis_label_reports_reference_comparison_when_it_happened():
    """기준 비교로 점수를 냈으면 라벨도 그렇게 말해야 한다.

    절대트랙 라벨을 단 채 기준 비교 점수를 내는 것이 TRUST-03 이 막으려던 결함이다.
    """
    assert app._mode3_scoring_basis(
        is_first=True, is_reference_free=False, reference_relative=True
    ) == assemble.MODE3_SCORING_BASIS_RECOGNIZED_REFERENCE_RELATIVE
    assert app._mode3_scoring_basis(
        is_first=False, is_reference_free=False, reference_relative=True
    ) == assemble.MODE3_SCORING_BASIS_PREV_PLUS_REFERENCE_RELATIVE


def test_basis_label_unchanged_when_axis_did_not_fire():
    """배선이 안 돌았으면 네 값 전부 종전 그대로 — 기본 인자도 False."""
    assert app._mode3_scoring_basis(is_first=True, is_reference_free=True) == (
        assemble.MODE3_SCORING_BASIS_REFERENCE_FREE_ABSOLUTE
    )
    assert app._mode3_scoring_basis(is_first=True, is_reference_free=False) == (
        assemble.MODE3_SCORING_BASIS_RECOGNIZED_ABSOLUTE
    )
    assert app._mode3_scoring_basis(is_first=False, is_reference_free=True) == (
        assemble.MODE3_SCORING_BASIS_PREV_PLUS_REFERENCE_FREE
    )
    assert app._mode3_scoring_basis(is_first=False, is_reference_free=False) == (
        assemble.MODE3_SCORING_BASIS_PREV_PLUS_ABSOLUTE
    )


def test_unregistered_motion_can_never_claim_reference_relative():
    """미등재는 기준을 못 찾는다 — 라벨이 기준 비교를 주장할 수 없다.

    D-08("미보유에 확신 점수 금지")이 서 있는 구분이라 방어 guard 를 건다.
    """
    for is_first in (True, False):
        basis = app._mode3_scoring_basis(
            is_first=is_first, is_reference_free=True, reference_relative=True
        )
        assert "reference_relative" not in basis


def test_new_bases_are_accepted_by_the_builder_contract():
    """build_mode3 가 두 신규 값을 거부하지 않는다 (계약 lockstep 확인)."""
    for basis in (
        assemble.MODE3_SCORING_BASIS_RECOGNIZED_REFERENCE_RELATIVE,
        assemble.MODE3_SCORING_BASIS_PREV_PLUS_REFERENCE_RELATIVE,
    ):
        out = assemble.build_mode3(is_first=True, scoring_basis=basis)
        assert out["scoringBasis"] == basis
        # 라벨은 선수 이름을 박지 않는다 — 기준 라이브러리가 바뀌면 과거 분석의
        # 라벨이 거짓이 된다 ([[display-string-is-not-a-join-key]]).
        assert out["scoringBasisLabel"]
        assert "정은지" not in out["scoringBasisLabel"]


def test_mode1_basis_never_leaks_into_mode3():
    """reference_motion 은 여전히 Mode1 전용 — 값을 늘렸다고 이 벽이 무너지면 안 된다."""
    with pytest.raises(ValueError):
        assemble.build_mode3(
            is_first=True, scoring_basis=assemble.MODE1_SCORING_BASIS
        )


# ── 3. 감점 경로에 실제로 닿는가 ─────────────────────────────────────────────

def _straight_and_bent():
    """같은 동작을 '기준처럼 편' 판과 '많이 굽힌' 판으로 만든다."""
    from sunity_shared.analysis.skeleton import JOINT_KEYS

    t, j = 40, len(JOINT_KEYS)
    ref = np.full((t, j), 175.0, dtype=float)
    bent = np.full((t, j), 120.0, dtype=float)  # 기준 대비 55도 부족
    return ref, bent


def test_reference_angles_reach_the_deduction_builder():
    """기준 각도를 주면 `angle_vs_reference__*` 가 감점 md 에 실린다.

    이 시험이 배선의 심장이다 — 이 키가 안 서면 `tally` 가 `dimension_overall`
    폴백(= 오늘의 떨림 점수)으로 떨어져 배선이 조용히 사문이 된다
    (`deduction_engine.py` — `if quant_unavailable and not activated`).
    """
    from sunity_shared.analysis import technique
    from sunity_shared.analysis.skeleton import JOINT_KEYS

    ref, bent = _straight_and_bent()
    nj = len(JOINT_KEYS)
    _dev, match, _seg, a_ref = app._deviation_against(
        bent, ref.reshape(-1).tolist(), nj
    )
    profile = technique.TechniqueProfile(
        name="테스트", category="recognized",
        joint_expectations={k: technique.JOINT_BENT_OK for k in JOINT_KEYS},
        motion_id="ref-test",
    )
    md = app._build_deduction_measured_deviations(
        angles=bent, profile=profile, assessments=None, dimension_scores=None,
        quantification=None, reference_dtw_match=match, reference_angles=a_ref,
    )
    emitted = [k for k in md if k.startswith("angle_vs_reference__")]
    assert emitted, "기준을 줬는데 reference_relative 키가 0개 — 배선이 사문이다"
    # 55도 부족이 그대로 실려야 한다 (허용오차 20도를 크게 넘는다).
    assert max(md[k] for k in emitted) > 40.0


def test_no_reference_means_no_reference_relative_keys():
    """기준이 없으면 그 키는 안 나온다 — 플래그 OFF 인 오늘의 mode3 가 이 상태다."""
    from sunity_shared.analysis import technique
    from sunity_shared.analysis.skeleton import JOINT_KEYS

    _ref, bent = _straight_and_bent()
    profile = technique.TechniqueProfile(
        name="테스트", category="recognized",
        joint_expectations={k: technique.JOINT_BENT_OK for k in JOINT_KEYS},
        motion_id="ref-test",
    )
    md = app._build_deduction_measured_deviations(
        angles=bent, profile=profile, assessments=None, dimension_scores=None,
        quantification=None, reference_dtw_match=None, reference_angles=None,
    )
    assert not [k for k in md if k.startswith("angle_vs_reference__")]


# ── 4. 배선이 확대카드·정렬·veto 를 건드리지 않는다 ──────────────────────────

def test_wiring_feeds_only_the_deduction_builder():
    """mode3 기준 축은 감점 builder 한 곳에만 주입된다.

    `reference_dtw_match` / `reference_angles_for_veto` 는 소비처가 여섯이고 그중
    셋(safety flags · motionAlignment · fault-zoom 확대카드)은 이미 mode 로 분기돼
    있다. mode3 에서 그 두 변수를 채우면 확대카드가 "지난 영상 대비"에서 "기준 선수
    대비"로 조용히 바뀐다 — belle 이 승인한 것은 **채점 축**이지 카드 문법이 아니다.

    그래서 구조로 못박는다 — 허용된 자리를 **이름으로** 적는다. 새 소비처가 생기면
    목록에 없는 줄이 나와 여기서 걸린다.
    """
    src = (_ROOT / "functions" / "pipeline" / "app.py").read_text(encoding="utf-8")
    allowed = {
        "mode3_ref_angles = None",                        # 초기화
        "mode3_ref_dtw_match, mode3_ref_angles, mode3_ref_fps = (",  # 배선 호출
        "reference_relative=mode3_ref_angles is not None,",  # 라벨이 산출을 따라감
        "else mode3_ref_angles",                          # 감점 builder 인자
    }
    code_lines = [
        ln.strip() for ln in src.splitlines() if not ln.strip().startswith("#")
    ]
    leaked = [
        ln for ln in code_lines if "mode3_ref_angles" in ln and ln not in allowed
    ]
    assert not leaked, (
        "mode3 기준 축이 승인된 자리 밖으로 샜다 — 확대카드/정렬/veto 가 같이 "
        "움직인다(belle 이 승인한 것은 채점 축이지 카드 문법이 아니다):\n  "
        + "\n  ".join(leaked)
    )
    # 짝이 되는 match 변수도 같은 방식으로 가둔다.
    allowed_match = {
        "mode3_ref_dtw_match = None",
        "mode3_ref_dtw_match, mode3_ref_angles, mode3_ref_fps = (",
        "reference_dtw_match=reference_dtw_match or mode3_ref_dtw_match,",
    }
    leaked_match = [
        ln for ln in code_lines
        if "mode3_ref_dtw_match" in ln and ln not in allowed_match
    ]
    assert not leaked_match, (
        "mode3 기준 DTW 정렬이 승인된 자리 밖으로 샜다:\n  " + "\n  ".join(leaked_match)
    )
    # 확대카드(fault-zoom)는 여전히 mode1 전용 변수만 읽는다 — mode3 는 이전 영상.
    assert "dtw_match=reference_dtw_match,\n" in src


# ── 5. 플래그가 켜졌을 때의 경로 ─────────────────────────────────────────────
#
# 위 시험들은 전부 OFF 상태의 산출을 지킨다. 정작 **켜면 무슨 일이 나는지**가 시험
# 밖에 있으면, 스위치를 올리는 사람이 처음 보는 코드를 라이브에서 처음 돌리게 된다.
# 그래서 배선을 부를 수 있는 함수(`_mode3_reference_axis`)로 두고 여기서 실행한다.

def _profile(motion_id="ref-test"):
    from sunity_shared.analysis import technique
    from sunity_shared.analysis.skeleton import JOINT_KEYS

    return technique.TechniqueProfile(
        name="테스트", category="recognized",
        joint_expectations={k: technique.JOINT_BENT_OK for k in JOINT_KEYS},
        motion_id=motion_id,
    )


def _ref_doc():
    from sunity_shared.analysis.skeleton import JOINT_KEYS

    ref, _bent = _straight_and_bent()
    return {
        "angles": ref.reshape(-1).tolist(),
        "anglesJointKeys": list(JOINT_KEYS),
        "keypointReport": {"fps": 18.0},
    }


def test_axis_is_silent_while_the_flag_is_off(monkeypatch):
    """OFF 면 Firestore 를 **읽지도 않는다** — 켜지 않은 채 머지해도 비용 0."""
    monkeypatch.delenv("MODE3_REFERENCE_RELATIVE_ENABLED", raising=False)
    calls = []
    monkeypatch.setattr(
        app, "_match_reference_by_motion_id", lambda m: calls.append(m)
    )
    _ref, bent = _straight_and_bent()
    assert app._mode3_reference_axis(bent, _profile()) == (None, None, 0.0)
    assert calls == [], "플래그가 꺼졌는데 기준 doc 을 읽었다 (읽기 비용 + 오염 위험)"


def test_axis_fires_and_feeds_real_deviations_when_on(monkeypatch):
    """ON 이면 기준 각도가 실제로 감점 md 에 닿는다 — 배선의 끝까지 따라간다."""
    monkeypatch.setenv("MODE3_REFERENCE_RELATIVE_ENABLED", "1")
    monkeypatch.setattr(app, "_match_reference_by_motion_id", lambda m: _ref_doc())
    _ref, bent = _straight_and_bent()

    match, a_ref, fps = app._mode3_reference_axis(bent, _profile())
    assert match is not None and a_ref is not None
    assert fps == 18.0, "기준 doc 의 fps 를 안 썼다 — 점수 창과 표시 창이 어긋난다"

    md = app._build_deduction_measured_deviations(
        angles=bent, profile=_profile(), assessments=None, dimension_scores=None,
        quantification=None, reference_dtw_match=match, reference_angles=a_ref,
        ref_fps=fps or None,
    )
    emitted = [k for k in md if k.startswith("angle_vs_reference__")]
    assert emitted, "플래그를 켰는데 기준 대비 감점이 0개 — 배선이 사문이다"
    assert max(md[k] for k in emitted) > 40.0


def test_unrecognized_motion_gets_no_axis_even_when_on(monkeypatch):
    """동작을 모르면 켜져 있어도 안 붙인다 — 근거 없는 확신 점수 금지(D-08)."""
    monkeypatch.setenv("MODE3_REFERENCE_RELATIVE_ENABLED", "1")
    monkeypatch.setattr(app, "_match_reference_by_motion_id", lambda m: None)
    _ref, bent = _straight_and_bent()
    assert app._mode3_reference_axis(bent, _profile(motion_id=None)) == (
        None, None, 0.0
    )


def test_alignment_failure_degrades_to_todays_mode3(monkeypatch):
    """정렬이 깨지면 예외를 던지지 않고 종전 mode3 로 강등한다 — 분석이 죽지 않는다."""
    monkeypatch.setenv("MODE3_REFERENCE_RELATIVE_ENABLED", "1")
    monkeypatch.setattr(app, "_match_reference_by_motion_id", lambda m: _ref_doc())

    def _boom(*a, **k):
        raise RuntimeError("정렬 실패 시뮬레이션")

    monkeypatch.setattr(app, "_deviation_against", _boom)
    _ref, bent = _straight_and_bent()
    assert app._mode3_reference_axis(bent, _profile()) == (None, None, 0.0)
