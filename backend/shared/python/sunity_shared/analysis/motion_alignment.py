"""MotionMatch → 초 단위 정렬 앵커 + tier. 표현/재생 전용, 채점 무접촉 (28-CONTEXT D-01~D-03).

`reference_dtw_match`(motiondtw.MotionMatch)를 초 단위 앵커(0.5s 간격, flat float 쌍) +
tier(D-02 사다리) + distance 로 변환하는 순수 함수. 방출(28-04)과 소비(28-06)가 공유할
정렬 데이터의 단일 산출 지점.

fps 도메인 함정 (28-RESEARCH Pitfall 1):
  학생 angles 는 9fps, reference angles 는 18fps(phase4_v1 — 28-01 live doc 실측으로 봉인).
  path 의 ref_idx 는 18fps 공간의 절대 인덱스다. 인덱스로 방출하면 정은지 시각이 2배로
  튄다 → **초 단위로만 방출**한다(uSec = user_frame/user_fps, rSec = ref_idx/ref_fps).
  fps 는 doc 메타에서 읽는다 — 18.0 하드코딩 금지(재처리 시 방어).

distance 임계 출처 (calibration-source-hard-gate):
  DISTANCE_T1/T2 = vision_veto H4 프로덕션 상수(_ALIGN_GLOBAL_T1=8.0 / _ALIGN_GLOBAL_T2=25.0)
  값 재사용. 자기 sweep 재보정이 아니다. cross-import 대신 값을 복제하고(순수 모듈에
  vision_veto 의 Gemini 인접 의존을 끌어오지 않기 위함) Task 2 의 lockstep 테스트로 drift 를
  차단한다. 경로 부분 붕괴(1:N 극단 런)는 별도 임계를 발명하지 않고 앵커 구간 기울기 클램프
  위반으로 표면화시킨다 — belle 고정 클램프(RATE_MIN 0.5 ~ RATE_MAX 2.0)가 구조적 기준(D-02).

채점 무접촉: 채점 경로(per_joint_deviation/kismam/dimensions) import 0, veto still 경로 무접촉.
결정론: 정렬/median 만 사용, 랜덤/시간 의존 0.

D-16 (32-CONTEXT): 저신뢰(distance > DISTANCE_T2)도 disabled 로 버리지 않고 trim_only 로
  방출해 sanity 검증된 anchors("시작점 맞춤")를 보존한다 — belle 최우선 수리. 진짜
  degenerate 3종(invalid_fps/empty_path/insufficient_anchors)과 첫 anchor 가 타임라인
  범위 밖/non-finite 인 이상치만 disabled 로 남는다(파생 offset garbage 차단, 리뷰 MEDIUM).
"""

from __future__ import annotations

import math

# 프로덕션 distance 임계 — vision_veto._ALIGN_GLOBAL_T1/T2 값 재사용 (cross-import 대신
# 값 복제 + Task 2 lockstep 테스트로 drift 차단; D-03 calibration-source-hard-gate).
DISTANCE_T1 = 8.0   # == vision_veto._ALIGN_GLOBAL_T1 (글로벌 1차 임계)
DISTANCE_T2 = 25.0  # == vision_veto._ALIGN_GLOBAL_T2 (글로벌 2차 임계)

# 배속 클램프 — belle 고정값 (28-CONTEXT specifics). app/src/lib/alignmentWarp.ts 와 lockstep.
RATE_MIN = 0.5
RATE_MAX = 2.0

# 학생 타임라인 앵커 간격(초). 20s 영상 ~80 float → Firestore 40k index-entry 회피
# (analyses-index-exemption-fix 운영 스텝 불필요).
ANCHOR_STEP_S = 0.5

# 앵커 flat float 상한 — validator(28-03) 상한과 lockstep. 초과 시 step 정수배 확대.
MAX_ANCHOR_FLOATS = 512

MOTION_ALIGNMENT_VERSION = "ma-v1"


def _disabled(distance: float, reason: str) -> dict:
    """degenerate 방출 (W3) — build 불가를 legacy 필드 부재와 구분.

    28-07 배너는 필드 부재(legacy)만 대상 — degenerate 도 방출해 '재분석하면 적용'
    과약속 루프를 차단한다 (checker W3). 빈 anchors 는 28-03 validator 의 disabled
    예외를 통과하는 형상 (역불변식 — disabled 만 빈 anchors 허용).
    """
    return {
        "version": MOTION_ALIGNMENT_VERSION,
        "source": "dtw",
        "tier": "disabled",
        "reason": reason,
        "anchors": [],
        "anchorCount": 0,
        "distance": float(distance),
    }


def build_motion_alignment(match, *, user_fps: float, ref_fps: float) -> dict | None:
    """MotionMatch → 초 단위 정렬 앵커 + tier dict (순수, 결정론).

    match=None → None (**유일한 None 케이스** — 정렬 컨텍스트 부재 = 미방출 legacy).
    degenerate(empty_path/invalid_fps/insufficient_anchors) → tier 'disabled' 방출.
    반환 dict: {version, source, tier, anchors(flat float), anchorCount, distance}
    (+ tier != 'warped' 일 때 reason).
    """
    if match is None:
        return None

    # 방어적 접근 (vision_veto getattr 패턴). non-finite(NaN/inf) → 0.0 정규화 (WR-03):
    # `float('nan') or 0.0` 은 NaN 이 truthy 라 그대로 남아 tier 비교(NaN<=8.0=False)를
    # 전부 통과해 'disabled' 로 방출되고, firestore_admin._validate_motion_alignment 의
    # distance-finite 검사가 complete_analysis 에서 raise → 채점이 끝난 분석이 표시 전용
    # 필드 때문에 통째로 fail_analysis 된다 (helper 의 '방출 실패 비차단' 약속과 모순).
    # 방출 시점 1줄 방어로 차단. inf/NaN/None/비수치 모두 0.0.
    _raw_distance = getattr(match, "distance", 0.0)
    try:
        distance = float(_raw_distance)
        if not math.isfinite(distance):
            distance = 0.0
    except (TypeError, ValueError):
        distance = 0.0

    if user_fps is None or ref_fps is None or user_fps <= 0 or ref_fps <= 0:
        return _disabled(distance, "invalid_fps")

    path = getattr(match, "path", None) or []
    if not path:
        return _disabled(distance, "empty_path")

    start = int(getattr(match, "start", 0) or 0)
    end = int(getattr(match, "end", 0) or 0)

    start_sec = start / user_fps
    end_sec = (end - 1) / user_fps
    span = end_sec - start_sec

    # 앵커 상한 회피: step 을 정수배로 확대해 grid pair 수를 상한 내로 (DoS 가드 T-28-05).
    max_pairs = MAX_ANCHOR_FLOATS // 2
    step = ANCHOR_STEP_S
    if span > 0:
        mult = 1
        while True:
            s = ANCHOR_STEP_S * mult
            n = int(span / s) + 2  # +start +endpoint 근사
            if n <= max_pairs or s >= span:
                step = s
                break
            mult += 1

    # 학생초 그리드 + 양 끝점 (전역 트림 내장).
    grid_times: list[float] = []
    t = start_sec
    while t < end_sec - 1e-9:
        grid_times.append(t)
        t += step
    grid_times.append(end_sec)

    # 각 그리드 시각 → user 절대 프레임 → path median ref_idx → 초 앵커.
    pairs: list[tuple[float, float]] = []
    seen_frames: set[int] = set()
    last_r = None
    for gt in grid_times:
        abs_frame = round(gt * user_fps)
        if abs_frame in seen_frames:
            continue  # u strictly increasing (dedup)
        user_local = abs_frame - start
        js = sorted(j for (i, j) in path if i == user_local)
        if not js:
            continue  # 대응 없는 앵커 skip
        median_ref = js[len(js) // 2]  # 1:N 안정화 (fault_zoom 선례)
        u_sec = abs_frame / user_fps
        r_sec = median_ref / ref_fps
        # 단조성 강제: r 이 직전보다 작으면 앵커 제거 (warp 역전 방지).
        if last_r is not None and r_sec < last_r:
            continue
        seen_frames.add(abs_frame)
        pairs.append((u_sec, r_sec))
        last_r = r_sec

    if len(pairs) < 2:
        return _disabled(distance, "insufficient_anchors")

    # tier 사다리 (D-02, 28-RESEARCH Pattern 2).
    slopes_ok = True
    for k in range(len(pairs) - 1):
        du = pairs[k + 1][0] - pairs[k][0]
        dr = pairs[k + 1][1] - pairs[k][1]
        if du <= 0:
            continue
        slope = dr / du
        if slope < RATE_MIN or slope > RATE_MAX:
            slopes_ok = False
            break

    u0, r0 = pairs[0]
    uN, rN = pairs[-1]
    length_ratio = (rN - r0) / (uN - u0) if (uN - u0) > 0 else 1.0
    length_extreme = length_ratio < RATE_MIN or length_ratio > RATE_MAX

    reason = None
    if distance <= DISTANCE_T1 and slopes_ok:
        tier = "warped"
    elif distance <= DISTANCE_T2:
        tier = "trim_only"
        if not slopes_ok:
            reason = "rate_clamp_exceeded"
        elif length_extreme:
            reason = "length_extreme"
        else:
            reason = "low_global_confidence"
    else:
        # D-16 (32-CONTEXT): 저신뢰(distance > DISTANCE_T2)도 disabled 대신 trim_only 로
        # 방출해 anchors 를 보존한다 — 배속 워핑은 끄되 시작점 맞춤은 살린다(belle 최우선
        # 수리, "동작 비교 정렬 포기 보완"). 단 방출 전 첫 anchor sanity 가드(리뷰 MEDIUM):
        # 첫 anchor 쌍 (u0, r0)이 각 타임라인 범위 [0, dur] 밖이거나 non-finite 면 파생
        # offset 이 garbage 이므로 기존 degenerate 경로(insufficient_anchors — 신규 reason
        # enum 0, 기존 값 재사용)로 낙하시켜 이상치 offset 이 trim 기준으로 쓰이는 것을 막는다.
        # 두 anchor 가 각자 [0, dur] 안이면 |r0 − u0| ≤ max(user_dur, ref_dur) 가 자동 성립.
        user_dur = end_sec
        _ref_indices = [j for (_i, j) in path]
        ref_dur = (max(_ref_indices) / ref_fps) if _ref_indices else 0.0
        first_anchor_ok = (
            math.isfinite(u0)
            and 0.0 <= u0 <= user_dur
            and math.isfinite(r0)
            and 0.0 <= r0 <= ref_dur
        )
        if not first_anchor_ok:
            return _disabled(distance, "insufficient_anchors")
        tier = "trim_only"
        reason = "low_global_confidence"

    anchors: list[float] = []
    for u_sec, r_sec in pairs:
        anchors.append(float(u_sec))
        anchors.append(float(r_sec))

    result = {
        "version": MOTION_ALIGNMENT_VERSION,
        "source": "dtw",
        "tier": tier,
        "anchors": anchors,
        "anchorCount": len(anchors) // 2,
        "distance": float(distance),
    }
    if reason is not None:
        result["reason"] = reason
    return result
