#!/usr/bin/env python3
"""축 반전 눈-우선 검증 하네스 (quick-260816-p1x) — belle 판정 재료 생산 전용.

belle 가 2026-08-16 원안("폴거리를 트랙이 먼저 주장하고 눈이 확인")을 뒤집었다.
근거는 두 실측: (1) 좌표가 깨진 동작(elbow)에서는 트랙-주장 구조가 원리적으로
무력하다 — 후보 12건이 전부 기계 눈에 기각됐다. (2) 좌표·마크 없이 짝 이미지를
그대로 눈에게 물었더니 belle 가 사전에 짚은 차이가 그대로 나왔다(elbow 3/3
일치). 단 눈은 틀릴 수도 있다 — peterpan 짝에서 폴 밀착 방향을 belle 판독과
반대로 답했고, 그 오답을 수치(발목-폴 거리)가 잡았다.

그래서 구조를 뒤집는다:
    구(폐기): 수치가 주장한다 → 눈이 검증한다   (축이 좁고, 좌표가 깨지면 무력)
    신(채택): 눈이 후보를 낸다 → 수치가 검증한다  (축 제약 없음, 지어낸 것은 수치로 걸림)

폴거리는 "주장하는 축"에서 "검증기"로 자리를 옮긴다. 관절각도·사지기울기도
같은 검증기 목록에 함께 들어간다.

이 사이클은 belle 판정 재료 생산까지다. 운영 코드·채점·S3 업로드·Firestore
쓰기 전부 무접촉 — card_gates/fault_zoom/skeleton/discover_sweep 은 전부
**임포트 재사용**(수정 0). 대상 = elbow, peterpan 만 눈-우선+검증 전량 실행.
kipup/pdshapefault/powerspin 은 좌표 품질표(align.json 만)만 산출해 대조
맥락으로 남긴다.

동작명 분기 0 (D-41 계열 규율 준수) — 모든 함수는 report/track 형상만 본다.

stages (CLI):
  --quality-gate  5동작(align.json 만) 좌표 품질표 산출 → evidence/quality_gate.json
  --smoke         기존 ehz 짝 스틸 2건(elbow/peterpan)으로 eye_propose 스모크
  --run           elbow·peterpan poseMin 후보 ≤20건 눈 제안 + 수치 검증 + 3버킷
                  → evidence/{motion}/eyefirst_verdicts.json (--cache-root 필요)

S3 read-only(재다운로드, source_gate 상속) · Pod 무접촉 · Firestore 쓰기 0
(refmotion 읽기만, mount() 상속) · 채점 무접촉 · Gemini = eye_propose 호출만.
키 = SSM --profile sunity-motion(키 값 로그 금지). 캐시 루트(scratchpad)는
휘발 — 보존 재료는 evidence/ 커밋분만이다.
"""

from __future__ import annotations

import argparse
import base64
import datetime as _dt
import json
import logging
import math
import os
import pathlib
import sys
import urllib.error
import urllib.request

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "backend" / "shared" / "python"))
sys.path.insert(0, str(_REPO / ".planning" / "quick" / "260814-ehz-5"))

import discover_sweep as ds  # noqa: E402 - sys.path 삽입 후 임포트
from sunity_shared.analysis import card_gates as cg  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_ANGLES  # noqa: E402

EV = _HERE / "evidence"
EHZ_EVIDENCE = _REPO / ".planning" / "quick" / "260814-ehz-5" / "evidence"

log = logging.getLogger("eyefirst_verify")

# ── 하네스 한정자 (게이트 임계 아님 — card_gates 임계는 재튜닝 0) ─────────────
# CONTRA_CUTOFF/LOWCONF_CUTOFF — 좌표 품질 라벨 컷오프. 오늘 실측(§Context)
# elbow(모순 3.7%/7.8%, 저신뢰 20.1%/22.3%)와 peterpan/kipup(모순 0%/0%, 저신뢰
# 0%/2.7%) 사이 값 — 둘을 가르기만 하면 되므로 중간 어디든 되지만, 자릿수가
# 뚜렷이 다른 지점(모순 2%, 저신뢰 10%)을 택해 향후 다른 동작이 추가돼도 여유가
# 있게 했다.
CONTRA_CUTOFF = 0.02
LOWCONF_CUTOFF = 0.10

# MAX_CANDS_PER_RECORD — 압축 상한. ehz(discover_sweep.MAX_CANDS_PER_RECORD)와
# 같은 규율·같은 값(4)이지만 이 하네스의 압축 단위(poseMin 최근접)가 달라 별도
# 상수로 신설한다(plan §context "이 하네스에도 같은 값 4 로 신설").
MAX_CANDS_PER_RECORD = 4

# 검증기 tie-band — 이 사이클에서 **신설**하는 값(기존 card_gates 게이트 임계와
# 달리 재튜닝 금지 대상 아님, belle 판정 후 근거와 함께 조정 가능).
#   POLE_TIE_TORSO: peterpan 실측 학생/기준 발목-폴 거리차 약 0.4 몸통배수보다
#     충분히 작게 잡아 노이즈만 거른다(§Context verification_notes 실측치).
POLE_TIE_TORSO = 0.15
ANGLE_TIE_DEG = 10.0
TILT_TIE_DEG = 8.0

_AXES = ("pole_distance", "joint_angle", "limb_tilt", "unmeasurable")
_SIDES = ("left", "right", "both", "unclear", "none")
_MORE_SIDES = ("student", "reference", "similar", "unclear")
_JOINT_ENUM = tuple(JOINT_ANGLES.keys()) + ("none",)


# ── (1) 좌표 품질 지표 — align.json 만, 영상/Gemini 불요 ─────────────────────

def _sign(v: float) -> int:
    if v > 0:
        return 1
    if v < 0:
        return -1
    return 0


def contradiction_rate(align: dict, side: str) -> float:
    """해부학 모순율 — "무릎이 엉덩이보다 위인데 발목이 엉덩이보다 아래" 패턴.

    좌/우 각각 hip/knee/ankle 세 점을 conf 게이트 없이(finite 만, fz._kp_xy)
    얻어 sign(knee_y-hip_y) != sign(ankle_y-hip_y) 이면 그 다리를 모순으로 본다.
    한쪽이라도 모순이면 그 프레임을 카운트. 분모 = 좌우 어느 한쪽이라도 세 점이
    finite 인 프레임 수 (양쪽 다 결측인 프레임은 판정 불가라 분모에서 뺀다).
    """
    key = "user" if side == "student" else "ref"
    rep = cg.align_to_report(align, key)
    frames = int(rep.get("frames") or 0)
    num, den = 0, 0
    for f in range(frames):
        any_present = False
        contradicted = False
        for prefix in ("left", "right"):
            hip = fz._kp_xy(rep, f, f"{prefix}_hip")  # noqa: SLF001
            knee = fz._kp_xy(rep, f, f"{prefix}_knee")  # noqa: SLF001
            ankle = fz._kp_xy(rep, f, f"{prefix}_ankle")  # noqa: SLF001
            if hip is None or knee is None or ankle is None:
                continue
            any_present = True
            if _sign(knee[1] - hip[1]) != _sign(ankle[1] - hip[1]):
                contradicted = True
        if any_present:
            den += 1
            if contradicted:
                num += 1
    return (num / den) if den else 0.0


def lowconf_rate(align: dict, side: str) -> float:
    """저신뢰율 — POSE_BASIS_12 12관절 x 전 프레임 중 conf<_KP_CONF_MIN 비율.

    conf 부재(legacy/이름공간 미매핑)도 "신뢰를 증명 못한 좌표"로 저신뢰에
    합산한다(fail-closed — fz._KP_CONF_MIN 재사용, 신규 임계 아님).
    """
    key = "user" if side == "student" else "ref"
    rep = cg.align_to_report(align, key)
    frames = int(rep.get("frames") or 0)
    total = frames * len(cg.POSE_BASIS_12)
    if total <= 0:
        return 0.0
    low = 0
    for f in range(frames):
        for j in cg.POSE_BASIS_12:
            c = fz._kp_conf(rep, f, j)  # noqa: SLF001
            if c is None or c < fz._KP_CONF_MIN:  # noqa: SLF001
                low += 1
    return low / total


def compute_quality_gate() -> dict:
    """5동작(SWEEP_JOBS 키 그대로, 신규/삭제 0) 좌표 품질표 — align.json 만."""
    out: dict = {}
    for m in ds.SWEEP_JOBS:
        align = json.loads((ds.DATA / m / "align.json").read_text())
        cr_s, cr_r = contradiction_rate(align, "student"), contradiction_rate(align, "reference")
        lc_s, lc_r = lowconf_rate(align, "student"), lowconf_rate(align, "reference")
        low = (cr_s > CONTRA_CUTOFF or cr_r > CONTRA_CUTOFF
               or lc_s > LOWCONF_CUTOFF or lc_r > LOWCONF_CUTOFF)
        out[m] = {
            "contradictionRate": {"student": round(cr_s, 4), "reference": round(cr_r, 4)},
            "lowConfRate": {"student": round(lc_s, 4), "reference": round(lc_r, 4)},
            "label": "low" if low else "high",
        }
    return out


def _print_quality_table(qg: dict) -> None:
    print(f"{'motion':<14}{'contra(s/r)':<18}{'lowconf(s/r)':<20}{'label':<6}")
    for m, row in qg.items():
        cr = row["contradictionRate"]
        lc = row["lowConfRate"]
        print(f"{m:<14}{cr['student']:.3f}/{cr['reference']:<10.3f}"
              f"{lc['student']:.3f}/{lc['reference']:<12.3f}{row['label']:<6}")


# ── (2) hip→ankle 기울기 ─────────────────────────────────────────────────────

def limb_tilt_deg(report: dict, idx: int, side: str,
                   size: tuple[int, int]) -> float | None:
    """다리(hip->ankle) 가 수직에서 벌어진 정도. 0도=수직 ~ 90도=수평.

    side="both" 는 좌우 각각 계산해 둘 다 유효하면 평균, 하나만 유효하면 그
    값, 둘 다 무효면 None — 다리 방향 결함이 한쪽만 관측돼도 정직하게 반영.
    """
    if side == "both":
        left = limb_tilt_deg(report, idx, "left", size)
        right = limb_tilt_deg(report, idx, "right", size)
        vals = [v for v in (left, right) if v is not None]
        if not vals:
            return None
        return sum(vals) / len(vals)
    hip = cg.kp(report, idx, f"{side}_hip")
    ankle = cg.kp(report, idx, f"{side}_ankle")
    if hip is None or ankle is None:
        return None
    W, H = size
    dx = (ankle[0] - hip[0]) * W
    dy = (ankle[1] - hip[1]) * H
    return math.degrees(math.atan2(abs(dx), abs(dy)))


# ── (3) 눈-우선 제안 호출 (Gemini, cg.machine_eye 와 같은 urllib 패턴) ───────

_GEMINI_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
               "{model}:generateContent?key={key}")

_EYE_PROPOSE_PROMPT = (
    "이 이미지는 왼쪽에 학생 정지 프레임, 오른쪽에 기준(프로) 정지 프레임을 "
    "나란히 붙인 것이다. 두 자세의 형태 차이를 최대 3개까지 자연어로 설명하라. "
    "관절 각도 숫자는 언급하지 마라. 각 차이마다: (a) 폴(세로 봉)과의 거리 "
    "문제인지 / 관절이 접히거나 펴진 정도 문제인지 / 다리가 수직에서 벌어진 "
    "정도 문제인지 / 이 셋으로 못 재는 것(근육 긴장 등 느낌)인지 분류하라. "
    "(b) 관절 문제면 어느 관절인지, 폴거리·다리방향 문제면 어느 쪽 다리인지"
    "(왼쪽/오른쪽/양쪽/불명확) 밝혀라. (c) 학생과 기준 중 어느 쪽이 그 특성을 "
    "더 강하게 보이는지 밝혀라 — 폴거리는 폴에서 더 멀리 떨어진 쪽, 관절은 더 "
    "접힌(굽은) 쪽, 다리방향은 수직에서 더 크게 벌어진 쪽이 기준이다."
)

_EYE_PROPOSE_SCHEMA = {
    "type": "object",
    "properties": {
        "differences": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "axis": {"type": "string", "enum": list(_AXES)},
                    "joint": {"type": "string", "enum": list(_JOINT_ENUM)},
                    "side": {"type": "string", "enum": list(_SIDES)},
                    "moreSide": {"type": "string", "enum": list(_MORE_SIDES)},
                },
                "required": ["description", "axis", "joint", "side", "moreSide"],
            },
        },
    },
    "required": ["differences"],
}


def eye_propose(pair_img_path, api_key: str, model: str = "gemini-3.5-flash") -> dict:
    """짝 스틸(전신, 무마크) -> 눈이 낸 형태 차이 최대 3개. fail-closed.

    machine_eye(card_gates.py 489-551행)와 같은 urllib 직접 호출 패턴 — SDK
    의존 0, temperature 0 + response_schema 로 enum 강제. 이미지는 크롭/마크
    없이 원본 그대로(이 사이클의 핵심 차이 — 눈이 좌표를 보지 않는다).
    실패(네트워크/파싱/스키마 위반)는 {"differences": [], "error": ...}.
    """
    p = pathlib.Path(pair_img_path)
    try:
        img_bytes = p.read_bytes()
    except OSError as e:  # noqa: BLE001 - 파일 부재도 fail-closed
        return {"differences": [], "error": f"{type(e).__name__}: {e}"}
    b64 = base64.b64encode(img_bytes).decode("ascii")
    body = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
            {"text": _EYE_PROPOSE_PROMPT},
        ]}],
        "generationConfig": {
            "temperature": 0,
            "response_mime_type": "application/json",
            "response_schema": _EYE_PROPOSE_SCHEMA,
        },
    }
    req = urllib.request.Request(
        _GEMINI_URL.format(model=model, key=api_key),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60.0) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        got = json.loads(text)
        raw_diffs = got.get("differences") or []
        out = []
        for it in raw_diffs[:3]:
            if not isinstance(it, dict):
                continue
            # 스키마가 강제해도 텍스트 파싱 결과는 재검증한다(fail-closed).
            out.append({
                "description": str(it.get("description", "")),
                "axis": it.get("axis") if it.get("axis") in _AXES else "unmeasurable",
                "joint": it.get("joint") if it.get("joint") in _JOINT_ENUM else "none",
                "side": it.get("side") if it.get("side") in _SIDES else "unclear",
                "moreSide": it.get("moreSide") if it.get("moreSide") in _MORE_SIDES else "unclear",
            })
        return {"differences": out}
    except Exception as e:  # noqa: BLE001 - 네트워크/파싱 실패는 fail-closed 로 수렴
        return {"differences": [], "error": f"{type(e).__name__}: {e}"}


# ── (Task 2) poseMin 후보 선정 ───────────────────────────────────────────────

def select_candidates(motion: str) -> list[tuple[str, str, list[tuple[str, dict]]]]:
    """ehz candidates.json 의 poseMin(found=true) 을 poseDist 오름차순 top-N.

    claimContrast 압축(ehz 원 규율)이 아니라 poseMin(claim 무관 최근접 짝) 을
    후보 소스로 쓴다(§Context "후보 소스 전환") — 재스캔/hold_gate/pair_gate
    재실행 0, 이미 계산된 candidates.json 값만 읽는다.
    """
    data = json.loads((EHZ_EVIDENCE / motion / "candidates.json").read_text())
    out: list[tuple[str, str, list[tuple[str, dict]]]] = []
    for rec in data.get("records") or []:
        rid = str(rec["rid"])
        joint = str(rec["joint"])
        founds = [c for c in (rec.get("candidates") or []) if c["poseMin"]["found"]]
        founds.sort(key=lambda c: c["poseMin"]["row"]["pair"]["poseDist"])
        top = founds[:MAX_CANDS_PER_RECORD]
        picks = [(f"cand{i + 1:02d}", c["poseMin"]["row"]) for i, c in enumerate(top)]
        out.append((rid, joint, picks))
    return out


def compose_pair_still(ctx, rid: str, cid: str, uSec: float, rSec: float):
    """학생|기준 무축소 가로 결합 짝 스틸 — 마크/링/좌표 표시 없음(이 사이클의
    핵심 차이). ehz pairsheet() 와 같은 문법(8px (24,24,24) 구분선)."""
    from PIL import Image

    iu = Image.fromarray(ds._frame_rgb(ctx, "user", uSec))  # noqa: SLF001
    ir = Image.fromarray(ds._frame_rgb(ctx, "ref", rSec))  # noqa: SLF001
    H = max(iu.height, ir.height)
    out = Image.new("RGB", (iu.width + ir.width + 8, H), (24, 24, 24))
    out.paste(iu, (0, 0))
    out.paste(ir, (iu.width + 8, 0))
    dst = EV / ctx.m / "stills" / f"{rid}_{cid}_PAIR_u{uSec}s_r{rSec}s.jpg"
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst, quality=92)
    return dst


# ── (Task 2) 수치 검증 — 눈이 낸 후보를 폴거리/관절각도/사지기울기로 대조 ────

def verify_difference(ctx, u_idx: int, r_idx: int, diff: dict,
                       quality_label: str) -> dict:
    """눈의 difference 1건을 수치로 검증 -> promoted/rejected/unmeasurable.

    분류 규칙(plan §truths 2):
      axis="unmeasurable" 이거나 필요 좌표/수치가 None 이거나 numericMore가
      "similar" 이거나 눈의 moreSide 가 similar/unclear 면 unmeasurable(기각과
      분리). 그 외 moreSide==numericMore 면 promoted, 다르면 rejected.
    """
    axis = diff.get("axis")
    out = dict(diff)
    out["qualityLabel"] = quality_label
    out["numeric"] = None
    out["numericMore"] = None

    if axis == "unmeasurable":
        out["bucket"] = "unmeasurable"
        out["reason"] = "눈이 수치화 불가로 분류"
        out["belleDirectionMatch"] = "해당없음(다른 axis)"
        return out

    if axis == "pole_distance":
        pu, pr = ctx.poles.get("user"), ctx.poles.get("ref")
        if pu is None or pr is None:
            out["bucket"] = "unmeasurable"
            out["reason"] = "폴 미검출(x_norm 없음) — 폴거리 계산 불가"
            out["belleDirectionMatch"] = "해당없음(다른 axis)"
            return out
        du = cg.body_pole_dist(ctx.urep, u_idx, pu, ctx.usize, ctx.u_torso)
        dr = cg.body_pole_dist(ctx.rrep, r_idx, pr, ctx.rsize, ctx.r_torso)
        if du is None or dr is None:
            out["numeric"] = {"student": du, "reference": dr, "metric": "bodyPoleDist_torsoUnit"}
            out["bucket"] = "unmeasurable"
            out["reason"] = "힙/어깨 좌표 부재로 몸중심-폴 거리 계산 불가"
            out["belleDirectionMatch"] = "해당없음(다른 axis)"
            return out
        d = du - dr
        num_more = "student" if d > POLE_TIE_TORSO else (
            "reference" if d < -POLE_TIE_TORSO else "similar")
        out["numeric"] = {"student": round(du, 4), "reference": round(dr, 4),
                           "metric": "bodyPoleDist_torsoUnit"}
        out["numericMore"] = num_more
        # belle 실측 방향(§Context: "학생이 폴에 더 가깝다" = du<dr) 대조 —
        # numericMore 어휘로는 그 방향이 "reference"(기준이 더 멀다=폴거리
        # 특성이 더 강함) 이다. tie(similar) 는 방향 미확정이라 불일치로 본다.
        out["belleDirectionMatch"] = (num_more == "reference")
    elif axis == "joint_angle":
        joint = diff.get("joint")
        if joint not in JOINT_ANGLES:
            out["bucket"] = "unmeasurable"
            out["reason"] = "관절 태그 무효(JOINT_ANGLES 8키 아님)"
            out["belleDirectionMatch"] = "해당없음(다른 axis)"
            return out
        ua = cg.joint_angle(ctx.urep, u_idx, joint)
        ra = cg.joint_angle(ctx.rrep, r_idx, joint)
        if ua is None or ra is None:
            out["numeric"] = {"student": ua, "reference": ra, "metric": "jointAngleDeg"}
            out["bucket"] = "unmeasurable"
            out["reason"] = "관절각 좌표 부재로 계산 불가"
            out["belleDirectionMatch"] = "해당없음(다른 axis)"
            return out
        bent_diff = ra - ua  # 양수 = 학생이 더 접힘(ua 가 더 작음)
        num_more = "student" if bent_diff > ANGLE_TIE_DEG else (
            "reference" if bent_diff < -ANGLE_TIE_DEG else "similar")
        out["numeric"] = {"student": round(ua, 2), "reference": round(ra, 2),
                           "metric": "jointAngleDeg"}
        out["numericMore"] = num_more
        out["belleDirectionMatch"] = "해당없음(다른 axis)"
    elif axis == "limb_tilt":
        side = diff.get("side")
        if side not in ("left", "right", "both"):
            out["bucket"] = "unmeasurable"
            out["reason"] = "side 태그 무효(left/right/both 아님)"
            out["belleDirectionMatch"] = "해당없음(다른 axis)"
            return out
        tu = limb_tilt_deg(ctx.urep, u_idx, side, ctx.usize)
        tr = limb_tilt_deg(ctx.rrep, r_idx, side, ctx.rsize)
        if tu is None or tr is None:
            out["numeric"] = {"student": tu, "reference": tr, "metric": "limbTiltDeg"}
            out["bucket"] = "unmeasurable"
            out["reason"] = "hip/ankle 좌표 부재로 기울기 계산 불가"
            out["belleDirectionMatch"] = "해당없음(다른 axis)"
            return out
        d = tu - tr
        num_more = "student" if d > TILT_TIE_DEG else (
            "reference" if d < -TILT_TIE_DEG else "similar")
        out["numeric"] = {"student": round(tu, 2), "reference": round(tr, 2),
                           "metric": "limbTiltDeg"}
        out["numericMore"] = num_more
        out["belleDirectionMatch"] = "해당없음(다른 axis)"
    else:
        out["bucket"] = "unmeasurable"
        out["reason"] = f"미지의 axis: {axis!r}"
        out["belleDirectionMatch"] = "해당없음(다른 axis)"
        return out

    more_side = diff.get("moreSide")
    if out["numericMore"] == "similar":
        out["bucket"] = "unmeasurable"
        out["reason"] = "수치 차이가 tie-band 이내 — 방향 불확정"
    elif more_side in ("similar", "unclear"):
        out["bucket"] = "unmeasurable"
        out["reason"] = f"눈이 moreSide={more_side} 로 답해 방향 불확정"
    elif more_side == out["numericMore"]:
        out["bucket"] = "promoted"
        out["reason"] = "눈 서술 방향과 수치 방향 일치"
    else:
        out["bucket"] = "rejected"
        out["reason"] = f"눈={more_side} vs 수치={out['numericMore']} 불일치"
    return out


# ── 스모크 (Task 1-4) — 기존 ehz 짝 스틸 2건 재사용, 신규 다운로드/마운트 0 ──

_SMOKE_PAIRS = {
    "elbow": EHZ_EVIDENCE / "elbow" / "stills" / "r03_cand11B_PAIR_u10.7333s_r13.7333s.jpg",
    "peterpan": EHZ_EVIDENCE / "peterpan" / "stills" / "r00_cand03E_PAIR_u2.2667s_r2.2667s.jpg",
}


def run_smoke() -> dict:
    ds._ensure_gemini_key()  # noqa: SLF001 - SSM -> GEMINI_API_KEY env, 값 로그 0
    api_key = os.environ["GEMINI_API_KEY"]
    smoke_dir = EV / "smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    out: dict = {}
    for name, p in _SMOKE_PAIRS.items():
        if not p.exists():
            raise SystemExit(f"스모크 원본 스틸 부재: {p}")
        res = eye_propose(p, api_key)
        (smoke_dir / f"{name}.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=1))
        diffs = res.get("differences") or []
        print(f"SMOKE {name}: {len(diffs)} differences"
              f"{' (error=' + res['error'] + ')' if res.get('error') else ''}")
        for d in diffs:
            print(f"  axis={d['axis']} joint={d['joint']} side={d['side']} "
                  f"moreSide={d['moreSide']} :: {d['description'][:70]}")
        out[name] = res
    return out


# ── (Task 2) 전량 실행 — 마운트 + 후보 전건 눈 제안 + 수치 검증 ─────────────

def run_candidates(motions: list[str], cache_root: pathlib.Path) -> dict:
    ds._CACHE_ROOT = cache_root  # noqa: SLF001 - ds._cr_root() 가 참조하는 모듈 전역
    cache_root.mkdir(parents=True, exist_ok=True)
    qg_path = EV / "quality_gate.json"
    if not qg_path.exists():
        raise SystemExit("quality_gate.json 부재 — 먼저 --quality-gate 실행")
    qg = json.loads(qg_path.read_text())
    ds._ensure_gemini_key()  # noqa: SLF001
    api_key = os.environ["GEMINI_API_KEY"]

    all_out: dict = {}
    total_calls = 0
    for m in motions:
        print(f"══ RUN {m} ══")
        gate = ds.source_gate(m, download=True)
        if not gate["passed"]:
            raise SystemExit(f"{m} source gate FAIL(로컬 불가): {gate['reasons']}")
        ctx = ds.mount(m)
        record_picks = select_candidates(m)
        call_count_by_rid: dict[str, int] = {}
        recs_out = []
        for rid, joint, picks in record_picks:
            cands_out = []
            for cid, row in picks:
                still = compose_pair_still(ctx, rid, cid, row["uSec"], row["rSec"])
                used = call_count_by_rid.get(rid, 0)
                if used >= ds.EYE_CALL_CAP:
                    eye_raw = {"differences": [],
                               "error": f"call cap reached ({ds.EYE_CALL_CAP}/record)"}
                else:
                    eye_raw = eye_propose(still, api_key)
                    call_count_by_rid[rid] = used + 1
                    total_calls += 1
                q_label = qg[m]["label"]
                diffs_out = [
                    verify_difference(ctx, row["uIdx"], row["rIdx"], d, q_label)
                    for d in (eye_raw.get("differences") or [])
                ]
                cands_out.append({
                    "cid": cid, "uSec": row["uSec"], "rSec": row["rSec"],
                    "uIdx": row["uIdx"], "rIdx": row["rIdx"],
                    "poseDist": row["pair"]["poseDist"],
                    "stillPair": str(still.relative_to(EV / m)),
                    "eyeRaw": eye_raw,
                    "differences": diffs_out,
                })
                buckets = [d["bucket"] for d in diffs_out]
                print(f"  {rid}/{cid} u={row['uSec']}s r={row['rSec']}s "
                      f"diffs={len(diffs_out)} buckets={buckets}")
            recs_out.append({"rid": rid, "joint": joint, "candidates": cands_out})
        out = {
            "meta": {
                "motion": m,
                "generated": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "qualityGate": qg[m],
                "eyeCallCount": sum(call_count_by_rid.values()),
            },
            "records": recs_out,
        }
        (EV / m).mkdir(parents=True, exist_ok=True)
        (EV / m / "eyefirst_verdicts.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1))
        all_out[m] = out
        print(f"  {m} eye calls per record: {call_count_by_rid} "
              f"(cap {ds.EYE_CALL_CAP}/record)")
    print(f"총 Gemini 호출 = {total_calls}건 (상한 20건)")
    return all_out


def main() -> int:
    apr = argparse.ArgumentParser()
    apr.add_argument("--quality-gate", action="store_true")
    apr.add_argument("--smoke", action="store_true")
    apr.add_argument("--run", action="store_true")
    apr.add_argument("--motions", default="elbow,peterpan")
    apr.add_argument("--cache-root", default=os.environ.get("EYEFIRST_CACHE_ROOT", ""),
                      help="캐시 루트 (실행 세션 scratchpad 하위 — 휘발)")
    args = apr.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    EV.mkdir(parents=True, exist_ok=True)

    if args.quality_gate:
        qg = compute_quality_gate()
        (EV / "quality_gate.json").write_text(
            json.dumps(qg, ensure_ascii=False, indent=1))
        _print_quality_table(qg)

    if args.smoke:
        run_smoke()

    if args.run:
        if not args.cache_root:
            raise SystemExit("--run 은 --cache-root 필요 (scratchpad 하위 경로)")
        motions = [m for m in args.motions.split(",") if m in ds.SWEEP_JOBS]
        run_candidates(motions, pathlib.Path(args.cache_root))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
