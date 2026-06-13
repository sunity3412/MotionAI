"""Phase 4 Wave 4 — Stage 4 video gen adapter 비활성 + stub 단위 테스트 (POSE-03 D-30 D-31).

5개 테스트:
  · test_video_gen_disabled_by_default — SYNTHESIS_VIDEO_GEN_ENABLED env 없으면
    get_video_gen_adapter() is None (기본 비활성, T-04-W4-01 mitigate)
  · test_video_gen_explicitly_disabled — env="0" 시 None (truthy check)
  · test_omni_adapter_raises_not_implemented — OmniVertexAdapter.generate_virtual_view
    → NotImplementedError (D-25 Vertex GA 후 활성화)
  · test_veo_adapter_raises_not_implemented — VeoAdapter.generate_virtual_view
    → NotImplementedError (D-27 Veo 3.1 spike 선행 필요)
  · test_protocol_structural_subtyping — isinstance(adapter, VideoGenerationAdapter)
    is True (@runtime_checkable Protocol 구조적 서브타입 정합)

xfail / pytest.skip 금지 — Wave 4 박제 완료 검증 게이트.
"""

from __future__ import annotations

import pytest

from sunity_shared.analysis.synthesis.interfaces import VideoGenerationAdapter
from sunity_shared.analysis.synthesis.video_gen_adapter import (
    OmniVertexAdapter,
    VeoAdapter,
    get_video_gen_adapter,
)


def test_video_gen_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """SYNTHESIS_VIDEO_GEN_ENABLED env 미설정 → get_video_gen_adapter() is None.

    T-04-W4-01 mitigate — env flag 기본값 비활성 회귀 게이트.
    """
    monkeypatch.delenv("SYNTHESIS_VIDEO_GEN_ENABLED", raising=False)
    assert get_video_gen_adapter() is None


def test_video_gen_explicitly_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """SYNTHESIS_VIDEO_GEN_ENABLED="0" → None.

    truthy check 회귀 — "0" / 빈 문자열 / 미설정 모두 동일하게 None 이어야 한다.
    """
    monkeypatch.setenv("SYNTHESIS_VIDEO_GEN_ENABLED", "0")
    assert get_video_gen_adapter() is None


def test_omni_adapter_raises_not_implemented() -> None:
    """OmniVertexAdapter().generate_virtual_view(...) → NotImplementedError.

    D-25 Vertex GA 후 활성화 — Wave 4 시점 호출 경로 차단 게이트.
    __init__ 은 raise 하지 않아 인스턴스 생성은 성공해야 한다 (팩토리 분리).
    """
    adapter = OmniVertexAdapter()
    with pytest.raises(NotImplementedError):
        adapter.generate_virtual_view(None, (0.0, 0.0, 0.0))


def test_veo_adapter_raises_not_implemented() -> None:
    """VeoAdapter().generate_virtual_view(...) → NotImplementedError.

    D-27 Veo 3.1 Vertex Public Preview PoC 대상 — spike 선행 전 호출 경로 차단.
    """
    adapter = VeoAdapter()
    with pytest.raises(NotImplementedError):
        adapter.generate_virtual_view(None, (0.0, 0.0, 0.0))


def test_protocol_structural_subtyping() -> None:
    """OmniVertexAdapter / VeoAdapter 가 VideoGenerationAdapter Protocol 을
    구조적 서브타입 (structural subtyping) 으로 만족한다.

    @runtime_checkable Protocol — isinstance() 체크가 generate_virtual_view 메서드
    존재 여부로 판정. 향후 새 adapter 가 동일 메서드 시그니처를 제공하면
    inheritance 없이도 Protocol 호환.
    """
    assert isinstance(OmniVertexAdapter(), VideoGenerationAdapter) is True
    assert isinstance(VeoAdapter(), VideoGenerationAdapter) is True
