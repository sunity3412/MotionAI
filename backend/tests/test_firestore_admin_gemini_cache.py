"""firestore_admin Gemini cache helper 단위 테스트 (Plan 5-02 Task 2).

박제 정신 (Plan 5-02 PLAN must_haves):
  · D-14 gemini_cache/{hash} 컬렉션 박제 (전역 공유, uid 비의존)
  · D-09 case 3 분기 3 자동 수집 (TERM-DATA-01 정합 — Phase 16 schema)
  · [[firestore-nested-array-flat]] — moments[i] 안 list 거부 (TypeError)
  · D-16 lazy import — firebase_admin 모듈 로드 시점 0 import

모든 테스트는 stdlib + pytest 만 사용 — 실제 Firestore 호출 0 (mock client).
"""

from __future__ import annotations

import sys
from typing import Any

import pytest


# ─────────────────── mock Firestore 인프라 ───────────────────


class _FakeSnapshot:
    def __init__(self, exists: bool, data: dict | None = None) -> None:
        self.exists = exists
        self._data = data

    def to_dict(self) -> dict | None:
        return self._data


class _FakeDocRef:
    def __init__(self, path: str, store: dict[str, dict]) -> None:
        self.path = path
        self._store = store
        self.set_calls: list[tuple[dict, dict]] = []  # (payload, kwargs)

    def get(self) -> _FakeSnapshot:
        if self.path in self._store:
            return _FakeSnapshot(True, dict(self._store[self.path]))
        return _FakeSnapshot(False, None)

    def set(self, payload: dict, **kwargs: Any) -> None:
        self.set_calls.append((dict(payload), dict(kwargs)))
        merge = kwargs.get("merge", False)
        if merge and self.path in self._store:
            existing = dict(self._store[self.path])
            # Increment / ArrayUnion mock 처리
            for k, v in payload.items():
                if isinstance(v, _MockIncrement):
                    existing[k] = existing.get(k, 0) + v.delta
                elif isinstance(v, _MockArrayUnion):
                    arr = list(existing.get(k, []))
                    for item in v.values:
                        if item not in arr:
                            arr.append(item)
                    existing[k] = arr
                else:
                    existing[k] = v
            self._store[self.path] = existing
        else:
            # Increment / ArrayUnion 첫 박제 처리
            resolved: dict[str, Any] = {}
            for k, v in payload.items():
                if isinstance(v, _MockIncrement):
                    resolved[k] = v.delta
                elif isinstance(v, _MockArrayUnion):
                    resolved[k] = list(v.values)
                else:
                    resolved[k] = v
            self._store[self.path] = resolved


class _MockIncrement:
    def __init__(self, delta: int) -> None:
        self.delta = delta


class _MockArrayUnion:
    def __init__(self, values: list) -> None:
        self.values = list(values)


class _FakeFirestore:
    """firestore_admin._db() / _doc() 우회 박제 fake."""

    def __init__(self) -> None:
        self.store: dict[str, dict] = {}
        self.doc_refs: dict[str, _FakeDocRef] = {}

    def document(self, path: str) -> _FakeDocRef:
        if path not in self.doc_refs:
            self.doc_refs[path] = _FakeDocRef(path, self.store)
        return self.doc_refs[path]


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> _FakeFirestore:
    """firestore_admin._db() 우회 + Increment / ArrayUnion mock 박제."""
    from sunity_shared import firestore_admin

    fake = _FakeFirestore()
    monkeypatch.setattr(firestore_admin, "_db", lambda: fake)

    # firebase_admin.firestore 의 Increment / ArrayUnion 을 mock 으로 swap.
    # record_unregistered_keyword 가 lazy import 후 호출.
    fake_firestore_module = type(
        "FakeFirestoreModule",
        (),
        {"Increment": _MockIncrement, "ArrayUnion": _MockArrayUnion},
    )
    # firebase_admin 모듈 자체를 mock 으로 sys.modules 박제
    monkeypatch.setitem(
        sys.modules,
        "firebase_admin",
        type("FakeFirebaseAdmin", (), {"firestore": fake_firestore_module})(),
    )

    return fake


# ─────────────────── get_gemini_cache ───────────────────


def test_get_gemini_cache_returns_none_on_miss(fake_db: _FakeFirestore) -> None:
    """gemini_cache/{hash} 미박제 → None 반환."""
    from sunity_shared.firestore_admin import get_gemini_cache

    assert get_gemini_cache("hash123") is None


def test_get_gemini_cache_returns_dict_on_hit(fake_db: _FakeFirestore) -> None:
    """gemini_cache/{hash} 박제 → dict 반환."""
    from sunity_shared.firestore_admin import get_gemini_cache

    fake_db.store["gemini_cache/hash123"] = {
        "motion": "ref-foxtop",
        "moments": [],
        "yaml_version": "abc",
        "model": "gemini-3.1-pro",
    }

    result = get_gemini_cache("hash123")
    assert result is not None
    assert result["motion"] == "ref-foxtop"
    assert result["yaml_version"] == "abc"


def test_get_gemini_cache_uses_correct_collection(fake_db: _FakeFirestore) -> None:
    """collection 경로 = gemini_cache (top-level, uid 비의존)."""
    from sunity_shared.firestore_admin import get_gemini_cache

    fake_db.store["gemini_cache/abc"] = {"motion": "x"}
    fake_db.store["users/user1/gemini_cache/abc"] = {"motion": "wrong"}

    result = get_gemini_cache("abc")
    assert result is not None
    assert result["motion"] == "x"  # top-level 박제


# ─────────────────── store_gemini_cache ───────────────────


def test_store_gemini_cache_sets_doc(fake_db: _FakeFirestore) -> None:
    """store 호출 → gemini_cache/{hash} document 박제."""
    from sunity_shared.firestore_admin import store_gemini_cache

    payload = {"motion": "ref-foxtop", "moments": [], "yaml_version": "v1"}
    store_gemini_cache("hashXYZ", payload)

    assert "gemini_cache/hashXYZ" in fake_db.store
    stored = fake_db.store["gemini_cache/hashXYZ"]
    assert stored["motion"] == "ref-foxtop"
    assert stored["video_hash"] == "hashXYZ"


def test_store_gemini_cache_adds_timestamps(fake_db: _FakeFirestore) -> None:
    """payload 에 created_at / updated_at 자동 박제."""
    from sunity_shared.firestore_admin import store_gemini_cache

    store_gemini_cache("hash1", {"motion": "ref-foxtop", "moments": []})

    stored = fake_db.store["gemini_cache/hash1"]
    assert "created_at" in stored
    assert "updated_at" in stored
    assert isinstance(stored["created_at"], int)
    assert isinstance(stored["updated_at"], int)
    # ms 단위 박제 — 현재 시각 근처 (충분히 큰 값)
    assert stored["created_at"] > 1_000_000_000_000  # > 2001-09 ms


def test_store_gemini_cache_preserves_existing_created_at(
    fake_db: _FakeFirestore,
) -> None:
    """payload 에 created_at 이미 있으면 보존 (재박제 시 첫 박제 시각 유지)."""
    from sunity_shared.firestore_admin import store_gemini_cache

    original_created_at = 1700000000000
    store_gemini_cache(
        "hash1",
        {
            "motion": "ref-foxtop",
            "moments": [],
            "created_at": original_created_at,
        },
    )

    stored = fake_db.store["gemini_cache/hash1"]
    assert stored["created_at"] == original_created_at


def test_store_gemini_cache_rejects_non_dict_moment_entry(
    fake_db: _FakeFirestore,
) -> None:
    """moments[i] 가 dict 아님 → TypeError ([[firestore-nested-array-flat]])."""
    from sunity_shared.firestore_admin import store_gemini_cache

    with pytest.raises(TypeError, match="flat dict"):
        store_gemini_cache(
            "hash1",
            {"motion": "ref-foxtop", "moments": [["hold", 5.5]]},
        )
    # 박제 되지 않아야 함
    assert "gemini_cache/hash1" not in fake_db.store


def test_store_gemini_cache_rejects_nested_array_in_moment_value(
    fake_db: _FakeFirestore,
) -> None:
    """moments[i] value 가 list/tuple → TypeError (Firestore crash 보호)."""
    from sunity_shared.firestore_admin import store_gemini_cache

    with pytest.raises(TypeError, match="scalar"):
        store_gemini_cache(
            "hash1",
            {
                "motion": "ref-foxtop",
                "moments": [
                    {"moment_key": "hold", "timestamps": [1.0, 2.0, 3.0]}
                ],
            },
        )
    assert "gemini_cache/hash1" not in fake_db.store


# ─────────────────── record_unregistered_keyword ───────────────────


def test_record_unregistered_keyword_uses_increment(fake_db: _FakeFirestore) -> None:
    """첫 호출 → Increment(1) + ArrayUnion([uid]) 박제."""
    from sunity_shared.firestore_admin import record_unregistered_keyword

    record_unregistered_keyword("kpose", uid="anon123", video_hash="abc")

    assert "term_collection/kpose" in fake_db.store
    stored = fake_db.store["term_collection/kpose"]
    assert stored["keyword"] == "kpose"
    assert stored["count"] == 1
    assert "anon123" in stored["unique_users"]
    assert stored["last_video_hash"] == "abc"


def test_record_unregistered_keyword_promotion_status_pending(
    fake_db: _FakeFirestore,
) -> None:
    """새 keyword → promotion_status = 'pending' (Phase 16 schema 정합)."""
    from sunity_shared.firestore_admin import record_unregistered_keyword

    record_unregistered_keyword("kpose", uid="anon1", video_hash="h1")

    stored = fake_db.store["term_collection/kpose"]
    assert stored["promotion_status"] == "pending"


def test_record_unregistered_keyword_idempotent_unique_users(
    fake_db: _FakeFirestore,
) -> None:
    """같은 (keyword, uid) 재호출 → unique_users set 멱등 (중복 없음)."""
    from sunity_shared.firestore_admin import record_unregistered_keyword

    record_unregistered_keyword("kpose", uid="anon1", video_hash="h1")
    record_unregistered_keyword("kpose", uid="anon1", video_hash="h2")

    stored = fake_db.store["term_collection/kpose"]
    # set 정합 — anon1 한 번만
    assert stored["unique_users"].count("anon1") == 1


def test_record_unregistered_keyword_accumulates_count(
    fake_db: _FakeFirestore,
) -> None:
    """여러 사용자 호출 → count 증가."""
    from sunity_shared.firestore_admin import record_unregistered_keyword

    record_unregistered_keyword("kpose", uid="anon1", video_hash="h1")
    record_unregistered_keyword("kpose", uid="anon2", video_hash="h2")
    record_unregistered_keyword("kpose", uid="anon3", video_hash="h3")

    stored = fake_db.store["term_collection/kpose"]
    assert stored["count"] == 3
    assert set(stored["unique_users"]) == {"anon1", "anon2", "anon3"}


# ─────────────────── lazy import (D-16) ───────────────────


def test_lazy_import_no_firebase_at_module_load() -> None:
    """firestore_admin 모듈 로드 시 firebase_admin 미import (D-16 박제).

    실제로는 기존 firestore_admin 이 함수 내부에서 import — Plan 5-02 helper
    추가 후에도 그 박제 패턴이 유지되어야 함.
    """
    # firestore_admin 강제 reload
    for mod in list(sys.modules):
        if (
            mod.startswith("firebase_admin")
            or mod == "sunity_shared.firestore_admin"
        ):
            del sys.modules[mod]
    import sunity_shared.firestore_admin  # noqa: F401

    assert "firebase_admin" not in sys.modules, (
        "D-16 위반 — firestore_admin 모듈 로드 시 firebase_admin import 됨"
    )


def test_gemini_cache_collection_constant_exposed() -> None:
    """_GEMINI_CACHE_COLLECTION / _TERM_COLLECTION 상수 박제 (grep 정합)."""
    from sunity_shared import firestore_admin

    assert firestore_admin._GEMINI_CACHE_COLLECTION == "gemini_cache"
    assert firestore_admin._TERM_COLLECTION == "term_collection"
