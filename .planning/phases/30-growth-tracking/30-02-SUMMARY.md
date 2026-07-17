---
phase: 30-growth-tracking
plan: "02"
subsystem: backend-contract
tags: [mode3, contract, data-accretion, D-04, lockstep]
requires:
  - "assemble.build_mode3 (Phase 19 scoring_basis 패턴)"
  - "TechniqueProfile.motion_id/name (technique.py)"
  - "_mode3_comparison first/progress 분기 (pipeline app.py)"
provides:
  - "Mode3Comparison.recognizedMotionId?/recognizedMotionName? optional 필드 (3-way)"
  - "build_mode3 recognized_motion_id/name kwargs (None→키 미추가, 비-str ValueError)"
  - "mode3 first·progress comparison 에 인식 동작 id/명 적립 (Firestore)"
affects:
  - "Phase 16 (학원 명칭 카테고리 체계) — 이 필드 소비 예정"
tech-stack:
  added: []
  patterns:
    - "scoring_basis None→키 미추가 패턴 복제 (legacy 동형 보존)"
    - "3-way lockstep 단일 atomic commit (analysis.ts + models.py + contract.md + builder)"
    - "builder 가 타입 강제 owner (T-30-03) — 호출부 조건 분기 불필요"
key-files:
  created:
    - ".planning/phases/30-growth-tracking/30-HUMAN-UAT.md"
  modified:
    - "app/src/types/analysis.ts"
    - "backend/shared/python/sunity_shared/models.py"
    - "docs/contract.md"
    - "backend/shared/python/sunity_shared/analysis/assemble.py"
    - "backend/functions/pipeline/app.py"
    - "backend/tests/test_assemble.py"
    - "backend/tests/test_pipeline_mode3.py"
decisions:
  - "recognized 필드는 build_mode3 early return 앞에 emit — 첫 분석(is_first=True)도 방출 (REVIEW HIGH-3)"
  - "저신뢰 억제(_apply_score_suppression)와 독립 emit — D-04 는 데이터 적립 목적, 신뢰도 처리는 소비 시점(Phase 16)"
  - "SAM 배포 보류 — CloudFormation ResourceExistenceCheck early-validation 훅 실패(선존 인프라, 순수 Python diff 무관). Pod OFF 라 production 회귀 0"
metrics:
  duration_min: 20
  tasks: 3
  files_changed: 8
  completed: 2026-07-17
---

# Phase 30 Plan 02: mode3 recognized motion 데이터 적립 (D-04) Summary

mode3 파이프라인이 이미 인식하던 동작 id/명(`TechniqueProfile.motion_id`/`name`)을 분석 문서 `comparison` 에 optional 필드로 방출 시작 — Phase 16(학원 명칭 카테고리)이 소비할 데이터를, legacy 무마이그레이션·채점 무접촉으로 적립.

## 무엇을 만들었나

- **3-way 계약 (단일 atomic commit, 59f2376):** `analysis.ts` Mode3Comparison 에 `recognizedMotionId?`/`recognizedMotionName?` + `models.py` Phase 30 D-04 명세 주석 + `docs/contract.md §4` 서술 + `assemble.build_mode3` kwargs 2개 + 테스트 4건.
- **build_mode3 방출 규칙:** `recognized_motion_id` None(FallbackRecognizer/인식 실패) → 두 키 미추가(legacy dict 바이트 동일 보존). str 이 아니면 ValueError(T-30-03 타입 강제). name 은 truthy 일 때만 emit. **emit 블록은 early return 앞** — 첫 분석(is_first=True)도 실어보낸다(REVIEW HIGH-3).
- **pipeline 배선 (93d9827):** `_mode3_comparison` 의 first·progress 두 `build_mode3` 호출에 `recognized_motion_id=profile.motion_id, recognized_motion_name=profile.name` 추가. 저신뢰 억제와 독립 emit. 순수성 유지(신규 import·부수효과 0).
- **HIGH-3 false-green 차단:** `test_pipeline_mode3.py` 에 `motion_id="ref-foo"` 실린 `_recognized_profile()` 픽스처로 first·progress **양 경로** 방출을 pytest 로 증명 + `motion_id=None` negative test. grep 배선은 보조 증거로만.
- **Ops 적립 (30-HUMAN-UAT.md, 8b5cf1f):** 실효 런타임=Pod(OFF) → 재가동 시 git pull 자동 반영 + `recognizedMotionId` 저장 확인 항목. SAM 배포 보류 사유 박제.

## 검증 결과

- `pytest tests/test_pipeline_mode3.py tests/test_assemble.py -q` → **53 passed**. 기존 `test_mode3_first_has_no_delta` 의 `assert c == {"mode":"mode3","isFirst":True}` 무수정 통과(backward-compat 증명).
- `npm run typecheck` → exit 0 (analysis.ts optional 필드 추가분).
- lockstep grep: `recognizedMotionId` = analysis.ts 1 / assemble.py 1 / contract.md 2. `firestore_admin.py`·`userAnalyses.ts` = 0 (무변경 확인).
- `grep -c "recognized_motion_id=profile.motion_id" pipeline/app.py` = 2 (first + progress).
- 채점 무접촉: 변경 파일 8개 중 dimensions/kismam/deduction 계열 **0건**. pipeline diff 는 build_mode3 kwargs + 주석만(비-주석 코드 변경 0).

## Deviations from Plan

### 배포 보류 (Task 3 — 계획된 graceful 분기)

**1. [Rule 3 - 인프라 블로커] SAM 배포 CloudFormation early-validation 실패**
- **Found during:** Task 3 (`sam deploy`)
- **Issue:** `sam build --use-container` 는 성공했으나 `sam deploy` 가 변경셋 생성 단계에서 `AWS::EarlyValidation::ResourceExistenceCheck` 훅 검증 FAILED (2회 재시도 동일 — transient 아님).
- **분석:** 스택 `sunity-motion-pilot` 은 정상(`UPDATE_COMPLETE`, 직전 배포 2026-07-16 성공). 이번 diff 는 순수 Python(layer + pipeline function)이라 CloudFormation 리소스를 추가·삭제하지 않음 → ResourceExistenceCheck 실패는 이 코드가 아니라 계정/스택의 선존 리소스 의존성에서 발생. 후속 hook 상세 조회는 환경 권한 제약으로 미실행.
- **처리:** 플랜 Task 3 의 "배포 불가 시" 분기대로 30-HUMAN-UAT.md ops 노트 + 본 deviation 에 박제 (acceptance "둘 중 하나 충족" 만족). **영향 없음** — 실효 런타임(Pod) OFF 라 production 실분석 미수행 중, Pod 재가동 시 git pull 로 D-04 코드 반영. 코드는 배포 준비 완료.
- **재시도 명령:** `cd backend && AWS_PROFILE=sunity-motion sam build --use-container && sam deploy --no-confirm-changeset --no-fail-on-empty-changeset`

Rules 1/2 자동수정: 없음 — 플랜대로 실행.

## Known Stubs

없음 — 이번 phase 화면은 이 필드를 소비하지 않는다(계획된 데이터 적립층). 소비는 Phase 16(계약 주석·contract.md·30-CONTEXT D-04 에 명시). 스텁 아님, 의도된 미소비.

## Threat Flags

없음 — 신규 network endpoint/auth path/schema 경계 변경 0. threat_model 의 T-30-03(타입강제 ValueError)/T-30-04(억제 독립 accept)/T-30-05(동작명 non-PII accept) 모두 계획대로 처리.

## Self-Check: PASSED

- FOUND: `.planning/phases/30-growth-tracking/30-HUMAN-UAT.md`
- FOUND: `.planning/phases/30-growth-tracking/30-02-SUMMARY.md`
- 커밋 3건 존재: 59f2376(Task 1) / 93d9827(Task 2) / 8b5cf1f(Task 3)
