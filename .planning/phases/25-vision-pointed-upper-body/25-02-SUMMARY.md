---
phase: 25-vision-pointed-upper-body
plan: 02
subsystem: backend-scoring
tags: [vision-veto, gemini, support-gate, keypoint-set-fold, cache-marker, prompt-v10, SCORE-15]
requires:
  - 25-01 (pointed 매퍼 — 대표 _faultKey.side=unknown 을 양측 해소하는 소비자)
  - vision_veto.FaultKey (canonical 키 어휘 — keypoint_set 에 shoulder 이미 커버)
provides:
  - _filter_supported_differences keypoint_set 단독 그룹 fold (side/fault_kind fragment 접합)
  - AGGREGATION_VERSION="agg2" 캐시 marker (build_key folding — 집계 변경 = 자동 cache-miss)
  - PROMPT_VERSION v10.0 — part_scope 구조화 강제 (서사-only 편차의 differences[] 방출)
affects:
  - 25-04 (Pod 6페어 sweep — 프롬프트/집계 bump 회귀 게이트 + 상체 faultKey 실효 판정)
  - 25-01 배선 (상체 faultKey 가 살아남아야 pointed→window 감점이 발화)
tech-stack:
  added: []
  patterns:
    - "집계 알고리즘 버전 marker 를 캐시 키에 folding — rich 캐시 stale-hit 구조적 차단"
    - "프롬프트 레버 = scope-집중 특정성 + 구조화 강제 (동작명 주입 아닌 generic)"
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py (+50/-9)
    - backend/tests/test_gemini_vision_scorer.py (+204/-2, 11 tests 신규 + 1 갱신)
decisions:
  - "그룹 키 = keypoint_set 단독 (part_scope 는 hint 균일이라 원래 무변별 — 리서치 §1 (a))"
  - "대표 _faultKey = 대표 difference 의 FaultKey 에 side 만 그룹-해소 값으로 dataclasses.replace (명시 side 유일=그 side / 혼재·부재=unknown)"
  - "support 카운트 = 기존 diff_id 발생 건수 순회 의미 보존 (call-교차로 재정의 안 함)"
  - "AGGREGATION_VERSION 은 PROMPT_VERSION 과 동일한 globals() 경유 folding (monkeypatch 반영)"
  - "구조화 강제 지시는 전 scope(upper/lower/line) 공통 — 일반화 원칙 정합, upper_body 전용 분기 0"
metrics:
  duration: ~8 min (05:02–05:10 UTC)
  completed: 2026-07-04
  tasks: 2/2 (Task 1 TDD RED→GREEN)
  tests: 11 신규 (8 fold/marker + 3 prompt), 파일 65 passed / 다운스트림 8개 스위트 253 passed (회귀 0)
---

# Phase 25 Plan 02: 상체 짚기 커버리지 — keypoint_set fold + 프롬프트 구조화 Summary

어깨 언급이 side/fault_kind fragment 로 support K=2 미달 drop 되던 것을 keypoint_set 단독 그룹 fold 로 접합하고, scope 집중 호출의 서사-only 편차를 differences[] 로 강제 방출(PROMPT_VERSION v10.0) — 차단 1(짚기)의 두 경우(집계 fragment + 미방출)를 모두 처방, 캐시는 AGGREGATION_VERSION+PROMPT_VERSION 2중 marker 로 전량 miss.

## Tasks

| Task | Name | Commits | Result |
|------|------|---------|--------|
| 1 | support 집계 fragment fold + AGGREGATION_VERSION 캐시 marker | a61262f (RED) / 2a94b6d (GREEN) | 8 tests PASS |
| 2 | upper_body 짚기 프롬프트 구조화 강제 + PROMPT_VERSION bump | 535b190 | 3 tests 신규 + 1 갱신 PASS |

## What Was Built

**Task 1 — `_filter_supported_differences` fold + 캐시 marker (gemini_vision_scorer.py):**
- 그룹 키를 FaultKey 4필드 전체 `tuple(sorted(fk.to_dict().items()))` → **`fk.keypoint_set` 단독**으로 변경. "왼쪽 어깨 굽음"(left/pole_gap_or_bent) + "어깨 정렬 흐트러짐"(unknown/extension_or_alignment)이 shoulder 그룹 support 2 로 K=2 통과 (단위 테스트 증명).
- 대표 선택 규칙(최고 severity rank → dev) / severity='none' 필터 / `_supportCount`·`_sourceIds` 메타 / severity 내림차순 정렬 — 전부 불변. 서로 다른 keypoint_set(shoulder vs leg)은 분리 유지, 출력은 그룹당 대표 1개(union 부풀림 0).
- 대표 `_faultKey` = 대표 difference 의 FaultKey 에 side 만 그룹-해소 값으로 `dataclasses.replace`: 그룹 내 명시(left/right) side 집합이 단일이면 그 side, 혼재/전부 unknown 이면 "unknown" (25-01 pointed 매퍼가 unknown → 양측 해소).
- `AGGREGATION_VERSION = "agg2"` 모듈 상수 신설(집계 알고리즘 버전 marker — 튜닝 상수 아님) + `VisionVetoCache.build_key` 의 `":".join` component 에 `globals()` 경유 folding (schema_v 뒤 삽입 — 기존 키 공간 재사용 0). docstring 에 "rich 캐시는 집계 후 supported_differences 저장 → 집계 변경 = marker bump 필수 (kip-up whole/whole_fanout stale-hit FP 이력, 90d038f)" 박제.

**Task 2 — part_scope 구조화 강제 + v10.0 (gemini_vision_scorer.py):**
- `_call_gemini_comparison` part_scope suffix 에 추가: "이 부위에서 관찰한 각 편차는 반드시 differences[] 배열의 개별 항목으로 구조화하고, body_part 에는 좌/우를 명시하세요(예: '왼쪽 어깨'). primary_fault 서사에만 언급하고 differences 에서 누락하는 것은 금지입니다." — 기존 1·2번 규칙(정타/사소차/촬영조건 비결함) 유지 문구 보존, 전 scope 공통.
- `PROMPT_VERSION` v9.0 → v10.0 + 주석에 변경 사유·회귀 게이트(25-04 6페어 full sweep, 리서치 함정 ⑤) 박제. PROMPT_VERSION 이 키 component 라 전 캐시 자동 무효화.
- fanout scope 수(3)/call 수/wall budget(120s) 불변 — resource_limited fail-closed 함정 ④ 무접촉. `_SCORE_PATTERN` 점수누출 폐기 로직 무접촉 (기존 테스트 통과로 확인).

**테스트 (test_gemini_vision_scorer.py, 11 신규 + 1 갱신):**
- fold: fragment 접합 K=2 통과 / side 해소(유일·혼재·부재) / 대표 선택 규칙 / keypoint_set 분리 / union 부풀림 0(같은 call 2건 → 대표 1, support=발생 건수) / none 필터 보존
- 캐시: build_key 에 AGGREGATION_VERSION 포함 + marker 변경 시 다른 키
- 프롬프트: 실송신 프롬프트 캡처(fake client)로 전 scope 구조화 지시 포함 / 등재 동작명(한·영 15종) 미포함 / part_scope=None 경로 byte-불변
- `test_prompt_schema_version` 갱신: v10.0 + `!= "v9.0"` bump assert

## Verification

- `pytest tests/test_gemini_vision_scorer.py -q` → **65 passed** (baseline 54 + 11)
- `pytest tests/ -k "vision or gemini or veto or fault" --continue-on-collection-errors` → **591 passed, 19 failed** — FAILED 집합이 baseline HEAD(981090a, 임시 worktree 재실행)와 **byte-diff IDENTICAL** (gemini env / app-module-name-collision pre-existing, 회귀 0)
- 다운스트림 소비자 8개 스위트(pointed mapper/coach_writer/vision_veto/deduction seam·engine/vision gate/phase24 gates/scorer) → **253 passed**
- 동작명 grep 게이트: 테스트로 assert (리포 잔여 "v9.0" 참조 0 — bump assert 만 잔존)
- 짚기 커버리지 실효(상체 faultKey 실산출)는 25-04 Pod sweep 이 최종 판정 (본 플랜 = 결정적 pure 함수/프롬프트 계층)

## Deviations from Plan

None - plan executed exactly as written.

(참고: 다운스트림 무회귀 확인을 위해 baseline 981090a 를 임시 read-only worktree 로 체크아웃해 동일 필터 FAILED 집합을 diff — 검증 절차 추가일 뿐 코드 변경 아님. worktree 는 제거 완료.)

## Known Stubs

None — 본 플랜 산출물에 stub/placeholder 0. 상체 faultKey 의 실효 발화는 설계상 25-04 Pod sweep 게이트 소관.

## Threat Model Compliance

- T-25-04 (환각 결함 spoofing): fold 는 fragment 접합만 — K=2 게이트/none 필터/tol 20° dead-zone 불변 (게이트 완화 0, 테스트로 단발 drop 유지 확인)
- T-25-05 (stale 캐시 tampering): AGGREGATION_VERSION + PROMPT_VERSION 2중 marker folding — 기존 키 공간 재사용 0
- T-25-06 (점수 누출): `_SCORE_PATTERN` 무접촉, 프롬프트에 점수 요청 0 (schema/verdict score-free 테스트 유지 통과)

## Self-Check: PASSED

- FOUND: backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py (AGGREGATION_VERSION 포함)
- FOUND: backend/tests/test_gemini_vision_scorer.py
- FOUND commits: a61262f / 2a94b6d / 535b190 (git log 확인)
