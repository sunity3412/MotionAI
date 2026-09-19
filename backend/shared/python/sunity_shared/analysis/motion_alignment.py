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


# ── quick-260919-mhl — 확대 비교 카드 짝 품질을 "시간 정렬 이탈"로 재는 계기 ──────
#
# 왜 (belle 2026-09-19 판정): 종전 짝 품질 지표는 **자세 거리**(card_gates.PAIR_POSE_MAX)
# 였는데 belle 이 이 설계를 무너뜨렸다 — 카드의 존재 이유가 "자세가 다르다"를 보여주는
# 것이라, 자세로 짝을 재면 "같은 순간인데 자세가 다르다"(정상)와 "다른 순간이라 자세가
# 다르다"(결함)를 원리적으로 구분할 수 없다. 감점이 클수록 지표가 커진다. 봉 동작은
# 같은 국면이라도 돌면 방향이 180° 바뀌므로 회전이 벌점으로 잡힌다
# ([[pose-distance-counts-rotation-as-penalty]]). belle 기준은 "동작의 **구간**이 같은가"
# 이고 회전량은 구간을 안 바꾼다 → 대체 축 = 시간 정렬 이탈
# ([[pair-quality-is-time-alignment-not-pose]]).
#
# 이 두 함수는 **관측 전용**이다. 게이트가 아니고, 채점 경로에 닿지 않고, 카드를
# 버리지 않는다. 통과선(threshold)은 belle 판정 대기 — 이 값으로 카드를 숨기거나
# 문구를 내지 말 것. 계약 정본 = docs/contract.md §11.12.
#
# ★ 재현 실패 기록 (인계서 260919-0d3 §6): 그 4행 표(팔꿈치 -4.28 / 오른무릎 +0.67 /
#   왼골반 -0.13 / 오른어깨 -0.20)는 라이브 doc(01668c02...)에서 네 가지 해석 전부로
#   재현에 실패했다. **크기뿐 아니라 순서도 일치하지 않는다** — 타임베이스까지 맞춘
#   해석의 실측은 왼골반 6.00 > 팔꿈치 5.33 > 오른어깨 2.00 > 오른무릎 1.11 로,
#   §6 에서 가장 좋았던 왼골반이 가장 나쁜 쪽 끝으로 간다. 그 표를 이 함수가 내야 할
#   기준값으로 인용하지 말 것. belle 눈 대조는 다음 Pod 가동 때 라이브 doc 1건으로
#   선행되어야 한다 ([[handoff-observation-not-diagnosis]]).


def _read_pairs(anchors) -> tuple[list[float], list[float]]:
    """anchors flat → (us, rs) 쌍 배열.

    `anchorCount` 를 신뢰하지 않고 `len(anchors)` 에서 직접 도출한다 — TS 정본
    `app/src/lib/alignmentWarp.ts::readPairs` 의 "단일 출처 — 방어적 소비" 주석 그대로.
    """
    us: list[float] = []
    rs: list[float] = []
    k = 0
    n = len(anchors)
    while k + 1 < n:
        us.append(float(anchors[k]))
        rs.append(float(anchors[k + 1]))
        k += 2
    return us, rs


def warp_time(alignment: dict, t_student: float) -> float:
    """학생 시각 t_student → 정렬이 가리키는 기준(정은지) 시각. TS 정본의 **정확한 미러**.

    정본 = `app/src/lib/alignmentWarp.ts::warpTime` (49~72행). 분기 순서·식이 같아야
    한다 — lockstep 은 테스트(test_pair_time_deviation.py)가 TS 소스 텍스트로 지킨다.
    Python 쪽에 warp 가 없어 짝 이탈을 잴 수 없었던 구멍을 메우는 것이 이 함수다.

      tier 'disabled'  → identity
      앵커 0개         → identity
      tier 'trim_only' → t - us[0] + rs[0]  (트림+오프셋만, D-02 tier 2)
      tier 'warped'    → 범위 밖 기울기 1.0 연장 + 구간 선형보간

    ⚠️ 라이브 실측(2026-09-19, alignment 보유 doc 36건): tier 는 trim_only 35 ·
    disabled 1 · **warped 0** 이다. 전부 reason='low_global_confidence'(distance
    52.8~72.0 = DISTANCE_T2 25.0 의 2~3배)라 warpTime 의 trim_only 분기가 앵커 곡선을
    버리고 오프셋만 쓰고, 거의 모든 doc 에서 us[0]=rs[0]=0 이다 → **프로덕션에서 이
    warp 는 사실상 항등함수다**. warped 분기는 계약상 존재하지만 지금 데이터에는 없다.

    인자 검증은 하지 않는다 (TS 미러 유지) — 호출측이 `pair_time_deviation_sec` 에서
    유효성을 먼저 거른다.
    """
    # disabled — 워핑 없음. 방어적 identity (TS 동일).
    if alignment.get("tier") == "disabled":
        return float(t_student)

    us, rs = _read_pairs(alignment.get("anchors") or [])
    n = len(us)
    # 앵커 부재 방어 (정상 계약에선 warped/trim_only 는 앵커 보유).
    if n == 0:
        return float(t_student)

    t = float(t_student)
    # trim_only — 트림+오프셋만 (D-02 tier 2, 가변속도 끔).
    if alignment.get("tier") == "trim_only":
        return t - us[0] + rs[0]

    # warped — 범위 밖은 기울기 1.0 연장 (오프셋 연속, 특수분기 없이 매끄러움).
    if t <= us[0]:
        return rs[0] - (us[0] - t)
    if t >= us[n - 1]:
        return rs[n - 1] + (t - us[n - 1])
    for k in range(n - 1):
        if us[k] <= t < us[k + 1]:
            slope = (rs[k + 1] - rs[k]) / (us[k + 1] - us[k])
            return rs[k] + (t - us[k]) * slope
    return rs[n - 1]  # 도달 불가 방어


def pair_time_deviation_sec(
    alignment: dict | None,
    *,
    user_video_sec: float | None,
    ref_video_sec: float | None,
    user_label_fps: float | None,
    ref_label_fps: float | None,
    anchor_fps: float,
) -> float | None:
    """확대 비교 카드 한 장의 짝 시간 정렬 이탈(초). 관측 전용 — 게이트 아님.

    **부호 규약: 표시된 기준 초 − 정렬이 가리키는 기준 초** (displayed − expected).
      양수 = 기준 패널이 정렬보다 **늦은** 순간을 보여준다.
      음수 = 기준 패널이 정렬보다 **이른** 순간을 보여준다.
    절대값만 실으면 "기준이 앞서냐 뒤서냐"를 잃는다. 판정은 나중에 |값| 으로 하면
    된다. 이 규약은 contract.md §11.12 에 박혀 있다 — 뒤집지 말 것.

    ★ 타임베이스 — 그냥 빼면 틀린다 (이 함수에서 가장 중요한 사실).
    카드의 초와 anchors 의 초는 **분모가 다르다**.
      · 카드: u_video_sec = u_idx / u_label_fps, r_video_sec = r_display_idx /
        r_label_fps (fault_zoom.py `build_fault_zoom_comparisons` 의 u/r_video_sec
        산출). `*_label_fps` = 측별 **실효** rate(probe_effective_fps, 예: 30fps
        원본 → 10.0). 판정 불가 시 frames_fps(9.0) 폴백.
      · anchors: uSec = user_frame / user_fps 이고 user_fps =
        pipeline `_pipeline_frame_fps()` = **라벨 9.0**
        (`_attach_motion_alignment` 호출부). ref 측은 rSec = ref_idx / ref_fps 인데
        ref_idx 는 rep 공간(mode1 = 18fps) 인덱스이고
        `fault_zoom._to_rep_idx = round(idx / frames_fps * rep_fps)` 이므로
        rep_idx ≈ ref9_idx × rep_fps/9.0 → **rSec = ref9_idx / 9.0** 로 수렴한다.
      → 양쪽 anchors 축은 공통적으로 "비디오 배열 인덱스 / 9.0(라벨 초)".

    라벨 9.0 과 실효 ~10.0 은 약 11% 어긋난다([[fps-label-vs-actual-decimation-rate]]).
    변환 없이 빼면 warp 절편의 약 10%가 그대로 오차로 남는다. 그래서 양방향 환산한다:

        u_anchor = user_video_sec * (user_label_fps / anchor_fps)
        r_anchor = ref_video_sec  * (ref_label_fps  / anchor_fps)
        dev      = (r_anchor - warp_time(alignment, u_anchor)) * (anchor_fps / ref_label_fps)

    라벨 드리프트가 없으면(label == anchor == 9.0) 배율이 1.0 이라
    `ref_video_sec - warp_time(alignment, user_video_sec)` 로 자연 축약된다.

    `anchor_fps` 는 **인자**로 받는다 — 이 모듈은 순수(채점/파이프라인 import 0)라
    `_pipeline_frame_fps` 를 끌어오지 않는다. 호출측(pipeline)이 단일 출처를 넘긴다.

    값 없음 = **키 생략**(fail-closed). 0.0 이나 추정치로 채우지 않는다:
      · alignment 부재 (legacy doc / mode3 첫 분석 / 방출 실패)
      · tier 가 'warped'/'trim_only' 가 아님 ('disabled' 포함 — identity warp 로
        뺀 값은 근거가 없다)
      · anchors 0쌍
      · user_video_sec 또는 ref_video_sec 부재 (기준 대응 실패 카드는 refVideoSec 을
        애초에 안 싣는다)
      · 비유한(NaN/Inf) 입력, label_fps/anchor_fps <= 0

    3-way lockstep: app/src/types/analysis.ts FaultZoomComparison.pairDeviationSec?
    + pipeline `_attach_pair_time_deviation` / `_fault_zoom_upload_items` 매퍼
    + docs/contract.md §11.12. TS warp 정본 = app/src/lib/alignmentWarp.ts.
    """
    if not isinstance(alignment, dict):
        return None
    # 'disabled' 와 미등재 tier 를 한 번에 거른다 — warp 분기가 정의되지 않은 tier 를
    # warped 로 오독하면 근거 없는 수를 만든다 (fail-closed).
    if alignment.get("tier") not in ("warped", "trim_only"):
        return None

    anchors = alignment.get("anchors")
    if not isinstance(anchors, (list, tuple)) or len(anchors) < 2:
        return None
    for a in anchors:
        if not isinstance(a, (int, float)) or isinstance(a, bool):
            return None
        if not math.isfinite(float(a)):
            return None

    vals = (user_video_sec, ref_video_sec, user_label_fps, ref_label_fps, anchor_fps)
    for v in vals:
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return None
        if not math.isfinite(float(v)):
            return None
    if user_label_fps <= 0 or ref_label_fps <= 0 or anchor_fps <= 0:
        return None

    u_anchor = float(user_video_sec) * (float(user_label_fps) / float(anchor_fps))
    r_anchor = float(ref_video_sec) * (float(ref_label_fps) / float(anchor_fps))
    dev_anchor = r_anchor - warp_time(alignment, u_anchor)
    dev = dev_anchor * (float(anchor_fps) / float(ref_label_fps))
    if not math.isfinite(dev):
        return None
    return float(dev)
