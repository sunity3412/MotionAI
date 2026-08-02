#!/usr/bin/env python3
"""quick-260802-tie 실 데이터 판정 — 저장 fixture 로 두 수치를 잰다.

**이 사이클이 답해야 하는 것 두 개.**

  ① tie-break 이 실 데이터에서 **몇 건이나 프레임을 바꾸는가**.
     대조군(신뢰도 미주입) vs 처리군(주입) — 처리 변수는 그것 하나뿐이다.
     0 이면 0 이라고 쓴다. 동점 후보가 몇 건이나 존재했는지도 함께 낸다
     (0건이면 "규칙이 안 걸린 것"이고, 여러 건인데 0 이면 "걸렸는데 못 이긴 것"이다 —
     둘은 다른 사실이라 구분해서 남긴다).

  ② 기준 패널 무표시(`refMarked=false`) 판정이 실 fixture 에서 **몇 장에 붙는가**.
     카드가 어느 프레임에서 잘렸느냐에 따라 답이 달라지므로 **3개 팔**로 잰다:
       A. 앵커 없음  = belle 이 07-31 doc 에서 본 그 프레임 (czw 가 재현 확인한 대조군)
       B. 앵커 있음  = quick-260801-gbk 반영 (아직 belle 에게 안 나감)
       C. 앵커 + 동점 신뢰도 = 이 사이클
     A 와 B/C 의 수를 **같은 것으로 읽으면 안 된다** — 다른 프레임의 카드다.

하네스 본체는 `backend/evals/realfixture/replay.py`(quick-260802-czw). 여기서는
그 함수를 부르기만 한다 — 재생 규칙·카드 인자 조립을 복제하지 않는다.
GPU 0 · Gemini 0 · Pod 0 · Firestore 0 (러너의 죽는 스텁 그대로).

사용법:
  backend/.venv/bin/python \\
    .planning/quick/260802-tie-frame-confidence-and-empty-ref-panel/measure_tie.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
# .planning/quick/<cycle>/ → 리포 루트는 두 단계 위.
_REPO = _HERE.parents[2]
_REPLAY = _REPO / "backend" / "evals" / "realfixture" / "replay.py"

_spec = importlib.util.spec_from_file_location("tie_replay", str(_REPLAY))
replay = importlib.util.module_from_spec(_spec)
sys.modules["tie_replay"] = replay
_spec.loader.exec_module(replay)

import numpy as np  # noqa: E402

from sunity_shared.analysis import moment  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_KEYS  # noqa: E402


def _dtw_tie_scan(replayed, conf) -> list[dict]:
    """DTW 경로의 동점 집합 크기 — "argmax 로 번지지 않았다"의 근거.

    tie-break 이 정당하려면 동점 집합이 **작아야** 한다. 창 전체가 동점이면 그것은
    사실상 argmax 다. 여기서 그 크기를 실제로 센다 — 주장이 아니라 수치로.

    산식은 `motiondtw.per_joint_representative_frames` 와 같은 재료
    (`|per-step deviation − median|`)를 쓰되, 그 함수의 반환을 재구성하지 않고
    **분포만** 본다(선택 자체는 production 이 한다).
    """
    match = replayed["match"]
    path = getattr(match, "path", None)
    if not path:
        return []
    start = int(match.start)
    seg = replayed["angles"][start:int(match.end)]
    a_ref = replayed["aRef"]
    diffs = np.empty((len(path), a_ref.shape[1]), dtype=float)
    for k, (u, r) in enumerate(path):
        diffs[k] = np.abs(seg[u] - a_ref[r])
    out: list[dict] = []
    for j, jk in enumerate(JOINT_KEYS):
        col = diffs[:, j]
        fin = np.isfinite(col)
        if not fin.any():
            continue
        med = float(np.median(col))
        if med != med:
            continue
        gaps = np.where(fin, np.abs(col - med), np.inf)
        gmin = float(gaps.min())
        exact = [i for i in range(len(gaps)) if gaps[i] <= gmin]
        tie = [i for i in range(len(gaps)) if gaps[i] - gmin <= moment.TIE_EPS]
        frames = sorted({start + int(path[i][0]) for i in tie})
        out.append({
            "joint": jk,
            "pathSteps": len(path),
            "exactTieSteps": len(exact),
            "tieSteps": len(tie),
            "tieDistinctFrames": len(frames),
            "tieFrames": frames,
            "tieSpanFrames": (max(frames) - min(frames)) if frames else 0,
            "tieConfidence": [
                (None if conf is None else conf(f, (jk,))) for f in frames
            ],
        })
    return out


def _tie_candidate_scan(app, replayed, conf) -> list[dict]:
    """pointed window 경로에서 **동점 후보가 몇 건 있었는지**를 직접 센다.

    측정 ① 의 결과가 0 일 때 그 0 이 "동점이 없었다"인지 "동점은 있었는데 신뢰도가
    못 이겼다"인지를 구분하기 위한 관측이다. 여기서 쓰는 window/median 은 저장 doc 의
    `windowMedianAngleDeltas` 그대로 — 재계산 0.
    """
    vv = (replayed["result"] or {}).get("visionVeto") or {}
    wm = vv.get("windowMedianAngleDeltas")
    if not isinstance(wm, dict):
        return []
    src = wm.get("sourceFrameIndices") or {}
    frames = [int(t) for t in (src.get("user") or ())]
    angles = replayed["angles"]
    out: list[dict] = []
    for entry in wm.get("deltas") or ():
        if not isinstance(entry, dict):
            continue
        jk = entry.get("joint")
        if jk not in JOINT_KEYS:
            continue
        try:
            sd = float(entry.get("student_deg"))
        except (TypeError, ValueError):
            continue
        if sd != sd:
            continue
        j = JOINT_KEYS.index(jk)
        cands, gaps = [], []
        for t in frames:
            if t < 0 or t >= len(angles):
                continue
            a = float(angles[t][j])
            if a != a:
                continue
            cands.append(t)
            gaps.append(abs(a - sd))
        if not gaps:
            continue
        g_min = min(gaps)
        tie = [
            (cands[i], gaps[i]) for i in range(len(gaps))
            if gaps[i] - g_min <= moment.TIE_EPS
        ]
        out.append({
            "joint": jk,
            "windowFrames": cands,
            "gaps": [round(g, 6) for g in gaps],
            "tieSize": len(tie),
            "tieFrames": [t for t, _g in tie],
            "tieConfidence": [
                (None if conf is None else conf(t, (jk,))) for t, _g in tie
            ],
        })
    return out


_SENS_H, _SENS_W = 640, 360  # 세로형 9fps/640px 장변 — 프로덕션 추출기 형상.


def _frame_size_sensitivity(app, manifest, frames_fps) -> dict:
    """프레임 기하만 바꿔 ② 를 다시 세고 답이 흔들리는지 본다 (러너 무수정)."""
    orig = replay._synthetic_frames

    def _big(n: int, seed: int):
        n = max(1, int(n))
        stack = np.zeros((n, _SENS_H, _SENS_W, 3), dtype=np.uint8)
        stack[:, :, :, :] = np.uint8(seed % 256)
        for f in range(n):
            stack[f, 0, 0, :] = np.uint8((f * 7 + seed) % 256)
        return stack

    def _count(entries) -> int:
        total = 0
        for entry in entries:
            try:
                r = replay.replay_fixture(app, entry, use_frame_confidence=True)
            except replay.Blocked:
                continue
            cs = replay.render_cards(
                app, r, replay._engrave(app, r, r["measuredAt"]), frames_fps
            )
            total += sum(1 for c in cs if c.get("refMarked") is False)
        return total

    baseline = _count(manifest["analyses"])
    replay._synthetic_frames = _big
    try:
        scaled = _count(manifest["analyses"])
    finally:
        replay._synthetic_frames = orig
    return {
        "size": f"{_SENS_H}x{_SENS_W}",
        "baseline": baseline,
        "scaled": scaled,
        "identical": baseline == scaled,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="quick-260802-tie 실 데이터 판정")
    ap.add_argument("--out", default=str(_HERE / "measure_out.json"))
    args = ap.parse_args(argv)

    manifest = replay.load_manifest()
    frames_fps = float(manifest["studentAnglesFps"])
    app = replay.load_pipeline_with_fixture_adapters(frames_fps)
    print(
        f"fixtures={len(manifest['analyses'])} studentAnglesFps={frames_fps} "
        f"TIE_EPS={moment.TIE_EPS}"
    )

    fixtures: list[dict] = []
    for entry in manifest["analyses"]:
        try:
            ctrl = replay.replay_fixture(app, entry)
            treat = replay.replay_fixture(app, entry, use_frame_confidence=True)
        except replay.Blocked as exc:
            print(f"\n== {entry['analysisId']}  BLOCKED ({exc})")
            continue
        rc = replay.recon(entry, ctrl)
        matched = set(rc["matchedCriteria"])

        # ── ① 순간 프레임이 갈렸는가 ────────────────────────────────────────
        moved: list[dict] = []
        for crit, m_ctrl in sorted(ctrl["measuredAt"].items()):
            m_treat = treat["measuredAt"].get(crit) or {}
            a, b = m_ctrl.get("frame_idx"), m_treat.get("frame_idx")
            if a != b:
                moved.append({
                    "criterion": crit, "control": a, "treatment": b,
                    "reconMatched": crit in matched,
                })
        # 순간을 가진 record 총수(분모).
        moment_count = len(ctrl["measuredAt"])

        conf = replay.frame_confidence_from_keypoint_report(
            (ctrl["result"] or {}).get("keypointReport") or {}, frames_fps
        )
        scan = _tie_candidate_scan(app, ctrl, conf)
        tie_multi = [s for s in scan if s["tieSize"] > 1]
        dtw_scan = _dtw_tie_scan(ctrl, conf)
        dtw_multi = [s for s in dtw_scan if s["tieDistinctFrames"] > 1]

        # md(점수 substrate) 무접촉 — 대조군/처리군 키·값 동등.
        md_equal = ctrl["md"].keys() == treat["md"].keys() and all(
            ctrl["md"][k] == treat["md"][k]
            for k in ctrl["md"]
            if not isinstance(ctrl["md"][k], (list, tuple))
        )
        final_equal = (ctrl["breakdown"] or {}).get("final") == (
            treat["breakdown"] or {}
        ).get("final")

        # ── ② 기준 패널 무표시 카드 ────────────────────────────────────────
        arms = {
            # A: 앵커 없음 = 저장 doc 의 카드 프레임(czw 가 REPRODUCED 로 확인).
            "A_no_anchor": replay.render_cards(
                app, ctrl, replay._engrave(app, ctrl, {}), frames_fps
            ),
            # B: 앵커 있음 = gbk 반영분.
            "B_anchor": replay.render_cards(
                app, ctrl, replay._engrave(app, ctrl, ctrl["measuredAt"]), frames_fps
            ),
            # C: 앵커 + 동점 신뢰도 = 이 사이클.
            "C_anchor_tie": replay.render_cards(
                app, treat, replay._engrave(app, treat, treat["measuredAt"]),
                frames_fps,
            ),
        }
        arm_stats = {}
        for _name, _cs in arms.items():
            _judged = [c for c in _cs if c.get("refMarked") is not None]
            _un = [c for c in _judged if c["refMarked"] is False]
            arm_stats[_name] = {
                "cardCount": len(_cs),
                "judgedCount": len(_judged),
                "unmarkedCount": len(_un),
                "unmarkedCriteria": [c.get("criterion") for c in _un],
                "frames": [c.get("userFrameIdx") for c in _cs],
            }
        cards = arms["C_anchor_tie"]
        judged_cards = [c for c in cards if c.get("refMarked") is not None]
        unmarked = [c for c in judged_cards if c["refMarked"] is False]

        fixtures.append({
            "analysisId": entry["analysisId"],
            "motionId": ctrl["motionId"],
            "reconVerdict": rc["verdict"],
            "momentRecordCount": moment_count,
            "movedCount": len(moved),
            "moved": moved,
            "tieScan": scan,
            "tieCandidateJoints": len(tie_multi),
            "dtwTieScan": dtw_scan,
            "dtwTieJoints": len(dtw_multi),
            "dtwPathSteps": dtw_scan[0]["pathSteps"] if dtw_scan else 0,
            "dtwMaxTieDistinctFrames": max(
                (s["tieDistinctFrames"] for s in dtw_scan), default=0
            ),
            "mdIdentical": bool(md_equal),
            "finalIdentical": bool(final_equal),
            "controlFinal": (ctrl["breakdown"] or {}).get("final"),
            "treatmentFinal": (treat["breakdown"] or {}).get("final"),
            "cardCount": len(cards),
            "refMarkedJudgedCount": len(judged_cards),
            "refUnmarkedCount": len(unmarked),
            "refUnmarkedCriteria": [c.get("criterion") for c in unmarked],
            "arms": arm_stats,
            "cards": [
                {
                    "criterion": c.get("criterion"),
                    "joint": c.get("joint"),
                    "tier": c.get("tier"),
                    "region": c.get("region"),
                    "refMatch": c.get("refMatch"),
                    "refMarked": c.get("refMarked"),
                    "userFrameIdx": c.get("userFrameIdx"),
                }
                for c in cards
            ],
        })

    print("\n── ① tie-break 이 실 데이터에서 프레임을 바꾼 건수 ──")
    for f in fixtures:
        print(
            f"  {f['analysisId']:34} moved={f['movedCount']}/"
            f"{f['momentRecordCount']}  동점후보(2개+) 관절={f['tieCandidateJoints']}"
            f"  md동등={f['mdIdentical']} final {f['controlFinal']}→"
            f"{f['treatmentFinal']}"
        )
        for m in f["moved"]:
            print(
                f"      {m['criterion']:38} {m['control']} → {m['treatment']}"
                f"  (recon={'O' if m['reconMatched'] else 'X'})"
            )

    print("\n── ①-b 동점 집합 크기 (argmax 로 번지지 않았다의 근거) ──")
    for f in fixtures:
        sizes = [s["tieDistinctFrames"] for s in f["dtwTieScan"]]
        print(
            f"  {f['analysisId']:34} DTW path={f['dtwPathSteps']} "
            f"(짝수={f['dtwPathSteps'] % 2 == 0}) "
            f"관절별 동점 프레임 수={sizes} 최대={f['dtwMaxTieDistinctFrames']}"
        )

    print("\n── ② 기준 패널 무표시(refMarked=false) 카드 — 3개 팔 ──")
    print("   A=앵커없음(저장 doc 프레임) · B=앵커(gbk) · C=앵커+동점신뢰도(이 사이클)")
    for f in fixtures:
        a, b, c = (f["arms"][k] for k in ("A_no_anchor", "B_anchor", "C_anchor_tie"))
        print(
            f"  {f['analysisId']:34} "
            f"A {a['unmarkedCount']}/{a['judgedCount']} · "
            f"B {b['unmarkedCount']}/{b['judgedCount']} · "
            f"C {c['unmarkedCount']}/{c['judgedCount']}"
        )
        print(f"      A frames={a['frames']} 무표시={a['unmarkedCriteria']}")
        print(f"      B frames={b['frames']} 무표시={b['unmarkedCriteria']}")
        print(f"      C frames={c['frames']} 무표시={c['unmarkedCriteria']}")

    moved_total = sum(f["movedCount"] for f in fixtures)
    moment_total = sum(f["momentRecordCount"] for f in fixtures)
    tie_total = sum(f["tieCandidateJoints"] for f in fixtures)
    unmarked_total = sum(f["refUnmarkedCount"] for f in fixtures)
    judged_total = sum(f["refMarkedJudgedCount"] for f in fixtures)
    card_total = sum(f["cardCount"] for f in fixtures)
    arm_totals = {
        k: {
            "unmarked": sum(f["arms"][k]["unmarkedCount"] for f in fixtures),
            "judged": sum(f["arms"][k]["judgedCount"] for f in fixtures),
            "cards": sum(f["arms"][k]["cardCount"] for f in fixtures),
        }
        for k in ("A_no_anchor", "B_anchor", "C_anchor_tie")
    }
    print(
        f"\n합계 ① 프레임 이동 {moved_total}/{moment_total} record "
        f"(동점 후보 보유 관절 {tie_total}건)"
    )
    for k, v in arm_totals.items():
        print(
            f"합계 ② [{k}] 기준 패널 무표시 {v['unmarked']}/{v['judged']} 카드 "
            f"(판정 대상 아닌 카드 {v['cards'] - v['judged']}장 제외)"
        )
    all_md = all(f["mdIdentical"] for f in fixtures)
    all_final = all(f["finalIdentical"] for f in fixtures)
    print(f"채점 무접촉: md 동등={all_md} · final 동등={all_final}")

    # ── ② 의 프레임 기하 민감도 — 8x8 합성 프레임이 답을 바꾸는가 ─────────────
    # crop 포함 게이트(_pt_in_crop)는 프레임 픽셀 크기에 의존한다. 합성 프레임이
    # 8x8 이라 프로덕션(9fps/640px)과 다르게 동작할 수 있다. 같은 측정을 세로형
    # 640 장변 기하로 한 번 더 돌려 답이 흔들리는지 본다. 픽셀 내용은 여전히
    # 무의미하고, 여기서 쓰는 것은 **기하**뿐이다.
    sens = _frame_size_sensitivity(app, manifest, frames_fps)
    print(
        f"프레임 기하 민감도(8x8 → {sens['size']}): "
        f"② 무표시 {sens['baseline']} → {sens['scaled']} "
        f"({'동일' if sens['identical'] else '변동'})"
    )

    payload = {
        "generatedBy": (
            ".planning/quick/260802-tie-frame-confidence-and-empty-ref-panel/"
            "measure_tie.py"
        ),
        "tieEps": moment.TIE_EPS,
        "recordValueDecimals": moment.RECORD_VALUE_DECIMALS,
        "studentAnglesFps": frames_fps,
        "fixtures": fixtures,
        "movedTotal": moved_total,
        "momentRecordTotal": moment_total,
        "tieCandidateJointTotal": tie_total,
        "refUnmarkedTotal": unmarked_total,
        "refMarkedJudgedTotal": judged_total,
        "cardTotal": card_total,
        "armTotals": arm_totals,
        "mdIdenticalAll": all_md,
        "finalIdenticalAll": all_final,
        "frameSizeSensitivity": sens,
        "limits": [
            "신뢰도 출처가 production 과 **어댑터만** 다르다 — production 은 "
            "pose_frames(9fps), 하네스는 저장 keypointReport(18fps 업샘플). 짝수 rep "
            "인덱스에서 선형보간 가중치가 0 이라 같은 표본이 복원되지만, 그 등가는 "
            "여기서 실측한 것이 아니라 upsample_to_fps 의 산식에서 온 것이다.",
            "기준 report 가 legacy 8관절이면 elbow/ankle 신뢰도를 모른다 → 그 관절의 "
            "tie-break 는 판정 불가로 미적용. 학생 report 만 신뢰도 출처로 쓴다.",
            "vision 주입 record(split_angle)와 창 의존 criterion 은 czw RECON 이 "
            "재현하지 못하는 것들이라 이 측정의 분모에도 들어오지 않는다.",
            "PNG 픽셀 내용은 판정 근거가 아니다 — 프레임 배열이 합성이다. ② 는 "
            "렌더 코드가 낸 인증값(refMarked)을 센 것이지 사진을 본 것이 아니다.",
            "② 의 세 팔은 **서로 다른 프레임의 카드**다 — A 와 B/C 의 수를 증감으로 "
            "읽지 말 것. A 만이 belle 이 07-31 doc 에서 본 프레임에 해당한다.",
            "프레임 배열이 8x8 합성이라 crop 기하에 의존하는 게이트(_pt_in_crop)는 "
            "프로덕션과 다르게 동작할 수 있다 — 아래 frameSizeSensitivity 로 확인한다.",
        ],
    }
    Path(args.out).write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    print(f"\n산출물: {args.out}")
    _ = np  # numpy 는 replay 모듈 경유로만 쓰인다(형상 확인용 import 유지)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
