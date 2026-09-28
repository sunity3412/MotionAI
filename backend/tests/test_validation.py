"""upload-url · reference/upload-url 입력 검증 — contract.md §2. AWS 불필요."""

import pytest

from sunity_shared import models
from sunity_shared.validation import (
    ValidationError,
    validate_reference_upload_request,
    validate_upload_request,
)

OK_MODE3 = {
    "mode": "mode3",
    "fileName": "swing.mp4",
    "fileSizeBytes": 5 * 1024 * 1024,
    "format": "mp4",
}


def test_mode3_valid():
    req = validate_upload_request(OK_MODE3)
    assert req.mode == "mode3"
    assert req.fmt == "mp4"
    assert req.reference_motion_id is None  # mode3 은 비교 대상 없음


def test_mode1_requires_reference_motion_id():
    body = {**OK_MODE3, "mode": "mode1"}
    with pytest.raises(ValidationError) as e:
        validate_upload_request(body)
    assert e.value.code == "bad_request"


def test_mode1_with_reference_ok():
    req = validate_upload_request(
        {**OK_MODE3, "mode": "mode1", "referenceMotionId": "  m1 "}
    )
    assert req.mode == "mode1"
    assert req.reference_motion_id == "m1"  # trim 됨


def test_unsupported_format_uses_contract_code():
    with pytest.raises(ValidationError) as e:
        validate_upload_request({**OK_MODE3, "format": "avi"})
    assert e.value.code == models.ERR_UNSUPPORTED_FORMAT
    assert e.value.message == models.ERROR_MESSAGE[models.ERR_UNSUPPORTED_FORMAT]


def test_size_exceeded_uses_contract_code():
    with pytest.raises(ValidationError) as e:
        validate_upload_request(
            {**OK_MODE3, "fileSizeBytes": models.MAX_VIDEO_BYTES + 1}
        )
    assert e.value.code == models.ERR_SIZE_EXCEEDED


def test_size_boundary_exactly_100mb_ok():
    req = validate_upload_request(
        {**OK_MODE3, "fileSizeBytes": models.MAX_VIDEO_BYTES}
    )
    assert req.file_size_bytes == models.MAX_VIDEO_BYTES


@pytest.mark.parametrize(
    "patch",
    [
        {"mode": "modeX"},
        {"fileName": "  "},
        {"fileSizeBytes": 0},
        {"fileSizeBytes": "10"},
        {"fileSizeBytes": True},  # bool 은 int 로 위장 — 거부돼야 함
    ],
)
def test_bad_inputs_rejected(patch):
    with pytest.raises(ValidationError):
        validate_upload_request({**OK_MODE3, **patch})


def test_non_dict_body_rejected():
    with pytest.raises(ValidationError):
        validate_upload_request("not-a-dict")  # type: ignore[arg-type]


# ── Phase 38 (Plan 38-01) — POST /reference/upload-url 폼 검증 (D-07·D-08·D-14) ──

OK_REFERENCE = {
    "name": "  킵업 ",
    "athleteName": " 정은지 ",
    "level": "intermediate",
    "techniqueRefId": "ref-kip-up",
    "isCombo": False,
    "isSplit": True,
    "hasHold": False,
    "standingStart": True,
    "clipRange": {"execStartS": 1.5, "execEndS": 7},
    "consent": {"portrait": True, "usage": True, "silent": True, "training": True},
    "format": "mov",
    "fileSizeBytes": 30 * 1024 * 1024,
    "durationSec": 12.4,
}


def test_reference_ok_normalizes():
    req = validate_reference_upload_request(OK_REFERENCE)
    assert req.name == "킵업"  # strip
    assert req.athlete_name == "정은지"
    assert req.level == "intermediate"
    assert req.technique_ref_id == "ref-kip-up"
    assert req.is_combo is False
    assert req.is_split is True and req.has_hold is False and req.standing_start is True
    assert req.clip_range == (1.5, 7.0)  # 튜플, float 정규화
    assert req.consent_training is True
    assert req.fmt == "mov"
    assert req.file_size_bytes == 30 * 1024 * 1024
    assert req.duration_sec == 12.4


def test_reference_defaults_training_false_and_combo_false():
    body = {**OK_REFERENCE, "consent": {"portrait": True, "usage": True, "silent": True}}
    del body["isCombo"]
    body["techniqueRefId"] = None
    body["clipRange"] = None
    body["durationSec"] = None  # 웹이 metadata 를 못 읽은 경우 — fail-open
    req = validate_reference_upload_request(body)
    assert req.consent_training is False  # D-08 기본 꺼짐
    assert req.is_combo is False
    assert req.technique_ref_id is None
    assert req.clip_range is None
    assert req.duration_sec is None


def test_reference_combo_allows_up_to_60s():
    req = validate_reference_upload_request(
        {**OK_REFERENCE, "isCombo": True, "durationSec": 45}
    )
    assert req.is_combo is True and req.duration_sec == 45.0


@pytest.mark.parametrize(
    ("patch", "code"),
    [
        ({"name": "   "}, "bad_request"),
        ({"name": "가" * 31}, "bad_request"),  # REFERENCE_NAME_MAX_LEN = 30
        ({"athleteName": ""}, "bad_request"),
        ({"level": "pro"}, "bad_request"),
        ({"techniqueRefId": "bad id!"}, "bad_request"),
        ({"isSplit": 1}, "bad_request"),  # int 위장 거부
        ({"hasHold": "yes"}, "bad_request"),
        ({"standingStart": False}, "bad_request"),  # D-09 사전 차단
        ({"isCombo": "true"}, "bad_request"),
        ({"clipRange": {"execStartS": 5, "execEndS": 3}}, "bad_request"),
        ({"clipRange": {"execStartS": True, "execEndS": 3}}, "bad_request"),
        ({"clipRange": [1, 2]}, "bad_request"),
        ({"consent": {"portrait": True, "usage": False, "silent": True}}, "bad_request"),
        ({"consent": {"portrait": True, "silent": True}}, "bad_request"),  # usage 누락
        ({"consent": {"portrait": True, "usage": True, "silent": True, "training": "yes"}}, "bad_request"),
        ({"format": "avi"}, models.ERR_UNSUPPORTED_FORMAT),
        ({"fileSizeBytes": True}, "bad_request"),
        ({"fileSizeBytes": 0}, "bad_request"),
        ({"fileSizeBytes": models.MAX_VIDEO_BYTES + 1}, models.ERR_SIZE_EXCEEDED),
        ({"durationSec": 4.9}, models.REG_ERR_TOO_SHORT),
        ({"durationSec": 31}, models.REG_ERR_TOO_LONG),
        ({"durationSec": 61, "isCombo": True}, models.REG_ERR_TOO_LONG),
        ({"durationSec": "12"}, "bad_request"),
        ({"durationSec": 0}, "bad_request"),
    ],
)
def test_reference_rejections(patch, code):
    with pytest.raises(ValidationError) as e:
        validate_reference_upload_request({**OK_REFERENCE, **patch})
    assert e.value.code == code


def test_reference_consent_missing_rejected():
    body = dict(OK_REFERENCE)
    del body["consent"]
    with pytest.raises(ValidationError) as e:
        validate_reference_upload_request(body)
    assert e.value.code == "bad_request"


def test_reference_duration_codes_reuse_registration_messages():
    with pytest.raises(ValidationError) as e:
        validate_reference_upload_request({**OK_REFERENCE, "durationSec": 3})
    assert e.value.message == models.REGISTRATION_ERROR_MESSAGE[models.REG_ERR_TOO_SHORT]
    with pytest.raises(ValidationError) as e:
        validate_reference_upload_request({**OK_REFERENCE, "durationSec": 40})
    assert e.value.message == models.REGISTRATION_ERROR_MESSAGE[models.REG_ERR_TOO_LONG]


def test_reference_non_dict_body_rejected():
    with pytest.raises(ValidationError):
        validate_reference_upload_request(["not", "a", "dict"])  # type: ignore[arg-type]
