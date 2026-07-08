---
phase: 28-dtw-motion-based-alignment
verified: 2026-07-08T15:10:00Z
status: human_needed
score: 11/11 must-haves verified
overrides_applied: 0
human_verification:
  - test: "비교 재생 정렬 체감 (D-01/A2) — warped doc에서 두 영상이 동작 기준으로 함께 흐르는지"
    expected: "정은지(right)가 학생 타임라인에 워핑되어 동작 싱크 유지"
    why_human: "expo-video playbackRate 실기기 지연/재버퍼는 코드로 검증 불가. 배치 UAT (phase 31 후 합동, belle 결정) — 28-HUMAN-UAT.md #1"
  - test: "스크럽/재시작 동기 유지 (Pitfall 7)"
    expected: "스크럽 직후·재시작 직후 drift/stutter 없음"
    why_human: "실기기 seek 타이밍 — 28-HUMAN-UAT.md #2"
  - test: "tier 배지 카피 3종 (D-02)"
    expected: "warped/trim_only/disabled 별 정직한 카피 표시 (가짜 수치 0)"
    why_human: "시각 확인 — 28-HUMAN-UAT.md #3"
  - test: "legacy 재분석 유도 배너 (D-05)"
    expected: "motionAlignment 부재 doc에서만 배너+CTA, 신규 disabled doc은 배너 없음"
    why_human: "legacy doc 실기기 확인 — 28-HUMAN-UAT.md #4"
  - test: "확대비교 카드 정합 (D2 종결/D-04) — mode3 second+ 포함 (CR-01 fix 실카드)"
    expected: "기준 측 크롭이 비교 부위와 같은 pose 순간, 대응 실패 시 전신+캡션"
    why_human: "Pod 실 mode3 카드 육안 확인 권장 (CR-01 fix status) — 28-HUMAN-UAT.md #5"
  - test: "결과 화면 진입→이탈 에러 로그 (WR-05)"
    expected: "unmount 시 released-object 예외/크래시 리포트 없음"
    why_human: "unmount 경로 실기기 전용 — 28-HUMAN-UAT.md #6"
---

# Phase 28: 동작 기반 비교 정렬 (DTW 워핑) Verification Report

**Phase Goal:** 두 영상(학생 vs 정은지)의 동작 기반 시간정렬 부재를 한 기능으로 해소 — D2(fault_zoom 크롭 오정합)와 power-spin 싱크 문제를 dtw_match 기반 워핑/트리밍으로 동시 해결. 백엔드(정렬 데이터 방출) + 앱(VideoCompare 소비). Phase 22 v1 시간 앵커 상위 호환 계약.
**Verified:** 2026-07-08 (HEAD 596f896)
**Status:** human_needed — 자동 검증 전부 통과, 실기기 6항목은 배치 UAT 적립분 (belle 정책, non-blocking)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | motionAlignment 3-way 계약 존재 + source 'vlm' 상위 호환 (ALGN-01) | ✓ VERIFIED | `analysis.ts:481` MotionAlignment interface + `:572` AnalysisResult.motionAlignment? / `models.py:182-187` MOTION_ALIGNMENT_KEYS·TIERS·SOURCES=('dtw','vlm')·MAX=512 / `contract.md:1529` §11 (§11.1~§11.6). 앱 normalizer VALID_SOURCES에 'vlm' 포함 |
| 2 | mode1+mode3 second+에 motionAlignment가 complete_analysis 동승 방출 — 초 단위 flat 앵커+tier+distance (ALGN-01) | ✓ VERIFIED | `app.py:4601-4620` mode 배타 분기 → `:4626` complete_analysis 직전 주입. ref_fps=doc 메타(`:3757` keypointReport.fps), user_fps=`_pipeline_frame_fps()`(리터럴 9.0 grep 0). Pod 실분석 DOC_CHECK_OK (uid phase28eval, anchors len 40 짝수·단조·초 단위) |
| 3 | degenerate 입력 → tier 'disabled' 방출 (legacy 필드 부재와 구분, W3) | ✓ VERIFIED | `motion_alignment.py:47-62` \_disabled (empty_path/invalid_fps/insufficient_anchors), None은 match=None만. 테스트 17개 중 degenerate 3형 GREEN |
| 4 | tier 사다리 = vision_veto 프로덕션 임계 재사용 + 클램프 0.5~2.0 lockstep (ALGN-02) | ✓ VERIFIED | DISTANCE_T1=8.0/T2=25.0 == `vision_veto.py:913-914` (lockstep 테스트 `test_motion_alignment.py:283-284` PASS). RATE 0.5/2.0 Python↔TS 텍스트 대조 `test_motion_alignment_contract.py:177` PASS. 자기 sweep 재보정 0 (calibration-source-hard-gate) |
| 5 | Firestore validator 역불변식 강제 (flat/finite/512/단조/tier↔anchors) | ✓ VERIFIED | `firestore_admin.py:308-405` \_validate_motion_alignment + `:1025` complete_analysis 훅. 12 validator 테스트 PASS (nested→TypeError, warped 빈 anchors→ValueError, disabled 빈 anchors→통과) |
| 6 | fault_zoom: ratio 근사 제거 + fps 도메인 정합(mode1·mode3) + 전신 폴백 + refMatch end-to-end (ALGN-03, D-04, CR-01) | ✓ VERIFIED | `fault_zoom.py:792` dtw_ref_fps 인자(CR-01, mode1=default None=r_rep_fps byte-identical, mode3=`app.py:3039` \_pipeline_frame_fps() 명시) + `:899-900` \_to_rep_idx 역변환 + `:992` refMatch 방출. mapper pass-through `app.py:2824-2825`. `test_ratio_approximation_removed_from_source` + mode3 실형상(report18fps+dtw9fps) 회귀 테스트 PASS. Pod doc faultZoomComparisons 3건 refMatch present |
| 7 | veto still 경로 무접촉 — 점수 이동 0 | ✓ VERIFIED | phase diff(8a6b106^..HEAD)에 \_build_selected_frame_pair 접촉 hunk 0. WR-04는 채점 무접촉 hard gate로 의도적 DEFERRED (28-REVIEW.md에 후속 백로그 기록 — pre-existing behavior 유지, phase 범위 밖) |
| 8 | VideoCompare 워핑: 정렬 활성 right 쓰기 전부 warp 경유 + rate feedforward/seek feedback + tier 배지 (ALGN-04, D-01) | ✓ VERIFIED | `rightPlayer.currentTime =` 3곳(:330 setRightToStudentTime→clampRefTarget, :338 setBothAbsoluteTime !alignmentActive 전용, :388 tick feedback→clampRefTarget) — 전부 warp/clamp 경유 또는 legacy 전용. rate는 구간 경계에서만(:414 lastRateRef diff 시). 배지 3종 카피 :869-875. 부재/null/disabled = legacy 100% 보존 |
| 9 | legacy 재분석 배너(D-05) + refMatch 캡션(D-04 앱측) (ALGN-05) | ✓ VERIFIED | `result.tsx:1471` `motionAlignment === undefined` 판정만(disabled 배너 아님) + CTA `router.replace('/(tabs)/analyze')`. refMatch 캡션 `DeductionDetailSheet.tsx:131-133` "같은 동작 순간을 찾지 못해 전신 화면으로 보여드려요" ← `result.tsx:1841` refMatchFailed prop |
| 10 | 채점 무접촉 — overallScore/deductionBreakdown diff 0 (ALGN-06, hard) | ✓ VERIFIED | phase diff에 vision_veto/kismam/dimensions/deduction/motiondtw 부재(재확인 grep 0). `test_no_scoring_contact_only_key_added` deepcopy diff-0 PASS. 실데이터 overallScore 52 = 결정론 baseline 무이동(28-08 박제). WR-03 fix로 non-finite distance의 간접 분석 실패 경로도 봉인(`motion_alignment.py:82-88` + NaN/inf 테스트 PASS) |
| 11 | 리뷰 fix 6건 코드 실재 + fix HEAD OTA 재발행 | ✓ VERIFIED | 커밋 f814b23(CR-01)/9178b7f(CR-02)/f8814b0(WR-02)/f3048b2(WR-01)/da8848e(WR-03)/7b0eec7(WR-05) 전부 존재, 코드 본문 직접 확인(위 truths 6/8/10 증거와 동일 지점). OTA 재발행 349aceb: preview 6a1df648 / production 1581bdf3, Pod pull 349aceb + /health ok (28-08 SUMMARY addendum, 커밋 596f896) |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `backend/shared/python/sunity_shared/analysis/motion_alignment.py` | build_motion_alignment 순수 함수 + tier 사다리 (min 80줄) | ✓ VERIFIED | 197줄, numpy·stdlib 외 import 0 (AST 가드 테스트로 봉인), WR-03 sanitize 포함 |
| `backend/tests/test_motion_alignment.py` | 계약 테스트 (min 80줄, degenerate 3형 포함) | ✓ VERIFIED | 358줄, 17 tests PASS (lockstep+AST 순수성 가드+nonfinite 포함) |
| `app/src/lib/alignmentWarp.ts` | warpTime/segmentRate/normalizeMotionAlignment 순수 함수, analysis.ts 계약 import | ✓ VERIFIED | 166줄, `import type { MotionAlignment } from '../types/analysis'` (:14), disabled 빈 anchors 예외 구현 |
| `app/src/types/analysis.ts` | MotionAlignment interface + AnalysisResult.motionAlignment? + FaultZoomComparison.refMatch? | ✓ VERIFIED | :467 refMatch, :481 interface, :572 optional 필드 |
| `backend/shared/python/sunity_shared/models.py` | MOTION_ALIGNMENT_* 계약 상수 블록 | ✓ VERIFIED | :182-187 KEYS/TIERS/SOURCES/MAX_ANCHOR_FLOATS=512 |
| `docs/contract.md` | §11 MotionAlignment 절 | ✓ VERIFIED | :1529 §11.1~§11.6 (역불변식 §11.4, refMatch §11.6) |
| `backend/shared/python/sunity_shared/firestore_admin.py` | \_validate_motion_alignment + complete_analysis 훅 | ✓ VERIFIED | :308 정의, :1025 훅 |
| `backend/functions/pipeline/app.py` | \_attach_motion_alignment + mode1/mode3 배선 + refMatch mapper pass-through | ✓ VERIFIED | :3352 helper(graceful try/except), :4601-4620 배선, :2824-2825 pass-through, :3039 CR-01 dtw_ref_fps |
| `backend/shared/python/sunity_shared/analysis/fault_zoom.py` | ratio 근사 제거 + fps 정합 + refMatch 방출 | ✓ VERIFIED | :792 dtw_ref_fps, :899-900 역변환, :913 전신 폴백, :992 refMatch |
| `app/src/components/VideoCompare.tsx` | alignment prop + helper 격리 + rate feedforward + tier 배지 | ✓ VERIFIED | :299-338 소비/helper, :376-418 tick 이중 제어, :865-875 배지, CR-02/WR-01/WR-02/WR-05 fix 반영 |
| `app/src/app/analysis/result.tsx` | alignment prop 전달 + legacy 배너 + refMatch 캡션 | ✓ VERIFIED | :1015 useMemo normalize, :1387 prop, :1471-1485 배너, :1841 캡션 prop |
| `backend/tests/test_motion_alignment_contract.py` | validator + 3-way 텍스트 lockstep 테스트 | ✓ VERIFIED | 185줄, 15 tests PASS |
| `backend/tests/test_pipeline_motion_alignment.py` | 방출 + 채점 무접촉 + graceful skip 테스트 (min 60줄) | ✓ VERIFIED | 154줄, 7 tests PASS (deepcopy diff-0 포함) |
| `backend/tests/test_fault_zoom_ref_match.py` | fps 변환/폴백/refMatch/근사 부재 + mapper 생존 테스트 (min 60줄) | ✓ VERIFIED | 296줄, 11 tests PASS (CR-01 실형상 재작성분 포함) |
| `backend/scripts/measure_reference_fps.py` | reference 11 doc fps 실측 (read-only) | ✓ VERIFIED | 171줄, `.set/.update/.delete` 0, A1 RESOLVED 출력 SUMMARY 박제 (11 doc 전부 18.0fps) |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| pipeline app.py | motion_alignment.build_motion_alignment | mode1 EXPERT + mode3 SELF 분기 호출 | ✓ WIRED | :85 import, :3371 호출, :4601-4620 양 분기 |
| pipeline app.py | firestore_admin.complete_analysis | result['motionAlignment'] complete 직전 주입 | ✓ WIRED | :4603/:4612 주입 → :4626 complete (27-06 게이트 정합, 사후 write 0) |
| motion_alignment.py | vision_veto.\_ALIGN_GLOBAL_T1/T2 | 값 재사용 + lockstep 테스트 | ✓ WIRED | 값 일치 8.0/25.0, 테스트가 drift 차단 |
| fault_zoom.py | \_to_rep_idx | rep↔frames 역변환 단일 공식 재사용 | ✓ WIRED | :899-900 (중복 공식 0) |
| app.py \_render_fault_zoom | fault_zoom refMatch | mapper 조건부 pass-through | ✓ WIRED | :2824-2825 ('dtw'/'failed' whitelist 복사), mapper 생존 테스트 3건 PASS |
| VideoCompare.tsx | alignmentWarp.ts | warpTime/segmentRate/normalizeMotionAlignment import | ✓ WIRED | :25-28 import, 소비측 재검증(:299) |
| VideoCompare.tsx | rightPlayer.playbackRate | 구간 경계에서만 설정 | ✓ WIRED | :414 lastRateRef diff 시에만 (매 tick 재설정 0), cleanup try/catch (WR-05) |
| result.tsx | VideoCompare | alignment={videoAlignment} prop (normalize 경유) | ✓ WIRED | :1015 useMemo → :1387 prop |
| result.tsx | /(tabs)/analyze | 배너 CTA router.replace | ✓ WIRED | :1477 (기존 재분석 플로우 재사용) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| result.tsx videoAlignment | result.motionAlignment | Firestore doc ← pipeline \_attach_motion_alignment ← 실 DTW match | Yes — Pod 실분석 doc에 tier=disabled·anchors 40 float 실재 (DOC_CHECK_OK) | ✓ FLOWING |
| VideoCompare tick target | clampRefTarget(cL) ← warpTime(alignment) | alignment prop (normalize 통과분) | Yes — 활성 시 warp, 부재 시 identity legacy | ✓ FLOWING |
| DeductionDetailSheet 캡션 | selectedZoom.refMatch | fault_zoom 방출 → mapper pass-through → doc | Yes — Pod doc faultZoomComparisons 3건 refMatch present | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| 정렬/계약/fault_zoom/파이프라인 테스트 | `pytest test_motion_alignment* test_pipeline_motion_alignment test_fault_zoom* test_pipeline_mode3 -q` | **134 passed** (0 failed) | ✓ PASS |
| 채점 무접촉 기계 판정 | `pytest -k no_scoring` | 1 passed (deepcopy diff-0) | ✓ PASS |
| 앱 typecheck | `npm run typecheck` | exit 0 | ✓ PASS |
| 채점 코어 phase diff | `git diff --name-only 8a6b106^..HEAD \| grep vision_veto\|kismam\|dimensions\|deduction\|motiondtw` | 0건 | ✓ PASS |
| veto still 무접촉 | phase diff 내 `_build_selected_frame_pair` hunk | 0건 | ✓ PASS |
| 실측 스크립트 read-only | `grep -c ".set(\|.update(\|.delete(" measure_reference_fps.py` | 0 | ✓ PASS |
| 리뷰 fix 커밋 실재 | `git log -1` × 6 해시 | 전부 존재 (f814b23, 9178b7f, f3048b2, f8814b0, da8848e, 7b0eec7) | ✓ PASS |
| Pod 실분석/OTA | — | 로컬 재실행 불가 — 28-08 SUMMARY DOC_CHECK_OK + addendum(596f896, OTA group ID 박제)으로 판정 | ? DOCUMENTED |

### Probe Execution

해당 없음 — 이 프로젝트에 `scripts/*/tests/probe-*.sh` 관례 부재, phase 게이트는 pytest/typecheck/grep (전부 위에서 재실행 PASS).

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
| ----------- | -------------- | ----------- | ------ | -------- |
| ALGN-01 | 28-01/02/03/04/08 | motionAlignment 계약+방출 (초 단위 flat 앵커+tier+distance, complete 동승, 'vlm' 상위 호환, mode1+mode3 second+) | ✓ SATISFIED | Truths 1/2/3 |
| ALGN-02 | 28-02/08 | tier 사다리 — vision_veto 임계 재사용, 클램프 0.5~2.0, calibration-source-hard-gate | ✓ SATISFIED | Truth 4 |
| ALGN-03 | 28-03/05/08 | fault_zoom D-04: 근사 제거+fps 정합+전신 폴백+refMatch, veto still 무접촉 | ✓ SATISFIED | Truths 6/7 |
| ALGN-04 | 28-06/07/08 | 앱 재생 워핑 D-01: warp 단일 경유, 이중 제어, tier 배지 | ✓ SATISFIED | Truth 8 (실기기 체감은 UAT #1-3) |
| ALGN-05 | 28-07/08 | legacy 재분석 유도 배너 D-05 | ✓ SATISFIED | Truth 9 (실기기 확인은 UAT #4) |
| ALGN-06 | 28-04/05/08 | 채점 무접촉 게이트 — overallScore/deductionBreakdown diff 0 (hard) | ✓ SATISFIED | Truth 10 |

Orphaned: 없음 — REQUIREMENTS.md에 Phase 28 매핑 행 부재 (ALGN IDs는 ROADMAP.md:946에서 mint, 6/6 전부 플랜이 클레임·검증됨).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (phase 수정 파일 15개) | — | TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER 스캔 | 없음 | debt marker 0 |
| 28-REVIEW.md frontmatter | :36 | `fix_report: 28-REVIEW-FIX.md` — 파일 미존재 (fix status는 REVIEW.md 본문 inline으로 기록됨) | ℹ️ Info | 추적성 무손실 (각 finding에 Status/commit 기록 완비), dangling 참조만 |
| 28-HUMAN-UAT.md | :14 | "production OTA는 approved 전까지 미발행" — belle 결정("지금 발행 — 배치 UAT") 이전 stale 문구 | ℹ️ Info | 실제 결정·발행 이력은 28-08 SUMMARY에 정확히 박제 |
| VideoCompare.tsx | :330/:338/:388 | 28-06 게이트 "직접 대입 정확히 2곳"이 WR-01 fix로 3곳이 됨 | ℹ️ Info | 3곳 전부 warp/clamp 경유 또는 !alignmentActive 전용 — 게이트의 실제 불변식("활성 경로 절대시간 대입 0")은 유지. 리뷰 fix의 정당한 결과 |

### Human Verification Required

배치 UAT 적립분 (28-HUMAN-UAT.md, pending 6 — phase 31 후 합동, belle 정책 [[batch-uat-after-phase-31]]. phase 진행 non-blocking):

### 1. 비교 재생 정렬 체감 (D-01/A2)

**Test:** warped tier doc에서 두 영상 비교 재생
**Expected:** 정은지가 학생 동작 타임라인에 워핑되어 동기 유지 (주의: 현 Pod 재분석 doc은 tier=disabled — warped 체감엔 정타 근접 doc 필요, 28-08 caveat)
**Why human:** expo-video playbackRate 지연·재버퍼는 실기기 전용

### 2. 스크럽/재시작 동기 유지 (Pitfall 7)

**Test:** 스크럽 후·재시작 후 재생
**Expected:** drift/stutter 없음 (WR-01 seek 폭풍 해소 확인 포함)
**Why human:** seek 타이밍 실기기 전용

### 3. tier 배지 카피 (D-02)

**Test:** tier별 doc에서 배지 확인
**Expected:** 3종 정직 카피, 가짜 수치 0
**Why human:** 시각 확인

### 4. legacy 재분석 유도 배너 (D-05)

**Test:** motionAlignment 부재 legacy doc 결과 화면
**Expected:** 배너+CTA 표시, 신규 disabled doc은 배너 없음
**Why human:** legacy doc 상태 실기기 확인

### 5. 확대비교 카드 정합 (D2/D-04, CR-01)

**Test:** mode1 + mode3 second+ 확대 카드 육안 확인
**Expected:** 기준 측 크롭 = 비교 부위 같은 pose 순간, 실패 시 전신+캡션
**Why human:** 프레임 정합은 육안 판정 (CR-01 fix가 실 mode3 카드 확인 권장)

### 6. 결과 화면 진입→이탈 에러 로그 (WR-05)

**Test:** 결과 화면 반복 진입/이탈
**Expected:** released-object 예외 없음
**Why human:** unmount 경로 실기기 전용

### Gaps Summary

**가짜 gap 없음.** SUMMARY 서사와 코드가 전 지점에서 일치했다 — 방출·계약·validator·워핑·배너·캡션·리뷰 fix 6건 전부 코드에 실재하고, affected 테스트 134건과 typecheck를 이 검증에서 직접 재실행해 확인했다. 채점 무접촉은 (a) phase-범위 diff에 채점 코어 부재, (b) deepcopy diff-0 기계 테스트, (c) 실데이터 overallScore 52 무이동의 3중 증빙. WR-04(veto still fps 오독)는 gap이 아니라 phase 범위 밖(28-VALIDATION 불변 제약 — veto still은 채점 인접이라 무접촉)의 의도적 deferral로 REVIEW.md에 후속 백로그로 기록되어 있다. 남은 것은 실기기 6항목뿐이며 belle 정책상 phase 31 후 배치 UAT로 이월 — phase 종결 non-blocking.

---

_Verified: 2026-07-08T15:10:00Z (HEAD 596f896)_
_Verifier: Claude (gsd-verifier)_
