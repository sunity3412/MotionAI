import sys, time
import numpy as np
import imageio
sys.path.insert(0, "backend/shared/python")
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor as FrameExtractor, decimation_step
path = sys.argv[1]
fx = FrameExtractor()

t = time.perf_counter(); a = fx.extract(path); t_cur = time.perf_counter() - t

def extract_skip_resize(self, p):
    reader = imageio.get_reader(p)
    try:
        src_fps = float(reader.get_meta_data().get("fps") or 30.0)
        step = decimation_step(src_fps, self.target_fps) or 1
        frames, last_raw, last_seen, last_app = [], None, -1, -1
        for i, frame in enumerate(reader):
            last_seen = i
            rgb = np.asarray(frame)[:, :, :3]
            if i % step != 0:
                last_raw = rgb
                continue
            last_raw = None
            frames.append(self._resize(rgb)); last_app = i
    finally:
        reader.close()
    if last_raw is not None and last_seen > last_app:
        frames.append(self._resize(last_raw))
    return np.stack(frames).astype(np.uint8)

t = time.perf_counter(); b = extract_skip_resize(fx, path); t_new = time.perf_counter() - t
t = time.perf_counter()
r = imageio.get_reader(path); n = sum(1 for _ in r); r.close()
t_decode = time.perf_counter() - t
print(f"current={t_cur:.1f}s skip_resize={t_new:.1f}s decode_only={t_decode:.1f}s frames={n} out={a.shape} identical={a.shape==b.shape and np.array_equal(a,b)}")
