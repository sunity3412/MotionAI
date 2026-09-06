"""M1 기하 — 어깨 각도 문법 4안(A/B/C/D)의 모델-없는 계기 (2026-09-06).

사전 박제: SHOULDER-GRAMMAR-PREREGISTRATION.md (커밋 2906b272, 14:04:32Z).
지표 정의 3개는 그 문서 그대로 쓴다. 기준을 바꾸지 않는다.

  1. beyond_hip        골반 방향 선의 끝점이 꼭짓점→골반 거리의 몇 배 지점인가 (>1.0 = 넘어감)
  2. nearest_joint     선 끝점에서 가장 가까운 저장 관절
  3. leg_intrusion_px  선분 끝 20% 구간에서 무릎·발목 좌표까지의 최단 거리 (px, 작을수록 다리 위)

계산은 전부 **저장 좌표 + fault_zoom.py 의 실제 상수·함수** 로 한다 (값 손으로 베끼기 금지).
패널 px 공간 = 배달된 카드와 같은 360x360 캔버스.

실행:
    \
    FIREBASE_SA_PATH=$PWD/firebase-sa.json AWS_PROFILE=sunity-motion \
    backend/.venv/bin/python .planning/quick/260906-n2j-stage-1-advisory/evidence/shoulder_grammar_m1.py
"""
from __future__ import annotations

import json
import math
import os
import sys

_R = "/Users/kimtaesung/Dev/SunityMotion"
sys.path.insert(0, _R + "/backend/shared/python")

import numpy as np                                          # noqa: E402
from PIL import Image                                       # noqa: E402

from sunity_shared import firestore_admin as fa             # noqa: E402
from sunity_shared.analysis import fault_zoom as fz         # noqa: E402

UID = "NdVZrpbmUbPMNMjASFwUgy8Fj9p1"
DOCS = [
    ("pdshape",   "4e232c4a73ec40a6a8deb07cbf6aa03f"),
    ("climb",     "a559705f06784505bf266afe99cf2822"),
    ("elbow",     "d213622a3e754d0f851a436e8bc9f208"),
    ("powerspin", "5ae210fabec349698e1d35912b8f22e1"),
    ("kipup",     "ea765def661e480292f95c5df57092a1"),
    ("peterpan",  "21b1b7ed3bc84d829d201334e64acc5b"),
]

# 프레임 해상도 — ffprobe 실측 (가정 아님, 2026-09-06).
#   학생 6편 = /Users/kimtaesung/Downloads/정은지 선수 추가 영상/*.mp4  전부 2160x3840
#   기준     = result.referenceVideoUrl (S3 presigned) 를 ffprobe
# crop 로그의 side_px = round(frac x min(h,w)) 와 대조 검증한다(아래 assert).
#
# ★종횡비 감도: 환경변수 ASPECT=16:9 를 주면 모든 프레임의 (w,h) 를 뒤집어(가로) 다시
#   계산한다. 실측이 전부 9:16 이라 가정은 필요 없지만, "종횡비 가정이 결과를 바꾸는가"를
#   되받기 위한 반사실 계산이다 (출력 파일명에 _aspect169 접미).
_SWAP = os.environ.get("ASPECT", "9:16") == "16:9"

USER_WH = (2160, 3840)          # (w, h)
REF_WH = {
    "ref-pdshape": (1080, 1920),
    "ref-climb": (2160, 3840),
    "ref-power-spin": (1080, 1920),
    "ref-kip-up": (1080, 1920),
    "ref-peter-pan": (1080, 1920),
    "ref-elbow-twist-sister": (1080, 1920),
}

if _SWAP:
    USER_WH = (USER_WH[1], USER_WH[0])
    REF_WH = {k: (v[1], v[0]) for k, v in REF_WH.items()}

PANEL_DIR = ("/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
             "ddbd68df-0096-4baa-8c03-5768db49ad77/scratchpad/panels_n2j")

LEG_JOINTS = ("left_knee", "right_knee", "left_ankle", "right_ankle")
OUT = fz._OUT                                        # noqa: SLF001  360
CIRCLE_R = int(OUT * 0.16)                           # _mark 의 원 반지름 (57px)


# ── 순수 기하 헬퍼 ────────────────────────────────────────────────────────────
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _norm(v):
    return math.hypot(v[0], v[1])


def _unit(v):
    n = _norm(v)
    return None if n < 1e-9 else (v[0] / n, v[1] / n)


def _pt_seg_dist(p, a, b):
    """점 p 에서 선분 ab 까지의 최단 거리."""
    ab = _sub(b, a)
    L2 = ab[0] ** 2 + ab[1] ** 2
    if L2 < 1e-12:
        return _norm(_sub(p, a))
    t = ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / L2
    t = max(0.0, min(1.0, t))
    proj = (a[0] + ab[0] * t, a[1] + ab[1] * t)
    return _norm(_sub(p, proj))


def all_joint_xy(report, fi):
    """저장 관절 전부 (finite 좌표만; conf 게이트 없음 — '가장 가까운 저장 관절')."""
    out = {}
    for j in (report.get("joints") or []):
        xy = fz._kp_xy(report, fi, j)                # noqa: SLF001
        if xy is not None:
            out[j] = (xy, fz._kp_conf(report, fi, j))  # noqa: SLF001
    return out


# ── 한 면(패널) 계산 ─────────────────────────────────────────────────────────
def measure_face(spec, frac, wh, report, fi, variant):
    """spec=(꼭짓점, 사지 방향점, 몸통 방향점) 정규화 → 지표 3개 (패널 px)."""
    w, h = wh
    vertex, limb, torso = spec
    side_px = fz.crop_side_px(frac, h, w)
    box = fz._crop_box_centered(h, w, vertex[0], vertex[1], side_px)  # noqa: SLF001

    def P(xy):
        return fz._to_crop_px_unclamped(xy, box[0], box[1], box[2], w, h)  # noqa: SLF001

    v_px, limb_px, torso_px = P(vertex), P(limb), P(torso)
    d_hip = _norm(_sub(torso_px, v_px))
    d_elbow = _norm(_sub(limb_px, v_px))
    ut = _unit(_sub(torso_px, v_px))
    ul = _unit(_sub(limb_px, v_px))

    joints = all_joint_xy(report, fi)
    jpx = {j: P(xy) for j, (xy, _c) in joints.items()}

    res = {
        "variant": variant,
        "crop_frac": round(frac, 4),
        "crop_side_px": side_px,
        "vertex_norm": [round(vertex[0], 5), round(vertex[1], 5)],
        "vertex_panel_px": [round(v_px[0], 1), round(v_px[1], 1)],
        "dist_vertex_to_hip_px": round(d_hip, 2),
        "dist_vertex_to_elbow_px": round(d_elbow, 2),
    }

    if variant == "D":
        # 선 없음 → beyond_hip / nearest_joint 는 null.
        # leg_intrusion_px 대체 정의: 부위 원(중심=꼭짓점=패널 정중앙, r=_mark 의
        # int(360*0.16)=57px) 경계까지의 여유 = d(중심, 가장 가까운 무릎·발목) - r.
        # <=0 이면 그 다리 관절이 원 **안**에 들어온 것. 부호 방향은 A/B/C 와 같다
        # (작을수록 나쁨).
        best, bestj = None, None
        for j in LEG_JOINTS:
            if j not in jpx:
                continue
            d = _norm(_sub(jpx[j], v_px)) - CIRCLE_R
            if best is None or d < best:
                best, bestj = d, j
        res.update({
            "beyond_hip": None, "nearest_joint": None,
            "leg_intrusion_px": None if best is None else round(best, 2),
            "leg_intrusion_joint": bestj,
            "leg_intrusion_def": "d(circle_center, nearest knee/ankle) - r(57px)",
        })
        return res

    if ut is None or ul is None:
        res.update({"beyond_hip": None, "nearest_joint": None,
                    "leg_intrusion_px": None, "degenerate": True})
        return res

    if variant == "B":
        L_torso = min(fz._ANGLE_TORSO_LEN_FRAC * OUT, d_hip)     # noqa: SLF001
        L_limb = min(fz._ANGLE_LIMB_LEN_FRAC * OUT, d_elbow)     # noqa: SLF001
    else:
        L_torso = fz._ANGLE_TORSO_LEN_FRAC * OUT                 # noqa: SLF001
        L_limb = fz._ANGLE_LIMB_LEN_FRAC * OUT                   # noqa: SLF001

    torso_end = (v_px[0] + ut[0] * L_torso, v_px[1] + ut[1] * L_torso)
    limb_end = (v_px[0] + ul[0] * L_limb, v_px[1] + ul[1] * L_limb)

    # 1. beyond_hip — 골반 방향 선 끝점 / (꼭짓점→골반)
    beyond = L_torso / d_hip if d_hip > 1e-9 else None

    # 2. nearest_joint — 골반 방향 선 끝점에서 가장 가까운 저장 관절
    nj, ndist = None, None
    for j, p in jpx.items():
        d = _norm(_sub(p, torso_end))
        if ndist is None or d < ndist:
            nj, ndist = j, d
    # (보조) 팔 선 끝점의 최근접 관절 — 지표 아님, 투명성용
    nj2, ndist2 = None, None
    for j, p in jpx.items():
        d = _norm(_sub(p, limb_end))
        if ndist2 is None or d < ndist2:
            nj2, ndist2 = j, d

    # 3. leg_intrusion_px — 골반 방향 선분의 **끝 20%** 구간에서 무릎·발목까지 최단거리
    seg_a = (v_px[0] + ut[0] * L_torso * 0.8, v_px[1] + ut[1] * L_torso * 0.8)
    best, bestj = None, None
    for j in LEG_JOINTS:
        if j not in jpx:
            continue
        d = _pt_seg_dist(jpx[j], seg_a, torso_end)
        if best is None or d < best:
            best, bestj = d, j
    # (보조) 팔 선 끝 20%
    bestL, bestLj = None, None
    segL_a = (v_px[0] + ul[0] * L_limb * 0.8, v_px[1] + ul[1] * L_limb * 0.8)
    for j in LEG_JOINTS:
        if j not in jpx:
            continue
        d = _pt_seg_dist(jpx[j], segL_a, limb_end)
        if bestL is None or d < bestL:
            bestL, bestLj = d, j

    res.update({
        "torso_line_len_px": round(L_torso, 2),
        "limb_line_len_px": round(L_limb, 2),
        "torso_end_px": [round(torso_end[0], 1), round(torso_end[1], 1)],
        "beyond_hip": None if beyond is None else round(beyond, 3),
        "nearest_joint": nj,
        "nearest_joint_dist_px": None if ndist is None else round(ndist, 2),
        "leg_intrusion_px": None if best is None else round(best, 2),
        "leg_intrusion_joint": bestj,
        # 보조(지표 아님)
        "aux_limb_end_nearest_joint": nj2,
        "aux_limb_end_nearest_dist_px": None if ndist2 is None else round(ndist2, 2),
        "aux_limb_leg_intrusion_px": None if bestL is None else round(bestL, 2),
        "aux_limb_leg_intrusion_joint": bestLj,
        "torso_dir_deg": round(math.degrees(math.atan2(ut[1], ut[0])), 2),
        "limb_dir_deg": round(math.degrees(math.atan2(ul[1], ul[0])), 2),
    })
    return res


# ── 배달된 패널에서 실제 그려진 선 방향 측정 (자가검증, 지표 아님) ──────────────
def panel_line_dirs(path):
    """브랜드색(255,75,51) 코어 픽셀의 중심 기준 방향 히스토그램 최빈 2개."""
    if not os.path.exists(path):
        return None
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
    br = np.array(fz._BRAND, dtype=np.int16)          # noqa: SLF001
    d = np.abs(im - br).sum(axis=2)
    ys, xs = np.where(d < 60)
    if len(xs) < 50:
        return None
    cx = cy = OUT / 2.0
    ang = np.degrees(np.arctan2(ys - cy, xs - cx))
    r = np.hypot(xs - cx, ys - cy)
    keep = (r > 25) & (r < 95)
    if keep.sum() < 30:
        return None
    a = ang[keep]
    hist, edges = np.histogram(a, bins=72, range=(-180, 180))
    peaks = []
    order = np.argsort(hist)[::-1]
    for i in order:
        c = (edges[i] + edges[i + 1]) / 2
        if hist[i] < 5:
            break
        if all(abs(((c - p + 180) % 360) - 180) > 25 for p in peaks):
            peaks.append(round(float(c), 1))
        if len(peaks) == 2:
            break
    return peaks


def main():
    crop_log = open(_R + "/.planning/quick/260906-n2j-stage-1-advisory/evidence/"
                    "crop_logs_n2j.txt", encoding="utf-8").read().splitlines()

    rows, faces_out, unmeasurable, notes = [], [], [], []
    ref_cache = {}

    for motion, aid in DOCS:
        doc = fa.get_analysis(UID, aid)
        if doc is None:
            unmeasurable.append(f"{motion}: 문서 없음")
            continue
        result = doc["result"]
        rid = doc.get("referenceMotionId")
        u_rep = result.get("keypointReport") or {}
        if rid not in ref_cache:
            ref_cache[rid] = ((fa.get_reference_motion(rid) or {})
                              .get("referenceKeypointReport") or {})
        r_rep = ref_cache[rid]
        if not r_rep:
            unmeasurable.append(f"{motion}: referenceKeypointReport 비어 있음 (rid={rid})")
            continue

        for ci, c in enumerate(result.get("faultZoomComparisons") or []):
            crit = c.get("criterion")
            joint = c.get("joint") or ""
            if not (joint.endswith("_shoulder") or (crit or "").endswith("_shoulder")):
                continue
            card_id = f"{motion}#{ci}"
            u_fi = int(c.get("userFrameIdx") or 0)
            r_fi = int(c.get("refFrameIdx") or 0)
            u_wh = USER_WH
            r_wh = REF_WH[rid]

            if crit is None:
                # 각도 문법 미적용 카드 (criterion 없음 → build_angle_bake_spec None,
                # 라이브 로그도 angle_bake=omitted:no_criterion). 원 마커만 그린다 —
                # 네 안이 전부 같은 그림이라 문법 비교가 성립하지 않는다.
                for side in ("user", "ref"):
                    for v in ("A", "B", "C", "D"):
                        rows.append({
                            "card": card_id, "motion": motion, "side": side,
                            "variant": v, "beyond_hip": None,
                            "nearest_joint": None, "leg_intrusion_px": None,
                        })
                    unmeasurable.append(
                        f"{card_id} {side} (joint={joint}, tier={c.get('tier')}): "
                        "criterion 없는 카드 — 각도 문법 미적용(원 마커만), "
                        "라이브 로그 angle_bake=omitted:no_criterion. 4안 전부 동일 그림."
                    )
                faces_out.append({"card": card_id, "criterion": None, "joint": joint,
                                  "tier": c.get("tier"), "skipped": "no_criterion"})
                continue

            members = (crit.split("__")[-1],)
            resolvers = {
                "user": fz._gated_kp,                                  # noqa: SLF001
                "ref": fz.make_reference_anchor_resolver(rid, crit),
            }
            reps = {"user": u_rep, "ref": r_rep}
            fis = {"user": u_fi, "ref": r_fi}
            whs = {"user": u_wh, "ref": r_wh}

            # ── A 스펙(현행 문법: 겨드랑이 꼭짓점) ─────────────────────────────
            specA, specC, bad = {}, {}, {}
            for side in ("user", "ref"):
                rep, fi, get = reps[side], fis[side], resolvers[side]
                sA = fz.build_angle_bake_spec(crit, members, rep, fi, get)
                specA[side] = sA
                if sA is None:
                    # 어느 관절이 막았는지 사유 기록
                    jk = members[0]
                    sd = jk.split("_", 1)[0]
                    miss = []
                    for n in (jk, f"{sd}_elbow", f"{sd}_hip"):
                        xy = fz._kp_xy(rep, fi, n)          # noqa: SLF001
                        cf = fz._kp_conf(rep, fi, n)        # noqa: SLF001
                        if get(rep, fi, n) is None:
                            miss.append(f"{n}(xy={'있음' if xy else '없음'},conf="
                                        f"{'na' if cf is None else round(cf, 3)})")
                    bad[side] = "게이트 미달/결측: " + ", ".join(miss)
                    specC[side] = None
                    continue
                sh = get(rep, fi, members[0])
                specC[side] = None if sh is None else (sh, sA[1], sA[2])

            if specA["user"] is None or specA["ref"] is None:
                for side in ("user", "ref"):
                    for v in ("A", "B", "C", "D"):
                        rows.append({"card": card_id, "motion": motion, "side": side,
                                 "variant": v, "beyond_hip": None,
                                 "nearest_joint": None, "leg_intrusion_px": None})
                    _why = bad.get(
                        side, "반대측 스펙 미성립 — both-or-neither 로 각도 미표시")
                    unmeasurable.append(f"{card_id} {side}: {_why}")
                faces_out.append({"card": card_id, "criterion": crit,
                                  "skipped": "spec_none", "reason": bad})
                continue

            fracAB = fz.criterion_crop_frac((
                (specA["user"], (u_wh[1], u_wh[0])),
                (specA["ref"], (r_wh[1], r_wh[0])),
            ))
            if specC["user"] is not None and specC["ref"] is not None:
                fracC = fz.criterion_crop_frac((
                    (specC["user"], (u_wh[1], u_wh[0])),
                    (specC["ref"], (r_wh[1], r_wh[0])),
                ))
            else:
                fracC = None

            # crop 로그 대조 — 재현 검증 (실측 frac 과 라이브 frac 이 같아야 한다)
            logged = None
            for ln in crop_log:
                if (f"analysis_id={aid} " in ln and f"criterion={crit} " in ln
                        and f"user_frame={u_fi // 2} " in ln):
                    logged = ln
            log_frac = None
            if logged and "shared_frac=" in logged:
                t = logged.split("shared_frac=")[-1].strip()
                if t != "none":
                    log_frac = float(t)

            card_rec = {
                "card": card_id, "criterion": crit, "joint": joint,
                "tier": c.get("tier"), "userFrameIdx": u_fi, "refFrameIdx": r_fi,
                "userMarked": c.get("userMarked"), "refMarked": c.get("refMarked"),
                "crop_frac_recomputed_A": round(fracAB, 4),
                "crop_frac_live_log": log_frac,
                "crop_frac_match": (log_frac is not None
                                    and abs(log_frac - fracAB) < 1e-3),
                "crop_frac_recomputed_C": None if fracC is None else round(fracC, 4),
                "sides": {},
            }

            for side in ("user", "ref"):
                rep, fi, wh = reps[side], fis[side], whs[side]
                per_variant = {}
                for v in ("A", "B", "C", "D"):
                    if v == "C":
                        if specC[side] is None or fracC is None:
                            per_variant[v] = {"variant": "C", "beyond_hip": None,
                                              "nearest_joint": None,
                                              "leg_intrusion_px": None,
                                              "note": "어깨 관절 게이트 미달"}
                            rows.append({"card": card_id, "motion": motion, "side": side,
                                         "variant": v, "beyond_hip": None,
                                         "nearest_joint": None,
                                         "leg_intrusion_px": None})
                            continue
                        m = measure_face(specC[side], fracC, wh, rep, fi, "C")
                    else:
                        m = measure_face(specA[side], fracAB, wh, rep, fi, v)
                    per_variant[v] = m
                    rows.append({
                        "card": card_id, "motion": motion, "side": side,
                        "variant": v,
                        "beyond_hip": m.get("beyond_hip"),
                        "nearest_joint": m.get("nearest_joint"),
                        "leg_intrusion_px": m.get("leg_intrusion_px"),
                    })
                # 배달 패널 자가검증 (A 방향 vs 실제 그려진 선)
                pn = f"{aid[:8]}_{ci:02d}_{crit}_{side}.jpg"
                dirs = panel_line_dirs(os.path.join(PANEL_DIR, pn))
                per_variant["_panel_check"] = {
                    "panel": pn, "drawn_dirs_deg": dirs,
                    "computed_A_dirs_deg": [per_variant["A"].get("limb_dir_deg"),
                                            per_variant["A"].get("torso_dir_deg")],
                }
                card_rec["sides"][side] = per_variant

            faces_out.append(card_rec)

    out = {
        "generated": "2026-09-06",
        "aspect": "16:9(counterfactual)" if _SWAP else "9:16(ffprobe 실측)",
        "preregistration": "SHOULDER-GRAMMAR-PREREGISTRATION.md (2906b272)",
        "uid": UID,
        "user_frame_wh": list(USER_WH),
        "ref_frame_wh": {k: list(v) for k, v in REF_WH.items()},
        "circle_r_px": CIRCLE_R,
        "cards": faces_out,
        "rows": rows,
        "unmeasurable": unmeasurable,
    }
    p = (_R + "/.planning/quick/260906-n2j-stage-1-advisory/evidence/"
         + ("shoulder_grammar_m1_aspect169.json" if _SWAP
            else "shoulder_grammar_m1.json"))
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"cards": len(faces_out), "rows": len(rows),
                      "unmeasurable": len(unmeasurable)}, ensure_ascii=False))
    print("wrote", p)


if __name__ == "__main__":
    main()
