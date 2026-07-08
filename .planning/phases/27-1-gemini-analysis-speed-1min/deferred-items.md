# Phase 27 — Deferred Items (scope 밖 발견, 회귀 아님)

> 27-09 gate sweep(2026-07-08)에서 발견된 pre-existing / 범위 밖 항목. 회귀 상태 방치 아님 — 근거는 27-TIMING-AFTER.md §2/§3.

## 1. [HIGH — gap-closure 회부] TechniqueCache hit 시 hold_window 미복원 → extension 측정 창 drift

- **증상:** cold(fresh recognizer) vs warm(TechniqueCache hit)에서 `leg_extension` measuredValue 가 달라짐 — power-spin fault 78.27°→140.9°(상한 −20 이 가려 점수 동일), power-spin success 135.84°(−20)→미발화(80→100).
- **근본 원인:** `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py:383-392` `_profile_from_cache` 가 `hold_window` 를 복원하지 않음. fresh 경로는 `:329` 에서 moments×fps 로 설정 → 캐시 hit 시 `dimensions._select_window` 자동 폴백 창으로 측정. hold_window 는 캐시 doc 에 저장도 안 됨 (fps 필요 — 복원 시 재계산 또는 저장 스키마 확장 필요).
- **pre-existing 증빙:** 함수 마지막 실질 수정 `fc3b6b7`(phase 8). phase 27 접촉은 `11d175f` 핸들 스레딩뿐. RTMW/DTW 결정론은 alignment byte-동일로 확인.
- **프로덕션 노출면:** 같은 영상 재분석(캐시 hit) 시 extension/line 계열 측정 창이 바뀜 — 분석 정확도(core value) 직결.
- **왜 지금 안 고쳤나:** 채점 표면 변경(warm-path 점수가 바뀜) → 자체 EVAL18 게이트 사이클 동반 필수. 27-09 범위(게이트 판정) 밖 + pre-existing (scope boundary 규칙).
- **fix 방향 제안:** store 시 `hold_window` 직렬화(또는 fps 동반 저장 후 복원 시 재계산) + `_profile_from_cache` 복원 1곳 + cold/warm 결정론 unit(캐시 round-trip fidelity) + EVAL18 재판정.

## 2. [관측 — 레버 후보] Pod S3 다운로드 일시 변동 (성공 멤버 4건 64.6~135.8s)

- 27-09 after cold run 한정 관측. 같은 파일이 before/warm run 에선 3.3~16.7s, 같은 run 의 fault 멤버는 전부 3.2~5.2s, 재시도/오류 로그 0 (boto3 GET 무음 대기).
- 코드 원인 아님(네트워크 변동) — TTFR 표의 pp-S +4% 역행 전액 귀속. s3 정규화 시 TTFR median 104s.
- 레버 후보(범위 밖): S3 Transfer Acceleration, boto3 재시도/타임아웃 튜닝, 다운로드 스테이지 재시도 계측 추가.
