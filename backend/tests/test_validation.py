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
# quick-260930-w9l (belle 2026-09-30 폰 확인): 새 본문 = name·level·techniqueRefId?·
# consent{portrait,usage}·format·fileSizeBytes·durationSec?. 선수 이름은 서버가 공급자
# displayName 으로 채운다. 옛 웹 번들이 보내는 athleteName·isCombo·isSplit·hasHold·
# standingStart·consent.silent·consent.training 은 **검증 없이 무시**한다.

OK_REFERENCE = {
    "name": "  킵업 ",
    "level": "intermediate",
    "techniqueRefId": "ref-kip-up",
    "clipRange": {"execStartS": 1.5, "execEndS": 7},
    "consent": {"portrait": True, "usage": True},
    "format": "mov",
    "fileSizeBytes": 30 * 1024 * 1024,
    "durationSec": 12.4,
}

# 배포된 옛 웹 번들(38-13) 본문 — 새 서버도 200 이어야 한다(웹이 늦게 나가는 동안).
OLD_WEB_BODY = {
    **OK_REFERENCE,
    "athleteName": " 정은지 ",
    "isCombo": "true",  # 옛 검증이면 bad_request — 이제 무시
    "isSplit": 1,
    "hasHold": "yes",
    "standingStart": False,  # 옛 D-09 사전 차단 — 이제 파이프라인 no_standing_start 가 본다
    "consent": {"portrait": True, "usage": True, "silent": False, "training": "yes"},
}


def test_reference_ok_normalizes():
    req = validate_reference_upload_request(OK_REFERENCE)
    assert req.name == "킵업"  # strip
    assert req.level == "intermediate"
    assert req.technique_ref_id == "ref-kip-up"
    assert req.clip_range == (1.5, 7.0)  # 튜플, float 정규화
    assert req.fmt == "mov"
    assert req.file_size_bytes == 30 * 1024 * 1024
    assert req.duration_sec == 12.4


def test_reference_request_has_no_dropped_fields():
    """선수 이름·선언 4·학습 동의는 요청 dataclass 에서 빠졌다(w9l 항목 5·9·10·11)."""
    req = validate_reference_upload_request(OK_REFERENCE)
    for gone in (
        "athlete_name",
        "is_combo",
        "is_split",
        "has_hold",
        "standing_start",
        "consent_training",
    ):
        assert not hasattr(req, gone), gone


def test_reference_old_web_body_is_accepted_and_ignored():
    req = validate_reference_upload_request(OLD_WEB_BODY)
    assert req.name == "킵업"
    assert req.level == "intermediate"


def test_reference_optional_fields_absent():
    body = dict(OK_REFERENCE)
    body["techniqueRefId"] = None
    body["clipRange"] = None
    body["durationSec"] = None  # 웹이 metadata 를 못 읽은 경우 — fail-open
    req = validate_reference_upload_request(body)
    assert req.technique_ref_id is None
    assert req.clip_range is None
    assert req.duration_sec is None


def test_reference_duration_upper_bound_is_120s_even_for_combo():
    """콤보 상한(2026-09-30 삭제) — 길이 상한은 하나, isCombo 는 무시."""
    assert models.REFERENCE_MAX_DURATION_SEC == 120.0
    assert not hasattr(models, "REFERENCE_COMBO_MAX_DURATION_SEC")
    req = validate_reference_upload_request({**OK_REFERENCE, "durationSec": 120})
    assert req.duration_sec == 120.0
    with pytest.raises(ValidationError) as e:
        validate_reference_upload_request(
            {**OK_REFERENCE, "isCombo": True, "durationSec": 120.1}
        )
    assert e.value.code == models.REG_ERR_TOO_LONG


def test_reference_size_limit_is_1gb_with_registration_message():
    assert models.REFERENCE_MAX_VIDEO_BYTES == 1024 * 1024 * 1024
    assert models.MAX_VIDEO_BYTES == 100 * 1024 * 1024  # 수강생 경로 불변
    req = validate_reference_upload_request(
        {**OK_REFERENCE, "fileSizeBytes": models.REFERENCE_MAX_VIDEO_BYTES}
    )
    assert req.file_size_bytes == models.REFERENCE_MAX_VIDEO_BYTES
    with pytest.raises(ValidationError) as e:
        validate_reference_upload_request(
            {**OK_REFERENCE, "fileSizeBytes": models.REFERENCE_MAX_VIDEO_BYTES + 1}
        )
    assert e.value.code == models.REG_ERR_TOO_LARGE
    assert e.value.message == models.REGISTRATION_ERROR_MESSAGE[models.REG_ERR_TOO_LARGE]
    assert "1GB" in e.value.message


def test_student_upload_still_100mb():
    with pytest.raises(ValidationError) as e:
        validate_upload_request({**OK_MODE3, "fileSizeBytes": models.MAX_VIDEO_BYTES + 1})
    assert e.value.code == models.ERR_SIZE_EXCEEDED


@pytest.mark.parametrize(
    ("patch", "code"),
    [
        ({"name": "   "}, "bad_request"),
        ({"name": "가" * 31}, "bad_request"),  # REFERENCE_NAME_MAX_LEN = 30
        ({"level": "pro"}, "bad_request"),
        ({"techniqueRefId": "bad id!"}, "bad_request"),
        ({"clipRange": {"execStartS": 5, "execEndS": 3}}, "bad_request"),
        ({"clipRange": {"execStartS": True, "execEndS": 3}}, "bad_request"),
        ({"clipRange": [1, 2]}, "bad_request"),
        ({"consent": {"portrait": True, "usage": False}}, "bad_request"),
        ({"consent": {"portrait": True}}, "bad_request"),  # usage 누락
        ({"consent": {"usage": True, "silent": True, "training": True}}, "bad_request"),
        ({"format": "avi"}, models.ERR_UNSUPPORTED_FORMAT),
        ({"fileSizeBytes": True}, "bad_request"),
        ({"fileSizeBytes": 0}, "bad_request"),
        ({"fileSizeBytes": models.REFERENCE_MAX_VIDEO_BYTES + 1}, models.REG_ERR_TOO_LARGE),
        ({"durationSec": 4.9}, models.REG_ERR_TOO_SHORT),
        ({"durationSec": 120.1}, models.REG_ERR_TOO_LONG),
        ({"durationSec": "12"}, "bad_request"),
        ({"durationSec": 0}, "bad_request"),
    ],
)
def test_reference_rejections(patch, code):
    with pytest.raises(ValidationError) as e:
        validate_reference_upload_request({**OK_REFERENCE, **patch})
    assert e.value.code == code


def test_reference_consent_message_is_two():
    with pytest.raises(ValidationError) as e:
        validate_reference_upload_request(
            {**OK_REFERENCE, "consent": {"portrait": True}}
        )
    assert e.value.message == "필수 동의 2가지에 체크해주세요."


def test_reference_consent_missing_rejected():
    body = dict(OK_REFERENCE)
    del body["consent"]
    with pytest.raises(ValidationError) as e:
        validate_reference_upload_request(body)
    assert e.value.code == "bad_request"
    assert e.value.message == "필수 동의 2가지에 체크해주세요."


def test_reference_duration_codes_reuse_registration_messages():
    with pytest.raises(ValidationError) as e:
        validate_reference_upload_request({**OK_REFERENCE, "durationSec": 3})
    assert e.value.message == models.REGISTRATION_ERROR_MESSAGE[models.REG_ERR_TOO_SHORT]
    with pytest.raises(ValidationError) as e:
        validate_reference_upload_request({**OK_REFERENCE, "durationSec": 121})
    assert e.value.message == models.REGISTRATION_ERROR_MESSAGE[models.REG_ERR_TOO_LONG]


def test_reference_non_dict_body_rejected():
    with pytest.raises(ValidationError):
        validate_reference_upload_request(["not", "a", "dict"])  # type: ignore[arg-type]
