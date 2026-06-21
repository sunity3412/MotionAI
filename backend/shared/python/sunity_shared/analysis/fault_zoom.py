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

import numpy as np
from PIL import Image, ImageDraw

# crop 한 변 = 프레임 짧은 변의 비율 (관절 주변 zoom — 작을수록 더 확대).
_CROP_FRAC = 0.42
# 합성 시 각 crop 출력 한 변(px). 두 장 가로 합성 → (2*OUT, OUT).
_OUT = 360
# 마커 색 (브랜드 #FF4B33).
_BRAND = (255, 75, 51)


def _frame_index(seconds: float | None, fps: float, n_frames: int) -> int:
    """worst-pose 초 → 프레임 인덱스 (clamp). seconds None → 중앙 프레임."""
    if n_frames <= 0:
        return 0
    if seconds is None or fps <= 0:
        return n_frames // 2
    idx = int(round(seconds * fps))
    return max(0, min(idx, n_frames - 1))


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


def _crop_zoom(frame: np.ndarray, cx: float, cy: float) -> Image.Image:
    """정규화 중심 (cx,cy) 주변을 정사각 crop 후 _OUT 으로 리사이즈.

    crop 한 변 = min(H,W)*_CROP_FRAC. 경계를 넘으면 안쪽으로 shift (검은 패딩 회피).
    """
    h, w = frame.shape[0], frame.shape[1]
    side = max(16, int(round(min(h, w) * _CROP_FRAC)))
    px, py = cx * w, cy * h
    left = int(round(px - side / 2))
    top = int(round(py - side / 2))
    left = max(0, min(left, w - side)) if w >= side else 0
    top = max(0, min(top, h - side)) if h >= side else 0
    right = min(w, left + side)
    bottom = min(h, top + side)
    crop = frame[top:bottom, left:right]
    img = Image.fromarray(crop).convert("RGB").resize((_OUT, _OUT), Image.BILINEAR)
    return img


def _mark(img: Image.Image, deficit_deg: float | None) -> Image.Image:
    """crop 중앙에 브랜드 원 + (deficit 있으면) 숫자 배지. 한글 없음(폰트 회피)."""
    draw = ImageDraw.Draw(img)
    c = _OUT // 2
    r = int(_OUT * 0.16)
    draw.ellipse([c - r, c - r, c + r, c + r], outline=_BRAND, width=4)
    if deficit_deg is not None and deficit_deg > 0:
        txt = f"{int(round(deficit_deg))}deg"
        # 배지 배경 (가독성) — 우상단.
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
) -> list[dict]:
    """결함 관절별 [학생|기준] 확대 비교 PNG 생성 → list[{joint, deficitDeg, png}].

    user_frames/ref_frames: frame_extractor.extract 결과 (T,H,W,3) uint8 @ frames_fps.
    worst_seconds: vision_veto.worst_pose_timestamp (None 이면 중앙 프레임).
    fault_joints: 강조할 keypoint 이름들 (visionVeto.faultJoints 또는 편차 top).
    joint_deltas: keypoint 이름 → deficit 각도(도). 없으면 마커만(숫자 X).

    **인덱싱 주의**: 프레임배열은 frames_fps(9)로, keypointReport 는 report['fps']
    (user 18 / reference 가변)로 **각자 시간 인덱싱** — upsample fps mismatch 회피.
    기준 프레임은 같은 정규화 시간 위치(ratio)로 근사(DTW 미threading MVP, held pose).

    각 항목 png 는 호출측이 S3 업로드 후 presigned URL 로 doc 에 박는다.
    실패 항목은 조용히 skip (graceful). 좌표 부재 관절도 skip.
    """
    out: list[dict] = []
    if user_frames is None or ref_frames is None:
        return out
    u_rep_fps = float(user_report.get("fps") or frames_fps)
    r_rep_fps = float(ref_report.get("fps") or frames_fps)
    u_n = int(user_frames.shape[0])
    r_n = int(ref_frames.shape[0])
    # 프레임 배열 인덱스 (frames_fps 기준).
    u_idx = _frame_index(worst_seconds, frames_fps, u_n)
    ratio = (u_idx / max(1, u_n - 1)) if u_n > 1 else 0.0
    r_idx = int(round(ratio * (r_n - 1))) if r_n > 1 else 0
    # keypointReport 인덱스 (각 report 의 fps 기준 — 같은 절대/상대 시간).
    u_rep_frames = int(user_report.get("frames") or 0)
    r_rep_frames = int(ref_report.get("frames") or 0)
    u_kp_idx = _frame_index(worst_seconds, u_rep_fps, u_rep_frames)
    r_kp_idx = int(round(ratio * (r_rep_frames - 1))) if r_rep_frames > 1 else 0

    seen: set[str] = set()
    for joint in fault_joints:
        if joint in seen:
            continue
        seen.add(joint)
        if len(out) >= max_items:
            break
        u_xy = _kp_xy(user_report, u_kp_idx, joint)
        r_xy = _kp_xy(ref_report, r_kp_idx, joint)
        if u_xy is None or r_xy is None:
            continue
        try:
            u_crop = _mark(
                _crop_zoom(user_frames[u_idx], u_xy[0], u_xy[1]),
                (joint_deltas or {}).get(joint),
            )
            r_crop = _crop_zoom(ref_frames[r_idx], r_xy[0], r_xy[1])
            png = _compose(u_crop, r_crop)
        except Exception:  # noqa: BLE001 - 단일 항목 실패는 전체를 막지 않음
            continue
        item = {
            "joint": joint,
            "deficitDeg": (joint_deltas or {}).get(joint),
            "png": png,
        }
        kind = (joint_kinds or {}).get(joint)
        if kind:
            item["kind"] = kind
        out.append(item)
    return out
