"""auth.py 의 SA 키 로딩 분기 — RunPod 등 비-AWS 환경 지원.

_load_service_account_dict() 의 우선순위:
  1. FIREBASE_SA_JSON  (JSON 원문)
  2. FIREBASE_SA_PATH  (파일 경로)
  3. FIREBASE_SA_PARAM (SSM, AWS 만)

실제 firebase_admin 초기화는 건드리지 않는다 — 자격증명이 가짜라 그건 통합 테스트 영역.
이 테스트는 키 디스패치 로직만.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from sunity_shared import auth


SA_SAMPLE = {
    "type": "service_account",
    "project_id": "sunity-ai-coach-test",
    "private_key_id": "x",
    "private_key": "-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----\n",
    "client_email": "test@sunity-ai-coach-test.iam.gserviceaccount.com",
    "client_id": "0",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
}


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for k in ("FIREBASE_SA_JSON", "FIREBASE_SA_PATH", "FIREBASE_SA_PARAM"):
        monkeypatch.delenv(k, raising=False)
    yield


def test_inline_json_wins(monkeypatch):
    monkeypatch.setenv("FIREBASE_SA_JSON", json.dumps(SA_SAMPLE))
    monkeypatch.setenv("FIREBASE_SA_PATH", "/tmp/should-not-read.json")
    monkeypatch.setenv("FIREBASE_SA_PARAM", "/should/not/touch")

    out = auth._load_service_account_dict()

    assert out["project_id"] == "sunity-ai-coach-test"
    assert out["client_email"].endswith("iam.gserviceaccount.com")


def test_path_used_when_no_inline(monkeypatch, tmp_path: Path):
    sa_file = tmp_path / "firebase-sa.json"
    sa_file.write_text(json.dumps(SA_SAMPLE), encoding="utf-8")
    monkeypatch.setenv("FIREBASE_SA_PATH", str(sa_file))

    out = auth._load_service_account_dict()

    assert out == SA_SAMPLE


def test_missing_all_raises(monkeypatch):
    # 모든 변수 미설정 — 명확한 에러 (조용한 통과 금지).
    with pytest.raises(auth.AuthError) as exc:
        auth._load_service_account_dict()
    assert "FIREBASE_SA" in str(exc.value)


def test_param_path_attempts_ssm(monkeypatch):
    """SSM 폴백 경로가 호출되는지 검증 (실제 호출은 모킹)."""
    monkeypatch.setenv("FIREBASE_SA_PARAM", "/sunity/motion/firebase-sa")

    class FakeSSM:
        def __init__(self):
            self.called_with: dict | None = None

        def get_parameter(self, Name: str, WithDecryption: bool):
            self.called_with = {"Name": Name, "WithDecryption": WithDecryption}
            return {"Parameter": {"Value": json.dumps(SA_SAMPLE)}}

    fake = FakeSSM()

    class FakeBoto3:
        @staticmethod
        def client(name):
            assert name == "ssm"
            return fake

    monkeypatch.setitem(__import__("sys").modules, "boto3", FakeBoto3)

    out = auth._load_service_account_dict()

    assert fake.called_with == {
        "Name": "/sunity/motion/firebase-sa",
        "WithDecryption": True,
    }
    assert out["project_id"] == "sunity-ai-coach-test"
