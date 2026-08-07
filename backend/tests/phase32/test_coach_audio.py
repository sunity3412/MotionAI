"""Plan 32-16 — 재생 중 큐 오디오 (D-18 B안, Polly 사후 합성) 테스트.

세 표면을 고정한다 (LOCAL ONLY — 실 Firestore/AWS/Polly 무접촉):

  1. 합성 스테이지 graceful (SP-3) — Polly 무자격/합성 실패에도 재raise 0,
     status done 유지(사후 스테이지가 분석 status 를 만지지 않음), 자막 경로
     (records cueLine) 무영향, coachAudio.status='failed' 방출. 부분 실패는
     성공분만 items 로 done.
  2. playback-url asset 가드 (H-02) — 서버 구성 canonical key + 저장 key exact
     비교로만 발급. stale key·타 uid recordId·형식 위반은 404/400, 기존 asset
     종류(correctedPose/rotation) 경로 무회귀.
  3. coachAudio 형상 validator (scalar dict 배열) + 채점 무접촉(사후) 회귀 가드.

pipeline app.py / playback-url app.py 는 파일 경로 spec 로드(고유 모듈명) —
tests/pipeline 의 'app' 모듈명 충돌 회피 (test_pipeline_emission 관례).
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from sunity_shared import firestore_admin, models
from sunity_shared.s3keys import build_coach_audio_key

_BACKEND = Path(__file__).resolve().parents[2]

UID = "u1"
OTHER_UID = "u2"
ANALYSIS_ID = "a" * 32
RECORD_ID = "r00:leg_extension"
RECORD_ID_2 = "r01:split_angle"
AUDIO_KEY = build_coach_audio_key(UID, ANALYSIS_ID, RECORD_ID)
AUDIO_KEY_2 = build_coach_audio_key(UID, ANALYSIS_ID, RECORD_ID_2)


# ─────────────────────── 모듈 로드 (고유 이름 — 관례) ───────────────────────


def _load_module(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def papp():
    """pipeline app — coach_audio 사후 스테이지 소유 모듈."""
    return _load_module(
        "pipeline_app_phase32_coach_audio",
        _BACKEND / "functions" / "pipeline" / "app.py",
    )


@pytest.fixture(scope="module")
def purl():
    """playback-url app — asset 재서명 Lambda."""
    os.environ.setdefault("VIDEO_BUCKET", "test-bucket")
    return _load_module(
        "playback_url_phase32_coach_audio",
        _BACKEND / "functions" / "playback-url" / "app.py",
    )


# ─────────────────────── 공용 fake ───────────────────────


class FakeAudioStream:
    def read(self) -> bytes:
        return b"ID3fake-mp3-bytes"


class FakePolly:
    """합성 호출 기록 + 주입 실패. record_id 별 선택 실패 가능."""

    def __init__(self, fail_texts: set[str] | None = None, fail_all: bool = False):
        self.calls: list[dict] = []
        self.fail_texts = fail_texts or set()
        self.fail_all = fail_all

    def synthesize_speech(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail_all or kwargs.get("Text") in self.fail_texts:
            raise RuntimeError("polly failure (injected)")
        return {"AudioStream": FakeAudioStream()}


class FakePipelineS3:
    def __init__(self, fail: bool = False):
        self.puts: list[dict] = []
        self.fail = fail

    def put_object(self, **kwargs):
        if self.fail:
            raise RuntimeError("s3 put failure (injected)")
        self.puts.append(kwargs)
        return {}


@pytest.fixture
def audio_updates(monkeypatch):
    """update_analysis_coach_audio 캡처 — validator 는 실제로 통과시킨다."""
    captured: list[dict] = []

    def _update(uid, analysis_id, items, status):
        payload = {"status": status, "items": list(items or [])}
        firestore_admin._validate_coach_audio(payload)  # 실 validator 경유
        captured.append({"uid": uid, "analysis_id": analysis_id, **payload})

    monkeypatch.setattr(firestore_admin, "update_analysis_coach_audio", _update)
    return captured


def _result_with_records() -> dict:
    """32-09 방출 형상의 최소 재현 — 채점 필드 + cueLine 보유 records 2건 +
    fail-closed record 1건(cueLine 부재 — 오디오 대상 아님)."""
    return {
        "overallScore": 55,
        "verdict": "needs_work",
        "dimensionScores": {"angle": 55, "line": 80, "stability": 90},
        "deductionBreakdown": {
            "baseline": 100,
            "final": 55,
            "records": [
                {
                    "recordId": RECORD_ID,
                    "criterion": "leg_extension",
                    "cueLine": "발끝으로 천장을 길게 밀어낸다는 느낌으로 다리를 쭉 뻗어보세요.",
                    "points": -20,
                },
                {
                    "recordId": RECORD_ID_2,
                    "criterion": "split_angle",
                    "cueLine": "양다리를 반대 방향으로 길게 벌린다는 느낌으로 유지해보세요.",
                    "points": -15,
                },
                {
                    # fail-closed 조합 (32-05) — cueLine 생략 record.
                    "recordId": "r02:angle_vs_reference__left_shoulder",
                    "criterion": "angle_vs_reference__left_shoulder",
                    "points": -10,
                },
            ],
        },
    }


# ═══════════════════ 1. 합성 스테이지 (pipeline) ═══════════════════


def test_synthesis_success_emits_items_with_record_id_join(
    papp, audio_updates, monkeypatch
):
    """정상 합성 — cueLine 보유 record 만, recordId 조인 키 + canonical key 저장."""
    polly = FakePolly()
    s3 = FakePipelineS3()
    monkeypatch.setattr(papp, "_get_polly_client", lambda: polly)
    monkeypatch.setattr(papp, "_s3", s3)

    papp._run_deferred_coach_audio(
        result=_result_with_records(), uid=UID, analysis_id=ANALYSIS_ID, bucket="b"
    )

    assert len(audio_updates) == 1
    upd = audio_updates[0]
    assert upd["status"] == models.COACH_AUDIO_STATUS_DONE
    assert upd["items"] == [
        {"recordId": RECORD_ID, "key": AUDIO_KEY},
        {"recordId": RECORD_ID_2, "key": AUDIO_KEY_2},
    ]
    # fail-closed record(cueLine 부재)는 합성 호출 자체가 없다.
    assert len(polly.calls) == 2
    # S3 저장 = canonical key + audio/mpeg (s3keys 단일 출처).
    assert [p["Key"] for p in s3.puts] == [AUDIO_KEY, AUDIO_KEY_2]
    assert all(p["ContentType"] == "audio/mpeg" for p in s3.puts)
    # 목표절·statusLine 없는 record — 조립식이 항등이라 cueLine 그대로 합성
    # (자막 조립 미러의 fail-closed 경로. 조립 본체는 아래 speech_text 테스트).
    assert polly.calls[0]["Text"].startswith("발끝으로")


def test_speech_text_mirrors_subtitle_composition(papp):
    """debug va-subtitle-audio-mismatch — 합성 문장 = 재생 중 자막과 같은 문장.

    앱 composeCueSubtitleKo(deductionSheet.ts) 미러 고정: statusLine(결함) +
    목표절 제거 actionLine. 한쪽만 바뀌면 음성·자막이 다시 갈라진다 (mrg
    SUMMARY 미검증 #4 의 재발 방지 핀).
    """
    goal_cue = (
        "목표는 거꾸로 매달린 채 윗다리를 폴을 따라 곧게 뽑는 자세예요. "
        "팔꿈치로 폴을 단단히 감은(엘보 그립) 채, 그 각을 기준 자세에 겹쳐 맞춰보세요"
    )
    status = "오른쪽 팔꿈치 각도가 엘보 트위스트 기준 자세와 차이가 있어요"

    # 본체: statusLine + 목표절 제거 행동절 — 자막 문자열과 동일.
    assert papp._coach_audio_speech_text(
        {"cueLine": goal_cue, "statusLine": status}
    ) == (
        f"{status} 팔꿈치로 폴을 단단히 감은(엘보 그립) 채, "
        "그 각을 기준 자세에 겹쳐 맞춰보세요"
    )
    # 음성 도입이 목표절이 아니어야 한다 (V-A 불일치의 본체였던 문장).
    assert not papp._coach_audio_speech_text(
        {"cueLine": goal_cue, "statusLine": status}
    ).startswith("목표는")

    # statusLine 부재 — 행동절만 (앱: status 없으면 action 단독).
    assert papp._coach_audio_speech_text({"cueLine": goal_cue}) == (
        "팔꿈치로 폴을 단단히 감은(엘보 그립) 채, 그 각을 기준 자세에 겹쳐 맞춰보세요"
    )

    # fail-closed 3종 — splitGoalClause 와 동일 (원문 그대로).
    common_cue = "발끝으로 천장을 길게 밀어낸다는 느낌으로 다리를 쭉 뻗어보세요."
    assert papp._cue_action_line(common_cue) == common_cue  # 목표절 접두 없음
    assert papp._cue_action_line("목표는 구분자 없는 문장") == "목표는 구분자 없는 문장"
    assert papp._cue_action_line("목표는 여기서 끝나는 문장이에요. ") == (
        "목표는 여기서 끝나는 문장이에요. "
    )  # 자른 뒤 행동절이 빈 문자열 → 자르지 않음

    # statusLine 이 비문자열/빈 문자열 — 행동절만 (앱 typeof/length 가드 미러).
    assert papp._coach_audio_speech_text(
        {"cueLine": common_cue, "statusLine": ""}
    ) == common_cue
    assert papp._coach_audio_speech_text(
        {"cueLine": common_cue, "statusLine": None}
    ) == common_cue


def test_synthesis_partial_failure_keeps_survivors_done(
    papp, audio_updates, monkeypatch
):
    """record 단위 격리 — 1건 합성 실패는 그 record 만 생략, 나머지는 done."""
    result = _result_with_records()
    fail_text = result["deductionBreakdown"]["records"][0]["cueLine"]
    monkeypatch.setattr(
        papp, "_get_polly_client", lambda: FakePolly(fail_texts={fail_text})
    )
    monkeypatch.setattr(papp, "_s3", FakePipelineS3())

    papp._run_deferred_coach_audio(
        result=result, uid=UID, analysis_id=ANALYSIS_ID, bucket="b"
    )

    upd = audio_updates[0]
    assert upd["status"] == models.COACH_AUDIO_STATUS_DONE
    assert upd["items"] == [{"recordId": RECORD_ID_2, "key": AUDIO_KEY_2}]


def test_synthesis_total_failure_marks_failed_and_never_raises(
    papp, audio_updates, monkeypatch
):
    """graceful (SP-3) — Polly 전면 실패(무자격 등)에도 재raise 0 + failed 방출 +
    자막 경로(records cueLine) 무영향."""
    result = _result_with_records()
    before = copy.deepcopy(result)
    monkeypatch.setattr(papp, "_get_polly_client", lambda: FakePolly(fail_all=True))
    monkeypatch.setattr(papp, "_s3", FakePipelineS3())

    papp._run_deferred_coach_audio(
        result=result, uid=UID, analysis_id=ANALYSIS_ID, bucket="b"
    )  # 예외 전파 없음 = 분석(이미 complete) 무훼손

    upd = audio_updates[0]
    assert upd["status"] == models.COACH_AUDIO_STATUS_FAILED
    assert upd["items"] == []
    # 자막 경로 무영향 — result(records cueLine 포함) 바이트 불변.
    assert result == before


def test_synthesis_no_cue_records_emits_done_empty(papp, audio_updates, monkeypatch):
    """결함 0(무결함 분석) = done + [] — 부재(legacy)와 구분되는 명시적 '큐 없음'."""
    monkeypatch.setattr(papp, "_get_polly_client", lambda: FakePolly())
    monkeypatch.setattr(papp, "_s3", FakePipelineS3())

    papp._run_deferred_coach_audio(
        result={"overallScore": 100, "deductionBreakdown": {"records": []}},
        uid=UID, analysis_id=ANALYSIS_ID, bucket="b",
    )

    assert audio_updates[0]["status"] == models.COACH_AUDIO_STATUS_DONE
    assert audio_updates[0]["items"] == []


def test_synthesis_update_write_failure_swallowed(papp, monkeypatch):
    """done write 실패 → failed 마킹 시도, 그것도 실패해도 재raise 0 (fault_zoom 규율)."""
    monkeypatch.setattr(papp, "_get_polly_client", lambda: FakePolly())
    monkeypatch.setattr(papp, "_s3", FakePipelineS3())

    def _always_fail(*_a, **_k):
        raise RuntimeError("firestore write failure (injected)")

    monkeypatch.setattr(firestore_admin, "update_analysis_coach_audio", _always_fail)

    # 어떤 예외도 전파되지 않아야 한다 — 분석은 이미 complete.
    papp._run_deferred_coach_audio(
        result=_result_with_records(), uid=UID, analysis_id=ANALYSIS_ID, bucket="b"
    )


def test_synthesis_stage_does_not_touch_scoring(papp, audio_updates, monkeypatch):
    """채점 무접촉(사후) 회귀 가드 — 스테이지 전/후 result 딥 동등 (점수·verdict·
    records 포함 어떤 키도 추가/변형 없음. coachAudio 는 doc 부분 갱신으로만)."""
    result = _result_with_records()
    before = copy.deepcopy(result)
    monkeypatch.setattr(papp, "_get_polly_client", lambda: FakePolly())
    monkeypatch.setattr(papp, "_s3", FakePipelineS3())

    papp._run_deferred_coach_audio(
        result=result, uid=UID, analysis_id=ANALYSIS_ID, bucket="b"
    )

    assert result == before  # result 에 coachAudio 를 심지 않는다 (사후 partial update 전용)
    assert audio_updates  # 방출은 update helper 경유로만


# ═══════════════════ 2. playback-url asset 가드 (H-02) ═══════════════════


class FakeUrlS3:
    def __init__(self):
        self.signed: list[dict] = []

    def generate_presigned_url(self, _op, Params=None, ExpiresIn=None):  # noqa: N803
        self.signed.append({"Params": Params, "ExpiresIn": ExpiresIn})
        return f"https://s3.example/signed?k={Params['Key']}"


@pytest.fixture
def url_s3(purl, monkeypatch):
    fake = FakeUrlS3()
    monkeypatch.setattr(purl, "_s3", fake)
    return fake


@pytest.fixture
def url_auth(purl, monkeypatch):
    monkeypatch.setattr(purl, "verify_request", lambda _event: UID)


@pytest.fixture
def analyses(purl, monkeypatch):
    store: dict[tuple[str, str], dict] = {}
    monkeypatch.setattr(
        purl.firestore_admin, "get_analysis", lambda uid, aid: store.get((uid, aid))
    )
    return store


def _call(purl, **body) -> dict:
    event = {"body": json.dumps(body), "headers": {"authorization": "Bearer t"}}
    return purl.lambda_handler(event, None)


def _coach_audio_doc(status: str = "done", items: list | None = None) -> dict:
    default_items = [{"recordId": RECORD_ID, "key": AUDIO_KEY}]
    return {"result": {"coachAudio": {"status": status, "items": default_items if items is None else items}}}


def test_asset_coach_audio_fresh_sign(purl, url_s3, url_auth, analyses):
    """done + 서버 구성 canonical == 저장 key → 1시간 presign + audio/mpeg."""
    analyses[(UID, ANALYSIS_ID)] = _coach_audio_doc()

    resp = _call(purl, analysisId=ANALYSIS_ID, asset="coachAudio", recordId=RECORD_ID)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert set(body) == {"playbackUrl", "expiresInSec"}  # key 노출 표면 없음 (H-05)
    assert body["expiresInSec"] == 3600
    assert url_s3.signed[0]["Params"]["Key"] == AUDIO_KEY
    assert url_s3.signed[0]["Params"]["ResponseContentType"] == "audio/mpeg"
    assert url_s3.signed[0]["ExpiresIn"] == 3600


def test_asset_coach_audio_stale_key_404(purl, url_s3, url_auth, analyses):
    """M2-01 핵심 — 저장 key 가 canonical 과 exact 불일치(stale/오염)면 서명 0."""
    analyses[(UID, ANALYSIS_ID)] = _coach_audio_doc(
        items=[{"recordId": RECORD_ID, "key": f"results/{UID}/{ANALYSIS_ID}/coach_audio_old.mp3"}]
    )

    resp = _call(purl, analysisId=ANALYSIS_ID, asset="coachAudio", recordId=RECORD_ID)

    assert resp["statusCode"] == 404
    assert url_s3.signed == []


def test_asset_coach_audio_other_uid_key_404(purl, url_s3, url_auth, analyses):
    """타 uid 산출물 key 가 (오염으로) 내 doc 에 실려도 — 토큰 uid 로 구성한
    canonical 과 불일치 → 404. prefix 부분일치 서명이 없음을 고정."""
    other_key = build_coach_audio_key(OTHER_UID, ANALYSIS_ID, RECORD_ID)
    analyses[(UID, ANALYSIS_ID)] = _coach_audio_doc(
        items=[{"recordId": RECORD_ID, "key": other_key}]
    )

    resp = _call(purl, analysisId=ANALYSIS_ID, asset="coachAudio", recordId=RECORD_ID)

    assert resp["statusCode"] == 404
    assert url_s3.signed == []


def test_asset_coach_audio_failed_status_404(purl, url_s3, url_auth, analyses):
    """status failed 인데 이전 성공분 items 가 남아 있어도 서명 불가 (M2-01)."""
    analyses[(UID, ANALYSIS_ID)] = _coach_audio_doc(status="failed")

    assert _call(purl, analysisId=ANALYSIS_ID, asset="coachAudio", recordId=RECORD_ID)[
        "statusCode"
    ] == 404
    assert url_s3.signed == []


def test_asset_coach_audio_absent_field_404(purl, url_s3, url_auth, analyses):
    """legacy doc(coachAudio 부재) / 미등재 recordId → 동일 404 (leak 0)."""
    analyses[(UID, ANALYSIS_ID)] = {"result": {}}
    assert _call(purl, analysisId=ANALYSIS_ID, asset="coachAudio", recordId=RECORD_ID)[
        "statusCode"
    ] == 404

    analyses[(UID, ANALYSIS_ID)] = _coach_audio_doc(items=[])
    assert _call(purl, analysisId=ANALYSIS_ID, asset="coachAudio", recordId=RECORD_ID)[
        "statusCode"
    ] == 404
    assert url_s3.signed == []


def test_asset_coach_audio_record_id_format_guard_400(purl, url_s3, url_auth, analyses):
    """recordId 형식 화이트리스트 — path injection 류는 key 빌더 도달 전 400."""
    analyses[(UID, ANALYSIS_ID)] = _coach_audio_doc()

    for bad in ("../../etc/passwd", "r0:leg", "r000:leg", "r00:has-dash", "", None, 7):
        resp = _call(purl, analysisId=ANALYSIS_ID, asset="coachAudio", recordId=bad)
        assert resp["statusCode"] == 400, f"recordId={bad!r}"
    assert url_s3.signed == []


def test_asset_visual_kinds_unchanged(purl, url_s3, url_auth, analyses):
    """기존 asset 종류 무회귀 — correctedPose 는 기존 가드 그대로 동작 +
    미지원 asset 은 기존 400 메시지 유지 (바이트 불변 원칙)."""
    joint = "left_knee"
    corrected_key = f"results/{UID}/{ANALYSIS_ID}/corrected_pose_{joint}.png"
    analyses[(UID, ANALYSIS_ID)] = {
        "result": {
            "correctedPoseStatus": "done",
            "correctedPoseKey": corrected_key,
            "correctedPoseJoint": joint,
        }
    }

    resp = _call(purl, analysisId=ANALYSIS_ID, asset="correctedPose")
    assert resp["statusCode"] == 200
    assert url_s3.signed[0]["Params"]["Key"] == corrected_key

    resp = _call(purl, analysisId=ANALYSIS_ID, asset="nonsense")
    assert resp["statusCode"] == 400


# ═══════════════════ 3. 형상 validator + 계약 lockstep ═══════════════════


def test_validator_accepts_canonical_shapes():
    firestore_admin._validate_coach_audio({"status": "done", "items": []})
    firestore_admin._validate_coach_audio(
        {"status": "failed", "items": []}
    )
    firestore_admin._validate_coach_audio(
        {"status": "done", "items": [{"recordId": RECORD_ID, "key": AUDIO_KEY}]}
    )


@pytest.mark.parametrize(
    "bad",
    [
        {"status": "pending", "items": []},  # 미정의 status
        {"status": "done"},  # items 누락
        {"status": "done", "items": [], "extra": 1},  # 여분 키
        {"status": "done", "items": [{"recordId": RECORD_ID}]},  # item key 누락
        {"status": "done", "items": [{"recordId": RECORD_ID, "key": "uploads/evil.mp3"}]},  # prefix 위반
        {"status": "done", "items": [{"recordId": "", "key": AUDIO_KEY}]},  # 빈 recordId
        {"status": "done", "items": [{"recordId": RECORD_ID, "key": AUDIO_KEY, "x": 1}]},  # item 여분 키
        {"status": "done", "items": [{"recordId": RECORD_ID, "key": [AUDIO_KEY]}]},  # nested list
        {"status": "done", "items": [{"recordId": RECORD_ID, "key": {"k": AUDIO_KEY}}]},  # nested dict
        {"status": "done", "items": "not-a-list"},
    ],
)
def test_validator_rejects_malformed(bad):
    with pytest.raises((ValueError, TypeError)):
        firestore_admin._validate_coach_audio(bad)


def test_update_helper_routes_through_validator(monkeypatch):
    """update_analysis_coach_audio 가 write 전에 validator 를 실제로 태운다 —
    오염 items 는 Firestore 에 도달하지 않는다."""
    calls: list[dict] = []

    class FakeDoc:
        def update(self, payload):
            calls.append(payload)

    monkeypatch.setattr(firestore_admin, "_doc", lambda _path: FakeDoc())

    with pytest.raises(ValueError):
        firestore_admin.update_analysis_coach_audio(
            UID, ANALYSIS_ID, [{"recordId": RECORD_ID, "key": "uploads/evil.mp3"}],
            status=models.COACH_AUDIO_STATUS_DONE,
        )
    assert calls == []  # 오염 payload write 0

    firestore_admin.update_analysis_coach_audio(
        UID, ANALYSIS_ID, [{"recordId": RECORD_ID, "key": AUDIO_KEY}],
        status=models.COACH_AUDIO_STATUS_DONE,
    )
    assert len(calls) == 1
    assert calls[0]["result.coachAudio"] == {
        "status": "done",
        "items": [{"recordId": RECORD_ID, "key": AUDIO_KEY}],
    }
    assert set(calls[0]) == {"result.coachAudio", "updatedAt"}  # 단일 field-path + 타임스탬프


def test_contract_lockstep_ts_interface_fields():
    """3-way lockstep 최소 가드 — analysis.ts CoachAudio/CoachAudioItem 필드 집합이
    models.py 상수와 동등 (test_mission_contract_lockstep 관례의 경량판)."""
    ts = (_BACKEND.parent / "app" / "src" / "types" / "analysis.ts").read_text(
        encoding="utf-8"
    )
    assert "export interface CoachAudio {" in ts
    assert "export interface CoachAudioItem {" in ts
    assert "coachAudio?: CoachAudio;" in ts
    # item 필드 집합 = models.COACH_AUDIO_ITEM_KEYS.
    item_block = ts.split("export interface CoachAudioItem {", 1)[1].split("}", 1)[0]
    ts_fields = {
        line.strip().split(":")[0].rstrip("?")
        for line in item_block.splitlines()
        if ":" in line and not line.strip().startswith("//")
    }
    assert ts_fields == set(models.COACH_AUDIO_ITEM_KEYS)
