"""기계 눈 회귀 하네스 (quick-260903-jxn) — jka 하네스 + `--majority` 모드.

운영 경로 그대로: 기본은 card_gates.eye_judge(단발), `--majority` 면 card_gates.eye_judge_majority
(불일치 시 최대 3회 다수결). GEMINI_API_KEY 는 env 로만, 어디에도 기록하지 않는다.
실행(리포 루트): GEMINI_API_KEY=... backend/.venv/bin/python <이 파일> [N] [--majority]
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/Users/kimtaesung/Dev/SunityMotion")
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))
from PIL import Image  # noqa: E402
from sunity_shared.analysis import card_gates as cg  # noqa: E402

EV = REPO / ".planning/quick/260903-jxn-eye-midlimb-majority/evidence"
JKA = REPO / ".planning/quick/260903-jka-eye-joint-kind/evidence"
II0 = REPO / ".planning/quick/260811-ii0-card-gates-5/evidence"
VLU = REPO / ".planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence"

# (이름, 파일, claim, joint, 기대 match — None = 보고만)
FIXTURES = [
    ("climb_occl_0902", JKA / "climb_eye_right_knee_0902.png", "bent", "right_knee", True),
    ("climb_occl_0901", VLU / "eye_crop.png", "bent", "right_knee", True),
    ("kneepath_user_markdisp", II0 / "eye_kneepath_user_left_knee.png", "bent", "left_knee", False),
    ("fresh_r00_left_elbow", II0 / "eye_fresh_r00_left_elbow.png", "bent", "left_elbow", True),
    ("fresh_r02_right_shoulder", II0 / "eye_fresh_r02_right_shoulder.png", "bent", "right_shoulder", True),
    ("elbow_r03_right_knee_ext", II0 / "eye_elbow_r03_right_knee.png", "extended", "right_knee", True),
    ("pdshape_0902_left_elbow", JKA / "pdshape_eye_left_elbow_0902.png", "bent", "left_elbow", True),
    ("pdshape_0902_left_hip", JKA / "pdshape_eye_left_hip_0902.png", "bent", "left_hip", None),
    ("fresh_r03_left_hip_transition", II0 / "eye_fresh_r03_left_hip.png", "bent", "left_hip", None),
]
args = [a for a in sys.argv[1:] if not a.startswith("--")]
N = int(args[0]) if args else 5
MAJORITY = "--majority" in sys.argv


def judge(crop, claim, key, limb, kind):
    if MAJORITY:
        return cg.eye_judge_majority(crop, claim, api_key=key, expected_limb=limb, joint_kind=kind)
    return cg.eye_judge(crop, claim, api_key=key, expected_limb=limb, joint_kind=kind)


def main() -> int:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        print("GEMINI_API_KEY 미설정")
        return 2
    ts = datetime.now(timezone.utc).isoformat()
    print(f"model={cg.DEFAULT_C_MODEL} N={N} majority={MAJORITY} ts={ts}")
    out = {"ts": ts, "model": cg.DEFAULT_C_MODEL, "n": N, "majority": MAJORITY, "fixtures": {}}
    all_ok = True
    for name, png, claim, joint, expect in FIXTURES:
        if not png.exists():
            print(f"[{name}] MISSING {png}")
            all_ok = False
            continue
        crop = Image.open(png).convert("RGB")
        limb, kind = cg.joint_limb(joint), cg.joint_kind_ko(joint)
        rounds = []
        calls = 0
        for _ in range(N):
            r = judge(crop, claim, key, limb, kind)
            calls += int(r.get("rounds", 1))
            rounds.append({k: r.get(k) for k in ("observed", "limb", "match", "confidence", "reason", "rounds")})
        c = Counter(bool(x["match"]) for x in rounds)
        ok = True if expect is None else ((c[True] == N) if expect else (c[False] == N))
        all_ok &= ok
        tag = "REPORT" if expect is None else ("PASS" if ok else "FAIL")
        print(f"== {name} claim={claim} joint={joint} expect={expect}: True={c[True]} False={c[False]} calls={calls} -> {tag}")
        out["fixtures"][name] = {"claim": claim, "joint": joint, "expect": expect, "true": c[True],
                                 "false": c[False], "calls": calls, "pass": ok, "rounds": rounds}
    out["all_pass"] = all_ok
    suffix = "_majority" if MAJORITY else "_single"
    (EV / f"eye_regression_results{suffix}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print("ALL PASS" if all_ok else "SOME FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
