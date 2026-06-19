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
> ⚠️ **HIGH-2:** `assert_baseline_v2.py --self-check` 는 phase gate 가 아니다(approval 금지). phase gate 는 `--phase-gate`(기본) 이며 Pod baseline 자산 부재 시 fail-closed(non-zero).

---

## Sampling Rate

- **After every task commit:** `python -m pytest backend/tests/ -q` (해당 모듈) + 객관성 내성검사(build_schema/dataclass — 점수 필드 0)
- **After every plan wave:** 전체 pytest 회귀 0 + `assert_baseline_v2.py --self-check` PASS (approval 아님)
- **Before `/gsd-verify-work`:** pod-free suite green + (Pod 재개 시) `--phase-gate` PASS ↔ baseline 대조
- **Max feedback latency:** ~60s (pod-free)

---

## Validation Architecture (검증해야 할 핵심 성질 — 임계값 수치 아님, 성질)

| ID | 검증 성질 | 방법 | pod 의존 |
|----|----------|------|---------|
| V-1 | kip-up fault 영상이 **≤50** 로 내려감(위양성 해소) — **`--phase-gate` fail-closed: baseline 자산 부재 시 non-zero, self-check 로 green 처리 금지** | `--phase-gate` 후 baseline 대조 — known_false_positive → discriminate 전환 + visionVeto.status='applied' | **Pod** |
| V-2 | 변별 4쌍(power-spin/peter-pan/elbow-twist/pdshape) **퇴행 0** (fault<success 유지) | `assert_baseline_v2.py --phase-gate` + sweep 대조 | **Pod** |
| V-3 | 정은지 **정타 95~100 유지** (비전이 깨끗한 자세를 안 깎음) | sweep 정타 영상 | **Pod** |
| V-4 | **결정론** — 같은 입력=같은 점수(캐시가 보장, temp 0 단독 아님 — Pitfall 2) | 같은 영상 N회 + 캐시 키 단위테스트(cache-warm byte-identity) | pod-free(캐시 단위) / Pod(실 점수) |
| V-5 | **일반화** — 미보유 + above-cutoff(고득점이어야 정상) sensitivity 케이스 위양성↔위음성 양방 | sensitivity 셋(별도 수집, 2-bucket) sweep | **Pod** + 자산 수집 |
| V-6 | 비전 veto **하향 전용** — 어떤 입력도 점수를 올리지 않음(min cap 구조) | 순수 `vision_veto` 단위테스트(올림 불가 invariant) | **pod-free** |
| V-7 | **객관성** — 비전 출력에 사람 점수 라벨 ground truth 0, 점수 필드 누출 0. **MEDIUM-1: raw 파일 grep 아닌 `build_schema()['properties']` + `VisionVerdict` dataclass 내성검사**(_SCORE_PATTERN 존재는 위반 아님; overall_qualitative 복사 금지) | 스키마/데이터클래스 내성검사 + `_SCORE_PATTERN` leak 거부 단위테스트 | **pod-free** |
| V-8 | Mode3 미보유 → confident 점수 억제 + '기준 없음' | 3분기 라우팅 단위테스트(recognizer category ↔ ipsf_map 정합 A2) | **pod-free** |
| V-9 | veto 무음실패 방지 — try/except 가 게이트를 silent no-op 안 함 | WARNING + audit 필드(visionVeto.status enum) 단위테스트 (Pitfall 5) | **pod-free** |
| V-10 | **veto no-op 차단(HIGH-1)** — Phase17 vision OFF + veto ON 이면 keep_local_video=True 라 adapter 가 non-None local_video_path 수신. visionVeto.status ∈ {applied, not_applicable, disabled, skipped_error, missing_local_video} 가 veto 실행을 증명(부재≠실행) | keep_local_video 게이트 + status enum 단위테스트 (mocked adapter) | **pod-free** |
| V-11 | **self-check ≠ approval(HIGH-2)** — `--self-check` 는 phase gate 아님(approval 기록 금지); `--phase-gate`/기본 은 baseline 자산 부재 시 fail-closed non-zero | argparse 모드 분기 단위 + terminal evidence(eval20_serial_baseline.json + eval20_gate_report.json) 존재 검사 | pod-free(모드 분기) / Pod(실 evidence) |
| V-12 | **derive fail-closed(HIGH-3)** — sensitivity TODO/누락 video key/2-bucket(must_drop+must_stay_high) 미달 시 cap 도출 거부 + SEVERITY_CAP 미변경. phase18 6페어 derive 입력 금지. cap 박제 시 SEVERITY_CAP_PROVENANCE.sensitivity_manifest_sha256 실 sha + phase18_pairs_used_for_derivation=False | derive_caps fail-closed 단위 + provenance 일관성 단위테스트 | **pod-free**(가드) / Pod(실 도출) |
| V-13 | **캐시 prompt/schema 버전(MEDIUM-2)** — VisionVetoCache 키에 PROMPT_VERSION/SCHEMA_VERSION 포함, 변경 시 stale verdict 무효화(recognizer 캐시 키 재사용 금지) | PROMPT_VERSION monkeypatch → cache-miss 단위테스트 | **pod-free** |

---

## Per-Task Verification Map

> V-1~V-13 를 task 에 매핑. pod-free task 먼저, V-1/2/3/5 는 terminal Pod `--phase-gate` (fail-closed).

| Task ID | Plan | Wave | Requirement | Threat Ref | Test Type | Automated Command | Pod | Status |
|---------|------|------|-------------|------------|-----------|-------------------|-----|--------|
| 20-01-T1 | 20-01 | 1 | SCORE-08, TRUST-08 | T-20-01/02/02b/03 | unit (property) | `pytest tests/test_vision_veto.py -x -q` | pod-free | ⬜ pending |
| 20-02-T1 | 20-02 | 1 | SCORE-08, TRUST-06/08 | T-20-04/04b/08 | unit (mocked) | `pytest tests/test_gemini_vision_scorer.py -x -q` | pod-free | ⬜ pending |
| 20-03-T1 | 20-03 | 2 | SCORE-08, TRUST-08 | T-20-09/09b/10 | unit (mocked) | `pytest tests/test_pipeline_mode3.py -k "vision_veto or keep_local_video" -x -q` | pod-free | ⬜ pending |
| 20-03-T2 | 20-03 | 2 | TRUST-08 | T-20-13 | typecheck | `cd app && npm run typecheck` | pod-free | ⬜ pending |
| 20-03-T3 | 20-03 | 2 | TRUST-06/07 | T-20-11/12/14 | unit (mocked) | `pytest tests/test_pipeline_mode3.py -k "branch3 or reference_free or recognizer_category or line_dim_determinism" -x -q` | pod-free | ⬜ pending |
| 20-04-T1 | 20-04 | 3 | SCORE-09 | T-20-15/15b/18 | self-check | `python evals/phase20/assert_baseline_v2.py --self-check` | pod-free | ⬜ pending |
| 20-04-T2 | 20-04 | 3 | SCORE-09/08, TRUST-06 | T-20-15/16/18 | phase-gate | `python evals/phase20/assert_baseline_v2.py --phase-gate` | **Pod** TERMINAL | ⬜ pending |

| V-ID → Task | V-1→20-04-T2 · V-2→20-04-T2 · V-3→20-04-T2 · V-4→20-02-T1/20-03-T3(cache)+20-04-T2(real) · V-5→20-04-T2 · V-6→20-01-T1 · V-7→20-02-T1 · V-8→20-03-T3 · V-9→20-03-T1 · V-10→20-03-T1 · V-11→20-04-T1/T2 · V-12→20-04-T1 · V-13→20-02-T1 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/` vision_veto 단위 픽스처(mocked Gemini 어댑터 — 실 API/Pod 무관)
- [ ] 객관성 내성검사 픽스처(build_schema/dataclass — 점수 필드 0, raw grep 아님 — MEDIUM-1)
- [ ] keep_local_video 게이트 + visionVeto status enum 픽스처(HIGH-1)

*기존 `backend/evals/phase18/`(pairs/baseline/assert_baseline.py) + `sweep_phase15.py` 재사용 — 신규 인프라 최소.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 실 GPU 정량 regression(V-1/2/3) | SCORE-08/09 | RTMW GPU 필요(Pod down) | Pod 재개 후 `sweep_phase15.py --mode mode1 --pair-sequential` 순차 → `assert_baseline_v2.py --phase-gate`(fail-closed) |
| sensitivity 일반화(V-5) | TRUST-06 | 미보유+above-cutoff 자산 수집 선행(2-bucket) | 별도 셋 수집(sensitivity.yaml TODO→실 video_key) 후 sweep |

*나머지 V-4(캐시)/V-6/V-7/V-8/V-9/V-10/V-12/V-13 는 pod-free 자동 검증. V-11 은 모드분기 pod-free + 실 evidence Pod.*

---

## Validation Sign-Off

- [ ] pod-free task 전부 `<automated>` verify 보유(V-6~V-10/V-12/V-13)
- [ ] Pod-dependent V-1/2/3/5 는 terminal `--phase-gate` (fail-closed, silent skip + self-check false-green 금지 — HIGH-2)
- [ ] 객관성 gate(V-7 내성검사) + 하향전용 invariant(V-6) + veto no-op 차단(V-10) Wave 0 커버
- [ ] derive fail-closed(V-12) + 캐시 prompt/schema 버전(V-13) 커버
- [ ] eval 동시 실행 금지(순차만) 박제
- [ ] `nyquist_compliant: true` (planner task 매핑 후)

**Approval:** pending
