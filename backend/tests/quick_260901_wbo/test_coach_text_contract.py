"""coach 텍스트 사후 분리 계약 테스트 (quick-260901-wbo Task 1).

박제 정신 (260901-wbo PLAN must_haves):
  · coachStatus 3중 미러 — models.COACH_STATUSES (FAULT_ZOOM_STATUSES 미러).
  · update_analysis_coach_text — field-path 부분 갱신, 허용 5필드뿐 (D-03 경계).
  · hook 값 None 이면 field-path 생략 (stub map 생성 금지 — 체커 warning 1).
  · [[firestore-nested-array-flat]] — tips[].detail2.causes 원소 nested 거부.
  · status='failed' 는 tips 없이 coachStatus 만 (수치 폴백 잔존 — 최후 바닥).

모든 테스트는 stdlib + pytest 만 — 실제 Firestore 호출 0 (mock client,
test_fault_zoom_deferred.py 관례).
"""

from __future__ import annotations

from typing import Any

import pytest


# ─────────────────── mock Firestore 인프라 (.update() 지원) ───────────────────


class _FakeDocRef:
    def __init__(self, path: str) -> None:
        self.path = path
        self.update_calls: list[dict] = []
        self.set_calls: list[tuple[dict, dict]] = []

    def update(self, payload: dict) -> None:
        self.update_calls.append(dict(payload))

    def set(self, payload: dict, **kwargs: Any) -> None:
        self.set_calls.append((dict(payload), dict(kwargs)))


class _FakeFirestore:
    def __init__(self) -> None:
        self.doc_refs: dict[str, _FakeDocRef] = {}

    def document(self, path: str) -> _FakeDocRef:
        if path not in self.doc_refs:
            self.doc_refs[path] = _FakeDocRef(path)
        return self.doc_refs[path]


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> _FakeFirestore:
    from sunity_shared import firestore_admin

    fake = _FakeFirestore()
    monkeypatch.setattr(firestore_admin, "_db", lambda: fake)
    return fake


def _coached_tips() -> list[dict]:
    """coach_dual 산출 형상 tips (detail2 포함 — 13-C 섹션 조립 결과)."""
    return [
        {
            "joint": "left_knee",
            "title": "왼무릎 각도 유지",
            "detail": "왼무릎이 기준보다 굽어 있어요.",
            "detail2": {
                "causes": [
                    {
                        "title": "햄스트링 유연성 부족",
                        "explanation": "무릎 신전이 제한됩니다.",
                        "fix": "폴 앞 스트레칭 3세트",
                    }
                ],
                "injuryRisk": "무리한 신전은 슬괵근 부상 위험이 있어요.",
                "coachNote": "강사와 함께 영상을 보며 확인해 보세요.",
            },
        },
        {
            "joint": "right_elbow",
            "title": "오른팔꿈치 정렬",
            "detail": "팔꿈치를 곧게 펴 보세요.",
        },
    ]


def _hook() -> dict:
    return {
        "autoFindingsSummary": "요약",
        "coachComment": "코멘트",
        "reviewedBy": "gemini",
        "sourceReport": "forcePatternInference",
        "suggestedCues": ["큐 하나"],
        "openQuestionsForCoach": ["질문 하나"],
    }


# ─────────────────── status enum 강제 ───────────────────


def test_coach_statuses_mirror_fault_zoom() -> None:
    """COACH_STATUSES 3값 — FAULT_ZOOM_STATUSES 와 동형, PIPELINE_SEQUENCE 미포함."""
    from sunity_shared import models

    assert models.COACH_STATUSES == ("pending", "done", "failed")
    for s in models.COACH_STATUSES:
        if s == "done":
            continue  # STATUS_DONE 과 문자열만 우연히 같음 — 별개 상수.
        assert s not in models.PIPELINE_SEQUENCE


def test_update_coach_text_rejects_unknown_status(fake_db: _FakeFirestore) -> None:
    from sunity_shared import firestore_admin

    with pytest.raises(ValueError):
        firestore_admin.update_analysis_coach_text(
            "u1", "a1", status="writing"
        )
    assert fake_db.doc_refs == {}


# ─────────────────── done + tips field-path ───────────────────


def test_done_with_tips_uses_field_path(fake_db: _FakeFirestore) -> None:
    """done+tips → result.tips + result.coachStatus + updatedAt 세 field-path 만."""
    from sunity_shared import firestore_admin, models

    tips = _coached_tips()
    firestore_admin.update_analysis_coach_text(
        "u1", "a1", status=models.COACH_STATUS_DONE, tips=tips
    )
    path = models.analysis_doc_path("u1", "a1")
    ref = fake_db.doc_refs[path]
    assert len(ref.update_calls) == 1
    payload = ref.update_calls[0]
    assert set(payload.keys()) == {
        "result.tips",
        "result.coachStatus",
        "updatedAt",
    }
    assert payload["result.tips"] == tips
    assert payload["result.coachStatus"] == "done"
    assert isinstance(payload["updatedAt"], int)
    # set(merge=True) 미사용 — field-path .update() 만 (배열 병합 모호성 회피).
    assert ref.set_calls == []


def test_done_full_payload_includes_hooks_and_gemini_b(
    fake_db: _FakeFirestore,
) -> None:
    """전수 표 5필드 전부 — tips + hook 2 field-path + top-level geminiB + status."""
    from sunity_shared import firestore_admin, models

    gemini_b = {"model": "gemini", "latencyMs": 1200, "dualTrack": True}
    firestore_admin.update_analysis_coach_text(
        "u1",
        "a1",
        status=models.COACH_STATUS_DONE,
        tips=_coached_tips(),
        force_hook=_hook(),
        body_hook=_hook(),
        gemini_b=gemini_b,
    )
    payload = fake_db.doc_refs[models.analysis_doc_path("u1", "a1")].update_calls[0]
    assert set(payload.keys()) == {
        "result.tips",
        "result.coachStatus",
        "result.forcePatternInference.coachCommentHook",
        "result.bodyComparisonReport.coachCommentHook",
        "geminiB",
        "updatedAt",
    }
    assert payload["geminiB"] == gemini_b
    # D-03 경계 — 허용 밖 result.* field-path 금지.
    allowed_result_paths = {
        "result.tips",
        "result.coachStatus",
        "result.forcePatternInference.coachCommentHook",
        "result.bodyComparisonReport.coachCommentHook",
    }
    assert not any(
        k.startswith("result.") and k not in allowed_result_paths for k in payload
    )


def test_none_hooks_omit_field_paths(fake_db: _FakeFirestore) -> None:
    """hook 값 None → 해당 field-path 생략 (stub map 생성 금지 — 체커 warning 1)."""
    from sunity_shared import firestore_admin, models

    firestore_admin.update_analysis_coach_text(
        "u1",
        "a1",
        status=models.COACH_STATUS_DONE,
        tips=_coached_tips(),
        force_hook=_hook(),
        body_hook=None,  # bodyComparisonReport 부재 doc — field-path 미전송
        gemini_b=None,
    )
    payload = fake_db.doc_refs[models.analysis_doc_path("u1", "a1")].update_calls[0]
    assert "result.bodyComparisonReport.coachCommentHook" not in payload
    assert "geminiB" not in payload
    assert "result.forcePatternInference.coachCommentHook" in payload


# ─────────────────── failed 전이 (수치 폴백 잔존) ───────────────────


def test_failed_writes_status_only(fake_db: _FakeFirestore) -> None:
    """failed → tips 미전송, coachStatus + updatedAt 만 (최후 바닥 유지)."""
    from sunity_shared import firestore_admin, models

    firestore_admin.update_analysis_coach_text(
        "u1", "a1", status=models.COACH_STATUS_FAILED
    )
    payload = fake_db.doc_refs[models.analysis_doc_path("u1", "a1")].update_calls[0]
    assert set(payload.keys()) == {"result.coachStatus", "updatedAt"}
    assert payload["result.coachStatus"] == "failed"


def test_failed_allows_gemini_b_audit(fake_db: _FakeFirestore) -> None:
    """failed + both_failed audit — gemini_b 는 선택 포함 가능."""
    from sunity_shared import firestore_admin, models

    firestore_admin.update_analysis_coach_text(
        "u1",
        "a1",
        status=models.COACH_STATUS_FAILED,
        gemini_b={"fallback": "cerebras", "fallbackReason": "both_failed"},
    )
    payload = fake_db.doc_refs[models.analysis_doc_path("u1", "a1")].update_calls[0]
    assert payload["geminiB"]["fallbackReason"] == "both_failed"
    assert "result.tips" not in payload


# ─────────────────── _validate_coach_tips 위반 형상 ───────────────────


def test_tips_reject_nested_array_in_causes(fake_db: _FakeFirestore) -> None:
    """causes 원소 안 nested list → TypeError ([[firestore-nested-array-flat]])."""
    from sunity_shared import firestore_admin, models

    bad = _coached_tips()
    bad[0]["detail2"]["causes"][0]["steps"] = ["a", "b"]  # nested list in cause
    with pytest.raises(TypeError):
        firestore_admin.update_analysis_coach_text(
            "u1", "a1", status=models.COACH_STATUS_DONE, tips=bad
        )


def test_tips_reject_empty_detail(fake_db: _FakeFirestore) -> None:
    from sunity_shared import firestore_admin, models

    bad = [{"joint": "left_knee", "title": "제목", "detail": ""}]
    with pytest.raises(ValueError):
        firestore_admin.update_analysis_coach_text(
            "u1", "a1", status=models.COACH_STATUS_DONE, tips=bad
        )


def test_tips_reject_unknown_key(fake_db: _FakeFirestore) -> None:
    from sunity_shared import firestore_admin, models

    bad = [
        {
            "joint": "left_knee",
            "title": "제목",
            "detail": "본문",
            "score": 88,  # 화이트리스트 밖 — 점수류 사후 주입 차단 (T-wbo-01)
        }
    ]
    with pytest.raises(ValueError):
        firestore_admin.update_analysis_coach_text(
            "u1", "a1", status=models.COACH_STATUS_DONE, tips=bad
        )


def test_tips_reject_non_list(fake_db: _FakeFirestore) -> None:
    from sunity_shared import firestore_admin, models

    with pytest.raises(TypeError):
        firestore_admin.update_analysis_coach_text(
            "u1", "a1", status=models.COACH_STATUS_DONE, tips={"joint": "x"}
        )


def test_tips_allow_generic_tip_with_null_joint(fake_db: _FakeFirestore) -> None:
    """angle>=95 일반 팁 (joint=None, detail2 부재) 형상 합법 — build_result 산출."""
    from sunity_shared import firestore_admin, models

    generic = [
        {
            "joint": None,
            "title": "정은지 선수와 거의 동일한 자세입니다",
            "detail": "관절각 일치도 97점 — 자세 차이가 거의 없어요.",
        }
    ]
    firestore_admin.update_analysis_coach_text(
        "u1", "a1", status=models.COACH_STATUS_DONE, tips=generic
    )
    payload = fake_db.doc_refs[models.analysis_doc_path("u1", "a1")].update_calls[0]
    assert payload["result.tips"] == generic


def test_hook_validation_reuses_strict_whitelist(fake_db: _FakeFirestore) -> None:
    """hook 은 기존 _validate_coach_comment_hook 재사용 — unknown key reject."""
    from sunity_shared import firestore_admin, models

    bad_hook = dict(_hook())
    bad_hook["score"] = 88
    with pytest.raises(ValueError):
        firestore_admin.update_analysis_coach_text(
            "u1",
            "a1",
            status=models.COACH_STATUS_DONE,
            tips=_coached_tips(),
            force_hook=bad_hook,
        )
