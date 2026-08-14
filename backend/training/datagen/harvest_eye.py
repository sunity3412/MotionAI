#!/usr/bin/env python3
"""기계 눈(machine_eye) 원장 → 학습 원장 수확기 (quick 260814-j24).

belle 지시(2026-08-14): "학습으로 흘러들어가게 해내야 한다." 기계 눈 원장은 계속
쌓이는데 학습으로 가는 경로가 없었다 — 이 모듈이 그 입구다.

눈 원장 1행 = 관절 마킹 크롭 PNG + "이 관절이 접혔나 폈나" 판정(observed) + 근거
(reason) + 신뢰도. 특히 트랙 주장(claim/trackAngleDeg)과 눈 관측(observed)이 어긋난
행(match=false)은 keypoint 환각(belle 2026-08-11 지목 근본 결함)의 **라벨된 실례**이며
현 파이프라인보다 나아질 수 있는 감독 축이다 — 그래서 불일치 행은 절대 버리지 않는다.

── 프라이버시 판정 (LICENSE-AUDIT 7-3, 2026-08-14) ──────────────────────────
  P-1 user 측 크롭          hold — 적재 0.
        LICENSE-AUDIT 7-1(c) "anonymize 강제 불변, 적재 전 강제, 소급 불가"(D-12).
        얼굴 블러 미적용 크롭이라 belle 결정(B-1) 전까지 적재 금지.
  P-2 ref 측 크롭           admit.
        LICENSE-AUDIT 5-1 internal seed 17행 = "자사 촬영 + 파일럿 참가 동의서(D-12
        1겹)". build_jsonl._is_customer_source("internal") = False → D-12 가명처리
        요건 비대상. 같은 정은지 영상 통째가 이미 anonymized=false 로 학습 소비 중
        (manifest rows[0])이므로 그 크롭이 원본보다 엄격할 근거가 없다.
  P-3 운영 S3 results/…/eye  기본 hold.
        LICENSE-AUDIT 7-1(d) 컷오프 2026-07-13 이후 문서는 learningOptIn=true 엄격.
        눈 원장은 2026-08 생성 = 컷오프 이후 → 동의 실측 없이는 fail-safe 보류.
        동의 실측(consent=True)이 있고 ref 측이면 P-2 논리로 admit.
  P-4 수확 행의 식별자       uid·analysisId 금지.
        LICENSE-AUDIT 119행 "매니페스트에 uid·사용자 식별자 필드 금지(테스트 fence)"
        + 7-1(f) "uid/analysisId 비파생, video_hash 기반만". eye 행 식별자는 크롭
        PNG content hash 단독(assert_no_identifier_keys 가 키·값 양쪽을 막는다).
  P-5 motion 미해결 행       hold.
        motion 없는 샘플은 build_jsonl._balance_media 에서 무조건 통과(m is None 이면
        kept) → 균등 규율 우회 = dump-all. 제약 위반이므로 fail-closed.

  추가(2026-08-14 오케스트레이터 해제): 동의 플래그 확인을 위한 Firestore **읽기**는
  허용됐다. learningOptIn=false 는 LICENSE-AUDIT 7-1(b) 에 따라 어떤 조합에서도 무조건
  제외(consent_denied) — 이 분기가 최우선이다. 실측 결과(true/false/부재)는 행의
  consent_flag 에 그대로 박제한다(T-j24-07 provenance).

순수층은 numpy/boto3/네트워크 0 이며 test_harvest_eye.py 가 계약을 고정한다.
I/O 껍데기(리포 스캔 / S3 읽기 / 원장 병합)는 파일 하단에 분리한다. S3 는 읽기 전용
(list_objects_v2 + get_object)이며 쓰기 호출은 이 모듈에 존재하지 않는다.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("harvest_eye")
if not log.handlers:
    log.setLevel(logging.INFO)

_HERE = Path(__file__).resolve()
_BACKEND = _HERE.parents[2]
_REPO_ROOT = _HERE.parents[3]

EYE_MANIFEST_PATH = _BACKEND / "training" / "data" / "eye_manifest.json"
MANIFEST_PATH = _BACKEND / "training" / "data" / "manifest.json"

SCHEMA_VERSION = "eye-v1.0"  # eye-v1.0 (2026-08-14, j24): 눈 크롭 수확 원장 초판.

# 크롭 미디어 prefix — 이 접두 밖은 금지(학습 산출 전용, S3 ObjectCreated 미-notified).
MEDIA_PREFIX = "training/phase22/eye/"

# 행 계약. score/severity/overall/points 계열은 **구조적으로 부재**한다 — 눈은 짚기·
# 관측만 하고 점수는 감점 엔진이 소유한다(D-01 불변식의 eye 판,
# [[scoring-must-be-transparent-deduction-tally]]). analysis_id/uid 계열 키도 부재(P-4).
EYE_ROW_KEYS: tuple[str, ...] = (
    "claim",               # 트랙(파이프라인) 주장: bent | extended.
    "collected_at",        # 수확 시각(UTC ISO8601).
    "confidence",          # 눈 판정 신뢰도.
    "consent_flag",        # 동의 실측치(True/False/None) — provenance, 판정 근거 박제.
    "disposition",         # admit | hold.
    "disposition_reason",  # P-1~P-5 / consent 분기 사유.
    "eye_id",              # = media_sha16 (식별자는 content hash 단독, P-4).
    "frame_idx",
    "joint",
    "limb",                # 눈이 본 사지 종류(arm|leg|other|unclear) — 마크-전위 축.
    "media_key",           # training/phase22/eye/{sha16}.png
    "media_sha16",
    "motion",
    "motion_source",       # entry | operator:{근거} — 추정 주입 금지.
    "observed",            # 눈 관측: bent | extended | unclear | off_body.
    "reason",              # 눈이 그렇게 본 근거(자유텍스트).
    "sec",
    "side",                # user | ref.
    "source",              # internal_machine_eye
    "source_kind",         # repo_evidence | s3_operational
    "source_ref",          # uid 비포함 — 리포 상대경로#idx 또는 s3-operational:{sha16}
    "track_angle_deg",     # 트랙이 잰 각도(불일치 진단 축).
    "track_claim_agrees",  # 원장 match — False 가 keypoint 환각 라벨.
    "uploaded",            # 크롭 S3 업로드 여부(이번 사이클 전량 False).
    "usage",               # training-only-no-redistribution
)

USAGE = "training-only-no-redistribution"
SOURCE = "internal_machine_eye"

SOURCE_KIND_REPO = "repo_evidence"
SOURCE_KIND_S3 = "s3_operational"

# P-4 fence — 금지 키(대소문자 무관 비교).
FORBIDDEN_IDENTIFIER_KEYS: tuple[str, ...] = (
    "uid", "uidhash", "analysisid", "analysis_id", "email", "user_id", "userid",
    "phone", "s3_key", "key",
)

# Firebase uid 패턴 — 실측 fvcNXzEqKjgqVxRPVSj1iwFnIpn2 (28자, 영문+숫자 혼합).
# 16자 content hash(media_sha16)와 겹치지 않도록 20자 이상 + 숫자·영문 동시 보유만 잡는다.
_TOKEN_RE = re.compile(r"[A-Za-z0-9]{20,}")


# ===========================================================================
# 순수층 — 네트워크/boto3/numpy 0.
# ===========================================================================
def utc_now_iso() -> str:
    """UTC ISO8601 (초 정밀, Z 접미) — phase22_watch 관례 동일."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ledger_shape(doc) -> str:
    """원장 JSON 형태 판별 — analysis_entries | flat_motion | flat | other."""
    if not isinstance(doc, dict):
        return "other"
    if "entries" in doc:
        # entries 키가 있는데 list 가 아니면 손상 — flat 로 오해석하면 쓰레기 행이 난다.
        return "analysis_entries" if isinstance(doc["entries"], list) else "other"
    if not doc:
        return "other"
    if doc.get("motion"):
        return "flat_motion"
    return "flat"


def iter_ledger_entries(doc) -> list[dict]:
    """원장 JSON → entry 리스트. 3형태 전부 흡수, 그 외(list·손상)는 빈 리스트.

    1. analysisId + entries 배열  — 운영/Pod 형.
    2. flat 단일 entry            — 발굴 하네스 형.
    3. flat 단일 entry + motion   — 스윕 형(motion 필드 보유).
    """
    shape = ledger_shape(doc)
    if shape == "analysis_entries":
        return [e for e in doc["entries"] if isinstance(e, dict)]
    if shape in ("flat", "flat_motion"):
        return [doc]
    return []


def content_hash(png_bytes: bytes) -> str:
    """크롭 바이트 → sha256 앞 16자. 같은 바이트면 같은 해시(멱등 키, P-4 식별자)."""
    return hashlib.sha256(png_bytes or b"").hexdigest()[:16]


def media_key(sha16: str) -> str:
    """수확 크롭의 S3 키 — 이 접두 밖은 금지."""
    return f"{MEDIA_PREFIX}{sha16}.png"


# ── 앱 미오픈 내부 계정 (belle 판정 2026-08-14) ────────────────────────────────
# belle 원문: "앱 계정은 그냥 우리거야 아직 앱이 오픈되지도 않음".
# P-1(user 측 가명처리)·P-3(옵트인 미검증)의 hold 근거는 **보호할 제3자가 있을 때**
# 성립한다. 앱이 외부에 공개된 적이 없어 외부 사용자 계정 자체가 존재하지 않으므로,
# 아래 명단의 계정에서 나온 크롭은 자사 촬영분과 같은 층(LICENSE-AUDIT 5-1 internal)
# 으로 다룬다.
#
# ★명단은 **오늘 존재가 확인된 자사 계정만** 담는다. 명단 밖 uid 는 기존 게이트가
#   그대로 적용되므로 앱 오픈 후 생기는 실제 수강생 계정은 자동으로 보호된다 —
#   전역 우회 플래그를 두지 않은 이유가 이것이다(화이트리스트가 조용히 넓어지지 않음).
# ★만료 조건: 앱이 외부에 공개되는 순간 이 근거는 소멸한다. 그때 이 상수를 비우고
#   learningOptIn 실측만 남겨야 한다 (LICENSE-AUDIT §7-4).
# ★uid 원문을 코드에 두지 않는다 (P-4 규율) — sha256 앞 16자로만 대조한다.
PRELAUNCH_INTERNAL_UID_SHA16 = frozenset({
    "a7430c9c130cdc25",  # 재분석 러너 계정 (p34fresh* 문서 + 운영 eye 원장 소유)
    "8ada262a78411cb5",  # 픽스처 영상 소유 계정 (pdshapefault/peterpanfault 업로드)
    "2809cb6912668209",  # belle 등록 계정
})
OWNER_PRELAUNCH_INTERNAL = "prelaunch_internal"
OWNER_UNVERIFIED = "unverified"


def owner_scope(uid) -> str:
    """uid → 소유 범위. 명단 밖·미상은 전부 unverified (fail-closed).

    uid 원문은 반환값에 실리지 않는다 — 호출부는 범위 문자열만 행에 남긴다(P-4).
    """
    if not isinstance(uid, str) or not uid:
        return OWNER_UNVERIFIED
    digest = hashlib.sha256(uid.encode("utf-8")).hexdigest()[:16]
    return (
        OWNER_PRELAUNCH_INTERNAL
        if digest in PRELAUNCH_INTERNAL_UID_SHA16
        else OWNER_UNVERIFIED
    )


def consent_disposition(
    side, motion, source_kind, consent=None, owner=OWNER_UNVERIFIED
) -> tuple[str, str]:
    """(disposition, reason) — 모듈 docstring P-1~P-5 표의 기계적 적용.

    우선순위(테스트로 고정):
      0. consent is False        → hold/consent_denied      (7-1(b) 무조건 제외)
      1. 미오픈 내부 계정 + motion → admit/prelaunch_internal (belle 260814)
      2. ref + repo_evidence + motion            → admit/internal_seed_ref            (P-2)
      3. ref + s3_operational + motion + consent → admit/internal_seed_ref_optin_verified
      4. side == user            → hold/customer_anonymize_required                   (P-1)
      5. s3_operational          → hold/optin_unverified_post_cutoff                  (P-3)
      6. motion 미해결           → hold/motion_unknown                                (P-5)
      7. 그 외                   → hold/unclassified

    0 이 1 보다 우선인 것은 의도다 — 명시적 거부(learningOptIn=false)는 자사 계정
    이라도 뒤집지 않는다. 5(P-5 motion 미해결)도 내부 계정에서 유지된다: 균등 규율
    우회를 막는 축이라 동의와 층이 다르다.

    명단 밖(owner=unverified)은 아래 4·5 가 그대로 걸린다 — 앱 오픈 후 실제
    수강생 크롭이 이 경로로 새지 않게 하는 회귀 방지선이다.
    """
    if consent is False:
        return "hold", "consent_denied"
    if owner == OWNER_PRELAUNCH_INTERNAL:
        # 내부 계정에서 동의 축은 소멸했다 — 남는 축은 P-5(motion 미해결) 하나뿐이다.
        # 여기서 바로 반환하지 않으면 motion 없는 내부 행이 아래 user 분기에 걸려
        # `customer_anonymize_required` 로 **잘못 진단**된다(실제 막는 축은 motion).
        if motion:
            return "admit", "prelaunch_internal"
        return "hold", "motion_unknown"
    if side == "ref" and motion:
        if source_kind == SOURCE_KIND_REPO:
            return "admit", "internal_seed_ref"
        if source_kind == SOURCE_KIND_S3 and consent is True:
            return "admit", "internal_seed_ref_optin_verified"
    if side == "user":
        return "hold", "customer_anonymize_required"
    if source_kind == SOURCE_KIND_S3:
        return "hold", "optin_unverified_post_cutoff"
    if not motion:
        return "hold", "motion_unknown"
    return "hold", "unclassified"


def _num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def entry_to_row(
    entry: dict,
    *,
    source_kind: str,
    source_ref: str,
    motion,
    motion_source,
    png_bytes: bytes,
    collected_at: str,
    consent=None,
    owner: str = OWNER_UNVERIFIED,
) -> dict | None:
    """눈 원장 entry → 학습 원장 행. 라벨 없는 행(observed=="error")은 None.

    match(트랙-눈 일치)는 track_claim_agrees 로 **이름을 보존한 채** 옮기며, False
    행도 반드시 행을 만든다(불일치 = 이 코퍼스의 최고가치, 버리면 안 된다).

    limb 는 반드시 함께 옮긴다 — 원장의 match 는 card_gates._eye_verdict 의 2단 판정
    (상태 일치 AND 기대 사지 일치)이라, limb 없이는 "상태는 같은데 agrees=false"
    (마크가 다른 사지에 얹힌 경우)가 설명 불가능한 잡음이 된다.
    """
    if not isinstance(entry, dict):
        return None
    observed = entry.get("observed")
    if observed == "error":
        return None  # 라벨 없음 — fail-closed(실측 0건이나 계약으로 고정).
    sha16 = content_hash(png_bytes)
    disposition, reason = consent_disposition(
        entry.get("side"), motion, source_kind, consent=consent, owner=owner
    )
    agrees = entry.get("match")
    row = {
        "claim": entry.get("claim"),
        "collected_at": collected_at,
        "confidence": _num(entry.get("confidence")),
        "consent_flag": consent,
        "disposition": disposition,
        "disposition_reason": reason,
        "eye_id": sha16,
        "frame_idx": _num(entry.get("frameIdx")),
        "joint": entry.get("joint"),
        "limb": entry.get("limb"),
        "media_key": media_key(sha16),
        "media_sha16": sha16,
        "motion": motion or None,
        "motion_source": motion_source,
        "observed": observed,
        "reason": entry.get("reason"),
        "sec": _num(entry.get("sec")),
        "side": entry.get("side"),
        "source": SOURCE,
        "source_kind": source_kind,
        "source_ref": source_ref,
        "track_angle_deg": _num(entry.get("trackAngleDeg")),
        "track_claim_agrees": agrees if isinstance(agrees, bool) else None,
        "uploaded": False,
        "usage": USAGE,
    }
    return {k: row[k] for k in sorted(EYE_ROW_KEYS)}


def _looks_like_firebase_uid(token: str) -> bool:
    """20자 이상 영숫자 연속 + 숫자·영문 동시 보유 = Firebase uid 패턴."""
    return any(c.isdigit() for c in token) and any(c.isalpha() for c in token)


def assert_no_identifier_keys(row: dict) -> None:
    """행에 uid/analysisId 계열 키 또는 uid 패턴 값이 있으면 ValueError (P-4).

    키 검사만으로는 부족하다 — 운영 S3 키(results/{uid}/{aid}/eye/…)가 source_ref 등
    자유 필드에 통째로 실려오는 경로가 실재하므로 값도 스캔한다.
    """
    for key in row or {}:
        if str(key).lower() in FORBIDDEN_IDENTIFIER_KEYS:
            raise ValueError(f"식별자 키 금지(P-4): {key!r}")
    for key, value in (row or {}).items():
        if not isinstance(value, str):
            continue
        for token in _TOKEN_RE.findall(value):
            if _looks_like_firebase_uid(token):
                raise ValueError(
                    f"식별자 패턴 값 금지(P-4): {key}={token[:6]}…({len(token)}자)"
                )


# 재판정이 갱신할 수 있는 필드 — 판정 결과와 그 근거뿐이다. 관측·이미지·출처는
# 불변(이력이 진실). 이 화이트리스트 밖 필드는 재판정으로 절대 바뀌지 않는다.
READJUDICATE_FIELDS = ("disposition", "disposition_reason", "consent_flag")


def merge_rows(existing, new, readjudicate: bool = False) -> tuple[list[dict], int, int]:
    """eye_id 기준 멱등 병합 → (merged, added, skipped). 기존 행 무변형(append-only).

    같은 원장을 2회 수확하면 added 0 / skipped N 이 되고, 기존 행은 새 값으로 덮이지
    않는다 — 수확 원장은 append-only 이며 이력이 진실이다.

    readjudicate=True 면 기존 행의 **판정 필드만**(READJUDICATE_FIELDS) 새 판정으로
    갱신한다. 정책 근거가 바뀌었을 때(예: belle 판정으로 hold 근거 소멸) 원장을
    지우고 다시 만들지 않고도 판정을 따라가기 위한 명시적 경로다 — 행 자체는
    보존되므로 append-only 취지(이력 유실 금지)는 지켜진다. 관측치·이미지 해시·
    출처는 갱신 대상이 아니다.
    """
    merged = list(existing or [])
    seen = {r.get("eye_id") for r in merged if r.get("eye_id")}
    by_id = {r.get("eye_id"): r for r in merged if r.get("eye_id")}
    added = skipped = 0
    for row in new or []:
        eid = row.get("eye_id")
        if not eid or eid in seen:
            skipped += 1
            if readjudicate and eid in by_id:
                for field in READJUDICATE_FIELDS:
                    by_id[eid][field] = row.get(field)
            continue
        seen.add(eid)
        merged.append(row)
        by_id[eid] = row
        added += 1
    return merged, added, skipped


def _bump(counter: dict, key) -> None:
    k = key if key is not None else "(none)"
    counter[k] = counter.get(k, 0) + 1


def summarize(rows) -> dict:
    """규모 실측 리포트의 단일 출처 — 총계/disposition/불일치/관절/관측/측."""
    by_disposition: dict = {}
    by_reason: dict = {}
    by_joint: dict = {}
    by_observed: dict = {}
    by_side: dict = {}
    by_source_kind: dict = {}
    by_arrow: dict = {}
    mismatch = admit_mismatch = admitted = 0
    for r in rows or []:
        _bump(by_disposition, r.get("disposition"))
        _bump(by_reason, r.get("disposition_reason"))
        _bump(by_joint, r.get("joint"))
        _bump(by_observed, r.get("observed"))
        _bump(by_side, r.get("side"))
        _bump(by_source_kind, r.get("source_kind"))
        _bump(by_arrow, f"{r.get('claim')}->{r.get('observed')}")
        if r.get("track_claim_agrees") is False:
            mismatch += 1
            if r.get("disposition") == "admit":
                admit_mismatch += 1
        if r.get("disposition") == "admit":
            admitted += 1
    return {
        "total": len(rows or []),
        "admitted": admitted,
        "mismatch": mismatch,
        "admit_mismatch": admit_mismatch,
        "by_disposition": by_disposition,
        "by_disposition_reason": by_reason,
        "by_joint": by_joint,
        "by_observed": by_observed,
        "by_side": by_side,
        "by_source_kind": by_source_kind,
        "by_claim_arrow": by_arrow,
    }


# ── 배치 등재 규약 (phase22_watch 준용, eye- 접두 자체 산출) ─────────────────
def compute_eye_batch_id(manifest: dict, today_yymmdd: str) -> str:
    """batch_id = eye-YYMMDD (같은 날 2회차부터 -2,-3 접미 — compute_batch_id 관례)."""
    base = f"eye-{today_yymmdd}"
    existing = {
        b.get("batch_id")
        for b in (manifest or {}).get("_meta", {}).get("collection_batches", [])
    }
    if base not in existing:
        return base
    n = 2
    while f"{base}-{n}" in existing:
        n += 1
    return f"{base}-{n}"


def make_eye_batch_entry(batch_id: str, trigger: str) -> dict:
    """눈 수확 배치 entry — manifest.rows 무접촉임을 ledger 필드로 명시한다.

    눈 크롭은 영상 행이 아니므로 manifest.rows 가 아니라 eye_manifest.json 이 소유한다.
    이것이 기존 3트랙 무회귀의 구조적 보장이다(T-j24-03/04).
    """
    return {
        "batch_id": batch_id,
        "opened_at": utc_now_iso(),
        "approved_by": "belle",
        "trigger": trigger,
        "ledger": "training/data/eye_manifest.json",
        "sources": {"eye_repo_evidence": 0, "eye_s3_operational": 0},
        "scanned_rows": 0,
        "scanned_admit": 0,
        "scanned_hold": 0,
        "new_rows": 0,
        "skipped_existing": 0,
        "ledger_rows_after": None,
        "ledger_admit_after": None,
        "ledger_hold_after": None,
        "status": "open",
        "cumulative_rows_after": None,
    }


# ===========================================================================
# I/O 껍데기 — 리포 evidence 스캔 (읽기 전용).
# ===========================================================================
def iter_eye_ledger_dirs(root) -> list[Path]:
    """이름에 eye_ledger 를 포함하는 디렉토리 전부(pod_eye_ledger 포함)."""
    root = Path(root)
    if not root.exists():
        return []
    out = {d for d in root.rglob("*") if d.is_dir() and "eye_ledger" in d.name}
    return sorted(out)


def _resolve_png(json_path: Path, entry: dict) -> Path | None:
    """크롭 PNG 해결 — entry key 의 basename, 없으면 JSON 과 같은 stem 의 .png."""
    key = entry.get("key")
    if key:
        cand = json_path.parent / Path(str(key)).name
        if cand.exists():
            return cand
    cand = json_path.with_suffix(".png")
    return cand if cand.exists() else None


def _rel(path: Path, repo_root: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(repo_root))
    except ValueError:
        return Path(path).name


def resolve_motion(entry, *, doc_analysis_id, dir_rel, motion_map, analysis_motion_map,
                   motion_alias) -> tuple[object, object]:
    """(motion, motion_source) — 근거 있는 값만 채택한다(추정 금지).

    1. entry.motion 이 있으면 채택. 단 motion_alias 에 근거 문서가 등재된 하네스 이름은
       manifest 어휘의 reference motion id 로 정규화한다 — 어휘가 다르면 build_jsonl 의
       val-motion leakage 대조가 원리적으로 발화하지 않아 게이트가 장식이 된다.
    2. 원장 doc 의 analysisId 가 analysis_motion_map 에 있으면 채택(Firestore 실측 등).
    3. 디렉토리 단위 motion_map 에 있으면 채택(해당 사이클 코드/문서 근거).
    4. 그 외 → (None, None) → consent_disposition 이 hold(P-5).
    근거 문자열(evidence) 없는 주입은 어느 경로에서도 허용하지 않는다.
    """
    raw = entry.get("motion")
    if raw:
        alias = (motion_alias or {}).get(raw)
        if alias and alias.get("motion") and alias.get("evidence"):
            return alias["motion"], f"entry+operator:{alias['evidence']}"
        return raw, "entry"
    for key, table in ((doc_analysis_id, analysis_motion_map), (dir_rel, motion_map)):
        hit = (table or {}).get(key) or {}
        if hit.get("motion") and hit.get("evidence"):
            return hit["motion"], f"operator:{hit['evidence']}"
    return None, None


def scan_repo_evidence(
    root,
    *,
    repo_root=None,
    motion_map=None,
    analysis_motion_map=None,
    motion_alias=None,
    consent_map=None,
    collected_at=None,
) -> dict:
    """리포 evidence 눈 원장 전수 스캔(읽기 전용, 파일 쓰기 0).

    motion 해결은 resolve_motion 이 소유한다(근거 없는 주입 금지).
    PNG 미해결 행은 fail-closed(행 생성 안 함 + 카운터 노출).
    """
    repo_root = Path(repo_root or _REPO_ROOT).resolve()
    collected_at = collected_at or utc_now_iso()
    motion_map = motion_map or {}
    consent_map = consent_map or {}

    rows: list[dict] = []
    shapes: dict = {}
    unresolved: list[str] = []
    entries_seen = 0
    files_seen = 0
    error_rows = 0

    for d in iter_eye_ledger_dirs(root):
        dir_rel = _rel(d, repo_root)
        for json_path in sorted(d.rglob("*.json")):
            files_seen += 1
            try:
                doc = json.loads(json_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                _bump(shapes, "unreadable")
                continue
            _bump(shapes, ledger_shape(doc))
            doc_analysis_id = (doc or {}).get("analysisId") if isinstance(doc, dict) else None
            analysis_consent = consent_map.get(doc_analysis_id)
            for idx, entry in enumerate(iter_ledger_entries(doc)):
                entries_seen += 1
                if entry.get("observed") == "error":
                    error_rows += 1
                    continue
                png = _resolve_png(json_path, entry)
                if png is None:
                    unresolved.append(f"{_rel(json_path, repo_root)}#{idx}")
                    continue
                motion, motion_source = resolve_motion(
                    entry,
                    doc_analysis_id=doc_analysis_id,
                    dir_rel=dir_rel,
                    motion_map=motion_map,
                    analysis_motion_map=analysis_motion_map,
                    motion_alias=motion_alias,
                )
                row = entry_to_row(
                    entry,
                    source_kind=SOURCE_KIND_REPO,
                    source_ref=f"{_rel(json_path, repo_root)}#{idx}",
                    motion=motion,
                    motion_source=motion_source,
                    png_bytes=png.read_bytes(),
                    collected_at=collected_at,
                    consent=analysis_consent,
                    # 리포 evidence 는 자사 하네스가 리포/픽스처 데이터로 생산한
                    # 원장이다 — 외부 업로드 경로를 거치지 않는다(계정 자체가 없음).
                    # 앱 오픈 후에도 이 경로로 수강생 데이터가 들어올 수 없다.
                    owner=OWNER_PRELAUNCH_INTERNAL,
                )
                if row is None:
                    error_rows += 1
                    continue
                assert_no_identifier_keys(row)
                rows.append(row)

    return {
        "rows": rows,
        "summary": summarize(rows),
        "files": files_seen,
        "entries": entries_seen,
        "shapes": shapes,
        "png_unresolved": len(unresolved),
        "png_unresolved_refs": unresolved,
        "observed_error_rows": error_rows,
    }


# ===========================================================================
# I/O 껍데기 — 운영 S3 스캔 (읽기 전용: list_objects_v2 + get_object 만).
# ===========================================================================
def scan_s3(
    bucket: str,
    prefix: str,
    s3_client,
    *,
    consent_map=None,
    collected_at=None,
    max_ledgers: int | None = None,
) -> dict:
    """운영 S3 results/{uid}/{aid}/eye/ledger.json 읽기 전용 수확.

    source_ref 는 uid 를 절대 담지 않는다 — 내용 파생(s3-operational:{sha16}) 단독.
    쓰기 API(put_object/upload_file/delete_object)는 호출하지 않는다.
    """
    consent_map = consent_map or {}
    collected_at = collected_at or utc_now_iso()
    rows: list[dict] = []
    unresolved: list[str] = []
    ledgers = 0
    entries_seen = 0

    paginator = s3_client.get_paginator("list_objects_v2")
    ledger_keys: list[str] = []
    crop_keys: set[str] = set()
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []) or []:
            key = obj["Key"]
            if "/eye/" not in key:
                continue
            if key.endswith("/eye/ledger.json"):
                ledger_keys.append(key)
            elif key.endswith(".png"):
                crop_keys.add(key)

    for lkey in sorted(ledger_keys):
        if max_ledgers is not None and ledgers >= max_ledgers:
            break
        ledgers += 1
        body = s3_client.get_object(Bucket=bucket, Key=lkey)["Body"].read()
        try:
            doc = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            unresolved.append("ledger-unreadable")
            continue
        analysis_consent = consent_map.get((doc or {}).get("analysisId"))
        base = lkey.rsplit("/", 1)[0]
        for idx, entry in enumerate(iter_ledger_entries(doc)):
            entries_seen += 1
            ckey = entry.get("key") or ""
            candidate = f"{base}/{ckey.rsplit('/', 1)[-1]}" if ckey else ""
            if candidate not in crop_keys:
                unresolved.append(f"s3#{idx}")
                continue
            png_bytes = s3_client.get_object(Bucket=bucket, Key=candidate)["Body"].read()
            sha16 = content_hash(png_bytes)
            # 소유 계정 = 운영 키 규약 results/{uid}/{aid}/eye/… 의 uid.
            # uid 는 여기서만 쓰이고 행에는 범위 문자열도 실리지 않는다(P-4).
            lkey_parts = lkey.split("/")
            row = entry_to_row(
                entry,
                source_kind=SOURCE_KIND_S3,
                source_ref=f"s3-operational:{sha16}",
                motion=entry.get("motion") or None,
                motion_source="entry" if entry.get("motion") else None,
                png_bytes=png_bytes,
                collected_at=collected_at,
                consent=analysis_consent,
                owner=owner_scope(lkey_parts[1] if len(lkey_parts) > 2 else None),
            )
            if row is None:
                continue
            assert_no_identifier_keys(row)
            rows.append(row)

    return {
        "rows": rows,
        "summary": summarize(rows),
        "ledgers": ledgers,
        "entries": entries_seen,
        "png_unresolved": len(unresolved),
    }


# ===========================================================================
# 원장 로드/저장 + 배치 등재.
# ===========================================================================
def load_eye_manifest() -> dict:
    if not EYE_MANIFEST_PATH.exists():
        return {
            "_meta": {
                "phase": "quick-260814-j24",
                "schema_version": SCHEMA_VERSION,
                "generated_by": "backend/training/datagen/harvest_eye.py",
                "usage_policy": USAGE,
                "privacy_verdict": "LICENSE-AUDIT 7-3 (P-1~P-5, 2026-08-14)",
                "identifier_policy": "크롭 content hash 단독 — uid/analysisId 금지(P-4)",
                "owner_note": (
                    "눈 크롭은 영상 행이 아니므로 manifest.json rows 가 아니라 이 원장이 "
                    "소유한다 — 기존 3트랙 무회귀의 구조적 보장"
                ),
                "batches": [],
            },
            "rows": [],
        }
    return json.loads(EYE_MANIFEST_PATH.read_text(encoding="utf-8"))


def save_eye_manifest(manifest: dict) -> None:
    EYE_MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _load_watch_invariants():
    """phase22_watch.assert_ledger_invariants 재사용 — 마감 무결성 규약 재발명 금지."""
    scripts = str(_BACKEND / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import phase22_watch  # noqa: PLC0415 - lazy(스크립트 경로 주입 후)

    return phase22_watch.assert_ledger_invariants


# ===========================================================================
# CLI — 2단 (dry-run 기본 / --run 기록).
# ===========================================================================
def _print_summary(title: str, payload: dict) -> None:
    s = payload["summary"]
    print(f"\n[{title}] 행 {s['total']} (admit {s['admitted']} / hold {s['total'] - s['admitted']})"
          f" | 불일치 {s['mismatch']} (admit 중 {s['admit_mismatch']})")
    for name in ("by_disposition_reason", "by_side", "by_joint", "by_observed",
                 "by_claim_arrow", "by_source_kind"):
        items = sorted(s[name].items(), key=lambda kv: (-kv[1], str(kv[0])))
        print(f"  {name}: " + ", ".join(f"{k}={v}" for k, v in items))


def _load_json_arg(path):
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="기계 눈 원장 수확기 — --dry-run 안전(쓰기 0) / --run 원장 기록"
    )
    ap.add_argument("--root", default=str(_REPO_ROOT / ".planning"))
    ap.add_argument("--repo-root", default=str(_REPO_ROOT))
    ap.add_argument("--motion-map", default=None,
                    help="{리포상대 eye_ledger 디렉토리: {motion, evidence}} JSON 경로")
    ap.add_argument("--analysis-motion-map", default=None,
                    help="{analysisId: {motion, evidence}} JSON 경로(Firestore 실측 등)")
    ap.add_argument("--motion-alias", default=None,
                    help="{하네스 motion 이름: {motion, evidence}} JSON 경로(어휘 정규화)")
    ap.add_argument("--consent-map", default=None,
                    help="{analysisId: true|false|null} 동의 실측 JSON 경로(Firestore read)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="스캔 + 요약만(기본, 쓰기 0)")
    mode.add_argument("--run", action="store_true", help="eye_manifest 병합 기록 + 배치 등재")
    ap.add_argument("--with-s3", action="store_true", help="운영 S3 읽기 전용 스캔 포함")
    ap.add_argument("--bucket", default="sunity-motion-pilot-videos")
    ap.add_argument("--s3-prefix", default="results/")
    ap.add_argument("--max-ledgers", type=int, default=None)
    ap.add_argument(
        "--readjudicate", action="store_true",
        help="기존 행의 판정 필드만 현행 규칙으로 갱신 (정책 근거 변경 시. 행·관측치는 보존)",
    )
    args = ap.parse_args(argv)

    collected_at = utc_now_iso()
    repo = scan_repo_evidence(
        args.root,
        repo_root=args.repo_root,
        motion_map=_load_json_arg(args.motion_map),
        analysis_motion_map=_load_json_arg(args.analysis_motion_map),
        motion_alias=_load_json_arg(args.motion_alias),
        consent_map=_load_json_arg(args.consent_map),
        collected_at=collected_at,
    )
    print(f"[repo] 원장 파일 {repo['files']} / entry {repo['entries']} / 형태 {repo['shapes']}"
          f" | PNG 미해결 {repo['png_unresolved']} | observed=error {repo['observed_error_rows']}")
    _print_summary("repo_evidence", repo)

    s3_payload = {"rows": [], "summary": summarize([]), "ledgers": 0, "entries": 0,
                  "png_unresolved": 0}
    s3_error = None
    if args.with_s3:
        try:
            import boto3  # noqa: PLC0415 - lazy(S3 스캔 시에만).

            client = boto3.client("s3", region_name="ap-northeast-2")
            s3_payload = scan_s3(
                args.bucket, args.s3_prefix, client,
                consent_map=_load_json_arg(args.consent_map),
                collected_at=collected_at, max_ledgers=args.max_ledgers,
            )
            print(f"\n[s3] ledger {s3_payload['ledgers']} / entry {s3_payload['entries']}"
                  f" | 크롭 미해결 {s3_payload['png_unresolved']}")
            _print_summary("s3_operational", s3_payload)
        except Exception as exc:  # noqa: BLE001 - 자격증명/권한 실패는 스킵 후 명기.
            s3_error = str(exc)[:200]
            print(f"\n[s3] 스캔 실패 — 스킵(전량 hold 라 결과물 영향 0): {s3_error}",
                  file=sys.stderr)

    all_rows = repo["rows"] + s3_payload["rows"]
    total = summarize(all_rows)
    _print_summary("TOTAL", {"summary": total})

    if not args.run:
        print("\n[dry-run] 파일 쓰기 0. 기록은 --run.")
        return 0

    # ── --run: eye_manifest 병합 + manifest.json 배치 등재 ────────────────────
    eye = load_eye_manifest()
    merged, added, skipped = merge_rows(
        eye.get("rows", []), all_rows, readjudicate=args.readjudicate
    )
    for row in merged:
        assert_no_identifier_keys(row)

    manifest_before = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest_after = copy.deepcopy(manifest_before)
    batches = manifest_after.setdefault("_meta", {}).setdefault("collection_batches", [])
    batch_id = compute_eye_batch_id(manifest_after, datetime.now(timezone.utc).strftime("%y%m%d"))
    ledger_summary = summarize(merged)
    entry = make_eye_batch_entry(batch_id, "harvest_eye --run")
    entry.update({
        "sources": {
            "eye_repo_evidence": len(repo["rows"]),
            "eye_s3_operational": len(s3_payload["rows"]),
        },
        # scanned_* = 스캔 총계(중복 포함) / ledger_*_after = content-hash 병합 후 원장 상태.
        # 둘을 구분해 적는다 — 같은 크롭이 여러 사이클 evidence 에 복사돼 있어 차이가 크다.
        "scanned_rows": total["total"],
        "scanned_admit": total["admitted"],
        "scanned_hold": total["total"] - total["admitted"],
        "new_rows": added,
        "skipped_existing": skipped,
        "ledger_rows_after": len(merged),
        "ledger_admit_after": ledger_summary["admitted"],
        "ledger_hold_after": ledger_summary["total"] - ledger_summary["admitted"],
        "status": "collected",
        # manifest.rows 는 무접촉 — 눈 행은 eye_manifest 가 소유한다.
        "cumulative_rows_after": len(manifest_after.get("rows", [])),
        "s3_scan_error": s3_error,
    })
    batches.append(entry)

    assert_invariants = _load_watch_invariants()
    assert_invariants(manifest_before, manifest_after)  # 위반 시 AssertionError → 저장 중단.

    eye["rows"] = merged
    eye_meta = eye.setdefault("_meta", {})
    eye_meta.setdefault("batches", []).append({
        "batch_id": batch_id, "collected_at": collected_at,
        "scanned_rows": total["total"], "added": added, "skipped_existing": skipped,
        "rows_after": len(merged),
        "admit_after": ledger_summary["admitted"],
        "hold_after": ledger_summary["total"] - ledger_summary["admitted"],
    })
    eye_meta["schema_version"] = SCHEMA_VERSION
    save_eye_manifest(eye)
    MANIFEST_PATH.write_text(
        json.dumps(manifest_after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    assert_invariants(manifest_before, json.loads(MANIFEST_PATH.read_text(encoding="utf-8")))

    print(f"\n[run] 배치 {batch_id} — added {added} / skipped {skipped} / rows_after {len(merged)}")
    print(f"  eye 원장: {EYE_MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    sys.exit(main())
