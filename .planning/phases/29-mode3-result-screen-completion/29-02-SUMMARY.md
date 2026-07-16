---
phase: 29-mode3-result-screen-completion
plan: 02
subsystem: scoring-seam (backend pipeline — mode3 투명 감점-합산 절개)
tags: [mode3, deduction-tally, tdd-red-green, seam, contract, wave-1]
requirements: [D-01, D-02, D-03]
dependency_graph:
  requires: []
  provides:
    - "mode3_held tally seam — 등록 동작 md(ipsf_absolute measured seed) 보유 시 deductionBreakdown 방출 (Gemini 호출 0)"
    - "D-02 항등: mode3 방출 doc 의 overallScore == deductionBreakdown.final (in-place 교체, 별도 점수 필드 0)"
    - "D-03 자연 방어: md 빈 dict → 미방출 + 점수 byte-불변 (빈 criteria 4동작 + 미등록)"
    - "contract.md §10.7 — mode3 방출 조건 서술 (신규 필드 0)"
  affects:
    - "29-03/29-04 (앱 결과화면 breakdown 렌더 mode 무관화 — result.deductionBreakdown != null 게이트)"
    - "29-05 (Pod sweep 게이트 — D-02 production 전환 조건, 정은지 페어셋 mode3)"
tech_stack:
  added: []
  patterns:
    - "24-04 low_alignment tally-eligible 편입 선례를 mode3_held 에 이식 (같은 함수 내 analog)"
    - "seam 내부 try/except graceful — 채점 hook 실패 != 분석 실패 (:2526 스타일 승계)"
    - "test_pipeline_deduction_seam.py path 주입 + _ctx 헬퍼 mock 패턴 승계 (실 Gemini/S3 0)"
key_files:
  created:
    - backend/tests/test_mode3_tally_seam.py
  modified:
    - backend/functions/pipeline/app.py
    - docs/contract.md
decisions:
  - "visionVeto.status 'mode3_held' 유지 — 'applied' 재사용 금지 (result.tsx vetoApplied 파생 의미 오염 방지, RESEARCH Pattern 1 옵션 a)"
  - "clean md(전 편차 tolerance 이내) → records 0 + final 100 방출 — mode1 no_fault clean 선례(260630-l4e) 동일 원리, 투명 tally 가 authoritative"
  - "quant sentinel(quantificationStatus='mode3_measured_seed', in-process 전용)로 §10.5 unavailable 폴백 우회 — md substrate 실재 시 폴백은 오적용 (아래 Deviations 참조)"
  - "contract.md 단독 서술 갱신(§10.7) — analysis.ts/models.py 무변경이므로 3-way lockstep 커밋 불필요 (계약 필드 신설 0)"
metrics:
  duration_min: 25
  tasks_completed: 2
  files_created: 1
  completed_date: 2026-07-16
---

# Phase 29 Plan 02: Mode3 점수 내역 백엔드 절개 Summary

**한 줄:** `_apply_vision_veto_from_context` 의 mode3_held passthrough 를 "md(RTMW ipsf_absolute measured seed) 보유 시 tally-eligible" 로 확장 — mode3 등록 동작이 Gemini 무호출로 투명 감점-합산 deductionBreakdown 을 방출하고 overallScore == final 항등을 지키며, md 빈 dict(빈 criteria 4동작 + 미등록)는 byte-불변 passthrough 로 위양성 0=100 을 차단한다.

## 수행 내역

### Task 1 — Wave 0 RED 테스트 (commit 69bb7ef)

`backend/tests/test_mode3_tally_seam.py` — D-01/D-02/D-03 매트릭스 7케이스, 전부 mock-based (실 Gemini/S3/boto3 import 0, grep 검증 완료):

1. D-01 방출: md 보유 → breakdown 방출, records 전부 `deviationSource=ipsf_absolute`, status `mode3_held` 유지 ('applied' 아님)
2. D-02 항등: `overallScore == final == max(0, round(100 + Σ points))` — 엔진 산술 그대로
3. D-03 미방출: md `{}` → breakdown 부재 + `out == {**입력, visionVeto:{status:mode3_held}}` byte-불변
4. clean tally: 편차 tol(20°) 이내 → records 0, final 100 방출
5. Gemini 무호출: `assess_fault_severity` + `_collect_vision_fault_context` raise sentinel 설치 후 정상 통과
6. 형제 status 무회귀: resource_limited/disabled/missing_reference/missing_current_video/skipped_error 는 md 있어도 미방출 + 점수 불변
7. D-02 sub-clause: 방출 dict 신규 키 == {deductionBreakdown, visionVeto} 뿐 — pre-tally 점수 나르는 별도 필드 0 (성장 델타 = 저장 overallScore 단일 소스 고정)

RED 확인: 1/2/4/7 FAIL + 3/5/6 PASS, pytest 종료코드 1 — plan 명세 그대로.

### Task 2 — seam 구현 + contract §10.7 (commit 26b1c6b)

`_apply_vision_veto_from_context` 비측정-status 분기 안에 mode3_held 절개:

- `status == "mode3_held" and measured_deviations` → `deduction_engine.tally(...)` 실행, `breakdown.fallback != "quantification_unavailable"` 이면 `overallScore: breakdown.final` + `deductionBreakdown: breakdown.to_dict()` + `visionVeto: {"status": "mode3_held"}` 방출
- 내부 try/except graceful — tally 실패 시 로그 후 기존 mode3_held passthrough (분석 차단 0)
- mode1 TALLY-ELIGIBLE 3-status tuple byte-불변 (diff 는 순수 삽입 — 삭제 0), collect 의 mode3 조기 bail(:2000)·md 빌더(:4137) 무접촉
- `docs/contract.md` §10.7 신설 — mode3 방출 조건/status 불변/항등/미방출 서술만 (신규 필드 0, `grep -c mode3` 32→38)

## 검증 결과

- `pytest tests/test_mode3_tally_seam.py tests/test_pipeline_deduction_seam.py` — 32/32 PASS (RED→GREEN + mode1 seam 무회귀)
- `pytest tests/test_pipeline_mode3.py` 포함 66/66 PASS
- backend/tests 전체(수집 가능분 2616): **변경 전후 failure set diff = 0** — base commit 에 app.py 원복 후 동일 커맨드로 비교, 44건 pre-existing FAIL 세트 byte-동일 (신규 실패 0). pre-existing 44건 + collection error 12건 + tests/pipeline 15건은 로컬 heavy deps(imageio 등)/자격 부재 환경 문제 — `deferred-items.md` 에 기록, 미수정 (scope boundary)
- `models.py` / `analysis.ts` diff 0 (계약 필드 신설 없음)
- mode3 경로에서 'applied' 방출 0 (테스트 케이스 1 단언 + diff grep 0)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan 내부 모순] tally 시그니처 `(None, None, ...)` 이 clean-md 케이스와 충돌 — quant sentinel 로 해소**
- **Found during:** Task 2 (Task 1 케이스 4 설계 시 발견)
- **Issue:** plan 은 legacy 선례(:2492) 의 `tally(None, None, ...)` 를 지시했으나, quant=None 이면 엔진의 §10.5 unavailable 폴백 게이트(`quant_unavailable and not activated`)가 clean md(전 편차 tolerance 이내 → seeded 0)에서 발화해 fallback-only breakdown 을 반환한다. 이는 plan 자신의 게이트("fallback-only 면 passthrough")와 결합하면 케이스 4("clean md → breakdown 방출 + final 100")·must_haves truth 1("md 비어있지 않으면 방출")과 모순.
- **Fix:** in-process 전용 `VisionQuantificationResult(quantificationStatus="mode3_measured_seed")` sentinel 을 tally 에 전달해 폴백 게이트를 우회. §10.5 폴백은 "측정 자체 불가(양쪽 substrate 빔)" 전용이고 mode3 는 md substrate 가 실재하므로 measured-seed 산술이 정도(正道) — mode1 no_fault clean 선례(quant available, 260630-l4e)와 동일 결과 형상. sentinel 객체는 저장/방출 경로에 실리지 않음 (breakdown.to_dict 에 quant status 없음). `breakdown.fallback != "quantification_unavailable"` 방어 게이트는 plan 대로 유지 (도달 불가하지만 명시 불변식).
- **Files modified:** backend/functions/pipeline/app.py (주석으로 근거 명시)
- **Commit:** 26b1c6b

기타: plan 그대로 실행.

## D-02 sub-clause 확인 (성장 델타 tally 일관)

- 백엔드 방출 dict 점검: overallScore in-place 교체 단일, pre-tally 점수 별도 필드 방출 0 (테스트 케이스 7 고정)
- 앱 소비처 읽기 확인: `app/src/lib/userAnalyses.ts` / GrowthChart 계열은 doc.overallScore 를 소비 (코드 무변경)
- legacy prev doc(구점수) vs 신규 doc(tally 점수) 혼재 델타는 코드 방어 대상 아님 — **D-04 재분석 배너가 완충 (수용)**

## 참고 사항

- **production 미노출:** Pod 는 구코드 유지 — D-02 전환(overallScore=final)의 production 노출은 29-05 sweep 게이트(정은지 페어셋 mode3, SERIAL) PASS 후 Pod 재기동 시점. wave 구조가 전환 조건을 강제.
- **mode3 breakdown 의 fallback 필드:** records 가 있으면 `fallback='gemini_silent'` (Gemini 무지목 관측 마커, §10.5 기존 의미 그대로 — mode3 는 Gemini 가 애초에 안 돌았으므로 semantics 정합).
- criteria yaml 복원/신설 0 (RESEARCH Pitfall 1 준수 — kip-up/peter-pan/elbow-twist-sister/pdshape 빈 criteria 는 정상 동작).

## Known Stubs

없음 — 이 plan 산출물에 stub/placeholder 0.

## Threat Flags

없음 — 신규 네트워크/인증/파일 접근 표면 0. threat register T-29-02-01(mode1 회귀)=seam 테스트 32 green + tuple byte-불변으로 mitigate, T-29-02-02(seam 예외)=내부 try/except passthrough 로 mitigate, T-29-02-03(불투명)=100−Σ=final 항등 테스트 + deviationSource 'ipsf_absolute' provenance 로 mitigate. 패키지 설치 0.

## Commits

| Task | Commit | 내용 |
|------|--------|------|
| 1 | 69bb7ef | test(29-02): failing mode3 tally seam tests (RED) |
| 2 | 26b1c6b | feat(29-02): mode3_held tally seam + contract §10.7 |

## Self-Check: PASSED

- 생성 파일 4종 존재 확인 (test/app.py/contract.md/SUMMARY)
- 커밋 3건 존재 확인 (69bb7ef / 26b1c6b / docs)
- working tree clean (테스트 부산물 .pyc 원복)
