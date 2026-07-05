---
phase: quick-260705-h5z
plan: 01
subsystem: ml-vision
tags: [gemini, vision-veto, hybrid-granularity, still-frame, dtw, support-gate]
requires:
  - quick-260705-g1d (하이브리드 granularity — upper still 분기 + media_kind='image')
  - fault_zoom._matched_ref_frame (DTW-매칭 ref 인덱스, 기존 재사용)
provides:
  - "scorer still 경로 주입 계약: assess_fault_context_video(still_student_png/still_reference_png/still_frame_indices)"
  - "SelectedFramePair.ref_match_source (dtw|ratio) provenance 판별"
  - "pipeline pair 경로/인덱스 → scorer 배선 (DTW 매칭 실패 시 video-only 폴백)"
  - "upper scope 2-call fanout — 비-각도 관측 distinct-call K=2 성립"
affects: [pod-sweep, vision-veto-cache]
tech-stack:
  added: []
  patterns: ["추출 책임 = 생성처(파이프라인), scorer 는 소비만", "프레임 provenance 변경 = granularity 마커 bump"]
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py
    - backend/shared/python/sunity_shared/analysis/vision_veto.py
    - backend/functions/pipeline/app.py
    - backend/tests/test_gemini_vision_scorer.py
    - backend/tests/test_pipeline_vision_gate.py
decisions:
  - "still 페어 추출을 스코어러-측(raw imageio+시간비례)에서 파이프라인-측(9fps window/DTW 인덱스)으로 이동 — 폴백으로도 미유지(죽은-틀린 경로 삭제)"
  - "still 활성 조건 = 세 kwargs 모두 제공 (부분 제공 = 미제공, 어중간한 상태 금지)"
  - "DTW 매칭 실패(ratio)면 still 미전달 — 위상 불일치 페어는 Gemini 가 정당하게 '편차 없음' 판정(0/6)"
  - "INPUT_GRANULARITY_WHOLE_FANOUT hybrid1→hybrid2 단일 bump 로 provenance 변경+2-call 집계 변화 동시 커버 (AGGREGATION_VERSION 무 bump)"
  - "upper 2-call 은 support 규칙 변경 아님 — distinct-call K=2 의미론을 충족시키는 입력 변경 (_filter_supported_differences 무접촉)"
metrics:
  duration: "~11분"
  completed: "2026-07-05"
  tasks: 3
  tests: "229 passed (4개 스위트)"
---

# Quick 260705-h5z: still 페어 파이프라인-측 추출 배선 Summary

**One-liner:** g1d 하이브리드 still 의 위상 불일치 추출(스코어러-측 raw imageio+시간비례)을 파이프라인의 window/DTW-매칭 인덱스 페어 주입으로 교체하고, upper scope 를 동일 핸들 2-call 로 만들어 각도쌍 없는 상체 관측(그립/어깨)이 distinct-call K=2 support 를 충족하게 배선.

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | scorer still 경로 주입 계약 + 자체 추출 제거 + hybrid2 키 bump | a45a7b3 |
| 2 | pipeline pair 경로/인덱스 배선 + DTW 매칭 실패 video-only 폴백 | 98358fd |
| 3 | upper scope 2-call fanout + telemetry 정합 + 전체 스위트 | 1c735e6 |

## What Changed

### Task 1 — scorer (RC-02)
- `assess_fault_context_video`: `still_at_seconds` 제거 → `still_student_png`/`still_reference_png`/`still_frame_indices` kwargs. 세 값 모두 제공 시만 still 활성.
- 스코어러-측 추출 3함수(`_still_frame_index`/`_ratio_ref_index`/`_extract_comparison_stills`) 완전 삭제 — 근거: 2026-07-05 pod 진단 3회, 위상 불일치 페어 0/6 vs 파이프라인 인덱스 페어 6/6.
- `_cleanup_stills` 제거 — PNG 소유권은 호출자(pair.cleanup_paths finally). Gemini File API 핸들 delete 는 유지.
- `INPUT_GRANULARITY_WHOLE_FANOUT` "whole_fanout_hybrid1" → "whole_fanout_hybrid2" — 인덱스 수치 충돌 stale-hit 구조 차단(90d038f 원칙). 업로드 실패 → fi=None 재키잉 폴백 유지.

### Task 2 — pipeline (RC-01/RC-04)
- `SelectedFramePair.ref_match_source: str = "ratio"` defaulted 필드 신설 ("dtw"=`fault_zoom._matched_ref_frame` 성공 / "ratio"=시간비례 폴백).
- `_build_selected_frame_pair`: `r_matched is not None` → "dtw" 세팅.
- `_collect_vision_fault_context`: pair 존재 + "dtw" 일 때만 still kwargs 전달, 그 외 video-only. `at`/user_frame_idx 산출·PNG unlink finally 순서 무변경. 새 추출 코드 0 (기존 pair 재사용).

### Task 3 — fanout (RC-03)
- `_run_part_frame_fanout`: (scope, repeat) 평탄화 — upper_body + still 핸들 존재 시 2 call(동일 이미지 핸들 재사용, uploadCount=4 불변), planned=4 (MAX_VETO_CALLS=9 내). wall-clock 가드·점수 누출 폐기·parse skip·resource_limited fail-closed(Option A) 무변경.
- per_call = call 당 1 entry 그대로 → upper 2 entries = distinct-call K=2 성립. `_filter_supported_differences` 무접촉.

## Verification

- 4개 스위트 GREEN: test_gemini_vision_scorer(96) + test_pipeline_vision_gate(40) + test_deduction_engine + test_phase25_eval_gates = **229 passed**.
- 제거 완전성: `_extract_comparison_stills|_still_frame_index|_ratio_ref_index|still_at_seconds` backend 전역 0건 (테스트의 부재-assert 3건만 잔존 — 의도된 상태 증명).
- PROMPT_VERSION v11.2 / SCHEMA_VERSION v8.1 / AGGREGATION_VERSION agg4 무변경 (git diff 로 프롬프트/스키마 미접촉 확인).
- 새 튜닝 상수 0 — K=2, MAX_VETO_CALLS=9 등 기존 상수만 사용.

## Deviations from Plan

None - plan executed exactly as written.

(추가 테스트 1건: `test_hybrid_partial_still_kwargs_treated_as_missing` — 계획의 "일부만 제공되면 미제공 취급" 계약을 직접 검증하는 보강, 규칙 변경 아님.)

## Known Stubs

None — 배선 완결. 실효(상체 방출이 실제 pointed set/window 감점으로 이어지는지)는 유닛 스코프 밖, pod 진단/sweep 에서 확인 필요.

## Next

- Pod sweep 으로 실측: DTW-매칭 still 페어 + upper 2-call 이 kip-up 상체(왼팔 그립 major 등) faultKey 를 pointed set 에 올리는지 + success 위양성 0 유지 확인.
- hybrid2 키 공간은 cold — 첫 sweep 은 전 페어 Gemini 재호출(캐시 미스) 예상.

## Self-Check: PASSED

- [x] backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py — FOUND
- [x] backend/shared/python/sunity_shared/analysis/vision_veto.py — FOUND
- [x] backend/functions/pipeline/app.py — FOUND
- [x] Commit a45a7b3 — FOUND
- [x] Commit 98358fd — FOUND
- [x] Commit 1c735e6 — FOUND
- [x] 229 passed (4개 스위트)
