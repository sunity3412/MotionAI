"""문제 부위 확대 비교 이미지 생성 (belle 2026-06-21).

깨진 3D 뷰어([[fault-zoom-compare-and-phase24-true3d]]) 대체. veto/결함이 잡힌
관절 부위만 worst-pose 시점 프레임에서 **crop + zoom** 해 학생 vs 기준(정은지/
이전 영상)을 나란히 보여주고, 부족한 각도를 숫자로 표기한다. 결함이 여러 개면
앱이 carousel 로 넘긴다.

설계:
  · 이미지에는 **숫자 각도 마커만** 그린다 (PIL 기본 폰트는 한글 글리프 부재 →
    한글 캡션/라벨은 앱이 담당, backend 는 시각 crop + 숫자만). 산출 출처 분리
    정합 — 좌표/각도는 backend, 표시는 app.
  · 프레임/좌표는 frame_extractor(9fps/640px) + keypointReport(정규화 0..1) 재사용.
  · 실패는 graceful — 본 기능은 부가물이라 분석 흐름을 막지 않는다 (호출측 try).

좌표계: keypointReport.data 는 flat (T*J*2), 값은 [0,1] 정규화 (frame 의 W/H 기준).
프레임은 frame_extractor 가 긴 변 640 으로 리사이즈한 (H,W,3) uint8.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

# crop 한 변 = 프레임 짧은 변의 비율 (관절 주변 zoom — 작을수록 더 확대).
_CROP_FRAC = 0.42
# 합성 시 각 crop 출력 한 변(px). 두 장 가로 합성 → (2*OUT, OUT).
_OUT = 360
# 마커 색 (브랜드 #FF4B33).
_BRAND = (255, 75, 51)

# 다리 사이각 선 최소 벡터 길이(px) — **display 전용, 채점 무접촉** (quick-260705-r6x).
# 골반 중점↔다리 끝 벡터가 이보다 짧으면(겹친 좌표) 선/호를 그려도 방향이 무의미해
# 오히려 오인 → 드로잉 생략하고 기존 렌더로 폴백. 채점/veto/게이트 경로에 진입하지
# 않는 표시 전용 상수이므로 calibration-source-hard-gate 대상 아님.
_MIN_LEG_VEC_PX = 8

# 사이각 선 keypoint 의 crop-포함 허용 마진(px) — **display 전용, 채점 무접촉**.
# 드로잉에 쓰는 hip 중점+다리 끝의 crop-내 raw 픽셀(clamp 전)이 crop 박스를
# 벗어나면 _to_crop_px clamp 가 좌표를 경계로 당겨 선이 몸과 무관하게 폭주한다
# (2026-07-05 belle pod PNG: 정은지 crop 이 정강이만 잘라 hip 이 crop 위로 벗어남 —
# conf 게이트는 통과했으나 자세가 스플릿이 아니고 crop 도 다리 하단만 포함).
# 경계 근처 rounding 은 허용하되 명백히 벗어난 점은 배제 = 그 측 사이각 생략.
_CROP_INCLUSION_MARGIN_PX = int(_OUT * 0.10)

# crop 앵커 keypoint 최소 confidence (quick-260702-sic). 프론트
# KeypointOverlay.KEYPOINT_LOW_CONFIDENCE_THRESHOLD = 0.5 선례 정합 — 저신뢰
# keypoint(RTMW 몸통 붕괴 등)를 crop 중심으로 쓰면 엉뚱한 부위(뒤통수)가 확대됨.
_KP_CONF_MIN = 0.5

# 결함단위(region) grouping — 같은 결함(스플릿 등)에서 온 좌+우 동일 부위 관절들을
# 카드 1장으로 묶는다 (quick-260702-sic). keypointReport 의 8-keypoint 이름공간
# (left/right_hand = COCO wrist 매핑) + 향후 확장 이름(ankle/elbow/wrist)을 함께 커버.
_REGION_JOINTS: dict[str, frozenset[str]] = {
    "legs": frozenset({
        "left_hip", "right_hip",
        "left_knee", "right_knee",
        "left_ankle", "right_ankle",
    }),
    "arms": frozenset({
        "left_shoulder", "right_shoulder",
        "left_elbow", "right_elbow",
        "left_wrist", "right_wrist",
        "left_hand", "right_hand",
    }),
}
# grouped bbox crop 마진 — 멤버 관절 전체 + 주변 컨텍스트.
_BBOX_MARGIN = 1.8

# 완화(relaxed) crop 확대 배율 — **display 전용, 채점 무접촉** (Phase 25-03).
# 저신뢰-유한 좌표는 실제 부위에서 벗어나 있을 수 있어 valid 공식 대비 넓게
# 잡아 부위가 crop 안에 남도록 한다. 채점/veto/게이트 경로에 진입하지 않는
# 표시 전용 상수이므로 calibration-source-hard-gate 대상 아님.
# 적용 범위 = bbox 파생분에만 (quick-260705-ftn): 2026-07-05 pod 재현 —
# floor(_CROP_FRAC 기본 줌)에도 margin 을 곱하면 side 가 프레임 전폭(360)에
# 클램프돼 모든 relaxed crop 이 전신처럼 보임 (belle 실기기, kip-up fault 76점).
_RELAXED_MARGIN = 2.0


@dataclass(frozen=True)
class _CropUnit:
    """fan-out crop 단위 — 단일 관절(region=None) 또는 결함단위 좌+우 묶음."""

    joint: str  # 대표 keypoint (S3 key / TS 계약의 joint 필드)
    members: tuple[str, ...]  # crop bbox 에 담을 keypoint 전부 (단일이면 (joint,))
    region: str | None  # "legs" | "arms" | None


def _group_fault_joints(
    fault_joints: list[str], joint_kinds: dict[str, str] | None
) -> list[_CropUnit]:
    """fault_joints → crop unit 리스트 (순수, 순서 보존 + dedup).

    grouping 조건 (전부 만족 시 region 1 unit):
      · 같은 region(_REGION_JOINTS) 소속 fault joint 가 2개 이상
      · 좌(left_*)+우(right_*) 양측에 걸침
      · kind 가 전원 동일한 non-None 값 — mode3 improved/worsened 혼재 시 비활성.
        kind 전원 부재(None)는 grouping 하지 않음: production 은 항상 kind 를
        세팅(Mode1='deficit'/Mode3 방향)하므로 부재 = legacy 호출 — 기존 관절당
        1장 동작 보존 (기존 테스트 6개 무수정 PASS 하위호환 게이트).
    대표 joint = fault_joints 순서상 첫 멤버. 그 외는 관절당 1 unit (region=None).
    """
    kinds = joint_kinds or {}
    ordered: list[str] = []
    seen: set[str] = set()
    for j in fault_joints:
        if j not in seen:
            seen.add(j)
            ordered.append(j)

    grouped: dict[str, str] = {}  # member joint → region
    reps: dict[str, str] = {}  # region → 대표 joint
    for region, region_joints in _REGION_JOINTS.items():
        members = [j for j in ordered if j in region_joints]
        if len(members) < 2:
            continue
        has_left = any(m.startswith("left_") for m in members)
        has_right = any(m.startswith("right_") for m in members)
        if not (has_left and has_right):
            continue
        member_kinds = {kinds.get(m) for m in members}
        if len(member_kinds) != 1 or next(iter(member_kinds)) is None:
            continue
        for m in members:
            grouped[m] = region
        reps[region] = members[0]

    units: list[_CropUnit] = []
    for j in ordered:
        region = grouped.get(j)
        if region is None:
            units.append(_CropUnit(joint=j, members=(j,), region=None))
        elif reps.get(region) == j:
            members = tuple(m for m in ordered if grouped.get(m) == region)
            units.append(_CropUnit(joint=j, members=members, region=region))
        # grouped 비대표 멤버 → 개별 fan-out 에서 제거 (카드 1장).
    return units


def select_advisory_joints(
    kp_deltas: dict[str, float],
    confirmed: set[str],
    tol_deg: float,
    max_items: int = 2,
) -> list[str]:
    """측정 초과 관절 선별 — advisory("참고·확인 권장") 확대 카드 대상 (quick-260704-fz4).

    입력 kp_deltas 는 이미 **keypoint 이름공간**으로 매핑된 {keypoint: delta_deg(signed)}.
    kismam angle key → keypoint 매핑은 호출측 pipeline(_KISMAM_TO_KEYPOINT) 책임 —
    본 모듈은 이름공간 무지 유지. 반환 = |delta| > tol_deg AND confirmed(확정 결함)
    제외인 keypoint 를 |delta| 내림차순으로 최대 max_items 개 (캐러셀 과밀 방지).
    비유한(nan/inf)/변환 불가 delta 는 defensive skip.

    위양성 교훈 ([[window-median-silent-seed-fp-reverted]], quick-260702-o0c revert):
    window median 측정 초과를 감점 seed 로 쓰면 RTMW jitter/촬영거리 노이즈가 위양성
    감점으로 증폭된다. advisory 는 "측정 초과 = 참고"일 뿐 결함 확정이 아니다 —
    **표시 전용. 채점/veto/게이트 입력으로 절대 쓰지 말 것.**
    """
    scored: list[tuple[float, str]] = []
    for kp, delta in (kp_deltas or {}).items():
        if kp in confirmed:
            continue
        try:
            mag = abs(float(delta))
        except (TypeError, ValueError):
            continue
        if not np.isfinite(mag) or mag <= float(tol_deg):
            continue
        scored.append((mag, kp))
    scored.sort(key=lambda t: -t[0])
    return [kp for _mag, kp in scored[: max(0, int(max_items))]]


def _to_rep_idx(
    idx: int, frames_fps: float, rep_fps: float, rep_frames: int
) -> int:
    """9fps frames 인덱스 → keypointReport fps 인덱스 (B1 변환 공식 단일 출처).

    build_fault_zoom_comparisons 와 select_confident_frame 이 같은 공식을
    공유한다 — 중복 공식 금지 (quick-260705-ftn)."""
    return max(0, min(
        int(round(idx / max(1e-6, frames_fps) * rep_fps)),
        max(0, rep_frames - 1),
    ))


def select_confident_frame(
    report: dict,
    candidates: list,
    members: list[str] | tuple[str, ...],
    frames_fps: float = 9.0,
) -> int | None:
    """window candidates 중 멤버 관절 평균 confidence 최대 프레임 선택 (순수).

    window median 프레임이 keypoint 붕괴 구간이면 relaxed/full 강하로 카드가
    망가짐 (2026-07-05 pod 재현: ref-kip-up frame 37 전 keypoint <0.5, 동일
    영상 30/59/80 에선 legs 4점 valid) — 측정-표시 정합은 window 안에서
    유지하면서 신뢰 프레임을 고른다. 표시 전용, 채점/veto/게이트 무접촉.

    candidates = 9fps frames 인덱스 (sourceFrameIndices 의 user/reference 리스트).
    빈 리스트/전원 비정수 → None (호출측 폴백 = override 없음). 전 candidate
    전 멤버 conf None(legacy/confidence 부재 report) → sorted median 폴백
    (기존 pipeline 동작 보존 — 하위호환 diff 0). 동점은 sorted 오름차순 첫
    인덱스 (결정론 tie-break). 반환 = 9fps frames 인덱스.
    """
    rep = report or {}
    ints: list[int] = []
    for c in candidates or []:
        try:
            ints.append(int(c))
        except (TypeError, ValueError):
            continue
    if not ints:
        return None
    ordered = sorted(ints)
    rep_fps = float(rep.get("fps") or frames_fps)
    rep_frames = int(rep.get("frames") or 0)
    best_idx: int | None = None
    best_score = -1.0
    for idx in ordered:
        rep_idx = _to_rep_idx(idx, frames_fps, rep_fps, rep_frames)
        confs = [
            c for m in members
            if (c := _kp_conf(rep, rep_idx, m)) is not None
        ]
        if not confs:
            continue
        score = sum(confs) / len(confs)
        if score > best_score:
            best_score, best_idx = score, idx
    if best_idx is None:
        # legacy 폴백 — 기존 pipeline 의 sorted median 과 동일 산출.
        return ordered[len(ordered) // 2]
    return best_idx


def _frame_index(seconds: float | None, fps: float, n_frames: int) -> int:
    """worst-pose 초 → 프레임 인덱스 (clamp). seconds None → 중앙 프레임."""
    if n_frames <= 0:
        return 0
    if seconds is None or fps <= 0:
        return n_frames // 2
    idx = int(round(seconds * fps))
    return max(0, min(idx, n_frames - 1))


def _matched_ref_frame(dtw_match, user_frame: int, ref_n: int) -> int | None:
    """B1 — DTW match 로 학생 프레임 ↔ 기준 프레임(같은 pose). None=불가.

    match.start = 사용자 구간 시작(angles 9fps), path = [(user_local, ref_idx)...].
    ref_idx = 기준 angles 인덱스 — **ref doc 의 keypointReport.fps 공간**(phase4_v1
    재처리 18fps, 28-01 실측). 반환도 이 angles(rep) 인덱스 공간이다. 호출측이
    clamp 상한(ref_n)과 9fps frames 배열로의 변환을 도메인에 맞게 책임진다
    (28-RESEARCH Pitfall 1, D2 fix — angles 인덱스를 9fps frames 에 그대로 넣으면
    시간 2배 오독). 학생 프레임을 구간-로컬로 변환 후 path 에서 같은 user_local 의
    ref_idx 들의 median 을 고른다(DTW 1:N 대응 안정화).

    **본체 수정 금지** — veto still 경로(app.py `_build_selected_frame_pair`)가 이
    함수를 공유하며 그쪽 입력이 바뀌면 점수가 움직인다 (28-RESEARCH Open Q2).
    """
    if dtw_match is None:
        return None
    try:
        start = int(getattr(dtw_match, "start", 0))
        path = getattr(dtw_match, "path", None) or []
    except Exception:  # noqa: BLE001 - match 형태 이상 시 graceful (proportional 폴백)
        return None
    local = user_frame - start
    js = sorted(j for (i, j) in path if i == local)
    if not js:
        return None
    return max(0, min(int(js[len(js) // 2]), ref_n - 1))


def _kp_xy(report: dict, frame_idx: int, joint: str) -> tuple[float, float] | None:
    """keypointReport(flat data) 의 frame_idx, joint 정규화 좌표 (x,y) | None.

    data layout = T * J * 2. joint 은 report['joints'] 의 이름.
    """
    joints = report.get("joints") or []
    if joint not in joints:
        return None
    j = joints.index(joint)
    nj = len(joints)
    data = report.get("data") or []
    frames = int(report.get("frames") or 0)
    if frames <= 0 or len(data) < frames * nj * 2:
        return None
    fi = max(0, min(frame_idx, frames - 1))
    base = (fi * nj + j) * 2
    x = float(data[base])
    y = float(data[base + 1])
    if not (np.isfinite(x) and np.isfinite(y)):
        return None
    return x, y


def _kp_conf(report: dict, frame_idx: int, joint: str) -> float | None:
    """keypointReport 의 (frame, joint) confidence. 부재/legacy → None (통과 취급).

    confidence 는 flat T*J (keypoint_frame.py KeypointReport). 길이가 frames*nj
    미만이면 부재 취급 (legacy/합성 report 하위호환).
    """
    joints = report.get("joints") or []
    if joint not in joints:
        return None
    j = joints.index(joint)
    nj = len(joints)
    conf = report.get("confidence") or []
    frames = int(report.get("frames") or 0)
    if frames <= 0 or len(conf) < frames * nj:
        return None
    fi = max(0, min(frame_idx, frames - 1))
    try:
        c = float(conf[fi * nj + j])
    except (TypeError, ValueError):
        return None
    return c if np.isfinite(c) else None


def _gated_kp(
    report: dict, frame_idx: int, joint: str
) -> tuple[float, float] | None:
    """좌표 finite AND 명시적 고신뢰(conf >= _KP_CONF_MIN)만 통과 (quick-260705-r6x).

    사이각 드로잉 전용 게이트 — crop 게이트(_member_pts, conf 부재=통과)보다
    엄격하다. confidence 부재(legacy report)도 불허: 2026-07-05 pod 실측(belle
    PNG 육안)에서 confidence 없는 reference report 가 통과해 몸과 무관한 방향으로
    선이 폭주했다 — 선/호는 확정적 시각 언어라 신뢰가 증명된 좌표에서만 그린다.
    저신뢰/미증명 → None (호출측 기존 렌더 폴백). 표시 전용, 채점 무접촉.
    """
    xy = _kp_xy(report, frame_idx, joint)
    if xy is None:
        return None
    c = _kp_conf(report, frame_idx, joint)
    if c is None or c < _KP_CONF_MIN:
        return None
    return xy


def _leg_line_pts(
    report: dict, frame_idx: int
) -> tuple[
    tuple[float, float], tuple[float, float], tuple[float, float]
] | None:
    """스플릿 사이각 드로잉용 3점(정규화): (골반 중점, 왼 다리 끝, 오른 다리 끝).

    belle 2026-07-05 실기기: "다리에 동그라미가 아니라 다리와 다리 사이각을 표시".
      · 골반 중점 = left_hip/right_hip 중점 — 양쪽 모두 게이트 통과 필수.
      · 다리 끝 = ankle 우선, 저신뢰/결측 시 knee 폴백 (측별 독립).
      · 셋 중 하나라도 해석 불가 → None (호출측 기존 렌더 폴백).
    fault_joints(결함 관절 목록)와 무관하게 report 에서 직접 조회한다 — 드로잉
    좌표는 결함 목록이 아니라 실제 관절 위치를 따른다 (fault_joints 에 knee 만
    있어도 hips 가 report 에 valid 하면 그린다).
    """
    lh = _gated_kp(report, frame_idx, "left_hip")
    rh = _gated_kp(report, frame_idx, "right_hip")
    if lh is None or rh is None:
        return None
    pelvis = ((lh[0] + rh[0]) / 2.0, (lh[1] + rh[1]) / 2.0)
    left_end = _gated_kp(report, frame_idx, "left_ankle") or _gated_kp(
        report, frame_idx, "left_knee"
    )
    right_end = _gated_kp(report, frame_idx, "right_ankle") or _gated_kp(
        report, frame_idx, "right_knee"
    )
    if left_end is None or right_end is None:
        return None
    return pelvis, left_end, right_end


def _crop_box(
    h: int, w: int, cx: float, cy: float, side: int | None = None
) -> tuple[int, int, int]:
    """정규화 중심 (cx,cy) 의 정사각 crop 박스 (left, top, side_px) — 순수 기하.

    side None 이면 min(H,W)*_CROP_FRAC (기존 단일 관절 zoom). 경계를 넘으면
    안쪽으로 shift (검은 패딩 회피) + 프레임 내 clamp (T-25-07 — NaN 은 상류
    finite 검사에서 이미 차단, 범위밖 좌표는 여기서 clamp).
    """
    if side is None:
        side = max(16, int(round(min(h, w) * _CROP_FRAC)))
    side = max(16, min(int(side), min(h, w)))
    px, py = cx * w, cy * h
    left = int(round(px - side / 2))
    top = int(round(py - side / 2))
    left = max(0, min(left, w - side)) if w >= side else 0
    top = max(0, min(top, h - side)) if h >= side else 0
    return left, top, side


def _render_crop(frame: np.ndarray, left: int, top: int, side: int) -> Image.Image:
    """crop 박스를 잘라 (_OUT,_OUT) 으로 리사이즈."""
    h, w = frame.shape[0], frame.shape[1]
    crop = frame[top:min(h, top + side), left:min(w, left + side)]
    return Image.fromarray(crop).convert("RGB").resize((_OUT, _OUT), Image.BILINEAR)


def _full_frame_fit(frame: np.ndarray) -> Image.Image:
    """full frame 을 비율 유지 contain-fit 으로 (_OUT,_OUT) 흰 캔버스에 배치.

    crop 앵커 keypoint 가 전부 결측/저신뢰인 측의 전신 폴백 — 엉뚱한 부위 확대보다
    전신이 낫다 (quick-260702-sic, belle 요구 3).
    """
    img = Image.fromarray(frame).convert("RGB")
    w, h = img.size
    scale = _OUT / max(1, max(w, h))
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    resized = img.resize((nw, nh), Image.BILINEAR)
    canvas = Image.new("RGB", (_OUT, _OUT), (255, 255, 255))
    canvas.paste(resized, ((_OUT - nw) // 2, (_OUT - nh) // 2))
    return canvas


def _member_pts(
    report: dict, frame_idx: int, members: tuple[str, ...]
) -> tuple[
    list[tuple[str, tuple[float, float]]], list[tuple[float, float]]
]:
    """unit 멤버 keypoint 를 (valid, relaxed) 로 분류.

    valid = 좌표 finite AND (confidence 부재 → 통과 | confidence >= _KP_CONF_MIN)
    — (관절명, 좌표) 쌍 (앵커 대표 관절 선택에 관절명 필요, Phase 25-03 Task 2).
    저신뢰 keypoint 를 crop 앵커로 쓰면 엉뚱한 부위가 확대됨 (quick-260702-sic).
    relaxed = 좌표 finite 이지만 confidence < _KP_CONF_MIN — 완화 crop 후보.
    좌표 자체 결측(NaN/부재)은 어느 쪽에도 안 들어감 (전신 폴백 대상).
    """
    valid: list[tuple[str, tuple[float, float]]] = []
    relaxed: list[tuple[float, float]] = []
    for m in members:
        xy = _kp_xy(report, frame_idx, m)
        if xy is None:
            continue
        c = _kp_conf(report, frame_idx, m)
        if c is not None and c < _KP_CONF_MIN:
            relaxed.append(xy)
        else:
            valid.append((m, xy))
    return valid, relaxed


def _anchor_xy(
    valid: list[tuple[str, tuple[float, float]]],
    deltas: dict[str, float] | None,
) -> tuple[float, float]:
    """앵커(대표) 관절의 정규화 좌표 — deficit(|delta|) 최대 valid 멤버.

    delta 없는/비유한 멤버는 후보 제외, 전원 delta 부재면 첫 valid 멤버
    (fault_joints 순서 보존). grouped(2관절+) 카드의 circle 1개 대상 선정.
    """
    best_xy = valid[0][1]
    best_mag = -1.0
    for name, xy in valid:
        d = (deltas or {}).get(name)
        try:
            mag = abs(float(d))
        except (TypeError, ValueError):
            continue
        if np.isfinite(mag) and mag > best_mag:
            best_mag, best_xy = mag, xy
    return best_xy


def _to_crop_px(
    xy: tuple[float, float],
    left: int,
    top: int,
    side: int,
    w: int,
    h: int,
) -> tuple[int, int]:
    """정규화 좌표 → crop 박스(left,top,side) 내 출력 픽셀 변환 단일 출처 (quick-260705-r6x).

    _side_crop 의 anchor_px 산출과 _draw_leg_angle 의 선/호 좌표가 같은 공식을
    공유한다 (중복 금지). [0,_OUT-1] clamp — 캔버스 밖 좌표 방어.
    """
    s = max(1, int(side))
    ax = int(round((xy[0] * w - left) / s * _OUT))
    ay = int(round((xy[1] * h - top) / s * _OUT))
    return max(0, min(_OUT - 1, ax)), max(0, min(_OUT - 1, ay))


def _pt_in_crop(
    xy: tuple[float, float],
    left: int,
    top: int,
    side: int,
    w: int,
    h: int,
    margin: float = _CROP_INCLUSION_MARGIN_PX,
) -> bool:
    """xy(정규화)의 crop-내 raw 픽셀(clamp 전)이 [−margin, _OUT+margin] 안인가.

    _to_crop_px 는 [0,_OUT-1] 로 clamp 하므로 crop 밖 점도 경계로 접힌다 — 포함
    판정은 반드시 clamp 전 좌표로(quick-260705-r6x pod fix). 사이각 선 시작/끝점이
    crop 밖이면 선이 경계로 폭주하므로 그 측 드로잉을 생략하는 데 쓴다.
    """
    s = max(1, int(side))
    ax = (xy[0] * w - left) / s * _OUT
    ay = (xy[1] * h - top) / s * _OUT
    lo = -float(margin)
    hi = _OUT + float(margin)
    return lo <= ax <= hi and lo <= ay <= hi


def _side_crop(
    frame: np.ndarray,
    valid_pts: list[tuple[float, float]],
    relaxed_pts: list[tuple[float, float]],
    anchor: tuple[float, float] | None = None,
) -> tuple[
    Image.Image, str, tuple[int, int] | None, tuple[int, int, int] | None
]:
    """한 측(user/ref)의 unit crop 3단 강하 → (이미지, crop_kind, anchor_px, box).

    crop_kind ∈ {"valid", "relaxed", "full"} — _mark 가 앵커 표시 여부 결정.
    anchor_px = anchor(결함 관절 정규화 좌표)의 crop-내 출력 픽셀 좌표 — valid
    crop 에서만 산출 (circle 을 crop 중심이 아닌 관절 좌표에 고정, Task 2).
    relaxed/full 은 좌표 불확실이라 None (앵커 생략 = 오인 방지).
    box = 이 crop 이 쓴 프레임 좌표계 (left, top, side) — 사이각 선/호 좌표 변환용
    (quick-260705-r6x). full 폴백은 crop 박스가 없어 None. 기존 호출측은 [0]/[:2]/
    [2] 인덱싱이라 4번째 원소 추가는 하위호환.

    (1) valid(신뢰 좌표) 있음 → 기존 로직 그대로: 1개=단일 관절 zoom, 2개 이상
        (grouped)=멤버 bounding box crop (변 = max(bbox)*_BBOX_MARGIN,
        floor=_CROP_FRAC 줌 수준, 상한=프레임 내).
    (2) valid 0개, 저신뢰-유한 좌표 있음 → 완화(relaxed) crop: 그 좌표 중심,
        변 = max(floor, bbox*_BBOX_MARGIN*_RELAXED_MARGIN) — margin 은 bbox
        파생분에만, floor(기본 줌)는 그대로 (display 전용, 채점 무접촉).
        reference 저신뢰 전신 폴백이 카드마다 동일 전신 반복 → 부위-중심 완화
        crop 으로 카드별 차별화 (Phase 25 동반 스코프, belle 2026-07-04 실기기).
        오인 방지는 앵커 생략으로 유지 (260702-sic 요구 3).
    (3) 좌표 자체 결측 → 기존 _full_frame_fit 전신 폴백.

    촬영거리 불일치는 bbox 가 측별 person 스케일을 따라가며 자연 해소.
    """
    h, w = frame.shape[0], frame.shape[1]

    def _box_for(pts: list[tuple[float, float]], margin: float):
        xs = [p[0] * w for p in pts]
        ys = [p[1] * h for p in pts]
        cx = (min(xs) + max(xs)) / 2 / w
        cy = (min(ys) + max(ys)) / 2 / h
        # margin 은 bbox 파생분에만 곱한다 (quick-260705-ftn) — floor 에도 곱하면
        # 밀집/단일 relaxed 좌표의 side 가 프레임 전폭에 클램프돼 전신처럼 보임
        # (2026-07-05 pod 재현). valid 경로는 margin=1.0 이라 산출 무변경.
        floor_side = int(round(min(h, w) * _CROP_FRAC))
        side = floor_side
        if len(pts) > 1:
            bbox_side = max(max(xs) - min(xs), max(ys) - min(ys))
            side = max(floor_side, int(round(bbox_side * _BBOX_MARGIN * margin)))
        # 확대 후에도 _crop_box 가 프레임 경계로 clamp (T-25-07).
        return _crop_box(h, w, cx, cy, side)

    if valid_pts:
        left, top, s = _box_for(valid_pts, 1.0)
        anchor_px: tuple[int, int] | None = None
        if anchor is not None:
            anchor_px = _to_crop_px(anchor, left, top, s, w, h)
        return _render_crop(frame, left, top, s), "valid", anchor_px, (
            left, top, s,
        )
    if relaxed_pts:
        left, top, s = _box_for(relaxed_pts, _RELAXED_MARGIN)
        return _render_crop(frame, left, top, s), "relaxed", None, (
            left, top, s,
        )
    return _full_frame_fit(frame), "full", None, None


def _deficit_label(deficit_deg: float) -> str:
    """deficit 배지 라벨 포맷 (quick-260704-fz4 후속) — "40°" (숫자 + 도 기호).

    구 "40deg" 원어 표기 교체 (belle 실기기 피드백). U+00B0 도 기호는 PIL 기본
    폰트(Pillow 12 load_default) 글리프 보유 확인 완료 (getmask 4x8 + 렌더 픽셀
    검증) — "한글 글리프 부재" 제약(모듈 docstring)과 무관, latin-1 범위라 안전.
    """
    return f"{int(round(deficit_deg))}°"


def _mark(
    img: Image.Image,
    deficit_deg: float | None,
    circle: bool = True,
    anchor_px: tuple[int, int] | None = None,
) -> Image.Image:
    """브랜드 원 + (deficit 있으면) 숫자 배지. 한글 없음(폰트 회피).

    circle 중심 = anchor_px(결함 관절의 crop-내 좌표, Phase 25-03 Task 2 —
    grouped bbox crop 에서 관절이 중심을 벗어나도 원이 관절을 가리킴). anchor_px
    None 이면 기존 crop 중앙 (하위호환).
    circle=False = relaxed/전신 폴백 측 (좌표 불확실/중앙 비결함 — 원 생략,
    오인 방지). deficit 배지는 유지. 라벨 포맷 = _deficit_label ("40°") —
    confirmed/advisory 양 배치가 본 함수를 공유하므로 동일 적용.
    """
    draw = ImageDraw.Draw(img)
    if circle:
        cx, cy = anchor_px if anchor_px is not None else (_OUT // 2, _OUT // 2)
        r = int(_OUT * 0.16)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=_BRAND, width=4)
    if deficit_deg is not None and deficit_deg > 0:
        txt = _deficit_label(deficit_deg)
        # 배지 배경 (가독성) — 우상단. 폭 추정 = 글자당 8px 상한 유지
        # (° 글리프는 4px 로 더 좁음 — 여유폭, 잘림 없음).
        tw = 8 * len(txt) + 10
        draw.rectangle([_OUT - tw - 8, 8, _OUT - 8, 34], fill=_BRAND)
        draw.text((_OUT - tw - 2, 13), txt, fill=(255, 255, 255))
    return img


def _draw_leg_angle(
    img: Image.Image,
    pelvis_px: tuple[int, int],
    left_px: tuple[int, int],
    right_px: tuple[int, int],
    angle_deg: float | None,
) -> bool:
    """골반 중점→양 다리 선 2개 + 사이각 호(arc) + (있으면) 각도 수치 (in-place).

    belle 2026-07-05 실기기: 스플릿 결함의 본질 = 두 다리 벌림 각도. 앵커 동그라미
    대신 사이각을 직접 그려 호 크기 차이가 곧 결함으로 보이게 한다. 성공 여부를
    반환 — display 전용, 채점 무접촉. 한글 없음(선/호/숫자만, 모듈 docstring 정합).
    """
    px, py = pelvis_px
    lx, ly = left_px
    rx, ry = right_px
    # 겹친 좌표(벡터 길이 < _MIN_LEG_VEC_PX)는 그리면 오히려 오인 → 드로잉 생략.
    if (
        math.hypot(lx - px, ly - py) < _MIN_LEG_VEC_PX
        or math.hypot(rx - px, ry - py) < _MIN_LEG_VEC_PX
    ):
        return False
    draw = ImageDraw.Draw(img)
    draw.line([pelvis_px, left_px], fill=_BRAND, width=4)
    draw.line([pelvis_px, right_px], fill=_BRAND, width=4)
    r = int(_OUT * 0.14)
    # 이미지 좌표(y down)의 atan2 와 PIL arc(3시 기준 시계방향)가 정합.
    a_left = math.degrees(math.atan2(ly - py, lx - px))
    a_right = math.degrees(math.atan2(ry - py, rx - px))
    a1, a2 = a_left, a_right
    if (a2 - a1) % 360 > 180:  # 두 선 사이 minor arc 만 그린다.
        a1, a2 = a2, a1
    draw.arc(
        [px - r, py - r, px + r, py + r], start=a1, end=a2, fill=_BRAND, width=3
    )
    if angle_deg is not None and np.isfinite(angle_deg):
        txt = _deficit_label(float(angle_deg))
        # 호 이등분 방향 반지름 r+12 지점에 배지 (기존 _mark 배지 스타일 재사용,
        # 폭 추정 8px/글자 동일).
        mid = math.radians(a1 + ((a2 - a1) % 360) / 2.0)
        label_r = r + 12
        mx = px + label_r * math.cos(mid)
        my = py + label_r * math.sin(mid)
        tw = 8 * len(txt) + 10
        th = 22
        x0 = int(round(mx - tw / 2.0))
        y0 = int(round(my - th / 2.0))
        draw.rectangle([x0, y0, x0 + tw, y0 + th], fill=_BRAND)
        draw.text((x0 + 5, y0 + 5), txt, fill=(255, 255, 255))
    return True


def _draw_side_leg_angle(
    img: Image.Image,
    frame: np.ndarray,
    report: dict,
    kp_idx: int,
    box: tuple[int, int, int],
    angle_deg: float | None,
) -> bool:
    """한 측 crop 에 다리 사이각을 그린다 (quick-260705-r6x) — 성공 여부 반환.

    _leg_line_pts 3점(정규화) → _to_crop_px 로 crop-내 픽셀 → _draw_leg_angle.
    pts 해석 불가/degenerate → False (호출측 기존 렌더 폴백). box = _side_crop 이
    반환한 (left, top, side) — crop 이 쓴 그 프레임 좌표계.

    crop-포함 게이트(quick-260705-r6x pod fix): 3점 중 하나라도 crop 박스 밖이면
    (_to_crop_px clamp 로 선이 경계로 폭주 — 2026-07-05 정은지 ref 측 실측) 드로잉
    생략하고 기존 crop 폴백. conf 게이트(_gated_kp)와 AND — 신뢰 좌표라도 그 측
    crop 이 관절을 안 담으면 그리지 않는다.
    """
    pts = _leg_line_pts(report, kp_idx)
    if pts is None:
        return False
    h, w = frame.shape[0], frame.shape[1]
    left, top, side = box
    if not all(_pt_in_crop(p, left, top, side, w, h) for p in pts):
        return False
    pelvis_px = _to_crop_px(pts[0], left, top, side, w, h)
    left_px = _to_crop_px(pts[1], left, top, side, w, h)
    right_px = _to_crop_px(pts[2], left, top, side, w, h)
    return _draw_leg_angle(img, pelvis_px, left_px, right_px, angle_deg)


def split_angle_degs_from_records(
    records,
) -> tuple[float | None, float | None] | None:
    """deductionBreakdown.records 에서 스플릿 사이각 수치 추출 (순수, boto3 무관).

    수치 출처 = 점수가 쓴 그 record — 측정-표시 정합
    ([[scoring-must-be-transparent-deduction-tally]]). 단 벌림각(사이각) semantics
    를 가진 record 만 표기한다 (2026-07-05 belle pod PNG 검증 fix):

      · deviationSource=='ipsf_absolute' 만 수용 — measuredValue = 추정 학생
        벌림각(180 − deficit)이라 호 옆 각도로 정직. 기준 측은 baselineValue(180)
        가 IPSF 목표치이지 정은지 실측 벌림각이 아니므로 **항상 생략(None)** —
        미측정 수치를 정은지 몸 옆에 붙이면 오인.
      · deviationSource=='reference_relative'(현행 split_vs_reference 규칙,
        vision-주입 kip-up 경로 포함)는 measuredValue = 정은지-대비 편차(예: 50)
        라 벌림각이 아님 — 표기하면 "벌림각 50°"로 오독(실측 재현된 결함).
        전체 None (선+호만, 수치 생략).

    반환 = (학생 벌림각, None) 또는 None. float 변환 실패/비유한 → None.
    records None/비리스트 graceful.
    """
    if not isinstance(records, list):
        return None

    def _finite(v):
        try:
            x = float(v)
        except (TypeError, ValueError):
            return None
        return x if np.isfinite(x) else None

    for rec in records:
        if not isinstance(rec, dict):
            continue
        if rec.get("criterion") != "split_angle" or rec.get("unit") != "deg":
            continue
        if rec.get("deviationSource") != "ipsf_absolute":
            # reference_relative(편차 semantics)/미상 출처 — 벌림각 아님, 수치 생략.
            return None
        student = _finite(rec.get("measuredValue"))
        if student is None:
            return None
        return student, None
    return None


def has_split_angle_record(records) -> bool:
    """records 에 스플릿 사이각 criterion 이 하나라도 있는지 (순수, boto3 무관).

    수치 추출(split_angle_degs_from_records)과 존재 판정을 분리하는 이유 — kip-up
    경로의 reference_relative split record 는 measuredValue 가 정은지-대비 편차라
    벌림각 수치는 생략(None)하지만, "다리가 벌어졌다"는 사이각 자체는 의미가 있어
    선+호는 그려야 한다 (2026-07-05 belle pod 전동작 검증). 그래서 존재 판정(이
    함수)으로 legs 사이각 게이트를 열고, 수치는 별도로 붙인다:
      · reference_relative split record → True (선+호, 수치 None)
      · ipsf_absolute split record → True (선+호+수치)
      · line-only / split 없음 / unit!='deg' → False
      · None / 비리스트 / 빈 리스트 → False (graceful)
    """
    if not isinstance(records, list):
        return False
    for rec in records:
        if not isinstance(rec, dict):
            continue
        if rec.get("criterion") == "split_angle" and rec.get("unit") == "deg":
            return True
    return False


def _compose(user_crop: Image.Image, ref_crop: Image.Image) -> bytes:
    """[user | ref] 가로 합성 → PNG bytes. 가운데 흰 구분선."""
    gap = 6
    canvas = Image.new("RGB", (_OUT * 2 + gap, _OUT), (255, 255, 255))
    canvas.paste(user_crop, (0, 0))
    canvas.paste(ref_crop, (_OUT + gap, 0))
    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def build_fault_zoom_comparisons(
    user_frames: np.ndarray,
    ref_frames: np.ndarray,
    user_report: dict,
    ref_report: dict,
    worst_seconds: float | None,
    fault_joints: list[str],
    joint_deltas: dict[str, float] | None = None,
    frames_fps: float = 9.0,
    max_items: int = 4,
    joint_kinds: dict[str, str] | None = None,
    dtw_match=None,
    *,
    user_frame_idx: int | None = None,
    ref_frame_idx: int | None = None,
    split_angle_degs: tuple[float | None, float | None] | None = None,
    split_angle_present: bool = False,
) -> list[dict]:
    """결함 unit 별 [학생|기준] 확대 비교 PNG 생성 → list[{joint, deficitDeg, png}].

    user_frames/ref_frames: frame_extractor.extract 결과 (T,H,W,3) uint8 @ frames_fps.
    worst_seconds: vision_veto.worst_pose_timestamp (None 이면 중앙 프레임).
    fault_joints: 강조할 keypoint 이름들 (visionVeto.faultJoints 또는 편차 top).
    joint_deltas: keypoint 이름 → deficit 각도(도). 없으면 마커만(숫자 X).
    user_frame_idx/ref_frame_idx: **명시 프레임 override (quick-260702-sic)** — 둘 다
      9fps frames 배열 인덱스 공간. 주어진 측은 worst_seconds/DTW 선택을 대체한다
      (vision veto 가 측정한 그 프레임 = 표시 프레임 정합). 둘 다 None(default) 이면
      기존 동작 100% 보존 (하위호환).
    split_angle_degs (quick-260705-r6x): region=='legs' 카드의 (학생 각도, 기준
      각도) 수치 — 호 옆 표기용. None(default) 이면 legs 카드도 선+호만(수치 생략).
      non-legs/legacy 경로는 무접촉. 채점 무접촉 — display 렌더 전용.
    split_angle_present (quick-260705-wbs): 사이각 두 게이트.
      · 게이트 A — split_angle criterion 이 실제 records 에 있을 때만(True) legs
        카드에 사이각을 그린다. legs 카드는 스플릿뿐 아니라 무릎(leg_extension)/
        골반(hip) 결함으로도 뜨는데(2026-07-05 belle pod 전동작 검증), 사이각은
        "다리 벌림"의 시각 언어라 스플릿 아닌 결함에 그리면 오독을 낳는다 →
        False(default)면 스플릿 아닌 legs 카드는 r6x 이전 circle 렌더로 복귀.
      · 게이트 B — split 카드라도 학생(user) 측만 그린다. 정은지(ref) 측은 kip-up
        도립 pose 부정확으로 선이 폭주(pose 한계)해 선 없는 crop 을 유지한다.

    **인덱싱 주의**: 프레임배열은 frames_fps(9)로, keypointReport 는 report['fps']
    (reference 가변, phase4_v1=18fps 실측)로 **각자 시간 인덱싱** — upsample fps
    mismatch 회피. 기준 프레임은 DTW match 로 같은-pose 를 잡되, 반환 인덱스는 ref
    angles(rep) 공간이라 _to_rep_idx 역변환으로 9fps frames 로 내린다 (D2 fix).
    대응 실패 시 = ref 전신 폴백 + refMatch='failed' (D-04, 260702-sic confidence<0.5
    전신 폴백과 일관 — 시간비례 근사로 엉뚱한 pose 를 확대하는 오도를 제거, 정보 보존).

    결함단위 grouping (quick-260702-sic): 같은 결함에서 온 좌+우 동일 부위 관절
    (스플릿 → hips+knees)은 _group_fault_joints 로 카드 1장으로 묶이고, crop 은
    멤버 keypoint bounding box 기반. 방출 dict 에 scalar "region" 추가 (grouped 만).
    측별 crop 은 3단 강하 (Phase 25-03): 신뢰 좌표=기존 crop → 저신뢰-유한
    좌표=부위-중심 완화(relaxed) crop (카드별 차별화, 앵커 생략) → 좌표 결측=
    전신 폴백. 양측 다 신뢰 좌표 0 이면 기존처럼 skip.

    각 항목 png 는 호출측이 S3 업로드 후 presigned URL 로 doc 에 박는다.
    실패 항목은 조용히 skip (graceful).
    """
    out: list[dict] = []
    if user_frames is None or ref_frames is None:
        return out
    u_rep_fps = float(user_report.get("fps") or frames_fps)
    r_rep_fps = float(ref_report.get("fps") or frames_fps)
    u_n = int(user_frames.shape[0])
    r_n = int(ref_frames.shape[0])
    u_rep_frames = int(user_report.get("frames") or 0)
    r_rep_frames = int(ref_report.get("frames") or 0)

    # 프레임 배열 인덱스 (frames_fps 기준). override 는 worst_seconds/DTW 를 이긴다
    # — vision 측정 window 내 표시 프레임과 일치. 변환 공식은 모듈 레벨
    # _to_rep_idx (select_confident_frame 과 공유, quick-260705-ftn).
    if user_frame_idx is not None:
        u_idx = max(0, min(int(user_frame_idx), max(0, u_n - 1)))
        u_kp_idx = _to_rep_idx(u_idx, frames_fps, u_rep_fps, u_rep_frames)
    else:
        u_idx = _frame_index(worst_seconds, frames_fps, u_n)
        u_kp_idx = _frame_index(worst_seconds, u_rep_fps, u_rep_frames)
    # ref_match_failed = 기준 프레임 대응을 세울 수 없음 → ref 전신 폴백 + 앱 캡션
    # (refMatch='failed'). D-04: 어느 pose 인지 모르는 채 시간비례로 근사한 프레임을
    # 확대하면 "비교 부위 아닌 곳" 을 보여줘 오도한다 (파일럿 D2) — 260702-sic 의
    # confidence<0.5 전신 폴백과 일관된 정직 전략(오도 0, 정보 보존).
    ref_match_failed = False
    if ref_frame_idx is not None:
        # override 경로 = vision 측정 프레임 정합 (dtw 취급 — 프레임 대응 보장됨).
        r_idx = max(0, min(int(ref_frame_idx), max(0, r_n - 1)))
        r_kp_idx = _to_rep_idx(r_idx, frames_fps, r_rep_fps, r_rep_frames)
    else:
        # B1: DTW match 로 같은-pose 기준 프레임.
        # clamp 도메인 = ref angles(keypointReport) 프레임 수 r_rep_frames —
        # _matched_ref_frame 반환은 ref angles(rep) 인덱스 공간(phase4_v1=18fps,
        # 28-01 실측)이라 9fps frames 수 r_n 으로 클램프하면 안 됨 (D2 fix).
        if r_rep_frames <= 0:
            r_matched = None
        else:
            r_matched = _matched_ref_frame(dtw_match, u_idx, r_rep_frames)
        if r_matched is not None:
            r_kp_idx = r_matched  # 이미 rep(angles) 공간 — 추가 변환 불필요
            # rep→frames 역변환 (28-RESEARCH Pitfall 1, D2 fix) — 같은 _to_rep_idx
            # 공식에 fps 인자 순서만 반대(중복 공식 금지, quick-260705-ftn 관례).
            r_idx = _to_rep_idx(r_matched, r_rep_fps, frames_fps, r_n)
        else:
            # 대응 실패 → ref 전신 폴백 (D-04, ratio 근사 제거). 프레임은 중앙
            # (전신이므로 어느 순간이든 오도 0), 좌표는 아래 루프에서 강제 skip.
            ref_match_failed = True
            r_idx = r_n // 2
            r_kp_idx = r_rep_frames // 2 if r_rep_frames > 0 else 0

    deltas = joint_deltas or {}
    for unit in _group_fault_joints(list(fault_joints), joint_kinds):
        if len(out) >= max_items:
            break
        u_valid, u_relaxed = _member_pts(user_report, u_kp_idx, unit.members)
        if ref_match_failed:
            # 대응 실패 = ref 측 전신 폴백 강제 (D-04). 좌표 계산을 건너뛰고 빈
            # 리스트를 넘겨 _side_crop 3단 강하의 전신 폴백 단계로 직행 (새 렌더
            # 금지 — 기존 좌표-결측 전신 폴백 분기 재사용). 학생 카드는 유지.
            r_valid, r_relaxed = [], []
        else:
            r_valid, r_relaxed = _member_pts(ref_report, r_kp_idx, unit.members)
        if not u_valid and not r_valid:
            # 양측 다 신뢰 좌표 0 — 최소 한 측 valid 일 때만 카드 (기존 skip
            # 규칙 보존). relaxed 는 반대측이 valid 인 카드에서 전신 폴백을
            # 대체하는 강하 단계이지, 단독으로 카드를 만들지 않는다 (양측
            # 불확실 crop = 오인 위험, 260702-sic 요구 3 정신).
            continue
        member_deltas = [
            float(deltas[m]) for m in unit.members if deltas.get(m) is not None
        ]
        deficit = max(member_deltas) if member_deltas else None
        try:
            u_frame = user_frames[u_idx]
            r_frame = ref_frames[r_idx]
            u_img, u_kind, u_anchor, u_box = _side_crop(
                u_frame,
                [xy for _n, xy in u_valid],
                u_relaxed,
                anchor=_anchor_xy(u_valid, deltas) if u_valid else None,
            )
            # 게이트 B 로 ref 측 사이각 미드로잉 → kind/box 미사용(선 없는 crop).
            r_img, _r_kind, _r_anchor, _r_box = _side_crop(
                r_frame, [xy for _n, xy in r_valid], r_relaxed
            )
            # legs(스플릿) 카드: 앵커 동그라미 대신 다리 사이각(선 2 + 호 + 수치).
            # 게이트 A(quick-260705-wbs) — split_angle criterion 이 실제 records 에
            # 있는 legs 카드(split_angle_present=True)만 진입. legs 카드는 스플릿뿐
            # 아니라 무릎(leg_extension)/골반(hip) 결함으로도 뜨는데 (2026-07-05
            # belle pod 전동작 검증: power-spin=leg_extension+hip, elbow-twist=
            # hip+knee), 사이각은 "다리 벌림"의 시각 언어라 스플릿 아닌 결함에
            # 그리면 오독을 낳는다 → 스플릿 아닌 legs 카드는 이 블록 미진입, 아래
            # 기존 circle 렌더로 복귀한다.
            # 게이트 B(quick-260705-wbs) — 학생(user) 측만 그린다. 정은지(ref) 측은
            # kip-up 도립 pose 부정확으로 선이 폭주(pose 한계)해 선 없는 crop 유지.
            # TODO(Phase 22): 자체학습 pose 개선 후 정은지(ref) 측 사이각 재활성.
            # split_angle_degs=(학생 수치, 기준 수치), None 이면 수치 생략(선+호만).
            u_deg = split_angle_degs[0] if split_angle_degs else None
            u_drew_legs = False
            if (
                unit.region == "legs"
                and split_angle_present
                and u_kind == "valid"
                and u_box is not None
            ):
                u_drew_legs = _draw_side_leg_angle(
                    u_img, u_frame, user_report, u_kp_idx, u_box, u_deg
                )
            # user 측: 사이각을 그렸으면 원 생략(배지는 유지 — 배지=부족분/호=측정
            # 각도로 역할 분리), 아니면 기존 규칙 그대로.
            if u_drew_legs:
                u_crop = _mark(u_img, deficit, circle=False, anchor_px=None)
            else:
                u_crop = _mark(
                    u_img, deficit, circle=u_kind == "valid", anchor_px=u_anchor
                )
            # ref 측은 _mark/사이각 모두 없음 — 선 없는 crop 그대로(게이트 B).
            png = _compose(u_crop, r_img)
        except Exception:  # noqa: BLE001 - 단일 항목 실패는 전체를 막지 않음
            continue
        item = {
            "joint": unit.joint,
            "deficitDeg": deficit,
            "png": png,
        }
        kind = (joint_kinds or {}).get(unit.joint)
        if kind:
            item["kind"] = kind
        if unit.region:
            item["region"] = unit.region
        # D-04 provenance scalar (region 선례 형식) — 기준 프레임 대응 성공='dtw',
        # 실패='failed'(전신 폴백). override(ref_frame_idx)는 vision 측정 프레임
        # 정합이 보장되므로 'dtw' 취급. scalar str 이라 _validate_dict_only_scalars
        # flat 제약 통과. app.py _render_fault_zoom mapper 가 최종 doc 까지 pass-through.
        item["refMatch"] = "failed" if ref_match_failed else "dtw"
        out.append(item)
    return out
