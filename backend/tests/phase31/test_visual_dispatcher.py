"""dispatcher — 이중 durable cursor 순환 + sent-recovery 재발행 + mark CAS — 담당 플랜 31-09.

실 Firestore/네트워크/Pod 미접촉 — LOCAL ONLY. 공용 스캐폴드(_FakeTransaction 경쟁
transaction·주입 시계·DashScope urllib mock)는 backend/tests/phase31/conftest.py 소유.

본 파일은 31-02 가 만든 **골격**이다. 실제 검증은 31-09 이 채운다 — 그때까지
대상 모듈이 없으므로 `_require()` 가드로 skip 하고, 여기서는 공용 fixture 가
살아 있는지만 확인한다(스캐폴드가 조용히 썩는 것을 막는 최소 계약).
"""

from __future__ import annotations

import pytest

_TARGET = "visual_dispatcher"


def _require():
    """대상 모듈 미존재 시 skip. 31-09 구현 후 자동으로 활성화된다."""
    return pytest.importorskip(
        _TARGET, reason=f"{_TARGET} 은 플랜 31-09 산출물 — 아직 미구현"
    )


def test_scaffold_fake_firestore_alive(fake_firestore):
    """in-memory Firestore seam 이 transaction CAS 를 실제로 검사하는지."""
    from sunity_shared import firestore_admin

    firestore_admin._doc("scaffold/a").set({"n": 1})

    def _bump(tx):
        snap = firestore_admin._doc("scaffold/a").get(transaction=tx)
        tx.update(firestore_admin._doc("scaffold/a"), {"n": snap.to_dict()["n"] + 1})
        return snap.to_dict()["n"]

    firestore_admin._run_in_transaction(_bump)
    assert fake_firestore.store["scaffold/a"]["n"] == 2

