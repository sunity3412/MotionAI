"""rot180 inversion pass — 역립 프레임을 180° 돌려 검출부터 다시 보고, 두 패스 불일치를 관절별로 잰다.

quick-260913-udr. 실측 근거 전부 =
`.planning/quick/260913-udr-rot180-inversion-pass/evidence/MEASUREMENTS.md` (아래 § 번호).
전부 로컬 CPU onnxruntime 재현 — 운영과 같은 가중치·전처리. 손조립 추론 경로가
`RTMPose.__call__` 과 최대 좌표차 1.8e-06 px 로 일치하므로 아래 수치는 운영 연산과 같다.
GPU(CUDA EP) 실경로에서의 수치 동일은 Pod 실행으로만 확인된다 — 이 모듈은 그것을 검증하지 않았다.

왜 프레임을 돌리는가 (§1): RTMW-x 의 학습 회전 증강은 ±90° 이고 crop 회전은 0 으로
하드코딩돼 있다(rtmlib `pre_processings.py:159` `rot = 0`). 180°(역립)는 합성으로도 도달할
수 없는 zero-shot 이다. 프레임을 정립으로 돌려 주면 모델은 학습 분포 안에서 본다.

§2 belle 영상 (`user.mp4`, pdshape, 181프레임 stride 3) — 4변형 분해:

  | 변형                                        | 평균 conf | 붕괴 프레임 | 뼈위반 p90 |
  |---------------------------------------------|-----------|-------------|------------|
  | `prod_orig` 현행 1-pass                     | 0.5669    | 9           | 2.108      |
  | `prod_rot`  프레임 180° 회전 (검출+포즈)    | 0.7065    | 0           | 0.776      |
  | `box_orig`  같은 bbox 강제, crop rot=0      | 0.5021    | 9           | 2.340      |
  | `box_rot`   같은 bbox 강제, crop rot=180    | 0.5193    | 0           | 2.163      |

  분해: 붕괴 소멸(9→0)은 포즈 모델 몫. conf +0.14 와 뼈위반 −63% 는 **검출기** 몫.
  crop affine 만 돌리면 절반만 얻는다 — **검출 전에 프레임을 돌려야** 한다. 그래서 이
  모듈은 프레임 픽셀을 돌리고(`rotate_frames_180`) 좌표를 되돌린다(`unrotate_points_180`).

§3 일반화 — 기준 모션 (`ref.mp4`, 정은지, 다른 촬영, 158프레임):
  conf 0.516 → 0.716 (89.2% 프레임 우세) · 붕괴 3 → 0 ·
  R전완 뼈위반 p90 19.877 → 0.825 · R하퇴 20.552 → 0.938.
  정립 프레임 무해: belle 33f 0.635 → 0.644 / 정은지 9f 0.582 → 0.670.

§4 정면 대결 — 지금 운영 ON 인 PR 원근 워프 vs 회전 (`user.mp4` 91프레임 stride 6,
  `detect_inversion` → is_inverted=True ratio=0.685 run=8 — 이 클립에 PR 워프는 실제로 돈다):

  | 변형              | conf   | 붕괴 | 뼈위반 p90 | boneCV        |
  |-------------------|--------|------|------------|---------------|
  | prod 현행 1-pass  | 0.5696 | 5    | 2.257      | 0.524         |
  | `pr_warp` 운영 ON | 0.5471 | 4    | 1.777      | 0.512 (−2%)   |
  | `rot180`          | 0.7083 | 0    | 0.753      | 0.404 (−23%)  |
  | `rot+pr`          | 0.7147 | 0    | 0.712      | 0.375 (−28%)  |

  PR 워프는 원근 정정(몸 중심 광선을 광축에 정렬)이지 회전이 아니다 — 인물이 화면 중앙이면
  H=I 로 아무 일도 안 한다. 180° 문제는 손댄 적이 없다. `rot+pr` 은 추론 3패스라 후속 검토
  대상이고 지금 붙이지 않는다 (R-3: 두 플래그가 같이 켜지면 회전이 이긴다).

§5 계기 — 두 패스 불일치 = ‖p_orig − p_rot180‖ / torso (181프레임 × 17관절, 유효 쌍 3077):

  | 지표      | 불일치                        | RTMW conf                |
  |-----------|-------------------------------|--------------------------|
  | 동적 범위 | 0.014 → 8.03 (570배)          | 0.29 → 0.77 (2.7배)      |
  | 분포      | 이봉 (골짜기 있음)            | 단봉, 골짜기 없음        |

  대표 사례 t=8.1s (09-10 에 "머리카락 위에서 잰 값" 으로 확정된 관절):
    `right_elbow` (관측 실패)  불일치 421px = 0.75 torso   conf 0.434
    `left_hip`    (정상)       불일치  25px = 0.04 torso   conf 0.504

★ 판별력 정정 (코디네이터 2026-09-13 — 위 "18배로 가른다" 는 한 프레임 한 관절 사례였다):
  독립 정답(뼈 길이 항상성 위반 — 두 계기 어느 쪽으로도 정의되지 않음) 대비 AUROC,
  belle 영상 181프레임 × 뼈 8종:  conf 0.807 · 불일치 0.793 · 둘 결합 0.818.
  판별력은 conf 와 대등하다(AUROC 0.793 vs 0.807, 독립 기준). 불일치의 값어치는
  **임계를 자의적으로 정하지 않아도 되는 것**이다 — 분포가 이봉이고 0.33~0.51 torso 에
  골짜기가 있다. conf 는 단봉(p1 0.163 → p99 0.903)이라 그 자리가 없다. 그리고 둘을
  결합하면 0.818 로 둘 중 어느 쪽보다 낫다(후속 검토 대상).
  → 이 모듈은 "불일치가 conf 보다 정확하다" 고 주장하지 않는다. 어디에도 그렇게 쓰지 말 것.

★ torso 정규화는 반드시 **클립 중앙값** 하나 (코디네이터 정정 1 — 버그 예방 박제):
  계획 초안의 "프레임별 두 패스 torso nanmean" 은 붕괴 프레임에서 터진다. 관절이 한 점으로
  뭉갠 프레임은 torso 가 0 이라 프레임별 torso p1 = 0.00 px 였고, 그 결과 불일치 p99 가
  5.98e10 으로 폭주했다 — 하필 우리가 보려는 프레임에서 계기가 폭주한다.
  클립 중앙값(스칼라 1개)으로 바꾸면 같은 데이터·같은 좌표에서 p99 = 3.191 로 정상화된다.
  사람 크기는 클립 내내 거의 일정하므로 중앙값이 옳은 정규화다.
  참고 분포 (belle 181프레임, 클립 중앙 torso 67.2px):
    p1 0.004 · p10 0.015 · p25 0.031 · p50 0.110 · p75 0.637 · p90 1.618 · p99 3.191
  프레임별 torso 를 쓰는 변형은 이 모듈에 남기지 않는다 — "프레임별이 더 정확하지 않나" 는
  함정이다. 되돌리지 말 것.

★ 곡선맞춤 위험 — 이 모듈은 **임계를 정의하지 않는다**:
  표본 = 영상 2편. 이봉성과 골짜기 위치(0.33~0.51)는 표본이 늘면 움직일 수 있다. 그래서
  불일치 **값만** 낸다. 채택 규칙(`choose_pass`)은 클립 게이트 + 프레임 유효성(유한·범위)
  뿐이고 불일치 크기로 채택을 정하지 않는다 (R-4). 감점 억제도 없다 — 감점이 사라지면
  점수가 **올라간다** (`final = max(25, round(100 − min(40, Σ|실행|) − Σ|치명|))`,
  실측 powerspin 62→67, 산술 elbow-twist 63→100). "못 봤다" 가 "완벽하다" 로 번역되는
  것을 막으려면 `wouldBePoints` 동반이 필수이고 그건 별건이다. 이번 범위는 기록만.

왜 좌우 인덱스 스왑이 없는가: 180° 회전은 det=+1 인 진짜 회전이라 손잡이(chirality)가
  보존된다 (`test_rotation_preserves_handedness_flip_does_not` 가 박제). 수평 flip(det=−1)
  이라면 스왑이 필요했을 것이다. 09-10 좌우 팔꿈치 건은 종결됐다 — 다시 열지 말 것.

왜 1차 미검출 프레임은 2차가 검출해도 채택하지 않는가 (R-5): `NoHumanError`·
  `detected_count` 가 1차 기준으로 이미 확정됐다. 검출 집합을 바꾸는 것은 범위 밖이다.
  건수는 `first_missing` 사유로 로그에 남겨 크기를 알 수 있게 한다.

기각된 가설 (§6 — 다시 열지 말 것): 영상 회전 메타데이터 버그(태그 없음, 실제로 거꾸로
  매달려 있음) · 엉뚱한 사람 선택(`kps_batch[0]` 이 최대 박스가 아닌 프레임 0건) ·
  "붕괴 25프레임"(5관절 약식 지표였고 17관절 기준 9 가 맞다).

순수 모듈 규약: numpy 만. AWS/모델/네트워크/cv2/torch 의존 0. PR 원근 워프 모듈도 import
하지 않는다 (R-8 — PR 워프가 나중에 빠져도 회전 모듈이 살아야 한다). 상수는 같은 값으로
자체 선언하고 선례는 주석으로만 인용한다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .skeleton import KEYPOINT_NAMES

# ── 골격 인덱스 ────────────────────────────────────────────────────────────
# COCO body 인덱스 (RTMW 133 의 선두 17 = COCO-17 순서). torso = 어깨 중점 ↔ 엉덩이 중점.
_L_SHOULDER, _R_SHOULDER, _L_HIP, _R_HIP = 5, 6, 11, 12
_TORSO_IDX = (_L_SHOULDER, _R_SHOULDER, _L_HIP, _R_HIP)
_BODY17 = 17

# ── 상수 (임계 아님) ───────────────────────────────────────────────────────
# torso 하한. 이보다 짧으면 어깨·엉덩이가 사실상 한 점이라 나눗셈 분모로 쓸 수 없다.
# 정정 1: 붕괴 프레임의 torso 는 정확히 0 — 프레임별 정규화가 여기서 폭주했다. 이 값
# 미만인 프레임은 클립 중앙값 풀에서 빠지고, 풀이 비면 불일치는 전부 NaN 이다.
_TORSO_EPS = 1e-6

# 역매핑 좌표 허용 마진 (프레임 각 변의 25%). 사지가 프레임을 살짝 벗어나는 정상 좌표는
# 통과시키고, 대탈출 좌표는 프레임 단위 폴백(1차 유지)으로 보낸다.
# PR 선례 inversion_warp.UNWARP_BOUNDS_TOLERANCE 와 같은 값을 자체 선언 (R-8).
BOUNDS_TOLERANCE = 0.25

# ── 채택 사유 (로그 집계 키) ───────────────────────────────────────────────
REASON_ADOPTED = "adopted"
REASON_FIRST_MISSING = "first_missing"
REASON_SECOND_MISSING = "second_missing"
REASON_SECOND_NONFINITE = "second_nonfinite"
REASON_SECOND_OUT_OF_BOUNDS = "second_out_of_bounds"
# 판정 순서 그대로 — 엔진이 카운터 dict 를 이 순서로 초기화해 로그 한 줄로 낸다.
REASONS = (
    REASON_FIRST_MISSING,
    REASON_SECOND_MISSING,
    REASON_SECOND_NONFINITE,
    REASON_SECOND_OUT_OF_BOUNDS,
    REASON_ADOPTED,
)


@dataclass(frozen=True)
class PassChoice:
    """어느 패스를 쓸지 + 그 근거. 근거는 항상 같이 돌려준다 — 로그가 사유별로 집계한다."""

    use_second: bool
    reason: str


# ── 프레임 회전 / 좌표 역매핑 ─────────────────────────────────────────────


def rotate_frames_180(frames: np.ndarray) -> np.ndarray:
    """(T,H,W,C) 프레임 배열을 프레임별 180° 회전한다 — 2차 추론 입력 (§2 `prod_rot`).

    구현은 `frames[:, ::-1, ::-1]` (= 프레임별 `np.rot90(f, 2)`). 결과는 반드시
    C-contiguous 로 만든다 — onnxruntime/rtmlib 입력이 contiguous 여야 한다
    (`evidence/decompose.py:44` 가 `np.ascontiguousarray(np.rot90(img, 2))` 를 쓴 이유).
    dtype 은 보존한다 (uint8 → uint8).

    Raises:
        ValueError: ndim != 4. 단일 프레임(H,W,C)을 넘기면 축이 틀어져 조용히 엉뚱한
        회전이 되므로 받지 않는다.
    """
    arr = np.asarray(frames)
    if arr.ndim != 4:
        raise ValueError(f"rotate_frames_180 expects (T,H,W,C), got ndim={arr.ndim}")
    return np.ascontiguousarray(arr[:, ::-1, ::-1])


def unrotate_points_180(points_xy: np.ndarray, image_width: int, image_height: int) -> np.ndarray:
    """(N,2) 픽셀 좌표를 180° 회전공간 ↔ 원본공간 사이에서 되돌린다.

    x' = (W−1) − x,  y' = (H−1) − y.  자기역원이라 회전공간→원본, 원본→회전공간 둘 다
    이 함수 하나다. 규약은 `evidence/tta_disagree.py:47` 과 자릿수까지 같아야 실측과 같은
    좌표가 나온다 (픽셀 인덱스 0..W−1 을 뒤집는 것이므로 W 가 아니라 W−1 이다 —
    `test_pixel_and_point_conventions_agree` 가 픽셀 규약과의 일치를 박제).

    NaN 은 마스킹하지 않고 NaN 으로 통과한다 — 결측은 결측인 채로 흘러가 `choose_pass` 가
    `second_nonfinite` 로 거른다.
    """
    pts = np.asarray(points_xy, dtype=float)
    out = np.empty_like(pts)
    out[..., 0] = (float(image_width) - 1.0) - pts[..., 0]
    out[..., 1] = (float(image_height) - 1.0) - pts[..., 1]
    return out


# ── 불일치 계기 ────────────────────────────────────────────────────────────


def _torso_series(kps_txy: np.ndarray) -> np.ndarray:
    """(T,K,2) → (T,) torso 길이. 어깨·엉덩이 4점 중 비유한이 있는 프레임은 NaN."""
    pts = kps_txy[:, list(_TORSO_IDX), :2]  # (T,4,2)
    sh_mid = pts[:, :2].mean(axis=1)
    hip_mid = pts[:, 2:].mean(axis=1)
    with np.errstate(invalid="ignore"):
        torso = np.linalg.norm(sh_mid - hip_mid, axis=-1)
    torso[~np.isfinite(pts).all(axis=(1, 2))] = np.nan
    return torso


def torso_length(kps_xy: np.ndarray) -> float:
    """(K,2), K ≥ 13 — 어깨(5,6) 중점과 엉덩이(11,12) 중점 거리. 4점 중 비유한이 있으면 nan.

    프레임 하나의 계기다. **불일치 정규화에는 이 값을 직접 쓰지 않는다** — 클립 중앙값
    (`clip_torso_median`)을 쓴다. 모듈 docstring 의 정정 1 참조.
    """
    k = np.asarray(kps_xy, dtype=float)
    if k.ndim != 2 or k.shape[0] <= _R_HIP or k.shape[1] < 2:
        return float("nan")
    return float(_torso_series(k[None, :, :])[0])


def clip_torso_median(kps_a_txy: np.ndarray, kps_b_txy: np.ndarray) -> float:
    """두 패스의 프레임별 torso 를 전부 모아 유한하고 `_TORSO_EPS` 이상인 값들의 중앙값 1개.

    클립 전체에서 스칼라 하나 — 정정 1 의 요구. 붕괴 프레임(torso 0)은 풀에 들어가지
    않으므로 그 프레임의 불일치도 정상 크기의 사람으로 나눠진다. 풀이 비면 nan.
    """
    pool: list[np.ndarray] = []
    for clip in (kps_a_txy, kps_b_txy):
        arr = np.asarray(clip, dtype=float)
        if arr.ndim != 3 or arr.shape[0] == 0 or arr.shape[1] <= _R_HIP:
            continue
        torso = _torso_series(arr)
        pool.append(torso[np.isfinite(torso) & (torso >= _TORSO_EPS)])
    if not pool:
        return float("nan")
    values = np.concatenate(pool)
    if values.size == 0:
        return float("nan")
    return float(np.median(values))


def joint_disagreement(kps_a_txy: np.ndarray, kps_b_txy: np.ndarray) -> np.ndarray:
    """같은 좌표공간(원본 프레임)의 두 패스 클립 좌표 (T,K,2) × 2 → body-17 불일치 (T,17).

    불일치 = ‖p_a − p_b‖ / torso.  분모 torso 는 **클립 중앙값 스칼라 1개**
    (`clip_torso_median`) — 프레임별이 아니다 (정정 1: 프레임별은 붕괴 프레임에서
    p99 5.98e10 으로 폭주, 중앙값은 3.191).

    반환 규약:
      - 유효 torso 가 클립에 하나도 없으면 전부 NaN.
      - 관절 좌표가 어느 패스에서든 비유한이면 그 (t, j) 만 NaN — 같은 프레임의 다른
        관절은 유효.
      - **inf 를 내지 않는다.** 실측 스크립트의 `+1e-9` 대신 NaN 으로 떨어뜨린다 —
        0 나눗셈이 "매우 큰 불일치" 로 둔갑하면 계기가 거짓말한다.

    Raises:
        ValueError: 두 입력의 형상 계약 위반 (ndim != 3, T 불일치, K < 17). 엔진이 배열을
        직접 조립하므로 이건 데이터가 아니라 프로그래밍 오류다.
    """
    a = np.asarray(kps_a_txy, dtype=float)
    b = np.asarray(kps_b_txy, dtype=float)
    if a.ndim != 3 or b.ndim != 3:
        raise ValueError(f"joint_disagreement expects (T,K,2) x 2, got ndim {a.ndim}/{b.ndim}")
    if a.shape[0] != b.shape[0]:
        raise ValueError(f"joint_disagreement T mismatch: {a.shape[0]} vs {b.shape[0]}")
    if a.shape[1] < _BODY17 or b.shape[1] < _BODY17:
        raise ValueError(f"joint_disagreement needs K >= 17, got {a.shape[1]}/{b.shape[1]}")

    T = a.shape[0]
    out = np.full((T, _BODY17), np.nan)
    if T == 0:
        return out

    torso = clip_torso_median(a, b)
    if not np.isfinite(torso) or torso < _TORSO_EPS:
        return out

    diff = a[:, :_BODY17, :2] - b[:, :_BODY17, :2]
    with np.errstate(invalid="ignore"):
        d = np.linalg.norm(diff, axis=-1) / torso
    d[~np.isfinite(d)] = np.nan
    return d


def disagreement_summary(d: np.ndarray) -> dict:
    """(T,17) 불일치 → 로그용 요약. **판정하지 않는다** — 값만 낸다 (R-4, R-6).

    Returns:
        dict(valid_pairs, p50, p90, max, per_joint) — `per_joint` 는
        `skeleton.KEYPOINT_NAMES` 순으로 `{name: (p50, p90)}`. 유효 쌍 0 이면
        `valid_pairs=0` 에 나머지 nan.
    """
    arr = np.asarray(d, dtype=float)
    if arr.ndim == 1:
        arr = arr[None, :]
    nan = float("nan")
    per_joint: dict[str, tuple[float, float]] = {}
    for j, name in enumerate(KEYPOINT_NAMES):
        col = arr[:, j] if (arr.ndim == 2 and j < arr.shape[1]) else np.empty(0)
        v = col[np.isfinite(col)]
        if v.size == 0:
            per_joint[name] = (nan, nan)
        else:
            per_joint[name] = (float(np.percentile(v, 50)), float(np.percentile(v, 90)))

    valid = np.isfinite(arr) if arr.ndim == 2 else np.zeros(0, dtype=bool)
    n_valid = int(valid.sum())
    if n_valid == 0:
        return {"valid_pairs": 0, "p50": nan, "p90": nan, "max": nan, "per_joint": per_joint}
    values = arr[valid]
    return {
        "valid_pairs": n_valid,
        "p50": float(np.percentile(values, 50)),
        "p90": float(np.percentile(values, 90)),
        "max": float(values.max()),
        "per_joint": per_joint,
    }


# ── 채택 규칙 — 클립 게이트 + 프레임 유효성만 (불일치 크기로 정하지 않는다, R-4) ──


def choose_pass(
    first: tuple[np.ndarray, np.ndarray] | None,
    second_back: tuple[np.ndarray, np.ndarray] | None,
    image_width: int,
    image_height: int,
) -> PassChoice:
    """프레임 하나에 대해 1차/2차 중 어느 것을 쓸지 정한다. 근거(reason)를 항상 같이 돌려준다.

    Args:
        first: 1차 `(kps, scores)` 또는 미검출 None.
        second_back: **이미 원본공간으로 역매핑된** 2차 `(kps_back, scores)` 또는 None.

    판정 순서 (프레임 단위 fail-safe — 전체 폐기 아님):
      first None            → first_missing   (R-5: 1차 미검출은 2차가 잡아도 채택 안 함)
      second None           → second_missing
      133 전량 중 비유한    → second_nonfinite (z 패딩 포함 전량 — 깨진 데이터를 채택하지 않는다)
      body-17 이 [-tol, W+tol] × [-tol, H+tol] 밖 → second_out_of_bounds
      그 외                 → adopted
    """
    if first is None:
        return PassChoice(False, REASON_FIRST_MISSING)
    if second_back is None:
        return PassChoice(False, REASON_SECOND_MISSING)

    kps = np.asarray(second_back[0], dtype=float)
    if kps.ndim != 2 or kps.shape[0] < _BODY17 or kps.shape[1] < 2:
        return PassChoice(False, REASON_SECOND_NONFINITE)
    if not np.all(np.isfinite(kps)):
        return PassChoice(False, REASON_SECOND_NONFINITE)

    body = kps[:_BODY17, :2]
    tol_x = float(image_width) * BOUNDS_TOLERANCE
    tol_y = float(image_height) * BOUNDS_TOLERANCE
    in_x = (body[:, 0] >= -tol_x) & (body[:, 0] <= float(image_width) + tol_x)
    in_y = (body[:, 1] >= -tol_y) & (body[:, 1] <= float(image_height) + tol_y)
    if not bool((in_x & in_y).all()):
        return PassChoice(False, REASON_SECOND_OUT_OF_BOUNDS)
    return PassChoice(True, REASON_ADOPTED)
