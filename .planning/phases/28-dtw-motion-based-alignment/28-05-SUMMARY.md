---
phase: 28-dtw-motion-based-alignment
plan: 05
subsystem: motion-alignment (fault_zoom 표시 경로 fps 정합 + ratio 근사 제거 + refMatch end-to-end)
tags: [fault-zoom, dtw, fps-domain, ref-match, d-04, high-1, display-only, scoring-untouched, tdd, wave-4]
requirements: [ALGN-03, ALGN-06]
dependency_graph:
  requires:
    - "28-01 (reference fps 18fps 실측 + anglesFrames==keypointReport.frames 정합 — clamp 도메인 근거)"
    - "28-03 (FaultZoomComparison.refMatch 계약 3-way lockstep — 방출 dict 형상 정합)"
    - "28-04 (app.py 소유권 + mode3 prev_dtw_match 배선 — dtw_match 가 이제 mode1/mode3 양쪽에 흐름)"
    - "27-06 (update_analysis_fault_zoom post-complete zoom 경로 — mapper 심볼 선행 확인)"
  provides:
    - "DTW 성공 경로 fps 정합 — ref angles(rep) 인덱스를 _to_rep_idx 역변환으로 9fps frames 인덱스로 내림 (D2 2배 오독 종결)"
    - "ratio 시간비례 근사 제거 → 대응 실패 시 ref 전신 폴백 + refMatch='failed' (D-04 오도 0)"
    - "refMatch scalar 가 build_fault_zoom_comparisons → _render_fault_zoom mapper → 반환 comparisons 까지 생존 (HIGH-1)"
  affects:
    - "28-07 (refMatch='failed' 캡션 렌더 — 이제 Firestore doc 까지 refMatch 도달 보장)"
    - "28-08 (end-to-end 검사 — mapper 생존이 여기서 늦게 터지지 않음)"
tech_stack:
  added: []
  patterns:
    - "표시 경로 전용 fps 도메인 변환 (호출측 교정, _matched_ref_frame 본체 무변경 — veto still 점수 인접 보호)"
    - "중복 공식 금지 — rep→frames 역변환도 _to_rep_idx 재사용(fps 인자 순서만 반대, quick-260705-ftn)"
    - "정직한 실패 = 전신 폴백 + provenance scalar (260702-sic confidence<0.5 전신 폴백과 일관)"
    - "mapper 조건부 pass-through (region 선례) + sys.modules 스텁으로 imageio 미설치 우회 mapper-level 테스트"
key_files:
  created:
    - backend/tests/test_fault_zoom_ref_match.py
  modified:
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/functions/pipeline/app.py
    - backend/tests/test_fault_zoom_relaxed_crop.py
decisions:
  - "clamp 도메인 = r_rep_frames(ref angles/keypointReport 프레임 수), r_n(9fps frames 수) 아님 — _matched_ref_frame 반환이 ref angles 공간(phase4_v1=18fps)이라 (28-01 실측). r_rep_frames<=0 이면 DTW 분기 자체를 실패 취급"
  - "대응 실패(r_matched is None / r_rep_frames<=0 / dtw_match=None) → ref_match_failed=True → 루프에서 r_valid/r_relaxed 를 강제 [] 로 넘겨 _side_crop 3단 강하의 전신 폴백 직행(새 렌더 금지). ref 프레임 = r_n//2 중앙(전신이라 어느 순간이든 오도 0). 학생 카드는 무변경 유지"
  - "override(ref_frame_idx) 경로 = vision 측정 프레임 정합 보장 → refMatch='dtw' 취급"
  - "_render_fault_zoom 가 유일 mapper — mode3(_build_mode3_fault_zoom_comparisons)도 이를 재사용하므로 pass-through 1곳으로 mode1/mode3 모두 커버. 27-06 이후 mapper 는 result 부착이 아니라 comparisons list 반환(호출측이 update_analysis_fault_zoom) — 플랜의 'result[faultZoomComparisons][0].refMatch' 는 반환 comparisons[0].refMatch 로 매핑"
metrics:
  duration_min: 24
  tasks_completed: 2
  files_created: 1
  files_modified: 3
  completed_date: 2026-07-08
---

# Phase 28 Plan 05: fault_zoom fps 정합 + ratio 근사 제거 + refMatch end-to-end Summary

파일럿 D2("정은지 쪽이 비교 부위 아닌 곳 확대")의 두 메커니즘을 한 몸으로 종결했다. (1) DTW "성공" 경로가 ref angles(18fps) 인덱스를 9fps frames 배열에 그대로 인덱싱하던 2배 시간 오독을 `_to_rep_idx` 역변환으로 잡고, (2) 대응 실패 시 어느 pose 인지 모르는 채 시간만 맞추던 ratio 시간비례 근사를 제거해 ref 전신 폴백 + `refMatch='failed'` 캡션 플래그로 대체했다. 그리고 (3) HIGH-1: refMatch scalar 가 `build_fault_zoom_comparisons` 방출만으로는 app.py `_render_fault_zoom` mapper 에서 버려지던 것을 조건부 pass-through 로 최종 comparisons list 까지 생존시켰다. `_matched_ref_frame` 본체와 veto still 경로(`_build_selected_frame_pair`)는 무접촉 — 점수 이동 0.

## 선행 확인 (심볼 기준 — 27-06 게이트)

착수 전 `grep -c "def update_analysis_fault_zoom" firestore_admin.py` = 1 (>= 1) 확인 → 27-06 실행 완료, 착수. (worktree base = wave-3 머지 61ffe12, 28-01/28-03/28-04 산출물 — reference fps 18fps 실측, refMatch 계약, mode3 prev_dtw_match 배선 — 전부 존재 확인.)

## What Was Built

### Task 1 — DTW 성공 경로 fps 정합 (표시 경로 전용 변환, TDD `2a23ff2`→`c9330fd`)

`build_fault_zoom_comparisons` 의 DTW 분기 **호출측**만 교정 (`_matched_ref_frame` 본체 무수정):
- clamp 도메인 교정: 세 번째 인자를 `r_n`(9fps frames 수) → `r_rep_frames`(ref angles/keypointReport 프레임 수 = 18fps 도메인, 28-01 실측 `anglesFrames==keypointReport.frames`)로 교체. `r_rep_frames<=0`이면 DTW 분기를 실패 취급.
- 반환값 도메인 변환: `r_matched`는 ref angles(rep) 인덱스이므로 `r_kp_idx = r_matched`(추가 변환 불필요), `r_idx = _to_rep_idx(r_matched, r_rep_fps, frames_fps, r_n)` — 같은 공식에 fps 인자 순서만 반대인 rep→frames 역변환(중복 공식 금지 관례).
- `_matched_ref_frame` docstring 정정: "ref_idx = 기준 angles 9fps 절대" → "ref doc keypointReport.fps 공간(phase4_v1=18fps), 호출측이 clamp/frames 변환 책임, 본체 수정 금지(veto still 공유)". 로직 무변경.

RED 가드 3종(합성 red-channel 프레임으로 ref crop 출처 프레임 식별): 18fps→9fps 변환(u_idx=6→ref frames 6, 구 코드=90), 9fps identity(mode1 하드코딩 부재 증명 — Pitfall 6), clamp 도메인=r_rep_frames(angles 15 미클램프→frames 8, 구 코드=90).

### Task 2 — ratio 근사 제거 + 전신 폴백 + refMatch 방출·mapper pass-through (D-04, HIGH-1, TDD `0b45787`→`ec23ec2`)

- **fault_zoom.py**: ratio 근사 else 블록(`ratio * (r_n - 1)` / `ratio * (r_rep_frames - 1)`) 삭제. 대응 실패 시 `ref_match_failed=True` + `r_idx=r_n//2`(중앙 전신). 루프에서 `ref_match_failed` 이면 `r_valid, r_relaxed = [], []` 강제 → `_side_crop` 이 기존 좌표-결측 전신 폴백 분기로 직행(새 렌더 금지). 방출 item 에 `"refMatch": "failed" if ref_match_failed else "dtw"` scalar 추가(region 선례 형식). docstring 의 "시간비례(ratio)로 근사" 서술 → "대응 실패 = ref 전신 폴백 + refMatch='failed'" 로 갱신.
- **app.py `_render_fault_zoom` (HIGH-1)**: 재조립 루프의 region pass-through 직후 `if c.get("refMatch") in ("dtw", "failed"): item["refMatch"] = c["refMatch"]` 검증 복사 추가. **`_render_fault_zoom` 가 유일 mapper 임을 심볼 재탐색으로 확인** — mode3(`_build_mode3_fault_zoom_comparisons`)도 이를 재사용하므로 이 1곳으로 mode1/mode3 모두 커버(별도 mapper 없음). 27-06 이후 mapper 는 result 부착이 아니라 comparisons list 를 반환(호출측이 `update_analysis_fault_zoom` 로 사후 부착)하므로, 생존 단언은 반환 comparisons 에 대해 수행.
- **mapper-level 테스트(HIGH-1)**: pipeline app 로드 후 `_s3`/`_signed_get` 스텁 + `build_fault_zoom_comparisons` monkeypatch. `frame_extractor` 실모듈은 imageio(테스트 환경 미설치)를 top-import 하므로 가짜 모듈을 `sys.modules` 에 주입 — `_render_fault_zoom` 내부 lazy `from ...frame_extractor import FfmpegFrameExtractor` 가 스텁을 집는다(체커 3회차 WARNING-1 대응). refMatch='failed'/'dtw' 각 생존 + refMatch 미포함 legacy 카드 → 최종 item 키 부재 단언.

## Verification

- fault_zoom 3파일(ref_match/fault_zoom/relaxed_crop) = **60 passed**.
- 플랜 verify 게이트: 위 테스트 GREEN + 주석 제외 `ratio * (r_n - 1)` grep 0 + `git diff app.py` 의 `_build_selected_frame_pair` grep 0 → **RATIO_REMOVED_MAPPER_SAFE** 출력.
- acceptance grep: `refMatch` fault_zoom.py=3(방출+docstring+주석), app.py=4(pass-through+주석) — 각 >= 하한.
- 좁은 안전 게이트: `git diff -U0 app.py` hunk = `_render_fault_zoom`(:2814) 1곳만 — `_build_selected_frame_pair`(:1836) 무접촉. vision_veto.py 0.
- 회귀: 관련 pipeline 테스트(test_pipeline_mode3 / test_fault_zoom_deferred / test_pipeline_dispatch / test_pipeline_motion_alignment) = **59 passed**.

## Deviations from Plan

### Rule 3 (blocking, 필연 연쇄) — relaxed_crop 4테스트에 identity dtw_match 보강

**Found during:** Task 2 (ratio 제거 후 회귀 확인)
**Issue:** `test_fault_zoom_relaxed_crop.py` 의 4테스트(`test_build_ref_low_conf_cards_differ_by_joint`, `test_build_ref_low_conf_finite_is_crop_not_full`, `test_build_relaxed_user_side_no_circle`, `test_build_full_user_side_no_circle`)가 `dtw_match=None` 으로 build 를 호출하면서 **구 ratio 근사가 우연히 유효한 ref 프레임 인덱스를 준 것에 의존**해 ref crop 계층(relaxed/full/부위 차별화)을 검증하고 있었다. D-04 계약 변경(dtw_match=None → ref 전신 폴백 + refMatch='failed')으로 ref 좌표가 강제 skip 되면서 4테스트가 깨짐(카드 소멸 또는 전신 흰 패딩).
**Fix:** 각 테스트에 identity `dtw_match=_Match(start=0, path=[(i,i) for i in range(9)])` 를 넘겨 기준 프레임 대응을 세워, 원래 검증 의도(crop 계층 동작)를 그대로 유지. 모듈 상단에 `_Match` dataclass + `_IDENTITY9` 상수 + 근거 주석 추가. 테스트 의도·프로덕션 로직 무변경.
**Files modified:** backend/tests/test_fault_zoom_relaxed_crop.py
**Commit:** ec23ec2 (Task 2 GREEN 에 포함)
**선례 정합:** 28-04 가 `_mode3_comparison` 5-tuple 변경으로 test_pipeline_mode3.py 6개 언팩을 정합시킨 것과 동형(시그니처/계약 변경의 필연적 테스트 연쇄).

## Notes

- **채점 무접촉 (phase hard 제약):** `_matched_ref_frame` 본체 diff = docstring-only. veto still 경로 `_build_selected_frame_pair` 무접촉(diff grep 0). fps fix 는 fault_zoom 내부 **호출측**에만(표시 경로 전용, 28-RESEARCH Open Q2). app.py 변경은 zoom mapper `_render_fault_zoom` 1 hunk 한정. vision_veto/kismam/dimensions/deduction 계열 0.
- **stale 라인 참조 정정:** 플랜의 `_render_fault_zoom` 재조립 루프 라인(:2625-2642)은 27-06 이전 기준 — 실제 심볼은 :2689 정의, 재조립 루프 :2792-2814. 심볼 재탐색으로 정정(플랜 "라인 번호는 심볼 기준 재탐색" 명시 준수).
- **의도된 seam (스텁 아님):** refMatch='failed' 캡션 렌더는 28-07 소관. 이 플랜은 공급측(방출+생존)까지 — refMatch scalar 가 Firestore doc 까지 도달함을 mapper-level 테스트로 증명. 빈 데이터 UI 스텁 아님.

## Threat Flags

None — 신규 네트워크 엔드포인트/인증/스키마 경계 0. 표시 경로 전용 fps 변환 + refMatch scalar 1개 추가(28-03 validator 가 저장 전 형상 강제). 채점/veto 경로 무접촉.

## Commits

- `2a23ff2` test(28-05): DTW 성공 경로 fps 정합 RED
- `c9330fd` fix(28-05): DTW 성공 경로 fps 정합 — ref angles→9fps frames 역변환 (D2)
- `0b45787` test(28-05): ratio 근사 제거 + refMatch 방출·mapper 생존 RED (D-04, HIGH-1)
- `ec23ec2` fix(28-05): ratio 근사 제거 + ref 전신 폴백 + refMatch 방출·mapper pass-through

## Self-Check: PASSED

- 신규 파일(test_fault_zoom_ref_match.py) + 수정 파일(fault_zoom.py / app.py) + SUMMARY 존재 확인.
- 커밋 4개(2a23ff2 / c9330fd / 0b45787 / ec23ec2) 존재 확인.
- 채점 경로(_matched_ref_frame 본체 / _build_selected_frame_pair / vision_veto) diff 0 확인.
