---
phase: 15-mode-1-mode-3-testflight
plan: 01
subsystem: testing
tags: [sweep, s3, firestore, fixtures, falsepositive-gate, mode1, mode3, phase15]

# Dependency graph
requires:
  - phase: 08.1-axis-metric-redesign
    provides: tilt_thresholds.yaml frozen baseline (sha256 c94bb8…e87c) + 25/25 'low' invariant
  - phase: 14-reference-backfill
    provides: 11 reference 모션 phase4_v1 RTMW (Mode 1 referenceMotionId lockstep)
provides:
  - "sweep_phase15.py — 비-reference SOURCE fixture 키용 sweep 변종 (per-run/per-mode 영숫자 identity, --trigger mutually-exclusive, createdAt/updatedAt, --pair-sequential)"
  - "assert_falsepositive_gate.py — FROZEN 08.1 baseline 대조 위양성 assert (checksum hard gate, fallback==0, 재calibrate 0)"
  - "upload_phase15_dataset.py — 13 정은지 영상 → 비-notified fixtures/ SOURCE 키 정규화 업로드"
  - "phase15_keys.json — sweep_phase15.py --keys-file 입력 매핑 (19 sweep 항목)"
affects: [15-02, 15-03, phase-18-fault-eval-set]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SOURCE fixture(immutable, 비-notified) vs analysis identity(per-run/per-mode 생성) 분리"
    - "--trigger mutually-exclusive 단일 경로 + 모드별 invariant 카운터 자체 검증"
    - "frozen checksum hard gate (재calibrate 차단) — calibration-source-hard-gate 정합"

key-files:
  created:
    - backend/scripts/sweep_phase15.py
    - backend/scripts/assert_falsepositive_gate.py
    - backend/scripts/upload_phase15_dataset.py
    - backend/scripts/phase15_keys.json
  modified: []

key-decisions:
  - "13 dataset 영상 → fixtures/phase15/{motion}/correct|fault.mp4 (combo=correct, Mode-1-only); fixtures/ 프리픽스라 uploads/ notification 비발화 (HIGH 1)"
  - "analysisId 는 영숫자만 — motion 슬러그 하이픈 제거 후 role+runId (예: elbowtwistsisterFault<runId>); uid 는 [^/]+ 라 하이픈/언더스코어 허용 (HIGH 2)"
  - "direct-process(default) 는 fixtures/ SOURCE 키를 _process 에 그대로 넘겨 uploads/ COPY 0 → double-analysis race 원천 차단"
  - "한글 fail 파일명은 macOS NFD 저장이라 NFC normalize 후 substring 매핑 (Rule 1 fix)"
  - "위양성 gate 는 08.1 frozen baseline 대조만 — 재calibrate import 0, fail per-fault 객관 기준 미확정 시 manual review 다운그레이드 (Phase 18 defer)"

patterns-established:
  - "Pattern 1: SOURCE/identity 분리 — sourceS3Key(fixtures/) 와 uploads/{uid}/{analysisId} 가 서로 다른 변수, direct-process 는 sourceS3Key 만 사용"
  - "Pattern 2: dry-run identity self-check — analysisId 영숫자(전 모드) + every-uploads-key parse_upload_key(notification/analyze)"
  - "Pattern 3: checksum hard gate first — assert 진입 즉시 frozen baseline drift 차단, dry-run 에서도 항상 실행"

requirements-completed: [MODE-01, SCORE-04]

# Metrics
duration: 35min
completed: 2026-06-17
---

# Phase 15 Plan 01: Wave 0 도구 + 데이터셋 업로드 Summary

**Pod-독립 sweep/assert/upload 3 스크립트 — SOURCE fixture(비-notified)와 per-run/per-mode 영숫자 analysis identity 를 분리하고, FROZEN 08.1 baseline 을 checksum hard-gate 로 대조하며, 13 정은지 영상을 fixtures/ SOURCE 키로 정규화 업로드한다.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-06-17 (Phase 15 execution)
- **Completed:** 2026-06-17
- **Tasks:** 3
- **Files modified:** 4 created (3 scripts + 1 keys JSON)

## Accomplishments
- `sweep_phase15.py` — 비-reference SOURCE fixture 키 목록을 받아 per-run/per-mode 영숫자 analysis identity 를 생성하고, `--trigger` direct-process(default, uploads/ COPY 0)/notification/analyze 중 mutually-exclusive 단일 경로로 `pipeline._process` 를 구동. 모든 doc 에 `createdAt/updatedAt` 박제(get_previous_analysis DESC 누락 차단), `--pair-sequential` Mode 3 fault→success 순차 제출, dry-run analysisId 영숫자 self-check + (notification/analyze) every-key parse 검증.
- `assert_falsepositive_gate.py` — `backend/judging_data/tilt_thresholds.yaml` sha256 을 08.1 frozen `c94bb8…e87c` 와 hard-gate 대조(불일치 시 non-zero), `tilt_thresholds_fallback==0` fail-open 탐지, success=low-severity / fail=객관 machine 기준(또는 manual Phase 18 defer) assert. 재calibrate import 0.
- `upload_phase15_dataset.py` — 13 정은지 영상(7 success + 6 fail)을 비-notified `fixtures/phase15/{motion}/correct|fault.mp4` SOURCE 키로 정규화 업로드(Content-Type video/mp4 강제), `phase15_keys.json` 산출.
- `phase15_keys.json` — 19 sweep 항목(combo=Mode-1-only + 6 motion × mode1 success/mode3 fault·success).

## Task Commits

각 태스크 atomic commit:

1. **Task 1: sweep_phase15.py** - `be590c4` (feat)
2. **Task 2: assert_falsepositive_gate.py** - `a3ba31d` (feat)
3. **Task 3: upload_phase15_dataset.py + phase15_keys.json** - `d9d4c72` (feat)

## Files Created/Modified
- `backend/scripts/sweep_phase15.py` - 비-reference SOURCE fixture 키용 sweep 변종 (sweep_phase8_1 패턴 재사용 + SOURCE/identity 분리 + --trigger + --pair-sequential + createdAt)
- `backend/scripts/assert_falsepositive_gate.py` - FROZEN 08.1 baseline 대조 위양성 evidence-assert
- `backend/scripts/upload_phase15_dataset.py` - 13 영상 비-notified fixtures/ SOURCE 정규화 업로드
- `backend/scripts/phase15_keys.json` - sweep --keys-file 입력 매핑 (19 항목)

## Decisions Made
- **SOURCE/identity 분리:** `sourceS3Key`(fixtures/) 는 절대 analysis doc identity 로 쓰지 않음. direct-process 는 `_process(bucket, sourceS3Key, uid, analysisId)` 로 fixtures/ 키를 직접 넘김 — `_process`(app.py:1633)는 key 를 parse_upload_key 로 재파싱하지 않고 bucket/key 를 직접 download 하므로 fixtures/ 키로 직접 분석 가능.
- **영숫자 analysisId:** s3keys.py:18 `analysis_id=[A-Za-z0-9]+` 통과를 위해 motion 슬러그 하이픈 제거(`_sanitize_slug`). uid 는 `[^/]+` 라 `phase15_mode3_power-spin_<runId>` 같은 하이픈 허용.
- **위양성 gate = 대조만:** D-02 calibration-source-hard-gate 정합 — checksum 불일치 시 즉시 non-zero, 신규 fit 금지.
- **fail per-fault 기준:** 객관 per-fault gating 은 `--fail-mode manual` 로 다운그레이드 가능(Phase 18 defer); `auto` 는 non-low severity 또는 finding 노출을 객관 신호로 인정.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 한글 fail 파일명 NFC normalize 매핑**
- **Found during:** Task 3 (upload_phase15_dataset.py dry-run)
- **Issue:** macOS 는 파일명을 NFD(자모 분리)로 저장하지만 매핑 dict 키(한글)는 NFC 라 raw substring 매칭이 실패 → 6 fail 영상 중 1개(pdshape, latin)만 매칭, 5 한글명(엘보트위스트시스터/클라임/킵업/파워스핀/피터팬) 누락.
- **Fix:** `_match_motion` 에서 파일명과 needle 양쪽을 `unicodedata.normalize("NFC", ...)` 후 비교.
- **Files modified:** backend/scripts/upload_phase15_dataset.py
- **Verification:** dry-run 재실행 → `unique videos=13 (mode1 success=7 + fault=6)` 전부 매핑, exit 0.
- **Committed in:** d9d4c72 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** NFC fix 는 13 영상 전체 매핑의 필수 조건 — 없으면 fail 영상 5개가 누락되어 dataset 불완전. No scope creep.

## Issues Encountered
- **Pre-existing backend pytest 실패 (out-of-scope):** `backend/tests/test_pole_detector.py` 수집 ImportError(`No module named 'fixtures'`) + `test_pipeline_geminid_wiring.py`/`test_spike_gemini_moment_smoke.py` 37 failures. 모두 Plan 15-01 신규 스크립트와 무관(grep 확인: 어떤 테스트도 phase15 스크립트 import 안 함). 스코프 경계 규칙에 따라 `deferred-items.md` 에 로깅, 미수정. Phase 15 는 import-only 스크립트만 추가 — `1858 passed`.

## User Setup Required
None - no external service configuration required. 실 S3 업로드(`upload_phase15_dataset.py` non-dry-run)는 sunity-motion AWS 자격증명 필요(이미 Pod ops 박제), Wave 2 진입 시 실행.

## Next Phase Readiness
- Plan 15-02/03 (실 E2E sweep + reference --verify)가 타는 Pod-독립 도구 3개 준비 완료.
- `phase15_keys.json` 은 dry-run 매핑으로 산출됨 — 실 업로드(`upload_phase15_dataset.py` non-dry-run) 후 동일 schema 로 재산출되며 sweep_phase15.py 가 그대로 소비.
- Blocker 없음. 실 sweep/assert 는 Pod 기동 + RUNPOD_ANALYZE_URL Lambda env 동기화 후 Wave 2~3 에서 실행.

## Self-Check: PASSED

- All 4 created files present (3 scripts + phase15_keys.json) + SUMMARY.md.
- All 3 task commits present in git log (be590c4 / a3ba31d / d9d4c72).

---
*Phase: 15-mode-1-mode-3-testflight*
*Completed: 2026-06-17*
