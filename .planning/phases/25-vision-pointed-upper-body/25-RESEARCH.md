# Phase 25: 상체 감점 커버리지 — vision-pointed window 측정 - Research

**Researched:** 2026-07-04
**Domain:** 기존 파이프라인 내부 배선 (Gemini vision 짚기 → worst-window 기하 측정 → 규칙 감점). 외부 라이브러리/신규 패키지 0.
**Confidence:** HIGH (전 발견이 리포 코드 + 커밋 이력 + sweep artifact 직접 검증)

## Summary

TestFlight 실기기에서 확정된 갭 — kip-up fault 의 어깨 편차 40.4°/31.0°(tol 20° 초과)가 **측정·표시는 되는데 감점 0** — 의 원인을 코드/artifact 로 확정했다. 원인은 **두 겹의 독립 차단**이다: (1) Gemini fan-out 이 어깨를 primaryFault 텍스트로는 언급하지만 supported_differences(faultKey)로 살아남지 못함(support 게이트 K=2 미달 — FaultKey 의 side/fault_kind 정규화가 어깨 언급을 fragment), (2) 설령 어깨 faultKey 가 살아남아도 `criteria_for_fault` 가 shoulder → `CoverageGap`(감점 0, 의도된 deferred) 으로 라우팅. 따라서 프롬프트만 고쳐도, 라우터만 고쳐도 감점은 발생하지 않는다 — 둘 다 풀어야 한다.

다행히 감점 측 인프라는 이미 완비: `angle_vs_reference__{joint}` criterion 8개(어깨 포함, tol 20°+slope 1.2, `_MEASURABLE_SEED_IDS` 등재)가 존재하고, quick 260702-o0c 의 revert 된 커밋 f513587 에 worst-window seed 방출 helper(`_emit_reference_relative` + wm 파싱)가 그대로 재사용 가능하다. 유일한 설계 변경 = f513587 의 "경로 단위 either/or"(전 관절 window)를 "**관절 단위 선택**"(vision 이 짚은 관절만 window, 나머지는 full-path median 유지)으로 바꾸는 것.

**Primary recommendation:** 라우터/엔진은 건드리지 말고 **seed-stage(Option A)** 로 배선하라 — `_build_deduction_measured_deviations` 에 `vision_pointed_joints` kwarg 추가, 짚인 관절만 `windowMedianAngleDeltas` 값으로 `md[angle_vs_reference__{jk}]` 방출. 짚기 커버리지는 support 집계 fragment 수정 + upper_body scope 프롬프트 보강으로 확보하되, **집계/프롬프트 어느 쪽을 바꿔도 캐시 버전 bump 필수**(rich 캐시는 집계 후 결과를 저장).

## User Constraints (from ROADMAP — Phase 25 CONTEXT.md 부재, roadmap locked)

### Locked Decisions (ROADMAP Phase 25 절)
- 아키텍처 = 역할 분리: **짚기(detector) = Gemini vision faultKey / 측정(measurement) = 짚인 관절만 worst-window median 기하 측정 / 감점(scoring) = 기존 명시규칙(tol 20°+slope)**
- Gemini-silent 관절 = 기존 보수적 full-path median seed 유지 (위양성 방어)
- 전제 작업 = vision 결함 짚기 커버리지를 상체까지 확대 (per-move 프롬프트/기준 — 프롬프트 특정성이 레버, [[flash-beats-pro-video-split-judgment]])
- belle 도메인 판정: kip-up fault 는 88(상체 누락)도 50(과감점)도 아닌 그 사이 — **특정 점수 맞추기(짜맞추기) 금지**, 측정 구조를 고쳐 점수가 자리를 찾게 한다

### 게이트 (Phase 24 승계 + 260702-o0c 교훈)
- sweep 6페어: fault 변별 유지·개선 AND **success 6/6 == 100** (위양성 0)
- kip-up fault: 88 미만 하락하되 상체 감점이 **vision-확인 관절에서만** 발생 (특정 점수 assert 금지 — "vision 짚은 관절만 감점" 구조 assert 로)
- 밴드 금지 / **신규 튜닝 상수 금지**(tol·slope·window 정책 기존 재사용) / 결정론 / 사람 점수 라벨 금지

### 동반 스코프
- 확대 카드 정밀도: reference 쪽 저신뢰 전신 폴백이 카드마다 동일 전신 반복 → 부위 bbox 완화 crop + 카드별 차별화 + 앵커 정밀화. vision 이 프레임/부위 확정 시 그 프레임·부위 crop.
- F(260704-fz4) advisory 티어(주황 "참고")가 이미 UI 선행 — 이 phase 완성 시 vision-확인분이 참고→확정(빨강) 승격 구조.

### Deferred / Out of scope
- Mode3 vision veto (mode3_held 유지), 객관 180° split(expects_split flag), head_neck/grip/torso substrate (coverage gap 잔류 가능)

## 핵심 발견 (focus 별)

### 1. 상체 faultKey 미산출의 정확한 원인 — 두 겹 차단 [VERIFIED: 코드 + sweep artifact]

**Artifact 증거** (`backend/evals/phase24/baseline/phase24_sweep_report.json`, kip-up fault):
- `primaryFault`: **"다리 스플릿 각도 부족 및 상체(어깨/목) 정렬 흐트러짐"** — Gemini 는 상체 결함을 *본다*.
- `rootCauseHypotheses`: **양다리(스플릿) 1건만** (supportCount 4, faultKey keypoint_set=leg) → split_angle −12 (source=vision) → 88.
- `windowMedianAngleDeltas`: left_shoulder Δ40.37° / right_shoulder Δ31.00° (worst_pose_center ±2 median) — 측정됨, 감점 0. TestFlight 관측과 정확히 일치.

**차단 1 — 짚기(support 게이트).** production collect = `assess_fault_context_video`(full-video, `whole_fanout` 캐시, at_seconds=None) → `_run_part_frame_fanout` 이 **3 scope(upper_body/lower_body/line) × 1 call** 실행 → `_filter_supported_differences(min_support_k=VETO_SUPPORT_K=2)`. FaultKey = (part_scope[hint 균일], **side**, keypoint_set, **fault_kind**). 어깨 언급은:
- side fragment: "왼쪽 어깨"(side=left) vs "어깨"(side=unknown) → 다른 키
- fault_kind fragment: "벌어/굽/떨어" 마커 유무로 pole_gap_or_bent vs extension_or_alignment → 다른 키
→ 3 call 중 각 키 support 1 로 K=2 미달 drop. (또는 애초에 differences[] entry 로 안 나오고 primary_fault 서사에만 등장 — per-call raw 가 미보존이라 artifact 로는 구분 불가. 두 경우 모두 아래 처방이 커버.) FaultKey **어휘 자체는 이미 shoulder 커버**(FAULT_KEYPOINT_SETS 에 "shoulder", `_KEYPOINT_SET_BY_KEYWORD` 에 어깨/견갑) — vocab 은 병목이 아니다.

**차단 2 — 감점 라우터.** `ipsf_criteria.criteria_for_fault` 는 어깨 body_part 를 **`CoverageGap("shoulder_alignment_substrate_deferred")`** 로 라우팅(감점 0, `COVERAGE_GAP_KEYPOINT_SETS`). 즉 짚기가 성공해도 현행 라우터 경로로는 감점이 안 난다. → Phase 25 는 라우터를 고치는 대신 **seed 경로**(criteria_from_measured_deviations → `angle_vs_reference__{jk}`)로 감점을 흐르게 하면 라우터 무접촉으로 해결된다(§2).

**안정적 상체 faultKey 산출을 위한 변경 (레버 2개, 병행 권장):**
- (a) **집계 수정**: support 그룹핑 시 fault_kind(및 side=unknown ↔ left/right)를 fold — 예: keypoint_set(+해소 가능한 side)만으로 그룹, 대표 difference 는 최고 severity/dev 유지. 결정적 pure 함수 수정, 프롬프트 무접촉. ⚠ rich 캐시는 **집계 후** supported_differences 를 저장하므로 집계만 바꿔도 캐시 버전 marker bump 필수(§5-2).
- (b) **upper_body scope 프롬프트 보강**: 이미 존재하는 per-scope 집중 힌트(`_call_gemini_comparison` part_scope, `_PART_SCOPE_LABEL`)에 "관찰된 상체 편차는 반드시 differences[] 항목으로(좌/우 명시) 구조화 — 서사(primary_fault)에만 남기지 말 것" 지시 추가. generic 유지(동작명/기대답 0 — D-06 curve-fit 밴과 양립). PROMPT_VERSION bump 필수.
- roadmap 의 "per-move 프롬프트/기준" 은 curve-fit 밴과 긴장 — 프롬프트에 동작명·기대답 하드코딩은 금지 유지, per-move 특정성은 **recognizer/criteria yaml 이 공급하는 측정대상 힌트** 형태로 discuss/plan 에서 결정할 것. [ASSUMED — belle 확인 필요]

### 2. 짚기→측정 배선 — 최소 변경 지점 [VERIFIED: git show f513587 + app.py 현행]

**재사용 가능 (revert 된 f513587 diff 그대로):**
- `_emit_reference_relative(jk, v)` helper — JOINT_KEYS 검증 / NaN·0 skip / `profile.expects_extension` cross-exclusion(§3-2) / md 방출 단일화
- `quantification.windowMedianAngleDeltas["deltas"]` 파싱 — `abs(float(entry["delta_deg"]))` (SIGNED→magnitude)
- seed source 관찰 로그 패턴 (`window_median` vs `dtw_median_fallback`)

**달라져야 할 것 (핵심 차이):** f513587 은 **경로 단위 either/or** — wm_deltas 가 있으면 *전 관절* window, fallback 은 실행 안 함. 이것이 FP 원인(silent 관절까지 window 편향 표집). Phase 25 = **관절 단위 merge**:
```
for jk in JOINT_KEYS:
    if jk in vision_pointed_joints and wm[jk] 존재:  md ← abs(wm delta)   # window (짚인 관절만)
    else:                                             md ← per_joint_deviation[jk]  # full-path median (기존)
```

**배선 지점 (순서 보장 확인됨):** `app.py:3499~3529` — `vision_fault_context`(collect 산출물)와 `quantification` 이 **`_build_deduction_measured_deviations` 호출(3518) 시점에 이미 가용**. 최소 변경 = kwarg 1개 추가:
- pointed joints 도출: `ctx.supported_differences` 의 faultKey/body_part → 관절명. ⚠ `vision_veto.fault_joints_from_differences` 를 그대로 쓰면 **과확장 함정**: 라인/상체/전신 → trunk(양어깨+양엉덩이), 스플릿 → 양다리(무릎+엉덩이) 로 broad 확장된다. line fault 하나가 어깨 4관절을 "짚은" 것으로 만들면 vision 게이트가 무력화됨. → **keypoint_set ∈ {shoulder, arm} (또는 명시적 관절 body_part)** 인 supported_differences 에서만, side 해소해서 도출하는 **좁은 매퍼**를 새로 쓸 것(순수 함수, vision_veto 에 배치).
- split→hip double-count 는 이미 방어됨: 엔진 HIGH-5 확장이 split_angle 활성 시 `angle_vs_reference__{left,right}_hip` discard (deduction_engine.py claimed_joints).

**Option B(엔진-stage, split 패턴 미러: tally 내 router→md 주입)는 비권장** — 라우터의 shoulder→CoverageGap 을 바꿔야 하고 엔진이 wm lookup 을 새로 배워야 함. Option A 는 엔진/라우터/criterion 전부 무접촉, `angle_vs_reference__{jk}` criterion(이미 tol 20+slope 1.2, `_MEASURABLE_SEED_IDS` 등재)이 그대로 발화. "신규 튜닝 상수 금지" 게이트 자동 충족.

**provenance:** 현행 record.source 는 `vision`(Gemini 가 잰 수치) vs `geometry`. window 측정은 기하 측정이므로 geometry 가 정직하나, belle 투명성 원칙상 "vision-짚음 관절은 window 집계" 출처를 보고서/audit 에 노출할지 plan 에서 결정 (deviationSource 나 별도 audit 필드 — Firestore nested-array 주의). [ASSUMED — 표기 방식은 discuss 대상]

### 3. 위양성 방어 [VERIFIED 일부 + 관측 공백 확인]

- **관측 공백 (중요):** `not_applicable` audit(`na_audit`) 는 collectionStatus/verdict/supported 를 버린다 → 기존 sweep artifact 에서 **"clean 영상에서 Gemini 가 상체를 짚는 빈도" 를 측정할 수 없다**. success 6/6 멤버 전부 visionVeto = {status: not_applicable, alignment} 뿐. Phase 25 eval 은 success 멤버에도 collect status + supported_differences 를 score-free 로 캡처하도록 harness 를 보강해야 짚기-FP 율이 처음으로 관측된다 (`probe_kip_up_gemini.py` 가 프로브 패턴).
- **구조적 방어 (현행 유지):** ① support K=2/3 게이트(단발 환각 drop), ② 비교 프롬프트 rule 1·2(정타/촬영조건 비결함), ③ tol 20° dead-zone — 짚여도 window median ≤20° 면 감점 0, ④ temperature 0.0 + rich 캐시 결정론.
- **잔여 FP 리스크 산식:** P(clean 에서 짚음) × P(window Δ>20°). 260702-o0c 이 증명한 것: 후자는 높다(RTMW jitter/촬영거리로 success 4/6 FP). 즉 **FP 방어 전체가 vision 게이트 하나에 실림** — §2 의 좁은 매퍼(broad 확장 금지)가 게이트의 실질이다. 최종 심판 = success 6/6==100 sweep.

### 4. eval 설계 [VERIFIED: run_sweep.py / assert_gates.py]

- **하네스 재사용:** `backend/evals/phase24/run_sweep.py` (phase18 6페어 both-member mode1, serial in-process `_process`, pdshape cold-rerun 결정론 체크, Pod 실행 커맨드 헤더에 박제) + `assert_gates.py` (traceability/monotonicity/determinism/criterion-selection/generalization/clean_residual). evals/phase25 로 복제-확장.
- **Phase 25 게이트 추가분:** ① success 멤버 `overallScore == 100` 명시 assert (현행 check_generalization 은 within-tolerance record 허용 — 25 게이트는 더 강함), ② kip-up fault: `deductionBreakdown.records` 에 상체 criterion 존재 AND **모든 angle_vs_reference window-sourced record 의 관절 ⊆ vision-pointed set** (구조 assert — 점수 assert 금지), ③ 기존 5동작 fault 변별 무퇴행.
- **Gemini 크레딧/캐시:** PROMPT_VERSION(현 v9.0)/집계 marker bump → whole_fanout 캐시 전량 miss → cold sweep = 12 멤버 × 3 call = **36 Gemini pro call + 멤버당 영상 2 업로드**. 실행 전 크레딧 충전 확인 필수([[gemini-credits-depleted-2026-06-20]]). warm 재실행은 캐시 hit 로 0 call (결정론 게이트용).
- **Pod:** RTMW GPU 필수, 신규 pod 면 Network Volume + bootstrap + Lambda env 재동기화([[next-pod-use-network-storage]], [[runpod-gpu-env]]). sweep 은 반드시 순차([[pipeline-not-concurrency-safe-eval-serial]]).

### 5. 함정 [VERIFIED: 코드 + 메모리 이력]

1. **캐시 키 충돌 이력 재발 금지:** kip-up FP 확정 원인이 `whole` vs `whole_fanout` stale-hit 이었다(90d038f fix). 새 캐시 형상 변경 시 기존 키 공간 재사용 절대 금지 — 새 granularity/버전 marker.
2. **집계 변경 = 캐시 무효화 필요 (비직관):** rich 캐시는 support-게이트 **통과 후** supported_differences 를 저장 — 프롬프트 안 바꿔도 `_filter_supported_differences` 그룹핑을 바꾸면 stale 결과가 살아남는다. SCHEMA_VERSION 또는 키 내 aggregation marker bump.
3. **at_seconds=None 유지:** full-video fanout 에 worst-pose 힌트를 넘기면 dynamic 결함을 좁혀 놓친다(실측 확정, app.py:1898 주석). 건드리지 말 것.
4. **자원 bound fail-closed:** `GEMINI_MAX_VETO_WALL_S=120s`, `MAX_VETO_CALLS=9`, planned=3(scope 수). scope/call 을 늘리면 planned 전부 완료 전 예산 소진 → `resource_limited`(score-free) 로 전 분석이 빠질 수 있음. call 수 증가는 wall budget 재검토 동반.
5. **프롬프트 bump = 전 동작 회귀 표면:** v9.0 프롬프트는 6동작 공용 — 변경 시 6페어 full sweep 이 유일한 회귀 게이트. upper_body scope 호출에만 추가되는 지시라도 PROMPT_VERSION 은 전역이라 전 캐시 무효.
6. **pointed 매퍼 과확장(§3):** `fault_joints_from_differences` 의 trunk/양다리 broad 확장을 감점 게이트에 쓰면 vision 게이트 무력화 — 표시용(faultJoints)과 감점용(pointed) 매퍼를 분리.
7. **이미 있는 이중감점 방어 재구현 금지:** seed-stage expects_extension 차단(f513587 helper 내장) + 엔진 HIGH-5 claimed_joints discard(split→hip). kip-up 은 criteria yaml 이 빈 리스트(무릎 EXTEND 도 2026-06-27 제거됨 — focus 의 "현재 무릎 EXTEND 만" 은 stale, elbow-twist 도 제거됨)라 expects_extension 전부 False → 어깨 방출 무차단.
8. **점수 짜맞추기 금지:** "kip-up fault == 특정값" assert 금지 — 구조 assert 만.

## 동반 스코프 조사 — 확대 카드 정밀도 [VERIFIED: fault_zoom.py / app.py fz4 배선]

현행: `fault_zoom.py` 에 grouped-bbox crop(`_BBOX_MARGIN`), 저신뢰(<0.5) keypoint 측 **전신 폴백**(quick-260702-sic), advisory 티어(`select_advisory_joints`, tol=`_LINE_TOL_DEG` 재사용, `zoom_adv_` S3 키 분리, tier confirmed/advisory)까지 배선 완료. 갭 = reference 측이 저신뢰면 **카드마다 동일 전신 사진 반복**. 자연 해법(roadmap): vision 이 확정한 프레임(`sourceFrameIndices` median — quick-260702-sic 의 user/ref_frame_idx override 이미 존재) + 부위 bbox 완화 crop 으로 카드별 차별화. vision-확인 관절의 advisory→confirmed 승격은 감점 배선(§2)이 완성되면 fault_joints 에 자연 포함되어 별도 로직 최소.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 (`backend/requirements-dev.txt`) |
| Config | 없음 (관례: `backend/tests/`) |
| Quick run | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/ -k "deduction or vision or criteria" -x -q` |
| Full suite | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/ -q` (기존 54 pre-existing fail = app-module-name-collision + gemini/knee env — HEAD 동일 여부로 회귀 판단) |
| Pod eval | `backend/evals/phase24/run_sweep.py` 패턴 (헤더의 env 커맨드 그대로) → phase25 복제 |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Command | Exists? |
|-----|----------|-----------|---------|---------|
| 짚인 관절만 window seed | pointed ∩ JOINT_KEYS 만 wm 값, 나머지 dtw median | unit (pure) | pytest `_build_deduction_measured_deviations` 신규 테스트 | ❌ Wave 0 |
| 좁은 pointed 매퍼 | shoulder/arm keypoint_set 만, trunk 확장 배제 | unit (pure) | pytest vision_veto 신규 매퍼 테스트 | ❌ Wave 0 |
| 집계 fragment fold | side/fault_kind fold 후 support 카운트 | unit (pure) | pytest `_filter_supported_differences` 확장 | ✅ 기존 테스트 파일 확장 |
| 캐시 버전 bump | 새 marker 로 기존 키 miss | unit | pytest VisionVetoCache build_key | ✅ 확장 |
| success 6/6==100 + 구조 게이트 | Pod 6페어 sweep | integration (Pod, 수동) | run_sweep + assert_gates 확장 | ❌ Wave 0 (harness 복제) |

### Sampling Rate
- per task commit: quick run (위 -k 필터)
- per wave: backend full suite + app `npm run typecheck`(앱 접촉 시)
- phase gate: Pod 6페어 sweep cold+warm — success 6/6==100 AND kip-up 구조 assert

### Wave 0 Gaps
- `backend/evals/phase25/` harness (phase24 복제 + success-멤버 collect 관측 캡처 + 구조 게이트)
- pointed 매퍼/seed merge 단위 테스트 파일

## Security Domain

내부 채점 파이프라인 변경 — 신규 패키지 0, 신규 네트워크 표면 0, 인증/세션 무접촉. 해당 ASVS: V5 입력검증만 — Gemini 응답 파싱은 기존 가드 재사용(`_parse_verdict` graceful, `_SCORE_PATTERN` 누출 폐기, NaN/Inf guard in tally, `FaultKey.from_dict` enum 거부). window delta 파싱 시 f513587 의 try/except + abs() 패턴 유지. 시크릿: GEMINI 키 = SSM `/sunity/motion/gemini-api-key`(로컬 조회는 `--profile sunity-motion` 필수), 하드코딩 금지.

## Package Legitimacy Audit

신규 외부 패키지 설치 없음 — 감사 대상 없음.

## Environment Availability

| Dependency | Required By | Available | Fallback |
|------------|------------|-----------|----------|
| RunPod GPU pod (RTMW+CUDA) | sweep 실측/게이트 | ✗ (직전 pod terminate 이력 — 재생성 필요) | 없음 — plan 에 pod bootstrap 태스크 필요 |
| Gemini API 크레딧 | cold sweep 36 calls | 미확인 | 없음 — 실행 전 충전 확인 태스크 |
| 로컬 pytest (numpy) | 단위 테스트 | ✓ | — |
| fixtures/phase15 6페어 S3 | sweep 입력 | ✓ (phase24 sweep 이 사용) | — |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 어깨 미산출이 "support fragment" 인지 "differences[] 미방출" 인지 artifact 로 구분 불가 — 둘 다 처방(집계 fold + 프롬프트 보강) 필요하다고 가정 | §1 | 한쪽만으로 충분할 수 있음 — Pod 프로브(probe 스크립트)로 첫 태스크에서 판별 권장 |
| A2 | per-move 프롬프트 특정성은 동작명 하드코딩이 아니라 profile/criteria 공급 힌트 형태여야 curve-fit 밴과 양립 | §1 | belle 이 동작명 명시를 허용하면 더 단순한 설계 가능 — discuss 확인 |
| A3 | window 측정 record 의 source 표기(geometry 유지 + 별도 관찰 마커) | §2 | 투명성 원칙 위반 소지 — discuss 확인 |

## Open Questions

1. **(RESOLVED — OD-1, orchestrator 2026-07-04)** pointed 매퍼의 side 해소 규칙 — side=unknown 이면 **양측 모두 window-측정 eligible** 로 확정 (판정은 측정+tol 게이트, fail-closed 버리기 금지). 단 broad 확장 방지를 위해 좁은 전용 매퍼 신설(line/전신 류 제외). → 25-01-PLAN Task 1 에 반영.
   ▸ 원 질문: side=unknown 어깨 faultKey 는 양쪽 다 짚은 것으로 볼지(보수적=양쪽 window), 한쪽 최대만 볼지. 권장: 양쪽 — 측정이 tol gate 를 통과해야만 감점되므로 과감점 위험은 tol 이 흡수. Pod sweep 이 심판.
2. **(RESOLVED — OD-2, orchestrator 2026-07-04)** success-멤버 짚기-FP 관측 — **eval 전용** 으로 확정 (production na_audit/스키마 무접촉). phase25 harness 가 read-only tee 로 캡처, 게이트는 감점 결과(success 6/6==100)가 지고 짚기-FP율은 관측 지표. → 25-04-PLAN Task 1 에 반영.
   ▸ 원 질문: production audit 에도 남길지(na_audit 확장) eval 전용으로 할지 — 스키마 접촉 최소화 관점에서 eval 전용 권장.

## Sources

- [VERIFIED: 코드] `gemini_vision_scorer.py`(프롬프트 v9.0/스키마 v7.0/fanout/support 게이트/캐시), `vision_veto.py`(FaultKey/키워드 매핑/fault_joints 매퍼), `ipsf_criteria.py`(라우터/CoverageGap/criterion 표), `deduction_engine.py`(tally/split vision 주입/HIGH-5), `app.py`(collect/apply/md 빌드/fz4 advisory), `features.py`(window_median_angle_deltas), `fault_zoom.py`
- [VERIFIED: git] `git show f513587`(revert 된 window seed diff — 00d19a5/c927286 로 revert)
- [VERIFIED: artifact] `backend/evals/phase24/baseline/phase24_sweep_report.json`(kip-up fault 어깨 Δ40.4/31.0 측정-무감점 + 짚기 1건 직접 증거)
- [CITED: memory] window-median-silent-seed-fp-reverted, kipup-fp-RESOLVED-phase24A, kipup-fp-root-cause-cache-key-collision-FIXED, flash-beats-pro-video-split-judgment, gemini-credits-depleted, pipeline-not-concurrency-safe-eval-serial, scoring-redesign-must-generalize-no-overfit

## Metadata

**Confidence:** 원인 규명/배선 지점/함정 = HIGH (전부 코드·artifact 검증). 짚기-FP 빈도 = LOW (관측 공백 — eval 이 채움). 프롬프트 레버 효과 = MEDIUM (과거 실측 근거는 있으나 상체 대상 미검증).
**Research date:** 2026-07-04 · **Valid until:** 코드베이스 변경 시 (특히 gemini_vision_scorer/ipsf_criteria 접촉 커밋)
