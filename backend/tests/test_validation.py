"""upload-url 입력 검증 — contract.md §2. AWS 불필요."""

import pytest

from sunity_shared import models
from sunity_shared.validation import ValidationError, validate_upload_request

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
