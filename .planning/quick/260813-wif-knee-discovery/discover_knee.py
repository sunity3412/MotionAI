#!/usr/bin/env python3
"""왼무릎 신규 발굴 하네스 (quick-260813-wif) — 판정 재료 생산 전용.

belle fresh 영상(doc p34fresh1786628533)의 진짜 결함 = 왼무릎(다리 안 폄)이
ufb freeze-only 구조에서 침묵(freeze u10.504 가 hold=moving)인 케이스를,
시스템이 스스로 옳은 순간을 잡는 발굴로 회복 후보화한다. 운영 코드 무접촉 —
card_gates / fault_zoom / compare_align / app 헬퍼는 전부 **임포트 재사용**
(수정 0), 게이트 임계 = ii0 SWEEP-REPORT §2 확정값 그대로 (재튜닝 0).

stages:
  --fetch   Firestore doc p34fresh1786628533 + refmotion + S3 read-only 영상
            → 세션 scratchpad 캐시 (ufb verify_local --fetch 패턴 상속).
            align = compare_align.build_align + P35 트랙 replay (운영 미러 —
            replay 의 프레임 수 정확 일치가 영상 정체성 게이트).
  --scan    클립 전 구간 홀드 후보 스캔 (hold_gate, 3창 Theil-Sen) + 기준측
            짝 탐색 (align 매핑 이웃 창 ±2s — nh4 교훈: 전역 포즈 유사도 최소
            선택 금지, 시퀀스 순서 제약을 창이 강제) + kpo/ufb 대조 행 +
            전신 프레임 짝 stills 덤프 → evidence/candidates.json
  --eye     최종 후보 기계 눈 실판정 (card_gates.machine_eye, user claim=bent
            + ref claim=extended + 양측 limb=leg — kpo 왼무릎 인증 동일 의미론).
            상한 16회/record 코드 강제 + eye_calls.log + eye_ledger/ 원장.
  --render  눈 PASS 후보를 운영 헬퍼(app._run_gated_card_inherit) 그대로 렌더
            — build_fault_zoom_comparisons override + criterion_units +
            native_frame_at + label_fps(실효 fps) 경로를 헬퍼가 소유 (새 문법
            발명 0, 스타일 파라미터 신규 0). S3/Firestore 는 로컬 스텁.
            같은 입력 2회 재렌더 md5 결정론 기록 (2회차 눈 = 1회차 판정 replay).
  --check-candidates  Task 1 검증 게이트 (candidates.json 스키마 + stills 실물
            + VISUAL-REVIEW.md 육안 기록 존재 — frames-before-numbers 강제).

초 환산 규율 (u8i 준수): align 타임베이스 15fps (재추출 정본 — xa1 R2 에서
게이트 인덱스 공식 round(sec x 15)이 실초와 일치함을 운영 실증). 9.0/18.0
라벨 분모 사용 0 — 렌더 override 의 초->프레임 환산은 운영 _override_idx
(probe_effective_fps + rep9 역변환)가 소유. 캐시 프레임 수/길이 유도로
align fps 를 교차검증해 meta 에 박제한다.

S3 read-only (업로드 0) · Pod 무접촉 · Firestore 쓰기 0 · Gemini = machine_eye
실호출만. 키 = SSM --profile sunity-motion (키 값 로그 금지).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import logging
import os
import pathlib
import shutil
import sys
import types

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "backend" / "shared" / "python"))
sys.path.insert(0, str(_REPO / "backend" / "functions" / "pipeline"))

# ── 좌표 (PLAN.md — locked) ──────────────────────────────────────────────────
UID = "fvcNXzEqKjgqVxRPVSj1iwFnIpn2"
AID = "p34fresh1786628533"
MOTION_ID = "ref-pdshape"
BUCKET = "sunity-motion-pilot-videos"
REF_VIDEO_KEY = "reference/ref-pdshape.mp4"

# kpo 실적 짝 — belle 육안 인증 (260811-kpo evidence/post-judgment.md:
# "실제 순간: user 12.80s / ref 12.24s", SUMMARY 표기 12.8/12.3).
KPO_PAIR = (12.80, 12.24)
# ufb freeze (침묵 원점) — 260811-ufb evidence/run_verdict.json r04:
# u 10.503501167055687 / r 9.4, dropped hold=moving.
UFB_FREEZE = (10.503501167055687, 9.4)

# 기계 눈 상한 (kpo T-kpo-03 기결론 — record 당 16회, 코드 강제)
EYE_CALL_CAP = 16

# 기준 짝 탐색 창 = align 매핑 이웃 ±2s (PLAN Task 1 (3) 명시값 — 시퀀스 순서
# 제약. 게이트 임계 아님: 탐색 범위 한정자다. 게이트 수치는 전부 card_gates
# 모듈 상수(ii0 확정값)를 그대로 쓴다 — 이 파일에 임계 신설 0.)
PAIR_WINDOW_S = 2.0

SP = pathlib.Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "ae166167-1abf-4754-9fe8-336a719ef9e2/scratchpad"
) / "wif_fresh"
DATA = _REPO / ".planning/phases/35-server-rendered-comparison-video/data"
EV = _HERE / "evidence"

DOC = SP / "doc.json"
REFMOTION = SP / "refmotion.json"
ALIGN_JSON = SP / "align.json"
VIDEOS = {"user": SP / "user.mp4", "ref": SP / "ref.mp4"}
ALIGN_WORK = SP / "align_work"
RENDER_WORK = SP / "render"

log = logging.getLogger("discover_knee")


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


# ── fetch ────────────────────────────────────────────────────────────────────

def fetch() -> None:
    """doc(대상 AID) + refmotion + 영상 → scratchpad 캐시 + align 산출.

    scratchpad 는 휘발 — 보존 재료는 wif evidence/ 커밋분만. 영상은 S3
    read-only 다운로드 (기존 로컬 캐시 재사용 허용 — 같은 S3 키). doc 은
    반드시 AID=p34fresh1786628533 실물 (구 doc 재사용 금지).
    """
    SP.mkdir(parents=True, exist_ok=True)
    if not DOC.exists() or not REFMOTION.exists():
        _ensure_firebase_env()
        from sunity_shared import firestore_admin as fa

        doc = (
            fa._db().collection("users").document(UID)  # noqa: SLF001
            .collection("analyses").document(AID).get().to_dict()
        )
        if not doc or "result" not in doc:
            raise SystemExit(f"doc {AID} 조회 실패 또는 result 부재")
        DOC.write_text(json.dumps({"result": doc["result"]}))
        ref = fa.get_reference_motion(MOTION_ID)
        REFMOTION.write_text(json.dumps(
            {"referenceKeypointReport": ref["referenceKeypointReport"]}))
        print(f"fetched doc {AID} + refmotion -> {SP}")

    res = json.loads(DOC.read_text())["result"]
    user_key = str(res.get("myVideoKey") or "")
    if not user_key:
        raise SystemExit("doc myVideoKey 부재 — 사용자 영상 키 미확정")
    s3 = None
    for which, key in (("user", user_key), ("ref", REF_VIDEO_KEY)):
        p = VIDEOS[which]
        if not p.exists():
            s3 = s3 or _s3_client()
            s3.download_file(BUCKET, key, str(p))
            print(f"fetched {which} video {p.stat().st_size} bytes")

    if not ALIGN_JSON.exists():
        from sunity_shared.analysis import compare_align

        records = (res.get("deductionBreakdown") or {}).get("records") or []
        p35 = json.loads((DATA / "pdshapefault" / "align.json").read_text())
        tracks = {}
        for side in ("user", "ref"):
            F = int(p35[f"{side}Frames"])
            W, H = p35[f"{side}Size"]
            kp = np.asarray(p35[f"{side}Kp"], dtype=float).reshape(F, 17, 2)
            sc = np.asarray(p35[f"{side}Score"], dtype=float).reshape(F, 17)
            tracks[F] = (kp * np.array([W, H], dtype=float), sc, W, H)

        def infer_fn(frames):
            """P35 트랙 replay — 프레임 수 정확 일치 강제 (fail-closed).

            같은 원본 영상(md5 일치 — ii0 08-08 실증) + RTMW_DETERMINISTIC
            세대 트랙이라 Pod 재추론과 등가. 불일치 = 영상 정체성 FAIL.
            """
            got = tracks.get(len(frames))
            if got is None:
                raise SystemExit(
                    f"replay 프레임 수 불일치: {len(frames)} not in "
                    f"{sorted(tracks)} — 캐시 영상이 대상 영상이 아님")
            return got

        ALIGN_WORK.mkdir(parents=True, exist_ok=True)
        align = compare_align.build_align(
            VIDEOS["user"], VIDEOS["ref"], records, ALIGN_WORK,
            infer_fn=infer_fn,
        )
        ALIGN_JSON.write_text(json.dumps(align))
        print(f"align built: userFrames={align['userFrames']} "
              f"refFrames={align['refFrames']} fps={align['fps']}")
    print("fetch OK")


# ── 트랙 로드 + 파생 ─────────────────────────────────────────────────────────

def _load_ctx():
    from sunity_shared.analysis import card_gates as cg

    res = json.loads(DOC.read_text())["result"]
    align = json.loads(ALIGN_JSON.read_text())
    urep = cg.align_to_report(align, "user")
    rrep = cg.align_to_report(align, "ref")
    afps = float(align["fps"])
    usize, rsize = tuple(align["userSize"]), tuple(align["refSize"])
    poles = {}
    for side in ("user", "ref"):
        p = RENDER_WORK / f"pole_{side}.json"
        poles[side] = (json.loads(p.read_text()).get("xNorm")
                       if p.exists() else None)
    return types.SimpleNamespace(
        cg=cg, res=res, align=align, urep=urep, rrep=rrep, afps=afps,
        usize=usize, rsize=rsize, poles=poles,
        u_torso=cg.torso_px_median(urep, usize),
        r_torso=cg.torso_px_median(rrep, rsize),
    )


def _target_record(res: dict, joint: str) -> dict:
    """crit_joint(criterion) == joint 인 record 특정 (동작명/ID 리터럴 분기 0
    — 대상 관절은 CLI 파라미터, 판별은 card_gates.crit_joint 구조 함수)."""
    from sunity_shared.analysis import card_gates as cg

    for r in (res.get("deductionBreakdown") or {}).get("records") or []:
        crit = str(r.get("criterion") or "")
        if crit and cg.crit_joint(crit.split("__")[-1]) == joint:
            return r
    raise SystemExit(f"criterion 에 {joint} 귀속 record 부재")


def _conf_min_of(cg, rep: dict, idx: int, joint: str) -> float | None:
    """관절각 삼각(JOINT_ANGLES) 좌표들의 align conf 최소값 (신뢰 근거 박제)."""
    from sunity_shared.analysis import fault_zoom as fz
    from sunity_shared.analysis.skeleton import JOINT_ANGLES

    tri = JOINT_ANGLES.get(joint)
    if tri is None:
        return None
    vals = []
    for n in tri:
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
        ctx.urep, u_idx, ctx.rrep, r_idx,
        ctx.poles["user"], ctx.poles["ref"],
        user_size=ctx.usize, ref_size=ctx.rsize,
        user_torso_px=ctx.u_torso, ref_torso_px=ctx.r_torso,
    )
    ua = cg.joint_angle(ctx.urep, u_idx, joint)
    ra = cg.joint_angle(ctx.rrep, r_idx, joint)
    return {
        "uSec": round(u_idx / ctx.afps, 4), "uIdx": u_idx,
        "rSec": round(r_idx / ctx.afps, 4), "rIdx": r_idx,
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


def _dump_still(side: str, sec: float, name: str) -> str | None:
    """30fps 1080p 렌더 프레임(운영 _frame_at 공식 round(sec x 30)+1)을
    evidence/stills/ 로 복사. 전신 프레임 실물 (frames-before-numbers)."""
    from sunity_shared.analysis import compare_render as _cr

    tag = f"{int(_cr.FPS_OUT)}_{_cr.PANEL_H}"
    d = RENDER_WORK / (f"u{tag}" if side == "user" else f"r{tag}")
    n = len(list(d.glob("*.jpg")))
    if n <= 0:
        return None
    idx = max(1, min(n, round(sec * float(_cr.FPS_OUT)) + 1))
    src = d / f"{idx:05d}.jpg"
    out = EV / "stills" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out)
    return str(out.relative_to(_HERE))


# ── scan (홀드 후보 + 기준 짝 + 대조 행 + stills) ────────────────────────────

def scan(joint: str) -> dict:
    ctx = _load_ctx()
    cg = ctx.cg
    rec = _target_record(ctx.res, joint)
    crit = str(rec.get("criterion") or "")
    uF, rF = int(ctx.urep["frames"]), int(ctx.rrep["frames"])

    # 실효 fps 교차검증 (u8i 규율) — align fps 라벨 vs 캐시 프레임 수/길이.
    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
    ext = FfmpegFrameExtractor(target_fps=9.0, max_side=640)
    eff = {}
    for which, p in (("user", VIDEOS["user"]), ("ref", VIDEOS["ref"])):
        eff[which] = float(ext.probe_effective_fps(str(p)))
    import imageio
    durs = {}
    for which, p in (("user", VIDEOS["user"]), ("ref", VIDEOS["ref"])):
        reader = imageio.get_reader(str(p))
        try:
            durs[which] = float(reader.get_meta_data().get("duration") or 0.0)
        finally:
            reader.close()
    align_fps_check = {
        "user": round(uF / durs["user"], 3) if durs["user"] else None,
        "ref": round(rF / durs["ref"], 3) if durs["ref"] else None,
    }

    # (2) 홀드 스캔 — 클립 전 구간, 프레임 단위. 원시 연속 run 은 전건 박제,
    # 후보 단위는 1초 클러스터 버킷 (kpo 눈 지연 평가의 클러스터 선례 —
    # 게이트 임계 아님, 표 granularity 만).
    holds_u = [cg.hold_gate(ctx.urep, f, joint) for f in range(uF)]
    pass_idx = [f for f, h in enumerate(holds_u) if h.passed]
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
            "bucketSec": b,
            "startF": min(fs), "endF": max(fs),
            "startSec": round(min(fs) / ctx.afps, 4),
            "endSec": round(max(fs) / ctx.afps, 4),
            "passFrames": len(fs),
            "repF": rep,
            "repSec": round(rep / ctx.afps, 4),
            "minDps": holds_u[rep].speed_dps,
        })

    # 기준측 홀드 캐시
    holds_r: dict[int, object] = {}

    def _hold_r(r_idx: int):
        if r_idx not in holds_r:
            holds_r[r_idx] = cg.hold_gate(ctx.rrep, r_idx, joint)
        return holds_r[r_idx]

    curve = ctx.align["curveRefSec"]

    # (3) 기준 짝 — align 매핑 이웃 창 (시퀀스 순서 제약, 전역 최소 금지).
    # 짝 2종 병기: ① poseMin(중립 — 창 내 양측홀드+짝정합 중 포즈거리 최소)
    # ② eyeEligible(kpo 의미론 — "눈 확정 가능한 후보 중 포즈 최소": user
    #   claim=bent 대표에 대해 ref 트랙 claim=extended 인 r 만 대상).
    # 포즈 유사도 최소는 결함(굽힘 차이)을 되레 지우는 방향이라(nh4 교훈의
    # 거울) ①만으로는 결함 짝이 원리적으로 안 나온다 — ②가 kpo 인증 짝의
    # 생산 규칙이다. claim 이분은 card_gates 기존 상수 (신규 임계 0).
    def _pair_search(u_idx: int, r_center: float, need_ext: bool):
        lo = max(0, int(round((r_center - PAIR_WINDOW_S) * ctx.afps)))
        hi = min(rF - 1, int(round((r_center + PAIR_WINDOW_S) * ctx.afps)))
        best = None
        for r_idx in range(lo, hi + 1):
            if not _hold_r(r_idx).passed:
                continue  # 양측 홀드 (기준측 hold 포함)
            if need_ext:
                rc = cg.track_claim(cg.joint_angle(ctx.rrep, r_idx, joint))
                if rc != "extended":
                    continue
            pair = cg.pair_gate(
                ctx.urep, u_idx, ctx.rrep, r_idx,
                ctx.poles["user"], ctx.poles["ref"],
                user_size=ctx.usize, ref_size=ctx.rsize,
                user_torso_px=ctx.u_torso, ref_torso_px=ctx.r_torso,
            )
            if not pair.passed:
                continue
            if best is None or (pair.pose_dist or 9e9) < (best[1].pose_dist or 9e9):
                best = (r_idx, pair)
        return best, lo, hi

    candidates: list[dict] = []
    for i, run in enumerate(runs):
        u_idx = run["repF"]
        r_center = float(curve[min(u_idx, len(curve) - 1)])
        best, lo, hi = _pair_search(u_idx, r_center, need_ext=False)
        cand: dict = {
            "id": f"cand{i + 1:02d}",
            "holdRun": {k: run[k] for k in
                        ("startSec", "endSec", "repSec", "minDps",
                         "passFrames")},
            "alignRefSec": round(r_center, 4),
        }
        if best is None:
            cand["row"] = _gate_row(
                ctx, u_idx,
                max(0, min(rF - 1, int(round(r_center * ctx.afps)))), joint)
            cand["pairFound"] = False
            cand["pairFail"] = ("창 내 양측홀드+짝정합 동시 통과 r_idx 없음 "
                                f"(창 {round(lo / ctx.afps, 2)}"
                                f"~{round(hi / ctx.afps, 2)}s)")
        else:
            cand["row"] = _gate_row(ctx, u_idx, best[0], joint)
            cand["pairFound"] = True

        # bent 대표 (버킷 pass 프레임 중 user claim=bent 최저 각속도) + kpo
        # 의미론 짝 (ref claim=extended 한정 포즈 최소)
        bent_frames = [
            f for f in buckets[run["bucketSec"]]
            if cg.track_claim(cg.joint_angle(ctx.urep, f, joint)) == "bent"
        ]
        if bent_frames:
            bent_rep = min(bent_frames, key=lambda f: (
                holds_u[f].speed_dps if holds_u[f].speed_dps is not None
                else float("inf")))
            b_center = float(curve[min(bent_rep, len(curve) - 1)])
            b_best, b_lo, b_hi = _pair_search(bent_rep, b_center,
                                              need_ext=True)
            if b_best is not None:
                cand["bentRow"] = _gate_row(ctx, bent_rep, b_best[0], joint)
                cand["bentPairFound"] = True
            else:
                cand["bentRow"] = _gate_row(
                    ctx, bent_rep,
                    max(0, min(rF - 1, int(round(b_center * ctx.afps)))),
                    joint)
                cand["bentPairFound"] = False
                cand["bentPairFail"] = (
                    "창 내 ref claim=extended + 양측홀드 + 짝정합 동시 통과 "
                    f"없음 (창 {round(b_lo / ctx.afps, 2)}"
                    f"~{round(b_hi / ctx.afps, 2)}s)")
        # kpo 실적 짝과의 관계 (재발견/신규 판별 재료)
        cand["kpoRelation"] = {
            "dUserSec": round(abs(u_idx / ctx.afps - KPO_PAIR[0]), 3),
            "coversKpoUser": bool(
                run["startSec"] - 0.001 <= KPO_PAIR[0] <= run["endSec"] + 0.001),
        }
        candidates.append(cand)

    # 대조 행 (필수 — kpo 실적 짝 + ufb freeze)
    kpo_r_idx = max(0, min(rF - 1, int(round(KPO_PAIR[1] * ctx.afps))))
    contrast = {
        "kpo": {
            "label": "kpo 실적 짝 (belle 육안 인증, post-judgment.md "
                     "u12.80/r12.24 — SUMMARY 표기 12.8/12.3)",
            "row": _gate_row(
                ctx,
                max(0, min(uF - 1, int(round(KPO_PAIR[0] * ctx.afps)))),
                kpo_r_idx, joint),
            # 기준측 홀드 경계 민감성 프로브 (kpo "hold 양측 PASS" 박제와의
            # 재계산 대조 — 이웃 인덱스 판정을 그대로 기록)
            "refHoldNeighbors": {
                str(i): {
                    "sec": round(i / ctx.afps, 4),
                    "passed": _hold_r(i).passed,
                    "speedDps": _hold_r(i).speed_dps,
                }
                for i in range(max(0, kpo_r_idx - 3),
                               min(rF, kpo_r_idx + 4))
            },
        },
        "ufbFreeze": {
            "label": "ufb 영상 freeze r04 (침묵 원점 — run_verdict.json "
                     "hold=moving)",
            "row": _gate_row(
                ctx,
                max(0, min(uF - 1, int(round(UFB_FREEZE[0] * ctx.afps)))),
                max(0, min(rF - 1, int(round(UFB_FREEZE[1] * ctx.afps)))),
                joint),
        },
    }

    # (4) stills — 짝 성립 후보 전건 + 대조 행 (frames-before-numbers 재료)
    for cand in candidates:
        row = cand["row"]
        cand["stills"] = {
            "user": _dump_still(
                "user", row["uSec"], f"{cand['id']}_user_{row['uSec']}s.jpg"),
            "ref": _dump_still(
                "ref", row["rSec"], f"{cand['id']}_ref_{row['rSec']}s.jpg"),
        }
        brow = cand.get("bentRow")
        if brow and (brow["uIdx"] != row["uIdx"] or brow["rIdx"] != row["rIdx"]):
            cand["bentStills"] = {
                "user": _dump_still(
                    "user", brow["uSec"],
                    f"{cand['id']}b_user_{brow['uSec']}s.jpg"),
                "ref": _dump_still(
                    "ref", brow["rSec"],
                    f"{cand['id']}b_ref_{brow['rSec']}s.jpg"),
            }
    for key, ent in contrast.items():
        row = ent["row"]
        ent["stills"] = {
            "user": _dump_still(
                "user", row["uSec"], f"{key}_user_{row['uSec']}s.jpg"),
            "ref": _dump_still(
                "ref", row["rSec"], f"{key}_ref_{row['rSec']}s.jpg"),
        }

    out = {
        "meta": {
            "uid": UID, "aid": AID, "motionId": MOTION_ID,
            "recordId": rec.get("recordId"), "criterion": crit,
            "joint": joint,
            "alignFps": ctx.afps,
            "alignFpsCheck_framesOverDuration": align_fps_check,
            "probeEffectiveFps": eff,
            "clip": {"userFrames": uF, "refFrames": rF,
                     "userDurS": round(durs["user"], 3),
                     "refDurS": round(durs["ref"], 3)},
            "poles": ctx.poles,
            "thresholds": {
                "source": "260811-ii0-SWEEP-REPORT §2 (card_gates 모듈 상수 "
                          "— 재튜닝 0)",
                "holdMaxDps": cg.HOLD_MAX_DPS, "poseMax": cg.PAIR_POSE_MAX,
                "poleDiffMax": cg.POLE_DIFF_MAX, "confMin": cg.HOLD_CONF_MIN,
                "pairWindowS": PAIR_WINDOW_S,
            },
            "generated": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        },
        "scan": {"passFrames": len(pass_idx), "totalFrames": uF,
                 "rawRuns": raw_runs, "buckets": runs},
        "candidates": candidates,
        "contrast": contrast,
    }
    EV.mkdir(exist_ok=True)
    (EV / "candidates.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(f"scan: pass {len(pass_idx)}/{uF} frames, runs {len(runs)}, "
          f"pairFound {sum(1 for c in candidates if c['pairFound'])}")
    for c in candidates:
        r = c["row"]
        print(f"  {c['id']} u={r['uSec']}s ({c['holdRun']['startSec']}~"
              f"{c['holdRun']['endSec']}s, min {c['holdRun']['minDps']:.1f}d/s)"
              f" pair={'OK' if c['pairFound'] else 'NONE'} "
              f"r={r['rSec']}s pose={r['pair']['poseDist']} "
              f"poleDiff={r['pair']['poleDiff']} uAngle={r['uAngleDeg']} "
              f"rAngle={r['rAngleDeg']} uClaim={r['uClaim']} "
              f"rClaim={r['rClaim']} inv=({r['uInverted']},{r['rInverted']})")
        b = c.get("bentRow")
        if b:
            print(f"    BENT u={b['uSec']}s uAngle={b['uAngleDeg']} "
                  f"eyePair={'OK' if c.get('bentPairFound') else 'NONE'} "
                  f"r={b['rSec']}s rAngle={b['rAngleDeg']} "
                  f"pose={b['pair']['poseDist']} "
                  f"poleDiff={b['pair']['poleDiff']} "
                  f"holdU={b['holdUser']['reason']}"
                  f"({b['holdUser']['speedDps']}) "
                  f"holdR={b['holdRef']['reason']}")
    for k, ent in contrast.items():
        r = ent["row"]
        print(f"  [{k}] u={r['uSec']} r={r['rSec']} "
              f"holdU={r['holdUser']['reason']}({r['holdUser']['speedDps']}) "
              f"holdR={r['holdRef']['reason']} pair={r['pair']['reason']} "
              f"pose={r['pair']['poseDist']} uAngle={r['uAngleDeg']} "
              f"rAngle={r['rAngleDeg']}")
    return out


# ── eye (기계 눈 실판정 — 상한 16회 코드 강제 + 원장) ────────────────────────

_EYE_STATE = {"calls": 0, "memo": {}}


def _eye_call(cg, side: str, rep: dict, idx: int, joint: str, claim: str,
              frame_rgb, cand_id: str, afps: float = 15.0) -> dict:
    """machine_eye 래퍼 — 전역 상한(EYE_CALL_CAP) 코드 강제 + 호출 로그 +
    원장(크롭 PNG + claim/판정/conf JSON) 적재. 같은 (측,프레임,관절,claim)
    은 메모 재사용 (실호출 1회 — 상한은 실호출만 계수)."""
    key = (side, int(idx), joint, claim)
    logp = EV / "eye_calls.log"
    if key in _EYE_STATE["memo"]:
        got = dict(_EYE_STATE["memo"][key])
        got["cached"] = True
        with open(logp, "a") as fh:
            fh.write(f"CACHED cand={cand_id} side={side} idx={idx} "
                     f"claim={claim} -> {got['observed']}/{got['limb']} "
                     f"match={got['match']} (실호출 계수 불변 "
                     f"{_EYE_STATE['calls']}/{EYE_CALL_CAP})\n")
        return got
    if _EYE_STATE["calls"] >= EYE_CALL_CAP:
        with open(logp, "a") as fh:
            fh.write(f"CAP cand={cand_id} side={side} idx={idx} claim={claim} "
                     f"-> 미판정 (상한 {EYE_CALL_CAP} 도달)\n")
        return {"observed": "cap_exceeded", "limb": None, "match": False,
                "confidence": 0.0, "reason": "call cap", "crop": None,
                "cached": False}
    _ensure_gemini_key()
    H, W = frame_rgb.shape[:2]
    xy = cg.kp(rep, idx, joint, conf_min=0.0)
    if xy is None:
        return {"observed": "no_kp", "limb": None, "match": False,
                "confidence": 0.0, "reason": "align 좌표 부재", "crop": None,
                "cached": False}
    _EYE_STATE["calls"] += 1
    res = cg.machine_eye(
        frame_rgb, (xy[0] * W, xy[1] * H), claim,
        api_key=os.environ["GEMINI_API_KEY"],
        expected_limb=cg.joint_limb(joint),
        crop_px=max(320, W // 2),
    )
    n = _EYE_STATE["calls"]
    with open(logp, "a") as fh:
        fh.write(f"CALL {n:02d}/{EYE_CALL_CAP} cand={cand_id} side={side} "
                 f"idx={idx} sec={idx / afps:.3f} claim={claim} "
                 f"observed={res['observed']} limb={res['limb']} "
                 f"match={res['match']} conf={res['confidence']}\n")
    led = EV / "eye_ledger"
    led.mkdir(parents=True, exist_ok=True)
    stem = f"{n:02d}_{cand_id}_{side}_{joint}_{claim}"
    if res.get("crop") is not None:
        res["crop"].save(led / f"{stem}.png")
    (led / f"{stem}.json").write_text(json.dumps({
        "cand": cand_id, "side": side, "frameIdx": int(idx),
        "sec": round(idx / afps, 3), "joint": joint, "claim": claim,
        "observed": res["observed"], "limb": res["limb"],
        "match": bool(res["match"]), "confidence": res["confidence"],
        "reason": res["reason"],
    }, ensure_ascii=False, indent=1))
    _EYE_STATE["memo"][key] = {k: v for k, v in res.items() if k != "crop"}
    # 헬퍼 키 공간에도 등재 — render 단계의 운영 헬퍼 user 측 눈이 같은
    # (프레임, 관절, claim) 판정을 재사용하게 (실호출 중복 억제, 판정 동일).
    H2, W2 = frame_rgb.shape[:2]
    _EYE_STATE["memo"][(
        "helper", claim, cg.joint_limb(joint),
        int(xy[0] * W2), int(xy[1] * H2),
    )] = _EYE_STATE["memo"][key]
    out = dict(_EYE_STATE["memo"][key])
    out["cached"] = False
    return out


def _frame_rgb(side: str, sec: float):
    from PIL import Image

    from sunity_shared.analysis import compare_render as _cr

    tag = f"{int(_cr.FPS_OUT)}_{_cr.PANEL_H}"
    d = RENDER_WORK / (f"u{tag}" if side == "user" else f"r{tag}")
    n = len(list(d.glob("*.jpg")))
    idx = max(1, min(n, round(sec * float(_cr.FPS_OUT)) + 1))
    return np.asarray(Image.open(d / f"{idx:05d}.jpg").convert("RGB"))


def _row_of(data: dict, cid: str) -> dict:
    """'candNN' -> row (중립 대표) / 'candNNb' -> bentRow (kpo 의미론 대표)."""
    base = cid[:-1] if cid.endswith("b") else cid
    c = {x["id"]: x for x in data["candidates"]}[base]
    return c["bentRow"] if cid.endswith("b") else c["row"]


def eye(joint: str, cand_ids: list[str]) -> dict:
    """최종 후보의 user 접힘 + ref 신전 + 양측 leg 확정 (kpo 인증 동일 의미론).

    눈이 기각하면 그 기각도 재료 — 재시도/크롭 재조정 조작 금지 (1후보 1판정)."""
    ctx = _load_ctx()
    cg = ctx.cg
    data = json.loads((EV / "candidates.json").read_text())
    verdicts = {}
    for cid in cand_ids:
        row = _row_of(data, cid)
        u = _eye_call(cg, "user", ctx.urep, row["uIdx"], joint, "bent",
                      _frame_rgb("user", row["uSec"]), cid, afps=ctx.afps)
        r = _eye_call(cg, "ref", ctx.rrep, row["rIdx"], joint, "extended",
                      _frame_rgb("ref", row["rSec"]), cid, afps=ctx.afps)
        verdicts[cid] = {
            "user": {k: u[k] for k in
                     ("observed", "limb", "match", "confidence", "reason")},
            "ref": {k: r[k] for k in
                    ("observed", "limb", "match", "confidence", "reason")},
            "eyePass": bool(u["match"] and r["match"]),
        }
        print(f"EYE {cid}: user bent->{u['observed']}/{u['limb']} "
              f"match={u['match']} | ref extended->{r['observed']}/{r['limb']} "
              f"match={r['match']} => {'PASS' if verdicts[cid]['eyePass'] else 'FAIL'}")
    (EV / "eye_verdicts.json").write_text(
        json.dumps(verdicts, ensure_ascii=False, indent=1))
    print(f"eye calls total {_EYE_STATE['calls']}/{EYE_CALL_CAP}")
    return verdicts


# ── render (운영 헬퍼 그대로 — 확정 문법, 새 문법 발명 0) ────────────────────

class _S3Stub:
    """put_object 를 로컬 저장으로 대체 (S3 read-only 제약 — 업로드 0).

    /eye/ 키(운영 원장)는 eye_ledger/ 로, 카드 PNG 는 cards_dir 로 라우팅."""

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


def render(joint: str, cand_ids: list[str]) -> dict:
    """후보별 운영 헬퍼(app._run_gated_card_inherit) 1회 = 카드 1안.

    보조 렌더 경로 없음 — 순간만 후보 짝으로 주입한 freeze 1건 report 를 먹여
    헬퍼가 소유한 확정 문법(fault_zoom.build_fault_zoom_comparisons override +
    criterion_units + native_frame_at + display_anchor 단일 출처 + align_bake +
    label_fps 실효 fps)을 그대로 통과시킨다. 스타일 파라미터 신규 0.
    같은 입력 2회 재렌더 md5 비교 (2회차 눈 = 1회차 판정 memo replay)."""
    _ensure_gemini_key()
    import app  # backend/functions/pipeline — 운영 모듈 그대로
    from sunity_shared import firestore_admin as fs_admin
    from sunity_shared.analysis import card_gates as cg

    # 9fps 추출 memo (드라이버 프로세스 한정 — 산출 byte 동일, 시간 절약)
    from sunity_shared.analysis import frame_extractor as fe_mod
    _base = fe_mod.FfmpegFrameExtractor

    class _CachingExtractor(_base):
        _cache: dict = {}

        def extract(self, path):
            key = (str(path), self.target_fps, self.max_side)
            if key not in self._cache:
                self._cache[key] = super().extract(path)
            return self._cache[key]

    # 헬퍼 내부 machine_eye 도 전역 상한/원장 래퍼를 타게 (실호출 계수 단일화)
    _orig_eye = cg.machine_eye

    def _counting_eye(frame_rgb, joint_xy_px, claim, *, api_key,
                      expected_limb=None, crop_px=360,
                      model="gemini-3.5-flash", timeout_s=60.0):
        mk = ("helper", claim, expected_limb,
              int(joint_xy_px[0]), int(joint_xy_px[1]))
        # (측,프레임,관절,claim) 메모와 키 공간이 달라 프레임 좌표로 식별 —
        # 같은 후보 재렌더(2회차)에서 동일 키 재사용.
        if mk in _EYE_STATE["memo"]:
            got = dict(_EYE_STATE["memo"][mk])
            got["crop"] = None
            with open(EV / "eye_calls.log", "a") as fh:
                fh.write(f"CACHED helper claim={claim} xy={mk[3]},{mk[4]} -> "
                         f"{got['observed']} (계수 불변 "
                         f"{_EYE_STATE['calls']}/{EYE_CALL_CAP})\n")
            return got
        if _EYE_STATE["calls"] >= EYE_CALL_CAP:
            with open(EV / "eye_calls.log", "a") as fh:
                fh.write(f"CAP helper claim={claim} -> fail-closed\n")
            return {"observed": "cap_exceeded", "limb": None, "match": False,
                    "confidence": 0.0, "reason": "call cap", "crop": None}
        _EYE_STATE["calls"] += 1
        res = _orig_eye(frame_rgb, joint_xy_px, claim, api_key=api_key,
                        expected_limb=expected_limb, crop_px=crop_px,
                        model=model, timeout_s=timeout_s)
        with open(EV / "eye_calls.log", "a") as fh:
            fh.write(f"CALL {_EYE_STATE['calls']:02d}/{EYE_CALL_CAP} "
                     f"helper claim={claim} observed={res['observed']} "
                     f"limb={res['limb']} match={res['match']} "
                     f"conf={res['confidence']}\n")
        _EYE_STATE["memo"][mk] = {k: v for k, v in res.items() if k != "crop"}
        return res

    res_doc = json.loads(DOC.read_text())["result"]
    ref_report = json.loads(REFMOTION.read_text())["referenceKeypointReport"]
    align = json.loads(ALIGN_JSON.read_text())
    data = json.loads((EV / "candidates.json").read_text())
    rec = _target_record(res_doc, joint)
    rid = str(rec.get("recordId") or "").split(":")[0]

    out: dict = {"cards": {}, "eyeCallsBefore": _EYE_STATE["calls"]}
    cards_root = EV / "cards"
    cards_root.mkdir(parents=True, exist_ok=True)
    fe_mod.FfmpegFrameExtractor = _CachingExtractor
    cg.machine_eye = _counting_eye
    orig_s3, orig_signed = app._s3, app._signed_get  # noqa: SLF001
    orig_update = fs_admin.update_analysis_fault_zoom
    try:
        for cid in cand_ids:
            row = _row_of(data, cid)
            report = {"freezes": [{
                "rid": rid, "joint": joint,
                "userSec": float(row["uSec"]), "refSec": float(row["rSec"]),
                "pairSrc": "discovery",
            }], "excludedFreezes": []}
            md5s = []
            for run_i in (1, 2):
                tmp = cards_root / f"_{cid}_run{run_i}"
                if tmp.exists():
                    shutil.rmtree(tmp)
                stub = _S3Stub(tmp, EV / "eye_ledger")
                attached: dict = {}

                def _cap_update(uid, analysis_id, comparisons, status,
                                _sink=attached):
                    _sink["comparisons"] = comparisons
                    _sink["status"] = status

                cap = _LogCapture()
                logging.getLogger().addHandler(cap)
                app._s3 = stub
                app._signed_get = lambda bucket, key: f"stub://{key}"
                fs_admin.update_analysis_fault_zoom = _cap_update
                # app 모듈이 바인딩한 이름도 동일 스텁으로 (운영 코드 무접촉,
                # 드라이버 프로세스 한정)
                app.firestore_admin.update_analysis_fault_zoom = _cap_update
                try:
                    profile = types.SimpleNamespace(
                        category=None, motion_id=MOTION_ID)
                    app._run_gated_card_inherit(
                        result=res_doc, report=report, align=align,
                        render_workdir=RENDER_WORK,
                        user_video_path=str(VIDEOS["user"]),
                        reference_video_path=str(VIDEOS["ref"]),
                        user_report=res_doc.get("keypointReport"),
                        ref_report=ref_report,
                        profile=profile,
                        existing_comparisons=[],
                        uid=UID, analysis_id=f"{AID}-wif-{cid}",
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
                        dst = cards_root / f"{cid}_u{row['uSec']}s_r{row['rSec']}s_{p.name}"
                        shutil.copyfile(p, dst)
                        final.append(dst.name)
                    out["cards"][cid] = {
                        "pngs": final,
                        "logs": cap.lines,
                        "attached": [
                            {k: v for k, v in c.items() if k not in
                             ("imageUrl", "referenceImageUrl")}
                            for c in (attached.get("comparisons") or [])
                        ],
                        "uSec": row["uSec"], "rSec": row["rSec"],
                    }
                shutil.rmtree(tmp, ignore_errors=True)
            det = md5s[0] == md5s[1]
            out["cards"][cid]["md5Run1"] = md5s[0]
            out["cards"][cid]["md5Run2"] = md5s[1]
            out["cards"][cid]["deterministic"] = det
            print(f"RENDER {cid}: cards={list(md5s[0])} determinism="
                  f"{'SAME' if det else 'DIFFER'}")
    finally:
        app._s3, app._signed_get = orig_s3, orig_signed
        fs_admin.update_analysis_fault_zoom = orig_update
        app.firestore_admin.update_analysis_fault_zoom = orig_update
        cg.machine_eye = _orig_eye
        fe_mod.FfmpegFrameExtractor = _base
    out["eyeCallsAfter"] = _EYE_STATE["calls"]
    (EV / "render_verdict.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(f"render done — eye calls {_EYE_STATE['calls']}/{EYE_CALL_CAP}")
    return out


# ── check-candidates (Task 1 게이트) ────────────────────────────────────────

def check_candidates() -> int:
    fails: list[str] = []
    p = EV / "candidates.json"
    if not p.exists():
        print("FAIL: candidates.json 부재")
        return 1
    data = json.loads(p.read_text())
    meta = data.get("meta") or {}
    if not (meta.get("probeEffectiveFps") or {}).get("user"):
        fails.append("meta.probeEffectiveFps.user 부재 (실효 fps 미박제)")
    for which in ("user", "ref"):
        chk = (meta.get("alignFpsCheck_framesOverDuration") or {}).get(which)
        if chk is None or abs(chk - float(meta.get("alignFps") or 0)) > 0.5:
            fails.append(f"align fps 교차검증 실패 ({which}: {chk})")
    cands = data.get("candidates") or []
    if not cands:
        fails.append("후보 0건")
    for c in cands:
        row = c.get("row") or {}
        for k in ("holdUser", "holdRef", "pair", "uSec", "rSec"):
            if k not in row:
                fails.append(f"{c.get('id')} row.{k} 부재")
        st = c.get("stills") or {}
        for side in ("user", "ref"):
            sp = st.get(side)
            if not sp or not (_HERE / sp).exists():
                fails.append(f"{c.get('id')} still {side} 실물 부재")
        if "kpoRelation" not in c:
            fails.append(f"{c.get('id')} kpo 대조 부재")
    for k in ("kpo", "ufbFreeze"):
        if k not in (data.get("contrast") or {}):
            fails.append(f"contrast.{k} 대조 행 부재")
    vr = _HERE / "evidence" / "VISUAL-REVIEW.md"
    if not vr.exists():
        fails.append("VISUAL-REVIEW.md 부재 (frames-before-numbers 미이행)")
    else:
        txt = vr.read_text()
        for c in cands:
            if c["id"] not in txt:
                fails.append(f"VISUAL-REVIEW.md 에 {c['id']} 기록 없음")
    if fails:
        print("CHECK-CANDIDATES FAIL:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"CHECK-CANDIDATES PASS ({len(cands)} candidates, "
          "stills+visual-review 전건)")
    return 0


def main() -> int:
    apr = argparse.ArgumentParser()
    apr.add_argument("--fetch", action="store_true")
    apr.add_argument("--scan", action="store_true")
    apr.add_argument("--eye", action="store_true")
    apr.add_argument("--render", action="store_true")
    apr.add_argument("--check-candidates", action="store_true")
    apr.add_argument("--joint", default="left_knee")
    apr.add_argument("--cands", default="",
                     help="쉼표구분 후보 id (eye/render 대상)")
    args = apr.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    EV.mkdir(exist_ok=True)
    if args.fetch:
        fetch()
    if args.scan:
        fetch()
        scan(args.joint)
    cand_ids = [c for c in args.cands.split(",") if c]
    if args.eye:
        if not cand_ids:
            raise SystemExit("--eye 는 --cands 필요 (육안 압축 후보만)")
        eye(args.joint, cand_ids)
    if args.render:
        if not cand_ids:
            raise SystemExit("--render 는 --cands 필요 (눈 PASS 후보만)")
        render(args.joint, cand_ids)
    if args.check_candidates:
        return check_candidates()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
