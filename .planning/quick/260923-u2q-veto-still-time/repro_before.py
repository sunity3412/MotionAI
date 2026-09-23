"""Gemini 에 보내는 정은지 still 이 학생 still 과 같은 순간인가 — 운영 함수로 재현.

재료: kip-up 정타 fixture(= 기준과 같은 테이크) 분석 doc 9fbe0cab 의 저장 각도 + 운영 기준 doc.
운영 경로 그대로: _deviation_against → match → fault_zoom._matched_ref_frame(match, u, r_n)
→ ref_frames[r_idx] (기준 영상을 9fps 목표로 추출한 프레임 배열).
판정: 같은 테이크라 올바른 짝이면 두 사진이 거의 같아야 한다 — 픽셀 차이로 기계 판정.
"""
import importlib.util, pathlib, sys
import numpy as np

REPO = pathlib.Path("/Users/kimtaesung/Dev/SunityMotion")
SP = pathlib.Path(__file__).parent
sys.path.insert(0, str(REPO / "backend/shared/python"))
spec = importlib.util.spec_from_file_location("pipeapp", str(REPO / "backend/functions/pipeline/app.py"))
app = importlib.util.module_from_spec(spec); spec.loader.exec_module(app)
from sunity_shared.analysis import fault_zoom
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
from PIL import Image
import boto3, firebase_admin
from firebase_admin import credentials, firestore

firebase_admin.initialize_app(credentials.Certificate(str(REPO / "firebase-sa.json")))
db = firestore.client()
s3 = boto3.Session(profile_name="sunity-motion").client("s3", region_name="ap-northeast-2")
B = "sunity-motion-pilot-videos"

stu_mp4, ref_mp4 = SP / "kip_correct.mp4", SP / "t_a.mp4"  # t_a.mp4 = reference/ref-kip-up.mp4
if not stu_mp4.exists():
    s3.download_file(B, "fixtures/phase15/kip-up/correct.mp4", str(stu_mp4))
if not ref_mp4.exists():
    s3.download_file(B, "reference/ref-kip-up.mp4", str(ref_mp4))

d = db.document("users/hohsgAIG1GSGvR9GRUtdgxYHBzT2/analyses/9fbe0cab92ec4c26a0e65d2c83151eae").get().to_dict()
rd = db.document("reference/ref-kip-up").get().to_dict()
nj = len(rd["anglesJointKeys"])
S = np.asarray(d["angles"], float).reshape(-1, nj)
fps_ref_angles = app._reference_angles_fps(rd)
_dev, m, _seg, a_ref = app._deviation_against(S, rd["angles"], nj, ref_fps=fps_ref_angles or None)

ext = FfmpegFrameExtractor(target_fps=9.0, max_side=640)
uf = ext.extract(str(stu_mp4)); rf = ext.extract(str(ref_mp4))
u_n, r_n = uf.shape[0], rf.shape[0]
eff_u, eff_r = ext.effective_fps_for(str(stu_mp4)), ext.effective_fps_for(str(ref_mp4))
print(f"학생 각도 {len(S)}프레임 · 학생 9fps 추출 {u_n}장({eff_u}fps)")
print(f"기준 각도 {len(a_ref)}프레임({fps_ref_angles:.2f}fps) · 기준 영상 9fps 추출 {r_n}장({eff_r}fps)")
print(f"DTW 창 ref [{m.ref_start},{m.ref_end}) user [{m.start},{m.end})\n")


def small(img):
    return np.asarray(Image.fromarray(img).convert("L").resize((96, 160)), dtype=float)


def diff(a, b):
    return float(np.mean(np.abs(small(a) - small(b))))


print(f"{'학생 still':>10s} | {'운영이 고른 기준 still':>22s} {'차이':>6s} | {'시각 맞춘 기준 still':>20s} {'차이':>6s} | 최선 {'':>3s}")
rows = []
for u in range(4, u_n - 2, 8):
    r_used = fault_zoom._matched_ref_frame(m, u, r_n)          # 운영 그대로
    if r_used is None:
        continue
    r_time = int(round(r_used / fps_ref_angles * eff_r))       # 각도 공간 → 영상 프레임 공간
    r_time = max(0, min(r_time, r_n - 1))
    best = int(np.argmin([diff(uf[u], rf[k]) for k in range(r_n)]))
    du, dt = diff(uf[u], rf[r_used]), diff(uf[u], rf[r_time])
    rows.append((u, r_used, du, r_time, dt, best))
    print(f"{u:>10d} | {r_used:>18d} ({r_used / eff_r:4.1f}초) {du:6.1f} | "
          f"{r_time:>16d} ({r_time / eff_r:4.1f}초) {dt:6.1f} | {best:>3d} (학생 {u / eff_u:4.1f}초)")
    Image.fromarray(np.concatenate([uf[u], rf[r_used], rf[r_time]], axis=1)).save(SP / f"veto_u{u:03d}.png")
ok_used = sum(1 for u, ru, du, rt, dt, b in rows if abs(ru - b) <= 1)
ok_time = sum(1 for u, ru, du, rt, dt, b in rows if abs(rt - b) <= 1)
print(f"\n가장 닮은 기준 프레임과 ±1 이내: 운영 {ok_used}/{len(rows)} · 시각 맞춤 {ok_time}/{len(rows)}")
