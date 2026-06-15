---
phase: 14-reference-motion-registration
reviewer: Codex
date: 2026-06-15
scope: direct-plan-review
status: revise-before-execution
reviewed_plans:
  - 14-CONTEXT.md
  - 14-RESEARCH.md
  - 14-PATTERNS.md
  - 14-VALIDATION.md
  - 14-01-PLAN.md
  - 14-02-PLAN.md
  - 14-03-PLAN.md
local_code_checked:
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/analysis/force_signals.py
  - backend/shared/python/sunity_shared/analysis/technique.py
  - app/src/lib/referenceMotions.ts
  - app/src/types/analysis.ts
  - docs/contract.md
---

# Phase 14 Direct Review

## Executive Verdict

Phase 14의 큰 방향은 맞다. 11개 reference 전체를 대상으로 하고, app UI가 아니라 admin CLI + Pod backfill + Firestore ADD-only merge로 가는 판단도 현재 코드베이스와 잘 맞는다. 특히 default-5 motion trap을 명시적으로 막고, Pod /health abort gate, dry-run-first seeder, belle human checkpoint를 넣은 점은 좋다.

하지만 현재 plan 그대로 14-02/14-03을 실행하면 **reference 문서 안에 서로 다른 pose run에서 나온 파생 필드가 섞일 위험**이 있다. 또 D-01 "student path와 동일"이라는 표현이 현재 production `_process`와 정확히 일치하지 않는다. plan은 `preflight_label_gate_passed=None` / `technique_profile=None`을 의도적으로 pin하지만, 실제 `_process`는 env 기반 preflight gate와 recognizer 상태를 넘긴다. 이건 실행 전에 문구가 아니라 계약으로 고정해야 한다.

내 판정은 **revise-before-execution**이다. 14-01은 거의 실행 가능하지만, 14-02/14-03 전에 아래 blocker를 plan patch로 반영해야 한다.

1. stored-sufficient 필드(`meanAngles`, EXTEND)는 re-run pose가 아니라 active `phase4_v1.angles`에서 산출.
2. Pod re-run pose와 active stored pose 사이의 frame count/hash/angle delta gate를 추가.
3. D-01 parity를 "student path exact"가 아니라 "reference-v1 pinned config exact"로 명확히 계약화.
4. seeder skip/partial fixture/rollback을 production write 기준으로 더 강하게 막기.

저라면 14-02를 바로 실행하지 않고 **14-PLAN-PATCH.md 또는 plan 파일 직접 수정**으로 이 네 가지를 먼저 넣는다.

## What Looks Strong

- 5개 기본값이 아니라 정확히 기존 11개 reference 전체를 대상으로 삼고 있다. `14-01-PLAN.md:84-96`, `14-02-PLAN.md:100-104`, `14-03-PLAN.md:83-86`이 default-5 trap을 반복해서 막는다.
- Firestore write는 14-03까지 미루고, 14-01은 audit/test/contract만 수행한다. 실행 순서가 안전하다.
- Pod down이면 CPU fallback을 금지하고 STOP하는 결정은 맞다. `14-03-PLAN.md:76-82`.
- app contract를 먼저 열어두는 접근은 맞다. `referenceMotions.ts`는 unknown field를 직접 깨뜨리지 않는 구조지만, 타입과 docs lockstep은 필요하다.
- belle visual checkpoint가 production state change 앞에 있다. `14-03-PLAN.md:115-148`.

## Blockers

### R1. stored-sufficient 필드를 re-run RTMW 결과에서 산출하면 active pose와 파생 필드가 갈라질 수 있다

Severity: **BLOCKER**

CONTEXT D-01/D-02의 핵심은 "belle이 이미 시각검증한 active phase4_v1 pose는 authoritative이고, 부족한 입력만 하이브리드로 채운다"이다. Research도 `meanAngles`와 EXTEND는 stored `angles`만으로 충분하다고 결론낸다.

그런데 14-02는 한 번의 Pod RTMW re-inference에서 `angles=temporal_fill(compute_joint_angles(kp), ...)`를 만들고, 그 re-run angles로 `meanAngles`, EXTEND, force 입력까지 계산한다.

Evidence:

- `14-CONTEXT.md` D-01/D-02: verified `phase4_v1` pose 재사용, 부족한 필드에 한해서만 Pod 재추론.
- `14-RESEARCH.md`: `meanAngles = STORED-SUFFICIENT`, EXTEND Fallback = `STORED-SUFFICIENT`.
- `14-02-PLAN.md:45-57`: one RTMW re-inference로 four outputs 산출.
- `14-02-PLAN.md:110-124`: re-run `pose_frames`에서 `angles`를 새로 계산하고 그 값으로 `meanAngles`, `FallbackRecognizer`, `compute_force_signals`를 호출.
- `14-02-PLAN.md:129-130`: active `joints3d/angles/activeVersion`은 건드리지 않음.

Risk:

- top-level `angles`는 phase4_v1인데 `meanAngles`는 re-run angles에서 나온 값이 될 수 있다.
- EXTEND profile도 active reference pose가 아니라 새 re-inference pose의 평균 각도 기준이 된다.
- RTMW 모델/전처리/fps/frame extraction이 조금이라도 달라지면 Mode 1 비교 기준이 내부적으로 불일치한다.
- "active pose는 unchanged"라는 14-03 성공 조건이 오히려 불일치 증거를 가릴 수 있다.

Recommendation:

나는 14-02 Task 1을 이렇게 바꾸겠다.

1. backfill 시작 시 Firestore에서 `reference/{id}` active `phase4_v1`의 `angles`, `anglesJointKeys`, `anglesFrames`, `activeVersion`을 읽는다.
2. `meanAngles`와 `techniqueProfile`은 반드시 stored active `angles`에서 산출한다.
3. Pod re-run은 `BodyNormalizationProfile`과 `ForceDirectionPattern`에 필요한 live `PoseFrame` 확보 용도로만 사용한다.
4. ForceSignals에 넣는 `angles`도 가능하면 stored active `angles`를 사용한다. 단, live `pose_frames` frame count와 stored `anglesFrames`가 맞지 않으면 seed를 중단한다.
5. re-run angles는 검증용으로만 계산하고, `maxAngleDelta`, `meanAngleDelta`, frame count, stored hash, re-run hash를 fixture/run log에 남긴다.
6. delta가 허용치를 넘으면 그 motion뿐 아니라 real seed 전체를 멈춘다. 이 경우는 "derived field backfill"이 아니라 "pose version 재검증" 문제다.

내 기준 acceptance gate:

```text
storedAnglesHash recorded
rerunAnglesHash recorded
anglesFrames == len(pose_frames)
max(abs(stored_angles - rerun_angles)) <= epsilon OR run aborted before seed
meanAnglesSource == "reference.phase4_v1.angles"
techniqueProfileSource == "reference.phase4_v1.angles"
```

### R2. D-01 "student path exact" 주장이 현재 `_process`와 다르다

Severity: **BLOCKER-HIGH**

Plan은 `preflight_label_gate_passed=None`와 `technique_profile=None`을 pin하고, 이것을 "student path와 SAME"이라고 부른다. 하지만 현재 production `_process`는 env 기반 `_preflight_label_gate_passed()` 결과와, Layer 2 recognizer 상태에 따른 `technique_profile`을 `compute_force_signals`에 넘긴다.

Evidence:

- `14-01-PLAN.md:115`: reference backfill을 `recognizer=FallbackRecognizer` + `technique_profile=None` + `preflight_label_gate_passed=None`으로 pin.
- `14-01-PLAN.md:140-143`: test도 helper와 direct-call reference 양쪽을 모두 `None`으로 비교.
- `14-02-PLAN.md:116-123`: helper도 `technique_profile=None`, `preflight_label_gate_passed=None`.
- `backend/functions/pipeline/app.py:851-871`: `_preflight_label_gate_passed()`는 env에 따라 True/False/None 반환.
- `backend/functions/pipeline/app.py:1899-1908`: `_process`는 `preflight_label_gate_passed=_preflight_label_gate_passed()`와 `technique_profile=profile if layer2_recognizer is not None else None`을 전달.
- `backend/shared/python/sunity_shared/analysis/force_signals.py:1579-1636`: 두 값은 phase boundary와 confidence/warnings에 실제 영향을 준다.

Risk:

- Phase 15에서 학생 분석은 env gate True/False 또는 Layer 2 on 상태로 실행되고, reference backfill은 None/None 상태로 저장될 수 있다.
- 그러면 "동일 함수"는 맞아도 "동일 configured path"가 아니다.
- 현재 parity test는 production path와의 parity가 아니라 pinned direct-call과의 parity만 증명한다. 테스트가 위험을 가리는 형태가 된다.

Recommendation:

이건 둘 중 하나로 명확히 정해야 한다.

Option A: **reference-v1 pinned config로 공식화**

- plan 문구를 "student path exact"가 아니라 "same functions under reference-v1 pinned config"로 바꾼다.
- fixture에 아래 메타를 저장한다.

```json
{
  "forceConfig": {
    "recognizer": "FallbackRecognizer",
    "techniqueProfileForForceSignals": null,
    "preflightLabelGatePassed": null,
    "forceSignalsLayer2Enabled": false
  }
}
```

- Phase 15는 reference force fields를 해석할 때 이 config가 학생 force config와 다를 수 있음을 명시적으로 처리해야 한다.

Option B: **진짜 production `_process` config와 맞춤**

- backfill run 시 Pod env의 `PREFLIGHT_LABEL_GATE_PASSED`와 `FORCE_SIGNALS_LAYER2_ENABLED`를 읽어 fixture/run log에 기록한다.
- `_process`와 동일한 recognizer/profile 전달 규칙을 shared helper로 뽑아 학생 path와 backfill이 같이 호출하게 한다.
- parity test는 env matrix(None/True/False, Layer2 off/on)를 최소 2개 이상 검증한다.

내 선택은 **Option A**다. v1 reference는 보수적 baseline이어야 하고, Fallback + Layer2 off pin 자체는 합리적이다. 다만 "student path exact"라고 부르면 안 된다. 이건 "동일 함수 + 명시 pin"이다.

### R3. Seeder idempotent skip 조건이 partial reference를 놓칠 수 있다

Severity: **HIGH**

14-02는 `--force`가 없으면 "field already present"일 때 skip한다고 되어 있다. 그런데 Phase 14는 기존 5개는 `bodyNormalizationProfile`만 있고, 다른 6개는 없을 수 있는 혼합 상태를 전제로 한다. skip 기준이 하나의 필드이면 일부 reference가 force/EXTEND 없이 지나갈 수 있다.

Evidence:

- `14-01-PLAN.md:17`: all 11 중 어떤 reference가 body profile을 갖는지 audit 필요.
- `14-02-PLAN.md:170-172`: field already present면 skip.
- `14-03-PLAN.md:20-22`: 최종 성공은 4개 필드 + `captureViews`가 모두 있어야 함.

Risk:

- original 5가 `bodyNormalizationProfile` 때문에 skip되어 `forceDirectionPattern`이나 `techniqueProfile`이 안 들어갈 수 있다.
- dry-run은 통과했는데 real-run 후 verify에서 partial missing이 나올 수 있다.
- `--force`로 해결하려다 기존 body profile까지 불필요하게 overwrite할 수 있다.

Recommendation:

skip 조건을 "어떤 필드 하나 존재"가 아니라 "Phase 14 required field set 전체가 valid"로 바꿔야 한다.

내가 넣을 규칙:

```text
required = meanAngles + techniqueProfile + bodyNormalizationProfile + forceDirectionPattern + captureViews
if all required present and valid and --force is false:
  skip
else:
  merge missing fields only
```

`--force`는 "기존 valid field overwrite"에만 사용하고, missing field repair는 기본 동작이어야 한다. dry-run summary도 `skippedComplete`, `repairMissing`, `forceOverwrite`를 분리해서 출력하게 하겠다.

### R4. 14-03의 "active pose unchanged" 검증이 assertion 수준이다

Severity: **HIGH**

14-03은 active `joints3d/angles/activeVersion`이 unchanged라고 기록하라고 하지만, 자동 검증은 run log에 문자열이 있는지만 본다. production Firestore write를 다루는 plan치고는 약하다.

Evidence:

- `14-03-PLAN.md:90-97`: verify-read에서 unchanged assertion을 기록.
- `14-03-PLAN.md:100-101`: automated check는 log file 존재, 11개 ID 문자열, `activeVersion`, `health` 문자열만 grep.
- `14-03-PLAN.md:108-110`: acceptance도 "run log asserts" 수준.

Risk:

- 실수로 `angles`, `joints3d`, `activeVersion`을 건드려도 run log에 "unchanged"라고 쓰면 gate가 통과할 수 있다.
- `merge:true`라도 payload 구성 실수로 active fields를 포함하면 production reference가 오염된다.
- rollback 근거가 없다.

Recommendation:

14-03 Task 1 앞에 pre-state snapshot을 추가하겠다.

1. seed 전 `reference/{id}` 11개를 읽어서 다음 hash를 저장:
   - `activeVersion`
   - `angles` length + sha256
   - `joints3d` length + sha256
   - `anglesJointKeys`
   - `versions/phase4_v1` 존재 여부
2. seed 후 같은 값을 다시 읽어 byte-level hash 비교.
3. mismatch가 하나라도 있으면 `14-BACKFILL-RUN.md`를 FAIL로 쓰고, belle 승인 단계로 가지 않는다.
4. pre-seed snapshot은 `.planning/phases/14-reference-motion-registration/14-PRESEED-SNAPSHOT.json`처럼 repo에 커밋하지 않을 수 있는 위치에 두되, run log에는 hash만 남긴다.

자동 verify도 grep이 아니라 JSON summary를 검사해야 한다.

```text
unchangedActivePoseCount == 11
changedActivePoseCount == 0
completeDownstreamFieldCount == 11
seededMotionCount == 11
```

### R5. Partial fixture가 real seed로 들어갈 수 있는 경로를 더 닫아야 한다

Severity: **MEDIUM-HIGH**

14-02는 per-motion failure isolation을 요구하고, 14-03은 failures를 record하라고 한다. 하지만 production seed는 all-or-nothing이어야 한다. "한 motion 실패했지만 10개 seed"는 Phase 14 success criteria와 맞지 않는다.

Evidence:

- `14-02-PLAN.md:85`: one bad motion does not abort the batch.
- `14-02-PLAN.md:128`: per-motion try/except logs failure and continues.
- `14-03-PLAN.md:86-87`: 11/11 computed, NaN 0, failures=0을 confirm or record.

Risk:

- fixture에 10개만 들어있는데 seeder가 그것만 merge할 수 있다.
- `14-BACKFILL-RUN.md`에는 failure가 기록되지만 Firestore는 partial state가 된다.
- 다음 run에서 idempotent skip/force 판단이 더 복잡해진다.

Recommendation:

backfill script는 per-motion compute는 계속 진행하되, process exit status는 아래처럼 해야 한다.

```text
if failures > 0 or len(results) != 11 or any_nan_or_inf:
  write diagnostic JSON
  exit non-zero
  do not emit seedable fixture unless --allow-partial-diagnostic is explicitly set
```

seeder도 input fixture가 exactly 11 ids가 아니면 real-run을 거부해야 한다. partial repair를 하려면 별도 `--motions` + `--repair-missing` flow로 분리하는 편이 낫다.

## Medium-Risk Findings

### R6. `compute_reference_downstream` helper가 pole measurement를 인자로 받지 않으면 parity 범위가 좁다

Severity: **MEDIUM**

14-02 helper signature는 `compute_reference_downstream(pose_frames, fps=9.0, motion_id=None, mode_context="mode1")`이다. 하지만 production `_process`는 `inputs.pole_axis_measurement`를 `compute_force_signals`에 넘긴다.

Evidence:

- `14-01-PLAN.md:135-136`: helper signature에 pole measurement 없음.
- `14-02-PLAN.md:115`: helper 내부에서 `build_pole_axis_measurement(... line=None)` 생성.
- `backend/functions/pipeline/app.py:1899-1902`: production은 `inputs.pole_axis_measurement` 전달.

Risk:

- 테스트는 vertical fallback `line=None`만 검증한다.
- 나중에 pole detector 또는 line-aware measurement가 들어오면 helper parity test가 실제 경로 차이를 못 잡는다.

Recommendation:

helper signature를 이렇게 바꾸는 게 낫다.

```python
compute_reference_downstream(
    pose_frames,
    *,
    pole_axis_measurement,
    angles,
    fps=9.0,
    motion_id=None,
    mode_context="mode1",
    force_config=REFERENCE_V1_FORCE_CONFIG,
)
```

vertical fallback은 orchestrator가 만들고 helper에 주입한다. 그러면 test가 production과 같은 call boundary를 검증한다.

### R7. ForceDirectionPattern만 저장하면 사후 디버깅 근거가 부족할 수 있다

Severity: **MEDIUM**

Phase 14의 target field는 `ForceDirectionPattern`이다. 그런데 force pattern이 이상할 때 원인 분석은 보통 raw `ForceSignalsReport` warnings/metrics를 봐야 한다.

Risk:

- belle spot-check에서 "ForceDirectionPattern findings가 이상하다"가 나오면 어떤 raw signal 때문에 그런지 Firestore에서 바로 확인하기 어렵다.
- 14-BACKFILL-RUN.md에 summary만 남으면 후속 Phase 15 디버깅이 느려진다.

Recommendation:

top-level schema에 raw report를 영구 저장할지는 별도 결정이 필요하지만, 최소한 fixture와 run log artifact에는 motion별 `forceSignalsReport` summary를 남기겠다. Firestore에는 storage/contract 부담을 피하고 싶다면 `forceDirectionPatternSource` 또는 `forceSignalsWarnings` 정도만 저장해도 된다.

### R8. contract lockstep 범위가 TS/docs만으로 충분한지 실행 중 재확인 필요

Severity: **MEDIUM**

14-01은 `docs/contract.md`와 `app/src/types/analysis.ts`만 수정한다. 현재 `reference-api`는 passthrough 성격이라 큰 문제는 없어 보이지만, Python `models`나 Firestore validator가 ReferenceMotion을 엄격히 다루는 코드가 있으면 빠질 수 있다.

Recommendation:

14-01 실행 중 `rg "ReferenceMotion|forceDirectionPattern|techniqueProfile|captureViews"`를 한 번 더 돌려서 typed mirror/validator가 없는지 확인하라. 나오면 3-way가 아니라 4-way lockstep으로 확장해야 한다.

## Risk Response: What I Would Do If It Happens

| Situation | My response |
|----------|-------------|
| Pod `/health` fails | 14-03 계획처럼 즉시 abort. `14-BACKFILL-RUN.md`에 health failure만 남기고 backfill/seed는 하지 않는다. CPU fallback은 금지. |
| S3 video missing for one motion | seedable fixture를 만들지 않는다. missing key, bucket, motion id만 run log에 남기고 S3 inventory/업로드 문제로 분리한다. 나머지 10개 seed도 하지 않는다. |
| re-run angles differ from active `phase4_v1.angles` | Phase 14 seed를 멈춘다. stored-sufficient fields는 active angles에서 산출하고, live pose_frames가 필요한 force/body만 쓸 수 있는지 frame alignment를 재검토한다. delta가 크면 새 pose version 검증 phase로 승격한다. |
| ForcePattern findings look fabricated or too aggressive | Firestore real-run 전이면 해당 fixture를 폐기하고 raw force signals를 검토한다. real-run 후 발견이면 ADD-only field만 rollback/delete하고 active pose는 건드리지 않는다. empty findings + warning은 허용한다. |
| Seeder dry-run says some fields already exist | skip하지 않고 complete/repair/overwrite를 분리한다. missing field repair는 기본 merge, existing valid overwrite는 `--force`일 때만 한다. |
| Real seed accidentally writes wrong fields | pre-seed snapshot hash로 영향 범위를 확인한다. Phase14-added fields만 삭제/restore하는 rollback script를 실행하고, active `joints3d/angles/activeVersion`이 바뀌었으면 즉시 stop하고 별도 incident로 다룬다. |
| ADC/auth fails locally | dry-run 결과까지만 남기고 real-run을 하지 않는다. 콘솔 수동 편집으로 우회하지 않고 ADC를 정상 로그인한 뒤 같은 fixture로 재시도한다. |
| belle spot-check rejects values | active pose는 그대로 두고 Phase14-added fields만 rollback한다. rejected motion id와 reject reason을 run log에 남긴 뒤 해당 motion만 diagnostic re-run한다. |

## Plan Patch I Recommend

내가 바로 고친다면 patch는 이 정도다.

1. `14-02-PLAN.md` Task 1:
   - stored active `angles` fetch를 필수화.
   - `meanAngles`/`techniqueProfile` source를 active `phase4_v1.angles`로 고정.
   - re-run angles는 only validation.
   - `maxAngleDelta`/hash/frame count gate 추가.
   - helper signature에 `angles`와 `pole_axis_measurement`를 주입.

2. `14-01-PLAN.md` Task 2:
   - parity test 이름을 "student path exact"에서 "reference-v1 pinned config exact"로 바꿈.
   - env flip test를 추가해 `PREFLIGHT_LABEL_GATE_PASSED=1`일 때 결과가 달라질 수 있음을 의도적으로 증명.

3. `14-02-PLAN.md` Task 2:
   - seeder skip 기준을 "all Phase14 fields valid"로 수정.
   - partial fixture real-run 거부.
   - dry-run summary에 complete/repair/overwrite 분리.

4. `14-03-PLAN.md` Task 1:
   - pre/post active pose hash snapshot 추가.
   - automated verify를 grep에서 JSON summary assertion으로 강화.
   - rollback/delete plan을 runbook에 포함.

## Final Recommendation

Phase 14는 실행할 가치가 있고, 방향도 맞다. 다만 지금 상태로는 "검증된 active pose를 그대로 둔다"와 "one RTMW re-inference에서 네 산출물을 모두 만든다"가 충돌한다. 이 충돌은 실행 후 발견하면 Firestore reference 데이터 신뢰도 문제로 커진다.

저라면 14-01은 위 수정 방향을 반영해서 실행하고, 14-02/14-03은 plan patch 후 진행한다. 특히 stored active angles를 source of truth로 고정하는 변경과 pre/post hash gate는 production seed 전에 반드시 넣겠다.
