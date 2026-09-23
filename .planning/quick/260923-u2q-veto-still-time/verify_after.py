"""수리 후 — 운영 함수 _build_selected_frame_pair 를 실제 영상·실제 추출기로 호출해
기준 still 이 학생 still 과 같은 순간인지 픽셀로 대조 (kip-up 정타 = 기준과 같은 테이크)."""
import importlib.util, pathlib, sys
import numpy as np
REPO = pathlib.Path("/Users/kimtaesung/Dev/SunityMotion"); SP = pathlib.Path(__file__).parent
sys.path.insert(0, str(REPO / "backend/shared/python"))
spec = importlib.util.spec_from_file_location("pipeapp", str(REPO / "backend/functions/pipeline/app.py"))
app = importlib.util.module_from_spec(spec); spec.loader.exec_module(app)
from PIL import Image
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
import firebase_admin
from firebase_admin import credentials, firestore
firebase_admin.initialize_app(credentials.Certificate(str(REPO / "firebase-sa.json")))
db = firestore.client()
import boto3
_s3 = boto3.Session(profile_name="sunity-motion").client("s3", region_name="ap-northeast-2")
for _k, _f in (("fixtures/phase15/kip-up/correct.mp4", "kip_correct.mp4"), ("reference/ref-kip-up.mp4", "t_a.mp4")):
    if not (SP / _f).exists():
        _s3.download_file("sunity-motion-pilot-videos", _k, str(SP / _f))
d = db.document("users/hohsgAIG1GSGvR9GRUtdgxYHBzT2/analyses/9fbe0cab92ec4c26a0e65d2c83151eae").get().to_dict()
rd = db.document("reference/ref-kip-up").get().to_dict()
nj = len(rd["anglesJointKeys"]); S = np.asarray(d["angles"], float).reshape(-1, nj)
fps = app._reference_angles_fps(rd)
_dev, m, _s, a_ref = app._deviation_against(S, rd["angles"], nj, ref_fps=fps or None)
uf = FfmpegFrameExtractor(9.0, 640).extract(str(SP / "kip_correct.mp4"))
def small(p): return np.asarray(Image.open(p).convert("L").resize((96, 160)), dtype=float)
ok = 0; n = 0
for u in range(4, 77, 8):
    for label, kw in (("수리 전(구 호출)", {}), ("수리 후", dict(reference_angles_len=len(a_ref), reference_angles_fps=fps))):
        pair = app._build_selected_frame_pair(user_video_path=str(SP / "kip_correct.mp4"),
            reference_video_path=str(SP / "t_a.mp4"), reference_dtw_match=m, user_frame_idx=u,
            cached_user_frames=uf, **kw)
        dpx = float(np.mean(np.abs(small(pair.student_frame_path) - small(pair.reference_frame_path))))
        if kw:
            n += 1; ok += dpx < 2.0
            print(f"u={u:2d}  {label}: 이미지 {pair.ref_image_idx:2d} · 각도 {pair.ref_frame_idx:3d}  픽셀차 {dpx:4.1f}")
        else:
            print(f"u={u:2d}  {label}: 이미지 {pair.ref_image_idx:2d} · 각도 {pair.ref_frame_idx:3d}  픽셀차 {dpx:4.1f}", end="   |   ")
        for p in pair.cleanup_paths: pathlib.Path(p).unlink(missing_ok=True)
print(f"\n수리 후 같은 순간(픽셀차 < 2): {ok}/{n}")
