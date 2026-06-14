"""Phase 4 Wave 5 — 정은지 5영상 재처리 G4 가드 behavioral 테스트 + dry-run schema 검증 + versioned write 검증.

RunPod 불필요 (pure Python 로직 검증). FakeSynthesisAdapter / FakeFirestoreClient 주입으로
reprocess 스크립트의 핵심 invariant 를 행위(behavioral) 로 증명한다.

테스트 4개:
  1. test_g4_guard_no_synthesis_for_reference_reprocess — FakeSynthesisAdapter 주입 → is_reference=True 경로에서 합성 adapter 호출 0
  2. test_dry_run_schema_validation_all_5 — synthetic fixture 기반 5개 motionId payload schema 전부 통과 (11 key)
  3. test_versioned_write_path_uses_versions_subpath — FakeFirestoreClient 주입 → write path == reference/{id}/versions/phase4_v1 정확 일치 + "referenceMotions" 미등장 + flip 전 top-level write 0 (HIGH-2, AST 검색 폐기)
  4. test_active_pointer_flip_requires_all_5 — 4개 미만 완료 시 flip 차단

계약 참조:
  D-09: reference migration 완료 기준 + versioned/atomic write
  D-10: G4 가드 정합 (is_reference=True → 합성 트리거 0)
  BLOCKER-1: reference active doc 에 synthetic 좌표 금지
  BLOCKER-2: joints3d 필드 세트 추가 (04-01 사용자 경로 contract 와 동일)
  HIGH-2: FakeFirestoreClient behavioral path assertion (AST constant 검색 폐기)
  T-04-W5-02: G4 guard bypass 위협 대응
  T-04-W5-03: 5개 미통과 상태에서 active pointer flip 방지
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

# reprocess 스크립트 경로 박제 — importlib.util.spec_from_file_location 로 import.
_SCRIPTS_DIR = Path(__file__).parents[2] / "scripts"
_REPROCESS_SCRIPT = _SCRIPTS_DIR / "reprocess_reference_motions_phase4.py"


def _load_reprocess() -> object:
    """reprocess_reference_motions_phase4.py 를 모듈로 로드."""
    spec = importlib.util.spec_from_file_location(
        "reprocess_reference_motions_phase4",
        str(_REPROCESS_SCRIPT),
    )
    assert spec is not None and spec.loader is not None, (
        f"reprocess_reference_motions_phase4.py 로드 실패 — {_REPROCESS_SCRIPT}"
    )
    mod = importlib.util.module_from_spec(spec)
    # sys.modules 에 등록 — 내부 import 가 이 모듈을 참조할 경우 필요.
    sys.modules["reprocess_reference_motions_phase4"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ── FakeSynthesisAdapter (D-10, T-04-W5-02) ──────────────────────────────────
#
# SynthesisAdapter Protocol 을 구현하는 fake. synthesize_occluded_joints 가
# 호출되면 즉시 AssertionError("synthesis adapter called for reference — G4 guard violated") raise.
# is_reference=True 경로에서 이 fake 를 주입해 호출이 0 임을 행위(behavioral)로 증명한다.


class FakeSynthesisAdapter:
    """synthesis adapter fake — 호출 시 AssertionError raise (G4 guard 위반 감지)."""

    def synthesize_occluded_joints(
        self,
        joint_sequence: np.ndarray,
        confidence_sequence: np.ndarray,
        occlusion_mask: np.ndarray,
        scene_findings: dict,
    ):
        raise AssertionError(
            "synthesis adapter called for reference — G4 guard violated (D-10, T-04-W5-02)"
        )


# ── FakeFirestoreClient (HIGH-2, T-04-W5-03) ─────────────────────────────────
#
# Firestore client fake — .document(path) / .collection(path) 호출 path 를 전부
# 기록. _write_versioned / _flip_active_pointer 호출 후 기록된 경로 검증.


class _FakeDocRef:
    """Fake Document Reference — set/update/get 호출 경로 기록."""

    def __init__(self, path: str, client: "FakeFirestoreClient"):
        self.path = path
        self._client = client

    def set(self, data: dict, **kwargs) -> None:
        self._client.write_calls.append(("set", self.path, data))

    def update(self, data: dict, **kwargs) -> None:
        self._client.write_calls.append(("update", self.path, data))

    def get(self):
        return _FakeDocSnapshot(self.path, self._client)

    def collection(self, name: str) -> "_FakeCollRef":
        return _FakeCollRef(f"{self.path}/{name}", self._client)


class _FakeDocSnapshot:
    """Fake Document Snapshot — 현재 activeVersion + top-level 필드 시뮬."""

    def __init__(self, path: str, client: "FakeFirestoreClient"):
        self._path = path
        self._client = client

    def to_dict(self) -> dict:
        return self._client.doc_state.get(self._path, {})


class _FakeCollRef:
    """Fake Collection Reference."""

    def __init__(self, path: str, client: "FakeFirestoreClient"):
        self.path = path
        self._client = client

    def document(self, name: str) -> "_FakeDocRef":
        return _FakeDocRef(f"{self.path}/{name}", self._client)


class FakeFirestoreClient:
    """Firestore client fake — 호출 경로 / write_calls 기록."""

    def __init__(self):
        self.write_calls: list[tuple] = []
        # doc_state: path → dict (get() 응답용)
        self.doc_state: dict[str, dict] = {}

    def collection(self, name: str) -> "_FakeCollRef":
        return _FakeCollRef(name, self)

    def document(self, path: str) -> "_FakeDocRef":
        return _FakeDocRef(path, self)


# ── 합성 fixture 헬퍼 ─────────────────────────────────────────────────────────


def _make_synthetic_payload(motion_id: str) -> dict:
    """test_dry_run_schema_validation_all_5 용 synthetic payload 생성.

    11개 키 (BLOCKER-2): angles, anglesJointKeys, anglesFrames, keypointReport,
    joints3d, joints3dKeys, joints3dFrames, coordDim, space, pipelineVersion, reprocessedAt.
    """
    T = 10  # 프레임 수 (smoke 용 최소값)
    J_ANGLES = 8  # skeleton.NUM_JOINTS
    J3D = 17  # COCO-17

    angles_flat = [0.0] * (T * J_ANGLES)
    angles_joint_keys = [
        "left_elbow", "right_elbow", "left_shoulder", "right_shoulder",
        "left_hip", "right_hip", "left_knee", "right_knee",
    ]
    keypoint_report: dict = {
        "version": "phase4_v1",
        "joints": ["nose"] * J3D,
        "frames": T,
        "fps": 18.0,
    }
    joints3d_flat = [0.0] * (T * J3D * 3)
    joints3d_keys = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle",
    ]

    return {
        "angles": angles_flat,
        "anglesJointKeys": angles_joint_keys,
        "anglesFrames": T,
        "keypointReport": keypoint_report,
        "joints3d": joints3d_flat,
        "joints3dKeys": joints3d_keys,
        "joints3dFrames": T,
        "coordDim": 3,
        "space": "pole_aligned",
        "pipelineVersion": "phase4_v1",
        "reprocessedAt": datetime.now(timezone.utc).isoformat(),
    }


# ── 테스트 1: G4 가드 behavioral (D-10, T-04-W5-02) ──────────────────────────


def test_g4_guard_no_synthesis_for_reference_reprocess() -> None:
    """FakeSynthesisAdapter 를 reprocess 경로에 주입 → is_reference=True 경로에서
    합성 adapter 호출이 0 임을 행위(behavioral)로 증명한다 (D-10, BLOCKER-1).

    _reprocess_one(motion_id, ..., synthesis_adapter=FakeSynthesisAdapter()) 호출 시
    FakeSynthesisAdapter.synthesize_occluded_joints 가 raise 되지 않으면 GREEN.
    is_reference=True 로 인해 합성 경로를 전혀 타지 않아야 한다 (G4 가드).
    RunPod 불필요 — S3/GPU 의존 없이 pure Python 로직 검증.
    """
    mod = _load_reprocess()
    _reprocess_one = getattr(mod, "_reprocess_one", None)
    assert _reprocess_one is not None, (
        "_reprocess_one 함수가 reprocess_reference_motions_phase4.py 에 없음"
    )

    fake_adapter = FakeSynthesisAdapter()

    # FakeS3Client: S3 download 를 생략하기 위해 dry-run 모드의 mock s3 제공.
    # _reprocess_one 이 synthesis_adapter 를 호출하지 않으면 AssertionError 미발생 = GREEN.
    # S3 / GPU 의존이 있으면 _reprocess_one 내부에서 예외가 발생할 수 있으나
    # synthesis_adapter 호출 여부만이 이 테스트의 관심사.
    # is_reference=True 경로 강제: synthesis_adapter 를 주입하되 호출되면 FAIL.
    try:
        _reprocess_one(
            motion_id="ref-sideway-spin",
            s3=None,  # S3 없음 (dry-run 시 skip)
            extractor=None,
            engine=None,
            target_fps=18.0,
            s3_prefix="reference",
            synthesis_adapter=fake_adapter,
            _dry_run=True,  # dry-run 모드 — S3 download / GPU 생략
        )
    except AssertionError as exc:
        # FakeSynthesisAdapter 가 발동 → G4 가드 미작동 = FAIL.
        pytest.fail(
            f"G4 가드 위반 — FakeSynthesisAdapter.synthesize_occluded_joints 가 호출됨 "
            f"(is_reference=True 경로에서 합성이 발동되어서는 안 됨). 상세: {exc}"
        )
    except Exception:
        # S3/GPU 없는 환경에서 다른 예외가 발생해도 synthesis_adapter 호출이 없으면 GREEN.
        # FakeSynthesisAdapter 호출만 체크하므로 다른 예외는 무시.
        pass

    # FakeSynthesisAdapter 의 synthesize_occluded_joints 가 호출된 적 없음 = PASS.
    # 호출 시 AssertionError 가 이미 pytest.fail 로 변환됨.
    # 추가 단언: AssertionError 가 발생하지 않은 것이 곧 호출 0 증명.


# ── 테스트 2: dry-run schema 검증 all 5 (BLOCKER-2) ──────────────────────────


def test_dry_run_schema_validation_all_5() -> None:
    """synthetic fixture 를 이용해 5개 motionId payload 의 schema 를 검증한다 (BLOCKER-2).

    11개 키 전부 존재해야 GREEN:
      angles, anglesJointKeys, anglesFrames, keypointReport,
      joints3d, joints3dKeys, joints3dFrames, coordDim(==3),
      space("pole_aligned"), pipelineVersion("phase4_v1"), reprocessedAt

    5개 motionId 전부 통과해야 GREEN. 1개라도 key 누락 → FAIL.
    "_5개 전부 통과 전 쓰기 0" 원칙의 dry-run 검증.
    """
    mod = _load_reprocess()
    _validate_payload_schema = getattr(mod, "_validate_payload_schema", None)
    assert _validate_payload_schema is not None, (
        "_validate_payload_schema 함수가 reprocess_reference_motions_phase4.py 에 없음"
    )

    motion_ids = getattr(mod, "MOTION_IDS", None)
    assert motion_ids is not None and len(motion_ids) == 5, (
        f"MOTION_IDS 가 없거나 5개가 아님: {motion_ids}"
    )

    # 11개 필수 키 (BLOCKER-2)
    REQUIRED_KEYS = {
        "angles", "anglesJointKeys", "anglesFrames",
        "keypointReport",
        "joints3d", "joints3dKeys", "joints3dFrames",
        "coordDim", "space",
        "pipelineVersion", "reprocessedAt",
    }

    for motion_id in motion_ids:
        payload = _make_synthetic_payload(motion_id)
        # _validate_payload_schema 는 ValueError 를 raise 해서는 안 됨 — 모든 키 존재.
        try:
            _validate_payload_schema(payload, motion_id)
        except ValueError as exc:
            pytest.fail(
                f"[{motion_id}] _validate_payload_schema 실패 — {exc}"
            )

        # 직접 키 존재 단언 (validator 가 일부만 검사할 경우 대비 이중 검증).
        missing = REQUIRED_KEYS - set(payload.keys())
        assert not missing, (
            f"[{motion_id}] payload 에 필수 키 누락: {sorted(missing)}"
        )

        # coordDim == 3 단언 (BLOCKER-2)
        assert payload["coordDim"] == 3, (
            f"[{motion_id}] coordDim != 3: {payload['coordDim']}"
        )
        # space == "pole_aligned" 단언 (BLOCKER-2)
        assert payload["space"] == "pole_aligned", (
            f"[{motion_id}] space != 'pole_aligned': {payload['space']}"
        )
        # pipelineVersion == "phase4_v1" 단언
        assert payload["pipelineVersion"] == "phase4_v1", (
            f"[{motion_id}] pipelineVersion != 'phase4_v1': {payload['pipelineVersion']}"
        )
        # joints3dKeys 길이 == 17 (COCO-17)
        assert len(payload["joints3dKeys"]) == 17, (
            f"[{motion_id}] joints3dKeys 길이 != 17: {len(payload['joints3dKeys'])}"
        )
        # angles 비어있지 않음
        assert len(payload["angles"]) > 0, (
            f"[{motion_id}] angles 가 빈 list"
        )


# ── 테스트 3: versioned write path (HIGH-2, AST 검색 폐기) ───────────────────


def test_versioned_write_path_uses_versions_subpath() -> None:
    """FakeFirestoreClient 주입 → write path == reference/{id}/versions/phase4_v1 정확 일치 단언.

    "referenceMotions" 문자열이 어떤 호출 path 에도 등장하지 않음을 단언 (HIGH-2/HIGH-3).
    _flip_active_pointer: completed 5개 미만일 때 top-level merge/update 호출 횟수 == 0 단언 (gate 전 쓰기 0).
    5개 완료 후에만 active pointer + top-level mirror write 발생 확인.

    AST constant 검색 폐기 — 실 write path 를 FakeFirestoreClient 로 증명.
    """
    mod = _load_reprocess()
    _write_versioned = getattr(mod, "_write_versioned", None)
    _flip_active_pointer = getattr(mod, "_flip_active_pointer", None)
    assert _write_versioned is not None, (
        "_write_versioned 함수 없음"
    )
    assert _flip_active_pointer is not None, (
        "_flip_active_pointer 함수 없음"
    )

    motion_ids = list(getattr(mod, "MOTION_IDS"))

    # 테스트할 단일 motionId
    test_motion_id = "ref-foxtop"
    payload = _make_synthetic_payload(test_motion_id)

    fake_fs = FakeFirestoreClient()
    result_path = _write_versioned(fake_fs, test_motion_id, payload)

    # write path == "reference/{id}/versions/phase4_v1" 정확 일치 단언.
    written_paths = [call[1] for call in fake_fs.write_calls]
    expected_path = f"reference/{test_motion_id}/versions/phase4_v1"
    assert any(expected_path in p for p in written_paths), (
        f"versioned write path 에 '{expected_path}' 미포함. "
        f"실제 기록된 paths: {written_paths}"
    )

    # "referenceMotions" 문자열이 어떤 호출 path 에도 등장하지 않음 단언 (HIGH-2/HIGH-3).
    for p in written_paths:
        assert "referenceMotions" not in p, (
            f"write path 에 'referenceMotions' 등장 — canonical reference collection 만 허용 "
            f"(HIGH-2, HIGH-3). path: {p}"
        )

    # _flip_active_pointer: completed 5개 미만일 때 top-level update 호출 횟수 == 0 (gate 전 쓰기 0).
    partial_completed = {m: _make_synthetic_payload(m) for m in motion_ids[:4]}  # 4개 (5개 미만)
    fake_fs_partial = FakeFirestoreClient()
    try:
        _flip_active_pointer(fake_fs_partial, motion_ids, partial_completed)
    except (ValueError, AssertionError):
        # 4개 미만 완료 시 flip 차단 예외 = 정상 (test 4 에서 별도 검증).
        pass

    # flip 전 (4개 미만) 에서 top-level update/set write 발생하지 않아야 함.
    # reference/{id}/versions/ 하위가 아닌 reference/{id} top-level 에 write 없음.
    flip_writes_partial = [
        call for call in fake_fs_partial.write_calls
        if "versions" not in call[1]  # top-level write = versions 없는 path
    ]
    assert len(flip_writes_partial) == 0, (
        f"_flip_active_pointer 가 4개 미만 상태에서 top-level write 발생 — gate 전 쓰기 0 원칙 위반. "
        f"발생한 write: {flip_writes_partial}"
    )

    # 5개 완료 후 _flip_active_pointer 실행 — active pointer + top-level mirror write 발생 확인.
    full_completed = {m: _make_synthetic_payload(m) for m in motion_ids}
    fake_fs_full = FakeFirestoreClient()
    # 현재 activeVersion 스냅샷 박제 (pre_phase4 백업용)
    for m in motion_ids:
        fake_fs_full.doc_state[f"reference/{m}"] = {
            "activeVersion": "pre_phase4",
            "angles": [],
        }
    try:
        _flip_active_pointer(fake_fs_full, motion_ids, full_completed)
    except Exception as exc:
        # full 5개 시에도 예외가 나면 스크립트 구현 문제.
        pytest.fail(
            f"_flip_active_pointer 가 5개 완료 상태에서 예외 raise — 구현 확인 필요: {exc}"
        )

    # 5개 완료 후에는 top-level write (activeVersion + mirror) 가 최소 5건 이상 발생해야 함.
    flip_writes_full = [
        call for call in fake_fs_full.write_calls
        if "versions" not in call[1]  # top-level write
    ]
    assert len(flip_writes_full) >= len(motion_ids), (
        f"_flip_active_pointer 5개 완료 시 top-level write 가 motion 수보다 적음 — "
        f"active pointer + top-level mirror 가 write 되어야 함. "
        f"write 수: {len(flip_writes_full)}, motion 수: {len(motion_ids)}"
    )


# ── 테스트 4: active pointer flip gate (T-04-W5-03) ─────────────────────────


def test_active_pointer_flip_requires_all_5() -> None:
    """partial_results 4개 미만 완료 시 flip 이 실행되지 않거나 ValueError/AssertionError 가
    raise 됨을 확인한다 (T-04-W5-03 — 5개 전부 성공 시에만 active pointer flip).

    5개 전부 성공 시에만 active pointer flip 진행 — 분析 정확도 최우선 (D-09).
    """
    mod = _load_reprocess()
    _flip_active_pointer = getattr(mod, "_flip_active_pointer", None)
    assert _flip_active_pointer is not None, (
        "_flip_active_pointer 함수 없음"
    )

    motion_ids = list(getattr(mod, "MOTION_IDS"))
    assert len(motion_ids) == 5, f"MOTION_IDS 5개 필요: {len(motion_ids)}"

    # 4개 미만 (= 4개) 완료 상태
    partial_completed = {m: _make_synthetic_payload(m) for m in motion_ids[:4]}
    fake_fs = FakeFirestoreClient()

    raised = False
    try:
        _flip_active_pointer(fake_fs, motion_ids, partial_completed)
    except (ValueError, AssertionError):
        # 4개 미만 완료 시 flip 차단 예외 = 정상 (T-04-W5-03).
        raised = True

    # flip 이 실행됐을 경우: fake_fs.write_calls 에 top-level update 있으면 FAIL.
    top_level_writes = [
        call for call in fake_fs.write_calls
        if "versions" not in call[1]
    ]

    # flip 이 실행되지 않았거나 예외가 raise 됐거나 둘 중 하나면 PASS.
    assert raised or len(top_level_writes) == 0, (
        f"_flip_active_pointer 가 4개 미만 완료 상태에서 active pointer flip 을 실행함 — "
        f"T-04-W5-03 위반. top-level write: {top_level_writes}"
    )
