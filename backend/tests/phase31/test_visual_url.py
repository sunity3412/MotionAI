"""canonical key → 인증 재서명 URL 발급 (Firestore 에 URL 미저장 — H-02/H3-01) — 담당 플랜 31-10.

실 Firestore/네트워크/S3 미접촉 — LOCAL ONLY. 공용 스캐폴드는 conftest.py 소유.

여기서 검증하는 것은 "URL 이 나온다" 가 아니라 **서버가 구성한 canonical key 와
전체 문자열이 일치할 때만 서명된다**는 계약이다 (2차 리뷰 M2-01). status 가
failed 로 돌아간 뒤에도 이전 성공분 key 필드가 문서에 남을 수 있고, prefix/basename
부분일치만 보면 그 stale key 가 계속 서명되기 때문이다.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

_APP = Path(__file__).resolve().parents[2] / "functions" / "playback-url" / "app.py"

UID = "u1"
OTHER_UID = "u2"
ANALYSIS_ID = "a" * 32
JOINT = "left_knee"


def _load_app():
    """하이픈 디렉터리의 Lambda 핸들러를 `visual_url` 로 적재 (backend 테스트 관례)."""
    if "visual_url" in sys.modules:
        return sys.modules["visual_url"]
    os.environ.setdefault("VIDEO_BUCKET", "test-bucket")
    spec = importlib.util.spec_from_file_location("visual_url", _APP)
    module = importlib.util.module_from_spec(spec)
    sys.modules["visual_url"] = module
    spec.loader.exec_module(module)
    return module


app = _load_app()

CORRECTED_KEY = f"results/{UID}/{ANALYSIS_ID}/corrected_pose_{JOINT}.png"
ROTATION_KEY = f"results/{UID}/{ANALYSIS_ID}/rotation.mp4"


class FakeS3:
    def __init__(self) -> None:
        self.signed: list[dict] = []
        self.fail = False

    def generate_presigned_url(self, _op, Params=None, ExpiresIn=None):  # noqa: N803
        if self.fail:
            raise RuntimeError("sign failed (injected)")
        self.signed.append({"Params": Params, "ExpiresIn": ExpiresIn})
        return f"https://s3.example/signed?k={Params['Key']}"


@pytest.fixture
def s3(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(app, "_s3", fake)
    return fake


@pytest.fixture
def auth(monkeypatch):
    """기본 = UID 로 인증 성공. 테스트가 실패를 주입한다."""
    state = {"uid": UID, "raise": False}

    def _verify(_event):
        if state["raise"]:
            raise app.AuthError("토큰 없음")
        return state["uid"]

    monkeypatch.setattr(app, "verify_request", _verify)
    return state


@pytest.fixture
def analyses(monkeypatch):
    """(uid, analysisId) → 문서. get_analysis 대체로 uid 스코프를 실제로 강제한다."""
    store: dict[tuple[str, str], dict] = {}
    monkeypatch.setattr(
        app.firestore_admin, "get_analysis", lambda uid, aid: store.get((uid, aid))
    )
    return store


def _doc(**result) -> dict:
    return {"result": result}


def _call(**body) -> dict:
    event = {"body": json.dumps(body), "headers": {"authorization": "Bearer t"}}
    return app.lambda_handler(event, None)


def _status(resp) -> int:
    return resp["statusCode"]


def _body(resp) -> dict:
    return json.loads(resp["body"])


# ─────────────────────── 정상 재서명 ───────────────────────


def test_corrected_pose_fresh_sign(s3, auth, analyses):
    """done + canonical key 일치 → 1시간 presign + image/png."""
    analyses[(UID, ANALYSIS_ID)] = _doc(
        correctedPoseStatus="done", correctedPoseKey=CORRECTED_KEY, correctedPoseJoint=JOINT
    )

    resp = _call(analysisId=ANALYSIS_ID, asset="correctedPose")

    assert _status(resp) == 200
    assert _body(resp)["expiresInSec"] == 3600
    assert s3.signed[0]["ExpiresIn"] == 3600
    assert s3.signed[0]["Params"]["Key"] == CORRECTED_KEY
    assert s3.signed[0]["Params"]["ResponseContentType"] == "image/png"


def test_rotation_fresh_sign(s3, auth, analyses):
    analyses[(UID, ANALYSIS_ID)] = _doc(rotationStatus="done", rotationVideoKey=ROTATION_KEY)

    resp = _call(analysisId=ANALYSIS_ID, asset="rotation")

    assert _status(resp) == 200
    assert s3.signed[0]["Params"]["Key"] == ROTATION_KEY
    assert s3.signed[0]["Params"]["ResponseContentType"] == "video/mp4"


def test_response_shape_is_url_and_ttl_only(s3, auth, analyses):
    """응답 필드는 2개뿐 — 클라이언트가 key 를 다루는 표면이 없다 (H-02/H-05)."""
    analyses[(UID, ANALYSIS_ID)] = _doc(rotationStatus="done", rotationVideoKey=ROTATION_KEY)

    body = _body(_call(analysisId=ANALYSIS_ID, asset="rotation"))

    assert set(body) == {"playbackUrl", "expiresInSec"}


# ─────────────────────── 가드 = 전부 동일 404 ───────────────────────


def test_other_uid_cannot_sign(s3, auth, analyses):
    """타인 문서는 uid 스코프 조회에서 애초에 안 잡힌다 — 404, 서명 0."""
    analyses[(OTHER_UID, ANALYSIS_ID)] = _doc(
        rotationStatus="done", rotationVideoKey=f"results/{OTHER_UID}/{ANALYSIS_ID}/rotation.mp4"
    )

    resp = _call(analysisId=ANALYSIS_ID, asset="rotation")

    assert _status(resp) == 404
    assert s3.signed == []


def test_missing_field_404(s3, auth, analyses):
    """아직 생성 안 됨(필드 부재) → 404."""
    analyses[(UID, ANALYSIS_ID)] = _doc()

    assert _status(_call(analysisId=ANALYSIS_ID, asset="rotation")) == 404
    assert s3.signed == []


def test_failed_status_with_stale_key_404(s3, auth, analyses):
    """M2-01 핵심: status failed 인데 이전 성공분 key 가 남아 있어도 서명 불가."""
    analyses[(UID, ANALYSIS_ID)] = _doc(rotationStatus="failed", rotationVideoKey=ROTATION_KEY)

    resp = _call(analysisId=ANALYSIS_ID, asset="rotation")

    assert _status(resp) == 404
    assert s3.signed == []


def test_pending_status_404(s3, auth, analyses):
    analyses[(UID, ANALYSIS_ID)] = _doc(rotationStatus="pending", rotationVideoKey=ROTATION_KEY)

    assert _status(_call(analysisId=ANALYSIS_ID, asset="rotation")) == 404
    assert s3.signed == []


def test_basename_mismatch_404(s3, auth, analyses):
    """prefix 는 맞지만 basename 이 다른 key → exact equality 실패로 404.

    prefix 검사만 하는 구현이면 여기서 200 이 나온다 (M2-01 회귀 가드).
    """
    analyses[(UID, ANALYSIS_ID)] = _doc(
        rotationStatus="done", rotationVideoKey=f"results/{UID}/{ANALYSIS_ID}/other.mp4"
    )

    resp = _call(analysisId=ANALYSIS_ID, asset="rotation")

    assert _status(resp) == 404
    assert s3.signed == []


def test_corrected_pose_joint_missing_404(s3, auth, analyses):
    """joint 부재 = canonical key 구성 불가 → 404 (key 추측 서명 차단)."""
    analyses[(UID, ANALYSIS_ID)] = _doc(
        correctedPoseStatus="done", correctedPoseKey=CORRECTED_KEY
    )

    assert _status(_call(analysisId=ANALYSIS_ID, asset="correctedPose")) == 404
    assert s3.signed == []


def test_corrected_pose_joint_mismatch_404(s3, auth, analyses):
    """저장 key 의 joint 와 correctedPoseJoint 가 어긋나면 exact 비교가 막는다."""
    analyses[(UID, ANALYSIS_ID)] = _doc(
        correctedPoseStatus="done",
        correctedPoseKey=CORRECTED_KEY,
        correctedPoseJoint="right_knee",
    )

    assert _status(_call(analysisId=ANALYSIS_ID, asset="correctedPose")) == 404


def test_analysis_doc_missing_404(s3, auth, analyses):
    assert _status(_call(analysisId=ANALYSIS_ID, asset="rotation")) == 404
    assert s3.signed == []


# ─────────────────────── 입력 검증 ───────────────────────


def test_invalid_asset_400(s3, auth, analyses):
    resp = _call(analysisId=ANALYSIS_ID, asset="thumbnail")

    assert _status(resp) == 400
    assert _body(resp)["error"]["code"] == "bad_request"
    assert s3.signed == []


def test_asset_with_bad_analysis_id_400(s3, auth, analyses):
    """asset 경로도 analysisId 형식 가드를 먼저 통과해야 한다 (path injection)."""
    resp = _call(analysisId="../../etc", asset="rotation")

    assert _status(resp) == 400
    assert s3.signed == []


def test_no_token_401(s3, auth, analyses):
    auth["raise"] = True

    resp = _call(analysisId=ANALYSIS_ID, asset="rotation")

    assert _status(resp) == 401
    assert s3.signed == []


def test_sign_failure_500(s3, auth, analyses):
    analyses[(UID, ANALYSIS_ID)] = _doc(rotationStatus="done", rotationVideoKey=ROTATION_KEY)
    s3.fail = True

    assert _status(_call(analysisId=ANALYSIS_ID, asset="rotation")) == 500


# ─────────────────────── 무회귀: asset 미지정 ───────────────────────


def test_asset_unspecified_preserves_legacy_path(s3, auth, analyses):
    """asset 미지정 = 기존 동작 — uploads/ key 를 7일 TTL 로, content-type 미포함."""
    resp = _call(analysisId=ANALYSIS_ID, ext="mp4")

    assert _status(resp) == 200
    assert _body(resp)["expiresInSec"] == app._PLAYBACK_EXPIRES
    assert s3.signed[0]["Params"]["Key"] == f"uploads/{UID}/{ANALYSIS_ID}.mp4"
    assert "ResponseContentType" not in s3.signed[0]["Params"]


def test_asset_unspecified_bad_ext_still_400(s3, auth, analyses):
    assert _status(_call(analysisId=ANALYSIS_ID, ext="avi")) == 400


# ─────────────────────── 공유 validator (L-03) ───────────────────────


def test_shared_validator_is_single_source():
    """playback-url 이 인라인 검사를 복제하지 않고 공유 validator 를 쓴다."""
    from sunity_shared.validation import validate_analysis_id_format

    assert validate_analysis_id_format("a" * 32) is True
    assert validate_analysis_id_format("short") is False
    assert validate_analysis_id_format("../../etc/passwd") is False
    assert validate_analysis_id_format(None) is False
    assert validate_analysis_id_format("a" * 15) is False

    source = _APP.read_text(encoding="utf-8")
    assert "validate_analysis_id_format" in source
    assert ".isalnum()" not in source  # 인라인 중복 0
