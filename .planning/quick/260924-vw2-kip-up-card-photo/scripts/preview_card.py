"""vw2 카드 합성 미리보기 — 운영 함수(compare_render.circle_card_png / _circle_marks / person_bbox)에
로컬 영상 프레임(1080 높이, 영상 렌더와 같은 높이)과 저장 키포인트로 만든 align 모양 입력을 넣는다.
(운영 align 은 Pod 15fps 재추출 — 여기서는 저장 9fps/15fps 키포인트를 그 자리에 넣은 근사.)"""
import json, pathlib, subprocess, sys, io
import numpy as np
from PIL import Image
sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")
from sunity_shared.analysis import compare_render as cr
H = pathlib.Path(__file__).parent
fd = json.load(open(H / "fault_doc.json")); rd = json.load(open(H / "ref_doc.json"))
J17 = ["nose","left_eye","right_eye","left_ear","right_ear","left_shoulder","right_shoulder","left_elbow","right_elbow",
       "left_wrist","right_wrist","left_hip","right_hip","left_knee","right_knee","left_ankle","right_ankle"]
MAP = {"left_hand": "left_wrist", "right_hand": "right_wrist"}
def to_align(kr, stride, fps):
    J = kr["joints"]; T = kr["frames"]
    X = np.asarray(kr["data"], float).reshape(T, len(J), 2)[::stride]; C = np.asarray(kr["confidence"], float).reshape(T, len(J))[::stride]
    F = X.shape[0]
    kp = np.full((F, 17, 2), np.nan); sc = np.zeros((F, 17))
    for j, n in enumerate(J):
        n17 = MAP.get(n, n)
        if n17 in J17:
            kp[:, J17.index(n17)] = X[:, j]; sc[:, J17.index(n17)] = C[:, j]
    return kp, sc, F
ukp, usc, uF = to_align(fd["result"]["keypointReport"], 2, 9.9733)
rkp, rsc, rF = to_align(rd["referenceKeypointReport"], 1, 15.0)
# 두 트랙 fps 가 달라 align 두 벌로(각자 fps) — _kp_reader 는 align["fps"] 하나를 쓰므로 측별 dict
def al(kp, sc, F, fps, side):
    d = {"fps": fps, "joints17": J17, f"{side}Frames": F, f"{side}Kp": np.nan_to_num(kp).tolist(), f"{side}Score": sc.tolist()}
    return d
ua = al(ukp, usc, uF, 9.9733, "user"); ra = al(rkp, rsc, rF, 15.0, "ref")
ut, rt = 21 / 9.9733, 38 / 15.0
um = cr._circle_marks(cr._kp_reader(ua, "user"), ut, "left"); rm = cr._circle_marks(cr._kp_reader(ra, "ref"), rt, "left")
ub = cr.person_bbox(ua, "user", ut); rb = cr.person_bbox(ra, "ref", rt)
def frame(video, sec):
    out = subprocess.run([cr.FF, "-loglevel", "error", "-ss", f"{sec:.3f}", "-i", str(video), "-frames:v", "1",
                          "-vf", f"scale=-2:{cr.PANEL_H}", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(out)).convert("RGB")
png, plain = cr.circle_card_png(frame(H / "fault.mp4", ut), frame(H / "ref.mp4", rt), ub, rb, um, rm)
(H / "preview_card.png").write_bytes(png); (H / "preview_card_plain.png").write_bytes(plain)
print("marks user", um, "\nmarks ref", rm, "\nbox", ub, rb, Image.open(io.BytesIO(png)).size)
