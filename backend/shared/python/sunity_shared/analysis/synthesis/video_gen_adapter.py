"""Phase 4 Wave 4 — Stage 4 영상 생성 plug-in 슬롯 stub (POSE-03 D-30 D-31).

D-25 정합: Omni Vertex endpoint 공식 등록 미완 (mid-to-late June 2026 윈도우).
본 모듈은 활성화 전 구현체 슬롯 박제만 한다 — 실제 API 호출 코드 없음.

활성화 조건 (R9 — env flag 단독 불충분, 4개 모두 충족 필수):
  1. SYNTHESIS_VIDEO_GEN_ENABLED="1" env (truthy check)
  2. Omni Vertex endpoint 공식 등록 확인 — model id / terms / region / IO shape
     명세 Vertex AI Model Garden console 박제 후 진행
  3. 10-video pose consistency gate 통과 — 생성 영상에서 RTMW 가 일관된 pose
     를 뽑아내는지 belle + Pod sweep 으로 입증
  4. belle 승인 — 비용 (D-28) 및 분석 영향 sign-off
  위 4개 중 단 하나라도 부재 시 활성화 금지.

R1 non-scoring 하드월 (W5 미래 우회 방지):
  실 구현 시 generate_virtual_view 의 raw ndarray 반환을 pipeline 에 직결하지
  말 것 — SynthesisResult 로 래핑하거나 _call_synthesis_adapter 가 SynthesisResult
  로 변환해야 non-scoring 채널 분리 (R1) 유지. DTW/kismam/IPSF DTW/kismam 입력
  에 절대 흐르지 않는다.

# 비용 박제 (D-28): Omni $2-6/10초 → 30~60초 영상 = $6-36/영상 (조건부 트리거 필수)
# Veo 3.1: Vertex Public Preview 가격 (가격 변동 확인 필요)
# Gemini Vision reasoning (현 PRIMARY): $0.12/video — 비교 기준선

연관 계약:
  · sunity_shared.analysis.synthesis.interfaces.VideoGenerationAdapter — Protocol
  · 04-CONTEXT.md D-30 D-31 — Stage 4 plug-in slot 정책
  · 04-RESEARCH.md §Pitfall 6 — Omni 조기 도입 차단 사유
"""

from __future__ import annotations

import logging
import os

import numpy as np

from .interfaces import VideoGenerationAdapter

log = logging.getLogger(__name__)


# Google Gemini API: Apache-2.0 SDK + Google ToS (DPA + zero-data-retention).
# D-20 상업 OK (Gemini API 라이선스 박제, mmpose RTMW 와 함께 commercial-friendly
# stack 일부).
class OmniVertexAdapter:
    """Gemini Omni via Vertex AI 어댑터 stub — Vertex GA 후 활성화 (D-30, D-25).

    Wave 4 시점 정책: __init__ 은 raise 하지 않는다 (인스턴스 생성 허용 —
    팩토리 truthy 체크와 분리). 실 호출 경로 generate_virtual_view 만
    NotImplementedError 로 차단.

    활성화 절차:
      1. Vertex AI Model Garden console 에서 Omni endpoint model id / region /
         terms / IO shape 확인.
      2. GEMINI_API_KEY 또는 service account 자격 증명을 AWS SSM Parameter Store
         에 박제 (CLAUDE.md §3 시크릿 정책 — .env 하드코딩 금지).
      3. 본 클래스의 generate_virtual_view 에 Vertex SDK 호출 + 응답 파싱 +
         (T', H, W, 3) ndarray 변환 박제.
      4. 10-video pose consistency gate 통과 후 belle 승인.
    """

    def __init__(self) -> None:
        log.debug("OmniVertexAdapter stub — 활성화 전 호출 금지 (D-30)")

    def generate_virtual_view(
        self,
        frames: np.ndarray,
        target_camera_delta: tuple[float, float, float],
    ) -> np.ndarray:
        raise NotImplementedError(
            "OmniVertexAdapter 미구현 — Vertex GA 후 활성화 (D-25). "
            "Vertex endpoint 등록 확인: Vertex AI Model Garden console."
        )


# Veo 3.1: Vertex Public Preview, Phase 17 DPA cover (D-27).
class VeoAdapter:
    """Veo 3.1 Vertex Public Preview 어댑터 stub (D-27 PoC 대상).

    Wave 4 시점 정책: __init__ raise 안 함, generate_virtual_view 에서만
    NotImplementedError. Omni 와 동일한 활성화 절차.
    """

    def __init__(self) -> None:
        log.debug("VeoAdapter stub — 활성화 전 호출 금지 (D-27)")

    def generate_virtual_view(
        self,
        frames: np.ndarray,
        target_camera_delta: tuple[float, float, float],
    ) -> np.ndarray:
        raise NotImplementedError(
            "VeoAdapter 미구현 — Veo 3.1 Vertex Public Preview PoC 대상 (D-27). "
            "구현 전 spike 선행 필요."
        )


def get_video_gen_adapter(adapter_type: str = "omni") -> VideoGenerationAdapter | None:
    """SYNTHESIS_VIDEO_GEN_ENABLED env flag gated 팩토리 (D-31).

    truthy check (T-04-W4-01 mitigate):
      env 미설정 / "0" / 빈 문자열 → None (기본 비활성).
      env == "1" → adapter_type 분기로 stub 인스턴스 반환.
      알 수 없는 adapter_type → log.warning + None.

    pipeline 측에서는 본 함수 반환이 None 이면 video gen 경로 자체를 호출하지
    않는다 — Wave 4 시점 pipeline/app.py 는 본 함수를 호출조차 하지 않음
    (인터페이스만 박제 단계, D-31).
    """
    enabled = os.environ.get("SYNTHESIS_VIDEO_GEN_ENABLED", "0")
    if enabled != "1":
        log.debug("video gen adapter disabled (SYNTHESIS_VIDEO_GEN_ENABLED=%r)", enabled)
        return None

    if adapter_type == "omni":
        return OmniVertexAdapter()
    if adapter_type == "veo":
        return VeoAdapter()

    log.warning(
        "get_video_gen_adapter: 알 수 없는 adapter_type=%r — None 반환",
        adapter_type,
    )
    return None


__all__ = [
    "OmniVertexAdapter",
    "VeoAdapter",
    "get_video_gen_adapter",
]
