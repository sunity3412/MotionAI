"""Pod RTMW 좌표 추출 단위 테스트 — 학습 JSONL 좌표 표현 정합 (22-04 Task 3 선행).

핵심 불변식(GPU 무의존, 모델 로드 없음 — fake (T,17,4) 정규화 배열/fake pose frame):
  · 좌표 행 표현이 build_jsonl._coords_to_frames 와 정확히 동일(discretize width=height=1.0,
    schema '상대좌표 ×1000' 계약) — 시험 대표성의 근거.
  · frame = 9fps 원 인덱스 서브샘플(select_frame_indices), 원 영상 재추출 0.
  · 결측/미감지 관절 = None 바인딩(D-11 철칙 1), 12 대상 관절 키 존재.
  · 캐시 키(video_hash 우선 → s3_key slug) + 관절 채움 헬스 리포트.

네트워크/torch/imageio 미의존 — 순수 조립만 검증. GPU 추론 배선
(extract_coords_for_video)은 Pod 세션에서 실측한다.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from datagen import schema
from datagen.build_jsonl import _coords_to_frames
from distill import pod_coords as pc
from distill.gemini_teacher import DEFAULT_TASK_JOINTS


# ---------------------------------------------------------------------------
# fake keypoints_2d / pose frames — (T, 17, 4) 정규화 배열에서 조립 (모델 무의존).
# ---------------------------------------------------------------------------
def _coco_names():
    from sunity_shared.analysis import skeleton

    return list(skeleton.KEYPOINT_NAMES)


def _fake_pose_frames(arr17):
    """(T, 17, 4) 정규화 배열 → fake PoseFrame 리스트.

    채널 = [x, y, z(무시), visibility]. NaN 관절은 keypoints_2d 에서 제외(미감지 모사).
    keypoints_2d 는 duck-typed(.x/.y/.visibility) — 실 Keypoint2D 없이 조립 로직만 검증.
    """
    names = _coco_names()
    frames = []
    for t in range(arr17.shape[0]):
        kp2d = {}
        for j, name in enumerate(names):
            x, y, vis = arr17[t, j, 0], arr17[t, j, 1], arr17[t, j, 3]
            if not (np.isfinite(x) and np.isfinite(y)):
                continue  # 미감지 관절은 dict 부재.
            kp2d[name] = SimpleNamespace(x=float(x), y=float(y), visibility=float(vis))
        frames.append(SimpleNamespace(keypoints_2d=kp2d))
    return frames


def _dense_array(T=100, val=0.5, vis=0.9):
    """모든 관절이 채워진 (T, 17, 4) 정규화 배열."""
    arr = np.full((T, 17, 4), np.nan, dtype=float)
    arr[:, :, 0] = val
    arr[:, :, 1] = val
    arr[:, :, 2] = 0.0  # z (무시)
    arr[:, :, 3] = vis
    return arr


# ---------------------------------------------------------------------------
# 표현 정합 — build_jsonl._coords_to_frames 와 동일해야 한다(최우선 불변식).
# ---------------------------------------------------------------------------
def test_rows_match_build_jsonl_representation():
    """frames_to_coords_rows == _coords_to_frames(width=height=1.0) — 표현 단일 owner."""
    T = 80
    task = np.full((T, len(DEFAULT_TASK_JOINTS), 3), np.nan, dtype=float)
    rng = np.random.default_rng(0)
    task[:, :, 0] = rng.random((T, len(DEFAULT_TASK_JOINTS)))
    task[:, :, 1] = rng.random((T, len(DEFAULT_TASK_JOINTS)))
    task[:, :, 2] = 0.8

    idxs = schema.select_frame_indices(T, pc.DEFAULT_FRAME_BUDGET)
    expected = _coords_to_frames(task, list(DEFAULT_TASK_JOINTS), idxs, 1.0, 1.0)
    got = pc.frames_to_coords_rows(task, DEFAULT_TASK_JOINTS)
    assert got == expected


def test_discretize_scale_is_relative_times_1000():
    """정규화 0.5 → dx=round(0.5*999)=500 (schema '상대좌표 ×1000' 계약)."""
    task = np.full((4, len(DEFAULT_TASK_JOINTS), 3), np.nan, dtype=float)
    task[:, :, 0] = 0.5
    task[:, :, 1] = 0.0
    task[:, :, 2] = 1.0
    rows = pc.frames_to_coords_rows(task, DEFAULT_TASK_JOINTS)
    dx, dy, conf = rows[0][DEFAULT_TASK_JOINTS[0]]
    assert dx == 500 and dy == 0 and conf == 1.0


def test_frame_is_original_9fps_index():
    """frame 필드 = select_frame_indices 원 인덱스(재추출 아님, Pattern 1)."""
    T = 130
    task = _dense_task(T)
    idxs = schema.select_frame_indices(T, pc.DEFAULT_FRAME_BUDGET)
    rows = pc.frames_to_coords_rows(task, DEFAULT_TASK_JOINTS)
    assert [r["frame"] for r in rows] == idxs
    assert len(rows) == len(idxs)


def _dense_task(T):
    task = np.full((T, len(DEFAULT_TASK_JOINTS), 3), np.nan, dtype=float)
    task[:, :, 0] = 0.3
    task[:, :, 1] = 0.7
    task[:, :, 2] = 0.95
    return task


# ---------------------------------------------------------------------------
# 관절 12개 계약 + 미감지 Null 바인딩.
# ---------------------------------------------------------------------------
def test_all_12_task_joints_present_and_typed():
    """모든 행에 12 대상 관절 키 + [dx,dy,conf] (dx,dy int 0..999)."""
    rows = pc.frames_to_coords_rows(_dense_task(50), DEFAULT_TASK_JOINTS)
    assert rows
    for r in rows:
        for name in DEFAULT_TASK_JOINTS:
            assert name in r
            dx, dy, conf = r[name]
            assert isinstance(dx, int) and 0 <= dx <= 999
            assert isinstance(dy, int) and 0 <= dy <= 999
            assert isinstance(conf, float)


def test_missing_joint_binds_null():
    """미감지 관절(NaN) → None (키 삭제 금지, D-11 철칙 1)."""
    task = _dense_task(20)
    task[:, 0, :] = np.nan  # 첫 관절 전 프레임 미감지.
    rows = pc.frames_to_coords_rows(task, DEFAULT_TASK_JOINTS)
    missing = DEFAULT_TASK_JOINTS[0]
    kept = DEFAULT_TASK_JOINTS[1]
    for r in rows:
        assert r[missing] is None
        assert r[kept] is not None


def test_empty_or_bad_shape_returns_empty():
    assert pc.frames_to_coords_rows(np.zeros((0, 12, 3)), DEFAULT_TASK_JOINTS) == []
    assert pc.frames_to_coords_rows(np.zeros((5, 12)), DEFAULT_TASK_JOINTS) == []


# ---------------------------------------------------------------------------
# pose frame → task array (fake (T,17,4), 모델 무의존).
# ---------------------------------------------------------------------------
def test_task_array_from_fake_pose_frames_selects_12_joints():
    """fake (T,17,4) 정규화 배열 → keypoints_2d → (T,12,3) 대상 관절만."""
    arr17 = _dense_array(T=30, val=0.4, vis=0.85)
    frames = _fake_pose_frames(arr17)
    out = pc.task_array_from_pose_frames(frames, DEFAULT_TASK_JOINTS)
    assert out.shape == (30, len(DEFAULT_TASK_JOINTS), 3)
    assert np.allclose(out[:, :, 0], 0.4)
    assert np.allclose(out[:, :, 2], 0.85)


def test_task_array_missing_joint_is_nan():
    """keypoints_2d 에 없는 관절 → NaN (하류에서 Null 바인딩)."""
    arr17 = _dense_array(T=10)
    names = _coco_names()
    left_ankle_idx = names.index("left_ankle")
    arr17[:, left_ankle_idx, :] = np.nan  # left_ankle 미감지.
    frames = _fake_pose_frames(arr17)
    out = pc.task_array_from_pose_frames(frames, DEFAULT_TASK_JOINTS)
    k = list(DEFAULT_TASK_JOINTS).index("left_ankle")
    assert np.all(np.isnan(out[:, k, :]))


def test_end_to_end_fake_frames_to_rows():
    """fake pose frames → task array → 좌표 행 (전 조립 체인, GPU 무의존)."""
    arr17 = _dense_array(T=64, val=0.25, vis=0.9)
    frames = _fake_pose_frames(arr17)
    task = pc.task_array_from_pose_frames(frames, DEFAULT_TASK_JOINTS)
    rows = pc.frames_to_coords_rows(task, DEFAULT_TASK_JOINTS)
    assert rows
    dx, dy, conf = rows[0][DEFAULT_TASK_JOINTS[0]]
    assert dx == round(0.25 * 999)
    assert conf == 0.9


# ---------------------------------------------------------------------------
# 캐시 키 + 헬스 리포트.
# ---------------------------------------------------------------------------
def test_cache_key_prefers_video_hash():
    assert pc.coords_cache_key({"video_hash": "abc123", "s3_key": "x/y.mp4"}) == "abc123"


def test_cache_key_slug_from_s3_key():
    assert pc.coords_cache_key({"s3_key": "reference/ref-climb.mp4"}) == "reference__ref-climb"
    assert pc.coords_cache_key({"s3_key": "a/b/c.mov"}) == "a__b__c"


def test_cache_key_empty_row():
    assert pc.coords_cache_key({}) == "unknown"


def test_coords_health_all_present():
    rows = pc.frames_to_coords_rows(_dense_task(20), DEFAULT_TASK_JOINTS)
    h = pc.coords_health(rows, DEFAULT_TASK_JOINTS)
    assert h["all_joints_present"] is True
    assert h["joints_filled_ratio"] == 1.0
    assert h["null_ratio"] == 0.0
    assert h["joints_present"] == sorted(DEFAULT_TASK_JOINTS)


def test_coords_health_partial_null():
    task = _dense_task(10)
    task[:, 0, :] = np.nan
    rows = pc.frames_to_coords_rows(task, DEFAULT_TASK_JOINTS)
    h = pc.coords_health(rows, DEFAULT_TASK_JOINTS)
    assert h["all_joints_present"] is False
    assert 0.0 < h["null_ratio"] < 1.0
    assert DEFAULT_TASK_JOINTS[0] not in h["joints_present"]


def test_cache_roundtrip(tmp_path):
    rows = pc.frames_to_coords_rows(_dense_task(8), DEFAULT_TASK_JOINTS)
    path = pc.save_coords(str(tmp_path), "k1", rows)
    assert path.endswith("k1.json")
    assert pc.load_cached_coords(str(tmp_path), "k1") == rows
    assert pc.load_cached_coords(str(tmp_path), "missing") is None


def test_provider_uses_cache(tmp_path):
    """provider 는 캐시 hit 를 재추출 없이 반환(scratch_dir miss 여도 GPU 무접촉)."""
    rows = pc.frames_to_coords_rows(_dense_task(8), DEFAULT_TASK_JOINTS)
    row = {"s3_key": "reference/ref-climb.mp4"}
    pc.save_coords(str(tmp_path), pc.coords_cache_key(row), rows)
    provider = pc.make_coords_provider(str(tmp_path))
    assert provider(row) == rows


def test_provider_cache_miss_no_scratch_returns_empty(tmp_path):
    provider = pc.make_coords_provider(str(tmp_path))
    assert provider({"s3_key": "reference/never.mp4"}) == []


def test_rows_to_task_array_inverts_discretize(tmp_path):
    """frames_to_coords_rows → rows_to_task_array 왕복 — 그리드 오차 ≤ 1/999."""
    import numpy as np

    task = _dense_task(6)
    rows = pc.frames_to_coords_rows(task, DEFAULT_TASK_JOINTS)
    arr = pc.rows_to_task_array(rows, DEFAULT_TASK_JOINTS)
    assert arr.shape == (len(rows), len(DEFAULT_TASK_JOINTS), 3)
    # 서브샘플된 원좌표와 비교 — x/y 는 그리드 오차 내, NaN 마스크 보존.
    from datagen import schema

    idxs = schema.select_frame_indices(task.shape[0], pc.DEFAULT_FRAME_BUDGET)
    sub = np.asarray(task, dtype=float)[idxs]
    both = ~(np.isnan(sub[..., 0]) | np.isnan(arr[..., 0]))
    assert np.all(np.abs(sub[..., :2][both] - arr[..., :2][both]) <= (1.0 / 999.0) + 1e-9)


def test_make_perturb_loader_contract(tmp_path):
    """full_batch.make_perturb_loader — 캐시 hit → build_jsonl 계약 dict, miss → None."""
    from distill.full_batch import make_perturb_loader

    rows = pc.frames_to_coords_rows(_dense_task(8), DEFAULT_TASK_JOINTS)
    row = {"s3_key": "fixtures/phase22/a/b.mp4"}
    pc.save_coords(str(tmp_path), pc.coords_cache_key(row), rows)
    loader = make_perturb_loader(str(tmp_path))
    loaded = loader(row)
    assert loaded is not None
    assert loaded["coords"].shape[1] == len(DEFAULT_TASK_JOINTS)
    assert loaded["width"] == 1.0 and loaded["height"] == 1.0
    assert loader({"s3_key": "fixtures/phase22/miss.mp4"}) is None
