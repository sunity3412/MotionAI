"""quick-260919-oxg — 각도 표시의 두 번째 축: 시간축 안정성. 문턱은 그대로 둔다.

belle 2026-09-19 지시:
  "분석의 정도를 높여서 왠만하면 다 찾아내야지. 앱에 이미 있는 것과 부딪히면
   뭐가 맞는지 둘 다 맞는지를 판단하는 것도 분석이야."

즉 (a) 표시가 침묵하는 것을 줄여라, (b) 충돌 판정은 재서 답을 내라.

**왜 문턱(`_KP_CONF_MIN` 0.5)을 안 내리나 — 2026-09-19 라이브 실측.**
  실측 1 (`card_moment_conf.py`, 각도 대상 카드 109장): 현행 0.5 로 3점 전부
  통과한 카드가 55/109(50%). 막힌 54장의 병목은 **이웃(방향) 관절 44장 :
  꼭짓점 10장** — 짚으려는 관절이 아니라 보조점이 막는다.
  실측 2 (`conf_vs_accuracy.py`, doc 25건 / 표본 1.5만, joints3d 공간):
      0.45-0.50 중앙값 6.23도  (버려진다)
      0.50-0.60 중앙값 5.06도  (통과한다)
  **문턱 바로 위아래가 사실상 같은 품질이다.** 0.5 는 좋은 좌표와 나쁜 좌표를
  가르지 않는 선이고, 신뢰도가 실제로 품질을 예측하는 것은 0.6 위부터다.
  그래서 문턱을 내리는 대신 **실제로 재는 축**을 하나 더 세운다:
      conf >= _KP_CONF_MIN  OR  (conf >= _ANGLE_DIR_CONF_MIN AND 시간축 안정)

**판정 1 — 꼭짓점은 완화하지 않는다.** 크롭 중심의 단일 출처가
`criterion_vertex_xy` 라, 꼭짓점을 완화하면 V 의 꼭짓점이 패널 정중앙이 아니게
되어 belle 승인 문법 4R#1("꼭짓점 = 패널 정중앙")이 깨진다. 방향 2점만 연다.
근거는 위 44:10 — 승인 문법을 안 깨고 막힌 것의 81% 를 연다.
어깨 계열은 `{side}_hip` 이 **꼭짓점 내분점과 몸통 방향점에 동시에** 쓰이므로
관절명으로는 두 역할을 가를 수 없다 → 해상기를 **역할로** 가른다(⑥ 이 잠근다).

**임계 유도** = `260919-oxg-CALIBRATION.md`. 코드가 실제로 쓸 **정규화 좌표 3점
사이각** 공간에서 다시 재서 `0.50-0.60` 행(= 지금 실제로 통과하고 있는 밴드)의
`p75` 칸을 읽었다. 실측 2 의 도(度) 값(joints3d 공간)을 그대로 옮기지 않은 이유는
두 공간의 도 값이 같은 수가 아니기 때문이다.

**이 축이 증명하지 못하는 것 (과장 금지):** 시간축 안정성은 좌표가 **튀는** 것을
잡지 **일관되게 틀린** 것은 못 잡는다. 매끄럽게 틀린 팔은 매끄럽게 통과한다
(keypoints-are-wrong-not-the-frame-choice). 새로 열린 카드의 V 가 실제로 옳은
부위에 앉았는지는 완성된 사진을 belle 눈으로 봐야 닫힌다.

여기서 잠그는 것 (①~⑧ = 순수 단위, ⑨~⑮ = 배선):
  ① 엄격 경로 무간섭 — `direction_resolver` 기본값이 기존 동작 그대로다.
  ② 완화 + 안정 → 3점 스펙이 나온다.
  ③ 완화 + 불안정 → None (원 마커 폴백).
  ④ 하한(`_ANGLE_DIR_CONF_MIN`) 미달 → 안정해도 None.
  ⑤ conf 부재(legacy report) → 안정해도 None.
  ⑥ 꼭짓점은 안 열린다 (판정 1) — 어깨 계열 `{side}_hip` 함정 포함.
  ⑦ 이웃 표본 부족 / fps 부재 → None (fail-closed).
  ⑧ 임계 경계 — 바로 아래는 성립, 바로 위는 None.
  ⑨ ★ additive 불변식 — 완화 경로가 불가능한 배치는 `angle_bake=drawn`(접미사 없음).
  ⑩ 새로 열린다 — `angle_bake=drawn:stable(...)` + 학생 패널 브랜드 픽셀 > 0.
  ⑪ 양측 대칭 — 기준 패널도 함께 산다(both-or-neither 무손상).
  ⑫ 불안정은 계속 침묵 — `omitted:user_gate` + 원 마커 폴백.
  ⑬ 장수 불변 (belle 규칙 1 — 게이트는 사진을 못 없앤다).
  ⑭ `pngPlain` 무접촉 — 어느 배치에서도 표시 픽셀 0.
  ⑮ ★ 크롭 무변경 자물쇠 — 완화 배치(0.42)와 **하한 미달 배치(0.30)** 의
     `pngPlain` 이 바이트 동일하다. `build_angle_bake_spec` 은 크롭 **치수**를
     정하는 자리(`:3529-3545`)에서도 불린다. 거기까지 완화하면 지금 나가는
     사진의 크롭이 바뀐다 = 순수 additive 파괴.
     0.30 배치는 새 하한 미달이라 이 변경이 **원리적으로 못 건드리는** 대조군이고,
     오늘 두 배치는 둘 다 "스펙 미성립 → `_CRITERION_CROP_FRAC_MAX`" 크롭을 받는다
     (변경 전 실측: 두 pngPlain sha256 동일, 엄격 0.9 배치와는 불일치).
     완화 해상기가 `:3529` 로 새면 0.42 배치만 좁은 크롭으로 옮겨가 **여기서 갈린다**.
  ⑯ 하한 미달 배치는 사진까지 종전 그대로 — "잴 자격이 없어 시도조차 안 함" 칸.

fixture 는 tests/test_fault_zoom_suppress_keeps_angle.py(`_Match`/`_identity`/
`_frames`/`_unit`/`_build`/`_brand_px_*`) 와 tests/test_fault_zoom_display_repair.py
(`_report_conf` 관절별 conf override) 를 **복제** — 테스트 모듈 간 import 금지 관행.
전부 합성 keypoint report + 프로덕션 함수 직접 호출 — GPU/S3/네트워크/눈 0.
"""

from __future__ import annotations

import io
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

_FPS = 12.0
_N = 24
_SIZE = 96
_MID = 10          # 측정 프레임 — 창(±3 at 12fps)이 양쪽으로 다 들어온다

# 각도를 **극좌표로 심는다** — 정규화 공간 사이각이 곧 두 방위각의 차라서
# "편차 N도"를 입력으로 직접 만들 수 있다(임계 경계 시험 ⑧ 의 전제).
_V = (0.5, 0.5)
_R = 0.2


def _polar(deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    return (_V[0] + _R * math.cos(a), _V[1] + _R * math.sin(a))


# 무릎 계열: 꼭짓점 = right_knee(관절 좌표 그대로), 방향 = right_ankle / right_hip.
# 사이각 90도 (ankle 방위 0도, hip 방위 90도).
_KNEE_CRIT = "angle_vs_reference__right_knee"
_KNEE_MEMBERS = ("right_knee",)

# 어깨 계열: 꼭짓점 = 겨드랑이 내분점(left_shoulder→left_hip, t=_ARMPIT_T),
# 방향 = left_elbow / **left_hip**. left_hip 이 두 역할에 동시에 쓰인다(⑥ 함정).
_SHOULDER_CRIT = "angle_vs_reference__left_shoulder"
_SHOULDER_MEMBERS = ("left_shoulder",)

_BASE_KP = {
    "right_knee": _V,
    "right_ankle": _polar(0.0),
    "right_hip": _polar(90.0),
    "left_shoulder": (0.30, 0.30),
    "left_hip": (0.30, 0.55),
    "left_elbow": (0.20, 0.42),
}


def _report(conf_by_joint=None, *, frames=_N, fps=_FPS,
            xy_by_frame=None, with_conf=True, xy=None):
    """합성 keypointReport. conf/좌표를 관절별·프레임별로 심을 수 있다.

    `conf_by_joint` = {관절: conf} (기본 0.9). `xy_by_frame` = {프레임: {관절: xy}}
    override. `with_conf=False` 는 legacy(confidence 키 없음) report.
    """
    xy = xy or _BASE_KP
    joints = list(xy)
    data: list[float] = []
    conf: list[float] = []
    for f in range(frames):
        over = (xy_by_frame or {}).get(f, {})
        for j in joints:
            p = over.get(j, xy[j])
            data += [float(p[0]), float(p[1])]
            conf.append(float((conf_by_joint or {}).get(j, 0.9)))
    rep = {"joints": joints, "frames": frames, "fps": fps, "data": data}
    if with_conf:
        rep["confidence"] = conf
    return rep


def _stable(report, criterion=_KNEE_CRIT, members=_KNEE_MEMBERS, idx=_MID):
    return fz.build_stable_angle_bake_spec(
        criterion, members, report, idx,
        vertex_resolver=fz._gated_kp,  # noqa: SLF001
        direction_resolver=fz._relaxed_dir_kp,  # noqa: SLF001
    )


# ── ① 엄격 경로 무간섭 ────────────────────────────────────────────────────────


def test_direction_resolver_default_is_existing_behaviour():
    """인자를 더해도 기존 호출의 산출이 한 점도 안 움직인다.

    순수 additive 의 첫 자물쇠 — 완화 해상기를 **명시로 주입해도** 전원 고신뢰
    배치에서는 기존 산출과 완전히 같아야 한다(완화는 저신뢰에서만 일한다).
    """
    rep = _report()
    base = fz.build_angle_bake_spec(
        _KNEE_CRIT, _KNEE_MEMBERS, rep, _MID, fz._gated_kp  # noqa: SLF001
    )
    assert base is not None, "conf 0.9 배치는 엄격 경로로 성립해야 한다"
    assert fz.build_angle_bake_spec(
        _KNEE_CRIT, _KNEE_MEMBERS, rep, _MID, fz._gated_kp,  # noqa: SLF001
        direction_resolver=None,
    ) == base
    assert fz.build_angle_bake_spec(
        _KNEE_CRIT, _KNEE_MEMBERS, rep, _MID, fz._gated_kp,  # noqa: SLF001
        direction_resolver=fz._relaxed_dir_kp,  # noqa: SLF001
    ) == base


# ── ② 완화 + 안정 → 성립 ──────────────────────────────────────────────────────


def test_relaxed_direction_point_with_stable_series_yields_spec():
    """방향점 conf 0.42(꼭짓점 0.9) + 전 프레임 동일 좌표 → 3점 스펙이 나온다."""
    rep = _report({"right_ankle": 0.42})
    assert fz.build_angle_bake_spec(
        _KNEE_CRIT, _KNEE_MEMBERS, rep, _MID, fz._gated_kp  # noqa: SLF001
    ) is None, "엄격 경로는 여기서 죽어야 이 시험이 무언가를 잰다"
    spec = _stable(rep)
    assert spec is not None
    assert len(spec) == 3
    assert spec[0] == _V, "꼭짓점은 엄격 경로가 준 그 좌표"


# ── ③ 완화 + 불안정 → None ────────────────────────────────────────────────────


def test_relaxed_direction_point_with_jitter_is_rejected():
    """같은 conf 인데 측정 프레임만 크게 튀면 침묵한다 — 이 축이 실제로 잰다.

    튐 폭은 임계의 3배(상수에서 파생)라 임계값이 재조정돼도 이 시험은 안 흔들린다.
    """
    dev = min(3.0 * fz._ANGLE_STABILITY_MAX_DEV_DEG, 89.0)  # noqa: SLF001
    rep = _report(
        {"right_ankle": 0.42},
        xy_by_frame={_MID: {"right_ankle": _polar(dev)}},
    )
    assert _stable(rep) is None


# ── ④ 하한 미달 → None ────────────────────────────────────────────────────────


def test_below_direction_floor_stays_silent():
    """0.35 미만은 안정해도 안 연다 — 완화는 하한 없는 개방이 아니다."""
    rep = _report({"right_ankle": 0.30})
    assert _stable(rep) is None


# ── ⑤ conf 부재 → None ────────────────────────────────────────────────────────


def test_missing_confidence_stays_silent():
    """완화는 "낮은 신뢰"를 여는 것이지 "증명 없음"을 여는 것이 아니다.

    2026-07-05 pod 실측: confidence 없는 기준 report 가 통과해 몸과 무관한 방향으로
    선이 폭주했다 (`_gated_kp` docstring).
    """
    rep = _report(with_conf=False)
    assert _stable(rep) is None


# ── ⑥ 꼭짓점은 안 열린다 (판정 1) ────────────────────────────────────────────


def test_low_confidence_vertex_is_never_relaxed():
    """꼭짓점 저신뢰 카드는 종전대로 침묵 — 승인 4R#1 을 안 깬다."""
    rep = _report({"right_knee": 0.42})
    assert _stable(rep) is None


def test_shoulder_hip_serves_two_roles_and_vertex_wins():
    """★ 함정: 어깨 계열에서 `left_hip` 은 꼭짓점 내분점 **과** 몸통 방향점이다.

    관절명으로 완화 대상을 가르면 꼭짓점까지 함께 열려 판정 1 이 무너진다.
    역할로 갈랐으므로 `left_hip` 저신뢰 = 꼭짓점 저신뢰 = None 이어야 한다.
    """
    rep = _report({"left_hip": 0.42})
    assert _stable(rep, _SHOULDER_CRIT, _SHOULDER_MEMBERS) is None
    # 대조군: 방향점 전용인 elbow 만 저신뢰면 어깨 계열도 정상적으로 열린다.
    ok = _stable(
        _report({"left_elbow": 0.42}), _SHOULDER_CRIT, _SHOULDER_MEMBERS
    )
    assert ok is not None


# ── ⑦ 이웃 표본 부족 / fps 부재 → None (fail-closed) ─────────────────────────


def test_insufficient_neighbors_is_fail_closed():
    """잴 수 없는 순간에는 확정 시각 언어를 그리지 않는다."""
    rep = _report({"right_ankle": 0.42}, frames=1)
    assert fz.build_stable_angle_bake_spec(
        _KNEE_CRIT, _KNEE_MEMBERS, rep, 0,
        vertex_resolver=fz._gated_kp,  # noqa: SLF001
        direction_resolver=fz._relaxed_dir_kp,  # noqa: SLF001
    ) is None


def test_neighbors_failing_the_floor_is_fail_closed():
    """이웃이 전부 하한 미달이면 기준선을 못 만든다 → None."""
    low = {f: {"right_ankle": (float("nan"), float("nan"))}
           for f in range(_N) if f != _MID}
    rep = _report({"right_ankle": 0.42}, xy_by_frame=low)
    assert _stable(rep) is None


def test_missing_fps_is_fail_closed():
    rep = _report({"right_ankle": 0.42}, fps=0.0)
    assert _stable(rep) is None


# ── ⑧ 임계 경계 ──────────────────────────────────────────────────────────────


def test_threshold_boundary_reads_the_constant():
    """편차가 임계 바로 아래면 성립, 바로 위면 None. 값 하드코딩 금지."""
    thr = fz._ANGLE_STABILITY_MAX_DEV_DEG  # noqa: SLF001
    under = _report(
        {"right_ankle": 0.42},
        xy_by_frame={_MID: {"right_ankle": _polar(thr - 0.5)}},
    )
    over = _report(
        {"right_ankle": 0.42},
        xy_by_frame={_MID: {"right_ankle": _polar(thr + 0.5)}},
    )
    assert _stable(under) is not None
    assert _stable(over) is None


# ══ 배선 (Task 3) ════════════════════════════════════════════════════════════


class _Match:
    def __init__(self, start, path):
        self.start = start
        self.path = path


def _identity(n=_N):
    return _Match(0, [(i, i) for i in range(n)])


def _frames():
    """**결이 있는** 합성 프레임 — 크롭 치수가 바뀌면 렌더 바이트가 반드시 갈린다.

    균일 회색 프레임을 쓰면 38px 크롭과 53px 크롭이 같은 360px 판으로 확대돼
    바이트가 우연히 같아진다 — 경계 B 자물쇠(⑮)가 아무것도 못 재게 된다.
    B 채널은 200 고정: 브랜드색(51)과 겹칠 수 없어 `pngPlain` 브랜드 픽셀 0
    판정(⑭)이 배경 우연 일치로 오염되지 않는다.
    """
    ys, xs = np.mgrid[0:_SIZE, 0:_SIZE]
    base = np.zeros((_N, _SIZE, _SIZE, 3), dtype=np.uint8)
    for f in range(_N):
        base[f, :, :, 0] = ((xs * 7 + ys * 3 + f * 5) % 256).astype(np.uint8)
        base[f, :, :, 1] = ((xs * 3 + ys * 11 + f * 2) % 256).astype(np.uint8)
        base[f, :, :, 2] = 200
    return base


def _brand_px_left_panel(png: bytes) -> int:
    arr = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))[:, : fz._OUT, :]
    return int(np.all(arr == np.asarray(fz._BRAND, dtype=np.uint8), axis=-1).sum())


def _brand_px_right_panel(png: bytes) -> int:
    """`_compose` 의 `gap` 은 함수 지역 리터럴이라 상수로 못 읽는다 — 마지막
    `_OUT` 열을 자른다 (test_fault_zoom_suppress_keeps_angle 복제)."""
    arr = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))[:, -fz._OUT:, :]
    return int(np.all(arr == np.asarray(fz._BRAND, dtype=np.uint8), axis=-1).sum())


def _unit(criterion, joints):
    return {"criterion": criterion, "joints": tuple(joints),
            "region": None, "at_frame_idx": None}


_WIRE_UNITS = [_unit(_KNEE_CRIT, ["right_knee"])]


def _build(report):
    """양측 같은 report 로 카드 1장 — 학생·기준이 대칭이라 both-or-neither 를 잰다."""
    return fz.build_fault_zoom_comparisons(
        _frames(), _frames(),
        report, report,
        worst_seconds=None,
        fault_joints=["right_knee"],
        joint_deltas={"right_knee": 20.0},
        frames_fps=_FPS,
        joint_kinds={"right_knee": "deficit"},
        dtw_match=None,
        criterion_units=_WIRE_UNITS,
        user_frame_idx=_MID,
        ref_frame_idx=_MID,
        analysis_id="t-oxg",
    )


def _bake_logs(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records
            if "fault_zoom_angle_bake" in r.getMessage()]


# ── ⑨ ★ additive 불변식 ──────────────────────────────────────────────────────


def test_strict_batch_never_takes_the_relaxed_path(caplog):
    """전원 고신뢰 배치는 완화 경로를 **안 탄다** — 로그가 증인이다.

    변경 전 산출을 기대값으로 박을 수 없으므로, 완화 경로를 탔다면 반드시 찍히는
    `:stable(` 접미사의 **부재**로 인증한다.
    """
    caplog.set_level("INFO")
    items = _build(_report())
    assert len(items) == 1
    logs = _bake_logs(caplog)
    assert logs and all("angle_bake=drawn" in m for m in logs)
    assert all(":stable(" not in m for m in logs), (
        "고신뢰 배치가 완화 경로를 타면 순수 additive 가 깨진 것이다"
    )
    assert _brand_px_left_panel(items[0]["png"]) > 0


# ── ⑩⑪ 새로 열린다 + 양측 대칭 ───────────────────────────────────────────────


def test_relaxed_direction_opens_the_card_on_both_panels(caplog):
    """방향점 conf 0.42 + 안정 → 양 패널에 V 가 새로 그려지고 인증도 함께 선다."""
    caplog.set_level("INFO")
    rep = _report({"right_ankle": 0.42})
    items = _build(rep)
    assert len(items) == 1
    it = items[0]
    logs = _bake_logs(caplog)
    assert any(":stable(" in m for m in logs), logs
    assert any("angle_bake=drawn" in m for m in logs)
    assert _brand_px_left_panel(it["png"]) > 0
    assert _brand_px_right_panel(it["png"]) > 0
    assert it["userMarked"] is True
    assert it["refMarked"] is True


# ── ⑫ 불안정은 계속 침묵 ─────────────────────────────────────────────────────


def test_unstable_direction_keeps_silence_and_falls_back_to_circle(caplog):
    """튀는 좌표는 안 연다 — 종전 사유(`user_gate`)로 침묵하고 원 마커로 폴백."""
    caplog.set_level("INFO")
    dev = min(3.0 * fz._ANGLE_STABILITY_MAX_DEV_DEG, 89.0)  # noqa: SLF001
    rep = _report(
        {"right_ankle": 0.42},
        xy_by_frame={_MID: {"right_ankle": _polar(dev)}},
    )
    items = _build(rep)
    assert len(items) == 1
    logs = _bake_logs(caplog)
    assert any("angle_bake=omitted:user_gate" in m for m in logs), logs
    assert all(":stable(" not in m for m in logs)
    # 원 마커 폴백 — 표시는 산다(브랜드 픽셀 > 0), V 만 없다.
    assert _brand_px_left_panel(items[0]["png"]) > 0
    assert items[0]["userMarked"] is True


# ── ⑬⑭⑮ 장수 불변 · pngPlain 무접촉 · 크롭 무변경 자물쇠 ────────────────────


def test_card_count_and_plain_png_are_untouched():
    """★ 경계 B 자물쇠 — 크롭 치수가 움직이면 여기서 바이트가 갈린다.

    `pngPlain` 은 같은 크롭·같은 초 도장에 표시만 없는 판이다. 대조군은
    **방향점 conf 0.30 배치** — 새 하한(`_ANGLE_DIR_CONF_MIN`) 미달이라 이 변경이
    원리적으로 못 건드린다. 오늘 0.42 배치와 0.30 배치는 둘 다 "스펙 미성립"이라
    같은(`_CRITERION_CROP_FRAC_MAX`) 크롭을 받는다. 완화 해상기가 크롭 치수 산출
    자리(`:3529-3545`)로 새면 0.42 배치만 좁은 크롭으로 옮겨가 둘이 갈린다.

    `_frames()` 가 결을 가진 이유가 이것이다 — 균일 배경이면 크롭 치수가 달라도
    같은 360px 판이 나와 이 시험이 아무것도 못 잰다.
    """
    strict = _build(_report())
    relaxed = _build(_report({"right_ankle": 0.42}))
    floor = _build(_report({"right_ankle": 0.30}))
    assert len(strict) == len(relaxed) == len(floor) == 1, "belle 규칙 1 — 장수 불변"
    assert relaxed[0]["pngPlain"] == floor[0]["pngPlain"], (
        "완화 배치의 크롭이 움직였다 — 순수 additive 파괴 (경계 B)"
    )
    assert strict[0]["pngPlain"] != relaxed[0]["pngPlain"], (
        "두 크롭 체제가 구분되지 않으면 위 단언이 공허하다"
    )
    for it in (strict[0], relaxed[0], floor[0]):
        plain = it["pngPlain"]
        assert _brand_px_left_panel(plain) == 0
        assert _brand_px_right_panel(plain) == 0


def test_below_floor_batch_is_untouched_by_the_new_axis(caplog):
    """하한 미달 배치는 사진까지 종전 그대로 — 완화가 넘지 말아야 할 선.

    ⑫(불안정)와 다른 칸을 잠근다: 저기는 "재봤지만 튀어서 거절", 여기는
    "잴 자격이 없어 시도조차 안 함". 둘 다 종전 침묵이지만 사유가 다르다.
    """
    caplog.set_level("INFO")
    items = _build(_report({"right_ankle": 0.30}))
    assert len(items) == 1
    logs = _bake_logs(caplog)
    assert any("angle_bake=omitted:user_gate" in m for m in logs), logs
    assert all(":stable(" not in m for m in logs)
