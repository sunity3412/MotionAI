"""p35 자율 발견 스크린 v1 — 전구간 + 홀드 구간 결함 후보 스크리닝.

belle 방향 원문(2026-08-08): "내가 바라는 건 너가 자체적으로 찾는 것" — 사람이 짚기 전에
기계가 스스로 결함 후보를 찾아내는 자율 발견 스크린.

구성:
- v0 재현 스펙: 08-08 세션 인라인으로 검증했던 전구간 스크린(피처 14종 짝 집계 + 미러
  체크)을 리포 스크립트로 영구화. 인라인 실측 지식은 V0_REGRESSION(--regress-v0) 게이트로
  코드에 박제 — 세션/재부팅 소실(08-08 scratchpad 소실 사건)에도 재실행 가능.
- v1 신규: 홀드 구간 인식(패널별 저에너지 구간) + 양쪽 모두 홀드인 짝 한정 별도 집계 +
  r03 verdict 하네스(--verdict-r03) — belle 승인 r03("엘보 몸-폴 편차")을 기계가 블라인드로
  재발견하는지 3게이트(G1 재발견 / G2 과검출 없음 / G3 유지)로 판정.

원칙:
- 스크린 피처·집계 로직에 동작명 분기 0 (motion-routing 일반화 원칙). 동작명은
  POLE_X_CACHE 의 데이터 키와 V0_REGRESSION·verdict 하네스(실측 대조 목적)에만 존재.
- r03 재발견 성공을 위한 임계 튜닝 금지 — 상수는 전부 v0 스펙 또는 구조 유도이며,
  verdict 는 기본 파라미터 1회 판정(curve-fit 금지). 성공이든 실패든 수치 근거와 함께
  정직 기록이 목적.
- 순수 numpy + stdlib. cv2 사용 금지(로컬 venv 에 없음). PIL·렌더러는 폴 재계산 폴백
  함수(_detect_pole_lazy) 내부에서만 lazy import — render_compare_prototype 는 module
  top 에서 PIL·imageio_ffmpeg 를 당기므로 top-level import 금지(렌더러 무수정 재사용).

입력: .planning/phases/35-server-rendered-comparison-video/data/{motion}/align.json
(리포 영구화 데이터 d266cb8d — 15fps RTMW 재추출 + DTW 정렬곡선 curveRefSec).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# 상수 — 전부 v0 재현 스펙 또는 구조 유도. r03 verdict 통과를 목적으로 한 변경 금지:
# 값을 바꾸려면 --regress-v0 재통과 + 변경 근거 주석이 필요하다.
# ---------------------------------------------------------------------------

CONF_GATE = 0.35
# ^ v0 재현 스펙. 렌더러 폴 문법(render_compare_prototype._pole_gap_series 등)은 0.5 를
#   쓰지만, 스크린은 결함 '후보 발굴'이 목적이라 v0 이 0.35 로 넓게 잡았다 — 값이 다른
#   것이 의도임을 명시해 둔다.

VALID_MIN = 0.40       # 유효 짝 비율 미달 피처는 집계 제외 표기 (v0 스펙)
SCALE_ANGLE = 30.0     # 각도 피처 정규화 분모(도) — v0 스펙
SCALE_GAP = 0.15       # 간격 피처 정규화 분모(몸통비) — 렌더러 유의미 마진 0.15 동일 구조
HOLD_SMOOTH_K = 5      # 홀드 에너지 이동평균 창(프레임) — v1 스펙
HOLD_PCT = 40          # 저에너지 임계 백분위 — verdict 는 이 값 고정(--hold-pct 는 관찰 전용)
HOLD_MIN_S = 1.0       # 홀드 최소 지속(초) — 15fps 기준 15프레임
HOLD_PAIR_MIN = 10     # 홀드 짝 최소 수 — 미만이면 "홀드 판정 불가" 정직 출력(수치 날조 금지)
MIRROR_IMPROVE = 0.03  # 미러 스왑 개선률 임계 — v0 스펙(이상이면 거울상, 미만 동측)

ANGLE_SPACE = "norm"
# ^ 좌표 공간 채택 근거 박제 (plan 명문: "v0 값을 재현하는 쪽 채택 + 채택 근거 주석"):
#   px 관례(kp x [W,H])로는 v0 인라인 실측이 재현되지 않아 정규화 좌표 관례 1회 교차를
#   실행했고, 정규화 공간이 v0 실측 4건을 전부 재현했다 — powerspin 실측 대조(08-08):
#     px  : 벌림각 diff -30.50 / u_med 46.37 / r_med 84.94, ankle gap diff +0.341 (FAIL)
#     norm: 벌림각 diff -24.55 / u_med 27.74 / r_med 98.05, ankle gap diff +0.555 (PASS)
#   따라서 v0 은 정규화 좌표 공간에서 일관 계산했음이 실측으로 확정 — 각도·간격·몸통·
#   에너지·미러 전부 정규화 공간으로 통일한다(공간 혼합 금지). 간격 분모 torso 도 정규화
#   공간 길이 ||sho_mid-hip_mid|| 다 (plan 의 px 공식 서술은 planner 재구성이었고, 게이트가
#   박제한 v0 실측이 정본 — 실측 > 문서). px 는 --regress-v0 실패 시 교차 진단 전용.

POLE_X_CACHE: dict[str, dict[str, float]] = {
    # 08-08 폴 감지 프로브 실측 + 증거 스틸 눈검증 출처(260808-epy — _detect_pole 산출을
    # 스틸로 확인). 영상 원본이 scratchpad 세션 의존이라 캐시가 기본 경로다.
    # --pole-frames-dir 지정 시에만 _detect_pole 재계산 폴백. 동작명은 이 캐시의 데이터
    # 키로만 존재 — 스크린 피처·집계 로직에는 동작명 분기가 없다.
    "elbow": {"user": 0.4992, "ref": 0.5003},
    "powerspin": {"user": 0.502, "ref": 0.502},
    "kipup": {"user": 0.498, "ref": 0.501},
    "pdshapefault": {"user": 0.4996, "ref": 0.4993},
    "peterpan": {"user": 0.501, "ref": 0.513},
}

BODY12 = (
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
)
_SWAP_NAME = {j: j.replace("left_", "right_") if j.startswith("left_")
              else j.replace("right_", "left_") for j in BODY12}

GAP_JOINTS = ("left_elbow", "right_elbow", "left_wrist", "right_wrist",
              "left_knee", "right_knee", "left_ankle", "right_ankle")

FEATURE_ORDER = (
    "gap_left_elbow", "gap_right_elbow", "gap_left_wrist", "gap_right_wrist",
    "gap_left_knee", "gap_right_knee", "gap_left_ankle", "gap_right_ankle",
    "gap_hip_mid", "gap_sho_mid", "bodyline",
    "split_angle", "knee_angle_left", "knee_angle_right",
)

DEFAULT_MOTIONS = "elbow,powerspin,kipup,pdshapefault,peterpan"
DEFAULT_DATA_DIR = ".planning/phases/35-server-rendered-comparison-video/data"


# ---------------------------------------------------------------------------
# 데이터 적재
# ---------------------------------------------------------------------------

def _load_align(path: Path) -> dict:
    align = json.load(open(path))
    need = ("fps", "userFrames", "refFrames", "userSize", "refSize",
            "userKp", "refKp", "userScore", "refScore", "curveRefSec", "joints17")
    for k in need:
        if k not in align:
            raise KeyError(f"align.json 필수 키 없음: {k} (구버전 포맷?)")
    return align


def _panel(align: dict, side: str) -> dict:
    """패널(user/ref) 배열 전개 + 몸통 길이 시계열.

    torso = ||어깨중점-힙중점|| 정규화 좌표 공간 길이 (ANGLE_SPACE 주석의 v0 재현 근거 —
    px 아님). 무효(<=1e-3) 프레임은 패널 중앙값 대체 — 렌더러 _pole_gap_series 의
    분모 안정화 관례 준용."""
    aj = list(align["joints17"])
    F = int(align[f"{side}Frames"])
    kp = np.asarray(align[f"{side}Kp"], dtype=float).reshape(F, len(aj), 2)
    sc = np.asarray(align[f"{side}Score"], dtype=float)
    W, H = (float(v) for v in align[f"{side}Size"])
    sh = (kp[:, aj.index("left_shoulder")] + kp[:, aj.index("right_shoulder")]) / 2
    hp = (kp[:, aj.index("left_hip")] + kp[:, aj.index("right_hip")]) / 2
    torso = np.linalg.norm(sh - hp, axis=1)
    valid = torso > 1e-3
    tmed = float(np.nanmedian(torso[valid])) if valid.any() else 1.0
    return {"aj": aj, "F": F, "kp": kp, "sc": sc, "W": W, "H": H,
            "sh": sh, "hp": hp, "torso": np.where(valid, torso, tmed)}


def _pair_indices(align: dict) -> np.ndarray:
    """v0 짝 스펙: user 프레임 i -> ref 프레임 j = round(curveRefSec[i] x fps),
    [0, refFrames-1] 클립."""
    fps = float(align["fps"])
    curve = np.asarray(align["curveRefSec"], dtype=float)
    return np.clip(np.round(curve * fps).astype(int), 0, int(align["refFrames"]) - 1)


# ---------------------------------------------------------------------------
# 피처 14종 (프레임별, 패널별)
# ---------------------------------------------------------------------------

def _vec_angle_deg(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """두 벡터열의 사이각(도). 퇴화(길이 ~0) 벡터는 NaN."""
    n1 = np.linalg.norm(a, axis=1)
    n2 = np.linalg.norm(b, axis=1)
    denom = n1 * n2
    with np.errstate(invalid="ignore", divide="ignore"):
        cos = np.sum(a * b, axis=1) / np.where(denom > 1e-9, denom, np.nan)
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def _split_angle_series(p: dict, space: str) -> np.ndarray:
    """다리 벌림각: hip_mid->left_ankle 와 hip_mid->right_ankle 사이각(도).

    space="norm" 이 정본(ANGLE_SPACE 주석의 v0 재현 근거). "px" 는 --regress-v0
    실패 시 교차 진단 전용."""
    aj = p["aj"]
    scale = np.array([p["W"], p["H"]]) if space == "px" else np.array([1.0, 1.0])
    hp = p["hp"] * scale
    la = p["kp"][:, aj.index("left_ankle")] * scale
    ra = p["kp"][:, aj.index("right_ankle")] * scale
    ang = _vec_angle_deg(la - hp, ra - hp)
    conf = np.minimum.reduce([p["sc"][:, aj.index(n)]
                              for n in ("left_hip", "right_hip", "left_ankle", "right_ankle")])
    return np.where(conf >= CONF_GATE, ang, np.nan)


def _panel_features(p: dict, pole_x: float | None) -> dict[str, np.ndarray]:
    """피처 14종: 폴간격 10(관절 8 + hip_mid/sho_mid) + bodyline 1 + 벌림각 1 + 무릎각 2.

    pole_x 가 None(캐시/frames 둘 다 없음)이면 폴 파생 11종은 생성하지 않는다(fail-closed)."""
    feats: dict[str, np.ndarray] = {}
    aj = p["aj"]
    if pole_x is not None:
        for jn in GAP_JOINTS:
            ji = aj.index(jn)
            gap = np.abs(p["kp"][:, ji, 0] - pole_x) / p["torso"]
            feats[f"gap_{jn}"] = np.where(p["sc"][:, ji] >= CONF_GATE, gap, np.nan)
        for name, mid, (ja, jb) in (
            ("gap_hip_mid", p["hp"], ("left_hip", "right_hip")),
            ("gap_sho_mid", p["sh"], ("left_shoulder", "right_shoulder")),
        ):
            conf = np.minimum(p["sc"][:, aj.index(ja)], p["sc"][:, aj.index(jb)])
            gap = np.abs(mid[:, 0] - pole_x) / p["torso"]
            feats[name] = np.where(conf >= CONF_GATE, gap, np.nan)
        # 몸라인-폴 편차: max(sho_mid, hip_mid) — np.maximum 은 NaN 전파라 둘 다 유효일 때만 값.
        feats["bodyline"] = np.maximum(feats["gap_sho_mid"], feats["gap_hip_mid"])
    feats["split_angle"] = _split_angle_series(p, ANGLE_SPACE)
    for side in ("left", "right"):
        k, h, a = (aj.index(f"{side}_{x}") for x in ("knee", "hip", "ankle"))
        v1 = p["kp"][:, h] - p["kp"][:, k]
        v2 = p["kp"][:, a] - p["kp"][:, k]
        ang = _vec_angle_deg(v1, v2)
        conf = np.minimum.reduce([p["sc"][:, i] for i in (k, h, a)])
        feats[f"knee_angle_{side}"] = np.where(conf >= CONF_GATE, ang, np.nan)
    return feats


def _feature_kind(name: str) -> str:
    return "angle" if name == "split_angle" or name.startswith("knee_angle") else "gap"


# ---------------------------------------------------------------------------
# 짝 집계 (v0 스펙)
# ---------------------------------------------------------------------------

def _aggregate(u_feats: dict, r_feats: dict, jmap: np.ndarray,
               scope: np.ndarray) -> list[dict]:
    """diff[i] = user[i] - ref[j(i)] (양수 = user 가 큼). 유효 짝 = 양쪽 non-NaN.

    유효율 < VALID_MIN 피처는 집계 제외 표기. 집계 = 유효 diff 의 median,
    scaled = |median| / (각도 SCALE_ANGLE, 간격 SCALE_GAP). 패널별 중앙값(user_med/
    ref_med)은 각 시계열의 독립 nanmedian(짝 동시 유효 요구 없음) — v0 실측 재현 확정
    관례(powerspin 벌림각 u 27.74/r 98.05 재현, ANGLE_SPACE 주석 참조). 벌림각
    "u 27.7 vs r 98.1" 류 대조용."""
    total = int(scope.sum())
    rows = []
    for name in FEATURE_ORDER:
        if name not in u_feats:
            continue  # 폴 파생 피처 제외 상태(pole_x 없음) — 사유는 모션 레벨에 기록
        u = u_feats[name][scope]
        r = r_feats[name][jmap[scope]]
        d = u - r
        m = np.isfinite(d)
        n = int(m.sum())
        rate = (n / total) if total else 0.0
        kind = _feature_kind(name)
        row: dict = {"feature": name, "kind": kind, "n_valid": n,
                     "valid_rate": round(rate, 3),
                     "included": bool(rate >= VALID_MIN and n > 0)}
        if row["included"]:
            med = float(np.median(d[m]))
            row["median"] = round(med, 4)
            row["scaled"] = round(abs(med) / (SCALE_ANGLE if kind == "angle" else SCALE_GAP), 3)
            row["user_med"] = round(float(np.nanmedian(u)), 4)
            row["ref_med"] = round(float(np.nanmedian(r)), 4)
        rows.append(row)
    inc = sorted([r for r in rows if r["included"]], key=lambda r: -r["scaled"])
    for i, r in enumerate(inc):
        r["rank"] = i + 1
    return inc + [r for r in rows if not r["included"]]


# ---------------------------------------------------------------------------
# 미러 체크 (v0 스펙)
# ---------------------------------------------------------------------------

def _mirror_check(up: dict, rp: dict, jmap: np.ndarray) -> dict:
    """body12 힙중심·몸통정규 pose feature 로 정상 ref vs 스왑 ref(L/R 라벨 스왑 +
    힙중심 상대 x 부호 반전 = 물리 거울) 평균 L2 비교. conf 미달 관절은 0 처리
    (렌더러 feat 방식 준용). 좌표는 정규화 공간(ANGLE_SPACE 주석의 v0 관례 통일).
    개선률 >= MIRROR_IMPROVE 일 때만 거울상."""
    def feat(p: dict) -> np.ndarray:
        idx = [p["aj"].index(j) for j in BODY12]
        rel = (p["kp"][:, idx, :] - p["hp"][:, None, :]) / p["torso"][:, None, None]
        ok = p["sc"][:, idx] >= CONF_GATE
        return np.where(ok[:, :, None], rel, 0.0)

    U = feat(up)
    Rn = feat(rp)[jmap]
    swap_idx = [BODY12.index(_SWAP_NAME[j]) for j in BODY12]
    Rs = Rn[:, swap_idx, :] * np.array([-1.0, 1.0])
    d_n = float(np.mean(np.linalg.norm((U - Rn).reshape(len(U), -1), axis=1)))
    d_s = float(np.mean(np.linalg.norm((U - Rs).reshape(len(U), -1), axis=1)))
    improve = (d_n - d_s) / d_n if d_n > 1e-9 else 0.0
    return {"d_normal": round(d_n, 4), "d_swap": round(d_s, 4),
            "improve": round(improve, 4),
            "verdict": "mirror" if improve >= MIRROR_IMPROVE else "same_side"}


# ---------------------------------------------------------------------------
# 홀드 구간 인식 (v1 신규)
# ---------------------------------------------------------------------------

def _moving_mean_nan(x: np.ndarray, k: int) -> np.ndarray:
    """NaN-인지 중심 이동평균 — 창 안 유효값 평균, 전무하면 NaN."""
    out = np.full_like(x, np.nan)
    half = k // 2
    for i in range(len(x)):
        w = x[max(0, i - half):i + half + 1]
        v = w[np.isfinite(w)]
        if len(v):
            out[i] = float(np.mean(v))
    return out


def _hold_intervals(p: dict, fps: float, hold_pct: int) -> dict:
    """패널별 저에너지 구간: energy[t] = body12 중 양 프레임 conf>=CONF_GATE 관절의
    ||kp[t]-kp[t-1]|| / torso 평균(정규화 공간 — v0 관례 통일. 유효 관절 <4 이면 NaN)
    -> 이동평균 k=HOLD_SMOOTH_K -> 유효 energy 의 p{hold_pct} 미만 연속 run >=
    HOLD_MIN_S 만 홀드."""
    idx = [p["aj"].index(j) for j in BODY12]
    kp = p["kp"][:, idx, :]
    sc = p["sc"][:, idx]
    F = p["F"]
    energy = np.full(F, np.nan)
    for t in range(1, F):
        ok = (sc[t] >= CONF_GATE) & (sc[t - 1] >= CONF_GATE)
        if int(ok.sum()) < 4:
            continue
        disp = np.linalg.norm(kp[t, ok] - kp[t - 1, ok], axis=1) / p["torso"][t]
        energy[t] = float(np.mean(disp))
    sm = _moving_mean_nan(energy, HOLD_SMOOTH_K)
    fin = sm[np.isfinite(sm)]
    if not len(fin):
        return {"intervals": [], "threshold": None, "n_energy_valid": 0,
                "reason": "유효 에너지 프레임 0 (conf 게이트 전멸)"}
    thr = float(np.percentile(fin, hold_pct))
    mask = np.isfinite(sm) & (sm < thr)
    min_run = int(round(HOLD_MIN_S * fps))
    intervals: list[tuple[int, int]] = []
    i = 0
    while i < F:
        if mask[i]:
            j = i
            while j + 1 < F and mask[j + 1]:
                j += 1
            if j - i + 1 >= min_run:
                intervals.append((i, j))
            i = j + 1
        else:
            i += 1
    return {"intervals": intervals, "threshold": round(thr, 5),
            "n_energy_valid": int(len(fin)), "reason": None}


def _intervals_sec(intervals: list[tuple[int, int]], fps: float) -> list[list[float]]:
    return [[round(i0 / fps, 2), round(i1 / fps, 2)] for i0, i1 in intervals]


def _hold_pair_mask(u_iv: list, r_iv: list, jmap: np.ndarray, uF: int, rF: int) -> np.ndarray:
    """홀드 짝 = user 프레임 i 와 짝 ref 프레임 j 가 양쪽 모두 홀드 구간에 속하는 짝."""
    u_in = np.zeros(uF, dtype=bool)
    for i0, i1 in u_iv:
        u_in[i0:i1 + 1] = True
    r_in = np.zeros(rF, dtype=bool)
    for i0, i1 in r_iv:
        r_in[i0:i1 + 1] = True
    return u_in & r_in[jmap]


# ---------------------------------------------------------------------------
# 폴 x 해석 (캐시 우선, frames-dir 시에만 재계산)
# ---------------------------------------------------------------------------

def _detect_pole_lazy(frame_dir: Path, align: dict, side: str):
    """폴 재계산 폴백 — 렌더러 _detect_pole 재사용(렌더러 무수정). 여기서만 lazy import:
    render_compare_prototype 는 module top 에서 PIL·imageio_ffmpeg 를 당긴다."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from render_compare_prototype import _detect_pole  # noqa: PLC0415 - lazy 필수 (top-level 금지)
    return _detect_pole(frame_dir, align, side)


def _resolve_pole_x(motion: str, align: dict, frames_root: str | None) -> tuple[dict | None, str | None]:
    if motion in POLE_X_CACHE:
        c = POLE_X_CACHE[motion]
        return {"user": c["user"], "ref": c["ref"], "source": "cache"}, None
    if frames_root:
        out: dict = {"source": "recompute"}
        for side in ("user", "ref"):
            fd = Path(frames_root) / motion / side
            if not fd.is_dir():
                return None, f"pole frames dir 없음: {fd} — 폴 파생 피처 제외(fail-closed)"
            res = _detect_pole_lazy(fd, align, side)
            if res is None:
                return None, f"폴 감지 실패 {motion}/{side} — 폴 파생 피처 제외(fail-closed)"
            out[side] = float(res["xNorm"])
        return out, None
    return None, "POLE_X_CACHE 미등재 + --pole-frames-dir 미지정 — 폴 파생 피처 제외(fail-closed)"


# ---------------------------------------------------------------------------
# 모션 1개 스크린
# ---------------------------------------------------------------------------

def _screen_motion(align: dict, pole: dict | None, do_full: bool, do_hold: bool,
                   hold_pct: int) -> dict:
    fps = float(align["fps"])
    up = _panel(align, "user")
    rp = _panel(align, "ref")
    jmap = _pair_indices(align)
    u_feats = _panel_features(up, pole["user"] if pole else None)
    r_feats = _panel_features(rp, pole["ref"] if pole else None)
    out: dict = {"n_user_frames": up["F"], "n_ref_frames": rp["F"], "fps": fps}
    if do_full:
        scope = np.ones(up["F"], dtype=bool)
        out["full"] = {"n_pairs": int(scope.sum()),
                       "rows": _aggregate(u_feats, r_feats, jmap, scope)}
    if do_hold:
        uh = _hold_intervals(up, fps, hold_pct)
        rh = _hold_intervals(rp, fps, hold_pct)
        out["hold_intervals"] = {
            "user_sec": _intervals_sec(uh["intervals"], fps),
            "ref_sec": _intervals_sec(rh["intervals"], fps),
            "user_threshold": uh["threshold"], "ref_threshold": rh["threshold"],
            "hold_pct": hold_pct,
        }
        mask = _hold_pair_mask(uh["intervals"], rh["intervals"], jmap, up["F"], rp["F"])
        n = int(mask.sum())
        if uh["reason"] or rh["reason"]:
            out["hold"] = {"available": False, "n_pairs": n,
                           "reason": uh["reason"] or rh["reason"]}
        elif n < HOLD_PAIR_MIN:
            out["hold"] = {"available": False, "n_pairs": n,
                           "reason": f"홀드 짝 {n} < HOLD_PAIR_MIN {HOLD_PAIR_MIN} — 홀드 판정 불가"}
        else:
            out["hold"] = {"available": True, "n_pairs": n,
                           "rows": _aggregate(u_feats, r_feats, jmap, mask)}
    out["mirror"] = _mirror_check(up, rp, jmap)
    return out


# ---------------------------------------------------------------------------
# 출력
# ---------------------------------------------------------------------------

def _print_screen(motion: str, res: dict, scope: str) -> None:
    data = res.get(scope)
    if data is None:
        return
    title = "전구간" if scope == "full" else "홀드"
    if scope == "hold" and not data.get("available"):
        print(f"\n[{motion}] {title} 스크린: 판정 불가 — {data['reason']}")
        return
    print(f"\n[{motion}] {title} 스크린 (짝 {data['n_pairs']})")
    print(f"{'순위':>4} {'피처':<18} {'median(u-r)':>12} {'scaled':>7} {'유효율':>6} {'u_med':>9} {'r_med':>9}")
    for r in data["rows"]:
        if r["included"]:
            print(f"{r['rank']:>4} {r['feature']:<18} {r['median']:>+12.4f} "
                  f"{r['scaled']:>7.3f} {r['valid_rate']:>6.2f} "
                  f"{r['user_med']:>9.3f} {r['ref_med']:>9.3f}")
    excl = [r for r in data["rows"] if not r["included"]]
    if excl:
        print("  제외(유효율<{:.2f}): ".format(VALID_MIN)
              + ", ".join(f"{r['feature']}({r['valid_rate']:.2f})" for r in excl))


def _print_motion(motion: str, res: dict) -> None:
    print(f"\n===== {motion} (user {res['n_user_frames']}f / ref {res['n_ref_frames']}f) =====")
    hi = res.get("hold_intervals")
    if hi:
        print(f"홀드 구간 user: {hi['user_sec']} (thr {hi['user_threshold']})")
        print(f"홀드 구간 ref : {hi['ref_sec']} (thr {hi['ref_threshold']})")
    _print_screen(motion, res, "full")
    _print_screen(motion, res, "hold")
    m = res["mirror"]
    label = "거울상" if m["verdict"] == "mirror" else "동측"
    print(f"미러: {label} (d_normal {m['d_normal']}, d_swap {m['d_swap']}, 개선률 {m['improve']:+.4f})")


# ---------------------------------------------------------------------------
# V0_REGRESSION 게이트 (--regress-v0) — v0 인라인 실측을 코드에 박제 (영구화의 본체)
# ---------------------------------------------------------------------------

def _included_row(res: dict, motion: str, scope: str, feature: str) -> dict | None:
    data = res.get(motion, {}).get(scope)
    if not data or (scope == "hold" and not data.get("available")):
        return None
    for r in data["rows"]:
        if r["feature"] == feature and r["included"]:
            return r
    return None


def _split_px_diagnostic(align: dict) -> dict:
    """--regress-v0 벌림각 실패 시에만 쓰는 px 좌표 관례 1회 교차 진단(plan 명문).

    정본은 norm(ANGLE_SPACE 주석의 채택 근거) — px 가 다시 v0 값을 재현하게 되면
    관례 재검토 신호이므로 진단으로 남겨 둔다."""
    up = _panel(align, "user")
    rp = _panel(align, "ref")
    jmap = _pair_indices(align)
    u = _split_angle_series(up, "px")
    r = _split_angle_series(rp, "px")[jmap]
    d = u - r
    m = np.isfinite(d)
    if not m.any():
        return {"median": None}
    return {"median": round(float(np.median(d[m])), 2),
            "user_med": round(float(np.nanmedian(u)), 2),
            "ref_med": round(float(np.nanmedian(r)), 2)}


def run_regress_v0(results: dict, aligns: dict) -> tuple[bool, list[dict]]:
    """v0 인라인 실측(08-08) 재현 게이트. 실패 시 exit 1 + 실측치 출력.

    - powerspin 전구간: left_ankle 폴간격 median diff in [0.51, 0.61] (v0 +0.56)
      AND 벌림각 diff in [-27.5, -21.5] (v0 -24.5) AND 벌림각 u_med 27.7+-3 / r_med 98.1+-3.
    - elbow 전구간: 유효 전 피처 scaled <= 0.5 (v0 "전 피처 <=0.4x" + 여유 0.1).
    - 미러: 5동작 전부 동측.
    - kipup·peterpan: hard gate 없음(v0 서술이 정성적 "진폭 부족") — 참고 출력만."""
    checks: list[dict] = []

    def add(name: str, ok: bool, measured: str, band: str) -> None:
        checks.append({"check": name, "pass": bool(ok), "measured": measured, "band": band})

    la = _included_row(results, "powerspin", "full", "gap_left_ankle")
    add("powerspin left_ankle median", la is not None and 0.51 <= la["median"] <= 0.61,
        "없음(제외/미실행)" if la is None else f"{la['median']:+.4f}", "[0.51, 0.61]")

    sa = _included_row(results, "powerspin", "full", "split_angle")
    sa_ok = sa is not None and -27.5 <= sa["median"] <= -21.5
    add("powerspin 벌림각 median", sa_ok,
        "없음" if sa is None else f"{sa['median']:+.2f}", "[-27.5, -21.5]")
    add("powerspin 벌림각 u_med", sa is not None and abs(sa["user_med"] - 27.7) <= 3,
        "없음" if sa is None else f"{sa['user_med']:.2f}", "27.7+-3")
    add("powerspin 벌림각 r_med", sa is not None and abs(sa["ref_med"] - 98.1) <= 3,
        "없음" if sa is None else f"{sa['ref_med']:.2f}", "98.1+-3")

    el = results.get("elbow", {}).get("full")
    if el:
        bad = [r for r in el["rows"] if r["included"] and r["scaled"] > 0.5]
        add("elbow 전 피처 scaled<=0.5", not bad,
            "전건 충족" if not bad else ", ".join(f"{r['feature']}={r['scaled']}" for r in bad),
            "<=0.5")
    else:
        add("elbow 전 피처 scaled<=0.5", False, "elbow 미실행", "<=0.5")

    mirrors = {m: results[m]["mirror"]["verdict"] for m in results}
    not_same = [m for m, v in mirrors.items() if v != "same_side"]
    add("미러 5동작 동측", len(mirrors) == 5 and not not_same,
        f"{len(mirrors)}동작, 비동측={not_same or '없음'}", "5/5 same_side")

    ok = all(c["pass"] for c in checks)

    print("\n===== V0_REGRESSION (--regress-v0) =====")
    for c in checks:
        print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['check']}: {c['measured']} (기대 {c['band']})")
    for m in ("kipup", "peterpan"):  # 참고 출력만 — v0 서술이 정성적("진폭 부족")이라 hard gate 없음
        data = results.get(m, {}).get("full")
        if data:
            inc = [r for r in data["rows"] if r["included"]]
            neg = [r for r in inc if r["median"] < 0]
            print(f"  [참고] {m}: 유효 {len(inc)}피처 중 음수 diff {len(neg)} "
                  f"(음수 다수 = user 진폭 부족 방향)")
    if not sa_ok and "powerspin" in aligns:
        diag = _split_px_diagnostic(aligns["powerspin"])
        print(f"  [교차 진단] 벌림각 px 좌표 관례: {diag} — v0 값을 재현하는 쪽 채택(plan 명문)")
    print(f"  V0_REGRESSION: {'PASS' if ok else 'FAIL'}")
    return ok, checks


# ---------------------------------------------------------------------------
# r03 verdict 하네스 (--verdict-r03) — 기계 판정으로 서사 왜곡 차단
# ---------------------------------------------------------------------------

def _top3(data: dict) -> list[dict]:
    return [r for r in data["rows"] if r["included"]][:3]


def run_verdict_r03(results: dict) -> dict:
    """belle 승인 r03(엘보 몸-폴) 블라인드 재발견 기계 판정. 3게이트 각각 PASS/FAIL.

    어떤 게이트든 FAIL 이면 FAIL 로 출력 — 홀드 파라미터를 verdict 통과 목적으로 바꾸는 것
    금지(curve-fit 금지, 판정은 기본값 1회). 측정 불가도 FAIL(fail-closed)로 정직 기록."""
    v: dict = {}

    # G1 재발견: elbow 홀드 스크린에서 bodyline 또는 hip_mid 폴간격이 scaled top 3
    #            AND 해당 median diff > 0 (user 가 폴에서 더 멂 — r03 방향 일치).
    g1: dict = {"pass": False}
    eh = results.get("elbow", {}).get("hold")
    if eh is None:
        g1["reason"] = "elbow 홀드 스크린 미실행"
    elif not eh.get("available"):
        g1["reason"] = f"elbow 홀드 판정 불가: {eh['reason']}"
    else:
        top3 = _top3(eh)
        g1["top3"] = [{"feature": r["feature"], "scaled": r["scaled"], "median": r["median"]}
                      for r in top3]
        hits = [r for r in top3 if r["feature"] in ("bodyline", "gap_hip_mid") and r["median"] > 0]
        if hits:
            g1["pass"] = True
            g1["evidence"] = [{"feature": r["feature"], "rank": r["rank"],
                               "median": r["median"], "scaled": r["scaled"],
                               "user_med": r["user_med"], "ref_med": r["ref_med"]}
                              for r in hits]
        else:
            in3 = [r for r in top3 if r["feature"] in ("bodyline", "gap_hip_mid")]
            g1["reason"] = ("top3 에 bodyline/gap_hip_mid 없음" if not in3
                            else f"top3 진입했으나 median<=0: "
                                 + ", ".join(f"{r['feature']}={r['median']:+.4f}" for r in in3))
    v["G1"] = g1

    # G2 과검출 없음: pdshapefault 홀드 스크린의 bodyline·hip_mid scaled < 1.0
    #    (1.0 = 렌더러 유의미 마진 POLE_MARGIN 0.15 몸통 / SCALE_GAP 0.15 — 구조 유도.
    #     epy 실측: pdshapefault r03 마진 0.061 -> 올바른 침묵이었음). 측정 불가 = FAIL.
    g2: dict = {"pass": False}
    ph = results.get("pdshapefault", {}).get("hold")
    if ph is None:
        g2["reason"] = "pdshapefault 홀드 스크린 미실행"
    elif not ph.get("available"):
        g2["reason"] = f"pdshapefault 홀드 판정 불가(측정 불가=FAIL, fail-closed): {ph['reason']}"
    else:
        vals = {}
        missing = []
        for f in ("bodyline", "gap_hip_mid"):
            row = next((r for r in ph["rows"] if r["feature"] == f and r["included"]), None)
            if row is None:
                missing.append(f)
            else:
                vals[f] = row["scaled"]
        if missing:
            g2["reason"] = f"측정 불가(집계 제외, fail-closed): {missing}"
        else:
            g2["values"] = vals
            over = {f: s for f, s in vals.items() if s >= 1.0}
            if over:
                g2["reason"] = f"scaled >= 1.0 과검출: {over}"
            else:
                g2["pass"] = True
    v["G2"] = g2

    # G3 유지: powerspin 스플릿 신호(벌림각 또는 ankle 폴간격)가 전구간 스크린 top 3 잔존.
    g3: dict = {"pass": False}
    pf = results.get("powerspin", {}).get("full")
    if pf is None:
        g3["reason"] = "powerspin 전구간 스크린 미실행"
    else:
        top3 = _top3(pf)
        g3["top3"] = [{"feature": r["feature"], "scaled": r["scaled"], "median": r["median"]}
                      for r in top3]
        hits = [r for r in top3
                if r["feature"] in ("split_angle", "gap_left_ankle", "gap_right_ankle")]
        if hits:
            g3["pass"] = True
            g3["evidence"] = [{"feature": r["feature"], "rank": r["rank"],
                               "median": r["median"], "scaled": r["scaled"]} for r in hits]
        else:
            g3["reason"] = "top3 에 스플릿 신호(split_angle/gap_*_ankle) 없음"
    v["G3"] = g3

    v["overall"] = bool(g1["pass"] and g2["pass"] and g3["pass"])

    print("\n===== r03 블라인드 재발견 verdict (--verdict-r03, 기본 파라미터 1회 판정) =====")
    for g, desc in (("G1", "재발견: elbow 홀드 bodyline/gap_hip_mid top3 AND median>0"),
                    ("G2", "과검출 없음: pdshapefault 홀드 bodyline·gap_hip_mid scaled<1.0"),
                    ("G3", "유지: powerspin 전구간 스플릿 신호 top3 잔존")):
        gg = v[g]
        tail = (f" — 근거 {gg.get('evidence', gg.get('values'))}" if gg["pass"]
                else f" — 사유 {gg.get('reason')}")
        print(f"  [{'PASS' if gg['pass'] else 'FAIL'}] {g} {desc}{tail}")
    print(f"  overall: {'PASS' if v['overall'] else 'FAIL'}")
    return v


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="p35 자율 발견 스크린 v1 (전구간+홀드)")
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR,
                    help="align.json 루트 (기본: 리포 영구화 데이터)")
    ap.add_argument("--motions", default=DEFAULT_MOTIONS, help="콤마 구분 동작 목록")
    ap.add_argument("--full", action="store_true", help="전구간 스크린만")
    ap.add_argument("--hold", action="store_true", help="홀드 스크린만")
    ap.add_argument("--json-out", default=None, help="리포트 JSON 저장 경로")
    ap.add_argument("--pole-frames-dir", default=None,
                    help="폴 재계산용 프레임 루트 ROOT/{motion}/{side}/*.jpg — 미지정 시 캐시만")
    ap.add_argument("--regress-v0", action="store_true", help="v0 인라인 실측 회귀 게이트 (실패 exit 1)")
    ap.add_argument("--verdict-r03", action="store_true", help="r03 블라인드 재발견 기계 판정")
    ap.add_argument("--hold-pct", type=int, default=HOLD_PCT,
                    help=f"홀드 임계 백분위 (기본 {HOLD_PCT}) — 관찰 전용, verdict 는 기본값 강제")
    args = ap.parse_args(argv)

    if args.verdict_r03 and args.hold_pct != HOLD_PCT:
        ap.error("--verdict-r03 은 기본 파라미터 1회 판정 — --hold-pct 변경 금지 (curve-fit 금지)")

    do_full = args.full or not args.hold
    do_hold = args.hold or not args.full
    if args.regress_v0 or args.verdict_r03:
        do_full = do_hold = True  # 게이트/판정은 두 스크린 모두 필요

    motions = [m.strip() for m in args.motions.split(",") if m.strip()]
    data_dir = Path(args.data_dir)
    results: dict = {}
    aligns: dict = {}
    skipped: dict = {}
    pole_info: dict = {}

    for motion in motions:
        path = data_dir / motion / "align.json"
        try:
            align = _load_align(path)
        except (OSError, KeyError, ValueError) as e:
            skipped[motion] = f"적재 실패: {e}"
            print(f"[skip] {motion}: {skipped[motion]}")
            continue
        pole, pole_reason = _resolve_pole_x(motion, align, args.pole_frames_dir)
        if pole_reason:
            print(f"[주의] {motion}: {pole_reason}")
        pole_info[motion] = pole if pole else {"excluded_reason": pole_reason}
        res = _screen_motion(align, pole, do_full, do_hold, args.hold_pct)
        results[motion] = res
        aligns[motion] = align
        _print_motion(motion, res)

    report: dict = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "data_dir": str(data_dir),
            "motions": motions,
            "skipped": skipped,
            "hold_pct": args.hold_pct,
            "angle_space": ANGLE_SPACE,
            "constants": {"CONF_GATE": CONF_GATE, "VALID_MIN": VALID_MIN,
                          "SCALE_ANGLE": SCALE_ANGLE, "SCALE_GAP": SCALE_GAP,
                          "HOLD_SMOOTH_K": HOLD_SMOOTH_K, "HOLD_PCT": HOLD_PCT,
                          "HOLD_MIN_S": HOLD_MIN_S, "HOLD_PAIR_MIN": HOLD_PAIR_MIN,
                          "MIRROR_IMPROVE": MIRROR_IMPROVE},
        },
        "pole_x": pole_info,
        "motions": results,
    }

    exit_code = 0
    if args.regress_v0:
        ok, checks = run_regress_v0(results, aligns)
        report["regress_v0"] = {"pass": ok, "checks": checks}
        if not ok:
            exit_code = 1
    if args.verdict_r03:
        report["verdict"] = run_verdict_r03(results)

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        json.dump(report, open(out, "w"), ensure_ascii=False, indent=1)
        print(f"\n[json] {out}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
