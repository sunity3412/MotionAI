"""학습 페어 적재/소비 계약 테스트 — 담당 플랜 31-07.

실 S3/네트워크 미접촉 (LOCAL ONLY). in-memory FakeS3 는 조건부 PUT(IfNoneMatch)과
list 페이지네이션을 **실제로** 구현하므로, 멱등/재개/커밋마커 계약이 "통과하도록 짠
mock" 이 아니라 진짜 재현으로 검증된다.

고정하는 것 (리뷰 추적):
  · 동의 3분기 strict + 비통과 시 S3 호출 0 (D-01 / [[learning-consent-pilot-mandatory]])
  · 가명 pairId — key/meta 에 uid/analysisId 원문 부재 (H-04)
  · caller-fixed pairId + meta-read 멱등 / crash+rotation 중복 0 (5차 B5-03)
  · meta 부재 재개 시 412 payload hash 검증 후에만 resume (6차 H6-04)
  · commit marker 순서 + 부분 실패 3종 정리 (3차 H3-07)
  · payload 검증 consumer + quarantine + pagination (4차 H4-11 / 5차 H5-08 / M5-05)
  · strict HMAC key set validator 단일 출처 (3차 H3-11)
  · 배포 상수 vs belle 결정 JSON 대조, 런타임 결정파일 읽기 0 (M2-05 / 3차 M3-02)
"""

from __future__ import annotations

import base64
import hashlib
import inspect
import io
import json
from pathlib import Path

import pytest

from sunity_shared.analysis import pair_store

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DECISION_PATH = (
    _REPO_ROOT / ".planning" / "phases" / "31-api-visual-correction" / "smoke" / "privacy_decision.json"
)

_KEY_V1 = base64.b64encode(b"\x11" * 32).decode()
_KEY_V2 = base64.b64encode(b"\x22" * 32).decode()
_KEY_SET = {"active": "k2", "keys": {"k1": _KEY_V1, "k2": _KEY_V2}}

_BUCKET = "sunity-motion-pilot-videos"
_BEFORE = b"\x89PNG-before-bytes"
_AFTER = b"\x89PNG-after-bytes"
_QUALITY = {
    "model_id": "wan2.7-image-pro",
    "judge_confidence": 0.87,
    "pose_error_deg": 3.4,
    "source_generation": "gen-1",
    "provenance": {"generator": "wan2.7", "promptVersion": "v3"},
}


# ─────────────────────── in-memory S3 ───────────────────────


class FakeClientError(Exception):
    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.response = {
            "Error": {"Code": code},
            "ResponseMetadata": {"HTTPStatusCode": status},
        }


class FakeS3:
    """조건부 PUT + Delimiter listing + continuation token 을 실제로 구현한다."""

    def __init__(self, page_size: int = 1000) -> None:
        self.store: dict[str, bytes] = {}
        self.calls: list[tuple[str, str]] = []
        self.writes: list[str] = []
        self.page_size = page_size
        self.fail_puts: dict[str, Exception] = {}

    # ── 헬퍼 ──

    def seed(self, key: str, body: bytes) -> None:
        self.store[key] = body

    def put_keys(self) -> list[str]:
        """**실제로 기록된** object 만. 412 로 거절된 조건부 PUT 시도는 재기록이 아니다."""
        return list(self.writes)

    def reset_calls(self) -> None:
        self.calls.clear()
        self.writes.clear()

    # ── S3 API ──

    def put_object(self, *, Bucket, Key, Body, ContentType=None, IfNoneMatch=None):
        self.calls.append(("put", Key))
        if Key in self.fail_puts:
            raise self.fail_puts[Key]
        if IfNoneMatch == "*" and Key in self.store:
            raise FakeClientError("PreconditionFailed", 412)
        self.store[Key] = Body
        self.writes.append(Key)
        return {}

    def get_object(self, *, Bucket, Key):
        self.calls.append(("get", Key))
        if Key not in self.store:
            raise FakeClientError("NoSuchKey", 404)
        return {"Body": io.BytesIO(self.store[Key])}

    def head_object(self, *, Bucket, Key):
        self.calls.append(("head", Key))
        if Key not in self.store:
            raise FakeClientError("NotFound", 404)
        return {"ContentLength": len(self.store[Key])}

    def delete_object(self, *, Bucket, Key, VersionId=None):
        self.calls.append(("delete", Key))
        self.store.pop(Key, None)
        return {}

    def list_objects_v2(self, *, Bucket, Prefix="", Delimiter=None, ContinuationToken=None):
        self.calls.append(("list", Prefix))
        if Delimiter != "/":
            raise AssertionError("pair listing 은 Delimiter='/' 로 pair prefix 만 열거해야 한다")
        prefixes = sorted(
            {
                Prefix + key[len(Prefix):].split("/", 1)[0] + "/"
                for key in self.store
                if key.startswith(Prefix) and "/" in key[len(Prefix):]
            }
        )
        start = int(ContinuationToken or 0)
        page = prefixes[start:start + self.page_size]
        nxt = start + len(page)
        truncated = nxt < len(prefixes)
        out = {"CommonPrefixes": [{"Prefix": p} for p in page], "IsTruncated": truncated}
        if truncated:
            out["NextContinuationToken"] = str(nxt)
        return out


@pytest.fixture
def s3() -> FakeS3:
    return FakeS3()


def _pid(uid="uid-abc", analysis="an-123", joint="left_knee", version="k2") -> str:
    key_set = pair_store.validate_hmac_key_set(_KEY_SET)
    return pair_store.pair_id(uid, analysis, joint, hmac_key=key_set["keys"][version])


def _store(s3: FakeS3, *, pid=None, version="k2", joint="left_knee", before=_BEFORE, after=_AFTER,
           opt_in=True, quality=None) -> str:
    return pair_store.store_training_pair(
        s3,
        _BUCKET,
        pair_id=pid or _pid(joint=joint, version=version),
        hmac_key_version=version,
        joint=joint,
        before_png=before,
        after_png=after,
        learning_opt_in=opt_in,
        consent_captured_at_ms=1_784_000_000_000,
        quality=quality or _QUALITY,
    )


# ─────────────────────── 동의 게이트 (D-01) ───────────────────────


@pytest.mark.parametrize("opt_in", [False, None, "true", 1, {}])
def test_consent_not_true_skips_with_zero_s3_calls(s3, opt_in):
    """truthy 판정이면 "true"/1 이 통과한다 — is True strict 여야 S3 호출이 0 이다."""
    assert _store(s3, opt_in=opt_in) == "skipped_consent"
    assert s3.calls == []
    assert s3.store == {}


def test_consent_true_commits_marker_last(s3):
    """before → after → meta 순서. meta 가 마지막 commit marker 다 (H3-07)."""
    pid = _pid()
    assert _store(s3, pid=pid) == "committed"
    assert s3.put_keys() == [
        f"training/phase31/pairs/{pid}/before.png",
        f"training/phase31/pairs/{pid}/after.png",
        f"training/phase31/pairs/{pid}/meta.json",
    ]


# ─────────────────────── 가명화 (H-04 / H2-06) ───────────────────────


def test_pair_id_is_hmac_pseudonym_without_raw_identifiers(s3):
    pid = _pid(uid="uid-abc", analysis="an-123")
    _store(s3, pid=pid)
    meta_raw = s3.store[f"training/phase31/pairs/{pid}/meta.json"].decode()
    meta = json.loads(meta_raw)

    assert pid == pair_store.pair_id(
        "uid-abc", "an-123", "left_knee",
        hmac_key=pair_store.validate_hmac_key_set(_KEY_SET)["keys"]["k2"],
    )
    for key in s3.store:
        assert "uid-abc" not in key and "an-123" not in key
    assert "uid-abc" not in meta_raw and "an-123" not in meta_raw
    assert meta["hmacKeyVersion"] == "k2"
    assert meta["beforeSha256"] == hashlib.sha256(_BEFORE).hexdigest()
    assert meta["afterSha256"] == hashlib.sha256(_AFTER).hexdigest()
    assert meta["blurApplied"] is False


def test_pair_id_differs_per_key_version():
    """키가 회전되면 같은 입력도 다른 pairId — 삭제는 전 버전을 재계산해야 한다."""
    assert _pid(version="k1") != _pid(version="k2")


def test_pair_id_rejects_wrong_key_length():
    with pytest.raises(ValueError):
        pair_store.pair_id("u", "a", "left_knee", hmac_key=b"\x00" * 31)


# ─────────────────────── meta-read 멱등 (5차 B5-03) ───────────────────────


def test_repeat_call_with_matching_meta_puts_nothing(s3):
    pid = _pid()
    assert _store(s3, pid=pid) == "committed"
    s3.reset_calls()
    assert _store(s3, pid=pid) == "committed"
    assert s3.put_keys() == []


def test_existing_meta_with_different_payload_is_conflict_not_overwrite(s3):
    pid = _pid()
    _store(s3, pid=pid)
    original = dict(s3.store)
    s3.reset_calls()

    assert _store(s3, pid=pid, before=b"different-before") == "conflict"
    assert s3.put_keys() == []
    assert s3.store == original


def test_crash_then_key_rotation_does_not_duplicate(s3):
    """postprocess crash 후 재시도 중 active 키가 k1→k2 로 회전해도 페어는 1개.

    caller 가 진입 시 고정한 pairId(k1 기준)를 그대로 재전달하므로, 적재 함수가 내부에서
    active 키를 다시 고르지 않는 한 재PUT 은 0 이다.
    """
    pid_v1 = _pid(version="k1")
    assert _store(s3, pid=pid_v1, version="k1") == "committed"
    s3.reset_calls()

    assert _store(s3, pid=pid_v1, version="k1") == "committed"
    assert s3.put_keys() == []
    pair_prefixes = {key.rsplit("/", 1)[0] for key in s3.store}
    assert len(pair_prefixes) == 1


def test_store_does_not_reselect_active_key(s3):
    """B5-03 구조 강제 — 적재 함수 본문에 key set 로드/active 선택이 없어야 한다."""
    src = inspect.getsource(pair_store.store_training_pair)
    body = src.split('"""')[2]  # signature / docstring / 본문
    code = "\n".join(line for line in body.splitlines() if not line.strip().startswith("#"))
    assert "load_hmac_key_set" not in code
    assert "active" not in code


# ─────────────────────── partial 재개 payload 검증 (6차 H6-04) ───────────────────────


def test_resume_when_preexisting_before_matches_expected_hash(s3):
    """before-only crash 재개 — hash 일치면 재PUT 없이 after/meta 만 쓴다."""
    pid = _pid()
    s3.seed(f"training/phase31/pairs/{pid}/before.png", _BEFORE)
    s3.reset_calls()

    assert _store(s3, pid=pid) == "committed"
    assert s3.put_keys() == [
        f"training/phase31/pairs/{pid}/after.png",
        f"training/phase31/pairs/{pid}/meta.json",
    ]


def test_tampered_preexisting_before_is_conflict_and_writes_no_marker(s3):
    """변조된 before 가 조용히 학습쌍으로 커밋되면 안 된다 — marker 미기록."""
    pid = _pid()
    s3.seed(f"training/phase31/pairs/{pid}/before.png", b"tampered-payload")
    s3.reset_calls()

    assert _store(s3, pid=pid) == "conflict"
    assert f"training/phase31/pairs/{pid}/meta.json" not in s3.store
    assert f"training/phase31/pairs/{pid}/after.png" not in s3.store


def test_same_size_but_different_bytes_is_caught_by_hash(s3):
    """HEAD size 만 보면 통과한다 — GET sha256 까지 봐야 잡힌다."""
    pid = _pid()
    s3.seed(f"training/phase31/pairs/{pid}/before.png", b"X" * len(_BEFORE))

    assert _store(s3, pid=pid) == "conflict"
    assert f"training/phase31/pairs/{pid}/meta.json" not in s3.store


def test_resume_when_before_and_after_both_match(s3):
    """after-only crash 재개 — 두 payload 다 일치면 marker 만 쓴다."""
    pid = _pid()
    s3.seed(f"training/phase31/pairs/{pid}/before.png", _BEFORE)
    s3.seed(f"training/phase31/pairs/{pid}/after.png", _AFTER)
    s3.reset_calls()

    assert _store(s3, pid=pid) == "committed"
    assert s3.put_keys() == [f"training/phase31/pairs/{pid}/meta.json"]


# ─────────────────────── 부분 실패 정리 (3차 H3-07) ───────────────────────


def test_first_put_failure_leaves_no_object(s3):
    pid = _pid()
    s3.fail_puts[f"training/phase31/pairs/{pid}/before.png"] = RuntimeError("boom")

    assert _store(s3, pid=pid) == "failed"
    assert s3.store == {}


def test_second_put_failure_removes_before(s3):
    pid = _pid()
    s3.fail_puts[f"training/phase31/pairs/{pid}/after.png"] = RuntimeError("boom")

    assert _store(s3, pid=pid) == "failed"
    assert s3.store == {}
    assert ("delete", f"training/phase31/pairs/{pid}/before.png") in s3.calls


def test_marker_put_failure_removes_before_and_after(s3):
    pid = _pid()
    s3.fail_puts[f"training/phase31/pairs/{pid}/meta.json"] = RuntimeError("boom")

    assert _store(s3, pid=pid) == "failed"
    assert s3.store == {}
    deleted = {key for op, key in s3.calls if op == "delete"}
    assert deleted == {
        f"training/phase31/pairs/{pid}/before.png",
        f"training/phase31/pairs/{pid}/after.png",
    }


# ─────────────────────── HMAC validator (3차 H3-11) ───────────────────────


def test_validator_accepts_deployed_schema():
    result = pair_store.validate_hmac_key_set(_KEY_SET)
    assert result["active"] == "k2"
    assert set(result["keys"]) == {"k1", "k2"}
    assert all(len(v) == 32 for v in result["keys"].values())


def test_validator_accepts_hex_key_material():
    hex_key = ("ab" * 32)
    result = pair_store.validate_hmac_key_set({"active": "v1", "keys": {"v1": hex_key}})
    assert result["keys"]["v1"] == bytes.fromhex(hex_key)


@pytest.mark.parametrize(
    "bad",
    [
        None,
        "not-a-dict",
        {},
        {"active": "k1"},
        {"keys": {"k1": _KEY_V1}},
        {"active": "k1", "keys": {"k1": _KEY_V1}, "extra": 1},          # unknown top-level key
        {"active": "k9", "keys": {"k1": _KEY_V1}},                       # active not in keys
        {"active": "k1", "keys": {}},                                    # empty key set
        {"active": "k1", "keys": {"k1": "!!!not-base64!!!"}},            # 비-디코딩
        {"active": "k1", "keys": {"k1": base64.b64encode(b"\x11" * 31).decode()}},
        {"active": "k1", "keys": {"k1": base64.b64encode(b"\x11" * 33).decode()}},
        {"active": "k1", "keys": {"bad/version": _KEY_V1}},              # 경로 문자 버전 ID
        {"active": "k1", "keys": {"k1": 12345}},                         # 비-문자열 키
    ],
)
def test_validator_rejects_malformed_key_sets(bad):
    assert pair_store.validate_hmac_key_set(bad) is None


def test_missing_env_key_set_is_fail_closed(monkeypatch):
    monkeypatch.delenv(pair_store.HMAC_KEYS_ENV, raising=False)
    assert pair_store.load_hmac_key_set() is None


def test_env_key_set_roundtrip_and_invalid_json(monkeypatch):
    monkeypatch.setenv(pair_store.HMAC_KEYS_ENV, json.dumps(_KEY_SET))
    assert pair_store.load_hmac_key_set()["active"] == "k2"
    monkeypatch.setenv(pair_store.HMAC_KEYS_ENV, "{not json")
    assert pair_store.load_hmac_key_set() is None


def test_unregistered_joint_is_rejected(s3):
    with pytest.raises(ValueError):
        _store(s3, pid=_pid(), joint="left_shoulder")
    assert s3.calls == []


# ─────────────────────── consumer helper (4차 H4-11 / 5차 H5-08) ───────────────────────


def test_list_committed_pairs_returns_only_verified(s3):
    healthy = _pid(analysis="an-ok")
    _store(s3, pid=healthy)
    assert pair_store.list_committed_pairs(s3, _BUCKET)["pairs"][0]["pair_id"] == healthy


def test_missing_payload_goes_to_quarantine(s3):
    pid = _pid(analysis="an-missing")
    _store(s3, pid=pid)
    del s3.store[f"training/phase31/pairs/{pid}/before.png"]

    result = pair_store.list_committed_pairs(s3, _BUCKET)
    assert result["pairs"] == []
    assert result["quarantine"] == [{"pair_id": pid, "reason": "before_missing"}]
    assert pair_store.load_committed_pair(s3, _BUCKET, pid) is None


def test_tampered_payload_goes_to_quarantine(s3):
    pid = _pid(analysis="an-tampered")
    _store(s3, pid=pid)
    s3.store[f"training/phase31/pairs/{pid}/after.png"] = b"Y" * len(_AFTER)

    result = pair_store.list_committed_pairs(s3, _BUCKET)
    assert result["pairs"] == []
    assert result["quarantine"][0]["reason"] == "after_hash_mismatch"


def test_uncommitted_prefix_without_marker_is_excluded(s3):
    """marker 없는 부분 적재물은 학습에 소비되지 않는다."""
    pid = _pid(analysis="an-partial")
    s3.seed(f"training/phase31/pairs/{pid}/before.png", _BEFORE)

    result = pair_store.list_committed_pairs(s3, _BUCKET)
    assert result["pairs"] == []
    assert result["quarantine"][0]["reason"] == "meta_invalid_or_missing"


def test_listing_walks_continuation_token_to_the_end(s3):
    """1,000 초과 페어에서 첫 페이지만 읽으면 학습셋이 조용히 잘린다 (M5-05)."""
    s3.page_size = 250
    expected = set()
    for i in range(1200):
        pid = _pid(analysis=f"an-{i}")
        expected.add(pid)
        s3.seed(f"training/phase31/pairs/{pid}/before.png", _BEFORE)

    assert set(pair_store.iter_pair_prefixes(s3, _BUCKET)) == expected
    assert len(expected) == 1200


def test_list_committed_pairs_across_pages(s3):
    s3.page_size = 100
    committed = set()
    for i in range(220):
        pid = _pid(analysis=f"an-page-{i}")
        committed.add(pid)
        _store(s3, pid=pid)

    result = pair_store.list_committed_pairs(s3, _BUCKET)
    assert {p["pair_id"] for p in result["pairs"]} == committed
    assert result["quarantine"] == []


# ─────────────────────── 배포 상수 대조 (M2-05 / 3차 M3-02) ───────────────────────


def _decision() -> dict:
    return json.loads(_DECISION_PATH.read_text(encoding="utf-8"))


def test_deployed_constants_match_belle_decision():
    decision = _decision()
    assert pair_store.CONSENT_VERSION == decision["consentVersion"]
    assert pair_store.BLUR_OPTION == decision["blurOption"]
    assert pair_store.RETENTION_DAYS == decision["retentionDays"]


def test_retention_is_our_deletion_sla_not_vendor_retention():
    """벤더 보존 일수는 미공개다 — 코드가 숫자를 지어내면 고지가 거짓이 된다."""
    decision = _decision()
    assert decision["vendorRetention"]["retentionDays"] is None
    assert decision["retentionDaysScope"] == "sunity_training_pairs_only"


def test_source_has_no_runtime_decision_file_read_and_no_blur_code():
    src = Path(pair_store.__file__).read_text(encoding="utf-8")
    assert ".planning" not in src
    assert "ultralytics" not in src
    assert "import anonymize" not in src and "from anonymize" not in src
    # option-a — blur 실행 분기가 존재하면 안 된다 (H2-10).
    assert "pod_blur" not in src.replace(
        "BLUR_OPTION = \"none\"  # belle option-a. 'pod_blur' 분기는 채택되지 않아 구현하지 않는다.", ""
    )


def test_source_never_calls_s3_versioning_api():
    """Never-versioned 상태는 31-12 hard gate — 버킷 versioning 을 만지지 않는다."""
    src = Path(pair_store.__file__).read_text(encoding="utf-8")
    assert "put_bucket_versioning" not in src
    assert "get_bucket_versioning" not in src


def test_historical_registry_covers_render_contract():
    """렌더 계약이 축소돼도 과거 페어를 삭제할 수 있어야 한다 (M3-05)."""
    from sunity_shared.analysis import fault_zoom

    assert set(fault_zoom.ARROW_JOINT_MAP) <= set(pair_store.HISTORICAL_PAIR_JOINTS)
    assert set(fault_zoom.HISTORICAL_JOINT_REGISTRY) <= set(pair_store.HISTORICAL_PAIR_JOINTS)


def test_scaffold_fake_clock_alive(fake_clock):
    """공용 스캐폴드(주입 시계)가 살아 있는지 — 31-02 골격 계약 유지."""
    start = fake_clock()
    assert fake_clock.advance(1000) == start + 1000
