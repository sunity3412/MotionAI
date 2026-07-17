"""Spike 004-iii-b — GT-free pose-consistency 게이트 계산.

입력: kpts/<name>.npz (원본) + kpts_omni/<name>.npz (Omni 합성)
축:
  1) 교차시점 굴곡각 MAE — flexion 각(팔꿈치/무릎/힙/어깨)은 시점 준불변.
     시간축은 ts 기반 공통 그리드 보간 + lag 탐색(±1s), L/R 라벨은 직접/스왑 중 우세 매핑.
  2) 뼈길이 불변 — torso 정규화 segment 길이의 프레임간 CV. omni/orig 비율 = 환각 지표.
  3) 시간축 일관성 — 각도 2차차분 스파이크(>25°) 빈도. omni/orig 비율.
  4) 검출 품질 — body kpt 평균 confidence.
근거: NLM 2026-07-17 프로토콜 (교차시점 일관성 / 뼈길이 / 가속도) + IPSF Page 19.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
BODY_CONF = 0.3

# COCO-Wholebody body 17
ANGLES = {
    "elbow_L": (5, 7, 9), "elbow_R": (6, 8, 10),
    "knee_L": (11, 13, 15), "knee_R": (12, 14, 16),
    "hip_L": (5, 11, 13), "hip_R": (6, 12, 14),
    "shoulder_L": (7, 5, 11), "shoulder_R": (8, 6, 12),
}
SWAP = {"elbow_L": "elbow_R", "elbow_R": "elbow_L", "knee_L": "knee_R", "knee_R": "knee_L",
        "hip_L": "hip_R", "hip_R": "hip_L", "shoulder_L": "shoulder_R", "shoulder_R": "shoulder_L"}
SEGMENTS = {
    "upper_arm_L": (5, 7), "forearm_L": (7, 9), "upper_arm_R": (6, 8), "forearm_R": (8, 10),
    "thigh_L": (11, 13), "shin_L": (13, 15), "thigh_R": (12, 14), "shin_R": (14, 16),
}


def joint_angles(kpts: np.ndarray, scores: np.ndarray) -> dict[str, np.ndarray]:
    out = {}
    for name, (a, b, c) in ANGLES.items():
        v1 = kpts[:, a] - kpts[:, b]
        v2 = kpts[:, c] - kpts[:, b]
        cos = (v1 * v2).sum(-1) / (np.linalg.norm(v1, axis=-1) * np.linalg.norm(v2, axis=-1) + 1e-9)
        ang = np.degrees(np.arccos(np.clip(cos, -1, 1)))
        conf = (scores[:, [a, b, c]] > BODY_CONF).all(-1)
        ang[~conf] = np.nan
        out[name] = ang
    return out


def bone_cv(kpts: np.ndarray, scores: np.ndarray) -> float:
    torso = np.linalg.norm(
        (kpts[:, 5] + kpts[:, 6]) / 2 - (kpts[:, 11] + kpts[:, 12]) / 2, axis=-1
    )
    cvs = []
    for a, b in SEGMENTS.values():
        seg = np.linalg.norm(kpts[:, a] - kpts[:, b], axis=-1) / (torso + 1e-9)
        conf = (scores[:, [a, b]] > BODY_CONF).all(-1) & (scores[:, [5, 6, 11, 12]] > BODY_CONF).all(-1)
        s = seg[conf]
        if len(s) >= 10:
            cvs.append(np.nanstd(s) / (np.nanmean(s) + 1e-9))
    return float(np.mean(cvs)) if cvs else float("nan")


def jerk_rate(angles: dict[str, np.ndarray]) -> float:
    spikes, total = 0, 0
    for a in angles.values():
        d2 = np.abs(np.diff(a, 2))
        valid = ~np.isnan(d2)
        spikes += int((d2[valid] > 25).sum())
        total += int(valid.sum())
    return spikes / total if total else float("nan")


def resample(ang: np.ndarray, ts: np.ndarray, grid: np.ndarray) -> np.ndarray:
    valid = ~np.isnan(ang)
    if valid.sum() < 5:
        return np.full_like(grid, np.nan)
    return np.interp(grid, ts[valid], ang[valid], left=np.nan, right=np.nan)


def pair_mae(o: dict, o_ts, m: dict, m_ts) -> tuple[float, str, float, dict[str, float]]:
    grid = np.arange(0.2, 7.8, 1 / 9)
    best = (np.inf, "direct", 0.0, {})
    for mapping in ("direct", "swap"):
        for lag in np.arange(-1.0, 1.01, 1 / 9):
            maes, per = [], {}
            for name in ANGLES:
                src = m[name if mapping == "direct" else SWAP[name]]
                a = resample(o[name], o_ts, grid)
                b = resample(src, m_ts + lag, grid)
                d = np.abs(a - b)
                if (~np.isnan(d)).sum() >= 20:
                    v = float(np.nanmean(d))
                    maes.append(v)
                    per[name] = round(v, 1)
            if len(maes) >= 4:
                mm = float(np.mean(maes))
                if mm < best[0]:
                    best = (mm, mapping, float(lag), per)
    return best


def main() -> None:
    rows = []
    for orig_npz in sorted((HERE / "kpts").glob("*.npz")):
        name = orig_npz.stem
        omni_npz = HERE / "kpts_omni" / f"{name}.npz"
        if not omni_npz.exists():
            rows.append({"clip": name, "status": "blocked(모더레이션)"})
            continue
        o, m = np.load(orig_npz), np.load(omni_npz)
        oa = joint_angles(o["kpts"], o["scores"])
        ma = joint_angles(m["kpts"], m["scores"])
        mae, mapping, lag, per = pair_mae(oa, o["ts"], ma, m["ts"])
        ocv, mcv = bone_cv(o["kpts"], o["scores"]), bone_cv(m["kpts"], m["scores"])
        oj, mj = jerk_rate(oa), jerk_rate(ma)
        oconf = float(np.nanmean(o["scores"][:, :17]))
        mconf = float(np.nanmean(m["scores"][:, :17]))
        rows.append({
            "clip": name, "status": "ok",
            "angle_mae_deg": round(mae, 1), "lr_mapping": mapping, "lag_s": round(lag, 2),
            "per_joint_mae": per,
            "bone_cv_orig": round(ocv, 3), "bone_cv_omni": round(mcv, 3),
            "bone_cv_ratio": round(mcv / ocv, 2) if ocv else None,
            "jerk_orig": round(oj, 4), "jerk_omni": round(mj, 4),
            "conf_orig": round(oconf, 2), "conf_omni": round(mconf, 2),
        })
    (HERE / "gate_out" / "metrics.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    for r in rows:
        if r["status"] != "ok":
            print(f"{r['clip']:<20} {r['status']}")
        else:
            print(f"{r['clip']:<20} MAE={r['angle_mae_deg']:>5}° map={r['lr_mapping']:<6} "
                  f"boneCV {r['bone_cv_orig']}→{r['bone_cv_omni']} (x{r['bone_cv_ratio']}) "
                  f"jerk {r['jerk_orig']}→{r['jerk_omni']} conf {r['conf_orig']}→{r['conf_omni']}")


if __name__ == "__main__":
    main()
