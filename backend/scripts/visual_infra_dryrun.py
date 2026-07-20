"""Phase 31 시각 교정물 인프라 dry-run — **read-only**. 라이브 mutation 0 (H2-09).

이 스크립트는 아무것도 바꾸지 않는다. put/create/delete 계열 호출이 한 줄도 없고,
산출물은 31-12 가 belle 승인 하에 적용할 **제안 JSON** 뿐이다. 실제 put 과 canary
delete 는 31-12 전용이다 (H5-07).

검사 3종:

  (1) VisualInputBucket 이 **Never-versioned** 인가 (7차 B7-02).
      `get-bucket-versioning` 응답에 `Status` key 가 **아예 없어야** 통과한다.
      `Enabled` 는 물론이고 `Suspended` 도 blocked 다 — Suspended 버킷의 단순
      delete 는 과거 version 의 완전 삭제를 보장하지 않는다. 임시 생체 프레임의
      "즉시 삭제" SLA 는 delete 1회 = 완전 소거일 때만 성립한다 (T-31-76).
      Object Lock 이 설정돼 있어도 blocked (삭제 불능).

  (2) 페어 버킷(VideoBucket) 은 versioning + Object Lock 을 **인지**만 한다
      (H4-03/H4-04). default retention 이 걸려 있으면 삭제 SLA 를 지킬 수 없어
      blocked, enabled·no-default 면 canary 판정을 31-12 로 넘긴다.

  (3) lifecycle 은 **버킷당 독립 파일** 4개로 산출한다 (7차 B7-07/H7-08).
      각 파일은 AWS API 가 그대로 받는 `{"Rules": [...]}` 단일-버킷 형상이다 —
      멀티버킷 wrapper 를 만들면 31-12 가 파일↔버킷 1:1 put 을 할 수 없다.

버킷 이름은 `infra/visual_input_bucket.json` **단일 출처**에서만 온다 (9차 B9-05).
기본값 하드코딩이 없으므로 파일이 없으면 STOP 한다 — 엉뚱한 버킷을 조회하느니
멈추는 쪽이 맞다.

privacy 결정값(retentionDays 등)은 여기서 로컬 JSON 을 읽는다. M3-02 위반이
아니다: M3-02 는 **Lambda/pipeline 런타임**이 .planning 을 읽지 못하게 하는 규칙이고,
이 파일은 배포 산출물이 아니라 개발자가 손으로 돌리는 로컬 스크립트다.

사용:
    python backend/scripts/visual_infra_dryrun.py [--out DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PHASE_DIR = _REPO_ROOT / ".planning" / "phases" / "31-api-visual-correction"
_INFRA_DIR = _PHASE_DIR / "infra"
_BUCKET_JSON = _INFRA_DIR / "visual_input_bucket.json"
_PRIVACY_JSON = _PHASE_DIR / "smoke" / "privacy_decision.json"

_VISUAL_INPUT_PREFIX = "visual-input/"
_VISUAL_INPUT_EXPIRE_DAYS = 1
_PAIRS_PREFIX = "training/phase31/pairs/"
_HMAC_PARAM = "/sunity/motion/pair-id-hmac-keys"


class DryRunStop(Exception):
    """진행 불가 — 추측하지 않고 멈춘다."""


# ─────────────────────── 단일 출처 입력 ───────────────────────


def load_bucket_config(path: Path | None = None) -> dict:
    """버킷 이름/리전의 단일 출처 (9차 B9-05). 기본값 하드코딩 없음."""
    path = path or _BUCKET_JSON
    if not path.exists():
        raise DryRunStop(
            f"{path} 부재 — 버킷 이름의 단일 출처가 없으면 진행하지 않는다 (B9-05)."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    name = data.get("bucketName")
    region = data.get("region")
    if not isinstance(name, str) or not name:
        raise DryRunStop(f"{path}: bucketName 이 비어 있다.")
    if not isinstance(region, str) or not region:
        raise DryRunStop(f"{path}: region 이 비어 있다.")
    return {"bucketName": name, "region": region}


def load_privacy_decision(path: Path | None = None) -> dict:
    path = path or _PRIVACY_JSON
    if not path.exists():
        raise DryRunStop(f"{path} 부재 — retentionDays 를 추측하지 않는다.")
    return json.loads(path.read_text(encoding="utf-8"))


# ─────────────────────── (1) VisualInputBucket ───────────────────────


def check_visual_input_bucket(s3, bucket: str) -> dict:
    """Never-versioned + Object Lock 미설정만 통과 (7차 B7-02)."""
    versioning = s3.get_bucket_versioning(Bucket=bucket) or {}
    status = versioning.get("Status")
    if status is not None:
        return {
            "bucket": bucket,
            "blocked": True,
            "reason": (
                "visual_input_must_be_never_versioned — Suspended 도 단순 delete 로 "
                f"과거 version 완전 삭제 미보장 (관측 Status={status!r})"
            ),
        }

    lock = _object_lock_config(s3, bucket)
    if lock.get("enabled"):
        return {
            "bucket": bucket,
            "blocked": True,
            "reason": "visual_input_object_lock_set — 삭제 불능이면 즉시 삭제 SLA 불가",
        }

    residue = _version_residue(s3, bucket, _VISUAL_INPUT_PREFIX)
    return {
        "bucket": bucket,
        "blocked": False,
        "neverVersioned": True,
        "objectLock": False,
        "versionResidue": residue,
    }


def _object_lock_config(s3, bucket: str) -> dict:
    """Object Lock 조회. 미설정 예외는 '없음' 으로 정규화한다."""
    try:
        conf = s3.get_object_lock_configuration(Bucket=bucket) or {}
    except Exception as exc:  # noqa: BLE001 - 미설정이 예외로 오는 API
        if _is_missing_lock(exc):
            return {"enabled": False, "defaultRetention": False}
        raise
    lock = (conf.get("ObjectLockConfiguration") or {})
    return {
        "enabled": lock.get("ObjectLockEnabled") == "Enabled",
        "defaultRetention": bool((lock.get("Rule") or {}).get("DefaultRetention")),
    }


def _is_missing_lock(exc) -> bool:
    code = str(((getattr(exc, "response", None) or {}).get("Error") or {}).get("Code") or "")
    return code in ("ObjectLockConfigurationNotFoundError", "NoSuchObjectLockConfiguration")


def _version_residue(s3, bucket: str, prefix: str) -> dict:
    """사용 전 잔여 version 기록 (read-only, checkpoint 주체 전용).

    worker 런타임에는 version 권한을 주지 않는다 — 이 조회는 사람이 돌리는
    dry-run 의 자격증명으로만 한다.
    """
    try:
        res = s3.list_object_versions(Bucket=bucket, Prefix=prefix, MaxKeys=1000) or {}
    except Exception as exc:  # noqa: BLE001 - 권한 부재는 정보로 남긴다
        return {"checked": False, "error": type(exc).__name__}
    return {
        "checked": True,
        "versions": len(res.get("Versions") or []),
        "deleteMarkers": len(res.get("DeleteMarkers") or []),
    }


# ─────────────────────── (2) 페어 버킷 ───────────────────────


def check_pair_bucket(s3, bucket: str) -> dict:
    """versioning + Object Lock 인지 (H4-03/H4-04). 실 canary 는 31-12 (H5-07)."""
    versioning = s3.get_bucket_versioning(Bucket=bucket) or {}
    status = versioning.get("Status")
    lock = _object_lock_config(s3, bucket)

    if lock.get("enabled") and lock.get("defaultRetention"):
        return {
            "bucket": bucket,
            "blocked": True,
            "reason": "object_lock_default_retention",
            "versioningStatus": status,
        }

    out = {
        "bucket": bucket,
        "blocked": False,
        "versioningStatus": status,
        "objectLockEnabled": bool(lock.get("enabled")),
        "canaryRequired": bool(lock.get("enabled")),
    }
    if out["canaryRequired"]:
        out["canaryNote"] = "Object Lock enabled + no default retention — 실 canary delete 는 31-12"
    return out


# ─────────────────────── (3) lifecycle merge ───────────────────────


def _existing_rules(s3, bucket: str) -> list:
    try:
        conf = s3.get_bucket_lifecycle_configuration(Bucket=bucket) or {}
    except Exception as exc:  # noqa: BLE001 - 규칙 부재는 예외로 온다
        code = str(((getattr(exc, "response", None) or {}).get("Error") or {}).get("Code") or "")
        if code in ("NoSuchLifecycleConfiguration",):
            return []
        raise
    return list(conf.get("Rules") or [])


def visual_input_merged_rules(existing: list) -> list:
    """visual-input/ 1일 만료 규칙 merge. NoncurrentVersionExpiration 없음(H7-08).

    비-버저닝 버킷에 noncurrent 규칙을 넣는 것은 무의미할 뿐 아니라, "이 버킷은
    버저닝이어도 된다" 는 잘못된 신호를 남긴다.
    """
    rule = {
        "ID": "visual-input-1d",
        "Status": "Enabled",
        "Filter": {"Prefix": _VISUAL_INPUT_PREFIX},
        "Expiration": {"Days": _VISUAL_INPUT_EXPIRE_DAYS},
    }
    return _merge_rule(existing, rule)


def pairs_merged_rules(existing: list, *, retention_days: int, versioned: bool) -> list:
    """페어 prefix 삭제 SLA merge. 기존 규칙은 전부 보존한다.

    versioned 면 noncurrent version 과 만료된 delete marker 까지 정리해야 실제로
    사라진다 (H3-08) — 현재 version 만 지우면 과거 version 이 남는다.
    """
    rule = {
        "ID": "phase31-pairs-retention",
        "Status": "Enabled",
        "Filter": {"Prefix": _PAIRS_PREFIX},
        "Expiration": {"Days": int(retention_days)},
    }
    if versioned:
        rule["NoncurrentVersionExpiration"] = {"NoncurrentDays": int(retention_days)}
        rule["Expiration"] = {
            "Days": int(retention_days),
            "ExpiredObjectDeleteMarker": True,
        }
    return _merge_rule(existing, rule)


def _merge_rule(existing: list, rule: dict) -> list:
    """같은 ID 만 교체하고 나머지는 원본 순서 그대로 보존 (T-31-55)."""
    out = [r for r in existing if r.get("ID") != rule["ID"]]
    out.append(rule)
    return out


def validate_lifecycle_shape(payload: dict) -> None:
    """AWS API 가 그대로 받는 단일-버킷 형상인지 (B7-07).

    botocore 가 있으면 실제 shape validation 을, 없으면 최소 구조 검사를 한다.
    """
    if set(payload) != {"Rules"} or not isinstance(payload["Rules"], list):
        raise DryRunStop("lifecycle 파일은 {'Rules': [...]} 단일-버킷 형상이어야 한다 (B7-07).")
    try:
        from botocore.session import get_session
        from botocore.validate import validate_parameters
    except ImportError:
        return
    model = get_session().get_service_model("s3")
    shape = model.operation_model("PutBucketLifecycleConfiguration").input_shape
    validate_parameters(
        {"Bucket": "placeholder", "LifecycleConfiguration": payload},
        shape,
    )


# ─────────────────────── (4) SSM (read-only) ───────────────────────


def check_hmac_key_param(ssm) -> dict:
    """존재 시 형식 검증, 부재 시 **생성 지시문**만 낸다. put 계열 호출 없음."""
    try:
        res = ssm.get_parameter(Name=_HMAC_PARAM, WithDecryption=True)
    except Exception as exc:  # noqa: BLE001 - 부재가 예외
        return {
            "present": False,
            "error": type(exc).__name__,
            "instruction": (
                f"aws ssm put-parameter --name {_HMAC_PARAM} --type SecureString "
                "--value '<key set JSON>' (31-12 가 belle 승인 하에 수행)"
            ),
        }
    from sunity_shared.analysis.pair_store import validate_hmac_key_set

    raw = (res.get("Parameter") or {}).get("Value")
    try:
        parsed = validate_hmac_key_set(json.loads(raw))
    except Exception:  # noqa: BLE001
        parsed = None
    return {"present": True, "valid": parsed is not None}


# ─────────────────────── 실행 ───────────────────────


def run(s3, ssm, *, out_dir: Path, video_bucket: str) -> dict:
    cfg = load_bucket_config()
    privacy = load_privacy_decision()
    visual_bucket = cfg["bucketName"]

    report = {
        "visualInputBucket": check_visual_input_bucket(s3, visual_bucket),
        "pairBucket": check_pair_bucket(s3, video_bucket),
        "hmacKeyParam": check_hmac_key_param(ssm),
        "retentionDays": privacy.get("retentionDays"),
        "liveMutations": 0,
    }

    # 버킷당 독립 4파일 (B7-07). 멀티버킷 wrapper 금지.
    vi_before = _existing_rules(s3, visual_bucket)
    vi_merged = visual_input_merged_rules(vi_before)
    vb_before = _existing_rules(s3, video_bucket)
    versioned = report["pairBucket"].get("versioningStatus") in ("Enabled", "Suspended")
    vb_merged = pairs_merged_rules(
        vb_before,
        retention_days=int(privacy.get("retentionDays") or 0),
        versioned=versioned,
    )

    files = {
        "visual_input_lifecycle_before.json": {"Rules": vi_before},
        "visual_input_lifecycle_merged.json": {"Rules": vi_merged},
        "video_lifecycle_before.json": {"Rules": vb_before},
        "video_lifecycle_merged.json": {"Rules": vb_merged},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in files.items():
        validate_lifecycle_shape(payload)
        (out_dir / name).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # 기존 규칙 보존 검증 — 버킷별로 따로 본다.
    _assert_preserved(vi_before, vi_merged, "visual_input")
    _assert_preserved(vb_before, vb_merged, "video")

    report["lifecycleFiles"] = sorted(files)
    return report


def _assert_preserved(before: list, merged: list, label: str) -> None:
    merged_ids = {r.get("ID") for r in merged}
    lost = [r.get("ID") for r in before if r.get("ID") not in merged_ids]
    if lost:
        raise DryRunStop(f"{label}: 기존 lifecycle 규칙 소실 {lost} (T-31-55)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Phase 31 인프라 dry-run (read-only)")
    parser.add_argument("--out", default=str(_INFRA_DIR), help="lifecycle 산출 디렉터리")
    parser.add_argument(
        "--video-bucket", default="sunity-motion-pilot-videos", help="페어(결과) 버킷"
    )
    args = parser.parse_args(argv)

    import boto3

    cfg = load_bucket_config()
    s3 = boto3.client("s3", region_name=cfg["region"])
    ssm = boto3.client("ssm", region_name=cfg["region"])
    try:
        report = run(s3, ssm, out_dir=Path(args.out), video_bucket=args.video_bucket)
    except DryRunStop as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["visualInputBucket"].get("blocked") else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
