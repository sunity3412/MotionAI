"""KISMAM 결과 → contract.md §4 AnalysisResult dict 조립.

키 이름은 app/src/types/analysis.ts 와 정확히 일치해야 한다(계약 단일 진실).
Cerebras 문장이 없으면 실제 편차값 기반 폴백 문장 사용(수치 위조 아님).
"""

from __future__ import annotations

from . import kismam
from .kismam import COACHING_FOCUS, JointAssessment

# 이 점수 미만이면 JointScore.issue 노출 (양호하면 생략)
GOOD_SCORE_THRESHOLD = 80


def _issue_text(a: JointAssessment) -> str | None:
    if a.score >= GOOD_SCORE_THRESHOLD:
        return None
    return f"기준 대비 평균 {round(a.deviation_deg)}° 차이"


def build_joints(assessments: list[JointAssessment]) -> list[dict]:
    joints = []
    for a in assessments:
        j: dict = {"key": a.key, "labelKo": a.label_ko, "score": a.score}
        # 구조화 가이드 — 백엔드가 채울 수 있을 때만(없으면 contract 옵셔널, UI 폴백).
        if a.current_angle is not None and a.target_angle is not None:
            j["currentAngle"] = round(float(a.current_angle), 1)
            j["targetAngle"] = round(float(a.target_angle), 1)
        if a.signed_delta_deg is not None:
            j["deltaDeg"] = round(float(a.signed_delta_deg), 1)
        if a.direction:
            j["direction"] = a.direction
        issue = _issue_text(a)
        if issue:
            j["issue"] = issue
        joints.append(j)
    return joints


def build_tips(
    top: list[JointAssessment], coach_details: dict | None = None
) -> list[dict]:
    details = coach_details or {}
    tips = []
    for a in top:
        detail = details.get(a.key) or (
            f"{a.label_ko} 각도가 기준과 평균 {round(a.deviation_deg)}° "
            f"차이가 납니다. 해당 동작 구간을 천천히 교정해 보세요."
        )
        tips.append(
            {
                "joint": a.key,
                "title": f"{a.label_ko} {COACHING_FOCUS[a.key]}",
                "detail": detail,
            }
        )
    return tips


def build_mode1(
    reference_motion: dict,
    similarity: int,
    segment_scores: dict | None = None,
) -> dict:
    out = {
        "mode": "mode1",
        "referenceMotionId": reference_motion["motionId"],
        "referenceMotionName": reference_motion.get("name", ""),
        "athleteName": reference_motion.get("athleteName", ""),
        "similarity": int(max(0, min(100, similarity))),
    }
    # 콤보 모션 분석 시에만 (segments.segment_scores 가 dict 반환). contract §4.
    if segment_scores:
        out["segmentScores"] = segment_scores
    return out


def build_mode3(
    is_first: bool,
    previous_analysis_id: str | None = None,
    prev_dimension_scores: dict | None = None,
    cur_dimension_scores: dict | None = None,
) -> dict:
    """자기 성장(mode3) 비교 블록.

    핵심은 '이전과 몇 % 일치'가 아니라 '발전(progress)'이다([[mode3-progress-not-similarity]]).
    절대 차원(라인/균형/안정성)은 기준 없이 산출돼 세션 간 같은 척도이므로,
    deltaFromPrevious = 이번 점수 − 지난 점수 가 진짜 발전을 의미한다.
    첫 분석이면 비교 대상이 없어 절대 점수만 (delta 없음)."""
    out: dict = {"mode": "mode3", "isFirst": bool(is_first)}
    if is_first or not previous_analysis_id:
        return out
    out["previousAnalysisId"] = previous_analysis_id
    if prev_dimension_scores and cur_dimension_scores:
        # 양쪽에 공통으로 있는 차원만(절대 지표는 항상 일치). 같은 척도라 델타 정합.
        out["deltaFromPrevious"] = {
            d: int(cur_dimension_scores[d] - prev_dimension_scores.get(d, 0))
            for d in cur_dimension_scores
            if d in prev_dimension_scores
        }
    return out


def build_result(
    assessments: list[JointAssessment],
    dimension_scores: dict,
    overall_score: int,
    comparison: dict,
    my_video_url: str,
    reference_video_url: str | None = None,
    coach_details: dict | None = None,
) -> dict:
    """contract AnalysisResult. status='done' 일 때 Firestore result 에 저장.

    dimension_scores = IPSF 실행 차원 점수(angle/line/balance/stability). overall_score 는
    파이프라인이 모드별로 계산(mode1=4차원, mode3=절대 3차원 평균). joints/tips 는
    관절각 편차 기반(코칭 포인트)으로 차원과 별개."""
    result = {
        "overallScore": int(max(0, min(100, overall_score))),
        "dimensionScores": {k: int(v) for k, v in dimension_scores.items()},
        "joints": build_joints(assessments),
        "tips": build_tips(kismam.top_issues(assessments, n=3), coach_details),
        "comparison": comparison,
        "myVideoUrl": my_video_url,
    }
    if reference_video_url:
        result["referenceVideoUrl"] = reference_video_url
    return result
