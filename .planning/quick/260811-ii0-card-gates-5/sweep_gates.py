#!/usr/bin/env python3
"""승인 5동작 게이트 스윕 (quick-260811-ii0, Task 2) — 채점·운영 코드 무접촉.

바닥 검증(승인 정지 전건 생존) + pdshape 목표 판정(왼골반 탈락·왼무릎 방출 경로).
동작 목록은 data/*/ glob (align.json + doc.json) — 하드코딩 금지 (D-41).

승인 정지의 정본 = 렌더러 probe 산출 (run_probes.sh → probes.log 의 PROBE 행).
probe 는 자동 짝 판정(피크/폴/그립/가중) + pdshapefault r01 수동 오버라이드까지
포함한, v7 승인 영상에 실제로 들어간 (ut, rt) 다 — align.json pairs 원시값이 아니다.

stages:
  python3 sweep_gates.py --stage pole      # 폴 축 검출 (동작별, 증거 PNG)
  python3 sweep_gates.py --stage approved  # 승인 정지 전건 hold+pair 게이트
  python3 sweep_gates.py --stage fresh     # pdshape fresh doc 5 record 판정 + 방출 경로
  python3 sweep_gates.py --stage eye       # 기계 눈 (pdshape 전건 + 타 동작 1건)
결과는 sweep_out/*.json 에 축적, 증거는 evidence/ 에 PNG.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_REPO / "backend" / "shared" / "python"))

import gates  # noqa: E402

DATA = _REPO / ".planning/phases/35-server-rendered-comparison-video/data"
SP = pathlib.Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "4ecaa5a2-717b-43a6-a9c5-e152a330b7a3/scratchpad"
)
OUT = _HERE / "sweep_out"
EV = _HERE / "evidence"
ACTIVE_SLOTS = None  # 판정용 활성 슬롯 = probe 에서 정지가 나온 동작 전부 (동적)

# 승인 영상 5편에 실린 슬롯 (P35 data/README.md "활성 렌더 슬롯" — 게이트 구속 대상).
# 벤치 슬롯(pdshape correct, realupload)은 정보 행으로만 다룬다.
def _active_slots() -> set[str]:
    txt = (DATA / "README.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| (\w+) \| [^|]* \| 활성 렌더 슬롯", txt, flags=re.M)
    return set(rows)


def motions() -> list[str]:
    out = []
    for d in sorted(DATA.iterdir()):
        if (d / "align.json").exists() and (d / "doc.json").exists():
            out.append(d.name)
    return out


def load_align(m: str) -> dict:
    return json.loads((DATA / m / "align.json").read_text())


def parse_probe_log(path: pathlib.Path) -> dict[str, list[dict]]:
    """probes.log → {motion: [{rid, joint, src, ut, rt}]}"""
    stops: dict[str, list[dict]] = {}
    cur = None
    for line in path.read_text().splitlines():
        mm = re.match(r"== PROBE (\w+) ==", line)
        if mm:
            cur = mm.group(1)
            stops[cur] = []
            continue
        mp = re.match(
            r"PROBE (r\d+) joint=(\S+) src=(\S+) ut=([\d.]+) rt=([\d.]+)", line)
        if mp and cur:
            stops[cur].append({
                "rid": mp.group(1), "joint": mp.group(2), "src": mp.group(3),
                "ut": float(mp.group(4)), "rt": float(mp.group(5)),
            })
    return stops


def crit_joint(joint_or_crit: str) -> str:
    """게이트가 잴 각도 축. 벌림 계열(criterion 이름 그대로 옴)은 split 벌림각."""
    if joint_or_crit in ("split_angle", "leg_extension"):
        return "split"
    return joint_or_crit


# ── 프레임 접근 (render probe 가 추출한 30fps 1080p jpg 재사용) ───────────────

def render_frames_dir(m: str, side: str) -> pathlib.Path:
    tag = "u30_1080" if side == "user" else "r30_1080"
    return SP / "p35" / m / "render" / tag


def frame_at_30(m: str, side: str, sec: float) -> np.ndarray | None:
    d = render_frames_dir(m, side)
    n = len(list(d.glob("*.jpg")))
    if n == 0:
        return None
    idx = max(1, min(n, round(sec * 30.0) + 1))
    return np.asarray(Image.open(d / f"{idx:05d}.jpg").convert("RGB"))


def sample_frames_30(m: str, side: str, k: int = 48) -> np.ndarray | None:
    d = render_frames_dir(m, side)
    files = sorted(d.glob("*.jpg"))
    if not files:
        return None
    sel = np.linspace(0, len(files) - 1, min(k, len(files))).astype(int)
    return np.stack([np.asarray(Image.open(files[i]).convert("RGB")) for i in sel])


# ── stage: pole ──────────────────────────────────────────────────────────────

def stage_pole() -> dict:
    """동작×(user|ref) 폴 축 검출 + 증거 PNG (배경 중앙값 위 축선 오버레이)."""
    res: dict[str, dict] = {}
    for m in motions():
        res[m] = {}
        for side in ("user", "ref"):
            frames = sample_frames_30(m, side)
            if frames is None:
                res[m][side] = None
                print(f"{m}/{side}: 프레임 없음 (probe 미실행?)")
                continue
            pole = gates.detect_pole_x(frames)
            if pole is None:
                res[m][side] = None
                print(f"{m}/{side}: 폴 미검출")
                continue
            res[m][side] = {"x_norm": pole.x_norm, "coverage": pole.coverage,
                            "width_px": pole.width_px}
            print(f"{m}/{side}: pole x={pole.x_norm:.3f} cov={pole.coverage:.2f}")
            med = np.median(frames.astype(np.float32), axis=0).astype(np.uint8)
            img = Image.fromarray(med)
            dr = ImageDraw.Draw(img)
            x = pole.x_norm * (img.width - 1)
            dr.line([(x, 0), (x, img.height)], fill=(255, 75, 51), width=3)
            img.save(EV / f"pole_{m}_{side}.png")
    (OUT / "poles.json").write_text(json.dumps(res, indent=1))
    return res


# ── stage: approved (바닥 검증) ──────────────────────────────────────────────

def _gate_stop(align: dict, ut: float, rt: float, joint: str,
               poles: dict, m: str, tuning: dict) -> dict:
    afps = float(align["fps"])
    urep = gates.align_to_report(align, "user")
    has_ref = "refKp" in align
    rrep = gates.align_to_report(align, "ref") if has_ref else None
    # 렌더러 [clamp] 미러 — 순간이 영상 끝을 넘는 record(피터팬 6.44s vs 6.07s)는
    # 마지막 재생 프레임으로 클램프된 정지가 실제 승인 화면이다.
    u_idx = min(round(ut * afps), int(urep["frames"]) - 1)
    r_idx = round(rt * afps)
    if rrep is not None:
        r_idx = min(r_idx, int(rrep["frames"]) - 1)
    gj = crit_joint(joint)
    hold = gates.hold_gate(urep, u_idx, gj, **tuning.get("hold", {}))
    row: dict = {
        "motion": m, "joint": joint, "ut": ut, "rt": rt,
        "hold_pass": hold.passed, "hold_speed": hold.speed_dps,
        "hold_n": hold.n_samples, "hold_reason": hold.reason,
    }
    if rrep is None:
        row.update({"pair_pass": None, "pair_reason": "ref_kp_absent"})
        return row
    pm = (poles.get(m) or {})
    pu = (pm.get("user") or {}).get("x_norm")
    pr = (pm.get("ref") or {}).get("x_norm")
    usize = tuple(align["userSize"])
    rsize = tuple(align["refSize"])
    ut_px = gates.torso_px_median(urep, usize)
    rt_px = gates.torso_px_median(rrep, rsize)
    pair = gates.pair_gate(urep, u_idx, rrep, r_idx, pu, pr,
                           user_size=usize, ref_size=rsize,
                           user_torso_px=ut_px, ref_torso_px=rt_px,
                           **tuning.get("pair", {}))
    row.update({
        "pair_pass": pair.passed, "pair_reason": pair.reason,
        "pose_dist": pair.pose_dist, "basis_k": pair.basis_k,
        "pole_user": pair.pole_user, "pole_ref": pair.pole_ref,
        "pole_diff": pair.pole_diff,
    })
    return row


def stage_approved(tuning: dict, tag: str) -> list[dict]:
    poles = json.loads((OUT / "poles.json").read_text())
    stops = parse_probe_log(SP / "probes.log")
    active = _active_slots()
    rows = []
    for m in motions():
        align = load_align(m)
        for st in stops.get(m, []):
            row = _gate_stop(align, st["ut"], st["rt"], st["joint"], poles, m, tuning)
            # 게이트 적용 범위 (구조 기반 — 동작명 아님): src=align-peak 는 벌림
            # 절정 표시 정지다. 성립 축이 "argmax 피크"(렌더러가 이미 강제)라
            # 홀드·포즈 parity 의 판정 대상이 아니다 — 실측: 파워스핀 절정은
            # 회전 중이라 428도/초, 가위스플릿 힙은 각자 절정 짝이라 포즈거리
            # 1.41 이 정당하다. 수치는 정보로 박제하되 바닥 검증 구속에서 제외.
            scope = "peak" if st["src"] == "align-peak" else "joint"
            row.update({"rid": st["rid"], "src": st["src"], "scope": scope,
                        "binding": (m in active) and scope == "joint"})
            rows.append(row)
            hp = "PASS" if row["hold_pass"] else "FAIL"
            pp = ("PASS" if row["pair_pass"] else
                  ("n/a" if row["pair_pass"] is None else "FAIL"))
            sp = (f"{row['hold_speed']:.0f}d/s" if row["hold_speed"] is not None
                  else "unmeas")
            pd = (f"{row['pose_dist']:.2f}" if row.get("pose_dist") is not None
                  else "-")
            pdf = (f"{row['pole_diff']:.2f}" if row.get("pole_diff") is not None
                   else "-")
            note = "" if row["binding"] else (
                " (peak-비구속)" if scope == "peak" else " (bench)")
            print(f"{m} {st['rid']} {st['joint']:<18} hold={hp}({sp} n={row['hold_n']})"
                  f" pair={pp}(d={pd} k={row.get('basis_k','-')} poleDiff={pdf})"
                  f" src={st['src']}{note}")
    (OUT / f"approved_{tag}.json").write_text(
        json.dumps({"tuning": tuning, "rows": rows}, indent=1))
    binding = [r for r in rows if r["binding"]]
    n_hold = sum(1 for r in binding if r["hold_pass"])
    n_pair = sum(1 for r in binding if r["pair_pass"])
    print(f"\n[binding(joint-scope) {len(binding)} stops] hold {n_hold}/{len(binding)}"
          f"  pair {n_pair}/{len(binding)}")
    return rows


# ── stage: fresh (pdshape 목표 판정) ─────────────────────────────────────────
#
# 판정 트랙 = pdshapefault align.json (15fps RTMW17, 타임베이스 정본). fresh 영상은
# pdshapefault 슬롯과 동일 원본(md5 일치 08-08 실증)이므로 같은 트랙이 적용된다.
# doc keypointReport 는 fps 라벨 오차(라벨 18 vs 실효 20.1 실측)와 12관절 제약이
# 있어 게이트 판정 트랙으로 쓰지 않는다 — record 의 atVideoSec(9.997fps 보정 세대,
# 실초)만 가져와 align 인덱스(×15)로 환산한다.

def _fresh_align():
    align = load_align("pdshapefault")
    urep = gates.align_to_report(align, "user")
    rrep = gates.align_to_report(align, "ref")
    recs = json.loads((SP / "fresh_records.json").read_text())["records"]
    return align, urep, rrep, recs


def _hold_mask(rep: dict, joint: str, tuning: dict) -> dict[int, gates.HoldResult]:
    out = {}
    for f in range(int(rep["frames"])):
        out[f] = gates.hold_gate(rep, f, joint, **tuning.get("hold", {}))
    return out


def stage_fresh(tuning: dict) -> dict:
    """fresh doc 5 record 에 게이트 → 기대: 왼골반 탈락(전환) + 왼무릎 방출 경로."""
    align, urep, rrep, recs = _fresh_align()
    afps = float(align["fps"])
    poles = json.loads((OUT / "poles.json").read_text())
    pm = poles.get("pdshapefault") or {}
    pu = (pm.get("user") or {}).get("x_norm")
    pr = (pm.get("ref") or {}).get("x_norm")
    usize, rsize = tuple(align["userSize"]), tuple(align["refSize"])
    ut_px = gates.torso_px_median(urep, usize)
    rt_px = gates.torso_px_median(rrep, rsize)

    rows = []
    for r in recs:
        joint = crit_joint(r["criterion"].split("__")[-1])
        u_idx = round(float(r["atVideoSec"]) * afps)
        hold = gates.hold_gate(urep, u_idx, joint, **tuning.get("hold", {}))
        rows.append({
            "recordId": r["recordId"], "joint": joint,
            "atVideoSec": r["atVideoSec"], "align_idx": u_idx,
            "dev": r["deviation"],
            "hold_pass": hold.passed, "hold_speed": hold.speed_dps,
            "hold_n": hold.n_samples, "hold_reason": hold.reason,
            "window_speeds": hold.window_speeds,
            "window_angles": hold.angles,
        })
        sp = f"{hold.speed_dps:.0f}d/s" if hold.speed_dps is not None else "unmeas"
        print(f"fresh {r['recordId']:<44} hold={'PASS' if hold.passed else 'FAIL'}"
              f"({sp} n={hold.n_samples}) win={hold.window_speeds} dev={r['deviation']}")

    # ── 왼무릎 방출 경로: 홀드 구간 탐색 → 짝 성립 → 편차 성립 ──
    knee = "left_knee"
    tol = next((float(r.get("tolerance") or 20.0) for r in recs
                if r["criterion"].endswith(knee)), 20.0)
    u_holds = {f: h for f, h in _hold_mask(urep, knee, tuning).items() if h.passed}
    r_holds = {f: h for f, h in _hold_mask(rrep, knee, tuning).items() if h.passed}
    print(f"\n[knee-path] user 홀드 프레임 {len(u_holds)}개, ref 홀드 프레임 {len(r_holds)}개"
          f" (tol={tol}도)")

    def _ang(rep, f):
        return gates.joint_angle(rep, f, knee)

    # user 접힘 홀드(각도 낮음) 후보 — 홀드 프레임 중 각도 오름차순
    u_cand = sorted(((f, a) for f in u_holds if (a := _ang(urep, f)) is not None),
                    key=lambda t: t[1])
    # ref 신전 홀드 후보 — 각도 내림차순
    r_cand = sorted(((f, a) for f in r_holds if (a := _ang(rrep, f)) is not None),
                    key=lambda t: -t[1])
    path, rejected = None, []
    for uf_i, ua in u_cand[:60]:
        for rf_i, ra in r_cand[:60]:
            if ra - ua < tol:
                continue  # 편차가 허용오차 미만 — 감점 주장 성립 안 함
            pair = gates.pair_gate(urep, uf_i, rrep, rf_i, pu, pr,
                                   user_size=usize, ref_size=rsize,
                                   user_torso_px=ut_px, ref_torso_px=rt_px,
                                   **tuning.get("pair", {}))
            cand = {"u_idx": uf_i, "r_idx": rf_i,
                    "u_sec": uf_i / afps, "r_sec": rf_i / afps,
                    "u_angle": ua, "r_angle": ra, "deficit": ra - ua,
                    "pose_dist": pair.pose_dist, "basis_k": pair.basis_k,
                    "pole_diff": pair.pole_diff, "pair_reason": pair.reason}
            if pair.passed:
                path = cand
                break
            if len(rejected) < 8:
                rejected.append(cand)
        if path:
            break
    if path:
        print(f"[knee-path] 성립: user {path['u_sec']:.2f}s({path['u_angle']:.0f}도)"
              f" vs ref {path['r_sec']:.2f}s({path['r_angle']:.0f}도)"
              f" deficit={path['deficit']:.0f}도 poseD={path['pose_dist']:.2f}"
              f" poleDiff={'-' if path['pole_diff'] is None else round(path['pole_diff'], 2)}")
        for side, sec, tagn in (("user", path["u_sec"], "u"),
                                ("ref", path["r_sec"], "r")):
            fr = frame_at_30("pdshapefault", side, sec)
            if fr is not None:
                Image.fromarray(fr).save(EV / f"kneepath_{tagn}_{sec:.2f}s.png")
    else:
        print("[knee-path] 성립 실패 — 게이트 통과 짝 없음 (기각 후보를 박제)")
        for c in rejected:
            print(f"   기각: u{c['u_sec']:.2f}s({c['u_angle']:.0f}도)"
                  f" r{c['r_sec']:.2f}s({c['r_angle']:.0f}도)"
                  f" d={c['pose_dist']} reason={c['pair_reason']}")
    out = {"records": rows, "knee_path": path, "knee_rejected": rejected,
           "u_hold_frames": sorted(u_holds), "r_hold_frames": sorted(r_holds)}
    (OUT / "fresh.json").write_text(json.dumps(out, indent=1))
    return out


# ── stage: eye (기계 눈 — pdshape 전건 + 타 동작 1건) ────────────────────────

def _track_claim(angle: float | None) -> str | None:
    """트랙 각도 → 기계 눈에 물을 주장. 중간각(100~150)은 판정 대상 아님."""
    if angle is None:
        return None
    if angle <= 100.0:
        return "bent"
    if angle >= 150.0:
        return "extended"
    return None


def stage_eye(sample_motion: str | None) -> list[dict]:
    """기계 눈 — pdshape 전건(fresh 5 record + 무릎 경로 짝) + 타 동작 1건 (비용 상한).

    프레임 = probe 30fps 1080p 추출본 (실초 좌표계), 트랙 = align 15fps.
    claim = 트랙 각도에서 유도 (bent<=100 / extended>=150) — 중간각은 굽힘/폄
    이분 판정의 대상이 아니므로 제외 (정직한 침묵).
    """
    key = (SP / "gemini_key.txt").read_text().strip()
    results = []

    def _run(tag: str, motion: str, side: str, rep: dict, idx: int, joint: str):
        afps = float(rep.get("fps") or 15.0)
        sec = idx / afps
        frame = frame_at_30(motion, side, sec)
        if frame is None:
            print(f"eye {tag:<34} 프레임 없음")
            results.append({"tag": tag, "observed": None, "match": None,
                            "note": "frame_missing"})
            return
        H, W = frame.shape[:2]
        ang = gates.joint_angle(rep, idx, joint, conf_min=0.0)
        claim = _track_claim(ang)
        xy = gates.kp(rep, idx, joint, conf_min=0.0)
        row = {"tag": tag, "joint": joint, "align_idx": idx, "sec": round(sec, 2),
               "track_angle": ang, "claim": claim}
        if claim is None or xy is None:
            row.update({"observed": None, "match": None,
                        "note": "중간각/좌표없음 — 기계 눈 이분 판정 대상 아님"})
            results.append(row)
            print(f"eye {tag:<34} angle={ang if ang is None else round(ang)} → 판정 대상 아님")
            return
        res = gates.machine_eye(frame, (xy[0] * W, xy[1] * H), claim,
                                api_key=key, crop_px=max(320, W // 2))
        res["crop"].save(EV / f"eye_{tag}.png")
        row.update({"observed": res["observed"], "match": res["match"],
                    "confidence": res["confidence"], "reason": res["reason"]})
        results.append(row)
        print(f"eye {tag:<34} track={ang:.0f}도 claim={claim} → observed={res['observed']}"
              f" match={res['match']} conf={res['confidence']}")

    # pdshape 전건 (fresh doc 5 record, user 측 측정 순간)
    align, urep, rrep, recs = _fresh_align()
    afps = float(align["fps"])
    for r in recs:
        joint = crit_joint(r["criterion"].split("__")[-1])
        idx = round(float(r["atVideoSec"]) * afps)
        _run(f"fresh_{r['recordId'].split(':')[0]}_{joint}", "pdshapefault",
             "user", urep, idx, joint)

    # 왼무릎 방출 경로 짝 (성립 시 양측)
    fresh = json.loads((OUT / "fresh.json").read_text())
    path = fresh.get("knee_path")
    if path:
        _run("kneepath_user_left_knee", "pdshapefault", "user", urep,
             path["u_idx"], "left_knee")
        _run("kneepath_ref_left_knee", "pdshapefault", "ref", rrep,
             path["r_idx"], "left_knee")

    # 타 동작 1건 표본 (비용 상한) — 승인 정지 중 무릎류 첫 건
    if sample_motion:
        stops = parse_probe_log(SP / "probes.log")
        for st in stops.get(sample_motion, []):
            if "knee" not in st["joint"]:
                continue
            salign = load_align(sample_motion)
            arep = gates.align_to_report(salign, "user")
            u_idx = round(st["ut"] * float(salign["fps"]))
            _run(f"{sample_motion}_{st['rid']}_{st['joint']}", sample_motion,
                 "user", arep, u_idx, st["joint"])
            break
    (OUT / "eye.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["pole", "approved", "fresh", "eye"])
    ap.add_argument("--tag", default="t0", help="approved 결과 파일 태그 (튜닝 이력)")
    ap.add_argument("--hold-max", type=float, default=gates.HOLD_MAX_DPS)
    ap.add_argument("--pose-max", type=float, default=gates.PAIR_POSE_MAX)
    ap.add_argument("--pole-diff-max", type=float, default=gates.POLE_DIFF_MAX)
    ap.add_argument("--eye-sample", default=None,
                    help="기계 눈 타 동작 표본 (동작 디렉터리명)")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    EV.mkdir(exist_ok=True)
    tuning = {"hold": {"max_speed_dps": args.hold_max},
              "pair": {"pose_max": args.pose_max,
                       "pole_diff_max": args.pole_diff_max}}
    if args.stage == "pole":
        stage_pole()
    elif args.stage == "approved":
        stage_approved(tuning, args.tag)
    elif args.stage == "fresh":
        stage_fresh(tuning)
    elif args.stage == "eye":
        stage_eye(args.eye_sample)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
