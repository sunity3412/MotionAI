#!/usr/bin/env python3
"""발굴 채택 freeze 배선 재현 + 프로덕션 반영 드라이버 (quick-260814-di7).

chd inject_freeze.py 의 fetch / _render_once / 사슬 대조 패턴을 미러하되
**주입·판정 monkeypatch 전면 제거** — compare_render.build_timeline /
compare_verify 원본을 그대로 호출한다 (이것이 승격의 정의: 사본 delta 였던
discover freeze 가 doc 영속화 + 운영 코드 정식 경로로 성립했는가).

stages:
  --fetch        wif_fresh 캐시 복사 재사용 (구 세션 scratchpad 생존 실측) +
                 영상 정체성 게이트 + discover mp3 를 canonical basename 으로
                 audio_dir 조인 + DISCOVER_TEXT 기계 대조 (chd verdict ==)
  --baseline     discovery 없는 doc 렌더 1회 — compose 사슬 == chd
                 frames_md5_baseline.json + 무수정 verify ALL PASS
  --inject       discovery payload 조립(_validate_discovery 사전 통과) →
                 doc 사본 렌더 1회 — [discover] 로그 / 사슬 == chd injected /
                 report freeze 6건 == chd verdict / 무수정 verify ALL PASS /
                 음성 게이트(+0.5s 비틀기 → H2 discover FAIL)
  --check-wire   위 전부 evidence/wire_verdict.json 기계 게이트 (exit code)
  --apply        프로덕션 반영 (belle 승인 완료 — Task 3): 승인본 mp4
                 byte-보존 업로드(md5 사전 STOP 게이트) + discover mp3
                 canonical 키 업로드 + doc discovery/renderedCompare 갱신 —
                 전 쓰기 로그 evidence/production_log.json 박제
  --live         반영 검증: doc 재fetch == 방금 쓴 payload → live doc 렌더 —
                 discover mp3 는 S3 방금 쓴 키에서 GET (키 왕복 증명) →
                 사슬 == chd injected + 무수정 verify ALL PASS + [discover]
                 로그 → evidence/live_verdict.json
  --check-apply  production_log + live_verdict 기계 게이트 (exit code)

제약 (Task 2): S3/Firestore 쓰기 0 (읽기 전용 — 캐시 재사용이라 네트워크 0),
Gemini/Polly 호출 0, 카드 경로 재실행 불요 (chd 가 카드 3장 md5 == 0p2 로
캡션 비종속을 기계 증명 — 재검 대상 아님). 렌더 결정론 규율 = chd
_render_once 형식 미러. Task 3 쓰기 = S3 2건 + doc 2필드 정확 (AWS_PROFILE
sunity-motion), LLM 추론 호출 0 (Gemini 0 / Polly 0 — 렌더·업로드·doc 쓰기만).
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import hashlib
import io
import json
import logging
import os
import pathlib
import shutil
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "backend" / "shared" / "python"))

# ── 좌표 (PLAN.md — locked, chd/wif 정본) ───────────────────────────────────
UID = "fvcNXzEqKjgqVxRPVSj1iwFnIpn2"
AID = "p34fresh1786628533"
MOTION_ID = "ref-pdshape"
BUCKET = "sunity-motion-pilot-videos"

INJECT_RID = "r04"
INJECT_JOINT = "left_knee"
INJECT_UT = 12.8667
INJECT_RT = 12.40

# chd inject_freeze.py DISCOVER_TEXT 원문 문자 단위 그대로 (전사 drift 는
# fetch() 가 chd evidence/inject_verdict.json meta.inject.text 와 == 대조).
DISCOVER_TEXT = (
    "기준 자세는 다리를 곧게 편 채 회전하는 순간인데, 왼쪽 무릎이 접혀 "
    "있어요. 무릎을 접은 채 돌지 말고, 다리를 끝까지 편 상태로 회전한 뒤에 "
    "걸어보세요."
)

# chd freeze 정본 (PLAN — voiceStartOutS): 반영 freezes 값 게이트의 근거.
CHD_EXPECTED_OUT = [
    ("r00", 5.33), ("r01", 15.67), ("r04", 29.93),
    ("r04", 42.07),  # discover
    ("r02", 54.17), ("r03", 69.0),
]

# 세션 경로 — 구 세션 scratchpad (planner 실측 08-14 생존) → 현 세션 복사.
OLD_SP = pathlib.Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "ae166167-1abf-4754-9fe8-336a719ef9e2/scratchpad") / "wif_fresh"
SP = pathlib.Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "2a78a76a-92ce-42f8-b5d0-18c558c3d196/scratchpad") / "di7_fresh"
OUT = SP.parent / "di7_out"
EV = _HERE / "evidence"

CHD_EV = _REPO / ".planning/quick/260814-chd-freeze-belle-ok-0p2/evidence"
CHD_MP3 = CHD_EV / "discover_left_knee.mp3"

DOC = SP / "doc.json"
ALIGN_JSON = SP / "align.json"
VIDEOS = {"user": SP / "user.mp4", "ref": SP / "ref.mp4"}
AUDIO_DIR = SP / "audio"
AUDIO_LIVE = SP / "audio_live"
RENDER_WORK = SP / "render"

# 승인본 mp4 (belle 승인은 이 바이트에 붙어 있다 — 불일치/전멸 = STOP).
APPROVED_MP4_MD5 = "77cdcd436472438f3580cbb8d48683f3"
APPROVED_MP4_CANDIDATES = (
    pathlib.Path("/Users/Shared/sunity-freeze-inject-260814/"
                 "재렌더영상_신규정지포함.mp4"),
    OLD_SP.parent / "chd_out" / "inject_run1.mp4",  # 구 세션 scratchpad (휘발)
)

log = logging.getLogger("wire_discover")


def _md5_file(p: pathlib.Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def discovery_items() -> list[dict]:
    """doc 반영 payload — Task 2 렌더 재현과 Task 3 update_analysis_discovery
    가 이 함수 하나를 공유한다 (단일 소스, 드라이버 상수 1곳)."""
    from sunity_shared import s3keys

    return [{
        "rid": INJECT_RID, "joint": INJECT_JOINT,
        "userSec": INJECT_UT, "refSec": INJECT_RT,
        "pairSrc": "discover", "text": DISCOVER_TEXT,
        "mp3Key": s3keys.build_discover_audio_key(
            UID, AID, INJECT_RID, INJECT_JOINT),
        "adoptedAt": "2026-08-14",
    }]


def _merge_verdict(path: pathlib.Path, section: str, payload: dict) -> None:
    v = json.loads(path.read_text()) if path.exists() else {}
    v[section] = payload
    v.setdefault("meta", {"uid": UID, "aid": AID, "motionId": MOTION_ID})
    v["meta"]["updated"] = _now()
    path.write_text(json.dumps(v, ensure_ascii=False, indent=1))


# ── fetch ────────────────────────────────────────────────────────────────────

def fetch() -> None:
    """wif_fresh 캐시 복사 재사용 + 정체성 게이트 + discover mp3 canonical 조인."""
    SP.parent.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if not DOC.exists():
        assert OLD_SP.exists(), (
            f"wif_fresh 캐시 부재: {OLD_SP} — chd fetch() 패턴 재수화 필요 "
            "(이번 실행 환경에선 캐시 생존이 전제)")
        print(f"copy wif_fresh -> {SP} (render 캐시 포함 — chd 렌더 조건 미러)")
        shutil.copytree(OLD_SP, SP)

    # 영상 정체성 게이트 — align 프레임 수 정확 일치 (wif/chd 검증분 재확인).
    align = json.loads(ALIGN_JSON.read_text())
    assert int(align["userFrames"]) == 272 and int(align["refFrames"]) == 237, (
        f"align 프레임 수 불일치: {align['userFrames']}/{align['refFrames']}"
        " != 272/237 — 캐시 영상 정체성 FAIL")

    # DISCOVER_TEXT 기계 대조 — chd 승인본 text 와 문자 단위 == (전사 drift 차단).
    chd_text = json.loads(
        (CHD_EV / "inject_verdict.json").read_text())["meta"]["inject"]["text"]
    assert DISCOVER_TEXT == chd_text, "DISCOVER_TEXT != chd 승인본 text — 전사 drift"

    # discover mp3 — canonical 키 basename 으로 audio_dir 조인 (D-di7-02 실사용:
    # s3keys 함수 import = 단일 출처 확인. repo 고정 chd mp3, 재합성 0/Polly 0).
    assert CHD_MP3.exists() and CHD_MP3.stat().st_size == 64700, (
        f"chd discover mp3 부재/크기 상이: {CHD_MP3}")
    basename = discovery_items()[0]["mp3Key"].rsplit("/", 1)[-1]
    dst = AUDIO_DIR / basename
    if not dst.exists() or _md5_file(dst) != _md5_file(CHD_MP3):
        shutil.copyfile(CHD_MP3, dst)
    print(f"fetch OK — align 272/237, text ==, mp3 {basename} "
          f"md5={_md5_file(dst)}")


# ── 렌더 1회 + 관측 (chd _render_once 미러 — monkeypatch 0) ─────────────────

def _render_once(tag: str, doc: dict) -> dict:
    from sunity_shared.analysis import compare_render as cr

    align = json.loads(ALIGN_JSON.read_text())
    out = OUT / f"{tag}.mp4"
    buf = io.StringIO()

    class _Tee(io.TextIOBase):
        def write(self, s):  # noqa: D102
            buf.write(s)
            sys.__stdout__.write(s)
            return len(s)

    with contextlib.redirect_stdout(_Tee()):
        report = cr.render(
            doc, VIDEOS["user"], VIDEOS["ref"], AUDIO_DIR, RENDER_WORK, out,
            align_json=align,
        )
    compose = RENDER_WORK / f"compose{int(cr.FPS_OUT)}_{cr.PANEL_H}"
    frames_md5 = [_md5_file(p) for p in sorted(compose.glob("*.jpg"))]
    return {
        "tag": tag, "out": str(out), "mp4Md5": _md5_file(out),
        "report": report, "framesMd5": frames_md5, "stdout": buf.getvalue(),
    }


def _verify_stock(mp4: pathlib.Path, report: dict, doc: dict,
                  rig_dir: pathlib.Path) -> tuple[bool, list[str]]:
    """운영 compare_verify.verify **무수정** — 면제 delta 0 (승격의 정의)."""
    from sunity_shared.analysis import compare_verify as cv

    align = json.loads(ALIGN_JSON.read_text())
    rig_dir.mkdir(parents=True, exist_ok=True)
    return cv.verify(mp4, report, rig_dir, align=align, doc=doc)


# ── baseline ─────────────────────────────────────────────────────────────────

def baseline() -> None:
    doc = json.loads(DOC.read_text())
    assert "discovery" not in doc["result"], (
        "캐시 doc 에 discovery 존재 — 베이스라인 전제(부재) 위반")
    r = _render_once("wire_baseline", doc)
    chd_frames = json.loads((CHD_EV / "frames_md5_baseline.json").read_text())
    chain_same = r["framesMd5"] == chd_frames

    ok, lines = _verify_stock(
        pathlib.Path(r["out"]), r["report"], doc, OUT / "rig_wire_base")
    for ln in lines:
        print(ln)

    _merge_verdict(EV / "wire_verdict.json", "baseline", {
        "mp4Md5": r["mp4Md5"],
        "composeFrames": len(r["framesMd5"]),
        "baselineChainSame": chain_same,
        "chainRef": "chd frames_md5_baseline.json (repo 고정)",
        "rigStockAllPass": ok,
        "rigLines": lines,
        "discoverFreezeCount": sum(
            1 for f in r["report"]["freezes"] if f["pairSrc"] == "discover"),
        "outFile": r["out"],
    })
    (OUT / "wire_baseline_report.json").write_text(json.dumps(r["report"]))
    print(f"baseline: chainSame={chain_same} rig={'PASS' if ok else 'FAIL'} "
          f"freezes={len(r['report']['freezes'])}")


# ── inject ───────────────────────────────────────────────────────────────────

def inject() -> None:
    from sunity_shared import firestore_admin as fa

    items = discovery_items()
    fa._validate_discovery({"items": items})  # noqa: SLF001 — 반영 payload 사전 통과
    doc = json.loads(DOC.read_text())
    doc["result"]["discovery"] = {"items": items}

    r = _render_once("wire_inject", doc)
    report = r["report"]
    mp4 = pathlib.Path(r["out"])

    # (배선 로그) 운영 코드가 실제 호출됐다는 실행 로그 실물.
    discover_lines = [
        ln for ln in r["stdout"].splitlines() if ln.startswith("[discover] rid=")]
    assert discover_lines, "[discover] 로그 부재 — 주입 레이어 미호출 의심"

    # (a) compose 사슬 == chd 승인본
    chd_frames = json.loads((CHD_EV / "frames_md5_injected.json").read_text())
    chain_same = r["framesMd5"] == chd_frames

    # (b) report freeze 6건 == chd inject_verdict.json freezes
    chd_freezes = json.loads(
        (CHD_EV / "inject_verdict.json").read_text())["freezes"]
    keys_exact = ("rid", "joint", "pairSrc", "text")
    keys_close = ("userSec", "refSec", "freezeS", "voiceStartOutS")
    freezes_match = len(report["freezes"]) == len(chd_freezes) == 6 and all(
        all(a.get(k) == b.get(k) for k in keys_exact)
        and all(abs(float(a.get(k)) - float(b.get(k))) <= 0.01
                for k in keys_close)
        for a, b in zip(report["freezes"], chd_freezes)
    )

    # (c) 무수정 verify ALL PASS — 면제 delta 0
    ok, lines = _verify_stock(mp4, report, doc, OUT / "rig_wire_inject")
    for ln in lines:
        print(ln)

    # (d) 음성 게이트 — discovery 순간 +0.5s 비틀기 → H2 discover FAIL 정확 발생
    # (fail-closed 실증 — verify 는 mp4+report 입력이라 재렌더 불필요).
    doc_pert = json.loads(DOC.read_text())
    pert_items = [dict(it) for it in items]
    pert_items[0]["userSec"] = float(pert_items[0]["userSec"]) + 0.5
    doc_pert["result"]["discovery"] = {"items": pert_items}
    ok_p, lines_p = _verify_stock(mp4, report, doc_pert, OUT / "rig_wire_pert")
    pert_fails = [ln for ln in lines_p if ln.strip().startswith("[FAIL]")]
    h2_fail = [ln for ln in pert_fails
               if f"H2 순간 {INJECT_RID}[discover]" in ln]
    perturb_h2_fail = (not ok_p) and len(h2_fail) == 1

    _merge_verdict(EV / "wire_verdict.json", "inject", {
        "discoveryPayload": items,
        "validatorPreflight": "firestore_admin._validate_discovery PASS",
        "mp4Md5": r["mp4Md5"],
        "composeFrames": len(r["framesMd5"]),
        "injectedChainSame": chain_same,
        "chainRef": "chd frames_md5_injected.json (repo 고정)",
        "reportFreezesMatch": freezes_match,
        "reportFreezes": report["freezes"],
        "rigStockAllPass": ok,
        "rigStockNote": "compare_verify.verify 무수정 — 면제 monkeypatch 0 "
                        "(chd 사본 delta 2축이 더 이상 불필요함의 기계 증명)",
        "rigLines": lines,
        "discoverLogSeen": bool(discover_lines),
        "discoverLogLines": discover_lines,
        "perturbH2Fail": perturb_h2_fail,
        "perturbFailLines": pert_fails,
        "outFile": r["out"],
    })
    (OUT / "wire_inject_report.json").write_text(json.dumps(report))
    print(f"inject: chainSame={chain_same} freezesMatch={freezes_match} "
          f"rigStock={'PASS' if ok else 'FAIL'} "
          f"discoverLog={len(discover_lines)} perturbH2Fail={perturb_h2_fail}")


# ── check-wire ───────────────────────────────────────────────────────────────

def check_wire() -> int:
    fails: list[str] = []
    p = EV / "wire_verdict.json"
    if not p.exists():
        print("CHECK-WIRE FAIL: wire_verdict.json 부재")
        return 1
    v = json.loads(p.read_text())
    b = v.get("baseline") or {}
    if not b.get("baselineChainSame"):
        fails.append("베이스라인 compose 사슬 != chd frames_md5_baseline")
    if not b.get("rigStockAllPass"):
        fails.append("베이스라인 무수정 verify ALL PASS 아님")
    if b.get("discoverFreezeCount") != 0:
        fails.append("베이스라인에 discover freeze 존재 (주입 off 위반)")
    i = v.get("inject") or {}
    if not i.get("injectedChainSame"):
        fails.append("주입 compose 사슬 != chd frames_md5_injected")
    if not i.get("reportFreezesMatch"):
        fails.append("report freeze 6건 != chd 승인본")
    if not i.get("rigStockAllPass"):
        fails.append("주입 무수정 verify ALL PASS 아님 (면제 delta 0 요구)")
    if not i.get("discoverLogSeen"):
        fails.append("[discover] 실행 로그 부재")
    if not i.get("perturbH2Fail"):
        fails.append("음성 게이트(+0.5s 비틀기 H2 discover FAIL) 미성립")
    if fails:
        print("CHECK-WIRE FAIL:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("CHECK-WIRE PASS (배선 경로 == chd 승인본: 베이스라인/주입 사슬 + "
          "freeze 6건 + 무수정 verify ALL PASS + [discover] 로그 + 음성 게이트)")
    return 0


# ── apply (Task 3 — 프로덕션 반영, belle 승인 완료. 전 쓰기 로그 박제) ───────

def _s3_client():
    import boto3

    return boto3.Session(
        profile_name=os.environ.get("AWS_PROFILE", "sunity-motion")
    ).client("s3", region_name="ap-northeast-2")


def _fa():
    if not os.environ.get("FIREBASE_SA_PATH") and not os.environ.get(
            "FIREBASE_SA_JSON"):
        os.environ["FIREBASE_SA_PATH"] = str(_REPO / "firebase-sa.json")
    from sunity_shared import firestore_admin as fa

    return fa


def _live_doc(fa) -> dict:
    doc = (
        fa._db().collection("users").document(UID)  # noqa: SLF001
        .collection("analyses").document(AID).get().to_dict()
    )
    assert doc and isinstance(doc.get("result"), dict), (
        f"live doc {AID} 조회 실패 또는 result 부재")
    return doc


def _freezes_payload() -> list[dict]:
    """반영 freezes — Task 2 재현 report 의 [{rid, outSec=voiceStartOutS}].

    discover 항목 rid = 'r04:discover' (D-di7-05 — 앱 freezeNumber fail-open
    무번호 틱 + React key 중복 회피). 값은 chd 정본과 ±0.01 일치 assert.
    """
    report = json.loads((OUT / "wire_inject_report.json").read_text())
    payload = []
    for fz in report["freezes"]:
        rid = fz["rid"]
        if fz.get("pairSrc") == "discover":
            rid = f"{rid}:discover"
        payload.append({"rid": rid, "outSec": fz["voiceStartOutS"]})
    assert len(payload) == len(CHD_EXPECTED_OUT) == 6, (
        f"freezes 6건 아님: {payload}")
    for (exp_rid, exp_out), got in zip(CHD_EXPECTED_OUT, payload):
        assert got["rid"].split(":")[0] == exp_rid, (
            f"freezes rid 순서 상이: {got} != {exp_rid}")
        assert abs(float(got["outSec"]) - exp_out) <= 0.01, (
            f"freezes outSec != chd 정본: {got} vs {exp_out}")
    return payload


def apply() -> None:
    from sunity_shared import s3keys

    writes: list[dict] = []

    # (1) 승인본 mp4 소스 확보 — md5 사전 STOP 게이트 (T-di7-03).
    src_mp4 = None
    probed = []
    for cand in APPROVED_MP4_CANDIDATES:
        if not cand.exists():
            probed.append({"path": str(cand), "exists": False})
            continue
        md5 = _md5_file(cand)
        probed.append({"path": str(cand), "exists": True, "md5": md5})
        if md5 == APPROVED_MP4_MD5:
            src_mp4 = cand
            break
    if src_mp4 is None:
        (EV / "production_log.json").write_text(json.dumps({
            "status": "STOP",
            "reason": f"승인본 mp4 md5 {APPROVED_MP4_MD5} 소스 전멸/불일치 — "
                      "업로드 없이 중단 (belle 승인은 이 바이트에 붙어 있다)",
            "probed": probed, "at": _now(),
        }, ensure_ascii=False, indent=1))
        raise SystemExit("STOP: 승인본 mp4 소스 확보 실패 — production_log 참조")

    fa = _fa()
    s3 = _s3_client()

    # (2) doc 현행 renderedCompare.key == canonical 키 exact assert → 같은 키
    #     덮어쓰기 = byte-보존 반영 (키 drift 시 STOP).
    doc_pre = _live_doc(fa)
    rc_pre = doc_pre["result"].get("renderedCompare") or {}
    canonical_key = s3keys.build_rendered_compare_key(UID, AID)
    assert rc_pre.get("key") == canonical_key, (
        f"STOP: doc renderedCompare.key {rc_pre.get('key')!r} != canonical "
        f"{canonical_key!r}")
    with open(src_mp4, "rb") as fh:
        s3.put_object(Bucket=BUCKET, Key=canonical_key, Body=fh,
                      ContentType="video/mp4")
    got = s3.get_object(Bucket=BUCKET, Key=canonical_key)["Body"].read()
    got_md5 = hashlib.md5(got).hexdigest()
    assert got_md5 == APPROVED_MP4_MD5, (
        f"업로드 후 S3 md5 재확인 실패: {got_md5}")
    writes.append({
        "op": "s3.put_object", "key": canonical_key,
        "contentType": "video/mp4", "bytes": src_mp4.stat().st_size,
        "sourcePath": str(src_mp4), "sourceMd5": APPROVED_MP4_MD5,
        "s3RoundtripMd5": got_md5, "at": _now(),
        "note": "belle 승인본 byte-보존 — doc 현행 key == canonical exact "
                "assert 후 같은 키 덮어쓰기",
    })
    print(f"apply(1,2): mp4 -> s3://{BUCKET}/{canonical_key} md5={got_md5}")

    # (3) discover mp3 — canonical 키 업로드 + 재확인.
    item = discovery_items()[0]
    mp3_md5 = _md5_file(CHD_MP3)
    with open(CHD_MP3, "rb") as fh:
        s3.put_object(Bucket=BUCKET, Key=item["mp3Key"], Body=fh,
                      ContentType="audio/mpeg")
    got = s3.get_object(Bucket=BUCKET, Key=item["mp3Key"])["Body"].read()
    got_md5 = hashlib.md5(got).hexdigest()
    assert got_md5 == mp3_md5, f"mp3 S3 재확인 실패: {got_md5}"
    writes.append({
        "op": "s3.put_object", "key": item["mp3Key"],
        "contentType": "audio/mpeg", "bytes": CHD_MP3.stat().st_size,
        "sourcePath": str(CHD_MP3), "sourceMd5": mp3_md5,
        "s3RoundtripMd5": got_md5, "at": _now(),
        "note": "chd 승인 discover mp3 (repo 고정, Polly 재합성 0) — "
                "s3keys.build_discover_audio_key canonical 키",
    })
    print(f"apply(3): mp3 -> s3://{BUCKET}/{item['mp3Key']} md5={got_md5}")

    # (4) doc discovery 기입 — Task 2 와 단일 소스 payload.
    items = discovery_items()
    fa.update_analysis_discovery(UID, AID, items)
    writes.append({
        "op": "firestore.update_analysis_discovery",
        "args": {"uid": UID, "analysisId": AID, "items": items},
        "fieldPath": "result.discovery", "at": _now(),
    })
    print("apply(4): doc result.discovery 기입")

    # (5) renderedCompare 갱신 — freezes 6건 (discover rid 'r04:discover').
    freezes = _freezes_payload()
    fa.update_analysis_rendered_compare(
        UID, AID, canonical_key, status="done", freezes=freezes)
    writes.append({
        "op": "firestore.update_analysis_rendered_compare",
        "args": {"uid": UID, "analysisId": AID, "key": canonical_key,
                 "status": "done", "freezes": freezes},
        "fieldPath": "result.renderedCompare",
        "preFreezes": rc_pre.get("freezes"), "at": _now(),
    })
    print(f"apply(5): doc result.renderedCompare freezes={freezes}")

    (EV / "production_log.json").write_text(json.dumps({
        "status": "APPLIED",
        "uid": UID, "aid": AID, "bucket": BUCKET,
        "awsProfile": os.environ.get("AWS_PROFILE", "sunity-motion"),
        "writes": writes,
        "llm": {"geminiCalls": 0, "pollyCalls": 0,
                "note": "렌더·업로드·doc 쓰기만 — LLM 추론 호출 0"},
        "at": _now(),
    }, ensure_ascii=False, indent=1))
    print("apply: production_log.json 박제 완료 (S3 2건 + doc 2필드)")


# ── live (반영 검증 — 영속화 필드가 운영 경로를 구동한다는 최종 증명) ────────

def live() -> None:
    global AUDIO_DIR

    fa = _fa()
    doc_live = _live_doc(fa)
    res = doc_live["result"]

    # (a) 재fetch doc == 방금 쓴 payload (로컬 캐시 미사용).
    items = discovery_items()
    disc_match = res.get("discovery") == {"items": items}
    from sunity_shared import s3keys

    canonical_key = s3keys.build_rendered_compare_key(UID, AID)
    freezes = _freezes_payload()
    rc_match = res.get("renderedCompare") == {
        "status": "done", "key": canonical_key, "freezes": freezes}
    assert disc_match, (
        f"live doc discovery != 반영 payload: {res.get('discovery')}")
    assert rc_match, (
        f"live doc renderedCompare != 반영 payload: {res.get('renderedCompare')}")

    # (b) discover mp3 = S3 의 방금 쓴 키에서 GET → basename 조인 (키 왕복 증명).
    if AUDIO_LIVE.exists():
        shutil.rmtree(AUDIO_LIVE)
    AUDIO_LIVE.mkdir(parents=True)
    for p in AUDIO_DIR.glob("r*.mp3"):
        shutil.copyfile(p, AUDIO_LIVE / p.name)
    s3 = _s3_client()
    basename = items[0]["mp3Key"].rsplit("/", 1)[-1]
    s3.download_file(BUCKET, items[0]["mp3Key"], str(AUDIO_LIVE / basename))
    mp3_md5 = _md5_file(AUDIO_LIVE / basename)
    assert mp3_md5 == _md5_file(CHD_MP3), f"S3 왕복 mp3 md5 상이: {mp3_md5}"

    # (c) live doc 렌더 — audio_dir = S3 왕복 mp3 디렉터리.
    audio_orig = AUDIO_DIR
    AUDIO_DIR = AUDIO_LIVE
    try:
        r = _render_once("live_render", {"result": res})
    finally:
        AUDIO_DIR = audio_orig
    discover_lines = [
        ln for ln in r["stdout"].splitlines() if ln.startswith("[discover] rid=")]
    chd_frames = json.loads((CHD_EV / "frames_md5_injected.json").read_text())
    chain_same = r["framesMd5"] == chd_frames

    ok, lines = _verify_stock(
        pathlib.Path(r["out"]), r["report"], {"result": res},
        OUT / "rig_live")
    for ln in lines:
        print(ln)

    (EV / "live_verdict.json").write_text(json.dumps({
        "meta": {"uid": UID, "aid": AID, "generated": _now(),
                 "docSource": "Firestore 재fetch (로컬 캐시 미사용)",
                 "mp3Source": f"s3://{BUCKET}/{items[0]['mp3Key']} GET "
                              f"(md5={mp3_md5})"},
        "liveDocFieldsMatch": bool(disc_match and rc_match),
        "injectedChainSame": chain_same,
        "chainRef": "chd frames_md5_injected.json (repo 고정)",
        "rigStockAllPass": ok,
        "rigLines": lines,
        "discoverLogSeen": bool(discover_lines),
        "discoverLogLines": discover_lines,
        "mp4Md5": r["mp4Md5"],
        "outFile": r["out"],
    }, ensure_ascii=False, indent=1))
    print(f"live: docMatch={disc_match and rc_match} chainSame={chain_same} "
          f"rig={'PASS' if ok else 'FAIL'} discoverLog={len(discover_lines)}")


# ── check-apply ──────────────────────────────────────────────────────────────

def check_apply() -> int:
    fails: list[str] = []
    pl = EV / "production_log.json"
    lv = EV / "live_verdict.json"
    if not pl.exists():
        print("CHECK-APPLY FAIL: production_log.json 부재")
        return 1
    p = json.loads(pl.read_text())
    if p.get("status") != "APPLIED":
        fails.append(f"production_log status != APPLIED: {p.get('status')}")
    ops = [w.get("op") for w in p.get("writes", [])]
    if ops != ["s3.put_object", "s3.put_object",
               "firestore.update_analysis_discovery",
               "firestore.update_analysis_rendered_compare"]:
        fails.append(f"쓰기 4건 정확 아님: {ops}")
    s3w = [w for w in p.get("writes", []) if w.get("op") == "s3.put_object"]
    if not (s3w and s3w[0].get("s3RoundtripMd5") == APPROVED_MP4_MD5):
        fails.append("mp4 업로드 md5 재확인 로그 부재/불일치")
    rc = [w for w in p.get("writes", [])
          if w.get("op") == "firestore.update_analysis_rendered_compare"]
    fz = (rc[0]["args"].get("freezes") if rc else None) or []
    if len(fz) != 6 or not any(f["rid"] == "r04:discover" for f in fz):
        fails.append(f"renderedCompare freezes 6건/r04:discover 아님: {fz}")
    if not lv.exists():
        fails.append("live_verdict.json 부재")
    else:
        v = json.loads(lv.read_text())
        for k in ("liveDocFieldsMatch", "injectedChainSame",
                  "rigStockAllPass", "discoverLogSeen"):
            if not v.get(k):
                fails.append(f"live_verdict.{k} != true")
    if fails:
        print("CHECK-APPLY FAIL:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("CHECK-APPLY PASS (S3 2건 md5 재확인 + doc 2필드 로그 전건 + live "
          "재fetch 렌더 == chd 승인본 + 무수정 verify ALL PASS)")
    return 0


def main() -> int:
    apr = argparse.ArgumentParser()
    apr.add_argument("--fetch", action="store_true")
    apr.add_argument("--baseline", action="store_true")
    apr.add_argument("--inject", action="store_true")
    apr.add_argument("--check-wire", action="store_true")
    apr.add_argument("--apply", action="store_true")
    apr.add_argument("--live", action="store_true")
    apr.add_argument("--check-apply", action="store_true")
    args = apr.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    EV.mkdir(exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.fetch:
        fetch()
    if args.baseline:
        fetch()
        baseline()
    if args.inject:
        fetch()
        inject()
    if args.check_wire:
        return check_wire()
    if args.apply:
        fetch()
        apply()
    if args.live:
        fetch()
        live()
    if args.check_apply:
        return check_apply()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
