#!/usr/bin/env python3
"""마크 문법 후보 라운드 하네스 (quick-260811-xa1) — ufb 드라이버 랩.

belle 반려 2카드(왼골반 freeze 16.7s "마크 반려" · 왼팔꿈치 freeze 5.3s "부위
특정 불가")의 표시 문법 후보를 **같은 freeze 순간에서** 산출한다. 경로 재발명
없이 ufb `verify_local.run()` 을 그대로 감싼다 (LD-1 — 운영 코드 무접촉,
드로잉 교체는 이 프로세스 안 monkeypatch 만, bz5 방식).

stages:
  --baseline    무패치 렌더 → md5 == ufb 인증값 2/2 + survivors 일치 게이트.
                동시에 `_draw_joint_angle` record 래퍼로 각 카드 user/ref 패널
                사이각을 1회 확보 (bz5 `_inner_deg` 재사용). 불일치 = 박제 후
                정지 (후보 렌더 진입 금지 — bz5 규율).
  --candidates  후보 6안 (left_hip P1~P3 / left_elbow E1~E3) — 후보별로 대상
                관절 카드의 드로잉만 교체하고 vl.run() 1회, 비대상 카드 md5 가
                인증값과 동일함(무누출)을 함께 판정.

Gemini 0회 (T-xa1-01): env 더미 키 + `card_gates.machine_eye` 스텁 (ufb
--zero-card 의 hold_gate 스텁과 같은 계열 — 관찰 실험 패치). ufb evidence 는
EV 리다이렉트 선행으로 무접촉 (T-xa1-02).
프로덕션 코드 아님 — quick 디렉터리 로컬 하네스. 채점 무접촉.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import math
import os
import pathlib
import shutil
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_UFB = _HERE.parent / "260811-ufb-freeze-only"
_BZ5 = _HERE.parent / "260811-bz5-mark-grammar"
_REPO = _HERE.parents[2]
_VENV_PY = _REPO / "backend" / ".venv" / "bin" / "python"


def _ensure_interpreter() -> None:
    """시스템 python3 에 numpy/imageio 가 없으면 backend venv 로 재실행.

    플랜 verify 커맨드가 `python3 grammar_round.py` 그대로이므로 하네스가
    스스로 의존성 있는 인터프리터를 잡는다 (Rule 3 — 신규 설치 0, T-xa1-SC).
    """
    try:
        import imageio  # noqa: F401
        import numpy  # noqa: F401
        import PIL  # noqa: F401
    except ModuleNotFoundError:
        # venv python 은 시스템 바이너리 심링크라 경로 비교로는 못 가른다 —
        # env 마커로 재실행 루프만 방지 (재실행 후에도 실패면 그대로 raise).
        if _VENV_PY.exists() and os.environ.get("_XA1_REEXEC") != "1":
            os.environ["_XA1_REEXEC"] = "1"
            os.execv(str(_VENV_PY), [str(_VENV_PY), *sys.argv])
        raise


_ensure_interpreter()

# Gemini 0회 (T-xa1-01) — vl._ensure_gemini_key 의 SSM 조회를 선차단.
# 실키가 이미 env 에 있어도 machine_eye 스텁이 네트워크를 막는다 (아래).
os.environ.setdefault("GEMINI_API_KEY", "xa1-stub")


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# verify_local 이 import 시점에 backend sys.path 를 넣어준다 (재사용 원천 ①).
vl = _load_module("verify_local", _UFB / "verify_local.py")
# bz5 하네스 = 재사용 원천 ② (_inner_deg/_rotate/_unit_vec/_dashed_line/
# _draw_candidate — 중복 발명 금지, LD-7). import 부작용 = 상수 정의뿐.
bz = _load_module("bz5_render_harness", _BZ5 / "render_harness.py")

from PIL import Image, ImageDraw  # noqa: E402
from sunity_shared.analysis import card_gates as cg  # noqa: E402
from sunity_shared.analysis import compare_align  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

OUT = _HERE / "out"
BASE = OUT / "baseline"
CAND = OUT / "candidates"

# ── EV 리다이렉트 (T-xa1-02) — run() 은 EV 하위 cards/·eye_ledger/ 를 비우므로
# 리다이렉트 없이는 ufb 반려 증거 정본이 파괴된다. 선행 + 가드.
vl.EV = OUT / "_ev"

log = logging.getLogger("grammar_round")

# ── ufb 인증 정본 (evidence/run_verdict.json pngMd5 / survivors — LD-2) ──────
CERT_MD5 = {
    "zoom_angle_vs_reference__left_elbow.png": "9891d2811eb9dcb7925bcf229831f19b",
    "zoom_angle_vs_reference__left_hip.png": "8e1472097f8a7c2acf3834dfdaf2c78f",
}
CERT_SURVIVORS = ["r03:inherit@u16.667/r15.20", "r00:inherit@u5.302/r5.13"]

CARD_NAME = {
    "left_hip": "zoom_angle_vs_reference__left_hip.png",
    "left_elbow": "zoom_angle_vs_reference__left_elbow.png",
}
MODES = {
    "P1": "left_hip", "P2": "left_hip", "P3": "left_hip",
    "E1": "left_elbow", "E2": "left_elbow", "E3": "left_elbow",
}
# freeze 실초 (evidence/run_verdict.json freezes — LD-2, 순간 변경 금지).
# 머리 원반 추정의 align 트랙 인덱스 산출에만 쓴다 (app 게이트 인덱스 공식 미러).
FREEZE_SEC = {
    "left_hip": {"user": 16.666666666666668, "ref": 15.2},
    "left_elbow": {"user": 5.301767255751917, "ref": 5.13},
}

_EYE_STUB = {"calls": 0}


def _stub_machine_eye(frame_rgb, joint_xy_px, claim, *, api_key=None,
                      expected_limb=None, crop_px=360, **_kw):
    """드라이버 프로세스 한정 스텁 — Gemini 실호출 0 (T-xa1-01).

    ufb 인증 run 에서 두 survivor 모두 실 눈 PASS 였으므로 match=True 고정이
    verdict 를 바꾸지 않는다 (dropped 3건은 hold/pair 단계 탈락 — 눈 무관).
    app.py 가 res["crop"].save 를 부르므로 PIL crop 필수 — cg.mark_crop 재사용
    (네트워크 0). 스텁 산출물은 눈 원장이 아니다 (JUDGMENT 명기).
    """
    _EYE_STUB["calls"] += 1
    crop, _ = cg.mark_crop(frame_rgb, joint_xy_px, crop_px=crop_px)
    return {
        "observed": claim, "limb": expected_limb, "match": True,
        "confidence": 1.0, "reason": "xa1-stub (ufb 인증 verdict 재사용)",
        "crop": crop,
    }


cg.machine_eye = _stub_machine_eye


def _guard_ev() -> None:
    """호출 전 필수 가드 (T-xa1-02) — EV 가 xa1 밖이면 즉시 중단."""
    assert "260811-xa1" in str(vl.EV), (
        f"EV 리다이렉트 실패: {vl.EV} — ufb evidence 파괴 위험, 실행 금지"
    )


def _require_cache() -> None:
    need = [vl.DOC, vl.REFMOTION, vl.VIDEOS["user"], vl.VIDEOS["ref"]]
    missing = [str(p) for p in need if not p.exists()]
    if missing:
        print("캐시 부재 — 세션 scratchpad fresh/ 가 죽어 있음:")
        for m in missing:
            print(f"  {m}")
        print("복구: AWS_PROFILE=sunity-motion python3 "
              f"{_UFB / 'verify_local.py'} --fetch")
        raise SystemExit(1)


# ── baseline record 패스 (2-pass 패치의 pass1 — bz5 _GrammarPatch 패턴) ──────
class _Recorder:
    """원본 위임 + 호출별 vertex/limb/torso 사이각 기록 (bz5 `_inner_deg` 재사용).

    렌더 호출 순서는 결정론 (ufb 2회 md5 동일 증명) — 카드당 user → ref 순서로
    `_draw_joint_angle` 이 정확히 2회 (fault_zoom.py 3205-3208, ref 는 user 성공
    시에만). 어느 build 호출이 어느 관절인지는 `build_fault_zoom_comparisons`
    랩이 joints 인자(위치 5)를 함께 기록한다.
    """

    def __init__(self):
        self.builds: list[dict] = []
        self._orig_build = fz.build_fault_zoom_comparisons
        self._orig_draw = fz._draw_joint_angle

    def install(self):
        fz.build_fault_zoom_comparisons = self._build
        fz._draw_joint_angle = self._draw

    def restore(self):
        fz.build_fault_zoom_comparisons = self._orig_build
        fz._draw_joint_angle = self._orig_draw

    def _build(self, *a, **k):
        joints = list(a[5]) if len(a) > 5 else list(k.get("fault_joints") or [])
        self.builds.append({"joints": joints, "angles": [], "pts": []})
        return self._orig_build(*a, **k)

    def _draw(self, img, vertex, limb, torso):
        deg = bz._inner_deg(vertex, limb, torso)
        if self.builds:
            self.builds[-1]["angles"].append(deg)
            self.builds[-1]["pts"].append([
                [float(vertex[0]), float(vertex[1])],
                [float(limb[0]), float(limb[1])],
                [float(torso[0]), float(torso[1])],
            ])
        return self._orig_draw(img, vertex, limb, torso)

    def by_joint(self) -> dict:
        out: dict = {}
        for b in self.builds:
            for j in b["joints"]:
                if j in CARD_NAME and len(b["angles"]) >= 2:
                    out[j] = {
                        "userDeg": b["angles"][0], "refDeg": b["angles"][1],
                        "pts": b["pts"],
                    }
        return out


def baseline() -> int:
    _guard_ev()
    _require_cache()
    BASE.mkdir(parents=True, exist_ok=True)
    rec = _Recorder()
    rec.install()
    try:
        out = vl.run()
    finally:
        rec.restore()

    fails: list[str] = []
    md5s = out.get("pngMd5") or {}
    for name, want in CERT_MD5.items():
        got = md5s.get(name)
        ok = got == want
        print(f"md5 {name}: {got} {'==' if ok else '!='} {want} "
              f"{'PASS' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"md5:{name}")
    survivors = list(out["verdict"]["survivors"])
    if survivors == CERT_SURVIVORS:
        print(f"survivors PASS: {survivors} (LD-2 순간 무변경 기계 증명)")
    else:
        print(f"survivors FAIL: {survivors} != {CERT_SURVIVORS}")
        fails.append("survivors")

    for name in CERT_MD5:
        src = vl.EV / "cards" / name
        if src.exists():
            shutil.copy2(src, BASE / name)

    angles = rec.by_joint()
    for j in CARD_NAME:
        a = angles.get(j)
        if a is None or a.get("refDeg") is None:
            fails.append(f"record:{j}")
            print(f"record FAIL: {j} 각도 시퀀스 미확보")
        else:
            print(f"record {j}: user={a['userDeg']:.1f}도 ref={a['refDeg']:.1f}도")

    gate = {
        "md5": {n: md5s.get(n) for n in CERT_MD5},
        "certMd5": CERT_MD5,
        "survivors": survivors,
        "certSurvivors": CERT_SURVIVORS,
        "recordedAngles": angles,
        "eyeStubCalls": _EYE_STUB["calls"],
        "pass": not fails,
        "fails": fails,
    }
    (BASE / "gate.json").write_text(json.dumps(gate, ensure_ascii=False, indent=1))
    print(f"eye stub calls: {_EYE_STUB['calls']} (machine_eye 스텁 — Gemini 실호출 0)")
    if fails:
        print(f"BASELINE GATE FAIL {fails} — 후보 렌더 진입 금지 (gate.json 박제)")
        return 1
    print("BASELINE GATE PASS (md5 2/2 + survivors 일치 — 반려 실물과 동일 경로)")
    return 0


# ── 기하 헬퍼 (후보 공통) ────────────────────────────────────────────────────
def _vertex_ring(draw, v, r: float = 11.0) -> None:
    """소형 vertex 링 — mark_crop 링과 같은 흰 halo + 브랜드 코어 계열."""
    for w_, color in ((5, fz._HALO), (3, fz._BRAND)):
        draw.ellipse([v[0] - r, v[1] - r, v[0] + r, v[1] + r],
                     outline=color, width=w_)


def _head_disc(meta, frame, box):
    """머리 원반 추정 — 플랜 휴리스틱 ② 채택 (어깨 중점에서 골반 반대 방향 연장).

    12관절 리포트에 머리 kp 가 없다. 드로잉 스펙과 **같은 report·같은 프레임**
    (좌표 단일 출처)의 어깨/골반으로: center = 어깨중점 + (어깨중점-골반중점)*0.45,
    radius = 몸통길이*0.36. 역립이면 축이 아래를 향하므로 중력 방향(머리카락)과
    자동 정합. 빗나가면 Task 2 육안에서 잡혀 재렌더한다 (플랜 명기).
    """
    if meta is None:
        return None
    report, idx = meta
    h, w = frame.shape[0], frame.shape[1]
    left, top, side = box
    pts = {}
    for name in ("left_shoulder", "right_shoulder", "left_hip", "right_hip"):
        p = fz._gated_kp(report, idx, name)
        if p is None:
            return None
        pts[name] = fz._to_crop_px_unclamped(p, left, top, side, w, h)
    sm = ((pts["left_shoulder"][0] + pts["right_shoulder"][0]) / 2.0,
          (pts["left_shoulder"][1] + pts["right_shoulder"][1]) / 2.0)
    hm = ((pts["left_hip"][0] + pts["right_hip"][0]) / 2.0,
          (pts["left_hip"][1] + pts["right_hip"][1]) / 2.0)
    ax = (sm[0] - hm[0], sm[1] - hm[1])
    n = math.hypot(*ax)
    if n < 1e-6:
        return None
    c = (sm[0] + ax[0] * 0.45, sm[1] + ax[1] * 0.45)
    return c, 0.36 * n


def _split_by_disc(a, b, head, margin: float = 8.0):
    """선분 a→b 를 머리 원반 회피 구간으로 분할 (비관통 공통 규칙)."""
    if head is None:
        return [(a, b)]
    (cx, cy), r = head
    rr = r + margin
    dx, dy = b[0] - a[0], b[1] - a[1]
    A = dx * dx + dy * dy
    if A < 1e-9:
        return [(a, b)]
    fx, fy = a[0] - cx, a[1] - cy
    B = 2 * (fx * dx + fy * dy)
    C = fx * fx + fy * fy - rr * rr
    disc = B * B - 4 * A * C
    if disc <= 0:
        return [(a, b)]
    sq = math.sqrt(disc)
    t1, t2 = (-B - sq) / (2 * A), (-B + sq) / (2 * A)
    if t2 <= 0 or t1 >= 1:
        return [(a, b)]

    def _pt(t):
        return (a[0] + dx * t, a[1] + dy * t)

    segs = []
    if t1 > 0.02:
        segs.append((a, _pt(max(0.0, t1))))
    if t2 < 0.98:
        segs.append((_pt(min(1.0, t2)), b))
    return segs


# ── 후보 드로잉 (근거 1줄은 PLAN LD-3 정본 — JUDGMENT.md 에 그대로) ──────────
def _draw_p1(img, v, l) -> bool:
    """P1 단일선 — 결함 사지 방향 선 1가닥 + vertex 소형 링. 몸통 선·호 제거."""
    ul = bz._unit_vec(v, l)
    if ul is None:
        return False
    sidepx = min(img.size)
    end = (v[0] + ul[0] * fz._ANGLE_LIMB_LEN_FRAC * sidepx,
           v[1] + ul[1] * fz._ANGLE_LIMB_LEN_FRAC * sidepx)
    draw = ImageDraw.Draw(img)
    for w_ in (fz._ANGLE_HALO_W, fz._ANGLE_CORE_W):
        fill = fz._HALO if w_ == fz._ANGLE_HALO_W else fz._BRAND
        draw.line([v, end], fill=fill, width=w_)
    _vertex_ring(draw, v)
    return True


def _draw_p2_user(img, v, l, t, ref_deg) -> bool:
    """P2 단일선 + 쐐기 — P1 + 기준각 이식 쐐기 + 교정 방향 화살촉.

    쐐기·카이럴리티·화살촉은 bz5 `_draw_candidate` 로직 재사용 (기준각 =
    record 패스 기록값, 학생 몸통 축 + 학생 회전 방향에 각도만 이식).
    """
    if ref_deg is None or not math.isfinite(ref_deg):
        return _draw_p1(img, v, l)
    ul, ut = bz._unit_vec(v, l), bz._unit_vec(v, t)
    if ul is None or ut is None:
        return False
    sidepx = min(img.size)
    cross = ut[0] * ul[1] - ut[1] * ul[0]
    sgn = 1.0 if cross >= 0 else -1.0
    ghost = bz._rotate(ut, sgn * math.radians(ref_deg))
    r = bz._WEDGE_R_FRAC * sidepx
    a_limb = math.degrees(math.atan2(ul[1], ul[0]))
    a_ghost = math.degrees(math.atan2(ghost[1], ghost[0]))
    d = (a_ghost - a_limb) % 360
    start, end_a = (a_limb, a_limb + d) if d <= 180 else (a_ghost, a_ghost + (360 - d))
    base = img.convert("RGBA")
    ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).pieslice(
        [v[0] - r, v[1] - r, v[0] + r, v[1] + r],
        start=start, end=end_a, fill=(*fz._BRAND, bz._WEDGE_ALPHA),
    )
    img.paste(Image.alpha_composite(base, ov).convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(img)
    end = (v[0] + ul[0] * fz._ANGLE_LIMB_LEN_FRAC * sidepx,
           v[1] + ul[1] * fz._ANGLE_LIMB_LEN_FRAC * sidepx)
    for w_ in (fz._ANGLE_HALO_W, fz._ANGLE_CORE_W):
        fill = fz._HALO if w_ == fz._ANGLE_HALO_W else fz._BRAND
        draw.line([v, end], fill=fill, width=w_)
    # 화살촉 — 쐐기 호의 고스트 쪽 끝, 사지→고스트 진행 방향 (bz5 재사용)
    ah = bz._ARROW_HEAD_PX
    a1r = math.radians(a_ghost)
    tip = (v[0] + math.cos(a1r) * r, v[1] + math.sin(a1r) * r)
    step = 1.0 if (a_ghost - a_limb) % 360 <= 180 else -1.0
    tang = (-math.sin(a1r) * step, math.cos(a1r) * step)
    nrm = (math.cos(a1r), math.sin(a1r))
    p1 = (tip[0] - tang[0] * ah + nrm[0] * ah * 0.6,
          tip[1] - tang[1] * ah + nrm[1] * ah * 0.6)
    p2 = (tip[0] - tang[0] * ah - nrm[0] * ah * 0.6,
          tip[1] - tang[1] * ah - nrm[1] * ah * 0.6)
    draw.polygon([tip, p1, p2], fill=fz._BRAND, outline=fz._HALO)
    _vertex_ring(draw, v)
    return True


def _draw_e1(img, v, l, t, head, notes, panel) -> bool:
    """E1 짧은 선 — 현행 2가닥 유지 + 머리 원반 경계 클리핑 (진입 전 중단)."""
    ul, ut = bz._unit_vec(v, l), bz._unit_vec(v, t)
    if ul is None or ut is None:
        return False
    sidepx = min(img.size)
    ends = {
        "limb": (v[0] + ul[0] * fz._ANGLE_LIMB_LEN_FRAC * sidepx,
                 v[1] + ul[1] * fz._ANGLE_LIMB_LEN_FRAC * sidepx),
        "torso": (v[0] + ut[0] * fz._ANGLE_TORSO_LEN_FRAC * sidepx,
                  v[1] + ut[1] * fz._ANGLE_TORSO_LEN_FRAC * sidepx),
    }
    draw = ImageDraw.Draw(img)
    kept: dict = {}
    for name, end in ends.items():
        segs = _split_by_disc(v, end, head)
        # vertex 쪽 구간만 채택 — 원반 뒤 재개는 관통으로 읽힌다 (진입 전 중단)
        seg = segs[0] if segs and segs[0][0] == v else None
        if seg is None:
            notes.append(f"{panel}:{name} 선 전체 생략 (시작점이 머리 원반 안)")
            continue
        if seg[1] != end:
            notes.append(f"{panel}:{name} 선 클리핑")
        kept[name] = seg
    for w_ in (fz._ANGLE_HALO_W, fz._ANGLE_CORE_W):
        fill = fz._HALO if w_ == fz._ANGLE_HALO_W else fz._BRAND
        for seg in kept.values():
            draw.line([seg[0], seg[1]], fill=fill, width=w_)
    r_arc = fz._ANGLE_ARC_R_FRAC * sidepx
    clear = head is None or (
        math.hypot(v[0] - head[0][0], v[1] - head[0][1]) > head[1] + r_arc + 8
    )
    if clear and len(kept) == 2:
        a1, a2 = fz._minor_arc_span_deg(v, ends["limb"], ends["torso"])
        draw.arc([v[0] - r_arc, v[1] - r_arc, v[0] + r_arc, v[1] + r_arc],
                 start=a1, end=a2, fill=fz._HALO, width=3)
    elif not clear:
        notes.append(f"{panel}: 호 생략 (머리 원반 근접)")
    return True


def _draw_e2(img, v, head, pole_xnorm, frame, box, notes, panel) -> bool:
    """E2 폴 간격 브래킷 — vertex 링 + 팔꿈치→폴 축선 간격 브래킷 (머리 우회).

    폴 x = 운영 pole 캐시 (render/pole_user.json xNorm) 재사용. P35 기결론
    "엘보 = 폴 근접도" 이식 — 이 부위 설명 문법은 각도가 아니라 폴 이탈.
    """
    if pole_xnorm is None:
        notes.append(f"{panel}: pole 캐시 없음 — E2 미성립")
        return False
    h, w = frame.shape[0], frame.shape[1]
    left, top, side = box
    px = fz._to_crop_px_unclamped((float(pole_xnorm), 0.5), left, top, side, w, h)[0]
    Wp, Hp = img.size
    if px < 4 or px > Wp - 4:
        px = min(max(px, 6.0), Wp - 6.0)
        notes.append(f"{panel}: 폴 축선 패널 밖 — 경계 클램프")
    draw = ImageDraw.Draw(img)
    # 폴 축선 (세로 점선) — 머리 원반 구간은 건너뛴다 (비관통 공통 규칙)
    for y0, y1 in _split_by_disc((px, 0.0), (px, float(Hp)), head):
        if abs(y1[1] - y0[1]) < 4:
            continue
        bz._dashed_line(draw, y0, y1, fz._HALO, 7)
        bz._dashed_line(draw, y0, y1, fz._BRAND, 3)
    # 브래킷 y 선정 — vertex y 에서 시작해 머리 원반을 피하는 첫 오프셋
    y_b = None
    for dy in (0, -24, 24, -48, 48, -72, 72, -96, 96, -120, 120):
        y = v[1] + dy
        if not (10 <= y <= Hp - 10):
            continue
        x0, x1 = sorted((float(v[0]), px))
        segs = _split_by_disc((x0, y), (x1, y), head)
        if len(segs) == 1 and segs[0] == ((x0, y), (x1, y)):
            y_b = y
            break
    if y_b is None:
        y_b = float(v[1])
        notes.append(f"{panel}: 브래킷 회피 실패 — vertex y 사용")
    x0, x1 = sorted((float(v[0]), px))
    for w_, fill in ((7, fz._HALO), (3, fz._BRAND)):
        draw.line([(x0, y_b), (x1, y_b)], fill=fill, width=w_)
        for xe in (x0, x1):
            draw.line([(xe, y_b - 9), (xe, y_b + 9)], fill=fill, width=w_)
    if abs(y_b - v[1]) > 6:
        # 연결자 (vertex → 브래킷) — 가는 점선, 머리 원반 회피 분할
        for a, b in _split_by_disc((float(v[0]), float(v[1])),
                                   (float(v[0]), y_b), head):
            bz._dashed_line(draw, a, b, fz._HALO, 5, dash=6)
            bz._dashed_line(draw, a, b, fz._BRAND, 2, dash=6)
    _vertex_ring(draw, v)
    return True


def _draw_e3(img, v, head, notes, panel) -> bool:
    """E3 스포트라이트 — 팔꿈치 중심 원 밖 감광 + vertex 링, 선 0가닥."""
    Wp, Hp = img.size
    r_spot = 0.30 * min(Wp, Hp)
    mask = Image.new("L", img.size, 120)
    ImageDraw.Draw(mask).ellipse(
        [v[0] - r_spot, v[1] - r_spot, v[0] + r_spot, v[1] + r_spot], fill=0)
    shade = Image.new("RGB", img.size, (12, 12, 16))
    img.paste(shade, (0, 0), mask)
    _vertex_ring(ImageDraw.Draw(img), v)
    if head is not None and (
        math.hypot(v[0] - head[0][0], v[1] - head[0][1]) < head[1] + 11
    ):
        notes.append(f"{panel}: vertex 링이 머리 원반 추정과 근접 — 육안 판정 필요")
    return True


# ── candidate 패스 (2-pass 패치의 pass2 — 대상 카드만 교체) ──────────────────
class _CandidatePatch:
    """대상 관절 카드의 드로잉만 교체, 비대상 카드는 원본 유지 (bz5 candidate 패턴).

    · `build_fault_zoom_comparisons` 랩 — 현재 build 의 joints + 카드별 카운터 리셋.
    · `build_angle_bake_spec` 랩 — 대상 카드의 (report, frame_idx) 캡처 (머리
      원반 추정이 드로잉과 같은 report·프레임을 쓰기 위해 — 좌표 단일 출처).
      호출 순서 = crop-frac 사이트(user, ref) → 베이크 사이트(user, ref), 전부
      드로잉보다 앞 (fault_zoom.py 3024/3184) — report id 로 dedupe 하면
      [user, ref] 2엔트리가 결정론으로 남는다.
    · `_draw_side_joint_angle` 랩 — 카드당 user(0) → ref(1) 순 호출
      (fault_zoom.py 3205-3208). frame/box 를 받아 crop 픽셀 변환은 원본
      `_draw_joint_angle` 경로와 같은 공식(_to_crop_px/_to_crop_px_unclamped).
    """

    def __init__(self, mode: str, joint: str, ref_deg, poles: dict):
        self.mode = mode
        self.joint = joint
        self.ref_deg = ref_deg
        self.poles = poles
        self.cur_joints: tuple = ()
        self.metas: dict[int, tuple] = {}
        self.draw_i = 0
        self.notes: list[str] = []
        self.align = None
        self._rep17: dict = {}
        self._orig_build = fz.build_fault_zoom_comparisons
        self._orig_spec = fz.build_angle_bake_spec
        self._orig_side = fz._draw_side_joint_angle
        self._orig_align = compare_align.build_align

    def install(self):
        fz.build_fault_zoom_comparisons = self._build
        fz.build_angle_bake_spec = self._spec
        fz._draw_side_joint_angle = self._side
        compare_align.build_align = self._build_align

    def restore(self):
        fz.build_fault_zoom_comparisons = self._orig_build
        fz.build_angle_bake_spec = self._orig_spec
        fz._draw_side_joint_angle = self._orig_side
        compare_align.build_align = self._orig_align

    def _build_align(self, *a, **k):
        out = self._orig_align(*a, **k)
        self.align = out
        return out

    def _head_disc_align(self, panel: str, frame, box):
        """머리 원반 — 플랜 옵션 ① (align 17-kp 트랙의 nose/eyes/ears 투영).

        12관절 리포트는 머리 kp 가 없고 역립 freeze 프레임에서 어깨/골반 conf
        게이트도 탈락한다 (E1 1차 실측) — RTMW17 트랙이 유일한 실측 머리 좌표.
        인덱스 = round(freeze 실초 × align fps) (app 게이트 인덱스 공식 미러).
        반지름 = max(머리 kp 산포 2.0배, 어깨폭 0.48배, 26px) — 머리카락 여유.
        """
        if self.align is None:
            return None
        rep = self._rep17.get(panel)
        if rep is None:
            try:
                rep = cg.align_to_report(self.align, panel)
            except Exception:  # noqa: BLE001 - refKp 부재 등 → 휴리스틱 폴백
                return None
            self._rep17[panel] = rep
        sec = FREEZE_SEC[self.joint][panel]
        idx = max(0, min(int(round(sec * float(rep["fps"]))),
                         int(rep["frames"]) - 1))
        h, w = frame.shape[0], frame.shape[1]
        left, top, side = box

        def _cp(p):
            return fz._to_crop_px_unclamped(p, left, top, side, w, h)

        head_pts = []
        for name in ("nose", "left_eye", "right_eye", "left_ear", "right_ear"):
            p = cg.kp(rep, idx, name, conf_min=0.35)
            if p is not None:
                head_pts.append(_cp(p))
        if not head_pts:
            return None
        cx = sum(p[0] for p in head_pts) / len(head_pts)
        cy = sum(p[1] for p in head_pts) / len(head_pts)
        r0 = max((math.hypot(p[0] - cx, p[1] - cy) for p in head_pts),
                 default=0.0)
        sw = 0.0
        ls = cg.kp(rep, idx, "left_shoulder", conf_min=0.35)
        rs = cg.kp(rep, idx, "right_shoulder", conf_min=0.35)
        if ls is not None and rs is not None:
            a, b = _cp(ls), _cp(rs)
            sw = math.hypot(a[0] - b[0], a[1] - b[1])
        return (cx, cy), max(2.0 * r0, 0.48 * sw, 26.0)

    def _build(self, *a, **k):
        self.cur_joints = tuple(a[5]) if len(a) > 5 else tuple(
            k.get("fault_joints") or ())
        self.metas = {}
        self.draw_i = 0
        return self._orig_build(*a, **k)

    def _spec(self, criterion, members, report, frame_idx, resolver=None):
        if self.joint in self.cur_joints:
            self.metas.setdefault(id(report), (report, int(frame_idx)))
        return self._orig_spec(criterion, members, report, frame_idx, resolver)

    def _side(self, img, frame, spec, box):
        if self.joint not in self.cur_joints:
            return self._orig_side(img, frame, spec, box)
        i = self.draw_i
        self.draw_i += 1
        panel = "user" if i == 0 else "ref"
        if self.mode == "P3" and panel == "ref":
            # bz5 하이브리드 그대로 — 기준 패널은 원본 문법 (bz5 판정 페이지와
            # 직접 대조 가능하도록, LD-7)
            return self._orig_side(img, frame, spec, box)
        h, w = frame.shape[0], frame.shape[1]
        left, top, side = box
        v = fz._to_crop_px(spec[0], left, top, side, w, h)
        l = fz._to_crop_px_unclamped(spec[1], left, top, side, w, h)
        t = fz._to_crop_px_unclamped(spec[2], left, top, side, w, h)
        if self.mode == "P1":
            return _draw_p1(img, v, l)
        if self.mode == "P2":
            # 쐐기(기준각 이식)는 학생 패널의 몫 — 기준 패널은 단일선 짝 유지
            if panel == "user":
                return _draw_p2_user(img, v, l, t, self.ref_deg)
            return _draw_p1(img, v, l)
        if self.mode == "P3":
            if self.ref_deg is None or not math.isfinite(float(self.ref_deg)):
                return self._orig_side(img, frame, spec, box)
            return bz._draw_candidate(img, v, l, t, float(self.ref_deg), "hybrid")
        head = self._head_disc_align(panel, frame, box)
        if head is None:
            # 폴백 = 휴리스틱 ② (12관절 어깨/골반 연장) — 둘 다 실패면 None
            metas = list(self.metas.values())
            meta = metas[i] if i < len(metas) else None
            head = _head_disc(meta, frame, box)
        if head is None:
            self.notes.append(f"{panel}: 머리 원반 추정 실패 (양 경로)")
        else:
            self.notes.append(
                f"{panel}: head c=({head[0][0]:.0f},{head[0][1]:.0f}) "
                f"r={head[1]:.0f}"
            )
        if self.mode == "E1":
            return _draw_e1(img, v, l, t, head, self.notes, panel)
        if self.mode == "E2":
            return _draw_e2(img, v, head, self.poles.get(panel), frame, box,
                            self.notes, panel)
        if self.mode == "E3":
            return _draw_e3(img, v, head, self.notes, panel)
        return self._orig_side(img, frame, spec, box)


def candidates() -> int:
    _guard_ev()
    _require_cache()
    gate_p = BASE / "gate.json"
    if not gate_p.exists():
        print("baseline 게이트 미실행 — python3 grammar_round.py --baseline 선행")
        return 1
    gate = json.loads(gate_p.read_text())
    if not gate.get("pass"):
        print("baseline 게이트 FAIL 박제 상태 — 후보 렌더 진입 금지 (bz5 규율)")
        return 1
    angles = gate.get("recordedAngles") or {}
    poles: dict = {}
    for pside in ("user", "ref"):
        p = vl.RENDER_WORK / f"pole_{pside}.json"
        poles[pside] = (
            json.loads(p.read_text()).get("xNorm") if p.exists() else None
        )

    fails: list[str] = []
    summary: dict = {}
    for mode, joint in MODES.items():
        print(f"── candidate {mode} ({joint}) ──")
        ref_deg = (angles.get(joint) or {}).get("refDeg")
        patch = _CandidatePatch(mode, joint, ref_deg, poles)
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
            "joint": joint, "refDeg": ref_deg,
            "leakFreeOtherCard": leak_ok, "survivorsOk": surv_ok,
            "targetChanged": changed, "notes": patch.notes,
            "targetMd5": out["pngMd5"].get(CARD_NAME[joint]),
        }
        print(f"  leak-free={leak_ok} survivors={surv_ok} changed={changed} "
              f"notes={patch.notes}")
        if not (leak_ok and surv_ok and changed):
            fails.append(mode)
    CAND.mkdir(parents=True, exist_ok=True)
    (CAND / "render_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"eye stub calls (이 프로세스 누적): {_EYE_STUB['calls']} — "
          "machine_eye 스텁, Gemini 실호출 0")
    if fails:
        print(f"CANDIDATES FAIL: {fails}")
        return 1
    print("CANDIDATES PASS (6/6 방출 + 비대상 카드 무누출 + survivors 불변)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--candidates", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    rc = 0
    if args.baseline:
        rc = baseline()
    if args.candidates and rc == 0:
        rc = candidates()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
