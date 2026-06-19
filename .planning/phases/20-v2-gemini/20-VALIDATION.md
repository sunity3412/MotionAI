---
phase: 20
slug: v2-gemini
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-19
amended: 2026-06-19
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 출처: 20-RESEARCH.md §Validation Architecture. 임계값 수치는 D-02(curve-fit 금지)에 따라 eval 도출 — 본 문서는 검증 *구조*만.
> **Amended 2026-06-19 (20-DIRECT-REVIEW):** V-1 phase-gate fail-closed, V-7 schema/dataclass 내성검사, +V-10(veto no-op 차단/status enum), +V-11(self-check≠approval), +V-12(derive fail-closed), +V-13(prompt/schema 캐시 무효화).
> **Amended 2026-06-19 (20-DIRECT-REVIEW-ITERATION2):** V-8 점수카드 전체 억제 + scoreSuppressed 3-way 계약(HIGH-2/3), V-11 fail-closed pod-free pytest 자동화(MEDIUM-4), V-12 diversity floor(MEDIUM-3), +V-14(per-row visionVeto.status — MEDIUM-2), +V-15(어댑터 토글 미소유 — MEDIUM-1), +V-16(cap-mutation monkeypatch 증명 — HIGH-1), +V-17(visionVeto discriminated union + input_granularity 캐시 키 — non-blocking).
> **Amended 2026-06-19 (20-DIRECT-REVIEW-ITERATION3):** V-8 실 실행 커맨드(`node app/scripts/assert-result-score-suppression.mjs` — 앱 test runner 부재, RN render test 대신 정적 단언; HIGH-1) + isScoreSuppressed STRICTLY scoreSuppressed===true(scoringBasis 폴백 0) + missing-flag producer-contract fail-loud(HIGH-2), +V-18(scoreSuppressedReason unheld vs recognition_low_confidence — low_confidence 를 '기준 없음' 과 분리, MEDIUM-1), V-14 DATA-DRIVEN per-row status(manifest expected_veto_status, regression fault row 는 applied|not_applicable 허용 — MEDIUM-2).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8 (backend, `backend/requirements-dev.txt`) + Python self-check 하니스 + node 정적 단언 스크립트(앱 — Jest/RN 스택 미도입) |
| **Config file** | none (backend/tests/ 직접; 앱 = `node app/scripts/*.mjs` 직접) |
| **Quick run command** | `python -m pytest backend/tests/ -q` + `python backend/evals/phase20/assert_baseline_v2.py --self-check` + `node app/scripts/assert-result-score-suppression.mjs` |
| **Full suite command** | `python -m pytest backend/tests/ -q` (회귀 0) + `node app/scripts/assert-result-score-suppression.mjs` + `cd app && npm run typecheck` |
| **Estimated runtime** | ~수십초 (pod-free 단위/self-check/정적 .mjs) |

> ⚠️ **앱 test runner 부재(iter3 HIGH-1):** `app/package.json` 에 `test` 스크립트/Jest/RN 테스트 스택이 없다. mid-phase 도입 금지. Mode3 억제 검증은 RN render test 가 아닌 **실행되는 정적 단언 스크립트** `node app/scripts/assert-result-score-suppression.mjs` — typecheck-only 가 아니라 점수카드 6요소 가드를 실제로 검사(false-green 차단).
> ⚠️ **정량 regression/generalization eval(`sweep_phase15.py --pair-sequential`)은 RunPod RTMW GPU 필요 — 현재 down.** pod-free 단위테스트(순수 `vision_veto` 로직 + mocked Gemini 어댑터) + self-check + 정적 .mjs 먼저, 실 sweep 은 **terminal gate**(Pod 재개 후, 순차만 — 동시 금지).
> ⚠️ **HIGH-2 + iter2 MEDIUM-4:** `assert_baseline_v2.py --self-check` 는 phase gate 가 아니다(approval 금지). phase gate 는 `--phase-gate`(기본) 이며 Pod baseline 자산 부재 시 fail-closed(non-zero). 이 fail-closed 동작은 pod-free pytest(`test_assert_baseline_v2.py`)로 자동 검증된다.

---

## Sampling Rate

- **After every task commit:** `python -m pytest backend/tests/ -q` (해당 모듈) + 객관성 내성검사(build_schema/dataclass — 점수 필드 0) + (result.tsx 변경 시) `node app/scripts/assert-result-score-suppression.mjs`
- **After every plan wave:** 전체 pytest 회귀 0 + `assert_baseline_v2.py --self-check` PASS (approval 아님) + fail-closed pytest GREEN + 정적 억제 단언 exit 0
- **Before `/gsd-verify-work`:** pod-free suite green + 정적 억제 단언 exit 0 + (Pod 재개 시) `--phase-gate` PASS ↔ baseline 대조 + data-driven per-row status counts
- **Max feedback latency:** ~60s (pod-free)

---

## Validation Architecture (검증해야 할 핵심 성질 — 임계값 수치 아님, 성질)

| ID | 검증 성질 | 방법 | pod 의존 |
|----|----------|------|---------|
| V-1 | kip-up fault 영상이 **≤50** 로 내려감(위양성 해소) — **`--phase-gate` fail-closed: baseline 자산 부재 시 non-zero, self-check 로 green 처리 금지** | `--phase-gate` 후 baseline 대조 — known_false_positive → discriminate 전환 + visionVeto.status='applied' | **Pod** |
| V-2 | 변별 4쌍(power-spin/peter-pan/elbow-twist/pdshape) **퇴행 0** (fault<success 유지) | `assert_baseline_v2.py --phase-gate` + sweep 대조 | **Pod** |
| V-3 | 정은지 **정타 95~100 유지** (비전이 깨끗한 자세를 안 깎음) + clean row visionVeto.status='not_applicable' | sweep 정타 영상 + per-row status | **Pod** |
| V-4 | **결정론** — 같은 입력=같은 점수(캐시가 보장, temp 0 단독 아님 — Pitfall 2) | 같은 영상 N회 + 캐시 키 단위테스트(cache-warm byte-identity) | pod-free(캐시 단위) / Pod(실 점수) |
| V-5 | **일반화** — 미보유 + above-cutoff(고득점이어야 정상) sensitivity 케이스 위양성↔위음성 양방 | sensitivity 셋(별도 수집, diversity floor) sweep | **Pod** + 자산 수집 |
| V-6 | 비전 veto **하향 전용** — 어떤 입력도 점수를 올리지 않음(min cap 구조) | 순수 `vision_veto` 단위테스트(올림 불가 invariant) | **pod-free** |
| V-7 | **객관성** — 비전 출력에 사람 점수 라벨 ground truth 0, 점수 필드 누출 0. **MEDIUM-1: raw 파일 grep 아닌 `build_schema()['properties']` + `VisionVerdict` dataclass 내성검사**(_SCORE_PATTERN 존재는 위반 아님; overall_qualitative 복사 금지) | 스키마/데이터클래스 내성검사 + `_SCORE_PATTERN` leak 거부 단위테스트 | **pod-free** |
| V-8 | Mode3 미보유 → **점수카드 전체 억제**(OctagonScore + gradeBadge + score-derived summary + LevelBenchmark + scoreCaption + '점수를 확인해보세요' 헤더 카피 모두 ABSENT — octagon-only 아님, iter2 HIGH-2) + '기준 없음'. **scoreSuppressed + scoreSuppressedReason 가 visionVeto 와 동일 3-way 계약(analysis.ts+models.py+contract.md) lockstep, scoringBasis 단독 의존 금지(iter2 HIGH-3 / iter3 MEDIUM-1)**. **iter3 HIGH-2: 프런트 isScoreSuppressed 는 STRICTLY result.scoreSuppressed===true(scoringBasis 폴백 0); reference_free_absolute 인데 flag 누락 = producer-contract FAILURE(fail-loud).** **iter3 HIGH-1: 검증은 RN render test 가 아닌 실 실행 정적 스크립트 `node app/scripts/assert-result-score-suppression.mjs`(점수카드 6요소 isScoreSuppressed 가드 검사, non-zero on 위반) — typecheck-only 아님** | **`node app/scripts/assert-result-score-suppression.mjs` (exit 0/non-zero)** + 3분기 라우팅 단위(recognizer category ↔ ipsf_map reconcile A2 / missing-flag fail-loud) + scoreSuppressed/scoreSuppressedReason 3-way grep + `cd app && npm run typecheck` | **pod-free** |
| V-9 | veto 무음실패 방지 — try/except 가 게이트를 silent no-op 안 함 | WARNING + audit 필드(visionVeto.status enum) 단위테스트 (Pitfall 5) | **pod-free** |
| V-10 | **veto no-op 차단(HIGH-1)** — Phase17 vision OFF + veto ON 이면 keep_local_video=True 라 adapter 가 non-None local_video_path 수신. visionVeto.status ∈ {applied, not_applicable, disabled, skipped_error, missing_local_video} 가 veto 실행을 증명(부재≠실행) | keep_local_video 게이트 + status enum 단위테스트 (mocked adapter) | **pod-free** |
| V-11 | **self-check ≠ approval(HIGH-2) + fail-closed 자동(iter2 MEDIUM-4)** — `--self-check` 는 phase gate 아님(approval 기록 금지); `--phase-gate`/기본 은 baseline 자산 부재 시 fail-closed non-zero. **이 fail-closed 동작은 pod-free pytest(temp empty baseline → non-zero exit assert)로 자동 검증 — acceptance 산문 아님** | `test_assert_baseline_v2.py`(fail-closed pytest + self-check≠approval) + terminal evidence(eval20_serial_baseline.json + eval20_gate_report.json) | **pod-free**(fail-closed/모드 분기) / Pod(실 evidence) |
| V-12 | **derive fail-closed + diversity floor(HIGH-3 + iter2 MEDIUM-3)** — sensitivity TODO/누락 video key/diversity floor(must_drop ≥2 videos·≥2 ids + must_stay_high ≥3 videos·≥2 ids + ≥2 sessions if available) 미달 시 cap 도출 거부 + SEVERITY_CAP 미변경. phase18 6페어 derive 입력 금지. cap 박제 시 SEVERITY_CAP_PROVENANCE.sensitivity_manifest_sha256 실 sha + phase18_pairs_used_for_derivation=False + diversity summary | derive_caps fail-closed/floor 단위(`test_derive_caps_floor_fail_closed`) + provenance 일관성 단위테스트 | **pod-free**(가드) / Pod(실 도출) |
| V-13 | **캐시 prompt/schema 버전(MEDIUM-2)** — VisionVetoCache 키에 PROMPT_VERSION/SCHEMA_VERSION 포함, 변경 시 stale verdict 무효화(recognizer 캐시 키 재사용 금지) | PROMPT_VERSION monkeypatch → cache-miss 단위테스트 | **pod-free** |
| V-14 | **DATA-DRIVEN per-row visionVeto.status(iter3 MEDIUM-2 — '모든 fault row=applied' 폐기)** — `--phase-gate` 가 EVERY eval row 의 status 를 manifest 의 row-local `expected_veto_status` 로 검사(generic fault/clean 라벨 도출 아님): must_drop row(kip-up 포함)→'applied'+점수 상한, must_stay_high row→'not_applicable'+고점 하한, **regression fault row(4쌍)→status ∈ {applied, not_applicable} 허용하되 fault<success + skipped status 0**; ALL row→disabled/missing_local_video/skipped_error/부재 시 FAIL. eval20_gate_report.json 에 vision_veto_status_counts + expected_bucket_counts + rows_without_veto_status + skipped_error_rows. D-04 를 코드-경로 주장에서 eval 산출물로 전환하되 over-cap curve-fit 압박 완화 | data-driven per-row status 검사 함수 단위(`test_per_row_status_data_driven`, pod-free — manifest expected_veto_status 읽고 must_drop/must_stay_high/regression 분기, applied-only 강제 아님) + Pod phase-gate 실 row | **pod-free**(로직) / Pod(실 row) |
| V-15 | **어댑터 토글 미소유(iter2 MEDIUM-1)** — gemini_vision_scorer 가 backend.functions.pipeline import 0 + `_gemini_vision_veto_enabled` 정의 0 + GEMINI_VISION_VETO_ENABLED env 미참조. 토글은 pipeline(app.py) 단독 소유, _apply_vision_veto 가 유일 게이트 (adapter-boundary, drift 방지) | 어댑터 AST/소스 import·정의 0 단위(`test_adapter_does_not_own_toggle`) + pipeline 소유 단위(`test_toggle_owned_by_pipeline`) | **pod-free** |
| V-16 | **cap-mutation 증명(iter2 HIGH-1)** — production SEVERITY_CAP 은 20-04 까지 placeholder None 유지하되, mutation 경로(overallScore 하향)는 pipeline 테스트에서 `monkeypatch.setitem(SEVERITY_CAP,'major',50)` scoped fixture 로 pod-free 증명(severity='major'+100→50). placeholder None(monkeypatch 없음)→not_applicable 도 증명. D-02 무손상 | cap-mutation monkeypatch 단위(`test_vision_veto_downward_only_with_cap` + `test_vision_veto_placeholder_cap_no_mutation`) | **pod-free** |
| V-17 | **visionVeto discriminated union + input_granularity 캐시 키(iter2 non-blocking)** — TS visionVeto 가 discriminated union 으로 status='applied'→capApplied 컴파일 강제. VisionVetoCache 키에 input_granularity 포함(whole↔frame 충돌 0) | tsc(union — applied without capApplied = 에러) + 캐시 키 단위(`test_cache_key_includes_input_granularity`) | **pod-free** |
| V-18 | **scoreSuppressedReason 분리(iter3 MEDIUM-1)** — low_confidence 를 '기준 없음' 으로 라벨하지 않음. scoreSuppressedReason ∈ {unheld, recognition_low_confidence} 3-way lockstep(analysis.ts+models.py+contract.md). is_reference_free(branch metadata)→'unheld'(기준 없음 카피), recognizer low_confidence→'recognition_low_confidence'(동작 인식 신뢰도 카피). A2 = '반드시 일치' 아닌 explicit reason reconcile, 불일치 audit 보고 | scoreSuppressedReason 3-way grep + `test_low_confidence_suppressed_reason` + `test_recognizer_ipsf_map_reconcile` (pod-free) | **pod-free** |

---

## Per-Task Verification Map

> V-1~V-18 를 task 에 매핑. pod-free task 먼저, V-1/2/3/5/14 는 terminal Pod `--phase-gate` (fail-closed + data-driven per-row status).

| Task ID | Plan | Wave | Requirement | Threat Ref | Test Type | Automated Command | Pod | Status |
|---------|------|------|-------------|------------|-----------|-------------------|-----|--------|
| 20-01-T1 | 20-01 | 1 | SCORE-08, TRUST-08 | T-20-01/02/02b/03 | unit (property) | `pytest tests/test_vision_veto.py -x -q` | pod-free | ⬜ pending |
| 20-02-T1 | 20-02 | 1 | SCORE-08, TRUST-06/08 | T-20-04/04b/08/08b/08c | unit (mocked) | `pytest tests/test_gemini_vision_scorer.py -x -q` | pod-free | ⬜ pending |
| 20-03-T1 | 20-03 | 2 | SCORE-08, TRUST-08 | T-20-09/09b/09c/09d/10 | unit (mocked) | `pytest tests/test_pipeline_mode3.py -k "vision_veto or keep_local_video or toggle_owned" -x -q` | pod-free | ⬜ pending |
| 20-03-T2 | 20-03 | 2 | TRUST-08 | T-20-13/11c | typecheck | `cd app && npm run typecheck` | pod-free | ⬜ pending |
| 20-03-T3 | 20-03 | 2 | TRUST-06/07 | T-20-11/11b/11d/11e/11f/12/14 | unit (mocked) + 정적 .mjs + typecheck | `pytest tests/test_pipeline_mode3.py -k "branch3 or reference_free or recognizer or line_dim_determinism or missing_suppression or low_confidence" -x -q && cd ../app && node scripts/assert-result-score-suppression.mjs && npm run typecheck` | pod-free | ⬜ pending |
| 20-04-T1 | 20-04 | 3 | SCORE-09 | T-20-15/15b/15c/18/18b | self-check + fail-closed pytest | `pytest tests/test_assert_baseline_v2.py -x -q && python evals/phase20/assert_baseline_v2.py --self-check` | pod-free | ⬜ pending |
| 20-04-T2 | 20-04 | 3 | SCORE-09/08, TRUST-06 | T-20-15/15c/16/18/18b | phase-gate | `python evals/phase20/assert_baseline_v2.py --phase-gate` | **Pod** TERMINAL | ⬜ pending |

| V-ID → Task | V-1→20-04-T2 · V-2→20-04-T2 · V-3→20-04-T2 · V-4→20-02-T1/20-03-T3(cache)+20-04-T2(real) · V-5→20-04-T2 · V-6→20-01-T1 · V-7→20-02-T1 · V-8→20-03-T3(정적 .mjs + scoreSuppressed/scoreSuppressedReason 3-way + missing-flag) · V-9→20-03-T1 · V-10→20-03-T1 · V-11→20-04-T1(fail-closed pytest)/T2 · V-12→20-04-T1 · V-13→20-02-T1 · V-14→20-04-T1(data-driven 로직)/T2(실 row) · V-15→20-02-T1+20-03-T1 · V-16→20-03-T1 · V-17→20-02-T1(캐시 키)+20-03-T2(union tsc) · V-18→20-03-T2(3-way)+20-03-T3(reason emit/reconcile) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/` vision_veto 단위 픽스처(mocked Gemini 어댑터 — 실 API/Pod 무관)
- [ ] 객관성 내성검사 픽스처(build_schema/dataclass — 점수 필드 0, raw grep 아님 — MEDIUM-1)
- [ ] keep_local_video 게이트 + visionVeto status enum 픽스처(HIGH-1)
- [ ] cap-mutation monkeypatch 픽스처(SEVERITY_CAP['major']=50 scoped — iter2 HIGH-1, V-16)
- [ ] **정적 억제 단언 스크립트 `app/scripts/assert-result-score-suppression.mjs`(점수카드 6요소 가드 검사 — iter3 HIGH-1, V-8; RN render test 대체, Jest/RN 스택 미도입)**
- [ ] fail-closed pytest 픽스처(temp empty baseline → non-zero — iter2 MEDIUM-4, V-11)
- [ ] **data-driven per-row status 픽스처(합성 manifest expected_veto_status — iter3 MEDIUM-2, V-14; applied-only 강제 아님 단언)**

*기존 `backend/evals/phase18/`(pairs/baseline/assert_baseline.py) + `sweep_phase15.py` 재사용 — 신규 인프라 최소. 앱 = node .mjs 직접(test runner 미도입).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 실 GPU 정량 regression(V-1/2/3/14) | SCORE-08/09 | RTMW GPU 필요(Pod down) | Pod 재개 후 `sweep_phase15.py --mode mode1 --pair-sequential` 순차 → `assert_baseline_v2.py --phase-gate`(fail-closed + data-driven per-row status) |
| sensitivity 일반화(V-5) | TRUST-06 | 미보유+above-cutoff 자산 수집 선행(diversity floor: must_drop≥2/≥2ids, must_stay_high≥3/≥2ids) | 별도 셋 수집(sensitivity.yaml TODO→실 video_key + expected_veto_status 채움) 후 sweep |

*나머지 V-4(캐시)/V-6/V-7/V-8(정적 .mjs)/V-9/V-10/V-12/V-13/V-15/V-16/V-17/V-18 는 pod-free 자동 검증. V-11 은 fail-closed pytest pod-free + 실 evidence Pod. V-14 는 data-driven per-row 로직 pod-free + 실 row Pod.*

---

## Validation Sign-Off

- [ ] pod-free task 전부 `<automated>` verify 보유(V-6~V-18 의 pod-free 부분) — **V-8 은 typecheck 단독 아닌 `node app/scripts/assert-result-score-suppression.mjs` 실 실행 포함(iter3 HIGH-1)**
- [ ] Pod-dependent V-1/2/3/5/14 는 terminal `--phase-gate` (fail-closed + data-driven per-row status, silent skip + self-check false-green 금지 — HIGH-2/iter3 MEDIUM-2/iter2 MEDIUM-4)
- [ ] 객관성 gate(V-7 내성검사) + 하향전용 invariant(V-6) + veto no-op 차단(V-10) + cap-mutation 증명(V-16) Wave 0 커버
- [ ] 점수카드 전체 억제(V-8 정적 .mjs 실 실행) + scoreSuppressed/scoreSuppressedReason 3-way 계약(V-8/V-18 grep) + STRICTLY flag/missing-flag fail-loud 커버 (iter2 HIGH-2/3 / iter3 HIGH-1/2/MEDIUM-1)
- [ ] 어댑터 토글 미소유(V-15) + data-driven per-row status(V-14) + fail-closed pytest(V-11) + diversity floor(V-12) 커버 (iter2 MEDIUM-1/iter3 MEDIUM-2/iter2 MEDIUM-4/3)
- [ ] derive fail-closed(V-12) + 캐시 prompt/schema 버전(V-13) + discriminated union/input_granularity(V-17) + scoreSuppressedReason 분리(V-18) 커버
- [ ] eval 동시 실행 금지(순차만) 박제
- [ ] `nyquist_compliant: true` (planner task 매핑 후)

**Approval:** pending
