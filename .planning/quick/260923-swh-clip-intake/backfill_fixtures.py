"""1회성 소급 — phase15 정은지 fixture 12편을 clips.jsonl 에, 2026-09-22 gnj 분석 11건을
analysis_runs.jsonl 에 기록한다 (quick-260923-swh).

영상 해시는 pairs.jsonl(2026-09-22 S3 원본에서 계산)을 그대로 쓴다.
분석 doc ↔ 영상 연결은 **S3 ETag 대조**로 확정한다 — 앱 경로 업로드 사본
uploads/{uid}/{analysisId}.mp4 와 fixture 원본이 둘 다 단일 PUT 이라 ETag = 내용 MD5.
분석 doc id 11건은 지난 세션 대화 기록에서 복원했다(그때 리포에 안 남아서).
재실행해도 이미 있는 해시/분석은 건너뛴다.
"""
import datetime as dt
import json
import pathlib
import sys

import boto3
import firebase_admin
from firebase_admin import credentials, firestore

REPO = pathlib.Path(__file__).resolve().parents[3]
DATA = REPO / "backend" / "training" / "data"
B = "sunity-motion-pilot-videos"
RUNS_0922 = [
    ("hohsgAIG1GSGvR9GRUtdgxYHBzT2", "9fbe0cab92ec4c26a0e65d2c83151eae"),
    ("1Zx7HJJT7ddl97ggQ2U7QIMN9Sk1", "9fd006aa9ddc427989fc2e5333e906ab"),
    ("PxM3cZkUvVSxcGbBDswtARLEYIK2", "c59042f4bc3f45c8a3ca5310a3d92d65"),
    ("MJ93ILDBESPUM14QmHQ6Q1T45gn1", "d44ddb0cf47f4ee2b9a1809b95153e19"),
    ("3tF01LOYZYRiMCQyNBrRhizJm212", "e28c760cc8ad42999f5dde9fd3c33a84"),
    ("tIftxhf1J5UNOAxWV7ljzS2gunl2", "027817a635e2480eb20755a283dd8fef"),
    ("vI6Bjq1K8uONW807tXWIO774AKB3", "8f5510aa9ae547c8a7d0265eb9679ef2"),
    ("KAi6p4ubcfVMvo8TfvytTkzNp0j2", "e83811d3cc484887b0aef315346f8aae"),
    ("FQVENFYcElbLPo8ukylcc2D5il43", "b468337d704a4b73b187f69c5798ff70"),
    ("0Vab2WWwRIUtACG2q802xbogOb02", "d023d584779348a8922464486090b50a"),
    ("16WrOWwza8gJzF6JRIL0FaxPrz93", "0d43112933134c30a4db352724f74ee8"),
]


def jl(p):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


s3 = boto3.Session(profile_name="sunity-motion").client("s3", region_name="ap-northeast-2")
firebase_admin.initialize_app(credentials.Certificate(str(REPO / "firebase-sa.json")))
db = firestore.client()

pairs = jl(DATA / "pairs.jsonl")
clips = jl(DATA / "clips.jsonl")
runs = jl(DATA / "analysis_runs.jsonl")
have_clip = {c["video_hash"] for c in clips}
have_run = {r["analysis_id"] for r in runs}

etag_to_hash, new_clips = {}, []
for p in pairs:
    for side in ("correct", "fault"):
        key, vh = p[f"{side}_s3_key"], p[f"{side}_hash"]
        h = s3.head_object(Bucket=B, Key=key)
        etag_to_hash[h["ETag"]] = vh
        if vh in have_clip:
            continue
        note = ("phase15 정타 — 기준 영상과 같은 사람·같은 촬영으로 기록됨. 기준 사본 "
                f"reference/ref-{p['motion']}.mp4 와 바이트는 다르다(별도 인코딩). 평가에 쓰면 누수"
                if side == "correct" else
                "phase15 정은지 일부러 실수 — 무엇을 틀리게 했는지 미기록(belle/강사 입력 대기)")
        new_clips.append({
            "video_hash": vh, "motion": p["motion"], "motion_supported": True,
            "subject_id": p["subject_id"], "intent": side, "fault_intent": [],
            "note": note, "capture": {"view": None, "session": p["captured_at"]},
            "s3_key": key, "bytes": int(h["ContentLength"]), "received_at": p["captured_at"],
            "recorded_by": "backfill quick-260923-swh",
        })

new_runs = []
for uid, aid in RUNS_0922:
    if aid in have_run:
        continue
    h = s3.head_object(Bucket=B, Key=f"uploads/{uid}/{aid}.mp4")
    vh = etag_to_hash.get(h["ETag"])
    if vh is None:
        print(f"  {aid[:8]}: 업로드 사본 ETag 가 fixture 와 안 맞는다 — 건너뜀", file=sys.stderr)
        continue
    d = db.document(f"users/{uid}/analyses/{aid}").get().to_dict() or {}
    res = d.get("result") or {}
    new_runs.append({
        "video_hash": vh, "uid": uid, "analysis_id": aid, "mode": d.get("mode"),
        "reference_motion_id": d.get("referenceMotionId"), "status": d.get("status"),
        "error_code": d.get("errorCode"), "overall_score": res.get("overallScore"),
        "analysis_version": res.get("analysisVersion"), "elapsed_sec": None,
        "analyzed_at": dt.datetime.fromtimestamp(d["createdAt"] / 1000, dt.timezone.utc)
                         .isoformat(timespec="seconds"),
        "recorded_by": "backfill quick-260923-swh (doc id = 지난 세션 대화 기록 복원, 영상 = S3 ETag 대조)",
    })

with open(DATA / "clips.jsonl", "a", encoding="utf-8") as f:
    for r in new_clips:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
with open(DATA / "analysis_runs.jsonl", "a", encoding="utf-8") as f:
    for r in new_runs:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"clips +{len(new_clips)} · analysis_runs +{len(new_runs)}")
for r in new_runs:
    print(f"  {r['analysis_id'][:8]} {r['reference_motion_id']:22s} {r['status']:5s} 점수 {r['overall_score']} "
          f"{(r['analysis_version'] or {}).get('commitSha', '?')[:8]} {r['video_hash'][:12]}")
