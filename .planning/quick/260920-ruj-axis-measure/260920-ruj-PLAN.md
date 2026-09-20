---
id: 260920-ruj
title: 학생 영상 도착 즉시 재는 측정 스크립트를 리포에 박제
date: 2026-09-20
status: planned
---

# 260920-ruj — 측정 장비를 scratchpad 에서 리포로

## 왜

2026-09-20 의 조사(§14~§17)는 전부 세션 scratchpad 에서 돌았고 그 판은 휘발한다.
그런데 그 판정의 절반이 **"학생 영상으로는 미측정"** 에서 멈춰 있다. belle 이 학생 영상을
요청해 두었으므로, 도착하는 순간 **같은 잣대로** 재야 비교가 된다.

## 태스크

- T1 `backend/scripts/measure_reference_axis.py` — 분석 doc 을 읽어 편차/바닥대비/여유/
  매칭/EXTEND 채점 결과를 한 표로. 운영 함수 호출만(재구현 0), 읽기 전용,
  전수 스캔 차단(--uid 또는 --ids 필수).
- T2 `backend/scripts/reference_axis_floors.json` — 정은지 자기비교 바닥(현재 판) 동봉.
- T3 스모크 — 오늘 Pod 분석으로 실제로 돌려 운영 수치와 일치 확인.

## must_haves

- truths: 스크립트가 운영과 **같은 출처**(criteria yaml)에서 EXTEND 를 뽑는다
- artifacts: 스크립트 · 바닥 JSON · SUMMARY
