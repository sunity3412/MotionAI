"""명부 정정 — panel_center_eye_measure_v2 의 크롭로그 조회 실패를 고친다 (2026-09-07).

결함: v2 는 크롭 로그를 `(doc8, joint, crit)` → `(doc8, joint, 'none')` → `crit` 일치 로
찾는다. 그런데 advisory 카드는 로그에 **묶음 region**(`arms`/`legs`) + `criterion=none`
으로 적힌다. 관절 이름으로는 어느 키도 안 맞아 `info` 가 {vertex_centered: None, frac: None}
로 남고, `if info['vertex_centered'] is False` 분기가 안 탄다. 그 결과
**중심을 안 맞추도록 설계된 카드**가 v2 가 없애려던 바로 그 리터럴 0.42 크롭으로 측정돼
`mismatch` 로 계상됐다.

수리: 관절 → 묶음 region 폴백을 한 단 추가한다. **눈에게 다시 묻지 않는다** — 이미 저장된
`verdict_clean` 을 그대로 쓰고 `vertex_centered` 메타데이터만 복구한다. 재판정이 아니라
메타데이터 수리다.

실행: python3 fix_roster.py   (의존성 없음)
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "260906-n2j-stage-1-advisory" / "evidence"
V2_JSON = SRC / "panel_center_v2_live.json"
CROPLOG = SRC / "crop_logs_n2j.txt"
OUT = Path(__file__).resolve().parent / "roster_corrected.json"

# fault_zoom 의 묶음 region 이름공간. 관절이 묶음 카드로 나갈 때 로그의 region 이 이것이 된다.
_ARM = ("shoulder", "elbow", "hand", "wrist")
_LEG = ("hip", "knee", "ankle", "foot")

_LINE = re.compile(
    r"analysis_id=(?P<aid>\w+) region=(?P<region>\S+) criterion=(?P<crit>\S+).*?"
    r"user_frame=(?P<uf>\S+) ref_rep_idx=(?P<rr>\S+) ref_video_idx=(?P<rv>\S+) "
    r"vertex_centered=(?P<vc>\S+) shared_side_px=\S+ shared_frac=(?P<frac>\S+)"
)


def bundle_of(joint: str) -> str | None:
    if any(t in joint for t in _ARM):
        return "arms"
    if any(t in joint for t in _LEG):
        return "legs"
    return None


def load_crop_map(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _LINE.search(line)
        if not m:
            continue
        d = m.groupdict()
        out[(d["aid"][:8], d["region"], d["crit"])] = {
            "vertex_centered": d["vc"] == "True",
            "frac": None if d["frac"] == "none" else float(d["frac"]),
            "user_frame": None if d["uf"] == "none" else int(d["uf"]),
            "ref_rep_idx": None if d["rr"] == "none" else int(d["rr"]),
            "ref_video_idx": None if d["rv"] == "none" else int(d["rv"]),
        }
    return out


def lookup(crop_map: dict, doc: str, joint: str, crit: str) -> tuple[dict | None, str]:
    """v2 의 3단 조회 + 묶음 region 폴백 1단. 어느 단에서 맞았는지도 돌려준다."""
    hit = crop_map.get((doc, joint, crit))
    if hit:
        return hit, "region=joint,crit"
    hit = crop_map.get((doc, joint, "none"))
    if hit:
        return hit, "region=joint,none"
    cands = [v for (d, _r, c), v in crop_map.items() if d == doc and c == crit]
    if cands:
        return cands[-1], "crit-only"
    b = bundle_of(joint)                                   # ← 추가된 단
    if b:
        hit = crop_map.get((doc, b, "none"))
        if hit:
            return hit, f"bundle={b}"
    return None, "miss"


def main() -> int:
    rows = json.loads(V2_JSON.read_text(encoding="utf-8"))
    crop_map = load_crop_map(CROPLOG)

    out, changed = [], []
    for r in rows:
        info, how = lookup(crop_map, r["doc"], r["joint"], r["crit"])
        vc = info["vertex_centered"] if info else None
        # v2 와 동일한 규칙. 눈의 답(verdict_clean)은 손대지 않는다.
        final = "not_center_anchored" if vc is False else r["verdict_clean"]
        rec = dict(r)
        rec.update({
            "vertex_centered": vc,
            "card_frac": info["frac"] if info else None,
            "user_frame": info["user_frame"] if info else None,
            "ref_rep_idx": info["ref_rep_idx"] if info else None,
            "ref_video_idx": info["ref_video_idx"] if info else None,
            "lookup": how,
            "final_v2": r["final"],
            "final": final,
        })
        out.append(rec)
        if final != r["final"]:
            changed.append(rec)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    before, after = Counter(r["final_v2"] for r in out), Counter(r["final"] for r in out)
    print("v2  :", dict(sorted(before.items())))
    print("정정:", dict(sorted(after.items())))
    print(f"\n뒤집힌 면 {len(changed)}:")
    for c in changed:
        print(f"  {c['doc']} [{c['idx']}] {c['side']:<4} {c['joint']:<14} "
              f"{c['final_v2']} -> {c['final']}   (조회 {c['lookup']}, vc={c['vertex_centered']})")

    still = [r for r in out if r["vertex_centered"] is None]
    print(f"\n아직 크롭로그에서 못 찾은 면 {len(still)}: "
          + (", ".join(f"{r['doc']}[{r['idx']}]{r['side']}/{r['joint']}" for r in still) or "없음"))

    tgt = [r for r in out if r["final"] == "mismatch"]
    print(f"\n대상 {len(tgt)}면:")
    for r in tgt:
        print(f"  {r['doc']} [{r['idx']}] {r['side']:<4} {r['joint']:<14} frac={r['card_frac']} "
              f"눈={r['observed_clean']:<10} user_frame={r['user_frame']} ref_video_idx={r['ref_video_idx']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
