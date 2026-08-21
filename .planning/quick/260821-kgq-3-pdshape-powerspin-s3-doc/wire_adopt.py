#!/usr/bin/env python3
"""발굴 신규 채택 2건 프로덕션 반영 드라이버 (quick-260821-kgq).

di7 wire_discover.py 미러 — belle 08-21 판정("추천 1, 2 둘 다 오케이")의 이행.
좌표를 동작별 JOBS 상수 블록으로 파라미터화한 것 외 경로 발명 0 (D-03):
compare_render.build_timeline / compare_verify.verify / firestore_admin /
s3keys 전부 backend 원본 무수정 호출.

대상 2건 (PLAN locked_coordinates — 재조사 금지, rid 만 live doc 재해석):
  pdshape   : uid fvcN…/aid p34fresh1786628533 — 왼팔꿈치 u16.4667/r15.1333
              (ehz cand17B). 현행 운영본(knee discover 포함 6 freezes) 위에
              elbow 추가 → 7 freezes.
  powerspin : uid csKW…/aid powerspinFault1785373695 — 왼어깨 u0.4667/r0.7333
              (ehz cand01E). renderedCompare/discovery 신설.

stages:
  --synthesize   두 DISCOVER_TEXT Polly 합성 → evidence mp3 고정 (멱등 —
                 재실행 = skip. Polly 는 TTS 비-LLM, Gemini/Cerebras 호출 0)
  --fetch        live doc 재fetch + rid suffix 해석(정확 1건 아니면 STOP) +
                 사전 상태 assert (pdshape: 6 freezes/knee discovery/현행 mp4
                 md5 77cdcd43… — 불일치 STOP · powerspin: renderedCompare/
                 discovery 부재 — 존재 시 STOP) + 영상/coach mp3 S3 GET +
                 align 재구성 (P35 트랙 replay — chd fetch 패턴)
  --baseline     live doc 그대로 렌더 2회 — 결정론 + 무수정 verify ALL PASS.
                 pdshape 는 사슬 == chd frames_md5_injected.json (왼무릎 정지
                 보존의 실렌더 증명 — 불일치 = 환경 drift STOP)
  --inject       discovery payload 병합(기존 항목 보존 — T-kgq-02) → 렌더 2회
                 — [discover] 로그 / 기존 freeze 정체성 전건 보존 / 무수정
                 verify ALL PASS / 음성 게이트(+0.5s 비틀기 → H2 FAIL) / 스틸
  --check-wire   위 전부 기계 게이트 (exit code)
  --apply        프로덕션 반영 (belle 08-21 승인 — D-01): 사전 assert 재실행
                 후 쓰기 4건, 전건 {motion}_production_log.json 박제
  --live         반영 검증: doc 재fetch == payload → live doc + S3 방금 쓴
                 mp3 GET 재렌더 — 사슬 == inject + 무수정 verify ALL PASS
  --check-apply  production_log + live_verdict 기계 게이트 (exit code)

제약: backend/ 수정 0 · LLM 추론 호출 0 (Polly TTS 2회만 — --synthesize) ·
시크릿 로그 0 · 캐시 = 현 세션 scratchpad (구 세션 캐시 재사용 0 — 휘발).
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
import subprocess
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
_VENV_PY = _REPO / "backend" / ".venv" / "bin" / "python"
sys.path.insert(0, str(_REPO / "backend" / "shared" / "python"))

BUCKET = "sunity-motion-pilot-videos"
ADOPTED_AT = "2026-08-21"

# ── 캡션 정본 (PLAN D-04 — 문자 단위 그대로, 실행 중 개작 금지) ──────────────
DISCOVER_TEXT_ELBOW = (
    "기준 자세는 팔을 곧게 뻗어 폴을 잡는 순간인데, 왼쪽 팔꿈치가 접혀 "
    "있어요. 손을 급하게 뻗어 잡으면 팔꿈치가 접혀요. 조금 더 돌고 올라온 "
    "뒤에 팔을 뻗어 편하게 잡아보세요."
)
DISCOVER_TEXT_SHOULDER = (
    "기준 자세는 팔을 굽혀 몸을 높이 들어올린 순간인데, 왼쪽 팔이 곧게 뻗어 "
    "있어요. 시작할 때 팔을 굽혀 몸을 폴 쪽으로 당겨서, 안정적인 위치를 만든 "
    "뒤에 돌아보세요."
)

# chd 승인 knee 캡션 (di7 반영 정본 — live doc discovery 대조용)
KNEE_TEXT = (
    "기준 자세는 다리를 곧게 편 채 회전하는 순간인데, 왼쪽 무릎이 접혀 "
    "있어요. 무릎을 접은 채 돌지 말고, 다리를 끝까지 편 상태로 회전한 뒤에 "
    "걸어보세요."
)

# 세션 경로 — 현 세션 scratchpad (구 세션 캐시 휘발 — 재사용 0, D-03 개작점)
SP_ROOT = pathlib.Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "aaf15967-cfc7-4d52-bfda-e1edd9858ef9/scratchpad")
EV = _HERE / "evidence"
CHD_EV = _REPO / ".planning/quick/260814-chd-freeze-belle-ok-0p2/evidence"
CHD_KNEE_MP3 = CHD_EV / "discover_left_knee.mp3"
P35_DATA = _REPO / ".planning/phases/35-server-rendered-comparison-video/data"

# di7 반영 정본 (pdshape 사전 assert 기준값 — PLAN locked_coordinates)
PDSHAPE_MP4_MD5 = "77cdcd436472438f3580cbb8d48683f3"
KNEE_MP3_MD5 = "7fb6a4a3859cbea445266a9877847f94"
PDSHAPE_EXPECTED_FREEZES = [
    ("r00", 5.33), ("r01", 15.67), ("r04", 29.93),
    ("r04:discover", 42.07), ("r02", 54.17), ("r03", 69.0),
]

JOBS: dict[str, dict] = {
    "pdshape": {
        "uid": "fvcNXzEqKjgqVxRPVSj1iwFnIpn2",
        "aid": "p34fresh1786628533",
        "motionId": "ref-pdshape",
        "refVideoKey": "reference/ref-pdshape.mp4",
        "p35Dir": "pdshapefault",
        "joint": "left_elbow",
        "uSec": 16.4667,
        "rSec": 15.1333,
        "recordSuffix": "angle_vs_reference__left_elbow",
        "text": DISCOVER_TEXT_ELBOW,
        "mp3Ev": EV / "discover_left_elbow.mp3",
        "coachN": 5,
        "alignFrames": (272, 237),
        # 현행 운영 doc 이 knee discovery 를 이미 보유 — 베이스라인 사슬 정본
        # = chd injected (di7 live_verdict 와 같은 대조축).
        "chainRef": CHD_EV / "frames_md5_injected.json",
        "expectRenderedCompare": True,
        "expectDiscoverBaseline": 1,
    },
    "powerspin": {
        "uid": "csKWYvI3WCPYPysNQ9KkWecaUvq1",
        "aid": "powerspinFault1785373695",
        "motionId": "ref-power-spin",
        "refVideoKey": "reference/ref-power-spin.mp4",
        "p35Dir": "powerspin",
        "joint": "left_shoulder",
        "uSec": 0.4667,
        "rSec": 0.7333,
        "recordSuffix": "angle_vs_reference__left_shoulder",
        "text": DISCOVER_TEXT_SHOULDER,
        "mp3Ev": EV / "discover_left_shoulder.mp3",
        "coachN": 3,
        "alignFrames": (123, 158),
        "chainRef": None,  # 선행 승인 사슬 없음 — 자기 결정론 + 무수정 리그
        "expectRenderedCompare": False,
        "expectDiscoverBaseline": 0,
    },
}

log = logging.getLogger("wire_adopt")


def _ensure_venv() -> None:
    """의존성 부재 시 backend/.venv 인터프리터로 재실행 (버전 박힌 경로)."""
    try:
        import imageio_ffmpeg  # noqa: F401
        from google.cloud import firestore  # noqa: F401
    except ImportError:
        if os.environ.get("KGQ_REEXEC") == "1":
            raise
        os.environ["KGQ_REEXEC"] = "1"
        os.execv(str(_VENV_PY), [str(_VENV_PY), *sys.argv])


def _md5_file(p: pathlib.Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _sp(motion: str) -> pathlib.Path:
    return SP_ROOT / f"kgq_{motion}"


def _out(motion: str) -> pathlib.Path:
    return SP_ROOT / "kgq_out" / motion


def _paths(motion: str) -> dict:
    sp = _sp(motion)
    return {
        "sp": sp, "out": _out(motion),
        "doc": sp / "doc.json", "align": sp / "align.json",
        "user": sp / "user.mp4", "ref": sp / "ref.mp4",
        "audio": sp / "audio", "audio_live": sp / "audio_live",
        "render": sp / "render",
        "verdict": EV / f"{motion}_wire_verdict.json",
        "prodlog": EV / f"{motion}_production_log.json",
        "livev": EV / f"{motion}_live_verdict.json",
        "frames_inject": EV / f"{motion}_frames_md5_inject.json",
    }


def _merge_verdict(path: pathlib.Path, section: str, payload: dict,
                   job: dict) -> None:
    v = json.loads(path.read_text()) if path.exists() else {}
    v[section] = payload
    v.setdefault("meta", {"uid": job["uid"], "aid": job["aid"],
                          "motionId": job["motionId"]})
    v["meta"]["updated"] = _now()
    path.write_text(json.dumps(v, ensure_ascii=False, indent=1))


def _stop(motion: str, job: dict, stage: str, reason: str,
          observed: dict | None = None) -> None:
    """STOP 게이트 — 쓰기 없이 중단 + 관측 그대로 박제 (우회 금지)."""
    p = _paths(motion)
    _merge_verdict(p["verdict"], f"STOP_{stage}", {
        "status": "STOP", "reason": reason, "observed": observed or {},
        "at": _now(),
    }, job)
    raise SystemExit(f"STOP[{motion}/{stage}]: {reason}")


def _aws_session():
    import boto3

    return boto3.Session(
        profile_name=os.environ.get("AWS_PROFILE", "sunity-motion"))


def _s3_client():
    return _aws_session().client("s3", region_name="ap-northeast-2")


def _fa():
    if not os.environ.get("FIREBASE_SA_PATH") and not os.environ.get(
            "FIREBASE_SA_JSON"):
        os.environ["FIREBASE_SA_PATH"] = str(_REPO / "firebase-sa.json")
    from sunity_shared import firestore_admin as fa

    return fa


def _live_doc(fa, job: dict) -> dict:
    doc = (
        fa._db().collection("users").document(job["uid"])  # noqa: SLF001
        .collection("analyses").document(job["aid"]).get().to_dict()
    )
    assert doc and isinstance(doc.get("result"), dict), (
        f"live doc {job['aid']} 조회 실패 또는 result 부재")
    return doc


def _resolve_rid(motion: str, job: dict, res: dict) -> str:
    """records 에서 criterion suffix 정확 1건 매칭 — 2건 이상/0건 = STOP."""
    matches = []
    for rec in (res.get("deductionBreakdown") or {}).get("records") or []:
        rec_id = str(rec.get("recordId", ""))
        if ":" not in rec_id:
            continue
        rid, crit = rec_id.split(":", 1)
        if crit == job["recordSuffix"]:
            matches.append((rid, rec))
    if len(matches) != 1:
        _stop(motion, job, "rid", (
            f"suffix {job['recordSuffix']!r} 매칭 {len(matches)}건 "
            f"(정확 1건 요구)"),
            {"matches": [m[0] for m in matches]})
    return matches[0][0]


def _discovery_items(motion: str, job: dict, res: dict) -> list[dict]:
    """반영 payload — 렌더 재현(inject)과 update_analysis_discovery(apply),
    live 대조가 이 함수 하나를 공유 (단일 소스). 기존 항목 병합 필수
    (update_analysis_discovery 는 field 통째 교체 — T-kgq-02)."""
    from sunity_shared import s3keys

    rid = _resolve_rid(motion, job, res)
    new_item = {
        "rid": rid, "joint": job["joint"],
        "userSec": job["uSec"], "refSec": job["rSec"],
        "pairSrc": "discover", "text": job["text"],
        "mp3Key": s3keys.build_discover_audio_key(
            job["uid"], job["aid"], rid, job["joint"]),
        "adoptedAt": ADOPTED_AT,
    }
    existing = list(((res.get("discovery") or {}).get("items")) or [])
    if motion == "pdshape":
        expected_knee = {
            "rid": "r04", "joint": "left_knee",
            "userSec": 12.8667, "refSec": 12.4,
            "pairSrc": "discover", "text": KNEE_TEXT,
            "mp3Key": s3keys.build_discover_audio_key(
                job["uid"], job["aid"], "r04", "left_knee"),
            "adoptedAt": "2026-08-14",
        }
        if existing != [expected_knee]:
            _stop(motion, job, "merge", (
                "live discovery != di7 knee 정본 — 병합 전제 붕괴 (T-kgq-02)"),
                {"liveItems": existing})
    else:
        if existing:
            _stop(motion, job, "merge",
                  "live discovery 존재 — 부재 전제 위반", {"liveItems": existing})
    return existing + [new_item]


# ── synthesize (Task 1 — Polly 2회, 멱등) ────────────────────────────────────

def synthesize() -> None:
    """두 DISCOVER_TEXT 를 Polly 합성 → evidence mp3 고정 (멱등 — 재합성 금지.

    Polly 는 호출마다 바이트가 달라 렌더 결정론이 깨진다). 파라미터 = 운영
    _synthesize_coach_audio_items env 기본값 미러 (chd synthesize() 그대로 —
    Seoyeon/neural/ko-KR/ap-northeast-2, 자격증명 = 로컬 프로필 sunity-motion).
    Polly = TTS 비-LLM — Gemini/Cerebras 호출 0.
    """
    from sunity_shared.analysis import compare_render as cr

    EV.mkdir(exist_ok=True)
    meta_path = EV / "polly_synthesis.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {
        "entries": {},
        "note": "Seoyeon/neural = 운영 _synthesize_coach_audio_items env "
                "기본값 미러. Polly = TTS 비-LLM 실호출 (캡션 텍스트만 송신 — "
                "PII/시크릿 0). Gemini/Cerebras 호출 0.",
    }
    polly = None
    for name, text, dst in (
            ("discover_left_elbow", DISCOVER_TEXT_ELBOW,
             JOBS["pdshape"]["mp3Ev"]),
            ("discover_left_shoulder", DISCOVER_TEXT_SHOULDER,
             JOBS["powerspin"]["mp3Ev"])):
        if dst.exists() and dst.stat().st_size > 0:
            print(f"synthesize {name}: skip (멱등 — 기존 mp3 유지 "
                  f"{dst.stat().st_size} bytes, md5={_md5_file(dst)})")
            continue
        if polly is None:
            polly = _aws_session().client("polly", region_name="ap-northeast-2")
        resp = polly.synthesize_speech(
            Text=text, VoiceId="Seoyeon", Engine="neural",
            LanguageCode="ko-KR", OutputFormat="mp3")
        audio = resp["AudioStream"].read()
        assert audio, f"Polly AudioStream 비어 있음: {name}"
        dst.write_bytes(audio)
        dur = cr.mp3_duration_s(dst)  # ffmpeg(imageio-ffmpeg 동봉) 실측
        meta["entries"][name] = {
            "voiceId": "Seoyeon", "engine": "neural",
            "languageCode": "ko-KR", "outputFormat": "mp3",
            "text": text, "mp3Md5": _md5_file(dst), "mp3Bytes": len(audio),
            "durationS": round(dur, 3),
            "freezeSExpected": round(dur + 0.4, 3),  # 운영 규칙 dur+FREEZE_TAIL_S
            "synthesizedAt": _now(),
        }
        print(f"synthesize {name}: OK {len(audio)} bytes dur={dur:.3f}s "
              f"md5={_md5_file(dst)}")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1))


# ── fetch ────────────────────────────────────────────────────────────────────

def fetch(motion: str) -> None:
    job = JOBS[motion]
    p = _paths(motion)
    p["sp"].mkdir(parents=True, exist_ok=True)
    p["out"].mkdir(parents=True, exist_ok=True)
    obs: dict = {}

    if not p["doc"].exists():
        fa = _fa()
        doc = _live_doc(fa, job)
        p["doc"].write_text(json.dumps({"result": doc["result"]}))
        print(f"fetched live doc {job['aid']}")
    res = json.loads(p["doc"].read_text())["result"]

    # rid 해석 (live doc suffix 정확 1건 — 아니면 STOP)
    rid = _resolve_rid(motion, job, res)
    obs["ridResolved"] = rid
    recs = (res.get("deductionBreakdown") or {}).get("records") or []
    if motion == "pdshape":
        # ehz 시트 §3-1 sanity: 그 record = 최대 감점 record (-15.3)
        pts = {str(r.get("recordId", "")).split(":")[0]: r.get("points")
               for r in recs}
        target_pts = pts.get(rid)
        numeric = {k: v for k, v in pts.items()
                   if isinstance(v, (int, float))}
        if not isinstance(target_pts, (int, float)) or (
                numeric and target_pts != min(numeric.values())):
            _stop(motion, job, "fetch",
                  f"rid {rid} 가 최대 감점 record 아님 (ehz §3-1 sanity FAIL)",
                  {"points": pts})
        obs["ridPoints"] = target_pts
        obs["ridPointsMatchesEhz"] = abs(float(target_pts) + 15.3) <= 0.05

    # 사전 상태 assert
    s3 = _s3_client()
    from sunity_shared import s3keys

    canonical_mp4 = s3keys.build_rendered_compare_key(job["uid"], job["aid"])
    rc = res.get("renderedCompare")
    disc = res.get("discovery")
    if job["expectRenderedCompare"]:
        fz = (rc or {}).get("freezes") or []
        rc_ok = (
            isinstance(rc, dict) and rc.get("status") == "done"
            and rc.get("key") == canonical_mp4
            and len(fz) == len(PDSHAPE_EXPECTED_FREEZES)
            and all(
                got.get("rid") == exp_rid
                and abs(float(got.get("outSec")) - exp_out) <= 0.011
                for got, (exp_rid, exp_out) in zip(fz, PDSHAPE_EXPECTED_FREEZES))
        )
        if not rc_ok:
            _stop(motion, job, "fetch",
                  "renderedCompare != di7 정본 (6 freezes/키/상태)",
                  {"renderedCompare": rc})
        items = _discovery_items(motion, job, res)  # knee 정본 대조 포함 (STOP)
        obs["preFreezes"] = fz
        obs["preDiscoveryItems"] = (disc or {}).get("items")
        # 현행 운영 mp4 GET + md5 — 불일치 = STOP (belle 승인은 이 바이트)
        cur_mp4 = p["sp"] / "current_compare_v1.mp4"
        if not cur_mp4.exists():
            s3.download_file(BUCKET, canonical_mp4, str(cur_mp4))
        cur_md5 = _md5_file(cur_mp4)
        obs["currentMp4Md5"] = cur_md5
        if cur_md5 != PDSHAPE_MP4_MD5:
            _stop(motion, job, "fetch",
                  f"현행 운영 mp4 md5 {cur_md5} != {PDSHAPE_MP4_MD5}",
                  obs)
    else:
        if rc is not None:
            _stop(motion, job, "fetch",
                  "renderedCompare 존재 — 부재 전제 위반 (예상 밖 상태)",
                  {"renderedCompare": rc})
        if disc is not None:
            _stop(motion, job, "fetch",
                  "discovery 존재 — 부재 전제 위반", {"discovery": disc})
        items = _discovery_items(motion, job, res)
    obs["discoveryPayloadPlanned"] = items

    # 영상 S3 GET (user = doc myVideoKey / ref = 고정 키)
    user_key = str(res.get("myVideoKey") or "")
    assert user_key, "doc myVideoKey 부재"
    for which, key, dst in (("user", user_key, p["user"]),
                            ("ref", job["refVideoKey"], p["ref"])):
        if not dst.exists():
            s3.download_file(BUCKET, key, str(dst))
            print(f"fetched {which} video {dst.stat().st_size} bytes <- {key}")
    obs["videoKeys"] = {"user": user_key, "ref": job["refVideoKey"]}

    # align 재구성 — P35 트랙 replay (chd fetch 패턴 그대로, GPU 0)
    if not p["align"].exists():
        import numpy as np

        from sunity_shared.analysis import compare_align

        p35 = json.loads(
            (P35_DATA / job["p35Dir"] / "align.json").read_text())
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

        align_work = p["sp"] / "align_work"
        align_work.mkdir(parents=True, exist_ok=True)
        align = compare_align.build_align(
            p["user"], p["ref"], recs, align_work, infer_fn=infer_fn)
        p["align"].write_text(json.dumps(align))
    align = json.loads(p["align"].read_text())
    exp_u, exp_r = job["alignFrames"]
    if not (int(align["userFrames"]) == exp_u
            and int(align["refFrames"]) == exp_r):
        _stop(motion, job, "fetch",
              f"align 프레임 수 {align['userFrames']}/{align['refFrames']} "
              f"!= {exp_u}/{exp_r} — 영상 정체성 FAIL", obs)
    obs["alignFrames"] = [int(align["userFrames"]), int(align["refFrames"])]

    # coach mp3 GET (coachAudio items 키 그대로 — chd 패턴)
    p["audio"].mkdir(parents=True, exist_ok=True)
    ca_items = (res.get("coachAudio") or {}).get("items") or []
    for it in ca_items:
        crid = str(it.get("recordId", "")).split(":")[0]
        key = it.get("key")
        if not crid or not key:
            continue
        mp3 = p["audio"] / f"{crid}.mp3"
        if not mp3.exists():
            s3.download_file(BUCKET, key, str(mp3))
            print(f"fetched mp3 {crid} <- {key}")
    have = sorted(q.stem for q in p["audio"].glob("r*.mp3"))
    if len(have) != job["coachN"]:
        _stop(motion, job, "fetch",
              f"coach mp3 {len(have)}건 != {job['coachN']}건", {"have": have})
    obs["coachMp3"] = have

    # 기존 discover mp3 (pdshape knee) — S3 GET + chd repo 고정본 md5 대조
    if motion == "pdshape":
        knee_key = s3keys.build_discover_audio_key(
            job["uid"], job["aid"], "r04", "left_knee")
        knee_local = p["sp"] / "discover_knee_s3.mp3"
        if not knee_local.exists():
            s3.download_file(BUCKET, knee_key, str(knee_local))
        knee_md5 = _md5_file(knee_local)
        if knee_md5 != KNEE_MP3_MD5 or knee_md5 != _md5_file(CHD_KNEE_MP3):
            _stop(motion, job, "fetch",
                  f"knee discover mp3 md5 {knee_md5} != chd 고정본 "
                  f"{KNEE_MP3_MD5}", obs)
        obs["kneeMp3Md5"] = knee_md5
        shutil.copyfile(
            knee_local, p["audio"] / knee_key.rsplit("/", 1)[-1])

    # 신규 discover mp3 (이 사이클 합성 고정본) — audio_dir 조인
    if not job["mp3Ev"].exists():
        _stop(motion, job, "fetch",
              f"합성 mp3 부재: {job['mp3Ev']} — --synthesize 선행 필요", obs)
    new_key = items[-1]["mp3Key"]
    dst = p["audio"] / new_key.rsplit("/", 1)[-1]
    if not dst.exists() or _md5_file(dst) != _md5_file(job["mp3Ev"]):
        shutil.copyfile(job["mp3Ev"], dst)
    obs["newMp3Md5"] = _md5_file(job["mp3Ev"])
    obs["newMp3Key"] = new_key

    _merge_verdict(p["verdict"], "fetch", {**obs, "at": _now()}, job)
    print(f"fetch OK — rid={rid} align={obs['alignFrames']} "
          f"coach={len(have)} preState=PASS")


# ── 렌더 1회 + 관측 (di7 _render_once 미러 — monkeypatch 0) ─────────────────

def _report_core(report: dict) -> dict:
    return {k: v for k, v in report.items() if k != "out"}


def _render_once(motion: str, tag: str, doc: dict,
                 audio_dir: pathlib.Path | None = None) -> dict:
    from sunity_shared.analysis import compare_render as cr

    p = _paths(motion)
    align = json.loads(p["align"].read_text())
    out = p["out"] / f"{tag}.mp4"
    buf = io.StringIO()

    class _Tee(io.TextIOBase):
        def write(self, s):  # noqa: D102
            buf.write(s)
            sys.__stdout__.write(s)
            return len(s)

    with contextlib.redirect_stdout(_Tee()):
        report = cr.render(
            doc, p["user"], p["ref"], audio_dir or p["audio"],
            p["render"], out, align_json=align)
    compose = p["render"] / f"compose{int(cr.FPS_OUT)}_{cr.PANEL_H}"
    frames_md5 = [_md5_file(q) for q in sorted(compose.glob("*.jpg"))]
    return {
        "tag": tag, "out": str(out), "mp4Md5": _md5_file(out),
        "report": report, "framesMd5": frames_md5, "stdout": buf.getvalue(),
    }


def _verify_stock(motion: str, mp4: pathlib.Path, report: dict, doc: dict,
                  rig_dir: pathlib.Path) -> tuple[bool, list[str]]:
    """운영 compare_verify.verify 무수정 — 면제 delta 0."""
    from sunity_shared.analysis import compare_verify as cv

    p = _paths(motion)
    align = json.loads(p["align"].read_text())
    rig_dir.mkdir(parents=True, exist_ok=True)
    return cv.verify(mp4, report, rig_dir, align=align, doc=doc)


# ── baseline ─────────────────────────────────────────────────────────────────

def baseline(motion: str) -> None:
    job = JOBS[motion]
    p = _paths(motion)
    doc = json.loads(p["doc"].read_text())
    n_disc = len(((doc["result"].get("discovery") or {}).get("items")) or [])
    assert n_disc == job["expectDiscoverBaseline"], (
        f"베이스라인 doc discovery {n_disc}건 != "
        f"{job['expectDiscoverBaseline']}건")

    r1 = _render_once(motion, "baseline_run1", doc)
    frames1 = r1["framesMd5"]
    r2 = _render_once(motion, "baseline_run2", doc)
    det = (r1["mp4Md5"] == r2["mp4Md5"]
           and frames1 == r2["framesMd5"]
           and _report_core(r1["report"]) == _report_core(r2["report"]))

    chain_same = None
    if job["chainRef"] is not None:
        chd_frames = json.loads(job["chainRef"].read_text())
        chain_same = frames1 == chd_frames
        if not chain_same:
            # 환경 drift 의심 — 프로덕션 쓰기 진입 금지 (STOP 은 check 가 아니라
            # 여기서 즉시: 이후 스테이지가 이 사슬 위에 선다).
            _merge_verdict(p["verdict"], "baseline", {
                "chainSameChd": False, "composeFrames": len(frames1),
                "determinism": det, "at": _now(),
            }, job)
            _stop(motion, job, "baseline",
                  "베이스라인 사슬 != chd frames_md5_injected — 환경 drift 의심",
                  {"composeFrames": len(frames1),
                   "chdFrames": len(chd_frames)})

    ok, lines = _verify_stock(
        motion, pathlib.Path(r1["out"]), r1["report"], doc,
        p["out"] / "rig_base")
    for ln in lines:
        print(ln)

    freezes = r1["report"]["freezes"]
    disc_n = sum(1 for f in freezes if f["pairSrc"] == "discover")
    extra: dict = {}
    if motion == "pdshape":
        seq_ok = (
            len(freezes) == 6
            and all(
                f["rid"] == exp_rid.split(":")[0]
                and abs(float(f["voiceStartOutS"]) - exp_out) <= 0.011
                for f, (exp_rid, exp_out)
                in zip(freezes, PDSHAPE_EXPECTED_FREEZES))
        )
        extra["freezesMatchDi7"] = seq_ok
    else:
        # powerspin — 관측 기록: r01(split_angle) 은 atVideoSec 부재 + align
        # pairs 밖이라 구조적으로 freeze 미성립 (plan 추정 3건과 다른 live 실측
        # — deviation 으로 SUMMARY 박제). H1 회계는 eligible 집합으로 정합.
        align = json.loads(p["align"].read_text())
        recs = (doc["result"].get("deductionBreakdown") or {}).get(
            "records") or []
        eligible = sorted(
            str(r.get("recordId", "")).split(":")[0] for r in recs
            if str(r.get("recordId", "")).split(":")[0] in (
                align.get("pairs") or {})
            or r.get("atVideoSec") is not None)
        got = sorted(f["rid"] for f in freezes)
        extra["eligibleRecordRids"] = eligible
        extra["freezeRids"] = got
        extra["recordFreezesMatchEligible"] = got == eligible
        structural = [
            str(r.get("recordId", ""))
            for r in recs
            if str(r.get("recordId", "")).split(":")[0] not in (
                align.get("pairs") or {})
            and r.get("atVideoSec") is None]
        extra["structurallySilentRecords"] = structural
        extra["planDeviationNote"] = (
            "plan 은 record freezes 3건(r00/r01/r02)을 예상했으나 live 실측 = "
            f"{got} — r01:split_angle 은 atVideoSec 부재 + align pairs 밖 "
            "(select_pairs fail-closed 스킵, kipup 선례와 동형). 관측 그대로 "
            "기록하고 live 값 사용.")
        if not extra["recordFreezesMatchEligible"]:
            _stop(motion, job, "baseline",
                  "freeze rid 집합 != eligible 집합", extra)
        rid = _resolve_rid(motion, job, doc["result"])
        if rid not in got:
            _stop(motion, job, "baseline",
                  f"채택 대상 record {rid} 의 freeze 미성립", extra)

    _merge_verdict(p["verdict"], "baseline", {
        "mp4Md5": r1["mp4Md5"],
        "composeFrames": len(frames1),
        "chainSameChd": chain_same,
        "chainRef": (str(job["chainRef"]) if job["chainRef"] else
                     "없음 — 신규 렌더 (자기 결정론 + 무수정 리그가 게이트, "
                     "plan 명기)"),
        "determinism": det,
        "rigStockAllPass": ok,
        "rigLines": lines,
        "freezeCount": len(freezes),
        "discoverFreezeCount": disc_n,
        **extra,
        "outFile": r1["out"],
        "at": _now(),
    }, job)
    (p["out"] / "wire_baseline_report.json").write_text(
        json.dumps(r1["report"]))
    (p["out"] / "frames_md5_baseline.json").write_text(json.dumps(frames1))
    if motion == "powerspin":
        (EV / "powerspin_frames_md5_baseline.json").write_text(
            json.dumps(frames1))
    print(f"baseline: chainSameChd={chain_same} det={det} "
          f"rig={'PASS' if ok else 'FAIL'} freezes={len(freezes)} "
          f"discover={disc_n}")


# ── inject ───────────────────────────────────────────────────────────────────

def _extract_frame_idx(motion: str, mp4: pathlib.Path, idx: int,
                       dst: pathlib.Path) -> None:
    import imageio_ffmpeg

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ff, "-y", "-loglevel", "error", "-i", str(mp4),
         "-vf", f"select=eq(n\\,{idx})", "-vsync", "0",
         "-frames:v", "1", str(dst)], check=True)


def inject(motion: str) -> None:
    job = JOBS[motion]
    p = _paths(motion)
    fa = _fa()

    doc_base = json.loads(p["doc"].read_text())
    items = _discovery_items(motion, job, doc_base["result"])
    fa._validate_discovery({"items": items})  # noqa: SLF001 — 사전 통과
    doc = json.loads(p["doc"].read_text())
    doc["result"]["discovery"] = {"items": items}

    r1 = _render_once(motion, "inject_run1", doc)
    frames1 = r1["framesMd5"]
    r2 = _render_once(motion, "inject_run2", doc)
    det = (r1["mp4Md5"] == r2["mp4Md5"]
           and frames1 == r2["framesMd5"]
           and _report_core(r1["report"]) == _report_core(r2["report"]))
    report = r1["report"]
    mp4 = pathlib.Path(r1["out"])

    discover_lines = [
        ln for ln in r1["stdout"].splitlines()
        if ln.startswith("[discover] rid=")]
    n_items = len(items)

    base_report = json.loads(
        (p["out"] / "wire_baseline_report.json").read_text())
    new_rid = items[-1]["rid"]

    def _is_new(fz: dict) -> bool:
        return (fz.get("pairSrc") == "discover"
                and fz.get("joint") == job["joint"]
                and abs(float(fz.get("userSec")) - job["uSec"]) < 1e-6)

    inj_new = [f for f in report["freezes"] if _is_new(f)]
    inj_old = [f for f in report["freezes"] if not _is_new(f)]
    keys_id = ("rid", "joint", "userSec", "refSec", "pairSrc", "text",
               "freezeS", "markers", "legsViz", "poleViz", "bodyViz")
    old_preserved = (
        len(inj_old) == len(base_report["freezes"])
        and all(
            {k: a.get(k) for k in keys_id} == {k: b.get(k) for k in keys_id}
            for a, b in zip(inj_old, base_report["freezes"]))
    )
    out_shifts = [
        {"rid": b["rid"], "pairSrc": b["pairSrc"],
         "baseOutSec": b["voiceStartOutS"], "injectOutSec": a["voiceStartOutS"],
         "shiftS": round(a["voiceStartOutS"] - b["voiceStartOutS"], 3)}
        for a, b in zip(inj_old, base_report["freezes"])
    ]
    new_exact = (
        len(inj_new) == 1
        and inj_new[0]["rid"] == new_rid
        and inj_new[0]["joint"] == job["joint"]
        and abs(inj_new[0]["refSec"] - job["rSec"]) < 0.005
        and inj_new[0]["text"] == job["text"]
    )

    ok, lines = _verify_stock(
        motion, mp4, report, doc, p["out"] / "rig_inject")
    for ln in lines:
        print(ln)

    # 음성 게이트 — 신규 항목 +0.5s 비틀기 → H2 discover FAIL 정확 발생 후 원복
    # (verify 는 mp4+report 입력 — 재렌더 불필요. 기존 항목 무접촉).
    pert_items = [dict(it) for it in items]
    pert_items[-1]["userSec"] = float(pert_items[-1]["userSec"]) + 0.5
    doc_pert = json.loads(p["doc"].read_text())
    doc_pert["result"]["discovery"] = {"items": pert_items}
    ok_p, lines_p = _verify_stock(
        motion, mp4, report, doc_pert, p["out"] / "rig_pert")
    pert_fails = [ln for ln in lines_p if ln.strip().startswith("[FAIL]")]
    h2_fail = [ln for ln in pert_fails
               if f"H2 순간 {new_rid}[discover]" in ln]
    perturb_h2_fail = (not ok_p) and len(h2_fail) == 1

    # 신규 정지 스틸 (frames-before-numbers — 실행자 육안 확인 대상)
    stills_dir = EV / "stills"
    stills_dir.mkdir(parents=True, exist_ok=True)
    fz = inj_new[0]
    mid_idx = round((fz["voiceStartOutS"] + fz["freezeS"] / 2) * 30)
    still_path = stills_dir / f"{motion}_discover_freeze_{job['joint']}.png"
    _extract_frame_idx(motion, mp4, mid_idx, still_path)

    _merge_verdict(p["verdict"], "inject", {
        "discoveryPayload": items,
        "validatorPreflight": "firestore_admin._validate_discovery PASS",
        "mp4Md5": r1["mp4Md5"],
        "composeFrames": len(frames1),
        "determinism": det,
        "freezeCount": len(report["freezes"]),
        "freezeCountExpected": len(base_report["freezes"]) + 1,
        "oldFreezesPreserved": old_preserved,
        "oldFreezeOutSecShifts": out_shifts,
        "newFreezeExact": new_exact,
        "newFreeze": {k: fz.get(k) for k in
                      ("rid", "joint", "userSec", "refSec", "pairSrc",
                       "text", "freezeS", "voiceStartOutS")},
        "rigStockAllPass": ok,
        "rigStockNote": "compare_verify.verify 무수정 — 면제 monkeypatch 0",
        "rigLines": lines,
        "discoverLogSeen": len(discover_lines) == n_items,
        "discoverLogLines": discover_lines,
        "perturbH2Fail": perturb_h2_fail,
        "perturbFailLines": pert_fails,
        "stillFile": str(still_path),
        "stillFrameIdx": mid_idx,
        "outFile": r1["out"],
        "at": _now(),
    }, job)
    (p["out"] / "wire_inject_report.json").write_text(json.dumps(report))
    p["frames_inject"].write_text(json.dumps(frames1))
    print(f"inject: det={det} freezes={len(report['freezes'])} "
          f"oldPreserved={old_preserved} newExact={new_exact} "
          f"rig={'PASS' if ok else 'FAIL'} "
          f"discoverLog={len(discover_lines)}/{n_items} "
          f"perturbH2Fail={perturb_h2_fail}")


# ── check-wire ───────────────────────────────────────────────────────────────

def check_wire(motion: str) -> int:
    job = JOBS[motion]
    p = _paths(motion)
    fails: list[str] = []
    if not p["verdict"].exists():
        print(f"CHECK-WIRE FAIL: {p['verdict'].name} 부재")
        return 1
    v = json.loads(p["verdict"].read_text())
    for k in list(v):
        if k.startswith("STOP_"):
            fails.append(f"STOP 기록 존재: {k} — {v[k].get('reason')}")
    f = v.get("fetch") or {}
    if not f.get("ridResolved"):
        fails.append("fetch rid 미해석")
    if motion == "pdshape" and f.get("currentMp4Md5") != PDSHAPE_MP4_MD5:
        fails.append("현행 운영 mp4 md5 확인 부재/불일치")
    b = v.get("baseline") or {}
    if job["chainRef"] is not None and not b.get("chainSameChd"):
        fails.append("베이스라인 사슬 != chd frames_md5_injected")
    if not b.get("determinism"):
        fails.append("베이스라인 결정론 실패")
    if not b.get("rigStockAllPass"):
        fails.append("베이스라인 무수정 verify ALL PASS 아님")
    if b.get("discoverFreezeCount") != job["expectDiscoverBaseline"]:
        fails.append(
            f"베이스라인 discover freeze {b.get('discoverFreezeCount')}건 != "
            f"{job['expectDiscoverBaseline']}건")
    if motion == "pdshape" and not b.get("freezesMatchDi7"):
        fails.append("베이스라인 freeze 6건 != di7 정본")
    if motion == "powerspin" and not b.get("recordFreezesMatchEligible"):
        fails.append("record freeze 집합 != eligible 집합")
    i = v.get("inject") or {}
    if not i.get("determinism"):
        fails.append("주입 결정론 실패")
    if i.get("freezeCount") != i.get("freezeCountExpected"):
        fails.append(f"주입 freeze {i.get('freezeCount')}건 != "
                     f"{i.get('freezeCountExpected')}건")
    if not i.get("oldFreezesPreserved"):
        fails.append("기존 freeze 정체성 보존 실패")
    if not i.get("newFreezeExact"):
        fails.append("신규 freeze 정확성 실패")
    if not i.get("rigStockAllPass"):
        fails.append("주입 무수정 verify ALL PASS 아님")
    if not i.get("discoverLogSeen"):
        fails.append("[discover] 실행 로그 건수 불일치")
    if not i.get("perturbH2Fail"):
        fails.append("음성 게이트(+0.5s 비틀기 H2 discover FAIL) 미성립")
    still = i.get("stillFile")
    if not still or not pathlib.Path(still).exists():
        fails.append("신규 정지 스틸 부재")
    if fails:
        print(f"CHECK-WIRE FAIL ({motion}):")
        for x in fails:
            print(f"  - {x}")
        return 1
    print(f"CHECK-WIRE PASS ({motion}): 사전 assert + 베이스라인"
          f"{' 사슬==chd' if job['chainRef'] else ' 자기 결정론'} + 기존 정지 "
          "보존 + 신규 정지 정확 + 무수정 verify ALL PASS + [discover] 로그 + "
          "음성 게이트 + 스틸")
    return 0


# ── apply (belle 08-21 승인 — D-01. 전 쓰기 로그 박제) ───────────────────────

def apply(motion: str) -> None:
    import botocore.exceptions

    from sunity_shared import s3keys

    job = JOBS[motion]
    p = _paths(motion)
    fa = _fa()
    s3 = _s3_client()
    writes: list[dict] = []

    # (0) check-wire 게이트 선행 확인 — FAIL 상태에서 쓰기 진입 금지.
    if check_wire(motion) != 0:
        raise SystemExit(f"STOP[{motion}/apply]: check-wire FAIL — 쓰기 금지")

    canonical_mp4 = s3keys.build_rendered_compare_key(job["uid"], job["aid"])

    # (1) 사전 assert 재실행 — live doc 재fetch (fetch 캐시 아님).
    doc_pre = _live_doc(fa, job)
    res_pre = doc_pre["result"]
    rc_pre = res_pre.get("renderedCompare")
    if job["expectRenderedCompare"]:
        fz_pre = (rc_pre or {}).get("freezes") or []
        ok_pre = (
            isinstance(rc_pre, dict) and rc_pre.get("key") == canonical_mp4
            and len(fz_pre) == len(PDSHAPE_EXPECTED_FREEZES)
            and all(
                got.get("rid") == exp_rid
                and abs(float(got.get("outSec")) - exp_out) <= 0.011
                for got, (exp_rid, exp_out)
                in zip(fz_pre, PDSHAPE_EXPECTED_FREEZES))
        )
        if not ok_pre:
            _stop(motion, job, "apply",
                  "직전 재확인: renderedCompare != di7 정본",
                  {"renderedCompare": rc_pre})
        # 현행 S3 mp4 md5 재확인 (덮어쓸 바이트가 승인본인지)
        got = s3.get_object(Bucket=BUCKET, Key=canonical_mp4)["Body"].read()
        cur_md5 = hashlib.md5(got).hexdigest()
        if cur_md5 != PDSHAPE_MP4_MD5:
            _stop(motion, job, "apply",
                  f"직전 재확인: 현행 S3 mp4 md5 {cur_md5} != "
                  f"{PDSHAPE_MP4_MD5}", {})
    else:
        if rc_pre is not None or res_pre.get("discovery") is not None:
            _stop(motion, job, "apply",
                  "직전 재확인: renderedCompare/discovery 존재 — 부재 전제 위반",
                  {"renderedCompare": rc_pre,
                   "discovery": res_pre.get("discovery")})
        # 신규 키 — 덮어쓸 기존 객체 없음 확인 (있으면 STOP)
        try:
            s3.head_object(Bucket=BUCKET, Key=canonical_mp4)
            _stop(motion, job, "apply",
                  f"canonical mp4 키에 기존 객체 존재: {canonical_mp4}", {})
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] not in ("404", "NoSuchKey", "NotFound"):
                raise

    items = _discovery_items(motion, job, res_pre)  # live 기준 병합 (재해석)

    # (2) inject 렌더 mp4 → canonical 키
    src_mp4 = p["out"] / "inject_run1.mp4"
    src_md5 = _md5_file(src_mp4)
    inj_v = json.loads(p["verdict"].read_text())["inject"]
    assert inj_v["mp4Md5"] == src_md5, (
        f"inject mp4 md5 {src_md5} != verdict {inj_v['mp4Md5']} — 산출물 drift")
    with open(src_mp4, "rb") as fh:
        s3.put_object(Bucket=BUCKET, Key=canonical_mp4, Body=fh,
                      ContentType="video/mp4")
    got = s3.get_object(Bucket=BUCKET, Key=canonical_mp4)["Body"].read()
    got_md5 = hashlib.md5(got).hexdigest()
    assert got_md5 == src_md5, f"업로드 후 S3 md5 재확인 실패: {got_md5}"
    writes.append({
        "op": "s3.put_object", "key": canonical_mp4,
        "contentType": "video/mp4", "bytes": src_mp4.stat().st_size,
        "sourcePath": str(src_mp4), "sourceMd5": src_md5,
        "s3RoundtripMd5": got_md5, "at": _now(),
        "note": ("기존 승인본 md5 재확인 후 같은 키 덮어쓰기"
                 if job["expectRenderedCompare"] else
                 "신규 키 (기존 객체 부재 확인 후 put)"),
    })
    print(f"apply(1): mp4 -> s3://{BUCKET}/{canonical_mp4} md5={got_md5}")

    # (3) 신규 discover mp3 → canonical 키
    new_item = items[-1]
    mp3_md5 = _md5_file(job["mp3Ev"])
    with open(job["mp3Ev"], "rb") as fh:
        s3.put_object(Bucket=BUCKET, Key=new_item["mp3Key"], Body=fh,
                      ContentType="audio/mpeg")
    got = s3.get_object(Bucket=BUCKET, Key=new_item["mp3Key"])["Body"].read()
    got_md5 = hashlib.md5(got).hexdigest()
    assert got_md5 == mp3_md5, f"mp3 S3 재확인 실패: {got_md5}"
    writes.append({
        "op": "s3.put_object", "key": new_item["mp3Key"],
        "contentType": "audio/mpeg", "bytes": job["mp3Ev"].stat().st_size,
        "sourcePath": str(job["mp3Ev"]), "sourceMd5": mp3_md5,
        "s3RoundtripMd5": got_md5, "at": _now(),
        "note": "이 사이클 Polly 합성 고정본 (repo evidence) — "
                "s3keys.build_discover_audio_key canonical 키",
    })
    print(f"apply(2): mp3 -> s3://{BUCKET}/{new_item['mp3Key']} md5={got_md5}")

    # (4) doc discovery 기입 — 기존 항목 병합 payload (단일 소스)
    fa.update_analysis_discovery(job["uid"], job["aid"], items)
    writes.append({
        "op": "firestore.update_analysis_discovery",
        "args": {"uid": job["uid"], "analysisId": job["aid"], "items": items},
        "fieldPath": "result.discovery",
        "preItems": ((res_pre.get("discovery") or {}).get("items")),
        "at": _now(),
    })
    print(f"apply(3): doc result.discovery {len(items)} items")

    # (5) renderedCompare 갱신 — inject report freezes (discover = ':discover' 틱)
    report = json.loads((p["out"] / "wire_inject_report.json").read_text())
    freezes = []
    for fz in report["freezes"]:
        rid = fz["rid"]
        if fz.get("pairSrc") == "discover":
            rid = f"{rid}:discover"
        freezes.append({"rid": rid, "outSec": fz["voiceStartOutS"]})
    n_expected = (7 if motion == "pdshape"
                  else len(report["freezes"]))
    assert len(freezes) == n_expected, f"freezes {len(freezes)} != {n_expected}"
    tick = f"{new_item['rid']}:discover"
    assert any(f["rid"] == tick for f in freezes), f"{tick} 틱 부재: {freezes}"
    fa.update_analysis_rendered_compare(
        job["uid"], job["aid"], canonical_mp4, status="done", freezes=freezes)
    writes.append({
        "op": "firestore.update_analysis_rendered_compare",
        "args": {"uid": job["uid"], "analysisId": job["aid"],
                 "key": canonical_mp4, "status": "done", "freezes": freezes},
        "fieldPath": "result.renderedCompare",
        "preFreezes": ((rc_pre or {}).get("freezes")),
        "at": _now(),
    })
    print(f"apply(4): doc result.renderedCompare freezes={freezes}")

    p["prodlog"].write_text(json.dumps({
        "status": "APPLIED",
        "uid": job["uid"], "aid": job["aid"], "bucket": BUCKET,
        "awsProfile": os.environ.get("AWS_PROFILE", "sunity-motion"),
        "writes": writes,
        "llm": {"geminiCalls": 0, "cerebrasCalls": 0,
                "pollyCallsThisStage": 0,
                "note": "apply = 렌더 산출 업로드·doc 쓰기만. Polly TTS 는 "
                        "--synthesize 에서 동작당 1회 (비-LLM). LLM 추론 호출 0."},
        "at": _now(),
    }, ensure_ascii=False, indent=1))
    print(f"apply: {p['prodlog'].name} 박제 완료 (S3 2건 + doc 2필드)")


# ── live (반영 검증 — 영속화 필드 → 렌더 구동 왕복 증명) ─────────────────────

def live(motion: str) -> None:
    from sunity_shared import s3keys

    job = JOBS[motion]
    p = _paths(motion)
    fa = _fa()
    s3 = _s3_client()

    doc_live = _live_doc(fa, job)
    res = doc_live["result"]

    # (a) 재fetch doc == 반영 payload
    prodlog = json.loads(p["prodlog"].read_text())
    w_disc = next(w for w in prodlog["writes"]
                  if w["op"] == "firestore.update_analysis_discovery")
    w_rc = next(w for w in prodlog["writes"]
                if w["op"] == "firestore.update_analysis_rendered_compare")
    items = w_disc["args"]["items"]
    canonical_mp4 = s3keys.build_rendered_compare_key(job["uid"], job["aid"])
    disc_match = res.get("discovery") == {"items": items}
    rc_match = res.get("renderedCompare") == {
        "status": "done", "key": canonical_mp4,
        "freezes": w_rc["args"]["freezes"]}
    assert disc_match, (
        f"live doc discovery != 반영 payload: {res.get('discovery')}")
    assert rc_match, (
        f"live doc renderedCompare != 반영 payload: "
        f"{res.get('renderedCompare')}")

    # (b) discover mp3 전건 = S3 방금 쓴 키 GET (키 왕복 증명)
    if p["audio_live"].exists():
        shutil.rmtree(p["audio_live"])
    p["audio_live"].mkdir(parents=True)
    for q in p["audio"].glob("r*.mp3"):
        shutil.copyfile(q, p["audio_live"] / q.name)
    fixed = {job["joint"]: job["mp3Ev"], "left_knee": CHD_KNEE_MP3}
    mp3_obs = {}
    for it in items:
        basename = it["mp3Key"].rsplit("/", 1)[-1]
        s3.download_file(BUCKET, it["mp3Key"], str(p["audio_live"] / basename))
        got_md5 = _md5_file(p["audio_live"] / basename)
        ref = fixed.get(it["joint"])
        assert ref is not None and got_md5 == _md5_file(ref), (
            f"S3 왕복 mp3 md5 상이: {it['mp3Key']} {got_md5}")
        mp3_obs[it["mp3Key"]] = got_md5

    # (c) live doc 렌더 — audio_dir = S3 왕복 디렉터리
    r = _render_once(motion, "live_render", {"result": res},
                     audio_dir=p["audio_live"])
    discover_lines = [
        ln for ln in r["stdout"].splitlines()
        if ln.startswith("[discover] rid=")]
    inj_frames = json.loads(p["frames_inject"].read_text())
    chain_same = r["framesMd5"] == inj_frames

    ok, lines = _verify_stock(
        motion, pathlib.Path(r["out"]), r["report"], {"result": res},
        p["out"] / "rig_live")
    for ln in lines:
        print(ln)

    p["livev"].write_text(json.dumps({
        "meta": {"uid": job["uid"], "aid": job["aid"], "generated": _now(),
                 "docSource": "Firestore 재fetch (로컬 캐시 미사용)",
                 "mp3Source": {k: f"s3 GET md5={v}"
                               for k, v in mp3_obs.items()}},
        "liveDocFieldsMatch": bool(disc_match and rc_match),
        "injectedChainSame": chain_same,
        "chainRef": f"{p['frames_inject'].name} (repo 고정 — 이 사이클 inject)",
        "rigStockAllPass": ok,
        "rigLines": lines,
        "discoverLogSeen": len(discover_lines) == len(items),
        "discoverLogLines": discover_lines,
        "mp4Md5": r["mp4Md5"],
        "outFile": r["out"],
    }, ensure_ascii=False, indent=1))
    print(f"live: docMatch={disc_match and rc_match} chainSame={chain_same} "
          f"rig={'PASS' if ok else 'FAIL'} "
          f"discoverLog={len(discover_lines)}/{len(items)}")


# ── check-apply ──────────────────────────────────────────────────────────────

def check_apply(motion: str) -> int:
    job = JOBS[motion]
    p = _paths(motion)
    fails: list[str] = []
    if not p["prodlog"].exists():
        print(f"CHECK-APPLY FAIL: {p['prodlog'].name} 부재")
        return 1
    pl = json.loads(p["prodlog"].read_text())
    if pl.get("status") != "APPLIED":
        fails.append(f"production_log status != APPLIED: {pl.get('status')}")
    ops = [w.get("op") for w in pl.get("writes", [])]
    if ops != ["s3.put_object", "s3.put_object",
               "firestore.update_analysis_discovery",
               "firestore.update_analysis_rendered_compare"]:
        fails.append(f"쓰기 4건 정확 아님: {ops}")
    for w in pl.get("writes", []):
        if w.get("op") == "s3.put_object" and (
                w.get("sourceMd5") != w.get("s3RoundtripMd5")):
            fails.append(f"md5 왕복 불일치: {w.get('key')}")
    rc = [w for w in pl.get("writes", [])
          if w.get("op") == "firestore.update_analysis_rendered_compare"]
    fz = (rc[0]["args"].get("freezes") if rc else None) or []
    ticks = [f["rid"] for f in fz if f["rid"].endswith(":discover")]
    want_ticks = 2 if motion == "pdshape" else 1
    if len(ticks) != want_ticks:
        fails.append(f":discover 틱 {len(ticks)}건 != {want_ticks}건: {fz}")
    if motion == "pdshape" and (len(fz) != 7 or "r04:discover" not in ticks):
        fails.append(f"pdshape freezes 7건/r04:discover 보존 아님: {fz}")
    if not p["livev"].exists():
        fails.append(f"{p['livev'].name} 부재")
    else:
        v = json.loads(p["livev"].read_text())
        for k in ("liveDocFieldsMatch", "injectedChainSame",
                  "rigStockAllPass", "discoverLogSeen"):
            if not v.get(k):
                fails.append(f"live_verdict.{k} != true")
    if fails:
        print(f"CHECK-APPLY FAIL ({motion}):")
        for x in fails:
            print(f"  - {x}")
        return 1
    print(f"CHECK-APPLY PASS ({motion}): 쓰기 4건 md5 왕복 + :discover 틱 + "
          "live 재fetch 렌더 사슬 == inject + 무수정 verify ALL PASS)")
    return 0


def main() -> int:
    _ensure_venv()
    apr = argparse.ArgumentParser()
    apr.add_argument("--motion", choices=sorted(JOBS))
    apr.add_argument("--synthesize", action="store_true")
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
    if args.synthesize:
        synthesize()
        return 0
    needs_motion = (args.fetch or args.baseline or args.inject
                    or args.check_wire or args.apply or args.live
                    or args.check_apply)
    if needs_motion and not args.motion:
        apr.error("--motion 필요")
    m = args.motion
    if args.fetch:
        fetch(m)
    if args.baseline:
        fetch(m)
        baseline(m)
    if args.inject:
        fetch(m)
        inject(m)
    if args.check_wire:
        return check_wire(m)
    if args.apply:
        fetch(m)
        apply(m)
    if args.live:
        live(m)
    if args.check_apply:
        return check_apply(m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
