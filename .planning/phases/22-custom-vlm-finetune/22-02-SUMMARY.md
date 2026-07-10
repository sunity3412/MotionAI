---
phase: 22-custom-vlm-finetune
plan: 02
subsystem: infra
tags: [dataset, provenance, yt-dlp, gemini-vision, anonymization, yolo, manifest, training-data]

# Dependency graph
requires:
  - phase: 22-01
    provides: "datagen/schema.py (D-11 규격·FAULT_CATEGORIES 재사용), tests/phase22 conftest sys.path fixture"
provides:
  - "채널 harvester(collect_phase22_youtube.py) — 3모드(--dry-run 안전 / --curate·--collect belle 게이트), 종목·길이·시리즈 순수 필터, fixtures/phase22 비-notified 키 규율"
  - "phase22_sources.yaml — 티어별 채널/계정 레지스트리(정타 공식대회 + fault 스튜디오 + IG), enabled=false 미성년·ToS 격리"
  - "curate_vision.py — Gemini Vision 다운로드-전 선별 게이트, 순수 decide()/normalize + Gemini I/O 분리, verdict score/severity 부재 불변식, verdict 캐시"
  - "anonymize.py — 얼굴 검출+Gaussian blur 가명처리(D-12), 순수 blur + I/O 껍데기 분리, 상단 1/3 폴백"
  - "manifest.json — 학습셋 provenance 원장(시드 17 + hard-negative 2 격리 + 371 customer_track 구조 참조)"
  - "phase22 provenance/균등/필터/vision 테스트 4종"
affects: [22-03, 22-04, 22-05, license-audit, training-jsonl]

# Tech tracking
tech-stack:
  added: [PyYAML registry, "yt-dlp(lazy, Task 3)", "google-genai(lazy, Task 3)", "ultralytics face(lazy)"]
  patterns:
    - "3모드 harvester: --dry-run(네트워크 0, 순수 검증) vs --curate/--collect(belle greenlight 게이트, lazy-import)"
    - "다운로드-전 Vision 선별 게이트 = 순수 decide() + Gemini I/O 어댑터(lazy, graceful) 분리 (coach_writer 전례)"
    - "verdict/manifest 화이트리스트 정규화로 score/severity/uid 유입 차단(불변식 가드)"
    - "가명처리 = 순수 numpy separable-box blur + I/O 껍데기(ultralytics lazy), OpenCV 무의존"

key-files:
  created:
    - backend/scripts/phase22_sources.yaml
    - backend/scripts/collect_phase22_youtube.py
    - backend/training/datagen/curate_vision.py
    - backend/training/datagen/anonymize.py
    - backend/training/data/manifest.json
    - backend/tests/phase22/test_provenance.py
    - backend/tests/phase22/test_manifest_consistency.py
    - backend/tests/phase22/test_harvest_filter.py
    - backend/tests/phase22/test_curate_vision.py
  modified:
    - backend/tests/phase22/conftest.py

key-decisions:
  - "Task 3(Gemini 실선별 + 카피라이트 prod S3 적재)은 belle greenlight 전 미실행 — --curate/--collect 는 PHASE22_BELLE_GREENLIGHT=1 env 게이트로 툴 레벨 차단"
  - "yt-dlp/boto3/google-genai/ultralytics 는 belle-gated 실행 경로에서만 lazy-import — --dry-run 과 전 테스트는 외부 의존·네트워크 0이라 로컬에서 안전 실행"
  - "hard-negative(A2 피터팬·A3 power-spin)는 s3_key=null·collected=false 로 정직 등재(미디어 relocate=Task 3), holdout=hard_negative_eval 로 학습 카운트 제외"
  - "371 고객 영상은 개별 행 미등재 — _meta.customer_track 구조 참조만(uid 미기재, anonymized=false 로는 22-04 build_jsonl 제외)"

patterns-established:
  - "belle 게이트 툴 인포스먼트: 과금·비가역 모드는 env greenlight 없으면 SystemExit(2)"
  - "필터 self-check: dry-run 이 합성 제목/길이로 후프배제·타이틀카드배제·폴통과를 검증(silent-통과 금지, phase18 전례)"

requirements-completed: [FT-02, FT-06]

# Metrics
duration: 38min
completed: 2026-07-09
---

# Phase 22 Plan 02: 학습셋 수집 엔진 (harvester + Vision 선별 게이트 + 가명처리 + provenance 원장) Summary

**티어별 채널 harvester + Gemini Vision 다운로드-전 선별 게이트(score-free) + 얼굴 가명처리 모듈 + 시드/hard-negative provenance 원장을 데이터가 쌓이기 전 게이트로 세웠다 — 실 다운로드·과금은 belle greenlight(Task 3)까지 0.**

## Performance

- **Duration:** ~38 min
- **Started:** 2026-07-09
- **Completed:** 2026-07-09
- **Tasks:** 2 of 3 (Task 3 belle-gated, 의도적 deferred)
- **Files modified:** 10 (9 created, 1 modified)

## Accomplishments
- **채널 harvester(collect_phase22_youtube.py)** — 3모드. `--dry-run` 은 레지스트리 로드 + 순수 필터 self-check + fixtures/phase22 키 스킴 검증만(네트워크·yt-dlp·boto3·Gemini 0, exit 0). `--curate`/`--collect` 는 과금·비가역이라 `PHASE22_BELLE_GREENLIGHT=1` 없으면 SystemExit(2).
- **phase22_sources.yaml** — 22-DATA-SOURCES.md 반영 티어별 레지스트리. Tier-1 정타(KPSA/KPSF/IPSF/PSO 등 공식대회) + Tier-2 fault(BerryTV 폴인폴 시리즈·스튜디오 강사) + IG. 미성년(@polesportkids)·IG ToS 계정은 `enabled=false` 격리.
- **curate_vision.py** — Gemini Vision 다운로드-전 선별 게이트. 순수 `decide()`/`normalize_verdict()` 와 Gemini I/O 어댑터(`VisionGate.gate`, lazy-import, 키 미설정 graceful) 분리. verdict schema = {bucket, keep, move_guess, reason, single_person_pole} — **score/severity 필드 영구 부재**(모델은 점수를 내지 않는다). verdict 캐시로 재호출 0(과금 방어).
- **anonymize.py** — 얼굴 검출(ultralytics 재사용, lazy) + numpy separable-box Gaussian 근사 blur(OpenCV 무의존) 가명처리(D-12). 순수 `blur_bbox_regions`/`top_third_fallback_bbox` 와 I/O 껍데기 분리. 검출 실패 시 상단 1/3 보수 폴백.
- **manifest.json** — provenance 원장. 시드 17행(정은지 reference 11 정타 + 일부러실수 6 fault) + hard-negative 2행(A2 피터팬·A3 power-spin, holdout 격리) + 371 customer_track 구조 참조.
- **테스트 4종** — provenance(필수필드·버킷 enum·uid 금지·금지모델 fence) / manifest_consistency(s3_key 중복·균등 gated·hard-negative 제외) / harvest_filter(후프배제·타이틀카드·시리즈) / curate_vision(score-free·enum·decide 순수성·graceful).

## Task Commits

1. **Task 1: 채널 harvester + Vision 선별 게이트 + provenance/균등/필터 테스트** — `988993e` (feat)
2. **Task 2: 시드 자산 등재 + 가명처리 모듈 + hard-negative 격리 (D-08, D-12)** — `cda85b1` (feat)

**Task 3: belle 게이트 (Vision 실선별 → 수집 실행 + LICENSE-AUDIT.md)** — **미실행(deferred)**. Gemini 실선별 API 과금 + 카피라이트 영상 prod S3 적재(비가역)라 belle greenlight 필요. `collect_phase22_instagram.py` 와 `LICENSE-AUDIT.md` 는 Task 3 산출물이라 아직 생성 안 함.

## Files Created/Modified
- `backend/scripts/phase22_sources.yaml` - 티어별 채널/계정 레지스트리(필터·버킷·caveat)
- `backend/scripts/collect_phase22_youtube.py` - 3모드 harvester, 순수 필터, 비-notified 키 규율
- `backend/training/datagen/curate_vision.py` - Gemini Vision 선별 게이트(순수 판정 + I/O 어댑터)
- `backend/training/datagen/anonymize.py` - 얼굴 가명처리(순수 blur + I/O 껍데기, D-12)
- `backend/training/data/manifest.json` - 학습셋 provenance 원장(시드 + hard-negative + customer_track)
- `backend/tests/phase22/test_provenance.py` - provenance·버킷·uid·모델 fence
- `backend/tests/phase22/test_manifest_consistency.py` - 중복·균등 gated·hard-negative 제외
- `backend/tests/phase22/test_harvest_filter.py` - 종목/길이/시리즈 순수 필터
- `backend/tests/phase22/test_curate_vision.py` - verdict score-free·enum·순수성·graceful
- `backend/tests/phase22/conftest.py` - sys.path 에 backend/scripts 추가(harvester import)

## Verification

- `python3 backend/scripts/collect_phase22_youtube.py --dry-run` → **exit 0**. stdout 키 스킴 전부 `fixtures/phase22/` 등장, `uploads/` 미등장. 다운로드·Gemini 호출 0. 활성 채널 12/15(enabled=false 3 격리).
- `python3 -m pytest backend/tests/phase22 -x -q` → **36 passed, 2 skipped**(균등 게이트 collection_complete=false gated skip + --check-s3 네트워크 skip).
- curate_vision `VERDICT_KEYS` = ('bucket','keep','move_guess','reason','single_person_pole') — score/severity grep 0.
- manifest: rows 19, hard_negative 2(≥2 ✓), seed 17(≥12 ✓). `grep -c "D-12" anonymize.py` = 5(≥1 ✓). uid 필드 0.

## Decisions Made
- **Task 3 툴-레벨 게이트:** `--curate`/`--collect` 는 belle greenlight(`PHASE22_BELLE_GREENLIGHT=1`) 없으면 즉시 차단. 스크립트 자체가 과금·비가역 실행을 막는다.
- **외부 의존 lazy-import:** yt-dlp/boto3/google-genai/ultralytics 는 belle-gated 경로에서만 import. Task 1·2 산출물과 전 테스트는 순수 로컬(네트워크 0)이라 yt-dlp 미설치 상태로도 완전 검증됨.
- **hard-negative 정직 등재:** A2/A3 실 미디어(Firestore 파일럿 업로드)는 아직 fixtures/phase22 로 relocate 안 됨 → `s3_key=null, collected=false` + note. 조작된 키 대신 미수집 상태를 정직하게 표기.

## Deviations from Plan

### Auto-fixed / Guardrail-driven

**1. [Rule 3 - Blocking / Guardrail] yt-dlp pip install 보류 + --dry-run 을 무-네트워크 순수 검증으로 설계**
- **Found during:** Task 1
- **Issue:** 플랜 action(1)은 `pip install yt-dlp` 후 `--dry-run` 이 채널을 열거(yt-dlp --flat-playlist = YouTube 네트워크 호출)하도록 기술. 그러나 (a) 실행 가드레일이 "다운로드/과금 0, --dry-run ONLY, LOCAL-ONLY" 이고 (b) yt-dlp 는 belle-gated Task 3 에서만 실제 필요하다.
- **Fix:** `--dry-run` 을 yt-dlp/네트워크 없이 레지스트리+순수 필터 self-check+키 스킴 검증만 수행하도록 설계. yt-dlp 는 `--curate`/`--collect`(Task 3) 경로에서만 lazy-import. yt-dlp 설치는 Task 3 belle greenlight 로 이월.
- **Files modified:** backend/scripts/collect_phase22_youtube.py
- **Verification:** `--dry-run` exit 0(네트워크 0), pytest 36 passed. yt-dlp 미설치 상태에서 전 산출물 검증 완료.
- **Committed in:** 988993e

**2. [Rule 2 - Missing Critical] 371 고객 트랙을 개별 행이 아닌 _meta.customer_track 구조 참조로 등재**
- **Found during:** Task 2
- **Issue:** 플랜은 "실사용 371건 video_hash + Firestore 경로 참조"를 요구하나, 실행 가드레일이 "uid/가짜 행 조작 금지, 문서 없으면 구조만 등재+SUMMARY 명기"로 못박음. 실제 371 문서/키 열거는 Firestore 접근이 필요하고 본 세션 범위 밖.
- **Fix:** 371건을 개별 행으로 조작하지 않고 `_meta.customer_track`(count 371, uid 미기재, anonymized=false, 22-04 build_jsonl 소비 조건, 가명처리 pending)로 구조만 정직 등재.
- **Files modified:** backend/training/data/manifest.json
- **Verification:** test_provenance uid-금지 통과, 조작 행 0.
- **Committed in:** cda85b1

**3. [Guardrail] Task 3 전체(collect_phase22_instagram.py, LICENSE-AUDIT.md, --curate/--collect 실행)를 미실행**
- **Found during:** 계획대로 (Task 3 = checkpoint:belle-gate)
- **Issue:** Gemini 실선별 과금 + 카피라이트 prod S3 적재(비가역)는 belle 명시 승인 필요.
- **Fix:** Task 1·2 툴링만 구축. Task 3 산출물은 생성하지 않음(가드레일 준수).
- **Impact:** 22-02 는 in-progress 유지 — ROADMAP complete 미표기.

---

**Total deviations:** 3 (1 blocking/guardrail, 1 missing-critical/guardrail, 1 planned belle-gate)
**Impact on plan:** 전부 실행 가드레일(로컬-only, 다운로드·과금 0, 조작 금지) 준수를 위한 설계 조정. 스코프 축소 없음 — Task 1·2 acceptance criteria 전부 충족. Task 3 는 원래 belle 게이트라 미실행이 정상 흐름.

## Issues Encountered
- 초기 blur 순수함수 sanity 테스트에서 균일(uniform) bbox 영역을 사용해 "blur 무효과"로 오판 — 균일 영역은 blur 후에도 동일한 것이 정상. bbox 내부에 엣지가 있는 입력으로 재검증해 정상 동작 확인(테스트 결함, 코드 정상).

## User Setup Required
None — Task 1·2 는 외부 서비스 구성 불필요. Task 3(belle greenlight 후)에서 yt-dlp 설치 + Gemini 키(Parameter Store `GEMINI_KEY_PARAM` 또는 `GOOGLE_API_KEY`) + sunity-motion AWS 프로필 필요.

## Next Phase Readiness
- **Task 3 대기(belle greenlight):** belle 에게 규모(채널별 후보 수·예상 다운로드·예상 Vision 호출 수)를 제시 후 승인받아 `PHASE22_BELLE_GREENLIGHT=1 --curate` → `--collect` 순차 실행. Task 3 산출물 = collect_phase22_instagram.py + LICENSE-AUDIT.md + 수집분 manifest append + _meta.collection_complete=true(균등 게이트 활성).
- **22-04 build_jsonl 준비:** manifest 계약(anonymized/internal 소비 조건, hard_negative 격리, score/severity 부재)이 게이트로 고정됨. 371 고객 트랙은 anonymize.py 가명처리 적용 후 등재.
- **블로커 없음.** yt-dlp 설치는 Task 3 실행 직전에 수행(belle 승인 후).

---
*Phase: 22-custom-vlm-finetune*
*Completed: 2026-07-09 (Tasks 1-2; Task 3 belle-gated)*

## Self-Check: PASSED

- 10/10 created files present on disk.
- Both task commits (988993e, cda85b1) present in git history.
- `--dry-run` exit 0 (0 downloads, 0 Gemini); phase22 pytest 36 passed, 2 skipped.

> **잔여 해소 (2026-07-10):** Task 3 잔여였던 `backend/training/LICENSE-AUDIT.md` 는 수집 마감(`_meta.collection_complete=true`, 131행 = 시드 19 + YouTube 68 + IG 44) 후 manifest 실측 원장 기반으로 확정 작성 완료(소스별 원장·리스크 플래그·belle 결정 이력·A9 체크리스트). 미성년 행 실측 0. 22-02 잔여 산출물 없음(내부 371 fault track 은 balance_waiver 로 다음 라운드 이월).
