#!/usr/bin/env python3
"""B 스펙 운영 이식 재현 게이트 (quick-260813-nh4).

m0k A/B 하네스가 인증한 B 스펙(V 베이크 align 단일 출처)이 **운영 코드**
(fault_zoom.align_bake_spec + build seam 2곳 + app.py align_bake payload)로
이식된 뒤, 승인 5동작 스윕을 **monkeypatch 없이 운영 경로 그대로** 실행해
m0k B 인증값과 기계 대조한다. 완료 기준 = "m0k B 재현"이지 새 판정이 아니다.

게이트 (전건 PASS 필요, 하나라도 실패 = exit 1):
  1. zoom md5 == m0k evidence/sweep_verdict_B.json (1차 — 로직 동치면 픽셀
     동일 기대). 불일치 시 숨기지 않고 카드 존재/부재 구조 대조로 강등 판정
     + 원인 실측 명기 (verdict json 에 mismatch 채록).
  2. survivors/dropped == ivs 정본 전건 (채점·게이트 무접촉 증거).
  3. 소생 6건 카드 성립 (elbow r00·r03, pdshape r00·r02·r03, powerspin r02).
  4. elbow r01 drop 유지 (display_anchor drop 로그 + align conf 실값 로그).
  5. 카드 총수 8(현행 A) → 10 (B).
  6. 승인 무회귀 — vl.approved() joint-scope hold 9/9 + pair 9/9.
  7. Gemini 실호출 0 (grammar_round machine_eye 스텁 계수).

프로덕션 코드 아님 — quick 로컬 드라이버 (ab_render.py 구조 상속: 같은 세션
scratchpad 캐시 + grammar_round 스텁/더미 키/인터프리터 승격).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import pathlib
import shutil
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_XA1 = _HERE.parent / "260811-xa1-mark-grammar-round-ufb-freeze-2-belle"
_M0K_EV = _HERE.parent / "260813-m0k-1-v-bake-align-a-b-2" / "evidence"
_IVS_EV = _HERE.parent / "260813-ivs-5" / "evidence"

EVID = _HERE / "evidence"
SCRATCH = pathlib.Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "ae166167-1abf-4754-9fe8-336a719ef9e2/scratchpad"
)

# m0k 인증 소생 6건 (motion, rid, zoom png 이름)
RECOVERED = [
    ("elbow", "r00", "zoom_angle_vs_reference__right_elbow.png"),
    ("elbow", "r03", "zoom_angle_vs_reference__right_knee.png"),
    ("pdshapefault", "r00", "zoom_angle_vs_reference__left_elbow.png"),
    ("pdshapefault", "r02", "zoom_angle_vs_reference__left_shoulder.png"),
    ("pdshapefault", "r03", "zoom_angle_vs_reference__left_knee.png"),
    ("powerspin", "r02", "zoom_angle_vs_reference__left_shoulder.png"),
]
CARDS_A_TOTAL = 8   # m0k A(현행) zoom 카드 총수
CARDS_B_TOTAL = 10  # m0k B 인증 zoom 카드 총수


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


gr = _load_module("grammar_round", _XA1 / "grammar_round.py")
vl = gr.vl
vl.EV = EVID
vl.SPA = SCRATCH / "approved_sweep"

log = logging.getLogger("verify_port")


class _PortTap(logging.Handler):
    """운영 로그 채록 — display_anchor drop / align_bake miss (증거 라인)."""

    def __init__(self):
        super().__init__(level=logging.INFO)
        self.drops: list[str] = []
        self.misses: list[str] = []

    def emit(self, record):  # noqa: D102
        try:
            msg = record.getMessage()
            if msg.startswith("display_anchor drop"):
                self.drops.append(msg)
            elif msg.startswith("align_bake miss"):
                self.misses.append(msg)
        except Exception:  # noqa: BLE001
            pass


def _zoom_md5_dir(cards_dir: pathlib.Path) -> dict[str, str]:
    return {
        p.name: hashlib.md5(p.read_bytes()).hexdigest()
        for p in sorted(cards_dir.glob("zoom_*.png"))
    }


def main() -> int:
    assert "260813-nh4" in str(vl.EV), f"EV 재지정 실패: {vl.EV}"
    assert str(vl.SPA).startswith(str(SCRATCH)), f"SPA 재지정 실패: {vl.SPA}"
    EVID.mkdir(exist_ok=True)

    iv = json.loads((_IVS_EV / "sweep_verdict.json").read_text())
    b = json.loads((_M0K_EV / "sweep_verdict_B.json").read_text())

    tap = _PortTap()
    logging.getLogger().addHandler(tap)
    eye0 = gr._EYE_STUB["calls"]  # noqa: SLF001
    try:
        res = vl.sweep()  # 무패치 — 운영 경로 그대로 (이식이 기본 동작)
    finally:
        logging.getLogger().removeHandler(tap)
    eye_stub_calls = gr._EYE_STUB["calls"] - eye0  # noqa: SLF001

    fails: list[str] = []
    notes: list[str] = []

    # 1. zoom md5 == m0k B
    md5_mismatch: list[str] = []
    port_cards_total = 0
    for m in b:
        cards_dir = EVID / "sweep_cards" / m
        port = _zoom_md5_dir(cards_dir)
        cert = {k: v for k, v in (b[m].get("pngMd5") or {}).items()
                if k.startswith("zoom_")}
        port_cards_total += len(port)
        for k in sorted(set(port) | set(cert)):
            if port.get(k) != cert.get(k):
                md5_mismatch.append(
                    f"{m}/{k}: port={port.get(k)} certB={cert.get(k)}"
                )
    if md5_mismatch:
        fails.append(f"zoom md5 != m0k B ({len(md5_mismatch)}건)")

    # 2. survivors/dropped == ivs 정본
    for m in iv:
        for fld in ("survivors", "dropped"):
            got = (res.get(m) or {}).get("verdict", {}).get(fld)
            want = iv[m]["verdict"][fld]
            if got != want:
                fails.append(f"{m}/{fld}: port={got} ivs={want}")

    # 3. 소생 6건 카드 성립
    for m, rid, png in RECOVERED:
        p = EVID / "sweep_cards" / m / png
        if not p.exists():
            fails.append(f"소생 미성립: {m} {rid} {png}")

    # 4. elbow r01 drop 유지 + conf 실값 로그
    r01_drop = [d for d in tap.drops if "rid=r01" in d]
    if not r01_drop:
        fails.append("elbow r01 display_anchor drop 로그 부재")
    r01_png = EVID / "sweep_cards" / "elbow" / \
        "zoom_angle_vs_reference__right_shoulder.png"
    if r01_png.exists():
        fails.append("elbow r01 카드가 생겼다 — drop 유지 위반")
    r01_miss = [x for x in tap.misses if "rid=r01" in x]
    if not r01_miss:
        notes.append("r01 align_bake miss 로그 없음 (conf 실값 미채록)")

    # 5. 카드 총수 8→10
    if port_cards_total != CARDS_B_TOTAL:
        fails.append(f"카드 총수 {port_cards_total} != {CARDS_B_TOTAL}")

    # 6. 승인 무회귀 (vl.approved — fxx 위임 경로 재사용)
    ap = vl.approved()
    if not (ap["binding"] == ap["hold"] == ap["pair"] == 9):
        fails.append(
            f"승인 무회귀 실패: binding={ap['binding']} hold={ap['hold']} "
            f"pair={ap['pair']} (기대 9/9/9)"
        )

    # 7. Gemini 실호출 0
    if eye_stub_calls <= 0:
        fails.append(f"눈 스텁 계수 이상: {eye_stub_calls} (스텁 미경유 의심)")

    # 산출 정리 — 정본 파일명으로 이동
    src_v = EVID / "sweep_verdict.json"
    if src_v.exists():
        shutil.move(str(src_v), str(EVID / "sweep_verdict_port.json"))
    (EVID / "port_verdict.json").write_text(json.dumps({
        "pass": not fails,
        "fails": fails,
        "notes": notes,
        "md5Mismatch": md5_mismatch,
        "cardsTotal": port_cards_total,
        "cardsExpected": {"A": CARDS_A_TOTAL, "B": CARDS_B_TOTAL},
        "recovered": [f"{m}:{rid}" for m, rid, _ in RECOVERED],
        "r01DropLogs": r01_drop,
        "alignBakeMissLogs": tap.misses,
        "approved": {k: ap[k] for k in ("binding", "hold", "pair", "peak")},
        "eyeStubCalls": eye_stub_calls,
    }, ensure_ascii=False, indent=1))

    print(f"\nPORT GATE {'PASS' if not fails else 'FAIL'} "
          f"cards={port_cards_total} eyeStub={eye_stub_calls} "
          f"approved hold={ap['hold']}/9 pair={ap['pair']}/9")
    for f in fails:
        print(f"  FAIL: {f}")
    for n in notes:
        print(f"  note: {n}")
    return 0 if not fails else 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
