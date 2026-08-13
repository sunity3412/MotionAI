#!/usr/bin/env python3
"""fresh pdshape 비교 영상에 발굴 채택 순간 freeze 주입 — 하네스 사본 확장
(quick-260814-0p2). 원본 스크립트/운영 코드 무수정 (backend/ diff 0).

belle 채택 순간 cand13b(user 12.8667s / ref 12.40s, 왼무릎 — wif
DISCOVERY-LEDGER "후보 1 채택")를 doc p34fresh1786628533 비교 영상의 정지
목록에 **추가**하고 로컬 재렌더한다. 표현 경로(belle locked) = "비교 영상
freezes 에 발굴 순간 추가 -> 재렌더 -> 카드 상속" (카드 단독 방출 금지).

지원 범위 실측(evidence/SUPPORT-SURFACE.md 선행 박제):
  · build_timeline 은 record-driven — 정지 추가 경로 부재 (pair-override 는
    rt 전용). 따라서 이 사본에서 build_timeline 을 monkeypatch 래핑해 원본
    호출 후 신규 1건 append (m0k/nh4 하네스 monkeypatch 선례).
  · 리그 H2 는 외부 삽입을 설계상 검출 — 신규 freeze 는 pairSrc 신설 라벨
    "discover" 로만 주입하고(align-peak/pole 사칭 금지 — T-0p2-02), 리그
    실행 시 _H2_UT_DISPLACING_SRC 에 그 1값만 사본 delta 로 추가. 기존
    freeze 전건은 **무수정 판정기 기준 PASS 를 별도 assert** (T-0p2-01).

제약: S3 GET 만(put 스텁 캡처) · Firestore 쓰기 0 · Gemini 실호출 0 (Pod
eye ledger + wif eye_ledger replay 스텁) · Pod 무접촉 · 채점 무접촉.

stages:
  --fetch           wif_fresh 캐시 확인/재수화 + 전 rid mp3 + Pod eye ledger
  --baseline        주입 off 렌더 2회 + 운영 리그 무수정 ALL PASS + 결정론
  --check-baseline  Task 1 게이트
  --inject          주입 on 렌더 2회 + 리그(무수정 1FAIL 국한 + 사본 delta
                    ALL PASS) + diff 국한 기계 증명(report/compose/mp4 3층)
  --cards           운영 헬퍼 _run_gated_card_inherit 호출 (눈 replay 스텁)
  --check-inject    Task 2 게이트
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
import subprocess
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

# 채택 순간 정본 (wif cand13b 카드 파일명 cand13b_u12.8667s_r12.4s_...)
INJECT_RID = "r04"
INJECT_JOINT = "left_knee"
INJECT_UT = 12.8667
INJECT_RT = 12.40
INJECT_SRC = "discover"  # 신설 라벨 — align-peak/pole 사칭 금지 (T-0p2-02)

SP = pathlib.Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "ae166167-1abf-4754-9fe8-336a719ef9e2/scratchpad"
) / "wif_fresh"
OUT = SP.parent / "0p2_out"
DATA = _REPO / ".planning/phases/35-server-rendered-comparison-video/data"
WIF_EV = _REPO / ".planning/quick/260813-wif-knee-discovery/evidence"
EV = _HERE / "evidence"

DOC = SP / "doc.json"
REFMOTION = SP / "refmotion.json"
ALIGN_JSON = SP / "align.json"
VIDEOS = {"user": SP / "user.mp4", "ref": SP / "ref.mp4"}
AUDIO_DIR = SP / "audio"
ALIGN_WORK = SP / "align_work"
RENDER_WORK = SP / "render"
POD_EYE_LEDGER = OUT / "pod_eye_ledger.json"

N_FADE = 5  # compare_render FADE_S 0.17s x 30fps = 5프레임 (복귀 페이드)

log = logging.getLogger("inject_freeze")


def _report_core(report: dict) -> dict:
    """결정론 대조용 — out 경로(run 태그 포함)만 제외한 report 본체."""
    return {k: v for k, v in report.items() if k != "out"}


def _md5_file(p: pathlib.Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _s3_client():
    import boto3

    session = boto3.Session(
        profile_name=os.environ.get("AWS_PROFILE", "sunity-motion"))
    return session.client("s3", region_name="ap-northeast-2")


# ── fetch ────────────────────────────────────────────────────────────────────

def fetch() -> None:
    """wif 캐시 재사용/재수화 + 전 rid mp3 + Pod eye ledger (전부 S3 GET 만)."""
    SP.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if not DOC.exists() or not REFMOTION.exists():
        # wif discover_knee.py fetch 패턴 그대로 (Firestore 읽기 전용)
        if not os.environ.get("FIREBASE_SA_PATH") and not os.environ.get(
                "FIREBASE_SA_JSON"):
            os.environ["FIREBASE_SA_PATH"] = str(_REPO / "firebase-sa.json")
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

    # 영상 정체성 게이트 — align 프레임 수 정확 일치 (wif fetch 검증분 재확인)
    align = json.loads(ALIGN_JSON.read_text())
    assert int(align["userFrames"]) == 272 and int(align["refFrames"]) == 237, (
        f"align 프레임 수 불일치: {align['userFrames']}/{align['refFrames']}"
        " != 272/237 — 캐시 영상 정체성 FAIL")

    # 전 rid mp3 (ufb verify_local --fetch 패턴 — coachAudio items 키 그대로)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    items = (res.get("coachAudio") or {}).get("items") or []
    for it in items:
        rid = str(it.get("recordId", "")).split(":")[0]
        key = it.get("key")
        if not rid or not key:
            continue
        p = AUDIO_DIR / f"{rid}.mp3"
        if not p.exists():
            s3 = s3 or _s3_client()
            s3.download_file(BUCKET, key, str(p))
            print(f"fetched mp3 {rid} <- {key}")
    have = sorted(p.stem for p in AUDIO_DIR.glob("*.mp3"))
    print(f"audio cache: {have}")
    assert f"{INJECT_RID}" in have, (
        f"{INJECT_RID}.mp3 부재 — locked 분기(캡션만·음성 무) 발동: "
        "SUPPORT-SURFACE/FINDINGS 에 명기 필요")

    # Pod 기계 눈 원장 (Task 2 replay 스텁 소스 — S3 GET)
    if not POD_EYE_LEDGER.exists():
        s3 = s3 or _s3_client()
        s3.download_file(
            BUCKET, f"results/{UID}/{AID}/eye/ledger.json",
            str(POD_EYE_LEDGER))
        print("fetched pod eye ledger")
    print("fetch OK")


# ── 주입 레이어 (사본 monkeypatch — 원본 build_timeline 무수정) ─────────────

def _install_injection(cr):
    """compare_render.build_timeline 래퍼 설치 → 원본 반환 (finally 복원용).

    원본 호출 후 신규 freeze 1건 append. 필드 생산 규칙은 전부 운영 재사용:
      dur  = mp3_duration_s + FREEZE_TAIL_S      (compare_render.py:1310)
      text = coach_audio_speech_text(r04 record) (새 문구 발명 0 — H3 조건)
      마크 = _align_markers + left_knee 이므로 _body_line_viz
             (compare_render.py:1256-1262 미러 — 새 문법 발명 0)
    render() 가 ut 순 정렬(:1423)하므로 삽입 위치는 자동.
    """
    orig = cr.build_timeline

    def patched(doc, audio_dir, moments=None, align=None, poles=None,
                text_overrides=None, pair_overrides=None):
        warp_b, freezes, excluded = orig(
            doc, audio_dir, moments, align, poles,
            text_overrides, pair_overrides)
        rec = next(
            r for r in doc["result"]["deductionBreakdown"]["records"]
            if str(r.get("recordId", "")).startswith(f"{INJECT_RID}:"))
        mp3 = pathlib.Path(audio_dir) / f"{INJECT_RID}.mp3"
        assert mp3.exists(), f"주입 freeze mp3 부재: {mp3}"
        ut, rt = float(INJECT_UT), float(INJECT_RT)
        markers = cr._align_markers(align, rec, ut)  # noqa: SLF001
        body_viz = cr._body_line_viz(align, ut, rt, poles or {})  # noqa: SLF001
        if body_viz is not None:
            markers = []  # compare_render.py:1261-1262 미러 (표시 소유권)
        freezes.append({
            "rid": INJECT_RID, "ut": ut, "rt": rt,
            "pair_src": INJECT_SRC,
            "dur": cr.mp3_duration_s(mp3) + cr.FREEZE_TAIL_S,
            "mp3": mp3, "joint": INJECT_JOINT, "markers": markers,
            "legs_viz": None, "viz_kind": None, "viz_side": None,
            "pole_viz": None, "body_viz": body_viz,
            "text": cr.coach_audio_speech_text(rec),
        })
        return warp_b, freezes, excluded

    cr.build_timeline = patched
    return orig


# ── 렌더 1회 + 관측 ──────────────────────────────────────────────────────────

def _render_once(tag: str, inject: bool) -> dict:
    from sunity_shared.analysis import compare_render as cr

    doc = json.loads(DOC.read_text())
    align = json.loads(ALIGN_JSON.read_text())
    out = OUT / f"{tag}.mp4"
    orig = _install_injection(cr) if inject else None
    try:
        report = cr.render(
            doc, VIDEOS["user"], VIDEOS["ref"], AUDIO_DIR, RENDER_WORK, out,
            align_json=align,
        )
    finally:
        if orig is not None:
            cr.build_timeline = orig
    compose = RENDER_WORK / f"compose{int(cr.FPS_OUT)}_{cr.PANEL_H}"
    frames_md5 = [
        _md5_file(p) for p in sorted(compose.glob("*.jpg"))
    ]
    return {
        "tag": tag, "out": str(out), "mp4Md5": _md5_file(out),
        "report": report, "framesMd5": frames_md5,
    }


def _verify(mp4: pathlib.Path, report: dict, rig_dir: pathlib.Path,
            delta_label: str | None = None) -> tuple[bool, list[str]]:
    """운영 compare_verify.verify — delta_label 지정 시에만 사본 면제 1값 추가."""
    from sunity_shared.analysis import compare_verify as cv

    doc = json.loads(DOC.read_text())
    align = json.loads(ALIGN_JSON.read_text())
    rig_dir.mkdir(parents=True, exist_ok=True)
    orig = cv._H2_UT_DISPLACING_SRC  # noqa: SLF001
    try:
        if delta_label is not None:
            # 사본 delta 1값 (T-0p2-01) — 판정 로직·타 항목 무접촉.
            cv._H2_UT_DISPLACING_SRC = orig + (delta_label,)  # noqa: SLF001
        return cv.verify(mp4, report, rig_dir, align=align, doc=doc)
    finally:
        cv._H2_UT_DISPLACING_SRC = orig  # noqa: SLF001


def _extract_frame(mp4: pathlib.Path, sec: float) -> np.ndarray:
    import imageio_ffmpeg
    from PIL import Image

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmp = OUT / "_frame.png"
    if tmp.exists():
        tmp.unlink()
    subprocess.run(
        [ff, "-y", "-loglevel", "error", "-ss", f"{sec:.4f}", "-i", str(mp4),
         "-frames:v", "1", str(tmp)], check=True)
    return np.asarray(Image.open(tmp).convert("RGB"), dtype=np.int16)


def _frame_compare(a: np.ndarray, b: np.ndarray) -> dict:
    if a.shape != b.shape:
        return {"identical": False, "shapeMismatch": True}
    d = np.abs(a - b)
    md5a = hashlib.md5(a.astype(np.uint8).tobytes()).hexdigest()
    md5b = hashlib.md5(b.astype(np.uint8).tobytes()).hexdigest()
    return {
        "identical": md5a == md5b,
        "maxDelta": int(d.max()),
        "meanDelta": round(float(d.mean()), 5),
        "pixelsOver8": int((d.max(axis=2) > 8).sum()),
    }


# ── baseline (Task 1) ────────────────────────────────────────────────────────

def baseline() -> None:
    r1 = _render_once("baseline_run1", inject=False)
    frames1 = r1.pop("framesMd5")
    r2 = _render_once("baseline_run2", inject=False)
    frames2 = r2.pop("framesMd5")
    det = r1["mp4Md5"] == r2["mp4Md5"]
    det_frames = frames1 == frames2
    same_report = _report_core(r1["report"]) == _report_core(r2["report"])

    ok, lines = _verify(
        pathlib.Path(r1["out"]), r1["report"], OUT / "rig_base")
    for ln in lines:
        print(ln)

    # 교차 확인 (informative) — doc renderedCompare 의 정지 outSec 과 대조
    doc_rc = (json.loads(DOC.read_text())["result"].get("renderedCompare")
              or {})
    cross = {
        "docFreezes": doc_rc.get("freezes"),
        "localFreezes": [
            {"rid": f["rid"], "outSec": f["voiceStartOutS"]}
            for f in r1["report"]["freezes"]
        ],
    }

    verdict = {
        "meta": {
            "uid": UID, "aid": AID, "motionId": MOTION_ID,
            "generated": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        },
        "freezes": r1["report"]["freezes"],
        "excludedFreezes": r1["report"]["excludedFreezes"],
        "rig": {"allPass": ok, "lines": lines,
                "verifier": "compare_verify.verify 무수정 (면제 delta 0)"},
        "determinism": {
            "mp4Md5Run1": r1["mp4Md5"], "mp4Md5Run2": r2["mp4Md5"],
            "mp4Same": det, "composeFramesSame": det_frames,
            "reportSame": same_report,
        },
        "crossCheckRenderedCompare": cross,
        "outFiles": [r1["out"], r2["out"]],
    }
    EV.mkdir(exist_ok=True)
    (EV / "baseline_verdict.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=1))
    (EV / "frames_md5_baseline.json").write_text(json.dumps(frames1))
    (OUT / "baseline_report.json").write_text(json.dumps(r1["report"]))
    print(f"baseline: freezes={len(r1['report']['freezes'])} rig={'PASS' if ok else 'FAIL'} "
          f"determinism mp4={'SAME' if det else 'DIFFER'}")


def check_baseline() -> int:
    fails: list[str] = []
    p = EV / "baseline_verdict.json"
    if not p.exists():
        print("FAIL: baseline_verdict.json 부재")
        return 1
    v = json.loads(p.read_text())
    if not v["rig"]["allPass"]:
        fails.append("리그 ALL PASS 아님")
    d = v["determinism"]
    if not (d["mp4Same"] and d["composeFramesSame"] and d["reportSame"]):
        fails.append(f"결정론 실패: {d}")
    fz = v.get("freezes") or []
    if len(fz) < 1:
        fails.append("freeze 기록 0건")
    for f in fz:
        for k in ("rid", "joint", "userSec", "refSec", "pairSrc", "text"):
            if k not in f:
                fails.append(f"freeze {f.get('rid')} 필드 {k} 부재")
    if any(f.get("pairSrc") == INJECT_SRC for f in fz):
        fails.append("베이스라인에 discover freeze 존재 (주입 off 위반)")
    if not (EV / "frames_md5_baseline.json").exists():
        fails.append("frames_md5_baseline.json 부재")
    if fails:
        print("CHECK-BASELINE FAIL:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"CHECK-BASELINE PASS (freezes {len(fz)}건, 리그 무수정 ALL PASS, "
          "md5 2회 동일)")
    return 0


# ── inject (Task 2 렌더 + 리그 + diff 국한) ─────────────────────────────────

def _out_sec_of(report: dict, t: float) -> float:
    """user 초 t 의 출력 초 — 그 report 의 freeze 편성으로 유도 (재생 프레임)."""
    shift = sum(
        f["freezeS"] for f in report["freezes"] if f["userSec"] <= t)
    return t + shift


def inject() -> None:
    base_report = json.loads((OUT / "baseline_report.json").read_text())
    base_frames = json.loads((EV / "frames_md5_baseline.json").read_text())

    r1 = _render_once("inject_run1", inject=True)
    frames1 = r1.pop("framesMd5")
    r2 = _render_once("inject_run2", inject=True)
    frames2 = r2.pop("framesMd5")
    det = r1["mp4Md5"] == r2["mp4Md5"]
    det_frames = frames1 == frames2
    same_report = _report_core(r1["report"]) == _report_core(r2["report"])
    report = r1["report"]
    mp4 = pathlib.Path(r1["out"])

    # (2a) 무수정 판정기 — 기존 freeze 전건 PASS + FAIL = discover H2 정확 1건
    ok_stock, lines_stock = _verify(mp4, report, OUT / "rig_inj_stock")
    stock_fails = [ln for ln in lines_stock if ln.strip().startswith("[FAIL]")]
    stock_confined = (
        len(stock_fails) == 1
        and "H2 순간" in stock_fails[0]
        and f"src={INJECT_SRC}" in stock_fails[0]
    )
    # (2b) 사본 delta 1값 — ALL PASS
    ok_delta, lines_delta = _verify(
        mp4, report, OUT / "rig_inj_delta", delta_label=INJECT_SRC)
    for ln in lines_delta:
        print(ln)

    # (3a) report 수준 diff 국한
    inj_new = [f for f in report["freezes"] if f["pairSrc"] == INJECT_SRC]
    inj_old = [f for f in report["freezes"] if f["pairSrc"] != INJECT_SRC]
    keys = ("rid", "joint", "userSec", "refSec", "pairSrc", "text",
            "freezeS", "markers", "legsViz", "poleViz", "bodyViz")
    old_fields_same = (
        len(inj_old) == len(base_report["freezes"])
        and all(
            {k: a.get(k) for k in keys} == {k: b.get(k) for k in keys}
            for a, b in zip(inj_old, base_report["freezes"])
        )
    )
    new_exact = (
        len(inj_new) == 1
        and inj_new[0]["rid"] == INJECT_RID
        and inj_new[0]["joint"] == INJECT_JOINT
        and abs(inj_new[0]["userSec"] - INJECT_UT) < 1e-9
        and abs(inj_new[0]["refSec"] - INJECT_RT) < 0.005
    )

    # (3b) 내용 수준 — compose 프레임 md5 사슬 (bit-exact 구조 증명)
    m = len(frames1) - len(base_frames)
    k = next(
        (i for i, (a, b) in enumerate(zip(base_frames, frames1)) if a != b),
        len(base_frames))
    prefix_same = base_frames[:k] == frames1[:k]
    suffix_same = frames1[k + m + N_FADE:] == base_frames[k + N_FADE:]
    fade_frames_changed = sum(
        1 for j in range(N_FADE)
        if k + j < len(base_frames)
        and base_frames[k + j] != frames1[k + m + j])
    dur_new = inj_new[0]["freezeS"] if inj_new else 0.0
    m_matches_dur = abs(m - dur_new * 30.0) <= 1.5
    compose_proof = {
        "insertIndex": k, "insertOutSec": round(k / 30.0, 3),
        "insertedFrames": m, "expectedFromFreezeS": round(dur_new * 30.0, 1),
        "prefixSame": prefix_same, "suffixSameAfterFade": suffix_same,
        "fadeFramesChanged": fade_frames_changed, "nFade": N_FADE,
        "note": ("의도 변경 = 삽입 블록 " f"{m}프레임 + 복귀 크로스페이드 "
                 f"{N_FADE}프레임(ref 패널 블렌드). 그 외 전 프레임 JPEG md5 "
                 "bit-동일. 삽입점 이후 출력 초는 신규 정지 길이만큼 이동 — "
                 "내용 동일성으로 증명 (무변경 주장 아님)."),
    }

    # (3b') mp4 수준 — 기존 정지 중앙 프레임 + 재생 표본 (양쪽 report 자체
    # 타임라인 매핑). H.264 재인코드 노이즈는 정직 기록 (hlv Δ3/255 선례).
    base_mp4 = pathlib.Path(json.loads(
        (EV / "baseline_verdict.json").read_text())["outFiles"][0])
    freeze_frame_checks = []
    for bf, jf in zip(base_report["freezes"], inj_old):
        mid_b = bf["voiceStartOutS"] + bf["freezeS"] / 2
        mid_i = jf["voiceStartOutS"] + jf["freezeS"] / 2
        cmpres = _frame_compare(
            _extract_frame(base_mp4, mid_b), _extract_frame(mp4, mid_i))
        freeze_frame_checks.append(
            {"rid": bf["rid"], "outSecBase": round(mid_b, 2),
             "outSecInjected": round(mid_i, 2), **cmpres})
    playback_checks = []
    for t in (3.0, 12.0, 15.5):
        cmpres = _frame_compare(
            _extract_frame(base_mp4, _out_sec_of(base_report, t) ),
            _extract_frame(mp4, _out_sec_of(report, t)))
        playback_checks.append({"userSec": t, **cmpres})
    content_ok = all(
        c["identical"] or (c.get("maxDelta", 99) <= 4 and c.get("pixelsOver8", 1) == 0)
        for c in freeze_frame_checks + playback_checks)

    verdict = {
        "meta": {
            "uid": UID, "aid": AID,
            "inject": {"rid": INJECT_RID, "joint": INJECT_JOINT,
                       "userSec": INJECT_UT, "refSec": INJECT_RT,
                       "pairSrc": INJECT_SRC},
            "generated": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        },
        "freezes": report["freezes"],
        "rigStock": {
            "verifier": "compare_verify.verify 무수정",
            "allPass": ok_stock,
            "failLines": stock_fails,
            "confinedToDiscoverH2": stock_confined,
            "note": "기존 freeze 전건 = 무수정 판정기 기준 PASS (T-0p2-01). "
                    "유일 FAIL = 신규 discover freeze 의 H2 — 게이트가 외부 "
                    "삽입을 설계대로 검출한 것.",
        },
        "rigDelta": {
            "verifier": "compare_verify.verify + _H2_UT_DISPLACING_SRC 사본 "
                        f"delta 1값('{INJECT_SRC}') — 판정 로직 무접촉",
            "allPass": ok_delta,
            "lines": lines_delta,
            "productionChange": "운영 반영 시 compare_verify "
                                "_H2_UT_DISPLACING_SRC 면제 튜플 확장 필요 "
                                "(SUPPORT-SURFACE §5)",
        },
        "diffConfined": {
            "reportLevel": {"oldFieldsSame": old_fields_same,
                            "newExactlyOne": new_exact},
            "composeLevel": compose_proof,
            "mp4Level": {"freezeMidFrames": freeze_frame_checks,
                         "playbackSamples": playback_checks,
                         "contentOk": content_ok},
        },
        "determinism": {
            "mp4Md5Run1": r1["mp4Md5"], "mp4Md5Run2": r2["mp4Md5"],
            "mp4Same": det, "composeFramesSame": det_frames,
            "reportSame": same_report,
        },
        "outFiles": [r1["out"], r2["out"]],
    }
    (EV / "inject_verdict.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=1))
    (EV / "frames_md5_injected.json").write_text(json.dumps(frames1))
    (OUT / "inject_report.json").write_text(json.dumps(report))
    print(f"inject: freezes={len(report['freezes'])} "
          f"rigStock confined={stock_confined} rigDelta={'PASS' if ok_delta else 'FAIL'} "
          f"reportDiff old={old_fields_same} new1={new_exact} "
          f"compose prefix={prefix_same} suffix={suffix_same} "
          f"mp4content={content_ok} determinism={'SAME' if det else 'DIFFER'}")


# ── cards (Task 2 (4) — 운영 헬퍼 상속, 눈 replay 스텁) ──────────────────────

class _S3Stub:
    """put_object 로컬 캡처 (S3 쓰기 0 — 업로드 없음). wif _S3Stub 패턴."""

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
        self.verdict_args: tuple | None = None

    def emit(self, record):  # noqa: D102
        try:
            msg = record.msg if isinstance(record.msg, str) else ""
            if msg.startswith("card_gates verdict"):
                self.verdict_args = record.args
            m = record.getMessage()
            if m.startswith(("card_gates", "display_anchor", "align_bake",
                             "fault_zoom")):
                self.lines.append(m)
        except Exception:  # noqa: BLE001
            pass


def _build_eye_replay():
    """replay 맵 — Pod eye ledger(r00/r03) + wif eye_ledger(cand13b r04).

    키 = (claim, expected_limb, 프레임 픽셀 좌표) — 운영 헬퍼가 machine_eye 에
    넘기는 인자 공간 그대로 (wif 로그 실측: cand13b xy=333,437 재현 확인).
    실호출 경로 없음 — 매핑 불가 시 fail-closed + 박제 (실호출 대체 금지).
    """
    from PIL import Image

    from sunity_shared.analysis import card_gates as cg

    align = json.loads(ALIGN_JSON.read_text())
    reps = {"user": cg.align_to_report(align, "user"),
            "ref": cg.align_to_report(align, "ref")}
    sizes = {}
    for side, d in (("user", RENDER_WORK / "u30_1080"),
                    ("ref", RENDER_WORK / "r30_1080")):
        first = sorted(d.glob("*.jpg"))[0]
        with Image.open(first) as im:
            sizes[side] = im.size  # (W, H)

    entries = []
    pod = json.loads(POD_EYE_LEDGER.read_text())
    for e in pod.get("entries", []):
        entries.append({**e, "src": "pod_eye_ledger(S3)"})
    wif = json.loads(
        (WIF_EV / "eye_ledger" / "01_cand13b_user_left_knee_bent.json"
         ).read_text())
    entries.append({**wif, "src": "wif eye_ledger cand13b"})

    replay = []
    for e in entries:
        side, idx, joint = e["side"], int(e["frameIdx"]), e["joint"]
        xy = cg.kp(reps[side], idx, joint, conf_min=0.0)
        if xy is None:
            continue
        W, H = sizes[side]
        replay.append({
            "claim": e["claim"], "limb": cg.joint_limb(joint),
            "px": (xy[0] * W, xy[1] * H),
            "side": side, "frameIdx": idx, "joint": joint,
            "result": {"observed": e["observed"], "limb": e["limb"],
                       "match": bool(e["match"]),
                       "confidence": e["confidence"],
                       "reason": e.get("reason", "")},
            "src": e["src"],
        })
    return replay


def cards() -> None:
    # Gemini 실호출 0 보증 2중: machine_eye 전면 교체 + 가짜 키 (네트워크 경로
    # 자체가 스텁 안에 없음 — 미스 시에도 실호출 불가).
    os.environ["GEMINI_API_KEY"] = "stub-0p2-replay-only"
    import app  # backend/functions/pipeline — 운영 모듈 그대로 (무수정)
    from PIL import Image
    from sunity_shared import firestore_admin as fs_admin
    from sunity_shared.analysis import card_gates as cg
    from sunity_shared.analysis import frame_extractor as fe_mod

    replay = _build_eye_replay()
    state = {"realCalls": 0, "replayHits": [], "misses": []}

    def _replay_eye(frame_rgb, joint_xy_px, claim, *, api_key,
                    expected_limb=None, crop_px=360,
                    model="gemini-3.5-flash", timeout_s=60.0):
        x, y = float(joint_xy_px[0]), float(joint_xy_px[1])
        hit = None
        for e in replay:
            if (e["claim"] == claim and e["limb"] == expected_limb
                    and abs(e["px"][0] - x) <= 2.0
                    and abs(e["px"][1] - y) <= 2.0):
                hit = e
                break
        if hit is None:
            # 실호출 대체 금지 (locked) — fail-closed + 박제.
            state["misses"].append(
                {"claim": claim, "limb": expected_limb,
                 "px": [round(x, 1), round(y, 1)]})
            return {"observed": "replay_miss", "limb": None, "match": False,
                    "confidence": 0.0,
                    "reason": "0p2 replay 스텁 매핑 불가 (실호출 금지)",
                    "crop": None}
        state["replayHits"].append(
            {"src": hit["src"], "side": hit["side"],
             "frameIdx": hit["frameIdx"], "joint": hit["joint"],
             "claim": claim, "match": hit["result"]["match"]})
        H, W = frame_rgb.shape[:2]
        half = int(crop_px) // 2
        x0, y0 = max(0, int(x) - half), max(0, int(y) - half)
        crop = Image.fromarray(
            frame_rgb[y0:min(H, int(y) + half), x0:min(W, int(x) + half)])
        return {**hit["result"], "crop": crop}

    res_doc = json.loads(DOC.read_text())["result"]
    ref_report = json.loads(REFMOTION.read_text())["referenceKeypointReport"]
    align = json.loads(ALIGN_JSON.read_text())
    report = json.loads((OUT / "inject_report.json").read_text())

    # 9fps 추출 memo (wif 선례 — 산출 byte 동일, 드라이버 프로세스 한정)
    _base_ext = fe_mod.FfmpegFrameExtractor

    class _CachingExtractor(_base_ext):
        _cache: dict = {}

        def extract(self, path):
            key = (str(path), self.target_fps, self.max_side)
            if key not in self._cache:
                self._cache[key] = super().extract(path)
            return self._cache[key]

    cards_root = EV / "cards"
    cards_root.mkdir(parents=True, exist_ok=True)
    out: dict = {"runs": [], "eyeRealCalls": 0}
    orig_eye = cg.machine_eye
    orig_s3, orig_signed = app._s3, app._signed_get  # noqa: SLF001
    orig_update = fs_admin.update_analysis_fault_zoom
    fe_mod.FfmpegFrameExtractor = _CachingExtractor
    cg.machine_eye = _replay_eye
    try:
        md5s = []
        for run_i in (1, 2):
            tmp = cards_root / f"_run{run_i}"
            if tmp.exists():
                shutil.rmtree(tmp)
            stub = _S3Stub(tmp, OUT / "eye_capture")
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
                    uid=UID, analysis_id=f"{AID}-0p2-inject",
                    bucket=BUCKET,
                )
            finally:
                logging.getLogger().removeHandler(cap)
            pngs = sorted(tmp.glob("*.png")) if tmp.exists() else []
            md5s.append({p.name: _md5_file(p) for p in pngs})
            run_out = {
                "run": run_i,
                "verdictArgs": None,
                "logs": cap.lines,
                "attached": [
                    {k: v for k, v in c.items()
                     if k not in ("imageUrl", "referenceImageUrl")}
                    for c in (attached.get("comparisons") or [])
                ],
                "s3Keys": stub.keys,
            }
            if cap.verdict_args:
                a = cap.verdict_args
                run_out["verdictArgs"] = {
                    "analysisId": a[0], "total": a[1],
                    "survivors": list(a[2]), "dropped": list(a[3]),
                    "eyeCalls": a[4],
                }
            out["runs"].append(run_out)
            if run_i == 1:
                for p in pngs:
                    shutil.copyfile(p, cards_root / p.name)
            shutil.rmtree(tmp, ignore_errors=True)
        out["cardMd5Run1"] = md5s[0]
        out["cardMd5Run2"] = md5s[1]
        out["deterministic"] = md5s[0] == md5s[1]
    finally:
        app._s3, app._signed_get = orig_s3, orig_signed
        fs_admin.update_analysis_fault_zoom = orig_update
        app.firestore_admin.update_analysis_fault_zoom = orig_update
        cg.machine_eye = orig_eye
        fe_mod.FfmpegFrameExtractor = _base_ext

    out["eyeRealCalls"] = state["realCalls"]  # 스텁 구조상 항상 0
    out["eyeReplayHits"] = state["replayHits"]
    out["eyeReplayMisses"] = state["misses"]

    # inject_verdict.json 에 cards 절 병합
    vp = EV / "inject_verdict.json"
    verdict = json.loads(vp.read_text())
    verdict["cards"] = out
    vp.write_text(json.dumps(verdict, ensure_ascii=False, indent=1))
    v1 = out["runs"][0].get("verdictArgs") or {}
    print(f"cards: survivors={v1.get('survivors')} "
          f"dropped={v1.get('dropped')} "
          f"replayHits={len(state['replayHits'])} misses={len(state['misses'])} "
          f"determinism={'SAME' if out['deterministic'] else 'DIFFER'}")


def check_inject() -> int:
    fails: list[str] = []
    p = EV / "inject_verdict.json"
    if not p.exists():
        print("FAIL: inject_verdict.json 부재")
        return 1
    v = json.loads(p.read_text())
    if not v["rigDelta"]["allPass"]:
        fails.append("리그(사본 delta) ALL PASS 아님")
    if not v["rigStock"]["confinedToDiscoverH2"]:
        fails.append("무수정 판정기 FAIL 이 discover H2 1건 국한 아님")
    d = v["determinism"]
    if not (d["mp4Same"] and d["composeFramesSame"] and d["reportSame"]):
        fails.append(f"결정론 실패: {d}")
    dc = v["diffConfined"]
    if not dc["reportLevel"]["oldFieldsSame"]:
        fails.append("기존 정지 필드 동일성 실패")
    if not dc["reportLevel"]["newExactlyOne"]:
        fails.append("신규 정지 정확 1건 실패")
    cl = dc["composeLevel"]
    if not (cl["prefixSame"] and cl["suffixSameAfterFade"]):
        fails.append("compose 프레임 diff 국한 실패")
    if not dc["mp4Level"]["contentOk"]:
        fails.append("mp4 프레임 내용 동일성 실패")
    cards_v = v.get("cards") or {}
    va = (cards_v.get("runs") or [{}])[0].get("verdictArgs") or {}
    surv = va.get("survivors") or []
    if not any(
            s.startswith(f"{INJECT_RID}:inherit@u12.867/r12.40")
            for s in surv):
        fails.append(f"카드 상속 실패: survivors={surv}")
    knee_cards = [
        a for r in cards_v.get("runs", [])[:1]
        for a in r.get("attached", [])
        if a.get("criterion") == f"angle_vs_reference__{INJECT_JOINT}"
    ]
    if not knee_cards:
        fails.append("왼무릎 상속 카드 부착 0건")
    else:
        uvs = float(knee_cards[0].get("userVideoSec") or 0.0)
        if round(uvs, 1) != 12.9:
            fails.append(f"카드 초 라벨 실효 fps 환산 아님: {uvs}")
    if cards_v.get("eyeRealCalls", 99) != 0:
        fails.append("기계 눈 실호출 발생 (0 이어야 함)")
    if cards_v.get("eyeReplayMisses"):
        fails.append(f"replay 매핑 불가 지점: {cards_v['eyeReplayMisses']}")
    if not (EV / "cards").exists() or not list((EV / "cards").glob("*.png")):
        fails.append("evidence/cards/ PNG 부재")
    if fails:
        print("CHECK-INJECT FAIL:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("CHECK-INJECT PASS (리그 delta ALL PASS + 무수정 1FAIL 국한 + "
          "결정론 + diff 국한 3층 + 카드 상속 u12.8667/r12.40 + 눈 실호출 0)")
    return 0


def main() -> int:
    apr = argparse.ArgumentParser()
    apr.add_argument("--fetch", action="store_true")
    apr.add_argument("--baseline", action="store_true")
    apr.add_argument("--check-baseline", action="store_true")
    apr.add_argument("--inject", action="store_true")
    apr.add_argument("--cards", action="store_true")
    apr.add_argument("--check-inject", action="store_true")
    args = apr.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    EV.mkdir(exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.fetch:
        fetch()
    if args.baseline:
        fetch()
        baseline()
    if args.check_baseline:
        return check_baseline()
    if args.inject:
        fetch()
        inject()
    if args.cards:
        cards()
    if args.check_inject:
        return check_inject()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
