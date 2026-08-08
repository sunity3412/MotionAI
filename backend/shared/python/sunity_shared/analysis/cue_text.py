"""큐 문장 단일 소스 — 자막·음성(Polly)·렌더 자막이 같은 문장을 읽는다 (quick-260808-jix).

기원: pipeline app.py `_coach_audio_speech_text` 계열의 **순수 이동** (로직 문자
단위 동일). 종전에는 렌더러(render_compare_prototype.py)가 pipeline app.py 를
path-exec 해 이 함수를 꺼냈는데, 파이프라인 내부에서 렌더를 호출하면 app.py 가
이중 exec 되는 구조라 여기로 분리했다 — 세 소비자(파이프라인 Polly 합성 /
합성 비교 영상 자막 / 프로토 CLI)가 전부 이 모듈 하나를 import 한다.

lockstep: app/src/lib/deductionSheet.ts GOAL_CLAUSE_PREFIX / GOAL_CLAUSE_SEPARATOR /
splitGoalClause / composeCueSubtitleKo 와 **문자 단위 동일** 필수 — 한쪽만 바뀌면
음성과 자막이 다시 갈라진다 (debug va-subtitle-audio-mismatch, 2026-08-07).
"""
from __future__ import annotations

# 목표절 구분 상수 — app/src/lib/deductionSheet.ts GOAL_CLAUSE_PREFIX /
# GOAL_CLAUSE_SEPARATOR 와 lockstep (문자 단위 동일 필수 — 한쪽만 바뀌면
# 음성과 자막이 다시 갈라진다).
GOAL_CLAUSE_PREFIX = "목표는"
GOAL_CLAUSE_SEPARATOR = ". "


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


def coach_audio_speech_text(rec: dict) -> str:
    """합성할 문장 = 재생 중 자막과 **같은 문장** (composeCueSubtitleKo 미러).

    debug va-subtitle-audio-mismatch (2026-08-07) — 음성이 자막에 없는 문장
    (목표절)으로 시작하고 자막의 결함문(statusLine)은 말하지 않아 V-A 불일치로
    지각됐다. 규칙: statusLine(결함) + 행동절. statusLine 부재면 행동절만 —
    앱 자막 조립(deductionSheet.ts composeCueSubtitleKo)과 문자 단위 동일. 앱의
    fallbackActionPhrase 분기는 cueLine 부재 record 전용인데 그 record 는
    합성 대상에서 이미 제외라(_run_deferred_coach_audio cue_records 필터)
    여기 미러 불요.

    결함문과 행동문 사이에는 **문장 경계(마침표)** 를 넣는다 (belle 08-07 실기기
    반려 — 경계 없이 이으면 Polly 가 두 문장을 한 문장으로 run-on 낭독한다:
    "…좁아요 다리를 와이드…"). statusLine 이 이미 문장부호로 끝나면 중복하지
    않는다. 앱 자막도 같은 규칙 — 한쪽만 바꾸면 음성·자막이 다시 갈라진다.
    """
    action = goal_clause_action_line(rec["cueLine"])
    status = rec.get("statusLine")
    if isinstance(status, str) and status:
        sep = "" if status.endswith((".", "!", "?")) else "."
        return f"{status}{sep} {action}"
    return action
