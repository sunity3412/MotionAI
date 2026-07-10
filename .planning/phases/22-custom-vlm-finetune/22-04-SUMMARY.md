---
phase: 22-custom-vlm-finetune
plan: 04
subsystem: ml-training-data
tags: [gemini, distillation, jsonl, sft, teacher-student, rtmw, file-api, llm-judge]

# Dependency graph
requires:
  - phase: 22-01
    provides: "schema.py 단일 owner(REPORT_KEYS/bind_key_prompt/discretize/select_frame_indices) + perturb.py 합성 교란"
  - phase: 22-02
    provides: "manifest.json 131행(시드19+YT68+IG44) + S3 fixtures/phase22 + LICENSE-AUDIT"
  - phase: 22-03
    provides: "vlm_shadow 로깅 helper(store_vlm_shadow) — shadow 트랙 데이터 소스(향후)"
provides:
  - "gemini_teacher.py — 교사 증류 배치 (File API delete-in-finally + 4중 품질 필터 + 429 즉시 중단)"
  - "full_batch.py — 재개 가능 full batch 러너 (행별 디스크 영속화, error/429만 재시도) + assemble_jsonl 조립 엔트리"
  - "build_jsonl.py — 3트랙 조립기 + 중첩 타입 강제(normalize_report 단일 지점)"
  - "SFT 학습셋 — s3://sunity-motion-pilot-videos/training/phase22/jsonl/ (train.jsonl 99행 + val.jsonl 2행 + _meta.json)"
  - "manifest 수집 마감 — collection_complete=true + balance_waiver (내부 371 fault track 이월 문서화)"
  - "Pod 산출 원장 — /workspace/phase22_distill_out/ (reports/ 129 + accepted/ 109)"
affects: [22-06-bakeoff, 22-07-sft, 22-08-serving, 22-09-shadow-comparison]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "재개 가능 배치: 행별 결과 파일이 진실(메모리 반환 의존 금지), 터미널 사유만 skip — 과금 재발 0"
    - "중첩 타입 강제는 normalize_report 단일 owner(산탄 가드 금지) — str은 json.loads 1회 복구, 결정적 무손실 변환만 허용, 실패는 필드 None(행 유지)"
    - "게이트 우회 금지: 균등 게이트 미충족 마감은 _meta.balance_waiver 로 위반 항목 명시 문서화 + 테스트가 waiver 정확성 검증"

key-files:
  created:
    - backend/training/distill/gemini_teacher.py
    - backend/training/distill/full_batch.py
    - backend/training/distill/pod_coords.py
    - backend/training/datagen/build_jsonl.py
    - backend/tests/phase22/test_gemini_teacher.py
    - backend/tests/phase22/test_full_batch.py
    - backend/tests/phase22/test_build_jsonl.py
    - backend/tests/phase22/test_pod_coords.py
  modified:
    - backend/training/datagen/schema.py
    - backend/training/data/manifest.json
    - backend/tests/phase22/test_schema.py
    - backend/tests/phase22/test_manifest_consistency.py

key-decisions:
  - "시험 배치 10행 → full batch 승인 전 3라운드 진단으로 교사/judge 결함 4건을 129행 과금 전에 fix (enum 미제공/동작명 미주입/judge 루브릭 편향/배열 파싱)"
  - "수집 마감 = balance_waiver 문서화 (silent 우회 금지) — fault 표본은 내부 371 track 다음 라운드 이월, JSONL 균등은 _balance_media 소유"
  - "교사 출력 중첩 타입 혼돈(coaching list 47행 등)은 휴리스틱 0 인 결정적 무손실 변환만 허용 — 스키마 환원 불가 형태는 None(D-11 스키마 순수성)"
  - "judge 점수는 필터 임계로만 사용, 라벨 미저장 (객관성 hard gate)"

patterns-established:
  - "distill accepted/<slug>.json = build_jsonl distill_loader 계약 (video_hash/s3_key/motion/thought/report/joint_keys/coords_by_frame)"
  - "manifest_with_hashes: manifest 행에 video_hash 주입(사본) — s3_key join 보강, 파일 불변"

requirements-completed: [FT-02]  # FT-03 부분: (b)증류 경로 완성·합류, (a)perturb/(c)shadow 는 JSONL 미합류 — Known Limitations 참조

# Metrics
duration: 다중 세션 (2026-07-09 Tasks 1-2 → 2026-07-10 시험배치+full batch 밤샘 → 2026-07-11 조립/업로드 마감)
completed: 2026-07-11
---

# Phase 22 Plan 04: Gemini 교사 증류 + 학습 JSONL 조립 Summary

**Gemini 3.1 Pro 교사 증류 full batch 129/129 (수락 109, File API 잔여물 0) → SFT 학습셋 train.jsonl 99행 / val.jsonl 2행을 S3 training/phase22/jsonl/ 에 완성. 시험 배치 3라운드가 129행 과금 전에 교사/judge 결함 4건을 잡았고, 조립기는 교사 출력 중첩 타입 혼돈을 normalize_report 단일 지점에서 결정적 무손실 변환으로 흡수.**

## Performance

- **Duration:** 다중 세션 — 2026-07-09 (Tasks 1-2 로컬) → 2026-07-10 (시험 배치 3라운드 + full batch 밤샘, 행당 ~3-5분) → 2026-07-11 (조립 fix + S3 업로드 마감)
- **Completed:** 2026-07-11 02:31 KST (S3 업로드 확인)
- **Tasks:** 4/4 (Task 3 = blocking checkpoint, belle "approved" 경유)
- **Files modified:** 12 (핵심 모듈 5 + 테스트 5 + manifest + schema)

## Accomplishments

- **교사 증류 full batch 129/129 터미널** — 수락 109 / rejected_judge 12 / rejected_parse 6 / rejected_contract 2. 소스별 수락률: IG 91% / internal 88% / YT 79%. judge 분포 건강(9점 69 + 10점 39, 폐기는 0~6점) — 시험 배치의 루브릭 fix(eb69692) 이후 "전부 10점" 붕괴 없음. File API 잔여물 0 (delete-in-finally + 종료 검사).
- **SFT 학습셋 S3 완성** — `training/phase22/jsonl/` train.jsonl 2.58MB 99행(distill 87 + text 14) / val.jsonl 2행 / _meta.json. video_hash 단위 split(leakage 0), validation_owner=explicit_val_jsonl, 균등 트림 109→87(64동작, max=2 ≤ 2·min=1), hard_negative 0건 포함.
- **수집 마감 선언** (f66f25f) — `_meta.collection_complete=true` + `balance_waiver`(belle 승인 2026-07-10, 위반 항목 명시, 내부 371 fault track 이월). 게이트 테스트가 waiver 가 실제 위반을 정확히 커버하는지 검증(은폐 불가).
- **재개 가능 full batch 러너** (a9b36cd) — 행별 결과/accepted 즉시 디스크 영속화, 터미널 사유 skip(재실행 Gemini 호출 0), error/429 재시도, 진행 로그 [N/129]. 밤샘 실행 중 RTMW env 누락으로 행 6~11 error → 재기동이 설계대로 이어받아 회복(재개성 실증).
- **중첩 타입 강제 단일화** (25e6752, 1930099) — 교사 출력 실측: svg_spec str 6/list 7, coaching list 47/dict 7, corrected_coords dict 51, segments dict 37. normalize_report 에서 str→json.loads 1회 복구 + 결정적 무손실 변환(coaching 문장 리스트→개행 join, 프레임 키 dict→리스트, `{label:[s,e]}`→SEGMENT_KEYS)으로 라벨 보존: 최종 distill 87행 기준 coaching 80 / corrected_coords 68 / segments 74 채움.
- **phase22 테스트 156 passed / 1 skipped** (이 플랜에서 test_gemini_teacher 33 + test_build_jsonl 15 + test_full_batch 11 + schema/manifest 확장).

## Task Commits

1. **Task 1: gemini_teacher.py 교사 증류 배치** — `9d5e3ff` (feat)
2. **Task 2: build_jsonl.py 3트랙 조립기 (TDD)** — `955eeb3` (test RED) → `d1028f1` (feat GREEN)
3. **Task 3: 증류 비용 checkpoint + 시험 배치 3라운드** —
   - `5f2164c` (feat: run_trial_batch 스캐폴드) / `8fb4d97` (docs: 권한 게이트 차단 기록)
   - `34ec9b2` (feat: pod_coords RTMW 좌표 추출·캐시 — keypoints_2d 가 좌표 계약 정답, to_coco17_array 는 pole-aligned 3D 라 부적합)
   - 시험 배치 발견 fix 4건: `59ac1a1` (교사 프롬프트 fault_category enum 유효값 주입) / `c5b14ef` (동작명 주입 — 무맥락 180° 위양성 방지) / `eb69692` (judge 루브릭 faults 유무 2분기 + 스케일 앵커) / `ce992e0` (최상위 배열 JSON 파싱 + raw 보존)
4. **Task 4: 수집 마감 + full batch + 조립 + S3** —
   - `f66f25f` (data: collection_complete=true + balance_waiver)
   - `a9b36cd` (feat: full_batch 러너 + accepted 영속화 + assemble 엔트리)
   - `25e6752` (fix: 중첩 타입 강제 — str svg_spec assemble 크래시) / `1930099` (fix: 결정적 무손실 변환 — 실측 109행 형태 반영)
   - full batch 실행·`--assemble --upload` 는 메인 세션이 Pod(ns8smhcydnduq9, A100)에서 수행

## Files Created/Modified

- `backend/training/distill/gemini_teacher.py` — 교사 증류: File API 업로드 ACTIVE 폴링 + delete-in-finally(DR-07, fake client 로 증명), 교사 gemini-3.1-pro-preview / judge gemini-3.5-flash, 4중 필터(judge<7 + 반복 루프 + 물리 불가 궤적 + 뼈길이 + faults⊇DEDUCTION_CONSUMED_KEYS), holdout 격리 + 고객 anonymized 게이트(D-12), greenlight env(DR-05)
- `backend/training/distill/full_batch.py` — 재개 가능 러너 + aggregate_stats + make_distill_loader/manifest_with_hashes/assemble_jsonl(업로드는 uploader 주입 시에만 gated)
- `backend/training/distill/pod_coords.py` — Pod RTMW 좌표 추출·video_hash 캐시 (Gemini 무접촉, build_jsonl 좌표 표현 재사용)
- `backend/training/datagen/build_jsonl.py` — 3트랙 조립 + T3/텍스트 혼합 + validation_owner 계약 + collection_complete fail-closed(DR-06) + distill 입구 재정규화
- `backend/training/datagen/schema.py` — normalize_report 중첩 타입 강제(단일 owner, SCHEMA_VERSION 유지 — 구조 불변)
- `backend/training/data/manifest.json` — 수집 마감 메타(collection_closed/balance_waiver)
- `backend/tests/phase22/` — test_gemini_teacher / test_build_jsonl / test_full_batch / test_pod_coords 신설, test_schema / test_manifest_consistency 확장

## Verification (plan acceptance)

- [x] train.jsonl + val.jsonl S3 존재 + validation_owner=explicit_val_jsonl 정합 — `--assemble --upload` 후 S3 확인 완료 (2026-07-11 02:31 KST, 메인 세션)
- [x] gemini files.list 잔량 0 (full batch 종료 후 계측)
- [x] 동작별 카운트 max ≤ 2×min (_meta motion_counts: 64동작 max 2 / min 1), hard_negative 0건
- [x] `pytest backend/tests/phase22` — 156 passed / 1 skipped (skip = --check-s3 네트워크 마커)
- [x] 사람 숫자 점수 라벨 0 — judge 점수는 필터 임계로만, normalize_report 가 score 계열 키 차단

## Decisions Made

- **시험 배치 3라운드 → full batch** (DR-05 checkpoint 설계 적중): 10행 시험이 129행 과금 전에 결함 4건을 잡음 — (1) fault_category enum 유효값 미제공 → 3/3 rejected_contract, (2) 동작명 미주입 → 무맥락 "모든 관절 180°" 위양성(ref-climb 무릎 97° 사건), (3) judge 루브릭 편향 → 정타 faults:[] 구조적 저점 + 위양성 리포트 만점, (4) 최상위 배열 JSON 크래시.
- **균등 게이트 waiver 문서화**: collection_complete=true 를 켜면 22-02 균등 게이트가 현 수집분(fault 7/129)에 대해 FAIL — silent skip 대신 `_meta.balance_waiver` 로 위반 목록을 명시하고 테스트가 waiver 정확성을 강제. JSONL 단계 균등은 `_balance_media` 가 소유.
- **중첩 타입 정책**: 필드 단위 graceful(행 폐기 금지) + 휴리스틱 0 인 결정적 변환만. 스키마 환원 불가(SVG 마크업, 시간앵커 phase-map)는 None — 스키마 불일치 라벨을 학습에 남기지 않는다(D-11).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 균등 게이트 테스트가 마감 선언과 충돌**
- **Found during:** Task 4 (수집 마감 커밋 전 사전 점검)
- **Issue:** collection_complete=true 시 test_manifest_consistency 균등 게이트 활성 → 62동작 fault 0 / max 9 > 2·min 2 로 즉시 FAIL (belle 마감 결정과 모순)
- **Fix:** `_meta.balance_waiver`(승인·사유·이월트랙·unmet 목록) + 테스트를 waiver-aware 로 변경 — waiver 없는 위반은 여전히 FAIL, waiver 는 실제 위반을 정확히 커버해야 통과
- **Committed in:** f66f25f

**2. [Rule 1 - Bug] str svg_spec assemble 크래시 (+ 중첩 타입 전수)**
- **Found during:** Task 4 (--assemble 첫 실행, 메인 세션 발견 → 릴레이)
- **Issue:** normalize_report 가 최상위 키만 화이트리스트 — 교사가 svg_spec 을 SVG 마크업 str(6행)/원시도형 list(7행)로 산출 → `src_svg.get()` AttributeError
- **Fix:** normalize_report 단일 지점 중첩 타입 강제 + build_jsonl distill 입구 재정규화(디스크 적재분은 구 normalize 산출) + 실측 형태 결정적 무손실 변환(coaching 47행 등 구제)
- **Committed in:** 25e6752, 1930099

**3. [Rule 2 - Missing Critical] 교사/judge 프롬프트·파싱 결함 4건 (시험 배치 진단)**
- **Found during:** Task 3 (시험 배치 3라운드)
- **Fix:** enum 주입(59ac1a1) / 동작명 주입(c5b14ef) / judge 2분기 루브릭+앵커(eb69692) / 배열 파싱+raw 보존(ce992e0)
- **Verification:** full batch judge 분포 건강 + rejected_contract 129행 중 2건으로 감소

**Total deviations:** 3건 auto-fixed (Rule 1×1, Rule 2×1, Rule 3×1)
**Impact on plan:** 전부 정확성/게이트 정합 필수 fix. scope creep 없음 — 3트랙 완전체 축소는 아래 Known Limitations 의 명시적 이월.

## Known Limitations / 이월 (숨김 없음)

1. **val.jsonl 2행 = 매우 얇음.** video_hash split 0.02 × 89 media hash → val 2행. 22-07 SFT 의 val 게이트 검증력이 제약된다. 후속 조치 후보: val_frac 확대 재조립 또는 `validation_owner=phase22_eval_gate` 전환(held-out eval gate 가 검증 소유) — 22-07 진입 전 belle 결정.
2. **svg_spec 감독 신호 0/87.** 교사 SVG 출력이 전부 비스키마(마크업 str/원시도형 list) → None 강등. v1 리포트의 SVG 축(force_vector/ideal_trajectory)은 **이번 SFT 라운드에서 학습 불가**. 교사 프롬프트에 SVG_SPEC_KEYS 스키마 강제 문구 추가는 후속 증류 라운드 항목. (target_angle_deg 는 reference 결정적 산출이라 교사 무관 — reference_loader 배선 시 채워짐.)
3. **이번 JSONL 은 2트랙 (distill 87 + text 14).** perturb 트랙 미포함 — raw 좌표 영속화 부재(pod_coords 캐시는 이산화 서브샘플이라 교란 입력용 원좌표 재구성 불가). shadow 트랙 0행 — 22-03 배선 직후라 vlm_shadow 적재 데이터 없음. **3트랙 완전체는 22-07 SFT 전 소규모 후속 작업 필요** (perturb 는 raw (T,J,3) 좌표 영속화 추가 후 재조립).
4. **운영 이슈 (비용 소량 sunk):** 시험 배치 중 권한 게이트 차단 1회(8fb4d97 — 코디네이터 릴레이는 사용자 동의 아님) + foreground 실행 kill 로 인한 sunk call 소량(고아 File API 업로드 35개 정리, 잔량 0 복구) + Gemini 월 상한 도달 1회(belle 상향으로 해소).

## Issues Encountered

- **full batch 밤샘 중 RTMW env 누락** (RTMW_ONNX_PATH 등) — 행 6~11 error 후 재기동, 러너 재개성이 설계대로 이어받음(error 는 비터미널 → 재시도). 과금 재발 0.
- **Pod 교체 추적** — s7gyvvlc6u7ktz → hibluobp71cuy8 → ns8smhcydnduq9(A100 80GB, 현행). SSH 엔드포인트는 재생성마다 변경.

## User Setup Required

None — Gemini 키/AWS 는 기존 SSM·Pod env 재사용. (Gemini 월 상한 상향은 belle 이 이미 처리.)

## Next Phase Readiness

- **22-06 (bake-off):** 학습셋 무관 — A100 Pod 에서 진행 중 (728cf5f).
- **22-07 (SFT):** train.jsonl 소비 가능. 진입 전 결정 2건 — val 얇음 대응(위 Limitation 1) + 3트랙 완전체 여부(Limitation 3). validation_owner 계약은 _meta 로 방출됨.
- **Pod 산출 보존:** /workspace/phase22_distill_out/ (reports 129 + accepted 109) — Network Volume, 재증류 없이 재조립 가능.

## Self-Check: PASSED

- FOUND: backend/training/distill/full_batch.py
- FOUND: backend/training/distill/gemini_teacher.py
- FOUND: backend/training/datagen/build_jsonl.py
- FOUND: commits 9d5e3ff / 955eeb3 / d1028f1 / 5f2164c / 34ec9b2 / 59ac1a1 / c5b14ef / eb69692 / ce992e0 / f66f25f / a9b36cd / 25e6752 / 1930099

---
*Phase: 22-custom-vlm-finetune*
*Completed: 2026-07-11*
