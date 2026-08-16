---
phase: quick-260816-k2f
plan: 01
subsystem: ml-pipeline-tooling
tags: [cache-invalidation, p35, compare_align, s3-download, argparse, tdd]

# Dependency graph
requires: []
provides:
  - "p35_extract_align.py 파생 캐시 화이트리스트(CACHE_PATHS) + clean_motion_cache()/maybe_clean_cache() 순수 함수 — 기본 fresh(매 motion 처리 전 삭제 후 재생성)"
  - "--reuse-cache CLI 플래그 — 옛 존재기반 재사용 동작을 명시적으로 선택하는 opt-in 경로"
  - "p35_new_motion_docs.py 캐시 감사 결과(로컬 파생 캐시 구조적으로 없음) docstring 문서화"
  - "회귀 테스트 7건(test_p35_cache_fresh_default.py) — 화이트리스트 삭제/보존 + reuse-cache 스킵 tmp_path 고정"
affects: [p35_extract_align.py 향후 실행(다음 ref 영상 교체 시), discover_sweep.py 소스 게이트(quick-260814-ehz-5), belle 의 다음 P35 재추출 세션]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "오래 남는 스크래치 작업 디렉토리(--workdir)를 재사용하는 CLI 스크립트는 존재기반 캐시가 구조적으로 위험 — 기본 동작은 fresh(삭제 후 재생성), 재사용은 명시적 플래그로만 opt-in"
    - "argparse 조립을 build_arg_parser() -> argparse.ArgumentParser 로 분리(parse_args() 미호출) — GPU/네트워크 없이 파서 단독 유닛테스트 가능 (backend/research/spikes/sweep_rtmpose.py 선례와 동일 컨벤션)"

key-files:
  created:
    - backend/tests/phase35/test_p35_cache_fresh_default.py
  modified:
    - backend/scripts/p35_extract_align.py
    - backend/scripts/p35_new_motion_docs.py

key-decisions:
  - "파생 캐시를 화이트리스트(리터럴 5개 이름: user.mp4/ref.mp4/uf15/rf15/verify)로 한정 — glob/와일드카드 금지. doc.json/moments.json/align.json 은 파생 캐시가 아니라 사전 주입 입력/최종 산출물이라 화이트리스트 밖으로 고정(지우면 재생성 불가능)"
  - "compare_align.extract() 자체는 손대지 않음 — shared 코드이고 운영 경로(pipeline._run_deferred_compare_render)는 분석마다 새 임시 workdir 을 써서 이 존재기반 캐시 구멍에 원래 안 걸린다. 이 스크립트가 쓰는 오래 남는 --workdir 에서만 위험하므로 이 스크립트에서만 fresh 를 기본화"
  - "--reuse-cache 로 옛 동작(존재기반 재사용)을 명시적 opt-in 으로 남김 — belle 승인('매번 캐시를 다 지우고 돌리는 것을 기본으로')은 기본값 전환이지 재사용 금지가 아니므로, 반복 실행 비용을 피하고 싶을 때 선택 가능하게 유지"

patterns-established:
  - "무엇을 지웠는지(또는 왜 안 지웠는지)를 조용히 넘어가지 않고 motion 단위로 stdout 에 3분기(삭제함/재사용/캐시 없음) 출력 — 삭제 동작의 Repudiation 위협에 대한 최소 방어"

requirements-completed: [QUICK-260816-K2F]

# Metrics
duration: ~15min (세션 시작 타임스탬프 미기록 — 커밋 구간 실측 3m30s, 컨텍스트 로드+기준선 pytest 3회(각 ~40s) 포함 시 더 김)
completed: 2026-08-16
---

# Quick 260816-k2f: P35 캐시 fresh-by-default Summary

**p35_extract_align.py 의 파생 캐시(user.mp4/ref.mp4/uf15/rf15/verify)를 화이트리스트로 한정해 motion 처리 전 기본 삭제하도록 바꾸고, --reuse-cache 로 옛 존재기반 재사용을 opt-in 으로 남겨 오늘의 climb refFrames=256 재사용 사고(같은 새 ref.mp4 인데 climbfault 만 refFrames=119 정상 산출)가 재발하지 않게 함**

## Performance

- **Duration:** ~15 min (추정 — 정확한 세션 시작 타임스탬프는 기록되지 않음)
- **Commit span (실측):** 2026-08-16T10:17:12Z ~ 2026-08-16T10:20:42Z (3m30s)
- **Tasks:** 2/2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `CACHE_PATHS = ("user.mp4", "ref.mp4", "uf15", "rf15", "verify")` 화이트리스트 + `clean_motion_cache(mdir)`(존재하는 항목만 재귀/단일 삭제, 삭제한 이름 리스트 반환) + `maybe_clean_cache(mdir, *, reuse_cache)`(reuse_cache=True 면 완전 스킵) 추가.
- `process()` 시그니처에 `reuse_cache: bool = False` 키워드 인자 추가, 함수 맨 앞(`mdir` 계산 직후, `doc.json` 로드 이전)에서 `maybe_clean_cache()` 호출 + motion 별 stdout 안내 3분기(`fresh: 파생 캐시 삭제 [...]` / `--reuse-cache: 캐시 재사용(삭제 건너뜀)` / `fresh: 캐시 없음(첫 실행)`).
- argparse 조립을 `build_arg_parser() -> argparse.ArgumentParser` 로 추출(parse_args() 미호출, sweep_rtmpose.py 컨벤션과 동일) + `--reuse-cache`(action="store_true") 플래그 추가. `main()` 은 `build_arg_parser().parse_args()` 로 교체하고 `process(..., reuse_cache=args.reuse_cache)` 로 배선.
- 모듈 docstring 에 "캐시 정책(quick-260816-k2f, 기본 fresh)" 문단 삽입 — 오늘 실측(climb refFrames=256 구 vs climbfault refFrames=119 신, 같은 새 ref.mp4 40,928,589B)과 두 존재기반 캐시의 정체, compare_align.extract() 를 손대지 않는 이유를 명시.
- `p35_new_motion_docs.py` 감사: `pipeline._process()` 직접 호출뿐 자체 로컬 비디오 다운로드/캐시 코드가 없고 `analysis_id` 가 `_fresh_analysis_id(slot)`(`int(time.time())` 기반)로 매번 새로 발급되어 Firestore 문서가 항상 새로 쓰인다는 사실을 확인해 docstring 에 "캐시 감사(quick-260816-k2f)" 문단으로 기록 — 코드 로직(ITEMS/`_load_pipeline_module()`/`main()`) 무변경.
- 신규 회귀 테스트 7건(`test_p35_cache_fresh_default.py`) — TestCleanMotionCache(화이트리스트 삭제+doc/moments/align 생존, 빈 디렉토리 noop, mdir 부재 안전) 3건, TestMaybeCleanCache(reuse_cache=True 스킵, reuse_cache=False 위임) 2건, TestReuseCacheFlag(기본값/명시값) 2건. RED 단계에서 7건 전부 `AttributeError`(미구현 함수/상수 접근)로 실패 확인 후 구현, GREEN 재실행 7/7 PASS.

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): p35 캐시 fresh-by-default 회귀 테스트** - `05dcc911` (test)
2. **Task 1 (GREEN): p35_extract_align 캐시 기본 fresh + --reuse-cache** - `40633c90` (feat)
3. **Task 2: p35_new_motion_docs 캐시 감사 문서화 + 전체 회귀 검증** - `e9ba7be1` (docs)

_Task 1 은 tdd="true" — RED(test) → GREEN(feat) 순서로 커밋. 조건문 분기 + 신규 순수 함수 3개(clean_motion_cache/maybe_clean_cache/build_arg_parser) 추가가 diff 전부라 REFACTOR 대상 없음, 별도 refactor 커밋 없음. Task 2 는 tdd 미지정(docstring 문단 추가 + 검증만) — 1커밋._

## Files Created/Modified

- `backend/tests/phase35/test_p35_cache_fresh_default.py` (신설, 99줄) - CACHE_PATHS 화이트리스트 삭제/보존 + --reuse-cache 스킵을 tmp_path 합성 디렉토리로 고정하는 7테스트
- `backend/scripts/p35_extract_align.py` (+76/-5) - CACHE_PATHS + clean_motion_cache()/maybe_clean_cache() + build_arg_parser() + --reuse-cache 플래그 + process()/main() 배선 + docstring 캐시 정책 문단. JOBS 딕셔너리(10행)·s3_download() 본문은 diff 0으로 무변경 확인.
- `backend/scripts/p35_new_motion_docs.py` (+10/-0, docstring 전용) - "캐시 감사(quick-260816-k2f)" 문단 추가. ITEMS/`_load_pipeline_module()`/`main()` 로직 무변경.

## Decisions Made

- **화이트리스트를 리터럴 5개 이름으로 고정, glob 없음** — T-k2f-01 mitigate. doc.json/moments.json/align.json 을 화이트리스트 밖에 두어 파생 캐시와 입력/산출물을 구조적으로 분리.
- **compare_align.extract() 는 무변경** — shared 코드(운영 경로 공유)이고, 운영 `_run_deferred_compare_render` 는 분석마다 새 임시 workdir 을 써서 이 존재기반 캐시 구멍에 원래 안 걸린다. 이 스크립트만 오래 남는 `/workspace/p35/{motion}/` 을 재사용해서 걸리므로 수리 범위를 이 스크립트로 한정.
- **--reuse-cache 를 opt-in 으로 유지** — belle 승인은 "기본을 fresh 로" 이지 "재사용을 아예 없애라"가 아니므로, 반복 실행이 잦은 상황을 위해 명시적 opt-out 경로를 남김.

## Deviations from Plan

None - plan executed exactly as written. PLAN.md 의 action 지시(화이트리스트 위치, 함수 시그니처, print 3분기 문구, docstring 삽입 지점, build_arg_parser 컨벤션)를 그대로 구현했고, 신규 발견된 버그/누락 기능/블로킹 이슈가 없어 Rule 1~4 어느 것도 발동하지 않았다.

## Issues Encountered

None.

## LLM 학습 영향 (필수)

N/A — 이번 사이클은 로컬 캐시 삭제 화이트리스트 + CLI 플래그만 변경, LLM/GPU/S3/Firestore 실호출 0. 테스트는 tmp_path 합성 디렉토리만 다루고 `s3_download()`/`compare_align.build_align()` 은 호출하지 않았다(계획의 로컬 전용 제약 그대로 준수).

## User Setup Required

None - no external service configuration required. (Pod 접속·GPU 필요 작업 없음 — 계획대로 로컬 전용으로 완결.)

## Verification Results

- `PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests/phase35/test_p35_cache_fresh_default.py` → **7 passed** (RED 단계에서 동일 7건이 AttributeError 로 실패했던 것과 대조 확인).
- `PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests` → **4398 passed, 59 failed, 26 skipped** — 계획 단계 기준선(4391/59/26)에서 passed 만 신규 테스트 수만큼(+7) 증가, failed/skipped 불변(기존 무관 실패 목록도 동일: test_pipeline_geminid_wiring.py 6건 + test_spike_gemini_moment_smoke.py 1건 계열).
- `git status --porcelain backend/shared backend/functions` → **빈 출력** (Task 1/Task 2 커밋 직후 각각 재확인, 최종 확인도 빈 출력) — 운영 코드 무접촉.
- `git diff backend/scripts/p35_extract_align.py` 시각 검토 → JOBS 딕셔너리(라인 56~70)에 대한 `+`/`-` 변경 줄 0건, `s3_download()` 함수 본문 무변경(컨텍스트로만 등장) — 계획의 "diff 는 명시된 추가/재배선에 한정" 요건 충족.
- `grep -q "quick-260816-k2f" backend/scripts/p35_new_motion_docs.py` → 성공.
- belle verification_notes 의 추가 요구(플랜 <verify> 태그엔 없었으나 명시적으로 요청됨) 확인: **doc.json/moments.json/align.json 무접촉** = `TestCleanMotionCache::test_removes_whitelist_preserves_inputs_and_output` 가 삭제 전/후 byte-identical 비교로 실증(PASS). **--reuse-cache 가 실제로 삭제를 건너뜀** = `TestMaybeCleanCache::test_reuse_cache_true_skips_deletion` 이 5항목 전부 생존을 실증(PASS).

## TDD Gate Compliance

Task 1 gate sequence 확인(git log): `test(quick-260816-k2f): p35 캐시 fresh-by-default 회귀 테스트 (RED)` (`05dcc911`) → `feat(quick-260816-k2f): p35_extract_align 캐시 기본 fresh + --reuse-cache (GREEN)` (`40633c90`). RED 단계에서 7테스트 전부 `AttributeError: module 'p35_extract_align' has no attribute '...'` 로 실패를 직접 확인(우연히 통과한 테스트 없음 — fail-fast 규칙 위반 없음) 후 구현. REFACTOR 커밋 없음 — 신규 함수 3개 + 조건 분기 추가가 diff 전부라 별도 리팩터링 대상이 없었다.

## Next Phase Readiness

- 다음에 belle 가 P35 ref 영상을 또 교체하고 재추출을 돌리면(플래그 없이) 기본으로 화이트리스트 5항목이 지워진 뒤 S3 재다운로드+재추출이 강제된다 — 오늘의 climb 재사용 사고 계열이 이 스크립트 경로에서는 재발하지 않는다.
- 반복 실행이 잦아 재다운로드 비용을 피하고 싶은 세션에서는 `--reuse-cache` 로 옛 동작을 명시적으로 선택 가능.
- `p35_new_motion_docs.py` 는 같은 계열 위험이 구조적으로 없음을 확인했으므로 이번 사이클에서 추가 수정 불필요.
- 운영 코드(`backend/shared/`, `backend/functions/`)는 완전 무접촉으로 남아 이번 변경의 blast radius 는 `--workdir` 스크래치 디렉토리로 완전히 국한된다(threat_model T-k2f-02 accept 그대로 유효).

---
*Task: quick-260816-k2f*
*Completed: 2026-08-16*

## Self-Check: PASSED

- FOUND: backend/tests/phase35/test_p35_cache_fresh_default.py
- FOUND: backend/scripts/p35_extract_align.py
- FOUND: backend/scripts/p35_new_motion_docs.py
- FOUND: .planning/quick/260816-k2f-cache-fresh-default/260816-k2f-SUMMARY.md
- FOUND commit: 05dcc911 (test — RED)
- FOUND commit: 40633c90 (feat — GREEN)
- FOUND commit: e9ba7be1 (docs — 캐시 감사 + 전체 회귀 검증)
