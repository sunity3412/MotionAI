"""S3 키 발급/역파싱 라운드트립. AWS 불필요."""

from sunity_shared.s3keys import build_upload_key, parse_upload_key


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
