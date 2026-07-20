"""D-01 학습 페어([틀린 폼 → 고쳐진 폼]) 적재/소비 — 담당 플랜 31-07.

phase 22 재도전의 원료를 privacy 통제 하에 제조한다. 통제 축 5개:

1. **동의 게이트 ([[learning-consent-pilot-mandatory]] + D-01)**
   `learning_opt_in is True` strict. False/부재/비-bool(문자열 "true" 포함)은 즉시
   'skipped_consent' 이며 **S3 호출이 0건**이다. truthy 판정을 쓰면 `"false"` 같은
   문자열이 통과해 동의하지 않은 사용자의 신체 이미지가 학습 저장소에 들어간다.

2. **HMAC 가명 (리뷰 H-04 + H2-06)**
   S3 key 와 meta 어디에도 uid/analysisId 원문이 없다. pairId = HMAC-SHA256(key,
   "uid:analysisId:joint")[:24]. 역추적은 키 보유자만 가능하고, 삭제 요청은 같은 키로
   pairId 를 재계산해 이행한다. 키는 **버전 집합**(active + keys)이라 회전해도 과거
   페어를 계속 삭제할 수 있다.

3. **caller-fixed pairId + meta-read 멱등 (5차 리뷰 B5-03, 6차 H6-04)**
   `store_training_pair` 는 active 키를 **스스로 재선택하지 않는다.** caller(31-09
   postprocess)가 진입 transaction 에서 1회 고정한 pair_id/hmac_key_version 을 인자로
   받는다. 그리고 쓰기 전에 meta.json 을 먼저 읽는다 — 존재+일치면 PUT 0건으로
   'committed', 존재+불일치면 덮어쓰지 않고 'conflict'. postprocess crash 후 재시도가
   키 회전과 겹쳐도 같은 분석에 페어는 1개다.

4. **commit marker (3차 리뷰 H3-07)**
   before.png → after.png → meta.json 순서로 쓰고 **meta.json 이 commit marker** 다.
   중간 실패 시 이번 호출이 만든 object 를 best-effort 삭제하므로 marker 없는 부분
   적재물은 학습에 소비되지 않는다. meta 부재 재개 경로에서 조건부 PUT 이 412(이미
   존재)를 만나면 **기존 payload 의 size+sha256 을 검증한 뒤에만** 재개한다 — 변조된
   before/after 가 조용히 학습쌍으로 커밋되는 경로를 막는다 (H6-04).

5. **payload 검증 consumer (4차 H4-11 + 5차 H5-08/M5-05)**
   consumer(phase 22 datagen)는 `list_committed_pairs`/`load_committed_pair` 만 쓴다.
   before/after prefix 직접 list 는 금지 — marker 와 payload hash 를 함께 검증한
   페어만 학습에 들어가고, 부재/불일치는 quarantine 으로 분리된다. listing 은
   continuation token 끝까지 돈다.

보존: `RETENTION_DAYS` 는 **우리(Sunity) S3 학습 페어의 삭제 SLA** 다. 벤더 보존 기간이
아니다 — 벤더는 일수를 공개하지 않으며 우리는 그 숫자를 추정하지 않는다. lifecycle
Expiration 적용은 31-12 소관이고, 즉시 삭제 경로는 backend/scripts/delete_training_pair.py.

blur: `BLUR_OPTION` 은 배포 상수다(belle 결정 option-a = 'none'). 이 모듈은 **blur 를
실행하지 않는다** (2차 리뷰 H2-10) — before_png 는 호출측이 이미 로드해 넘긴 바이트다.
consentVersion/BLUR_OPTION 은 배포 상수이며 런타임에 결정 JSON 을 읽지 않는다. 값 일치는
build 테스트가 대조한다 (M2-05 + 3차 M3-02).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import re
import time

log = logging.getLogger("pair_store")
if not log.handlers:
    log.setLevel(logging.INFO)


# ── S3 canonical prefix (학습 산출 전용 — S3 ObjectCreated 미-notified) ──
PAIRS_PREFIX = "training/phase31/pairs/"
PAIRS_BUCKET_DEFAULT = "sunity-motion-pilot-videos"

# ── 배포 상수 (M2-05 / M3-02) — 런타임 JSON 읽기 금지, build 테스트가 대조한다 ──
CONSENT_VERSION = "pilot-optout-v1"
BLUR_OPTION = "none"  # belle option-a. 'pod_blur' 분기는 채택되지 않아 구현하지 않는다.
RETENTION_DAYS = 180  # 우리 페어 삭제 SLA. 벤더 보존 기간 아님(벤더 미공개).
PURPOSE = "phase22-v2-generation-head"

HMAC_KEYS_ENV = "PAIR_ID_HMAC_KEYS"
HMAC_KEYS_SSM_PARAM = "/sunity/motion/pair-id-hmac-keys"

# **삭제 전용 안정 레지스트리 — append-only, 항목 제거/rename 금지** (3차 M3-05).
# 삭제는 pairId 를 joint 이름으로 재계산하므로, 여기서 관절이 사라지면 과거 페어의
# pairId 를 다시 만들 수 없다 = 삭제 불가능한 고아 페어. fault_zoom.ARROW_JOINT_MAP 은
# 렌더 계약이라 축소될 수 있어 삭제 계약을 여기로 분리했다(양쪽 포함 관계는 테스트 고정).
HISTORICAL_PAIR_JOINTS: tuple[str, ...] = (
    "left_knee",
    "right_knee",
    "left_elbow",
    "right_elbow",
    "left_hip",
    "right_hip",
)

_HMAC_KEY_BYTES = 32
# 키 버전 ID 형식. 실제 배포된 SSM 파라미터의 버전 ID 는 `k1` 이라 플랜 초안의
# `^v[0-9]+$` 로는 fail-closed 되어 적재 자체가 불가능하다. 경로/구분자 문자를 배제한
# 짧은 토큰만 허용하는 선으로 넓혔다 (SUMMARY 편차 1 참조).
_KEY_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
_PAIR_ID_RE = re.compile(r"^[0-9a-f]{24}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_PRECONDITION_CODES = frozenset({"PreconditionFailed", "412"})
_NOT_FOUND_CODES = frozenset({"NoSuchKey", "NotFound", "404"})

_META_STR_FIELDS = (
    "consentVersion",
    "purpose",
    "joint",
    "model_id",
    "hmacKeyVersion",
    "beforeSha256",
    "afterSha256",
)
_META_INT_FIELDS = ("consentCapturedAtMs", "beforeSize", "afterSize", "storedAtMs")

# 멱등 판정에 쓰는 동일성 필드 (B5-03). storedAtMs/judge_confidence 같은 관측 잡음은
# 제외한다 — 재시도마다 달라지는 값을 넣으면 정상 재시도가 conflict 로 오판된다.
_IDENTITY_FIELDS = (
    "beforeSha256",
    "afterSha256",
    "consentVersion",
    "joint",
    "model_id",
    "purpose",
    "hmacKeyVersion",
)


# ─────────────────────── HMAC key set ───────────────────────


def _decode_key_material(raw: object) -> bytes | None:
    """키 문자열 → 32바이트. hex(64자) 우선, 아니면 strict base64.

    배포된 파라미터는 base64 이고 플랜 초안은 hex 를 명시했다. 64자 hex 는 base64 로
    해석하면 48바이트라 32바이트 게이트에서 어차피 탈락하므로, hex 선판정 후 base64
    라는 순서에 모호성이 없다. 어느 경로든 **정확히 32바이트만** 통과한다.
    """
    if not isinstance(raw, str) or not raw:
        return None
    text = raw.strip()
    if len(text) == 2 * _HMAC_KEY_BYTES:
        try:
            return bytes.fromhex(text)
        except ValueError:
            pass
    try:
        decoded = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        return None
    return decoded if len(decoded) == _HMAC_KEY_BYTES else None


def validate_hmac_key_set(obj: object) -> dict | None:
    """key set strict validator — store/delete/31-10 dry-run 공용 단일 출처 (3차 H3-11).

    통과 시 {"active": str, "keys": {version: bytes}}, 위반 시 None(=fail-closed).
    검증기가 여러 벌이면 한쪽만 느슨해져 무가명/약한 키로 적재되는 경로가 생긴다.
    """
    if not isinstance(obj, dict):
        return None
    if set(obj) != {"active", "keys"}:
        return None
    active = obj.get("active")
    keys = obj.get("keys")
    if not isinstance(active, str) or not isinstance(keys, dict) or not keys:
        return None
    if active not in keys:
        return None
    decoded: dict[str, bytes] = {}
    for version, raw in keys.items():
        if not isinstance(version, str) or not _KEY_VERSION_RE.match(version):
            return None
        material = _decode_key_material(raw)
        if material is None:
            return None
        decoded[version] = material
    return {"active": active, "keys": decoded}


def load_hmac_key_set() -> dict | None:
    """env `PAIR_ID_HMAC_KEYS`(JSON) → validate_hmac_key_set. 미설정/위반 시 None."""
    raw = os.environ.get(HMAC_KEYS_ENV)
    if not raw:
        return None
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        log.error("pair_store HMAC key set JSON 파싱 실패 — 적재 거부(fail-closed)")
        return None
    key_set = validate_hmac_key_set(obj)
    if key_set is None:
        log.error("pair_store HMAC key set 스키마 위반 — 적재 거부(fail-closed)")
    return key_set


def pair_id(uid: str, analysis_id: str, joint: str, *, hmac_key: bytes) -> str:
    """가명 페어 ID (H-04). 원문은 어디에도 저장되지 않는다."""
    if not isinstance(hmac_key, bytes) or len(hmac_key) != _HMAC_KEY_BYTES:
        raise ValueError("hmac_key 는 32바이트여야 한다")
    if not uid or not analysis_id or not joint:
        raise ValueError("uid/analysis_id/joint 필수")
    message = f"{uid}:{analysis_id}:{joint}".encode("utf-8")
    return hmac.new(hmac_key, message, hashlib.sha256).hexdigest()[:24]


# ─────────────────────── S3 key 계산 ───────────────────────


def pair_prefix(pid: str) -> str:
    return f"{PAIRS_PREFIX}{pid}/"


def before_key(pid: str) -> str:
    return f"{pair_prefix(pid)}before.png"


def after_key(pid: str) -> str:
    return f"{pair_prefix(pid)}after.png"


def meta_key(pid: str) -> str:
    return f"{pair_prefix(pid)}meta.json"


# ─────────────────────── S3 저수준 helper ───────────────────────


def _error_code(exc: Exception) -> str:
    """botocore ClientError 의 코드 추출 (botocore import 없이 duck-typing)."""
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = (response.get("Error") or {}).get("Code")
        if code:
            return str(code)
        status = (response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
        if status:
            return str(status)
    return ""


def _get_json(s3_client, bucket: str, key: str) -> dict | None:
    """부재 → None, 파손 → {}(스키마 검증에서 탈락). 그 외 예외는 그대로 전파."""
    try:
        obj = s3_client.get_object(Bucket=bucket, Key=key)
    except Exception as exc:  # noqa: BLE001 - 부재만 흡수, 나머지는 재전파
        if _error_code(exc) in _NOT_FOUND_CODES:
            return None
        raise
    body = obj["Body"].read()
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _put_if_absent(s3_client, bucket: str, key: str, body: bytes, content_type: str, created: list) -> str:
    """조건부 PUT. 'created' | 'exists'. 성공분은 정리 대상으로 기록한다."""
    try:
        resp = s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
            IfNoneMatch="*",
        )
    except Exception as exc:  # noqa: BLE001 - 412 만 흡수
        if _error_code(exc) in _PRECONDITION_CODES:
            return "exists"
        raise
    created.append((key, (resp or {}).get("VersionId")))
    return "created"


def _cleanup(s3_client, bucket: str, created: list) -> None:
    """이번 호출이 만든 object 만 best-effort 삭제 (H3-07). 예외는 삼킨다."""
    for key, version_id in reversed(created):
        params = {"Bucket": bucket, "Key": key}
        if version_id:
            params["VersionId"] = version_id
        try:
            s3_client.delete_object(**params)
        except Exception:  # noqa: BLE001 - 정리 실패는 lifecycle 이 2차 방어
            log.warning("pair_store 부분 적재 정리 실패 key=%s", key)
    created.clear()


def _verify_payload(s3_client, bucket: str, key: str, expected_sha: str, expected_size: int) -> str | None:
    """기존 payload 가 이번 expected 와 같은가. 정상 None, 아니면 사유 코드 (H6-04/H5-08)."""
    try:
        head = s3_client.head_object(Bucket=bucket, Key=key)
    except Exception as exc:  # noqa: BLE001
        if _error_code(exc) in _NOT_FOUND_CODES:
            return "missing"
        raise
    try:
        size = int(head.get("ContentLength", -1))
    except (TypeError, ValueError):
        return "size_mismatch"
    if size != int(expected_size):
        return "size_mismatch"
    try:
        obj = s3_client.get_object(Bucket=bucket, Key=key)
    except Exception as exc:  # noqa: BLE001
        if _error_code(exc) in _NOT_FOUND_CODES:
            return "missing"
        raise
    if hashlib.sha256(obj["Body"].read()).hexdigest() != expected_sha:
        return "hash_mismatch"
    return None


# ─────────────────────── meta 스키마 ───────────────────────


def _valid_meta_or_none(raw: object) -> dict | None:
    """commit marker 스키마 검증. 위반 시 None — 소비/멱등 판정 양쪽의 단일 출처."""
    if not isinstance(raw, dict):
        return None
    for field in _META_STR_FIELDS:
        if not isinstance(raw.get(field), str) or not raw.get(field):
            return None
    for field in _META_INT_FIELDS:
        value = raw.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return None
    if not _SHA256_RE.match(raw["beforeSha256"]) or not _SHA256_RE.match(raw["afterSha256"]):
        return None
    if raw["joint"] not in HISTORICAL_PAIR_JOINTS:
        return None
    if not isinstance(raw.get("blurApplied"), bool):
        return None
    if "anonymizerVersion" not in raw or "provenance" not in raw or "sourceGeneration" not in raw:
        return None
    return raw


def _identity_matches(existing: dict, expected: dict) -> bool:
    return all(existing.get(f) == expected.get(f) for f in _IDENTITY_FIELDS)


# ─────────────────────── 적재 ───────────────────────


def store_training_pair(
    s3_client,
    bucket: str,
    *,
    pair_id: str,
    hmac_key_version: str,
    joint: str,
    before_png: bytes,
    after_png: bytes,
    learning_opt_in: object,
    consent_captured_at_ms: int,
    quality: dict,
) -> str:
    """[틀린 폼 → 고쳐진 폼] 페어 1건 적재. 반환은 4상태 중 하나.

    'skipped_consent' — 동의 미통과. **S3 호출 0건**.
    'committed'       — marker 까지 확정(신규) 또는 기존 marker 와 동일(멱등 재시도).
    'conflict'        — 같은 pairId 에 다른 내용이 이미 있다. 덮어쓰지 않고 중단한다.
    'failed'          — 도중 실패. 이번 호출 생성분을 정리했고 marker 는 없다.

    pair_id/hmac_key_version 은 **caller 가 고정해 넘긴다** (B5-03). 이 함수 안에서
    active 키를 다시 고르면, postprocess 재시도 중 키가 회전됐을 때 같은 분석이 서로
    다른 pairId 로 두 번 적재된다.
    """
    # (1) 동의 게이트 — strict. 여기를 통과하기 전에는 S3 를 만지지 않는다.
    if learning_opt_in is not True:
        return "skipped_consent"

    if not isinstance(pair_id, str) or not _PAIR_ID_RE.match(pair_id):
        raise ValueError("pair_id 형식 위반 — caller 가 pair_id() 로 생성해야 한다")
    if not isinstance(hmac_key_version, str) or not _KEY_VERSION_RE.match(hmac_key_version):
        raise ValueError("hmac_key_version 형식 위반")
    if joint not in HISTORICAL_PAIR_JOINTS:
        raise ValueError(f"미등록 joint: {joint!r} — HISTORICAL_PAIR_JOINTS 에 먼저 추가")
    if not isinstance(before_png, bytes) or not isinstance(after_png, bytes):
        raise ValueError("before_png/after_png 는 bytes")
    model_id = (quality or {}).get("model_id")
    if not isinstance(model_id, str) or not model_id:
        raise ValueError("quality.model_id 필수 — provenance 없는 페어는 학습 불가")

    # (2) payload 해시 — 멱등 판정과 소비측 검증의 기준값.
    before_sha = hashlib.sha256(before_png).hexdigest()
    after_sha = hashlib.sha256(after_png).hexdigest()

    expected_meta = {
        "consentVersion": CONSENT_VERSION,
        "consentCapturedAtMs": int(consent_captured_at_ms),
        "purpose": PURPOSE,
        "joint": joint,
        "model_id": model_id,
        "judge_confidence": (quality or {}).get("judge_confidence"),
        "pose_error_deg": (quality or {}).get("pose_error_deg"),
        "hmacKeyVersion": hmac_key_version,
        "beforeSha256": before_sha,
        "afterSha256": after_sha,
        "beforeSize": len(before_png),
        "afterSize": len(after_png),
        "sourceGeneration": (quality or {}).get("source_generation"),
        "provenance": (quality or {}).get("provenance"),
        # blur 미실행 (H2-10) — option-a. 값은 관측 기록일 뿐 분기가 아니다.
        "blurApplied": False,
        "anonymizerVersion": None,
        "storedAtMs": int(time.time() * 1000),
    }

    mkey = meta_key(pair_id)
    bkey = before_key(pair_id)
    akey = after_key(pair_id)

    # (3) marker 를 먼저 읽는다 — 멱등의 근거 (B5-03).
    existing_raw = _get_json(s3_client, bucket, mkey)
    if existing_raw is not None:
        existing = _valid_meta_or_none(existing_raw)
        if existing is None:
            log.error("pair_store 기존 meta 스키마 위반 — 덮어쓰지 않는다 pair_id=%s", pair_id)
            return "conflict"
        if _identity_matches(existing, expected_meta):
            return "committed"
        log.error("pair_store 기존 meta 불일치 — 덮어쓰지 않는다 pair_id=%s", pair_id)
        return "conflict"

    created: list[tuple[str, str | None]] = []
    try:
        # (4) before → after 순 조건부 PUT. 412 는 재개 후보이되 검증 후에만 skip (H6-04).
        for key, payload, sha, size in (
            (bkey, before_png, before_sha, len(before_png)),
            (akey, after_png, after_sha, len(after_png)),
        ):
            if _put_if_absent(s3_client, bucket, key, payload, "image/png", created) == "exists":
                reason = _verify_payload(s3_client, bucket, key, sha, size)
                if reason is not None:
                    log.error(
                        "pair_store 기존 payload 불일치(%s) — marker 미기록 pair_id=%s key=%s",
                        reason,
                        pair_id,
                        key,
                    )
                    _cleanup(s3_client, bucket, created)
                    return "conflict"

        # (5) meta.json = commit marker. 마지막에 쓴다.
        body = json.dumps(expected_meta, ensure_ascii=False, sort_keys=True).encode("utf-8")
        if _put_if_absent(s3_client, bucket, mkey, body, "application/json", created) == "exists":
            # 동시 writer 가 먼저 확정했다. 내용이 같으면 멱등 성공.
            concurrent = _valid_meta_or_none(_get_json(s3_client, bucket, mkey))
            if concurrent is not None and _identity_matches(concurrent, expected_meta):
                return "committed"
            log.error("pair_store 동시 marker 불일치 pair_id=%s", pair_id)
            _cleanup(s3_client, bucket, created)
            return "conflict"
        return "committed"
    except Exception:  # noqa: BLE001 - 적재 실패가 분석 전체를 깨뜨리면 안 된다
        log.warning("pair_store 적재 실패 pair_id=%s — 부분 적재 정리", pair_id, exc_info=True)
        _cleanup(s3_client, bucket, created)
        return "failed"


# ─────────────────────── 소비 (consumer 전용 계약) ───────────────────────


def iter_pair_prefixes(s3_client, bucket: str):
    """PAIRS_PREFIX 하위 pair id 열거 — continuation token 끝까지 (M5-05)."""
    token = None
    while True:
        params = {"Bucket": bucket, "Prefix": PAIRS_PREFIX, "Delimiter": "/"}
        if token:
            params["ContinuationToken"] = token
        page = s3_client.list_objects_v2(**params) or {}
        for entry in page.get("CommonPrefixes") or []:
            prefix = entry.get("Prefix") or ""
            pid = prefix[len(PAIRS_PREFIX):].rstrip("/")
            if pid:
                yield pid
        if not page.get("IsTruncated"):
            return
        token = page.get("NextContinuationToken")
        if not token:
            return


def _open_pair(s3_client, bucket: str, pid: str) -> tuple[dict | None, str | None]:
    """(pair, reason). marker + payload 존재/hash 를 모두 통과한 것만 pair 로 반환."""
    meta = _valid_meta_or_none(_get_json(s3_client, bucket, meta_key(pid)))
    if meta is None:
        return None, "meta_invalid_or_missing"
    bkey, akey = before_key(pid), after_key(pid)
    reason = _verify_payload(s3_client, bucket, bkey, meta["beforeSha256"], meta["beforeSize"])
    if reason is not None:
        return None, f"before_{reason}"
    reason = _verify_payload(s3_client, bucket, akey, meta["afterSha256"], meta["afterSize"])
    if reason is not None:
        return None, f"after_{reason}"
    return {"pair_id": pid, "before_key": bkey, "after_key": akey, "meta": meta}, None


def list_committed_pairs(s3_client, bucket: str) -> dict:
    """학습 소비 진입점 (H4-11 + H5-08).

    consumer 는 before/after prefix 를 직접 list 하지 않는다 — marker 와 payload hash 를
    함께 통과한 페어만 "pairs" 로 나가고, 부재/변조는 "quarantine" 으로 분리된다.
    """
    pairs: list[dict] = []
    quarantine: list[dict] = []
    for pid in iter_pair_prefixes(s3_client, bucket):
        pair, reason = _open_pair(s3_client, bucket, pid)
        if pair is None:
            quarantine.append({"pair_id": pid, "reason": reason})
        else:
            pairs.append(pair)
    if quarantine:
        log.warning("pair_store quarantine=%d committed=%d", len(quarantine), len(pairs))
    return {"pairs": pairs, "quarantine": quarantine}


def load_committed_pair(s3_client, bucket: str, pid: str) -> dict | None:
    """단건 로드. marker/payload 검증 실패 시 None (조용한 부분 소비 금지)."""
    pair, reason = _open_pair(s3_client, bucket, pid)
    if pair is None:
        log.warning("pair_store 페어 소비 거부 pair_id=%s reason=%s", pid, reason)
        return None
    return pair
