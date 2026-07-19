"""SAM template 배선 게이트 (lease/visibility/timeout 부등식 — H6-07/H10-06) — 담당 플랜 31-10.

실 Firestore/네트워크/Pod 미접촉 — LOCAL ONLY. 공용 스캐폴드(_FakeTransaction 경쟁
transaction·주입 시계·DashScope urllib mock)는 backend/tests/phase31/conftest.py 소유.

본 파일은 31-02 가 만든 **골격**이다. 실제 검증은 31-10 이 채운다 — 그때까지
대상 모듈이 없으므로 `_require()` 가드로 skip 하고, 여기서는 공용 fixture 가
살아 있는지만 확인한다(스캐폴드가 조용히 썩는 것을 막는 최소 계약).
"""

from __future__ import annotations

import pytest

_TARGET = "visual_dispatch"


def _require():
    """대상 모듈 미존재 시 skip. 31-10 구현 후 자동으로 활성화된다."""
    return pytest.importorskip(
        _TARGET, reason=f"{_TARGET} 은 플랜 31-10 산출물 — 아직 미구현"
    )


def test_scaffold_fake_clock_alive(fake_clock):
    """주입 시계가 단조 전진하는지 — lease 만료 전/후 결정론 재현의 전제."""
    start = fake_clock()
    assert fake_clock.advance(1000) == start + 1000
    assert fake_clock() == start + 1000

