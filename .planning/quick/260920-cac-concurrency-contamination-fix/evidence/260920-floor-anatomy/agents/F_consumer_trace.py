"""조사 F — 편차 스칼라 → 화면 점수 소비처 추적.

재구현 0. 운영 함수만 호출한다:
  pipeline/app.py::_deviation_against            (DTW 정렬 + per-joint median|Δ|)
  pipeline/app.py::_build_deduction_measured_deviations  (md seed — angle_vs_reference__{jk})
  pipeline/app.py::_baseline_kind_for_profile
  analysis/deduction_engine.py::tally            (감점 합산 → breakdown.final = 화면 점수)

산출: out/F_finals.json  (분석별) + 콘솔 표
"""
from __future__ import annotations
import sys, json, collections
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import numpy as np
import harness as H
from sunity_shared.analysis import deduction_engine, technique, skeleton

app = H.app
JK = list(skeleton.JOINT_KEYS)

class _QuantOK:
    """tally 가 읽는 최소 stub — quantificationStatus 만 'ok', notch substrate 없음.

    운영 mode1(Gemini context 보유)은 quantification 이 실재하므로 quant_unavailable=False.
    이 stub 은 그 상태를 재현하되 reach 칸(notch)은 비워 이 축만 점수에 닿게 한다."""
    quantificationStatus = "ok"
    bodyRelativeNotches = None
    windowMedianAngleDeltas = None


QUANT_OK = _QuantOK()

facts = {r["id"]: r for r in json.load(open(f"{D}/facts.json"))}
students = {s["id"]: s for s in H.load_students()}
refs = H.load_references()


def profile_from_ref(rdoc):
    """기준 doc 에 박제된 techniqueProfile → 운영 TechniqueProfile dataclass.

    운영 mode1 은 학생 영상에 recognizer 를 돌려 profile 을 만든다(Gemini). 오프라인
    에서는 그 호출이 불가하므로, 같은 동작에 대해 시딩 때 인식기가 낸 박제본을 쓴다.
    [미확인] 이것이 그 분석 시점 학생 profile 과 동일하다는 보장은 없다.
    """
    tp = rdoc.get("techniqueProfile") or {}
    je = {k: v for k, v in (tp.get("jointExpectations") or {}).items()}
    return technique.TechniqueProfile(
        name=tp.get("name") or "미상",
        category=tp.get("category") or "unknown",
        joint_expectations=je,
        motion_id=rdoc.get("id") or rdoc.get("motionId"),
    )


def run_one(sid, profile_mode):
    s = students[sid]
    f = facts[sid]
    rdoc = refs[s["ref"]]
    ang = H.student_matrix(s)
    nj = ang.shape[1]
    dev, match, user_seg, a_ref = app._deviation_against(
        ang, np.asarray(rdoc["angles"], dtype=float), nj,
        ref_boundary=H.ref_boundary_of(rdoc), ref_fps=H.ref_fps_of(rdoc),
    )
    profile = None if profile_mode == "none" else profile_from_ref(rdoc)
    merr: dict = {}
    md = app._build_deduction_measured_deviations(
        angles=ang, profile=profile, assessments=None, dimension_scores=None,
        quantification=None,
        reference_dtw_match=match,
        reference_angles=a_ref,                    # 운영이 넘기는 것과 동일(전체 a_ref)
        ref_fps=H.ref_fps_of(rdoc),
        measurement_error_out=merr,
    )
    bk = app._baseline_kind_for_profile(profile)
    out = {}
    axis_md = {k: v for k, v in md.items() if k.startswith("angle_vs_reference__")}
    for tag, mdx, me, quant in (
        # quantAvail: 운영 mode1(Gemini context 보유)처럼 quantification 이 실재하는 경우.
        #   → activated 가 비어도 dimension_overall 폴백이 안 걸리고 final=100.
        ("qa", md, merr, QUANT_OK),
        ("qa_nosupp", md, None, QUANT_OK),
        ("qa_axis", axis_md, merr, QUANT_OK),
        # quantNone: quantification 부재 — activated 0 이면 dimension_overall 폴백.
        ("qn", md, merr, None),
    ):
        b = deduction_engine.tally(
            quant, None,
            dimension_overall=f.get("overall"),
            measured_deviations=dict(mdx),          # tally 가 md 를 mutate 할 수 있어 복사
            dimension_scores=None, baseline_kind=bk,
            measurement_error=me,
        )
        out[tag] = dict(
            final=b.final,
            exec_raw=b.execution_raw_total, exec_capped=b.execution_capped_total,
            n_records=len(b.records), n_suppressed=len(b.suppressed_records),
            crit=[r.criterion for r in b.records],
            fallback=b.fallback,
        )
    return dict(
        id=sid, ref=s["ref"], label=f["label"], vk=f["vk"], overall=f.get("overall"),
        scalar=H.scalar(dev), dev=[float(x) for x in dev],
        md={k: float(v) for k, v in md.items() if isinstance(v, (int, float))},
        md_keys=sorted(md.keys()),
        n_axis_keys=sum(1 for k in md if k.startswith("angle_vs_reference__")),
        a_ref_T=int(a_ref.shape[0]), ref_start=int(match.ref_start),
        ref_end=int(match.ref_end), dtw=float(match.distance),
        profile_mode=profile_mode, baseline_kind=bk,
        **{f"{t}_{k}": v for t, d in out.items() for k, v in d.items()},
    )


TARGET_LABELS = {"correct", "fault", "self"}
ids = [i for i, r in facts.items() if r["label"] in TARGET_LABELS]
print(f"대상 분석 {len(ids)}건 · 동작 {len({facts[i]['ref'] for i in ids})}개", flush=True)

rows = []
for n, sid in enumerate(ids):
    for pm in ("none", "ref"):
        rows.append(run_one(sid, pm))
    if (n + 1) % 100 == 0:
        print(f"  {n+1}/{len(ids)}", flush=True)
json.dump(rows, open(f"{D}/out/F_finals.json", "w"))
print("저장:", f"{D}/out/F_finals.json", len(rows), "행")
