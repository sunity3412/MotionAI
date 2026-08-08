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

# 폴 문법 상수 (미세조정 2차, belle 08-08 마감: "폴에 가까운 부분에서 차이가 나는
# 것 — 각도를 재달라는 게 아님"). 임계는 전부 구조 유도 — 픽스처 curve-fit 금지:
#   τ_prox = 폴반폭/몸통 + 0.15 (팔꿈치는 뼈가 폴에 직접 닿음)
#   τ_grip = 폴반폭/몸통 + 0.20 (손이 폴을 쥐면 손목점은 축에서 손폭만큼 벗어남)
POLE_COV_MIN = 0.25       # 감지 fail-closed 하한 (프레임 높이 25% 미만 에지 = 폴 아님)
POLE_MARGIN = 0.15        # 유의미 마진 (몸통 단위) — ① user 대비·접촉 특정성·τ_prox 오프셋 공용
GRIP_OFFSET = 0.20        # τ_grip 해부학 오프셋 — 손이 폴을 쥐면 손목점은 축에서 손폭만큼 벗어남
POLE_DWELL_S = 0.5        # ref 접촉 체류 하한 — '붙임'(홀드) vs '스침'(회전 중 x 교차).
#   실측(pdshapefault r00): 통과 딥은 run 0.20s, 엘보 홀드는 1.60s — 넉넉히 가름.
GRIP_NEAR_S = 0.75        # user 접촉 개시가 cue 와 같은 순간이라 볼 허용 오차
GRIP_WIN_S = 2.5          # ref 창 반폭 (정렬곡선 기준 — 기존 가중 짝과 동일)


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


def _spread_series(align: dict, side: str = "user", conf_min: float = 0.3,
                   smooth: bool = True) -> np.ndarray:
    """프레임별 다리 벌림각 시계열 (표시 순간 유도용). 저신뢰 프레임은 NaN.

    conf_min 0.3 + 3프레임 이동평균 — 스플릿 절정에서 발목 신뢰도가 순간 떨어져
    진짜 피크(파워스핀 완전 스플릿)가 마스킹되던 것을 완화."""
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
    s = np.where(cmin >= conf_min, ang, np.nan)
    if not smooth:
        return s
    pad = np.pad(s, 1, mode="edge")
    sm = np.nanmean(np.stack([pad[:-2], pad[1:-1], pad[2:]]), axis=0)
    return np.where(np.isfinite(s), sm, np.nan)


_LIMB_GROUPS = {
    "arm": ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist"],
    "leg": ["left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"],
}


def _weighted_repair_pair(align: dict, ut: float, joint: str) -> float | None:
    """짝 재선정 — 큐 관절이 속한 사지군(팔/다리) 가중 자세거리 (belle: pdshape
    '정은지도 왼손 잡는 순간으로' — 팔 동작 국면까지 맞춘 짝).

    창 = 정렬 곡선 ±2.5s. 기존 짝과 0.15s 미만 차이면 None(안정 — 승인 짝 보호)."""
    if "refKp" not in align:
        return None
    aj = align["joints17"]
    afps = float(align["fps"])
    Fu, Fr = int(align["userFrames"]), int(align["refFrames"])
    ukp = np.asarray(align["userKp"], dtype=float).reshape(Fu, len(aj), 2)
    usc = np.asarray(align["userScore"], dtype=float)
    rkp = np.asarray(align["refKp"], dtype=float).reshape(Fr, len(aj), 2)
    rsc = np.asarray(align["refScore"], dtype=float)

    group = "arm" if joint in ("left_elbow", "right_elbow", "left_shoulder", "right_shoulder") else "leg"
    body12 = _LIMB_GROUPS["arm"] + _LIMB_GROUPS["leg"]
    w = np.array([2.5 if n in _LIMB_GROUPS[group] else 1.0 for n in body12])

    def feat(kp, sc):
        idx = [aj.index(n) for n in body12]
        hm = (kp[:, aj.index("left_hip")] + kp[:, aj.index("right_hip")]) / 2
        sh = (kp[:, aj.index("left_shoulder")] + kp[:, aj.index("right_shoulder")]) / 2
        torso = np.linalg.norm(sh - hm, axis=1)
        torso = np.where(torso > 1e-4, torso, np.nanmedian(torso[torso > 1e-4]) if (torso > 1e-4).any() else 1.0)
        f = (kp[:, idx] - hm[:, None, :]) / torso[:, None, None]
        conf = sc[:, idx]
        return np.nan_to_num(np.where(conf[..., None] >= 0.3, f, 0.0), nan=0.0)

    fu, fr = feat(ukp, usc), feat(rkp, rsc)
    ui = int(np.clip(round(ut * afps), 0, Fu - 1))
    curve = np.asarray(align["curveRefSec"], dtype=float)
    ci = curve[min(ui, len(curve) - 1)]
    lo = max(0, int((ci - 2.5) * afps))
    hi = min(Fr, int((ci + 2.5) * afps) + 1)
    if hi <= lo:
        return None
    d = np.sqrt(np.sum(((fu[ui][None, :, :] - fr[lo:hi]) ** 2) * w[None, :, None], axis=(1, 2)))
    return (lo + int(np.argmin(d))) / afps


def _column_coverage(img: Image.Image) -> np.ndarray:
    """컬럼별 수직 에지 커버리지 (0..1) — 폴 = 프레임 높이 대부분에 에지가 있는 컬럼.

    파일럿 영상 가정: 고정 카메라 + 화면상 수직 폴 (파이프라인 vertical fallback 동일).
    그레이스케일 수평 그래디언트 상위 8% 에지만 (pole_probe 실측 PASS 4/4 이식).
    PIL+numpy 만 — cv2 는 로컬 venv 에 없음 (import 금지)."""
    g = np.asarray(img.convert("L"), dtype=float)
    gx = np.abs(g[:, 2:] - g[:, :-2])
    thr = np.percentile(gx, 92)
    edge = gx >= max(thr, 8.0)
    return np.pad(edge.mean(axis=0), (1, 1), mode="edge")


def _detect_pole(frame_dir: Path, align: dict, side: str) -> dict | None:
    """폴 축선(x) 감지 — 사전 추출 30fps 프레임에서 균등 16장 샘플.

    프레임 중앙값으로 움직이는 사람을 상쇄 → 클러스터 후보 → 그립 프라이어
    (손목 conf>=0.5 프레임 x 중앙값이 후보폭 3배 이내인 후보 우선 — 창틀 등
    배경 수직 에지 오선택 방지). fail-closed: 커버리지 < POLE_COV_MIN → None
    (폴 표시 생략, 기존 링 마커 폴백). 결과는 workdir 에 JSON 캐시."""
    cache = frame_dir.parent / f"pole_{side}.json"
    if cache.exists():
        cached = json.load(open(cache))
        return cached or None
    frames = sorted(frame_dir.glob("*.jpg"))
    if not frames:
        return None
    sample = [frames[i] for i in np.linspace(0, len(frames) - 1, 16).astype(int)]
    covs = [_column_coverage(Image.open(p)) for p in sample]
    W = min(len(c) for c in covs)
    med = np.median(np.stack([c[:W] for c in covs]), axis=0)
    k = 3
    sm = np.convolve(np.pad(med, (k // 2, k // 2), mode="edge"), np.ones(k) / k, mode="valid")
    cands = []
    used = np.zeros(W, dtype=bool)
    for _ in range(3):
        masked = np.where(used, -1.0, sm)
        i = int(np.argmax(masked))
        if masked[i] <= 0.15:
            break
        lo = hi = i
        while lo > 0 and sm[lo - 1] >= sm[i] * 0.45 and not used[lo - 1]:
            lo -= 1
        while hi < W - 1 and sm[hi + 1] >= sm[i] * 0.45 and not used[hi + 1]:
            hi += 1
        used[max(0, lo - 6):min(W, hi + 7)] = True
        w_seg = sm[lo:hi + 1]
        centroid = float(np.sum(np.arange(lo, hi + 1) * w_seg) / (np.sum(w_seg) + 1e-9))
        cands.append({"xNorm": centroid / W, "coverage": float(sm[i]),
                      "halfWidthNorm": (hi - lo + 1) / 2 / W})
    chosen = None
    if cands:
        aj = align["joints17"]
        F = int(align[f"{side}Frames"])
        kp = np.asarray(align[f"{side}Kp"], dtype=float).reshape(F, len(aj), 2)
        sc = np.asarray(align[f"{side}Score"], dtype=float)
        wx: list[float] = []
        for w in ("left_wrist", "right_wrist"):
            j = aj.index(w)
            m = sc[:, j] >= 0.5
            wx.extend(kp[m, j, 0].tolist())
        if wx:
            wmed = float(np.median(wx))
            for c in cands:
                if abs(c["xNorm"] - wmed) <= 3 * (c["halfWidthNorm"] * 2):
                    chosen = c
                    break
        if chosen is None:
            chosen = cands[0]
        if chosen["coverage"] < POLE_COV_MIN:
            chosen = None
    json.dump(chosen, open(cache, "w"))
    return chosen


def _pole_gap_series(align: dict, side: str, joint: str, pole_x: float) -> tuple[np.ndarray, float]:
    """프레임별 |joint_x − pole_x|/몸통 비율 시계열 (conf<0.5 = NaN) + 몸통 px 중앙값.

    좌표→물리 스케일: kp 정규화 좌표를 userSize/refSize 로 픽셀 환산,
    torso = 어깨중점-힙중점 거리. 비율은 무차원 — 패널 간 비교 가능(몸통 단위)."""
    aj = align["joints17"]
    F = int(align[f"{side}Frames"])
    kp = np.asarray(align[f"{side}Kp"], dtype=float).reshape(F, len(aj), 2)
    sc = np.asarray(align[f"{side}Score"], dtype=float)
    W, H = align[f"{side}Size"]
    sh = (kp[:, aj.index("left_shoulder")] + kp[:, aj.index("right_shoulder")]) / 2
    hp = (kp[:, aj.index("left_hip")] + kp[:, aj.index("right_hip")]) / 2
    torso = np.linalg.norm((sh - hp) * np.array([W, H], dtype=float), axis=1)
    valid = torso > 1e-3
    tmed = float(np.nanmedian(torso[valid])) if valid.any() else 1.0
    j = aj.index(joint)
    gap = np.abs(kp[:, j, 0] - pole_x) * W
    ratio = gap / np.where(valid, torso, tmed)
    return np.where(sc[:, j] >= 0.5, ratio, np.nan), tmed


def _hipmid_gap_series(align: dict, side: str, pole_x: float) -> np.ndarray:
    """힙 중점의 폴 간격 비율 시계열 — 접촉 '특정성' 판정용 (양 힙 conf>=0.5)."""
    aj = align["joints17"]
    F = int(align[f"{side}Frames"])
    kp = np.asarray(align[f"{side}Kp"], dtype=float).reshape(F, len(aj), 2)
    sc = np.asarray(align[f"{side}Score"], dtype=float)
    W, H = align[f"{side}Size"]
    sh = (kp[:, aj.index("left_shoulder")] + kp[:, aj.index("right_shoulder")]) / 2
    hp = (kp[:, aj.index("left_hip")] + kp[:, aj.index("right_hip")]) / 2
    torso = np.linalg.norm((sh - hp) * np.array([W, H], dtype=float), axis=1)
    valid = torso > 1e-3
    tmed = float(np.nanmedian(torso[valid])) if valid.any() else 1.0
    conf = np.minimum(sc[:, aj.index("left_hip")], sc[:, aj.index("right_hip")])
    ratio = np.abs(hp[:, 0] - pole_x) * W / np.where(valid, torso, tmed)
    return np.where(conf >= 0.5, ratio, np.nan)


def _med3(s: np.ndarray) -> np.ndarray:
    """3프레임 중앙값 필터 — 15fps 지터 1프레임 스파이크 억제 (NaN 은 이웃으로)."""
    pad = np.pad(s, 1, mode="edge")
    out = np.full_like(s, np.nan)
    for i in range(len(s)):
        w = pad[i:i + 3]
        v = w[np.isfinite(w)]
        if len(v):
            out[i] = np.median(v)
    return out


def _contact_onsets(s: np.ndarray, tau: float, lo_f: int, hi_f: int) -> list[int]:
    """접촉 개시 프레임 목록 — 이탈(>2τ) 후 처음 ≤τ 로 들어와 3프레임 유지.

    창 시작부터 이미 접촉인 구간은 개시 아님(이탈→재접촉 첫 순간). 중앙값 필터
    선행 — med3 값이 2τ 를 넘으려면 생값 2프레임 이상 상승이 필요해 지터에 강함."""
    sm = _med3(s)
    res: list[int] = []
    departed = False
    for i in range(max(0, lo_f), min(hi_f, len(sm))):
        v = sm[i]
        if not np.isfinite(v):
            continue
        if v > 2 * tau:
            departed = True
        elif v <= tau and departed:
            hold = sm[i:i + 3]
            hv = hold[np.isfinite(hold)]
            if len(hv) >= 2 and (hv <= tau).all():
                res.append(i)
                departed = False
    return res


def _max_contact_overlap_s(s: np.ndarray, tau: float, lo_f: int, hi_f: int, afps: float) -> float:
    """창과 겹치는 접촉 run(med3 ≤ τ 연속) 최대 겹침 길이(초) — dwell 판정."""
    sm = _med3(s)
    best = 0
    start = None
    for i in range(len(sm) + 1):
        ok = i < len(sm) and np.isfinite(sm[i]) and sm[i] <= tau
        if ok and start is None:
            start = i
        elif not ok and start is not None:
            a, b = max(start, lo_f), min(i, hi_f)
            if b - a > best:
                best = b - a
            start = None
    return best / afps


def _pole_prox_pair(align: dict, ut: float, joint: str, poles: dict) -> dict | None:
    """① 폴-근접 (belle 08-08 마감 교정: "폴에 가까운 부분에서 차이가 나는 것 —
    각도를 재달라는 게 아님"). 팔꿈치 큐에서 기준=폴에 붙인 팔꿈치, 유저=떨어진
    팔꿈치를 폴 축선+간격 브래킷으로 보여준다.

    발동 (전부 데이터 판정 — 동작명 분기 없음):
      · criterion 관절이 팔꿈치 AND 양 패널 폴 감지 성공
      · ref 창(curve(atVideoSec)±2.5s) 내 팔꿈치 ratio min ≤ τ_prox
      · ref 접촉 체류(dwell) ≥ 0.5s — 회전 중 x 교차 스침 배제
        (실측: pdshapefault r00 통과 딥 run 0.20s vs 엘보 홀드 1.60s)
      · 접촉 특정성: rt 에서 힙중점 ratio − 팔꿈치 ratio ≥ 0.15 — belle 문장
        그대로 "폴에 가까운 '부분'": 팔꿈치가 접촉 부위려면 몸통보다 유의미하게
        가까워야 한다. 몸 전체가 폴선에 있는 진입 국면(실측: pdshapefault r01
        마진 +0.074 vs 엘보 홀드 +0.595)은 팔꿈치 교차가 부수적이므로 배제.
      · user 창(atVideoSec±2.5s) 내 ratio max ≥ ref_min + 0.15 (유의미 마진)

    표시 순간 (미세조정 1차 "양쪽 각자의 피크" 원칙 승계, 창 제한으로 엉뚱한
    국면 방지): ut = user 창 내 간격 최대 프레임, rt = ref 창 내 간격 최소 프레임.
    이 큐는 가중 짝 호출 생략(순간·짝 모두 폴 문법 소유) — 0.15s 승인 짝 보호
    규칙의 예외. 예외는 판정 조건 성립 한정(record/동작 한정 아님)이며 근거는
    belle 명시 교정이다.
    """
    if joint not in ("left_elbow", "right_elbow"):
        return None
    pu, pr = poles.get("user"), poles.get("ref")
    if not pu or not pr or "refKp" not in align:
        return None
    afps = float(align["fps"])
    curve = np.asarray(align["curveRefSec"], dtype=float)
    ui = int(np.clip(round(ut * afps), 0, len(curve) - 1))
    ct = float(curve[ui])

    su, _tmu = _pole_gap_series(align, "user", joint, pu["xNorm"])
    sr, tmr = _pole_gap_series(align, "ref", joint, pr["xNorm"])
    Wr, _ = align["refSize"]
    tau_prox_r = pr["halfWidthNorm"] * Wr / tmr + POLE_MARGIN

    ulo, uhi = max(0, int((ut - GRIP_WIN_S) * afps)), int((ut + GRIP_WIN_S) * afps) + 1
    rlo, rhi = max(0, int((ct - GRIP_WIN_S) * afps)), int((ct + GRIP_WIN_S) * afps) + 1
    uw, rw = su[ulo:uhi], sr[rlo:rhi]
    if not (np.isfinite(uw).any() and np.isfinite(rw).any()):
        return None
    rmin = float(np.nanmin(rw))
    umax = float(np.nanmax(uw))
    if rmin > tau_prox_r or umax < rmin + POLE_MARGIN:
        return None
    if _max_contact_overlap_s(sr, tau_prox_r, rlo, rhi, afps) < POLE_DWELL_S:
        return None

    ri = rlo + int(np.nanargmin(rw))
    rt = ri / afps
    # 접촉 특정성 — rt 이웃 3프레임 중앙값으로 팔꿈치 vs 힙중점 간격 비교.
    hs = _med3(_hipmid_gap_series(align, "ref", pr["xNorm"]))
    es = _med3(sr)
    ew, hw = es[max(0, ri - 1):ri + 2], hs[max(0, ri - 1):ri + 2]
    if not (np.isfinite(ew).any() and np.isfinite(hw).any()):
        return None
    if float(np.nanmedian(hw)) - float(np.nanmedian(ew)) < POLE_MARGIN:
        return None

    ut_new = (ulo + int(np.nanargmax(uw))) / afps

    # 그리기 페이로드 (양 패널 대칭) — 팔꿈치 링은 기존 신뢰 문법 승계.
    # 선택 프레임이 conf>=0.5 게이트 시계열에서 나오므로 실질 solid.
    viz: dict[str, dict | None] = {}
    for side, pole, t in (("user", pu, ut_new), ("ref", pr, rt)):
        kp_at = _kp_reader(align, side)
        p, c = kp_at(joint, t)
        if c < 0.35 or not np.isfinite(p).all():
            viz[side] = None
        else:
            viz[side] = {"poleX": float(pole["xNorm"]),
                         "joint": [float(p[0]), float(p[1])],
                         "style": "solid" if c >= 0.5 else "est"}
    # both-or-neither (fault_zoom 계약 승계) — 한쪽만 그려지면 비대칭 오독.
    if viz.get("user") is None or viz.get("ref") is None:
        return None
    return {"ut": ut_new, "rt": rt, "viz": viz}


def _grip_pair(align: dict, ut: float, joint: str, poles: dict, rid: str) -> float | None:
    """② 그립 (belle "정은지도 왼손 폴 잡는 순간으로") — 팔 큐에서 기준 정지를
    손목-폴 접촉 개시 순간으로 스냅. 표시는 기존 링 마커 문법 그대로(짝만 교정).

    발동 (전부 성립 시, ①미발동 후 평가):
      · criterion 관절이 팔(elbow/shoulder/wrist) AND 양 패널 폴 감지 성공
      · user 손목(좌/우 중 conf>=0.5) 중 cue 순간 ratio ≤ τ_grip 인 쪽 존재
        (둘 다면 ratio 작은 쪽)
      · user 그 손목의 접촉 개시가 |t−atVideoSec| ≤ 0.75s 안에 존재 — "그 순간이
        잡는 순간"임을 데이터로. 손이 처음부터 계속 잡고 있는 큐(엘보 계열)에
        오발동해 승인 장면을 깨는 것을 구조적으로 차단.
      · ref 같은 side 손목의 접촉 개시가 ref 창(curve(atVideoSec)±2.5s) 안에 존재

    실패(개시 못 찾음/신뢰 미달/user 개시 부재) → None (fail-closed, 기존 짝 유지)
    + stderr 로그 — 조용한 생략 금지, SUMMARY 박제 대상.
    """
    if joint not in ("left_elbow", "right_elbow", "left_shoulder", "right_shoulder",
                     "left_wrist", "right_wrist"):
        return None
    pu, pr = poles.get("user"), poles.get("ref")
    if not pu or not pr or "refKp" not in align:
        return None
    afps = float(align["fps"])
    curve = np.asarray(align["curveRefSec"], dtype=float)
    ui = int(np.clip(round(ut * afps), 0, len(curve) - 1))
    ct = float(curve[ui])
    Wu, _ = align["userSize"]
    Wr, _ = align["refSize"]

    best: tuple[str, float, np.ndarray] | None = None
    tau_gu = None
    for w in ("left_wrist", "right_wrist"):
        s_u, tmu = _pole_gap_series(align, "user", w, pu["xNorm"])
        tau_gu = pu["halfWidthNorm"] * Wu / tmu + GRIP_OFFSET
        v = s_u[min(ui, len(s_u) - 1)]
        if np.isfinite(v) and v <= tau_gu and (best is None or v < best[1]):
            best = (w, float(v), s_u)
    if best is None:
        return None
    w, v, s_u = best
    u_on = [o / afps for o in _contact_onsets(s_u, tau_gu, 0, len(s_u))]
    near = [o for o in u_on if abs(o - ut) <= GRIP_NEAR_S]
    s_r, tmr = _pole_gap_series(align, "ref", w, pr["xNorm"])
    tau_gr = pr["halfWidthNorm"] * Wr / tmr + GRIP_OFFSET
    rlo, rhi = max(0, int((ct - GRIP_WIN_S) * afps)), int((ct + GRIP_WIN_S) * afps) + 1
    r_on = _contact_onsets(s_r, tau_gr, rlo, rhi)
    if near and r_on:
        return r_on[0] / afps
    print(f"[grip-fail-closed] {rid} wrist={w} cue_ratio={v:.3f} "
          f"user_onsets={[round(o, 2) for o in u_on]} near_cue={[round(o, 2) for o in near]} "
          f"ref_onsets_in_win={[round(o / afps, 2) for o in r_on]} -> 기존 짝 유지",
          file=sys.stderr)
    return None


def _legs_angle_viz(kp_at, t: float) -> dict | None:
    """다리 사이각 표시 페이로드 — 꼭짓점(힙 중점)과 양다리 끝점(발목, 미덥으면 무릎).

    belle 4차: "점 표기 대신 다리 사이의 사이각 표시" — 다리벌림 계열 정지 전용.
    수치 배지가 아니라 **모양**(두 선 + 호)으로 벌림을 보여준다. 신뢰도 미달이면 None
    (fail-closed — 틀린 선을 긋느니 안 긋는다).
    """
    pts: dict[str, tuple[np.ndarray, float]] = {}
    for n in ("left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"):
        pts[n] = kp_at(n, t)
    if min(pts["left_hip"][1], pts["right_hip"][1]) < 0.35:
        return None
    vertex = (pts["left_hip"][0] + pts["right_hip"][0]) / 2
    ends = []
    for side in ("left", "right"):
        if pts[f"{side}_ankle"][1] >= 0.35 and np.isfinite(pts[f"{side}_ankle"][0]).all():
            ends.append(pts[f"{side}_ankle"][0])
        elif pts[f"{side}_knee"][1] >= 0.35 and np.isfinite(pts[f"{side}_knee"][0]).all():
            ends.append(pts[f"{side}_knee"][0])
        else:
            return None
    if not np.isfinite(vertex).all():
        return None
    v1, v2 = ends[0] - vertex, ends[1] - vertex
    cos = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9))
    deg = float(np.degrees(np.arccos(np.clip(cos, -1, 1))))
    conf = min(pts["left_hip"][1], pts["right_hip"][1],
               *(max(pts[f"{s}_ankle"][1], pts[f"{s}_knee"][1]) for s in ("left", "right")))
    return {"v": [float(vertex[0]), float(vertex[1])],
            "a": [float(ends[0][0]), float(ends[0][1])],
            "b": [float(ends[1][0]), float(ends[1][1])],
            # 수치는 벌림각만 병기(해석 자명: 클수록 더 벌림) — 단 신뢰 0.5 이상일 때만.
            "deg": deg if (conf >= 0.5 and 20.0 <= deg <= 179.5) else None}


def _armpit_angle_viz(kp_at, t: float, side: str) -> dict | None:
    """겨드랑이 사이각 — 꼭짓점=어깨, 두 선=팔꿈치·힙 방향 (belle: '겨드랑이가 더
    벌려져야 한다' 류 문장엔 사이각이 어울림). 규칙은 다리 사이각과 동일."""
    sh = kp_at(f"{side}_shoulder", t)
    el = kp_at(f"{side}_elbow", t)
    hp = kp_at(f"{side}_hip", t)
    conf = min(sh[1], el[1], hp[1])
    if conf < 0.35:
        return None
    pts = [sh[0], el[0], hp[0]]
    if not all(np.isfinite(p).all() for p in pts):
        return None
    v1, v2 = el[0] - sh[0], hp[0] - sh[0]
    cos = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9))
    deg = float(np.degrees(np.arccos(np.clip(cos, -1, 1))))
    return {"v": [float(sh[0][0]), float(sh[0][1])],
            "a": [float(el[0][0]), float(el[0][1])],
            "b": [float(hp[0][0]), float(hp[0][1])],
            "deg": deg if (conf >= 0.5 and 20.0 <= deg <= 179.5) else None}


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
                   align: dict | None = None, poles: dict | None = None,
                   text_overrides: dict | None = None,
                   pair_overrides: dict | None = None):
    """(user_sec, ref_sec, freeze|None) 프레임 열 + 음성 배치 계획.

    moments: 측정 순간이 없는 record(rid 키)에 주입할 유도 순간 (프로토타입 한정).
    align: p35_extract_align.py 산출(align.json) — 있으면 재생 곡선·정지 짝·마커를
      doc 리포트 대신 전부 이것으로 (Pod 재추출 데이터 = 뿌리 수리본).
    poles: {"user": 감지결과|None, "ref": ...} — 폴-근접·그립 판정 입력 (render 가
      사전 추출 프레임에서 감지해 전달).
    text_overrides: rid→문장 dict — 렌더 자막과 Polly 재합성이 같은 파일을 읽어
      자막=음성 lockstep 이 구조로 보장된다 (belle 08-08 엘보 '폴 근접' 문구).
    pair_overrides: rid→{refVideoSec, note} — 사람이 명시 지정한 기준 정지 순간.
      자동 짝 선정(피크·①폴·②그립·③가중)보다 우선, Pod 원본(align.json)은
      무수정. 출처는 pairSrc="override" 로 리포트에 남긴다 (belle 08-08 (a) 결정:
      pdshapefault r01 = 왼손 그립 개시 0.8s — x-투영으로 자동 검출 불가 실측 후
      명시 지정. 자동 그립 검출 경로는 fail-closed 로 존치 — 별도 명시 레이어).
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
        legs_viz = None
        pole_viz = None
        if "_alignRefSec" in rec:
            rt, src = float(rec["_alignRefSec"]), "align"
            u_at = _kp_reader(align, "user")
            r_at = _kp_reader(align, "ref") if "refKp" in align else None
            crit = rec["criterion"]

            legs_cue = crit == "split_angle" or (
                crit.startswith("angle_vs_reference__") and joint in ("left_hip", "right_hip"))
            armpit_cue = crit.startswith("angle_vs_reference__") and joint in (
                "left_shoulder", "right_shoulder")

            pair_ov = (pair_overrides or {}).get(rid)
            # 표시 순간 교정 — 벌림이 장면의 의미인 큐(split/신전/가위스플릿 힙)는
            # 잰 값의 순간이 아니라 **벌림 최대 국면**을 보여준다. 양쪽 각자의 피크
            # (유저 = 자기 시도의 절정, 기준 = 대표 찢기 국면). belle 5차: 엘보
            # "저 장면으로는 파악 어려움" · 파워스핀 "완전 스플릿 장면에서 표기돼야".
            if pair_ov is not None:
                # 명시 짝 오버라이드 — belle 지정이 자동 판정 전체보다 우선.
                # ut 는 기존 순간 유지(user 장면 무접촉), rt 만 명시값.
                rt, src = float(pair_ov["refVideoSec"]), "override"
            elif crit in ("split_angle", "leg_extension") or legs_cue:
                # 피크 탐색은 생값·게이트 0.35 — 스무딩·완화는 킵업 승인 피크(1.47s)를
                # 4.2s 로 밀어내는 퇴행 실측되어 철회.
                sp = _spread_series(align, "user", conf_min=0.35, smooth=False)
                if np.isfinite(sp).any():
                    ut = float(np.nanargmax(sp)) / float(align["fps"])
                    src = "align-peak"
                    if r_at is not None:
                        rsp = _spread_series(align, "ref")
                        if np.isfinite(rsp).any():
                            rt = float(np.nanargmax(rsp)) / float(align["fps"])
            elif crit.startswith("angle_vs_reference__"):
                # 관절 큐 판정 우선순위 (미세조정 2차): ① 폴-근접 → ② 그립 → ③ 가중 짝.
                # 순서 근거: 엘보 r00 은 ref 팔꿈치가 폴에 붙어(간격/몸통 0.002)
                # 폴-근접이 선점, 그립은 "잡는 순간" 이 데이터로 성립할 때만,
                # 나머지는 기존 사지군 가중 재선정 — 데이터가 가른다.
                pole_res = _pole_prox_pair(align, ut, joint, poles or {})
                if pole_res is not None:
                    ut, rt, src = pole_res["ut"], pole_res["rt"], "align-pole"
                    pole_viz = pole_res["viz"]
                else:
                    rt_grip = _grip_pair(align, ut, joint, poles or {},
                                         rec["recordId"].split(":")[0])
                    if rt_grip is not None:
                        # 그립 성공 — ut 는 atVideoSec 유지(user 장면은 belle 가
                        # 반려하지 않음), ref 정지만 접촉 개시 순간으로.
                        rt, src = rt_grip, "align-grip"
                    else:
                        # ③ 사지군 가중 재선정(미세조정 1차). 기존 짝과 0.15s
                        # 미만 차이는 유지(승인 짝 보호).
                        rt2 = _weighted_repair_pair(align, ut, joint)
                        if rt2 is not None and abs(rt2 - rt) >= 0.15:
                            rt, src = rt2, "align-w"
            markers = _align_markers(align, rec, ut)
            if pole_viz is not None:
                markers = []  # 폴 문법이 순간·표시 모두 소유 — 링은 pole_viz 가 양 패널에 그림

            # 사이각 그리기 — 벌림 문장(다리·겨드랑이·신전의 스플릿 맥락)에 두 선+호.
            # 수치는 신뢰 시 벌림각만. 관절 문장은 링만.
            if legs_cue or crit in ("split_angle", "leg_extension"):
                legs_viz = {"user": _legs_angle_viz(u_at, ut),
                            "ref": _legs_angle_viz(r_at, rt) if r_at is not None else None}
            elif armpit_cue:
                side = joint.split("_")[0]
                legs_viz = {"user": _armpit_angle_viz(u_at, ut, side),
                            "ref": _armpit_angle_viz(r_at, rt, side) if r_at is not None else None}
            # both-or-neither (fault_zoom 계약 승계) — 한쪽만 그려지면 비대칭 오독.
            if legs_viz is not None and (legs_viz.get("user") is None or legs_viz.get("ref") is None):
                legs_viz = None
            if legs_viz is not None and crit != "leg_extension":
                markers = []  # 점 대신 사이각 표시 (신전은 무릎 링 + 사이각 병행)
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
            "legs_viz": legs_viz,
            "pole_viz": pole_viz,
            # 오버라이드 우선 — elbow_text_overrides.json 을 렌더 자막과 Polly
            # 재합성(p35_audio.py synth)이 공용으로 읽어 lockstep 이 구조 보장.
            "text": (text_overrides or {}).get(rid) or speech_text(rec),
        })
    return warp_b, freezes


def render(doc_json: Path, user_video: Path, ref_video: Path, audio_dir: Path,
           workdir: Path, out: Path, moments_json: Path | None = None,
           align_json: Path | None = None, text_override_json: Path | None = None,
           probe: bool = False, pair_override_json: Path | None = None) -> dict:
    doc = json.load(open(doc_json))
    moments = json.load(open(moments_json)) if moments_json else None
    align = json.load(open(align_json)) if align_json else None
    text_overrides = json.load(open(text_override_json)) if text_override_json else None
    pair_overrides = json.load(open(pair_override_json)) if pair_override_json else None

    tag = f"{int(FPS_OUT)}_{PANEL_H}"
    udir, rdir, odir = workdir / f"u{tag}", workdir / f"r{tag}", workdir / f"compose{tag}"
    # 추출을 build_timeline 앞으로 — 폴 감지가 사전 추출 프레임을 읽는다 (캐시 멱등).
    nu = extract_frames(user_video, udir)
    nr = extract_frames(ref_video, rdir)

    poles = None
    if align is not None and "refKp" in align:
        poles = {"user": _detect_pole(udir, align, "user"),
                 "ref": _detect_pole(rdir, align, "ref")}

    warp_b, freezes = build_timeline(doc, audio_dir, moments, align, poles,
                                     text_overrides, pair_overrides)

    if probe:
        # 발동 집합 dry-run — 어떤 record 가 어느 경로(①폴/②그립/③가중/기존)로
        # 잡히는지 표로만 출력하고 렌더 없이 종료 (Task 2-4 선행 게이트).
        for fz in freezes:
            print(f"PROBE {fz['rid']} joint={fz['joint']} src={fz['pair_src']} "
                  f"ut={fz['ut']:.3f} rt={fz['rt']:.3f} "
                  f"poleViz={'y' if fz.get('pole_viz') else '-'}")
        return {"probe": True, "freezes": len(freezes)}

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
            lv = fz.get("legs_viz")
            if lv is not None:
                for panel_key, off, pw in (("user", 0, a.width), ("ref", a.width + GAP, b.width)):
                    v = lv.get(panel_key)
                    if not v:
                        continue
                    vx, vy = v["v"][0] * pw + off, v["v"][1] * PANEL_H
                    angs = []
                    ray_lens = []
                    for ek in ("a", "b"):
                        ex, ey = v[ek][0] * pw + off, v[ek][1] * PANEL_H
                        # 선 길이 상한 + 호 반경 적응 — 큰 각(170°대)에서 호가 몸을
                        # 가로지르던 것(belle 5차 파워스핀 어깨) 완화.
                        dx, dy = ex - vx, ey - vy
                        L = float((dx * dx + dy * dy) ** 0.5) or 1.0
                        maxL = 250 * S
                        if L > maxL:
                            ex, ey = vx + dx / L * maxL, vy + dy / L * maxL
                            L = maxL
                        ray_lens.append(L)
                        d.line([vx, vy, ex, ey], fill=BRAND + (235,), width=round(4 * S))
                        angs.append(float(np.degrees(np.arctan2(ey - vy, ex - vx))) % 360.0)
                    r_arc = round(min(56 * S, 0.5 * min(ray_lens)))
                    d0, d1 = sorted(angs)
                    if d1 - d0 > 180:
                        d0, d1 = d1, d0 + 360
                    d.arc([vx - r_arc, vy - r_arc, vx + r_arc, vy + r_arc],
                          start=d0, end=d1, fill=BRAND + (235,), width=round(4 * S))
                    if v.get("deg") is not None:
                        mid = np.radians((d0 + d1) / 2)
                        tx = vx + (r_arc + round(30 * S)) * np.cos(mid)
                        ty = vy + (r_arc + round(30 * S)) * np.sin(mid)
                        vfont = ImageFont.truetype(str(FONT_PATH), round(19 * S))
                        label = f"{v['deg']:.0f}°"
                        tw = d.textlength(label, font=vfont)
                        bx = float(np.clip(tx - tw / 2, off + 4, off + pw - tw - round(18 * S)))
                        by = float(np.clip(ty - round(14 * S), 4, PANEL_H - round(44 * S)))
                        d.rounded_rectangle([bx - round(7 * S), by - round(3 * S),
                                             bx + tw + round(7 * S), by + round(27 * S)],
                                            radius=round(7 * S), fill=(15, 13, 12, 200))
                        d.text((bx, by), label, font=vfont, fill=(255, 255, 255))
            pv = fz.get("pole_viz")
            if pv is not None:
                # 폴-근접 문법 (belle 08-08): 양 패널 대칭 — 폴 축선(세로선) +
                # 팔꿈치 링(기존 신뢰 문법) + 팔꿈치→폴 수평 간격 브래킷.
                # 수치 없음 — 수치 배지 철회 유지, 수치는 벌림각 전용(belle 4차 문법).
                for panel_key, off, pw in (("user", 0, a.width), ("ref", a.width + GAP, b.width)):
                    v = pv.get(panel_key)
                    if not v:
                        continue
                    px = v["poleX"] * pw + off
                    d.line([px, 0, px, PANEL_H], fill=BRAND + (140,), width=round(3 * S))
                    ex, ey = v["joint"][0] * pw + off, v["joint"][1] * PANEL_H
                    r_out, r_in = round(13 * S), round(4 * S)
                    if v["style"] == "est":
                        box = [ex - r_out, ey - r_out, ex + r_out, ey + r_out]
                        for a0 in range(0, 360, 45):
                            d.arc(box, start=a0, end=a0 + 27, fill=BRAND + (255,), width=round(3 * S))
                    else:
                        d.ellipse([ex - r_out, ey - r_out, ex + r_out, ey + r_out],
                                  outline=BRAND + (255,), width=round(4 * S))
                        d.ellipse([ex - r_in, ey - r_in, ex + r_in, ey + r_in], fill=BRAND + (255,))
                    # 간격 브래킷 — 팔꿈치 y 높이에서 팔꿈치 x↔폴 x 수평선 + 양끝 세로 틱.
                    # 기준(붙음)은 브래킷이 거의 0 으로 수렴 — '붙었다'가 모양으로 읽힘.
                    tick = round(10 * S)
                    d.line([ex, ey, px, ey], fill=BRAND + (235,), width=round(4 * S))
                    d.line([ex, ey - tick, ex, ey + tick], fill=BRAND + (235,), width=round(3 * S))
                    d.line([px, ey - tick, px, ey + tick], fill=BRAND + (235,), width=round(3 * S))
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
             "legsViz": {k: fz["legs_viz"].get(k) is not None for k in ("user", "ref")}
                        if fz.get("legs_viz") else None,
             # poleViz 요약(성립 여부 + poleX) — baseline↔v7 diff 게이트 관측 가능성.
             "poleViz": {k: round(fz["pole_viz"][k]["poleX"], 4)
                         for k in ("user", "ref") if fz["pole_viz"].get(k)}
                        if fz.get("pole_viz") else None,
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
    ap.add_argument("--text-override-json", type=Path, default=None,
                    help="rid→문장 오버라이드 (자막·음성 공용 단일 테이블)")
    ap.add_argument("--pair-override-json", type=Path, default=None,
                    help="rid→{refVideoSec, note} 명시 기준 정지 (자동 판정보다 우선, pairSrc=override)")
    ap.add_argument("--probe", action="store_true",
                    help="발동 집합 dry-run — 렌더 없이 record→경로 표만 출력")
    args = ap.parse_args()
    report = render(args.doc_json, args.user_video, args.ref_video,
                    args.audio_dir, args.workdir, args.out, args.moments_json,
                    args.align_json, args.text_override_json, args.probe,
                    args.pair_override_json)
    if not args.probe:
        print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
