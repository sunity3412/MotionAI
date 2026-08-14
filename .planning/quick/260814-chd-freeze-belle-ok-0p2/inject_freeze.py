#!/usr/bin/env python3
"""발굴 정지 캡션·음성 교체 재렌더 — 0p2 하네스 사본 확장 (quick-260814-chd).
원본 스크립트/운영 코드/0p2 사본 무수정 (backend/ + 0p2 dir diff 0).

belle 판정(2026-08-14 "영상은 괜찮음, 캡션만 고치면 됨") 반영: 발굴 정지
(왼무릎, u12.8667/r12.40)의 캡션을 belle 결함 서사("다리 펴고 회전 후 걸기")에
정합하는 박제 신규 문장(DISCOVER_TEXT)으로 교체하고, 같은 문장을 Polly 로 새로
합성(자막=음성 lockstep 유지 — cue_text 단일 소스 원칙의 발굴 정지판)해 로컬
재렌더한다. 원본 r04 정지(10.5s)는 그 순간 기준으로 옳으므로 무변경.

0p2 대비 변경점:
  · DISCOVER_TEXT 상수 (박제 원문 — Polly Text / freeze text / H3 delta
    expected 3곳 단일 참조)
  · DISCOVER_MP3 = evidence/discover_left_knee.mp3 (repo 보존 — 렌더 결정론의
    고정 입력. Polly 는 호출마다 바이트가 달라 멱등 합성 필수)
  · --synthesize 스테이지 (멱등 — mp3 존재 시 재합성 금지)
  · _install_injection: discover freeze 의 text/mp3/dur 3필드만 교체
  · 리그 사본 delta 2축: H2 tuple (0p2 그대로) + H3 discover expected 교체
    (rid 단위 text_overrides 는 원본 r04 와 rid 공유라 불가 — locked 2)
  · stock 국한 = FAIL 정확 2건 (H2 discover + H3 discover) + 원본 r04 H3
    PASS 정확 1건 (캡션 무변경 기계 증명)
  · 카드 md5 게이트 = 0p2 카드 3장과 동일 (무릎 상이 = STOP, locked 5)
  · --stills 스테이지 (육안 실물 — 새 캡션 구움 / 구 캡션 무변경)

제약: S3 GET 만(put 스텁 캡처) · Firestore 쓰기 0 · Gemini 실호출 0 (replay
스텁) · Polly 1회(TTS 비-LLM) · Pod 무접촉 · 채점 무접촉.

stages:
  --synthesize      DISCOVER_TEXT Polly 합성 -> evidence mp3 (멱등)
  --fetch           wif_fresh 캐시 확인/재수화 + 전 rid mp3 + Pod eye ledger
  --baseline        주입 off 렌더 2회 + 운영 리그 무수정 ALL PASS + 결정론
  --check-baseline  Task 2 게이트 (베이스라인)
  --inject          주입 on 렌더 2회 + 리그(무수정 2FAIL 국한 + 사본 delta
                    ALL PASS) + diff 국한 기계 증명(report/compose/mp4 3층)
  --recontent       mp4Level 재계산 (compose 캐시 무결성 선확인)
  --cards           운영 헬퍼 _run_gated_card_inherit 호출 (눈 replay 스텁)
  --stills          육안 스틸 2장 (발굴 정지 새 캡션 / 원본 r04 구 캡션)
  --check-inject    Task 2 게이트 (주입)
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
INJECT_SRC = "discover"  # 신설 라벨 — align-peak/pole 사칭 금지 (T-chd-01)

# 박제 신규 문장 (PLAN locked_decisions 1 — 문자 단위 이 원문 그대로.
# 재작성·윤문 금지. 문장 경계 = 마침표 + 공백: cue_text coach_audio_speech_text
# 의 Polly run-on 방지 규칙 미러 — belle 08-07 실기기 반려 근거).
DISCOVER_TEXT = (
    "기준 자세는 다리를 곧게 편 채 회전하는 순간인데, 왼쪽 무릎이 접혀 "
    "있어요. 무릎을 접은 채 돌지 말고, 다리를 끝까지 편 상태로 회전한 뒤에 "
    "걸어보세요."
)

SP = pathlib.Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "ae166167-1abf-4754-9fe8-336a719ef9e2/scratchpad"
) / "wif_fresh"
OUT = SP.parent / "chd_out"
DATA = _REPO / ".planning/phases/35-server-rendered-comparison-video/data"
WIF_EV = _REPO / ".planning/quick/260813-wif-knee-discovery/evidence"
P02_CARDS = (_REPO / ".planning/quick/260814-0p2-fresh-pdshape-freeze"
             / "evidence" / "cards")
EV = _HERE / "evidence"

DISCOVER_MP3 = EV / "discover_left_knee.mp3"

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


def _aws_session():
    import boto3

    return boto3.Session(
        profile_name=os.environ.get("AWS_PROFILE", "sunity-motion"))


def _s3_client():
    return _aws_session().client("s3", region_name="ap-northeast-2")


# ── synthesize (Task 1 — Polly 1회, 멱등) ────────────────────────────────────

def synthesize() -> None:
    """DISCOVER_TEXT 를 Polly 합성 → evidence mp3 고정 (멱등 — 재합성 금지.

    Polly 는 호출마다 바이트가 달라 렌더 결정론이 깨진다 — T-chd-02).
    파라미터 = 운영 _synthesize_coach_audio_items 미러 (app.py:3981-3986):
    Seoyeon/neural = env 기본값 미러 (Pod env 실값은 터미네이트로 확인 불가 —
    기본값 채택을 기록으로 남긴다). 자격증명만 로컬 프로필 (sunity-motion).
    """
    from sunity_shared.analysis import compare_render as cr

    EV.mkdir(exist_ok=True)
    if DISCOVER_MP3.exists() and DISCOVER_MP3.stat().st_size > 0:
        print(f"synthesize: skip (멱등 — 기존 mp3 유지 "
              f"{DISCOVER_MP3.stat().st_size} bytes, "
              f"md5={_md5_file(DISCOVER_MP3)})")
        return
    polly = _aws_session().client("polly", region_name="ap-northeast-2")
    resp = polly.synthesize_speech(
        Text=DISCOVER_TEXT,
        VoiceId="Seoyeon",
        Engine="neural",
        LanguageCode="ko-KR",
        OutputFormat="mp3",
    )
    audio = resp["AudioStream"].read()
    assert audio, "Polly AudioStream 비어 있음"
    DISCOVER_MP3.write_bytes(audio)
    dur = cr.mp3_duration_s(DISCOVER_MP3)
    (EV / "polly_synthesis.json").write_text(json.dumps({
        "voiceId": "Seoyeon",
        "engine": "neural",
        "languageCode": "ko-KR",
        "outputFormat": "mp3",
        "text": DISCOVER_TEXT,
        "mp3Md5": _md5_file(DISCOVER_MP3),
        "mp3Bytes": len(audio),
        "durationS": round(dur, 3),
        "synthesizedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "note": "Seoyeon/neural = 운영 _synthesize_coach_audio_items env "
                "기본값 미러 (POLLY_VOICE_ID/POLLY_ENGINE Pod env 실값은 "
                "터미네이트로 확인 불가 — 기본값 채택). 자격증명만 로컬 "
                "프로필(sunity-motion). Polly = TTS 비-LLM 실호출 1회.",
    }, ensure_ascii=False, indent=1))
    print(f"synthesize: OK {len(audio)} bytes dur={dur:.3f}s "
          f"md5={_md5_file(DISCOVER_MP3)}")


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
        f"{INJECT_RID}.mp3 부재 — 원본 r04 정지의 음성 소스 실종 (0p2 실측과"
        " 상이): SUPPORT-SURFACE/FINDINGS 에 명기 필요")

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

    0p2 대비 3필드만 교체 (belle 캡션 판정 반영 — chd locked):
      text = DISCOVER_TEXT               (구 r04 문구 재사용 제거)
      mp3  = DISCOVER_MP3                (새 Polly 합성본 — 자막=음성 lockstep)
      dur  = mp3_duration_s(DISCOVER_MP3) + FREEZE_TAIL_S (운영 규칙
             compare_render.py:1310 그대로 — 길이 변동은 정상, 실측 기록)
    나머지 (markers/_body_line_viz 미러, ut/rt, rid, joint) 전부 0p2 그대로.
    audio_dir/r04.mp3 는 원본 r04 정지 전용으로 잔류 — record-driven 원본
    build_timeline 경로 무접촉. render() 가 ut 순 정렬(:1423)하므로 삽입
    위치는 자동.
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
        _ = rec  # rid 존재 확인용 (필드 생산은 전부 chd 고정 스펙)
        assert DISCOVER_MP3.exists(), (
            f"주입 freeze mp3 부재: {DISCOVER_MP3} — 합성 선행 필요 "
            "(--synthesize)")
        ut, rt = float(INJECT_UT), float(INJECT_RT)
        markers = cr._align_markers(align, rec, ut)  # noqa: SLF001
        body_viz = cr._body_line_viz(align, ut, rt, poles or {})  # noqa: SLF001
        if body_viz is not None:
            markers = []  # compare_render.py:1261-1262 미러 (표시 소유권)
        freezes.append({
            "rid": INJECT_RID, "ut": ut, "rt": rt,
            "pair_src": INJECT_SRC,
            "dur": cr.mp3_duration_s(DISCOVER_MP3) + cr.FREEZE_TAIL_S,
            "mp3": DISCOVER_MP3, "joint": INJECT_JOINT, "markers": markers,
            "legs_viz": None, "viz_kind": None, "viz_side": None,
            "pole_viz": None, "body_viz": body_viz,
            "text": DISCOVER_TEXT,
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


def _make_h3_discover_delta(orig_auth):
    """H3 discover 사본 delta — discover freeze 의 H3 엔트리만 expected 를
    DISCOVER_TEXT 실제 문자 비교로 교체 (fail-closed: 불일치면 FAIL 그대로).

    rid 단위 text_overrides 는 사용 불가 (compare_verify.py:256 — 발굴 정지와
    원본 정지가 rid=r04 공유, override 가 둘에 동시 적용돼 원본 쪽 FAIL —
    locked 2). 엔트리 매핑: H3 루프(compare_verify.py:251)는 freezes 순회 순서
    그대로이고 rec 부재 freeze 만 건너뛴다 — 같은 guard 로 서수를 계산해 대응
    엔트리를 특정한다. 원본 r04 를 포함한 비-discover freeze 의 H3 판정 무접촉.
    """

    def wrapped(report, doc, align=None, text_overrides=None):
        checks = orig_auth(
            report, doc, align=align, text_overrides=text_overrides)
        freezes = report.get("freezes") or []
        disc = [i for i, fz in enumerate(freezes)
                if fz.get("pairSrc") == INJECT_SRC]
        assert len(disc) == 1, (
            f"discover freeze 정확 1건 아님: {len(disc)}건 — delta 적용 불가")
        result = (doc.get("result")
                  if isinstance(doc.get("result"), dict) else {})
        records = (result.get("deductionBreakdown") or {}).get("records") or []
        by_rid = {
            str(r.get("recordId", "")).split(":")[0]: r
            for r in records
            if isinstance(r, dict) and r.get("recordId")
        }
        fz = freezes[disc[0]]
        assert by_rid.get(fz.get("rid")) is not None, (
            "discover freeze 의 rid 가 doc record 에 없음 — 매핑 불가")
        # H3 서수 = rec 보유 freeze 중 discover 가 몇 번째인가 (루프 guard 미러)
        ordinal = sum(
            1 for f in freezes[:disc[0]]
            if by_rid.get(f.get("rid")) is not None)
        h3_pos = [j for j, (name, _, _) in enumerate(checks)
                  if name.startswith("H3 자막 진품")]
        j = h3_pos[ordinal]
        ok = fz.get("text") == DISCOVER_TEXT
        tail = "(사본 delta — expected=발굴 박제 문장)"
        checks[j] = (
            f"H3 자막 진품 {fz.get('rid')}[discover]",
            ok,
            f"문자 일치 {tail}" if ok
            else f"불일치: 구운='{str(fz.get('text'))[:40]}…' {tail}",
        )
        return checks

    return wrapped


def _verify(mp4: pathlib.Path, report: dict, rig_dir: pathlib.Path,
            delta_label: str | None = None) -> tuple[bool, list[str]]:
    """운영 compare_verify.verify — delta_label 지정 시에만 사본 delta 2축.

    delta 축 = ① H2 tuple 1값(discover 라벨 — 0p2 그대로) ② H3 discover
    expected 교체 (_make_h3_discover_delta). align-peak/pole 사칭 절대 금지.
    """
    from sunity_shared.analysis import compare_verify as cv

    doc = json.loads(DOC.read_text())
    align = json.loads(ALIGN_JSON.read_text())
    rig_dir.mkdir(parents=True, exist_ok=True)
    orig_src = cv._H2_UT_DISPLACING_SRC  # noqa: SLF001
    orig_auth = cv.authenticity_checks
    try:
        if delta_label is not None:
            # 사본 delta (T-chd-01) — 판정 로직·타 항목 무접촉.
            cv._H2_UT_DISPLACING_SRC = orig_src + (delta_label,)  # noqa: SLF001
            cv.authenticity_checks = _make_h3_discover_delta(orig_auth)
        return cv.verify(mp4, report, rig_dir, align=align, doc=doc)
    finally:
        cv._H2_UT_DISPLACING_SRC = orig_src  # noqa: SLF001
        cv.authenticity_checks = orig_auth


def _extract_frame_idx(mp4: pathlib.Path, idx: int) -> np.ndarray:
    """프레임 **인덱스** 정확 추출 (select=eq) — -ss 초 지정의 half-frame
    경계 모호성(예: 56.65s x 30 = 1699.5) 제거."""
    import imageio_ffmpeg
    from PIL import Image

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    tmp = OUT / "_frame.png"
    if tmp.exists():
        tmp.unlink()
    subprocess.run(
        [ff, "-y", "-loglevel", "error", "-i", str(mp4),
         "-vf", f"select=eq(n\\,{idx})", "-vsync", "0",
         "-frames:v", "1", str(tmp)], check=True)
    return np.asarray(Image.open(tmp).convert("RGB"), dtype=np.int16)


def _load_compose_jpg(idx: int) -> np.ndarray:
    """현행 compose 캐시(마지막 렌더 = injected run)의 소스 JPEG (0-based idx)."""
    from PIL import Image

    p = RENDER_WORK / "compose30_1080" / f"{idx + 1:06d}.jpg"
    return np.asarray(Image.open(p).convert("RGB"), dtype=np.int16)


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


def _out_sec_of(report: dict, t: float) -> float:
    """user 초 t 의 출력 초 — 그 report 의 freeze 편성으로 유도 (재생 프레임)."""
    shift = sum(
        f["freezeS"] for f in report["freezes"] if f["userSec"] <= t)
    return t + shift


def _mp4_content_checks(base_report: dict, report: dict,
                        base_mp4: pathlib.Path, mp4: pathlib.Path) -> dict:
    """mp4 수준 내용 동일성 — 프레임 인덱스 정확 추출 + 공유 소스 전이 증명.

    내용 동일성의 **정본 층은 compose JPEG md5 사슬(bit-exact)** 이다. 이 층은
    "두 mp4 가 그 bit-동일 증명된 같은 소스 프레임의 인코드"임을 확인한다:
    cross(두 mp4 프레임 간) + 각 mp4 프레임 vs 공유 소스 JPEG (전이 증명).
    H.264 는 삽입점 이후(레이트컨트롤 이력 상이)와 삽입 직전 lookahead 창에서
    비트스트림이 갈리므로 디코드 픽셀이 코덱 노이즈만큼 다를 수 있다 — 노이즈는
    정직 기록 (hlv "디코드 노이즈 Δ3/255 구조 차 0" 선례). 게이트 = md5 동일
    또는 (양쪽 mp4 프레임이 같은 소스에 mean<=1.0/255 && cross mean<=1.0/255 —
    실측 mean 은 0.0001~0.6 대역, 임계는 코덱 노이즈 자릿수 상계이지 튜닝 아님).
    """
    inj_old = [f for f in report["freezes"] if f["pairSrc"] != INJECT_SRC]

    def _one(base_idx: int, inj_idx: int, label: dict) -> dict:
        a = _extract_frame_idx(base_mp4, base_idx)
        b = _extract_frame_idx(mp4, inj_idx)
        src = _load_compose_jpg(inj_idx)
        cross = _frame_compare(a, b)
        bsrc = _frame_compare(a, src)
        isrc = _frame_compare(b, src)
        ok = cross["identical"] or (
            bsrc["meanDelta"] <= 1.0 and isrc["meanDelta"] <= 1.0
            and cross["meanDelta"] <= 1.0)
        return {**label, "frameIdxBase": base_idx, "frameIdxInjected": inj_idx,
                "cross": cross, "baseVsSharedSrc": bsrc,
                "injectedVsSharedSrc": isrc, "contentSame": ok}

    freeze_checks = []
    for bf, jf in zip(base_report["freezes"], inj_old):
        bi = round((bf["voiceStartOutS"] + bf["freezeS"] / 2) * 30)
        ii = round((jf["voiceStartOutS"] + jf["freezeS"] / 2) * 30)
        freeze_checks.append(_one(bi, ii, {"rid": bf["rid"]}))
    playback_checks = []
    for t in (3.0, 12.0, 15.5):
        bi = round(_out_sec_of(base_report, t) * 30)
        ii = round(_out_sec_of(report, t) * 30)
        playback_checks.append(_one(bi, ii, {"userSec": t}))
    return {
        "method": "프레임 인덱스 정확 추출(select=eq) + 공유 소스 JPEG 전이 "
                  "증명 (cross + 각 mp4 vs bit-동일 소스 — 코덱 노이즈 정직 "
                  "기록. 정본 내용 증명은 composeLevel md5 사슬)",
        "freezeMidFrames": freeze_checks,
        "playbackSamples": playback_checks,
        "contentOk": all(c["contentSame"]
                         for c in freeze_checks + playback_checks),
    }


def recontent() -> None:
    """--inject 산출(mp4 2본 + report) 위에서 mp4Level 만 재계산 — 재렌더 0.

    compose 캐시가 injected 렌더 그대로인지 md5 사슬로 먼저 확인 (무결성)."""
    base_report = json.loads((OUT / "baseline_report.json").read_text())
    report = json.loads((OUT / "inject_report.json").read_text())
    vp = EV / "inject_verdict.json"
    verdict = json.loads(vp.read_text())
    base_mp4 = pathlib.Path(json.loads(
        (EV / "baseline_verdict.json").read_text())["outFiles"][0])
    mp4 = pathlib.Path(verdict["outFiles"][0])
    frames_inj = json.loads((EV / "frames_md5_injected.json").read_text())
    compose = RENDER_WORK / "compose30_1080"
    cur = [_md5_file(p) for p in sorted(compose.glob("*.jpg"))]
    assert cur == frames_inj, (
        "compose 캐시가 injected 렌더와 불일치 — --inject 재실행 필요")
    verdict["diffConfined"]["mp4Level"] = _mp4_content_checks(
        base_report, report, base_mp4, mp4)
    vp.write_text(json.dumps(verdict, ensure_ascii=False, indent=1))
    print(f"recontent: contentOk={verdict['diffConfined']['mp4Level']['contentOk']}")


# ── baseline (Task 2 (2)) ────────────────────────────────────────────────────

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
    # 0p2 재현 게이트 — freeze 5건 outSec 이 운영 doc 실증값과 일치 (0.01s)
    expected_out = {"r00": 5.33, "r01": 15.67, "r04": 29.93,
                    "r02": 43.0, "r03": 57.83}
    local = {f["rid"]: round(float(f["voiceStartOutS"]), 2) for f in fz}
    for rid, sec in expected_out.items():
        got = local.get(rid)
        if got is None or abs(got - sec) > 0.011:
            fails.append(f"베이스라인 outSec 재현 실패: {rid} {got} != {sec}")
    if not (EV / "frames_md5_baseline.json").exists():
        fails.append("frames_md5_baseline.json 부재")
    if fails:
        print("CHECK-BASELINE FAIL:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print(f"CHECK-BASELINE PASS (freezes {len(fz)}건, 리그 무수정 ALL PASS, "
          "md5 2회 동일, outSec 0p2/운영 doc 재현)")
    return 0


# ── inject (Task 2 렌더 + 리그 + diff 국한) ─────────────────────────────────

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

    # (2a) 무수정 판정기 — FAIL = 발굴 freeze 의 H2+H3 정확 2건 국한
    #      + 원본 r04 정지의 H3 PASS 정확 1건 (캡션 무변경 기계 증명)
    ok_stock, lines_stock = _verify(mp4, report, OUT / "rig_inj_stock")
    stock_fails = [ln for ln in lines_stock if ln.strip().startswith("[FAIL]")]
    h2_fails = [ln for ln in stock_fails
                if "H2 순간" in ln and f"src={INJECT_SRC}" in ln]
    h3_fails = [ln for ln in stock_fails
                if "H3 자막 진품 r04" in ln and DISCOVER_TEXT[:20] in ln]
    stock_confined = (
        len(stock_fails) == 2
        and len(h2_fails) == 1
        and len(h3_fails) == 1
    )
    orig_r04_h3_pass = [
        ln for ln in lines_stock
        if ln.strip().startswith("[PASS]")
        and "H3 자막 진품 r04" in ln and "문자 일치" in ln
    ]
    # (2b) 사본 delta 2축 (H2 tuple + H3 discover expected) — ALL PASS
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
        and inj_new[0]["text"] == DISCOVER_TEXT
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
        "insertMatchesFreezeS": m_matches_dur,
        "prefixSame": prefix_same, "suffixSameAfterFade": suffix_same,
        "fadeFramesChanged": fade_frames_changed, "nFade": N_FADE,
        "note": ("의도 변경 = 삽입 블록 " f"{m}프레임 + 복귀 크로스페이드 "
                 f"{N_FADE}프레임(ref 패널 블렌드). 그 외 전 프레임 JPEG md5 "
                 "bit-동일. 삽입점 이후 출력 초는 신규 정지 길이만큼 이동 — "
                 "내용 동일성으로 증명 (무변경 주장 아님)."),
    }

    # (3b') mp4 수준 — 프레임 인덱스 정확 추출 + 공유 소스 전이 증명.
    base_mp4 = pathlib.Path(json.loads(
        (EV / "baseline_verdict.json").read_text())["outFiles"][0])
    mp4_level = _mp4_content_checks(base_report, report, base_mp4, mp4)
    content_ok = mp4_level["contentOk"]

    verdict = {
        "meta": {
            "uid": UID, "aid": AID,
            "inject": {"rid": INJECT_RID, "joint": INJECT_JOINT,
                       "userSec": INJECT_UT, "refSec": INJECT_RT,
                       "pairSrc": INJECT_SRC,
                       "text": DISCOVER_TEXT,
                       "mp3": str(DISCOVER_MP3)},
            "generated": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        },
        "freezes": report["freezes"],
        "rigStock": {
            "verifier": "compare_verify.verify 무수정",
            "allPass": ok_stock,
            "failLines": stock_fails,
            "confinedToDiscoverH2H3": stock_confined,
            "origR04H3PassCount": len(orig_r04_h3_pass),
            "origR04H3PassLines": orig_r04_h3_pass,
            "note": "기존 freeze 전건 = 무수정 판정기 기준 PASS (T-chd-01). "
                    "FAIL = 신규 discover freeze 의 H2(순간)+H3(신규 캡션) "
                    "정확 2건 — 게이트가 외부 삽입과 캡션 교체를 설계대로 "
                    "검출한 것. 원본 r04 정지의 H3 PASS 1건 = 캡션 무변경 "
                    "기계 증명.",
        },
        "rigDelta": {
            "verifier": "compare_verify.verify + 사본 delta 2축: "
                        f"_H2_UT_DISPLACING_SRC 1값('{INJECT_SRC}') + H3 "
                        "discover expected=DISCOVER_TEXT 교체 — 판정 로직 "
                        "무접촉, 라벨 명기 (사칭 0)",
            "allPass": ok_delta,
            "lines": lines_delta,
            "productionChange": "운영 반영 시 compare_verify "
                                "_H2_UT_DISPLACING_SRC 면제 튜플 확장 + 발굴 "
                                "캡션 소스의 doc 영속화 규약 필요 "
                                "(0p2 SUPPORT-SURFACE §5 + 이번 캡션 소스)",
        },
        "diffConfined": {
            "reportLevel": {"oldFieldsSame": old_fields_same,
                            "newExactlyOne": new_exact},
            "composeLevel": compose_proof,
            "mp4Level": mp4_level,
        },
        "determinism": {
            "mp4Md5Run1": r1["mp4Md5"], "mp4Md5Run2": r2["mp4Md5"],
            "mp4Same": det, "composeFramesSame": det_frames,
            "reportSame": same_report,
        },
        "discoverFreezeS": dur_new,
        "outFiles": [r1["out"], r2["out"]],
    }
    (EV / "inject_verdict.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=1))
    (EV / "frames_md5_injected.json").write_text(json.dumps(frames1))
    (OUT / "inject_report.json").write_text(json.dumps(report))
    print(f"inject: freezes={len(report['freezes'])} "
          f"rigStock confined2={stock_confined} "
          f"origR04H3Pass={len(orig_r04_h3_pass)} "
          f"rigDelta={'PASS' if ok_delta else 'FAIL'} "
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
    os.environ["GEMINI_API_KEY"] = "stub-chd-replay-only"
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
                    "reason": "chd replay 스텁 매핑 불가 (실호출 금지)",
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
                    uid=UID, analysis_id=f"{AID}-chd-inject",
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


# ── stills (Task 2 육안 실물 — frames-before-numbers 게이트) ─────────────────

def stills() -> None:
    """injected mp4 에서 육안 스틸 2장 인덱스 정확 추출.

    ① 발굴 정지 중앙 프레임 — 새 캡션(DISCOVER_TEXT)이 화면에 구워져 있는지
    ② 원본 r04 정지(10.5s) 중앙 프레임 — 구 문구 잔존(무변경)
    """
    from PIL import Image

    report = json.loads((OUT / "inject_report.json").read_text())
    mp4 = pathlib.Path(json.loads(
        (EV / "inject_verdict.json").read_text())["outFiles"][0])
    sd = EV / "stills"
    sd.mkdir(parents=True, exist_ok=True)
    for fz in report["freezes"]:
        if fz["pairSrc"] == INJECT_SRC:
            name = "discover_freeze_new_caption.png"
        elif fz["rid"] == INJECT_RID:
            name = "orig_r04_freeze_old_caption.png"
        else:
            continue
        idx = round((fz["voiceStartOutS"] + fz["freezeS"] / 2) * 30)
        arr = _extract_frame_idx(mp4, idx)
        Image.fromarray(arr.astype(np.uint8)).save(sd / name)
        print(f"still: {name} frameIdx={idx} userSec={fz['userSec']} "
              f"freezeS={fz['freezeS']:.3f}")


# ── check-inject (Task 2 게이트) ─────────────────────────────────────────────

def check_inject() -> int:
    from sunity_shared.analysis import compare_render as cr

    fails: list[str] = []
    p = EV / "inject_verdict.json"
    if not p.exists():
        print("FAIL: inject_verdict.json 부재")
        return 1
    v = json.loads(p.read_text())
    if not v["rigDelta"]["allPass"]:
        fails.append("리그(사본 delta) ALL PASS 아님")
    rs = v["rigStock"]
    if not rs["confinedToDiscoverH2H3"]:
        fails.append("무수정 판정기 FAIL 이 discover H2+H3 정확 2건 국한 아님: "
                     f"{rs['failLines']}")
    if rs.get("origR04H3PassCount") != 1:
        fails.append("원본 r04 정지의 H3 PASS 정확 1건 아님 (캡션 무변경 기계 "
                     f"증명 실패): count={rs.get('origR04H3PassCount')}")
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

    # discover freeze 캡션·길이 게이트 (chd 신설)
    disc = [f for f in (v.get("freezes") or [])
            if f.get("pairSrc") == INJECT_SRC]
    if len(disc) != 1:
        fails.append(f"discover freeze 정확 1건 아님: {len(disc)}")
    else:
        if disc[0].get("text") != DISCOVER_TEXT:
            fails.append("discover freeze text != DISCOVER_TEXT (문자 단위)")
        if not DISCOVER_MP3.exists():
            fails.append("discover mp3 부재")
        else:
            want = cr.mp3_duration_s(DISCOVER_MP3) + 0.4
            got = float(disc[0].get("freezeS") or 0.0)
            if abs(got - want) > 0.01:
                fails.append(
                    f"discover freezeS {got:.3f} != mp3+0.4 {want:.3f}")

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

    # 카드 md5 무회귀 — chd cardMd5Run1 == 0p2 evidence/cards 실파일 md5 (3장).
    # 무릎 카드 상이 = 카드에 문장 구움 의심 -> STOP (locked 5).
    md5s = cards_v.get("cardMd5Run1") or {}
    knee_png = f"zoom_angle_vs_reference__{INJECT_JOINT}.png"
    p02 = {q.name: _md5_file(q) for q in sorted(P02_CARDS.glob("*.png"))}
    if len(p02) != 3:
        fails.append(f"0p2 대조 카드 3장 아님: {sorted(p02)}")
    if sorted(md5s) != sorted(p02):
        fails.append(f"카드 파일명 집합 상이: chd={sorted(md5s)} "
                     f"0p2={sorted(p02)}")
    for name, ref_md5 in p02.items():
        got = md5s.get(name)
        if got is None or got == ref_md5:
            continue
        if name == knee_png:
            fails.append(
                "카드에 문장 구움 의심 — STOP, belle 재채택 필요 보고 "
                f"(무릎 카드 md5 상이: chd={got} 0p2={ref_md5})")
        else:
            fails.append(f"카드 회귀: {name} chd={got} 0p2={ref_md5}")

    if fails:
        print("CHECK-INJECT FAIL:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("CHECK-INJECT PASS (리그 delta ALL PASS + 무수정 2FAIL 국한 + 원본 "
          "r04 H3 PASS 1건 + 결정론 + diff 국한 3층 + discover 캡션/길이 + "
          "카드 상속 u12.8667/r12.40 + 카드 3장 md5 == 0p2 + 눈 실호출 0)")
    return 0


def main() -> int:
    apr = argparse.ArgumentParser()
    apr.add_argument("--synthesize", action="store_true")
    apr.add_argument("--fetch", action="store_true")
    apr.add_argument("--baseline", action="store_true")
    apr.add_argument("--check-baseline", action="store_true")
    apr.add_argument("--inject", action="store_true")
    apr.add_argument("--recontent", action="store_true")
    apr.add_argument("--cards", action="store_true")
    apr.add_argument("--stills", action="store_true")
    apr.add_argument("--check-inject", action="store_true")
    args = apr.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    EV.mkdir(exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.synthesize:
        synthesize()
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
    if args.recontent:
        recontent()
    if args.cards:
        cards()
    if args.stills:
        stills()
    if args.check_inject:
        return check_inject()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
