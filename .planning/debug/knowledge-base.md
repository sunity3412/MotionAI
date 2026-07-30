# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## faultzoom-same-frame-crops — 확대비교 크롭이 전 관절 동일 프레임에서 잘리고 기준 패널이 엉뚱한 순간을 보여줌
- **Date:** 2026-07-28
- **Error patterns:** faultZoomComparisons, userFrameIdx 동일, 확대비교 크롭, 같은 프레임, 기준 패널 다른 장면, DTW 정렬, pose match, ref 타임베이스, sourceFrameIndices, keypoint 환각, 역립, facing 불일치, fault_zoom, 크롭 마커
- **Root cause:** 5겹 누적 — ① worst-pose window 를 단일 프레임으로 뭉개 전 crop unit 재사용 ② 학생/기준 프레임 독립 선택으로 카드 내 DTW 짝 붕괴 ③ DTW 타이밍 정렬이 시각 포즈(국면·facing)를 보장 못함 + 탐색창 ±2프레임 구조적 부족 ④ ref keypointReport ↔ 렌더 비디오 배열 타임베이스 4/3 불일치(모든 ref 패널이 ≈2.7s 이른 순간 표시) ⑤ 역립 구간 keypoint 환각(무릎→머리, conf 0.68~0.70)이 단일프레임 conf argmax / pose 거리 신호를 기만. 잔여 facing ~20°(같은 반회전 내 토르소 회전)는 8관절 2D 기하의 원리적 한계 → belle 결정 A(Ochy 탭-상세 글결합으로 흡수)
- **Fix:** per-unit 프레임 선택 → DTW position-lock → pose-match(기저 고정, 저관절 허위승리 차단) → ref 타임베이스 선형 매핑 + conf 가중 게이트 → pair-opt ±2 궤적 평균(환각 flicker 자연 강등, 창 ±4s) → 각도 배지 제거·학생 패널만 초 표기. 커밋 체인 149b770→ea55069→191c296→95ee80f→4cb272a→e8613e8→79221f0→27635ce. 전부 표시 전용, 채점 무접촉(SCORE 60 D-20 6연속 불변)
- **Files changed:** backend/shared/python/sunity_shared/analysis/fault_zoom.py, backend/functions/pipeline/app.py, backend/tests/test_fault_zoom.py, backend/tests/test_fault_zoom_relaxed_crop.py
---

## voice-cue-resume-ref-desync — 음성 큐 종료 후 자동 재개 실패(F-1) + 큐 정지 중 기준(right) 영상 계속 재생(F-2)
- **Date:** 2026-07-30
- **Error patterns:** 음성 큐, 자동 재개 실패, 영구 정지, 기준 영상 계속 재생, right 만 재생, VideoCompare, tick, stale, leftPlaying, shouldPauseAtEnd, voicePauseRef, CUE_PAUSE_MAX_MS, overMax 미발화, drift-sync, follow 홀드해제, mid-tick pause, expo-video, 잠시 멈춤 pill, 재생 버튼 paused 복귀
- **Root cause:** VideoCompare.tsx tick 의 intra-tick stale 재생상태 — tick 시작 시 캡처한 leftPlaying/bothPlaying/cR 로컬을 mid-tick 상태 변이(큐 both-pause / 재개 both-play) 이후 블록이 그대로 소비. (F-2) 큐 시작 tick 에서 follow 홀드해제 분기가 stale leftPlaying=true 로 진입해 방금 pause 된 right 를 즉시 play() 부활 → 음성 정지 중 native end 까지 주행. (F-1) 음성 종료 tick 에서 재개 play() 직후 같은 tick 의 shouldPauseAtEnd 가 stale cR(=dR, F-2 산물)로 either-own-end=true → 재개 즉시 삼킴. voicePauseRef 이미 false 라 overMax(15s) 안전망 영구 미도달.
- **Fix:** tick 에 조기 종료(return) 2곳 — (1) 큐 pause 상태 진입 직후, (2) 자동 재개 play() 직후. mid-tick 플레이어 상태 변이 후에는 다음 tick(100ms)이 신선한 상태로 판정 (drift 보정 1 tick 지연 무해). 커밋 6adbfe4. 교훈: setInterval tick 이 플레이어 상태를 변이시키면 그 tick 의 후단 블록은 stale 캡처 로컬을 소비한다 — 변이 즉시 return.
- **Files changed:** app/src/components/VideoCompare.tsx
---
