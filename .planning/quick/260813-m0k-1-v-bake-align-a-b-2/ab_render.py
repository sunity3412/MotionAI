#!/usr/bin/env python3
"""V 베이크 스펙 align 단일 출처 이관 A/B + 반려 짝 후보 스캔 (quick-260813-m0k).

belle 08-13 locked: "어차피 둘 다 해야 하잖아" — V 회복 + 반려 회복 같은 라운드.
이 파일은 판정 재료 생산 전용 — 운영 코드(backend/)·기존 하네스 원본
(sweep_render.py / verify_wiring.py / verify_local.py / grammar_round.py) 전부
무수정. B 변형은 이 프로세스 안 함수 속성 monkeypatch 2 seam 만.

stages:
  --ab      A 런(무패치, vl.sweep 그대로) → zoom md5 == ivs 정본 게이트(불일치
            = BLOCKER 박제 + 비영 종료) → B 런(align 유도 스펙 seam 2개) →
            evidence/ab_verdict.json + ab_cards/{A,B,sheets}.
  --pairs   반려 2건(피디쉐입 왼무릎 u3.667 / 왼팔꿈치 u8.556)의 ref 짝 국면
            후보 스캔 (포즈 거리 랭킹 + 0.5s 분산 + baseline) + 전신 스틸.
  --recommend joint=refSec:노트   육안 대조 후 추천 확정 기록 (후보 값 검증).

B seam (하네스 monkeypatch — 원본 파일 무수정):
  1) fz.build_angle_bake_spec 랩: 원본 None + ANGLE_BAKE_MAP 선언 접미사면
     align 유도 3점 (꼭짓점 = align crit 관절, 사지·몸통 = ANGLE_BAKE_MAP 선언
     관절, ai = clamp(round(freeze_sec × align fps)) — app.py 4733 공식 그대로,
     conf >= 0.5 fail-closed). 한 점이라도 미달 = None 유지(정직한 침묵) +
     관절별 conf 실값 채록. 원본이 스펙을 준 카드는 무개입.
  2) fz._member_pts 랩: valid 0 인 호출에서 같은 freeze ai 의 align 점들
     (conf >= 0.5)로 valid 자리 폴백 — 반환 계약 (valid=[(name,xy)],
     relaxed=[xy]) 실물 확인 완료 (fault_zoom.py 1308-1332). relaxed 자리
     주입 금지 (의미가 다름 — 완화 crop 후보).

명명: card_gates.NAME_ALT 는 wrist→hand(rep12) 방향만 처리한다 — align17
(wrist 명명)에서 ANGLE_BAKE_MAP 의 'hand' 사지점을 조회하려면 같은 NAME_ALT
데이터의 역방향(hand→wrist)으로 정규화해 cg.kp 에 넘긴다 (신규 매핑 발명 0,
_resolve 실물 확인: 'left_hand' 는 align17 에서 미해석 → None).

Gemini 실호출 0 (grammar_round machine_eye 스텁 + 더미 키 상속, T-m0k-03).
채점 무접촉 — survivors/dropped ivs==A==B 3원 동일이 기계 증거.
프로덕션 코드 아님 — quick 로컬 드라이버.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import logging
import math
import pathlib
import re
import shutil
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_XA1 = _HERE.parent / "260811-xa1-mark-grammar-round-ufb-freeze-2-belle"
_IVS_EV = _HERE.parent / "260813-ivs-5" / "evidence"

EVID = _HERE / "evidence"
# 현 세션 scratchpad — ivs 와 같은 세션이라 approved_sweep 캐시 재사용 가능
SCRATCH = pathlib.Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "ae166167-1abf-4754-9fe8-336a719ef9e2/scratchpad"
)


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# grammar_round 로드 — machine_eye 스텁/더미 키/인터프리터 승격/backend sys.path
# 전부 상속 (ivs sweep_render 62-68행 패턴). vl.EV/SPA 는 즉시 재재지정.
gr = _load_module("grammar_round", _XA1 / "grammar_round.py")
vl = gr.vl
vl.EV = EVID
vl.SPA = SCRATCH / "approved_sweep"

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import app  # noqa: E402 - backend/functions/pipeline 운영 모듈 그대로 (무패치)
from sunity_shared.analysis import card_gates as cg  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

log = logging.getLogger("ab_render")

MOTIONS = list(vl.SWEEP_JOBS)
_CONF_MIN = float(fz._KP_CONF_MIN)  # 0.5 — 운영 상수 인용 (신규 임계 0)

# hand→wrist 역정규화 — cg.NAME_ALT 데이터 재사용 (위 docstring 근거)
_HAND2WRIST = {v: k for k, v in cg.NAME_ALT.items()}


def _canon17(name: str) -> str:
    return _HAND2WRIST.get(name, name)


def _guard_ev() -> None:
    """실행 전 필수 가드 (T-m0k-02) — 타 사이클 evidence 파괴 fail-closed."""
    assert "260813-m0k" in str(vl.EV), (
        f"EV 재지정 실패: {vl.EV} — 타 사이클 evidence 파괴 위험, 실행 금지"
    )
    assert str(vl.SPA).startswith(str(SCRATCH)), (
        f"SPA 재지정 실패: {vl.SPA} — 죽은 구세션 scratchpad 부활 금지"
    )


def _preflight() -> list[str]:
    missing: list[str] = []
    for m in MOTIONS:
        for f in ("doc.json", "align.json"):
            p = vl.DATA / m / f
            if not p.exists():
                missing.append(str(p))
    for p in (vl.II0 / "probes.log", vl.II0 / "sweep_out" / "poles.json",
              _IVS_EV / "sweep_verdict.json"):
        if not p.exists():
            missing.append(str(p))
    return missing


# ── 컨텍스트 (동작·criterion·report identity·align 캐시) ─────────────────────
class _Ctx:
    def __init__(self):
        self.motion: str | None = None
        self.crit: str | None = None
        self.reports: dict[str, dict] = {}   # motion -> {"user": obj, "ref": obj}
        self.align: dict[str, dict] = {}     # motion -> {afps, rep15, sizes}
        self.freeze_by_joint: dict[str, dict[str, dict]] = {}
        self.freeze_by_rid: dict[str, dict[str, dict]] = {}


CTX = _Ctx()


def _load_freezes() -> None:
    stops = vl._probe_freezes()  # noqa: SLF001 - ii0 정본 파싱 재사용
    for m, lst in stops.items():
        CTX.freeze_by_joint[m] = {f["joint"]: f for f in lst}
        CTX.freeze_by_rid[m] = {f["rid"]: f for f in lst}


def _ensure_align(m: str) -> dict:
    ax = CTX.align.get(m)
    if ax is not None:
        return ax
    align = json.loads((vl.DATA / m / "align.json").read_text())
    ax = {
        "afps": float(align["fps"]),
        "rep15": {
            "user": cg.align_to_report(align, "user"),
            "ref": cg.align_to_report(align, "ref"),
        },
        "sizes": {
            "user": tuple(align["userSize"]),
            "ref": tuple(align["refSize"]),
        },
    }
    CTX.align[m] = ax
    return ax


def _clamp_ai(sec: float, afps: float, frames: int) -> int:
    return max(0, min(int(round(sec * afps)), frames - 1))


def _conf_of(rep: dict, ai: int, name17: str) -> float | None:
    rn = cg._resolve(rep, name17)  # noqa: SLF001 - 판독 전용
    if rn is None:
        return None
    c = fz._kp_conf(rep, ai, rn)  # noqa: SLF001
    return None if c is None else round(float(c), 3)


def _side_of(report: dict) -> str | None:
    r = CTX.reports.get(CTX.motion or "") or {}
    if report is r.get("user"):
        return "user"
    if report is r.get("ref"):
        return "ref"
    return None


# ── 런별 관찰 저장소 ─────────────────────────────────────────────────────────
RUNS: dict[str, dict] = {}
CUR: dict | None = None


def _switch_run(name: str) -> None:
    global CUR
    RUNS[name] = {
        "bake": {},        # (motion, crit) -> "drawn"|"drawn_hybrid"|"omitted:X"
        "anchors": [],
        "drops": [],       # {motion, rid, joint, side}
        "seams": {},       # (motion, crit, side, seam#) -> event
        "eyeStubCalls": 0,
    }
    CUR = RUNS[name]


_BAKE_RE = re.compile(
    r"fault_zoom_angle_bake analysis_id=sweep-(\S+) criterion=(\S+) angle_bake=(\S+)"
)
_DROP_RE = re.compile(r"display_anchor drop rid=(\S+) joint=(\S+) side=(\S+)")


class _LogTap(logging.Handler):
    """root 로거 캡처 — bake 상태·display_anchor 성립/드랍 (라인 파싱)."""

    def __init__(self):
        super().__init__(level=logging.INFO)

    def emit(self, record):  # noqa: D102
        if CUR is None:
            return
        try:
            msg = record.getMessage()
            mb = _BAKE_RE.match(msg)
            if mb:
                st = mb.group(3)
                CUR["bake"][(mb.group(1), mb.group(2))] = (
                    st.replace("drawn_hybrid", "drawn_hybrid")
                )
                return
            md = _DROP_RE.match(msg)
            if md:
                CUR["drops"].append({
                    "motion": CTX.motion, "rid": md.group(1),
                    "joint": md.group(2), "side": md.group(3),
                })
                return
            if msg.startswith("display_anchor "):
                CUR["anchors"].append({"motion": CTX.motion, "line": msg})
        except Exception:  # noqa: BLE001 - 캡처 실패는 드라이버 문제로만
            pass


class _Observer:
    """운영 함수 관찰 래퍼 — 산출 무변경 (동작/crit/report identity 추적)."""

    def __init__(self):
        self._orig_helper = app._run_gated_card_inherit
        self._orig_build = fz.build_fault_zoom_comparisons

    def install(self):
        app._run_gated_card_inherit = self._helper
        fz.build_fault_zoom_comparisons = self._build

    def restore(self):
        app._run_gated_card_inherit = self._orig_helper
        fz.build_fault_zoom_comparisons = self._orig_build

    def _helper(self, *a, **k):
        aid = str(k.get("analysis_id") or "")
        m = aid[len("sweep-"):] if aid.startswith("sweep-") else aid
        CTX.motion = m
        CTX.reports[m] = {
            "user": k.get("user_report"), "ref": k.get("ref_report"),
        }
        _ensure_align(m)
        return self._orig_helper(*a, **k)

    def _build(self, *a, **k):
        units = k.get("criterion_units") or []
        CTX.crit = str(units[0].get("criterion")) if units else None
        return self._orig_build(*a, **k)


# ── B seam 패치 (드라이버 프로세스 한정 — 원본 파일 무수정) ──────────────────
def _freeze_of_crit(m: str, crit: str | None) -> dict | None:
    if not crit:
        return None
    joint = (crit.split("__")[-1]
             if crit.startswith(fz.ANGLE_VS_REFERENCE_PREFIX) else crit)
    return (CTX.freeze_by_joint.get(m) or {}).get(joint)


def _align_pts(m: str, side: str, names: list[str], sec: float) -> tuple[
    list, dict, int
]:
    """align 유도 좌표 조회 — (pts[각 None 가능], conf 실값, ai)."""
    ax = _ensure_align(m)
    rep = ax["rep15"][side]
    ai = _clamp_ai(sec, ax["afps"], int(rep["frames"]))
    pts, confs = [], {}
    for n in names:
        cn = _canon17(n)
        xy = cg.kp(rep, ai, cn, conf_min=_CONF_MIN)
        confs[n] = {
            "conf": _conf_of(rep, ai, cn),
            "pass": xy is not None,
        }
        pts.append(None if xy is None else (float(xy[0]), float(xy[1])))
    return pts, confs, ai


class _BPatch:
    """seam 2개 — build_angle_bake_spec / _member_pts 함수 속성 교체만."""

    def __init__(self):
        self._orig_bake = fz.build_angle_bake_spec
        self._orig_members = fz._member_pts

    def install(self):
        fz.build_angle_bake_spec = self._bake
        fz._member_pts = self._members

    def restore(self):
        fz.build_angle_bake_spec = self._orig_bake
        fz._member_pts = self._orig_members

    # seam 1 — align 유도 스펙 (원본 None 일 때만, 기존 성립 경로 무개입)
    def _bake(self, criterion, members, report, frame_idx, resolver=None):
        spec = self._orig_bake(criterion, members, report, frame_idx, resolver)
        if spec is not None:
            return spec
        jk = fz._criterion_vertex_joint(criterion, members)  # noqa: SLF001
        if jk is None or "_" not in jk:
            return None
        prefix, suffix = jk.split("_", 1)
        decl = fz.ANGLE_BAKE_MAP.get(suffix)
        if decl is None:
            return None
        m = CTX.motion or "?"
        side = _side_of(report)
        key = (m, str(criterion), side or "?", 1)
        ev = CUR["seams"].get(key) if CUR is not None else None
        if ev is not None:
            ev["calls"] += 1
            return (tuple(ev["pts"][0]), tuple(ev["pts"][1]),
                    tuple(ev["pts"][2])) if ev["outcome"] == "spec" else None
        entry = {"seam": 1, "motion": m, "criterion": str(criterion),
                 "side": side, "calls": 1}
        if side is None:
            entry["outcome"] = "side_unresolved"
            if CUR is not None:
                CUR["seams"][key] = entry
            return None
        frz = _freeze_of_crit(m, str(criterion))
        if frz is None:
            entry["outcome"] = "no_freeze"
            if CUR is not None:
                CUR["seams"][key] = entry
            return None
        sec = frz["userSec"] if side == "user" else frz["refSec"]
        names = [jk, f"{prefix}_{decl[0]}", f"{prefix}_{decl[1]}"]
        pts, confs, ai = _align_pts(m, side, names, sec)
        entry.update({"sec": sec, "ai": ai, "confs": confs})
        if any(p is None for p in pts):
            entry["outcome"] = "conf_gate"  # 정직한 침묵 유지 (환각 좌표 금지)
            if CUR is not None:
                CUR["seams"][key] = entry
            return None
        entry["outcome"] = "spec"
        entry["pts"] = [list(p) for p in pts]
        if CUR is not None:
            CUR["seams"][key] = entry
        return tuple(pts)

    # seam 2 — rep12 valid 0 인 호출에서 align 점 valid 자리 폴백
    def _members(self, report, frame_idx, members):
        valid, relaxed = self._orig_members(report, frame_idx, members)
        if valid:
            return valid, relaxed
        m = CTX.motion or "?"
        side = _side_of(report)
        crit = CTX.crit
        frz = _freeze_of_crit(m, crit)
        key = (m, str(crit), side or "?", 2)
        if side is None or frz is None:
            return valid, relaxed
        ev = CUR["seams"].get(key) if CUR is not None else None
        if ev is not None:
            ev["calls"] += 1
            inj = [(n, tuple(xy)) for n, xy in ev.get("injected") or []]
            return (inj, relaxed) if inj else (valid, relaxed)
        sec = frz["userSec"] if side == "user" else frz["refSec"]
        pts, confs, ai = _align_pts(m, side, list(members), sec)
        inj = [
            (n, p) for n, p in zip(members, pts) if p is not None
        ]
        entry = {"seam": 2, "motion": m, "criterion": str(crit), "side": side,
                 "sec": sec, "ai": ai, "confs": confs, "calls": 1,
                 "injected": [[n, list(p)] for n, p in inj],
                 "outcome": "injected" if inj else "none_pass"}
        if CUR is not None:
            CUR["seams"][key] = entry
        if inj:
            return inj, relaxed  # valid 자리 (relaxed 자리 주입 금지)
        return valid, relaxed


# ── A 런 md5 게이트 + 산출 조립 ──────────────────────────────────────────────
def _zoom_md5(res_m: dict) -> dict[str, str]:
    return {k: v for k, v in (res_m.get("pngMd5") or {}).items()
            if k.startswith("zoom_")}


def _a_gate(res_a: dict, iv: dict) -> list[str]:
    """A(무패치) == ivs 정본 — zoom_*.png md5 + survivors/dropped 전건."""
    bad: list[str] = []
    for m in iv:
        za, zi = _zoom_md5(res_a.get(m) or {}), _zoom_md5(iv[m])
        for k in sorted(set(za) | set(zi)):
            if za.get(k) != zi.get(k):
                bad.append(f"{m}/{k}: A={za.get(k)} ivs={zi.get(k)}")
        for fld in ("survivors", "dropped"):
            if (res_a.get(m) or {}).get("verdict", {}).get(fld) != \
                    iv[m]["verdict"][fld]:
                bad.append(f"{m}/{fld}: A={res_a[m]['verdict'][fld]} "
                           f"ivs={iv[m]['verdict'][fld]}")
    return bad


def _snapshot_cards(run: str) -> None:
    dst = EVID / "ab_cards" / run
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(EVID / "sweep_cards", dst)


def _crit_of_joint(joint: str | None) -> str | None:
    if joint is None:
        return None
    if joint in ("split_angle", "leg_extension"):
        return joint
    return fz.ANGLE_VS_REFERENCE_PREFIX + joint


def _conf_probe_all() -> dict[str, dict]:
    """전 angle freeze x 양측 x (꼭짓점/사지/몸통) align conf 실값 — 독립 채록.

    스윕 5동작 한정 — probes.log 에는 벤치 슬롯(pdshape correct/realupload,
    구포맷 align refKp 부재)도 있어 전 동작 순회는 KeyError (run1 실측).
    """
    out: dict[str, dict] = {}
    for m in MOTIONS:
        by_rid = CTX.freeze_by_rid.get(m) or {}
        ax = _ensure_align(m)
        for rid, f in by_rid.items():
            jk = f["joint"]
            if jk in ("split_angle", "leg_extension") or "_" not in jk:
                continue
            prefix, suffix = jk.split("_", 1)
            decl = fz.ANGLE_BAKE_MAP.get(suffix)
            if decl is None:
                continue
            names = [jk, f"{prefix}_{decl[0]}", f"{prefix}_{decl[1]}"]
            ent: dict = {}
            for side, sec in (("user", f["userSec"]), ("ref", f["refSec"])):
                rep = ax["rep15"][side]
                ai = _clamp_ai(sec, ax["afps"], int(rep["frames"]))
                ent[side] = {
                    n: {
                        "conf": _conf_of(rep, ai, _canon17(n)),
                        "pass": cg.kp(rep, ai, _canon17(n),
                                      conf_min=_CONF_MIN) is not None,
                    }
                    for n in names
                }
                ent[f"{side[0]}Ai"] = ai
            out[f"{m}|{rid}"] = ent
    return out


def _status(run: str, m: str, rid: str, crit: str | None,
            dropped: dict[str, str], res_m: dict) -> tuple[str, bool, str | None]:
    """(상태 문자열, 카드 존재, zoom md5)."""
    if rid in dropped:
        return f"dropped:{dropped[rid]}", False, None
    r = RUNS[run]
    if any(d["motion"] == m and d["rid"] == rid for d in r["drops"]):
        return "omitted:display_anchor_drop", False, None
    st = r["bake"].get((m, crit))
    name = f"zoom_{crit}.png"
    md5 = _zoom_md5(res_m).get(name)
    if st is None:
        # 유닛이 build 에 들어갔으나 카드 0 — 3184행 무로그 skip (member 신뢰 0)
        return "omitted:member_conf_zero", False, None
    return st, md5 is not None, md5


def _assemble(iv: dict, res_a: dict, res_b: dict, confs: dict) -> dict:
    cards = []
    survivors, dropped = {}, {}
    seams_b = RUNS["B"]["seams"]
    for m in iv:
        survivors[m] = {
            "ivs": iv[m]["verdict"]["survivors"],
            "A": res_a[m]["verdict"]["survivors"],
            "B": res_b[m]["verdict"]["survivors"],
        }
        dropped[m] = {
            "ivs": iv[m]["verdict"]["dropped"],
            "A": res_a[m]["verdict"]["dropped"],
            "B": res_b[m]["verdict"]["dropped"],
        }
        drop_a = {s.split(":", 1)[0]: s.split(":", 1)[1]
                  for s in res_a[m]["verdict"]["dropped"]}
        drop_b = {s.split(":", 1)[0]: s.split(":", 1)[1]
                  for s in res_b[m]["verdict"]["dropped"]}
        rids = sorted(set(CTX.freeze_by_rid.get(m) or {}) | set(drop_a))
        for rid in rids:
            f = (CTX.freeze_by_rid.get(m) or {}).get(rid)
            joint = f["joint"] if f else None
            crit = _crit_of_joint(joint)
            a_st, a_card, md_a = _status("A", m, rid, crit, drop_a, res_a[m])
            b_st, b_card, md_b = _status("B", m, rid, crit, drop_b, res_b[m])
            seam_events = [
                v for k, v in seams_b.items()
                if k[0] == m and crit is not None and k[1] == str(crit)
            ]
            seam_tried = bool(seam_events) or b_st in (
                "omitted:display_anchor_drop", "omitted:member_conf_zero",
            )
            entry = {
                "motion": m, "rid": rid, "joint": joint, "criterion": crit,
                "freeze": ({"userSec": f["userSec"], "refSec": f["refSec"]}
                           if f else None),
                "aStatus": a_st, "bStatus": b_st,
                "aCard": a_card, "bCard": b_card,
                "mdA": md_a, "mdB": md_b,
                "changed": md_a != md_b,
                "seamTried": seam_tried,
                "seamFired": sorted({e["seam"] for e in seam_events
                                     if e.get("outcome") in ("spec", "injected")}),
                "alignConf": confs.get(f"{m}|{rid}"),
                "recovered": (b_st.startswith("drawn")
                              and not a_st.startswith("drawn")),
            }
            cards.append(entry)
    return {
        "survivors": survivors,
        "dropped": dropped,
        "cards": cards,
        "eyeStubCalls": {r: RUNS[r]["eyeStubCalls"] for r in RUNS},
    }


def _sheets(verdict: dict) -> int:
    """카드별 A|B 나란히 시트 — 대조용 합성 (육안 판정은 원본 카드 Read)."""
    out_dir = EVID / "ab_cards" / "sheets"
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for c in verdict["cards"]:
        if not (c["aCard"] or c["bCard"]):
            continue
        name = f"zoom_{c['criterion']}.png"
        panels = []
        for run in ("A", "B"):
            p = EVID / "ab_cards" / run / c["motion"] / name
            if p.exists():
                panels.append((run, Image.open(p).convert("RGB")))
            else:
                panels.append((run, None))
        h = max(im.height for _, im in panels if im is not None)
        ims = []
        for run, im in panels:
            if im is None:
                im = Image.new("RGB", (max(
                    i.width for _, i in panels if i is not None), h),
                    (240, 240, 240))
                d = ImageDraw.Draw(im)
                d.text((20, h // 2), f"{run}: no card", fill=(120, 120, 120))
            elif im.height != h:
                im = im.resize((round(im.width * h / im.height), h))
            ims.append((run, im))
        gap, label_h = 12, 28
        w = sum(im.width for _, im in ims) + gap
        sheet = Image.new("RGB", (w, h + label_h), (255, 255, 255))
        d = ImageDraw.Draw(sheet)
        x = 0
        for run, im in ims:
            tag = f"{run} ({c['motion']} {c['rid']})"
            if run == "B" and c["changed"]:
                tag += " *changed"
            d.text((x + 6, 7), tag, fill=(200, 40, 20))
            sheet.paste(im, (x, label_h))
            x += im.width + gap
        sheet.save(out_dir / f"{c['motion']}__{name}")
        n += 1
    return n


def ab() -> int:
    _guard_ev()
    missing = _preflight()
    if missing:
        EVID.mkdir(exist_ok=True)
        (EVID / "BLOCKER.md").write_text(
            "# BLOCKER — 정본 재료 부재 (대체 재료 발명 금지)\n\n"
            + "\n".join(f"- `{p}`" for p in missing) + "\n"
        )
        print(f"BLOCKER: 정본 재료 {len(missing)}건 부재 — evidence/BLOCKER.md")
        return 1
    EVID.mkdir(exist_ok=True)
    _load_freezes()
    iv = json.loads((_IVS_EV / "sweep_verdict.json").read_text())

    tap = _LogTap()
    obs = _Observer()
    logging.getLogger().addHandler(tap)
    obs.install()
    try:
        # ── A 런 (무패치 동치 게이트) ─────────────────────────────────────
        print("══ RUN A (무패치 — ivs 동치 게이트) ══")
        _switch_run("A")
        eye0 = gr._EYE_STUB["calls"]
        res_a = vl.sweep()
        RUNS["A"]["eyeStubCalls"] = gr._EYE_STUB["calls"] - eye0
        shutil.copyfile(EVID / "sweep_verdict.json",
                        EVID / "sweep_verdict_A.json")
        _snapshot_cards("A")

        bad = _a_gate(res_a, iv)
        if bad:
            (EVID / "BLOCKER.md").write_text(
                "# BLOCKER — A 런(무패치)이 ivs 정본과 불일치\n\n"
                "기반이 흔들린 채 B 를 재면 무의미 — 진행 중단 (plan 게이트).\n\n"
                + "\n".join(f"- {b}" for b in bad) + "\n"
            )
            print(f"BLOCKER: A != ivs {len(bad)}건 — evidence/BLOCKER.md 박제")
            return 1
        print(f"A GATE PASS (zoom md5 + survivors/dropped == ivs, "
              f"eyeStub={RUNS['A']['eyeStubCalls']})")

        # ── B 런 (seam 2 monkeypatch) ─────────────────────────────────────
        print("══ RUN B (align 유도 스펙 — seam 1/2) ══")
        _switch_run("B")
        eye0 = gr._EYE_STUB["calls"]
        bp = _BPatch()
        bp.install()
        try:
            res_b = vl.sweep()
        finally:
            bp.restore()
        RUNS["B"]["eyeStubCalls"] = gr._EYE_STUB["calls"] - eye0
        shutil.copyfile(EVID / "sweep_verdict.json",
                        EVID / "sweep_verdict_B.json")
        _snapshot_cards("B")
    finally:
        obs.restore()
        logging.getLogger().removeHandler(tap)

    confs = _conf_probe_all()
    verdict = _assemble(iv, res_a, res_b, confs)

    a_match = not _a_gate(res_a, iv)
    sur_ok = all(
        verdict["survivors"][m]["ivs"] == verdict["survivors"][m]["A"]
        == verdict["survivors"][m]["B"]
        and verdict["dropped"][m]["ivs"] == verdict["dropped"][m]["A"]
        == verdict["dropped"][m]["B"]
        for m in iv
    )
    verdict["aMatchesIvs"] = bool(a_match)
    verdict["gateUntouched3Way"] = bool(sur_ok)

    for run in ("A", "B"):
        (EVID / f"measure_{run}.json").write_text(json.dumps({
            "bake": {f"{k[0]}|{k[1]}": v for k, v in RUNS[run]["bake"].items()},
            "anchors": RUNS[run]["anchors"],
            "drops": RUNS[run]["drops"],
            "seams": [v for v in RUNS[run]["seams"].values()],
            "eyeStubCalls": RUNS[run]["eyeStubCalls"],
        }, ensure_ascii=False, indent=1))
    (EVID / "ab_verdict.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=1))

    n_sheet = _sheets(verdict)
    # 정리 — 마지막 런 잔여물 (A/B 스냅샷이 정본)
    shutil.rmtree(EVID / "sweep_cards", ignore_errors=True)
    (EVID / "sweep_verdict.json").unlink(missing_ok=True)

    n_rec = sum(1 for c in verdict["cards"] if c["recovered"])
    n_chg = sum(1 for c in verdict["cards"] if c["changed"])
    print(
        f"AB DONE cards={len(verdict['cards'])} recovered={n_rec} "
        f"changed={n_chg} sheets={n_sheet} 3way={'OK' if sur_ok else 'FAIL'} "
        f"eyeStub A={RUNS['A']['eyeStubCalls']} B={RUNS['B']['eyeStubCalls']} "
        "(machine_eye 스텁 — Gemini 실호출 0)"
    )
    return 0 if (a_match and sur_ok) else 1


# ── --pairs: 반려 2건 짝 국면 회복 후보 스캔 ─────────────────────────────────
PAIR_MOTION = "pdshapefault"
PAIR_TARGETS = {"left_knee": "r03", "left_elbow": "r00"}
# 거리 규칙 (1줄): 양측 conf>=0.5 공통 관절만(POSE_BASIS_12), root=양 hip 중점
# 중심화, scale=torso(hip중점-어깨중점) px 정규화, 전신=공통 관절 L2 평균 —
# 랭킹은 전신, 국소(crit+ANGLE_BAKE_MAP 사지·몸통)는 참고 열.
_GEOM_NEED = ("left_hip", "right_hip", "left_shoulder", "right_shoulder")


def _side_pose(rep: dict, idx: int, size: tuple) -> dict[str, tuple]:
    pts = {}
    for j in cg.POSE_BASIS_12:
        xy = cg.kp(rep, idx, j, conf_min=_CONF_MIN)
        if xy is not None:
            pts[j] = (float(xy[0]) * size[0], float(xy[1]) * size[1])
    return pts


def _geom(p: dict) -> tuple | None:
    if any(n not in p for n in _GEOM_NEED):
        return None
    hip = ((p["left_hip"][0] + p["right_hip"][0]) / 2,
           (p["left_hip"][1] + p["right_hip"][1]) / 2)
    sh = ((p["left_shoulder"][0] + p["right_shoulder"][0]) / 2,
          (p["left_shoulder"][1] + p["right_shoulder"][1]) / 2)
    torso = math.hypot(sh[0] - hip[0], sh[1] - hip[1])
    if torso < 1e-6:
        return None
    return hip, torso


def _pose_dist(u_pts: dict, r_pts: dict, limb_joints: list[str]) -> dict | None:
    gu, gr_ = _geom(u_pts), _geom(r_pts)
    if gu is None or gr_ is None:
        return None
    common = sorted(set(u_pts) & set(r_pts))
    if not common:
        return None

    def nrm(p, g):
        return ((p[0] - g[0][0]) / g[1], (p[1] - g[0][1]) / g[1])

    ds = {
        j: math.dist(nrm(u_pts[j], gu), nrm(r_pts[j], gr_)) for j in common
    }
    limb_avail = [j for j in limb_joints if j in ds]
    return {
        "fullBody": round(sum(ds.values()) / len(ds), 4),
        "limb": (round(sum(ds[j] for j in limb_avail) / len(limb_avail), 4)
                 if limb_avail else None),
        "nBasis": len(common),
        "nLimb": len(limb_avail),
    }


def _video_frame(path: pathlib.Path, sec: float):
    import imageio.v2 as iio

    reader = iio.get_reader(str(path))
    fps = float(reader.get_meta_data()["fps"])
    idx = max(0, int(round(sec * fps)))
    try:
        frame = reader.get_data(idx)
    except IndexError:
        frame = reader.get_data(reader.count_frames() - 1)
    reader.close()
    return frame


def _still(user_img, ref_img, label: str, out: pathlib.Path) -> None:
    h = 960
    ims = []
    for arr in (user_img, ref_img):
        im = Image.fromarray(arr)
        im = im.resize((round(im.width * h / im.height), h))
        ims.append(im)
    gap, label_h = 10, 30
    w = sum(im.width for im in ims) + gap
    sheet = Image.new("RGB", (w, h + label_h), (255, 255, 255))
    ImageDraw.Draw(sheet).text((8, 8), label, fill=(200, 40, 20))
    x = 0
    for im in ims:
        sheet.paste(im, (x, label_h))
        x += im.width + gap
    sheet.save(out)


def pairs() -> int:
    _guard_ev()
    _load_freezes()
    m = PAIR_MOTION
    ax = _ensure_align(m)
    urep, rrep = ax["rep15"]["user"], ax["rep15"]["ref"]
    usize, rsize = ax["sizes"]["user"], ax["sizes"]["ref"]
    afps = ax["afps"]
    # 영상 캐시 확보 (--ab 가 먼저 돌았으면 존재; 없으면 vl 규칙으로 fetch)
    md = vl.SPA / m
    md.mkdir(parents=True, exist_ok=True)
    ukey, rkey, _mid = vl.SWEEP_JOBS[m]
    for p, key in ((md / "user.mp4", ukey), (md / "ref.mp4", rkey)):
        if not p.exists():
            vl._s3_client().download_file(vl.BUCKET, key, str(p))  # noqa: SLF001
            print(f"fetched {key}")

    stills_dir = EVID / "pair_stills"
    stills_dir.mkdir(parents=True, exist_ok=True)
    out: dict[str, dict] = {}
    for joint, rid in PAIR_TARGETS.items():
        f = CTX.freeze_by_rid[m][rid]
        assert f["joint"] == joint, (rid, f["joint"])
        u_sec, base_r_sec = f["userSec"], f["refSec"]
        u_ai = _clamp_ai(u_sec, afps, int(urep["frames"]))
        base_r_ai = _clamp_ai(base_r_sec, afps, int(rrep["frames"]))
        prefix, suffix = joint.split("_", 1)
        decl = fz.ANGLE_BAKE_MAP[suffix]
        limb_joints = [joint, _canon17(f"{prefix}_{decl[0]}"),
                       f"{prefix}_{decl[1]}"]
        u_pts = _side_pose(urep, u_ai, usize)

        rows = []
        for ri in range(int(rrep["frames"])):
            d = _pose_dist(u_pts, _side_pose(rrep, ri, rsize), limb_joints)
            if d is None:
                continue
            rows.append({"refAi": ri, "refSec": round(ri / afps, 3), **d})
        base = _pose_dist(u_pts, _side_pose(rrep, base_r_ai, rsize),
                          limb_joints)
        rows.sort(key=lambda r: r["fullBody"])
        cands: list[dict] = []
        for r in rows:
            if all(abs(r["refSec"] - c["refSec"]) >= 0.5 for c in cands):
                cands.append(dict(r))
            if len(cands) == 3:
                break
        # 후보 순간 ref V 성립 여부 (B 스펙 conf 판정만 — 렌더 재실행 불요)
        names = [joint, f"{prefix}_{decl[0]}", f"{prefix}_{decl[1]}"]
        for i, c in enumerate(cands, 1):
            c["rank"] = i
            confs = {}
            ok = True
            for n in names:
                cn = _canon17(n)
                p = cg.kp(rrep, c["refAi"], cn, conf_min=_CONF_MIN)
                confs[n] = {"conf": _conf_of(rrep, c["refAi"], cn),
                            "pass": p is not None}
                ok = ok and p is not None
            c["refVOk"] = ok
            c["refVConf"] = confs
            c["isNearBaseline"] = abs(c["refSec"] - base_r_sec) < 0.25
        out[joint] = {
            "rid": rid,
            "userSec": u_sec,
            "uAi": u_ai,
            "rule": ("양측 conf>=0.5 공통 관절만(POSE_BASIS_12), root=양 hip "
                     "중점 중심화, scale=torso(hip중점-어깨중점) px 정규화, "
                     "전신=공통 관절 L2 평균 — 랭킹은 전신, 국소는 참고"),
            "baseline": {"refSec": base_r_sec, "refAi": base_r_ai,
                         **(base or {"fullBody": None, "limb": None,
                                     "nBasis": 0, "nLimb": 0,
                                     "unmeasurable": True})},
            "candidates": cands,
            "scannedFrames": int(rrep["frames"]),
            "measurableFrames": len(rows),
            # 사전값 — 육안 대조 후 --recommend 로 확정 (rank1 자동 기입)
            "recommend": ({**{k: cands[0][k] for k in
                              ("refSec", "refAi", "fullBody", "limb")},
                           "src": "rank1-auto",
                           "note": "포즈 거리 1위 자동 — 육안 확정 전"}
                          if cands else None),
        }
        # 스틸 — 후보 + baseline (전신 나란히, l0u 선례)
        u_frame = _video_frame(md / "user.mp4", u_sec)
        for c in cands:
            r_frame = _video_frame(md / "ref.mp4", c["refSec"])
            _still(
                u_frame, r_frame,
                f"user {u_sec:.3f}s | ref cand{c['rank']} {c['refSec']:.3f}s "
                f"d={c['fullBody']}",
                stills_dir / f"pair_{joint}_cand{c['rank']}_"
                             f"ref{c['refSec']:.3f}s.png",
            )
        r_frame = _video_frame(md / "ref.mp4", base_r_sec)
        _still(
            u_frame, r_frame,
            f"user {u_sec:.3f}s | ref BASELINE(rejected) {base_r_sec:.2f}s "
            f"d={(base or {}).get('fullBody')}",
            stills_dir / f"pair_{joint}_baseline_ref{base_r_sec:.2f}s.png",
        )
        print(f"PAIRS {joint}: cands={[c['refSec'] for c in cands]} "
              f"baseline d={(base or {}).get('fullBody')} "
              f"measurable={len(rows)}/{int(rrep['frames'])}")

    (EVID / "pair_candidates.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    print("PAIRS DONE — evidence/pair_candidates.json + pair_stills/")
    return 0


def set_recommend(specs: list[str]) -> int:
    """육안 대조 후 추천 확정 — 후보 값 검증 (임의 값 발명 금지)."""
    p = EVID / "pair_candidates.json"
    data = json.loads(p.read_text())
    for spec in specs:
        joint, rest = spec.split("=", 1)
        sec_s, _, note = rest.partition(":")
        sec = float(sec_s)
        cands = data[joint]["candidates"]
        hit = [c for c in cands if abs(c["refSec"] - sec) < 1e-6]
        assert hit, f"{joint}: {sec} 는 후보에 없음 — 추천은 후보 중에서만"
        c = hit[0]
        data[joint]["recommend"] = {
            "refSec": c["refSec"], "refAi": c["refAi"],
            "fullBody": c["fullBody"], "limb": c["limb"],
            "src": "distance+eye", "note": note or "육안 대조 확정",
        }
        print(f"recommend {joint} -> ref {c['refSec']}s (rank {c['rank']})")
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ab", action="store_true")
    ap.add_argument("--pairs", action="store_true")
    ap.add_argument("--recommend", action="append", default=[],
                    metavar="joint=refSec:note")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    rc = 0
    if args.ab:
        rc = ab()
        if rc:
            return rc
    if args.pairs:
        rc = pairs()
        if rc:
            return rc
    if args.recommend:
        rc = set_recommend(args.recommend)
    if not (args.ab or args.pairs or args.recommend):
        ap.print_help()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
