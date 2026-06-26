---
phase: quick-260627-afq
plan: 01
subsystem: backend/analysis (judging + recognizer + scoring seam)
tags: [ipsf, objective-knee-extension, recognizer, de-contamination, cross-exclusion]
requires:
  - 24-07 reference_relative per-joint cross-exclusion seam (engine + builder)
  - GeometricCriterion loader + extension_class EXTEND path
provides:
  - 5 moves registered (REGISTERED_MOTIONS + 한/영 alias) → classify recognized
  - 5 objective IPSF knee-extension criteria yaml (EXTEND 180°, ipsf_absolute)
  - motion_ipsf_map criteriaYaml 링크 (copy/coach routing 문서)
  - de-contamination + cross-exclusion 단위테스트 (pod-free 핵심 증거)
affects:
  - GeminiTechniqueRecognizer._build_profile (yaml EXTEND 무릎 → expects_extension)
  - dimensions.extension_deviation / deduction_engine.tally (데이터로 객관 채점 활성)
tech-stack:
  added: []
  patterns: [yaml-data-only, profile-gated-scoring, cross-exclusion]
key-files:
  created:
    - backend/judging_data/criteria/ref-kip-up.yaml
    - backend/judging_data/criteria/ref-power-spin.yaml
    - backend/judging_data/criteria/ref-peter-pan.yaml
    - backend/judging_data/criteria/ref-elbow-twist-sister.yaml
    - backend/judging_data/criteria/ref-pdshape.yaml
    - backend/tests/test_p1_objective_knee_decontamination.py
  modified:
    - backend/shared/python/sunity_shared/analysis/gemini_motion_classifier.py
    - backend/data/motion_ipsf_map.json
    - backend/tests/test_geometric_criterion_loader.py
    - backend/tests/test_gemini_motion_classifier.py
    - backend/tests/test_gemini_motion_classify_spike.py
decisions:
  - "Task 3 보수적: angleSource 유지(no_angle_criterion) + criteriaYaml/sourceNote만 갱신 — 채점은 인식기→yaml 직접(map 미경유), angleSource 는 coach-프롬프트 경로(직교)"
metrics:
  duration: ~40m
  completed: 2026-06-27
---

# Phase quick-260627-afq Plan 01: P1 step 4 — 5동작 등록 + 객관 IPSF 무릎 신전 Summary

엔진 코드 변경 0으로 (yaml 데이터 + classifier 등록 + map 정합 + 테스트), IPSF element 미등재 5동작(kip-up/power-spin/peter-pan/elbow-twist-sister/pdshape)에 객관 180° 무릎 신전(ipsf_absolute) 채점을 켜고, pod-free 단위테스트로 de-contamination(곧은 무릎=감점0)과 cross-exclusion(굽은 무릎=leg_extension 감점 + 무릎 reference 제외)을 구조적으로 입증했다.

## 무엇을 했나 (Task별)

- **Task 1** — 5 criteria yaml 생성. hold_moment 양 무릎(대칭) `extension_class: EXTEND`, `angle_target: 180.0`(IPSF 보편 신전기준, 정은지 측정값 아님), `tolerance_full: 20.0`, `minimum_requirement: 160.0`(micro-bent 경계). `source_ref` = IPSF Glossary 'Fully extended leg' + 동작 의도된 폼(belle 도메인) — element code 날조 금지. pdshape 는 비대칭 주의 주석(anchor 다리 위양성 → step5 게이트 재조정). loader validate 5/5 통과.
- **Task 2** — `REGISTERED_MOTIONS` 5→10, `_ALIAS_TABLE` 한국어(킵업/파워스핀/피터팬/엘보 트위스트 시스터/피디쉐입)+영어 alias. classify 10/10 recognized. 헤더 코멘트에 sanctioned Phase 5 scope 확장 근거 박제.
- **Task 3** — motion_ipsf_map.json 5 entry `criteriaYaml: ref-{move}.yaml` 링크 + sourceNote 갱신. **보수적 선택**: `angleSource`/`angleFixtureKey` 미변경(아래 deviation 참조).
- **Task 4** — 테스트 3종: (a) loader(5동작 load+validate+EXTEND 무릎+IPSF source_ref), (b) classifier alias, (c) de-contamination/cross-exclusion(신규 파일, 핵심).

## de-contamination/cross-exclusion 증거 (pod-free, 구조적 단언만)

- **dimensions.extension_deviation** — EXTEND 무릎 profile에서 곧음(178°)=deficit~0 / 굽음(140°)=deficit>0. 비-EXTEND hip=0(신전 채점 제외). 곧음/굽음이 채점을 가르며 정은지 measured 와 무관.
- **deduction_engine.tally (엔진-stage)** — md에 `leg_extension`(>tol)과 `angle_vs_reference__{knee}`가 공존해도 무릎 reference를 discard(`leg_extension` record 존재, knee reference record 없음, double-count 0).
- **builder seam (`_build_deduction_measured_deviations`, seed-stage)** — 곧은 학생 무릎이 정은지(reference)와 20° 차이여도 `angle_vs_reference__{knee}` seed 자체를 차단(expects_extension). 비-EXTEND hip의 reference 편차는 유지(control — 차단이 blanket 아님). builder→tally 전 경로에서 곧은 무릎=무릎 감점 record 0 / 굽은 무릎=`leg_extension` 검출.

## Deviations from Plan

### 의사결정 (보수적)

**1. [Task 3] angleSource 미변경 — 보수적 선택**
- **근거:** 채점 경로는 인식기→`load_grouped_criteria(motion)`(yaml 파일명)로 직접 동작하며 motion_ipsf_map.json을 경유하지 않는다(map header: "채점 경로 미진입"). map의 `angleSource`는 coach-프롬프트 각도 출처(직교 routing). 새 enum(`ipsf_extension_objective`) 도입은 소비처(`_load_coach_angle_fixture`, `is_reference_free_motion`)에서 graceful이긴 하나 문서화 enum 밖이고 채점에 무익, `eunji_measured_yaml` 라벨링은 객관 기준을 정은지-measured로 오기록하는 거짓이 됨. 따라서 `criteriaYaml`+sourceNote만 갱신(angleFixtureKey null 유지). 제약의 "불확실하면 보수적" 지침 정합. 소비처 회귀 0(`test_motion_ipsf_map_coverage`/`test_coach_prompt_angle_fixture` 37/37 통과).

### Auto-fixed (Rule 1 — 직접 회귀)

**2. [Rule 1] REGISTERED_MOTIONS count/set 단언 테스트 2건 갱신**
- **발견:** Task 2 등록(5→10)이 `test_gemini_motion_classifier.py`(len==5/set), `test_gemini_motion_classify_spike.py`(count_5/set)를 깨뜨림.
- **수정:** 두 파일의 count/set 단언을 10/신규 set으로 갱신. Task 2 커밋(ed6ec24)에 포함(직접 consequence).

## 회귀 검증

- 전체 backend suite: 50 failed / 1947 passed / 19 skipped / 11 collection errors. **신규 실패 0** — baseline(내 변경 stash) 대비 실패 집합 동일(50==50, diff 공집합). 11 collection errors + 50 failures는 전부 pre-existing(`backend.research.spikes` import path 부재 + 환경 의존 pipeline/gemini/height 테스트, MEMORY 부채 audit과 정합). passed +49(신규 테스트).
- phase24 `assert_gates.py`: `generalization kip-up`만 FAIL(structural false-negative) — 제약에 명시된 **예상된 red**(step5 pod 전까지, eval fixture 미변경이라 본 작업이 도입한 게 아님). sensitivity set은 SKIPPED(pod-serial deferred).

## Known Stubs

없음. 데이터+등록+테스트만, 분석 경로 활성(GEMINI_RECOGNIZER_ENABLED)은 step 5 pod 셋업 책임(설계상 의도).

## Self-Check: PASSED
- created files 6/6 FOUND, modified 5/5.
- commits de61a9f / ed6ec24 / e61dad8 / 9678ab5 모두 FOUND.
