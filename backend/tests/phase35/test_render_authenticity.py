"""quick-260808-jix 렌더 방어 라운드 — H 진품 판정(산출-분석 일치) 유닛.

belle 신뢰 장치: v7 통째 삽입류 조작(다른 분석의 mp4/report 를 이 doc 에 부착)이
기계적으로 FAIL 나는 축. 순수 함수 authenticity_checks 에 합성 report/doc 조합.
+ build_timeline 의 no_mp3 제외 회계(H1 의 근거 데이터) 통합 검증.
"""

from __future__ import annotations

import json
from pathlib import Path

from sunity_shared.analysis import compare_render
from sunity_shared.analysis.compare_verify import authenticity_checks
from sunity_shared.analysis.cue_text import coach_audio_speech_text

_REPO = Path(__file__).resolve().parents[3]
_DATA = _REPO / ".planning" / "phases" / "35-server-rendered-comparison-video" / "data"

CUE = "목표는 기준 자세예요. 팔꿈치를 폴에 붙여서 몸을 고정해 보세요"
STATUS = "오른쪽 팔꿈치 각도가 기준 자세와 차이가 있어요"


def _doc(records=None, items=None) -> dict:
    return {
        "result": {
            "deductionBreakdown": {"records": records if records is not None else [
                {"recordId": "r00:angle_vs_reference__right_elbow",
                 "criterion": "angle_vs_reference__right_elbow",
                 "atVideoSec": 3.0, "cueLine": CUE, "statusLine": STATUS},
            ]},
            "coachAudio": {"status": "done", "items": items if items is not None else [
                {"recordId": "r00:angle_vs_reference__right_elbow", "key": "results/u/a/coach_audio_r00:angle_vs_reference__right_elbow.mp3"},
            ]},
        }
    }


def _report(freezes=None, excluded=None, dur=10.0) -> dict:
    text = coach_audio_speech_text(
        {"cueLine": CUE, "statusLine": STATUS})
    return {
        "outDurationS": 20.0,
        "userDurationS": dur,
        "expectedFreezes": len(freezes) if freezes is not None else 1,
        "excludedFreezes": excluded or [],
        "freezes": freezes if freezes is not None else [
            {"rid": "r00", "joint": "right_elbow", "userSec": 3.0, "refSec": 4.0,
             "pairSrc": "align", "freezeS": 5.0, "voiceStartOutS": 3.0,
             "text": text},
        ],
    }


def _fails(checks):
    return [name for name, passed, _ in checks if not passed]


def test_authentic_pair_all_pass():
    assert _fails(authenticity_checks(_report(), _doc())) == []


def test_h1_count_mismatch_fails():
    """doc 에 렌더 대상 record 2건인데 정지 1 + 제외 0 → H1 FAIL (조용한 탈락)."""
    doc = _doc(records=[
        {"recordId": "r00:angle_vs_reference__right_elbow",
         "criterion": "angle_vs_reference__right_elbow",
         "atVideoSec": 3.0, "cueLine": CUE, "statusLine": STATUS},
        {"recordId": "r01:split_angle", "criterion": "split_angle",
         "atVideoSec": 5.0, "cueLine": CUE},
    ])
    fails = _fails(authenticity_checks(_report(), doc))
    assert "H1 정지 회계" in fails


def test_h1_excluded_accounting_passes():
    """제외 회계(no_mp3)가 리포트에 실리면 H1 성립 — 탈락이 조용하지 않음."""
    doc = _doc(records=[
        {"recordId": "r00:angle_vs_reference__right_elbow",
         "criterion": "angle_vs_reference__right_elbow",
         "atVideoSec": 3.0, "cueLine": CUE, "statusLine": STATUS},
        {"recordId": "r01:split_angle", "criterion": "split_angle",
         "atVideoSec": 5.0, "cueLine": CUE},
    ])
    report = _report(excluded=[{"rid": "r01", "reason": "no_mp3"}])
    assert "H1 정지 회계" not in _fails(authenticity_checks(report, doc))


def test_h2_moment_drift_fails_and_clamp_allows():
    """순간 불일치(>0.2s) = FAIL / 영상 끝 클램프(렌더러 [clamp] 미러)는 허용."""
    # 불일치: doc 3.0 vs 구운 4.0
    report = _report(freezes=[{**_report()["freezes"][0], "userSec": 4.0}])
    assert any(n.startswith("H2 순간") for n in _fails(authenticity_checks(report, _doc())))

    # 클램프: at=9.95 (>= dur 10.0 - 0.1) → 기대 9.8 — 구운 9.8 = PASS
    doc = _doc(records=[{
        "recordId": "r00:angle_vs_reference__right_elbow",
        "criterion": "angle_vs_reference__right_elbow",
        "atVideoSec": 9.95, "cueLine": CUE, "statusLine": STATUS,
    }])
    report = _report(freezes=[{**_report()["freezes"][0], "userSec": 9.8}])
    assert not any(n.startswith("H2 순간") for n in _fails(authenticity_checks(report, doc)))


def test_h2_displacing_grammar_exempt():
    """align-peak/align-pole = 승인 이동 문법 — 순간-동일성 면제 (kipup 피크 선례)."""
    for src in ("align-peak", "align-pole"):
        report = _report(freezes=[{**_report()["freezes"][0],
                                   "userSec": 7.77, "pairSrc": src}])
        assert not any(
            n.startswith("H2 순간") for n in _fails(authenticity_checks(report, _doc()))
        )


def test_h3_text_tamper_fails_and_override_passes():
    report = _report(freezes=[{**_report()["freezes"][0], "text": "조작된 문장"}])
    assert any(n.startswith("H3 자막 진품") for n in _fails(authenticity_checks(report, _doc())))

    # 오버라이드 테이블 제공 시 오버라이드 문장이 진품 (elbow 픽스처 경로).
    report = _report(freezes=[{**_report()["freezes"][0], "text": "폴에 붙여요"}])
    checks = authenticity_checks(report, _doc(), text_overrides={"r00": "폴에 붙여요"})
    assert not any(n.startswith("H3 자막 진품") for n in _fails(checks))


def test_h4_foreign_audio_rid_fails():
    """freeze rid 가 이 분석 coachAudio 에 없음 = 외부 mp3 의심 FAIL."""
    doc = _doc(items=[{"recordId": "r99:other", "key": "results/u/a/coach_audio_r99:other.mp3"}])
    assert any(n.startswith("H4 음성 조인") for n in _fails(authenticity_checks(_report(), doc)))


def test_wholesale_substitution_fails_multiaxis():
    """v7 통째 삽입 시뮬 — 다른 분석의 report(다른 rid·순간·문장)를 이 doc 에
    대조하면 H 다축 동시 FAIL (belle 신뢰 장치의 본체 시나리오)."""
    foreign = {
        "outDurationS": 60.0, "userDurationS": 17.9, "expectedFreezes": 1,
        "excludedFreezes": [],
        "freezes": [{"rid": "r07", "joint": "left_knee", "userSec": 12.3,
                     "refSec": 9.9, "pairSrc": "align", "freezeS": 6.0,
                     "voiceStartOutS": 12.3, "text": "다른 분석의 문장"}],
    }
    fails = _fails(authenticity_checks(foreign, _doc()))
    assert "H1 정지 회계" in fails
    assert any(n.startswith("H2 순간") for n in fails)  # doc 에 없는 record
    assert any(n.startswith("H4 음성 조인") for n in fails)


def test_h2_moment_from_align_pairs_when_doc_absent():
    """doc atVideoSec 부재(moments 주입 계열 — kipup r00)는 align.pairs 순간이 근거."""
    doc = _doc(records=[{
        "recordId": "r00:split_angle", "criterion": "split_angle",
        "cueLine": CUE,  # atVideoSec 없음
    }])
    align = {"pairs": {"r00": {"atVideoSec": 3.0, "refVideoSec": 4.0}}}
    report = _report(freezes=[{**_report()["freezes"][0], "pairSrc": "align",
                               "text": coach_audio_speech_text({"cueLine": CUE})}])
    checks = authenticity_checks(report, doc, align=align)
    assert _fails(checks) == []
    # align 미제공이면 근거 부재 = FAIL (fail-closed) + H1 도 대상 산정 불일치.
    fails2 = _fails(authenticity_checks(report, doc))
    assert any(n.startswith("H2 순간") for n in fails2)


# ═══════════════ build_timeline no_mp3 제외 회계 (H1 근거 통합) ═══════════════


def test_build_timeline_records_no_mp3_exclusion(tmp_path):
    """elbow 픽스처에서 mp3 1개(r02) 부재 → 그 freeze 는 excluded(no_mp3)로 회계
    되고 나머지 3 freeze 렌더 대상 유지 (H1: 3 + 1 == 4). mp3 는 ffmpeg 합성
    무음 1s — 픽스처/스크래치 오디오 의존 0 (자족 테스트)."""
    import subprocess

    from sunity_shared.analysis.compare_render import FF

    audio = tmp_path / "audio"
    audio.mkdir()
    for rid in ("r00", "r01", "r03"):  # r02 의도 부재
        subprocess.run(
            [FF, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc",
             "-t", "1", str(audio / f"{rid}.mp3")],
            check=True,
        )

    doc = json.load(open(_DATA / "elbow" / "doc.json"))
    align = json.load(open(_DATA / "elbow" / "align.json"))
    warp_b, freezes, excluded = compare_render.build_timeline(doc, audio, None, align, None)
    assert excluded == [{"rid": "r02", "reason": "no_mp3"}]
    assert {fz["rid"] for fz in freezes} == {"r00", "r01", "r03"}


# ═══════════════ G 경계 핀 (ref-경계 아티팩트 — 대안 승인) ═══════════════


def test_boundary_pin_checks_flags_ref_edges():
    """rt 가 ref 양끝 0.5s 이내 = G FAIL, 밖 = PASS (belle doc 실측 16.4~16.6/끝)."""
    from sunity_shared.analysis.compare_verify import boundary_pin_checks

    align = {"refFrames": 240, "fps": 15.0}  # ref 16.0s
    report = {"freezes": [
        {"rid": "r00", "refSec": 15.8},  # 끝 0.2s 이내 — belle 케이스
        {"rid": "r01", "refSec": 0.3},   # 시작 0.5s 이내 — 대칭
        {"rid": "r02", "refSec": 8.0},   # 중앙 — PASS
        {"rid": "r03", "refSec": 0.8},   # 승인 최소 마진 (pdshapefault override) — PASS
    ]}
    verdicts = {n: p for n, p, _ in boundary_pin_checks(report, align)}
    assert verdicts["G 경계 핀 r00"] is False
    assert verdicts["G 경계 핀 r01"] is False
    assert verdicts["G 경계 핀 r02"] is True
    assert verdicts["G 경계 핀 r03"] is True


def test_build_timeline_excludes_boundary_pinned_freeze(tmp_path):
    """belle doc 기전 재현 — pairs rt 를 ref 끝단으로 조작하면 그 freeze 는
    ref_boundary_pin 으로 제외되고 (렌더 진행), 회계에 남는다."""
    import subprocess

    from sunity_shared.analysis.compare_render import FF

    audio = tmp_path / "audio"
    audio.mkdir()
    for rid in ("r00", "r01", "r02", "r03"):
        subprocess.run(
            [FF, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc",
             "-t", "1", str(audio / f"{rid}.mp3")],
            check=True,
        )

    doc = json.load(open(_DATA / "elbow" / "doc.json"))
    align = json.load(open(_DATA / "elbow" / "align.json"))
    ref_dur = align["refFrames"] / align["fps"]
    # 끝단 핀 주입 — pair_overrides 경로 (자동 문법의 짝 재선정이 pairs 주입값을
    # self-heal 하는 것을 유닛 실측 후 벡터 교체: override 는 rt 를 그대로 쓰므로
    # 경계 판정이 문법 전체보다 뒤에서 최종 방어함을 함께 핀).
    warp_b, freezes, excluded = compare_render.build_timeline(
        doc, audio, None, align, None,
        pair_overrides={"r03": {"refVideoSec": ref_dur - 0.2}},
    )
    assert {"rid": "r03", "reason": "ref_boundary_pin"} in excluded
    assert {fz["rid"] for fz in freezes} == {"r00", "r01", "r02"}
