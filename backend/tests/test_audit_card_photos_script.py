"""audit_card_photos 스크립트의 순수 헬퍼 테스트 (quick-260905-mvm) — 네트워크·Firestore 0.

modal_token(토큰 다수결·동률 fail-closed) / split_panels(fault_zoom._compose 기하 복원) /
parse_pairs(입력 형식). 눈 호출·문서 읽기는 스크립트 실행(라이브 검증)의 몫.
"""

from __future__ import annotations

import argparse
import io

import pytest
from PIL import Image

import audit_card_photos as acp


def test_modal_token_majority_and_ties():
    assert acp.modal_token(["knee", "knee", "elbow"]) == "knee"
    assert acp.modal_token(["thigh"]) == "thigh"
    assert acp.modal_token(["knee", "elbow"]) == "unclear"           # 동률 = fail-closed
    assert acp.modal_token(["unclear", "unclear", "error"]) == "unclear"
    assert acp.modal_token(["unclear", "unclear", "hip"]) == "hip"    # 못 읽음은 표가 아니다
    assert acp.modal_token(["bent", "bent", "bent"]) == "unclear"     # 어휘 밖 = 못 읽음
    assert acp.modal_token([]) == "unclear"


def _png(w: int, h: int) -> bytes:
    img = Image.new("RGB", (w, h), (255, 255, 255))
    # 왼쪽 패널 빨강, 오른쪽 패널 파랑 — 이등분이 어느 쪽을 잘랐는지 픽셀로 확인
    left_w = h if w - 2 * h >= 0 else w // 2
    for x in range(w):
        for y in range(0, h, max(1, h // 8)):
            img.putpixel((x, y), (255, 0, 0) if x < left_w else (0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_split_panels_recovers_compose_gap():
    """_compose 형상(정사각 2 + gap 6) → 각 패널 정사각, gap 픽셀은 어느 쪽에도 안 들어간다."""
    user, ref = acp.split_panels(_png(360 * 2 + 6, 360))
    assert user.size == (360, 360) and ref.size == (360, 360)
    assert user.getpixel((359, 0)) == (255, 0, 0)
    assert ref.getpixel((0, 0)) == (0, 0, 255)


def test_split_panels_falls_back_to_halves_on_unknown_shape():
    user, ref = acp.split_panels(_png(800, 300))   # gap 200 > 상한 → 단순 이등분
    assert user.size == (400, 300) and ref.size == (400, 300)
    user, ref = acp.split_panels(_png(500, 300))   # gap 음수 → 단순 이등분
    assert user.size == (250, 300) and ref.size == (250, 300)


def test_parse_pairs_forms():
    ns = argparse.Namespace(uid="u1", analysis_id="a1", pairs="u2:a2, u3:a3,")
    assert acp.parse_pairs(ns) == [("u1", "a1"), ("u2", "a2"), ("u3", "a3")]
    with pytest.raises(SystemExit):
        acp.parse_pairs(argparse.Namespace(uid=None, analysis_id=None, pairs="bad"))
    with pytest.raises(SystemExit):
        acp.parse_pairs(argparse.Namespace(uid=None, analysis_id=None, pairs=""))
