"""배달 패널 정중앙 재측정 v2 — v1 의 계기 결함 3건을 고친 판.

v1(panel_center_eye_measure.py)의 결함, 2026-09-06 검증에서 확정:
 1. `RATIO = ANCHOR_CHECK_CROP_FRAC / 0.42` 로 크롭 비율 0.42 를 리터럴로 박았다.
    실측(fault_zoom_crop 로그)에서 감점 카드는 0.40~0.55 밴드로 흩어진다 —
    0.55 카드에서는 계기 창이 게이트 창보다 면적 1.7배 넓다.
 2. 표시(브랜드색 링)가 그려진 패널을 무표시 전용 질문(eye_part_token)에 넣는다.
    card_gates.py part_crop docstring 이 스스로 "링을 그리면 눈이 링을 보고 답한다"고 적었다.
    실측: 같은 창에서 링만 지우면 elbow 5/5 → thigh 3/knee 2 로 판정이 뒤집힌다.
 3. "패널 정중앙 = 앵커" 가 `vertex_centered=False` 카드에서는 설계상 거짓이다.
    09-06 라이브 18카드 중 10카드가 그 경우 — v1 은 그것을 전부 "중심이 딴 부위"로 셌다.

v2 가 하는 일:
 - 카드별 실제 크롭 비율을 `fault_zoom_crop` 로그에서 읽어 창 크기를 맞춘다.
 - 브랜드색 화소를 inpaint 로 지운 뒤 묻는다(원본도 같이 물어 링 효과를 분리한다).
 - `vertex_centered=False` 카드는 mismatch 로 세지 않고 `not_center_anchored` 로 분리한다.
   (그 카드의 앵커 판정은 게이트 자신의 trail 로그가 정본이다.)

사용: panel_center_eye_measure_v2.py <dump-dir> <crop-log.txt> <out.json> [rounds]
"""
from __future__ import annotations
import json, re, sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

REPO = Path("/Users/kimtaesung/Dev/SunityMotion")
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))
sys.path.insert(0, str(REPO / "backend"))

from sunity_shared.analysis import card_gates as cg
from sunity_shared.analysis import card_photo_audit as cpa
from sunity_shared.gemini.config import resolve_model
from sunity_shared.judging.gemini_moment_extractor import _load_api_key

DUMP = Path(sys.argv[1])
CROPLOG = Path(sys.argv[2])
OUT = Path(sys.argv[3])
ROUNDS = int(sys.argv[4]) if len(sys.argv) > 4 else 5

BRAND = np.array([255, 75, 51], dtype=np.int16)   # #FF4B33
BRAND_TOL = 70

_CROP_RE = re.compile(
    r"analysis_id=(?P<aid>[0-9a-f]+) region=(?P<region>\S+) criterion=(?P<crit>\S+) "
    r"user_kind=\S+ user_side_px=\S+ ref_kind=\S+ ref_side_px=\S+ .*?"
    r"vertex_centered=(?P<vc>\S+) shared_side_px=\S+ shared_frac=(?P<frac>\S+)"
)

def load_crop_map(path: Path) -> dict:
    """(doc8, region, crit) -> {vertex_centered, frac}. 같은 키가 여러 번이면 마지막이 최종 렌더."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _CROP_RE.search(line)
        if not m:
            continue
        key = (m["aid"][:8], m["region"], m["crit"])
        frac = None if m["frac"] == "none" else float(m["frac"])
        out[key] = {"vertex_centered": m["vc"] == "True", "frac": frac}
    return out

def strip_marks(im: Image.Image) -> Image.Image:
    """브랜드색 화소만 inpaint 로 지운다 — 링이 눈의 답을 바꾸는 것을 배제."""
    arr = np.asarray(im.convert("RGB")).astype(np.int16)
    dist = np.abs(arr - BRAND).sum(axis=2)
    mask = (dist < BRAND_TOL).astype(np.uint8) * 255
    if mask.sum() == 0:
        return im
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=1)
    bgr = cv2.cvtColor(np.asarray(im.convert("RGB")), cv2.COLOR_RGB2BGR)
    fixed = cv2.inpaint(bgr, mask, 3, cv2.INPAINT_TELEA)
    return Image.fromarray(cv2.cvtColor(fixed, cv2.COLOR_BGR2RGB))

def brand_frac(im: Image.Image) -> float:
    arr = np.asarray(im.convert("RGB")).astype(np.int16)
    return float((np.abs(arr - BRAND).sum(axis=2) < BRAND_TOL).mean())

def main() -> int:
    crop_map = load_crop_map(CROPLOG)
    model = resolve_model("C")
    api_key = _load_api_key()
    rows = []
    for p in sorted(DUMP.glob("*.jpg")):
        stem = p.stem                       # {doc}_{idx}_{crit}_{side}
        side = stem.rsplit("_", 1)[1]
        doc, idx, crit = stem.rsplit("_", 1)[0].split("_", 2)
        joint = crit.split("__")[-1] if "__" in crit else crit
        # 로그 키: criterion 카드는 (region=joint, crit), advisory 는 (region=joint, 'none')
        info = crop_map.get((doc, joint, crit)) or crop_map.get((doc, joint, "none"))
        if info is None:
            # region 이 arms/legs 등 묶음인 카드 — joint 로는 못 찾는다
            cands = [v for (d, _r, c), v in crop_map.items() if d == doc and c == crit]
            info = cands[-1] if cands else {"vertex_centered": None, "frac": None}

        im = Image.open(p).convert("RGB")
        w, h = im.size
        frac = info["frac"] or 0.42
        ratio = cg.ANCHOR_CHECK_CROP_FRAC / frac
        box = int(round(min(w, h) * ratio))
        cx, cy = w // 2, h // 2
        crop = im.crop((cx - box // 2, cy - box // 2, cx - box // 2 + box, cy - box // 2 + box))
        clean = strip_marks(crop)

        r_raw = cg.eye_part_token(crop, api_key=api_key, model=model, rounds=ROUNDS)
        r_cln = cg.eye_part_token(clean, api_key=api_key, model=model, rounds=ROUNDS)

        crit_arg = crit if (crit in cpa._CRIT_PARTS or crit.startswith(cpa.ANGLE_CRIT_PREFIX)) else None
        exp = cpa.expected_parts(crit_arg, joint)
        v_raw = cpa.anchor_verdict(r_raw["observed"], exp)
        v_cln = cpa.anchor_verdict(r_cln["observed"], exp)

        if info["vertex_centered"] is False:
            final = "not_center_anchored"
        else:
            final = v_cln

        rows.append({
            "doc": doc, "idx": idx, "crit": crit, "joint": joint, "side": side,
            "vertex_centered": info["vertex_centered"], "card_frac": info["frac"],
            "ratio_v2": round(ratio, 4), "ratio_v1": round(cg.ANCHOR_CHECK_CROP_FRAC / 0.42, 4),
            "box_px_v2": box, "box_px_v1": int(round(min(w, h) * cg.ANCHOR_CHECK_CROP_FRAC / 0.42)),
            "brand_frac": round(brand_frac(crop), 4),
            "observed_marked": r_raw["observed"], "tokens_marked": r_raw["tokens"], "verdict_marked": v_raw,
            "observed_clean": r_cln["observed"], "tokens_clean": r_cln["tokens"], "verdict_clean": v_cln,
            "expected": sorted(exp), "final": final,
        })
        print(f"{doc} [{idx}] {joint:<14} {side:<4} vc={str(info['vertex_centered']):<5} "
              f"frac={info['frac']} box {rows[-1]['box_px_v1']}->{box} "
              f"marked={r_raw['observed']:<11} clean={r_cln['observed']:<11} final={final}", flush=True)

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    c = Counter(r["final"] for r in rows)
    flipped = sum(1 for r in rows if r["verdict_marked"] != r["verdict_clean"])
    centered = [r for r in rows if r["vertex_centered"]]
    print(f"panel_center_eye_v2 total={len(rows)} " + " ".join(f"{k}={v}" for k, v in sorted(c.items())))
    print(f"mark_flipped_verdict={flipped}/{len(rows)}  center_anchored_panels={len(centered)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
