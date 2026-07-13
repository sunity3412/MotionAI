"""내부 fault 트랙 열거 순수 로직 테스트 — consent 게이트/dedup/스케일 가드 (quick 260713-jxr Task 1).

불변식 (처방 B, belle 2026-07-13 결정):
  · learningOptIn=false 문서는 어떤 플래그 조합에서도 제외 (명시 거부 1건 무조건 제외).
  · learningOptIn 부재 문서는 --bulk-approval 명시 + 컷오프(2026-07-13) 이전 생성일
    때만 통과 — 기본값은 strict 제외 (models.py learningOptIn fail-safe 계약 보존).
  · dedup 후 계수가 100~500 밖이면 scale_guard False (T-Q13-04 과금 폭주 방어).
  · 후보 dict 에 uid 키 부재 — uid 는 s3_key 안에만 존재하는 중간값 (T-Q13-01,
    최종 manifest fence 는 test_anonymize_batch 가 소유).

네트워크 0 — 순수 함수만 (Firestore/S3 는 I/O 껍데기, 여기서 미접촉).
"""

from __future__ import annotations

import pytest

from datagen import enumerate_internal as ei

CUTOFF = ei.BELLE_BULK_APPROVAL_CUTOFF_MS
BEFORE_CUTOFF = CUTOFF - 86_400_000  # 컷오프 하루 전.
AFTER_CUTOFF = CUTOFF + 86_400_000   # 컷오프 하루 후.


# ---------------------------------------------------------------------------
# consent_allows — 3분기 (belle 명시 거부 / strict 부재 / bulk 예외).
# ---------------------------------------------------------------------------
def test_consent_false_excluded_even_with_bulk_approval():
    """learningOptIn=false 는 bulk_approval=True 에서도 무조건 제외 (belle 명시 거부)."""
    doc = {"learningOptIn": False, "createdAt": BEFORE_CUTOFF}
    assert ei.consent_allows(doc, bulk_approval=False) is False
    assert ei.consent_allows(doc, bulk_approval=True) is False


def test_consent_absent_strict_excluded_by_default():
    """필드 부재 + bulk_approval=False(기본) → 제외 (models.py fail-safe 계약)."""
    assert ei.consent_allows({"createdAt": BEFORE_CUTOFF}, bulk_approval=False) is False


def test_consent_absent_bulk_passes_only_before_cutoff():
    """필드 부재 + bulk_approval=True → 컷오프 이전 생성만 통과 (이중 방어)."""
    assert ei.consent_allows({"createdAt": BEFORE_CUTOFF}, bulk_approval=True) is True
    assert ei.consent_allows({"createdAt": AFTER_CUTOFF}, bulk_approval=True) is False


def test_consent_absent_bulk_without_created_at_excluded():
    """필드 부재 + createdAt 미상 → bulk 라도 제외 (컷오프 이전 입증 불가 = 방어적 제외)."""
    assert ei.consent_allows({}, bulk_approval=True) is False


def test_consent_true_passes_regardless_of_flags():
    """learningOptIn=true 는 플래그·컷오프 무관 통과."""
    assert ei.consent_allows({"learningOptIn": True}, bulk_approval=False) is True
    assert ei.consent_allows(
        {"learningOptIn": True, "createdAt": AFTER_CUTOFF}, bulk_approval=True
    ) is True


# ---------------------------------------------------------------------------
# derive_upload_key — videoFormat 우선, fileName 확장자 폴백, 미상 None.
# ---------------------------------------------------------------------------
def test_derive_upload_key_video_format_first():
    key = ei.derive_upload_key("uidA", "an1", {"videoFormat": "mp4"})
    assert key == "uploads/uidA/an1.mp4"


def test_derive_upload_key_filename_fallback():
    key = ei.derive_upload_key("uidA", "an2", {"fileName": "video.MOV"})
    assert key == "uploads/uidA/an2.mov"


def test_derive_upload_key_unknown_returns_none():
    assert ei.derive_upload_key("uidA", "an3", {}) is None
    assert ei.derive_upload_key("uidA", "an4", {"fileName": "clip.avi"}) is None
    assert ei.derive_upload_key("uidA", "an5", {"videoFormat": "avi"}) is None


# ---------------------------------------------------------------------------
# dedup_candidates — 후보 간 중복 + known_etags 제외 + 멀티파트 통과.
# ---------------------------------------------------------------------------
def _cand(s3_key: str, etag: str | None) -> dict:
    return {
        "s3_key": s3_key,
        "etag": etag,
        "created_at_ms": BEFORE_CUTOFF,
        "motion": None,
        "provisional_bucket": "fault",
        "opt_in": None,
    }


def test_dedup_keeps_first_among_duplicate_etags():
    cands = [_cand("uploads/u/a.mp4", "e1"), _cand("uploads/u/b.mp4", "e1")]
    out = ei.dedup_candidates(cands, known_etags=set())
    assert [c["s3_key"] for c in out] == ["uploads/u/a.mp4"]


def test_dedup_excludes_known_manifest_etags():
    cands = [_cand("uploads/u/a.mp4", "e1"), _cand("uploads/u/b.mp4", "e2")]
    out = ei.dedup_candidates(cands, known_etags={"e1"})
    assert [c["s3_key"] for c in out] == ["uploads/u/b.mp4"]


def test_dedup_multipart_etag_passes_through():
    """멀티파트 ETag('-')는 pre-dedup 통과 — content-hash dedup(Task 2)에 위임."""
    cands = [
        _cand("uploads/u/a.mp4", "abc-2"),
        _cand("uploads/u/b.mp4", "abc-2"),
    ]
    out = ei.dedup_candidates(cands, known_etags={"abc-2"})
    assert len(out) == 2


def test_dedup_none_etag_passes_through():
    """ETag 미상(head 실패 등)은 dedup 불능 — 통과시켜 후속 hash dedup 에 위임."""
    cands = [_cand("uploads/u/a.mp4", None), _cand("uploads/u/b.mp4", None)]
    out = ei.dedup_candidates(cands, known_etags=set())
    assert len(out) == 2


# ---------------------------------------------------------------------------
# scale_guard — 100~500 경계값 (T-Q13-04).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "n,ok",
    [(99, False), (100, True), (371, True), (500, True), (501, False), (0, False)],
)
def test_scale_guard_bounds(n, ok):
    assert ei.scale_guard(n) is ok


# ---------------------------------------------------------------------------
# provisional_label_bucket — result.overallScore 임계 라벨 (잠정 — 교사 라벨이 최종).
# ---------------------------------------------------------------------------
def test_provisional_bucket_three_way():
    assert ei.provisional_label_bucket({"result": {"overallScore": 85}}) == "정타"
    assert ei.provisional_label_bucket({"result": {"overallScore": 80}}) == "정타"
    assert ei.provisional_label_bucket({"result": {"overallScore": 79}}) == "fault"
    assert ei.provisional_label_bucket({"result": {}}) is None
    assert ei.provisional_label_bucket({}) is None


def test_provisional_bucket_rejects_non_numeric():
    """overall 이 숫자가 아니면 None (bool 은 int subclass 라 명시 거부)."""
    assert ei.provisional_label_bucket({"result": {"overallScore": "85"}}) is None
    assert ei.provisional_label_bucket({"result": {"overallScore": True}}) is None


# ---------------------------------------------------------------------------
# build_candidate — 후보 dict 에 uid 키 부재 (s3_key 안의 uid 는 허용, T-Q13-01).
# ---------------------------------------------------------------------------
def test_build_candidate_has_no_uid_key():
    doc = {
        "learningOptIn": None,
        "createdAt": BEFORE_CUTOFF,
        "videoFormat": "mp4",
        "referenceMotionId": "kip-up",
        "result": {"overallScore": 55},
    }
    cand = ei.build_candidate("uidX", "an9", doc, etag="e9")
    assert "uid" not in cand
    assert "analysisId" not in cand and "analysis_id" not in cand
    assert cand["s3_key"] == "uploads/uidX/an9.mp4"
    assert cand["etag"] == "e9"
    assert cand["provisional_bucket"] == "fault"
    assert cand["motion"] == "kip-up"
    assert cand["created_at_ms"] == BEFORE_CUTOFF


# ---------------------------------------------------------------------------
# out 경로 가드 — 후보 JSON(uid 포함 중간산출물)은 리포 안 기록 금지.
# ---------------------------------------------------------------------------
def test_out_path_inside_repo_rejected(tmp_path):
    repo_internal = ei._REPO_ROOT / "backend" / "training" / "candidates.json"
    assert ei.out_path_inside_repo(str(repo_internal)) is True
    assert ei.out_path_inside_repo(str(tmp_path / "candidates.json")) is False


# ---------------------------------------------------------------------------
# iter_candidate_docs — __name__ 커서 페이지네이션 (라이브 타임아웃 방지 회귀).
# 무페이지 stream 이 872 문서에서 Firestore 503(query timed out)을 낸 사건의 fix.
# 네트워크 0 — fake collection_group 이 select/order_by/limit/start_after/stream 체인
# 을 흉내내 페이지 경계·전수 yield·경로 필터만 검증(실 Firestore 무접촉).
# ---------------------------------------------------------------------------
class _FakeSnap:
    def __init__(self, path, data):
        self.reference = type("R", (), {"path": path})()
        self._data = data

    def to_dict(self):
        return dict(self._data)


class _FakeQuery:
    """select→order_by→limit→(start_after)→stream 체인 흉내. 커서 이후 page_size 만큼 반환."""

    def __init__(self, snaps, page_size=None, after=None):
        self._snaps = snaps
        self._page_size = page_size
        self._after = after

    def select(self, fields):
        return self

    def order_by(self, field):
        return self

    def limit(self, n):
        return _FakeQuery(self._snaps, page_size=n, after=self._after)

    def start_after(self, snap):
        return _FakeQuery(self._snaps, page_size=self._page_size, after=snap)

    def stream(self):
        start = 0
        if self._after is not None:
            start = self._snaps.index(self._after) + 1
        end = start + (self._page_size or len(self._snaps))
        return iter(self._snaps[start:end])


class _FakeDB:
    def __init__(self, snaps):
        self._snaps = snaps

    def collection_group(self, name):
        return _FakeQuery(self._snaps)


def test_iter_candidate_docs_paginates_all_docs():
    """페이지 크기보다 많은 문서를 커서로 전수 yield(무페이지 stream 타임아웃 fix)."""
    snaps = [
        _FakeSnap(f"users/uid{i}/analyses/an{i}", {"status": "done"})
        for i in range(5)
    ]
    db = _FakeDB(snaps)
    got = list(ei.iter_candidate_docs(db, page_size=2))
    assert [uid for uid, _, _ in got] == [f"uid{i}" for i in range(5)]
    assert len(got) == 5


def test_iter_candidate_docs_skips_non_analyses_paths():
    """users/{uid}/analyses/{id} 형식 밖 경로(다른 collection_group 충돌)는 skip."""
    snaps = [
        _FakeSnap("users/uidA/analyses/an1", {"status": "done"}),
        _FakeSnap("orgs/o1/analyses/x", {"status": "done"}),  # 형식 밖.
        _FakeSnap("users/uidB/analyses/an2", {"status": "done"}),
    ]
    got = list(ei.iter_candidate_docs(_FakeDB(snaps), page_size=10))
    assert [uid for uid, _, _ in got] == ["uidA", "uidB"]


def test_iter_candidate_docs_respects_limit():
    """limit 도달 시 조기 종료(스트림 중단)."""
    snaps = [
        _FakeSnap(f"users/uid{i}/analyses/an{i}", {"status": "done"})
        for i in range(10)
    ]
    got = list(ei.iter_candidate_docs(_FakeDB(snaps), limit=3, page_size=2))
    assert len(got) == 3
