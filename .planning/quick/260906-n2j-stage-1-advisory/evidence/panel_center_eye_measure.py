"""배달된 카드 패널의 정중앙만 잘라 눈에 묻는다 — 게이트가 본 시야를 카드에서 재현.

게이트는 원본 프레임 짧은변 18% 를 앵커 중심으로 잘라 물었고, 카드 패널은 같은 중심의
짧은변 42% 크롭이다. 그래서 패널을 다시 18/42 = 42.9% 로 정중앙 크롭하면 게이트가 본 것과
같은 시야가 된다. 감사(42% 전체)와 게이트(18%)가 어긋난 면들을 이걸로 중재한다.
"""
from __future__ import annotations
import json, sys, os
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
REPO = Path("/Users/kimtaesung/Dev/SunityMotion")
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))
sys.path.insert(0, str(REPO / "backend"))

from sunity_shared.analysis import card_gates as cg
from sunity_shared.analysis import card_photo_audit as cpa
from sunity_shared.gemini.config import resolve_model
from sunity_shared.judging.gemini_moment_extractor import _load_api_key

DUMP = Path(sys.argv[1])
OUT = Path(sys.argv[2])
ROUNDS = int(sys.argv[3]) if len(sys.argv) > 3 else 5
RATIO = cg.ANCHOR_CHECK_CROP_FRAC / 0.42   # 패널 안에서 게이트 시야가 차지하는 비율

model = resolve_model("C")
api_key = _load_api_key()
rows = []
for p in sorted(DUMP.glob("*.jpg")):
    stem = p.stem                       # {doc}_{idx}_{crit}_{side}
    side = stem.rsplit("_", 1)[1]
    rest = stem.rsplit("_", 1)[0]
    doc, idx, crit = rest.split("_", 2)
    joint = crit.split("__")[-1] if "__" in crit else crit
    im = Image.open(p).convert("RGB")
    w, h = im.size
    box = int(round(min(w, h) * RATIO))
    cx, cy = w // 2, h // 2
    crop = im.crop((cx - box // 2, cy - box // 2, cx - box // 2 + box, cy - box // 2 + box))
    r = cg.eye_part_token(crop, api_key=api_key, model=model, rounds=ROUNDS)
    crit_arg = crit if (crit in cpa._CRIT_PARTS or crit.startswith(cpa.ANGLE_CRIT_PREFIX)) else None
    exp = cpa.expected_parts(crit_arg, joint)
    verdict = cpa.anchor_verdict(r["observed"], exp)
    row = {"doc": doc, "idx": idx, "crit": crit, "joint": joint, "side": side,
           "observed": r["observed"], "tokens": r["tokens"], "verdict": verdict,
           "expected": sorted(exp), "reason": r["reason"][:160]}
    rows.append(row)
    print(f"{doc} [{idx}] {joint:<15} {side:<4} center18={r['observed']:<12} {verdict:<14} tokens={r['tokens']}", flush=True)

OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
n_ok = sum(1 for r in rows if r["verdict"] == "ok")
n_mm = sum(1 for r in rows if r["verdict"] == "mismatch")
n_un = sum(1 for r in rows if r["verdict"] == "unreadable")
n_ne = sum(1 for r in rows if r["verdict"] == "no_expectation")
print(f"panel_center_eye total={len(rows)} ok={n_ok} mismatch={n_mm} unreadable={n_un} no_expectation={n_ne}")
