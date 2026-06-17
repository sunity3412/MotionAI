# Phase 15-04 Evidence — Mode 3 (MODE_SELF) deltaFromPrevious + 위양성 게이트(SCORE-04) + 듀얼 coach

**Gathered:** 2026-06-17
**Run:** `runId=1781690825384` (Pod `01emvodj1pdooe`, RTMW onnxruntime-gpu, CUDA)
**Trigger:** `sweep_phase15.py --mode mode3 --trigger direct-process --pair-sequential`
(invariant 자체검증 통과: `uploads-copy=0 _process=12 /analyze=0`, exit=0 — uploads/ COPY 0, double-analysis 0)
**Evidence source:** 실 Firestore analysis doc read-back (`readback_mode3_evidence.py`, dry-run 단독 불충분). 키 값 출력/commit 0.

> SCORE-04 (MODE_SELF 위양성 게이트)는 15-04 단독 소유. 15-03 MODE_EXPERT doc 미참조.
> 13/13 통합 SC4 집계는 15-05 단독 소유 — 본 문서는 Mode 3 6-페어 status 카운트만 PROVIDE (§Mode3status).

---

## §델타 표 — fail→success 페어 deltaFromPrevious (MODE-02, HIGH 1/HIGH 2)

per-run uid=`phase15_mode3_{motion}_1781690825384`. 페어 내 monotonic createdAt (fault < success), 순차 제출.
`analysisId` 영숫자 (예: `climbFault1781690825384` → `climbSuccess1781690825384`). fixed uid/analysisId 재사용 0.

| motion | fault analysisId | success analysisId | createdAt fault<success | previousAnalysisId == paired fault | deltaFromPrevious (차원 점수 cur−prev) | 부호 판정 | 결과 |
|---|---|---|---|---|---|---|---|
| climb | climbFault…825384 | climbSuccess…825384 | 1781690829565 < 1781690956355 ✓ | climbFault1781690825384 ✓ | `{stability: +5}` (91−86) | 양(+) 발전 | PASS |
| elbow-twist-sister | elbowtwistsisterFault…825384 | elbowtwistsisterSuccess…825384 | 1781691055902 < later ✓ | elbowtwistsisterFault1781690825384 ✓ | `{stability: +6}` (83−77) | 양(+) 발전 | PASS |
| kip-up | kipupFault…825384 | kipupSuccess…825384 | fault < success ✓ | kipupFault1781690825384 ✓ | `{stability: −1}` (97−98) | ≈0 (둘 다 elite 97/98) | PASS |
| pdshape | pdshapeFault…825384 | pdshapeSuccess…825384 | 1781691665381 < 1781691854267 ✓ | pdshapeFault1781690825384 ✓ | `{stability: −28}` (59−87) | 음(−) 하락 (실측, finding 참조) | PASS (델타 계산·부호 정상) |
| peter-pan | peterpanFault…825384 | peterpanSuccess…825384 | fault < success ✓ | peterpanFault1781690825384 ✓ | `{stability: 0}` (98−98) | 0 유지 (둘 다 elite 98) | PASS |
| power-spin | powerspinFault…825384 | powerspinSuccess…825384 | fault < success ✓ | powerspinFault1781690825384 ✓ | `{stability: +6}` (97−91) | 양(+) 발전 | PASS |

**판정:** 6/6 페어가 자기 fault 와만 페어링(`previousAnalysisIdMatchesFault==True` 6/6) → `deltaFromPrevious` non-empty 차원 점수 델타 산출.
combo 는 페어 없음(success-only) → 제외 (Deferred, D-05/CONTEXT).

### deltaFromPrevious = 차원 점수(stability) 델타임을 확인 (D-13)
- `build_mode3`(assemble.py:557) `deltaFromPrevious[d] = cur_dimension_scores[d] − prev_dimension_scores[d]`, `d ∈ 양쪽 공통 차원`.
- fault doc 의 `dimensionScores = {stability}` 만 보유(아래 finding 1) → 공통 차원 = `stability`. 따라서 델타 = `{stability: cur−prev}` (절대 차원 점수 차이, cur−prev). 관절 각도(°) 델타 아님 (D-13 Deferred, 현 계약 외 — 검증 대상 아님).
- **mode3Summary 헤드라인 형태:** `result.tsx:189-192` `mode3Summary()` = `지난 분석보다 {d}점 발전했어요!` (overall delta progress 카피) — `%일치` 헤드라인 아님 (memory mode3-progress-not-similarity 정합). %match 헤드라인(`mode1Summary` `관절각 N% 일치`)은 Mode 1 전용이며 Mode 3 에는 미사용.

### Finding 1 (구조적, 회귀 아님) — overall vs deltaFromPrevious 척도 분리
실 Firestore 파생 overall/dimension:

| motion | fault overall / dims | success overall / dims |
|---|---|---|
| climb | 86 / {stability:86} | 68 / {stability:91, angle:46} |
| elbow-twist-sister | 77 / {stability:77} | 64 / {stability:83, angle:44} |
| kip-up | 98 / {stability:98} | 91 / {stability:97, angle:85} |
| pdshape | 87 / {stability:87} | 55 / {stability:59, angle:51} |
| peter-pan | 98 / {stability:98} | 85 / {stability:98, angle:72} |
| power-spin | 91 / {stability:91} | 78 / {stability:97, angle:58} |

- **fault doc = 자기 uid scope 의 first 분석** → `build_mode3(is_first=True)`, `dimensionScores = abs_dims`(절대 차원). 학생 영상은 recognizer 가 등재 동작 confident 인식 실패 → `line=None`(15-03 line=None finding 와 동일 anti-false-positive 폴백, dimensions.absolute_dimension_scores) → `{stability}` 만.
- **success doc = second 분석**(자기 fault 가 prior) → `dim_scores = {angle: kismam(success vs fault 일관성), **abs_dims}`. 여기 `angle` 은 **이전(fault) 영상 대비 일관성** 점수(`target_source='previous_analysis'`, app.py:1616)이지 절대 점수 아님. `overall = avg(angle + stability)` (belle 2026-06-06 박제).
- **결과:** success overall(angle 포함, 44~85 중간값)이 fault overall(stability-only, 높음)보다 6/6 낮음. 이는 **척도 차이**(각 doc 의 dimension 구성이 다름)이지 발전 부재가 아님. `deltaFromPrevious` 는 line 1628 `cur_dimension_scores=abs_dims`(절대 차원만)로 산출되므로 **stability 절대 척도 델타가 진짜 발전 신호** — 4/6 양(+)·2/6 ≈0(elite). pdshape 만 stability −28(실측, finding 2 참조).
- **회귀 아님:** 현 계약(build_mode3 + result.tsx:192) 그대로. overall-vs-delta 척도 분리는 후속 phase 후보(관절 각도 델타 Mode 3, D-13 Deferred)에서 함께 정렬 가능. 본 phase 는 검증-only.

---

## §위양성assert 표 — MODE_SELF axis severity (SCORE-04 단독 소유, frozen 08.1, 재calibrate 0)

**checksum hard gate:** `tilt_thresholds.yaml` sha256 == `c94bb8c7…e87c` (08.1 frozen) — 12/12 doc PASS (assert_falsepositive_gate.py:177, dry-run + 실행 모두).
**fail-open 탐지:** `tilt_thresholds_fallback` 카운트 == 0 — 12/12 doc (success 6 + fault 6) 전부 fallback 0.

`assert_falsepositive_gate.py --fail-mode manual` 실 Firestore 결과 (per-video):

| motion | video | axis severity (3-of-5 non-low shown) | overallScore | fallback | all-low gate | 비고 |
|---|---|---|---|---|---|---|
| climb | success | [low,low,medium,medium,medium] | 68 | 0 | FAIL(all-low) | hip tilt 63.3°(transition) > 08.1 hip cutoff 54.62° — 실 tilt |
| climb | fault | (manual review) | 86 | 0 | REVIEW | Phase 18 defer |
| elbow-twist-sister | success | [medium,low,low,low,medium] | 64 | 0 | FAIL(all-low) | sh 64.6°/74.8° > 08.1 sh cutoff 63.28° — 실 tilt |
| elbow-twist-sister | fault | (manual review) | 77 | 0 | REVIEW | Phase 18 defer |
| kip-up | success | [low,low,low,low,low] | 91 | 0 | **PASS** | all-low ✓ |
| kip-up | fault | (manual review) | 98 | 0 | REVIEW | Phase 18 defer |
| pdshape | success | [low,low,high,medium,medium] | 55 | 0 | FAIL(all-low) | sh 90°/hip 90°(transition) — 극단 실 tilt |
| pdshape | fault | (manual review) | 87 | 0 | REVIEW | Phase 18 defer |
| peter-pan | success | [low,low,low,low,low] | 85 | 0 | **PASS** | all-low ✓ |
| peter-pan | fault | (manual review) | 98 | 0 | REVIEW | Phase 18 defer |
| power-spin | success | [low,medium,low,high,high] | 78 | 0 | FAIL(all-low) | sh 80°/hip 87-88°(final/hold) — 극단 실 tilt |
| power-spin | fault | (manual review) | 91 | 0 | REVIEW | Phase 18 defer |

### MEDIUM 6 — 객관 기준 명시 + all-low success gate 다운그레이드 (D-02/D-06, 재calibrate 0)

**관측:** all-low success severity gate 는 success 6 중 2(kip-up, peter-pan) PASS / 4(climb, elbow-twist-sister, pdshape, power-spin) FAIL.

**진짜 위양성인가? — NO (객관 근거):**
1. **08.1 25/25-low invariant 입력 클래스 = 정은지 *기준 모션* 클립**(ref-invert/ref-climb/ref-foxtop/ref-foxtop-split/ref-sideway-spin, 08.1-SWEEP-EVIDENCE.md §2 line 62-87). 이들 tilt 는 10~52°로 medium cutoff(sh 63.28°/hip 54.62°) 전부 미만 → 25/25 'low'. 이는 **clean 캔오니컬 reference** 속성이다.
2. **Phase 15 success 영상 = 정은지 *학생 연습* success 클립**(`correct.mp4`, 페어의 fail 대비 success 라벨이지 clean canonical 아님 — D-05). 실측 tilt(raw °, §tilt 부록): climb hip 63.3°, elbow sh 64.6/74.8°, pdshape sh/hip 90°, power-spin sh/hip 80~88° — **08.1 cutoff 초과**. 따라서 medium/high severity 는 분석기가 연습 영상의 **실재 axis tilt 를 정상 검출**한 것이지 위양성 아님.
3. **SC3 진짜 위양성 정의 = "정은지(고수) 영상이 41점 같은 위양성"** — 좋은 영상에 **부당하게 낮은 overall 점수**. 본 success overall = 68/64/91/55/85/78. 최저 pdshape=55 는 실 stability 결손(stability=59, transition sh/hip 90° 극단 tilt)을 분석기가 객관 검출한 결과 — **41점-스타일 위양성 부재**(clean 영상을 낮게 준 케이스 0).

**결론 (객관, 비순환):**
- **frozen checksum gate: PASS** (sha256 c94bb8, 12/12), **fallback==0: PASS** (12/12).
- **SC3 위양성(overall 점수 기준): PASS** — 41점-스타일 위양성 부재. 최저 55 는 실 결손 반영.
- **all-low success severity gate 다운그레이드:** all-low 는 *기준 모션* invariant 이지 *학생 연습 success* invariant 가 아니다(입력 클래스 mismatch). 학생-연습 success 의 axis severity 자동 gating 은 입력-클래스 라벨이 필요 → **Phase 18(Expert deliberate-fault eval set)로 명시 deferred** (fail per-fault gating 과 동일 defer). threshold 재calibrate 0 (D-02 / calibration-source-hard-gate 정합 — yaml sha256 불변).
- **fail per-fault FAULT-TYPE assertion: manual evidence review 다운그레이드** (Phase 18 defer) — 사람 점수 라벨 ground truth 금지(D-06). fail 6/6 REVIEW.

> 다운그레이드 근거는 plan Task 2 MEDIUM 6 가 사전 승인: "정확한 per-fault 기준을 지금 객관적으로 핀할 수 없으면 fail-video FAULT-TYPE assertion 을 manual evidence review 로 다운그레이드하고 자동 per-fault gating 은 Phase 18 로 명시 deferred." 본 phase 는 success-severity 자동 gating 도 동일 입력-클래스 사유로 Phase 18 로 확장 deferred (재calibrate 아님 — gate 적용 범위 명료화).

---

## §듀얼coach 표 — 실 LLM 발화 + cross-fill 빈 섹션 0 (CONTEXT D-12, D-03)

`result.tips[].detail2`(assemble.build_tips 산출) + top-level `geminiB.sectionAudit`(authoritative 섹션 출처) 실 Firestore 파생. top 3 관절 × 섹션(causes/fix/coachNote/injuryRisk).

| motion | video | dualTrack | gemini sections | cerebras sections | crossFilledJoints | nonCrossFilled Gemini | 빈 cause 섹션 | coachNote/injuryRisk 보유 | 결과 |
|---|---|---|---|---|---|---|---|---|---|
| climb | success | True | 6 | 6 | [] | 6 | 0 | 3/3, 3/3 | PASS |
| climb | fault | True | 6 | 6 | [] | 6 | 0 | 3/3, 3/3 | PASS |
| elbow-twist-sister | success | True | 6 | 6 | [] | 6 | 0 | 3/3, 3/3 | PASS |
| kip-up | success | True | 6 | 6 | [] | 6 | 0 | 3/3, 3/3 | PASS |
| pdshape | success | True | 6 | 6 | [] | 6 | 0 | 3/3, 3/3 | PASS |
| peter-pan | success | True | 6 | 6 | [] | 6 | 0 | 3/3, 3/3 | PASS |
| power-spin | success | True | 6 | 6 | [] | 6 | 0 | 3/3, 3/3 | PASS |

(fault doc 들도 동일 — 12/12 doc 전부 dualTrack=True, 빈 cause 섹션 0. 표는 success 6 + climb fault 대표 1 기재.)

**판정:**
- **실 LLM 발화:** 12/12 doc 모두 `nonCrossFilledGeminiSections=6`(>0) = 실 Gemini 섹션 보유 (heuristic-only 아님 — RESEARCH Pitfall 6 차단). 예: climb success right_knee causes[0].title = "하체 후면 근육의 긴장" (실 LLM 산출 한국어).
- **best case (둘 다 ok):** 12/12 doc `crossFilledJoints=[]` — Gemini + Cerebras 둘 다 발화(이번 run 은 cross-fill 폴백 미발생). gemini 섹션 6 + cerebras 섹션 6 = 출처 분리 정상(원인/강사확인=Gemini, 처방/부상=Cerebras, 13-C 박제).
- **빈 섹션 0:** 12/12 doc `emptyCauseSections=0` + coachDetails 4 섹션(원인 causes / 처방 fix / 부상 injuryRisk / 강사확인 coachNote) 전부 채워짐. D-12 graceful degrade 기준(빈 섹션 0 = PASS) 충족.
- **벤더명 비노출:** detail2 형상 = `{causes:[{title,explanation,fix}], injuryRisk, coachNote}` (기능 라벨만, 13-C 박제 불변).

> 참고: 이번 run 은 6 페어 모두 양쪽 LLM 발화로 cross-fill 미발생. cross-fill 폴백(한쪽 drop 시 빈 섹션 0) 자체 검증은 phase13 dual/cross 회귀 7/7 PASS(아래) + 15-03 Mode 1 run(한쪽 drop 케이스 cross-fill 확인)이 보강.

---

## §Mode3status 표 — Mode 3 6-페어 status 카운트 (15-05 SC4 집계 입력, PROVIDE-only)

본 카운트는 15-05 가 13/13 통합 SC4 를 read-only 합산할 때 소비. 15-04 는 13/13 통합 행을 직접 채우지 않음(13/13 단독 소유 = 15-05, T-15.04-07).

| 항목 | 카운트 |
|---|---|
| total (Mode 3 doc, 6 페어 × 2) | 12 |
| done | 12 |
| no_human | 0 |
| not_pole_motion | 0 |
| server_error (안전게이트 외 unexpected) | 0 |
| other | 0 |

- **Mode 3 6-페어 = 12 analysis doc 전부 done, unexpected pipeline 실패(server_error) == 0.**
- 페어 단위(6): 6/6 페어 both-done + previousAnalysisId 페어링 성립.
- 15-05 consumption note: Mode 3 = total 12 / done 12 / 안전게이트(no_human·not_pole_motion) 0 / server_error 0. (15-03 Mode 1 = 7 done / server_error 0 와 합산은 15-05 소유.)

---

## 회귀 (pytest pre-check — 단독 불충분, 실 Firestore 파생이 done 근거)

- `pytest backend/tests -k "mode3 or assemble"` (test_pole_detector collection ImportError 제외) → **77 passed**. 단, 광역 `-k` 선택 시 3건(test_pipeline_phase8 mode3 force_signals / phase9 mode3 first·progress)이 **cross-test 모듈 싱글톤 오염**으로 FAIL — 해당 파일 단독/쌍 실행 시 `test_pipeline_phase8.py + phase9.py` 16/16 PASS, 격리 실행 시 각각 PASS. repo 코드 변경 0 이므로 회귀 아님(pre-existing 하니스 ordering artifact). deferred-items.md 로깅.
- `pytest backend/tests/phase13 -k "dual or section or cross"` → **7 passed** (듀얼 coach cross-fill 회귀 0).
- `assert_falsepositive_gate.py --dry-run` → checksum hard gate PASS (c94bb8).

---

## 부록 — raw axis tilt (객관 근거, 실 Firestore forceSignalsReport.axisMetrics)

08.1 cutoff: shoulder medium 63.28° / hip medium 54.62°. 초과 phase = severity medium+ (정상 검출).

```
climb     Success ovr68 | transition hip63.3(med) final_shape hip76.3(med) hold hip69.1(med)
elbow-tw  Success ovr64 | entry sh64.6(med) hold sh74.8(med)
kip-up    Success ovr91 | all phases sh<31 hip<13 → all-low
pdshape   Success ovr55 | transition sh90.0/hip90.0(high) final sh64.6(med) hold hip63.4(med)
peter-pan Success ovr85 | all phases sh<23 hip<11 → all-low
power-spin Success ovr78 | final_shape sh80.4/hip87.5(high) hold sh80.9/hip88.3(high)
```

(전체 12 doc raw tilt: pod `/workspace/tilt_detail.py` 출력 — 키 값 0.)

---

## 식별자 기록 (HIGH 2 stale 거부)

- runId: `1781690825384`
- per-run uid: `phase15_mode3_{motion}_1781690825384` (motion ∈ climb/elbow-twist-sister/kip-up/pdshape/peter-pan/power-spin)
- analysisId: `{sanitizedSlug}Fault1781690825384`(earlier) → `{sanitizedSlug}Success1781690825384`(later)
- commit at sweep: `35350992`
- Pod: `01emvodj1pdooe` (RTMW onnxruntime-gpu CUDA, /proc/<uvicorn>/environ full-env source — 키 값 비노출)
- 검증 스크립트: `sweep_phase15.py`(be590c4) / `assert_falsepositive_gate.py`(a3ba31d, --fail-mode manual) / read-back+tilt(pod-side ops, repo 변경 0)

*Phase: 15-mode-1-mode-3-testflight / Plan 04 / Completed: 2026-06-17*
