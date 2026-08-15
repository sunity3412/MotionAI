"""22-12 승격 래칫 — D-15 게이트 판정을 단방향 승격 원장으로 변환하는 단일 owner.

래칫 원칙 (박제): 게이트 PASS(assert_gates --require-pass exit 0)만 current 를
전진시킨다. FAIL 은 attempt 로 기록만 — 서빙/swap(22-08~10 소관)은 current 포인터만
신뢰한다. 미승격(FAIL) 모델이 current 가 되는 경로는 존재하지 않는다(단조성).

객관성 hard gate([[analysis-objectivity-no-human-scores]]): 원장/리포트에는 게이트
verdict 문자열(PASS/FAIL)과 비용 관측치만 저장한다 — 사람 점수·judge 점수 수치는
저장 금지(게이트가 이미 그것들을 소비해 verdict 로 응축했다).

순수 로직: parse/make/apply 는 파일·네트워크 I/O 0(boto3/torch import 0). load/save
는 얇은 I/O 껍데기로 분리한다. 셸 러너(run_retrain_cycle.sh)의 promote stage 가
`python3 -m training.sft.promotion --gate-exit N --ckpt ... --stats-json ... --ledger ...
--report-out ...` 로 호출하고, promoted 여부를 exit 0/1 로 받아 분기한다.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LEDGER_SCHEMA = "promotion-ledger-v1"

# make_cycle_report 가 방출하는 reject 분해 필드 ← full_batch.aggregate_stats 키 정합.
_REJECT_KEYS = ("rejected_judge", "rejected_parse", "rejected_contract")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── 순수 로직 ────────────────────────────────────────────────────────────────
def parse_gate_verdict(require_pass_exit_code, gate_results=None) -> dict:
    """require-pass 모드 exit 0 만 pass=True (게이트 PASS 유일 승격 조건).

    gate_results = assert_gates.run_all_checks() 출력 {label: (fails, skips)} (선택) —
    있으면 per-gate PASS/FAIL 로 변환한다(fails 비면 PASS, SKIPPED-only 도 PASS 표기).
    없으면 gates={} 로 반환하고 승격 판정은 exit code 만으로 결정한다.
    """
    passed = int(require_pass_exit_code) == 0
    gates: dict[str, str] = {}
    if gate_results:
        for label, val in gate_results.items():
            fails = val[0] if isinstance(val, (tuple, list)) else val
            gates[label] = "PASS" if not fails else "FAIL"
    return {"pass": passed, "gates": gates, "artifacts": sorted(gates.keys())}


def make_ledger_entry(ckpt_path, verdict, data_snapshot, batch_ids, ts=None) -> dict:
    """승격 원장 entry — promoted 는 verdict.pass 를 그대로 따른다.

    data_snapshot = {train_rows, val_rows, distill, perturb, text} (조립 _meta 파생).
    judge/사람 점수는 저장하지 않는다 — verdict 의 gates 문자열만 근거로 남긴다.
    """
    return {
        "ckpt": ckpt_path,
        "ts": ts or _utc_now_iso(),
        "promoted": bool(verdict.get("pass")),
        "gates": dict(verdict.get("gates") or {}),
        "data": dict(data_snapshot or {}),
        "batch_ids": list(batch_ids or []),
    }


def apply_ratchet(ledger, entry) -> dict:
    """append-only + promoted=True 일 때만 current 전진(단방향 래칫).

    입력 ledger 는 변형하지 않는다(순수 — 기존 entries deep-equal 보존). FAIL entry 는
    entries 에 기록만 되고 current 는 직전 promoted 를 그대로 가리킨다. current 가
    None(초기)인 상태에서 FAIL 만 쌓이면 current 는 None 을 유지한다.
    """
    out = copy.deepcopy(ledger)
    out.setdefault("schema", LEDGER_SCHEMA)
    out.setdefault("entries", [])
    out.setdefault("current", None)
    out["entries"].append(copy.deepcopy(entry))
    if entry.get("promoted"):
        out["current"] = {"ckpt": entry["ckpt"], "ts": entry["ts"]}
    return out


def make_cycle_report(label_stats, sft_wall_seconds, verdict, promoted) -> dict:
    """사이클 비용 관측치 방출 — 은폐 금지, 사람 점수 필드 없음.

    label_stats = full_batch 러너 결과 dict({stats, n_processed, ...}) 또는
    aggregate_stats 그대로. new_labeled = 이번 사이클 신규 처리 행(n_processed), 없으면
    accepted+reject 합으로 근사. est_gemini_calls = new_labeled*2 (교사 1콜 + judge 1콜).
    """
    stats = label_stats.get("stats") if isinstance(label_stats.get("stats"), dict) else label_stats
    stats = stats or {}
    new_labeled = label_stats.get("n_processed")
    if new_labeled is None:
        new_labeled = int(stats.get("accepted", 0)) + sum(
            int(stats.get(k, 0)) for k in _REJECT_KEYS
        )
    new_labeled = int(new_labeled)
    gates = verdict.get("gates") or {"overall": "PASS" if verdict.get("pass") else "FAIL"}
    return {
        "new_labeled": new_labeled,
        "accepted": int(stats.get("accepted", 0)),
        "rejected_judge": int(stats.get("rejected_judge", 0)),
        "rejected_parse": int(stats.get("rejected_parse", 0)),
        "rejected_contract": int(stats.get("rejected_contract", 0)),
        "est_gemini_calls": new_labeled * 2,
        "sft_wall_seconds": sft_wall_seconds,
        "gates": gates,
        "promoted": bool(promoted),
    }


# ── I/O 껍데기 (순수 로직과 분리) ────────────────────────────────────────────
def load_ledger(path) -> dict:
    """원장 로드 — 부재/손상이면 초기 원장({current: null, entries: []})."""
    p = Path(path)
    if not p.exists():
        return {"schema": LEDGER_SCHEMA, "current": None, "entries": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"schema": LEDGER_SCHEMA, "current": None, "entries": []}
    data.setdefault("schema", LEDGER_SCHEMA)
    data.setdefault("current", None)
    data.setdefault("entries", [])
    return data


def save_ledger(path, ledger) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_json(path):
    """부재/빈 파일은 `{}` — 그 밖의 파손은 그대로 터뜨린다.

    ★2026-08-15: 체인을 `train|gates|promote` 로만 돌리면 label 단계 산출물
    (`cycle_label_stats.json`)이 아예 없거나 이전 사이클의 빈 파일로 남아 있다.
    거기서 promote 가 죽으면 **리포트가 통째로 사라져** 사이클 비용 관측치를 잃는다
    (게이트 판정과 무관한 손실). 없는 것은 없는 대로 리포트에 싣고 진행한다.
    반대로 내용이 있는데 파싱이 안 되면 그것은 생산자 버그이므로 숨기지 않는다.
    """
    p = Path(path)
    if not p.exists():
        return {}
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    return json.loads(text)


def _data_snapshot_from_meta(meta) -> dict:
    """조립 _meta.json → data_snapshot(train_rows/val_rows/distill/perturb/text)."""
    if not isinstance(meta, dict):
        return {"train_rows": None, "val_rows": None, "distill": None, "perturb": None, "text": None}
    tracks = meta.get("track_counts") or {}
    return {
        "train_rows": meta.get("train_rows"),
        "val_rows": meta.get("val_rows"),
        "distill": tracks.get("distill"),
        "perturb": tracks.get("perturb"),
        "text": tracks.get("text"),
    }


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="22-12 승격 래칫 — 게이트 판정 → 원장 전진")
    ap.add_argument("--gate-exit", type=int, required=True,
                    help="assert_gates --require-pass exit code (0=PASS 만 승격)")
    ap.add_argument("--ckpt", required=True, help="게이트를 통과 시도한 병합 체크포인트 경로")
    ap.add_argument("--stats-json", required=True, help="full_batch 결과 JSON(라벨 비용 관측치)")
    ap.add_argument("--ledger", required=True, help="promotion_ledger.json 경로")
    ap.add_argument("--report-out", required=True, help="사이클 리포트 출력 JSON 경로")
    ap.add_argument("--meta-json", default=None, help="조립 _meta.json(선택 — data_snapshot 보강)")
    ap.add_argument("--batch-ids", default="", help="소비한 collection_batch id 목록(콤마 구분)")
    ap.add_argument("--sft-wall-seconds", type=float, default=None, help="SFT 학습 wall time(초)")
    args = ap.parse_args(argv)

    label_stats = _load_json(args.stats_json)
    meta = _load_json(args.meta_json) if args.meta_json else None
    batch_ids = [b for b in (x.strip() for x in args.batch_ids.split(",")) if b]

    verdict = parse_gate_verdict(args.gate_exit)
    entry = make_ledger_entry(
        args.ckpt, verdict, _data_snapshot_from_meta(meta), batch_ids
    )
    ledger = apply_ratchet(load_ledger(args.ledger), entry)
    save_ledger(args.ledger, ledger)

    report = make_cycle_report(
        label_stats, args.sft_wall_seconds, verdict, entry["promoted"]
    )
    Path(args.report_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report_out).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if entry["promoted"]:
        print(f"PROMOTED — current -> {args.ckpt} (ledger 커밋 필요: {args.ledger})")
        return 0
    print("NOT PROMOTED — 기존 모델 유지 (attempt 만 기록). 게이트 FAIL 은 다음 처방 근거.")
    return 1


if __name__ == "__main__":  # pragma: no cover - 실 실행은 셸 러너(Pod, belle-gated).
    raise SystemExit(main())
