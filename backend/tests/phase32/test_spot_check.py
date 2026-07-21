"""Plan 32-13 — 스팟체크 (D-22/D-23) 테스트 (LOCAL ONLY — 실 Gemini/AWS 무접촉).

세 표면을 고정한다:

  1. 어댑터 graceful (SP-3) — 무키/API 실패에도 raise 0 + hiddenRecordIds 빈
     배열(전 카드 표시 유지 — fail-open). 반환 형상(verdicts scalar dict) 고정.
  2. 판정 대상 선별 — recordId 없는 record 스킵, 문장 없는 record 스킵,
     감점 큰 순 상한 8 절삭(초과분 미판정 통과).
  3. 보수 후처리 — 보낸 recordId 만 인정(환각 id 무시), 응답 누락 = uncertain
     (표시), mismatch 만 숨김, reason 120자 절삭, praise 교차검증 게이트.

fake client 로 generate_content 를 대체 — google.genai 실호출 0.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from sunity_shared.analysis import spot_check

# ─────────────────────── 공용 fixture ───────────────────────


def _rec(
    record_id: str | None,
    *,
    points: float = -10.0,
    status_line: str | None = "무릎이 기준보다 덜 펴져 있어요",
    cue_line: str | None = "발끝으로 천장을 밀어보세요",
    deviation_source: str = "ipsf_absolute",
) -> dict:
    rec: dict = {
        "criterion": "leg_extension",
        "points": points,
        "deviationSource": deviation_source,
    }
    if record_id is not None:
        rec["recordId"] = record_id
    if status_line is not None:
        rec["statusLine"] = status_line
    if cue_line is not None:
        rec["cueLine"] = cue_line
    return rec


def _frames(n: int = 2) -> list[dict]:
    return [
        {"label": f"프레임 t≈{i}.0s:", "imageBytes": b"fake-jpeg", "mime": "image/jpeg"}
        for i in range(n)
    ]


class FakeResponse:
    def __init__(self, doc: dict):
        self.text = json.dumps(doc, ensure_ascii=False)


class FakeModels:
    def __init__(self, doc: dict | Exception):
        self._doc = doc
        self.calls: list[dict] = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if isinstance(self._doc, Exception):
            raise self._doc
        return FakeResponse(self._doc)


class FakeClient:
    def __init__(self, doc: dict | Exception):
        self.models = FakeModels(doc)


@pytest.fixture
def fake_client(monkeypatch):
    """_ensure_client 를 fake 로 대체 — 반환된 FakeClient 로 응답 주입."""

    def _install(doc: dict | Exception) -> FakeClient:
        client = FakeClient(doc)
        monkeypatch.setattr(spot_check, "_ensure_client", lambda: client)
        return client

    return _install


@pytest.fixture
def no_client(monkeypatch):
    """무키 환경 — client 생성 실패 (RuntimeError)."""
    calls = {"n": 0}

    def _raise():
        calls["n"] += 1
        raise RuntimeError("GEMINI_API_KEY 부재")

    monkeypatch.setattr(spot_check, "_ensure_client", _raise)
    return calls


# ─────────────────────── 1. graceful (SP-3) ───────────────────────


def test_no_key_env_is_noop(no_client):
    """무키 환경 = status 'skipped' + 빈 hiddenRecordIds + praiseMismatch False (비예외)."""
    out = spot_check.run_spot_check(
        _frames(), [_rec("r00:leg_extension")], "잘한 점 문장"
    )
    assert out["status"] == "skipped"
    assert out["hiddenRecordIds"] == []
    assert out["verdicts"] == []
    assert out["praiseMismatch"] is False
    assert out["model"] == spot_check.DEFAULT_SPOTCHECK_MODEL
    assert out["promptVersion"] == spot_check.SPOTCHECK_PROMPT_VERSION


def test_api_failure_is_failed_noop(fake_client):
    """generate_content 예외 = status 'failed' + 빈 숨김 (분석 무훼손, raise 0)."""
    fake_client(RuntimeError("api down"))
    out = spot_check.run_spot_check(_frames(), [_rec("r00:leg_extension")], None)
    assert out["status"] == "failed"
    assert out["hiddenRecordIds"] == []
    assert out["praiseMismatch"] is False


def test_malformed_json_is_failed_noop(fake_client, monkeypatch):
    """비-JSON 응답 = failed no-op (자유 텍스트 파싱 금지 방어)."""
    client = FakeClient({})
    client.models.generate_content = lambda **kw: type(
        "R", (), {"text": "일치하는 것 같습니다"}
    )()
    monkeypatch.setattr(spot_check, "_ensure_client", lambda: client)
    out = spot_check.run_spot_check(_frames(), [_rec("r00:leg_extension")], None)
    assert out["status"] == "failed"
    assert out["hiddenRecordIds"] == []


def test_no_frames_is_skipped(fake_client):
    """프레임 입력 없음 = skipped (판정 불가 — 호출 0)."""
    client = fake_client({"verdicts": [], "praiseVerdict": "not_given"})
    out = spot_check.run_spot_check([], [_rec("r00:leg_extension")], None)
    assert out["status"] == "skipped"
    assert client.models.calls == []  # generate_content 미호출


def test_nothing_to_judge_is_vacuous_done(no_client):
    """판정 대상 0 + praise 없음 = 호출 없이 'done' (client 생성조차 안 함 — 비용 0)."""
    out = spot_check.run_spot_check(_frames(), [], None)
    assert out["status"] == "done"
    assert out["hiddenRecordIds"] == []
    assert no_client["n"] == 0  # _ensure_client 미호출


# ─────────────────────── 2. 판정 대상 선별 ───────────────────────


def test_select_skips_record_without_record_id():
    """recordId 없는 record(legacy) = 스킵 — 판정도 숨김도 안 함 (fail-open)."""
    judged = spot_check.select_judged_records(
        [_rec(None), _rec("r01:split_angle")]
    )
    assert [r["recordId"] for r in judged] == ["r01:split_angle"]


def test_select_skips_record_without_sentence():
    """statusLine/cueLine 둘 다 없는 record = 판정할 문장 없음 — 스킵."""
    judged = spot_check.select_judged_records(
        [
            _rec("r00:leg_extension", status_line=None, cue_line=None),
            _rec("r01:split_angle"),
        ]
    )
    assert [r["recordId"] for r in judged] == ["r01:split_angle"]


def test_select_caps_at_8_by_deduction_size():
    """상한 절삭 — 10건 중 감점 큰 순 8건만 (초과분 미판정 통과)."""
    records = [
        _rec(f"r{i:02d}:leg_extension", points=-(i + 1)) for i in range(10)
    ]
    judged = spot_check.select_judged_records(records)
    assert len(judged) == spot_check.SPOTCHECK_MAX_RECORDS == 8
    # 감점 큰 순 = points 절대값 내림차순 (r09 가 -10 으로 최대).
    assert judged[0]["recordId"] == "r09:leg_extension"
    excluded = {"r00:leg_extension", "r01:leg_extension"}
    assert excluded.isdisjoint({r["recordId"] for r in judged})


def test_select_handles_non_list_and_non_dict():
    assert spot_check.select_judged_records(None) == []
    assert spot_check.select_judged_records("bogus") == []
    assert spot_check.select_judged_records([1, None, "x"]) == []


# ─────────────────────── 3. done 경로 — 보수 후처리 ───────────────────────


def test_mismatch_hides_and_shape_is_scalar_dict(fake_client):
    """mismatch 만 hiddenRecordIds — verdicts 는 {recordId, verdict, reason} scalar dict."""
    fake_client(
        {
            "verdicts": [
                {
                    "recordId": "r00:leg_extension",
                    "verdict": "mismatch",
                    "reason": "모든 프레임에서 무릎이 완전히 펴져 있습니다",
                },
                {
                    "recordId": "r01:split_angle",
                    "verdict": "match",
                    "reason": "다리 벌림이 기준보다 좁게 보입니다",
                },
            ],
            "praiseVerdict": "not_given",
        }
    )
    records = [
        _rec("r00:leg_extension", points=-20),
        _rec("r01:split_angle", points=-10),
    ]
    out = spot_check.run_spot_check(_frames(), records, None)
    assert out["status"] == "done"
    assert out["hiddenRecordIds"] == ["r00:leg_extension"]
    assert len(out["verdicts"]) == 2
    for v in out["verdicts"]:
        assert set(v.keys()) == {"recordId", "verdict", "reason"}
        for value in v.values():
            assert isinstance(value, str)  # scalar only (Firestore flat)
    assert out["verdicts"][0]["verdict"] == "mismatch"
    assert out["verdicts"][1]["verdict"] == "match"


def test_omitted_record_defaults_to_uncertain(fake_client):
    """모델이 응답에서 누락한 record = uncertain (표시 유지 — 과숨김 방지)."""
    fake_client({"verdicts": [], "praiseVerdict": "not_given"})
    out = spot_check.run_spot_check(
        _frames(), [_rec("r00:leg_extension")], None
    )
    assert out["status"] == "done"
    assert out["hiddenRecordIds"] == []
    assert out["verdicts"][0]["verdict"] == "uncertain"


def test_hallucinated_record_id_is_ignored(fake_client):
    """보낸 적 없는 recordId 판정 = 무시 (환각 id 가 숨김 권한을 얻지 못함)."""
    fake_client(
        {
            "verdicts": [
                {"recordId": "r99:fake", "verdict": "mismatch", "reason": "환각"},
            ],
            "praiseVerdict": "not_given",
        }
    )
    out = spot_check.run_spot_check(_frames(), [_rec("r00:leg_extension")], None)
    assert out["hiddenRecordIds"] == []
    assert [v["recordId"] for v in out["verdicts"]] == ["r00:leg_extension"]


def test_invalid_verdict_value_defaults_to_uncertain(fake_client):
    """enum 밖 verdict 값 = uncertain 강등 (표시)."""
    fake_client(
        {
            "verdicts": [
                {"recordId": "r00:leg_extension", "verdict": "hide", "reason": "x"},
            ],
            "praiseVerdict": "not_given",
        }
    )
    out = spot_check.run_spot_check(_frames(), [_rec("r00:leg_extension")], None)
    assert out["verdicts"][0]["verdict"] == "uncertain"
    assert out["hiddenRecordIds"] == []


def test_reason_clipped_to_120(fake_client):
    fake_client(
        {
            "verdicts": [
                {
                    "recordId": "r00:leg_extension",
                    "verdict": "match",
                    "reason": "가" * 500,
                },
            ],
            "praiseVerdict": "not_given",
        }
    )
    out = spot_check.run_spot_check(_frames(), [_rec("r00:leg_extension")], None)
    assert len(out["verdicts"][0]["reason"]) == 120


def test_praise_mismatch_gate(fake_client):
    """praise 전달 + praiseVerdict mismatch = True. record 숨김과 독립."""
    fake_client(
        {
            "verdicts": [
                {"recordId": "r00:leg_extension", "verdict": "match", "reason": "ok"},
            ],
            "praiseVerdict": "mismatch",
        }
    )
    out = spot_check.run_spot_check(
        _frames(), [_rec("r00:leg_extension")], "안정감이 좋아요"
    )
    assert out["praiseMismatch"] is True
    assert out["hiddenRecordIds"] == []


def test_praise_absent_never_mismatch(fake_client):
    """praise 미전달이면 모델이 뭐라 하든 praiseMismatch False."""
    fake_client({"verdicts": [], "praiseVerdict": "mismatch"})
    out = spot_check.run_spot_check(_frames(), [_rec("r00:leg_extension")], None)
    assert out["praiseMismatch"] is False


def test_praise_only_call_without_records(fake_client):
    """record 0건 + praise 존재 = praise 만 검수하는 1콜 (success 멤버 경로)."""
    client = fake_client({"verdicts": [], "praiseVerdict": "match"})
    out = spot_check.run_spot_check(_frames(), [], "이 부분은 잘 해냈어요")
    assert out["status"] == "done"
    assert out["praiseMismatch"] is False
    assert len(client.models.calls) == 1


def test_single_call_per_analysis(fake_client):
    """분석당 1콜 고정 — records 여러 건이어도 generate_content 1회."""
    client = fake_client({"verdicts": [], "praiseVerdict": "not_given"})
    records = [_rec(f"r{i:02d}:leg_extension", points=-i - 1) for i in range(5)]
    spot_check.run_spot_check(_frames(), records, "칭찬")
    assert len(client.models.calls) == 1


def test_comparison_record_marked_in_prompt(fake_client):
    """비교-측정 record(deviationSource != ipsf_absolute)는 프롬프트에 마커 부착."""
    client = fake_client({"verdicts": [], "praiseVerdict": "not_given"})
    records = [
        _rec("r00:leg_extension", deviation_source="ipsf_absolute"),
        _rec("r01:angle_vs_reference__left_knee", deviation_source="reference_relative"),
    ]
    spot_check.run_spot_check(_frames(), records, None)
    prompt = client.models.calls[0]["contents"][-1]
    lines = {
        line.split("]")[0].lstrip("- ["): line
        for line in prompt.splitlines()
        if line.startswith("- [")
    }
    assert lines["r01:angle_vs_reference__left_knee"].endswith("(비교 측정)")
    assert not lines["r00:leg_extension"].endswith("(비교 측정)")


# ─────────────────────── lazy import 규율 ───────────────────────


def test_no_toplevel_google_genai_import():
    """google.genai top-level import 부재 — lazy 만 (D-16, 소스 단언 관례)."""
    source = Path(spot_check.__file__).read_text(encoding="utf-8")
    # 함수 밖(들여쓰기 0) 의 google import 금지.
    assert not re.search(
        r"^(from google|import google)", source, flags=re.MULTILINE
    )


# ═══════════════ Task 2 — 계약 validator + 사후 스테이지 배선 ═══════════════

import importlib.util
import sys

import numpy as np

from sunity_shared import firestore_admin, models

_BACKEND = Path(__file__).resolve().parents[2]


def _load_module(name: str, path: Path):
    """pipeline app.py 파일 경로 spec 로드 (고유 모듈명 — test_coach_audio 관례)."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def papp():
    """pipeline app — spot_check 사후 스테이지 소유 모듈."""
    return _load_module(
        "pipeline_app_phase32_spot_check",
        _BACKEND / "functions" / "pipeline" / "app.py",
    )


def _payload(**overrides) -> dict:
    base = {
        "status": "done",
        "hiddenRecordIds": [],
        "verdicts": [],
        "praiseMismatch": False,
        "model": "gemini-3.1-pro-preview",
        "promptVersion": "v1.0",
    }
    base.update(overrides)
    return base


# ─────────────────────── _validate_spot_check ───────────────────────


def test_validator_accepts_done_with_backed_hidden():
    firestore_admin._validate_spot_check(
        _payload(
            hiddenRecordIds=["r00:leg_extension"],
            verdicts=[
                {
                    "recordId": "r00:leg_extension",
                    "verdict": "mismatch",
                    "reason": "명백 반증",
                },
                {"recordId": "r01:split_angle", "verdict": "match", "reason": "ok"},
            ],
        )
    )


def test_validator_accepts_skipped_and_failed_noop():
    firestore_admin._validate_spot_check(_payload(status="skipped"))
    firestore_admin._validate_spot_check(_payload(status="failed"))


def test_validator_rejects_bad_keys_status_and_verdict():
    with pytest.raises(ValueError):
        firestore_admin._validate_spot_check(_payload(extra="x"))
    with pytest.raises(ValueError):
        firestore_admin._validate_spot_check(_payload(status="pending"))
    with pytest.raises(ValueError):
        firestore_admin._validate_spot_check(
            _payload(
                verdicts=[
                    {"recordId": "r00:x", "verdict": "hide", "reason": ""},
                ]
            )
        )


def test_validator_rejects_orphan_hidden_id():
    """숨김-정합 불변식 — mismatch verdict 없는 숨김 id 거부 (T-32-30)."""
    with pytest.raises(ValueError, match="mismatch verdict 없는"):
        firestore_admin._validate_spot_check(
            _payload(
                hiddenRecordIds=["r00:leg_extension"],
                verdicts=[
                    {
                        "recordId": "r00:leg_extension",
                        "verdict": "uncertain",
                        "reason": "",
                    },
                ],
            )
        )


def test_validator_rejects_over_limits_and_nested():
    over = [
        {"recordId": f"r{i:02d}:x", "verdict": "match", "reason": ""}
        for i in range(models.SPOT_CHECK_MAX_VERDICTS + 1)
    ]
    with pytest.raises(ValueError, match="초과"):
        firestore_admin._validate_spot_check(_payload(verdicts=over))
    with pytest.raises(ValueError, match="120"):
        firestore_admin._validate_spot_check(
            _payload(
                verdicts=[
                    {"recordId": "r00:x", "verdict": "match", "reason": "가" * 121},
                ]
            )
        )
    with pytest.raises(TypeError):
        firestore_admin._validate_spot_check(
            _payload(
                verdicts=[
                    {"recordId": "r00:x", "verdict": "match", "reason": {"a": 1}},
                ]
            )
        )
    with pytest.raises(TypeError):
        firestore_admin._validate_spot_check(_payload(praiseMismatch="yes"))


def test_update_writes_single_field_path(monkeypatch):
    """update_analysis_spot_check = result.spotCheck 단일 field-path 부분 갱신."""
    captured: list[dict] = []

    class FakeDoc:
        def update(self, fields: dict):
            captured.append(fields)

    monkeypatch.setattr(firestore_admin, "_doc", lambda path: FakeDoc())
    firestore_admin.update_analysis_spot_check("u1", "a" * 32, _payload())
    assert len(captured) == 1
    keys = set(captured[0].keys())
    assert keys == {"result.spotCheck", "updatedAt"}  # 그 외 result.* 사후 변경 0


def test_adapter_models_lockstep():
    """어댑터 상수 ↔ models 계약 상수 drift 차단."""
    assert tuple(spot_check._ALLOWED_VERDICTS) == models.SPOT_CHECK_VERDICTS
    assert spot_check.SPOTCHECK_MAX_RECORDS == models.SPOT_CHECK_MAX_VERDICTS
    assert spot_check._REASON_MAX_LEN == models.SPOT_CHECK_REASON_MAX_LEN


# ─────────────────────── _build_spot_check_video_ref ───────────────────────


def _fake_frames(n: int = 20) -> np.ndarray:
    return np.zeros((n, 24, 24, 3), dtype=np.uint8)


def test_video_ref_budget_and_shape(papp):
    """예산 = clamp(2×record 수, 4..8) — label + JPEG bytes."""
    angles = np.full((20, 8), 150.0)
    judged = [_rec(f"r{i:02d}:leg_extension") for i in range(3)]
    ref = papp._build_spot_check_video_ref(judged, angles, None, _fake_frames())
    assert 1 <= len(ref) <= 6  # 2×3=6 상한 (window 폭에 따라 중복 제거 가능)
    for f in ref:
        assert f["mime"] == "image/jpeg"
        # 초 라벨(fps 가용) 또는 인덱스 라벨(로컬 — fps 소스 부재 폴백) 둘 다 허용.
        assert f["label"].startswith("프레임 ")
        assert isinstance(f["imageBytes"], bytes) and len(f["imageBytes"]) > 0


def test_video_ref_caps_at_max_frames(papp):
    angles = np.full((60, 8), 150.0)
    judged = [_rec(f"r{i:02d}:leg_extension") for i in range(8)]
    ref = papp._build_spot_check_video_ref(judged, angles, None, _fake_frames(60))
    assert len(ref) <= spot_check.SPOTCHECK_MAX_FRAMES == 8


def test_video_ref_none_frames_is_empty(papp):
    assert papp._build_spot_check_video_ref([], np.zeros((5, 8)), None, None) == []


def test_video_ref_window_failure_falls_back_whole_clip(papp, monkeypatch):
    """_select_window 예외 = 전 구간 폴백 (graceful — 빈 입력 아님)."""
    monkeypatch.setattr(
        papp.dimensions,
        "_select_window",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("window fail")),
    )
    angles = np.full((20, 8), 150.0)
    ref = papp._build_spot_check_video_ref(
        [_rec("r00:leg_extension")], angles, None, _fake_frames()
    )
    assert len(ref) >= 1


# ─────────────────────── _run_deferred_spot_check ───────────────────────


def _result_with_records(praise: bool = True) -> dict:
    result = {
        "deductionBreakdown": {
            "baseline": 100,
            "records": [
                _rec("r00:leg_extension", points=-20),
                _rec("r01:split_angle", points=-10),
            ],
            "final": 70,
        },
    }
    if praise:
        result["summaryPraise"] = {
            "source": "clean_dimension",
            "headline": "이 부분은 기준에 맞게 잘 해냈어요",
        }
    return result


@pytest.fixture
def spot_updates(monkeypatch):
    """update_analysis_spot_check 캡처 — 실 validator 경유 (coach_audio 관례)."""
    captured: list[dict] = []

    def _update(uid, analysis_id, payload):
        firestore_admin._validate_spot_check(payload)
        captured.append({"uid": uid, "analysis_id": analysis_id, **payload})

    monkeypatch.setattr(firestore_admin, "update_analysis_spot_check", _update)
    return captured


def test_deferred_passes_praise_headline_and_stores(papp, spot_updates, monkeypatch):
    """run_spot_check 호출 인자에 summaryPraise.headline 전달 + 판정 저장."""
    calls: list[dict] = []

    def _fake_run(video_ref, records, praise_headline=None):
        calls.append(
            {"n_frames": len(video_ref), "praise": praise_headline}
        )
        return {
            "status": "done",
            "hiddenRecordIds": ["r00:leg_extension"],
            "verdicts": [
                {
                    "recordId": "r00:leg_extension",
                    "verdict": "mismatch",
                    "reason": "명백 반증",
                },
                {"recordId": "r01:split_angle", "verdict": "match", "reason": "ok"},
            ],
            "praiseMismatch": True,
            "model": "gemini-3.1-pro-preview",
            "promptVersion": "v1.0",
        }

    from sunity_shared.analysis import spot_check as sc_mod

    monkeypatch.setattr(sc_mod, "run_spot_check", _fake_run)

    papp._run_deferred_spot_check(
        result=_result_with_records(),
        angles=np.full((20, 8), 150.0),
        profile=None,
        frames=_fake_frames(),
        uid="u1",
        analysis_id="a" * 32,
    )
    assert calls[0]["praise"] == "이 부분은 기준에 맞게 잘 해냈어요"
    assert calls[0]["n_frames"] >= 1
    assert len(spot_updates) == 1
    assert spot_updates[0]["hiddenRecordIds"] == ["r00:leg_extension"]
    assert spot_updates[0]["praiseMismatch"] is True


def test_deferred_failure_marks_failed(papp, spot_updates, monkeypatch):
    """스테이지 내부 예외 = failed 마킹 (분석 무훼손 — raise 0)."""
    from sunity_shared.analysis import spot_check as sc_mod

    def _boom(*a, **k):
        raise RuntimeError("stage boom")

    monkeypatch.setattr(sc_mod, "run_spot_check", _boom)
    papp._run_deferred_spot_check(
        result=_result_with_records(),
        angles=np.full((20, 8), 150.0),
        profile=None,
        frames=_fake_frames(),
        uid="u1",
        analysis_id="a" * 32,
    )
    assert len(spot_updates) == 1
    assert spot_updates[0]["status"] == "failed"
    assert spot_updates[0]["hiddenRecordIds"] == []


def test_deferred_double_failure_never_raises(papp, monkeypatch):
    """failed 마킹 write 실패까지 겹쳐도 재raise 0 (spotCheck 부재 = fail-open)."""
    from sunity_shared.analysis import spot_check as sc_mod

    monkeypatch.setattr(
        sc_mod, "run_spot_check", lambda *a, **k: (_ for _ in ()).throw(RuntimeError())
    )
    monkeypatch.setattr(
        firestore_admin,
        "update_analysis_spot_check",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("write down")),
    )
    papp._run_deferred_spot_check(
        result=_result_with_records(),
        angles=np.full((20, 8), 150.0),
        profile=None,
        frames=_fake_frames(),
        uid="u1",
        analysis_id="a" * 32,
    )  # 예외 전파 없으면 통과


def test_deferred_no_praise_none(papp, spot_updates, monkeypatch):
    """summaryPraise 부재 doc = praise_headline None 전달."""
    calls: list[dict] = []
    from sunity_shared.analysis import spot_check as sc_mod

    def _fake_run(video_ref, records, praise_headline=None):
        calls.append({"praise": praise_headline})
        return {
            "status": "done",
            "hiddenRecordIds": [],
            "verdicts": [],
            "praiseMismatch": False,
            "model": "m",
            "promptVersion": "v1.0",
        }

    monkeypatch.setattr(sc_mod, "run_spot_check", _fake_run)
    papp._run_deferred_spot_check(
        result=_result_with_records(praise=False),
        angles=np.full((20, 8), 150.0),
        profile=None,
        frames=_fake_frames(),
        uid="u1",
        analysis_id="a" * 32,
    )
    assert calls[0]["praise"] is None
    assert spot_updates[0]["status"] == "done"


# ─────────────────────── 코드 순서 (사후 스테이지 보장) ───────────────────────


def test_spot_check_stage_after_complete_and_fault_zoom():
    """spot_check _stage 블록이 firestore_complete·fault_zoom **이후** 위치.

    동기 채점 경로(complete 이전) 신규 외부 호출 0 을 소스 순서로 고정한다
    (플랜 acceptance — 속도 예산 구조 보호).
    """
    source = (_BACKEND / "functions" / "pipeline" / "app.py").read_text(
        encoding="utf-8"
    )
    complete_pos = source.index('"firestore_complete"')
    fault_zoom_pos = source.index(
        "_run_deferred_fault_zoom(\n                    render="
    )
    stage_pos = source.index('_stage(timings_ms, analysis_id, "spot_check")')
    deferred_pos = source.index("_run_deferred_spot_check(\n                result=")
    assert complete_pos < stage_pos
    assert fault_zoom_pos < stage_pos
    assert stage_pos < deferred_pos
    # 동기 경로에 spot_check 외부 호출이 없다 — run_spot_check 호출 지점은 정확히
    # 1곳 (_run_deferred_spot_check 내부, complete 이후).
    assert source.count("run_spot_check(") == 1
