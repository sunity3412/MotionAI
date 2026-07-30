#!/usr/bin/env python3
"""legacy/advisory/mode3 산출 PNG 무회귀 해시 게이트 (quick-260730-l7t Task 2 verify).

criterion 카드만 정중앙 crop 으로 바뀌고 legacy fan-out(`criterion_units=None`)·
advisory 배치·mode3 경로는 **픽셀 byte-동일**해야 한다. 그것을 증명하려면 변경 전
해시를 먼저 캡처해 두어야 하므로 이 하네스를 두 번 실행한다:

    python3 legacy_baseline.py --capture   # 변경 전 (기준 해시 기록)
    python3 legacy_baseline.py --verify    # 변경 후 (비교 + legacy_baseline.json)

산출 = legacy_baseline_before.json (캡처) / legacy_baseline.json (판정, match: bool).
프로덕션 코드 아님 — quick 디렉터리 로컬 하네스.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from dataclasses import dataclass

import numpy as np
from PIL import Image

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "backend" / "shared" / "python"))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

_REAL_FRAME_DIR = _REPO / ".planning" / "phases" / "33-result-trust-recovery"


@dataclass
class _Match:
    start: int
    path: list


_IDENTITY9 = _Match(start=0, path=[(i, i) for i in range(9)])


def _grad_frames(n: int = 9, h: int = 400, w: int = 400) -> np.ndarray:
    a = np.zeros((n, h, w, 3), dtype=np.uint8)
    a[:, :, :, 0] = np.linspace(0, 255, w).astype(np.uint8)[None, None, :]
    a[:, :, :, 1] = np.linspace(0, 255, h).astype(np.uint8)[None, :, None]
    return a


def _real_frames(rel: str, n: int = 9) -> np.ndarray:
    img = Image.open(_REAL_FRAME_DIR / rel).convert("RGB")
    arr = np.asarray(img, dtype=np.uint8)
    return np.repeat(arr[None, ...], n, axis=0)


def _report(n: int, fps: float, joint_xy: dict, joint_conf: dict) -> dict:
    joints = list(joint_xy)
    data: list[float] = []
    conf: list[float] = []
    for _f in range(n):
        for j in joints:
            data += list(joint_xy[j])
            conf.append(joint_conf.get(j, 0.9))
    return {
        "joints": joints,
        "frames": n,
        "fps": fps,
        "data": data,
        "confidence": conf,
    }


_LEGS_XY = {
    "left_hip": (0.42, 0.35),
    "right_hip": (0.58, 0.35),
    "left_knee": (0.30, 0.72),
    "right_knee": (0.70, 0.72),
}
_ARMS_XY = {
    "left_shoulder": (0.40, 0.28),
    "right_shoulder": (0.60, 0.28),
    "left_hand": (0.24, 0.10),
    "right_hand": (0.76, 0.10),
    "left_hip": (0.44, 0.52),
    "right_hip": (0.56, 0.52),
    "left_elbow": (0.32, 0.18),
    "right_elbow": (0.68, 0.18),
}


def _cases() -> dict[str, list[dict]]:
    """이름 → build_fault_zoom_comparisons 산출 (legacy/advisory/mode3 경로만)."""
    grad = _grad_frames()
    out: dict[str, list[dict]] = {}

    # (1) legacy 단일 관절 fan-out.
    u1 = _report(9, 9.0, {"left_knee": (0.375, 0.5)}, {"left_knee": 0.9})
    r1 = _report(9, 9.0, {"left_knee": (0.625, 0.5)}, {"left_knee": 0.9})
    out["legacy_single"] = fz.build_fault_zoom_comparisons(
        grad, grad, u1, r1, 0.5, ["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0, dtw_match=_IDENTITY9,
    )

    # (2) legacy legs 그룹 + 사이각(선/호) 드로잉.
    conf = {j: 0.9 for j in _LEGS_XY}
    u2 = _report(9, 9.0, _LEGS_XY, conf)
    r2 = _report(9, 9.0, _LEGS_XY, conf)
    out["legacy_grouped_split"] = fz.build_fault_zoom_comparisons(
        grad, grad, u2, r2, 0.5, list(_LEGS_XY),
        joint_deltas={"left_knee": 40.0}, frames_fps=9.0,
        joint_kinds={j: "deficit" for j in _LEGS_XY},
        dtw_match=_IDENTITY9, split_angle_present=True,
    )

    # (3) legacy relaxed crop (ref 저신뢰).
    r3 = _report(9, 9.0, {"left_knee": (0.625, 0.5)}, {"left_knee": 0.2})
    out["legacy_relaxed"] = fz.build_fault_zoom_comparisons(
        grad, grad, u1, r3, 0.5, ["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0, dtw_match=_IDENTITY9,
    )

    # (4) legacy 전신 폴백 + refMatch failed (dtw None).
    out["legacy_full_failed"] = fz.build_fault_zoom_comparisons(
        grad, grad, u1, r1, 0.5, ["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0, dtw_match=None,
    )

    # (5) advisory 배치 형상 (criterion_units 없음 = legacy 렌더 경로 공유,
    #     split_angle_present=False, 관절만 다름).
    u5 = _report(9, 9.0, _ARMS_XY, {j: 0.9 for j in _ARMS_XY})
    out["advisory_batch"] = fz.build_fault_zoom_comparisons(
        grad, grad, u5, u5, 0.5, ["left_shoulder", "right_shoulder"],
        joint_deltas={"left_shoulder": 25.0, "right_shoulder": 22.0},
        frames_fps=9.0, joint_kinds={
            "left_shoulder": "deficit", "right_shoulder": "deficit",
        },
        dtw_match=_IDENTITY9, split_angle_present=False,
    )

    # (6) mode3 (dtw_ref_fps 명시, ref rep 18fps).
    r6 = _report(18, 18.0, {"left_knee": (0.625, 0.5)}, {"left_knee": 0.9})
    out["mode3_dtw_ref_fps"] = fz.build_fault_zoom_comparisons(
        grad, grad, u1, r6, 0.5, ["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
        dtw_match=_IDENTITY9, dtw_ref_fps=9.0,
    )

    # (7) legacy + 목표 화살표 (31-03 경로).
    u7 = _report(
        9, 9.0,
        {
            "left_hip": (0.45, 0.40), "right_hip": (0.55, 0.40),
            "left_knee": (0.40, 0.62), "right_knee": (0.60, 0.62),
            "left_ankle": (0.36, 0.86), "right_ankle": (0.64, 0.86),
            "left_shoulder": (0.44, 0.20), "right_shoulder": (0.56, 0.20),
        },
        {},
    )
    r7 = _report(
        9, 9.0,
        {
            "left_hip": (0.45, 0.40), "right_hip": (0.55, 0.40),
            "left_knee": (0.41, 0.63), "right_knee": (0.59, 0.63),
            "left_ankle": (0.30, 0.84), "right_ankle": (0.70, 0.84),
            "left_shoulder": (0.44, 0.20), "right_shoulder": (0.56, 0.20),
        },
        {},
    )
    out["legacy_arrows"] = fz.build_fault_zoom_comparisons(
        grad, grad, u7, r7, 0.5, ["left_knee"],
        joint_deltas={"left_knee": 30.0}, frames_fps=9.0,
        dtw_match=_IDENTITY9, draw_arrows=True,
    )

    # (8) 실물 프레임 legacy (촬영거리/해상도 실제 형상).
    real_u = _real_frames("33-S4-M8-crops/ref-invert_0.png")
    real_r = _real_frames("33-S4-M8-crops/ref-foxtop_0.png")
    out["legacy_real_frames"] = fz.build_fault_zoom_comparisons(
        real_u, real_r, u2, r2, 0.5, list(_LEGS_XY),
        joint_deltas={"left_knee": 40.0}, frames_fps=9.0,
        joint_kinds={j: "deficit" for j in _LEGS_XY},
        dtw_match=_IDENTITY9, split_angle_present=True,
    )

    # (9) 회전류 기준측 초 표기 (stamp_ref) legacy.
    out["legacy_stamp_ref"] = fz.build_fault_zoom_comparisons(
        grad, grad, u1, r1, 0.5, ["left_knee"],
        joint_deltas={"left_knee": 20.0}, frames_fps=9.0,
        dtw_match=_IDENTITY9, stamp_ref=True,
    )
    return out


def _hashes() -> dict[str, list[str]]:
    res: dict[str, list[str]] = {}
    for name, comps in _cases().items():
        res[name] = [
            hashlib.sha256(c["png"]).hexdigest() for c in comps
        ]
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    before_p = _HERE / "legacy_baseline_before.json"
    out_p = _HERE / "legacy_baseline.json"

    now = _hashes()
    if args.capture:
        before_p.write_text(json.dumps(now, indent=2, sort_keys=True) + "\n")
        print(f"captured {sum(len(v) for v in now.values())} png hashes -> {before_p}")
        for k, v in sorted(now.items()):
            print(f"  {k}: {len(v)} card(s)")
        return 0

    if not args.verify:
        ap.error("--capture 또는 --verify 중 하나 필요")
    if not before_p.exists():
        out_p.write_text(json.dumps(
            {"match": False, "reason": "baseline_before_missing"}, indent=2) + "\n")
        print("FAIL: legacy_baseline_before.json 미존재 — --capture 선행 필요")
        return 1

    before = json.loads(before_p.read_text())
    diffs: list[str] = []
    for k in sorted(set(before) | set(now)):
        b, a = before.get(k), now.get(k)
        if b != a:
            diffs.append(f"{k}: before={b} after={a}")
    payload = {
        "match": not diffs,
        "cases": len(now),
        "cards": sum(len(v) for v in now.values()),
        "diffs": diffs,
        "before": before,
        "after": now,
    }
    out_p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if diffs:
        print("FAIL — legacy/advisory/mode3 산출 변경:")
        for d in diffs:
            print("  " + d)
        return 1
    print(f"PASS — {payload['cases']} case / {payload['cards']} card 해시 동일")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
