#!/usr/bin/env python3
"""영상 받는 도구 — 사람이 모아준 영상을 Phase 37 원장에 등록하고, 분석 기록을 잇는다.

왜 이게 리포에 있나 (quick-260923-swh)
──────────────────────────────────
2026-09-23 의 kip-up 비교는 손으로 했고, 어느 분석 doc 을 썼는지 기록이 없어 다음 세션이
대화 기록을 뒤져서야 doc id 를 복원했다. 그 과정에서 그 비교가 운영 계산이 아니었다는 것도
드러났다(quick-260923-smt). 영상이 들어올 때마다 **영상(내용 해시) → 분석 doc** 연결을
원장에 남기지 않으면 같은 일이 반복된다.

무엇을 하나
──────────
register  영상 + 메모 → 내용 해시 · S3 영구 사본 · 원장 기록
          clips.jsonl (영상 1편 = 1행) · subjects.jsonl (새 사람) · pairs.jsonl (정타/실수 짝)
analyze   등록된 영상을 앱과 같은 경로로 분석(e2e_app_path.py)하고 결과 doc 을
          analysis_runs.jsonl 에 잇는다. **Pod 이 떠 있어야 한다.** 직렬로만 돈다.
짝 비교는 여기 없다 — `measure_reference_axis.py --pairs` 가 한다(자를 두 개 만들지 않는다).

지켜야 할 것 (37-DATA-SPEC §1)
─────────────────────────────
- 조인 키 = video_hash(SHA256 내용 해시). 파일명·경로로 잇지 않는다.
- **사람 영상은 manifest.json 에 넣지 않는다.** 플라이휠이 manifest 의 s3_key 보유 행을
  증류 후보로 자동 선택한다(`gemini_teacher.eligible_for_distill`) — 동의 조건이 다른 영상이
  주 1회 자동으로 학습에 들어간다. 그래서 clips.jsonl 이 따로 있다.
- 점수 필드 없음. 사람 이름 없음 — 학생은 display_name 을 두지 않고, note 에도 이름을 쓰지 않는다.
  원본 파일명도 남기지 않는다(이름이 들어 있을 수 있다).
- S3 영구 사본은 `fixtures/intake/` 에 둔다. 앱 경로의 `uploads/` 는 30일 뒤 지워진다(수명 규칙).

사용
────
  # 메모를 한 줄씩 JSON 으로 옮긴 시트 (예시는 --help 아래 SHEET 절)
  backend/.venv/bin/python backend/scripts/intake_clips.py register --sheet sheet.jsonl --dry-run
  backend/.venv/bin/python backend/scripts/intake_clips.py register --sheet sheet.jsonl
  backend/.venv/bin/python backend/scripts/intake_clips.py analyze --pending
  backend/.venv/bin/python backend/scripts/intake_clips.py analyze --hash <video_hash>

SHEET (한 줄 = 영상 1편)
───────────────────────
  {"file": "/Users/Shared/sunity-intake/0924/a.mov", "motion": "kip-up",
   "subject_id": "sub_s01",
   "subject": {"role": "student", "consent": {"granted": true, "scope": "training", "at": "2026-09-24"}},
   "intent": "fault", "fault_intent": ["left_arm_underbent"], "note": "왼팔을 덜 굽혔다",
   "view": "side", "session": "2026-09-24-studio", "pair_key": "s01-kipup-1"}
  - subject 는 처음 보는 subject_id 일 때만 필요하다.
  - pair_key 가 같은 두 줄 = 같은 사람 · 같은 동작의 정타 1 + 실수 1 → pairs.jsonl.
  - 파일은 홈 디렉터리(git 저장소) 밖에 둘 것 — /Users/Shared/ 권장.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))

from sunity_shared.models import MAX_VIDEO_BYTES  # noqa: E402

DATA = REPO / "backend" / "training" / "data"
CLIPS = DATA / "clips.jsonl"
PAIRS = DATA / "pairs.jsonl"
SUBJECTS = DATA / "subjects.jsonl"
RUNS = DATA / "analysis_runs.jsonl"

BUCKET = "sunity-motion-pilot-videos"
INTAKE_PREFIX = "fixtures/intake/"
REGION = "ap-northeast-2"
_PROFILE = os.environ.get("SUNITY_AWS_PROFILE", "sunity-motion")
LAMBDA_FN = "sunity-motion-pilot-pipeline"
POD_DOWN_URL = "https://pod-down.invalid/analyze"  # pod_teardown.PLACEHOLDER 와 같은 값
E2E = REPO / "backend" / "scripts" / "e2e_app_path.py"
# 2026-09-22 사고: 900초 고정 타임아웃이 느린 Pod 에서 앞 분석을 안 기다리고 다음 것을
# 제출해 동시 분석 2건이 됐다(quick-260922-gnj). 넉넉히 기다리고, 넘기면 배치를 멈춘다.
E2E_TIMEOUT_S = 5400

# 통제 어휘 — 37-DATA-SPEC §3 v1. 늘리되 지우지 않는다.
INTENTS = ("correct", "fault", "unlabeled")
VIEWS = ("side", "front", "back")
ROLES = ("champion", "instructor", "student")
FAULT_INTENT_VOCAB = (
    "left_arm_underbent", "shoulder_shrug", "knee_bent", "hip_drop",
    "timing_early", "timing_late", "asymmetry", "other",
)
VIDEO_EXTS = (".mp4", ".mov")
_TERMINAL = ("done", "completed", "failed", "error")


class IntakeError(ValueError):
    """시트 한 줄이 규격을 어겼다 — 등록하지 않는다."""


# ── 순수 함수 (네트워크·파일쓰기 없음 — tests/test_intake_clips.py) ──────────────


def sha256_file(path: pathlib.Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def validate_row(row: dict, *, known_subjects: set[str]) -> dict:
    """시트 한 줄 검증 → 정규화된 dict. 어기면 IntakeError.

    동작 이름은 여기서 거르지 않는다 — 기준 라이브러리 밖 동작도 받는다
    (37-DATA-SPEC §4 우선순위 5 "지원 밖 동작"은 일부러 모으는 데이터다).
    """
    if not isinstance(row, dict):
        raise IntakeError("한 줄이 JSON 객체가 아니다")
    f = row.get("file")
    if not f:
        raise IntakeError("file 없음")
    ext = pathlib.Path(f).suffix.lower()
    if ext not in VIDEO_EXTS:
        raise IntakeError(f"영상 형식 {ext!r} — mp4/mov 만 받는다 (앱과 같다)")
    motion = (row.get("motion") or "").strip()
    if not motion or motion.startswith("ref-"):
        raise IntakeError(f"motion {motion!r} — 'kip-up' 처럼 ref- 없이 적는다")
    sid = (row.get("subject_id") or "").strip()
    if not sid.startswith("sub_"):
        raise IntakeError(f"subject_id {sid!r} — sub_ 로 시작해야 한다")
    subject = row.get("subject")
    if sid not in known_subjects:
        if not isinstance(subject, dict):
            raise IntakeError(f"{sid} 는 처음 보는 사람이다 — subject(role·consent)를 같이 적어라")
        validate_subject(subject)
    intent = row.get("intent")
    if intent not in INTENTS:
        raise IntakeError(f"intent {intent!r} — {INTENTS} 중 하나")
    fi = row.get("fault_intent") or []
    if not isinstance(fi, list) or any(x not in FAULT_INTENT_VOCAB for x in fi):
        raise IntakeError(f"fault_intent {fi!r} — 어휘 {FAULT_INTENT_VOCAB}")
    if fi and intent != "fault":
        raise IntakeError("fault_intent 는 intent=fault 일 때만")
    view = row.get("view")
    if view is not None and view not in VIEWS:
        raise IntakeError(f"view {view!r} — {VIEWS} 또는 null(모름)")
    return {
        "file": f, "ext": ext, "motion": motion, "subject_id": sid,
        "subject": subject if sid not in known_subjects else None,
        "intent": intent, "fault_intent": list(fi),
        "note": (row.get("note") or "").strip(),
        "view": view, "session": (row.get("session") or "").strip() or None,
        "pair_key": (row.get("pair_key") or "").strip() or None,
    }


def validate_sheet(rows: list[dict], *, known_subjects: set[str]) -> list[dict]:
    """시트 전체 검증. 새 사람은 **처음 나오는 줄에만** subject 를 적으면 된다."""
    known = set(known_subjects)
    out = []
    for i, row in enumerate(rows, 1):
        try:
            v = validate_row(row, known_subjects=known)
        except IntakeError as e:
            raise IntakeError(f"{i}행: {e}") from None
        if v["subject"] is not None:
            known.add(v["subject_id"])
        out.append(v)
    return out


def validate_subject(spec: dict) -> None:
    role = spec.get("role")
    if role not in ROLES:
        raise IntakeError(f"role {role!r} — {ROLES}")
    if role == "student" and spec.get("display_name"):
        raise IntakeError("학생은 display_name 을 두지 않는다 (개인정보) — subject_id 로만 식별")
    consent = spec.get("consent")
    if not isinstance(consent, dict) or "granted" not in consent:
        raise IntakeError("consent.granted 를 적어라 — 모르면 null (학습에는 안 쓴다)")
    if consent["granted"] not in (True, False, None):
        raise IntakeError("consent.granted 는 true / false / null")


def clip_record(v: dict, *, video_hash: str, s3_key: str, nbytes: int,
                motion_supported: bool, received_at: str) -> dict:
    return {
        "video_hash": video_hash,
        "motion": v["motion"],
        "motion_supported": motion_supported,
        "subject_id": v["subject_id"],
        "intent": v["intent"],
        "fault_intent": v["fault_intent"],
        "note": v["note"],
        "capture": {"view": v["view"], "session": v["session"] or received_at},
        "s3_key": s3_key,
        "bytes": nbytes,
        "received_at": received_at,
        "recorded_by": "intake_clips.py",
    }


def subject_record(subject_id: str, spec: dict, recorded_at: str) -> dict:
    return {
        "subject_id": subject_id,
        "role": spec["role"],
        "display_name": None if spec["role"] == "student" else spec.get("display_name"),
        "consent": spec["consent"],
        "recorded_at": recorded_at,
        "recorded_by": "intake_clips.py",
    }


def next_pair_id(motion: str, subject_id: str, existing: list[dict]) -> str:
    stem = f"pr_{motion.replace('-', '')}_{subject_id.removeprefix('sub_')}_"
    used = [p["pair_id"] for p in existing if str(p.get("pair_id", "")).startswith(stem)]
    n = 1 + max((int(u[len(stem):]) for u in used if u[len(stem):].isdigit()), default=0)
    return f"{stem}{n:03d}"


def assemble_pairs(clips: list[dict], pair_keys: dict[str, str], existing: list[dict],
                   recorded_at: str) -> list[dict]:
    """pair_key 로 묶인 clip 들 → pairs 레코드.

    짝의 정의(37-DATA-SPEC §2-3): **같은 사람 · 같은 동작**의 정타 1 + 실수 1.
    사람이 다르면 짝이 아니다(체형 차이가 결함으로 잡힌다). 어기면 IntakeError.
    이미 같은 (정타, 실수) 해시 짝이 있으면 만들지 않는다.
    """
    groups: dict[str, list[dict]] = {}
    for c in clips:
        k = pair_keys.get(c["video_hash"])
        if k:
            groups.setdefault(k, []).append(c)
    have = {(p.get("correct_hash"), p.get("fault_hash")) for p in existing}
    out: list[dict] = []
    for k, g in groups.items():
        intents = sorted(c["intent"] for c in g)
        if intents != ["correct", "fault"]:
            raise IntakeError(f"pair_key {k!r}: 정타 1 + 실수 1 이어야 한다 (지금 {intents})")
        if len({c["subject_id"] for c in g}) != 1 or len({c["motion"] for c in g}) != 1:
            raise IntakeError(f"pair_key {k!r}: 같은 사람 · 같은 동작이어야 짝이다")
        cor = next(c for c in g if c["intent"] == "correct")
        flt = next(c for c in g if c["intent"] == "fault")
        if (cor["video_hash"], flt["video_hash"]) in have:
            continue
        rec = {
            "pair_id": next_pair_id(cor["motion"], cor["subject_id"], existing + out),
            "motion": cor["motion"], "subject_id": cor["subject_id"],
            "correct_hash": cor["video_hash"], "fault_hash": flt["video_hash"],
            "correct_s3_key": cor["s3_key"], "fault_s3_key": flt["s3_key"],
            "fault_intent": flt["fault_intent"],
            "fault_intent_status": ("labeled — 촬영 메모" if flt["fault_intent"]
                                    else "unlabeled — belle/강사 입력 대기"),
            "captured_at": cor["capture"]["session"],
            "recorded_at": recorded_at, "recorded_by": "intake_clips.py",
        }
        out.append(rec)
    return out


def pending_clips(clips: list[dict], runs: list[dict]) -> list[dict]:
    """분석이 필요한 clip — 기준이 있는 동작 중 끝난(done) 분석 기록이 없는 것."""
    done = {r["video_hash"] for r in runs if r.get("status") == "done"}
    return [c for c in clips if c.get("motion_supported") and c["video_hash"] not in done]


def run_record(clip: dict, e2e: dict, doc: dict, analyzed_at: str) -> dict:
    result = (doc or {}).get("result") or {}
    return {
        "video_hash": clip["video_hash"],
        "uid": e2e.get("uid"),
        "analysis_id": e2e.get("analysisId"),
        "mode": (doc or {}).get("mode") or "mode1",
        "reference_motion_id": (doc or {}).get("referenceMotionId") or f"ref-{clip['motion']}",
        "status": e2e.get("status"),
        "error_code": e2e.get("errorCode"),
        "overall_score": result.get("overallScore"),
        "analysis_version": result.get("analysisVersion"),
        "elapsed_sec": e2e.get("elapsedSec"),
        "analyzed_at": analyzed_at,
        "recorded_by": "intake_clips.py analyze",
    }


# ── 입출력 ─────────────────────────────────────────────────────────────────────


def read_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        return
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _session():
    """로컬 = sunity-motion 프로파일 (pod_teardown._session 과 같은 규칙)."""
    import boto3

    try:
        if _PROFILE in boto3.Session().available_profiles:
            return boto3.Session(profile_name=_PROFILE)
    except Exception:  # noqa: BLE001 - 프로파일 조회 실패 = 기본 체인
        pass
    return boto3.Session()


def _firestore():
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(str(REPO / "firebase-sa.json")))
    return firestore.client()


def known_reference_motions(db) -> set[str]:
    """mode1 기준 라이브러리의 동작 이름 (ref- 뗀 것). 문서 본문은 안 읽는다."""
    return {d.id.removeprefix("ref-") for d in db.collection("reference").list_documents()
            if d.id.startswith("ref-")}


def s3_put_if_absent(s3, path: pathlib.Path, key: str, nbytes: int) -> str:
    from botocore.exceptions import ClientError

    try:
        head = s3.head_object(Bucket=BUCKET, Key=key)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") not in ("404", "NoSuchKey", "NotFound"):
            raise
    else:
        if int(head["ContentLength"]) == nbytes:
            return "exists"
        raise IntakeError(f"s3://{BUCKET}/{key} 가 다른 크기로 이미 있다 — 해시 충돌이면 멈춘다")
    ctype = "video/quicktime" if key.endswith(".mov") else "video/mp4"
    s3.upload_file(str(path), BUCKET, key, ExtraArgs={"ContentType": ctype})
    return "uploaded"


def pod_analyze_url(session) -> str:
    lam = session.client("lambda", region_name=REGION)
    env = lam.get_function_configuration(FunctionName=LAMBDA_FN)["Environment"]["Variables"]
    return env.get("RUNPOD_ANALYZE_URL", "")


# ── 명령 ───────────────────────────────────────────────────────────────────────


def cmd_register(a) -> int:
    today = _dt.date.today().isoformat()
    lines = [ln for ln in pathlib.Path(a.sheet).read_text(encoding="utf-8").splitlines() if ln.strip()]
    subjects = read_jsonl(SUBJECTS)
    known_subjects = {s["subject_id"] for s in subjects}
    clips = read_jsonl(CLIPS)
    have_hash = {c["video_hash"]: c for c in clips}

    # 1) 전부 검증부터 — 한 줄이라도 틀리면 아무것도 쓰지 않는다.
    try:
        validated = validate_sheet([json.loads(ln) for ln in lines], known_subjects=known_subjects)
    except (IntakeError, json.JSONDecodeError) as e:
        print(f"  {e}", file=sys.stderr)
        return 2
    rows = []
    for i, v in enumerate(validated, 1):
        p = pathlib.Path(v["file"]).expanduser()
        if not p.is_file():
            print(f"  {i}행: 파일 없음 {p}", file=sys.stderr)
            return 2
        rows.append((v, p))

    db = _firestore()
    known_motions = known_reference_motions(db)
    s3 = None if a.dry_run else _session().client("s3", region_name=REGION)

    new_clips, pair_keys, new_subjects = [], {}, []
    for v, p in rows:
        nbytes = p.stat().st_size
        vh = sha256_file(p)
        supported = v["motion"] in known_motions
        note = []
        if not supported:
            note.append("기준 라이브러리 밖 동작 — mode1 비교 불가, 그대로 받는다")
        if nbytes > MAX_VIDEO_BYTES:
            note.append(f"{nbytes / 1e6:.1f}MB > 앱 한도 {MAX_VIDEO_BYTES / 1e6:.0f}MB — 앱 경로 분석 불가")
        if vh in have_hash:
            prev = have_hash[vh]
            clash = [k for k in ("motion", "subject_id", "intent") if prev.get(k) != v[k]]
            print(f"  이미 등록됨 {vh[:12]} {prev['motion']} {prev['intent']}"
                  + (f"  ★같은 영상인데 시트가 {', '.join(clash)} 를 다르게 적었다 — 기존 기록 유지, 확인 필요"
                     if clash else ""))
            if v["pair_key"]:
                pair_keys[vh] = v["pair_key"]
            continue
        key = f"{INTAKE_PREFIX}{vh}{v['ext']}"
        state = "dry-run" if a.dry_run else s3_put_if_absent(s3, p, key, nbytes)
        rec = clip_record(v, video_hash=vh, s3_key=key, nbytes=nbytes,
                          motion_supported=supported, received_at=today)
        new_clips.append(rec)
        have_hash[vh] = rec
        if v["pair_key"]:
            pair_keys[vh] = v["pair_key"]
        if v["subject"] is not None and v["subject_id"] not in {s["subject_id"] for s in new_subjects}:
            new_subjects.append(subject_record(v["subject_id"], v["subject"], today))
        print(f"  {vh[:12]} {v['motion']:14s} {v['intent']:9s} {v['subject_id']:8s} "
              f"{nbytes / 1e6:6.1f}MB  S3 {state}" + ("  ★" + " / ".join(note) if note else ""))

    all_clips = list(have_hash.values())
    try:
        new_pairs = assemble_pairs([c for c in all_clips if c["video_hash"] in pair_keys],
                                   pair_keys, read_jsonl(PAIRS), today)
    except IntakeError as e:
        print(f"  짝 오류: {e}", file=sys.stderr)
        return 2
    for pr in new_pairs:
        print(f"  짝 {pr['pair_id']}  {pr['motion']} · {pr['subject_id']}")

    if a.dry_run:
        print(f"\ndry-run — 쓰지 않았다. 새 영상 {len(new_clips)} · 새 사람 {len(new_subjects)} · 새 짝 {len(new_pairs)}")
        return 0
    append_jsonl(SUBJECTS, new_subjects)
    append_jsonl(CLIPS, new_clips)
    append_jsonl(PAIRS, new_pairs)
    print(f"\n등록: 새 영상 {len(new_clips)} · 새 사람 {len(new_subjects)} · 새 짝 {len(new_pairs)}")
    if new_subjects and any(s["consent"].get("granted") is not True for s in new_subjects):
        print("  ★동의가 true 가 아닌 사람이 있다 — 그 영상은 평가·측정에만 쓰고 학습에는 안 쓴다")
    return 0


def cmd_analyze(a) -> int:
    clips = read_jsonl(CLIPS)
    runs = read_jsonl(RUNS)
    if a.hash:
        want = set(a.hash)
        todo = [c for c in clips if c["video_hash"] in want or c["video_hash"][:12] in want]
    else:
        todo = pending_clips(clips, runs)
    if not todo:
        print("분석할 영상이 없다")
        return 0
    unsupported = [c for c in todo if not c.get("motion_supported")]
    todo = [c for c in todo if c.get("motion_supported")]
    for c in unsupported:
        print(f"  건너뜀 {c['video_hash'][:12]} {c['motion']} — 기준 라이브러리 밖(mode1 불가)")

    session = _session()
    url = pod_analyze_url(session)
    if not url or url == POD_DOWN_URL:
        print(f"Pod 이 내려가 있다 (Lambda RUNPOD_ANALYZE_URL={url or '없음'}).\n"
              "지금 분석하면 실패 화면만 쌓인다 — Pod 기동 절차 먼저 "
              "([[demo-only-pod-bring-up-procedure]]).", file=sys.stderr)
        return 3
    s3 = session.client("s3", region_name=REGION)
    db = _firestore()
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="sunity-intake-"))
    print(f"분석 {len(todo)}편 — 직렬, 한 편당 최대 {E2E_TIMEOUT_S // 60}분")
    for c in todo:
        local = tmp / pathlib.Path(c["s3_key"]).name
        s3.download_file(BUCKET, c["s3_key"], str(local))
        if sha256_file(local) != c["video_hash"]:
            print(f"  실패 {c['video_hash'][:12]} S3 사본 해시 불일치 — 멈춘다", file=sys.stderr)
            return 4
        cmd = [sys.executable, str(E2E), "--video", str(local), "--mode", "mode1",
               "--reference", f"ref-{c['motion']}", "--timeout", str(E2E_TIMEOUT_S)]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
        local.unlink(missing_ok=True)
        out_line = next((ln for ln in reversed(proc.stdout.splitlines()) if ln.startswith("{")), None)
        if proc.returncode != 0 or out_line is None:
            print(f"  실패 {c['video_hash'][:12]} e2e rc={proc.returncode}\n{proc.stderr[-800:]}",
                  file=sys.stderr)
            return 5
        e2e = json.loads(out_line)
        doc = db.document(f"users/{e2e['uid']}/analyses/{e2e['analysisId']}").get().to_dict() or {}
        rec = run_record(c, e2e, doc, _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"))
        append_jsonl(RUNS, [rec])
        print(f"  {c['video_hash'][:12]} {c['motion']:14s} {c['intent']:9s} → {rec['status']} "
              f"점수 {rec['overall_score']}  ({e2e.get('elapsedSec')}초)  {e2e['analysisId'][:8]}")
        if rec["status"] not in _TERMINAL:
            # 끝나지 않은 채 다음 영상을 넣으면 동시 분석이 된다 (2026-09-22 사고).
            print("  ★시간 안에 안 끝났다 — 동시 분석을 막으려고 배치를 멈춘다", file=sys.stderr)
            return 6
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register", help="영상 + 메모 → 원장 등록 + S3 영구 사본")
    r.add_argument("--sheet", required=True, help="한 줄 = 영상 1편인 JSONL")
    r.add_argument("--dry-run", action="store_true", help="검증·해시만. S3·원장 쓰기 없음")
    z = sub.add_parser("analyze", help="등록 영상 → 앱 경로 분석 → analysis_runs.jsonl")
    g = z.add_mutually_exclusive_group(required=True)
    g.add_argument("--pending", action="store_true", help="분석 기록이 없는 영상 전부")
    g.add_argument("--hash", nargs="+", help="video_hash (앞 12자리도 됨)")
    a = ap.parse_args()
    return cmd_register(a) if a.cmd == "register" else cmd_analyze(a)


if __name__ == "__main__":
    raise SystemExit(main())
