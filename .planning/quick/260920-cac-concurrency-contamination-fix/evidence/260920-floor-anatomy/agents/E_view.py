"""E — 시점 기술자(viewpoint descriptor) 공용 모듈.

좌표 출처: 각 doc 의 joints3d (flat, joints3dKeys/joints3dFrames 로 reshape).
z 는 전부 0 이므로 사실상 2D 이미지 좌표다 — 운영 features.compute_joint_angles
가 그 위에서 3점 각을 잰다(= 2D 투영각).

기술자는 전부 '스케일 불변 비율' 이라 체형·거리·해상도에 둔감하고, 카메라 방위각
(yaw)·고도(pitch)에만 반응하도록 골랐다.
"""
from __future__ import annotations
import numpy as np

COCO = ("nose","left_eye","right_eye","left_ear","right_ear","left_shoulder","right_shoulder",
        "left_elbow","right_elbow","left_wrist","right_wrist","left_hip","right_hip",
        "left_knee","right_knee","left_ankle","right_ankle")
IDX = {n: i for i, n in enumerate(COCO)}


def kp_of(doc):
    """doc(ref doc 또는 fixture result) → (T,17,2) 이미지좌표."""
    if "joints3d" in doc:
        j3, keys, = doc["joints3d"], doc["joints3dKeys"]
    else:
        r = doc["result"]; j3, keys = r["joints3d"], r["joints3dKeys"]
    nk = len(keys)
    a = np.asarray(j3, float).reshape(-1, nk, 3)
    assert list(keys) == list(COCO), keys
    return a[:, :, :2]


def _n(v):
    return np.linalg.norm(v, axis=-1)


def descriptors(kp):
    """(T,17,2) → dict[name] = (T,) 프레임별 시점 기술자."""
    P = lambda k: kp[:, IDX[k], :]
    ls, rs = P("left_shoulder"), P("right_shoulder")
    lh, rh = P("left_hip"), P("right_hip")
    msh, mhp = (ls + rs) / 2, (lh + rh) / 2
    torso = _n(msh - mhp)
    torso = np.where(torso > 1e-6, torso, np.nan)

    d = {}
    # 1) 단축(foreshortening) — 몸통 yaw 프록시. 정면 max, 측면 ~0.
    d["sw_torso"] = _n(ls - rs) / torso            # 어깨폭/몸통길이
    d["hw_torso"] = _n(lh - rh) / torso            # 골반폭/몸통길이
    # 2) 좌우 사지 투영길이 비 (log) — 카메라가 정면에서 벗어나면 한쪽이 짧아진다.
    for nm, a, b in (("uparm", "shoulder", "elbow"), ("forearm", "elbow", "wrist"),
                     ("thigh", "hip", "knee"), ("shank", "knee", "ankle")):
        L = _n(P(f"left_{a}") - P(f"left_{b}"))
        R = _n(P(f"right_{a}") - P(f"right_{b}"))
        with np.errstate(divide="ignore", invalid="ignore"):
            d[f"lr_{nm}"] = np.log((L + 1e-6) / (R + 1e-6))
    # 3) 몸 축 방위 — 폴 축은 doc 에 없다. 폴이 화면 수직이라는 가정 아래
    #    이미지 수직을 폴 축 프록시로 쓴다. [가정] 표시 대상.
    ax = msh - mhp
    d["body_tilt_deg"] = np.degrees(np.arctan2(np.abs(ax[:, 0]), np.abs(ax[:, 1])))
    # 4) 어깨선이 몸통축과 이루는 각 — 롤/카메라 고도 프록시
    sh = ls - rs
    cs = np.abs((sh[:, 0] * ax[:, 0] + sh[:, 1] * ax[:, 1]) / (_n(sh) * _n(ax) + 1e-9))
    d["sh_axis_deg"] = np.degrees(np.arccos(np.clip(cs, 0, 1)))
    # 5) 머리 폭(귀 간격)/몸통 — 머리 yaw 프록시
    d["ear_torso"] = _n(P("left_ear") - P("right_ear")) / torso
    return d


NAMES = ("sw_torso", "hw_torso", "lr_uparm", "lr_forearm", "lr_thigh", "lr_shank",
         "body_tilt_deg", "sh_axis_deg", "ear_torso")
# 좌우비(log)는 절대값으로 요약해야 '카메라가 한쪽에서 본다'는 크기를 잰다.
ABS = {"lr_uparm", "lr_forearm", "lr_thigh", "lr_shank"}


def summary(kp):
    d = descriptors(kp)
    out = {}
    for k in NAMES:
        v = d[k]
        v = np.abs(v) if k in ABS else v
        v = v[np.isfinite(v)]
        out[k] = float(np.median(v)) if v.size else float("nan")
    return out
