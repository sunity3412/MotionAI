"""Phase 34 재채점 하네스 (quick-260808-r82) — 7 doc 로컬 재채점 + 점수 이동 회계.

수술 ②(측정창 ref-경계 마진 제외)의 before/after 를 같은 입력·같은 배선으로 재채점해
회계 표를 만든다. 순수 계층만 사용(sunity_shared.analysis 직접 import — pipeline
app.py import 불요). 네트워크는 --fetch(1회, **read-only**) 뿐.

배선 동일성: `_deviation_against`(pipeline app.py 4880) 와 같은 순서 —
  reshape(flat -> (T,J)) -> motion_dtw(feature_vector(user), feature_vector(ref))
  -> per_joint_deviation(path, user_seg, a_ref_win) + per_joint_representative_frames.
ref_boundary 는 항상 None — 7 doc 전부 단일 기술(콤보 아님, doc referenceMotionId 로
확인: ref-elbow-twist-sister/ref-power-spin/ref-kip-up/ref-pdshape/ref-peter-pan).

서브커맨드:
  --fetch  7 doc 의 referenceMotionId 수집(중복 제거) → Firestore `reference/{id}`
           top-level 필드(angles/anglesJointKeys/anglesFrames/keypointReport.fps/
           joints3d/joints3dKeys/joints3dFrames — Wave 5 top-level mirror)를 1회 조회
           → data/reference_angles/{id}.json 캐시(재현성 박제, 커밋 대상).
           인증 = repo 루트 firebase-sa.json. **Firestore 는 읽기 전용 — 쓰기 0.**
  --run    각 doc 재채점. per_joint_deviation 이 ref_fps 파라미터를 지원하면(수술 후)
           캐시된 keypointReport.fps 를 전달해 rescore_after.json, 미지원(수술 전
           HEAD)이면 rescore_before.json 을 쓴다 — 같은 하네스가 양쪽 HEAD 에서 동작.
  --diff   before/after 대조 → rescore_diff.md 회계 표 + **불변식 1 전건 검사**
           (after 대표 프레임이 제외-전용 스텝 user 프레임 집합 밖 — 위반 시 exit 1).
  --side   수술 ③ 관측: doc 별 user/ref 그립 판별(std 비·유효 프레임 관측 표) +
           발동 doc 의 팔만 스왑 vs 팔+다리 스왑 편차 비교 → side_report.md.

회계 단위(오케스트레이터 검수분): md(관절별 편차) diff 가 1차. deduction_engine.tally
재실행은 입력 재구성(profile/recognizer/vision 컨텍스트/quantification 전체)이 순수
계층 범위를 넘어 과도 — 편차→over(tol 20° 초과분) 환산 열로 갈음하고 그 사실을 표
하단에 명시한다.
"""
from __future__ import annotations

import argparse
import inspect
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT / "shared" / "python"))

import numpy as np  # noqa: E402

# 7 doc 슬롯 (.planning/phases/35-server-rendered-comparison-video/data/README.md).
DOC_SLOTS = (
    "elbow", "powerspin", "kipup", "pdshapefault", "peterpan", "pdshape", "realupload",
)
# 캐시할 reference top-level 필드 (Wave 5 top-level mirror 11필드의 소비 부분집합).
REF_FIELDS = (
    "angles", "anglesJointKeys", "anglesFrames",
    "joints3d", "joints3dKeys", "joints3dFrames",
)
# 학생 각도 축 fps — frame_extractor 9fps (doc top-level angles 계약). 프로덕션은
# _pipeline_frame_fps() 단일 출처를 쓰고, 하네스는 표시 환산(rep_video_sec)에만 쓴다.
USER_ANGLES_FPS = 9.0


def _load_doc(data_dir: Path, slot: str) -> dict:
    return json.loads((data_dir / slot / "doc.json").read_text(encoding="utf-8"))


def _reshape_flat(flat, num_cols: int) -> np.ndarray:
    a = np.asarray(flat, dtype=float)
    if a.ndim == 1:
        a = a.reshape(-1, num_cols)
    return a


# ── --fetch ──────────────────────────────────────────────────────────────────

def cmd_fetch(data_dir: Path, out_dir: Path) -> int:
    """reference/{id} top-level 1회 조회 → 캐시 JSON. Firestore 읽기 전용."""
    motion_ids: list[str] = []
    for slot in DOC_SLOTS:
        mid = _load_doc(data_dir, slot).get("referenceMotionId")
        if mid and mid not in motion_ids:
            motion_ids.append(mid)
    print(f"reference ids ({len(motion_ids)}): {motion_ids}")

    import firebase_admin
    from firebase_admin import credentials, firestore

    sa_path = REPO_ROOT / "firebase-sa.json"
    if not sa_path.exists():
        print(f"ERROR: 서비스 계정 없음: {sa_path}", file=sys.stderr)
        return 1
    app = firebase_admin.initialize_app(
        credentials.Certificate(str(sa_path)), name="phase34-rescore-fetch"
    )
    db = firestore.client(app)

    cache_dir = out_dir / "reference_angles"
    cache_dir.mkdir(parents=True, exist_ok=True)
    rc = 0
    for mid in motion_ids:
        snap = db.document(f"reference/{mid}").get()  # read-only — 쓰기 0
        if not snap.exists:
            print(f"ERROR: reference/{mid} 문서 부재", file=sys.stderr)
            rc = 1
            continue
        doc = snap.to_dict() or {}
        present = {f: (f in doc and doc[f] is not None) for f in REF_FIELDS}
        kr = doc.get("keypointReport") or {}
        kr_fps = kr.get("fps") if isinstance(kr, dict) else None
        present["keypointReport.fps"] = kr_fps is not None
        # angles 는 재채점의 하드 요건 — 부재면 실패.
        if not present["angles"]:
            print(f"ERROR: reference/{mid} top-level angles 결측", file=sys.stderr)
            rc = 1
            continue
        j3 = doc.get("joints3d")
        payload = {
            "motionId": mid,
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "fieldsPresent": present,
            # angles 는 재채점 substrate — 전정밀도 유지 (반올림 금지).
            "angles": list(doc["angles"]),
            "anglesJointKeys": doc.get("anglesJointKeys"),
            "anglesFrames": doc.get("anglesFrames"),
            "keypointReportFps": float(kr_fps) if kr_fps is not None else None,
            # joints3d 는 그립 판별 관측용 — 4dp 반올림(0.1mm)로 캐시 슬림.
            "joints3d": (
                [round(float(v), 4) for v in j3] if isinstance(j3, list) else None
            ),
            "joints3dKeys": doc.get("joints3dKeys"),
            "joints3dFrames": doc.get("joints3dFrames"),
        }
        out_path = cache_dir / f"{mid}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        print(
            f"cached {mid}: anglesFrames={payload['anglesFrames']} "
            f"kpFps={payload['keypointReportFps']} "
            f"missing={[f for f, ok in present.items() if not ok]}"
        )
    return rc


# ── --run ────────────────────────────────────────────────────────────────────

def _keep_floor(n_path: int) -> int:
    """fail-open 하한 — motiondtw 수술 ②와 동일식 (max(3, ceil(0.5*len(path))))."""
    return max(3, int(math.ceil(0.5 * n_path)))


def cmd_run(data_dir: Path, out_dir: Path) -> int:
    from sunity_shared.analysis import motiondtw
    from sunity_shared.analysis.features import feature_vector
    from sunity_shared.analysis.motiondtw import (
        motion_dtw,
        per_joint_deviation,
        per_joint_representative_frames,
    )

    supports_ref_fps = (
        "ref_fps" in inspect.signature(per_joint_deviation).parameters
    )
    label = "after" if supports_ref_fps else "before"
    print(f"rescore mode = {label} (per_joint_deviation ref_fps 지원={supports_ref_fps})")

    docs_out: dict = {}
    for slot in DOC_SLOTS:
        doc = _load_doc(data_dir, slot)
        joint_keys = list(doc.get("anglesJointKeys") or [])
        user = _reshape_flat(doc["angles"], len(joint_keys))
        mid = doc.get("referenceMotionId")
        cache_path = out_dir / "reference_angles" / f"{mid}.json"
        if not cache_path.exists():
            print(f"ERROR: 캐시 부재 {cache_path} — --fetch 선행 필요", file=sys.stderr)
            return 1
        ref_cache = json.loads(cache_path.read_text(encoding="utf-8"))
        ref_keys = list(ref_cache.get("anglesJointKeys") or joint_keys)
        a_ref = _reshape_flat(ref_cache["angles"], len(ref_keys))
        ref_fps = ref_cache.get("keypointReportFps")

        # _deviation_against 동일 배선 (ref_boundary=None — 단일 기술 7 doc).
        match = motion_dtw(feature_vector(user), feature_vector(a_ref))
        user_seg = user[match.start : match.end]
        a_ref_win = a_ref[match.ref_start : match.ref_end]
        kwargs = {}
        if supports_ref_fps and ref_fps:
            kwargs["ref_fps"] = float(ref_fps)
        dev = per_joint_deviation(match.path, user_seg, a_ref_win, **kwargs)
        reps = per_joint_representative_frames(
            match.path, user_seg, a_ref_win, int(match.start), **kwargs
        )

        n_path = len(match.path)
        mask_info = None
        if supports_ref_fps and ref_fps:
            keep = motiondtw.ref_boundary_step_mask(
                match.path, a_ref_win.shape[0], float(ref_fps)
            )
            kept = int(keep.sum())
            fail_open = kept < _keep_floor(n_path)
            excluded_user = {
                int(match.start) + int(u)
                for (u, _r), m in zip(match.path, keep) if not m
            }
            kept_user = {
                int(match.start) + int(u)
                for (u, _r), m in zip(match.path, keep) if m
            }
            mask_info = {
                "margin_frames": int(
                    math.ceil(motiondtw.REF_BOUNDARY_EXCLUDE_S * float(ref_fps))
                ),
                "n_excluded": n_path - kept,
                "n_used": n_path if fail_open else kept,
                "fail_open": fail_open,
                # 불변식 1 검사용 — 제외 스텝에만 나타나는 user 절대 프레임 집합.
                # (겹치는 프레임은 kept 스텝이 선택 주체이므로 위반이 아니다.)
                "excluded_only_user_frames": sorted(excluded_user - kept_user),
            }

        joints: dict = {}
        for i, jk in enumerate(joint_keys):
            rep = reps.get(i)
            joints[jk] = {
                "deviation": float(dev[i]) if np.isfinite(dev[i]) else None,
                "rep_frame": int(rep) if rep is not None else None,
                "rep_video_sec": (
                    round(int(rep) / USER_ANGLES_FPS, 4) if rep is not None else None
                ),
            }
        records = (
            ((doc.get("result") or {}).get("deductionBreakdown") or {}).get("records")
            or []
        )
        docs_out[slot] = {
            "referenceMotionId": mid,
            "ref_fps": float(ref_fps) if ref_fps else None,
            "match": {
                "start": int(match.start), "end": int(match.end),
                "ref_start": int(match.ref_start), "ref_end": int(match.ref_end),
                "distance": float(match.distance), "n_path": n_path,
            },
            "mask": mask_info,
            "joints": joints,
            "doc_records": [
                {
                    "recordId": r.get("recordId"),
                    "criterion": r.get("criterion"),
                    "atVideoSec": r.get("atVideoSec"),
                }
                for r in records
                if isinstance(r, dict)
            ],
        }
        print(
            f"{slot}: n_path={n_path} "
            + (
                f"excluded={mask_info['n_excluded']} used={mask_info['n_used']} "
                f"fail_open={mask_info['fail_open']}"
                if mask_info
                else "(mask 미적용)"
            )
        )

    out_path = out_dir / f"rescore_{label}.json"
    out_path.write_text(
        json.dumps(
            {
                "label": label,
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "docs": docs_out,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"wrote {out_path}")
    return 0


# ── --diff ───────────────────────────────────────────────────────────────────

_TOL_DEG = 20.0  # 표시용 환산 상수 — kismam._IPSF_TOLERANCE_DEG 와 동일(산식 무접촉).


def _fmt(v, nd=2):
    return "-" if v is None else f"{v:.{nd}f}"


def cmd_diff(out_dir: Path) -> int:
    bpath = out_dir / "rescore_before.json"
    apath = out_dir / "rescore_after.json"
    if not bpath.exists() or not apath.exists():
        print("ERROR: before/after JSON 둘 다 필요 (--run 을 수술 전/후 각각 실행)",
              file=sys.stderr)
        return 1
    before = json.loads(bpath.read_text(encoding="utf-8"))["docs"]
    after = json.loads(apath.read_text(encoding="utf-8"))["docs"]

    lines: list[str] = []
    lines.append("# Phase 34 수술 ② 재채점 회계 표 (quick-260808-r82)")
    lines.append("")
    lines.append("측정창 ref-경계 마진 제외(REF_BOUNDARY_EXCLUDE_S=0.5s) 전/후의 관절별")
    lines.append("DTW-median 편차와 대표 프레임(측정 순간) 이동. `over` = max(0, dev-20°)")
    lines.append("(tol 20° 초과분 — 감점으로 흐르는 성분의 환산 표시, 산식 무접촉).")
    lines.append("")
    violations: list[str] = []
    for slot in DOC_SLOTS:
        b = before.get(slot)
        a = after.get(slot)
        if not b or not a:
            continue
        mask = a.get("mask") or {}
        lines.append(f"## {slot} (ref={a.get('referenceMotionId')}, ref_fps={a.get('ref_fps')})")
        lines.append("")
        lines.append(
            f"- n_path={a['match']['n_path']} margin={mask.get('margin_frames')}f "
            f"n_excluded={mask.get('n_excluded')} n_used={mask.get('n_used')} "
            f"fail_open={mask.get('fail_open')}"
        )
        lines.append("")
        lines.append(
            "| joint | dev_before | dev_after | delta | over_before | over_after "
            "| rep_frame before -> after | rep_sec before -> after |"
        )
        lines.append("|---|---|---|---|---|---|---|---|")
        excluded_only = set(mask.get("excluded_only_user_frames") or [])
        for jk, jb in b["joints"].items():
            ja = a["joints"].get(jk) or {}
            db_, da_ = jb.get("deviation"), ja.get("deviation")
            delta = (da_ - db_) if (db_ is not None and da_ is not None) else None
            ob = max(0.0, db_ - _TOL_DEG) if db_ is not None else None
            oa = max(0.0, da_ - _TOL_DEG) if da_ is not None else None
            rb, ra = jb.get("rep_frame"), ja.get("rep_frame")
            moved = " <- 이동" if (rb is not None and ra is not None and rb != ra) else ""
            lines.append(
                f"| {jk} | {_fmt(db_)} | {_fmt(da_)} | {_fmt(delta, 2)} "
                f"| {_fmt(ob)} | {_fmt(oa)} "
                f"| {rb} -> {ra}{moved} "
                f"| {_fmt(jb.get('rep_video_sec'))} -> {_fmt(ja.get('rep_video_sec'))} |"
            )
            # 불변식 1 — after 대표 프레임이 제외-전용 스텝 user 프레임 집합 밖.
            if ra is not None and int(ra) in excluded_only:
                violations.append(
                    f"{slot}/{jk}: rep_frame {ra} 가 제외-전용 user 프레임 집합 내"
                )
        # doc 기존 record 대조 (같은 관절의 atVideoSec 참고).
        recs = a.get("doc_records") or []
        if recs:
            lines.append("")
            lines.append("기존 doc records (대조용):")
            for r in recs:
                lines.append(
                    f"- {r.get('recordId')} atVideoSec={r.get('atVideoSec')}"
                )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("회계 단위 주석: 이 표는 md(관절별 편차, DTW-fallback 경로 "
                 "`angle_vs_reference__*` seed) 레벨의 1차 회계다. "
                 "deduction_engine.tally 재실행(record/final 레벨)은 입력 재구성"
                 "(profile/recognizer/vision 컨텍스트/quantification 전체)이 순수 계층 "
                 "범위를 넘어 생략하고, 편차→over(tol 20° 초과분) 환산 열로 갈음했다. "
                 "vision-pointed 관절의 window-median(wm) 경로는 이번 수술 무접촉이라 "
                 "이 표의 delta 가 그 관절의 최종 record 에 그대로 반영되지 않을 수 있다.")
    lines.append("")
    if violations:
        lines.append("## 불변식 1 위반")
        lines.extend(f"- {v}" for v in violations)
    else:
        lines.append("## 불변식 1 전건 검사: PASS "
                     "(after 대표 프레임 전건이 제외-전용 스텝 프레임 집합 밖)")
    lines.append("")

    diff_path = out_dir / "rescore_diff.md"
    diff_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {diff_path}")
    if violations:
        for v in violations:
            print(f"불변식 1 위반: {v}", file=sys.stderr)
        return 1
    print("불변식 1 전건 검사 PASS")
    return 0


# ── --side ───────────────────────────────────────────────────────────────────

def _joints3d_from(doc_like: dict, keys_field: str = "joints3dKeys") -> tuple:
    """(flat joints3d, keys) → (T,17,3) 배열. 부재 = (None, None)."""
    flat = doc_like.get("joints3d")
    keys = doc_like.get(keys_field)
    if not isinstance(flat, list) or not flat or not keys:
        return None, None
    arr = np.asarray(flat, dtype=float).reshape(-1, len(keys), 3)
    return arr, list(keys)


def cmd_side(data_dir: Path, out_dir: Path) -> int:
    from sunity_shared.analysis import side_match
    from sunity_shared.analysis.features import feature_vector
    from sunity_shared.analysis.motiondtw import motion_dtw, per_joint_deviation

    lines: list[str] = []
    lines.append("# Phase 34 수술 ③ side_match 관측 표 (quick-260808-r82)")
    lines.append("")
    lines.append("| doc | user_grip | user_ratio | user_valid(L/R) "
                 "| ref_grip | ref_ratio | ref_valid(L/R) | 발동 |")
    lines.append("|---|---|---|---|---|---|---|---|")

    fired: list[tuple[str, dict, np.ndarray, np.ndarray, list]] = []
    for slot in DOC_SLOTS:
        doc = _load_doc(data_dir, slot)
        result = doc.get("result") or {}
        u_arr, u_keys = _joints3d_from(result)
        mid = doc.get("referenceMotionId")
        ref_cache = json.loads(
            (out_dir / "reference_angles" / f"{mid}.json").read_text(encoding="utf-8")
        )
        r_arr, r_keys = _joints3d_from(ref_cache)

        u_diag: dict = {}
        r_diag: dict = {}
        u_side = (
            side_match.grip_side(u_arr, u_keys, debug_out=u_diag)
            if u_arr is not None else None
        )
        r_side = (
            side_match.grip_side(r_arr, r_keys, debug_out=r_diag)
            if r_arr is not None else None
        )
        fire = u_side is not None and r_side is not None and u_side != r_side

        def _ratio(d):
            v = d.get("std_ratio")
            return "-" if v is None else f"{v:.2f}"

        def _valid(d):
            lv, rv = d.get("valid_left"), d.get("valid_right")
            return f"{lv}/{rv}" if lv is not None else "-"

        lines.append(
            f"| {slot} | {u_side} | {_ratio(u_diag)} | {_valid(u_diag)} "
            f"| {r_side} | {_ratio(r_diag)} | {_valid(r_diag)} "
            f"| {'발동' if fire else '미발동'} |"
        )
        if fire:
            joint_keys = list(doc.get("anglesJointKeys") or [])
            user = _reshape_flat(doc["angles"], len(joint_keys))
            a_ref = _reshape_flat(
                ref_cache["angles"], len(ref_cache.get("anglesJointKeys") or joint_keys)
            )
            fired.append((slot, ref_cache, user, a_ref, joint_keys))

    lines.append("")
    # 발동 doc — 팔만 스왑 vs 팔+다리 스왑 편차 비교 (다리 확장 여부의 실측 근거).
    for slot, ref_cache, user, a_ref, joint_keys in fired:
        lines.append(f"## {slot} — 스왑 편차 비교 (base vs 팔만 vs 팔+다리)")
        lines.append("")
        ref_fps = ref_cache.get("keypointReportFps")
        variants = {
            "base(무스왑)": a_ref,
            "팔만 스왑": side_match.swap_lr_arm_columns(a_ref, tuple(joint_keys)),
            "팔+다리 스왑": side_match._swap_columns(
                a_ref, tuple(joint_keys),
                side_match.ARM_LR_PAIRS + side_match.LEG_LR_PAIRS,
            ),
        }
        rows: dict[str, dict[str, float]] = {}
        for name, ref_v in variants.items():
            match = motion_dtw(feature_vector(user), feature_vector(ref_v))
            seg = user[match.start : match.end]
            win = ref_v[match.ref_start : match.ref_end]
            kwargs = {}
            if ref_fps and "ref_fps" in inspect.signature(per_joint_deviation).parameters:
                kwargs["ref_fps"] = float(ref_fps)
            dev = per_joint_deviation(match.path, seg, win, **kwargs)
            rows[name] = {jk: float(dev[i]) for i, jk in enumerate(joint_keys)}
        lines.append("| joint | " + " | ".join(variants.keys()) + " |")
        lines.append("|---|" + "---|" * len(variants))
        for jk in joint_keys:
            lines.append(
                f"| {jk} | " + " | ".join(_fmt(rows[n].get(jk)) for n in variants) + " |"
            )
        lines.append("")

    if not fired:
        lines.append("발동 doc 0건 — 스왑 편차 비교 표 없음 (전건 미발동 = byte-동일 경로).")
        lines.append("")

    side_path = out_dir / "side_report.md"
    side_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {side_path}")
    return 0


# ── main ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fetch", action="store_true")
    p.add_argument("--run", action="store_true")
    p.add_argument("--diff", action="store_true")
    p.add_argument("--side", action="store_true")
    p.add_argument(
        "--data",
        default=str(REPO_ROOT / ".planning/phases/35-server-rendered-comparison-video/data"),
    )
    p.add_argument(
        "--out",
        default=str(REPO_ROOT / ".planning/quick/260808-r82-phase-34-3/data"),
    )
    args = p.parse_args(argv)
    data_dir = Path(args.data)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rc = 0
    if args.fetch:
        rc = cmd_fetch(data_dir, out_dir) or rc
    if args.run and rc == 0:
        rc = cmd_run(data_dir, out_dir) or rc
    if args.diff and rc == 0:
        rc = cmd_diff(out_dir) or rc
    if args.side and rc == 0:
        rc = cmd_side(data_dir, out_dir) or rc
    if not (args.fetch or args.run or args.diff or args.side):
        p.print_help()
        return 2
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
