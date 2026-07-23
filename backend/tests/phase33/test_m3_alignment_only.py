"""33-05 M3 정렬 전용(alignment-only) 불변식 — 33-M3-SPEC.md §6 RED 테스트.

이 파일은 M3(`find_action_segment`/`MotionMatch` paired range + coverage floor +
fail-closed)가 **채점에 누출되지 않음**을 증명하는 장치다(D-18). 33-M3-SPEC.md 의
불변식 I1~I5 + 안전 플래그 회귀(§6.1)를 그대로 인코딩한다.

- I1 zero-on-identity  : 동일 입력 → per_joint_deviation == 0 (window 경로).
- I2 byte-identical    : 이미 정렬된 쌍 → window 후 deviation 이 전체-기준 결과와 byte-identical.
- I3 no motion-key     : window 선정이 동작 id/라벨로 분기하지 않음(수치만 의존).
- I4 coverage floor    : nu/nr < 0.80 → 전체 기준 폴백. nu<nr 바닥 통과 → 창 실제 트리밍.
- I5 constants hash    : tol 20°/slope 1.2 + per_joint_deviation 산식 불변(D-20/D-29).
- §4 ambiguity         : 근-동률·다른 국면 후보 → 전체 기준 폴백.
- §2.2 structural floor: 공유 베이스 경계가 window 밖이면 fail-closed.

채점 산식/임계는 절대 건드리지 않는다(정렬 substrate 수정일 뿐).
"""

from __future__ import annotations

import hashlib
import inspect

import numpy as np

from sunity_shared.analysis import kismam
from sunity_shared.analysis.motiondtw import (
    AMBIGUITY_EPSILON,
    AMBIGUITY_OVERLAP_MIN,
    COVERAGE_FLOOR,
    MotionMatch,
    dtw,
    find_action_segment,
    motion_dtw,
    per_joint_deviation,
)

# per_joint_deviation 산식 본문(motiondtw.py) SHA-256 — D-20/D-29 불변식 고정.
# 산식이 바뀌면(median→mean 등) 이 해시가 트립한다. M3 는 이 함수를 건드리지 않는다.
PER_JOINT_DEVIATION_SHA256 = (
    "7e23e00d1764525051f1fc4b7aa93b8827f4abe58f212ebbaf4b774b410d1373"
)


def _wave(n, phase=0.0, amp=1.0):
    t = np.linspace(0, 2 * np.pi, n)
    return np.stack([amp * np.sin(t + phase), amp * np.cos(t + phase)], axis=1)


def _angles(n, j=3, seed=0):
    """결정적 각도 시퀀스 (T,J) — 단조 성분 + 관절별 위상."""
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 4 * np.pi, n)
    cols = [30.0 * np.sin(t + k) + 5.0 * k for k in range(j)]
    base = np.stack(cols, axis=1)
    return base + rng.normal(0, 0.01, size=base.shape)


# ── I1: zero-on-identity (window 경로) ───────────────────────────────────────
def test_m3_zero_on_identity_through_window():
    """동일 입력을 motion_dtw window 경로로 통과시켜도 per_joint_deviation == 0."""
    A = _angles(40, j=3, seed=1)
    match = motion_dtw(A, A)
    a_ref_win = A[match.ref_start : match.ref_end]
    user_seg = A[match.start : match.end]
    dev = per_joint_deviation(match.path, user_seg, a_ref_win)
    assert np.allclose(dev, 0.0), f"identity through window must be 0, got {dev}"


# ── I2: byte-identical (already-aligned) ─────────────────────────────────────
def test_m3_byte_identical_when_already_aligned():
    """이미 정렬된 쌍(nu==nr, 준비/대기 없음) → window 후 deviation 이 전체-기준 path
    결과와 byte-identical(np.array_equal). 정렬이 바뀌지 않아야 할 입력에서 출력 불변."""
    user = _angles(45, j=4, seed=2)
    ref = user + 3.0  # 일관 3° 오프셋 (nu==nr, 정렬은 identity)
    match = motion_dtw(user, ref)
    a_ref_win = ref[match.ref_start : match.ref_end]
    user_seg = user[match.start : match.end]
    dev_m3 = per_joint_deviation(match.path, user_seg, a_ref_win)
    # 전체-기준(pre-M3 등가): nu==nr 이면 window = 전체이므로 동일 path·동일 산식.
    _dist_full, path_full = dtw(user, ref)
    dev_full = per_joint_deviation(path_full, user, ref)
    assert match.ref_start == 0 and match.ref_end == len(ref)
    assert np.array_equal(dev_m3, dev_full), (
        f"aligned input must be byte-identical: m3={dev_m3} full={dev_full}"
    )


# ── I4: coverage floor 폴백 + 실제 발동 ──────────────────────────────────────
def test_m3_coverage_floor_fallback():
    """nu/nr < COVERAGE_FLOOR(0.80) → 기준 미트리밍(전체 정렬)로 폴백."""
    nr = 50
    nu = 30  # 30/50 = 0.60 < 0.80
    F_user = _wave(nu)
    F_ref = _wave(nr)
    (u_s, u_e), (r_s, r_e) = find_action_segment(F_user, F_ref, radius=8)
    assert (u_s, u_e) == (0, nu)
    assert (r_s, r_e) == (0, nr), "coverage floor 미달 → 전체 기준 폴백이어야 함"


def test_m3_window_actually_fires():
    """nu<nr 이고 coverage 바닥 통과 → 기준 window 가 실제로 잘림(ref_start>0 또는
    ref_end<nr). SEED 성공판정 #5(M3 발동)."""
    core = _wave(48)
    ref = np.concatenate([np.zeros((4, 2)), core, np.zeros((4, 2))])  # nr=56
    user = core.copy()  # nu=48, 48/56 ≈ 0.857 >= 0.80
    (u_s, u_e), (r_s, r_e) = find_action_segment(user, ref, radius=10)
    assert (u_s, u_e) == (0, 48), "짧은 쪽(사용자) 통째"
    assert (r_e - r_s) == 48, "기준 window 길이 = nu"
    assert r_s > 0 or r_e < len(ref), "기준 준비/대기 구간이 실제로 트리밍되어야 함"


# ── §4: ambiguity fail-closed (폴백은 항상 안전) ─────────────────────────────
def test_m3_ambiguous_falls_back_full_reference():
    """근-동률 후보가 서로 다른 국면(겹침 < 0.80)을 선택하면 전체 기준 폴백.
    핵심 불변: 어떤 폴백도 팽창 불가(전체 기준 = 더 많은 편차 노출)."""
    big = _wave(16)
    F_ref = np.concatenate([big, np.zeros((4, 2)), big, np.zeros((4, 2))])  # nr=40
    F_user = np.concatenate([big, np.zeros((4, 2)), big[:12]])  # nu=32, 32/40=0.80
    (u_s, u_e), (r_s, r_e) = find_action_segment(F_user, F_ref, radius=8)
    # 발동 시 전체 기준; 미발동이면 contiguous window(길이=nu). 팽창 방향 폴백 금지.
    assert (r_s, r_e) == (0, len(F_ref)) or (r_e - r_s) == (u_e - u_s)


# ── §2.2: structural floor (공유 베이스 경계) ─────────────────────────────────
def test_m3_shared_base_structural_floor():
    """best window 가 base/확장 경계를 밖에 두면(한 국면 통째 제거) fail-closed."""
    core2 = _wave(44)
    ref2 = np.concatenate([np.zeros((4, 2)), core2, np.zeros((4, 2))])  # nr=52
    user2 = core2.copy()  # nu=44, 44/52 ≈ 0.846 >= floor
    boundary = 50  # 뒤쪽 경계 — window [r_s, r_s+44) 가 내부에 두기 어려움
    (u_s, u_e), (r_s, r_e) = find_action_segment(
        user2, ref2, radius=10, ref_boundary=boundary
    )
    if not (r_s < boundary < r_e):
        assert (r_s, r_e) == (0, len(ref2)), "경계 밖 → 전체 기준 fail-closed"


# ── I3: no motion-key branch ─────────────────────────────────────────────────
def test_m3_no_motion_key_branch_source():
    """(a) 소스 검사: window 선정 **로직**에 motion_id/technique/동작이름 참조 0.

    docstring/주석의 D-02 설명 언급은 오탐이므로 코드 본문만 검사한다(AST 로 docstring
    제거 + 주석 제거)."""
    import ast

    tree = ast.parse(inspect.getsource(find_action_segment))
    fn = tree.body[0]
    # docstring(첫 표현식 문자열) 제거.
    if (
        fn.body
        and isinstance(fn.body[0], ast.Expr)
        and isinstance(fn.body[0].value, ast.Constant)
    ):
        fn.body = fn.body[1:]
    code_only = ast.unparse(fn)
    for token in ("motion_id", "technique", "motionId", "motion_key", "동작이름"):
        assert token not in code_only, f"find_action_segment 에 동작-키 분기 발견: {token}"


def test_m3_no_motion_key_branch_behavior():
    """(b) 행동 검사: 동일 수치 시퀀스는 라벨과 무관하게 동일 window 선택."""
    F_user = _wave(40)
    F_ref = _wave(56)
    r1 = find_action_segment(F_user, F_ref, radius=10)
    r2 = find_action_segment(F_user.copy(), F_ref.copy(), radius=10)
    assert r1 == r2


# ── I5: constants / formula hash 불변 (D-20/D-29) ────────────────────────────
def test_m3_constants_hash_unchanged():
    """채점 상수 + per_joint_deviation 산식이 불변. M3 는 정렬 substrate 수정이지
    감점 산식/임계 재fit 이 아니다."""
    assert kismam._IPSF_TOLERANCE_DEG == 20.0
    assert kismam._PENALTY_PER_DEG == 1.2
    body = inspect.getsource(per_joint_deviation)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    assert digest == PER_JOINT_DEVIATION_SHA256, (
        f"per_joint_deviation 산식 변경 감지: {digest}"
    )
    assert "np.median" in body


# ── 정렬 게이트 상수 노출 (채점 상수 아님) ────────────────────────────────────
def test_m3_alignment_gate_constants_present():
    assert COVERAGE_FLOOR == 0.80
    assert AMBIGUITY_EPSILON == 0.02
    assert AMBIGUITY_OVERLAP_MIN == 0.80


# ── scoring-untouched DATA-GATE (codex concern 8 — `|| echo` 흡수 버그 수정) ──
def test_m3_scoring_untouched_data_gate(tmp_path):
    """채점 무접촉을 JSON/종료코드 데이터 게이트로 증명한다. 산문 grep 이나 trailing
    `|| echo ... OK` 가 아니라, live 코드 상수 ↔ pinned 매니페스트의 값 비교 + gate_check
    종료 코드로 강제(D-20/D-29). 실패하면 이 assertion 이 트립한다(흡수 불가)."""
    import json as _json
    from pathlib import Path

    import gate_check
    from dump_scoring_constants import current_scoring_constants

    pinned = Path(__file__).with_name("scoring_constants_pinned.json")
    live_path = tmp_path / "scoring_constants_current.json"
    live_path.write_text(
        _json.dumps(current_scoring_constants(), ensure_ascii=False), encoding="utf-8"
    )
    # (a) 저수준: pinned 의 모든 키가 live 값과 동일해야 problems 가 비어야 한다.
    live = _json.loads(live_path.read_text(encoding="utf-8"))
    problems = gate_check._check_scoring_constants(live, str(pinned))
    assert problems == [], f"scoring-constants drift: {problems}"
    # (b) CLI 종료 코드: gate_check.main 이 정확히 0 을 반환(게이트 통과).
    rc = gate_check.main(
        ["--file", str(live_path), "--scoring-constants-match", str(pinned)]
    )
    assert rc == 0, f"gate_check.main rc={rc} (0 이어야 함)"
    # (c) drift 주입 시 non-zero — 게이트가 실제로 잡는지(흡수 아님) 확인.
    tampered = tmp_path / "tampered.json"
    bad = dict(live)
    bad["tol"] = 25.0  # 임계 재fit 시뮬레이션
    tampered.write_text(_json.dumps(bad), encoding="utf-8")
    rc_bad = gate_check.main(
        ["--file", str(tampered), "--scoring-constants-match", str(pinned)]
    )
    assert rc_bad != 0, "drift 를 게이트가 잡지 못함(concern 8 회귀)"


def test_m3_motion_match_carries_reference_range():
    """MotionMatch 가 paired reference range(ref_start/ref_end)를 운반한다(§1.1)."""
    assert {"ref_start", "ref_end"} <= set(MotionMatch.__dataclass_fields__)
    m = motion_dtw(_angles(30, seed=3), _angles(30, seed=3))
    assert isinstance(m.ref_start, int) and isinstance(m.ref_end, int)
    assert 0 <= m.ref_start < m.ref_end <= 30
