#!/usr/bin/env python3
"""등재 10동작 일반화 스위프 — S9 정중앙 crop + S8 각도 베이크 (quick-260730-l7t Task 3).

single-motion-fixation 금지(D-41, blocking)의 실증 하네스. 한 동작에서만 맞는
수정이 아님을 보이려면 **등재 동작 전건**에서 같은 불변식이 성립해야 한다.

동작 목록은 `backend/judging_data/criteria/*.yaml` **glob 에서 파생**한다 —
목록 하드코딩 0 (동작이 추가되면 자동 등장). criterion 도 그 동작의 criteria yaml
관절 + `fault_zoom.CRITERION_REGION` 키에서 파생한다.

프레임은 로컬 실물(360x640 추출분 + 33-S4 크롭 패널)을 쓰고, keypointReport 는
**실제 형상**(학생 12관절 / 기준 8관절 = phase4_v1)으로 합성한다 — 기준 영상은
로컬에 없으므로(§C-4 Pod 이관) 좌표만 합성하고 프레임은 실물을 쓴다.

    python3 sweep_angle_crop.py            # PNG + summary.json 생성
    python3 sweep_angle_crop.py --assert   # 불변식 4개 검사 (exit 1 = 위반)

산출: sweep_out/{motion}__{criterion}.png · sweep_out/summary.json
프로덕션 코드 아님 — quick 디렉터리 로컬 하네스.
"""

from __future__ import annotations

import argparse
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
# 기준 = phase4_v1 legacy 8관절 (ankle/elbow **부재**가 실제 형상).
_REF_KP = {
    "left_shoulder": (0.520, 0.352), "right_shoulder": (0.586, 0.336),
    "left_hip": (0.488, 0.492), "right_hip": (0.540, 0.480),
    "left_knee": (0.430, 0.664), "right_knee": (0.600, 0.680),
    "left_hand": (0.446, 0.164), "right_hand": (0.604, 0.152),
}


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


def _frame_sources() -> list[tuple[pathlib.Path, pathlib.Path]]:
    """(학생 프레임, 기준 프레임) 실물 페어 — 동작마다 순환 사용."""
    stills = sorted(_ASSETS.glob("belle_still_f0*.png"))
    pairs: list[tuple[pathlib.Path, pathlib.Path]] = []
    for i in range(len(stills)):
        pairs.append((stills[i], stills[(i + 3) % len(stills)]))
    return pairs


def run(anchor_all: bool) -> dict:
    # 두 변종의 PNG 를 섞지 않는다 — sweep_out/ = production 진실(현 주석 상태),
    # sweep_out/anchored/ = "§C-4 주석이 채워졌다면" 가정 산출.
    out_dir = _OUT_DIR / "anchored" if anchor_all else _OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = _Capture()
    logger = logging.getLogger("sunity_shared.analysis.fault_zoom")
    logger.setLevel(logging.INFO)
    logger.addHandler(cap)

    pairs = _frame_sources()
    motions = _registered_motions()
    rows: list[dict] = []
    for mi, motion in enumerate(motions):
        u_path, r_path = pairs[mi % len(pairs)]
        u_frames = _load_frames(u_path)
        r_frames = _load_frames(r_path)
        user_rep = _report(9, 9.0, _USER_KP)
        ref_rep = _report(9, 9.0, _REF_KP)
        for unit in _units_for(motion):
            cap.crop.clear()
            cap.bake.clear()
            # 앵커 주석 override — anchor_all 이면 부재 관절 대입을 전 동작에 가정해
            # "주석이 채워졌을 때" 거동까지 스위프한다 (§C-4 사전 검증).
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
            comps = fz.build_fault_zoom_comparisons(
                u_frames, r_frames, user_rep, ref_rep,
                worst_seconds=0.5,
                fault_joints=list(unit["joints"]),
                joint_deltas={j: 24.0 + i for i, j in enumerate(unit["joints"])},
                frames_fps=9.0,
                joint_kinds={j: "deficit" for j in unit["joints"]},
                dtw_match=_identity(9),
                criterion_units=[unit],
                split_angle_present=unit["criterion"] == "split_angle",
                motion_id=motion,
                reference_anchor_overrides=overrides,
                analysis_id=f"sweep-{motion}",
            )
            row: dict = {
                "motion": motion,
                "criterion": unit["criterion"],
                "emitted": bool(comps),
                "user_frame": u_path.name,
                "ref_frame": r_path.name,
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
            if comps:
                c = comps[0]
                row["userVideoSec"] = c.get("userVideoSec")
                row["refVideoSec"] = c.get("refVideoSec")
                u_panel, r_panel = _split_panels(c["png"])
                row["user_angle_drawn"] = _panel_has_angle(u_panel)
                row["ref_angle_drawn"] = _panel_has_angle(r_panel)
                name = f"{motion}__{unit['criterion']}.png"
                (out_dir / name).write_bytes(c["png"])
                row["png"] = name
            rows.append(row)
    logger.removeHandler(cap)
    return {"motions": motions, "cards": rows}


def check(summary: dict) -> list[str]:
    """불변식 4개 — 위반 목록 반환 (빈 리스트 = PASS)."""
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
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assert", dest="do_assert", action="store_true")
    ap.add_argument(
        "--anchor-all", action="store_true",
        help="부재 관절 대입 선언을 전 동작에 가정 (주석 채움 후 거동 사전 검증)",
    )
    args = ap.parse_args()

    summary = run(anchor_all=args.anchor_all)
    problems = check(summary)
    summary["invariant_violations"] = problems
    summary["anchor_all"] = args.anchor_all
    out = (_OUT_DIR / "anchored" if args.anchor_all else _OUT_DIR) / "summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")

    cards = summary["cards"]
    emitted = [c for c in cards if c.get("emitted")]
    centered = [c for c in emitted if c.get("vertex_centered")]
    baked = [c for c in emitted if c.get("user_angle_drawn")]
    print(f"motions={len(summary['motions'])} cards={len(cards)} "
          f"emitted={len(emitted)} vertex_centered={len(centered)} "
          f"angle_baked={len(baked)}")
    print(f"summary -> {out}")
    if problems:
        print(f"INVARIANT VIOLATIONS ({len(problems)}):")
        for p in problems[:20]:
            print("  " + p)
        return 1 if args.do_assert else 0
    print("invariants: PASS (동작명 분기 0 · 배율 동일 · parity · 각도 대칭)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
