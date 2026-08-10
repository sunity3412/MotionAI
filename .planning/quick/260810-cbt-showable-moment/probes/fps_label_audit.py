"""표시 순간의 초가 틀렸다 — fps 라벨 대 실제 솎음 rate 대조 (관찰 전용).

`frame_extractor.FfmpegFrameExtractor.extract` 는 **정수 step** 으로 프레임을 솎는다:

    step = max(1, round(src_fps / target_fps))

그래서 실제 산출 rate 는 `src_fps / step` 이고 `target_fps` 와 같지 않다. 30fps 원본에
target 9 를 주면 step 3 → **9.997fps** 다. 그런데 감점 record 의 시각은

    video_sec = frame_idx / _pipeline_frame_fps()   # = target_fps (요청값)

로 만든다(`pipeline/app.py:2535`, `:5224`). 즉 **저장된 초가 실제보다 11% 부풀려진다**
(30fps 원본). 렌더는 그 초로 정지 프레임을 뽑으므로(`build_align`: `round(atVideoSec*15)`)
사진은 감점을 실제로 측정한 순간이 아닌 곳에서 찍힌다.

이 스크립트가 재는 것:
  ① 영상 실물(ffprobe) → step → 실제 rate. 저장 트랙 프레임 수가 그 규칙으로
     재현되는가(강제 마지막 프레임 규칙 포함).
  ② record 별 저장 초 대 실제 초의 차 (초 · 15fps 프레임 · 클립 대비 %).
  ③ 값어치 — 실제 초로 옮기면 그림의 각도 차이·나머지몸 정렬이 어떻게 되는가.

usage: fps_label_audit.py <video_dir> [case...]
  video_dir = 원본 mp4 를 내려둔 디렉터리 (S3 키 basename 그대로).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))

from sunity_shared.analysis import compare_render as cr  # noqa: E402

ROOT = REPO / ".planning/phases/35-server-rendered-comparison-video/data"
TARGET_FPS = 9.0        # frame_extractor 기본값 = _pipeline_frame_fps() 이 쓰는 값
RECORD_FPS = 9.0        # record 의 atVideoSec = atFrameIdx / 이 값

# case → 사용자 영상 파일명 (data/README.md JOBS 표의 S3 키 basename)
USER_VIDEO = {
    "pdshapefault": "pdshapefault1785373695.mp4",
    "peterpan": "peterpanfault1785373695.mp4",
    "elbow": "elbow_fault.mp4",
    "powerspin": "powerspin_fault.mp4",
    "kipup": "kipup_fault.mp4",
}


def probe(path: Path) -> tuple[float, int, float]:
    """(src_fps, nb_frames, duration) — ffprobe 실측."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=avg_frame_rate,nb_frames", "-show_entries", "format=duration",
         "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    st = j["streams"][0]
    num, den = st["avg_frame_rate"].split("/")
    return float(num) / float(den), int(st["nb_frames"]), float(j["format"]["duration"])


def expected_frames(src_frames: int, step: int) -> int:
    """extract() 의 실제 산출 프레임 수 — 강제 마지막 프레임 규칙 포함."""
    idx = list(range(0, src_frames, step))
    last_seen = src_frames - 1
    return len(idx) + (1 if last_seen > idx[-1] else 0)


def run(vdir: Path, case: str):
    d = ROOT / case
    doc = json.load(open(d / "doc.json"))
    align = json.load(open(d / "align.json"))
    res = doc["result"]
    vid = vdir / USER_VIDEO.get(case, "")
    if not vid.exists():
        print(f"\n=== {case} === 사용자 영상 없음({vid.name}) — ② ③ 건너뜀")
        return
    src_fps, src_frames, dur = probe(vid)
    step = max(1, round(src_fps / TARGET_FPS))
    real_fps = src_fps / step
    n3d = int(res.get("joints3dFrames") or 0)
    exp = expected_frames(src_frames, step)

    print(f"\n=== {case} ===")
    print(f"  영상 실물   {dur:.3f}s · {src_frames}프레임 · {src_fps:.3f}fps")
    print(f"  솎음        step={step} → 실제 {real_fps:.3f}fps "
          f"(라벨 {TARGET_FPS:.1f}fps, 오차 {100*(TARGET_FPS/real_fps-1):+.1f}%)")
    print(f"  저장 트랙   joints3dFrames={n3d} / 규칙 예상={exp} "
          f"→ {'재현 O' if n3d == exp else '재현 X'}")

    curve = align.get("curveRefSec")
    afps = float(align["fps"])
    try:
        u_at, r_at = cr._kp_reader(align, "user"), cr._kp_reader(align, "ref")
    except (KeyError, ValueError):
        u_at = r_at = None
    joints = list(align["joints17"])

    def rest_align(ut, rt, tri):
        if u_at is None:
            return None
        from rest_body_alignment import pd_rest
        return pd_rest(u_at, r_at, joints, ut, rt, tri)

    def ref_at(ut):
        """align DTW 곡선으로 사용자 시각 → 기준 시각."""
        if not curve:
            return None
        i = int(np.clip(round(ut * afps), 0, len(curve) - 1))
        return float(curve[i])

    print(f"  {'rid':<5}{'관절':<15}{'at':>4}{'저장초':>8}{'실제초':>8}{'Δ':>7}"
          f"{'Δ프레임@15':>11}   그림 차이 (저장 → 실제)")
    for rec in (res.get("deductionBreakdown") or {}).get("records") or []:
        at = rec.get("atFrameIdx")
        crit = rec.get("criterion") or ""
        if at is None:
            continue
        rid = (rec.get("recordId") or "").split(":")[0]
        stored = float(at) / RECORD_FPS
        real = float(at) / real_fps
        dsec = stored - real
        jk = crit.split("__", 1)[1] if "angle_vs_reference__" in crit else None
        cell = "-"
        if jk in cr._ANGLE_TRIPLES and u_at is not None:
            tri = set(cr._ANGLE_TRIPLES[jk])
            vals = []
            for t in (stored, real):
                rt = ref_at(t)
                a = cr._joint_angle(u_at, jk, t, conf_min=cr.KP_CONF_MIN)
                b = (cr._joint_angle(r_at, jk, rt, conf_min=cr.KP_CONF_MIN)
                     if rt is not None else None)
                pr = rest_align(t, rt, tri) if rt is not None else None
                vals.append((None if (a is None or b is None) else abs(a - b), pr))
            def fmt(v):
                dv = "-" if v[0] is None else f"{v[0]:.1f}도"
                pr = "-" if v[1] is None else f"{v[1]:.3f}"
                return f"{dv}/정렬{pr}"
            cell = f"{fmt(vals[0])} → {fmt(vals[1])}"
        print(f"  {rid:<5}{(jk or crit)[:15]:<15}{at:>4}{stored:>7.2f}s{real:>7.2f}s"
              f"{dsec:>+6.2f}s{dsec*15:>10.1f}   {cell}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    vdir = Path(sys.argv[1])
    cases = sys.argv[2:] or ["elbow", "pdshapefault", "peterpan", "powerspin"]
    for c in cases:
        run(vdir, c)
