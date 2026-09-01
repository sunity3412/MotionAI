---
phase: quick-260901-wbo
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/contract.md
  - backend/shared/python/sunity_shared/models.py
  - backend/shared/python/sunity_shared/firestore_admin.py
  - backend/functions/pipeline/app.py
  - backend/tests/quick_260901_wbo/test_coach_text_contract.py
  - backend/tests/quick_260901_wbo/test_coach_text_deferred.py
  - app/src/types/analysis.ts
  - app/src/app/analysis/result.tsx
  - app/src/app/analysis/loading.tsx
autonomous: true
requirements: [quick-260901-wbo]
must_haves:
  truths:
    - "로딩 화면은 코칭 문장 생성을 기다리지 않는다 — status 'done' 이 coach_dual(43s)+hook(~14s) 이전에 도착"
    - "신 doc(coachStatus='pending')은 결과 화면 코칭 섹션에 '작성 중' placeholder 를 보이고, 부분 갱신 도착 시 onSnapshot 으로 자동 채움"
    - "coachStatus 없는 구 doc 은 지금처럼 코칭 즉시 표시 (렌더 무회귀)"
    - "구 앱(1.2.2)이 신 doc 을 봐도 크래시 없음 — tips 필수 필드는 complete 시점에 수치 폴백으로 채워져 있고 코칭 텍스트만 늦게 승격"
    - "사후 코치 스테이지 실패 시에도 분석 done 유지 + tips 수치 폴백 잔존 (최후 바닥 불변)"
    - "진행률이 comparison 에서 2분 기어오르지 않는다 — 새 실측 기대치로 재배분"
  artifacts:
    - path: "backend/shared/python/sunity_shared/models.py"
      provides: "COACH_STATUS_PENDING/DONE/FAILED + COACH_STATUSES (FAULT_ZOOM_STATUSES 미러)"
      contains: "COACH_STATUSES"
    - path: "backend/shared/python/sunity_shared/firestore_admin.py"
      provides: "update_analysis_coach_text 사후 부분 갱신 (field-path .update())"
      contains: "def update_analysis_coach_text"
    - path: "backend/functions/pipeline/app.py"
      provides: "_run_deferred_coach_text 사후 스테이지 (complete 뒤, coach_audio 앞)"
      contains: "def _run_deferred_coach_text"
    - path: "docs/contract.md"
      provides: "coachStatus 계약 절 (faultZoomStatus 절 미러)"
      contains: "coachStatus"
    - path: "app/src/types/analysis.ts"
      provides: "AnalysisResult.coachStatus? TS 미러"
      contains: "coachStatus?:"
    - path: "app/src/app/analysis/result.tsx"
      provides: "coachPending placeholder + 타임아웃 상한"
      contains: "COACH_PENDING_TIMEOUT_MS"
    - path: "app/src/app/analysis/loading.tsx"
      provides: "재보정된 PROGRESS_PCT/PROGRESS_CEIL"
  key_links:
    - from: "backend/functions/pipeline/app.py"
      to: "result.coachStatus"
      via: "complete_analysis 직전 result['coachStatus']='pending' 마커 (faultZoomStatus 마커 선례, app.py:7916)"
      pattern: "coachStatus"
    - from: "backend/functions/pipeline/app.py::_run_deferred_coach_text"
      to: "firestore_admin.update_analysis_coach_text"
      via: "사후 부분 갱신 (result.tips / result.coachStatus / result.forcePatternInference.coachCommentHook / result.bodyComparisonReport.coachCommentHook / geminiB)"
      pattern: "update_analysis_coach_text"
    - from: "app/src/app/analysis/result.tsx"
      to: "result.coachStatus"
      via: "useAnalysisDoc onSnapshot (구독 이미 존재 — 폴링 금지)"
      pattern: "coachStatus === 'pending'"
---

<objective>
분석 로딩 단축 (belle 2026-09-01 승인: "로딩 단축도 진행해줘 코칭 문장 뒤로 빼는거 포함").
coach_dual(실측 43.1s) + coach hook Gemini 콜(~14s 미계측)을 complete_analysis 사후
스테이지로 이동해 status 'done' 도착을 ~57s 앞당긴다. Phase 27 D-06 fault_zoom
사후화가 승인 선례이며 그 패턴(pending 마커 + 부분 갱신 + 앱 placeholder)을 그대로
미러한다.

Purpose: 로딩 체감 2분 10초 → 약 1분 초반 (timingsMs 91.7s 중 coach 43.1s + hook ~14s 제거).
Output: 계약 3중 미러(coachStatus) + update_analysis_coach_text + _run_deferred_coach_text
스테이지 + 앱 placeholder + 진행률 재보정.
</objective>

<context>

## coach 산출 필드 전수 지도 (설계 3번 — 이 표가 부분 갱신 payload 스펙)

코드 전수 확인 결과 (app.py 7280~7460 coach_dual 블록, 7740~7800 hook 블록,
assemble.py build_result/build_tips/rebuild_tips_for_vision_fault, firestore_admin.py
complete_analysis kwarg 매핑):

**이동 대상 (coach_dual + hook 산출) — 5개 필드:**

| # | doc 필드 | 산출자 | 저장 위치 | 사후 갱신 field-path |
|---|---------|--------|----------|---------------------|
| 1 | tips[].detail | coach_dual (Gemini 우선, Cerebras 폴백 — assemble_dual_coach_sections) | result.tips (build_result 내) | result.tips 통째 교체 |
| 2 | tips[].detail2 (causes[].title/explanation=Gemini, causes[].fix/injuryRisk=Cerebras, coachNote=Gemini) | coach_dual 섹션 조립 (13-C) | result.tips | result.tips 통째 교체 |
| 3 | geminiB (audit: dualTrack/sectionAudit/crossFilledJoints/model/latencyMs/fallback) | _gemini_b_audit_payload | **top-level** geminiB (complete kwarg) | geminiB |
| 4 | forcePatternInference.coachCommentHook | hook Gemini 콜 (GeminiCoachHookWriter.build_coach_hooks) | result.forcePatternInference (complete kwarg) | result.forcePatternInference.coachCommentHook |
| 5 | bodyComparisonReport.coachCommentHook | hook Gemini 콜 (동일 번들) | result.bodyComparisonReport (complete kwarg) | result.bodyComparisonReport.coachCommentHook |

**무이동 (coach_dual 산출 아님 — 결정론 생성, 동기 경로 잔류):**

| doc 필드 | 실제 산출자 |
|---------|-----------|
| tips[].joint / tips[].title | kismam.top_issues + COACHING_FOCUS (결정론) |
| deductionBreakdown.records[].cueLine/statusLine/whyLine/actionLine | 32-09 `_attach_translation_emission` 문구집 (승인 문구, "문구 변경 금지") — **coach_dual 산출 아님** |
| summaryPraise / mission / missionOutcome / coachQuestions | `_attach_translation_emission` (결정론 수집) |
| dimensionExplanation | assemble.build_dimension_explanation (결정론 — Phase 12.5) |
| coachAudio | records[].cueLine 의 Polly TTS — **coach_dual 무의존** (아래 판정 참조) |

**record 문구 출처 판정 (설계 3번 요구):** records[].cueLine 등 감점 record 문구는
32-05 승인 문구집에서 결정론 생성되며 coach_dual 산출이 **아니다**. 따라서 이동 범위
재판단 불필요 — 승인 범위(coach_dual + hook 만 이동) 그대로 유효하다.
**설계 전제 정정 1건:** coach_audio 는 cueLine(문구집)을 TTS 하므로 실제로는 coach_dual
에 의존하지 않는다. 다만 승인된 사후 순서(coach_text → coach_audio → fault_zoom →
spot_check → compare_render)는 그대로 유지한다 — 순서 유지 비용 0, 승인 원문 존중.

**사후 스테이지 소비처 검사 ([[partial-field-writes-invisible-to-inmemory-doc]] 함정):**
- coach_audio: deductionBreakdown.records[].cueLine 만 읽음 (app.py:4152~4160) — tips/hook 무소비
- fault_zoom: records/keypoints — tips/hook 무소비
- spot_check: statusLine/cueLine + summaryPraise.headline (app.py:5138, 5269) — tips/hook 무소비
- compare_render: coach_audio_items + fault_zoom_items — tips/hook 무소비
- `_apply_score_suppression`(mode3): tips 무접촉 (grep 확인)
→ 현재 소비처 0. 그래도 회귀 갑주로 사후 스테이지가 in-memory result 도 동기 갱신한다 (Task 2).

**동기 경로의 coach_details 소비처 (이동 시 함께 처리):**
- assemble.build_result(coach_details=) → tips 분기 (app.py:7440대)
- assemble.rebuild_tips_for_vision_fault(result, assessments, coach_details) (app.py:7599 — veto applied 시 표시 재조립)
- _gemini_b_audit_payload → complete kwarg gemini_b (app.py:8073)

## 선례 파일 (미러 대상)

- 계약: docs/contract.md:485~505 faultZoomStatus 절 / models.py:631~650 FAULT_ZOOM_STATUSES / analysis.ts:920~928
- 부분 갱신: firestore_admin.update_analysis_fault_zoom(:1389) + update_analysis_coach_audio(:1495) — field-path `.update()`, merge 금지 사유 주석 포함
- 사후 스테이지 뼈대: app.py `_run_deferred_coach_audio`(:4122) / `_run_deferred_fault_zoom`(:3981) — 어떤 경로도 재raise 0
- pending 마커: app.py:7916 `result["faultZoomStatus"] = FAULT_ZOOM_STATUS_PENDING` (complete 직전 result 에 실림)
- 앱 placeholder: result.tsx:125~135 FAULT_ZOOM_PENDING_TIMEOUT_MS(180_000) + :1582~1610 zoomPending effect
- 테스트: backend/tests/test_fault_zoom_deferred.py, backend/tests/phase32/test_coach_audio.py (mock Firestore 선례)

## 배포 시퀀스 (verification_requirements 명시 요구)

- 백엔드: 지금 배포 활성 없음 — Pod 는 **다음 기동 때 git pull** 로 이 코드를 받는다. Lambda 경로는 CPU 폴백(흐름 검증용)이라 실사용 무영향.
- 앱: 다음 빌드(1.2.2+)에 실린다. 순수 TS 변경이지만 OTA 는 현재 금지 상태(네이티브 모듈 건) — 빌드 채널로만.
- 호환 매트릭스: 구 앱 + 신 doc = tips 수치 폴백 즉시 표시 → 몇십 초 뒤 코칭 텍스트로 자동 승격 (크래시 0, 허용됨) / 신 앱 + 구 doc = coachStatus 부재 → placeholder 게이트 자연 false → 즉시 표시 (무회귀).

## 범위 제외 (hard constraints)

- 채점/veto/게이트 로직 무접촉 (코칭은 표시 텍스트) / compare_render·spot_check·fault_zoom 내부 무수정 (순서상 뒤로 밀릴 뿐)
- 사후 스테이지 GPU 경합 분리(별도 태스크/큐) — 다음 태스크
- not_pole_motion 등 실패 게이트는 coach 이전에 결정 — 무접촉. mode1·mode3 동일 적용.
- kill-switch env 신설 안 함 — fault_zoom D-06 선례도 무스위치 (단일 코드 경로 유지)
</context>

<tasks>

<task type="auto">
  <name>Task 1: 계약 3중 미러 (coachStatus) + update_analysis_coach_text 신설</name>
  <files>docs/contract.md, backend/shared/python/sunity_shared/models.py, backend/shared/python/sunity_shared/firestore_admin.py, app/src/types/analysis.ts, backend/tests/quick_260901_wbo/test_coach_text_contract.py</files>
  <action>
계약 3중 미러 동시 수정 (하나만 고치면 반려 — hard constraint).

(1) models.py — FAULT_ZOOM_STATUSES 블록(:631~650) 바로 아래에 미러 블록 신설:
COACH_STATUS_PENDING/DONE/FAILED = "pending"/"done"/"failed" + COACH_STATUSES 튜플.
주석은 fault_zoom 블록 서술 모범 그대로: 코칭 문장은 점수가 아닌 표현물, complete
이후 부분 갱신 도착, PIPELINE_SEQUENCE/status enum 추가 영구 금지, 부재(legacy doc)=
즉시 표시 하위호환, 3-way lockstep 위치 명기.

(2) firestore_admin.py — update_analysis_coach_audio 아래에 update_analysis_coach_text
신설 (fault_zoom/coach_audio 뼈대 복제, field-path `.update()` — merge 의 배열 병합
모호성 회피 사유 주석 포함). 시그니처: (uid, analysis_id, *, status, tips=None,
force_hook=None, body_hook=None, gemini_b=None). 동작:
  - status 는 COACH_STATUSES 강제 (밖이면 ValueError). pending 마커는 complete 시
    result 에 실려 저장되므로 본 함수는 done/failed 전이만 쓴다 (fault_zoom 서술 미러).
  - update payload: "result.coachStatus"=status + "updatedAt" 필수. tips 가 None 아니면
    "result.tips" 통째 교체. force_hook/body_hook 이 None 아니면 각각
    "result.forcePatternInference.coachCommentHook" / "result.bodyComparisonReport.coachCommentHook"
    field-path. gemini_b 가 None 아니면 top-level "geminiB".
  - 검증: 신설 _validate_coach_tips (list[dict]; 각 tip 키 화이트리스트 joint/title/detail/
    detail2, title/detail 비어있지 않은 str, joint 는 str|None, detail2 는 dict 면
    causes(list[dict-of-scalars], _validate_dict_only_scalars 라우팅 — validator 본체
    무수정, safetyFlags 선례) + injuryRisk?/coachNote scalar str). hook 은 기존
    _validate_coach_comment_hook 재사용, gemini_b 는 기존 _validate_flat_dict_no_nested_array
    재사용. status='failed' 시 tips/hook/gemini_b 는 선택(부재 허용 — 최후 바닥 유지,
    coach_audio failed-마킹 선례). Firestore nested-array 금지 준수 — tips[].detail2.causes
    는 array→map→map→array 라 합법 (complete_analysis 가 오늘도 같은 형상 저장).

(3) docs/contract.md — §4 faultZoomStatus 절 뒤에 coachStatus 절 신설 (동일 골격):
'pending'|'done'|'failed' optional. 의미: pending=코칭 작성 중(앱은 코칭 섹션
placeholder, 그동안 tips 는 수치 폴백으로 이미 유효) / done=코칭 텍스트 도착
(result.tips 승격 + coachCommentHook Gemini 승격) / failed=수치 폴백 잔존(placeholder
해제). 부재=사후 분리 이전 legacy doc — 즉시 표시, no migration. 사후 변경 경계:
coach_text 스테이지의 write 는 result.tips + result.coachStatus +
result.forcePatternInference.coachCommentHook + result.bodyComparisonReport.coachCommentHook
+ top-level geminiB 뿐 — 점수/verdict/감점 tally(deductionBreakdown)/records 문구 무접촉
(D-03 경계, 문구집 문장은 표현·오디오·spot_check 의 단일 원천이라 사후 변경 영구 금지).
Python 정본 = models.COACH_STATUSES + firestore_admin.update_analysis_coach_text, lockstep
= analysis.ts AnalysisResult.coachStatus?.

(4) analysis.ts — faultZoomStatus?(:928) 인접에 coachStatus?: 'pending' | 'done' | 'failed'
추가. 주석은 faultZoomStatus 주석 미러 (Python lockstep 위치 + 부재=legacy 즉시 표시 +
tips 는 pending 동안에도 수치 폴백으로 항상 유효 — required 필드 불변).

(5) 단위 테스트 backend/tests/quick_260901_wbo/test_coach_text_contract.py (mock
Firestore — test_fault_zoom_deferred.py 의 _doc patch 선례): status enum 강제 /
done+tips → result.tips·result.coachStatus·updatedAt field-path 검증 / hook·geminiB
조건부 포함 / failed 는 tips 없이 coachStatus 만 / _validate_coach_tips 위반 형상
(nested array in causes, 빈 detail, 여분 키) TypeError·ValueError.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests/quick_260901_wbo/test_coach_text_contract.py -q && cd /Users/kimtaesung/Dev/SunityMotion/app && npx tsc --noEmit</automated>
  </verify>
  <done>계약 3파일(contract.md + models.py + analysis.ts) 동시 반영, update_analysis_coach_text 가 field-path 부분 갱신으로 표의 5개 필드만 쓰며 신규 테스트 전부 통과, tsc 0 에러.</done>
</task>

<task type="auto">
  <name>Task 2: coach_dual + hook 을 _run_deferred_coach_text 사후 스테이지로 이동</name>
  <files>backend/functions/pipeline/app.py, backend/tests/quick_260901_wbo/test_coach_text_deferred.py</files>
  <action>
app.py _process 수술 — 로직 무수정 이동 (설계 6번: coach_dual 내부 구조는 이동만).

(1) 동기 경로에서 coach 블록 제거: 7360~7437 의 dual-track/Cerebras-only 블록
(ThreadPoolExecutor + _call_coach_writer_with_retry + assemble_dual_coach_sections +
_gemini_b_audit_payload)을 들어내고 그 자리에 coach_details = {} 고정 + 주석
(quick-260901-wbo — 코칭 작성은 complete 이후 _run_deferred_coach_text, 여기서는
수치 폴백 조립만). build_result·rebuild_tips_for_vision_fault(:7599) 호출은 그대로
둔다 — coach_details={} 면 build_tips 수치 폴백/rebuild 는 자연 no-op (visible_details
빈 dict 조기 반환, 코드 확인 완료).

(2) hook 블록(7740~7800)에서 Gemini 콜 제거: GeminiCoachHookWriter().build_coach_hooks
+ resolve_coach_hook_bundle 호출을 들어내고 build_canned_hook 2콜(force/body — 기존
except 폴백 경로와 동일 코드)로 대체 — complete 시점에 hook 필드는 canned 로 항상
존재 (구 앱 하위호환 + "분석 절대 실패 안 함" 불변식 보존). _force_findings /
_body_findings 리스트는 deferred 스테이지 전달용으로 로컬에 유지.

(3) pending 마커: result["timingsMs"] = timings_ms (:8057) 직전에
result["coachStatus"] = models.COACH_STATUS_PENDING (faultZoomStatus 마커 :7916 선례,
mode1·mode3 무조건 — coach 블록은 모든 complete 도달 분석에서 돌던 경로). complete_analysis
호출의 gemini_b kwarg 는 None 으로 (audit 은 사후 갱신으로 이동).

(4) _run_deferred_coach_text 신설 (_run_deferred_coach_audio :4122 뼈대 복제 — 어떤
경로도 재raise 0). 시그니처(전부 kw-only): result, assessments, coach_context,
force_findings, body_findings, uid, analysis_id, timings_ms. 본체:
  - _stage(timings_ms, analysis_id, "coach_dual") 안에서 기존 블록 그대로: _coach_enabled()
    분기 + Gemini 스레드 ∥ Cerebras + 재시도 + 섹션 조립 + gemini_b_audit 조립
    (dualTrack/sectionAudit/crossFilledJoints 포함). Cerebras 폴백 관계 무수정.
  - _stage(timings_ms, analysis_id, "coach_hook") 안에서 hook Gemini 콜 + resolve
    (설계 2번 — hook 별도 계측 신설. force_findings 또는 body_findings 가 있을 때만.
    실패 시 canned 유지 = hook field-path 미전송). timingsMs 는 이미 저장됨 — 사후
    계측은 스테이지 로그 라인으로만 (fault_zoom 관례).
  - tips 재조립 (in-memory 최종 result 위에서, 오늘의 동기 산출과 동일 결과 보장):
    현재 result["tips"] 가 일반 팁 단독(len 1 + joint None — angle>=95 분기)이면
    assemble.rebuild_tips_for_vision_fault(result, assessments, coach_details) 로 재조립
    (veto applied·귀속 신뢰 게이트는 함수 내부가 판정 — 게이트 불통과면 tips 불변 =
    오늘과 동일하게 코칭이 tips 에 안 실리는 케이스). 그 외에는
    assemble.build_tips(kismam.top_issues(assessments, n=3), coach_details).
  - 성공: firestore_admin.update_analysis_coach_text(uid, analysis_id,
    status=COACH_STATUS_DONE, tips=재조립분, force_hook=Gemini 성공분|None,
    body_hook=동일, gemini_b=audit). ★검수기 경고 반영 (260901-wbo 체커 warning 1):
    **body_hook field-path 전송은 동기 경로의 attach 조건(app.py:7774 `if
    body_comparison_report is not None`)을 미러해, complete 시점에 doc 에
    bodyComparisonReport 가 실렸을 때만 보낸다. force_hook 도 forcePatternInference
    방출 시에만.** 아니면 `.update()` 가 중간 map 을 새로 만들어 findings 없는 stub
    리포트가 doc 에 박힌다. update_analysis_coach_text 쪽에서도 같은 이유로 hook 값이
    None 이면 해당 field-path 를 payload 에서 생략한다. 테스트 (b′): body 리포트 부재
    doc 케이스 — body_hook field-path 미전송 assert. 그리고 in-memory result 동기 갱신 —
    result["tips"]/result["coachStatus"]/forcePatternInference·bodyComparisonReport 의
    coachCommentHook 교체 ([[partial-field-writes-invisible-to-inmemory-doc]] 회귀 갑주.
    현재 사후 소비처 0 을 코드로 재확인했지만 미래 소비처 방어).
  - 양쪽 writer 실패: status=FAILED + gemini_b=both_failed audit, tips 미전송 (수치
    폴백 잔존 — 오늘의 both-failed 최종 상태와 동일). 스테이지 예외: FAILED 마킹 시도,
    마킹 write 실패는 log.exception 만 (coach_audio failed-마킹 규율 복제).
  - **동기 채점 경로 호출 금지** — 사후 전용 (docstring 에 명기, coach_audio 선례).

(5) 호출부 삽입: complete_analysis 성공 로그(:8064) 및 corrected_pose enqueue 블록 뒤,
coach_audio 스테이지(:8095) **앞** — 승인 사후 순서 coach_text → coach_audio →
fault_zoom → spot_check → compare_render. session.close()/영상 unlink 는 outer finally
라 coach_context 의 preuploadedHandle·local_video_path 는 이 시점 유효 (fault_zoom
주석 선례). RunPod server 는 _process 재사용이라 무수정.

(6) 테스트 backend/tests/quick_260901_wbo/test_coach_text_deferred.py (mock Firestore +
writer mock — verification_requirements 명세): (a) complete payload 에 coachStatus=
'pending' 이 실리고 tips 는 수치 폴백 형상(detail2 부재)이며 gemini_b kwarg None,
(b) 사후 성공 경로가 update_analysis_coach_text 를 전수 표의 필드 전부(tips+status+
force_hook+body_hook+gemini_b)로 호출 + in-memory result 동기 갱신 확인, (c) 일반 팁
단독(angle>=95)+veto applied 케이스에서 rebuild_tips_for_vision_fault 경유 재조립,
(d) 양쪽 writer 실패 → FAILED + tips 미전송, (e) 스테이지 예외 → FAILED 마킹 + 재raise 0,
(b′) bodyComparisonReport 부재 doc → body_hook field-path 미전송 (stub map 생성 금지).
★체커 info 반영: _force_findings/_body_findings 는 조건 블록 앞에 기본값 [] 호이스팅.
기존 스위트에서 coach 동기 산출을 전제한 테스트가 깨지면 전제를 사후 스테이지로
옮겨 수리 (채점 기준선 무접촉 확인 — 점수 asserting 테스트는 깨지면 안 된다).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest tests -q</automated>
  </verify>
  <done>전체 스위트 기준선 4548 passed / 0 failed 유지(신규 테스트 추가분 증가 허용, 실패 0). complete 시점 payload 에 coach 산출 5필드 부재 + coachStatus pending, 사후 갱신에 5필드 전부. 채점·veto·게이트 테스트 diff 0.</done>
</task>

<task type="auto">
  <name>Task 3: 앱 placeholder (coachStatus pending) + 진행률 곡선 재보정</name>
  <files>app/src/app/analysis/result.tsx, app/src/app/analysis/loading.tsx</files>
  <action>
(1) result.tsx — zoomPending 선례(:125~135 상수, :1582~1610 effect) 1:1 미러:
  - const COACH_PENDING_TIMEOUT_MS = 180_000 (근거 주석: 실측 coach_dual 43.1s + hook
    ~14s + writer 재시도 여유. FAULT_ZOOM 상수와 같은 보수 규율 — 정상 pending 조기
    숨김 금지, 무한 pending 고아 방지 T-27-21 미러).
  - coachPendingTimedOut state + effect (updatedAt 기준 잔여 계산, updatedAt 갱신마다
    재무장 — zoom effect 복제, deps 만 result.coachStatus).
  - const coachPending = result.coachStatus === 'pending' && !coachPendingTimedOut.
  - 코칭 팁 섹션(visibleTips 렌더부, :1776 memo 하류) 렌더 분기: coachPending 이면
    tips 카드 리스트 대신 "작성 중" placeholder 카드 1장 (카피 예: "AI 코치가 교정
    문장을 작성하고 있어요" — 한국어, 이모지 금지, theme 토큰만·하드코딩 색 금지,
    zoom placeholder 시각 문법 미러). 상한 초과·failed·부재(legacy)·done 은 전부 기존
    tips 렌더 그대로 — placeholder 만 숨고 섹션은 비지 않는다 (tips 는 required 필드,
    pending 동안에도 수치 폴백이 실려 있음). 도착 시 onSnapshot 재렌더 자동 (구독
    이미 존재 — 신규 폴링 금지 안티패턴).
  - primaryFault 폴백(:1487 tips[0]?.title)은 무접촉 — title 은 결정론 산출이라 pending
    동안에도 최종값과 동일 (전수 표 근거, 주석 1줄).
  - coachCommentHook 소비부(:1639~1651)는 무접촉 — complete 시점에 canned 로 항상
    존재, Gemini 승격은 같은 onSnapshot 으로 텍스트만 교체.

(2) loading.tsx — 값만 재배분, 단조 로직/creep 메커니즘 무변경 (Phase 27 D-02 규율):
  - 새 실측 기대(코칭 43.1s + hook ~14s 가 빠진 뒤): frame_extraction 상태 ≈ s3_download
    3.9 + frame_extract 15.0 ≈ 19s / pose_analysis ≈ rtmw 2s / comparison ≈ scene 11.2 +
    veto 14.7 + 잔여 미계측 ~8 + firestore ~3 ≈ 37~40s. 총 파이프라인 ≈ 60s.
  - PROGRESS_PCT: uploading 8, queued 16, frame_extraction 30, pose_analysis 42,
    comparison 48, done 100, failed 0.
  - PROGRESS_CEIL: uploading 15, queued 28, frame_extraction 40, pose_analysis 47,
    comparison 97, done 100, failed 0.
  - PROGRESS_CREEP_MS: 2500 → 1500 (comparison 기대 ~38s 동안 48→~73 전진, 장영상
    아웃라이어도 97 상한까지 계속 전진 — "comparison 142.5초 기어오름" 제거. 실제
    done 전 100 도달 금지 불변).
  - 블록 주석의 실측 근거를 새 수치로 교체 (구 median 229.6s 서술 → 2026-09-01 실측
    ea975e6e + coach/hook 사후화 반영 서술, quick-260901-wbo 태그).

(3) 시뮬레이터 눈검증: iOS 시뮬레이터에서 앱 기동, 구 doc(코칭 있음, coachStatus 부재)
결과 화면 렌더 무회귀 스크린샷을 .planning/quick/260901-wbo-coach-defer-loading/ 에
저장. pending→채움 라이브 검증은 Pod 필요 — 수행 불가를 SUMMARY 에 명시하고 완료
주장 금지 (다음 Pod E2E 항목: 신규 분석 1건으로 done 조기 도착 + placeholder →
코칭 승격 + coach_dual/coach_hook 스테이지 로그 + 구/신 앱 교차 확인).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/app && npx tsc --noEmit && node --test "src/lib/__tests__/*.test.*"</automated>
    <human-check>구 doc 결과 화면 스크린샷 렌더 무회귀 (belle 확인용 아티팩트 — pending 라이브 검증은 다음 Pod E2E)</human-check>
  </verify>
  <done>tsc 0 에러, node 테스트 기준선 212 passed / 0 유지. coachPending placeholder 가 coachStatus==='pending' 에서만 표시되고 legacy doc 렌더 무회귀 스크린샷 저장. PROGRESS_* 3상수 재보정 완료.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| LLM 출력 → Firestore doc | coach_dual/hook 텍스트가 사후 부분 갱신으로 사용자 doc 에 진입 |
| 사후 스테이지 → 사용자 doc | complete 이후 write 는 계약이 허용한 field-path 만 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-wbo-01 | Tampering | update_analysis_coach_text | mitigate | 키 화이트리스트 + status enum + 기존 hook/flat validator 재사용 — 계약 밖 field-path write 불가 (D-03 경계: 점수·records 문구 사후 변경 영구 금지) |
| T-wbo-02 | DoS | 사후 coach 스테이지 | mitigate | 재raise 0 규율 (coach_audio 뼈대) — coach 실패가 분석·후속 스테이지를 죽이지 않음, FAILED 마킹 + 수치 폴백 잔존 |
| T-wbo-03 | Info Disclosure | 로그 | mitigate | 본문/시크릿 미기록 관례 유지 (coach_audio 로그 규율 복제) |
| T-wbo-SC | Tampering | 패키지 설치 | accept | 신규 패키지 0 — 기존 의존만 사용 |
</threat_model>

<verification>
- 백엔드: `cd backend && .venv/bin/python -m pytest tests` — 기준선 4548 passed / 0 failed 유지 (신규 테스트 추가분 증가 허용).
- 앱: `npx tsc --noEmit` 0 / `node --test "src/lib/__tests__/*.test.*"` 212 passed / 0.
- 계약 3중 미러 diff 확인: contract.md coachStatus 절 + models.COACH_STATUSES + analysis.ts coachStatus? 세 곳 동시 존재.
- 시뮬레이터 구 doc 렌더 무회귀 스크린샷 (아티팩트 저장).
- 라이브 pending→채움·스테이지 로그 검증 = **다음 Pod E2E 항목** (이 계획에서 완료 주장 금지). Pod 는 다음 기동 때 git pull 로 수령, 앱은 다음 빌드.
</verification>

<success_criteria>
- status 'done' write 가 coach_dual/hook 실행 이전에 발생 (단위 테스트로 complete payload 에 coach 5필드 부재 + coachStatus='pending' 증명)
- 사후 갱신 payload 에 전수 표 5필드 전부 (tips 통째 + hook 2 field-path + geminiB + coachStatus)
- 채점·veto·게이트·records 문구 경로 diff 0 (기존 테스트 무손상)
- 앱 placeholder: pending 에서만, 상한 180s, legacy/failed/done 은 기존 렌더
- 진행률: comparison 장시간 정지/기어오름 제거 (새 실측 기대치 3상수)
</success_criteria>

<output>
완료 시 `.planning/quick/260901-wbo-coach-defer-loading/260901-wbo-SUMMARY.md` 작성 —
다음 Pod E2E 체크리스트(신규 분석 1건: done 조기 도착 실측, placeholder→승격,
coach_dual/coach_hook 스테이지 로그, 파워스핀·킵업 페어 재실행과 병행 가능) 포함.
</output>
