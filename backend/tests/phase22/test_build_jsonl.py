"""3트랙 학습 JSONL 조립기 검증 — 규격·격리·균등·leakage 방지 (22-04 Task 2).

네트워크 0 — Firestore/S3 는 주입 가능한 loader 인터페이스로 분리한다. 소형 fixture
manifest 로 조립 로직만 검증한다. belle 노트 §8 원형(system / user video+RTMW_Data /
assistant thought+통합리포트) + D-11 알파벳 정렬 + D-01 score-free + DR-01 shadow 격리
+ DR-04/06 validation_owner/collection_complete 게이트.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from datagen import build_jsonl
from datagen import schema


# ---------------------------------------------------------------------------
# fixture — 소형 manifest + 주입 loader.
# ---------------------------------------------------------------------------
_JOINT_KEYS = ["left_knee", "right_knee", "left_hip", "right_hip"]


def _coords(t=6, j=4):
    rng = np.random.default_rng(0)
    return rng.random((t, j, 3)).astype(float)


def _manifest(collection_complete=True):
    return {
        "_meta": {
            "usage_policy": "training-only-no-redistribution",
            "collection_complete": collection_complete,
            "schema_version": schema.SCHEMA_VERSION,
        },
        "rows": [
            {"s3_key": "fixtures/phase22/kip-up/a.mp4", "motion": "kip-up",
             "label_bucket": "정타", "source": "youtube", "usage": "training-only",
             "holdout": None, "anonymized": False, "video_hash": "hashA"},
            {"s3_key": "fixtures/phase22/kip-up/b.mp4", "motion": "kip-up",
             "label_bucket": "fault", "source": "internal", "usage": "training-only",
             "holdout": None, "anonymized": False, "video_hash": "hashB"},
            {"s3_key": "fixtures/phase22/split/c.mp4", "motion": "split",
             "label_bucket": "정타", "source": "youtube", "usage": "training-only",
             "holdout": None, "anonymized": False, "video_hash": "hashC"},
            {"s3_key": "fixtures/phase22/split/d.mp4", "motion": "split",
             "label_bucket": "fault", "source": "internal", "usage": "training-only",
             "holdout": None, "anonymized": False, "video_hash": "hashD"},
            # hard-negative eval — 절대 학습에 유입 금지.
            {"s3_key": None, "motion": "peter-pan", "label_bucket": "fault",
             "source": "internal_pilot", "usage": "eval-only", "holdout": "hard_negative_eval",
             "anonymized": False, "video_hash": "hashHN"},
            # 미가명 고객 행 — media 유입 금지.
            {"s3_key": "fixtures/phase22/cust/e.mp4", "motion": "kip-up",
             "label_bucket": "fault", "source": "customer", "usage": "training-only",
             "holdout": None, "anonymized": False, "video_hash": "hashCust"},
        ],
    }


def _perturb_loader(row):
    if not row.get("s3_key"):
        return None
    return {"coords": _coords(), "joint_keys": _JOINT_KEYS, "width": 640.0, "height": 480.0}


def _distill_record(video_hash, motion):
    return {
        "video_hash": video_hash,
        "motion": motion,
        "thought": "가려짐으로 좌표가 튐. 무릎 각도 재측정.",
        "report": {
            "coaching": "무릎을 더 펴세요",
            "faults": [
                {"student_angle_deg": 120.0, "reference_angle_deg": 178.0,
                 "measurement_basis": "왼무릎 관절각", "fault_category": "limb_extension",
                 "body_part": "왼무릎"}
            ],
            "svg_spec": {"force_vector": [0.0, -1.0], "ideal_trajectory": [[0.1, 0.1]]},
        },
    }


def _distill_loader():
    return [
        _distill_record("hashA", "kip-up"),
        _distill_record("hashC", "split"),
    ]


def _shadow_loader():
    return [
        # 등록 + anonymized 아님 → media 강등(text-only). (customer row hashCust)
        {"video_hash": "hashCust", "roles": {"coach": {"text": "골반을 세우세요"},
                                             "veto": {"verdict": "fault"}}},
        # 미등록 hash → text-only.
        {"video_hash": "hashUNREG", "roles": {"coach": {"text": "팔을 펴세요"},
                                              "veto": {"verdict": "fault"}}},
    ]


def _reference_loader(motion):
    return {"target_angle_deg": 178.0}


def _build(**overrides):
    kwargs = dict(
        manifest=_manifest(),
        perturb_loader=_perturb_loader,
        distill_loader=_distill_loader,
        shadow_loader=_shadow_loader,
        reference_loader=_reference_loader,
        partial=False,
        seed=0,
    )
    kwargs.update(overrides)
    return build_jsonl.build_dataset(**kwargs)


# ---------------------------------------------------------------------------
# Test 1 — belle 노트 §8 3롤 구조.
# ---------------------------------------------------------------------------
def test_message_structure_three_roles():
    data = _build()
    media = [s for s in data["train"] if build_jsonl.sample_has_video(s)]
    assert media, "media 샘플 부재"
    s = media[0]
    msgs = s["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert msgs[2]["role"] == "assistant"
    # user 에 video 참조 + RTMW_Data 텍스트.
    types = [c.get("type") for c in msgs[1]["content"]]
    assert "video" in types and "text" in types
    rtmw = [c["text"] for c in msgs[1]["content"] if c.get("type") == "text"][0]
    assert rtmw.startswith("RTMW_Data:")
    # assistant = thought + REPORT_KEYS 알파벳 정렬 JSON.
    report = build_jsonl.assistant_report(s)
    assert list(report.keys()) == sorted(report.keys())
    for k in schema.REPORT_KEYS:
        assert k in report


# ---------------------------------------------------------------------------
# Test 2 — score-free (normalize_report 강제).
# ---------------------------------------------------------------------------
def test_assistant_json_has_no_score_keys():
    data = _build()
    for s in data["train"] + (data["val"] or []):
        report = build_jsonl.assistant_report(s)
        if report is None:
            continue
        flat = json.dumps(report)
        for banned in ('"score"', '"overall"', '"points"', '"severity"', '"rating"'):
            assert banned not in flat


# ---------------------------------------------------------------------------
# Test 3 — hard-negative + 미가명 고객 media 0.
# ---------------------------------------------------------------------------
def test_hard_negative_and_unanonymized_customer_excluded():
    data = _build()
    all_samples = data["train"] + (data["val"] or [])
    hashes_with_video = {
        s.get("_video_hash") for s in all_samples if build_jsonl.sample_has_video(s)
    }
    assert "hashHN" not in hashes_with_video
    assert "hashCust" not in hashes_with_video  # 미가명 고객 = media 금지.


# ---------------------------------------------------------------------------
# Test 4 — 동작별 균등 + 트랙별 카운트.
# ---------------------------------------------------------------------------
def test_balance_gate_and_track_counts():
    data = _build()
    meta = data["_meta"]
    assert "track_counts" in meta
    for track in ("perturb", "distill", "shadow", "text"):
        assert track in meta["track_counts"]
    # 동작별 media 샘플 균등 (max <= 2*min).
    per_motion = meta.get("motion_counts", {})
    counts = [v for v in per_motion.values() if v > 0]
    if counts:
        assert max(counts) <= 2 * min(counts), per_motion


# ---------------------------------------------------------------------------
# Test 5 — T3 시간추론 + 순수 텍스트 instruction 혼합비.
# ---------------------------------------------------------------------------
def test_text_mix_ratio_present():
    data = _build()
    text_samples = [s for s in data["train"] if s.get("_track") == "text"]
    assert text_samples, "텍스트 혼합 샘플 부재"
    kinds = {s.get("_text_kind") for s in text_samples}
    assert "t3_temporal" in kinds
    assert "instruction" in kinds
    # 기본 혼합비 config 합 0.15.
    assert abs(sum(build_jsonl.DEFAULT_MIX_RATIOS.values()) - 0.15) < 1e-9


# ---------------------------------------------------------------------------
# Test 6 — video_hash 단위 split (leakage 0).
# ---------------------------------------------------------------------------
def test_split_by_video_hash_no_leakage():
    data = _build(validation_owner="explicit_val_jsonl")
    train_hashes = {s.get("_video_hash") for s in data["train"] if s.get("_video_hash")}
    val_hashes = {s.get("_video_hash") for s in (data["val"] or []) if s.get("_video_hash")}
    assert train_hashes.isdisjoint(val_hashes), (train_hashes & val_hashes)


# ---------------------------------------------------------------------------
# Test 7 — faults[] 감점 계약 상위집합 (미충족 폐기).
# ---------------------------------------------------------------------------
def test_faults_satisfy_deduction_contract():
    def _bad_distill():
        rec = _distill_record("hashA", "kip-up")
        # 각도쌍 제거 → 계약 미충족 → 폐기돼야 함.
        rec["report"]["faults"] = [{"fault_category": "limb_extension", "body_part": "왼무릎"}]
        return [rec]

    data = _build(distill_loader=_bad_distill)
    for s in data["train"] + (data["val"] or []):
        report = build_jsonl.assistant_report(s)
        if not report:
            continue
        for f in report.get("faults") or []:
            has_pair = f.get("student_angle_deg") is not None and f.get("reference_angle_deg") is not None
            has_fallback = f.get("approx_angle_deviation_deg") is not None
            assert has_pair or has_fallback
            assert f.get("fault_category")


# ---------------------------------------------------------------------------
# Test 8 — svg_spec 결정적 target_angle_deg + force/ideal 교사분 or Null.
# ---------------------------------------------------------------------------
def test_svg_spec_deterministic_target_angle():
    data = _build()
    found = False
    for s in data["train"] + (data["val"] or []):
        report = build_jsonl.assistant_report(s)
        if not report:
            continue
        svg = report.get("svg_spec")
        if svg is None:
            continue
        # svg_spec 전체가 스키마 유효 (SVG_SPEC_KEYS).
        assert set(svg.keys()) == set(schema.SVG_SPEC_KEYS)
        if svg.get("target_angle_deg") is not None:
            assert svg["target_angle_deg"] == 178.0  # reference_loader 결정적 산출.
            found = True
    assert found, "결정적 target_angle_deg 산출 샘플 부재"


# ---------------------------------------------------------------------------
# Test 9 — 미등록 shadow → video 참조 0 (text-only 허용).
# ---------------------------------------------------------------------------
def test_unregistered_shadow_no_video_reference():
    data = _build()
    for s in data["train"] + (data["val"] or []):
        if s.get("_track") == "shadow" and s.get("_video_hash") in ("hashUNREG", "hashCust"):
            assert not build_jsonl.sample_has_video(s), "미등록/미가명 shadow media 유입"


# ---------------------------------------------------------------------------
# Test 10 — shadow 드롭 카운터 방출.
# ---------------------------------------------------------------------------
def test_shadow_drop_counters_emitted():
    data = _build()
    meta = data["_meta"]
    assert "shadow_unregistered_dropped" in meta
    assert "shadow_text_only_count" in meta
    assert meta["shadow_unregistered_dropped"] >= 1
    assert meta["shadow_text_only_count"] >= 1


# ---------------------------------------------------------------------------
# Test 11 — collection_complete fail-closed + partial prefix 격리.
# ---------------------------------------------------------------------------
def test_collection_incomplete_fails_without_partial():
    with pytest.raises((ValueError, SystemExit)):
        build_jsonl.assert_collection_complete(_manifest(collection_complete=False), partial=False)
    # partial 이면 통과.
    build_jsonl.assert_collection_complete(_manifest(collection_complete=False), partial=True)


def test_partial_run_not_canonical_prefix():
    canonical = build_jsonl.resolve_upload_prefix(partial=False)
    partial = build_jsonl.resolve_upload_prefix(partial=True)
    assert canonical == "training/phase22/jsonl/"
    assert partial != canonical


# ---------------------------------------------------------------------------
# Test 12 — validation_owner 계약과 발행물 정합.
# ---------------------------------------------------------------------------
def test_validation_owner_explicit_emits_val():
    data = _build(validation_owner="explicit_val_jsonl")
    assert data["_meta"]["validation_owner"] == "explicit_val_jsonl"
    assert data["val"] is not None  # val.jsonl 발행.


def test_validation_owner_eval_gate_omits_val():
    data = _build(validation_owner="phase22_eval_gate")
    assert data["_meta"]["validation_owner"] == "phase22_eval_gate"
    assert data["val"] is None  # val 미발행 (eval gate 소유).


def test_validation_owner_must_be_valid():
    with pytest.raises(ValueError):
        _build(validation_owner="bogus")
