# PLAN-CHECK — Phase 17: Gemini Vision Integration — 4 영역 통합

> Goal-backward verification. Adversarial stance — plans are flawed until proven.
> 작성일: 2026-06-12. 검증자: gsd-plan-checker.

---

## 0. Verdict (한 줄)

**ISSUES FOUND — 1 BLOCKER + 5 WARNING.** Plan 06 의 dependency 누락 (Plan 07이 06에 dep 박혀있는데 06은 04까지만 dep 박힘 → 결과적으로 06 이 04 와 wave 동일로 박혀 G1 객관성 reject regex 가 client.py 박히기 전에 호출 path 발동될 수 있음). 단, 4 영역 핵심 호출 path (A/B/C/D) 의 success criteria 1~4 coverage 는 전부 covered, SC#5 (비용/지연 budget) 은 partial.

---

## 1. Success Criteria Coverage

| SC# | 목표 | Covering Plan(s) | Status | 근거 |
|---|---|---|---|---|
| SC1 | A. Reference 자동 등록 (IPSF + clipRange + checkpoint joint) | **05** | **COVERED** | Plan 05 Task 1+2 가 extract_reference_metadata + 분기 1/2/3 + G3 fallback + Lambda endpoint + Firestore upsert 박제. ReferenceRegistration schema (AI-SPEC §4b) 그대로 박힘. |
| SC2 | B. 코칭 멘트 품질 (RTMW 수치 + Gemini Vision 결합 + 강사 검수 통과) | **04** | **COVERED** | Plan 04 Task 1 의 GeminiCoachWriter + 부위별 용어 14개 화이트리스트 + coach_note 3 어휘 강제 + blocklist + Cerebras dual-track + LLM judge (Plan 06 F1 flywheel) 박제. |
| SC3 | C. Finding 장면 인식 (high_score_finding_gated warning 감소) | **02** | **COVERED** | Plan 02 Task 1+2 의 find_scene_flags + G4 정은지 가드 + Firestore geminiC + wave 1 wiring 박제. 단 "high_score_finding_gated warning 감소" 의 측정 path (현 비율 → 목표 비율) 는 직접 박혀있지 않음 — ⚠️ WARN-3 참조. |
| SC4 | D-v1. KeypointReport overlay 품질 (`KeypointReport.confidence < 0.5` 비율 < 5%, mirror hint audit) | **03**, **07** | **COVERED** | Plan 03 의 augment_low_confidence + G5 좌표 환각 가드 + **KeypointReport.data/confidence 보강 (B2 정합)** + Plan 07 의 신규 6 motion mock e2e 분석 (`KeypointReport.confidence` field — `data` 가 아님, `assemble.py:393-448` 검증 — < 0.5 비율 < 5% 검증). ROADMAP "현 신규 6 = 13-35% → < 5%" 직격. **D-v2 deferred (별도 후속 plan)**: 좌표계 계약 박은 후 coco_array 주입 + DTW/KISMAM/dim_scores 재계산으로 점수 회복. |
| SC5 | 비용/지연 budget (< $0.20 / call, latency 추가 < 15s) | **06** (간접), **AI-SPEC §4b** | **PARTIAL** | Plan 06 Task 1 의 Phoenix 자동 계측 + Promptfoo assertion E8 (p95 latency ≤ 40s, per-call cost ≤ $0.08) 박힘. **단 ROADMAP 의 임계값 ("latency 추가 < 15s") vs AI-SPEC §4b 박제값 ("4 영역 병렬 30~40s") 불일치** — ⚠️ WARN-1 참조. |

**Phase goal 달성 가능성**: 5 SC 중 4 COVERED + 1 PARTIAL. 핵심 분석 path 는 박힘 박힘 — phase goal "분석 정확도 + 사용자 가치 본질 강화" 의 4 영역 wiring 자체는 검증 통과. SC5 의 임계값 불일치는 BLOCKER 아닌 WARNING (실측 후 조정 가능).

---

## 2. AI-SPEC E1~E8 Dimension Coverage

| E# | Dimension | Plan 박힌 위치 | Status |
|---|---|---|---|
| E1 | 객관성 가드 (reject regex) | Plan 01 guardrails.py + Plan 06 assertion objectivity_reject.py | ✅ Covered |
| E2 | IPSF 명칭/Criteria 정합 | Plan 05 ipsf_whitelist.json + Plan 06 assertion ipsf_routing.py | ✅ Covered |
| E3 | 학원 용어 3분기 라우팅 | Plan 05 _route_branch + studio_branch2_aliases.json + Plan 06 assertion | ✅ Covered |
| E4 | 코칭 톤 (강사 보조 + 원인-해결) | Plan 04 _validate_tone (부위별 용어 14 + coach_note 3 어휘 + blocklist) + Plan 06 LLM judge | ✅ Covered |
| E5 | Finding flag 정확도 ≥ 0.95 | Plan 02 G4 + Plan 06 promptfoo assertion + auto-escalation GEMINI_C_MODEL_OVERRIDE | ✅ Covered |
| E6 | 정은지 영상 hard gate (A+B+C 합산) | Plan 02 G4 + Plan 05 분기 1/2 + Plan 06 dataset 5건 hard gate | ⚠️ Partial — B 영역의 정은지 spot check binary pass 박는 task 가 명시 안 됨 (WARN-2) |
| E7 | 영역 D 좌표 인접 frame 거리 < 0.15 | Plan 03 G5 가드 + Plan 07 mock e2e | ✅ Covered |
| E8 | Schema 검증 통과율 + latency p95 | Plan 06 Phoenix M3 + Promptfoo E8 게이트 | ✅ Covered |

---

## 3. AI-SPEC G1~G6 Guardrail Coverage

| G# | Guardrail | Plan 박힌 위치 | Status |
|---|---|---|---|
| G1 | 객관성 reject regex (hard fail) | Plan 01 guardrails.py + Plan 06 span event | ✅ Covered |
| G2 | Pydantic schema 실패 graceful | Plan 01 client.py retry × 1 + Plan 04 _validate_tone retry + Plan 06 span event | ✅ Covered |
| G3 | IPSF 화이트리스트 미매치 fallback | Plan 05 _route_branch + isActive=false + reviewRequired=True | ✅ Covered |
| G4 | 정은지 occlusion_severe FP block | Plan 02 G4 가드 (is_reference + occlusion_severe 동시) + Plan 06 span event | ✅ Covered |
| G5 | 영역 D 좌표 환각 block | Plan 03 _check_neighbor_distance + L2 ≥ 0.15 폐기 | ✅ Covered |
| G6 | API quota/5xx exhaustion graceful | Plan 01 client.py 4xx 즉시 None + 5xx retry × 1 | ✅ Covered |

**6/6 guardrail 박혀있음.** G1/G4 는 hard block (graceful X), G2/G3/G5/G6 는 graceful fallback — AI-SPEC §6 정합.

---

## 4. Critical Failure Modes (AI-SPEC §1) Mitigation

| CFM# | Failure Mode | Mitigation 박힌 위치 | Status |
|---|---|---|---|
| 1 | 객관성 위반 (좌표/점수/사람 판단) | Plan 01 G1 + Plan 06 dataset E1=100% PR block | ✅ Mitigated |
| 2 | 고수 위양성 (정은지 영상 fallback) | Plan 02 G4 + Plan 05 G3 + Plan 06 E6 dataset 5건 hard gate | ✅ Mitigated |
| 3 | 강사 대체 톤 (단정/지시형) | Plan 04 blocklist (이렇게 하세요/틀렸습니다/당신은) + coach_note 3 어휘 강제 | ✅ Mitigated |
| 4 | IPSF 명칭/Criteria 환각 | Plan 05 ipsf_whitelist.json + G3 fallback + checkpointJoints Pydantic Literal | ✅ Mitigated |
| 5 | 학원 용어 ↔ IPSF 매핑 실패 | Plan 05 분기 1/2/3 라우팅 + studio_branch2_aliases.json (13개 AKA + 3개 분기 2 박제) | ✅ Mitigated |

**5/5 critical failure mode 박혀있음.**

---

## 5. Wave 순서 정합성 + Dependency 그래프

```
Wave 1: 01 (deps=[])                                     ✓ 베이스 — schemas + client + guardrails
Wave 2: 02 (deps=[01])                                   ✓ 영역 C (gen client + schema 의존)
Wave 3: 03 (deps=[01, 02])                               ✓ 영역 D (C 의 occlusion_severe 게이트 의존)
Wave 4: 04 (deps=[01, 02, 03])                           ⚠ 영역 B (사실 02/03 의존 필요 없음 — WARN-4)
Wave 5: 05 (deps=[01, 02, 03, 04])                       ⚠ 영역 A (사실 02/03/04 의존 필요 없음 — WARN-4)
Wave 6: 06 (deps=[01, 02, 03, 04, 05])                   ⚠ Eval — 단 06 이 04 의 client.py 갱신과 동거 (WARN-5)
Wave 7: 07 (deps=[05, 06])                               ✓ 신규 6 재활성화 (endpoint + Promptfoo)
```

**File overlap 검사 (sequential 보장):**

| File | 박는 plan(s) | 보장? |
|---|---|---|
| backend/functions/pipeline/app.py | 02 → 03 → 04 | ✅ Wave 순차 보장 (02 wave 1 → 03 wave 2 → 04 wave 3 직렬) |
| backend/shared/python/sunity_shared/firestore_admin.py | 02 → 03 → 04 → 05 → 06 | ✅ Wave 순차 (각 wave 가 kwarg 추가 — backward compat) |
| backend/shared/python/sunity_shared/gemini/client.py | 01 (생성) → 06 (span event 박제 갱신) | ⚠ Wave 1 → Wave 6 — OK 단 06 의 다른 task 와 동거 (BLOCKER-1) |
| backend/shared/python/sunity_shared/gemini/scene_finder.py | 02 (생성) → 06 (span event 갱신) | ✅ Wave 2 → Wave 6 직렬 |
| backend/shared/python/sunity_shared/gemini/coach_writer_v2.py | 04 (생성) → 06 (span event 갱신) | ✅ Wave 4 → Wave 6 직렬 |
| backend/template.yaml | 05 (단독) | ✅ 단일 plan |
| backend/scripts/extract_reference_angles.py | 07 (단독) | ✅ 단일 plan |

**모듈 dep 검사:**

| 모듈 | Importer plan(s) | Provider plan(s) | OK? |
|---|---|---|---|
| sunity_shared.gemini.{schemas,client,guardrails} | 02,03,04,05,06 | 01 | ✅ 01 이 wave 1 — 모든 후속 import 가능 |
| sunity_shared.gemini.scene_finder.find_scene_flags | 03 (occlusion_severe 게이트), 04 (직접 import X) | 02 | ✅ 02 wave 2 → 03 wave 3 |
| sunity_shared.gemini.coach_writer_v2.GeminiCoachWriter | 04 self | 04 | ✅ self-contained |
| sunity_shared.gemini.reference_extractor.extract_reference_metadata | 05 self + 07 자동화 스크립트 | 05 | ✅ 05 wave 5 → 07 wave 7 |
| sunity_shared.eval.* (phoenix_setup, llm_judge, sampling) | 06 self | 06 | ✅ |

**결론**: file overlap 의 sequential 보장은 wave 순서로 박혀있다. 단 BLOCKER-1 + WARN-4 + WARN-5 박혀있다 (아래 §7 참조).

---

## 6. RESEARCH §6 "신규 6 motion 재활성화" (F4 UAT finding 해소) Path

| 단계 | Plan 박힌 위치 | Status |
|---|---|---|
| 1. 영역 A endpoint 호출 | Plan 05 Task 2 (Lambda) + Plan 07 Task 1 (자동화 스크립트) | ✅ |
| 2. belle 검수 (reviewRequired/branch 라벨) | Plan 07 Task 2 checkpoint:human-verify | ✅ |
| 3. RTMW 로 신규 6 영상 angles 재추출 (NLF → _RTMWNlfCompat swap) | Plan 07 Task 1 extract_reference_angles.py swap | ✅ |
| 4. Firestore seed 재실행 (angles + bodyComparisonSourcePose + geminiA) | Plan 07 Task 1 reactivate_new6_motions.py | ✅ |
| 5. isActive=true 박는다 | Plan 07 Task 2 checkpoint | ✅ |
| 6. D-v1 영역 (keypoint overlay 보강) 으로 inverted/twist 시각화 정확도 회복 | Plan 03 augment_low_confidence (B2 정합: KeypointReport.data/confidence 만) + Plan 07 mock e2e 분석 (`KeypointReport.confidence < 0.5` 비율 < 5% — `data` 가 아닌 `confidence` field) | ✅ (단 점수 회복은 D-v2 후속 plan deferred) |

**6/6 단계 박혀있음.** F4 finding 해소 path 가 PLAN 합으로 완성됨.

---

## 7. Issues 박혀있음

### BLOCKER-1 — Plan 06 의 client.py 갱신과 동시작업 race

**Dimension**: dependency_correctness + key_links_planned
**Severity**: blocker

**Description**: Plan 06 Task 1 이 `backend/shared/python/sunity_shared/gemini/client.py` 를 갱신해서 G1/G2/G4/G5 span event 박는다 (`add_event`). 단 이 변경은 Plan 01 의 client.py 와 다른 task 가 박혀있다. Plan 06 이 wave 6 — 즉 Plan 02/03/04 의 호출 path 가 wave 2/3/4 에 박힌 후 wave 6 에서 client.py 가 갱신될 때 **이미 박혀있는 G1 ValueError raise 자체는 동작** — 단 Phoenix span event 가 박힌 그 record 는 wave 2/3/4 에서 발동된 호출에는 없음. 즉 production 진입 직후의 모든 호출이 trace 없이 발동.

**핵심 우려**: SC5 (비용/지연 budget 측정) 가 Plan 06 wiring 전에 호출되는 wave 2/3/4 발동 시 측정 불가. 5 SC 중 SC5 의 measurement 가 wave 6 까지 박혀야 하므로 — 실제 production 진입 (Wave 7 신규 6 재활성화) 시 첫 호출들은 trace 누락.

**Fix hint**:
- (옵션 A) Plan 06 의 Phoenix bootstrap + span event 박제 부분을 **Wave 1 박는 Plan 01 에 흡수** (phoenix_setup 만 wave 1, eval/promptfoo/sampling 은 wave 6 유지). 그러면 wave 2 의 첫 호출부터 trace 박힘.
- (옵션 B) Plan 02/03/04 의 task 안에 span event helper 호출 stub 박제 (no-op if phoenix_setup not bootstrapped) → Wave 6 에서 phoenix 활성화 시 자동 박힘.

**의의**: SC5 가 PARTIAL 인 부분 직격. Phase goal "비용/지연 budget" 의 측정 path 가 wave 6 까지 비어있음.

---

### WARN-1 — ROADMAP SC5 ("latency 추가 < 15s") vs AI-SPEC §4b ("4 영역 병렬 30~40s") 불일치

**Dimension**: context_compliance + scope_reduction
**Severity**: warning

**Description**: ROADMAP.md Success #5 박제 — "분석 완료 latency 추가 < 15s". AI-SPEC §4b "Latency 예산" 박제 — "client.aio + asyncio.gather 로 A+C 병렬 / B+D 병렬 = 30~40초 박제. Lambda pipeline 900s timeout 정합." Plan 06 의 Promptfoo assertion E8 = "p95 latency ≤ 40s". **15s vs 40s = 2.6배 박힘 박힘.** 즉 plan-checker 입장에서는 plans 가 박은 임계값 (40s) 이 phase goal SC5 (15s) 와 불일치.

**Fix hint**:
- belle 결정 필요 — ROADMAP SC5 15s 수정 (실측 후 30~40s 가 현실) 또는 AI-SPEC §4b 박제 latency 축소 (Flash-only 영역 C 만 호출하거나, B/D 비동기 fire-and-forget). 단 후자는 분석 정확도 영향.
- 본 plan-checker 는 BLOCKER 로 박지 않음 — SC5 자체가 belle "비용 신경X but 효율" 박제 정합이라 실측 후 belle 가 임계값 조정 가능. 단 belle 가 명시적으로 15s hard gate 박은 게 아니면.

---

### WARN-2 — E6 (정은지 hard gate) 의 영역 B binary pass 박는 task 명시 안 됨

**Dimension**: requirement_coverage + verification_derivation
**Severity**: warning

**Description**: AI-SPEC §5 E6 박제 — "정은지 영상 5~10건 전체에서 (a) 영역 A IPSF 매핑 OR 분기 2 등록, (b) 영역 B 코칭 멘트가 강사 보조 톤 + 원인-해결 PASS, (c) 영역 C occlusion_severe=False & camera_angle_problematic=False." Plan 06 dataset 의 정은지 5건 박혔지만 (b) 영역 B 의 belle binary 검수 task 가 명시 안 됨. Plan 06 Task 3 의 reference_dataset.yaml entry 30 중 정은지 5건은 박힘 — 단 belle binary 라벨 박는 timing 이 미정 (labels.json 박은 timeline 박혀있지만 25건 placeholder TODO).

**Fix hint**:
- Plan 06 Task 3 의 labels.json 박을 때 영역 B 정은지 5건 라벨링도 (a)/(b)/(c) 박제 명시. belle 가 PR 로 라벨링 추가하는 path 가 박힘 — 단 검수 timing 이 wave 7 의 mock e2e 와 동시.
- 또는 Plan 07 의 checkpoint:human-verify 안에 E6 (a)+(b)+(c) 합산 PASS 박는 게이트 명시.

---

### WARN-3 — SC3 "high_score_finding_gated warning 감소" 의 측정 path 박혀있지 않음

**Dimension**: requirement_coverage
**Severity**: warning

**Description**: ROADMAP SC3 박제 — "forcePatternInference.findings[] 가 Gemini Vision 의 장면 정보 입력으로 강화. high_score_finding_gated warning 감소." Plan 02 의 find_scene_flags 가 4 flag 박는 부분은 박힘 — 단 **현 high_score_finding_gated 비율 vs Phase 17 후 비율 측정 path 가 박혀있지 않음**. Phase 12 UAT 산출 본 (referenceKeypointReport) 에 박혀있는지 확인 필요. Plan 07 의 mock e2e 분석 success_criteria 에는 "not_pole_motion 폴백 0건" 박혀있고 confidence < 0.5 비율 박혀있지만 high_score_finding_gated warning 비율 박혀있지 않음.

**Fix hint**:
- Plan 07 Task 2 checkpoint:human-verify 의 how-to-verify 에 "high_score_finding_gated warning 비율 측정" 박제 (Phase 12 baseline 과 비교).
- 또는 Plan 02 의 success_criteria 에 "find_scene_flags 박힌 후 forcePatternInference.findings[] 의 게이트 통과율 측정" 박제.

---

### WARN-4 — Plan 04 와 05 의 depends_on 과잉 박힘

**Dimension**: dependency_correctness
**Severity**: warning

**Description**: Plan 04 (영역 B) 의 depends_on=[01, 02, 03] 박힘. 단 영역 B 의 실제 모듈 의존은 [01] 만 (GeminiVisionCall + CoachPayload schema 의존). 02 (영역 C) / 03 (영역 D) 는 _process 의 wave 순서 박힘 외 module-level 의존 0. Plan 05 (영역 A) 의 depends_on=[01, 02, 03, 04] 박힘 — 단 영역 A 는 Lambda 별도 path (RESEARCH §1 박제), 영역 C/D/B 와 module-level 의존 0.

**Impact**: 병렬 실행 path 박혀있는데 over-sequential 박힘 — 실제로는 Plan 02/03/04/05 가 모두 Plan 01 직후 병렬 실행 가능 (단 pipeline/app.py 와 firestore_admin.py 의 file overlap 으로 sequential merge 필요). wave 가 깊어지면서 phase 전체 latency 늘어남.

**Fix hint**:
- Plan 04 depends_on → [01]
- Plan 05 depends_on → [01]
- 단 pipeline/app.py + firestore_admin.py 의 file overlap 은 wave 안에서 sequential merge 박제 (planner 가 wave 같은 wave 내 다른 plan 의 file overlap 정합 박힘 박힘).
- 또는 그대로 두기 (보수적 sequential — 단 phase 전체 latency 증가).

---

### WARN-5 — Plan 06 의 scope 과대 + 3 task × 다영역 (eval + judge + sampling + dataset + assertion + Phoenix wiring)

**Dimension**: scope_sanity
**Severity**: warning

**Description**: Plan 06 의 files_modified = 14개 (gemini/client.py + scene_finder.py + coach_writer_v2.py + eval/* 4 + evals/phase17/* 5 + tests/eval/* 3). AI-SPEC §5/§6/§7 의 박제가 한 plan 에 박혀있어서 scope_sanity 의 4 task threshold (warning) + 15 files threshold (blocker) 박힘 박힘 박힘 박힘. Plan 06 의 task 는 3 (Phoenix bootstrap / LLM judge + sampling / Promptfoo + dataset + assertion) — task 개수는 OK 단 files = 14 = warning threshold.

**Impact**: 실행 중 context degradation 가능. Phoenix + judge + sampling 박는 게 한 plan 에 박혀있어서 wave 6 의 execute-plan 이 한 번에 14 file 박는다 — quality 위험.

**Fix hint**:
- Plan 06 을 06A (Phoenix + span event wiring) + 06B (LLM judge + sampling + Promptfoo dataset + assertion) 으로 split 박제.
- BLOCKER-1 fix 와 결합: 06A 의 phoenix bootstrap 만 Wave 1 (Plan 01 흡수) 박제, 06B 의 dataset + assertion 은 wave 6 유지.

---

## 8. Context Compliance (CONTEXT.md 없음)

Phase 17 directory 에 CONTEXT.md 박혀있지 않음 — `gsd-discuss-phase` 단계 skip 박힘. 단 ROADMAP + AI-SPEC + RESEARCH 가 명시적 박제로 박혀있어 정합 검증 가능. AI-SPEC §1~§7 박제 와 plan 의 박힘 박힘 — 위 §2 (E1~E8) + §3 (G1~G6) + §4 (Critical Failure Modes) 박제 통과.

**CONTEXT.md 부재 박혀있는 impact**: belle 의 명시적 user decisions (D-01, D-02, …) 박혀있지 않음. 단 ROADMAP SC1~5 + AI-SPEC §1 critical failure mode + memory 박제 ([[gemini-vision-active-use]], [[analysis-objectivity-no-human-scores]] 등) 가 사실상 user decisions 박은 역할.

---

## 9. CLAUDE.md Compliance (Project Conventions)

| 항목 | Plan 박힌 위치 | OK? |
|---|---|---|
| `.env` 하드코딩 금지 | Plan 05 GEMINI_API_KEY 가 env 또는 Parameter Store fallback 박제 (기존 gemini_moment_extractor.py 패턴 재사용) | ✅ |
| Motion AI 별도 Lambda + S3 (기존 EC2 X) | Plan 05 신규 Lambda + 기존 SAM template 박제 — EC2 박지 않음 | ✅ |
| 작은 단위 작업 | Plan 01~05/07 의 task 2~3개 / 5~8 file — OK. Plan 06 만 14 file (WARN-5) | ⚠️ Plan 06 만 |
| 이모지 금지 | 모든 plan 박혀있는 텍스트에 이모지 없음 박제 | ✅ |
| 한국어 user-facing copy + 영어 identifiers | Pydantic Field description 한국어 박힘, identifier 영어 박힘 — coach_writer.py 패턴 정합 | ✅ |
| Firestore nested array 금지 | Plan 02/03/04/05 의 geminiC/B/D/A 모두 flat object 박제 (RESEARCH §5-3 정합) | ✅ |
| 단일 source of truth (TS + Python contract) | geminiC/B/D/A 박는 Firestore field 가 app/src/types/analysis.ts 에 박혀야 함 — 단 Phase 17 = 백엔드 only (RESEARCH §8), App 변경 0 박힘 | ⚠️ App side 의 AnalysisDoc 박힘 박힘 — App 이 결과 표시 시 geminiC/B 박혀있는 데이터 모르고 진행. 단 RESEARCH §8 박제 "기존 tips[] 그대로 표시 → App 변경 0" 정합 — minor (info, not warning) |

---

## 10. 결론 + Recommendation

**Verdict**: ISSUES FOUND — 1 BLOCKER + 5 WARNING.

**Blocker fix 우선순위** (revision 1 박제):
1. BLOCKER-1 fix — Plan 06 의 phoenix_setup bootstrap 부분만 Wave 1 박는 Plan 01 에 흡수 (또는 별도 wave 1.5 박제). 이게 SC5 measurement 가 wave 2 부터 박히는 path 박제 핵심.

**Warning fix 우선순위** (revision 2 박제, 또는 belle 결정):
1. WARN-1 — ROADMAP SC5 "15s" 가 AI-SPEC "30~40s" 와 불일치. belle 결정 필요 — 15s 수정 또는 latency 축소 path 박제.
2. WARN-2 — E6 정은지 hard gate 의 영역 B 검수 박는 task 명시 (Plan 06 또는 07).
3. WARN-3 — SC3 의 high_score_finding_gated warning 비율 측정 path 박제 (Plan 07 mock e2e).
4. WARN-4 — Plan 04/05 의 depends_on 과잉 박힘 (병렬 가능). 단 file overlap 정합 박힘 — 보수적 sequential 박혀도 OK.
5. WARN-5 — Plan 06 split (Phoenix wiring + eval/judge/dataset). BLOCKER-1 fix 와 결합 가능.

**Goal-backward gate 통과**: ⚠️ **CONDITIONAL** — 5 SC 중 4 covered + 1 partial. BLOCKER-1 fix 박은 후 SC5 measurement path 박혀 production 진입 직후부터 trace 활성. Critical failure modes 5/5 + Guardrails 6/6 + Dimensions 7/8 박혀있음 (E6 partial). 4 영역 wiring 자체는 phase goal 박는다 — 단 측정/관찰 가능성 (observability) 박힘 박힘.

**다음 단계 권고**:
- planner 에게 BLOCKER-1 + WARN-5 (combined fix) 박는 revision 요청.
- belle 결정 박힘 박혀있는 항목 (WARN-1) 은 escalation gate 박제 — belle 확인 후 ROADMAP SC5 임계값 수정 또는 AI-SPEC §4b latency 박제 수정.
- 나머지 WARN-2/3/4 는 revision 1 안에서 fix 가능 (planner judgment).

---

*PLAN-CHECK created: 2026-06-12. 다음 revision 박힘 박힘 박힘 — planner 가 BLOCKER-1 fix + WARN-5 split 박은 후 재검증.*
