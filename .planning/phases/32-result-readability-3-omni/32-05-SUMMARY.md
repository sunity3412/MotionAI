---
phase: 32-result-readability-3-omni
plan: 05
subsystem: ui
tags: [phrasebook, terminology-map, ipsf, coaching-copy, fail-closed, lockstep, tdd]

# Dependency graph
requires:
  - phase: 32-01
    provides: 계약·데이터 골격 (감점 카드/미션 표면이 소비할 result 필드)
  - phase: 24 (ipsf_criteria)
    provides: CRITERION_GROUPS 실존 방출값 (문구집 키 소스)
  - phase: 10 (safety_flags)
    provides: _FLAG_TYPES 4종 (안전 entry 키 소스)
  - phase: 13 (exercise_map)
    provides: corrective_exercises.json defects 키 (exerciseId 슬롯 참조)
provides:
  - 동작×결함 고정 문구집 phrasebook.json (13 entry × 6 슬롯 + 4 안전 entry + fail-closed 폴백 + 커버리지 매트릭스)
  - phrasebook.py 순수 조립 함수 (assemble_phrases/assemble_safety_phrases, fail-closed, boto3/network 0)
  - 용어 맵 단일 출처 terminology_map.json + 앱 미러 terminologyMap.ts (lockstep 강제)
  - 금지어 grep 게이트(D-09 %환산·수치·유사도·박제) + sanity + 양방향 lockstep 테스트
affects: [32-09 (파이프라인 방출), 32-10 (감점 카드 렌더), 32-08 (감점 카드 3단 컴포넌트)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "고정 문구집 fixture + 순수 조립 함수 (exercise_map.py 아날로그 복제 — lazy 캐시·flat scalar·graceful)"
    - "fail-closed 폴백: 미지원 조합은 cueLine/exerciseId 생성 0 (일반론 조언 fabrication 차단)"
    - "커버리지 매트릭스 = 개수 아닌 셀 분류로 커버리지 증명 (198 셀 전분류, 빈 셀 0)"
    - "JSON 단일 출처 + TS 미러 양방향 lockstep 테스트 (주석 정합이 아니라 텍스트 대조 정합)"

key-files:
  created:
    - backend/data/phrasebook.json
    - backend/data/terminology_map.json
    - backend/shared/python/sunity_shared/analysis/phrasebook.py
    - backend/tests/phase32/test_phrasebook_forbidden.py
    - backend/tests/phase32/test_phrasebook_assembly.py
    - backend/tests/phase32/test_terminology_lockstep.py
    - app/src/lib/terminologyMap.ts
    - .planning/phases/32-result-readability-3-omni/32-PHRASEBOOK-REVIEW.md
  modified: []

key-decisions:
  - "dimension_overall_fallback(엔진 국소화 실패 저정보 criterion) → fail-closed (특정 행동 큐 생성 시 일반론). 이것이 커버리지 매트릭스의 fail-closed 열."
  - "entries 전량 criterion-common(동작 독립) — 같은 criterion 이 동작마다 다른 뜻이 되지 않으므로 motion-specific override 0 (일반화 우선, overfit 금지)."
  - "top-level failClosed 를 4번째 키로 분리 — fail-closed 스키마(cueLine/exerciseId 없음)가 entries 균일성(전 entry 6키+실존 exerciseId)과 충돌하므로."
  - "금지어 게이트는 렌더 카피만 스코프(_meta provenance 제외) — copy_templates AST 게이트가 docstring/FORBIDDEN tuple 을 scope 밖으로 두는 선례 정합."

patterns-established:
  - "phrasebook 조립: 매칭 우선순위 {motion}.{criterion} → __common__.{criterion} → failClosed"
  - "안전 entry: cueLine·게임 요소 없음 (D-14 차분한 안전 톤), coachQuestion 에 '강사와 이 화면을 함께 확인' 유도"

requirements-completed: [D-11, D-12, D-08, D-06, D-13, D-09, D-14]

# Metrics
duration: ~45min
completed: 2026-07-21
---

# Phase 32 Plan 05: 번역 레이어 문구집 · 용어 맵 Summary

**동작×결함 고정 문구집(13 entry × 상태→왜→행동→코치질문→운동연결 5슬롯 + 4 안전 entry + fail-closed 폴백) + 측정 용어→심사 언어 용어 맵을, 실존 방출값 커버리지 매트릭스·금지어 게이트·양방향 lockstep·belle 감수의 4중 보증으로 구축 — LLM 골격 소유 경로 차단(D-11)**

## CHECKPOINT — belle 전량 승인 (Task 3, 종결)

**Tasks 1-3 완료. Task 3(belle 문구 전량 감수) = 전량 승인 (2026-07-21).**

- 감수 산출물: `.planning/phases/32-result-readability-3-omni/32-PHRASEBOOK-REVIEW.md` (전 entry 표 + 안전 + fail-closed + 용어 맵 + 커버리지 매트릭스 요약 + belle 판정 기준 5개)
- 승인 후 수정 지시 없음 → 금지어·lockstep 게이트 재실행 불요 (승인 시점 게이트 green 유지)

### belle 승인 기록 (정본)

- **판정:** 전량 승인
- **일자:** 2026-07-21
- **응답 원문:** "전량 승인"
- **맥락:** 오케스트레이터가 판정 기준 5가지(①톤 친숙하되 장난스럽지 않게 ②행동문이 일반론 아닌 외부 큐 ③심사 언어가 IPSF 기준과 정합 ④코치 질문이 강사에게 그대로 보여줄 완성문 ⑤fail-closed 문구 자연스러움)와 문구 전량 + 설계 판단 4건을 제시한 상태에서 전량 승인.
- **승인에 포함된 설계 판단 4건:** (1) entries 전량 criterion-common 일반화(동작 전용 override 0) (2) dimension_overall_fallback → fail-closed (3) angle_vs_reference cueLine = 기준 자세 겹치기 외부-기준 큐 (4) REGISTERED_MOTIONS 실측 10동작으로 매트릭스 행 정정.
- **수정 지시:** 없음. → D-11 승인 선출시 충족. 파일럿 현장(강사·수강생) 반응으로 개정하는 것은 후속(D-11 개정 경로).

## Performance

- **Duration:** ~45 min (+ belle 감수 turnaround)
- **Tasks:** 3/3 완료 (Task 3 = belle 전량 승인 2026-07-21)
- **Files created:** 8
- **Tests:** phase32 31 passed (신규 21 + 기존 10 무회귀)

## Accomplishments

- **phrasebook.json** — 실존 방출값 전수 조사(ipsf_criteria CRITERION_GROUPS 14 criterion + safety_flags 4 유형 + REGISTERED_MOTIONS 10 + corrective_exercises defects 6) 기반 문구집. 13 criterion-common entry × 6 슬롯, 4 안전 entry(D-14), fail-closed 폴백, `_meta.coverageMatrix`(11행×18열=198 셀 전분류)·keySources·evidence.
- **phrasebook.py** — 순수 조립 함수(assemble_phrases 매칭 우선순위 + assemble_safety_phrases + load_terminology_map + rendered_copy_strings). exercise_map.py 순수성 복제(boto3/network 0, lazy 캐시, flat scalar, graceful). fail-closed 시 cueLine/exerciseId 생성 0.
- **terminology_map.json + terminologyMap.ts** — 측정 용어(angle/line/stability/reach/split)→심사 언어 사람 말 단일 출처 + 앱 미러.
- **게이트** — 금지어(D-09 %환산·수치·유사도·박제 0) + sanity(추출 93 ≥ 50) + 양방향 lockstep(JSON↔TS 키·값 동일) TDD.

## Task Commits

1. **Task 1: phrasebook.json 초안 + 커버리지 매트릭스** — `2296414` (feat)
2. **Task 2 (TDD RED): assembly/forbidden/lockstep 실패 테스트** — `5fb1ad8` (test)
3. **Task 2 (TDD GREEN): phrasebook.py + terminology_map.json + terminologyMap.ts** — `dd3d4a9` (feat)
4. **Task 3: 32-PHRASEBOOK-REVIEW.md 감수 산출물** — `63f6a6e` (docs)
5. **Task 3: belle 전량 승인 반영 (승인란 + SUMMARY 정본)** — 이 문서와 동일 종결 커밋 (docs)

## Files Created

- `backend/data/phrasebook.json` — 동작×결함 고정 문구집 fixture (+커버리지 매트릭스·근거 출처)
- `backend/data/terminology_map.json` — 측정 용어→심사 언어 단일 출처
- `backend/shared/python/sunity_shared/analysis/phrasebook.py` — 조립 순수 함수(fail-closed 포함)
- `backend/tests/phase32/test_phrasebook_forbidden.py` — 금지어 게이트 + sanity
- `backend/tests/phase32/test_phrasebook_assembly.py` — 조립·fail-closed·flat scalar·safety
- `backend/tests/phase32/test_terminology_lockstep.py` — JSON↔TS 양방향 대조
- `app/src/lib/terminologyMap.ts` — terminology_map.json 미러 (lockstep 대상)
- `.planning/phases/32-result-readability-3-omni/32-PHRASEBOOK-REVIEW.md` — belle 감수용 전량 표

## Decisions Made

- **dimension_overall_fallback = fail-closed:** 엔진이 결함을 특정 관절로 국소화 실패한 저정보 폴백. 특정 행동 큐를 지어내면 일반론이 되므로 fail-closed 로 라우팅 — 이것이 커버리지 매트릭스의 fail-closed 열.
- **entries 전량 criterion-common:** 같은 criterion 이 동작마다 다른 뜻이 되지 않으므로 motion-specific override 0 (일반화 우선, [[scoring-redesign-must-generalize-no-overfit]]). 매트릭스 분류는 전 motion 행에 균일 → 등록/미등재 모두 같은 phrasing.
- **angle_vs_reference cueLine = 기준 겹치기 외부-기준 큐:** per-joint reference_relative 는 방향 미상(abs deviation)이라 "펴세요/굽히세요"가 오도 위험. "기준 자세에 나란히 겹쳐 맞추기"(방향 무관 external-focus)로 통일 — D-20 줌 비교와 정합.

## Deviations from Plan

### Auto-fixed / 판정 정정

**1. [Rule 1 - 실측 정정] REGISTERED_MOTIONS = 10 (플랜 "6동작" 문구 정정)**
- **Found during:** Task 1 (실존 방출값 전수 조사)
- **Issue:** 플랜은 "등록 6동작"이라 기술했으나 `gemini_motion_classifier.REGISTERED_MOTIONS` 실측 = 10 (ref-climb/foxtop/foxtop-split/invert/sideway-spin + kip-up/power-spin/peter-pan/elbow-twist-sister/pdshape). belle 의 "6동작"은 fixture 스윕 부분집합(D-23).
- **Fix:** 플랜 자체 지시("REGISTERED_MOTIONS 실측")를 따라 커버리지 매트릭스 행 = 10 등록 + 미등재 = 11행. phrasing 코퍼스 무영향(criterion-common — 동작 수 무관).
- **Files:** backend/data/phrasebook.json (_meta.coverageMatrix.rows)
- **Committed in:** 2296414

**2. [설계 결정] top-level `failClosed` 4번째 키 추가**
- **Found during:** Task 1
- **Issue:** 플랜 스키마는 최상위 {_meta, entries, safetyEntries} 3키. 그러나 fail-closed 는 cueLine/exerciseId 를 갖지 않아 "entries 각각 6키 + 실존 exerciseId" 균일 규칙과 충돌(entries 안에 두면 acceptance 위반).
- **Fix:** failClosed 를 top-level 4번째 키로 분리. verify 스크립트는 3키만 assert 하므로 통과. entries 균일성 보존.
- **Files:** backend/data/phrasebook.json, phrasebook.py
- **Committed in:** 2296414, dd3d4a9

**3. [설계 결정] 금지어 게이트 스코프 = 렌더 카피(_meta provenance 제외)**
- **Found during:** Task 2
- **Issue:** 플랜은 "JSON 2개 전체 string 순회". 그러나 _meta 는 IPSF 근거 수치("20° 허용오차")·코드경로·메모리 태그를 정직 인용하는 문서 — 사용자 카피 아님. 전체 순회 시 근거 수치가 D-09 수치-금지에 걸리는 거짓 위반.
- **Fix:** 게이트를 렌더 카피(entries 슬롯 + safetyEntries + failClosed + terminology terms)로 스코프. copy_templates AST 게이트가 docstring/FORBIDDEN tuple 을 scope 밖으로 두는 선례 정합. 테스트 docstring 에 근거 명시.
- **Files:** phrasebook.py (rendered_copy_strings), test_phrasebook_forbidden.py
- **Committed in:** dd3d4a9

---

**Total deviations:** 1 실측 정정(Rule 1) + 2 설계 결정. 스키마/스코프 정정은 acceptance 와 도메인 정합을 지키기 위한 필수 조정 — scope creep 없음.

## Issues Encountered

- **worktree node_modules 부재:** 병렬 실행 worktree 에 `app/node_modules` 없어 `npm run typecheck` 전체 실행 불가. terminologyMap.ts 는 무-import 독립 모듈이라 메인 리포 tsc 로 standalone strict typecheck(EXIT=0) 검증. 전체 typecheck 는 병합 후 CI/오케스트레이터가 실행.
- **환경 python 3.14 (homebrew), Lambda 런타임은 3.12:** 순수 함수 테스트라 무영향. 문법도 3.12 호환(from __future__ import annotations).

## Next Phase Readiness

- **belle 전량 승인 완료 (2026-07-21)** — 32-09(파이프라인 방출)·32-10(감점 카드 렌더)이 phrasebook.py 를 데이터 원천으로 소비 가능. 문구 변경 재작업 위험 해소.
- **미지원 조합은 fail-closed 로 코치 출구 연결** — 일반론 재유입 경로 0 (성공 기준 충족).
- **blocker 없음.** D-11 승인 선출시 충족. 파일럿 현장 반응 기반 개정은 후속 D-11 개정 경로(별도).

## Self-Check: PASSED

- 8 created files 전부 FOUND (phrasebook.json/terminology_map.json/phrasebook.py + 3 tests + terminologyMap.ts + 32-PHRASEBOOK-REVIEW.md + 이 SUMMARY)
- 4 task 커밋 전부 FOUND (2296414 / 5fb1ad8 / dd3d4a9 / 63f6a6e)
- phase32 31 passed (신규 21 + 기존 10 무회귀), terminologyMap.ts standalone strict tsc EXIT=0

---
*Phase: 32-result-readability-3-omni*
*Plan: 05 — Tasks 1-3 완료 (Task 3 belle 전량 승인 2026-07-21)*
*Completed: 2026-07-21*
