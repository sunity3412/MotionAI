"""Phase 33-17 — reference-versioning primitives 불변식 잠금 (LOCAL ONLY, Pod/네트워크 0).

codex release-mechanics 3결함을 회귀 테스트로 박제한다:
  - concern 1: immutable candidate id — refuse-overwrite + candidate!=active
  - concern 3: shadow-reference resolver — candidate 를 flip 없이 read-only 소비
  - concern 7: idempotent atomic 11-doc flip — pre_phase4 불변 + 11/11 hash 검증 +
               전역 release 포인터 (reference/_release.activeCandidate)

전부 순수 함수 / in-memory Firestore fake — GPU/Firestore/S3 미접촉.
채점 math 는 건드리지 않는다 (D-20/D-29): versioning/resolver/flip = 데이터 배관.
"""

from __future__ import annotations

import copy
import importlib.util
import logging
import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2]
_SCRIPTS = _BACKEND / "scripts"
_REPROCESS_SCRIPT = _SCRIPTS / "reprocess_reference_motions_phase4.py"


def _load_reprocess():
    """reprocess_reference_motions_phase4.py 를 모듈로 로드 (phase04 선례 동일)."""
    spec = importlib.util.spec_from_file_location(
        "reprocess_reference_motions_phase4_p33", _REPROCESS_SCRIPT
    )
    assert spec is not None and spec.loader is not None, (
        f"reprocess script 로드 실패 — {_REPROCESS_SCRIPT}"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ─────────────────────── in-memory Firestore fake (chained + path seam) ───────────────────────
#
# reprocess 스크립트는 chained builder(fs.collection(id).document(mid).collection('versions')
# .document(v))를 쓰고, firestore_admin.get_reference_motion 은 path seam(_doc(path))을 쓴다.
# 아래 fake 는 동일 store 를 양쪽에 노출해 두 경로가 같은 상태를 본다.


def _deep_merge(base: dict, patch: dict) -> dict:
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = copy.deepcopy(v)
    return base


class _Snap:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return copy.deepcopy(self._data) if self._data is not None else None


class _DocRef:
    def __init__(self, store: dict, path: str):
        self._store = store
        self.path = path
        self.id = path.rsplit("/", 1)[-1]

    def collection(self, name: str) -> "_CollRef":
        return _CollRef(self._store, f"{self.path}/{name}")

    def get(self) -> _Snap:
        return _Snap(self._store.get(self.path))

    def set(self, payload: dict, merge: bool = False) -> None:
        if merge and self.path in self._store:
            _deep_merge(self._store[self.path], payload)
        else:
            self._store[self.path] = copy.deepcopy(payload)

    def update(self, payload: dict) -> None:
        if self.path not in self._store:
            raise KeyError(f"update on missing doc {self.path}")
        cur = self._store[self.path]
        for k, v in payload.items():
            cur[k] = copy.deepcopy(v)


class _CollRef:
    def __init__(self, store: dict, prefix: str):
        self._store = store
        self._prefix = prefix

    def document(self, doc_id: str) -> _DocRef:
        return _DocRef(self._store, f"{self._prefix}/{doc_id}")


class FakeFS:
    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    # chained builder seam (reprocess 스크립트)
    def collection(self, name: str) -> _CollRef:
        return _CollRef(self.store, name)

    # path seam (firestore_admin._doc / _db().document)
    def document(self, path: str) -> _DocRef:
        return _DocRef(self.store, path)

    def doc(self, path: str) -> _DocRef:
        return _DocRef(self.store, path)


def _make_payload(motion_id: str, seed: float = 0.0) -> dict:
    """schema-valid candidate payload (11 키). seed 로 angles 를 흔들어 hash 를 구분."""
    T, J_ANGLES, J3D = 3, 8, 17
    return {
        "angles": [seed + i for i in range(T * J_ANGLES)],
        "anglesJointKeys": [
            "left_elbow", "right_elbow", "left_shoulder", "right_shoulder",
            "left_hip", "right_hip", "left_knee", "right_knee",
        ],
        "anglesFrames": T,
        "keypointReport": {"version": "phase4_v1", "joints": ["nose"], "frames": T, "fps": 18.0},
        "joints3d": [0.0] * (T * J3D * 3),
        "joints3dKeys": [
            "nose", "left_eye", "right_eye", "left_ear", "right_ear",
            "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
            "left_wrist", "right_wrist", "left_hip", "right_hip",
            "left_knee", "right_knee", "left_ankle", "right_ankle",
        ],
        "joints3dFrames": T,
        "coordDim": 3,
        "space": "pole_aligned",
        "pipelineVersion": motion_id,  # overwritten by callers where relevant
        "reprocessedAt": "2026-07-23T00:00:00+00:00",
    }


# ══════════════════════ Task 1: immutable candidate id ══════════════════════


def test_reprocess_one_stamps_resolved_version() -> None:
    """dry-run _reprocess_one(version=X) 가 pipelineVersion=X 로 stamp (frozen 상수 아님)."""
    mod = _load_reprocess()
    payload = mod._reprocess_one(
        motion_id="ref-pdshape", s3=None, extractor=None, engine=None,
        target_fps=18.0, s3_prefix="reference", synthesis_adapter=None,
        _dry_run=True, version="phase33-cm3-run1",
    )
    assert payload["pipelineVersion"] == "phase33-cm3-run1"
    # validator 도 resolved version 과 비교 (frozen 상수 아님)
    mod._validate_payload_schema(payload, "ref-pdshape", "phase33-cm3-run1")
    with pytest.raises(ValueError):
        mod._validate_payload_schema(payload, "ref-pdshape", "phase4_v1")


def test_write_versioned_refuse_overwrite() -> None:
    """versions/{candidate} 가 이미 존재하면 abort (run1 을 run2 가 clobber 못함)."""
    mod = _load_reprocess()
    fs = FakeFS()
    mid = "ref-pdshape"
    # top-level: active = phase4_v1 (candidate != active 는 통과)
    fs.store[f"reference/{mid}"] = {"activeVersion": "phase4_v1"}
    # 이미 run1 이 존재
    fs.store[f"reference/{mid}/versions/phase33-cm3-run1"] = _make_payload(mid, seed=1.0)

    with pytest.raises(ValueError, match="이미 존재|refuse"):
        mod._write_versioned(fs, mid, _make_payload(mid, seed=2.0), "phase33-cm3-run1")


def test_write_versioned_candidate_equals_active_aborts() -> None:
    """resolved version == 현재 activeVersion 이면 abort (phase4_v1 충돌 방지)."""
    mod = _load_reprocess()
    fs = FakeFS()
    mid = "ref-pdshape"
    fs.store[f"reference/{mid}"] = {"activeVersion": "phase33-cm3-run1"}

    with pytest.raises(ValueError, match="activeVersion"):
        mod._write_versioned(fs, mid, _make_payload(mid), "phase33-cm3-run1")


def test_write_versioned_run1_and_run2_stay_distinct() -> None:
    """run1, run2 를 같은 active(phase4_v1) 위에 쓰면 둘 다 성공, 두 version doc 공존."""
    mod = _load_reprocess()
    fs = FakeFS()
    mid = "ref-pdshape"
    fs.store[f"reference/{mid}"] = {"activeVersion": "phase4_v1"}

    p1 = mod._write_versioned(fs, mid, _make_payload(mid, seed=1.0), "phase33-cm3-run1")
    p2 = mod._write_versioned(fs, mid, _make_payload(mid, seed=2.0), "phase33-cm3-run2")

    assert p1 == f"reference/{mid}/versions/phase33-cm3-run1"
    assert p2 == f"reference/{mid}/versions/phase33-cm3-run2"
    assert f"reference/{mid}/versions/phase33-cm3-run1" in fs.store
    assert f"reference/{mid}/versions/phase33-cm3-run2" in fs.store
    # backing 활성 doc 은 무변형 (candidate write 는 active-pointed doc 을 안 건드림)
    assert fs.store[f"reference/{mid}"] == {"activeVersion": "phase4_v1"}
