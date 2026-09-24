"""사진 후보 — 학생 | 정은지 나란히(같은 촬영 구도라 크기·바닥 보정 없이 같은 크롭), 왼팔·낮은발 동그라미, 각도 선 없음.
표식 좌표 = 저장 키포인트 그대로. 기계 점검 결과를 stdout 에."""
import json, pathlib, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
H = pathlib.Path(__file__).parent
fd = json.load(open(H / "fault_doc.json")); rd = json.load(open(H / "ref_doc.json")); facts = json.load(open(H / "facts.json"))
Fs = np.load(H / "fault_frames.npy"); Fr = np.load(H / "ref_frames.npy")
def kp(kr, stride):
    J = kr["joints"]; T = kr["frames"]; j = {n: i for i, n in enumerate(J)}
    X = np.asarray(kr["data"], float).reshape(T, len(J), 2)[::stride]; C = np.asarray(kr["confidence"], float).reshape(T, len(J))[::stride]
    return X, C, j
Xs, Cs, j = kp(fd["result"]["keypointReport"], 2); Xr, Cr, _ = kp(rd["referenceKeypointReport"], 1)
BRAND = (255, 75, 51)
SCALE = 3  # 그리기 해상도 배율(선이 깔끔하게)
u, r = map(int, sys.argv[1].split(",")); tag = sys.argv[2]
fl = max(facts["fault"]["stand"]["student"]["floor"], facts["fault"]["stand"]["ref"]["floor"])
top = min(Xs[u, [j["left_hand"], j["right_hand"]], 1].min(), Xr[r, [j["left_hand"], j["right_hand"]], 1].min())
y0, y1 = max(0.0, top - 0.04), min(1.0, fl + 0.09)
checks = []
def panel(img, X, C, idx, who):
    h, w = img.shape[:2]
    im = Image.fromarray(img).convert("RGB").resize((w * SCALE, h * SCALE), Image.LANCZOS)
    d = ImageDraw.Draw(im); W, Hh = im.size
    P = lambda n: np.array([X[idx, j[n], 0] * W, X[idx, j[n], 1] * Hh])
    arm = [P("left_shoulder"), P("left_elbow"), P("left_hand")]
    c = np.mean(arm, axis=0); rad = max(np.linalg.norm(p - c) for p in arm) + 14 * SCALE
    d.ellipse([c[0] - rad, c[1] - rad, c[0] + rad, c[1] + rad], outline=BRAND, width=4 * SCALE)
    ank = "left_ankle" if X[idx, j["left_ankle"], 1] > X[idx, j["right_ankle"], 1] else "right_ankle"
    fc = P(ank); fr = 26 * SCALE
    d.ellipse([fc[0] - fr, fc[1] - fr, fc[0] + fr, fc[1] + fr], outline=BRAND, width=4 * SCALE)
    lt = X[idx, j["left_hand"], 1] > X[idx, j["right_hand"], 1]
    conf = {n: round(float(C[idx, j[n]]), 2) for n in ("left_shoulder", "left_elbow", "left_hand", ank)}
    inside = all(0 <= v <= 1 for v in (X[idx, j[ank], 0], X[idx, j[ank], 1])) and (fc[1] / Hh) < y1
    checks.append(f"{who}: 표식 관절 신뢰도 {conf} · 왼손이 아래 손 {bool(lt)} · 낮은발={ank} · 발 원이 크롭 안 {bool(inside)}")
    return im.crop((0, int(y0 * Hh), W, int(y1 * Hh)))
a = panel(Fs[u], Xs, Cs, u, f"학생 f{u}"); b = panel(Fr[r], Xr, Cr, r, f"정은지 f{r}")
gap = 4 * SCALE
out = Image.new("RGB", (a.width + b.width + gap, a.height), "white")
out.paste(a, (0, 0)); out.paste(b, (a.width + gap, 0))
d = ImageDraw.Draw(out)
font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 15 * SCALE, index=6)
for x0, text in ((10 * SCALE, "내 영상"), (a.width + gap + 10 * SCALE, "정은지 선수")):
    tw = d.textlength(text, font=font); pad = 8 * SCALE
    d.rounded_rectangle([x0, 10 * SCALE, x0 + tw + 2 * pad, 10 * SCALE + 15 * SCALE + 2 * pad], radius=14 * SCALE, fill=(20, 20, 20))
    d.text((x0 + pad, 10 * SCALE + pad - 2 * SCALE), text, fill="white", font=font)
out = out.resize((out.width // SCALE * 2, out.height // SCALE * 2), Image.LANCZOS)
out.save(H / f"cand_{tag}.png")
print(tag, out.size, f"crop y {y0:.2f}~{y1:.2f}", f"학생 {u/9.9733:.2f}s · 정은지 {r/15:.2f}s")
print("\n".join(checks))
