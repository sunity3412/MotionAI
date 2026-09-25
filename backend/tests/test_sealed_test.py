"""봉인 시험지 스크립트(backend/scripts/sealed_test.py) — 순수 부분. 네트워크·git·Firestore 호출 0.
단언: (1) 이미 분석된 영상은 연습 문제로 빠진다 (2) answer 없는 행은 오류 (3) 판정지는 정답·카드를 나란히 놓고 ○× 칸을 비운다
(4) 화면 문장 추출(감점 statusLine·못 잰 한 줄, 숨김 record 제외) (5) ○× 파싱 (6) 닫힌 시험지는 N 중 M 을 적는다."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
_spec = importlib.util.spec_from_file_location("sealed_test", Path(__file__).resolve().parents[1] / "scripts" / "sealed_test.py")
st = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(st)


def _rows():
    return [
        {"file": "/x/a.mp4", "motion": "kip-up", "intent": "fault", "answer": "왼팔을 접은 채로 돈다", "video_hash": "a" * 64},
        {"file": "/x/b.mp4", "motion": "power-spin", "intent": "correct", "answer": "없음", "video_hash": "b" * 64},
        {"file": "/x/c.mp4", "motion": "climb", "intent": "fault", "answer": "엉덩이가 처진다", "video_hash": "c" * 64},
    ]


def test_already_analyzed_videos_become_practice_not_tests():
    runs = [{"video_hash": "c" * 64}]
    tests, practice = st.plan_rows(_rows(), clips=[], runs=runs)
    assert [t["video_hash"][0] for t in tests] == ["a", "b"]
    assert practice[0]["video_hash"][0] == "c" and "연습 문제" in practice[0]["reason"]


def test_missing_answer_is_an_error():
    rows = _rows(); rows[1]["answer"] = ""
    with pytest.raises(st.ic.IntakeError):
        st.plan_rows(rows, clips=[], runs=[])


def test_registered_clip_with_different_labels_is_an_error():
    clips = [{"video_hash": "a" * 64, "motion": "kip-up", "intent": "correct"}]
    with pytest.raises(st.ic.IntakeError):
        st.plan_rows(_rows(), clips=clips, runs=[])


def test_intake_row_carries_the_sealed_answer_in_note():
    r = st.to_intake_sheet_row(_rows()[0])
    assert r["note"] == "봉인 정답: 왼팔을 접은 채로 돈다" and r["subject_id"] == "sub_je" and r["motion"] == "kip-up"


def _doc(score, recs, questions=(), hidden=()):
    return {"status": "done", "result": {
        "overallScore": score,
        "deductionBreakdown": {"records": recs},
        "spotCheck": {"hiddenRecordIds": list(hidden)},
        "coachQuestions": [{"source": "unmeasured", "text": q} for q in questions],
    }}


def test_screen_lines_pick_status_lines_and_unmeasured_and_skip_hidden():
    doc = _doc(83, [
        {"recordId": "r00:x", "criterion": "angle_vs_reference__left_shoulder", "points": -16.6,
         "statusLine": "돌기 시작해서 끝날 때까지 몸이 정은지 선수보다 낮게 떠 있어요", "measuredPattern": "body_low_arm_open"},
        {"recordId": "r01:y", "criterion": "split_angle", "points": -20.0, "statusLine": "숨김"},
    ], questions=["왼팔을 굽혀 폴을 감싸 안는 것이 동작의 문제가 될 수 있어요. 강사님과 확인해보세요."], hidden=["r01:y"])
    s = st.screen_lines(doc)
    assert s["score"] == 83 and len(s["deductions"]) == 1 and "body_low_arm_open" in s["deductions"][0]
    assert s["unmeasured"] == ["왼팔을 굽혀 폴을 감싸 안는 것이 동작의 문제가 될 수 있어요. 강사님과 확인해보세요."]


def test_grade_table_puts_answer_and_card_side_by_side_with_empty_marks():
    test = {"test_id": "t1", "sealed_at": "2026-10-05T01:00:00+00:00", "code_commit": "abcdef0123", "run_at": "2026-10-05T02:00:00+00:00",
            "rows": _rows()[:2], "practice": [dict(_rows()[2], reason="이미 분석된 영상")], "runs": {}, "marks": None}
    docs = {"a" * 64: _doc(83, [{"recordId": "r00:x", "criterion": "c", "points": -16.6, "statusLine": "몸이 낮게 떠 있어요"}])}
    md = st.grade_table(test, docs)
    assert "| 1 | kip-up fault | 왼팔을 접은 채로 돈다 | 83 | 몸이 낮게 떠 있어요 [-16.6] | - |  |" in md
    assert "| 2 | power-spin correct | 없음 | — | (분석 없음) | | |" in md
    assert "연습 문제로 빠진 영상" in md and "climb fault" in md
    assert "맞게 말함" not in md   # 닫기 전엔 셈하지 않는다


def test_parse_marks_and_closed_table_counts():
    assert st.parse_marks("○,x,O", 3) == ["○", "×", "○"]
    with pytest.raises(ValueError):
        st.parse_marks("○,×", 3)
    test = {"test_id": "t1", "sealed_at": "s", "code_commit": "abcdef0123", "rows": _rows()[:2], "practice": [], "runs": {}, "marks": ["○", "×"]}
    md = st.grade_table(test, {})
    assert "처음 보는 영상 2편 중 1편 맞게 말함" in md
