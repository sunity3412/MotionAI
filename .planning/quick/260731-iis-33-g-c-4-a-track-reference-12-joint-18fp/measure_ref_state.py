"""기준 11 doc 의 타임베이스·해시·릴리스 포인터 실측 (읽기 전용).

quick-260731-iis T1-c. 33-G §C-4 A-트랙의 BEFORE 스냅샷을 만든다.
쓰기 0 — Firestore 를 읽기만 한다.

기록 대상 (동작별):
  · top-level: activeVersion / anglesFrames / len(anglesJointKeys)
  · top-level `keypointReport` 와 `referenceKeypointReport` 의 fps·frames·len(joints)
    (부재는 null 로 명시 — 조용히 빠뜨리지 않는다)
  · 채점 8필드 해시 = reprocess_reference_motions_phase4._release_doc_hash (import 재사용)
  · candidate `phase33-cm3-run1` 의 두 보고서 메타 + anglesFrames
  · get_reference_motion() 이 **실제로 해석하는** 문서의 anglesFrames / keypointReport.fps
  · 파생: rep9_n = report.frames * 9.0 / report.fps — ref_display_frame_index 배율 왜곡 추적

전역: reference/_release 문서 존재 여부와 activeCandidate (L-4 GATE-C 입력).

실행 위치 = Pod (로컬 Mac 은 Firestore 조회가 행에 걸린다 — 2026-07-31 실측).
  cd /workspace/SunityMotion/backend
  export PYTHONPATH=$PWD:$PWD/shared/python
  python /workspace/measure_ref_state.py --out /workspace/refkp_before.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# repo 루트 주입 — extract_reference_keypoint_reports.py:43-45 패턴.
# Pod 에서는 스크립트가 repo 밖(/workspace)에 놓이므로 조상 탐색 + Pod 기본경로 폴백.
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
sys.path.insert(0, str(_BACKEND / "scripts"))

from sunity_shared import firestore_admin as fa  # noqa: E402

# 해시 로직 복제 금지 — 프로덕션 스크립트에서 import (플랜 T1-c).
import importlib.util as _ilu  # noqa: E402

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
CANDIDATE = "phase33-cm3-run1"


def _rep_meta(rep) -> dict:
    """보고서 메타 3종. 부재/비-dict 는 null 로 명시."""
    if not isinstance(rep, dict) or not rep:
        return {"fps": None, "frames": None, "joints": None}
    joints = rep.get("joints")
    return {
        "fps": float(rep["fps"]) if rep.get("fps") is not None else None,
        "frames": int(rep["frames"]) if rep.get("frames") is not None else None,
        "joints": len(joints) if isinstance(joints, list) else None,
    }


def _rep9_n(meta: dict) -> float | None:
    """9fps 렌더 공간으로 환산한 프레임 수 (ref_display_frame_index 배율 추적용)."""
    if not meta.get("frames") or not meta.get("fps"):
        return None
    return round(meta["frames"] * 9.0 / meta["fps"], 3)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    db = fa._db()

    # 전역 릴리스 포인터 (GATE-C 입력).
    rel_snap = db.document("reference/_release").get()
    rel_exists = bool(getattr(rel_snap, "exists", False))
    rel = (rel_snap.to_dict() or {}) if rel_exists else {}
    release = {
        "docExists": rel_exists,
        "activeCandidate": rel.get("activeCandidate"),
        "allKeys": sorted(rel.keys()) if rel else [],
    }

    rows = []
    for mid in MOTION_IDS_11:
        snap = db.document(f"reference/{mid}").get()
        if not getattr(snap, "exists", False):
            rows.append({"motion": mid, "topLevelMissing": True})
            continue
        top = snap.to_dict() or {}
        kp = _rep_meta(top.get("keypointReport"))
        rkp = _rep_meta(top.get("referenceKeypointReport"))

        # candidate 버전 문서 실측 (열린 질문 — 가정 금지).
        csnap = db.document(f"reference/{mid}/versions/{CANDIDATE}").get()
        cand: dict = {"docExists": bool(getattr(csnap, "exists", False))}
        if cand["docExists"]:
            c = csnap.to_dict() or {}
            cand["anglesFrames"] = c.get("anglesFrames")
            cand["keypointReport"] = _rep_meta(c.get("keypointReport"))
            cand["referenceKeypointReport"] = _rep_meta(c.get("referenceKeypointReport"))
            cand["hasReferenceKeypointReport"] = isinstance(
                c.get("referenceKeypointReport"), dict
            ) and bool(c.get("referenceKeypointReport"))

        # get_reference_motion 이 실제로 해석하는 문서 (shadow env 미설정 상태).
        resolved = fa.get_reference_motion(mid) or {}
        ajk = top.get("anglesJointKeys")

        rows.append({
            "motion": mid,
            "activeVersion": top.get("activeVersion"),
            "anglesFrames": top.get("anglesFrames"),
            "anglesJointKeysLen": len(ajk) if isinstance(ajk, list) else None,
            "kpFps": kp["fps"], "kpFrames": kp["frames"], "kpJoints": kp["joints"],
            "refkpFps": rkp["fps"], "refkpFrames": rkp["frames"], "refkpJoints": rkp["joints"],
            "scoringHash": _release_doc_hash(top),
            "resolvedAnglesFrames": resolved.get("anglesFrames"),
            "resolvedKpFps": _rep_meta(resolved.get("keypointReport"))["fps"],
            "candidate": cand,
            # 파생 — 현행 배율 왜곡 (rep9_n vs ref_video_n)
            "refkpRep9N": _rep9_n(rkp),
            "anglesRep9N": (
                round(top["anglesFrames"] * 9.0 / kp["fps"], 3)
                if top.get("anglesFrames") and kp["fps"] else None
            ),
        })

    payload = {"release": release, "candidateVersion": CANDIDATE, "motions": rows}
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    # stderr 표 (사람이 읽는 판정용).
    print(f"reference/_release exists={rel_exists} activeCandidate={release['activeCandidate']!r}",
          file=sys.stderr)
    hdr = (f"{'motion':<24}{'activeVer':<18}{'aFrames':>8}{'refkp fps/fr/J':>20}"
           f"{'kp fps/fr/J':>18}{'hash':>18}{'candRefkp fps/fr/J':>22}")
    print(hdr, file=sys.stderr)
    for r in rows:
        c = r.get("candidate", {}).get("referenceKeypointReport") or {}
        print(
            f"{r['motion']:<24}{str(r.get('activeVersion')):<18}{str(r.get('anglesFrames')):>8}"
            f"{str(r.get('refkpFps'))+'/'+str(r.get('refkpFrames'))+'/'+str(r.get('refkpJoints')):>20}"
            f"{str(r.get('kpFps'))+'/'+str(r.get('kpFrames'))+'/'+str(r.get('kpJoints')):>18}"
            f"{str(r.get('scoringHash')):>18}"
            f"{str(c.get('fps'))+'/'+str(c.get('frames'))+'/'+str(c.get('joints')):>22}",
            file=sys.stderr,
        )
    print(f"\n→ {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
