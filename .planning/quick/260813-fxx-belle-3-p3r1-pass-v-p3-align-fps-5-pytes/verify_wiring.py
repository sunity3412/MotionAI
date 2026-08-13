#!/usr/bin/env python3
"""운영 배선 검증 드라이버 (quick-260813-fxx) — display_anchor + 골반 P3 하이브리드.

Task 2 배선(fault_zoom display_anchor 단일 출처 + HYBRID_ANGLE_SUFFIXES)이
**운영 코드 그대로** ufb fresh doc 재렌더에서 의도-변경-국한으로 동작함을 기계
증명한다. 하네스 monkeypatch 렌더가 아니라 무패치 vl.run() — 관찰 래퍼만.

grammar_round importlib 상속 (round3.py 선례): machine_eye 스텁(Gemini 실호출
0) + env 더미 키 + 인터프리터 자동 승격 + vl/CERT_MD5/CERT_SURVIVORS/FREEZE_SEC
/CARD_NAME. 단 EV 는 이 사이클 evidence/_ev 로 재지정 (ufb/xa1 원본 무접촉).

stages:
  --once --out P   무패치 vl.run() 1회 → JSON (pngMd5/survivors/dropped/
                   display_anchor 실행 로그 캡처/스펙 평행이동 관찰/크롭 박스).
  --check          --once 별도 프로세스 2회 →
                   (1) 결정론: pngMd5/survivors/dropped 완전 동일
                   (2) freeze 전건 일치: survivors @u/r == gr.FREEZE_SEC 그대로
                       (u{:.3f}/r{:.2f} — verify_local 90행 포맷, 순간 발명 0)
                   (3) 의도-변경-국한: 대상 2카드 md5 != 인증값(변경 = 의도)
                       AND survivors/dropped/advisory == ufb 인증값 AND
                       display_anchor drop 0건 AND manifest 키셋 동일
                   (4) align 예측 대조: 캡처 로그의 (u_ai, r_ai, 좌표)를 캐시
                       align 독립 재구축 + cg.kp(conf_min=0.5)로 재계산 일치 +
                       hip vertex px 이동량을 P3r1 실측(user 1.6/ref 8.7px)과
                       대조 기록 (게이트 아님 — 기록, evidence/wiring_check.json)
                   (5) vl.approved() 위임: 승인 코퍼스 hold 9/9 + pair 9/9
                   전 판정 PASS = "WIRING-CHECK PASS", FAIL = 박제 후 비영 종료.

프로덕션 코드 아님 — quick 로컬 드라이버. 채점 무접촉, 네트워크 신규 0
(캐시 부재 시에만 vl --fetch 안내).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import math
import pathlib
import shutil
import subprocess
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_XA1 = _HERE.parent / "260811-xa1-mark-grammar-round-ufb-freeze-2-belle"
_UFB = _HERE.parent / "260811-ufb-freeze-only"

EVID = _HERE / "evidence"
P3R1_REF_PX = {"user": 1.6, "ref": 8.7}  # 라운드 3 실측 (좌표 검산 기준점)


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# grammar_round 로드 — 스텁/더미 키/인터프리터 승격 전부 상속. import 시점에
# vl.EV 를 xa1 로 돌려놓는데, 이 사이클 evidence 로 재재지정한다.
gr = _load_module("grammar_round", _XA1 / "grammar_round.py")
vl = gr.vl
gr.vl.EV = EVID / "_ev"

from sunity_shared.analysis import card_gates as cg  # noqa: E402
from sunity_shared.analysis import compare_align  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

log = logging.getLogger("verify_wiring")

TARGET_CRITS = {
    "left_hip": "angle_vs_reference__left_hip",
    "left_elbow": "angle_vs_reference__left_elbow",
}


def _guard_ev() -> None:
    assert "260813-fxx" in str(vl.EV), (
        f"EV 재지정 실패: {vl.EV} — ufb/xa1 evidence 파괴 위험, 실행 금지"
    )


class _AnchorLogCapture(logging.Handler):
    """root 로거에서 display_anchor 실행 로그 args 캡처 (문자열 재파싱 아님)."""

    def __init__(self):
        super().__init__(level=logging.INFO)
        self.anchors: list[dict] = []
        self.drops: list[str] = []

    def emit(self, record):  # noqa: D102
        try:
            msg = record.msg if isinstance(record.msg, str) else ""
            if msg.startswith("display_anchor drop"):
                self.drops.append(record.getMessage())
            elif msg.startswith("display_anchor"):
                a = record.args
                self.anchors.append({
                    "rid": a[0], "joint": a[1],
                    "uAi": int(a[2]), "rAi": int(a[3]),
                    "user": [float(a[4]), float(a[5])],
                    "ref": [float(a[6]), float(a[7])],
                    "line": record.getMessage(),
                })
        except Exception:  # noqa: BLE001 - 캡처 실패는 드라이버 문제로만
            pass


class _ShiftObserver:
    """fz 관찰 래퍼 — 산출 무변경, 스펙 평행이동/크롭 박스만 기록.

    build 랩이 현재 unit 의 criterion 을 스택하고, shift_bake_spec 랩이
    (spec0, anchor) 짝을, _side_crop 랩이 (frame shape, box)를 crit 별 호출
    순서(user → ref)대로 기록한다 — P3r1 px 이동량 대조 재료.
    """

    def __init__(self):
        self.cur_crit: str | None = None
        self.shifts: dict[str, list[dict]] = {}
        self.crops: dict[str, list[dict]] = {}
        self._orig_build = fz.build_fault_zoom_comparisons
        self._orig_shift = fz.shift_bake_spec
        self._orig_crop = fz._side_crop

    def install(self):
        fz.build_fault_zoom_comparisons = self._build
        fz.shift_bake_spec = self._shift
        fz._side_crop = self._crop

    def restore(self):
        fz.build_fault_zoom_comparisons = self._orig_build
        fz.shift_bake_spec = self._orig_shift
        fz._side_crop = self._orig_crop

    def _build(self, *a, **k):
        units = k.get("criterion_units") or []
        self.cur_crit = str(units[0].get("criterion")) if units else None
        return self._orig_build(*a, **k)

    def _shift(self, spec, anchor):
        out = self._orig_shift(spec, anchor)
        if spec is not None and anchor is not None and self.cur_crit:
            self.shifts.setdefault(self.cur_crit, []).append({
                "spec0": [float(spec[0][0]), float(spec[0][1])],
                "anchor": [float(anchor[0]), float(anchor[1])],
            })
        return out

    def _crop(self, frame, *a, **k):
        out = self._orig_crop(frame, *a, **k)
        if self.cur_crit and out[3] is not None:
            self.crops.setdefault(self.cur_crit, []).append({
                "shape": [int(frame.shape[0]), int(frame.shape[1])],
                "box": [int(x) for x in out[3]],
            })
        return out


def once(out_path: pathlib.Path) -> int:
    _guard_ev()
    gr._require_cache()
    cap = _AnchorLogCapture()
    obs = _ShiftObserver()
    logging.getLogger().addHandler(cap)
    obs.install()
    try:
        out = vl.run()
    finally:
        obs.restore()
        logging.getLogger().removeHandler(cap)
    payload = {
        "pngMd5": out["pngMd5"],
        "survivors": list(out["verdict"]["survivors"]),
        "dropped": list(out["verdict"]["dropped"]),
        "advisory": [
            [c.get("joint"), c.get("tier")]
            for c in out["attached"]["comparisons"]
            if c.get("tier") == "advisory"
        ],
        "confirmedJoints": [
            c.get("joint") for c in out["attached"]["comparisons"]
            if c.get("tier") == "confirmed"
        ],
        "displayAnchors": cap.anchors,
        "displayAnchorDrops": cap.drops,
        "shifts": obs.shifts,
        "crops": obs.crops,
        "eyeStubCalls": gr._EYE_STUB["calls"],
        "cropLines": out.get("cropLines") or [],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    print(f"ONCE OK -> {out_path} (eye stub calls={gr._EYE_STUB['calls']} — "
          "machine_eye 스텁, Gemini 실호출 0)")
    return 0


def _rebuild_align() -> dict:
    """--check 프로세스에서 align 독립 재구축 — vl.run 과 같은 재료·같은 함수."""
    doc = json.loads(vl.DOC.read_text())
    records = (doc["result"].get("deductionBreakdown") or {}).get("records") or []
    p35 = json.loads((vl.DATA / "pdshapefault" / "align.json").read_text())
    return compare_align.build_align(
        vl.VIDEOS["user"], vl.VIDEOS["ref"], records, vl.ALIGN_WORK,
        infer_fn=vl._replay_infer(p35),
    )


def check() -> int:
    _guard_ev()
    gr._require_cache()
    fails: list[str] = []
    report: dict = {"p3r1ReferencePx": P3R1_REF_PX}

    # ── 별도 프로세스 2회 ────────────────────────────────────────────────────
    runs: list[dict] = []
    EVID.mkdir(exist_ok=True)
    for i in (1, 2):
        p = EVID / f"once{i}.json"
        print(f"── once {i}/2 (별도 프로세스) ──")
        r = subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).resolve()),
             "--once", "--out", str(p)],
            capture_output=True, text=True,
        )
        sys.stdout.write(r.stdout[-2500:])
        if r.returncode != 0:
            sys.stderr.write(r.stderr[-2500:])
            print(f"once {i} FAILED (exit {r.returncode})")
            return 1
        runs.append(json.loads(p.read_text()))
    j1, j2 = runs

    # (1) 결정론
    det = {k: (j1[k] == j2[k]) for k in ("pngMd5", "survivors", "dropped")}
    report["determinism"] = det
    if all(det.values()):
        print("DETERMINISM PASS (pngMd5/survivors/dropped 2회 동일)")
    else:
        fails.append(f"determinism:{det}")

    # (2) freeze 전건 일치 — verify_local 90행 포맷 (u{:.3f}/r{:.2f})
    expect_moments = {
        j: f"u{gr.FREEZE_SEC[j]['user']:.3f}/r{gr.FREEZE_SEC[j]['ref']:.2f}"
        for j in gr.CARD_NAME
    }
    got_moments = [s.split("@", 1)[1] for s in j1["survivors"]]
    fm_ok = sorted(got_moments) == sorted(expect_moments.values())
    report["freezeMatch"] = {
        "expected": expect_moments, "got": got_moments, "ok": fm_ok,
    }
    if fm_ok:
        print(f"FREEZE-MATCH PASS ({got_moments} == FREEZE_SEC — 순간 발명 0)")
    else:
        fails.append(f"freeze:{got_moments}")

    # (3) 의도-변경-국한
    ufb_cert = json.loads((_UFB / "evidence" / "run_verdict.json").read_text())
    targets = list(gr.CERT_MD5)
    changed = {
        n: j1["pngMd5"].get(n) != gr.CERT_MD5[n] for n in targets
    }
    keyset_ok = sorted(j1["pngMd5"]) == sorted(gr.CERT_MD5)
    nontarget_ok = all(
        j1["pngMd5"][n] == gr.CERT_MD5[n]
        for n in j1["pngMd5"] if n not in targets
    )
    surv_ok = j1["survivors"] == gr.CERT_SURVIVORS
    drop_ok = j1["dropped"] == ufb_cert["verdict"]["dropped"]
    adv_cert = [
        [c.get("joint"), c.get("tier")]
        for c in ufb_cert["attached"]["comparisons"]
        if c.get("tier") == "advisory"
    ]
    adv_ok = j1["advisory"] == adv_cert
    da_drop_ok = not j1["displayAnchorDrops"] and not any(
        "display_anchor" in d for d in j1["dropped"]
    )
    report["intendedChangeOnly"] = {
        "targetChanged": changed, "manifestKeysetOk": keyset_ok,
        "nonTargetUnchanged": nontarget_ok, "survivorsOk": surv_ok,
        "droppedOk": drop_ok, "advisoryOk": adv_ok,
        "displayAnchorDrops0": da_drop_ok,
        "pngMd5": j1["pngMd5"], "certMd5": dict(gr.CERT_MD5),
    }
    if (all(changed.values()) and keyset_ok and nontarget_ok and surv_ok
            and drop_ok and adv_ok and da_drop_ok):
        print("INTENDED-CHANGE PASS (대상 2장만 md5 변경 + survivors/dropped/"
              "advisory 인증값 일치 + display_anchor drop 0)")
    else:
        fails.append("intended-change")

    # (4) align 예측 대조 — 독립 재구축 + 같은 공식 재계산
    align = _rebuild_align()
    afps = float(align["fps"])
    rep15 = {s: cg.align_to_report(align, s) for s in ("user", "ref")}
    pred_rows = []
    anchors_by_joint = {a["joint"]: a for a in j1["displayAnchors"]}
    align_ok = len(anchors_by_joint) == len(gr.CARD_NAME)
    for joint in gr.CARD_NAME:
        got = anchors_by_joint.get(joint)
        row: dict = {"joint": joint, "logged": got}
        if got is None:
            row["ok"] = False
            align_ok = False
            pred_rows.append(row)
            continue
        ok_j = True
        for panel, key_idx, key_xy in (
            ("user", "uAi", "user"), ("ref", "rAi", "ref"),
        ):
            idx = max(0, min(
                int(round(gr.FREEZE_SEC[joint][panel] * afps)),
                int(rep15[panel]["frames"]) - 1,
            ))
            xy = cg.kp(rep15[panel], idx, joint, conf_min=0.5)
            row[f"{panel}Expected"] = {
                "idx": idx, "xy": None if xy is None else list(xy),
            }
            if xy is None or got[key_idx] != idx or (
                math.hypot(xy[0] - got[key_xy][0], xy[1] - got[key_xy][1])
                > 1e-9
            ):
                ok_j = False
        row["ok"] = ok_j
        align_ok = align_ok and ok_j
        pred_rows.append(row)
    report["alignPrediction"] = {"ok": align_ok, "rows": pred_rows}
    if align_ok:
        print("ALIGN-PREDICTION PASS (u_ai/r_ai/좌표 = 독립 재계산과 일치)")
    else:
        fails.append("align-prediction")

    # hip vertex px 이동량 — P3r1 실측 대조 **기록** (게이트 아님).
    hip_crit = TARGET_CRITS["left_hip"]
    hip_shift_px: dict = {}
    sh = (j1["shifts"] or {}).get(hip_crit) or []
    cr = (j1["crops"] or {}).get(hip_crit) or []
    for k, panel in ((0, "user"), (1, "ref")):
        if k < len(sh) and k < len(cr):
            dx = sh[k]["anchor"][0] - sh[k]["spec0"][0]
            dy = sh[k]["anchor"][1] - sh[k]["spec0"][1]
            h, w = cr[k]["shape"]
            side = cr[k]["box"][2]
            hip_shift_px[panel] = round(
                math.hypot(dx * w, dy * h) / max(1, side) * 360.0, 2
            )
    report["hipShiftPanelPx"] = {
        "measured": hip_shift_px, "p3r1Reference": P3R1_REF_PX,
        "note": "현행 크롭 박스 px 환산 — P3r1 은 크롭 무변경 박스 측정치라 "
                "직접 대조는 근사 (기록 전용, 게이트 아님)",
    }
    print(f"hip vertex 이동 (panel px): {hip_shift_px} "
          f"(P3r1 실측 {P3R1_REF_PX} — 대조 기록)")

    # (5) 승인 코퍼스 위임 (오프라인 — Gemini 0회)
    ap = vl.approved()
    ap_ok = ap["binding"] == 9 and ap["hold"] == 9 and ap["pair"] == 9
    report["approved"] = {
        "binding": ap["binding"], "hold": ap["hold"], "pair": ap["pair"],
        "peak": ap["peak"], "ok": ap_ok,
    }
    if ap_ok:
        print("APPROVED PASS (joint-scope hold 9/9 + pair 9/9)")
    else:
        fails.append(f"approved:{ap['hold']}/{ap['pair']}/{ap['binding']}")

    # 카드 실물 복사 (육안 판정 재료 — frames-before-numbers)
    cards_src = vl.EV / "cards"
    cards_dst = EVID / "cards"
    cards_dst.mkdir(parents=True, exist_ok=True)
    for name in targets:
        src = cards_src / name
        if src.exists():
            shutil.copy2(src, cards_dst / name)

    report["pass"] = not fails
    report["fails"] = fails
    (EVID / "wiring_check.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1))
    if fails:
        print(f"WIRING-CHECK FAIL: {fails} (wiring_check.json 박제)")
        return 1
    print("WIRING-CHECK PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--out", type=pathlib.Path, default=EVID / "once.json")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    EVID.mkdir(exist_ok=True)
    if args.once:
        return once(args.out)
    if args.check:
        return check()
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
