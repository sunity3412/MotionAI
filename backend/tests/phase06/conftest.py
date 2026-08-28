"""Phase 6 단위 테스트 공통 helper. Validation Architecture 6 fixture 정합.

R5 fix 신규 fixture_high_dispersion_arms_sprawled 포함 (2026-06-08 round-2 reviews).

기존 backend/tests/conftest.py 가 parents[1]/shared/python 을 sys.path 에 자동 주입
하므로 본 파일은 별도 path 주입 X — Phase 6 fixture 디렉토리 경로 상수만 노출.
"""

from __future__ import annotations

import pytest

from pathlib import Path

# Phase 6 fixture 디렉토리 (Validation Architecture 6 fixture).
PHASE06_FIXTURES_DIR: Path = Path(__file__).resolve().parent / "fixtures"


# ── not_pole 안전 게이트 비활성 (2026-08-28) ────────────────────────────────
#
# phase06 는 `compare_body_profiles` **배선**을 보는 mock 전용 테스트다
# (모듈 docstring: "RTMW / S3 / Firestore 실 호출 0"). 합성 픽스처라 각도 유사도가
# 0 으로 나오는 것이 정상인데, 나중에 추가된 not_pole 게이트
# (`angle_dim < models.NOT_POLE_SIMILARITY_THRESHOLD` → NotPoleMotionError)가
# 그걸 "폴 동작이 아님"으로 거부해 9건이 실패하고 있었다.
#
# 게이트는 제 일을 한 것이다 — 잘못은 관심 밖 게이트를 통과할 의무가 없는 테스트가
# 그 사실을 명시하지 않은 것. 임계를 0 으로 낮춰 **이 디렉터리에서만** 비활성화한다.
# (게이트 자체의 검증은 not_pole 전용 테스트 책임 — 여기서 잠재우는 것과 무관하다.)
@pytest.fixture(autouse=True)
def _disable_not_pole_gate(monkeypatch):
    from sunity_shared import models

    monkeypatch.setattr(models, "NOT_POLE_SIMILARITY_THRESHOLD", 0, raising=False)
