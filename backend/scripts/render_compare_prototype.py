"""Phase 35 — 서버측 정렬 합성 비교 영상 렌더러 (프로토타입).

user·ref 두 패널을 나란히 붙이고 감점 순간 정지·음성·자막까지 구운 단일 mp4 를 만든다.
앱은 이것을 재생만 한다 — 동기·스냅·재개·드리프트 계열이 재생기 차원에서 소멸(35-CONTEXT D-00~D-16).

렌더 문법 (2026-08-07 엘보 프로브 실측으로 확정):
  - 재생 구간: ref 패널 = motionAlignment.anchors 곡선(B) 워핑. 전 구간 DTW 워핑(A)은
    엘보 스틸 4/4 시각 기각 — 항상 뒤 국면으로 튐 (probe v2).
  - 감점 정지: 양패널 프리즈. ref 프레임 = fault_zoom pose-matched 짝(refVideoSec, C).
    프리즈 길이 = 음성 mp3 길이 + 0.4s (D-04).
  - 자막 = 음성과 같은 문장 소스(pipeline `_coach_audio_speech_text` import — lockstep 미러,
    V-A 재발 원리적 차단). 화면에 굽는다(D-07).
  - 부위 빨강 마커 = 정지 중 활성 관절만, keypointReport conf >= 0.5 게이트(D-09 저신뢰 억제).
  - 좌표 계약: keypointReport (x,y) = 전체 프레임 정규화 — 앱 KeypointOverlay 와 동일.
  - 시간 계약: atVideoSec/refVideoSec 초 값만 사용. fps 재계산 금지 (iwp 계약 승계 —
    ref 각도행렬 fps != 영상 fps 실측).
  - 원본 소리 제외, 코칭 음성만 먹싱(D-05/D-08). 감점 0 동작은 정지 0회 순수 재생.

실행 (로컬 프로토):
    cd backend && .venv/bin/python scripts/render_compare_prototype.py \
      --doc-json <analysis doc json> --user-video u.mp4 --ref-video r.mp4 \
      --audio-dir <mp3 dir: {rid}.mp3> --workdir <scratch> --out out.mp4
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
for _p in (BACKEND / "shared" / "python", BACKEND):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import imageio_ffmpeg  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS_OUT = 18.0
PANEL_H = 640
GAP = 6
BRAND = (255, 75, 51)  # #FF4B33
KP_CONF_MIN = 0.5
FREEZE_TAIL_S = 0.4
FONT_PATH = BACKEND.parent / "app" / "assets" / "fonts" / "Pretendard-SemiBold.ttf"


def _load_speech_text():
    """pipeline `_coach_audio_speech_text` 를 경로 import — 자막·음성 단일 소스(분기 0)."""
    path = BACKEND / "functions" / "pipeline" / "app.py"
    spec = importlib.util.spec_from_file_location("pipeline_app_for_render", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._coach_audio_speech_text


def mp3_duration_s(path: Path) -> float:
    err = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if not m:
        raise RuntimeError(f"duration parse 실패: {path}")
    h, mn, s = m.groups()
    return int(h) * 3600 + int(mn) * 60 + float(s)


def video_duration_s(path: Path) -> float:
    return mp3_duration_s(path)  # 같은 파서


def extract_frames(video: Path, outdir: Path) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    if not any(outdir.glob("*.png")):
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(video),
                        "-vf", f"fps={FPS_OUT},scale=-2:{PANEL_H}",
                        str(outdir / "%05d.png")], check=True)
    return len(list(outdir.glob("*.png")))


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def build_timeline(doc: dict, audio_dir: Path, moments: dict | None = None):
    """(user_sec, ref_sec, freeze|None) 프레임 열 + 음성 배치 계획.

    moments: 측정 순간이 없는 record(rid 키)에 주입할 유도 순간
      {"r00": {"atVideoSec": 1.67, "refVideoSec": 1.67}} — 프로토타입 한정
      (킵업 split 등 비전 산출 감점의 V-2 데이터측 유도값. 파이프라인 배선은 채택 후).
    """
    r = doc["result"]
    anch = r["motionAlignment"].get("anchors") or [0.0, 0.0, 1.0, 1.0]
    bu, br = np.array(anch[0::2], dtype=float), np.array(anch[1::2], dtype=float)

    def warp_b(t: float) -> float:
        return float(np.interp(t, bu, br))

    c_pairs = {fz["criterion"]: float(fz["refVideoSec"])
               for fz in r.get("faultZoomComparisons", [])
               if fz.get("criterion") and fz.get("refMatched") and fz.get("refVideoSec") is not None}

    moments = moments or {}
    enriched = []
    for rec in r.get("deductionBreakdown", {}).get("records", []):
        rid = rec["recordId"].split(":")[0]
        if rec.get("atVideoSec") is None and rid in moments:
            rec = {**rec, "atVideoSec": moments[rid]["atVideoSec"],
                   "_derivedRefSec": moments[rid].get("refVideoSec"), "_derived": True}
        if rec.get("atVideoSec") is not None:
            enriched.append(rec)
    records = sorted(enriched, key=lambda rec: rec["atVideoSec"])
    speech_text = _load_speech_text()

    kr = r["keypointReport"]
    kj = kr["joints"]
    kdata = np.asarray(kr["data"], dtype=float).reshape(kr["frames"], len(kj), 2)
    kconf = np.asarray(kr["confidence"], dtype=float).reshape(kr["frames"], len(kj))
    kfps = float(kr["fps"])

    freezes = []
    for rec in records:
        rid = rec["recordId"].split(":")[0]
        mp3 = audio_dir / f"{rid}.mp3"
        if not mp3.exists():
            print(f"[warn] mp3 없음 — 정지 스킵: {rid}")
            continue
        ut = float(rec["atVideoSec"])
        joint = rec["criterion"].split("__")[-1]
        marker = None
        if joint in kj:
            fi = min(kr["frames"] - 1, round(ut * kfps))
            ji = kj.index(joint)
            if float(kconf[fi, ji]) >= KP_CONF_MIN and np.isfinite(kdata[fi, ji]).all():
                marker = (float(kdata[fi, ji, 0]), float(kdata[fi, ji, 1]))
        if rec.get("_derived"):
            rt, src = float(rec.get("_derivedRefSec") or warp_b(ut)), "derived"
        elif rec["criterion"] in c_pairs:
            rt, src = c_pairs[rec["criterion"]], "C"
        else:
            rt, src = warp_b(ut), "B"
        freezes.append({
            "rid": rid, "ut": ut,
            "rt": rt,
            "pair_src": src,
            "dur": mp3_duration_s(mp3) + FREEZE_TAIL_S,
            "mp3": mp3, "joint": joint, "marker": marker,
            "text": speech_text(rec),
        })
    return warp_b, freezes


def render(doc_json: Path, user_video: Path, ref_video: Path, audio_dir: Path,
           workdir: Path, out: Path, moments_json: Path | None = None) -> dict:
    doc = json.load(open(doc_json))
    moments = json.load(open(moments_json)) if moments_json else None
    warp_b, freezes = build_timeline(doc, audio_dir, moments)

    udir, rdir, odir = workdir / "u18", workdir / "r18", workdir / "compose"
    nu = extract_frames(user_video, udir)
    nr = extract_frames(ref_video, rdir)
    odir.mkdir(parents=True, exist_ok=True)
    for f in odir.glob("*.png"):
        f.unlink()

    dur_user = video_duration_s(user_video)

    def uimg(sec: float) -> Image.Image:
        return Image.open(udir / f"{max(1, min(nu, round(sec * FPS_OUT) + 1)):05d}.png")

    def rimg(sec: float) -> Image.Image:
        return Image.open(rdir / f"{max(1, min(nr, round(sec * FPS_OUT) + 1)):05d}.png")

    font = ImageFont.truetype(str(FONT_PATH), 22)

    frames: list[tuple[float, float, dict | None]] = []
    audio_plan: list[tuple[Path, float]] = []  # (mp3, out_sec)
    t, k = 0.0, 0
    while t < dur_user:
        if k < len(freezes) and t >= freezes[k]["ut"]:
            fz = freezes[k]
            audio_plan.append((fz["mp3"], len(frames) / FPS_OUT))
            frames += [(fz["ut"], fz["rt"], fz)] * int(round(fz["dur"] * FPS_OUT))
            k += 1
        frames.append((t, warp_b(t), None))
        t += 1 / FPS_OUT

    first = uimg(0)
    W = first.width * 2 + GAP
    for i, (us, rs_, fz) in enumerate(frames):
        a, b = uimg(us), rimg(rs_)
        canvas = Image.new("RGB", (W, PANEL_H), (20, 18, 17))
        canvas.paste(a, (0, 0))
        canvas.paste(b, (a.width + GAP, 0))
        if fz is not None:
            d = ImageDraw.Draw(canvas, "RGBA")
            if fz["marker"] is not None:
                mx, my = fz["marker"][0] * a.width, fz["marker"][1] * PANEL_H
                d.ellipse([mx - 13, my - 13, mx + 13, my + 13], outline=BRAND + (255,), width=4)
                d.ellipse([mx - 4, my - 4, mx + 4, my + 4], fill=BRAND + (255,))
            lines = wrap_text(d, fz["text"], font, W - 48)[:3]
            band_h = 18 + 30 * len(lines)
            d.rectangle([0, PANEL_H - band_h, W, PANEL_H], fill=(15, 13, 12, 216))
            for li, line in enumerate(lines):
                d.text((24, PANEL_H - band_h + 10 + 30 * li), line, font=font, fill=(255, 255, 255))
        canvas.save(odir / f"{i + 1:06d}.png")

    silent = out.with_suffix(".video.mp4")
    subprocess.run([FF, "-y", "-loglevel", "error", "-framerate", str(FPS_OUT),
                    "-i", str(odir / "%06d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "21", "-g", "18", str(silent)], check=True)

    if audio_plan:
        cmd = [FF, "-y", "-loglevel", "error", "-i", str(silent)]
        for mp3, _ in audio_plan:
            cmd += ["-i", str(mp3)]
        parts, labels = [], []
        for idx, (_, at) in enumerate(audio_plan):
            ms = int(round(at * 1000))
            parts.append(f"[{idx + 1}]adelay={ms}|{ms}[a{idx}]")
            labels.append(f"[a{idx}]")
        fc = ";".join(parts) + f";{''.join(labels)}amix=inputs={len(labels)}:normalize=0[aout]"
        cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", str(out)]
        subprocess.run(cmd, check=True)
        silent.unlink()
    else:
        silent.rename(out)

    report = {
        "out": str(out),
        "outDurationS": round(len(frames) / FPS_OUT, 2),
        "userDurationS": round(dur_user, 2),
        "freezes": [
            {"rid": fz["rid"], "joint": fz["joint"], "userSec": fz["ut"],
             "refSec": round(fz["rt"], 2), "pairSrc": fz["pair_src"],
             "freezeS": round(fz["dur"], 2), "voiceStartOutS": round(at, 2),
             "marker": fz["marker"] is not None, "text": fz["text"]}
            for fz, (_, at) in zip(freezes, audio_plan)
        ],
    }
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc-json", required=True, type=Path)
    ap.add_argument("--user-video", required=True, type=Path)
    ap.add_argument("--ref-video", required=True, type=Path)
    ap.add_argument("--audio-dir", required=True, type=Path)
    ap.add_argument("--workdir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--moments-json", type=Path, default=None)
    args = ap.parse_args()
    report = render(args.doc_json, args.user_video, args.ref_video,
                    args.audio_dir, args.workdir, args.out, args.moments_json)
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
