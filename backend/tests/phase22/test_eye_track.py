"""build_jsonl eye 트랙 + 기존 3트랙 무회귀 TDD (quick 260814-j24 Task 2).

1급 게이트 = **무회귀**. eye_loader 미주입 시 train/val 샘플 리스트가 기존과 완전
동일해야 하고, 주입 시에도 비-eye 부분과 기존 _meta 키가 값까지 불변이어야 한다.
(test_build_jsonl.py 는 수정하지 않는다 — 그것이 무회귀의 독립 증인이다.)

eye 트랙 불변식:
  · assistant JSON 에 score/severity/overall/points 계열 키 0 (재귀 스캔).
  · track_claim_agrees=false(트랙-눈 불일치) 행이 방출되고 샘플에서 식별 가능.
  · disposition != admit 행은 유입 0 (hold 차단).
  · val motion 과 겹치는 eye 샘플 드롭(leakage 0).
  · _balance_media 트랙 독립 균등 통과.
"""

from __future__ import annotations

import json

import pytest

from datagen import build_jsonl
from datagen import schema

from test_build_jsonl import (  # noqa: E402 - 무회귀 대조는 같은 fixture 로만 성립.
    _distill_loader,
    _manifest,
    _perturb_loader,
    _reference_loader,
    _shadow_loader,
)

_SCORE_MARKERS = ("score", "severity", "overall", "points")


# ---------------------------------------------------------------------------
# fixture — eye 원장 행(harvest_eye EYE_ROW_KEYS 부분집합).
# ---------------------------------------------------------------------------
def _eye_row(eye_id, motion, joint, side="ref", claim="extended", observed="extended",
             agrees=True, disposition="admit", uploaded=False):
    return {
        "eye_id": eye_id,
        "media_sha16": eye_id,
        "media_key": f"training/phase22/eye/{eye_id}.png",
        "motion": motion,
        "joint": joint,
        "side": side,
        "claim": claim,
        "observed": observed,
        "track_claim_agrees": agrees,
        "track_angle_deg": 171.7,
        "confidence": 0.9,
        "reason": "주황 원이 팔꿈치 관절에 있고 팔이 펴져 있다.",
        "sec": 1.2,
        "frame_idx": 18,
        "disposition": disposition,
        "disposition_reason": "internal_seed_ref",
        "uploaded": uploaded,
        "usage": "training-only-no-redistribution",
    }


def _eye_rows():
    return [
        _eye_row("aaaa000000000001", "kip-up", "left_elbow"),
        _eye_row("aaaa000000000002", "kip-up", "right_elbow",
                 claim="bent", observed="extended", agrees=False),
        _eye_row("aaaa000000000003", "split", "left_knee"),
        _eye_row("aaaa000000000004", "split", "right_knee",
                 claim="bent", observed="unclear", agrees=False),
        # hold 행 — 유입 0 이어야 한다.
        _eye_row("aaaa000000000005", "kip-up", "left_hip", side="user",
                 disposition="hold"),
    ]


def _eye_loader(rows=None):
    data = rows if rows is not None else _eye_rows()

    def loader():
        return [r for r in data if r.get("disposition") == "admit" and r.get("motion")]

    return loader


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


def _eye_samples(data):
    return [s for s in data["train"] + (data["val"] or []) if s.get("_track") == "eye"]


def _non_eye(samples):
    return [s for s in samples if s.get("_track") != "eye"]


def _scan_score_keys(obj, found):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(m in str(k).lower() for m in _SCORE_MARKERS):
                found.append(k)
            _scan_score_keys(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _scan_score_keys(v, found)


# ---------------------------------------------------------------------------
# 1급 게이트 — eye_loader 미주입 무회귀.
# ---------------------------------------------------------------------------
def test_eye_loader_absent_leaves_dataset_byte_identical():
    base = _build()
    again = _build(eye_loader=None)
    assert again["train"] == base["train"]
    assert again["val"] == base["val"]
    assert again["_meta"] == base["_meta"]


def test_eye_injection_does_not_disturb_existing_samples():
    base = _build()
    with_eye = _build(eye_loader=_eye_loader())
    assert _non_eye(with_eye["train"]) == base["train"]
    assert _non_eye(with_eye["val"] or []) == (base["val"] or [])


def test_eye_injection_meta_is_additive_only():
    """eye 네임스페이스 밖 _meta 값은 주입 여부와 무관하게 불변(키 집합도 동일)."""
    base = _build()
    with_eye = _build(eye_loader=_eye_loader())
    assert set(with_eye["_meta"]) == set(base["_meta"]), "_meta 키 집합이 주입에 따라 흔들림"
    for key, value in base["_meta"].items():
        if key.startswith("eye_"):
            continue  # eye 네임스페이스 = additive 관측치.
        if key == "track_counts":
            for track, count in value.items():
                if track == "eye":
                    continue
                assert with_eye["_meta"]["track_counts"][track] == count
            continue
        assert with_eye["_meta"][key] == value, f"_meta.{key} 변형 — 무회귀 위반"
    for added in ("eye_admitted_count", "eye_mismatch_count", "eye_media_pending_upload",
                  "eye_leakage_dropped", "eye_observed_counts", "eye_motion_counts",
                  "eye_balance_trimmed"):
        assert added in with_eye["_meta"]
    assert base["_meta"]["track_counts"]["eye"] == 0
    assert with_eye["_meta"]["track_counts"]["eye"] > 0


def test_cap_fault_free_applies_before_eye_join():
    """eye 는 전부 fault-free — 캡 이전에 끼면 기존 distill 행을 밀어낸다."""
    base = _build()
    with_eye = _build(eye_loader=_eye_loader())
    assert with_eye["_meta"]["fault_bearing_count"] == base["_meta"]["fault_bearing_count"]
    assert with_eye["_meta"]["fault_free_count"] == base["_meta"]["fault_free_count"]


def test_text_mix_denominator_excludes_eye():
    base = _build()
    with_eye = _build(eye_loader=_eye_loader())
    n_base = sum(1 for s in base["train"] if s.get("_track") == "text")
    n_eye = sum(1 for s in with_eye["train"] if s.get("_track") == "text")
    assert n_base == n_eye


# ---------------------------------------------------------------------------
# eye 트랙 규격.
# ---------------------------------------------------------------------------
def test_eye_task_keys_are_alphabetical_and_score_free():
    assert build_jsonl.EYE_TASK_KEYS == tuple(sorted(build_jsonl.EYE_TASK_KEYS))
    for key in build_jsonl.EYE_TASK_KEYS:
        assert not any(m in key.lower() for m in _SCORE_MARKERS)
    assert set(build_jsonl.EYE_TASK_KEYS) == {
        "joint", "limb", "observed", "reason", "side", "track_claim", "track_claim_agrees"
    }


def test_eye_schema_carries_limb_so_two_stage_verdict_is_explainable():
    """원장 match 는 (상태 일치 AND 사지 일치) 2단 판정 — limb 없으면 잡음이 된다."""
    rows = [_eye_row("ffff000000000001", "split", "left_knee", claim="bent",
                     observed="bent", agrees=False)]
    rows[0]["limb"] = "arm"  # 무릎 마크가 굽은 '팔' 에 얹힘 = 마크 전위.
    data = _build(eye_loader=_eye_loader(rows))
    samples = _eye_samples(data)
    assert samples
    report = build_jsonl.assistant_report(samples[0])
    assert report["limb"] == "arm"
    assert report["observed"] == report["track_claim"] == "bent"
    assert report["track_claim_agrees"] is False


def test_normalize_eye_report_whitelists_and_fills_null():
    out = build_jsonl.normalize_eye_report(
        {"observed": "bent", "score": 41, "severity": "high", "reason": "r"}
    )
    assert set(out) == set(build_jsonl.EYE_TASK_KEYS)
    assert list(out) == sorted(out)
    assert out["observed"] == "bent" and out["reason"] == "r"
    assert out["joint"] is None and out["side"] is None


def test_eye_sample_assistant_json_has_no_score_keys():
    data = _build(eye_loader=_eye_loader())
    samples = _eye_samples(data)
    assert samples
    for s in samples:
        report = build_jsonl.assistant_report(s)
        assert report is not None
        found: list = []
        _scan_score_keys(report, found)
        assert found == [], f"eye 샘플에 점수 계열 키 유입: {found}"


def test_eye_sample_is_image_reference_not_video():
    data = _build(eye_loader=_eye_loader())
    for s in _eye_samples(data):
        assert build_jsonl.sample_has_video(s) is False
        content = s["messages"][1]["content"]
        images = [c for c in content if c.get("type") == "image"]
        assert len(images) == 1
        assert images[0]["image"].startswith("s3://")
        assert "training/phase22/eye/" in images[0]["image"]


def test_eye_user_message_carries_track_claim_so_agreement_is_learnable():
    data = _build(eye_loader=_eye_loader())
    for s in _eye_samples(data):
        text = " ".join(c.get("text", "") for c in s["messages"][1]["content"])
        report = build_jsonl.assistant_report(s)
        assert report["track_claim"] in text, "track_claim 이 입력에 없으면 agrees 는 학습 불가"
        assert report["joint"] in text


def test_eye_mismatch_rows_survive_and_are_identifiable():
    """트랙-눈 불일치 = keypoint 환각 라벨. 방출되고 샘플에서 식별 가능해야 한다."""
    data = _build(eye_loader=_eye_loader())
    samples = _eye_samples(data)
    mismatched = [s for s in samples if s.get("_eye_agrees") is False]
    assert mismatched, "불일치 행이 전부 사라졌다 — 최고가치 코퍼스 소실"
    for s in mismatched:
        report = build_jsonl.assistant_report(s)
        assert report["track_claim_agrees"] is False
        assert report["track_claim"] != report["observed"]
    assert data["_meta"]["eye_mismatch_count"] == len(mismatched)


def test_hold_rows_never_reach_jsonl():
    rows = _eye_rows()
    loader_all = lambda: rows  # noqa: E731 - fail-closed 를 build 층에서도 확인.
    data = _build(eye_loader=loader_all)
    for s in _eye_samples(data):
        report = build_jsonl.assistant_report(s)
        assert report["side"] != "user" or s.get("_disposition") == "admit"
    keys = [s["messages"][1]["content"][0]["image"] for s in _eye_samples(data)]
    assert not any("aaaa000000000005" in k for k in keys), "hold 행 유입 — 프라이버시 fence 붕괴"


def test_rows_without_motion_are_dropped_by_build_layer():
    rows = [_eye_row("bbbb000000000001", None, "left_elbow")]
    data = _build(eye_loader=lambda: rows)
    assert _eye_samples(data) == []


def test_eye_samples_pass_track_independent_balance_gate():
    # kip-up 은 이 fixture 에서 val motion 이라 leakage 로 빠진다 — 균등만 보려고 회피.
    rows = [_eye_row(f"cccc{i:012d}", "split", "left_elbow") for i in range(9)]
    rows.append(_eye_row("dddd000000000001", "climb", "left_knee"))
    data = _build(eye_loader=_eye_loader(rows))
    counts: dict = {}
    for s in _eye_samples(data):
        counts[s["_motion"]] = counts.get(s["_motion"], 0) + 1
    assert max(counts.values()) <= 2 * min(counts.values())
    # 트림 손실은 은폐되지 않는다(9+1 → cap=2 → 2+1, 7건 트림).
    assert data["_meta"]["eye_leakage_dropped"] == 0
    assert data["_meta"]["eye_balance_trimmed"] == 10 - sum(counts.values()) == 7


def test_eye_leakage_dropped_when_motion_is_in_val():
    data = _build(eye_loader=_eye_loader())
    val_motions = {s.get("_motion") for s in (data["val"] or []) if s.get("_motion")}
    for s in _eye_samples(data):
        assert s["_motion"] not in val_motions
    assert data["_meta"]["eye_leakage_dropped"] >= 0
    if val_motions:
        assert data["_meta"]["eye_leakage_dropped"] > 0


def test_eye_samples_are_train_only_no_video_hash():
    data = _build(eye_loader=_eye_loader())
    for s in _eye_samples(data):
        assert s.get("_video_hash") is None
        assert s.get("_has_faults") is False
    assert all(s.get("_track") != "eye" for s in (data["val"] or []))


def test_eye_media_pending_upload_counter_is_exposed():
    data = _build(eye_loader=_eye_loader())
    assert data["_meta"]["eye_media_pending_upload"] == data["_meta"]["track_counts"]["eye"]
    uploaded_rows = [dict(r, uploaded=True) for r in _eye_rows()]
    data2 = _build(eye_loader=_eye_loader(uploaded_rows))
    assert data2["_meta"]["eye_media_pending_upload"] == 0


def test_eye_system_prompt_is_shared_constant_not_adhoc():
    data = _build(eye_loader=_eye_loader())
    systems = {s["messages"][0]["content"] for s in _eye_samples(data)}
    assert systems == {build_jsonl._EYE_SYSTEM}


# ---------------------------------------------------------------------------
# full_batch 배선 — make_eye_loader fail-closed + 업로드 게이트.
# ---------------------------------------------------------------------------
def test_make_eye_loader_emits_only_admit_rows_with_motion(tmp_path):
    from distill import full_batch

    path = tmp_path / "eye_manifest.json"
    path.write_text(json.dumps({"_meta": {}, "rows": _eye_rows() + [
        _eye_row("eeee000000000001", None, "left_hip"),
    ]}, ensure_ascii=False), encoding="utf-8")
    rows = full_batch.make_eye_loader(str(path))()
    assert {r["eye_id"] for r in rows} == {
        "aaaa000000000001", "aaaa000000000002", "aaaa000000000003", "aaaa000000000004"
    }


def test_make_eye_loader_missing_manifest_is_empty_not_crash(tmp_path):
    from distill import full_batch

    assert full_batch.make_eye_loader(str(tmp_path / "nope.json"))() == []


def test_assemble_blocks_upload_while_crops_pending(tmp_path):
    """크롭 S3 업로드 전 canonical 업로드 차단(T-j24-06 fail-closed)."""
    from distill import full_batch

    accepted = tmp_path / "accepted"
    accepted.mkdir()
    uploaded: list = []
    with pytest.raises(SystemExit) as exc:
        full_batch.assemble_jsonl(
            _manifest(), str(accepted), str(tmp_path / "out"),
            eye_loader=_eye_loader(),
            uploader=lambda local, key: uploaded.append(key),
        )
    assert "eye" in str(exc.value).lower()
    assert uploaded == [], "차단 전에 업로드가 새어나갔다"


def test_assemble_local_only_emits_eye_rows(tmp_path):
    from distill import full_batch

    accepted = tmp_path / "accepted"
    accepted.mkdir()
    out = tmp_path / "out"
    result = full_batch.assemble_jsonl(
        _manifest(), str(accepted), str(out), eye_loader=_eye_loader()
    )
    assert result["uploaded"] == []
    lines = [json.loads(l) for l in (out / "train.jsonl").read_text(encoding="utf-8").splitlines()]
    eye = [s for s in lines if s.get("_track") == "eye"]
    assert eye, "로컬 조립에서 eye 행이 나오지 않았다"
    assert result["meta"]["track_counts"]["eye"] == len(eye)


def test_assemble_without_eye_loader_is_unchanged(tmp_path):
    from distill import full_batch

    accepted = tmp_path / "accepted"
    accepted.mkdir()
    a = full_batch.assemble_jsonl(_manifest(), str(accepted), str(tmp_path / "a"))
    b = full_batch.assemble_jsonl(
        _manifest(), str(accepted), str(tmp_path / "b"), eye_loader=None
    )
    assert (tmp_path / "a" / "train.jsonl").read_text(encoding="utf-8") == (
        tmp_path / "b" / "train.jsonl"
    ).read_text(encoding="utf-8")
    assert a["meta"] == b["meta"]


# ---------------------------------------------------------------------------
# 사이클 배선 — assemble 스테이지가 eye 트랙을 태울 수 있다.
# ---------------------------------------------------------------------------
def test_retrain_cycle_assemble_stage_carries_with_eye():
    from pathlib import Path as _P

    script = _P(__file__).resolve().parents[2] / "training" / "sft" / "run_retrain_cycle.sh"
    text = script.read_text(encoding="utf-8")
    assert "--with-eye" in text
    assemble = text.split("assemble()", 1)[1].split("\n}", 1)[0]
    assert "--with-eye" in assemble, "assemble 스테이지 밖에 붙었다"


def test_schema_report_keys_untouched_by_eye_track():
    """eye 는 자체 6키 스키마 — D-01 REPORT_KEYS 를 오염시키지 않는다."""
    assert "track_claim" not in schema.REPORT_KEYS
    assert set(build_jsonl.EYE_TASK_KEYS).isdisjoint(set(schema.REPORT_KEYS))
