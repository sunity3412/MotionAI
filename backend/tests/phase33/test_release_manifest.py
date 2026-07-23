"""Phase 33 (33-18) — release_manifest.py 계약 잠금 (LOCAL ONLY, Firestore/Pod 무접촉).

release_manifest 는 substrate 를 하나의 릴리스 튜플로 묶는다:
  {candidateVersion, perDocHashes(11), commitSha, targetFps, prInversionEnabled,
   rtmwDeterministic, derivedFieldSchemaVersion, verificationResult, updatedAt}.

이 테스트가 잠그는 것 (D-31 / codex suggestion 2):
  1. create → verify (일치) → 통과.
  2. verify — candidate doc 한 개를 조작하면 per-doc 해시 불일치로 실패(non-zero).
  3. tuple-completeness — 필드가 하나라도 빠지면 verify 실패(non-zero).

fake Firestore 는 `reference/{id}/versions/{candidate}` 경로 조회와 `reference/_release`
publish 만 재현한다 (release_manifest 가 실제로 쓰는 seam 만).
"""

from __future__ import annotations

import copy
import json

import pytest

import release_manifest as rm


# ─────────────────────── in-memory Firestore (release_manifest seam 한정) ───────────────────────


class _FakeSnap:
    def __init__(self, data: dict | None) -> None:
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> dict:
        return copy.deepcopy(self._data) if self._data is not None else {}


class _FakeDoc:
    def __init__(self, store: dict, path: str) -> None:
        self._store = store
        self._path = path

    def collection(self, name: str) -> "_FakeColl":
        return _FakeColl(self._store, f"{self._path}/{name}")

    def get(self) -> _FakeSnap:
        return _FakeSnap(self._store.get(self._path))

    def set(self, payload: dict, merge: bool = False) -> None:
        if merge and self._path in self._store:
            self._store[self._path].update(copy.deepcopy(payload))
        else:
            self._store[self._path] = copy.deepcopy(payload)


class _FakeColl:
    def __init__(self, store: dict, path: str) -> None:
        self._store = store
        self._path = path

    def document(self, doc_id: str) -> _FakeDoc:
        return _FakeDoc(self._store, f"{self._path}/{doc_id}")


class FakeDB:
    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    def collection(self, name: str) -> _FakeColl:
        return _FakeColl(self.store, name)

    def document(self, path: str) -> _FakeDoc:
        return _FakeDoc(self.store, path)

    def seed_version(self, motion_id: str, candidate: str, payload: dict) -> None:
        self.store[f"reference/{motion_id}/versions/{candidate}"] = copy.deepcopy(payload)


CANDIDATE = "phase33-cm3-run1"
COMMIT = "abc1234def5678"


def _seed_all(db: FakeDB, candidate: str = CANDIDATE) -> None:
    for i, mid in enumerate(rm.MOTION_IDS):
        db.seed_version(
            mid,
            candidate,
            {
                "angles": [float(i), float(i) + 0.5, float(i) + 1.0],
                "anglesJointKeys": ["a", "b"],
                "anglesFrames": 3,
                "space": "pole_aligned",
                "pipelineVersion": candidate,
            },
        )


# ─────────────────────── 1. create → verify (일치) ───────────────────────


def test_create_then_verify_matches():
    db = FakeDB()
    _seed_all(db)
    manifest = rm.create_manifest(candidate=CANDIDATE, commit=COMMIT, db=db)

    # 8-field 튜플 존재 확인.
    assert manifest["candidateVersion"] == CANDIDATE
    assert manifest["commitSha"] == COMMIT
    assert manifest["targetFps"] == rm.DEFAULT_TARGET_FPS
    assert manifest["prInversionEnabled"] is True
    assert manifest["rtmwDeterministic"] is True
    assert manifest["derivedFieldSchemaVersion"]
    assert manifest["verificationResult"] is None
    assert len(manifest["perDocHashes"]) == len(rm.MOTION_IDS)

    ok, problems = rm.verify_manifest(manifest, db=db)
    assert ok, problems
    assert problems == []


# ─────────────────────── 2. verify — 조작된 candidate doc → non-zero ───────────────────────


def test_verify_fails_on_doctored_doc():
    db = FakeDB()
    _seed_all(db)
    manifest = rm.create_manifest(candidate=CANDIDATE, commit=COMMIT, db=db)

    # 한 doc 의 저장된 angles 를 조작 → 해시가 어긋난다.
    victim = rm.MOTION_IDS[3]
    db.store[f"reference/{victim}/versions/{CANDIDATE}"]["angles"] = [9999.0]

    ok, problems = rm.verify_manifest(manifest, db=db)
    assert not ok
    assert any(victim in p for p in problems)


# ─────────────────────── 3. tuple-completeness ───────────────────────


def test_verify_fails_on_incomplete_tuple():
    db = FakeDB()
    _seed_all(db)
    manifest = rm.create_manifest(candidate=CANDIDATE, commit=COMMIT, db=db)

    # commitSha 를 비운다 → 불완전 튜플.
    manifest["commitSha"] = None
    ok, problems = rm.verify_manifest(manifest, db=db)
    assert not ok
    assert any("commitSha" in p for p in problems)

    # perDocHashes 에서 하나를 제거해도 실패.
    manifest2 = rm.create_manifest(candidate=CANDIDATE, commit=COMMIT, db=db)
    manifest2["perDocHashes"].pop(rm.MOTION_IDS[0])
    ok2, _ = rm.verify_manifest(manifest2, db=db)
    assert not ok2


# ─────────────────────── 4. verify — 누락된 candidate doc → non-zero ───────────────────────


def test_verify_fails_on_missing_version_doc():
    db = FakeDB()
    _seed_all(db)
    manifest = rm.create_manifest(candidate=CANDIDATE, commit=COMMIT, db=db)

    # candidate 버전 doc 을 통째로 지운다.
    missing = rm.MOTION_IDS[5]
    del db.store[f"reference/{missing}/versions/{CANDIDATE}"]

    ok, problems = rm.verify_manifest(manifest, db=db)
    assert not ok
    assert any(missing in p for p in problems)


# ─────────────────────── 5. publish — reference/_release 로 튜플 기록 ───────────────────────


def test_publish_writes_global_release_pointer():
    db = FakeDB()
    _seed_all(db)
    manifest = rm.create_manifest(candidate=CANDIDATE, commit=COMMIT, db=db)

    pointer = rm.publish_manifest(manifest, db=db)
    assert pointer["activeCandidate"] == CANDIDATE

    stored = db.store[f"reference/{rm.RELEASE_POINTER_ID}"]
    assert stored["activeCandidate"] == CANDIDATE
    assert stored["commitSha"] == COMMIT
    assert len(stored["perDocHashes"]) == len(rm.MOTION_IDS)
    # publish 는 검증 결과를 함께 각인한다 (PASS).
    assert stored["verificationResult"]["status"] == "PASS"


def test_publish_refuses_mismatched_tuple():
    db = FakeDB()
    _seed_all(db)
    manifest = rm.create_manifest(candidate=CANDIDATE, commit=COMMIT, db=db)
    # candidate doc 조작 → publish 는 검증 실패로 pointer 를 쓰지 않아야 한다.
    db.store[f"reference/{rm.MOTION_IDS[1]}/versions/{CANDIDATE}"]["angles"] = [1.0]

    with pytest.raises(rm.ManifestError):
        rm.publish_manifest(manifest, db=db)
    assert f"reference/{rm.RELEASE_POINTER_ID}" not in db.store


# ─────────────────────── 6. content-hash 결정성 (33-07 flip 이 재계산 공유) ───────────────────────


def test_doc_content_hash_is_deterministic_and_order_independent():
    a = {"angles": [1.0, 2.0], "space": "pole_aligned", "anglesFrames": 2}
    b = {"anglesFrames": 2, "space": "pole_aligned", "angles": [1.0, 2.0]}
    assert rm.doc_content_hash(a) == rm.doc_content_hash(b)
    c = {"angles": [1.0, 2.1], "space": "pole_aligned", "anglesFrames": 2}
    assert rm.doc_content_hash(a) != rm.doc_content_hash(c)


# ─────────────────────── 7. CLI main() — create → verify round-trip ───────────────────────


def test_cli_create_and_verify(tmp_path, monkeypatch):
    db = FakeDB()
    _seed_all(db)
    # CLI 는 firestore_admin._db() 를 쓰므로 fake 로 치환.
    monkeypatch.setattr(rm, "_resolve_db", lambda: db)

    out = tmp_path / "manifest.json"
    rc = rm.main(
        ["create", "--candidate", CANDIDATE, "--commit", COMMIT, "--out", str(out)]
    )
    assert rc == 0
    written = json.loads(out.read_text())
    assert written["candidateVersion"] == CANDIDATE

    rc2 = rm.main(["verify", "--manifest", str(out)])
    assert rc2 == 0

    # 조작 후 verify 는 non-zero.
    db.store[f"reference/{rm.MOTION_IDS[2]}/versions/{CANDIDATE}"]["angles"] = [0.0]
    rc3 = rm.main(["verify", "--manifest", str(out)])
    assert rc3 != 0
