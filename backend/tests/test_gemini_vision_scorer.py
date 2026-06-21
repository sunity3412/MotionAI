"""Plan 20-02 — gemini_vision_scorer 어댑터 단위 테스트 (mocked-Gemini, pod-free).

전부 mock — google.genai / boto3 / RTMW 실 호출 0. 실 Gemini API/Pod 무관.

박제 정신 (20-02-PLAN must_haves / 20-CONTEXT D-02/D-06):
  · MEDIUM-1 (객관성 hard gate): build_schema()/dataclass 내성검사(introspection)로
    score/overall/rating/점수 0. raw grep 아님. spike 의 overall_qualitative 복사 금지.
  · MEDIUM-2 (결정론): temp 0 + 전용 VisionVetoCache 키
    (video_hash, model, PROMPT_VERSION, SCHEMA_VERSION, input_granularity, at_seconds_bucket).
    PROMPT_VERSION/SCHEMA_VERSION 변경 시 stale verdict 무효화.
  · iter2 MEDIUM-1 (adapter-boundary): 어댑터 토글 미소유 —
    backend.functions.pipeline import 0 + _gemini_vision_veto_enabled 정의 0 +
    GEMINI_VISION_VETO_ENABLED env 미참조.
  · B4: caller local_video_path 만 사용 — S3 재다운로드/RTMW 재실행 0.
  · Pitfall 5: 키 부재/API 실패 → verdict=None + WARNING (raise 0).
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sunity_shared.analysis import gemini_vision_scorer as gvs
from sunity_shared.analysis.gemini_vision_scorer import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    VisionVerdict,
    VisionVetoCache,
    assess_fault_severity,
    build_schema,
)

# ─────────────────── 객관성 내성검사 (MEDIUM-1) ───────────────────

_FORBIDDEN_KEYS = {"score", "overall", "rating", "점수"}


def _walk_property_keys(schema: dict) -> set[str]:
    """build_schema() 의 모든 properties 키 (중첩 properties 재귀 포함)."""
    keys: set[str] = set()

    def _recurse(node: object) -> None:
        if not isinstance(node, dict):
            return
        props = node.get("properties")
        if isinstance(props, dict):
            for k, v in props.items():
                keys.add(k)
                _recurse(v)
        items = node.get("items")
        if isinstance(items, dict):
            _recurse(items)

    _recurse(schema)
    return keys


def test_schema_introspection_has_no_score_field():
    """build_schema()['properties'] (중첩 재귀) 에 forbidden {score,overall,rating,점수} 0."""
    keys = _walk_property_keys(build_schema())
    for forbidden in _FORBIDDEN_KEYS:
        for key in keys:
            assert forbidden not in key.lower(), (
                f"객관성 위반 — schema property '{key}' 에 forbidden '{forbidden}' 포함"
            )
    # severity enum + primary_fault 는 존재해야
    assert "primary_fault" in keys
    assert "severity" in keys


def test_no_overall_qualitative_copied():
    """spike 의 overall_qualitative(217) 를 production 스키마에 복사 금지 (strict no-overall)."""
    keys = _walk_property_keys(build_schema())
    assert "overall_qualitative" not in keys
    assert "overall" not in keys


def test_verdict_dataclass_fields_exact():
    """VisionVerdict 필드 = {primary_fault, severity, differences} 정확 (초과/score 0)."""
    field_names = {f.name for f in dataclasses.fields(VisionVerdict)}
    assert field_names == {"primary_fault", "severity", "differences"}, field_names
    # score 속성 부재
    v = VisionVerdict(primary_fault="x", severity="major", differences=())
    assert not hasattr(v, "score")


# ─────────────────── _SCORE_PATTERN 누출 가드 ───────────────────


@pytest.mark.parametrize("leak", ["85점", "85/100", "85%", "100/100"])
def test_score_pattern_rejects_leak(leak):
    """응답 텍스트에 NN점/NN/100/NN% 누출 시 _SCORE_PATTERN.search 가 매칭."""
    assert gvs._SCORE_PATTERN.search(leak) is not None


# ─────────────────── 테스트 헬퍼 — fake Gemini client ───────────────────


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text


class _FakeModels:
    def __init__(self, parent):
        self._parent = parent

    def generate_content(self, *, model, contents, config):
        self._parent.calls.append(
            {"model": model, "config": config, "contents": contents}
        )
        return _FakeResponse(self._parent.response_text)


class _FakeFiles:
    def upload(self, *, file, config):
        return MagicMock(name="uploaded", state=MagicMock(name="ACTIVE"))

    def get(self, *, name):
        return MagicMock(name="active", state="ACTIVE")


class _FakeClient:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.calls: list[dict] = []
        self.models = _FakeModels(self)
        self.files = _FakeFiles()


_VALID_JSON = (
    '{"motion": "kip-up", "primary_fault": "다리 신전 붕괴", '
    '"differences": [{"body_part": "무릎", "correct_state": "신전", '
    '"fault_state": "굽음", "severity": "major", "ipsf_note": "신전 deficit"}]}'
)


@pytest.fixture
def fake_video(tmp_path):
    p = tmp_path / "input.mp4"
    p.write_bytes(b"\x00\x01\x02fake-video-bytes")
    return str(p)


def _patch_client(monkeypatch, client):
    """_ensure_client 가 fake client 를 반환하도록 + upload_and_wait noop."""
    monkeypatch.setattr(gvs, "_ensure_client", lambda: client)
    monkeypatch.setattr(gvs, "_upload_video", lambda c, path, hint: MagicMock())


def _in_memory_cache(monkeypatch):
    """VisionVetoCache 의 Firestore I/O 를 in-memory dict 로 대체."""
    store: dict[str, dict] = {}

    def _get(self, key):
        return store.get(key)

    def _put(self, key, payload):
        store[key] = payload

    monkeypatch.setattr(VisionVetoCache, "_backend_get", _get, raising=False)
    monkeypatch.setattr(VisionVetoCache, "_backend_put", _put, raising=False)
    return store


# ─────────────────── 어댑터 동작 ───────────────────


def test_assess_returns_severity_enum(monkeypatch, fake_video):
    """mocked Gemini JSON → VisionVerdict.severity ∈ {minor,moderate,major}, score 부재."""
    _in_memory_cache(monkeypatch)
    client = _FakeClient(_VALID_JSON)
    _patch_client(monkeypatch, client)

    verdict = assess_fault_severity(fake_video)
    assert verdict is not None
    assert verdict.severity in {"none", "minor", "moderate", "major"}
    assert not hasattr(verdict, "score")
    assert getattr(verdict, "score", None) is None


_CLEAN_JSON = (
    '{"motion": "kip-up", "dominant_severity": "none", '
    '"primary_fault": "없음", "differences": []}'
)


def test_clean_form_reports_none_no_cap(monkeypatch, fake_video):
    """정타(dominant_severity none + 빈 differences) → severity 'none' → cap 미적용.

    over-penalization fix (2026-06-20): 정은지 정타가 major 로 스탬프돼 50 으로 깎이던
    버그의 회귀 가드. clean form 은 점수를 깎지 않는다.
    """
    from sunity_shared.analysis import vision_veto

    _in_memory_cache(monkeypatch)
    client = _FakeClient(_CLEAN_JSON)
    _patch_client(monkeypatch, client)

    verdict = assess_fault_severity(fake_video)
    assert verdict is not None
    assert verdict.severity == "none"
    # apply_downward_cap 은 'none' 에서 점수 불변 (정타 95~100 보존, D-01).
    assert vision_veto.apply_downward_cap(100, verdict.severity) == 100
    assert vision_veto.apply_downward_cap(97, verdict.severity) == 97


def test_determinism_cache_same_key(monkeypatch, fake_video):
    """같은 키 2회 → Gemini 1회(2번째 캐시) + verdict 동일 + temperature=0.0."""
    _in_memory_cache(monkeypatch)
    client = _FakeClient(_VALID_JSON)
    _patch_client(monkeypatch, client)

    v1 = assess_fault_severity(fake_video)
    v2 = assess_fault_severity(fake_video)
    assert v1 == v2
    assert len(client.calls) == 1, "2번째 호출은 캐시 hit — Gemini 재호출 0"
    # temperature=0.0 호출 인자 단언
    config = client.calls[0]["config"]
    assert getattr(config, "temperature", None) == 0.0


def test_prompt_version_invalidates_cache(monkeypatch, fake_video):
    """PROMPT_VERSION 변경 시 같은 video_hash 라도 cache miss → Gemini 재호출 (MEDIUM-2)."""
    _in_memory_cache(monkeypatch)
    client = _FakeClient(_VALID_JSON)
    _patch_client(monkeypatch, client)

    assess_fault_severity(fake_video)
    assert len(client.calls) == 1

    monkeypatch.setattr(gvs, "PROMPT_VERSION", "v-bumped-999")
    assess_fault_severity(fake_video)
    assert len(client.calls) == 2, "PROMPT_VERSION bump → stale 무효화 + 재호출"


def test_cache_key_includes_input_granularity():
    """VisionVetoCache 캐시 키에 input_granularity 마커 포함 (iter2 non-blocking)."""
    key = VisionVetoCache.build_key(
        video_hash="abc123",
        model_name="gemini-3.1-pro-preview",
        input_granularity="whole",
        at_seconds=None,
    )
    assert "whole" in key
    # frame-input 키와 충돌 0
    key_frame = VisionVetoCache.build_key(
        video_hash="abc123",
        model_name="gemini-3.1-pro-preview",
        input_granularity="frame",
        at_seconds=None,
    )
    assert key != key_frame
    # PROMPT_VERSION/SCHEMA_VERSION 도 키에 포함
    assert PROMPT_VERSION in key
    assert SCHEMA_VERSION in key


def test_graceful_no_key(monkeypatch, fake_video, caplog):
    """키 부재/client 생성 실패 → None 반환(raise 0) + WARNING 로그."""
    _in_memory_cache(monkeypatch)

    def _raise():
        raise RuntimeError("Gemini API 키 없음")

    monkeypatch.setattr(gvs, "_ensure_client", _raise)

    import logging

    with caplog.at_level(logging.WARNING):
        verdict = assess_fault_severity(fake_video)
    assert verdict is None
    assert any(r.levelno >= logging.WARNING for r in caplog.records)


def test_no_video_redownload(monkeypatch, fake_video):
    """어댑터가 caller local_video_path 만 사용 — S3 download/RTMW 재실행 0."""
    _in_memory_cache(monkeypatch)
    client = _FakeClient(_VALID_JSON)
    _patch_client(monkeypatch, client)

    # boto3 가 import 되더라도 client/download 가 호출되면 실패시킴
    import sys
    import types

    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.client = MagicMock(
        side_effect=AssertionError("어댑터가 boto3.client 호출 — B4 위반")
    )
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    verdict = assess_fault_severity(fake_video)
    assert verdict is not None
    fake_boto3.client.assert_not_called()


def test_score_pattern_rejects_leak_in_response(monkeypatch, fake_video, caplog):
    """응답 raw_text 에 점수 누출 시 어댑터가 verdict 거부(None) + WARNING."""
    _in_memory_cache(monkeypatch)
    leaky = (
        '{"motion": "kip-up", "primary_fault": "85점 수준의 자세", '
        '"differences": [{"body_part": "무릎", "correct_state": "신전", '
        '"fault_state": "굽음", "severity": "major"}]}'
    )
    client = _FakeClient(leaky)
    _patch_client(monkeypatch, client)

    import logging

    with caplog.at_level(logging.WARNING):
        verdict = assess_fault_severity(fake_video)
    assert verdict is None, "점수 누출 응답은 객관성 위반 — verdict 폐기"
    assert any(r.levelno >= logging.WARNING for r in caplog.records)


# ─────────────────── adapter-boundary (iter2 MEDIUM-1) ───────────────────


def test_adapter_does_not_own_toggle(monkeypatch, fake_video):
    """(a) 모듈 소스에 pipeline import 0 + _gemini_vision_veto_enabled 정의 0.
    (b) GEMINI_VISION_VETO_ENABLED env 미참조 — OFF/unset 에서도 동작."""
    source = Path(inspect.getfile(gvs)).read_text(encoding="utf-8")

    # (a) raw 소스 검사 + AST 검사
    assert "backend.functions.pipeline" not in source
    assert "from backend.functions.pipeline" not in source
    assert "_gemini_vision_veto_enabled" not in source
    assert "GEMINI_VISION_VETO_ENABLED" not in source

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            assert node.name != "_gemini_vision_veto_enabled", "토글 정의 금지"
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("backend.functions.pipeline"), (
                "pipeline 역방향 import 금지"
            )

    # (b) 토글 env OFF/unset 이어도 키/캐시만으로 동작
    _in_memory_cache(monkeypatch)
    monkeypatch.delenv("GEMINI_VISION_VETO_ENABLED", raising=False)
    client = _FakeClient(_VALID_JSON)
    _patch_client(monkeypatch, client)
    verdict = assess_fault_severity(fake_video)
    assert verdict is not None, "토글 미참조 — 어댑터-local 전제조건만으로 동작"


# ─────────────────── reference-anchored 비교 모드 (v4.0, Mode1) ───────────────────


@pytest.fixture
def fake_reference_video(tmp_path):
    p = tmp_path / "reference.mp4"
    p.write_bytes(b"\x00\x09\x08reference-video-bytes")
    return str(p)


def _patch_client_with_upload_spy(monkeypatch, client):
    """_ensure_client → fake + _upload_video 가 업로드 path 를 기록 (비교 시 2회)."""
    uploads: list[str] = []

    def _spy_upload(c, path, hint):
        uploads.append(path)
        return MagicMock(name=f"uploaded-{len(uploads)}")

    monkeypatch.setattr(gvs, "_ensure_client", lambda: client)
    monkeypatch.setattr(gvs, "_upload_video", _spy_upload)
    return uploads


def test_comparison_mode_uploads_both_and_parses_severity(
    monkeypatch, fake_video, fake_reference_video
):
    """reference_video_path 제공 → 두 영상 모두 업로드 + 비교 응답에서 severity 파싱.

    belle 2026-06-20 — Mode1 reference-anchored 비교. 기준(정타) 영상 먼저, 학생 둘째.
    """
    _in_memory_cache(monkeypatch)
    client = _FakeClient(_VALID_JSON)
    uploads = _patch_client_with_upload_spy(monkeypatch, client)

    verdict = assess_fault_severity(
        fake_video, reference_video_path=fake_reference_video
    )
    assert verdict is not None
    assert verdict.severity in {"none", "minor", "moderate", "major"}
    # 두 영상 모두 업로드 (기준 먼저, 학생 둘째 — _call_gemini_comparison 순서).
    assert len(uploads) == 2
    assert fake_reference_video in uploads
    assert fake_video in uploads
    # generate_content 호출 contents 에 기준/학생 라벨 둘 다 포함 (비교 경로 증명).
    config_call = client.calls[-1]
    contents = config_call["contents"]
    joined = " ".join(c for c in contents if isinstance(c, str))
    assert "기준" in joined and "학생" in joined


def test_comparison_cache_key_includes_reference_hash(
    monkeypatch, fake_video, fake_reference_video, tmp_path
):
    """다른 기준 영상 → 다른 캐시 키 (pair keying). 같은 학생, reference 만 교체."""
    store = _in_memory_cache(monkeypatch)
    client = _FakeClient(_VALID_JSON)
    _patch_client_with_upload_spy(monkeypatch, client)

    # 기준 A 로 1회.
    assess_fault_severity(fake_video, reference_video_path=fake_reference_video)
    assert len(store) == 1
    key_a = next(iter(store))

    # 기준 B (다른 바이트) 로 1회 — 같은 학생이지만 reference_hash 가 달라 새 키.
    ref_b = tmp_path / "reference_b.mp4"
    ref_b.write_bytes(b"\x05\x05\x05different-reference-bytes")
    assess_fault_severity(fake_video, reference_video_path=str(ref_b))
    assert len(store) == 2, "다른 기준 영상 → 새 캐시 키 (pair keying, reference_hash 반영)"
    key_b = [k for k in store if k != key_a][0]
    assert key_a != key_b


def test_comparison_key_differs_from_single_video_key(
    monkeypatch, fake_video, fake_reference_video
):
    """비교(reference 포함) 키 ≠ 단일 영상(reference None 'noref') 키 — 경로 격리."""
    store = _in_memory_cache(monkeypatch)
    client = _FakeClient(_VALID_JSON)
    _patch_client_with_upload_spy(monkeypatch, client)

    assess_fault_severity(fake_video)  # 단일 영상 (noref)
    assess_fault_severity(fake_video, reference_video_path=fake_reference_video)
    assert len(store) == 2, "단일 영상 verdict 와 비교 verdict 는 키 충돌 0"


def test_single_video_signature_back_compat(monkeypatch, fake_video):
    """reference_video_path 기본 None — 기존 단일 영상 시그니처 호환 (Mode3 보류 경로 보존)."""
    _in_memory_cache(monkeypatch)
    client = _FakeClient(_VALID_JSON)
    uploads = _patch_client_with_upload_spy(monkeypatch, client)

    verdict = assess_fault_severity(fake_video)  # reference 미전달
    assert verdict is not None
    assert len(uploads) == 1, "단일 영상 경로는 1회 업로드만 (비교 아님)"


# ─────────────────── 비교 multi-sample 집계 (Phase 20 robustify) ───────────────────


def _sev_json(severity: str, fault: str = "다리 신전 부족") -> str:
    """dominant_severity + primary_fault 만 있는 비교 응답 JSON."""
    return (
        '{"motion": "kip-up", "dominant_severity": "%s", '
        '"primary_fault": "%s", "differences": []}' % (severity, fault)
    )


class _SeqModels:
    """generate_content 가 호출마다 다음 응답을 순차 반환 (multi-sample 시뮬)."""

    def __init__(self, parent):
        self._parent = parent

    def generate_content(self, *, model, contents, config):
        self._parent.calls.append(
            {"model": model, "config": config, "contents": contents}
        )
        idx = len(self._parent.calls) - 1
        seq = self._parent.responses
        text = seq[idx] if idx < len(seq) else seq[-1]
        return _FakeResponse(text)


class _SeqClient:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.calls: list[dict] = []
        self.models = _SeqModels(self)
        self.files = _FakeFiles()


def _patch_seq_client(monkeypatch, client):
    """_SeqClient + 업로드 spy (비교 시 영상당 1회만 업로드 검증용)."""
    uploads: list[str] = []

    def _spy_upload(c, path, hint):
        uploads.append(path)
        return MagicMock(name=f"uploaded-{len(uploads)}")

    monkeypatch.setattr(gvs, "_ensure_client", lambda: client)
    monkeypatch.setattr(gvs, "_upload_video", _spy_upload)
    return uploads


def test_comparison_median_moderate(monkeypatch, fake_video, fake_reference_video):
    """[moderate, moderate, moderate] 단순 다수 → median moderate. 업로드 1회/영상."""
    _in_memory_cache(monkeypatch)
    monkeypatch.setattr(gvs, "VISION_VETO_SAMPLES", 3)
    client = _SeqClient(
        [_sev_json("moderate"), _sev_json("moderate"), _sev_json("minor")]
    )
    uploads = _patch_seq_client(monkeypatch, client)

    verdict = assess_fault_severity(
        fake_video, reference_video_path=fake_reference_video
    )
    assert verdict is not None
    # rank-median([moderate=2, moderate=2, minor=1] sorted=[1,2,2], idx=1) → moderate.
    assert verdict.severity == "moderate"
    # 업로드는 영상당 1회만 (핸들 재사용) — N 회 generateContent 만 반복.
    assert len(uploads) == 2, "비교 = ref+student 각 1회 업로드 (재업로드 0)"
    assert len(client.calls) == 3, "N=3 generateContent (샘플마다 1회)"


def test_comparison_median_minor(monkeypatch, fake_video, fake_reference_video):
    """[minor, minor, moderate] → rank-median minor (단일 라벨 흔들림 제거)."""
    _in_memory_cache(monkeypatch)
    monkeypatch.setattr(gvs, "VISION_VETO_SAMPLES", 3)
    client = _SeqClient(
        [_sev_json("minor"), _sev_json("minor"), _sev_json("moderate")]
    )
    _patch_seq_client(monkeypatch, client)

    verdict = assess_fault_severity(
        fake_video, reference_video_path=fake_reference_video
    )
    assert verdict is not None
    # sorted ranks=[1,1,2], idx=1 → minor.
    assert verdict.severity == "minor"
    assert len(client.calls) == 3


def test_comparison_skips_none_parse_sample(
    monkeypatch, fake_video, fake_reference_video
):
    """파싱 실패(None) 샘플은 집계에서 제외 — 남은 [moderate, moderate] median moderate."""
    _in_memory_cache(monkeypatch)
    monkeypatch.setattr(gvs, "VISION_VETO_SAMPLES", 3)
    client = _SeqClient(
        ["this is not json at all", _sev_json("moderate"), _sev_json("moderate")]
    )
    _patch_seq_client(monkeypatch, client)

    verdict = assess_fault_severity(
        fake_video, reference_video_path=fake_reference_video
    )
    assert verdict is not None
    # None-parse 1개 제외 → [moderate, moderate] sorted=[2,2], idx=0 → moderate.
    assert verdict.severity == "moderate"
    assert len(client.calls) == 3, "N=3 호출은 모두 시도 (파싱 실패도 호출은 발생)"


def test_comparison_all_none_parse_returns_none(
    monkeypatch, fake_video, fake_reference_video
):
    """모든 샘플 파싱 실패 → verdict None (graceful)."""
    _in_memory_cache(monkeypatch)
    monkeypatch.setattr(gvs, "VISION_VETO_SAMPLES", 3)
    client = _SeqClient(["bad", "also bad", "still bad"])
    _patch_seq_client(monkeypatch, client)

    verdict = assess_fault_severity(
        fake_video, reference_video_path=fake_reference_video
    )
    assert verdict is None


def test_comparison_even_count_lower_middle(
    monkeypatch, fake_video, fake_reference_video
):
    """짝수 개수 → lower-middle 인덱스(보수적). [minor, moderate] → minor."""
    _in_memory_cache(monkeypatch)
    monkeypatch.setattr(gvs, "VISION_VETO_SAMPLES", 2)
    client = _SeqClient([_sev_json("minor"), _sev_json("moderate")])
    _patch_seq_client(monkeypatch, client)

    verdict = assess_fault_severity(
        fake_video, reference_video_path=fake_reference_video
    )
    assert verdict is not None
    # sorted=[1,2], (2-1)//2=0 → idx 0 → minor (lower-middle, 보수적).
    assert verdict.severity == "minor"


def test_comparison_aggregated_verdict_cached(
    monkeypatch, fake_video, fake_reference_video
):
    """집계 verdict 가 캐시됨 — 2번째 호출은 cache hit (재샘플링 0)."""
    store = _in_memory_cache(monkeypatch)
    monkeypatch.setattr(gvs, "VISION_VETO_SAMPLES", 3)
    client = _SeqClient(
        [_sev_json("moderate"), _sev_json("moderate"), _sev_json("minor")]
    )
    _patch_seq_client(monkeypatch, client)

    v1 = assess_fault_severity(fake_video, reference_video_path=fake_reference_video)
    assert len(client.calls) == 3
    assert len(store) == 1, "집계 verdict 1개만 캐시 (pair 당 1 entry)"

    v2 = assess_fault_severity(fake_video, reference_video_path=fake_reference_video)
    assert v1 == v2
    assert len(client.calls) == 3, "cache hit — 재샘플링 0 (N 호출 추가 발생 0)"


def test_samples_count_invalidates_cache(
    monkeypatch, fake_video, fake_reference_video
):
    """VISION_VETO_SAMPLES 변경 시 같은 pair 라도 cache miss (키에 N 포함)."""
    _in_memory_cache(monkeypatch)
    monkeypatch.setattr(gvs, "VISION_VETO_SAMPLES", 3)
    client = _SeqClient([_sev_json("moderate")] * 6)
    _patch_seq_client(monkeypatch, client)

    assess_fault_severity(fake_video, reference_video_path=fake_reference_video)
    calls_after_first = len(client.calls)
    assert calls_after_first == 3

    monkeypatch.setattr(gvs, "VISION_VETO_SAMPLES", 1)
    assess_fault_severity(fake_video, reference_video_path=fake_reference_video)
    assert len(client.calls) == calls_after_first + 1, (
        "N 변경 → stale 무효화 + 재샘플 (N=1 추가 호출)"
    )


def test_prompt_schema_version():
    """PROMPT_VERSION = v7.0 (head-to-toe 강제 스캔 + 전 구간 힌트, 2026-06-22). SCHEMA_VERSION = v5.0."""
    assert PROMPT_VERSION == "v7.0"
    assert SCHEMA_VERSION == "v5.0"


def test_default_samples_is_three():
    """VISION_VETO_SAMPLES 기본 3 (env override 가능, min 1)."""
    assert gvs.VISION_VETO_SAMPLES >= 1
