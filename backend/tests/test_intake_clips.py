"""intake_clips 순수 헬퍼 — 37-DATA-SPEC 규칙이 코드에서 실제로 막히는가 (quick-260923-swh).

네트워크·S3·Firestore 0. 여기서 지키는 것은 "나중에 못 쓰게 되는" 실수들이다:
짝이 아닌 것을 짝으로 묶기 · 학생 이름 저장 · 점수 필드 · 지원 밖 동작을 버리기.
"""

from __future__ import annotations

import pytest

import intake_clips as ic

_SUBJ_STUDENT = {"role": "student", "consent": {"granted": True, "scope": "training", "at": "2026-09-24"}}


def _row(**kw):
    base = {"file": "/Users/Shared/x/a.mov", "motion": "kip-up", "subject_id": "sub_je",
            "intent": "correct", "view": "side"}
    base.update(kw)
    return base


def _clip(h, intent, subject="sub_s01", motion="kip-up", fi=()):
    v = ic.validate_row(
        _row(subject_id=subject, motion=motion, intent=intent, fault_intent=list(fi),
             subject=_SUBJ_STUDENT),
        known_subjects=set(),
    )
    return ic.clip_record(v, video_hash=h, s3_key=f"fixtures/intake/{h}.mov", nbytes=1,
                          motion_supported=True, received_at="2026-09-24")


def test_validate_rejects_what_would_break_joins_or_privacy():
    known = {"sub_je"}
    with pytest.raises(ic.IntakeError, match="ref-"):
        ic.validate_row(_row(motion="ref-kip-up"), known_subjects=known)
    with pytest.raises(ic.IntakeError, match="처음 보는"):
        ic.validate_row(_row(subject_id="sub_s01"), known_subjects=known)
    with pytest.raises(ic.IntakeError, match="display_name"):
        ic.validate_row(_row(subject_id="sub_s01",
                             subject={**_SUBJ_STUDENT, "display_name": "홍길동"}),
                        known_subjects=known)
    with pytest.raises(ic.IntakeError, match="intent=fault"):
        ic.validate_row(_row(fault_intent=["knee_bent"]), known_subjects=known)
    with pytest.raises(ic.IntakeError, match="어휘"):
        ic.validate_row(_row(intent="fault", fault_intent=["power_spin_bad_leg"]), known_subjects=known)
    with pytest.raises(ic.IntakeError, match="consent"):
        ic.validate_row(_row(subject_id="sub_s01", subject={"role": "student"}), known_subjects=known)


def test_unsupported_motion_and_unknown_view_are_kept_not_dropped():
    """지원 밖 동작 · 촬영 방향 모름도 받는다 — 판정불가 데이터는 일부러 모으는 것이다."""
    v = ic.validate_row(_row(motion="ayesha", view=None), known_subjects={"sub_je"})
    assert v["motion"] == "ayesha"
    assert v["view"] is None


def test_records_hold_no_score_and_no_student_name():
    v = ic.validate_row(_row(subject_id="sub_s01", subject=_SUBJ_STUDENT), known_subjects=set())
    rec = ic.clip_record(v, video_hash="h", s3_key="k", nbytes=1, motion_supported=False,
                         received_at="2026-09-24")
    assert not [k for k in rec if "score" in k.lower()]
    assert rec["capture"]["session"] == "2026-09-24"  # 세션 미기재 = 받은 날(인물·세션 분리 평가용)
    subj = ic.subject_record("sub_s01", {**_SUBJ_STUDENT, "display_name": None}, "2026-09-24")
    assert subj["display_name"] is None


def test_pair_requires_same_person_same_motion_one_correct_one_fault():
    existing = [{"pair_id": "pr_kipup_s01_001", "correct_hash": "x", "fault_hash": "y"}]
    c, f = _clip("c1", "correct"), _clip("f1", "fault", fi=["left_arm_underbent"])
    pairs = ic.assemble_pairs([c, f], {"c1": "k", "f1": "k"}, existing, "2026-09-24")
    assert len(pairs) == 1
    assert pairs[0]["pair_id"] == "pr_kipup_s01_002"  # 기존 번호 다음
    assert pairs[0]["fault_intent"] == ["left_arm_underbent"]

    other_person = _clip("f2", "fault", subject="sub_s02")
    with pytest.raises(ic.IntakeError, match="같은 사람"):
        ic.assemble_pairs([c, other_person], {"c1": "k", "f2": "k"}, [], "2026-09-24")
    two_correct = _clip("c2", "correct")
    with pytest.raises(ic.IntakeError, match="정타 1 \\+ 실수 1"):
        ic.assemble_pairs([c, two_correct], {"c1": "k", "c2": "k"}, [], "2026-09-24")


def test_same_pair_is_not_registered_twice():
    c, f = _clip("c1", "correct"), _clip("f1", "fault")
    existing = [{"pair_id": "pr_kipup_s01_001", "correct_hash": "c1", "fault_hash": "f1"}]
    assert ic.assemble_pairs([c, f], {"c1": "k", "f1": "k"}, existing, "2026-09-24") == []


def test_pending_skips_done_and_unsupported_but_retries_failed():
    a, b, d = _clip("a", "correct"), _clip("b", "fault"), _clip("d", "correct")
    d["motion_supported"] = False
    runs = [{"video_hash": "a", "status": "done"}, {"video_hash": "b", "status": "failed"}]
    assert [c["video_hash"] for c in ic.pending_clips([a, b, d], runs)] == ["b"]


def test_new_person_is_introduced_once_per_sheet():
    """같은 시트에서 새 사람은 첫 줄에만 소개하면 된다 — 2026-09-23 드라이런에서 잡은 거절."""
    rows = [
        _row(subject_id="sub_s01", subject=_SUBJ_STUDENT, intent="correct"),
        _row(subject_id="sub_s01", intent="fault"),
    ]
    out = ic.validate_sheet(rows, known_subjects=set())
    assert out[0]["subject"] is not None and out[1]["subject"] is None
    with pytest.raises(ic.IntakeError, match="^1행"):
        ic.validate_sheet(list(reversed(rows)), known_subjects=set())
