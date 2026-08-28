---
quick_id: 260828-rtm
slug: opencv-5-0
description: 폴 검출기 OpenCV 5.0 호환 수리
date: 2026-08-28
status: complete
commits:
  - 6765ad93 fix(pole) HoughLinesP 반환 형태 OpenCV 5.0 호환
  - 82d23333 test(pole) OpenCV 4.x/5.0 반환 형태 회귀 테스트
---

# 260828-rtm — 폴 검출기 OpenCV 5.0 호환 수리 (완료)

## 무엇이 문제였나

`cv2.HoughLinesP` 반환 형태가 **4.x `(N,1,4)` → 5.0 `(N,4)`** 로 바뀌었다.
`detector.py` 는 4.x 를 가정해 `x1, y1, x2, y2 = line[0]` 로 언팩했고, 5.0 에서는
`line[0]` 이 스칼라라 `TypeError: cannot unpack non-iterable numpy.int32`.

**발견 경위**: 08-28 실분석 복구 후 E2E 검증 중 서빙 Pod 로그에서 관측.
치명적 예외가 아니라 `vertical_fallback` 으로 degrade 하고 있어서 **분석은 "성공"으로
끝났다** — 조용한 열화였다.

**왜 중요한가 (내 해석)**: 폴백은 폴 축을 수직으로 가정해 축 자체는 대충 맞지만,
**폴의 x 위치(`midpoints_x_norm`)가 통째로 유실**된다. 이건 belle 이 08-17 판독에서
지목한 **"몸통-폴 거리"** 축과 **"엘보 = 폴 근접도"** 의 입력이다. 즉 belle 이 직접
지목한 채점 축이 조용히 죽어 있었다.

## 수리

`_hough_segments()` 헬퍼로 `(N,4)` 정규화 — 두 형태 모두 수용. 호출부 2곳(166/300).
리포 전체에서 `HoughLinesP` 사용처는 이 파일뿐(확인 완료).

## 검증 (실측)

```
수리 전: tests/test_pole_detector.py  4 failed / 4 passed   ← 기존 테스트가 이미 잡고 있었다
수리 후: tests/test_pole_detector.py  11 passed (신규 3 포함)
백엔드 전체: 4216 passed / 62 failed / 20 skipped
            → 실패 수는 수리 전과 동일(62). 신규 회귀 0.
로컬 opencv 5.0.0 으로 재현·검증. (N,1,4) 경로는 monkeypatch 로 박제.
```

## 정직한 한계

- **로컬 검증만이다.** 서빙 Pod 에서 실제로 폴이 검출되는지(그리고 `midpoints_x_norm`
  이 채점에 반영되는지)는 **다음 Pod 가동 때 확인해야 한다.** 이번엔 잔액 $4.66 이라
  Pod 을 다시 띄우지 않았다.
- 검출 알고리즘·임계값은 손대지 않았다. 호환성 수리뿐이다.
- 백엔드 전체 62 failed 는 수리 전부터 있던 것으로, 이 작업 범위 밖이다
  (메모리 기준선 59 failed 대비 +3 — 별도 확인 필요).

## 남은 결함 (별건)

- `visionVeto: skipped_error` — Gemini 비전 거부권 미실행. 진단에 Pod 필요.
- mode3 `dimensionScores` 가 `{stability}` 1개뿐 — plan.md 가 2026-05-29 에 적은
  "overall 이 차원 1개에 휘둘림"이 그대로.
- 기준 모션 11개 `videoUrl` 전부 만료 (S3 presigned 7일). GPU 불필요·무료.
