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


# ===========================================================================
# watch 대상 선별 + 리포트 조립 (순수).
# ===========================================================================
def watch_targets(registry: dict) -> dict:
    """watch 대상 = watch:false 옵트아웃 제외. 순수.

    YouTube 는 enabled 채널만(_active_channels 관례 — 미성년 등 격리 유지),
    Instagram 은 트랙 전체(IG 어댑터가 enabled 무관 처리 — collect_phase22_instagram
    설계). watch 필드 부재 = 대상(기본 opt-in).
    """
    yt_ch = [
        c for c in yt._active_channels(registry)
        if c.get("platform") == "youtube" and c.get("watch", True)
    ]
    ig_ch = [
        c for c in registry.get("channels", [])
        if c.get("platform") == "instagram" and c.get("watch", True)
    ]
    return {"youtube": yt_ch, "instagram": ig_ch}


def _parse_collect_counts(captured_text: str) -> dict:
    """하위 수집기 stdout 에서 reject/skip 카운트 추출(순수, 은폐 금지 보조).

    curate 라인 "... reject {n} ..." + collect 라인 "skip(기존) {n}" 을 합산한다.
    실 수집을 재실행하지 않고 방출 리포트를 조립하기 위한 파싱(테스트 대상).
    """
    import re

    rejects = sum(int(x) for x in re.findall(r"reject\s+(\d+)", captured_text))
    skips = sum(int(x) for x in re.findall(r"skip\(기존\)\s+(\d+)", captured_text))
    return {"curated_reject": rejects, "skipped_existing": skips}


def summarize_run(before: dict, after: dict, batch_entry: dict) -> dict:
    """실행 요약 리포트 조립 — 신규 행/소스분해/버킷분해/누적(순수).

    curated_reject/skipped_existing 은 batch_entry 에서(오케스트레이터가 채움),
    new_rows/소스/버킷은 before/after 행 diff 에서 계산한다.
    """
    before_rows = before.get("rows", [])
    after_rows = after.get("rows", [])
    new_rows = after_rows[len(before_rows):]
    by_source = {"youtube": 0, "instagram": 0}
    by_bucket = {"정타": 0, "fault": 0}
    for r in new_rows:
        src = r.get("source")
        if src in by_source:
            by_source[src] += 1
        b = r.get("label_bucket")
        if b in by_bucket:
            by_bucket[b] += 1
    return {
        "batch_id": batch_entry.get("batch_id"),
        "trigger": batch_entry.get("trigger"),
        "opened_at": batch_entry.get("opened_at"),
        "new_rows": len(new_rows),
        "new_by_source": by_source,
        "new_by_bucket": by_bucket,
        "curated_reject": int(batch_entry.get("curated_reject") or 0),
        "skipped_existing": int(batch_entry.get("skipped_existing") or 0),
        "cumulative_rows_after": len(after_rows),
    }


def write_report(batch_id: str, summary: dict) -> Path:
    """watch_reports/{batch_id}.json 이중 기록(T-22-11-05 은폐 방지). I/O 껍데기."""
    WATCH_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = WATCH_REPORTS_DIR / f"{batch_id}.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


class _Tee:
    """stdout 을 실시간 표시 + 버퍼 캡처(하위 수집기 카운트 파싱용)."""

    def __init__(self, *streams):
        self._streams = streams

    def write(self, s):
        for st in self._streams:
            st.write(s)
        return len(s)

    def flush(self):
        for st in self._streams:
            st.flush()


# ===========================================================================
# 오케스트레이션.
# ===========================================================================
def _yt_passthrough(mode_flag: str, args) -> list[str]:
    argv = [mode_flag, "--sources", args.sources]
    if args.only:
        argv += ["--only", args.only]
    if args.limit_per_channel:
        argv += ["--limit-per-channel", str(args.limit_per_channel)]
    if args.max_candidates:
        argv += ["--max-candidates", str(args.max_candidates)]
    return argv


def _ig_passthrough(args) -> list[str]:
    argv = ["--collect", "--sources", args.sources]
    if args.only:
        argv += ["--only", args.only]
    if args.cap_per_account:
        argv += ["--cap-per-account", str(args.cap_per_account)]
    if args.max_candidates:
        argv += ["--max-candidates", str(args.max_candidates)]
    return argv


def _dry_run(registry: dict, args) -> int:
    """레지스트리 + watch 대상 + 원장 불변식 self-check + 하위 dry-run 위임. network 0."""
    targets = watch_targets(registry)
    n_yt, n_ig = len(targets["youtube"]), len(targets["instagram"])
    print(
        f"[watch dry-run] 레지스트리 {args.sources} | watch 대상 채널 {n_yt + n_ig} "
        f"(youtube {n_yt} + instagram {n_ig}) | network 0 · 과금 0",
        flush=True,
    )
    for c in targets["youtube"]:
        print(f"  [YT] {c['name']:<34} bucket={c.get('bucket','?'):<6} tier={c.get('tier','?')}", flush=True)
    for c in targets["instagram"]:
        cap = c.get("cap_per_account", "기본")
        print(f"  [IG] {c['name']:<34} bucket={c.get('bucket','?'):<6} cap={cap}", flush=True)

    # 배치 원장 불변식 self-check — 합성 manifest 왕복(silent 통과 금지, 실 파일 무접촉).
    synth = {
        "_meta": {
            "collection_complete": True,
            "collection_closed": {"closed_at": "x"},
            "balance_waiver": {"unmet": ["max_le_2min"]},
            "collection_batches": [],
        },
        "rows": [{"s3_key": "fixtures/phase22/x/A.mp4", "motion": "x",
                  "label_bucket": "정타", "source": "youtube", "usage": "x", "holdout": None}],
    }
    before = copy.deepcopy(synth)
    after = copy.deepcopy(synth)
    bid = compute_batch_id(after, "000000")
    register_batch(after, make_batch_entry(bid, "dry-run-selfcheck"))
    after["rows"].append(make_watch_row(
        {"s3_key": "fixtures/phase22/x/B.mp4", "motion": "x", "label_bucket": "fault",
         "source": "instagram", "usage": "x", "holdout": None}, bid))
    try:
        assert_ledger_invariants(before, after)
    except AssertionError as exc:
        print(f"  [LEDGER-FAIL] {exc}", file=sys.stderr, flush=True)
        return 1
    print("  [ledger self-check] OK — append-only + 마감 무결성 왕복 통과", flush=True)

    # 하위 수집기 dry-run 위임(네트워크 0).
    print("\n[watch dry-run] 하위 수집기 dry-run 위임:", flush=True)
    import collect_phase22_instagram as ig

    rc_yt = yt.main(["--dry-run", "--sources", args.sources])
    rc_ig = ig.main(["--dry-run", "--sources", args.sources])
    if rc_yt != 0 or rc_ig != 0:
        print(f"  [SUB-FAIL] yt={rc_yt} ig={rc_ig}", file=sys.stderr, flush=True)
        return 1
    print(
        "\n[watch dry-run] exit 0 — watch 대상 확인 + 원장 불변식 + 하위 dry-run 전부 통과. "
        "다운로드·Gemini·boto3 호출 0. 실 수집은 --run(belle greenlight).",
        flush=True,
    )
    return 0


def _run(registry: dict, args) -> int:
    """belle 1커맨드 실 수집 — 배치 등재 + 멱등 수집 + 리포트 + 게이트 재검증."""
    import os

    if os.environ.get(BELLE_GREENLIGHT_ENV) != "1":
        print(
            f"[BLOCKED] --run 은 belle 과금 게이트 — Gemini 과금 + 카피라이트 S3 적재(비가역).\n"
            f"승인 후에만: {BELLE_GREENLIGHT_ENV}=1 AWS_PROFILE=sunity-motion 로 재실행.",
            file=sys.stderr, flush=True,
        )
        raise SystemExit(2)

    import io
    import contextlib
    import subprocess

    import collect_phase22_instagram as ig

    # (1) 스냅샷(before) + 진입 fail-closed(collection_complete 마감 확인).
    before = copy.deepcopy(load_manifest())
    if before.get("_meta", {}).get("collection_complete") is not True:
        print("[watch --run] 진입 차단 — _meta.collection_complete != true(마감 미완).",
              file=sys.stderr, flush=True)
        return 1

    today = datetime.now(timezone.utc).strftime("%y%m%d")
    batch_id = compute_batch_id(before, today)
    entry = make_batch_entry(batch_id, "belle-manual --run")

    # (1b) open 배치를 디스크에 먼저 등재(수집 중 크래시 시에도 이력 존치).
    working = copy.deepcopy(before)
    register_batch(working, entry)
    save_manifest(working)
    print(f"[watch --run] 배치 {batch_id} open 등재. before rows={len(before['rows'])}", flush=True)

    # (2)(3) 하위 수집기 위임 — verdict 캐시 + s3_key 멱등이 재과금 차단. stdout 캡처.
    buf = io.StringIO()
    with contextlib.redirect_stdout(_Tee(sys.stdout, buf)):
        yt.main(_yt_passthrough("--curate", args))
        yt.main(_yt_passthrough("--collect", args))
        ig.main(_ig_passthrough(args))
    captured = buf.getvalue()
    counts = _parse_collect_counts(captured)

    # (4) 재로드 → 신규 행 collection_batch 태깅 + 배치 entry 갱신.
    after = load_manifest()
    before_len = len(before["rows"])
    tagged_new = [make_watch_row(r, batch_id) for r in after["rows"][before_len:]]
    after["rows"] = after["rows"][:before_len] + tagged_new
    new_by_source = {"youtube": 0, "instagram": 0}
    for r in tagged_new:
        if r.get("source") in new_by_source:
            new_by_source[r["source"]] += 1
    update_batch_entry(
        after, batch_id,
        sources=new_by_source,
        new_rows=len(tagged_new),
        curated_reject=counts["curated_reject"],
        skipped_existing=counts["skipped_existing"],
        status="collected",
        cumulative_rows_after=len(after["rows"]),
    )

    # (5) 불변식 통과 후에만 저장.
    assert_ledger_invariants(before, after)
    save_manifest(after)

    # 리포트(은폐 금지) — stdout 요약 + watch_reports/{batch_id}.json.
    entry_after = next(b for b in after["_meta"]["collection_batches"] if b["batch_id"] == batch_id)
    summary = summarize_run(before, after, entry_after)
    report_path = write_report(batch_id, summary)
    print(
        f"\n[watch --run] 배치 {batch_id} collected — 신규 {summary['new_rows']} "
        f"(yt {summary['new_by_source']['youtube']} / ig {summary['new_by_source']['instagram']}) "
        f"| reject {summary['curated_reject']} | skip(기존) {summary['skipped_existing']} "
        f"| 버킷 정타 {summary['new_by_bucket']['정타']} / fault {summary['new_by_bucket']['fault']} "
        f"| 누적 training 행 {summary['cumulative_rows_after']}\n"
        f"  리포트: {report_path}",
        flush=True,
    )

    # (6) 수집 후 게이트 자동 재검증(FAIL 은 exit 비0으로 표면화 — 은폐 금지).
    gate = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tests/phase22/test_manifest_consistency.py",
         "tests/phase22/test_provenance.py", "-q"],
        cwd=str(BACKEND),
    )
    if gate.returncode != 0:
        print(f"[watch --run] 수집 후 게이트 FAIL (exit {gate.returncode}) — 원장 표면화.",
              file=sys.stderr, flush=True)
        return gate.returncode
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 22 데이터 플라이휠 쌓기 러너 — --dry-run 안전, --run belle 게이트"
    )
    parser.add_argument("--sources", default=str(SOURCES_YAML))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="watch 대상 + 원장 self-check + 하위 dry-run (기본)")
    mode.add_argument("--run", action="store_true", help="실 수집 (belle greenlight 필수)")
    parser.add_argument("--only", default=None, help="채널/계정명 부분일치 (파일럿 스코프)")
    parser.add_argument("--limit-per-channel", type=int, default=None, dest="limit_per_channel")
    parser.add_argument("--cap-per-account", type=int, default=None, dest="cap_per_account")
    parser.add_argument("--max-candidates", type=int, default=None, dest="max_candidates")
    args = parser.parse_args(argv)

    registry = yt.load_registry(Path(args.sources))
    if args.run:
        return _run(registry, args)
    return _dry_run(registry, args)


if __name__ == "__main__":
    sys.exit(main())
