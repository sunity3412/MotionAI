#!/usr/bin/env python3
"""승인 5동작 새 문법 스윕 렌더 드라이버 (quick-260813-ivs).

belle 08-13 방침 (locked): "전체 반영한 다음에 조정하자" — 이 사이클 = 전체
반영 실물 만들기. 렌더는 **무패치 운영 헬퍼** `app._run_gated_card_inherit`
(ufb `verify_local.sweep()` 그대로 — fxx 배선 display_anchor + 골반 P3
하이브리드가 운영 코드에 있으므로 sweep 만 돌리면 새 문법 카드가 나온다).
이 파일은 **관찰만** 한다 — 하네스 자체 그리기 0, 마크 튜닝 0, 임계 변경 0.

grammar_round importlib 상속 (verify_wiring 선례): machine_eye 스텁(Gemini
실호출 0, T-ivs-03) + 더미 키(`_ensure_gemini_key` early-return, SSM 무접촉)
+ 인터프리터 승격 + backend sys.path. gr 쪽 EV-가드 함수(baseline 등)는
"260811-xa1" 전제이므로 호출 금지 — 스텁 상속만 쓴다.

재지정 (실행 전 필수, T-ivs-02):
  vl.EV  = <ivs>/evidence          (ufb/xa1 evidence 파괴 금지 — 가드 assert)
  vl.SPA = <현 세션 scratchpad>/approved_sweep  (죽은 구세션 경로 부활 금지 —
           캐시는 휘발 OK, 보존은 evidence/ 리포만)

stages:
  --sweep   vl.sweep() 1회 구동 → evidence/sweep_verdict.json (sweep 이 직접
            기록) + evidence/sweep_cards/{motion}/ 카드 PNG + 관찰 산출물
            evidence/measure.json (displayAnchors/Drops, shifts, crops,
            drawCalls, bakeLines, cropLines, s3Keys eye·card 분류,
            eyeStubCalls, panelMetrics, markConstants).

실패 처리 (무리한 추측 금지): S3/Firestore 접근 실패·P35/ii0 정본 부재 시
빠진 목록을 evidence/BLOCKER.md 에 명기하고 비영 종료 (대체 재료 발명 금지).
게이트 미달 침묵은 결함이 아니라 "정직한 침묵" — dropped 사유 그대로 기록.

프로덕션 코드 아님 — quick 로컬 드라이버. 채점 무접촉, 코드 수정 0.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import math
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_XA1 = _HERE.parent / "260811-xa1-mark-grammar-round-ufb-freeze-2-belle"

EVID = _HERE / "evidence"
# 현 세션 scratchpad (플랜 지시 — 이 플랜 환경의 세션 scratchpad 디렉터리)
SCRATCH = pathlib.Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "ae166167-1abf-4754-9fe8-336a719ef9e2/scratchpad"
)


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# grammar_round 로드 — 스텁/더미 키/인터프리터 승격/backend sys.path 전부 상속.
# import 시점에 vl.EV 를 xa1 로 돌려놓는데, 이 사이클 evidence 로 재재지정한다.
gr = _load_module("grammar_round", _XA1 / "grammar_round.py")
vl = gr.vl
vl.EV = EVID
vl.SPA = SCRATCH / "approved_sweep"

import app  # noqa: E402 - backend/functions/pipeline 운영 모듈 그대로 (무패치)
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

log = logging.getLogger("sweep_render")

MOTIONS = list(vl.SWEEP_JOBS)


def _guard_ev() -> None:
    """실행 전 필수 가드 (T-ivs-02) — 타 사이클 evidence 파괴 fail-closed."""
    assert "260813-ivs" in str(vl.EV), (
        f"EV 재지정 실패: {vl.EV} — ufb/xa1 evidence 파괴 위험, 실행 금지"
    )
    assert str(vl.SPA).startswith(str(SCRATCH)), (
        f"SPA 재지정 실패: {vl.SPA} — 죽은 구세션 scratchpad 부활 금지"
    )


def _preflight() -> list[str]:
    """P35 data + ii0 정본 재료 존재 확인 — 부재 시 목록 반환 (발명 금지)."""
    missing: list[str] = []
    for m in MOTIONS:
        for f in ("doc.json", "align.json"):
            p = vl.DATA / m / f
            if not p.exists():
                missing.append(str(p))
    for p in (vl.II0 / "probes.log", vl.II0 / "sweep_out" / "poles.json"):
        if not p.exists():
            missing.append(str(p))
    return missing


# ── 관찰 상태 (산출 무변경 — 관찰만) ─────────────────────────────────────────
class _Obs:
    def __init__(self):
        self.cur_motion: str | None = None
        self.cur_crit: str | None = None
        self.anchors: list[dict] = []
        self.anchor_drops: list[dict] = []
        self.builds: list[dict] = []
        self.member_pts: dict[str, list[dict]] = {}
        self.shifts: dict[str, list[dict]] = {}
        self.crops: dict[str, list[dict]] = {}
        self.draw_calls: dict[str, list[dict]] = {}
        self.bake_lines: list[dict] = []
        self.crop_lines: dict[str, list[str]] = {}
        self.s3_keys: list[str] = []
        self.s3_by_motion: dict[str, dict[str, list[str]]] = {}

    def key(self) -> str:
        return f"{self.cur_motion or '?'}|{self.cur_crit or '?'}"


OBS = _Obs()


class _LogTap(logging.Handler):
    """root 로거 캡처 — display_anchor args·crop 라인·angle_bake(문법 표기)."""

    def __init__(self):
        super().__init__(level=logging.INFO)

    def emit(self, record):  # noqa: D102
        try:
            msg = record.msg if isinstance(record.msg, str) else ""
            if msg.startswith("display_anchor drop"):
                OBS.anchor_drops.append({
                    "motion": OBS.cur_motion, "line": record.getMessage(),
                })
            elif msg.startswith("display_anchor"):
                a = record.args
                OBS.anchors.append({
                    "motion": OBS.cur_motion,
                    "rid": a[0], "joint": a[1],
                    "uAi": int(a[2]), "rAi": int(a[3]),
                    "user": [float(a[4]), float(a[5])],
                    "ref": [float(a[6]), float(a[7])],
                    "line": record.getMessage(),
                })
            elif msg.startswith("fault_zoom_crop"):
                OBS.crop_lines.setdefault(
                    OBS.cur_motion or "?", []).append(record.getMessage())
            elif msg.startswith("fault_zoom_angle_bake"):
                OBS.bake_lines.append({
                    "motion": OBS.cur_motion, "criterion": OBS.cur_crit,
                    "line": record.getMessage(),
                })
        except Exception:  # noqa: BLE001 - 캡처 실패는 드라이버 문제로만
            pass


class _Observer:
    """운영 함수 관찰 래퍼 — 산출 무변경 (verify_wiring _ShiftObserver 확장).

    · app._run_gated_card_inherit — analysis_id("sweep-{m}")로 현재 동작 추적.
    · fz.build_fault_zoom_comparisons — criterion_units[0] 스택 (crit 추적).
    · fz.shift_bake_spec — (spec 3점, anchor) 짝, 호출 순서 user → ref.
    · fz._side_crop — frame shape·crop_kind·box, 호출 순서 user → ref.
    · fz._draw_joint_angle / fz._draw_hybrid_joint_angle — 호출 실측 =
      카드별 문법 (hip=P3 하이브리드 / 기타=V, hybrid_fallback 은 bake 로그).
    · vl._S3Stub.put_object — 키 기록 ("/eye/" 키 vs 카드 키 분류).
    """

    def __init__(self):
        self._orig_helper = app._run_gated_card_inherit
        self._orig_build = fz.build_fault_zoom_comparisons
        self._orig_shift = fz.shift_bake_spec
        self._orig_crop = fz._side_crop
        self._orig_members = fz._member_pts
        self._orig_draw_v = fz._draw_joint_angle
        self._orig_draw_h = fz._draw_hybrid_joint_angle
        self._orig_put = vl._S3Stub.put_object

    def install(self):
        app._run_gated_card_inherit = self._helper
        fz.build_fault_zoom_comparisons = self._build
        fz.shift_bake_spec = self._shift
        fz._side_crop = self._crop
        fz._member_pts = self._members
        fz._draw_joint_angle = self._draw_v
        fz._draw_hybrid_joint_angle = self._draw_h
        obs = self

        def _put(stub_self, *, Bucket, Key, Body, ContentType):  # noqa: N803
            OBS.s3_keys.append(Key)
            by = OBS.s3_by_motion.setdefault(
                OBS.cur_motion or "?", {"cards": [], "eye": []})
            by["eye" if "/eye/" in Key else "cards"].append(Key)
            return obs._orig_put(
                stub_self, Bucket=Bucket, Key=Key, Body=Body,
                ContentType=ContentType)

        vl._S3Stub.put_object = _put

    def restore(self):
        app._run_gated_card_inherit = self._orig_helper
        fz.build_fault_zoom_comparisons = self._orig_build
        fz.shift_bake_spec = self._orig_shift
        fz._side_crop = self._orig_crop
        fz._member_pts = self._orig_members
        fz._draw_joint_angle = self._orig_draw_v
        fz._draw_hybrid_joint_angle = self._orig_draw_h
        vl._S3Stub.put_object = self._orig_put

    def _helper(self, *a, **k):
        aid = str(k.get("analysis_id") or "")
        OBS.cur_motion = aid[len("sweep-"):] if aid.startswith("sweep-") else aid
        return self._orig_helper(*a, **k)

    def _build(self, *a, **k):
        units = k.get("criterion_units") or []
        OBS.cur_crit = str(units[0].get("criterion")) if units else None
        OBS.builds.append({
            "motion": OBS.cur_motion, "criterion": OBS.cur_crit,
        })
        return self._orig_build(*a, **k)

    def _members(self, report, idx, members):
        """침묵 드랍 판별 재료 — D-12①(호출 0회) vs 양측 신뢰 0(2회, valid 0)."""
        out = self._orig_members(report, idx, members)
        OBS.member_pts.setdefault(OBS.key(), []).append({
            "idx": int(idx), "members": list(members),
            "nValid": len(out[0]), "nRelaxed": len(out[1]),
        })
        return out

    def _shift(self, spec, anchor):
        out = self._orig_shift(spec, anchor)
        if spec is not None and anchor is not None:
            OBS.shifts.setdefault(OBS.key(), []).append({
                "spec": [[float(p[0]), float(p[1])] for p in spec],
                "anchor": [float(anchor[0]), float(anchor[1])],
            })
        return out

    def _crop(self, frame, *a, **k):
        out = self._orig_crop(frame, *a, **k)
        # box None(full 폴백)도 기록 — D-12 침묵 드랍(같은 배율 불가)의 실측.
        # 호출 순서 = 카드당 user → ref (fault_zoom 3298/3306 결정론).
        OBS.crops.setdefault(OBS.key(), []).append({
            "shape": [int(frame.shape[0]), int(frame.shape[1])],
            "kind": str(out[1]),
            "box": [int(x) for x in out[3]] if out[3] is not None else None,
        })
        return out

    def _draw_v(self, img, vertex, limb, torso):
        ok = self._orig_draw_v(img, vertex, limb, torso)
        OBS.draw_calls.setdefault(OBS.key(), []).append(
            {"fn": "V", "ok": bool(ok)})
        return ok

    def _draw_h(self, img, vertex, limb, torso, ref_inner_deg):
        ok = self._orig_draw_h(img, vertex, limb, torso, ref_inner_deg)
        OBS.draw_calls.setdefault(OBS.key(), []).append(
            {"fn": "hybrid", "ok": bool(ok)})
        return ok


def _panel_metrics() -> dict:
    """부위/패널 비율 실측 — shifts(스펙 3점) x crops(박스) 짝으로 계산.

    스펙 3점은 정규화 프레임 좌표 (실관절: 꼭짓점/사지점/몸통점). 프레임 px 로
    환산한 최대 쌍거리 = 부위 스프레드. 패널 px 환산 = spread/side*_OUT
    (스펙 평행이동본이지만 스프레드는 이동 불변).

    패널 판별은 인덱스가 아니라 **anchor 좌표 = display_anchor 로그 args 대조**
    (단일 출처) — 한쪽 스펙이 None 이면 shift 호출이 빠져 인덱스 짝이 어긋난다
    (run 1 실측: elbow right_elbow 는 frac-user 스펙 None → 엔트리 1개 = ref).
    crops 는 카드당 user → ref 2회 호출 결정론이라 인덱스 짝 유지.
    """
    anchors_by_key: dict[str, dict] = {}
    for a in OBS.anchors:
        anchors_by_key[f"{a['motion']}|angle_vs_reference__{a['joint']}"] = a
    out: dict = {}
    for key, shs in OBS.shifts.items():
        crs = OBS.crops.get(key) or []
        anc = anchors_by_key.get(key)
        rows = []
        seen: set[str] = set()
        for sh in shs:
            panel = None
            if anc is not None:
                for side_name in ("user", "ref"):
                    exp = anc[side_name]
                    if math.hypot(sh["anchor"][0] - exp[0],
                                  sh["anchor"][1] - exp[1]) < 1e-9:
                        panel = side_name
                        break
            if panel is None or panel in seen:
                continue  # frac/bake 사이트 스펙 동일 — 패널당 1회면 충분
            seen.add(panel)
            ci = 0 if panel == "user" else 1
            if ci >= len(crs) or crs[ci]["box"] is None:
                continue
            h, w = crs[ci]["shape"]
            side = crs[ci]["box"][2]
            pts = [(p[0] * w, p[1] * h) for p in sh["spec"]]
            spread = max(
                math.hypot(a[0] - b[0], a[1] - b[1])
                for ai, a in enumerate(pts) for b in pts[ai + 1:]
            )
            rows.append({
                "panel": panel,
                "cropKind": crs[ci]["kind"],
                "cropSidePx": side,
                "frameDims": [int(w), int(h)],
                "specSpreadFramePx": round(spread, 1),
                "specSpreadPanelPx": round(spread / side * fz._OUT, 1),
                "partPerPanelPct": round(spread / side * 100.0, 1),
                "cropPerSourcePct": round(side / min(w, h) * 100.0, 1),
            })
        rows.sort(key=lambda r: r["panel"], reverse=True)  # user 먼저
        out[key] = rows
    return out


def _mark_constants() -> dict:
    """마크 고정 px (운영 상수 실측 인용 — 손 재유도 금지)."""
    o = float(fz._OUT)
    return {
        "panelOutPx": int(fz._OUT),
        "limbLinePx": round(fz._ANGLE_LIMB_LEN_FRAC * o, 1),
        "torsoLinePx": round(fz._ANGLE_TORSO_LEN_FRAC * o, 1),
        "arcRadiusPx": round(fz._ANGLE_ARC_R_FRAC * o, 1),
        "wedgeRadiusPx": round(fz._WEDGE_R_FRAC * o, 1),
        "limbMarkPerPanelPct": round(fz._ANGLE_LIMB_LEN_FRAC * 100.0, 1),
        "torsoMarkPerPanelPct": round(fz._ANGLE_TORSO_LEN_FRAC * 100.0, 1),
        "arcMarkPerPanelPct": round(fz._ANGLE_ARC_R_FRAC * 100.0, 1),
        "wedgeMarkPerPanelPct": round(fz._WEDGE_R_FRAC * 100.0, 1),
        "haloW": int(fz._ANGLE_HALO_W),
        "coreW": int(fz._ANGLE_CORE_W),
        "hybridSuffixes": sorted(fz.HYBRID_ANGLE_SUFFIXES),
    }


def sweep() -> int:
    _guard_ev()
    missing = _preflight()
    if missing:
        EVID.mkdir(exist_ok=True)
        (EVID / "BLOCKER.md").write_text(
            "# BLOCKER — 정본 재료 부재 (대체 재료 발명 금지)\n\n"
            + "\n".join(f"- `{m}`" for m in missing) + "\n"
        )
        print(f"BLOCKER: 정본 재료 {len(missing)}건 부재 — evidence/BLOCKER.md 박제")
        return 1

    EVID.mkdir(exist_ok=True)
    tap = _LogTap()
    obs = _Observer()
    logging.getLogger().addHandler(tap)
    obs.install()
    try:
        results = vl.sweep()
    finally:
        obs.restore()
        logging.getLogger().removeHandler(tap)

    measure = {
        "eyeStubCalls": gr._EYE_STUB["calls"],
        "displayAnchors": OBS.anchors,
        "displayAnchorDrops": OBS.anchor_drops,
        "builds": OBS.builds,
        "memberPts": OBS.member_pts,
        "shifts": OBS.shifts,
        "crops": OBS.crops,
        "drawCalls": OBS.draw_calls,
        "bakeLines": OBS.bake_lines,
        "cropLines": OBS.crop_lines,
        "s3Keys": OBS.s3_keys,
        "s3KeysByMotion": OBS.s3_by_motion,
        "panelMetrics": _panel_metrics(),
        "markConstants": _mark_constants(),
    }
    (EVID / "measure.json").write_text(
        json.dumps(measure, ensure_ascii=False, indent=1))

    n_cards = len([
        k for k in OBS.s3_keys if "/eye/" not in k and k.endswith(".png")
    ])
    n_emit = sum(len(r["verdict"]["survivors"]) for r in results.values())
    n_drop = sum(len(r["verdict"]["dropped"]) for r in results.values())
    print(
        f"SWEEP DONE motions={len(results)} emitted={n_emit} "
        f"silenced={n_drop} cards={n_cards} anchors={len(OBS.anchors)} "
        f"anchorDrops={len(OBS.anchor_drops)} "
        f"eyeStubCalls={gr._EYE_STUB['calls']} (machine_eye 스텁 — "
        "Gemini 실호출 0)"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.sweep:
        return sweep()
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
