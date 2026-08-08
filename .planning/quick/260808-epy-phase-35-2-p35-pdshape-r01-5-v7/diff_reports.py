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
  elbow — 수리 라운드(belle 08-08 v7 반려) 후 의도 상태:
    r00 = baseline(v6) 표시로 완전 복귀 — pairSrc==align, rt 12.07, 원 문구·원 mp3
      (폴-근접은 분위수 지속-분리 게이트로 자동 철회, poleViz 부재, 마커 링 복귀).
    r03 = 표시요소·문구만 변경 — ut/rt/pairSrc 불변, bodyViz user/ref 성립,
      markers==[](몸라인 문법 소유), text==오버라이드, freezeS=새 mp3 반영.
    r01·r02 행 불변(voiceStartOutS 는 r03 길이 변화로 이동 — 제외).
    outDurationS 차이 = r03 freezeS 차이 ±0.3.
    report_v7_pre_r03fix.json 존재 시: 직전 v7 대비 변경 = r00 복귀 + r03 표시 2건만.
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
for rid in ("r01", "r02"):
    check(same_row(rows(b)[rid], rows(v)[rid], NUM_TEXT),
          f"elbow {rid} 행 불변 (voiceStart 제외 — r03 길이 변화로 이동)")
# r00 = baseline 완전 복귀 (폴-근접 분위수 게이트 자동 철회 — belle 08-08 v7 반려)
r00b, r00v = rows(b)["r00"], rows(v)["r00"]
check(same_row(r00b, r00v, NUM_TEXT),
      f"elbow r00 행 == baseline 복귀 (pairSrc={r00v['pairSrc']} rt={r00v['refSec']} 원 문구·원 mp3)")
check(r00v.get("poleViz") is None, "elbow r00 poleViz 부재 (자동 철회)")
check(r00v.get("markers") == r00b.get("markers") and (r00v.get("markers") or []) != [],
      f"elbow r00 마커 링 복귀 {r00v.get('markers')}")
# r03 = 몸-폴 라인 문법 (표시·문구만 — ut/rt/pairSrc 불변)
r03b, r03v = rows(b)["r03"], rows(v)["r03"]
ov = json.load(open(OVERRIDES))
check(same_row(r03b, r03v, ("userSec", "refSec", "pairSrc")),
      f"elbow r03 ut/rt/pairSrc 불변 (ut={r03v['userSec']} rt={r03v['refSec']} src={r03v['pairSrc']})")
bv = r03v.get("bodyViz") or {}
check("user" in bv and "ref" in bv, f"elbow r03 bodyViz user/ref 성립 {bv}")
check(r03v.get("markers") == [], f"elbow r03 markers={r03v.get('markers')} == [] (몸라인 문법 소유)")
check(r03v["text"] == ov["r03"], "elbow r03 text == 오버라이드 문장")
check(abs(r03v["freezeS"] - r03b["freezeS"]) > 0.02,
      f"elbow r03 freezeS {r03b['freezeS']} -> {r03v['freezeS']} (새 mp3 반영)")
d_out = v["outDurationS"] - b["outDurationS"]
d_frz = r03v["freezeS"] - r03b["freezeS"]
check(abs(d_out - d_frz) <= 0.3,
      f"elbow outDuration 차이 {d_out:+.2f} == r03 freezeS 차이 {d_frz:+.2f} (±0.3)")

# 직전 v7(폴-근접판) 대비 — 변경 = r00 복귀 + r03 표시 2건만 (존재 시)
pre3 = SP / "p35" / "elbow" / "report_v7_pre_r03fix.json"
if pre3.exists():
    p = json.load(open(pre3))
    check(set(rows(p)) == set(rows(v)), "elbow(pre-r03fix 대비) rid 집합 동일")
    for rid in ("r01", "r02"):
        check(same_row(rows(p)[rid], rows(v)[rid], NUM_TEXT),
              f"elbow(pre-r03fix 대비) {rid} 행 불변")
    check(rows(p)["r00"]["pairSrc"] == "align-pole" and r00v["pairSrc"] == "align",
          "elbow(pre-r03fix 대비) r00 align-pole -> align 복귀")
    check(rows(p)["r03"]["text"] != r03v["text"] and rows(p)["r03"].get("bodyViz") is None,
          "elbow(pre-r03fix 대비) r03 문구·bodyViz 신규")

print()
if FAILS:
    print(f"DIFF GATE FAIL — {len(FAILS)}건")
    sys.exit(1)
print("DIFF GATE ALL PASS")
sys.exit(0)
