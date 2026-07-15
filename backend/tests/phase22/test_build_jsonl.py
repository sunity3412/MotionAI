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


# ---------------------------------------------------------------------------
# Test 13 — v4 자유생성 붕괴 fix (2026-07-14): 태스크 지시문 + distill 항등 echo 제거.
# ---------------------------------------------------------------------------
def test_user_media_msg_contains_task_instruction():
    """user 텍스트 = RTMW_Data 접두 유지 + 출력 계약 지시문 포함 (v3 무지시 입력이
    자유생성을 베이스 프라이어로 이탈시킨 결함의 fix)."""
    data = _build()
    media = [s for s in data["train"] if build_jsonl.sample_has_video(s)]
    for s in media:
        text = [c["text"] for c in s["messages"][1]["content"] if c.get("type") == "text"][0]
        assert text.startswith("RTMW_Data:")  # 기존 계약 불변.
        assert "JSON 리포트" in text and "faults" in text  # 지시문 존재.


def test_distill_track_corrected_coords_always_none():
    """distill 행 corrected_coords=None — 교사 echo 항등 학습(v3 holdout 0.0444≈0.0417)
    차단. 좌표 보정 감독은 perturb 트랙 단독 소유."""
    data = _build()
    for s in data["train"] + (data["val"] or []):
        if s.get("_track") != "distill":
            continue
        report = build_jsonl.assistant_report(s)
        assert report is not None
        assert report.get("corrected_coords") is None


def test_perturb_track_keeps_corrected_coords():
    """perturb 행은 원좌표 corrected_coords 유지 — 실보정 신호 보존."""
    data = _build(include_perturb=True, distill_loader=None, shadow_loader=None)
    perturb = [s for s in data["train"] + (data["val"] or []) if s.get("_track") == "perturb"]
    assert perturb, "perturb 샘플 부재"
    for s in perturb:
        report = build_jsonl.assistant_report(s)
        assert report is not None
        assert report.get("corrected_coords")  # truthy 좌표 리스트.


# ---------------------------------------------------------------------------
# quick-260715-wq9 — C1 perturb descope(가역) + B fault-ratio 재균형.
# ---------------------------------------------------------------------------
def _distill_loader_imbalanced():
    """fault-bearing 1 + fault-free 3 — B 캡 트림 검증(정타가 결함 신호 익사).

    manifest row motion: hashA/hashB=kip-up, hashC/hashD=split — 트랙 내 균등 게이트
    (max<=2*min) 통과. hashA 만 결함 보유(각도쌍), 나머지는 정타(faults=[])."""
    recs = [_distill_record("hashA", "kip-up")]  # 결함 보유.
    for vh in ("hashC", "hashB", "hashD"):
        rec = _distill_record(vh, "kip-up")
        rec["report"]["faults"] = []  # 정타(fault-free).
        recs.append(rec)
    return recs


def _distill_loader_all_clean():
    """전부 정타(fault_bearing==0) — 캡 skip guard 검증."""
    recs = []
    for vh, m in (("hashA", "kip-up"), ("hashC", "split")):
        rec = _distill_record(vh, m)
        rec["report"]["faults"] = []
        recs.append(rec)
    return recs


def test_perturb_excluded_by_default():
    """C1 (belle 2026-07-15) — include_perturb 기본 False → perturb 트랙 부재.

    근거: 모델 5/5 corrected_coords 빈배열 거부 + perturb 95행(faults=[])이 결함
    신호를 익사시키는 최대 주범 → 좌표보정 학습 보류(삭제 아님, 가역 descope)."""
    data = _build()
    perturb = [s for s in data["train"] + (data["val"] or [])
               if s.get("_track") == "perturb"]
    assert perturb == []
    assert data["_meta"]["perturb_coords_only_count"] == 0
    assert data["_meta"]["track_counts"]["perturb"] == 0


def test_perturb_revived_with_include_flag():
    """가역 descope — include_perturb=True 로 도먼트 perturb 트랙 부활(코드 보존)."""
    data = _build(include_perturb=True)
    perturb = [s for s in data["train"] + (data["val"] or [])
               if s.get("_track") == "perturb"]
    assert perturb  # 부활.


def test_fault_free_capped_by_ratio():
    """B — fault-free 미디어가 fault-bearing 대비 캡 비율 초과 시 결정적 트림."""
    data = _build(distill_loader=_distill_loader_imbalanced,
                  perturb_loader=None, shadow_loader=None)
    meta = data["_meta"]
    assert meta["fault_free_cap_ratio"] == build_jsonl.FAULT_FREE_CAP_RATIO
    assert meta["fault_bearing_count"] == 1
    # nb=1, ratio=1.5 → cap=1. fault_free 3 → 1.
    assert meta["fault_free_count"] == 1
    assert meta["fault_free_count"] > 0  # 정타 신호 완전 소거 금지(invariant).
    media = [s for s in data["train"] + (data["val"] or [])
             if build_jsonl.sample_has_video(s)]
    assert len(media) == 2  # fault-bearing 1 + 캡된 fault-free 1.


def test_fault_free_cap_skipped_when_no_fault_bearing():
    """B guard — fault_bearing==0 이면 캡 skip(전량 트림 방지)."""
    data = _build(distill_loader=_distill_loader_all_clean,
                  perturb_loader=None, shadow_loader=None)
    meta = data["_meta"]
    assert meta["fault_bearing_count"] == 0
    assert meta["fault_free_count"] == 2  # 트림 없음(guard).


def test_fault_ratio_meta_emitted():
    """B — _meta 에 fault_bearing/fault_free 관측치 방출(드롭률 은폐 불가)."""
    data = _build()
    for k in ("fault_bearing_count", "fault_free_count", "fault_free_cap_ratio"):
        assert k in data["_meta"]


# ---------------------------------------------------------------------------
# quick-260715-fjw — perturb 트랙 재설계 (D3/D4/D5/D6).
#   C1(260715-wq9) 이후 perturb 는 기본 off — 이 도먼트 경로는 include_perturb=True
#   명시 호출로 커버 유지(가역 descope 보존). distill/shadow 는 None 으로 격리해
#   B fault-free 캡이 perturb 계측을 간섭하지 않게 한다.
# ---------------------------------------------------------------------------
def _perturb_loader_long(row):
    """t=130 > select_frame_indices budget(64) — 서브샘플이 실제로 프레임을 떨군다."""
    if not row.get("s3_key"):
        return None
    rng = np.random.default_rng(1)
    return {
        "coords": rng.random((130, len(_JOINT_KEYS), 3)).astype(float),
        "joint_keys": _JOINT_KEYS,
        "width": 640.0,
        "height": 480.0,
    }


def _all_perturb(data):
    return [
        s for s in data["train"] + (data["val"] or []) if s.get("_track") == "perturb"
    ]


def _user_text(sample) -> str:
    return [
        c["text"] for c in sample["messages"][1]["content"] if c.get("type") == "text"
    ][0]


def _parse_user_frames(text: str) -> list:
    """user 텍스트에서 프레임 행 파싱 — _rtmw_text(frames)+_TASK_INSTRUCTION 역변환."""
    assert text.endswith(build_jsonl._TASK_INSTRUCTION)
    body = text[: -len(build_jsonl._TASK_INSTRUCTION)]
    assert body.startswith("RTMW_Data: ")
    return json.loads(body[len("RTMW_Data: "):])


def test_coords_only_sample_matches_gate_aligned_format():
    """Test D — 좌표전용 perturb 샘플: text 단일 파트, 게이트 aligned 좌표전용
    (build_aligned_report_messages(rows, [])) 경로와 문자 단위 동일 양식."""
    data = _build(include_perturb=True, distill_loader=None, shadow_loader=None)
    coords_only = [
        s for s in _all_perturb(data) if not build_jsonl.sample_has_video(s)
    ]
    assert coords_only, "좌표전용 perturb 샘플 부재"
    for s in coords_only:
        assert s.get("_coords_only") is True
        content = s["messages"][1]["content"]
        assert isinstance(content, list) and len(content) == 1
        assert content[0].get("type") == "text"
        text = content[0]["text"]
        frames = _parse_user_frames(text)
        # 모듈 상수 재사용으로 조립돼 재조립 결과와 문자 단위 동일 (단일 진실).
        assert text == build_jsonl._rtmw_text(frames) + build_jsonl._TASK_INSTRUCTION


def test_coords_only_deterministic_third_ratio_and_counter():
    """Test E — 좌표전용 비율 = 결정적 cycle(1/3), video 양식 다수 유지 + 카운터 방출."""
    data = _build(include_perturb=True, distill_loader=None, shadow_loader=None)
    samples = _all_perturb(data)
    n = len(samples)
    coords_only = [s for s in samples if not build_jsonl.sample_has_video(s)]
    expected = sum(1 for k in range(n) if k % 3 == 2)
    assert len(coords_only) == expected
    assert 0 < len(coords_only) < n  # video 양식이 다수(2/3) 유지.
    assert data["_meta"]["perturb_coords_only_count"] == len(coords_only)


def test_subsample_first_perturbation_visible_in_user_frames():
    """Test F — 모든 perturb 샘플에서 user 표시 frames 와 원좌표 frames 가 최소 1개
    셀에서 상이 (표시 프레임 내 교란 보장 — 순수 항등 echo 샘플 0). frame 라벨은
    원본 영상 프레임 번호이며 user 행과 corrected_coords 행이 일치한다."""
    data = _build(perturb_loader=_perturb_loader_long,
                  include_perturb=True, distill_loader=None, shadow_loader=None)
    samples = _all_perturb(data)
    assert samples, "perturb 샘플 부재"
    for s in samples:
        report = build_jsonl.assistant_report(s)
        orig_frames = report["corrected_coords"]
        user_frames = _parse_user_frames(_user_text(s))
        user_labels = [r["frame"] for r in user_frames]
        orig_labels = [r["frame"] for r in orig_frames]
        assert user_labels == orig_labels  # frame 라벨 집합 일치 계약.
        assert max(user_labels) > 63  # 라벨 = 원본 영상 프레임 번호 (배열 인덱스 아님).
        assert user_frames != orig_frames, "표시 프레임 내 교란 0 (순수 항등 echo)"


def test_stage_cycle_weighted_displacement(monkeypatch):
    """Test G — stage 배분이 _STAGE_CYCLE=(1,1,2,3) 결정적 cycle 을 따른다."""
    seen: list[int] = []
    real = build_jsonl.perturb.perturb_sequence

    def spy(coords, profile, stage, rng, joint_keys=None):
        seen.append(stage)
        return real(coords, profile, stage, rng, joint_keys)

    monkeypatch.setattr(build_jsonl.perturb, "perturb_sequence", spy)
    _build(include_perturb=True, distill_loader=None, shadow_loader=None)
    assert tuple(build_jsonl._STAGE_CYCLE) == (1, 1, 2, 3)
    assert len(seen) >= 4  # fixture eligible 4행 — cycle 전체 관측.
    cycle = build_jsonl._STAGE_CYCLE
    assert seen == [cycle[k % len(cycle)] for k in range(len(seen))]


def test_perturb_corrected_coords_full_frame_rows():
    """Test H — perturb corrected_coords = 표시 프레임 전체 행 (D6: 부분 방출 채택
    안 함 — cherry-picking 뒷문 차단). distill cc=None 계약은 기존 테스트가 고정."""
    data = _build(perturb_loader=_perturb_loader_long,
                  include_perturb=True, distill_loader=None, shadow_loader=None)
    n_expected = len(schema.select_frame_indices(130))
    for s in _all_perturb(data):
        report = build_jsonl.assistant_report(s)
        cc = report["corrected_coords"]
        assert cc
        assert len(cc) == n_expected  # 행 수 == len(idxs) — 전체 프레임 echo.


def test_hash_split_form_agnostic():
    """Test I — video_hash split 이 양식(좌표전용/video) 무관하게 동작 (leakage 0)."""
    data = _build(val_frac=0.75, include_perturb=True,
                  distill_loader=None, shadow_loader=None)  # 좌표전용 hash 를 val 에 배치.
    by_hash: dict = {}
    for name, samples in (("train", data["train"]), ("val", data["val"] or [])):
        for s in samples:
            vh = s.get("_video_hash")
            if vh:
                by_hash.setdefault(vh, set()).add(name)
    assert all(len(v) == 1 for v in by_hash.values()), by_hash
    # 좌표전용 샘플이 val 에 존재 — 양식 무관 split 실증.
    assert any(s.get("_coords_only") for s in data["val"] or [])
