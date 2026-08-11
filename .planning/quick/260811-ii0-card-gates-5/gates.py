#!/usr/bin/env python3
"""성립 게이트 순수 함수 3종 (quick-260811-ii0, Task 1) — 채점·운영 코드 무접촉.

CONTINUE-2026-08-11 프로세스 확정본의 게이트 층 (A1 홀드 / A2 짝 정합 / A3 기계 눈)
프로토타입. 동작명 분기 0 (D-41) — 모든 함수는 report/track 형상만 본다.

  · hold_gate   — 측정 순간의 robust 각속도(±3f Theil-Sen) < 임계. 측정불가 = FAIL.
  · pair_gate   — 포즈거리(fz.pose_distance, 기저 명시 고정) + 몸중심-폴거리 parity.
  · detect_pole_x — bz5 부록 D 방식 재구현: 배경 중앙값 프레임의 세로 에지 열 커버리지.
  · machine_eye — 관절 마킹 크롭 → Gemini(gemini-3.5-flash, temp 0, JSON) 판정.
                  좌우 해부학 이름 금지 — "표시된 부위"만 지시 (bz5 부록 C 설계).

report 형식 = 운영 keypointReport(joints/data/confidence/frames/fps) 그대로.
align.json(15fps RTMW17) 트랙은 align_to_report() 로 같은 형식으로 변환해 쓴다.
임계 출발값은 PLAN.md — 튜닝은 sweep_gates.py 가 승인 코퍼스 생존 조건으로 수행하고
이력을 보고서 표에 박제한다 (픽스처 curve-fit 금지).
"""

from __future__ import annotations

import base64
import io
import json
import math
import pathlib
import sys
import urllib.request
from dataclasses import dataclass, field

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "backend" / "shared" / "python"))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_ANGLES  # noqa: E402

# ── 임계 출발값 (PLAN.md — 근거 있는 단일 값, 튜닝 이력은 sweep 보고서 표) ────
HOLD_MAX_DPS = 60.0        # 홀드 판정 각속도 상한 (도/초) — PLAN 출발값
HOLD_HALF_WINDOW_F = 3     # ±3 프레임 (CONTINUE A1 명세)
HOLD_MIN_SAMPLES = 4       # 창 7표본 중 최소 유효 측정 수 — 미만 = 측정불가(FAIL)
HOLD_CONF_MIN = 0.35       # 각도 측정 좌표 신뢰 하한 — 렌더러 표시 게이트(0.35) 재사용
                           # (fz._KP_CONF_MIN 0.5 는 확정 시각 언어용 — 속도 추정은
                           #  표본 수가 생명이라 렌더러 몸라인/피크와 같은 층을 쓴다)
PAIR_CONF_MIN = 0.35       # 포즈거리 기저 채택 신뢰 하한 — 같은 근거
PAIR_MIN_JOINTS = 4        # fz._POSE_MIN_COMMON_JOINTS 재사용 (신규 튜닝상수 0)
PAIR_POSE_MAX = 1.30       # 포즈거리 상한 — 승인 pairs poseDist 실측 0.78~1.19 위
POLE_DIFF_MAX = 0.15       # 몸중심-폴거리 parity 상한 (몸통 단위) — PLAN 출발값
POLE_COVERAGE_MIN = 0.25   # 폴 검출 성립 하한 — compare_render 폴 감지와 동일 값

# 포즈거리 기저 후보 = 사지·몸통 12관절 (얼굴 5점 제외 — 자세 비교에 무의미하고
# 뒤돌기 국면에서 결측 잦음). 실제 기저 = 이 중 양쪽 신뢰 통과 교집합을 **명시**
# 고정해 fz.pose_distance 에 전달 (자동 공통관절 모드 금지 — docstring 경고).
POSE_BASIS_12 = (
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
)

# 운영 keypointReport(12관절)는 wrist 를 hand 로 부른다 (unify_probe 실측)
NAME_ALT = {"left_wrist": "left_hand", "right_wrist": "right_hand"}


# ── report 접근 (fz 헬퍼 재사용 + 이름공간 폴백) ─────────────────────────────

def _resolve(report: dict, name: str) -> str | None:
    joints = report.get("joints") or []
    if name in joints:
        return name
    alt = NAME_ALT.get(name)
    if alt and alt in joints:
        return alt
    return None


def kp(report: dict, idx: int, name: str,
       conf_min: float = HOLD_CONF_MIN) -> tuple[float, float] | None:
    """정규화 좌표 (finite AND conf >= conf_min). 불성립 = None."""
    rn = _resolve(report, name)
    if rn is None:
        return None
    xy = fz._kp_xy(report, idx, rn)  # noqa: SLF001
    if xy is None:
        return None
    c = fz._kp_conf(report, idx, rn)  # noqa: SLF001
    if c is None or c < conf_min:
        return None
    return xy


def align_to_report(align: dict, side: str) -> dict:
    """align.json 의 (user|ref) 15fps RTMW17 트랙 → keypointReport 형식."""
    joints = list(align["joints17"])
    frames = int(align[f"{side}Frames"])
    data = np.asarray(align[f"{side}Kp"], dtype=float).reshape(frames, len(joints), 2)
    conf = np.asarray(align[f"{side}Score"], dtype=float).reshape(frames, len(joints))
    return {
        "joints": joints,
        "frames": frames,
        "fps": float(align["fps"]),
        "data": data.reshape(-1).tolist(),
        "confidence": conf.reshape(-1).tolist(),
        "_size": tuple(align.get(f"{side}Size") or ()),  # (W, H) px
    }


# ── 각도 시계열 (홀드 게이트 입력) ───────────────────────────────────────────

def joint_angle(report: dict, idx: int, joint: str,
                conf_min: float = HOLD_CONF_MIN) -> float | None:
    """관절 사이각(도). joint='split' 은 발목-힙중점-발목 벌림각 (렌더러 정의 미러)."""
    if joint == "split":
        pts = []
        for n in ("left_ankle", "right_ankle", "left_hip", "right_hip"):
            p = kp(report, idx, n, conf_min)
            if p is None:
                return None
            pts.append(np.asarray(p, dtype=float))
        hm = (pts[2] + pts[3]) / 2
        v1, v2 = pts[0] - hm, pts[1] - hm
    else:
        tri = JOINT_ANGLES.get(joint)
        if tri is None:
            return None
        ps = []
        for n in tri:
            p = kp(report, idx, n, conf_min)
            if p is None:
                return None
            ps.append(np.asarray(p, dtype=float))
        v1, v2 = ps[0] - ps[1], ps[2] - ps[1]
    n1, n2 = float(np.linalg.norm(v1)), float(np.linalg.norm(v2))
    if n1 < 1e-9 or n2 < 1e-9:
        return None
    cos = float(np.dot(v1, v2) / (n1 * n2))
    return float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


@dataclass(frozen=True)
class HoldResult:
    passed: bool
    speed_dps: float | None      # robust 각속도 (도/초) — 측정불가면 None
    n_samples: int               # 창 안 유효 각도 표본 수
    reason: str                  # "hold" | "moving" | "unmeasurable"
    angles: dict = field(default_factory=dict)  # {frame: deg} 근거 박제용


def hold_gate(report: dict, kp_idx: int, joint: str, *,
              max_speed_dps: float = HOLD_MAX_DPS,
              half_window_f: int = HOLD_HALF_WINDOW_F,
              min_samples: int = HOLD_MIN_SAMPLES,
              conf_min: float = HOLD_CONF_MIN) -> HoldResult:
    """A1 홀드 게이트 — 측정 순간이 자세 성립(정지) 구간인가.

    robust 각속도 = 창(±half_window_f) 안 유효 (t, 각도) 쌍의 **Theil-Sen 기울기**
    (전 쌍 기울기의 중앙값). 원시 인접차(부록 E: 1129도/초 물리 불가값)와 달리
    단일 환각/지터 프레임이 중앙값에서 걸러진다. 저신뢰로 표본 미달 = 측정불가 =
    FAIL (fail-closed — 속도를 잴 수 없는 순간의 감점은 성립을 증명 못한 것).
    """
    fps = float(report.get("fps") or 0.0)
    frames = int(report.get("frames") or 0)
    if fps <= 0 or frames <= 0:
        return HoldResult(False, None, 0, "unmeasurable")
    lo = max(0, kp_idx - half_window_f)
    hi = min(frames - 1, kp_idx + half_window_f)
    samples: list[tuple[float, float]] = []
    angles: dict[int, float] = {}
    for f in range(lo, hi + 1):
        a = joint_angle(report, f, joint, conf_min)
        if a is not None:
            samples.append((f / fps, a))
            angles[f] = round(a, 1)
    if len(samples) < min_samples:
        return HoldResult(False, None, len(samples), "unmeasurable", angles)
    slopes = [
        (samples[j][1] - samples[i][1]) / (samples[j][0] - samples[i][0])
        for i in range(len(samples)) for j in range(i + 1, len(samples))
        if samples[j][0] > samples[i][0]
    ]
    speed = abs(float(np.median(slopes)))
    ok = speed < max_speed_dps
    return HoldResult(ok, speed, len(samples), "hold" if ok else "moving", angles)


# ── A2 짝 정합 게이트 (포즈거리 + 폴거리 parity) ─────────────────────────────

def confident_pose(report: dict, idx: int,
                   conf_min: float = PAIR_CONF_MIN) -> dict[str, tuple[float, float]]:
    """POSE_BASIS_12 중 신뢰 통과 관절의 정규화 좌표 map. 키는 COCO 이름으로 통일."""
    out: dict[str, tuple[float, float]] = {}
    for name in POSE_BASIS_12:
        xy = kp(report, idx, name, conf_min)
        if xy is not None:
            out[name] = xy
    return out


def torso_px_median(report: dict, size: tuple[int, int]) -> float | None:
    """트랙 전체 어깨중점-골반중점 px 거리의 중앙값 (프레임 지터에 robust)."""
    W, H = size
    vals = []
    for f in range(int(report.get("frames") or 0)):
        ls, rs = kp(report, f, "left_shoulder"), kp(report, f, "right_shoulder")
        lh, rh = kp(report, f, "left_hip"), kp(report, f, "right_hip")
        if None in (ls, rs, lh, rh):
            continue
        sm = ((ls[0] + rs[0]) / 2 * W, (ls[1] + rs[1]) / 2 * H)
        hm = ((lh[0] + rh[0]) / 2 * W, (lh[1] + rh[1]) / 2 * H)
        vals.append(math.hypot(sm[0] - hm[0], sm[1] - hm[1]))
    return float(np.median(vals)) if vals else None


def body_pole_dist(report: dict, idx: int, pole_x_norm: float,
                   size: tuple[int, int], torso_px: float) -> float | None:
    """몸중심(힙중점, 폴백 어깨중점)-폴 축선 수평거리 (몸통 단위). 불성립 = None."""
    W, _H = size
    lh, rh = kp(report, idx, "left_hip"), kp(report, idx, "right_hip")
    if lh is not None and rh is not None:
        cx = (lh[0] + rh[0]) / 2
    else:
        ls, rs = kp(report, idx, "left_shoulder"), kp(report, idx, "right_shoulder")
        if ls is None or rs is None:
            return None
        cx = (ls[0] + rs[0]) / 2
    if torso_px is None or torso_px <= 1e-6:
        return None
    return abs(cx - pole_x_norm) * W / torso_px


@dataclass(frozen=True)
class PairResult:
    passed: bool
    pose_dist: float | None
    basis_k: int                  # 포즈거리 기저 관절 수 (박제 — k 편향 감시)
    pole_user: float | None       # 몸중심-폴 거리 (몸통 단위)
    pole_ref: float | None
    pole_diff: float | None
    reason: str                   # "match" | "pose_far" | "pole_mismatch"
    #                             | "pose_unmeasurable" | "pole_unmeasured"(비차단)


def pair_gate(user_report: dict, u_kp: int, ref_report: dict, r_kp: int,
              pole_u: float | None, pole_r: float | None, *,
              user_size: tuple[int, int] | None = None,
              ref_size: tuple[int, int] | None = None,
              user_torso_px: float | None = None,
              ref_torso_px: float | None = None,
              pose_max: float = PAIR_POSE_MAX,
              pole_diff_max: float = POLE_DIFF_MAX,
              conf_min: float = PAIR_CONF_MIN) -> PairResult:
    """A2 짝 정합 — 두 정지가 "같은 장면"인가 (국면 + 폴 위치).

    · 포즈거리: 신뢰 통과 교집합 기저를 **명시 고정**해 fz.pose_distance 호출
      (단일 쌍 비교지만 임계와의 비교가 정지들 사이에 걸쳐 있으므로 기저 크기 k 를
      결과에 박제해 k-편향을 감시한다). 기저 < PAIR_MIN_JOINTS 또는 거리 None =
      측정불가 = FAIL (fail-closed).
    · 폴 parity: 양쪽 몸중심-폴 거리(몸통 단위) 차 < pole_diff_max. 폴 미검출 등
      측정 불가 시 **비차단**("pole_unmeasured") — 폴 검출은 게이트 밖 환경 요인
      이라 fail-closed 로 걸면 폴이 안 보이는 촬영 전부가 침묵한다. 보고서에 박제.
    """
    pu = confident_pose(user_report, u_kp, conf_min)
    pr = confident_pose(ref_report, r_kp, conf_min)
    basis = sorted(set(pu) & set(pr))
    if len(basis) < PAIR_MIN_JOINTS:
        return PairResult(False, None, len(basis), None, None, None,
                          "pose_unmeasurable")
    d = fz.pose_distance(pu, pr, basis=basis)
    if d is None:
        return PairResult(False, None, len(basis), None, None, None,
                          "pose_unmeasurable")

    du = dr = diff = None
    if (pole_u is not None and pole_r is not None
            and user_size and ref_size
            and user_torso_px and ref_torso_px):
        du = body_pole_dist(user_report, u_kp, pole_u, user_size, user_torso_px)
        dr = body_pole_dist(ref_report, r_kp, pole_r, ref_size, ref_torso_px)
        if du is not None and dr is not None:
            diff = abs(du - dr)

    if d >= pose_max:
        return PairResult(False, d, len(basis), du, dr, diff, "pose_far")
    if diff is not None and diff >= pole_diff_max:
        return PairResult(False, d, len(basis), du, dr, diff, "pole_mismatch")
    reason = "match" if diff is not None else "pole_unmeasured"
    return PairResult(True, d, len(basis), du, dr, diff, reason)


# ── 폴 축 검출 (bz5 부록 D 재구현 — 배경 중앙값 세로 에지) ───────────────────

@dataclass(frozen=True)
class PoleResult:
    x_norm: float        # 폴 축선 x (0..1, 프레임 너비 기준)
    coverage: float      # 축선 열의 세로 에지 커버리지 (행 비율)
    width_px: int        # 검출에 쓴 프레임 너비


def detect_pole_x(frames: np.ndarray, *, sample_max: int = 48,
                  edge_quantile: float = 0.92,
                  coverage_min: float = POLE_COVERAGE_MIN,
                  smooth_frac: float = 0.01) -> PoleResult | None:
    """폴 축선 x 검출. frames = (N,H,W,3) uint8 (시간축 샘플이면 충분).

    ① 시간축 중앙값 → 배경 프레임 (움직이는 사람 제거 — bz5 부록 D)
    ② 그레이스케일 수평 그래디언트 상위 8% 를 에지로 (compare_render 실측 이식)
    ③ 열별 에지 커버리지(행 비율)를 폭 1% 박스 스무딩 → 최대 열 = 폴 축
    ④ 커버리지 < coverage_min → None (폴 없음/가림 — 검출 불성립)
    """
    if frames.ndim != 4 or len(frames) == 0:
        return None
    if len(frames) > sample_max:
        sel = np.linspace(0, len(frames) - 1, sample_max).astype(int)
        frames = frames[sel]
    med = np.median(frames.astype(np.float32), axis=0)
    gray = med @ np.asarray([0.299, 0.587, 0.114], dtype=np.float32)
    gx = np.abs(np.gradient(gray, axis=1))
    thr = float(np.quantile(gx, edge_quantile))
    if thr <= 1e-6:
        return None
    mask = gx >= thr
    cov = mask.mean(axis=0)
    W = cov.shape[0]
    k = max(3, int(round(W * smooth_frac)) | 1)
    kernel = np.ones(k, dtype=float) / k
    cov_s = np.convolve(cov, kernel, mode="same")
    x = int(np.argmax(cov_s))
    c = float(cov_s[x])
    if c < coverage_min:
        return None
    return PoleResult(x / max(1, W - 1), c, W)


# ── A3 기계 눈 게이트 (Gemini vision — bz5 부록 C 설계) ─────────────────────

_GEMINI_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
               "{model}:generateContent?key={key}")

_CLAIM_QUESTION = {
    # 좌우 해부학 이름 금지 — keypoint 환각 시 마크가 엉뚱한 곳에 찍히고
    # 그 불일치를 기계 눈이 잡는다 (bz5 부록 C: 환각 프레임 conf 1.0 적중).
    "bent": ("사진의 주황색 원은 관절 하나를 표시합니다. 그 관절이 이루는 "
             "사지(팔 또는 다리)가 '접혀 있음(bent)'인지 '펴져 있음(extended)'"
             "인지 판정하세요. 원이 신체 위에 있지 않으면 'off_body'."),
    "extended": ("사진의 주황색 원은 관절 하나를 표시합니다. 그 관절이 이루는 "
                 "사지(팔 또는 다리)가 '접혀 있음(bent)'인지 '펴져 있음(extended)'"
                 "인지 판정하세요. 원이 신체 위에 있지 않으면 'off_body'."),
    "off_pole": ("사진의 주황색 원은 신체 부위 하나를 표시합니다. 세로 봉(폴)이 "
                 "보인다면, 표시된 부위가 폴에서 '떨어져 있음(off_pole)'인지 "
                 "'붙어 있음(on_pole)'인지 판정하세요. 원이 신체 위에 있지 않으면 "
                 "'off_body', 폴이 안 보이면 'no_pole'."),
}

_CLAIM_ENUM = {
    "bent": ["bent", "extended", "off_body", "unclear"],
    "extended": ["bent", "extended", "off_body", "unclear"],
    "off_pole": ["off_pole", "on_pole", "off_body", "no_pole", "unclear"],
}


def mark_crop(frame_rgb: np.ndarray, joint_xy_px: tuple[float, float], *,
              crop_px: int = 360, ring_frac: float = 0.10):
    """관절 중심 정사각 크롭 + 주황 링 마킹. (PIL.Image, 크롭 내 마크 좌표) 반환."""
    from PIL import Image, ImageDraw

    H, W = frame_rgb.shape[:2]
    side = int(min(crop_px, H, W))
    x, y = float(joint_xy_px[0]), float(joint_xy_px[1])
    x0 = int(np.clip(round(x - side / 2), 0, W - side))
    y0 = int(np.clip(round(y - side / 2), 0, H - side))
    crop = Image.fromarray(frame_rgb[y0:y0 + side, x0:x0 + side])
    draw = ImageDraw.Draw(crop)
    r = max(8, int(side * ring_frac / 2))
    cx, cy = x - x0, y - y0
    for w, color in ((6, (255, 255, 255)), (3, (255, 75, 51))):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=w)
    return crop, (cx, cy)


def machine_eye(frame_rgb: np.ndarray, joint_xy_px: tuple[float, float],
                claim: str, *, api_key: str, crop_px: int = 360,
                model: str = "gemini-3.5-flash",
                timeout_s: float = 60.0) -> dict:
    """A3 기계 눈 — 마킹 크롭을 Gemini 가 판정, 감점 주장과 일치 여부 반환.

    claim ∈ {bent, extended, off_pole}. 반환 {observed, match, confidence,
    reason, crop(PIL)}. 호출/네트워크 실패는 observed="error" (fail-closed —
    match=False). temp 0 + JSON schema 강제.
    """
    if claim not in _CLAIM_QUESTION:
        raise ValueError(f"unknown claim: {claim}")
    crop, _ = mark_crop(frame_rgb, joint_xy_px, crop_px=crop_px)
    buf = io.BytesIO()
    crop.save(buf, format="JPEG", quality=90)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    body = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
            {"text": _CLAIM_QUESTION[claim]},
        ]}],
        "generationConfig": {
            "temperature": 0,
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "object",
                "properties": {
                    "observed": {"type": "string", "enum": _CLAIM_ENUM[claim]},
                    "confidence": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["observed", "confidence", "reason"],
            },
        },
    }
    req = urllib.request.Request(
        _GEMINI_URL.format(model=model, key=api_key),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        got = json.loads(text)
        observed = str(got.get("observed", "unclear"))
        return {
            "observed": observed,
            "match": observed == claim,
            "confidence": float(got.get("confidence", 0.0)),
            "reason": str(got.get("reason", "")),
            "crop": crop,
        }
    except Exception as e:  # noqa: BLE001 - 네트워크/파싱 실패는 fail-closed 로 수렴
        return {"observed": "error", "match": False, "confidence": 0.0,
                "reason": f"{type(e).__name__}: {e}", "crop": crop}
