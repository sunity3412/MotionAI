---
phase: 14-reference-motion-registration
reviewer: Codex
date: 2026-06-15
scope: direct-plan-review-iteration3
status: revise-before-execution
reviewed_plans:
  - 14-DIRECT-REVIEW.md
  - 14-DIRECT-REVIEW-ITERATION2.md
  - 14-01-PLAN.md
  - 14-02-PLAN.md
  - 14-03-PLAN.md
  - 14-VALIDATION.md
local_code_checked:
  - app/package.json
  - app/src/lib/referenceMotions.ts
  - app/src/types/analysis.ts
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/shared/python/sunity_shared/auth.py
  - .gitignore
---

# Phase 14 Direct Review Iteration 3

## Executive Verdict

2차 리뷰의 BLOCKER/HIGH는 대부분 계획에 반영됐다. 특히 restore-aware rollback, `app/scripts`로의 Node admin script 위치 이동, Pod `--check-firestore` gate, `referenceMotions.ts normalize()` 업데이트, `seedPayload`/`diagnostics` 분리, JSON assertion gate는 실행 안정성을 많이 올렸다.

다만 아직 **as-is 실행은 보류**가 맞다. 새로 남은 핵심 리스크는 좁지만 실행 시 실제로 깨질 수 있다. 14-02가 `forceDirectionPattern` 저장 helper에 generic `_validate_flat_dict_no_nested_array`를 쓰라고 지시하는데, 현재 ForcePattern schema는 `findings[].warnings: string[]`를 허용한다. 기존 generic validator는 list 안의 dict에 nested list가 있으면 reject한다. 즉 계획대로 구현하면 유효한 `forceDirectionPattern`을 helper나 seeder가 거부할 수 있다.

판정: **revise-before-execution, very close**. R3-1만 plan patch하면 실행으로 넘어갈 수 있다. R3-2는 blocker는 아니지만 expensive Pod run 전에 실패를 더 앞당기는 운영 개선으로 같이 반영하는 편이 낫다.

## Cleared From 2차 Review

- Cleared: R2-1 rollback/snapshot. `14-03-PLAN.md`가 active pose hash뿐 아니라 Phase-14 field presence/value snapshot을 저장하고, absent-before는 delete, present-before는 restore로 바뀌었다.
- Cleared: R2-2 Node admin script packaging. Snapshot/rollback script가 `backend/scripts`가 아니라 `app/scripts`에 위치하도록 바뀌었다. `firebase-admin`은 `app/package.json`에 있으므로 이 방향이 맞다.
- Cleared: R2-3 Pod credential/read gate. 14-02/14-03에 Pod `--check-firestore` mode와 `FIREBASE_SA_PATH`/`FIREBASE_SA_JSON` setup이 들어갔다.
- Cleared: R2-4 app runtime normalize. `14-01-PLAN.md`가 `app/src/lib/referenceMotions.ts`를 수정 대상으로 추가하고 새 reference downstream fields를 normalize return에 포함하도록 바뀌었다.
- Cleared: R2-5 fixture collision. Backfill fixture가 `{ generatedAt, seedPayload, diagnostics }`로 분리되고, seeder는 `seedPayload`만 읽도록 바뀌었다.
- Cleared: R2-6 verification gate. 14-03이 markdown grep 대신 `14-BACKFILL-RUN-SUMMARY.json` assertion을 요구한다.
- Cleared: R2-7 requirement tag. `14-03-PLAN.md` frontmatter에 `requirements: [REF-01]`가 복구됐다.

## Findings

### R3-1. `forceDirectionPattern` cannot safely use the generic flat validator

Severity: **BLOCKER**

14-02는 새 `update_reference_downstream_data(...)` helper에서 `force_direction_pattern`에도 `_validate_flat_dict_no_nested_array`를 적용하라고 한다. 하지만 현재 `ForcePatternInference` 계약은 top-level `warnings: string[]`뿐 아니라 `findings[].warnings: string[]`도 허용한다. generic flat validator는 top-level list[str]는 허용하지만, list 안의 dict는 scalar-only로 검사하므로 `findings[0].warnings` 같은 list field를 reject한다.

Evidence:

- `14-02-PLAN.md:228-233`: `force_direction_pattern`을 포함한 각 dict에 `_validate_flat_dict_no_nested_array`를 실행하라고 지시한다.
- `14-02-PLAN.md:263`: done condition도 generic `_validate_flat_dict_no_nested_array` 사용을 요구한다.
- `backend/shared/python/sunity_shared/firestore_admin.py:45-90`: generic validator는 list item이 dict일 때 `_validate_dict_only_scalars`로 넘긴다.
- `backend/shared/python/sunity_shared/firestore_admin.py:104-128`: `_validate_dict_only_scalars`는 list/dict 값을 모두 reject한다.
- `app/src/types/analysis.ts:833-866`: `ForcePatternFinding.warnings: string[]`, `ForcePatternInference.findings: ForcePatternFinding[]`, top-level `warnings: string[]`가 계약이다.
- `backend/shared/python/sunity_shared/firestore_admin.py:343` and `:751-755`: production analysis 저장 경로는 이미 `_validate_force_pattern_inference(...)` scoped validator를 사용한다.

Risk:

- 유효한 `forceDirectionPattern` fixture가 `findings[].warnings`를 포함하면 `update_reference_downstream_data`가 TypeError/ValueError로 실패한다.
- JS seeder가 `seed-reference-body-profile.mjs`의 nested-array rejection pattern을 그대로 확장하면 같은 shape를 dry-run 단계에서 reject할 수 있다.
- 현재 11개 fixture에서 우연히 finding warning이 비어 있으면 통과할 수 있지만, schema-level로는 잘못된 gate가 남는다. Phase 14 이후 재생성/repair 때 같은 문제가 다시 나온다.
- "nested array 금지" 정책을 지키려다 이미 scoped validator로 허용한 `forcePatternInference` 예외를 reference mirror path에서 잃어버리는 형태다.

Recommendation:

나는 14-02 Task 2를 이렇게 고치겠다.

1. `meanAngles`, `techniqueProfile`, `bodyNormalizationProfile`에는 generic `_validate_flat_dict_no_nested_array`를 유지한다.
2. `forceDirectionPattern`에는 generic validator 대신 existing `_validate_force_pattern_inference(force_direction_pattern)`을 호출한다.
3. `update_reference_downstream_data` done condition을 "runs `_validate_force_pattern_inference` for forceDirectionPattern and generic flat validator for the other downstream dicts"로 바꾼다.
4. `seed-reference-downstream.mjs`에도 scoped JS validation을 둔다:
   - top-level `warnings`: list[str]
   - `findings`: list of whitelisted finding objects
   - `findings[].warnings`: list[str]
   - 그 외 nested list/dict는 reject
5. Test/verification에 최소 fixture 2개를 추가한다:
   - valid: `findings[0].warnings: ["axis_signal_unavailable"]` accepted
   - invalid: `findings[0].warnings: [["nested"]]` or unknown finding key rejected

이 패치는 기존 project-wide `[[firestore-nested-array-flat]]` 정책을 약화하지 않는다. 이미 production `result.forcePatternInference`에 있는 scoped exception을 reference `forceDirectionPattern` mirror에도 동일하게 적용하는 것이다.

### R3-2. Pod `--check-firestore` still checks only one doc, so non-ref-climb doc completeness can fail later

Severity: **MEDIUM**

2차에서 요구한 credential/read gate는 들어갔고 방향은 맞다. 다만 현재 command는 `--check-firestore --motions ref-climb`로 고정되어 있다. 이건 Pod Firebase SA mount와 Firestore read permission을 확인하는 데는 충분하지만, all 11 references의 `activeVersion`, `angles`, `anglesJointKeys`, `anglesFrames` completeness를 expensive S3/RTMW 전에 전부 확인하지는 못한다.

Evidence:

- `14-02-PLAN.md:102`, `:136`, `:203`: `--check-firestore` mode는 one reference doc read로 정의되어 있다.
- `14-03-PLAN.md:152-153`, `:192`, `:300`: 실행 gate가 `--check-firestore --motions ref-climb`이다.
- 14-02 real backfill은 이후 all 11 motions의 stored active angles를 load-bearing input으로 사용한다.

Risk:

- `ref-climb`은 통과하지만 다른 reference 문서의 `anglesFrames`나 `anglesJointKeys`가 누락된 경우, Pod는 credential gate를 통과한 뒤 S3/RTMW 작업을 시작하고 나서야 실패할 수 있다.
- 이 경우 실패 자체는 안전하지만, 14-02가 의도한 "fail before expensive path" 성격이 약해진다.

Recommendation:

나는 `--check-firestore`를 cheap metadata gate로 확장하겠다.

```text
python backend/scripts/backfill_reference_downstream.py --check-firestore --motions <all 11 explicitly>
```

구현은 S3/RTMW를 절대 호출하지 않고, 11개 문서에 대해 `activeVersion`, `angles`, `anglesJointKeys`, `anglesFrames` presence와 frame count sanity만 확인한다. credential 확인용 one-doc mode를 남겨도 되지만, 14-03 production run gate는 all-11 check를 쓰는 게 낫다.

## My Execution Advice

내가 실행 책임자라면 R3-1을 blocker로 보고 14-02 plan patch 없이 Pod/seed real-run에 들어가지 않는다. 이 문제는 문구 문제가 아니라 유효 payload를 reject할 수 있는 validator mismatch다.

R3-1 패치 후에는 14-02/14-03 실행 순서를 그대로 유지하되, R3-2도 같이 넣어서 `--check-firestore`가 all 11 metadata를 먼저 읽게 만들겠다. 그 다음부터는 현재 계획의 preseed snapshot → Pod dry-run → Pod real-run → seeder dry-run → seeder real-run → JSON summary assertion → post hash gate 흐름이 충분히 방어적이다.

