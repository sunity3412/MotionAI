"""Phase 22 Plan 22-03 Task 1 — firestore_admin.store_vlm_shadow helper 검증.

D-10c(증류 라벨 즉시 적재) + D-13(shadow 병행) + D-12(PII 금지) 정합. Firestore
client 는 전부 mock/stub — 실 Firestore/네트워크/Pod 미접촉 (LOCAL ONLY). set(merge=True)
멱등 누적 + created_at 첫 기록 보존 + nested-array 사전 차단 + PII 키 거부를 강제한다.

배선(Task 2) / Pod 실측(Task 4)은 belle-gated 후속 세션으로 이월 — 본 파일은 helper
4종만 검증한다.
"""

from __future__ import annotations

import pytest

from sunity_shared import firestore_admin


# ─── Firestore client stub (실 Firestore/네트워크 0) ──────────────────────────


def _deep_merge(base: dict, patch: dict) -> dict:
    """Firestore set(merge=True) 의 nested-map deep merge 모사."""
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


class _FakeSnapshot:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data) if self._data else {}


class _FakeDoc:
    def __init__(self, registry, path):
        self._registry = registry
        self._path = path

    def get(self):
        return _FakeSnapshot(self._registry["store"].get(self._path))

    def set(self, payload, merge=False):
        self._registry["set_calls"].append(
            {"path": self._path, "payload": payload, "merge": merge}
        )
        store = self._registry["store"]
        if merge and self._path in store:
            store[self._path] = _deep_merge(dict(store[self._path]), payload)
        else:
            store[self._path] = dict(payload)


class _FakeTime:
    """firestore_admin.time 대체 — 결정적 ms epoch 검증."""

    def __init__(self, seq):
        self._seq = iter(seq)

    def time(self):
        return next(self._seq)


@pytest.fixture
def fake_firestore(monkeypatch):
    registry = {"store": {}, "set_calls": []}
    monkeypatch.setattr(
        firestore_admin, "_doc", lambda path: _FakeDoc(registry, path)
    )
    return registry


# ─── Test 1: set(merge=True) + created_at/updated_at ms epoch ─────────────────


def test_store_vlm_shadow_writes_merge_and_timestamps(fake_firestore):
    firestore_admin.store_vlm_shadow(
        "hash123",
        "veto",
        {
            "verdict": "fail",
            "prompt_version": "v3",
            "schema_version": 2,
            "model": "gemini-3.5-flash",
            "status": "applied",
        },
    )
    calls = fake_firestore["set_calls"]
    assert len(calls) == 1
    call = calls[0]
    assert call["path"] == "vlm_shadow/hash123"
    assert call["merge"] is True
    p = call["payload"]
    assert p["video_hash"] == "hash123"
    assert isinstance(p["created_at"], int)
    assert isinstance(p["updated_at"], int)
    assert p["roles"]["veto"]["verdict"] == "fail"
    assert p["roles"]["veto"]["model"] == "gemini-3.5-flash"


def test_store_vlm_shadow_preserves_created_at(fake_firestore, monkeypatch):
    # 첫 기록 시각(created_at)은 재호출에도 보존, updated_at 만 갱신.
    monkeypatch.setattr(firestore_admin, "time", _FakeTime([1.0, 2.0]))
    firestore_admin.store_vlm_shadow("h", "veto", {"verdict": "a"})
    firestore_admin.store_vlm_shadow("h", "coach", {"text": "b"})
    doc = fake_firestore["store"]["vlm_shadow/h"]
    assert doc["created_at"] == 1000  # 첫 기록 시각 보존
    assert doc["updated_at"] == 2000  # 최신 갱신


# ─── Test 2: nested array (list-of-list) → TypeError, 저장 전 차단 ────────────


def test_store_vlm_shadow_rejects_nested_array(fake_firestore):
    with pytest.raises(TypeError):
        firestore_admin.store_vlm_shadow(
            "hash123",
            "recognizer",
            {"checkpoints": [[1, 2], [3, 4]]},  # firestore nested array 금지
        )
    assert fake_firestore["set_calls"] == []  # 저장 시도조차 없어야 함


# ─── Test 3: PII 키 포함 → ValueError, 저장 전 차단 ──────────────────────────


@pytest.mark.parametrize(
    "pii",
    [
        {"uid": "abc123"},
        {"email": "a@b.com"},
        {"userId": "u-1"},
        {"phoneNumber": "010-0000-0000"},
    ],
)
def test_store_vlm_shadow_rejects_pii_keys(fake_firestore, pii):
    payload = {"verdict": "fail", **pii}
    with pytest.raises(ValueError):
        firestore_admin.store_vlm_shadow("hash123", "veto", payload)
    assert fake_firestore["set_calls"] == []


def test_store_vlm_shadow_rejects_nested_pii(fake_firestore):
    # 중첩 dict 안의 식별자도 거부 (재귀 검증).
    with pytest.raises(ValueError):
        firestore_admin.store_vlm_shadow(
            "hash123", "coach", {"meta": {"userId": "u1"}}
        )
    assert fake_firestore["set_calls"] == []


def test_store_vlm_shadow_allows_domain_scalars(fake_firestore):
    # 도메인 측정 스칼라/좌표명(motionName, jointName 등)은 PII 아님 — 통과.
    firestore_admin.store_vlm_shadow(
        "hash123",
        "recognizer",
        {"motionName": "power-spin", "jointName": "left_hip", "angleDeg": 172.5},
    )
    assert len(fake_firestore["set_calls"]) == 1


# ─── Test 4: 같은 video_hash 재호출 시 role별 서브필드 merge (기존 미파괴) ─────


def test_store_vlm_shadow_accumulates_roles(fake_firestore):
    firestore_admin.store_vlm_shadow("h", "veto", {"verdict": "fail"})
    firestore_admin.store_vlm_shadow("h", "coach", {"text": "hi"})
    doc = fake_firestore["store"]["vlm_shadow/h"]
    assert doc["roles"]["veto"]["verdict"] == "fail"  # 기존 role 미파괴
    assert doc["roles"]["coach"]["text"] == "hi"  # 신규 role 누적


# ─── role 검증 ────────────────────────────────────────────────────────────────


def test_store_vlm_shadow_rejects_unknown_role(fake_firestore):
    with pytest.raises(ValueError):
        firestore_admin.store_vlm_shadow("h", "bogus", {"x": 1})
    assert fake_firestore["set_calls"] == []


def test_store_vlm_shadow_rejects_empty_video_hash(fake_firestore):
    with pytest.raises(ValueError):
        firestore_admin.store_vlm_shadow("", "veto", {"verdict": "fail"})
    assert fake_firestore["set_calls"] == []
