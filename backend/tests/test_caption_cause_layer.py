"""캡션 원인 절(causeLine) 계약 — quick-260814-rcz.

belle 2026-08-14 발굴 판정: 두 발굴 모두 **결함 성립은 인정**됐고 미달은
**설명 층**이다 ("앞뒤로 설명이 필요… 캡션이 중요"). 지금 캡션은 statusLine(증상)
+ 행동절 2문장 고정이라 원인이 들어갈 자리가 구조적으로 없다. 이 파일은 그
자리(causeLine)를 만들고 다음 4가지를 못 박는다:

  1. **무회귀 1급** — causeLine 이 없는 record 는 오늘과 **문자 단위 동일**한
     2문장을 낸다. 테스트는 오늘 규칙의 동결 사본(`_legacy_compose`)과 대조한다
     (구현을 그대로 다시 부르면 무회귀를 증명하지 못한다).
  2. **양엔진 동일** — python(cue_text) 산출 == node 로 **실제 실행한** TS
     (deductionSheet.composeCueSubtitleKo) 산출. 소스 눈대조 금지 — 그 방식이
     2026-08-07 V-A 불일치를 belle 실기기까지 통과시켰다.
  3. **가설 어투·무수치** — 원인은 측정된 것이 아니다(회전 위상·진입 구간은 현
     데이터로 측정 불가). 측정 안 된 것을 측정된 것처럼 쓰면 1급 불변식 위반이라
     시드 문구는 가설 어미로 끝나고 수치·각도·퍼센트·단정 어미가 0이어야 한다.
  4. **구운 자막 3줄 상한** — compare_render 자막 블록은 `wrap_text(...)[:3]` 로
     4번째 줄을 조용히 버린다. 원인 절이 붙어 4줄이 되면 **행동절이 사라져**
     2026-08-01 belle 반려가 재발한다. 운영 폰트·폭으로 줄수를 재서 막는다.

순수 함수 + 로컬 프로브만 — AWS/네트워크/Pod 무접촉.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from sunity_shared import models
from sunity_shared.analysis import phrasebook
from sunity_shared.analysis.cue_text import (
    coach_audio_speech_text,
    goal_clause_action_line,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROBE = Path(__file__).resolve().parent / "phase32" / "compose_cue_probe.mjs"

# 시드 2건의 문구집 키 (belle 08-14 판정 원문 전사 — 새 사실 발명 0).
SEED_KEYS = (
    "ref-pdshape.angle_vs_reference__left_elbow",
    "ref-power-spin.angle_vs_reference__left_shoulder",
)

# 승인 코퍼스 실측 패널 폭 — 5동작 전건 user 원본 2160x3840 → scale=-2:1080 →
# 패널 608px. compare_render 는 W = user패널 * 2 + GAP 로 캔버스를 잡는다.
# (ffprobe 실측 2026-08-14: pdshapefault/elbow/kipup/peterpan/powerspin 전건 동일.
#  구운 영상 실물도 1224x1080 — /Users/Shared/sunity-freeze-inject-260814/.)
APPROVED_PANEL_W = 608
SUBTITLE_MAX_LINES = 3  # compare_render.py `wrap_text(...)[:3]` 하드 클립


# ── 오늘 규칙의 동결 사본 (무회귀 대조 기준) ────────────────────────────────
def _legacy_compose(rec: dict) -> str:
    """2026-08-14 이전 조립 규칙의 **동결 사본** — 구현을 부르지 않는다.

    구현을 다시 부르면 "구현이 구현과 같다"는 동어반복이 된다. 이 사본이 오늘의
    산출을 들고 있어야 causeLine 부재 경로의 byte-동일이 증명된다.
    """
    action = goal_clause_action_line(rec["cueLine"])
    status = rec.get("statusLine")
    if isinstance(status, str) and status:
        sep = "" if status.endswith((".", "!", "?")) else "."
        return f"{status}{sep} {action}"
    return action


# ── fixture 행 (python 단일 소유 — 프로브에 그대로 파이프) ───────────────────
GOAL_CUE = (
    "목표는 거꾸로 매달린 채 윗다리를 폴을 따라 곧게 뽑는 자세예요. "
    "팔꿈치로 폴을 단단히 감은(엘보 그립) 채, 그 각을 기준 자세에 겹쳐 맞춰보세요"
)
PLAIN_CUE = "발끝으로 천장을 길게 밀어낸다는 느낌으로 다리를 쭉 뻗어보세요."
STATUS = "오른쪽 팔꿈치 각도가 엘보 트위스트 기준 자세와 차이가 있어요"
CAUSE = "회전이 덜 된 채 손을 먼저 뻗어 잡은 것일 수 있어요"


def _seed_records() -> list[dict]:
    """시드 2건의 실제 문구집 산출 record (조립 입력 그대로)."""
    out = []
    for key in SEED_KEYS:
        motion, criterion = key.split(".", 1)
        out.append(phrasebook.assemble_phrases(motion, criterion))
    return out


def fixture_rows() -> list[dict]:
    """양엔진 비교 fixture — python 이 단일 소유한다."""
    rows: list[dict] = [
        # T1 무-cause (무회귀 1급)
        {"cueLine": GOAL_CUE, "statusLine": STATUS},
        {"cueLine": PLAIN_CUE, "statusLine": STATUS},
        {"cueLine": GOAL_CUE},
        {"cueLine": PLAIN_CUE},
        # T2 정상 3절
        {"cueLine": GOAL_CUE, "statusLine": STATUS, "causeLine": CAUSE},
        # T3 문장부호 중복 0
        {"cueLine": GOAL_CUE, "statusLine": f"{STATUS}.", "causeLine": f"{CAUSE}."},
        {"cueLine": GOAL_CUE, "statusLine": f"{STATUS}!", "causeLine": f"{CAUSE}?"},
        # T4 status 부재 + cause 있음
        {"cueLine": GOAL_CUE, "causeLine": CAUSE},
        # T5 빈/비문자열 cause (fail-closed)
        {"cueLine": GOAL_CUE, "statusLine": STATUS, "causeLine": ""},
        {"cueLine": GOAL_CUE, "statusLine": STATUS, "causeLine": None},
        {"cueLine": GOAL_CUE, "statusLine": STATUS, "causeLine": 3},
        {"cueLine": PLAIN_CUE, "statusLine": "", "causeLine": ""},
    ]
    rows.extend(_seed_records())
    return rows


# ── T1 — causeLine 부재 = 오늘과 문자 단위 동일 (무회귀 1급) ─────────────────
@pytest.mark.parametrize("rec", [r for r in fixture_rows() if not r.get("causeLine")])
def test_no_cause_line_is_byte_identical_to_today(rec: dict) -> None:
    assert coach_audio_speech_text(rec) == _legacy_compose(rec)


def test_no_cause_line_regression_covers_whole_phrasebook() -> None:
    """문구집 전 entry — causeLine 미보유 record 의 캡션은 오늘과 byte-동일."""
    pb = json.loads(
        (_REPO_ROOT / "backend" / "data" / "phrasebook.json").read_text(
            encoding="utf-8"
        )
    )
    checked = 0
    for key, entry in pb["entries"].items():
        if not isinstance(entry.get("cueLine"), str):
            continue
        if isinstance(entry.get("causeLine"), str) and entry["causeLine"]:
            continue  # 시드 2건 — 의도된 변경분
        rec = {k: entry.get(k) for k in ("statusLine", "cueLine")}
        assert coach_audio_speech_text(rec) == _legacy_compose(rec), key
        checked += 1
    assert checked >= 60, f"대조 entry 수 이상: {checked}"


# ── T2/T3/T4 — 3절 조립 규칙 ───────────────────────────────────────────────
def test_three_clause_order_and_boundary() -> None:
    action = goal_clause_action_line(GOAL_CUE)
    got = coach_audio_speech_text(
        {"cueLine": GOAL_CUE, "statusLine": STATUS, "causeLine": CAUSE}
    )
    assert got == f"{STATUS}. {CAUSE}. {action}"
    # 순서 고정 — 증상 → 원인 → 행동.
    assert got.index(STATUS) < got.index(CAUSE) < got.index(action)
    # 음성 도입이 목표절이 아니다 (V-A 불일치 본체 문장 재발 가드).
    assert not got.startswith("목표는")


def test_existing_punctuation_is_not_duplicated() -> None:
    action = goal_clause_action_line(GOAL_CUE)
    assert coach_audio_speech_text(
        {"cueLine": GOAL_CUE, "statusLine": f"{STATUS}.", "causeLine": f"{CAUSE}."}
    ) == f"{STATUS}. {CAUSE}. {action}"
    assert coach_audio_speech_text(
        {"cueLine": GOAL_CUE, "statusLine": f"{STATUS}!", "causeLine": f"{CAUSE}?"}
    ) == f"{STATUS}! {CAUSE}? {action}"
    assert ".." not in coach_audio_speech_text(
        {"cueLine": GOAL_CUE, "statusLine": f"{STATUS}.", "causeLine": f"{CAUSE}."}
    )


def test_cause_without_status() -> None:
    action = goal_clause_action_line(GOAL_CUE)
    assert coach_audio_speech_text(
        {"cueLine": GOAL_CUE, "causeLine": CAUSE}
    ) == f"{CAUSE}. {action}"


# ── T5 — 빈/비문자열 cause 는 조립에 끼어들지 않는다 (fail-closed) ───────────
@pytest.mark.parametrize("bad", ["", None, 3, [], {}, True])
def test_non_string_cause_falls_back_to_two_clause(bad) -> None:
    rec = {"cueLine": GOAL_CUE, "statusLine": STATUS, "causeLine": bad}
    assert coach_audio_speech_text(rec) == _legacy_compose(rec)


# ── T6 — 양엔진 실행 비교 (소스 눈대조 아님) ───────────────────────────────
@pytest.mark.skipif(shutil.which("node") is None, reason="node 부재")
def test_python_and_node_agree_on_every_fixture_row() -> None:
    rows = fixture_rows()
    proc = subprocess.run(
        ["node", str(_PROBE)],
        input=json.dumps([{"record": r, "fallback": None} for r in rows]),
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        timeout=120,
    )
    assert proc.returncode == 0, f"probe 실패: {proc.stderr[-2000:]}"
    ts_out = json.loads(proc.stdout)
    py_out = [coach_audio_speech_text(r) for r in rows]
    assert len(ts_out) == len(py_out) == len(rows)
    for i, (py, ts) in enumerate(zip(py_out, ts_out)):
        assert py == ts, f"행 {i} 갈라짐\n  python={py!r}\n  node  ={ts!r}"


# ── T7 — 시드 문구: 가설 어투 · 무수치 · 금지어 게이트 ──────────────────────
# 가설 어미 화이트리스트 — "측정 안 된 원인"임이 어미에서 읽혀야 한다.
HYPOTHESIS_ENDINGS = ("일 수 있어요", "것으로 보여요", "듯 보여요", "것 같아요")
# 단정 어미 — 측정 안 된 것을 측정된 것처럼 말하는 형태.
ASSERTIVE_PATTERNS = ("때문입니다", "때문이에요", "입니다.", "이 원인입니다", "탓입니다")


def _cause_lines() -> dict[str, str]:
    pb = json.loads(
        (_REPO_ROOT / "backend" / "data" / "phrasebook.json").read_text(
            encoding="utf-8"
        )
    )
    return {
        k: v["causeLine"]
        for k, v in pb["entries"].items()
        if isinstance(v.get("causeLine"), str) and v["causeLine"]
    }


def test_seed_count_is_exactly_two_and_keys_match() -> None:
    causes = _cause_lines()
    assert set(causes) == set(SEED_KEYS), f"시드 키 불일치: {sorted(causes)}"


@pytest.mark.parametrize("key", SEED_KEYS)
def test_seed_cause_is_hypothesis_and_numberless(key: str) -> None:
    cause = _cause_lines()[key]
    assert cause.endswith(HYPOTHESIS_ENDINGS), f"{key}: 가설 어미 아님 — {cause!r}"
    assert not re.search(r"\d", cause), f"{key}: 수치 유입 — {cause!r}"
    assert "도" not in cause.replace("도록", "").replace("정도", "") or not re.search(
        r"\d\s*(도|°)", cause
    ), f"{key}: 각도 표기 유입"
    assert "%" not in cause
    for bad in ASSERTIVE_PATTERNS:
        assert bad not in cause, f"{key}: 단정 어미 {bad!r}"


def test_seed_cause_passes_existing_forbidden_gate() -> None:
    """기존 금지어 게이트가 entries 를 재귀 수집하므로 새 문구도 자동 스캔된다."""
    copy_strings = phrasebook.rendered_copy_strings()
    for cause in _cause_lines().values():
        assert cause in copy_strings, "causeLine 이 금지어 게이트 스코프 밖"
    for phrase in phrasebook.FORBIDDEN_PHRASES_PHRASEBOOK:
        for cause in _cause_lines().values():
            assert phrase not in cause
    for pattern in phrasebook.FORBIDDEN_REGEX_PHRASEBOOK:
        for cause in _cause_lines().values():
            assert not re.search(pattern, cause)


def test_cause_line_is_a_contract_phrase_slot() -> None:
    """배선 증인 — 문구집 슬롯 ↔ 계약 키 ↔ 파이프라인 병합 루프가 한 tuple."""
    assert "causeLine" in phrasebook._ENTRY_SLOTS  # noqa: SLF001
    assert "causeLine" in models.DEDUCTION_PHRASE_KEYS
    assert models.DEDUCTION_PHRASE_KEYS == phrasebook._ENTRY_SLOTS  # noqa: SLF001


def test_fail_closed_path_does_not_invent_cause() -> None:
    """미지원 조합은 원인을 짓지 않는다 (일반론 fabrication 차단, D-11)."""
    slots = phrasebook.assemble_phrases("ref-kip-up", "no_such_criterion")
    assert "causeLine" not in slots
    assert slots.get("failClosed") is True


# ── T8 — 구운 자막 3줄 상한 실측 (운영 폰트·폭) ────────────────────────────
def _wrap_lines(text: str, panel_w: int = APPROVED_PANEL_W) -> list[str]:
    from PIL import Image, ImageDraw, ImageFont

    from sunity_shared.analysis import compare_render as cr

    scale = cr.PANEL_H / 640.0
    font = ImageFont.truetype(str(cr.FONT_PATH), round(22 * scale))
    pad = round(24 * scale)
    draw = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    width = panel_w * 2 + cr.GAP
    return cr.wrap_text(draw, text, font, width - 2 * pad)


@pytest.mark.parametrize("key", SEED_KEYS)
def test_seed_caption_fits_baked_subtitle_three_lines(key: str) -> None:
    """4번째 줄은 `[:3]` 이 조용히 버린다 = 행동절 소실 (08-01 반려 재발)."""
    motion, criterion = key.split(".", 1)
    rec = phrasebook.assemble_phrases(motion, criterion)
    text = coach_audio_speech_text(rec)
    lines = _wrap_lines(text)
    assert len(lines) <= SUBTITLE_MAX_LINES, (
        f"{key}: 자막 {len(lines)}줄 ({len(text)}자) — {SUBTITLE_MAX_LINES}줄 초과 시 "
        f"행동절이 잘린다\n" + "\n".join(f"  | {x}" for x in lines)
    )
    # 클립 후에도 행동절 꼬리가 살아있는지 (소실 직접 확인).
    action_tail = goal_clause_action_line(rec["cueLine"])[-8:]
    assert action_tail in "".join(lines[:SUBTITLE_MAX_LINES])


def test_every_phrasebook_caption_fits_three_lines() -> None:
    """시드 밖 entry 도 3줄 이내 — 이 상한이 오늘 실제로 어디서도 안 자른다는
    사실이 무회귀의 근거다 (자르는 entry 가 생기면 이 테스트가 먼저 운다)."""
    pb = json.loads(
        (_REPO_ROOT / "backend" / "data" / "phrasebook.json").read_text(
            encoding="utf-8"
        )
    )
    over: list[str] = []
    for key, entry in pb["entries"].items():
        if not isinstance(entry.get("cueLine"), str):
            continue
        rec = {
            k: entry.get(k) for k in ("statusLine", "causeLine", "cueLine")
        }
        n = len(_wrap_lines(coach_audio_speech_text(rec)))
        if n > SUBTITLE_MAX_LINES:
            over.append(f"{key}({n}줄)")
    assert not over, f"3줄 초과 entry: {over}"
