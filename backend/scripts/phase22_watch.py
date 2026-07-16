#!/usr/bin/env python3
"""Phase 22 데이터 플라이휠 "쌓기" 러너 — watchlist 주기 수집 오케스트레이터 (22-11, FT-02).

belle 확정(2026-07-16): v7 SFT 성패와 무관하게 데이터를 계속 쌓아 "스포츠 모션 분석의
힉스필드"를 만든다. 22-02 가 만든 수집기(collect_phase22_youtube.py /
collect_phase22_instagram.py, D-09)를 재발명 없이 재사용해, YT 폴 채널 +
정은지 IG(eunji.poledancer, cap 60)를 belle 트리거 1커맨드로 주기 수집한다.
수집+큐레이션만 — RTMW/교사 라벨 없음(비용 통제, 라벨링은 22-12).

배치 등재 규약 (마감 무결성 정합):
  · `_meta.collection_complete=true` 의 의미는 "131행 초기 수집 라운드 마감" 이며,
    이 플래그의 소유자는 build_jsonl.assert_collection_complete(DR-06 게이트)다.
    본 규약은 build_jsonl 에 맞추며 역은 금지 — build_jsonl 은 무접촉 파일이다.
    (build_jsonl.assert_collection_complete 는 truthiness 만 검사하므로
     collection_batches 추가는 이 게이트에 무영향임을 실측 확인.)
  · 초기 라운드 마감 이후의 증분은 `_meta.collection_batches[]` 배치 단위로만 등재한다.
  · batch_id 형식은 "watch-YYMMDD" (같은 날 2회차부터 "-2","-3" 접미).
  · 기존 `_meta.recollection_rounds[]`(fault-yt-ig-260714 선례)는 이력으로 동결하고,
    신규 등재는 collection_batches 로 일원화한다.
  · 신규 watch 수집 행에는 `collection_batch=batch_id` 필드가 추가된다 —
    기존 131행 마감분은 이 필드가 부재(무접촉)로 식별된다(22-12 가 신규분 소비).

동작 모드 2단 (belle 과금 게이트 유지 — 22-02 관례):
  --dry-run  : 레지스트리 로드 + watch 대상 목록 + 원장 불변식 self-check +
               하위 수집기 dry-run 위임. 네트워크·과금 0. 기본 모드.
  --run      : PHASE22_BELLE_GREENLIGHT=1 필수(없으면 SystemExit 2). 실 수집
               (YT curate+collect / IG collect) + 배치 등재 + 리포트. 하위
               수집기의 verdict 캐시 + s3_key 멱등이 재과금을 차단한다.

순수성 규율: 배치 원장 헬퍼 + 리포트 조립은 전부 순수(파일 I/O 는 별도 껍데기).
boto3/yt_dlp 는 이 모듈 최상위에서 import 하지 않는다(하위 수집기가 lazy-import).
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "scripts"))

import collect_phase22_youtube as yt  # 키 스킴·매니페스트·레지스트리·필터 재사용.

MANIFEST_PATH = yt.MANIFEST_PATH
SOURCES_YAML = yt.SOURCES_YAML
BELLE_GREENLIGHT_ENV = "PHASE22_BELLE_GREENLIGHT"

WATCH_REPORTS_DIR = BACKEND / "training" / "data" / "watch_reports"

# 배치 entry 필수 키 집합(여분 금지 — make_batch_entry 계약).
_BATCH_ENTRY_KEYS = (
    "batch_id", "opened_at", "approved_by", "trigger", "sources",
    "new_rows", "curated_reject", "skipped_existing", "status",
    "cumulative_rows_after",
)


# ===========================================================================
# 순수 헬퍼 — 배치 원장 규약 (네트워크/boto3/yt-dlp 무관).
# ===========================================================================
def _utc_now_iso() -> str:
    """UTC ISO8601 (초 정밀, Z 접미)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_batch_entry(batch_id: str, trigger: str) -> dict:
    """배치 원장 entry 초기형 — 여분 키 0(계약). status=open, 카운트 0.

    approved_by 는 belle 고정(과금 게이트 통과 = belle 승인). cumulative_rows_after
    는 수집 완료 후 update_batch_entry 로 채운다.
    """
    return {
        "batch_id": batch_id,
        "opened_at": _utc_now_iso(),
        "approved_by": "belle",
        "trigger": trigger,
        "sources": {"youtube": 0, "instagram": 0},
        "new_rows": 0,
        "curated_reject": 0,
        "skipped_existing": 0,
        "status": "open",
        "cumulative_rows_after": None,
    }


def register_batch(manifest: dict, entry: dict) -> dict:
    """_meta.collection_batches 에 entry append. batch_id 중복은 ValueError.

    다른 _meta 키(collection_complete/collection_closed/balance_waiver/
    recollection_rounds 등)와 rows 는 무접촉. 멱등 재실행은 update_batch_entry 경로.
    """
    meta = manifest.setdefault("_meta", {})
    batches = meta.setdefault("collection_batches", [])
    bid = entry["batch_id"]
    if any(b.get("batch_id") == bid for b in batches):
        raise ValueError(
            f"batch_id {bid!r} 이미 등재됨 — 중복 register 금지(멱등은 update_batch_entry)"
        )
    batches.append(entry)
    return manifest


def update_batch_entry(manifest: dict, batch_id: str, **fields) -> dict:
    """기존 배치 entry 필드 갱신(멱등 재실행 경로). 미존재 batch_id 는 KeyError."""
    batches = manifest.get("_meta", {}).get("collection_batches", [])
    for b in batches:
        if b.get("batch_id") == batch_id:
            b.update(fields)
            return b
    raise KeyError(f"batch_id {batch_id!r} 미등재 — update 대상 없음")


def compute_batch_id(manifest: dict, today_yymmdd: str) -> str:
    """batch_id 산출 — 같은 날 2회차부터 "-2","-3" 접미(순수)."""
    base = f"watch-{today_yymmdd}"
    batches = manifest.get("_meta", {}).get("collection_batches", [])
    existing = {b.get("batch_id") for b in batches}
    if base not in existing:
        return base
    n = 2
    while f"{base}-{n}" in existing:
        n += 1
    return f"{base}-{n}"


def make_watch_row(base_row: dict, batch_id: str) -> dict:
    """신규 watch 수집 행에 collection_batch=batch_id 주입(원본 무접촉, 순수)."""
    return {**base_row, "collection_batch": batch_id}


def assert_ledger_invariants(before: dict, after: dict) -> None:
    """마감 무결성 강제 — 위반 시 AssertionError(저장 중단 트리거).

    (a) collection_complete 가 정확히 True 유지(before·after 양측).
    (b) collection_closed / balance_waiver 무변형.
    (c) rows append-only — 기존 행(before rows)이 after 의 prefix 로 불변 보존.
    """
    bmeta = (before or {}).get("_meta", {})
    ameta = (after or {}).get("_meta", {})
    # (a)
    assert bmeta.get("collection_complete") is True, (
        "before manifest 의 collection_complete 가 True 가 아님 — 마감 상태 아님"
    )
    assert ameta.get("collection_complete") is True, (
        "after manifest 의 collection_complete 가 True 에서 이탈 — 마감 플래그 훼손"
    )
    # (b)
    assert bmeta.get("collection_closed") == ameta.get("collection_closed"), (
        "collection_closed 원장 변형 감지 — 마감 무결성 위반"
    )
    assert bmeta.get("balance_waiver") == ameta.get("balance_waiver"), (
        "balance_waiver 변형 감지 — 마감 무결성 위반"
    )
    # (c)
    before_rows = (before or {}).get("rows", [])
    after_rows = (after or {}).get("rows", [])
    assert len(after_rows) >= len(before_rows), "rows 삭제 감지 — append-only 위반"
    assert after_rows[: len(before_rows)] == before_rows, (
        "기존 행 변형/삭제 감지 — append-only 위반(신규분은 뒤에만 추가돼야)"
    )
    before_keys = {r.get("s3_key") for r in before_rows if r.get("s3_key")}
    after_keys = {r.get("s3_key") for r in after_rows if r.get("s3_key")}
    assert before_keys <= after_keys, "기존 s3_key 집합 소실 — append-only 위반"


# ===========================================================================
# 파일 I/O 껍데기 (순수 헬퍼와 분리).
# ===========================================================================
def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    sys.exit(main())  # noqa: F821 — main 은 Task 2 에서 추가.
