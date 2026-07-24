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
import logging
import math
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

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
    """motion_ipsf_map.json lazy load + 모듈 캐시 (`_` 시작 메타 키 제외).

    WR-07: 파일 부재/파싱 실패 시 raise 하지 않고 빈 map 으로 degrade —
    lookup_motion_branch 가 자연히 _SAFE_DEFAULT_BRANCH 로 폴백한다 (배포가
    데이터 파일을 누락해도 매 분석이 unhandled exception 으로 죽지 않음).
    반환 dict 는 캐시의 얕은 복사 — 호출자가 mutate 해도 공유 캐시(Lambda
    컨테이너 재사용 + 스레드 간 공유)가 오염되지 않는다.
    """
    global _MOTION_IPSF_MAP_CACHE
    if _MOTION_IPSF_MAP_CACHE is None:
        try:
            raw = json.loads(_MOTION_IPSF_MAP_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            log.exception("motion_ipsf_map load 실패 — 안전 기본(_SAFE_DEFAULT_BRANCH) 사용")
            raw = {}
        _MOTION_IPSF_MAP_CACHE = {
            k: v for k, v in raw.items() if not str(k).startswith("_")
        }
    return dict(_MOTION_IPSF_MAP_CACHE)


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

def is_reference_free_motion(branch_info: "MotionBranchInfo | None") -> bool:
    """미보유(reference-free) 동작 판정 (Phase 19 TRUST-03 / BLOCKER-1 iter-1).

    copyBranch 단독 분기 금지 — `_SAFE_DEFAULT_BRANCH.copyBranch == "branch2_eunji_reference"`
    이고 실제 등재 branch2 동작도 같은 copyBranch 값을 갖기 때문에 copyBranch 만으로는
    "안전 기본(미등록)" 과 "실 branch2(정은지 등재)" 를 구분할 수 없다. 미등록은
    angleSource='unavailable' + angleFixtureKey/ipsfCode None + officialName 없음 으로
    판정한다 (lookup_motion_branch 가 _SAFE_DEFAULT_BRANCH 를 반환한 상태와 정합).

    None(branch_info 미상) 도 reference-free 로 본다 — 어떤 등재 정보도 없으므로 절대
    트랙(line+stability) 채점이 안전 기본 (fail-closed/raise 아님,
    [[motion-routing-generalize-principle]]).
    """
    if branch_info is None:
        return True
    return (
        branch_info.angleSource == "unavailable"
        and branch_info.angleFixtureKey is None
        and branch_info.ipsfCode is None
        and not branch_info.officialName
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

    # Phase 19 HIGH-1 — stability 가 종합 입력에서 제외되므로(overall_from_dimensions
    # min-of-core) 균등 weightPercent 는 거짓 기여 표시(사용자 오도). 기여 차원
    # (CORE_DIMENSIONS=angle/line)에만 largest-remainder 분배(합=100), 비기여(stability)
    # 차원은 weightPercent=0 + contributesToOverall=false 로 표시.
    contributing = [d for d in dims if d in dimensions.CORE_DIMENSIONS]
    contrib_pcts = _largest_remainder_pct(len(contributing)) if contributing else []
    pct_by_dim = {d: contrib_pcts[i] for i, d in enumerate(contributing)}

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
    for dim in dims:
        score = int(dimension_scores.get(dim, 0))
        deficit = _deficit_summary_for(
            dim, score, angle_worst, line_defs, stab_wobble
        )
        contributes = dim in dimensions.CORE_DIMENSIONS
        out[dim] = {
            # 비기여 차원(stability)은 weightPercent=0 — 거짓 기여 표시 차단 (HIGH-1).
            "weightPercent": pct_by_dim.get(dim, 0),
            "baseline": baselines.get(dim, ""),
            "deficitSummary": deficit,
            # Phase 19 — 종합 기여 여부 (core 차원만 True). UI 가 stability 를
            # 보조 지표로 표시하도록. 옵셔널 계약 필드(legacy doc 미존재 → UI default true).
            "contributesToOverall": contributes,
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
        # WR-03: NaN 방어 — NaN 비교는 항상 False 라 max() 가 임의 키를 고를 수 있다.
        # 산출 helper(line_deficits_by_joint)가 이미 np.isnan 필터하지만 로컬 가드로
        # 두 모듈 떨어진 invariant 에 결합되지 않게 한다 (v != v == NaN).
        finite_line = {k: v for k, v in line_defs.items() if v == v}
        if finite_line:
            worst_key = max(finite_line, key=finite_line.get)
            label = JOINT_LABEL_KO.get(worst_key, worst_key)
            return f"{label} 신전 부족"
        return _GOOD_COPY_BY_DIM["line"]
    if dim == "stability":
        finite_wobble = {k: v for k, v in stab_wobble.items() if v == v}
        if finite_wobble:
            worst_key = max(finite_wobble, key=finite_wobble.get)
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


# ── Phase 13-C: 섹션형 듀얼 coach 조립 + 계층형 cross-fill 폴백 ────────────────
# belle 2026-06-16 [[section-dual-coach-report]]. 토글(택1)을 "둘 다 호출 + 섹션
# 조립"으로 확장. 머지(섞기) 아님 — 출처별 섹션 분리.
#
# 13-C locked 섹션 배분:
#   원인(causes title/explanation) = Gemini (개념적 framing 강함)
#   교정 처방(causes[].fix)         = Cerebras (구체 운동·세트·시간)
#   부상 위험(injuryRisk)           = Cerebras (injuryRisk 강함)
#   강사 확인(coachNote)            = Gemini (강사 철학 존중 톤)
#
# 한쪽 writer 가 해당 관절키를 비웠으면(빈 dict / 키 누락) → 다른 writer 의 같은
# 섹션으로 cross-fill (빈 섹션 0). 양쪽 모두 비면 detail2 생략 → build_tips 의
# 수치 폴백이 detail 만 채운다 (둘 다 실패 = 최후 바닥).
#
# detail2 계약 형상은 불변: {causes:[{title,explanation,fix}], injuryRisk?, coachNote}.
# 출처는 별도 데이터(source 필드)가 아니라 섹션 조립 결과 + 반환 audit dict 로만 표현
# — 벤더명 비노출(13-C locked), 3-way lockstep 최소 변경 (source 필드 추가 금지).


def _entry_detail2(details: dict, joint: str) -> dict | None:
    """writer 결과(details)에서 joint 의 detail2 dict 추출 (없으면 None).

    coach_writer._normalize_entry 가 이미 {detail, detail2?} 로 정규화. causes 가
    비어있으면(빈 list / 키 누락) detail2 자체를 없는 것으로 본다 (cross-fill trigger).
    """
    entry = details.get(joint)
    if not isinstance(entry, dict):
        return None
    d2 = entry.get("detail2")
    if not isinstance(d2, dict):
        return None
    causes = d2.get("causes")
    if not isinstance(causes, list) or not causes:
        return None
    return d2


def _norm_cause_title_explanation(c: dict) -> tuple[str, str]:
    return str(c.get("title", "")), str(c.get("explanation", ""))


def assemble_dual_coach_sections(
    gemini_details: dict | None,
    cerebras_details: dict | None,
    joint_keys: list[str],
) -> tuple[dict, dict]:
    """양쪽 writer 결과를 관절키별 detail2 로 섹션 출처에 따라 조립 (13-C).

    Args:
        gemini_details: GeminiCoachWriter.write() 결과 ({joint: {detail, detail2?}}).
        cerebras_details: CerebrasCoachWriter.write() 결과 (동일 형상).
        joint_keys: 조립 대상 관절키 (보통 top_assessments 의 key — top 3).

    Returns:
        (merged_details, section_audit) 튜플.
        - merged_details: {joint: {detail, detail2?}} — build_tips 가 그대로 소비.
          양쪽 모두 빈 관절키는 detail2 생략 (수치 폴백 진입). detail 은 Gemini 우선,
          없으면 Cerebras, 둘 다 없으면 키 누락 (build_tips fallback).
        - section_audit: {joint: {causes, fix, coachNote, injuryRisk, crossFilled}}.
          각 섹션 출처('gemini'/'cerebras'/None) + cross-fill 된 섹션 이름 list.
          Task 2 의 pipeline 로깅이 소비 (성공/폴백률 실측 전환 근거).
    """
    gemini = gemini_details or {}
    cerebras = cerebras_details or {}
    merged: dict = {}
    audit: dict = {}

    for joint in joint_keys:
        g2 = _entry_detail2(gemini, joint)
        c2 = _entry_detail2(cerebras, joint)

        section_src = {
            "causes": None,
            "fix": None,
            "coachNote": None,
            "injuryRisk": None,
            "crossFilled": [],
        }

        # detail (카드 본문) — Gemini 우선, 없으면 Cerebras.
        g_entry = gemini.get(joint) if isinstance(gemini.get(joint), dict) else {}
        c_entry = cerebras.get(joint) if isinstance(cerebras.get(joint), dict) else {}
        detail = g_entry.get("detail") or c_entry.get("detail")

        if g2 is None and c2 is None:
            # 둘 다 누락 → detail2 생략 (build_tips 수치 폴백 진입). detail 도 비면 키 누락.
            audit[joint] = section_src
            if isinstance(detail, str) and detail.strip():
                merged[joint] = {"detail": detail}
            continue

        # ── 원인(causes title/explanation) = Gemini, 없으면 Cerebras cross-fill.
        if g2 is not None:
            cause_src = g2["causes"]
            section_src["causes"] = "gemini"
        else:
            cause_src = c2["causes"]
            section_src["causes"] = "cerebras"
            section_src["crossFilled"].append("causes")

        # ── 교정 처방(causes[].fix) = Cerebras, 없으면 해당 cause 본인 fix(Gemini).
        if c2 is not None:
            section_src["fix"] = "cerebras"
            cerebras_fixes = [str(c.get("fix", "")) for c in c2["causes"]]
        else:
            section_src["fix"] = section_src["causes"]  # cause 출처와 동일 (Gemini)
            section_src["crossFilled"].append("fix")
            cerebras_fixes = []

        out_causes = []
        for i, c in enumerate(cause_src):
            if not isinstance(c, dict):
                continue
            title, explanation = _norm_cause_title_explanation(c)
            # Cerebras fix 가 있으면 i 번째 처방을 매핑, 없으면 cause 본인 fix.
            if i < len(cerebras_fixes) and cerebras_fixes[i].strip():
                fix = cerebras_fixes[i]
            else:
                fix = str(c.get("fix", ""))
            out_causes.append(
                {"title": title, "explanation": explanation, "fix": fix}
            )

        detail2: dict = {"causes": out_causes}

        # ── 부상 위험(injuryRisk) = Cerebras, 없으면 Gemini cross-fill. 둘 다 없으면 생략.
        injury = None
        if c2 is not None and isinstance(c2.get("injuryRisk"), str) and c2["injuryRisk"].strip():
            injury = c2["injuryRisk"]
            section_src["injuryRisk"] = "cerebras"
        elif g2 is not None and isinstance(g2.get("injuryRisk"), str) and g2["injuryRisk"].strip():
            injury = g2["injuryRisk"]
            section_src["injuryRisk"] = "gemini"
            section_src["crossFilled"].append("injuryRisk")
        if injury is not None:
            detail2["injuryRisk"] = injury

        # ── 강사 확인(coachNote) = Gemini, 없으면 Cerebras cross-fill.
        if g2 is not None and isinstance(g2.get("coachNote"), str) and g2["coachNote"].strip():
            detail2["coachNote"] = g2["coachNote"]
            section_src["coachNote"] = "gemini"
        elif c2 is not None and isinstance(c2.get("coachNote"), str) and c2["coachNote"].strip():
            detail2["coachNote"] = c2["coachNote"]
            section_src["coachNote"] = "cerebras"
            section_src["crossFilled"].append("coachNote")
        else:
            detail2["coachNote"] = "강사와 함께 영상을 보며 확인해 보세요."
            # 출처 없음(둘 다 빈 coachNote) — 기본 문구. None 유지.

        entry_out: dict = {"detail2": detail2}
        if isinstance(detail, str) and detail.strip():
            entry_out["detail"] = detail
        merged[joint] = entry_out
        audit[joint] = section_src

    return merged, audit


# ── Phase 19 TRUST-03: scoringBasis (실제 채점 SOURCE 라벨) ────────────────────
# Mode3 의 허용 scoringBasis = 정확히 4 값. reference_motion 은 **Mode1 전용** —
# Mode3 에 들어오면 거짓 reference 비교 함의(신뢰 문제 재발)이므로 build_mode3 가
# ValueError 로 거부한다 (ITER-3 HIGH-2 + ITER-4 HIGH-2). first reference-free 는
# reference motion 비교가 아니라 절대 트랙(line+stability) 평가이므로 절대 reference_motion
# 라벨을 붙이지 않는다.
MODE3_SCORING_BASIS_REFERENCE_FREE_ABSOLUTE = "reference_free_absolute"
MODE3_SCORING_BASIS_RECOGNIZED_ABSOLUTE = "recognized_motion_absolute"
MODE3_SCORING_BASIS_PREV_PLUS_ABSOLUTE = "previous_analysis_plus_absolute"
MODE3_SCORING_BASIS_PREV_PLUS_REFERENCE_FREE = (
    "previous_analysis_plus_reference_free_absolute"
)
_MODE3_SCORING_BASES: frozenset[str] = frozenset(
    {
        MODE3_SCORING_BASIS_REFERENCE_FREE_ABSOLUTE,
        MODE3_SCORING_BASIS_RECOGNIZED_ABSOLUTE,
        MODE3_SCORING_BASIS_PREV_PLUS_ABSOLUTE,
        MODE3_SCORING_BASIS_PREV_PLUS_REFERENCE_FREE,
    }
)
# user-facing 한국어 라벨 — 정확한 채점 source 를 화면에 노출 (TRUST-03 가시화).
_MODE3_SCORING_BASIS_LABELS: dict[str, str] = {
    MODE3_SCORING_BASIS_REFERENCE_FREE_ABSOLUTE: "기준 동작 없음 — 절대 자세 기준 평가",
    MODE3_SCORING_BASIS_RECOGNIZED_ABSOLUTE: "등재 동작 — 절대 자세 기준 평가",
    MODE3_SCORING_BASIS_PREV_PLUS_ABSOLUTE: "이전 분석 대비 + 절대 자세 기준",
    MODE3_SCORING_BASIS_PREV_PLUS_REFERENCE_FREE: (
        "이전 분석 대비 + 절대 자세 기준 (기준 동작 없음)"
    ),
}

# Mode1 전용 — 정은지 reference 각도와 실제 비교한 채점. Mode3 에는 절대 부재.
MODE1_SCORING_BASIS = "reference_motion"


def build_mode1(
    reference_motion: dict,
    similarity: int,
    segment_scores: dict | None = None,
) -> dict:
    """Mode1(전문가 비교) comparison.

    Phase 19 ITER-4 HIGH-1 — Mode1 의 scoringBasis 는 항상 `reference_motion`
    (정은지 reference 각도와 실제 비교한 채점). 신규 Mode1 doc 에 scoringBasis +
    scoringBasisLabel 을 **항상 emit** (Mode1Comparison schema 의 OPTIONAL 필드 —
    legacy doc 호환). 이 값은 Mode1 에서만 set — Mode3Comparison/build_mode3 로 절대
    전달하지 않는다 (Mode3 에는 reference_motion 이 존재하지 않음).
    """
    athlete = reference_motion.get("athleteName", "")
    out = {
        "mode": "mode1",
        "referenceMotionId": reference_motion["motionId"],
        "referenceMotionName": reference_motion.get("name", ""),
        "athleteName": athlete,
        "similarity": int(max(0, min(100, similarity))),
        "scoringBasis": MODE1_SCORING_BASIS,
        "scoringBasisLabel": (
            f"{athlete} 측정 각도 기준 비교" if athlete else "기준 선수 측정 각도 기준 비교"
        ),
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
    scoring_basis: str | None = None,
    scoring_basis_label: str | None = None,
    recognized_motion_id: str | None = None,
    recognized_motion_name: str | None = None,
) -> dict:
    """자기 성장(mode3) 비교 블록.

    핵심은 '이전과 몇 % 일치'가 아니라 '발전(progress)'이다([[mode3-progress-not-similarity]]).
    절대 차원(라인/균형/안정성)은 기준 없이 산출돼 세션 간 같은 척도이므로,
    deltaFromPrevious = 이번 점수 − 지난 점수 가 진짜 발전을 의미한다.
    첫 분석이면 비교 대상이 없어 절대 점수만 (delta 없음).

    Phase 19 (ITER-2 MEDIUM-2 backward-compat + ITER-3 HIGH-2 4-value enum):
    scoring_basis 미전달(None) 시 기존 dict 정확히 보존 (scoringBasis 키 미추가).
    전달 시에만 scoringBasis + scoringBasisLabel emit. 허용값 = 정확히 4 Mode3 값
    (_MODE3_SCORING_BASES). `reference_motion` 은 Mode1 전용 — Mode3 에 들어오면
    거짓 reference 비교 함의이므로 ValueError (free-form 문자열도 거부).

    Phase 30 (D-04): recognized_motion_id/name 미전달(None) 시 기존 dict 정확히
    보존 (두 키 미추가 — legacy 동형). recognized 필드는 early return 전에 out 에
    추가하므로 첫 분석(is_first=True) mode3 도 실어보낸다 (REVIEW HIGH-3). str 이
    아니면 ValueError (T-30-03 — LLM 유래 값 타입 강제). name 은 truthy 일 때만 emit.
    3중 계약: analysis.ts + models.py + docs/contract.md §4 lockstep.
    """
    if scoring_basis is not None and scoring_basis not in _MODE3_SCORING_BASES:
        raise ValueError(
            f"build_mode3 scoring_basis 는 4 Mode3 값 중 하나여야 함 "
            f"(reference_motion 은 Mode1 전용 — Mode3 불가): {scoring_basis!r}"
        )
    if recognized_motion_id is not None and not isinstance(recognized_motion_id, str):
        raise ValueError(
            f"build_mode3 recognized_motion_id 는 str 이어야 함 (T-30-03): "
            f"{recognized_motion_id!r}"
        )
    if recognized_motion_name is not None and not isinstance(
        recognized_motion_name, str
    ):
        raise ValueError(
            f"build_mode3 recognized_motion_name 는 str 이어야 함 (T-30-03): "
            f"{recognized_motion_name!r}"
        )
    out: dict = {"mode": "mode3", "isFirst": bool(is_first)}
    if scoring_basis is not None:
        out["scoringBasis"] = scoring_basis
        out["scoringBasisLabel"] = (
            scoring_basis_label or _MODE3_SCORING_BASIS_LABELS.get(scoring_basis, "")
        )
    # Phase 30 D-04: recognized 필드는 early return 전에 추가 (첫 분석도 포함).
    # id 가 None 이면 두 키 모두 미추가 = legacy dict 바이트 동일 보존.
    if recognized_motion_id is not None:
        out["recognizedMotionId"] = recognized_motion_id
        if recognized_motion_name:
            out["recognizedMotionName"] = recognized_motion_name
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
    는 파이프라인이 overall_from_dimensions = min-of-core(angle/line) 로 계산
    (stability 는 종합 비기여 — 보조 지표; core 부재 시 절대트랙 단독).
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


def rebuild_tips_for_vision_fault(
    result: dict,
    assessments: list[JointAssessment],
    coach_details: dict | None,
) -> dict:
    """visionVeto applied(실감점) 시 '거의 동일' 일반 팁을 per-joint 코칭 팁으로 재조립.

    quick-260704-fwb follow-up (pod 검증): build_result 는 veto apply **이전**에
    실행되므로 angle>=95 분기가 "거의 동일한 자세" 일반 팁 1개로 tips 를 대체하며
    듀얼 코치 detail2(causes/fix/coachNote)를 통째로 버린다. kip-up 처럼 kismam
    angle=100 인데 vision veto 가 감점한 케이스에선 (1) 카피가 88점·확정 결함과
    모순 (2) 처방 코칭이 유저에게 안 보임.

    apply 이후 pipeline 이 본 함수를 호출해 **표시만** 재조립한다 (채점 무접촉 —
    점수/veto/breakdown 필드 일절 변경 없음):
      - visionVeto.status == 'applied' 일 때만 (applied = 감점 record 존재;
        clean tally 는 not_applicable — 260630-l4e). 그 외 status → 입력 그대로.
      - 현재 tips 가 일반 팁(joint=None 단독 1개)일 때만 — per-joint tips 가 이미
        있으면 그대로 (기존 동작 불변, 하위호환).
      - 조립된 coach_details 에 user-visible 관절 entry 가 있을 때만 — 없으면
        build_tips 수치 폴백이 "평균 0° 차이" 모순 카피를 만들므로 일반 팁 유지.
      - veto faultJoints 관절을 top 목록 선두로 (안정 정렬 — 나머지 상대순서 보존).
    """
    veto = result.get("visionVeto") if isinstance(result, dict) else None
    if not isinstance(veto, dict) or veto.get("status") != "applied":
        return result
    # 33-NEXT — 귀속 저신뢰(역립 광범위-다관절 아티팩트) 시 per-joint 팁 재조립을 건너뛴다.
    # magnitude(감점 record/final)는 그대로 두되, "왼팔꿈치 30°·오른무릎 28°..." 식 8관절
    # 단정이 사용자에게 새는 것을 막는다(belle DECISION 1 "단정형 금지"). 앱 표현 레이어는
    # result["attributionReliability"].aggregateStatement 로 clean aggregate 를 렌더한다.
    attr = result.get("attributionReliability")
    if isinstance(attr, dict) and attr.get("unreliable"):
        return result
    tips = result.get("tips")
    is_generic_only = (
        isinstance(tips, list)
        and len(tips) == 1
        and isinstance(tips[0], dict)
        and tips[0].get("joint") is None
    )
    if not is_generic_only:
        return result
    visible_details = {
        k: v for k, v in (coach_details or {}).items() if not str(k).startswith("_")
    }
    if not visible_details:
        return result
    top = kismam.top_issues(assessments, n=3)
    # coach_details 가 커버하는 관절만 (조립된 코칭 텍스트가 있는 관절 — 수치 폴백
    # "0° 차이" 모순 차단). veto fault 관절 우선, 나머지는 top 순서 보존.
    fault_joints = veto.get("faultJoints") or []
    covered = [a for a in top if a.key in visible_details]
    if not covered:
        return result
    ordered = sorted(covered, key=lambda a: a.key not in fault_joints)
    new_tips = build_tips(ordered, visible_details)
    if not new_tips:
        return result
    out = dict(result)
    out["tips"] = new_tips
    return out


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
    """12 body keypoint flat + axisData polyline → KeypointReport 산출.

    Phase 12 Wave 0B (Plan 12-01) 박제 — KeypointOverlay Wave 1+ 소비.
    Phase 32 (32-14, D-22 1단) — _KEYPOINT_NAMES 8→12 확장을 len() 파생으로
    자동 추종 (발목·팔꿈치 추출 배선 — pose 추론 무변경, 추출만 확장).
    keypoints_2d 에 신규 키 부재 시 기존 fallback 그대로 (0.0, 0.0) + conf 0.

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
            if not math.isfinite(x) or not math.isfinite(y):
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

    # finite guard helper — loop 밖 1회 정의 (WR-06: frame 당 closure 재정의 제거).
    def _safe(v: float) -> tuple[float, bool]:
        fv = float(v)
        if math.isfinite(fv):
            return fv, True
        return 0.0, False

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

    # 길이 invariants — KeypointReport.__post_init__ 도 검증하지만 여기서 명시 raise
    # (WR-06: assert 는 python -O 에서 stripped → 유일 길이 가드가 사라짐).
    if len(data) != T * J * 2:
        raise ValueError(f"data 길이 {len(data)} != {T * J * 2}")
    if len(confidence) != T * J:
        raise ValueError(f"confidence 길이 {len(confidence)} != {T * J}")
    if len(reliability) != T:
        raise ValueError(f"reliability 길이 {len(reliability)} != {T}")
    if len(axis_data) != T * _AXIS_POLYLINE_POINTS * 2:
        raise ValueError(
            f"axis_data 길이 {len(axis_data)} != {T * _AXIS_POLYLINE_POINTS * 2}"
        )
    if len(axis_mask) != T * _AXIS_POLYLINE_POINTS:
        raise ValueError(
            f"axis_mask 길이 {len(axis_mask)} != {T * _AXIS_POLYLINE_POINTS}"
        )

    return KeypointReport(
        # 32-14 version bump: "1.0"(legacy 8관절) → "1.1"(12관절 확장).
        # version 은 참고용 — 소비처 판별 기준은 joints 배열 길이 (capability source).
        version="1.1",
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
