"""운영 FfmpegFrameExtractor 로 정지컷 — 게이트: 프레임 수 == 저장 각도 프레임 수."""
import sys, pathlib, json
import numpy as np
B = pathlib.Path("/Users/kimtaesung/Dev/SunityMotion/backend")
sys.path.insert(0, str(B / "shared" / "python"))
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
H = pathlib.Path(__file__).parent
fd = json.load(open(H / "fault_doc.json")); rd = json.load(open(H / "ref_doc.json"))
for name, fps, want in (("fault", 9.0, fd["anglesFrames"]), ("ref", 15.0, rd["anglesFrames"])):
    ex = FfmpegFrameExtractor(target_fps=fps, max_side=640)
    arr = ex.extract(str(H / f"{name}.mp4"))
    eff = ex.effective_fps_for(str(H / f"{name}.mp4"))
    print(name, arr.shape, "eff fps", eff, "want", want, "→", "PASS" if len(arr) == want else "FAIL")
    np.save(H / f"{name}_frames.npy", arr)
