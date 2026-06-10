# Phase 09: ForceDirectionPattern + 실패 원인 후보 3개 - Discussion Log

**Discussed:** 2026-06-10
**Mode:** discuss-phase (default, autonomous mode after first turn)

> User triggered autonomous mode after gray-area selection: "work without stopping
> for clarifying questions. Make reasonable calls and continue; they'll redirect."
> Claude made discretionary calls for all 4 areas based on prior CONTEXTs (06/07/08/8.1),
> research 02, REQUIREMENTS, ROADMAP, and code state.

---

## Pre-discussion context loaded

- `.planning/STATE.md` — Phase 8.1 종료 ready, Phase 9 평행 진입 박제, milestone v1.5
- `.planning/REQUIREMENTS.md` — FORCE-01 (Phase 8 신호 + Phase 9 패턴 + Top-3 카드), FEED-02 (실패 원인 카드 → 부위별 언어 → 보완 동작 순서)
- `.planning/ROADMAP.md` §Phase 9 (line 277-291) — 4 SC + raw signal only guard (Codex C-M4 / Phase 8.1 D-05)
- `.planning/phases/08-jerk-jitter/08-CONTEXT.md` — D-08-A2 Layer 1/Layer 2 분리 + D-08-C3 module 분리 패턴
- `.planning/phases/08.1-axis-metric-redesign/08.1-CONTEXT.md` — D-01 distance 필드 제거 + D-03 IPSF tolerance 20° + **D-05 raw signal only guard**
- `.planning/phases/08.1-axis-metric-redesign/08.1-SWEEP-EVIDENCE.md` §11 — sensitivity 5/5 PASS
- `.planning/phases/07-difference-classification/07-CONTEXT.md` — D-07-B1 캔드 우선 + D-07-D 카피 톤 룰 + 금지 표현 grep gate
- `.planning/phases/12_5-ui-transparency/12.5-CONTEXT.md` — mode 분기 (mode1 / mode3_first / mode3_progress) 패턴
- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §4/§7/§8/§10 — 패턴 enum + 신호 표 + 알고리즘 초안 + 카피 톤
- `app/src/types/analysis.ts` (현 contract) — `ForceSignalsReport` + Phase 8/8.1 metric 박제 확인
- `backend/shared/python/sunity_shared/analysis/force_signals.py` — 1762줄, raw signal 산출 + 임계 모듈 상수 박제
- `backend/judging_data/tilt_thresholds.yaml` — `ipsf_tolerance.tolerance_deg=20.0` / `major_fault_deg=40.0` (IPSF Aerial Pole CoP Page 63 S55 Iron X citation)

---

## Gray areas presented

Phase 9 (ForceDirectionPattern + 실패 원인 후보 3개) 어떤 영역을 논의할까요?
(Phase 8/8.1 산출 위 추론 레이어 — raw signal only)

multiSelect=true, 4 options 박제:

1. Pattern inference 룰 (5종)
2. Top-3 ranking + 후보 pool
3. Layer 2 Gemini 사용 여부
4. 카드 schema + 노출 깊이

---

## User selection

**선택: 4/4 모두** ("Pattern inference 룰 (5종), Top-3 ranking + 후보 pool, Layer 2 Gemini 사용 여부, 카드 schema + 노출 깊이")

이후 사용자가 autonomous 모드 진입 — "work without stopping for clarifying questions" 박제.
Claude 가 prior context + research 02 + 메모리 invariants 위에 reasonable call 박제 후 CONTEXT.md 단일 박제.

---

## (A) Pattern inference 룰 (5종)

**Claude's reasoning**:
- research §4.2 영상 신호 8행 표 → 5 pattern 매핑 박제 source.
- research §8 의 `inferForceDirectionPattern` 코드 초안 4 detection function + base_confidence 박제.
- **scope 축소**: Phase 8 산출 `ForceSignalsReport` 가 직접 노출하는 6 signal 만 v1 박제 — 절대 joint angle 패턴 (어깨 elevation / elbow lock) 은 features.py angles_tj 통합 필요 → v2 deferred.
- **Tilt 임계 source**: Phase 8.1 D-03 의 IPSF tolerance 20° (`tilt_thresholds.yaml::ipsf_tolerance.tolerance_deg`) 재사용. axis severity calibration (medium=63°/82°) 과 분리 — severity 직접 trust 차단 정합.
- **axis warnings 무시 룰**: `axis_metric_transitional` / `tilt_unavailable` / `tilt_thresholds_fallback` 포함 시 raw tilt 도 무시 (Phase 8.1 sensitivity gate 미통과 신호).

**Locked decisions**: D-09-A1 (6 signal v1 scope) / D-09-A2 (raw signal only guard + IPSF tolerance 20°) / D-09-A3 (phase 별 multiple finding) / D-09-A4 (phase 미인식 fallback) / D-09-A5 (confidence base × phase_metric_confidence_factor).

**Deferred**: 어깨 elevation / elbow lock 절대 joint angle 패턴 (v2).

---

## (B) Top-3 ranking + 후보 pool

**Claude's reasoning**:
- 후보 pool = 6 signal × 5 phase = 최대 30 candidate. detection threshold 미통과 시 candidate 생성 X (fabrication 금지).
- 정렬 = `score = confidence × signal_weight` — signal_weight 박제 (axis_tilt=1.0 / pelvis_drop=1.0 / late_contact=0.95 / abnormal_release=1.1 release 직접 신호 priority / high_jerk=0.85 / high_jitter=0.80 gross signal).
- tie-break = phase priority (lock > hold > transition > final_shape > entry) → signal priority (axis > contact > stability) → confidence.
- 후보 부족 (0~2) 시 → 빈 슬롯 pad X, findings list 0~3 길이.
- 0 finding 시 → `overallConfidence='low'` + 카피 "분명한 힘 흐름 이슈 신호 없음, 강사 확인 권유" — fabrication 금지 정합 ([[mode3-progress-not-similarity]] + [[analysis-objectivity-no-human-scores]]).
- **Pattern 중복 cap**: 동일 pattern 다중 finding 시 1개만 emit (UX 다양성). 단 phase 다른 동일 pattern 인정.

**Locked decisions**: D-09-B1 (30 max candidate pool) / D-09-B2 (score = confidence × signal_weight) / D-09-B3 (tie-break phase > signal > confidence) / D-09-B4 (후보 부족 시 길이 0~3) / D-09-B5 (pattern 중복 cap).

---

## (C) Layer 2 Gemini 사용 여부

**Claude's reasoning**:
- Phase 11 책임 = "Gemini 자연어 번역만, 좌표·판단·점수 출력 금지" (ROADMAP Phase 11 SC #3). Phase 9 가 Gemini 호출해 패턴 분류 시 "판단 출력" 금지 위반.
- Phase 9 추론 = deterministic + 객관 임계 (IPSF tolerance + Phase 8 fixed threshold) 박제. 비결정적 LLM 으로 객관성 훼손 X.
- Phase 8 Layer 2 (Gemini key_moment timestamp 보강) 은 phase 분할 정확도 향상 → 패턴 추론 자체 X. Phase 9 는 phaseBoundaries 입력으로 받아 신호 처리만 → Layer 2 영향 X (자동 정합).
- motion_id 인식 시 confidence × 1.05 보강 (max 1.0 cap), 미인식 시 보강 X (motion-agnostic Layer 1 단독 박제 — Phase 8 D-08-A4 정합).

**Locked decisions**: D-09-C1 (Layer 1 단독 영구 차단) / D-09-C2 (motion_id 인식 시 confidence 보강 × 1.05) / D-09-C3 (자연어 번역은 Phase 11 책임).

---

## (D) 카드 schema + 노출 깊이

**Claude's reasoning**:
- ForcePatternFinding 8 필드 박제 (pattern / phase / sourceSignal / reason EN / interpretation KO canned / confidence / jointHint / warnings).
- ForcePatternInference 5 필드 박제 (version / findings 0~3 / overallConfidence / warnings / modeContext).
- **interpretation canned**: 6 sourceSignal × 3 modeContext = 18 카피 박제. phase 분기 X (v1 단순화). 위치 = 신설 `force_pattern_copy.py` (Phase 7 `copy_templates.py` 패턴 정합).
- **금지 표현 grep gate**: research §10.2 6종 + 신규 4종 (근육 힘 방향 확정 / 힘이 정확히 / 프로보다 못합 / 수치 단독 감점). 단위 test 회귀 차단.
- **evidence raw 값 노출 X**: interpretation = canned KO 만. raw shoulder_tilt 값 등 수치 단독 노출은 Phase 12 책임 (실측 각도 표시).
- **UI hint 없음**: ROADMAP Phase 9 entry 명시 X. 결과 화면 노출 = Phase 12 / 12.5 책임 — Phase 9 = backend canned data 박제만.
- **mode 분기**: Phase 12.5 `_select_mode3_subcontext` 패턴 재사용 가능 — planner 확인.

**Locked decisions**: D-09-D1 (ForcePatternFinding 8 필드 + ForcePatternInference 5 필드) / D-09-D2 (18 canned, mode × signal) / D-09-D3 (10종 금지 grep gate) / D-09-D4 (raw 수치 노출 X — Phase 12 책임) / D-09-D5 (UI hint 없음) / D-09-D6 (mode 분기 = Phase 12.5 패턴 재사용).

---

## (E) Plan 구조 (D-09-E1/E2/E3)

**Claude's reasoning** (사용자 명시 정합 — "RunPod 불필요 Wave 0/1 = pure-function"):
- 2 wave 박제 — Phase 8.1 D-06 패턴 정합 (wave 단위 위험 차원 분리).
  - Wave 0 = schema lockstep (TS + Python + docs §9.5 + Firestore validator + frontend null-guard, 단일 atomic commit)
  - Wave 1 = inference 본체 (force_pattern.py 신설 + Top-3 ranking + 18 canned + pipeline wiring + 단위 test + 금지 표현 grep gate)
- Wave 2 production sweep 불요 — RunPod GPU 무관 + Phase 8.1 sensitivity gate 8/8 PASS 가 raw signal 정합성 검증 완료 + Phase 11 / Phase 15 통합 시점 자연 검증.

**Locked decisions**: D-09-E1 (2 wave 구조) / D-09-E2 (Wave 2 sweep deferred — Phase 11/15 자연 검증) / D-09-E3 (Wave 1 종료 후 belle 검수 + cross-AI plan-review 권장).

---

## (Universal) Phase 9 전반 박제

- D-09-U1 (3-way contract lockstep) / D-09-U2 (pure function + numpy only) / D-09-U3 (frozen dataclass + `__post_init__` validator) / D-09-U4 (camelCase 변환) / D-09-U5 (Firestore nested-array 금지 / scoped validator) / D-09-U6 (금지 표현 grep gate 회귀 차단).

---

## Deferred ideas captured

- 어깨 elevation / elbow lock 절대 joint angle 패턴 → v2 or 후속 plan
- Phase-aware canned interpretation mapping → Phase 11 LLM 풍부화 통합
- Confidence factor 정밀화 (joint × phase × technique weighted) → v2
- `rotate` pattern 자동 검출 (회전 angular velocity 산출) → v2
- EMG / 챔피언 근력 통합 → v2 R&D milestone
- 카메라 다각도 시점 → Phase 4 후 v2
- Cross-phase aggregate summary (`patternSummaryByPhase`) → v2 or Phase 12

---

## Scope creep redirected

없음 — 사용자 박제 (raw signal 사용 + RunPod 불필요) 가 Phase 9 SC 정합 + scope 명시 박제.

---

## Open questions for planner / researcher

- `force_pattern.py` 신설 vs `force_signals.py` 확장 — 신설 권장 (D-08-C3 분리 패턴 정합), planner 최종.
- 18 canned KO interpretation 정확한 본문 — plan 단계 belle 검수.
- `jointHint` 부위 어휘 매핑 (sourceSignal → 부위 키워드) — researcher / planner.
- `phase_metric_confidence_factor` 산식 디테일 (min vs avg vs weighted) — planner.
- Firestore scoped validator 정확한 화이트리스트 — planner.
- pipeline `_process` 호출 위치 — `compute_force_signals` 직후 권장.
- `modeContext` 산출 룰 (mode3 first vs progress) — Phase 12.5 helper 재사용 가능 여부 planner 확인.

---

*Phase: 09-forcedirectionpattern-3*
*Context gathered: 2026-06-10*
*Mode: autonomous (after gray-area selection)*
