---
phase: 22-custom-vlm-finetune
plan: 01
subsystem: testing
tags: [vlm, datagen, schema, json-spec, synthetic-perturbation, rtmw, self-label]

# Dependency graph
requires:
  - phase: 24-transparent-deduction-scoring
    provides: "감점 엔진 계약 (deduction_engine.supported_differences 소비 키) — faults[] 상위집합 lockstep 기준"
  - phase: 25-05
    provides: "vision_veto.FAULT_CATEGORIES 고정 enum 단일 owner (schema fault_category 검증 재사용)"
provides:
  - "backend/training/datagen/schema.py — D-11 JSON 규격 + D-01 통합 리포트 v1 스키마 단일 owner (REPORT_KEYS, discretize/undiscretize, filter_joints, select_frame_indices, bind_key_prompt, normalize_report)"
  - "backend/training/datagen/perturb.py — 합성 교란 순수 모듈 (자가 라벨: 정답=원좌표, 3단 커리큘럼, 실측 분포 샘플, 시간역전 함정)"
  - "backend/training/datagen/rtmw_error_profile.json — 실 RTMW 오류 분포 artifact (source_doc_count=247, A3 해소)"
  - "backend/tests/phase22/ — schema + perturb 계약 테스트 (16 GREEN)"
affects: [22-04 JSONL 조립, 22-05 bake-off, 22-08 서빙 파서, 22 SFT 학습]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "데이터 규격 단일 owner 모듈 (schema.py) — 학습/bake-off/서빙 파서 공유"
    - "순수 교란 모듈 (numpy 단독, boto3/네트워크 0, (T,J,C) shape 계약 ValueError)"
    - "실측 분포 artifact 기반 합성 교란 (curve-fit 아닌 오류 '분포' 측정)"

key-files:
  created:
    - backend/training/datagen/schema.py
    - backend/training/datagen/perturb.py
    - backend/training/datagen/measure_error_profile.py
    - backend/training/datagen/rtmw_error_profile.json
    - backend/training/datagen/__init__.py
    - backend/tests/phase22/conftest.py
    - backend/tests/phase22/test_schema.py
    - backend/tests/phase22/test_perturb.py
  modified: []

key-decisions:
  - "faults[] 서브스키마 = gemini_vision_scorer v8.1 differences[] 미러(severity 제외) + part_scope — DEDUCTION_CONSUMED_KEYS 상위집합으로 감점 엔진 무수정 소비"
  - "좌표 이산화 = 000~999 3자리 정수(CogVLM 방식), <loc_NNN> 어휘 확장 아님 — 토크나이저 무접촉"
  - "저신뢰 임계 0.3은 측정 정의(관측 기준)이며 교란 수치 아님 — _meta.measurement 로 투명 노출"
  - "confidence 채널은 result.keypointReport.confidence(flat, [0,1], frames×J), 각도 점프는 top-level angles(T,J flat) — 두 소스 분리"

patterns-established:
  - "REPORT_KEYS/FAULT_ITEM_KEYS 알파벳 정렬 + Null 고정 + 화이트리스트 normalize (D-11 4철칙 단일 owner)"
  - "PerturbResult(frozen, eq=False) — perturbed/original(정답)/perturbed_joints/perturbed_frames/stage"

requirements-completed: [FT-03]

# Metrics
duration: 18min
completed: 2026-07-09
---

# Phase 22 Plan 01: Wave 0 데이터 엔진 코어 Summary

**D-11 JSON 규격 + D-01 통합 리포트 v1 스키마 단일 owner(schema.py) + 실측 RTMW 오류 분포 artifact(247건) + 실측 분포 기반 합성 교란 순수 모듈(perturb.py, 자가 라벨) — 전부 테스트로 고정.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-07-09T01:44:00Z
- **Completed:** 2026-07-09T02:02:10Z
- **Tasks:** 3 / 3
- **Files created:** 8

## Accomplishments

- **schema.py (D-11 + D-01 단일 owner):** REPORT_KEYS 5출력(coaching/corrected_coords/faults/segments/svg_spec/time_anchors, 알파벳 정렬, score/severity 영구 부재). normalize_report(화이트리스트 + Null 고정 + 키 알파벳 정렬 + fault_category enum 강제), discretize/undiscretize(000~999 3자리 정수, 왕복 ≤ 1/1000), filter_joints(얼굴/손가락 사전 필터), select_frame_indices(9fps 균등 서브샘플), bind_key_prompt(키 사전 바인딩). FAULT_ITEM_KEYS ⊇ DEDUCTION_CONSUMED_KEYS lockstep — 감점 엔진 무수정 소비.
- **rtmw_error_profile.json (A3 해소):** Firestore analyses collection_group 읽기 전용 측정 → 3종 히스토그램(confidence_drop_run_length / per_joint_jump_deg 관절별 / low_confidence_joint_rank). source_doc_count=247(≥30). 교란 수치 하드코딩 0 — 오류 '분포'만 측정. T-22-01: 식별자 미포함 화이트리스트 검증.
- **perturb.py (D-10a 자가 라벨):** perturb_sequence(정답=원좌표 보존, stage 1/2/3 커리큘럼), 가려짐 Null(NaN)+confidence 저값(키 삭제 금지), 파라미터는 rtmw_error_profile 분포 샘플(profile=None → TypeError), swap_lr_joints + make_temporal_trap(Pitfall 6 순열 함정). numpy 단독, 재현 가능.

## Task Commits

1. **Task 1: schema.py — D-11 규격 + D-01 리포트 v1 스키마** — `bfd9a89` (test) → `b7b62ee` (feat)
2. **Task 2: 실 RTMW 오류 분포 측정 → artifact** — `612afdc` (feat)
3. **Task 3: perturb.py — 합성 교란 순수 모듈** — `a0d2898` (test) → `c1feb2a` (feat)

_TDD tasks 1·3: test(RED) → feat(GREEN) 2-commit._

## Files Created/Modified

- `backend/training/datagen/schema.py` — D-11 4철칙 + D-01 리포트 v1 스키마 단일 owner (272 lines)
- `backend/training/datagen/perturb.py` — 합성 교란 순수 모듈, 자가 라벨 생성기 (296 lines)
- `backend/training/datagen/measure_error_profile.py` — Firestore 읽기 전용 오류 분포 측정 스크립트
- `backend/training/datagen/rtmw_error_profile.json` — 실측 히스토그램 artifact (source_doc_count=247)
- `backend/training/datagen/__init__.py` — datagen 패키지 docstring
- `backend/tests/phase22/conftest.py` — shared layer + training 패키지 sys.path 주입
- `backend/tests/phase22/test_schema.py` — 9 tests (규격/이산화/Null/정렬/필터/서브샘플/lockstep)
- `backend/tests/phase22/test_perturb.py` — 7 tests (자가 라벨/Null/분포 출처/커리큘럼/함정/재현/shape)

## Decisions Made

- **faults[] 서브스키마 설계:** gemini_vision_scorer SCHEMA v8.1 differences[] 를 미러하되 severity(비채점 라벨)를 의도적으로 제외하고 part_scope 를 추가. lockstep 테스트가 `gemini_diff_keys - {severity} ⊆ FAULT_ITEM_KEYS` 를 강제 — 감점 엔진이 새 소비 키를 추가하면 스키마도 따라오도록 봉인.
- **DEDUCTION_CONSUMED_KEYS 상수:** deduction_engine 이 실제로 읽는 키(각도쌍·approx·body_part·fault_state·correct_state·ipsf_note·fault_category)를 명시. FAULT_ITEM_KEYS 의 부분집합 assert 로 drift 시 FAIL.
- **저신뢰 임계 0.3:** 교란 강도가 아니라 오류를 '관측'하는 측정 정의. `_meta.measurement` 로 투명 노출해 curve-fit 논란 차단.

## Deviations from Plan

None - plan executed exactly as written. (3 tasks, acceptance criteria 전부 충족; 아키텍처/스코프 변경 0.)

## Issues Encountered

- **Firestore 스키마 확인:** angles(top-level flat, T×J)는 8 body 각도, confidence 는 result.keypointReport.confidence(flat, frames×J_kp, [0,1])로 분리 저장됨을 실 문서 probe 로 확인 후 두 소스를 각각 소비하도록 측정 로직 구성. 로컬 서비스계정(FIREBASE_SA_PATH=firebase-sa.json)으로 collection_group 접근 — 실사용 유효분 247건 확보(≥30, reference 보강 불필요).

## User Setup Required

None - 로컬 Firestore 읽기(read-only)만 사용, 외부 서비스 신규 구성 없음. Pod/GPU 미사용(LOCAL ONLY 준수).

## Next Phase Readiness

- FT-03 라벨링 (a) 합성 교란 트랙이 실측 분포 기반으로 가동 가능. schema.py 가 후속 plan(22-04 JSONL 조립 / 22-05 bake-off / 22-08 서빙 파서)의 단일 규격 소스로 준비됨.
- D-11 규격 위반이 코드 리뷰가 아니라 테스트로 잡히는 상태 확립 (16 GREEN).
- 회귀 0: 전체 backend 스위트 pre-existing 실패(python 3.14 / numpy 2.x / google-genai 환경)와 base 커밋 대비 동일(baseline diff IDENTICAL). phase22 신규 16 tests 전부 GREEN.

## Self-Check

- 파일 8개 생성 확인 (아래 검증).
- 커밋 5개 존재 확인 (bfd9a89/b7b62ee/612afdc/a0d2898/c1feb2a).

---
*Phase: 22-custom-vlm-finetune*
*Completed: 2026-07-09*
