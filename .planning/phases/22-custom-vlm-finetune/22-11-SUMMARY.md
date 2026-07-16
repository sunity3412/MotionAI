---
phase: 22-custom-vlm-finetune
plan: 11
subsystem: infra
tags: [data-flywheel, collection, manifest-ledger, provenance, watch-runner]

# Dependency graph
requires:
  - phase: 22-02
    provides: collect_phase22_youtube.py / collect_phase22_instagram.py 수집기 + phase22_sources.yaml 레지스트리 + manifest 원장(D-09)
provides:
  - phase22_watch.py 쌓기 러너 (belle 1커맨드 --run / --dry-run watch 오케스트레이터)
  - _meta.collection_batches[] 배치 증분 등재 규약 (마감 무결성 정합, append-only)
  - watch:false 옵트아웃 규약 + 신규 채널 등재 형식 (phase22_sources.yaml)
  - FLYWHEEL-RUNBOOK.md §1(쌓기) 운영 절차서
  - watch_reports/{batch_id}.json 리포트 규약 (은폐 금지 이중 기록)
affects: [22-12 공부 배치 루프(collection_batch 필드로 신규분 소비), 데이터 플라이휠 지속 운영]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "배치 원장 규약: collection_complete(마감 소유=build_jsonl)와 collection_batches(증분)를 분리해 마감 무결성과 append-only 증분을 공존"
    - "순수 헬퍼 + I/O 껍데기 분리: 원장/리포트 로직은 네트워크 0 으로 테스트, boto3/yt-dlp 는 하위 수집기 lazy-import 재사용"
    - "belle 과금 게이트 재사용(PHASE22_BELLE_GREENLIGHT): --run 진입 SystemExit(2), 스케줄에서도 유지"

key-files:
  created:
    - backend/scripts/phase22_watch.py
    - backend/tests/phase22/test_watch_collect.py
    - backend/training/FLYWHEEL-RUNBOOK.md
  modified:
    - backend/training/data/manifest.json
    - backend/scripts/phase22_sources.yaml

key-decisions:
  - "collection_complete 플래그 소유자는 build_jsonl(DR-06) — watch 규약이 게이트에 맞추고 역은 금지(build_jsonl 무접촉)"
  - "증분은 collection_batches[] 배치 단위로만 등재, recollection_rounds[]는 이력 동결"
  - "watch:false 부재 = watch 대상(기본 opt-in) — YT는 enabled만, IG는 트랙 전체"
  - "기존 sources.yaml entry 값 무변형(주석·watch 규약 헤더만 추가)"

patterns-established:
  - "assert_ledger_invariants: 실행마다 collection_complete=True + closed/waiver 무변형 + rows append-only(prefix) 강제, 위반 시 저장 중단"
  - "summarize_run/_parse_collect_counts 순수 리포트 조립 — 신규/reject/skip/누적 4필드 방출(은폐 금지)"

requirements-completed: [FT-02]

# Metrics
duration: 22min
completed: 2026-07-16
---

# Phase 22 Plan 11: 데이터 플라이휠 쌓기 상설화 Summary

**belle 1커맨드(PHASE22_BELLE_GREENLIGHT=1 --run)로 watchlist 주기 수집을 실행하는 watch 러너를 22-02 수집기 재사용으로 구축하고, 마감된 manifest(collection_complete=true)를 깨지 않는 collection_batches[] 배치 증분 등재 규약을 순수 헬퍼+불변식 테스트로 박제.**

## Performance

- **Duration:** ~22 min
- **Completed:** 2026-07-16
- **Tasks:** 3/3
- **Files created:** 3 / modified: 2

## Accomplishments

- **Task 1 (TDD):** 배치 원장 규약 + 순수 헬퍼 — `make_batch_entry`(여분 키 0) / `register_batch`(append-only, 중복 ValueError) / `update_batch_entry` / `compute_batch_id`(watch-YYMMDD, 같은 날 -2 접미) / `make_watch_row`(collection_batch 주입) / `assert_ledger_invariants`(마감 무결성 강제). manifest `_meta.collection_batches=[]` 초기화(스크립트, rows/기타 _meta 무접촉). RED→GREEN 2커밋.
- **Task 2:** watch 오케스트레이션 `main(argv)` — `--dry-run`(watch 대상 + 원장 self-check + 하위 수집기 dry-run 위임, network 0) / `--run`(belle greenlight 게이트 → YT curate+collect / IG collect → 신규 행 배치 태깅 → 불변식 통과 후 저장 → 게이트 pytest 자동 재검증). `watch_targets`(watch:false 옵트아웃) / `summarize_run` / `_parse_collect_counts` 순수. phase22_sources.yaml watch 규약 헤더 주석(기존 entry 무변형, 12 insertions/0 deletions).
- **Task 3:** FLYWHEEL-RUNBOOK.md §1(쌓기) — belle 1커맨드 절차 + 사전조건 체크리스트 + 멱등/스코프/주기(주1회)/스케줄 옵션(무인 과금 금지 게이트 유지) + 리포트 읽는 법 + 동의·라이선스 경계(D-12 3겹, IG 공개릴스만·쿠키 금지, 내부트랙 스코프 밖) + 배치 원장 규약 요약. §2(22-12) 헤더 예약.

## Verification

- `python3 -m pytest backend/tests/phase22 -q` → **293 passed, 1 skipped** (기존 스위트 무회귀 + 신규 test_watch_collect 20).
- `python3 backend/scripts/phase22_watch.py --dry-run` → exit 0, network·과금 0.
- `PHASE22_BELLE_GREENLIGHT= python3 backend/scripts/phase22_watch.py --run` → exit 2 (과금 게이트 차단).
- `git diff --quiet build_jsonl.py schema.py assert_gates.py` → exit 0 (프로덕션 무접촉 최종 확인).
- build_jsonl.assert_collection_complete(manifest, False) → OK (collection_batches 추가 무영향).
- manifest: collection_complete=true 보존 + collection_batches=[] 초기화 + 기존 239행 무변형.
- phase22_watch.py boto3/yt_dlp 최상위 import 0.

## Deviations from Plan

None - 플랜 3개 태스크를 작성된 대로 실행. Rules 1-4 발동 없음. 실 수집(과금 경로)은 플랜 스코프대로 실행하지 않음(운영은 런북 절차).

## Known Stubs

- FLYWHEEL-RUNBOOK.md §2(공부 배치 루프)는 의도적 헤더 예약 — 22-12가 소유(플랜 명시). 목표(쌓기 상설화)를 막지 않음.
- watch_reports/ 디렉토리는 --run 실행 시에만 생성(런타임 산출) — 현재 미생성이 정상.

## Threat Surface Notes

플랜 threat_model(T-22-11-01~SC) 범위 내 — 신규 보안 표면 없음. 기존 3중 필터+curate_vision 게이트 재사용(우회 경로 신설 0), assert_ledger_invariants가 원장 훼손 차단, PHASE22_BELLE_GREENLIGHT가 무인 과금 차단, 리포트 JSON에 자격·uid 필드 없음, 신규 pip 설치 0.

## Self-Check: PASSED

- FOUND: backend/scripts/phase22_watch.py
- FOUND: backend/tests/phase22/test_watch_collect.py
- FOUND: backend/training/FLYWHEEL-RUNBOOK.md
- FOUND: commits bb80d51 / 4c622c7 / acf5919 / 31bbbd3
