---
phase: quick-260704-fwb
plan: 01
subsystem: coaching-output
tags: [coach-prompt, corrective-exercises, vision-veto, error-copy, low-quality]
requires: [vision_veto.FaultKey, exercise_map, coach_writer dual-track, analyze low-quality warning]
provides:
  - "코치 양 writer(Cerebras+Gemini) 프롬프트 처방 구조 강제 (원인 기전 사슬 + 구체 처방)"
  - "보완 운동 매칭에 vision veto 결함 부위(fault_keypoint_sets) 배선"
  - "저화질 승인 업로드의 not_pole 실패 → 화질 우선 안내 분기 (앱 로컬)"
  - "'먼저 교정할 점' 카드 상태 → 원인 기전 → 처방 연결 구조"
affects: [backend coach prompts, backend exercise mapping, app analysis flow copy]
tech-stack:
  added: []
  patterns: [keypoint_set 문자열 리터럴 lockstep 매핑, 라우터 param 로컬 표시 플래그]
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/coach_writer.py
    - backend/shared/python/sunity_shared/gemini/coach_writer_v2.py
    - backend/shared/python/sunity_shared/analysis/exercise_map.py
    - backend/functions/pipeline/app.py
    - backend/tests/test_coach_writer.py
    - backend/tests/gemini/test_coach_writer_v2.py
    - backend/tests/phase13/test_map_exercises.py
    - app/src/app/(tabs)/analyze.tsx
    - app/src/app/analysis/reference.tsx
    - app/src/app/analysis/loading.tsx
    - app/src/app/analysis/result.tsx
decisions:
  - "기전 사슬 지시는 Cerebras _SYSTEM(시스템 프롬프트)에 배치 — vision_fault 없는 유저 프롬프트는 기존과 동등 (graceful 불변 테스트 고정)"
  - "leg → hip_hamstring_tight 1순위 (스플릿 각도 부족 = 고관절 유연성, kip-up 케이스 정합)"
  - "lowQuality 플래그는 '경고를 보고 진행한' 업로드에만 심음 — 경고 없이 통과한 영상은 기존 카피"
  - "vetoLeadNote 문구 축약 — 신설 처방 라인('이렇게 교정해 보세요')과 중복 제거"
metrics:
  duration: ~25min
  completed: 2026-07-04
  tasks: 3/3
  tests: backend 126 passed (coach 48 + phase13 94 교집합 포함), app tsc clean
---

# Quick 260704-fwb: 코칭 처방화 + 보완운동 결함 매칭 + 저화질 에러문구 분기 Summary

Cerebras/Gemini 코치 프롬프트에 원인 기전 사슬('무엇 때문에 → 무엇이 무너짐') + 구체 처방 구조를 강제하고, vision veto 결함 부위(keypoint_set)를 보완 운동 매칭에 배선하며(kip-up 다리/어깨 결함에 Farmer's Walk 그립 운동 선두 미스매치 해소), 저화질 승인 업로드의 not_pole 실패를 화질 우선 안내로 분기했다.

## Tasks

| Task | Commit | 내용 |
|---|---|---|
| 1. 코치 프롬프트 처방화 | b2b8fb9 | _SYSTEM/_COACH_SYSTEM_INSTRUCTION 기전 사슬 + 상태-서술-금지 + fix 구체화, vision 가설 '출발점' 승격, supportedDifferences 실측 근거 렌더(방어적), 프롬프트 빌드 테스트 11건 |
| 2. 보완 운동 결함 매칭 | c03203e | _KEYPOINT_SET_TO_DEFECTS(8값 전부) + map_exercises fault_keypoint_sets kwarg(None=byte-동등) + pipeline applied 시 keypoint_set join(try/except None 폴백), 테스트 6건 |
| 3. 앱 카피/카드 분기 | eb8c294 | lowQuality param 3-경로 전달(analyze→[reference→]loading), not_pole+저화질 → 화질 우선 title/본문/tipCard, '먼저 교정할 점' = 상태→원인 기전(상위 2 가설)→처방 연결(faultJoints 매칭 팁) |

## Pod 검증 Follow-up (2026-07-04)

| Fix | Commit | 내용 |
|---|---|---|
| 보완 운동 정렬 재수정 | 7bcd3e0 | pod 재분석에서 painArea wrist 안전 운동(Farmer's Walk/Hand Grippers)이 여전히 선두 (13-A painArea 최우선 설계가 원인 — forcePatternInference 아님, 2개 짝 = wrist painArea 시그니처) → fault_keypoint_sets 존재 시 확정 결함 유래 운동을 목록 선두로. defect 당 상위 2 선행 배치(_FAULT_LEAD_PER_DEFECT=2) + 나머지 후순위 백필, grip/painArea 운동은 제거 없이 후순위 유지, None 경로 byte-동등. pod 재현 케이스(pain wrist + fault leg) exact-order 테스트 추가. phase13 95 passed |
| '거의 동일' 팁이 detail2 폐기 | e0401ae | kip-up fault 문서 tips 가 일반 팁 1개(detail2 0) — build_result 의 angle>=95 분기가 veto apply **이전**에 실행돼 조립된 듀얼 코치 detail2 를 통째로 버림 (88점·확정 결함과 카피 모순 + 처방 코칭 미노출). fix = `assemble.rebuild_tips_for_vision_fault` 신설(순수 함수): veto applied + 일반 팁 단독 + coach_details 존재 시에만 per-joint tips+detail2 재조립 (faultJoints 관절 선두, coach 커버 관절만 — 수치 폴백 '0° 차이' 모순 차단), pipeline 이 _apply_vision_veto 직후 호출 (최종 status 를 아는 유일 시점, try/except 비치명). clean(not_applicable)/veto 부재/기존 per-joint tips/coach_details 빈 경우 = byte-동등 (하위호환). build_result 본체·채점 무접촉. 테스트 6건, phase13+coach 133 passed |

**듀얼 코치 실텍스트 저장 경로 (코드 확인):** `users/{uid}/analyses/{analysisId}` 문서의 `result.tips[]`. pipeline `_process` 가 `assemble_dual_coach_sections` (app.py:3358) 출력 coach_details 를 `assemble.build_result` → `build_tips` (assemble.py:384) 로 전달 → `result.tips[i] = {joint, title, detail(카드 한 줄), detail2: {causes: [{title, explanation, fix}], injuryRisk?, coachNote}}`. kismam top 3 관절만 detail2 보유. `geminiB` 는 audit 메타 전용 (sectionAudit = 섹션별 출처/crossFilled, 실텍스트 없음). TS mirror = app/src/types/analysis.ts CoachingTip/CoachingTipDetail(:175-206).

## Verification

- backend: `pytest tests/test_coach_writer.py tests/gemini/test_coach_writer_v2.py tests/phase13/ -q` → **126 passed** (초기 3 task 시점) / follow-up 후 phase13 **95 passed** (회귀 0)
- app: `npm run typecheck` → clean
- 채점 무접촉 grep: dimensions.py / deduction_engine.py / kismam.py / vision_veto.py / models.py / types/analysis.ts diff **0** (확인 완료)
- 스키마·validator 형상 불변: _normalize_entry / tone_validation / RecommendedExercise 계약 변경 0

## Deviations from Plan

None - plan executed exactly as written.

## Pod 재기동 후 실측 검증 체크리스트 (orchestrator + belle — executor SSH 금지)

kip-up fault 페어 재분석으로 확인:

1. 코칭 팁 causes 가 "X 때문에 Y가 무너짐 → Z 연습" 구조인지 (상태 서술 단독 문장 부재)
2. kip-up fault 결과의 보완 운동에 다리(햄스트링/고관절)·어깨 운동 포함, Farmer's Walk 류 그립 운동이 선두 아님
3. 카톡 압축본(저화질 경고 승인 후 진행) not_pole 실패 시 "화질이 낮아 분석하지 못했을 수 있어요" 안내 (앱은 OTA 또는 다음 빌드 반영 필요)
4. '먼저 교정할 점' 카드가 상태 → 가능한 원인('~로 보임') → "이렇게 교정해 보세요" 순으로 렌더
5. 점수 회귀 없음 (success 100 / kip-up fault 88 유지 — 채점 경로 무접촉이므로 변동 시 즉시 조사)

## Known Stubs

None — 모든 신설 UI 섹션은 저장된 Firestore 값(rootCauseHypotheses/faultJoints/tips)에 배선됨. 데이터 부재 doc 은 섹션 생략/폴백 한 줄 (의도된 graceful, 스텁 아님).

## Threat Flags

없음 — 신규 네트워크 엔드포인트/auth 경로/스키마 변경 0. lowQuality 는 표시 전용 로컬 param (백엔드 미전송).

## Self-Check: PASSED

- 커밋 3건 존재 확인: b2b8fb9 / c03203e / eb8c294
- 수정 파일 11개 전부 존재
- 게이트: backend 126 passed / app tsc clean / 채점 파일 무접촉
