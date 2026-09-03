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


# 관절 → 종류 한국어 (기계 눈 질문의 관절 종류 힌트 — quick-260903-jka).
# 좌/우 이름은 여기서도 안 쓴다. hand 는 운영 keypointReport 의 wrist 별칭(NAME_ALT).
_KIND_KO = {
    "knee": "무릎", "elbow": "팔꿈치", "hip": "엉덩이", "shoulder": "어깨",
    "ankle": "발목", "wrist": "손목", "hand": "손목",
}

# 종류 한국어 → 사지 (힌트 문형 선택·expected_limb 불일치 방어에 사용)
_KIND_LIMB = {ko: _LIMB_OF[suffix] for suffix, ko in _KIND_KO.items()}


def joint_kind_ko(joint: str) -> str | None:
    """관절 이름 → 종류 한국어('무릎'|'팔꿈치'|'엉덩이'|'어깨'|'발목'|'손목').

    기계 눈 질문의 관절 종류 힌트용 (quick-260903-jka). joint_limb 과 같은
    split("_")[-1] 관례 — 'split' 등 미등록 축은 None (힌트 미부착).
    """
    return _KIND_KO.get(joint.split("_")[-1])


# 기계 눈 검사 제외 관절 종류 — 몸통 관절 (quick-260903-lpl). 키 공간 = _LIMB_OF
# 와 같은 관절 이름 꼬리. 눈을 안 받는 카드도 hold·pair 게이트는 그대로 받는다.
EYE_SKIP_KINDS = frozenset({"hip", "shoulder"})


def eye_applicable(joint: str) -> bool:
    """관절이 기계 눈 검사 대상인가 — 몸통 관절(엉덩이·어깨)은 False, 그 외 True.

    belle 09-03: "비교 사진이 있어야 뭘 보지 저것만 보고 어케 알아". 눈은 사진
    한 장(내 영상 크롭 + 원)만 받고 "그 관절이 접혔나 펴졌나"를 절대 판정한다.
    무릎·팔꿈치는 한 장에서 각이 보여 성립하지만(회귀 5/5), 엉덩이는 기준 없이
    정해지지 않는다 (같은 크롭 5회: 3/5, 힌트 주면 1/5 — quick-260903-jka/jxn).
    감점 자체가 정은지 대비 각도 차이인데 눈에는 기준을 안 준 것이 구조적 원인.
    기준 사진을 함께 주는 질문은 "같은 순간" 검증(참고 카드 × 사유)과 얽혀 별건 —
    여기서는 몸통 관절을 눈에서 빼 확정 사진이 운으로 사라지지 않게만 한다.

    joint_limb 과 같은 split("_")[-1] 관례. 미등록 관절('split', 'left_foo' 등)은
    True — 종전 동작 (눈 여부는 호출측 midrange 등 기존 게이트가 정한다).
    """
    return joint.split("_")[-1] not in EYE_SKIP_KINDS


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


# 관절 종류 → 그 관절을 이루는 두 분절 (힌트 문장 "뒤로 {분절}이/가 이어지면")
_KIND_SEGMENTS = {
    "무릎": "허벅지와 정강이", "엉덩이": "몸통과 허벅지", "발목": "정강이와 발",
    "팔꿈치": "위팔과 아래팔", "어깨": "몸통과 위팔", "손목": "아래팔과 손",
}

# 힌트를 붙이는 관절 종류 = 사지 중간 관절만 (quick-260903-jxn). 09-03 측정
# (jka 운영 질문, temperature 0, 5회): 무릎·팔꿈치는 힌트로 5/5 안정이지만
# 엉덩이(pdshape 09-02 확정 카드, 기대 True)는 힌트 없이 3/5 → 힌트 부착 1/5 로
# 더 나빠진다 — 눈이 "엉덩이 굽힘"을 허벅지 방향(아래로 뻗음=extended)으로
# 오독. 어깨는 5/5 였으나 같은 몸통 관절이라 보수적으로 제외 (측정 전 상태 =
# jka 이전 질문 그대로). joint_kind_ko 는 여전히 엉덩이/어깨를 반환한다 —
# 호출측 무변경, 게이트는 이 집합 한 곳.
_HINT_KINDS = frozenset({"무릎", "팔꿈치", "발목", "손목"})


def _ga_i(word: str) -> str:
    """주격 조사 가/이 — 마지막 글자 받침 유무 (한글 음절 외는 '가')."""
    c = ord(word[-1])
    if 0xAC00 <= c <= 0xD7A3 and (c - 0xAC00) % 28:
        return "이"
    return "가"


def _joint_kind_hint(expected_limb: str, joint_kind: str | None) -> str:
    """관절 종류 힌트 1문장 (quick-260903-jka) — 선행 공백 포함, 미부착이면 "".

    미등록 종류(None 포함)와 expected_limb 와 사지가 어긋나는 종류(예: leg 에
    '팔꿈치')는 빈 문자열 — 질문은 vlu 오클루전 변형 그대로. 무릎/leg 문장은
    09-03 측정본(5/5)과 문자 동일해야 한다 — 문형·조사 변경 금지.

    _HINT_KINDS 밖(엉덩이·어깨)도 빈 문자열 (quick-260903-jxn) — 엉덩이는
    힌트가 3/5 → 1/5 로 판정을 해쳤다. 그 경우 질문은 jka 이전(vlu) 질문과
    byte-동일.
    """
    if joint_kind not in _HINT_KINDS or _KIND_LIMB.get(joint_kind) != expected_limb:
        return ""
    seg = _KIND_SEGMENTS[joint_kind]
    other, mine = ("팔", "다리") if expected_limb == "leg" else ("다리", "팔")
    return (
        f" 참고: 이 원은 {joint_kind} 관절 표시이며, {other}{_ga_i(other)} "
        f"{joint_kind} 앞을 가로질러 가릴 수 있습니다. {other} 뒤로 "
        f"{seg}{_ga_i(seg)} 이어지면 그 {mine}{_ga_i(mine)} 판정 대상입니다."
    )


def _claim_question(claim: str, expected_limb: str | None,
                    joint_kind: str | None = None) -> str:
    """claim 별 기계 눈 질문 조립 (quick-260901-vlu — belle 09-01 오클루전 FP 승인 수리).

    좌/우 해부학 이름 금지 (왼/오른/left/right 0) — _CLAIM_QUESTION 설계 승계
    (bz5 부록 C: keypoint 환각 시 마크가 엉뚱한 곳에 찍히고 그 불일치를 눈이
    잡아야 한다).

    expected_limb 미지정(None)과 off_pole 은 _CLAIM_QUESTION 그대로 반환
    (byte-동일 하위호환 — 질문 무변경). bent/extended + arm/leg 은 오클루전
    반영 변형: 판정 대상 사지를 명시하고, 다른 사지에 가려져 뒤에 있어도 그
    사지를 판정하게 한다 (오클루전 프레임에서 "원 위치의 가장 앞 사지"를 답해
    확정 카드가 삭제되던 위양성 교정). 마크-전위 차단은 유지 — 기대 사지가
    원 위치·배후에 아예 없으면 "실제로 보이는 사지"를 limb 에 적게 하고,
    _eye_verdict(무접촉, ii0 §6-3)의 arm↔leg 확정 상충이 FAIL 을 낸다.
    이 변형에는 _LIMB_QUESTION 접미를 붙이지 않는다 (limb 지시가 본문에
    내장 — 중복/모순 방지). 응답 스키마(_CLAIM_ENUM/_LIMB_ENUM)는 무변경.

    joint_kind (quick-260903-jka): 등록된 관절 종류('무릎' 등, joint_kind_ko)
    가 오면 오클루전 변형 끝에 힌트 1문장을 붙인다 — "이 원은 {종류} 관절
    표시, 다른 사지가 앞을 가로질러 가릴 수 있음, 그 뒤로 두 분절이
    이어지면 그 사지가 대상". 09-03 측정(운영 경로 eye_judge, temperature 0,
    5회): 클라임 3.0s 오클루전 크롭(뻗은 팔이 굽힌 무릎 앞, claim=bent/leg)
    운영 질문 2/5·1/5 성립 → 힌트 부착 5/5·5/5, 마크-전위 회귀(kneepath 무릎
    마크가 팔 위, 기대 False) 0/5 → 0/5 유지. vlu "라이브 1회 PASS"는 눈의
    비결정성이었고 관절 종류 명시가 이를 안정시킨다. joint_kind None·미등록·
    off_pole 은 종전과 byte-동일 (하위호환).
    """
    if claim == "off_pole" or expected_limb not in ("arm", "leg"):
        return _CLAIM_QUESTION[claim]
    target, subj = ("팔", "팔이") if expected_limb == "arm" else ("다리", "다리가")
    q = (
        "사진의 주황색 원은 관절 하나를 표시합니다. 원 주변에는 팔과 다리가 "
        f"겹쳐 보일 수 있습니다. 판정 대상은 원 위치의 {target}입니다. "
        f"원 위치에 {subj} 보이면 — 다른 사지에 부분적으로 가려져 뒤에 "
        f"있어도 — 그 {subj} '접혀 있음(bent)'인지 '펴져 있음(extended)'인지 "
        "판정하고 limb 필드에 그 사지 종류를 적으세요 (팔='arm', 다리='leg'). "
        f"원 위치와 그 바로 뒤 어디에도 {subj} 보이지 않으면(표시가 엉뚱한 "
        "곳에 찍힌 경우), 원이 실제로 놓인 사지의 접힘/펴짐을 판정하고 limb "
        "필드에 실제로 보이는 사지 종류를 적으세요 (그 외='other'). 원이 신체 "
        "위에 있지 않으면 observed 는 'off_body' 로 하세요."
    )
    return q + _joint_kind_hint(expected_limb, joint_kind)


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


def eye_judge(crop, claim: str, *, api_key: str,
              expected_limb: str | None = None,
              joint_kind: str | None = None,
              model: str = DEFAULT_C_MODEL, timeout_s: float = 60.0) -> dict:
    """마킹 크롭(PIL RGB) 판정 진입점 — machine_eye 에서 추출 (quick-260901-vlu).

    질문 조립(_claim_question) → JPEG 인코딩 → Gemini 호출 → _eye_verdict 까지
    운영 경로 한 벌 — 하네스/검증이 크롭 입력으로 같은 프롬프트·스키마를
    재판정한다 (프롬프트 재구현 금지의 근거 지점). 반환 {observed, limb, match,
    confidence, reason} — crop 미포함 (machine_eye 가 첨부). 호출/네트워크/파싱
    실패는 observed="error" (fail-closed — match=False). temp 0 + JSON schema
    강제. 개인정보는 크롭 이미지 외 미전송, 추론 호출만 (T-kpo-01).
    joint_kind (quick-260903-jka, joint_kind_ko 값) 는 질문 힌트에만 쓰이고
    판정(_eye_verdict)·스키마·반환 형상은 무변경 — None 이면 종전 질문.
    """
    if claim not in _CLAIM_QUESTION:
        raise ValueError(f"unknown claim: {claim}")
    buf = io.BytesIO()
    crop.save(buf, format="JPEG", quality=90)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    body = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
            {"text": _claim_question(claim, expected_limb, joint_kind)},
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
        }
    except Exception as e:  # noqa: BLE001 - 네트워크/파싱 실패는 fail-closed 로 수렴
        return {"observed": "error", "limb": None, "match": False,
                "confidence": 0.0, "reason": f"{type(e).__name__}: {e}"}


def eye_judge_majority(crop, claim: str, *, api_key: str,
                       expected_limb: str | None = None,
                       joint_kind: str | None = None,
                       model: str = DEFAULT_C_MODEL, timeout_s: float = 60.0,
                       max_rounds: int = 3) -> dict:
    """불일치일 때만 재질문하는 다수결 판정 (quick-260903-jxn).

    1회 eye_judge → match=True 면 그대로 반환 (추가 호출 0 — 비용·시간 무변화).
    False 면 같은 크롭에 (max_rounds-1)회 더 물어 match 다수결(True 표 > 절반)
    로 확정한다. 09-03 측정(jka 운영 질문 5회): 클라임 오클루전 무릎 4/5,
    엉덩이 3/5 처럼 남은 비결정을 줄이는 용도 — p=0.8 → 0.93, p=0.6 → 0.74,
    kneepath 마크-전위(p=0) → 0 (위양성 증가 없음).

    반환 = 다수 쪽 판정 중 **첫 번째** 결과 dict(observed/limb/match/
    confidence/reason — eye_judge 와 동일 형상) + rounds(총 호출 수) +
    votesTrue/votesFalse. observed="error"(호출 실패)는 match=False 이므로
    False 표 — fail-closed 유지. max_rounds 는 홀수만 (동률 방지) — 짝수면
    ValueError. _eye_verdict·질문·스키마 무접촉: 판정 1회의 의미는 eye_judge
    그대로이고 이 함수는 표만 센다.
    """
    if max_rounds < 1 or max_rounds % 2 == 0:
        raise ValueError(f"max_rounds must be a positive odd int, got {max_rounds}")
    results = [eye_judge(crop, claim, api_key=api_key, expected_limb=expected_limb,
                         joint_kind=joint_kind, model=model, timeout_s=timeout_s)]
    if bool(results[0].get("match")):
        out = dict(results[0])
        out.update({"rounds": 1, "votesTrue": 1, "votesFalse": 0})
        return out
    for _ in range(max_rounds - 1):
        results.append(eye_judge(crop, claim, api_key=api_key,
                                 expected_limb=expected_limb, joint_kind=joint_kind,
                                 model=model, timeout_s=timeout_s))
    votes_true = sum(1 for r in results if bool(r.get("match")))
    votes_false = len(results) - votes_true
    winner = votes_true > len(results) / 2
    first = next(r for r in results if bool(r.get("match")) == winner)
    out = dict(first)
    out.update({"rounds": len(results), "votesTrue": votes_true,
                "votesFalse": votes_false})
    return out


def machine_eye(frame_rgb: np.ndarray, joint_xy_px: tuple[float, float],
                claim: str, *, api_key: str, expected_limb: str | None = None,
                joint_kind: str | None = None,
                crop_px: int = 360, model: str = DEFAULT_C_MODEL,
                timeout_s: float = 60.0, majority: bool = False) -> dict:
    """A3 기계 눈 — 마킹 크롭을 Gemini 가 판정, 감점 주장과 일치 여부 반환.

    claim ∈ {bent, extended, off_pole}. expected_limb ∈ {arm, leg, None} —
    주어지면 질문이 기대 사지 명시형(_claim_question, 오클루전 반영)으로
    조립되고, 2단 판정(_eye_verdict)이 arm↔leg 확정 상충을 차단한다
    (마크-전위 구멍, ii0 §3-2 — 차단 무접촉 유지). joint_kind (quick-260903-jka,
    joint_kind_ko 값) 는 eye_judge 로 통과해 관절 종류 힌트 1문장을 붙인다 —
    None 이면 종전 질문. 반환 {observed, limb, match, confidence, reason,
    crop(PIL)} — 공개 시그니처(kwarg 추가만)·반환 형상·원장 필드는 추출 전과
    동일. 실패 의미론은 eye_judge 와 동일 (fail-closed).
    majority (quick-260903-jxn): True 면 eye_judge_majority(불일치 시만 최대
    3회 다수결) — 반환에 rounds/votesTrue/votesFalse 가 추가된다. 기본 False
    = 종전 단발 판정 그대로 (하위호환·하네스), 추가 키 없음.
    """
    if claim not in _CLAIM_QUESTION:
        raise ValueError(f"unknown claim: {claim}")
    crop, _ = mark_crop(frame_rgb, joint_xy_px, crop_px=crop_px)
    judge = eye_judge_majority if majority else eye_judge
    out = judge(crop, claim, api_key=api_key, expected_limb=expected_limb,
                joint_kind=joint_kind, model=model, timeout_s=timeout_s)
    out["crop"] = crop
    return out


# ── 카드 결정 — 게이트는 표시만 정한다 (quick-260903-upx) ─────────────────────
#
# belle 09-03 (원문): "확대사진을 그 멈추는 구간은 다 보여줘야하고, 그걸 모든 동작에서
# 통과시켜야한다. 지금처럼 짜맞추는게 아니라 매번 사용자가 올렸을 때 그 동작을
# 캐치해서 확대사진을 넣어줘야하는데" / "pdshape 는 5개잖아 멈추는 동작(음성나오는
# 구간)이 근데 왜 또 4개야". 실측: 감점 5 = 비교 영상 정지 5 인데 사진은 4장(상한)
# → 2장(게이트 삭제). 그래서 게이트(hold/pair/eye)에는 **카드 삭제 권한이 없다** —
# 판정 결과는 doc 에 상태 문자열로 남고, 눈의 실제 불일치만 학생 패널 표시를
# 생략한다. 동작명·영상 ID 분기 0 — 문자열 형상만 본다.

EYE_STATE_MATCH = "match"
EYE_STATE_MISMATCH = "mismatch"
EYE_STATE_SKIP = "skip"    # 의도적 제외 — 몸통 관절(skip:torso_joint)·중간각(midrange)
EYE_STATE_NONE = "none"    # 판정 없음 — 미실행(hold/pair 뒤 미도달·peak)·프레임/키 부재
STATE_UNMEASURED = "unmeasured"   # 게이트 미실행 (peak 경로의 pair, 호출측 None)


@dataclass(frozen=True)
class CardDecision:
    emit: bool               # 항상 True — 게이트에 삭제 권한 없음 (belle 09-03)
    draw_user_marks: bool    # 학생 패널 표시(원·선·호·화살표) 여부 — 눈 불일치만 False
    hold_state: str          # "hold"|"moving"|"unmeasurable"|"peak"|"unmeasured"
    pair_state: str          # PairResult.reason 어휘 그대로 | "unmeasured"
    eye_state: str           # EYE_STATE_*


def eye_mismatch(eye_ok: bool | None, eye_why: str | None) -> bool:
    """눈 판정이 **실제 불일치**인가 — observed≠claim 또는 arm↔leg 확정 상충.

    pipeline._eye_check 의 사유 문자열은 판정이 실제로 났을 때만
    `claim->observed/limb` 형상(`->` 포함)이다. frame_missing / no_api_key 는 눈이
    못 본 것이지 틀린 것이 아니고, midrange / skip:torso_joint 는 의도적 제외다 —
    전부 불일치 아님 (표시 유지: 눈이 못 본 것은 틀린 게 아니다).
    """
    return eye_ok is False and "->" in (eye_why or "")


def eye_state(eye_ok: bool | None, eye_why: str | None) -> str:
    """눈 사유 → 상태 문자열 (match | mismatch | skip | none)."""
    why = eye_why or ""
    if "->" in why:
        return EYE_STATE_MATCH if eye_ok else EYE_STATE_MISMATCH
    if why == "midrange" or why.startswith("skip:"):
        return EYE_STATE_SKIP
    return EYE_STATE_NONE


def decide_card(hold_reason: str | None, pair_reason: str | None,
                eye_ok: bool | None, eye_why: str | None) -> CardDecision:
    """게이트 결과 → 카드 결정 (순수). emit 은 **항상 True**.

    belle 09-03: 멈추는 구간마다 확대 사진 1장 — 검사는 표시만 조정한다.
      · emit: 항상 True. hold/pair FAIL·눈 불일치·측정불가 어느 것도 카드를
        없애지 않는다 (종전 "FAIL freeze = 미방출" 폐기 — quick-260903-upx).
      · draw_user_marks: 눈이 실제 불일치(eye_mismatch)일 때만 False — 마크가
        엉뚱한 사지에 얹혔거나 상태가 틀린 표시는 그리지 않는다(사진은 남긴다).
        눈이 못 본 것(frame_missing/no_api_key)·안 본 것(midrange/skip)은 True.
      · hold_state / pair_state: 게이트 reason 그대로(HoldResult/PairResult.reason
        어휘 — 재해석 0), 미실행(None)은 "unmeasured". peak pass-through 는
        호출측이 hold_reason="peak" 로 표기한다.
      · eye_state: eye_state() 매핑.
    """
    return CardDecision(
        emit=True,
        draw_user_marks=not eye_mismatch(eye_ok, eye_why),
        hold_state=hold_reason or STATE_UNMEASURED,
        pair_state=pair_reason or STATE_UNMEASURED,
        eye_state=eye_state(eye_ok, eye_why),
    )
