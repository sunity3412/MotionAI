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
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

# crop 한 변 = 프레임 짧은 변의 비율 (관절 주변 zoom — 작을수록 더 확대).
_CROP_FRAC = 0.42
# 합성 시 각 crop 출력 한 변(px). 두 장 가로 합성 → (2*OUT, OUT).
_OUT = 360
# 마커 색 (브랜드 #FF4B33).
_BRAND = (255, 75, 51)

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


def _frame_index(seconds: float | None, fps: float, n_frames: int) -> int:
    """worst-pose 초 → 프레임 인덱스 (clamp). seconds None → 중앙 프레임."""
    if n_frames <= 0:
        return 0
    if seconds is None or fps <= 0:
        return n_frames // 2
    idx = int(round(seconds * fps))
    return max(0, min(idx, n_frames - 1))


def _matched_ref_frame(dtw_match, user_frame: int, ref_n: int) -> int | None:
    """B1 — DTW match 로 학생 9fps 프레임 ↔ 기준 9fps 프레임(같은 pose). None=불가.

    match.start = 사용자 구간 시작(angles 9fps), path = [(user_local, ref_idx)...]
    (ref_idx = 기준 angles 9fps 절대). 학생 프레임을 구간-로컬로 변환 후 path 에서
    같은 user_local 의 ref_idx 들의 median 을 고른다(DTW 1:N 대응 안정화).
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


def _side_crop(
    frame: np.ndarray,
    valid_pts: list[tuple[float, float]],
    relaxed_pts: list[tuple[float, float]],
    anchor: tuple[float, float] | None = None,
) -> tuple[Image.Image, str, tuple[int, int] | None]:
    """한 측(user/ref)의 unit crop 3단 강하 → (이미지, crop_kind, anchor_px).

    crop_kind ∈ {"valid", "relaxed", "full"} — _mark 가 앵커 표시 여부 결정.
    anchor_px = anchor(결함 관절 정규화 좌표)의 crop-내 출력 픽셀 좌표 — valid
    crop 에서만 산출 (circle 을 crop 중심이 아닌 관절 좌표에 고정, Task 2).
    relaxed/full 은 좌표 불확실이라 None (앵커 생략 = 오인 방지).

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
            ax = int(round((anchor[0] * w - left) / s * _OUT))
            ay = int(round((anchor[1] * h - top) / s * _OUT))
            anchor_px = (
                max(0, min(_OUT - 1, ax)),
                max(0, min(_OUT - 1, ay)),
            )
        return _render_crop(frame, left, top, s), "valid", anchor_px
    if relaxed_pts:
        left, top, s = _box_for(relaxed_pts, _RELAXED_MARGIN)
        return _render_crop(frame, left, top, s), "relaxed", None
    return _full_frame_fit(frame), "full", None


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

    **인덱싱 주의**: 프레임배열은 frames_fps(9)로, keypointReport 는 report['fps']
    (user 18 / reference 가변)로 **각자 시간 인덱싱** — upsample fps mismatch 회피.
    기준 프레임은 같은 정규화 시간 위치(ratio)로 근사(DTW 미threading MVP, held pose).

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

    def _to_rep_idx(idx: int, rep_fps: float, rep_frames: int) -> int:
        # 9fps frames 인덱스 → keypointReport fps 인덱스 (기존 B1 변환 공식 재사용).
        return max(0, min(
            int(round(idx / max(1e-6, frames_fps) * rep_fps)),
            max(0, rep_frames - 1),
        ))

    # 프레임 배열 인덱스 (frames_fps 기준). override 는 worst_seconds/DTW 를 이긴다
    # — vision 측정 프레임(sourceFrameIndices median)과 표시 프레임 일치.
    if user_frame_idx is not None:
        u_idx = max(0, min(int(user_frame_idx), max(0, u_n - 1)))
        u_kp_idx = _to_rep_idx(u_idx, u_rep_fps, u_rep_frames)
    else:
        u_idx = _frame_index(worst_seconds, frames_fps, u_n)
        u_kp_idx = _frame_index(worst_seconds, u_rep_fps, u_rep_frames)
    if ref_frame_idx is not None:
        r_idx = max(0, min(int(ref_frame_idx), max(0, r_n - 1)))
        r_kp_idx = _to_rep_idx(r_idx, r_rep_fps, r_rep_frames)
    else:
        # B1: DTW match 로 같은-pose 기준 프레임. 불가 시 시간비례 근사 폴백.
        r_matched = _matched_ref_frame(dtw_match, u_idx, r_n)
        if r_matched is not None:
            r_idx = r_matched
            r_kp_idx = _to_rep_idx(r_matched, r_rep_fps, r_rep_frames)
        else:
            ratio = (u_idx / max(1, u_n - 1)) if u_n > 1 else 0.0
            r_idx = int(round(ratio * (r_n - 1))) if r_n > 1 else 0
            r_kp_idx = (
                int(round(ratio * (r_rep_frames - 1))) if r_rep_frames > 1 else 0
            )

    deltas = joint_deltas or {}
    for unit in _group_fault_joints(list(fault_joints), joint_kinds):
        if len(out) >= max_items:
            break
        u_valid, u_relaxed = _member_pts(user_report, u_kp_idx, unit.members)
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
            u_img, u_kind, u_anchor = _side_crop(
                user_frames[u_idx],
                [xy for _n, xy in u_valid],
                u_relaxed,
                anchor=_anchor_xy(u_valid, deltas) if u_valid else None,
            )
            u_crop = _mark(
                u_img, deficit, circle=u_kind == "valid", anchor_px=u_anchor
            )
            r_crop, _r_kind, _r_anchor = _side_crop(
                ref_frames[r_idx], [xy for _n, xy in r_valid], r_relaxed
            )
            png = _compose(u_crop, r_crop)
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
        out.append(item)
    return out
