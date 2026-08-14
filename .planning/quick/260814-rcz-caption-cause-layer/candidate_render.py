#!/usr/bin/env python3
"""후보 2건 render-only 재현 + 마크 관측 (quick-260814-rcz Task 2).

ehz `discover_sweep.py` 사본을 **렌더만** 하도록 축약했다. 스캔·짝 유도·기계 눈
재실행은 전부 제거 — 발굴은 이미 끝났고 좌표는 ehz `evidence/{motion}/
candidates.json`(및 eye_verdicts.json)에 확정 기록돼 있다. 이 파일이 하는 일은
그 좌표를 **그대로 읽어** 운영 헬퍼(`app._run_gated_card_inherit`)로 다시 그리고,
mark_gate_sweep 과 **같은 관측 필드**를 남기는 것뿐이다.

대상 2건 (belle 08-14 판정 대상):
  · pdshapefault cand17B — 왼팔꿈치 u16.4667 / r15.1333  → belle **채택**(조건부)
  · powerspin    cand01E — 왼어깨   u0.4667  / r0.7333   → belle **각도 표기 반려**

Gemini 실호출 0 (T-rcz 제약): `card_gates.machine_eye` 를 **ehz 실측 판정 재생**
스텁으로 교체한다. 지어낸 값이 아니라 ehz 원장에 기록된 그 판정(observed/limb/
confidence/reason)을 그대로 돌려준다 — 재렌더가 눈 판정을 다시 사지 않게 하면서
verdict 는 원본과 같아진다. 재생 실패(원장에 없는 조회)는 fail-closed.

자기검증: 카드 md5 == ehz `render_verdict.json` md5Run1 (채택분 무손상 증거).
S3 읽기만(캐시 재사용), Firestore 읽기만, Pod 무접촉, 채점 무접촉.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import math
import os
import pathlib
import shutil
import sys
import types

_HERE = pathlib.Path(__file__).resolve().parent
_EHZ = _HERE.parent / "260814-ehz-5"
_EHZ_EV = _EHZ / "evidence"

EVID = _HERE / "evidence"
SCRATCH = pathlib.Path(
    os.environ.get("RCZ_SCRATCH")
    or "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
      "2a78a76a-92ce-42f8-b5d0-18c558c3d196/scratchpad"
)
CACHE_ROOT = SCRATCH / "ehz_sweep"   # ehz 가 이미 받아 둔 소스 (S3 재다운로드 0)

# (motion, rid, cid) — 정확히 2건. 좌표는 ehz 원장에서 읽고 여기 하드코딩 0.
TARGETS = (("pdshapefault", "r00", "cand17B"), ("powerspin", "r02", "cand01E"))

# 마크 게이트(Task 3) 이식 **후** 기대되는 변화 선언.
#   · cand17B = belle 채택분 → md5 **동일**해야 한다 (무손상 1급)
#   · cand01E = belle 반려분 → md5 **달라져야** 하고, 그 차이는 V 소멸이어야 한다
# 이 선언이 없으면 "md5 가 달라졌다"가 회귀인지 의도인지 산출물에서 구분되지
# 않는다. `RCZ_EXPECT_GATE=0` 으로 두면 패치 전(무게이트) 기대로 되돌아간다.
EXPECT_CHANGED_AFTER_GATE = {"cand01E"}
EXPECT_GATE = os.environ.get("RCZ_EXPECT_GATE", "1") == "1"

log = logging.getLogger("candidate_render")


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


os.environ.setdefault("GEMINI_API_KEY", "rcz-replay-stub")
ds = _load_module("discover_sweep", _EHZ / "discover_sweep.py")
ds._CACHE_ROOT = CACHE_ROOT  # noqa: SLF001 - --cache-root 대체 (구 세션 UUID 금지)

# mark_gate_sweep 의 관측 tap 재사용 (관측 정의 1벌 — 재발명 0).
mgs = _load_module("mark_gate_sweep_tap", _HERE / "mark_gate_sweep.py")


# ── ehz 실측 판정 재생 스텁 (Gemini 실호출 0) ───────────────────────────────
class _ReplayEye:
    """ehz eye_verdicts.json 의 그 판정을 그대로 재생. 계수는 따로 센다."""

    def __init__(self, verdicts: dict, key: str):
        self.v = verdicts[key]
        self.calls = 0
        self.served: list[str] = []

    def __call__(self, frame_rgb, joint_xy_px, claim, *, api_key=None,
                 expected_limb=None, crop_px=360, **_kw):
        from sunity_shared.analysis import card_gates as cg

        self.calls += 1
        # claim 으로 어느 측 판정인지 고른다 (uClaim/rClaim 이 원장에 있다).
        side = "user" if claim == self.v.get("uClaim") else (
            "ref" if claim == self.v.get("rClaim") else None)
        if side is None:  # 원장에 없는 조회 = fail-closed (지어내지 않는다)
            self.served.append(f"unknown_claim:{claim}")
            return {"observed": None, "limb": None, "match": False,
                    "confidence": 0.0, "reason": "rcz replay: 원장 미보유",
                    "crop": cg.mark_crop(frame_rgb, joint_xy_px,
                                         crop_px=crop_px)[0]}
        rec = self.v[side]
        self.served.append(f"{side}:{rec['observed']}")
        crop, _ = cg.mark_crop(frame_rgb, joint_xy_px, crop_px=crop_px)
        return {"observed": rec["observed"], "limb": rec["limb"],
                "match": rec["match"], "confidence": rec["confidence"],
                "reason": f"rcz replay(ehz 실측): {rec['reason']}",
                "crop": crop}


def _md5_dir(d: pathlib.Path) -> dict[str, str]:
    return {p.name: hashlib.md5(p.read_bytes()).hexdigest()
            for p in sorted(d.glob("*.png"))}


def main() -> int:
    assert "260814-rcz" in str(EVID), f"EVID 경로 이상: {EVID}"
    out_root = EVID / "candidate_cards"
    out_root.mkdir(parents=True, exist_ok=True)

    import app  # noqa: F401 - 운영 모듈 그대로
    from sunity_shared import firestore_admin as fs_admin
    from sunity_shared.analysis import card_gates as cg
    from sunity_shared.analysis import fault_zoom as fz

    ds._ensure_firebase_env()  # noqa: SLF001

    results: dict[str, dict] = {}
    fails: list[str] = []
    gemini_real_calls = 0

    for m, rid, cid in TARGETS:
        key = f"{rid}/{cid}"
        verdicts = json.loads((_EHZ_EV / m / "eye_verdicts.json").read_text())
        cert = json.loads(
            (_EHZ_EV / m / "render_verdict.json").read_text())["cards"][key]
        v = verdicts[key]
        print(f"══ RENDER {m} {key} u={v['uSec']} r={v['rSec']} ══")

        ctx = ds.mount(m)
        ref_report = json.loads(
            ctx.paths.refmotion.read_text())["referenceKeypointReport"]
        report = {"freezes": [{
            "rid": rid, "joint": v["joint"],
            "userSec": float(v["uSec"]), "refSec": float(v["rSec"]),
            "pairSrc": "discovery",
        }], "excludedFreezes": []}

        tmp = out_root / f"_{m}_{rid}_{cid}"
        if tmp.exists():
            shutil.rmtree(tmp)
        stub = ds._S3Stub(tmp, tmp / "eye_ledger")  # noqa: SLF001
        eye = _ReplayEye(verdicts, key)
        tap = mgs._AngleTap(fz)  # noqa: SLF001
        handler = mgs._TapHandler(tap)  # noqa: SLF001
        cap = ds._LogCapture()  # noqa: SLF001
        attached: dict = {}

        def _cap_update(uid, analysis_id, comparisons, status, _sink=attached):
            _sink["comparisons"] = comparisons
            _sink["status"] = status

        orig_eye = cg.machine_eye
        orig_s3, orig_signed = app._s3, app._signed_get  # noqa: SLF001
        orig_update = fs_admin.update_analysis_fault_zoom
        cg.machine_eye = eye
        app._s3 = stub
        app._signed_get = lambda bucket, k: f"stub://{k}"
        fs_admin.update_analysis_fault_zoom = _cap_update
        app.firestore_admin.update_analysis_fault_zoom = _cap_update
        tap.install()
        logging.getLogger().addHandler(handler)
        logging.getLogger().addHandler(cap)
        try:
            profile = types.SimpleNamespace(
                category=ds.SWEEP_CATEGORY.get(m), motion_id=ctx.motion_id)
            app._run_gated_card_inherit(  # noqa: SLF001
                result=ctx.res, report=report, align=ctx.align,
                render_workdir=ctx.paths.render,
                user_video_path=str(ctx.paths.user),
                reference_video_path=str(ctx.paths.ref),
                user_report=ctx.res.get("keypointReport"),
                ref_report=ref_report, profile=profile,
                existing_comparisons=[],
                uid="rcz-candidate",
                analysis_id=f"ehz-{m}-{rid}-{cid}",  # ehz 와 동일 (md5 대조용)
                bucket=ds.BUCKET,
            )
        finally:
            logging.getLogger().removeHandler(cap)
            logging.getLogger().removeHandler(handler)
            tap.restore()
            cg.machine_eye = orig_eye
            app._s3, app._signed_get = orig_s3, orig_signed
            fs_admin.update_analysis_fault_zoom = orig_update
            app.firestore_admin.update_analysis_fault_zoom = orig_update

        got_md5 = _md5_dir(tmp)
        want_md5 = cert["md5Run1"]
        should_change = EXPECT_GATE and cid in EXPECT_CHANGED_AFTER_GATE
        changed = got_md5 != want_md5
        if should_change and not changed:
            fails.append(
                f"{m} {key} md5 가 그대로다 — 게이트가 발동하지 않았다")
        if not should_change and changed:
            fails.append(
                f"{m} {key} md5 != ehz (무손상 위반): now={got_md5} ehz={want_md5}")

        # 최종 카드 배치 (belle 재료 이름 그대로 — ehz 시트와 조인 가능)
        final = []
        for p in sorted(tmp.glob("*.png")):
            dst = out_root / (f"{rid}_{cid}_u{v['uSec']}s_r{v['rSec']}s_"
                              f"{p.name}")
            shutil.copyfile(p, dst)
            final.append(dst.name)

        pay = next((c for c in (attached.get("comparisons") or [])
                    if c.get("criterion")), {})
        rows = []
        for row in tap.rows:
            e = mgs._derive(row)  # noqa: SLF001
            e["motion"] = m
            e["cid"] = cid
            e["A5_deficitDeg"] = pay.get("deficitDeg")
            e["A5_tolerance"] = pay.get("tolerance")
            e["userVideoSec"] = pay.get("userVideoSec")
            e["refVideoSec"] = pay.get("refVideoSec")
            rows.append(e)

        gemini_real_calls += 0  # 스텁 경유 — 실호출 없음
        results[f"{m}/{key}"] = {
            "motion": m, "rid": rid, "cid": cid,
            "uSec": v["uSec"], "rSec": v["rSec"], "joint": v["joint"],
            "belleVerdict": ("채택(조건부 — 캡션 보강)" if cid == "cand17B"
                             else "캐치 유효 / 각도 표기 부적절"),
            "md5": got_md5, "md5Cert": want_md5,
            "md5Match": not changed,
            "expectedChangedByGate": should_change,
            "gateReason": next(
                (line.split("angle_bake=")[-1] for line in cap.lines
                 if "fault_zoom_angle_bake" in line), None),
            "cards": final,
            "eyeReplayCalls": eye.calls, "eyeReplayServed": eye.served,
            "observations": rows,
            "logs": [line for line in cap.lines
                     if "angle_bake" in line or "display_anchor" in line
                     or "card_gates verdict" in line],
        }
        print(f"  md5 {'OK' if got_md5 == want_md5 else 'MISMATCH'} "
              f"eyeReplay={eye.calls} cards={final}")
        for r in rows:
            print(f"  {r['criterion']:<38} {r['verdict']:<20} "
                  f"A1ref={r['A1_refInnerDeg']} A2user={r['A2_userInnerDeg']}")

    (EVID / "candidate_render.json").write_text(json.dumps({
        "selfCheck": {
            "pass": not fails, "fails": fails,
            "geminiRealCalls": gemini_real_calls,
            "eyeMode": "ehz 실측 판정 재생 (지어낸 값 0, 미보유 조회는 fail-closed)",
        },
        "candidates": results,
    }, ensure_ascii=False, indent=1) + "\n")

    print(f"\nCANDIDATE RENDER {'PASS' if not fails else 'FAIL'} "
          f"(Gemini 실호출 {gemini_real_calls})")
    for f in fails:
        print(f"  FAIL: {f}")
    return 0 if not fails else 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
