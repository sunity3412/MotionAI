"""운영 분석 → 학습 트랙(report) 변환 계약 — quick-260815-glc.

belle 2026-08-15: "분석 리포트 자체가 학습에 도움이 된다면 배선 설계를 해야하는거
아녀? 우리 베타 오픈하고 사용자들이 동의하면 그것도 학습하는거 맞제?"

이 파일이 못 박는 것:
  1. **빈 골격을 학습에 넣지 않는다** — 결함 0건 분석은 리포트를 만들지 않는다.
     (2026-08-15 게이트 FAIL 의 관측 증상이 정확히 "29건 전부 빈 골격"이었다.)
  2. **조립 계약을 통과할 결함만 만든다** — build_jsonl._faults_satisfy_contract 와
     같은 규칙. 통과 못 할 행을 만들어두면 조립에서 조용히 사라진다.
  3. **재지 않은 것을 쟀다고 말하지 않는다** — reference_relative 기록의
     baselineValue(=0)를 기준 각도로 적지 않는다.
  4. **동의 축** — 명시 거부는 내부 계정도 뒤집지 않고, 명단 밖은 optIn 실측이
     True 일 때만 admit(= 베타 오픈 후 경로).
  5. **학생 서술 원인 재사용 금지** — quick-260815-fzi 판정의 하류 강제.

순수 함수만 — Firestore/S3/네트워크 무접촉.
"""

from __future__ import annotations

import pytest

from datagen import harvest_reports as hr
from datagen.build_jsonl import _faults_satisfy_contract


# ── 운영 실물에서 뜬 감점 기록 (2026-08-15, analysisId 2f68dcb3…) ────────────
ABS_RECORD = {
    "criterion": "leg_extension",
    "deviation": 18.99,
    "unit": "deg",
    "deviationSource": "ipsf_absolute",
    "points": -20,
    "ruleId": "leg_extension_over_tol_linear",
    "baselineValue": 180,
    "measuredValue": 141.01,
    "source": "geometry",
    "ipsfAnchor": "19-IPSF §A 트랙2 (다리 신전 부족 누적 감점)",
}
REL_RECORD = {
    "criterion": "angle_vs_reference__left_shoulder",
    "deviationSource": "reference_relative",
    "points": -12.6,
    "ruleId": "angle_vs_reference_over_tol_linear",
    "baselineValue": 0,
    "deviation": 10.53,
    "ipsfAnchor": "expert_reference_deviation (정은지 대비 per-joint 편차)",
    "source": "vision",
    "unit": "deg",
}


def test_absolute_record_yields_angle_pair():
    """ipsf_absolute 는 baselineValue 가 정타 각도 → 각도쌍 성립."""
    f = hr.fault_from_record(ABS_RECORD)
    assert f["student_angle_deg"] == pytest.approx(141.01)
    assert f["reference_angle_deg"] == pytest.approx(180.0)
    assert f["body_part"] == "leg" and f["part_scope"] == "lower_body"
    assert f["fault_category"] == "limb_extension"
    assert f["source"] == "geometry"


def test_reference_relative_does_not_invent_a_reference_angle():
    """★baselineValue=0 은 편차 기준선이지 기준 각도가 아니다 — 각도쌍을 짓지 않는다."""
    f = hr.fault_from_record(REL_RECORD)
    assert f["reference_angle_deg"] is None, "재지 않은 기준 각도를 지어냈다"
    assert f["approx_angle_deviation_deg"] == pytest.approx(10.53)
    assert f["body_part"] == "left_shoulder" and f["part_scope"] == "upper_body"
    assert f["source"] == "vision_hypothesis"


def test_every_produced_fault_passes_assembly_contract():
    """조립기가 버릴 행을 만들지 않는다 (같은 계약을 여기서 미리 통과)."""
    faults = [hr.fault_from_record(ABS_RECORD), hr.fault_from_record(REL_RECORD)]
    assert all(f is not None for f in faults)
    assert _faults_satisfy_contract({"faults": faults})


def test_unknown_criterion_is_dropped_not_guessed():
    """모르는 criterion 을 other 로 뭉뚱그리지 않는다 (라우팅 오배송 방지)."""
    assert hr.fault_from_record({**ABS_RECORD, "criterion": "wat_is_this"}) is None
    assert hr.criterion_parts("angle_vs_reference__left_pinky") is None
    assert hr.fault_from_record({**ABS_RECORD, "criterion": None}) is None


def test_record_without_pair_or_fallback_is_dropped():
    bad = {"criterion": "leg_extension", "unit": "deg", "source": "geometry"}
    assert hr.fault_from_record(bad) is None


# ── 빈 골격 차단 (이 배선의 존재 이유) ────────────────────────────────────────
def test_analysis_without_faults_makes_no_training_row():
    doc = {"status": "done", "result": {"tips": [{"detail": "잘했어요"}], "overallScore": 93}}
    assert hr.report_from_analysis(doc) is None, "결함 0건 분석이 학습 행이 됐다 — 빈 골격 학습"


def test_analysis_with_faults_makes_a_report():
    doc = {
        "status": "done",
        "referenceMotionId": "ref-power-spin",
        "result": {
            "deductionBreakdown": {"records": [ABS_RECORD, REL_RECORD]},
            "tips": [{"detail": "다리를 더 뻗어보세요"}, {"detail": "어깨를 내려보세요"}],
        },
    }
    rep = hr.report_from_analysis(doc)
    assert rep is not None
    assert len(rep["faults"]) == 2
    assert rep["coaching"] == "다리를 더 뻗어보세요 어깨를 내려보세요"
    assert set(rep) == {"coaching", "corrected_coords", "faults", "segments", "svg_spec", "time_anchors"}


# ── 문면은 문구집만 소유 / 학생 서술 원인 재사용 금지 (fzi 하류 강제) ────────
def test_reference_subject_cause_is_carried_student_subject_is_not():
    entries = {
        "ref-power-spin.angle_vs_reference__left_shoulder": {
            "statusLine": "왼쪽 어깨(겨드랑이) 각도가 파워스핀 기준 자세와 차이가 있어요",
            "causeLine": "기준은 안정된 위치를 만들려 팔을 굽혀 더 올린 것으로 보여요",
            "causeSubject": "reference",
        }
    }
    doc = {
        "status": "done",
        "referenceMotionId": "ref-power-spin",
        "result": {"deductionBreakdown": {"records": [REL_RECORD]}},
    }
    f = hr.report_from_analysis(doc, entries)["faults"][0]
    assert f["root_cause_hypothesis"] == entries[
        "ref-power-spin.angle_vs_reference__left_shoulder"]["causeLine"]
    assert f["fault_state"].startswith("왼쪽 어깨")

    # 주어가 학생이면 실리지 않는다 (belle 2026-08-15 반려의 하류 강제).
    student = {k: dict(v) for k, v in entries.items()}
    student["ref-power-spin.angle_vs_reference__left_shoulder"]["causeSubject"] = "student"
    f2 = hr.report_from_analysis(doc, student)["faults"][0]
    assert f2["root_cause_hypothesis"] is None, "학생 서술 원인이 다른 분석으로 새어나갔다"


def test_no_phrasebook_entry_means_no_invented_text():
    f = hr.fault_from_record(ABS_RECORD, None)
    assert f["fault_state"] is None and f["correct_state"] is None
    assert f["root_cause_hypothesis"] is None


# ── 동의 축 (베타 오픈 경로) ──────────────────────────────────────────────────
APP_UID = "csKWYvI3WCPYPysNQ9KkWecaUvq1"   # 28자 Firebase 익명 uid (실사용자 형태)
APP_UID2 = "hT7guc8zs7R79Z5J2W877bvS1Vt2"


def _owner(scope):
    return lambda uid: scope


def test_explicit_denial_beats_internal_account():
    doc = {"uid": APP_UID, "learningOptIn": False}
    assert hr.analysis_disposition(doc, _owner("prelaunch_internal")) == ("hold", "consent_denied")


def test_internal_account_admits_without_optin():
    doc = {"uid": APP_UID}
    assert hr.analysis_disposition(doc, _owner("prelaunch_internal")) == ("admit", "prelaunch_internal")


def test_script_created_uids_are_internal_but_app_shaped_uids_are_not():
    """★보호선 — 28자 Firebase uid 는 실제 사용자와 형태가 같아 구조 통과 금지."""
    for runner in ("phase25eval", "genpod2", "mock_e2e_v3_1781249495", "devdiag", "eval18"):
        assert hr.is_script_created_uid(runner), runner
        assert hr.analysis_disposition({"uid": runner}, _owner("unverified")) == (
            "admit", "internal_runner")
    for app_uid in ("csKWYvI3WCPYPysNQ9KkWecaUvq1", "hT7guc8zs7R79Z5J2W877bvS1Vt2",
                    "Wm5KTg0OsObIHchuMmfMr1hDSxy2"):
        assert len(app_uid) == 28 and app_uid.isalnum()
        assert not hr.is_script_created_uid(app_uid), app_uid
        assert hr.analysis_disposition({"uid": app_uid}, _owner("unverified")) == (
            "hold", "optin_unverified")
    assert not hr.is_script_created_uid(None)
    assert not hr.is_script_created_uid("")


def test_denial_beats_script_created_uid():
    """명시 거부는 러너 계정이라도 뒤집지 않는다 (우선순위 0)."""
    assert hr.analysis_disposition(
        {"uid": "phase25eval", "learningOptIn": False}, _owner("unverified")
    ) == ("hold", "consent_denied")


def test_outside_account_requires_measured_optin():
    """★베타 오픈 후 경로 — 동의 실측 True 만 통과, 미상은 보류(fail-closed)."""
    assert hr.analysis_disposition({"uid": APP_UID2, "learningOptIn": True}, _owner("unverified")) == (
        "admit", "optin_verified")
    assert hr.analysis_disposition({"uid": APP_UID2}, _owner("unverified")) == (
        "hold", "optin_unverified")


def test_consent_lookup_is_used_when_doc_has_no_flag():
    doc = {"uid": APP_UID2}
    got = hr.analysis_disposition(doc, _owner("unverified"), consent_lookup=lambda uid: True)
    assert got == ("admit", "optin_verified")


# ── 원장 append-only ─────────────────────────────────────────────────────────
def test_ledger_merge_is_append_only_by_analysis_id():
    ledger = {"_meta": {}, "rows": [{"analysis_id": "a1"}]}
    ledger, added, skipped = hr.merge_rows(ledger, [{"analysis_id": "a1"}, {"analysis_id": "a2"}])
    assert (added, skipped) == (1, 1)
    assert [r["analysis_id"] for r in ledger["rows"]] == ["a1", "a2"]
