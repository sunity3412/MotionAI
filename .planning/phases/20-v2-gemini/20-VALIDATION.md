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

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8 (backend, `backend/requirements-dev.txt`) + Python self-check 하니스 |
| **Config file** | none (backend/tests/ 직접) |
| **Quick run command** | `python -m pytest backend/tests/ -q` + `python backend/evals/phase20/assert_baseline_v2.py --self-check` |
| **Full suite command** | `python -m pytest backend/tests/ -q` (회귀 0) |
| **Estimated runtime** | ~수십초 (pod-free 단위/self-check) |

> ⚠️ **정량 regression/generalization eval(`sweep_phase15.py --pair-sequential`)은 RunPod RTMW GPU 필요 — 현재 down.** pod-free 단위테스트(순수 `vision_veto` 로직 + mocked Gemini 어댑터) + self-check 먼저, 실 sweep 은 **terminal gate**(Pod 재개 후, 순차만 — 동시 금지).
> ⚠️ **HIGH-2 + iter2 MEDIUM-4:** `assert_baseline_v2.py --self-check` 는 phase gate 가 아니다(approval 금지). phase gate 는 `--phase-gate`(기본) 이며 Pod baseline 자산 부재 시 fail-closed(non-zero). 이 fail-closed 동작은 pod-free pytest(`test_assert_baseline_v2.py`)로 자동 검증된다.

---

## Sampling Rate

- **After every task commit:** `python -m pytest backend/tests/ -q` (해당 모듈) + 객관성 내성검사(build_schema/dataclass — 점수 필드 0)
- **After every plan wave:** 전체 pytest 회귀 0 + `assert_baseline_v2.py --self-check` PASS (approval 아님) + fail-closed pytest GREEN
- **Before `/gsd-verify-work`:** pod-free suite green + (Pod 재개 시) `--phase-gate` PASS ↔ baseline 대조 + per-row status counts
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
| V-8 | Mode3 미보유 → **점수카드 전체 억제**(OctagonScore + gradeBadge + score-derived summary + LevelBenchmark + scoreCaption + '점수를 확인해보세요' 헤더 카피 모두 ABSENT — octagon-only 아님, iter2 HIGH-2) + '기준 없음'. **scoreSuppressed 가 visionVeto 와 동일 3-way 계약(analysis.ts+models.py+contract.md) lockstep, scoringBasis 단독 의존 금지(iter2 HIGH-3)** | RN render/component test(score-derived 요소 ABSENT) + 3분기 라우팅 단위(recognizer category ↔ ipsf_map 정합 A2) + scoreSuppressed 3-way grep | **pod-free** |
| V-9 | veto 무음실패 방지 — try/except 가 게이트를 silent no-op 안 함 | WARNING + audit 필드(visionVeto.status enum) 단위테스트 (Pitfall 5) | **pod-free** |
| V-10 | **veto no-op 차단(HIGH-1)** — Phase17 vision OFF + veto ON 이면 keep_local_video=True 라 adapter 가 non-None local_video_path 수신. visionVeto.status ∈ {applied, not_applicable, disabled, skipped_error, missing_local_video} 가 veto 실행을 증명(부재≠실행) | keep_local_video 게이트 + status enum 단위테스트 (mocked adapter) | **pod-free** |
| V-11 | **self-check ≠ approval(HIGH-2) + fail-closed 자동(iter2 MEDIUM-4)** — `--self-check` 는 phase gate 아님(approval 기록 금지); `--phase-gate`/기본 은 baseline 자산 부재 시 fail-closed non-zero. **이 fail-closed 동작은 pod-free pytest(temp empty baseline → non-zero exit assert)로 자동 검증 — acceptance 산문 아님** | `test_assert_baseline_v2.py`(fail-closed pytest + self-check≠approval) + terminal evidence(eval20_serial_baseline.json + eval20_gate_report.json) | **pod-free**(fail-closed/모드 분기) / Pod(실 evidence) |
| V-12 | **derive fail-closed + diversity floor(HIGH-3 + iter2 MEDIUM-3)** — sensitivity TODO/누락 video key/diversity floor(must_drop ≥2 videos·≥2 ids + must_stay_high ≥3 videos·≥2 ids + ≥2 sessions if available) 미달 시 cap 도출 거부 + SEVERITY_CAP 미변경. phase18 6페어 derive 입력 금지. cap 박제 시 SEVERITY_CAP_PROVENANCE.sensitivity_manifest_sha256 실 sha + phase18_pairs_used_for_derivation=False + diversity summary | derive_caps fail-closed/floor 단위(`test_derive_caps_floor_fail_closed`) + provenance 일관성 단위테스트 | **pod-free**(가드) / Pod(실 도출) |
| V-13 | **캐시 prompt/schema 버전(MEDIUM-2)** — VisionVetoCache 키에 PROMPT_VERSION/SCHEMA_VERSION 포함, 변경 시 stale verdict 무효화(recognizer 캐시 키 재사용 금지) | PROMPT_VERSION monkeypatch → cache-miss 단위테스트 | **pod-free** |
| V-14 | **per-row visionVeto.status(iter2 MEDIUM-2)** — `--phase-gate` 가 EVERY eval row 의 status 검사: fault/false-positive(떨어져야 함)→'applied', clean/above-cutoff(유지)→'not_applicable'; disabled/missing_local_video/skipped_error/부재 row 는 FAIL. eval20_gate_report.json 에 vision_veto_status_counts + rows_without_veto_status + skipped_error_rows. D-04 를 코드-경로 주장에서 eval 산출물로 전환 | per-row status 검사 함수 단위(`test_per_row_status_logic`, pod-free) + Pod phase-gate 실 row | **pod-free**(로직) / Pod(실 row) |
| V-15 | **어댑터 토글 미소유(iter2 MEDIUM-1)** — gemini_vision_scorer 가 backend.functions.pipeline import 0 + `_gemini_vision_veto_enabled` 정의 0 + GEMINI_VISION_VETO_ENABLED env 미참조. 토글은 pipeline(app.py) 단독 소유, _apply_vision_veto 가 유일 게이트 (adapter-boundary, drift 방지) | 어댑터 AST/소스 import·정의 0 단위(`test_adapter_does_not_own_toggle`) + pipeline 소유 단위(`test_toggle_owned_by_pipeline`) | **pod-free** |
| V-16 | **cap-mutation 증명(iter2 HIGH-1)** — production SEVERITY_CAP 은 20-04 까지 placeholder None 유지하되, mutation 경로(overallScore 하향)는 pipeline 테스트에서 `monkeypatch.setitem(SEVERITY_CAP,'major',50)` scoped fixture 로 pod-free 증명(severity='major'+100→50). placeholder None(monkeypatch 없음)→not_applicable 도 증명. D-02 무손상 | cap-mutation monkeypatch 단위(`test_vision_veto_downward_only_with_cap` + `test_vision_veto_placeholder_cap_no_mutation`) | **pod-free** |
| V-17 | **visionVeto discriminated union + input_granularity 캐시 키(iter2 non-blocking)** — TS visionVeto 가 discriminated union 으로 status='applied'→capApplied 컴파일 강제. VisionVetoCache 키에 input_granularity 포함(whole↔frame 충돌 0) | tsc(union — applied without capApplied = 에러) + 캐시 키 단위(`test_cache_key_includes_input_granularity`) | **pod-free** |

---

## Per-Task Verification Map

> V-1~V-17 를 task 에 매핑. pod-free task 먼저, V-1/2/3/5/14 는 terminal Pod `--phase-gate` (fail-closed + per-row status).

| Task ID | Plan | Wave | Requirement | Threat Ref | Test Type | Automated Command | Pod | Status |
|---------|------|------|-------------|------------|-----------|-------------------|-----|--------|
| 20-01-T1 | 20-01 | 1 | SCORE-08, TRUST-08 | T-20-01/02/02b/03 | unit (property) | `pytest tests/test_vision_veto.py -x -q` | pod-free | ⬜ pending |
| 20-02-T1 | 20-02 | 1 | SCORE-08, TRUST-06/08 | T-20-04/04b/08/08b/08c | unit (mocked) | `pytest tests/test_gemini_vision_scorer.py -x -q` | pod-free | ⬜ pending |
| 20-03-T1 | 20-03 | 2 | SCORE-08, TRUST-08 | T-20-09/09b/09c/09d/10 | unit (mocked) | `pytest tests/test_pipeline_mode3.py -k "vision_veto or keep_local_video or toggle_owned" -x -q` | pod-free | ⬜ pending |
| 20-03-T2 | 20-03 | 2 | TRUST-08 | T-20-13/11c | typecheck | `cd app && npm run typecheck` | pod-free | ⬜ pending |
| 20-03-T3 | 20-03 | 2 | TRUST-06/07 | T-20-11/11b/12/14 | unit (mocked) + RN render | `pytest tests/test_pipeline_mode3.py -k "branch3 or reference_free or recognizer_category or line_dim_determinism" -x -q && cd ../app && npm run typecheck` | pod-free | ⬜ pending |
| 20-04-T1 | 20-04 | 3 | SCORE-09 | T-20-15/15b/18/18b | self-check + fail-closed pytest | `pytest tests/test_assert_baseline_v2.py -x -q && python evals/phase20/assert_baseline_v2.py --self-check` | pod-free | ⬜ pending |
| 20-04-T2 | 20-04 | 3 | SCORE-09/08, TRUST-06 | T-20-15/16/18/18b | phase-gate | `python evals/phase20/assert_baseline_v2.py --phase-gate` | **Pod** TERMINAL | ⬜ pending |

| V-ID → Task | V-1→20-04-T2 · V-2→20-04-T2 · V-3→20-04-T2 · V-4→20-02-T1/20-03-T3(cache)+20-04-T2(real) · V-5→20-04-T2 · V-6→20-01-T1 · V-7→20-02-T1 · V-8→20-03-T3(render+scoreSuppressed 3-way) · V-9→20-03-T1 · V-10→20-03-T1 · V-11→20-04-T1(fail-closed pytest)/T2 · V-12→20-04-T1 · V-13→20-02-T1 · V-14→20-04-T1(로직)/T2(실 row) · V-15→20-02-T1+20-03-T1 · V-16→20-03-T1 · V-17→20-02-T1(캐시 키)+20-03-T2(union tsc) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/` vision_veto 단위 픽스처(mocked Gemini 어댑터 — 실 API/Pod 무관)
- [ ] 객관성 내성검사 픽스처(build_schema/dataclass — 점수 필드 0, raw grep 아님 — MEDIUM-1)
- [ ] keep_local_video 게이트 + visionVeto status enum 픽스처(HIGH-1)
- [ ] cap-mutation monkeypatch 픽스처(SEVERITY_CAP['major']=50 scoped — iter2 HIGH-1, V-16)
- [ ] RN render/component test 픽스처(점수카드 전체 억제 ABSENT 단언 — iter2 HIGH-2, V-8)
- [ ] fail-closed pytest 픽스처(temp empty baseline → non-zero — iter2 MEDIUM-4, V-11)

*기존 `backend/evals/phase18/`(pairs/baseline/assert_baseline.py) + `sweep_phase15.py` 재사용 — 신규 인프라 최소.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 실 GPU 정량 regression(V-1/2/3/14) | SCORE-08/09 | RTMW GPU 필요(Pod down) | Pod 재개 후 `sweep_phase15.py --mode mode1 --pair-sequential` 순차 → `assert_baseline_v2.py --phase-gate`(fail-closed + per-row status) |
| sensitivity 일반화(V-5) | TRUST-06 | 미보유+above-cutoff 자산 수집 선행(diversity floor: must_drop≥2/≥2ids, must_stay_high≥3/≥2ids) | 별도 셋 수집(sensitivity.yaml TODO→실 video_key) 후 sweep |

*나머지 V-4(캐시)/V-6/V-7/V-8/V-9/V-10/V-12/V-13/V-15/V-16/V-17 는 pod-free 자동 검증. V-11 은 fail-closed pytest pod-free + 실 evidence Pod. V-14 는 per-row 로직 pod-free + 실 row Pod.*

---

## Validation Sign-Off

- [ ] pod-free task 전부 `<automated>` verify 보유(V-6~V-17 의 pod-free 부분)
- [ ] Pod-dependent V-1/2/3/5/14 는 terminal `--phase-gate` (fail-closed + per-row status, silent skip + self-check false-green 금지 — HIGH-2/iter2 MEDIUM-2/4)
- [ ] 객관성 gate(V-7 내성검사) + 하향전용 invariant(V-6) + veto no-op 차단(V-10) + cap-mutation 증명(V-16) Wave 0 커버
- [ ] 점수카드 전체 억제(V-8 render) + scoreSuppressed 3-way 계약(V-8 grep) 커버 (iter2 HIGH-2/3)
- [ ] 어댑터 토글 미소유(V-15) + per-row status(V-14) + fail-closed pytest(V-11) + diversity floor(V-12) 커버 (iter2 MEDIUM-1/2/3/4)
- [ ] derive fail-closed(V-12) + 캐시 prompt/schema 버전(V-13) + discriminated union/input_granularity(V-17) 커버
- [ ] eval 동시 실행 금지(순차만) 박제
- [ ] `nyquist_compliant: true` (planner task 매핑 후)

**Approval:** pending
