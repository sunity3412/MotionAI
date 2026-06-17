#!/usr/bin/env python3
"""Phase 15 dataset 업로드 — 정은지 13 영상 → 비-notified fixtures/ SOURCE 키.

Phase 15 / CONTEXT D-05 (파일명 정규화 = Claude discretion) / HIGH 1 (fixture 업로드가
uploads/ 트리거를 발화하면 안 됨) / R1 (fixtures/phase15/{motion}/correct|fault.mp4 스킴) /
LOW 7 (combo = Mode-1-only, 페어 없음).

소스 = ~/Downloads/정은지 선수 추가 영상/ (잘된 예시/ 의 7 success + top-level 6 fail 한글명).
13 영상을 비-notified fixtures/ 프리픽스로 immutable SOURCE 로 업로드한다.

키 스킴 (R1 + HIGH 1):
  • success: fixtures/phase15/{motion}/correct.mp4
  • fail:    fixtures/phase15/{motion}/fault.mp4
  • combo:   fixtures/phase15/combo/correct.mp4 (Mode-1-only, 페어 없음, Deferred)

fixtures/ 프리픽스는 backend/README.md(line 106-107)의 uploads/ ObjectCreated notification·
lifecycle 대상이 아니므로 업로드 즉시 production S3→SQS→pipeline 트리거가 발화하지 않고
영구 SOURCE 로 보존된다. 이전 스킴 uploads/phase15-{motion}/correct|fault.mp4 는
parse-compatible 라서 업로드 즉시 notification 을 발화시켜(HIGH 1) Lambda/RunPod 가 doc 생성
전 partial 분석을 enqueue 할 수 있었다 — fixtures/ 로 옮겨 이 side-effect 를 제거한다.
SOURCE fixtures 키는 parse_upload_key 정규식을 만족할 필요가 없다 (분석 입력이 아니라 SOURCE).

동작:
  (1) 한글 fail 파일명을 motion 슬러그로 매핑.
  (2) fixtures: prefix + 더블 확장자 오타 "pdshape-correct.mp4  .mp4" 정규화.
  (3) 각 PUT 에 Content-Type video/mp4 명시 (memory s3-presigned-video-playback — 누락 시
      octet-stream 저장, T-15.01-03).
  (4) 업로드 전 각 fixtures 키가 기대 스킴을 따르는지 self-check.

AWS 자격증명 = sunity-motion (RESEARCH Pitfall 2; sunity-api 는 Motion AI 권한 없음).
산출 = backend/scripts/phase15_keys.json (sweep_phase15.py --keys-file 입력으로 직접 소비;
각 항목 sourceS3Key/motionId/mode/label/referenceMotionId). sourceS3Key 는 fixtures/ 키이며
analysis identity 가 아니다.

CLI:
    python backend/scripts/upload_phase15_dataset.py --dry-run   # 매핑·정규화·스킴 self-check
    python backend/scripts/upload_phase15_dataset.py             # 실 PUT (sunity-motion creds)
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
KEYS_OUT = BACKEND / "scripts" / "phase15_keys.json"

DEFAULT_SOURCE_DIR = Path.home() / "Downloads" / "정은지 선수 추가 영상"
BUCKET = "sunity-motion-pilot-videos"
FIXTURES_PREFIX = "fixtures/phase15"
CONTENT_TYPE = "video/mp4"

# 한글 fail 파일명 → motion 슬러그. top-level 6 fail.
# (실제 파일명에 부가 설명이 붙어 있어 substring 매칭으로 견고하게 처리.)
FAIL_NAME_TO_MOTION = {
    "pdshape": "pdshape",
    "엘보트위스트시스터": "elbow-twist-sister",
    "클라임": "climb",
    "킵업": "kip-up",
    "파워스핀": "power-spin",
    "피터팬": "peter-pan",
}

# success 파일은 잘된 예시/ 안에 fixtures: prefix 로 존재 — substring 으로 motion 매핑.
SUCCESS_NAME_TO_MOTION = {
    "climb": "climb",
    "elbow-twist-sister": "elbow-twist-sister",
    "kip-up": "kip-up",
    "pdshape": "pdshape",
    "peter-pan": "peter-pan",
    "power-spin": "power-spin",
    "combo": "combo",  # Mode-1-only, 페어 없음.
}

# combo 는 Mode-1-only (페어 없음). 나머지 6 motion 은 Mode 3 페어 + Mode 1.
MODE1_MOTIONS = {
    "climb", "elbow-twist-sister", "kip-up", "pdshape",
    "peter-pan", "power-spin", "combo",
}


def _match_motion(filename: str, table: dict[str, str]) -> str | None:
    """파일명 안에서 motion 키워드를 substring 매칭. 가장 긴 키 우선 (구체성).

    macOS 는 파일명을 NFD(자모 분리)로 저장하지만 dict 키(한글)는 NFC 라 raw substring
    매칭이 실패한다 — 양쪽을 NFC 로 normalize 한 뒤 비교한다 (D-05 파일명 정규화).
    """
    base = unicodedata.normalize("NFC", filename).lower()
    for needle in sorted(table, key=len, reverse=True):
        nfc_needle = unicodedata.normalize("NFC", needle).lower()
        if nfc_needle in base:
            return table[needle]
    return None


def _fixtures_key(motion: str, label: str) -> str:
    """fixtures/phase15/{motion}/correct|fault.mp4 (combo=correct)."""
    leaf = "correct" if label in ("success",) else "fault"
    return f"{FIXTURES_PREFIX}/{motion}/{leaf}.mp4"


def _assert_scheme(key: str) -> None:
    """업로드 전 키 스킴 self-check — fixtures/phase15/{motion}/correct|fault.mp4."""
    parts = key.split("/")
    if (
        len(parts) != 4
        or parts[0] != "fixtures"
        or parts[1] != "phase15"
        or parts[3] not in ("correct.mp4", "fault.mp4")
    ):
        raise RuntimeError(f"키 {key!r} 가 fixtures/phase15/{{motion}}/correct|fault.mp4 스킴 위반")
    if key.startswith("uploads/"):
        raise RuntimeError(f"키 {key!r} 가 uploads/ 프리픽스 — notification 발화 위험 (HIGH 1)")


def _build_mapping(source_dir: Path) -> list[dict]:
    """13 영상 → motion↔fixtures 키↔mode↔label↔referenceMotionId 매핑.

    success 7 (잘된 예시/, combo 포함) + fail 6 (top-level). 각 항목:
      sourceLocalPath / sourceS3Key(fixtures/) / motionId / mode / label / referenceMotionId.
    """
    items: list[dict] = []
    success_dir = source_dir / "잘된 예시"

    # ── success 7 (잘된 예시/) ──────────────────────────────────────────────
    if success_dir.exists():
        success_files = sorted(p for p in success_dir.iterdir() if p.suffix == ".mp4" or p.name.endswith(".mp4"))
    else:
        success_files = []
    seen_success: set[str] = set()
    for f in success_files:
        motion = _match_motion(f.name, SUCCESS_NAME_TO_MOTION)
        if motion is None or motion in seen_success:
            continue
        seen_success.add(motion)
        key = _fixtures_key(motion, "success")
        _assert_scheme(key)
        items.append({
            "sourceLocalPath": str(f),
            "sourceS3Key": key,
            "motionId": motion,
            "mode": "mode1",  # success 영상은 Mode 1 (정은지 기준 비교) 입력 + Mode 3 success.
            "label": "success",
            "referenceMotionId": f"ref-{motion}",
            "contentType": CONTENT_TYPE,
        })

    # ── fail 6 (top-level 한글명) ───────────────────────────────────────────
    fail_files = sorted(
        p for p in source_dir.iterdir()
        if p.is_file() and (p.suffix == ".mp4" or p.name.endswith(".mp4"))
    )
    seen_fail: set[str] = set()
    for f in fail_files:
        motion = _match_motion(f.name, FAIL_NAME_TO_MOTION)
        if motion is None or motion in seen_fail:
            continue
        seen_fail.add(motion)
        key = _fixtures_key(motion, "fault")
        _assert_scheme(key)
        items.append({
            "sourceLocalPath": str(f),
            "sourceS3Key": key,
            "motionId": motion,
            "mode": "mode3",  # fault 영상은 Mode 3 페어 (success vs fault 델타).
            "label": "fault",
            "referenceMotionId": None,
            "contentType": CONTENT_TYPE,
        })

    # success 영상 중 Mode 3 페어가 성립하는 motion(=fail 이 있는 6 motion)은 mode3 success 도
    # sweep 가 쓸 수 있도록 mode=mode3 success 항목을 별도 추가. combo 는 페어 없음 → mode1 만.
    fail_motions = {it["motionId"] for it in items if it["mode"] == "mode3"}
    extra: list[dict] = []
    for it in items:
        if it["mode"] == "mode1" and it["label"] == "success" and it["motionId"] in fail_motions:
            extra.append({
                "sourceLocalPath": it["sourceLocalPath"],
                "sourceS3Key": it["sourceS3Key"],
                "motionId": it["motionId"],
                "mode": "mode3",
                "label": "success",
                "referenceMotionId": None,
                "contentType": CONTENT_TYPE,
            })
    items.extend(extra)
    return items


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 15 dataset 업로드 — 비-notified fixtures/ SOURCE 키 (HIGH 1)"
    )
    parser.add_argument(
        "--source-dir", default=str(DEFAULT_SOURCE_DIR),
        help="정은지 13 영상 디렉토리 (default ~/Downloads/정은지 선수 추가 영상)",
    )
    parser.add_argument("--bucket", default=BUCKET)
    parser.add_argument("--keys-out", default=str(KEYS_OUT))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source_dir = Path(args.source_dir).expanduser()
    items = _build_mapping(source_dir)

    # 매핑 요약 출력. 13 영상 = 7 success(combo 포함) + 6 fail (sourceLocalPath unique).
    unique_files = {it["sourceLocalPath"] for it in items}
    success_count = sum(1 for it in items if it["label"] == "success" and it["mode"] == "mode1")
    fault_count = sum(1 for it in items if it["label"] == "fault")
    print(
        f"[mapping] unique videos={len(unique_files)} "
        f"(mode1 success={success_count} + fault={fault_count}) items={len(items)}",
        flush=True,
    )
    for it in items:
        combo_tag = " [combo=mode1-only]" if it["motionId"] == "combo" else ""
        print(
            f"  motion={it['motionId']:<18} mode={it['mode']:<6} label={it['label']:<7} "
            f"key={it['sourceS3Key']} ct={it['contentType']}{combo_tag}",
            flush=True,
        )

    # 모든 SOURCE 키 스킴 self-check (이중).
    for it in items:
        _assert_scheme(it["sourceS3Key"])

    # phase15_keys.json 산출 (sweep_phase15.py --keys-file 호환).
    keys_payload = {
        "bucket": args.bucket,
        "items": [
            {
                "sourceS3Key": it["sourceS3Key"],
                "motionId": it["motionId"],
                "mode": it["mode"],
                "label": it["label"],
                "referenceMotionId": it["referenceMotionId"],
            }
            for it in items
        ],
    }

    if args.dry_run:
        print(
            f"\n[dry-run] no S3 PUT. {len(items)} 항목 매핑·정규화·스킴 self-check 통과. "
            "모든 SOURCE 키 fixtures/phase15/ (uploads/ 미사용, 트리거 비발화, HIGH 1).",
            flush=True,
        )
        # dry-run 에서도 keys 파일은 갱신하지 않는다 (실 업로드 후에만 산출).
        return 0

    import boto3  # noqa: E402 — dry-run path 는 boto3 불필요.

    s3 = boto3.client("s3")
    for it in items:
        # 동일 영상이 mode1/mode3 로 중복 등장하지만 sourceS3Key 가 같으므로 PUT 은 1회만 필요.
        # set 으로 중복 제거.
        pass
    uploaded: set[str] = set()
    for it in items:
        key = it["sourceS3Key"]
        if key in uploaded:
            continue
        local = Path(it["sourceLocalPath"])
        if not local.exists():
            raise RuntimeError(f"소스 영상 없음: {local}")
        with local.open("rb") as fh:
            s3.put_object(
                Bucket=args.bucket,
                Key=key,
                Body=fh,
                ContentType=it["contentType"],  # T-15.01-03 — 누락 시 octet-stream.
            )
        uploaded.add(key)
        print(f"  PUT {key} (ContentType={it['contentType']})", flush=True)

    Path(args.keys_out).write_text(
        json.dumps(keys_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n[keys] wrote {args.keys_out} ({len(keys_payload['items'])} items)", flush=True)
    print(f"[done] uploaded {len(uploaded)} unique SOURCE objects under {FIXTURES_PREFIX}/", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
