"""배치 원장 불변식 + watch 오케스트레이션 순수성 테스트 (22-11).

검사:
  · make_batch_entry 가 정확한 키 집합(여분 0)을 반환.
  · register_batch 가 _meta.collection_batches 에 append 만 하고 나머지 _meta/rows 를 보존.
  · batch_id 중복 register 는 ValueError.
  · assert_ledger_invariants 가 마감 무결성(collection_complete True 유지 +
    collection_closed/balance_waiver 무변형 + rows append-only)을 강제.
  · watch 수집 행 규약(collection_batch=batch_id 주입, 기존 행 무접촉).
  · phase22_watch 헬퍼가 순수(네트워크/boto3/yt-dlp 모듈 최상위 import 0).
  · 실 manifest 가 build_jsonl.assert_collection_complete 를 무수정 통과 +
    collection_batches 가 list.

conftest 가 backend/scripts 를 sys.path 에 얹어 phase22_watch 직접 import 가능.
실 수집(과금 경로)은 이 테스트에서 실행하지 않는다 — 순수 헬퍼 + dry-run 게이트만.
"""

import copy
import json
from pathlib import Path

import pytest

import phase22_watch as watch

_BACKEND = Path(__file__).resolve().parents[2]
_MANIFEST = _BACKEND / "training" / "data" / "manifest.json"


def _load_real_manifest() -> dict:
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))


def _synthetic_manifest() -> dict:
    """마감 무결성 검증용 합성 manifest — 실 파일 무접촉."""
    return {
        "_meta": {
            "usage_policy": "training-only-no-redistribution",
            "collection_complete": True,
            "collection_closed": {"closed_at": "2026-07-10", "approved_by": "belle"},
            "balance_waiver": {"approved_by": "belle", "unmet": ["max_le_2min"]},
            "collection_batches": [],
        },
        "rows": [
            {"s3_key": "fixtures/phase22/kip-up/AAA.mp4", "motion": "kip-up",
             "label_bucket": "정타", "source": "youtube", "usage": "x", "holdout": None},
            {"s3_key": "fixtures/phase22/split/BBB.mp4", "motion": "split",
             "label_bucket": "fault", "source": "instagram", "usage": "x", "holdout": None},
        ],
    }


# ── make_batch_entry ────────────────────────────────────────────────────────
def test_make_batch_entry_exact_keys():
    entry = watch.make_batch_entry("watch-260716", "belle-manual")
    expected_keys = {
        "batch_id", "opened_at", "approved_by", "trigger", "sources",
        "new_rows", "curated_reject", "skipped_existing", "status",
        "cumulative_rows_after",
    }
    assert set(entry.keys()) == expected_keys, "여분 키 존재 또는 누락"
    assert entry["batch_id"] == "watch-260716"
    assert entry["approved_by"] == "belle"
    assert entry["trigger"] == "belle-manual"
    assert entry["sources"] == {"youtube": 0, "instagram": 0}
    assert entry["new_rows"] == 0
    assert entry["curated_reject"] == 0
    assert entry["skipped_existing"] == 0
    assert entry["status"] == "open"
    assert entry["cumulative_rows_after"] is None
    # opened_at 은 UTC ISO 문자열(Z 또는 +00:00).
    assert isinstance(entry["opened_at"], str)
    assert "T" in entry["opened_at"]
    assert entry["opened_at"].endswith("Z") or "+00:00" in entry["opened_at"]


# ── register_batch ──────────────────────────────────────────────────────────
def test_register_batch_appends_and_preserves():
    m = _synthetic_manifest()
    before = copy.deepcopy(m)
    entry = watch.make_batch_entry("watch-260716", "belle-manual")
    watch.register_batch(m, entry)
    # collection_batches 에 append.
    assert len(m["_meta"]["collection_batches"]) == 1
    assert m["_meta"]["collection_batches"][0]["batch_id"] == "watch-260716"
    # 다른 _meta 키 무변형.
    assert m["_meta"]["collection_closed"] == before["_meta"]["collection_closed"]
    assert m["_meta"]["balance_waiver"] == before["_meta"]["balance_waiver"]
    assert m["_meta"]["collection_complete"] is True
    # rows 무변형.
    assert m["rows"] == before["rows"]


def test_register_batch_duplicate_raises():
    m = _synthetic_manifest()
    watch.register_batch(m, watch.make_batch_entry("watch-260716", "t"))
    with pytest.raises(ValueError):
        watch.register_batch(m, watch.make_batch_entry("watch-260716", "t"))


def test_update_batch_entry_mutates_existing():
    m = _synthetic_manifest()
    watch.register_batch(m, watch.make_batch_entry("watch-260716", "t"))
    watch.update_batch_entry(m, "watch-260716", new_rows=5, status="collected")
    entry = m["_meta"]["collection_batches"][0]
    assert entry["new_rows"] == 5
    assert entry["status"] == "collected"
    with pytest.raises(KeyError):
        watch.update_batch_entry(m, "watch-999999", new_rows=1)


# ── assert_ledger_invariants ────────────────────────────────────────────────
def test_ledger_invariants_pass_on_append():
    before = _synthetic_manifest()
    after = copy.deepcopy(before)
    # 신규 행 append + 배치 등재 (정상 경로).
    after["rows"].append(
        {"s3_key": "fixtures/phase22/split/CCC.mp4", "motion": "split",
         "label_bucket": "fault", "source": "youtube", "usage": "x",
         "holdout": None, "collection_batch": "watch-260716"}
    )
    watch.register_batch(after, watch.make_batch_entry("watch-260716", "t"))
    watch.assert_ledger_invariants(before, after)  # 예외 없어야.


def test_ledger_invariants_fail_on_existing_row_mutation():
    before = _synthetic_manifest()
    after = copy.deepcopy(before)
    after["rows"][0]["label_bucket"] = "fault"  # 기존 행 변형 = 위반.
    with pytest.raises(AssertionError):
        watch.assert_ledger_invariants(before, after)


def test_ledger_invariants_fail_on_row_deletion():
    before = _synthetic_manifest()
    after = copy.deepcopy(before)
    after["rows"].pop(0)  # 기존 행 삭제 = append-only 위반.
    with pytest.raises(AssertionError):
        watch.assert_ledger_invariants(before, after)


def test_ledger_invariants_fail_on_collection_closed_mutation():
    before = _synthetic_manifest()
    after = copy.deepcopy(before)
    after["_meta"]["collection_closed"]["scope"] = "훼손"  # 마감 원장 변형.
    with pytest.raises(AssertionError):
        watch.assert_ledger_invariants(before, after)


def test_ledger_invariants_fail_when_collection_complete_flipped():
    before = _synthetic_manifest()
    after = copy.deepcopy(before)
    after["_meta"]["collection_complete"] = False  # 마감 플래그 훼손.
    with pytest.raises(AssertionError):
        watch.assert_ledger_invariants(before, after)


# ── 신규 행 규약 ─────────────────────────────────────────────────────────────
def test_make_watch_row_injects_batch_field():
    base = {"s3_key": "fixtures/phase22/split/DDD.mp4", "motion": "split",
            "label_bucket": "fault", "source": "youtube", "usage": "x", "holdout": None}
    tagged = watch.make_watch_row(base, "watch-260716")
    assert tagged["collection_batch"] == "watch-260716"
    # 원본 무접촉(순수).
    assert "collection_batch" not in base
    # 기존 필드 보존.
    assert tagged["s3_key"] == base["s3_key"]
    assert tagged["motion"] == base["motion"]


def test_compute_batch_id_same_day_suffix():
    m = _synthetic_manifest()
    assert watch.compute_batch_id(m, "260716") == "watch-260716"
    watch.register_batch(m, watch.make_batch_entry("watch-260716", "t"))
    assert watch.compute_batch_id(m, "260716") == "watch-260716-2"
    watch.register_batch(m, watch.make_batch_entry("watch-260716-2", "t"))
    assert watch.compute_batch_id(m, "260716") == "watch-260716-3"


# ── 순수성(네트워크/무거운 의존 import 0) ────────────────────────────────────
def test_module_has_no_heavy_toplevel_imports():
    src = (_BACKEND / "scripts" / "phase22_watch.py").read_text(encoding="utf-8")
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # 모듈 최상위(들여쓰기 0) import 만 검사 — 함수 내부 lazy import 는 허용.
        if line.startswith(("import ", "from ")):
            for banned in ("boto3", "yt_dlp"):
                assert banned not in line, f"최상위 {banned} import 금지: {line}"


# ── 실 manifest 호환 (build_jsonl 무수정 통과) ───────────────────────────────
def test_real_manifest_collection_batches_is_list():
    m = _load_real_manifest()
    assert isinstance(m["_meta"].get("collection_batches"), list)
    assert m["_meta"]["collection_complete"] is True


def test_real_manifest_passes_build_jsonl_gate():
    """collection_batches 추가가 build_jsonl.assert_collection_complete 를 안 깨뜨림."""
    import sys
    sys.path.insert(0, str(_BACKEND / "training"))
    from datagen.build_jsonl import assert_collection_complete

    m = _load_real_manifest()
    assert_collection_complete(m, partial=False)  # 예외 없어야.


# ── Task 2: watch 대상 선별 ──────────────────────────────────────────────────
def _synthetic_registry() -> dict:
    return {
        "defaults": {},
        "channels": [
            {"name": "ytA", "platform": "youtube", "bucket": "정타", "enabled": True},
            {"name": "ytOff", "platform": "youtube", "bucket": "정타", "enabled": True,
             "watch": False},
            {"name": "ytDisabled", "platform": "youtube", "bucket": "정타", "enabled": False},
            {"name": "igA", "platform": "instagram", "bucket": "fault", "enabled": False},
            {"name": "igOff", "platform": "instagram", "bucket": "fault", "enabled": False,
             "watch": False},
        ],
    }


def test_watch_targets_excludes_watch_false():
    reg = _synthetic_registry()
    t = watch.watch_targets(reg)
    yt_names = {c["name"] for c in t["youtube"]}
    ig_names = {c["name"] for c in t["instagram"]}
    # watch:false 제외.
    assert "ytOff" not in yt_names
    assert "igOff" not in ig_names
    # YT 는 enabled 만(disabled 제외), IG 는 enabled 무관(트랙 전체).
    assert "ytDisabled" not in yt_names
    assert yt_names == {"ytA"}
    assert ig_names == {"igA"}


def test_real_registry_eunji_is_watch_target():
    """정은지(eunji.poledancer)는 watch:false 부재 = watch 대상 + cap 60 유지."""
    reg = watch.yt.load_registry(watch.SOURCES_YAML)
    t = watch.watch_targets(reg)
    ig_names = {c["name"] for c in t["instagram"]}
    assert "eunji.poledancer" in ig_names
    eunji = next(c for c in t["instagram"] if c["name"] == "eunji.poledancer")
    assert eunji.get("cap_per_account") == 60


# ── Task 2: summarize_run + 카운트 파싱 ──────────────────────────────────────
def test_summarize_run_counts():
    before = _synthetic_manifest()
    after = copy.deepcopy(before)
    after["rows"].append(
        {"s3_key": "fixtures/phase22/x/N1.mp4", "motion": "x", "label_bucket": "fault",
         "source": "youtube", "usage": "x", "holdout": None, "collection_batch": "watch-260716"})
    after["rows"].append(
        {"s3_key": "fixtures/phase22/x/N2.mp4", "motion": "x", "label_bucket": "정타",
         "source": "instagram", "usage": "x", "holdout": None, "collection_batch": "watch-260716"})
    entry = watch.make_batch_entry("watch-260716", "t")
    entry["curated_reject"] = 3
    entry["skipped_existing"] = 5
    s = watch.summarize_run(before, after, entry)
    assert s["new_rows"] == 2
    assert s["new_by_source"] == {"youtube": 1, "instagram": 1}
    assert s["new_by_bucket"] == {"정타": 1, "fault": 1}
    assert s["curated_reject"] == 3
    assert s["skipped_existing"] == 5
    # 누적 = before(2) + new(2).
    assert s["cumulative_rows_after"] == 4


def test_parse_collect_counts():
    text = (
        "  KoreaPole [정타] 열거 40 필터통과 12 | gated 12 keep 8 reject 3 unknown 1\n"
        "  BerryTV  [fault] 열거 20 필터통과  5 | gated  5 keep 2 reject 2 unknown 1\n"
        "[collect] 다운로드 6 | skip(기존) 4 | unavailable 0 | fail 0 | manifest rows 245\n"
        "[collect-ig] 적재 2 | reject(품질) 1 | skip(기존) 3 | fail 0 | manifest rows 248.\n"
    )
    c = watch._parse_collect_counts(text)
    assert c["curated_reject"] == 5   # 3 + 2
    assert c["skipped_existing"] == 7  # 4 + 3


# ── Task 2: --run 게이트 ─────────────────────────────────────────────────────
def test_run_gate_blocks_without_greenlight(monkeypatch):
    monkeypatch.delenv("PHASE22_BELLE_GREENLIGHT", raising=False)
    with pytest.raises(SystemExit) as ei:
        watch.main(["--run"])
    assert ei.value.code == 2


def test_run_gate_blocks_with_empty_greenlight(monkeypatch):
    monkeypatch.setenv("PHASE22_BELLE_GREENLIGHT", "")
    with pytest.raises(SystemExit) as ei:
        watch.main(["--run"])
    assert ei.value.code == 2
