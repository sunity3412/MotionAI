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
    assert cache.lookup(video_file, motion_query="auto") is None
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
    cache.store(video_file, payload, motion_query="ref-foxtop")

    # 새 인스턴스 (in-memory 의존 X) — Firestore 만 의지
    cache2 = TechniqueCache(yaml_version="v1", model_name="gemini-3.1-pro")
    hit = cache2.lookup(video_file, motion_query="ref-foxtop")

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
    writer.store(video_file, {"motion": "ref-foxtop", "moments": []}, motion_query="ref-foxtop")

    reader = TechniqueCache(yaml_version="v2", model_name="gemini-3.1-pro")
    assert reader.lookup(video_file, motion_query="ref-foxtop") is None


def test_model_mismatch_invalidates(
    fake_firestore: _FakeFirestoreAdmin, video_file: Path
) -> None:
    """model_name mismatch → None (모델 교체 시 stale 박제 보호)."""
    from sunity_shared.analysis.technique_cache import TechniqueCache
    from sunity_shared.gemini.config import DEFAULT_C_MODEL

    writer = TechniqueCache(yaml_version="v1", model_name="gemini-3.1-pro")
    writer.store(video_file, {"motion": "ref-foxtop", "moments": []}, motion_query="ref-foxtop")

    reader = TechniqueCache(yaml_version="v1", model_name=DEFAULT_C_MODEL)
    assert reader.lookup(video_file, motion_query="ref-foxtop") is None


def test_in_memory_hit_skips_firestore(
    fake_firestore: _FakeFirestoreAdmin, video_file: Path
) -> None:
    """in-memory store 후 같은 인스턴스 lookup → Firestore 미호출 (Pod 안 중복 흡수)."""
    from sunity_shared.analysis.technique_cache import TechniqueCache

    cache = TechniqueCache(yaml_version="v1")
    cache.store(video_file, {"motion": "ref-foxtop", "moments": []}, motion_query="ref-foxtop")
    fake_firestore.get_calls.clear()  # store 시 호출 0 → 안전, 추적 reset

    hit = cache.lookup(video_file, motion_query="ref-foxtop")
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
    # 2026-09-20: Firestore doc id = {hash}__{질의}. 같은 영상의 mode1/mode3 산출이
    # 서로 덮어쓰지 않고 공존해야 둘 다 캐시가 먹는다.
    fake_firestore.store[f"{video_hash}__ref-foxtop"] = {
        "motion": "ref-foxtop",
        "moments": [],
        "yaml_version": "v1",
        "model": "gemini-3.1-pro",
        "motion_query": "ref-foxtop",
        "video_hash": video_hash,
    }

    cache = TechniqueCache(yaml_version="v1", model_name="gemini-3.1-pro")
    hit1 = cache.lookup(video_file, motion_query="ref-foxtop")
    assert hit1 is not None
    assert len(fake_firestore.get_calls) == 1

    # 두 번째 lookup — in-memory hit 박제
    hit2 = cache.lookup(video_file, motion_query="ref-foxtop")
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
    cache.store(video_file, {"motion": "ref-foxtop", "moments": []}, motion_query="ref-foxtop")

    assert len(fake_firestore.set_calls) == 1
    stored_id, stored_doc = fake_firestore.set_calls[0]
    expected_hash = compute_video_hash(video_file)
    # 2026-09-20: document **id** 는 해시+질의다(질의별 doc 공존).
    assert stored_id == f"{expected_hash}__ref-foxtop"
    # 그러나 doc 안의 video_hash **필드**는 순수 해시 그대로여야 한다 —
    # 이 필드로 영상을 되찾는 소비처가 있다(id 와 필드를 섞으면 안 된다).
    assert stored_doc["video_hash"] == expected_hash
    assert stored_doc["yaml_version"] == "abc"
    assert stored_doc["model"] == "gemini-3.1-pro"
    assert stored_doc["motion_query"] == "ref-foxtop"
    assert stored_doc["motion"] == "ref-foxtop"


# ─────────────────────────────────────────────────────────────────────────────
# 2026-09-20 — 캐시 키에 동작 질의가 없어서 생긴 결함의 회귀
#
# Gemini 산출은 (video, motion_query) 의 함수다 — 질의가 프롬프트에 들어가고 거기서
# profile 이 나온다. 그런데 키는 영상만 잡고 있었다. 그래서 같은 영상을 mode1 으로 먼저
# 분석하면 그 판정이 박히고, 이후 같은 영상의 mode3 분석이 그걸 물려받았다
# (실행 확인: 같은 mode3 분석이 종합 100 점도 0 점도 됐다).
# Firestore layer 는 gemini_cache/{hash} top-level 전역 공유라 Pod 재기동을 넘어 살고
# 사용자를 넘었다. 라이브 지문도 있었다 — mode3 는 자력으로 동작을 인식할 수 없는데
# recognizedMotionId 를 가진 mode3 doc 이 표본 40건 중 1건 실재했다.
# ─────────────────────────────────────────────────────────────────────────────


def test_different_motion_query_is_a_cache_miss(
    fake_firestore: _FakeFirestoreAdmin, video_file: Path
) -> None:
    """같은 영상이라도 **질의가 다르면 히트가 아니다** — 이 결함의 핵심 회귀.

    mode1(ref-power-spin)이 박은 답을 mode3(auto)가 물려받으면 안 된다.
    """
    from sunity_shared.analysis.technique_cache import TechniqueCache

    cache = TechniqueCache(yaml_version="v1", model_name="m")
    cache.store(
        video_file,
        {"motion": "ref-power-spin", "moments": [],
         "joint_expectations": {"left_knee": "extend"}},
        motion_query="ref-power-spin",
    )

    # 같은 영상, 같은 인스턴스, 다른 질의 → miss 여야 한다.
    assert cache.lookup(video_file, motion_query="auto") is None, (
        "mode3(auto) 분석이 mode1(ref-power-spin) 의 판정을 물려받았다 — "
        "같은 영상의 같은 분석이 이력에 따라 다른 점수를 낸다."
    )
    # 자기 질의로는 여전히 히트.
    own = cache.lookup(video_file, motion_query="ref-power-spin")
    assert own is not None and own["motion"] == "ref-power-spin"


def test_two_queries_coexist_instead_of_overwriting(
    fake_firestore: _FakeFirestoreAdmin, video_file: Path
) -> None:
    """같은 영상의 두 질의 산출이 **서로 덮어쓰지 않고 공존**한다.

    한 칸에 겹쳐 쓰면 두 모드가 번갈아 분석될 때마다 서로를 무효화해 매번
    Gemini 를 다시 부른다. document id 에 질의를 넣어 공존시킨다.
    """
    from sunity_shared.analysis.technique_cache import TechniqueCache

    cache = TechniqueCache(yaml_version="v1", model_name="m")
    cache.store(video_file, {"motion": "ref-power-spin", "moments": []},
                motion_query="ref-power-spin")
    cache.store(video_file, {"motion": "auto", "moments": []},
                motion_query="auto")

    assert len(fake_firestore.set_calls) == 2
    ids = {call[0] for call in fake_firestore.set_calls}
    assert len(ids) == 2, f"두 질의가 같은 doc 에 겹쳐 쓰였다: {ids}"

    fresh = TechniqueCache(yaml_version="v1", model_name="m")
    a = fresh.lookup(video_file, motion_query="ref-power-spin")
    b = fresh.lookup(video_file, motion_query="auto")
    assert a is not None and a["motion"] == "ref-power-spin"
    assert b is not None and b["motion"] == "auto"


def test_legacy_doc_without_motion_query_is_invalidated(
    fake_firestore: _FakeFirestoreAdmin, video_file: Path
) -> None:
    """2026-09-20 이전 doc 은 재사용하지 않는다 — 어떤 질의로 만든 건지 알 수 없다.

    옛 doc 은 id 가 해시 단독이라 새 id 로는 조회되지 않고, 설령 조회돼도
    motion_query 필드가 없어 mismatch 로 무효화된다(이중 방어).
    """
    from sunity_shared.analysis.technique_cache import (
        TechniqueCache,
        compute_video_hash,
    )

    video_hash = compute_video_hash(video_file)
    legacy = {
        "motion": "ref-power-spin", "moments": [],
        "yaml_version": "v1", "model": "m", "video_hash": video_hash,
    }
    # 옛 레이아웃(해시 단독 id) + 새 레이아웃(해시+질의) 양쪽에 심어 이중 방어를 태운다.
    fake_firestore.store[video_hash] = dict(legacy)
    fake_firestore.store[f"{video_hash}__auto"] = dict(legacy)

    cache = TechniqueCache(yaml_version="v1", model_name="m")
    assert cache.lookup(video_file, motion_query="auto") is None, (
        "motion_query 필드가 없는 옛 doc 을 재사용했다 — 어떤 질의로 만든 "
        "판정인지 알 수 없으므로 무효화해야 한다."
    )


def test_memory_key_and_doc_id_both_carry_the_query(
    video_file: Path,
) -> None:
    """키 구성 자체를 박제 — 질의가 빠지면 이 테스트가 깨진다."""
    from sunity_shared.analysis.technique_cache import TechniqueCache

    cache = TechniqueCache(yaml_version="v1", model_name="m")
    assert cache._mem_key("H", "auto") != cache._mem_key("H", "ref-power-spin")
    assert cache._doc_id("H", "auto") != cache._doc_id("H", "ref-power-spin")
    # document id 안전화 — '/' 는 Firestore path 구분자다.
    assert "/" not in cache._doc_id("H", "a/b")


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
        cache.store(video_file, bad_payload, motion_query="ref-foxtop")
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
        cache.store(video_file, bad_payload, motion_query="ref-foxtop")


def test_lookup_skips_when_video_missing(
    fake_firestore: _FakeFirestoreAdmin, tmp_path: Path
) -> None:
    """video 파일 없음 → lookup graceful None (분석 흐름 박제 보호)."""
    from sunity_shared.analysis.technique_cache import TechniqueCache

    cache = TechniqueCache(yaml_version="v1")
    result = cache.lookup(tmp_path / "no_such_video.mp4", motion_query="auto")
    assert result is None
    assert len(fake_firestore.get_calls) == 0  # Firestore 미호출


def test_store_skips_when_video_missing(
    fake_firestore: _FakeFirestoreAdmin, tmp_path: Path
) -> None:
    """video 파일 없음 → store skip (silent, log.warning)."""
    from sunity_shared.analysis.technique_cache import TechniqueCache

    cache = TechniqueCache(yaml_version="v1")
    cache.store(
        tmp_path / "no_such.mp4", {"motion": "ref-foxtop", "moments": []},
        motion_query="ref-foxtop",
    )
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
