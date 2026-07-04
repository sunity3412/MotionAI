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


def test_clean_form_reports_none_score_free(monkeypatch, fake_video):
    """정타(dominant_severity none + 빈 differences) → severity 'none' + 숫자 0 (ND-02).

    Phase 24 (밴드 제거): Gemini 은 점수를 절대 내지 않는다 — verdict 에 score 필드 부재,
    severity 는 non-scoring 라벨. '없음' fault 는 짚을 측정대상 없음 → 엔진이 어떤 criterion
    도 routing 하지 않는다(criteria_for_fault). over-penalization fix 의 의도(정타를 깎지
    않음)는 이제 엔진(measured seed 활성화 0)이 보장한다.
    """
    from sunity_shared.analysis import gemini_vision_scorer, deduction_engine, ipsf_criteria

    _in_memory_cache(monkeypatch)
    client = _FakeClient(_CLEAN_JSON)
    _patch_client(monkeypatch, client)

    verdict = assess_fault_severity(fake_video)
    assert verdict is not None
    assert verdict.severity == "none"
    # 객관성: verdict 는 숫자 점수 필드를 들지 않는다(_SCORE_PATTERN 누수 가드 동행).
    assert not hasattr(verdict, "score")
    assert "score" not in gemini_vision_scorer.build_schema()["properties"]
    # 정타 차이 0 — 엔진이 어떤 measured criterion 도 seed 하지 않는다(깎임 0).
    assert ipsf_criteria.criteria_from_measured_deviations({}) == frozenset()


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
    """PROMPT_VERSION = v10.0 (25-02: part_scope 구조화 강제) / SCHEMA_VERSION = v7.0."""
    assert PROMPT_VERSION == "v10.0"
    assert PROMPT_VERSION != "v9.0", "25-02 프롬프트 변경 = bump 필수 (캐시 무효화)"
    assert SCHEMA_VERSION == "v7.0"


def test_default_samples_is_three():
    """VISION_VETO_SAMPLES 기본 3 (env override 가능, min 1)."""
    assert gvs.VISION_VETO_SAMPLES >= 1


# ─────────────────── Task 1 — still-image 업로드 swap (D-01, D-09 H3) ───────────────────


def test_mime_image_branches():
    """_mime png→image/png, jpg/jpeg→image/jpeg + video 분기 불변 (Task 1)."""
    assert gvs._mime("frame.png") == "image/png"
    assert gvs._mime("frame.PNG") == "image/png"
    assert gvs._mime("frame.jpg") == "image/jpeg"
    assert gvs._mime("frame.jpeg") == "image/jpeg"
    assert gvs._mime("frame.JPEG") == "image/jpeg"
    assert gvs._mime("clip.mov") == "video/quicktime"
    assert gvs._mime("clip.qt") == "video/quicktime"
    assert gvs._mime("clip.webm") == "video/webm"
    assert gvs._mime("clip.mp4") == "video/mp4"
    assert gvs._mime("clip.unknown") == "video/mp4"


class _ActiveHandle:
    """state.name == 'ACTIVE' 인 업로드 핸들 (MagicMock name kwarg 함정 회피)."""

    def __init__(self, name="uploaded"):
        self.name = name
        self.state = type("S", (), {"name": "ACTIVE"})()


class _FakeImageFiles:
    def __init__(self):
        self.upload_mimes: list[str] = []
        self.deleted: list[str] = []

    def upload(self, *, file, config):
        self.upload_mimes.append(getattr(config, "mime_type", None))
        return _ActiveHandle()

    def get(self, *, name):
        return _ActiveHandle()

    def delete(self, *, name):
        self.deleted.append(name)


class _ImageClient:
    def __init__(self):
        self.files = _FakeImageFiles()
        self.models = MagicMock()


@pytest.fixture
def fake_image(tmp_path):
    p = tmp_path / "worst_frame.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\nfake-png")
    return str(p)


def test_upload_image_uses_image_mime_and_active_wait(fake_image):
    """_upload_image 가 ACTIVE-wait 디시플린 + 이미지 mime 분기 (Task 1)."""
    client = _ImageClient()
    uploaded = gvs._upload_image(client, fake_image)
    assert uploaded is not None
    assert client.files.upload_mimes == ["image/png"]


def test_upload_image_path_guard_before_upload():
    """없는 경로 → 업로드 전 예외 (D-10 HIGH-2)."""
    client = _ImageClient()
    with pytest.raises((FileNotFoundError, OSError)):
        gvs._upload_image(client, "/nonexistent/path/to/frame.png")
    assert client.files.upload_mimes == []


def test_no_toplevel_google_import():
    """google.genai import 는 함수 내부에만 (lazy, D-16) — 모듈 top-level(들여쓰기 0) 0."""
    source = Path(inspect.getfile(gvs)).read_text(encoding="utf-8")
    for line in source.splitlines():
        # 들여쓰기 0(모듈 레벨) 인 import 만 검사 — 함수 내부 lazy import 는 허용.
        if line and not line[0].isspace():
            if line.startswith("from google") or line.startswith("import google"):
                pytest.fail(f"top-level google import: {line!r}")


def test_assess_still_pair_signature():
    """assess_fault_severity still 경로 명시 인자 (Task 1)."""
    sig = inspect.signature(gvs.assess_fault_severity)
    params = sig.parameters
    assert "student_frame_path" in params
    assert "reference_frame_path" in params
    assert "part_scopes" in params
    assert "frame_indices" in params
    assert "selector_version" in params


def test_comparison_contents_two_separate_handles(monkeypatch):
    """"나란히" = 두 분리 image 핸들 (H3 — composite 아님)."""
    captured: dict = {}

    def _spy(client, ref_uploaded, student_uploaded, at_seconds, *args, **kwargs):
        captured["ref"] = ref_uploaded
        captured["student"] = student_uploaded
        captured["distinct"] = ref_uploaded is not student_uploaded
        return '{"motion":"x","dominant_severity":"minor","primary_fault":"라인","differences":[]}'

    monkeypatch.setattr(gvs, "_call_gemini_comparison", _spy)

    ref_handle = MagicMock(name="ref-handle")
    student_handle = MagicMock(name="student-handle")
    verdict = gvs._aggregate_comparison_verdict(
        _ImageClient(), ref_handle, student_handle, None
    )
    assert verdict is not None
    assert captured["distinct"] is True
    assert captured["ref"] is ref_handle
    assert captured["student"] is student_handle


# ─────────────── Task 2 — precision/support 게이트 + 자원 bound (H1, H6, MED-1) ───────────────


def _diff(body_part, severity="moderate", dev=10.0):
    return {
        "body_part": body_part, "severity": severity,
        "approx_angle_deviation_deg": dev,
        "correct_state": "신전", "fault_state": "굽음",
    }


def test_resource_bound_constants_defined():
    """MAX_VETO_CALLS/MAX_VETO_UPLOADS/MAX_VETO_WALL_S 상수 존재 (H6)."""
    assert isinstance(gvs.MAX_VETO_CALLS, int) and gvs.MAX_VETO_CALLS > 0
    assert isinstance(gvs.MAX_VETO_UPLOADS, int) and gvs.MAX_VETO_UPLOADS > 0
    assert gvs.MAX_VETO_WALL_S > 0
    # support 게이트 상수 generic (특정 동작명 0).
    assert isinstance(gvs.VETO_SUPPORT_K, int) and gvs.VETO_SUPPORT_K >= 1


def test_single_frame_hallucination_does_not_survive_union():
    """단발 환각 결함(support<K)은 union 에서 drop (H1 핵심)."""
    # per-call differences: 무릎은 3회(support 충분), 환각 '왼팔'은 1회만.
    per_call = [
        [_diff("무릎", "major")],
        [_diff("무릎", "major")],
        [_diff("무릎", "major"), _diff("왼팔", "moderate")],
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="lower_body", min_support_k=2,
    )
    parts = {str(d.get("body_part")) for d in supported}
    assert any("무릎" in p for p in parts), "support≥K 무릎은 생존"
    assert not any("왼팔" in p for p in parts), "단발 환각 왼팔은 drop"


def test_supported_difference_survives_at_k():
    """K 이상 support 인 부위별 결함은 union 에 보존 (H1)."""
    per_call = [
        [_diff("왼팔", "moderate")],
        [_diff("left arm", "moderate")],
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="upper_body", min_support_k=2,
    )
    # 한·영 alias 가 같은 canonical 키로 합쳐져 K=2 도달.
    assert len(supported) >= 1
    assert any("팔" in str(d.get("body_part")) or "arm" in str(d.get("body_part")).lower()
               for d in supported)


def test_root_cause_derived_only_from_supported():
    """root cause 는 support 통과분에서만 + provenance 보존 (D-13 MED-1)."""
    per_call = [
        [_diff("무릎", "major")],
        [_diff("무릎", "major")],
        [_diff("왼팔", "moderate")],  # 단발 — drop.
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="lower_body", min_support_k=2,
    )
    causes = gvs._derive_root_causes_from_supported_differences(supported)
    texts = " ".join(getattr(c, "text", "") for c in causes)
    assert "왼팔" not in texts, "drop 된 환각의 root cause 누출 0"
    for c in causes:
        assert hasattr(c, "fault_key")
        assert hasattr(c, "source_difference_ids")
        assert hasattr(c, "support_count")


def test_all_dropped_yields_zero_root_causes():
    """모든 difference 가 support 게이트로 drop → root cause 0 (D-13 MED-1)."""
    per_call = [[_diff("왼팔")], [_diff("오른팔")], [_diff("무릎")]]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="upper_body", min_support_k=3,
    )
    assert supported == []
    assert gvs._derive_root_causes_from_supported_differences(supported) == []


def test_clean_input_severity_none_preserved():
    """정타(모든 부위 none) → severity none 유지 (위양성 비증가)."""
    per_call = [
        [_diff("무릎", "none")],
        [_diff("무릎", "none")],
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="lower_body", min_support_k=1,
    )
    # none severity 는 인정 결함 아님 → supported 비어야.
    assert supported == []


class _FakeClock:
    def __init__(self, ticks):
        self._ticks = list(ticks)
        self._i = 0

    def __call__(self):
        v = self._ticks[min(self._i, len(self._ticks) - 1)]
        self._i += 1
        return v


def test_fanout_budget_exhaust_before_planned_returns_resource_limited(monkeypatch):
    """planned call 전부 완료 전 예산(wall-clock) 소진 → resource_limited (D-13 HIGH-2, Option A)."""
    calls = {"n": 0}

    def _spy(client, ref_uploaded, student_uploaded, at_seconds, part_scope=None):
        calls["n"] += 1
        return '{"motion":"x","dominant_severity":"moderate","primary_fault":"다리","differences":[]}'

    monkeypatch.setattr(gvs, "_call_gemini_comparison", _spy)
    # wall-clock 이 두 번째 호출 후 budget 초과하도록 ticks 설정.
    clock = _FakeClock([0.0, 0.0, 999.0, 999.0, 999.0, 999.0])
    out = gvs._run_part_frame_fanout(
        _ImageClient(), MagicMock(), MagicMock(),
        part_scopes=["upper_body", "lower_body", "line"],
        at_seconds=None,
        clock=clock,
        wall_budget_s=10.0,
    )
    assert out["status"] == "resource_limited", out
    assert out["telemetry"]["samplingComplete"] is False
    assert out["telemetry"]["completedCalls"] < out["telemetry"]["plannedCalls"]


def test_fanout_complete_returns_verdict_sampling_complete(monkeypatch):
    """planned call 전부 완료 → applied 후보 verdict + samplingComplete=true."""
    def _spy(client, ref_uploaded, student_uploaded, at_seconds, part_scope=None):
        return '{"motion":"x","dominant_severity":"moderate","primary_fault":"다리","differences":[{"body_part":"무릎","severity":"moderate","approx_angle_deviation_deg":12}]}'

    monkeypatch.setattr(gvs, "_call_gemini_comparison", _spy)
    clock = _FakeClock([0.0] * 20)
    out = gvs._run_part_frame_fanout(
        _ImageClient(), MagicMock(), MagicMock(),
        part_scopes=["upper_body", "lower_body", "line"],
        at_seconds=None,
        clock=clock,
        wall_budget_s=1000.0,
    )
    assert out["status"] == "candidate_verdict", out
    assert out["telemetry"]["samplingComplete"] is True
    assert out["telemetry"]["completedCalls"] == out["telemetry"]["plannedCalls"]


def test_still_cache_key_includes_selector_version():
    """still 경로 cache 키가 selector_version 다르면 다른 키 + whole 와 충돌 0 (H3)."""
    k_whole = gvs.VisionVetoCache.build_key(
        video_hash="abc", model_name="m", input_granularity="whole",
    )
    k_a = gvs.VisionVetoCache.build_key(
        video_hash="abc", model_name="m", input_granularity="frame_pair",
        selector_version="sel1", frame_indices=[10, 20], top_k=2, window="w3",
    )
    k_b = gvs.VisionVetoCache.build_key(
        video_hash="abc", model_name="m", input_granularity="frame_pair",
        selector_version="sel2", frame_indices=[10, 20], top_k=2, window="w3",
    )
    assert k_a != k_b, "selector_version 다르면 다른 키"
    assert k_whole != k_a, "frame_pair 키는 whole 와 충돌 0"


# ─────────────── 23 GAP-FIX — assess_fault_context (production still-pair 진입점) ───────────────


@pytest.fixture
def fake_pair_frames(tmp_path):
    s = tmp_path / "student_worst.png"
    r = tmp_path / "ref_match.png"
    s.write_bytes(b"\x89PNG\r\n\x1a\nstudent")
    r.write_bytes(b"\x89PNG\r\n\x1a\nreference")
    return str(s), str(r)


def test_assess_fault_context_uploads_images_not_video(monkeypatch, fake_pair_frames):
    """still-pair 경로는 _upload_image(IMAGE) 만 사용 — _upload_video 호출 0 (23 GAP-FIX)."""
    _in_memory_cache(monkeypatch)
    student, ref = fake_pair_frames
    client = _ImageClient()
    monkeypatch.setattr(gvs, "_ensure_client", lambda: client)
    monkeypatch.setattr(
        gvs, "_upload_video",
        lambda *a, **k: pytest.fail("still-pair 가 _upload_video 호출 — IMAGE 여야 함"),
    )
    monkeypatch.setattr(
        gvs, "_call_gemini_comparison",
        lambda *a, **k: '{"motion":"x","dominant_severity":"moderate","primary_fault":"무릎","differences":[{"body_part":"무릎","severity":"moderate","approx_angle_deviation_deg":12}]}',
    )
    out = gvs.assess_fault_context(
        student, ref, at_seconds=1.3,
        part_scopes=["upper_body", "lower_body", "line"],
        frame_indices=[12], reference_frame_indices=[10],
        selector_version="v1",
    )
    assert out["status"] == "candidate_verdict", out
    # 두 IMAGE 업로드 (student + reference).
    assert client.files.upload_mimes == ["image/png", "image/png"]
    # 업로드 핸들 정리(File API delete) 호출됨 (저장소 누수 방지).
    assert len(client.files.deleted) == 2


def test_assess_fault_context_cold_warm_determinism(monkeypatch, fake_pair_frames):
    """cold miss → store, warm hit → 동일 rich dict + 재샘플링 0 (결정론 D-06)."""
    _in_memory_cache(monkeypatch)
    student, ref = fake_pair_frames
    calls = {"n": 0}

    def _spy(client, ref_uploaded, student_uploaded, at_seconds, part_scope=None):
        calls["n"] += 1
        return '{"motion":"x","dominant_severity":"moderate","primary_fault":"무릎","differences":[{"body_part":"무릎","severity":"moderate","approx_angle_deviation_deg":12}]}'

    monkeypatch.setattr(gvs, "_ensure_client", lambda: _ImageClient())
    monkeypatch.setattr(gvs, "_call_gemini_comparison", _spy)

    kwargs = dict(
        at_seconds=1.3, part_scopes=["upper_body", "lower_body", "line"],
        frame_indices=[12], reference_frame_indices=[10], selector_version="v1",
    )
    cold = gvs.assess_fault_context(student, ref, **kwargs)
    cold_calls = calls["n"]
    assert cold["status"] == "candidate_verdict"
    assert cold["telemetry"]["cacheHit"] is False
    assert cold_calls > 0

    warm = gvs.assess_fault_context(student, ref, **kwargs)
    # warm 은 Gemini 재호출 0 (cache hit).
    assert calls["n"] == cold_calls, "warm hit 가 fan-out 재실행하면 안 됨"
    assert warm["telemetry"]["cacheHit"] is True

    # supported_differences 의 _faultKey 가 byte-stable 복원 (canonical 어휘).
    assert len(warm["supported_differences"]) == len(cold["supported_differences"])
    cold_fk = cold["supported_differences"][0]["_faultKey"].to_dict()
    warm_fk = warm["supported_differences"][0]["_faultKey"].to_dict()
    assert cold_fk == warm_fk
    # root cause provenance 보존.
    assert len(warm["root_cause_hypotheses"]) == len(cold["root_cause_hypotheses"])


def test_assess_fault_context_missing_frame_graceful(monkeypatch):
    """still 이미지 결측 → skipped_error (graceful, 분석 흐름 차단 0)."""
    _in_memory_cache(monkeypatch)
    monkeypatch.setattr(gvs, "_ensure_client", lambda: _ImageClient())
    out = gvs.assess_fault_context(
        "/nonexistent/student.png", "/nonexistent/ref.png",
        part_scopes=["line"],
    )
    assert out["status"] == "skipped_error"
    assert out["supported_differences"] == []


# ─────────────── Task 3 (23-02) — DESCRIPTIVE 원인 가설 + source provenance ───────────────


def test_schema_has_root_cause_and_source_descriptive():
    """build_schema 의 differences[] 에 root_cause_hypothesis + source DESCRIPTIVE 필드 (D-04)."""
    keys = _walk_property_keys(build_schema())
    assert "root_cause_hypothesis" in keys
    assert "source" in keys


def test_schema_no_score_field_after_root_cause_add():
    """root_cause/source 추가 후에도 schema property 키에 score/overall/rating/percent/100 매칭 0 (MED-3 정밀화).

    description 텍스트의 부정 가드("숫자 점수 금지" 류)는 검사 대상 아님 — property **키**만.
    """
    keys = _walk_property_keys(build_schema())
    forbidden = ("score", "overall", "rating", "점수", "percent", "100")
    for key in keys:
        for f in forbidden:
            assert f not in key.lower(), f"schema property 키 '{key}' 에 forbidden '{f}'"


def test_verdict_dataclass_still_score_free():
    """VisionVerdict 에 score 류 필드 부재 유지 (객관성 hard gate, D-06)."""
    field_names = {f.name for f in dataclasses.fields(VisionVerdict)}
    assert field_names == {"primary_fault", "severity", "differences"}


def test_comparison_prompt_has_hypothesis_and_no_notch_or_percent_request():
    """_COMPARISON_PROMPT 에 '~로 보임' 가설 + cm/m 금지 + 칸/percent 산출 요청 0 (D-04/D-08)."""
    prompt = gvs._COMPARISON_PROMPT
    # 원인 가설 "~로 보임" 가설형 지시 존재.
    assert "보임" in prompt
    assert "root_cause_hypothesis" in prompt
    assert "vision_hypothesis" in prompt
    # cm/m 절대거리 금지 명시.
    assert "cm" in prompt  # "절대 cm/m 로 표기하지 마세요" 금지 지시.
    # Gemini 에 칸/percent 산출 요청이 없어야 — "%"/"100%" 표기 유도 0.
    # (prompt 가 percent 를 *금지*하는 문구는 허용 — 유도가 아님.)
    assert "100%" not in prompt or "만들어내지" in prompt


def test_comparison_prompt_generic_no_motion_name_hardcoded():
    """_COMPARISON_PROMPT 에 특정 동작명(kip-up 등) 하드코딩 0 — generic (D-06)."""
    prompt = gvs._COMPARISON_PROMPT.lower()
    for motion in ("kip-up", "kip up", "pdshape", "power-spin", "peter-pan", "climb"):
        assert motion not in prompt, f"curve-fit 위험 — 동작명 '{motion}' 하드코딩"


def test_prompt_schema_version_bumped_for_task3():
    """PROMPT_VERSION/SCHEMA_VERSION 이 23-01(v8.0/v6.0) 대비 추가 bump (캐시 무효화)."""
    assert PROMPT_VERSION != "v8.0"
    assert SCHEMA_VERSION != "v6.0"


def test_root_cause_hypothesis_passes_through_parse():
    """_parse_verdict 가 root_cause_hypothesis/source 를 DESCRIPTIVE 로 통과 (score 필드 추가 0)."""
    raw = (
        '{"motion":"x","dominant_severity":"moderate","primary_fault":"무릎 굽음",'
        '"differences":[{"body_part":"오른 무릎","correct_state":"신전","fault_state":"굽음",'
        '"severity":"moderate","root_cause_hypothesis":"코어 힘 부족으로 보임",'
        '"source":"vision_hypothesis"}]}'
    )
    verdict = gvs._parse_verdict(raw)
    assert verdict is not None
    assert not hasattr(verdict, "score")
    d0 = verdict.differences[0]
    assert d0.get("root_cause_hypothesis") == "코어 힘 부족으로 보임"
    assert d0.get("source") == "vision_hypothesis"


# ─────────────── 25-02 Task 1 — keypoint_set fold 집계 + AGGREGATION_VERSION ───────────────
#
# 25-RESEARCH §1 차단 1 재현: 어깨 언급이 side("왼쪽 어깨"=left vs "어깨"=unknown) /
# fault_kind("굽음"=pole_gap_or_bent vs "정렬 흐트러짐"=extension_or_alignment) fragment 로
# 분산돼 support K=2 미달 drop 되던 것을 keypoint_set 단독 그룹 키 fold 가 살린다.


def _sdiff(body_part, severity="moderate", dev=30.0, fault_state="정렬 흐트러짐"):
    return {
        "body_part": body_part, "severity": severity,
        "approx_angle_deviation_deg": dev,
        "correct_state": "정렬", "fault_state": fault_state,
    }


def test_shoulder_side_and_kind_fragments_fold_to_support_two():
    """side/fault_kind fragment 어깨 2건이 keypoint_set fold 로 K=2 통과 (차단 1 해소)."""
    per_call = [
        [_sdiff("왼쪽 어깨", dev=40.0, fault_state="굽음")],       # left + pole_gap_or_bent
        [_sdiff("어깨", dev=31.0, fault_state="정렬 흐트러짐")],   # unknown + extension_or_alignment
        [],
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="upper_body", min_support_k=2,
    )
    assert len(supported) == 1, "fragment 2건이 shoulder 그룹 하나로 fold — 대표 1개"
    rec = supported[0]
    assert rec["_supportCount"] == 2
    assert rec["_faultKey"].keypoint_set == "shoulder"
    # 대표 = 최고 severity rank → dev (동 rank 에서 dev 40 > 31).
    assert float(rec["approx_angle_deviation_deg"]) == 40.0


def test_fold_representative_side_unique_explicit_wins():
    """그룹 내 명시(left/right) side 가 유일하면 대표 _faultKey.side = 그 side."""
    per_call = [
        [_sdiff("왼쪽 어깨", dev=40.0)],
        [_sdiff("어깨", dev=31.0)],  # unknown — 명시 아님.
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="upper_body", min_support_k=2,
    )
    assert supported[0]["_faultKey"].side == "left"


def test_fold_representative_side_mixed_or_absent_is_unknown():
    """명시 side 혼재(left+right) 또는 전부 unknown → 대표 side = unknown."""
    mixed = [
        [_sdiff("왼쪽 어깨")],
        [_sdiff("오른쪽 어깨")],
    ]
    supported = gvs._filter_supported_differences(
        mixed, part_scope_hint="upper_body", min_support_k=2,
    )
    assert supported[0]["_faultKey"].side == "unknown"

    all_unknown = [
        [_sdiff("어깨")],
        [_sdiff("shoulder")],
    ]
    supported2 = gvs._filter_supported_differences(
        all_unknown, part_scope_hint="upper_body", min_support_k=2,
    )
    assert supported2[0]["_faultKey"].side == "unknown"


def test_fold_representative_is_highest_severity_then_dev():
    """대표 record = 그룹 내 최고 severity rank → 최고 dev (기존 규칙 불변)."""
    per_call = [
        [_sdiff("어깨", severity="minor", dev=50.0)],
        [_sdiff("왼쪽 어깨", severity="major", dev=25.0)],
        [_sdiff("오른쪽 어깨", severity="moderate", dev=45.0)],
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="upper_body", min_support_k=2,
    )
    assert len(supported) == 1
    rec = supported[0]
    assert rec["severity"] == "major"
    assert float(rec["approx_angle_deviation_deg"]) == 25.0
    assert rec["_supportCount"] == 3
    assert len(rec["_sourceIds"]) == 3


def test_fold_does_not_merge_distinct_keypoint_sets():
    """서로 다른 keypoint_set(shoulder vs leg)은 fold 되지 않는다 (그룹 분리 유지)."""
    per_call = [
        [_sdiff("왼쪽 어깨"), _sdiff("무릎", severity="major", dev=60.0)],
        [_sdiff("어깨"), _sdiff("오른 무릎", severity="major", dev=55.0)],
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="upper_body", min_support_k=2,
    )
    kp_sets = {r["_faultKey"].keypoint_set for r in supported}
    assert kp_sets == {"shoulder", "leg"}
    # severity 내림차순 정렬 불변 — major(leg) 가 앞.
    assert supported[0]["_faultKey"].keypoint_set == "leg"


def test_fold_no_union_inflation_same_call_counting_preserved():
    """fold 로 union 부풀림 없음 — 같은 call 안 같은 keypoint_set 2건도 대표 1개.

    support 는 기존 diff_id 순회(발생 건수) 의미 그대로 — call-교차 여부로 재정의하지
    않는다 (기존 카운트 로직 보존).
    """
    per_call = [
        [_sdiff("왼쪽 어깨", dev=40.0), _sdiff("오른쪽 어깨", dev=31.0)],
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="upper_body", min_support_k=2,
    )
    assert len(supported) == 1, "출력은 그룹당 대표 1개 (union 부풀림 0)"
    assert supported[0]["_supportCount"] == 2, "발생 건수 카운트 의미 보존"


def test_fold_severity_none_still_filtered():
    """severity='none' 은 fold 후에도 인정 결함 아님 (support 에 미기여)."""
    per_call = [
        [_sdiff("왼쪽 어깨", severity="none")],
        [_sdiff("어깨", severity="none")],
        [_sdiff("오른쪽 어깨", severity="moderate")],
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="upper_body", min_support_k=2,
    )
    assert supported == [], "none 2건은 카운트 밖 — moderate 단발은 K=2 미달 drop"


def test_fold_preserves_member_faults_and_original_fault_keys():
    """fold 대표에 그룹 멤버 원문(_memberFaults) + fold 전 FaultKey(_memberFaultKeys) 보존 (CR-01).

    fold 는 support 집계용 — 라우팅(split vs knee)/recall 어휘는 멤버 원문에서 소비된다.
    IN-02: fold 의미를 고치는 사람이 이 파일에서 marker 를 만나도록 값 자체를 박제.
    """
    assert gvs.AGGREGATION_VERSION == "agg3"
    per_call = [
        [_sdiff("왼쪽 어깨", dev=40.0, fault_state="굽음")],
        [_sdiff("어깨", dev=31.0, fault_state="정렬 흐트러짐")],
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="upper_body", min_support_k=2,
    )
    rec = supported[0]
    members = rec["_memberFaults"]
    assert {m["body_part"] for m in members} == {"왼쪽 어깨", "어깨"}
    fks = rec["_memberFaultKeys"]
    assert {(fk.side, fk.fault_kind) for fk in fks} == {
        ("left", "pole_gap_or_bent"), ("unknown", "extension_or_alignment"),
    }, "fold 전 원본 side/fault_kind 어휘 보존 (recall trace 입력)"
    assert all(fk.keypoint_set == "shoulder" for fk in fks)


def test_fold_member_dedup_keeps_best_by_rank_then_dev():
    """멤버 dedup = (body_part, fault_state) 키, 항목별 최선(rank→dev) 유지 — split 편차 보존."""
    per_call = [
        [_sdiff("스플릿", severity="minor", dev=25.0, fault_state="각도 부족")],
        [_sdiff("스플릿", severity="moderate", dev=30.0, fault_state="각도 부족")],
        [_sdiff("무릎", severity="major", dev=0.0, fault_state="굽음")],
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="lower_body", min_support_k=2,
    )
    assert len(supported) == 1  # 전부 keypoint_set=leg → 한 그룹
    members = {m["body_part"]: m for m in supported[0]["_memberFaults"]}
    assert set(members) == {"스플릿", "무릎"}
    assert float(members["스플릿"]["approx_angle_deviation_deg"]) == 30.0, (
        "동일 (body_part, fault_state) 멤버는 최고 rank→dev 1개만"
    )


def test_rich_doc_round_trip_preserves_member_meta():
    """_rich_to_doc/_rich_from_doc 가 _memberFaults/_memberFaultKeys 를 왕복 보존 (캐시 결정론)."""
    per_call = [
        [_sdiff("왼쪽 어깨", dev=40.0, fault_state="굽음")],
        [_sdiff("어깨", dev=31.0, fault_state="정렬 흐트러짐")],
    ]
    supported = gvs._filter_supported_differences(
        per_call, part_scope_hint="upper_body", min_support_k=2,
    )
    rich = {
        "status": "candidate_verdict",
        "verdict": None,
        "supported_differences": supported,
        "root_cause_hypotheses": gvs._derive_root_causes_from_supported_differences(supported),
        "telemetry": {},
    }
    doc = VisionVetoCache._rich_to_doc(rich)
    restored = VisionVetoCache._rich_from_doc(doc)
    r0 = restored["supported_differences"][0]
    o0 = supported[0]
    assert tuple(m["body_part"] for m in r0["_memberFaults"]) == tuple(
        m["body_part"] for m in o0["_memberFaults"]
    )
    assert tuple(fk.to_dict() for fk in r0["_memberFaultKeys"]) == tuple(
        fk.to_dict() for fk in o0["_memberFaultKeys"]
    )
    # doc(Firestore payload) 는 flat map 리스트 — FaultKey 객체 직렬화 누출 0.
    doc_rec = doc["supported_differences"][0]
    assert all(isinstance(m, dict) for m in doc_rec["_memberFaults"])
    assert all(isinstance(x, dict) for x in doc_rec["_memberFaultKeyDicts"])


def test_aggregation_version_constant_and_in_cache_key(monkeypatch):
    """AGGREGATION_VERSION 이 build_key 산출 키에 포함 + marker 변경 시 다른 키.

    rich 캐시는 집계 **후** supported_differences 를 저장 — 집계 변경 시 marker bump
    없이는 stale-hit (kip-up whole/whole_fanout FP 이력, 90d038f). 기존 키 공간 재사용 0.
    """
    assert isinstance(gvs.AGGREGATION_VERSION, str) and gvs.AGGREGATION_VERSION
    key = VisionVetoCache.build_key(video_hash="vh-agg", model_name="m")
    assert gvs.AGGREGATION_VERSION in key
    monkeypatch.setattr(gvs, "AGGREGATION_VERSION", "agg-test-999")
    key2 = VisionVetoCache.build_key(video_hash="vh-agg", model_name="m")
    assert key2 != key, "marker 변경 = 다른 키 (기존 키 공간 재사용 0)"
    assert "agg-test-999" in key2


# ─────────────── 25-02 Task 2 — part_scope 구조화 강제 프롬프트 (v10.0) ───────────────


def _comparison_prompt_for_scope(part_scope):
    """_call_gemini_comparison 이 실제로 보내는 최종 프롬프트 캡처 (fake client)."""
    client = _FakeClient(_VALID_JSON)
    gvs._call_gemini_comparison(
        client, MagicMock(name="ref"), MagicMock(name="student"), None,
        part_scope=part_scope,
    )
    contents = client.calls[-1]["contents"]
    return contents[-1]


def test_part_scope_prompt_forces_differences_structuring():
    """part_scope 제공 시 프롬프트에 differences[] 구조화 + 좌/우 명시 + 서사-only 금지 지시."""
    for scope in gvs.VETO_PART_SCOPES:
        prompt = _comparison_prompt_for_scope(scope)
        assert "differences" in prompt, f"{scope}: differences[] 구조화 지시 부재"
        assert "좌/우" in prompt, f"{scope}: 좌/우 명시 지시 부재"
        assert "누락" in prompt and "금지" in prompt, (
            f"{scope}: primary_fault 서사-only 금지 지시 부재"
        )
        # 기존 1·2번 규칙(정타/사소차/촬영조건 비결함) 유지 지시 보존.
        assert "1·2번 규칙" in prompt


def test_part_scope_prompt_generic_no_motion_names():
    """scope 프롬프트 산출물에 등재 동작명 하드코딩 0 (D-06 curve-fit 밴)."""
    motion_names = (
        "kip-up", "kip up", "킵업", "power-spin", "power spin", "파워스핀",
        "peter-pan", "peter pan", "피터팬", "elbow-twist", "elbow twist",
        "엘보 트위스트", "pdshape", "climb", "클라임",
    )
    for scope in (*gvs.VETO_PART_SCOPES, None):
        prompt = _comparison_prompt_for_scope(scope).lower()
        for motion in motion_names:
            assert motion not in prompt, (
                f"scope={scope}: 동작명 '{motion}' 하드코딩 — curve-fit 위험"
            )


def test_part_scope_none_prompt_unchanged_no_structuring_suffix():
    """part_scope 미제공(None) 경로는 suffix 없음 — 기존 비교 프롬프트 그대로."""
    prompt = _comparison_prompt_for_scope(None)
    assert prompt == gvs._COMPARISON_PROMPT


