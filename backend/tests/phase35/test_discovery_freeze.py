"""quick-260814-di7 — 발굴 채택 freeze doc 영속화 + 주입 레이어 + verify discover.

발굴(discover) 채택 순간이 doc `result.discovery.items` 로 영속화되고,
compare_render.build_timeline 이 그것을 읽어 discover freeze 를 추가하며(주입
레이어), compare_verify H 게이트가 discover 를 정식 지원(fail-closed — doc
discovery 에 그 순간이 없으면 FAIL, blanket 면제 없음)함을 합성 fixture 로 핀.

전부 합성 값 (실좌표/동작명/분석 ID 리터럴 0 — rid r02/r07, 임의 초).
스펙 실증본 = quick-260814-chd inject_freeze.py `_install_injection` (사본 delta
→ 정식 경로 승격이 이 테스트의 대상).
"""

from __future__ import annotations

import subprocess

import numpy as np
import pytest

from sunity_shared import firestore_admin, models
from sunity_shared.analysis import compare_render
from sunity_shared.analysis import compare_verify
from sunity_shared.analysis.compare_render import FF, FREEZE_TAIL_S, mp3_duration_s
from sunity_shared.analysis.compare_verify import authenticity_checks
from sunity_shared.analysis.cue_text import coach_audio_speech_text
from sunity_shared.s3keys import build_discover_audio_key

CUE = "목표는 기준 자세예요. 왼쪽 팔꿈치를 곧게 펴 보세요"
STATUS = "왼쪽 팔꿈치 각도가 기준 자세와 차이가 있어요"
DISC_TEXT = "합성 발굴 문장 — 무릎을 편 상태로 회전해 보세요."

_JOINTS17 = (
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
)


# ══════════════════════ 합성 fixture 빌더 ══════════════════════


def _mk_align(user_frames: int = 90, ref_frames: int = 90, fps: float = 15.0) -> dict:
    """최소 합성 align — 전 관절 conf 0.9 / 좌표 0.5 (마커 성립 가능)."""
    kp = np.full((user_frames, len(_JOINTS17), 2), 0.5, dtype=float)
    sc = np.full((user_frames, len(_JOINTS17)), 0.9, dtype=float)
    return {
        "fps": fps,
        "joints17": list(_JOINTS17),
        "userFrames": user_frames,
        "refFrames": ref_frames,
        "userKp": kp.tolist(),
        "userScore": sc.tolist(),
        "userSize": [640, 1080],
        # 등속 user→ref 매핑 (identity) — warp_b/경계 판정 단순화.
        "curveRefSec": (np.arange(user_frames) / fps).tolist(),
        "pairs": {},
    }


def _mk_doc(records=None, discovery=None, items=None) -> dict:
    frames = 60
    doc = {
        "result": {
            "motionAlignment": {"anchors": [0.0, 0.0, 5.0, 5.0]},
            "keypointReport": {
                "joints": ["left_elbow"],
                "frames": frames,
                "fps": 9.0,
                "data": [0.5] * (frames * 1 * 2),
                "confidence": [0.9] * (frames * 1),
            },
            "deductionBreakdown": {"records": records if records is not None else [
                {"recordId": "r02:angle_vs_reference__left_elbow",
                 "criterion": "angle_vs_reference__left_elbow",
                 "atVideoSec": 2.0, "cueLine": CUE, "statusLine": STATUS},
            ]},
            "coachAudio": {"status": "done", "items": items if items is not None else [
                {"recordId": "r02:angle_vs_reference__left_elbow",
                 "key": "results/u1/a1/coach_audio_r02:angle_vs_reference__left_elbow.mp3"},
            ]},
        }
    }
    if discovery is not None:
        doc["result"]["discovery"] = discovery
    return doc


def _disc_item(**over) -> dict:
    base = {
        "rid": "r07", "joint": "left_knee", "userSec": 3.2, "refSec": 2.9,
        "pairSrc": "discover", "text": DISC_TEXT,
        "mp3Key": build_discover_audio_key("u1", "a1", "r07", "left_knee"),
        "adoptedAt": "2026-01-01",
    }
    base.update(over)
    return base


def _silence_mp3(path) -> None:
    subprocess.run(
        [FF, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc",
         "-t", "1", str(path)],
        check=True,
    )


@pytest.fixture
def audio_dir(tmp_path):
    d = tmp_path / "audio"
    d.mkdir()
    _silence_mp3(d / "r02.mp3")
    return d


def _with_discover_mp3(audio_dir, item) -> None:
    _silence_mp3(audio_dir / item["mp3Key"].rsplit("/", 1)[-1])


# ══════════════════════ build_timeline 주입 레이어 ══════════════════════


def test_build_timeline_injects_discover_freeze_fields(audio_dir):
    """discovery items 1건 → pair_src 'discover' freeze 1건, 필드 정확."""
    item = _disc_item()
    _with_discover_mp3(audio_dir, item)
    doc = _mk_doc(discovery={"items": [item]})
    align = _mk_align()
    _, freezes, excluded = compare_render.build_timeline(doc, audio_dir, None, align, None)

    disc = [f for f in freezes if f["pair_src"] == models.DISCOVERY_PAIR_SRC]
    assert len(disc) == 1
    fz = disc[0]
    assert fz["rid"] == "r07"
    assert fz["joint"] == "left_knee"
    assert fz["ut"] == pytest.approx(3.2)
    assert fz["rt"] == pytest.approx(2.9)
    assert fz["text"] == DISC_TEXT
    mp3 = audio_dir / item["mp3Key"].rsplit("/", 1)[-1]
    assert fz["mp3"] == mp3
    assert fz["dur"] == pytest.approx(mp3_duration_s(mp3) + FREEZE_TAIL_S)
    # 기존 record freeze (r02) 는 그대로 렌더 대상.
    assert {f["rid"] for f in freezes} == {"r02", "r07"}
    assert excluded == []


def test_build_timeline_discover_log_line(audio_dir, capsys):
    """배선 로그 — 주입 성립마다 '[discover] rid=' print (실행 로그 게이트 근거)."""
    item = _disc_item()
    _with_discover_mp3(audio_dir, item)
    compare_render.build_timeline(
        _mk_doc(discovery={"items": [item]}), audio_dir, None, _mk_align(), None)
    out = capsys.readouterr().out
    assert "[discover] rid=r07" in out


def test_build_timeline_discover_knee_body_viz_owns_markers(audio_dir, monkeypatch):
    """knee 관절 = _body_line_viz 시도, 성립 시 markers 비움 (:1261 미러)."""
    sentinel = {"user": {"poleX": 0.5}, "ref": {"poleX": 0.5}}
    calls = []

    def stub(align, ut, rt, poles):
        calls.append((ut, rt))
        return sentinel

    monkeypatch.setattr(compare_render, "_body_line_viz", stub)
    item = _disc_item(rid="r02", joint="left_knee")
    _with_discover_mp3(audio_dir, item)
    doc = _mk_doc(discovery={"items": [item]})
    _, freezes, _ = compare_render.build_timeline(doc, audio_dir, None, _mk_align(), None)
    fz = [f for f in freezes if f["pair_src"] == "discover"][0]
    assert calls and calls[-1] == (pytest.approx(3.2), pytest.approx(2.9))
    assert fz["body_viz"] == sentinel
    assert fz["markers"] == []
    assert fz["legs_viz"] is None and fz["pole_viz"] is None
    assert fz["viz_kind"] is None and fz["viz_side"] is None


def test_build_timeline_discover_knee_body_viz_none_keeps_markers(audio_dir):
    """poles 부재 → body_viz None (실코드 경로), rec 보유 rid 는 markers 유지."""
    # rid r02 공유 — record criterion(left_elbow)로 _align_markers 성립.
    item = _disc_item(rid="r02", joint="left_knee")
    _with_discover_mp3(audio_dir, item)
    doc = _mk_doc(discovery={"items": [item]})
    _, freezes, _ = compare_render.build_timeline(doc, audio_dir, None, _mk_align(), None)
    fz = [f for f in freezes if f["pair_src"] == "discover"][0]
    assert fz["body_viz"] is None
    assert fz["markers"]  # conf 0.9 합성 align — 마커 성립


def test_build_timeline_discover_nonknee_markers_only(audio_dir):
    """비-knee 관절 = markers 만 (body/legs/pole/viz_kind/viz_side 전부 None)."""
    item = _disc_item(
        rid="r02", joint="left_elbow",
        mp3Key=build_discover_audio_key("u1", "a1", "r02", "left_elbow"))
    _with_discover_mp3(audio_dir, item)
    doc = _mk_doc(discovery={"items": [item]})
    _, freezes, _ = compare_render.build_timeline(doc, audio_dir, None, _mk_align(), None)
    fz = [f for f in freezes if f["pair_src"] == "discover"][0]
    assert fz["markers"]
    assert fz["body_viz"] is None and fz["legs_viz"] is None
    assert fz["pole_viz"] is None and fz["viz_kind"] is None and fz["viz_side"] is None


def test_build_timeline_discover_new_rid_fail_open_markers(audio_dir):
    """doc records 에 없는 신규 rid = markers [] (fail-open — 표시만 생략)."""
    item = _disc_item(rid="r07", joint="left_elbow",
                      mp3Key=build_discover_audio_key("u1", "a1", "r07", "left_elbow"))
    _with_discover_mp3(audio_dir, item)
    doc = _mk_doc(discovery={"items": [item]})
    _, freezes, _ = compare_render.build_timeline(doc, audio_dir, None, _mk_align(), None)
    fz = [f for f in freezes if f["pair_src"] == "discover"][0]
    assert fz["markers"] == []


def test_build_timeline_discovery_absent_backcompat(audio_dir):
    """discovery 부재/빈 items = freezes/excluded 종전과 완전 동일 (byte-동일 유닛판)."""
    align = _mk_align()
    _, fz_absent, ex_absent = compare_render.build_timeline(
        _mk_doc(), audio_dir, None, align, None)
    _, fz_empty, ex_empty = compare_render.build_timeline(
        _mk_doc(discovery={"items": []}), audio_dir, None, align, None)
    assert fz_absent == fz_empty
    assert ex_absent == ex_empty
    assert all(f["pair_src"] != "discover" for f in fz_absent)


def test_build_timeline_discover_no_mp3_excluded(audio_dir):
    """audio_dir 에 basename(mp3Key) 부재 → excluded 'discover_no_mp3' 회계, 예외 0."""
    item = _disc_item()  # mp3 미생성
    doc = _mk_doc(discovery={"items": [item]})
    _, freezes, excluded = compare_render.build_timeline(
        doc, audio_dir, None, _mk_align(), None)
    assert all(f["pair_src"] != "discover" for f in freezes)
    assert {"rid": "r07", "reason": "discover_no_mp3"} in excluded


def test_build_timeline_discover_ref_boundary_pin_excluded(audio_dir):
    """rt 가 ref 양끝 REF_BOUNDARY_PIN_S 이내 = record 경로와 같은 경계 제외."""
    item = _disc_item(refSec=0.1)
    _with_discover_mp3(audio_dir, item)
    doc = _mk_doc(discovery={"items": [item]})
    _, freezes, excluded = compare_render.build_timeline(
        doc, audio_dir, None, _mk_align(), None)
    assert all(f["pair_src"] != "discover" for f in freezes)
    assert {"rid": "r07", "reason": "ref_boundary_pin"} in excluded


# ══════════════════════ authenticity_checks — discover 정식 지원 ══════════════════════


def _record_freeze(**over) -> dict:
    base = {
        "rid": "r02", "joint": "left_elbow", "userSec": 2.0, "refSec": 2.0,
        "pairSrc": "align", "freezeS": 5.0, "voiceStartOutS": 2.0,
        "text": coach_audio_speech_text({"cueLine": CUE, "statusLine": STATUS}),
    }
    base.update(over)
    return base


def _discover_freeze(**over) -> dict:
    base = {
        "rid": "r07", "joint": "left_knee", "userSec": 3.2, "refSec": 2.9,
        "pairSrc": "discover", "freezeS": 6.0, "voiceStartOutS": 9.0,
        "text": DISC_TEXT,
    }
    base.update(over)
    return base


def _report(freezes, excluded=None) -> dict:
    return {
        "outDurationS": 30.0, "userDurationS": 6.0,
        "expectedFreezes": len(freezes),
        "excludedFreezes": excluded or [],
        "freezes": freezes,
    }


def _fails(checks):
    return [name for name, passed, _ in checks if not passed]


def _passes(checks):
    return [name for name, passed, _ in checks if passed]


def test_h2_discover_matching_moment_passes():
    doc = _mk_doc(discovery={"items": [_disc_item()]})
    checks = authenticity_checks(
        _report([_record_freeze(), _discover_freeze()]), doc)
    assert "H2 순간 r07[discover]" in _passes(checks)
    assert _fails(checks) == []


def test_h2_discover_moment_perturbed_fails():
    """순간 0.5s 비틀기 = FAIL (fail-closed — 외부 삽입 검출 유지)."""
    doc = _mk_doc(discovery={"items": [_disc_item()]})
    checks = authenticity_checks(
        _report([_record_freeze(), _discover_freeze(userSec=3.7)]), doc)
    assert "H2 순간 r07[discover]" in _fails(checks)


def test_h2_discover_no_doc_discovery_fails():
    """doc 에 discovery 목록 자체 부재 = FAIL — blanket 면제 없음 검증."""
    checks = authenticity_checks(
        _report([_record_freeze(), _discover_freeze()]), _mk_doc())
    assert "H2 순간 r07[discover]" in _fails(checks)


def test_h2_displacing_tuple_not_expanded():
    """_H2_UT_DISPLACING_SRC 는 ('align-peak','align-pole') 불변 — D-di7-04.

    튜플 blanket 면제는 임의 순간 이동이 discover 를 사칭할 수 있어(T-di7-01)
    자체 분기(fail-closed)로 대체됐다."""
    assert compare_verify._H2_UT_DISPLACING_SRC == ("align-peak", "align-pole")
    assert "discover" not in compare_verify._H2_UT_DISPLACING_SRC


def test_discover_label_lockstep_with_models():
    """compare_verify 의 discover 리터럴 == models.DISCOVERY_PAIR_SRC (drift 0)."""
    assert compare_verify._DISCOVER_PAIR_SRC == models.DISCOVERY_PAIR_SRC


def test_h3_discover_text_matches_doc_item():
    """discover freeze expected = discovery item text 문자 일치. 같은 rid 의
    원본 record freeze H3 는 종전 로직 그대로 (rid 공유 — chd stock 2FAIL
    구조 원인 해소 검증)."""
    item = _disc_item(rid="r02")
    doc = _mk_doc(discovery={"items": [item]})
    report = _report([_record_freeze(), _discover_freeze(rid="r02")])
    checks = authenticity_checks(report, doc)
    assert "H3 자막 진품 r02[discover]" in _passes(checks)
    assert "H3 자막 진품 r02" in _passes(checks)  # 원본 record freeze — 종전 로직
    assert _fails(checks) == []

    # discover text 조작 = discover 엔트리만 FAIL.
    report2 = _report([_record_freeze(), _discover_freeze(rid="r02", text="조작 문장")])
    checks2 = authenticity_checks(report2, doc)
    assert "H3 자막 진품 r02[discover]" in _fails(checks2)
    assert "H3 자막 진품 r02" in _passes(checks2)


def test_h3_discover_no_match_fails():
    """매칭 item 부재(순간 비틀림) = H3 도 FAIL (단일 매칭 헬퍼 공유 — drift 0)."""
    doc = _mk_doc(discovery={"items": [_disc_item()]})
    checks = authenticity_checks(
        _report([_record_freeze(), _discover_freeze(userSec=3.7)]), doc)
    assert "H3 자막 진품 r07[discover]" in _fails(checks)


def test_h4_discover_mp3key_join_passes_without_coach_audio():
    """discover freeze = discovery item mp3Key 'results/' 조인 PASS — coachAudio
    에 없는 신규 rid 도 PASS (D-di7-03: coachAudio 무접촉)."""
    doc = _mk_doc(discovery={"items": [_disc_item()]})
    checks = authenticity_checks(
        _report([_record_freeze(), _discover_freeze()]), doc)
    assert "H4 음성 조인 r07[discover]" in _passes(checks)
    assert _fails(checks) == []


def test_h4_discover_no_match_fails():
    doc = _mk_doc(discovery={"items": [_disc_item()]})
    checks = authenticity_checks(
        _report([_record_freeze(), _discover_freeze(userSec=3.7)]), doc)
    assert "H4 음성 조인 r07[discover]" in _fails(checks)


def test_h1_new_rid_discovery_joins_eligible():
    """신규 rid discovery 렌더 = eligible 합류 PASS (미래 케이스 게이트)."""
    doc = _mk_doc(discovery={"items": [_disc_item()]})
    checks = authenticity_checks(
        _report([_record_freeze(), _discover_freeze()]), doc)
    h1 = [c for c in checks if c[0] == "H1 정지 회계"]
    assert h1 and h1[0][1] is True

    # discovery 없는 doc 에 같은 report = H1 FAIL (r07 이 eligible 밖).
    checks2 = authenticity_checks(
        _report([_record_freeze(), _discover_freeze()]), _mk_doc())
    h1b = [c for c in checks2 if c[0] == "H1 정지 회계"]
    assert h1b and h1b[0][1] is False


def test_authenticity_backcompat_discovery_absent_identical():
    """discovery 부재 doc = 체크 목록 종전과 완전 동일 (빈 items 와도 동일)."""
    report = _report([_record_freeze()])
    a = authenticity_checks(report, _mk_doc())
    b = authenticity_checks(report, _mk_doc(discovery={"items": []}))
    assert a == b
    assert all("[discover]" not in name for name, _, _ in a)


# ══════════════════════ _validate_discovery + update_analysis_discovery ══════════════════════


def _payload(items=None):
    return {"items": items if items is not None else [_disc_item()]}


def test_validate_discovery_accepts_canonical():
    firestore_admin._validate_discovery(_payload())
    firestore_admin._validate_discovery(_payload(items=[]))


@pytest.mark.parametrize("bad", [
    "not-a-dict",
    {},                                        # items 누락
    {"items": [_disc_item()], "extra": 1},     # 여분 키
    {"items": "not-a-list"},
    {"items": [_disc_item(pairSrc="align")]},          # pairSrc enum 위반
    {"items": [_disc_item(mp3Key="uploads/u1/a1/x.mp3")]},  # prefix 위반
    {"items": [{k: v for k, v in _disc_item().items() if k != "adoptedAt"}]},  # 키 누락
    {"items": [{**_disc_item(), "extra": 1}]},          # item 여분 키
    {"items": [_disc_item(rid="")]},                    # 빈 str
    {"items": [_disc_item(userSec=-1.0)]},              # 음수
    {"items": [_disc_item(userSec=float("nan"))]},      # 비유한
    {"items": [_disc_item(text=["문장"])]},             # item 내 list (중첩 배열)
    {"items": [_disc_item(), _disc_item(userSec=4.0)]},  # mp3Key 중복
])
def test_validate_discovery_rejects_malformed(bad):
    with pytest.raises((TypeError, ValueError)):
        firestore_admin._validate_discovery(bad)


def test_validate_discovery_rejects_non_mp3_suffix():
    with pytest.raises(ValueError):
        firestore_admin._validate_discovery(
            _payload(items=[_disc_item(mp3Key="results/u1/a1/discover_audio_r07_left_knee.wav")]))


def test_update_analysis_discovery_single_field_path(monkeypatch):
    calls = []

    class FakeDoc:
        def update(self, payload):
            calls.append(payload)

    monkeypatch.setattr(firestore_admin, "_doc", lambda _path: FakeDoc())
    items = [_disc_item()]
    firestore_admin.update_analysis_discovery("u1", "a1", items)
    assert len(calls) == 1
    assert set(calls[0].keys()) == {"result.discovery", "updatedAt"}
    assert calls[0]["result.discovery"] == {"items": items}

    # validator 라우팅 — 오염 payload 는 update 도달 전 거부.
    with pytest.raises(ValueError):
        firestore_admin.update_analysis_discovery(
            "u1", "a1", [_disc_item(pairSrc="align")])
    assert len(calls) == 1


# ══════════════════════ s3keys.build_discover_audio_key ══════════════════════


def test_build_discover_audio_key_canonical():
    key = build_discover_audio_key("u1", "a1", "r07", "left_knee")
    assert key == "results/u1/a1/discover_audio_r07_left_knee.mp3"
    # basename 'discover_' 접두 — record 큐 오디오(r{NN}.mp3)와 구조 비충돌.
    assert key.rsplit("/", 1)[-1].startswith("discover_")


def test_models_discovery_contract_block():
    assert models.DISCOVERY_KEYS == ("items",)
    assert models.DISCOVERY_ITEM_KEYS == (
        "rid", "joint", "userSec", "refSec", "pairSrc", "text", "mp3Key", "adoptedAt")
    assert models.DISCOVERY_PAIR_SRC == "discover"
