"""Phase 35 — Pod 데이터 조정: 재추출 + 자세거리 정렬 + 짝 재선정 + 마커 좌표.

belle 반려(08-07 "재생 중 딴 동작 · 마커 전부 엉뚱 · 짝 장면 불신")의 뿌리 수리.
렌더의 세 입력을 낡은 doc 리포트 대신 여기서 전부 재생성한다:

  1. 재추출 — user·ref 영상을 rtmlib RTMW(GPU)로 15fps 재추출. 좌표는 **픽셀 →
     x/W·y/H 정규화를 이 스크립트가 직접** 수행(해석 모호성 0) + 스켈레톤 오버레이
     jpg 를 함께 산출해 눈으로 검증 가능하게.
  2. 정렬 — 프레임별 정규화 자세(힙 중심·몸통 스케일)를 특징으로 한 자세거리 DTW
     → 단조·슬로프 제한·이동평균 스무딩 → user_sec→ref_sec 곡선 (재생 트랙).
  3. 짝 재선정 — 각 감점 순간(atVideoSec)에서 정렬 곡선 ±2s 창의 자세거리 argmin
     → 정지 장면의 ref 프레임 (정지 트랙).
  4. 마커 — 감점 관절의 재추출 좌표+신뢰도 (정지 마커).

Pod 실행 (프로젝트 /workspace/SunityMotion, doc.json 은 로컬에서 scp 로 주입):
    cd /workspace/SunityMotion/backend && source /workspace/aws_env.sh && \
    RTMW_DEVICE=cuda python3 scripts/p35_extract_align.py --workdir /workspace/p35

산출: {workdir}/{motion}/align.json + verify/*.jpg (오버레이·짝 스틸).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

BUCKET = "sunity-motion-pilot-videos"

# motion → (user_key, ref_key). doc.json 은 {workdir}/{motion}/doc.json 필수(사전 주입).
JOBS: dict[str, tuple[str, str]] = {
    "elbow": ("fixtures/phase15/elbow-twist-sister/fault.mp4", "reference/ref-elbow-twist-sister.mp4"),
    "powerspin": ("fixtures/phase15/power-spin/fault.mp4", "reference/ref-power-spin.mp4"),
    "pdshape": ("fixtures/phase15/pdshape/correct.mp4", "reference/ref-pdshape.mp4"),
    "kipup": ("fixtures/phase15/kip-up/fault.mp4", "reference/ref-kip-up.mp4"),
    "realupload": ("uploads/csKWYvI3WCPYPysNQ9KkWecaUvq1/071df9f894d64d1696f106e613f51f5c.mp4",
                   "reference/ref-power-spin.mp4"),
}

FPS = 15.0
# COCO-17 인덱스 (rtmlib wholebody 앞 17개 = COCO body)
J17 = ["nose", "left_eye", "right_eye", "left_ear", "right_ear",
       "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
       "left_wrist", "right_wrist", "left_hip", "right_hip",
       "left_knee", "right_knee", "left_ankle", "right_ankle"]
BODY12 = ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
          "left_wrist", "right_wrist", "left_hip", "right_hip",
          "left_knee", "right_knee", "left_ankle", "right_ankle"]
EDGES = [(5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (5, 11), (6, 12),
         (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]
CONF_MIN = 0.3


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def extract(video: Path, outdir: Path) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    if not any(outdir.glob("*.jpg")):
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(video),
                        "-vf", f"fps={FPS}", "-q:v", "3", str(outdir / "%05d.jpg")], check=True)
    return sorted(outdir.glob("*.jpg"))


def build_model():
    from rtmlib import Wholebody
    det = os.environ.get("YOLOX_ONNX_PATH", "/workspace/yolox_weights/yolox_m.onnx")
    pose = os.environ.get("RTMW_ONNX_PATH", "/workspace/rtmw_weights/rtmw-x-384.onnx")
    device = os.environ.get("RTMW_DEVICE", "cuda")
    return Wholebody(det=det, det_input_size=(640, 640), pose=pose,
                     to_openpose=False, backend="onnxruntime", device=device)


def infer_video(model, frames: list[Path]):
    import cv2
    kps, scs = [], []
    W = H = None
    for p in frames:
        img = cv2.imread(str(p))
        if W is None:
            H, W = img.shape[:2]
        out = model(img)
        k, s = out[0], out[1]
        if k is None or len(k) == 0:
            kps.append(np.full((17, 2), np.nan))
            scs.append(np.zeros(17))
            continue
        body_s = np.asarray(s)[:, :17]
        best = int(np.argmax(body_s.mean(axis=1)))
        kps.append(np.asarray(k)[best, :17, :2].astype(float))
        scs.append(body_s[best].astype(float))
    return np.stack(kps), np.stack(scs), W, H


def pose_feature(kp_norm: np.ndarray, sc: np.ndarray) -> np.ndarray:
    """(T,17,2) 정규화 좌표 → (T,24) 자세 특징: 힙중심·몸통스케일 정규화 12관절."""
    idx = [J17.index(j) for j in BODY12]
    hip = (kp_norm[:, J17.index("left_hip")] + kp_norm[:, J17.index("right_hip")]) / 2
    sho = (kp_norm[:, J17.index("left_shoulder")] + kp_norm[:, J17.index("right_shoulder")]) / 2
    torso = np.linalg.norm(sho - hip, axis=1)
    torso = np.where(torso > 1e-4, torso, np.nanmedian(torso[torso > 1e-4]) if (torso > 1e-4).any() else 1.0)
    feat = (kp_norm[:, idx] - hip[:, None, :]) / torso[:, None, None]
    conf = sc[:, idx]
    feat = np.where(conf[..., None] >= CONF_MIN, feat, 0.0)
    return np.nan_to_num(feat.reshape(len(kp_norm), -1), nan=0.0)


def dtw_path(D: np.ndarray) -> list[tuple[int, int]]:
    Tu, Tr = D.shape
    INF = np.inf
    cost = np.full((Tu + 1, Tr + 1), INF)
    cost[0, 0] = 0.0
    for i in range(1, Tu + 1):
        j0, j1 = 1, Tr + 1
        for j in range(j0, j1):
            c = D[i - 1, j - 1]
            cost[i, j] = c + min(cost[i - 1, j - 1], cost[i - 1, j], cost[i, j - 1])
    path = []
    i, j = Tu, Tr
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        moves = [(cost[i - 1, j - 1], i - 1, j - 1), (cost[i - 1, j], i - 1, j), (cost[i, j - 1], i, j - 1)]
        _, i, j = min(moves)
    return path[::-1]


def smooth_curve(path: list[tuple[int, int]], Tu: int) -> np.ndarray:
    """path → user 프레임별 ref 프레임 곡선 (단조 + 이동평균)."""
    from collections import defaultdict
    agg = defaultdict(list)
    for u, r in path:
        agg[u].append(r)
    xs = np.array(sorted(agg))
    ys = np.array([np.mean(agg[u]) for u in xs])
    full = np.interp(np.arange(Tu), xs, ys)
    k = 7
    pad = np.pad(full, (k // 2, k // 2), mode="edge")
    sm = np.convolve(pad, np.ones(k) / k, mode="valid")
    return np.maximum.accumulate(sm)  # 단조 보장


def draw_skeleton(img_path: Path, kp: np.ndarray, sc: np.ndarray, out: Path):
    import cv2
    img = cv2.imread(str(img_path))
    for a, b in EDGES:
        if sc[a] >= CONF_MIN and sc[b] >= CONF_MIN:
            cv2.line(img, tuple(kp[a].astype(int)), tuple(kp[b].astype(int)), (80, 220, 80), 3)
    for j in range(17):
        if sc[j] >= CONF_MIN:
            cv2.circle(img, tuple(kp[j].astype(int)), 6, (51, 75, 255), -1)
    cv2.imwrite(str(out), img)


def hstack_save(paths: list[Path], out: Path):
    import cv2
    imgs = [cv2.imread(str(p)) for p in paths]
    h = min(i.shape[0] for i in imgs)
    imgs = [cv2.resize(i, (int(i.shape[1] * h / i.shape[0]), h)) for i in imgs]
    cv2.imwrite(str(out), np.hstack(imgs))


def s3_download(key: str, dst: Path):
    import boto3
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    boto3.client("s3").download_file(BUCKET, key, str(dst))


def process(motion: str, workdir: Path, model) -> None:
    ukey, rkey = JOBS[motion]
    mdir = workdir / motion
    doc = json.load(open(mdir / "doc.json"))
    records = doc["result"].get("deductionBreakdown", {}).get("records", [])
    moments_path = mdir / "moments.json"
    inject = json.load(open(moments_path)) if moments_path.exists() else {}

    uvid, rvid = mdir / "user.mp4", mdir / "ref.mp4"
    s3_download(ukey, uvid)
    s3_download(rkey, rvid)
    uframes = extract(uvid, mdir / "uf15")
    rframes = extract(rvid, mdir / "rf15")

    ukp, usc, UW, UH = infer_video(model, uframes)
    rkp, rsc, RW, RH = infer_video(model, rframes)
    ukn = ukp / np.array([UW, UH])
    rkn = rkp / np.array([RW, RH])

    fu = pose_feature(ukn, usc)
    fr = pose_feature(rkn, rsc)
    D = np.linalg.norm(fu[:, None, :] - fr[None, :, :], axis=2)
    curve = smooth_curve(dtw_path(D), len(fu))  # user frame -> ref frame

    verify = mdir / "verify"
    verify.mkdir(exist_ok=True)
    pairs = {}
    for rec in records:
        rid = rec["recordId"].split(":")[0]
        ut = rec.get("atVideoSec")
        if ut is None:
            ut = inject.get(rid, {}).get("atVideoSec")
        if ut is None:
            continue
        ui = int(np.clip(round(float(ut) * FPS), 0, len(fu) - 1))
        center = int(round(curve[ui]))
        lo, hi = max(0, center - int(2 * FPS)), min(len(fr), center + int(2 * FPS) + 1)
        ri = lo + int(np.argmin(D[ui, lo:hi]))
        joint = rec["criterion"].split("__")[-1]
        marker = None
        if joint in J17:
            ji = J17.index(joint)
            if usc[ui, ji] >= 0.5:
                marker = [float(ukn[ui, ji, 0]), float(ukn[ui, ji, 1])]
        pairs[rid] = {"atVideoSec": float(ut), "refVideoSec": ri / FPS,
                      "poseDist": float(D[ui, ri]), "joint": joint, "marker": marker,
                      "markerConf": float(usc[ui, J17.index(joint)]) if joint in J17 else None}
        # 짝 스틸 (스켈레톤 포함)
        up, rp = verify / f"pair_{rid}_u.jpg", verify / f"pair_{rid}_r.jpg"
        draw_skeleton(uframes[ui], ukp[ui], usc[ui], up)
        draw_skeleton(rframes[ri], rkp[ri], rsc[ri], rp)
        hstack_save([up, rp], verify / f"pair_{rid}.jpg")

    # 스켈레톤 검증 6장 (균등 샘플)
    for i in np.linspace(0, len(uframes) - 1, 6).astype(int):
        draw_skeleton(uframes[i], ukp[i], usc[i], verify / f"skel_u{i:04d}.jpg")

    out = {
        "motion": motion, "fps": FPS,
        "userSize": [UW, UH], "refSize": [RW, RH],
        "userFrames": len(fu), "refFrames": len(fr),
        "curveRefSec": [round(float(c) / FPS, 4) for c in curve],  # index = user frame @15fps
        "pairs": pairs,
        "userKp": np.round(ukn, 4).reshape(len(fu), -1).tolist(),
        "userScore": np.round(usc, 3).tolist(),
        "joints17": J17,
    }
    json.dump(out, open(mdir / "align.json", "w"))
    print(f"[{motion}] frames u={len(fu)} r={len(fr)} pairs={list(pairs)} -> align.json", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True, type=Path)
    ap.add_argument("--motions", default=",".join(JOBS))
    args = ap.parse_args()
    model = build_model()
    for m in args.motions.split(","):
        process(m.strip(), args.workdir, model)
    print("ALL_DONE")


if __name__ == "__main__":
    main()
