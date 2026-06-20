---
phase: 20-v2-gemini
plan: 03
subsystem: api
tags: [scoring, vision-veto, gemini, downward-cap, score-suppression, contract-lockstep, mode3, pytest, tdd]

# Dependency graph
requires:
  - phase: 20-v2-gemini (20-01)
    provides: apply_downward_cap(하향 전용 min cap) + SEVERITY_CAP placeholder + worst_pose_timestamp
  - phase: 20-v2-gemini (20-02)
    provides: assess_fault_severity → VisionVerdict | None (severity enum, 토글 미소유 adapter)
  - phase: 19-vision-hybrid
    provides: _apply_vision_veto identity hook 자리 + Mode3 scoringBasis + branch-3 라벨
provides:
  - "_gemini_vision_veto_enabled() 토글 (pipeline 단독 소유) + keep_local_video 게이트 확장(HIGH-1)"
  - "_apply_vision_veto 하향-전용 mutation 본체 (apply_downward_cap + visionVeto status enum audit + graceful)"
  - "_score_suppression_reason resolver (category PROVENANCE — low_confidence unheld collapse 차단)"
  - "_apply_score_suppression (scoreSuppressed/reason emit + reason-owns-copy + producer-contract fail-loud + A2 structured audit)"
  - "visionVeto/scoreSuppressed/scoreSuppressedReason/scoreSuppressionAudit 3-way 계약 lockstep"
  - "result.tsx 점수카드 전체 억제 UX + assert-result-score-suppression.mjs (cwd-stable + self-test)"
affects: [20-04-derive-caps-eval]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "토글 pipeline 단독 소유: feature-toggle 게이트가 _apply_vision_veto 1곳 (어댑터 복제 0, drift 차단)"
    - "status enum audit: visionVeto.status 가 veto 실행을 명시 증명 (부재 ≠ 실행)"
    - "resolver provenance: recognizer category 가 suppression reason 의 단일 진실 (safe-default ≠ unheld 증거)"
    - "producer-contract fail-loud: reference_free_absolute↔scoreSuppressed, suppressed↔reason 누락 = 명시 assert"
    - "reason-owns-copy: suppression reason 이 헤더 + scoringBasisLabel 둘 다 소유 (두 번째 UI 필드 leak 차단)"
    - "pod-free 정적 .mjs 억제 단언: RN test 스택 미도입, cwd-stable + self-test 로 false-green/red 차단"

key-files:
  created:
    - app/scripts/assert-result-score-suppression.mjs
  modified:
    - backend/functions/pipeline/app.py
    - backend/tests/test_pipeline_mode3.py
    - backend/tests/test_pipeline_vision_gate.py
    - app/src/types/analysis.ts
    - backend/shared/python/sunity_shared/models.py
    - docs/contract.md
    - app/src/app/analysis/result.tsx

key-decisions:
  - "cap-mutation 경로는 monkeypatch SEVERITY_CAP['major']=50 으로 pod-free 증명 — production cap=None 무손상(D-02, 20-04 까지 placeholder)"
  - "low_confidence resolver provenance 우선 — motion_id=None→_SAFE_DEFAULT_BRANCH(is_reference_free True)여도 unheld 로 collapse 안 됨(iter4 HIGH-1)"
  - "isScoreSuppressed = STRICTLY result.scoreSuppressed===true (scoringBasis 폴백 0, iter3 HIGH-2)"
  - "A2 reconcile = 단일 structured 필드 scoreSuppressionAudit (log.warning 대안 폐기, iter5 MEDIUM-2)"
  - "앱 test runner 부재 → pod-free 정적 .mjs 단언 (Jest/RN 스택 mid-phase 미도입, iter3 HIGH-1)"

patterns-established:
  - "하향-전용 거부권 통합: terminal min cap 만(올림 0, 평균 0) + 단일 호출부 mode 분기 밖 = Mode1+Mode3 자동"
  - "discriminated suppression: scoreSuppressed=true → reason REQUIRED (tsc + producer-contract 양면 강제)"

requirements-completed: [SCORE-08, TRUST-06, TRUST-07, TRUST-08]

# Metrics
duration: 38min
completed: 2026-06-20
---

# Phase 20 Plan 03: Wave 2 pipeline 통합 (비전 거부권 + Mode3 억제 + 3-way 계약) Summary

**20-01 순수 cap 코어 + 20-02 Gemini 어댑터를 채점 path 에 통합 — _apply_vision_veto 를 하향-전용 mutation 으로 swap(올림 0, 평균 0, Mode1+Mode3 단일 호출부) + visionVeto status enum audit + Mode3 미보유/저신뢰 점수카드 전체 억제(resolver provenance + reason-owns-copy + producer-contract fail-loud + 단일 structured reconcile audit). 전부 pod-free: adapter mocked, cap monkeypatch, 억제 cwd-stable 정적 .mjs. 위양성을 채점 path 에서 죽이되 v1 정타는 안 건드리고, 미보유 confident 97 을 점수카드 통째로 억제해 신뢰 회복.**

## Performance

- **Duration:** ~38 min
- **Tasks:** 3 (Task 1 TDD RED→GREEN, Task 2/3 auto)
- **Files created:** 1
- **Files modified:** 7

## Accomplishments

### Task 1 — 토글 pipeline 소유 + keep_local_video 게이트 + _apply_vision_veto 본체 swap
- **iter2 MEDIUM-1:** `_gemini_vision_veto_enabled()` 를 pipeline(app.py) 단독 정의. 어댑터(gemini_vision_scorer) 정의 0 — `_apply_vision_veto` 가 유일 feature-toggle 게이트(toggle drift no-op 차단).
- **HIGH-1:** keep_local_video 게이트를 `_gemini_enabled() or _gemini_vision_enabled() or _gemini_vision_veto_enabled()` 로 확장 — Phase17 vision OFF + veto ON 이어도 local_video_path 보존(veto None 무음 no-op 차단). adapter 가 non-None path 수신 단언.
- **SCORE-08 (D-01/03/04/05):** `_apply_vision_veto(score_result, local_video_path, angles, profile)` = worst_pose_timestamp(profile) → assess_fault_severity → apply_downward_cap → `capped < overall` 시에만 하향. 단일 호출부(mode 분기 밖) → Mode1+Mode3 자동. 올림 0(grep `max(`/블렌드 0), 평균 0(terminal cap만).
- **iter2 HIGH-1:** cap-mutation 경로를 `monkeypatch.setitem(vision_veto.SEVERITY_CAP, "major", 50)` scoped fixture 로 증명(severity=major+overall=100 → 50). production cap=None(monkeypatch 없음) + major → 불변 + not_applicable 도 별도 단언(D-02 무손상).
- **TRUST-08 (status enum):** visionVeto.status ∈ {applied, not_applicable, disabled, skipped_error, missing_local_video} 직렬화 — 부재 ≠ 실행. adapter None → graceful 통과 + WARNING + skipped_error(Pitfall 5). 객관성: score/점수 필드 0.
- 기존 `test_vision_hook_passthrough`(out is score_result identity) → 10 mocked downward/status/keep_local 테스트로 정당 전환.

### Task 2 — 3-way 계약 lockstep
- `app/src/types/analysis.ts`: VisionVeto discriminated union(status='applied'→capApplied 컴파일-타임 강제) + ScoreSuppression discriminated type(scoreSuppressed=true→scoreSuppressedReason REQUIRED, false/부재→never) + ScoreSuppressionAudit. AnalysisResult = ScoreSuppression & {...} 합성.
- `models.py`: VISION_VETO_STATUSES/VISION_VETO_KEYS + SCORE_SUPPRESSED_REASONS(unheld | recognition_low_confidence) + SCORE_SUPPRESSION_AUDIT_KEYS + producer-contract 불변식 주석.
- `docs/contract.md §4`: visionVeto/scoreSuppressed/scoreSuppressedReason/scoreSuppressionAudit 정의 + enum + 불변식 + Firestore flat 정합. result-level 위치 채택.

### Task 3 — Mode3 억제 + resolver + UX + 정적 단언
- **iter4 HIGH-1:** `_score_suppression_reason(profile, branch_info)` resolver = category PROVENANCE 우선순위(low_confidence→recognition_low_confidence, unregistered/concrete-unheld→unheld). _SAFE_DEFAULT_BRANCH(motion_id=None 유래)를 low_confidence 일 때 unheld 증거로 쓰지 않음. `test_resolver_low_confidence_not_unheld` 회귀 박제.
- **iter2 HIGH-3 / iter3 MEDIUM-1:** `_apply_score_suppression` 가 scoreSuppressed=True + scoreSuppressedReason emit(명시 플래그, scoringBasis 단독 아님). low_confidence 분리.
- **iter5 HIGH-2 (reason-owns-copy):** recognition_low_confidence 면 scoringBasisLabel 을 reference-free '기준 동작 없음'이 아닌 '신뢰도 낮음' 라벨로 override. `test_low_confidence_scoring_basis_label_not_unheld` 가 leak 부재 강제.
- **iter5 MEDIUM-2:** A2 불일치를 정확히 하나의 structured 필드 `scoreSuppressionAudit {recognizerCategory, branchReferenceFree, resolvedReason}` 로 보고(log 대안 폐기). raise 0.
- **iter3 HIGH-2 / iter4 MEDIUM-1 (fail-loud):** reference_free_absolute↔scoreSuppressed 누락 + suppressed↔reason 누락 = 명시 assert(producer-contract FAILURE).
- **TRUST-06 (C-1/D-06):** recognizer 캐시 hit(Gemini 0) → 같은 category → run 간 line 차원 변동 0(mocked, pod-free).
- **result.tsx (iter2 HIGH-2 / iter3 HIGH-2):** isScoreSuppressed = STRICTLY scoreSuppressed===true → 점수카드 전체('기준 없음' state) 대체(OctagonScore + gradeBadge + summary + LevelBenchmark + scoreCaption + 헤더 카피). reason별 헤더 카피.
- **assert-result-score-suppression.mjs (iter3 HIGH-1 / iter4 MEDIUM-2 / iter5 HIGH-2):** cwd-stable(import.meta.url) + --self-test(guarded PASS / unguarded octagon FAIL / unguarded header FAIL / low-conf reason-leak FAIL) + 점수카드 5요소 균형-괄호 else-branch 단언 + 헤더 라인-윈도우 가드 + reason-leak 가드.

## Task Commits

1. **Task 1** — `bf39e9e` (feat) — _apply_vision_veto 하향-전용 전환 + 토글 pipeline 소유 (10 mocked GREEN)
2. **Task 2** — `f79f42a` (feat) — visionVeto + ScoreSuppression + scoreSuppressionAudit 3-way lockstep (tsc clean)
3. **Task 3** — `c09dd49` (feat) — Mode3 점수카드 전체 억제 + resolver + reason-owns-copy + .mjs (12 backend GREEN, mjs/tsc clean)
4. **Deviation (Rule 1)** — `76c19f4` (fix) — keep_local_video grep 회귀 테스트를 veto 토글 추가에 정합

**Plan metadata:** (this commit) (docs: complete plan)

## Files Created/Modified

- `backend/functions/pipeline/app.py` — `_gemini_vision_veto_enabled` 토글 + keep_local_video 게이트 확장 + `_veto_passthrough`/`_apply_vision_veto` 하향-전용 본체 + `_score_suppression_reason` resolver + `_apply_score_suppression` + MODE_SELF wiring + 호출부 profile 인자.
- `backend/tests/test_pipeline_mode3.py` — Task 1 10 + Task 3 12 mocked 테스트 (vision_veto/keep_local/toggle/resolver/branch3/reconcile/missing-flag/missing-reason/low_confidence/basis_label/determinism).
- `backend/tests/test_pipeline_vision_gate.py` — 게이트 grep 회귀 테스트를 3 토글 OR 토큰 단위로 갱신 (Rule 1).
- `app/src/types/analysis.ts` — VisionVeto/ScoreSuppression/ScoreSuppressionAudit + AnalysisResult 합성.
- `backend/shared/python/sunity_shared/models.py` — VISION_VETO_* + SCORE_SUPPRESSED_REASONS + SCORE_SUPPRESSION_AUDIT_KEYS + 불변식 주석.
- `docs/contract.md` — §4 visionVeto/scoreSuppressed/scoreSuppressedReason/scoreSuppressionAudit 정의.
- `app/src/app/analysis/result.tsx` — isScoreSuppressed 점수카드 전체 억제 + reason별 카피 + suppressed state 스타일(토큰만).
- `app/scripts/assert-result-score-suppression.mjs` — cwd-stable + self-test 정적 억제 단언 (신규).

## Decisions Made

- **mjs 가드를 positional → structural 로 재설계:** 초기 "token 이 first ternary 이후 등장" 휴리스틱이 (1) import 라인 오탐(`OctagonScore`), (2) 헤더 삼항이 점수카드 삼항보다 먼저 등장하는 구조에서 false-positive 발생. 균형-괄호 스캐너로 점수카드 else-branch 를 추출해 5요소가 else 안에만 존재하는지 + 헤더 카피는 라인-윈도우(±2줄)에 `isScoreSuppressed ?/&&` 가드가 있는지로 교체. self-test 4 fixture 가 검사 함수 자체를 증명.
- **suppression 을 build_result 직후 result dict 에 주입:** `_apply_score_suppression` 를 `_apply_vision_veto` 다음, `mode == MODE_SELF` 게이트 안에서 호출(Mode1 미적용). comparison.scoringBasisLabel override 도 같은 result dict 의 comparison 을 직접 갱신(별도 build 경로 0).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] keep_local_video grep 회귀 테스트 정합**
- **Found during:** Task 1 (full suite 회귀 확인)
- **Issue:** `test_pipeline_vision_gate.py::test_gate_line_present_in_source` 가 정확 문자열 `_gemini_enabled() or _gemini_vision_enabled()` 를 단언하는데, Task 1 의 HIGH-1 게이트가 `_gemini_vision_veto_enabled()` 추가 + multi-line 포맷으로 의도적으로 바뀜 → NEW 실패 1건.
- **Fix:** 단일 정확 문자열 단언을 3 토글 OR 토큰 단위(`_gemini_enabled()` / `_gemini_vision_enabled()` / `_gemini_vision_veto_enabled()` 각각 존재)로 전환. 게이트 변경이 plan 의도이므로 정당한 테스트 전환.
- **Files modified:** backend/tests/test_pipeline_vision_gate.py
- **Commit:** 76c19f4

이 외 plan 의도 범위 내 구현 디테일(mjs structural 재설계, suppression 주입 위치)은 위 "Decisions Made" 참조 — scope 변경 아님.

## Issues Encountered

**전체 backend suite 의 pre-existing 실패 ~50건 (격리 — 본 plan 무관):**
- `tests/pipeline/test_pipeline_phase8.py`(11) / `test_pipeline_geminid_wiring.py`(8) / `test_pipeline_geminic_wiring.py`(6) / `test_pipeline_phase9.py`(5) 등 + `test_gemini_technique_recognizer.py`의 2건(`test_default_model_is_gemini_3_1_pro` / `test_spike_prompt_template_clean`)은 base commit 5d67d94 에서도 동일 재현(직접 checkout 후 재실행으로 pre-existence 증명) — gemini-c/d wiring + 모델 string + optional-dep smoke 등 별도 미완 기능. 본 plan 신규 심볼과 결합 0.
- 11 collection error(`test_spike_*` / `test_pole_detector` 등)는 optional dep(cv2/imageio/fixtures) 부재 — 본 plan 무관.
- **본 plan 변경으로 인한 NEW 실패는 vision_gate 1건뿐이었고 즉시 Rule 1 으로 fix(76c19f4).** 그 외 NEW 회귀 0.

## Verification Results

- `cd backend && PYTHONPATH=shared/python python3 -m pytest tests/test_pipeline_mode3.py -x -q` → **31 passed** (Task 1 10 + Task 3 12 + 기존 9)
- `cd backend && PYTHONPATH=shared/python python3 -m pytest tests/test_vision_veto.py tests/test_gemini_vision_scorer.py tests/test_pipeline_mode3.py -q` → **54 passed**
- `cd backend && PYTHONPATH=shared/python python3 -m pytest tests/test_pipeline_vision_gate.py -q` → **14 passed** (Rule 1 fix 후)
- `cd app && node scripts/assert-result-score-suppression.mjs --self-test` → exit 0 (4 fixture 기대대로)
- `cd app && node scripts/assert-result-score-suppression.mjs` → exit 0 (점수카드 전체 억제 + reason-owns-copy 통과, cwd-stable: repo root + app/ 둘 다 동일)
- `cd app && npm run typecheck` → clean (visionVeto union + ScoreSuppression discriminated type + scoreSuppressionAudit)
- 3-way lockstep grep: visionVeto/scoreSuppressedReason/scoreSuppressionAudit 가 analysis.ts + models.py + contract.md 3곳 동시 정의 확인
- 객관성 grep: visionVeto 에 score/점수 필드 0; result.tsx 신규 라인 hardcoded hex/magic-px 0
- 전체 suite: 51 failed(전부 base 5d67d94 에서 동일 재현되는 pre-existing) + 1690 passed + 11 collection error(optional dep). NEW 회귀 0.
- **Pod 무관** — 전부 pod-free(adapter mocked + cap monkeypatch + 정적 .mjs). 실 정량 게이트(kip-up≤50, visionVeto.status='applied') 는 20-04 Pod sweep.

## User Setup Required

None — 기존 GEMINI_API_KEY 재사용, 신규 패키지 0(20-01/20-02 모듈 + 기존 adapter + node stdlib fs/.mjs). 운영 시 `GEMINI_VISION_VETO_ENABLED` env opt-in + visionVeto/scoreSuppressed* schema 키 추가로 EAS 재빌드 필요(optional 키).

## Next Phase Readiness

- **20-04 (derive_caps eval):** SEVERITY_CAP moderate/major 채움 + sensitivity_manifest_sha256 갱신(20-01 fail-closed 통과 조건) → cap 활성. 실 거부권(kip-up≤50) + visionVeto.status='applied' 정량 증명 = Pod sweep terminal gate. _apply_vision_veto 본체 + status enum + scoreSuppressed UX 전부 준비됨.
- **블로커:** 없음 (pod-free Wave 2 완료).

---
*Phase: 20-v2-gemini*
*Completed: 2026-06-20*

## Self-Check: PASSED

- 20-03-SUMMARY.md FOUND
- assert-result-score-suppression.mjs FOUND
- app.py (pipeline) FOUND
- commits bf39e9e / f79f42a / c09dd49 / 76c19f4 FOUND
