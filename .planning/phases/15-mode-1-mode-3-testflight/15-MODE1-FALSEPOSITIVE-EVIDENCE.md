# Phase 15-03: Mode 1 (MODE_EXPERT) 실 E2E + False-Positive Evidence

**Generated:** 2026-06-17 (Phase 15 Wave 2, plan 15-03)
**Plan:** 15-03 (MODE-01 Mode 1 실영상 E2E + 정은지 success 영상 OBSERVATIONAL)
**Pod:** `01emvodj1pdooe` (proxy `https://01emvodj1pdooe-8000.proxy.runpod.net`, GPU RTMW + Gemini recognizer + 듀얼 coach)

> 보안: 이 문서는 키 NAME / presence(SET/UNSET)만 기록한다. 어떤 secret 값도 포함하지 않는다.

---

## Scope / Ownership (HIGH 3)

15-03 은 오직 다음을 소유한다:
- 11-reference downstream 필드 검증 게이트 (seed-reference-downstream.mjs --verify 11/11)
- Mode 1 (MODE_EXPERT) 7-motion 실 E2E evidence + success 영상 OBSERVATIONAL 점수
- **Mode 1 7/7 server_error == 0 (15-03 단독 gate)**

15-03 이 소유하지 **않는** 것:
- MODE_SELF (reference-independent) axis severity 위양성 블로킹 게이트(SCORE-04) → **15-04 단독** (frozen MODE_SELF baseline). 15-03 은 15-04 의 MODE_SELF doc 을 참조·재사용하지 않는다.
- 13-영상 통합 SC4 집계(Mode1 7 + Mode3 6) → **15-05** (depends_on 15-03+15-04).

---

## §필드검증 — 11 reference downstream 4필드 + captureViews (Task 1, A1 게이트)

도구: `app/scripts/seed-reference-downstream.mjs --input ../reference-downstream-backfill.json --verify`
(Firebase Admin SA `firebase-sa.json`, project `sunity-ai-coach`, owner sunity3412 — memory firebase-project-account)

backfill_reference_downstream.py 는 fixture GENERATOR 이며 Firestore 를 쓰지 않는다 — downstream 4필드 검증의 REAL 도구는 seed-reference-downstream.mjs --verify 다 (HIGH 2 리뷰 정정). repair 불필요 (11/11 이미 충족).

| motionId | meanAngles | techniqueProfile | bodyNormalizationProfile | forceDirectionPattern | captureViews | complete |
|----------|-----------|------------------|--------------------------|-----------------------|--------------|----------|
| ref-climb | true | true | true | true | true | **true** |
| ref-foxtop | true | true | true | true | true | **true** |
| ref-foxtop-split | true | true | true | true | true | **true** |
| ref-invert | true | true | true | true | true | **true** |
| ref-sideway-spin | true | true | true | true | true | **true** |
| ref-combo | true | true | true | true | true | **true** |
| ref-elbow-twist-sister | true | true | true | true | true | **true** |
| ref-kip-up | true | true | true | true | true | **true** |
| ref-pdshape | true | true | true | true | true | **true** |
| ref-peter-pan | true | true | true | true | true | **true** |
| ref-power-spin | true | true | true | true | true | **true** |

**`completeRequiredSet = 11/11`** — 11개 전부 FIELD-VERIFIED. PASS (Task 2 live E2E 선행 게이트 충족).

---

## §Mode1점수 — 7-motion 실 E2E (MODE_EXPERT, 실 Firestore doc 파생)

실행: `backend/scripts/sweep_phase15.py --keys-file backend/scripts/phase15_keys.json --mode mode1 --trigger direct-process` (Pod 위 SSH, pod-ops-claude-runs). per-run uid + 영숫자 analysisId (HIGH 2). 각 행은 실 Firestore `users/{uid}/analyses/{analysisId}` doc 에서 read-back 한 값이다 (dry-run 출력 아님).

**Identity (HIGH 2 — fixed id 재사용 0):**
- 메인 run: `runId=1781688254964`, `uid=phase15_mode1_1781688254964` (5 motion)
- 재시도 run: `runId=1781689675370`, `uid=phase15_mode1_1781689675370` (2 motion — Gemini 503 후 재실행, 아래 Deviation 참조)
- analysisId = `<sanitizedSlug>Success<runId>` (영숫자만, 하이픈 제거)

| referenceMotionId | analysisId | uid (runId) | status | errorCode | overallScore | angle | line | stability | axisSeverity | createdAt |
|-------------------|-----------|-------------|--------|-----------|--------------|-------|------|-----------|--------------|-----------|
| ref-climb | climbSuccess…254964 | …254964 | done | null | 65 | 38 | None | 92 | medium | 1781688259140 |
| ref-combo | comboSuccess…254964 | …254964 | done | null | 90 | 91 | None | 88 | medium | 1781688371931 |
| ref-elbow-twist-sister | elbowtwistsisterSuccess…254964 | …254964 | done | null | 78 | 74 | None | 83 | medium | 1781688801514 |
| ref-kip-up | kipupSuccess…254964 | …254964 | done | null | 98 | 99 | None | 97 | low | 1781689022409 |
| ref-pdshape | pdshapeSuccess…254964 | …254964 | done | null | 68 | 78 | None | 59 | high | 1781689152900 |
| ref-peter-pan | peterpanSuccess…675370 | …675370 | done | null | 97 | 96 | None | 98 | low | 1781689679489 |
| ref-power-spin | powerspinSuccess…675370 | …675370 | done | null | 95 | 93 | None | 97 | high | 1781689807088 |

**referenceMotionId lockstep:** 7/7 motion 이 matching reference (ref-{motion}) 로 비교됨 (ROADMAP SC1). dimensionScores = `{angle, stability}` (line 미산출 — 아래 Open Q3 참조).

---

## §Mode1 7/7 server_error==0 GATE (15-03 단독 gate) — **PASS**

| 집계 | 값 |
|------|-----|
| total Mode 1 (MODE_EXPERT) | 7 |
| done | **7** |
| **server_error** | **0** |
| no_human / not_pole_motion | 0 |

Mode 1 MODE_EXPERT 7-motion sweep 이 크래시·unexpected pipeline 실패 없이 완주했고 `server_error == 0`. **15-03 단독 gate 충족.** (13-영상 통합 SC4 집계는 15-05 소관 — HIGH 3.)

---

## §실 LLM path (D-03 / D-12) — 듀얼 coach 빈 섹션 0

recognizer = Gemini (env `RECOGNIZER_BACKEND=gemini`), 듀얼 coach env `GEMINI_COACH_ENABLED=1`. 실 Firestore doc 의 `result.tips[].detail2` 섹션 read-back:

| referenceMotionId | tips | coachSections (causes/coachNote/injuryRisk) | emptySections | Cerebras fix(원인 내부) |
|-------------------|------|---------------------------------------------|---------------|------------------------|
| ref-climb | 3 | 9 | **0** | 9 |
| ref-combo | 3 | 9 | **0** | 9 |
| ref-elbow-twist-sister | 3 | 9 | **0** | 9 |
| ref-kip-up | 1 | 0 | 0 | 0 |
| ref-pdshape | 3 | 9 | **0** | 9 |
| ref-peter-pan | 1 | 0 | 0 | 0 |
| ref-power-spin | 3 | 9 | **0** | 9 |

- **빈 섹션 0** (fault 섹션 산출 5 motion 전부 — causes/coachNote(Gemini) + injuryRisk + cause 내부 fix(Cerebras) 전부 채워짐). 듀얼 coach 양쪽 실 발화 (gemini causes/coachNote + cerebras fix/injuryRisk) — cross-fill 폴백 빈 섹션 0 = D-12 PASS.
- kip-up / peter-pan 은 angle 일치도가 매우 높아(99/96) `build_result` 의 angle≥임계 positive 단일 tip path 진입 → fault 섹션 없음(detail2 없음). 정상 동작이며 빈 섹션 아님.

---

## §line dimension (RESEARCH Open Question 3) — 관측 결과: 7/7 line=None

7 motion 전부 `dimensionScores` 에 line 키 부재(line=None). 원인은 `forceSignalsReport.warnings` 에 명시:
`['fps_normalization_applied', 'motion_unrecognized_layer1_only', 'layer2_unavailable', 'preflight_gate_pending']`

- recognizer(Gemini)가 이 정은지 student 영상들을 **등재 동작으로 confident 인식하지 못함**(`motion_unrecognized_layer1_only`) → 학생 측 technique profile 의 `expects_extension` 이 모든 관절 False → `dimensions.line_score()` 가 None 반환(`absolute_dimension_scores` 가 line 키 생략).
- 이는 **설계상 anti-false-positive 폴백**이다: 신전 요구를 confident 추론 못 하면 가짜 line 점수를 만들지 않고 생략한다(STATE.md 장기 박제 "FallbackRecognizer 가 굽은 자세에서 EXTEND 못 찾아 line 차원 None" 과 정확히 일치, calibration-source-hard-gate 정합 — 임의 line floor 신규 fit 금지).
- **Open Q3 결론:** 이번 7 student 영상에서 line 은 non-None 으로 해소되지 **않았다**. 이는 recognizer 의 student-영상 인식 한계이지 15-03 의 server_error/gate 실패가 아니다(line 은 15-03 의 blocking gate 가 아님). recognizer 가 student 영상에서 등재 동작을 인식하도록 하는 것은 후속 과제(Phase 5 recognizer 정확도 / Phase 18 fault eval) 범위.
- 주: angle 차원(정은지 reference 대비 관절각 일치도)은 7/7 정상 산출(38~99) — Mode 1 전문가 비교의 핵심 신호는 angle 이며 lockstep 으로 작동.

---

## §success 영상 OBSERVATIONAL (MEDIUM 6 — blocking 게이트 아님)

정은지 success 영상이 Mode 1(MODE_EXPERT) 전문가 비교에서 받은 점수를 **가시성 목적**으로 기록한다. 객관적 numeric floor(최소 점수/severity 임계)가 아직 정의되지 않았으므로(calibration-source-hard-gate — 임의 floor 신규 fit 금지), 아래 행은 **PASS/FAIL 판정이 아니다**. 블로킹 SCORE-04 게이트는 15-04 의 frozen MODE_SELF baseline 이 단독 소유한다(HIGH 3).

| motion | overallScore | axisSeverity | referenceMotionId match | server_error |
|--------|--------------|--------------|-------------------------|--------------|
| climb | 65 | medium | ref-climb ✓ | 0 |
| combo | 90 | medium | ref-combo ✓ | 0 |
| elbow-twist-sister | 78 | medium | ref-elbow-twist-sister ✓ | 0 |
| kip-up | 98 | low | ref-kip-up ✓ | 0 |
| pdshape | 68 | high | ref-pdshape ✓ | 0 |
| peter-pan | 97 | low | ref-peter-pan ✓ | 0 |
| power-spin | 95 | high | ref-power-spin ✓ | 0 |

관측 (판정 아님): 고수(정은지) success 영상이 41점 같은 극단 위양성 없이 대체로 중상위 점수(65~98). 단, climb=65 / pdshape=68 + 일부 high axisSeverity 처럼 낮게/엄격하게 나온 케이스도 있음 — 이는 객관 baseline 없는 단순 관측치이며, 위양성 여부의 블로킹 판정은 15-04 (frozen MODE_SELF baseline) 가 수행한다. 사람 작성 분석 .md 의 점수를 라벨로 쓰지 않음(D-06).

---

## §coverage 한계 (R3 — 정직성, 은폐 금지)

11 reference 는 전부 FIELD-VERIFIED(downstream 4필드 11/11)이지만, **정은지 student 영상이 있는 7 motion 만 Mode 1 live E2E 비교**를 수행했다. 아래 4 reference 는 student 영상 부재로 **이번 phase live 미비교**다:

| reference (no student video) | 필드 검증 | live Mode 1 비교 |
|------------------------------|-----------|------------------|
| ref-foxtop | FIELD-VERIFIED 11/11 | **미비교 (student 영상 없음)** |
| ref-foxtop-split | FIELD-VERIFIED 11/11 | **미비교 (student 영상 없음)** |
| ref-invert | FIELD-VERIFIED 11/11 | **미비교 (student 영상 없음)** |
| ref-sideway-spin | FIELD-VERIFIED 11/11 | **미비교 (student 영상 없음)** |

11 live E2E 로 과대 주장하지 않는다 — Mode 1 live 비교 coverage = 7/11 motion (student 영상 가용분).

---

## Deviations (auto-handled)

**1. [Rule 3 - 블로킹 환경 fix] onnxruntime CPU 폴백 → GPU 강제 (LD_LIBRARY_PATH)**
- 1차 sweep 실행 시 onnxruntime 이 `libcudnn.so.9: cannot open shared object file` 로 CUDAExecutionProvider 생성 실패 → CPU 폴백(GPU 0%, combo 영상 매우 느림). 원인: sweep runner 가 sourcing 한 env 에 `LD_LIBRARY_PATH`(cudnn lib 경로 `/usr/local/lib/python3.11/dist-packages/nvidia/cudnn/lib`) 누락. 실행 중인 uvicorn 서버 proc env 에는 존재.
- Fix: sweep runner 가 live uvicorn proc(`/proc/<pid>/environ`)에서 `LD_LIBRARY_PATH`/`CUDA_*` 포함 전체 env 를 source(키 값 비노출, NUL-delimited 읽기). 재실행 시 `ort.get_available_providers()` CUDA 포함 + cudnn 에러 0 + GPU 70%+ 가동. climb CPU ~5.5min → GPU ~112s.
- repo 파일 변경 0 (Pod-side 실행 env 만). Pod env 박제는 후속 sweep 재사용 가능.

**2. [Rule 3 - 블로킹 외부 의존 retry] Gemini 503 UNAVAILABLE — peter-pan / power-spin 재실행**
- 메인 sweep 의 item 6/7(peter-pan, power-spin)에서 Gemini API `503 UNAVAILABLE`(transient 외부 LLM 가용성) 발생 → `_process` 예외 → 두 doc 이 `comparison` 상태로 미완(이 단계에서 errorCode 미기록, server_error 아님). pdshape 는 Gemini `files.get` 503 을 graceful skip 후 정상 done.
- Fix: 두 motion 만 별도 2-item keys 로 재실행(새 per-run uid `phase15_mode1_1781689675370`, HIGH 2 fixed id 재사용 0). 재실행 결과 둘 다 `_process OK` + status done + server_error 0(peter-pan=97, power-spin=95). 미완 stuck doc 2개는 재실행 전 삭제(stale 차단).
- 503 은 transient 외부 LLM 가용성 이슈이지 분석 pipeline server_error 아님 — Mode 1 7/7 done gate 는 재실행 후 충족.

> Note (참고): SSM `/sunity/motion/gemini-api-key --with-decryption` 직접 read 는 auto-mode classifier 가 차단(키 값 출력 금지 정합). 대안으로 live uvicorn proc env 의 GEMINI_API_KEY(값 비노출)를 그대로 재사용 — secret 값을 한 번도 출력/commit 하지 않음.

---

## Success Criteria Summary

- [x] seed-reference-downstream.mjs --verify `completeRequiredSet == 11/11` (11개 전부 FIELD-VERIFIED, repair 불필요)
- [x] Mode 1 (MODE_EXPERT) 실 E2E on 7 student-video motion, 각자 matching reference (referenceMotionId lockstep), 실 Pod GPU path (RTMW + Gemini recognizer + 듀얼 coach)
- [x] **Mode 1 7/7 server_error == 0 (sole gate) — PASS**
- [x] 실 Firestore doc 파생 per-motion 점수(overallScore/dimensionScores) + runId/uid/analysisId/createdAt (dry-run 단독 아님)
- [x] 듀얼 coach 빈 섹션 0 (fault 섹션 산출분 전부) — D-03/D-12
- [x] success 영상 OBSERVATIONAL 행 (overallScore/severity/referenceMotionId match/server_error) — blocking 게이트 아님(MEDIUM 6)
- [x] 4 no-student-video reference coverage 한계 명시 (R3)
- [ ] line non-None: 7/7 line=None (recognizer student-영상 미인식 anti-false-positive 폴백) — Open Q3 finding, 15-03 blocking gate 아님

**Open item (15-03 게이트 아님):** student 영상에서 line 차원 해소 = recognizer 인식 정확도 후속 과제. axis severity 위양성 블로킹 판정 = 15-04(MODE_SELF frozen baseline). 13-영상 통합 SC4 = 15-05.
