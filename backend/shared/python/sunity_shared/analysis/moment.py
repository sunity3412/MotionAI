"""측정 순간(대표 프레임) 선택의 공통 규칙 — 표시 전용, 채점 무접촉.

quick-260801-gbk 가 감점 record 마다 "이 값을 어느 프레임에서 쟀는가"(`atFrameIdx`)
를 방출하면서 정한 규칙은 하나다 — **그 record 가 보고한 집계값에 가장 가까운 프레임**.
argmax(최대 편차 프레임)는 금지다: 집계가 median/mean 인데 최대 편차 프레임을 가리키면
record 가 보고한 값과 다른 순간을 지목하고, jitter 프레임을 확대해 지금보다 나빠진다
(`motiondtw.py` per_joint_representative_frames 독스트링 근거).

quick-260802-tie 는 그 규칙의 **의미를 바꾸지 않고** 동점 처리만 정한다.

이유(오케스트레이터 실측, power-spin 실 doc): 다리 keypoint 신뢰도가 프레임마다 널뛴다.
같은 동작 구간 안에서 인접 세 프레임의 발목 신뢰도가 0.180 → 0.463 → 0.746 으로 움직이는데
표시 게이트(`fault_zoom._KP_CONF_MIN`)는 그 사이에 있다. 그래서 사이각·각도가 그려지느냐가
**어느 프레임에 걸리느냐에 달린 우연**이 된다. 집계값과의 거리가 실질적으로 같은 후보가
여럿이라면, 그중 신뢰도가 높은 프레임을 고르는 편이 같은 값을 더 잘 보여준다.

**이 모듈은 "찾아 나서지" 않는다.** 신뢰도는 오직 동점을 가르는 데만 쓰이고, 동점 후보가
없으면 산출은 종전과 byte-동일하다. 게이트(`_KP_CONF_MIN`)는 여기서 읽지도 바꾸지도
않는다 — 이 사이클은 게이트를 여는 것이 아니라 게이트 앞에서 더 나은 후보를 고르는 것이다.

채점 무접촉: 여기서 고른 프레임은 `measured_at` out-param 을 거쳐 표시 계층
(확대비교 카드 앵커)까지만 간다. `deduction_engine.tally` 의 입력(md)에도, record 의
`points`/`measuredValue` 에도 닿지 않는다.
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from .skeleton import JOINT_ANGLES

# 감점 record 가 publish 하는 값의 소수 자릿수 — `deduction_engine` 의 record 방출이
# `measured_value`/`deviation` 을 이 자릿수로 반올림한다. 여기 숫자를 손으로 맞춰 둔
# 것이 아니라 **엔진의 실제 출력에서 되읽어 게이트가 잠근다**
# (`test_moment_tiebreak.py::test_tie_eps_is_the_record_published_resolution` —
# 엔진에 소수점 아래가 긴 값을 먹여 방출된 자릿수를 세고 이 상수와 대조한다).
RECORD_VALUE_DECIMALS = 2

# 동점 허용오차. **"실질적으로 같다"의 정의를 임의로 고르지 않는다** — record 가
# 자기 값을 publish 하는 해상도가 곧 그 정의다. 두 후보의 집계값 거리 차이가 이보다
# 작으면, 그 차이는 record 가 말하는 어떤 것으로도 드러나지 않는다("이 값을 여기서
# 쟀다"는 주장은 record 가 publish 한 값에 대한 주장이므로, record 가 구분하지 못하는
# 차이는 주장을 구분하지도 못한다).
#
# 상한도 이 값이 스스로 준다: 허용오차 안의 두 후보는 집계값을 사이에 두더라도 각도가
# 서로 2×TIE_EPS 이상 벌어질 수 없고(같은 쪽이면 TIE_EPS 이내), 그 크기는 RTMW jitter
# (도 단위)보다 두 자릿수 아래다. 즉 이 tie-break 는 창 전체를 훑는 argmax 로 번질 수
# 없다.
TIE_EPS = 10.0 ** -RECORD_VALUE_DECIMALS

# (frame_idx, joint_keys) -> 0..1 신뢰도 | None(판정 불가)
FrameConfidence = Callable[[int, "tuple[str, ...]"], "float | None"]


def _unit_conf(value) -> float | None:
    """0..1 유한 **수치** 신뢰도만 통과 — 그 외는 전부 None(판정 불가, fail-closed).

    문자열은 `float()` 로 파싱되더라도 거부한다. 신뢰도 출처가 문자열을 주는 상황은
    출처가 깨진 것이고, 깨진 출처로 표시 프레임을 옮기면 조용한 악화가 된다.
    `bool` 은 int 서브클래스라 명시 배제(True 가 1.0 으로 통과하면 최고 신뢰가 된다).
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, np.floating,
                                                        np.integer)):
        return None
    v = float(value)
    if not np.isfinite(v) or v < 0.0 or v > 1.0:
        return None
    return v


def select_moment_index(gaps, *, confidence=None) -> int | None:
    """집계값 최근접 후보의 index — **동점일 때만** 신뢰도로 가른다 (순수).

    Args:
        gaps: |후보별 값 − 집계값| 시퀀스. 비유한(NaN/inf)은 후보에서 제외.
        confidence: `(index) -> 0..1 | None`. index 는 `gaps` 안의 위치다 —
            프레임 공간 변환은 호출측이 소유한다(이 모듈은 프레임 축을 모른다).
            None 이면 종전 argmin 과 **byte-동일**.

    Returns:
        `gaps` 안의 index. 유한 후보가 하나도 없으면 None(fail-closed).

    무회귀 보장 — 아래 셋 중 하나라도 참이면 종전 argmin 그대로다:
      · `confidence` 미전달 (신뢰도 출처 없음)
      · 최근접 후보의 신뢰도가 판정 불가(None) — 비교 기준점이 없으면 가르지 않는다
      · 허용오차 안에서 최근접 후보를 **엄격히 이기는** 후보가 없음 (동률은 유지)
    """
    arr = np.asarray(gaps, dtype=float)
    if arr.ndim != 1 or arr.size == 0:
        return None
    finite = np.isfinite(arr)
    if not finite.any():
        return None
    masked = np.where(finite, arr, np.inf)
    # 종전 산출 — np.argmin 은 동점에서 첫 index 를 준다(결정론).
    i_min = int(np.argmin(masked))
    if confidence is None:
        return i_min
    best_conf = _unit_conf(confidence(i_min))
    if best_conf is None:
        return i_min
    best = i_min
    tie_hi = float(masked[i_min]) + TIE_EPS
    for i in range(int(arr.size)):
        if i == i_min or not bool(finite[i]) or float(masked[i]) > tie_hi:
            continue
        c = _unit_conf(confidence(i))
        # 엄격 부등호 — 동률이면 최근접(=종전 선택)을 유지한다.
        if c is not None and c > best_conf:
            best, best_conf = i, c
    return best


def joint_confidence_from_pose_frames(pose_frames) -> FrameConfidence:
    """`pose_frames` → `(frame_idx, joint_keys) -> 신뢰도 | None` (순수).

    프레임 인덱스 도메인은 `pose_frames` 자신의 축이다 — 파이프라인에서 이 축은
    `angles` 행 인덱스와 같다(`angles = compute_joint_angles(to_coco17_array(pose_frames))`).
    `measured_at` 의 `frame_idx` 도 같은 축이므로 변환이 필요 없다.

    **집계는 최솟값이다.** 관절각 하나는 keypoint 3점(`skeleton.JOINT_ANGLES`)으로
    이뤄지고, 표시 게이트(`fault_zoom._high_conf_pts`)는 그 3점이 **전부** 임계 이상일
    때만 각을 그린다. 그래서 게이트가 실제로 보는 양은 최솟값이다. 평균을 쓰면 신뢰도
    높은 골반이 무너진 발목을 가려, 고른 프레임에서 정작 각이 안 그려진다 — 이
    사이클이 없애려는 현상 그 자체다.

    keypoint 가 없거나 visibility 가 0..1 유한이 아니면 **None**(판정 불가). 0.0 으로
    보정하지 않는다 — 모르는 것과 낮은 것은 다르고, 모를 때는 종전 선택을 유지한다.
    """
    frames = list(pose_frames or ())

    def _conf(frame_idx: int, joint_keys) -> float | None:
        try:
            t = int(frame_idx)
        except (TypeError, ValueError):
            return None
        if t < 0 or t >= len(frames):
            return None
        kps = getattr(frames[t], "keypoints_2d", None)
        if not isinstance(kps, dict):
            return None
        worst: float | None = None
        for jk in joint_keys or ():
            triple = JOINT_ANGLES.get(jk)
            if triple is None:
                return None
            for name in triple:
                c = _unit_conf(getattr(kps.get(name), "visibility", None))
                if c is None:
                    return None
                if worst is None or c < worst:
                    worst = c
        return worst

    return _conf
