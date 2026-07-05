---
phase: quick-260705-g1d-vision-upper-scope-still-frame-hybrid
plan: 01
subsystem: backend-analysis (gemini vision veto)
tags: [gemini, vision, hybrid-granularity, kip-up, upper-body, cache-key]
requires:
  - quick-260705-fmg (PROMPT v11.2 part_scope 배타 강제)
  - Phase 24 close-out A (full-video fanout, whole_fanout 키)
provides:
  - vision fanout 하이브리드 granularity — upper_body scope 만 worst-pose 정지 이미지 페어 입력
  - INPUT_GRANULARITY_WHOLE_FANOUT = "whole_fanout_hybrid1" (새 캐시 키 공간)
  - telemetry.upperGranularity ("still_frame" | "video_fallback") 관측점
affects:
  - backend/functions/pipeline/app.py (_collect_vision_fault_context 호출부)
tech-stack:
  added: []
  patterns:
    - scope 별 media_kind 분기 (_call_gemini_comparison media_kind="image")
    - frame_indices folding 으로 폴백 결과의 키 공간 구조 분리 ('fi-' bucket)
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py
    - backend/functions/pipeline/app.py
    - backend/tests/test_gemini_vision_scorer.py
key-decisions:
  - "레버는 granularity, NOT 프롬프트 — v11.1/v11.2 프롬프트 라운드 소진(상체 방출 0/6) 후 2026-06-22 스파이크 실증(정지프레임=팔 복구)에 따라 upper_body scope 만 정지 이미지로 전환"
  - "PROMPT/SCHEMA/AGGREGATION_VERSION 무 bump — 이미지-모드 문구는 whole_fanout_hybrid1 키 공간에서만 발생, 기존 키와 절대 안 섞임"
  - "이미지 업로드 실패 시 키를 'fi-' bucket 으로 재산출 — 폴백(전-scope video) 결과가 still-키 공간을 오염하지 않게 (90d038f stale-hit 이력 방어, plan (4) frame_indices 분리 근거의 연장)"
metrics:
  completed: 2026-07-05
  tasks: 2
  commits: 2
---

# Quick 260705-g1d: vision upper scope still-frame 하이브리드 Summary

**One-liner:** vision fanout 을 하이브리드 granularity 로 전환 — upper_body scope 호출만 학생/기준 worst-pose 정지 이미지 페어(media_kind="image")를 입력받고 lower_body/line 은 full-video 유지, 캐시 키는 whole_fanout_hybrid1 로 bump 해 옛 키 공간과 구조적 분리.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | gemini_vision_scorer 하이브리드 granularity — 정지프레임 helper + upper scope 분기 + 캐시 키 bump | c81a18c | gemini_vision_scorer.py |
| 2 | pipeline 배선 + 하이브리드 유닛 테스트 | 08c1698 | functions/pipeline/app.py, tests/test_gemini_vision_scorer.py |

## What Changed

- `INPUT_GRANULARITY_WHOLE_FANOUT` 값 `"whole_fanout"` → `"whole_fanout_hybrid1"` (상수명 유지, 참조부 무변경). PROMPT v11.2 / SCHEMA v8.1 / agg4 무변경.
- 순수 helper `_still_frame_index` (None → 중앙, clamp) + `_ratio_ref_index` (fault_zoom 시간비례 공식 동일) — IO 없음, 결정적.
- IO helper `_extract_comparison_stills`: imageio 로 두 영상 각 1프레임 → 임시 PNG 2장. count_frames 우선, inf/실패 시 메타데이터(duration*fps) 폴백, 불가 시 raise (폴백 판단은 호출자).
- `assess_fault_context_video(still_at_seconds=None)` kw 추가: 추출 성공 시 build_key 에 `frame_indices=[student_idx, ref_idx]` folding, 실패 시 `fi-` bucket. 이미지 업로드는 별도 try — 실패 시 upper scope 만 video 폴백 + 키 재산출(`fi-`) + 폴백 키 재조회. finally 에서 핸들 4개 delete + 임시 PNG unlink. MAX_VETO_UPLOADS=4 정합 (2 video + 2 image).
- `_run_part_frame_fanout(upper_still_handles=None)`: upper_body + handles 존재 → 이미지 핸들 + `media_kind="image"`, 그 외 video 핸들 + 기본값. telemetry `upperGranularity`/`uploadCount(4|2)`. fail-closed/support 게이트/median severity 무변경.
- `_call_gemini_comparison(media_kind="video")`: "image" 일 때만 contents 라벨 "기준(정타)/평가 대상(학생) 정지 이미지:" + 프롬프트 끝 이미지-모드 정합 문구(영상 구간 탐색 지시 무시, 자세끼리 비교). default "video" 경로는 라벨/프롬프트 byte-동일 (기존 캐시 무효화 0). v11.2 배타 블록은 image 모드에도 그대로 적용.
- pipeline `_collect_vision_fault_context`: `still_at_seconds=at` (기존 `at = vision_veto.worst_pose_timestamp(profile)` 재사용). `at_seconds=None` 유지 (Phase 24 close-out A). runpod_inference/server.py 는 pipeline `_process` 재사용 — 변경 0 확인.

## Verification

- 제약 검증 세트: `PYTHONPATH=shared/python:. python3 -m pytest tests/test_gemini_vision_scorer.py tests/test_pipeline_vision_gate.py tests/test_deduction_engine.py tests/test_phase25_eval_gates.py -q` — **223 passed** GREEN.
- test_gemini_vision_scorer.py 단독: 93 passed (기존 86 + 신규 7: 순수 helper 2, upper 분기 라우팅, 추출 실패 폴백, cold/warm 결정론+키 공간, media_kind 라벨, 업로드 실패 재키).
- backend 전체 스위트 (`PYTHONPATH=shared/python:.:..:tests pytest tests/`): 57 failed / 2425 passed — **base 커밋(74689eb) 동일 조건 실측과 실패 집합 동일** (57 failed / 2418 passed, +7 = 신규 테스트). 실패 전부 pre-existing 환경/경로 의존 (`pytest.importorskip("app")` 해석, spike/smoke 모듈 경로) — 이번 변경과 무관, 회귀 0.
- 채점 경로 diff 0: 변경 파일은 frontmatter files_modified 3개뿐 (`git diff 74689eb --stat` 확인). _filter_supported_differences / deduction 라우팅 / severity 규칙 무접촉.
- 캐시 키: 신규 키에 `whole_fanout_hybrid` + `fi12_10` 직렬화 포함, 동일 인자 옛 `whole_fanout` 키와 불일치 단언 (stale-hit 0).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - 캐시 오염 방어 보강] 이미지 업로드 실패 시 캐시 키 재산출**
- **Found during:** Task 1
- **Issue:** plan (4)는 "추출 실패 시 frame_indices=None → 'fi-' bucket" 만 명시 — 추출 성공 후 **업로드** 실패 케이스는 키가 이미 still-인덱스로 산출된 뒤라, 폴백(전-scope video) 결과가 still-키 공간에 저장돼 다음 성공 run 의 still 결과와 섞일 수 있었다 (plan 자체의 오염-분리 근거와 모순).
- **Fix:** 업로드 실패 시 `frame_indices=None` 으로 키 재산출 + 폴백 키 lookup_rich 재조회 후 진행.
- **Files modified:** gemini_vision_scorer.py
- **Commit:** c81a18c

### 실행 중 사고 (회복 완료)

- 전체 스위트 실패가 pre-existing 임을 증명하려 base 파일을 `git checkout 74689eb -- <3 files>` 로 임시 체크아웃 후 `git checkout HEAD -- <files>` 복원했는데, 당시 Task 2 변경분(pipeline 배선 + 테스트)이 미커밋 상태라 **덮어써 유실** → 컨텍스트에 보존된 동일 내용으로 즉시 재적용, 검증 세트 223 passed 재확인 후 커밋. 최종 산출물 영향 0.

## Known Stubs

None — 하드코딩 빈 값/placeholder 0. 폴백 경로는 스텁이 아니라 명세된 graceful degradation.

## Threat Flags

None — plan threat_model 과 일치: T-g1d-01(이미지 핸들 delete + PNG unlink 확장) / T-g1d-02(키 bump + frame_indices folding) 둘 다 구현. 새 네트워크 표면/패키지 0.

## PENDING (pod 실효 검증)

**유닛 테스트는 배선 정확성만 증명한다.** 실효 — kip-up fault 페어에서 upper_body scope 가 실제로 상체(어깨) 편차를 differences[] 로 방출하는지 — 는 pod 격리 진단 + sweep 으로 후속 확인 필요:
1. pod 에서 kip-up fault 영상 fresh 진단 (`upperGranularity=="still_frame"` telemetry 확인)
2. 6-pair sweep — success 100 유지 + 짚기-FP 0 게이트 + kip-up fault 상체 감점 발생 여부
3. 캐시는 `whole_fanout_hybrid1` 신규 키 공간이라 poisoned 엔트리 우회 자동

## Self-Check: PASSED

- [x] backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py — FOUND (contains `whole_fanout_hybrid`)
- [x] backend/functions/pipeline/app.py — FOUND (contains `still_at_seconds`)
- [x] backend/tests/test_gemini_vision_scorer.py — FOUND (hybrid 테스트 7종)
- [x] commit c81a18c — FOUND
- [x] commit 08c1698 — FOUND
- [x] 검증 세트 223 passed GREEN
