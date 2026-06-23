"""Phase 23-03 Task 1b — pre-Pod manifest freeze (D-16 HIGH-1/HIGH-2, D-17 MED-1/MED-2).

목적:
  manifest freeze 를 Pod 측정과 **별도 pre-Pod 단계** 로 분리한다. D-15 의 "manifest+lock
  동시 생성" 워크플로는 "결과 본 뒤 relabel→lock→commit" 를 여전히 허용한다(hash 일치는
  '현 manifest=lock' 만 증명할 뿐 '결과 전 freeze' 를 증명 못 함). 따라서 freeze 를 독립
  실행으로 강제한다:

    ① eval_stillframe_veto_manifest.json 작성
    ② commit
    ③ **clean worktree 에서** 이 freeze 실행 (manifest uncommitted/worktree dirty 면 REFUSE)
    ④ eval_stillframe_veto_manifest.lock.json commit
    ⑤ Pod 가 그 commit pull → eval 은 result JSON 만 생성

  assert 는 lock_git_commit 이 result.run_git_commit 의 ancestor 인지 검증해 post-result
  freeze 를 차단한다 (D-17 HIGH-1). 본 스크립트는 lock 의 출처(lock_git_commit/sha256/
  expected_policy/regression_pairs/gate_policy) owner 다.

★ stdlib only (D-16 HIGH-2): json / hashlib / subprocess(git) 만. PyYAML 은
  runpod_inference/requirements.txt 에 없어 Pod-terminal assert 가 import 단계에서 죽으면
  안 되므로 manifest 는 JSON, 본 스크립트도 외부 의존 0.

★ created_at 은 주입 (--created-at) — 벽시계 직접 호출(현재시각 함수) 금지 (결정론·재현성).

★ 임계/프롬프트 주입 0 (D-06): freeze 는 라벨을 읽어 박제만 한다(생성·변경 아님).

호출 (고정):
  cd backend && python3 research/spikes/freeze_stillframe_veto_manifest.py \\
    --manifest research/spikes/eval_stillframe_veto_manifest.json \\
    --created-at 2026-06-23T00:00:00Z \\
    [--lock research/spikes/eval_stillframe_veto_manifest.lock.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("freeze_stillframe_veto_manifest")

# expected_policy 에 박제할 row 필드 (freeze 가 읽어 snapshot — 변경·생성 0).
_EXPECTED_POLICY_FIELDS = (
    "expected_bucket",
    "allowed_veto_statuses",
    "expected_severity",
    "max_score",
    "min_score",
    "abstention_allowed",
    "budget_stress",
    "alignment_unverifiable",
    "required_arms",
    "optional_arms",
    "expected_recall_keys",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _worktree_dirty(manifest_rel: str) -> tuple[bool, bool]:
    """git status --porcelain → (worktree_dirty, manifest_uncommitted).

    manifest 가 modified/staged/untracked 면 manifest_uncommitted=True.
    그 외 어떤 변경이라도 있으면 worktree_dirty=True.
    """
    out = _git("status", "--porcelain")
    dirty = False
    manifest_uncommitted = False
    norm_manifest = os.path.normpath(manifest_rel)
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        dirty = True
        if os.path.normpath(path) == norm_manifest:
            manifest_uncommitted = True
    return dirty, manifest_uncommitted


def build_lock(manifest_path: str, created_at: str) -> dict:
    """manifest.json 을 읽어 lock dict 를 구성 (snapshot only — 생성·변경 0)."""
    raw = Path(manifest_path).read_bytes()
    manifest_sha256 = hashlib.sha256(raw).hexdigest()
    manifest = json.loads(raw.decode("utf-8"))

    rows = manifest.get("rows") or []
    row_ids = [r["row_id"] for r in rows]

    expected_policy = {}
    for row in rows:
        expected_policy[row["row_id"]] = {
            field: row.get(field) for field in _EXPECTED_POLICY_FIELDS
        }

    lock_git_commit = _git("rev-parse", "HEAD")

    return {
        "manifest_sha256": manifest_sha256,
        "lock_git_commit": lock_git_commit,
        "dirty_worktree": False,  # (1) 에서 dirty 면 이미 거부됨.
        "created_at": created_at,
        "row_ids": row_ids,
        "expected_policy": expected_policy,
        # D-17 MED-1/MED-2 — manifest top-level policy snapshot.
        "regression_pairs": manifest.get("regression_pairs"),
        "gate_policy": manifest.get("gate_policy"),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Phase 23-03 pre-Pod manifest freeze (lock.json 생성)"
    )
    p.add_argument("--manifest", required=True, help="frozen manifest.json 경로")
    p.add_argument(
        "--created-at", required=True,
        help="lock created_at (ISO8601, 주입 — 벽시계 현재시각 함수 직접 호출 금지)",
    )
    p.add_argument(
        "--lock", default=None,
        help="lock.json 출력 경로 (기본: manifest 의 .lock.json)",
    )
    args = p.parse_args(argv)

    manifest_path = args.manifest
    if not os.path.isfile(manifest_path):
        log.error("manifest 파일 없음: %s", manifest_path)
        return 2

    lock_path = args.lock or manifest_path.replace(".json", ".lock.json")

    # (1) clean-worktree 강제 (REFUSE on dirty/uncommitted, D-16 HIGH-1).
    #     manifest 는 commit 된 상태에서만 freeze — '결과 전 freeze' 시간순을 보장한다.
    dirty, manifest_uncommitted = _worktree_dirty(manifest_path)
    if manifest_uncommitted:
        log.error(
            "REFUSE: manifest 가 uncommitted/modified — 먼저 manifest.json 을 commit 하라 "
            "(freeze 는 commit 된 manifest 에서만). path=%s", manifest_path
        )
        return 3
    if dirty:
        log.error(
            "REFUSE: worktree dirty — clean worktree 에서만 freeze 한다 (post-result relabel "
            "차단, D-16 HIGH-1). `git status` 확인."
        )
        return 3

    # (2) lock.json emit (snapshot only).
    lock = build_lock(manifest_path, args.created_at)

    out = Path(lock_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(
        "freeze OK → %s (sha256=%s lock_git_commit=%s rows=%d pairs=%d)",
        lock_path, lock["manifest_sha256"][:12], lock["lock_git_commit"][:12],
        len(lock["row_ids"]), len(lock.get("regression_pairs") or []),
    )
    log.info(
        "다음: lock.json 을 commit → Pod 가 그 commit pull → eval 실행 (D-16 HIGH-1 워크플로)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
