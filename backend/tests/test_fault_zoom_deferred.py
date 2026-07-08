"""fault_zoom 사후 분리 (D-06 / SPD-04) 단위 테스트 — Phase 27 Plan 06.

박제 정신 (27-06 PLAN must_haves):
  · D-06 zoom 사후 부분 업데이트 — 점수 먼저 complete, zoom 은 pending→done/failed.
  · result.faultZoom* **두 필드만** field-path 부분 갱신 (D-03 경계 — 다른 result.*
    사후 변경 금지).
  · [[firestore-nested-array-flat]] — comparisons item 안 nested list/dict 거부.
  · status 는 models.FAULT_ZOOM_STATUSES 강제 (ValueError).

모든 테스트는 stdlib + pytest 만 — 실제 Firestore 호출 0 (mock client).
test_firestore_admin_gemini_cache.py mock 관례 따름 (+ `.update()` 지원).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# pipeline/app.py + shared layer path 주입 (Task 2/3 오케스트레이션 테스트용).
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


# ─────────────────── mock Firestore 인프라 (.update() 지원) ───────────────────


class _FakeDocRef:
    def __init__(self, path: str) -> None:
        self.path = path
        self.update_calls: list[dict] = []
        self.set_calls: list[tuple[dict, dict]] = []

    def update(self, payload: dict) -> None:
        # field-path 부분 업데이트 (firebase-admin 표준 API mock).
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


# ─────────────────── Task 1: update_analysis_fault_zoom ───────────────────


def test_update_fault_zoom_done_uses_field_path(fake_db: _FakeFirestore) -> None:
    """Test 1 — status='done' 시 field-path 부분 업데이트 (2 zoom 필드 + updatedAt)."""
    from sunity_shared import firestore_admin, models

    comparisons = [
        {"joint": "left_knee", "deficitDeg": 12.0, "imageUrl": "https://x/a.png",
         "tier": "confirmed", "region": "legs"},
        {"joint": "right_knee", "deficitDeg": None, "imageUrl": "https://x/b.png",
         "tier": "advisory"},
    ]
    firestore_admin.update_analysis_fault_zoom(
        "user1", "analysis1", comparisons, status=models.FAULT_ZOOM_STATUS_DONE
    )
    path = models.analysis_doc_path("user1", "analysis1")
    ref = fake_db.doc_refs[path]
    assert len(ref.update_calls) == 1
    payload = ref.update_calls[0]
    # field-path 형 — result.faultZoom* + updatedAt 세 키만.
    assert set(payload.keys()) == {
        "result.faultZoomComparisons",
        "result.faultZoomStatus",
        "updatedAt",
    }
    assert payload["result.faultZoomComparisons"] == comparisons
    assert payload["result.faultZoomStatus"] == "done"
    assert isinstance(payload["updatedAt"], int)
    # D-03 경계 — result.* zoom 외 field-path 금지.
    assert not any(
        k.startswith("result.") and not k.startswith("result.faultZoom")
        for k in payload
    )


def test_update_fault_zoom_rejects_nested_in_item(fake_db: _FakeFirestore) -> None:
    """Test 2 — comparisons item 안 nested list/dict → TypeError (scoped validator)."""
    from sunity_shared import firestore_admin, models

    bad = [{"joint": "left_knee", "nested": [1, 2, 3]}]
    with pytest.raises(TypeError):
        firestore_admin.update_analysis_fault_zoom(
            "user1", "analysis1", bad, status=models.FAULT_ZOOM_STATUS_DONE
        )
    bad2 = [{"joint": "left_knee", "nested": {"a": 1}}]
    with pytest.raises(TypeError):
        firestore_admin.update_analysis_fault_zoom(
            "user1", "analysis1", bad2, status=models.FAULT_ZOOM_STATUS_DONE
        )


def test_update_fault_zoom_failed_allows_empty_list(fake_db: _FakeFirestore) -> None:
    """Test 3 — status='failed' + 빈 리스트 허용 (실패 전이 shape)."""
    from sunity_shared import firestore_admin, models

    firestore_admin.update_analysis_fault_zoom(
        "user1", "analysis1", [], status=models.FAULT_ZOOM_STATUS_FAILED
    )
    path = models.analysis_doc_path("user1", "analysis1")
    payload = fake_db.doc_refs[path].update_calls[0]
    assert payload["result.faultZoomStatus"] == "failed"
    assert payload["result.faultZoomComparisons"] == []


def test_update_fault_zoom_rejects_unknown_status(fake_db: _FakeFirestore) -> None:
    """Test 4 — status ∉ FAULT_ZOOM_STATUSES → ValueError (models 상수 강제)."""
    from sunity_shared import firestore_admin

    with pytest.raises(ValueError):
        firestore_admin.update_analysis_fault_zoom(
            "user1", "analysis1", [], status="in_progress"
        )
    # 유효 상수는 3종만.
    from sunity_shared import models

    assert models.FAULT_ZOOM_STATUSES == ("pending", "done", "failed")


def test_fault_zoom_status_not_in_pipeline_sequence() -> None:
    """3-way lockstep 비용 회피 — zoom 상태는 PIPELINE_SEQUENCE/status enum 미포함."""
    from sunity_shared import models

    for s in models.FAULT_ZOOM_STATUSES:
        if s == "done":
            continue  # STATUS_DONE 과 문자열만 우연히 같음 — 별개 상수.
        assert s not in models.PIPELINE_SEQUENCE


# ─────────────────── Task 2: _run_deferred_fault_zoom 오케스트레이션 ───────────────────


class _UpdateSpy:
    """firestore_admin.update_analysis_fault_zoom mock — 호출 인자 캡처.

    fail_on_status: 이 status 로 호출되면 예외 발생 (failed write 실패 시나리오).
    """

    def __init__(self, fail_on_status: str | None = None) -> None:
        self.calls: list[tuple[str, str, list, str]] = []
        self.fail_on_status = fail_on_status

    def __call__(self, uid, analysis_id, comparisons, status) -> None:
        self.calls.append((uid, analysis_id, list(comparisons), status))
        if self.fail_on_status is not None and status == self.fail_on_status:
            raise RuntimeError("firestore update failed (mock)")


@pytest.fixture
def pipeline_app(monkeypatch):
    import app  # noqa: E402 — path 주입 후 지연 import (모듈 전역 부작용 격리)

    return app


def test_deferred_success_writes_done_once(pipeline_app, monkeypatch) -> None:
    """렌더 성공 → update(done) 정확히 1회 + comparisons 전달."""
    spy = _UpdateSpy()
    monkeypatch.setattr(
        pipeline_app.firestore_admin, "update_analysis_fault_zoom", spy
    )
    comps = [{"joint": "left_knee", "imageUrl": "x"}]
    pipeline_app._run_deferred_fault_zoom(
        render=lambda: comps, uid="u1", analysis_id="a1"
    )
    assert len(spy.calls) == 1
    uid, aid, sent, status = spy.calls[0]
    assert (uid, aid, status) == ("u1", "a1", "done")
    assert sent == comps


def test_deferred_render_exception_writes_failed(pipeline_app, monkeypatch) -> None:
    """렌더 예외 → update(failed) 호출 (빈 리스트) + 재raise 없음 (비차단)."""
    spy = _UpdateSpy()
    monkeypatch.setattr(
        pipeline_app.firestore_admin, "update_analysis_fault_zoom", spy
    )

    def _boom():
        raise RuntimeError("render boom")

    # 재raise 되지 않아야 한다 (분석은 이미 complete).
    pipeline_app._run_deferred_fault_zoom(
        render=_boom, uid="u1", analysis_id="a1"
    )
    assert len(spy.calls) == 1
    _, _, sent, status = spy.calls[0]
    assert status == "failed"
    assert sent == []


def test_deferred_failed_write_exception_swallowed(pipeline_app, monkeypatch) -> None:
    """렌더 예외 + failed write 자체 실패 → 예외 삼킴 (pending 고아 허용, 27-07 방어)."""
    spy = _UpdateSpy(fail_on_status="failed")
    monkeypatch.setattr(
        pipeline_app.firestore_admin, "update_analysis_fault_zoom", spy
    )

    def _boom():
        raise RuntimeError("render boom")

    # failed write 가 예외를 던져도 _run_deferred_fault_zoom 은 재raise 하지 않는다.
    pipeline_app._run_deferred_fault_zoom(
        render=_boom, uid="u1", analysis_id="a1"
    )
    # done 시도 없음(render 실패) → failed 1회만 시도됨.
    assert [c[3] for c in spy.calls] == ["failed"]
