"""Phase 17 Wave 2 — 영역 D keypoint 보강 (Gemini Pro Vision).

박제 정신:
  · 17-RESEARCH §9 Wave 2 + AI-SPEC §4b 영역 D 정합. RTMW 의 `uncertainty_proxy > 0.5`
    frame 을 Gemini Pro 의 영상 이해로 보강 (의상/머리 방향/폴 접촉점 단서).
  · B2 hard gate (2026-06-12, Codex review) — 3D `coco_array` (DTW/KISMAM/각도 점수
    입력) 는 본 모듈의 입출력 격리. 시그너처 인자 `coco_array` / `rtmw_array` 영구
    박제 X. user-visible `KeypointReport.data` + `confidence` 만 보강.
  · 3차 R-B3 정합 — Gemini 가 normalized [0,1] 좌표 self-return. frame_w/h 인자 박제
    X. KeypointRefinement Pydantic schema 의 Field(ge=0, le=1) 가 1차 차단.
  · G5 좌표 환각 가드 — 인접 frame (±2) 의 동일 joint 좌표와 정규화 L2 거리 ≥ 0.15
    면 폐기 + guardrail_blocked_count++. 인접 frame 도 confidence < 0.3 면 비교 skip.
  · 좌우 mirror hint — left/right joint pair 가 RTMW 원본 대비 swap 의심 시
    `mirror_hint[frame_idx] = "swap_lr"` 박제. 1차 PR 은 audit only.
  · Graceful 폴백: low_uncertainty_frame_indices 빈 / GeminiVisionCall.call() None →
    빈 dict 반환 (Gemini 호출 0 박제).
  · 객관성 가드 — `enforce_object_guard=False` (영역 D 만 좌표 허용, AI-SPEC §6 G1).
    schema 의 `RefinedKeypoint` 가 x/y/confidence/joint_key/frame_index 외 필드 거부 —
    점수/판단 어휘는 schema 차원에서 출력 불가.

후속 plan 정합:
  · 본 모듈은 후속 plan (좌표계 계약 + 2D→3D lifter + `coco_array` in-place 주입) 이
    들어올 자리만 박제 — 본 plan 에선 `KeypointReport` 만 보강.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import math

from .client import GeminiVisionCall
from .config import resolve_model
from .schemas import KeypointRefinement, JointKeyLiteral


log = logging.getLogger(__name__)


# ─────────────────── G5 가드 / chunk 박제 상수 ───────────────────

# G5 — 인접 frame ±2 의 동일 joint 와 정규화 L2 거리 임계값.
_G5_NEIGHBOR_DISTANCE_THRESHOLD: float = 0.15

# G5 — 인접 frame confidence 이 본 임계값 미만이면 비교 skip (둘 다 못 믿는 케이스).
_G5_NEIGHBOR_MIN_CONFIDENCE: float = 0.3

# G5 — 인접 frame 검색 윈도 ±N.
_G5_NEIGHBOR_WINDOW: int = 2

# Gemini 호출 chunk 크기 — KeypointRefinement.refined max_length=200 / 8 joints = 25 frame.
_FRAME_CHUNK_SIZE: int = 25

# JointKeyLiteral 8개 박제 — sunity_shared.analysis.skeleton.JOINT_KEYS 정합.
_TARGET_JOINTS: tuple[JointKeyLiteral, ...] = (
    "left_elbow",
    "right_elbow",
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
)

# 좌우 pair 박제 — mirror hint 산출용. KeypointReport 의 _KEYPOINT_NAMES (8 body) 와
# 부분 overlap (shoulder/hip/knee). elbow 는 schema 에는 있고 KeypointReport 에는 없음.
_MIRROR_PAIRS: tuple[tuple[JointKeyLiteral, JointKeyLiteral], ...] = (
    ("left_elbow", "right_elbow"),
    ("left_shoulder", "right_shoulder"),
    ("left_hip", "right_hip"),
    ("left_knee", "right_knee"),
)


# ─────────────────── prompt (한국어, normalized [0,1] 강제) ───────────────────
#
# 3차 R-B3 정합 — Gemini 가 frame width/height 모름 (frame 좌상=0, 우하=1 self-normalize).
# 객관성 헌장 정합 — 점수 / 사람 판단 어휘 영구 금지. enforce_object_guard=False 는
# 좌표 패턴 (`x=`, `y=`, `좌표`) 만 우회 — RefinedKeypoint schema 가 점수/판단 출력 불가.

_AUGMENT_PROMPT: str = (
    "당신은 폴스포츠 동작 영상의 객관적 keypoint 좌표 보강기입니다.\n"
    "주어진 영상의 지정된 frame 들에서 다음 8 관절의 좌표를 추출하세요.\n"
    "관절: left_elbow, right_elbow, left_shoulder, right_shoulder,\n"
    "      left_hip, right_hip, left_knee, right_knee.\n"
    "\n"
    "좌표는 frame 의 좌상단을 (0, 0), 우하단을 (1, 1) 로 정규화한 [0, 1] 값으로\n"
    "반환하세요. 절대 픽셀 좌표 금지.\n"
    "\n"
    "각 RefinedKeypoint 항목은 frame_index / joint_key / x_normalized / y_normalized\n"
    "/ confidence 필드만 박으세요. 점수/등급/사람 판단 어휘 영구 금지.\n"
    "관절이 영상에서 보이지 않으면 그 frame×joint 는 응답에서 생략하세요.\n"
    "\n"
    "대상 frame index 리스트: {frame_indices}\n"
)


# ─────────────────── 영역 D 호출 설정 (AI-SPEC §4) ───────────────────
#
# Pro preview — 영상 좌표 보정 깊이 필요. temperature 0.0 (객관 좌표), thinking_budget=0
# (Pro 3.x default-on thinking 비용 박제 차단), max_output_tokens 2048 (200 refined ×
# 5 field ~= 충분).

_TEMPERATURE: float = 0.0
_MAX_OUTPUT_TOKENS: int = 2048
_THINKING_BUDGET: int = 0


def _resolve_d_model() -> str:
    """env 박제 → resolve_model('D', env_override=...) 단일 source.

    우선순위:
      1. GEMINI_D_MODEL (운영 override — emergency)
      2. DEFAULT_D_MODEL ('gemini-3.1-pro-preview')

    Raises:
      ValueError: override 가 ALLOWED_MODELS 박제 외 (2.5 호출 / plain Pro 차단).
    """
    env_override = os.environ.get("GEMINI_D_MODEL")
    return resolve_model("D", env_override=env_override)


# ─────────────────── KeypointReport 좌표 lookup 헬퍼 ───────────────────


def _keypoint_report_data_xy(
    keypoint_report_2d: Any, frame_idx: int, joint_name: str
) -> tuple[float, float] | None:
    """KeypointReport.data 에서 (frame_idx, joint_name) 의 (x, y) 박제.

    data 박제 위치 = (frame_idx * J + joint_idx) * 2. joint_name 이 KeypointReport.joints
    안에 없으면 None.
    """
    joints = list(keypoint_report_2d.joints)
    if joint_name not in joints:
        return None
    joint_idx = joints.index(joint_name)
    J = len(joints)
    base = (frame_idx * J + joint_idx) * 2
    data = keypoint_report_2d.data
    if base + 1 >= len(data):
        return None
    return float(data[base]), float(data[base + 1])


def _keypoint_report_confidence(
    keypoint_report_2d: Any, frame_idx: int, joint_name: str
) -> float | None:
    """KeypointReport.confidence 에서 (frame_idx, joint_name) 박제."""
    joints = list(keypoint_report_2d.joints)
    if joint_name not in joints:
        return None
    joint_idx = joints.index(joint_name)
    J = len(joints)
    idx = frame_idx * J + joint_idx
    confidence = keypoint_report_2d.confidence
    if idx >= len(confidence):
        return None
    return float(confidence[idx])


# JointKeyLiteral 의 8 schema joint key → KeypointReport.joints 의 8 body joint key 매핑.
# schema 는 elbow/shoulder/hip/knee, KeypointReport 는 shoulder/hip/knee/hand.
# 겹치는 6개 (shoulder/hip/knee) 만 KeypointReport 박제 가능. 나머지 (elbow 2개) 는
# audit-only — Firestore geminiD.augmentedFrames 에 박힘.
_SCHEMA_TO_REPORT_JOINT: dict[str, str | None] = {
    "left_elbow": None,  # KeypointReport 에 elbow 없음 — audit only.
    "right_elbow": None,
    "left_shoulder": "left_shoulder",
    "right_shoulder": "right_shoulder",
    "left_hip": "left_hip",
    "right_hip": "right_hip",
    "left_knee": "left_knee",
    "right_knee": "right_knee",
}


# ─────────────────── G5 좌표 환각 가드 ───────────────────


def _check_neighbor_distance(
    keypoint_report_2d: Any,
    frame_idx: int,
    schema_joint_key: str,
    refined_x: float,
    refined_y: float,
) -> bool:
    """G5 — 보강된 좌표 vs 인접 frame ±N 동일 joint 좌표 정규화 L2 거리.

    인접 frame 도 confidence < 0.3 면 비교 skip (둘 다 못 믿는 케이스). 모든 인접
    frame 의 거리가 < 0.15 면 통과 (True). 하나라도 ≥ 0.15 면 폐기 (False).

    Args:
      keypoint_report_2d: caller 의 KeypointReport (2D 보고서).
      frame_idx: 보강 대상 frame.
      schema_joint_key: 보강 대상 joint (schema 의 JointKeyLiteral, 8 keys).
      refined_x, refined_y: Gemini 보강 정규화 [0,1] 좌표.

    Returns:
      True = 통과 (refined 좌표 박제 가능). False = 폐기 (G5 가드 발동).
    """
    report_joint = _SCHEMA_TO_REPORT_JOINT.get(schema_joint_key)
    if report_joint is None:
        # KeypointReport 에 elbow 없음 — 비교 데이터 없음 → 통과 (audit only).
        return True

    frames = int(getattr(keypoint_report_2d, "frames", 0))
    for offset in range(-_G5_NEIGHBOR_WINDOW, _G5_NEIGHBOR_WINDOW + 1):
        if offset == 0:
            continue
        neighbor_idx = frame_idx + offset
        if neighbor_idx < 0 or neighbor_idx >= frames:
            continue
        neighbor_conf = _keypoint_report_confidence(
            keypoint_report_2d, neighbor_idx, report_joint
        )
        if neighbor_conf is None or neighbor_conf < _G5_NEIGHBOR_MIN_CONFIDENCE:
            # 인접 frame 도 못 믿음 — 비교 skip.
            continue
        neighbor_xy = _keypoint_report_data_xy(
            keypoint_report_2d, neighbor_idx, report_joint
        )
        if neighbor_xy is None:
            continue
        nx, ny = neighbor_xy
        dx = refined_x - nx
        dy = refined_y - ny
        l2 = math.sqrt(dx * dx + dy * dy)
        if l2 >= _G5_NEIGHBOR_DISTANCE_THRESHOLD:
            return False
    return True


# ─────────────────── mirror hint 박제 ───────────────────


def _detect_mirror_swap(
    keypoint_report_2d: Any,
    refined_frame_dict: dict[str, tuple[float, float]],
    frame_idx: int,
) -> bool:
    """left/right joint pair 가 RTMW 원본 대비 frame 내 좌우 픽셀 위치 swap 의심.

    refined 의 left.x > refined 의 right.x AND RTMW 원본은 반대 (left.x < right.x)
    인 pair 가 1개 이상이면 swap 의심.

    Args:
      keypoint_report_2d: caller 의 KeypointReport (2D 보고서).
      refined_frame_dict: {schema_joint_key: (x, y)} — 본 frame 의 refined 좌표.
      frame_idx: 대상 frame.

    Returns:
      True = swap 의심 → mirror_hint[frame_idx] = "swap_lr".
    """
    for left_key, right_key in _MIRROR_PAIRS:
        if left_key not in refined_frame_dict or right_key not in refined_frame_dict:
            continue
        refined_left_x = refined_frame_dict[left_key][0]
        refined_right_x = refined_frame_dict[right_key][0]
        report_left = _SCHEMA_TO_REPORT_JOINT.get(left_key)
        report_right = _SCHEMA_TO_REPORT_JOINT.get(right_key)
        if report_left is None or report_right is None:
            # KeypointReport 에 elbow 없음 — RTMW 원본 비교 불가, skip.
            continue
        rtmw_left = _keypoint_report_data_xy(
            keypoint_report_2d, frame_idx, report_left
        )
        rtmw_right = _keypoint_report_data_xy(
            keypoint_report_2d, frame_idx, report_right
        )
        if rtmw_left is None or rtmw_right is None:
            continue
        # swap 의심: refined left.x > refined right.x AND rtmw left.x < rtmw right.x.
        if refined_left_x > refined_right_x and rtmw_left[0] < rtmw_right[0]:
            return True
    return False


# ─────────────────── 메인 함수 ───────────────────


def augment_low_confidence(
    video_path: str,
    low_uncertainty_frame_indices: list[int],
    keypoint_report_2d: Any,
) -> dict[str, Any]:
    """RTMW 저신뢰 frame 의 8 keypoint 를 Gemini Pro Vision 으로 보강.

    Args:
      video_path: 로컬 영상 path (Pod tmpfs / Lambda /tmp). caller (pipeline) 가 박은
        local_video_path 만 사용 — S3 재다운로드 0, RTMW 재실행 0 (B4 hard gate).
      low_uncertainty_frame_indices: RTMW `uncertainty_proxy > 0.5` 인 frame index 리스트.
        빈 list 면 Gemini 호출 0 (graceful 빈 dict 반환).
      keypoint_report_2d: caller 가 방금 만든 `KeypointReport` (assemble.build_keypoint_report
        산출). 2D normalized 좌표 + confidence 박제. **3D `coco_array` 는 입력 X**
        (B2 hard gate — 시그너처 인자에 coco_array 영구 박제 X).

    Returns:
      dict — keys:
        refined: list[{frame_index, joint_key, x_normalized, y_normalized, confidence}]
        augmented_frames: list[int]
        original_rtmw_uncertainty_proxy: list[float] (KeypointReport.confidence 의 invert)
        guardrail_blocked_count: int (G5 폐기 카운트)
        mirror_hint: dict[str, str] (frame_idx str → "swap_lr")
        model: str

      low_uncertainty_frame_indices 가 빈 list 면 모든 key 가 빈/0 dict 반환 (Gemini 호출 0).
      Gemini call() None 반환 시도 모든 key 빈/0 dict (graceful 폴백).

    Raises:
      ValueError: GeminiVisionCall 의 G1 객관성 가드 (점수/판단 어휘) 매치 — graceful X.
    """
    model = _resolve_d_model()

    # ── 빈 input 박제 — Gemini 호출 0. ─────────────────────────────────────
    if not low_uncertainty_frame_indices:
        log.info(
            "augment_low_confidence skip — low_uncertainty_frame_indices empty (model=%s).",
            model,
        )
        return {
            "refined": [],
            "augmented_frames": [],
            "original_rtmw_uncertainty_proxy": [],
            "guardrail_blocked_count": 0,
            "mirror_hint": {},
            "model": model,
        }

    # ── original_rtmw_uncertainty_proxy 산출 (KeypointReport.confidence invert) ──
    # (3차 R-W2 정합: KeypointReport.confidence 가 user-visible audit single source).
    original_uncertainty_list: list[float] = []
    for frame_idx in low_uncertainty_frame_indices:
        max_uncertainty = 0.0
        for joint_name in _SCHEMA_TO_REPORT_JOINT.values():
            if joint_name is None:
                continue
            conf = _keypoint_report_confidence(
                keypoint_report_2d, frame_idx, joint_name
            )
            if conf is None:
                continue
            uncertainty = 1.0 - conf
            if uncertainty > max_uncertainty:
                max_uncertainty = uncertainty
        original_uncertainty_list.append(float(max_uncertainty))

    # ── chunked Gemini 호출 (KeypointRefinement.refined max_length=200 / 8 joints) ──
    refined_all: list[dict[str, Any]] = []

    for chunk_start in range(
        0, len(low_uncertainty_frame_indices), _FRAME_CHUNK_SIZE
    ):
        chunk = low_uncertainty_frame_indices[
            chunk_start : chunk_start + _FRAME_CHUNK_SIZE
        ]
        prompt = _AUGMENT_PROMPT.format(frame_indices=chunk)
        call = GeminiVisionCall(
            schema=KeypointRefinement,
            model=model,
            prompt=prompt,
            temperature=_TEMPERATURE,
            max_output_tokens=_MAX_OUTPUT_TOKENS,
            thinking_budget=_THINKING_BUDGET,
            enforce_object_guard=False,  # 영역 D 만 좌표 허용 (AI-SPEC §6 G1).
            allow_coords=True,
        )

        parsed: KeypointRefinement | None = call.call(video_path)
        if parsed is None:
            log.info(
                "augment_low_confidence graceful skip — call None (model=%s chunk=%d).",
                model,
                chunk_start,
            )
            continue

        for rk in parsed.refined:
            refined_all.append(
                {
                    "frame_index": int(rk.frame_index),
                    "joint_key": str(rk.joint_key),
                    "x_normalized": float(rk.x_normalized),
                    "y_normalized": float(rk.y_normalized),
                    "confidence": float(rk.confidence),
                }
            )

    # ── G5 가드 + mirror hint 산출 ────────────────────────────────────────
    guardrail_blocked_count = 0
    refined_passed: list[dict[str, Any]] = []
    # frame_idx → {joint_key: (x, y)} 박제 — mirror hint 비교용.
    refined_by_frame: dict[int, dict[str, tuple[float, float]]] = {}

    for entry in refined_all:
        f_idx = entry["frame_index"]
        j_key = entry["joint_key"]
        rx = entry["x_normalized"]
        ry = entry["y_normalized"]
        # G5 가드.
        if not _check_neighbor_distance(
            keypoint_report_2d, f_idx, j_key, rx, ry
        ):
            guardrail_blocked_count += 1
            log.info(
                "augment_low_confidence G5 가드 발동 frame=%d joint=%s (model=%s).",
                f_idx,
                j_key,
                model,
            )
            continue
        refined_passed.append(entry)
        refined_by_frame.setdefault(f_idx, {})[j_key] = (rx, ry)

    # mirror hint — frame 별로 좌우 swap 의심 검사.
    mirror_hint: dict[str, str] = {}
    for f_idx, joint_dict in refined_by_frame.items():
        if _detect_mirror_swap(keypoint_report_2d, joint_dict, f_idx):
            mirror_hint[str(f_idx)] = "swap_lr"

    augmented_frames = sorted({entry["frame_index"] for entry in refined_passed})

    return {
        "refined": refined_passed,
        "augmented_frames": augmented_frames,
        "original_rtmw_uncertainty_proxy": original_uncertainty_list,
        "guardrail_blocked_count": guardrail_blocked_count,
        "mirror_hint": mirror_hint,
        "model": model,
    }


__all__ = ["augment_low_confidence"]
