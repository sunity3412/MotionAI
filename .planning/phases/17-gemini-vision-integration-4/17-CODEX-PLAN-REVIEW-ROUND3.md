# Phase 17 Plan Review Round 3 - Codex

> Scope: commit `138d6b6` 기준 3차 plan review.
> 목적: 2차 패치 후 execute 진입 가능 여부, 남은 정합성 리스크, 더 나은 구현 방안 제시.
> 결론: **execute 보류 권고.** 1차/2차의 핵심 blocker는 상당히 닫혔지만, 문서 잔재가 executor에게 서로 다른 구현 지시를 주는 지점이 아직 있다.

---

## Verdict

**ISSUES FOUND - 5 BLOCKER + 5 WARNING.**

2차 패치로 다음은 대체로 충분해졌다.

- 모델 ID single source: Plan 01 `gemini/config.py` 중심으로 정리됨.
- B2 scope reduction: D-v1이 `KeypointReport.data/confidence`와 mirror hint만 다루고, 3D scoring 행렬 mutate 금지는 큰 방향이 맞음.
- B3 writer interface: `GeminiCoachWriter.write(context: dict) -> dict`로 Cerebras와 맞춰짐.
- B4 local video gate: S3 재다운로드/RTMW 재실행 금지가 Plan 01/02/03/04에 박힘.
- Plan 06 split: 06A/06B/06C in-file 구조는 현재 GSD plan 번호 체계에서는 수용 가능.

다만 execute를 시작하면 아래 5개는 실제 구현 오류나 workflow gate 충돌로 이어질 가능성이 높다.

---

## BLOCKER-1 - C/B 병렬 pseudo-code가 `scene_flags`를 정의 전에 사용한다

**Evidence**

- `17-RESEARCH.md:102-118`에서 `wave2()`가 `_build_coach_context(..., scene_flags=scene_flags)`를 호출하지만, `scene_flags`는 `await asyncio.gather(wave1(), wave2())`의 반환값으로 처음 정의된다.
- 같은 문서 `17-RESEARCH.md:117-118`은 C와 B를 병렬 실행한다고 지시한다.
- Plan 04는 B context에 `sceneFlags`를 포함한다고 명시한다 (`17-04-PLAN.md:96-99`, `17-04-PLAN.md:136`).

**Risk**

executor가 RESEARCH pseudo-code를 그대로 따르면 Python에서는 `scene_flags`가 unbound variable이다. 더 중요한 문제는 설계 의도가 두 갈래로 갈라져 있다는 점이다.

- B가 C의 `sceneFlags`를 사용하려면 C가 먼저 끝나야 한다.
- B와 C를 병렬로 돌리려면 B context에서 `sceneFlags`를 빼야 한다.

**Recommendation**

둘 중 하나로 명시해야 한다.

1. **Option A - C 먼저, B 다음.** `scene_flags = await wave_c()` 후 `_build_coach_context(..., scene_flags=scene_flags)`로 B를 호출한다. 지연은 Flash 2~5초 정도 늘지만, Plan 04의 prompt 설계를 보존한다.
2. **Option B - B/C 병렬 유지.** B context에서 `sceneFlags`를 제거하고, C 결과는 Firestore audit 및 D skip gate에만 사용한다.

**My opinion**

Plan 04가 `occlusion_severe/backbend_present`를 코칭 prompt hint로 쓰도록 설계되어 있으므로 **Option A가 더 일관적**이다. 다만 latency 목표가 진짜 hard gate라면 Option B가 더 안전하다. 어느 쪽이든 현재처럼 “B가 sceneFlags를 받으면서 C와 병렬”은 구현 불가능하다.

---

## BLOCKER-2 - Plan 04 Task 2가 여전히 D 이후 B 삽입과 `geminiD` context를 지시한다

**Evidence**

- Plan 04 Task 2 behavior는 `_process`의 “Plan 03 augment_low_confidence 직후 + assemble result 직전”에 B 호출을 넣으라고 한다 (`17-04-PLAN.md:132-134`).
- 같은 task action은 기존 Cerebras context에 `videoPath/sceneFlags/dimensionScores/geminiD` 4개를 추가하라고 지시한다 (`17-04-PLAN.md:145`).
- 그러나 같은 파일 앞부분은 v1에서 `geminiD` 키를 박지 않는다고 정정했다 (`17-04-PLAN.md:99`, `17-04-PLAN.md:136`).
- 실제 pipeline 순서는 coach writer 호출 후 `assemble.build_result`가 먼저 실행되고 (`backend/functions/pipeline/app.py:1149-1177`), `build_keypoint_report`는 그 뒤다 (`backend/functions/pipeline/app.py:1263-1275`).

**Risk**

이 지시는 2차 R-B1 정정과 정면 충돌한다. executor가 Task 2 action을 따르면 B를 D 뒤로 옮기거나, `geminiD`를 B context에 다시 넣는 regression이 생긴다.

**Recommendation**

Plan 04 Task 2를 아래처럼 고쳐야 한다.

- B 삽입 위치: 기존 coach writer 호출부 (`backend/functions/pipeline/app.py:1149-1163`)를 교체 또는 감싼다. `assemble.build_result` 직전이다.
- B context v1 필드: `mode`, `joints`, `videoPath`, `dimensionScores`, `sceneFlags`까지만 허용한다.
- `geminiD`는 v1에서 금지하고, D-v2에서 “D -> B -> build_result” 순서로 재설계할 때만 다시 연다.
- BLOCKER-1에서 Option A를 택하면 C를 먼저 호출한 뒤 이 위치에서 B를 호출한다. Option B를 택하면 `sceneFlags`도 제거한다.

---

## BLOCKER-3 - Plan 03 D wiring이 `_process`에 없는 `coco_array`, `frame_w`, `frame_h`를 사용한다

**Evidence**

- Plan 03은 D gate에서 `coco_array[:, :, 3].max(axis=1)`를 쓰고 (`17-03-PLAN.md:128`), `augment_low_confidence(..., frame_w, frame_h)`를 호출한다 (`17-03-PLAN.md:129`, `17-03-PLAN.md:137`).
- 실제 `_VideoAnalysisInputs`는 `angles`, `student_profile`, `pose_frames`, `local_video_path`, `pole_axis_measurement`만 반환한다 (`backend/functions/pipeline/app.py:464-485`).
- `_extract_video_analysis_inputs()` 안에서 `keypoints_4ch = to_coco17_array(pose_frames)`는 계산되지만 helper 밖으로 반환되지 않는다 (`backend/functions/pipeline/app.py:527-529`).
- `frames`도 helper 내부 local 변수라 `_process`의 D 삽입 위치에서는 `frame_w/h`를 알 수 없다 (`backend/functions/pipeline/app.py:511-520`, `backend/functions/pipeline/app.py:537`).

**Risk**

Plan 03 구현 시점에 바로 NameError 또는 ad-hoc 재계산이 발생한다. 특히 frame 크기를 원본 비디오 기준으로 잡을지, RTMW가 사용한 extracted/resized frame 기준으로 잡을지 애매해진다.

**Recommendation**

Plan 03에 `_VideoAnalysisInputs` 계약 확장을 명시한다.

- `keypoints_4ch: np.ndarray` 추가: 기존 `to_coco17_array(pose_frames)` 결과를 반환한다.
- `frame_shape: tuple[int, int]` 또는 `frame_width/frame_height` 추가: `frames.frames` 또는 `np.asarray(frames)` 기준의 `(height, width)`를 반환한다.
- D의 low-uncertainty selection은 `inputs.keypoints_4ch[:, :, 3].max(axis=1) > 0.5`를 사용한다.

**My opinion**

frame 크기가 실제로 prompt에만 쓰이고 `KeypointReport.data`는 이미 normalized 좌표라면, `augment_low_confidence` signature에서 `frame_width/frame_height`를 제거하는 편이 더 낫다. Gemini에게 “normalized [0,1] 좌표만 반환”하게 하면 coordinate-space 혼선이 줄어든다. 그래도 frame dimensions가 필요하면 반드시 RTMW frame extractor가 만든 frame 크기를 source로 박아야 한다.

---

## BLOCKER-4 - Plan 07의 RTMW 전환 패치가 문서 상단/검증/성공조건에 일관되게 반영되지 않았다

**Evidence**

- Plan 07 상단 truth/artifact는 여전히 `_RTMWNlfCompat` swap을 말한다 (`17-07-PLAN.md:21`, `17-07-PLAN.md:27-29`).
- objective와 task name도 `NlfPoseEstimator -> _RTMWNlfCompat`로 남아 있다 (`17-07-PLAN.md:48`, `17-07-PLAN.md:78`).
- behavior에서는 `_RTMWNlfCompat`을 박지 말고 `RTMWPoseEngine + to_coco17_array` 직접 사용이라고 정정했다 (`17-07-PLAN.md:86`).
- verify는 `_RTMWNlfCompat`가 없어야 한다고 검사한다 (`17-07-PLAN.md:103`).
- 그런데 verification과 success criteria는 다시 `_RTMWNlfCompat`가 있어야 한다고 말한다 (`17-07-PLAN.md:153`, `17-07-PLAN.md:161`).

**Risk**

이 상태로는 같은 task 안에 서로 반대되는 grep gate가 존재한다. executor 또는 checker가 어느 줄을 따르느냐에 따라 실패/성공 판정이 바뀐다.

**Recommendation**

Plan 07 전체를 한 방향으로 통일한다.

- 표현: “NlfPoseEstimator -> RTMWPoseEngine direct path”
- artifact `provides`: `RTMWPoseEngine + to_coco17_array direct extraction`
- artifact `contains`: `RTMWPoseEngine`
- verification: `grep -c "RTMWPoseEngine" >= 1` 그리고 `! grep -q "_RTMWNlfCompat"`
- success criteria: `_RTMWNlfCompat swap`가 아니라 `RTMWPoseEngine direct path`로 수정

private adapter를 script에서 import하지 않는 2차 결정은 맞다. 그 결정이 문서 전체에 아직 퍼지지 않은 것이 문제다.

---

## BLOCKER-5 - `17-PLAN-CHECK.md`가 여전히 blocker verdict를 유지한다

**Evidence**

- `17-PLAN-CHECK.md:10`은 아직 `ISSUES FOUND - 1 BLOCKER + 5 WARNING`이라고 말한다.
- `17-PLAN-CHECK.md:127-140`은 Plan 06 client.py telemetry timing race를 BLOCKER로 유지한다.
- 결론도 `ISSUES FOUND - 1 BLOCKER + 5 WARNING`이며, planner에게 blocker fix를 요청한다 (`17-PLAN-CHECK.md:239-255`).
- 반면 commit `138d6b6` 메시지는 “execute 진입 보류 해소”라고 선언한다.

**Risk**

GSD workflow의 gate artifact와 commit intent가 충돌한다. 실제 기술 blocker가 아니라고 판단하더라도, gate 문서가 blocker 상태로 남아 있으면 다음 executor는 보수적으로 멈추는 것이 맞다.

**Recommendation**

둘 중 하나를 선택해야 한다.

1. Plan 06 telemetry race를 실제로 반영한다. 예: Phoenix bootstrap/span no-op hooks는 Plan 01로 당기고, dataset/assertion은 Plan 06에 둔다.
2. 이 이슈를 warning으로 downgrade한다고 명시한다. 그 경우 `17-PLAN-CHECK.md`의 verdict, section 7, conclusion을 모두 갱신하고 downgrade 이유를 남긴다.

**My opinion**

기술적으로는 “첫 호출 trace 누락 가능성”이 production blocker인지 논쟁 가능하다. 하지만 현재 상태에서는 **문서 gate blocker**가 맞다. execute 전 `17-PLAN-CHECK.md`를 반드시 재검증 상태로 갱신해야 한다.

---

## WARNING-1 - `17-RESEARCH.md`에 1차 설계 잔재가 많이 남아 있다

**Evidence**

- D 설명이 아직 “RTMW confidence < 0.5”라고 되어 있다 (`17-RESEARCH.md:43`).
- pipeline mapping이 `_RTMWNlfCompat.estimate` 직후 + `kismam.assess` 직전 wave 추가라고 되어 있다 (`17-RESEARCH.md:51`).
- pseudo-code import가 `write_coach_gemini`를 사용하지만, Plan 04의 실제 설계는 `GeminiCoachWriter`다 (`17-RESEARCH.md:92-94`).
- pseudo-code가 `_POSE_ESTIMATOR.estimate_with_profile(frames)`를 호출하지만, 현재 pipeline은 `_extract_video_analysis_inputs()`와 `_RTMW_ENGINE.estimate()` 중심이다 (`17-RESEARCH.md:97`, `backend/functions/pipeline/app.py:488-529`).
- “wave 2(B/D)” 표현이 남아 있는데, 2차 이후 D는 B와 분리되었다 (`17-RESEARCH.md:166`).
- Plan 07 관련 `_RTMWNlfCompat` swap 잔재가 남아 있다 (`17-RESEARCH.md:261`, `17-RESEARCH.md:342`, `17-RESEARCH.md:376`).
- Promptfoo CI/CD config 표현도 아직 남아 있다 (`17-RESEARCH.md:336`).

**Risk**

executor가 RESEARCH를 source-of-truth로 강하게 참고하면 Plan 02/03/04/07과 다른 구현으로 끌려간다.

**Recommendation**

RESEARCH는 implementation pseudo-code라기보다 design history로 낮추거나, §4 pseudo-code를 현재 plan과 동일하게 다시 쓴다. 최소한 B/C 순서, D 위치, Plan 07 RTMW direct path, local eval wording은 정리해야 한다.

---

## WARNING-2 - `uncertainty_proxy`와 `KeypointReport.confidence`를 “동등”하다고 쓰는 부분은 정밀하지 않다

**Evidence**

- AI-SPEC E7은 `1 - uncertainty_proxy`가 `KeypointReport.confidence`와 동등하다고 적는다 (`17-AI-SPEC.md:704`).
- Plan 03 Task 1은 `original_uncertainty_proxy`를 `keypoint_report_2d.confidence`의 invert로 기록한다고 한다 (`17-03-PLAN.md:104`).
- 실제 `to_coco17_array`의 4번째 채널은 3D `uncertainty_proxy`다 (`backend/shared/python/sunity_shared/analysis/pose_frame.py:326-351`).
- `KeypointReport.confidence`는 user-visible 2D report의 confidence field다. 이 값이 항상 3D `uncertainty_proxy`와 1:1 동일하다는 계약은 plan에 충분히 박혀 있지 않다.

**Risk**

D 진입 frame 선택은 3D uncertainty 기준인데, eval/fail 판정은 KeypointReport confidence 기준으로 섞인다. 둘이 실제로 같은 source에서 계산된다는 보장이 깨지면 “저신뢰 frame만 호출” 회귀 테스트가 틀린 값을 검증할 수 있다.

**Recommendation**

- selection metric: `rtmw_uncertainty_proxy = inputs.keypoints_4ch[:, :, 3]`
- user-visible metric: `keypoint_report.confidence`
- audit field: `originalRtmwUncertaintyProxy`와 `originalKeypointConfidence`를 분리
- `original_uncertainty_proxy = 1 - keypoint_report.confidence` 같은 이름은 피한다.

---

## WARNING-3 - AI-SPEC에 남은 표현 일부가 2차 정정과 어긋난다

**Evidence**

- C model escalation 설명은 runtime config를 쓰도록 정정됐지만, env override 중심 표현이 아직 섞여 있다 (`17-AI-SPEC.md:702`).
- D dataset row가 아직 “RTMW confidence < 0.3 frame”이라고 되어 있다 (`17-AI-SPEC.md:802`).
- checklist는 여전히 “CI/CD eval integration specified”라고 한다 (`17-AI-SPEC.md:925`).

**Risk**

작은 wording처럼 보이지만, Phase 17은 모델 선택/runtime config/eval gate가 핵심이다. 표현이 섞이면 reviewer가 “자동 CI gate가 있는가”, “C 모델은 env로만 바뀌는가”, “D threshold는 confidence인가 uncertainty인가”를 다시 묻게 된다.

**Recommendation**

- C model: runtime config가 primary, env는 emergency manual override라고 명확히 분리.
- D dataset: `KeypointReport.confidence < 0.5` sample 또는 `rtmw_uncertainty_proxy > 0.5` sample 중 하나로 명시.
- checklist: “local eval specified; CI gate deferred”로 수정.

---

## WARNING-4 - latency budget 15s vs 40s 불일치가 아직 남아 있다

**Evidence**

- PLAN-CHECK는 ROADMAP SC5의 “latency 추가 < 15s”와 AI-SPEC/Plan 06의 `p95 <= 40s`가 충돌한다고 지적한다 (`17-PLAN-CHECK.md:22`, `17-PLAN-CHECK.md:144-153`).
- AI-SPEC E8도 40초 budget을 기준으로 한다 (`17-AI-SPEC.md:705`, `17-AI-SPEC.md:780`).

**Risk**

execute 후 UAT에서 “계획상 성공”과 “ROADMAP상 실패”가 동시에 발생할 수 있다.

**Recommendation**

Phase 17에서 정확도가 latency보다 우선이라는 의사결정이면 ROADMAP SC5를 수정한다. 반대로 15초가 hard gate면 B/D를 동기 path에서 빼거나, B를 async post-processing으로 돌리는 설계를 Plan 04/06에 다시 박아야 한다.

---

## WARNING-5 - Plan 06 in-file 06A/06B/06C는 유지 가능하지만 gate 문서와 맞춰야 한다

**Assessment**

사용자가 물은 “06A/B/C를 별도 plan 파일로 split할지”에 대한 내 의견은 **현재는 in-file 유지가 낫다**다.

이유:

- GSD wave/dependency는 `17-06-PLAN.md` 하나를 기준으로 이미 잡혀 있다.
- `17-06A-PLAN.md` 같은 alphanumeric split은 tooling이 plan discovery에서 놓칠 수 있다.
- scope는 커졌지만 Phoenix wiring, LLM judge/sampling, local eval이 하나의 eval plan으로 묶이는 것은 논리적으로 방어 가능하다.

단, `17-PLAN-CHECK.md`가 Plan 06 split/telemetry timing을 blocker로 유지하고 있으므로 문서 상태를 맞춰야 한다.

**Recommendation**

- 파일은 유지한다.
- Plan 06 안에 “06A = Phoenix bootstrap/hook, 06B = judge/sampling, 06C = local eval dataset/assertions” 체크포인트를 더 명확히 둔다.
- Plan 01로 당긴 Task 3/4가 있다면 Plan 06에서는 “Phoenix bootstrap은 Plan 01에서 완료, 여기서는 eval artifact만”으로 중복 범위를 줄인다.
- PLAN-CHECK verdict를 이 결정과 일치시킨다.

---

## Requested Areas Answered

### 1. 1차 review의 4 BLOCKER + 6 WARNING 패치가 충분한가

**부분적으로 충분.** core intent는 대부분 반영됐다. 그러나 문서 잔재가 아직 executor에게 반대 지시를 준다. 특히 Plan 04 Task 2, Plan 07 verification/success, PLAN-CHECK verdict는 execute 전에 다시 패치해야 한다.

### 2. B2 scope 축소가 D 가치를 유지하면서 안전하게 박혔는가

**방향은 맞다.** D-v1을 user-visible `KeypointReport` 보강으로 제한하고, 3D scoring 행렬을 건드리지 않는 결정은 안전하다. Wave 3 진입의 1순위 gap gate로서도 의미가 있다.

단, D가 “점수 회복”이 아니라 “overlay/diagnostic 회복”이라는 점은 모든 문서에서 일관되게 말해야 한다. 실제 점수 회복은 D-v2로 deferred된 상태다. 또한 `uncertainty_proxy`와 `KeypointReport.confidence`를 분리해 audit하면 B2의 안전성이 더 강해진다.

### 3. Sub-phase 06A/B/C를 별도 plan 파일로 split할지

**별도 split 비권장.** 지금은 in-file 유지가 tooling risk가 낮다. 대신 Plan 06 내부 체크포인트와 output summary를 분리하고, PLAN-CHECK의 blocker/downgrade 상태를 맞추는 편이 낫다.

### 4. Plan 01 Task 3/4 신설로 Wave 0 범위가 커진 게 적절한가

**적절하다.** model config single source와 `_gemini_vision_enabled()`는 후속 Plan 02/03/04/05가 모두 공유하는 foundation이다. Wave 0/1에 두는 것이 맞다.

다만 Plan 01에 너무 많은 runtime/eval wiring까지 빨아들이면 다시 scope가 커진다. Plan 01은 config, schema, guardrail, local-video gate까지만 두고, Phoenix/eval artifact는 Plan 06에 남기는 경계가 좋다.

### 5. 새로 발견되는 issue

이번 3차에서 새로 중요한 것은 3개다.

- C/B 병렬 pseudo-code의 unbound `scene_flags`.
- Plan 03 D가 필요한 `coco_array/frame_w/frame_h`가 현재 `_process` scope에 없음.
- Plan 07이 `_RTMWNlfCompat` 금지와 요구를 동시에 검증함.

---

## Minimal Patch List Before Execute

1. `17-RESEARCH.md`와 `17-04-PLAN.md`에서 C/B ordering을 하나로 결정한다. 내 권고는 C 먼저, B 다음.
2. `17-04-PLAN.md` Task 2에서 `geminiD` context와 “augment 직후 B 삽입” 지시를 제거한다.
3. `17-03-PLAN.md`에 `_VideoAnalysisInputs.keypoints_4ch` 및 frame shape 반환, 또는 `augment_low_confidence`에서 frame dimension 제거를 명시한다.
4. `17-07-PLAN.md`의 `_RTMWNlfCompat` 잔재를 전부 `RTMWPoseEngine direct path`로 바꾼다.
5. `17-PLAN-CHECK.md` verdict를 실제 결정과 맞춘다. blocker 유지면 Plan 01/06을 고치고, downgrade면 이유를 남긴다.
6. AI-SPEC의 D threshold, CI wording, uncertainty/confidence equivalence를 정리한다.

---

## Execute Gate

현재 상태로는 **execute 진입 보류**가 맞다. 패치량은 크지 않다. 대부분 새 기능 설계가 아니라 문서 정합성 정리다. 위 blocker 5개를 닫으면 Phase 17은 execute 가능한 수준으로 들어갈 수 있다.
