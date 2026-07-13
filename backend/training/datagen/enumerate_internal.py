"""내부 fault 트랙 열거 — Firestore 분석 문서 → 학습 후보 JSON (처방 B, quick 260713-jxr).

22-07 게이트 FAIL 근본원인 1번(fault 트랙 0행 — 결함 짚기 감독 신호 부재)의 유일한
데이터 처방. belle 결정(2026-07-13, 구두 승인): 파일럿 이전 내부 데이터 학습사용 일괄
승인 + 명시 거부(learningOptIn=false) 1건 무조건 제외 + anonymize(얼굴 블러) 강제 유지
+ 이후 신규 데이터는 optIn=true 엄격 필터.

learningOptIn 계약(models.py §Phase 26 미러 주석): 필드 부재(Phase 26 이전 문서) =
미동의 fail-safe. 이 모듈의 consent_allows 가 학습 후보 진입점에서 이 계약을 집행한다
— 기본 strict(부재=제외), belle 일괄승인은 호출자가 --bulk-approval 로 명시할 때만
컷오프(2026-07-13) 이전 문서에 한해 발동(T-Q13-02 동의 우회 방어).

흐름: collection_group('analyses') 읽기 전용 스트림(measure_error_profile 패턴) →
status=done + consent 게이트 + uploads/{uid}/{analysisId}.{ext} 도출(s3keys 재사용) →
S3 head(존재 확인 + ETag) → 후보 간/기존 manifest 대비 ETag pre-dedup → 스케일 가드
(100~500, T-Q13-04) → 후보 JSON 방출.

uid 취급(T-Q13-01): uid 는 s3 키 도출용 중간값 — 후보 dict 에 uid 키를 만들지 않고
s3_key 문자열 안에만 존재한다. 후보 JSON 자체가 uid 파생 정보를 담으므로 산출 경로는
리포 밖 강제(out_path_inside_repo 가드) — 최종 manifest 에는 uid 파생 필드가 절대
들어가지 않는다(anonymize_batch 의 fence 가 소유).

google/boto3 는 lazy import — 순수 함수(consent/dedup/guard/bucket)는 네트워크 0 으로
테스트된다(test_enumerate_internal.py).

CLI (Pod 실행 — runbook 참조, executor 로컬 실행 금지):
  FIREBASE_SA_PATH=... python3 datagen/enumerate_internal.py --bulk-approval --dry-run
  FIREBASE_SA_PATH=... python3 datagen/enumerate_internal.py --bulk-approval \
      --out /workspace/internal_candidates.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve()
_BACKEND = _HERE.parents[2]
_REPO_ROOT = _HERE.parents[3]
_SHARED = _BACKEND / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

SCRIPT_VERSION = "enumerate-internal-v1.0"

# belle 일괄승인 컷오프 = 2026-07-13T00:00:00Z (epoch ms). 이후 생성 문서는 부재 =
# 미동의 fail-safe 복원(phase 26 이후 앱이 필드를 항상 기록하므로 부재 = 파일럿 이전
# 이지만, createdAt 컷오프로 이중 방어한다 — T-Q13-02).
BELLE_BULK_APPROVAL_CUTOFF_MS = 1_783_900_800_000

# 스케일 가드 범위 — belle 승인 예산 = 129행 배치의 ~2.9배(≈371행 스케일, 구 추정치).
# 범위 밖 = Firestore 상태가 예상과 다르다는 신호(과금 폭주/공집합) → 계수만 출력하고
# 정지, --force 로만 우회 (T-Q13-04).
SCALE_GUARD_LO = 100
SCALE_GUARD_HI = 500

# 잠정 버킷 임계 — result.overall 이 이 값 이상이면 "정타", 미만이면 "fault".
PROVISIONAL_BUCKET_THRESHOLD = 80

_DEFAULT_BUCKET = "sunity-motion-pilot-videos"
_VIDEO_EXTS = ("mp4", "mov")


# ---------------------------------------------------------------------------
# 순수 함수 — 네트워크 0 (test_enumerate_internal.py 가 소유).
# ---------------------------------------------------------------------------
def _created_at_ms(doc: dict):
    """doc.createdAt → epoch ms 또는 None. int/float ms 와 datetime 양쪽 흡수."""
    v = (doc or {}).get("createdAt")
    if isinstance(v, bool):  # bool 은 int subclass — 명시 거부.
        return None
    if isinstance(v, (int, float)):
        return int(v)
    # Firestore Timestamp/datetime — timestamp() 보유 시 ms 변환.
    ts = getattr(v, "timestamp", None)
    if callable(ts):
        try:
            return int(ts() * 1000)
        except (ValueError, OverflowError, OSError):
            return None
    return None


def consent_allows(
    doc: dict,
    *,
    bulk_approval: bool,
    cutoff_ms: int = BELLE_BULK_APPROVAL_CUTOFF_MS,
) -> bool:
    """학습 동의 게이트 3분기 (belle 2026-07-13 결정 + models.py learningOptIn 계약).

    · learningOptIn is False → 제외. 플래그 무관 — belle 명시 거부 1건 무조건 제외.
    · learningOptIn is True → 통과.
    · 필드 부재(None 포함) → 기본 strict 제외(fail-safe 계약 보존). bulk_approval=True
      명시 시에만 createdAt < cutoff_ms(파일럿 이전 문서)에 한해 통과. createdAt 미상은
      컷오프 이전 입증 불가라 제외(방어적).
    """
    opt = (doc or {}).get("learningOptIn")
    if opt is False:
        return False
    if opt is True:
        return True
    # 부재(None) — strict 기본.
    if not bulk_approval:
        return False
    created = _created_at_ms(doc)
    return created is not None and created < cutoff_ms


def derive_upload_key(uid: str, analysis_id: str, doc: dict) -> str | None:
    """분석 문서 → uploads/{uid}/{analysisId}.{ext} (s3keys.build_upload_key 재사용).

    videoFormat 우선, 없으면 fileName 확장자(mp4/mov 만), 그 외 None(재구성 불가).
    """
    from sunity_shared import s3keys  # shared layer — 네트워크 무관 순수.

    fmt = str((doc or {}).get("videoFormat") or "").lower()
    if fmt not in _VIDEO_EXTS:
        name = str((doc or {}).get("fileName") or "")
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        fmt = ext if ext in _VIDEO_EXTS else ""
    if not fmt:
        return None
    return s3keys.build_upload_key(uid, analysis_id, fmt)


def provisional_label_bucket(doc: dict) -> str | None:
    """result.overall → 잠정 버킷 — 교사 라벨이 최종, ground truth 아님.

    [[analysis-objectivity-no-human-scores]] 저촉 없음: 파이프라인 산출값의 임계 라벨
    (사람 점수 라벨링이 아니라 자동 산출 overall 의 임계 분기)이다. overall >= 80 →
    "정타", 미만 → "fault", 부재/비숫자 → None (Task 2 에서 병합 전 skip).
    """
    overall = ((doc or {}).get("result") or {}).get("overall")
    if isinstance(overall, bool) or not isinstance(overall, (int, float)):
        return None
    return "정타" if overall >= PROVISIONAL_BUCKET_THRESHOLD else "fault"


def build_candidate(uid: str, analysis_id: str, doc: dict, etag: str | None) -> dict:
    """후보 dict 생성 — uid/analysisId 키를 만들지 않는다 (T-Q13-01).

    uid 는 s3_key 문자열 안에만 존재(다운로드용 중간값). 최종 manifest 행은
    anonymize_batch.build_manifest_row 가 video_hash 기반으로만 생성한다.
    """
    return {
        "s3_key": derive_upload_key(uid, analysis_id, doc),
        "etag": etag,
        "created_at_ms": _created_at_ms(doc),
        "motion": (doc or {}).get("referenceMotionId") or None,
        "provisional_bucket": provisional_label_bucket(doc),
        "opt_in": (doc or {}).get("learningOptIn"),
    }


def dedup_candidates(candidates: list[dict], known_etags: set[str]) -> list[dict]:
    """ETag pre-dedup — (a) 후보 간 중복 첫 행만 유지 (b) 기존 manifest ETag 와 일치
    시 제외(시드/reference/수집분 재업로드 차단).

    멀티파트 ETag('-' 포함)는 content-md5 가 아니라 파트 해시 조합이라 신뢰 불가 —
    pre-dedup 을 통과시키고 후속 content-hash dedup(anonymize_batch, video_hash)에
    위임한다. ETag 미상(None)도 동일하게 통과.
    """
    seen: set[str] = set()
    out: list[dict] = []
    for cand in candidates:
        etag = cand.get("etag")
        if not etag or "-" in str(etag):
            out.append(cand)  # 멀티파트/미상 — hash dedup(Task 2) 위임.
            continue
        if etag in known_etags or etag in seen:
            continue
        seen.add(etag)
        out.append(cand)
    return out


def scale_guard(n: int, *, lo: int = SCALE_GUARD_LO, hi: int = SCALE_GUARD_HI) -> bool:
    """dedup 후 계수가 belle 승인 예산 범위(100~500) 안이면 True (T-Q13-04)."""
    return lo <= int(n) <= hi


def out_path_inside_repo(path: str) -> bool:
    """산출 경로가 리포 안이면 True — 후보 JSON(uid 포함)은 리포 내 기록 금지."""
    try:
        resolved = Path(path).resolve()
    except (OSError, ValueError):
        return True  # 판정 불가 — 보수적으로 거부.
    return resolved.is_relative_to(_REPO_ROOT)


# ---------------------------------------------------------------------------
# I/O 껍데기 — Firestore/S3 (lazy import, Pod 실행 전용).
# ---------------------------------------------------------------------------
def iter_candidate_docs(db, *, limit: int = 0):
    """collection_group('analyses') 읽기 전용 스트림 → (uid, analysis_id, doc) yield.

    measure_error_profile._iter_analyses 와 달리 uid 가 s3 키 도출에 필요하므로
    reference.path(users/{uid}/analyses/{id})에서 파싱해 튜플로 넘긴다 — uid 는 s3 키
    도출용 중간값이며 최종 manifest 에 기록되지 않는다(T-22-01 정신).
    """
    q = db.collection_group("analyses")
    if limit:
        q = q.limit(limit)
    for snap in q.stream():
        parts = str(snap.reference.path).split("/")
        # users/{uid}/analyses/{id} — 형식 밖 경로(다른 collection_group 충돌)는 skip.
        if len(parts) != 4 or parts[0] != "users" or parts[2] != "analyses":
            continue
        yield parts[1], parts[3], (snap.to_dict() or {})


def fetch_etag(s3, bucket: str, key: str) -> str | None:
    """head_object → ETag(따옴표 strip). 404/오류 는 None(존재 확인 겸용)."""
    try:
        resp = s3.head_object(Bucket=bucket, Key=key)
    except Exception:  # noqa: BLE001 - 404 포함, 부재/권한 오류는 후보 제외 신호.
        return None
    etag = resp.get("ETag")
    return str(etag).strip('"') if etag else None


def known_manifest_etags(manifest: dict, s3, bucket: str) -> set[str]:
    """기존 manifest 행(collected=true + s3_key 보유)의 S3 ETag 집합 — 재업로드 차단.

    head 실패는 graceful skip(해당 행 ETag 없이 진행 — dedup 은 hash 단계가 보완).
    """
    etags: set[str] = set()
    for row in (manifest or {}).get("rows", []):
        if not row.get("collected") or not row.get("s3_key"):
            continue
        etag = fetch_etag(s3, bucket, row["s3_key"])
        if etag:
            etags.add(etag)
    return etags


def enumerate_candidates(
    db,
    s3,
    manifest: dict,
    *,
    bulk_approval: bool,
    bucket: str = _DEFAULT_BUCKET,
    limit: int = 0,
) -> tuple[list[dict], dict]:
    """전 단계 실행 → (dedup 후 후보 리스트, counts). 스케일 가드 판정은 호출자 몫."""
    counts = {
        "scanned": 0, "done": 0, "opted_out": 0, "no_video": 0,
        "s3_missing": 0, "deduped": 0, "final": 0,
    }
    raw: list[dict] = []
    for uid, analysis_id, doc in iter_candidate_docs(db, limit=limit):
        counts["scanned"] += 1
        if doc.get("status") != "done":
            continue
        counts["done"] += 1
        if not consent_allows(doc, bulk_approval=bulk_approval):
            counts["opted_out"] += 1
            continue
        key = derive_upload_key(uid, analysis_id, doc)
        if not key:
            counts["no_video"] += 1
            continue
        etag = fetch_etag(s3, bucket, key)
        if etag is None:
            counts["s3_missing"] += 1
            continue
        raw.append(build_candidate(uid, analysis_id, doc, etag))
    known = known_manifest_etags(manifest, s3, bucket)
    final = dedup_candidates(raw, known)
    counts["deduped"] = len(raw) - len(final)
    counts["final"] = len(final)
    return final, counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="내부 fault 트랙 열거 (처방 B — belle 2026-07-13 일괄승인)"
    )
    parser.add_argument("--out", help="후보 JSON 산출 경로 (리포 밖 필수 — uid 포함 중간산출물)")
    parser.add_argument("--bulk-approval", action="store_true",
                        help="belle 일괄승인 발동 — learningOptIn 부재 + 컷오프 이전 문서 통과")
    parser.add_argument("--limit", type=int, default=0, help="문서 상한 (0=전체)")
    parser.add_argument("--force", action="store_true", help="스케일 가드(100~500) 우회")
    parser.add_argument("--bucket", default=_DEFAULT_BUCKET)
    parser.add_argument("--dry-run", action="store_true", help="계수 요약만 — 파일 미기록")
    parser.add_argument(
        "--manifest",
        default=str(_BACKEND / "training" / "data" / "manifest.json"),
    )
    args = parser.parse_args(argv)

    if not args.dry_run:
        if not args.out:
            parser.error("--out 필수 (dry-run 이 아니면). 후보 JSON 은 리포 밖 경로만.")
        if out_path_inside_repo(args.out):
            print(f"[fatal] --out={args.out} 이 리포 안 — uid 포함 중간산출물은 리포 기록 금지")
            return 1

    import boto3  # lazy

    from sunity_shared import firestore_admin as fa

    db = fa._db()
    s3 = boto3.client("s3", region_name="ap-northeast-2")
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    candidates, counts = enumerate_candidates(
        db, s3, manifest,
        bulk_approval=args.bulk_approval, bucket=args.bucket, limit=args.limit,
    )

    print("[counts]", json.dumps(counts, ensure_ascii=False))
    if args.dry_run:
        if not scale_guard(counts["final"]):
            print(f"[warn] final={counts['final']} 이 스케일 가드(100~500) 밖 — 본실행은 --force 필요")
        return 0

    if not scale_guard(counts["final"]) and not args.force:
        print(
            f"[halt] final={counts['final']} 이 스케일 가드({SCALE_GUARD_LO}~{SCALE_GUARD_HI}) "
            "밖 — 계수만 출력하고 정지 (T-Q13-04). 우회는 --force."
        )
        return 1

    payload = {
        "_meta": {
            "script_version": SCRIPT_VERSION,
            "generated_at": int(time.time()),
            "bulk_approval": bool(args.bulk_approval),
            "counts": counts,
        },
        "candidates": candidates,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[ok] wrote {out} final={counts['final']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
