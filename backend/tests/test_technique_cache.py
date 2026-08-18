"""TechniqueCache 단위 테스트 (Plan 5-02 Task 1).

박제 정신 (Plan 5-02 PLAN must_haves):
  · D-14 영상 hash 캡싱 (SHA256, stdlib hashlib) — 같은 영상 = 같은 hash
  · D-16 lazy import — 모듈 로드 시점 firebase_admin / boto3 0 import
  · Open Question 4 yaml_version 박제 — yaml 갱신 시 cache stale auto-invalidate
  · [[firestore-nested-array-flat]] — KeyMoment list 안 nested list/tuple 거부
  · B4 fix (2026-06-04): compute_yaml_version 절대 경로 + strict=True default + 64hex full

모든 테스트는 stdlib + pytest 만 사용 (firebase_admin / boto3 / google.generativeai 미import).
firestore_admin helper 는 monkeypatch 로 mock — 실제 Firestore 호출 0.
"""

from __future__ import annotations

import hashlib
import inspect
import sys
from pathlib import Path
from typing import Any

import pytest


# ─────────────────── compute_video_hash ───────────────────


def test_compute_video_hash_deterministic(tmp_path: Path) -> None:
    """같은 파일 → 같은 SHA256 hex (D-14 박제 결정성)."""
    from sunity_shared.analysis.technique_cache import compute_video_hash

    video = tmp_path / "demo.mp4"
    video.write_bytes(b"hello pole world" * 32)

    h1 = compute_video_hash(video)
    h2 = compute_video_hash(video)

    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex = 64자
    assert all(c in "0123456789abcdef" for c in h1)


def test_compute_video_hash_different_files(tmp_path: Path) -> None:
    """1 byte 차이 = 다른 hash (collision 0 박제)."""
    from sunity_shared.analysis.technique_cache import compute_video_hash

    a = tmp_path / "a.mp4"
    b = tmp_path / "b.mp4"
    a.write_bytes(b"hello pole world" * 32)
    b.write_bytes(b"hello pole world" * 32 + b"X")

    assert compute_video_hash(a) != compute_video_hash(b)


def test_compute_video_hash_missing_raises(tmp_path: Path) -> None:
    """파일 없음 → FileNotFoundError (무성 hash 박제 금지)."""
    from sunity_shared.analysis.technique_cache import compute_video_hash

    with pytest.raises(FileNotFoundError):
        compute_video_hash(tmp_path / "does_not_exist.mp4")


def test_compute_video_hash_streams_in_chunks(tmp_path: Path) -> None:
    """chunk_size 인자 박제 — 대용량 영상 메모리 보호 path."""
    from sunity_shared.analysis.technique_cache import compute_video_hash

    video = tmp_path / "chunked.mp4"
    payload = b"X" * 200_000  # 200KB
    video.write_bytes(payload)

    # 기대값 = stdlib hashlib 으로 직접 계산한 값과 동일
    expected = hashlib.sha256(payload).hexdigest()
    assert compute_video_hash(video, chunk_size=4096) == expected
    assert compute_video_hash(video, chunk_size=131072) == expected


# ─────────────────── compute_yaml_version (B4 fix) ───────────────────


def test_compute_yaml_version_returns_full_hex() -> None:
    """B4 fix — 64자 hex string 반환 (truncation 제거)."""
    from sunity_shared.analysis.technique_cache import compute_yaml_version

    result = compute_yaml_version()
    assert isinstance(result, str)
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_compute_yaml_version_uses_absolute_path() -> None:
    """B4 fix — _YAML_CRITERIA_DIR 절대 경로 박제 (CWD 의존 0)."""
    from sunity_shared.analysis import technique_cache

    assert technique_cache._YAML_CRITERIA_DIR.is_absolute()
    # parents[4]/judging_data/criteria — 실제 yaml 박제 path
    assert technique_cache._YAML_CRITERIA_DIR.name == "criteria"
    assert technique_cache._YAML_CRITERIA_DIR.parent.name == "judging_data"


def test_compute_yaml_version_strict_default() -> None:
    """B4 fix — strict=True 가 default 박제 (signature inspection)."""
    from sunity_shared.analysis.technique_cache import compute_yaml_version

    sig = inspect.signature(compute_yaml_version)
    strict = sig.parameters["strict"]
    assert strict.default is True
    assert strict.kind == inspect.Parameter.KEYWORD_ONLY


def test_compute_yaml_version_strict_raises_when_yaml_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """B4 fix — yaml 누락 + strict=True → FileNotFoundError raise (무성 누락 0)."""
    from sunity_shared.analysis import technique_cache

    monkeypatch.setattr(technique_cache, "_YAML_CRITERIA_DIR", tmp_path / "missing-dir")

    with pytest.raises(FileNotFoundError) as exc_info:
        technique_cache.compute_yaml_version(strict=True)

    assert "B4 fix" in str(exc_info.value) or "cache invalidation" in str(exc_info.value)


def test_compute_yaml_version_nonstrict_returns_sentinel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """B4 fix — yaml 누락 + strict=False → sentinel string + log.warning."""
    import logging

    from sunity_shared.analysis import technique_cache

    monkeypatch.setattr(technique_cache, "_YAML_CRITERIA_DIR", tmp_path / "missing-dir")

    with caplog.at_level(logging.WARNING):
        result = technique_cache.compute_yaml_version(strict=False)

    assert result == "yaml-missing-cache-disabled"
    assert any("yaml" in rec.message for rec in caplog.records)


def test_compute_yaml_version_changes_when_yaml_content_changes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """yaml 갱신 시 자동 stale invalidate path 박제 (Open Question 4)."""
    from sunity_shared.analysis import technique_cache

    # 모든 yaml 파일을 tmp_path 로 박제
    fake_dir = tmp_path / "criteria"
    fake_dir.mkdir()
    for name in technique_cache._YAML_FILENAMES:
        (fake_dir / name).write_bytes(b"motion: foo\n")
    monkeypatch.setattr(technique_cache, "_YAML_CRITERIA_DIR", fake_dir)

    v1 = technique_cache.compute_yaml_version()
    # yaml 1개 변경
    (fake_dir / technique_cache._YAML_FILENAMES[0]).write_bytes(b"motion: bar\n")
    v2 = technique_cache.compute_yaml_version()

    assert v1 != v2


# ─────────────────── TechniqueCache 클래스 ───────────────────


class _FakeFirestoreAdmin:
    """firestore_admin mock — get_gemini_cache / store_gemini_cache 추적."""

    def __init__(self) -> None:
        self.store: dict[str, dict] = {}
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, dict]] = []

    def get_gemini_cache(self, video_hash: str) -> dict | None:
        self.get_calls.append(video_hash)
        if video_hash not in self.store:
            return None
        return dict(self.store[video_hash])

    def store_gemini_cache(self, video_hash: str, payload: dict) -> None:
        self.set_calls.append((video_hash, dict(payload)))
        self.store[video_hash] = dict(payload)


@pytest.fixture
def fake_firestore(monkeypatch: pytest.MonkeyPatch) -> _FakeFirestoreAdmin:
    """sunity_shared.firestore_admin 모듈을 fake 로 swap."""
    fake = _FakeFirestoreAdmin()
    from sunity_shared import firestore_admin

    monkeypatch.setattr(firestore_admin, "get_gemini_cache", fake.get_gemini_cache, raising=False)
    monkeypatch.setattr(firestore_admin, "store_gemini_cache", fake.store_gemini_cache, raising=False)
    return fake


@pytest.fixture
def video_file(tmp_path: Path) -> Path:
    """단위 테스트용 임시 영상 파일 (hash 계산용)."""
    video = tmp_path / "sample.mp4"
    video.write_bytes(b"sample-video-bytes" * 64)
    return video


def test_lookup_miss_returns_none(
    fake_firestore: _FakeFirestoreAdmin, video_file: Path
) -> None:
    """cache 빈 상태 lookup → None (Firestore mock 미저장)."""
    from sunity_shared.analysis.technique_cache import TechniqueCache

    cache = TechniqueCache(yaml_version="v1")
    assert cache.lookup(video_file) is None
    assert len(fake_firestore.get_calls) == 1  # Firestore 1회 조회


def test_lookup_then_store(
    fake_firestore: _FakeFirestoreAdmin, video_file: Path
) -> None:
    """store → lookup → 박제된 dict 반환 (cache hit path)."""
    from sunity_shared.analysis.technique_cache import TechniqueCache

    cache = TechniqueCache(yaml_version="v1", model_name="gemini-3.1-pro")
    payload = {
        "motion": "ref-foxtop",
        "moments": [
            {"moment_key": "hold", "timestamp_seconds": 5.5, "frame_index": 49, "confidence": 0.88}
        ],
        "joint_expectations": {"left_shoulder": "extend"},
    }
    cache.store(video_file, payload)

    # 새 인스턴스 (in-memory 의존 X) — Firestore 만 의지
    cache2 = TechniqueCache(yaml_version="v1", model_name="gemini-3.1-pro")
    hit = cache2.lookup(video_file)

    assert hit is not None
    assert hit["motion"] == "ref-foxtop"
    assert hit["yaml_version"] == "v1"
    assert hit["model"] == "gemini-3.1-pro"


def test_yaml_version_mismatch_invalidates(
    fake_firestore: _FakeFirestoreAdmin, video_file: Path
) -> None:
    """yaml_version mismatch → None (Open Question 4 박제 정합)."""
    from sunity_shared.analysis.technique_cache import TechniqueCache

    writer = TechniqueCache(yaml_version="v1", model_name="gemini-3.1-pro")
    writer.store(video_file, {"motion": "ref-foxtop", "moments": []})

    reader = TechniqueCache(yaml_version="v2", model_name="gemini-3.1-pro")
    assert reader.lookup(video_file) is None


def test_model_mismatch_invalidates(
    fake_firestore: _FakeFirestoreAdmin, video_file: Path
) -> None:
    """model_name mismatch → None (모델 교체 시 stale 박제 보호)."""
    from sunity_shared.analysis.technique_cache import TechniqueCache

    writer = TechniqueCache(yaml_version="v1", model_name="gemini-3.1-pro")
    writer.store(video_file, {"motion": "ref-foxtop", "moments": []})

    reader = TechniqueCache(yaml_version="v1", model_name="gemini-3.7-flash")
    assert reader.lookup(video_file) is None


def test_in_memory_hit_skips_firestore(
    fake_firestore: _FakeFirestoreAdmin, video_file: Path
) -> None:
    """in-memory store 후 같은 인스턴스 lookup → Firestore 미호출 (Pod 안 중복 흡수)."""
    from sunity_shared.analysis.technique_cache import TechniqueCache

    cache = TechniqueCache(yaml_version="v1")
    cache.store(video_file, {"motion": "ref-foxtop", "moments": []})
    fake_firestore.get_calls.clear()  # store 시 호출 0 → 안전, 추적 reset

    hit = cache.lookup(video_file)
    assert hit is not None
    assert len(fake_firestore.get_calls) == 0  # Firestore 미호출 박제


def test_in_memory_miss_firestore_hit_updates_memory(
    fake_firestore: _FakeFirestoreAdmin, video_file: Path
) -> None:
    """Firestore hit → in-memory 갱신 → 두 번째 lookup Firestore 미호출."""
    from sunity_shared.analysis.technique_cache import (
        TechniqueCache,
        compute_video_hash,
    )

    # Firestore 만 미리 박제
    video_hash = compute_video_hash(video_file)
    fake_firestore.store[video_hash] = {
        "motion": "ref-foxtop",
        "moments": [],
        "yaml_version": "v1",
        "model": "gemini-3.1-pro",
        "video_hash": video_hash,
    }

    cache = TechniqueCache(yaml_version="v1", model_name="gemini-3.1-pro")
    hit1 = cache.lookup(video_file)
    assert hit1 is not None
    assert len(fake_firestore.get_calls) == 1

    # 두 번째 lookup — in-memory hit 박제
    hit2 = cache.lookup(video_file)
    assert hit2 is not None
    assert len(fake_firestore.get_calls) == 1  # 추가 호출 0


def test_store_includes_yaml_version_and_model(
    fake_firestore: _FakeFirestoreAdmin, video_file: Path
) -> None:
    """store 호출 시 yaml_version / model / video_hash 자동 박제."""
    from sunity_shared.analysis.technique_cache import (
        TechniqueCache,
        compute_video_hash,
    )

    cache = TechniqueCache(yaml_version="abc", model_name="gemini-3.1-pro")
    cache.store(video_file, {"motion": "ref-foxtop", "moments": []})

    assert len(fake_firestore.set_calls) == 1
    stored_hash, stored_doc = fake_firestore.set_calls[0]
    expected_hash = compute_video_hash(video_file)
    assert stored_hash == expected_hash
    assert stored_doc["yaml_version"] == "abc"
    assert stored_doc["model"] == "gemini-3.1-pro"
    assert stored_doc["video_hash"] == expected_hash
    assert stored_doc["motion"] == "ref-foxtop"


def test_store_rejects_nested_array_in_moments_value(
    fake_firestore: _FakeFirestoreAdmin, video_file: Path
) -> None:
    """moments[i] 안 list value → TypeError ([[firestore-nested-array-flat]] 박제)."""
    from sunity_shared.analysis.technique_cache import TechniqueCache

    cache = TechniqueCache(yaml_version="v1")
    bad_payload = {
        "motion": "ref-foxtop",
        "moments": [
            {
                "moment_key": "hold",
                "timestamps": [1.0, 2.0, 3.0],  # nested list → 거부
            }
        ],
    }
    with pytest.raises(TypeError, match="firestore"):
        cache.store(video_file, bad_payload)
    # store 도 호출되지 않아야 함
    assert len(fake_firestore.set_calls) == 0


def test_store_rejects_non_dict_moment_entry(
    fake_firestore: _FakeFirestoreAdmin, video_file: Path
) -> None:
    """moments[i] 가 dict 아님 → TypeError (flat dict 박제 강제)."""
    from sunity_shared.analysis.technique_cache import TechniqueCache

    cache = TechniqueCache(yaml_version="v1")
    bad_payload = {
        "motion": "ref-foxtop",
        "moments": [["hold", 5.5]],  # entry 가 list → 거부
    }
    with pytest.raises(TypeError, match="flat dict"):
        cache.store(video_file, bad_payload)


def test_lookup_skips_when_video_missing(
    fake_firestore: _FakeFirestoreAdmin, tmp_path: Path
) -> None:
    """video 파일 없음 → lookup graceful None (분석 흐름 박제 보호)."""
    from sunity_shared.analysis.technique_cache import TechniqueCache

    cache = TechniqueCache(yaml_version="v1")
    result = cache.lookup(tmp_path / "no_such_video.mp4")
    assert result is None
    assert len(fake_firestore.get_calls) == 0  # Firestore 미호출


def test_store_skips_when_video_missing(
    fake_firestore: _FakeFirestoreAdmin, tmp_path: Path
) -> None:
    """video 파일 없음 → store skip (silent, log.warning)."""
    from sunity_shared.analysis.technique_cache import TechniqueCache

    cache = TechniqueCache(yaml_version="v1")
    cache.store(tmp_path / "no_such.mp4", {"motion": "ref-foxtop", "moments": []})
    assert len(fake_firestore.set_calls) == 0


# ─────────────────── lazy import (D-16) ───────────────────


def test_lazy_import_no_firebase_admin() -> None:
    """모듈 로드 시 firebase_admin 미import (D-16 박제)."""
    # 모듈 강제 reload — sys.modules 보장
    for mod in list(sys.modules):
        if mod.startswith("firebase_admin") or mod.startswith("google.generativeai"):
            del sys.modules[mod]
    # technique_cache import — 이후 firebase_admin 이 sys.modules 에 없어야 함
    if "sunity_shared.analysis.technique_cache" in sys.modules:
        del sys.modules["sunity_shared.analysis.technique_cache"]
    import sunity_shared.analysis.technique_cache  # noqa: F401

    assert "firebase_admin" not in sys.modules, (
        "D-16 위반 — technique_cache 모듈 로드 시 firebase_admin import 됨"
    )
    assert "google.generativeai" not in sys.modules, (
        "D-16 위반 — technique_cache 모듈 로드 시 google.generativeai import 됨"
    )
