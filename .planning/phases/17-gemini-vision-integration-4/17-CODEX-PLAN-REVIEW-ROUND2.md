# Phase 17 Plan Review Round 2 - Codex

Date: 2026-06-12
Scope: commit `890c338` 이후 1차 review 패치 반영본 재검토.

## Verdict

**아직 execute 진입 보류.** 1차 review 의 큰 방향은 대부분 반영됐지만, 실행자가 그대로 따르면 깨질 가능성이 있는 새 blocker 가 남아 있다. 핵심은 B2 축소 설계가 Plan 03 안에서는 안전해졌지만, `AI-SPEC.md` / `RESEARCH.md` / Plan 07 / 일부 success gate 에 옛 D 설계가 남아 있다는 점이다.

내 의견은 다음 순서로 추가 패치 후 실행하는 것이다.

1. D 영역 문서 정합성부터 닫기: `AI-SPEC.md`, `17-RESEARCH.md`, `17-PLAN-CHECK.md`, Plan 07 의 `RTMW/coco_array/confidence < 0.5` 잔재 제거.
2. Plan 03/04 의 pipeline 삽입 위치를 실제 `pipeline/app.py` 순서에 맞게 다시 박기.
3. Plan 07 의 RTMW engine 재사용 방식을 import 가능한 shared module 로 정리.
4. Plan 06 은 가능하면 `06A/06B/06C` 별도 plan 파일로 split.

## Requested Checks

### 1. 1차 BLOCKER 4 + WARNING 6 패치 충분성

- **B1 model ID:** 거의 충분. `gemini-3.1-pro-preview` / `gemini-3.5-flash` 자체는 Google 공식 docs 의 model code 와 맞는다. 다만 Plan 02 는 아직 `GEMINI_C_MODEL default "gemini-3.5-flash"` 같은 raw default 문장이 남아 있어 `resolve_model("C", ...)` 사용을 명시해야 한다.
- **B2 Plan 03 scope 축소:** Plan 03 내부는 안전한 방향이다. `coco_array` mutate 금지, `KeypointReport.data/confidence` 보강, mirror hint audit 로 축소한 것은 맞다. 하지만 주변 문서에 옛 설계가 남아 있어 충분하지 않다.
- **B3 writer interface:** 핵심 시그니처는 충분히 고쳤다. 단 Plan 04 에 "None 반환 시 Cerebras 폴백" 문장이 아직 남아 있어 `{}` / `_fallbackReason` 계약과 충돌한다.
- **B4 local video / no re-run gate:** 방향은 충분하다. 다만 Plan 02 의 `_process(..., is_reference)` 시그니처 확장 지시는 불필요하게 call-site scope 를 넓힌다. `_process` 내부에서 `key` / analysis mode 로 판별하는 편이 안전하다.
- **W1 Plan 06 deps split:** in-file subphase 로 리스크는 줄었지만, 실행 단위로는 아직 크다. 별도 plan 파일 split 권장.
- **W2 Lambda timeout 240s:** 충분.
- **W3 audit vs result 분리:** 충분한 방향. Plan 04/03 에 top-level `geminiB/geminiD` audit 와 user-visible result 분리 의도가 있다.
- **W4 alias mapping:** `STUDIO_ALIAS_OVERRIDES` 자체는 충분. 그러나 Plan 07 engine import path 가 새 blocker 다.
- **W5 runtime config:** AI-SPEC E5 는 runtime config 로 고쳐졌다. Plan 02 일부 문구는 env auto-escalation 뉘앙스가 남아 있어 정리 필요.
- **W6 local eval:** Plan 06 must_have 는 local eval 로 고쳐졌지만 objective/artifact/AI-SPEC 에 CI/CD 표현이 남아 있어 불충분.

### 2. B2 scope 축소가 D 가치를 유지하는지

**안전성은 올라갔지만, D 가치 정의를 좁혀야 한다.**

현재 축소안은 `KeypointReport` overlay 품질과 mirror hint audit 에는 가치가 있다. 즉 "사용자가 보는 keypoint confidence gap" 을 줄이는 gate 라면 Wave 3 진입 1순위 gap 으로 유지 가능하다.

반대로 "고수가 낮게 나오는 위양성" 이나 "DTW/KISMAM/8 관절각 점수 회복" 을 D 가치로 주장하면 아직 과대 주장이다. Plan 03 이 명시하듯 3D scoring 행렬은 불변이고, 점수 계산은 D 이전 값 그대로다. Success Criteria 를 다음처럼 분리하는 것을 권장한다.

- D-v1 in scope: `KeypointReport.confidence < 0.5` 비율 < 5%, overlay continuity 개선, mirror hint audit.
- D-v2 deferred: RTMW 3D 좌표계 계약 + 2D->3D lifter + scoring 재계산으로 점수 회복.

### 3. Plan 06 sub-phase 를 별도 plan 파일로 split 할지

**별도 파일 split 권장.** 현재 in-file 구조는 읽기에는 괜찮지만 실행 품질에는 불리하다.

추천 구조:

- `17-06A-PLAN.md`: telemetry deps + optional Phoenix bootstrap. Depends on `17-01`.
- `17-06B-PLAN.md`: 4 영역 span event wiring + tests. Depends on `17-02`~`17-05`.
- `17-06C-PLAN.md`: Promptfoo local eval dataset/assertions/README. Depends on `17-06B`.

이렇게 나누면 06A 를 일찍 검증할 수 있고, 06C 의 local eval 작업이 telemetry wiring 과 섞이지 않는다. GSD tooling 이 alphanumeric plan id 를 싫어하면 현재 파일은 parent 로 유지하되, 내부 task 별 summary/checkpoint 를 강제해야 한다.

### 4. Plan 01 Task 3/4 로 Wave 0 범위가 커진 것

**적절하다.** Task 3 model config 는 후속 plan 전체의 drift 를 막는 shared contract 이라 Wave 0 에 있어야 한다. Task 4 `_gemini_vision_enabled()` 도 Plan 02/03/04 의 "S3 재다운로드/RTMW 재실행 금지"가 의존하므로 선행 작업이 맞다.

다만 B/C default ON 때문에 `_gemini_vision_enabled()` 는 기본적으로 true 가 된다. 즉 Gemini coach/finding 을 명시적으로 끄지 않으면 모든 분석에서 `local_video_path` 보존 경로가 열린다. 이 정책이 의도라면 괜찮지만, disk cleanup / temp file lifecycle 테스트를 Plan 01 에 명시해야 한다.

## Blockers

### BLOCKER-1 - Plan 03/04 의 pipeline 삽입 위치가 실제 코드 순서와 맞지 않는다

현재 Plan 03 은 D wave 를 "assemble.build_keypoint_report 직후 + assemble.build_result 직전"에 넣으라고 한다 (`17-03-PLAN.md:124`, `17-03-PLAN.md:138`). 하지만 실제 코드에서는 `assemble.build_result` 가 먼저 호출되고 (`backend/functions/pipeline/app.py:1163`), `build_keypoint_report` 는 훨씬 뒤에 호출된다 (`backend/functions/pipeline/app.py:1263`). `complete_analysis(..., keypoint_report=...)` 는 그 이후다 (`backend/functions/pipeline/app.py:1275`).

추가로 `assemble.build_result` 시그니처에는 `keypoint_report` 인자가 없다 (`backend/shared/python/sunity_shared/analysis/assemble.py:271`). 그런데 Plan 03 은 `assemble.build_result` 입력의 `keypoint_report` 라고 적고 있다 (`17-03-PLAN.md:132`).

Risk:
- 실행자가 `build_result` 와 `KeypointReport` 순서를 재배치하려다 pipeline blast radius 를 키운다.
- Plan 04 는 `geminiD` 를 coach context 에 넣는다고 되어 있는데 (`17-04-PLAN.md:98`, `17-04-PLAN.md:135`), 현재 안전한 D 위치는 `build_result` 이후라 B 가 D 결과를 안정적으로 사용할 수 없다.

Better approach:
- Phase 17 v1 에서는 `geminiD` 를 B context 에서 제거한다. B 는 `sceneFlags`, `dimensionScores`, `joints`, `videoPath` 만 사용한다.
- D 는 `build_keypoint_report` 생성 직후, `complete_analysis` 직전에 실행한다. `build_result` 는 건드리지 않는다.
- Plan 03 의 문구를 "build_result 직전"이 아니라 "build_keypoint_report 생성/upsample 후, keypoint_report_dict 변환 및 complete_analysis 직전"으로 바꾼다.
- Plan 03 test 도 `assemble.build_result` 인자 검증 대신 `complete_analysis(keypoint_report=augmented_dict, gemini_d=...)` 검증으로 바꾼다.

### BLOCKER-2 - B2 축소 설계가 AI-SPEC/RESEARCH/PLAN-CHECK 에 아직 반영되지 않았다

Plan 03 내부는 B2 축소가 반영됐지만 상위 계약 문서에는 옛 설계가 남아 있다.

Evidence:
- `17-AI-SPEC.md:47` 은 "영역 D 출력은 RTMW keypoint 행렬에 직접 주입 → DTW + 8 관절각 차원 점수 계산"이라고 되어 있다.
- `17-RESEARCH.md:97`~`17-RESEARCH.md:109` 는 `coco_array[:, :, 3].min(axis=1) < 0.5` 와 `augment_low_confidence(..., coco_array)` pseudo-code 를 그대로 둔다.
- `17-PLAN-CHECK.md:21`, `17-PLAN-CHECK.md:119` 는 RTMW 행렬 in-place 주입과 `KeypointReport.data confidence` 를 여전히 성공 근거로 본다.
- `17-AI-SPEC.md:704` 는 E7 을 RTMW confidence 기준으로 정의한다. B2 이후에는 `KeypointReport.confidence` 또는 `1 - confidence` 기준으로 다시 써야 한다.

Risk:
- 실행 agent 가 Plan 03 보다 AI-SPEC/RESEARCH 를 더 상위 계약으로 보고 old D 설계를 되살릴 수 있다.
- 1차 review 의 핵심 blocker B2 가 우회적으로 재발한다.

Better approach:
- `AI-SPEC.md` Output Consequence 를 "D 출력은 user-visible `KeypointReport.data/confidence` 보강 + mirror hint audit. scoring 행렬 주입은 deferred" 로 교체.
- `RESEARCH.md` wave pseudo-code 를 Plan 03 의 `KeypointReport` 기반 흐름으로 교체.
- `17-PLAN-CHECK.md` 의 SC4 를 `KeypointReport.confidence` 기준으로 고치고, RTMW in-place 주입 표현을 제거.
- D deferred section 을 상위 문서에도 명시한다.

### BLOCKER-3 - Plan 07 의 `_RTMWNlfCompat` import 지시가 실제 코드와 맞지 않는다

Plan 07 은 `backend/scripts/extract_reference_angles.py` 에서 `from sunity_shared.analysis.pose_estimator import _RTMWNlfCompat as PoseEstimator` 로 swap 하라고 한다 (`17-07-PLAN.md:100`). 하지만 `_RTMWNlfCompat` 는 `backend/functions/pipeline/app.py:305` 에 정의되어 있고, `pose_estimator.py` 에는 `NlfPoseEstimator` 만 있다 (`backend/shared/python/sunity_shared/analysis/pose_estimator.py:68`).

Risk:
- Plan 07 실행 시 import 가 바로 실패한다.
- 더 나쁜 경우 `backend/functions/pipeline/app.py` 의 private class 를 script 에서 직접 import 하게 되어 Lambda pipeline module import side-effect 와 boto3/client 초기화까지 끌고 올 수 있다.

Better approach:
- `_RTMWNlfCompat` 를 shared import 가능한 module 로 추출한다. 예: `sunity_shared.analysis.pose_engines.rtmw.compat.RTMWNlfCompat`.
- `pipeline/app.py` 와 `extract_reference_angles.py` 가 그 shared class 를 같이 import 하게 한다.
- 또는 script 가 `RTMWPoseEngine` + `to_coco17_array` 를 직접 사용하고, pipeline compatibility wrapper 이름을 참조하지 않는다.

## Warnings

### WARNING-1 - Plan 06 은 local eval 로 고쳤지만 CI/CD 표현이 아직 남아 있다

Plan 06 must_have 는 "local eval" 로 잘 바뀌었지만, objective 에는 여전히 "Promptfoo CI/CD 회귀 게이트", "PR 마다 회귀 자동 검증", "E5 auto-escalation gate 활성"이 남아 있다 (`17-06-PLAN.md:89`~`17-06-PLAN.md:91`). artifact 설명도 "Promptfoo CI 회귀 게이트 config" 라고 되어 있다 (`17-06-PLAN.md:64`~`17-06-PLAN.md:66`).

AI-SPEC 도 `Promptfoo - CI/CD prompt regression` 과 "PR 마다 자동 회귀 검증"을 유지한다 (`17-AI-SPEC.md:716`), 그리고 CI/CD Integration 섹션은 merge gate 를 설명한다 (`17-AI-SPEC.md:760`~`17-AI-SPEC.md:781`).

Recommendation:
- Phase 17 에서는 "local eval config" 로 표현을 통일한다.
- `.github/workflows/phase17-evals.yml` / merge block / PR block 은 후속 plan 으로 분리한다.

### WARNING-2 - Plan 02 는 model config 단일 source 를 완전히 따르지 않는다

Plan 01 은 `gemini/config.py` 를 단일 source 로 만들고 Plan 02/03/04/05 는 상수 import 만 하라고 한다 (`17-01-PLAN.md:33`, `17-01-PLAN.md:178`). 그런데 Plan 02 는 여전히 "env GEMINI_C_MODEL default gemini-3.5-flash" 와 "GEMINI_C_MODEL_OVERRIDE 우선"을 직접 적는다 (`17-02-PLAN.md:94`).

Recommendation:
- Plan 02 에 `from sunity_shared.gemini import config as gemini_config` 를 명시.
- model 선택은 `resolve_model("C", env_override=os.environ.get("GEMINI_C_MODEL_OVERRIDE") or os.environ.get("GEMINI_C_MODEL"))` 같은 단일 path 로 박는다.
- "auto-escalation gate" 문구는 runtime config 쪽으로 옮기고 env override 는 manual emergency 로만 표현한다.

### WARNING-3 - Plan 02 의 `_process(..., is_reference)` 확장은 scope 대비 이득이 작다

Plan 02 는 `_process` 시그니처에 `is_reference` 를 추가하고 RunPod/server caller 도 갱신하라고 한다 (`17-02-PLAN.md:117`, `17-02-PLAN.md:124`, `17-02-PLAN.md:128`). 1차 review 의 B4 의도는 "재다운로드/재추론 금지"였지 `_process` signature 확대가 아니다.

Risk:
- Lambda fallback, RunPod server, tests, any direct internal caller 를 모두 맞춰야 한다.
- reference 판별 하나 때문에 call-site drift 가 커진다.

Recommendation:
- `_process(bucket, key, uid, analysis_id)` 시그니처는 유지한다.
- `is_reference = key.startswith("reference/") or analysis_doc.mode == "mode1_register"` 를 `_process` 내부에서 계산한다.
- Firestore 조회가 부담이면 우선 S3 key prefix 를 1차 source 로 쓰고, mode 조회는 reference path 일 때만 보강한다.

### WARNING-4 - Plan 04 의 fallback 계약 문구가 아직 혼재되어 있다

Plan 04 Task 1 은 "절대 None 반환 X" 를 잘 명시한다 (`17-04-PLAN.md:101`). 하지만 must_have/objective/key_links/done 에는 "None 반환 시 Cerebras 폴백"이 남아 있다 (`17-04-PLAN.md:25`, `17-04-PLAN.md:54`, `17-04-PLAN.md:59`, `17-04-PLAN.md:122`).

Recommendation:
- `None` 을 전부 `{}` 또는 `{"_fallbackReason": ...}` 로 교체.
- `_fallbackReason` 은 audit-only, `assemble.build_result` 에는 reserved key strip 후 전달한다는 계약만 남긴다.

### WARNING-5 - Plan 07 의 success metric field 가 잘못됐다

Plan 07 은 "KeypointReport.data 의 confidence < 0.5" 라고 반복한다 (`17-07-PLAN.md:24`, `17-07-PLAN.md:50`, `17-07-PLAN.md:124`, `17-07-PLAN.md:156`, `17-07-PLAN.md:165`). 실제 `KeypointReport.data` 는 flat x/y 좌표이고 confidence 는 별도 field 다 (`backend/shared/python/sunity_shared/analysis/assemble.py:393`~`backend/shared/python/sunity_shared/analysis/assemble.py:448`).

Recommendation:
- 전부 `KeypointReport.confidence < 0.5` 로 교체.
- ratio 산식도 `sum(c < 0.5 for c in report.confidence) / len(report.confidence)` 형태로 명시한다.

### WARNING-6 - `_gemini_vision_enabled()` default ON 정책은 명시적 운영 결정이 필요하다

Plan 01 Task 4 는 `GEMINI_COACH_ENABLED` 와 `GEMINI_FINDING_ENABLED` 를 default `"1"` 로 본다 (`17-01-PLAN.md:193`). 그러면 Gemini recognizer 를 꺼도 Phase 17 기본 설정에서는 `keep_local_video=True` 가 된다.

이건 B/C default ON 이 의도라면 맞다. 다만 temp video 보존 경로가 모든 분석에서 열리므로 `finally` cleanup 회귀가 반드시 필요하다.

Recommendation:
- Plan 01 에 "B/C default ON 이므로 기본 분석에서도 local video 보존 후 finally cleanup" 테스트를 추가한다.
- disk budget / temp file deletion failure logging 을 threat model 에 한 줄 추가한다.

## External Source Check

Model ID 는 2026-06-12 기준 Google 공식 Gemini API model page 로 확인했다.

- `gemini-3.1-pro-preview`: https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview
- `gemini-3.5-flash`: https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash

## Minimal Patch List Before Execute

1. Patch `17-AI-SPEC.md`, `17-RESEARCH.md`, `17-PLAN-CHECK.md` to remove D `coco_array` injection and old confidence semantics.
2. Patch `17-03-PLAN.md` insertion point to run after `build_keypoint_report` and before `complete_analysis`, not before `build_result`.
3. Patch `17-04-PLAN.md` to remove `geminiD` from B context for v1, unless D is intentionally moved earlier.
4. Patch `17-07-PLAN.md` engine swap to use a shared RTMW adapter module or direct `RTMWPoseEngine`, not `pose_estimator._RTMWNlfCompat`.
5. Patch Plan 06 and AI-SPEC CI/CD wording to "local eval only"; CI gate is separate follow-up.
6. Patch Plan 02 to keep `_process` signature stable and use `gemini_config.resolve_model`.
7. Split Plan 06 into `06A/06B/06C` files if the GSD executor accepts alphanumeric plan ids.
