"""붕괴한 사지 판정 — "관측하지 못한 사지에는 감점을 매기지 않는다"의 순수 판정기.

belle 2026-09-10: *"아는척 하면 안되지."* 카메라 방향 때문에 사지가 렌즈 축으로
포개져 버리면 그 팔·다리의 각도는 우리가 **잰 것이 아니라 추측한 것**이다. 그
추측으로 감점 행과 확대 사진을 만들면 앱이 아무 데도 안 가리키는 사진을 들이민다.

판정 규칙은 **두 조건의 AND** 하나뿐이다.

  붕괴 = 납작함(aspect < COLLAPSE_ASPECT_MAX) AND 단축(L/medL < COLLAPSE_LENGTH_FRAC_MAX)

★ 공선성 단독 사용 금지 — 실측으로 재현된 함정이다. **곧게 편 정상 다리도 공선이다.**
판정가능성 축 3종을 승인 fixture 5대상에 실측한 결과(2026-09-10):

  | 대상                                   | aspect(단축/장축) | 길이비 L/median(L) |
  |----------------------------------------|-------------------|--------------------|
  | 대표 사례 c64afae6 f162 **오른팔**(붕괴) | **0.052**         | **0.46**           |
  | 같은 프레임 **왼팔**(정상)              | **0.748**         | —                  |
  | kip-up f16 곧게 편 다리                 | 0.016~0.042       | **1.16 / 0.88**    |

곧게 편 다리는 붕괴한 팔보다 **더** 납작하다(0.016 < 0.052). 공선성만 쓰면 정립
fixture 5행이 위양성으로 걸린다. 갈라주는 축은 **단축(foreshortening)** — 붕괴한
사지는 길이가 평소의 절반으로 줄고(0.46) 곧게 편 다리는 안 줄어든다(0.88~1.16).

★ 곡선맞춤 위험 박제 — `COLLAPSE_LENGTH_FRAC_MAX` 는 게이트 실패를 본 뒤 **사후에
추가**된 축이고 표본이 5대상뿐이다. 그래서 보수적으로(붕괴 쪽에 붙여) 잡았고,
정립 fixture 에서 하나라도 발화하면 임계를 옮기는 것이 아니라 실패로 본다.
역립 동작 표본이 더 들어오면 재검토 대상이다.

**의심스러우면 붕괴가 아니다.** 이 게이트는 감점을 *없애는* 쪽이므로 결측(NaN)·
0 나눗셈·이름 미상은 전부 False(붕괴 아님)로 떨어진다. 없앨 근거가 확실할 때만 없앤다.

이번 범위에 **신뢰도(conf) 기준은 넣지 않는다** — 같은 실측에서 계기가 위태로운
것이 확인됐다(RTMW conf 가 역립·정립 구분 없이 0.4~0.6 에 몰려 임계가 분포 한가운데에
그어진다). 별건이다.

순수 모듈 규약: numpy 만. AWS/모델/네트워크 의존 0.
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from .reliability import ANGLE_REQUIRED_KEYPOINTS

# ── 임계값 ────────────────────────────────────────────────────────────────
# 단축/장축 상한. 대표 사례 붕괴 팔 0.052 (belle 육안 서명 "가로 12px / 세로 220px"
# = 0.055 와 일치) vs 같은 프레임 정상 팔 0.748 — 한 자릿수 넘게 벌어져 있다.
COLLAPSE_ASPECT_MAX: float = 0.10
# 길이비 상한. 붕괴 팔 0.46 vs 곧게 편 정상 다리 0.88~1.16 사이에 두되 붕괴 쪽에
# 가깝게. **사후 추가 축** — 모듈 docstring 의 곡선맞춤 경고 참조.
COLLAPSE_LENGTH_FRAC_MAX: float = 0.60

# 장축이 이보다 짧으면 세 점이 사실상 한 점이다 — 방향을 못 정하므로 판정하지 않는다.
_DEGENERATE_EPS: float = 1e-9

# 각도 관절이 놓인 **해부학적 사지**의 각도 키.
# ANGLE_REQUIRED_KEYPOINTS 의 `{side}_shoulder_flex`(팔꿈치-어깨-엉덩이)와
# `{side}_hip_flex`(어깨-엉덩이-무릎)는 몸통을 가로지르는 사슬이라 사지가 아니다.
# 그 두 관절의 각도를 실제로 못 보게 만드는 것은 옆에 붙은 팔/다리가 포개지는
# 일이므로, 사지 사슬은 같은 쪽 elbow/knee 사슬에서 가져온다.
# **새 좌표 매핑표를 만들지 않는다** — 3점 좌표는 전부 ANGLE_REQUIRED_KEYPOINTS 에서만 온다.
_LIMB_ANGLE_KEY_BY_PART: dict[str, str] = {
    "elbow": "elbow",
    "shoulder": "elbow",
    "knee": "knee",
    "hip": "knee",
}


def limb_keypoints_for_joint(joint: str) -> tuple[str, str, str] | None:
    """각도 관절 이름 → 그 각도가 놓인 사지의 keypoint 3점 (COCO-17 이름).

    좌표 사슬의 단일 출처는 `reliability.ANGLE_REQUIRED_KEYPOINTS` 다.
    이름을 해석할 수 없으면 None — 호출측은 그때 게이트를 걸지 않는다.
    """
    if not isinstance(joint, str) or "_" not in joint:
        return None
    side, _, part = joint.rpartition("_")
    angle_part = _LIMB_ANGLE_KEY_BY_PART.get(part)
    if angle_part is None or not side:
        return None
    names = ANGLE_REQUIRED_KEYPOINTS.get(f"{side}_{angle_part}_flex")
    if not names or len(names) != 3:
        return None
    return (str(names[0]), str(names[1]), str(names[2]))


def limb_aspect_and_length(p0, p1, p2) -> tuple[float, float]:
    """사지 3점(어깨-팔꿈치-손 / 엉덩이-무릎-발목)의 납작한 정도와 길이.

    aspect = PCA 단축/장축.  length = |p0-p1| + |p1-p2|.

    3점 중 하나라도 결측(NaN/비유한)이면 `(nan, nan)` — 판정 불가를 그대로 흘려보내
    `is_limb_collapsed` 가 False 로 떨어지게 한다(보수적).

    세 점이 사실상 한 점이면(장축 < _DEGENERATE_EPS) aspect = 1.0 을 돌려준다.
    방향을 정할 수 없는 배치를 "가장 납작하다"로 읽으면 좌표가 통째로 0 인 결측
    프레임이 붕괴로 둔갑한다 — 여기서도 의심스러우면 붕괴가 아니다.
    """
    pts = np.asarray([p0, p1, p2], dtype=float)
    if pts.shape != (3, 2) or not np.all(np.isfinite(pts)):
        return float("nan"), float("nan")
    length = float(
        np.linalg.norm(pts[1] - pts[0]) + np.linalg.norm(pts[2] - pts[1])
    )
    centered = pts - pts.mean(axis=0)
    # SVD 우특이벡터 = 주축. 3점뿐이라 비용은 상수.
    _u, _s, vt = np.linalg.svd(centered, full_matrices=False)
    projected = centered @ vt.T
    major = float(projected[:, 0].max() - projected[:, 0].min())
    minor = float(projected[:, 1].max() - projected[:, 1].min())
    if major <= _DEGENERATE_EPS:
        return 1.0, length
    return minor / major, length


def median_limb_length(points) -> float:
    """클립 전체 프레임의 그 사지 길이 중앙값.

    Args:
        points: `(F, 3, 2)` — 프레임별 사지 3점. 결측은 NaN 으로 채워 넣는다.

    Returns:
        유한 길이 표본의 중앙값. 유한 표본이 하나도 없으면 `nan`.
    """
    arr = np.asarray(points, dtype=float)
    if arr.ndim != 3 or arr.shape[1:] != (3, 2) or arr.shape[0] == 0:
        return float("nan")
    seg = np.linalg.norm(arr[:, 1] - arr[:, 0], axis=1) + np.linalg.norm(
        arr[:, 2] - arr[:, 1], axis=1
    )
    finite = seg[np.isfinite(seg)]
    if finite.size == 0:
        return float("nan")
    return float(np.median(finite))


def _finite(value) -> float | None:
    """유한 **수치**만 통과 — 그 외는 None.

    문자열은 `float()` 로 파싱되더라도 거부한다(`moment._unit_conf` 와 같은 규약).
    수치를 문자열로 주는 출처는 깨진 출처이고, 깨진 출처로 감점을 없애면 조용한
    악화가 된다. `bool` 은 int 서브클래스라 명시 배제한다.
    """
    if isinstance(value, bool) or not isinstance(
        value, (int, float, np.floating, np.integer)
    ):
        return None
    v = float(value)
    return v if np.isfinite(v) else None


def is_limb_collapsed(
    aspect: float,
    length: float,
    median_length: float,
    *,
    aspect_max: float = COLLAPSE_ASPECT_MAX,
    length_frac_max: float = COLLAPSE_LENGTH_FRAC_MAX,
) -> bool:
    """납작함 AND 단축 — 둘 다여야 붕괴다.

    (곧게 편 정상 사지는 납작하지만 안 줄어든다. 모듈 docstring 의 실측표 참조.)

    비유한/비수치 입력·0 이하 median 은 전부 False — 0 나눗셈 없이 보수적으로 떨어진다.
    """
    a = _finite(aspect)
    ln = _finite(length)
    med = _finite(median_length)
    if a is None or ln is None or med is None:
        return False
    if med <= 0.0:
        return False
    if a >= float(aspect_max):
        return False
    return (ln / med) < float(length_frac_max)


def collapse_from_pose_frames(pose_frames) -> Callable[[int, str], bool]:
    """`pose_frames` → `(frame_idx, joint) -> 붕괴 여부` (순수).

    프레임 인덱스 도메인은 `pose_frames` 자신의 축이다 — 파이프라인에서 이 축은
    `angles` 행 인덱스와 같고(`angles = compute_joint_angles(to_coco17_array(pose_frames))`),
    감점의 측정 순간(`measured_at` 의 `frame_idx`)도 같은 축이라 변환이 필요 없다.
    (`moment.joint_confidence_from_pose_frames` 와 같은 선례·같은 축.)

    좌표는 `frame.keypoints_2d[COCO 이름].x/.y` 를 그대로 읽는다. keypoint 부재·
    비유한 좌표는 NaN 으로 두고, NaN 이 섞인 프레임은 붕괴 판정에서 False 로 떨어진다.
    길이 중앙값은 클립 전체(유한 표본)에서 한 번만 계산해 캐시한다.
    """
    frames = list(pose_frames or ())

    # 사지별 (F,3,2) 좌표 캐시 — 처음 물어본 사지만 만든다.
    cache: dict[tuple[str, str, str], tuple[np.ndarray, float]] = {}

    def _limb_series(names: tuple[str, str, str]) -> tuple[np.ndarray, float]:
        hit = cache.get(names)
        if hit is not None:
            return hit
        pts = np.full((len(frames), 3, 2), np.nan, dtype=float)
        for t, frame in enumerate(frames):
            kps = getattr(frame, "keypoints_2d", None)
            if not isinstance(kps, dict):
                continue
            for k, name in enumerate(names):
                kp = kps.get(name)
                if kp is None:
                    continue
                try:
                    x = float(getattr(kp, "x"))
                    y = float(getattr(kp, "y"))
                except (TypeError, ValueError, AttributeError):
                    continue
                if np.isfinite(x) and np.isfinite(y):
                    pts[t, k] = (x, y)
        out = (pts, median_limb_length(pts))
        cache[names] = out
        return out

    def _collapsed(frame_idx: int, joint: str) -> bool:
        names = limb_keypoints_for_joint(joint)
        if names is None:
            return False
        try:
            t = int(frame_idx)
        except (TypeError, ValueError):
            return False
        if t < 0 or t >= len(frames):
            return False
        pts, med = _limb_series(names)
        aspect, length = limb_aspect_and_length(pts[t, 0], pts[t, 1], pts[t, 2])
        return is_limb_collapsed(aspect, length, med)

    return _collapsed
