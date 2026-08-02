#!/usr/bin/env python3
"""split_angle crop 멤버 수리(quick-260802-gny)의 before/after 계측기.

프로덕션 함수만 호출한다 — crop 기하 계산식·마진·conf 임계를 이 파일이
복제하지 않는다. 계측 대상은 두 축이다.

  (a) --real  : 리포에 박제된 실 doc 4건(backend/evals/realfixture/fixtures)에서
                프로덕션 `criterion_units_from_records` 로 unit 을 만들고, 저장 카드가
                쓴 프레임에서 `_member_pts` -> `_side_crop` 의 crop box 를 잰다.
  (b) --sweep : 등재 10동작 x criterion 카드 전건의 배율 parity(user/ref side_px)와
                PNG sha256 을 잰다. 동작 합성과 실물 프레임 페어는 quick-260731-f5h
                하네스에서 빌려 쓰고(그 파일은 수정하지 않는다), unit 만 프로덕션
                `criterion_units_from_records` 로 새로 만든다 — f5h `_units_for` 는
                `REGION_MEMBERS` 를 직접 읽어 vision 분기가 실행되지 않기 때문이다.
  (c) --check : 산출의 구조 완결성만 본다(판정 아님).
  (d) --diff  : before/after 판정 게이트.

**한계 (조용히 통과시키지 말 것)**
  · 실 영상 프레임 해상도를 알 수 없다. `--real` 의 프레임은 `--frame-shape H W`
    (기본 640 360) 로 만든 합성 배열이고, 그 값은 산출 JSON 헤더에 박아 둔다.
    crop box 의 절대 px 는 이 가정에 의존한다. 가정 의존을 줄이려고 멤버 좌표의
    정규화 bbox extent 와 user/ref side 비를 함께 적는다 — 비는 두 패널이 같은
    shape 를 쓰는 한 shape 무관이다.
  · PNG 픽셀 내용과 사이각의 실제 재드로잉은 이 프로브의 범위 밖이다.
    여기서 답하는 것은 "crop 이 발목을 담는가"까지다.

표시 전용 계측 — 채점 경로에 어떤 값도 되돌리지 않는다.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import logging
import pathlib
import sys

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
_F5H = _REPO / ".planning" / "quick" / (
    "260731-f5h-33-g-c-3-d-1-split-angle-leg-angle-omitt"
)
_FIXTURES = _REPO / "backend" / "evals" / "realfixture" / "fixtures"

for _p in (
    str(_REPO / "backend" / "shared" / "python"),
    str(_REPO / "backend" / "functions" / "pipeline"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

# 32-03 배율 parity 판정 밴드 — fault_zoom.py 2813행 주석이 소유하는 기존 수치다.
# 이 프로브는 밴드를 **읽기만** 한다. 이탈이 나오면 표에 적고 belle 판단으로 올린다.
_PARITY_LO = 0.8
_PARITY_HI = 1.25


def _load_module(name: str, path: pathlib.Path):
    """경로 import — RunPod server._load_pipeline_module 과 같은 방식."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _pipeline():
    return _load_module(
        "gny_pipeline_app",
        _REPO / "backend" / "functions" / "pipeline" / "app.py",
    )


def _f5h():
    """f5h 스위프 하네스를 경로 import (읽기 전용 — 그 파일은 수정하지 않는다)."""
    return _load_module("gny_f5h_sweep", _F5H / "sweep_leg_angle.py")


# ── 로그 캡처 — 포맷 재파싱 대신 LogRecord.args 튜플을 읽는다 ────────────────
# fault_zoom_crop 로그 포맷이 바뀌어도 계측이 안 깨지도록 위치 인자를 그대로 쓴다.
# fault_zoom.py 2823행의 인자 순서:
#   analysis_id, region, criterion, user_kind, user_side_px, ref_kind,
#   ref_side_px, user_frame, ref_rep_idx, ref_video_idx, vertex_centered,
#   shared_side_px
_CROP_ARG_KEYS = (
    "analysis_id", "region", "criterion", "user_kind", "user_side_px",
    "ref_kind", "ref_side_px", "user_frame", "ref_rep_idx", "ref_video_idx",
    "vertex_centered", "shared_side_px",
)


class _CropCapture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict] = []

    def emit(self, record: logging.LogRecord) -> None:
        if not str(record.msg).startswith("fault_zoom_crop "):
            return
        args = record.args or ()
        if len(args) != len(_CROP_ARG_KEYS):
            self.rows.append({"_arity_mismatch": len(args)})
            return
        self.rows.append(dict(zip(_CROP_ARG_KEYS, args)))


def _as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _ratio(u, r):
    ui, ri = _as_int(u), _as_int(r)
    if ui is None or ri is None or ri == 0:
        return None
    return round(ui / ri, 6)


# ── (a) 실 doc 계측 ──────────────────────────────────────────────────────────


def _stored_cards(result: dict) -> list[dict]:
    return [c for c in (result.get("faultZoomComparisons") or []) if isinstance(c, dict)]


def _card_for(cards: list[dict], criterion: str) -> dict | None:
    for c in cards:
        if c.get("criterion") == criterion:
            return c
    return None


def _geom(report: dict, frame_idx: int, members: tuple[str, ...], h: int, w: int):
    """그 report/프레임/멤버로 프로덕션 crop 기하를 산출.

    `_member_pts` -> `_side_crop` 을 직접 부르고 반환 4번째 원소(box)를 읽는다.
    포함 판정은 `_pt_in_crop`, conf 는 `_kp_conf` — 술어 복제 0.
    """
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    valid, relaxed = fz._member_pts(report, frame_idx, members)
    anchor = fz._anchor_xy(valid, None) if valid else None
    _img, kind, _anchor_px, box = fz._side_crop(
        frame,
        [xy for _n, xy in valid],
        relaxed,
        anchor=anchor,
        center=None,
        side_override=None,
    )
    out: dict = {
        "crop_kind": kind,
        "box": list(box) if box is not None else None,
        "valid_members": [n for n, _xy in valid],
        "relaxed_count": len(relaxed),
    }
    if valid:
        xs = [xy[0] for _n, xy in valid]
        ys = [xy[1] for _n, xy in valid]
        out["norm_bbox_extent"] = {
            "x": round(max(xs) - min(xs), 6),
            "y": round(max(ys) - min(ys), 6),
        }
    probes = (
        "pelvis", "left_knee", "right_knee", "left_ankle", "right_ankle",
    )
    in_crop: dict[str, bool | None] = {}
    confs: dict[str, float | None] = {}
    for name in probes:
        if name == "pelvis":
            lh = fz._kp_xy(report, frame_idx, "left_hip")
            rh = fz._kp_xy(report, frame_idx, "right_hip")
            xy = (
                ((lh[0] + rh[0]) / 2.0, (lh[1] + rh[1]) / 2.0)
                if lh is not None and rh is not None
                else None
            )
            confs[name] = None
        else:
            xy = fz._kp_xy(report, frame_idx, name)
            c = fz._kp_conf(report, frame_idx, name)
            confs[name] = round(float(c), 6) if c is not None else None
        if xy is None or box is None:
            in_crop[name] = None
            continue
        in_crop[name] = bool(
            fz._pt_in_crop(xy, box[0], box[1], box[2], w, h)
        )
    out["in_crop"] = in_crop
    out["conf"] = confs
    return out


def run_real(frame_h: int, frame_w: int) -> dict:
    pipe = _pipeline()
    rows: list[dict] = []
    fixtures = sorted(
        p for p in _FIXTURES.glob("*.json") if p.name != "MANIFEST.json"
    )
    for path in fixtures:
        doc = json.loads(path.read_text("utf-8"))
        result = doc.get("result") or {}
        records = (result.get("deductionBreakdown") or {}).get("records") or []
        fault_joints = (result.get("visionVeto") or {}).get("faultJoints") or []
        user_report = result.get("keypointReport") or {}
        ref_id = doc.get("referenceMotionId")
        ref_path = _FIXTURES / "reference" / f"{ref_id}.json"
        ref_doc = json.loads(ref_path.read_text("utf-8")) if ref_path.exists() else {}
        ref_report = ref_doc.get("keypointReport") or {}
        cards = _stored_cards(result)
        units = fz.criterion_units_from_records(
            records, fault_joints, pipe._KISMAM_TO_KEYPOINT
        )
        for unit in units:
            crit = unit["criterion"]
            members = tuple(unit["joints"])
            card = _card_for(cards, crit)
            row: dict = {
                "fixture": path.stem,
                "referenceMotionId": ref_id,
                "criterion": crit,
                "region": unit["region"],
                "joints": list(members),
                "jointCount": len(members),
                "recordSource": next(
                    (
                        r.get("source")
                        for r in records
                        if isinstance(r, dict) and r.get("criterion") == crit
                    ),
                    None,
                ),
            }
            if card is None:
                # 그 criterion 의 저장 카드가 없다. 다른 카드의 프레임을 빌려 오지
                # 않는다 — 비워 두고 사유를 남긴다.
                row["storedCard"] = None
                row["nullReason"] = "저장 faultZoomComparisons 에 그 criterion 카드 없음"
                rows.append(row)
                continue
            u_idx = _as_int(card.get("userFrameIdx"))
            r_idx = _as_int(card.get("refFrameIdx"))
            row["storedCard"] = {
                "userFrameIdx": u_idx,
                "refFrameIdx": r_idx,
                "region": card.get("region"),
                "joint": card.get("joint"),
                "deficitDeg": card.get("deficitDeg"),
            }
            if u_idx is None or r_idx is None:
                row["nullReason"] = "저장 카드에 userFrameIdx/refFrameIdx 부재"
                rows.append(row)
                continue
            row["user"] = _geom(user_report, u_idx, members, frame_h, frame_w)
            row["ref"] = (
                _geom(ref_report, r_idx, members, frame_h, frame_w)
                if ref_report
                else None
            )
            if row["ref"] is None:
                row["refNullReason"] = f"기준 fixture 미존재: {ref_id}"
            u_box = (row["user"] or {}).get("box")
            r_box = (row["ref"] or {}).get("box") if row["ref"] else None
            if u_box and r_box:
                row["side_ratio"] = _ratio(u_box[2], r_box[2])
            rows.append(row)
    return {
        "mode": "real",
        "frameShape": {"h": frame_h, "w": frame_w},
        "frameShapeIsAssumption": True,
        "fixtures": [p.stem for p in fixtures],
        "rows": rows,
    }


# ── (b) 등재 10동작 배율 parity 스위프 ───────────────────────────────────────


def _synth_records(criterion: str) -> list[dict]:
    """실 fixture 모양의 record 합성 — split_angle 만 vision, 나머지는 geometry.

    실 doc 의 split_angle record 가 전부 `source='vision'` 이라(F1) vision 분기를
    실제로 태워야 이번 수정이 실행 경로에 오른다.
    """
    source = "vision" if criterion == "split_angle" else "geometry"
    return [{"criterion": criterion, "source": source, "points": -12}]


# 실 fixture power-spin 의 visionVeto.faultJoints 형상 (8-keypoint 이름공간).
_SYNTH_FAULT_JOINTS = (
    "left_shoulder", "right_shoulder",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
)


def _sweep_units(f5h, motion: str, kismam_map: dict) -> list[dict]:
    """그 동작의 criterion 카드 목록을 **프로덕션 함수**로 조립.

    criterion id 목록만 f5h 규칙(criteria yaml 관절 + per-joint reference_relative
    + region 표)에서 파생하고, joints 조립은 `criterion_units_from_records` 가 한다.
    """
    crits: list[str] = []
    seen: set[str] = set()
    for jk in [*f5h._criteria_joints(motion), *f5h._ANGLE_MAP]:
        if kismam_map.get(jk) is None:
            continue
        crit = f"{fz.ANGLE_VS_REFERENCE_PREFIX}{jk}"
        if crit in seen:
            continue
        seen.add(crit)
        crits.append(crit)
    crits.extend(sorted(fz.CRITERION_REGION))
    units: list[dict] = []
    for crit in crits:
        made = fz.criterion_units_from_records(
            _synth_records(crit), list(_SYNTH_FAULT_JOINTS), kismam_map
        )
        units.extend(made)
    return units


def run_sweep() -> dict:
    f5h = _f5h()
    pipe = _pipeline()
    kismam_map = pipe._KISMAM_TO_KEYPOINT
    cap = _CropCapture()
    logger = logging.getLogger("sunity_shared.analysis.fault_zoom")
    logger.setLevel(logging.INFO)
    logger.addHandler(cap)
    try:
        pairs = f5h._frame_sources()
        motions = f5h._registered_motions()
        rows: list[dict] = []
        for mi, motion in enumerate(motions):
            u_path, r_path = pairs[mi % len(pairs)]
            u_frames = f5h._load_frames(u_path)
            r_frames = f5h._load_frames(r_path)
            user_rep = f5h._report(9, 9.0, f5h._user_kp_for(mi, True))
            ref_rep = f5h._report(9, 9.0, f5h._REF_KP)
            for unit in _sweep_units(f5h, motion, kismam_map):
                crit = unit["criterion"]
                joints = list(unit["joints"])
                cap.rows.clear()
                comps = fz.build_fault_zoom_comparisons(
                    u_frames, r_frames, user_rep, ref_rep,
                    worst_seconds=0.5,
                    fault_joints=joints,
                    joint_deltas={j: 24.0 + i for i, j in enumerate(joints)},
                    frames_fps=9.0,
                    joint_kinds={j: "deficit" for j in joints},
                    dtw_match=f5h._identity(9),
                    criterion_units=[unit],
                    split_angle_present=crit == "split_angle",
                    motion_id=motion,
                    reference_anchor_overrides=None,
                    analysis_id=f"gny-{motion}",
                )
                row: dict = {
                    "motion": motion,
                    "motion_index": mi,
                    "criterion": crit,
                    "region": unit["region"],
                    "joints": joints,
                    "jointCount": len(joints),
                    "emitted": bool(comps),
                }
                if cap.rows:
                    log_row = cap.rows[-1]
                    row["crop_log"] = log_row
                    row["user_side_px"] = _as_int(log_row.get("user_side_px"))
                    row["ref_side_px"] = _as_int(log_row.get("ref_side_px"))
                    row["ratio"] = _ratio(
                        log_row.get("user_side_px"), log_row.get("ref_side_px")
                    )
                else:
                    row["crop_log"] = None
                    row["nullReason"] = "fault_zoom_crop 로그 미방출 (카드 미생성)"
                if comps:
                    png = comps[0]["png"]
                    row["png_sha256"] = hashlib.sha256(png).hexdigest()
                    row["frame_h"] = int(u_frames.shape[1])
                    row["frame_w"] = int(u_frames.shape[2])
                    row["side_clamp_limit"] = int(
                        min(u_frames.shape[1], u_frames.shape[2])
                    )
                else:
                    row["png_sha256"] = None
                rows.append(row)
    finally:
        logger.removeHandler(cap)
    return {
        "mode": "sweep",
        "parityBand": {"lo": _PARITY_LO, "hi": _PARITY_HI},
        "motions": motions,
        "cards": rows,
    }


# ── (c) 구조 완결성 ─────────────────────────────────────────────────────────


def check(label: str) -> int:
    d = _HERE / label
    problems: list[str] = []
    real_p, sweep_p = d / "real.json", d / "sweep.json"
    if not real_p.exists():
        problems.append(f"{real_p} 없음")
    if not sweep_p.exists():
        problems.append(f"{sweep_p} 없음")
    if problems:
        for p in problems:
            print("MISSING:", p)
        return 1
    real = json.loads(real_p.read_text("utf-8"))
    sweep = json.loads(sweep_p.read_text("utf-8"))
    if len(real.get("fixtures") or []) != 4:
        problems.append(f"fixture {len(real.get('fixtures') or [])}건 (4 기대)")
    for row in real.get("rows") or []:
        if not row.get("criterion"):
            problems.append(f"criterion 없는 행: {row}")
        has_box = bool((row.get("user") or {}).get("box"))
        if not has_box and not row.get("nullReason") and not row.get("refNullReason"):
            problems.append(
                f"box 도 null 사유도 없는 행: {row.get('fixture')}/{row.get('criterion')}"
            )
    if len(sweep.get("motions") or []) < 10:
        problems.append(f"동작 {len(sweep.get('motions') or [])}건 (10 이상 기대)")
    for row in sweep.get("cards") or []:
        if not row.get("criterion"):
            problems.append(f"criterion 없는 sweep 행: {row}")
        if row.get("crop_log") is None and not row.get("nullReason"):
            problems.append(
                f"crop 로그도 null 사유도 없는 행: {row.get('motion')}/{row.get('criterion')}"
            )
    if problems:
        for p in problems:
            print("INCOMPLETE:", p)
        return 1
    print(
        f"CHECK-OK {label}: fixture {len(real['fixtures'])} · real rows "
        f"{len(real['rows'])} · motions {len(sweep['motions'])} · sweep cards "
        f"{len(sweep['cards'])}"
    )
    return 0


# ── (d) before/after 판정 ───────────────────────────────────────────────────


def _key_sweep(row: dict) -> tuple:
    return (row.get("motion"), row.get("criterion"))


def _key_real(row: dict) -> tuple:
    return (row.get("fixture"), row.get("criterion"))


def diff(a_label: str, b_label: str) -> int:
    a_dir, b_dir = _HERE / a_label, _HERE / b_label
    a_sweep = json.loads((a_dir / "sweep.json").read_text("utf-8"))
    b_sweep = json.loads((b_dir / "sweep.json").read_text("utf-8"))
    a_real = json.loads((a_dir / "real.json").read_text("utf-8"))
    b_real = json.loads((b_dir / "real.json").read_text("utf-8"))
    fail: list[str] = []

    # (1) split_angle 이 아닌 sweep 카드: side_px 2종 + png_sha256 전건 동일.
    a_map = {_key_sweep(r): r for r in a_sweep["cards"]}
    b_map = {_key_sweep(r): r for r in b_sweep["cards"]}
    if set(a_map) != set(b_map):
        fail.append(
            f"sweep 카드 키 집합 불일치: only-{a_label}="
            f"{sorted(set(a_map) - set(b_map))} only-{b_label}="
            f"{sorted(set(b_map) - set(a_map))}"
        )
    moved_non_split: list[str] = []
    for key in sorted(set(a_map) & set(b_map)):
        if key[1] == "split_angle":
            continue
        ra, rb = a_map[key], b_map[key]
        for field in ("user_side_px", "ref_side_px", "png_sha256"):
            if ra.get(field) != rb.get(field):
                moved_non_split.append(
                    f"{key[0]}/{key[1]} {field}: {ra.get(field)} -> {rb.get(field)}"
                )
    if moved_non_split:
        fail.append("비-split 카드가 움직였다 (과잉 일반화):")
        fail.extend("  " + m for m in moved_non_split)

    # (2) split_angle 이 아닌 real 행: box 튜플 동일.
    ar = {_key_real(r): r for r in a_real["rows"]}
    br = {_key_real(r): r for r in b_real["rows"]}
    for key in sorted(set(ar) & set(br)):
        if key[1] == "split_angle":
            continue
        for side in ("user", "ref"):
            ba = (ar[key].get(side) or {}).get("box") if ar[key].get(side) else None
            bb = (br[key].get(side) or {}).get("box") if br[key].get(side) else None
            if ba != bb:
                fail.append(f"real {key[0]}/{key[1]} {side} box: {ba} -> {bb}")

    # (3) power-spin split_angle: 멤버 4 -> 6, box 가 leg_extension 과 갈림,
    #     발목 in_crop 이 False -> True.
    ps_key = None
    for key in br:
        if key[1] == "split_angle" and "powerspin" in (key[0] or ""):
            ps_key = key
            break
    if ps_key is None:
        fail.append("power-spin split_angle 행을 after 에서 찾지 못했다")
    else:
        a_row, b_row = ar.get(ps_key), br[ps_key]
        if a_row is None:
            fail.append("power-spin split_angle 행이 before 에 없다")
        else:
            if not (a_row.get("jointCount") == 4 and b_row.get("jointCount") == 6):
                fail.append(
                    "power-spin split_angle 멤버 수 4 -> 6 아님: "
                    f"{a_row.get('jointCount')} -> {b_row.get('jointCount')}"
                )
            le_key = (ps_key[0], "leg_extension")
            le_row = br.get(le_key)
            if le_row is None:
                fail.append("power-spin leg_extension 행이 after 에 없다")
            else:
                sb = (b_row.get("user") or {}).get("box")
                lb = (le_row.get("user") or {}).get("box")
                if sb is None or lb is None or sb == lb:
                    fail.append(
                        f"power-spin split_angle box 가 leg_extension 과 안 갈렸다: "
                        f"split={sb} leg={lb}"
                    )
            a_in = ((a_row.get("user") or {}).get("in_crop") or {})
            b_in = ((b_row.get("user") or {}).get("in_crop") or {})
            flipped = [
                j for j in ("left_ankle", "right_ankle")
                if a_in.get(j) is not True and b_in.get(j) is True
            ]
            if not flipped:
                fail.append(
                    "power-spin split_angle 발목 _pt_in_crop 이 False -> True 로 "
                    f"바뀐 것이 없다: before={a_in} after={b_in}"
                )

    if fail:
        print(f"DIFF-FAIL ({a_label} -> {b_label})")
        for f in fail:
            print(" ", f)
        return 1
    print(f"DIFF-OK ({a_label} -> {b_label}) — 게이트 3종 전건 통과")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--check")
    ap.add_argument("--diff", nargs=2, metavar=("BEFORE", "AFTER"))
    ap.add_argument(
        "--frame-shape", nargs=2, type=int, default=[640, 360], metavar=("H", "W")
    )
    args = ap.parse_args()

    if args.check:
        return check(args.check)
    if args.diff:
        return diff(args.diff[0], args.diff[1])
    if not args.out:
        ap.error("--real/--sweep 은 --out {label} 필요")
    out_dir = _HERE / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.real:
        data = run_real(args.frame_shape[0], args.frame_shape[1])
        (out_dir / "real.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8"
        )
        print(f"real -> {out_dir / 'real.json'} ({len(data['rows'])} rows)")
        return 0
    if args.sweep:
        data = run_sweep()
        (out_dir / "sweep.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8"
        )
        print(f"sweep -> {out_dir / 'sweep.json'} ({len(data['cards'])} cards)")
        return 0
    ap.error("--real / --sweep / --check / --diff 중 하나 필요")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
