"""quick-260802-tie Task 2 — 기준(정은지) 패널에 표시가 없으면 그렇다고 말한다.

문제: 확대비교 카드의 기준 패널에 오버레이가 하나도 없는데 아무 말 없이 나갔다.
원인은 신뢰도/crop 게이트가 fail-closed 로 닫힌 **정상 동작**이지만, 비교 카드인데
비교 대상 표시가 없는 채로 침묵하는 것은 틀린 출력이다.

여기서 잠그는 것:
  ① `refMarked` 는 **그리는 코드가 인증**한다 — 원·사이각·각도 세 경로 각각.
  ② 게이트가 닫히면 false 로 방출한다(카드는 그대로 나간다 — 정보 보존).
  ③ criterion 없는 카드(legacy/advisory)에는 키 자체가 없다 — 게이트가 아니라
     정책(게이트 B)으로 무마킹인 카드에 "게이트가 닫혔다"를 말하지 않는다.
  ④ `_KP_CONF_MIN` 은 읽지도 바꾸지도 않는다.

전부 합성 keypoint report + 프로덕션 함수 직접 호출 — GPU/S3/네트워크 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

# **일부러 프로덕션 기본 fps 가 아닌 값** (record-moment 테스트 선례).
_FPS = 12.0
_N = 24
_SIZE = 96

# 12관절 report — 어깨 각도 베이크(elbow/hip 필요)까지 성립하는 좌표.
_KP = {
    "left_shoulder": (0.564, 0.397), "right_shoulder": (0.612, 0.372),
    "left_hip": (0.505, 0.475), "right_hip": (0.548, 0.462),
    "left_knee": (0.402, 0.628), "right_knee": (0.612, 0.652),
    "left_hand": (0.470, 0.196), "right_hand": (0.628, 0.184),
    "left_ankle": (0.386, 0.792), "right_ankle": (0.640, 0.804),
    "left_elbow": (0.498, 0.288), "right_elbow": (0.640, 0.272),
}


class _Match:
    def __init__(self, start, path):
        self.start = start
        self.path = path


def _identity(n=_N):
    return _Match(0, [(i, i) for i in range(n)])


def _report(xy=None, conf=0.9, joints=None):
    xy = xy or _KP
    names = list(joints) if joints is not None else list(xy)
    data: list[float] = []
    confs: list[float] = []
    for _f in range(_N):
        for j in names:
            data += list(xy[j])
            confs.append(float(conf))
    return {"joints": names, "frames": _N, "fps": _FPS,
            "data": data, "confidence": confs}


def _frames():
    base = np.full((_N, _SIZE, _SIZE, 3), 120, dtype=np.uint8)
    for f in range(_N):
        base[f, 0, 0, :] = np.uint8((f * 11) % 256)
    return base


def _build(units, ref_rep=None, user_rep=None, **kw):
    joints: list[str] = []
    for u in units or ():
        for j in u["joints"]:
            if j not in joints:
                joints.append(j)
    if not joints:
        joints = list(kw.pop("fault_joints", ["left_knee", "right_knee"]))
    return fz.build_fault_zoom_comparisons(
        _frames(), _frames(),
        user_rep or _report(), ref_rep or _report(),
        worst_seconds=1.0,
        fault_joints=joints,
        joint_deltas={j: 20.0 for j in joints},
        frames_fps=_FPS,
        joint_kinds={j: "deficit" for j in joints},
        dtw_match=_identity(),
        criterion_units=units,
        user_frame_candidates=[8, 9, 10, 11, 12],
        ref_frame_candidates=[8, 9, 10, 11, 12],
        analysis_id="t",
        **kw,
    )


def _unit(criterion, joints, region=None):
    return {"criterion": criterion, "joints": tuple(joints),
            "region": region, "at_frame_idx": None}


# ── ① 인증 — 세 드로잉 경로 각각이 스스로 인증한다 ──────────────────────────
#
# 세 케이스가 **서로 다른 경로**를 타는지는 드로잉 함수를 감싸 확인했다(아래 각
# 테스트가 그 경로만 발화하도록 입력을 고른다). 같은 True 를 세 번 확인하는 것이
# 아니라, 인증이 세 곳 전부에 배선됐는지를 본다.


def test_circle_marker_certifies_ref_marked():
    """각도 대상이 아닌 다관절 카드 → 원 마커만 → refMarked=true.

    `leg_extension`(무릎 2개)은 꼭짓점이 성립하지 않아(`_criterion_vertex_joint`
    가 단일 관절만 인정) 각도 베이크가 `unmapped` 로 빠지고, `split_angle_present`
    가 False 라 사이각도 안 그린다 — 남는 인증 경로가 원 마커뿐이다.
    """
    items = _build([
        _unit("leg_extension", ["left_knee", "right_knee"], region="legs"),
    ])
    assert items, "카드가 나오지 않으면 이 게이트는 성립하지 않는다"
    assert items[0]["refMarked"] is True


def test_low_confidence_reference_yields_ref_marked_false():
    """기준 keypoint 가 저신뢰(relaxed) → 원 생략 → refMarked=false.

    카드는 **그대로 방출된다** — 사진은 여전히 정보다(숨기지 않는다).
    """
    items = _build(
        [_unit("angle_vs_reference__left_hip", ["left_hip"])],
        ref_rep=_report(conf=0.2),
    )
    assert items, "저신뢰라고 카드를 떨구면 정보 보존 원칙이 깨진다"
    assert items[0]["refMarked"] is False
    # 게이트가 닫혔을 뿐 프레임 대응은 성립했다 — 두 사실은 다르다.
    assert items[0]["refMatched"] is True
    assert items[0]["refMatch"] == "dtw"


def test_angle_bake_certifies_ref_marked(monkeypatch):
    """양측 각도 베이크가 성립한 카드도 기준 패널에 그린 것 — true.

    이 카드는 **원 마커 경로로 인증되지 않는다**(각도를 그리면 원을 생략한다).
    그래서 기준측 드로잉 호출을 세어 각도 경로가 실제로 발화했음을 함께 잠근다 —
    같은 True 를 다른 이유로 얻는 것을 막는다.
    """
    drawn = []
    orig = fz._draw_side_joint_angle
    monkeypatch.setattr(
        fz, "_draw_side_joint_angle",
        lambda *a, **k: (lambda r: (drawn.append(bool(r)), r)[1])(orig(*a, **k)),
    )
    items = _build([
        _unit("angle_vs_reference__left_shoulder", ["left_shoulder"]),
    ])
    assert items
    assert items[0]["refMarked"] is True
    assert drawn == [True, True], "학생·기준 양측 각도 베이크가 발화해야 한다"


def test_legs_split_arc_certifies_ref_marked(monkeypatch):
    """legs 사이각(both-or-neither)이 그려진 카드도 true — 사이각 경로로 인증."""
    drawn = []
    orig = fz._draw_side_leg_angle
    monkeypatch.setattr(
        fz, "_draw_side_leg_angle",
        lambda *a, **k: (lambda r: (drawn.append(bool(r)), r)[1])(orig(*a, **k)),
    )
    items = _build(
        [_unit("split_angle", ["left_knee", "right_knee"], region="legs")],
        split_angle_present=True,
    )
    assert items
    assert items[0]["refMarked"] is True
    assert drawn == [True, True], "기준·학생 양측 사이각이 발화해야 한다"


# ── ③ 방출 범위 — criterion 없는 카드에는 키 자체가 없다 ────────────────────


def test_legacy_cards_have_no_ref_marked_key():
    """legacy(criterion 부재) 카드는 게이트 B 로 기준측 무마킹이 **정책**이다.

    false 를 실으면 앱이 "관절 위치를 확인하지 못했다"는 없는 이유를 말하게 된다.
    """
    items = _build(None, fault_joints=["left_hip"])
    assert items
    for it in items:
        assert "criterion" not in it
        assert "refMarked" not in it


# ── ④ 게이트 무접촉 + 하위호환 ──────────────────────────────────────────────


def test_kp_conf_min_unchanged():
    """이 사이클은 게이트를 여는 것이 아니라 게이트가 닫혔음을 말하는 것이다."""
    assert fz._KP_CONF_MIN == 0.5


def test_ref_marked_is_a_flat_bool_scalar():
    """Firestore flat 제약 — dict/list 금지, bool scalar 만."""
    items = _build([_unit("angle_vs_reference__left_hip", ["left_hip"])])
    assert isinstance(items[0]["refMarked"], bool)


def test_ref_marked_does_not_change_other_fields():
    """기존 방출 필드는 그대로 — 추가만 한다(additive)."""
    items = _build([_unit("angle_vs_reference__left_hip", ["left_hip"])])
    it = items[0]
    for k in ("joint", "png", "userFrameIdx", "refFrameIdx", "refMatched",
              "refMatch", "criterion"):
        assert k in it, k


# ── 매퍼 화이트리스트 — 여기 없으면 앱이 인증을 영영 못 본다 ────────────────
#
# quick-260801-gbk Deviation 3 이 정확히 이 자리에서 데였다(`atMatched` 누락 →
# no-op 출하). `refMatched` 선례를 따라 **False 도** 통과해야 한다 — 앱이 알려야
# 하는 값이 바로 False 쪽이다.


def _load_pipeline_app():
    _PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
    if str(_PIPELINE) not in sys.path:
        sys.path.insert(0, str(_PIPELINE))
    import app  # noqa: WPS433

    return app


def _patch_render_deps(app, monkeypatch, cards):
    """`_render_fault_zoom` 의 추출기/S3/build 를 스텁 — 매퍼 로직만 노출.

    (test_fault_zoom_ref_match.py 의 같은 하네스 형식 — 매퍼 단위 대조용.)
    """
    import types

    from sunity_shared.analysis import fault_zoom as fzmod

    class _FakeExt:
        def __init__(self, *a, **k) -> None:
            pass

        def extract(self, _path):
            return np.zeros((3, 8, 8, 3), dtype=np.uint8)

    fake_fe = types.ModuleType("sunity_shared.analysis.frame_extractor")
    fake_fe.FfmpegFrameExtractor = _FakeExt
    monkeypatch.setitem(
        sys.modules, "sunity_shared.analysis.frame_extractor", fake_fe
    )
    monkeypatch.setattr(fzmod, "build_fault_zoom_comparisons", lambda *a, **k: cards)

    class _FakeS3:
        def put_object(self, **k):
            return None

    monkeypatch.setattr(app, "_s3", _FakeS3())
    monkeypatch.setattr(app, "_signed_get", lambda b, k: "https://signed")


def _run_render(app):
    return app._render_fault_zoom(
        {}, "u.mp4", "r.mp4", {"joints": []}, {"joints": []},
        ["left_knee"], {"left_knee": 20.0}, {}, 0.5, "u1", "a1", "bucket",
    )


def _mapper_out(monkeypatch, card_extra):
    app = _load_pipeline_app()
    _patch_render_deps(app, monkeypatch, [
        {"joint": "left_knee", "deficitDeg": 20.0, "png": b"\x89PNG",
         **card_extra},
    ])
    return _run_render(app)[0]


def test_mapper_preserves_ref_marked_false(monkeypatch):
    """False 가 매퍼를 통과해야 앱이 문구를 낼 수 있다."""
    assert _mapper_out(monkeypatch, {"refMarked": False})["refMarked"] is False


def test_mapper_preserves_ref_marked_true(monkeypatch):
    assert _mapper_out(monkeypatch, {"refMarked": True})["refMarked"] is True


def test_mapper_omits_ref_marked_for_legacy_card(monkeypatch):
    """키 없는 legacy 형상 → 최종 item 에도 키 부재 (refMatch 선례 동일 조건부)."""
    assert "refMarked" not in _mapper_out(monkeypatch, {})


def test_mapper_rejects_non_bool_ref_marked(monkeypatch):
    """bool 이 아닌 값은 통과시키지 않는다 — 앱은 boolean 만 계약한다."""
    assert "refMarked" not in _mapper_out(monkeypatch, {"refMarked": "false"})
    assert "refMarked" not in _mapper_out(monkeypatch, {"refMarked": 0})


# ── 3-way lockstep — TS ↔ contract ↔ Python 방출부 ──────────────────────────


def test_ref_marked_three_way_lockstep():
    """계약 한쪽만 고치는 것을 막는다 (`refMatch`/`criterion`/`atMatched` 선례)."""
    repo = Path(__file__).resolve().parents[2]
    ts = (repo / "app" / "src" / "types" / "analysis.ts").read_text(
        encoding="utf-8"
    )
    import re

    m = re.search(r"export interface FaultZoomComparison \{(.*?)\n\}", ts, re.S)
    assert m, "FaultZoomComparison interface 부재"
    assert "refMarked?: boolean;" in m.group(1)

    contract = (repo / "docs" / "contract.md").read_text(encoding="utf-8")
    assert "§11.9 FaultZoomComparison.refMarked" in contract

    mapper = (
        repo / "backend" / "functions" / "pipeline" / "app.py"
    ).read_text(encoding="utf-8")
    assert 'item["refMarked"] = c["refMarked"]' in mapper
