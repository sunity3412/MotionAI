"""33-12 (A-5) — 확대비교 criterion-keyed 방출 joint-exact 단위테스트.

seam #1 (33-A3-ZOOM-DESIGN §4 확정 — 재론 금지): crop 생성 입력을
visionVeto.faultJoints 단독(+advisory top-2)에서 **deductionBreakdown.records[]
(화면에 실제 표시되는 항목)가 가리키는 관절 집합**으로 전환하고, 각 item 에
자기 record 를 식별하는 `criterion` scalar 를 실어 앱 join 을 first-match 추측에서
키 일치로 바꾼다. 다리 스플릿 항목에 어깨 crop 이 붙는 defect #5 의 근본 수리 (D-12).

D-18 — 자동화 불가분 명시 (앱 측 반쪽):
  앱 join(result.tsx selectedZoom / deductionLabels.ts)은 JS 테스트 러너가 없어
  (프로젝트 정적 게이트 = `tsc --noEmit` 단독) 여기서 자동 검증 불가. 대체 증명 =
  app `npm run typecheck` + 33-16 페이즈 게이트의 D-19 재분석분 PNG/실기기 전수
  열람. 백엔드 측 반쪽(item 이 올바른 관절·criterion 을 나른다 + 불일치 카드
  미방출)은 본 파일이 assert 한다.

defect #6 (각도 숫자 베이크) — RED 아님, 회귀 핀 (T-33-47):
  `_mark` 각도 배지·`_draw_leg_angle` 수치 라벨은 faultzoom debug 에서 이미 제거됨
  (commit 79221f0, belle 2026-07-28 "각도 배지는 빼고 초 표기로"). 33-12-PLAN 은
  debug 랜딩 전에 작성돼 이 부분이 RED 대상으로 기술됐으나 코드 실상은 이미 GREEN —
  본 파일은 이를 **회귀 핀**으로 박제한다: 크롭 PNG 에 타임스탬프("N.Ns") 외의
  텍스트(각도 숫자 등)가 다시 그려지면 즉시 실패한다. 수치의 단일 거처 = 점수
  내역 (D-16).

순수 — PIL/numpy 외 의존 0 (S3/네트워크/firestore import 금지).
합성 fixture 는 tests/phase32/test_fault_zoom_crop_parity.py:24-55 골격 복제.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

from sunity_shared.analysis import fault_zoom as fz


# ─────────── 합성 fixture (phase32 parity 골격) ───────────


@dataclass
class _Match:
    start: int
    path: list


_IDENTITY9 = _Match(start=0, path=[(i, i) for i in range(9)])


def _frames(n: int = 9, h: int = 400, w: int = 400) -> np.ndarray:
    """위치-인코딩 gradient 프레임 (red=x, green=y) — crop 출처 픽셀 검증용."""
    a = np.zeros((n, h, w, 3), dtype=np.uint8)
    a[:, :, :, 0] = np.linspace(0, 255, w).astype(np.uint8)[None, None, :]
    a[:, :, :, 1] = np.linspace(0, 255, h).astype(np.uint8)[None, :, None]
    return a


def _report(n: int, fps: float, joint_xy, joint_conf) -> dict:
    """per-joint 위치/confidence 지정 합성 keypointReport."""
    joints = list(joint_xy)
    data: list[float] = []
    for _f in range(n):
        for j in joints:
            data += list(joint_xy[j])
    conf: list[float] = []
    for _f in range(n):
        for j in joints:
            conf.append(joint_conf.get(j, 0.9))
    return {"joints": joints, "frames": n, "fps": fps, "data": data, "confidence": conf}


# kismam angle key → keypoint 매핑 스텁 — pipeline._KISMAM_TO_KEYPOINT 미러
# (fault_zoom 은 이름공간 무지 유지 — 매핑은 호출측 소유라 인자로 주입).
# 33-G S9 (quick-260730-l7t): elbow → 동명 관절. hand 인접 매핑은 belle #7·#9
# "팔꿈치인데 손을 집고 있음"의 원인이라 제거됐다. drift 게이트 =
# tests/phase33/test_reference_anchors.py::test_test_stub_mirror_matches_pipeline_map.
_ANGLE_MAP = {
    "left_elbow": "left_elbow",
    "right_elbow": "right_elbow",
    "left_shoulder": "left_shoulder",
    "right_shoulder": "right_shoulder",
    "left_hip": "left_hip",
    "right_hip": "right_hip",
    "left_knee": "left_knee",
    "right_knee": "right_knee",
}

_LEGS = {"left_hip", "right_hip", "left_knee", "right_knee"}


def _rec(criterion: str, source: str = "geometry", unit: str = "deg") -> dict:
    """감점 record 스텁 — unit 파생엔 criterion/source/unit 만 유의미."""
    return {
        "criterion": criterion,
        "measuredValue": 100.0,
        "baselineValue": 180.0,
        "deviation": 80.0,
        "ruleId": "r",
        "points": -10.0,
        "unit": unit,
        "ipsfAnchor": "t",
        "source": source,
        "deviationSource": "ipsf_absolute",
    }


# ─────────── Test 1 — record → criterion unit 투영이 joint-exact ───────────


def test_criterion_units_from_records_joint_exact():
    """record 가 가리키는 관절만 unit 이 된다 — 다리 항목에 어깨 없음 (defect #5).

    투영 규칙 = 앱 projectDeductionRecordKeypoints 백엔드 미러 + A-3 vision 좁힘:
      a_v_r__{jk} → 단일 관절 / vision → faultJoints ∩ criterion 부위(전체 투영 금지)
      / ipsf geometry → region 멤버 / line·fallback → 미생성.
    """
    records = [
        _rec("angle_vs_reference__left_knee"),
        _rec("split_angle", source="vision"),
        _rec("leg_extension"),
        _rec("line"),
        _rec("dimension_overall_fallback", unit="score_delta"),
        _rec("split_angle", source="vision"),  # 중복 criterion → dedupe
    ]
    fault_joints = [
        "left_knee", "right_knee", "left_hip", "right_hip",
        "left_shoulder", "right_shoulder",  # vision 전체 투영이면 이게 새어 들어감
    ]
    units = fz.criterion_units_from_records(records, fault_joints, _ANGLE_MAP)
    by_crit = {u["criterion"]: u for u in units}

    # a_v_r__left_knee → 단일 관절 (인접 관절 대체 금지).
    assert tuple(by_crit["angle_vs_reference__left_knee"]["joints"]) == ("left_knee",)

    # vision split_angle → faultJoints ∩ legs — 어깨 배제 (defect #5 근본 assert).
    split_joints = set(by_crit["split_angle"]["joints"])
    assert split_joints == _LEGS & set(fault_joints)
    assert not any("shoulder" in j for j in split_joints), (
        "다리 스플릿 항목에 어깨 관절이 투영됨 — vision 전체 투영 금지 (A-3/D-12)"
    )
    assert by_crit["split_angle"]["region"] == "legs"

    # geometry leg_extension → legs region 멤버 (8-kp 이름공간 미러).
    assert set(by_crit["leg_extension"]["joints"]) == _LEGS

    # line / dimension_overall_fallback → 미생성 (앱 무투영 결정 미러).
    assert "line" not in by_crit
    assert "dimension_overall_fallback" not in by_crit

    # 중복 criterion 은 첫 record 승 (S3 키·join 키 유일성).
    assert len([u for u in units if u["criterion"] == "split_angle"]) == 1


# ─────────── Test 2 — 방출 item 이 criterion 을 나른다 (키 일치 join 재료) ─────


def test_build_emits_criterion_keyed_item():
    """criterion_units 경로의 item 은 자기 criterion scalar 를 나른다 (scalar-only)."""
    frames = _frames()
    user_rep = _report(9, 9.0, {"left_knee": (0.375, 0.5)}, {"left_knee": 0.9})
    ref_rep = _report(9, 9.0, {"left_knee": (0.625, 0.5)}, {"left_knee": 0.9})
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep,
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
        dtw_match=_IDENTITY9,
        criterion_units=[{
            "criterion": "angle_vs_reference__left_knee",
            "joints": ("left_knee",),
            "region": None,
        }],
    )
    assert len(comps) == 1
    item = comps[0]
    assert item["criterion"] == "angle_vs_reference__left_knee"
    assert item["joint"] == "left_knee"
    # Firestore flat 제약 — png(bytes) 외 값은 전부 scalar.
    for k, v in item.items():
        if k == "png":
            continue
        assert v is None or isinstance(v, (str, int, float, bool)), (
            f"non-scalar item field {k}={type(v)}"
        )


# ─────────── Test 3 — 같은 순간·같은 배율 불가 카드는 미방출 (D-12) ───────────


def test_mismatched_pair_dropped_criterion_path():
    """criterion 경로: ref 좌표 결측(full 폴백)·DTW 대응 실패 → 카드 drop (D-12).

    legacy(criterion 미지정) 경로는 D-04 정직 폴백(refMatch='failed'/전신)을
    byte-보존한다 — 기존 doc·advisory 렌더 무회귀 (test_fault_zoom_ref_match 박제).
    """
    frames = _frames()
    user_rep = _report(9, 9.0, {"left_knee": (0.375, 0.5)}, {"left_knee": 0.9})
    # ref 좌표 전부 NaN — _side_crop 3단 강하의 full 폴백 대상.
    ref_nan = _report(
        9, 9.0, {"left_knee": (float("nan"), float("nan"))}, {"left_knee": 0.9}
    )
    unit = [{
        "criterion": "angle_vs_reference__left_knee",
        "joints": ("left_knee",),
        "region": None,
    }]
    common = dict(
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
    )

    # (a) ref full 폴백 = 같은 배율 불가 → drop.
    dropped_scale = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_nan,
        dtw_match=_IDENTITY9, criterion_units=unit, **common,
    )
    assert dropped_scale == [], "ref full 폴백 카드가 방출됨 — D-12 같은 배율 위반"

    # (b) DTW 대응 실패 = 같은 순간 불가 → drop.
    ref_ok = _report(9, 9.0, {"left_knee": (0.625, 0.5)}, {"left_knee": 0.9})
    dropped_moment = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_ok,
        dtw_match=None, criterion_units=unit, **common,
    )
    assert dropped_moment == [], "ref 대응 실패 카드가 방출됨 — D-12 같은 순간 위반"

    # (c) legacy 경로 무회귀 — 동일 입력에서 정직 폴백 유지 (refMatch='failed').
    legacy = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_ok,
        dtw_match=None, **common,
    )
    assert len(legacy) == 1 and legacy[0]["refMatch"] == "failed"


# ─────────── Test 4 — 기준(정은지) 측도 그려진다 (defect #1, 같은 표시) ─────────


def test_ref_side_marked_criterion_path():
    """criterion 경로 valid 쌍: 합성 PNG 오른쪽(기준) 절반에도 브랜드 마커 존재."""
    frames = _frames()
    user_rep = _report(9, 9.0, {"left_knee": (0.375, 0.5)}, {"left_knee": 0.9})
    ref_rep = _report(9, 9.0, {"left_knee": (0.625, 0.5)}, {"left_knee": 0.9})
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep,
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
        dtw_match=_IDENTITY9,
        criterion_units=[{
            "criterion": "angle_vs_reference__left_knee",
            "joints": ("left_knee",),
            "region": None,
        }],
    )
    assert len(comps) == 1
    img = np.asarray(Image.open(io.BytesIO(comps[0]["png"])).convert("RGB"))
    # _compose 좌우 배치: [user 0..360 | gap 6 | ref 366..726].
    right = img[:, 366:, :]
    brand = np.array([255, 75, 51])
    hit = (np.abs(right.astype(int) - brand[None, None, :]).sum(axis=2) < 30).any()
    assert hit, "기준(정은지) 패널에 마커가 없음 — defect #1 (D-12 같은 표시)"


# ─────────── Test 5 — 각도 숫자 미베이크 회귀 핀 (defect #6, T-33-47) ───────────


_TS_RE = re.compile(r"^\d+(\.\d)?s$")


def test_no_angle_number_baked_regression_pin(monkeypatch):
    """크롭 PNG 의 텍스트 = 타임스탬프("N.Ns")뿐 — 각도 숫자 재등장 시 실패.

    legs 스플릿 카드(선+호 경로)를 실제로 그리면서 ImageDraw.text 호출 전수를
    스파이한다. 각도 배지("40")·호 옆 수치("130") 등 타임스탬프 패턴 밖의 텍스트가
    하나라도 그려지면 회귀 (D-16 — 수치의 단일 거처는 점수 내역). 선/호(같은 표시
    기하)는 유지돼야 한다.
    """
    texts: list[str] = []
    arcs: list[tuple] = []
    lines: list[tuple] = []
    orig_text = ImageDraw.ImageDraw.text
    orig_arc = ImageDraw.ImageDraw.arc
    orig_line = ImageDraw.ImageDraw.line

    def spy_text(self, xy, text, *a, **k):
        texts.append(str(text))
        return orig_text(self, xy, text, *a, **k)

    def spy_arc(self, *a, **k):
        arcs.append(a)
        return orig_arc(self, *a, **k)

    def spy_line(self, *a, **k):
        lines.append(a)
        return orig_line(self, *a, **k)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy_text)
    monkeypatch.setattr(ImageDraw.ImageDraw, "arc", spy_arc)
    monkeypatch.setattr(ImageDraw.ImageDraw, "line", spy_line)

    frames = _frames()
    legs_xy = {
        "left_hip": (0.42, 0.35), "right_hip": (0.58, 0.35),
        "left_knee": (0.30, 0.72), "right_knee": (0.70, 0.72),
    }
    conf = {j: 0.9 for j in legs_xy}
    user_rep = _report(9, 9.0, legs_xy, conf)
    ref_rep = _report(9, 9.0, legs_xy, conf)
    fault_joints = list(legs_xy)
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep,
        worst_seconds=0.5, fault_joints=fault_joints,
        joint_deltas={"left_knee": 40.0}, frames_fps=9.0,
        joint_kinds={j: "deficit" for j in fault_joints},
        dtw_match=_IDENTITY9,
        split_angle_present=True,
    )
    assert len(comps) == 1
    offenders = [t for t in texts if not _TS_RE.match(t)]
    assert offenders == [], (
        f"크롭에 타임스탬프 외 텍스트가 베이크됨(각도 숫자 회귀): {offenders}"
    )
    # 같은 표시 기하(선/호)는 유지 — 숫자만 없는 것이지 시각 언어가 사라지면 안 됨.
    assert lines, "다리 사이각 선이 그려지지 않음 (기하 유지 실패)"
    assert arcs, "다리 사이각 호가 그려지지 않음 (기하 유지 실패)"


# ─────────── Test 6 — 회전류 기준측 실영상 초 표기 (6R 규칙 3, stamp_ref) ────────


def test_ref_timestamp_stamped_when_stamp_ref(monkeypatch):
    """stamp_ref=True → 기준 패널에도 타임스탬프 배지 (회전류 비교쌍, 6R amendment).

    회전류 판정은 호출측(pipeline)이 technique category 데이터로 키잉 — 렌더러는
    bool 만 받는다 (동작명 하드코딩 금지, 이름공간 무지 유지).
    """
    texts: list[str] = []
    orig_text = ImageDraw.ImageDraw.text

    def spy_text(self, xy, text, *a, **k):
        texts.append(str(text))
        return orig_text(self, xy, text, *a, **k)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy_text)

    frames = _frames()
    user_rep = _report(9, 9.0, {"left_knee": (0.375, 0.5)}, {"left_knee": 0.9})
    ref_rep = _report(9, 9.0, {"left_knee": (0.625, 0.5)}, {"left_knee": 0.9})
    common = dict(
        worst_seconds=0.5, fault_joints=["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
        dtw_match=_IDENTITY9,
    )
    comps = fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep, stamp_ref=True, **common,
    )
    assert len(comps) == 1
    stamps = [t for t in texts if _TS_RE.match(t)]
    assert len(stamps) == 2, (
        f"stamp_ref=True 인데 타임스탬프 {len(stamps)}개 — 기준측 초 미표기"
    )

    texts.clear()
    fz.build_fault_zoom_comparisons(
        frames, frames, user_rep, ref_rep, **common,
    )
    stamps_off = [t for t in texts if _TS_RE.match(t)]
    assert len(stamps_off) == 1, "stamp_ref 기본값(False)에서 학생 패널 단독 표기 회귀"
