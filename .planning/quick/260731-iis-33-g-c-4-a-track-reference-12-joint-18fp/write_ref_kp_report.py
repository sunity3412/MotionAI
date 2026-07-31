"""top-level `referenceKeypointReport` 단일 필드 교체 + 백업/복구 + 게이트 + 사후 재조회.

quick-260731-iis T2. 33-G §C-4 A-트랙.
프로덕션 스크립트가 아니다 — 이 quick 사이클 전용 운영 도구.

**쓰기 범위 (L-1)**: `reference/{id}` 의 top-level `referenceKeypointReport` 필드 **하나**뿐.
`set({"referenceKeypointReport": rep}, merge=True)` 의 dict 에 다른 키를 넣지 않는다.
angles / anglesJointKeys / anglesFrames / joints3d 계열 / coordDim / space /
activeVersion / reference/_release / versions/* 에는 쓰지 않는다.

게이트:
  GATE-C (쓰기 전) — reference/_release.activeCandidate 가 세팅돼 있으면 중단.
    그러면 get_reference_motion 이 해석하는 angles 가 candidate 것이라 top-level 18fps
    표시 보고서는 정합이 아니다.
  GATE-A (쓰기 전, 11/11 all-or-nothing) —
    fps == 18.0 / len(joints) == 12 / frames == 그 doc 의 top-level anglesFrames /
    len(data) == frames*joints*2 / len(confidence) == frames*joints / NaN·inf 0 /
    firestore_admin._validate_keypoint_report 통과 (새 validator 작성 금지, 재사용).
  GATE-B (쓰기 후) — 채점 8필드 해시(_release_doc_hash) BEFORE == AFTER 11/11,
    activeVersion 11/11 불변, _release.activeCandidate 불변.

모드:
  --backup   현행 top-level referenceKeypointReport 원본 전체를 저장 (부재는 null 명시).
  --dry-run  (기본) GATE-C + GATE-A 를 계산해 표로 출력. 쓰기 0.
  --write    교체 수행. 백업 파일이 없으면 거부. 쓰기 직전 GATE-C·해시를 다시 확인.
  --restore  백업 값을 그대로 되돌린다. 백업이 null 이던 doc 은 건너뛴다
             (Firestore 필드 삭제는 이 플랜 범위 밖).

실행 위치 = Pod (로컬 Mac 은 Firestore 조회가 행에 걸린다 — 2026-07-31 실측).
"""
from __future__ import annotations

import argparse
import importlib.util as _ilu
import json
import math
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()


def _find_backend() -> Path:
    for p in _HERE.parents:
        if (p / "backend" / "shared" / "python").is_dir():
            return p / "backend"
    pod = Path("/workspace/SunityMotion/backend")
    if (pod / "shared" / "python").is_dir():
        return pod
    raise RuntimeError("backend 디렉터리를 찾지 못함")


_BACKEND = _find_backend()
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_BACKEND / "shared" / "python"))

from sunity_shared import firestore_admin as fa  # noqa: E402

_spec = _ilu.spec_from_file_location(
    "_reprocess_p4", str(_BACKEND / "scripts" / "reprocess_reference_motions_phase4.py")
)
_reprocess = _ilu.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_reprocess)
_release_doc_hash = _reprocess._release_doc_hash

MOTION_IDS_11 = [
    "ref-sideway-spin", "ref-climb", "ref-invert", "ref-foxtop", "ref-foxtop-split",
    "ref-combo", "ref-elbow-twist-sister", "ref-kip-up", "ref-pdshape",
    "ref-peter-pan", "ref-power-spin",
]
TARGET_FPS = 18.0
TARGET_JOINTS = 12
FIELD = "referenceKeypointReport"


# ── 조회 ──────────────────────────────────────────────────────────────────────


def _top(db, mid: str) -> dict:
    snap = db.document(f"reference/{mid}").get()
    return (snap.to_dict() or {}) if getattr(snap, "exists", False) else {}


def _release(db) -> tuple[bool, object]:
    snap = db.document("reference/_release").get()
    if not getattr(snap, "exists", False):
        return (False, None)
    return (True, (snap.to_dict() or {}).get("activeCandidate"))


def _row(mid: str, top: dict) -> dict:
    rep = top.get(FIELD)
    rep = rep if isinstance(rep, dict) and rep else {}
    joints = rep.get("joints")
    return {
        "motion": mid,
        "activeVersion": top.get("activeVersion"),
        "anglesFrames": top.get("anglesFrames"),
        "refkpFps": float(rep["fps"]) if rep.get("fps") is not None else None,
        "refkpFrames": int(rep["frames"]) if rep.get("frames") is not None else None,
        "refkpJoints": len(joints) if isinstance(joints, list) else None,
        "scoringHash": _release_doc_hash(top),
    }


# ── GATE-A ────────────────────────────────────────────────────────────────────


def _gate_a(mid: str, rep: dict, angles_frames) -> list[str]:
    """이 동작 1건의 GATE-A 위반 사유 목록. 빈 리스트 = 통과."""
    bad: list[str] = []
    fps = rep.get("fps")
    joints = rep.get("joints") or []
    frames = rep.get("frames")
    data = rep.get("data") or []
    conf = rep.get("confidence") or []

    if fps is None or float(fps) != TARGET_FPS:
        bad.append(f"fps={fps!r} != {TARGET_FPS}")
    if len(joints) != TARGET_JOINTS:
        bad.append(f"joints={len(joints)} != {TARGET_JOINTS}")
    if frames is None or angles_frames is None or int(frames) != int(angles_frames):
        bad.append(f"frames={frames!r} != anglesFrames={angles_frames!r}")
    if frames is not None and joints:
        want_d = int(frames) * len(joints) * 2
        want_c = int(frames) * len(joints)
        if len(data) != want_d:
            bad.append(f"len(data)={len(data)} != frames*joints*2={want_d}")
        if len(conf) != want_c:
            bad.append(f"len(confidence)={len(conf)} != frames*joints={want_c}")
    n_bad = sum(1 for v in data if not math.isfinite(float(v)))
    n_bad += sum(1 for v in conf if not math.isfinite(float(v)))
    for v in rep.get("axisData") or []:
        if not math.isfinite(float(v)):
            n_bad += 1
    if n_bad:
        bad.append(f"NaN/inf {n_bad}개")

    # 프로덕션 validator 재사용 (새 validator 작성 금지).
    try:
        fa._validate_keypoint_report(rep, path=f"{mid}.{FIELD}")
    except ValueError as exc:
        bad.append(f"_validate_keypoint_report: {exc}")
    return bad


def _evaluate(db, reports: dict) -> tuple[list[dict], list[str], dict]:
    """11/11 GATE-A 평가 + GATE-C. 반환 (표, 치명 사유, 현재 BEFORE row 인덱스)."""
    rows: list[dict] = []
    fatal: list[str] = []
    before: dict[str, dict] = {}

    rel_exists, rel_cand = _release(db)
    if rel_cand:
        fatal.append(
            f"GATE-C 실패: reference/_release.activeCandidate={rel_cand!r} 세팅됨 — "
            "candidate angles 가 해석되므로 top-level 18fps 표시 보고서는 정합이 아니다"
        )

    for mid in MOTION_IDS_11:
        top = _top(db, mid)
        before[mid] = _row(mid, top)
        rep = reports.get(mid)
        if not isinstance(rep, dict) or not rep:
            fatal.append(f"{mid}: 신규 보고서 없음")
            rows.append({"motion": mid, "verdict": "NO_REPORT"})
            continue
        bad = _gate_a(mid, rep, top.get("anglesFrames"))
        rows.append({
            "motion": mid,
            "anglesFrames": top.get("anglesFrames"),
            "newFps": rep.get("fps"),
            "newFrames": rep.get("frames"),
            "newJoints": len(rep.get("joints") or []),
            "curFps": before[mid]["refkpFps"],
            "curFrames": before[mid]["refkpFrames"],
            "curJoints": before[mid]["refkpJoints"],
            "verdict": "PASS" if not bad else "FAIL",
            "violations": bad,
        })
        if bad:
            fatal.append(f"{mid}: " + "; ".join(bad))

    return rows, fatal, before


def _print_gate_table(rows: list[dict], rel_exists: bool, rel_cand) -> None:
    print(f"reference/_release exists={rel_exists} activeCandidate={rel_cand!r}", file=sys.stderr)
    print(
        f"{'motion':<24}{'anglesFrames':>13}{'new fps/fr/J':>18}{'cur fps/fr/J':>18}{'verdict':>9}",
        file=sys.stderr,
    )
    for r in rows:
        if r.get("verdict") == "NO_REPORT":
            print(f"{r['motion']:<24}{'-':>13}{'-':>18}{'-':>18}{'NO_REPORT':>9}", file=sys.stderr)
            continue
        new_s = "{}/{}/{}".format(r["newFps"], r["newFrames"], r["newJoints"])
        cur_s = "{}/{}/{}".format(r["curFps"], r["curFrames"], r["curJoints"])
        print(
            f"{r['motion']:<24}{str(r['anglesFrames']):>13}"
            f"{new_s:>18}{cur_s:>18}{r['verdict']:>9}",
            file=sys.stderr,
        )
        for v in r.get("violations") or []:
            print(f"    ! {v}", file=sys.stderr)


# ── 모드 ──────────────────────────────────────────────────────────────────────


def do_backup(db, out: Path) -> int:
    payload = {}
    for mid in MOTION_IDS_11:
        top = _top(db, mid)
        rep = top.get(FIELD)
        payload[mid] = rep if isinstance(rep, dict) and rep else None
    out.write_text(json.dumps(payload, ensure_ascii=False))
    n_null = sum(1 for v in payload.values() if v is None)
    print(f"백업 {len(payload)}건 저장 (null {n_null}건) → {out}", file=sys.stderr)
    return 0


def do_write(db, reports: dict, backup_file: Path, before_file: Path, out_after: Path,
             only: list[str] | None) -> int:
    if not backup_file.is_file():
        print(f"거부: 백업 파일 부재 {backup_file} — --backup 먼저 실행", file=sys.stderr)
        return 2
    backup = json.loads(backup_file.read_text())
    missing = [m for m in MOTION_IDS_11 if m not in backup]
    if missing:
        print(f"거부: 백업에 누락 {missing}", file=sys.stderr)
        return 2

    rows, fatal, before_now = _evaluate(db, reports)
    rel_exists, rel_cand = _release(db)
    _print_gate_table(rows, rel_exists, rel_cand)
    if fatal:
        print("\nGATE 실패 — 쓰기 0. 사유:", file=sys.stderr)
        for f in fatal:
            print(f"  - {f}", file=sys.stderr)
        return 3

    # T1 시점 이후 채점 8필드가 변하지 않았는지 재확인 (변했으면 중단).
    if before_file.is_file():
        t1 = {r["motion"]: r for r in json.loads(before_file.read_text())["motions"]}
        drift = [
            m for m in MOTION_IDS_11
            if m in t1 and t1[m].get("scoringHash") != before_now[m]["scoringHash"]
        ]
        if drift:
            print(f"거부: T1 이후 채점 8필드 해시 변동 {drift}", file=sys.stderr)
            return 3

    targets = only or MOTION_IDS_11
    for mid in targets:
        db.document(f"reference/{mid}").set({FIELD: reports[mid]}, merge=True)
        print(f"  [{mid}] {FIELD} 교체", file=sys.stderr)

    return _emit_after(db, before_now, out_after)


def do_restore(db, backup_file: Path, only: list[str] | None) -> int:
    backup = json.loads(backup_file.read_text())
    targets = only or MOTION_IDS_11
    for mid in targets:
        rep = backup.get(mid)
        if rep is None:
            print(f"  [{mid}] 백업 null — 건너뜀 (필드 삭제는 범위 밖)", file=sys.stderr)
            continue
        db.document(f"reference/{mid}").set({FIELD: rep}, merge=True)
        print(f"  [{mid}] {FIELD} 원본 복구", file=sys.stderr)
    return 0


def _emit_after(db, before_now: dict, out_after: Path) -> int:
    rel_exists, rel_cand = _release(db)
    rows = []
    for mid in MOTION_IDS_11:
        top = _top(db, mid)
        r = _row(mid, top)
        b = before_now.get(mid, {})
        r["scoringHashBefore"] = b.get("scoringHash")
        r["scoringHashUnchanged"] = b.get("scoringHash") == r["scoringHash"]
        r["activeVersionBefore"] = b.get("activeVersion")
        r["activeVersionUnchanged"] = b.get("activeVersion") == r["activeVersion"]
        # 파생 — ref_display_frame_index 배율이 identity 로 가는지
        r["refkpRep9N"] = (
            round(r["refkpFrames"] * 9.0 / r["refkpFps"], 3)
            if r["refkpFrames"] and r["refkpFps"] else None
        )
        kp = top.get("keypointReport") or {}
        r["anglesRep9N"] = (
            round(top["anglesFrames"] * 9.0 / float(kp["fps"]), 3)
            if top.get("anglesFrames") and kp.get("fps") else None
        )
        r["scaleRatio"] = (
            round(r["anglesRep9N"] / r["refkpRep9N"], 4)
            if r["refkpRep9N"] and r["anglesRep9N"] else None
        )
        rows.append(r)

    out_after.write_text(json.dumps(
        {"release": {"docExists": rel_exists, "activeCandidate": rel_cand}, "motions": rows},
        ensure_ascii=False, indent=2,
    ))

    print(f"\n{'motion':<24}{'fps/fr/J':>18}{'aFrames':>9}{'hash==':>8}"
          f"{'aVer==':>8}{'rep9N':>9}{'scale':>8}", file=sys.stderr)
    for r in rows:
        rep_s = "{}/{}/{}".format(r["refkpFps"], r["refkpFrames"], r["refkpJoints"])
        print(
            f"{r['motion']:<24}{rep_s:>18}"
            f"{str(r['anglesFrames']):>9}{str(r['scoringHashUnchanged']):>8}"
            f"{str(r['activeVersionUnchanged']):>8}{str(r['refkpRep9N']):>9}"
            f"{str(r['scaleRatio']):>8}",
            file=sys.stderr,
        )
    n_h = sum(1 for r in rows if r["scoringHashUnchanged"])
    n_v = sum(1 for r in rows if r["activeVersionUnchanged"])
    print(f"\nGATE-B: 채점해시 불변 {n_h}/11 · activeVersion 불변 {n_v}/11 · "
          f"_release.activeCandidate={rel_cand!r}", file=sys.stderr)
    print(f"→ {out_after}", file=sys.stderr)
    return 0 if (n_h == 11 and n_v == 11) else 4


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--backup", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--write", action="store_true")
    g.add_argument("--restore", action="store_true")
    ap.add_argument("--reports", type=Path, help="reference-kp-18fps.json")
    ap.add_argument("--backup-file", type=Path, default=Path("/workspace/refkp_backup.json"))
    ap.add_argument("--before-file", type=Path, default=Path("/workspace/refkp_before.json"))
    ap.add_argument("--out-after", type=Path, default=Path("/workspace/refkp_after.json"))
    ap.add_argument("--motions", nargs="+", default=None, help="부분 대상 (restore 왕복 실증용)")
    args = ap.parse_args()

    db = fa._db()

    if args.backup:
        return do_backup(db, args.backup_file)
    if args.restore:
        rc = do_restore(db, args.backup_file, args.motions)
        if rc == 0:
            _emit_after(db, {}, args.out_after)
        return rc

    reports = {}
    if args.reports:
        reports = json.loads(args.reports.read_text())["motions"]

    if args.write:
        return do_write(db, reports, args.backup_file, args.before_file,
                        args.out_after, args.motions)

    # 기본 = dry-run
    rows, fatal, _ = _evaluate(db, reports)
    rel_exists, rel_cand = _release(db)
    _print_gate_table(rows, rel_exists, rel_cand)
    n_pass = sum(1 for r in rows if r.get("verdict") == "PASS")
    print(f"\nGATE-A {n_pass}/11 통과 (all-or-nothing)", file=sys.stderr)
    if fatal:
        print("치명 사유:", file=sys.stderr)
        for f in fatal:
            print(f"  - {f}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
