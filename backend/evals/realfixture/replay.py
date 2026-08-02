#!/usr/bin/env python3
"""실 doc 재생 하네스 — 저장 산출물만으로 채점·record 를 재현한다 (quick-260802-czw).

**합성(`sweep_record_moment.py`) = 내가 만든 경계값에서 규칙이 작동하는지 본다(통제).
실물(`replay.py`) = 내가 만들 수 없는 실제 분포에서 그 규칙이 무엇을 내는지 본다(대표성).
전자는 코드가 맞는지를, 후자는 답이 맞는지를 묻는다.** 둘 다 남는다.

재현 깊이 (D-1) — 저장 산출물 → builder → tally → 각인 → units → 카드.
`_process` 전체가 아니다. `atFrameIdx` 의 유일한 writer 는
`_build_deduction_measured_deviations` 안의 `_record_moment`, 유일한 각인처는
`_attach_translation_emission`, 유일한 카드 전달 경로는
`criterion_units_from_records → build_fault_zoom_comparisons` 다. 그 위 단계
(S3 / ffmpeg / RTMW / Gemini / coach / Firestore write)는 값에 기여하지 않고 입력
산출물(`angles`·`visionVeto`·`keypointReport`)만 만드는데, 그 산출물은 doc 에 저장돼 있다.

**이 전제는 주장이 아니라 게이트가 증명한다.** RECON 게이트가 재현본과 저장
`deductionBreakdown.records` 를 record 단위로 대조하고, 재현하지 못한 record 로는
판정을 내지 않는다.

**PNG 픽셀은 이 단계에서 의미가 없다.** 프레임 배열이 합성이라 사진의 내용은 무의미하고,
여기서 쓰는 건 "프레임 선택이 갈렸다"는 방증(sha256)뿐이다. 사진이 실제로 다른 순간인지는
S3 영상 → 프레임 추출 → 실제 렌더가 필요한 **B 단계**다.

GPU 0 · Gemini 0 · Pod 0 · Firestore 0 — 어댑터/쓰기 경로는 **호출되면 죽는** 스텁으로
갈아끼운다. "안 불렀다"가 가정이 아니라 실행 결과다.

사용법:
  backend/.venv/bin/python backend/evals/realfixture/replay.py --recon-only
  backend/.venv/bin/python backend/evals/realfixture/replay.py --out <path>
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
_FIXTURES = _HERE / "fixtures"

for _p in (
    str(_REPO / "backend" / "shared" / "python"),
    str(_REPO / "backend" / "functions" / "pipeline"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402

# measuredValue 동등 허용오차 — 저장 doc 은 반올림된 값이라 그 자릿수까지만 본다.
_MEASURED_EPS = 1e-6


# ---------------------------------------------------------------------------
# 죽는 스텁 — GPU/네트워크/쓰기 차단을 **실행으로** 증명한다.
# ---------------------------------------------------------------------------
class _DeadCallable:
    """호출되면 RuntimeError. 어떤 이름으로 접근해도 같은 함수를 준다."""

    def __init__(self, label: str) -> None:
        self._label = label

    def _die(self, *_a, **_k):
        raise RuntimeError(
            f"{self._label} 호출 — 이 하네스는 GPU/네트워크/Firestore 에 접근하지 않는다 "
            "(quick-260802-czw)"
        )

    def __getattr__(self, name: str):
        if name.startswith("__"):
            raise AttributeError(name)
        return self._die

    def __call__(self, *a, **k):
        return self._die(*a, **k)


class _DeadOnAccess:
    """속성 접근 자체가 죽는다 (_s3 처럼 어떤 사용도 허용하지 않는 객체)."""

    def __init__(self, label: str) -> None:
        object.__setattr__(self, "_label", label)

    def __getattr__(self, name: str):
        raise RuntimeError(
            f"{object.__getattribute__(self, '_label')}.{name} 접근 — "
            "이 하네스는 S3/네트워크에 접근하지 않는다 (quick-260802-czw)"
        )


class _FixtureFrameExtractor:
    """`target_fps` 만 내놓고 실제 추출은 죽는 FrameExtractor 스텁.

    이 값 하나로 `app._pipeline_frame_fps()` 가 production 경로 그대로 동작한다 —
    하네스가 fps 리터럴을 쓰지 않는 이유다. fps 출처는 MANIFEST 파생값 하나뿐.
    """

    def __init__(self, target_fps: float, max_side: int = 640) -> None:
        self.target_fps = float(target_fps)
        self.max_side = int(max_side)

    def extract(self, *_a, **_k):
        raise RuntimeError(
            "FrameExtractor.extract 호출 — 이 하네스는 영상을 읽지 않는다 (quick-260802-czw)"
        )


_WRITE_PREFIXES = (
    "update_",
    "complete_",
    "fail_",
    "store_",
    "record_",
    "set_",
    "acquire_",
    "release_",
    "claim_",
    "commit_",
    "delete_",
)


def _install_dead_firestore(label: str = "firestore_admin") -> list[str]:
    """firestore_admin 의 쓰기 경로 + 클라이언트 진입점을 죽는 함수로 교체.

    `_db`/`_doc` 까지 막는 이유: 쓰기 0 을 "쓰기 함수를 안 불렀다"로 증명하는 것보다
    **Firestore 에 아예 닿지 않았다**로 증명하는 쪽이 강하다. 이 하네스는 리포에
    박제된 JSON 만 읽는다.
    """
    from sunity_shared import firestore_admin as fa

    blocked: list[str] = []
    for name in dir(fa):
        if name.startswith("__"):
            continue
        obj = getattr(fa, name)
        if not callable(obj):
            continue
        if name.startswith(_WRITE_PREFIXES) or name in ("_db", "_doc"):
            setattr(fa, name, _DeadCallable(f"{label}.{name}")._die)
            blocked.append(name)
    return sorted(blocked)


def load_pipeline_with_fixture_adapters(student_fps: float | None = None):
    """`backend/functions/pipeline/app.py` 를 로드하고 어댑터를 fixture 스텁으로 교체.

    로드 방식은 RunPod `server.py::_load_pipeline_module` 과 같다 (사본 금지 — 이
    파일 하나가 production 과 같은 코드를 돈다는 것이 재현의 전제다).
    """
    if student_fps is None:
        student_fps = float(load_manifest()["studentAnglesFps"])
    path = _REPO / "backend" / "functions" / "pipeline" / "app.py"
    spec = importlib.util.spec_from_file_location("czw_pipeline_app", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules["czw_pipeline_app"] = module
    spec.loader.exec_module(module)

    module._FRAME_EXTRACTOR = _FixtureFrameExtractor(student_fps)
    module._POSE_ESTIMATOR = _DeadCallable("PoseEstimator")
    module._RTMW_ENGINE = _DeadCallable("RTMWEngine")
    module._POLE_DETECTOR = _DeadCallable("PoleDetector")
    module._COACH_WRITER = _DeadCallable("CoachWriter")
    module._GEMINI_COACH_WRITER = _DeadCallable("GeminiCoachWriter")
    module._SYNTHESIS_ADAPTER = _DeadCallable("SynthesisAdapter")
    module._RECOGNIZER = _DeadCallable("TechniqueRecognizer")
    module._s3 = _DeadOnAccess("_s3")
    module._czw_blocked_firestore = _install_dead_firestore()
    return module


# ---------------------------------------------------------------------------
# fixture 로딩
# ---------------------------------------------------------------------------
def load_manifest() -> dict:
    return json.loads((_FIXTURES / "MANIFEST.json").read_text())


def load_analysis(analysis_id: str) -> dict:
    return json.loads((_FIXTURES / f"{analysis_id}.json").read_text())


def load_reference(motion_id: str) -> dict:
    return json.loads((_FIXTURES / "reference" / f"{motion_id}.json").read_text())


def _angles_matrix(doc: dict) -> np.ndarray:
    keys = doc.get("anglesJointKeys") or []
    frames = int(doc.get("anglesFrames") or 0)
    flat = doc.get("angles") or []
    return np.asarray(flat, dtype=float).reshape(frames, len(keys))


# ---------------------------------------------------------------------------
# 신뢰도 어댑터 (quick-260802-tie) — 저장 keypointReport → 순간 tie-break 입력
# ---------------------------------------------------------------------------
def frame_confidence_from_keypoint_report(report: dict, frames_fps: float):
    """저장 `keypointReport` → `(9fps 프레임, joint_keys) -> 0..1 | None`.

    **어댑터 경계 치환**이다 — 규칙(최솟값 집계 · 동점 폭)은 production
    `moment` 모듈이 그대로 소유하고, 여기서는 값을 어디서 읽어오는지만 바꾼다.

    production 은 `pose_frames`(9fps, `angles` 와 같은 축)에서 읽지만 하네스에는
    그 객체가 없다. 대신 doc 에 저장된 report 를 쓴다 — **같은 수치다**:
      · report.confidence = `_clamp_unit(keypoints_2d[coco].visibility)`
        (`assemble.build_keypoint_report`)
      · 18fps 업샘플은 선형 보간이고 `new_t[i] = i * (9/18) = i/2` 이므로 짝수 rep
        인덱스에서 가중치가 0 → **원본 9fps 표본이 그대로 복원**된다
        (`keypoint_frame.upsample_to_fps`).
      · 인덱스 변환은 production 과 같은 단일 출처(`fault_zoom._to_rep_idx`)를
        호출한다 — 하네스가 fps 산술을 새로 쓰지 않는다.

    관절 이름공간: 관절각 3점은 COCO-17 이름(`skeleton.JOINT_ANGLES`)이고 report 는
    `KeypointName`(wrist→hand)이라 `JOINT_KEY_TO_ANGLE_KEY` 를 역인덱싱한다.
    report 에 없는 keypoint(legacy 8관절의 elbow/ankle 등)는 **None**(판정 불가) —
    0 으로 보정하지 않는다.
    """
    from sunity_shared.analysis.fault_zoom import _to_rep_idx
    from sunity_shared.analysis.keypoint_frame import JOINT_KEY_TO_ANGLE_KEY
    from sunity_shared.analysis.moment import _unit_conf
    from sunity_shared.analysis.skeleton import JOINT_ANGLES

    names = list((report or {}).get("joints") or ())
    conf = list((report or {}).get("confidence") or ())
    rep_fps = float((report or {}).get("fps") or frames_fps)
    rep_frames = int((report or {}).get("frames") or 0)
    coco_to_col = {
        JOINT_KEY_TO_ANGLE_KEY[n]: i
        for i, n in enumerate(names)
        if n in JOINT_KEY_TO_ANGLE_KEY
    }
    j = len(names)

    def _conf(frame_idx: int, joint_keys) -> float | None:
        if j == 0 or rep_frames <= 0:
            return None
        rep_idx = _to_rep_idx(int(frame_idx), frames_fps, rep_fps, rep_frames)
        worst: float | None = None
        for jk in joint_keys or ():
            triple = JOINT_ANGLES.get(jk)
            if triple is None:
                return None
            for coco in triple:
                col = coco_to_col.get(coco)
                if col is None:
                    return None
                pos = rep_idx * j + col
                if pos < 0 or pos >= len(conf):
                    return None
                c = _unit_conf(conf[pos])
                if c is None:
                    return None
                if worst is None or c < worst:
                    worst = c
        return worst

    return _conf


# ---------------------------------------------------------------------------
# 재생 — production 함수만 부른다. 하네스가 산식을 다시 쓰지 않는다.
# ---------------------------------------------------------------------------
class Blocked(Exception):
    """재현에 필요한 입력을 doc 에서 구할 수 없음 — 추정으로 메우지 않는다."""


def replay_fixture(app, entry: dict, *, use_frame_confidence: bool = False) -> dict:
    """분석 1건 재생 → {md, breakdown, measured_at, match, profile, ...}.

    use_frame_confidence (quick-260802-tie): True 면 저장 keypointReport 에서 만든
    신뢰도를 builder 에 주입한다 — 대표 프레임이 **동점일 때만** 쓰인다.
    False(default) = 이 인자가 생기기 전과 완전히 같은 재생(RECON 게이트 무영향).
    """
    from sunity_shared.analysis import dimensions, kismam, skeleton, vision_veto
    from sunity_shared.analysis.gemini_technique_recognizer import (
        GeminiTechniqueRecognizer,
    )

    analysis_id = entry["analysisId"]
    doc = load_analysis(analysis_id)
    result = doc.get("result") or {}
    ref = load_reference(entry["referenceMotionId"])

    angles = _angles_matrix(doc)
    if angles.size == 0:
        raise Blocked("angles 비어 있음")

    # (1) 기술 프로파일 — production 등재 조회 경로 그대로.
    #     `_build_profile` 은 `self` 를 쓰지 않는 순수 조립기(yaml hold_moment criteria →
    #     joint_expectations). 하네스가 dataclass 를 손으로 채우지 않는다.
    #     hold_window 는 Gemini KeyMoment 파생인데 4 doc 전부 forceSignalsReport 에
    #     `layer2_unavailable` 가 박혀 있다 = production 도 key_moments 부재였다 →
    #     moments 빈 리스트가 그때의 상태다. 이 전제가 틀리면 window 를 쓰는 record
    #     (leg/arm_extension·line)가 RECON 에서 어긋나 스스로 드러난다.
    motion_id = ((result.get("mission") or {}).get("motionId")) or entry.get(
        "referenceMotionId"
    )
    profile = GeminiTechniqueRecognizer._build_profile(None, motion_id, [])

    # (2) DTW — production 진입점 그대로. sharedBaseMotionId 부재 → ref_boundary None
    #     (app.py 의 3-조건 게이트를 그대로 따른다).
    num_joints = len(ref.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
    ref_boundary = None
    if ref.get("sharedBaseMotionId") and ref.get("baseUntilS") is not None and ref.get(
        "clipRange"
    ):
        from sunity_shared.analysis import segments

        nr_full = len(ref["angles"]) // max(num_joints, 1)
        ref_boundary = segments.ref_boundary_frame(
            ref["clipRange"], ref["baseUntilS"], nr_full
        )
    deviation, match, user_seg, a_ref = app._deviation_against(
        angles, ref["angles"], num_joints, ref_boundary=ref_boundary
    )

    user_mean, ref_mean = app._angles_to_dtw_median_dicts(
        angles, a_ref, skeleton.JOINT_KEYS, ref_boundary=ref_boundary
    )
    assessments = kismam.assess(
        deviation,
        user_angles=user_mean,
        reference_angles=ref_mean,
        target_source="reference_motion",
    )

    # (3) 정량화 — production 데이터클래스에 저장값을 그대로 담는다(가짜 클래스 금지).
    vv = result.get("visionVeto") or {}
    quantification = vision_veto.VisionQuantificationResult(
        quantificationStatus=vv.get("quantificationStatus") or "unavailable",
        angleDeltas=vv.get("angleDeltas"),
        bodyRelativeNotches=vv.get("bodyRelativeNotches"),
        windowMedianAngleDeltas=vv.get("windowMedianAngleDeltas"),
        warnings=(),
    )

    # (4) pointed 관절 — production 매퍼 호출. rootCauseHypotheses 부재/빈 → 빈 tuple.
    hyps = vv.get("rootCauseHypotheses") or []
    pointed = vision_veto.pointed_joints_from_supported_differences(
        [{"_faultKey": h.get("faultKey")} for h in hyps if isinstance(h, dict)]
    )

    # (5) 측정 substrate + 측정 순간 out-param.
    dimension_scores = result.get("dimensionScores") or {}
    align = vv.get("alignment") or {}
    measured_at: dict = {}
    seed_audit: dict = {}
    frame_confidence = None
    if use_frame_confidence:
        frame_confidence = frame_confidence_from_keypoint_report(
            result.get("keypointReport") or {},
            float(getattr(app._FRAME_EXTRACTOR, "target_fps", 0.0)) or 1.0,
        )
    md = app._build_deduction_measured_deviations(
        angles=angles,
        profile=profile,
        assessments=assessments,
        dimension_scores=dimension_scores,
        quantification=quantification,
        reference_dtw_match=match,
        reference_angles=a_ref,
        # split_deficit_deg 는 기준 source_pose(keypoints)에서 산출되는데 doc 에 없다.
        # 추정하지 않는다 — 이 경로의 split record 는 어차피 vision 주입이다.
        split_deficit_deg=None,
        vision_pointed_joints=pointed,
        seed_audit_out=seed_audit,
        alignment_visibility=align.get("visibility"),
        alignment_visibility_measured=bool(align.get("visibility_measured", False)),
        vision_status=vv.get("collectionStatus"),
        measured_at_out=measured_at,
        frame_confidence=frame_confidence,
    )

    # (6) tally — production 경로(_apply_vision_veto_from_context)를 그대로 탄다.
    #     supported_differences 는 doc 에 남아 있지 않다(rootCauseHypotheses 는 fold
    #     결과라 각도쌍이 없다) → vision 라우팅 record(split_angle)는 재현 대상이 아니고
    #     RECON 에서 MISSING 으로 정직하게 드러난다. 채워 넣지 않는다.
    ctx = vision_veto.VisionFaultContext(
        collection_status=vv.get("collectionStatus") or "no_fault",
        verdict=None,
        supported_differences=[],
        root_cause_hypotheses=[],
        selected_frame_pairs=[],
        alignment=align,
        telemetry={},
        cap_would_apply=False,
    )
    dimension_overall = dimensions.overall_from_dimensions(dimension_scores)
    score_result = {
        "overallScore": dimension_overall,
        "dimensionScores": dimension_scores,
    }
    baseline_kind = app._baseline_kind_for_profile(profile)
    veto_result = app._apply_vision_veto_from_context(
        score_result,
        ctx,
        quantification,
        measured_deviations=md,
        baseline_kind=baseline_kind,
    )
    breakdown = veto_result.get("deductionBreakdown") or {}

    return {
        "analysisId": analysis_id,
        "motionId": motion_id,
        "doc": doc,
        "ref": ref,
        "result": result,
        "angles": angles,
        "profile": profile,
        "profileExtendJoints": [
            k for k, v in profile.joint_expectations.items() if v == "extend"
        ],
        "profileHoldWindow": profile.hold_window,
        "match": match,
        "aRef": a_ref,
        "md": md,
        "measuredAt": measured_at,
        "seedAudit": seed_audit,
        "quantification": quantification,
        "vetoResult": veto_result,
        "breakdown": breakdown,
        "dimensionOverall": dimension_overall,
        "baselineKind": baseline_kind,
        "pointedJoints": list(pointed),
    }


# ---------------------------------------------------------------------------
# RECON 게이트 — 이 하네스가 production 을 재현했는가
# ---------------------------------------------------------------------------
def _num_eq(a, b) -> bool:
    if a is None or b is None:
        return a is b
    try:
        return abs(float(a) - float(b)) <= _MEASURED_EPS
    except (TypeError, ValueError):
        return a == b


_WINDOW_DEPENDENT = ("leg_extension", "arm_extension", "line")


def _cause_for(row: dict, stored_rows: list[dict]) -> str | None:
    """불일치 row 의 구조적 원인 — fixture 별 하드코딩 없이 계약에서 파생한다.

    원인 문자열은 **설명일 뿐 판정을 바꾸지 않는다**. verdict 는 위에서 이미 정해졌고
    여기서 무르게 만들지 않는다.
    """
    from sunity_shared.analysis import ipsf_criteria

    crit = row.get("criterion") or ""
    if row["verdict"] == "MISSING":
        src = (row.get("stored") or {}).get("source")
        if src == "vision":
            return (
                "vision 주입 record — 산출 입력(supported_differences 의 각도쌍)이 doc 에 "
                "남아 있지 않다(저장된 rootCauseHypotheses 는 fold 결과라 각도가 없다). "
                "추정으로 채우지 않는다."
            )
        return "재현 md 에 이 criterion 이 없다."
    if row["verdict"] == "EXTRA" and crit.startswith("angle_vs_reference__"):
        jk = crit[len("angle_vs_reference__"):]
        by_id = {c["id"]: c for c in ipsf_criteria.CRITERION_GROUPS}
        for s in stored_rows:
            sc = s.get("criterion")
            if sc in ("leg_extension", "arm_extension", "split_angle") and jk in (
                by_id.get(sc, {}).get("joint_keys") or ()
            ):
                return (
                    f"저장 doc 의 `{sc}` 가 claim 하는 관절 — 그 record 를 재현하지 못해 "
                    "engine cross-exclusion(deduction_engine.py:306-311)이 걸리지 않았다. "
                    "재현 실패의 기계적 파생이지 별개의 편차가 아니다."
                )
        return None
    if row["verdict"] == "MISMATCH" and crit in _WINDOW_DEPENDENT:
        return (
            "`dimensions._select_window` 창 의존 criterion — 창은 profile.hold_window "
            "(Gemini KeyMoment 파생)가 정하는데 그 값이 분석 doc 에 없다. 창을 역산해 "
            "맞추면 그 순간 판정이 하네스의 창작이 되므로 비워 둔다."
        )
    return None


def recon(entry: dict, replayed: dict) -> dict:
    """재현 breakdown ↔ MANIFEST 정답지 record 단위 대조.

    정답지는 리포에 박제돼 있다 — Firestore doc 이 나중에 덮어써져도 대조 대상은 남는다.
    """
    stored = entry.get("sourceRecordCriteria") or []
    got = [r for r in (replayed["breakdown"].get("records") or []) if isinstance(r, dict)]
    got_by_crit = {r.get("criterion"): r for r in got}
    rows: list[dict] = []
    for s in stored:
        crit = s.get("criterion")
        g = got_by_crit.pop(crit, None)
        if g is None:
            rows.append({"criterion": crit, "verdict": "MISSING", "stored": s, "got": None})
            continue
        mv_ok = _num_eq(s.get("measuredValue"), g.get("measuredValue"))
        pt_ok = _num_eq(s.get("points"), g.get("points"))
        if mv_ok and pt_ok:
            rows.append({
                "criterion": crit, "verdict": "MATCH",
                "measuredValue": g.get("measuredValue"), "points": g.get("points"),
            })
        else:
            rows.append({
                "criterion": crit, "verdict": "MISMATCH",
                "storedMeasuredValue": s.get("measuredValue"),
                "gotMeasuredValue": g.get("measuredValue"),
                "storedPoints": s.get("points"), "gotPoints": g.get("points"),
                "deltaMeasured": (
                    None if s.get("measuredValue") is None or g.get("measuredValue") is None
                    else float(g["measuredValue"]) - float(s["measuredValue"])
                ),
            })
    for crit, g in got_by_crit.items():
        rows.append({
            "criterion": crit, "verdict": "EXTRA",
            "measuredValue": g.get("measuredValue"), "points": g.get("points"),
        })
    for row in rows:
        cause = _cause_for(row, stored)
        if cause:
            row["cause"] = cause
    stored_final = entry.get("deductionFinal")
    got_final = replayed["breakdown"].get("final")
    final_ok = _num_eq(stored_final, got_final)
    all_match = bool(rows) and all(r["verdict"] == "MATCH" for r in rows)
    return {
        "rows": rows,
        "storedFinal": stored_final,
        "gotFinal": got_final,
        "finalMatch": final_ok,
        # 전 record MATCH + final 동일 = 이 fixture 는 재현됐다.
        "verdict": "PASS" if (all_match and final_ok) else "PARTIAL",
        "matchedCriteria": [r["criterion"] for r in rows if r["verdict"] == "MATCH"],
    }


def print_recon_table(entry: dict, replayed: dict, rc: dict) -> None:
    print(f"\n== {entry['analysisId']}  (ref={entry['referenceMotionId']}, motion={replayed['motionId']})")
    print(
        f"   profile EXTEND={replayed['profileExtendJoints']} "
        f"hold_window={replayed['profileHoldWindow']} baseline_kind={replayed['baselineKind']}"
    )
    print(
        f"   pointed={replayed['pointedJoints']} "
        f"dimension_overall={replayed['dimensionOverall']} "
        f"final stored={rc['storedFinal']} got={rc['gotFinal']} "
        f"{'OK' if rc['finalMatch'] else 'DIFF'}"
    )
    for r in rc["rows"]:
        if r["verdict"] == "MATCH":
            print(f"   MATCH     {r['criterion']:38} mv={r['measuredValue']} pts={r['points']}")
        elif r["verdict"] == "MISMATCH":
            print(
                f"   MISMATCH  {r['criterion']:38} "
                f"mv {r['storedMeasuredValue']} -> {r['gotMeasuredValue']} "
                f"(d={r['deltaMeasured']}) pts {r['storedPoints']} -> {r['gotPoints']}"
            )
        elif r["verdict"] == "MISSING":
            print(
                f"   MISSING   {r['criterion']:38} "
                f"stored mv={r['stored'].get('measuredValue')} src={r['stored'].get('source')}"
            )
        else:
            print(f"   EXTRA     {r['criterion']:38} mv={r['measuredValue']} pts={r['points']}")
        if r.get("cause"):
            print(f"             원인: {r['cause']}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="실 doc 재생 하네스 (quick-260802-czw)")
    p.add_argument(
        "--recon-only", action="store_true",
        help="재현 대조만 수행 — 판정(atFrameIdx 분포) 산출 없음",
    )
    p.add_argument("--out", default=None, help="판정 산출물 경로 (replay_out.json)")
    return p


_DEFAULT_OUT = (
    _REPO
    / ".planning/quick/260802-czw-keypoint-fixture-keypointreport-joints3d/replay_out.json"
)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    manifest = load_manifest()
    app = load_pipeline_with_fixture_adapters(float(manifest["studentAnglesFps"]))

    print(
        f"fixtures={len(manifest['analyses'])} "
        f"studentAnglesFps={manifest['studentAnglesFps']} "
        f"referenceAnglesFps={manifest['referenceAnglesFps']}"
    )
    print(f"firestore 차단 함수 {len(app._czw_blocked_firestore)}종")

    replays: list[tuple[dict, dict, dict]] = []
    recon_all_pass = True
    for entry in manifest["analyses"]:
        try:
            replayed = replay_fixture(app, entry)
        except Blocked as exc:
            print(f"\n== {entry['analysisId']}\n   RECON: BLOCKED ({exc})")
            recon_all_pass = False
            continue
        rc = recon(entry, replayed)
        print_recon_table(entry, replayed, rc)
        if rc["verdict"] != "PASS":
            recon_all_pass = False
        replays.append((entry, replayed, rc))

    total = sum(len(r["rows"]) for _e, _r, r in replays)
    matched = sum(
        1 for _e, _r, r in replays for row in r["rows"] if row["verdict"] == "MATCH"
    )
    print(f"\nRECON: record {matched}/{total} MATCH · fixture {len(replays)}건")

    if args.recon_only:
        # exit code 는 "재현했는가"만 답한다. 판정은 여기에 영향을 주지 않는다.
        return 0 if recon_all_pass else 1

    out_path = Path(args.out) if args.out else _DEFAULT_OUT
    verdict_payload = build_verdict(app, manifest, replays)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(verdict_payload, indent=1, sort_keys=True) + "\n")
    print(f"\n산출물: {out_path}")
    return 0 if recon_all_pass else 1


# ---------------------------------------------------------------------------
# 카드 렌더 — production `_render_fault_zoom` 을 **그대로** 돌린다.
# 바꿔 끼우는 것은 영상→프레임 어댑터와 S3 업로드 두 곳뿐(어댑터 경계).
# 그래야 `atMatched` pass-through 같은 매퍼 코드도 실제로 실행된다.
# ---------------------------------------------------------------------------
class _RecordingS3:
    """put_object 바이트만 메모리에 담는다. 네트워크 0 — 그 외 호출은 죽는다."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, *, Bucket, Key, Body, ContentType=None):  # noqa: N803
        self.objects[f"{Bucket}/{Key}"] = bytes(Body)
        return {}

    def generate_presigned_url(self, *_a, **_k):
        return "https://example.invalid/czw-no-network"

    def __getattr__(self, name):
        raise RuntimeError(f"_RecordingS3.{name} 호출 — 이 하네스는 S3 에 접근하지 않는다")


class _FixtureExtractorFactory:
    """`FfmpegFrameExtractor(target_fps=..., max_side=...)` 자리에 끼우는 합성 추출기.

    production `_render_fault_zoom` 은 학생 프레임을 `cached_user_frames` 로 받으므로
    여기로 오는 것은 기준(우측) 영상뿐이다.
    """

    def __init__(self, frames) -> None:
        self._frames = frames

    def __call__(self, *_a, **kwargs):
        outer = self

        class _Ext:
            target_fps = float(kwargs.get("target_fps") or 0.0)

            def extract(self, *_a2, **_k2):
                return outer._frames

        return _Ext()


def _synthetic_frames(n: int, seed: int) -> np.ndarray:
    """프레임마다 1픽셀을 흔든 (n, 8, 8, 3) uint8 배열.

    전부 동일하면 "카드가 다른 프레임을 골랐다"를 PNG 로 구분할 수 없다 —
    프레임 선택이 갈렸는지 sha256 으로 보이게 하는 최소 표식이다
    (`sweep_record_moment._load_frames` 선례). **픽셀 내용은 판정 근거가 아니다.**
    """
    n = max(1, int(n))
    stack = np.zeros((n, 8, 8, 3), dtype=np.uint8)
    stack[:, :, :, :] = np.uint8(seed % 256)
    for f in range(n):
        stack[f, 0, 0, :] = np.uint8((f * 7 + seed) % 256)
    return stack


def _ref_frames_count(ref_report: dict, frames_fps: float) -> int:
    """기준 9fps 프레임 배열 길이 — production 의 fps 환산식을 그대로 쓴다.

    `fault_zoom.build_fault_zoom_comparisons` 가 `_dtw_ref_frames` 를 만들 때 쓰는
    바로 그 식(`round(rep_frames / rep_fps * 대상fps)`)이다. 하네스가 새 산술을
    만들지 않는다. 이 길이는 기준 프레임 인덱스의 클램프 상한으로만 쓰이며,
    적절한지는 대조군 카드가 저장 카드 프레임을 재현하는지로 검증된다.
    """
    rep_fps = float(ref_report.get("fps") or frames_fps)
    rep_frames = int(ref_report.get("frames") or 0)
    return max(1, int(round(rep_frames / max(1e-6, rep_fps) * frames_fps)))


def render_cards(app, replayed: dict, records: list, frames_fps: float) -> list[dict]:
    """production `_build_fault_zoom_comparisons` 호출 — 인자 조립도 production 담당.

    `result` 는 저장 doc 의 result 를 그대로 쓰고 `deductionBreakdown` 만 재현본으로
    바꾼다. 그 시점 production 이 fault_zoom 에 준 입력이 곧 저장된 result 이기 때문이다 —
    바꾸는 것은 이 사이클이 검사하려는 변수(record) 하나뿐이다.
    """
    import copy
    import hashlib
    import types

    from sunity_shared.analysis import fault_zoom

    doc, ref, stored_result = replayed["doc"], replayed["ref"], replayed["result"]
    user_report = stored_result.get("keypointReport")
    ref_report = ref.get("referenceKeypointReport")
    if not user_report or not ref_report:
        return []

    u_n = int(doc.get("anglesFrames") or 0)
    r_n = _ref_frames_count(ref_report, frames_fps)
    user_frames = _synthetic_frames(u_n, seed=11)
    ref_frames = _synthetic_frames(r_n, seed=131)

    card_result = copy.deepcopy(stored_result)
    card_result["deductionBreakdown"] = {
        **(replayed["breakdown"] or {}),
        "records": records,
    }

    # frame_extractor 는 imageio 의존이라 이 venv 에서 import 자체가 죽는다.
    # production 이 함수 안에서 import 하므로 sys.modules 에 미리 꽂는다.
    fake_fe = types.ModuleType("sunity_shared.analysis.frame_extractor")
    fake_fe.FfmpegFrameExtractor = _FixtureExtractorFactory(ref_frames)
    prev_fe = sys.modules.get("sunity_shared.analysis.frame_extractor")
    prev_s3, prev_get = app._s3, app._signed_get
    rec_s3 = _RecordingS3()
    sys.modules["sunity_shared.analysis.frame_extractor"] = fake_fe
    app._s3 = rec_s3
    app._signed_get = lambda _b, _k: "https://example.invalid/czw-no-network"
    try:
        items = app._build_fault_zoom_comparisons(
            card_result,
            "czw://user-video",
            "czw://ref-video",
            user_report,
            ref_report,
            replayed["profile"],
            "czw-uid",
            replayed["analysisId"],
            "czw-bucket",
            dtw_match=replayed["match"],
            cached_user_frames=user_frames,
        )
    finally:
        app._s3, app._signed_get = prev_s3, prev_get
        if prev_fe is None:
            sys.modules.pop("sunity_shared.analysis.frame_extractor", None)
        else:
            sys.modules["sunity_shared.analysis.frame_extractor"] = prev_fe

    # PNG 바이트는 산출물에 넣지 않는다 — 합성 픽셀이라 내용이 무의미하고,
    # 남길 가치가 있는 것은 "프레임 선택이 갈렸다"는 방증(sha256)뿐이다.
    by_key = {k.rsplit("/", 1)[-1]: v for k, v in rec_s3.objects.items()}
    out: list[dict] = []
    for it in items:
        base = it.get("criterion") or it.get("joint")
        prefix = "zoom_" if it.get("tier") == "confirmed" else "zoom_adv_"
        png = by_key.get(f"{prefix}{base}.png")
        out.append({
            "criterion": it.get("criterion"),
            "joint": it.get("joint"),
            "tier": it.get("tier"),
            "region": it.get("region"),
            "userFrameIdx": it.get("userFrameIdx"),
            "refFrameIdx": it.get("refFrameIdx"),
            "refMatched": it.get("refMatched"),
            "userVideoSec": it.get("userVideoSec"),
            "atMatched": it.get("atMatched"),
            # quick-260802-tie — 기준 패널 마킹 인증(부재=criterion 없는 카드).
            "refMarked": it.get("refMarked"),
            "png_sha256": hashlib.sha256(png).hexdigest() if png else None,
        })
    _ = fault_zoom  # 모듈 로딩 확인용(직접 호출은 production 이 한다)
    return out


def _engrave(app, replayed: dict, measured_at: dict) -> list[dict]:
    """production `_attach_translation_emission` 으로 record 에 순간을 각인한다."""
    import copy

    breakdown = copy.deepcopy(replayed["breakdown"] or {})
    result = {
        "deductionBreakdown": breakdown,
        "dimensionScores": replayed["result"].get("dimensionScores") or {},
        "safetyFlags": replayed["result"].get("safetyFlags"),
    }
    app._attach_translation_emission(
        result,
        mode="mode1",
        motion_id=replayed["motionId"],
        prev_doc=None,
        uid="czw-uid",
        analysis_id=replayed["analysisId"],
        measured_at=measured_at,
    )
    return list(breakdown.get("records") or [])


def build_verdict(app, manifest: dict, replays) -> dict:
    """판정 산출 — record 별 atFrameIdx 분포 + 카드 프레임.

    **판정은 exit code 에 영향을 주지 않는다** (Task 2 규약). 이 러너가 묻는 것은
    "재현했는가"이고, 답이 마음에 드는가는 별개다.
    """
    frames_fps = float(manifest["studentAnglesFps"])
    fixtures: list[dict] = []
    for entry, replayed, rc in replays:
        matched = set(rc["matchedCriteria"])
        treat_records = _engrave(app, replayed, replayed["measuredAt"])
        ctrl_records = _engrave(app, replayed, {})

        recs: list[dict] = []
        fail_closed: list[dict] = []
        for r in treat_records:
            crit = r.get("criterion")
            at = r.get("atFrameIdx")
            row = {
                "criterion": crit,
                "source": r.get("source"),
                "measuredValue": r.get("measuredValue"),
                "points": r.get("points"),
                "atFrameIdx": at,
                "atVideoSec": r.get("atVideoSec"),
                # 재현 못 한 record 로는 판정하지 않는다.
                "reconMatched": crit in matched,
            }
            recs.append(row)
            if at is None:
                fail_closed.append({"criterion": crit, "source": r.get("source")})

        judged = [r for r in recs if r["reconMatched"] and r["atFrameIdx"] is not None]
        distinct = len({r["atFrameIdx"] for r in judged})

        cards_treat = render_cards(app, replayed, treat_records, frames_fps)
        cards_ctrl = render_cards(app, replayed, ctrl_records, frames_fps)
        at_flags = [bool(c.get("atMatched")) for c in cards_treat]
        at_ratio = (sum(at_flags) / len(at_flags)) if at_flags else None
        # advisory 카드는 criterion_units 를 받지 않아 **구조적으로** 앵커가 없다
        # (quick-260801-gbk 가 이미 기록한 사실). 전체 비율만 내면 그 구조적 제외가
        # 실패처럼 읽히므로 confirmed 전용 분모도 함께 낸다. 둘 다 남긴다.
        conf_flags = [
            bool(c.get("atMatched")) for c in cards_treat if c.get("tier") == "confirmed"
        ]
        conf_ratio = (sum(conf_flags) / len(conf_flags)) if conf_flags else None

        stored_cards = entry.get("sourceCardFrames") or []
        # 카드 경로 RECON — 대조군(순간 없음)이 저장 카드 프레임을 재현하는가.
        # 재현하면 카드 인자 구성이 검증된 것이고, 그때만 처리군 델타가 근거가 된다.
        ctrl_frames = sorted(
            c["userFrameIdx"] for c in cards_ctrl if c.get("userFrameIdx") is not None
        )
        stored_frames = sorted(
            c["userFrameIdx"] for c in stored_cards if c.get("userFrameIdx") is not None
        )
        card_recon = "REPRODUCED" if ctrl_frames == stored_frames else "NOT_REPRODUCED"
        # 장수가 어긋나면 전체 비교가 실패로 뭉개진다(재현 못 한 record 가 카드 수를
        # 바꾸므로). criterion 단위로도 대조해 어느 카드가 재현됐는지 남긴다.
        ctrl_by_crit = {
            c.get("criterion"): c.get("userFrameIdx")
            for c in cards_ctrl
            if c.get("criterion")
        }
        card_recon_by_criterion = []
        for sc in stored_cards:
            crit = sc.get("criterion")
            if not crit:
                continue
            got = ctrl_by_crit.get(crit, "ABSENT")
            card_recon_by_criterion.append({
                "criterion": crit,
                "storedUserFrameIdx": sc.get("userFrameIdx"),
                "controlUserFrameIdx": None if got == "ABSENT" else got,
                "verdict": (
                    "ABSENT" if got == "ABSENT"
                    else ("MATCH" if got == sc.get("userFrameIdx") else "MISMATCH")
                ),
            })

        fixtures.append({
            "analysisId": entry["analysisId"],
            "referenceMotionId": entry["referenceMotionId"],
            "motionId": replayed["motionId"],
            "storedScore": entry.get("overallScore"),
            "reconVerdict": rc["verdict"],
            "reconRows": rc["rows"],
            "reconMatchedCriteria": sorted(matched),
            "profileExtendJoints": replayed["profileExtendJoints"],
            "profileHoldWindow": replayed["profileHoldWindow"],
            "records": recs,
            "judgedRecordCount": len(judged),
            "distinctAtFrameIdx": distinct,
            "failClosed": fail_closed,
            "cards": cards_treat,
            "cardsControl": cards_ctrl,
            "cardRecon": card_recon,
            "cardReconByCriterion": card_recon_by_criterion,
            "controlCardFrames": ctrl_frames,
            "storedCardFrames": stored_frames,
            "atMatchedRatio": at_ratio,
            "atMatchedCount": sum(at_flags),
            "cardCount": len(cards_treat),
            "atMatchedConfirmedRatio": conf_ratio,
            "atMatchedConfirmedCount": sum(conf_flags),
            "confirmedCardCount": len(conf_flags),
        })

    print("\n── 판정 (atFrameIdx 가 실 데이터에서 record 마다 갈리는가) ──")
    for f in fixtures:
        judged, distinct = f["judgedRecordCount"], f["distinctAtFrameIdx"]
        if judged == 0:
            line = "판정 불가 — 순간을 가진 재현 record 0건"
        elif judged == 1:
            line = "record 1건 — 갈림 여부를 물을 수 없다(비교 대상 없음)"
        elif distinct == 1:
            # belle 이 본 증상 그대로 — 감점이 여럿인데 순간이 하나.
            line = (
                f"뭉쳤다 — 재현 record {judged}건이 프레임 1개로 수렴. "
                "quick-260801-gbk 는 실 데이터에서 실패"
            )
        elif distinct == judged:
            line = f"갈렸다 — 재현 record {judged}건이 서로 다른 프레임 {distinct}개"
        else:
            line = (
                f"갈렸다(부분 중복) — 재현 record {judged}건이 서로 다른 프레임 "
                f"{distinct}개. 겹친 쌍 {judged - distinct}건"
            )
        print(f"  {f['analysisId']:34} {line}")
        print(
            f"      atFrameIdx={[r['atFrameIdx'] for r in f['records']]} "
            f"cards(treat)={[c['userFrameIdx'] for c in f['cards']]} "
            f"cards(ctrl)={f['controlCardFrames']} stored={f['storedCardFrames']} "
            f"cardRecon={f['cardRecon']} atMatched={f['atMatchedCount']}/{f['cardCount']}"
        )

    weight = [f for f in fixtures if "elbowtwist" in f["analysisId"]]
    if weight:
        w = weight[0]
        print(
            "\n판정의 무게중심 = elbow-twist "
            f"(record {w['judgedRecordCount']}건, 전부 angle_vs_reference, 관절 8개 상이): "
            f"서로 다른 atFrameIdx {w['distinctAtFrameIdx']}개"
        )

    total_cards = sum(f["cardCount"] for f in fixtures)
    total_at = sum(f["atMatchedCount"] for f in fixtures)
    ratio = (total_at / total_cards) if total_cards else None
    conf_cards = sum(f["confirmedCardCount"] for f in fixtures)
    conf_at = sum(f["atMatchedConfirmedCount"] for f in fixtures)
    conf_all = (conf_at / conf_cards) if conf_cards else None
    print(
        f"\n실 데이터 atMatched = 전체 {total_at}/{total_cards}"
        + (f" = {ratio:.1%}" if ratio is not None else "")
        + f" · confirmed 전용 {conf_at}/{conf_cards}"
        + (f" = {conf_all:.1%}" if conf_all is not None else "")
        + "  (합성 스위프 30/30 = 100% 와 나란히 읽을 것)"
    )

    judged_all = sum(f["judgedRecordCount"] for f in fixtures)
    distinct_all = sum(f["distinctAtFrameIdx"] for f in fixtures)
    # 판정 대상 = 재현 record 2건 이상인 fixture (1건짜리는 갈림을 물을 수 없다).
    decidable = [f for f in fixtures if f["judgedRecordCount"] > 1]
    if not decidable:
        verdict = "UNDECIDABLE"
    elif all(f["distinctAtFrameIdx"] == 1 for f in decidable):
        verdict = "CLUMPED"
    elif all(
        f["distinctAtFrameIdx"] == f["judgedRecordCount"] for f in decidable
    ):
        verdict = "SPLIT"
    else:
        verdict = "SPLIT_PARTIAL"
    return {
        "generatedBy": "backend/evals/realfixture/replay.py (quick-260802-czw)",
        "studentAnglesFps": manifest["studentAnglesFps"],
        "referenceAnglesFps": manifest["referenceAnglesFps"],
        "fixtures": fixtures,
        "judgedRecordTotal": judged_all,
        "distinctAtFrameIdxTotal": distinct_all,
        "atMatchedTotal": total_at,
        "cardTotal": total_cards,
        "atMatchedRatioTotal": ratio,
        "atMatchedConfirmedTotal": conf_at,
        "confirmedCardTotal": conf_cards,
        "atMatchedConfirmedRatioTotal": conf_all,
        "syntheticSweepAtMatchedRatio": 1.0,
        "verdict": verdict,
        "decidableFixtures": [f["analysisId"] for f in decidable],
        "limits": [
            "PNG 픽셀 내용은 판정 근거가 아니다 — 프레임 배열이 합성이다. sha256 은 "
            "프레임 선택이 갈렸다는 방증일 뿐. 사진이 실제로 다른 순간인지는 B 단계.",
            "vision 주입 record(split_angle)는 산출 입력이 doc 에 없어 재현 대상이 아니다.",
            "창 의존 criterion(leg/arm_extension·line)은 profile.hold_window 가 doc 밖이라 "
            "재현되지 않을 수 있다 — RECON 이 record 단위로 표시한다.",
            "failClosed 가 비어 있는 것은 fail-closed 가 깨졌다는 뜻이 **아니다** — "
            "설계상 순간이 없어야 할 split_angle record 자체가 재현되지 않아 "
            "이 하네스의 관측 범위 밖이다. 여기서는 확인되지 않았다.",
            "advisory 카드는 criterion_units 미전달로 구조적으로 atMatched 를 가질 수 "
            "없다 — 전체 비율과 confirmed 전용 비율을 둘 다 읽을 것.",
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
