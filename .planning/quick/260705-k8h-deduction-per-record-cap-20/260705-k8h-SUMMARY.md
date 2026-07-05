---
phase: quick-260705-k8h
plan: 01
subsystem: scoring-engine
tags: [deduction-engine, per-record-cap, contract-lockstep, transparency]
requires: []
provides:
  - "PER_RECORD_DEDUCTION_CAP = 20.0 — 관절(criterion record)당 감점 상한 클램프"
  - "DeductionRecord rawPoints/capApplied optional 계약 (models.py / analysis.ts / contract.md 3-way)"
affects: [deduction_engine, models, analysis-ts-contract, contract-md]
tech-stack:
  added: []
  patterns:
    - "additive optional 계약 필드 — 조건부 방출(cap_applied 시에만 키 추가)로 byte-호환 유지"
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/deduction_engine.py
    - backend/shared/python/sunity_shared/models.py
    - app/src/types/analysis.ts
    - docs/contract.md
    - backend/tests/test_deduction_engine.py
decisions:
  - "관절당 감점 상한 -20 채택 (belle 승인 2026-07-05) — run6 4-규칙 비교서 체감가중/RSS 탈락, IPSF 결함 유형별 상한 구조 정합"
  - "클램프 비교는 round(0.1) 후 — float epsilon 가짜 capApplied 잡음 방지, 경계(== cap)는 상한 이하 취급"
  - "fallback record(dimension_overall_fallback)는 클램프 비대상 — final == dimension_overall 불변식 + 100+Σpoints==final 추적성 보존"
metrics:
  duration: "~25min"
  completed: "2026-07-05"
---

# Quick 260705-k8h: 관절당 감점 상한 -20 Summary

**One-liner:** deduction_engine per-criterion record 감점을 -20 으로 클램프(kip-up 26점급
폭주 감점 → 47점급)하되 rawPoints/capApplied 로 원 감점을 투명 노출 — 상한 미적용
record 는 기존 11키 byte-동일, 계약 3-way(models/analysis.ts/contract.md §10) 동기.

## Tasks

| Task | Name | Commits | Files |
|------|------|---------|-------|
| 1 (TDD) | 엔진 per-record cap + 계약 3-way 동기 | d87a040 (RED), d9ea18f (GREEN) | deduction_engine.py, models.py, analysis.ts, contract.md |
| 2 | 유닛 게이트 신설 + cap-인지 기존 단언 갱신 | 540b854 | test_deduction_engine.py |

## What Was Built

- `PER_RECORD_DEDUCTION_CAP = 20.0` 모듈 상수 (한국어 why 주석: belle 승인, run6 비교,
  IPSF 정합, severity 밴드 아님, fallback 비대상 사유).
- per-criterion loop: `capped_r = round(capped, 1)` 후 `capped_r > CAP` 이면 points 를
  `-20.0` 으로 클램프 + `raw_points=-capped_r`, `cap_applied=True`. 경계(정확히 == cap)는
  미클램프(필드 생략).
- `DeductionRecord` 에 default 필드 2개(`raw_points`, `cap_applied`) — 기존 생성부
  (fallback record 포함) 무수정 호환. `to_dict()` 는 `cap_applied` 일 때만
  `rawPoints`/`capApplied` 키 추가 (Firestore-flat scalar).
- 계약 동기: `models.DEDUCTION_RECORD_OPTIONAL_KEYS = ("rawPoints", "capApplied")`,
  analysis.ts `rawPoints?: number` / `capApplied?: true`, contract.md §10.1(final 단위
  유일 clamp 문구 갱신) + §10.2(필수 11 + optional 2, 행 2개 추가) + §10.6(record-level
  optional 예외) + 하단 갱신 footnote.
- 신설 유닛 게이트 6종: 클램프+투명성 / byte-호환 / monkeypatch 경계(12.0 vs 11.9
  대비쌍) / final Σ 정합(둘 다 capped → 60) / fallback 비클램프(-38 유지, final 62) /
  결정성. 전부 상수 파생 값만 단언(실영상 점수 리터럴 0).
- 기존 게이트 cap-인지 갱신: contract_lockstep(union+disjoint), `_assert_record_keys`
  helper, no_final_band(100 − round(3×cap) == 40 < 50), deadzone/split/unavailable
  단조 sweep 을 sub-cap devs 로 교체.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_unavailable_seed_monotonic_deduction cap 동점 붕괴 (플랜 미열거 6번째 갱신 지점)**
- **Found during:** Task 2 전체 검증
- **Issue:** 구 fixture(leg 20 vs 40)가 cap 도입 후 fallback -20 vs cap-포화 -20 동점이
  되어 strict 단조 단언 실패. 플랜은 갱신 지점 5곳만 열거 — 이 테스트가 누락.
- **Fix:** 다른 sweep 갱신과 동일 패턴으로 sub-cap granular devs(25/35)로 교체 +
  이유 주석. ND-07 단조성 의미 보존.
- **Files modified:** backend/tests/test_deduction_engine.py
- **Commit:** 540b854

## Verification

- `pytest tests/test_deduction_engine.py tests/test_phase25_eval_gates.py -q` → 98 passed
- 소비 테스트 9파일(phase24 gates/seed merge/pipeline seam/vision gate/mode3/
  gemini scorer/vision veto 포함) → 365 passed. check_monotonicity 실엔진 PASS
  (test_phase24_gates.py 포함).
- `cd app && npm run typecheck` (tsc --noEmit) → GREEN (worktree 에 node_modules 부재라
  main repo node_modules 임시 symlink 로 실행 후 제거).
- 게이트 소스 무접촉: `git diff base..HEAD -- backend/evals/` = 0 files.
- 엔진 소스 가드: `min(100` / `min(final` 부재 유지 (test_no_final_band).

## Deferred Issues

- `test_p1_objective_knee_decontamination.py` 4건 사전-실패 (pre-existing, base commit
  에서도 동일 실패 확인 — ref-kip-up YAML knee expectation drift). 본 태스크 무관,
  `deferred-items.md` 에 상세 기록.

## Known Stubs

None — 스텁/placeholder 없음. 앱 화면 코드 무수정(optional 필드라 안전).

## Threat Flags

None — 신규 네트워크/auth/파일 접근 표면 없음 (순수 채점 수학 모듈 내부 변경).
T-k8h-01(round 후 비교로 epsilon 잡음 방지) / T-k8h-02(rawPoints/capApplied 쌍 불변식
`_assert_record_keys` 로 고정) mitigation 반영 완료.

## Self-Check: PASSED

- 커밋 3개(d87a040/d9ea18f/540b854) 존재 확인
- must_haves artifacts 5파일 존재 + contains 마커(PER_RECORD_DEDUCTION_CAP /
  DEDUCTION_RECORD_OPTIONAL_KEYS / rawPoints) 전부 확인
