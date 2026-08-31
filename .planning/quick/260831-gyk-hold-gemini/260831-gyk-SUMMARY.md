---
phase: quick-260831-gyk-hold-gemini
plan: 01
subsystem: analysis-scoring
tags: [dimensions, select-window, gemini-phase-hint, false-positive]
requires: []
provides:
  - "_select_window 힌트-창-내부 안정 부창 재선택 (Gemini 국면 창 = 힌트 강등)"
affects: [leg_extension, line_score, stability, safety_flags, hold_window_median]
tech-stack:
  added: []
  patterns: ["기존 hold_window 분산-최소 로직 재사용 — 새 튜닝 상수 0, 동작명 분기 0"]
key-files:
  created:
    - .planning/quick/260831-gyk-hold-gemini/verify_hold_subwindow.py
    - .planning/quick/260831-gyk-hold-gemini/VERIFY.md
  modified:
    - backend/shared/python/sunity_shared/analysis/dimensions.py
    - backend/tests/test_dimensions.py
    - backend/tests/test_record_measured_at.py
decisions:
  - "Gemini 국면 창을 국면 힌트로 강등 — profile.hold_window 내부에서 분산-최소 부창 재선택 (belle 08-31 파워스핀 위양성 판정)"
  - "gemini_technique_recognizer fps 9.0 리터럴 수정은 명시적 보류 — 검증 귀속을 단일 변경에 묶기 위함"
metrics:
  duration: "약 11분"
  completed: "2026-08-31"
---

# Quick 260831-gyk: Gemini 국면 창 힌트 강등 — 파워스핀 정타 위양성 수리 Summary

`_select_window` 가 Gemini 국면 창(hold ±2초)을 verbatim 쓰지 않고 창 내부에서
기존 hold_window(분산 최소) 로직으로 안정 부창을 재선택 — 파워스핀 정타의
leg_extension -20 위양성 + line micro-bent 0점이 실데이터에서 소멸 (135.81° →
173.40°, deficit 44.19 → 8.07).

## 실행 결과

### Task 1 — `_select_window` 수정 + 테스트 정합 (TDD)

- RED `74d2c977`: 신규 테스트 4종 (전환부 오염 차단 / 포함 불변식 / WR-05 폴백 /
  profile 부재 무변경). Test 1 이 현행 verbatim 사용에서 실패 확인.
- GREEN `51ccbcef`: `dimensions.py::_select_window` 한 함수만 수정 — clamp 후
  s < e 이면 `ss, se = hold_window(a[s:e])` 로 부창 재선택, `(s+ss, s+se)` 반환.
  부창 폭 = 기존 규칙 w = max(2, min(t', t'//4)) 그대로 (**새 튜닝 상수 0, 동작명
  분기 0**). WR-05(s==e → 전체 자동 폴백)·profile 부재 경로 무변경.
- 소비처 드리프트 확인 (수정 아님): `profile.hold_window` 를 창 선택에 읽는 곳은
  `_select_window` L316 하나뿐 (grep 재확인 — gemini_technique_recognizer 는 창
  생산자). line/stability/extension/safety_flags/pipeline._hold_window_median_dict
  전부 `_select_window` 경유 → 함수 1개 수정으로 일관 적용.
- 전체 스위트: **4532 passed / 0 failed / 20 skipped** (기준선 4528 + 신규 4).
  phase10 safety_flags·assemble_dimension_explanation·p1_objective 파급 실패 0.

### Task 2 — 실데이터 사전 박제 검증 (`07df0c4f`)

VERIFY.md 예측 블록을 **스크립트 실행 전** 박제 → 실행 → 출력 원문 측정 블록 추가
(예측 블록 수정 0). **예측 4건 전부 PASS**:

| # | 예측 | 실측 |
|---|------|------|
| 1 | 기질 동일성: verbatim 평균 = record measuredValue 135.81 | 135.81 vs 135.81 (diff 0.0036) PASS |
| 2 | 부창이 홀드 구간(약 68 이후)으로 이동 | (54,90) → (80,89) |
| 3 | correct: rk 평균 >= 170, deficit < 20, micro-bent 미발화 | 173.40 / 8.07 / False → line_score 93 (종전 0) PASS |
| 4 | 방향 보존: fault 홀드 무릎 평균 < correct | 158.35 < 173.40 PASS |

- 힌트 창 도출: 양쪽 doc 모두 gemini 캐시 필드에 hold moments 미저장 → correct 는
  예측 블록 규칙대로 역산 확정치 (54,90) 사용 (verbatim 평균이 record measuredValue
  와 일치해 실제 감점 창이었음이 교차 확인됨). fault 는 자동 hold_window 경로
  (동일 규칙 명기).
- fault 는 자동 창에서도 deficit 39.05 + micro-bent 발화 유지 — 수리가 fault 를
  무결점으로 만들지 않음 (fault < correct 방향 보존).
- 스크립트는 Firestore get 만 사용 (쓰기 0 — T-gyk-02), 가명 식별자만 출력
  (T-gyk-01), 신규 패키지 설치 0 (T-gyk-SC).

## 바뀐 테스트 목록 + 케이스별 정당화 (전부 주석 동반)

| 테스트 | 종전 | 신규 | 정당화 |
|--------|------|------|--------|
| test_dimensions.py::test_select_window_uses_profile_when_set | (s,e)==(5,15) 정확 일치 | 포함 불변식 5<=s'<e'<=15 + 부창 폭 w=2 + 결정론 (5,7) | profile 창은 이제 국면 힌트 상한이지 창 그 자체가 아님 (이 수리의 정의 변경) |
| test_dimensions.py::test_helpers_share_window_with_score_functions | shape==10 | shape==2 (부창 폭) | 의도(점수 함수들과 창 공유, drift 0)는 그대로 성립 — shape 단언만 새 의미 |
| test_record_measured_at.py::test_leg_extension_moment_follows_the_winning_joint | hold_window=(2,5) verbatim fixture | 힌트 (2,14) 전환부+홀드 fixture, 부창 (10,13) 결정론 안착 | 종전 fixture 는 전환부형 변동만 담아 부창 재선택 시 동점 타이브레이크. 의도(집계 최근접, argmax 아님, 창 포함)·수치(120/140/160→40→중간 프레임) 보존, 프레임 번호만 이동 |
| test_record_measured_at.py::test_extension_moment_is_not_the_worst_frame | 상동 | 상동 (argmax 유혹 프레임 10 배제) | 상동 |
| test_record_measured_at.py::test_line_moment_uses_the_contributing_joint_set_mean | 상동 (동점 타이브레이크로만 통과 — fragile) | 유일 최근접 프레임 11 명시 단언 추가 | 상동 + 타이브레이크 의존 제거 |

각 테스트에 `_select_window` 부창 안착 전제 확인 assert 추가 (fixture 자기 문서화).

## Deviations from Plan

None - plan executed exactly as written. (test_line_moment 는 수리 후에도 동점
타이브레이크로 우연히 통과했으나, 플랜이 "hold_window=(2,5) 3건" fixture 조정을
지시했으므로 3건 모두 조정 — fragile 통과를 결정론으로 교체.)

## 명시적 보류 (플랜 스코프 밖 — 후속 후보)

- **`gemini_technique_recognizer._hold_window_from_moments` 의 fps 9.0 리터럴**:
  실효 fps 인자 배관(_pipeline_frame_fps 경로)이 필요해 스코프가 넓어지며 검증
  귀속을 흐림 — 이번 수리 효과를 단일 변경에 귀속시키기 위해 보류. 안정 부창
  재선택이 fps 오차를 완충함 (memory fps-label-vs-actual 계열 함정 박제됨).

## Commits

| Task | Commit | 내용 |
|------|--------|------|
| 1 (RED) | 74d2c977 | test: 힌트-창-내부 부창 재선택 실패 테스트 4종 |
| 1 (GREEN) | 51ccbcef | fix: _select_window 부창 재선택 + 기존 테스트 5건 정합 |
| 2 | 07df0c4f | chore: verify_hold_subwindow.py Firestore 실데이터 재현 스크립트 |

## Known Stubs

None.

## Threat Flags

None — 신규 표면 0 (기존 admin SA 읽기 전용 재사용, 신규 권한/설치/네트워크 0).

## Self-Check: PASSED
