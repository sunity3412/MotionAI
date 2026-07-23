"""reference/{id} 11 doc 전량 백업 — C+M3 substrate 트랙 Task 0 (SEED `## 롤백 설계`).

어떤 재처리 write 보다 **먼저** 실행한다. SEED 불변식: "백업 JSON 이 없으면 어떤
write 도 금지." 이 스크립트는 롤백 원천(D-31)이 **존재만** 하는 게 아니라 **바이트
충실**하고 **복원 가능**함을 백업 시점에 증명한다 (codex concern 10 / suggestion 8):

  1. 읽기 전용 dump — reference 컬렉션에 어떤 set/update/delete 도 하지 않는다.
     (rehearsal 은 별도 격리 컬렉션 `reference_restore_rehearsal` 에만 쓴다 — 실
      reference 무접촉.)
  2. TEMP-then-atomic-rename — 직렬화 산출을 `{out}.tmp` 에 먼저 쓰고 4-check
     무결성 게이트 통과 후에만 `{out}` (백업 glob `reference-11-preC-*.json` 에
     매칭되는 유일한 이름)으로 os.replace. 실패한 dump 는 `{out}.FAILED`
     (백업 glob 에 매칭 안 되는 이름)로 떨어뜨리고 non-zero exit — 잘린/부분
     백업이 백업 행세를 할 수 없다 (concern 10).
  3. whole-file SHA-256 — 백업 파일 전체 바이트 해시를 계산해 S3 object Metadata
     로 올리고, S3 object 를 **재다운로드**해 로컬 파일과 **바이트 비교**한다
     (suggestion 8). S3 사본이 로컬과 다르면 non-zero.
  4. restore rehearsal — `--rehearse-restore` 시 백업 JSON 을 격리 컬렉션에
     set(merge=False) 로 복원하고, 읽어들여 원본과 바이트 비교한다 (round-trip
     증명, suggestion 8). 실 reference 는 절대 건드리지 않는다.

4-check 무결성 게이트 (SEED `## 롤백 설계 / 백업 무결성 게이트`):
  (1) 11/11 doc 존재 · isActive=True · activeVersion=='phase4_v1'
  (2) anglesFrames == joints3dFrames == keypointReport.frames
  (3) len(angles) == anglesFrames × len(anglesJointKeys);
      len(joints3d) == joints3dFrames × len(joints3dKeys) × coordDim(3)
  (4) doc 별 SHA-256 + whole-file SHA-256 기록
  → 하나라도 실패하면 *.FAILED + non-zero (재처리 착수 금지).

크리덴셜 (하드코딩 금지 — CLAUDE.md / Parameter Store):
  Firestore: FIREBASE_SA_PATH=../firebase-sa.json (로컬 SA)
  AWS S3   : AWS_PROFILE=sunity-motion (또는 표준 boto3 크리덴셜 체인)

실행 (백업 + S3 검증 + rehearsal 한 번에):
  cd backend && PYTHONPATH=shared/python:. FIREBASE_SA_PATH=../firebase-sa.json \
    AWS_PROFILE=sunity-motion python3 scripts/backup_reference_docs.py \
      --motions ref-climb ref-foxtop ref-foxtop-split ref-invert ref-sideway-spin \
                ref-combo ref-elbow-twist-sister ref-kip-up ref-pdshape \
                ref-peter-pan ref-power-spin \
      --out ../.planning/debug/backups/reference-11-preC-$(date +%Y%m%d-%H%M%S).json \
      --rehearse-restore

rehearsal 만 (기존 백업 대상):
  cd backend && PYTHONPATH=shared/python:. FIREBASE_SA_PATH=../firebase-sa.json \
    python3 scripts/backup_reference_docs.py --rehearse-restore \
      --from-backup ../.planning/debug/backups/reference-11-preC-<ts>.json

[per [[reference-library-phase4-all11]], [[aws-keys-and-bucket]], SEED 롤백 설계,
 33-REVIEWS codex concern 10 / suggestion 8, D-11/D-18/D-19/D-25/D-26/D-27/D-31]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import glob as _glob
import hashlib
import json
import os
import sys
from pathlib import Path

# sys.path 주입 — shared/python layer (dump_analysis_doc.py / measure_reference_fps.py 패턴).
HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent  # scripts/ → backend
for _p in (BACKEND / "shared" / "python", BACKEND):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared import models as _models  # noqa: E402

# ── 11-id 전체 motion 상수 ([[reference-library-phase4-all11]], measure_reference_fps 정합) ──
# 절대 5-subset default 금지 — 전 active doc 백업이 롤백 원천 성립 조건.
ALL_MOTION_IDS: tuple[str, ...] = (
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
)

EXPECTED_ACTIVE_VERSION = "phase4_v1"
COORD_DIM = 3
BACKUP_GLOB_STEM = "reference-11-preC-"  # 백업 glob = reference-11-preC-*.json
S3_BUCKET_DEFAULT = "sunity-motion-pilot-videos"
S3_PREFIX = "backups/"
# 격리 복원 리허설 컬렉션 — 실 reference 와 절대 겹치면 안 됨 (T-33-20 방어).
REHEARSAL_COLLECTION_DEFAULT = "reference_restore_rehearsal"

# 실 reference 컬렉션이 single-field 인덱스에서 면제한 필드 (콘솔에서 owner 가 설정,
# [[firestore-index-entry-limit]] / [[analyses-index-exemption-fix]]). 대형 flat 배열이
# 40k index-entry 한도를 넘기지 않도록 자동 인덱싱을 끈다. 격리 리허설 컬렉션은 이
# 면제가 없으면 set(merge=False) 이 400 INDEX_ENTRIES_COUNT_LIMIT_EXCEEDED 로 실패한다
# → 실 restore 경로(면제된 reference/{id})와 동형이 되도록 같은 면제를 복제한다.
REFERENCE_EXEMPT_FIELDS: tuple[str, ...] = ("angles", "joints3d", "keypointReport")


def _canon(obj) -> bytes:
    """결정론적 canonical 직렬화 — sort_keys 로 Firestore 키 순서 무관 바이트 비교.

    Firestore Timestamp 등 non-JSON 값은 default=str 로 문자열화 (롤백 원천은
    JSON-표현 가능 형상으로 고정한다 — set(merge=False) 복원 시 문자열로 저장/복귀,
    round-trip 일관).
    """
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── 읽기 전용 fetch ─────────────────────────────────────────────────────────────


def _fetch_docs(motions: tuple[str, ...]) -> dict[str, dict | None]:
    """reference/{id} 전량 read-only fetch (get 만 — 어떤 write 도 없음)."""
    docs: dict[str, dict | None] = {}
    for mid in motions:
        docs[mid] = fa.get_reference_motion(mid)  # read-only get
    return docs


# ── 4-check 무결성 게이트 ────────────────────────────────────────────────────────


def _int_or_none(value) -> int | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _integrity_gate(
    motions: tuple[str, ...], docs: dict[str, dict | None]
) -> tuple[bool, list[str], list[str]]:
    """4-check 게이트. (전체 PASS 여부, 통과 요약, 실패 사유) 반환.

    실패를 삼키지 않고 사유를 그대로 축적한다 (D-18: 틀리면 걸리는 장치).
    """
    passes: list[str] = []
    failures: list[str] = []

    # ── check 1: 11/11 doc + isActive + activeVersion ──
    present = [m for m in motions if docs.get(m) is not None]
    if len(present) != len(motions):
        missing = [m for m in motions if docs.get(m) is None]
        failures.append(f"check1: 결측 doc {missing} ({len(present)}/{len(motions)})")
    else:
        passes.append(f"check1a: {len(present)}/{len(motions)} doc 전량 존재")
        bad_active = [
            m for m in motions if docs[m].get("isActive") is not True  # type: ignore[union-attr]
        ]
        bad_version = [
            m
            for m in motions
            if docs[m].get("activeVersion") != EXPECTED_ACTIVE_VERSION  # type: ignore[union-attr]
        ]
        if bad_active:
            failures.append(f"check1: isActive!=True → {bad_active}")
        else:
            passes.append("check1b: 11/11 isActive=True")
        if bad_version:
            detail = {m: docs[m].get("activeVersion") for m in bad_version}  # type: ignore[union-attr]
            failures.append(
                f"check1: activeVersion!={EXPECTED_ACTIVE_VERSION!r} → {detail}"
            )
        else:
            passes.append(f"check1c: 11/11 activeVersion=={EXPECTED_ACTIVE_VERSION!r}")

    # doc 결측이면 이후 검사 불가 — 조기 반환.
    if len(present) != len(motions):
        return False, passes, failures

    # ── check 2: anglesFrames == joints3dFrames == keypointReport.frames ──
    frames_ok = True
    for m in motions:
        doc = docs[m] or {}
        af = _int_or_none(doc.get("anglesFrames"))
        jf = _int_or_none(doc.get("joints3dFrames"))
        kr = doc.get("keypointReport") or {}
        krf = _int_or_none(kr.get("frames")) if isinstance(kr, dict) else None
        if af is None or jf is None or krf is None:
            frames_ok = False
            failures.append(
                f"check2[{m}]: frames 결측/비정수 "
                f"anglesFrames={doc.get('anglesFrames')!r} "
                f"joints3dFrames={doc.get('joints3dFrames')!r} "
                f"keypointReport.frames={kr.get('frames') if isinstance(kr, dict) else None!r}"
            )
            continue
        if not (af == jf == krf):
            frames_ok = False
            failures.append(
                f"check2[{m}]: frames 불일치 angles={af} joints3d={jf} keypoint={krf}"
            )
    if frames_ok:
        passes.append("check2: 11/11 anglesFrames==joints3dFrames==keypointReport.frames")

    # ── check 3: 배열 길이 == frames × keys × dim ──
    len_ok = True
    for m in motions:
        doc = docs[m] or {}
        af = _int_or_none(doc.get("anglesFrames"))
        angles = doc.get("angles")
        akeys = doc.get("anglesJointKeys")
        jf = _int_or_none(doc.get("joints3dFrames"))
        joints3d = doc.get("joints3d")
        jkeys = doc.get("joints3dKeys")
        coord = _int_or_none(doc.get("coordDim"))
        if not isinstance(angles, list) or not isinstance(akeys, list) or af is None:
            len_ok = False
            failures.append(f"check3[{m}]: angles/anglesJointKeys/anglesFrames 형상 결측")
        else:
            expect_a = af * len(akeys)
            if len(angles) != expect_a:
                len_ok = False
                failures.append(
                    f"check3[{m}]: len(angles)={len(angles)} != "
                    f"anglesFrames({af})×keys({len(akeys)})={expect_a}"
                )
        if (
            not isinstance(joints3d, list)
            or not isinstance(jkeys, list)
            or jf is None
            or coord is None
        ):
            len_ok = False
            failures.append(
                f"check3[{m}]: joints3d/joints3dKeys/joints3dFrames/coordDim 형상 결측"
            )
        else:
            expect_j = jf * len(jkeys) * coord
            if len(joints3d) != expect_j:
                len_ok = False
                failures.append(
                    f"check3[{m}]: len(joints3d)={len(joints3d)} != "
                    f"joints3dFrames({jf})×keys({len(jkeys)})×dim({coord})={expect_j}"
                )
    if len_ok:
        passes.append("check3: 11/11 angles+joints3d 배열 길이 정합")

    # ── check 4 는 해시 계산으로 별도 충족 (per-doc + whole-file SHA-256) ──
    passes.append("check4: per-doc SHA-256 + whole-file SHA-256 기록 (아래 참조)")

    ok = not failures
    return ok, passes, failures


# ── 백업 파일 조립 + temp-then-rename + S3 ────────────────────────────────────────


def _build_backup_object(
    motions: tuple[str, ...],
    docs: dict[str, dict | None],
    per_doc_sha256: dict[str, str],
    gate_passes: list[str],
    gate_failures: list[str],
) -> dict:
    return {
        "header": {
            "kind": "reference-11-preC-backup",
            "createdAtUtc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "expectedActiveVersion": EXPECTED_ACTIVE_VERSION,
            "coordDim": COORD_DIM,
            "motions": list(motions),
            "count": len([m for m in motions if docs.get(m) is not None]),
            "perDocSha256": per_doc_sha256,
            "integrityPasses": gate_passes,
            "integrityFailures": gate_failures,
            "schemaNote": (
                "docs[id] = reference/{id} full top-level dict (read-only get). "
                "복원은 set(merge=False) 통째 복원 (SEED 복원 절차 3)."
            ),
        },
        "docs": {m: docs[m] for m in motions},
    }


def _s3_upload_and_verify(
    local_path: Path, whole_sha256: str, bucket: str
) -> dict:
    """put_object(Metadata=sha256) → 재다운로드 → 바이트 비교 (suggestion 8).

    성공 시 결과 dict 반환. 실패 시 예외 (D-18 — 삼키지 않음).
    """
    import boto3  # lazy — AWS 크리덴셜 없는 환경에서 --skip-s3 로 우회 가능.

    key = f"{S3_PREFIX}{local_path.name}"
    s3 = boto3.client("s3")
    local_bytes = local_path.read_bytes()

    # 업로드 — whole-file SHA-256 을 object Metadata 로 박제.
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=local_bytes,
        Metadata={"sha256": whole_sha256},
        ContentType="application/json",
    )

    # 재다운로드 — 저장 Metadata + 실제 바이트 둘 다 검증.
    obj = s3.get_object(Bucket=bucket, Key=key)
    downloaded = obj["Body"].read()
    stored_meta_sha = (obj.get("Metadata") or {}).get("sha256")
    downloaded_sha = _sha256_hex(downloaded)

    if stored_meta_sha != whole_sha256:
        raise RuntimeError(
            f"S3 metadata sha256 불일치: stored={stored_meta_sha!r} "
            f"expected={whole_sha256!r} (T-33-21)"
        )
    if downloaded != local_bytes:
        raise RuntimeError(
            f"S3 재다운로드 바이트 != 로컬 바이트 "
            f"(local_sha={whole_sha256} downloaded_sha={downloaded_sha}) (T-33-21)"
        )
    return {
        "bucket": bucket,
        "key": key,
        "uri": f"s3://{bucket}/{key}",
        "storedMetadataSha256": stored_meta_sha,
        "downloadedSha256": downloaded_sha,
        "localSha256": whole_sha256,
        "byteCompare": "PASS",
    }


def _run_backup(args: argparse.Namespace) -> tuple[int, Path | None, str | None]:
    """백업 mode. (exit_code, backup_path_or_None, whole_sha256_or_None) 반환."""
    motions = tuple(args.motions)
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 78, flush=True)
    print("backup_reference_docs — 읽기 전용 dump + 4-check gate (채점 무접촉, D-20)", flush=True)
    print(f"  motions = {len(motions)} ids", flush=True)
    print(f"  out     = {out}", flush=True)
    creds = os.environ.get("FIREBASE_SA_PATH") or os.environ.get("FIREBASE_SA_PARAM")
    print(f"  creds   = FIREBASE_SA_PATH/PARAM -> {creds!r}", flush=True)
    print("=" * 78, flush=True)

    docs = _fetch_docs(motions)
    per_doc_sha256: dict[str, str] = {
        m: _sha256_hex(_canon(docs[m])) for m in motions if docs.get(m) is not None
    }

    ok, passes, failures = _integrity_gate(motions, docs)

    backup_obj = _build_backup_object(motions, docs, per_doc_sha256, passes, failures)
    file_bytes = _canon(backup_obj)
    whole_sha256 = _sha256_hex(file_bytes)

    tmp_path = out.with_name(out.name + ".tmp")
    tmp_path.write_bytes(file_bytes)

    print("\n### 4-check 무결성 게이트", flush=True)
    for p in passes:
        print(f"  PASS  {p}", flush=True)
    for f in failures:
        print(f"  FAIL  {f}", flush=True)
    print(f"  whole-file SHA-256 = {whole_sha256}", flush=True)

    if not ok:
        # 실패 dump — 백업 glob 에 매칭 안 되는 *.FAILED 로 (concern 10).
        failed_path = out.with_name(out.name + ".FAILED")
        os.replace(tmp_path, failed_path)
        print(
            f"\nGATE FAIL — {failed_path} 로 격리 (백업 glob 미매칭). "
            f"재처리 착수 금지 (SEED). 33-03 blocked.",
            flush=True,
        )
        return 3, None, None

    # PASS — atomic rename tmp → out (백업 glob 매칭 유일 이름).
    os.replace(tmp_path, out)
    # MANIFEST 이름은 백업 stem 기반 (`{stem}.MANIFEST.json`) — `{name}.MANIFEST.json`
    # (= `...json.MANIFEST.json`)는 백업 glob `reference-11-preC-*.json` 에 매칭되며
    # sorted()[-1] 에서 백업 대신 잡히는 함정을 만든다. stem 기반은 'M' < 'j' 라 백업보다
    # 먼저 정렬돼 백업 조회를 오염시키지 않는다.
    manifest_path = out.with_name(out.stem + ".MANIFEST.json")
    manifest = {
        "status": "PASS",
        "backupPath": str(out),
        "wholeFileSha256": whole_sha256,
        "perDocSha256": per_doc_sha256,
        "integrityPasses": passes,
        "count": len(per_doc_sha256),
        "s3Target": f"s3://{args.s3_bucket}/{S3_PREFIX}{out.name}",
        "createdAtUtc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }

    s3_result: dict | None = None
    if args.skip_s3:
        print("\n### S3 업로드 SKIP (--skip-s3)", flush=True)
    else:
        print("\n### S3 업로드 + 재다운로드 바이트 비교", flush=True)
        s3_result = _s3_upload_and_verify(out, whole_sha256, args.s3_bucket)
        manifest["s3"] = s3_result
        print(f"  uri              = {s3_result['uri']}", flush=True)
        print(f"  stored metadata  = {s3_result['storedMetadataSha256']}", flush=True)
        print(f"  downloaded sha   = {s3_result['downloadedSha256']}", flush=True)
        print(f"  local sha        = {s3_result['localSha256']}", flush=True)
        print(f"  byte-compare     = {s3_result['byteCompare']}", flush=True)

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nGATE PASS — 백업 {out}", flush=True)
    print(f"  manifest = {manifest_path}", flush=True)
    return 0, out, whole_sha256


# ── restore rehearsal (격리 컬렉션 round-trip) ─────────────────────────────────────


def _resolve_rehearsal_source(args: argparse.Namespace, fresh: Path | None) -> Path | None:
    if args.from_backup:
        return Path(args.from_backup).resolve()
    if fresh is not None:
        return fresh
    # 최신 백업 glob 자동 탐색.
    out_dir = Path(args.out).resolve().parent if args.out else Path.cwd()
    matches = sorted(_glob.glob(str(out_dir / f"{BACKUP_GLOB_STEM}*.json")))
    matches = [m for m in matches if not m.endswith(".FAILED")]
    return Path(matches[-1]) if matches else None


def _ensure_rehearsal_exemptions(collection: str) -> list[str]:
    """격리 리허설 컬렉션에 실 reference 와 동일한 single-field 인덱스 면제를 건다.

    대형 flat 배열(angles/joints3d/keypointReport)의 자동 인덱싱을 꺼 40k index-entry
    한도(400 INDEX_ENTRIES_COUNT_LIMIT_EXCEEDED)를 피한다 — 실 restore 경로가 향하는
    reference/{id}(면제됨)와 동형으로 만든다. FirestoreAdminClient 를 SA 크리덴셜로
    구성하며, 각 field override 는 long-running op 라 완료까지 대기한다. 멱등
    (이미 면제면 같은 config 재적용). 반환: 면제 적용한 field path 목록.
    """
    sa_path = os.environ.get("FIREBASE_SA_PATH")
    if not sa_path or not Path(sa_path).is_file():
        raise RuntimeError(
            "인덱스 면제 설정에는 FIREBASE_SA_PATH(로컬 SA 파일)가 필요하다 — "
            f"현재 값 {sa_path!r} 파일 없음 (D-18)."
        )
    from google.cloud import firestore_admin_v1
    from google.oauth2 import service_account

    project = json.loads(Path(sa_path).read_text())["project_id"]
    creds = service_account.Credentials.from_service_account_file(sa_path)
    client = firestore_admin_v1.FirestoreAdminClient(credentials=creds)

    applied: list[str] = []
    for field in REFERENCE_EXEMPT_FIELDS:
        name = (
            f"projects/{project}/databases/(default)/collectionGroups/"
            f"{collection}/fields/{field}"
        )
        # indexes=[] + uses_ancestor_config=False = 이 필드 single-field 인덱스 면제.
        fld = firestore_admin_v1.Field(
            name=name,
            index_config=firestore_admin_v1.Field.IndexConfig(
                indexes=[], uses_ancestor_config=False
            ),
        )
        op = client.update_field(request=firestore_admin_v1.UpdateFieldRequest(field=fld))
        op.result(timeout=180)  # long-running op 완료 대기 (빈 컬렉션이라 신속).
        applied.append(f"{collection}/{field}")
        print(f"  인덱스 면제 적용: {collection}/{field}", flush=True)
    return applied


def _rehearse_restore(source: Path, collection: str, keep: bool) -> int:
    """백업 JSON 을 격리 컬렉션에 set(merge=False) 복원 → 읽어 바이트 비교 (round-trip).

    실 reference 컬렉션 무접촉 (guard). 성공 0 / 실패 non-zero (D-18).
    """
    if collection == _models.REFERENCE_MOTIONS_COLLECTION:
        raise RuntimeError(
            f"rehearsal collection={collection!r} 이 실 reference 컬렉션과 동일 — "
            f"실 데이터 오염 방지로 중단 (T-33-20)."
        )

    print("=" * 78, flush=True)
    print("restore rehearsal — 격리 컬렉션 round-trip 바이트 비교 (실 reference 무접촉)", flush=True)
    print(f"  source     = {source}", flush=True)
    print(f"  collection = {collection}/ (격리)", flush=True)
    print("=" * 78, flush=True)

    payload = json.loads(source.read_text(encoding="utf-8"))
    docs = payload.get("docs") or {}
    if not docs:
        print("REHEARSAL FAIL — 백업 docs 비어 있음 (D-18).", flush=True)
        return 4

    # 리허설 백엔드 선택:
    #  · FIRESTORE_EMULATOR_HOST 설정 시 → 로컬 에뮬레이터 (40k index-entry 한도 미적용,
    #    실 프로젝트 무접촉 — 완전 격리, plan 이 명시 허용한 경로).
    #  · 미설정 시 → 실 Firestore 격리 컬렉션. 이때만 실 reference 와 동일한 인덱스
    #    면제를 복제해야 40k 한도(400 INDEX_ENTRIES_COUNT_LIMIT_EXCEEDED)를 피한다.
    emulator = os.environ.get("FIRESTORE_EMULATOR_HOST")
    if emulator:
        print(f"### 에뮬레이터 모드 — FIRESTORE_EMULATOR_HOST={emulator} (실 프로젝트 무접촉)", flush=True)
    else:
        print("### 실 Firestore 격리 컬렉션 — 인덱스 면제 복제 (angles/joints3d/keypointReport)", flush=True)
        _ensure_rehearsal_exemptions(collection)

    results: list[tuple[str, bool, str]] = []
    written: list[str] = []
    for mid, doc in docs.items():
        if doc is None:
            results.append((mid, False, "backup doc None"))
            continue
        path = f"{collection}/{mid}"
        # 격리 컬렉션에만 write — set(merge=False) 통째 복원 (SEED 복원 절차 3 재현).
        fa._doc(path).set(doc, merge=False)
        written.append(path)
        snap = fa._doc(path).get()
        restored = snap.to_dict() if snap.exists else None
        match = _canon(restored) == _canon(doc)
        results.append((mid, match, "byte-match" if match else "MISMATCH"))

    for mid, match, note in results:
        print(f"  {'PASS' if match else 'FAIL'}  {mid}: {note}", flush=True)

    # 정리 — 격리 doc 삭제 (best-effort, 실패는 노출).
    if not keep:
        for path in written:
            try:
                fa._doc(path).delete()
            except Exception as exc:  # noqa: BLE001 — 정리 실패 노출 (D-18)
                print(f"  CLEANUP WARN {path}: {exc!r}", flush=True)
        print(f"  격리 컬렉션 {collection}/ {len(written)} doc 삭제 (정리)", flush=True)
    else:
        print(f"  --keep-rehearsal — 격리 doc {len(written)}개 보존", flush=True)

    all_pass = all(match for _, match, _ in results) and len(results) == len(docs)
    print(
        f"\nREHEARSAL {'PASS' if all_pass else 'FAIL'} — "
        f"{sum(1 for _, m, _ in results if m)}/{len(results)} round-trip 바이트 일치",
        flush=True,
    )
    return 0 if all_pass else 5


# ── main ────────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description="reference 11 doc 백업 (읽기 전용) + 무결성/복원 증명")
    ap.add_argument("--motions", nargs="+", default=list(ALL_MOTION_IDS))
    ap.add_argument("--out", default=None, help="백업 출력 경로 (백업 mode 필수)")
    ap.add_argument("--s3-bucket", default=S3_BUCKET_DEFAULT)
    ap.add_argument("--skip-s3", action="store_true", help="S3 업로드/검증 생략 (AWS 크리덴셜 없는 환경)")
    ap.add_argument(
        "--rehearse-restore",
        action="store_true",
        help="백업 후 (또는 --from-backup 대상) 격리 복원 round-trip 리허설 실행",
    )
    ap.add_argument("--from-backup", default=None, help="rehearsal 원천 백업 JSON (백업 mode 생략 시 rehearsal-only)")
    ap.add_argument("--rehearsal-collection", default=REHEARSAL_COLLECTION_DEFAULT)
    ap.add_argument("--keep-rehearsal", action="store_true", help="리허설 격리 doc 삭제하지 않음")
    args = ap.parse_args()

    # rehearsal-only mode — --from-backup 주고 --out 생략.
    if args.from_backup and not args.out:
        return _rehearse_restore(
            Path(args.from_backup).resolve(),
            args.rehearsal_collection,
            args.keep_rehearsal,
        )

    if not args.out:
        ap.error("--out 필수 (백업 mode). rehearsal-only 는 --from-backup 지정.")

    code, backup_path, _whole = _run_backup(args)
    if code != 0:
        return code

    if args.rehearse_restore:
        source = _resolve_rehearsal_source(args, backup_path)
        if source is None:
            print("REHEARSAL FAIL — 원천 백업 파일을 찾을 수 없음 (D-18).", flush=True)
            return 6
        rc = _rehearse_restore(source, args.rehearsal_collection, args.keep_rehearsal)
        if rc != 0:
            return rc

    return 0


if __name__ == "__main__":
    sys.exit(main())
