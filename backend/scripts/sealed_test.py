#!/usr/bin/env python3
"""봉인 시험지 — belle 정답을 시스템 결과보다 먼저 봉인하고, 같은 코드로 돌려, 나란히 놓고 ○× 받는다 (quick-260925-nnt).

왜 (belle 2026-09-25)
────────────────────
*"내가 알려주면 그걸로 짜맞추려고?"* — 규칙인지 짜맞춤인지 가르는 유일한 방법은 규칙을 만들 때 안 본 영상에서 맞는가다.
그래서 (1) 정답을 카드보다 먼저 리포에 봉인(커밋)하고 (2) 코드 커밋을 고정한 채 앱 경로로 돌리고 (3) 정답과 카드를
나란히 놓아 belle 이 ○× 만 한다. 오늘(1회)은 손으로 했다 — 다음부터는 이 스크립트가 같은 순서를 강제한다.

규칙 (스크립트가 막는 것)
────────────────────────
- 이미 분석된 적 있는 영상(analysis_runs.jsonl 에 있음)은 시험지가 못 된다 → "연습 문제"로 표시하고 봉인에서 뺀다.
- 봉인 뒤 코드가 움직였으면(HEAD ≠ 봉인 커밋) run 이 멈춘다 (--allow-drift 로만 진행, 기록에 남는다).
- 채점은 사람(belle)만 한다 — 스크립트는 정답과 카드를 나란히 놓을 뿐, "맞았다"를 계산하지 않는다.

사용
────
  backend/.venv/bin/python backend/scripts/sealed_test.py seal  --sheet sheet.jsonl [--dry-run] [--no-push]
  backend/.venv/bin/python backend/scripts/sealed_test.py run   --test 260930-a1 [--allow-drift]      # Pod 이 떠 있어야 한다
  backend/.venv/bin/python backend/scripts/sealed_test.py grade --test 260930-a1                      # GRADE.md 생성(○× 빈 칸)
  backend/.venv/bin/python backend/scripts/sealed_test.py close --test 260930-a1 --marks "○,×,○"      # belle ○× 기록

SHEET (한 줄 = 영상 1편, intake_clips 시트의 부분집합 + answer)
  {"file": "/Users/Shared/sunity-intake/1005/a.mov", "motion": "kip-up", "intent": "fault",
   "answer": "왼팔을 접은 채로 돈다", "subject_id": "sub_je", "session": "2026-10-05-studio", "view": "side"}
  - answer: belle 한 줄. 정타면 "없음". 결과를 보기 **전에** 적는다.
  - subject 가 처음이면 intake_clips 시트처럼 "subject": {role, consent} 를 같이.
  - 파일은 홈 디렉터리 밖(/Users/Shared/)에 둘 것.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import pathlib
import subprocess
import sys
import types

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))
_spec = importlib.util.spec_from_file_location("intake_clips", REPO / "backend" / "scripts" / "intake_clips.py")
ic = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ic)  # type: ignore[union-attr]

SEALED = ic.DATA / "sealed_tests.jsonl"
GRADE_DIR = REPO / ".planning" / "sealed"
MARK_OK = "○"
MARK_NO = "×"


# ── 순수 함수 (tests/test_sealed_test.py) ─────────────────────────────────────────


def plan_rows(sheet_rows: list[dict], clips: list[dict], runs: list[dict]) -> tuple[list[dict], list[dict]]:
    """시트 → (시험지 행, 연습 문제 행). 이미 분석된 영상은 연습 문제. answer 없는 행은 오류."""
    seen = {r["video_hash"] for r in runs}
    have = {c["video_hash"]: c for c in clips}
    tests, practice = [], []
    for row in sheet_rows:
        ans = (row.get("answer") or "").strip()
        if not ans:
            raise ic.IntakeError(f"{row.get('file')}: answer 없음 — 정타면 \"없음\" 이라고 적는다")
        vh = row["video_hash"]
        entry = {"video_hash": vh, "motion": row["motion"], "intent": row["intent"], "answer": ans}
        if vh in seen:
            entry["reason"] = "이미 분석된 영상 — 시스템이 본 적 있다(연습 문제)"
            practice.append(entry)
        else:
            if vh in have and (have[vh].get("motion") != row["motion"] or have[vh].get("intent") != row["intent"]):
                raise ic.IntakeError(f"{vh[:12]}: 등록된 motion/intent 와 다르다 — 시트를 고쳐라")
            tests.append(entry)
    return tests, practice


def to_intake_sheet_row(row: dict) -> dict:
    """봉인 시트 행 → intake_clips 시트 행 (note = 봉인 정답)."""
    out = {k: row[k] for k in ("file", "motion", "intent", "subject_id") if k in row}
    out.setdefault("subject_id", "sub_je")
    out["note"] = f"봉인 정답: {row['answer']}"
    for k in ("subject", "view", "session", "pair_key", "fault_intent"):
        if k in row:
            out[k] = row[k]
    return out


def screen_lines(doc: dict) -> dict:
    """분석 doc(result) → 화면이 말하는 것: 점수 · 감점 문장(statusLine) · 못 잰 부위 한 줄 · 잰 값 패턴."""
    r = doc.get("result") or doc
    bd = r.get("deductionBreakdown") or {}
    recs = bd.get("records") or []
    hidden = set((r.get("spotCheck") or {}).get("hiddenRecordIds") or [])
    said = []
    for rec in recs:
        if rec.get("recordId") in hidden:
            continue
        line = rec.get("statusLine") or rec.get("criterion") or "?"
        pts = rec.get("points")
        tag = f" (잰 값 패턴 {rec.get('measuredPattern')})" if rec.get("measuredPattern") else ""
        said.append(f"{line} [{pts}]{tag}")
    unmeasured = [q.get("text") for q in (r.get("coachQuestions") or []) if q.get("source") == "unmeasured" and q.get("text")]
    return {
        "score": r.get("overallScore"),
        "deductions": said,
        "unmeasured": unmeasured,
        "status": doc.get("status") or r.get("status"),
    }


def grade_table(test: dict, docs: dict[str, dict]) -> str:
    """정답과 카드를 나란히 — ○× 칸은 비워 둔다(사람만 채운다)."""
    lines = [
        f"# 봉인 시험지 {test['test_id']} — 판정지",
        "",
        f"봉인 {test['sealed_at']} · 코드 {test.get('code_commit', '?')[:8]} · 분석 {test.get('run_at', '-')}",
        "",
        "| # | 영상 | belle 정답(봉인) | 점수 | 카드가 말한 것 | 못 잰 부위 한 줄 | belle ○× |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, row in enumerate(test["rows"], 1):
        doc = docs.get(row["video_hash"])
        if doc is None:
            lines.append(f"| {i} | {row['motion']} {row['intent']} | {row['answer']} | — | (분석 없음) | | |")
            continue
        s = screen_lines(doc)
        ded = "<br>".join(s["deductions"]) or "감점 없음"
        unm = "<br>".join(s["unmeasured"]) or "-"
        mark = (test.get("marks") or [None] * len(test["rows"]))[i - 1] or ""
        lines.append(f"| {i} | {row['motion']} {row['intent']} | {row['answer']} | {s['score']} | {ded} | {unm} | {mark} |")
    if test.get("practice"):
        lines += ["", "연습 문제로 빠진 영상(시스템이 본 적 있음):"]
        lines += [f"- {p['motion']} {p['intent']} {p['video_hash'][:12]} — {p['answer']}" for p in test["practice"]]
    if test.get("marks"):
        n_ok = sum(1 for m in test["marks"] if m == MARK_OK)
        lines += ["", f"**처음 보는 영상 {len(test['rows'])}편 중 {n_ok}편 맞게 말함** (belle ○ 기준)"]
    return "\n".join(lines) + "\n"


def parse_marks(text: str, n: int) -> list[str]:
    marks = [m.strip() for m in text.replace("O", MARK_OK).replace("o", MARK_OK).replace("X", MARK_NO).replace("x", MARK_NO).split(",")]
    if len(marks) != n or any(m not in (MARK_OK, MARK_NO) for m in marks):
        raise ValueError(f"○× {n}개를 쉼표로 — 예: \"○,×,○\" (받은 것: {text!r})")
    return marks


# ── 파일·git ────────────────────────────────────────────────────────────────────


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=str(REPO), text=True).strip()


def _load_tests() -> list[dict]:
    return ic.read_jsonl(SEALED)


def _save_tests(tests: list[dict]) -> None:
    SEALED.parent.mkdir(parents=True, exist_ok=True)
    SEALED.write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tests), encoding="utf-8")


def _get_test(test_id: str) -> tuple[list[dict], dict]:
    tests = _load_tests()
    for t in tests:
        if t["test_id"] == test_id:
            return tests, t
    raise SystemExit(f"시험지 {test_id} 없음 — {SEALED}")


def _commit(paths: list[pathlib.Path], msg: str, push: bool) -> str:
    _git("add", *[str(p) for p in paths])
    _git("commit", "-q", "-m", msg + "\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>")
    if push:
        _git("push", "-q", "origin", "main")
    return _git("rev-parse", "--short", "HEAD")


# ── 명령 ─────────────────────────────────────────────────────────────────────────


def cmd_seal(a) -> int:
    lines = [ln for ln in pathlib.Path(a.sheet).read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows = [json.loads(ln) for ln in lines]
    for r in rows:
        p = pathlib.Path(r.get("file", "")).expanduser()
        if not p.is_file():
            print(f"  파일 없음 {p}", file=sys.stderr)
            return 2
        r["video_hash"] = ic.sha256_file(p)
    try:
        tests, practice = plan_rows(rows, ic.read_jsonl(ic.CLIPS), ic.read_jsonl(ic.RUNS))
    except ic.IntakeError as e:
        print(f"  {e}", file=sys.stderr)
        return 2
    for p in practice:
        print(f"  연습 문제 {p['video_hash'][:12]} {p['motion']} {p['intent']} — {p['reason']}")
    if not tests:
        print("봉인할 새 영상이 없다.")
        return 3
    # intake 등록 (S3 영구 사본 + clips.jsonl) — 봉인 정답은 note 에.
    sheet = pathlib.Path(a.sheet).with_suffix(".intake.jsonl")
    sheet.write_text("".join(json.dumps(to_intake_sheet_row(r), ensure_ascii=False) + "\n"
                             for r in rows if r["video_hash"] in {t["video_hash"] for t in tests}), encoding="utf-8")
    rc = ic.cmd_register(types.SimpleNamespace(sheet=str(sheet), dry_run=a.dry_run))
    if rc != 0:
        return rc
    test_id = a.test_id or _dt.date.today().strftime("%y%m%d") + "-" + _dt.datetime.now().strftime("%H%M")
    entry = {
        "test_id": test_id, "status": "sealed",
        "sealed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "code_commit": _git("rev-parse", "HEAD"),
        "rows": tests, "practice": practice, "runs": {}, "marks": None,
    }
    if a.dry_run:
        print(f"\ndry-run — 봉인 안 함. 시험지 {len(tests)}편 · 연습 문제 {len(practice)}편")
        return 0
    all_tests = _load_tests() + [entry]
    _save_tests(all_tests)
    h = _commit([SEALED, ic.CLIPS, ic.SUBJECTS, ic.PAIRS],
                f"seal(sealed-test {test_id}): belle 정답 {len(tests)}편 봉인 — 카드 대조 전", push=not a.no_push)
    print(f"\n봉인 {test_id}: {len(tests)}편, 커밋 {h}. 이제 Pod 을 띄우고 `run --test {test_id}`.")
    return 0


def cmd_run(a) -> int:
    tests, t = _get_test(a.test)
    if t["status"] not in ("sealed", "run"):
        print(f"  상태 {t['status']} — run 은 sealed 에서만", file=sys.stderr)
        return 2
    head = _git("rev-parse", "HEAD")
    if head != t["code_commit"]:
        print(f"  ★코드가 봉인 뒤 움직였다: 봉인 {t['code_commit'][:8]} → 지금 {head[:8]}.", file=sys.stderr)
        if not a.allow_drift:
            print("    시험은 봉인 커밋의 코드로 해야 한다. 그 커밋으로 Pod 을 올리거나, 알고도 가려면 --allow-drift.", file=sys.stderr)
            return 4
        t["code_drift"] = head
    hashes = [r["video_hash"] for r in t["rows"]]
    rc = ic.cmd_analyze(types.SimpleNamespace(hash=hashes, pending=False))
    runs = ic.read_jsonl(ic.RUNS)
    for r in runs:  # 원장은 시간순 append — 같은 영상이 여러 번이면 마지막(이번) 것이 남는다
        if r["video_hash"] in hashes:
            t["runs"][r["video_hash"]] = {"uid": r["uid"], "analysis_id": r["analysis_id"], "status": r["status"],
                                         "overall_score": r.get("overall_score")}
    t["status"] = "run"
    t["run_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    _save_tests(tests)
    h = _commit([SEALED, ic.RUNS], f"data(sealed-test {a.test}): 앱 경로 분석 {len(t['runs'])}/{len(hashes)}편 기록", push=not a.no_push)
    print(f"\n분석 기록 커밋 {h} (rc={rc}). 다음: `grade --test {a.test}`")
    return rc


def cmd_grade(a) -> int:
    tests, t = _get_test(a.test)
    from sunity_shared import firestore_admin as fa
    docs = {}
    for vh, run in (t.get("runs") or {}).items():
        d = fa.get_analysis(run["uid"], run["analysis_id"])
        if d:
            docs[vh] = d
    md = grade_table(t, docs)
    out = GRADE_DIR / t["test_id"] / "GRADE.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(md)
    if t["status"] == "run":
        t["status"] = "graded"
        _save_tests(tests)
    h = _commit([SEALED, out], f"docs(sealed-test {a.test}): 판정지 — 정답·카드 나란히, ○× 는 belle", push=not a.no_push)
    print(f"판정지 {out} 커밋 {h}. belle ○× 뒤: `close --test {a.test} --marks \"○,×,…\"`")
    return 0


def cmd_close(a) -> int:
    tests, t = _get_test(a.test)
    try:
        marks = parse_marks(a.marks, len(t["rows"]))
    except ValueError as e:
        print(f"  {e}", file=sys.stderr)
        return 2
    t["marks"] = marks
    t["status"] = "closed"
    t["closed_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    _save_tests(tests)
    from sunity_shared import firestore_admin as fa
    docs = {vh: fa.get_analysis(run["uid"], run["analysis_id"]) for vh, run in (t.get("runs") or {}).items()}
    out = GRADE_DIR / t["test_id"] / "GRADE.md"
    out.write_text(grade_table(t, {k: v for k, v in docs.items() if v}), encoding="utf-8")
    n_ok = sum(1 for m in marks if m == MARK_OK)
    h = _commit([SEALED, out], f"docs(sealed-test {a.test}): belle ○× — {len(marks)}편 중 {n_ok}편", push=not a.no_push)
    print(f"닫힘: {len(marks)}편 중 {n_ok}편 맞게 말함. 커밋 {h}. 이 영상들은 이제 연습 문제다(정답 공개).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seal"); s.add_argument("--sheet", required=True); s.add_argument("--test-id"); s.add_argument("--dry-run", action="store_true"); s.add_argument("--no-push", action="store_true")
    r = sub.add_parser("run"); r.add_argument("--test", required=True); r.add_argument("--allow-drift", action="store_true"); r.add_argument("--no-push", action="store_true")
    g = sub.add_parser("grade"); g.add_argument("--test", required=True); g.add_argument("--no-push", action="store_true")
    c = sub.add_parser("close"); c.add_argument("--test", required=True); c.add_argument("--marks", required=True); c.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    return {"seal": cmd_seal, "run": cmd_run, "grade": cmd_grade, "close": cmd_close}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
