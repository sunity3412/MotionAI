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


# ══════════════════════ Task 2: shadow-reference resolver + 전역 포인터 ══════════════════════


def _patch_firestore_admin(monkeypatch, fs: FakeFS):
    """firestore_admin._doc 를 FakeFS path seam 으로 교체 → get_reference_motion 검증."""
    from sunity_shared import firestore_admin

    monkeypatch.setattr(firestore_admin, "_doc", fs.doc, raising=True)
    return firestore_admin


def _seed_reference(fs: FakeFS, mid: str, *, top_seed: float, cand_version: str, cand_seed: float):
    top = _make_payload(mid, seed=top_seed)
    top["activeVersion"] = "phase4_v1"
    fs.store[f"reference/{mid}"] = top
    fs.store[f"reference/{mid}/versions/{cand_version}"] = _make_payload(mid, seed=cand_seed)


def test_shadow_env_overlay_returns_candidate_and_leaves_top_level(monkeypatch, caplog):
    """SUNITY_SHADOW_REFERENCE_VERSION 세팅 시 candidate angles overlay + top-level 무변형 + hash 로깅."""
    fs = FakeFS()
    mid = "ref-pdshape"
    _seed_reference(fs, mid, top_seed=100.0, cand_version="phase33-cm3-run1", cand_seed=7.0)
    top_before = copy.deepcopy(fs.store[f"reference/{mid}"])

    fa = _patch_firestore_admin(monkeypatch, fs)
    monkeypatch.setenv("SUNITY_SHADOW_REFERENCE_VERSION", "phase33-cm3-run1")

    with caplog.at_level(logging.INFO, logger="sunity_shared.firestore_admin"):
        out = fa.get_reference_motion(mid)

    # candidate angles overlay (top_seed 100 이 아니라 cand_seed 7 기반)
    assert out is not None
    assert out["angles"] == _make_payload(mid, seed=7.0)["angles"]
    assert out["angles"] != top_before["angles"]
    # top-level 문서는 절대 write 되지 않음 (read-only)
    assert fs.store[f"reference/{mid}"] == top_before
    # version+hash 로깅 증거 (concern 3 — 어떤 candidate 가 소비됐는지 증명)
    logtext = "\n".join(r.getMessage() for r in caplog.records)
    assert "resolved shadow reference" in logtext
    assert "version=phase33-cm3-run1" in logtext
    assert "anglesHash=" in logtext


def test_no_env_no_pointer_returns_top_level_unchanged(monkeypatch):
    """shadow env 없고 _release 포인터 없으면 top-level 그대로 (하위호환)."""
    fs = FakeFS()
    mid = "ref-pdshape"
    _seed_reference(fs, mid, top_seed=100.0, cand_version="phase33-cm3-run1", cand_seed=7.0)

    fa = _patch_firestore_admin(monkeypatch, fs)
    monkeypatch.delenv("SUNITY_SHADOW_REFERENCE_VERSION", raising=False)

    out = fa.get_reference_motion(mid)
    assert out is not None
    assert out["angles"] == _make_payload(mid, seed=100.0)["angles"]  # top-level, candidate 아님


def test_global_release_pointer_resolution(monkeypatch):
    """shadow env 없이 reference/_release.activeCandidate 로 candidate 해석."""
    fs = FakeFS()
    mid = "ref-pdshape"
    _seed_reference(fs, mid, top_seed=100.0, cand_version="phase33-cm3-run1", cand_seed=7.0)
    fs.store["reference/_release"] = {"activeCandidate": "phase33-cm3-run1"}

    fa = _patch_firestore_admin(monkeypatch, fs)
    monkeypatch.delenv("SUNITY_SHADOW_REFERENCE_VERSION", raising=False)

    out = fa.get_reference_motion(mid)
    assert out is not None
    assert out["angles"] == _make_payload(mid, seed=7.0)["angles"]  # 포인터가 가리키는 candidate
    # 포인터 해석도 read-only — top-level 무변형
    assert fs.store[f"reference/{mid}"]["angles"] == _make_payload(mid, seed=100.0)["angles"]


def test_missing_reference_returns_none(monkeypatch):
    """top-level 부재 + shadow/pointer 없음 → None (기존 계약 보존)."""
    fs = FakeFS()
    fa = _patch_firestore_admin(monkeypatch, fs)
    monkeypatch.delenv("SUNITY_SHADOW_REFERENCE_VERSION", raising=False)
    assert fa.get_reference_motion("ref-nope") is None


# ══════════════════════ Task 3: idempotent atomic 11-doc flip ══════════════════════

_FLIP_IDS = ["ref-a", "ref-b", "ref-c"]


def _setup_flip(mod):
    """flip 대상 top-level(구 phase4_v1) 시드 + candidate completed + manifest(hash)."""
    fs = FakeFS()
    completed: dict[str, dict] = {}
    for i, mid in enumerate(_FLIP_IDS):
        # 구 활성 상태 — pre_phase4 rollback preimage 가 될 값.
        fs.store[f"reference/{mid}"] = {
            "activeVersion": "phase4_v1",
            "angles": [999.0],
            "old_meta": mid,
        }
        payload = _make_payload(mid, seed=float(i + 1))
        payload["pipelineVersion"] = "phase33-cm3-run1"
        completed[mid] = payload
    manifest = {mid: mod._release_doc_hash(completed[mid]) for mid in _FLIP_IDS}
    return fs, completed, manifest


def test_flip_pre_phase4_immutable_and_idempotent() -> None:
    """2번째 flip 이 pre_phase4 preimage 를 덮어쓰지 않고 11/11 로 수렴 (concern 7)."""
    mod = _load_reprocess()
    fs, completed, manifest = _setup_flip(mod)

    mod._flip_active_pointer(fs, _FLIP_IDS, completed, "phase33-cm3-run1", manifest)

    pre1 = copy.deepcopy(fs.store["reference/ref-a/versions/pre_phase4"])
    assert pre1["angles"] == [999.0]  # flip 전 구 top-level 을 포착
    assert pre1["activeVersion"] == "phase4_v1"

    # 재실행 전 top-level 을 인위적으로 흔들어 놓음 (crash 후 재개 모사).
    fs.store["reference/ref-a"]["angles"] = [123.0]

    # 2번째 flip (resumable) — 예외 없이 수렴해야 함.
    mod._flip_active_pointer(fs, _FLIP_IDS, completed, "phase33-cm3-run1", manifest)

    pre2 = fs.store["reference/ref-a/versions/pre_phase4"]
    assert pre2 == pre1, "pre_phase4 preimage 가 2번째 flip 에서 덮어써짐 — rollback 소스 파괴"
    # 11/11 activeVersion 수렴 + candidate angles 재-mirror(흔든 값 복구)
    for mid in _FLIP_IDS:
        assert fs.store[f"reference/{mid}"]["activeVersion"] == "phase33-cm3-run1"
    assert fs.store["reference/ref-a"]["angles"] != [123.0]


def test_flip_post_write_verify_detects_doctored_hash() -> None:
    """manifest 의 한 doc hash 를 조작하면 post-write verify 가 raise (부분 flip 감지)."""
    mod = _load_reprocess()
    fs, completed, manifest = _setup_flip(mod)
    manifest["ref-b"] = "deadbeefdeadbeef"  # 11번째 doc(여기선 2번째) hash 오염

    with pytest.raises(ValueError, match="post-write verify|부분 flip|ref-b"):
        mod._flip_active_pointer(fs, _FLIP_IDS, completed, "phase33-cm3-run1", manifest)


def test_flip_drives_global_release_pointer() -> None:
    """flip 이 reference/_release.activeCandidate 를 candidate 로 세팅 (단일 원자 포인터)."""
    mod = _load_reprocess()
    fs, completed, manifest = _setup_flip(mod)

    mod._flip_active_pointer(fs, _FLIP_IDS, completed, "phase33-cm3-run1", manifest)

    assert fs.store["reference/_release"]["activeCandidate"] == "phase33-cm3-run1"
    for mid in _FLIP_IDS:
        assert fs.store[f"reference/{mid}"]["activeVersion"] == "phase33-cm3-run1"


def test_flip_partial_completed_aborts_before_write() -> None:
    """completed 가 motion 수보다 적으면 write 전에 abort (T-04-W5-03 gate 보존)."""
    mod = _load_reprocess()
    fs, completed, manifest = _setup_flip(mod)
    partial = {k: completed[k] for k in _FLIP_IDS[:2]}

    with pytest.raises(ValueError, match="flip 차단"):
        mod._flip_active_pointer(fs, _FLIP_IDS, partial, "phase33-cm3-run1", manifest)
    # 전역 포인터가 쓰이지 않음 (gate 전 쓰기 0)
    assert "reference/_release" not in fs.store


# ═══════ 33-07 flip 잠복 버그 방어: referenceKeypointReport 동반 이동 ═══════
#
# 왜 필요한가: 채점은 `angles` 를, 표시 오버레이는 `referenceKeypointReport` 를 읽는다.
# 후자는 `firestore_admin._REFERENCE_CONSUMER_FIELDS` 에 없어서 **항상 top-level** 에서
# 읽힌다. flip 이 angles 만 옮기고 표시 보고서를 두고 가면 두 축의 타임베이스가 어긋나
# 기준 패널이 의도 시점의 엉뚱한 프레임을 보여준다 (28-RESEARCH D2 기왕 이력).
#
# 소스가 둘인 이유: `_reprocess_one` payload 의 REQUIRED_KEYS 에는
# referenceKeypointReport 가 **없다** (backfill_reference_downstream.py 가 candidate
# 문서에 나중에 MERGE 한다). 그래서 payload 만 보는 1줄은 no-op 이 된다 —
# candidate 버전 문서 폴백이 있어야 실제로 값이 실린다.

_REFKP_A = {
    "version": "phase33", "joints": ["nose", "left_hip"], "frames": 2, "fps": 18.0,
    "data": [0.1] * 8, "confidence": [0.9] * 4,
}
_REFKP_B = {
    "version": "phase33", "joints": ["nose"], "frames": 1, "fps": 9.0,
    "data": [0.2] * 2, "confidence": [0.8],
}


def test_flip_mirrors_reference_keypoint_report_from_payload() -> None:
    """payload 에 referenceKeypointReport 가 있으면 top-level 로 미러된다."""
    mod = _load_reprocess()
    fs, completed, manifest = _setup_flip(mod)
    for mid in _FLIP_IDS:
        completed[mid]["referenceKeypointReport"] = copy.deepcopy(_REFKP_A)
    # payload 에 키가 늘어도 채점 8필드 해시는 그대로 (manifest 재계산 불필요) —
    # 이 단언 자체가 "표시 필드는 채점 해시에 안 든다" 를 지킨다.
    assert manifest == {mid: mod._release_doc_hash(completed[mid]) for mid in _FLIP_IDS}

    mod._flip_active_pointer(fs, _FLIP_IDS, completed, "phase33-cm3-run1", manifest)

    for mid in _FLIP_IDS:
        assert fs.store[f"reference/{mid}"]["referenceKeypointReport"] == _REFKP_A


def test_flip_mirrors_reference_keypoint_report_from_candidate_doc() -> None:
    """payload 에 없고 candidate 버전 문서에만 있으면 폴백으로 미러된다.

    실 프로덕션 형상이 이쪽이다 (_reprocess_one 산출에는 그 키가 없다).
    폴백이 없으면 `payload.get(...)` 1줄은 no-op — "방어했다"가 거짓이 된다.
    """
    mod = _load_reprocess()
    fs, completed, manifest = _setup_flip(mod)
    for mid in _FLIP_IDS:
        assert "referenceKeypointReport" not in completed[mid]  # 전제 박제
        fs.store[f"reference/{mid}/versions/phase33-cm3-run1"] = {
            **copy.deepcopy(completed[mid]),
            "referenceKeypointReport": copy.deepcopy(_REFKP_A),
        }
        # flip 전 top-level 에는 낡은 표시 보고서가 남아 있다 (잠복 버그 재현 조건).
        fs.store[f"reference/{mid}"]["referenceKeypointReport"] = copy.deepcopy(_REFKP_B)

    mod._flip_active_pointer(fs, _FLIP_IDS, completed, "phase33-cm3-run1", manifest)

    for mid in _FLIP_IDS:
        got = fs.store[f"reference/{mid}"]["referenceKeypointReport"]
        assert got == _REFKP_A, f"{mid}: 낡은 표시 보고서가 남음 — 타임베이스 불일치"
        assert got["fps"] == 18.0 and got["frames"] == 2


def test_flip_warns_and_preserves_when_report_absent_everywhere(caplog) -> None:
    """payload·candidate 어디에도 없으면 값을 지어내지 않고 기존 값 보존 + 경고.

    표시 보고서를 날조하지 않는다(fail-closed). 다만 조용히 넘어가면 낡은 타임베이스가
    무증상으로 남으므로 운영자가 알 수 있게 경고를 남긴다.
    """
    mod = _load_reprocess()
    fs, completed, manifest = _setup_flip(mod)
    for mid in _FLIP_IDS:
        fs.store[f"reference/{mid}"]["referenceKeypointReport"] = copy.deepcopy(_REFKP_B)

    with caplog.at_level(logging.WARNING):
        mod._flip_active_pointer(fs, _FLIP_IDS, completed, "phase33-cm3-run1", manifest)

    for mid in _FLIP_IDS:
        assert fs.store[f"reference/{mid}"]["referenceKeypointReport"] == _REFKP_B
    assert "referenceKeypointReport" in caplog.text
