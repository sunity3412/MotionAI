#!/usr/bin/env python3
"""마크 문법 라운드 3 하네스 (quick-260813-ebd) — belle 08-13 번복 판정 스펙.

belle 08-13 (locked): D-01 스포트라이트 채택 철회 / D-02 골반 = P3 채택 /
D-03 팔꿈치 = V 문법 채택 + 얼굴회피 위치 보정 ("E1보다 좀 더 길어지는 건
상관없음. 네가 가장 표현 잘하는 방향으로 추천"). 이 하네스는:

  --baseline    라운드 1 게이트 재실행 위임 (gr.baseline — md5 2/2 == ufb
                인증값 + survivors 일치). FAIL 이면 박제 후 정지 (bz5 규율).
  --candidates  라운드 3 후보 렌더:
                  · P3r1  D-02 채택본(P3 하이브리드)의 좌표 수리 재렌더 —
                    vertex 를 align 17-kp 게이트 freeze 순간으로 교체
                    (라운드 2 진단: 라운드 1 P3 vertex = 12관절 report 좌표
                    = fps 라벨 사슬, align 단일 출처와 user 1.6px/ref 8.7px
                    차이). 드로잉은 라운드 1 P3 경로 그대로.
                  · EV1~EV3  D-03 팔꿈치 얼굴회피 V 변형안 — V 2가닥 문법
                    유지 + 얼굴·머리 관통 0. 차이는 선의 길이·도달점 문법뿐:
                      EV1 관절 도달 선 — 허공 스텁 대신 실측 손목·어깨
                          keypoint(같은 align 게이트 순간)까지, 원반 진입 전
                          클리핑. (라운드 2 진단 "선이 관절에 닿지 않는다" 수리)
                      EV2 팔길이 비례 — 방향 = 평행이동한 bake spec (V 사이각
                          보존), 길이 = 실측 전완/상완 px x 0.85 (고정 프랙션
                          폐기 — 스텁이 허공에서 끝나지 않게 사지 실물을 따라감).
                      EV3 E1 연장 — 채택 베이스라인 문법 최소 변경: 고정 방향
                          스텁 x1.6 (belle "E1보다 길어도 됨") + 원반 클리핑
                          유지 + 호 복원 조건 완화 (원반 밖 구간만 폴리라인 —
                          사이각 시각 재료 복원).

좌표 규율 (전 후보 공통 — fps 라벨 사슬 skew 재도입 금지):
  vertex = `refine_round._R2Patch._gate_moment_px` 그대로 상속 —
  align 17-kp @ round(freeze_sec x align_fps), conf >= fz._KP_CONF_MIN,
  미달 = 미방출 (fail-closed). limb/torso 방향점은 bake spec 값을 vertex
  이동 델타만큼 평행이동 (V 사이각·방향 보존, 앵커만 수리 — `_to_rep_idx`
  fps 라벨 사슬 경유 0). 원반 규칙도 전 변형안 공통 (`_head_disc_align`
  옵션 ① + `_split_by_disc` 진입 전 클리핑, 원반 뒤 재개 금지).

refine_round(→ grammar_round) importlib 로드 — 인터프리터 자동 승격·Gemini
스텁·EV 리다이렉트(`vl.EV` = xa1 out/_ev, 재지정 금지)·`_guard_ev` 가드 전부
상속. 운영 코드 무접촉, 채점 무접촉. 프로덕션 코드 아님 — quick 로컬 하네스.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import math
import pathlib
import shutil
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_XA1 = _HERE.parent / "260811-xa1-mark-grammar-round-ufb-freeze-2-belle"


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# refine_round 로드 — 내부에서 grammar_round import (스텁/가드/승격 전부 상속).
rr = _load_module("refine_round", _XA1 / "refine_round.py")
gr = rr.gr if hasattr(rr, "gr") else sys.modules["grammar_round"]

from PIL import ImageDraw  # noqa: E402

vl = rr.vl
bz = rr.bz
fz = rr.fz
cg = rr.cg

OUT3 = _HERE / "out"
CAND3 = OUT3 / "candidates"

log = logging.getLogger("round3")

MODES3 = {"P3r1": "left_hip", "EV1": "left_elbow",
          "EV2": "left_elbow", "EV3": "left_elbow"}

_EV2_REACH_FRAC = 0.85   # EV2 — 실측 세그먼트 길이 대비 스텁 길이 (도달 직전 종료)
_EV3_LEN_MULT = 1.6      # EV3 — E1 고정 프랙션 대비 연장 배율 (belle "길어도 됨")
_DISC_MARGIN = 8.0       # 원반 여유 px (gr._split_by_disc 기본과 동일)


# ── 라운드 3 공통 패치 — vertex = _gate_moment_px 상속 + 방향점 평행이동 ─────
class _R3Patch(rr._R2Patch):
    """vertex = `_R2Patch._gate_moment_px` **그대로 상속** (좌표 단일 출처).

    limb/torso 방향점 = bake spec 값을 vertex 이동 델타만큼 평행이동 —
    V 사이각·방향 보존, 앵커만 수리. `_gate_moment_px` 가 conf 게이트
    (fz._KP_CONF_MIN) 미달이면 None → 미방출 (fail-closed, 게이트가 잡는다).
    """

    @staticmethod
    def _px_to_norm(px, left, top, side, w, h):
        """`fz._to_crop_px_unclamped` 의 정확 역변환 (아핀) — 공식 재발명 아님."""
        s = max(1, int(side))
        return (px[0] / fz._OUT * s + left) / w, (px[1] / fz._OUT * s + top) / h

    def _gate_idx(self, panel: str, al_rep: dict) -> int:
        """`_gate_moment_px` 와 같은 인덱스 공식 — round(freeze_sec x align_fps)."""
        return max(0, min(
            int(round(rr.FREEZE_SEC[self.joint][panel] * float(al_rep["fps"]))),
            int(al_rep["frames"]) - 1))

    def _repaired_pts(self, panel: str, frame, spec, box):
        """(v_new_px, l_px, t_px) — vertex 수리 + 방향점 평행이동. None = 미방출."""
        v_new = self._gate_moment_px(panel, frame, box)
        if v_new is None:
            return None
        h, w = frame.shape[0], frame.shape[1]
        left, top, side = box
        v_old = fz._to_crop_px_unclamped(spec[0], left, top, side, w, h)
        dx, dy = v_new[0] - v_old[0], v_new[1] - v_old[1]
        l_old = fz._to_crop_px_unclamped(spec[1], left, top, side, w, h)
        t_old = fz._to_crop_px_unclamped(spec[2], left, top, side, w, h)
        self.notes.append(
            f"{panel}: vertex 이동 {math.hypot(dx, dy):.1f}px "
            f"(dx={dx:.1f}, dy={dy:.1f}) — 방향점 평행이동 (V 사이각 보존)")
        return v_new, (l_old[0] + dx, l_old[1] + dy), (t_old[0] + dx, t_old[1] + dy)


# ── P3r1 — D-02 채택본(P3 하이브리드)의 좌표 수리 재렌더 ─────────────────────
class _P3R1Patch(_R3Patch):
    """드로잉 = 라운드 1 P3 경로 그대로 (user=bz hybrid / ref=원본 문법).

    바뀌는 것은 앵커뿐 — vertex 가 align 게이트 순간 단일 출처로 이동하고,
    방향점·(ref 패널) spec 전체가 그 델타만큼 평행이동한다.
    """

    def __init__(self, poles: dict, ref_deg):
        super().__init__("P3r1", "left_hip", poles)
        self.p3_ref_deg = ref_deg

    def _side(self, img, frame, spec, box):
        if self.joint not in self.cur_joints:
            return self._orig_side(img, frame, spec, box)
        i = self.draw_i
        self.draw_i += 1
        panel = "user" if i == 0 else "ref"
        got = self._repaired_pts(panel, frame, spec, box)
        if got is None:
            return False  # fail-closed — 카드 미방출로 게이트가 잡는다
        v, l, t = got
        if panel == "user":
            if self.p3_ref_deg is None or not math.isfinite(float(self.p3_ref_deg)):
                self.notes.append("user: refDeg 부재 — 미방출")
                return False
            return bz._draw_candidate(img, v, l, t, float(self.p3_ref_deg), "hybrid")
        # ref 패널 = 평행이동한 spec 으로 원본 문법 호출 (라운드 1 P3 미러)
        h, w = frame.shape[0], frame.shape[1]
        left, top, side = box
        v_n = self._px_to_norm(v, left, top, side, w, h)
        d_n = (v_n[0] - spec[0][0], v_n[1] - spec[0][1])
        spec2 = (
            v_n,
            (spec[1][0] + d_n[0], spec[1][1] + d_n[1]),
            (spec[2][0] + d_n[0], spec[2][1] + d_n[1]),
        )
        return self._orig_side(img, frame, spec2, box)


# ── EV 변형안 드로잉 (관통 규칙 공통 — 진입 전 클리핑, 원반 뒤 재개 금지) ────
def _clip_before_disc(v, end, head):
    """v→end 선을 원반 진입 전까지만. None = 시작점이 원반 안 (전체 생략)."""
    segs = gr._split_by_disc(v, end, head)
    if not segs or segs[0][0] != v:
        return None
    return segs[0]


def _draw_strands(img, v, kept):
    draw = ImageDraw.Draw(img)
    for w_ in (fz._ANGLE_HALO_W, fz._ANGLE_CORE_W):
        fill = fz._HALO if w_ == fz._ANGLE_HALO_W else fz._BRAND
        for seg in kept:
            draw.line([seg[0], seg[1]], fill=fill, width=w_)
    gr._vertex_ring(draw, v)


def _draw_ev1(img, v, wrist, shoulder, head, notes, panel) -> bool:
    """EV1 관절 도달 선 — 실측 손목·어깨까지 (진단 "선이 관절에 닿지 않는다" 수리)."""
    kept = []
    for name, end in (("wrist", wrist), ("shoulder", shoulder)):
        seg = _clip_before_disc(v, end, head)
        if seg is None:
            notes.append(f"{panel}: {name} 선 전체 생략 (시작점 원반 안)")
            continue
        if seg[1] != end:
            notes.append(f"{panel}: {name} 선 원반 진입 전 클리핑")
        kept.append(seg)
    if len(kept) < 2:
        notes.append(f"{panel}: V 2가닥 미성립 — 미방출")
        return False
    _draw_strands(img, v, kept)
    return True


def _draw_ev2(img, v, l_dir, t_dir, fore_px, upper_px, head, notes, panel) -> bool:
    """EV2 팔길이 비례 — 방향 = 평행이동 spec, 길이 = 실측 세그먼트 x 0.85."""
    ul, ut = bz._unit_vec(v, l_dir), bz._unit_vec(v, t_dir)
    if ul is None or ut is None:
        return False
    kept = []
    for name, u, seg_len in (("limb", ul, fore_px), ("torso", ut, upper_px)):
        end = (v[0] + u[0] * seg_len * _EV2_REACH_FRAC,
               v[1] + u[1] * seg_len * _EV2_REACH_FRAC)
        seg = _clip_before_disc(v, end, head)
        if seg is None:
            notes.append(f"{panel}: {name} 선 전체 생략 (시작점 원반 안)")
            continue
        if seg[1] != end:
            notes.append(f"{panel}: {name} 선 원반 진입 전 클리핑")
        kept.append(seg)
    if len(kept) < 2:
        notes.append(f"{panel}: V 2가닥 미성립 — 미방출")
        return False
    _draw_strands(img, v, kept)
    return True


def _arc_outside_disc(draw, v, r, a1, a2, head):
    """호를 원반 밖 구간만 폴리라인으로 — EV3 호 복원 조건 완화."""
    span = (a2 - a1) % 360
    n = max(2, int(span))
    run: list = []

    def _flush():
        if len(run) >= 2:
            draw.line(run, fill=fz._HALO, width=3)
        run.clear()

    for k in range(n + 1):
        a = math.radians(a1 + span * k / n)
        p = (v[0] + r * math.cos(a), v[1] + r * math.sin(a))
        inside = head is not None and math.hypot(
            p[0] - head[0][0], p[1] - head[0][1]) < head[1] + _DISC_MARGIN
        if inside:
            _flush()
        else:
            run.append(p)
    _flush()


def _draw_ev3(img, v, l_dir, t_dir, head, notes, panel) -> bool:
    """EV3 E1 연장 — 고정 방향 스텁 x1.6 + 원반 클리핑 + 호 복원(원반 밖 구간)."""
    ul, ut = bz._unit_vec(v, l_dir), bz._unit_vec(v, t_dir)
    if ul is None or ut is None:
        return False
    sidepx = min(img.size)
    ends = {
        "limb": (v[0] + ul[0] * fz._ANGLE_LIMB_LEN_FRAC * _EV3_LEN_MULT * sidepx,
                 v[1] + ul[1] * fz._ANGLE_LIMB_LEN_FRAC * _EV3_LEN_MULT * sidepx),
        "torso": (v[0] + ut[0] * fz._ANGLE_TORSO_LEN_FRAC * _EV3_LEN_MULT * sidepx,
                  v[1] + ut[1] * fz._ANGLE_TORSO_LEN_FRAC * _EV3_LEN_MULT * sidepx),
    }
    kept = []
    for name, end in ends.items():
        seg = _clip_before_disc(v, end, head)
        if seg is None:
            notes.append(f"{panel}: {name} 선 전체 생략 (시작점 원반 안)")
            continue
        if seg[1] != end:
            notes.append(f"{panel}: {name} 선 원반 진입 전 클리핑")
        kept.append(seg)
    if len(kept) < 2:
        notes.append(f"{panel}: V 2가닥 미성립 — 미방출")
        return False
    _draw_strands(img, v, kept)
    r_arc = fz._ANGLE_ARC_R_FRAC * _EV3_LEN_MULT * sidepx
    a1, a2 = fz._minor_arc_span_deg(v, ends["limb"], ends["torso"])
    _arc_outside_disc(ImageDraw.Draw(img), v, r_arc, a1, a2, head)
    return True


class _EVPatch(_R3Patch):
    """팔꿈치 얼굴회피 V 변형안 — 좌표 출처·원반 규칙 공통, 차이 = 선 길이·도달점."""

    def __init__(self, mode: str, poles: dict):
        super().__init__(mode, "left_elbow", poles)

    def _reach_px(self, panel: str, frame, box):
        """EV1/EV2 실측 도달점 — 같은 align 게이트 순간의 wrist/shoulder px."""
        al_rep = self._rep17.get(panel)
        if al_rep is None:
            return None
        idx = self._gate_idx(panel, al_rep)
        h, w = frame.shape[0], frame.shape[1]
        left, top, side = box
        pts = []
        for name in ("left_wrist", "left_shoulder"):
            p = cg.kp(al_rep, idx, name, conf_min=fz._KP_CONF_MIN)
            if p is None:
                self.notes.append(
                    f"{panel}: {name}@al17 conf 게이트({fz._KP_CONF_MIN}) 미달")
                return None
            pts.append(fz._to_crop_px_unclamped(p, left, top, side, w, h))
        return pts[0], pts[1]

    def _side(self, img, frame, spec, box):
        if self.joint not in self.cur_joints:
            return self._orig_side(img, frame, spec, box)
        i = self.draw_i
        self.draw_i += 1
        panel = "user" if i == 0 else "ref"
        got = self._repaired_pts(panel, frame, spec, box)
        if got is None:
            return False
        v, l, t = got
        head = self._head_disc_align(panel, frame, box)
        if head is None:
            # 얼굴회피가 이 라운드의 스펙 — 원반 추정 실패 시 관통 무보증이라 미방출
            self.notes.append(f"{panel}: 머리 원반 추정 실패 — 미방출 (fail-closed)")
            return False
        self.notes.append(
            f"{panel}: head c=({head[0][0]:.0f},{head[0][1]:.0f}) r={head[1]:.0f}")
        if self.mode == "EV1":
            reach = self._reach_px(panel, frame, box)
            if reach is None:
                return False
            wrist, shoulder = reach
            self.notes.append(
                f"{panel}: 도달점 wrist=({wrist[0]:.0f},{wrist[1]:.0f}) "
                f"shoulder=({shoulder[0]:.0f},{shoulder[1]:.0f})")
            return _draw_ev1(img, v, wrist, shoulder, head, self.notes, panel)
        if self.mode == "EV2":
            reach = self._reach_px(panel, frame, box)
            if reach is None:
                return False
            wrist, shoulder = reach
            fore = math.hypot(wrist[0] - v[0], wrist[1] - v[1])
            upper = math.hypot(shoulder[0] - v[0], shoulder[1] - v[1])
            self.notes.append(
                f"{panel}: 실측 전완 {fore:.0f}px 상완 {upper:.0f}px "
                f"(스텁 = x{_EV2_REACH_FRAC})")
            return _draw_ev2(img, v, l, t, fore, upper, head, self.notes, panel)
        if self.mode == "EV3":
            return _draw_ev3(img, v, l, t, head, self.notes, panel)
        return False


# ── 러너 ─────────────────────────────────────────────────────────────────────
def candidates3() -> int:
    gr._guard_ev()
    gr._require_cache()
    gate_p = rr.BASE / "gate.json"
    if not gate_p.exists():
        print("baseline 게이트 미실행 — --baseline 선행")
        return 1
    gate = json.loads(gate_p.read_text())
    if not gate.get("pass"):
        print("baseline 게이트 FAIL 박제 상태 — 후보 렌더 진입 금지 (bz5 규율)")
        return 1
    ref_deg = ((gate.get("recordedAngles") or {}).get("left_hip") or {}).get("refDeg")
    poles: dict = {}
    for pside in ("user", "ref"):
        p = vl.RENDER_WORK / f"pole_{pside}.json"
        poles[pside] = (
            json.loads(p.read_text()).get("xNorm") if p.exists() else None
        )

    fails: list[str] = []
    summary: dict = {}
    for mode, joint in MODES3.items():
        print(f"── candidate {mode} ({joint}) ──")
        if mode == "P3r1":
            patch: _R3Patch = _P3R1Patch(poles, ref_deg)
        else:
            patch = _EVPatch(mode, poles)
        patch.install()
        try:
            out = vl.run()
        finally:
            patch.restore()
        mdir = CAND3 / mode
        mdir.mkdir(parents=True, exist_ok=True)
        src = vl.EV / "cards" / rr.CARD_NAME[joint]
        if not src.exists():
            print(f"  FAIL: {rr.CARD_NAME[joint]} 미방출")
            fails.append(mode)
            summary[mode] = {"joint": joint, "emitted": False,
                             "notes": patch.notes}
            continue
        shutil.copy2(src, mdir / rr.CARD_NAME[joint])
        other = next(j for j in rr.CARD_NAME if j != joint)
        leak_ok = (out["pngMd5"].get(rr.CARD_NAME[other])
                   == rr.CERT_MD5[rr.CARD_NAME[other]])
        surv_ok = list(out["verdict"]["survivors"]) == rr.CERT_SURVIVORS
        changed = (out["pngMd5"].get(rr.CARD_NAME[joint])
                   != rr.CERT_MD5[rr.CARD_NAME[joint]])
        summary[mode] = {
            "joint": joint, "emitted": True,
            "leakFreeOtherCard": leak_ok, "survivorsOk": surv_ok,
            "targetChanged": changed, "notes": patch.notes,
            "targetMd5": out["pngMd5"].get(rr.CARD_NAME[joint]),
        }
        print(f"  leak-free={leak_ok} survivors={surv_ok} changed={changed}")
        for n in patch.notes:
            print(f"  note: {n}")
        if not (leak_ok and surv_ok and changed):
            fails.append(mode)
    CAND3.mkdir(parents=True, exist_ok=True)
    summary["_meta"] = {
        "eyeStubCalls": gr._EYE_STUB["calls"],
        "vertexSource": "refine_round._R2Patch._gate_moment_px "
                        "(align17 @ round(freeze_sec x align_fps), "
                        f"conf>={fz._KP_CONF_MIN}, fail-closed)",
    }
    (CAND3 / "render_summary_round3.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"eye stub calls (이 프로세스 누적): {gr._EYE_STUB['calls']} — "
          "machine_eye 스텁, Gemini 실호출 0")
    if fails:
        print(f"CANDIDATES-R3 FAIL: {fails}")
        return 1
    print(f"CANDIDATES-R3 PASS ({len(MODES3)}/{len(MODES3)} 방출 + "
          "비대상 카드 무누출 + survivors 불변)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--candidates", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    rc = 0
    if args.baseline:
        rc = gr.baseline()
    if args.candidates and rc == 0:
        rc = candidates3()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
