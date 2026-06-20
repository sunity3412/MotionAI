---
phase: 20-v2-gemini
plan: 01
subsystem: api
tags: [scoring, vision-veto, downward-cap, provenance, worst-pose, numpy, pytest, tdd]

# Dependency graph
requires:
  - phase: 19-vision-hybrid
    provides: v1 감점식 overall(min-of-core) + vision-hybrid hook 자리 (vision_veto 가 그 위에 terminal min cap 으로 합성)
  - phase: 08-force-signals
    provides: TechniqueProfile.key_moments(hold/peak) — worst_pose_timestamp 가 신규 Gemini 호출 0 으로 재사용
provides:
  - "apply_downward_cap(overall, severity) — 하향 전용 min() cap (D-01 invariant 코드 강제)"
  - "SEVERITY_CAP placeholder 테이블 (moderate/major=None, 20-04 eval 도출 자리)"
  - "SEVERITY_CAP_PROVENANCE(data) — curve-fit fail-closed 게이트 (sensitivity_manifest_sha256)"
  - "worst_pose_timestamp(profile) — key_moments(hold>peak>전체) 재사용, IPSF phase 평균 거부 (D-05)"
affects: [20-02-gemini-adapter, 20-03-pipeline-wiring, 20-04-derive-caps-eval]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "하향-전용 거부권: terminal min() cap 으로 비전이 점수를 올릴 수 없음을 코드가 강제"
    - "Provenance-as-data: cap 도출 출처를 주석이 아닌 module dict 로 박제 + fail-closed 단위테스트"

key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/vision_veto.py
    - backend/tests/test_vision_veto.py
  modified: []

key-decisions:
  - "SEVERITY_CAP moderate/major 는 placeholder None — 20-04 generalization eval 에서만 도출 (6페어 curve-fit 금지, D-02)"
  - "SEVERITY_CAP_PROVENANCE.sensitivity_manifest_sha256 가 실 sha 가 아닌 동안 cap 채움 금지 — 단위테스트가 fail-closed 강제 (HIGH-3)"
  - "worst_pose_timestamp 는 명시적 None 검사로 폴백 (timestamp 0.0 hold 가 falsy 로 떨어지는 버그 차단)"

patterns-established:
  - "하향-전용 invariant: apply_downward_cap 출력 ≤ 입력 항상 (property test 전수 0..100 × severity)"
  - "Provenance fail-closed: 데이터-출처 dict + cap↔sha 일관성 단위테스트로 curve-fit 경로 차단"

requirements-completed: [SCORE-08, TRUST-08]

# Metrics
duration: 14min
completed: 2026-06-20
---

# Phase 20 Plan 01: v2 비전 거부권 순수 코어 Summary

**numpy 외 의존 0 의 vision_veto.py — apply_downward_cap(하향 전용 min cap, D-01) + SEVERITY_CAP placeholder + SEVERITY_CAP_PROVENANCE(curve-fit fail-closed, HIGH-3) + worst_pose_timestamp(key_moments 재사용, D-05). 비전이 점수를 올려 위양성을 재발시키는 경로를 구조적으로 차단.**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-06-20T07:22Z (approx)
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files created:** 2

## Accomplishments
- **D-01 하향-전용 invariant 코드 강제:** `apply_downward_cap` = severity→SEVERITY_CAP lookup 후 `min(overall, cap)`. None/미지/minor → 불변. property test 가 ∀(overall 0..100 × severity) 출력 ≤ 입력을 단언 — 비전이 점수를 올리는 경로 0 (grep: `max(` 0건, `min(` 5건).
- **D-02 curve-fit 금지:** SEVERITY_CAP moderate/major = placeholder None. 실 수치는 20-04 generalization eval 에서만 도출. minor 는 영구 None(정타 95~100 무캡 보존).
- **HIGH-3 fail-closed:** `SEVERITY_CAP_PROVENANCE` = module dict(주석 아님) `{source: 'phase20_sensitivity', sensitivity_manifest_sha256: None, phase18_pairs_used_for_derivation: False}`. cap 이 채워지면 sha 도 실 sha 여야 함을 단위테스트가 강제 (현재 cap=None + sha=None 일관 → PASS). phase18 6페어는 회귀 검증 전용, derive 입력 영구 False.
- **D-05 worst-pose 재사용:** `worst_pose_timestamp` = key_moments(hold > peak > 전체) 우선순위로 단일 지배 pose 시점 선택. IPSF phase 평균 거부(Phase 19 희석 버그 재발 차단). 신규 Gemini moment 호출 0 (getattr 방어로 profile.key_moments 만 읽음).

## Task Commits

TDD 사이클 (test → feat):

1. **Task 1 (RED): 실패 테스트** - `7925988` (test) — vision_veto 미존재 → ImportError
2. **Task 1 (GREEN): 순수 코어 구현** - `f2bb1ae` (feat) — 8/8 PASS

**Plan metadata:** (this commit) (docs: complete plan)

## Files Created/Modified
- `backend/shared/python/sunity_shared/analysis/vision_veto.py` - 순수 거부권 코어: SEVERITY_CAP + SEVERITY_CAP_PROVENANCE + apply_downward_cap(min cap) + worst_pose_timestamp(key_moments 재사용). numpy 외 의존 0.
- `backend/tests/test_vision_veto.py` - 8 단위테스트: 하향-전용 property + minor-no-cap + cap-lowers-for-major + curve-fit 마커 + provenance-is-data + cap-fill-requires-real-sha(fail-closed) + worst-pose-prefers-hold + no-new-moment-call(순수 grep 가드).

## Decisions Made
- **worst_pose 폴백을 명시적 None 검사로:** 초기 구현은 `_ts("hold") or _ts("peak") or _ts(None)` 였으나, `or` 는 timestamp 0.0(영상 시작 hold)을 falsy 로 떨어뜨려 hold→peak 로 잘못 폴백한다. `for group in (...)` + `is not None` 명시 검사로 교체 (구현 중 자체 발견·수정, plan 의도 정합).
- **자기-grep 가드 docstring 워딩:** test_worst_pose_no_new_moment_call 이 소스에 `max(` 0건을 단언하므로, 모듈 docstring 의 설명용 `max()` 토큰을 "상향연산"으로 치환 (가드가 의미대로 — `max(` 호출 0 — 작동하도록).

## Deviations from Plan

None - plan 의 단일 task 를 작성된 대로 TDD(RED→GREEN)로 실행. 위 "Decisions Made" 의 두 항목은 plan 의도 범위 내 구현 디테일(0.0 falsy 버그 자체 차단 + 자기-grep 가드 정합)이며 scope 변경 아님.

## Issues Encountered

**전체 backend suite 의 pre-existing 실패 50건 (격리 — 본 plan 무관):**
- `tests/test_pipeline_geminic_wiring.py` / `test_pipeline_geminid_wiring.py` 등의 50 failed 는 본 plan 이전 커밋(5d67d94)에서도 동일하게 실패 — `git checkout 5d67d94 -- tests/` 후 `test_pipeline_geminid_wiring.py` 8 failed 재현으로 pre-existence 증명. 이들은 pipeline gemini-c/d wiring(별도 미완 기능, `_apply_vision_veto`/`augment_low_confidence` 심볼 부재)을 단언하며 vision_veto 와 결합 0 (grep: 실패 모듈 중 vision_veto 참조 0건).
- 11건의 collection error(`test_pole_detector.py` 등 smoke/spike 모듈)는 optional dep(cv2/imageio/fixtures) 부재 — 본 plan 무관, plan 의 "pre-existing 격리 제외" 정합.
- **본 plan 신규 코드(vision_veto.py)는 어느 기존 모듈에도 import 되지 않으며, vision_veto.py 자체도 numpy 외 import 0** — 결합 0, 회귀 0.

## Verification Results

- `cd backend && PYTHONPATH=shared/python python3 -m pytest tests/test_vision_veto.py -q` → **8 passed**
- 객관성 grep: vision_veto.py `max(` **0건**, heavy deps(genai/google/requests/boto3/firestore) import **0건**, `min(` 5건
- provenance fail-closed: test_cap_fill_requires_real_manifest_sha **GREEN** (cap=None + sha=None 일관)
- 회귀: 본 plan 무관 모듈의 50 failed 는 prior commit(5d67d94)에서 동일 재현 → pre-existing 격리 확인 (vision_veto 결합 0)
- Pod 무관 (전부 pod-free 단위테스트)

## User Setup Required

None - 외부 서비스 설정 불필요 (순수 알고리즘 모듈 + 단위테스트, 신규 패키지 0).

## Next Phase Readiness
- **20-02 (Gemini adapter):** severity 산출용 Gemini vision 어댑터가 apply_downward_cap 의 severity 입력을 공급할 자리 준비됨.
- **20-03 (pipeline wiring):** `_apply_vision_veto` 가 score_result['overallScore'] 위에 apply_downward_cap 을 terminal min 으로 합성 (dimensions.py:384 정합). worst_pose_timestamp 가 결함 pose 시점 제공.
- **20-04 (derive_caps eval):** SEVERITY_CAP moderate/major 를 generalization eval 에서 채우고 SEVERITY_CAP_PROVENANCE.sensitivity_manifest_sha256 을 실 sha 로 갱신해야 cap 활성 (fail-closed 가드 통과 조건). phase18_pairs_used_for_derivation 은 영구 False 유지 필수.
- **블로커:** 없음 (pod-free, 후속 plan 진입 가능).

---
*Phase: 20-v2-gemini*
*Completed: 2026-06-20*

## Self-Check: PASSED

- vision_veto.py FOUND
- test_vision_veto.py FOUND
- 20-01-SUMMARY.md FOUND
- commits 7925988 (RED test) + f2bb1ae (GREEN feat) FOUND
