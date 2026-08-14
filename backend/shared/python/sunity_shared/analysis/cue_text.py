"""큐 문장 단일 소스 — 자막·음성(Polly)·렌더 자막이 같은 문장을 읽는다 (quick-260808-jix).

기원: pipeline app.py `_coach_audio_speech_text` 계열의 **순수 이동** (로직 문자
단위 동일). 종전에는 렌더러(render_compare_prototype.py)가 pipeline app.py 를
path-exec 해 이 함수를 꺼냈는데, 파이프라인 내부에서 렌더를 호출하면 app.py 가
이중 exec 되는 구조라 여기로 분리했다 — 세 소비자(파이프라인 Polly 합성 /
합성 비교 영상 자막 / 프로토 CLI)가 전부 이 모듈 하나를 import 한다.

lockstep: app/src/lib/deductionSheet.ts GOAL_CLAUSE_PREFIX / GOAL_CLAUSE_SEPARATOR /
splitGoalClause / composeCueSubtitleKo 와 **문자 단위 동일** 필수 — 한쪽만 바뀌면
음성과 자막이 다시 갈라진다 (debug va-subtitle-audio-mismatch, 2026-08-07).
검증 방식도 lockstep 의 일부다: 소스 눈대조가 아니라 같은 fixture 를 양쪽 엔진에
**실제로 통과시켜** 비교한다 (backend/tests/test_caption_cause_layer.py +
backend/tests/phase32/compose_cue_probe.mjs).

원인 절(causeLine, quick-260814-rcz): belle 2026-08-14 발굴 판정 "앞뒤로 설명이
필요… 캡션이 중요" — 증상과 행동만 있고 **원인이 들어갈 자리가 없었다**. 원인
문장의 출처는 승인 문구집(phrasebook)이고 **LLM 생성 경로는 쓰지 않는다**: 카드
3단 골격은 문구집이 소유하고 LLM 은 가변부만 소유한다(D-11). 음성·자막은 가장
하중이 큰 표면이라 골격 소유 원칙이 여기서 완화될 수 없다.
"""
from __future__ import annotations

# 목표절 구분 상수 — app/src/lib/deductionSheet.ts GOAL_CLAUSE_PREFIX /
# GOAL_CLAUSE_SEPARATOR 와 lockstep (문자 단위 동일 필수 — 한쪽만 바뀌면
# 음성과 자막이 다시 갈라진다).
GOAL_CLAUSE_PREFIX = "목표는"
GOAL_CLAUSE_SEPARATOR = ". "
# 절 끝 문장부호 — 이미 문장이 끝나 있으면 마침표를 중복하지 않는다.
_CLAUSE_ENDINGS = (".", "!", "?")


def goal_clause_action_line(cue_line: str) -> str:
    """cueLine 에서 목표절을 뺀 행동절 (app splitGoalClause.actionLine 미러).

    fail-closed — 접두(목표는)와 구분자(. )가 둘 다 성립하고 자른 뒤가 비지
    않을 때만 자른다. `__common__` 문형(목표절 없음)·구분자 부재·빈 행동절은
    원문 그대로 — 앱 자막과 동일 규칙 (deductionSheet.ts:375-390).
    """
    if not cue_line.startswith(GOAL_CLAUSE_PREFIX):
        return cue_line
    cut = cue_line.find(GOAL_CLAUSE_SEPARATOR)
    if cut < 0:
        return cue_line
    action = cue_line[cut + len(GOAL_CLAUSE_SEPARATOR):]
    return action if action else cue_line


def _append_clause(head: str, clause: str) -> str:
    """절 이어붙이기 — 사이에 **문장 경계**(마침표 + 공백 한 칸).

    belle 08-07 실기기 반려 — 경계 없이 이으면 Polly 가 두 문장을 한 문장으로
    run-on 낭독한다("…좁아요 다리를 와이드…"). 앞 절이 이미 문장부호로 끝나면
    중복하지 않는다. 이 규칙은 **절 공용**이다 — 원인 절이 붙어도 같은 경계가
    적용돼야 run-on 방지가 새 이음매에서 뚫리지 않는다 (분기 복제 금지).
    """
    sep = "" if head.endswith(_CLAUSE_ENDINGS) else "."
    return f"{head}{sep} {clause}"


def coach_audio_speech_text(rec: dict) -> str:
    """합성할 문장 = 재생 중 자막과 **같은 문장** (composeCueSubtitleKo 미러).

    debug va-subtitle-audio-mismatch (2026-08-07) — 음성이 자막에 없는 문장
    (목표절)으로 시작하고 자막의 결함문(statusLine)은 말하지 않아 V-A 불일치로
    지각됐다. 규칙: statusLine(증상) → causeLine(원인) → 행동절, 각 절 사이는
    문장 경계. 앱 자막 조립(deductionSheet.ts composeCueSubtitleKo)과 문자 단위
    동일. 앱의 fallbackActionPhrase 분기는 cueLine 부재 record 전용인데 그
    record 는 합성 대상에서 이미 제외라(_run_deferred_coach_audio cue_records
    필터) 여기 미러 불요.

    causeLine (quick-260814-rcz, belle 08-14 "앞뒤로 설명이 필요"):
      - **선택 절**이다. str 이 아니거나 빈 문자열이면 아예 없는 것처럼 동작해
        산출이 오늘과 byte-동일해야 한다 — 무회귀 1급 (문구집 67 entry 중 2건만
        보유하므로 나머지 65건의 캡션은 문자 하나도 변하지 않는다).
      - 순서는 고정 — 증상 다음, 행동 앞. 원인을 행동 뒤에 두면 자막 3줄 클립에서
        가장 먼저 잘리는 것이 행동절이 되어 2026-08-01 반려가 재발한다.
      - 내용은 **측정된 사실이 아니라 가설**이다. 문구집이 가설 어미로만 소유하고
        (test_caption_cause_layer) 이 조립기는 문자열을 만들지 않는다.
    """
    action = goal_clause_action_line(rec["cueLine"])
    clauses: list[str] = []
    for slot in ("statusLine", "causeLine"):
        value = rec.get(slot)
        if isinstance(value, str) and value:
            clauses.append(value)
    clauses.append(action)
    text = clauses[0]
    for clause in clauses[1:]:
        text = _append_clause(text, clause)
    return text
