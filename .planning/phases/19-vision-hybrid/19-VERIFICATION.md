---
phase: 19-vision-hybrid
verified: 2026-06-18T00:00:00Z
status: human_needed
score: 24/24 must-haves verified
overrides_applied: 0
human_verification:
  - test: "실기기(TestFlight native build)에서 3D 골격 렌더 육안 검증 — 신규 doc + 과거 doc 모두, PoseViewer3D GL frustum 내 렌더 + OrbitControls + timeline scrub"
    expected: "골격이 화면 frustum 안에 들어와 정상 렌더되고(절단/사라짐 없음), 회전/스크럽이 동작한다"
    why_human: "GL on-device 렌더는 native build + 실기기에서만 시각 확인 가능. 코드 수준 정규화(좌표 frustum 적합)는 smoke 로 자동 검증됐으나 실제 GPU 렌더 결과는 grep/유닛으로 검증 불가. belle 가 approved-with-deferred-device-check 로 다음 native build TestFlight 묶음에 합류시킴 (STATE.md Wave 2 override 동일 처리)"
---

# Phase 19: 분석 점수 신뢰도 재설계 (vision-hybrid 채점) Verification Report

**Phase Goal:** v1 — 평균식 집계를 IPSF 감점식 집계로 교체(단일 major fault 가 종합 지배, 정은지 fault 영상 94/89% 위양성 제거) + 확정 버그 3건 수정(표시-점수 정합, 어깨 라벨/stability 오인, 3D 골격 렌더) + Mode3 미보유동작 유효성 게이트 + v2 vision-veto hook 자리(v1 pass-through). v2 비전 거부권 본체는 deferred.
**Verified:** 2026-06-18
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1   | kismam.overall_score 가 감점식(평균 아님)이고 단일 major fault 가 종합 지배 | ✓ VERIFIED | `kismam.py:213-243` `total_penalty += over*w*1.2`, `100-total_penalty`. test_single_major_fault_dominates(단일 50° fault → <70) + test_clean_pose_high_score(전부 8° → ≥90) PASS |
| 2   | 정상 동작(편차<tol)은 높은 점수 유지 (위양성 없음) | ✓ VERIFIED | dead-zone `over=max(0,dev-20)`; test_clean_pose_high_score PASS; anchor test_above_cutoff_synthetic_stays_high PASS (always-on) |
| 3   | 신전 요구 관절 160° 미달 시 line 차원 0점(요소 무효) | ✓ VERIFIED | `dimensions.py:263-264` `if any(a < _SPLIT_FAIL_THRESHOLD_DEG(160) ...): return 0`. test_micro_bent_zero_track PASS |
| 4   | 의도적 굽힘(expects_extension False) 관절은 0점 트랙 미적용 | ✓ VERIFIED | `dimensions.py:254-258` rep_angles 필터가 `profile.expects_extension(k)` 만 포함 |
| 5   | overall_from_dimensions = min-of-core(angle/line), stability 분리 | ✓ VERIFIED | `dimensions.py:384-400` core=CORE_DIMENSIONS=(angle,line), `min(core)`; stability 제외. test_overall_from_dimensions_uses_core_dimensions PASS |
| 6   | stability 가 높아도 angle/line 낮으면 종합 낮음 (인플레 차단) | ✓ VERIFIED | min-of-core 가 stability 미입력. assemble contributesToOverall=false + weightPercent=0 (`assemble.py:306-314`) |
| 7   | 어깨 COACHING_FOCUS 라벨이 '안정성'(떨림) 오인 아님 | ✓ VERIFIED | `kismam.py:80-81` left/right_shoulder='자세각'. test_shoulder_focus_label(≠'안정성', '떨림'/'어깨' 미포함) PASS |
| 8   | 표시 각도값이 점수 산출 DTW path-정렬 median 과 동일 source (TRUST-01) | ✓ VERIFIED | `pipeline/app.py:1541-1585` `_angles_to_dtw_median_dicts` (per_joint_deviation 동일 DTW path). Mode1(:1979)·Mode3(:1772) 호출. 구 `_angles_to_mean_dict` orphaned(미호출) |
| 9   | scoringBasis 가 실제 채점 SOURCE 로 라벨링 (Mode3 4-value, reference_motion 부재) | ✓ VERIFIED | `assemble.py:582-605` 4 enum; `pipeline/app.py:1693-1708` `_mode3_scoring_basis`. test_unknown_move_gate 4-param + reference_motion invariant PASS |
| 10  | Mode1 reference_motion basis 는 build_mode1 이 OPTIONAL 직렬화 (Mode3 미경유) | ✓ VERIFIED | `assemble.py:630` `"scoringBasis": MODE1_SCORING_BASIS`. test_mode1_scoring_basis_reference_motion PASS |
| 11  | Mode3 미보유 동작 = is_reference_free_motion 판정 → 절대트랙 + reference-free basis (fail-closed/raise 없음) | ✓ VERIFIED | `assemble.py:130-150` (copyBranch 단독 분기 금지, None→True); `pipeline/app.py:1732-1736` wiring, raise 없음. test_unknown_move_gate copyBranch-equal-but-basis-differs invariant PASS |
| 12  | scoringBasis/Label 이 result 화면 + DimensionDetailModal 에 표시 | ✓ VERIFIED | `result.tsx:682-683` 헤더 렌더 + `:1074-1075` modal 전달; `DimensionDetailModal.tsx:65,184` isReferenceFreeBasis 분기 |
| 13  | contributesToOverall===false 차원은 modal 에 보조지표 카피 | ✓ VERIFIED | `DimensionDetailModal.tsx:198` `isAuxiliaryDimension = explanation?.contributesToOverall === false` |
| 14  | v1 vision hook = SAME-OBJECT identity pass-through (점수 불변), v2 슬롯 미차단 | ✓ VERIFIED | `pipeline/app.py:1631-1659` `return score_result` (copy 없음), graceful try/except, `overallScore` 키 문서화. test_vision_hook_passthrough(`out is score_result` + mutation 0) PASS |
| 15  | 3D 골격 골반중심 recenter + 몸통길이 정규화, frustum 안 (TRUST-04 code-side) | ✓ VERIFIED (code) / human_needed (device) | `normalizePose3d.ts:66-106` hip-mid recenter + torso scale. smoke(maxAbsCoord<=3) EXIT=0. 실기기 GL 렌더는 deferred — 아래 Human Verification |
| 16  | hip/shoulder 인덱스를 jointKeys(COCO-17)에서 indexOf 도출 | ✓ VERIFIED | `normalizePose3d.ts:190` `jointKeys.indexOf(HIP_LEFT)` 등. 8 angle JOINT_KEYS 미참조 |
| 17  | 정규화 출력 frame 수 == 입력 frame 수 (per-frame drop 금지) | ✓ VERIFIED | `normalizePose3d.ts:198-228` prevValid 또는 zeroSkeleton 폴백; WR-04 joint-count 가드(:215-217). smoke frame_count_stable PASS |
| 18  | 정규화 순수수학 단일 source — joints.ts + smoke 동일 함수 import | ✓ VERIFIED | `joints.ts:21,66` `import { normalizeFrames }` + 호출; smoke `:21,26,129` createRequire + LOCAL tsc 컴파일 (복제 없음) |
| 19  | smoke 는 thrown error + process.exitCode 로 실패 신호 (inline process.exit 0건) | ✓ VERIFIED | `_smoke_joints_normalize.mjs:213` `process.exitCode = exitCode`; inline `process.exit(` 0건; finally cleanup |
| 20  | 3-way contract(analysis.ts/models.py/contract.md) overallScore=min-of-core 일관 (CR-01 fix) | ✓ VERIFIED | contract.md:161 + analysis.ts:339 = "min-of-core"; pipeline:2002 comment 정정; models.py 미러 일관 |
| 21  | RED 테스트가 behavior 실패 형태로 실재 (collection 아님) | ✓ VERIFIED | 6 신규 케이스 + 갱신 케이스 GREEN; 70 passed (targeted), 85 passed/6 skipped (확장) |
| 22  | D-05 앵커 per-test @requires_anchor_env gate + synthetic always-on | ✓ VERIFIED | `test_anchor_known_answer.py` 6 anchor SKIPPED(GPU 부재) + test_above_cutoff_synthetic_stays_high PASS (module-level skip 아님) |
| 23  | 감점 임계가 IPSF 근거 인용 (보유 13영상 curve-fit 아님) | ✓ VERIFIED | `_IPSF_TOLERANCE_DEG=20` CoP §4 인용; `_SPLIT_FAIL_THRESHOLD_DEG=160`=180−20[CITED]; `_PENALTY_PER_DEG=1.2` 정직히 `[ASSUMED]` + no-overfit memory 인용 |
| 24  | NaN/Inf 편차 가드 (WR-02/03/04) — graceful degrade, raise 없음 | ✓ VERIFIED | `kismam.py:121,239` np.isfinite 가드; `assemble.py:320,326` finite filter; `normalizePose3d.ts:215-217` joint-count 가드 |

**Score:** 24/24 truths verified (truth #15 code-side verified; on-device GL render is the human-verify item below)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `backend/shared/.../kismam.py` | overall_score 감점식 + shoulder 라벨 | ✓ VERIFIED | def overall_score deduction; COACHING_FOCUS shoulder='자세각' |
| `backend/shared/.../dimensions.py` | line_score 0점 트랙 + overall min-of-core | ✓ VERIFIED | 160° 무효 + overall_from_dimensions min(core) |
| `backend/shared/.../assemble.py` | is_reference_free_motion + build_mode3/build_mode1 basis + contributesToOverall | ✓ VERIFIED | 4-value enum + ValueError 가드 + Mode1 always-emit |
| `backend/functions/pipeline/app.py` | DTW median + MODE_SELF 게이트 + scoring_basis + vision hook | ✓ VERIFIED | 모두 정의 + wired |
| `app/src/types/analysis.ts` | Mode1/Mode3 scoringBasis + contributesToOverall + min-of-core doc | ✓ VERIFIED | union 정확, CR-01 fix |
| `backend/shared/.../models.py` | contract 미러 | ✓ VERIFIED | MODE3_SCORING_BASES + contributesToOverall |
| `app/src/lib/normalizePose3d.ts` | 정규화 단일 source | ✓ VERIFIED | normalizeFrames standalone, react/expo import 0 |
| `app/src/lib/joints.ts` | reshapePose3dData → normalizeFrames | ✓ VERIFIED | :66 호출 |
| `app/scripts/_smoke_joints_normalize.mjs` | LOCAL tsc + createRequire 자동검증 | ✓ VERIFIED | EXIT 0, 복제 없음 |
| `app/src/app/analysis/result.tsx` | Mode3 scoringBasisLabel 헤더 | ✓ VERIFIED | :682-683 렌더 |
| `app/src/components/DimensionDetailModal.tsx` | reference-free copy + 보조지표 카피 | ✓ VERIFIED | isReferenceFreeBasis + isAuxiliaryDimension |
| `docs/contract.md` | overallScore min-of-core | ✓ VERIFIED | :161 정정 |
| 4 test 모듈 | RED→GREEN 케이스 | ✓ VERIFIED | 신규 케이스 모두 존재 + PASS |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| dimensions.line_score | profile.expects_extension | 신전 요구 관절만 160° 0점 트랙 | ✓ WIRED | :254-264 |
| dimensions.overall_from_dimensions | DIM_ANGLE/DIM_LINE | core 만 입력, stability 제외 | ✓ WIRED | :396-398 CORE_DIMENSIONS |
| assemble.build_dimension_explanation | contributesToOverall | stability 비기여 표시 | ✓ WIRED | :306-314 |
| pipeline MODE_SELF | assemble.is_reference_free_motion | angleSource/fixtureKey/ipsfCode/officialName 판정 | ✓ WIRED | :1732-1736 |
| assemble.build_mode1 | analysis.ts Mode1Comparison | scoringBasis='reference_motion' 직렬화 | ✓ WIRED | :630 + TS :250 |
| assemble.build_mode3 | result.tsx | scoringBasisLabel 헤더 | ✓ WIRED | :670 + result.tsx :683 |
| pipeline 점수 산출 직후 | _apply_vision_veto | v1 SAME-OBJECT identity | ✓ WIRED | :2226 호출, :1656 identity |
| joints.ts reshapePose3dData | normalizePose3d.normalizeFrames | 단일 정규화 source | ✓ WIRED | :66 |
| smoke | normalizePose3d.normalizeFrames | LOCAL tsc + createRequire | ✓ WIRED | :129 호출 |
| pipeline display | _angles_to_dtw_median_dicts | 표시=점수 DTW median 통일 | ✓ WIRED | :1772, :1979 |

### Behavioral Spot-Checks / Probe Execution

| Check | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| Phase 19 targeted suite | `pytest test_kismam/dimensions/assemble/assemble_dimension_explanation/pipeline_mode3` | 70 passed | ✓ PASS |
| anchor known-answer | `pytest test_anchor_known_answer.py -v` | 1 passed(synthetic always-on), 6 skipped(GPU-gated) | ✓ PASS |
| 확장 analysis suite | `pytest test_*(analysis+segments+technique+selfmotion)` | 85 passed, 6 skipped | ✓ PASS |
| 3D normalize smoke | `node scripts/_smoke_joints_normalize.mjs` | SMOKE_PASS maxAbsCoord<=3 + frame_count_stable, EXIT=0 | ✓ PASS |
| app typecheck | `npx tsc --noEmit` | TSC_EXIT=0 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| SCORE-06 | 19-01, 19-02 | 감점식 종합 집계, 단일 major fault 지배 | ✓ SATISFIED | Truths #1,#2 |
| SCORE-07 | 19-01, 19-02 | micro-bent 0점 트랙 (extension-required only) | ✓ SATISFIED | Truths #3,#4 |
| TRUST-01 | 19-01, 19-04 | 표시 각도 = 점수 DTW-정렬 median 정합 | ✓ SATISFIED | Truth #8 |
| TRUST-02 | 19-01, 19-02 | 어깨 라벨 정정 + stability 종합 분리 | ✓ SATISFIED | Truths #6,#7 |
| TRUST-03 | 19-01, 19-04 | Mode3 미보유 게이트 + 점수근거 표시 | ✓ SATISFIED | Truths #9,#10,#11,#12 |
| TRUST-04 | 19-03 | 3D 골격 실기기 렌더 (정규화) | ✓ SATISFIED (code) / ? NEEDS HUMAN (device) | Truths #15,#16,#17,#18,#19; on-device 렌더 deferred |
| TRUST-05 | 19-01, 19-04 | v2 vision hook 자리 (v1 pass-through) | ✓ SATISFIED | Truth #14 |

모든 7 requirement ID 가 plan frontmatter 에 매핑됨 (orphan 없음). REQUIREMENTS.md 의 Phase 19 매핑(SCORE-06/07, TRUST-01~05)과 일치.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| dimensions.py | 246 | "박제 박제 박제 박제" docstring filler | ℹ️ Info | review IN-03 (Info, out-of-scope). 동작 무관 주석 노이즈 — no-baekje memory 위반이나 비기능 |

debt marker(TBD/FIXME/XXX) 스캔: Phase 19 수정 파일 전부 0건 — blocker 없음.

### Human Verification Required

#### 1. 실기기 3D 골격 렌더 육안 검증 (TRUST-04 — approved-with-deferred-device-check)

**Test:** 다음 native build(TestFlight)에서 신규 doc + 과거 doc 분석 결과의 3D 골격(PoseViewer3D)을 열어 GL frustum 내 정상 렌더 + OrbitControls 회전 + timeline scrub 동작을 확인.
**Expected:** 골격이 화면 frustum 안에 들어와 절단/사라짐 없이 렌더되고, 회전/스크럽이 동작한다.
**Why human:** GL on-device 렌더는 native build + 실기기에서만 시각 확인 가능. 코드 수준 정규화(좌표가 frustum 에 적합)는 smoke(maxAbsCoord<=3) 로 자동 검증 완료됐으나, 실제 GPU 렌더 결과는 grep/유닛으로 검증 불가. belle 가 "approved-with-deferred-device-check" 로 승인 — 다음 native build TestFlight 묶음(STATE.md Wave 2 override 와 동일 처리)에 합류.

### Gaps Summary

블로커 갭 없음. 24/24 observable truths 가 코드베이스에서 검증됨 — 감점식 집계(단일 major fault 지배), micro-bent 0점 트랙, min-of-core(stability 분리), Mode3 미보유 게이트(fail-closed 없음, reference_motion 미emit), v1 vision identity hook(overallScore 키 정합), 3D 정규화 단일 source, 3-way contract CR-01 정합 모두 실재하고 wired. 8 review finding(1 Critical + 7 Warning) 전부 fix 확인(NaN/Inf 가드, prevValid joint-count 가드, vision 키 정합 포함). 임계값은 IPSF 인용 또는 정직한 `[ASSUMED]` 표기로 보유 13영상 curve-fit 회피.

유일한 미완 항목은 TRUST-04 의 **on-device GL 렌더 육안 검증** — belle 가 의도적으로 다음 native build 로 연기(approved-with-deferred-device-check)하고 outstanding human-UAT 로 추적 중. 코드 측 정규화는 전부 통과(smoke EXIT 0). 이 단일 human-verify 항목 때문에 status=human_needed (passed 는 human 항목이 비어야 유효).

Info 1건(dimensions.py:246 docstring filler)은 review IN-03 으로 이미 식별된 비기능 주석 노이즈 — gap 아님.

---

_Verified: 2026-06-18_
_Verifier: Claude (gsd-verifier)_
