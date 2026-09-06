---
phase: quick-260906-f4j
plan: 01
subsystem: analysis-display
tags: [fault_zoom, pose_collapse, gated-card, zoom-compare, pipeline, pytest]

# Dependency graph
requires:
  - phase: quick-260810-ms2 / quick-260810-e4v
    provides: pose_collapse 단일 출처 판정, _MOMENT_ANCHOR_RADIUS_WIDE(=4), 창 승급 블록
  - phase: quick-260813-fxx / quick-260813-nh4
    provides: display_anchor(freeze-순간 단일 출처), align_bake 폴백 payload
  - phase: quick-260903-upx
    provides: gated(멈춤 상속) 카드 호출부 _run_gated_card_inherit
provides:
  - fault_zoom._frame_usable — 성한 프레임(비붕괴 AND 그릴 수 있음) 판정 단일 함수 (창 승급과 gated 이동이 공유)
  - fault_zoom.nearest_usable_frame — 붕괴 앵커를 ±4 안 가장 가까운 성한 프레임으로 옮기는 순수 함수 (kept/moved/stuck)
  - _run_gated_card_inherit 배선 — u9/r9 를 build_fault_zoom_comparisons 직전에 양측 독립으로 옮김 + 로그 1행 + freeze-순간 payload 정합
  - backend/tests/test_gated_frame_skips_collapse.py — 실측 fixture 양방향 테스트 10 + 배선 source 단언 4
affects: [zoom-compare cards, audit_card_photos, next Pod live verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "성한 프레임 판정은 _frame_usable 한 곳 — 붕괴만 보면 그릴 수 없는 프레임으로 간다(p34fresh1786349646)"
    - "gated 경로의 프레임 보정은 호출부에서 순수 함수로, 파이프라인은 얇게(판정·반경은 fault_zoom 소유)"
    - "프레임을 옮기면 그 순간의 좌표 payload(display_anchor/align_bake[side])는 정의상 무효 — 떨군다"

key-files:
  created:
    - backend/tests/test_gated_frame_skips_collapse.py
  modified:
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/functions/pipeline/app.py

key-decisions:
  - "트리거는 붕괴만(is_collapsed_frame) — 비붕괴인데 그릴 수 없는 앵커는 align_bake 폴백(nh4)이 소유, 트리거를 넓히면 m0k A/B 소생 6/6 인증 경로가 바뀐다"
  - "반경은 새 상수 없이 _MOMENT_ANCHOR_RADIUS_WIDE(4) 재사용 — ±8 이 14/14 이지만 ms2 '항상 넓히면 악화' 교훈 위에서 belle 지목 카드가 ±4 에서 구제"
  - "u9/r9 교체·payload 떨굼은 status=='moved' 로 판정(값 비교가 아니라) — nearest_usable_frame 이 앵커를 클램프하므로 범위 밖 kept 앵커가 display_anchor 를 억울하게 잃지 않게"
  - "stuck 도 로그에 남긴다 — '앵커 붕괴인데 ±4 안에 성한 프레임 없음'이 사후 판별의 핵심 흔적"

patterns-established:
  - "source 단언 테스트로 배선 범위를 고정(app.py 비주석 nearest_usable_frame( == 2, gated body 안, build 직전) — stage-1·advisory 무접촉을 기계가 지킨다"

requirements-completed: [quick-260906-f4j]

# Metrics
duration: 5min
completed: 2026-09-06
---

# Quick 260906-f4j: gated 카드 붕괴 프레임 배제 Summary

**gated(멈춤 상속) 카드의 앵커 프레임이 붕괴면 ±4 안 가장 가까운 성한 프레임으로 옮긴다 — 08-10 붕괴 방어가 구조적으로 도달 못 하던 경로(dtw_match=None + at_frame_idx=None)에 순수 함수 `nearest_usable_frame` 을 호출부에서 배선, 판정은 창 승급과 같은 `_frame_usable` 한 개, 새 상수 0, 전체 pytest 4669/0/20.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-09-06T02:07:41Z
- **Completed:** 2026-09-06T02:12:59Z
- **Tasks:** 2/2
- **Files modified:** 3 (+352 / -8)

## Accomplishments

- `fault_zoom._frame_usable(report, idx, members, frames_fps, rep_fps, rep_frames)` — "쓸 수 있는 프레임 = 그릴 수 있음(_member_pts valid) AND 비붕괴(pose_collapse 단일 출처)". 창 승급 블록(ms2)의 인라인 공식을 이 함수 호출로 교체(순수 추출). 비주석 등장 3곳(정의·창 승급·nearest_usable_frame).
- `fault_zoom.nearest_usable_frame(report, frame_idx, members, *, n_frames, frames_fps=9.0, radius=_MOMENT_ANCHOR_RADIUS_WIDE) -> (idx, "kept"|"moved"|"stuck")` — 트리거는 붕괴만, −d 를 +d 보다 먼저 보므로 동점은 작은 인덱스, 범위 밖 후보는 스킵, 못 찾으면 fail-open. docstring 에 09-06 실측(42패널/붕괴 14 전부 gated/±2 10·±4 11·±8 14/반사실 악화 0)과 기전 박제.
- `app.py _run_gated_card_inherit`: `r9 = _override_idx(...)` 직후·`comps = _fz.build_fault_zoom_comparisons(` 직전에 양측 독립 호출. moved 측만 u9/r9 교체, `display_anchor=None`(both-or-neither), 옮긴 측 `align_bake[side]={}`. `suppress`·stage-1(3488)·advisory(3531)·채점·방출 필드·conf 임계 무접촉 — app.py diff 는 5334행 단일 삽입 hunk(+52) 뿐.
- 로그 1행 `fault_zoom_gated_frame_shift analysis_id=%s rid=%s user=%d->%d(%s) ref=%d->%d(%s) display_anchor=%s` — moved·stuck 일 때만, 둘 다 kept 면 침묵(종전 로그 byte-동일). 로컬 logging 렌더 확인: `fault_zoom_gated_frame_shift analysis_id=p34fresh1786349646 rid=R:abc user=61->57(moved) ref=122->122(kept) display_anchor=dropped`.

## Task Commits

1. **Task 1 (RED): 실패 테스트** — `e0a0fd15` (test) — 10건 전부 `AttributeError: no attribute '_frame_usable'` 로 실패 확인 후 커밋
2. **Task 1 (GREEN): fault_zoom 순수 함수 + 판정 공유** — `89065231` (fix)
3. **Task 2: gated 호출부 배선 + 로그 + payload 정합 + source 단언 + 전체 게이트** — `bf250cc6` (fix)

**Plan metadata:** 오케스트레이터가 docs 커밋 (SUMMARY/STATE/PLAN 은 이 실행에서 커밋하지 않음)

## Files Created/Modified

- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` (+91/−8) — `_frame_usable`(`_drop_collapsed` 아래), 창 승급 블록 교체(+주석 1줄), `nearest_usable_frame`(`_MOMENT_ANCHOR_RADIUS_WIDE = 4` 직후)
- `backend/functions/pipeline/app.py` (+52) — `_run_gated_card_inherit` unit 루프, u9/r9 산출 직후 삽입 블록
- `backend/tests/test_gated_frame_skips_collapse.py` (신규 217행) — 실측 fixture(`test_select_frame_skips_collapse.py` 의 `_report`/`_mk` 복사) 양방향 10 + 배선 source 단언 4

## Verification (성립시킨 행위)

| 판정 | 실행한 것 | 출력 |
|------|-----------|------|
| RED | `.venv/bin/python -m pytest -q tests/test_gated_frame_skips_collapse.py` (구현 전) | `10 failed` (AttributeError) |
| Task 1 타깃 6파일 | `pytest -q tests/test_gated_frame_skips_collapse.py tests/test_fault_zoom_record_moment.py tests/test_pose_pair_skips_collapse.py tests/test_fault_zoom_display_repair.py tests/test_select_frame_skips_collapse.py tests/test_pose_collapse.py` | `67 passed` |
| 판정 단일화 | `grep -v '^\s*#' fault_zoom.py \| grep -c "_frame_usable("` / `grep -c "^_MOMENT_ANCHOR_RADIUS_WIDE"` | `3` / `1` |
| 창 승급 인라인 잔존 | 승급 블록 구간에서 `[0]$` 패턴 grep | `0` |
| Task 2 컴파일·범위 | `py_compile functions/pipeline/app.py` / 비주석 `nearest_usable_frame(` 수 | OK / `2` |
| app.py diff 범위 | `git diff -U0 functions/pipeline/app.py \| grep '^@@'` | `@@ -5333,0 +5334,52 @@` (단일 삽입 hunk) |
| 신규 파일 단독 | `pytest -q tests/test_gated_frame_skips_collapse.py` | `14 passed` |
| **전체 게이트(rtk 없이)** | `cd backend && .venv/bin/python -m pytest -q` | **`4669 passed, 20 skipped` (failed 0, 46.93s)** = 기준선 4655 + 신규 14 |
| 삭제 검사 | `git diff --diff-filter=D --name-only HEAD~3 HEAD` | (없음) |

## Decisions Made

- **status 기반 교체.** 플랜 문구는 `u9_new != u9 or r9_new != r9` 였으나 `nearest_usable_frame` 이 앵커를 `n_frames-1` 로 클램프하므로 `_override_idx` 가 범위 밖 값을 줬을 때 "kept" 인데도 값이 달라져 `display_anchor` 를 억울하게 잃는다. 비붕괴 앵커 byte-동일 보장을 지키기 위해 `u_why == "moved"` / `r_why == "moved"` 로 판정하고, kept/stuck 은 원값 그대로 넘긴다(클램프는 build_fault_zoom_comparisons 가 종전대로).
- **`display_anchor` 태그 3종** `dropped`(있었는데 떨굼) / `absent`(원래 없음) / `kept`(안 옮김) — 플랜의 "구분 필요하면 absent" 채택. 사후 로그에서 fxx 경로 카드였는지 바로 읽힌다.
- **로그 시점 = 교체 전.** 처음 작성본은 `u9 = u9_new` 를 먼저 하고 로그에서 조건식으로 원값을 되살리려 해 moved 측 "from" 값이 소실됐다 — 로그를 교체 앞으로 옮겨 `user=A->B` 가 실제 원값→새값을 찍게 했다(커밋 전 발견·수정, 커밋 이력에는 수정본만).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 교체 조건을 값 비교에서 status 비교로**
- **Found during:** Task 2 (배선)
- **Issue:** `nearest_usable_frame` 의 클램프 때문에 범위 밖 kept 앵커가 `u9_new != u9` 를 참으로 만들어 `display_anchor` 가 떨어지고 kept 인데 값이 바뀜 — "비붕괴 앵커 byte-동일" 진실 위반
- **Fix:** `u_why == "moved"` / `r_why == "moved"` 로 판정, 그 측만 교체
- **Files modified:** backend/functions/pipeline/app.py
- **Verification:** source 단언 + 전체 게이트 4669/0/20
- **Committed in:** bf250cc6

---

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** 플랜 의도(옮긴 카드만 payload 정합, 비붕괴 byte-동일) 그대로. 범위 확장 0.

## Issues Encountered

None — 플랜 관측 4번(rtk 부분 배치 imageio_ffmpeg 아티팩트)은 전체 실행으로 회피, 재현되지 않음.

## 라이브 미검증 — 다음 Pod 실증 절차

**이 quick 의 게이트는 pod-free 테스트까지다. 배선이 실제 분석에서 돈 실행 로그는 아직 없다** (wiring-claims-need-log-evidence). Pod 는 시연 때만(belle 08-28) — 이 quick 에서 띄우지 않았다.

다음 Pod 세션에서:
1. 09-03 라이브 6문서(fixture) 재분석.
2. 로그 회수: `grep fault_zoom_gated_frame_shift` — 붕괴 14패널 중 **≥11 moved** 기대(±4 구제 11/14 실측), 나머지 `stuck`. 두 상태 모두 로그 1행. 둘 다 kept 인 카드는 로그 없음(정상).
3. `backend/scripts/audit_card_photos.py --pairs …` 재감사 — mismatched **7 → 감소**, 신규 불일치 **0** 이 실증. 특히 belle 09-05 지목 팔꿈치 카드(±4 에서 구제되는 케이스)가 제목 부위로 이동했는지.
4. 옮긴 카드에서 `display_anchor=dropped` 인 것은 양측 rep12 vertex 경로로 그려졌는지(fxx 이전 동작) 사진으로 확인.

## Known Stubs

None — 하드코딩 빈 값·placeholder 없음. 빈 dict 대입(`align_bake[side] = {}`)은 "그 측 폴백 없음"이라는 fault_zoom 계약값이지 스텁이 아니다.

## Threat Flags

None — 새 네트워크 경로·auth·파일 접근·스키마 변경 0. 로그는 analysis_id·recordId·정수 인덱스·status 문자열만(플랜 T-f4j-03 그대로).

## Next Steps

- 다음 Pod: 위 라이브 실증 절차 → 로그·재감사 결과를 `.planning/CONTINUE-*.md` 착수점에 반영.
- 실증에서 stuck 이 3건(±8 에서만 구제되는 실측분)으로 나오면 반경 승급 논의는 **그 로그를 근거로** 별도 quick — 이 quick 에서는 열지 않는다(ms2 교훈).

## Self-Check: PASSED

- FOUND: backend/shared/python/sunity_shared/analysis/fault_zoom.py
- FOUND: backend/functions/pipeline/app.py
- FOUND: backend/tests/test_gated_frame_skips_collapse.py
- FOUND: .planning/quick/260906-f4j-gated-card-collapse-frame-skip/260906-f4j-SUMMARY.md
- FOUND: e0a0fd15
- FOUND: 89065231
- FOUND: bf250cc6
- FOUND: def nearest_usable_frame
- FOUND: def _frame_usable
- FOUND: _fz.nearest_usable_frame( in app.py
- FOUND: test file 217 lines (>=80)
