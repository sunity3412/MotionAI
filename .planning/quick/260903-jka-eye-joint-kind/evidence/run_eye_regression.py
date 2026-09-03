"""기계 눈 회귀 하네스 (quick-260903-jka) — 운영 경로 card_gates.eye_judge 그대로, N회 반복.

질문은 신규 시그니처 eye_judge(crop, claim, api_key=..., expected_limb=..., joint_kind=...) 로 조립된다
(프롬프트 재구현 금지). GEMINI_API_KEY 는 env 로만, 어디에도 기록하지 않는다.

기대값 출처: ii0 SWEEP-REPORT §(fresh r00/r02/r03, kneepath, elbow r03) + 09-02 pdshape eye ledger(match True 2건)
+ 09-03 측정(클라임 오클루전 2크롭). 실행: 리포 루트에서
  GEMINI_API_KEY=... backend/.venv/bin/python .planning/quick/260903-jka-eye-joint-kind/evidence/run_eye_regression.py [N]
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

EV = REPO / ".planning/quick/260903-jka-eye-joint-kind/evidence"
II0 = REPO / ".planning/quick/260811-ii0-card-gates-5/evidence"
VLU = REPO / ".planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence"

# (이름, 파일, claim, joint, 기대 match)
FIXTURES = [
    ("climb_occl_0902", EV / "climb_eye_right_knee_0902.png", "bent", "right_knee", True),
    ("climb_occl_0901", VLU / "eye_crop.png", "bent", "right_knee", True),
    ("kneepath_user_markdisp", II0 / "eye_kneepath_user_left_knee.png", "bent", "left_knee", False),
    ("fresh_r00_left_elbow", II0 / "eye_fresh_r00_left_elbow.png", "bent", "left_elbow", True),
    ("fresh_r02_right_shoulder", II0 / "eye_fresh_r02_right_shoulder.png", "bent", "right_shoulder", True),
    ("fresh_r03_left_hip_transition", II0 / "eye_fresh_r03_left_hip.png", "bent", "left_hip", False),
    ("elbow_r03_right_knee_ext", II0 / "eye_elbow_r03_right_knee.png", "extended", "right_knee", True),
    ("pdshape_0902_left_elbow", EV / "pdshape_eye_left_elbow_0902.png", "bent", "left_elbow", True),
    ("pdshape_0902_left_hip", EV / "pdshape_eye_left_hip_0902.png", "bent", "left_hip", True),
]
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def main() -> int:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        print("GEMINI_API_KEY 미설정")
        return 2
    ts = datetime.now(timezone.utc).isoformat()
    print(f"model={cg.DEFAULT_C_MODEL} N={N} ts={ts}")
    out = {"ts": ts, "model": cg.DEFAULT_C_MODEL, "n": N, "fixtures": {}}
    all_ok = True
    for name, png, claim, joint, expect in FIXTURES:
        if not png.exists():
            print(f"[{name}] MISSING {png}")
            all_ok = False
            continue
        crop = Image.open(png).convert("RGB")
        limb, kind = cg.joint_limb(joint), cg.joint_kind_ko(joint)
        rounds = []
        for i in range(N):
            r = cg.eye_judge(crop, claim, api_key=key, expected_limb=limb, joint_kind=kind)
            rounds.append({k: r.get(k) for k in ("observed", "limb", "match", "confidence", "reason")})
        c = Counter(bool(x["match"]) for x in rounds)
        ok = (c[True] == N) if expect else (c[False] == N)
        all_ok &= ok
        print(f"== {name} claim={claim} joint={joint} expect={expect}: True={c[True]} False={c[False]} -> {'PASS' if ok else 'FAIL'}")
        out["fixtures"][name] = {"claim": claim, "joint": joint, "expect": expect,
                                 "true": c[True], "false": c[False], "pass": ok, "rounds": rounds}
    out["all_pass"] = all_ok
    (EV / "eye_regression_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print("ALL PASS" if all_ok else "SOME FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
