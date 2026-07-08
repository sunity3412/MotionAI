---
phase: 28-dtw-motion-based-alignment
plan: 02
subsystem: motion-alignment (build_motion_alignment 순수 산출 코어)
tags: [dtw, alignment, pure-function, seconds-domain, tier-ladder, wave-2, tdd-green]
requirements: [ALGN-01, ALGN-02]
dependency_graph:
  requires:
    - "28-01 (build_motion_alignment 최종 계약 RED 테스트 + reference fps 18.0 실측 봉인)"
  provides:
    - "build_motion_alignment(match, *, user_fps, ref_fps) -> dict | None 순수 함수 (초 단위 앵커 + tier 사다리)"
    - "DISTANCE_T1/T2/RATE_MIN/RATE_MAX/ANCHOR_STEP_S/MAX_ANCHOR_FLOATS/MOTION_ALIGNMENT_VERSION 공개 상수"
    - "임계 lockstep + 순수성 AST 가드 + degenerate 방출 계약 테스트 (16 tests GREEN)"
  affects:
    - "28-04 (파이프라인 방출 — 이 함수 호출해 alignment dict 산출)"
    - "28-06 (VideoCompare 소비 — alignmentWarp.ts 가 이 dict 형상 소비)"
    - "28-03 (validator — MAX_ANCHOR_FLOATS/disabled 빈 anchors 예외 lockstep)"
tech_stack:
  added: []
  patterns:
    - "방어적 getattr 접근 (vision_veto assess_alignment_confidence 선례)"
    - "1:N median 안정화 (fault_zoom._matched_ref_frame 선례)"
    - "값 복제 + lockstep 테스트로 cross-import 회피 (순수 모듈에 Gemini 인접 의존 차단)"
    - "AST import 화이트리스트 가드 (채점 무접촉 경계 구조 강제)"
key_files:
  created:
    - backend/shared/python/sunity_shared/analysis/motion_alignment.py
  modified:
    - backend/tests/test_motion_alignment.py
decisions:
  - "distance 임계 = vision_veto._ALIGN_GLOBAL_T1/T2 값 재사용(복제) + lockstep 테스트 — cross-import 대신 값 복제로 순수성 유지 (D-03, calibration-source-hard-gate)"
  - "uSec = round(t*user_fps)/user_fps (그리드 시각 t 원값 아님) — 반올림된 프레임에서 uSec·rSec 동시 도출해 identity 기울기 1.0 보존"
  - "degenerate 3형(empty_path/invalid_fps/insufficient_anchors) = tier disabled + 빈 anchors 방출, None은 match=None만 (W3 legacy 구분)"
  - "high-distance disabled(25.1)는 anchors 유지 — 빈 anchors는 disabled에만 허용이지 disabled가 빈 anchors를 강제하지 않음"
metrics:
  duration_min: 12
  tasks_completed: 2
  files_created: 1
  files_modified: 1
  completed_date: 2026-07-08
---

# Phase 28 Plan 02: build_motion_alignment 순수 산출 코어 Summary

28-01이 고정한 계약 RED 테스트를 GREEN으로 만드는 `motion_alignment.py` 순수 모듈을 구현했다. MotionMatch를 초 단위 앵커(0.5s 그리드, flat float 쌍) + tier 사다리(warped/trim_only/disabled) + distance로 결정론적으로 변환하고, distance 임계는 vision_veto 프로덕션 상수를 재사용하며, degenerate 입력은 None이 아닌 tier disabled로 방출한다. 임계 drift·의존 오염·degenerate 형상을 3개 신규 테스트로 영구 차단했다.

## What Was Built

### Task 1 — build_motion_alignment 본체 (Wave 0 계약 GREEN)
`backend/shared/python/sunity_shared/analysis/motion_alignment.py` (순수 모듈, `from __future__ import annotations` 외 import 0). 핵심 로직:

- **초 단위 방출 (Pitfall 1 회귀 가드):** 학생초 그리드를 `match.start/user_fps` ~ `(match.end-1)/user_fps`에서 ANCHOR_STEP_S(0.5s) 간격 + 양 끝점으로 생성. 각 그리드 시각 → `abs_frame = round(t*user_fps)` → path에서 same-local ref_idx들의 **median** (fault_zoom 선례) → `rSec = median_ref/ref_fps`. **uSec은 `abs_frame/user_fps`** (그리드 원값 t가 아니라 반올림된 프레임에서 도출) — 이래야 user_fps==ref_fps identity path에서 uSec·rSec가 함께 반올림돼 기울기 1.0이 정확히 유지된다.
- **단조성 강제:** abs_frame dedup으로 u strictly increasing, r이 직전보다 작은 앵커 제거로 warp 역전 방지.
- **tier 사다리 (D-02):** `distance <= 8.0 AND 전 구간 기울기 ∈ [0.5,2.0]` → warped / `distance <= 25.0` → trim_only(reason: 기울기 위반=`rate_clamp_exceeded`, 전체 길이비 클램프 밖=`length_extreme`, 그 외=`low_global_confidence`) / else → disabled.
- **degenerate 방출 (W3):** match=None만 None. path 빈=`empty_path` / fps 비양수=`invalid_fps` / 앵커<2쌍=`insufficient_anchors` → 전부 tier `disabled` + 빈 anchors dict (None 아님 — legacy 필드 부재와 구분).
- **DoS 가드:** grid pair가 MAX_ANCHOR_FLOATS(512)/2를 넘으면 step을 정수배로 확대. 300s(2700프레임) 합성 → step 1.5s로 확대돼 앵커 512 이내.

### Task 2 — 임계 lockstep + 순수성 가드 + degenerate 계약 (기존 테스트 무수정)
`backend/tests/test_motion_alignment.py`에 4개 테스트 append (89줄 삽입, 삭제 0):
- **임계 lockstep:** `DISTANCE_T1/T2 == vision_veto._ALIGN_GLOBAL_T1/T2` 단언 (vision_veto는 테스트에서만 import). 값 복제 drift 차단 (D-03).
- **순수성 AST 가드:** `ast.parse`로 import 노드 검사 — numpy/math/typing/dataclasses/__future__ 화이트리스트 밖 import 0 강제 (T-28-04 채점 무접촉 구조 가드).
- **T2 경계 상수 참조형:** distance==DISTANCE_T2 → trim_only (25.0 하드코딩 아닌 모듈 상수로 경계 고정).
- **degenerate 방출 계약:** 앵커<2쌍·ref_fps=0 → tier disabled + 빈 anchors + reason; None은 match=None만.

## Verification

- Task 1: `pytest tests/test_motion_alignment.py -q` → 12 passed (Wave 0 계약 전부 GREEN). 금지 import grep 0, `_ALIGN_GLOBAL` 출처 주석 4회(≥1), 기존 테스트 diff 0.
- Task 2: 전체 16 passed (≥12). `ast.parse/ast.walk` grep 3(≥1). test 파일 diff = 89 insertions / 0 deletions (append-only, MEDIUM-2 churn 0).

## Deviations from Plan

None — 2 태스크 계획대로 실행. (설계 명료화 1건, 계획 무변경: uSec을 그리드 원값 t가 아닌 `round(t*user_fps)/user_fps`로 도출 — 플랜 규칙 2의 "user_sec 앵커"를 identity-slope 테스트가 요구하는 형태로 구현. rSec도 동일 프레임 기반이라 기울기 일관성 확보.)

## Notes

- **채점 무접촉:** 신규 파일 1(순수 함수) + 테스트 append만. per_joint_deviation/kismam/dimensions import 0, veto still 경로 무접촉 — 28-VALIDATION 불변 제약 정합. AST 가드로 구조적으로 영구 봉인.
- **의도된 seam (스텁 아님):** 이 함수는 아직 호출부가 없다 — 28-04(파이프라인 방출)가 소비. UI로 흐르는 빈 데이터 아니라 후속 웨이브가 배선할 순수 산출 지점.
- **lockstep 부채 명시:** DISTANCE_T1/T2는 vision_veto 값을 복제(cross-import 회피)했으므로, vision_veto._ALIGN_GLOBAL 변경 시 이 모듈도 함께 고쳐야 한다 — lockstep 테스트가 drift를 CI에서 잡는다.

## Threat Flags

None — 신규 네트워크 엔드포인트/인증/스키마 경계 0. 순수 함수 (numpy/stdlib 외 의존 0).

## Commits

- `7d22fb1` feat(28-02): build_motion_alignment 순수 모듈 — Wave 0 계약 GREEN
- `9574f17` test(28-02): 임계 lockstep + 순수성 AST 가드 + degenerate 방출 계약

## Self-Check: PASSED

- 신규 파일 motion_alignment.py + SUMMARY 존재 확인 (아래 자동 검증).
- 커밋 2개 (7d22fb1 / 9574f17) 존재 확인.
