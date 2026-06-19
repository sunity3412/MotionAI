---
phase: 20
slug: v2-gemini
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-19
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 출처: 20-RESEARCH.md §Validation Architecture. 임계값 수치는 D-02(curve-fit 금지)에 따라 eval 도출 — 본 문서는 검증 *구조*만.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8 (backend, `backend/requirements-dev.txt`) + Python self-check 하니스 |
| **Config file** | none (backend/tests/ 직접) |
| **Quick run command** | `python -m pytest backend/tests/ -q` + `python backend/evals/phase18/assert_baseline.py` |
| **Full suite command** | `python -m pytest backend/tests/ -q` (회귀 0) |
| **Estimated runtime** | ~수십초 (pod-free 단위/self-check) |

> ⚠️ **정량 regression/generalization eval(`sweep_phase15.py --pair-sequential`)은 RunPod RTMW GPU 필요 — 현재 down.** pod-free 단위테스트(순수 `vision_veto` 로직 + mocked Gemini 어댑터) + self-check 먼저, 실 sweep 은 **terminal gate**(Pod 재개 후, 순차만 — 동시 금지).

---

## Sampling Rate

- **After every task commit:** `python -m pytest backend/tests/ -q` (해당 모듈) + 객관성 grep gate(점수 라벨 누출 0)
- **After every plan wave:** 전체 pytest 회귀 0 + `assert_baseline.py` PASS
- **Before `/gsd-verify-work`:** pod-free suite green + (Pod 재개 시) sweep ↔ baseline 대조
- **Max feedback latency:** ~60s (pod-free)

---

## Validation Architecture (검증해야 할 핵심 성질 — 임계값 수치 아님, 성질)

| ID | 검증 성질 | 방법 | pod 의존 |
|----|----------|------|---------|
| V-1 | kip-up fault 영상이 **≤50** 로 내려감(위양성 해소) | sweep 후 baseline 대조 — known_false_positive → discriminate 전환 | **Pod** |
| V-2 | 변별 4쌍(power-spin/peter-pan/elbow-twist/pdshape) **퇴행 0** (fault<success 유지) | `assert_baseline.py` + sweep 대조 | **Pod** |
| V-3 | 정은지 **정타 95~100 유지** (비전이 깨끗한 자세를 안 깎음) | sweep 정타 영상 | **Pod** |
| V-4 | **결정론** — 같은 입력=같은 점수(캐시가 보장, temp 0 단독 아님 — Pitfall 2) | 같은 영상 N회 + 캐시 키=referenceMotionId 단위테스트 | pod-free(캐시 단위) / Pod(실 점수) |
| V-5 | **일반화** — 미보유 + above-cutoff(고득점이어야 정상) sensitivity 케이스 위양성↔위음성 양방 | sensitivity 셋(별도 수집) sweep | **Pod** + 자산 수집 |
| V-6 | 비전 veto **하향 전용** — 어떤 입력도 점수를 올리지 않음(min cap 구조) | 순수 `vision_veto` 단위테스트(올림 불가 invariant) | **pod-free** |
| V-7 | **객관성** — 비전 출력에 사람 점수 라벨 ground truth 0, 점수 필드 누출 0 | grep gate(`_SCORE_PATTERN` 류) + 스키마 단위테스트 | **pod-free** |
| V-8 | Mode3 미보유 → confident 점수 억제 + '기준 없음' | 3분기 라우팅 단위테스트(recognizer category ↔ ipsf_map 정합 A2) | **pod-free** |
| V-9 | veto 무음실패 방지 — try/except 가 게이트를 silent no-op 안 함 | WARNING + audit 필드(visionVeto) 단위테스트 (Pitfall 5) | **pod-free** |

---

## Per-Task Verification Map

> planner 가 task 분해 후 채움 (V-1~V-9 를 task 에 매핑). pod-free task 먼저, V-1/2/3/5 는 terminal Pod gate.

| Task ID | Plan | Wave | Requirement | Threat Ref | Test Type | Automated Command | Pod | Status |
|---------|------|------|-------------|------------|-----------|-------------------|-----|--------|
| TBD | — | — | SCORE-08/09, TRUST-06/07/08 (권장) | T-20-* | unit / eval | TBD | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/` vision_veto 단위 픽스처(mocked Gemini 어댑터 — 실 API/Pod 무관)
- [ ] 객관성 grep gate 픽스처(점수 라벨 누출 검출)

*기존 `backend/evals/phase18/`(pairs/baseline/assert_baseline.py) + `sweep_phase15.py` 재사용 — 신규 인프라 최소.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 실 GPU 정량 regression(V-1/2/3) | SCORE-08/09 | RTMW GPU 필요(Pod down) | Pod 재개 후 `sweep_phase15.py --mode mode1 --pair-sequential` 순차 → baseline 대조 |
| sensitivity 일반화(V-5) | TRUST-06 | 미보유+above-cutoff 자산 수집 선행 | 별도 셋 수집 후 sweep |

*나머지 V-4(캐시)/V-6/V-7/V-8/V-9 는 pod-free 자동 검증.*

---

## Validation Sign-Off

- [ ] pod-free task 전부 `<automated>` verify 보유(V-6~V-9)
- [ ] Pod-dependent V-1/2/3/5 는 terminal gate 로 명시(silent skip 금지)
- [ ] 객관성 gate(V-7) + 하향전용 invariant(V-6) Wave 0 커버
- [ ] eval 동시 실행 금지(순차만) 박제
- [ ] `nyquist_compliant: true` (planner task 매핑 후)

**Approval:** pending
