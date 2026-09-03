"""기계 눈 질문 변형 실험 — 운영 경로(cg.eye_judge) 그대로, _claim_question 만 바꿔 끼움.

기준선(eye_repeat.py, 운영 질문): A_0902 2/5, A_0901 1/5, B 0/5.
변형은 좌/우 해부학 이름 금지 유지. 키는 env 로만.
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
    "A_0902": SP / "cards" / "160a9a29__eye__right_knee.png",
    "A_0901": REPO / ".planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence/eye_crop.png",
    "B_kneepath": REPO / ".planning/quick/260811-ii0-card-gates-5/evidence/eye_kneepath_user_left_knee.png",
}

# V1 — 관절 종류(무릎) 명시 + "팔이 앞을 가로질러 가릴 수 있다" + 다리 존재 판정 기준(허벅지·정강이 연결)
V1 = (
    "사진의 주황색 원은 무릎 관절 하나를 표시합니다. 폴 동작에서는 팔이 무릎 앞을 "
    "가로질러 무릎을 부분적으로 가릴 수 있습니다. 판정 대상은 원 위치의 다리(무릎)입니다. "
    "원 위에 팔이 보이더라도, 그 팔 뒤로 허벅지와 정강이가 원 근처에서 이어지는 다리가 "
    "있는지 먼저 확인하세요. 그런 다리가 있으면 그 다리의 무릎이 '접혀 있음(bent)'인지 "
    "'펴져 있음(extended)'인지 판정하고 limb 필드에 'leg' 를 적으세요. 원 위치와 그 바로 "
    "뒤 어디에도 허벅지·정강이가 이어지는 다리가 없으면(표시가 엉뚱한 곳에 찍힌 경우), "
    "원이 실제로 놓인 사지의 접힘/펴짐을 판정하고 limb 필드에 실제로 보이는 사지 종류를 "
    "적으세요 (팔='arm', 그 외='other'). 원이 신체 위에 있지 않으면 observed 는 "
    "'off_body' 로 하세요."
)
# V2 — 운영 질문 + 무릎 힌트 한 줄만 (최소 변경)
V2 = cg._claim_question("bent", "leg") + (
    " 참고: 이 원은 무릎 관절 표시이며, 팔이 무릎 앞을 가로질러 가릴 수 있습니다. "
    "팔 뒤로 허벅지와 정강이가 이어지면 그 다리가 판정 대상입니다."
)
VARIANTS = {"V1_knee_explicit": V1, "V2_prod_plus_hint": V2}
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def main() -> int:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        print("GEMINI_API_KEY 미설정")
        return 2
    results = {}
    orig = cg._claim_question
    for vname, text in VARIANTS.items():
        cg._claim_question = lambda claim, limb, _t=text: _t  # noqa: E731
        results[vname] = {}
        for cname, png in CASES.items():
            crop = Image.open(png).convert("RGB")
            rounds = []
            for i in range(N):
                r = cg.eye_judge(crop, "bent", api_key=key, expected_limb="leg")
                rounds.append({k: r.get(k) for k in ("observed", "limb", "match", "confidence", "reason")})
                print(f"[{vname} {cname} #{i+1}] {r['observed']}/{r['limb']} match={r['match']} conf={r['confidence']:.2f} :: {str(r['reason'])[:80]}")
            c = Counter(bool(x["match"]) for x in rounds)
            print(f"== {vname} {cname}: True={c[True]} False={c[False]}")
            results[vname][cname] = {"true": c[True], "false": c[False], "rounds": rounds}
    cg._claim_question = orig
    (SP / "eye_variants_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
