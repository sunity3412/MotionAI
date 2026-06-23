"""Phase 23-03 Task 2 — mandatory behavioral test for assert_stillframe_veto_gate.py.

grep/AST(단어 존재·sys.exit 존재)만으론 terminal gate 로 약하다 — precomputed bool 신뢰·
`"true"` 문자열·missing row·hash mismatch·kip-up major≤50·post-result freeze·unknown arm 오통과를
다 통과시킬 수 있다 (D-16 MED-2 + D-17). 따라서 본 테스트는 assert 스크립트를 **실제 subprocess
실행해 exit code 를 assert** 한다. 각 fixture 는 최소 result JSON(cases[].arms) + manifest
(regression_pairs/gate_policy/required_arms) + lock 을 임시 git repo 에 생성한다.

필수 fixture (각 정확한 exit code):
  ① valid 최소 → exit 0
  ② manifest hash mismatch → non-zero
  ③ missing row → non-zero
  ④ extra unmanifested row → non-zero
  ⑤ bool 자리 `"true"` 문자열 → non-zero
  ⑥ non-budget-stress row 의 resource_limited → non-zero
  ⑦ kip-up severity=major, score=50 → non-zero (severity 오분류)
  ⑧ kip-up severity=moderate, score=80 → non-zero (cap 적용 실패)
  ⑨ EVAL18 pair fault>=success → regression count↑ non-zero
  ⑩ lock_git_commit ∉ ancestor(result.run_git_commit) → non-zero (D-17 HIGH-1)
  ⑪ worktree_dirty_at_run==true → non-zero (D-17 HIGH-1)
  ⑫ case 에 required arm 결측 → non-zero (D-17 HIGH-2)
  ⑬ unknown arm 존재 → non-zero (D-17 HIGH-2)
  ⑭ manifest unknown fault_kind → non-zero (D-17 MED-3)
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]  # backend/
_GATE = _REPO_ROOT / "research" / "spikes" / "assert_stillframe_veto_gate.py"


# ─────────────────────────── git temp-repo helpers ───────────────────────────


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def _init_repo(repo: Path) -> tuple[str, str, str]:
    """3 commit 체인 (A=lock, B=run, C=head). 반환: (commit_a, commit_b, commit_c)."""
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.com")
    _git(repo, "config", "user.name", "t")
    (repo / "a.txt").write_text("a")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "A")
    commit_a = _git(repo, "rev-parse", "HEAD")
    (repo / "b.txt").write_text("b")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-q", "-m", "B")
    commit_b = _git(repo, "rev-parse", "HEAD")
    (repo / "c.txt").write_text("c")
    _git(repo, "add", "c.txt")
    _git(repo, "commit", "-q", "-m", "C")
    commit_c = _git(repo, "rev-parse", "HEAD")
    return commit_a, commit_b, commit_c


# ─────────────────────────── canonical valid fixtures ───────────────────────────


def _faultkey(side: str, keypoint_set: str, fault_kind: str) -> dict:
    return {
        "part_scope": "upper_body",
        "side": side,
        "keypoint_set": keypoint_set,
        "fault_kind": fault_kind,
    }


_KIPUP_RECALL = [
    _faultkey("left", "arm", "pole_gap_or_bent"),
    _faultkey("right", "arm", "pole_gap_or_bent"),
    _faultkey("unknown", "head_neck", "extension_or_alignment"),
]


def _arm(**over) -> dict:
    base = {
        "arm": "production_still",
        "cache_namespace": "ns",
        "run_id": "rid",
        "call_count": 1,
        "upload_count": 2,
        "duration_ms": 1000,
        "cacheKey": "k-prod",
        "cacheHit": False,
        "recall_set": [],
        "alignment_status": "none",
        "samplingComplete": True,
        "final_score": 100,
        "severity": None,
    }
    base.update(over)
    return base


def _base_arm(**over) -> dict:
    a = _arm(arm="whole_video_baseline", cacheKey="k-base")
    a.update(over)
    return a


def _clean_row(row_id: str, case_class: str, *, abstention_allowed=False,
               min_score=0, allowed=None) -> dict:
    return {
        "row_id": row_id,
        "case_class": case_class,
        "expected_bucket": "must_stay_high" if case_class == "elite_clean" else "evaluable_non_fault",
        "allowed_veto_statuses": allowed or ["none", "not_applicable"],
        "expected_severity": "none",
        "max_score": 100,
        "min_score": min_score,
        "abstention_allowed": abstention_allowed,
        "budget_stress": False,
        "alignment_unverifiable": False,
        "required_arms": ["production_still", "whole_video_baseline"],
        "optional_arms": [],
        "expected_recall_keys": [],
    }


def _kipup_row() -> dict:
    return {
        "row_id": "eval18-kip-up-fault",
        "case_class": "known_fault",
        "expected_bucket": "must_drop",
        "allowed_veto_statuses": ["applied"],
        "expected_severity": "moderate",
        "max_score": 75,
        "min_score": 0,
        "abstention_allowed": False,
        "budget_stress": False,
        "alignment_unverifiable": False,
        "required_arms": ["production_still", "whole_video_baseline"],
        "optional_arms": [],
        "expected_recall_keys": copy.deepcopy(_KIPUP_RECALL),
    }


def _pair_rows() -> list:
    """EVAL18 1쌍 (fault/success) — power-spin 만 최소 구성."""
    fault = {
        "row_id": "eval18-power-spin-fault", "case_class": "known_fault",
        "expected_bucket": "must_drop", "allowed_veto_statuses": ["applied", "not_applicable"],
        "expected_severity": "moderate", "max_score": 100, "min_score": 0,
        "abstention_allowed": False, "budget_stress": False, "alignment_unverifiable": False,
        "required_arms": ["production_still", "whole_video_baseline"], "optional_arms": [],
        "expected_recall_keys": [],
    }
    success = _clean_row("eval18-power-spin-success", "elite_clean", min_score=95,
                         allowed=["none", "not_applicable"])
    return [fault, success]


def _make_manifest() -> dict:
    rows = [
        _kipup_row(),
        _clean_row("elite-clean", "elite_clean", min_score=95),
        _clean_row("imperfect-clean", "imperfect_clean"),
        _clean_row("occluded-clean", "occluded"),
        _clean_row("spinning-clean", "spinning"),
        _clean_row("tempo-clean", "tempo_shifted", abstention_allowed=True,
                   allowed=["none", "not_applicable", "low_alignment_confidence"]),
        *_pair_rows(),
    ]
    return {
        "gate_policy": {
            "clean_coverage_min": 4,
            "clean_gate_case_classes": ["elite_clean", "imperfect_clean", "occluded", "spinning"],
            "alignment_abstention_case_classes": ["tempo_shifted"],
            "known_fault_case_classes": ["known_fault"],
            "required_arms": ["production_still", "whole_video_baseline"],
        },
        "regression_pairs": [
            {"pair_id": "eval18-power-spin", "fault_row_id": "eval18-power-spin-fault",
             "success_row_id": "eval18-power-spin-success", "min_margin": 1},
        ],
        "rows": rows,
    }


def _make_result(commit_run: str) -> dict:
    """valid result — kip-up applied moderate 75, clean 4개 true_negative, EVAL18 margin>0."""
    cases = [
        {"row_id": "eval18-kip-up-fault", "arms": {
            "production_still": _arm(alignment_status="applied", severity="moderate",
                                     final_score=75, recall_set=copy.deepcopy(_KIPUP_RECALL)),
            "whole_video_baseline": _base_arm(alignment_status="none", final_score=100, recall_set=[]),
        }},
        {"row_id": "elite-clean", "arms": {
            "production_still": _arm(alignment_status="none", final_score=100),
            "whole_video_baseline": _base_arm(alignment_status="none", final_score=100),
        }},
        {"row_id": "imperfect-clean", "arms": {
            "production_still": _arm(alignment_status="none", final_score=90),
            "whole_video_baseline": _base_arm(alignment_status="none", final_score=90),
        }},
        {"row_id": "occluded-clean", "arms": {
            "production_still": _arm(alignment_status="not_applicable", final_score=88),
            "whole_video_baseline": _base_arm(alignment_status="none", final_score=88),
        }},
        {"row_id": "spinning-clean", "arms": {
            "production_still": _arm(alignment_status="none", final_score=92),
            "whole_video_baseline": _base_arm(alignment_status="none", final_score=92),
        }},
        {"row_id": "tempo-clean", "arms": {
            "production_still": _arm(alignment_status="low_alignment_confidence", final_score=90),
            "whole_video_baseline": _base_arm(alignment_status="none", final_score=90),
        }},
        {"row_id": "eval18-power-spin-fault", "arms": {
            "production_still": _arm(alignment_status="applied", severity="moderate", final_score=72),
            "whole_video_baseline": _base_arm(alignment_status="none", final_score=100),
        }},
        {"row_id": "eval18-power-spin-success", "arms": {
            "production_still": _arm(alignment_status="none", final_score=100),
            "whole_video_baseline": _base_arm(alignment_status="none", final_score=100),
        }},
    ]
    return {
        "run_git_commit": commit_run,
        "worktree_dirty_at_run": False,
        "manifest_lock_git_commit": None,  # _write 가 채움.
        "manifest_sha256": None,           # _write 가 채움.
        "eval_command": ["eval"],
        "result_generated_at": "2026-06-23T00:00:00Z",
        "model": "gemini-3.1-pro-preview",
        "cases": cases,
        "false_positive_count": 0,
        "clean_applied_fault_count": 0,
        "clean_true_negative_count": 4,
        "clean_abstention_count": 1,
        "resource_incomplete_count": 0,
        "clean_evaluable_count": 4,
        "completion_pass": True,
        "coverage_pass": True,
        "eval18_discrimination_regression_count": 0,
        "eval18_pair_margins": [{"pair_id": "eval18-power-spin", "margin": 28}],
    }


def _write_fixture(tmp_path: Path, manifest: dict, result: dict,
                   commit_lock: str) -> tuple[Path, Path, Path]:
    """manifest/lock/result 를 디스크에 쓰고, sha/lock_commit 정합을 맞춘다."""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    lock = {
        "manifest_sha256": sha,
        "lock_git_commit": commit_lock,
        "dirty_worktree": False,
        "created_at": "2026-06-23T00:00:00Z",
        "row_ids": [r["row_id"] for r in manifest["rows"]],
        "expected_policy": {
            r["row_id"]: {
                f: r.get(f) for f in (
                    "expected_bucket", "allowed_veto_statuses", "expected_severity",
                    "max_score", "min_score", "abstention_allowed", "budget_stress",
                    "alignment_unverifiable", "required_arms", "optional_arms",
                    "expected_recall_keys",
                )
            }
            for r in manifest["rows"]
        },
        "regression_pairs": manifest.get("regression_pairs"),
        "gate_policy": manifest.get("gate_policy"),
    }
    lock_path = tmp_path / "manifest.lock.json"
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")

    # result 의 lock 정합 필드 채움.
    result = copy.deepcopy(result)
    result["manifest_lock_git_commit"] = commit_lock
    result["manifest_sha256"] = sha
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result_path, manifest_path, lock_path


def _run_gate(result_path: Path, manifest_path: Path, lock_path: Path,
              head: str, repo: Path) -> int:
    # cwd=repo 로 실행 — assert 의 git merge-base/--is-ancestor 가 temp 커밋 체인을
    # 해소하게 한다 (A=lock, B=run, C=head 가 이 repo 에만 존재).
    proc = subprocess.run(
        [sys.executable, str(_GATE),
         "--results", str(result_path),
         "--manifest", str(manifest_path),
         "--lock", str(lock_path),
         "--head", head],
        capture_output=True, text=True, cwd=str(repo),
    )
    return proc.returncode


@pytest.fixture
def gate_env(tmp_path):
    """temp git repo + commit chain (A=lock, B=run, C=head)."""
    repo = tmp_path / "repo"
    commit_a, commit_b, commit_c = _init_repo(repo)
    return {
        "tmp_path": tmp_path, "repo": repo,
        "lock": commit_a, "run": commit_b, "head": commit_c,
    }


# ─────────────────────────── ① valid → exit 0 ───────────────────────────


def test_valid_minimal_passes(gate_env):
    manifest = _make_manifest()
    result = _make_result(gate_env["run"])
    rp, mp, lp = _write_fixture(gate_env["tmp_path"], manifest, result, gate_env["lock"])
    assert _run_gate(rp, mp, lp, gate_env["head"], gate_env["repo"]) == 0


# ─────────────────────────── ② hash mismatch → non-zero ─────────────────────


def test_manifest_hash_mismatch_fails(gate_env):
    manifest = _make_manifest()
    result = _make_result(gate_env["run"])
    rp, mp, lp = _write_fixture(gate_env["tmp_path"], manifest, result, gate_env["lock"])
    # manifest 파일을 freeze 이후 변조 (sha 불일치).
    m = json.loads(mp.read_text())
    m["_meta"] = {"tamper": True}
    mp.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    assert _run_gate(rp, mp, lp, gate_env["head"], gate_env["repo"]) != 0


# ─────────────────────────── ③ missing row → non-zero ───────────────────────


def test_missing_row_fails(gate_env):
    manifest = _make_manifest()
    result = _make_result(gate_env["run"])
    # result.cases 에서 한 row 제거 (manifest 에는 존재).
    result["cases"] = [c for c in result["cases"] if c["row_id"] != "spinning-clean"]
    rp, mp, lp = _write_fixture(gate_env["tmp_path"], manifest, result, gate_env["lock"])
    assert _run_gate(rp, mp, lp, gate_env["head"], gate_env["repo"]) != 0


# ─────────────────────────── ④ extra row → non-zero ─────────────────────────


def test_extra_unmanifested_row_fails(gate_env):
    manifest = _make_manifest()
    result = _make_result(gate_env["run"])
    result["cases"].append({"row_id": "ghost-row", "arms": {
        "production_still": _arm(), "whole_video_baseline": _base_arm(),
    }})
    rp, mp, lp = _write_fixture(gate_env["tmp_path"], manifest, result, gate_env["lock"])
    assert _run_gate(rp, mp, lp, gate_env["head"], gate_env["repo"]) != 0


# ─────────────────────────── ⑤ "true" string-bool → non-zero ────────────────


def test_string_bool_fails(gate_env):
    manifest = _make_manifest()
    result = _make_result(gate_env["run"])
    # worktree_dirty_at_run 을 문자열 "true" 로 (bool 아님).
    result["worktree_dirty_at_run"] = "true"
    rp, mp, lp = _write_fixture(gate_env["tmp_path"], manifest, result, gate_env["lock"])
    assert _run_gate(rp, mp, lp, gate_env["head"], gate_env["repo"]) != 0


# ─────────────────────────── ⑥ non-budget resource_limited → non-zero ───────


def test_non_budget_resource_limited_fails(gate_env):
    manifest = _make_manifest()
    result = _make_result(gate_env["run"])
    for c in result["cases"]:
        if c["row_id"] == "imperfect-clean":
            c["arms"]["production_still"]["alignment_status"] = "resource_limited"
            c["arms"]["production_still"]["samplingComplete"] = False
    # status 화이트리스트 우회를 위해 manifest allowed 에 추가했더라도 completion 이 잡아야 함.
    # 여기서는 화이트리스트가 먼저 잡힐 수도 있으나 어느 쪽이든 non-zero 면 OK.
    rp, mp, lp = _write_fixture(gate_env["tmp_path"], manifest, result, gate_env["lock"])
    assert _run_gate(rp, mp, lp, gate_env["head"], gate_env["repo"]) != 0


# ─────────────────────────── ⑦ kip-up major+50 → non-zero (severity 오분류) ──


def test_kipup_major_50_fails(gate_env):
    manifest = _make_manifest()
    result = _make_result(gate_env["run"])
    for c in result["cases"]:
        if c["row_id"] == "eval18-kip-up-fault":
            c["arms"]["production_still"]["severity"] = "major"
            c["arms"]["production_still"]["final_score"] = 50
    rp, mp, lp = _write_fixture(gate_env["tmp_path"], manifest, result, gate_env["lock"])
    assert _run_gate(rp, mp, lp, gate_env["head"], gate_env["repo"]) != 0


# ─────────────────────────── ⑧ kip-up moderate+80 → non-zero (cap 실패) ──────


def test_kipup_moderate_80_fails(gate_env):
    manifest = _make_manifest()
    result = _make_result(gate_env["run"])
    for c in result["cases"]:
        if c["row_id"] == "eval18-kip-up-fault":
            c["arms"]["production_still"]["severity"] = "moderate"
            c["arms"]["production_still"]["final_score"] = 80
    rp, mp, lp = _write_fixture(gate_env["tmp_path"], manifest, result, gate_env["lock"])
    assert _run_gate(rp, mp, lp, gate_env["head"], gate_env["repo"]) != 0


# ─────────────────────────── ⑨ EVAL18 fault>=success → non-zero ─────────────


def test_eval18_regression_fails(gate_env):
    manifest = _make_manifest()
    result = _make_result(gate_env["run"])
    for c in result["cases"]:
        if c["row_id"] == "eval18-power-spin-fault":
            c["arms"]["production_still"]["final_score"] = 100  # margin 0.
    result["eval18_discrimination_regression_count"] = 0  # precomputed 거짓말 — 재계산이 잡아야.
    rp, mp, lp = _write_fixture(gate_env["tmp_path"], manifest, result, gate_env["lock"])
    assert _run_gate(rp, mp, lp, gate_env["head"], gate_env["repo"]) != 0


# ─────────────────────────── ⑩ lock ∉ ancestor(run) → non-zero ──────────────


def test_lock_not_ancestor_of_run_fails(gate_env):
    manifest = _make_manifest()
    # run_git_commit = lock (A), lock_git_commit = head (C) — C 는 A 의 ancestor 아님.
    result = _make_result(gate_env["lock"])  # run = A
    rp, mp, lp = _write_fixture(gate_env["tmp_path"], manifest, result, gate_env["head"])  # lock = C
    assert _run_gate(rp, mp, lp, gate_env["head"], gate_env["repo"]) != 0


# ─────────────────────────── ⑪ worktree_dirty_at_run==true → non-zero ───────


def test_worktree_dirty_at_run_fails(gate_env):
    manifest = _make_manifest()
    result = _make_result(gate_env["run"])
    result["worktree_dirty_at_run"] = True
    rp, mp, lp = _write_fixture(gate_env["tmp_path"], manifest, result, gate_env["lock"])
    assert _run_gate(rp, mp, lp, gate_env["head"], gate_env["repo"]) != 0


# ─────────────────────────── ⑫ missing required arm → non-zero ──────────────


def test_missing_required_arm_fails(gate_env):
    manifest = _make_manifest()
    result = _make_result(gate_env["run"])
    for c in result["cases"]:
        if c["row_id"] == "elite-clean":
            del c["arms"]["whole_video_baseline"]  # required arm 결측.
    rp, mp, lp = _write_fixture(gate_env["tmp_path"], manifest, result, gate_env["lock"])
    assert _run_gate(rp, mp, lp, gate_env["head"], gate_env["repo"]) != 0


# ─────────────────────────── ⑬ unknown arm → non-zero ───────────────────────


def test_unknown_arm_fails(gate_env):
    manifest = _make_manifest()
    result = _make_result(gate_env["run"])
    for c in result["cases"]:
        if c["row_id"] == "elite-clean":
            c["arms"]["ghost_arm"] = _arm(arm="ghost_arm")
    rp, mp, lp = _write_fixture(gate_env["tmp_path"], manifest, result, gate_env["lock"])
    assert _run_gate(rp, mp, lp, gate_env["head"], gate_env["repo"]) != 0


# ─────────────────────────── ⑭ manifest unknown fault_kind → non-zero ───────


def test_unknown_fault_kind_fails(gate_env):
    manifest = _make_manifest()
    # kip-up expected_recall_keys 에 unknown fault_kind 주입 (Pod 결과 보기 전 fail).
    for r in manifest["rows"]:
        if r["row_id"] == "eval18-kip-up-fault":
            r["expected_recall_keys"][0]["fault_kind"] = "totally_unknown_kind"
    result = _make_result(gate_env["run"])
    rp, mp, lp = _write_fixture(gate_env["tmp_path"], manifest, result, gate_env["lock"])
    assert _run_gate(rp, mp, lp, gate_env["head"], gate_env["repo"]) != 0
