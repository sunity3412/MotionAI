#!/usr/bin/env python3
"""카드 초 라벨 실효 fps 수리 재현 게이트 (quick-260813-u8i).

label_fps 배선(수리 커밋 1eccf9c+5e85758) 뒤 승인 5동작 스윕을 운영 경로로
2회 실행해 "변경 = 초 라벨뿐"을 기계 증명한다 — nh4 verify_port.py 구조 상속
(같은 세션 scratchpad 캐시 + grammar_round Gemini 스텁/더미 키 — 실호출 0,
로컬 S3 업로드 0).

게이트 (전건 PASS 필요, 하나라도 실패 = exit 1 — 결과 = evidence/label_check.json):
  1. 무회귀 핵: 본 런 survivors/dropped == nh4 정본(sweep_verdict_port.json)
     전건 + display_anchor 좌표 로그(u_ai/r_ai/user/ref xy) 본 런 == 대조 런.
     nh4 정본은 스윕 display_anchor 성공 라인을 따로 박제하지 않았으므로
     정본 대조는 전이 사슬로 성립한다: 대조 런 md5 == nh4 정본(게이트 2)이
     대조 런의 전 픽셀·좌표를 nh4 와 동치로 못박고, 본 런 좌표 == 대조 런
     좌표가 그 동치를 본 런까지 잇는다 (좌표는 같은 입력의 결정론 산출).
  2. 변경=라벨뿐 증명 (대조 런): build_fault_zoom_comparisons 를 shim 으로
     감싸 label_fps 만 (9.0, 9.0) 강제한 대조 런의 zoom 카드 md5 == nh4 정본
     md5 전건 — 라벨 분모를 종전값으로 되돌리면 픽셀이 완전 재현된다 = 이
     수리의 픽셀 변경원이 라벨뿐임의 기계 증명. shim 은 대조 런 한정 하네스
     장치 (운영 코드 무패치), 본 런(무패치)은 게이트 3 이 판정.
  3. 라벨 라운드트립 (본 런): 카드별 |신 라벨 − freeze 실초| <= 측별
     1.5프레임/eff. freeze 실초·구 라벨 기대값은 전부 nh4 정본 freezes 에서
     기계 유도 (앵커 값 하드코딩 0). 허용치 근거: user 측은 반올림 1회
     (u9=round(sec x eff), 최대 0.5프레임)지만 ref 측은 rep9 보정(k<1 rep
     메타 실존 케이스)의 **이중 반올림 경로** — _override_idx 의
     round(sec x eff x rep9/video_n) 와 fault_zoom ref_display_frame_index
     역변환 round 가 겹쳐 최악 ≈0.117s 로 1프레임(0.12s) 게이트는 경계선
     플레이크. 1.5프레임(≈0.15s)이 결정론 마진. 구 라벨은 대조 런의 같은
     표시 인덱스에서 ÷9.0 독립 산출 (인덱스 사슬 불변은 게이트 1·2 가 증명)
     + nh4 정본 attached 값과 일치 교차검증.
  4. pytest 기준선: backend/tests 전체 failed 59 동일 (신규 실패 0).
  5. 채점 무접촉: 산식 5파일(deduction_engine/dimensions/kismam/motiondtw/
     assemble) 수리 커밋 범위 diff 0.
  6. 분기 0: 수리 diff 추가 라인에 동작명/분석 ID 리터럴 0 (fxx W-1 방식).
  7. Gemini 실호출 0 (grammar_round machine_eye 스텁 계수).

프로덕션 코드 아님 — quick 로컬 드라이버 (verify_port.py 구조 상속).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import os
import pathlib
import re
import shutil
import subprocess
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
_XA1 = _HERE.parent / "260811-xa1-mark-grammar-round-ufb-freeze-2-belle"
_NH4_EV = (
    _HERE.parent / "260813-nh4-2-b-ref-v-pdshape-pair-override-pod" / "evidence"
)

EVID = _HERE / "evidence"
CONTRAST = EVID / "contrast"
SCRATCH = pathlib.Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "ae166167-1abf-4754-9fe8-336a719ef9e2/scratchpad"
)

# 수리 커밋 범위 (게이트 5·6) — 사전 박제: 6ded49cf = 수리 전 HEAD,
# 5e85758 = feat 커밋 (1eccf9c test + 5e85758 feat 두 커밋이 수리 전량).
REPAIR_BASE = "6ded49cf"
REPAIR_HEAD = "5e85758"
SCORING_FILES = [
    "backend/shared/python/sunity_shared/analysis/deduction_engine.py",
    "backend/shared/python/sunity_shared/analysis/dimensions.py",
    "backend/shared/python/sunity_shared/analysis/kismam.py",
    "backend/shared/python/sunity_shared/analysis/motiondtw.py",
    "backend/shared/python/sunity_shared/analysis/assemble.py",
]
# 동작명/분석 ID 리터럴 (게이트 6) — 관절명(left_elbow 등)은 동작명이 아니라
# 제외. "elbow" 단독은 관절명 오탐이라 모션 id 형태로만 잡는다.
BRANCH_LITERALS = [
    "pdshape", "peterpan", "peter-pan", "powerspin", "power-spin",
    "kipup", "kip-up", "elbowtwist", "elbow-twist", "foxtop",
    "1785373695", "p34fresh", "csKWYvI3",
]
PYTEST_BASELINE_FAILED = 59
TOL_FRAMES = 1.5  # 측별 허용치 (프레임/eff) — 모듈 docstring 게이트 3 근거


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


gr = _load_module("grammar_round", _XA1 / "grammar_round.py")
vl = gr.vl
fz = gr.fz  # sunity_shared.analysis.fault_zoom 모듈 객체 (shim 대상)
vl.SPA = SCRATCH / "approved_sweep"

log = logging.getLogger("verify_label")


class _AnchorTap(logging.Handler):
    """운영 로그 채록 — display_anchor 성공 좌표 / drop / align_bake miss."""

    def __init__(self):
        super().__init__(level=logging.INFO)
        self.anchors: list[str] = []
        self.drops: list[str] = []
        self.misses: list[str] = []

    def emit(self, record):  # noqa: D102
        try:
            msg = record.getMessage()
            if msg.startswith("display_anchor drop"):
                self.drops.append(msg)
            elif msg.startswith("display_anchor "):
                self.anchors.append(msg)
            elif msg.startswith("align_bake miss"):
                self.misses.append(msg)
        except Exception:  # noqa: BLE001
            pass


def _sweep(ev_dir: pathlib.Path, shim_label_90: bool) -> tuple[dict, _AnchorTap]:
    """스윕 1회 — ev_dir 로 산출 리다이렉트, shim 은 대조 런 한정."""
    vl.EV = ev_dir
    assert "260813-u8i" in str(vl.EV), f"EV 재지정 실패: {vl.EV}"
    assert str(vl.SPA).startswith(str(SCRATCH)), f"SPA 재지정 실패: {vl.SPA}"
    ev_dir.mkdir(parents=True, exist_ok=True)

    tap = _AnchorTap()
    logging.getLogger().addHandler(tap)
    orig_build = fz.build_fault_zoom_comparisons
    if shim_label_90:
        # 대조 런 shim — label_fps 만 종전 분모(9.0)로 강제. 운영 코드 무패치:
        # 이 프로세스의 모듈 속성만 잠시 바꾸고 finally 복원.
        def _shim(*a, **kw):
            kw["label_fps"] = (9.0, 9.0)
            return orig_build(*a, **kw)

        fz.build_fault_zoom_comparisons = _shim
    try:
        res = vl.sweep()
    finally:
        fz.build_fault_zoom_comparisons = orig_build
        logging.getLogger().removeHandler(tap)
    return res, tap


def _zoom_md5_dir(cards_dir: pathlib.Path) -> dict[str, str]:
    return {
        p.name: hashlib.md5(p.read_bytes()).hexdigest()
        for p in sorted(cards_dir.glob("zoom_*.png"))
    }


def _probe_eff() -> dict[str, dict[str, float]]:
    """동작별 (user, ref) 실효 fps + user 프레임 수 — 운영 함수 그대로."""
    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor

    ext = FfmpegFrameExtractor(target_fps=9.0, max_side=640)
    out: dict[str, dict[str, float]] = {}
    for m in vl.SWEEP_JOBS:
        md = vl.SPA / m
        out[m] = {
            "user": float(ext.probe_effective_fps(md / "user.mp4")),
            "ref": float(ext.probe_effective_fps(md / "ref.mp4")),
            # 클립 끝 clamp 판정 재료 (게이트 3 경계 케이스) — 운영 build 가
            # 쓰는 frames 배열 길이 그대로 (ext.extract 동일 파라미터).
            "userVideoN": int(ext.extract(md / "user.mp4").shape[0]),
        }
    return out


def _crit_to_freeze(crit: str, freezes: list[dict]) -> dict | None:
    """criterion → nh4 정본 freeze 행 (기계 유도 — 앵커 하드코딩 0)."""
    joint = crit.split("__")[-1] if "__" in crit else crit
    for f in freezes:
        if f["joint"] == joint:
            return f
    return None


def _confirmed_cards(res_m: dict) -> list[dict]:
    return [
        c for c in (res_m.get("attached", {}).get("comparisons") or [])
        if c.get("tier") == "confirmed" and c.get("criterion")
    ]


def main() -> int:
    EVID.mkdir(exist_ok=True)
    fails: list[str] = []
    notes: list[str] = []

    nh4 = json.loads((_NH4_EV / "sweep_verdict_port.json").read_text())

    eye0 = gr._EYE_STUB["calls"]  # noqa: SLF001
    print("══ 본 런 (무패치 — 실효 fps 라벨) ══")
    main_res, main_tap = _sweep(EVID, shim_label_90=False)
    print("══ 대조 런 (shim label_fps=(9.0,9.0) — 종전 분모) ══")
    con_res, con_tap = _sweep(CONTRAST, shim_label_90=True)
    eye_stub_calls = gr._EYE_STUB["calls"] - eye0  # noqa: SLF001

    # ── 게이트 1: survivors/dropped == nh4 정본 + display_anchor 좌표 동일 ──
    for m in nh4:
        for fld in ("survivors", "dropped"):
            want = nh4[m]["verdict"][fld]
            for tag, res in (("main", main_res), ("contrast", con_res)):
                got = (res.get(m) or {}).get("verdict", {}).get(fld)
                if got != want:
                    fails.append(f"{tag} {m}/{fld}: {got} != nh4 {want}")
    if sorted(main_tap.anchors) != sorted(con_tap.anchors):
        fails.append(
            "display_anchor 좌표 로그 본 런 != 대조 런 "
            f"(main={len(main_tap.anchors)} con={len(con_tap.anchors)})"
        )
    if not main_tap.anchors:
        fails.append("display_anchor 성공 로그 0건 — 배선 실행 증거 부재")

    # ── 게이트 2: 대조 런 zoom md5 == nh4 정본 전건 ─────────────────────────
    md5_mismatch: list[str] = []
    main_cards_total = 0
    for m in nh4:
        cert = {k: v for k, v in (nh4[m].get("pngMd5") or {}).items()
                if k.startswith("zoom_")}
        con = _zoom_md5_dir(CONTRAST / "sweep_cards" / m)
        main_cards_total += len(_zoom_md5_dir(EVID / "sweep_cards" / m))
        for k in sorted(set(con) | set(cert)):
            if con.get(k) != cert.get(k):
                md5_mismatch.append(
                    f"{m}/{k}: contrast={con.get(k)} nh4={cert.get(k)}"
                )
    if md5_mismatch:
        fails.append(f"대조 런 md5 != nh4 정본 ({len(md5_mismatch)}건)")

    # ── 게이트 3: 라벨 라운드트립 표 (본 런) ────────────────────────────────
    eff = _probe_eff()
    table: list[dict] = []
    n_cards_gated = 0
    for m in nh4:
        con_by_crit = {
            c["criterion"]: c for c in _confirmed_cards(con_res.get(m) or {})
        }
        for c in _confirmed_cards(main_res.get(m) or {}):
            crit = c["criterion"]
            frz = _crit_to_freeze(crit, nh4[m]["freezes"])
            if frz is None:
                fails.append(f"{m}/{crit}: nh4 freezes 에 대응 없음")
                continue
            old = con_by_crit.get(crit)
            if old is None:
                fails.append(f"{m}/{crit}: 대조 런에 같은 카드 없음")
                continue
            row = {
                "motion": m, "rid": frz["rid"], "criterion": crit,
                "freezeUserSec": frz["userSec"], "freezeRefSec": frz["refSec"],
                "effUser": eff[m]["user"], "effRef": eff[m]["ref"],
                "oldUserSec": old.get("userVideoSec"),
                "oldRefSec": old.get("refVideoSec"),
                "newUserSec": c.get("userVideoSec"),
                "newRefSec": c.get("refVideoSec"),
            }
            # 구 라벨 교차검증 — nh4 정본 attached 값과 일치 (전이 사슬 보강).
            nh4_old = {
                x["criterion"]: x
                for x in _confirmed_cards(nh4.get(m) or {})
            }.get(crit)
            if nh4_old is not None:
                for k_new, k_nh4 in (
                    ("oldUserSec", "userVideoSec"), ("oldRefSec", "refVideoSec"),
                ):
                    a, b = row[k_new], nh4_old.get(k_nh4)
                    if (a is None) != (b is None) or (
                        a is not None and abs(a - b) > 1e-9
                    ):
                        fails.append(
                            f"{m}/{crit} {k_new}: 대조 런 {a} != nh4 정본 {b}"
                        )
            # 라운드트립 게이트 — 측별 1.5프레임/eff (docstring 근거).
            checks = []
            for side, new_v, frz_v, e in (
                ("user", row["newUserSec"], frz["userSec"], eff[m]["user"]),
                ("ref", row["newRefSec"], frz["refSec"], eff[m]["ref"]),
            ):
                if new_v is None:
                    checks.append({"side": side, "skipped": "라벨 부재"})
                    continue
                tol = TOL_FRAMES / e
                delta = abs(new_v - frz_v)
                ok = delta <= tol
                clamped = False
                if side == "user" and not ok:
                    # 경계 케이스 (본 스윕 실측 peterpan) — freeze 초가 클립 끝
                    # 너머 (freeze 6.444s vs 클립 62프레임/eff=6.22s). 운영
                    # override 는 마지막 프레임으로 clamp 하므로 (fault_zoom
                    # u_idx = min(round(sec x eff x k), video_n-1), k 실측 1.0
                    # 전 동작) 라벨의 정답 = **표시된 마지막 프레임의 실초**.
                    # 종전 ÷9.0 라벨(6.778s)은 6.22s 클립 밖의 불가능한 초를
                    # 가리켰다 — freeze 초 자체가 클립 밖인 것은 freeze
                    # 타임베이스 상류 의제 (이 수리 밖, SUMMARY 한계 박제).
                    # 이 분기는 clamp 성립 시에만 좁게 통과 — 허용치 완화 아님.
                    last_idx = eff[m]["userVideoN"] - 1
                    if (round(frz_v * e) >= last_idx
                            and abs(new_v - last_idx / e) <= 1e-6):
                        ok = True
                        clamped = True
                        notes.append(
                            f"{m}/{crit} user: freeze {frz_v:.3f}s > 클립 끝 "
                            f"{(eff[m]['userVideoN']) / e:.3f}s — 마지막 프레임"
                            f"({last_idx}/{e:.4f}={new_v:.3f}s) clamp 라벨"
                        )
                checks.append({
                    "side": side, "delta": round(delta, 4),
                    "tol": round(tol, 4), "ok": ok,
                    **({"clampedAtClipEnd": True} if clamped else {}),
                })
                if not ok:
                    fails.append(
                        f"{m}/{crit} {side}: |{new_v:.3f}-{frz_v:.3f}|="
                        f"{delta:.3f} > {tol:.3f}"
                    )
                # 표시 인덱스 불변 교차검증 — 신/구가 같은 인덱스의 다른 분모.
                old_v = row["oldUserSec" if side == "user" else "oldRefSec"]
                if old_v is not None and (
                    round(new_v * e) != round(old_v * 9.0)
                ):
                    fails.append(
                        f"{m}/{crit} {side}: 표시 인덱스 이동 "
                        f"round({new_v:.4f}x{e:.4f})={round(new_v * e)} != "
                        f"round({old_v:.4f}x9)={round(old_v * 9.0)}"
                    )
            row["checks"] = checks
            table.append(row)
            n_cards_gated += 1
    if n_cards_gated == 0:
        fails.append("라운드트립 게이트 카드 0장 — 스윕 산출 이상")

    # ── 게이트 4: pytest 기준선 ─────────────────────────────────────────────
    env = dict(os.environ)
    env["PYTHONPATH"] = "backend/tests"
    pt = subprocess.run(
        [str(_REPO / "backend/.venv/bin/python"), "-m", "pytest", "-q",
         "backend/tests"],
        capture_output=True, text=True, cwd=str(_REPO), env=env,
    )
    tail = "\n".join(pt.stdout.splitlines()[-40:])
    (EVID / "pytest_baseline_tail.log").write_text(tail + "\n")
    mfail = re.search(r"(\d+) failed", pt.stdout)
    mpass = re.search(r"(\d+) passed", pt.stdout)
    n_failed = int(mfail.group(1)) if mfail else -1
    n_passed = int(mpass.group(1)) if mpass else -1
    if n_failed != PYTEST_BASELINE_FAILED:
        fails.append(
            f"pytest failed {n_failed} != 기준선 {PYTEST_BASELINE_FAILED}"
        )

    # ── 게이트 5: 산식 5파일 diff 0 (수리 커밋 범위) ────────────────────────
    gd = subprocess.run(
        ["git", "diff", "--name-only", REPAIR_BASE, REPAIR_HEAD, "--",
         *SCORING_FILES],
        capture_output=True, text=True, cwd=str(_REPO),
    )
    if gd.stdout.strip():
        fails.append(f"산식 파일 diff 존재: {gd.stdout.strip()}")

    # ── 게이트 6: 수리 diff 추가 라인 동작명/분석 ID 리터럴 0 ───────────────
    diff = subprocess.run(
        ["git", "diff", REPAIR_BASE, REPAIR_HEAD],
        capture_output=True, text=True, cwd=str(_REPO),
    ).stdout
    added = [
        ln[1:] for ln in diff.splitlines()
        if ln.startswith("+") and not ln.startswith("+++")
    ]
    lit_hits = [
        f"{lit}: {ln.strip()[:90]}"
        for ln in added for lit in BRANCH_LITERALS if lit in ln
    ]
    if lit_hits:
        fails.append(f"수리 diff 추가 라인 리터럴 {len(lit_hits)}건")

    # ── 게이트 7: Gemini 실호출 0 (스텁 계수) ───────────────────────────────
    if eye_stub_calls <= 0:
        fails.append(f"눈 스텁 계수 이상: {eye_stub_calls} (스텁 미경유 의심)")

    # ── 산출 정리 ───────────────────────────────────────────────────────────
    for src, dst in (
        (EVID / "sweep_verdict.json", EVID / "sweep_verdict_main.json"),
        (CONTRAST / "sweep_verdict.json", CONTRAST / "sweep_verdict_shim.json"),
    ):
        if src.exists():
            shutil.move(str(src), str(dst))
    (EVID / "label_check.json").write_text(json.dumps({
        "pass": not fails,
        "fails": fails,
        "notes": notes,
        "labelTable": table,
        "cardsGated": n_cards_gated,
        "cardsTotalMain": main_cards_total,
        "md5Mismatch": md5_mismatch,
        "displayAnchorLogs": sorted(main_tap.anchors),
        "displayAnchorDrops": main_tap.drops,
        "alignBakeMissLogs": main_tap.misses,
        "pytest": {"failed": n_failed, "passed": n_passed,
                   "baselineFailed": PYTEST_BASELINE_FAILED},
        "repairRange": f"{REPAIR_BASE}..{REPAIR_HEAD}",
        "branchLiteralHits": lit_hits,
        "eyeStubCalls": eye_stub_calls,
        "tolFramesPerEff": TOL_FRAMES,
    }, ensure_ascii=False, indent=1))

    print(f"\nLABEL GATE {'PASS' if not fails else 'FAIL'} "
          f"cards={n_cards_gated} md5Δ={len(md5_mismatch)} "
          f"pytest={n_failed}f/{n_passed}p eyeStub={eye_stub_calls}")
    for row in table:
        print(f"  {row['motion']}/{row['criterion']}: "
              f"u {row['oldUserSec']:.3f}→{row['newUserSec']:.3f} "
              f"(freeze {row['freezeUserSec']:.3f}) | r "
              f"{(row['oldRefSec'] or -1):.3f}→{(row['newRefSec'] or -1):.3f} "
              f"(freeze {row['freezeRefSec']:.3f})")
    for f in fails:
        print(f"  FAIL: {f}")
    for n in notes:
        print(f"  note: {n}")
    return 0 if not fails else 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
