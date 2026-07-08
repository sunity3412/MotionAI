---
phase: 28-dtw-motion-based-alignment
plan: 01
subsystem: motion-alignment (backend 계측 + 계약 + 앱 워핑 수학)
tags: [dtw, alignment, fps, wave-0, red-test, pure-function, typecheck]
requirements: [ALGN-01]
dependency_graph:
  requires: []
  provides:
    - "reference fps 실측 봉인 (A1 해소 — 활성 11 doc 전부 18.0fps, anglesFrames==keypointReport.frames)"
    - "build_motion_alignment 최종 계약 (RED 테스트, degenerate=disabled 포함)"
    - "alignmentWarp.ts 순수 함수 (warpTime/segmentRate/normalizeMotionAlignment) — typecheck green"
  affects:
    - "28-02 (build_motion_alignment GREEN 구현 — 이 테스트를 만족)"
    - "28-03 (MotionAlignment 계약 analysis.ts 이관 — 임시 로컬 정의 대체)"
    - "28-06 (VideoCompare 워핑 배선 — alignmentWarp.ts 소비)"
tech_stack:
  added: []
  patterns:
    - "read-only Firestore Admin 실측 스크립트 (backfill SA 초기화 선례 재사용)"
    - "구현 전 계약 고정 RED 테스트 (test_dimensions 순수 모듈 표준형)"
    - "방어적 normalize (userAnalyses 선례) — malformed → null legacy 폴백"
key_files:
  created:
    - backend/scripts/measure_reference_fps.py
    - backend/tests/test_motion_alignment.py
    - app/src/lib/alignmentWarp.ts
  modified: []
decisions:
  - "정렬 맵은 초 단위 방출 (fps 는 doc 메타에서 읽음) — 실측으로 18.0fps 확정했으나 하드코딩 회피 설계 유지 (Pitfall 1 방어)"
  - "degenerate(empty_path/invalid_fps/insufficient_anchors)는 tier='disabled' 방출 — legacy 필드 부재와 구별 (과약속 배너 루프 차단, W3)"
  - "MotionAlignment 는 alignmentWarp.ts 에 임시 로컬 정의 — 28-03 이 analysis.ts 로 이관"
metrics:
  duration_min: 18
  tasks_completed: 3
  files_created: 3
  completed_date: 2026-07-08
---

# Phase 28 Plan 01: 계측-먼저 검증 재료 3종 Summary

reference fps 를 실측으로 봉인(A1 해소)하고, 28-02 가 만족할 정렬 계약을 최종 형태(degenerate=disabled)로 RED 테스트에 고정하며, 앱측 워핑 수학(warpTime/segmentRate/normalizeMotionAlignment)을 순수 모듈로 신설해 typecheck 게이트에 진입시켰다.

## What Was Built

### Task 1 — reference fps 실측 (A1 해소)
`backend/scripts/measure_reference_fps.py` (read-only Firestore Admin get). 활성 reference 11 doc 의 `keypointReport.fps` / `keypointReport.frames` / `anglesFrames` 실측 + 판정 (a) `anglesFrames == keypointReport.frames`, (b) `keypointReport.fps > 0`. write 연산 0 (T-28-01 read-only 강제 — grep 게이트 통과).

**실측 출력 전문 (A1 RESOLVED):**
```
[ref-climb] activeVersion=phase4_v1 keypointReport.fps=18.0 keypointReport.frames=257 anglesFrames=257 seconds=14.28
[ref-foxtop] activeVersion=phase4_v1 keypointReport.fps=18.0 keypointReport.frames=426 anglesFrames=426 seconds=23.67
[ref-foxtop-split] activeVersion=phase4_v1 keypointReport.fps=18.0 keypointReport.frames=485 anglesFrames=485 seconds=26.94
[ref-invert] activeVersion=phase4_v1 keypointReport.fps=18.0 keypointReport.frames=260 anglesFrames=260 seconds=14.44
[ref-sideway-spin] activeVersion=phase4_v1 keypointReport.fps=18.0 keypointReport.frames=298 anglesFrames=298 seconds=16.56
[ref-combo] activeVersion=phase4_v1 keypointReport.fps=18.0 keypointReport.frames=931 anglesFrames=931 seconds=51.72
[ref-elbow-twist-sister] activeVersion=phase4_v1 keypointReport.fps=18.0 keypointReport.frames=329 anglesFrames=329 seconds=18.28
[ref-kip-up] activeVersion=phase4_v1 keypointReport.fps=18.0 keypointReport.frames=118 anglesFrames=118 seconds=6.56
[ref-pdshape] activeVersion=phase4_v1 keypointReport.fps=18.0 keypointReport.frames=237 anglesFrames=237 seconds=13.17
[ref-peter-pan] activeVersion=phase4_v1 keypointReport.fps=18.0 keypointReport.frames=130 anglesFrames=130 seconds=7.22
[ref-power-spin] activeVersion=phase4_v1 keypointReport.fps=18.0 keypointReport.frames=159 anglesFrames=159 seconds=8.83
A1 RESOLVED: 11 docs, fps set=[18.0]
```
→ 활성 reference 11개 전부 angles=18.0fps, `anglesFrames == keypointReport.frames` 정합 확인. 학생 9fps vs reference 18fps 도메인 함정(Pitfall 1)이 코드/주석 추정이 아닌 **live doc 실측**으로 봉인됨. 초 단위 방출 + fps 를 doc 메타에서 읽는 설계는 이후 웨이브에서 유지 (18.0 하드코딩 금지 — 재처리 시 방어).

### Task 2 — build_motion_alignment 계약 고정 (RED, 최종 계약)
`backend/tests/test_motion_alignment.py` (12 테스트, 모듈 top-level import = 의도된 RED). 합성 `MotionMatch` 빌더 + 계약:
- None(유일 None 케이스) vs degenerate 3형(`empty_path`/`invalid_fps`/`insufficient_anchors` → tier=`disabled`).
- 초 단위 + fps 변환 (user 9fps/ref 18fps identity-in-time → uSec≈rSec, 인덱스 아닌 초).
- 단조성 / 결정론 / identity 기울기 1.0(warped).
- tier 경계 8.0(warped)/8.1(trim_only)/25.0(trim_only)/25.1(disabled) + `rate_clamp_exceeded`.
- flat 계약 키 + anchorCount == len(anchors)//2, 앵커 512 상한.

기대값은 처음부터 최종 계약(degenerate=disabled)으로 작성 — 28-02 GREEN 이 테스트를 재갱신하는 churn 0 (리뷰 MEDIUM-2). 현재 상태: `ImportError: cannot import name 'motion_alignment'` (구현 부재 = RED, pytest exit 2).

### Task 3 — alignmentWarp.ts 워핑 수학 순수 모듈
`app/src/lib/alignmentWarp.ts` (player/react 의존 0, `tsc --noEmit` 만으로 검증). `warpTime`(구간 선형보간 + 범위 밖 기울기 1.0 연장, trim_only=오프셋, disabled=identity), `segmentRate`(구간 기울기 clamp RATE_MIN 0.5/RATE_MAX 2.0, trim_only/disabled=1.0), `normalizeMotionAlignment`(방어적 소비 — 비단조/NaN/홀수/512초과/미등재 tier·source → null; 예외: `disabled`+`anchors=[]` 는 유효 객체로 통과해 배지 안내 보존). MotionAlignment 는 임시 로컬 정의(28-03 analysis.ts 이관 예정, 헤더 주석 박제).

## Verification

- Task 1: 스크립트 exit 0, "A1 RESOLVED" + 11 doc 라인. read-only grep(`\.set|\.update|\.delete`) == 0.
- Task 2: pytest 비영 exit(RED, ModuleNotFoundError). `def test_` 12 (≥9), `build_motion_alignment` 18 (≥6), `disabled` 14 (≥3).
- Task 3: `npm run typecheck` exit 0. export 함수 3, `RATE_MIN` 4회(≥2).

## Deviations from Plan

None — 3 태스크 계획대로 실행. (환경 처리 2건은 계획 무변경: (1) firebase-sa.json 이 worktree 아닌 main repo 에 위치 → FIREBASE_SA_PATH 를 절대경로로 지정해 실행. (2) worktree app 에 node_modules 부재 → main repo node_modules 를 임시 심링크(gitignored, 커밋 무관)해 `npm run typecheck` 실행 후 제거.)

## Notes

- **채점 무접촉:** 이 플랜은 채점 코드 0접촉 (신규 파일 2 + 1회성 스크립트 + 앱 순수 모듈). veto still 경로(`_build_selected_frame_pair`) 무접촉 — phase 전역 원칙 정합.
- **의도된 Wave 0 seam (스텁 아님):** (a) `motion_alignment` 모듈 미구현(RED, 28-02 GREEN 대상), (b) MotionAlignment 임시 로컬 타입(28-03 이관 대상) — 둘 다 후속 플랜에서 해소 예정으로 문서화됨. UI 로 흐르는 빈 데이터 스텁 아님.

## Commits

- `8a6b106` feat(28-01): reference fps 실측 스크립트 — A1 가정 해소
- `6e5cf19` test(28-01): build_motion_alignment 계약 고정 (RED, 최종 계약)
- `bb2f639` feat(28-01): alignmentWarp.ts — 워핑 수학 순수 모듈 (typecheck 진입)

## Self-Check: PASSED

- 신규 파일 3 + SUMMARY 존재 확인 (measure_reference_fps.py / test_motion_alignment.py / alignmentWarp.ts / 28-01-SUMMARY.md).
- 커밋 4개 존재 확인 (8a6b106 / 6e5cf19 / bb2f639 / 39727ca).
