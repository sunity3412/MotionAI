#!/usr/bin/env python3
"""fresh doc 정답표 대조 + 승인 무회귀 로컬 드라이버 (quick-260811-kpo, Task 2).

**배선한 운영 함수를 그대로** 구동한다 (U6 교훈 — 하네스가 다른 함수를 부르면
배선 검증이 아니다): compare_align.build_align(P35 트랙 리플레이 infer_fn 주입,
GPU 무관 — build_align 의 문서화된 주입 지점) → compare_render.build_timeline
→ pipeline._run_gated_card_inherit **동일 함수 import** (S3 put/presign +
Firestore 부착만 스텁 — 캡처해 카드 PNG 를 evidence/ 에 산출).

stages:
  --fetch     Firestore doc/ref report + S3 영상/음성 → 세션 scratchpad 캐시
  --run       운영 헬퍼 구동 → evidence/cards/*.png + verdict 캡처
  --approved  승인 코퍼스 무회귀 (ii0 스윕 등가성 — probes.log/poles.json 정본)
  --check     전 단계 실행 + 판정 라인 출력 (자동 게이트 grep 대상)

주의: scratchpad 는 휘발 — 재료 정본은 리포(.planning P35 data + ii0 probes.log)
와 S3. 캐시 부재 시 --fetch 가 재구성한다. Gemini 키는 SSM 에서 env 주입
(키 값 로그 금지 — T-kpo-01).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
import subprocess
import sys
import types

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "backend" / "shared" / "python"))
sys.path.insert(0, str(_REPO / "backend" / "functions" / "pipeline"))

# ── 좌표 (PLAN.md — 재탐색 불요) ─────────────────────────────────────────────
UID = "fvcNXzEqKjgqVxRPVSj1iwFnIpn2"
AID = "p34fresh1786363530"
MOTION_ID = "ref-pdshape"
BUCKET = "sunity-motion-pilot-videos"
USER_VIDEO_KEY = "uploads/csKWYvI3WCPYPysNQ9KkWecaUvq1/127a2a90c1d74c62ad61270eb3fe5625.mp4"
REF_VIDEO_KEY = "reference/ref-pdshape.mp4"
AUDIO_KEYS = {
    f"r{n:02d}": (
        f"results/{UID}/{AID}/coach_audio_r{n:02d}:angle_vs_reference__{j}.mp3"
    )
    for n, j in enumerate(
        ["left_elbow", "right_elbow", "right_shoulder", "left_hip", "left_knee"]
    )
}

SP = pathlib.Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "8a8d6013-0acb-4e98-83e5-71bde7ca7d9d/scratchpad"
) / "fresh"
DATA = _REPO / ".planning/phases/35-server-rendered-comparison-video/data"
II0 = _REPO / ".planning/quick/260811-ii0-card-gates-5"
EV = _HERE / "evidence"

DOC = SP / "doc.json"
REFMOTION = SP / "refmotion.json"
VIDEOS = {"user": SP / "user.mp4", "ref": SP / "ref.mp4"}
AUDIO_DIR = SP / "audio"
ALIGN_WORK = SP / "align_work"
RENDER_WORK = SP / "render"

log = logging.getLogger("verify_local")


def _s3_client():
    import boto3

    session = boto3.Session(profile_name=os.environ.get("AWS_PROFILE", "sunity-motion"))
    return session.client("s3", region_name="ap-northeast-2")


def _ensure_gemini_key() -> None:
    """SSM → GEMINI_API_KEY env (미설정 시). 키 값은 절대 로그하지 않는다."""
    if os.environ.get("GEMINI_API_KEY", "").strip():
        return
    import boto3

    session = boto3.Session(profile_name=os.environ.get("AWS_PROFILE", "sunity-motion"))
    ssm = session.client("ssm", region_name="ap-northeast-2")
    val = ssm.get_parameter(Name="/sunity/motion/gemini-api-key", WithDecryption=True)[
        "Parameter"
    ]["Value"]
    os.environ["GEMINI_API_KEY"] = val
    print(f"GEMINI_API_KEY injected (len={len(val)})")


def fetch() -> None:
    SP.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    if not DOC.exists() or not REFMOTION.exists():
        from sunity_shared import firestore_admin as fa

        doc = (
            fa._db().collection("users").document(UID)  # noqa: SLF001
            .collection("analyses").document(AID).get().to_dict()
        )
        DOC.write_text(json.dumps({"result": doc["result"]}))
        ref = fa.get_reference_motion(MOTION_ID)
        REFMOTION.write_text(
            json.dumps({"referenceKeypointReport": ref["referenceKeypointReport"]})
        )
        print(f"fetched doc + refmotion -> {SP}")
    s3 = _s3_client()
    for which, key in (("user", USER_VIDEO_KEY), ("ref", REF_VIDEO_KEY)):
        p = VIDEOS[which]
        if not p.exists():
            s3.download_file(BUCKET, key, str(p))
            print(f"fetched {which} video {p.stat().st_size} bytes")
    for rid, key in AUDIO_KEYS.items():
        p = AUDIO_DIR / f"{rid}.mp3"
        if not p.exists():
            s3.download_file(BUCKET, key, str(p))
    print("fetch OK")


def _replay_infer(p35: dict):
    """P35 align 트랙 리플레이 infer_fn — 프레임 수 정확 일치 강제 (fail-closed).

    같은 원본 영상(md5 일치 — ii0 08-08 실증) + RTMW_DETERMINISTIC 세대 트랙이라
    Pod 재추론과 등가. 반올림(kp 4자리/score 3자리) 오차만 존재 — 로컬 근사임을
    출력에 명시하고 최종 판정은 Task 3 Pod 실증이 맡는다.
    """
    tracks = {}
    for side in ("user", "ref"):
        F = int(p35[f"{side}Frames"])
        W, H = p35[f"{side}Size"]
        kp = np.asarray(p35[f"{side}Kp"], dtype=float).reshape(F, 17, 2)
        sc = np.asarray(p35[f"{side}Score"], dtype=float).reshape(F, 17)
        tracks[F] = (kp * np.array([W, H], dtype=float), sc, W, H)

    def infer_fn(frames):
        got = tracks.get(len(frames))
        if got is None:
            raise RuntimeError(
                f"replay 프레임 수 불일치: {len(frames)} not in {sorted(tracks)}"
            )
        return got

    return infer_fn


class _S3Stub:
    """put_object 를 로컬 저장으로 대체 — 카드 실물 + 기계 눈 원장 산출.

    /eye/ 키(belle 08-11 추가 지시 — Phase 22 플라이휠 씨앗 보존)는
    evidence/eye_ledger/ 로, 나머지(카드 PNG)는 evidence/cards/ 로 라우팅.
    scratchpad 는 휘발이라 보존으로 안 침 — evidence/ 는 리포 커밋 대상.
    """

    def __init__(self, cards_dir: pathlib.Path, eye_dir: pathlib.Path):
        self.cards_dir = cards_dir
        self.eye_dir = eye_dir
        self.keys: list[str] = []

    def put_object(self, *, Bucket, Key, Body, ContentType):  # noqa: N803
        self.keys.append(Key)
        outdir = self.eye_dir if "/eye/" in Key else self.cards_dir
        outdir.mkdir(parents=True, exist_ok=True)
        p = outdir / pathlib.Path(Key).name
        p.write_bytes(Body if isinstance(Body, (bytes, bytearray)) else Body.read())


def run() -> dict:
    fetch()
    _ensure_gemini_key()
    import app  # backend/functions/pipeline — 운영 모듈 그대로
    from sunity_shared.analysis import compare_align, compare_render

    doc = json.loads(DOC.read_text())
    res = doc["result"]
    records = (res.get("deductionBreakdown") or {}).get("records") or []
    ref_report = json.loads(REFMOTION.read_text())["referenceKeypointReport"]

    # ① align — 운영과 같은 build_align (리플레이 infer 주입)
    ALIGN_WORK.mkdir(parents=True, exist_ok=True)
    p35 = json.loads((DATA / "pdshapefault" / "align.json").read_text())
    align = compare_align.build_align(
        VIDEOS["user"], VIDEOS["ref"], records, ALIGN_WORK,
        infer_fn=_replay_infer(p35),
    )
    q_ok, q_lines = compare_align.align_quality(align)
    print(f"align_quality: {'PASS' if q_ok else 'FAIL'}")

    # ② 폴 감지 + 30fps 프레임 (운영 render 와 같은 함수·같은 캐시 규칙)
    RENDER_WORK.mkdir(parents=True, exist_ok=True)
    tag = f"{int(compare_render.FPS_OUT)}_{compare_render.PANEL_H}"
    udir, rdir = RENDER_WORK / f"u{tag}", RENDER_WORK / f"r{tag}"
    compare_render.extract_frames(VIDEOS["user"], udir)
    compare_render.extract_frames(VIDEOS["ref"], rdir)
    poles = {
        "user": compare_render._detect_pole(udir, align, "user"),  # noqa: SLF001
        "ref": compare_render._detect_pole(rdir, align, "ref"),  # noqa: SLF001
    }
    print(f"poles: user={poles['user']} ref={poles['ref']}")

    # ③ freezes — 운영 build_timeline 그대로 (overrides 없음 = 운영 render 호출 미러)
    doc_like = {"result": res}
    _warp, freezes, excluded = compare_render.build_timeline(
        doc_like, AUDIO_DIR, None, align, poles, None, None,
    )
    report = {
        # render 리포트와 같은 매핑 (compare_render.render 후반 — userSec/refSec/pairSrc)
        "freezes": [
            {"rid": fz["rid"], "joint": fz["joint"], "userSec": fz["ut"],
             "refSec": round(fz["rt"], 2), "pairSrc": fz["pair_src"]}
            for fz in freezes
        ],
        "excludedFreezes": excluded,
    }
    for f in report["freezes"]:
        print(f"FREEZE {f['rid']} joint={f['joint']} src={f['pairSrc']} "
              f"u={f['userSec']:.3f} r={f['refSec']:.2f}")

    # ④ 운영 헬퍼 그대로 — S3/Firestore 만 스텁 (부착 payload 캡처)
    cards_dir = EV / "cards"
    eye_dir = EV / "eye_ledger"
    cards_dir.mkdir(parents=True, exist_ok=True)
    eye_dir.mkdir(parents=True, exist_ok=True)
    for old in cards_dir.glob("*.png"):
        old.unlink()
    for old in list(eye_dir.glob("*.png")) + list(eye_dir.glob("*.json")):
        old.unlink()
    s3_stub = _S3Stub(cards_dir, eye_dir)
    attached: dict = {}

    def _capture_update(uid, analysis_id, comparisons, status):
        attached["uid"] = uid
        attached["analysisId"] = analysis_id
        attached["status"] = status
        attached["comparisons"] = comparisons

    orig_s3, orig_signed = app._s3, app._signed_get  # noqa: SLF001
    orig_update = app.firestore_admin.update_analysis_fault_zoom
    app._s3 = s3_stub
    app._signed_get = lambda bucket, key: f"stub://{key}"
    app.firestore_admin.update_analysis_fault_zoom = _capture_update
    try:
        profile = types.SimpleNamespace(category=None, motion_id=MOTION_ID)
        app._run_gated_card_inherit(
            result=res,
            report=report,
            align=align,
            render_workdir=RENDER_WORK,
            user_video_path=str(VIDEOS["user"]),
            reference_video_path=str(VIDEOS["ref"]),
            user_report=res.get("keypointReport"),
            ref_report=ref_report,
            profile=profile,
            existing_comparisons=res.get("faultZoomComparisons") or [],
            uid=UID,
            analysis_id=AID,
            bucket=BUCKET,
        )
    finally:
        app._s3, app._signed_get = orig_s3, orig_signed
        app.firestore_admin.update_analysis_fault_zoom = orig_update

    out = {
        "freezes": report["freezes"],
        "excluded": [dict(e) for e in excluded],
        "alignQuality": q_ok,
        "attached": {
            "status": attached.get("status"),
            "comparisons": [
                {k: v for k, v in c.items()}
                for c in (attached.get("comparisons") or [])
            ],
        },
        "s3Keys": s3_stub.keys,
    }
    (EV / "run_verdict.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"cards saved: {sorted(p.name for p in cards_dir.glob('*.png'))}")
    return out


def approved() -> dict:
    """승인 코퍼스 무회귀 — ii0 스윕 등가성 (probes.log + poles.json 정본).

    joint-scope 정지에 card_gates(이식본, 확정 임계)를 적용해 9/9 생존을 재현.
    align-peak 정지는 비구속 (정보 행). 임계 완화 금지 — 죽으면 이식 결함.
    """
    import re

    from sunity_shared.analysis import card_gates as cg

    txt = (DATA / "README.md").read_text(encoding="utf-8")
    active = set(re.findall(r"^\| (\w+) \| [^|]* \| 활성 렌더 슬롯", txt, flags=re.M))
    poles = json.loads((II0 / "sweep_out" / "poles.json").read_text())

    stops: dict[str, list[dict]] = {}
    cur = None
    for line in (II0 / "probes.log").read_text().splitlines():
        mm = re.match(r"== PROBE (\w+) ==", line)
        if mm:
            cur = mm.group(1)
            stops[cur] = []
            continue
        mp = re.match(
            r"PROBE (r\d+) joint=(\S+) src=(\S+) ut=([\d.]+) rt=([\d.]+)", line)
        if mp and cur:
            stops[cur].append({
                "rid": mp.group(1), "joint": mp.group(2), "src": mp.group(3),
                "ut": float(mp.group(4)), "rt": float(mp.group(5)),
            })

    rows = []
    n_bind = n_hold = n_pair = n_peak = 0
    for m in sorted(stops):
        align_p = DATA / m / "align.json"
        if not align_p.exists():
            continue
        align = json.loads(align_p.read_text())
        urep = cg.align_to_report(align, "user")
        has_ref = "refKp" in align
        rrep = cg.align_to_report(align, "ref") if has_ref else None
        for st in stops[m]:
            scope = "peak" if st["src"] == "align-peak" else "joint"
            binding = (m in active) and scope == "joint"
            gj = cg.crit_joint(st["joint"])
            u_idx = min(round(st["ut"] * float(align["fps"])), int(urep["frames"]) - 1)
            hold = cg.hold_gate(urep, u_idx, gj)
            row = {"motion": m, "rid": st["rid"], "joint": st["joint"],
                   "src": st["src"], "scope": scope, "binding": binding,
                   "hold_pass": hold.passed, "hold_speed": hold.speed_dps}
            if rrep is not None:
                r_idx = min(round(st["rt"] * float(align["fps"])),
                            int(rrep["frames"]) - 1)
                pm = poles.get(m) or {}
                pu = (pm.get("user") or {}).get("x_norm")
                pr = (pm.get("ref") or {}).get("x_norm")
                usize, rsize = tuple(align["userSize"]), tuple(align["refSize"])
                pair = cg.pair_gate(
                    urep, u_idx, rrep, r_idx, pu, pr,
                    user_size=usize, ref_size=rsize,
                    user_torso_px=cg.torso_px_median(urep, usize),
                    ref_torso_px=cg.torso_px_median(rrep, rsize),
                )
                row.update({"pair_pass": pair.passed, "pose_dist": pair.pose_dist,
                            "basis_k": pair.basis_k, "pole_diff": pair.pole_diff})
            else:
                row.update({"pair_pass": None})
            rows.append(row)
            if binding:
                n_bind += 1
                n_hold += 1 if row["hold_pass"] else 0
                n_pair += 1 if row.get("pair_pass") else 0
            elif scope == "peak" and m in active:
                n_peak += 1
            sp = (f"{row['hold_speed']:.0f}d/s" if row["hold_speed"] is not None
                  else "unmeas")
            print(f"{m} {st['rid']} {st['joint']:<18} scope={scope} "
                  f"hold={'PASS' if row['hold_pass'] else 'FAIL'}({sp}) "
                  f"pair={row.get('pair_pass')}"
                  f"{'' if binding else ' (비구속)'}")
    summary = {"binding": n_bind, "hold": n_hold, "pair": n_pair, "peak": n_peak,
               "rows": rows}
    (EV / "approved_verdict.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"[approved] joint-scope hold {n_hold}/{n_bind} pair {n_pair}/{n_bind} "
          f"peak(비구속) {n_peak}")
    return summary


def check() -> int:
    out = run()
    ap = approved()
    fails = 0

    comps = out["attached"]["comparisons"]
    confirmed = [c for c in comps if c.get("tier") == "confirmed"]
    joints = [c.get("joint") for c in confirmed]

    knee = next((c for c in confirmed if c.get("joint") == "left_knee"), None)
    if knee is not None:
        print(f"left_knee CARD uSec={knee.get('userVideoSec')} "
              f"rSec={knee.get('refVideoSec')} uIdx={knee.get('userFrameIdx')} "
              f"rIdx={knee.get('refFrameIdx')}")
    else:
        print("left_knee MISSING — 정답표 위반")
        fails += 1

    if not any(c.get("joint") == "left_hip" for c in confirmed):
        print("left_hip ABSENT")
    else:
        print("left_hip PRESENT — 정답표 위반")
        fails += 1

    elbow = next((c for c in confirmed if c.get("joint") == "left_elbow"), None)
    if elbow is not None:
        print(f"left_elbow SURVIVES attribution={elbow.get('attribution')}")
        if elbow.get("attribution") != "pole_proximity":
            print("left_elbow attribution MISSING — 정답표 3항 미달 (박제)")
            fails += 1
    else:
        print("left_elbow MISSING — 정답표 위반")
        fails += 1

    if ap["binding"] == 9 and ap["hold"] == 9 and ap["pair"] == 9:
        print("approved 9/9 (hold+pair) + peak 비구속", ap["peak"])
    else:
        print(f"approved REGRESSION hold {ap['hold']}/{ap['binding']} "
              f"pair {ap['pair']}/{ap['binding']} — 이식 결함 의심")
        fails += 1

    print(f"confirmed joints: {joints}")
    print(f"CHECK {'PASS' if fails == 0 else f'FAIL({fails})'}")
    return 1 if fails else 0


def main() -> int:
    apr = argparse.ArgumentParser()
    apr.add_argument("--fetch", action="store_true")
    apr.add_argument("--run", action="store_true")
    apr.add_argument("--approved", action="store_true")
    apr.add_argument("--check", action="store_true")
    args = apr.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    EV.mkdir(exist_ok=True)
    if args.fetch:
        fetch()
    if args.run:
        run()
    if args.approved:
        approved()
    if args.check:
        return check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
