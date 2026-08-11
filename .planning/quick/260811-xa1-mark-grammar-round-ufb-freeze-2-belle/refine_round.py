#!/usr/bin/env python3
"""마크 문법 라운드 2 정제 하네스 (quick-260811-xa1 continuation) — belle 판정 스펙.

belle 판정 (2026-08-12): E3 채택, 단 "정은지쪽 붉은 원이 좀만 더 조정되면 완벽" /
P1~P3 전부 반려 "선 자체가 어떻게 집고 있는질 모르니까". 이 하네스는:

  --baseline    라운드 1 게이트 재실행 (md5 == ufb 인증값 2/2 + survivors 일치).
  --diagnose    원 앵커 좌표 출처 실물 추적 — 대상 2카드 각 패널에 후보 좌표
                3종 마커 오버레이 + 트랙 정합 통계:
                  · rep12  = 현행 vertex 출처 (12관절 keypointReport, 기준측은
                    phase4_v1 pinned 구 리포트) — 초록 X
                  · al17i  = align 17-kp 트랙, **콘텐츠 선형 인덱스**
                    round(rep_idx x al_frames / rep_frames) — 파랑 십자
                  · al17t  = align 17-kp 트랙, fps 라벨 초 공식
                    round(freeze_sec x al_fps) — 주황 마름모
                판정 재료: 어느 좌표가 **표시된 그 프레임**의 관절 위에 앉는가.
  --candidates  E3r1 (왼팔꿈치 스포트라이트, 원 좌표 출처 교정) + P4 (왼골반
                스포트라이트, E3 문법 이식 + 같은 출처 원칙). 교정 = 픽셀
                오프셋이 아니라 **좌표 출처 교체** — align 17-kp 트랙을 게이트
                freeze 순간 인덱스로 읽는다 (belle "지금 쓴 영상만 잘 돌아가는
                건 아닌지" 규율 — 게이트/기계눈과 같은 공식, 튜닝상수 0.
                근거는 _R2Patch docstring + diagnose.json).
  --composite   E3(보정 전) / E3r1(보정 후) 세로 나란히 1장.

라운드 1 하네스(grammar_round)를 import 재사용 — 운영 코드 무접촉, Gemini 0회
(machine_eye 스텁 + env 더미 키), ufb evidence EV 리다이렉트 가드 전부 상속.
프로덕션 코드 아님 — quick 디렉터리 로컬 하네스. 채점 무접촉.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import pathlib
import shutil
import sys

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import grammar_round as gr  # noqa: E402 - 부작용 = 라운드 1 스텁/가드 전부 상속

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

vl = gr.vl
bz = gr.bz
fz = gr.fz
cg = gr.cg

OUT = gr.OUT
BASE = gr.BASE
CAND = gr.CAND
DIAG = OUT / "diagnose"

CARD_NAME = gr.CARD_NAME
CERT_MD5 = gr.CERT_MD5
CERT_SURVIVORS = gr.CERT_SURVIVORS
FREEZE_SEC = gr.FREEZE_SEC

log = logging.getLogger("refine_round")

MODES2 = {"E3r1": "left_elbow", "P4": "left_hip"}

# 마커 색 (진단 전용 — 브랜드 레드 드로잉과 구분되는 색)
_C_REP12 = (0, 190, 0)      # 초록 X — 현행 vertex 출처
_C_AL17I = (40, 110, 255)   # 파랑 십자 — align 17kp 콘텐츠 선형 인덱스
_C_AL17T = (255, 150, 0)    # 주황 마름모 — align 17kp fps 라벨 초 공식


def _content_linear_idx(rep_idx: int, rep_frames: int, al_frames: int) -> int:
    """rep 인덱스 → align 인덱스, 콘텐츠 선형 매핑 (데이터-유도, 튜닝상수 0).

    두 트랙이 같은 영상 콘텐츠 구간을 다른 밀도로 덮는다는 사실에서 유도 —
    `ref_display_frame_index` 의 "길이 비례 선형 매핑" 선례와 같은 공식.
    rep_frames == al_frames (pdshape ref: 237==237) 이면 identity.
    """
    if rep_frames <= 0 or al_frames <= 0:
        return 0
    return max(0, min(int(round(rep_idx * al_frames / rep_frames)), al_frames - 1))


def _draw_x(draw, p, color, r=9, w=3):
    draw.line([(p[0] - r, p[1] - r), (p[0] + r, p[1] + r)], fill=color, width=w)
    draw.line([(p[0] - r, p[1] + r), (p[0] + r, p[1] - r)], fill=color, width=w)


def _draw_plus(draw, p, color, r=11, w=3):
    draw.line([(p[0] - r, p[1]), (p[0] + r, p[1])], fill=color, width=w)
    draw.line([(p[0], p[1] - r), (p[0], p[1] + r)], fill=color, width=w)


def _draw_diamond(draw, p, color, r=9, w=3):
    pts = [(p[0], p[1] - r), (p[0] + r, p[1]), (p[0], p[1] + r), (p[0] - r, p[1])]
    draw.polygon(pts, outline=color, width=w)


# ── 진단 패치 — 원본 드로잉 유지 + 후보 좌표 3종 마커 오버레이 ────────────────
class _DiagPatch(gr._CandidatePatch):
    """대상 2카드 모두에 마커 오버레이 (드로잉은 원본 유지 — 문법 비교 기준 보존).

    라운드 1 `_CandidatePatch` 의 build/spec/side/build_align 랩 재사용. mode 는
    사용하지 않는다 (진단 전용) — joint 를 카드별로 판정한다.
    """

    def __init__(self):
        super().__init__("DIAG", "left_elbow", None, {})
        self.rows: list[dict] = []

    def _spec(self, criterion, members, report, frame_idx, resolver=None):
        # 부모는 self.joint 카드만 캡처 — 진단은 대상 2카드 모두 캡처한다.
        if any(j in self.cur_joints for j in CARD_NAME):
            self.metas.setdefault(id(report), (report, int(frame_idx)))
        return self._orig_spec(criterion, members, report, frame_idx, resolver)

    def _panel_joint(self) -> str | None:
        for j in CARD_NAME:
            if j in self.cur_joints:
                return j
        return None

    def _side(self, img, frame, spec, box):
        joint = self._panel_joint()
        if joint is None:
            return self._orig_side(img, frame, spec, box)
        i = self.draw_i
        self.draw_i += 1
        panel = "user" if i == 0 else "ref"
        ok = self._orig_side(img, frame, spec, box)  # 원본 문법 그대로

        h, w = frame.shape[0], frame.shape[1]
        left, top, side = box

        def _cp(p):
            return fz._to_crop_px_unclamped(p, left, top, side, w, h)

        metas = list(self.metas.values())
        meta = metas[i] if i < len(metas) else None
        row: dict = {"joint": joint, "panel": panel, "box": [left, top, side],
                     "frameWH": [w, h]}
        draw = ImageDraw.Draw(img)

        # ① rep12 — 현행 vertex 출처 (spec[0])
        v_px = _cp(spec[0])
        row["rep12"] = {"normXY": list(spec[0]), "px": list(v_px)}
        if meta is not None:
            rep, rep_idx = meta
            row["rep12"]["repIdx"] = int(rep_idx)
            row["rep12"]["repFrames"] = int(rep.get("frames") or 0)
            row["rep12"]["repFps"] = float(rep.get("fps") or 0.0)
            c = fz._kp_conf(rep, rep_idx, joint)
            row["rep12"]["conf"] = None if c is None else float(c)
            # 선 앵커 진단 재료 — limb/torso 방향점 (P1~P3 선이 가리키던 것)
            row["specLimbPx"] = list(_cp(spec[1]))
            row["specTorsoPx"] = list(_cp(spec[2]))
        _draw_x(draw, v_px, _C_REP12)

        # ② ③ align 17-kp — 콘텐츠 선형 인덱스 / fps 라벨 초 공식
        al_rep = None
        if self.align is not None:
            try:
                al_rep = self._rep17.get(panel) or cg.align_to_report(
                    self.align, panel)
                self._rep17[panel] = al_rep
            except Exception:  # noqa: BLE001 - refKp 부재 등 → 진단 표기만
                al_rep = None
        if al_rep is not None and meta is not None:
            rep, rep_idx = meta
            ai = _content_linear_idx(
                int(rep_idx), int(rep.get("frames") or 0), int(al_rep["frames"]))
            at = max(0, min(int(round(FREEZE_SEC[joint][panel]
                                      * float(al_rep["fps"]))),
                            int(al_rep["frames"]) - 1))
            for key, idx, drawer, color in (
                ("al17i", ai, _draw_plus, _C_AL17I),
                ("al17t", at, _draw_diamond, _C_AL17T),
            ):
                p = cg.kp(al_rep, idx, joint, conf_min=0.0)
                conf = None
                if p is not None:
                    # conf 는 기록 (게이트는 candidates 단계 몫)
                    rn = cg._resolve(al_rep, joint)
                    conf = fz._kp_conf(al_rep, idx, rn) if rn else None
                    px = _cp(p)
                    drawer(draw, px, color)
                    row[key] = {"alignIdx": idx, "normXY": list(p),
                                "px": list(px),
                                "conf": None if conf is None else float(conf)}
                else:
                    row[key] = {"alignIdx": idx, "normXY": None, "px": None,
                                "conf": None}
        self.rows.append(row)
        return ok


def _track_correlation(align: dict) -> dict:
    """rep 트랙 vs align 17-kp 트랙 — 인덱스 매핑 가설 2종의 평균 px 거리.

    가설 H-linear: 같은 콘텐츠 구간 선형 인덱스 매핑 (`_content_linear_idx`).
    가설 H-label:  fps 라벨 신뢰 매핑 round(i / rep_fps * al_fps).
    거리가 작은 쪽이 실제 대응 — "같은 시퀀스인가" 를 데이터로 판정.
    """
    doc = json.loads(vl.DOC.read_text())
    urep = doc["result"].get("keypointReport") or {}
    rrep = json.loads(vl.REFMOTION.read_text())["referenceKeypointReport"]
    out: dict = {}
    for side, rep in (("user", urep), ("ref", rrep)):
        al = cg.align_to_report(align, side)
        W, H = (align.get(f"{side}Size") or (1, 1))
        rf = int(rep.get("frames") or 0)
        af = int(al["frames"])
        rfps = float(rep.get("fps") or 1.0)
        afps = float(al["fps"])
        stats: dict = {"repFrames": rf, "alFrames": af,
                       "repFps": rfps, "alFps": afps}
        for joint in ("left_elbow", "left_hip"):
            dists: dict[str, list[float]] = {"linear": [], "label": []}
            for i in range(rf):
                rp = fz._gated_kp(rep, i, joint)
                if rp is None:
                    continue
                for hyp, ai in (
                    ("linear", _content_linear_idx(i, rf, af)),
                    ("label", max(0, min(int(round(i / rfps * afps)), af - 1))),
                ):
                    ap = cg.kp(al, ai, joint, conf_min=0.0)
                    if ap is None:
                        continue
                    dists[hyp].append(math.hypot(
                        (rp[0] - ap[0]) * W, (rp[1] - ap[1]) * H))
            stats[joint] = {
                hyp: {
                    "n": len(v),
                    "meanPx": (sum(v) / len(v)) if v else None,
                    "medianPx": (sorted(v)[len(v) // 2]) if v else None,
                }
                for hyp, v in dists.items()
            }
        out[side] = stats
    return out


def diagnose() -> int:
    gr._guard_ev()
    gr._require_cache()
    gate_p = BASE / "gate.json"
    if not gate_p.exists() or not json.loads(gate_p.read_text()).get("pass"):
        print("baseline 게이트 PASS 선행 필요 — --baseline 먼저")
        return 1
    DIAG.mkdir(parents=True, exist_ok=True)
    patch = _DiagPatch()
    patch.install()
    try:
        out = vl.run()
    finally:
        patch.restore()
    surv_ok = list(out["verdict"]["survivors"]) == CERT_SURVIVORS
    for joint, name in CARD_NAME.items():
        src = vl.EV / "cards" / name
        if src.exists():
            shutil.copy2(src, DIAG / name)
    corr = _track_correlation(patch.align) if patch.align is not None else {}
    diag = {"survivorsOk": surv_ok, "rows": patch.rows,
            "trackCorrelation": corr,
            "legend": {"rep12": "초록 X — 현행 vertex (12관절 report)",
                       "al17i": "파랑 십자 — align 17kp 콘텐츠 선형 인덱스",
                       "al17t": "주황 마름모 — align 17kp fps 라벨 초 공식"}}
    (DIAG / "diagnose.json").write_text(
        json.dumps(diag, ensure_ascii=False, indent=1))
    for row in patch.rows:
        r12 = row.get("rep12") or {}
        a_i = row.get("al17i") or {}
        a_t = row.get("al17t") or {}

        def _d(a, b):
            if not a or not b or a.get("px") is None or b.get("px") is None:
                return None
            return math.hypot(a["px"][0] - b["px"][0], a["px"][1] - b["px"][1])

        print(f"{row['joint']}/{row['panel']}: rep12@{r12.get('repIdx')} "
              f"conf={r12.get('conf')} | al17i@{a_i.get('alignIdx')} "
              f"conf={a_i.get('conf')} d={_d(r12, a_i)} | "
              f"al17t@{a_t.get('alignIdx')} conf={a_t.get('conf')} "
              f"d={_d(r12, a_t)}")
    for side, st in corr.items():
        for joint in ("left_elbow", "left_hip"):
            s = st.get(joint) or {}
            lin = (s.get("linear") or {}).get("meanPx")
            lab = (s.get("label") or {}).get("meanPx")
            print(f"corr {side}/{joint}: linear={lin} label={lab} "
                  f"(repF={st['repFrames']} alF={st['alFrames']})")
    print(f"survivors {'OK' if surv_ok else 'CHANGED — 진단 무효'}")
    return 0 if surv_ok else 1


# ── 후보 패치 — E3r1 / P4 (스포트라이트, 원 좌표 출처 = 게이트 순간 트랙) ────
class _R2Patch(gr._CandidatePatch):
    """스포트라이트 문법 + 원 좌표 출처 = align 17-kp **게이트 freeze 순간**.

    진단(--diagnose + 타임베이스 교차검증) 실측 근거:
      · align 트랙의 fps 라벨(15)은 실측과 일치한다 — 게이트/기계눈이 이미
        `round(freeze_sec x align_fps)` 인덱스로 홀드/짝/눈 검증을 통과시켰고,
        눈 프레임(초 x FPS_OUT)과 같은 실초로 맞아떨어진다 (app 게이트 공식).
      · 반면 12관절 report 의 fps 라벨은 실측과 어긋난다 (user: 라벨 18 vs 실효
        ~20 / ref: 라벨 18 vs 실효 ~14.9 — diagnose.json trackCorrelation 에서
        라벨 매핑 평균오차가 선형 매핑의 5~9배). 현행 vertex 는 이 어긋난 라벨
        사슬(`_to_rep_idx`)을 지나므로 ref 측에서 1프레임 이르게 읽힌다 — 팔이
        ~600px/s 로 쓸리는 이 freeze 에선 그 1프레임이 원을 관절 밖으로 민다
        (belle "정은지쪽 붉은 원" 반려의 뿌리).
    교정 = **좌표 출처 교체** (게이트가 인증한 그 순간의 그 트랙): 픽셀 오프셋
    0, 동작/영상 분기 0, 튜닝상수 0 — 어느 분석에서도 같은 공식.

    양 패널 동일 출처 (단일 출처 원칙). align 좌표가 conf 게이트
    (fz._KP_CONF_MIN — 드로잉 규율 단일 출처) 미달이면 **미방출** (엉뚱한
    좌표로 폴백하지 않는다 — fail-closed).
    """

    def __init__(self, mode: str, joint: str, poles: dict):
        super().__init__(mode, joint, None, poles)

    def _gate_moment_px(self, panel: str, frame, box):
        """align 17-kp @ round(freeze_sec x align_fps) → crop px | None."""
        if self.align is None:
            return None
        try:
            al_rep = self._rep17.get(panel) or cg.align_to_report(
                self.align, panel)
            self._rep17[panel] = al_rep
        except Exception:  # noqa: BLE001 - refKp 부재 → 교정 불가
            return None
        idx = max(0, min(
            int(round(FREEZE_SEC[self.joint][panel] * float(al_rep["fps"]))),
            int(al_rep["frames"]) - 1))
        p = cg.kp(al_rep, idx, self.joint, conf_min=fz._KP_CONF_MIN)
        if p is None:
            self.notes.append(
                f"{panel}: al17@{idx} conf 게이트({fz._KP_CONF_MIN}) 미달 — 미방출")
            return None
        h, w = frame.shape[0], frame.shape[1]
        left, top, side = box
        px = fz._to_crop_px_unclamped(p, left, top, side, w, h)
        self.notes.append(
            f"{panel}: 원 좌표 출처 rep12->al17(게이트 순간)@{idx} "
            f"px=({px[0]:.0f},{px[1]:.0f})")
        return px

    def _side(self, img, frame, spec, box):
        if self.joint not in self.cur_joints:
            return self._orig_side(img, frame, spec, box)
        i = self.draw_i
        self.draw_i += 1
        panel = "user" if i == 0 else "ref"
        v = self._gate_moment_px(panel, frame, box)
        if v is None:
            return False  # fail-closed — 카드 미방출로 게이트가 잡는다
        head = self._head_disc_align(panel, frame, box)
        return gr._draw_e3(img, v, head, self.notes, panel)


def candidates2() -> int:
    gr._guard_ev()
    gr._require_cache()
    gate_p = BASE / "gate.json"
    if not gate_p.exists() or not json.loads(gate_p.read_text()).get("pass"):
        print("baseline 게이트 PASS 선행 필요 — --baseline 먼저")
        return 1
    poles: dict = {}
    for pside in ("user", "ref"):
        p = vl.RENDER_WORK / f"pole_{pside}.json"
        poles[pside] = (
            json.loads(p.read_text()).get("xNorm") if p.exists() else None
        )
    fails: list[str] = []
    summary: dict = {}
    for mode, joint in MODES2.items():
        print(f"── candidate {mode} ({joint}) ──")
        patch = _R2Patch(mode, joint, poles)
        patch.install()
        try:
            out = vl.run()
        finally:
            patch.restore()
        mdir = CAND / mode
        mdir.mkdir(parents=True, exist_ok=True)
        src = vl.EV / "cards" / CARD_NAME[joint]
        if not src.exists():
            print(f"  FAIL: {CARD_NAME[joint]} 미방출")
            fails.append(mode)
            continue
        shutil.copy2(src, mdir / CARD_NAME[joint])
        other = next(j for j in CARD_NAME if j != joint)
        leak_ok = out["pngMd5"].get(CARD_NAME[other]) == CERT_MD5[CARD_NAME[other]]
        surv_ok = list(out["verdict"]["survivors"]) == CERT_SURVIVORS
        changed = out["pngMd5"].get(CARD_NAME[joint]) != CERT_MD5[CARD_NAME[joint]]
        summary[mode] = {
            "joint": joint,
            "leakFreeOtherCard": leak_ok, "survivorsOk": surv_ok,
            "targetChanged": changed, "notes": patch.notes,
            "targetMd5": out["pngMd5"].get(CARD_NAME[joint]),
        }
        print(f"  leak-free={leak_ok} survivors={surv_ok} changed={changed}")
        for n in patch.notes:
            print(f"  note: {n}")
        if not (leak_ok and surv_ok and changed):
            fails.append(mode)
    (CAND / "render_summary_round2.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"eye stub calls (이 프로세스 누적): {gr._EYE_STUB['calls']} — "
          "machine_eye 스텁, Gemini 실호출 0")
    if fails:
        print(f"CANDIDATES-R2 FAIL: {fails}")
        return 1
    print("CANDIDATES-R2 PASS (2/2 방출 + 비대상 카드 무누출 + survivors 불변)")
    return 0


def composite() -> int:
    """E3(보정 전) / E3r1(보정 후) 세로 나란히 — belle 판정용 1장."""
    before_p = CAND / "E3" / CARD_NAME["left_elbow"]
    after_p = CAND / "E3r1" / CARD_NAME["left_elbow"]
    if not before_p.exists() or not after_p.exists():
        print("E3/E3r1 카드 부재 — --candidates 선행")
        return 1
    before = Image.open(before_p).convert("RGB")
    after = Image.open(after_p).convert("RGB")
    W = max(before.width, after.width)
    bar = 34
    canvas = Image.new("RGB", (W, before.height + after.height + bar * 2),
                       (255, 255, 255))
    font = None
    for cand in ("/System/Library/Fonts/AppleSDGothicNeo.ttc",):
        try:
            font = ImageFont.truetype(cand, 20)
            break
        except Exception:  # noqa: BLE001 - 폰트 부재 → 기본 폰트
            font = None
    draw = ImageDraw.Draw(canvas)
    y = 0
    for label, img in (
        ("보정 전 (E3) — 원 = 12관절 report 좌표 (fps 라벨 사슬)", before),
        ("보정 후 (E3-r1) — 원 = align 17kp, 게이트 freeze 순간", after),
    ):
        draw.rectangle([0, y, W, y + bar], fill=(24, 24, 28))
        try:
            draw.text((10, y + 6), label, fill=(255, 255, 255), font=font)
        except Exception:  # noqa: BLE001 - 글리프 실패 → 영문 폴백
            draw.text((10, y + 10), label.encode("ascii", "ignore").decode(),
                      fill=(255, 255, 255))
        y += bar
        canvas.paste(img, (0, y))
        y += img.height
    out_p = CAND / "E3r1" / "before_after.png"
    canvas.save(out_p)
    print(f"composite -> {out_p}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--diagnose", action="store_true")
    ap.add_argument("--candidates", action="store_true")
    ap.add_argument("--composite", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    rc = 0
    if args.baseline:
        rc = gr.baseline()
    if args.diagnose and rc == 0:
        rc = diagnose()
    if args.candidates and rc == 0:
        rc = candidates2()
    if args.composite and rc == 0:
        rc = composite()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
