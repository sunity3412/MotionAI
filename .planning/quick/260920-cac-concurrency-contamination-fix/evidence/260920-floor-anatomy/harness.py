"""§13 다음 측정 공용 하네스.

운영 함수를 그대로 호출한다 — 채점 코드 재구현 0.
  pipeline/app.py::_deviation_against  (motion_dtw + per_joint_deviation, ref_boundary/ref_fps 포함)
  pipeline/app.py::_reference_angles_fps
  analysis/segments.ref_boundary_frame

지표 정의 (§12/§13 과 동일): per-joint median |Δ각도| 8개 → 그 중앙값 = 그 분석의 '편차'.
"""
from __future__ import annotations
import json, os, sys, importlib.util
import numpy as np

REPO = "/Users/kimtaesung/Dev/SunityMotion"
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, f"{REPO}/backend/shared/python")

_spec = importlib.util.spec_from_file_location("pipeapp", f"{REPO}/backend/functions/pipeline/app.py")
app = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(app)

from sunity_shared.analysis import segments, skeleton  # noqa: E402

JOINT_KEYS = list(skeleton.JOINT_KEYS)


def load_students():
    return json.load(open(f"{D}/students.json"))


def load_references():
    refs = json.load(open(f"{D}/references_full.json"))
    refs.pop("_release", None)
    return refs


def ref_matrix(rdoc):
    nj = len(rdoc.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
    return np.asarray(rdoc["angles"], dtype=float).reshape(-1, nj)


def ref_boundary_of(rdoc):
    """운영 mode1 경로와 동일한 ref_boundary 산출 (app.py:8191-8199)."""
    if rdoc.get("sharedBaseMotionId") and rdoc.get("baseUntilS") is not None and rdoc.get("clipRange"):
        nj = len(rdoc.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
        nr_full = len(rdoc["angles"]) // max(nj, 1)
        return segments.ref_boundary_frame(rdoc["clipRange"], rdoc["baseUntilS"], nr_full)
    return None


def ref_fps_of(rdoc):
    return app._reference_angles_fps(rdoc) or None


def student_matrix(s):
    nj = len(s.get("keys") or []) or skeleton.NUM_JOINTS
    return np.asarray(s["angles"], dtype=float).reshape(-1, nj)


def deviate(user_angles, rdoc_or_matrix, *, ref_boundary=None, ref_fps=None, num_joints=None):
    """운영 `_deviation_against` 호출 → (per-joint deviation(J,), match).

    rdoc_or_matrix 가 dict 면 doc 에서 boundary/fps 를 스스로 뽑는다.
    ndarray 면 호출자가 준 boundary/fps 를 쓴다(대조군 시퀀스용)."""
    if isinstance(rdoc_or_matrix, dict):
        a_ref = ref_matrix(rdoc_or_matrix)
        ref_boundary = ref_boundary_of(rdoc_or_matrix)
        ref_fps = ref_fps_of(rdoc_or_matrix)
    else:
        a_ref = np.asarray(rdoc_or_matrix, dtype=float)
    nj = num_joints or a_ref.shape[1]
    dev, match, user_seg, a_ref_full = app._deviation_against(
        np.asarray(user_angles, dtype=float), a_ref.reshape(-1), nj,
        ref_boundary=ref_boundary, ref_fps=ref_fps,
    )
    return np.asarray(dev, dtype=float), match


def scalar(dev):
    """§13 이 쓴 그 스칼라 — 관절별 median |Δ| 8개의 중앙값."""
    d = np.asarray(dev, dtype=float)
    d = d[np.isfinite(d)]
    return float(np.median(d)) if d.size else float("nan")


def variance_decomposition(groups: dict):
    """groups = {그룹명: [값...]} → (그룹내 분산이 전체를 설명하는 비율, 표).

    §13 과 동일 정의: within_ss / total_ss."""
    allv = [v for vs in groups.values() for v in vs]
    if len(allv) < 2:
        return float("nan"), {}
    gm = float(np.mean(allv))
    total_ss = float(np.sum((np.asarray(allv) - gm) ** 2))
    within_ss = 0.0
    table = {}
    for g, vs in groups.items():
        a = np.asarray(vs, dtype=float)
        if a.size == 0:
            continue
        within_ss += float(np.sum((a - a.mean()) ** 2))
        table[g] = dict(n=int(a.size), median=float(np.median(a)), mean=float(a.mean()),
                        sd=float(a.std(ddof=0)), lo=float(a.min()), hi=float(a.max()))
    return (within_ss / total_ss if total_ss > 0 else float("nan")), table
