"""신규 6 motion (UAT 2026-06-12) 재활성화 자동화 스크립트.

Phase 17 Plan 07 Task 1 박제. 신규 6 motion 의 NLF↔RTMW 호환 깨짐 finding
(현재 isActive=false) 을 영역 A endpoint (Plan 05, POST /reference/auto-register)
호출로 해소. 흐름:
  1. Firestore reference/{motionId} 조회 → 기존 videoS3Key 확인.
  2. STUDIO_ALIAS_OVERRIDES 또는 reference doc 의 studioAlias field 에서
     studio_alias 결정 (분기 라우팅 의도 박제).
  3. POST /reference/auto-register body { s3Key, studioAlias?, overrideMotionId }
     호출 — Lambda 가 S3 download → Gemini A Pro Vision → routing_branch +
     motion_name_ipsf + clipRange + checkpointJoints 박힌 reference doc upsert.
  4. 응답 받은 routing_branch + reviewRequired log + 다음 motion 진행.

belle 검수 후 별도 admin script 또는 Firestore Console 로 isActive=true.

dry-run 모드:
  --dry-run 박혀 있으면 endpoint 호출 X + Firestore 갱신 X + log 만.

env (belle 박제):
  REFERENCE_AUTO_REGISTER_URL — Lambda HTTP endpoint URL (SAM output ApiBaseUrl
    + "/reference/auto-register").
  BELLE_ID_TOKEN — belle Firebase ID token (Firebase Auth REST API 또는 앱에서
    추출). Lambda 의 BELLE_UID 화이트리스트 정합 박제.

사용:
  cd backend
  export REFERENCE_AUTO_REGISTER_URL="https://xxxx.execute-api.ap-northeast-2.amazonaws.com/pilot/reference/auto-register"
  export BELLE_ID_TOKEN="eyJ..."
  python -m scripts.reactivate_new6_motions --dry-run
  python -m scripts.reactivate_new6_motions

graceful failure:
  motion 1건 실패해도 다음 motion 진행 (재시도 비용 차단). 일부 실패 시
  exit code 1 — caller (belle) 가 실패 motion 만 재호출.

Memory 박제:
  · pod-ops-claude-runs — Pod 작업은 Claude 가 실행 박제.
  · sim-scaffold-not-decorate — 실분석 의존 화면 박제 X (dry-run = 자리만).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))

# 사용자 박제 메시지는 print() 로 stdout 직접 박는다 — capsys 정합 박제. logging
# 박제 시 핸들러의 sys.stdout reference 가 모듈 import 시점에 박혀버려 pytest
# capsys 의 fd redirect 박지 못함. 본 스크립트는 외부 호출 1회용 박제 —
# 구조화된 logging 박제 불필요.


# ── 신규 6 motion ID 박제 ────────────────────────────────────────────────
# UAT 2026-06-12 belle 결정 박힘 — app/scripts/seed-reference-motions.mjs:271-419
# 의 "정은지 추가 영상 6 motion" 주석 블록 박은 list 와 1:1.
# belle 가 환경 차이로 수정 가능하도록 list 상단 박제 + --motion-ids CLI flag
# 박제 (overrides).
NEW6_MOTION_IDS: list[str] = [
    "ref-kip-up",
    "ref-peter-pan",
    "ref-power-spin",
    "ref-elbow-twist-sister",
    "ref-pdshape",
    "ref-combo",
]


# ── STUDIO_ALIAS_OVERRIDES 박제 (W4 정합) ───────────────────────────────────
# {motion_id: studio_alias} 형식. belle 가 신규 6 motion 의 분기 2 라우팅 (예:
# 폭스탑/사이드웨이 스핀 매칭) 의도하면 이 dict 에 직접 박는다. 미박제 motion
# 은 studio_alias=None → Gemini A 가 분기 1 IPSF whitelist 매치 시도 → 미매치
# 시 분기 3 auto fallback (G3 guardrail, isActive=false 박힘).
#
# 학원 통용명 (seed-reference-motions.mjs 박힘) 그대로 사용 — IPSF 정식 등재
# strict 매칭 미박제 motion 들이라 분기 2 (정은지 reference 측정값 = 채점 기준)
# 가 의도된 라우팅 (.planning/research/new-motions-ipsf-matching-2026-06-12/
# CROSS-CHECK.md 박힘).
STUDIO_ALIAS_OVERRIDES: dict[str, str] = {
    "ref-kip-up": "킵업",
    "ref-peter-pan": "피터팬",
    "ref-power-spin": "파워스핀",
    "ref-elbow-twist-sister": "엘보 트위스트 시스터",
    "ref-pdshape": "pdshape",
    "ref-combo": "콤보",
}


# ── env ────────────────────────────────────────────────────────────────────
_ENV_ENDPOINT = "REFERENCE_AUTO_REGISTER_URL"
_ENV_ID_TOKEN = "BELLE_ID_TOKEN"
_HTTP_TIMEOUT_S = 300  # Lambda Timeout 240s + 네트워크 jitter 60s.


def _fetch_reference_doc(motion_id: str) -> dict | None:
    """Firestore reference/{motion_id} 조회 — videoS3Key + studioAlias 확인.

    firebase_admin lazy import 박제 — 테스트는 monkeypatch 로 차단. graceful X
    (Firestore 호출 실패 시 caller 가 RuntimeError raise — script 가 graceful
    매핑).
    """
    from sunity_shared.firestore_admin import get_db  # lazy import

    db = get_db()
    snap = db.collection("reference").document(motion_id).get()
    if not snap.exists:
        return None
    return snap.to_dict() or {}


def _post_auto_register(
    *,
    endpoint_url: str,
    id_token: str,
    s3_key: str,
    studio_alias: str | None,
    override_motion_id: str,
) -> dict:
    """POST /reference/auto-register — stdlib urllib (pipeline/_delegate_to_runpod 정합).

    requests 의존성 X — Lambda Layer 부담 회피. RunPod proxy 와 동일하게 일반
    UA + Accept 헤더 박제 (Cloudflare 1010 차단 회피).

    Raises:
      RuntimeError: HTTP 응답 비-2xx 또는 네트워크 실패.
    """
    body: dict = {"s3Key": s3_key, "overrideMotionId": override_motion_id}
    if studio_alias is not None:
        body["studioAlias"] = studio_alias
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        endpoint_url,
        method="POST",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {id_token}",
            "User-Agent": "sunity-motion-reactivate/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:
            raw = resp.read()
            if resp.status not in (200, 202):
                raise RuntimeError(
                    f"auto-register {resp.status}: {raw[:512]!r}"
                )
    except urllib.error.HTTPError as e:
        body_bytes = e.read()[:512] if hasattr(e, "read") else b""
        raise RuntimeError(
            f"auto-register HTTPError {e.code}: {body_bytes!r}"
        ) from e

    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"auto-register 응답 JSON 파싱 실패: {raw[:512]!r}") from e

    # responses.ok 박제 envelope 풀기 — { ok: true, ...payload }.
    if isinstance(data, dict) and "ok" in data:
        return {k: v for k, v in data.items() if k != "ok"}
    return data


def _resolve_studio_alias(motion_id: str, ref_doc: dict | None) -> str | None:
    """STUDIO_ALIAS_OVERRIDES 우선, 없으면 reference doc 의 studioAlias field 박제."""
    if motion_id in STUDIO_ALIAS_OVERRIDES:
        return STUDIO_ALIAS_OVERRIDES[motion_id]
    if ref_doc and isinstance(ref_doc.get("studioAlias"), str):
        return ref_doc["studioAlias"]
    return None


def run(
    *,
    motion_ids: list[str],
    dry_run: bool,
    endpoint_url: str,
    id_token: str,
) -> int:
    """신규 6 motion 순차 재활성화.

    Returns:
      0 = 모두 성공, 1 = 일부 실패 (graceful).
    """
    if not motion_ids:
        log.error("motion_ids 가 비었습니다.")
        return 1

    failures: list[tuple[str, str]] = []
    successes: list[tuple[str, dict]] = []

    # 사용자 박제 banner — capsys 정합 박제 print() 직접 박는다 (logger 핸들러
    # 의 stdout reference 박힘 시점 박혀 pytest capsys 의 fd redirect 못 박음).
    if dry_run:
        print("=== DRY-RUN — endpoint 호출 X, Firestore 갱신 X ===")
    print(
        f"신규 motion {len(motion_ids)} 건 재활성화 시작 — "
        f"endpoint={endpoint_url if not dry_run else '(dry-run)'} dry_run={dry_run}"
    )

    for motion_id in motion_ids:
        print(f"\n[{motion_id}]")

        # 1. Firestore reference doc 조회 (dry-run 도 조회는 박는다 — videoS3Key
        #    안정성 박제 박은 메타데이터 확인). 조회 실패 시 graceful skip.
        try:
            ref_doc = _fetch_reference_doc(motion_id)
        except Exception as exc:  # noqa: BLE001 — Firestore 실패 graceful 박제
            print(f"  Firestore 조회 실패: {exc} (skip)")
            failures.append((motion_id, f"firestore: {exc}"))
            continue

        if ref_doc is None:
            print("  reference doc 박혀있지 않음 (skip)")
            failures.append((motion_id, "missing reference doc"))
            continue

        # 2. videoS3Key 확인 — presigned videoUrl 박제 X (7일 만료 — 박제 안정성).
        s3_key = ref_doc.get("videoS3Key")
        if not isinstance(s3_key, str) or not s3_key:
            print("  videoS3Key 박혀있지 않음 (skip)")
            failures.append((motion_id, "missing videoS3Key"))
            continue

        # 3. studio_alias 결정.
        studio_alias = _resolve_studio_alias(motion_id, ref_doc)
        print(f"  s3Key={s3_key} studioAlias={studio_alias}")

        if dry_run:
            print("  DRY-RUN: endpoint 호출 박제 X")
            successes.append((motion_id, {"dryRun": True}))
            continue

        # 4. POST /reference/auto-register 호출 — Lambda 가 RTMW angles 재추출 +
        #    Gemini A + Firestore upsert 박는다.
        try:
            result = _post_auto_register(
                endpoint_url=endpoint_url,
                id_token=id_token,
                s3_key=s3_key,
                studio_alias=studio_alias,
                override_motion_id=motion_id,
            )
        except Exception as exc:  # noqa: BLE001 — endpoint 실패 graceful 박제
            print(f"  auto-register FAIL: {exc}")
            failures.append((motion_id, str(exc)))
            continue

        routing = result.get("routingBranch", "(unknown)")
        review_required = result.get("reviewRequired", True)
        print(f"  OK — routingBranch={routing} reviewRequired={review_required}")
        successes.append((motion_id, result))

    print(f"\n=== 완료 — 성공 {len(successes)} / 실패 {len(failures)} ===")
    for motion_id, reason in failures:
        print(f"  FAIL {motion_id} — {reason}")

    return 0 if not failures else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="신규 6 motion 재활성화 (POST /reference/auto-register 호출)"
    )
    parser.add_argument(
        "--motion-ids",
        nargs="+",
        default=None,
        help="대상 motionId 부분집합 (디버그용). 기본은 NEW6_MOTION_IDS 6개 전부.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="endpoint 호출 X + Firestore 갱신 X + log 만 박는다.",
    )
    args = parser.parse_args(argv)

    motion_ids = list(args.motion_ids) if args.motion_ids else list(NEW6_MOTION_IDS)

    endpoint_url = os.environ.get(_ENV_ENDPOINT, "")
    id_token = os.environ.get(_ENV_ID_TOKEN, "")

    if not args.dry_run:
        if not endpoint_url:
            log.error(
                "%s env 미박제 — auto-register Lambda URL 필요 (SAM ApiBaseUrl + '/reference/auto-register').",
                _ENV_ENDPOINT,
            )
            return 2
        if not id_token:
            log.error(
                "%s env 미박제 — belle Firebase ID token 필요 (Lambda BELLE_UID 화이트리스트 정합).",
                _ENV_ID_TOKEN,
            )
            return 2

    return run(
        motion_ids=motion_ids,
        dry_run=args.dry_run,
        endpoint_url=endpoint_url,
        id_token=id_token,
    )


if __name__ == "__main__":
    sys.exit(main())
