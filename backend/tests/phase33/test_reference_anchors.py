"""33-G §C-1 (quick-260730-l7t Task 1) — 기준 앵커 주석 로더 + 인접매핑 제거 + F-3 초 방출.

근거: 승인 목업 7R (`mockups/index.html` 780-814행 "A-5(33-12) 구현 지시" 4R 확정) —
"기준 라이브러리는 11개 동작으로 고정(phase4_v1 pinned)이라, 기준 쪽 각도 앵커는
기준 모션당 1회 수동 주석으로 달면 끝 — A-5 는 이 저장된 앵커를 읽어 그리기만 하면 돼요."

검증 대상:
  1. `load_reference_anchors` — 시딩 모션 1건 로드 / 미주석 모션 `{}` / 스키마 위반 항목만 드롭.
  2. `resolve_anchor_joint_xy` — 단일 관절 · midpoint · 게이트 미달 None · **report 우선**.
  3. `_KISMAM_TO_KEYPOINT` elbow→hand 인접 매핑 제거 (belle #7·#9 "팔꿈치인데 손을 집고 있음").
  4. F-3 — item 이 `userVideoSec`/`refVideoSec` 를 `_stamp_time` 과 **동일 산출**로 방출.

전부 순수 — S3/네트워크/Firestore 호출 0. 채점 무접촉(D-44): 본 파일의 어떤 값도
deductionBreakdown/veto/게이트에 유입되지 않는다.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_PIPELINE = Path(__file__).resolve().parents[2] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402
from sunity_shared.analysis import reference_anchors as ra  # noqa: E402
from sunity_shared.analysis.keypoint_frame import _KEYPOINT_NAMES  # noqa: E402


# ─────────── 합성 fixture (phase32 parity 골격 복제) ───────────


@dataclass
class _Match:
    start: int
    path: list


_IDENTITY9 = _Match(start=0, path=[(i, i) for i in range(9)])


def _frames(n: int = 9, h: int = 400, w: int = 400) -> np.ndarray:
    a = np.zeros((n, h, w, 3), dtype=np.uint8)
    a[:, :, :, 0] = np.linspace(0, 255, w).astype(np.uint8)[None, None, :]
    a[:, :, :, 1] = np.linspace(0, 255, h).astype(np.uint8)[None, :, None]
    return a


def _report(n: int, fps: float, joint_xy: dict, joint_conf: dict) -> dict:
    joints = list(joint_xy)
    data: list[float] = []
    conf: list[float] = []
    for _f in range(n):
        for j in joints:
            data += list(joint_xy[j])
            conf.append(joint_conf.get(j, 0.9))
    return {
        "joints": joints, "frames": n, "fps": fps,
        "data": data, "confidence": conf,
    }


# ─────────── 1. 로더 ───────────


def test_seeded_motion_carries_approved_substitution():
    """승인 7R 근거 시딩 모션이 로드되고 대입 선언·note 를 나른다."""
    anchors = ra.load_reference_anchors("ref-power-spin")
    assert "angle_vs_reference__left_shoulder" in anchors, (
        "승인 7R 기준 패널 근거 criterion 미시딩"
    )
    entry = anchors["angle_vs_reference__left_shoulder"]
    assert entry["joint_substitutions"]["left_elbow"] == "left_hand"
    # note = 근거 필수 (근거 없는 주석 금지).
    assert isinstance(entry["note"], str) and entry["note"].strip()


def test_unannotated_motion_returns_empty_without_raising():
    """미주석/미존재 모션 → {} (예외 0, fail-closed)."""
    assert ra.load_reference_anchors("ref-does-not-exist-260730") == {}
    assert ra.load_reference_anchors("") == {}
    assert ra.load_reference_anchors(None) == {}  # type: ignore[arg-type]


def test_schema_violation_drops_only_offending_entry(tmp_path):
    """미등재 관절명/비-dict 항목만 드롭하고 나머지는 유지."""
    (tmp_path / "ref-x.yaml").write_text(
        "motion: ref-x\n"
        "annotated: '2026-07-30'\n"
        "source: test\n"
        "criteria:\n"
        "  angle_vs_reference__left_shoulder:\n"
        "    joint_substitutions:\n"
        "      left_elbow: left_hand\n"
        "    note: ok\n"
        "  angle_vs_reference__left_knee:\n"
        "    joint_substitutions:\n"
        "      left_ankle: left_foot_typo\n"   # 미등재 관절명 → 드롭
        "    note: bad target\n"
        "  angle_vs_reference__right_knee: 'not a dict'\n"   # 비-dict → 드롭
        "  angle_vs_reference__left_hip:\n"
        "    joint_substitutions:\n"
        "      left_ankle: left_knee\n"
        "    note: ''\n",                        # note 공백 → 드롭
        encoding="utf-8",
    )
    got = ra.load_reference_anchors("ref-x", base_dir=tmp_path)
    assert set(got) == {"angle_vs_reference__left_shoulder"}


def test_motion_field_must_match_filename(tmp_path):
    """motion 필드 ↔ 파일명 불일치 = 전체 드롭 (오배치 주석 유입 차단, T-l7t-01)."""
    (tmp_path / "ref-a.yaml").write_text(
        "motion: ref-b\ncriteria:\n"
        "  c:\n    joint_substitutions:\n      left_elbow: left_hand\n    note: n\n",
        encoding="utf-8",
    )
    assert ra.load_reference_anchors("ref-a", base_dir=tmp_path) == {}


def test_criteria_block_non_dict_is_empty(tmp_path):
    (tmp_path / "ref-c.yaml").write_text(
        "motion: ref-c\ncriteria: [1, 2, 3]\n", encoding="utf-8"
    )
    assert ra.load_reference_anchors("ref-c", base_dir=tmp_path) == {}


def test_midpoint_declaration_accepted(tmp_path):
    (tmp_path / "ref-m.yaml").write_text(
        "motion: ref-m\ncriteria:\n"
        "  split_angle:\n"
        "    joint_substitutions:\n"
        "      left_ankle:\n"
        "        midpoint: [left_knee, left_hip]\n"
        "    note: n\n",
        encoding="utf-8",
    )
    got = ra.load_reference_anchors("ref-m", base_dir=tmp_path)
    decl = got["split_angle"]["joint_substitutions"]["left_ankle"]
    assert decl == {"midpoint": ["left_knee", "left_hip"]}


# ─────────── 2. 해석기 ───────────


_XY = {
    "left_shoulder": (0.50, 0.30),
    "left_hip": (0.48, 0.55),
    "left_hand": (0.40, 0.10),
    "left_knee": (0.46, 0.80),
}


def test_resolve_single_joint_declaration():
    rep = _report(3, 9.0, _XY, {j: 0.9 for j in _XY})
    got = ra.resolve_anchor_joint_xy(rep, 0, "left_elbow", "left_hand")
    assert got == _XY["left_hand"]


def test_resolve_midpoint_declaration():
    rep = _report(3, 9.0, _XY, {j: 0.9 for j in _XY})
    got = ra.resolve_anchor_joint_xy(
        rep, 0, "left_elbow", {"midpoint": ["left_shoulder", "left_hand"]}
    )
    assert got is not None
    assert abs(got[0] - (0.50 + 0.40) / 2) < 1e-9
    assert abs(got[1] - (0.30 + 0.10) / 2) < 1e-9


def test_resolve_returns_none_when_source_gate_fails():
    """소스 관절 저신뢰 → None (추정 좌표로 선을 긋지 않음, T-l7t-05)."""
    rep = _report(3, 9.0, _XY, {**{j: 0.9 for j in _XY}, "left_hand": 0.2})
    assert ra.resolve_anchor_joint_xy(rep, 0, "left_elbow", "left_hand") is None
    assert ra.resolve_anchor_joint_xy(
        rep, 0, "left_elbow", {"midpoint": ["left_shoulder", "left_hand"]}
    ) is None


def test_report_takes_priority_over_declaration():
    """report 가 관절을 직접 보유하면 선언보다 report 우선 (대입은 부재 관절 전용)."""
    xy = {**_XY, "left_elbow": (0.44, 0.18)}
    rep = _report(3, 9.0, xy, {j: 0.9 for j in xy})
    assert ra.resolve_anchor_joint_xy(rep, 0, "left_elbow", "left_hand") == (0.44, 0.18)


def test_resolve_rejects_malformed_declaration():
    rep = _report(3, 9.0, _XY, {j: 0.9 for j in _XY})
    for bad in (None, 42, [], {"midpoint": ["left_hip"]}, {"other": "x"}, ""):
        assert ra.resolve_anchor_joint_xy(rep, 0, "left_elbow", bad) is None


def test_module_is_scoring_free():
    """채점 모듈 미import (D-44) — display 전용 계약."""
    src = Path(ra.__file__).read_text(encoding="utf-8")
    for banned in ("dimensions", "kismam", "deduction_engine", "boto3", "requests"):
        assert f"import {banned}" not in src and f" {banned} import" not in src, (
            f"reference_anchors 가 {banned} 를 import — 채점/네트워크 무접촉 위반"
        )


def test_declared_joint_names_are_whitelisted():
    """시딩 파일의 모든 관절명이 keypoint_frame 이름공간 안 (오타 방어)."""
    anchors = ra.load_reference_anchors("ref-power-spin")
    for entry in anchors.values():
        for absent, decl in entry["joint_substitutions"].items():
            assert absent in _KEYPOINT_NAMES
            targets = decl["midpoint"] if isinstance(decl, dict) else [decl]
            for t in targets:
                assert t in _KEYPOINT_NAMES


# ─────────── 3. 팔꿈치 인접 매핑 제거 ───────────


def test_pipeline_elbow_map_is_identity_not_hand():
    """`_KISMAM_TO_KEYPOINT` elbow → 동명 관절 (hand 대입 잔재 0).

    belle #7·#9 "팔꿈치인데 손을 집고 있음"(33-G S9)의 실 원인. 32-14 로
    keypointReport 가 12관절이 되어 elbow 직접 표기가 가능해졌다.
    """
    import app  # noqa: PLC0415 - pipeline 모듈은 테스트 시점에 경로 주입 후 import

    m = app._KISMAM_TO_KEYPOINT
    assert m["left_elbow"] == "left_elbow"
    assert m["right_elbow"] == "right_elbow"
    assert "left_hand" not in m.values()
    assert "right_hand" not in m.values()


def test_test_stub_mirror_matches_pipeline_map():
    """테스트 스텁 미러(_ANGLE_MAP)가 파이프라인 map 과 동일 — drift 차단."""
    import app  # noqa: PLC0415

    from test_zoom_join_joint_exact import _ANGLE_MAP  # noqa: PLC0415

    assert _ANGLE_MAP == app._KISMAM_TO_KEYPOINT


# ─────────── 4. F-3 실영상 초 방출 ───────────


def _build_one(**kw):
    frames = _frames()
    u = _report(9, 9.0, {"left_knee": (0.375, 0.5)}, {"left_knee": 0.9})
    r = _report(9, 9.0, {"left_knee": (0.625, 0.5)}, {"left_knee": 0.9})
    base = dict(
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0, dtw_match=_IDENTITY9,
    )
    base.update(kw)
    return fz.build_fault_zoom_comparisons(frames, frames, u, r, **base)


def test_item_emits_video_seconds():
    """userVideoSec/refVideoSec = 프레임 배열 인덱스 / frames_fps (실영상 초)."""
    comps = _build_one()
    assert len(comps) == 1
    item = comps[0]
    assert "userVideoSec" in item and "refVideoSec" in item
    # worst_seconds=0.5 @ 9fps → 프레임 4 (=_frame_index) → 4/9 초.
    assert abs(item["userVideoSec"] - 4 / 9.0) < 1e-9
    assert abs(item["refVideoSec"] - 4 / 9.0) < 1e-9
    # rep 인덱스로 초를 재계산하면 안 된다는 것이 F-3 의 요지 — 두 값은 별개 축.
    assert item["userFrameIdx"] == 4


def test_video_seconds_are_scalars_only():
    """Firestore flat 제약 — 신규 필드도 scalar (T-l7t-02)."""
    item = _build_one()[0]
    for k in ("userVideoSec", "refVideoSec"):
        assert isinstance(item[k], float)


def test_ref_video_sec_omitted_when_ref_match_failed():
    """기준 대응 실패 카드는 refVideoSec 미방출 (같은 순간 근거 없음)."""
    comps = _build_one(dtw_match=None)
    assert len(comps) == 1
    item = comps[0]
    assert item["refMatch"] == "failed"
    assert "refVideoSec" not in item
    assert "userVideoSec" in item


def test_ref_video_sec_uses_display_frame_timebase():
    """refVideoSec = ref_display_frame_index(타임베이스 보정) / frames_fps.

    F-3 근본원인 = 앱이 refFrameIdx / rep.fps 로 초를 추정해 rep(18fps) ↔
    video(9fps) 불일치를 그대로 먹었다. 백엔드가 보정분을 방출하면 그 오독이 사라진다.
    """
    frames_u = _frames(n=9)
    frames_r = _frames(n=20)
    u = _report(9, 9.0, {"left_knee": (0.375, 0.5)}, {"left_knee": 0.9})
    # ref rep = 18fps / 40프레임 → rep9_n = 20 → 배율 1.0 (identity) 검증용 형상.
    r = _report(40, 18.0, {"left_knee": (0.625, 0.5)}, {"left_knee": 0.9})
    comps = fz.build_fault_zoom_comparisons(
        frames_u, frames_r, u, r,
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
        dtw_match=_Match(start=0, path=[(i, i * 2) for i in range(9)]),
    )
    assert len(comps) == 1
    item = comps[0]
    expected_display = fz.ref_display_frame_index(
        int(round(8 * 9.0 / 18.0)), 20, 40, 18.0, 9.0
    )
    assert abs(item["refVideoSec"] - expected_display / 9.0) < 1e-9
