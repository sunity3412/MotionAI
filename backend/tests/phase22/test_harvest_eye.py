"""기계 눈 원장 수확기 순수층 TDD (quick 260814-j24 Task 1).

고정하는 계약:
  · 원장 JSON 3형태(analysisId+entries / flat / flat+motion) 전부 흡수.
  · 식별자는 크롭 content hash 단독 — uid/analysisId 키·값(Firebase uid 패턴) 차단(P-4).
  · disposition 표 P-1~P-5 + 동의 실측(consent) 분기 우선순위.
  · match=false(트랙-눈 불일치) 행은 절대 버려지지 않는다 — 이 코퍼스의 최고가치.
  · 같은 원장 재수확은 멱등(added 0).
네트워크/boto3/numpy 의존 0.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from datagen import harvest_eye as he

_REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# 행 계약 — score/severity 구조적 부재 + 식별자 키 부재.
# ---------------------------------------------------------------------------
def test_eye_row_keys_have_no_score_or_identifier_fields():
    lowered = [k.lower() for k in he.EYE_ROW_KEYS]
    for banned in ("score", "severity", "overall", "points", "grade", "rating"):
        assert not any(banned in k for k in lowered), f"점수 계열 키 유입: {banned}"
    for banned in ("uid", "analysis_id", "analysisid", "email", "user_id"):
        assert banned not in lowered, f"식별자 키 유입: {banned}"
    assert "media_sha16" in he.EYE_ROW_KEYS
    assert "track_claim_agrees" in he.EYE_ROW_KEYS


# ---------------------------------------------------------------------------
# iter_ledger_entries — 3형태 흡수.
# ---------------------------------------------------------------------------
def test_iter_ledger_entries_shape_a_analysis_id_entries():
    doc = {"analysisId": "x", "entries": [{"joint": "a"}, {"joint": "b"}]}
    assert he.iter_ledger_entries(doc) == [{"joint": "a"}, {"joint": "b"}]


def test_iter_ledger_entries_shape_b_flat_single_entry():
    doc = {"side": "user", "joint": "left_knee", "claim": "bent", "observed": "bent"}
    assert he.iter_ledger_entries(doc) == [doc]


def test_iter_ledger_entries_shape_c_flat_with_motion():
    doc = {"motion": "pdshapefault", "rid": "r00", "side": "ref", "joint": "left_elbow",
           "trackAngleDeg": 171.7, "claim": "extended", "observed": "extended"}
    assert he.iter_ledger_entries(doc) == [doc]


@pytest.mark.parametrize("doc", [None, [], [1, 2], "x", 3, {"entries": "not-a-list"}])
def test_iter_ledger_entries_rejects_non_dict_and_damaged(doc):
    assert he.iter_ledger_entries(doc) == []


# ---------------------------------------------------------------------------
# content_hash / media_key — 멱등 키.
# ---------------------------------------------------------------------------
def test_content_hash_is_16_hex_and_deterministic():
    h1 = he.content_hash(b"\x89PNG-bytes")
    h2 = he.content_hash(b"\x89PNG-bytes")
    assert h1 == h2
    assert len(h1) == 16
    assert all(c in "0123456789abcdef" for c in h1)
    assert he.content_hash(b"other") != h1


def test_media_key_prefix_is_fixed():
    assert he.media_key("0123456789abcdef") == "training/phase22/eye/0123456789abcdef.png"


# ---------------------------------------------------------------------------
# consent_disposition — P-1~P-5 표 + consent 실측 분기(우선순위 고정).
# ---------------------------------------------------------------------------
def test_p2_ref_repo_evidence_with_motion_is_admitted():
    assert he.consent_disposition("ref", "pdshapefault", "repo_evidence") == (
        "admit", "internal_seed_ref"
    )


def test_p1_user_side_is_held_even_with_motion():
    assert he.consent_disposition("user", "pdshapefault", "repo_evidence") == (
        "hold", "customer_anonymize_required"
    )


def test_p1_user_side_stays_held_even_when_optin_measured_true():
    """동의 실측 true 라도 user 픽셀은 가명처리(B-1 belle 미결)가 남아 hold."""
    assert he.consent_disposition("user", "m", "s3_operational", consent=True) == (
        "hold", "customer_anonymize_required"
    )


def test_p3_s3_operational_is_held_when_optin_unverified():
    assert he.consent_disposition("ref", "m", "s3_operational") == (
        "hold", "optin_unverified_post_cutoff"
    )
    assert he.consent_disposition("ref", "m", "s3_operational", consent=None) == (
        "hold", "optin_unverified_post_cutoff"
    )


def test_s3_operational_ref_admitted_only_when_optin_measured_true():
    assert he.consent_disposition("ref", "m", "s3_operational", consent=True) == (
        "admit", "internal_seed_ref_optin_verified"
    )


def test_consent_denied_outranks_every_other_branch():
    """learningOptIn=false 는 어떤 조합에서도 무조건 제외(LICENSE-AUDIT 7-1(b))."""
    assert he.consent_disposition("ref", "m", "repo_evidence", consent=False) == (
        "hold", "consent_denied"
    )
    assert he.consent_disposition("ref", "m", "s3_operational", consent=False) == (
        "hold", "consent_denied"
    )


def test_p5_motion_unresolved_is_held():
    for motion in (None, "", 0):
        assert he.consent_disposition("ref", motion, "repo_evidence") == (
            "hold", "motion_unknown"
        )


def test_unclassified_side_is_held():
    assert he.consent_disposition("both", "m", "repo_evidence") == ("hold", "unclassified")


def test_disposition_hold_priority_user_outranks_motion_unknown():
    assert he.consent_disposition("user", None, "repo_evidence") == (
        "hold", "customer_anonymize_required"
    )


# ---------------------------------------------------------------------------
# entry_to_row — 라벨 없음 fail-closed / 불일치 보존.
# ---------------------------------------------------------------------------
def _entry(**over):
    base = {
        "side": "ref", "joint": "left_elbow", "frameIdx": 18, "sec": 1.2,
        "claim": "extended", "observed": "extended", "trackAngleDeg": 171.7,
        "limb": "arm", "match": True, "confidence": 0.9, "reason": "elbow extended",
    }
    base.update(over)
    return base


def _row(**kw):
    kw.setdefault("entry", _entry())
    kw.setdefault("source_kind", "repo_evidence")
    kw.setdefault("source_ref", ".planning/quick/x/eye_ledger/a.json#0")
    kw.setdefault("motion", "pdshapefault")
    kw.setdefault("motion_source", "entry")
    kw.setdefault("png_bytes", b"png-a")
    kw.setdefault("collected_at", "2026-08-14T00:00:00Z")
    return he.entry_to_row(**kw)


def test_entry_to_row_emits_exact_key_contract():
    row = _row()
    assert tuple(sorted(row)) == tuple(sorted(he.EYE_ROW_KEYS))


def test_entry_to_row_observed_error_returns_none():
    assert _row(entry=_entry(observed="error")) is None


def test_entry_to_row_preserves_mismatch_rows():
    """match=false = 트랙-눈 불일치 = keypoint 환각 라벨. 절대 버리지 않는다."""
    row = _row(entry=_entry(match=False, claim="bent", observed="extended"))
    assert row is not None
    assert row["track_claim_agrees"] is False
    assert row["claim"] == "bent"
    assert row["observed"] == "extended"


def test_entry_to_row_carries_provenance_and_usage():
    row = _row()
    assert row["source_kind"] == "repo_evidence"
    assert row["source_ref"].endswith("#0")
    assert row["motion_source"] == "entry"
    assert row["collected_at"] == "2026-08-14T00:00:00Z"
    assert row["usage"] == "training-only-no-redistribution"
    assert row["source"] == "internal_machine_eye"
    assert row["uploaded"] is False


def test_entry_to_row_eye_id_is_content_hash_only():
    row = _row(png_bytes=b"png-XYZ")
    assert row["eye_id"] == he.content_hash(b"png-XYZ")
    assert row["media_sha16"] == row["eye_id"]
    assert row["media_key"] == he.media_key(row["eye_id"])


def test_entry_to_row_applies_disposition_and_consent_flag():
    admit = _row()
    assert admit["disposition"] == "admit"
    hold = _row(entry=_entry(side="user"))
    assert hold["disposition"] == "hold"
    assert hold["disposition_reason"] == "customer_anonymize_required"
    assert hold["consent_flag"] is None


def test_entry_to_row_records_measured_consent_flag():
    row = _row(consent=True, source_kind="s3_operational")
    assert row["consent_flag"] is True
    assert row["disposition"] == "admit"


# ---------------------------------------------------------------------------
# assert_no_identifier_keys — P-4 fence.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "key", ["uid", "uidHash", "analysisId", "analysis_id", "email", "user_id"]
)
def test_assert_no_identifier_keys_rejects_forbidden_keys(key):
    row = _row()
    row[key] = "x"
    with pytest.raises(ValueError):
        he.assert_no_identifier_keys(row)


def test_assert_no_identifier_keys_rejects_firebase_uid_pattern_value():
    """실측 Firebase uid(28자 영숫자)가 값에 섞여도 거부."""
    row = _row()
    row["source_ref"] = "results/fvcNXzEqKjgqVxRPVSj1iwFnIpn2/p34fresh1/eye/00.png"
    with pytest.raises(ValueError):
        he.assert_no_identifier_keys(row)


def test_assert_no_identifier_keys_passes_clean_row():
    he.assert_no_identifier_keys(_row())  # 예외 없음.


def test_assert_no_identifier_keys_allows_16_hex_media_key():
    row = _row()
    assert len(row["media_sha16"]) == 16
    he.assert_no_identifier_keys(row)


# ---------------------------------------------------------------------------
# merge_rows — eye_id 멱등.
# ---------------------------------------------------------------------------
def test_merge_rows_is_idempotent_on_eye_id():
    a = _row(png_bytes=b"a")
    b = _row(png_bytes=b"b")
    merged, added, skipped = he.merge_rows([], [a, b])
    assert (added, skipped) == (2, 0)
    merged2, added2, skipped2 = he.merge_rows(merged, [a, b])
    assert (added2, skipped2) == (0, 2)
    assert merged2 == merged


def test_merge_rows_does_not_mutate_existing_rows():
    a = _row(png_bytes=b"a")
    existing = [dict(a)]
    changed = dict(a)
    changed["reason"] = "재수확에서 바뀐 문구"
    merged, added, skipped = he.merge_rows(existing, [changed])
    assert (added, skipped) == (0, 1)
    assert merged[0]["reason"] == a["reason"]


def test_merge_rows_dedupes_within_the_new_batch():
    a = _row(png_bytes=b"a")
    merged, added, skipped = he.merge_rows([], [a, dict(a)])
    assert (added, skipped) == (1, 1)
    assert len(merged) == 1


# ---------------------------------------------------------------------------
# summarize — 규모 실측 리포트 단일 출처.
# ---------------------------------------------------------------------------
def test_summarize_counts_total_disposition_mismatch_joint_observed_side():
    rows = [
        _row(png_bytes=b"1"),
        _row(png_bytes=b"2", entry=_entry(side="user", match=False, observed="bent",
                                          claim="extended", joint="left_hip")),
        _row(png_bytes=b"3", entry=_entry(side="user", joint="left_knee",
                                          observed="unclear", match=False)),
    ]
    s = he.summarize(rows)
    assert s["total"] == 3
    assert s["by_disposition"] == {"admit": 1, "hold": 2}
    assert s["by_disposition_reason"]["customer_anonymize_required"] == 2
    assert s["mismatch"] == 2
    assert s["by_joint"] == {"left_elbow": 1, "left_hip": 1, "left_knee": 1}
    assert s["by_observed"] == {"extended": 1, "bent": 1, "unclear": 1}
    assert s["by_side"] == {"ref": 1, "user": 2}
    assert s["admit_mismatch"] == 0


def test_summarize_empty_rows():
    s = he.summarize([])
    assert s["total"] == 0 and s["mismatch"] == 0


# ---------------------------------------------------------------------------
# resolve_motion — 근거 있는 값만 채택(추정 금지).
# ---------------------------------------------------------------------------
def _resolve(entry, **kw):
    kw.setdefault("doc_analysis_id", None)
    kw.setdefault("dir_rel", "d")
    kw.setdefault("motion_map", None)
    kw.setdefault("analysis_motion_map", None)
    kw.setdefault("motion_alias", None)
    return he.resolve_motion(entry, **kw)


def test_resolve_motion_takes_entry_field_first():
    assert _resolve({"motion": "pdshapefault"}) == ("pdshapefault", "entry")


def test_resolve_motion_normalizes_via_documented_alias():
    alias = {"pdshapefault": {"motion": "ref-pdshape", "evidence": "discover_sweep.py:73"}}
    motion, src = _resolve({"motion": "pdshapefault"}, motion_alias=alias)
    assert motion == "ref-pdshape"
    assert src == "entry+operator:discover_sweep.py:73"


def test_resolve_motion_ignores_alias_without_evidence():
    alias = {"pdshapefault": {"motion": "ref-pdshape"}}
    assert _resolve({"motion": "pdshapefault"}, motion_alias=alias) == ("pdshapefault", "entry")


def test_resolve_motion_uses_analysis_map_then_dir_map():
    amap = {"aid1": {"motion": "ref-pdshape", "evidence": "firestore:referenceMotionId"}}
    dmap = {"d": {"motion": "ref-kip-up", "evidence": "doc:x"}}
    assert _resolve({}, doc_analysis_id="aid1", analysis_motion_map=amap, motion_map=dmap) == (
        "ref-pdshape", "operator:firestore:referenceMotionId"
    )
    assert _resolve({}, motion_map=dmap) == ("ref-kip-up", "operator:doc:x")


def test_resolve_motion_refuses_injection_without_evidence():
    assert _resolve({}, motion_map={"d": {"motion": "ref-pdshape"}}) == (None, None)
    assert _resolve({}) == (None, None)


# ---------------------------------------------------------------------------
# 배치 id — watch 규약 준용(eye- 접두 자체 산출).
# ---------------------------------------------------------------------------
def test_compute_eye_batch_id_uses_eye_prefix_and_suffix_convention():
    m = {"_meta": {"collection_batches": []}}
    assert he.compute_eye_batch_id(m, "260814") == "eye-260814"
    m["_meta"]["collection_batches"].append({"batch_id": "eye-260814"})
    assert he.compute_eye_batch_id(m, "260814") == "eye-260814-2"
    m["_meta"]["collection_batches"].append({"batch_id": "eye-260814-2"})
    assert he.compute_eye_batch_id(m, "260814") == "eye-260814-3"


def test_eye_batch_entry_records_ledger_ownership():
    entry = he.make_eye_batch_entry("eye-260814", "harvest_eye --run")
    assert entry["batch_id"] == "eye-260814"
    assert entry["ledger"] == "training/data/eye_manifest.json"
    assert entry["status"] == "open"


# ---------------------------------------------------------------------------
# 통합 — 실 리포 원장 3형태 파싱 (파일 쓰기 0, 네트워크 0).
# ---------------------------------------------------------------------------
def test_real_repo_evidence_covers_all_three_ledger_shapes():
    dirs = he.iter_eye_ledger_dirs(_REPO_ROOT / ".planning")
    if not dirs:
        pytest.skip("리포에 눈 원장 evidence 없음")
    shapes = set()
    entries = 0
    for d in dirs:
        for p in sorted(d.rglob("*.json")):
            doc = json.loads(p.read_text(encoding="utf-8"))
            shape = he.ledger_shape(doc)
            shapes.add(shape)
            entries += len(he.iter_ledger_entries(doc))
    assert entries > 0
    assert shapes >= {"analysis_entries", "flat", "flat_motion"}


def test_real_repo_evidence_scan_produces_identifier_free_rows():
    result = he.scan_repo_evidence(_REPO_ROOT / ".planning")
    if not result["rows"]:
        pytest.skip("리포에 눈 원장 evidence 없음")
    for row in result["rows"]:
        he.assert_no_identifier_keys(row)
        assert row["media_key"].startswith("training/phase22/eye/")
    # 불일치 보존 — 원장에 match=false 가 있으면 수확 행에도 있어야 한다.
    assert result["summary"]["mismatch"] > 0
    assert result["summary"]["total"] == len(result["rows"])


def test_real_repo_evidence_scan_writes_nothing(tmp_path, monkeypatch):
    """스캔은 순수 읽기 — eye_manifest.json 이 생기지 않는다."""
    before = he.EYE_MANIFEST_PATH.exists()
    he.scan_repo_evidence(_REPO_ROOT / ".planning")
    assert he.EYE_MANIFEST_PATH.exists() is before
