"""학습 페어 삭제/철회 이행 스크립트 — 담당 플랜 31-07 (T-31-26 삭제 요청 이행).

사용자가 학습 동의를 철회하거나 삭제를 요청하면, 해당 분석에서 만들어진 [틀린 폼 →
고쳐진 폼] 페어를 저장소에서 **완전히** 지운다. "완전히" 가 어려운 이유가 셋이다:

1. **가명 ID** — 저장소에는 uid/analysisId 원문이 없다. pairId 를 HMAC 으로 다시
   계산해야만 지울 대상을 찾을 수 있다.
2. **키 회전** — 적재 시점의 키가 그 뒤 회전됐을 수 있다. 그래서 active 하나가 아니라
   **key set 의 전 버전**(활성+retired)으로 pairId 를 재계산한다. 그리고 삭제 전에
   inventory gate 를 건다 — 저장소에 남아 있는 meta 의 hmacKeyVersion 중 하나라도 현재
   key set 에 없으면 그 페어는 pairId 를 재계산할 수 없다 = 삭제 불가 고아. 이때는
   지우다 마는 대신 **중단**하고 사람이 키를 복구하게 한다 (3차 H3-11).
3. **joint 이름 변화** — 렌더 계약(ARROW_JOINT_MAP)은 축소될 수 있다. 삭제는 반드시
   append-only 인 `HISTORICAL_PAIR_JOINTS` 를 순회한다 (3차 M3-05).

버킷 versioning: `list_object_versions` 로 **무조건** 열거해 Versions 와 DeleteMarkers 를
versionId 로 지운다. never-versioned 버킷에서도 versionId 는 "null" 로 돌아와 정상
동작하므로 `get_bucket_versioning` 분기가 필요 없다 — 버킷 versioning 설정 API 는
읽기·쓰기 모두 호출하지 않는다(never-versioned 상태는 31-12 hard gate). 단일 key 의
version 이 페이지 경계를 넘길 수 있으므로 NextKeyMarker 와 NextVersionIdMarker 를
**쌍으로** 넘겨 끝까지 돈다 — 하나만 넘기면 그 key 를 되돌아 읽거나 건너뛴다
(3차 H3-08 + 6차 H6-06). 삭제 후 재조회로 current/noncurrent/delete-marker 0 을 확인하고,
잔존이 있으면 비정상 종료한다.

실행:
  # dry-run (목록만, 삭제 0)
  AWS_PROFILE=sunity-motion python backend/scripts/delete_training_pair.py \\
      --uid <uid> --analysis-id <analysisId> --dry-run
  # 실삭제
  AWS_PROFILE=sunity-motion python backend/scripts/delete_training_pair.py \\
      --uid <uid> --analysis-id <analysisId>

비밀값(HMAC 키)은 어떤 경로로도 출력하지 않는다.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))

from sunity_shared.analysis.pair_store import (  # noqa: E402
    HISTORICAL_PAIR_JOINTS,
    HMAC_KEYS_SSM_PARAM,
    PAIRS_BUCKET_DEFAULT,
    iter_pair_prefixes,
    pair_id,
    pair_prefix,
    read_pair_meta_raw,
    validate_hmac_key_set,
)

log = logging.getLogger("delete_training_pair")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

_DELETE_BATCH = 1000


class DeletionAborted(Exception):
    """삭제를 안전하게 끝낼 수 없다 — 부분 삭제 대신 중단한다."""


# ─────────────────────── key set ───────────────────────


def load_key_set(ssm_client, param_name: str = HMAC_KEYS_SSM_PARAM) -> dict:
    """SSM SecureString → 검증된 key set. 실패 시 DeletionAborted (비밀값 미출력)."""
    resp = ssm_client.get_parameter(Name=param_name, WithDecryption=True)
    raw = ((resp or {}).get("Parameter") or {}).get("Value")
    try:
        obj = json.loads(raw) if isinstance(raw, str) else None
    except ValueError:
        obj = None
    key_set = validate_hmac_key_set(obj)
    if key_set is None:
        raise DeletionAborted(
            f"{param_name} 의 HMAC key set 이 스키마를 위반한다 — 삭제 중단"
        )
    return key_set


def plan_pair_ids(key_set: dict, uid: str, analysis_id: str, joints) -> list[tuple[str, str, str]]:
    """(keyVersion, joint, pairId) 전개 — 활성+retired 전 버전 × historical joint."""
    plan: list[tuple[str, str, str]] = []
    for version in sorted(key_set["keys"]):
        material = key_set["keys"][version]
        for joint in joints:
            plan.append((version, joint, pair_id(uid, analysis_id, joint, hmac_key=material)))
    return plan


# ─────────────────────── inventory gate (H3-11) ───────────────────────


def inventory_key_versions(s3_client, bucket: str) -> set[str]:
    """저장소에 남아 있는 페어들이 선언한 hmacKeyVersion 집합."""
    versions: set[str] = set()
    for pid in iter_pair_prefixes(s3_client, bucket):
        meta = read_pair_meta_raw(s3_client, bucket, pid)
        if isinstance(meta, dict):
            version = meta.get("hmacKeyVersion")
            if isinstance(version, str) and version:
                versions.add(version)
    return versions


def assert_inventory_deletable(s3_client, bucket: str, key_set: dict) -> None:
    unknown = inventory_key_versions(s3_client, bucket) - set(key_set["keys"])
    if unknown:
        raise DeletionAborted(
            "저장소에 현재 key set 으로 재계산 불가능한 페어가 있다 "
            f"(미보유 keyVersion: {sorted(unknown)}) — 키 복구 전 삭제 중단"
        )


# ─────────────────────── versioned 완전 삭제 (H3-08 / H6-06) ───────────────────────


def enumerate_versions(s3_client, bucket: str, prefix: str) -> list[dict]:
    """prefix 하위 전 object version + delete marker. marker 쌍으로 끝까지 (H6-06)."""
    found: list[dict] = []
    key_marker: str | None = None
    version_marker: str | None = None
    while True:
        params: dict = {"Bucket": bucket, "Prefix": prefix}
        if key_marker:
            params["KeyMarker"] = key_marker
        if version_marker:
            params["VersionIdMarker"] = version_marker
        page = s3_client.list_object_versions(**params) or {}
        for group in ("Versions", "DeleteMarkers"):
            for item in page.get(group) or []:
                found.append({"Key": item["Key"], "VersionId": item["VersionId"]})
        if not page.get("IsTruncated"):
            return found
        key_marker = page.get("NextKeyMarker")
        version_marker = page.get("NextVersionIdMarker")
        if not key_marker and not version_marker:
            # 잘린 응답인데 이어받을 marker 가 없다 — 조용히 누락하지 않는다.
            raise DeletionAborted(f"{prefix} 열거가 marker 없이 잘렸다 — 삭제 중단")


def delete_prefix(s3_client, bucket: str, prefix: str) -> int:
    """prefix 하위 전 version 삭제 후 재조회로 0 확인. 반환 삭제 건수."""
    targets = enumerate_versions(s3_client, bucket, prefix)
    for start in range(0, len(targets), _DELETE_BATCH):
        batch = targets[start:start + _DELETE_BATCH]
        s3_client.delete_objects(Bucket=bucket, Delete={"Objects": batch, "Quiet": True})

    residue = enumerate_versions(s3_client, bucket, prefix)
    if residue:
        raise DeletionAborted(
            f"{prefix} 삭제 후 {len(residue)}건이 남았다 — 삭제 미완료로 비정상 종료"
        )
    return len(targets)


# ─────────────────────── orchestration ───────────────────────


def run_deletion(
    s3_client,
    key_set: dict,
    *,
    bucket: str,
    uid: str,
    analysis_id: str,
    joints=HISTORICAL_PAIR_JOINTS,
    dry_run: bool = False,
) -> dict:
    """전 키 버전 × historical joint 재계산 → prefix 별 완전 삭제."""
    assert_inventory_deletable(s3_client, bucket, key_set)

    report: dict = {"dry_run": bool(dry_run), "deleted": 0, "prefixes": []}
    for version, joint, pid in plan_pair_ids(key_set, uid, analysis_id, joints):
        prefix = pair_prefix(pid)
        targets = enumerate_versions(s3_client, bucket, prefix)
        if not targets:
            continue
        entry = {
            "keyVersion": version,
            "joint": joint,
            "pairId": pid,
            "objects": len(targets),
        }
        if not dry_run:
            entry["deleted"] = delete_prefix(s3_client, bucket, prefix)
            report["deleted"] += entry["deleted"]
        report["prefixes"].append(entry)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="학습 페어 삭제 (전 HMAC 키 버전 × historical joint × versionId 완전 삭제)"
    )
    parser.add_argument("--uid", required=True, help="대상 사용자 uid (원문 — 저장소에는 기록되지 않는다)")
    parser.add_argument("--analysis-id", required=True, help="대상 분석 id")
    parser.add_argument(
        "--joint",
        action="append",
        choices=list(HISTORICAL_PAIR_JOINTS),
        help="특정 관절만. 미지정 시 HISTORICAL_PAIR_JOINTS 전체 순회",
    )
    parser.add_argument("--bucket", default=PAIRS_BUCKET_DEFAULT)
    parser.add_argument("--param", default=HMAC_KEYS_SSM_PARAM)
    parser.add_argument("--profile", default="sunity-motion")
    parser.add_argument("--dry-run", action="store_true", help="목록만 출력, 삭제 0")
    args = parser.parse_args()

    import boto3

    session = boto3.Session(profile_name=args.profile)
    try:
        key_set = load_key_set(session.client("ssm"), args.param)
        report = run_deletion(
            session.client("s3"),
            key_set,
            bucket=args.bucket,
            uid=args.uid,
            analysis_id=args.analysis_id,
            joints=args.joint or HISTORICAL_PAIR_JOINTS,
            dry_run=args.dry_run,
        )
    except DeletionAborted as exc:
        log.error("삭제 중단: %s", exc)
        return 1

    mode = "dry-run (삭제 0)" if report["dry_run"] else "삭제 완료"
    log.info("%s — 페어 %d개, object %d건", mode, len(report["prefixes"]), report["deleted"])
    for entry in report["prefixes"]:
        log.info(
            "  keyVersion=%s joint=%s pairId=%s objects=%d",
            entry["keyVersion"],
            entry["joint"],
            entry["pairId"],
            entry["objects"],
        )
    if not report["prefixes"]:
        log.info("  대상 없음 (이미 삭제됐거나 적재된 적 없음)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
