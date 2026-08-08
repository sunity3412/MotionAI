"""baseline↔v7 freeze 리포트 diff 게이트 (260808-epy Task 3-3).

의도 변경 외 diff 0 을 rid 단위로 기계 판정 — 전항목 PASS 아니면 업로드 금지 (D-00).

규칙:
  powerspin·kipup·peterpan — 전 freeze 행(userSec·refSec·pairSrc·freezeS·text·
    voiceStartOutS) 동일(수치 ±0.02) + outDurationS ±0.1.
    kipup r00 userSec = 1.47(±0.1) 명시 assert (피크 퇴행 즉시 검출 — 미세조정 1차
    실측 철회 선례).
  pdshapefault — r00·r02·r03 행 불변 + outDurationS ±0.1. r01 은 의도 상태 3가지 중
    하나만 허용: (a) align-grip 발동(refSec 변경 + pairSrc==align-grip) /
    (b) fail-closed(행 전체 baseline 동일 — 계획 ② 명시 경로) /
    (c) 명시 오버라이드(belle 08-08 (a) 결정: pairSrc==override + refSec==
    pdshape_pair_overrides.json 값 + ut/freeze/text 불변). 어느 쪽인지 출력.
    report_v7_pre_override.json 존재 시: 이전 v7 대비 변경 = r01 refSec 단 1건 assert.
  elbow — r00 만 변경: pairSrc==align-pole, poleViz user/ref 성립, text==오버라이드
    문장, freezeS=새 mp3 길이 반영, ut/rt 는 각각 atVideoSec±2.5s / curve±2.5s 창 안,
    마커는 폴 문법이 소유(markers==[]). r01·r02·r03 행 불변(voiceStartOutS 는 r00
    길이 변화로 뒤 행이 이동하므로 제외). outDurationS 차이 = r00 freezeS 차이 ±0.3.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SP = Path("/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/e6ff396b-4e73-4d48-b163-2b06d562d292/scratchpad")
DATA = Path("/Users/kimtaesung/Dev/SunityMotion/.planning/phases/35-server-rendered-comparison-video/data")
OVERRIDES = Path(__file__).parent / "elbow_text_overrides.json"

FAILS: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
    if not cond:
        FAILS.append(msg)


def rows(report: dict) -> dict[str, dict]:
    return {f["rid"]: f for f in report["freezes"]}


def same_row(a: dict, b: dict, fields: tuple[str, ...], tol: float = 0.02) -> bool:
    for f in fields:
        va, vb = a.get(f), b.get(f)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            if abs(va - vb) > tol:
                return False
        elif va != vb:
            return False
    return True


NUM_TEXT = ("userSec", "refSec", "pairSrc", "freezeS", "text")

for m in ("powerspin", "kipup", "peterpan"):
    b = json.load(open(SP / "p35" / m / "report_baseline.json"))
    v = json.load(open(SP / "p35" / m / "report_v7.json"))
    print(f"=== {m} ===")
    check(set(rows(b)) == set(rows(v)), f"{m} rid 집합 동일 {sorted(rows(v))}")
    for rid in rows(b):
        check(same_row(rows(b)[rid], rows(v)[rid], NUM_TEXT + ("voiceStartOutS",)),
              f"{m} {rid} 행 불변")
    check(abs(b["outDurationS"] - v["outDurationS"]) <= 0.1,
          f"{m} outDurationS {b['outDurationS']} -> {v['outDurationS']} (±0.1)")

kb = json.load(open(SP / "p35" / "kipup" / "report_v7.json"))
u = rows(kb)["r00"]["userSec"]
check(abs(u - 1.47) <= 0.1, f"kipup r00 userSec={u:.3f} == 1.47(±0.1)")

print("=== pdshapefault ===")
b = json.load(open(SP / "p35" / "pdshapefault" / "report_baseline.json"))
v = json.load(open(SP / "p35" / "pdshapefault" / "report_v7.json"))
check(set(rows(b)) == set(rows(v)), f"pdshapefault rid 집합 동일 {sorted(rows(v))}")
for rid in ("r00", "r02", "r03"):
    check(same_row(rows(b)[rid], rows(v)[rid], NUM_TEXT + ("voiceStartOutS",)),
          f"pdshapefault {rid} 행 불변")
r01b, r01v = rows(b)["r01"], rows(v)["r01"]
if r01v["pairSrc"] == "override":
    pov = json.load(open(Path(__file__).parent / "pdshape_pair_overrides.json"))
    check(abs(r01v["refSec"] - float(pov["r01"]["refVideoSec"])) <= 0.02,
          f"pdshapefault r01 refSec={r01v['refSec']} == 명시값 {pov['r01']['refVideoSec']}")
    check(same_row(r01b, r01v, ("userSec", "freezeS", "text", "voiceStartOutS")),
          "pdshapefault r01 ut/freeze/text/voiceStart 불변 (rt 만 명시 교체)")
    print("  -> r01 상태 = (c) 명시 오버라이드 (belle 08-08 (a) 결정)")
elif r01v["pairSrc"] == "align-grip":
    check(abs(r01v["refSec"] - r01b["refSec"]) > 0.02, "pdshapefault r01 refSec 변경 (grip 발동)")
    check(same_row(r01b, r01v, ("userSec", "freezeS", "text")), "pdshapefault r01 ut/freeze/text 불변")
    print("  -> r01 상태 = (a) align-grip 발동")
else:
    check(same_row(r01b, r01v, NUM_TEXT + ("voiceStartOutS",)),
          "pdshapefault r01 행 전체 불변 (fail-closed — 계획 ② 명시 경로, belle 지시 미충족 SUMMARY 박제)")
    print("  -> r01 상태 = (b) fail-closed (기존 짝 유지)")
check(abs(b["outDurationS"] - v["outDurationS"]) <= 0.1,
      f"pdshapefault outDurationS {b['outDurationS']} -> {v['outDurationS']} (±0.1)")

# 이전 v7(오버라이드 전) 대비 단일 변경 assert — 존재 시에만 (scratchpad 소실 허용)
pre_path = SP / "p35" / "pdshapefault" / "report_v7_pre_override.json"
if pre_path.exists():
    pre = json.load(open(pre_path))
    check(set(rows(pre)) == set(rows(v)), "pdshapefault(pre-override 대비) rid 집합 동일")
    for rid in ("r00", "r02", "r03"):
        check(same_row(rows(pre)[rid], rows(v)[rid], NUM_TEXT + ("voiceStartOutS",)),
              f"pdshapefault(pre-override 대비) {rid} 행 불변")
    p01 = rows(pre)["r01"]
    check(same_row(p01, r01v, ("userSec", "freezeS", "text", "voiceStartOutS")),
          "pdshapefault(pre-override 대비) r01 rt 외 전 필드 불변")
    check(abs(p01["refSec"] - r01v["refSec"]) > 0.02 and r01v["pairSrc"] == "override",
          f"pdshapefault(pre-override 대비) 변경 = r01 refSec {p01['refSec']} -> {r01v['refSec']} 단 1건")
    check(abs(pre["outDurationS"] - v["outDurationS"]) <= 0.1,
          "pdshapefault(pre-override 대비) outDurationS 불변")

print("=== elbow ===")
b = json.load(open(SP / "p35" / "elbow" / "report_baseline.json"))
v = json.load(open(SP / "p35" / "elbow" / "report_v7.json"))
check(set(rows(b)) == set(rows(v)), f"elbow rid 집합 동일 {sorted(rows(v))}")
for rid in ("r01", "r02", "r03"):
    check(same_row(rows(b)[rid], rows(v)[rid], NUM_TEXT),
          f"elbow {rid} 행 불변 (voiceStart 제외 — r00 길이 변화로 이동)")
r00b, r00v = rows(b)["r00"], rows(v)["r00"]
check(r00v["pairSrc"] == "align-pole", f"elbow r00 pairSrc={r00v['pairSrc']} == align-pole")
pv = r00v.get("poleViz") or {}
check("user" in pv and "ref" in pv, f"elbow r00 poleViz user/ref 성립 {pv}")
check(r00v.get("markers") == [], f"elbow r00 markers={r00v.get('markers')} == [] (폴 문법 소유)")
ov = json.load(open(OVERRIDES))
check(r00v["text"] == ov["r00"], "elbow r00 text == 오버라이드 문장")
# freezeS = 새 mp3 길이 + 0.4 — 재합성 mp3 6.29s 실측 반영 확인
align = json.load(open(DATA / "elbow" / "align.json"))
at = 11.111  # doc r00 atVideoSec (렌더 대상 창의 기준)
afps = float(align["fps"])
curve = align["curveRefSec"]
ct = float(curve[min(int(round(at * afps)), len(curve) - 1)])
check(abs(r00v["userSec"] - at) <= 2.5, f"elbow r00 ut={r00v['userSec']:.2f} in atVideoSec±2.5s")
check(abs(r00v["refSec"] - ct) <= 2.5, f"elbow r00 rt={r00v['refSec']:.2f} in curve({at:.2f})={ct:.2f}±2.5s")
check(abs(r00v["freezeS"] - r00b["freezeS"]) > 0.02,
      f"elbow r00 freezeS {r00b['freezeS']} -> {r00v['freezeS']} (새 mp3 반영)")
d_out = v["outDurationS"] - b["outDurationS"]
d_frz = r00v["freezeS"] - r00b["freezeS"]
check(abs(d_out - d_frz) <= 0.3,
      f"elbow outDuration 차이 {d_out:+.2f} == r00 freezeS 차이 {d_frz:+.2f} (±0.3)")

print()
if FAILS:
    print(f"DIFF GATE FAIL — {len(FAILS)}건")
    sys.exit(1)
print("DIFF GATE ALL PASS")
sys.exit(0)
