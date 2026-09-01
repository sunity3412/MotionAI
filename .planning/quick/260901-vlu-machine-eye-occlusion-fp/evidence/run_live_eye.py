"""라이브 양방향 재판정 하네스 (quick-260901-vlu Task 2).

card_gates.eye_judge 경유만 — 프롬프트/스키마/HTTP 재구현 금지 (운영 코드
경로 그대로가 검증 대상). GEMINI_API_KEY 는 env 로만 받으며 코드/로그/결과
어디에도 기록하지 않는다.

Case A (오클루전 -> PASS 전환 목표): evidence/eye_crop.png — belle 실물
  (uid csKWYvI3WCPYPysNQ9KkWecaUvq1 / ea975e6e83374564a7803ca31aefa46b,
  right_knee 3.0s, 뻗은 팔이 굽힌 무릎 앞을 가로지르는 프레임).
  claim=bent, expected_limb=leg. 기대 = match=True.
Case B (마크-전위 -> FAIL 유지 회귀, 1급): ii0 kneepath 실물 — 무릎 마크가
  굽은 팔 위, 기대 다리는 그 자리에 없음. claim=bent, expected_limb=leg.
  기대 = match=False. B 가 True 로 새는 프롬프트는 즉시 폐기 (ii0 §6-3).

결과는 live_eye_results.json 에 rounds 누적 + final 갱신 (반복 회차 전부 박제).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/Users/kimtaesung/Dev/SunityMotion")
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))

from PIL import Image  # noqa: E402

from sunity_shared.analysis import card_gates as cg  # noqa: E402

EV = REPO / ".planning/quick/260901-vlu-machine-eye-occlusion-fp/evidence"
CASE_A = EV / "eye_crop.png"
CASE_B = (REPO / ".planning/quick/260811-ii0-card-gates-5/evidence/"
          "eye_kneepath_user_left_knee.png")
RESULTS = EV / "live_eye_results.json"


def run_case(name: str, png: Path, api_key: str) -> dict:
    crop = Image.open(png).convert("RGB")
    out = cg.eye_judge(crop, "bent", api_key=api_key, expected_limb="leg")
    out["model"] = cg.DEFAULT_C_MODEL
    out["crop_file"] = str(png.relative_to(REPO))
    print(f"[{name}] observed={out['observed']} limb={out['limb']} "
          f"match={out['match']} conf={out['confidence']:.2f}")
    print(f"[{name}] reason: {out['reason']}")
    return out


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("GEMINI_API_KEY 미설정 — 중단 (키는 env 로만 주입)")
        return 2
    prompt = cg._claim_question("bent", "leg")
    sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    ts = datetime.now(timezone.utc).isoformat()
    print(f"prompt_sha256={sha} model={cg.DEFAULT_C_MODEL} ts={ts}")
    a = run_case("caseA occlusion", CASE_A, api_key)
    b = run_case("caseB mark-displacement", CASE_B, api_key)
    doc = {"rounds": [], "final": {}}
    if RESULTS.exists():
        doc = json.loads(RESULTS.read_text())
    doc["rounds"].append({"caseA": a, "caseB": b, "prompt_sha256": sha,
                          "ts": ts})
    doc["final"] = {"caseA": a, "caseB": b}
    RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    ok = a["match"] is True and b["match"] is False
    print(f"round verdict: caseA(match=True 기대)={a['match']} / "
          f"caseB(match=False 기대)={b['match']} -> "
          f"{'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
