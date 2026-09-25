#!/usr/bin/env python3
"""평가셋 분리 점검 — 봉인 시험지 영상(과 같은 인물·세션의 클립)이 학습 후보(manifest 증류 대상)에 새는지 (quick-260925-nnt).

근거: 37-DATA-SPEC 규칙 6 "평가 분할은 인물·세션 단위로 — video hash 분리는 같은 인물·같은 세션·다른 인코딩의 누수를 못 막는다",
TRAINING-DUE 게이트 4 "인물·세션 분리 평가셋이 있나". 플라이휠은 manifest 의 s3_key 보유 행을 증류 후보로 자동 선택한다
(gemini_teacher.eligible_for_distill) — 그래서 평가 영상이 manifest 에 있으면 그대로 학습에 들어간다.

무엇을 점검하나
──────────────
  평가 항목 = sealed_tests.jsonl 의 영상(봉인 정답이 있는 것) + pairs.jsonl 로 묶인 짝 + 같은 (subject_id, session) 의 clips.jsonl 클립.
  학습 후보 = manifest.json rows 중 eligible_for_distill 이 True 인 행.
  L1 (오류) 같은 파일: 학습 후보 s3_key == 평가 클립 s3_key
  L2 (오류) 같은 세션: 학습 후보가 clips.jsonl 에 등록된 클립이고 그 (subject, session) 이 평가 그룹
  L3 (경고) 같은 인물: 학습 후보가 평가 인물의 다른 세션(내부 촬영분 — reference/ 는 sub_je 로 본다)
  평가 인물이 1명뿐이면 "인물 분리 불가"를 그대로 적는다 — 게이트 4 는 그때 켜지지 않는다.

사용
────
  backend/.venv/bin/python backend/scripts/eval_split_check.py            # 보고서 stdout + .planning/sealed/EVAL-SPLIT.md, 누수(L1/L2)면 exit 1
  backend/.venv/bin/python backend/scripts/eval_split_check.py --mark-holdout   # L1/L2 행에 holdout="sealed_eval" 표시(증류 제외). belle 결정 뒤에만.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))
sys.path.insert(0, str(REPO / "backend"))
DATA = REPO / "backend" / "training" / "data"
MANIFEST = DATA / "manifest.json"
CLIPS = DATA / "clips.jsonl"
PAIRS = DATA / "pairs.jsonl"
SEALED = DATA / "sealed_tests.jsonl"
REPORT = REPO / ".planning" / "sealed" / "EVAL-SPLIT.md"
REFERENCE_SUBJECT = "sub_je"          # reference/ 영상 = 정은지 (subjects.jsonl role champion)
REFERENCE_SESSION = "reference"       # reference 촬영 세션은 clips 에 없다 — 별도 세션으로 본다


def _jsonl(p: pathlib.Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _eligible(row: dict) -> bool:
    try:
        spec = importlib.util.spec_from_file_location("gemini_teacher", REPO / "backend" / "training" / "distill" / "gemini_teacher.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return bool(mod.eligible_for_distill(row))
    except Exception:  # noqa: BLE001 — 증류 모듈 import 실패 시 같은 규칙을 로컬로
        return not row.get("holdout") and bool(row.get("s3_key"))


# ── 순수 함수 (tests/test_eval_split_check.py) ──────────────────────────────────


def group_key(clip: dict) -> tuple[str, str]:
    return (str(clip.get("subject_id") or "?"), str((clip.get("capture") or {}).get("session") or "?"))


def eval_groups(clips: list[dict], pairs: list[dict], sealed: list[dict]) -> dict:
    """봉인 시험지 → 평가 해시 → (짝 확장) → 평가 그룹 (subject, session) → 그 그룹의 모든 클립. 반환 {hashes, groups, subjects, clips}."""
    by_hash = {c["video_hash"]: c for c in clips}
    eval_hashes: set[str] = set()
    for t in sealed:
        for r in t.get("rows") or []:
            eval_hashes.add(r["video_hash"])
        for p in t.get("practice") or []:      # 연습 문제로 빠졌어도 정답이 공개된 영상 — 학습에 넣지 않는다
            eval_hashes.add(p["video_hash"])
    for p in pairs:
        if p.get("correct_hash") in eval_hashes or p.get("fault_hash") in eval_hashes:
            eval_hashes.update(h for h in (p.get("correct_hash"), p.get("fault_hash")) if h)
    groups = {group_key(by_hash[h]) for h in eval_hashes if h in by_hash}
    eval_clips = [c for c in clips if group_key(c) in groups or c["video_hash"] in eval_hashes]
    return {"hashes": eval_hashes, "groups": groups, "subjects": {g[0] for g in groups}, "clips": eval_clips}


def find_leaks(manifest_rows: list[dict], clips: list[dict], ev: dict, *, eligible=_eligible) -> dict:
    by_key = {c.get("s3_key"): c for c in clips if c.get("s3_key")}
    eval_keys = {c.get("s3_key") for c in ev["clips"] if c.get("s3_key")}
    l1, l2, l3 = [], [], []
    for row in manifest_rows:
        if not eligible(row):
            continue
        key = row.get("s3_key")
        if key in eval_keys:
            l1.append(key); continue
        clip = by_key.get(key)
        if clip is not None and group_key(clip) in ev["groups"]:
            l2.append(key); continue
        subj = clip.get("subject_id") if clip else (REFERENCE_SUBJECT if str(key or "").startswith("reference/") else None)
        if subj and subj in ev["subjects"]:
            l3.append(key)
    return {"L1_same_file": l1, "L2_same_session": l2, "L3_same_subject": l3}


def render_report(ev: dict, leaks: dict, n_eligible: int, *, now: str) -> str:
    subjects = sorted(ev["subjects"])
    lines = [
        "# 평가셋 분리 점검 (TRAINING-DUE 게이트 4)", "",
        f"점검 {now} · 학습 후보(증류 대상) {n_eligible}행", "",
        f"- 평가 영상(봉인 시험지 + 짝): {len(ev['hashes'])}편 · 평가 그룹(인물·세션): {sorted(ev['groups'])} · 평가 인물: {subjects}",
        f"- 평가 그룹에 속한 클립: {len(ev['clips'])}편",
        "",
        f"| 누수 | 건수 | 뜻 |", "|---|---|---|",
        f"| L1 같은 파일 | {len(leaks['L1_same_file'])} | 평가 영상 그 자체가 학습 후보 — **오류** |",
        f"| L2 같은 세션 | {len(leaks['L2_same_session'])} | 평가 인물·같은 촬영 세션의 다른 클립이 학습 후보 — **오류** |",
        f"| L3 같은 인물 | {len(leaks['L3_same_subject'])} | 평가 인물의 다른 세션(내부 촬영·reference) — 경고 |",
        "",
    ]
    for k in ("L1_same_file", "L2_same_session", "L3_same_subject"):
        if leaks[k]:
            lines += [f"{k}:"] + [f"- {s}" for s in leaks[k]] + [""]
    if len(subjects) <= 1:
        lines += ["**인물 분리 불가** — 평가 인물이 1명뿐이다(정은지). 다른 사람의 봉인 시험지가 생겨야 게이트 4 가 켜진다. "
                  "그 전까지 세션 분리(L1·L2 = 0)만 지킨다.", ""]
    ok = not leaks["L1_same_file"] and not leaks["L2_same_session"]
    lines += ["판정: " + ("세션 분리 OK (L1·L2 = 0)" if ok else "**누수 — 학습 전에 `--mark-holdout` 또는 manifest 수정**")]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mark-holdout", action="store_true", help="L1/L2 행에 holdout=sealed_eval 표시(증류 제외)")
    a = ap.parse_args()
    man = json.loads(MANIFEST.read_text(encoding="utf-8")); rows = man["rows"]
    clips, pairs, sealed = _jsonl(CLIPS), _jsonl(PAIRS), _jsonl(SEALED)
    ev = eval_groups(clips, pairs, sealed)
    leaks = find_leaks(rows, clips, ev)
    n_el = sum(1 for r in rows if _eligible(r))
    now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    md = render_report(ev, leaks, n_el, now=now)
    REPORT.parent.mkdir(parents=True, exist_ok=True); REPORT.write_text(md, encoding="utf-8")
    print(md)
    if a.mark_holdout and (leaks["L1_same_file"] or leaks["L2_same_session"]):
        bad = set(leaks["L1_same_file"]) | set(leaks["L2_same_session"])
        n = 0
        for r in rows:
            if r.get("s3_key") in bad and not r.get("holdout"):
                r["holdout"] = "sealed_eval"; r["usage"] = "eval-only-no-redistribution"; n += 1
        MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"manifest: {n}행 holdout=sealed_eval")
        return 0
    return 0 if not (leaks["L1_same_file"] or leaks["L2_same_session"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
