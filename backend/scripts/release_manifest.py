"""C+M3 substrate 릴리스 매니페스트 — 기질(substrate)을 하나의 튜플로 묶는다.

배경 (`.planning/debug/ref-student-substrate-gap.md`):
  C+M3 는 개별 변경의 합이 아니라 **하나의 튜플로서만** 유효하다 —
  {9fps 재추출 reference, PR_INVERSION_ENABLED=1, M3 코드, 파생 필드}.
  이 매니페스트가 그 튜플을 명시적으로 만들어, 활성화(33-07)와 롤백이
  **원자적으로 같은 튜플** 위에서 동작하게 한다 (codex suggestion 2 / D-31).

튜플 (9 필드):
  candidateVersion            후보 reference 버전 id (예: phase33-cm3-run1)
  perDocHashes                {motion_id → content SHA-256} (11 doc)
  commitSha                   재추출을 만든 코드 커밋 SHA
  targetFps                   9.0 (M1 해소)
  prInversionEnabled          True (M6 해소)
  rtmwDeterministic           True (R-4 재현성)
  derivedFieldSchemaVersion   파생 필드 스키마 버전
  verificationResult          None | {"status": "PASS"|"FAIL", ...}
  updatedAt                   ISO8601 UTC

서브커맨드:
  create   --candidate --commit [--out]   11 candidate doc 을 읽어 매니페스트 JSON 생성
  update   --manifest --set k=v ...        필드 갱신(주로 verificationResult) 후 재기록
  verify   --manifest                       11 doc 해시 재계산 → 불일치/불완전 시 non-zero
  publish  --manifest                       검증 후 reference/_release 로 튜플 각인(활성화 소스)

설계 규율:
  · 채점 무접촉 (D-20/D-29) — 매니페스트/게이트/헬스는 릴리스 배관일 뿐.
  · Firestore 클라이언트는 firestore_admin._db() 재사용 — 클라이언트 hand-roll 금지.
  · read/verify 전용. 유일한 write 는 명시적 `publish` (reference/_release).
  · doc_content_hash 는 결정적·키 순서 무관 — 33-07 flip 의 post-write verify 가
    같은 함수로 재계산해 부분 활성화를 잡는다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone

# reference-library-phase4-all11 — 11 종 전량 (default 5-subset 금지).
MOTION_IDS: list[str] = [
    "ref-climb",
    "ref-foxtop",
    "ref-foxtop-split",
    "ref-invert",
    "ref-sideway-spin",
    "ref-combo",
    "ref-elbow-twist-sister",
    "ref-kip-up",
    "ref-pdshape",
    "ref-peter-pan",
    "ref-power-spin",
]

DEFAULT_TARGET_FPS: float = 9.0
DERIVED_FIELD_SCHEMA_VERSION: str = "phase33-cm3-v1"
RELEASE_POINTER_ID: str = "_release"

# verify/complete 판정에 요구되는 non-null 스칼라 필드 (perDocHashes 는 별도 count 검사).
_REQUIRED_SCALAR_FIELDS: tuple[str, ...] = (
    "candidateVersion",
    "commitSha",
    "targetFps",
    "prInversionEnabled",
    "rtmwDeterministic",
    "derivedFieldSchemaVersion",
)


class ManifestError(Exception):
    """매니페스트 무결성 위반 — 불완전/불일치 튜플. publish 는 이 예외로 중단된다."""


# ─────────────────────── content hash ───────────────────────


def _canonical_json(obj: object) -> str:
    """키 순서 무관·결정적 직렬화. Firestore 타임스탬프 등 비직렬화 타입은 str 로 강등.

    sort_keys 로 dict 키 순서를, separators 로 공백을 제거해 같은 내용이면 같은
    바이트열이 되게 한다 (33-07 flip 이 같은 함수로 재계산 → 해시 대조 가능).
    """
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
    )


def doc_content_hash(doc: dict) -> str:
    """candidate 버전 doc 의 content SHA-256 (hex). 키 순서·공백 무관."""
    return hashlib.sha256(_canonical_json(doc).encode("utf-8")).hexdigest()


# ─────────────────────── db seam ───────────────────────


def _resolve_db():
    """운영 Firestore 클라이언트. firestore_admin._db() 재사용 (hand-roll 금지).

    테스트는 이 함수를 monkeypatch 로 fake db 로 치환한다.
    """
    from sunity_shared import firestore_admin

    return firestore_admin._db()


def _version_snapshot(db, motion_id: str, candidate: str):
    """reference/{motion_id}/versions/{candidate} 스냅샷."""
    return (
        db.collection("reference")
        .document(motion_id)
        .collection("versions")
        .document(candidate)
        .get()
    )


def compute_per_doc_hashes(candidate: str, *, db, motion_ids: list[str] | None = None) -> dict[str, str]:
    """11 candidate doc 을 읽어 per-doc content 해시를 계산.

    Raises:
        ManifestError: candidate 버전 doc 이 하나라도 없을 때.
    """
    ids = motion_ids if motion_ids is not None else MOTION_IDS
    hashes: dict[str, str] = {}
    missing: list[str] = []
    for mid in ids:
        snap = _version_snapshot(db, mid, candidate)
        if not getattr(snap, "exists", False):
            missing.append(mid)
            continue
        hashes[mid] = doc_content_hash(snap.to_dict())
    if missing:
        raise ManifestError(
            f"candidate={candidate!r} 버전 doc 누락: {missing} "
            f"(reference/{{id}}/versions/{candidate})"
        )
    return hashes


# ─────────────────────── build / verify ───────────────────────


def create_manifest(
    *,
    candidate: str,
    commit: str,
    db,
    target_fps: float = DEFAULT_TARGET_FPS,
    pr_inversion: bool = True,
    rtmw_deterministic: bool = True,
    schema_version: str = DERIVED_FIELD_SCHEMA_VERSION,
    motion_ids: list[str] | None = None,
) -> dict:
    """11 candidate doc 을 읽어 릴리스 튜플을 만든다 (verificationResult=None)."""
    per_doc_hashes = compute_per_doc_hashes(candidate, db=db, motion_ids=motion_ids)
    return {
        "candidateVersion": candidate,
        "perDocHashes": per_doc_hashes,
        "commitSha": commit,
        "targetFps": target_fps,
        "prInversionEnabled": bool(pr_inversion),
        "rtmwDeterministic": bool(rtmw_deterministic),
        "derivedFieldSchemaVersion": schema_version,
        "verificationResult": None,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


def check_tuple_complete(manifest: dict, *, motion_ids: list[str] | None = None) -> list[str]:
    """튜플 완전성 검사. 문제 목록 반환(빈 리스트 = 완전).

    verificationResult 는 None 을 허용한다(create 직후 미검증 상태). 나머지 스칼라
    필드는 non-null 필수 + perDocHashes 는 11 종 전량이 있어야 한다.
    """
    ids = motion_ids if motion_ids is not None else MOTION_IDS
    problems: list[str] = []
    for field in _REQUIRED_SCALAR_FIELDS:
        if manifest.get(field) in (None, ""):
            problems.append(f"불완전 튜플: {field} 누락/빈값")
    hashes = manifest.get("perDocHashes")
    if not isinstance(hashes, dict):
        problems.append("불완전 튜플: perDocHashes 부재/형식 오류")
    else:
        for mid in ids:
            if mid not in hashes or not hashes.get(mid):
                problems.append(f"불완전 튜플: perDocHashes[{mid}] 누락")
    return problems


def verify_manifest(manifest: dict, *, db, motion_ids: list[str] | None = None) -> tuple[bool, list[str]]:
    """튜플 완전성 + 11 doc 해시 재계산 대조.

    Returns:
        (ok, problems). ok=False 이면 problems 에 사유가 담긴다. 매니페스트가
        substrate 활성화/롤백의 단일 진실 원천이므로, doc 조작·불완전 튜플은
        여기서 반드시 걸린다 (D-18).
    """
    ids = motion_ids if motion_ids is not None else MOTION_IDS
    problems: list[str] = check_tuple_complete(manifest, motion_ids=ids)

    candidate = manifest.get("candidateVersion")
    expected = manifest.get("perDocHashes") or {}
    if candidate:
        for mid in ids:
            snap = _version_snapshot(db, mid, candidate)
            if not getattr(snap, "exists", False):
                problems.append(f"{mid}: candidate 버전 doc 부재")
                continue
            actual = doc_content_hash(snap.to_dict())
            want = expected.get(mid)
            if want is None:
                # 완전성 검사에서 이미 보고됨 — 중복 방지.
                continue
            if actual != want:
                problems.append(
                    f"{mid}: content 해시 불일치 (manifest={want[:12]}… actual={actual[:12]}…)"
                )
    return (len(problems) == 0, problems)


# ─────────────────────── publish ───────────────────────


def publish_manifest(manifest: dict, *, db, motion_ids: list[str] | None = None) -> dict:
    """검증 통과 시에만 reference/_release 로 튜플을 각인한다 (활성화 소스).

    verificationResult 를 PASS 로 각인한 뒤 activeCandidate + 매니페스트 전량을
    글로벌 릴리스 포인터 doc 에 쓴다. 33-17 resolver 와 33-07 flip 이 이 doc 을
    소비한다. 부분/불일치 튜플은 ManifestError 로 중단 — 아무 write 도 하지 않는다.
    """
    ok, problems = verify_manifest(manifest, db=db, motion_ids=motion_ids)
    if not ok:
        raise ManifestError(f"publish 차단 — 튜플 검증 실패: {problems}")

    verified_at = datetime.now(timezone.utc).isoformat()
    pointer = dict(manifest)
    pointer["activeCandidate"] = manifest["candidateVersion"]
    pointer["verificationResult"] = {"status": "PASS", "verifiedAt": verified_at}
    pointer["updatedAt"] = verified_at

    db.collection("reference").document(RELEASE_POINTER_ID).set(pointer, merge=False)
    return pointer


# ─────────────────────── local JSON io ───────────────────────


def _write_json(path: str, obj: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ─────────────────────── CLI ───────────────────────


def _coerce_set_value(raw: str):
    """`--set k=v` 의 v 를 JSON 으로 해석 시도(true/false/숫자/null/문자열)."""
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release_manifest",
        description="C+M3 substrate 릴리스 매니페스트 — create/update/verify/publish.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create", help="11 candidate doc → 매니페스트 JSON 생성")
    p_create.add_argument("--candidate", required=True, help="후보 reference 버전 id")
    p_create.add_argument("--commit", required=True, help="재추출 코드 커밋 SHA")
    p_create.add_argument("--target-fps", type=float, default=DEFAULT_TARGET_FPS)
    p_create.add_argument("--schema-version", default=DERIVED_FIELD_SCHEMA_VERSION)
    p_create.add_argument("--out", required=True, help="매니페스트 JSON 출력 경로")

    p_update = sub.add_parser("update", help="매니페스트 필드 갱신 후 재기록")
    p_update.add_argument("--manifest", required=True)
    p_update.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="필드 갱신 (예: verificationResult='{\"status\":\"PASS\"}')",
    )

    p_verify = sub.add_parser("verify", help="11 doc 해시 재계산 → 불일치/불완전 시 non-zero")
    p_verify.add_argument("--manifest", required=True)

    p_publish = sub.add_parser("publish", help="검증 후 reference/_release 로 튜플 각인")
    p_publish.add_argument("--manifest", required=True)

    args = parser.parse_args(argv)

    if args.cmd == "create":
        db = _resolve_db()
        try:
            manifest = create_manifest(
                candidate=args.candidate,
                commit=args.commit,
                db=db,
                target_fps=args.target_fps,
                schema_version=args.schema_version,
            )
        except ManifestError as exc:
            print(f"create 실패: {exc}", file=sys.stderr)
            return 1
        _write_json(args.out, manifest)
        print(f"매니페스트 생성 → {args.out} (candidate={args.candidate})")
        return 0

    if args.cmd == "update":
        manifest = _load_json(args.manifest)
        for pair in args.set:
            if "=" not in pair:
                print(f"--set 형식 오류(KEY=VALUE): {pair!r}", file=sys.stderr)
                return 2
            key, raw = pair.split("=", 1)
            manifest[key] = _coerce_set_value(raw)
        manifest["updatedAt"] = datetime.now(timezone.utc).isoformat()
        _write_json(args.manifest, manifest)
        print(f"매니페스트 갱신 → {args.manifest}")
        return 0

    if args.cmd == "verify":
        manifest = _load_json(args.manifest)
        db = _resolve_db()
        ok, problems = verify_manifest(manifest, db=db)
        if ok:
            print(f"verify PASS — candidate={manifest.get('candidateVersion')} 11/11 해시 일치")
            return 0
        print("verify FAIL:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    if args.cmd == "publish":
        manifest = _load_json(args.manifest)
        db = _resolve_db()
        try:
            pointer = publish_manifest(manifest, db=db)
        except ManifestError as exc:
            print(f"publish 차단: {exc}", file=sys.stderr)
            return 1
        # 검증 결과를 로컬 매니페스트에도 반영.
        manifest["verificationResult"] = pointer["verificationResult"]
        manifest["updatedAt"] = pointer["updatedAt"]
        _write_json(args.manifest, manifest)
        print(
            f"publish 완료 → reference/{RELEASE_POINTER_ID}.activeCandidate="
            f"{pointer['activeCandidate']}"
        )
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
