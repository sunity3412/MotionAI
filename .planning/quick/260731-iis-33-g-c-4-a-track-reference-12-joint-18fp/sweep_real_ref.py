#!/usr/bin/env python3
"""등재 동작 전건 스위프 — **기준측만 실 12관절 18fps 보고서**로 교체 (quick-260731-iis T4).

quick-260731-f5h `sweep_leg_angle.py` 복제본. 통제 변수는 전부 그대로 두고
**딱 한 가지**만 바꾼다:

    `_REF_KP` 합성 8관절  →  T1 산출 `reference-kp-18fps.json` 의 실 12관절 18fps 보고서

바꾸지 않은 것 (f5h 와 직접 비교가 성립하도록): 배경 정지 이미지, 학생 12관절 좌표,
ankle 사다리, criteria glob, 렌더 엔트리, A/B 픽셀 오라클, crop 기하 스파이, 불변식 6종.

**표시 프레임 선택** (변환식 복제 0 — 프로덕션 함수만 사용):
  f5h 의 기준 보고서는 9프레임짜리 합성이라 `_identity(9)` DTW 로 충분했다. 실 보고서는
  118~931 프레임이라 identity 를 그대로 쓰면 기준의 **앞 0.44초만** 보게 된다 = 측정 대상이
  아니다. 그래서 카드마다:
    (1) 후보 = 기준 전 구간을 덮는 9fps 인덱스 (rep9_n = frames*9/fps, 프로덕션 공식과
        같은 식을 `fz.ref_display_frame_index` 가 쓰는 그 정의로만 계산)
    (2) `fz.select_confident_frame(ref_rep, 후보, members)` 로 **멤버 관절 평균 conf 최대**
        프레임을 고른다 (프로덕션 함수 직접 호출)
    (3) 그 9fps 값을 `fz._to_rep_idx` 로 DTW ref 인덱스 공간(= r_rep_fps)으로 올려
        DTW path 를 그 프레임에 고정한다
  즉 "그 카드가 실제로 보게 되는 기준 프레임"을 프로덕션 선택 규칙으로 정한다.
  고른 인덱스는 카드별로 `ref_sel_9fps` / `ref_sel_rep_idx` 로 산출에 남긴다.

산출: sweep_out/{label}/{motion}__{criterion}.png · sweep_out/{label}/summary.json
프로덕션 코드 아님 — quick 디렉터리 로컬 하네스.

─────────────────────────── 아래는 f5h 원본 설명 ───────────────────────────
등재 10동작 일반화 스위프 — D-1 다리 사이각 crop 인지 끝점 (quick-260731-f5h).

quick-260730-l7t `sweep_angle_crop.py` 이관분. 기존 4 불변식(동작명 분기 0 /
정중앙 배율 동일 / parity / 각도 대칭)과 `_units_for` 파생 로직은 그대로 두고,
D-1 판정에 필요한 6가지를 더했다:

  ① `--out {before|after}` 로 산출 분리 (`sweep_out/{label}/`).
  ② 다리 사이각 검출 = **A/B 픽셀 오라클** (임계값 0개). 같은 카드를 두 번 렌더해
     (A) 정상 · (B) `_draw_leg_angle` 를 no-op(False 반환)로 교체한 상태를 비교한다.
     `_draw_leg_angle` 가 False 를 주면 `_draw_side_leg_angle` 도 False → 호출측이
     원 마커로 폴백하므로 픽셀이 반드시 달라진다. 반대로 정상 렌더가 이미 폴백
     중이었다면 두 산출이 byte-동일하다. 즉 `png_A != png_B` ⟺ 다리 사이각이 실제로
     픽셀에 그려졌다. `_panel_has_angle` 는 재사용하지 않는다 — 그것은 패널 정중앙
     반경 16px 의 S8 호 판정이라 다리 호(반경 50px, 중심 = 골반 픽셀)를 구조적으로
     못 잡는다. 브랜드 픽셀 카운트 임계도 쓰지 않는다 — 폴백 원 마커가 같은 `_BRAND`
     색 링(r=57, width=4)이라 픽셀 수가 선+호와 같은 자릿수다 (`brand_px_*` 참고 컬럼이
     그 사실을 수치로 보인다).
  ③ crop 기하 계측 — `_draw_side_leg_angle` pass-through 스파이가 호출마다 (box,
     frame 크기, 결과)를 기록하고, 그 box 로 **프로덕션 술어** `_pt_in_crop`/`_gated_kp`
     를 직접 호출해 pelvis/ankle/knee 포함 여부와 끝점 예상(`ankle`|`knee`|`none`)을
     산출한다. crop 계산식 복제 0.
  ④ 동작축 변형 — `_USER_KP` 의 **ankle 좌표만** 정렬 인덱스 파생 사다리로 흩는다
     (동작명 분기 0). 목표 = `left_ankle_in_crop` 에 True 와 False 가 둘 다 나타나
     계약 1행(ankle 유지)과 2행(knee 폴백)이 동작축에서 동시에 실증되는 것.
  ⑤ before/after 해시 대조 — `--compare before after` 로 카드별 `changed` 표.
  ⑥ INV-D1 불변식 (`--assert`, after 전용) + 사다리 캘리브레이션 게이트(양쪽).

    python3 sweep_leg_angle.py --out before
    python3 sweep_leg_angle.py --out after --assert
    python3 sweep_leg_angle.py --compare before after

산출: sweep_out/{label}/{motion}__{criterion}.png · sweep_out/{label}/summary.json
프로덕션 코드 아님 — quick 디렉터리 로컬 하네스.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import pathlib
import re
import sys
from dataclasses import dataclass

import numpy as np
from PIL import Image

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "backend" / "shared" / "python"))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

_CRITERIA_DIR = _REPO / "backend" / "judging_data" / "criteria"
_ASSETS = _REPO / ".planning" / "phases" / "33-result-trust-recovery" / "mockups" / "assets"
_S4_CROPS = _REPO / ".planning" / "phases" / "33-result-trust-recovery" / "33-S4-M8-crops"
_OUT_DIR = _HERE / "sweep_out"

# 앱/백엔드 공유 매핑 미러 (pipeline._KISMAM_TO_KEYPOINT — 33-G S9 교정분).
_ANGLE_MAP = {
    "left_elbow": "left_elbow", "right_elbow": "right_elbow",
    "left_shoulder": "left_shoulder", "right_shoulder": "right_shoulder",
    "left_hip": "left_hip", "right_hip": "right_hip",
    "left_knee": "left_knee", "right_knee": "right_knee",
}

# 학생 = 12관절(32-14). 폴 자세 형상에 맞춘 그럴듯한 정규화 좌표.
_USER_KP = {
    "left_shoulder": (0.564, 0.397), "right_shoulder": (0.612, 0.372),
    "left_hip": (0.505, 0.475), "right_hip": (0.548, 0.462),
    "left_knee": (0.402, 0.628), "right_knee": (0.612, 0.652),
    "left_hand": (0.470, 0.196), "right_hand": (0.628, 0.184),
    "left_ankle": (0.336, 0.828), "right_ankle": (0.680, 0.848),
    "left_elbow": (0.516, 0.336), "right_elbow": (0.640, 0.288),
}
# 기준 = phase4_v1 legacy 8관절 (ankle/elbow **부재**가 f5h 시점의 실제 형상).
# T4 에서는 쓰지 않는다 — 아래 `_real_ref_reports()` 가 실 12관절 보고서로 대체한다.
# 남겨 두는 이유: f5h 대비 "무엇이 통제 변수였고 무엇만 바뀌었는지"를 코드에서 보이기 위함.
_REF_KP = {
    "left_shoulder": (0.520, 0.352), "right_shoulder": (0.586, 0.336),
    "left_hip": (0.488, 0.492), "right_hip": (0.540, 0.480),
    "left_knee": (0.430, 0.664), "right_knee": (0.600, 0.680),
    "left_hand": (0.446, 0.164), "right_hand": (0.604, 0.152),
}

# ── T4: 실 기준 보고서 (18fps 12관절) ────────────────────────────────────────
_REAL_REF_JSON = _HERE / "reference-kp-18fps.json"


def _real_ref_reports() -> dict[str, dict]:
    """`reference-kp-18fps.json` → {motion_id: report}. 재가공 0 (그대로 넘긴다)."""
    raw = json.loads(_REAL_REF_JSON.read_text())["motions"]
    return {mid: rep for mid, rep in raw.items()}


def _ref_motion_id(motion: str) -> str:
    """criteria 동작 stem → reference doc id. criteria stem 이 이미 `ref-*` 형상이다."""
    return motion


def _rep9_n(rep: dict) -> int:
    """기준 보고서의 9fps 환산 길이 — ref_display_frame_index 의 rep9_n 정의와 동일."""
    frames = int(rep.get("frames") or 0)
    fps = float(rep.get("fps") or 9.0)
    if frames <= 0 or fps <= 0:
        return 0
    return max(1, int(round(frames * 9.0 / fps)))


def _ref_gate_coverage(rep: dict) -> dict[str, float]:
    """관절별 기준측 드로잉 게이트 통과율 (전 프레임). 프로덕션 술어 `_gated_kp` 직접 호출.

    "약해서 뺐다" 대신 "몇 프레임 중 몇이 통과했고 그래서 fail-closed" 를 적기 위한 수치.
    """
    frames = int(rep.get("frames") or 0)
    out: dict[str, float] = {}
    for j in rep.get("joints") or []:
        if frames <= 0:
            out[j] = float("nan")
            continue
        ok = sum(
            1 for f in range(frames) if fz._gated_kp(rep, f, j) is not None
        )
        out[j] = round(ok / frames, 4)
    return out


def _select_ref_frames(rep: dict, members) -> tuple[int, int]:
    """그 카드가 볼 기준 프레임을 **프로덕션 선택 규칙**으로 고른다.

    반환 (9fps 인덱스, DTW ref 인덱스 = r_rep_fps 공간).
    변환식을 복제하지 않는다 — `select_confident_frame` 과 `_to_rep_idx` 만 쓴다.
    """
    n9 = _rep9_n(rep)
    candidates = list(range(n9))
    sel9 = fz.select_confident_frame(rep, candidates, list(members), 9.0)
    if sel9 is None:
        sel9 = n9 // 2
    rep_fps = float(rep.get("fps") or 9.0)
    rep_frames = int(rep.get("frames") or 0)
    return int(sel9), fz._to_rep_idx(int(sel9), 9.0, rep_fps, rep_frames)

# ── ④ 동작축 ankle 사다리 (single-motion-fixation 방어) ─────────────────────────
# 종전 스위프는 10동작이 전부 같은 `_USER_KP` 라 "1 기하 x 10 배경"이었다. 정렬
# 인덱스 i(0..9) 파생으로 **ankle 만** 흩어 벌림 크기를 동작축에 실어 준다 —
# 동작명 문자열 분기 0. hips/knees/상체는 불변, 기준(_REF_KP)은 8관절 그대로.
#
# 캘리브레이션(2026-07-31): **재조정 없음** — 플랜 사다리 그대로 쓴다.
# 실측 legs crop box = (73, 247, 219) @ 360x640 (l7t 기록치와 동일). 그 box 의
# ankle y 허용 상한은 0.76(in) / 0.77(out) 이므로 아래 사다리는 i=0..2 가 crop 안,
# i=3..9 가 crop 밖으로 갈린다 = 계약 1행(ankle 유지)과 2행(knee 폴백)이 같은
# 실행에서 동시에 실증된다. (게이트 (6) 이 이 갈림을 매 실행 검사한다.)
_ANKLE_AXIS_X = 0.505      # left_hip x — 좌우 대칭축
_ANKLE_Y0 = 0.68
_ANKLE_DY = 0.03
_ANKLE_DX0 = 0.10
_ANKLE_DDX = 0.02


def _user_kp_for(i: int, ladder: bool = True) -> dict:
    """정렬 인덱스 i 의 학생 12관절 — ankle 만 사다리로 이동.

    `ladder=False` 는 대조군 — `_USER_KP` 원본(ankle y 0.828/0.848, l7t 가 D-1 을
    실측한 그 형상)을 그대로 쓴다. 사다리 효과와 D-1 자체를 분리해 보이기 위한 것.
    """
    kp = dict(_USER_KP)
    if not ladder:
        return kp
    y = _ANKLE_Y0 + _ANKLE_DY * i
    dx = _ANKLE_DX0 + _ANKLE_DDX * i
    kp["left_ankle"] = (_ANKLE_AXIS_X - dx, y)
    kp["right_ankle"] = (_ANKLE_AXIS_X + dx, y)
    return kp


@dataclass
class _Match:
    start: int
    path: list


def _identity(n: int) -> _Match:
    return _Match(start=0, path=[(i, i) for i in range(n)])


def _report(n: int, fps: float, xy: dict) -> dict:
    joints = list(xy)
    data: list[float] = []
    conf: list[float] = []
    for _f in range(n):
        for j in joints:
            data += list(xy[j])
            conf.append(0.9)
    return {
        "joints": joints, "frames": n, "fps": fps,
        "data": data, "confidence": conf,
    }


def _load_frames(path: pathlib.Path, n: int = 9) -> np.ndarray:
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
    return np.repeat(a[None, ...], n, axis=0)


def _registered_motions() -> list[str]:
    """등재 동작 = criteria glob 파생 (하드코딩 0)."""
    return sorted(p.stem for p in _CRITERIA_DIR.glob("*.yaml"))


def _criteria_joints(motion: str) -> list[str]:
    """그 동작 criteria yaml 의 관절(kismam angle key) — 중복 제거, 순서 보존."""
    import yaml

    data = yaml.safe_load((_CRITERIA_DIR / f"{motion}.yaml").read_text("utf-8")) or {}
    block = data.get("criteria") or {}
    out: list[str] = []
    for entries in block.values():
        for e in entries or []:
            j = (e or {}).get("joint")
            if isinstance(j, str) and j and j not in out:
                out.append(j)
    return out


def _units_for(motion: str) -> list[dict]:
    """그 동작의 criterion 카드 목록 (전부 데이터 파생 — 동작별 하드코딩 0).

    production 이 방출할 수 있는 criterion 은 두 갈래이고 둘 다 덮는다:
      (a) IPSF absolute — criteria yaml 의 관절 (동작별로 다름).
      (b) reference_relative per-joint (quick-260626-jwu) — 편차가 있는 **모든**
          kismam angle key 에 `angle_vs_reference__{jk}` 가 생긴다. 승인 목업의
          어깨 상세 카드가 바로 이 갈래다 (power-spin criteria yaml 에는 어깨
          criterion 이 없다) → yaml 만 보면 승인 카드를 스위프에서 놓친다.
    합집합 = 순서 보존 dedupe.
    """
    units: list[dict] = []
    seen: set[str] = set()
    for jk in [*_criteria_joints(motion), *_ANGLE_MAP]:
        kp = _ANGLE_MAP.get(jk)
        if kp is None:
            continue
        crit = f"{fz.ANGLE_VS_REFERENCE_PREFIX}{jk}"
        if crit in seen:
            continue
        seen.add(crit)
        units.append({"criterion": crit, "joints": (kp,), "region": None})
    # region criterion (split_angle/leg_extension/arm_extension) — 표에서 파생.
    for crit, region in sorted(fz.CRITERION_REGION.items()):
        units.append({
            "criterion": crit,
            "joints": tuple(fz.REGION_MEMBERS[region]),
            "region": region,
        })
    return units


_LOG_RE = re.compile(
    r"user_kind=(?P<uk>\S+) user_side_px=(?P<us>\S+) ref_kind=(?P<rk>\S+) "
    r"ref_side_px=(?P<rs>\S+) .*vertex_centered=(?P<vc>\S+) shared_side_px=(?P<ss>\S+)"
)


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.crop: list[str] = []
        self.bake: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        if msg.startswith("fault_zoom_crop "):
            self.crop.append(msg)
        elif msg.startswith("fault_zoom_angle_bake "):
            self.bake.append(msg)


def _panel_has_angle(panel: np.ndarray) -> bool:
    """그 패널에 각도 기하(흰 호)가 그려졌는가 — 정중앙 r16 흰 픽셀로 판정."""
    import math

    c = fz._OUT // 2
    r = round(fz._ANGLE_ARC_R_FRAC * fz._OUT)
    hits = 0
    for deg in range(-180, 180, 5):
        for rr in (r - 3, r - 2, r - 1, r):
            x = int(round(c + rr * math.cos(math.radians(deg))))
            y = int(round(c + rr * math.sin(math.radians(deg))))
            if 0 <= x < fz._OUT and 0 <= y < fz._OUT and tuple(panel[y, x]) == (
                255, 255, 255
            ):
                hits += 1
    return hits >= 8


def _split_panels(png: bytes) -> tuple[np.ndarray, np.ndarray]:
    img = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))
    return img[:, :fz._OUT, :], img[:, fz._OUT + 6:, :]


def _brand_px(panel: np.ndarray) -> int:
    """패널의 브랜드색(_BRAND) 정확 일치 픽셀 수 — 참고 컬럼(판정 미사용)."""
    return int(np.all(panel == np.array(fz._BRAND, dtype=panel.dtype), axis=-1).sum())


def _frame_sources() -> list[tuple[pathlib.Path, pathlib.Path]]:
    """(학생 프레임, 기준 프레임) 실물 페어 — 동작마다 순환 사용."""
    stills = sorted(_ASSETS.glob("belle_still_f0*.png"))
    pairs: list[tuple[pathlib.Path, pathlib.Path]] = []
    for i in range(len(stills)):
        pairs.append((stills[i], stills[(i + 3) % len(stills)]))
    return pairs


# ── ③ crop 기하 스파이 + 프로덕션 술어 계측 ──────────────────────────────────


class _LegSpy:
    """`_draw_side_leg_angle` pass-through 스파이 (컨텍스트 종료 시 원복).

    호출마다 (측, box, frame 크기, 반환값)을 기록한다. 측 라벨은 report 객체
    identity 로 정한다 — criterion 경로의 ref->user 호출 순서에 의존하지 않는다.
    """

    def __init__(self, user_rep: dict, ref_rep: dict) -> None:
        self.calls: list[dict] = []
        self._user = user_rep
        self._ref = ref_rep
        self._orig = fz._draw_side_leg_angle

    def __enter__(self) -> _LegSpy:
        def spy(img, frame, report, kp_idx, box):
            res = self._orig(img, frame, report, kp_idx, box)
            if report is self._user:
                side = "user"
            elif report is self._ref:
                side = "ref"
            else:
                side = "unknown"
            self.calls.append({
                "side": side,
                "box": [int(v) for v in box],
                "kp_idx": int(kp_idx),
                "h": int(frame.shape[0]),
                "w": int(frame.shape[1]),
                "result": bool(res),
                "_report": report,
            })
            return res

        fz._draw_side_leg_angle = spy
        return self

    def __exit__(self, *exc) -> bool:
        fz._draw_side_leg_angle = self._orig
        return False


def _geom_for_call(call: dict) -> dict:
    """스파이가 기록한 box 로 **프로덕션 술어**를 직접 호출해 crop 기하 산출.

    crop 계산식을 복제하지 않는다 — `_gated_kp`(conf 게이트)와 `_pt_in_crop`
    (포함 판정 단일 출처, 마진 소유)만 쓴다.
    """
    rep = call["_report"]
    idx = call["kp_idx"]
    left, top, side = call["box"]
    w, h = call["w"], call["h"]

    def _in(joint: str):
        xy = fz._gated_kp(rep, idx, joint)
        if xy is None:
            return None  # 부재/저신뢰 — "밖"이 아니라 "후보 아님"
        return fz._pt_in_crop(xy, left, top, side, w, h)

    lh = fz._gated_kp(rep, idx, "left_hip")
    rh = fz._gated_kp(rep, idx, "right_hip")
    pelvis_in = None
    if lh is not None and rh is not None:
        pelvis = ((lh[0] + rh[0]) / 2.0, (lh[1] + rh[1]) / 2.0)
        pelvis_in = fz._pt_in_crop(pelvis, left, top, side, w, h)

    def _endpoint(sd: str) -> str:
        for cand in (f"{sd}_ankle", f"{sd}_knee"):
            xy = fz._gated_kp(rep, idx, cand)
            if xy is not None and fz._pt_in_crop(xy, left, top, side, w, h):
                return cand.split("_", 1)[1]
        return "none"

    return {
        "side": call["side"],
        "box": call["box"],
        "drew": call["result"],
        "pelvis_in_crop": pelvis_in,
        "left_ankle_in_crop": _in("left_ankle"),
        "right_ankle_in_crop": _in("right_ankle"),
        "left_knee_in_crop": _in("left_knee"),
        "right_knee_in_crop": _in("right_knee"),
        "left_endpoint_expected": _endpoint("left"),
        "right_endpoint_expected": _endpoint("right"),
    }


def _side_ok(g: dict | None) -> bool | None:
    """그 측이 사이각을 그릴 수 있는가 (수정 후 계약) — 기하만으로 판정."""
    if g is None:
        return None
    return bool(
        g.get("pelvis_in_crop")
        and g.get("left_endpoint_expected") != "none"
        and g.get("right_endpoint_expected") != "none"
    )


# ── ② A/B 픽셀 오라클 ────────────────────────────────────────────────────────


class _NoLegAngle:
    """`_draw_leg_angle` 를 no-op(False) 로 교체 (컨텍스트 종료 시 원복)."""

    def __enter__(self) -> _NoLegAngle:
        self._orig = fz._draw_leg_angle

        def noop(*_a, **_k):
            return False

        fz._draw_leg_angle = noop
        return self

    def __exit__(self, *exc) -> bool:
        fz._draw_leg_angle = self._orig
        return False


def run(label: str, anchor_all: bool, ladder: bool = True) -> dict:
    out_dir = _OUT_DIR / label
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = _Capture()
    logger = logging.getLogger("sunity_shared.analysis.fault_zoom")
    logger.setLevel(logging.INFO)
    logger.addHandler(cap)

    pairs = _frame_sources()
    motions = _registered_motions()
    real_refs = _real_ref_reports()
    missing_ref = [m for m in motions if _ref_motion_id(m) not in real_refs]
    if missing_ref:
        raise SystemExit(f"실 기준 보고서 부재: {missing_ref}")
    ref_meta: dict[str, dict] = {}
    rows: list[dict] = []
    for mi, motion in enumerate(motions):
        u_path, r_path = pairs[mi % len(pairs)]
        u_frames = _load_frames(u_path)
        r_frames = _load_frames(r_path)
        user_kp = _user_kp_for(mi, ladder)
        user_rep = _report(9, 9.0, user_kp)
        # ★ 유일한 변경점 — 기준을 실 12관절 18fps 보고서로 (재가공 0).
        ref_rep = real_refs[_ref_motion_id(motion)]
        coverage = _ref_gate_coverage(ref_rep)
        ref_meta[motion] = {
            "fps": float(ref_rep.get("fps") or 0),
            "frames": int(ref_rep.get("frames") or 0),
            "joints": list(ref_rep.get("joints") or []),
            "gate_coverage": coverage,
        }
        for unit in _units_for(motion):
            # 앵커 주석 override — anchor_all 이면 부재 관절 대입을 전 동작에 가정.
            overrides = None
            if anchor_all:
                overrides = {
                    unit["criterion"]: {
                        "joint_substitutions": {
                            "left_elbow": "left_hand",
                            "right_elbow": "right_hand",
                            "left_ankle": "left_knee",
                            "right_ankle": "right_knee",
                        },
                        "note": "sweep override",
                    }
                }

            # 이 카드가 볼 기준 프레임 = 프로덕션 선택 규칙 (멤버 관절 conf 최대).
            members_for_sel = list(unit["joints"])
            if unit.get("region"):
                members_for_sel = list(fz.REGION_MEMBERS[unit["region"]])
            sel9, sel_rep_idx = _select_ref_frames(ref_rep, members_for_sel)
            ref_match = _Match(start=0, path=[(i, sel_rep_idx) for i in range(9)])

            def _build(_unit=unit, _ov=overrides, _m=motion, _match=ref_match):
                return fz.build_fault_zoom_comparisons(
                    u_frames, r_frames, user_rep, ref_rep,
                    worst_seconds=0.5,
                    fault_joints=list(_unit["joints"]),
                    joint_deltas={
                        j: 24.0 + i for i, j in enumerate(_unit["joints"])
                    },
                    frames_fps=9.0,
                    joint_kinds={j: "deficit" for j in _unit["joints"]},
                    dtw_match=_match,
                    criterion_units=[_unit],
                    split_angle_present=_unit["criterion"] == "split_angle",
                    motion_id=_m,
                    reference_anchor_overrides=_ov,
                    analysis_id=f"sweep-{_m}",
                )

            # (A) 정상 렌더 + crop 기하 스파이.
            cap.crop.clear()
            cap.bake.clear()
            with _LegSpy(user_rep, ref_rep) as spy:
                comps = _build()
                calls = list(spy.calls)
            # (A') 결정성 확인 — 오라클/해시 대조가 성립하는 전제.
            comps_a2 = _build()
            # (B) `_draw_leg_angle` no-op — 폴백 강제.
            with _NoLegAngle():
                comps_b = _build()

            row: dict = {
                "motion": motion,
                "motion_index": mi,
                "criterion": unit["criterion"],
                "emitted": bool(comps),
                "user_frame": u_path.name,
                "ref_frame": r_path.name,
                "ankle_ladder": {
                    "left": list(user_kp["left_ankle"]),
                    "right": list(user_kp["right_ankle"]),
                },
                # T4 신규 — 실 기준 보고서 메타 + 이 카드가 본 기준 프레임.
                "ref_rep_fps": float(ref_rep.get("fps") or 0),
                "ref_rep_frames": int(ref_rep.get("frames") or 0),
                "ref_rep_joints": len(ref_rep.get("joints") or []),
                "ref_sel_9fps": sel9,
                "ref_sel_rep_idx": sel_rep_idx,
                # 그 프레임에서 멤버 관절이 기준측 드로잉 게이트를 통과했는가.
                "ref_member_gated": {
                    j: fz._gated_kp(ref_rep, sel_rep_idx, j) is not None
                    for j in members_for_sel
                },
            }
            if cap.crop:
                m = _LOG_RE.search(cap.crop[-1])
                if m:
                    row.update({
                        "user_kind": m.group("uk"),
                        "user_side_px": m.group("us"),
                        "ref_kind": m.group("rk"),
                        "ref_side_px": m.group("rs"),
                        "vertex_centered": m.group("vc") == "True",
                        "shared_side_px": m.group("ss"),
                    })
            if cap.bake:
                row["angle_bake"] = cap.bake[-1].rsplit("angle_bake=", 1)[-1]

            # ③ crop 기하 — 측별 (프로덕션 술어 직접 호출).
            geoms = {g["side"]: g for g in (_geom_for_call(c) for c in calls)}
            if geoms:
                row["leg_geom"] = geoms
                u_g = geoms.get("user")
                if u_g is not None:
                    for k in (
                        "pelvis_in_crop", "left_ankle_in_crop",
                        "right_ankle_in_crop", "left_knee_in_crop",
                        "right_knee_in_crop", "left_endpoint_expected",
                        "right_endpoint_expected",
                    ):
                        row[k] = u_g[k]

            if comps:
                c = comps[0]
                png = c["png"]
                row["userVideoSec"] = c.get("userVideoSec")
                row["refVideoSec"] = c.get("refVideoSec")
                u_panel, r_panel = _split_panels(png)
                row["user_angle_drawn"] = _panel_has_angle(u_panel)
                row["ref_angle_drawn"] = _panel_has_angle(r_panel)
                row["brand_px_user"] = _brand_px(u_panel)
                row["brand_px_ref"] = _brand_px(r_panel)
                row["png_sha256"] = hashlib.sha256(png).hexdigest()
                row["deterministic"] = bool(
                    comps_a2 and comps_a2[0]["png"] == png
                )
                # ② A/B 오라클 — 임계값 0.
                png_b = comps_b[0]["png"] if comps_b else None
                row["leg_drawn"] = bool(png_b is not None and png_b != png)
                name = f"{motion}__{unit['criterion']}.png"
                (out_dir / name).write_bytes(png)
                row["png"] = name
            else:
                row["leg_drawn"] = False
            rows.append(row)
    logger.removeHandler(cap)
    return {
        "motions": motions,
        "cards": rows,
        "ladder": ladder,
        "ref_meta": ref_meta,
        "ref_library_size": len(real_refs),
        # 등재(criteria glob) 와 기준 라이브러리 크기는 다르다 — 섞어 쓰지 않는다.
        "ref_not_swept": sorted(set(real_refs) - set(motions)),
    }


def check(summary: dict, label: str) -> list[str]:
    """불변식 — 위반 목록 반환 (빈 리스트 = PASS).

    기존 4개(동작명 분기 0 / 정중앙 배율 동일 / parity / 각도 대칭) + 결정성 +
    사다리 캘리브레이션 게이트(양쪽 실행) + INV-D1(after 전용).
    """
    problems: list[str] = []

    # (1) 동작명 분기 0 — 프로덕션 모듈 grep.
    src = (
        _REPO / "backend" / "shared" / "python" / "sunity_shared" / "analysis"
        / "fault_zoom.py"
    ).read_text("utf-8").splitlines()
    for ln in src:
        if re.search(r'["\']ref-[a-z]', ln) and not ln.lstrip().startswith("#"):
            problems.append(f"동작명 문자열 분기: {ln.strip()}")

    for row in summary["cards"]:
        tag = f"{row['motion']}/{row['criterion']}"
        if not row.get("emitted"):
            continue
        # (2) 정중앙 경로 카드는 두 패널 배율이 **정확히** 같아야 한다.
        if row.get("vertex_centered"):
            if row.get("user_side_px") != row.get("ref_side_px"):
                problems.append(
                    f"{tag}: 정중앙 카드 배율 불일치 "
                    f"{row.get('user_side_px')} vs {row.get('ref_side_px')}"
                )
            if row.get("shared_side_px") != row.get("user_side_px"):
                problems.append(f"{tag}: shared_side_px 불일치")
        else:
            # (3) 비-정중앙 criterion 카드는 기존 32-03 parity 밴드(0.8~1.25) 유지.
            try:
                ratio = int(row["user_side_px"]) / int(row["ref_side_px"])
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                ratio = None
            if ratio is not None and not (0.8 <= ratio <= 1.25):
                problems.append(f"{tag}: 프레이밍 parity 이탈 ratio={ratio:.3f}")
        # (4) 각도 드로잉 대칭 — 한쪽만 그려진 카드 0.
        if row.get("user_angle_drawn") != row.get("ref_angle_drawn"):
            problems.append(
                f"{tag}: 각도 비대칭 user={row.get('user_angle_drawn')} "
                f"ref={row.get('ref_angle_drawn')}"
            )
        # (5) 결정성 — A/B 오라클과 해시 대조의 전제.
        if row.get("deterministic") is False:
            problems.append(f"{tag}: 렌더 비결정적 — A/B 오라클 무효")

    splits = [
        r for r in summary["cards"]
        if r["criterion"] == "split_angle" and r.get("emitted")
    ]
    # (6) 사다리 캘리브레이션 — ankle crop 포함이 동작축에서 갈려야 계약 1·2행이
    #     같은 실행에서 동시에 실증된다 (양쪽 실행 공통 게이트).
    seen = {r.get("left_ankle_in_crop") for r in splits}
    if summary.get("ladder", True) and not ({True, False} <= seen):
        problems.append(
            f"사다리 미캘리브레이션: left_ankle_in_crop={sorted(map(str, seen))} "
            "— True/False 가 둘 다 나와야 한다 (사다리 범위 조정 필요)"
        )

    # (7) INV-D1 — 수정 후 라벨 전용. before 에서 깨지는 것이 정상이며 그것이 D-1 버그다.
    #     T4(real-ref)도 수정 후 코드로 도는 실행이라 같은 계약을 적용한다.
    if label in ("after", "real-ref"):
        for row in splits:
            geoms = row.get("leg_geom") or {}
            u_ok = _side_ok(geoms.get("user"))
            r_ok = _side_ok(geoms.get("ref"))
            expect = bool(u_ok) and bool(r_ok)
            if bool(row.get("leg_drawn")) != expect:
                problems.append(
                    f"{row['motion']}/split_angle: INV-D1 위반 "
                    f"leg_drawn={row.get('leg_drawn')} expect={expect} "
                    f"(user_ok={u_ok} ref_ok={r_ok})"
                )
    return problems


def compare(a_label: str, b_label: str) -> int:
    """카드별 png_sha256 대조 — 변경 카드가 split_angle 뿐이어야 한다."""
    a_p = _OUT_DIR / a_label / "summary.json"
    b_p = _OUT_DIR / b_label / "summary.json"
    for p in (a_p, b_p):
        if not p.exists():
            print(f"FAIL: {p} 미존재")
            return 1
    a = json.loads(a_p.read_text())
    b = json.loads(b_p.read_text())

    def _idx(s):
        return {(r["motion"], r["criterion"]): r for r in s["cards"]}

    ai, bi = _idx(a), _idx(b)
    keys = sorted(set(ai) | set(bi))
    changed: list[tuple[str, str]] = []
    missing: list[str] = []
    for k in keys:
        ra, rb = ai.get(k), bi.get(k)
        if ra is None or rb is None:
            missing.append(f"{k[0]}/{k[1]}: 한쪽 실행에만 존재")
            continue
        if ra.get("png_sha256") != rb.get("png_sha256"):
            changed.append(k)

    by_crit: dict[str, int] = {}
    for _m, crit in changed:
        by_crit[crit] = by_crit.get(crit, 0) + 1
    print(f"compare {a_label} -> {b_label}: cards={len(keys)} changed={len(changed)}")
    for crit, n in sorted(by_crit.items()):
        print(f"  changed[{crit}] = {n}")
    for m, crit in changed:
        ra, rb = ai[(m, crit)], bi[(m, crit)]
        print(
            f"  {m}/{crit}: leg_drawn {ra.get('leg_drawn')} -> {rb.get('leg_drawn')}"
            f" | endpoint L {ra.get('left_endpoint_expected')}"
            f"->{rb.get('left_endpoint_expected')}"
            f" R {ra.get('right_endpoint_expected')}"
            f"->{rb.get('right_endpoint_expected')}"
        )
    changed_set = set(changed)
    unchanged_splits = [
        k for k in keys if k[1] == "split_angle" and k not in changed_set
    ]
    if unchanged_splits:
        print(f"  (split_angle 무변경 {len(unchanged_splits)}건: "
              + ", ".join(m for m, _c in unchanged_splits) + ")")

    bad = [k for k in changed if k[1] != "split_angle"]
    if missing:
        print("MISSING:")
        for m in missing:
            print("  " + m)
    if bad:
        print(f"VIOLATION: split_angle 외 카드 {len(bad)}건 변경")
        for m, crit in bad:
            print(f"  {m}/{crit}")
        return 1
    if missing:
        return 1
    print("compare: PASS (변경 카드 = split_angle 뿐)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="산출 라벨 (before/after)")
    ap.add_argument("--assert", dest="do_assert", action="store_true")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"))
    ap.add_argument(
        "--no-ladder", dest="ladder", action="store_false",
        help="대조군 — ankle 사다리 없이 _USER_KP 원본 형상(l7t 실측 좌표)으로",
    )
    ap.add_argument(
        "--anchor-all", action="store_true",
        help="부재 관절 대입 선언을 전 동작에 가정 (주석 채움 후 거동 사전 검증)",
    )
    args = ap.parse_args()

    if args.compare:
        return compare(args.compare[0], args.compare[1])
    if not args.out:
        ap.error("--out {before|after} 또는 --compare A B 필요")

    label = args.out
    summary = run(label, anchor_all=args.anchor_all, ladder=args.ladder)
    problems = check(summary, label)
    summary["invariant_violations"] = problems
    summary["anchor_all"] = args.anchor_all
    summary["label"] = label
    summary["ankle_ladder_spec"] = {
        "enabled": args.ladder,
        "axis_x": _ANKLE_AXIS_X, "y0": _ANKLE_Y0, "dy": _ANKLE_DY,
        "dx0": _ANKLE_DX0, "ddx": _ANKLE_DDX,
    }
    out = _OUT_DIR / label / "summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")

    cards = summary["cards"]
    emitted = [c for c in cards if c.get("emitted")]
    centered = [c for c in emitted if c.get("vertex_centered")]
    baked = [c for c in emitted if c.get("user_angle_drawn")]
    splits = [c for c in emitted if c["criterion"] == "split_angle"]
    legs_drawn = [c for c in splits if c.get("leg_drawn")]
    other_drawn = [
        c for c in emitted
        if c.get("leg_drawn") and c["criterion"] != "split_angle"
    ]
    print(f"[{label}] motions={len(summary['motions'])} cards={len(cards)} "
          f"emitted={len(emitted)} vertex_centered={len(centered)} "
          f"angle_baked={len(baked)}")
    print(f"[{label}] split_angle={len(splits)} leg_drawn={len(legs_drawn)} "
          f"(비-split 카드 leg_drawn={len(other_drawn)})")
    for c in splits:
        print(
            f"  {c['motion']:<26} ankle_in_crop L={c.get('left_ankle_in_crop')}"
            f" R={c.get('right_ankle_in_crop')}"
            f" endpoint L={c.get('left_endpoint_expected')}"
            f"/R={c.get('right_endpoint_expected')}"
            f" pelvis={c.get('pelvis_in_crop')}"
            f" leg_drawn={c.get('leg_drawn')}"
            f" brand_px u/r={c.get('brand_px_user')}/{c.get('brand_px_ref')}"
        )
    print(f"summary -> {out}")
    if problems:
        print(f"INVARIANT VIOLATIONS ({len(problems)}):")
        for p in problems[:20]:
            print("  " + p)
        return 1 if args.do_assert else 0
    print("invariants: PASS (동작명 분기 0 · 배율 동일 · parity · 각도 대칭 · "
          "결정성 · 사다리 캘리브레이션"
          + (" · INV-D1)" if label == "after" else ")"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
