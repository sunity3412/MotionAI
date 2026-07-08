---
phase: 27-1-gemini-analysis-speed-1min
verified: 2026-07-08T12:20:00Z
status: human_needed
score: 8/8 must-haves verified
overrides_applied: 0
human_verification:
  - test: "실기기에서 mode1 분석 완료 직후 결과 화면 진입 — 확대비교 카드가 로딩 placeholder(pending)로 표시되다 zoom PNG 도착 시 자동 전환되는지"
    expected: "점수/감점 내역 먼저 표시 → 확대비교 자리 ActivityIndicator + '준비하고 있어요' 카피 → onSnapshot 도착 시 이미지로 자동 전환. 180s 초과 시 조용히 숨김(무한 로딩 0)"
    why_human: "Firestore 부분 업데이트 → onSnapshot rerender 타이밍과 시각 전환은 실기기에서만 관찰 가능. 배치 UAT 정책 — HUMAN-UAT.md 적립, 즉시 belle 호출 금지"
  - test: "분석 대기 화면에서 폴스포츠 팁 텍스트 로테이션(6s 주기, 12개) 확인"
    expected: "대기 중 팁 문구가 주기적으로 교체 표시, 기존 카피 로테이터(4s)와 동시 점프 없음"
    why_human: "타이머 기반 시각 로테이션은 정적 분석으로 체감 검증 불가"
  - test: "분석 대기 중 진행률이 85%에서 멈추지 않고 계속 전진하는지 (comparison 구간 base 40 → 상한 97 재배분)"
    expected: "긴 비전/코치 구간 내내 진행률이 단조 전진 — '멈춘 것 같다' 체감 없음, 역행 0"
    why_human: "진행률 체감(대기 경험 D-02)은 실분석 실기기에서만 판정 가능 — 파일럿 피드백 재발 여부 확인"
---

# Phase 27: 분석 속도 1분 (analysis-speed-1min) Verification Report

**Phase Goal:** mode1 분석 시간을 belle 기준선 1분 내로 (시나리오 2 — 대기 경험). 레버: (a) Gemini File API 라운드트립 축소, (b) veto 결과-후 비동기 분리 검토, (c) 후처리 병렬화/축소. 게이트: 점수·verdict 무회귀(EVAL18 serial 대조) = hard. 시간은 "가능한 범위 최대 절감"이 목표치 — 1분은 지향점이지 hard 아님 (belle 원문 D-01, 27-09-PLAN 명시).
**Verified:** 2026-07-08T12:20:00Z
**Status:** human_needed (자동 검증 전량 통과 — 실기기 3항목은 배치 UAT 정책으로 적립)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | mode1 분석 시간 대폭 절감이 실측으로 증명된다 (before/after 대조표) | ✓ VERIFIED | 27-TIMING-BEFORE.md(122줄, runId 1783469050, cold 증빙) + 27-TIMING-AFTER.md §3 — TTFR median 229.6s→124.7s (−46%), s3 이상치 정규화 시 ~104s. 두-지표 분리(TTFR vs server task 총시간 133.7s) 기재. **1분 지향점 미달(104~125s)이나 스펙상 hard 아님** — hard gate는 무회귀(아래 #2) |
| 2 | 점수·verdict 무회귀 (EVAL18 SERIAL cold 대조, D-01 hard gate) | ✓ VERIFIED | 27-TIMING-AFTER.md §2 — success 5/5 record 완전 동일, fault drift 2건은 감점 증가(검출) 방향 + margin 유지·확대, 정본 assert_baseline.py PASS. cold 증빙(cacheHit=false 전원) + SERIAL 실행 기록 |
| 3 | 학생 영상 File API 업로드가 분석당 1회, 핸들 일괄 delete 누수 0 (SPD-02/D-04) | ✓ VERIFIED | `gemini/file_session.py`(303줄) GeminiFileSession + per-path in-flight dedupe + close() 일괄 delete. 소비처 4곳 배선(scene_finder 3, moment_extractor 7, coach_writer_v2 4곳 preuploaded_handle 참조) + still PNG inline(`Part.from_bytes`:902). 게이트 로그: 업로드/삭제 24/24 균형, prefetch 13/13. 테스트 43건 green |
| 4 | 단일 분석 내부 병렬화 + 분석 간 SERIAL 불변 (SPD-03/D-03) | ✓ VERIFIED | seam 리팩터 `_download_analysis_video`(:1356)+`_extract_video_analysis_inputs_from_local`(:1385) 실존, prefetch submit 마커(:3428)가 포즈 추출 이전. executor 전부 분석-로컬(모듈 전역 0 — grep 확인: app.py :3397/:3924, vision_scorer :1754 모두 함수 스코프). coach B∥Cerebras 동시화(:3922-3934) |
| 5 | fail-closed·집계 순서 결정론 보존 | ✓ VERIFIED | fan-out 인덱스 순 join(`for idx, fut in enumerate(futures)`:1758, as_completed 미사용), budget 이탈 시 cancel_futures(:1779, WR-01 fix). test_vision_fanout_parallel.py green. 게이트: completedCalls 4/4 전원, 429 실검출 0. cold/warm 결정론 = 병렬화 귀속 위반 0 (유일 divergence는 phase 8 pre-existing — 하단 Deferred) |
| 6 | fault_zoom 사후 분리 — 점수 먼저 complete, zoom pending→done/failed 부분 업데이트 (SPD-04/D-06) | ✓ VERIFIED | models.py FAULT_ZOOM_STATUS_*(:371-374) + firestore_admin.update_analysis_fault_zoom(:1026) + _process 배선(:3046/:3056, done/failed 양경로) + analysis.ts faultZoomStatus?(:538) + contract.md §4(:293-312) 3-way lockstep. test_fault_zoom_deferred.py green |
| 7 | 앱 대기 경험 — zoom placeholder + 시간 상한 폴백 + 팁 로테이터 + 진행률 재배분 (SPD-05/D-02/D-07) | ✓ VERIFIED (실기기 체감은 human) | result.tsx FAULT_ZOOM_PENDING_TIMEOUT_MS=180_000(:79) + pending 판정(:992-1002), DeductionDetailSheet zoomPending 분기(:123), loading.tsx POLE_TIPS 12개(:63) + Math.max 단조 무변경(:439). `tsc --noEmit` PASS |
| 8 | Pro→Flash 조건부 전환 판정 박제 + 캐시 오염 0 (SPD-07/D-05) | ✓ VERIFIED | 27-FLASH-DECISION.md(100줄) — 12멤버 record diff 0으로 게이트 통과, veto Pro 유지 기계 증빙(httpx 62/25콜), 공유 env 제약 발견 → 전용 키 `GEMINI_MOMENT_MODEL`(gemini_moment_extractor.py:62, 커밋 87a9326)로 27-09에서 반영. Pod live environ 6종 검증 기록 |

**Score:** 8/8 truths verified

### Deferred Items

회귀 아닌 pre-existing/범위 밖 발견 — deferred-items.md에 박제됨.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | TechniqueCache hit 시 hold_window 미복원 → warm-path extension 측정 창 drift | gap-closure 회부 (deferred-items.md #1) | pre-existing 코드 확인: `gemini_technique_recognizer.py` `_profile_from_cache`(:383-392)가 TechniqueProfile 생성 시 hold_window 미전달 — fresh 경로(:329)만 설정. 마지막 실질 수정 fc3b6b7(phase 8). 수정은 채점 표면 변경 → 자체 EVAL 게이트 동반 필수라는 판단 타당 |
| 2 | Pod S3 다운로드 일시 변동 (성공 멤버 4건 64.6~135.8s) | 관측 항목 (deferred-items.md #2) | after cold run 한정, warm/before 정상 + 재시도 로그 0 — 네트워크 변동 판정 합리적. TTFR 표에 원인 병기됨 |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/functions/pipeline/app.py` | _stage 계측 + 세션 배선 + seam + prefetch + coach 동시화 + zoom 사후 | ✓ VERIFIED | stage_timing 4hit, GeminiFileSession :3364, session.close() :3491/:4582(이중 경로), seam 함수 2개, prefetch :3397-3428 |
| `backend/shared/python/sunity_shared/gemini/file_session.py` | GeminiFileSession (min 80줄) | ✓ VERIFIED | 303줄, get_or_upload/close/__exit__/_inflight 전부 실존 |
| `backend/shared/python/sunity_shared/gemini/client.py` | preuploaded_handle 주입 | ✓ VERIFIED | call(video_path, *, preuploaded_handle=None) :167, skip 분기 :217-219 |
| `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py` | still inline + fan-out 병렬(인덱스 순 join) | ✓ VERIFIED | Part.from_bytes :902, GEMINI_FANOUT_WORKERS :1728, 인덱스 순 join :1758 |
| `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py` | 핸들 주입 + self-upload finally delete + GEMINI_MOMENT_MODEL | ✓ VERIFIED | preuploaded_handle 7hit, GEMINI_MOMENT_MODEL :62 |
| `backend/shared/python/sunity_shared/models.py` | FAULT_ZOOM_STATUS_* 상수 | ✓ VERIFIED | :371-374, PIPELINE_SEQUENCE 비추가 확인 |
| `backend/shared/python/sunity_shared/firestore_admin.py` | update_analysis_fault_zoom | ✓ VERIFIED | :1026, pipeline 소비 :3046/:3056 |
| `app/src/types/analysis.ts` | timingsMs? + faultZoomStatus? lockstep | ✓ VERIFIED | :520/:538, contract.md 상호 인용 주석 |
| `docs/contract.md` | timingsMs 절 + faultZoomStatus 절 | ✓ VERIFIED | :275-312, 3-way lockstep 명시 |
| `app/src/app/analysis/result.tsx` | zoom pending placeholder + 시간 상한 | ✓ VERIFIED | faultZoomStatus 판정 + 180s 상수, DeductionDetailSheet에 zoomPending 전달(구조 편차 — 하단 Deviations) |
| `app/src/app/analysis/loading.tsx` | POLE_TIPS + 진행률 재배분 | ✓ VERIFIED | POLE_TIPS 12개, Math.max 단조 로직 무변경 |
| 테스트 6파일 (stage_timing/fake_genai/file_session/session_wiring/fanout/fault_zoom) | min_lines 충족 + green | ✓ VERIFIED | 223/140/341/328/207/345줄 — 전부 min_lines 상회. **43/43 passed (직접 실행)** |
| `.planning/.../27-TIMING-BEFORE.md` | cold baseline (min 30줄) | ✓ VERIFIED | 122줄, cacheHit=false 증빙 + Pod/커밋 해시 + env 스냅샷 |
| `.planning/.../27-TIMING-AFTER.md` | 게이트 판정 증빙 (min 40줄) | ✓ VERIFIED | 235줄, canary/rollback 선기록 + 두-지표 분리 표 + 결정론 절 |
| `.planning/.../27-FLASH-DECISION.md` | 채택/기각 판정 (min 20줄) | ✓ VERIFIED | 100줄, 판정 표 + 기계 증빙 + 반영 제약 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| pipeline app.py | firestore complete_analysis | result['timingsMs'] flat dict | ✓ WIRED | _stage 계측 → result 부착, contract 주석 :112 |
| pipeline app.py | gemini/file_session.py | _process 세션 생성 → outer finally close() | ✓ WIRED | :3364 생성, :3491(조기 raise 경로)+:4582(outer finally) 이중 close |
| client.py | file_session 핸들 | preuploaded_handle 주입 시 업로드/폴링/delete skip | ✓ WIRED | :217-219 |
| pipeline app.py | _extract_video_analysis_inputs_from_local | 다운로드 직후 prefetch submit → 포즈 추출 | ✓ WIRED | :3406(submit) → :3432(from_local), 게이트 로그 13/13 순서 확인 |
| vision_scorer | per_call 집계 | call_plan 인덱스 순 join | ✓ WIRED | :1758 `for idx, fut in enumerate(futures)` |
| pipeline app.py | update_analysis_fault_zoom | complete 이후 같은 BackgroundTask에서 렌더 → 부분 update | ✓ WIRED | :3029-3056 |
| result.tsx | analysis.ts faultZoomStatus | onSnapshot 구독, 추가 폴링 0 | ✓ WIRED | setTimeout(상한 폴백)만 — setInterval 폴링 0 확인 |
| loading.tsx | PROGRESS_PCT 단조 로직 | 값만 재배분, Math.max 무변경 | ✓ WIRED | :439 |
| 27-TIMING-AFTER | 27-TIMING-BEFORE | 동일 페어·동일 단계 키(timingsMs) 대조 | ✓ WIRED | §3 표 — 동일 runId 참조 체계 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 27 신규 테스트 5파일 | `pytest tests/test_stage_timing.py tests/gemini/test_file_session.py tests/gemini/test_session_wiring.py tests/test_vision_fanout_parallel.py tests/test_fault_zoom_deferred.py` | 43 passed | ✓ PASS |
| 마이그레이션 파이프라인 테스트 4파일 | `pytest tests/test_pipeline_gemini_integration.py tests/pipeline/test_pipeline_phase8.py tests/pipeline/test_pipeline_phase9.py tests/test_pipeline_geminic_wiring.py` | 28 passed / 6 failed | ⚠️ 6건 실패는 **pre-existing** (하단 Anti-Patterns) |
| 앱 타입 게이트 | `npm run typecheck` (tsc --noEmit) | 오류 0 | ✓ PASS |
| 리뷰 fix 커밋 6건 실존 | `git log` 57ca9fd/ab713b7/b925156/26d1e27/38cf52c/1e013a9 | 전부 실존 + 코드 실물 대조 일치 | ✓ PASS |
| Pod 실측 (sweep) | — | 재실행 불가(Pod/크레딧) — 27-TIMING-AFTER 문서 증빙 + 코드 정합으로 판정 | ? SKIP |

### Probe Execution

해당 없음 — 이 프로젝트는 `scripts/*/tests/probe-*.sh` 관례 부재, PLAN/SUMMARY에 probe 선언 0. 게이트는 EVAL18 Pod sweep(위 SKIP 항목)으로 수행됨.

### Requirements Coverage

**주의:** SPD-01~07은 REQUIREMENTS.md에 등재되어 있지 않다 — ROADMAP.md :901에 명시된 대로 플래너가 phase goal에서 mint(2026-07-07)한 ID다. ORPHANED 아님 (ROADMAP이 정의 출처).

| Requirement | Source Plan | Description (ROADMAP mint) | Status | Evidence |
|-------------|------------|---------------------------|--------|----------|
| SPD-01 | 27-01, 27-02 | stage-timing 계측 + timingsMs + cold baseline | ✓ SATISFIED | _stage 계측 + 계약 lockstep + 27-TIMING-BEFORE.md |
| SPD-02 | 27-03, 27-04 | File API 라운드트립 축소 (핸들 세션 1회 + inline + 누수 0) | ✓ SATISFIED | file_session.py + 소비처 4곳 + 게이트 24/24 균형 |
| SPD-03 | 27-05 | 단일 분석 내부 병렬화 (SERIAL·fail-closed·결정론 불변) | ✓ SATISFIED | seam + prefetch + fan-out + coach 동시화 (moment extractor prefetch는 문서화된 범위 축소 — 하단) |
| SPD-04 | 27-06, 27-07 | fault_zoom 사후 분리 + 3-way lockstep + 앱 placeholder | ✓ SATISFIED | 계약 3-way + persistence + 앱 소비 전부 실물 확인 |
| SPD-05 | 27-05, 27-07 | 대기 경험 (status 시점 교정 + 진행률 재배분 + 팁 로테이션) | ✓ SATISFIED | 코드 실물 확인 (체감 판정은 human 항목) |
| SPD-06 | 27-02, 27-09 | 정확도 무회귀 게이트 (EVAL18 cold 대조 + 결정론 + before/after 표) | ✓ SATISFIED | D-01 PASS 증빙 (27-TIMING-AFTER §2) |
| SPD-07 | 27-08 | Pro→Flash 조건부 전환 (동일 시만 채택) | ✓ SATISFIED | diff 0 게이트 통과 + 전용 키 반영 (27-09) |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/tests/test_pipeline_geminic_wiring.py` | 207 등 6개 테스트 | `monkeypatch.setattr(pipeline_app, "find_scene_flags", ...)` — 모듈 속성 부재로 6건 실패 | ⚠️ Warning (**pre-existing, phase 27 무관**) | phase 27 이전 커밋 910a568에서도 동일 6건 실패 재현(worktree 검증). 원인 = phase 17 배포 fix `fe8579f`가 find_scene_flags를 lazy import로 전환 — 그 시점부터 깨진 테스트 부채. 27-05가 이 파일을 수정(seam 마이그레이션 — 해당 부분은 green)했으나 pre-existing 실패는 미수선. 후속 정리 권장 (fix-now 원칙상 다음 quick/phase에서) |
| `backend/evals/phase25/run_sweep.py` | 95-110 | GEMINI_FANOUT_WORKERS / STUDENT_FRAME_CACHE setdefault 미러 부재 (PREFETCH/MOMENT_MODEL만 존재) | ℹ️ Info | 코드 default(4/RunPod ON)가 프로덕션 박제값과 동일해 sweep 동작 차이 0. A/B 재현 편의만 감소 |
| `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py` | 62 | 최종 fallback 모델 `gemini-2.5-pro` (2.5 금지 규칙 충돌) | ℹ️ Info | 27-REVIEW IN-03 skipped — 의도된 vision-only 예외(파일 주석 근거) + belle 결정 대기 문서화. 운영 레버는 GEMINI_MOMENT_MODEL env |
| 디버깅 마커 (TBD/FIXME/XXX) | — | phase 27 수정 파일 14개 전량 스캔 | 없음 | 0건 |

### Review Fix Verification (27-REVIEW 2 Critical + 4 Warning)

SUMMARY 주장이 아닌 코드 실물로 대조 — 전부 실존:

| Finding | Claimed fix | Code evidence | Status |
|---------|------------|---------------|--------|
| CR-01 (세션 업로드 비-APIError 전파 → 분석 사망) | 57ca9fd | file_session.py :160/:182 broad except graceful None + 폴링-실패 orphan delete(:192) | ✓ 실존 |
| CR-02 (self-upload 부분 실패 orphan) | ab713b7 | vision_scorer.py :1340/:1342 — 업로드 성공 즉시 개별 append | ✓ 실존 |
| WR-01 (fan-out budget soft bound) | b925156 | vision_scorer.py :1779 `pool.shutdown(wait=joined_all, cancel_futures=not joined_all)` | ✓ 실존 |
| WR-02 (unlink-while-upload 레이스) | 26d1e27 | app.py :1392 `unlink_on_error` kwarg + :3440 `(executor is None)` 게이트 | ✓ 실존 |
| WR-03 (ref temp 누수) | 38cf52c | app.py :3741 `_safe_unlink_local_video(ref_tmp.name)` | ✓ 실존 |
| WR-04 (errorCode 키 불일치) | 1e013a9 | run_sweep.py :262-271 `d.get("error")` → code 추출 | ✓ 실존 |

IN-01~05 skipped는 각각 사유 문서화(trivial 기준 초과 / belle 결정 대기) — 상태 표기 정확.

### Deviations Assessed (숨김 아닌 판정)

1. **27-05 범위 축소 — moment extractor·기준영상 prefetch 미구현.** plan must_have truth("업로드 prefetch·scene_finder·**moment extractor**가 겹쳐 실행")의 moment extractor 부분 미충족. 코드 주석(app.py :3392-3394)과 SUMMARY key-decisions에 근거 박제: recognize()는 angles 의존 + moment 주입은 채점 코어(technique.py) 수정 필요 → 위험 관리상 제외. **phase goal 훼손 아님으로 판정** — recognizer 단계는 세션 핸들+Flash로 median 35.5s→5.8s(−84%) 달성, 전체 TTFR −46%로 "가능한 범위 최대 절감" 스펙 충족. 잔여 레버(coach_dual 30.7s)는 27-TIMING-AFTER에 후속 후보로 기재.
2. **27-07 구조 편차 — zoom placeholder 렌더 위치.** plan은 result.tsx 확대카드 자리를 지정했으나 실제 zoom 소비처가 DeductionDetailSheet라서 placeholder를 시트에, 판정/폴백을 result.tsx에 배치. 의도(D-06 소비) 충족 — 수용.
3. **27-08 "채택 + 반영 보류" 경로.** plan의 "채택 시 즉시 env 반영"과 달리 GEMINI_MODEL 공유 제약 발견 → 전용 키 신설 후 27-09에서 반영 완료. belle 승인 범위(veto 보류) 준수를 위한 올바른 편차 — 수용.

### Human Verification Required

배치 UAT 정책 (즉시 belle 호출 금지 — HUMAN-UAT 적립, 추후 /gsd-audit-uat 일괄):

### 1. zoom pending→done 전이

**Test:** 실기기 mode1 분석 → 결과 화면 — 점수 먼저 표시, 확대비교 placeholder → 이미지 자동 전환
**Expected:** pending 로딩 표시 → onSnapshot 도착 시 전환, 180s 초과 시 숨김 폴백 (무한 로딩 0)
**Why human:** Firestore 부분 업데이트의 실기기 rerender 타이밍은 정적 분석 불가

### 2. 팁 로테이션

**Test:** 분석 대기 화면에서 폴스포츠 팁 로테이션(12개, 6s 주기) 관찰
**Expected:** 팁 교체 표시, 기존 카피 로테이터(4s)와 동시 점프 없음
**Why human:** 타이머 기반 시각 동작

### 3. 진행률 전진

**Test:** 분석 대기 내내 진행률 관찰 (comparison base 40→상한 97 재배분)
**Expected:** 85% 얼어붙음 없이 단조 전진, 역행 0
**Why human:** 대기 체감(D-02)은 실분석 실기기 판정만 유효

### Gaps Summary

**가로막는 gap 0.** phase goal의 hard gate(점수·verdict 무회귀)는 EVAL18 12멤버 record 레벨 대조로 PASS했고, 시간 레버 3종(a/b/c)은 전부 코드 실물 + 실측 증빙으로 확인됐다. TTFR median 124.7s(정규화 104s)는 1분 지향점에 미달하나, 27-09-PLAN·belle 원문 D-01이 명시한 대로 시간은 "가능한 범위 최대 절감"이 목표치이며 보고 항목이다 — 감축 −46%, Gemini vision 그룹 −78%로 계획 수확 달성. 리뷰 Critical 2건·Warning 4건 fix는 전부 커밋+코드 실물로 검증됐다. 검증 중 발견한 test_pipeline_geminic_wiring.py 6건 실패는 phase 27 이전 커밋(910a568)에서 동일 재현되는 phase 17 유래 pre-existing 테스트 부채로 확정(회귀 아님) — 후속 정리 권장. warm-path hold_window 버그는 pre-existing으로 코드 확인 완료, deferred-items.md 회부 타당. 남은 것은 실기기 체감 3항목뿐 — 배치 UAT 정책에 따라 적립.

---

_Verified: 2026-07-08T12:20:00Z_
_Verifier: Claude (gsd-verifier)_
