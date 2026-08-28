---
quick_id: 260828-rtm
slug: opencv-5-0
description: 폴 검출기 OpenCV 5.0 호환 수리
date: 2026-08-28
status: planned
---

# 폴 검출기 OpenCV 5.0 호환 수리

## 문제 (실측)

`cv2.HoughLinesP` 반환 형태가 **OpenCV 5.0 에서 `(N,1,4)` → `(N,4)` 로 바뀌었다.**
`detector.py` 는 `(N,1,4)` 를 가정하고 `x1, y1, x2, y2 = line[0]` 로 언팩하므로
5.0 에서는 `line[0]` 이 스칼라라 `TypeError: cannot unpack non-iterable numpy.int32`.

```
로컬 재현 (opencv 5.0.0):
  lines.shape = (2, 4)          # 4.x 였다면 (2, 1, 4)
  type(line[0][0]) = int32
기존 테스트 4건이 이미 이 오류로 실패 중 (레드 확보):
  test_detect_vertical_pole_returns_detected · test_detect_tilted_pole_fallback
  test_video_level_single_axis · test_pole_axis_returns_unit_vector
```

**운영 영향**: 08-28 서빙 Pod 실분석 로그에서 매 프레임 발생 → `vertical_fallback`
으로 degrade. 폴 축은 수직으로 가정되어 대충 맞지만 **폴의 x 위치
(`midpoints_x_norm`)가 통째로 유실**된다. 이건 belle 이 08-17 판독에서 지목한
"몸통-폴 거리" 축과 "엘보 = 폴 근접도"의 입력이다. 즉 조용한 채점 열화다.

## 수리 대상

`backend/shared/python/sunity_shared/analysis/pole/detector.py` 두 곳 — 166, 300.
리포 전체에서 `HoughLinesP` 사용처는 이 파일뿐(확인 완료).

## Task 1 — 반환 형태 정규화

`lines` 를 순회 전에 `(N,4)` 로 정규화해 두 형태를 모두 수용한다.
`np.asarray(lines).reshape(-1, 4)` — `(N,1,4)` 도 `(N,4)` 도 같은 결과.

- files: `shared/python/sunity_shared/analysis/pole/detector.py`
- verify: `PYTHONPATH=tests .venv/bin/python -m pytest tests/test_pole_detector.py -q`
- done: 기존 4 failed → 0 failed

## Task 2 — 두 형태를 모두 먹이는 회귀 테스트

cv2 버전에 의존하지 않고 **두 반환 형태를 직접 주입**하는 테스트를 추가한다.
(로컬이 5.0 이라 4.x 경로는 실물로 못 밟는다 — monkeypatch 로 박제)

- files: `backend/tests/test_pole_detector.py`
- verify: 같은 pytest
- done: `(N,1,4)`/`(N,4)` 두 케이스 모두 동일한 검출 결과

## must_haves

- truths: OpenCV 4.x·5.x 양쪽 반환 형태에서 폴 검출이 동작한다
- artifacts: detector.py 정규화 1줄 × 2곳, 회귀 테스트 1개
- key_links: `shared/python/sunity_shared/analysis/pole/detector.py`, `tests/test_pole_detector.py`

## 범위 밖 (건드리지 않음)

- 검출 알고리즘·임계값 튜닝 (호환성 수리만)
- `visionVeto: skipped_error`, mode3 단일 차원 — 별건 결함, 각각 따로
