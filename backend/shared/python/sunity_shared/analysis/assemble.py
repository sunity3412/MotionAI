"""KISMAM 결과 → contract.md §4 AnalysisResult dict 조립.

키 이름은 app/src/types/analysis.ts 와 정확히 일치해야 한다(계약 단일 진실).
Cerebras 문장이 없으면 실제 편차값 기반 폴백 문장 사용(수치 위조 아님).

Phase 12.5 (2026-06-07): dimensionExplanation 추가 — 사용자가 결과 화면에서
"왜 이 점수인지" 를 볼 수 있도록 차원별 baseline + weightPercent + deficitSummary
출력. line/stability deficit 은 점수 산식과 동일 source (dimensions._select_window
+ line_deficits_by_joint + stability_wobble_by_joint) — Codex v3 HIGH-2 정합.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import dimensions, kismam
from .dimensions import AxisFrame, compute_axis_frames
from .keypoint_frame import (
    JOINT_KEY_TO_ANGLE_KEY,
    _AXIS_POLYLINE_POINTS,
    _KEYPOINT_NAMES,
    KeypointReport,
)
from .kismam import COACHING_FOCUS, JointAssessment
from .skeleton import JOINT_LABEL_KO

# 이 점수 미만이면 JointScore.issue 노출 (양호하면 생략)
GOOD_SCORE_THRESHOLD = 80


# ── Phase 13-B: motion_ipsf_map 라우팅 객체 (BLOCKER-1 / HIGH-1) ───────────────
# 단일 boolean(isRegistered) 폐기 — copyBranch 와 angleSource 는 직교. 카피 분기는
# copyBranch, coach 프롬프트 각도 출처는 angleSource 가 라우팅. 채점 경로 미진입
# (objectivity / D-05) — 카피/프롬프트 분기 전용.


@dataclass(frozen=True)
class MotionBranchInfo:
    """motion_id → 라우팅 객체 (13-REVIEW-FIXES.md §2, 4차 MEDIUM-1 = dict 아님).

    소비측(app.py / build_result / build_dimension_explanation / coach_writer)은
    attribute 접근 (`branch_info.copyBranch`). bare boolean / dict 아님.
    """

    copyBranch: str
    ipsfCode: str | None
    officialName: str
    angleSource: str
    angleFixtureKey: str | None
    criteriaYaml: str | None
    sourceNote: str


# motion_ipsf_map.json — repo root 기준 (exercise_map._CORRECTIVE_EXERCISES_PATH 패턴
# 정합: analysis → sunity_shared → python → shared → backend / "data").
_MOTION_IPSF_MAP_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "data"
    / "motion_ipsf_map.json"
)
_MOTION_IPSF_MAP_CACHE: dict | None = None

# belle 2026-06-16 DECISION 2 — 미지/미래 동작 안전 기본. branch2 는 정은지 reference
# 인용이고 IPSF 주장을 안 하므로 미확인 동작에 항상 안전 (fail-closed/raise 아님).
# branch1/IPSF citation 을 미확인 동작에 fabricate 하지 않는다는 원래 가드 의도 보존.
_SAFE_DEFAULT_BRANCH = MotionBranchInfo(
    copyBranch="branch2_eunji_reference",
    ipsfCode=None,
    officialName="",
    angleSource="unavailable",
    angleFixtureKey=None,
    criteriaYaml=None,
    sourceNote="안전 기본 (belle 2026-06-16 DECISION 2) — motion_ipsf_map 미등록 motion_id. "
    "branch2 는 IPSF 주장 없는 정은지 reference 카피라 미지 동작에 안전. fail-closed/raise 아님.",
)


def _load_motion_ipsf_map() -> dict:
    """motion_ipsf_map.json lazy load + 모듈 캐시 (`_` 시작 메타 키 제외)."""
    global _MOTION_IPSF_MAP_CACHE
    if _MOTION_IPSF_MAP_CACHE is None:
        raw = json.loads(_MOTION_IPSF_MAP_PATH.read_text(encoding="utf-8"))
        _MOTION_IPSF_MAP_CACHE = {
            k: v for k, v in raw.items() if not str(k).startswith("_")
        }
    return _MOTION_IPSF_MAP_CACHE


def lookup_motion_branch(motion_id: str | None) -> MotionBranchInfo:
    """motion_id → MotionBranchInfo (BLOCKER-1, tuple lookup_motion_ipsf 폐기).

    motion_ipsf_map.json 을 motion_id 로 lookup. 미존재(None/미등록 신규)이면
    belle 2026-06-16 DECISION 2 의 안전 기본 (copyBranch=branch2_eunji_reference)
    반환 — fail-closed/raise/copyBranch="unknown" 아님. 안전 기본은 IPSF 주장을
    하지 않으므로(angleSource=unavailable, ipsfCode=None) 미지 동작에 항상 안전하며,
    build_dimension_explanation 은 분기2 카피("정은지 선수 기준")를 적용한다.
    """
    if not motion_id:
        return _SAFE_DEFAULT_BRANCH
    entry = _load_motion_ipsf_map().get(motion_id)
    if not isinstance(entry, dict) or not entry.get("copyBranch"):
        return _SAFE_DEFAULT_BRANCH
    return MotionBranchInfo(
        copyBranch=entry["copyBranch"],
        ipsfCode=entry.get("ipsfCode"),
        officialName=entry.get("officialName", ""),
        angleSource=entry.get("angleSource", "unavailable"),
        angleFixtureKey=entry.get("angleFixtureKey"),
        criteriaYaml=entry.get("criteriaYaml"),
        sourceNote=entry.get("sourceNote", ""),
    )

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

# ── Phase 13-B: copyBranch 별 baseline 카피 (BLOCKER-1 / HIGH-3) ────────────────
# 180° 는 line(신전/EXTEND) 차원 전용 — angle 차원 baseline 은 동작별 정의 각도(NON-180).
# 분기2 카피는 "세계 심사 기준" / "180°" 를 절대 포함하지 않는다 (criteria 8 게이트).

_DIMENSION_BASELINES_BRANCH1 = {
    "angle": "IPSF 동작별 정의 각도",
    "line": "IPSF 신전 기준 — 해당 동작에서 EXTEND 인 팔꿈치/무릎은 180° 신전",
    "stability": "hold 구간 안정성",
}
_DIMENSION_BASELINES_BRANCH2 = {
    "angle": "정은지 선수 기준 관절 각도",
    "line": "정은지 선수 기준 신전 완성도",
    "stability": "hold 구간 안정성 (절대 지표)",
}

# 분기2 카피 가드 (criteria 8). force_pattern_copy.FORBIDDEN_PHRASES_PHASE9_REGEX
# precedent. "180도" 도 catch (숫자 표기 변형).
BRANCH2_FORBIDDEN_PHRASES: tuple[str, ...] = (
    "세계 심사 기준",
    "IPSF",
    "180°",
    "180도",
)


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


def _baselines_for_branch(
    branch_info: MotionBranchInfo | None, mode: str | None
) -> dict[str, str]:
    """copyBranch 별 baseline 카피 선택 (Phase 13-B BLOCKER-1).

    branch1/branch2 = 분기 카피. unknown/None = 기존 mode-aware baseline
    (의도적 하위호환 폴백 — FallbackRecognizer / motion_id 미등록).
    """
    if branch_info is not None:
        if branch_info.copyBranch == "branch1_ipsf_registered":
            return _DIMENSION_BASELINES_BRANCH1
        if branch_info.copyBranch == "branch2_eunji_reference":
            return _DIMENSION_BASELINES_BRANCH2
    return _DIMENSION_BASELINES_MODE1 if mode == "mode1" else _DIMENSION_BASELINES_MODE3


def build_dimension_explanation(
    assessments: list[JointAssessment],
    dimension_scores: dict[str, int],
    comparison: dict | None,
    joint_angles=None,
    profile=None,
    branch_info: MotionBranchInfo | None = None,
) -> dict[str, dict]:
    """차원별 explanation: weightPercent + baseline + deficitSummary.

    Phase 12.5 (Codex v2 + v3 review 반영):
    - mode = comparison["mode"] 직접 추출 (별도 mode 인자 X — drift 방지, v3 MED-1)
    - weightPercent = Largest Remainder Method (합 100% 보장, v3 HIGH-3)
    - deficitSummary = 차원별 산식-정합 source:
      - angle → kismam.top_issues (관절 각도)
      - line → dimensions.line_deficits_by_joint (EXTEND 관절, profile/_select_window 정합)
      - stability → dimensions.stability_wobble_by_joint (inter-frame diff median, 같은 window)
    - 양호 임계 (점수 ≥ 80) 시 deviation 수치 X (오해 회피)
    - 빈 dimension_scores 시 빈 dict 반환 (항상 emit, v3 suggestion)

    Phase 13-B (BLOCKER-1 / HIGH-3): baseline 카피가 branch_info.copyBranch 로 분기.
    - branch1_ipsf_registered → IPSF 동작별 정의 각도(angle) + EXTEND 180°(line).
    - branch2_eunji_reference → "정은지 선수 기준" — "세계 심사 기준"/"180°" 미포함.
    - copyBranch="unknown" 또는 branch_info is None → 기존 mode-aware baseline = 의도적
      하위호환 폴백(FallbackRecognizer / motion_id 미등록, silent old-copy 아님).
    angleSource 는 카피 텍스트에 영향 X — 각도 출처는 coach 프롬프트에서만 쓰임.
    (ref-invert 처럼 branch1 + eunji_measured 조합도 정상.)

    Args:
        assessments: kismam.assess 결과 — angle deficit source.
        dimension_scores: 차원별 점수 (1/2/3 차원 모두 박제).
        comparison: build_mode1/build_mode3 출력 dict. "mode" 키 추출.
        joint_angles: pipeline 의 (T, J) ndarray. None 이면 line/stability source 폴백.
        profile: TechniqueProfile. None 이면 line/stability source 폴백.
        branch_info: lookup_motion_branch 결과. None 이면 mode-aware baseline 폴백.

    Returns:
        dict[dim, {"weightPercent": int, "baseline": str, "deficitSummary": str}].
        키 = dimension_scores.keys() 의 부분 집합.
    """
    dims = list(dimension_scores.keys())
    if not dims:
        return {}

    mode = comparison.get("mode") if isinstance(comparison, dict) else None
    baselines = _baselines_for_branch(branch_info, mode)
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
        # Phase 12 Wave 0A R2/R4 (Codex 직접 리뷰 2026-06-10):
        # JointScore.targetSource camelCase wiring. 4 enum (reference_motion /
        # previous_analysis / extension_requirement / unavailable) — kismam.assess
        # 의 target_source kwarg 흐름.
        if a.target_source is not None:
            j["targetSource"] = a.target_source
        issue = _issue_text(a)
        if issue:
            j["issue"] = issue
        joints.append(j)
    return joints


def build_tips(
    top: list[JointAssessment], coach_details: dict | None = None
) -> list[dict]:
    """CoachingTip[] 조립. Phase 12.5 T9 (2026-06-07): coach_details 가
    legacy string 또는 신 dict ({"detail": str, "detail2"?: dict}) 둘 다 지원.

    detail2 (causes/injuryRisk/coachNote) = 자세히 모달용. dict 인 경우만 박제,
    없으면 카드 본문만 (이전 동작과 동일).
    """
    details = coach_details or {}
    tips = []
    fallback = lambda a: (
        f"{a.label_ko} 각도가 기준과 평균 {round(a.deviation_deg)}° "
        f"차이가 납니다. 해당 동작 구간을 천천히 교정해 보세요."
    )
    for a in top:
        raw = details.get(a.key)
        tip: dict = {
            "joint": a.key,
            "title": f"{a.label_ko} {COACHING_FOCUS[a.key]}",
        }
        if isinstance(raw, dict):
            tip["detail"] = raw.get("detail") or fallback(a)
            d2 = raw.get("detail2")
            if isinstance(d2, dict) and d2.get("causes"):
                tip["detail2"] = d2
        elif isinstance(raw, str) and raw.strip():
            tip["detail"] = raw
        else:
            tip["detail"] = fallback(a)
        tips.append(tip)
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
    branch_info: MotionBranchInfo | None = None,
) -> dict:
    """contract AnalysisResult. status='done' 일 때 Firestore result 에 저장.

    dimension_scores = IPSF 실행 차원 점수 (angle/line/stability — 3차원). overall_score
    는 파이프라인이 모드별로 계산 (mode1 = 3차원 평균, mode3 = 절대 차원 평균).
    joints/tips 는 관절각 편차 기반 (코칭 포인트) 으로 차원과 별개.

    Phase 12.5: joint_angles + profile 가 주어지면 dimensionExplanation 출력 (line/
    stability deficit source = dimensions helpers). 둘 다 None 이면 explanation 은
    빈 dict (호환성).

    Phase 13-B (HIGH-2): branch_info 를 build_dimension_explanation 으로 forward —
    pipeline 이 build_result 경유이므로 여기서 pass-through 가 끊기면 분기가 무효.
    None 이면 기존 mode-aware baseline (하위호환)."""
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
            branch_info=branch_info,
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


# ── Phase 12 Wave 0B (Plan 12-01) — build_keypoint_report ─────────────────
# KeypointOverlay (Wave 1+) 소비 source. compute_axis_frames (12-00 T4) 결과를
# 받아 KeypointReport 의 axis_data + axis_mask 박제 (UI 자체 계산 차단, A7 해소).
# Codex 직접 리뷰 2026-06-10:
#   R2 — axisData 별도 field, 3-point polyline.
#   R3 — fps required kw-only.
#   R6 — confidence source = clamp(Keypoint2D.visibility, 0, 1).
#   R7 iter-2 — axisData finite only (NaN 0회).
#   H4 iter-4 — early-return 완화 (첫 frame keypoints_2d None 단독은 drop X).


def _clamp_unit(v: float) -> float:
    """clamp [0, 1] — Keypoint2D.visibility → confidence 정규화."""
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return float(v)


def build_keypoint_report(
    pose_frames: list,
    *,
    fps: float,
) -> KeypointReport | None:
    """8 body keypoint flat + axisData polyline → KeypointReport 산출.

    Phase 12 Wave 0B (Plan 12-01) 박제 — KeypointOverlay Wave 1+ 소비.

    Args:
        pose_frames: PoseFrame 시퀀스. 각 frame.keypoints_2d 사용 (R1 RTMW 채움).
        fps: 영상 frame rate (kw-only, R3 정합 — default 제거).

    Returns:
        KeypointReport 또는 None (pose_frames 빈/전수 keypoints_2d None 시).
        개별 frame keypoints_2d=None 은 (0.0, 0.0) placeholder + confidence 0 +
        reliability "low" 강제 (D-12-U6 fallback).

    Raises:
        ValueError: fps <= 0.
    """
    if not isinstance(fps, (int, float)) or fps <= 0:
        raise ValueError(f"fps must be > 0, got {fps!r}")

    # H4 iter-4 — early-return 조건: 빈 list 또는 모든 frame 의 keypoints_2d 가 None.
    if not pose_frames:
        return None
    if not any(getattr(f, "keypoints_2d", None) for f in pose_frames):
        return None

    T = len(pose_frames)
    joints_list = list(_KEYPOINT_NAMES)
    J = len(joints_list)

    data: list[float] = []
    confidence: list[float] = []
    reliability: list[str] = []

    for frame in pose_frames:
        kp = getattr(frame, "keypoints_2d", None)
        frame_reliability = getattr(frame, "reliability", "low") or "low"
        # missing frame fallback — 강제 low.
        if kp is None:
            for _ in range(J):
                data.extend((0.0, 0.0))
                confidence.append(0.0)
            reliability.append("low")
            continue

        any_missing = False
        for name in joints_list:
            coco_key = JOINT_KEY_TO_ANGLE_KEY[name]
            kpt = kp.get(coco_key) if isinstance(kp, dict) else None
            if kpt is None:
                # keypoint 누락 → (0.0, 0.0) + conf 0.
                data.extend((0.0, 0.0))
                confidence.append(0.0)
                any_missing = True
                continue
            # Keypoint2D = (x, y, visibility) — pose_frame.py 정의.
            x = float(getattr(kpt, "x", 0.0))
            y = float(getattr(kpt, "y", 0.0))
            vis_raw = getattr(kpt, "visibility", None)
            # R6 — visibility None → 0.0 + frame "low" 강제.
            if vis_raw is None:
                data.extend((0.0, 0.0))
                confidence.append(0.0)
                any_missing = True
                continue
            # NaN/Inf 좌표 → fallback (0.0, 0.0) + conf 0.
            if not (
                isinstance(x, float)
                and isinstance(y, float)
                and (x == x)  # noqa: PLR0124 — NaN check
                and (y == y)
            ):
                data.extend((0.0, 0.0))
                confidence.append(0.0)
                any_missing = True
                continue
            # finite 검증 (Inf 제거).
            import math as _math

            if not _math.isfinite(x) or not _math.isfinite(y):
                data.extend((0.0, 0.0))
                confidence.append(0.0)
                any_missing = True
                continue
            data.extend((x, y))
            confidence.append(_clamp_unit(float(vis_raw)))

        if any_missing:
            reliability.append("low")
        else:
            # frame_reliability 가 _VALID_RELIABILITY 안 값이면 그대로, 아니면 "low" 강제.
            reliability.append(
                frame_reliability
                if frame_reliability in ("high", "medium", "low")
                else "low"
            )

    # axis_data + axis_mask — compute_axis_frames (12-00 T4) 결과 박제.
    axis_frames: list[AxisFrame | None] = compute_axis_frames(pose_frames)
    axis_data: list[float] = []
    axis_mask: list[bool] = []

    for af in axis_frames:
        if af is None:
            # 전 frame 누락 의미 — placeholder (0.0)*6 + mask all False.
            axis_data.extend((0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
            axis_mask.extend((False, False, False))
            continue
        sx, sy = af.shoulder_mid
        hx, hy = af.hip_mid
        if af.knee_mid is None:
            kx, ky = 0.0, 0.0
            knee_ok = False
        else:
            kx, ky = af.knee_mid
            knee_ok = True
        # finite guard — non-finite → placeholder + mask false (R7 iter-2 — NaN 0회).
        import math as _math

        def _safe(v: float) -> tuple[float, bool]:
            fv = float(v)
            if _math.isfinite(fv):
                return fv, True
            return 0.0, False

        sx_v, sx_ok = _safe(sx)
        sy_v, sy_ok = _safe(sy)
        hx_v, hx_ok = _safe(hx)
        hy_v, hy_ok = _safe(hy)
        kx_v, kx_ok = _safe(kx)
        ky_v, ky_ok = _safe(ky)
        axis_data.extend((sx_v, sy_v, hx_v, hy_v, kx_v, ky_v))
        axis_mask.extend(
            (
                bool(sx_ok and sy_ok),
                bool(hx_ok and hy_ok),
                bool(knee_ok and kx_ok and ky_ok),
            )
        )

    # 길이 invariants — KeypointReport.__post_init__ 가 강제 검증.
    assert len(data) == T * J * 2
    assert len(confidence) == T * J
    assert len(reliability) == T
    assert len(axis_data) == T * _AXIS_POLYLINE_POINTS * 2
    assert len(axis_mask) == T * _AXIS_POLYLINE_POINTS

    return KeypointReport(
        version="1.0",
        joints=joints_list,
        frames=T,
        fps=float(fps),
        data=data,
        confidence=confidence,
        reliability=reliability,
        axis_data=axis_data,
        axis_mask=axis_mask,
        warnings=[],
    )
