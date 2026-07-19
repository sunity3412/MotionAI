"""visual job 데이터 계약 (상태·outbox·claim·finalize·dispatcher) — 담당 플랜 31-02.

실 Firestore/네트워크/Pod 미접촉 — LOCAL ONLY. 공용 스캐폴드는
backend/tests/phase31/conftest.py 소유.

본 파일은 31-02 Task 1 이 만든 골격이고 Task 3 이 실 검증으로 채운다.
"""

from __future__ import annotations


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
