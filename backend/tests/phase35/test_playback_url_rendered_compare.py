"""quick-260808-jix — playback-url asset 'renderedCompare' 가드 테스트 (H-02/V-0).

고정 표면 (phase32 test_coach_audio 서식 미러): done + 서버 구성 canonical ==
저장 key exact 일 때만 서명. failed/부재/stale key = 전부 동일 404 (leak 0).
기존 asset 경로(correctedPose/미지원 asset) 무회귀.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from sunity_shared.s3keys import build_rendered_compare_key

_BACKEND = Path(__file__).resolve().parents[2]

UID = "u1"
OTHER_UID = "u2"
ANALYSIS_ID = "a" * 32
KEY = build_rendered_compare_key(UID, ANALYSIS_ID)


def _load_module(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def purl():
    os.environ.setdefault("VIDEO_BUCKET", "test-bucket")
    return _load_module(
        "playback_url_phase35_rendered_compare",
        _BACKEND / "functions" / "playback-url" / "app.py",
    )


class FakeUrlS3:
    def __init__(self):
        self.signed: list[dict] = []

    def generate_presigned_url(self, _op, Params=None, ExpiresIn=None):  # noqa: N803
        self.signed.append({"Params": Params, "ExpiresIn": ExpiresIn})
        return f"https://s3.example/signed?k={Params['Key']}"


@pytest.fixture
def url_s3(purl, monkeypatch):
    fake = FakeUrlS3()
    monkeypatch.setattr(purl, "_s3", fake)
    return fake


@pytest.fixture
def url_auth(purl, monkeypatch):
    monkeypatch.setattr(purl, "verify_request", lambda _event: UID)


@pytest.fixture
def analyses(purl, monkeypatch):
    store: dict[tuple[str, str], dict] = {}
    monkeypatch.setattr(
        purl.firestore_admin, "get_analysis", lambda uid, aid: store.get((uid, aid))
    )
    return store


def _call(purl, **body) -> dict:
    event = {"body": json.dumps(body), "headers": {"authorization": "Bearer t"}}
    return purl.lambda_handler(event, None)


def _doc(status: str = "done", key: str | None = KEY) -> dict:
    return {"result": {"renderedCompare": {"status": status, "key": key}}}


def test_done_exact_signs_one_hour_video(purl, url_s3, url_auth, analyses):
    """done + 서버 구성 canonical == 저장 key → 1시간 presign + video/mp4."""
    analyses[(UID, ANALYSIS_ID)] = _doc()

    resp = _call(purl, analysisId=ANALYSIS_ID, asset="renderedCompare")

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert set(body) == {"playbackUrl", "expiresInSec"}  # key 노출 표면 없음 (H-05)
    assert body["expiresInSec"] == 3600
    assert url_s3.signed[0]["Params"]["Key"] == KEY
    assert url_s3.signed[0]["Params"]["ResponseContentType"] == "video/mp4"
    assert url_s3.signed[0]["ExpiresIn"] == 3600


def test_failed_status_404_even_with_stale_key(purl, url_s3, url_auth, analyses):
    """M2-01 — failed 로 돌아간 doc 에 이전 key 가 남아 있어도 서명 0."""
    analyses[(UID, ANALYSIS_ID)] = _doc(status="failed")

    resp = _call(purl, analysisId=ANALYSIS_ID, asset="renderedCompare")

    assert resp["statusCode"] == 404
    assert url_s3.signed == []


def test_absent_field_404(purl, url_s3, url_auth, analyses):
    """legacy doc(renderedCompare 부재) — 404 (앱은 듀얼 플레이어 폴백)."""
    analyses[(UID, ANALYSIS_ID)] = {"result": {}}
    assert _call(purl, analysisId=ANALYSIS_ID, asset="renderedCompare")["statusCode"] == 404

    analyses[(UID, ANALYSIS_ID)] = {}
    assert _call(purl, analysisId=ANALYSIS_ID, asset="renderedCompare")["statusCode"] == 404
    assert url_s3.signed == []


def test_stale_or_foreign_key_404(purl, url_s3, url_auth, analyses):
    """저장 key 가 canonical 과 exact 불일치(오염/타 uid/버전 상이)면 전부 404."""
    for bad_key in (
        f"results/{UID}/{ANALYSIS_ID}/compare_v0.mp4",  # 구 렌더 버전
        build_rendered_compare_key(OTHER_UID, ANALYSIS_ID),  # 타 uid 산출물
        f"uploads/{UID}/{ANALYSIS_ID}.mp4",  # prefix 위반
        "",  # 빈 key
        None,  # 비 str
    ):
        analyses[(UID, ANALYSIS_ID)] = _doc(key=bad_key)
        resp = _call(purl, analysisId=ANALYSIS_ID, asset="renderedCompare")
        assert resp["statusCode"] == 404, f"key={bad_key!r}"
    assert url_s3.signed == []


def test_existing_asset_paths_unchanged(purl, url_s3, url_auth, analyses):
    """기존 asset 종류 무회귀 — correctedPose 는 기존 가드 그대로 200,
    미지원 asset 은 기존 400 유지 (분기 추가만 — 응답 바이트 불변 원칙)."""
    joint = "left_knee"
    corrected_key = f"results/{UID}/{ANALYSIS_ID}/corrected_pose_{joint}.png"
    analyses[(UID, ANALYSIS_ID)] = {
        "result": {
            "correctedPoseStatus": "done",
            "correctedPoseKey": corrected_key,
            "correctedPoseJoint": joint,
        }
    }

    resp = _call(purl, analysisId=ANALYSIS_ID, asset="correctedPose")
    assert resp["statusCode"] == 200
    assert url_s3.signed[0]["Params"]["Key"] == corrected_key

    resp = _call(purl, analysisId=ANALYSIS_ID, asset="nonsense")
    assert resp["statusCode"] == 400
