"""IPSF 실행 심사기준 기반 점수 차원 (docs/research/폴스포츠-지식.md 보고서 5·6).

신체 부위(상체/코어/하체)가 아니라 심판이 실제로 보는 실행 차원으로 채점한다:

  - angle      각도 정확도  : 관절각 vs 기준(reference) 편차. reference 필요.
                             (mode1=정은지, mode3=이전 영상). kismam.overall_score 사용.
  - line       라인·확장    : '펴야 하는' 사지의 신전 완성도. **기술 조건부** — 어떤
                             관절이 펴져야 하는지는 TechniqueProfile 이 정한다.
  - stability  안정성·홀딩  : 피크/홀딩 구간의 시간축 떨림(분산). 절대 지표.

2026-05-29 재교정: '균형(좌우 대칭)' 차원 제거. IPSF 기술감점 프로토콜(보고서 6 §4)에
좌우 신체 대칭 항목이 없고, 폴 동작 상당수가 의도적 비대칭이라 대칭 페널티가 정상
동작(세계챔피언 포함)을 깎는 위양성이었다. line 도 무조건 180° 가 아니라 기술이 신전을
요구하는 관절(profile.expects_extension)에만 적용 — '의도된 굽힘'을 결함으로 깎지 않는다.

점수 스케일은 kismam.score_from_deviation(가우시안 z=편차/허용오차)을 공유한다.
허용오차(tol)는 IPSF 기준(각도 허용오차 20°)에서 출발한 휴리스틱 — belle 시연
데이터로 튜닝 예정.

Phase 19 D-01 재설계:
  - line_score 에 micro-bent 0점 트랙 추가: 신전 요구 관절이 160°(=180°−20°tol [CITED])
    미만이면 요소 무효(0점) — 비례감점 아님 (19-IPSF §A 트랙1).
  - overall_from_dimensions: 단순평균 → min-of-core(angle/line). stability(떨림)는 종합
    입력에서 분리한다 — 매끄러운 fault(stability 높음)가 평균식에서 종합을 끌어올리는
    인플레 위양성 차단. stability 는 dimension_scores 표시는 유지(보조 지표).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from . import kismam, moment
from .pose_frame import Keypoint2D, PoseFrame
from .skeleton import JOINT_KEYS
from .technique import TechniqueProfile


# Phase 12 Wave 0A R2 (Codex 직접 리뷰 2026-06-10) — 중심축 폴리라인 정의.
# 12-CONTEXT.md: 중심축 = 어깨중심 ↔ 골반중심 ↔ 무릎중심 선.
# 기존 plan 의 axis = midpoint(left_shoulder, right_shoulder) 단일 점 박제는
# UI-SPEC 의 "중심축 선" 과 모순. AxisFrame 폴리라인으로 재정의.

@dataclass(frozen=True)
class AxisFrame:
    """중심축 폴리라인 (R2 정합) — 어깨중심 ↔ 골반중심 ↔ 무릎중심 (옵션).

    Phase 12 Wave 0A R2 (Codex 직접 리뷰 2026-06-10) — 단일 midpoint 폐기,
    3 point 폴리라인 박제. Wave 0B (12-01) 의 `axisData` Firestore field source.

      shoulder_mid: 좌우 어깨 keypoints_2d 중점 (normalized [0, 1]).
      hip_mid: 좌우 골반 keypoints_2d 중점.
      knee_mid: 좌우 무릎 keypoints_2d 중점 (옵션 — keypoint 누락 시 None).

    어깨 또는 골반 keypoint 누락 시 AxisFrame 생성 X (compute_axis_frames 가
    list 안 None 반환). 무릎만 누락 시 knee_mid=None (어깨↔골반 선만).
    """

    shoulder_mid: tuple[float, float]
    hip_mid: tuple[float, float]
    knee_mid: tuple[float, float] | None  # 무릎 keypoint 누락 시 None


def _midpoint(a: Keypoint2D, b: Keypoint2D) -> tuple[float, float]:
    """좌우 keypoint 중점 — Phase 12 axis polyline source."""
    return ((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)


def compute_axis_frames(
    pose_frames: list[PoseFrame],
) -> list[AxisFrame | None]:
    """각 PoseFrame 의 중심축 폴리라인 산출. Phase 12 Wave 0A R2 정합.

    Phase 12 Wave 0A R2 (Codex 직접 리뷰 2026-06-10):
      - 어깨중심/골반중심 둘 다 있으면 AxisFrame 생성 (knee_mid 는 옵션).
      - 어깨 또는 골반 keypoint 누락 → None (외부 fallback 책임).
      - keypoints_2d=None (RTMW R1 fallback) frame → None.

    Args:
        pose_frames: PoseFrame 시퀀스. 각 frame.keypoints_2d 사용.

    Returns:
        list[AxisFrame | None] — len == len(pose_frames). frame 별 1:1 매핑.
    """
    result: list[AxisFrame | None] = []
    for frame in pose_frames:
        kp = frame.keypoints_2d
        if not kp:
            result.append(None)
            continue
        try:
            sm = _midpoint(kp["left_shoulder"], kp["right_shoulder"])
            hm = _midpoint(kp["left_hip"], kp["right_hip"])
        except KeyError:
            # 어깨 또는 골반 keypoint 누락 — axis polyline 산출 불가.
            result.append(None)
            continue
        # knee 는 옵션 — 누락 시 knee_mid=None (어깨↔골반 선만 유지).
        try:
            km = _midpoint(kp["left_knee"], kp["right_knee"])
        except KeyError:
            km = None
        result.append(AxisFrame(shoulder_mid=sm, hip_mid=hm, knee_mid=km))
    return result


# Phase 12 Wave 0A R4 (Codex 직접 리뷰 2026-06-10) — target_angle 산출 출처 enum.
# kismam.TargetSource 와 동일 4 enum (lockstep). dimensions.py 안에서 mode3 first 의
# joint 별 target 산출 helper (_target_source_for_extension) 가 사용.
TargetSource = Literal[
    "reference_motion",        # mode1 = 정은지 measured
    "previous_analysis",       # mode3_progress = 이전 영상 measured
    "extension_requirement",   # mode3_first 의 extension-required joint = IPSF 180°
    "unavailable",             # mode3_first 의 non-extension joint OR data missing
]

# Phase 12 Wave 0A R4 — TargetSource 허용 값 validator (kismam.TargetSource 1:1).
_TARGET_SOURCES: frozenset[str] = frozenset(
    {
        "reference_motion",
        "previous_analysis",
        "extension_requirement",
        "unavailable",
    }
)


def _validate_target_source(value: str) -> str:
    """Phase 12 Wave 0A R4 — TargetSource Literal 입력 검증.

    허용되지 않은 값은 ValueError. mode 분기 미스, typo, 외부 입력 오염 차단.
    """
    if value not in _TARGET_SOURCES:
        raise ValueError(
            f"target_source must be one of {sorted(_TARGET_SOURCES)}, got {value!r}"
        )
    return value


def _target_source_for_extension(
    joint_name: str, profile: TechniqueProfile
) -> tuple[float | None, TargetSource]:
    """mode3 first 의 joint 별 target 산출. Phase 12 Wave 0A R4 정합.

    profile.expects_extension(joint) == True → (180.0, 'extension_requirement')
    profile.expects_extension(joint) == False → (None, 'unavailable')

    IPSF 180° = extension-required joint 의 신전 완성 기준. 그 외 관절은
    의도된 굽힘 (예: chair pose 의 무릎) — 기준 없음.
    """
    if profile.expects_extension(joint_name):
        return 180.0, "extension_requirement"
    return None, "unavailable"

# 차원 키 (contract / app dimensionScores 키와 동일 문자열).
DIM_ANGLE = "angle"
DIM_LINE = "line"
DIM_STABILITY = "stability"
# 기준 영상 없이 산출 가능한 절대 지표 — mode3 첫 분석부터 사용.
ABSOLUTE_DIMENSIONS = (DIM_LINE, DIM_STABILITY)

# 허용오차(도). z=dev/tol 가우시안 → tol 만큼 벗어나면 점수 ~61.
_LINE_TOL_DEG = 20.0      # 완전 신전(180°) 대비 부족분. IPSF 각도 허용오차 20° 기준.
_STABILITY_TOL_DEG = 15.0  # Path T1 (2026-06-05): inter-frame diff median 기준. 정은지 reference 5영상 wobble 측정 6~16° 박제 → 사용자 영상 정상 wobble 범위 박제 정신 정합 (RTMW noise + 자세 미세 변화 흡수). 진짜 떨림 (20°+) 만 FAIL.
# 2026-06-12 belle 결정: tol 25° 완화는 짜맞추기 — talkv 영상 같은 영상인데 angle=59 의 진짜 원인 (시간 정렬 / RTMW 변형 강건성) 우회 X. 15° 원복 + 별도 debug 로 root cause 진단.

_FULL_EXTENSION_DEG = 180.0

# Phase 19 D-01 트랙1 (요소 무효 0점) — micro-bent 임계.
# IPSF: "Fully Extended" 요건 요소를 미세하게 굽히면(micro-bent) 비례감점이 아니라
# 득점 전체가 0점("not awarded"). 스플릿 180° 목표 ±20° 허용 → 160° 미만이면 요소 fail
# [CITED: 19-IPSF-DEDUCTION-NOTES §A 트랙1]. _LINE_TOL_DEG(20°) 와 동일 IPSF 허용오차 근거.
# 보유 sweep 재calibrate 금지 — IPSF 근거(180°−20°tol)에서만.
_SPLIT_FAIL_THRESHOLD_DEG = 160.0


def _as_tj(angles) -> np.ndarray:
    a = np.asarray(angles, dtype=float)
    if a.ndim != 2 or a.shape[1] != len(JOINT_KEYS):
        raise ValueError(f"angles 형상은 (T,{len(JOINT_KEYS)}) 이어야 합니다.")
    return a


def hold_window(angles) -> tuple[int, int]:
    """가장 안정적인(분산 최소) 구간 (start, end). 홀딩=동작이 완성돼 정지한 지점.
    stability(그 구간의 떨림)와 line(그 구간의 대표 포즈) 둘 다 이 구간을 쓴다."""
    a = _as_tj(angles)
    t = a.shape[0]
    if t <= 1:
        return 0, t
    w = max(2, min(t, t // 4))
    best_s, best_v = 0, float("inf")
    for s in range(0, t - w + 1):
        v = float(np.mean(np.std(a[s : s + w], axis=0)))
        if v < best_v:
            best_v, best_s = v, s
    return best_s, best_s + w


def stability_wobble(angles, profile: "TechniqueProfile | None" = None) -> float:
    """Raw inter-frame median wobble (degrees) — stability_score 의 score 변환 전 값.

    Plan 08-01 신설 — Plan 08-02 의 force_signals.py 가 본 helper 를 import 하여
    StabilityMetric.jitter_score (degrees, frame inter median) 산출에 재사용. 산식
    복제 차단 → drift 방지 (Phase 12.5 v4 Codex HIGH-2 패턴 정합).

    jerk_score (deg/sec^3) 는 별도 산출 — Plan 08-02 의 _compute_jerk 가 dt=1/fps
    정규화 박제 (REVIEWS R5).

    Returns:
        float (degrees). frame 부족 (T<2) 시 0.0.
    """
    sliced, _ = _select_window(angles, profile)
    if sliced.shape[0] < 2:
        return 0.0
    inter_frame_diff = np.abs(np.diff(sliced, axis=0))  # (T-1, J)
    median_jerk = np.nanmedian(inter_frame_diff, axis=0)  # (J,)
    return float(np.nanmean(median_jerk))


def stability_score(angles, profile: "TechniqueProfile | None" = None) -> int:
    """홀딩 구간 관절각 안정도 → 가우시안. 낮은 떨림 = 통제된 정지.

    Path R (2026-06-05): inter-frame difference median 알고리즘.
    Phase 12.5 v4 (Codex v3 HIGH-2): `_select_window` 박제 stability_wobble_by_joint /
    line helpers 와 같은 windowing — drift 방지.
    Plan 08-01: wobble 산식이 stability_wobble() helper 로 분리됨 — 본 함수는
    helper 호출 + kismam.score_from_deviation 변환만 담당 (force_signals.py 가
    같은 helper 를 jitter_score 산출에 재사용, drift 차단).
    """
    sliced, _ = _select_window(angles, profile)
    if sliced.shape[0] < 2:
        return 100  # 프레임 부족 시 떨림 측정 불가 — 감점 근거 없음
    wobble = stability_wobble(angles, profile)
    return kismam.score_from_deviation(wobble, _STABILITY_TOL_DEG)


def line_score(angles, profile: TechniqueProfile) -> int | None:
    """라인·확장 점수. 홀딩 구간 대표 포즈에서, profile 이 신전(EXTEND)을 요구한
    관절만 180° 대비 부족분으로 채점한다. 신전 요구 관절이 하나도 없으면(전부 의도적
    굽힘) 라인 평가 대상이 아니므로 None → 해당 차원 생략(가짜 점수 안 만듦).

    Phase 12.5 v4 (Codex v3 HIGH-2): `_select_window` 박제 line_deficits_by_joint /
    extension_deviation 박제 박제 박제 박제 박제 박제 박제 — drift 방지.
    """
    sliced, _ = _select_window(angles, profile)
    if sliced.shape[0] == 0:
        return None
    rep = np.nanmean(sliced, axis=0)
    # 신전 요구 관절(profile.expects_extension)만 평가 — 의도적 굽힘(BENT_OK)은
    # 0점 트랙도 비례감점도 미적용 (Pitfall 4 위양성 차단).
    rep_angles = [
        float(rep[JOINT_KEYS.index(k)])
        for k in JOINT_KEYS
        if profile.expects_extension(k) and not np.isnan(rep[JOINT_KEYS.index(k)])
    ]
    if not rep_angles:
        return None
    # Phase 19 D-01 트랙1 (요소 무효): 신전 요구 관절 중 하나라도 160° 미만(micro-bent)
    # 이면 요소 무효 → 0점 (비례감점 아님, 19-IPSF §A 트랙1).
    if any(a < _SPLIT_FAIL_THRESHOLD_DEG for a in rep_angles):
        return 0
    # 미달 관절 없으면 기존 부족분 가우시안(트랙2) 경로 유지.
    deficits = [max(0.0, _FULL_EXTENSION_DEG - a) for a in rep_angles]
    return kismam.score_from_deviation(float(np.mean(deficits)), _LINE_TOL_DEG)


def extension_deviation(angles, profile: TechniqueProfile) -> np.ndarray:
    """관절별 신전 부족분(도) 벡터 (J,) — 코칭 tips 용. EXTEND 관절만 (180-각),
    그 외는 0. mode3 첫 분석에서 '더 펴주세요' 코칭의 IPSF 라인 근거.

    Phase 12.5 (Codex v3 HIGH-2 fix): `_select_window` 박제 line_score / 신
    line_deficits_by_joint / stability_score 와 동일 windowing 박제 — drift 방지.
    """
    sliced, _ = _select_window(angles, profile)
    rep = np.mean(sliced, axis=0) if sliced.shape[0] > 0 else np.zeros(len(JOINT_KEYS))
    dev = np.zeros(len(JOINT_KEYS), dtype=float)
    for i, k in enumerate(JOINT_KEYS):
        if profile.expects_extension(k):
            dev[i] = max(0.0, _FULL_EXTENSION_DEG - float(rep[i]))
    return dev


# ── Phase 12.5 (v4): 공유 window helper + 차원별 deficit source ────────
# Codex v3 HIGH-2 fix: line_score/stability_score/extension_deviation/신helpers 모두
# 동일 windowing 사용 — `dimensionExplanation` 의 deficitSummary 가 점수 산출과 같은
# frames 만 보도록 보장 (transparency phase 의 핵심 신뢰 조건).


def _select_window(angles, profile: "TechniqueProfile | None" = None) -> tuple[np.ndarray, tuple[int, int]]:
    """공유 window 선택 — profile.hold_window 우선, fallback 자동 (분산 최소).

    line_score, line_deficits_by_joint, stability_score, stability_wobble_by_joint,
    extension_deviation 모두 이 함수 하나만 호출 — drift 방지 (Codex v3 HIGH-2).

    Returns:
        (sliced, (s, e)): sliced = angles[s:e] (shape (T', J)), (s, e) = 윈도우 인덱스.
    """
    a = _as_tj(angles)
    t = a.shape[0]
    if t <= 1:
        return a, (0, t)
    if profile is not None and getattr(profile, "hold_window", None) is not None:
        s, e = profile.hold_window
        s = max(0, min(int(s), t))
        e = max(s, min(int(e), t))
        # WR-05: profile 윈도우가 clamp 후 빈 슬라이스(s == e)로 무너지면 자동
        # hold_window 로 폴백. 빈 슬라이스를 그대로 두면 pipeline 의
        # _hold_window_median_dict 가 {} 를 반환 → assess 가 모든 target_angle=None
        # 으로 표시 target angle 을 조용히 전부 제거한다 (quiet quality 저하).
        if s == e:
            s, e = hold_window(a)
    else:
        s, e = hold_window(a)
    return a[s:e], (s, e)


def line_deficits_by_joint(angles, profile: TechniqueProfile) -> dict[str, float]:
    """관절별 신전 부족분 (EXTEND 관절만). line deficit summary 의 source.

    line_score 와 동일 windowing (`_select_window`) 사용 — 점수 산출과 동일 frames.
    Codex v2 HIGH-1 + v3 HIGH-2 fix.

    Edge cases:
    - sliced 가 비어있음 → 빈 dict
    - profile.expects_extension 이 모든 관절 False → 빈 dict (line score 도 None)
    - NaN frames → np.nanmean 으로 처리 (그래도 NaN 이면 그 관절 제외)
    """
    sliced, _ = _select_window(angles, profile)
    if sliced.shape[0] == 0:
        return {}
    rep = np.nanmean(sliced, axis=0)  # (J,)
    out: dict[str, float] = {}
    for i, k in enumerate(JOINT_KEYS):
        if profile.expects_extension(k) and not np.isnan(rep[i]):
            out[k] = max(0.0, _FULL_EXTENSION_DEG - float(rep[i]))
    return out


# ── quick-260801-gbk: 감점을 "어느 프레임에서 쟀는가" ─────────────────────
# extension_deviation / line 집계는 window 안 프레임들을 평균으로 뭉개 시간축을
# 버린다. 아래 두 helper 는 그 window 를 다시 열어 **집계값에 가장 가까운** 프레임을
# 돌려준다. 최대 부족 프레임(argmax)이 아니다 — 집계가 mean 인데 max 프레임을
# 가리키면 record 가 보고한 값과 다른 순간을 지목하게 되고, 각도 jitter 가 큰
# 프레임이 뽑혀 확대비교가 지금보다 나빠진다.
#
# windowing 은 반드시 `_select_window` 경유 (이 파일 286-297 의 drift 방지 규율).
# 새 windowing 상수 0. extension_deviation / line_score 본체 무접촉 — 점수 substrate
# 를 만드는 코드는 이 helper 를 호출하지 않는다.
#
# quick-260802-tie: 두 helper 의 최근접 선택을 `moment.select_moment_index` 하나로
# 모았다. 규칙(집계값 최근접)은 그대로이고, **거리가 실질적으로 같은 후보가 여럿일
# 때만** keypoint 신뢰도로 가른다. `frame_confidence` 미전달이면 종전 argmin 과
# byte-동일 — 신규 임계 0, 게이트 완화 0.


def extension_representative_frame(
    angles,
    profile: "TechniqueProfile | None",
    joint_key: str,
    target_deficit: float,
    *,
    frame_confidence=None,
) -> int | None:
    """`joint_key` 의 per-frame 180° 부족분이 `target_deficit` 에 가장 가까운 프레임.

    `target_deficit` 은 record 가 실제로 보고한 집계값(extension_deviation 이 낸
    관절별 부족분)이다. 재계산하지 않고 받아 쓴다 — 재계산이 없으면 drift 도 없다.

    frame_confidence (quick-260802-tie): `(절대 프레임, joint_keys) -> 0..1 | None`.
    거리가 동점인 후보들 사이에서만 쓰인다(`moment.TIE_EPS`). None(default)=종전 산출.

    Returns:
        `_select_window` 구간 기준 **절대** 프레임 인덱스. window 가 비었거나 유한
        각도가 하나도 없으면 None(fail-closed).
    """
    if joint_key not in JOINT_KEYS:
        return None
    sliced, (s, _e) = _select_window(angles, profile)
    if sliced.shape[0] == 0:
        return None
    col = np.asarray(sliced[:, JOINT_KEYS.index(joint_key)], dtype=float)
    finite = np.isfinite(col)
    if not finite.any():
        return None
    deficits = np.maximum(0.0, _FULL_EXTENSION_DEG - col)
    gaps = np.where(finite, np.abs(deficits - float(target_deficit)), np.inf)
    idx = moment.select_moment_index(
        gaps,
        confidence=(
            None
            if frame_confidence is None
            else lambda k: frame_confidence(int(s) + int(k), (joint_key,))
        ),
    )
    if idx is None:
        return None
    return int(s) + int(idx)


def line_representative_frame(
    angles,
    profile: "TechniqueProfile | None",
    joint_keys,
    target_deficit: float,
    *,
    frame_confidence=None,
) -> int | None:
    """`joint_keys` per-frame 평균 부족분이 `target_deficit` 에 가장 가까운 프레임.

    `joint_keys` 는 line 집계값을 실제로 만든 관절 집합이어야 한다 — 호출측이
    그 목록을 그대로 넘긴다(여기서 다시 고르지 않는다).

    frame_confidence (quick-260802-tie): 동점 후보 사이에서만 쓰이는 신뢰도 조회.
    집계에 실제로 기여한 관절 집합 전체를 함께 넘긴다 — 그 중 하나라도 신뢰도를
    모르면 그 후보는 최근접 후보를 이기지 못한다(fail-closed).

    Returns:
        절대 프레임 인덱스. 유효 관절/유한 프레임이 없으면 None(fail-closed).
    """
    keys = tuple(k for k in (joint_keys or ()) if k in JOINT_KEYS)
    cols = [JOINT_KEYS.index(k) for k in keys]
    if not cols:
        return None
    sliced, (s, _e) = _select_window(angles, profile)
    if sliced.shape[0] == 0:
        return None
    sub = np.asarray(sliced[:, cols], dtype=float)
    deficits = np.maximum(0.0, _FULL_EXTENSION_DEG - sub)
    gaps = np.full(sub.shape[0], np.inf, dtype=float)
    target = float(target_deficit)
    for t in range(sub.shape[0]):
        row = deficits[t]
        row_finite = row[np.isfinite(row)]
        if row_finite.size == 0:
            continue  # 그 프레임은 후보 아님 — 평균을 만들 수 없다.
        gaps[t] = abs(float(row_finite.mean()) - target)
    if not np.isfinite(gaps).any():
        return None
    idx = moment.select_moment_index(
        gaps,
        confidence=(
            None
            if frame_confidence is None
            else lambda k: frame_confidence(int(s) + int(k), keys)
        ),
    )
    if idx is None:
        return None
    return int(s) + int(idx)


def stability_wobble_by_joint(angles, profile: "TechniqueProfile | None" = None) -> dict[str, float]:
    """관절별 inter-frame diff median (windowed). stability deficit summary source.

    stability_score 와 동일 windowing (`_select_window`) + 동일 산식 (inter-frame
    abs diff median). `_STABILITY_TOL_DEG=15` 와 같은 임계값 의미.
    Codex v2 HIGH-2 + v3 HIGH-2 fix.

    Edge cases:
    - sliced shape[0] < 2 (single frame) → 빈 dict (떨림 측정 불가)
    - NaN frames → np.nanmedian 으로 처리, 그래도 NaN 인 관절 제외
    """
    sliced, _ = _select_window(angles, profile)
    if sliced.shape[0] < 2:
        return {}
    inter_frame_diff = np.abs(np.diff(sliced, axis=0))  # (T-1, J)
    median = np.nanmedian(inter_frame_diff, axis=0)  # (J,)
    out: dict[str, float] = {}
    for i, k in enumerate(JOINT_KEYS):
        if not np.isnan(median[i]):
            out[k] = float(median[i])
    return out


def absolute_dimension_scores(angles, profile: TechniqueProfile) -> dict[str, int]:
    """기준 영상 없이 산출하는 절대 차원 점수. 항상 stability, 신전 관절이 있으면 line.
    mode3 첫 분석 + 모든 분석의 절대 지표 부분."""
    out: dict[str, int] = {}
    ls = line_score(angles, profile)
    if ls is not None:
        out[DIM_LINE] = ls
    out[DIM_STABILITY] = stability_score(angles, profile)
    return out


# Phase 19 D-01 — 종합 입력에 기여하는 core 차원 (stability 분리).
# stability(떨림)는 절대 보조 지표로 표시는 유지하되 종합 입력에서 제외한다 — 매끄러운
# fault(stability 높음 + angle/line 낮음)가 평균식에서 종합을 끌어올리는 인플레 위양성
# 차단 (deferred-items 근본원인). 19-IPSF §B: 기술 감점 트랙은 요소 성공과 무관한 자세
# 품질을 보지만, 종합 지배는 core 기하 차원(angle/line)이 맡는다.
CORE_DIMENSIONS = (DIM_ANGLE, DIM_LINE)


def overall_from_dimensions(dimension_scores: dict[str, int]) -> int:
    """종합 점수 = core 차원(angle/line) 의 min — 단일 major 차원이 종합을 지배한다.

    Phase 19 D-01 — 단순평균 교체. 평균은 stability(높음)가 core(낮음)를 희석/인플레해
    위양성을 만들었다. min-of-core 로 가장 낮은 기하 차원이 종합을 끌어내린다 (단일 major
    fault 지배 정신 정합). stability 는 종합 입력에서 제외 (dimension_scores 표시는 유지).

    - core 차원(angle/line)이 하나라도 있으면 → min(core).
    - core 가 하나도 없으면 → 절대트랙(stability) 단독 사용 (mode3 first 등, 19-IPSF §B).
    - 빈 dict → 0.
    입력 dict 는 변형하지 않는다 (키/순서 보존, Pitfall 2).
    """
    core = [v for k, v in dimension_scores.items() if k in CORE_DIMENSIONS]
    if core:
        return int(round(min(core)))
    vals = list(dimension_scores.values())
    return int(round(min(vals))) if vals else 0
