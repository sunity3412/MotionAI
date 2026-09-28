"""S3 키 발급/역파싱 라운드트립. AWS 불필요."""

from sunity_shared.s3keys import (
    REFERENCE_KEY_KIND_FINAL,
    REFERENCE_KEY_KIND_UPLOAD,
    build_reference_final_key,
    build_reference_upload_key,
    build_upload_key,
    parse_reference_key,
    parse_upload_key,
)


def test_roundtrip():
    key = build_upload_key("uid123", "abc123def", "mp4")
    assert key == "uploads/uid123/abc123def.mp4"
    parsed = parse_upload_key(key)
    assert parsed is not None
    assert parsed.uid == "uid123"
    assert parsed.analysis_id == "abc123def"
    assert parsed.ext == "mp4"


def test_mov_ext():
    parsed = parse_upload_key(build_upload_key("u", "a1", "mov"))
    assert parsed is not None and parsed.ext == "mov"


def test_rejects_foreign_keys():
    for bad in [
        "results/u/a.mp4",
        "uploads/u/a.avi",
        "uploads/a.mp4",
        "uploads/u/a/b.mp4",
        "random",
    ]:
        assert parse_upload_key(bad) is None


# --- Phase 38 공급자 링크 기준 키 (D-04 · D-19 · 리뷰 R5) ---------------------

_REF_ID = "0123456789abcdef0123456789abcdef"


def test_reference_key_roundtrip():
    up = build_reference_upload_key("uid42", _REF_ID, "mov")
    assert up == f"reference/uid42/{_REF_ID}/upload.mov"
    parsed = parse_reference_key(up)
    assert parsed is not None
    assert parsed.uid == "uid42"
    assert parsed.ref_id == _REF_ID
    assert parsed.ext == "mov"
    assert parsed.kind == "upload" == REFERENCE_KEY_KIND_UPLOAD
    assert parsed.is_upload is True

    final = build_reference_final_key("uid42", _REF_ID, "mov")
    assert final == f"reference/uid42/{_REF_ID}/v1.mov"
    parsed_final = parse_reference_key(final)
    assert parsed_final is not None
    assert parsed_final.uid == "uid42"
    assert parsed_final.ref_id == _REF_ID
    assert parsed_final.ext == "mov"
    assert parsed_final.kind == "v1" == REFERENCE_KEY_KIND_FINAL
    assert parsed_final.is_upload is False

    # 업로드 키와 확정 키는 같은 uid/refId 라도 서로 다른 객체다(R5).
    assert up != final


def test_parse_reference_key_final_kind_mp4():
    parsed = parse_reference_key("reference/u1/a1/v1.mp4")
    assert parsed is not None
    assert parsed.kind == "v1"
    assert parsed.ext == "mp4"


def test_parse_reference_key_rejects_legacy_and_foreign():
    for bad in [
        "reference/ref-kip-up.mp4",  # 기존 평면 11개(손 등록) — 무접촉
        "reference/_archive/ref-kip-up.mp4",  # 보관 폴더
        "reference/u1/a1.mp4",  # 리뷰 이전 옛 모양
        "reference/u1/a1/upload.avi",  # 허용 확장자 밖
        "reference/u1/a1/v2.mp4",  # kind 는 upload|v1 만(R5)
        "reference/u1/a1/original.mp4",  # 임의 파일명
        "reference/u-1/a1/upload.mp4",  # uid 세그먼트 영숫자 한정(D-19)
        "reference/u1/a1/upload.mp4.bak",
        "reference/u1/a1/b/upload.mp4",  # 세그먼트 수 초과
        "uploads/u1/a1.mp4",
        "results/u1/a1.mp4",
        "random",
    ]:
        assert parse_reference_key(bad) is None, bad


def test_upload_parser_rejects_reference_keys():
    # 학생 경로 파서는 기준 키를 절대 받지 않는다(Success ④ byte-무접촉).
    assert parse_upload_key("reference/u1/a1/upload.mp4") is None
    assert parse_upload_key("reference/u1/a1/v1.mp4") is None
