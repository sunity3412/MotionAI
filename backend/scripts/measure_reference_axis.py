#!/usr/bin/env python3
"""정은지 대비 각도 축을 분석 doc 위에서 잰다 — 학생 영상이 들어오면 바로 돌리는 자다.

왜 이게 리포에 있나
──────────────────
2026-09-20 의 조사(§14~§17, 착수점 SUMMARY)는 전부 세션 scratchpad 에서 돌았고 그 판은
휘발한다. 그런데 그때 내린 판정의 절반이 **"학생 영상으로는 미측정"** 에서 멈춰 있다.
영상이 오는 순간 같은 잣대로 다시 재야 비교가 되므로, 그 잣대를 여기 박제한다.

무엇을 재나 (전부 운영 함수 호출 — 채점 코드 재구현 0)
────────────────────────────────────────────────
1. **편차** — `pipeline/app.py::_deviation_against` 로 관절별 median |Δ각도|.
2. **바닥 대비** — 그 동작에서 정은지 본인 영상이 내는 바닥(`--floors`)과 비교.
   학생 편차가 바닥에 얼마나 얹히는지가 이 축의 핵심 미지수다.
3. **여유** — EXTEND criterion 의 감점 문턱(20도)까지 남은 거리.
   `[정정]` 여기 적혀 있던 "바닥 pdshape 15.0 / elbow-twist 15.8, 여유 2.0~2.3도" 는
   **옛 판(2026-09-17 rot180_v1 승격 이전) 값**이다. 현재 판은 pdshape 5.8 로 여유가
   12.1~17.2도다. **인용 정본은 옆 파일 `reference_axis_floors.json` 하나**로 한다 —
   이 머리말에 수치를 다시 박지 말 것(같은 세션이 만든 두 파일이 서로 다른 값을 말했다).
   학생이 그 위에 얼마나 얹히는지가 "못해서가 아니라 남이라서 깎이는가"를 가른다.
4. **매칭** — 저장된 각도만으로 기준 11편과 DTW 매칭해 top-1 이 사용자가 고른 기준과
   같은지. 크레딧 0 · Pod 0.
5. **채점 도달** — `line_score` / `leg_extension` 이 실제로 감점을 내는지.

주의 (읽는 사람에게)
──────────────────
- **기준 버전을 맞춰라.** 저장 분석과 라이브 기준 doc 의 버전이 다르면 편차가 통째로
  틀린다(2026-09-17 rot180_v1 승격). `--ref-version` 으로 고정하고, 모르면 doc 의
  `result.analysisVersion.referenceRelease` 를 보라. 기본값은 라이브 top-level 이다.
- Firestore 는 무료 플랜(읽기 5만/일)이다. `--limit` 없이 전수를 돌리지 마라.
- 이 스크립트는 **읽기 전용**이다. 쓰기 0.

사용:
  backend/.venv/bin/python backend/scripts/measure_reference_axis.py --pairs          # 원장의 짝 전부
  backend/.venv/bin/python backend/scripts/measure_reference_axis.py --pair pr_kipup_je_001
  backend/.venv/bin/python backend/scripts/measure_reference_axis.py --clips --floors backend/scripts/reference_axis_floors.json
  backend/.venv/bin/python backend/scripts/measure_reference_axis.py --uid <uid>
  backend/.venv/bin/python backend/scripts/measure_reference_axis.py --ids a1,a2 --json out.json
  backend/.venv/bin/python backend/scripts/measure_reference_axis.py --uid <uid> --ref-version phase4_v1
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))

_spec = importlib.util.spec_from_file_location(
    "pipeapp", str(REPO / "backend" / "functions" / "pipeline" / "app.py")
)
app = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(app)

from sunity_shared.analysis import dimensions, motiondtw, segments, skeleton, technique  # noqa: E402
from sunity_shared.analysis.features import feature_vector  # noqa: E402
from sunity_shared.analysis.ipsf_criteria import _ANGLE_TOLERANCE_DEG  # noqa: E402

JOINT_KEYS = list(skeleton.JOINT_KEYS)


def _db():
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", str(REPO / "firebase-sa.json"))
    from google.cloud import firestore

    return firestore.Client(project="sunity-ai-coach")


def load_references(db, version: str | None):
    """기준 11편. version 을 주면 versions/{version} 에서 angles 를 가져온다."""
    refs = {}
    for snap in db.collection("reference").stream():
        d = snap.to_dict() or {}
        mid = d.get("motionId") or snap.id
        if mid.startswith("_") or not d.get("angles"):
            continue
        if version:
            v = (db.document(f"reference/{mid}/versions/{version}").get().to_dict() or {})
            if v.get("angles"):
                d = {**d, **{k: v[k] for k in ("angles", "anglesFrames") if k in v}}
            else:
                print(f"  경고: {mid} 에 versions/{version} 이 없다 — top-level 사용", file=sys.stderr)
        refs[mid] = d
    return refs


def ref_matrix(rd):
    nj = len(rd.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
    return np.asarray(rd["angles"], dtype=float).reshape(-1, nj)


def ref_boundary_of(rd):
    """운영 mode1 경로와 동일 (app.py 의 _mode1_ref_boundary 산출)."""
    if rd.get("sharedBaseMotionId") and rd.get("baseUntilS") is not None and rd.get("clipRange"):
        nj = len(rd.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
        nr_full = len(rd["angles"]) // max(nj, 1)
        return segments.ref_boundary_frame(rd["clipRange"], rd["baseUntilS"], nr_full)
    return None


def deviate(student_angles, rd):
    dev, match, _seg, _a_ref = app._deviation_against(
        np.asarray(student_angles, dtype=float),
        np.asarray(rd["angles"], dtype=float),
        len(rd.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS,
        ref_boundary=ref_boundary_of(rd),
        ref_fps=app._reference_angles_fps(rd) or None,
    )
    return np.asarray(dev, dtype=float), match


def scalar(dev):
    d = dev[np.isfinite(dev)]
    return float(np.median(d)) if d.size else float("nan")


def extend_profile(rd, motion_id):
    """운영과 **같은 출처**에서 EXTEND 관절을 뽑는다 — criteria yaml.

    ★ 기준 doc 의 `techniqueProfile` 을 쓰면 안 된다. 그 스냅샷과 yaml 이 어긋난다 —
    2026-09-20 실측: `ref-power-spin` doc 은 무릎을 `bent_ok` · 오른팔꿈치를 `extend`
    라 적는데 `ref-power-spin.yaml` 은 **양 무릎 EXTEND** 다. 운영 채점기는 yaml 을
    본다(`gemini_technique_recognizer._joint_expectations_from_yaml`, `load_grouped_criteria`).
    doc 쪽을 쓰면 이 스크립트가 운영과 다른 점수를 보고한다(실측 line 81 vs 91).
    """
    try:
        from sunity_shared.judging.loader import load_grouped_criteria

        by_moment = load_grouped_criteria(motion_id)
        hold = by_moment.get("hold_moment", []) or by_moment.get("hold", [])
        extend = {c.joint_key for c in hold if c.extension_class == "EXTEND"}
    except (FileNotFoundError, ImportError, ValueError) as exc:
        print(f"  경고: {motion_id} yaml 미확보 — 8관절 BENT_OK 로 간주 ({exc})", file=sys.stderr)
        extend = set()
    exp = {
        k: (technique.JOINT_EXTEND if k in extend else technique.JOINT_BENT_OK)
        for k in JOINT_KEYS
    }
    return technique.TechniqueProfile(
        name=(rd.get("name") or "미상"), category="recognized",
        joint_expectations=exp, motion_id=motion_id,
    )


def collect(db, uid: str | None, ids: list[str], limit: int):
    """대상 분석 doc 수집. uid 를 주면 그 사용자 것만, ids 를 주면 그것만."""
    out = []
    if ids:
        for i in ids:
            if uid:
                snap = db.document(f"users/{uid}/analyses/{i}").get()
                if snap.exists:
                    out.append((uid, i, snap.to_dict() or {}))
            else:
                print("  --ids 는 --uid 와 함께 써라 (경로 복원 불가)", file=sys.stderr)
                break
        return out
    if uid:
        q = db.collection(f"users/{uid}/analyses").limit(limit)
        for snap in q.stream():
            out.append((uid, snap.id, snap.to_dict() or {}))
        return out
    print("  --uid 또는 --ids 가 필요하다 (전수 스캔은 일부러 막아뒀다)", file=sys.stderr)
    return out


# ── 원장에서 doc 찾기 + 짝 비교 (quick-260923-swh) ─────────────────────────────
# 2026-09-23 kip-up 비교는 손으로 했고 (1) 어느 doc 을 썼는지 안 남았고 (2) 운영과 다른
# 계산이었다(원시 각도 DTW · 경계 마스크 없음 → 어깨 20.1도, 운영·저장값은 20.62도).
# 그래서 여기서는 새 계산을 만들지 않는다 — 편차는 이 파일의 deviate()(= 운영
# _deviation_against), 점수·감점은 그 분석이 **저장한 값**을 읽는다.
# doc 은 intake_clips.py 가 남긴 analysis_runs.jsonl 로 찾는다(video_hash → doc).

DATA = REPO / "backend" / "training" / "data"


def _jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def latest_done_runs(runs: list[dict]) -> dict[str, dict]:
    """video_hash → 가장 최근에 끝난(done) 분석 기록."""
    out: dict[str, dict] = {}
    for r in runs:
        if r.get("status") != "done":
            continue
        cur = out.get(r["video_hash"])
        if cur is None or str(r.get("analyzed_at", "")) >= str(cur.get("analyzed_at", "")):
            out[r["video_hash"]] = r
    return out


def stored_consumer(d: dict) -> dict:
    """그 분석이 **실제로 낸 것** — 저장된 점수·감점·억제. 재계산이 아니다."""
    res = d.get("result") or {}
    bd = res.get("deductionBreakdown") or {}
    return {
        "overall": res.get("overallScore"),
        "records": [{"criterion": r.get("criterion"), "measured": r.get("measuredValue"),
                     "points": r.get("points")} for r in bd.get("records") or []],
        "suppressed": [{"criterion": s.get("criterion"), "measured": s.get("measuredValue"),
                        "would_be": s.get("wouldBePoints"), "low": s.get("intervalLow"),
                        "high": s.get("intervalHigh"), "tolerance": s.get("tolerance")}
                       for s in bd.get("suppressedRecords") or []],
        "version": res.get("analysisVersion") or {},
    }


def measure_doc(d: dict, rd: dict) -> dict:
    """운영 점수 경로로 관절별 편차 + 정렬 창. 창이 [0, 기준 전체)가 아니면 DTW 가 기준 안에서
    창을 미끄러뜨린 것이다(학생 영상이 기준의 1.2~1.5배 길이 — quick-260923-sqt)."""
    nj = len(d.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
    sa = np.asarray(d["angles"], dtype=float).reshape(-1, nj)
    dev, m = deviate(sa, rd)
    return {"per_joint": dict(zip(JOINT_KEYS, map(float, dev))),
            "window": [int(m.ref_start), int(m.ref_end)], "user_frames": int(len(sa)),
            "ref_frames": int(len(ref_matrix(rd))), "dtw_distance": float(m.distance)}


def _fetch(db, run: dict) -> dict:
    snap = db.document(f"users/{run['uid']}/analyses/{run['analysis_id']}").get()
    return (snap.to_dict() or {}) if snap.exists else {}


def _live_release(db) -> str | None:
    return (db.document("reference/_release").get().to_dict() or {}).get("activeCandidate")


def _suppressed_line(s: dict) -> str:
    return (f"{s['criterion']} {s['measured']}도 → {s['would_be']}점이 측정오차 구간 "
            f"{s['low']}~{s['high']}(허용 {s['tolerance']})에 걸려 빠짐")


def compare_pairs(db, refs, pair_filter: str | None, ref_version: str | None) -> list[dict]:
    """원장의 정타/실수 짝 → 같은 기준 대비 관절별 편차를 나란히 + 저장된 점수·감점."""
    runs = latest_done_runs(_jsonl(DATA / "analysis_runs.jsonl"))
    live = None if ref_version else _live_release(db)
    out = []
    for p in _jsonl(DATA / "pairs.jsonl"):
        if pair_filter and p["pair_id"] != pair_filter:
            continue
        print(f"\n== {p['pair_id']}  {p['motion']} · {p['subject_id']} ==")
        pick = {"정타": runs.get(p["correct_hash"]), "실수": runs.get(p["fault_hash"])}
        missing = [k for k, r in pick.items() if r is None]
        if missing:
            print(f"  분석 기록 없음: {', '.join(missing)} — intake_clips.py analyze 필요")
            continue
        rd = refs.get(f"ref-{p['motion']}")
        if rd is None:
            print(f"  기준 doc ref-{p['motion']} 없음")
            continue
        sides = {}
        for label, run in pick.items():
            d = _fetch(db, run)
            if d.get("status") != "done" or not d.get("angles"):
                print(f"  {label} doc 을 못 읽었다 ({run['analysis_id'][:8]})")
                break
            sides[label] = {"analysis_id": run["analysis_id"], "uid": run["uid"],
                            "measure": measure_doc(d, rd), "stored": stored_consumer(d)}
        if len(sides) < 2:
            continue
        rels = {s["stored"]["version"].get("referenceRelease") for s in sides.values()}
        used = ref_version or live
        for label, s in sides.items():
            m, st, v = s["measure"], s["stored"], s["stored"]["version"]
            print(f"  {label}  {s['analysis_id'][:8]}  저장 점수 {st['overall']}  "
                  f"창 [{m['window'][0]},{m['window'][1]}) 학생/기준 {m['user_frames']}/{m['ref_frames']}프레임  "
                  f"DTW {m['dtw_distance']:.2f}  {str(v.get('commitSha') or '?')[:8]} · {v.get('referenceRelease')}")
        if len(rels) > 1:
            print(f"  ★두 분석의 기준 판이 다르다 {sorted(map(str, rels))} — 편차 비교가 판 차이를 섞는다")
        elif used and rels != {used}:
            print(f"  ★분석 당시 기준 판 {rels.pop()} ≠ 지금 재는 판 {used} — "
                  f"--ref-version 으로 맞출 것 (reference-version-mismatch-trap)")
        pc, pf = sides["정타"]["measure"]["per_joint"], sides["실수"]["measure"]["per_joint"]
        print("  관절별 편차 — 운영 점수 경로(_deviation_against) 재계산, 도")
        print(f"    {'관절':16s}{'정타':>7s}{'실수':>7s}{'차':>8s}")
        for jk in sorted(JOINT_KEYS, key=lambda k: pf[k] - pc[k], reverse=True):
            print(f"    {jk:16s}{pc[jk]:7.1f}{pf[jk]:7.1f}{pf[jk] - pc[jk]:+8.1f}")
        for label, s in sides.items():
            st = s["stored"]
            recs = ", ".join(f"{r['criterion']} {r['measured']}도 {r['points']}점" for r in st["records"]) or "없음"
            print(f"  {label} — 실제로 받은 감점(저장값): {recs}")
            for sp in st["suppressed"]:
                print(f"    억제: {_suppressed_line(sp)}")
        out.append({"pair_id": p["pair_id"], "motion": p["motion"], "subject_id": p["subject_id"],
                    "reference_version_used": used, **{k: v for k, v in sides.items()}})
    return out


def clip_docs(db) -> list[tuple[str, str, dict]]:
    """원장(clips.jsonl)의 분석된 영상 → (uid, analysisId, doc). 기존 표 출력에 그대로 넣는다."""
    runs = latest_done_runs(_jsonl(DATA / "analysis_runs.jsonl"))
    out = []
    for c in _jsonl(DATA / "clips.jsonl"):
        r = runs.get(c["video_hash"])
        if r is None:
            continue
        out.append((r["uid"], r["analysis_id"], _fetch(db, r)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uid", help="대상 사용자 uid")
    ap.add_argument("--ids", default="", help="쉼표로 구분한 analysisId (--uid 필수)")
    ap.add_argument("--limit", type=int, default=50, help="uid 스캔 상한 (기본 50)")
    ap.add_argument("--ref-version", help="기준 버전 고정 (예: phase4_v1). 기본 = 라이브")
    ap.add_argument("--floors", help="동작별 바닥 JSON ({motionId: 도}). 주면 바닥 대비도 낸다")
    ap.add_argument("--json", help="결과를 이 경로에 JSON 으로 저장")
    ap.add_argument("--pairs", action="store_true",
                    help="원장 pairs.jsonl 의 짝 전부: 정타 vs 실수 (doc 은 analysis_runs.jsonl 로 찾음)")
    ap.add_argument("--pair", help="짝 하나만 (pair_id, 예: pr_kipup_je_001)")
    ap.add_argument("--clips", action="store_true",
                    help="원장 clips.jsonl 의 분석된 영상 전부를 아래 표로 (학생 영상용)")
    a = ap.parse_args()

    db = _db()
    refs = load_references(db, a.ref_version)
    if a.pairs or a.pair:
        rows = compare_pairs(db, refs, a.pair, a.ref_version)
        if a.json:
            json.dump(rows, open(a.json, "w"), ensure_ascii=False, indent=1)
            print(f"\n저장: {a.json}")
        return 0 if rows else 1
    floors = json.load(open(a.floors)) if a.floors else {}
    ids = [x.strip() for x in a.ids.split(",") if x.strip()]
    docs = clip_docs(db) if a.clips else collect(db, a.uid, ids, a.limit)
    if not docs:
        return 1
    print(f"대상 분석 {len(docs)}건 · 기준 {len(refs)}편"
          f"{' (버전 ' + a.ref_version + ')' if a.ref_version else ' (라이브)'}\n")

    rows = []
    hdr = (f"{'analysisId':14s}{'mode':6s}{'기준':22s}{'편차':>7s}{'바닥':>7s}"
           f"{'얹힌양':>8s}{'여유':>7s}{'매칭':>6s}{'line':>6s}{'저장점수':>9s}")
    print(hdr)
    print("-" * len(hdr))
    for uid, aid, d in docs:
        if d.get("status") != "done" or not d.get("angles"):
            continue
        mref = d.get("referenceMotionId")
        rd = refs.get(mref)
        if rd is None:
            continue
        nj = len(d.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
        sa = np.asarray(d["angles"], dtype=float).reshape(-1, nj)

        dev, _m = deviate(sa, rd)
        sc = scalar(dev)

        # 매칭: 기준 11편 중 DTW 최근접이 사용자가 고른 기준인가
        dists = sorted(
            (motiondtw.motion_dtw(feature_vector(sa), feature_vector(ref_matrix(r))).distance, k)
            for k, r in refs.items()
        )
        top1 = dists[0][1]

        # EXTEND 채점이 실제로 감점을 내는가
        prof = extend_profile(rd, mref)
        ls = dimensions.line_score(sa, prof)
        ext = dimensions.extension_deviation(sa, prof)
        worst_ext = float(np.max(ext)) if ext.size else 0.0

        floor = floors.get(mref)
        over = (sc - floor) if floor is not None else float("nan")
        margin = _ANGLE_TOLERANCE_DEG - sc
        res = (d.get("result") or {})
        rows.append(dict(uid=uid, analysisId=aid, mode=d.get("mode"), reference=mref,
                         deviation=sc, per_joint=dict(zip(JOINT_KEYS, map(float, dev))),
                         floor=floor, above_floor=over, margin_to_tolerance=margin,
                         match_top1=top1, match_ok=(top1 == mref),
                         line_score=ls, worst_extension_deficit=worst_ext,
                         stored_overall=res.get("overallScore")))
        print(f"{aid[:14]:14s}{str(d.get('mode')):6s}{str(mref):22s}{sc:7.1f}"
              f"{(f'{floor:7.1f}' if floor is not None else '      -')}"
              f"{(f'{over:+8.1f}' if floor is not None else '       -')}"
              f"{margin:7.1f}{('O' if top1 == mref else 'X'):>6s}"
              f"{str(ls):>6s}{str(res.get('overallScore')):>9s}")

    if rows:
        devs = np.array([r["deviation"] for r in rows], dtype=float)
        print(f"\n편차 중앙 {np.median(devs):.1f}도 · 범위 {devs.min():.1f}~{devs.max():.1f}")
        print(f"감점 문턱({_ANGLE_TOLERANCE_DEG:.0f}도) 초과 = "
              f"{int((devs > _ANGLE_TOLERANCE_DEG).sum())}/{len(devs)}건")
        ok = sum(1 for r in rows if r["match_ok"])
        print(f"DTW 매칭 top-1 일치 = {ok}/{len(rows)}건")
        if floors:
            ab = np.array([r["above_floor"] for r in rows if r["floor"] is not None], dtype=float)
            if ab.size:
                print(f"정은지 바닥 위로 얹힌 양: 중앙 {np.median(ab):+.1f}도 · "
                      f"범위 {ab.min():+.1f}~{ab.max():+.1f}")
                print("  ★ 이 값이 '학생이 못해서'인지 '남이라서'인지는 이 스크립트가 못 가른다 —")
                print("     같은 학생의 여러 동작, 또는 같은 동작의 여러 학생이 있어야 갈린다.")
    if a.json:
        json.dump(rows, open(a.json, "w"), ensure_ascii=False, indent=1)
        print(f"\n저장: {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
