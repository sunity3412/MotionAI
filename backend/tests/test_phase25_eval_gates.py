"""Phase 25 eval 게이트 단위 테스트 — pod-free, 합성 report fixture (25-04 Task 1).

phase24 의 test_phase24_gates.py 패턴 박제: evals/phase25/assert_gates.py 의 importable
게이트 함수를 파일 경로 로드로 직접 호출한다 (전체 CLI 안 돌림, AWS/GPU/Gemini 불필요).

신규 게이트 4종 + cold/warm 결정론 (모두 artifact-gated — 부재 시 SKIPPED, 실패 아님):
  · check_success_100          — success 멤버 overallScore != 100 하나라도 있으면 FAIL
                                 (phase24 generalization 의 within-tolerance 허용보다 강함).
                                 climb 은 known not_pole 게이트라 제외(그 유지는
                                 check_fault_no_regression 소관).
  · check_pointed_only_window  — 어느 멤버든 seedObservation.window_joints ⊄ pointed 면 FAIL.
  · check_kipup_upper_structure— kip-up fault: (a) overall < phase24 baseline(방향 비교,
                                 고정 타깃 아님) (b) pointed 상체 관절(shoulder/elbow)
                                 angle_vs_reference record ≥ 1 (c) 그 record 관절 ∈ pointed.
  · check_fault_no_regression  — 5 fault 멤버 score <= phase24 baseline(방향 비교, 무퇴행)
                                 + climb not_pole 유지.
  · check_cold_warm_determinism— cold/warm 재실행 report 동일성(verdict/breakdown).

객관성: 특정 점수 assert 금지 — 모든 단언은 방향/구조 비교 (kip-up "< 88" 은 phase24
baseline artifact 값 대비 방향 비교이지 고정 타깃이 아님, curve-fit 금지,
[[scoring-redesign-must-generalize-no-overfit]]).
"""

import importlib.util
import pathlib


# ── assert_gates 를 파일 경로로 로드 (evals/ 는 패키지 아님 — phase24 패턴) ────


def _load_gates():
    path = (pathlib.Path(__file__).resolve().parents[1]
            / "evals" / "phase25" / "assert_gates.py")
    spec = importlib.util.spec_from_file_location("phase25_assert_gates", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gates = _load_gates()


# ── 합성 report fixture 빌더 ─────────────────────────────────────────────────


def _entry(motion, label, score, *, status="done", error_code=None, exception=None,
           records=None, seed=None, collect=None, criteria=None):
    bd = None
    if records is not None:
        pts = sum(r.get("points", 0) for r in records)
        bd = {"baseline": 100, "final": max(0, round(100 + pts)),
              "records": list(records), "coverageGaps": [], "fallback": None}
    e = {
        "motion_id": motion,
        "label": label,
        "analysisId": motion.replace("-", "") + label,
        "status": status,
        "overallScore": score,
        "errorCode": error_code,
        "exception": exception,
        "deductionBreakdown": bd,
        "activatedCriteria": criteria if criteria is not None else (
            sorted({r.get("criterion") for r in records}) if records else []),
    }
    if seed is not None:
        e["seedObservation"] = seed
    if collect is not None:
        e["collectObservation"] = collect
    return e


def _report(entries):
    return {"_meta": {"phase": "25"}, "results": list(entries)}


def _angle_ref_record(joint, dev=30.0):
    """angle_vs_reference__{joint} 감점 record (합성 — 실 엔진 형상 박제)."""
    return {
        "criterion": f"angle_vs_reference__{joint}",
        "ruleId": "angle_vs_reference_over_tol_linear",
        "measuredValue": dev,
        "baselineValue": 0.0,
        "deviation": max(0.0, dev - 20.0),
        "points": -round(max(0.0, dev - 20.0) * 1.2, 1),
        "unit": "deg",
        "source": "geometry",
        "deviationSource": "reference_relative",
        "ipsfAnchor": "expert_reference_deviation",
    }


def _seed(pointed=(), window=(), fallback=()):
    return {"pointed": list(pointed), "window_joints": list(window),
            "fallback_joints": list(fallback)}


def _p24_report():
    """phase24 baseline sweep report 형상(방향 비교 소스) — 실 커밋 artifact 값 박제."""
    scores = {
        ("power-spin", "fault"): 60, ("power-spin", "success"): 100,
        ("peter-pan", "fault"): 79, ("peter-pan", "success"): 100,
        ("elbow-twist-sister", "fault"): 62, ("elbow-twist-sister", "success"): 100,
        ("pdshape", "fault"): 58, ("pdshape", "success"): 100,
        ("kip-up", "fault"): 88, ("kip-up", "success"): 100,
    }
    entries = [_entry(m, l, s) for (m, l), s in scores.items()]
    entries.append(_entry("climb", "fault", None, status="comparison",
                          exception="NotPoleMotionError: angle 0 < 25"))
    entries.append(_entry("climb", "success", None, status="comparison",
                          exception="NotPoleMotionError: angle 10 < 25"))
    return _report(entries)


def _clean_success_entries():
    """5 scoring 페어의 success 멤버 (100, seed 정합) + climb not_pole."""
    out = []
    for m in ("power-spin", "peter-pan", "elbow-twist-sister", "pdshape", "kip-up"):
        out.append(_entry(m, "success", 100, seed=_seed(), collect={
            "collectionStatus": "collected", "pointedJoints": []}))
    out.append(_entry("climb", "success", None, status="comparison",
                      exception="NotPoleMotionError: angle 10 < 25"))
    return out


def _real_fails(res):
    return [r for r in res if not r.startswith("SKIPPED")]


# ── check_success_100 ────────────────────────────────────────────────────────


def test_success_100_passes_when_all_scoring_success_are_100():
    rep = _report(_clean_success_entries())
    assert _real_fails(gates.check_success_100(report=rep)) == []


def test_success_100_fails_on_sub_100_success():
    entries = _clean_success_entries()
    entries[0]["overallScore"] = 92  # power-spin success 92 — 260702-o0c FAIL 재발 형상
    fails = _real_fails(gates.check_success_100(report=_report(entries)))
    assert any("power-spin" in f and "92" in f for f in fails)


def test_success_100_fails_on_unscored_non_climb_success():
    entries = _clean_success_entries()
    entries[1]["overallScore"] = None  # peter-pan success 미채점 — 퇴행
    entries[1]["status"] = "failed"
    fails = _real_fails(gates.check_success_100(report=_report(entries)))
    assert any("peter-pan" in f for f in fails)


def test_success_100_ignores_known_not_pole_climb():
    # climb success 는 known not_pole 게이트 — success_100 소관 아님(무 FAIL).
    rep = _report(_clean_success_entries())
    fails = _real_fails(gates.check_success_100(report=rep))
    assert not any("climb" in f for f in fails)


def test_success_100_skipped_when_report_absent():
    res = gates.check_success_100(report=None)
    if not gates._REPORT_ARTIFACT.exists():
        assert res and all(r.startswith("SKIPPED") for r in res)


# ── check_pointed_only_window ────────────────────────────────────────────────


def test_pointed_only_window_passes_subset():
    e = _entry("kip-up", "fault", 80,
               records=[_angle_ref_record("left_shoulder", 40.0)],
               seed=_seed(pointed=("left_shoulder", "right_shoulder"),
                          window=("left_shoulder",), fallback=("left_knee",)))
    assert _real_fails(gates.check_pointed_only_window(report=_report([e]))) == []


def test_pointed_only_window_fails_on_unpointed_window_joint():
    # window 감점이 vision-짚지 않은 관절에서 발생 — 260702-o0c 경로 재발 구조 FAIL.
    e = _entry("power-spin", "success", 100,
               seed=_seed(pointed=("left_shoulder",),
                          window=("left_shoulder", "right_knee")))
    fails = _real_fails(gates.check_pointed_only_window(report=_report([e])))
    assert any("right_knee" in f for f in fails)


def test_pointed_only_window_fails_on_missing_seed_for_done_member():
    # 채점 완료(done) mode1 멤버인데 seedObservation 자체가 없음 = harness 배선 결함.
    e = _entry("pdshape", "success", 100)  # seed 없음
    fails = _real_fails(gates.check_pointed_only_window(report=_report([e])))
    assert any("pdshape" in f and "seedObservation" in f for f in fails)


def test_pointed_only_window_skips_gated_member_without_seed():
    # not_pole 로 채점 전 중단된 멤버(climb)는 seed 부재가 정상 — FAIL 아님.
    e = _entry("climb", "fault", None, status="comparison",
               exception="NotPoleMotionError: angle 0 < 25")
    assert _real_fails(gates.check_pointed_only_window(report=_report([e]))) == []


# ── check_kipup_upper_structure ──────────────────────────────────────────────


def _kipup_fault_entry(*, score=80, records=None, seed=None):
    if records is None:
        records = [_angle_ref_record("left_shoulder", 40.0)]
    if seed is None:
        seed = _seed(pointed=("left_shoulder", "right_shoulder"),
                     window=("left_shoulder",))
    return _entry("kip-up", "fault", score, records=records, seed=seed)


def test_kipup_structure_passes_full_structure():
    rep = _report([_kipup_fault_entry()])
    res = gates.check_kipup_upper_structure(report=rep, phase24_report=_p24_report())
    assert _real_fails(res) == []


def test_kipup_structure_fails_at_or_above_baseline():
    # 방향 비교: phase24 baseline(88) 이상이면 FAIL — 고정 타깃 88 이 아니라 baseline 대비.
    rep = _report([_kipup_fault_entry(score=88)])
    res = gates.check_kipup_upper_structure(report=rep, phase24_report=_p24_report())
    assert any("88" in f for f in _real_fails(res))


def test_kipup_structure_fails_without_upper_body_record():
    # 상체(shoulder/elbow) angle_vs_reference record 0 → 구조 FAIL (점수만으론 불충분).
    rep = _report([_kipup_fault_entry(
        records=[_angle_ref_record("left_knee", 40.0)],
        seed=_seed(pointed=("left_knee",), window=("left_knee",)))])
    res = gates.check_kipup_upper_structure(report=rep, phase24_report=_p24_report())
    assert any("upper" in f or "상체" in f for f in _real_fails(res))


def test_kipup_structure_fails_when_record_joint_not_pointed():
    # 상체 record 는 있는데 그 관절이 pointed set 에 없음 — window 출처 위반.
    rep = _report([_kipup_fault_entry(
        records=[_angle_ref_record("left_shoulder", 40.0)],
        seed=_seed(pointed=("left_elbow",), window=()))])
    res = gates.check_kipup_upper_structure(report=rep, phase24_report=_p24_report())
    assert any("left_shoulder" in f for f in _real_fails(res))


def test_kipup_structure_skipped_without_baseline():
    rep = _report([_kipup_fault_entry()])
    res = gates.check_kipup_upper_structure(report=rep, phase24_report={})
    assert res and all(r.startswith("SKIPPED") for r in res)


# ── check_fault_no_regression ────────────────────────────────────────────────


def _fault_entries(overrides=None):
    base = {"power-spin": 60, "peter-pan": 75, "elbow-twist-sister": 62,
            "pdshape": 55, "kip-up": 80}
    base.update(overrides or {})
    out = [_entry(m, "fault", s) for m, s in base.items()]
    out.append(_entry("climb", "fault", None, status="comparison",
                      exception="NotPoleMotionError: angle 0 < 25"))
    return out


def test_fault_no_regression_passes_direction():
    rep = _report(_fault_entries())
    res = gates.check_fault_no_regression(report=rep, phase24_report=_p24_report())
    assert _real_fails(res) == []


def test_fault_no_regression_fails_on_score_above_baseline():
    # peter-pan fault 79 → 95: baseline 초과 = fault 변별 퇴행 FAIL.
    rep = _report(_fault_entries({"peter-pan": 95}))
    res = gates.check_fault_no_regression(report=rep, phase24_report=_p24_report())
    assert any("peter-pan" in f for f in _real_fails(res))


def test_fault_no_regression_fails_when_climb_scores():
    # climb not_pole 게이트가 풀려 점수가 나오면 FAIL (안전 게이트 유지 위반).
    entries = [e for e in _fault_entries() if e["motion_id"] != "climb"]
    entries.append(_entry("climb", "fault", 97))
    res = gates.check_fault_no_regression(
        report=_report(entries), phase24_report=_p24_report())
    assert any("climb" in f for f in _real_fails(res))


def test_fault_no_regression_skipped_without_baseline():
    res = gates.check_fault_no_regression(
        report=_report(_fault_entries()), phase24_report={})
    assert res and all(r.startswith("SKIPPED") for r in res)


# ── check_cold_warm_determinism ──────────────────────────────────────────────


def test_cold_warm_determinism_passes_identical():
    cold = _report(_fault_entries() + _clean_success_entries())
    warm = _report(_fault_entries() + _clean_success_entries())
    res = gates.check_cold_warm_determinism(report=cold, warm_report=warm)
    assert _real_fails(res) == []


def test_cold_warm_determinism_fails_on_overall_mismatch():
    cold = _report(_fault_entries())
    warm = _report(_fault_entries({"pdshape": 61}))
    res = gates.check_cold_warm_determinism(report=cold, warm_report=warm)
    assert any("pdshape" in f for f in _real_fails(res))


def test_cold_warm_determinism_skipped_without_warm():
    res = gates.check_cold_warm_determinism(report=_report(_fault_entries()),
                                            warm_report=None)
    if not gates._REPORT_WARM_ARTIFACT.exists():
        assert res and all(r.startswith("SKIPPED") for r in res)


# ── 전체 main() smoke (artifact 부재 시 exit 0 — phase24 계약 동일) ────────────


def test_full_gate_run_exits_zero_when_phase25_artifacts_absent():
    if not gates._REPORT_ARTIFACT.exists():
        assert gates.main() == 0


def test_no_fixed_score_target_in_gate_source():
    # 특정 점수 assert 금지 (locked): kip-up "< 88" 하드코딩이 아니라 baseline 방향 비교.
    src = pathlib.Path(gates.__file__).read_text(encoding="utf-8")
    assert "< 88" not in src and "<88" not in src, (
        "fixed kip-up score target leaked into gate source (must be baseline-relative)"
    )


# ── harness tee smoke (pod-free — fake pipeline 로 배선 검증) ─────────────────


def _load_sweep():
    path = (pathlib.Path(__file__).resolve().parents[1]
            / "evals" / "phase25" / "run_sweep.py")
    spec = importlib.util.spec_from_file_location("phase25_run_sweep", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeCtx:
    def __init__(self, status, supported):
        self.collection_status = status
        self.supported_differences = supported


class _FakePipeline:
    """tee 설치 대상 최소 표면 — 원본 호출/인자 전달을 기록한다."""

    def __init__(self):
        self.collect_kwargs = None
        self.build_kwargs = None

        def _collect(**kwargs):
            self.collect_kwargs = kwargs
            return _FakeCtx("collected", [{
                "_faultKey": {"part_scope": "upper_body", "side": "left",
                              "keypoint_set": "shoulder",
                              "fault_kind": "pole_gap_or_bent"},
                "body_part": "왼쪽 어깨", "severity": "moderate",
                "_supportCount": 2,
            }])

        def _build(**kwargs):
            self.build_kwargs = kwargs
            audit = kwargs.get("seed_audit_out")
            if isinstance(audit, dict):
                audit["pointed"] = ["left_shoulder"]
                audit["window_joints"] = ["left_shoulder"]
                audit["fallback_joints"] = ["left_knee"]
            return {"angle_vs_reference__left_shoulder": 25.0}

        self._collect_vision_fault_context = _collect
        self._build_deduction_measured_deviations = _build


def test_tee_collect_is_read_only_and_captures_pointed():
    sweep = _load_sweep()
    fake = _FakePipeline()
    sweep._CURRENT["key"] = "kip-up:fault:smoke"
    sweep._install_tee(fake)
    ctx = fake._collect_vision_fault_context(
        overall_score=80, dimension_scores={}, mode="expert",
        local_video_path="/tmp/u.mp4", reference_video_path="/tmp/r.mp4",
    )
    # read-only: 원본이 받은 kwargs 가 호출 kwargs 그대로 (인자 변경 0 — at_seconds 불변).
    assert fake.collect_kwargs == {
        "overall_score": 80, "dimension_scores": {}, "mode": "expert",
        "local_video_path": "/tmp/u.mp4", "reference_video_path": "/tmp/r.mp4",
    }
    assert ctx.collection_status == "collected"
    cap = sweep._COLLECT_CAP.pop("kip-up:fault:smoke")
    assert cap["collectionStatus"] == "collected"
    assert cap["pointedJoints"] == ["left_shoulder"]
    assert cap["supportedFaultKeys"][0]["faultKey"]["keypoint_set"] == "shoulder"
    assert cap["supportedFaultKeys"][0]["supportCount"] == 2


def test_tee_build_injects_seed_audit_and_captures():
    sweep = _load_sweep()
    fake = _FakePipeline()
    sweep._CURRENT["key"] = "kip-up:fault:smoke2"
    sweep._install_tee(fake)
    md = fake._build_deduction_measured_deviations(angles=None, profile=None,
                                                   assessments=None,
                                                   dimension_scores=None,
                                                   quantification=None)
    # 반환값 무변경 + seed_audit_out 주입 확인.
    assert md == {"angle_vs_reference__left_shoulder": 25.0}
    assert isinstance(fake.build_kwargs.get("seed_audit_out"), dict)
    cap = sweep._SEED_CAP.pop("kip-up:fault:smoke2")
    assert cap == {"pointed": ["left_shoulder"], "window_joints": ["left_shoulder"],
                   "fallback_joints": ["left_knee"]}
