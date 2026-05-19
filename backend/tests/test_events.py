"""SQS→S3 이벤트 키 추출. AWS 불필요."""

import json

from sunity_shared.events import iter_s3_keys_from_sqs


def _sqs(*keys):
    return {
        "Records": [
            {
                "body": json.dumps(
                    {
                        "Records": [
                            {
                                "s3": {
                                    "bucket": {"name": "b"},
                                    "object": {"key": k},
                                }
                            }
                        ]
                    }
                )
            }
            for k in keys
        ]
    }


def test_extracts_keys_in_order():
    out = list(iter_s3_keys_from_sqs(_sqs("uploads/u/a.mp4", "uploads/u/b.mov")))
    assert out == [("b", "uploads/u/a.mp4"), ("b", "uploads/u/b.mov")]


def test_url_decodes_key():
    # S3 는 공백을 '+' 로 인코딩
    out = list(iter_s3_keys_from_sqs(_sqs("uploads/u/my+clip.mp4")))
    assert out == [("b", "uploads/u/my clip.mp4")]


def test_skips_broken_records():
    event = {"Records": [{"body": "not-json"}, {"body": ""}, {}]}
    assert list(iter_s3_keys_from_sqs(event)) == []


def test_empty_event():
    assert list(iter_s3_keys_from_sqs({})) == []
