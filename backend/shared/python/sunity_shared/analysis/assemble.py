"""KISMAM 결과 → contract.md §4 AnalysisResult dict 조립.

키 이름은 app/src/types/analysis.ts 와 정확히 일치해야 한다(계약 단일 진실).
Cerebras 문장이 없으면 실제 편차값 기반 폴백 문장 사용(수치 위조 아님).

Phase 12.5 (2026-06-07): dimensionExplanation 추가 — 사용자가 결과 화면에서
"왜 이 점수인지" 를 볼 수 있도록 차원별 baseline + weightPercent + deficitSummary
출력. line/stability deficit 은 점수 산식과 동일 source (dimensions._select_window
+ line_deficits_by_joint + stability_wobble_by_joint) — Codex v3 HIGH-2 정합.
"""

from __future__ import annotations

from . import dimensions, kismam
from .kismam import COACHING_FOCUS, JointAssessment
from .skeleton import JOINT_LABEL_KO

# 이 점수 미만이면 JointScore.issue 노출 (양호하면 생략)
GOOD_SCORE_THRESHOLD = 80

# ── Phase 12.5: dimensionExplanation baseline 카피 ────────────────────────────
# Codex v3 HIGH-1 fix: "IPSF 기준" → "IPSF 실행 기준 참고" (현재 line/stability_score
# 는 generic heuristic 이지 Phase 16 IPSF 정식 통합 X — 과대 주장 회피).

_DIMENSION_BASELINES_MODE1 = {
    "angle": "정은지 측정값 + IPSF 실행 기준 참고",
    "line": "정은지 측정값 + 신전 완성도 (IPSF 실행 기준 참고)",
    "stability": "hold 구간 떨림 (절대 지표)",
}
_DIMENSION_BASELINES_MODE3 = {
    "angle": "이전 영상 대비 관절 각도 일관성",
    "line": "신전 완성도 (실행 기준 참고)",
    "stability": "hold 구간 떨림 (절대 지표)",
}

_GOOD_COPY_BY_DIM = {
    "angle": "관절 각도 안정",
    "line": "신전 자세 안정",
    "stability": "hold 구간 떨림 작음",
}


def _largest_remainder_pct(n: int) -> list[int]:
    """Largest Remainder Method — n 차원 정수 weightPercent, 합 = 100.

    n=3 → [34, 33, 33], n=2 → [50, 50], n=1 → [100], n=0 → [].
    Codex v3 HIGH-3 fix: `Math.round(0.333*100) = 33` × 3 = 99% 박제 박제.
    """
    if n <= 0:
        return []
    base = 100 // n
    remainder = 100 - base * n
    return [base + 1 if i < remainder else base for i in range(n)]


def build_dimension_explanation(
    assessments: list[JointAssessment],
    dimension_scores: dict[str, int],
    comparison: dict | None,
    joint_angles=None,
    profile=None,
) -> dict[str, dict]:
    """차원별 explanation: weightPercent + baseline + deficitSummary.

    Phase 12.5 (Codex v2 + v3 review 반영):
    - mode = comparison["mode"] 직접 추출 (별도 mode 인자 X — drift 방지, v3 MED-1)
    - weightPercent = Largest Remainder Method (합 100% 보장, v3 HIGH-3)
    - baseline = mode-aware (v2 MED-3), "IPSF 실행 기준 참고" 카피 (v3 HIGH-1)
    - deficitSummary = 차원별 산식-정합 source:
      - angle → kismam.top_issues (관절 각도)
      - line → dimensions.line_deficits_by_joint (EXTEND 관절, profile/_select_window 정합)
      - stability → dimensions.stability_wobble_by_joint (inter-frame diff median, 같은 window)
    - 양호 임계 (점수 ≥ 80) 시 deviation 수치 X (오해 회피)
    - 빈 dimension_scores 시 빈 dict 반환 (항상 emit, v3 suggestion)

    Args:
        assessments: kismam.assess 결과 — angle deficit source.
        dimension_scores: 차원별 점수 (1/2/3 차원 모두 박제).
        comparison: build_mode1/build_mode3 출력 dict. "mode" 키 추출.
        joint_angles: pipeline 의 (T, J) ndarray. None 이면 line/stability source 폴백.
        profile: TechniqueProfile. None 이면 line/stability source 폴백.

    Returns:
        dict[dim, {"weightPercent": int, "baseline": str, "deficitSummary": str}].
        키 = dimension_scores.keys() 의 부분 집합.
    """
    dims = list(dimension_scores.keys())
    if not dims:
        return {}

    mode = comparison.get("mode") if isinstance(comparison, dict) else None
    baselines = _DIMENSION_BASELINES_MODE1 if mode == "mode1" else _DIMENSION_BASELINES_MODE3
    pcts = _largest_remainder_pct(len(dims))

    # angle deficit source — kismam.top_issues 의 worst joint
    top = kismam.top_issues(assessments, n=1) if assessments else []
    angle_worst = top[0] if top else None

    # line / stability deficit source — dimensions helpers (산식 정합)
    line_defs: dict[str, float] = {}
    stab_wobble: dict[str, float] = {}
    if joint_angles is not None and profile is not None:
        try:
            line_defs = dimensions.line_deficits_by_joint(joint_angles, profile)
        except Exception:
            line_defs = {}
        try:
            stab_wobble = dimensions.stability_wobble_by_joint(joint_angles, profile)
        except Exception:
            stab_wobble = {}

    out: dict[str, dict] = {}
    for i, dim in enumerate(dims):
        score = int(dimension_scores.get(dim, 0))
        deficit = _deficit_summary_for(
            dim, score, angle_worst, line_defs, stab_wobble
        )
        out[dim] = {
            "weightPercent": pcts[i],
            "baseline": baselines.get(dim, ""),
            "deficitSummary": deficit,
        }
    return out


def _deficit_summary_for(
    dim: str,
    score: int,
    angle_worst: JointAssessment | None,
    line_defs: dict[str, float],
    stab_wobble: dict[str, float],
) -> str:
    """차원별 deficit summary 한 줄 (양호 시 수치 X 카피)."""
    if score >= GOOD_SCORE_THRESHOLD:
        return _GOOD_COPY_BY_DIM.get(dim, "안정")
    if dim == "angle":
        if angle_worst is not None and angle_worst.deviation_deg >= 5:
            return f"{angle_worst.label_ko} {round(angle_worst.deviation_deg)}° 차이"
        return _GOOD_COPY_BY_DIM["angle"]
    if dim == "line":
        if line_defs:
            worst_key = max(line_defs, key=line_defs.get)
            label = JOINT_LABEL_KO.get(worst_key, worst_key)
            return f"{label} 신전 부족"
        return _GOOD_COPY_BY_DIM["line"]
    if dim == "stability":
        if stab_wobble:
            worst_key = max(stab_wobble, key=stab_wobble.get)
            label = JOINT_LABEL_KO.get(worst_key, worst_key)
            return f"{label} hold 구간 떨림"
        return _GOOD_COPY_BY_DIM["stability"]
    return ""


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
    my_video_key: str | None = None,
    joint_angles=None,
    profile=None,
) -> dict:
    """contract AnalysisResult. status='done' 일 때 Firestore result 에 저장.

    dimension_scores = IPSF 실행 차원 점수 (angle/line/stability — 3차원). overall_score
    는 파이프라인이 모드별로 계산 (mode1 = 3차원 평균, mode3 = 절대 차원 평균).
    joints/tips 는 관절각 편차 기반 (코칭 포인트) 으로 차원과 별개.

    Phase 12.5: joint_angles + profile 가 주어지면 dimensionExplanation 출력 (line/
    stability deficit source = dimensions helpers). 둘 다 None 이면 explanation 은
    빈 dict (호환성)."""
    # 박제 (2026-06-06 belle): angle dim 95+ 시 "완벽 수행" 메시지 박제.
    # 편차 거의 0 인 perfect 자세 시 worst 3 박제하면 "0° 차이" 어색.
    # mode 분기 박제 — mode1 만 "정은지 선수" 박제, mode3 박제 = 자기 영상 박제.
    angle_dim_score = dimension_scores.get("angle")
    cmp_mode = comparison.get("mode") if isinstance(comparison, dict) else None
    if angle_dim_score is not None and angle_dim_score >= 95:
        if cmp_mode == "mode1":
            title = "정은지 선수와 거의 동일한 자세입니다"
        else:
            title = "이전 분석과 거의 동일한 자세입니다"
        tips = [
            {
                "joint": None,
                "title": title,
                "detail": (
                    f"관절각 일치도 {int(angle_dim_score)}점 — 자세 차이가 거의 없어요. "
                    "안정성·라인 차원도 함께 확인해 보세요."
                ),
            }
        ]
    else:
        tips = build_tips(kismam.top_issues(assessments, n=3), coach_details)
    result = {
        "overallScore": int(max(0, min(100, overall_score))),
        "dimensionScores": {k: int(v) for k, v in dimension_scores.items()},
        "dimensionExplanation": build_dimension_explanation(
            assessments,
            dimension_scores,
            comparison,
            joint_angles=joint_angles,
            profile=profile,
        ),
        "joints": build_joints(assessments),
        "tips": tips,
        "comparison": comparison,
        "myVideoUrl": my_video_url,
    }
    # 박제 (2026-06-06 belle): myVideoUrl 의 S3 signed URL 은 7일 TTL.
    # mode3 second+ 가 일주일 뒤 prev 영상 fetch 시 만료 → 영상 안 뜸 보고.
    # myVideoKey 박제 → frontend 가 만료 시 GET /playback-url 호출 + fresh sign.
    if my_video_key:
        result["myVideoKey"] = my_video_key
    if reference_video_url:
        result["referenceVideoUrl"] = reference_video_url
    return result
