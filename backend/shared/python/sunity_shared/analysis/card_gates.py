"""성립 게이트 3종 (홀드/짝정합/기계눈) — 카드 생산 경로 운영 모듈 (quick-260811-kpo).

260811-ii0 `gates.py` 프로토타입의 운영 이식. CONTINUE-2026-08-11 프로세스 확정본의
게이트 층 (A1 홀드 / A2 짝 정합 / A3 기계 눈). 동작명 분기 0 (D-41) — 모든 함수는
report/track 형상만 본다. **채점 무접촉** — 소비처는 complete 이후 표현물 스테이지
(pipeline._run_gated_card_inherit) 뿐이다.

  · hold_gate   — 측정 순간의 robust 각속도(3창 최소 Theil-Sen) < 임계. 측정불가 = FAIL.
  · pair_gate   — 포즈거리(fz.pose_distance 가중 모드) + 몸중심-폴거리 parity.
  · detect_pole_x — 배경 중앙값 프레임의 세로 에지 열 커버리지 (bz5 부록 D 방식).
  · machine_eye — 관절 마킹 크롭 → Gemini(temp 0, JSON schema) 2단 판정.
                  좌우 해부학 이름 금지 — "표시된 부위"만 지시 (bz5 부록 C 설계).
                  2단 = 상태(bent/extended) + 사지 종류(팔/다리) — 마크-전위 구멍
                  (ii0 SWEEP-REPORT §3-2 kneepath 실측: 무릎 마크가 팔에 얹혀
                  claim=bent 가 우연 일치) 수리분.

임계는 ii0 스윕 확정값 (260811-ii0-SWEEP-REPORT §2 튜닝 이력 — **재튜닝 금지**):
  · HOLD_MAX_DPS 60  — 승인 9정지 hold 최대 59.3(경계) vs fresh 전환 최소 98 실측.
  · PAIR_POSE_MAX 0.85 — 승인 최대 0.74 vs 부정 대조군 최소 0.96 사이 (양측 유도).
  · POLE_DIFF_MAX 0.375 — 승인 최대 0.31(elbow r03: 차이 자체가 결함인 승인 표시)
    vs NEG left_hip 0.44 사이 중점.

report 형식 = 운영 keypointReport(joints/data/confidence/frames/fps) 그대로.
align.json(15fps RTMW17) 트랙은 align_to_report() 로 같은 형식으로 변환해 쓴다 —
**doc keypointReport 는 게이트 판정 트랙으로 부적합** (fps 라벨 오차: 라벨 18 vs
실효 20.1 ffprobe 실측, ii0 발견 4). fail-closed 의미론: 측정불가 = FAIL, 기계 눈
네트워크/파싱 실패 = match False.
"""

from __future__ import annotations

import base64
import io
import json
import math
import urllib.request
from dataclasses import dataclass, field

import numpy as np

from ..gemini.config import DEFAULT_C_MODEL  # 모델 문자열 owner = config 한 곳
from . import fault_zoom as fz
from .skeleton import JOINT_ANGLES

# ── 확정 임계 (ii0 스윕 — 근거는 모듈 docstring, 재튜닝 금지) ─────────────────
HOLD_MAX_DPS = 60.0        # 홀드 판정 각속도 상한 (도/초)
HOLD_HALF_WINDOW_F = 3     # ±3 프레임 (CONTINUE A1 명세)
HOLD_MIN_SAMPLES = 4       # 대칭창 7표본 중 최소 유효 측정 수 — 미만 = 측정불가(FAIL)
HOLD_CONF_MIN = 0.35       # 각도 측정 좌표 신뢰 하한 — 렌더러 표시 게이트(0.35) 재사용
                           # (fz._KP_CONF_MIN 0.5 는 확정 시각 언어용 — 속도 추정은
                           #  표본 수가 생명이라 렌더러 몸라인/피크와 같은 층을 쓴다)
PAIR_CONF_MIN = 0.35       # 포즈거리 기저 채택 신뢰 하한 — 같은 근거
PAIR_MIN_JOINTS = fz._POSE_MIN_COMMON_JOINTS  # noqa: SLF001 - 재사용 (신규 튜닝상수 0)
PAIR_POSE_MAX = 0.85       # 포즈거리 상한 — 승인 0.74 / NEG 0.96 사이 (ii0 final)
POLE_DIFF_MAX = 0.375      # 몸중심-폴거리 parity 상한 (몸통 단위) — ii0 final
POLE_COVERAGE_MIN = 0.25   # 폴 검출 성립 하한 — compare_render POLE_COV_MIN 과 동일 값

# 기계 눈 claim 유도 — 트랙 각도 이분 (ii0 sweep_gates._track_claim 이식).
# 중간각 (BENT_MAX, EXT_MIN) 은 굽힘/폄 이분 판정 대상이 아님 = 정직한 침묵.
EYE_BENT_MAX_DEG = 100.0
EYE_EXT_MIN_DEG = 150.0

# 포즈거리 기저 후보 = 사지·몸통 12관절 (얼굴 5점 제외 — 자세 비교에 무의미하고
# 뒤돌기 국면에서 결측 잦음). 실제 기저 = 이 중 양쪽 성립 교집합을 **명시** 고정해
# fz.pose_distance 에 전달 (자동 공통관절 모드 금지 — fz.pose_distance docstring 경고).
POSE_BASIS_12 = (
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
)

# 운영 keypointReport(12관절)는 wrist 를 hand 로 부른다 (bz5 unify_probe 실측)
NAME_ALT = {"left_wrist": "left_hand", "right_wrist": "right_hand"}

# 관절 → 사지 종류 (기계 눈 2단 판정의 기대값 — 좌/우 이름은 여기서도 안 쓴다)
_LIMB_OF = {
    "elbow": "arm", "shoulder": "arm", "wrist": "arm", "hand": "arm",
    "knee": "leg", "hip": "leg", "ankle": "leg",
}


def crit_joint(joint_or_crit: str) -> str:
    """게이트가 잴 각도 축. 벌림 계열(criterion 이름 그대로 옴)은 split 벌림각."""
    if joint_or_crit in ("split_angle", "leg_extension"):
        return "split"
    return joint_or_crit


def joint_limb(joint: str) -> str | None:
    """관절 이름 → 사지 종류('arm'|'leg') — 기계 눈 마크-전위 검증의 기대값."""
    return _LIMB_OF.get(joint.split("_")[-1])


def track_claim(angle: float | None) -> str | None:
    """트랙 각도 → 기계 눈에 물을 주장. 중간각은 판정 대상 아님 (정직한 침묵)."""
    if angle is None:
        return None
    if angle <= EYE_BENT_MAX_DEG:
        return "bent"
    if angle >= EYE_EXT_MIN_DEG:
        return "extended"
    return None


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
    speed_dps: float | None      # 판정에 쓴 각속도 = 3창 중 최소 (도/초)
    n_samples: int               # 대칭창 유효 각도 표본 수
    reason: str                  # "hold" | "moving" | "unmeasurable"
    angles: dict = field(default_factory=dict)  # {frame: deg} 근거 박제용
    window_speeds: dict = field(default_factory=dict)  # {past|sym|future: dps}


def _theil_sen(samples: list[tuple[float, float]]) -> float | None:
    if len(samples) < 2:
        return None
    slopes = [
        (samples[j][1] - samples[i][1]) / (samples[j][0] - samples[i][0])
        for i in range(len(samples)) for j in range(i + 1, len(samples))
        if samples[j][0] > samples[i][0]
    ]
    return abs(float(np.median(slopes))) if slopes else None


def hold_gate(report: dict, kp_idx: int, joint: str, *,
              max_speed_dps: float = HOLD_MAX_DPS,
              half_window_f: int = HOLD_HALF_WINDOW_F,
              min_samples: int = HOLD_MIN_SAMPLES,
              conf_min: float = HOLD_CONF_MIN) -> HoldResult:
    """A1 홀드 게이트 — 측정 순간이 자세 성립(정지) 구간에 붙어 있는가.

    robust 각속도 = 유효 (t, 각도) 쌍의 **Theil-Sen 기울기**(전 쌍 기울기 중앙값).
    원시 인접차(bz5 부록 E: 1129도/초 물리 불가값)와 달리 단일 환각/지터 프레임이
    중앙값에서 걸러진다.

    **3창 최소 판정** (ii0 스윕 구조 수리 ① — 승인 코퍼스 실측 유도): 정지는 홀드
    구간의 **경계 순간**(자세 도달 직후)에 잡히는 것이 정당하다 — 승인 pdshapefault
    r00 은 재그립 직후 정착 프레임이라 대칭창은 직전 전이를 물어 111도/초가 나오지만
    전방창은 33도/초로 안정이다. 과거창 [i-w, i] / 대칭창 [i-w, i+w] / 미래창 [i, i+w]
    중 **최소 속도** < 임계면 홀드에 접해 있다고 본다. 양쪽 다 전이 중(전환 구간)이면
    세 창 전부 높아 FAIL — 판별력은 유지된다 (fresh 왼골반 3창 전부 >110 실측).
    대칭창 표본이 min_samples 미만이고 부분창도 표본 부족 = 측정불가 = FAIL
    (fail-closed — 속도를 잴 수 없는 순간의 감점은 성립을 증명 못한 것).
    """
    fps = float(report.get("fps") or 0.0)
    frames = int(report.get("frames") or 0)
    if fps <= 0 or frames <= 0:
        return HoldResult(False, None, 0, "unmeasurable")
    kp_idx = max(0, min(frames - 1, kp_idx))
    lo = max(0, kp_idx - half_window_f)
    hi = min(frames - 1, kp_idx + half_window_f)
    angles: dict[int, float] = {}
    for f in range(lo, hi + 1):
        a = joint_angle(report, f, joint, conf_min)
        if a is not None:
            angles[f] = a
    sym = [(f / fps, a) for f, a in angles.items()]
    past = [(f / fps, a) for f, a in angles.items() if f <= kp_idx]
    futr = [(f / fps, a) for f, a in angles.items() if f >= kp_idx]
    half_min = max(2, (min_samples + 1) // 2)
    speeds: dict[str, float] = {}
    if len(sym) >= min_samples:
        s = _theil_sen(sym)
        if s is not None:
            speeds["sym"] = s
    for name, smp in (("past", past), ("future", futr)):
        if len(smp) >= half_min:
            s = _theil_sen(smp)
            if s is not None:
                speeds[name] = s
    shown = {k: round(v, 1) for k, v in speeds.items()}
    disp = {f: round(a, 1) for f, a in angles.items()}
    if not speeds:
        return HoldResult(False, None, len(sym), "unmeasurable", disp, shown)
    best = min(speeds.values())
    ok = best < max_speed_dps
    return HoldResult(ok, best, len(sym), "hold" if ok else "moving", disp, shown)


# ── A2 짝 정합 게이트 (포즈거리 + 폴거리 parity) ─────────────────────────────

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

    · 포즈거리 = **가중 모드** (fz.select_pose_matched_ref_frame 2026-07-27 재설계
      미러): 기저 = 학생 finite∩conf>0 관절 ∩ 기준 finite 관절 (POSE_BASIS_12 안),
      가중 = 학생 confidence 그대로. conf>=0.5 경질 게이트는 실 fixture 에서 역립
      구간 기저 붕괴(승인 elbow r01 k=3 측정불가)를 만든 실측 재현 (ii0 구조 수리 ②).
      기저는 **명시 고정**해 전달하고 크기 k 를 박제 (k-편향 감시). 기저 <
      PAIR_MIN_JOINTS 또는 거리 None = 측정불가 = FAIL (fail-closed).
    · 폴 parity: 양쪽 몸중심-폴 거리(몸통 단위) 차 < pole_diff_max. 폴 미검출 등
      측정 불가 시 **비차단**("pole_unmeasured") — 폴 검출은 게이트 밖 환경 요인
      이라 fail-closed 로 걸면 폴이 안 보이는 촬영 전부가 침묵한다. 보고서에 박제.
    """
    pu: dict[str, tuple[float, float]] = {}
    weights: dict[str, float] = {}
    for name in POSE_BASIS_12:
        rn = _resolve(user_report, name)
        if rn is None:
            continue
        xy = fz._kp_xy(user_report, u_kp, rn)  # noqa: SLF001
        if xy is None:
            continue
        c = fz._kp_conf(user_report, u_kp, rn)  # noqa: SLF001
        if c is None or c <= 0.0:
            continue
        pu[name] = xy
        weights[name] = float(c)
    pr: dict[str, tuple[float, float]] = {}
    for name in pu:
        rn = _resolve(ref_report, name)
        if rn is None:
            continue
        xy = fz._kp_xy(ref_report, r_kp, rn)  # noqa: SLF001
        if xy is not None:
            pr[name] = xy
    basis = sorted(set(pu) & set(pr))
    if len(basis) < PAIR_MIN_JOINTS:
        return PairResult(False, None, len(basis), None, None, None,
                          "pose_unmeasurable")
    d = fz.pose_distance(pu, pr, basis=basis, weights=weights)
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


# ── 폴 축 검출 (bz5 부록 D — 배경 중앙값 세로 에지) ──────────────────────────

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

    운영 소비처는 compare_render._detect_pole 캐시(pole_{side}.json) 재사용이 1순위
    — 이 함수는 캐시가 없는 하네스/검증 경로용이다.

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


# ── A3 기계 눈 게이트 (Gemini vision — bz5 부록 C + ii0 §3-2 마크-전위 수리) ──

_GEMINI_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
               "{model}:generateContent?key={key}")

_LIMB_QUESTION = (
    " 또한 원 안의 관절이 팔의 관절인지 다리의 관절인지 limb 필드로 함께 "
    "판정하세요 (팔='arm', 다리='leg', 그 외='other')."
)

_CLAIM_QUESTION = {
    # 좌우 해부학 이름 금지 — keypoint 환각 시 마크가 엉뚱한 곳에 찍히고
    # 그 불일치를 기계 눈이 잡는다 (bz5 부록 C: 환각 프레임 conf 1.0 적중).
    "bent": ("사진의 주황색 원은 관절 하나를 표시합니다. 그 관절이 이루는 "
             "사지(팔 또는 다리)가 '접혀 있음(bent)'인지 '펴져 있음(extended)'"
             "인지 판정하세요. 원이 신체 위에 있지 않으면 'off_body'."
             + _LIMB_QUESTION),
    "extended": ("사진의 주황색 원은 관절 하나를 표시합니다. 그 관절이 이루는 "
                 "사지(팔 또는 다리)가 '접혀 있음(bent)'인지 '펴져 있음(extended)'"
                 "인지 판정하세요. 원이 신체 위에 있지 않으면 'off_body'."
                 + _LIMB_QUESTION),
    "off_pole": ("사진의 주황색 원은 신체 부위 하나를 표시합니다. 세로 봉(폴)이 "
                 "보인다면, 표시된 부위가 폴에서 '떨어져 있음(off_pole)'인지 "
                 "'붙어 있음(on_pole)'인지 판정하세요. 원이 신체 위에 있지 않으면 "
                 "'off_body', 폴이 안 보이면 'no_pole'." + _LIMB_QUESTION),
}

_CLAIM_ENUM = {
    "bent": ["bent", "extended", "off_body", "unclear"],
    "extended": ["bent", "extended", "off_body", "unclear"],
    "off_pole": ["off_pole", "on_pole", "off_body", "no_pole", "unclear"],
}

_LIMB_ENUM = ["arm", "leg", "other", "unclear"]


def _eye_verdict(observed: str, limb: str | None, claim: str,
                 expected_limb: str | None) -> bool:
    """순수 판정 — 상태 일치 AND (사지 종류가 판정됐다면) 기대 사지와 일치.

    2단 판정 (ii0 SWEEP-REPORT §6-3 지정 수리): 마크가 다른 사지에 얹히면
    (kneepath 실측 — 무릎 마크가 굽은 팔에 얹혀 claim=bent 우연 일치) 상태가
    맞아도 불일치 처리. limb 가 'other'/'unclear' 는 적극 모순이 아니므로 비차단
    — 차단은 arm↔leg 확정 상충에만 (좌/우 이름 금지는 유지).
    """
    if observed != claim:
        return False
    if (expected_limb in ("arm", "leg") and limb in ("arm", "leg")
            and limb != expected_limb):
        return False
    return True


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
                claim: str, *, api_key: str, expected_limb: str | None = None,
                crop_px: int = 360, model: str = DEFAULT_C_MODEL,
                timeout_s: float = 60.0) -> dict:
    """A3 기계 눈 — 마킹 크롭을 Gemini 가 판정, 감점 주장과 일치 여부 반환.

    claim ∈ {bent, extended, off_pole}. expected_limb ∈ {arm, leg, None} —
    주어지면 2단 판정(_eye_verdict): 눈이 본 사지 종류가 기대와 확정 상충이면
    상태가 맞아도 match=False (마크-전위 구멍, ii0 §3-2). 반환 {observed, limb,
    match, confidence, reason, crop(PIL)}. 호출/네트워크/파싱 실패는
    observed="error" (fail-closed — match=False). temp 0 + JSON schema 강제.
    개인정보는 크롭 이미지 외 미전송, 추론 호출만 (T-kpo-01 — 학습 재료 무접촉).
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
                    "limb": {"type": "string", "enum": _LIMB_ENUM},
                    "confidence": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["observed", "limb", "confidence", "reason"],
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
        limb = str(got.get("limb", "unclear"))
        return {
            "observed": observed,
            "limb": limb,
            "match": _eye_verdict(observed, limb, claim, expected_limb),
            "confidence": float(got.get("confidence", 0.0)),
            "reason": str(got.get("reason", "")),
            "crop": crop,
        }
    except Exception as e:  # noqa: BLE001 - 네트워크/파싱 실패는 fail-closed 로 수렴
        return {"observed": "error", "limb": None, "match": False,
                "confidence": 0.0, "reason": f"{type(e).__name__}: {e}",
                "crop": crop}
