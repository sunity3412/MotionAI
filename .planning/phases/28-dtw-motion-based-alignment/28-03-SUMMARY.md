---
phase: 28-dtw-motion-based-alignment
plan: 03
subsystem: motion-alignment (계약 3-way lockstep + Firestore scoped validator)
tags: [contract, lockstep, firestore-validator, motion-alignment, refMatch, tdd, wave-2]
requirements: [ALGN-01, ALGN-03]
dependency_graph:
  requires:
    - "28-01 (alignmentWarp.ts RATE_MIN/RATE_MAX 고정값 + normalizeMotionAlignment disabled 예외 규칙 — W4/MEDIUM-3 대칭 대상)"
    - "27-06 (faultZoomStatus 3-way lockstep + update_analysis_fault_zoom — 선행 심볼)"
  provides:
    - "MotionAlignment 계약 3-way lockstep (analysis.ts interface + models.py MOTION_ALIGNMENT_KEYS + contract.md §11)"
    - "FaultZoomComparison.refMatch? (D-04 캡션 provenance 플래그)"
    - "_validate_motion_alignment scoped validator (상한/flat/단조 + tier↔anchors 역불변식 MEDIUM-3) + complete_analysis 훅"
    - "RATE 클램프 W4 lockstep 텍스트 대조 테스트"
  affects:
    - "28-04 (방출 — result.motionAlignment 채움, MAX_ANCHOR_FLOATS lockstep 단언 소관 B1)"
    - "28-06/07 (소비 — VideoCompare 워핑 + refMatch 캡션)"
    - "22-* (source:'vlm' 상위 호환 축 — Phase 22 v1 time_anchors 동형 소비 자리)"
tech_stack:
  added: []
  patterns:
    - "scoped validator + complete_analysis 단일 persistence 훅 (safetyFlags 선례 — 신규 kwarg 없음)"
    - "3-way atomic 계약 커밋 (한쪽만 수정 = anti-pattern 방어)"
    - "구현-전 계약 고정 RED 테스트 (TDD, 12 validator + 3 텍스트 lockstep)"
    - "병렬 wave 격리 — 같은 wave 산출물(motion_alignment.py) import 0 (B1)"
key_files:
  created:
    - backend/tests/test_motion_alignment_contract.py
  modified:
    - app/src/types/analysis.ts
    - backend/shared/python/sunity_shared/models.py
    - docs/contract.md
    - backend/shared/python/sunity_shared/firestore_admin.py
decisions:
  - "빈 anchors 역불변식(MEDIUM-3): tier=='disabled' 만 허용, warped/trim_only 는 2쌍 이상 강제 — 모순 데이터를 앱 silent fallback 대신 저장 전 거부(validator)"
  - "MAX_ANCHOR_FLOATS==512 lockstep 단언은 여기서 제외(B1) — 28-04 test_pipeline_motion_alignment.py 로 이동(같은 wave 병렬 collection error 회피). 여기서는 models/TS 텍스트 쪽 단독 검증"
  - "nested anchors → TypeError, 그 외(NaN/inf/비단조/미등재/whitelist/역불변식) → ValueError (safety_flags TypeError 관례 정합)"
  - "refMatch 계약은 §11.6 에 문서화 — 독립 FaultZoomComparison 테이블 절이 contract.md 에 부재(faultZoomStatus 노트만 존재)라 §11 하위절로 편입"
metrics:
  duration_min: 22
  tasks_completed: 2
  files_created: 1
  files_modified: 4
  completed_date: 2026-07-08
---

# Phase 28 Plan 03: motionAlignment 계약 3-way lockstep + Firestore validator Summary

방출(28-04)·소비(28-06/07)가 착수하기 전에 MotionAlignment 계약을 단일 atomic 커밋으로 3곳(analysis.ts + models.py + contract.md §11)에 고정하고, malformed/초대형/모순(tier↔anchors) alignment 를 저장 전에 차단하는 Firestore scoped validator 를 TDD 로 박제했다. D-04 캡션용 `FaultZoomComparison.refMatch` 도 함께 계약화, Phase 22 `source:'vlm'` 상위 호환 축으로 설계했다.

## 선행 확인 (심볼 기준 — 27-07 선례)

착수 전 27-06 산출 심볼 존재 확인 (라인 번호 아닌 심볼):
- `grep -c "faultZoomStatus" app/src/types/analysis.ts` = 2 (>= 1) ✓
- `grep -c "def update_analysis_fault_zoom" firestore_admin.py` = 1 (>= 1) ✓

두 심볼 존재 → 착수. (worktree 초기 HEAD 가 27-complete 커밋이었으나 `<worktree_branch_check>` merge-base 로직으로 28-01 base `3a2d92b` 로 정상 리셋 후 진행 — 28-01 산출물 alignmentWarp.ts / test_motion_alignment.py 존재 확인.)

## What Was Built

### Task 1 — 계약 3-way lockstep (atomic 커밋 `a2d2802`)

단일 커밋으로 세 파일 동시 수정:
- **analysis.ts**: `MotionAlignment` interface 신설(version/source/tier/reason?/anchors/anchorCount/distance) — JSDoc 에 anchors flat 규칙·legacy 하위호환·Phase 22 vlm 상위 호환·Python lockstep·역불변식 5항 박제. `AnalysisResult.motionAlignment?` 추가(faultZoomStatus 인접 optional 자리). `FaultZoomComparison.refMatch?: 'dtw' | 'failed'` 추가(D-04 — 기준 프레임 대응 provenance, region/tier 선례와 동일 주석 형식).
- **models.py**: `MOTION_ALIGNMENT_KEYS`/`MOTION_ALIGNMENT_TIERS`/`MOTION_ALIGNMENT_SOURCES`/`MOTION_ALIGNMENT_MAX_ANCHOR_FLOATS=512` 상수 블록(DEDUCTION_RECORD_KEYS 형식) — 헤더 주석에 3-way lockstep + 40k index-entry 상한 lockstep 명기.
- **contract.md**: `## §11. MotionAlignment` 절 신설 — 필드 표, tier 사다리 3단(§11.2), 초 단위 fps 도메인(§11.3, 9fps vs 18fps), anchors flat 상한 512 + tier↔anchors 역불변식(§11.4), legacy 하위호환 + Phase 22 vlm 상위 호환(§11.5), refMatch(§11.6) + 변경이력 footer 라인.

### Task 2 — scoped validator + lockstep 테스트 (TDD, RED `b8ce7d8` → GREEN `15b8da7`)

- **RED**: `test_motion_alignment_contract.py` 신설 — validator behavior 9케이스 + 역불변식 3케이스 + 3-way 텍스트 lockstep 3케이스. 구현 부재로 12 validator 테스트 실패(AttributeError), 3 텍스트 테스트는 Task 1 이 이미 만족.
- **GREEN**: `firestore_admin._validate_motion_alignment(payload, *, path='motionAlignment')` 신설 — dict 강제 + `MOTION_ALIGNMENT_KEYS` 화이트리스트(reason optional) + tier/source enum + version str + distance finite scalar + anchors flat list[숫자](nested→TypeError, NaN/inf→ValueError) + 짝수 + 상한 512 + `anchorCount==len//2` + tier↔anchors 역불변식(disabled 만 빈 허용, warped/trim_only 는 `len>=4 AND anchorCount>=2`) + u strictly increasing·r non-decreasing. `complete_analysis` 의 result 검증 블록에 한 줄(`_validate_motion_alignment((result or {}).get("motionAlignment"))`) + Phase 28 docstring 단락 추가. **generic `_validate_dict_only_scalars` 본체 무변경.**

## Verification

- **Task 1**: `npm run typecheck` exit 0. `grep -c "motionAlignment" analysis.ts`=2 / `refMatch`=2 / `MotionAlignment`=3 / `MOTION_ALIGNMENT_KEYS` models.py=1 / `§11` contract.md=11. 세 파일 동일 커밋(a2d2802) — 3-way atomic.
- **Task 2**: `pytest test_motion_alignment_contract.py` = **15 passed**(>= 11, 역불변식 3케이스 포함). `_validate_motion_alignment` fa.py=3(정의+훅+docstring) / `def _validate_dict_only_scalars`=1(무변경) / `RATE_MIN` test=5(>= 1, W4) / `^(from|import).*motion_alignment` test=0(B1 격리).
- **회귀**: complete_analysis 소비 테스트 무회귀 — `test_fault_zoom_deferred.py` + `test_pipeline_deduction_seam.py` = 37 passed.

## Deviations from Plan

None — 2 태스크 계획대로 실행. (환경 처리 2건, 계획 무변경:
1. worktree 초기 HEAD 가 27-complete(53860a1)였으나 `<worktree_branch_check>` merge-base 로직대로 28-01 base `3a2d92b` 로 `git reset --hard` 후 진행 — 28-01 계약 전제 정상 확보.
2. worktree app 에 node_modules 부재 → main repo node_modules 임시 심링크(gitignored, 커밋 무관)로 `npm run typecheck` 실행 후 제거.)

한 가지 조정 기록(Rule 1 성격의 마이크로 fix, 별도 커밋 아님 — GREEN 커밋에 포함): RED 테스트 docstring 의 한글 문장("import 하지 않는다 … `motion_alignment`…")이 B1 게이트 grep `^(from|import).*motion_alignment` 를 오탐(문장이 "import"로 시작 + 같은 줄에 motion_alignment). 실제 import 아님 — 문구를 재작성해 게이트 0 만족(계약/로직 무변경).

## Notes

- **채점 무접촉:** 계약/validator 추가만 — 점수 산출 코드 0접촉(deduction_engine/dimensions/veto 경로 무접촉). phase 전역 원칙 정합.
- **의도된 seam (스텁 아님):** (a) `result.motionAlignment` 방출부는 28-04 소관(현재 validator 는 None graceful 통과 — 방출 전 doc 안전), (b) MAX_ANCHOR_FLOATS 모듈↔models lockstep 단언은 28-04 로 이관(B1, 같은 wave 병렬 collection error 회피), (c) `source:'vlm'` 축은 Phase 22 상위 호환 예약. 셋 다 후속 문서화됨. UI 로 흐르는 빈 데이터 스텁 아님.
- **threat 정합:** T-28-05(40k index-entry DoS)=상한 512+flat scalar 강제 / T-28-07(계약 drift)=atomic 커밋 + 텍스트 lockstep 테스트 / T-28-18(모순 데이터)=역불변식 저장 전 거부 — 전부 mitigate 반영.

## Commits

- `a2d2802` feat(28-03): motionAlignment + refMatch 계약 3-way lockstep
- `b8ce7d8` test(28-03): _validate_motion_alignment 계약 + 역불변식 RED
- `15b8da7` feat(28-03): _validate_motion_alignment scoped validator + complete_analysis 훅
- `ade7a68` docs(28-03): complete motionAlignment 계약 lockstep + validator plan

## Self-Check: PASSED

- 계약/코드 5 파일 + 신규 테스트 1 + SUMMARY 존재 확인 (analysis.ts / models.py / contract.md / firestore_admin.py / test_motion_alignment_contract.py / 28-03-SUMMARY.md).
- 커밋 4개 존재 확인 (a2d2802 / b8ce7d8 / 15b8da7 / ade7a68).
- working tree clean (미커밋 산출물 0).
