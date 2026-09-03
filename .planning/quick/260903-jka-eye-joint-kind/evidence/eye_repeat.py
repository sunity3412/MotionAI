"""기계 눈 반복 재판정 — 같은 크롭에 N회, 운영 경로(card_gates.eye_judge) 그대로.

목적: 09-01 하네스 match=True vs 09-02 운영 match=False 가 같은 크롭(픽셀 동일, 링 주변만 미세 차)에서
갈린 이유가 비결정성인지 재기 위한 측정. 키는 env 로만, 어디에도 기록하지 않는다.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/Users/kimtaesung/Dev/SunityMotion")
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))
from PIL import Image  # noqa: E402
from sunity_shared.analysis import card_gates as cg  # noqa: E402

SP = Path("/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/b6261bd3-eff6-4149-b01d-4456b90e7924/scratchpad")
CASES = {
    "A_0902_prod_crop": SP / "cards" / "160a9a29__eye__right_knee.png",
    "A_0901_harness_crop": REPO / ".planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/eye_crop.png",
    "B_kneepath_regress": REPO / ".planning/quick/260811-ii0-card-gates-5/evidence/eye_kneepath_user_left_knee.png",
}
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def main() -> int:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        print("GEMINI_API_KEY 미설정")
        return 2
    print(f"model={cg.DEFAULT_C_MODEL} N={N}")
    out = {}
    for name, png in CASES.items():
        crop = Image.open(png).convert("RGB")
        rounds = []
        for i in range(N):
            r = cg.eye_judge(crop, "bent", api_key=key, expected_limb="leg")
            rounds.append({k: r.get(k) for k in ("observed", "limb", "match", "confidence", "reason")})
            print(f"[{name} #{i+1}] observed={r['observed']} limb={r['limb']} match={r['match']} conf={r['confidence']:.2f} :: {str(r['reason'])[:90]}")
        c = Counter(bool(x["match"]) for x in rounds)
        print(f"== {name}: match True={c[True]} False={c[False]}")
        out[name] = {"rounds": rounds, "true": c[True], "false": c[False]}
    (SP / "eye_repeat_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
