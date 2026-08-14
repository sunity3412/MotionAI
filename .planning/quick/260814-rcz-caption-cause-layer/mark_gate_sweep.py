#!/usr/bin/env python3
"""승인 5동작 V 마크 관측 스윕 (quick-260814-rcz Task 2) — **재는 것만** 한다.

nh4 `verify_port.py` 의 사본이다. 하는 일은 그대로 — 승인 5동작을 운영 경로
(`app._run_gated_card_inherit`)로 렌더하고 카드 md5 를 nh4 정본과 대조한다.
**추가된 것은 관측 필드뿐**이고, 하네스가 직접 그리거나 임계를 만드는 일은 0 이다.

관측 방법 (새 산식 발명 0):
  드로잉 진입 함수(`fault_zoom._draw_side_joint_angle` /
  `_draw_side_hybrid_joint_angle`)를 **원본 위임 래퍼**로 감싸 호출 인자
  (frame, spec, box)를 채록하고, 그 인자로 운영 함수 `_spec_inner_deg_px` 를
  그대로 호출해 px 공간 사이각을 얻는다. spec 은 `shift_bake_spec` 적용 **이후**
  값이므로 **실제로 그려지는 좌표**의 각이다.
  귀속은 `fault_zoom_angle_bake` 로그 라인에서 flush — 그 로그가 criterion 과
  drawn/omitted 판정을 함께 들고 있어 카드 단위 대조가 가능하다.

자기검증 (측정값을 믿기 전에 하네스가 옳다는 증거):
  · zoom 카드 md5 == **u8i** `evidence/sweep_verdict_main.json`
  · survivors/dropped == 같은 정본
  · 승인 무회귀 hold 9/9 + pair 9/9
  · Gemini 실호출 0 (grammar_round 눈 스텁 계수 > 0)

★정본 선택 근거 (실측 2026-08-14): 플랜은 nh4 `sweep_verdict_port.json` 을
"현 HEAD 정본"으로 지목했으나 **실행해 보니 10/10 전건 불일치**였다. 원인은
nh4(08-13) **이후** 들어온 u8i 의 카드 초 라벨 수리(÷9.0 → label_fps 실효 fps
환산)다 — 카드에 구워지는 초 문자가 바뀌었으니 픽셀이 바뀌는 것이 옳다. 같은
실행을 u8i 정본과 대조하면 **10/10 일치**. 그러므로 현 HEAD 정본은 u8i 이고
nh4 는 pre-u8i 이력이다 ([[verify-the-target-before-touching-it]] — 인계 노트가
지목한 파일명도 검증 대상). 이 일치는 동시에 **관측 래퍼가 픽셀을 바꾸지
않는다**는 증거이기도 하다(래퍼를 단 채로 byte-동일).

프로덕션 코드 아님 — quick 로컬 드라이버. 채점 무접촉. S3 읽기만, Firestore 읽기만.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import math
import os
import pathlib
import shutil
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_XA1 = _HERE.parent / "260811-xa1-mark-grammar-round-ufb-freeze-2-belle"
_NH4_EV = _HERE.parent / "260813-nh4-2-b-ref-v-pdshape-pair-override-pod" / "evidence"
_U8I_EV = _HERE.parent / "260813-u8i-fps-fps-pod" / "evidence"

EVID = _HERE / "evidence"
# 캐시는 **현 세션 scratchpad** — 구 세션 UUID 하드코딩 금지(scratchpad 는 휘발).
SCRATCH = pathlib.Path(
    os.environ.get("RCZ_SCRATCH")
    or "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
      "2a78a76a-92ce-42f8-b5d0-18c558c3d196/scratchpad"
)


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# grammar_round import 부작용 = Gemini 눈 스텁 설치(cg.machine_eye) + backend
# sys.path 주입. verify_port 와 동일 경로 (재발명 0).
gr = _load_module("grammar_round", _XA1 / "grammar_round.py")
vl = gr.vl
vl.EV = EVID
# 캐시 재사용 — ehz 가 같은 S3 키로 이미 받아 둔 현 세션 scratchpad 사본을 그대로
# 마운트한다 (S3 재다운로드 0, 프레임 재추출 0). evidence 가 아니라 scratchpad 라
# 남의 산출물을 덮어쓰지 않는다.
vl.SPA = SCRATCH / "ehz_sweep"

log = logging.getLogger("mark_gate_sweep")


def _seed_env_and_refreports() -> list[str]:
    """Firebase 자격 + refmotion 캐시 시딩 (Firestore 읽기도 0 으로 만든다).

    verify_local 은 `SPA/refreports/{motionId}.json` 을 찾고, ehz 캐시는
    `{m}/refmotion.json` 에 **같은 Firestore 문서**를 이미 갖고 있다. 형상이
    같으므로 복사로 대체한다 — 내용이 달랐다면 카드 md5 자기검증이 즉시 운다.
    """
    repo = _HERE.parents[2]
    if not os.environ.get("FIREBASE_SA_PATH") and not os.environ.get(
            "FIREBASE_SA_JSON"):
        sa = repo / "firebase-sa.json"
        if sa.exists():
            os.environ["FIREBASE_SA_PATH"] = str(sa)
    seeded: list[str] = []
    dst_dir = vl.SPA / "refreports"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for m, (_u, _r, motion_id) in vl.SWEEP_JOBS.items():
        src = vl.SPA / m / "refmotion.json"
        dst = dst_dir / f"{motion_id}.json"
        if src.exists() and not dst.exists():
            shutil.copyfile(src, dst)
            seeded.append(motion_id)
    return seeded


# ── 관측 tap ────────────────────────────────────────────────────────────────
class _AngleTap:
    """V 드로잉 인자 채록 + `fault_zoom_angle_bake` 로그 귀속.

    운영 동작 무변경 — 래퍼는 원본을 그대로 호출하고 반환값을 그대로 돌려준다.
    """

    def __init__(self, fz):
        self.fz = fz
        self.buf: list[dict] = []          # 카드 1장 분량 (user, ref 순)
        self.rows: list[dict] = []         # flush 된 관측 행
        self.drops: list[str] = []
        self._orig_plain = fz._draw_side_joint_angle      # noqa: SLF001
        self._orig_hybrid = fz._draw_side_hybrid_joint_angle  # noqa: SLF001

    # -- 드로잉 래퍼 --------------------------------------------------------
    def _record(self, kind, frame, spec, box):
        try:
            inner = self.fz._spec_inner_deg_px(frame, spec, box)  # noqa: SLF001
        except Exception as exc:  # noqa: BLE001 - 관측 실패는 관측만 잃는다
            inner = None
            log.warning("inner_deg 계산 실패: %s", exc)
        self.buf.append({"kind": kind, "innerDeg": inner})

    def plain(self, img, frame, spec, box):
        self._record("plain", frame, spec, box)
        return self._orig_plain(img, frame, spec, box)

    def hybrid(self, img, frame, spec, box, ref_inner):
        self._record("hybrid", frame, spec, box)
        return self._orig_hybrid(img, frame, spec, box, ref_inner)

    def install(self):
        self.fz._draw_side_joint_angle = self.plain            # noqa: SLF001
        self.fz._draw_side_hybrid_joint_angle = self.hybrid    # noqa: SLF001

    def restore(self):
        self.fz._draw_side_joint_angle = self._orig_plain      # noqa: SLF001
        self.fz._draw_side_hybrid_joint_angle = self._orig_hybrid  # noqa: SLF001

    # -- 로그 귀속 ----------------------------------------------------------
    def flush(self, analysis_id: str, criterion: str, verdict: str) -> None:
        """`fault_zoom_angle_bake` 1줄 = 카드 1장. 버퍼를 그 카드로 귀속."""
        drew = verdict.startswith("drawn")
        # 드로잉 순서 = user(0) → ref(1). `_r_ok` 는 `_u_ok` 단락평가라 user 실패
        # 시 ref 호출이 아예 없다(관측 1건) — 그 사실 자체가 기록 대상이다.
        u = self.buf[0]["innerDeg"] if len(self.buf) >= 1 else None
        r = self.buf[1]["innerDeg"] if len(self.buf) >= 2 else None
        self.rows.append({
            "analysisId": analysis_id,
            "criterion": criterion,
            "verdict": verdict,
            "vDrawn": drew,
            "hybrid": bool(self.buf and self.buf[0]["kind"] == "hybrid"),
            "A2_userInnerDeg": u,
            "A1_refInnerDeg": r,
            "drawCalls": len(self.buf),
        })
        self.buf = []


class _TapHandler(logging.Handler):
    def __init__(self, tap: _AngleTap):
        super().__init__(level=logging.INFO)
        self.tap = tap

    def emit(self, record):  # noqa: D102
        try:
            msg = record.getMessage()
        except Exception:  # noqa: BLE001
            return
        if msg.startswith("fault_zoom_angle_bake "):
            parts = dict(
                p.split("=", 1) for p in msg.split(" ")[1:] if "=" in p
            )
            self.tap.flush(
                parts.get("analysis_id", "?"),
                parts.get("criterion", "?"),
                parts.get("angle_bake", "?"),
            )
        elif msg.startswith("display_anchor drop"):
            self.tap.drops.append(msg)


# ── 파생 축 ─────────────────────────────────────────────────────────────────
def _derive(row: dict) -> dict:
    """A3/A4/A6 = A1·A2 의 순수 파생 (측정 아님 — 산식 1줄씩)."""
    a1, a2 = row.get("A1_refInnerDeg"), row.get("A2_userInnerDeg")
    out = dict(row)
    fin = (
        isinstance(a1, (int, float)) and math.isfinite(a1)
        and isinstance(a2, (int, float)) and math.isfinite(a2)
    )
    out["A3_absDiffDeg"] = abs(a1 - a2) if fin else None
    out["A4_refStraightness"] = (
        min(a1, 180.0 - a1) if isinstance(a1, (int, float)) and math.isfinite(a1)
        else None
    )
    out["A4_userStraightness"] = (
        min(a2, 180.0 - a2) if isinstance(a2, (int, float)) and math.isfinite(a2)
        else None
    )
    # A6 — 굽음 = 사이각이 작은 쪽. belle "방향 반대" 축.
    out["A6_moreBentSide"] = (
        None if not fin else ("user" if a2 < a1 else "ref" if a1 < a2 else "tie")
    )
    return out


def _zoom_md5_dir(cards_dir: pathlib.Path) -> dict[str, str]:
    return {
        p.name: hashlib.md5(p.read_bytes()).hexdigest()
        for p in sorted(cards_dir.glob("zoom_*.png"))
    }


def main() -> int:
    assert "260814-rcz" in str(vl.EV), f"EV 재지정 실패: {vl.EV}"
    assert str(vl.SPA).startswith(str(SCRATCH)), f"SPA 재지정 실패: {vl.SPA}"
    EVID.mkdir(exist_ok=True)
    seeded = _seed_env_and_refreports()
    if seeded:
        print(f"  refmotion 캐시 시딩 (Firestore 읽기 0): {seeded}")

    cert = json.loads((_U8I_EV / "sweep_verdict_main.json").read_text())
    stale = json.loads((_NH4_EV / "sweep_verdict_port.json").read_text())

    from sunity_shared.analysis import fault_zoom as fz

    tap = _AngleTap(fz)
    handler = _TapHandler(tap)
    tap.install()
    logging.getLogger().addHandler(handler)
    eye0 = gr._EYE_STUB["calls"]  # noqa: SLF001
    try:
        res = vl.sweep()  # 무패치 — 운영 경로 그대로
    finally:
        logging.getLogger().removeHandler(handler)
        tap.restore()
    eye_stub_calls = gr._EYE_STUB["calls"] - eye0  # noqa: SLF001

    fails: list[str] = []

    # ── 자기검증 1: zoom 카드 md5 == nh4 정본 ──────────────────────────────
    md5_mismatch: list[str] = []
    cards_total = 0
    for m in cert:
        got = _zoom_md5_dir(EVID / "sweep_cards" / m)
        want = {k: v for k, v in (cert[m].get("pngMd5") or {}).items()
                if k.startswith("zoom_")}
        cards_total += len(got)
        for k in sorted(set(got) | set(want)):
            if got.get(k) != want.get(k):
                md5_mismatch.append(
                    f"{m}/{k}: now={got.get(k)} u8i={want.get(k)}")
    if md5_mismatch:
        fails.append(f"zoom md5 != u8i 정본 ({len(md5_mismatch)}건)")
    if cards_total != 10:
        fails.append(f"카드 총수 {cards_total} != 10")

    # pre-u8i(nh4) 대비 델타는 **기대되는 차이**다 — 초 라벨 수리분. 숨기지 않고
    # 계수만 남겨 "왜 옛 정본과 다른가"가 산출물에서 읽히게 한다.
    pre_u8i_delta = 0
    for m in stale:
        old = {k: v for k, v in (stale[m].get("pngMd5") or {}).items()
               if k.startswith("zoom_")}
        now = _zoom_md5_dir(EVID / "sweep_cards" / m)
        pre_u8i_delta += sum(1 for k, v in old.items() if now.get(k) != v)

    # ── 자기검증 2: survivors/dropped == 정본 ─────────────────────────────
    for m in cert:
        for fld in ("survivors", "dropped"):
            now = (res.get(m) or {}).get("verdict", {}).get(fld)
            want = cert[m]["verdict"][fld]
            if now != want:
                fails.append(f"{m}/{fld}: now={now} u8i={want}")

    # ── 자기검증 3: 승인 무회귀 ───────────────────────────────────────────
    ap = vl.approved()
    if not (ap["hold"] == ap["pair"] == 9):
        fails.append(
            f"승인 무회귀 실패 hold={ap['hold']} pair={ap['pair']} (기대 9/9)")

    # ── 자기검증 4: Gemini 실호출 0 ───────────────────────────────────────
    if eye_stub_calls <= 0:
        fails.append(f"눈 스텁 계수 {eye_stub_calls} — 스텁 미경유 의심")

    # ── 관측 행 + 카드 조인 (A5 는 부착 payload 에서) ─────────────────────
    payload_by_criterion: dict[tuple[str, str], dict] = {}
    for m in res:
        for c in ((res[m].get("attached") or {}).get("comparisons") or []):
            if c.get("criterion"):
                payload_by_criterion[(m, c["criterion"])] = c
    motion_of_analysis = {f"sweep-{m}": m for m in res}

    rows = []
    for row in tap.rows:
        m = motion_of_analysis.get(row["analysisId"], row["analysisId"])
        pay = payload_by_criterion.get((m, row["criterion"])) or {}
        enriched = _derive(row)
        enriched["motion"] = m
        enriched["A5_deficitDeg"] = pay.get("deficitDeg")
        enriched["A5_tolerance"] = pay.get("tolerance")
        enriched["cardTier"] = pay.get("tier")
        enriched["userVideoSec"] = pay.get("userVideoSec")
        enriched["refVideoSec"] = pay.get("refVideoSec")
        rows.append(enriched)

    src = EVID / "sweep_verdict.json"
    if src.exists():
        shutil.move(str(src), str(EVID / "sweep_verdict_rcz.json"))
    (EVID / "mark_gate_sweep.json").write_text(json.dumps({
        "selfCheck": {
            "pass": not fails,
            "fails": fails,
            "md5Mismatch": md5_mismatch,
            "certSource": "260813-u8i evidence/sweep_verdict_main.json",
            "preU8iDeltaCards": pre_u8i_delta,
            "preU8iNote": (
                "nh4(pre-u8i) 정본과의 차이 — u8i 초 라벨 수리로 카드에 구워지는 "
                "초 문자가 바뀐 결과. 기대된 델타이며 회귀 아님."
            ),
            "cardsTotal": cards_total,
            "approved": {k: ap[k] for k in ("binding", "hold", "pair", "peak")},
            "eyeStubCalls": eye_stub_calls,
            "geminiRealCalls": 0,
        },
        "displayAnchorDrops": tap.drops,
        "observations": rows,
    }, ensure_ascii=False, indent=1) + "\n")

    drawn = [r for r in rows if r["vDrawn"]]
    print(f"\nMARK GATE SWEEP {'PASS' if not fails else 'FAIL'} "
          f"cards={cards_total} V그려짐={len(drawn)}/{len(rows)} "
          f"eyeStub={eye_stub_calls} approved hold={ap['hold']}/9 "
          f"pair={ap['pair']}/9")
    for f in fails:
        print(f"  FAIL: {f}")
    for r in rows:
        print(f"  {r['motion']:<13} {r['criterion']:<38} "
              f"{r['verdict']:<22} "
              f"A1ref={r['A1_refInnerDeg']} A2user={r['A2_userInnerDeg']}")
    return 0 if not fails else 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raise SystemExit(main())
