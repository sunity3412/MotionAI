"""M2 기계 눈 — 어깨 각도 문법 4안(A/B/C/D)을 **실제 프레임 위에 렌더**해 눈에 묻는다.

사전 박제: SHOULDER-GRAMMAR-PREREGISTRATION.md (커밋 2906b272, 14:04:32Z) "M2 기계 눈" 절.
  · 렌더된 패널을 그대로 주고 **표시가 가리키는 부위**를 묻는다.
  · 질문·허용 답안은 기존 `card_gates` 어휘 그대로 — 새 어휘를 만들지 않는다.
  · M2 는 보조. M1 과 어긋나면 판정을 내리지 않고 어긋났다고 적는다.

프로덕션 코드 수정 0. `fault_zoom` 의 상수·함수를 그대로 import 해 쓴다.
B 만 길이 클램프를 스크립트 안에서 다시 그린다(_draw_joint_angle 을 복제하지 않고
같은 상수·같은 호 공식 `fz._minor_arc_span_deg` 를 호출).

측정 대상 = M1 이 다룬 **같은 면** — criterion 어깨 카드 4장 × 2면 = 8면.
(criterion 없는 어깨 카드 2장(pdshape#4·kipup#0)은 M1 에서 "각도 문법 미적용"으로
 판정불가였고, 그건 M2 에서도 같다 — 4안이 전부 같은 그림이라 비교가 성립 안 한다.)

프레임 = 라이브가 쓴 그 프레임. crop 로그(`crop_logs_n2j.txt`)의
`user_frame`(=u_idx_unit) / `ref_video_idx`(=r_display_idx) 를 그대로 쓰고,
운영과 같은 `compare_render._native_frame(video, idx/실효fps)` 로 원본 해상도 1장을 뽑는다.

크롭 폭 = 현행 그대로 (belle 판정 대기 항목 — 변경 금지).
  · A/B/D = 라이브 shared_frac 을 `criterion_crop_frac` 로 재산출(로그와 대조).
  · C 는 꼭짓점이 바뀌므로 `criterion_crop_frac` 이 다시 계산되지만, 4카드 전부
    밴드 클램프에 걸려 frac 이 A 와 **같은 값**이 나온다(M1 실측) — 폭 불변.

판정 규칙 (임무 지시 그대로, 눈을 부르기 전에 고정):
  허용집합 = `card_photo_audit.expected_parts(criterion, joint)`  (어깨 = shoulder/
  armpit/chest/back_waist). A 의 최빈 토큰이 허용집합 안이면 A 가 좋은 것.
    A in / V in  → same      A in / V out → worse
    A out/ V in  → better    A out/ V out → same
    어느 한쪽이 못 읽음(unclear/error) → null (판정 불가)

실행:
    GEMINI_API_KEY=$(aws ssm get-parameter --name /sunity/motion/gemini-api-key \
      --with-decryption --profile sunity-motion --region ap-northeast-2 \
      --query Parameter.Value --output text) \
    FIREBASE_SA_PATH=$PWD/firebase-sa.json AWS_PROFILE=sunity-motion \
    backend/.venv/bin/python .planning/quick/260906-n2j-stage-1-advisory/evidence/shoulder_grammar_m2.py

    RENDER_ONLY=1 을 주면 렌더 + 배달 패널 대조까지만 하고 눈을 부르지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import tempfile
from pathlib import Path

_R = "/Users/kimtaesung/Dev/SunityMotion"
sys.path.insert(0, _R + "/backend/shared/python")

import numpy as np                                          # noqa: E402
from PIL import Image, ImageDraw                            # noqa: E402

from sunity_shared import firestore_admin as fa             # noqa: E402
from sunity_shared.analysis import card_gates as cg         # noqa: E402
from sunity_shared.analysis import card_photo_audit as cpa  # noqa: E402
from sunity_shared.analysis import compare_render as cr     # noqa: E402
from sunity_shared.analysis import fault_zoom as fz         # noqa: E402
from sunity_shared.analysis.frame_extractor import (        # noqa: E402
    FfmpegFrameExtractor,
)

UID = "NdVZrpbmUbPMNMjASFwUgy8Fj9p1"
OUTDIR = "/Users/Shared/sunity-shoulder-trial"
REFDIR = "/Users/Shared/sunity-ref-videos"
VIDBASE = "/Users/kimtaesung/Downloads/정은지 선수 추가 영상/"
PANEL_DIR = ("/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
             "ddbd68df-0096-4baa-8c03-5768db49ad77/scratchpad/panels_n2j")
EVID = _R + "/.planning/quick/260906-n2j-stage-1-advisory/evidence/"

# M1 이 다룬 criterion 어깨 카드 4장. user_frame/ref_video_idx = crop 로그 실측.
CARDS = [
    # motion, analysis_id, card_idx, user_video, user_frame(u_idx_unit), ref_video_idx
    ("pdshape",   "4e232c4a73ec40a6a8deb07cbf6aa03f", 2,
     "pdshape(정확한명칭없음,잘못되예시).mp4", 89, 131),
    ("climb",     "a559705f06784505bf266afe99cf2822", 2,
     "클라임(잘못된예시).mp4", 53, 61),
    ("powerspin", "5ae210fabec349698e1d35912b8f22e1", 1,
     "파워스핀(잘못된예시).mp4", 54, 65),
    ("peterpan",  "21b1b7ed3bc84d829d201334e64acc5b", 0,
     "피터팬(잘못된예시).mp4", 48, 64),
]

VARIANTS = ("A", "B", "C", "D")
OUT = fz._OUT                                       # noqa: SLF001  360
ROUNDS = 5                                          # belle 09-03: 눈 판정은 5회 반복


# ── B 안 드로잉 (스크립트 국소 — fault_zoom.py 무수정) ────────────────────────
def _draw_joint_angle_clamped(img, vertex_px, limb_dir_px, torso_dir_px):
    """B 안 = `fz._draw_joint_angle` 과 동일하되 선 길이를 **관절까지로 클램프**.

    길이만 `min(고정길이, 꼭짓점→관절 실제 거리)` 로 바꾼다. 색·두께·halo 순서·
    호 반경·호 공식은 전부 fault_zoom 상수/함수를 그대로 호출한다(값 베끼기 0).
    """
    vx, vy = float(vertex_px[0]), float(vertex_px[1])

    def _u(p):
        dx, dy = float(p[0]) - vx, float(p[1]) - vy
        n = math.hypot(dx, dy)
        if n < fz._MIN_LEG_VEC_PX:                  # noqa: SLF001
            return None, n
        return (dx / n, dy / n), n

    ul, d_limb = _u(limb_dir_px)
    ut, d_torso = _u(torso_dir_px)
    if ul is None or ut is None:
        return False
    limb_len = min(fz._ANGLE_LIMB_LEN_FRAC * OUT, d_limb)     # noqa: SLF001
    torso_len = min(fz._ANGLE_TORSO_LEN_FRAC * OUT, d_torso)  # noqa: SLF001
    limb_end = (vx + ul[0] * limb_len, vy + ul[1] * limb_len)
    torso_end = (vx + ut[0] * torso_len, vy + ut[1] * torso_len)
    draw = ImageDraw.Draw(img)
    for w_ in (fz._ANGLE_HALO_W, fz._ANGLE_CORE_W):           # noqa: SLF001
        fill = fz._HALO if w_ == fz._ANGLE_HALO_W else fz._BRAND   # noqa: SLF001
        draw.line([(vx, vy), limb_end], fill=fill, width=w_)
        draw.line([(vx, vy), torso_end], fill=fill, width=w_)
    r = fz._ANGLE_ARC_R_FRAC * OUT                            # noqa: SLF001
    a1, a2 = fz._minor_arc_span_deg((vx, vy), limb_end, torso_end)  # noqa: SLF001
    draw.arc([vx - r, vy - r, vx + r, vy + r], start=a1, end=a2,
             fill=fz._HALO, width=3)                          # noqa: SLF001
    return True


def _draw_side_clamped(img, frame, spec, box):
    """B: `fz._draw_side_joint_angle` 과 같은 좌표 변환, 드로잉만 클램프판."""
    h, w = frame.shape[0], frame.shape[1]
    left, top, side = box
    vertex, limb, torso = spec
    return _draw_joint_angle_clamped(
        img,
        fz._to_crop_px(vertex, left, top, side, w, h),          # noqa: SLF001
        fz._to_crop_px_unclamped(limb, left, top, side, w, h),  # noqa: SLF001
        fz._to_crop_px_unclamped(torso, left, top, side, w, h),  # noqa: SLF001
    )


# ── 배달 패널 대조 (자가검증) ────────────────────────────────────────────────
def _brand_mask(im: Image.Image) -> np.ndarray:
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    br = np.array(fz._BRAND, dtype=np.int16)                  # noqa: SLF001
    return (np.abs(a - br).sum(axis=2) < 60)


def _has_time_badge(im: Image.Image) -> bool:
    """`fz._stamp_time` 이 찍는 무채색 배지(좌하단 (8,_OUT-34)) 존재 여부."""
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    patch = a[OUT - 30:OUT - 12, 10:26]
    dark = (np.abs(patch - np.array([40, 40, 40])).sum(axis=2) < 60)
    return bool(dark.mean() > 0.25)


def _locate_delivered_box(frame: np.ndarray, panel_path: str, side_px: int,
                          expect_box: tuple[int, int, int]) -> dict:
    """배달된 패널이 프레임의 **어느 상자**를 잘랐는지 역산 (밝기 L1 최소, 1px 격자).

    라이브 크롭 중심을 문서·로그에서 못 읽는 경로(멈춤 상속 = display_anchor 는
    align 17-kp 이고 어디에도 저장되지 않는다)가 있어, 배달된 산출물 위에서 직접
    잰다. 반환 delta = (실측 상자) − (저장 좌표로 계산한 상자), 원본 px.
    """
    if not os.path.exists(panel_path):
        return {"exists": False}
    panel = np.asarray(Image.open(panel_path).convert("L")).astype(np.float32)
    h, w = frame.shape[:2]
    sc = OUT / float(side_px)
    small = np.asarray(
        Image.fromarray(frame).convert("L").resize(
            (max(1, int(round(w * sc))), max(1, int(round(h * sc)))),
            Image.BILINEAR)
    ).astype(np.float32)
    H, W = small.shape
    best = (1e9, None)
    for step, span in ((3, 60), (1, 4)):
        c = best[1] or (int(round(expect_box[0] * sc)), int(round(expect_box[1] * sc)))
        lo_l, hi_l = c[0] - span, c[0] + span
        lo_t, hi_t = c[1] - span, c[1] + span
        if best[1] is None:                       # 1차 = 프레임 전역
            lo_l, hi_l, lo_t, hi_t = -60, W - OUT + 60, -60, H - OUT + 60
        found = (1e9, None)
        for top in range(lo_t, hi_t + 1, step):
            for left in range(lo_l, hi_l + 1, step):
                t0, l0 = max(0, top), max(0, left)
                t1, l1 = min(H, top + OUT), min(W, left + OUT)
                if t1 - t0 < 200 or l1 - l0 < 200:
                    continue
                m = float(np.abs(small[t0:t1, l0:l1]
                                 - panel[t0 - top:t1 - top, l0 - left:l1 - left]).mean())
                if m < found[0]:
                    found = (m, (left, top))
        best = found
    L, T = best[1]
    nl, nt = int(round(L / sc)), int(round(T / sc))
    return {"exists": True, "match_mae_gray": round(best[0], 2),
            "measured_box_native": [nl, nt],
            "expected_box_native": [expect_box[0], expect_box[1]],
            "delta_native_px": [nl - expect_box[0], nt - expect_box[1]],
            "delta_panel_px": [round((nl - expect_box[0]) * sc, 1),
                               round((nt - expect_box[1]) * sc, 1)]}


def _compare_to_delivered(rendered: Image.Image, panel_path: str) -> dict:
    if not os.path.exists(panel_path):
        return {"panel": os.path.basename(panel_path), "exists": False}
    ref = Image.open(panel_path).convert("RGB")
    if ref.size != rendered.size:
        ref = ref.resize(rendered.size, Image.BILINEAR)
    a = np.asarray(rendered.convert("RGB")).astype(np.int16)
    b = np.asarray(ref).astype(np.int16)
    mae = float(np.abs(a - b).mean())
    ma, mb = _brand_mask(rendered), _brand_mask(ref)
    inter = int((ma & mb).sum())
    union = int((ma | mb).sum())
    return {
        "panel": os.path.basename(panel_path), "exists": True,
        "mae": round(mae, 2),
        "brand_px_rendered": int(ma.sum()), "brand_px_delivered": int(mb.sum()),
        "brand_iou": round(inter / union, 3) if union else None,
    }


# ── 렌더 ────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUTDIR, exist_ok=True)
    render_only = os.environ.get("RENDER_ONLY") == "1"
    api_key = os.environ.get("GEMINI_API_KEY", "")
    ext = FfmpegFrameExtractor()
    workdir = Path(tempfile.mkdtemp(prefix="m2_native_"))

    faces, rows, unmeasurable, notes = [], [], [], []
    ref_cache: dict[str, dict] = {}

    for motion, aid, ci, uvid, u_idx, r_idx in CARDS:
        doc = fa.get_analysis(UID, aid)
        result = doc["result"]
        rid = doc.get("referenceMotionId")
        u_rep = result.get("keypointReport") or {}
        if rid not in ref_cache:
            ref_cache[rid] = ((fa.get_reference_motion(rid) or {})
                              .get("referenceKeypointReport") or {})
        r_rep = ref_cache[rid]
        c = (result.get("faultZoomComparisons") or [])[ci]
        crit = c["criterion"]
        joint = c["joint"]
        members = (crit.split("__")[-1],)
        u_fi, r_fi = int(c["userFrameIdx"]), int(c["refFrameIdx"])

        u_video = VIDBASE + uvid
        r_video = f"{REFDIR}/{rid}.mp4"
        u_fps = ext.probe_effective_fps(u_video)
        r_fps = ext.probe_effective_fps(r_video)
        u_frame = np.asarray(cr._native_frame(          # noqa: SLF001
            Path(u_video), u_idx / u_fps, workdir))
        r_frame = np.asarray(cr._native_frame(          # noqa: SLF001
            Path(r_video), r_idx / r_fps, workdir))

        reps = {"user": u_rep, "ref": r_rep}
        fis = {"user": u_fi, "ref": r_fi}
        frames = {"user": u_frame, "ref": r_frame}
        resolvers = {
            "user": fz._gated_kp,                       # noqa: SLF001
            "ref": fz.make_reference_anchor_resolver(rid, crit),
        }
        secs = {"user": u_idx / u_fps, "ref": r_idx / r_fps}

        # A 스펙(현행 겨드랑이 꼭짓점) · C 스펙(어깨 관절 꼭짓점)
        specA, specC = {}, {}
        for side in ("user", "ref"):
            sA = fz.build_angle_bake_spec(crit, members, reps[side], fis[side],
                                          resolvers[side])
            specA[side] = sA
            sh = resolvers[side](reps[side], fis[side], members[0])
            specC[side] = None if (sA is None or sh is None) else (sh, sA[1], sA[2])

        hw = {s: (frames[s].shape[0], frames[s].shape[1]) for s in ("user", "ref")}
        fracAB = fz.criterion_crop_frac((
            (specA["user"], hw["user"]), (specA["ref"], hw["ref"]),
        ))
        fracC = fz.criterion_crop_frac((
            (specC["user"], hw["user"]), (specC["ref"], hw["ref"]),
        ))

        card_rec = {
            "card": f"{motion}#{ci}", "motion": motion, "analysisId": aid,
            "criterion": crit, "joint": joint, "tier": c.get("tier"),
            "userFrameIdx": u_fi, "refFrameIdx": r_fi,
            "userMarked": c.get("userMarked"), "refMarked": c.get("refMarked"),
            "gatedPath": "holdState" in c,
            "user_video_frame_idx": u_idx, "ref_video_frame_idx": r_idx,
            "user_eff_fps": round(u_fps, 4), "ref_eff_fps": round(r_fps, 4),
            "frame_wh": {s: [hw[s][1], hw[s][0]] for s in hw},
            "crop_frac_A": round(fracAB, 4), "crop_frac_C": round(fracC, 4),
            "crop_frac_unchanged_by_C": abs(fracAB - fracC) < 1e-9,
            "expected_parts": sorted(cpa.expected_parts(crit, joint)),
            "sides": {},
        }

        for side in ("user", "ref"):
            frame = frames[side]
            h, w = hw[side]
            panel_path = os.path.join(
                PANEL_DIR, f"{aid[:8]}_{ci:02d}_{crit}_{side}.jpg")
            stamp = (_has_time_badge(Image.open(panel_path))
                     if os.path.exists(panel_path) else side == "user")
            per = {"stamp_time_from_delivered": stamp, "variants": {}}
            for v in VARIANTS:
                spec = specC[side] if v == "C" else specA[side]
                frac = fracC if v == "C" else fracAB
                if spec is None:
                    per["variants"][v] = {"rendered": False,
                                          "why": "스펙 미성립(게이트 미달/부재)"}
                    unmeasurable.append(
                        f"{motion}#{ci} {side} {v}: 스펙 미성립 — 렌더 불가")
                    rows.append({"motion": motion, "side": side, "variant": v,
                                 "eye_mode": "n/a", "tokens": [],
                                 "better_than_A": None})
                    continue
                side_px = fz.crop_side_px(frac, h, w)
                img, kind, anchor_px, box = fz._side_crop(   # noqa: SLF001
                    frame, [], [], anchor=spec[0],
                    center=spec[0], side_override=side_px)
                drew = False
                if v in ("A", "C"):
                    drew = fz._draw_side_joint_angle(       # noqa: SLF001
                        img, frame, spec, box)
                elif v == "B":
                    drew = _draw_side_clamped(img, frame, spec, box)
                if v == "D":
                    # 각 없음 — 부위 원 하나만. 운영 `_mark` 그대로, 앵커=꼭짓점.
                    img = fz._mark(img, circle=True, anchor_px=anchor_px)  # noqa: SLF001
                else:
                    img = fz._mark(img, circle=False, anchor_px=None)      # noqa: SLF001
                if stamp:
                    img = fz._stamp_time(img, secs[side])   # noqa: SLF001
                path = f"{OUTDIR}/{motion}_{side}_{v}.jpg"
                img.save(path, quality=92)
                rec = {"rendered": True, "path": path, "drew_angle": drew,
                       "crop_kind": kind, "crop_side_px": side_px,
                       "brand_px": int(_brand_mask(img).sum()),
                       "sha1": hashlib.sha1(open(path, "rb").read()).hexdigest()}
                if v == "A":
                    rec["vs_delivered"] = _compare_to_delivered(img, panel_path)
                    db = _locate_delivered_box(frame, panel_path, side_px, box)
                    # 배달 중심이 A(겨드랑이)인가 C(어깨 관절)인가 — 저장 좌표로
                    # 만든 두 후보 꼭짓점을 **A 의 크롭 상자**에서 패널 px 로 놓고
                    # 실측 델타와 견준다. (라이브 gated 경로는 크롭 중심을
                    # align 17-kp 로 갈아끼우는데 그 좌표가 어디에도 저장되지 않는다.)
                    if db.get("exists") and specC[side] is not None:
                        vA = fz._to_crop_px_unclamped(          # noqa: SLF001
                            spec[0], box[0], box[1], box[2], w, h)
                        vC = fz._to_crop_px_unclamped(          # noqa: SLF001
                            specC[side][0], box[0], box[1], box[2], w, h)
                        ac = (vC[0] - vA[0], vC[1] - vA[1])
                        dl = db["delta_panel_px"]
                        db["armpit_to_shoulder_panel_px"] = [round(ac[0], 1),
                                                             round(ac[1], 1)]
                        db["dist_delta_to_A_px"] = round(math.hypot(*dl), 1)
                        db["dist_delta_to_C_px"] = round(
                            math.hypot(dl[0] - ac[0], dl[1] - ac[1]), 1)
                        # 8px = 패널 360 의 2% — 이 안이어야 "그 후보다" 라고
                        # 말한다. 둘 다 밖이면 저장 좌표로 만들 수 없는 제3의 중심.
                        _near = min(db["dist_delta_to_A_px"],
                                    db["dist_delta_to_C_px"])
                        if _near > 8.0:
                            db["closer_to"] = "제3의 좌표(A·C 어느 쪽도 아님)"
                        else:
                            db["closer_to"] = ("A(겨드랑이)"
                                               if db["dist_delta_to_A_px"]
                                               <= db["dist_delta_to_C_px"]
                                               else "C(어깨 관절)")
                    rec["delivered_box"] = db
                per["variants"][v] = rec
            same_ab = (per["variants"]["A"].get("sha1")
                       == per["variants"]["B"].get("sha1"))
            per["B_identical_to_A"] = same_ab
            if same_ab:
                notes.append(
                    f"{motion} {side}: B 렌더가 A 와 **바이트 동일** "
                    "(고정 길이 64/85px 가 꼭짓점→관절 거리보다 짧아 클램프가 안 걸린다) "
                    "— 눈 호출은 그대로 하되 이 면에서 B 는 A 의 재측정이다.")
            card_rec["sides"][side] = per
        faces.append(card_rec)

    # ── 눈 ──────────────────────────────────────────────────────────────────
    # 이미 측정한 눈 답은 sha1(렌더 산출물) 키로 재사용한다 — 같은 그림에 같은 질문을
    # 다시 던지는 것은 새 측정이 아니고, 계기 호출 수만 늘린다. 캐시는 리포 밖 파일.
    cache_path = "/Users/Shared/sunity-shoulder-trial/_eye_cache.json"
    eye_cache: dict = {}
    if os.path.exists(cache_path):
        try:
            eye_cache = json.load(open(cache_path, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            eye_cache = {}

    if not render_only:
        if not api_key:
            notes.append("GEMINI_API_KEY 부재 — 눈 미측정")
        else:
            for card in faces:
                allowed = set(card["expected_parts"])
                for side, per in card["sides"].items():
                    for v in VARIANTS:
                        rec = per["variants"][v]
                        if not rec.get("rendered"):
                            continue
                        ck = f"{rec['sha1']}|{card['motion']}|{side}|{v}"
                        cached = eye_cache.get(ck)
                        if cached is not None:
                            r = cached
                        else:
                            r = cg.eye_part_token(
                                Image.open(rec["path"]).convert("RGB"),
                                api_key=api_key, rounds=ROUNDS)
                            eye_cache[ck] = r
                            with open(cache_path, "w", encoding="utf-8") as cf:
                                json.dump(eye_cache, cf, ensure_ascii=False)
                        print(f"eye {card['motion']}/{side}/{v} -> "
                              f"{r['observed']} {r['tokens']}"
                              f"{' (cached)' if cached else ''}", flush=True)
                        rec["eye"] = {
                            "observed": r["observed"], "tokens": r["tokens"],
                            "calls": r["calls"], "reason": r["reason"],
                            "cached": cached is not None,
                            "in_allowed": r["observed"] in allowed,
                        }
                    a = per["variants"]["A"].get("eye")
                    for v in VARIANTS:
                        rec = per["variants"][v]
                        e = rec.get("eye")
                        if a is None or e is None:
                            verdict = None
                        elif (a["observed"] in cpa.UNREAD
                              or e["observed"] in cpa.UNREAD):
                            verdict = None
                        elif a["in_allowed"] and e["in_allowed"]:
                            verdict = "same"
                        elif a["in_allowed"] and not e["in_allowed"]:
                            verdict = "worse"
                        elif not a["in_allowed"] and e["in_allowed"]:
                            verdict = "better"
                        else:
                            verdict = "same"
                        rec["better_than_A"] = verdict
                        rows.append({
                            "motion": card["motion"], "side": side, "variant": v,
                            "eye_mode": (e or {}).get("observed", "n/a"),
                            "tokens": (e or {}).get("tokens", []),
                            "better_than_A": verdict,
                        })

    # ── 계기 한계·재현 실측을 산출물에 같이 박는다 ────────────────────────────
    notes.append(
        "[계기 한계] `eye_part_token` 의 질문(_CLAIM_QUESTION['part'])은 "
        "\"사진 **정중앙**에 가장 크게 보이는 부위\"다. 이 문법은 꼭짓점을 패널 "
        "정중앙에 두므로 이 계기가 재는 것은 **꼭짓점이 어느 부위에 앉았는가**이고, "
        "belle 지적의 핵심인 \"선 끝이 다리에 닿는다\"는 **못 잰다** — 그건 M1 의 "
        "nearest_joint / leg_intrusion_px 몫이다. 새 어휘를 만들지 말라는 지시를 "
        "따랐고, 그래서 이 한계가 남는다.")
    notes.append(
        "[5회 규율] rounds=5 로 불렀다. `eye_part_token` 은 어느 토큰이 3표에 이르면 "
        "조기 종료한다(남은 표가 못 뒤집으므로 5회 최빈과 결과 동일) — 각 면의 "
        "tokens 길이가 실제 호출 수다.")
    _ab = [(c["motion"], s) for c in faces for s, p in c["sides"].items()
           if (p["variants"]["A"].get("eye") or {}).get("observed")
           != (p["variants"]["B"].get("eye") or {}).get("observed")]
    notes.append(
        f"[눈 재현율] A/B 렌더는 8면 전부 바이트 동일인데 최빈 토큰이 갈린 면 = "
        f"{len(_ab)}/8 {_ab}. 같은 그림에 같은 질문을 던진 결과라 이 수가 곧 "
        "이 계기의 노이즈 바닥이다.")
    _repro = {f'{c["motion"]}/{s}': p["variants"]["A"]["delivered_box"].get("closer_to")
              for c in faces for s, p in c["sides"].items()}
    notes.append(
        "[배달 재현] stage-1 카드(pdshape·powerspin)는 배달된 크롭 상자와 0~1 원본px "
        "일치 — 내 A 는 belle 이 본 그 사진과 같은 크롭이다. 멈춤 상속 카드"
        "(climb·peterpan)는 라이브가 꼭짓점을 display_anchor(align 17-kp, 어디에도 "
        "저장 안 됨)로 갈아끼워 상자가 다르다. 배달 중심이 어느 후보에 가까운가 = "
        f"{_repro}. peterpan 2면은 배달 중심이 **C(어깨 관절)** 에 3.5~5.2 패널px 로 "
        "붙는다 — 그 카드는 라이브에서 이미 C 문법으로 그려져 있었다는 뜻이다. "
        "climb 2면은 A(43.5·47.8)에도 C(46.8·37.8)에도 안 붙는 제3의 중심이다. "
        "네 면 다 여기 A 렌더는 반사실이다.")
    notes.append(
        "[반사실 1면] powerspin user 는 라이브에서 앵커 게이트가 표시를 억제했다"
        "(userMarked=False, 배달 패널 브랜드 픽셀 0). 여기 렌더는 \"억제가 없었다면\" "
        "의 그림이다 — 문법 비교에는 필요하지만 배달된 사진은 아니다.")

    out = {
        "generated": "2026-09-06",
        "preregistration": "SHOULDER-GRAMMAR-PREREGISTRATION.md (2906b272)",
        "instrument": "card_gates.eye_part_token (claim='part', PART_VOCAB)",
        "rounds": ROUNDS,
        "verdict_rule": ("A 의 최빈이 expected_parts 안이면 A 가 좋다. "
                         "A in/V in=same, A in/V out=worse, A out/V in=better, "
                         "A out/V out=same, 못 읽음=null"),
        "render_dir": OUTDIR,
        "cards": faces,
        "rows": rows,
        "unmeasurable": unmeasurable,
        "notes": notes,
    }
    p = EVID + "shoulder_grammar_m2.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"cards": len(faces), "rows": len(rows),
                      "unmeasurable": len(unmeasurable)}, ensure_ascii=False))
    print("wrote", p)


if __name__ == "__main__":
    main()
