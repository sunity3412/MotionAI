"""Phase 4 Wave 1 — Stage 1 PRIMARY: Gemini View Reasoning SynthesisAdapter
(POSE-03 D-18 PRIMARY / R1 R2 fix).

박제 정신:
  · D-18 PRIMARY: 영상 + 주변 맥락 → 가려진 관절 좌표 추정 (픽셀 합성 X — 좌표만).
  · R1 non-scoring 하드월: 본 어댑터의 출력은 SynthesisResult.joints / confidence
    뿐이고, pipeline 의 merge_with_temporal 가 KeypointReport / aiSynthesisMeta /
    joints3d 로만 흘려보낸다. DTW/kismam/IPSF coco_array 에 절대 mutate 0.
  · R2 fix: 항상 SynthesisResult 반환. (zeros, zeros) tuple / None 영구 금지.
    실패 → status='failed' + joints=None + confidence=None + warnings=(raw reason,).
  · G4 occlusion FP 가드: is_reference=True 시 호출 자체 skip — pipeline 의
    _call_synthesis_adapter 가 일차로 가드하지만, 어댑터 진입점에서도 동일 가드
    유지 (defense-in-depth).
  · SYNTHESIS_ENABLED=0 → status='skipped' (운영 안전 스위치).
  · OCCLUDED_JOINT_REASONING_PROMPT: Spike 003 박제 프롬프트 (RESEARCH.md Code
    Examples). 폴스포츠 도메인 컨텍스트 + indeterminate 허용 + 점수/판단 어휘 금지.
  · resolve_model("C", env_override="GEMINI_C_MODEL_OVERRIDE") 재사용 — Vision
    영역은 `gemini-3.1-pro-preview` 또는 `gemini-3.5-flash` 만 허용 (config.py
    ALLOWED_MODELS). 2.5 호출 / plain Pro 영구 금지.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

import numpy as np

from ...gemini.client import GeminiVisionCall
from ...gemini.config import resolve_model
from ..skeleton import KEYPOINT_NAMES
from .interfaces import SynthesisAdapter, SynthesisResult

log = logging.getLogger(__name__)


# ─────────────────── Occluded joint reasoning prompt (Spike 003 박제) ───────────────────
#
# RESEARCH.md Code Examples 박제. 폴스포츠 도메인 컨텍스트 + indeterminate 허용 +
# 점수/판단 어휘 금지 (analysis-objectivity-no-human-scores 정합).
OCCLUDED_JOINT_REASONING_PROMPT: str = (
    "폴스포츠 동작 분석 전문가로서 RTMW 포즈 추정기가 신뢰도 미달로 추정하지 못한\n"
    "관절 좌표를 영상과 주변 맥락으로 추정해 주세요.\n"
    "\n"
    "분석 맥락:\n"
    "- 기술: {motion_category}\n"
    "- occlusion_severe: {occlusion_severe}\n"
    "- camera_angle: {camera_angle}\n"
    "- 폴 축 x 픽셀: {pole_axis_pixel_x}\n"
    "- 고신뢰 anchor joints: {visible_anchors}\n"
    "- 이전 프레임 포즈: {prev_frame_pose}\n"
    "- 추정 필요 관절: {occluded_joints}\n"
    "\n"
    "중요 제약:\n"
    "- 픽셀 이미지 생성 금지. 좌표만 출력.\n"
    "- 불확실한 경우 \"indeterminate\" 출력 (추정 거짓말 금지).\n"
    "- 사람 점수/판단 라벨링 금지.\n"
    "\n"
    "출력 형식 (JSON):\n"
    "{{\"joints\": [{{\"name\": \"left_shoulder\", \"x\": 0.45, \"y\": 0.23,"
    " \"z_rel\": -0.1, \"confidence\": 0.65}}, ...], \"reasoning\": \"...\"}}\n"
)


# Prompt hash — aiSynthesisMeta.promptHash 감사 필드 source.
_PROMPT_HASH: str = hashlib.sha256(
    OCCLUDED_JOINT_REASONING_PROMPT.encode("utf-8")
).hexdigest()[:16]


# Model version tag — aiSynthesisMeta.modelVersion. resolve_model 가 ALLOWED_MODELS
# 박제 안에서 정한 string 이 그대로 modelId 가 되고, version 은 그 string 의
# Phase 4 안에서의 변경 이력 추적 박제 — v1 시작.
_MODEL_VERSION: str = "v1"


# SYNTHESIS_ENABLED env truthy 판정 — default OFF (운영 안전 스위치, D-07/D-08).
_SYNTHESIS_FALSY: frozenset[str] = frozenset({"0", "false", ""})


def _synthesis_enabled() -> bool:
    raw = os.environ.get("SYNTHESIS_ENABLED", "0")
    return raw.strip().lower() not in _SYNTHESIS_FALSY


def _resolve_view_reasoner_model() -> str:
    """Vision 영역 — region C model 재사용 (gemini-2.5-pro 영구 금지, config.py
    ALLOWED_MODELS 박제 가드).

    env 우선순위:
      1. GEMINI_C_MODEL_OVERRIDE (emergency manual override)
      2. GEMINI_C_MODEL (alias)
      3. config.py DEFAULT_C_MODEL = 'gemini-3.5-flash'
    """
    env_override = (
        os.environ.get("GEMINI_C_MODEL_OVERRIDE")
        or os.environ.get("GEMINI_C_MODEL")
    )
    return resolve_model("C", env_override=env_override)


class GeminiViewReasoner:
    """Stage 1 PRIMARY SynthesisAdapter — Gemini Vision 좌표 추정.

    is_reference=True 시 어댑터 진입점 자체에서 status='skipped' (G4 가드 defense
    in depth — pipeline 측 _call_synthesis_adapter 가 일차 가드).

    SYNTHESIS_ENABLED env OFF 시 status='skipped' (운영 안전 스위치).

    그 외의 모든 except Exception 경로는 status='failed' + joints=None +
    confidence=None + warnings=(raw reason,) 로 graceful degrade.
    """

    def __init__(self, *, is_reference: bool = False) -> None:
        # is_reference 는 instance-level G4 가드 박제. pipeline 측에서 분석 컨텍스트
        # 마다 다른 인스턴스를 박는 패턴이 무거우면 synthesize_occluded_joints
        # 호출 시 scene_findings 안의 정보로 분기할 수도 있지만, 본 어댑터는 직접
        # is_reference flag 를 받는 단순 path 박제.
        self._is_reference: bool = is_reference

    def synthesize_occluded_joints(
        self,
        joint_sequence: np.ndarray,
        confidence_sequence: np.ndarray,
        occlusion_mask: np.ndarray,
        scene_findings: dict,
    ) -> SynthesisResult:
        """SynthesisAdapter Protocol 구현 — 항상 SynthesisResult 반환 (R2 fix).

        실패 경로 (모두 status='failed', joints=None, confidence=None):
          · GeminiVisionCall.call() None 반환 (API key 미설정 / 4xx / schema 실패)
            → warnings=('gemini_api_error',)
          · JSON 파싱 실패 → warnings=('gemini_parse_error',)
          · 그 외 except Exception → warnings=('exception',)

        skipped 경로 (status='skipped'):
          · SYNTHESIS_ENABLED env OFF
          · is_reference=True (G4 가드)
          · occlusion_mask 가 비어 있음

        partial 경로 (status='partial', joints/conf non-None):
          · 일부 관절 응답이 'indeterminate' → 해당 관절 confidence=0.0 박제 + 합성
            결과 좌표는 0 sentinel (caller 의 merge_with_temporal 가
            synth_conf > primary_conf 비교로 자동 제거).

        applied 경로 (status='applied'):
          · 모든 추정 필요 관절을 confidence>0 으로 응답.

        분기 보호 (defense-in-depth):
          이 메서드는 ndarray 출력만 책임지며, KeypointReport / aiSynthesisMeta /
          joints3d 로의 흐름은 pipeline 의 _call_synthesis_adapter + 후속 wiring
          이 책임진다. coco_array (DTW/kismam) 에 절대 흘려보내지 않는다 (R1
          non-scoring 하드월).
        """
        if not _synthesis_enabled():
            log.info("SYNTHESIS_ENABLED OFF — GeminiViewReasoner skip")
            return SynthesisResult(status="skipped")

        if self._is_reference:
            # defense-in-depth — pipeline 측에서도 가드되지만 어댑터에서 한번 더
            # 확인 (caller 가 _call_synthesis_adapter 를 우회하는 회귀 가드).
            log.info("GeminiViewReasoner — is_reference=True G4 guard skip")
            return SynthesisResult(
                status="skipped",
                warnings=("g4_reference_guard",),
            )

        mask = np.asarray(occlusion_mask, dtype=bool)
        if not mask.any():
            return SynthesisResult(status="skipped")

        joint_sequence = np.asarray(joint_sequence)
        confidence_sequence = np.asarray(confidence_sequence)
        T, J = mask.shape[0], mask.shape[1] if mask.ndim >= 2 else 0
        if J != len(KEYPOINT_NAMES):
            # 17 joint 가 아니면 본 어댑터의 책임 영역 밖.
            return SynthesisResult(
                status="failed",
                warnings=("invalid_input_shape",),
            )

        try:
            model = _resolve_view_reasoner_model()
        except ValueError as exc:
            # config.py ALLOWED_MODELS 박제 가드 실패 — hard fail 인지 (R2 fix:
            # status='failed' 로 통일).
            log.warning("model resolve failure — graceful skip: %s", exc)
            return SynthesisResult(
                status="failed",
                warnings=("model_resolve_failed",),
                meta={"modelVersion": _MODEL_VERSION},
            )

        # Gemini 호출 path 박제 — schema 는 본 plan 단계에서 stub (None 응답
        # gracefully handle). Wave 1 시점에 schema 미박제 시 GeminiVisionCall 가
        # graceful None 을 반환하도록 의도. 실 schema 박제 + video_path 흐름은
        # Wave 3' (04-03) accuracy gate 에서 보강.
        prompt_filled = OCCLUDED_JOINT_REASONING_PROMPT.format(
            motion_category=scene_findings.get("motion_category", "unknown")
            if scene_findings
            else "unknown",
            occlusion_severe=bool(scene_findings.get("occlusion_severe"))
            if scene_findings
            else False,
            camera_angle=scene_findings.get("camera_angle", "unknown")
            if scene_findings
            else "unknown",
            pole_axis_pixel_x="?",  # pipeline wiring 시 채움.
            visible_anchors="?",
            prev_frame_pose="?",
            occluded_joints=int(mask.sum()),
        )

        # Note: Wave 1 박제 시점에는 Pydantic schema + video_path 흐름이 미완성.
        # 본 메서드는 시그너처 정합 + 4-way status 분기 + graceful degrade 만
        # 박제하고, 실 GeminiVisionCall 흐름은 SYNTHESIS_ENABLED=1 + video path +
        # schema 가 갖춰진 후속 wave 에서 보강한다. 본 단계에서 호출이 들어와도
        # graceful None 으로 떨어지도록 path 박제.
        try:
            response = self._invoke_gemini(prompt_filled, model)
        except Exception:  # noqa: BLE001 - graceful degrade
            log.exception(
                "GeminiViewReasoner — synthesize_occluded_joints exception"
            )
            return SynthesisResult(
                status="failed",
                warnings=("exception",),
                meta={
                    "modelId": model,
                    "modelVersion": _MODEL_VERSION,
                    "promptHash": _PROMPT_HASH,
                },
            )

        if response is None:
            log.info(
                "GeminiViewReasoner — graceful skip (api_or_schema_fail model=%s)",
                model,
            )
            return SynthesisResult(
                status="failed",
                warnings=("gemini_api_error",),
                meta={
                    "modelId": model,
                    "modelVersion": _MODEL_VERSION,
                    "promptHash": _PROMPT_HASH,
                },
            )

        # response 파싱 — JSON 응답 dict 또는 string.
        try:
            parsed = self._parse_response(response)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            log.warning("GeminiViewReasoner — JSON parse 실패 (model=%s)", model)
            return SynthesisResult(
                status="failed",
                warnings=("gemini_parse_error",),
                meta={
                    "modelId": model,
                    "modelVersion": _MODEL_VERSION,
                    "promptHash": _PROMPT_HASH,
                },
            )

        # parsed → (synth_joints, synth_conf) ndarray + indeterminate 분기.
        synth_joints = np.zeros((T, J, 3), dtype=np.float32)
        synth_conf = np.zeros((T, J), dtype=np.float32)
        any_partial = False
        for entry in parsed.get("joints", []):
            name = entry.get("name")
            if name not in KEYPOINT_NAMES:
                continue
            j = KEYPOINT_NAMES.index(name)
            x = entry.get("x")
            y = entry.get("y")
            z = entry.get("z_rel", 0.0)
            conf = entry.get("confidence", 0.0)
            if x == "indeterminate" or conf in (None, "indeterminate"):
                # indeterminate — confidence=0 으로 두면 merge_with_temporal 가
                # primary 보다 낮아 자동 제거. partial 분기.
                any_partial = True
                continue
            # Wave 1 단계는 단일 응답을 모든 frame 에 동일 적용 (간이 박제).
            # Wave 3' (04-03) accuracy gate 에서 frame 별 응답으로 확장.
            synth_joints[:, j, 0] = float(x)
            synth_joints[:, j, 1] = float(y)
            synth_joints[:, j, 2] = float(z)
            synth_conf[:, j] = float(conf)

        status: str = "partial" if any_partial else "applied"

        meta = {
            "modelId": model,
            "modelVersion": _MODEL_VERSION,
            "promptHash": _PROMPT_HASH,
            "framesConsidered": int(T),
            "framesSynthesized": int(mask.any(axis=1).sum()),
            "geminiCalls": 1,
            "framesSkipped": 0,
            "framesFailed": 0,
            "estCostUsd": 0.0,
        }

        return SynthesisResult(
            status=status,  # type: ignore[arg-type]
            joints=synth_joints,
            confidence=synth_conf,
            warnings=(),
            meta=meta,
        )

    # ───────────── 내부 헬퍼 ─────────────

    def _invoke_gemini(self, prompt_filled: str, model: str) -> Any | None:
        """GeminiVisionCall 호출 박제 — Wave 1 시점에는 schema 미박제 path 박제.

        본 메서드는 후속 Wave 가 schema + video_path 인자를 추가하기 전까지의
        진입점 박제. 현재는 SYNTHESIS_ENABLED=1 + video path 가 갖춰진 호출
        path 박제 없이 graceful None 반환 (API 흐름 차단 0).
        """
        # Wave 1 시점 — GeminiVisionCall 인스턴스 박제 만 (실 호출 X). 후속
        # wave 에서 video_path 인자를 받아 .call(video_path) 호출하도록 확장.
        # 본 박제는 어떤 schema 도 모르므로 None 반환으로 graceful skip.
        _ = GeminiVisionCall  # 모듈 참조 유지 (회귀 grep gate)
        _ = prompt_filled  # 후속 wave 가 사용
        _ = model
        return None

    def _parse_response(self, response: Any) -> dict:
        """response → dict 변환. 실패 시 ValueError / KeyError 등 raise."""
        if isinstance(response, dict):
            return response
        if isinstance(response, str):
            return json.loads(response)
        # Pydantic BaseModel 호환 — model_dump 가 있으면 사용.
        if hasattr(response, "model_dump"):
            return response.model_dump()
        raise ValueError(
            f"GeminiViewReasoner — unsupported response type {type(response).__name__}"
        )


__all__ = [
    "GeminiViewReasoner",
    "OCCLUDED_JOINT_REASONING_PROMPT",
]
