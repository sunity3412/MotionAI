"""각도 V 마크 적용 조건 게이트 — quick-260814-rcz Task 3.

belle 2026-08-14 (powerspin cand01E): "각도를 표기한다고 해도 잘한 영상쪽 각도가
좀 애매해 저렇게 표기하는게 맞는지 모르겠네".

임계의 **소유자는 MEASURE.md** 이고 이 테스트는 그것을 고정만 한다. 테스트를
통과시키려고 임계를 움직이면 커브핏이므로 금지 — 임계를 바꾸려면 먼저 다시 재고
MEASURE.md 를 갱신해야 한다 ([[recommend-only-after-measuring-the-deciding-fact]]).

표 값은 quick-260814-rcz MEASURE.md §2-1 실측표 그대로다 (승인 코퍼스에서 V 가
실제로 그려진 카드 8건 + belle 채택 후보 cand17B = P, belle 반려 cand01E = N).
"""

from __future__ import annotations

import math

import pytest

from sunity_shared.analysis.fault_zoom import (
    ANGLE_MARK_MAX_PANEL_DIFF_DEG,
    angle_mark_admissible,
)

# ── MEASURE.md §2-1 실측표 (label, ref 사이각, user 사이각) ──────────────────
# P = 통과집합 — 전부 V 가 유지돼야 한다 (승인 무회귀 1급).
MEASURED_PASS = [
    ("elbow/right_elbow", 18.614035012831458, 103.45907549334406),
    ("elbow/right_knee", 170.30981229090804, 175.9879413550348),
    ("pdshapefault/left_elbow", 29.486102732057176, 93.35321792927164),
    ("pdshapefault/left_knee", 93.82616161701502, 131.92112201738868),
    ("pdshapefault/left_shoulder", 159.99996695651387, 151.93072159297313),
    ("pdshapefault/right_elbow", 167.02890688456324, 177.38258164444048),
    ("peterpan/left_shoulder", 149.30943827800795, 164.77100485841947),
    ("powerspin/left_shoulder", 110.42622944972304, 169.5738238793276),
    ("pdshapefault/cand17B/left_elbow", 172.6034941287, 109.74123762695616),
]
# N = 반려집합 — V 가 억제돼야 한다. **표본 1건**(MEASURE.md §3-3).
MEASURED_SUPPRESS = [
    ("powerspin/cand01E/left_shoulder", 64.51029691354823, 178.91443216834273),
]


@pytest.mark.parametrize("label,ref,user", MEASURED_PASS)
def test_measured_pass_set_keeps_mark(label: str, ref: float, user: float) -> None:
    ok, reason = angle_mark_admissible(user, ref)
    assert ok, f"{label}: 승인/채택 카드의 V 가 억제됐다 (사유 {reason})"
    assert reason == "admissible"


@pytest.mark.parametrize("label,ref,user", MEASURED_SUPPRESS)
def test_measured_suppress_set_drops_mark(
    label: str, ref: float, user: float
) -> None:
    ok, reason = angle_mark_admissible(user, ref)
    assert not ok, f"{label}: belle 반려 카드의 V 가 그대로 그려진다"
    assert reason.startswith("panel_diff_")


def test_threshold_lies_strictly_inside_the_measured_gap() -> None:
    """임계는 P 최대와 N 사이에 **엄격히** 있어야 한다 (MEASURE.md §3-1).

    이 단언이 곧 "승인 카드를 죽이지 않는다"의 산술적 증거다 — 임계가 P 최대보다
    작아지는 순간 승인 카드가 조용히 사라진다 (T-rcz-04).
    """
    p_max = max(abs(u - r) for _, r, u in MEASURED_PASS)
    n_min = min(abs(u - r) for _, r, u in MEASURED_SUPPRESS)
    assert p_max < ANGLE_MARK_MAX_PANEL_DIFF_DEG <= n_min, (
        f"임계 {ANGLE_MARK_MAX_PANEL_DIFF_DEG} 가 실측 구간 "
        f"({p_max:.2f}, {n_min:.2f}) 밖"
    )
    # 사전 규칙 §1-3 의 마진 조건 — 분리 마진 >= P 산포의 20%.
    diffs = [abs(u - r) for _, r, u in MEASURED_PASS]
    spread = max(diffs) - min(diffs)
    assert (n_min - p_max) >= spread * 0.20


@pytest.mark.parametrize(
    "user,ref",
    [
        (None, 120.0),
        (120.0, None),
        (None, None),
        (float("nan"), 10.0),
        (10.0, float("inf")),
        ("170", 10.0),
        (True, 10.0),  # bool 은 int 서브클래스라 명시 배제
    ],
)
def test_unmeasurable_fails_open(user, ref) -> None:
    """사이각을 못 재면 오늘과 동일하게 **그린다** — 무회귀 우선."""
    ok, reason = angle_mark_admissible(user, ref)
    assert ok is True
    assert reason == "unmeasurable"


def test_boundary_is_inclusive_on_suppression_side() -> None:
    """임계 정확히 = 억제. 경계 규칙을 코드가 아니라 테스트가 고정한다."""
    thr = ANGLE_MARK_MAX_PANEL_DIFF_DEG
    assert angle_mark_admissible(0.0, thr)[0] is False
    assert angle_mark_admissible(0.0, thr - 0.001)[0] is True


def test_symmetric_in_arguments() -> None:
    """어느 패널을 먼저 넣든 같은 판정 — |Δ| 축이므로 방향 비의존."""
    for _, ref, user in MEASURED_PASS + MEASURED_SUPPRESS:
        assert angle_mark_admissible(user, ref) == angle_mark_admissible(ref, user)


def test_reason_string_carries_the_measured_value() -> None:
    """로그가 배선의 증인 — 사유에 실측값이 실려야 사후 추적이 된다."""
    _, ref, user = MEASURED_SUPPRESS[0]
    ok, reason = angle_mark_admissible(user, ref)
    assert not ok
    assert f"{abs(user - ref):.1f}" in reason


def test_threshold_is_a_single_declared_constant() -> None:
    """임계는 상수 1개 — 동작명/criterion 분기 0 (D-41)."""
    assert isinstance(ANGLE_MARK_MAX_PANEL_DIFF_DEG, float)
    assert math.isfinite(ANGLE_MARK_MAX_PANEL_DIFF_DEG)
    assert 0.0 < ANGLE_MARK_MAX_PANEL_DIFF_DEG < 180.0
