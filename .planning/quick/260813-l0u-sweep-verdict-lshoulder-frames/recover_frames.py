"""recover_frames.py — quick-260813-l0u Task 2 회수 스크립트.

피디쉐입 왼어깨(r02, freeze u3.222/r2.00 라벨 공간) 답변 재료 회수:
  pair   : 캐시 영상(user/ref)에서 freeze 순간 전신 프레임 짝을 카드 패널
           content-match(크롭 -> 360px 리사이즈 -> grayscale 평균 절대 diff 최소)로
           기계 선정 + frame_match.json 기록 + 풀프레임 나란히 합성.
  v7scan : v7 승인 비교 영상(pdshape_v3.mp4, S3 GET 사본)에서 정지 run
           (인접 프레임 diff ~0 이 >= 0.8s) 전수 스캔 + run 대표 프레임 추출.
  v7pick : 육안 특정된 run 의 대표 프레임을 evidence 로 확정 복사.

제약: backend/·기존 하네스(verify_local.py, grammar_round.py, sweep_render.py)
무접촉 — import 0, ffmpeg + PIL + stdlib 만. Gemini 호출 0. Pod 무접촉.

프레임 선정 근거 (PLAN preverified):
- freeze 초는 ÷9.0 라벨 공간 — naive `-ss 3.222` 추출 금지, content-match 가 판정자.
- user 후보창 프레임 66~114 (30fps 실초 2.2~3.8s), ref 12~75 (0.4~2.5s).
- 크롭 박스 = measure.json crops["pdshapefault|angle_vs_reference__left_shoulder"]:
  user [x=326, y=1758, side=907] on 2160x3840 / ref [x=169, y=802, side=454] on 1080x1920.
- 카드 = 726x360, 좌 user 패널 (0..360) / 구분선 6px / 우 ref 패널 (366..726) —
  실행자 육안 확인 완료.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

FFMPEG = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"

REPO = Path("/Users/kimtaesung/Dev/SunityMotion")
QUICK = REPO / ".planning/quick/260813-l0u-sweep-verdict-lshoulder-frames"
EVIDENCE = QUICK / "evidence"
CARD = (
    REPO
    / ".planning/quick/260813-ivs-5/evidence/sweep_cards/pdshapefault"
    / "zoom_angle_vs_reference__left_shoulder.png"
)

SCRATCH = Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "ae166167-1abf-4754-9fe8-336a719ef9e2/scratchpad"
)
CACHE = SCRATCH / "approved_sweep" / "pdshapefault"
WORK = SCRATCH / "l0u_frames"

# 크롭 박스 (measure.json crops — preverified)
USER_BOX = (326, 1758, 907)  # x, y, side on 2160x3840
REF_BOX = (169, 802, 454)  # x, y, side on 1080x1920

# 후보창 (프레임 인덱스, 30fps 원본 — 라벨 skew 양방향 커버)
USER_WINDOW = (66, 114)
REF_WINDOW = (12, 75)

PANEL = 360  # 카드 패널 한 변 px
DIVIDER = 6  # 카드 중앙 구분선 px


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def _extract_window(video: Path, lo: int, hi: int, out_dir: Path, tag: str) -> None:
    """프레임 lo..hi (0-based 디코드 순서) 풀프레임 PNG 추출."""
    out_dir.mkdir(parents=True, exist_ok=True)
    _run(
        [
            FFMPEG,
            "-y",
            "-i",
            str(video),
            "-vf",
            f"select=between(n\\,{lo}\\,{hi})",
            "-vsync",
            "0",
            "-start_number",
            str(lo),
            str(out_dir / f"{tag}_%04d.png"),
        ]
    )


def _panel_diff(frame_png: Path, box: tuple[int, int, int], panel_img: Image.Image) -> float:
    """크롭 박스 -> 360px 리사이즈 -> grayscale 평균 절대 diff (카드 패널 대비)."""
    x, y, side = box
    im = Image.open(frame_png)
    crop = im.crop((x, y, x + side, y + side)).resize((PANEL, PANEL), Image.LANCZOS)
    a = crop.convert("L")
    b = panel_img
    pa, pb = a.load(), b.load()
    total = 0
    for j in range(PANEL):
        for i in range(PANEL):
            total += abs(pa[i, j] - pb[i, j])
    return total / (PANEL * PANEL)


def stage_pair() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    card = Image.open(CARD)
    assert card.size == (PANEL * 2 + DIVIDER, PANEL), f"card size {card.size}"
    user_panel = card.crop((0, 0, PANEL, PANEL)).convert("L")
    ref_panel = card.crop((PANEL + DIVIDER, 0, PANEL * 2 + DIVIDER, PANEL)).convert("L")

    user_dir = WORK / "user"
    ref_dir = WORK / "ref"
    if not any(user_dir.glob("user_*.png")):
        _extract_window(CACHE / "user.mp4", *USER_WINDOW, user_dir, "user")
    if not any(ref_dir.glob("ref_*.png")):
        _extract_window(CACHE / "ref.mp4", *REF_WINDOW, ref_dir, "ref")

    results: dict[str, dict] = {}
    selected: dict[str, dict] = {}
    for tag, d, box, panel, window in (
        ("user", user_dir, USER_BOX, user_panel, USER_WINDOW),
        ("ref", ref_dir, REF_BOX, ref_panel, REF_WINDOW),
    ):
        diffs: dict[int, float] = {}
        for png in sorted(d.glob(f"{tag}_*.png")):
            idx = int(png.stem.split("_")[1])
            diffs[idx] = round(_panel_diff(png, box, panel), 4)
        best = min(diffs, key=diffs.get)
        ordered = sorted(diffs.items(), key=lambda kv: kv[1])
        results[tag] = {
            "window_frames": list(window),
            "src_fps": 30.0,
            "diffs_by_frame": {str(k): v for k, v in sorted(diffs.items())},
            "top5": [{"frame": k, "diff": v} for k, v in ordered[:5]],
        }
        selected[tag] = {
            "frame": best,
            "diff": diffs[best],
            "real_sec_30fps": round(best / 30.0, 3),
            "neighbor_diffs": {
                str(n): diffs.get(n) for n in (best - 2, best - 1, best + 1, best + 2)
            },
        }
        print(f"[{tag}] best frame={best} diff={diffs[best]} top5={ordered[:5]}")

    match = {
        "criterion": "angle_vs_reference__left_shoulder",
        "record": "pdshapefault r02",
        "freeze_label_space_sec": {"user": 3.222, "ref": 2.00},
        "note_label_space": "freeze 초는 ÷9.0 라벨 공간 — naive 초 환산 추출 금지, "
        "content-match(카드 패널 대비 최소 diff)가 프레임 판정자 (PLAN preverified)",
        "crop_boxes": {"user": USER_BOX, "ref": REF_BOX},
        "card": str(CARD.relative_to(REPO)),
        "card_panels": {"user": [0, 0, 360, 360], "ref": [366, 0, 726, 360]},
        "candidates": results,
        "selected": selected,
        "croplines_hint": {"user_frame": 32, "ref_rep_idx": 15, "ref_video_idx": 20,
                           "note": "sweep_verdict.json cropLines 참고값 (보조) — "
                           "user_frame 은 rep(솎음) 공간 인덱스"},
    }
    (EVIDENCE / "frame_match.json").write_text(
        json.dumps(match, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # 육안 대조용: 선정 크롭 vs 카드 패널 나란히 (scratchpad — 비커밋)
    check = Image.new("RGB", (PANEL * 4 + DIVIDER * 3, PANEL), "white")
    ux, uy, us = USER_BOX
    rx, ry, rs = REF_BOX
    u_sel = Image.open(user_dir / f"user_{selected['user']['frame']:04d}.png")
    r_sel = Image.open(ref_dir / f"ref_{selected['ref']['frame']:04d}.png")
    check.paste(u_sel.crop((ux, uy, ux + us, uy + us)).resize((PANEL, PANEL)), (0, 0))
    check.paste(card.crop((0, 0, PANEL, PANEL)), (PANEL + DIVIDER, 0))
    check.paste(
        r_sel.crop((rx, ry, rx + rs, ry + rs)).resize((PANEL, PANEL)),
        (PANEL * 2 + DIVIDER * 2, 0),
    )
    check.paste(card.crop((PANEL + DIVIDER, 0, PANEL * 2 + DIVIDER, PANEL)),
                (PANEL * 3 + DIVIDER * 3, 0))
    check.save(WORK / "eye_check_crops_vs_card.png")

    # 풀프레임 짝 합성 (마크·자막 추가 0 — 원본 그대로, 같은 높이 스케일)
    out_h = 1200
    u_full = u_sel.resize((round(u_sel.width * out_h / u_sel.height), out_h), Image.LANCZOS)
    r_full = r_sel.resize((round(r_sel.width * out_h / r_sel.height), out_h), Image.LANCZOS)
    pair = Image.new("RGB", (u_full.width + 6 + r_full.width, out_h), "white")
    pair.paste(u_full, (0, 0))
    pair.paste(r_full, (u_full.width + 6, 0))
    pair.save(EVIDENCE / "lshoulder_fullframe_pair.png")
    print("wrote", EVIDENCE / "lshoulder_fullframe_pair.png")
    print("wrote", EVIDENCE / "frame_match.json")
    print("eye check:", WORK / "eye_check_crops_vs_card.png")


def stage_v7scan(threshold: float = 0.5, min_run_sec: float = 0.8) -> None:
    """v7 사본에서 정지 run 스캔 + run 대표 프레임 추출 (전부 scratchpad)."""
    v7 = SCRATCH / "pdshape_v3.mp4"
    small = WORK / "v7_small"
    small.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=r_frame_rate,nb_frames,width,height", "-of", "json", str(v7)],
        check=True, capture_output=True, text=True,
    )
    st = json.loads(probe.stdout)["streams"][0]
    num, den = st["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    print(f"v7: {st['width']}x{st['height']} fps={fps} nb_frames={st.get('nb_frames')}")

    if not any(small.glob("f_*.png")):
        _run([FFMPEG, "-y", "-i", str(v7), "-vf", "scale=180:-1,format=gray",
              "-vsync", "0", str(small / "f_%05d.png")])  # 1-based

    frames = sorted(small.glob("f_*.png"))
    prev = None
    diffs: list[float] = []
    for png in frames:
        im = Image.open(png)
        px = im.load()
        w, h = im.size
        if prev is not None:
            t = 0
            for j in range(0, h, 2):
                for i in range(0, w, 2):
                    t += abs(px[i, j] - prev[i, j])
            diffs.append(t / ((w // 2 + w % 2) * (h // 2 + h % 2)))
        prev = px

    min_run = int(round(min_run_sec * fps))
    runs = []
    start = None
    for i, dv in enumerate(diffs):
        if dv < threshold:
            if start is None:
                start = i
        else:
            if start is not None and i - start >= min_run:
                runs.append((start, i))
            start = None
    if start is not None and len(diffs) - start >= min_run:
        runs.append((start, len(diffs)))

    reps = WORK / "v7_runs"
    reps.mkdir(parents=True, exist_ok=True)
    run_meta = []
    for k, (a, b) in enumerate(runs):
        mid = (a + b) // 2
        out = reps / f"run{k:02d}_frame{mid:05d}.png"
        _run([FFMPEG, "-y", "-i", str(v7), "-vf", f"select=eq(n\\,{mid})",
              "-vsync", "0", "-frames:v", "1", str(out)])
        run_meta.append({"run": k, "frames": [a, b], "sec": [round(a / fps, 2),
                        round(b / fps, 2)], "rep_frame": mid, "rep_png": str(out)})
        print(f"run {k}: frames {a}..{b} ({a/fps:.2f}s..{b/fps:.2f}s) rep={mid}")
    (WORK / "v7_runs.json").write_text(
        json.dumps({"fps": fps, "threshold": threshold, "min_run_sec": min_run_sec,
                    "runs": run_meta}, ensure_ascii=False, indent=1), encoding="utf-8")


def stage_v7pick(rep_png: str) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    Image.open(rep_png).save(EVIDENCE / "lshoulder_v7_freeze.png")
    print("wrote", EVIDENCE / "lshoulder_v7_freeze.png")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "pair"
    if stage == "pair":
        stage_pair()
    elif stage == "v7scan":
        thr = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
        stage_v7scan(threshold=thr)
    elif stage == "v7pick":
        stage_v7pick(sys.argv[2])
    else:
        raise SystemExit(f"unknown stage: {stage}")
