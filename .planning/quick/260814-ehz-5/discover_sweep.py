#!/usr/bin/env python3
"""발굴 일반화 스윕 하네스 (quick-260814-ehz) — 판정 재료 생산 전용.

wif `discover_knee.py`(왼무릎 단일 record 발굴, belle 채택 1/1)의 **사본 확장**
이다 — wif 원본 3파일(discover_knee.py / evidence/candidates.json / LEDGER 기존
절)은 무수정. 이 파일은 그 규율을 승인 5동작 13 record 전수로 일반화한다:

  · 동작 파라미터화 — SWEEP_JOBS(ufb verify_local.py:378-389 원문 키: S3 user/ref
    키 + motion_id 정본)를 상수로 옮기고, 동작별 마운트는 ufb sweep() 패턴 그대로
    (doc/align = P35 data 직접 로드 — align.json 이 곧 판정 트랙이라 build_align
    재구축 불요, 폴 = ii0 poles.json, refmotion = Firestore 읽기, 영상 = S3
    read-only, 30fps 스틸 = compare_render.extract_frames).
  · claim 유도 일반화 — wif 의 `need_ext`(user=bent / ref=extended) 하드코딩을
    **양방향 트랙 대조**로 교체: 후보 순간 user 각도의 track_claim 과 **반대**
    claim 인 ref 프레임만 짝 후보. 관절별 하드코딩 0.
  · 소스 게이트 — 동작별 로컬 replay 가능성(P35 doc/align 실물 + align 스키마 +
    S3 영상 + fps 교차검증)을 record 스캔 **전에** 판정. 실패 동작은 "로컬 불가
    — Pod 필요"로 정직 박제하고 스캔 생략 (억지 성립 0).

운영 코드 무접촉 — card_gates / fault_zoom / compare_render / app 헬퍼는 전부
**임포트 재사용**(수정 0). 게이트 임계는 card_gates 모듈 상수(260811-ii0
SWEEP-REPORT §2 확정값) 그대로 — 이 파일에 임계 신설 0.

stages:
  --fetch   동작별 소스 게이트 + S3 영상(read-only) + refmotion + 30fps 프레임
            + 폴 캐시 마운트 → 캐시 루트(--cache-root, 실행 세션 scratchpad).
  --scan    동작별 record **전건** 홀드 스캔(hold_gate 3창 Theil-Sen) + 짝 2종
            (poseMin 중립 / claimContrast 발굴) + 승인 freeze 대조 행(ii0
            probes.log) + 탈락 사유 분포 + 압축 후보 stills 덤프
            → evidence/{motion}/candidates.json
  --eye     압축 후보 기계 눈 실판정 (card_gates.machine_eye) — claim 은 스캔이
            유도한 uClaim/rClaim. 상한 **record 당 16회** (motion, rid) 키 계수기
            코드 강제 + eye_calls.log + eye_ledger/ 원장.
  --render  눈 PASS 후보만 운영 헬퍼(app._run_gated_card_inherit) 그대로 렌더 —
            새 문법 발명 0. S3/Firestore 는 로컬 스텁. 2회 재렌더 md5 결정론.
  --check   Task 1 게이트 (5동작 후보표 + record 커버리지 13/13 + 압축 후보
            stills 실물 + VISUAL-REVIEW 후보 id 전건 + fps 교차검증).

초 환산 규율 (u8i 준수): 스캔/게이트/짝 = **align 15fps 타임베이스 단일**.
9.0/18.0 라벨 분모 사용 0 — 렌더 override 의 초→프레임 환산은 운영 _override_idx
(probe_effective_fps + rep9 역변환)가 소유한다.

S3 read-only(업로드 0) · Pod 무접촉 · Firestore 쓰기 0(refmotion 읽기만) ·
채점 무접촉 · Gemini = machine_eye 실호출만. 키 = SSM --profile sunity-motion
(키 값 로그 금지). 캐시 루트(scratchpad)는 **휘발** — 보존 재료는 evidence/
커밋분만이다.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import logging
import os
import pathlib
import re
import shutil
import sys
import types

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "backend" / "shared" / "python"))
sys.path.insert(0, str(_REPO / "backend" / "functions" / "pipeline"))

BUCKET = "sunity-motion-pilot-videos"

# ── 스윕 대상 (ufb verify_local.py:378-389 원문 — S3 키/motion_id 정본) ────────
SWEEP_JOBS: dict[str, tuple[str, str, str]] = {
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
    # quick-260821-ls0 정식 등재 (c3m SUMMARY 박제 절차 이행) — S3 키/motion_id
    # 정본 = backend/scripts/p35_extract_align.py JOBS + c3m verify_source_gate.py.
    "climb": ("fixtures/phase15/climb/correct.mp4",
              "reference/ref-climb.mp4", "ref-climb"),
    "climbfault": ("fixtures/phase15/climb/fault.mp4",
                   "reference/ref-climb.mp4", "ref-climb"),
    "combo": ("fixtures/phase15/combo/correct.mp4",
              "reference/ref-combo.mp4", "ref-combo"),
}
# profile.category 는 렌더 스탬프(stamp_ref)에만 영향 — 게이트/방출 판정 무관.
SWEEP_CATEGORY = {"powerspin": "spin"}

# 플래너 실측 인벤토리 (PLAN context 표) — 스캔 커버리지 대조용 (누락 0 확인).
RECORD_INVENTORY = {
    "elbow": 4, "kipup": 1, "pdshapefault": 4, "peterpan": 1, "powerspin": 3,
    # quick-260821-ls0 실행 시점 재실측 (커밋 P35 doc.json 직접 판독, 2026-08-21):
    # climb records:[] 길이 0 / climbfault deductionBreakdown 키 자체 부재
    # (Firestore 원본 대조로 스냅샷 결손 아님 확인 — 진짜 0) / combo records:[] 0.
    # quick-260821-pnp 재실측: climbfault=1 (veto-ON 재분석 doc p35newclimbfault1787297579, records 1 — 구 0 은 veto OFF 생성본 재료 결손).
    "climb": 0, "climbfault": 1, "combo": 0,
}

DATA = _REPO / ".planning/phases/35-server-rendered-comparison-video/data"
II0 = _REPO / ".planning/quick/260811-ii0-card-gates-5"
EV = _HERE / "evidence"

# ── 하네스 한정자 (게이트 임계 아님 — 임계는 전부 card_gates 모듈 상수) ───────
EYE_CALL_CAP = 16          # record 당 기계 눈 실호출 상한 (kpo T-kpo-03 기결론)
PAIR_WINDOW_S = 2.0        # 기준 짝 탐색 창 = align 매핑 이웃 ±2s (순서 제약)
MAX_CANDS_PER_RECORD = 4   # 압축 상한 (wif 눈 4후보 규율 — 전 프레임 눈 금지)
FPS_CHECK_TOL = 0.5        # align fps 라벨 vs 프레임수/길이 교차검증 허용오차

log = logging.getLogger("discover_sweep")

_CACHE_ROOT: pathlib.Path | None = None


def _cr_root() -> pathlib.Path:
    if _CACHE_ROOT is None:
        raise SystemExit(
            "--cache-root 미지정 (실행 세션 scratchpad 하위 경로를 주세요 — "
            "구 세션 UUID 하드코딩 금지, scratchpad 는 휘발)")
    return _CACHE_ROOT


# ── 공용: 자격/키 ────────────────────────────────────────────────────────────

def _s3_client():
    import boto3

    session = boto3.Session(
        profile_name=os.environ.get("AWS_PROFILE", "sunity-motion"))
    return session.client("s3", region_name="ap-northeast-2")


def _ensure_gemini_key() -> None:
    """SSM → GEMINI_API_KEY env (미설정 시). 키 값은 절대 로그하지 않는다."""
    if os.environ.get("GEMINI_API_KEY", "").strip():
        return
    import boto3

    session = boto3.Session(
        profile_name=os.environ.get("AWS_PROFILE", "sunity-motion"))
    ssm = session.client("ssm", region_name="ap-northeast-2")
    val = ssm.get_parameter(
        Name="/sunity/motion/gemini-api-key", WithDecryption=True,
    )["Parameter"]["Value"]
    os.environ["GEMINI_API_KEY"] = val
    print(f"GEMINI_API_KEY injected (len={len(val)})")


def _ensure_firebase_env() -> None:
    if not os.environ.get("FIREBASE_SA_PATH") and not os.environ.get(
            "FIREBASE_SA_JSON"):
        os.environ["FIREBASE_SA_PATH"] = str(_REPO / "firebase-sa.json")


def _paths(m: str) -> types.SimpleNamespace:
    md = _cr_root() / m
    return types.SimpleNamespace(
        dir=md, user=md / "user.mp4", ref=md / "ref.mp4",
        render=md / "render", refmotion=md / "refmotion.json",
    )


# ── 승인 freeze (ii0 probes.log 정본 — 대조 행 재료) ─────────────────────────

def _probe_freezes() -> dict[str, list[dict]]:
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
                "rid": mp.group(1), "joint": mp.group(2), "pairSrc": mp.group(3),
                "userSec": float(mp.group(4)), "refSec": float(mp.group(5)),
            })
    return stops


# ── 소스 게이트 (record 스캔 **전** 동작별 판정 — 억지 성립 0) ────────────────

_ALIGN_REQUIRED = (
    "userKp", "refKp", "userScore", "refScore", "curveRefSec", "fps",
    "userFrames", "refFrames", "userSize", "refSize", "joints17",
)


def source_gate(m: str, *, download: bool = True) -> dict:
    """동작별 로컬 replay 가능성 판정. 실패 = '로컬 불가 — Pod 필요' 박제."""
    g: dict = {"motion": m, "checks": {}, "reasons": [], "passed": True}

    def fail(reason: str) -> None:
        g["passed"] = False
        g["reasons"].append(reason)

    doc_p, align_p = DATA / m / "doc.json", DATA / m / "align.json"
    g["checks"]["p35DocExists"] = doc_p.is_file()
    g["checks"]["p35AlignExists"] = align_p.is_file()
    if not doc_p.is_file():
        fail(f"P35 doc.json 부재 ({doc_p})")
    if not align_p.is_file():
        fail(f"P35 align.json 부재 ({align_p})")
    if not g["passed"]:
        return g

    align = json.loads(align_p.read_text())
    missing = [k for k in _ALIGN_REQUIRED if k not in align]
    g["checks"]["alignSchemaMissing"] = missing
    if missing:
        fail(f"align 스키마 결손: {missing}")
    g["checks"]["alignFpsLabel"] = align.get("fps")
    g["checks"]["frames"] = {"user": align.get("userFrames"),
                             "ref": align.get("refFrames")}

    pp = _paths(m)
    pp.dir.mkdir(parents=True, exist_ok=True)
    ukey, rkey, motion_id = SWEEP_JOBS[m]
    g["s3Keys"] = {"user": ukey, "ref": rkey, "motionId": motion_id}
    s3 = None
    for which, key, p in (("user", ukey, pp.user), ("ref", rkey, pp.ref)):
        if p.exists():
            g["checks"][f"video_{which}"] = "cached"
            continue
        if not download:
            fail(f"{which} 영상 캐시 부재 (--fetch 선행 필요)")
            continue
        try:
            s3 = s3 or _s3_client()
            s3.download_file(BUCKET, key, str(p))
            g["checks"][f"video_{which}"] = f"downloaded {p.stat().st_size}B"
        except Exception as e:  # noqa: BLE001 - 다운로드 실패 = 로컬 불가 판정
            g["checks"][f"video_{which}"] = f"FAIL {type(e).__name__}"
            fail(f"S3 {which} 영상 다운로드 실패 ({key}): {type(e).__name__}: {e}")
    if not g["passed"]:
        return g

    # fps 교차검증 — align 프레임수/영상 길이 vs align fps 라벨 (u8i 규율).
    import imageio

    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor

    ext = FfmpegFrameExtractor(target_fps=9.0, max_side=640)
    afps = float(align.get("fps") or 0.0)
    chk: dict = {}
    eff: dict = {}
    for which, p, nf in (("user", pp.user, int(align["userFrames"])),
                         ("ref", pp.ref, int(align["refFrames"]))):
        reader = imageio.get_reader(str(p))
        try:
            dur = float(reader.get_meta_data().get("duration") or 0.0)
        finally:
            reader.close()
        ratio = round(nf / dur, 3) if dur else None
        chk[which] = {"durS": round(dur, 3), "framesOverDuration": ratio}
        if ratio is None or abs(ratio - afps) > FPS_CHECK_TOL:
            fail(f"fps 교차검증 실패 ({which}: {ratio} vs align 라벨 {afps})")
        try:
            eff[which] = float(ext.probe_effective_fps(str(p)))
        except Exception as e:  # noqa: BLE001
            eff[which] = None
            fail(f"{which} 실효 fps 판정 불가: {type(e).__name__}")
    g["checks"]["fpsCrossCheck"] = chk
    g["checks"]["probeEffectiveFps"] = eff
    return g


# ── 마운트 (ufb sweep() 패턴 — doc/align/폴/refmotion/프레임) ────────────────

def mount(m: str, *, frames: bool = True) -> types.SimpleNamespace:
    from sunity_shared.analysis import card_gates as cg
    from sunity_shared.analysis import compare_render as _cr

    pp = _paths(m)
    _ukey, _rkey, motion_id = SWEEP_JOBS[m]
    doc = json.loads((DATA / m / "doc.json").read_text())
    res = doc.get("result", doc)
    align = json.loads((DATA / m / "align.json").read_text())

    # 폴 = ii0 poles.json 정본을 render workdir 캐시로 마운트 (재검출 0).
    pp.render.mkdir(parents=True, exist_ok=True)
    poles_all = json.loads((II0 / "sweep_out" / "poles.json").read_text())
    pm = poles_all.get(m) or {}
    poles: dict[str, float | None] = {}
    for side in ("user", "ref"):
        xn = (pm.get(side) or {}).get("x_norm")
        poles[side] = float(xn) if xn is not None else None
        cache = pp.render / f"pole_{side}.json"
        if xn is not None and not cache.exists():
            cache.write_text(json.dumps({"xNorm": float(xn)}))

    # refmotion = Firestore 읽기 (쓰기 0) — 캐시 재사용.
    if not pp.refmotion.exists():
        _ensure_firebase_env()
        from sunity_shared import firestore_admin as fa

        ref = fa.get_reference_motion(motion_id)
        pp.refmotion.write_text(json.dumps(
            {"referenceKeypointReport": ref["referenceKeypointReport"]}))
        print(f"  fetched refmotion {motion_id}")

    if frames:
        tag = f"{int(_cr.FPS_OUT)}_{_cr.PANEL_H}"
        _cr.extract_frames(pp.user, pp.render / f"u{tag}")
        _cr.extract_frames(pp.ref, pp.render / f"r{tag}")

    urep = cg.align_to_report(align, "user")
    rrep = cg.align_to_report(align, "ref")
    usize, rsize = tuple(align["userSize"]), tuple(align["refSize"])
    return types.SimpleNamespace(
        m=m, motion_id=motion_id, cg=cg, res=res, align=align,
        urep=urep, rrep=rrep, afps=float(align["fps"]),
        usize=usize, rsize=rsize, poles=poles, paths=pp,
        u_torso=cg.torso_px_median(urep, usize),
        r_torso=cg.torso_px_median(rrep, rsize),
    )


# ── 게이트 행 (wif _gate_row 일반화 — 관절 파라미터) ─────────────────────────

def _conf_min_of(cg, rep: dict, idx: int, joint: str) -> float | None:
    """관절각 좌표들의 align conf 최소값. split 은 발목/힙 4점 기준."""
    from sunity_shared.analysis import fault_zoom as fz
    from sunity_shared.analysis.skeleton import JOINT_ANGLES

    names = (("left_ankle", "right_ankle", "left_hip", "right_hip")
             if joint == "split" else JOINT_ANGLES.get(joint))
    if not names:
        return None
    vals = []
    for n in names:
        rn = cg._resolve(rep, n)  # noqa: SLF001
        c = fz._kp_conf(rep, idx, rn) if rn else None  # noqa: SLF001
        if c is None:
            return None
        vals.append(float(c))
    return min(vals)


def _inverted(cg, rep: dict, idx: int) -> bool | None:
    """역립 국면 플래그 — 힙중점이 어깨중점보다 화면 위(y 작음)."""
    ls, rs = cg.kp(rep, idx, "left_shoulder"), cg.kp(rep, idx, "right_shoulder")
    lh, rh = cg.kp(rep, idx, "left_hip"), cg.kp(rep, idx, "right_hip")
    if None in (ls, rs, lh, rh):
        return None
    return (lh[1] + rh[1]) / 2 < (ls[1] + rs[1]) / 2


def _gate_row(ctx, u_idx: int, r_idx: int, joint: str) -> dict:
    """한 (u, r) 짝의 게이트 수치 전부 — 후보 행/대조 행 공용."""
    cg = ctx.cg
    hold_u = cg.hold_gate(ctx.urep, u_idx, joint)
    hold_r = cg.hold_gate(ctx.rrep, r_idx, joint)
    pair = cg.pair_gate(
        ctx.urep, u_idx, ctx.rrep, r_idx, ctx.poles["user"], ctx.poles["ref"],
        user_size=ctx.usize, ref_size=ctx.rsize,
        user_torso_px=ctx.u_torso, ref_torso_px=ctx.r_torso,
    )
    ua = cg.joint_angle(ctx.urep, u_idx, joint)
    ra = cg.joint_angle(ctx.rrep, r_idx, joint)
    return {
        "uSec": round(u_idx / ctx.afps, 4), "uIdx": int(u_idx),
        "rSec": round(r_idx / ctx.afps, 4), "rIdx": int(r_idx),
        "holdUser": {"passed": hold_u.passed, "speedDps": hold_u.speed_dps,
                     "reason": hold_u.reason, "windows": hold_u.window_speeds},
        "holdRef": {"passed": hold_r.passed, "speedDps": hold_r.speed_dps,
                    "reason": hold_r.reason, "windows": hold_r.window_speeds},
        "pair": {"passed": pair.passed, "poseDist": pair.pose_dist,
                 "basisK": pair.basis_k, "poleUser": pair.pole_user,
                 "poleRef": pair.pole_ref, "poleDiff": pair.pole_diff,
                 "reason": pair.reason},
        "uAngleDeg": None if ua is None else round(ua, 1),
        "rAngleDeg": None if ra is None else round(ra, 1),
        "uClaim": cg.track_claim(ua), "rClaim": cg.track_claim(ra),
        "uConfMin": _conf_min_of(cg, ctx.urep, u_idx, joint),
        "rConfMin": _conf_min_of(cg, ctx.rrep, r_idx, joint),
        "uInverted": _inverted(cg, ctx.urep, u_idx),
        "rInverted": _inverted(cg, ctx.rrep, r_idx),
    }


def _dump_still(ctx, side: str, sec: float, name: str) -> str | None:
    """30fps 1080p 렌더 프레임(운영 _frame_at 공식 round(sec x 30)+1)을
    evidence/{motion}/stills/ 로 복사 — 전신 프레임 실물."""
    from sunity_shared.analysis import compare_render as _cr

    tag = f"{int(_cr.FPS_OUT)}_{_cr.PANEL_H}"
    d = ctx.paths.render / (f"u{tag}" if side == "user" else f"r{tag}")
    n = len(list(d.glob("*.jpg")))
    if n <= 0:
        return None
    idx = max(1, min(n, round(sec * float(_cr.FPS_OUT)) + 1))
    out = EV / ctx.m / "stills" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(d / f"{idx:05d}.jpg", out)
    return str(out.relative_to(_HERE))


# ── 스캔 (record 전수 홀드 + 짝 2종 + 대조 행 + 탈락 분포) ────────────────────

def _scan_record(ctx, rec: dict, approved: list[dict]) -> dict:
    """record 1건 — 홀드 전 구간 스캔 → 버킷 → 짝 2종 → 후보/탈락 분포."""
    cg = ctx.cg
    rid = str(rec.get("recordId") or "").split(":")[0]
    crit = str(rec.get("criterion") or "")
    joint = cg.crit_joint(crit.split("__")[-1])
    uF, rF = int(ctx.urep["frames"]), int(ctx.rrep["frames"])
    curve = ctx.align["curveRefSec"]

    # split 계열(벌림각)은 cg.kp 단일 마크 좌표가 없어 기계 눈 유도가 원리적으로
    # 불가 — 스캔/짝 수치는 남기되 claim 대조/눈/렌더 대상에서 정직 탈락.
    eye_eligible = joint != "split"
    eye_reason = None if eye_eligible else (
        "split 벌림각 — cg.kp 단일 마크 좌표 부재로 기계 눈 유도 불가 "
        "(운영 helper 는 align-peak pass-through = 게이트 비구속)")

    holds_u = [cg.hold_gate(ctx.urep, f, joint) for f in range(uF)]
    pass_idx = [f for f, h in enumerate(holds_u) if h.passed]
    unmeas = sum(1 for h in holds_u if h.reason == "unmeasurable")
    raw_runs: list[dict] = []
    for f in pass_idx:
        if raw_runs and f == raw_runs[-1]["endF"] + 1:
            raw_runs[-1]["endF"] = f
        else:
            raw_runs.append({"startF": f, "endF": f})
    for run in raw_runs:
        run["startSec"] = round(run["startF"] / ctx.afps, 4)
        run["endSec"] = round(run["endF"] / ctx.afps, 4)

    buckets: dict[int, list[int]] = {}
    for f in pass_idx:
        buckets.setdefault(int(f / ctx.afps), []).append(f)
    runs: list[dict] = []
    for b in sorted(buckets):
        fs = buckets[b]
        rep = min(fs, key=lambda f: (
            holds_u[f].speed_dps if holds_u[f].speed_dps is not None
            else float("inf")))
        runs.append({
            "bucketSec": b, "startF": min(fs), "endF": max(fs),
            "startSec": round(min(fs) / ctx.afps, 4),
            "endSec": round(max(fs) / ctx.afps, 4),
            "passFrames": len(fs), "repF": rep,
            "repSec": round(rep / ctx.afps, 4),
            "minDps": holds_u[rep].speed_dps,
        })

    holds_r: dict[int, object] = {}

    def _hold_r(r_idx: int):
        if r_idx not in holds_r:
            holds_r[r_idx] = cg.hold_gate(ctx.rrep, r_idx, joint)
        return holds_r[r_idx]

    def _pair_search(u_idx: int, r_center: float, need_claim: str | None):
        """align 매핑 이웃 창 ±2s 안에서 양측홀드+짝정합 통과 중 포즈 최소.

        need_claim 지정 시 ref 트랙 claim 이 그 값인 프레임만 대상 (발굴 짝 —
        claim 대조 방향에서 유도. claim 이분은 card_gates 기존 상수)."""
        lo = max(0, int(round((r_center - PAIR_WINDOW_S) * ctx.afps)))
        hi = min(rF - 1, int(round((r_center + PAIR_WINDOW_S) * ctx.afps)))
        best = None
        stat = {"window": [round(lo / ctx.afps, 3), round(hi / ctx.afps, 3)],
                "holdFail": 0, "claimFail": 0, "pairFail": 0, "ok": 0}
        for r_idx in range(lo, hi + 1):
            if not _hold_r(r_idx).passed:
                stat["holdFail"] += 1
                continue
            if need_claim is not None:
                rc = cg.track_claim(cg.joint_angle(ctx.rrep, r_idx, joint))
                if rc != need_claim:
                    stat["claimFail"] += 1
                    continue
            pair = cg.pair_gate(
                ctx.urep, u_idx, ctx.rrep, r_idx,
                ctx.poles["user"], ctx.poles["ref"],
                user_size=ctx.usize, ref_size=ctx.rsize,
                user_torso_px=ctx.u_torso, ref_torso_px=ctx.r_torso,
            )
            if not pair.passed:
                stat["pairFail"] += 1
                continue
            stat["ok"] += 1
            if best is None or (pair.pose_dist or 9e9) < (best[1].pose_dist or 9e9):
                best = (r_idx, pair)
        return best, stat

    def _clamp_r(sec: float) -> int:
        return max(0, min(rF - 1, int(round(sec * ctx.afps))))

    cands: list[dict] = []
    drop = {"noHold": 0, "pairNone": 0, "claimNone": 0, "claimSame": 0,
            "claimPairNone": 0, "splitNoMark": 0, "ok": 0}
    if not runs:
        drop["noHold"] = 1
    for i, run in enumerate(runs):
        u_idx = run["repF"]
        r_center = float(curve[min(u_idx, len(curve) - 1)])
        cid = f"cand{i + 1:02d}"

        # ① poseMin (중립 짝) — 창 내 양측홀드+짝정합 중 포즈거리 최소
        best, stat = _pair_search(u_idx, r_center, None)
        cand: dict = {
            "id": cid, "rid": rid, "joint": joint,
            "holdRun": {k: run[k] for k in
                        ("startSec", "endSec", "repSec", "minDps", "passFrames")},
            "alignRefSec": round(r_center, 4),
            "poseMin": {"found": best is not None, "search": stat},
        }
        cand["poseMin"]["row"] = _gate_row(
            ctx, u_idx, best[0] if best else _clamp_r(r_center), joint)
        if best is None:
            cand["poseMin"]["fail"] = (
                f"창 {stat['window']}s 내 양측홀드+짝정합 동시 통과 없음 "
                f"(holdFail {stat['holdFail']} / pairFail {stat['pairFail']})")
            drop["pairNone"] += 1

        # ② claimContrast (발굴 짝) — user claim 의 **반대** claim ref 한정
        if not eye_eligible:
            cand["claimContrast"] = {"found": False, "reason": eye_reason}
            drop["splitNoMark"] += 1
            cands.append(cand)
            continue

        u_by_claim: dict[str, int] = {}
        for f in buckets[run["bucketSec"]]:
            c = cg.track_claim(cg.joint_angle(ctx.urep, f, joint))
            if c is None:
                continue
            prev = u_by_claim.get(c)
            spd = holds_u[f].speed_dps
            if prev is None or (spd if spd is not None else float("inf")) < (
                    holds_u[prev].speed_dps if holds_u[prev].speed_dps is not None
                    else float("inf")):
                u_by_claim[c] = f
        if not u_by_claim:
            cand["claimContrast"] = {
                "found": False,
                "reason": ("버킷 전 프레임 user 트랙 중간각(100~150도) 또는 좌표 "
                           "부재 — claim 이분 유도 불가"),
            }
            drop["claimNone"] += 1
            cands.append(cand)
            continue

        variants = []
        for uclaim, u_rep in sorted(u_by_claim.items()):
            opp = "extended" if uclaim == "bent" else "bent"
            b_center = float(curve[min(u_rep, len(curve) - 1)])
            b_best, b_stat = _pair_search(u_rep, b_center, opp)
            v = {
                "uClaim": uclaim, "needRefClaim": opp,
                "found": b_best is not None, "search": b_stat,
                "row": _gate_row(ctx, u_rep,
                                 b_best[0] if b_best else _clamp_r(b_center),
                                 joint),
            }
            if b_best is None:
                v["fail"] = (
                    f"창 {b_stat['window']}s 내 ref claim={opp} + 양측홀드 + "
                    f"짝정합 동시 통과 없음 (holdFail {b_stat['holdFail']} / "
                    f"claimFail {b_stat['claimFail']} / pairFail "
                    f"{b_stat['pairFail']})")
            variants.append(v)
        cand["claimContrast"] = {
            "found": any(v["found"] for v in variants), "variants": variants,
        }
        if cand["claimContrast"]["found"]:
            drop["ok"] += 1
        else:
            drop["claimPairNone"] += 1
        cands.append(cand)

    # 승인 freeze 대조 행 (재발견/신규 판별 재료)
    ap = [a for a in approved if a["rid"] == rid]
    contrast: dict = {}
    if ap:
        a = ap[0]
        contrast = {
            "label": f"승인 freeze (ii0 probes.log — src={a['pairSrc']})",
            "userSec": a["userSec"], "refSec": a["refSec"],
            "row": _gate_row(
                ctx, max(0, min(uF - 1, int(round(a["userSec"] * ctx.afps)))),
                _clamp_r(a["refSec"]), joint),
        }
    else:
        contrast = {"label": "승인 freeze 없음 (ii0 probes.log 에 이 rid 미등재)"}

    # 후보별 승인 freeze 와의 거리 (재발견/신규)
    for c in cands:
        rows = []
        pm = c.get("poseMin") or {}
        if pm.get("row"):
            rows.append(pm["row"])
        for v in (c.get("claimContrast") or {}).get("variants") or []:
            rows.append(v["row"])
        if ap:
            au = ap[0]["userSec"]
            c["approvedRelation"] = {
                "approvedUserSec": au,
                "dUserSec": round(min(abs(r["uSec"] - au) for r in rows), 3)
                if rows else None,
                "coversApprovedUser": bool(
                    c["holdRun"]["startSec"] - 0.001 <= au
                    <= c["holdRun"]["endSec"] + 0.001),
            }
        else:
            c["approvedRelation"] = {"approvedUserSec": None}

    return {
        "rid": rid, "criterion": crit, "joint": joint,
        "eyeEligible": eye_eligible, "eyeIneligibleReason": eye_reason,
        "deviation": rec.get("deviation"),
        "scan": {"passFrames": len(pass_idx), "totalFrames": uF,
                 "unmeasurableFrames": unmeas,
                 "rawRuns": raw_runs, "buckets": runs},
        "dropDistribution": drop,
        "candidates": cands,
        "approvedFreeze": contrast,
    }


def _compress(rec_out: dict) -> list[dict]:
    """record 당 claimContrast 성립 후보를 게이트 수치(포즈거리) 순 최대 4개.

    압축 단위 = (후보, uClaim) 변형 1건 = 눈 1쌍 = 카드 1안."""
    picks: list[dict] = []
    for c in rec_out["candidates"]:
        for v in (c.get("claimContrast") or {}).get("variants") or []:
            if not v["found"]:
                continue
            picks.append({
                "cid": f"{c['id']}{'B' if v['uClaim'] == 'bent' else 'E'}",
                "candId": c["id"], "uClaim": v["uClaim"],
                "rClaim": v["needRefClaim"], "row": v["row"],
                "holdRun": c["holdRun"],
                "approvedRelation": c.get("approvedRelation"),
            })
    picks.sort(key=lambda p: (p["row"]["pair"]["poseDist"] if
                              p["row"]["pair"]["poseDist"] is not None else 9e9))
    return picks[:MAX_CANDS_PER_RECORD]


def scan(motions: list[str]) -> dict:
    approved_all = _probe_freezes()
    summary: dict = {}
    for m in motions:
        print(f"══ SCAN {m} ══")
        gate = source_gate(m, download=True)
        out: dict = {
            "meta": {
                "motion": m, "motionId": SWEEP_JOBS[m][2],
                "s3Keys": {"user": SWEEP_JOBS[m][0], "ref": SWEEP_JOBS[m][1]},
                "sourceGate": gate,
                "generated": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            },
            "records": [],
        }
        if not gate["passed"]:
            out["meta"]["verdict"] = "로컬 불가 — Pod 필요"
            (EV / m).mkdir(parents=True, exist_ok=True)
            (EV / m / "candidates.json").write_text(
                json.dumps(out, ensure_ascii=False, indent=1))
            print(f"  SOURCE GATE FAIL — {gate['reasons']} (스캔 생략)")
            summary[m] = out
            continue

        ctx = mount(m)
        cg = ctx.cg
        from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
        _ext = FfmpegFrameExtractor(target_fps=9.0, max_side=640)
        out["meta"].update({
            "alignFps": ctx.afps,
            "poles": ctx.poles,
            "clip": {"userFrames": int(ctx.urep["frames"]),
                     "refFrames": int(ctx.rrep["frames"])},
            "thresholds": {
                "source": "260811-ii0 SWEEP-REPORT §2 (card_gates 모듈 상수 — "
                          "재튜닝 0)",
                "holdMaxDps": cg.HOLD_MAX_DPS, "poseMax": cg.PAIR_POSE_MAX,
                "poleDiffMax": cg.POLE_DIFF_MAX, "confMin": cg.HOLD_CONF_MIN,
                "eyeBentMaxDeg": cg.EYE_BENT_MAX_DEG,
                "eyeExtMinDeg": cg.EYE_EXT_MIN_DEG,
                "pairWindowS": PAIR_WINDOW_S,
                "maxCandsPerRecord": MAX_CANDS_PER_RECORD,
            },
            "verdict": "로컬 replay 가능",
        })
        records = [r for r in
                   ((ctx.res.get("deductionBreakdown") or {}).get("records") or [])
                   if isinstance(r, dict)]
        out["meta"]["recordCount"] = len(records)
        out["meta"]["recordInventoryExpected"] = RECORD_INVENTORY.get(m)
        for rec in records:
            ro = _scan_record(ctx, rec, approved_all.get(m) or [])
            picks = _compress(ro)
            # frames-before-numbers — 압축 후보 전건 전신 스틸 덤프
            for p in picks:
                r = p["row"]
                p["stills"] = {
                    "user": _dump_still(ctx, "user", r["uSec"],
                                        f"{ro['rid']}_{p['cid']}_user_{r['uSec']}s.jpg"),
                    "ref": _dump_still(ctx, "ref", r["rSec"],
                                       f"{ro['rid']}_{p['cid']}_ref_{r['rSec']}s.jpg"),
                }
            ro["compressed"] = picks
            out["records"].append(ro)
            nb = len(ro["scan"]["buckets"])
            print(f"  {ro['rid']} {ro['criterion']} joint={ro['joint']} "
                  f"hold {ro['scan']['passFrames']}/{ro['scan']['totalFrames']}"
                  f"f buckets={nb} claimOK={ro['dropDistribution']['ok']} "
                  f"compressed={len(picks)} eyeEligible={ro['eyeEligible']}")
            for p in picks:
                r = p["row"]
                print(f"    {p['cid']} u={r['uSec']}s({r['uAngleDeg']}deg/"
                      f"{p['uClaim']}) r={r['rSec']}s({r['rAngleDeg']}deg/"
                      f"{r['rClaim']}) pose={r['pair']['poseDist']} "
                      f"poleDiff={r['pair']['poleDiff']} "
                      f"holdU={r['holdUser']['speedDps']}")
        (EV / m).mkdir(parents=True, exist_ok=True)
        (EV / m / "candidates.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1))
        summary[m] = out
        del _ext
    return summary


def pairsheet(motions: list[str]) -> int:
    """압축 후보별 (학생|기준) 스틸 **무축소 가로 결합** — 육안 검수 단위.

    두 패널 모두 추출 원본 해상도(608x1080) 그대로 붙인다 (축소 0 — 몽타주
    축소본 검수 금지 규율). 개별 스틸도 stills/ 에 그대로 남는다.
    """
    from PIL import Image

    n = 0
    for m in motions:
        p = EV / m / "candidates.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        for ro in data.get("records") or []:
            for pk in ro.get("compressed") or []:
                st = pk.get("stills") or {}
                if not st.get("user") or not st.get("ref"):
                    continue
                iu = Image.open(_HERE / st["user"]).convert("RGB")
                ir = Image.open(_HERE / st["ref"]).convert("RGB")
                H = max(iu.height, ir.height)
                out = Image.new("RGB", (iu.width + ir.width + 8, H),
                                (24, 24, 24))
                out.paste(iu, (0, 0))
                out.paste(ir, (iu.width + 8, 0))
                dst = (EV / m / "stills" /
                       f"{ro['rid']}_{pk['cid']}_PAIR_u{pk['row']['uSec']}s_"
                       f"r{pk['row']['rSec']}s.jpg")
                out.save(dst, quality=92)
                pk["pairSheet"] = str(dst.relative_to(_HERE))
                n += 1
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"pairsheet: {n} 장 (학생|기준 무축소 결합)")
    return n


# ── eye (record 당 16회 상한 코드 강제 + 원장) ───────────────────────────────

_EYE_STATE: dict = {"per_record": {}, "memo": {}}


def _eye_log(m: str) -> pathlib.Path:
    p = EV / m / "eye_calls.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _eye_call(ctx, side: str, rep: dict, idx: int, joint: str, claim: str,
              frame_rgb, cid: str, rid: str) -> dict:
    """machine_eye 래퍼 — (motion, rid) 키 상한 코드 강제 + 로그 + 원장."""
    cg = ctx.cg
    m = ctx.m
    rkey = (m, rid)
    n_used = _EYE_STATE["per_record"].get(rkey, 0)
    memo_key = (m, side, int(idx), joint, claim)
    logp = _eye_log(m)
    if memo_key in _EYE_STATE["memo"]:
        got = dict(_EYE_STATE["memo"][memo_key])
        got["cached"] = True
        with open(logp, "a") as fh:
            fh.write(f"CACHED rid={rid} cand={cid} side={side} idx={idx} "
                     f"claim={claim} -> {got['observed']}/{got['limb']} "
                     f"match={got['match']} (실호출 계수 불변 "
                     f"{n_used}/{EYE_CALL_CAP})\n")
        return got
    if n_used >= EYE_CALL_CAP:
        with open(logp, "a") as fh:
            fh.write(f"CAP rid={rid} cand={cid} side={side} idx={idx} "
                     f"claim={claim} -> 미판정 (상한 {EYE_CALL_CAP} 도달)\n")
        return {"observed": "cap_exceeded", "limb": None, "match": False,
                "confidence": 0.0, "reason": "call cap", "cached": False}
    xy = cg.kp(rep, idx, joint, conf_min=0.0)
    if xy is None:
        with open(logp, "a") as fh:
            fh.write(f"NOKP rid={rid} cand={cid} side={side} idx={idx} "
                     f"claim={claim} -> align 좌표 부재 (마크 불가)\n")
        return {"observed": "no_kp", "limb": None, "match": False,
                "confidence": 0.0, "reason": "align 좌표 부재", "cached": False}
    _ensure_gemini_key()
    H, W = frame_rgb.shape[:2]
    _EYE_STATE["per_record"][rkey] = n_used + 1
    n = n_used + 1
    res = cg.machine_eye(
        frame_rgb, (xy[0] * W, xy[1] * H), claim,
        api_key=os.environ["GEMINI_API_KEY"],
        expected_limb=cg.joint_limb(joint), crop_px=max(320, W // 2),
    )
    with open(logp, "a") as fh:
        fh.write(f"CALL {n:02d}/{EYE_CALL_CAP} rid={rid} cand={cid} "
                 f"side={side} idx={idx} sec={idx / ctx.afps:.3f} "
                 f"claim={claim} observed={res['observed']} limb={res['limb']} "
                 f"match={res['match']} conf={res['confidence']}\n")
    led = EV / m / "eye_ledger"
    led.mkdir(parents=True, exist_ok=True)
    stem = f"{rid}_{n:02d}_{cid}_{side}_{joint}_{claim}"
    if res.get("crop") is not None:
        res["crop"].save(led / f"{stem}.png")
    (led / f"{stem}.json").write_text(json.dumps({
        "motion": m, "rid": rid, "cand": cid, "side": side,
        "frameIdx": int(idx), "sec": round(idx / ctx.afps, 3), "joint": joint,
        "claim": claim, "trackAngleDeg": round(
            cg.joint_angle(rep, idx, joint) or float("nan"), 1)
        if cg.joint_angle(rep, idx, joint) is not None else None,
        "observed": res["observed"], "limb": res["limb"],
        "match": bool(res["match"]), "confidence": res["confidence"],
        "reason": res["reason"],
    }, ensure_ascii=False, indent=1))
    _EYE_STATE["memo"][memo_key] = {
        k: v for k, v in res.items() if k != "crop"}
    # 운영 헬퍼 키 공간에도 등재 — render 단계 user 측 눈이 같은 (프레임, 좌표,
    # claim) 판정을 재사용 (실호출 중복 억제, 판정 동일).
    _EYE_STATE["memo"][(m, "helper", claim, cg.joint_limb(joint),
                        int(xy[0] * W), int(xy[1] * H))] = \
        _EYE_STATE["memo"][memo_key]
    out = dict(_EYE_STATE["memo"][memo_key])
    out["cached"] = False
    return out


def _frame_rgb(ctx, side: str, sec: float):
    from PIL import Image

    from sunity_shared.analysis import compare_render as _cr

    tag = f"{int(_cr.FPS_OUT)}_{_cr.PANEL_H}"
    d = ctx.paths.render / (f"u{tag}" if side == "user" else f"r{tag}")
    n = len(list(d.glob("*.jpg")))
    idx = max(1, min(n, round(sec * float(_cr.FPS_OUT)) + 1))
    return np.asarray(Image.open(d / f"{idx:05d}.jpg").convert("RGB"))


def _visual_rejected() -> dict[str, str]:
    """실행자 육안 탈락 목록 (evidence/visual_verdicts.json — 근거는
    VISUAL-REVIEW.md). 육안 탈락은 기계 눈 대상에서 빠지되 표에는 잔존한다."""
    p = EV / "visual_verdicts.json"
    if not p.exists():
        return {}
    return dict((json.loads(p.read_text()).get("rejected") or {}))


def eye(motions: list[str], only: set[str] | None = None) -> dict:
    """육안 통과 압축 후보 기계 눈 실판정 — claim 은 스캔이 유도한 uClaim/rClaim.

    눈이 기각하면 그 기각도 재료 — 재시도/크롭 재조정 조작 금지 (1후보 1판정)."""
    rejected = _visual_rejected()
    allout: dict = {}
    for m in motions:
        p = EV / m / "candidates.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        if not (data["meta"].get("sourceGate") or {}).get("passed"):
            continue
        picks = []
        for ro in data["records"]:
            for pk in ro.get("compressed") or []:
                tag = f"{m}/{ro['rid']}/{pk['cid']}"
                if tag in rejected:
                    print(f"  SKIP {tag} — 육안 탈락: {rejected[tag]}")
                    continue
                if only is not None and tag not in only:
                    continue
                picks.append((ro, pk))
        if not picks:
            continue
        print(f"══ EYE {m} ({len(picks)} candidates) ══")
        ctx = mount(m)
        verdicts: dict = {}
        for ro, pk in picks:
            row = pk["row"]
            u = _eye_call(ctx, "user", ctx.urep, row["uIdx"], ro["joint"],
                          pk["uClaim"], _frame_rgb(ctx, "user", row["uSec"]),
                          pk["cid"], ro["rid"])
            r = _eye_call(ctx, "ref", ctx.rrep, row["rIdx"], ro["joint"],
                          pk["rClaim"], _frame_rgb(ctx, "ref", row["rSec"]),
                          pk["cid"], ro["rid"])
            key = f"{ro['rid']}/{pk['cid']}"
            verdicts[key] = {
                "rid": ro["rid"], "cid": pk["cid"], "joint": ro["joint"],
                "uSec": row["uSec"], "rSec": row["rSec"],
                "uClaim": pk["uClaim"], "rClaim": pk["rClaim"],
                "uAngleDeg": row["uAngleDeg"], "rAngleDeg": row["rAngleDeg"],
                "user": {k: u[k] for k in
                         ("observed", "limb", "match", "confidence", "reason")},
                "ref": {k: r[k] for k in
                        ("observed", "limb", "match", "confidence", "reason")},
                "eyePass": bool(u["match"] and r["match"]),
            }
            print(f"  {key}: user {pk['uClaim']}->{u['observed']}/{u['limb']} "
                  f"match={u['match']} | ref {pk['rClaim']}->{r['observed']}/"
                  f"{r['limb']} match={r['match']} => "
                  f"{'PASS' if verdicts[key]['eyePass'] else 'FAIL'}")
        (EV / m / "eye_verdicts.json").write_text(
            json.dumps(verdicts, ensure_ascii=False, indent=1))
        allout[m] = verdicts
        used = {f"{k[0]}/{k[1]}": v
                for k, v in _EYE_STATE["per_record"].items() if k[0] == m}
        print(f"  eye calls per record: {used} (cap {EYE_CALL_CAP})")
    return allout


# ── render (운영 헬퍼 그대로 — 확정 문법, 새 문법 발명 0) ────────────────────

class _S3Stub:
    """put_object 를 로컬 저장으로 대체 (S3 read-only 제약 — 업로드 0)."""

    def __init__(self, cards_dir: pathlib.Path, eye_dir: pathlib.Path):
        self.cards_dir = cards_dir
        self.eye_dir = eye_dir
        self.keys: list[str] = []

    def put_object(self, *, Bucket, Key, Body, ContentType):  # noqa: N803
        self.keys.append(Key)
        outdir = self.eye_dir if "/eye/" in Key else self.cards_dir
        outdir.mkdir(parents=True, exist_ok=True)
        p = outdir / pathlib.Path(Key).name
        p.write_bytes(Body if isinstance(Body, (bytes, bytearray))
                      else Body.read())


class _LogCapture(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.lines: list[str] = []

    def emit(self, record):  # noqa: D102
        try:
            msg = record.getMessage()
            if msg.startswith(("card_gates", "display_anchor", "align_bake",
                               "fault_zoom")):
                self.lines.append(msg)
        except Exception:  # noqa: BLE001
            pass


def render(motions: list[str]) -> dict:
    """눈 PASS 후보만 운영 헬퍼 1회 = 카드 1안. 2회 재렌더 md5 결정론."""
    import app  # backend/functions/pipeline — 운영 모듈 그대로
    from sunity_shared import firestore_admin as fs_admin
    from sunity_shared.analysis import card_gates as cg
    from sunity_shared.analysis import frame_extractor as fe_mod

    _base = fe_mod.FfmpegFrameExtractor

    class _CachingExtractor(_base):
        _cache: dict = {}

        def extract(self, path):
            key = (str(path), self.target_fps, self.max_side)
            if key not in self._cache:
                self._cache[key] = super().extract(path)
            return self._cache[key]

    _orig_eye = cg.machine_eye
    _cur = {"m": None, "rid": None}

    def _counting_eye(frame_rgb, joint_xy_px, claim, *, api_key,
                      expected_limb=None, crop_px=360,
                      model="gemini-3.5-flash", timeout_s=60.0):
        m, rid = _cur["m"], _cur["rid"]
        mk = (m, "helper", claim, expected_limb,
              int(joint_xy_px[0]), int(joint_xy_px[1]))
        logp = _eye_log(m)
        if mk in _EYE_STATE["memo"]:
            got = dict(_EYE_STATE["memo"][mk])
            got["crop"] = None
            with open(logp, "a") as fh:
                fh.write(f"CACHED rid={rid} helper claim={claim} "
                         f"xy={mk[4]},{mk[5]} -> {got['observed']} "
                         f"(계수 불변)\n")
            return got
        n_used = _EYE_STATE["per_record"].get((m, rid), 0)
        if n_used >= EYE_CALL_CAP:
            with open(logp, "a") as fh:
                fh.write(f"CAP rid={rid} helper claim={claim} -> fail-closed\n")
            return {"observed": "cap_exceeded", "limb": None, "match": False,
                    "confidence": 0.0, "reason": "call cap", "crop": None}
        _EYE_STATE["per_record"][(m, rid)] = n_used + 1
        res = _orig_eye(frame_rgb, joint_xy_px, claim, api_key=api_key,
                        expected_limb=expected_limb, crop_px=crop_px,
                        model=model, timeout_s=timeout_s)
        with open(logp, "a") as fh:
            fh.write(f"CALL {n_used + 1:02d}/{EYE_CALL_CAP} rid={rid} helper "
                     f"claim={claim} observed={res['observed']} "
                     f"limb={res['limb']} match={res['match']} "
                     f"conf={res['confidence']}\n")
        _EYE_STATE["memo"][mk] = {k: v for k, v in res.items() if k != "crop"}
        return res

    allout: dict = {}
    for m in motions:
        vp = EV / m / "eye_verdicts.json"
        if not vp.exists():
            continue
        verdicts = json.loads(vp.read_text())
        passes = {k: v for k, v in verdicts.items() if v["eyePass"]}
        if not passes:
            print(f"══ RENDER {m}: 눈 PASS 0건 — 렌더 생략 (침묵) ══")
            allout[m] = {"cards": {}, "note": "눈 PASS 0건 — 렌더 생략"}
            (EV / m / "render_verdict.json").write_text(
                json.dumps(allout[m], ensure_ascii=False, indent=1))
            continue
        print(f"══ RENDER {m} ({len(passes)} eye-PASS) ══")
        _ensure_gemini_key()
        ctx = mount(m)
        data = json.loads((EV / m / "candidates.json").read_text())
        ref_report = json.loads(
            ctx.paths.refmotion.read_text())["referenceKeypointReport"]
        out: dict = {"cards": {}}
        cards_root = EV / m / "cards"
        cards_root.mkdir(parents=True, exist_ok=True)
        fe_mod.FfmpegFrameExtractor = _CachingExtractor
        cg.machine_eye = _counting_eye
        orig_s3, orig_signed = app._s3, app._signed_get  # noqa: SLF001
        orig_update = fs_admin.update_analysis_fault_zoom
        try:
            for key, v in passes.items():
                rid, cid = v["rid"], v["cid"]
                _cur["m"], _cur["rid"] = m, rid
                report = {"freezes": [{
                    "rid": rid, "joint": v["joint"],
                    "userSec": float(v["uSec"]), "refSec": float(v["rSec"]),
                    "pairSrc": "discovery",
                }], "excludedFreezes": []}
                md5s = []
                for run_i in (1, 2):
                    tmp = cards_root / f"_{rid}_{cid}_run{run_i}"
                    if tmp.exists():
                        shutil.rmtree(tmp)
                    stub = _S3Stub(tmp, EV / m / "eye_ledger")
                    attached: dict = {}

                    def _cap_update(uid, analysis_id, comparisons, status,
                                    _sink=attached):
                        _sink["comparisons"] = comparisons
                        _sink["status"] = status

                    cap = _LogCapture()
                    logging.getLogger().addHandler(cap)
                    app._s3 = stub
                    app._signed_get = lambda bucket, k: f"stub://{k}"
                    fs_admin.update_analysis_fault_zoom = _cap_update
                    app.firestore_admin.update_analysis_fault_zoom = _cap_update
                    try:
                        profile = types.SimpleNamespace(
                            category=SWEEP_CATEGORY.get(m),
                            motion_id=ctx.motion_id)
                        app._run_gated_card_inherit(
                            result=ctx.res, report=report, align=ctx.align,
                            render_workdir=ctx.paths.render,
                            user_video_path=str(ctx.paths.user),
                            reference_video_path=str(ctx.paths.ref),
                            user_report=ctx.res.get("keypointReport"),
                            ref_report=ref_report, profile=profile,
                            existing_comparisons=[],
                            uid="discovery-sweep",
                            analysis_id=f"ehz-{m}-{rid}-{cid}",
                            bucket=BUCKET,
                        )
                    finally:
                        logging.getLogger().removeHandler(cap)
                    pngs = sorted(tmp.glob("*.png")) if tmp.exists() else []
                    md5s.append({p.name: hashlib.md5(p.read_bytes()).hexdigest()
                                 for p in pngs})
                    if run_i == 1:
                        final = []
                        for p in pngs:
                            dst = (cards_root /
                                   f"{rid}_{cid}_u{v['uSec']}s_r{v['rSec']}s_"
                                   f"{p.name}")
                            shutil.copyfile(p, dst)
                            final.append(dst.name)
                        out["cards"][key] = {
                            "rid": rid, "cid": cid, "pngs": final,
                            "logs": cap.lines,
                            "attached": [
                                {kk: vv for kk, vv in c.items() if kk not in
                                 ("imageUrl", "referenceImageUrl")}
                                for c in (attached.get("comparisons") or [])
                            ],
                            "uSec": v["uSec"], "rSec": v["rSec"],
                            "stills": next(
                                (pk.get("stills") for ro in data["records"]
                                 for pk in ro.get("compressed") or []
                                 if ro["rid"] == rid and pk["cid"] == cid),
                                None),
                        }
                    shutil.rmtree(tmp, ignore_errors=True)
                det = md5s[0] == md5s[1]
                out["cards"][key]["md5Run1"] = md5s[0]
                out["cards"][key]["md5Run2"] = md5s[1]
                out["cards"][key]["deterministic"] = det
                print(f"  RENDER {key}: cards={list(md5s[0])} determinism="
                      f"{'SAME' if det else 'DIFFER'}")
        finally:
            app._s3, app._signed_get = orig_s3, orig_signed
            fs_admin.update_analysis_fault_zoom = orig_update
            app.firestore_admin.update_analysis_fault_zoom = orig_update
            cg.machine_eye = _orig_eye
            fe_mod.FfmpegFrameExtractor = _base
        out["eyeCallsPerRecord"] = {
            f"{k[0]}/{k[1]}": v for k, v in _EYE_STATE["per_record"].items()
            if k[0] == m}
        (EV / m / "render_verdict.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1))
        allout[m] = out
    return allout


# ── check (Task 1 게이트) ───────────────────────────────────────────────────

def check() -> int:
    fails: list[str] = []
    n_rec = 0
    vr = EV / "VISUAL-REVIEW.md"
    vtxt = vr.read_text() if vr.exists() else ""
    if not vr.exists():
        fails.append("VISUAL-REVIEW.md 부재 (frames-before-numbers 미이행)")
    for m in SWEEP_JOBS:
        p = EV / m / "candidates.json"
        if not p.exists():
            fails.append(f"{m}/candidates.json 부재")
            continue
        data = json.loads(p.read_text())
        meta = data.get("meta") or {}
        gate = meta.get("sourceGate") or {}
        if "passed" not in gate:
            fails.append(f"{m} sourceGate 판정 부재")
            continue
        if not gate["passed"]:
            # 로컬 불가 = 정직 박제. 사유가 있어야 한다.
            if not gate.get("reasons"):
                fails.append(f"{m} sourceGate FAIL 인데 사유 미기재")
            continue
        chk = (gate.get("checks") or {}).get("fpsCrossCheck") or {}
        for which in ("user", "ref"):
            r = (chk.get(which) or {}).get("framesOverDuration")
            if r is None or abs(r - float(meta.get("alignFps") or 0)) > FPS_CHECK_TOL:
                fails.append(f"{m} align fps 교차검증 실패 ({which}: {r})")
        recs = data.get("records") or []
        exp = RECORD_INVENTORY.get(m)
        if exp is not None and len(recs) != exp:
            fails.append(f"{m} record 커버리지 {len(recs)} != 인벤토리 {exp}")
        n_rec += len(recs)
        for ro in recs:
            for k in ("scan", "dropDistribution", "candidates", "approvedFreeze",
                      "eyeEligible"):
                if k not in ro:
                    fails.append(f"{m}/{ro.get('rid')} {k} 부재")
            for pk in ro.get("compressed") or []:
                st = pk.get("stills") or {}
                for side in ("user", "ref"):
                    sp = st.get(side)
                    if not sp or not (_HERE / sp).exists():
                        fails.append(
                            f"{m}/{ro['rid']}/{pk['cid']} still {side} 실물 부재")
                tag = f"{m}/{ro['rid']}/{pk['cid']}"
                if vtxt and tag not in vtxt:
                    fails.append(f"VISUAL-REVIEW.md 에 {tag} 기록 없음")
    if n_rec != sum(RECORD_INVENTORY.values()):
        fails.append(f"record 총 커버리지 {n_rec}/{sum(RECORD_INVENTORY.values())}")
    if fails:
        print("CHECK FAIL:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"CHECK PASS (5 motions, records {n_rec}/"
          f"{sum(RECORD_INVENTORY.values())}, stills+VISUAL-REVIEW 전건)")
    return 0


def main() -> int:
    global _CACHE_ROOT
    apr = argparse.ArgumentParser()
    apr.add_argument("--fetch", action="store_true")
    apr.add_argument("--scan", action="store_true")
    apr.add_argument("--pairsheet", action="store_true")
    apr.add_argument("--eye", action="store_true")
    apr.add_argument("--render", action="store_true")
    apr.add_argument("--check", action="store_true")
    apr.add_argument("--motions", default=",".join(SWEEP_JOBS))
    apr.add_argument("--only", default="",
                     help="쉼표구분 {motion}/{rid}/{cid} (eye 대상 한정)")
    apr.add_argument("--cache-root", default=os.environ.get("EHZ_CACHE_ROOT", ""),
                     help="캐시 루트 (실행 세션 scratchpad 하위 — 휘발)")
    args = apr.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.cache_root:
        _CACHE_ROOT = pathlib.Path(args.cache_root)
        _CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    motions = [m for m in args.motions.split(",") if m in SWEEP_JOBS]
    EV.mkdir(parents=True, exist_ok=True)
    if args.fetch:
        for m in motions:
            print(f"══ FETCH {m} ══")
            g = source_gate(m, download=True)
            print(f"  source gate {'PASS' if g['passed'] else 'FAIL'} "
                  f"{g.get('reasons') or ''}")
            if g["passed"]:
                mount(m)
    if args.scan:
        scan(motions)
    if args.pairsheet:
        pairsheet(motions)
    if args.eye:
        only = {s for s in args.only.split(",") if s} or None
        eye(motions, only)
    if args.render:
        render(motions)
    if args.check:
        return check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
