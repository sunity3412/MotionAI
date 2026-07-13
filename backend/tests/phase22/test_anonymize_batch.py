"""내부 fault 트랙 anonymize 배치 러너 테스트 — manifest 행 생성/병합/재개 (quick 260713-jxr Task 2).

불변식 (처방 B, belle 2026-07-13 결정):
  · 업로드 키는 fixtures/phase22/internal/{video_hash}.mp4 뿐 — uploads/ 생성 경로
    구조적 부재(S3 ObjectCreated→SQS 발화 차단, T-Q13-03).
  · 생성 manifest 행은 gemini_teacher.eligible_for_distill 을 실제 통과
    (source 에 'user' 포함 + anonymized=true + s3_key + holdout 없음).
  · 생성 행은 test_provenance fence 를 실제 통과 — REQUIRED_PROVENANCE_FIELDS 전부
    truthy(source_url sentinel 포함) + label_bucket ∈ VALID_BUCKETS + 금지 식별자 부재.
    상수는 test_provenance 에서 import(단일 owner — 하드코딩 복제 금지).
  · provisional_bucket=None 후보는 병합 전 skip(다운로드/anonymize 미수행).
  · 재개 가능 — 터미널 행 결과 파일 존재 시 anonymize 호출 0 (full_batch TERMINAL 패턴).
  · merge_manifest_rows 는 사본 반환 + 멱등 + 기존 131행 불변.

GPU/네트워크 0 — anonymize/boto3 는 monkeypatch, anonymize_video 자체는 재테스트 안 함
(기존 소유 테스트 존재 — 수치 채우기 금지).
"""

from __future__ import annotations

import json

import pytest

from datagen import anonymize_batch as ab
from distill import gemini_teacher as gt

# provenance fence 상수 — 단일 owner(test_provenance) 에서 import (복제 금지).
from test_provenance import (
    FORBIDDEN_IDENTITY_FIELDS,
    REQUIRED_PROVENANCE_FIELDS,
    VALID_BUCKETS,
)


def _candidate(**over) -> dict:
    """enumerate_internal.build_candidate 산출 형태의 후보 dict."""
    base = {
        "s3_key": "uploads/uidABC/analysis123.mp4",
        "etag": "abc123",
        "created_at_ms": 1_700_000_000_000,
        "motion": "ref-kip-up",
        "provisional_bucket": "fault",
        "opt_in": None,
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# internal_upload_key / internal_source_url — prefix 강제 + sentinel.
# ---------------------------------------------------------------------------
def test_internal_upload_key_prefix_forced():
    key = ab.internal_upload_key("deadbeef")
    assert key == "fixtures/phase22/internal/deadbeef.mp4"
    assert key.startswith("fixtures/phase22/internal/")
    assert not key.startswith("uploads/")


def test_internal_upload_key_empty_hash_rejected():
    with pytest.raises(ValueError):
        ab.internal_upload_key("")


def test_internal_source_url_is_hash_based_sentinel():
    url = ab.internal_source_url("deadbeef")
    assert url == "internal://firestore-analyses/deadbeef"
    # uid/analysisId 파생값이 sentinel 에 새어들지 않는다 (T-Q13-01).
    assert "uid" not in url.lower()
    assert "analysis" not in url.replace("firestore-analyses", "").lower()


# ---------------------------------------------------------------------------
# build_manifest_row — 스키마 + 방어 assert.
# ---------------------------------------------------------------------------
def test_build_manifest_row_schema():
    row = ab.build_manifest_row(_candidate(), "hash01")
    assert row["s3_key"] == "fixtures/phase22/internal/hash01.mp4"
    assert row["anonymized"] is True
    assert "user" in row["source"].lower()  # _is_customer_source 발화.
    assert row["label_bucket"] in VALID_BUCKETS
    assert row["holdout"] is None
    assert row["collected"] is True
    assert row.get("consent_evidence")  # belle 일괄승인 근거 truthy.


def test_build_manifest_row_has_no_identity_fields():
    row = ab.build_manifest_row(_candidate(), "hash01")
    for forbidden in FORBIDDEN_IDENTITY_FIELDS:
        assert forbidden not in row
    # 원본 uploads/ 키(uid 포함)가 행에 새어들지 않는다.
    assert "uid" not in json.dumps(row, ensure_ascii=False).lower()


def test_build_manifest_row_passes_eligible_for_distill():
    row = ab.build_manifest_row(_candidate(), "hash01")
    assert gt.eligible_for_distill(row) is True


def test_build_manifest_row_passes_provenance_fence():
    row = ab.build_manifest_row(_candidate(provisional_bucket="정타"), "hash01")
    assert all(row.get(f) for f in REQUIRED_PROVENANCE_FIELDS)
    assert row["label_bucket"] in VALID_BUCKETS


def test_build_manifest_row_rejects_none_bucket():
    with pytest.raises(ValueError):
        ab.build_manifest_row(_candidate(provisional_bucket=None), "hash01")


def test_build_manifest_row_rejects_out_of_enum_bucket():
    with pytest.raises(ValueError):
        ab.build_manifest_row(_candidate(provisional_bucket="87"), "hash01")


# ---------------------------------------------------------------------------
# merge_manifest_rows — 사본 + 멱등 + 기존 행 불변.
# ---------------------------------------------------------------------------
def _manifest() -> dict:
    return {
        "_meta": {"customer_track": {"count": 371, "anonymized": False}},
        "rows": [
            {"s3_key": "fixtures/phase22/A/x.mp4", "label_bucket": "정타"},
        ],
    }


def test_merge_manifest_rows_idempotent_and_copy():
    m = _manifest()
    new = [ab.build_manifest_row(_candidate(), "h1")]
    merged1 = ab.merge_manifest_rows(m, new)
    merged2 = ab.merge_manifest_rows(merged1, new)
    # 원본 불변 (사본 반환).
    assert len(m["rows"]) == 1
    # 1회 병합 = 2회 병합 (s3_key 기준 멱등).
    assert len(merged1["rows"]) == 2
    assert len(merged2["rows"]) == 2


def test_merge_manifest_rows_preserves_existing_rows():
    m = _manifest()
    original_first = dict(m["rows"][0])
    merged = ab.merge_manifest_rows(m, [ab.build_manifest_row(_candidate(), "h1")])
    assert merged["rows"][0] == original_first


def test_merge_manifest_rows_updates_customer_track():
    m = _manifest()
    merged = ab.merge_manifest_rows(m, [ab.build_manifest_row(_candidate(), "h1")])
    ct = merged["_meta"]["customer_track"]
    assert ct.get("anonymized") == "in_progress"
    assert "2026-07-13" in json.dumps(ct, ensure_ascii=False)


# ---------------------------------------------------------------------------
# is_row_done — 터미널 판정 (재개).
# ---------------------------------------------------------------------------
def test_is_row_done_terminal_states():
    assert ab.is_row_done({"result": "uploaded"}) is True
    assert ab.is_row_done({"result": "skipped_no_bucket"}) is True
    assert ab.is_row_done({"result": "error"}) is False
    assert ab.is_row_done({}) is False


# ---------------------------------------------------------------------------
# assert_no_identifier_keys — 행 화이트리스트 fence.
# ---------------------------------------------------------------------------
def test_assert_no_identifier_keys_rejects_uid():
    with pytest.raises(AssertionError):
        ab.assert_no_identifier_keys([{"uid": "x", "s3_key": "y"}])


def test_assert_no_identifier_keys_passes_clean_row():
    row = ab.build_manifest_row(_candidate(), "h1")
    ab.assert_no_identifier_keys([row])  # 예외 없음.


# ---------------------------------------------------------------------------
# run_anonymize_batch — 재개 skip / bucket None skip / hash 중복 skip.
# 네트워크/GPU 0 — 다운로드·anonymize·업로드를 monkeypatch 로 계수만 관찰.
# ---------------------------------------------------------------------------
class _Spy:
    """다운로드/anonymize/업로드 호출 계수 스파이 (I/O 대체)."""

    def __init__(self, hash_map=None):
        self.download_calls = 0
        self.anonymize_calls = 0
        self.upload_calls = 0
        self.hash_map = hash_map or {}  # s3_key → video_hash

    def download(self, bucket, key, dest):
        self.download_calls += 1

    def anonymize(self, in_path, out_path, weights=None):
        self.anonymize_calls += 1
        return out_path

    def compute_hash(self, path):
        # dest 경로에서 원본 s3_key 를 복원할 수 없으므로 호출 순서로 매핑.
        return self._next_hash

    def upload(self, path, bucket, key, ExtraArgs=None):
        self.upload_calls += 1


def _patch_io(monkeypatch, spy, hashes):
    """run_anonymize_batch 의 I/O 경계를 spy 로 교체. hashes = 순차 반환할 해시 리스트."""
    seq = list(hashes)

    def _dl(bucket, key, dest):
        spy.download(bucket, key, dest)

    def _anon(in_path, out_path, weights=None):
        return spy.anonymize(in_path, out_path, weights)

    def _hash(path, **kw):
        spy.anonymize_calls  # noop ref
        return seq.pop(0) if seq else "hZ"

    class _FakeS3:
        def upload_file(self, path, bucket, key, ExtraArgs=None):
            spy.upload(path, bucket, key, ExtraArgs=ExtraArgs)

    monkeypatch.setattr(ab, "_download_s3", _dl, raising=False)
    monkeypatch.setattr(ab, "_anonymize_video", _anon, raising=False)
    monkeypatch.setattr(ab, "_compute_video_hash", _hash, raising=False)
    monkeypatch.setattr(ab, "_s3_client", lambda: _FakeS3(), raising=False)


def test_run_batch_skips_bucket_none_before_download(tmp_path, monkeypatch):
    spy = _Spy()
    _patch_io(monkeypatch, spy, hashes=["h1"])
    cand = {"candidates": [_candidate(provisional_bucket=None)]}
    cpath = tmp_path / "cand.json"
    cpath.write_text(json.dumps(cand), encoding="utf-8")
    out_dir = tmp_path / "out"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_manifest()), encoding="utf-8")

    summary = ab.run_anonymize_batch(
        str(cpath), str(out_dir), str(tmp_path / "scratch"),
        bucket="b", manifest_path=str(manifest), dry_run=False,
    )
    # bucket None → 다운로드/anonymize 0, skipped 기록, manifest 병합 미포함.
    assert spy.download_calls == 0
    assert spy.anonymize_calls == 0
    assert summary["skipped_no_bucket"] == 1
    m = json.loads(manifest.read_text(encoding="utf-8"))
    assert len(m["rows"]) == 1  # 신규 행 없음.


def test_run_batch_resume_skips_terminal_rows(tmp_path, monkeypatch):
    spy = _Spy()
    _patch_io(monkeypatch, spy, hashes=["h1"])
    cand = {"candidates": [_candidate()]}
    cpath = tmp_path / "cand.json"
    cpath.write_text(json.dumps(cand), encoding="utf-8")
    out_dir = tmp_path / "out"
    (out_dir / "rows").mkdir(parents=True)
    # 이미 터미널(uploaded) 행 결과 파일 존재 → 재개 시 skip.
    slug = "uploads__uidABC__analysis123.mp4"
    (out_dir / "rows" / f"{slug}.json").write_text(
        json.dumps({"result": "uploaded", "video_hash": "h1"}), encoding="utf-8"
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_manifest()), encoding="utf-8")

    ab.run_anonymize_batch(
        str(cpath), str(out_dir), str(tmp_path / "scratch"),
        bucket="b", manifest_path=str(manifest), dry_run=False,
    )
    assert spy.anonymize_calls == 0  # 재개 skip — 재anonymize 0.


def test_run_batch_processes_fresh_candidate(tmp_path, monkeypatch):
    spy = _Spy()
    _patch_io(monkeypatch, spy, hashes=["h1"])
    cand = {"candidates": [_candidate()]}
    cpath = tmp_path / "cand.json"
    cpath.write_text(json.dumps(cand), encoding="utf-8")
    out_dir = tmp_path / "out"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_manifest()), encoding="utf-8")

    summary = ab.run_anonymize_batch(
        str(cpath), str(out_dir), str(tmp_path / "scratch"),
        bucket="b", manifest_path=str(manifest), dry_run=False,
    )
    assert spy.download_calls == 1
    assert spy.anonymize_calls == 1
    assert spy.upload_calls == 1
    assert summary["uploaded"] == 1
    m = json.loads(manifest.read_text(encoding="utf-8"))
    assert len(m["rows"]) == 2  # 신규 internal 행 1개 병합.
    new_row = [r for r in m["rows"] if r["s3_key"].startswith("fixtures/phase22/internal/")][0]
    assert gt.eligible_for_distill(new_row) is True
