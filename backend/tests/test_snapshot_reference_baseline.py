"""snapshot_reference_baseline — legacy 무접촉 증명의 해시 · diff · 오프라인 규약 (38-09 R10, 38-14 T2 소비처)."""

from __future__ import annotations

import copy
import json
import os

import pytest

import snapshot_reference_baseline as snap


def _ref_doc(angles=None, **extra):
    doc = {
        "motionId": "ref-kip-up",
        "angles": [10.0, 20.5, 30.25, 0.0] if angles is None else angles,
        "anglesJointKeys": ["left_elbow", "right_elbow"],
        "anglesFrames": 2,
        "anglesUpdatedAt": 1750000000000,
        "clipRange": [0.0, 3.5],
        "isActive": True,
        "updatedAt": 1750000000001,
    }
    doc.update(extra)
    return doc


def _snapshot():
    return {
        "source": snap.SOURCE_LABEL,
        "bucket": "sunity-motion-pilot-videos",
        "takenAtMs": 1,
        "references": {
            "ref-kip-up": snap.summarize_reference_doc(_ref_doc()),
            "ref-climb": snap.summarize_reference_doc(_ref_doc(angles=[1.0, 2.0])),
        },
        "s3ReferenceObjects": [
            {"Key": "reference/ref-kip-up.mp4", "ETag": '"abc"', "Size": 2300000},
        ],
        "regressionSamples": [
            {"uid": "u1", "analysisId": "a1", **snap.summarize_analysis_doc({"status": "done", "mode": "mode1"})},
        ],
    }


def test_canonical_doc_hash_ignores_key_order_but_not_values():
    a = {"x": 1, "y": [1, 2]}
    b = {"y": [1, 2], "x": 1}
    assert snap.canonical_doc_hash(a) == snap.canonical_doc_hash(b)
    assert snap.canonical_doc_hash(a) != snap.canonical_doc_hash({"x": 1, "y": [2, 1]})
    assert snap.canonical_doc_hash(None) is None


def test_diff_identical_snapshots_is_empty():
    before = _snapshot()
    after = copy.deepcopy(before)
    after["takenAtMs"] = 999  # 찍은 시각은 비교 대상이 아니다
    assert snap.diff_snapshots(before, after) == []


def test_diff_reports_changed_angles_hash_field():
    before = _snapshot()
    after = copy.deepcopy(before)
    after["references"]["ref-kip-up"] = snap.summarize_reference_doc(_ref_doc(angles=[10.0, 20.5, 30.25, 0.01]))
    lines = snap.diff_snapshots(before, after)
    assert any("references[ref-kip-up] anglesSha256" in line for line in lines)
    assert any("references[ref-kip-up] docSha256" in line for line in lines)
    assert not any("ref-climb" in line for line in lines)


def test_diff_reports_missing_doc_and_missing_s3_key():
    before = _snapshot()
    after = copy.deepcopy(before)
    del after["references"]["ref-climb"]
    after["s3ReferenceObjects"] = []
    lines = snap.diff_snapshots(before, after)
    assert "references[ref-climb]: missing in after" in lines
    assert "s3[reference/ref-kip-up.mp4]: missing in after" in lines


def test_summarize_reference_doc_keeps_version_pointer_fields_and_absence():
    s = snap.summarize_reference_doc(_ref_doc(activeCandidate="v3"))
    assert s["pointer:activeCandidate"] == "v3"
    assert s["anglesLen"] == 4
    assert snap.summarize_reference_doc(None) == {"exists": False}


def test_pick_regression_samples_first_three_distinct_pairs():
    keys = [
        "results/u1/a1/frame0.jpg",
        "results/u1/a1/frame1.jpg",
        "results/u2/a9/x.mp3",
        "results/other.txt",
        "results/u1/a2/y.json",
        "results/u3/a3/z.json",
    ]
    assert snap.pick_regression_samples(keys) == [("u1", "a1"), ("u2", "a9"), ("u1", "a2")]


def _write(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


def test_offline_same_files_exit_zero(tmp_path, capsys):
    before = _write(tmp_path, "before.json", _snapshot())
    after = _write(tmp_path, "after.json", _snapshot())
    assert snap.main(["--diff", before, "--out", os.devnull, "--offline", after]) == 0
    assert "differences: 0" in capsys.readouterr().out


def test_offline_changed_field_exit_one_with_diff_line(tmp_path, capsys):
    changed = _snapshot()
    changed["references"]["ref-kip-up"]["anglesSha256"] = "0" * 64
    before = _write(tmp_path, "before.json", _snapshot())
    after = _write(tmp_path, "after.json", changed)
    assert snap.main(["--diff", before, "--out", os.devnull, "--offline", after]) == 1
    out = capsys.readouterr().out
    assert "anglesSha256" in out
    assert "differences: 1" in out


def test_offline_never_touches_firestore_or_aws(tmp_path, monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("offline must not read")

    import boto3

    monkeypatch.setattr(snap.firestore_admin, "get_reference_registration", _boom)
    monkeypatch.setattr(snap.firestore_admin, "get_analysis", _boom)
    monkeypatch.setattr(snap.firestore_admin, "_db", _boom)
    monkeypatch.setattr(boto3, "client", _boom)
    before = _write(tmp_path, "before.json", _snapshot())
    after = _write(tmp_path, "after.json", _snapshot())
    assert snap.main(["--diff", before, "--out", os.devnull, "--offline", after]) == 0


def test_offline_without_diff_is_rejected():
    with pytest.raises(SystemExit):
        snap.main(["--out", os.devnull, "--offline", "x.json"])
