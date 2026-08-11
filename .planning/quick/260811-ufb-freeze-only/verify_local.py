#!/usr/bin/env python3
"""freeze 전건 일치 + 2회 결정론 + 승인 무회귀 드라이버 (quick-260811-ufb, Task 2).

kpo verify_local.py 적응 이식 (kpo 원본은 kpo 기록 — 무접촉). fetch/replay/
S3·Firestore 스텁/approved 스테이지는 그대로, check() 만 ufb 불변식으로 교체:

  (1) freeze 전건 일치 (LD-1): 방출된 모든 카드의 순간(verdict survivors 의
      @u/r)이 그 분석 report["freezes"] 의 (userSec, refSec)와 전건 일치.
      변형 연산이 없으므로(u_sec/r_sec 덮어쓰기 0 — Task 1 수술) 같은 float 의
      같은 포맷 문자열이 성립해야 한다. peak pass-through 포함.
  (2) 2회 결정론: --run 을 별도 프로세스로 2회 — 카드 목록(joint/tier) + 방출
      순간(survivors/dropped) + 카드 PNG md5 전부 동일. 순간이 다르면 Task 1
      수술 미완 (순간 비결정은 구조상 불가능해졌어야 한다). 눈 flip 으로 생존
      집합이 달라지면 임계 튜닝 없이 원장 박제 후 DETERMINISM FAIL.
  (3) 승인 무회귀: ii0 스윕 등가성 — joint-scope hold 9/9 + pair 9/9 +
      align-peak 비구속 (수술은 판정 함수 무접촉이라 동일해야 함).

주의: 카드 doc 의 userVideoSec 표기는 ÷9.0 라벨 잔존(kpo 유보 3, 무접촉)으로
freeze 실초와 어긋날 수 있다 — 판정 seam 은 helper 가 먹인 순간(verdict 로그
args 캡처)이지 doc 표기가 아니다. doc 표기 값은 기록만 (수리 범위 밖).

stages:
  --fetch      Firestore doc/ref report + S3 영상/음성 → 세션 scratchpad 캐시
  --run        운영 헬퍼 구동 → evidence/cards/*.png + verdict/crop 캡처
  --zero-card  LD-5 관찰 — 드라이버 프로세스 안에서만 hold_gate 전부 FAIL
               monkeypatch (운영 코드 무접촉) → 0장 시 부착 semantics 실물 기록
  --approved   승인 코퍼스 무회귀 (ii0 probes.log/poles.json 정본)
  --check      2회 --run(별도 프로세스) + freeze 일치 + 결정론 + approved

Gemini 키는 SSM 에서 env 주입 (키 값 로그 금지 — T-ufb-01).
"""

from __future__ import annotations

import argparse
import hashlib
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


class _LogCapture(logging.Handler):
    """root 로거 캡처 — verdict args(실 리스트) + fault_zoom_crop 라인.

    판정 seam: app 헬퍼가 로그에 넘긴 args 그대로 (문자열 재파싱 아님) —
    survivors 원소 = "{rid}:{path}@u{u:.3f}/r{r:.2f}" (Task 1 포맷).
    """

    def __init__(self):
        super().__init__(level=logging.INFO)
        self.verdict_args: tuple | None = None
        self.crop_lines: list[str] = []
        self.attach_line: str | None = None

    def emit(self, record):  # noqa: D102
        try:
            msg = record.msg if isinstance(record.msg, str) else ""
            if msg.startswith("card_gates verdict"):
                self.verdict_args = record.args
            elif msg.startswith("fault_zoom_crop"):
                self.crop_lines.append(record.getMessage())
            elif msg.startswith("card_gates 대체 부착 완료"):
                self.attach_line = record.getMessage()
        except Exception:  # noqa: BLE001 - 캡처 실패는 드라이버 문제로만
            pass


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

    /eye/ 키(LD-8 — Phase 22 플라이휠 씨앗 보존)는 evidence/eye_ledger/ 로,
    나머지(카드 PNG)는 evidence/cards/ 로 라우팅. scratchpad 는 휘발이라
    보존으로 안 침 — evidence/ 는 리포 커밋 대상.
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


def run(zero_card: bool = False) -> dict:
    fetch()
    _ensure_gemini_key()
    import app  # backend/functions/pipeline — 운영 모듈 그대로
    from sunity_shared.analysis import card_gates as cg
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
    sub = "zero_card" if zero_card else "cards"
    cards_dir = EV / sub
    eye_dir = EV / "eye_ledger"
    cards_dir.mkdir(parents=True, exist_ok=True)
    eye_dir.mkdir(parents=True, exist_ok=True)
    for old in cards_dir.glob("*.png"):
        old.unlink()
    if not zero_card:
        for old in list(eye_dir.glob("*.png")) + list(eye_dir.glob("*.json")):
            old.unlink()
    s3_stub = _S3Stub(cards_dir, eye_dir)
    attached: dict = {}

    def _capture_update(uid, analysis_id, comparisons, status):
        attached["uid"] = uid
        attached["analysisId"] = analysis_id
        attached["status"] = status
        attached["comparisons"] = comparisons

    cap = _LogCapture()
    logging.getLogger().addHandler(cap)
    orig_s3, orig_signed = app._s3, app._signed_get  # noqa: SLF001
    orig_update = app.firestore_admin.update_analysis_fault_zoom
    orig_hold = cg.hold_gate
    app._s3 = s3_stub
    app._signed_get = lambda bucket, key: f"stub://{key}"
    app.firestore_admin.update_analysis_fault_zoom = _capture_update
    if zero_card:
        # LD-5 관찰 실험 — 드라이버 프로세스 한정 (운영 코드 무접촉).
        # hold 전부 FAIL → joint-scope 생존 0 → 부착 semantics 실물 관찰.
        def _always_fail(*_a, **_k):
            return cg.HoldResult(
                passed=False, speed_dps=None, n_samples=0,
                reason="zero_card_experiment",
            )

        cg.hold_gate = _always_fail
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
        cg.hold_gate = orig_hold
        logging.getLogger().removeHandler(cap)

    va = cap.verdict_args or ()
    survivors = list(va[2]) if len(va) >= 5 else []
    dropped = list(va[3]) if len(va) >= 5 else []
    eye_calls = int(va[4]) if len(va) >= 5 else -1
    png_md5 = {
        p.name: hashlib.md5(p.read_bytes()).hexdigest()
        for p in sorted(cards_dir.glob("*.png"))
    }
    out = {
        "zeroCard": zero_card,
        "freezes": report["freezes"],
        "excluded": [dict(e) for e in excluded],
        "alignQuality": q_ok,
        "verdict": {
            "survivors": survivors,
            "dropped": dropped,
            "eyeCalls": eye_calls,
        },
        "attached": {
            "called": bool(attached),
            "status": attached.get("status"),
            "comparisons": [
                {k: v for k, v in c.items()}
                for c in (attached.get("comparisons") or [])
            ],
        },
        "existingTiers": [
            c.get("tier") for c in (res.get("faultZoomComparisons") or [])
            if isinstance(c, dict)
        ],
        "s3Keys": s3_stub.keys,
        "pngMd5": png_md5,
        "cropLines": cap.crop_lines,
    }
    name = "zero_card_verdict.json" if zero_card else "run_verdict.json"
    (EV / name).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"survivors: {survivors}")
    print(f"dropped: {dropped}")
    print(f"cards saved ({sub}): {sorted(png_md5)}")
    if zero_card:
        conf = [c for c in out["attached"]["comparisons"]
                if c.get("tier") == "confirmed"]
        adv = [c for c in out["attached"]["comparisons"]
               if c.get("tier") == "advisory"]
        print(f"ZERO-CARD attach called={out['attached']['called']} "
              f"confirmed={len(conf)} advisory={len(adv)} "
              f"(기존 doc tiers={out['existingTiers']})")
    return out


# ── 승인 5동작 스윕 (belle 추가 지시 — "어떤 영상을 올려도 제대로") ──────────
# P35 활성 5슬롯 전부에 **운영 헬퍼 그대로** freeze-only 상속 경로를 실행.
# freezes = ii0 probes.log 정본 (승인 렌더의 실제 정지), 폴 = ii0 poles.json.
# 벤치 2슬롯(pdshape correct/realupload)은 구버전 포맷(refKp 부재) — helper 의
# refKp 스킵 가드 대상이라 범위 밖. README JOBS 원문 키.
SWEEP_JOBS = {
    "elbow": ("fixtures/phase15/elbow-twist-sister/fault.mp4",
              "reference/ref-elbow-twist-sister.mp4", "ref-elbow-twist-sister"),
    "kipup": ("fixtures/phase15/kip-up/fault.mp4",
              "reference/ref-kip-up.mp4", "ref-kip-up"),
    "pdshapefault": ("uploads/csKWYvI3WCPYPysNQ9KkWecaUvq1/pdshapefault1785373695.mp4",
                     "reference/ref-pdshape.mp4", "ref-pdshape"),
    "peterpan": ("uploads/csKWYvI3WCPYPysNQ9KkWecaUvq1/peterpanfault1785373695.mp4",
                 "reference/ref-peter-pan.mp4", "ref-peter-pan"),
    "powerspin": ("fixtures/phase15/power-spin/fault.mp4",
                  "reference/ref-power-spin.mp4", "ref-power-spin"),
}
# profile.category 는 렌더 스탬프(stamp_ref)에만 영향 — 게이트/방출 판정 무관.
SWEEP_CATEGORY = {"powerspin": "spin"}
SPA = SP.parent / "approved_sweep"


def _probe_freezes() -> dict[str, list[dict]]:
    """ii0 probes.log → 동작별 승인 freeze 목록 (approved() 와 같은 파싱)."""
    import re

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
                "rid": mp.group(1), "joint": mp.group(2),
                "pairSrc": mp.group(3),
                "userSec": float(mp.group(4)), "refSec": float(mp.group(5)),
            })
    return stops


def sweep() -> dict:
    """승인 5동작에 운영 헬퍼 실행 — 동작별 방출/침묵 + freeze 초 일치."""
    _ensure_gemini_key()
    import app  # noqa: F401 - 운영 모듈 그대로
    from sunity_shared.analysis import compare_render

    s3 = _s3_client()
    poles_all = json.loads((II0 / "sweep_out" / "poles.json").read_text())
    stops = _probe_freezes()
    refrep_dir = SPA / "refreports"
    refrep_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}
    all_match = True
    for m, (ukey, rkey, motion_id) in SWEEP_JOBS.items():
        print(f"══ SWEEP {m} ══")
        md = SPA / m
        md.mkdir(parents=True, exist_ok=True)
        uv, rv = md / "user.mp4", md / "ref.mp4"
        for p, key in ((uv, ukey), (rv, rkey)):
            if not p.exists():
                s3.download_file(BUCKET, key, str(p))
                print(f"  fetched {key} {p.stat().st_size} bytes")
        doc = json.loads((DATA / m / "doc.json").read_text())
        res = doc.get("result", doc)
        align = json.loads((DATA / m / "align.json").read_text())
        rr_p = refrep_dir / f"{motion_id}.json"
        if not rr_p.exists():
            from sunity_shared import firestore_admin as fa

            ref = fa.get_reference_motion(motion_id)
            rr_p.write_text(json.dumps(
                {"referenceKeypointReport": ref["referenceKeypointReport"]}))
            print(f"  fetched refmotion {motion_id}")
        ref_report = json.loads(rr_p.read_text())["referenceKeypointReport"]

        # 운영 render workdir 미러 — 폴 캐시(ii0 정본) + 30fps 프레임 (눈 재료)
        wd = md / "render"
        wd.mkdir(exist_ok=True)
        pm = poles_all.get(m) or {}
        for side in ("user", "ref"):
            xn = (pm.get(side) or {}).get("x_norm")
            cache = wd / f"pole_{side}.json"
            if xn is not None and not cache.exists():
                cache.write_text(json.dumps({"xNorm": xn}))
        tag = f"{int(compare_render.FPS_OUT)}_{compare_render.PANEL_H}"
        compare_render.extract_frames(uv, wd / f"u{tag}")
        compare_render.extract_frames(rv, wd / f"r{tag}")

        freezes = [dict(f) for f in stops.get(m) or []]
        report = {"freezes": freezes, "excludedFreezes": []}
        for f in freezes:
            print(f"  FREEZE {f['rid']} joint={f['joint']} src={f['pairSrc']} "
                  f"u={f['userSec']:.3f} r={f['refSec']:.2f}")

        cards_dir = EV / "sweep_cards" / m
        cards_dir.mkdir(parents=True, exist_ok=True)
        for old in cards_dir.glob("*.png"):
            old.unlink()
        s3_stub = _S3Stub(cards_dir, cards_dir)
        attached: dict = {}

        def _capture_update(uid, analysis_id, comparisons, status,
                            _sink=attached):
            _sink["comparisons"] = comparisons
            _sink["status"] = status

        cap = _LogCapture()
        logging.getLogger().addHandler(cap)
        orig_s3, orig_signed = app._s3, app._signed_get  # noqa: SLF001
        orig_update = app.firestore_admin.update_analysis_fault_zoom
        app._s3 = s3_stub
        app._signed_get = lambda bucket, key: f"stub://{key}"
        app.firestore_admin.update_analysis_fault_zoom = _capture_update
        try:
            profile = types.SimpleNamespace(
                category=SWEEP_CATEGORY.get(m), motion_id=motion_id)
            app._run_gated_card_inherit(
                result=res,
                report=report,
                align=align,
                render_workdir=wd,
                user_video_path=str(uv),
                reference_video_path=str(rv),
                user_report=res.get("keypointReport"),
                ref_report=ref_report,
                profile=profile,
                existing_comparisons=res.get("faultZoomComparisons") or [],
                uid="sweep",
                analysis_id=f"sweep-{m}",
                bucket=BUCKET,
            )
        finally:
            app._s3, app._signed_get = orig_s3, orig_signed
            app.firestore_admin.update_analysis_fault_zoom = orig_update
            logging.getLogger().removeHandler(cap)

        va = cap.verdict_args or ()
        survivors = list(va[2]) if len(va) >= 5 else []
        dropped = list(va[3]) if len(va) >= 5 else []
        out_m = {
            "freezes": freezes,
            "verdict": {
                "survivors": survivors,
                "dropped": dropped,
                "eyeCalls": int(va[4]) if len(va) >= 5 else -1,
            },
            "attached": {
                "comparisons": [
                    {k: v for k, v in c.items()}
                    for c in (attached.get("comparisons") or [])
                ],
            },
            "cropLines": cap.crop_lines,
            "pngMd5": {
                p.name: hashlib.md5(p.read_bytes()).hexdigest()
                for p in sorted(cards_dir.glob("*.png"))
            },
        }
        bad = _freeze_match(out_m)
        out_m["freezeMatch"] = not bad
        out_m["freezeMatchViolations"] = bad
        if bad:
            all_match = False
        results[m] = out_m
        print(f"  survivors: {survivors}")
        print(f"  dropped: {dropped}")
        print(f"  freeze-match: {'OK' if not bad else bad}")

    (EV / "sweep_verdict.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1))
    n_emit = sum(len(r["verdict"]["survivors"]) for r in results.values())
    n_drop = sum(len(r["verdict"]["dropped"]) for r in results.values())
    print(f"SWEEP FREEZE-MATCH {'ALL' if all_match else 'FAIL'} "
          f"(5 motions, emitted={n_emit} silenced={n_drop})")
    return results


def approved() -> dict:
    """승인 코퍼스 무회귀 — ii0 스윕 등가성 (probes.log + poles.json 정본).

    joint-scope 정지에 card_gates(확정 임계)를 적용해 9/9 생존을 재현.
    align-peak 정지는 비구속 (정보 행). 임계 완화 금지 — 죽으면 수술이
    판정 함수에 샌 것 (Task 1 은 판정 함수 무접촉이어야 한다).
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


def _freeze_match(out: dict) -> list[str]:
    """LD-1 — survivors 의 @u/r 이 freezes[] 값 그대로인지. 위반 목록 반환."""
    by_rid = {f["rid"]: f for f in out["freezes"]}
    bad: list[str] = []
    for s in out["verdict"]["survivors"]:
        rid, rest = s.split(":", 1)
        _path, moments = rest.split("@", 1)
        fz = by_rid.get(rid)
        if fz is None:
            bad.append(f"{s} — freeze 에 없는 rid (순간 발명)")
            continue
        expect = f"u{fz['userSec']:.3f}/r{fz['refSec']:.2f}"
        if moments != expect:
            bad.append(f"{s} — freeze 는 {expect} (변형 연산 존재)")
    return bad


def check() -> int:
    fails = 0

    # (1)(2) 2회 별도 프로세스 실행 → freeze 일치 + 결정론
    runs: list[dict] = []
    for i in (1, 2):
        print(f"── run {i}/2 (별도 프로세스) ──")
        r = subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).resolve()), "--run"],
            capture_output=True, text=True,
        )
        sys.stdout.write(r.stdout[-3000:])
        if r.returncode != 0:
            sys.stderr.write(r.stderr[-3000:])
            print(f"run {i} FAILED (exit {r.returncode})")
            return 1
        out = json.loads((EV / "run_verdict.json").read_text())
        (EV / f"run{i}_verdict.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1))
        runs.append(out)

    for i, out in enumerate(runs, 1):
        bad = _freeze_match(out)
        if bad:
            print(f"FREEZE-MATCH FAIL (run {i}):")
            for b in bad:
                print(f"  {b}")
            fails += 1
    if fails == 0:
        n = len(runs[0]["verdict"]["survivors"])
        print(f"FREEZE-MATCH ALL ({n} survivors == freezes, 2 runs)")

    keys = [
        ("survivors", lambda o: o["verdict"]["survivors"]),
        ("dropped", lambda o: o["verdict"]["dropped"]),
        ("cards(joint/tier)", lambda o: [
            (c.get("joint"), c.get("tier"))
            for c in o["attached"]["comparisons"]
        ]),
        ("pngMd5", lambda o: o["pngMd5"]),
    ]
    det_ok = True
    for name, fn in keys:
        a, b = fn(runs[0]), fn(runs[1])
        if a != b:
            det_ok = False
            print(f"DETERMINISM FAIL [{name}]\n  run1={a}\n  run2={b}")
    if det_ok:
        print("DETERMINISM PASS (survivors/dropped/cards/pngMd5 2회 동일)")
    else:
        fails += 1

    # (3) 승인 무회귀
    ap = approved()
    if ap["binding"] == 9 and ap["hold"] == 9 and ap["pair"] == 9:
        print("approved 9/9 (hold+pair) + peak 비구속", ap["peak"])
    else:
        print(f"approved REGRESSION hold {ap['hold']}/{ap['binding']} "
              f"pair {ap['pair']}/{ap['binding']} — 수술이 판정에 샌 것 의심")
        fails += 1

    # 참고 출력 (판정 조건 아님 — LD-5/6, 개별 관절 방출은 실측 그대로 보고)
    conf = [c for c in runs[0]["attached"]["comparisons"]
            if c.get("tier") == "confirmed"]
    print(f"confirmed joints: {[c.get('joint') for c in conf]}")
    print(f"eye_calls: run1={runs[0]['verdict']['eyeCalls']} "
          f"run2={runs[1]['verdict']['eyeCalls']}")
    print(f"CHECK {'PASS' if fails == 0 else f'FAIL({fails})'}")
    return 1 if fails else 0


def main() -> int:
    apr = argparse.ArgumentParser()
    apr.add_argument("--fetch", action="store_true")
    apr.add_argument("--run", action="store_true")
    apr.add_argument("--zero-card", action="store_true")
    apr.add_argument("--sweep", action="store_true")
    apr.add_argument("--approved", action="store_true")
    apr.add_argument("--check", action="store_true")
    args = apr.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    EV.mkdir(exist_ok=True)
    if args.fetch:
        fetch()
    if args.run:
        run()
    if args.zero_card:
        run(zero_card=True)
    if args.sweep:
        sweep()
    if args.approved:
        approved()
    if args.check:
        return check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
