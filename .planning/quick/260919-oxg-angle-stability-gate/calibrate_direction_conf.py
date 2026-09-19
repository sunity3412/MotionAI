"""방향점 신뢰도 대 시간축 안정성 — 게이트가 실제로 쓸 공간에서 다시 잰다.

왜 다시 재나 (quick-260919-oxg Task 1).
  `conf_vs_accuracy.py` 의 편차는 doc 최상위 `angles`(= joints3d 공간, 9fps 축)에서
  나왔다. 반면 게이트가 보게 될 각도는 `fz.build_angle_bake_spec` 이 돌려주는
  **정규화 좌표 3점의 사이각**이다. 두 공간의 도(度) 값은 같은 수가 아니다.
  conf_vs_accuracy 는 "0.5 가 아무것도 안 가른다"는 **모양**을 증명했고,
  임계 **숫자**는 코드가 실제로 쓸 공간에서 읽어야 한다.

계기 = 게이트와 같은 공간·같은 함수.
  · 꼭짓점 = `fz.criterion_vertex_xy(..., resolver=fz._gated_kp)` — 재구현 금지,
    어깨 계열 겨드랑이 내분점(`fz._ARMPIT_T`)까지 프로덕션 정의 그대로.
    꼭짓점은 **엄격 유지**(판정 1) 이므로 계기도 엄격하게 잡는다.
  · 방향 2점 = `fz.ANGLE_BAKE_MAP` 선언 관절. 중앙 프레임은 **게이트 없이**
    조회해 전 신뢰도 구간의 표를 채우고(서술용), 버킷 x축은 그 2점 conf 의 **최소값**
    이다 — 우리가 여는 값이 바로 그것이기 때문(판정 1).
  · 이웃 프레임(기준선)은 **프로덕션 규칙 그대로** 게이트한다 — 꼭짓점 0.5,
    방향점 `_DIR_CONF_MIN` 0.35. 그래야 0.50-0.60 행에서 읽는 p75 가
    `build_stable_angle_bake_spec` 이 런타임에 계산할 량과 같은 량이 된다.
  · 창 폭 = `_HALF_WINDOW_SEC`(2/9초) × report fps → 프레임. 실측 2 표가 쓴
    9fps ±2프레임과 같은 **시간** 폭. fps 라벨 오차 ~10% 는 창 폭 10% 오차이고
    지표가 중앙값이라 무해하다.

라이브 읽기는 Spark 무료 플랜 5만/일 하드 캡 안이다 — users 30 × analyses 25,
doc 25건에서 끊는다. 전수 스캔 금지.

산출: 260919-oxg-CALIBRATION.md (학생 표 / 기준 표 / 채택 임계 + 읽은 칸).
코드 변경 0 — 이 파일은 계기다.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath("backend/shared/python"))
os.environ.setdefault("FIREBASE_SA_PATH", os.path.abspath("firebase-sa.json"))

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

# 게이트가 쓸 값과 같은 층 (Task 2 가 fault_zoom 에 박을 상수의 사전 선언).
_DIR_CONF_MIN = 0.35
_HALF_WINDOW_SEC = 2.0 / 9.0
_MIN_NEIGHBORS = 2

BUCKETS = (
    "<0.30", "0.30-0.35", "0.35-0.40", "0.40-0.45",
    "0.45-0.50", "0.50-0.60", "0.60-0.70", ">=0.70",
)
_EDGES = (
    (0.0, 0.30, "<0.30"), (0.30, 0.35, "0.30-0.35"),
    (0.35, 0.40, "0.35-0.40"), (0.40, 0.45, "0.40-0.45"),
    (0.45, 0.50, "0.45-0.50"), (0.50, 0.60, "0.50-0.60"),
    (0.60, 0.70, "0.60-0.70"), (0.70, 9.0, ">=0.70"),
)

# 운영 keypointReport 는 wrist 를 hand 로 부른다 (card_gates.NAME_ALT 와 같은 규칙,
# 양방향). ANGLE_BAKE_MAP["elbow"] 가 "hand" 를 선언하므로 역방향도 필요하다.
NAME_ALT = {
    "left_wrist": "left_hand", "right_wrist": "right_hand",
    "left_hand": "left_wrist", "right_hand": "right_wrist",
}


def bucket_of(c: float) -> str:
    for lo, hi, k in _EDGES:
        if lo <= c < hi:
            return k
    return ">=0.70"


def resolve(report: dict, name: str) -> str | None:
    """report 이름공간으로 관절명 해석 (card_gates._resolve 와 같은 규칙)."""
    joints = report.get("joints") or []
    if name in joints:
        return name
    alt = NAME_ALT.get(name)
    if alt and alt in joints:
        return alt
    return None


def _raw_xy(report: dict, idx: int, name: str):
    """conf 게이트 없이 좌표만 (중앙 프레임 서술용). conf 부재는 여전히 불허."""
    rn = resolve(report, name)
    if rn is None:
        return None
    xy = fz._kp_xy(report, idx, rn)  # noqa: SLF001
    if xy is None:
        return None
    c = fz._kp_conf(report, idx, rn)  # noqa: SLF001
    if c is None or not np.isfinite(c):
        return None
    return xy


def _dir_conf(report: dict, idx: int, name: str):
    rn = resolve(report, name)
    if rn is None:
        return None
    c = fz._kp_conf(report, idx, rn)  # noqa: SLF001
    return float(c) if c is not None and np.isfinite(c) else None


def _gated_dir_xy(report: dict, idx: int, name: str, conf_min: float):
    rn = resolve(report, name)
    if rn is None:
        return None
    xy = fz._kp_xy(report, idx, rn)  # noqa: SLF001
    if xy is None:
        return None
    c = fz._kp_conf(report, idx, rn)  # noqa: SLF001
    if c is None or c < conf_min:
        return None
    return xy


def inner_deg_norm(vertex, limb, torso) -> float | None:
    """정규화 3점 사이각 (도). 퇴화(길이 0 벡터) = None — 게이트와 같은 정의."""
    def _unit(p):
        dx = float(p[0]) - float(vertex[0])
        dy = float(p[1]) - float(vertex[1])
        n = math.hypot(dx, dy)
        if n <= 0.0 or not np.isfinite(n):
            return None
        return dx / n, dy / n

    ul, ut = _unit(limb), _unit(torso)
    if ul is None or ut is None:
        return None
    d = max(-1.0, min(1.0, ul[0] * ut[0] + ul[1] * ut[1]))
    return math.degrees(math.acos(d))


def angle_at(report: dict, idx: int, joint: str, decl, side: str,
             *, gate_directions: bool) -> float | None:
    """(꼭짓점 엄격 + 방향 2점) 사이각. gate_directions → 프로덕션 하한 적용."""
    crit = fz.ANGLE_VS_REFERENCE_PREFIX + joint
    vertex = fz.criterion_vertex_xy(
        crit, (joint,), report, idx, None, fz._gated_kp  # noqa: SLF001
    )
    if vertex is None:
        return None
    if gate_directions:
        limb = _gated_dir_xy(report, idx, f"{side}_{decl[0]}", _DIR_CONF_MIN)
        torso = _gated_dir_xy(report, idx, f"{side}_{decl[1]}", _DIR_CONF_MIN)
    else:
        limb = _raw_xy(report, idx, f"{side}_{decl[0]}")
        torso = _raw_xy(report, idx, f"{side}_{decl[1]}")
    if limb is None or torso is None:
        return None
    return inner_deg_norm(vertex, limb, torso)


def collect(report: dict, buckets: dict[str, list[float]], stats: dict) -> None:
    """report 하나에서 (프레임 × 각도 대상 관절) 표본을 버킷에 쌓는다."""
    joints = report.get("joints") or []
    frames = int(report.get("frames") or 0)
    try:
        fps = float(report.get("fps") or 0.0)
    except (TypeError, ValueError):
        fps = 0.0
    if frames <= 0 or fps <= 0:
        stats["skipped_reports"] += 1
        return
    w = max(1, int(round(_HALF_WINDOW_SEC * fps)))
    stats["windows"].append(w)
    stats["fps"].append(fps)

    targets = []
    for jn in joints:
        if "_" not in jn:
            continue
        side, suffix = jn.split("_", 1)
        decl = fz.ANGLE_BAKE_MAP.get(suffix)
        if decl is None:
            continue
        targets.append((jn, side, decl))
    if not targets:
        stats["skipped_reports"] += 1
        return

    for jn, side, decl in targets:
        for t in range(frames):
            cl = _dir_conf(report, t, f"{side}_{decl[0]}")
            ct = _dir_conf(report, t, f"{side}_{decl[1]}")
            if cl is None or ct is None:
                continue
            cmin = min(cl, ct)
            cur = angle_at(report, t, jn, decl, side, gate_directions=False)
            if cur is None:
                continue
            stats["measurable_center"] += 1
            neigh = []
            for k in range(max(0, t - w), min(frames, t + w + 1)):
                if k == t:
                    continue
                a = angle_at(report, k, jn, decl, side, gate_directions=True)
                if a is not None:
                    neigh.append(a)
            if len(neigh) < _MIN_NEIGHBORS:
                stats["no_neighbors"] += 1
                continue
            buckets[bucket_of(cmin)].append(abs(cur - float(np.median(neigh))))


def table(buckets: dict[str, list[float]]) -> list[tuple]:
    rows = []
    for k in BUCKETS:
        v = np.asarray(buckets[k], dtype=float)
        if v.size < 30:
            rows.append((k, int(v.size), None, None, None, None))
            continue
        rows.append((
            k, int(v.size), float(np.median(v)),
            float(np.percentile(v, 75)), float(np.percentile(v, 90)),
            float(100.0 * (v > 20).mean()),
        ))
    return rows


def render(title: str, rows: list[tuple]) -> str:
    out = [f"### {title}", "",
           "| 방향 2점 conf 최소 | 표본 | 중앙값 | p75 | p90 | >20도 |",
           "|---|---:|---:|---:|---:|---:|"]
    for k, n, med, p75, p90, big in rows:
        if med is None:
            out.append(f"| {k} | {n} | (표본 부족) | | | |")
            continue
        mark = ""
        if k == "0.45-0.50":
            mark = " <- 문턱 바로 아래"
        if k == "0.50-0.60":
            mark = " <- 문턱 바로 위 (임계를 읽는 행)"
        out.append(
            f"| {k}{mark} | {n} | {med:.2f} | {p75:.2f} | {p90:.2f} | {big:.1f}% |"
        )
    out.append("")
    return "\n".join(out)


def row_of(rows: list[tuple], key: str) -> tuple:
    for r in rows:
        if r[0] == key:
            return r
    raise KeyError(key)


def new_stats() -> dict:
    return {"measurable_center": 0, "no_neighbors": 0, "skipped_reports": 0,
            "windows": [], "fps": []}


def main() -> None:
    db = fa._db()  # noqa: SLF001

    user_b = {k: [] for k in BUCKETS}
    user_s = new_stats()
    docs = 0
    for usnap in db.collection("users").limit(30).stream():
        for asnap in usnap.reference.collection("analyses").limit(25).stream():
            d = asnap.to_dict() or {}
            kr = (d.get("result") or {}).get("keypointReport") or {}
            if not kr.get("confidence") or not kr.get("data"):
                continue
            docs += 1
            collect(kr, user_b, user_s)
            if docs >= 25:
                break
        if docs >= 25:
            break

    ref_b = {k: [] for k in BUCKETS}
    ref_s = new_stats()
    ref_docs = 0
    for m in fa.list_reference_motions():
        kr = m.get("keypointReport") or {}
        if not kr.get("confidence") or not kr.get("data"):
            continue
        ref_docs += 1
        collect(kr, ref_b, ref_s)

    urows, rrows = table(user_b), table(ref_b)
    ur = row_of(urows, "0.50-0.60")
    rr = row_of(rrows, "0.50-0.60")

    lines = [
        "# 260919-oxg CALIBRATION — 방향점 신뢰도 대 시간축 안정성",
        "",
        "계기 = `calibrate_direction_conf.py`. 각도는 **정규화 좌표 3점 사이각**",
        "(`fz.criterion_vertex_xy` 꼭짓점 + `ANGLE_BAKE_MAP` 방향 2점) — 게이트가",
        "런타임에 계산할 량과 같은 공간·같은 함수다. 지표 =",
        "`|사이각(t) − 시간축 이웃 중앙값|` (도).",
        "",
        "- 꼭짓점: 엄격(`fz._gated_kp`, conf >= 0.5) — 판정 1(꼭짓점 비완화) 반영.",
        "- 버킷 x축: **방향 2점 conf 의 최소값** (중앙 프레임은 게이트 없이 조회).",
        f"- 이웃(기준선): 프로덕션 규칙 그대로 게이트 (꼭짓점 0.5 / 방향 {_DIR_CONF_MIN}).",
        f"- 창: ±{_HALF_WINDOW_SEC:.3f}초 × report fps → 프레임, 최소 이웃 {_MIN_NEIGHBORS}점.",
        "",
        f"학생 doc {docs}건 (users 30 × analyses 25 상한, Spark 5만/일 캡 안).",
        f"기준 doc {ref_docs}건.",
        "",
        render("학생 표", urows),
        render("기준(정은지) 표", rrows),
        "## 측정 불가 몫",
        "",
        "| 모집단 | 중앙 프레임 성립 | 이웃 부족으로 탈락 | 비율 | report 스킵 | 창 폭(프레임) | fps |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for name, s in (("학생", user_s), ("기준", ref_s)):
        tot = s["measurable_center"]
        pct = (100.0 * s["no_neighbors"] / tot) if tot else 0.0
        ws = sorted(set(s["windows"]))
        fs = sorted(set(round(f, 2) for f in s["fps"]))
        lines.append(
            f"| {name} | {tot} | {s['no_neighbors']} | {pct:.1f}% | "
            f"{s['skipped_reports']} | {ws} | {fs} |"
        )
    lines.append("")

    stop = []
    u45 = row_of(urows, "0.45-0.50")
    if ur[3] is None:
        stop.append("학생 표 0.50-0.60 행 표본 부족 — 임계를 읽을 칸이 없다.")
    elif u45[2] is not None and u45[2] > ur[3]:
        stop.append(
            f"학생 0.45-0.50 중앙값({u45[2]:.2f}) > 0.50-0.60 p75({ur[3]:.2f}) — "
            "실측 2 의 결론이 코드 공간에서 성립하지 않는다. 중단 조건."
        )

    lines += ["## 채택 임계", ""]
    if stop:
        lines += ["**중단 조건 발동 — 임계 채택 없음.**", ""]
        lines += [f"- {s}" for s in stop] + [""]
        print("\n".join(lines))
        out = ".planning/quick/260919-oxg-angle-stability-gate/260919-oxg-CALIBRATION.md"
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"\n!! 중단 조건: {stop}")
        return

    ref_short = rr[3] is None
    if ref_short:
        picked = ur[3]
        basis = (
            "기준 표 0.50-0.60 행이 표본 부족(30 미만)이라 `min()` 이 성립하지 않는다. "
            "PLAN 의 **대체 규칙** 발동 — 임계는 학생 표에서 읽고, 완화 경로는 "
            "**학생 측에만** 배선한다(기준 측 해상기는 `_gated_kp` 그대로)."
        )
        read_at = "학생 표 · 행 `0.50-0.60` · 열 `p75`"
    else:
        picked = min(ur[3], rr[3])
        which = "학생" if ur[3] <= rr[3] else "기준"
        basis = (
            f"`min(학생 p75 {ur[3]:.2f}, 기준 p75 {rr[3]:.2f})` = {picked:.2f} "
            f"({which} 쪽이 엄하다). 두 모집단 중 엄한 쪽에 맞추면 상수 1개로 양측을 "
            "덮으면서 어느 쪽에서도 현행보다 느슨해지지 않는다(판정 2 해소)."
        )
        read_at = f"{which} 표 · 행 `0.50-0.60` · 열 `p75`"
    adopted = math.floor(picked * 10.0) / 10.0

    lines += [
        f"```",
        f"_ANGLE_STABILITY_MAX_DEV_DEG = {adopted:.1f}",
        f"```",
        "",
        f"- 읽은 칸: **{read_at}** = `{picked:.2f}` → 소수 첫째 자리 **내림** = `{adopted:.1f}`.",
        f"- {basis}",
        "- 왜 0.50-0.60 행인가: **지금 실제로 통과하고 있는** 밴드다. 새로 여는 점은",
        "  \"이미 나가고 있는 것과 같은 수준으로 안정하다\"를 증명해야 한다.",
        "- 왜 p75 인가: 중앙값은 지금 나가는 것의 절반을 거절해 여는 목적을 스스로",
        "  없애고, p90 은 `>20도` 튐 꼬리에 붙어 튐을 통과시킨다. p75 = 지금 나가는",
        "  것의 4분의 3이 보이는 안정성 = 현행과 모순되지 않는 가장 좁은 칸.",
        "",
        "## 이 표가 증명하지 못하는 것",
        "",
        "- 정규화 공간 도(度)는 화면에 그려지는 각(이미지 평면 px 각)과 같은 수가",
        "  아니다. 라이브 doc 에 영상 W·H 가 없어 계기·게이트를 둘 다 정규화 공간으로",
        "  통일했다 — 자가 일치하지만 \"화면에서 N도\"로 읽으면 안 된다.",
        "- 시간축 안정성은 좌표가 **튀는** 것을 잡지 **일관되게 틀린** 것은 못 잡는다.",
        "- 라이브 표본 값이지 모집단 값이 아니다.",
        "",
    ]
    text = "\n".join(lines)
    out = ".planning/quick/260919-oxg-angle-stability-gate/260919-oxg-CALIBRATION.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    print(f"\n채택 임계 _ANGLE_STABILITY_MAX_DEV_DEG = {adopted:.1f}   -> {out}")


if __name__ == "__main__":
    main()
