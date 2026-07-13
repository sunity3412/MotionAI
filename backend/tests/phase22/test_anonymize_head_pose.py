"""포즈기반 머리 블러 순수 로직 테스트 — head_bbox_from_wholebody (quick 260713-jxr 후속).

배경: 일반 얼굴 검출기가 폴 영상(역자세·회전)에서 프레임의 ~40%만 얼굴을 잡아 얼굴이
노출됐다(2026-07-13 실측, D-12 위반). RTMW-133 얼굴 랜드마크로 머리 bbox 를 산출해
recall 을 높이는 순수 함수만 검증(rtmlib/네트워크 0 — I/O 껍데기는 Pod 전용).

불변식:
  · 유효 머리 키포인트 2개 미만 → None(호출자가 폴백).
  · 저신뢰(score<conf) 키포인트는 무시.
  · bbox 는 프레임 경계로 클립, 상단은 머리카락/이마 추가 패딩.
  · 몸통/사지 키포인트는 bbox 산출에 미포함(포즈 학습 신호 보존).
"""

from __future__ import annotations

import numpy as np

from datagen import anonymize as an


def _kps_scores(points: dict[int, tuple[float, float]], conf: float = 0.9):
    """지정 인덱스에만 좌표+신뢰를 채운 (133,2)/(133,) 배열."""
    kps = np.zeros((133, 2), dtype=np.float32)
    scores = np.zeros((133,), dtype=np.float32)
    for i, (x, y) in points.items():
        kps[i] = (x, y)
        scores[i] = conf
    return kps, scores


def test_head_bbox_from_face_landmarks():
    """얼굴 랜드마크(23~90)로 머리 bbox 산출 + 경계 클립."""
    pts = {23: (300, 300), 40: (320, 320), 60: (340, 310), 90: (330, 340)}
    kps, scores = _kps_scores(pts)
    bb = an.head_bbox_from_wholebody(kps, scores, width=640, height=720)
    assert bb is not None
    x0, y0, x1, y1 = bb
    # 랜드마크 범위(300~340,300~340)를 포함하고 관대하게 패딩.
    assert x0 < 300 and x1 > 340
    assert y0 < 300 and y1 > 340
    # 상단 추가 패딩 — y0 여백이 y1 여백보다 크다(머리카락/이마).
    assert (300 - y0) > (y1 - 340)


def test_head_bbox_clipped_to_frame():
    """프레임 밖 좌표는 [0,W]/[0,H] 로 클립."""
    pts = {0: (5, 5), 1: (10, 8), 2: (2, 6), 3: (12, 10)}
    kps, scores = _kps_scores(pts)
    bb = an.head_bbox_from_wholebody(kps, scores, width=640, height=720)
    assert bb is not None
    x0, y0, x1, y1 = bb
    assert x0 >= 0 and y0 >= 0 and x1 <= 640 and y1 <= 720


def test_head_bbox_none_when_too_few_points():
    """유효 머리 키포인트 1개(코만) → None."""
    kps, scores = _kps_scores({0: (300, 300)})
    assert an.head_bbox_from_wholebody(kps, scores, 640, 720) is None


def test_head_bbox_ignores_low_confidence():
    """score<conf 인 머리 키포인트는 무시 — 유효점 부족 시 None."""
    kps, scores = _kps_scores({0: (300, 300), 1: (310, 300)}, conf=0.1)
    assert an.head_bbox_from_wholebody(kps, scores, 640, 720, conf=0.3) is None


def test_head_bbox_ignores_body_limb_keypoints():
    """몸통/사지(5~16)만 있으면 머리 bbox None — 포즈 학습 신호 보존."""
    # 5=left_shoulder ... 16=right_ankle (머리 인덱스 아님).
    pts = {5: (200, 400), 11: (210, 500), 16: (220, 650)}
    kps, scores = _kps_scores(pts)
    assert an.head_bbox_from_wholebody(kps, scores, 640, 720) is None


def test_head_bbox_min_span_floor_for_tiny_face():
    """코+눈만 잡혀 span 이 작아도 하한(_HEAD_MIN_SPAN_FRAC)으로 최소 커버 보장."""
    pts = {0: (320, 360), 1: (322, 359), 2: (318, 359)}  # 매우 조밀.
    kps, scores = _kps_scores(pts)
    bb = an.head_bbox_from_wholebody(kps, scores, width=640, height=720)
    assert bb is not None
    x0, y0, x1, y1 = bb
    # 하한(0.06*720≈43)*pad 로 bbox 가 조밀 좌표보다 충분히 크다.
    assert (x1 - x0) > 40 and (y1 - y0) > 40
