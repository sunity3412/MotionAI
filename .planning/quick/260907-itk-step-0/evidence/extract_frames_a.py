"""측정 A 1단계 — 배달 렌더러가 본 것과 같은 픽셀을 뽑는다.

프로덕션 추출기(FfmpegFrameExtractor, 9fps/640) 그대로. 영상당 1회만 디코드.
프레임 원장은 roster_corrected.json 이 준다 — 여기서 인덱스 산술을 새로 하지 않는다.
"""
from __future__ import annotations
import sys, json, hashlib, os
sys.path.insert(0, '/Users/kimtaesung/Dev/SunityMotion/backend/shared/python')
from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
from PIL import Image

EV = '/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260907-itk-step-0/evidence'
OUT = os.path.join(EV, 'frames')
os.makedirs(OUT, exist_ok=True)

VIDEOS = {
  'user:21b1b7ed': '/Users/kimtaesung/Downloads/정은지 선수 추가 영상/피터팬(잘못된예시).mp4',
  'user:4e232c4a': '/Users/kimtaesung/Downloads/정은지 선수 추가 영상/pdshape(정확한명칭없음,잘못되예시).mp4',
  'user:5ae210fa': '/Users/kimtaesung/Downloads/정은지 선수 추가 영상/파워스핀(잘못된예시).mp4',
  'user:a559705f': '/Users/kimtaesung/Downloads/정은지 선수 추가 영상/클라임(잘못된예시).mp4',
  'user:d213622a': '/Users/kimtaesung/Downloads/정은지 선수 추가 영상/엘보트위스트시스터(잘못된예시).mp4',
  'ref:21b1b7ed': '/Users/Shared/sunity-ref-videos/ref-peter-pan.mp4',
  'ref:4e232c4a': '/Users/Shared/sunity-ref-videos/ref-pdshape.mp4',
  'ref:5ae210fa': '/Users/Shared/sunity-ref-videos/ref-power-spin.mp4',
  'ref:a559705f': '/Users/Shared/sunity-ref-videos/ref-climb.mp4',
  'ref:d213622a': '/Users/Shared/sunity-motion-260816-ill2-cache/ill2/videos/ref-elbow-twist-sister.mp4',
}

roster = json.load(open(os.path.join(EV, 'roster_corrected.json')))
need: dict[str, set[int]] = {k: set() for k in VIDEOS}
for r in roster:
    if not r.get('vertex_centered') or r.get('card_frac') is None:
        continue
    key = f"{r['side']}:{r['doc']}"
    idx = int(r['user_frame']) if r['side'] == 'user' else int(r['ref_video_idx'])
    need[key].add(idx)

ex = FfmpegFrameExtractor(target_fps=9.0, max_side=640)
manifest = {}
for key, path in VIDEOS.items():
    if not need[key]:
        continue
    size = os.path.getsize(path)
    frames = ex.extract(path)
    n = len(frames)
    entry = {'video_path': path, 'video_bytes': size, 'n_frames_9fps': n, 'saved': {}}
    for i in sorted(need[key]):
        if i >= n:
            entry['saved'][str(i)] = {'error': f'index {i} >= n_frames {n}'}
            continue
        arr = frames[i]  # (H, W, 3) RGB uint8
        H, W = int(arr.shape[0]), int(arr.shape[1])
        fn = f"{key.replace(':','_')}_f{i:04d}.png"
        Image.fromarray(arr).save(os.path.join(OUT, fn))
        entry['saved'][str(i)] = {'file': fn, 'W': W, 'H': H}
    manifest[key] = entry
    print(key, 'bytes=', size, 'n9=', n, 'saved', sorted(need[key]), flush=True)

json.dump(manifest, open(os.path.join(EV, 'frames_manifest_a.json'), 'w'), ensure_ascii=False, indent=1)
print('OK')
