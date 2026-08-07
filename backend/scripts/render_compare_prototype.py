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
# v2 (2026-08-07 belle "엉망진창" 반려 → 저더 실측 후): 18fps/640h 는 기준 패널
# 가다-서다 저더 + 저화질을 만들었다. 30fps + 1080h + 등속 ref 매핑으로 교정.
FPS_OUT = 30.0
PANEL_H = 1080
GAP = 8
BRAND = (255, 75, 51)  # #FF4B33
KP_CONF_MIN = 0.5
FREEZE_TAIL_S = 0.4
FADE_S = 0.17  # 정지 진입/복귀 시 기준 패널 크로스페이드(순간이동 완화)
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
    if not any(outdir.glob("*.jpg")):
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(video),
                        "-vf", f"fps={FPS_OUT},scale=-2:{PANEL_H}",
                        str(outdir / "%05d.jpg")], check=True)
    return len(list(outdir.glob("*.jpg")))


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


def _simplify_curve(xs: np.ndarray, ys: np.ndarray, max_knots: int = 6,
                    tol: float = 0.4) -> tuple[np.ndarray, np.ndarray]:
    """정렬 곡선을 소수 등속 선분으로 단순화 (Douglas-Peucker 유사, 재귀 분할).

    슬로프가 출렁이는 곡선을 그대로 30fps 리샘플하면 v1 저더가 재발한다.
    구간 안에서는 등속(부드러움), 구간 경계는 국면 전환(정렬) — 둘을 동시에.
    """
    knots = {0, len(xs) - 1}

    def split(a: int, b: int, depth: int):
        if depth <= 0 or b - a < 4:
            return
        yl = ys[a] + (ys[b] - ys[a]) * (xs[a:b + 1] - xs[a]) / max(xs[b] - xs[a], 1e-9)
        err = np.abs(ys[a:b + 1] - yl)
        i = int(np.argmax(err))
        if err[i] > tol:
            knots.add(a + i)
            split(a, a + i, depth - 1)
            split(a + i, b, depth - 1)

    split(0, len(xs) - 1, max_knots)
    ks = np.array(sorted(knots))
    return xs[ks], np.maximum.accumulate(ys[ks])


def _kp_reader(align: dict, side: str):
    """align 의 (user|ref) kp 를 초 단위 보간으로 읽는 헬퍼: kp_at(joint, t) -> (xy, conf)."""
    aj = align["joints17"]
    afps = float(align["fps"])
    F = int(align[f"{side}Frames"])
    kp = np.asarray(align[f"{side}Kp"], dtype=float).reshape(F, len(aj), 2)
    sc = np.asarray(align[f"{side}Score"], dtype=float)

    def kp_at(name: str, t: float) -> tuple[np.ndarray, float]:
        j = aj.index(name)
        x = t * afps
        i0 = int(np.clip(np.floor(x), 0, F - 1))
        i1 = min(i0 + 1, F - 1)
        a = float(np.clip(x - i0, 0.0, 1.0))
        return kp[i0, j] * (1 - a) + kp[i1, j] * a, float(min(sc[i0, j], sc[i1, j]))

    return kp_at


_ANGLE_TRIPLES = {
    "left_elbow": ("left_shoulder", "left_elbow", "left_wrist"),
    "right_elbow": ("right_shoulder", "right_elbow", "right_wrist"),
    "left_knee": ("left_hip", "left_knee", "left_ankle"),
    "right_knee": ("right_hip", "right_knee", "right_ankle"),
    "left_shoulder": ("left_elbow", "left_shoulder", "left_hip"),
    "right_shoulder": ("right_elbow", "right_shoulder", "right_hip"),
    "left_hip": ("left_shoulder", "left_hip", "left_knee"),
    "right_hip": ("right_shoulder", "right_hip", "right_knee"),
}


def _joint_angle(kp_at, joint: str, t: float, conf_min: float = 0.3) -> float | None:
    """관절각(도) — 배지 표기용. split_angle 은 발목-힙중점-발목."""
    if joint == "split":
        pts = []
        for n in ("left_ankle", "right_ankle", "left_hip", "right_hip"):
            p, c = kp_at(n, t)
            if c < conf_min or not np.isfinite(p).all():
                return None
            pts.append(p)
        la, ra = pts[0], pts[1]
        hm = (pts[2] + pts[3]) / 2
        v1, v2 = la - hm, ra - hm
    else:
        tri = _ANGLE_TRIPLES.get(joint)
        if tri is None:
            return None
        ps = []
        for n in tri:
            p, c = kp_at(n, t)
            if c < conf_min or not np.isfinite(p).all():
                return None
            ps.append(p)
        v1, v2 = ps[0] - ps[1], ps[2] - ps[1]
    cos = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9))
    return float(np.degrees(np.arccos(np.clip(cos, -1, 1))))


def _spread_series(align: dict, side: str = "user") -> np.ndarray:
    """프레임별 다리 벌림각 시계열 (표시 순간 유도용). 저신뢰 프레임은 NaN."""
    aj = align["joints17"]
    F = int(align[f"{side}Frames"])
    kp = np.asarray(align[f"{side}Kp"], dtype=float).reshape(F, len(aj), 2)
    sc = np.asarray(align[f"{side}Score"], dtype=float)
    idx = {n: aj.index(n) for n in ("left_ankle", "right_ankle", "left_hip", "right_hip")}
    hm = (kp[:, idx["left_hip"]] + kp[:, idx["right_hip"]]) / 2
    v1 = kp[:, idx["left_ankle"]] - hm
    v2 = kp[:, idx["right_ankle"]] - hm
    cos = np.sum(v1 * v2, axis=1) / (np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1) + 1e-9)
    ang = np.degrees(np.arccos(np.clip(cos, -1, 1)))
    cmin = np.minimum.reduce([sc[:, idx[k]] for k in idx])
    return np.where(cmin >= 0.35, ang, np.nan)


def _align_markers(align: dict, rec: dict, ut: float) -> list[tuple[float, float, str]]:
    """정지 마커 목록 [(x, y, style)] — belle 08-07 2차 판정 반영.

    규칙 (criterion 종류로 분기 — 동작명 분기 아님):
      angle_vs_reference__{hip}  → 허벅지 중간점(힙-무릎 중점). 힙 관절점은 "엉덩이
                                   표시"로 읽힘(belle 엘보 ① 반려).
      angle_vs_reference__{그외} → 해당 관절점.
      split_angle                → 양 무릎 (다리 벌림은 두 다리가 대상).
      leg_extension              → 덜 펴진(무릎각 작은) 쪽 무릎 — 문구가 짚는 그 무릎.
    좌표는 15fps 그리드 선형 보간(정확 순간 좌표 — belle 엘보 ③ "초미세조정").
    style: conf>=0.5 solid / >=0.35 est(점선) / 미만 표시 없음.
    """
    aj = align.get("joints17") or []
    if not aj:
        return []
    afps = float(align["fps"])
    F = int(align["userFrames"])
    akp = np.asarray(align["userKp"], dtype=float).reshape(F, len(aj), 2)
    asc = np.asarray(align["userScore"], dtype=float)

    def kp_at(name: str) -> tuple[np.ndarray, float]:
        j = aj.index(name)
        x = ut * afps
        i0 = int(np.clip(np.floor(x), 0, F - 1))
        i1 = min(i0 + 1, F - 1)
        a = float(np.clip(x - i0, 0.0, 1.0))
        return akp[i0, j] * (1 - a) + akp[i1, j] * a, float(min(asc[i0, j], asc[i1, j]))

    def knee_angle(side: str) -> float | None:
        pts = {}
        for part in ("hip", "knee", "ankle"):
            p, c = kp_at(f"{side}_{part}")
            if c < 0.3 or not np.isfinite(p).all():
                return None
            pts[part] = p
        v1, v2 = pts["hip"] - pts["knee"], pts["ankle"] - pts["knee"]
        cos = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9))
        return float(np.degrees(np.arccos(np.clip(cos, -1, 1))))

    crit = rec["criterion"]
    joint = crit.split("__")[-1]
    targets: list[tuple[str, str | None]] = []
    if crit == "split_angle":
        targets = [("left_knee", None), ("right_knee", None)]
    elif crit == "leg_extension":
        la, ra = knee_angle("left"), knee_angle("right")
        if la is not None or ra is not None:
            side = "left" if (ra is None or (la is not None and la <= ra)) else "right"
            targets = [(f"{side}_knee", None)]
    elif joint in ("left_hip", "right_hip"):
        targets = [(joint, f"{joint.split('_')[0]}_knee")]
    elif joint in aj:
        targets = [(joint, None)]

    markers: list[tuple[float, float, str]] = []
    for j1, j2 in targets:
        p1, c1 = kp_at(j1)
        if j2 is not None:
            p2, c2 = kp_at(j2)
            p, c = (p1 + p2) / 2, min(c1, c2)
        else:
            p, c = p1, c1
        if c >= 0.35 and np.isfinite(p).all():
            markers.append((float(p[0]), float(p[1]), "solid" if c >= 0.5 else "est"))
    return markers


def build_timeline(doc: dict, audio_dir: Path, moments: dict | None = None,
                   align: dict | None = None):
    """(user_sec, ref_sec, freeze|None) 프레임 열 + 음성 배치 계획.

    moments: 측정 순간이 없는 record(rid 키)에 주입할 유도 순간 (프로토타입 한정).
    align: p35_extract_align.py 산출(align.json) — 있으면 재생 곡선·정지 짝·마커를
      doc 리포트 대신 전부 이것으로 (Pod 재추출 데이터 = 뿌리 수리본).
    """
    r = doc["result"]

    if align is not None:
        afps = float(align["fps"])
        curve = np.asarray(align["curveRefSec"], dtype=float)
        xs = np.arange(len(curve)) / afps
        kx, ky = _simplify_curve(xs, curve)

        def warp_b(t: float) -> float:
            return float(np.interp(t, kx, ky))
    else:
        anch = r["motionAlignment"].get("anchors") or [0.0, 0.0, 1.0, 1.0]
        bu, br = np.array(anch[0::2], dtype=float), np.array(anch[1::2], dtype=float)
        # v2: 앵커 양끝 단일 등속 매핑 — 곡선 워핑 리샘플 저더(실측 8/62 반복) 방지.
        u0, u1 = float(bu[0]), float(bu[-1])
        r0, r1 = float(br[0]), float(br[-1])
        slope = (r1 - r0) / (u1 - u0) if u1 > u0 else 1.0

        def warp_b(t: float) -> float:
            return r0 + (t - u0) * slope

    c_pairs = {fz["criterion"]: float(fz["refVideoSec"])
               for fz in r.get("faultZoomComparisons", [])
               if fz.get("criterion") and fz.get("refMatched") and fz.get("refVideoSec") is not None}
    apairs = (align or {}).get("pairs", {})

    moments = moments or {}
    enriched = []
    for rec in r.get("deductionBreakdown", {}).get("records", []):
        rid = rec["recordId"].split(":")[0]
        if rid in apairs:
            rec = {**rec, "atVideoSec": apairs[rid]["atVideoSec"],
                   "_alignRefSec": apairs[rid]["refVideoSec"],
                   "_alignMarker": apairs[rid].get("marker")}
        elif rec.get("atVideoSec") is None and rid in moments:
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
        badge = None
        if "_alignRefSec" in rec:
            rt, src = float(rec["_alignRefSec"]), "align"
            u_at = _kp_reader(align, "user")
            r_at = _kp_reader(align, "ref") if "refKp" in align else None
            crit = rec["criterion"]

            # 표시 순간 교정 (belle 3차 — 파워스핀 "자막은 다리찢기인데 화면은 스핀 중"):
            # 복합 기준(split/신전)은 잰 값의 순간이 아니라 **벌림 최대 국면**이 장면의
            # 의미다. 유저 벌림각 시계열의 최대 근방(>=90%) 중 가장 이른 순간으로.
            if crit in ("split_angle", "leg_extension"):
                sp = _spread_series(align, "user")
                if np.isfinite(sp).any():
                    # 벌림 최대 순간 (earliest-90% 는 킵업의 승인된 순간을 밀어내는
                    # 과일반화라 철회 — belle 칭찬 짝 보존).
                    ut = float(np.nanargmax(sp)) / float(align["fps"])
                    src = "align-peak"
                    if r_at is not None:
                        # 기준 쪽은 **전체에서 벌림 최대**(기준의 대표 찢기 국면).
                        # 정렬 창으로 제한하면 유저 시도 시각대의 접힌 기준 프레임이
                        # 잡힌다(실측 3.33s — belle "화면이 이상함"의 원인).
                        rsp = _spread_series(align, "ref")
                        if np.isfinite(rsp).any():
                            rt = float(np.nanargmax(rsp)) / float(align["fps"])
            markers = _align_markers(align, rec, ut)

            # 각도 배지 (belle 3차 킵업 "각도 표기 있으면 좋겠다" + 엘보 차이 파악 보완):
            # 마커 관절의 관절각을 양 패널에 작은 배지로 — 내 각 vs 기준 각.
            if crit == "split_angle":
                bj = "split"
            elif crit == "leg_extension":
                # 덜 펴진(각 작은) 무릎 — 마커 선택 로직과 동일 기준
                best = None
                for side in ("left", "right"):
                    ang = _joint_angle(u_at, f"{side}_knee", ut)
                    if ang is not None and (best is None or ang < best[1]):
                        best = (f"{side}_knee", ang)
                bj = best[0] if best else None
            else:
                bj = joint
            if bj is not None and (bj in _ANGLE_TRIPLES or bj == "split"):
                ua_deg = _joint_angle(u_at, bj, ut)
                ra_deg = _joint_angle(r_at, bj, rt) if r_at is not None else None
                # 해부학 범위 게이트 — 겹침/가림 퇴화값(실측 3.9°, 2.7°) 차단.
                # 틀린 수치보다 없는 게 낫다.
                if ua_deg is not None and not (20.0 <= ua_deg <= 179.5):
                    ua_deg = None
                if ra_deg is not None and not (20.0 <= ra_deg <= 179.5):
                    ra_deg = None
                if ua_deg is not None:
                    if bj == "split":
                        up, _ = u_at("left_hip", ut)
                        up2, _ = u_at("right_hip", ut)
                        upos = (up + up2) / 2
                        rpos = None
                        if r_at is not None:
                            rp, _ = r_at("left_hip", rt)
                            rp2, _ = r_at("right_hip", rt)
                            rpos = (rp + rp2) / 2
                    else:
                        upos, _ = u_at(bj, ut)
                        rpos = r_at(bj, rt)[0] if r_at is not None else None
                    badge = {"userDeg": ua_deg, "refDeg": ra_deg,
                             "userPos": [float(upos[0]), float(upos[1])],
                             "refPos": [float(rpos[0]), float(rpos[1])] if rpos is not None and np.isfinite(rpos).all() else None}
        else:
            markers = []
            if joint in kj:
                fi = min(kr["frames"] - 1, round(ut * kfps))
                ji = kj.index(joint)
                if float(kconf[fi, ji]) >= KP_CONF_MIN and np.isfinite(kdata[fi, ji]).all():
                    markers = [(float(kdata[fi, ji, 0]), float(kdata[fi, ji, 1]), "solid")]
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
            "mp3": mp3, "joint": joint, "markers": markers,
            "badge": badge,
            "text": speech_text(rec),
        })
    return warp_b, freezes


def render(doc_json: Path, user_video: Path, ref_video: Path, audio_dir: Path,
           workdir: Path, out: Path, moments_json: Path | None = None,
           align_json: Path | None = None) -> dict:
    doc = json.load(open(doc_json))
    moments = json.load(open(moments_json)) if moments_json else None
    align = json.load(open(align_json)) if align_json else None
    warp_b, freezes = build_timeline(doc, audio_dir, moments, align)

    tag = f"{int(FPS_OUT)}_{PANEL_H}"
    udir, rdir, odir = workdir / f"u{tag}", workdir / f"r{tag}", workdir / f"compose{tag}"
    nu = extract_frames(user_video, udir)
    nr = extract_frames(ref_video, rdir)
    odir.mkdir(parents=True, exist_ok=True)
    for f in odir.glob("*.jpg"):
        f.unlink()

    dur_user = video_duration_s(user_video)

    # 순간이 영상 끝을 넘는 record(피터팬 실측: 6.44s vs 영상 6.1s — 파이프라인 rep
    # 도메인 산물) → 마지막 재생 가능 지점으로 클램프. 정지 소실(조용한 탈락) 금지.
    for fz in freezes:
        if fz["ut"] >= dur_user - 0.1:
            print(f"[clamp] {fz['rid']} atVideoSec {fz['ut']:.2f}s -> {dur_user - 0.2:.2f}s (영상 {dur_user:.2f}s)",
                  file=sys.stderr)
            fz["ut"] = max(0.0, dur_user - 0.2)
    freezes.sort(key=lambda f: f["ut"])

    def uimg(sec: float) -> Image.Image:
        return Image.open(udir / f"{max(1, min(nu, round(sec * FPS_OUT) + 1)):05d}.jpg")

    def rimg(sec: float) -> Image.Image:
        return Image.open(rdir / f"{max(1, min(nr, round(sec * FPS_OUT) + 1)):05d}.jpg")

    S = PANEL_H / 640.0
    font = ImageFont.truetype(str(FONT_PATH), round(22 * S))
    line_h, pad = round(30 * S), round(24 * S)

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

    # 마지막 정지 뒤 남은 재생이 1.5s 미만이면(감점 순간이 영상 끝 — 피터팬 belle
    # "멈춘 채 끝난다" 반려) 정지 후 처음부터 한 번 더 순수 재생 — "멈췄다가 틀기".
    if freezes and (dur_user - freezes[-1]["ut"]) < 1.5:
        t2 = 0.0
        while t2 < dur_user:
            frames.append((t2, warp_b(t2), None))
            t2 += 1 / FPS_OUT

    # 기준 패널 크로스페이드 계획 — 정지 진입/복귀 순간의 순간이동 완화 (v2).
    n_fade = max(1, int(round(FADE_S * FPS_OUT)))
    ref_blend: dict[int, tuple[float, float, float]] = {}  # i -> (from_sec, to_sec, alpha)
    for i in range(1, len(frames)):
        prev_fz, cur_fz = frames[i - 1][2], frames[i][2]
        if (prev_fz is None) != (cur_fz is None):
            frm, to = frames[i - 1][1], frames[i][1]
            for k2 in range(min(n_fade, len(frames) - i)):
                ref_blend[i + k2] = (frm, frames[i + k2][1], (k2 + 1) / n_fade)

    first = uimg(0)
    W = first.width * 2 + GAP
    for i, (us, rs_, fz) in enumerate(frames):
        a = uimg(us)
        if i in ref_blend:
            frm, to, alpha = ref_blend[i]
            b = Image.blend(rimg(frm), rimg(to), alpha)
        else:
            b = rimg(rs_)
        canvas = Image.new("RGB", (W, PANEL_H), (20, 18, 17))
        canvas.paste(a, (0, 0))
        canvas.paste(b, (a.width + GAP, 0))
        if fz is not None:
            d = ImageDraw.Draw(canvas, "RGBA")
            bd = fz.get("badge")
            if bd is not None:
                bfont = ImageFont.truetype(str(FONT_PATH), round(17 * S))

                def draw_badge(x_px: float, y_px: float, deg: float):
                    label = f"{deg:.0f}°"
                    tw = d.textlength(label, font=bfont)
                    bx = min(max(x_px + round(18 * S), 4), W - tw - round(20 * S))
                    by = min(max(y_px - round(34 * S), 4), PANEL_H - round(40 * S))
                    d.rounded_rectangle([bx, by, bx + tw + round(16 * S), by + round(28 * S)],
                                        radius=round(8 * S), fill=(15, 13, 12, 200))
                    d.text((bx + round(8 * S), by + round(4 * S)), label, font=bfont, fill=(255, 255, 255))

                if bd.get("userDeg") is not None and bd.get("userPos"):
                    draw_badge(bd["userPos"][0] * a.width, bd["userPos"][1] * PANEL_H, bd["userDeg"])
                if bd.get("refDeg") is not None and bd.get("refPos"):
                    draw_badge(a.width + GAP + bd["refPos"][0] * b.width, bd["refPos"][1] * PANEL_H, bd["refDeg"])
            for mx_n, my_n, style in fz.get("markers") or []:
                mx, my = mx_n * a.width, my_n * PANEL_H
                r_out, r_in = round(13 * S), round(4 * S)
                if style == "est":
                    # 추정(저신뢰) — 속 빈 점선 링: 45도 간격 호 8개, 중심점 없음
                    box = [mx - r_out, my - r_out, mx + r_out, my + r_out]
                    for a0 in range(0, 360, 45):
                        d.arc(box, start=a0, end=a0 + 27, fill=BRAND + (255,), width=round(3 * S))
                else:
                    d.ellipse([mx - r_out, my - r_out, mx + r_out, my + r_out],
                              outline=BRAND + (255,), width=round(4 * S))
                    d.ellipse([mx - r_in, my - r_in, mx + r_in, my + r_in], fill=BRAND + (255,))
            lines = wrap_text(d, fz["text"], font, W - 2 * pad)[:3]
            band_h = round(18 * S) + line_h * len(lines)
            d.rectangle([0, PANEL_H - band_h, W, PANEL_H], fill=(15, 13, 12, 216))
            for li, line in enumerate(lines):
                d.text((pad, PANEL_H - band_h + round(10 * S) + line_h * li),
                       line, font=font, fill=(255, 255, 255))
        canvas.save(odir / f"{i + 1:06d}.jpg", quality=92)

    silent = out.with_suffix(".video.mp4")
    subprocess.run([FF, "-y", "-loglevel", "error", "-framerate", str(FPS_OUT),
                    "-i", str(odir / "%06d.jpg"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "20", "-g", str(int(FPS_OUT)), "-movflags", "+faststart", str(silent)], check=True)

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
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)
        silent.unlink()
    else:
        silent.rename(out)

    report = {
        "out": str(out),
        "outDurationS": round(len(frames) / FPS_OUT, 2),
        "userDurationS": round(dur_user, 2),
        "expectedFreezes": len(freezes),
        "freezes": [
            {"rid": fz["rid"], "joint": fz["joint"], "userSec": fz["ut"],
             "refSec": round(fz["rt"], 2), "pairSrc": fz["pair_src"],
             "freezeS": round(fz["dur"], 2), "voiceStartOutS": round(at, 2),
             "markers": [m[2] for m in (fz.get("markers") or [])],
             "badge": ({"userDeg": round(fz["badge"]["userDeg"], 1),
                        "refDeg": round(fz["badge"]["refDeg"], 1) if fz["badge"].get("refDeg") is not None else None}
                       if fz.get("badge") else None),
             "text": fz["text"]}
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
    ap.add_argument("--align-json", type=Path, default=None)
    args = ap.parse_args()
    report = render(args.doc_json, args.user_video, args.ref_video,
                    args.audio_dir, args.workdir, args.out, args.moments_json,
                    args.align_json)
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
