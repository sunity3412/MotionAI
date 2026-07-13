"""내부 fault 트랙 anonymize 배치 러너 — 후보 → 얼굴 블러 → S3 → manifest 행 (처방 B, quick 260713-jxr).

enumerate_internal.py 가 방출한 후보 JSON 을 소비해: uploads/ 원본 다운로드 →
anonymize_video(얼굴 블러, D-12 강제) → fixtures/phase22/internal/{video_hash}.mp4
업로드 → manifest 행 생성/병합. full_batch.py 의 재개 규율을 원형으로 한다 —
행별 결과 파일(out_dir/rows/{slug}.json)이 진실이고, 터미널이면 재실행 시 skip.

경계·불변식:
  · 업로드 키는 internal_upload_key 가 fixtures/phase22/internal/ 를 하드 소유한다
    — uploads/ 생성 경로가 구조적으로 없다(S3 ObjectCreated→SQS 발화 차단, T-Q13-03).
  · manifest 행은 uid/analysisId/이메일 계열 키를 담지 않는다 — source_url 도 video_hash
    기반 sentinel 만(uid 비파생, T-Q13-01). build_manifest_row + assert_no_identifier_keys
    이중 fence.
  · provisional_bucket=None 후보는 병합 전 skip(다운로드/anonymize 미수행) — test_provenance
    label_bucket enum(정타|fault) 위반 원천 차단.
  · 생성 행은 gemini_teacher.eligible_for_distill 과 test_provenance fence 를 무수정 통과
    → 후속 라벨링(full_batch)에 코드 변경 0.

belle 결정(2026-07-13): 파일럿 이전 내부 데이터 학습사용 일괄 승인 — 행별 consent_evidence
필드에 근거를 박제한다. anonymize_video 자체는 여기서 테스트하지 않는다(anonymize.py 소유).

boto3/anonymize/imageio 는 전부 lazy import — 순수 함수(키/행/병합)는 네트워크 0 으로
테스트된다(test_anonymize_batch.py). I/O 경계(_download_s3/_anonymize_video/
_compute_video_hash/_s3_client)는 monkeypatch 대상 모듈 함수로 분리.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_BACKEND = _HERE.parents[2]
_SHARED = _BACKEND / "shared" / "python"
_TRAINING = _BACKEND / "training"
for _p in (_SHARED, _TRAINING):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

SCRIPT_VERSION = "anonymize-batch-v1.0"

_INTERNAL_PREFIX = "fixtures/phase22/internal/"
_DEFAULT_BUCKET = "sunity-motion-pilot-videos"
_DEFAULT_MANIFEST = str(_BACKEND / "training" / "data" / "manifest.json")

# manifest 행 label_bucket enum (test_provenance VALID_BUCKETS 와 정합 — 여기서는
# 방어 assert 용 로컬 상수, 테스트는 test_provenance 상수로 교차검증).
_VALID_BUCKETS = ("정타", "fault")

# 최종 manifest 행 금지 키 — uid/식별자 유출 fence (test_provenance FORBIDDEN_IDENTITY_FIELDS 정합).
_FORBIDDEN_ROW_KEYS = ("uid", "user_id", "userId", "email", "phone", "analysisId", "analysis_id")

# belle 2026-07-13 일괄승인 근거 — 행별 박제(T-Q13-05 부인 방지).
_CONSENT_EVIDENCE = (
    "belle 일괄승인 2026-07-13 — 파일럿 이전 내부 데이터 학습사용(구두), 명시 거부 1건 제외"
)

# 재개 터미널 상태 — 이 결과면 재실행 시 skip (full_batch TERMINAL 패턴).
_TERMINAL_RESULTS = ("uploaded", "skipped_no_bucket")


# ---------------------------------------------------------------------------
# 순수 함수 — 네트워크 0 (test_anonymize_batch.py 가 소유).
# ---------------------------------------------------------------------------
def internal_upload_key(video_hash: str) -> str:
    """anonymize 산출물 업로드 키 — fixtures/phase22/internal/{video_hash}.mp4.

    uploads/ prefix 생성 경로가 구조적으로 없다: S3 ObjectCreated→SQS 분석 파이프라인이
    uploads/ 에서만 발화하므로, 학습 전용 산출물은 비-notified prefix 로만 오른다
    (T-Q13-03). 빈 hash 는 ValueError(키 오염 방지).
    """
    h = str(video_hash or "").strip()
    if not h:
        raise ValueError("video_hash 가 비었다 — 업로드 키 생성 불가")
    return f"{_INTERNAL_PREFIX}{h}.mp4"


def internal_source_url(video_hash: str) -> str:
    """provenance sentinel source_url — internal://firestore-analyses/{video_hash}.

    test_provenance REQUIRED_PROVENANCE_FIELDS 의 truthy source_url 요건 충족용 내부
    sentinel. uid/analysisId 파생 금지 — video_hash 기반만(T-Q13-01). 실제 URL 이 아니라
    "내부 Firestore 분석 유래"를 나타내는 출처 표식이다.
    """
    h = str(video_hash or "").strip()
    if not h:
        raise ValueError("video_hash 가 비었다 — source_url 생성 불가")
    return f"internal://firestore-analyses/{h}"


def build_manifest_row(candidate: dict, video_hash: str) -> dict:
    """후보 + video_hash → manifest 행 (기존 131행 스키마 + consent_evidence).

    source='internal_pilot_user' 로 gemini_teacher._is_customer_source 를 발화시키고,
    anonymized=True 로 eligible_for_distill 의 고객 소스 게이트를 통과한다(D-12).
    방어 assert 2종: (a) 금지 식별자 키 부재 (b) label_bucket ∈ 정타|fault
    (None/enum 밖이면 ValueError — 정상 경로는 호출 전 skip 이지만 이중 방어).
    """
    bucket = (candidate or {}).get("provisional_bucket")
    if bucket not in _VALID_BUCKETS:
        raise ValueError(
            f"label_bucket 이 enum({_VALID_BUCKETS}) 밖: {bucket!r} — bucket None 후보는 "
            "병합 전 skip 되어야 한다"
        )
    row = {
        "s3_key": internal_upload_key(video_hash),
        "motion": (candidate or {}).get("motion") or None,
        "label_bucket": bucket,
        "source": "internal_pilot_user",
        "channel": "internal",
        "source_url": internal_source_url(video_hash),
        "license_evidence": "파일럿 참가 동의서(D-12 1겹)",
        "consent_evidence": _CONSENT_EVIDENCE,
        "usage": "training-only-no-redistribution",
        "tier": "customer",
        "anonymized": True,
        "holdout": None,
        "collected": True,
    }
    # (a) 금지 식별자 키 부재 이중 방어.
    for forbidden in _FORBIDDEN_ROW_KEYS:
        if forbidden in row:
            raise ValueError(f"금지 식별자 키 {forbidden!r} 가 행에 존재")
    return row


def assert_no_identifier_keys(rows: list[dict]) -> None:
    """행 리스트에 uid/식별자 키가 하나도 없음을 강제(measure_error_profile 정신).

    uploads/... 원본 키(uid 포함)가 s3_key 값으로 남아도 안 된다 — 값 스캔까지 포함.
    """
    for row in rows:
        for forbidden in _FORBIDDEN_ROW_KEYS:
            assert forbidden not in row, f"금지 식별자 키 {forbidden!r} 등장"
        # s3_key 값이 uploads/ 원본이면 uid 노출 — internal prefix 만 허용.
        key = str(row.get("s3_key") or "")
        assert not key.startswith("uploads/"), f"uploads/ 원본 키 유출: {key}"


def merge_manifest_rows(manifest: dict, new_rows: list[dict]) -> dict:
    """기존 manifest 사본에 신규 행 upsert(s3_key 기준) + _meta.customer_track 갱신.

    사본 반환(원본 불변) + 멱등(같은 s3_key 재병합 시 덮어쓰기, 행 증가 0). 기존 131행은
    s3_key 가 겹치지 않으므로 불변. full_batch.manifest_with_hashes 의 사본 규율 재사용.
    """
    assert_no_identifier_keys(new_rows)
    out = copy.deepcopy(manifest or {})
    rows = out.setdefault("rows", [])
    by_key = {r.get("s3_key"): i for i, r in enumerate(rows)}
    for nr in new_rows:
        k = nr.get("s3_key")
        if k in by_key:
            rows[by_key[k]] = nr
        else:
            by_key[k] = len(rows)
            rows.append(nr)
    meta = out.setdefault("_meta", {})
    ct = meta.setdefault("customer_track", {})
    ct["anonymized"] = "in_progress"
    ct["approved_at"] = "2026-07-13"
    ct["approved_by"] = "belle"
    ct["approval_scope"] = (
        "파일럿 이전 내부 데이터 학습사용 일괄 승인(구두) — learningOptIn=false 1건 제외, "
        "anonymize 강제, 이후 신규는 optIn=true 엄격"
    )
    return out


def is_row_done(payload: dict) -> bool:
    """행 결과가 터미널(uploaded|skipped_no_bucket)이면 True — 재개 시 skip."""
    return (payload or {}).get("result") in _TERMINAL_RESULTS


def _row_slug(s3_key: str) -> str:
    """행 결과 파일 slug — s3_key 의 '/' 를 '__' 로(pod_coords/full_batch 규칙 동일)."""
    return str(s3_key or "unknown").replace("/", "__")


# ---------------------------------------------------------------------------
# I/O 껍데기 — boto3/anonymize/imageio (lazy import, Pod 실행 전용, monkeypatch 경계).
# ---------------------------------------------------------------------------
def _s3_client():
    import boto3  # lazy

    return boto3.client("s3", region_name="ap-northeast-2")


def _download_s3(bucket: str, key: str, dest_path: str) -> None:
    """S3 객체 → 로컬 (gemini_teacher._download_s3 와 동일 규율, 재사용 회피용 로컬 래퍼)."""
    from distill.gemini_teacher import _download_s3 as _dl  # lazy

    _dl(bucket, key, dest_path)


def _anonymize_video(in_path: str, out_path: str, weights: str | None = None) -> str:
    """anonymize.anonymize_video 얇은 래퍼 (lazy import — torch/ultralytics 무거움)."""
    from datagen.anonymize import anonymize_video  # lazy

    return anonymize_video(in_path, out_path, weights)


def _compute_video_hash(path: str, **kw) -> str:
    """technique_cache.compute_video_hash 얇은 래퍼 (content-hash dedup 용)."""
    from sunity_shared.analysis.technique_cache import compute_video_hash  # lazy

    return compute_video_hash(path, **kw)


def _write_row_result(rows_dir: Path, s3_key: str, payload: dict) -> None:
    rows_dir.mkdir(parents=True, exist_ok=True)
    path = rows_dir / f"{_row_slug(s3_key)}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_row_result(rows_dir: Path, s3_key: str) -> dict | None:
    path = rows_dir / f"{_row_slug(s3_key)}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def run_anonymize_batch(
    candidates_path: str,
    out_dir: str,
    scratch_dir: str,
    *,
    bucket: str = _DEFAULT_BUCKET,
    manifest_path: str = _DEFAULT_MANIFEST,
    dry_run: bool = False,
    max_rows: int = 0,
) -> dict:
    """후보 소비 → anonymize → 업로드 → 행 결과 영속화 → manifest 병합(재개 가능).

    행별 처리: 터미널 결과 파일 → skip / provisional_bucket None → skipped_no_bucket 기록
    후 다음 행(다운로드·anonymize 미수행) / content-hash 중복 → skip / 그 외 다운로드 →
    anonymize → 업로드 → uploaded 기록. 전체 종료 시 uploaded 행을 모아 merge_manifest_rows
    → manifest_path 기록. dry_run 은 다운로드/업로드 없이 계획 계수만.
    """
    cand = json.loads(Path(candidates_path).read_text(encoding="utf-8"))
    candidates = cand.get("candidates", [])
    if max_rows:
        candidates = candidates[:max_rows]

    out = Path(out_dir)
    rows_dir = out / "rows"
    scratch = Path(scratch_dir)
    summary = {
        "total": len(candidates), "uploaded": 0, "skipped_no_bucket": 0,
        "skipped_done": 0, "skipped_dup_hash": 0, "error": 0,
    }
    if dry_run:
        for c in candidates:
            if c.get("provisional_bucket") in _VALID_BUCKETS:
                summary["uploaded"] += 1  # 계획상 처리 대상.
            else:
                summary["skipped_no_bucket"] += 1
        print("[dry-run counts]", json.dumps(summary, ensure_ascii=False))
        return summary

    seen_hashes: set[str] = set()
    for c in candidates:
        s3_key = c.get("s3_key")
        if not s3_key:
            summary["error"] += 1
            continue
        prior = _read_row_result(rows_dir, s3_key)
        if prior and is_row_done(prior):
            summary["skipped_done"] += 1
            vh = prior.get("video_hash")
            if vh:
                seen_hashes.add(vh)
            continue
        if c.get("provisional_bucket") not in _VALID_BUCKETS:
            _write_row_result(rows_dir, s3_key, {"result": "skipped_no_bucket", "s3_key": s3_key})
            summary["skipped_no_bucket"] += 1
            continue
        try:
            scratch.mkdir(parents=True, exist_ok=True)
            src = scratch / f"src_{_row_slug(s3_key)}"
            _download_s3(bucket, s3_key, str(src))
            video_hash = _compute_video_hash(str(src))
            if video_hash in seen_hashes:
                _cleanup(src)
                _write_row_result(
                    rows_dir, s3_key,
                    {"result": "skipped_dup_hash", "s3_key": s3_key, "video_hash": video_hash},
                )
                summary["skipped_dup_hash"] += 1
                continue
            blurred = scratch / f"anon_{video_hash}.mp4"
            _anonymize_video(str(src), str(blurred))
            key = internal_upload_key(video_hash)
            _s3_client().upload_file(
                str(blurred), bucket, key, ExtraArgs={"ContentType": "video/mp4"}
            )
            row = build_manifest_row(c, video_hash)
            _write_row_result(
                rows_dir, s3_key,
                {"result": "uploaded", "s3_key": s3_key, "video_hash": video_hash, "row": row},
            )
            seen_hashes.add(video_hash)
            summary["uploaded"] += 1
            _cleanup(src)
            _cleanup(blurred)
        except Exception as exc:  # noqa: BLE001 - 행 오류는 배치를 막지 않는다(재개 가능).
            _write_row_result(rows_dir, s3_key, {"result": "error", "s3_key": s3_key, "error": str(exc)})
            summary["error"] += 1

    # uploaded 행을 모아 manifest 병합.
    new_rows = []
    if rows_dir.exists():
        for rf in sorted(rows_dir.glob("*.json")):
            try:
                payload = json.loads(rf.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            if payload.get("result") == "uploaded" and payload.get("row"):
                new_rows.append(payload["row"])
    if new_rows:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        merged = merge_manifest_rows(manifest, new_rows)
        Path(manifest_path).write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print("[counts]", json.dumps(summary, ensure_ascii=False))
    return summary


def _cleanup(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="내부 fault 트랙 anonymize 배치 (처방 B — belle 2026-07-13 일괄승인)"
    )
    parser.add_argument("--candidates", required=True, help="enumerate_internal 산출 후보 JSON")
    parser.add_argument("--out-dir", required=True, help="행 결과 영속화 디렉터리(재개 진실)")
    parser.add_argument("--scratch-dir", required=True, help="다운로드/블러 임시 디렉터리")
    parser.add_argument("--bucket", default=_DEFAULT_BUCKET)
    parser.add_argument("--manifest", default=_DEFAULT_MANIFEST)
    parser.add_argument("--dry-run", action="store_true", help="다운로드/업로드 없이 계수만")
    parser.add_argument("--max-rows", type=int, default=0, help="시험 배치 상한(0=전체)")
    args = parser.parse_args(argv)

    run_anonymize_batch(
        args.candidates, args.out_dir, args.scratch_dir,
        bucket=args.bucket, manifest_path=args.manifest,
        dry_run=args.dry_run, max_rows=args.max_rows,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
