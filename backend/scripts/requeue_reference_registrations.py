#!/usr/bin/env python3
"""대기 중인 공급자 링크 등록을 Pod 에 다시 보낸다 (Phase 38-08, D-20 · 리뷰 R3 · R4).

왜:
  Pod 이 없는 동안 올린 등록 영상은 파이프라인 Lambda 가 `queued` 로 두고 메시지를 정상 소비한다
  (D-20 — Pod 부재를 server_error 로 위장하지 않는다). SQS 재시도는 재개 수단이 아니다(RESEARCH Q13 —
  maxReceiveCount 3 뒤 DLQ 로 격리될 뿐). 그래서 Pod 을 띄운 사람이 이 스크립트를 한 번 돌려야 대기 건이
  등록된다 — 안 돌리면 영영 `queued` 다(메모리 build-it-and-schedule-it).
  재개도 `claim_registration` 을 지난다(R3) — 이 스크립트를 두 번 돌리거나 Lambda 위임과 겹쳐도 등록은
  한 번만 실행된다. presign 이 만료된 뒤에도 `registering` 에 멈춘 건(PUT 취소 · 이벤트 유실)은
  `--sweep-expired` 가 닫는다(R4) — 객체가 있으면 재개, 없으면 `expired`.

사용 (리포 루트에서, AWS_PROFILE=sunity-motion — SSM 조회 · S3 객체 확인에 필요):
  backend/.venv/bin/python backend/scripts/requeue_reference_registrations.py --dry-run          # 표만, 쓰기 0
  backend/.venv/bin/python backend/scripts/requeue_reference_registrations.py                    # queued 재개
  backend/.venv/bin/python backend/scripts/requeue_reference_registrations.py --reclaim-stale    # + lease 만료 processing
  backend/.venv/bin/python backend/scripts/requeue_reference_registrations.py --sweep-expired    # + presign 만료 registering

Pod 기동 절차의 7단계다 — 1~6(생성 · 부트스트랩 · start_server · health · Lambda/SSM 동기화)을 마친 뒤
`--dry-run` 으로 대기 건을 보고 인자 없이 한 번 돌린다(메모리 demo-only-pod-bring-up-procedure 갱신 대상).

주소 · 토큰: `--register-url`/`--token` 을 주거나, 없으면 SSM `/sunity/motion/runpod-analyze-url`
(`/analyze` → `/register-reference` 치환) · `/sunity/motion/runpod-auth-token`. 토큰은 출력하지 않는다.
Firestore Admin SA: env FIREBASE_SA_JSON / FIREBASE_SA_PATH 가 없으면 리포 루트 SA json 을 FIREBASE_SA_PATH 로.

이 스크립트가 쓰는 doc 필드는 claim(processing · jobId · leaseUntil)과 expired 뿐이다 — 나머지 상태 갱신
(active · failed · angles · 자기 재현성)은 Pod 의 등록 서비스가 한다. 읽기 수 = 대기 건수(상태별 등가 쿼리
하나씩, 전수 스캔 없음 — Firestore Spark 무료 플랜 읽기 5만/일 캡).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

_REPO = Path(__file__).resolve().parents[2]
_LAYER = _REPO / "backend" / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

from sunity_shared import firestore_admin, models  # noqa: E402
from sunity_shared.s3keys import parse_reference_key  # noqa: E402

DEFAULT_BUCKET = "sunity-motion-pilot-videos"
_SSM_ANALYZE_URL = "/sunity/motion/runpod-analyze-url"
_SSM_AUTH_TOKEN = "/sunity/motion/runpod-auth-token"
_SA_JSON = _REPO / "sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json"
_USER_AGENT = "sunity-motion-pilot/1.0 (+requeue)"
_POST_TIMEOUT_S = 30
_NOT_FOUND_CODES = ("404", "NoSuchKey", "NotFound")


def register_url_from_analyze(analyze_url: str) -> str:
    """`…/analyze` → `…/register-reference` (pipeline `_runpod_route` 와 같은 규칙)."""
    u = analyze_url.strip()
    if u.endswith("/analyze"):
        return u[: -len("/analyze")] + "/register-reference"
    return u.rstrip("/") + "/register-reference"


def _resolve_endpoint(args) -> tuple[str, str]:
    url, token = args.register_url, args.token
    if url and token:
        return url, token
    ssm = boto3.client("ssm")
    if not url:
        url = register_url_from_analyze(ssm.get_parameter(Name=_SSM_ANALYZE_URL)["Parameter"]["Value"])
    if not token:
        token = ssm.get_parameter(Name=_SSM_AUTH_TOKEN, WithDecryption=True)["Parameter"]["Value"].strip()
    return url, token


def _post(url: str, token: str, bucket: str, key: str, job_id: str) -> int:
    """Pod `/register-reference` POST → HTTP 코드. HTTPError 는 코드로, 네트워크 오류는 0 으로."""
    payload = json.dumps({"bucket": bucket, "key": key, "jobId": job_id}).encode("utf-8")
    req = urllib.request.Request(
        url,
        method="POST",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
            "X-RunPod-Token": token,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_POST_TIMEOUT_S) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as e:
        return int(e.code)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  POST 실패 {type(e).__name__}: {e}", file=sys.stderr)
        return 0


def _upload_key(doc: dict) -> str | None:
    """doc 의 uploadKey 가 이 doc 의 upload 키일 때만 반환 — legacy 평면 · 확정 v1 · 다른 refId 는 None."""
    key = doc.get("uploadKey")
    ref = parse_reference_key(key) if isinstance(key, str) else None
    if ref is None or not ref.is_upload or ref.ref_id != doc.get("motionId"):
        return None
    return key


def _plan(args, now: int) -> list[tuple[dict, str]]:
    """(doc, 행동) 목록. 행동 = queued · reclaim · sweep · skip(사유)."""
    out: list[tuple[dict, str]] = []
    for d in firestore_admin.list_reference_registrations_by_status(models.REGISTRATION_STATUS_QUEUED):
        out.append((d, "queued"))
    if args.reclaim_stale:
        for d in firestore_admin.list_reference_registrations_by_status(models.REGISTRATION_STATUS_PROCESSING):
            lease = d.get("leaseUntil")
            alive = isinstance(lease, (int, float)) and not isinstance(lease, bool) and lease >= now
            out.append((d, "skip(lease 살아 있음)" if alive else "reclaim"))
    if args.sweep_expired:
        for d in firestore_admin.list_reference_registrations_by_status(models.REGISTRATION_STATUS_REGISTERING):
            exp = d.get("uploadExpiresAt")
            expired = isinstance(exp, (int, float)) and not isinstance(exp, bool) and exp < now
            out.append((d, "sweep" if expired else "skip(업로드 기간 남음)"))
    return out


def _print_table(rows: list[tuple[dict, str]]) -> None:
    print(f"{'ref_id':34} {'status':12} {'supplierUid':30} {'updatedAt':>14}  uploadKey  → 계획")
    for d, action in rows:
        print(
            f"{str(d.get('motionId')):34} {str(d.get('registrationStatus')):12} "
            f"{str(d.get('supplierUid')):30} {str(d.get('registrationUpdatedAt')):>14}  "
            f"{d.get('uploadKey')}  → {action}"
        )
    print(f"총 {len(rows)}건")


def _claim_and_post(ref_id: str, key: str, *, url: str, token: str, bucket: str, now: int) -> bool:
    """claim 을 지난 건만 POST. 반환 = 실패 여부(claim 실패는 실패가 아니라 스킵)."""
    job_id = uuid.uuid4().hex
    if not firestore_admin.claim_registration(ref_id, job_id, now_ms=now):
        print(f"ref_id={ref_id} key={key} job={job_id} → skip(claim) — 다른 실행이 잡았거나 종결")
        return False
    code = _post(url, token, bucket, key, job_id)
    if code in (200, 202):
        print(f"ref_id={ref_id} key={key} job={job_id} → {code}")
        return False
    print(
        f"ref_id={ref_id} key={key} job={job_id} → 실패(http={code}) — processing 으로 남음, "
        f"lease 만료 뒤 --reclaim-stale 로 재시도"
    )
    return True


def _sweep_one(s3, ref_id: str, key: str, *, url: str, token: str, bucket: str, now: int) -> bool:
    """presign 만료 registering 1건: 객체 있으면 claim+POST, 없으면 expired. 반환 = 실패 여부."""
    try:
        s3.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        err = str((getattr(e, "response", None) or {}).get("Error", {}).get("Code", ""))
        if err in _NOT_FOUND_CODES:
            ok = firestore_admin.set_registration_expired(ref_id)
            print(f"ref_id={ref_id} key={key} → {'expired' if ok else 'skip(expired 전이 거부 — 상태 바뀜)'}")
            return False
        print(f"ref_id={ref_id} key={key} → 실패(S3 head {err or type(e).__name__})")
        return True
    return _claim_and_post(ref_id, key, url=url, token=token, bucket=bucket, now=now)


def main(argv: list[str] | None = None, *, now_ms: int | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="대기 중인 공급자 링크 등록을 Pod /register-reference 로 재개 (Pod 기동 절차 7단계)."
    )
    ap.add_argument("--register-url", help="Pod /register-reference URL (없으면 SSM runpod-analyze-url 에서 파생)")
    ap.add_argument("--token", help="X-RunPod-Token (없으면 SSM runpod-auth-token). 출력하지 않는다")
    ap.add_argument("--bucket", default=DEFAULT_BUCKET, help=f"영상 버킷 (기본 {DEFAULT_BUCKET})")
    ap.add_argument("--dry-run", action="store_true", help="대기 건 표만 출력 — claim · POST · 쓰기 0")
    ap.add_argument(
        "--reclaim-stale", action="store_true", help="lease 가 만료된 processing(Pod 이 죽은 작업)도 재claim"
    )
    ap.add_argument(
        "--sweep-expired",
        action="store_true",
        help="presign 만료 registering 을 S3 객체 유무로 판정 — 객체 있으면 재개, 없으면 expired",
    )
    args = ap.parse_args(argv)
    now = int(now_ms) if now_ms is not None else int(time.time() * 1000)

    rows = _plan(args, now)
    if args.dry_run:
        _print_table(rows)
        return 0

    work = [(d, a) for d, a in rows if not a.startswith("skip")]
    for d, a in rows:
        if a.startswith("skip"):
            print(f"ref_id={d.get('motionId')} → {a}")
    if not work:
        print("재개할 건 없음")
        return 0

    url, token = _resolve_endpoint(args)
    s3 = boto3.client("s3") if any(a == "sweep" for _, a in work) else None
    failures = 0
    for d, action in work:
        ref_id = str(d.get("motionId"))
        key = _upload_key(d)
        if key is None:
            print(f"ref_id={ref_id} key={d.get('uploadKey')} → skip(upload 키 아님 — legacy/확정/불일치)", file=sys.stderr)
            continue
        if action == "sweep":
            failed = _sweep_one(s3, ref_id, key, url=url, token=token, bucket=args.bucket, now=now)
        else:
            failed = _claim_and_post(ref_id, key, url=url, token=token, bucket=args.bucket, now=now)
        failures += int(failed)
    print(f"완료 — 대상 {len(work)}건, 실패 {failures}건")
    return 1 if failures else 0


def _default_sa_env() -> None:
    """CLI 전용 — SA env 가 없으면 리포 루트 json 을 쓴다(테스트 프로세스 env 를 건드리지 않게 main 밖)."""
    if not (os.environ.get("FIREBASE_SA_JSON") or os.environ.get("FIREBASE_SA_PATH")) and _SA_JSON.exists():
        os.environ["FIREBASE_SA_PATH"] = str(_SA_JSON)


if __name__ == "__main__":
    _default_sa_env()
    sys.exit(main())
