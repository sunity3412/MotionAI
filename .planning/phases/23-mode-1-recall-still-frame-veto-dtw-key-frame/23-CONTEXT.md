# Phase 23: Mode 1 결함 recall 복구 — still-frame veto + 기준선 정량화 - Context

**Gathered:** 2026-06-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Mode 1(정은지 기준 비교) veto/비교의 **입력 방식**을 "영상 통째 Gemini 업로드"에서 "DTW worst-pose **단일 key-frame(들)** + 부위별 프롬프트 + 프레임×부위 union + N-sample"으로 교체해, 전체영상 VLM이 구조적으로 놓치던 **상체 결함(팔-폴 갭/고개젖힘/팔꿈치) recall을 복구**한다. 위양성은 늘리지 않는다(깨끗 프레임/정타 = none 유지). 더불어 결함 출력에 **기준선 정량화 레이어**(각도=직접 측정 / 거리=몸-상대 칸·층 / 기준선=동작별)와 **증상→root cause(힘/폴밀착) 묶음 코칭**을 추가한다. **Mode 3 정량화/정렬은 본 phase 범위 아님 — Backlog B-15a 로 공식 defer(D-07).** (이 문단 이전 버전의 "Mode 3 에도 동일 적용"은 D-07 정정으로 폐기 — ITERATION2 LOW-1.)

**근거:** 2026-06-22 deep-research(소스 23개, 18 confirmed — whole-video VLM은 프레임 독립 인코딩으로 미세 결함을 놓치는 구조적 한계) + B 스파이크(kip-up: whole-video=다리만, 5프레임 배치=팔1, **단일 프레임=좌/우팔+고개 풀 recall, 위양성 0**). 레버는 프롬프트가 아니라 **입력 granularity**임이 실증됨.

**경계 (scope creep 아님):** 채점 수식(KISMAM tol/감점 공식) 변경 아님 — veto **입력**과 출력 정량화에 집중. 자체 모델 파인튜닝은 Phase 22. reference 등록은 Phase 21. 구현/eval = Pod GPU 필요.

</domain>

<decisions>
## Implementation Decisions

### D-01: Mode 1 veto 입력 형태 = 학생 + 정은지 still 나란히
학생 worst-pose frame + **DTW로 매칭된 정은지 same-pose frame**을 나란히(side-by-side) Gemini에 입력한다. Mode 1의 "정은지 기준 비교" 설계를 유지하고 상대 편차를 포착하며, 기존 v7.0 비교 프롬프트(`_COMPARISON_PROMPT`)와 정합. (대안: 학생 단일 frame만 IPSF 평가 — 스파이크 방식, recall은 되나 reference 기준점 의미 약화 → 채택 안 함.)

### D-02: 정량화 표현 + v1 범위 = 각도 수치 + 몸-상대 칸/층 텍스트 (시각 오버레이 바로 후속)
v1 출력 = ① **관절각 직접 수치**("무릎 145° vs 정은지 178°, 33° 더 굽음, ↑펴라") + ② **거리는 몸-상대 칸/층 텍스트**("정은지 3칸, 너 2칸 ⅔"). 절대 cm/m 금지(단일 카메라 스케일 모호, 140/150 깨짐). **화살표 + 칸 시각 오버레이**는 기존 fault-zoom 확대비교 이미지 위에 **후속(v1.1)** — v1은 텍스트+각도 먼저, 백엔드 계산·저장까지(앱 표시는 후속 UI phase, D-07). "칸" = keypoint/폴/바닥 baseline 에서 **결정적 계산**한 정수 칸("정은지 3칸, 너 2칸 ⅔") — **percent 표기 금지**(`_SCORE_PATTERN` 누수, D-08). VLM 이 칸 수치를 지어내지 않음.

### D-03: DTW 정렬 신뢰도 폴백 = 다중프레임 union → 보류+표시
정렬 신뢰도(`MotionMatch.distance`)가 낮으면(시작점/템포 상이) 단일 프레임 대신 **worst-pose ±윈도우 다중프레임 union**으로. 그래도 낮으면 **veto 보류 + "비교 신뢰도 낮음" 표시**(거짓결함 fabrication 금지 — 객관성·위양성 게이트). 전체영상 폴백은 채택 안 함(그게 상체를 놓치는 원인이라).

### D-04: 증상→root cause 묶음 = Gemini 추론, "~로 보임" 가설
Gemini가 결함군(예: 팔꿈치 굽음 + 고개젖힘 동시)을 보고 가능한 root cause(힘 부족/폴 밀착 풀림)를 **기존 dual-coach "원인" 섹션에서 추론**한다. 단정 금지 — "~로 보임" 가설 형태(객관성: 사람-라벨 원인을 ground truth로 박지 않음). 룰기반 매핑은 brittle → 채택 안 함. (belle 도메인: 폴 자세는 힘/밀착이 root, 고개젖힘·삐뚤어짐은 동반 증상 = 창발 시스템.)

### D-05: recall 완전성 = 프레임×부위 union + N-sample
단일 호출은 1~2개만 보고(과소열거) → 부위별(상체/하체/라인) 프롬프트 × 선별 key-frame을 union하고, Phase 20의 N-sample 집계(`VISION_VETO_SAMPLES`, rank-median)를 still 경로에도 적용해 흔들림을 줄인다.

### D-06: 객관성·일반화·위양성 게이트 (불변)
- 사람 점수 라벨 ground truth 금지 — VisionVerdict에 score 필드 영구 부재 유지([[analysis-objectivity-no-human-scores]]).
- known-answer에 맞춘 유도 프롬프트/curve-fit 금지 — 프롬프트는 generic, recall은 자체 라벨셋으로 측정([[scoring-redesign-must-generalize-no-overfit]]).
- 깨끗 프레임/정타 = none 유지(스파이크 확인 — 특이도 보존). 결정론(같은 입력=같은 verdict) 유지.

### D-07: 스코프 정정 (belle 2026-06-22, cross-AI 리뷰 후)
- **Mode 1 집중. Mode 3 정량화/정렬은 공식 defer** → Backlog B-15a("Mode 3 즉석 2영상 비교")로 합류. 본 phase 는 Mode 1 still-frame veto + 정량화/코칭 백엔드.
- **정량화·코칭 = 백엔드 계산·저장·생성까지.** 앱 표시(result.tsx 각도/칸 렌더, coach-report 원인섹션 렌더)는 **후속 UI phase** 로 분리. SC#4/#5 "표시"→"계산·저장/생성"으로 정정(ROADMAP 반영). (D-02 시각 오버레이 v1.1 방침과 일관.)

### D-08: cross-AI 리뷰 hardening (Codex HIGH 반영)
- **precision/support 게이트** — part×frame union 이 단발 환각 결함을 살리지 않도록, differences 는 최소 support(샘플/프레임 N 중 K 이상)일 때만 인정, 미만은 descriptive-only/폐기. 위양성 비증가(D-06) 강화.
- **칸/층 = 결정적 기하 계산.** keypoint + 폴축(pole_geometry)/바닥/엉덩이-라인 baseline 에서 reach 를 계산 — **Gemini 가 수치를 지어내지 않음**. body_normalization 비율은 보조. **percent("100%") 표기 절대 금지** — `_SCORE_PATTERN` 누수 가드에 걸려 정상 verdict 가 폐기됨. "정은지 = 3칸" 식 정수 칸만.
- **provenance 필드** — 측정값은 `source: "geometry" | "vision_hypothesis"` + confidence/가시성 표기(특히 root-cause 가설).
- **DTW 신뢰도 = 글로벌+로컬.** `MotionMatch.distance`(글로벌) 만으로 부족 → 선택 프레임 주변 path 밀도/ref-frame 존재/keypoint 가시성·blur 로컬 신뢰도 추가. worst_pose_timestamp 가 상체 결함 프레임이 아닐 수 있음 — 부위별 worst 후보 고려.
- **23-01 배선 명시** — `_apply_vision_veto` 시그니처/콜사이트가 `reference_dtw_match`/ref angles 를 받도록 변경 명시. still-pair API(이미지 경로·프레임 메타·part scope·selector version) 정의. 캐시 키에 selector version/frame indices/top-K/window 포함.
- **23-03 eval = 실제 production 경로** — 어댑터 직접호출 아니라 `_apply_vision_veto` 전체 경로 통과. whole-video baseline 을 **동일 모델/버전으로 재실행**(apples-to-apples). 케이스 매트릭스 확장(elite clean/imperfect clean/occluded/tempo-shifted/spinning/known-fault). cold vs warm 캐시 결정론 분리. cost/latency 게이트 + machine-checkable pass/fail 필드.
- **호출수 상한 강화** — `MAX_VETO_CALLS` 가 호출수뿐 아니라 upload count + wall-clock budget 도 bound. File API 핸들은 추적 list 에서 일괄 delete.

### D-09: direct-review fix (2026-06-22, [[23-DIRECT-REVIEW.md]] — 통합/키잉 차원)
- **(HIGH-1) 코칭 순서** — 현 파이프라인은 coach detail(app.py:2578-2668)을 veto(2692) **이전**에 생성 → veto verdict 의 root_cause 가 `coach_details.detail2.causes` 에 못 들어감(SC#5 가 audit-only 로 거짓 통과). **fix:** veto 가 만든 `VisionFaultContext`(verdict+supported diffs+root-cause+provenance)를 **coach 작성 전에** 수집해 `_build_coach_context` 에 주입 → Gemini/Cerebras 가 `detail2.causes` 생성. 이후 cap 적용 + 같은 context 를 visionVeto audit 에도 attach. 테스트: fake verdict 의 root_cause 가 `visionVeto.rootCauseHypotheses` **와** `coachingTips[].detail2.causes[]` 둘 다에 나타남.
- **(HIGH-2) canonical FaultKey** — support gate 를 raw `body_part` 문자열로 세면 "왼팔/left arm/왼쪽 팔꿈치"가 분산돼 K 미달(recall 손실) + 모호한 "팔"이 양쪽으로 부풀려짐. **fix:** support 카운트 전에 `FaultKey(part_scope, side, keypoint_set, fault_kind)` 정규화. 모호 side=`unknown`(support 용); 양쪽 highlight 확장은 *저신뢰 표시 fallback* 일 뿐 두 side-specific 결함 증거 아님. `_union_differences` 는 정규화·support 통과 레코드만 받음. 테스트: 좌우 동시결함 / 한 결함의 한·영 alias / 모호 "팔"이 두 side 결함 안 만듦.
- **(HIGH-3) 같은-프레임 측정 계약** — 결정적 칸 공식도 틀린 프레임 재면 틀림. **fix:** `FramePairMeasurementContext`(user_frame_idx, ref_frame_idx, 그 인덱스의 keypointReport keypoints, baseline kind, 폴/바닥/힙 source, visibility, selector_version)에서만 각도델타·칸 계산. 필수 per-frame 입력 결측 시 static source pose 로 폴백 금지 → `quantificationStatus="unavailable"` + warning. 테스트: 일부러 mismatch 한 ref 프레임이 다른 칸 값을 내면 reject.
- **(MED-1) 예산소진 = fail-closed** — 부분 샘플링으로 `applied` 반환 금지(false-positive 게이트 약화). 최소 support quorum 미완 시 score-free `resource_limited`/`sampling_incomplete` status(3-way lockstep 추가) + telemetry(completedCalls/plannedCalls/uploadCount/durationMs/samplingComplete).
- **(MED-2) eval = runtime trace 게이트** — grep(소스에 `_apply_vision_veto` 문자열 존재)으로 통과 가능 → 우회 위험. 결과 JSON 에 `entrypoint/selectorVersion/studentFrameIndices/referenceFrameIndices/alignmentConfidence/cacheKey/cacheHit/callCount/uploadCount/durationMs/pathUsed` 런타임 trace 필드를 박고 그걸로 게이트. 가능하면 `_process` 레벨 통합 1케이스(real 또는 fake S3/Firestore).
- **(MED-3) 객관성 grep 정밀화** — recursive 로 `점수/100/percent` 문자열 거부하면 기존 정당한 가드 텍스트("점수 아님","숫자 점수 금지")를 깨거나 그 가드 제거를 유도(객관성 약화). **fix:** schema 는 property **키** `score|overall|rating|percent|100` 만 거부(description 의 부정문 허용); 프롬프트는 positive 점수 예시·`NN/100` 출력요청만 거부(부정 지시 허용); raw text 누수는 `_SCORE_PATTERN` 으로 유지.

### D-10: ITERATION2 아키텍처 재정렬 (2026-06-22, [[23-DIRECT-REVIEW-ITERATION2.md]] — D-09 HIGH-1 의 파급)
- **(HIGH-1) Gemini 호출 소유권 분리** — VisionFaultContext 가 coach **이전**에 필요해졌으므로 `_apply_vision_veto` 가 더 이상 Gemini 호출 소유자일 수 없다(아니면 Gemini 2회 호출 또는 coach 가 verdict 못 씀). **2-함수 계약:** `_collect_vision_fault_context(...) -> VisionFaultContext | status` = 프레임 선별·로컬/글로벌 정렬·still 이미지 추출·Gemini 호출·support 게이트·캐시 키·telemetry **소유**(coach 전 1회 실행). `_apply_vision_veto(score_result, vision_fault_context=...)` = **Gemini 호출 안 함**, downward cap + audit/status attach 만. 23-03 production 경로 정의를 "collect(coach 전) → coach writers 소비 → build_result → apply context"로 갱신. trace 필드에 `contextCollectedBeforeCoach=true`, `contextReusedForAudit=true`, `geminiCallCount=1`.
- **(HIGH-2) still 이미지 추출/cleanup/keypoint 가시성 계약** — still-pair API 가 이미지 경로를 요구하나 그 경로 생성/정리 계약 부재. **`SelectedFramePair` helper:** in=user/ref video path + MotionMatch + 후보 user frame indices + (pose_frames 또는 prebuilt keypoint reports); out=student/reference_frame_path + user/ref_frame_idx + 양 프레임 keypoints/confidence + cleanup handles. cleanup=`finally` 가 생성 이미지 파일 unlink(Gemini File API delete 와 독립). **keypoint visibility/confidence(로컬 정렬 H4 + FramePairMeasurementContext H3 입력)는 현재 veto 이후에 build 됨 → vision context 수집 전으로 이동**(또는 pose_frames 직접 사용). 테스트: `_upload_image` 가 존재안하는 경로로 호출되거나 예외 후 temp 프레임 파일이 남으면 실패.
- **(HIGH-3) 각도 의미 단일화** — Task 1(DTW path median)과 Task 2(verdict same-frame)가 충돌. **결정: 표시 문장("무릎 145° vs 178°")은 frame-specific** → `student_deg`/`reference_deg` 는 `FramePairMeasurementContext.user_frame_idx/ref_frame_idx` 에서만 계산(정량화 표시용). DTW median 은 **기존 scoring 경로**(per_joint_deviation)로 분리 유지 — 정량화 표시에 median 을 쓰려면 `windowMedianAngleDeltas`(+sourceFrameIndices/windowPolicy)로 별도 명명, still 프레임의 정확 각도로 표기 금지. 테스트: 선택 프레임 각도 ≠ DTW median 인 케이스에서 표시값이 frame-specific 임을 명확히.
- **(MED-1) resource_limited lockstep 완전 고정** — must_haves artifact + acceptance 가 `low_alignment_confidence` **와 `resource_limited`(또는 최종 `sampling_incomplete`) 둘 다** 를 3-way(models.py/analysis.ts/contract.md)에서 요구. TS discriminated-union: `resource_limited` 는 severity/capApplied/primaryFault/angleDeltas/bodyRelativeNotches/rootCauseHypotheses **없음**, telemetry 만 허용.
- **(MED-2) Task 5 verify 가 coach_writer 테스트 실행** — `pytest tests/test_pipeline_vision_gate.py tests/test_coach_writer.py`. 실제 Cerebras/Gemini 프롬프트 payload(또는 정규화 writer 입력)를 inspect — 최종 assembled tip 만 보지 말 것(monkeypatch writer 로 false-pass 방지).

### D-11: ITERATION3 status-의미론 (2026-06-22, [[23-DIRECT-REVIEW-ITERATION3.md]])
- **(HIGH-1) cap 적용성을 pre-coach 계약에 포함** — coach injection 은 collect 시점에 일어나지만 `applied` 여부는 cap 적용(`apply_downward_cap(overall,severity) < overallScore`) 후에 확정된다. 즉 minor/overall=88 처럼 **valid 한 verdict 이 not_applicable** 이 될 수 있어, 비적용 verdict 의 root-cause 가 coach 에 새어든다(비적용 경로 무주입 규칙 위반). **fix:** `_collect_vision_fault_context` 가 prospective `overallScore`/`score_result` 를 받아 **production 동일 cap 함수로 `cap_would_apply = apply_downward_cap(overallScore, severity) < overallScore` 계산**해 VisionFaultContext 에 노출; coach 에는 `cap_would_apply=true` + status eligible 일 때만 root-cause 주입. (cap 이 점수 안 내려도 원인 코칭을 원하면 `applied` 재사용 말고 별도 status `visionFaultCandidate` 로.) 테스트: minor/88→not_applicable+coach 무주입, moderate/92→applied+coach 주입, none/score-free→무주입.
- **(HIGH-2) eval FP 와 abstention 분리** — clean case 전부 `low_alignment_confidence` 로 abstain 하면 `false_positive_count=0` 이 specificity 증명 없이 통과(분모 오류). **fix:** JSON 에 `clean_applied_fault_count`/`clean_true_negative_count`/`clean_abstention_count`/`clean_evaluable_count` + case 별 `abstention_allowed`. case class 별 게이트: elite/imperfect clean/occluded/spinning 은 manifest 가 alignment-unverifiable 로 명시 안 한 한 evaluable non-fault(none/not_applicable) 요구; tempo-shifted 는 low_alignment_confidence 허용하되 **abstention 으로 카운트(true negative 아님)**. FP=0 유지 + **coverage 임계**(전부 abstain 이면 fail).
- **(MED-1) applied-but-quant-unavailable 명시 허용** — vision veto 는 applied 인데 same-frame 정량화 입력만 결측인 케이스. `quantificationStatus` 를 **applied audit 에 필수**(available|unavailable). 테스트: cap 적용되나 FramePairMeasurementContext keypoint 결측 → `status="applied"`, capApplied+root-cause **유지**, `quantificationStatus="unavailable"`, angleDeltas/notches **부재**, warning/telemetry 기록. not_applicable 로 강등 금지, crash 금지.
- **(MED-2) VisionFaultContext typed contract** — pipeline collect→coach inject→writer payload→audit→eval trace 를 가로지르는 실제 내부 API. ad-hoc dict 면 키 drift(root_cause_hypothesis vs rootCauseHypotheses 등). **fix:** 단일 dataclass/TypedDict owner(`vision_veto.py` 또는 인접 shared model): status/verdict/supported_differences/root_cause_hypotheses/selected_frame_pairs/alignment/telemetry/`cap_would_apply`/quantification_status + serializer `to_coach_context()`/`to_audit_dict()`/`to_trace_dict()`. 테스트는 이 타입을 생성, writer 테스트는 `to_coach_context()` 소비(payload↔audit fork 방지).
- **(LOW-1) UI defer 문구 정정** — 기존 앱이 이미 `detail2.causes` 를 `CoachingTipDetailModal`(105-125)에서 렌더한다. Task 5 가 root-cause 를 `coachingTips[].detail2.causes` 에 주입하면 **UI 파일 변경 없이 기존 모달에 자동 표시**됨. S2 문구를 "신규 정량화 UI/result.tsx 각도·칸 렌더/시각 오버레이는 defer; **기존 coach cause 렌더는 새로 생성된 detail2.causes 를 자동 surface 할 수 있음**"으로 — QA 가 자동표시를 scope creep/누락으로 오인 방지. (D-07 S2 의 "앱 표시 defer" 는 *신규 정량화 UI* 한정으로 정정.)

### D-12: ITERATION4 계약 경계 (2026-06-22, [[23-DIRECT-REVIEW-ITERATION4.md]] — typed context 후속)
- **(HIGH-1) context/audit/quant 객체 분리** — `VisionFaultContext.to_audit_dict()` 가 과부하: final `visionVeto.status` 는 `_apply_vision_veto` 가 build 결과 대비 cap 재계산 후 확정(app.py:1727-1762)이고, geometry payload(angleDeltas/notches)는 23-02 Task1/2/4 가 *이후* 산출 → pre-coach context 가 완전한 audit 을 소유하면 drift(applied-looking audit가 final 과 어긋남) 또는 raw dict side-load. **fix:** ① `VisionFaultContext` = **pre-apply/pre-coach 만**(collection status/verdict/supported_differences/selected_frame_pairs/alignment/telemetry/cap_would_apply). ② `VisionQuantificationResult` = post-geometry(quantificationStatus/angleDeltas/bodyRelativeNotches/windowMedianAngleDeltas/warnings) 별도. ③ audit 직렬화는 `ctx.to_audit_dict(final_status=, cap_applied=, quantification=)` 로 **`_apply_vision_veto` 안에서 final cap 계산 후에만** 호출. 테스트: final_status/quantification 없이 to_audit_dict() 호출 시 fail-fast 또는 final 필드 생략; applied-but-quant-unavailable 은 serializer 가 아니라 `_apply_vision_veto` 경로로 검증.
- **(HIGH-2) resource_limited 는 abstention 아니라 완료실패** — eval 이 `low_alignment_confidence` 와 `resource_limited` 를 같은 abstention 으로 묶으면, under-budget/timeout 구현이 clean FP 회피 + recall 의무 부분 회피 가능. **fix:** eval outcome class 분리 — `alignment_abstention_count`(low_alignment_confidence 만) / `resource_incomplete_count`(resource_limited / samplingComplete=false) / `clean_abstention_count`(alignment 만) / `completion_pass`(budget-stress 아닌 모든 케이스가 samplingComplete=true & not resource_limited). main Pod gate 에서 `resource_limited` 는 manifest 가 의도적 budget-stress 로 표시 안 한 한 completion/resource coverage **fail**, true negative 아님, tempo-shift alignment abstention 과 그룹화 금지.
- **(MED-1) collect 시그니처를 pre-build primitive 로** — `_collect_vision_fault_context(score_result, ...)` 가 `score_result["overallScore"]` 읽는데 result dict 는 `assemble.build_result`(coach 이후) 후에야 존재 → 구현자가 build_result 를 앞당기거나 collect 를 build 후 호출해 임계 순서(collect<coach<build_result<apply)를 깰 위험. numeric `overall` 은 app.py:2441-2442 에서 더 일찍 가용. **fix:** 시그니처를 `_collect_vision_fault_context(*, overall_score:int, dimension_scores:dict, mode:str, local_video_path, ...)` 로(존재하는 것만 전달). ordering 테스트/trace assertion: overall 계산→collect→_build_coach_context→coach writers→build_result→_apply_vision_veto, 그리고 **coach 전에 build_result 호출 0**.
- **(MED-2) eval arm 간 캐시 격리** — production seam / direct-adapter / whole-video baseline 이 캐시 namespace 공유하거나 서로 warm 시키면 cold/warm 결과 오도. **fix:** `arm` ∈ {production_still, direct_adapter_still, whole_video_baseline}; arm·cold 반복마다 `cache_namespace`/`run_id`; cold assertion=각 arm 첫 cold run `cacheHit=false`; warm assertion=직전 cold 와 같은 키 + `cacheHit=true`; cross-arm=whole-video baseline 키 ≠ still production 키, direct-adapter 는 manifest 가 의도 표시 안 한 한 production gate run 을 pre-warm 금지.

### D-13: ITERATION5 integration 계약 (2026-06-23, [[23-DIRECT-REVIEW-ITERATION5.md]])
- **(HIGH-1) `_build_vision_quantification_result` 명시 production seam** — `VisionQuantificationResult` 타입·serializer 는 정리됐으나 *언제/어디서 생성해 `_apply_vision_veto` 에 넘기는지* 암묵적 → None/raw dict/stale/post-audit 생성 위험. **fix:** named 함수 `_build_vision_quantification_result(fault_context, selected_frame_pair, current_measurements, reference_measurements, body_profile, pole_geometry)` 추가, 파이프라인 순서 박제: `overall_score → _collect_vision_fault_context → coach context/writers → _build_result → _build_vision_quantification_result → _apply_vision_veto(..., quantification=)`. 입력 결측 시 `None` 금지 — `VisionQuantificationResult(quantificationStatus="unavailable", warnings=[...])` 반환. 테스트: cap-applied 경로가 apply 전에 정확히 1회 호출 / apply 가 dict·None 아닌 객체 수신 / applied audit 은 항상 quantificationStatus 보유 / non-applied 는 measurement 필드 0 / 결측 입력 → unavailable 이 full `_apply_vision_veto` 경로로.
- **(HIGH-2, belle=Option A) main eval: applied ⟹ samplingComplete=true** — quorum 후 budget 소진이지만 일부 planned call 미샘플 상태를 normal `applied` 로 허용하면, 같은 클립이 wall-clock/cache/latency 에 따라 applied 변동(비결정). **fix(main path):** planned call 전부 완료 전 budget 소진 = **`resource_limited`**(normal applied 아님). normal `applied` 는 `samplingComplete=true` 필수. budget-stress fixture 만 graceful degradation 검증(별도). 테스트: fake-clock 으로 quorum 후·전체 call 전 budget 소진 → main eval 에서 clean success 카운트 금지 / cold·warm 이 completion-pass 분류를 바꾸지 못함. (23-01 의 "quorum 후 budget 소진 → applied" 를 main path 에선 resource_limited 로 정정.)
- **(MED-1) root_cause 는 support-gated difference 에서만** — raw Gemini difference 에서 root_cause 를 복사하면 support 게이트가 drop 한 환각 결함의 원인이 coach/audit 에 남음(23이 막으려던 one-frame 설명 재발). **fix:** `supported = _filter_supported_differences(raw,...)` → `root_cause_hypotheses = _derive_root_causes_from_supported_differences(supported)`. 각 root cause 는 provenance 보존: `RootCauseHypothesis(text, fault_key, source_difference_ids, support_count)`. 테스트: 미support single-frame root cause 가 coach+audit 에 부재 / support 된 alias·root 쌍은 source_difference_ids 와 함께 생존 / 모든 difference 가 drop 되면 root cause 0.
- **(MED-2) `VisionFaultContext.status` → `collection_status` 개명 + pre-final enum** — generic status 가 final audit status(applied/not_applicable/...)와 다시 섞일 위험. **fix:** `collection_status: VisionFaultCollectionStatus` 로 개명, **pre-final enum 전용**(candidate_verdict/no_fault/low_alignment_confidence/resource_limited/disabled/mode3_held/missing_reference/missing_current_video/skipped_error — `applied` 같은 final 값 금지). `eligible_for_coach = collection_status=="candidate_verdict" and cap_would_apply is True`. 테스트: VisionFaultContext 를 final `"applied"` 로 생성 불가 / final status 는 `to_audit_dict(final_status=...)` 만 방출 / coach gate 는 collection_status 읽음.

### D-14: Phase 20-04 흡수 — **regression subset 한정** (belle 2026-06-23, ITERATION6 정정)
- **23-03 가 흡수하는 건 still-frame SEVERITY_CAP *regression subset* 만**(SCORE-08 cap + TRUST-06 결정론). **SCORE-09(일반화/sensitivity — 미보유+above-cutoff 양방검증)는 흡수하지 않고 별도 pending 유지**(belle 2026-06-23 ITERATION6 HIGH-1). 23 재팽창 방지 + SCORE-09 를 조용히 잃지 않기.
- **23-03 가 still-frame veto 에서 소유·검증하는 게이트:** 정은지 정타 95~100 / **kip-up fault = moderate, 점수 ≤75**(belle ITERATION6 HIGH-3 — 무릎굽음/발끝/스트래들은 *제대로 인식된 kip-up 의 moderate 실행결함*이지 틀린 동작 아님. 기존 20-04 evidence 75/moderate 와 일치. **≤50 억지 격상=curve-fit 금지**. "잘못된 동작 ≤50" 스펙은 진짜 실패/틀린 동작용) / 결정론(cold+warm) / EVAL18 변별 4쌍(power-spin/peter-pan/elbow-twist/pdshape) 퇴행 0.
- ROADMAP/REQUIREMENTS/STATE 정정: "20-04 **regression subset** superseded-by-23-03; SCORE-09 sensitivity/generalization 는 별도 pending(Phase 20/후속)". 23-03 frontmatter requirements = VETO-06 + SCORE-08 + TRUST-06(SCORE-09 미포함 — pending 유지).

### D-15: ITERATION6 — 흡수 게이트의 terminal 강제 (2026-06-23, [[23-DIRECT-REVIEW-ITERATION6.md]])
- **(HIGH-2) non-zero assert 스크립트** — "machine-checkable JSON" 만으론 약함(필드 누락/`"true"` 문자열/stale/row 실패 은닉). **fix:** `backend/research/spikes/assert_stillframe_veto_gate.py` 신설(JSON+manifest 받아 **실패 시 non-zero exit**, compact gate report). 최소검사: 필수 top/row 필드 정확 타입 / 모든 manifest row 가 결과에 정확히 1회 / unmanifested row 가 pass metric 에 안 섞임 / coverage_pass·completion_pass·determinism·arm 캐시격리·D-14 게이트를 **precomputed 필드 신뢰 말고 row 에서 재계산** / kipup·elite·eval18 게이트를 실제 final score 에서 도출 / resource_limited·samplingComplete=false 가 non-budget-stress row 를 fail / 미허용 status fail. 23-03 Task 2 = Pod 가 JSON 수락 전 이 스크립트 실행.
- **(MED-2) frozen manifest + lock** — `eval_stillframe_veto_manifest.yaml` + `eval_stillframe_veto_manifest.lock.json`(manifest sha256/timestamp/git commit/dirty-flag/row ids+expected policy). assert 가 fail: manifest 해시≠lock / dirty worktree lock / 결과 row≠manifest row / expected-policy 필드 누락·변경. **Pod 측정 전 라벨(abstention_allowed/budget_stress/alignment_unverifiable/case class/expected recall/D-14 row policy) freeze** — 결과 본 뒤 hard case 를 relabel 해 통과시키는 것 차단.
- **(MED-1) 소유권 문서 원자적 정합** — ROADMAP("regression subset superseded; SCORE-09 pending") / REQUIREMENTS(SCORE-09 = Phase 20/후속 pending 유지, still-frame regression 은 23-03) / STATE(20-04 regression superseded-by-23-03, SCORE-09 pending) / 23-03 frontmatter requirements(VETO-06+SCORE-08+TRUST-06). executor 가 SCORE-09 미처리로 23 닫거나 20-04 를 SCORE-09 채로 superseded 처리하는 것 방지.
- kip-up manifest row 예: `{row_id: eval18-kip-up-fault, expected_bucket: must_drop, allowed_veto_statuses: [applied], expected_severity: moderate, max_score: 75}` (D-14 moderate 결정). row-level 실패 메시지가 severity 오분류 vs cap 적용 실패를 구분.

### D-16: ITERATION7 — terminal gate 운영화 (2026-06-23, [[23-DIRECT-REVIEW-ITERATION7.md]])
- **(HIGH-1) freeze 를 Pod 측정 전 별도 단계로 분리** — 현 워크플로는 manifest+lock 동시 생성이라 "결과 본 뒤 relabel→lock→commit" 가 여전히 가능(D-15 가 막으려던 것). lock 의 hash 일치는 "현 manifest=lock" 만 증명하지 결과 전 freeze 를 증명 못 함. **fix:** freeze 를 독립 단계로 — `freeze_stillframe_veto_manifest.py`(또는 assert 의 `freeze-manifest` 서브커맨드). 워크플로: ① manifest.json 작성 → ② **commit** → ③ clean worktree 에서 freeze 실행(uncommitted/dirty 면 거부) → ④ lock.json **commit** → ⑤ Pod 가 그 commit pull → ⑥ Pod eval 은 result JSON 만 생성 → ⑦ assert 가 `lock_git_commit` 이 현 HEAD 의 ancestor 인지 + dirty/dev 아닌지 검증. result JSON 에 `manifest_lock_git_commit` 기록. 수용: freeze 가 uncommitted/dirty 면 거부 / assert 가 lock_git_commit ∉ ancestor(HEAD) 면 fail / Task 3 가 "Pod run 은 manifest+lock 포함 commit 에서 시작" 명시.
- **(HIGH-2) manifest = JSON (stdlib only)** — assert 가 yaml 파싱하는데 **PyYAML 은 stdlib 아님 + RunPod requirements 에 없음**(`runpod_inference/requirements.txt`) → Pod-terminal assert 가 import 단계에서 죽을 수 있음. **fix(belle=Option 1):** manifest 를 **`eval_stillframe_veto_manifest.json`** + `.lock.json` 으로(YAML 폐기), assert 는 `json`/`hashlib`/`subprocess`(git) **stdlib 만**. RunPod 의존 추가 0.
- **(MED-1) expected_recall = canonical FaultKey, 표시라벨 아님** — manifest 가 `[왼팔,오른팔,고개·목]` 한글 표시라벨 쓰면 canonical FaultKey 계약(D-09)과 drift(표시카피 rename 이 게이트 깨거나, 두 라벨이 한 fault 로 recall 부풀림). **fix:** `expected_recall_keys: [{part_scope:upper_body, side:left, keypoint_set:arm, fault_kind:pole_gap_or_bent}, {…side:right…}, {…side:unknown, keypoint_set:head_neck, fault_kind:extension_or_alignment}]`. `display_label_ko` 는 optional 문서용만. assert 는 `supported_differences[].fault_key`(또는 `to_trace_dict()` 의 canonical key)와 비교, 렌더 한글 텍스트 아님.
- **(MED-2) assert 의 behavioral test 필수** — grep/AST 만으론 terminal gate 로 약함(precomputed bool 신뢰/`"true"` 문자열/missing row/hash mismatch/kip-up major≤50 오통과 가능). **fix:** `backend/tests/test_assert_stillframe_veto_gate.py`(또는 `--self-test`) 필수 fixture: valid 최소→exit0 / manifest hash mismatch→non-zero / missing row→non-zero / extra unmanifested row→non-zero / bool 자리 `"true"` 문자열→non-zero / non-budget-stress row 의 resource_limited→non-zero / kip-up severity=major score=50→non-zero(severity 오분류) / kip-up severity=moderate score=80→non-zero(cap 적용 실패) / EVAL18 pair fault≥success→regression count↑ non-zero. Task 2 verify = `pytest tests/test_assert_stillframe_veto_gate.py`.

### Claude's Discretion
- key-frame 선별 알고리즘 세부(worst-pose 선정 기준, ±윈도우 크기, top-K), 부위 분할 경계(skeleton.JOINT_TO_PART 확장: 머리/그립 추가), N-sample 수, 캐시 키에 input_granularity 반영 방식, 비용 상한(호출수 bound) — 구현 디테일은 planner/executor 재량(게이트 D-06 준수 하에).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Vision veto 어댑터 (교체 대상 핵심)
- `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py` — veto 어댑터. `assess_fault_severity()`(COMPARISON/SINGLE), `_upload_video()`(영상 통째 — **이 입력을 still로 swap**), `_call_gemini_comparison()`/`_COMPARISON_PROMPT`(v7.0 ①→⑧), `_aggregate_comparison_verdict()`(N-sample rank-median), `build_schema()`(no-score), `VisionVetoCache`(키에 `input_granularity` 포함 — frame-input swap 대비 이미 설계됨), File API `client.files.delete` 정리.
- `backend/shared/python/sunity_shared/analysis/vision_veto.py` — `apply_downward_cap()`(하향 전용 cap), `fault_joints_from_differences()`(부위→키포인트), `worst_pose_timestamp()`(worst-pose 시점).
- `backend/functions/pipeline/app.py` — `_apply_vision_veto()` (≈1662-1767, swap 지점), `_process()`, B1 DTW wiring(≈2411 `_deviation_against`/`reference_dtw_match`), reference/prev profile fetch(≈2360 Mode1, ≈2494 Mode3).

### DTW 정렬 + 프레임 매칭 (still 선별 기반)
- `backend/shared/python/sunity_shared/analysis/motiondtw.py` — `find_action_segment()`(시작점), `dtw()`(워핑), `MotionMatch.distance`(**정렬 신뢰도 신호 — D-03 게이팅**), `per_joint_deviation()`(median).
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` — `_matched_ref_frame()`(학생↔정은지 same-pose 프레임 쌍 — **D-01 나란히 still 재사용**), `build_fault_zoom_comparisons()`(확대비교 carousel — **D-02 시각 칸/층 오버레이 후속 위치**).

### 정량화 기반 (각도/거리/사이즈)
- `backend/shared/python/sunity_shared/analysis/features.py` — `compute_joint_angles()`(3D 관절각, 스케일 무관 → D-02 각도 직접).
- `backend/shared/python/sunity_shared/analysis/dimensions.py` — `JOINT_ANGLES`(8 관절), `line_score`.
- `backend/shared/python/sunity_shared/analysis/skeleton.py` — `JOINT_TO_PART`(상체/코어/하체 — D-05 부위 분할 시드), `JOINT_KEYS`.
- `backend/shared/python/sunity_shared/analysis/body_normalization.py` + `body_normalization_measurer.py` — 상대 스케일 프로파일(arm/leg/torso/height ratio — D-02 몸-상대 거리 기반).

### 진입점 / 로드맵
- `backend/runpod_inference/server.py` — `POST /analyze` (단일 분석 진입, X-RunPod-Token).
- `.planning/ROADMAP.md` — Phase 23 (Goal/Success Criteria/게이트).

### Pod 산출물 (스파이크 근거 — eval 시드)
- `/workspace/spike_kipup_granularity_result.json` (pod) — 3-way(A/B1/B2) 결과.
- `/workspace/spike_perframe_upper_result.json` (pod) — 단일프레임 풀 recall 실증.
- `backend/research/spikes/reports/spike_vision_grounding_kip-up.json` — whole-video baseline(상체 0).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **gemini_vision_scorer 어댑터 경계**: 입력만 whole-video→still로 swap하면 됨. N-sample 집계·캐시·no-score 스키마·File 정리는 그대로 재사용. 캐시 키에 `input_granularity`가 이미 있어 frame-input verdict가 whole-video verdict와 충돌 안 함(20-02 설계).
- **fault_zoom._matched_ref_frame**: 학생↔정은지 same-pose 프레임 쌍이 이미 계산됨 → D-01 나란히 still 입력에 그대로 사용.
- **fault_zoom.build_fault_zoom_comparisons**: 확대비교 carousel 산출 → D-02 칸/층 시각 오버레이가 얹힐 자리.
- **MotionMatch.distance**: 정렬 신뢰도 신호가 이미 산출됨 → D-03 게이팅 임계만 추가.
- **compute_joint_angles + JOINT_ANGLES**: 스케일 무관 각도가 이미 계산·저장(keypointReport) → D-02 각도 직접 출력에 사용.
- **body_normalization 프로파일**: 학생·정은지 둘 다 측정·저장·wiring(force_signals 포함) → D-02 몸-상대 거리 정규화 기반.

### Established Patterns
- 어댑터 경계 + lazy-import(google.genai), VisionVerdict 객체(no-score 영구), temp 0 + 캐시 결정론, downward-only cap(비전이 점수 못 올림).
- Firestore nested-array 금지 → (T,J)는 flat 저장 + 읽는 쪽 reshape.
- 분석 코어는 numpy-only 순수 함수, 무거운 deps(genai/ffmpeg)는 어댑터 뒤.

### Integration Points
- `_apply_vision_veto` (pipeline/app.py) = 입력 swap의 단일 지점.
- `VisionVerdict` 스키마 = 정량화 필드 추가 시 객관성(score 부재) 유지.
- 앱 `result.tsx` + fault-zoom carousel = 정량화 표시/시각 오버레이 후속.

</code_context>

<specifics>
## Specific Ideas

- 칸/층 표현 예시(belle): "정은지 선수는 3칸 올라갔는데 너는 2칸, 2칸 ⅔ 올라갔다" + 화살표로 방향.
- 기준선은 동작별: kip-up=바닥, 공중 동작=폴(수직, 항상 프레임 내)/엉덩이 라인.
- 고개 젖힘 사례: belle 추정 "결함에 가까움" + Gemini 단일프레임 독립 판정("목 뒤로 젖혀져 정렬 무너짐") 수렴 → 결함으로 다루되 하드 라벨 금지.
- 검증: 시작점/템포가 정은지와 다른 일반 사용자 케이스(Mode 1 정상 상황)로 프레임선별이 거짓결함을 만들지 않는지 별도 검증 task.

</specifics>

<deferred>
## Deferred Ideas

- 화살표 + 칸/층 **시각 오버레이** 풀 구현 — v1.1(확대비교 이미지 위, v1은 텍스트+각도 먼저).
- **앱 표시(result.tsx 각도/칸 렌더 + coach-report 원인섹션 렌더)** — 후속 UI phase(D-07; 본 phase 는 백엔드 계산·저장·생성까지).
- **Mode 3 still-frame 정량화/정렬** — Backlog B-15a 합류(D-07; 본 phase Mode 1 집중).
- 자체 비전 모델 파인튜닝(오픈 모델) — Phase 22.
- reference 셀프 등록 자동화 — Phase 21.
- AQA-style part-aware contrastive 점수 모델 — 라벨 데이터셋 확보 후 중장기(리서치 중장기 트랙).

</deferred>

---

*Phase: 23-mode-1-recall-still-frame-veto-dtw-key-frame*
*Context gathered: 2026-06-22*
