"""이름표 골격 오버레이 — 좌표 오류와 크롭 폭 문제를 가르는 계측기 (2026-09-06).

배달된 카드가 쓴 그 프레임 위에 **저장된 관절 좌표 12개 전부**를 이름표와 함께 그린다.
지목 관절만 빨간 점. 그러면 원인이 세 갈래로 갈린다:
  A 빨간 점이 실제 그 부위 위      → 좌표 맞음 = 크롭/표시 문제
  B 골격 전체가 사람 몸 밖         → 자세 모델
  C 골격은 몸에 붙었는데 이름이 밀림 → 자세 모델(사지 뒤바뀜)

★왜 이 계측기가 필요한가: 좌표에 바짝 붙여(짧은 변 18%) 자른 뒤 "무슨 부위냐"를 묻는
  방식은 **좌표가 맞아도 옆 부위가 화면을 채우면 '틀림'으로 읽어** 두 원인을 못 가른다.
  09-06 오전에 그걸로 "36패널 중 14 좌표 오류"를 냈다가 이 계측기로 정정했다
  (학생 패널 불일치 5장 중 실제 좌표 오류는 2장).

★기준(정은지) 측 함정: `refFrameIdx` 는 rep(18fps upsample) 인덱스이고 프레임 배열은
  9fps PTS 라, rep9 를 배열에 그대로 넣으면 **계통적으로 이른 순간**이 나온다. 반드시
  `fault_zoom.ref_display_frame_index` 로 환산할 것. 09-06 에 이걸 빠뜨려 기준 14패널
  판정을 통째로 오염시켰다(심사자들이 "카드와 옷차림이 다르다"로 잡아냄).

실행:
    cd backend && FIREBASE_SA_PATH=../firebase-sa.json AWS_PROFILE=sunity-motion \\
      .venv/bin/python <이 파일> <uid> <출력디렉터리>

전제: 학생/기준 영상이 로컬에 있어야 한다 (아래 VID/REFVID 경로 — 없으면 S3 에서 받을 것).
출력: skel_{doc}_{idx}_{side}_{joint}.png (이름표 골격) · time_*.png (앞뒤 5프레임 띠)
      + <출력디렉터리>/rows.json (좌표·프레임·신뢰도 원장)
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

_R = "/Users/kimtaesung/Dev/SunityMotion"
sys.path.insert(0, _R + "/backend/shared/python")
sys.path.insert(0, _R + "/backend")

from sunity_shared import firestore_admin as fa           # noqa: E402
from sunity_shared.analysis import fault_zoom as fz       # noqa: E402
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor  # noqa: E402
import firebase_admin                                      # noqa: E402
from firebase_admin import credentials, firestore          # noqa: E402

UID = sys.argv[1] if len(sys.argv) > 1 else "verifyj8g0906"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/Users/Shared/sunity-skel"
VID = os.environ.get("VID_DIR", "/Users/Shared/sunity-vid")        # {motion}_user.mp4
REFVID = os.environ.get("REFVID_DIR", "/Users/Shared/sunity-refvid")  # {rid}.mp4
os.makedirs(OUT, exist_ok=True)

if not firebase_admin._apps:
    firebase_admin.initialize_app(credentials.Certificate(_R + "/firebase-sa.json"))
db = firestore.client()

MOT = {"ref-pdshape": "pdshape", "ref-climb": "climb", "ref-power-spin": "powerspin",
       "ref-elbow-twist-sister": "elbowtwist", "ref-kip-up": "kipup",
       "ref-peter-pan": "peterpan"}
BONES = [("left_shoulder", "right_shoulder"), ("left_shoulder", "left_elbow"),
         ("left_elbow", "left_hand"), ("right_shoulder", "right_elbow"),
         ("right_elbow", "right_hand"), ("left_shoulder", "left_hip"),
         ("right_shoulder", "right_hip"), ("left_hip", "right_hip"),
         ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
         ("right_hip", "right_knee"), ("right_knee", "right_ankle")]
SHORT = {"left_shoulder": "L-SHO", "right_shoulder": "R-SHO", "left_elbow": "L-ELB",
         "right_elbow": "R-ELB", "left_hand": "L-HND", "right_hand": "R-HND",
         "left_hip": "L-HIP", "right_hip": "R-HIP", "left_knee": "L-KNE",
         "right_knee": "R-KNE", "left_ankle": "L-ANK", "right_ankle": "R-ANK"}


def _font(sz):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(p, sz)
        except Exception:  # noqa: BLE001
            pass
    return ImageFont.load_default()


def vjoint(crit, joint):
    if crit and crit.startswith(fz.ANGLE_VS_REFERENCE_PREFIX):
        return crit[len(fz.ANGLE_VS_REFERENCE_PREFIX):]
    return joint


_ex: dict[str, np.ndarray] = {}


def frames(path):
    if path not in _ex:
        _ex[path] = FfmpegFrameExtractor(target_fps=9.0, max_side=640).extract(path)
    return _ex[path]


def pts(rep, ri):
    out = {}
    for j in SHORT:
        xy = fz._kp_xy(rep, ri, j)          # noqa: SLF001
        if xy is not None:
            out[j] = (float(xy[0]), float(xy[1]), fz._kp_conf(rep, ri, j))  # noqa: SLF001
    return out


def draw_skel(frame, p, target, scale=2):
    h, w = frame.shape[:2]
    im = Image.fromarray(frame).resize((w * scale, h * scale), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    W, H = im.size
    f = _font(max(11, int(H * 0.022)))

    def px(j):
        x, y, _ = p[j]
        return (x * W, y * H)

    for a, b in BONES:
        if a in p and b in p:
            d.line([px(a), px(b)], fill=(0, 200, 255), width=max(2, H // 300))
    for j, (x, y, c) in p.items():
        X, Y = x * W, y * H
        hit = (j == target)
        r = max(5, H // 90) if hit else max(3, H // 150)
        col = (255, 60, 40) if hit else (255, 235, 0)
        d.ellipse([X - r, Y - r, X + r, Y + r], fill=col, outline=(0, 0, 0), width=2)
        lab = SHORT[j] + (f" {c:.2f}" if c is not None else "")
        tb = d.textbbox((0, 0), lab, font=f)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        tx = min(max(0, X + r + 2), W - tw - 2)
        ty = min(max(0, Y - th - 2), H - th - 2)
        d.rectangle([tx - 2, ty - 2, tx + tw + 2, ty + th + 4],
                    fill=(150, 0, 0) if hit else (0, 0, 0))
        d.text((tx, ty), lab, font=f, fill=(255, 255, 255))
    return im


def strip(arr, p_by_frame, i9, target, n=2, size=300):
    ims = []
    for k in range(i9 - n, i9 + n + 1):
        k = max(0, min(k, arr.shape[0] - 1))
        fr = arr[k]
        h, w = fr.shape[:2]
        im = Image.fromarray(fr).resize((size, int(size * h / w)), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        W, H = im.size
        pk = p_by_frame.get(k) or {}
        if target in pk:
            x, y, _ = pk[target]
            r = max(5, H // 60)
            d.ellipse([x * W - r, y * H - r, x * W + r, y * H + r],
                      outline=(255, 60, 40), width=4)
        d.rectangle([0, 0, 70, 22], fill=(0, 0, 0))
        d.text((4, 3), f"{k - i9:+d}" if k != i9 else "  0", font=_font(16),
               fill=(255, 255, 0))
        ims.append(im)
    W = sum(i.size[0] for i in ims) + 8 * (len(ims) - 1)
    H = max(i.size[1] for i in ims)
    out = Image.new("RGB", (W, H), (20, 20, 20))
    x = 0
    for i in ims:
        out.paste(i, (x, 0))
        x += i.size[0] + 8
    return out


rows = []
docs = [(d.id, d.to_dict()) for d in
        db.collection("users").document(UID).collection("analyses").stream()]
print("docs", len(docs), flush=True)
for did, x in docs:
    short = did[:8]
    r = x.get("result") or {}
    rid = x.get("referenceMotionId")
    name = MOT.get(rid)
    if not name:
        continue
    kr = r.get("keypointReport") or {}
    rr = (fa.get_reference_motion(rid) or {}).get("referenceKeypointReport") or {}
    upath, rpath = f"{VID}/{name}_user.mp4", f"{REFVID}/{rid}.mp4"
    if not (os.path.exists(upath) and os.path.exists(rpath)):
        print("skip (video missing)", name, flush=True)
        continue
    uf, rf = frames(upath), frames(rpath)
    for i, c in enumerate(r.get("faultZoomComparisons") or []):
        crit = c.get("criterion")
        joint = vjoint(crit, c.get("joint"))
        for side in ("user", "ref"):
            rep, arr, kidx = ((kr, uf, "userFrameIdx") if side == "user"
                              else (rr, rf, "refFrameIdx"))
            ri = int(c.get(kidx) or 0)
            rfps = float(rep.get("fps") or 9.0)
            r9 = int(round(ri * 9.0 / rfps))
            if side == "ref":
                # ★타임베이스 보정 — 이걸 빼면 기준 프레임이 계통적으로 이르다.
                i9 = fz.ref_display_frame_index(
                    r9, int(arr.shape[0]), int(rep.get("frames") or 0), rfps, 9.0)
            else:
                i9 = r9
            i9 = max(0, min(i9, arr.shape[0] - 1))
            p = pts(rep, ri)
            if not p:
                continue
            tag = f"{short}_{i:02d}_{side}_{joint}"
            draw_skel(arr[i9], p, joint).save(f"{OUT}/skel_{tag}.png")
            pbf = {k: pts(rep, int(round(k * rfps / 9.0)))
                   for k in range(max(0, i9 - 2), min(arr.shape[0], i9 + 3))}
            strip(arr, pbf, i9, joint).save(f"{OUT}/time_{tag}.png")
            rows.append({"doc": short, "motion": name, "idx": i, "side": side,
                         "joint": joint, "criterion": crit, "repIdx": ri,
                         "repFps": rfps, "frame9": i9,
                         "conf": (None if joint not in p or p[joint][2] is None
                                  else round(p[joint][2], 3)),
                         "xy": (None if joint not in p else
                                [round(p[joint][0], 4), round(p[joint][1], 4)]),
                         "skel": f"skel_{tag}.png", "time": f"time_{tag}.png"})
            print(json.dumps(rows[-1], ensure_ascii=False), flush=True)

json.dump(rows, open(f"{OUT}/rows.json", "w"), ensure_ascii=False, indent=1)
print(f"\nwrote {len(rows)} panels -> {OUT}")
