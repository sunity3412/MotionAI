"""Phase 38 (Plan 38-01) — 기준 등록 계약 3벌 대조. AWS/Firestore 불필요.

models.py 의 REGISTRATION_* / REG_ERR_* / ANALYSIS_FIELD_SELF_CHECK_* 가
app/src/types/analysis.ts · docs/contract.md 와 같은 문자열로 존재하는지 파일 텍스트로
대조한다(계약 단일 진실 — CLAUDE.md Cross-cutting "세 벌 동시 변경").
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from sunity_shared import models

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_TS = REPO_ROOT / "app/src/types/analysis.ts"
CONTRACT_MD = REPO_ROOT / "docs/contract.md"
REFERENCE_MOTIONS_MD = REPO_ROOT / "docs/reference-motions.md"

# 이 값들이 바뀌면 3-way lockstep 이 깨진 것이다 — 등록 상태가 분석 status 머신에 새지
# 않았다는 단언의 기준선(현재 값 박제).
_ANALYSIS_STATUS_COUNT = 7  # uploading·queued·frame_extraction·pose_analysis·comparison·done·failed
_PIPELINE_SEQUENCE_COUNT = 5
_ANALYSIS_ERROR_CODE_COUNT = 5


def _ts_text() -> str:
    return ANALYSIS_TS.read_text(encoding="utf-8")


def _contract_text() -> str:
    return CONTRACT_MD.read_text(encoding="utf-8")


def _ts_type_body(text: str, type_name: str) -> str:
    """`export type <name> =` 부터 첫 `;` 까지 — 유니온 선언 본문."""
    m = re.search(rf"export type {type_name} =(.*?);", text, re.S)
    assert m, f"analysis.ts 에 export type {type_name} 가 없다"
    return m.group(1)


def _ts_interface_body(text: str, name: str) -> str:
    """`export interface <name> {` 부터 줄머리 `}` 까지 — 인터페이스 블록.

    AnalysisDoc 안에는 `error?: { code; message }` 같은 인라인 객체가 있어 '첫 `}`' 로
    자르면 필드 몇 개가 잘린다 — 블록 끝은 줄 첫 칸의 `}` 다.
    """
    start = text.find(f"export interface {name} {{")
    assert start >= 0, f"analysis.ts 에 export interface {name} 가 없다"
    end = text.find("\n}", start)
    assert end > start
    return text[start:end]


# ── (1)(2) 실패 코드 ↔ 문구 ────────────────────────────────────────────────


def test_error_message_keys_match_codes():
    assert set(models.REGISTRATION_ERROR_MESSAGE) == set(models.REGISTRATION_ERROR_CODES)
    assert len(models.REGISTRATION_ERROR_CODES) == 8
    assert models.REG_ERR_TOO_LARGE in models.REGISTRATION_ERROR_CODES


def test_no_human_reuses_analysis_error_message_object():
    # D-09 — 문자열 복사가 아니라 객체 그대로 참조. 기존 문구가 바뀌면 같이 바뀐다.
    assert models.REGISTRATION_ERROR_MESSAGE["no_human"] is models.ERROR_MESSAGE["no_human"]


def test_too_long_and_too_large_messages_w9l():
    # belle 2026-09-30 — 5초~2분 · 1GB. 3벌 대조는 아래 test_ts_mirror / test_contract_md 가 잠근다.
    assert (
        models.REGISTRATION_ERROR_MESSAGE[models.REG_ERR_TOO_LONG]
        == "영상이 너무 길어요. 기준 동작은 2분 이내로 올려주세요."
    )
    assert (
        models.REGISTRATION_ERROR_MESSAGE[models.REG_ERR_TOO_LARGE]
        == "용량이 너무 커요. 1GB 이하 영상으로 다시 올려주세요."
    )


def test_low_confidence_placeholder_is_replace_style():
    # 파이프라인은 str.replace("{joints}", ...) 로 치환한다 — 중괄호 자리는 정확히 하나.
    msg = models.REGISTRATION_ERROR_MESSAGE[models.REG_ERR_LOW_CONFIDENCE]
    assert msg.count("{joints}") == 1
    assert msg.count("{") == 1 and msg.count("}") == 1


# ── (3) 별개 enum — 분석 status 머신 무접촉 ─────────────────────────────────


def test_registration_states_do_not_leak_into_analysis_status_machine():
    assert "registering" not in models.PIPELINE_SEQUENCE
    assert "active" not in models.PIPELINE_SEQUENCE
    assert "expired" not in models.PIPELINE_SEQUENCE
    assert len(models.PIPELINE_SEQUENCE) == _PIPELINE_SEQUENCE_COUNT
    assert len(models.ANALYSIS_ERROR_CODES) == _ANALYSIS_ERROR_CODE_COUNT
    status_consts = [
        models.STATUS_UPLOADING,
        models.STATUS_QUEUED,
        models.STATUS_FRAME_EXTRACTION,
        models.STATUS_POSE_ANALYSIS,
        models.STATUS_COMPARISON,
        models.STATUS_DONE,
        models.STATUS_FAILED,
    ]
    assert len(set(status_consts)) == _ANALYSIS_STATUS_COUNT

    assert models.REGISTRATION_STATUSES == (
        "registering",
        "queued",
        "processing",
        "failed",
        "active",
        "expired",
    )
    assert models.REGISTRATION_STATUS_EXPIRED in models.REGISTRATION_STATUSES
    assert models.SELF_CHECK_STATUSES == ("pending", "queued", "done", "failed")

    # TS 쪽 AnalysisStatus 유니온에도 새지 않았다.
    ts_status = _ts_type_body(_ts_text(), "AnalysisStatus")
    assert "'registering'" not in ts_status
    assert "'active'" not in ts_status
    assert "'expired'" not in ts_status


# ── (4) SUPPLIER_UIDS 파서 (D-12) ─────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, {}),
        ("", {}),
        ("   ", {}),
        ("abc:EUNJI", {"abc": "EUNJI"}),
        ("abc:EUNJI, def, ghi:bad code", {"abc": "EUNJI", "def": None, "ghi": None}),
        ("abc:eunji", {"abc": None}),  # 소문자 — 형식 오류, uid 는 유지
        ("abc:AB", {"abc": None}),  # 3자 미만
        ("abc:ABCDEFGHI", {"abc": None}),  # 8자 초과
        (" abc : EUNJI ,, def ", {"abc": "EUNJI", "def": None}),  # 공백·빈 항목
        (":EUNJI", {}),  # uid 없음 — 무시
    ],
)
def test_parse_supplier_uids(value, expected):
    assert models.parse_supplier_uids(value) == expected


def test_supplier_code_re_bounds():
    assert models.SUPPLIER_CODE_RE.match("ABC")
    assert models.SUPPLIER_CODE_RE.match("A1B2C3D4")
    assert not models.SUPPLIER_CODE_RE.match("ab")
    assert not models.SUPPLIER_CODE_RE.match("ABC DEF")


# ── (5) 3벌 대조: analysis.ts · contract.md ─────────────────────────────────


def test_ts_mirror_has_codes_statuses_and_messages():
    text = _ts_text()

    code_body = _ts_type_body(text, "ReferenceRegistrationErrorCode")
    for code in models.REGISTRATION_ERROR_CODES:
        assert f"'{code}'" in code_body, code

    status_body = _ts_type_body(text, "ReferenceRegistrationStatus")
    for status in models.REGISTRATION_STATUSES:
        assert f"'{status}'" in status_body, status
    assert "'expired'" in status_body

    self_body = _ts_type_body(text, "SelfCheckStatus")
    for status in models.SELF_CHECK_STATUSES:
        assert f"'{status}'" in self_body, status

    assert "export const REGISTRATION_ERROR_MESSAGE" in text
    for code, msg in models.REGISTRATION_ERROR_MESSAGE.items():
        if code == models.REG_ERR_NO_HUMAN:
            # 객체 참조 — TS 도 ERROR_MESSAGE.no_human 을 참조한다.
            assert "no_human: ERROR_MESSAGE.no_human" in text
            continue
        assert msg in text, code

    for name in (
        "ReferenceRegistrationError",
        "ReferenceConsent",
        "ReferenceUploadUrlRequest",
        "ReferenceUploadUrlResponse",
        "SupplierProbeResponse",
        "ReferenceRegistrationPrivate",
    ):
        assert f"export interface {name} " in text, name


def test_contract_md_has_endpoint_messages_and_private_doc():
    text = _contract_text()
    assert "supplier_name_missing" in text
    assert "trainingBasis" in text
    assert text.count("### POST /reference/upload-url") == 1
    assert "REGISTRATION_ERROR_MESSAGE" in text
    assert "reference/{refId}/private/registration" in text
    assert "ReferenceRegistrationPrivate" in text
    for code, msg in models.REGISTRATION_ERROR_MESSAGE.items():
        if code == models.REG_ERR_NO_HUMAN:
            continue
        assert msg in text, code
    for code in models.REGISTRATION_ERROR_CODES:
        assert code in text, code


def test_reference_motions_md_marks_register_fields():
    text = REFERENCE_MOTIONS_MD.read_text(encoding="utf-8")
    assert text.count("// register") >= 10
    assert "private/registration" in text
    assert "ReferenceRegistrationPrivate" in text


# ── (6) selfCheckForReference · selfCheckJobId 3벌 (D-10, R2·R8) ────────────


def test_self_check_field_constants_three_way():
    assert models.ANALYSIS_FIELD_SELF_CHECK_FOR_REFERENCE == "selfCheckForReference"
    assert models.ANALYSIS_FIELD_SELF_CHECK_JOB_ID == "selfCheckJobId"

    doc_block = _ts_interface_body(_ts_text(), "AnalysisDoc")
    assert "selfCheckForReference?: string | null;" in doc_block
    assert "selfCheckJobId?: string | null;" in doc_block

    contract = _contract_text()
    s3 = contract.find("## 3. Firestore 문서")
    s4 = contract.find("## 4.", s3)
    assert 0 <= s3 < s4
    section = contract[s3:s4]
    assert "selfCheckForReference" in section
    assert "selfCheckJobId" in section


# ── (7) 경로·상수 ──────────────────────────────────────────────────────────


def test_private_path_and_constants():
    assert models.reference_private_path("abc") == "reference/abc/private/registration"
    assert models.REFERENCE_PRIVATE_SUBCOLLECTION == "private"
    assert models.REFERENCE_PRIVATE_DOC_ID == "registration"
    assert models.REFERENCE_UPLOAD_EXPIRES_SEC == 900
    assert models.REGISTRATION_LEASE_SEC == 900
    assert models.REFERENCE_LEVELS == ("basic", "intermediate", "advanced")
    assert models.REFERENCE_MIN_DURATION_SEC == 5.0
    # quick-260930-w9l (belle 09-30): 5초~2분 하나, 콤보 상한(2026-09-30 삭제).
    assert models.REFERENCE_MAX_DURATION_SEC == 120.0
    assert not hasattr(models, "REFERENCE_COMBO_MAX_DURATION_SEC")
    # 공급자 기준 등록만 1GB — 수강생 분석 경로는 100MB 그대로.
    assert models.REFERENCE_MAX_VIDEO_BYTES == 1024 * 1024 * 1024
    assert models.MAX_VIDEO_BYTES == 100 * 1024 * 1024
    assert models.REFERENCE_NAME_MAX_LEN == 30
    # 동의 문안이 바뀌어 판을 올렸다(w9l) + 학습 근거 = 공급자 계약.
    assert models.CONSENT_VERSION == "2026-09-30"
    assert models.CONSENT_TRAINING_BASIS_CONTRACT == "supplier_contract"
    assert models.SUPPLIER_ERR_NAME_MISSING == "supplier_name_missing"
    assert (
        models.SUPPLIER_NAME_MISSING_MESSAGE
        == "선수 이름이 등록되지 않았어요. 운영팀에 알려주세요."
    )
    assert models.SUPPLIER_UIDS_PARAM_DEFAULT == "/sunity/motion/supplier-uids"
