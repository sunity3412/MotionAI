---
phase: 28-dtw-motion-based-alignment
plan: 04
subsystem: motion-alignment (파이프라인 방출 배선 — mode1/mode3 → result.motionAlignment)
tags: [pipeline, motion-alignment, emission, scoring-untouched, dtw, wave-3, graceful]
requirements: [ALGN-01, ALGN-06]
dependency_graph:
  requires:
    - "28-02 (build_motion_alignment 순수 함수 — 이 배선이 호출)"
    - "28-03 (MotionAlignment 계약 3-way + _validate_motion_alignment — 방출 dict 형상 정합)"
    - "27-06 (faultZoomStatus/update_analysis_fault_zoom + complete 후 result.* write 금지 게이트)"
  provides:
    - "_attach_motion_alignment helper — DTW match → result['motionAlignment'] (complete 직전, 채점 무접촉, graceful)"
    - "_pipeline_frame_fps 단일 출처 (I1 — frame_extractor target_fps, 리터럴 9.0 금지)"
    - "mode1 EXPERT + mode3 SELF second+ 방출 배선 (degenerate 도 disabled 로 실림)"
    - "_mode3_comparison 반환에 prev_dtw_match 추가 + mode3 fault_zoom 에 DTW 대응 전달 (28-05 회귀 방지)"
    - "채점 무접촉 deepcopy diff-0 기계 게이트 (ALGN-06) + 상한 lockstep 이동 (B1)"
  affects:
    - "28-05 (mode1/mode3 fault_zoom ratio 근사 제거 — dtw_match 이제 mode3 에도 흐름)"
    - "28-06 (VideoCompare 소비 — 새 분석 doc 의 motionAlignment 를 워핑에 사용)"
    - "28-07 (배너 — legacy 필드 부재 vs degenerate 'disabled' 구분 소비)"
    - "Phase 29 D1 (Mode3 비교영상 — 이 산출물 소비)"
tech_stack:
  added: []
  patterns:
    - "result 안으로 흐른다, 신규 kwarg 없음 (result[key] 추가만 — safetyFlags/timingsMs 선례)"
    - "graceful skip try/except (분석 흐름 차단 0 — 부가 방출 비차단 규율)"
    - "fps 단일 출처 introspection 폴백 (값 재복제 회피 — frame_extractor 기본값 정본)"
    - "complete_analysis 직전 단일 주입 지점 (mode 별 fps 선택 — 27-06 게이트 정합)"
key_files:
  created:
    - backend/tests/test_pipeline_motion_alignment.py
  modified:
    - backend/functions/pipeline/app.py
    - backend/tests/test_pipeline_mode3.py
decisions:
  - "user_fps 단일 출처 = _pipeline_frame_fps() (I1) — _FRAME_EXTRACTOR.target_fps 정본 + 미초기화 폴백은 FfmpegFrameExtractor.__init__ 기본값 introspect (리터럴 9.0 복제 0)"
  - "주입 지점 단일화 — complete_analysis 직전 한 곳에서 mode 별 fps 선택 (mode1=18fps ref doc / mode3=양측 9fps, Pitfall 6). 27-06 게이트(complete 후 result.* write 금지) 정합"
  - "mode3 fault_zoom 심볼은 _build_mode3_fault_zoom_comparisons (플랜의 _attach_mode3_fault_zoom 은 심볼 재탐색으로 정정) — dtw_match kwarg 추가 → _render_fault_zoom(dtw_match=) 전달"
  - "test_pipeline_mode3 6개 언팩을 5-tuple 로 정합 (Rule 3 — _mode3_comparison 시그니처 변경의 필연적 연쇄, 채점 로직 무변경)"
metrics:
  duration_min: 18
  tasks_completed: 3
  files_created: 1
  files_modified: 2
  completed_date: 2026-07-08
---

# Phase 28 Plan 04: 파이프라인 motionAlignment 방출 배선 Summary

28-02 순수 함수(build_motion_alignment)를 파이프라인 `_process` 후반부에 배선해, mode1(정은지 reference_dtw_match + ref doc 18fps)과 mode3 second+(이전 영상 prev_dtw_match + 양측 9fps)의 새 분석 result 에 `motionAlignment` 키를 **complete_analysis 호출 전에** 동승시킨다. 방출의 유일한 부작용이 키 1개 추가임을 deepcopy diff-0 게이트로 기계 증명(ALGN-06)했고, degenerate 입력도 tier 'disabled' 로 실려 legacy(필드 부재)와 구분되며, 방출 실패는 graceful skip 으로 분석을 죽이지 않는다. mode3 fault_zoom 에 prev DTW 대응을 전달해 28-05 의 ratio 근사 제거가 mode3 카드 회귀를 만들지 않게 예방했다.

## 선행 확인 (심볼 기준 — 27-06 게이트)

착수 전 `grep -c "faultZoomStatus\|update_analysis_fault_zoom"` → app.py=7, firestore_admin.py=4 (>0). 27-06 실행 완료 확인 → 착수. (worktree 초기 HEAD 가 wave-2 머지 6f0fda6 — `<worktree_branch_check>` merge-base 로직대로 base 유지, 28-02/28-03 산출물 motion_alignment.py / _validate_motion_alignment / models 상수 존재 확인.)

## What Was Built

### Task 1 — mode1 EXPERT 방출 + _attach_motion_alignment helper (commit 0b23ae6)
- **helper `_attach_motion_alignment(result, match, *, user_fps, ref_fps, uid, analysis_id)`**: `build_motion_alignment` 호출 → dict 면 `result["motionAlignment"] = alignment` (그 외 무변경). match=None → 미방출(legacy). 전체 try/except graceful — 방출 실패 시 `log.exception` 후 통과(분석 비차단). docstring 에 "complete_analysis 전에만 호출 (27-06 게이트)" 박제.
- **`_pipeline_frame_fps()` 단일 출처 (I1)**: `_FRAME_EXTRACTOR.target_fps`(=_ensure_adapters 초기화분) 정본 참조, 미초기화 폴백은 `FfmpegFrameExtractor.__init__` 의 target_fps 기본값 introspect — 리터럴 9.0 복제 0.
- **mode1 배선**: EXPERT 분기에서 `reference_kp_fps = float((((ref or {}).get("keypointReport")) or {}).get("fps") or 0.0)` (28-01 실측 phase4_v1=18fps, 하드코딩 금지). complete 직전 `if mode == MODE_EXPERT:` 에서 `_attach_motion_alignment(result, reference_dtw_match, user_fps=_pipeline_frame_fps(), ref_fps=reference_kp_fps, ...)`. `reference_kp_fps = 0.0` 을 `reference_dtw_match = None` 인접에 초기화(동일 수명). ref fps <=0 이면 build 가 degenerate 'disabled' 방출(W3).

### Task 2 — mode3 second+ 방출 + mode3 fault_zoom prev match 전달 (commit 3bb14aa)
- **`_mode3_comparison` 반환 확장**: 버려지던 `_match` 를 `prev_dtw_match` 로 반환 tuple 5번째 원소에 추가(첫 분석/prev 부재 = None). docstring 반환 절 갱신. 단일 호출부에서 `..., prev_dtw_match = _mode3_comparison(...)` 수령. `prev_dtw_match = None` 을 outer scope 초기화(reference_dtw_match 수명 관리 동형).
- **mode3 방출**: complete 직전 `else: # MODE_SELF` 에서 `_attach_motion_alignment(result, prev_dtw_match, user_fps=_ma_frame_fps, ref_fps=_ma_frame_fps, ...)` — 양측 9fps(prev angles 는 자기 분석의 9fps 저장분, Pitfall 6: mode1 18fps 변환 금지, fps 는 인자). 주입 지점 단일화(mode 별 fps 선택).
- **mode3 fault_zoom 회귀 방지**: `_build_mode3_fault_zoom_comparisons` 에 `dtw_match=None` kwarg 추가 → 내부 `_render_fault_zoom(..., dtw_match=dtw_match)` 전달(kwarg 는 이미 존재) → 호출부에서 `dtw_match=prev_dtw_match`. 주석: 28-05 시간비례 근사 제거(D-04) 대비 전신 폴백 회귀 방지.
- **test_pipeline_mode3 정합 (Rule 3)**: `_mode3_comparison` 6개 언팩을 5-tuple 로 갱신 (`_prev_match` 추가). 시그니처 변경의 필연적 연쇄 — 채점 로직 무변경.

### Task 3 — 채점 무접촉 + graceful + 방출 단위 + 상한 lockstep (commit da01696, TDD)
`test_pipeline_motion_alignment.py` 신설 (7 테스트, dispatch 관례로 app 로드):
- **채점 무접촉 (hard 게이트)**: overallScore/deductionBreakdown 포함 fixture → `_attach_motion_alignment` → `{k:v for k in result if k != 'motionAlignment'} == deepcopy(baseline)` (diff 0). ALGN-06.
- **초 단위 방출**: user 9fps/ref 18fps identity path → anchors max ≤ 구간초+1 (인덱스 2i=34 아님), tier ∈ 3종.
- **degenerate 방출 (W3)**: ref_fps=0 → tier 'disabled' + anchors [].
- **graceful**: build_motion_alignment monkeypatch raise → helper 통과 + result 완전 무변경.
- **미방출**: match=None → motionAlignment 키 부재.
- **validator 정합**: 정상+degenerate 방출 dict 가 `firestore_admin._validate_motion_alignment` raise 없이 통과.
- **상한 lockstep (B1)**: `motion_alignment.MAX_ANCHOR_FLOATS == models.MOTION_ALIGNMENT_MAX_ANCHOR_FLOATS` (28-03 test_motion_alignment_contract.py 에서 이동 — wave-3 안전).

## Verification

- Task 1: `pytest test_pipeline_dispatch.py test_motion_alignment.py` = 22 passed. `_attach_motion_alignment`=2(정의+호출), keypointReport delta=+4(≥+1), `user_fps=9.0` 리터럴=0.
- Task 2: `pytest test_pipeline_mode3.py test_pipeline_dispatch.py test_motion_alignment.py` = 56 passed. `prev_dtw_match`=11(≥3), mode3 fault_zoom `dtw_match=prev_dtw_match` 확인.
- Task 3: `pytest test_pipeline_motion_alignment.py` = 7 passed. `deepcopy`=4(≥1), `MOTION_ALIGNMENT_MAX_ANCHOR_FLOATS`=1(≥1), 154줄(≥60).
- 통합: 7개 관련 파일 = **115 passed**. `git diff --stat` = app.py + test_pipeline_mode3 + test_pipeline_motion_alignment 3파일만.

## Deviations from Plan

None (계획 3태스크 계획대로 실행). 심볼 정정·필연 연쇄 2건 (계획 무변경):
1. **[심볼 정정]** 플랜 Task 2 의 `_attach_mode3_fault_zoom` 은 실제 심볼 `_build_mode3_fault_zoom_comparisons` 로 재탐색·정정(플랜이 "라인 번호 참조는 전부 심볼 기준 재탐색" 명시). dtw_match kwarg 추가 로직은 명세대로.
2. **[Rule 3 — blocking, 연쇄]** `_mode3_comparison` 5-tuple 반환 변경으로 test_pipeline_mode3.py 6개 언팩이 깨짐 → 5-tuple 로 정합(`_prev_match` 추가). 시그니처 변경의 필연적 연쇄, 채점/테스트 의도 무변경. files_modified 프런트매터엔 없으나 현재 태스크 변경이 직접 유발한 blocking 이라 in-scope.

## Notes

- **채점 무접촉 (phase hard 제약):** git diff 범위에 vision_veto.py / kismam.py / dimensions.py / deduction 계열 0. `_build_selected_frame_pair`(veto still 경로, app.py:1720) 무접촉 확인. 방출은 result 키 1개 추가뿐 — deepcopy diff-0 로 기계 증명.
- **27-06 게이트 정합:** 방출은 complete_analysis 호출 **직전** 단일 지점 — complete 후 result.* write 경로 신설 0. 사후 업데이트 경로(update_analysis_fault_zoom)와 분리.
- **의도된 seam (스텁 아님):** 이 방출은 새 분석부터 doc 에 존재(D-05 공급측). legacy doc 은 필드 부재로 남고, 28-06(VideoCompare 소비)/28-07(배너)이 소비한다. UI 로 흐르는 빈 데이터 아님 — degenerate 도 'disabled' tier 로 명시 방출돼 legacy 와 구분.
- **fps 단일 출처 (I1):** _pipeline_frame_fps() 가 frame_extractor 기본 target_fps 를 정본으로 참조. 재처리로 fps 가 바뀌어도 코드 재복제 0.

## Threat Flags

None — 신규 네트워크 엔드포인트/인증/스키마 경계 0. result 에 키 1개 추가(방출) + 기존 함수 시그니처 확장뿐. 방출 dict 는 28-03 validator 가 저장 전 형상 강제.

## Commits

- `0b23ae6` feat(28-04): mode1 motionAlignment 방출 배선
- `3bb14aa` feat(28-04): mode3 second+ 정렬 방출 + prev match를 mode3 zoom에 전달
- `da01696` test(28-04): 채점 무접촉 + graceful + 방출 단위 + 상한 lockstep

## Self-Check: PASSED

- 신규 파일 test_pipeline_motion_alignment.py + SUMMARY 존재 (아래 자동 검증).
- 커밋 3개 (0b23ae6 / 3bb14aa / da01696) 존재 확인.
- 채점 경로(vision_veto/kismam/dimensions/_build_selected_frame_pair) diff 0 확인.
