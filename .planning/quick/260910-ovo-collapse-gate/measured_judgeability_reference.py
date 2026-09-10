"""판정 가능성(judgeability) 지표 — 저장된 분석 doc 만으로 계산하는 순수 함수.

목적: "이 관절을 실제로 관측했는가"를 doc 만으로 판정한다. GPU 0 · Pod 0 · Gemini 0.
프로덕션 코드 무접촉 (읽기 전용 측정 스크립트).

입력은 Firestore 분석 doc(또는 backend/evals/realfixture/fixtures/*.json 의 동일 형식)
하나. 쓰는 필드는 전부 이미 저장돼 있는 것뿐:
  result.keypointReport.{joints, frames, data, confidence}   ← 2D 정규화 좌표 + per-kp conf
  result.deductionBreakdown.records[].{criterion, atFrameIdx}
  result.faultZoomComparisons[].{joint, criterion, userFrameIdx}
  result.joints3dFrames                                       ← 9fps 각도 프레임 수

판정 불가 = (a) OR (b) OR (c). 서로 직교하는 축이라 AND 가 아니다.

  (a) 절대 신뢰도 바닥 — 각도를 정의하는 3점의 **최소** conf 가 CONF_MIN 미만인
      프레임이 감점 순간의 DTW 정렬 창 안에서 절반 초과.
  (b) 붕괴 — 사지 3점이 거의 공선이고 가로(단축) 산포가 몸통 대비 아주 작다.
      ★ 폴을 곧게 잡은 정상 팔도 폴과 공선이다 → (b) 단독 사용 금지.
  (c) 좌우 자기모순 — 좌/우 앵커 쌍의 x 순서 부호가 프레임마다 뒤집히면
      그 클립의 좌(또는 우) 축 전체를 강등. 관절 단위가 아니라 축 단위.

임계값 출처 (새 임계 도입 최소화):
  CONF_MIN = 0.5
      표시층이 이미 쓰는 값을 그대로 재사용.
      backend/shared/python/sunity_shared/analysis/fault_zoom.py:115  `_KP_CONF_MIN = 0.5`
      (앱 KeypointOverlay.KEYPOINT_LOW_CONFIDENCE_THRESHOLD = 0.5 와 동일 선례)
      ※ reliability.py:22 의 _LOW_THRESHOLD(0.4) 는 쓰지 않는다 — 그 모듈은
        프로덕션 미배선이고, 0.5 쪽이 이미 사용자에게 보이는 선이다.
  DTW_RADIUS = 12  (9fps 프레임)
      backend/shared/python/sunity_shared/analysis/motiondtw.py:178  `radius: int = 12`
      align_and_compare 의 기본 밴드 폭 = 정렬 불확실성. 새 상수 아님.
  FRAC_OVER = 0.5   ("절반 초과" — 과제 문언 그대로)
  COLLAPSE_ASPECT = 0.10
      ★ 신설 1/2. 근거는 대표 사례의 실측 서명:
        c64afae6 frame 162 right arm 의 3점 PCA 단축/장축 = 0.052
        (belle 관측 "가로 12px / 세로 220px" = 0.055 와 일치).
        같은 프레임 left arm(유효로 확인된 팔) = 0.748. 한 자릿수 넘게 벌어져 있다.
  COLLAPSE_LEN_FRAC = 0.60
      ★ 신설 2/2 — **사후 추가**. 초판은 공선성만 봤고, 그 결과 kip-up 의 **곧게 편
        정상 다리**가 전부 발화해 변별 게이트를 깼다 (aspect 0.016~0.042). 과제가
        경고한 함정("폴을 곧게 잡은 정상 팔도 공선")이 다리에서 그대로 재현된 것이다.
        실측으로 갈린 축은 **단축(foreshortening)**이었다:
          붕괴한 팔  c64afae6 f162 right_arm : L/medL = 0.46
          정상 곧은 다리 kipup f16 left/right_leg : L/medL = 1.16 / 0.88
        L = 두 분절 길이의 합, medL = 그 사지의 클립 중앙값. 0.60 은 0.46 과 0.88
        사이에 두되 붕괴 쪽에 가깝게 잡았다. **이 임계는 결과를 보고 도입했다** —
        곡선맞춤 위험이 있으므로 그 사실을 여기 박제한다.
  LR_FLIP_RATE = 0.20  (프레임 간 좌우 부호 뒤집힘 비율)

관절 이름공간: keypointReport 는 12점이며 wrist 를 `left_hand`/`right_hand` 로 부른다.
skeleton.JOINT_ANGLES / reliability.ANGLE_REQUIRED_KEYPOINTS 의 COCO wrist 를 그리로 매핑한다.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

import numpy as np

sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")

# 프로덕션 정의 재사용 — 각도 3점 사슬은 여기서만 온다 (중복 정의 금지).
from sunity_shared.analysis.reliability import ANGLE_REQUIRED_KEYPOINTS  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_ANGLES  # noqa: E402

# ── 임계값 ────────────────────────────────────────────────────────────────
CONF_MIN = 0.5           # fault_zoom.py:115 _KP_CONF_MIN
DTW_RADIUS = 12          # motiondtw.py:178 align_and_compare(radius=12), 9fps 단위
FRAC_OVER = 0.5
COLLAPSE_ASPECT = 0.10     # 신설 1/2 — 근거는 모듈 docstring
COLLAPSE_LEN_FRAC = 0.60   # 신설 2/2 — 사후 추가, 모듈 docstring 에 경위 박제
LR_FLIP_RATE = 0.20

# COCO wrist → keypointReport 이름
_KR_ALIAS = {"left_wrist": "left_hand", "right_wrist": "right_hand"}

# 사지 3점 (붕괴 축 (b) 대상)
LIMB_TRIPLES = {
    "left_arm": ("left_shoulder", "left_elbow", "left_hand"),
    "right_arm": ("right_shoulder", "right_elbow", "right_hand"),
    "left_leg": ("left_hip", "left_knee", "left_ankle"),
    "right_leg": ("right_hip", "right_knee", "right_ankle"),
}
# 각도 관절 → 그 각도가 놓인 사지
JOINT_LIMB = {
    "left_elbow": "left_arm", "right_elbow": "right_arm",
    "left_shoulder": "left_arm", "right_shoulder": "right_arm",
    "left_hip": "left_leg", "right_hip": "right_leg",
    "left_knee": "left_leg", "right_knee": "right_leg",
}
# (c) 좌우 순서 앵커 쌍 — keypointReport 에 ear 가 없어 어깨/엉덩이/무릎으로 잰다.
LR_ANCHORS = ("shoulder", "hip", "knee")


def angle_triple(joint: str) -> tuple[str, str, str]:
    """각도 관절 이름 → keypointReport 이름공간의 3점.

    출처: reliability.ANGLE_REQUIRED_KEYPOINTS(`{joint}_flex` 키)를 1순위로 쓰고,
    거기 없는 hip/shoulder 변형은 skeleton.JOINT_ANGLES 로 떨어진다. 둘은 같은 사슬이다.
    """
    key = f"{joint}_flex"
    if key in ANGLE_REQUIRED_KEYPOINTS:
        names = ANGLE_REQUIRED_KEYPOINTS[key]
    else:
        names = list(JOINT_ANGLES[joint])
    return tuple(_KR_ALIAS.get(n, n) for n in names)  # type: ignore[return-value]


# ── doc → 배열 ─────────────────────────────────────────────────────────────
@dataclass
class Clip:
    name: str
    joints: list[str]
    frames: int              # keypointReport 프레임 수 (보통 18fps)
    conf: np.ndarray         # (F, K)
    xy: np.ndarray           # (F, K, 2) 정규화 좌표
    frames9: int             # joints3d/각도 프레임 수 (9fps)
    ratio: float             # frames / frames9
    records: list[dict] = field(default_factory=list)
    cards: list[dict] = field(default_factory=list)

    def i(self, name: str) -> int:
        return self.joints.index(name)


def load_clip(doc: dict, name: str) -> Clip:
    r = doc["result"]
    kr = r["keypointReport"]
    J = list(kr["joints"])
    F = int(kr["frames"])
    K = len(J)
    conf = np.asarray(kr["confidence"], dtype=float).reshape(F, K)
    xy = np.asarray(kr["data"], dtype=float).reshape(F, K, 2)
    f9 = int(r.get("joints3dFrames") or 0) or F
    return Clip(
        name=name, joints=J, frames=F, conf=conf, xy=xy, frames9=f9,
        ratio=F / f9 if f9 else 1.0,
        records=list((r.get("deductionBreakdown") or {}).get("records") or []),
        cards=list(r.get("faultZoomComparisons") or []),
    )


def body_scale(c: Clip) -> float:
    """몸통 길이(어깨중점↔엉덩이중점)의 클립 중앙값. 정규화 좌표 단위.

    어깨 폭 단독은 역립·회전에서 0 에 가깝게 붕괴해 분모로 못 쓴다 (실측: 대표
    사례 f160→f164 에서 0.114→0.050 으로 요동). 몸통 길이는 훨씬 안정적이다.
    """
    sh = (c.xy[:, c.i("left_shoulder")] + c.xy[:, c.i("right_shoulder")]) / 2
    hp = (c.xy[:, c.i("left_hip")] + c.xy[:, c.i("right_hip")]) / 2
    return float(np.median(np.linalg.norm(sh - hp, axis=1)))


# ── 감점 순간 앵커 ────────────────────────────────────────────────────────
def deduction_anchor(c: Clip, criterion: str, joint: str | None) -> tuple[int | None, str]:
    """그 감점을 잰 순간을 keypointReport 프레임 인덱스로.

    우선순위:
      1) record.atFrameIdx (9fps, quick-260801-gbk) → * ratio
      2) 같은 criterion / 같은 joint 의 faultZoomComparisons[].userFrameIdx (이미 kr 공간)
      3) 없음 → 창 = 클립 전체 (호출측이 'whole' 로 표기)
    """
    for rec in c.records:
        if rec.get("criterion") != criterion:
            continue
        at = rec.get("atFrameIdx")
        if isinstance(at, int) and not isinstance(at, bool) and at >= 0:
            return int(round(at * c.ratio)), "atFrameIdx"
    for z in c.cards:
        if z.get("criterion") == criterion or (joint and z.get("joint") == joint):
            u = z.get("userFrameIdx")
            if isinstance(u, int) and not isinstance(u, bool) and u >= 0:
                return int(u), "cardFrame"
    return None, "whole"


def window(c: Clip, anchor: int | None, radius9: int = DTW_RADIUS) -> tuple[int, int]:
    """DTW 정렬 창 → keypointReport 프레임 구간 [lo, hi)."""
    if anchor is None:
        return 0, c.frames
    w = int(round(radius9 * c.ratio))
    return max(0, anchor - w), min(c.frames, anchor + w + 1)


# ── 축 (a) 절대 신뢰도 바닥 ────────────────────────────────────────────────
def axis_a(c: Clip, joint: str, lo: int, hi: int) -> dict:
    tri = angle_triple(joint)
    idx = [c.i(n) for n in tri]
    m = np.min(c.conf[lo:hi, idx], axis=1)      # 3점 중 최소
    frac = float(np.mean(m < CONF_MIN)) if m.size else 1.0
    return {
        "fires": frac > FRAC_OVER,
        "frac_below": round(frac, 4),
        "median_min_conf": round(float(np.median(m)), 4) if m.size else None,
        "triple": tri,
        "n": int(m.size),
    }


# ── 축 (b) 붕괴 ────────────────────────────────────────────────────────────
def _limb_series(c: Clip, limb: str) -> tuple[np.ndarray, np.ndarray]:
    """사지별 (프레임당 aspect, 프레임당 L/medL)."""
    idx = [c.i(n) for n in LIMB_TRIPLES[limb]]
    P = c.xy[:, idx, :]                       # (F,3,2)
    L = (np.linalg.norm(P[:, 1] - P[:, 0], axis=1)
         + np.linalg.norm(P[:, 2] - P[:, 1], axis=1))
    med = float(np.median(L)) or 1e-9
    asp = np.empty(c.frames)
    for f in range(c.frames):
        q = P[f] - P[f].mean(axis=0)
        _, _, vt = np.linalg.svd(q, full_matrices=False)
        pr = q @ vt.T
        major = float(pr[:, 0].max() - pr[:, 0].min())
        minor = float(pr[:, 1].max() - pr[:, 1].min())
        asp[f] = minor / major if major > 1e-9 else 1.0
    return asp, L / med


def axis_b(c: Clip, joint: str, lo: int, hi: int, anchor: int | None) -> dict:
    """붕괴 = 공선(aspect<0.10) AND 단축(L < 0.60 * 클립 중앙 길이).

    판정 지점은 **그 카드가 잘린 프레임(anchor)** 이다 — 사진 한 장이 의미를
    가지느냐가 belle 의 불만이므로, 창 평균이 아니라 그 순간을 본다.
    anchor 가 없으면 창 안 붕괴 프레임 비율이 절반 초과인지로 떨어진다.
    """
    limb = JOINT_LIMB[joint]
    asp, lr = _limb_series(c, limb)
    hit = (asp < COLLAPSE_ASPECT) & (lr < COLLAPSE_LEN_FRAC)
    frac = float(np.mean(hit[lo:hi])) if hi > lo else 0.0
    if anchor is not None and 0 <= anchor < c.frames:
        fires = bool(hit[anchor])
        at = {"aspect": round(float(asp[anchor]), 4), "len_ratio": round(float(lr[anchor]), 4)}
    else:
        fires = frac > FRAC_OVER
        at = None
    return {
        "fires": fires, "frac_collapsed": round(frac, 4), "at_anchor": at,
        "median_aspect": round(float(np.median(asp[lo:hi])), 4) if hi > lo else None,
        "limb": limb, "n": int(hi - lo),
    }


# ── 축 (c) 좌우 자기모순 (축 단위) ─────────────────────────────────────────
def axis_c(c: Clip) -> dict:
    """좌/우 앵커 쌍의 x 순서 부호가 프레임마다 뒤집히는 비율 (클립 전체).

    부호가 계속 뒤집히면 그 클립에서 좌/우 라벨 자체를 믿을 수 없다 → 좌·우 축
    전체를 판정 불가로 강등한다. 몸이 실제로 도는 동작은 부호가 몇 번 바뀌지만
    프레임마다 뒤집히지는 않는다.
    """
    rates = {}
    for a in LR_ANCHORS:
        li, ri = c.i(f"left_{a}"), c.i(f"right_{a}")
        dx = c.xy[:, li, 0] - c.xy[:, ri, 0]
        s = np.sign(dx)
        s = s[s != 0]
        rates[a] = float(np.mean(s[1:] != s[:-1])) if s.size > 1 else 0.0
    worst = max(rates.values()) if rates else 0.0
    return {
        "fires": worst > LR_FLIP_RATE,
        "flip_rates": {k: round(v, 4) for k, v in rates.items()},
        "worst": round(worst, 4),
    }


# ── 종합 ───────────────────────────────────────────────────────────────────
def judge_clip(doc: dict, name: str, whole_clip: bool = False) -> dict:
    """whole_clip=True 면 (a) 창을 클립 전체로 강제 — 감점 순간 앵커가 없는 구본 대조용."""
    c = load_clip(doc, name)
    scale = body_scale(c)
    cax = axis_c(c)

    units = []
    for rec in c.records:
        crit = rec.get("criterion")
        if not isinstance(crit, str):
            continue
        units.append(crit)

    # 감점이 걸린 관절 = angle_vs_reference__{joint} 로 이름이 붙은 것만 관절 단위로
    # 판정할 수 있다. region 기반 criterion(split_angle, leg_extension 등)은
    # criterion_units_from_records 가 REGION_MEMBERS 전체를 붙이므로 별도 취급한다.
    rows = []
    for crit in units:
        joint = crit.split("__", 1)[1] if crit.startswith("angle_vs_reference__") else None
        targets = [joint] if joint in JOINT_LIMB else _region_joints(crit)
        anchor, src = deduction_anchor(c, crit, joint)
        lo, hi = (0, c.frames) if whole_clip else window(c, anchor)
        if whole_clip:
            src = src + "/whole"
        for j in targets:
            a = axis_a(c, j, lo, hi)
            b = axis_b(c, j, lo, hi, anchor)
            rows.append({
                "criterion": crit, "joint": j, "anchor": anchor, "anchor_src": src,
                "win": [lo, hi], "a": a, "b": b,
                "c_axis": cax["fires"],
                "unjudgeable": bool(a["fires"] or b["fires"] or cax["fires"]),
            })
    return {
        "clip": name, "whole_clip": whole_clip, "frames": c.frames, "frames9": c.frames9, "ratio": c.ratio,
        "body_scale": round(scale, 4), "axis_c": cax, "rows": rows,
    }


def _region_joints(crit: str) -> list[str]:
    """region 기반 criterion → 그 부위의 각도 관절들 (fault_zoom.CRITERION_REGION 미러)."""
    from sunity_shared.analysis.fault_zoom import CRITERION_REGION
    region = CRITERION_REGION.get(crit)
    if region == "legs":
        return ["left_hip", "right_hip", "left_knee", "right_knee"]
    if region == "arms":
        return ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow"]
    return []
