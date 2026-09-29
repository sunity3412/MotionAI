#!/usr/bin/env python3
"""legacy 기준 모션 무접촉 증명용 스냅샷 · diff (Phase 38-09, 리뷰 R10 · Success ④).

왜:
  Phase 38 은 `reference/` 컬렉션에 공급자 등록 doc 을 새로 쓰고, 버킷 알림에 `reference/` 접두사를
  붙이고, 공유 layer 를 5함수에 다시 붙인다. "legacy 11 doc 과 저장 분석은 건드리지 않았다" 는 말은
  **첫 쓰기 전** 에 찍은 raw 값의 해시와 대조할 때만 증명이 된다 — 쓰고 나서 찍으면 무엇과도 비교할
  수 없다. 그래서 이 스크립트는 버전 overlay 를 거치지 않는 raw top-level doc
  (`firestore_admin.get_reference_registration`) 을 읽는다(`get_reference_motion` 은 overlay 라 쓰지 않는다).

사용 (리포 루트에서, AWS_PROFILE=sunity-motion — S3 목록에 필요):
  backend/.venv/bin/python backend/scripts/snapshot_reference_baseline.py --out <before.json>
      # 스냅샷 저장(읽기 ≈ 15: legacy 11 + release 포인터 1 + 저장 분석 3)
  backend/.venv/bin/python backend/scripts/snapshot_reference_baseline.py --diff <before.json> --out <after.json>
      # 온라인: 같은 대상을 다시 읽어 after 를 저장한 뒤 before 와 비교
  backend/.venv/bin/python backend/scripts/snapshot_reference_baseline.py --diff <before.json> --out /dev/null --offline <after.json>
      # 오프라인: after 를 파일에서 읽는다 — Firestore 읽기 0 · S3/AWS 호출 0 · 클라이언트 생성 0

exit code (온라인 · 오프라인 같은 규약): 0 = 차이 없음, 1 = 차이 ≥ 1(차이 줄을 stdout 에 한 줄씩).
--out 만 쓰면 저장 후 0.

읽기 예산: Firestore Spark 무료 플랜 읽기 5만/일 캡(메모리 firestore-spark-50k-read-cap) — 이 스크립트는
온라인 1회에 15건만 읽는다. 전수 스캔 없음. 회귀 표본 3건은 `--out` 첫 스냅샷에서 S3 `results/` 목록으로
고정하고, `--diff` 는 before 에 적힌 같은 3건을 다시 읽는다(목록을 다시 뽑지 않는다 — 표본이 바뀌면
diff 가 무의미하다).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_LAYER = _REPO / "backend" / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

from sunity_shared import firestore_admin  # noqa: E402  (클라이언트는 첫 읽기 때 lazy 생성)

DEFAULT_BUCKET = "sunity-motion-pilot-videos"
_SA_JSON = _REPO / "sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json"
SOURCE_LABEL = "raw top-level doc (no version overlay)"

# docs/reference-motions.md §5 의 legacy id 11개 — 공급자 등록 doc(uuid hex) 과 섞이지 않는다.
LEGACY_REFERENCE_IDS = (
    "ref-sideway-spin",
    "ref-climb",
    "ref-invert",
    "ref-foxtop",
    "ref-foxtop-split",
    "ref-kip-up",
    "ref-peter-pan",
    "ref-power-spin",
    "ref-elbow-twist-sister",
    "ref-pdshape",
    "ref-combo",
)
# 전역 버전 포인터(reference/_release.activeCandidate) — mode1 이 읽는 기준 버전을 정한다.
RELEASE_POINTER_ID = "_release"

# 소비 필드 — mode1 이 기준 doc 에서 읽는 것(docs/reference-motions.md §3).
_REF_FIELDS = ("anglesJointKeys", "anglesFrames", "anglesUpdatedAt", "clipRange", "isActive", "updatedAt")
_ANALYSIS_FIELDS = ("status", "mode", "referenceMotionId", "updatedAt")
_RESULTS_KEY_RE = re.compile(r"^results/(?P<uid>[^/]+)/(?P<aid>[^/]+)/")
REGRESSION_SAMPLE_COUNT = 3


# ─────────────────────────── 순수 함수 (테스트 대상) ───────────────────────────


def _canonical_json(value) -> str:
    # Firestore 의 DatetimeWithNanoseconds 등 JSON 밖 타입은 str 로 — 같은 값이면 같은 문자열.
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_doc_hash(doc: dict | None) -> str | None:
    """키 정렬 JSON 의 sha256. doc 이 없으면 None(없는 것과 빈 것은 다르다)."""
    if doc is None:
        return None
    return _sha256(_canonical_json(doc))


def _plain(value):
    """스냅샷 JSON 에 넣을 수 있는 값으로(원문 타입이 JSON 밖이면 str)."""
    return json.loads(_canonical_json(value))


def summarize_reference_doc(doc: dict | None) -> dict:
    """legacy 기준 doc 1개의 raw 소비 필드 + 해시. doc 이 없으면 exists=False 만."""
    if doc is None:
        return {"exists": False}
    angles = doc.get("angles")
    out: dict = {
        "exists": True,
        "docSha256": canonical_doc_hash(doc),
        "anglesSha256": _sha256(_canonical_json(angles)) if angles is not None else None,
        "anglesLen": len(angles) if isinstance(angles, list) else None,
    }
    for field in _REF_FIELDS:
        out[field] = _plain(doc.get(field))
    # 버전 포인터 계열 필드는 이름이 여럿이라 있는 것 그대로 싣는다.
    for key in sorted(doc):
        lowered = key.lower()
        if "version" in lowered or "candidate" in lowered:
            out[f"pointer:{key}"] = _plain(doc[key])
    return out


def summarize_analysis_doc(doc: dict | None) -> dict:
    if doc is None:
        return {"exists": False}
    result = doc.get("result") if isinstance(doc.get("result"), dict) else {}
    breakdown = result.get("deductionBreakdown") if isinstance(result.get("deductionBreakdown"), dict) else {}
    out: dict = {"exists": True, "docSha256": canonical_doc_hash(doc)}
    for field in _ANALYSIS_FIELDS:
        out[field] = _plain(doc.get(field))
    out["result.overallScore"] = _plain(result.get("overallScore"))
    out["result.deductionBreakdown.final"] = _plain(breakdown.get("final"))
    return out


def pick_regression_samples(keys: list[str], count: int = REGRESSION_SAMPLE_COUNT) -> list[tuple[str, str]]:
    """`results/{uid}/{analysisId}/…` 키 목록에서 서로 다른 (uid, analysisId) 앞 count 쌍(목록 순서 고정)."""
    seen: list[tuple[str, str]] = []
    for key in keys:
        m = _RESULTS_KEY_RE.match(key)
        if not m:
            continue
        pair = (m.group("uid"), m.group("aid"))
        if pair not in seen:
            seen.append(pair)
        if len(seen) >= count:
            break
    return seen


def _diff_field_maps(label: str, before: dict, after: dict) -> list[str]:
    lines: list[str] = []
    for field in sorted(set(before) | set(after)):
        if field not in after:
            lines.append(f"{label} {field}: missing in after (before={_canonical_json(before[field])})")
        elif field not in before:
            lines.append(f"{label} {field}: new in after (after={_canonical_json(after[field])})")
        elif before[field] != after[field]:
            lines.append(
                f"{label} {field}: {_canonical_json(before[field])} -> {_canonical_json(after[field])}"
            )
    return lines


def diff_snapshots(before: dict, after: dict) -> list[str]:
    """필드별 차이 문자열 목록. 빈 목록 = 무접촉."""
    lines: list[str] = []
    b_refs, a_refs = before.get("references", {}), after.get("references", {})
    for ref_id in sorted(set(b_refs) | set(a_refs)):
        if ref_id not in a_refs:
            lines.append(f"references[{ref_id}]: missing in after")
        elif ref_id not in b_refs:
            lines.append(f"references[{ref_id}]: new in after")
        else:
            lines.extend(_diff_field_maps(f"references[{ref_id}]", b_refs[ref_id], a_refs[ref_id]))

    b_s3 = {o["Key"]: o for o in before.get("s3ReferenceObjects", [])}
    a_s3 = {o["Key"]: o for o in after.get("s3ReferenceObjects", [])}
    for key in sorted(set(b_s3) | set(a_s3)):
        if key not in a_s3:
            lines.append(f"s3[{key}]: missing in after")
        elif key not in b_s3:
            lines.append(f"s3[{key}]: new in after")
        else:
            lines.extend(_diff_field_maps(f"s3[{key}]", b_s3[key], a_s3[key]))

    def _samples(snap: dict) -> dict:
        return {f"{s['uid']}/{s['analysisId']}": s for s in snap.get("regressionSamples", [])}

    b_sm, a_sm = _samples(before), _samples(after)
    for sid in sorted(set(b_sm) | set(a_sm)):
        if sid not in a_sm:
            lines.append(f"regressionSamples[{sid}]: missing in after")
        elif sid not in b_sm:
            lines.append(f"regressionSamples[{sid}]: new in after")
        else:
            lines.extend(_diff_field_maps(f"regressionSamples[{sid}]", b_sm[sid], a_sm[sid]))
    return lines


# ─────────────────────────── 읽기 (온라인 전용) ───────────────────────────


def _s3_client():
    import boto3  # 온라인에서만 — 오프라인 diff 는 boto3 클라이언트를 만들지 않는다.

    return boto3.client("s3")


def _list_keys(s3, bucket: str, prefix: str, max_keys: int) -> list[dict]:
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=max_keys)
    return list(resp.get("Contents", []))


def take_snapshot(bucket: str, samples: list[tuple[str, str]] | None = None) -> dict:
    """온라인 스냅샷. samples 가 None 이면 results/ 목록에서 앞 3쌍을 고른다."""
    if not (os.environ.get("FIREBASE_SA_JSON") or os.environ.get("FIREBASE_SA_PATH")) and _SA_JSON.exists():
        os.environ["FIREBASE_SA_PATH"] = str(_SA_JSON)

    references: dict = {}
    for ref_id in (*LEGACY_REFERENCE_IDS, RELEASE_POINTER_ID):
        references[ref_id] = summarize_reference_doc(firestore_admin.get_reference_registration(ref_id))

    s3 = _s3_client()
    s3_objects = [
        {"Key": o["Key"], "ETag": o["ETag"], "Size": o["Size"]}
        for o in _list_keys(s3, bucket, "reference/ref-", 1000)
    ]
    if samples is None:
        results = _list_keys(s3, bucket, "results/", 300)
        samples = pick_regression_samples([o["Key"] for o in results])

    regression = []
    for uid, aid in samples:
        entry = {"uid": uid, "analysisId": aid}
        entry.update(summarize_analysis_doc(firestore_admin.get_analysis(uid, aid)))
        regression.append(entry)

    return {
        "source": SOURCE_LABEL,
        "bucket": bucket,
        "takenAtMs": int(time.time() * 1000),
        "references": references,
        "s3ReferenceObjects": s3_objects,
        "regressionSamples": regression,
    }


# ─────────────────────────── CLI ───────────────────────────


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dump(snapshot: dict, path: str) -> None:
    Path(path).write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="스냅샷 저장 경로(/dev/null 가능)")
    ap.add_argument("--diff", default=None, help="비교할 before 스냅샷 JSON")
    ap.add_argument(
        "--offline",
        default=None,
        help="--diff 와 함께: after 를 이 JSON 에서 읽는다(Firestore · AWS 호출 0)",
    )
    ap.add_argument("--bucket", default=DEFAULT_BUCKET)
    args = ap.parse_args(argv)

    if args.offline and not args.diff:
        ap.error("--offline 은 --diff 와 함께만 쓴다")

    if not args.diff:
        _dump(take_snapshot(args.bucket), args.out)
        print(f"snapshot saved: {args.out}")
        return 0

    before = _load(args.diff)
    if args.offline:
        after = _load(args.offline)
    else:
        samples = [(s["uid"], s["analysisId"]) for s in before.get("regressionSamples", [])]
        after = take_snapshot(before.get("bucket", args.bucket), samples=samples)
    if not (args.offline and Path(args.out).resolve() == Path(args.offline).resolve()):
        _dump(after, args.out)

    lines = diff_snapshots(before, after)
    for line in lines:
        print(line)
    print(f"differences: {len(lines)}")
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
