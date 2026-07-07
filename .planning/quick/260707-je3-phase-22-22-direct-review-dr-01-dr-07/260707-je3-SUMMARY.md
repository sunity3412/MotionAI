---
phase: quick-260707-je3
plan: 01
subsystem: planning-docs
tags: [phase-22, plan-revision, direct-review, dr-01-07]
requires: [".planning/phases/22-custom-vlm-finetune/22-DIRECT-REVIEW.md"]
provides:
  - "Phase 22 플랜 7개 수정본 (22-01/02/03/04/07/08/10) — DR-01~07 + P2 3건 반영"
affects: [phase-22-execution]
tech-stack:
  added: []
  patterns: ["blocking checkpoint(canary-first + rollback 선기록)", "fail-closed gate(--require-pass)", "manifest video_hash join"]
key-files:
  created: []
  modified:
    - .planning/phases/22-custom-vlm-finetune/22-01-PLAN.md
    - .planning/phases/22-custom-vlm-finetune/22-02-PLAN.md
    - .planning/phases/22-custom-vlm-finetune/22-03-PLAN.md
    - .planning/phases/22-custom-vlm-finetune/22-04-PLAN.md
    - .planning/phases/22-custom-vlm-finetune/22-07-PLAN.md
    - .planning/phases/22-custom-vlm-finetune/22-08-PLAN.md
    - .planning/phases/22-custom-vlm-finetune/22-10-PLAN.md
decisions:
  - "22-03/22-04/22-08 autonomous: false — production Pod 변형과 증류 비용이 blocking checkpoint 뒤로 이동"
  - "train/val split 소유권 = build_jsonl.py 단독, SFT는 explicit val 소비(미지원 시 val 미발행 + eval gate가 validation owner)"
  - "assert_gates 이중 모드: 기본(SKIPPED-only exit 0) / --require-pass(전 게이트 PASS 아니면 exit 비0) — Wave 5 진입 조건"
metrics:
  duration: "~8분"
  tasks: 3
  files: 7
  completed: 2026-07-07
---

# Quick 260707-je3: Phase 22 플랜 DR-01~07 반영 Summary

22-DIRECT-REVIEW.md의 BLOCK verdict 편집 요건(P0 3건 + P1 4건 + P2 3건)을 Phase 22 플랜 문서 7개에 외과 반영 — replan 0, 소스 코드 diff 0.

## Task Commits

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | 22-04 + 22-02 데이터 유입/비용/split/verify (DR-01/04/05/06/07, P2-LICENSE) | 0892e88 | 22-04-PLAN.md, 22-02-PLAN.md |
| 2 | 22-03 + 22-08 production Pod blocking checkpoint + canary/rollback (DR-02, DR-07) | 618ed5c | 22-03-PLAN.md, 22-08-PLAN.md |
| 3 | 22-07 게이트 fail-open 제거 + split 소비 정합, 22-01/22-10 P2 (DR-03/04, P2-2201/2210) | 981ee6f | 22-07-PLAN.md, 22-01-PLAN.md, 22-10-PLAN.md |

## DR 항목별 반영 내역

- **DR-01 (P0)**: 22-04 Task 2 — shadow 유래 샘플은 manifest.json video_hash join 필수. row 부재/anonymized != true → text-only verdict 라벨만(media 참조 0). 프레임 사용 = anonymized=true + 등록된 anonymized S3 key. _meta.shadow_unregistered_dropped / shadow_text_only_count 카운터. behavior Test 9/10 추가, must_haves truth 보강.
- **DR-02 (P0)**: 22-03 Task 2/3 사이 + 22-08 Task 1/2 사이 blocking checkpoint(`gate="blocking"`) 삽입 — canary-first 우선, 현재 Pod 직접 시 rollback 블록(env revert / start_server.sh revert / 재기동 / health / Lambda RUNPOD_ANALYZE_URL sync) 전제. 두 플랜 autonomous: false, Pod 변형 태스크 action 첫머리에 "(0) rollback 블록 선기록" 스텝. 22-08 폴백 전환 시에도 production 원복 선행 명시.
- **DR-03 (P0)**: 22-07 Task 3 verify에서 `assert_gates.py; test $? -le 1` fail-open 제거 → 로컬 unit 모드는 test_assert_gates.py만. `--require-pass` 플래그 스펙(전 게이트 PASS 아니면 SKIPPED 포함 exit 비0) + post-Pod acceptance + Wave 5 진입 조건(--require-pass PASS 또는 belle 명시 결정, 암묵 진행 금지) — action/truths/success_criteria 3곳 정합.
- **DR-04 (P1)**: split 단일 소유. 22-04 "D-06 split_dataset_ratio 정합" 삭제 → build_jsonl.py 단독 소유 선언. 22-07 `--split_dataset_ratio 0.02` 제거 → explicit val 파일 인자 확인·명시 소비, 미지원 시 val 미발행 + eval gate = validation owner 문서화. 두 파일에서 이중 split 문구 0.
- **DR-05 (P1)**: 22-04 Task 2/3 사이 증류 비용 blocking checkpoint 삽입(대상 행 수·teacher/judge call 수·quota probe·첫 run 10 rows·abort threshold), 기존 Task 3 → Task 4. autonomous: false.
- **DR-06 (P1)**: build_jsonl 진입점 `_meta.collection_complete is true` assert — `--partial` 없이 false/부재 시 즉시 실패, --partial run은 canonical prefix 업로드 금지. behavior Test 11. 22-02에 fail-closed 책임 소재 cross-ref.
- **DR-07 (P1)**: 22-04 Task 1 delete-in-finally를 fake client unit test(test_gemini_teacher.py)로 실증 + verify에 pytest 추가. 22-04 S3 prefix listing → head-object(object key). 22-03 collect-only pytest(`--co`) 제거 → full-suite 실 실행 + baseline FAILED/ERROR diff 기록.
- **P2-2201**: 22-01 Task 2 verify에 `source_doc_count >= 30` assert, print-only 통과 금지.
- **P2-2210**: 22-10 "env 1개" 전 출현(5곳) → "역할당 env 1개" — 3개 role-specific env 설계 유지, 문구만 정정.
- **P2-LICENSE**: 22-02 LICENSE-AUDIT A9 이월 항목에 "법률 검토 서명 전 release-clean 미함의" 명시 + `grep -c "release-clean"` acceptance.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 22-07에 추가한 fail-open 금지 문구가 자기 verify를 위반**
- **Found during:** Task 3
- **Issue:** action에 "fail-open(`test $? -le 1` 류) 금지"라고 리터럴을 적어 `! grep -qF 'test $? -le 1'` 체인이 FAIL
- **Fix:** "fail-open(exit 코드 1 이하를 통과로 간주하는 verify) 금지"로 리터럴 없이 재서술
- **Files modified:** 22-07-PLAN.md
- **Commit:** 981ee6f

**2. [Rule 1 - Bug] 22-10 replace_all이 선편집된 truth 라인을 이중 접두**
- **Found during:** Task 3
- **Issue:** truth를 먼저 "역할당 env 1개(one env per role...)"로 편집한 뒤 전 출현 replace_all을 돌려 "역할당 역할당" 발생
- **Fix:** 해당 라인 단건 수정으로 원복 — 최종 'env 1개' 5회 == '역할당 env 1개' 5회
- **Files modified:** 22-10-PLAN.md
- **Commit:** 981ee6f

**3. [Rule 2 - Consistency] 22-04 Task 2 acceptance 테스트 카운트 정합**
- **Found during:** Task 1
- **Issue:** behavior에 Test 9~11을 추가하면서 acceptance "6 tests"가 실제 정의(11종)와 불일치 확대
- **Fix:** "≥ 11 tests"로 갱신 (구조 변경 아님, 카운트 정합)
- **Files modified:** 22-04-PLAN.md
- **Commit:** 0892e88

## Verification

- Task 1/2/3 verify grep 체인 전부 GREEN (TASK1-OK / TASK2-OK / TASK3-OK)
- 7개 플랜 frontmatter YAML 파싱 유효, wave/depends_on/plan 번호 전부 불변 — replan 0
- checkpoint 삽입 3개 플랜(22-03, 22-04, 22-08) 전부 autonomous: false
- 소스 코드(.py/.ts/.sh) diff 0 — git diff HEAD~3 HEAD는 .planning 플랜 문서 7개만

## Next

- opus 재검증 (22-DIRECT-REVIEW.md 재대조)
- belle 외부 리뷰
- 제품결정 3건 미결(22-PLAN-REVIEW.md 참조)은 이 quick task 범위 밖

## Self-Check: PASSED
