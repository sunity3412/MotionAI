"""quick-260919-tkv — result.analysisVersion (출처 기록) 불변식 잠금.

belle 2026-09-19: "분석이 할 때마다 다르니까 문제 아냐. 언제는 3장이라 보고하고
6장이라 보고하고 5장이라 보고하고 ... 몇 일은 이렇게 몇 일은 이렇게 해서 꼬이는 거
아냐."  같은 pdshape 영상의 라이브 이전 이력을 실측해 원인을 갈랐다:

  3판(9/02~9/03) 60점 / 감점 5 / 결과 지문 389f9b31 / 버전 기록 없음
  3판(9/09)      60점 / 감점 6 / 결과 지문 3ac37f2f / 버전 기록 없음
  오늘           80점 / 감점 1 / 결과 지문 c162916  / 버전 기록 없음

(1) 비결정성이 아니다 — 같은 코드에서 3번 돌려 3번 다 지문이 같다(두 묶음 3/3).
(2) 어느 판이 어느 코드/기준에서 나왔는지 기록이 doc 어디에도 없어 **분석이 바뀐
    건지 우리가 바꾼 건지** 구분할 수단이 없었다.

이 파일이 지키는 것 (contract.md §11.13):
  · 채점 무접촉 — 방출 helper 가 result 의 다른 키를 하나도 건드리지 않는다.
  · fail-closed — 못 구한 값은 키 생략 (빈 문자열/'unknown'/추측 금지).
  · flat scalar only — Firestore nested-array 금지 정합.
  · 플래그 판정 규칙 parity — 소비처(rtmw_engine / ort_determinism) 와 동일.
  · 3-way lockstep — provenance ↔ models ↔ analysis.ts ↔ contract.md.

전부 로컬 — GPU/Firestore/S3/네트워크 0.
"""

from __future__ import annotations

import copy
import importlib
import sys
from pathlib import Path

import pytest

from sunity_shared import firestore_admin, models, provenance

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TS_CONTRACT = _REPO_ROOT / "app" / "src" / "types" / "analysis.ts"
_MD_CONTRACT = _REPO_ROOT / "docs" / "contract.md"

_PIPELINE_DIR = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))


def _import_pipeline():
    sys.modules.pop("app", None)
    import app  # noqa: WPS433

    return importlib.reload(app)


@pytest.fixture(autouse=True)
def _clean_flag_env(monkeypatch):
    """플래그·SHA env 를 매 테스트 초기화 — 실행 환경 오염 차단."""
    for name in (
        "ROT180_INVERSION_ENABLED",
        "PR_INVERSION_ENABLED",
        "RTMW_DETERMINISTIC",
        "SUNITY_COMMIT_SHA",
        "SUNITY_SHADOW_REFERENCE_VERSION",
    ):
        monkeypatch.delenv(name, raising=False)


# ══════════════════ 1. 채점 무접촉 (이 단위의 최우선 제약) ══════════════════


def _scoring_result() -> dict:
    """점수/감점/카드가 들어 있는 대표 result — 이 값들이 1도 바뀌면 안 된다."""
    return {
        "overallScore": 80,
        "dimensionScores": {"angle": 72, "line": 88, "stability": 91},
        "deductionBreakdown": {
            "baseline": 100,
            "final": 80,
            "records": [
                {"recordId": "r1", "ruleId": "line_extension", "points": 12},
                {"recordId": "r2", "ruleId": "angle_dev", "points": 8},
            ],
            "coverageGaps": [],
        },
        "faultZoomComparisons": [
            {"recordId": "r1", "userVideoSec": 8.1, "refVideoSec": 3.8},
            {"recordId": "r2", "userVideoSec": 5.7, "refVideoSec": 6.4},
        ],
        "timingsMs": {"pose": 1200},
        "coachStatus": "pending",
    }


def test_attach_analysis_version_touches_nothing_else():
    """방출 helper 의 유일한 부작용 = analysisVersion 키 1개 (채점 무접촉 박제).

    점수(overallScore)·감점(deductionBreakdown.final / records 수)·카드 수
    (faultZoomComparisons 길이) 가 호출 전후로 완전히 동일해야 한다.
    """
    pipeline = _import_pipeline()
    result = _scoring_result()
    before = copy.deepcopy(result)

    pipeline._attach_analysis_version(
        result, reference_release="rot180_v1", uid="u", analysis_id="a"
    )

    assert set(result) - set(before) == {"analysisVersion"}
    for key, value in before.items():
        assert result[key] == value, f"{key} 가 변했다 — 채점 무접촉 위반"
    # 점수 3종을 명시적으로 다시 못 박는다 (회귀가 났을 때 무엇이 깨졌는지 즉시 보이게).
    assert result["overallScore"] == 80
    assert result["deductionBreakdown"]["final"] == 80
    assert len(result["deductionBreakdown"]["records"]) == 2
    assert len(result["faultZoomComparisons"]) == 2


def test_attach_analysis_version_is_graceful_on_failure(monkeypatch):
    """기록 실패가 완료된 분석을 fail 시키지 않는다 (graceful skip)."""
    pipeline = _import_pipeline()

    def _boom(**_kwargs):
        raise RuntimeError("provenance 조립 실패")

    monkeypatch.setattr(pipeline.provenance, "build_analysis_version", _boom)

    result = _scoring_result()
    before = copy.deepcopy(result)
    pipeline._attach_analysis_version(
        result, reference_release=None, uid="u", analysis_id="a"
    )
    assert result == before  # 키 추가조차 없음 — 분석 산출 완전 무변경


def test_attach_analysis_version_pose_engine_from_same_source_as_health_canary(monkeypatch):
    """poseEngine 출처 = pipeline 모듈 전역 `_RTMW_ENGINE` (/health canary 와 동일)."""
    pipeline = _import_pipeline()

    class RTMWPoseEngine:  # 클래스명만 쓰인다 (인스턴스 내용 무관)
        pass

    monkeypatch.setattr(pipeline, "_RTMW_ENGINE", RTMWPoseEngine(), raising=False)
    result: dict = {}
    pipeline._attach_analysis_version(
        result, reference_release=None, uid="u", analysis_id="a"
    )
    assert result["analysisVersion"]["poseEngine"] == "RTMWPoseEngine"


def test_attach_analysis_version_omits_pose_engine_when_adapters_unloaded(monkeypatch):
    """어댑터 미로드(테스트/CPU 경로) → poseEngine 키 생략 (fail-closed)."""
    pipeline = _import_pipeline()
    monkeypatch.setattr(pipeline, "_RTMW_ENGINE", None, raising=False)
    result: dict = {}
    pipeline._attach_analysis_version(
        result, reference_release=None, uid="u", analysis_id="a"
    )
    assert "poseEngine" not in result["analysisVersion"]


# ══════════════════ 2. fail-closed — 못 구한 값은 키 생략 ══════════════════


def test_commit_sha_omitted_when_unresolvable(monkeypatch):
    """SHA 를 못 구하면 키가 없다 — 'unknown'/'' 로 채우지 않는다."""
    monkeypatch.setattr(provenance, "_commit_sha_cache", None, raising=False)
    monkeypatch.setattr(provenance, "resolve_commit_sha", lambda: None)
    out = provenance.build_analysis_version()
    assert "commitSha" not in out


def test_commit_sha_prefers_env(monkeypatch):
    monkeypatch.setattr(provenance, "_commit_sha_cache", None, raising=False)
    monkeypatch.setenv("SUNITY_COMMIT_SHA", "  deadbeef  ")
    assert provenance.resolve_commit_sha() == "deadbeef"


def test_resolve_commit_sha_returns_none_not_unknown(monkeypatch):
    """git 실패 + env 부재 → None. 'unknown' 문자열은 provenance 계약이 아니다."""
    monkeypatch.setattr(provenance, "_commit_sha_cache", None, raising=False)

    def _fail(*_a, **_k):
        raise FileNotFoundError("git 없음")

    import subprocess

    monkeypatch.setattr(subprocess, "run", _fail)
    assert provenance.resolve_commit_sha() is None


@pytest.mark.parametrize(
    "kwargs, absent",
    [
        ({"reference_release": None}, "referenceRelease"),
        ({"reference_release": ""}, "referenceRelease"),
        ({"pose_engine": None}, "poseEngine"),
        ({"pose_engine": ""}, "poseEngine"),
    ],
)
def test_empty_values_omit_keys(monkeypatch, kwargs, absent):
    """빈 문자열도 값이 아니다 — 키 생략 (fail-closed)."""
    monkeypatch.setattr(provenance, "resolve_commit_sha", lambda: None)
    out = provenance.build_analysis_version(**kwargs)
    assert absent not in out


def test_flags_always_present_and_bool(monkeypatch):
    """env 미설정의 사실값은 False — 플래그는 항상 실린다.

    그래서 analysisVersion 은 절대 빈 객체가 아니고, **필드 존재 자체** 가
    'quick-260919-tkv 이후 분석' 표식이 된다 (contract.md §11.13).
    """
    monkeypatch.setattr(provenance, "resolve_commit_sha", lambda: None)
    out = provenance.build_analysis_version()
    assert out == {
        "rot180InversionEnabled": False,
        "prInversionEnabled": False,
        "rtmwDeterministic": False,
    }


def test_payload_is_flat_scalar_only(monkeypatch):
    """Firestore nested-array 금지 정합 — 값은 전부 str/bool."""
    monkeypatch.setenv("SUNITY_COMMIT_SHA", "abc1234")
    monkeypatch.setattr(provenance, "_commit_sha_cache", None, raising=False)
    out = provenance.build_analysis_version(
        reference_release="rot180_v1", pose_engine="RTMWPoseEngine"
    )
    for key, value in out.items():
        assert isinstance(value, (str, bool)), f"{key} 가 scalar 가 아니다: {type(value)}"


def test_no_secret_shaped_keys(monkeypatch):
    """비밀 금지 — sha/버전/플래그/엔진명만. 키·토큰류 이름이 섞이면 실패."""
    monkeypatch.setenv("SUNITY_COMMIT_SHA", "abc1234")
    monkeypatch.setattr(provenance, "_commit_sha_cache", None, raising=False)
    out = provenance.build_analysis_version(
        reference_release="rot180_v1", pose_engine="RTMWPoseEngine"
    )
    banned = ("token", "secret", "key", "password", "credential")
    for key in out:
        low = key.lower()
        assert not any(b in low for b in banned), f"의심 키: {key}"


# ══════════════════ 3. 플래그 판정 parity — 소비처가 정본 ══════════════════

# 규칙이 플래그마다 다르다(2026-09-19 실측). 값 목록은 규칙 차이가 드러나는 것들:
#   "true" → rot180/pr 는 ON, deterministic 은 OFF
#   " 1 "  → strip 하는 쪽만 ON
#   "on"/"yes" → 셋 다 OFF (health 의 _env_flag 만 ON — contract.md §11.13 표)
_FLAG_VALUES = ("1", "true", "TRUE", " 1 ", "0", "", "on", "yes", "True ")


@pytest.mark.parametrize("value", _FLAG_VALUES)
def test_rot180_and_pr_flag_parity_with_rtmw_engine(monkeypatch, value):
    """provenance 의 복제 규칙 == rtmw_engine._env_on (실제로 동작을 켜는 쪽)."""
    from sunity_shared.analysis.pose_engines.rtmw import rtmw_engine

    for env_name, doc_key in (
        ("ROT180_INVERSION_ENABLED", "rot180InversionEnabled"),
        ("PR_INVERSION_ENABLED", "prInversionEnabled"),
    ):
        monkeypatch.setenv(env_name, value)
        monkeypatch.setattr(provenance, "resolve_commit_sha", lambda: None)
        out = provenance.build_analysis_version()
        assert out[doc_key] == rtmw_engine._env_on(env_name), (
            f"{env_name}={value!r} — provenance 와 엔진 판정이 갈렸다"
        )


@pytest.mark.parametrize("value", _FLAG_VALUES)
def test_deterministic_flag_parity_with_ort_determinism(monkeypatch, value):
    """provenance 의 복제 규칙 == ort_determinism.deterministic_enabled (정확히 "1")."""
    from sunity_shared.analysis.pose_engines.rtmw import ort_determinism

    monkeypatch.setenv("RTMW_DETERMINISTIC", value)
    monkeypatch.setattr(provenance, "resolve_commit_sha", lambda: None)
    out = provenance.build_analysis_version()
    assert out["rtmwDeterministic"] == ort_determinism.deterministic_enabled(), (
        f"RTMW_DETERMINISTIC={value!r} — provenance 와 세션 게이트 판정이 갈렸다"
    )


def test_deterministic_rule_is_stricter_than_rot180(monkeypatch):
    """규칙 차이가 실재함을 못 박는다 — 'true' 는 rot180 ON / deterministic OFF.

    이 비대칭이 우연이 아니라 실측된 사실이라는 것을 기록으로 남긴다
    (contract.md §11.13 표). 어느 한쪽을 '정리' 하려면 이 테스트를 먼저 봐야 한다.
    """
    monkeypatch.setattr(provenance, "resolve_commit_sha", lambda: None)
    monkeypatch.setenv("ROT180_INVERSION_ENABLED", "true")
    monkeypatch.setenv("RTMW_DETERMINISTIC", "true")
    out = provenance.build_analysis_version()
    assert out["rot180InversionEnabled"] is True
    assert out["rtmwDeterministic"] is False


# ══════════════════ 4. referenceRelease 해석 — 실제로 쓴 판만 ══════════════════


class _Snap:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return copy.deepcopy(self._data) if self._data is not None else None


class _FakeDocStore:
    """firestore_admin._doc path seam (phase33/test_candidate_staging.py 선례)."""

    def __init__(self, store: dict):
        self.store = store

    def __call__(self, path: str):
        outer = self

        class _Ref:
            def get(self):
                return _Snap(outer.store.get(path))

        return _Ref()


def _patch_doc(monkeypatch, store: dict):
    monkeypatch.setattr(firestore_admin, "_doc", _FakeDocStore(store), raising=True)


def test_active_release_returns_pointer_when_version_doc_exists(monkeypatch):
    store = {
        "reference/_release": {"activeCandidate": "rot180_v1"},
        "reference/ref-pdshape/versions/rot180_v1": {"angles": [1.0]},
    }
    _patch_doc(monkeypatch, store)
    assert firestore_admin.get_active_reference_release("ref-pdshape") == "rot180_v1"


def test_active_release_none_when_version_doc_missing(monkeypatch):
    """포인터는 있는데 버전 문서가 없다 → get_reference_motion 이 top-level 로 폴백.

    그래서 여기서도 None 이어야 한다 — **실제로 안 쓴 릴리스를 박제하지 않는다.**
    """
    store = {"reference/_release": {"activeCandidate": "rot180_v1"}}
    _patch_doc(monkeypatch, store)
    assert firestore_admin.get_active_reference_release("ref-pdshape") is None


def test_active_release_none_when_no_pointer(monkeypatch):
    _patch_doc(monkeypatch, {})
    assert firestore_admin.get_active_reference_release("ref-pdshape") is None


def test_active_release_honours_shadow_env(monkeypatch):
    """eval shadow(SUNITY_SHADOW_REFERENCE_VERSION)가 포인터보다 우선 — 해석기와 동일."""
    store = {
        "reference/_release": {"activeCandidate": "rot180_v1"},
        "reference/ref-pdshape/versions/cand-x": {"angles": [1.0]},
    }
    _patch_doc(monkeypatch, store)
    monkeypatch.setenv("SUNITY_SHADOW_REFERENCE_VERSION", "cand-x")
    assert firestore_admin.get_active_reference_release("ref-pdshape") == "cand-x"


def test_active_release_and_get_reference_motion_agree(monkeypatch):
    """두 함수가 같은 포인터 판정을 쓴다 — 갈리면 doc 의 기록이 거짓말이 된다."""
    store = {
        "reference/_release": {"activeCandidate": "rot180_v1"},
        "reference/ref-pdshape": {"angles": [0.0], "name": "top"},
        "reference/ref-pdshape/versions/rot180_v1": {"angles": [9.0]},
    }
    _patch_doc(monkeypatch, store)
    doc = firestore_admin.get_reference_motion("ref-pdshape")
    assert doc is not None and doc["angles"] == [9.0]  # candidate overlay 소비
    assert firestore_admin.get_active_reference_release("ref-pdshape") == "rot180_v1"


# ══════════════════ 5. scoped validator ══════════════════


def test_validator_accepts_none_and_flat_scalars():
    firestore_admin._validate_analysis_version(None)
    firestore_admin._validate_analysis_version(
        {"commitSha": "abc", "referenceRelease": "rot180_v1", "rtmwDeterministic": True}
    )


def test_validator_rejects_nested():
    with pytest.raises(TypeError):
        firestore_admin._validate_analysis_version({"commitSha": ["a", "b"]})
    with pytest.raises(TypeError):
        firestore_admin._validate_analysis_version({"commitSha": {"x": 1}})
    with pytest.raises(TypeError):
        firestore_admin._validate_analysis_version(["not", "a", "dict"])


def test_validator_rejects_unknown_key():
    """계약 밖 키가 조용히 섞이면 기록 자체를 못 믿게 된다."""
    with pytest.raises(ValueError, match="미등재 키"):
        firestore_admin._validate_analysis_version({"runpodAuthToken": "x"})


def test_builder_output_passes_validator(monkeypatch):
    """조립기 산출이 저장 검증을 무조건 통과한다 (계약 왕복)."""
    monkeypatch.setenv("SUNITY_COMMIT_SHA", "abc1234")
    monkeypatch.setattr(provenance, "_commit_sha_cache", None, raising=False)
    out = provenance.build_analysis_version(
        reference_release="rot180_v1", pose_engine="RTMWPoseEngine"
    )
    firestore_admin._validate_analysis_version(out)


# ══════════════════ 6. 3-way lockstep ══════════════════


def test_keys_lockstep_provenance_and_models():
    assert provenance.ANALYSIS_VERSION_KEYS == models.ANALYSIS_VERSION_KEYS


def test_builder_emits_only_registered_keys(monkeypatch):
    monkeypatch.setenv("SUNITY_COMMIT_SHA", "abc1234")
    monkeypatch.setattr(provenance, "_commit_sha_cache", None, raising=False)
    out = provenance.build_analysis_version(
        reference_release="rot180_v1", pose_engine="RTMWPoseEngine"
    )
    assert set(out) <= set(models.ANALYSIS_VERSION_KEYS)
    # 전부 채운 호출은 등재 키를 빠짐없이 낸다 (키 목록이 사문화되지 않게).
    assert set(out) == set(models.ANALYSIS_VERSION_KEYS)


def test_typescript_contract_declares_every_key():
    """app/src/types/analysis.ts 의 AnalysisVersion 이 같은 키를 선언한다."""
    src = _TS_CONTRACT.read_text(encoding="utf-8")
    assert "export interface AnalysisVersion" in src
    assert "analysisVersion?: AnalysisVersion;" in src
    for key in models.ANALYSIS_VERSION_KEYS:
        assert f"{key}?:" in src, f"analysis.ts 에 {key} 선언 없음 (lockstep 위반)"


def test_markdown_contract_section_exists():
    src = _MD_CONTRACT.read_text(encoding="utf-8")
    assert "### §11.13 AnalysisResult.analysisVersion" in src
    for key in models.ANALYSIS_VERSION_KEYS:
        assert key in src, f"contract.md 에 {key} 기술 없음 (lockstep 위반)"


# ══════════════════ 7. 배선 — 진짜 `_process` 가 실어 보낸다 ══════════════════
#
# helper 단위 테스트는 "만들었다" 만 증명한다. [[wiring-claims-need-log-evidence]]
# 규율에 따라 **실제 `_process` 를 완주시켜 complete_analysis 로 넘어간 result** 에
# 필드가 실렸는지를 본다. 하네스는 tests/pipeline/test_pipeline_phase9.py 의 것을
# 그대로 재사용한다 (mock E2E — GPU/S3/Firestore 0).


def _phase9_harness():
    from tests.pipeline import test_pipeline_phase9 as h  # noqa: WPS433

    return h


def test_process_mode3_emits_analysis_version_without_reference_release(monkeypatch):
    """mode3 = 기준 없음 → analysisVersion 은 실리되 referenceRelease 키는 생략."""
    from unittest.mock import MagicMock

    h = _phase9_harness()
    pipeline = h._import_pipeline()
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_analysis",
        lambda uid, aid: {"mode": pipeline.models.MODE_SELF},
    )
    monkeypatch.setattr(
        pipeline.firestore_admin, "update_analysis_status", lambda *a, **k: None
    )
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_previous_analysis",
        lambda uid, aid, mode=None: None,
    )
    complete_mock = MagicMock()
    monkeypatch.setattr(pipeline.firestore_admin, "complete_analysis", complete_mock)
    monkeypatch.setattr(pipeline, "_signed_get", lambda bucket, key: f"https://s/{key}")
    coach = MagicMock()
    coach.write.return_value = {"summary": "mock"}
    pipeline._COACH_WRITER = coach
    monkeypatch.setattr(pipeline, "_ensure_adapters", lambda: None)
    h._patch_extract_inputs(monkeypatch, pipeline)

    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")

    result = complete_mock.call_args[0][2]
    version = result["analysisVersion"]
    assert "referenceRelease" not in version  # mode3 = 기준 자체가 없다
    assert version["rot180InversionEnabled"] is False
    firestore_admin._validate_analysis_version(version)


def test_process_mode1_emits_reference_release(monkeypatch):
    """mode1 = 기준 사용 → 실제로 overlay 된 candidate version 이 실린다."""
    from unittest.mock import MagicMock

    import numpy as np

    h = _phase9_harness()
    pipeline = h._import_pipeline()
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_analysis",
        lambda uid, aid: {
            "mode": pipeline.models.MODE_EXPERT,
            "referenceMotionId": "ref-pdshape",
        },
    )
    monkeypatch.setattr(
        pipeline.firestore_admin, "update_analysis_status", lambda *a, **k: None
    )
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_reference_motion",
        lambda mid: {
            "motionId": "ref-pdshape",
            "name": "pdshape",
            "athleteName": "정은지",
            "angles": np.full(60 * 8, 90.0).tolist(),
            "anglesJointKeys": list(["a"] * 8),
            "videoS3Key": None,
        },
    )
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_active_reference_release",
        lambda mid: "rot180_v1",
    )
    complete_mock = MagicMock()
    monkeypatch.setattr(pipeline.firestore_admin, "complete_analysis", complete_mock)
    monkeypatch.setattr(pipeline, "_signed_get", lambda bucket, key: f"https://s/{key}")
    coach = MagicMock()
    coach.write.return_value = {"summary": "mock"}
    pipeline._COACH_WRITER = coach
    monkeypatch.setattr(pipeline, "_ensure_adapters", lambda: None)
    h._patch_extract_inputs(monkeypatch, pipeline)

    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")

    result = complete_mock.call_args[0][2]
    assert result["analysisVersion"]["referenceRelease"] == "rot180_v1"
    firestore_admin._validate_analysis_version(result["analysisVersion"])


def test_process_survives_reference_release_lookup_failure(monkeypatch):
    """기록 조회가 터져도 분석은 완주한다 (graceful — 기록은 분석을 막지 않는다)."""
    from unittest.mock import MagicMock

    import numpy as np

    h = _phase9_harness()
    pipeline = h._import_pipeline()
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_analysis",
        lambda uid, aid: {
            "mode": pipeline.models.MODE_EXPERT,
            "referenceMotionId": "ref-pdshape",
        },
    )
    monkeypatch.setattr(
        pipeline.firestore_admin, "update_analysis_status", lambda *a, **k: None
    )
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_reference_motion",
        lambda mid: {
            "motionId": "ref-pdshape",
            "name": "pdshape",
            "athleteName": "정은지",
            "angles": np.full(60 * 8, 90.0).tolist(),
            "anglesJointKeys": list(["a"] * 8),
            "videoS3Key": None,
        },
    )

    def _boom(_mid):
        raise RuntimeError("Firestore 읽기 실패")

    monkeypatch.setattr(
        pipeline.firestore_admin, "get_active_reference_release", _boom
    )
    complete_mock = MagicMock()
    monkeypatch.setattr(pipeline.firestore_admin, "complete_analysis", complete_mock)
    monkeypatch.setattr(pipeline, "_signed_get", lambda bucket, key: f"https://s/{key}")
    coach = MagicMock()
    coach.write.return_value = {"summary": "mock"}
    pipeline._COACH_WRITER = coach
    monkeypatch.setattr(pipeline, "_ensure_adapters", lambda: None)
    h._patch_extract_inputs(monkeypatch, pipeline)

    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")

    complete_mock.assert_called_once()  # 분석 완주
    result = complete_mock.call_args[0][2]
    assert "referenceRelease" not in result["analysisVersion"]  # 못 구했으니 키 생략
    assert result["overallScore"] is not None  # 점수는 그대로 나온다
