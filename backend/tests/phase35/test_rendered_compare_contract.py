"""quick-260808-jix — renderedCompare 계약 py측 테스트 (phase32 test_coach_audio 서식 미러).

고정 표면: s3keys 빌더 형식 / models 상수 / _validate_rendered_compare 불변식 /
update_analysis_rendered_compare 단일 field-path (contract.md §12.9 lockstep).
LOCAL ONLY — 실 Firestore 무접촉 (_doc monkeypatch).
"""

from __future__ import annotations

import pytest

from sunity_shared import firestore_admin, models
from sunity_shared.s3keys import (
    RENDERED_COMPARE_RENDER_VERSION,
    build_rendered_compare_key,
)

UID = "u1"
ANALYSIS_ID = "a" * 32
KEY = build_rendered_compare_key(UID, ANALYSIS_ID)


# ─────────────────────── s3keys 빌더 (단일 출처) ───────────────────────


def test_key_builder_canonical_format():
    """저장측(pipeline)·서명측(playback-url)이 공유하는 canonical 형식."""
    assert KEY == (
        f"results/{UID}/{ANALYSIS_ID}/compare_v{RENDERED_COMPARE_RENDER_VERSION}.mp4"
    )
    assert KEY.startswith("results/")
    assert KEY.endswith(".mp4")


def test_key_builder_version_pinned_v1():
    """렌더 버전 = 1 (표시 문법 변경 시 bump — 구 mp4·신 doc 혼합 차단)."""
    assert RENDERED_COMPARE_RENDER_VERSION == 1
    assert "/compare_v1.mp4" in KEY


# ─────────────────────── models 상수 (3-way lockstep py면) ───────────────────────


def test_models_constants():
    assert models.RENDERED_COMPARE_KEYS == ("status", "key")
    assert models.RENDERED_COMPARE_STATUS_DONE == "done"
    assert models.RENDERED_COMPARE_STATUS_FAILED == "failed"
    assert models.RENDERED_COMPARE_STATUSES == ("done", "failed")
    assert models.PLAYBACK_ASSET_RENDERED_COMPARE == "renderedCompare"
    # visual job 계약과 분리 유지 — 기존 asset 디스패치 응답 바이트 불변의 전제.
    assert models.PLAYBACK_ASSET_RENDERED_COMPARE not in models.VISUAL_JOB_KINDS


# ─────────────────────── validator 불변식 (T-35J-02) ───────────────────────


def test_validator_accepts_canonical_shapes():
    firestore_admin._validate_rendered_compare({"status": "done", "key": KEY})
    firestore_admin._validate_rendered_compare({"status": "failed", "key": ""})


@pytest.mark.parametrize(
    "bad",
    [
        {"status": "pending", "key": KEY},  # 미정의 status
        {"status": "done"},  # key 누락
        {"status": "done", "key": KEY, "extra": 1},  # 여분 키
        {"status": "done", "key": ""},  # done 인데 빈 key
        {"status": "done", "key": f"uploads/{UID}/evil.mp4"},  # prefix 위반
        {"status": "done", "key": f"results/{UID}/{ANALYSIS_ID}/compare_v1.png"},  # suffix 위반
        {"status": "failed", "key": KEY},  # failed 인데 key 잔존 (stale 금지)
        {"status": "done", "key": 7},  # 비 str
        "not-a-dict",
    ],
)
def test_validator_rejects_malformed(bad):
    with pytest.raises((ValueError, TypeError)):
        firestore_admin._validate_rendered_compare(bad)


# ─────────────────────── update helper (단일 field-path) ───────────────────────


def test_update_helper_routes_through_validator_and_single_field_path(monkeypatch):
    """write 전에 validator 를 실제로 태우고, `result.renderedCompare` 단일
    field-path 만 갱신한다 (T-27-18/D-03 — 사후 단일 필드 규율)."""
    calls: list[dict] = []

    class FakeDoc:
        def update(self, payload):
            calls.append(payload)

    monkeypatch.setattr(firestore_admin, "_doc", lambda _path: FakeDoc())

    # 오염 payload — write 도달 0.
    with pytest.raises(ValueError):
        firestore_admin.update_analysis_rendered_compare(
            UID, ANALYSIS_ID, "uploads/evil.mp4",
            status=models.RENDERED_COMPARE_STATUS_DONE,
        )
    assert calls == []

    firestore_admin.update_analysis_rendered_compare(
        UID, ANALYSIS_ID, KEY, status=models.RENDERED_COMPARE_STATUS_DONE
    )
    assert len(calls) == 1
    assert calls[0]["result.renderedCompare"] == {"status": "done", "key": KEY}
    assert set(calls[0]) == {"result.renderedCompare", "updatedAt"}

    firestore_admin.update_analysis_rendered_compare(
        UID, ANALYSIS_ID, "", status=models.RENDERED_COMPARE_STATUS_FAILED
    )
    assert calls[1]["result.renderedCompare"] == {"status": "failed", "key": ""}
