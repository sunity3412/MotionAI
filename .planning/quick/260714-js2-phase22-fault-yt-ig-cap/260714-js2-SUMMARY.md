---
phase: quick-260714-js2
plan: 01
subsystem: ml-training-data
tags: [phase22, fault-recollection, curation-profile, vision-gate, license-audit]
requires: [22-02 수집 인프라, curate_vision VisionGate, phase22_sources.yaml]
provides:
  - fault_demo 큐레이션 프로필 (편집/자막 수용, 점수 금지 불변)
  - 프로필 스코프 verdict 캐시 키 (cache_key 헬퍼)
  - fault 검색쿼리 엔트리 5개 + eunji.poledancer cap 60
  - LICENSE-AUDIT §7-2 + manifest _meta.recollection_rounds
  - RUN-SHEET.md (오케스트레이터 실행 시퀀스)
affects: [22-07 v5 재학습 데이터 확충 라운드]
tech-stack:
  added: []
  patterns: [프로필 분기(default 경로 무변경), 순수 헬퍼 단일 소유(cache_key/build_enumeration_url/account_cap)]
key-files:
  created:
    - .planning/quick/260714-js2-phase22-fault-yt-ig-cap/RUN-SHEET.md
  modified:
    - backend/training/datagen/curate_vision.py
    - backend/scripts/phase22_sources.yaml
    - backend/scripts/collect_phase22_youtube.py
    - backend/scripts/collect_phase22_instagram.py
    - backend/tests/phase22/test_curate_vision.py
    - backend/tests/phase22/test_harvest_filter.py
    - backend/training/LICENSE-AUDIT.md
    - backend/training/data/manifest.json
decisions:
  - "fault_demo 프로필 keep 조건 = keep && single_person_pole && bucket==fault && fault_demo (일반 튜토리얼 유입 차단)"
  - "캐시 키: default=video_id 그대로(기존 캐시 히트 유지), 프로필={vid}::{profile} suffix"
  - "manifest collection_complete=true 유지 + recollection_rounds 리스트 등재 (계약 비파괴)"
  - "eunji.poledancer 는 curation_profile 미부여 = default 유지 (cap 상향만)"
metrics:
  duration: ~13분
  completed: 2026-07-14
---

# Quick Task 260714-js2: Phase 22 fault 타겟 재수집 라운드 준비 Summary

fault_demo 큐레이션 프로필(편집/자막 수용 + 프로필 스코프 캐시 키)로 22-02 에서 튜토리얼이 통째로 reject 되던 근본원인을 해소하고, 소스 레지스트리 확장(검색쿼리 5개 + eunji cap 60)과 승인 문서(§7-2/recollection_rounds/RUN-SHEET)를 박제 — 실 수집 0건 실행.

## Tasks

| Task | Name | Commits | 결과 |
|------|------|---------|------|
| 1 | curate_vision fault_demo 프로필 (TDD) | 4b34a11 (test) / e0ba31b (feat) | verdict 스키마 fault_demo/fault_desc 편입, decide(profile) 분기, cache_key 헬퍼, _GATE_PROMPT_FAULT_DEMO. default 경로 문자 그대로 무변경 |
| 2 | 레지스트리 확장 + 수집기 배선 (TDD) | 2036a69 (test) / 856ebf0 (feat) | Tier-2 fault 채널 5개 프로필 부여 + 검색쿼리 5개(ytsearch 스킴) + eunji cap 60. YT/IG 수집기 profile/cap pass-through, 캐시 직조회 cache_key 경유 |
| 3 | 재수집 라운드 문서화 | 21fa47c | LICENSE-AUDIT §7-2 + §8 이력 행, manifest _meta.recollection_rounds(status=open, rows 154 불변), RUN-SHEET.md |

## Verification

- phase22 전체 스위트: **258 passed / 1 skipped** (기존 248 기준 무회귀, 신규 +10)
- `collect_phase22_youtube.py --dry-run` exit 0 / `collect_phase22_instagram.py --dry-run` exit 0 (네트워크·과금 0)
- sources.yaml defaults·Tier-1 정타 블록 diff 0 (삭제 라인 = eunji notes 1줄 갱신뿐)
- manifest: collection_complete=true 불변 + rows 154 불변 + recollection_rounds[0].round == "fault-yt-ig-260714"

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 기존 VERDICT_KEYS 정확 튜플 assert 갱신**
- **Found during:** Task 1 (RED)
- **Issue:** `test_verdict_schema_has_no_score_or_severity` 가 VERDICT_KEYS 를 5-키 튜플로 정확 비교 — 플랜이 지시한 fault_demo/fault_desc 편입과 양립 불가 ("기존 6개 테스트 무수정" fence 와 충돌)
- **Fix:** 해당 assert 만 신규 7-키 스키마로 갱신 (스키마 추적 스펙 assert 의 필연적 동반 수정). decide 판정 동작 테스트 5개는 무수정 GREEN
- **Files modified:** backend/tests/phase22/test_curate_vision.py
- **Commit:** 4b34a11

**2. [Rule 1 - Bug] dry-run 테스트 assertion 교정**
- **Found during:** Task 2 (GREEN)
- **Issue:** 신규 테스트의 `"uploads/" not in out` 이 dry-run 안내 문구("uploads/ 미사용")에 오탐
- **Fix:** sample_key= 라인 파싱으로 실제 키 스킴만 검증 (fixtures/phase22/ prefix 전건 + uploads/ 0건)
- **Files modified:** backend/tests/phase22/test_harvest_filter.py
- **Commit:** 856ebf0

## Known Stubs

없음 — 신규 검색쿼리 엔트리 5개는 실체 미검증 상태로 등재됐으나 이는 의도된 설계 (실체 검증 = RUN-SHEET 2단계, 실행 단계에서 dry 열거 → 제목 스팟체크 → belle 확인). LICENSE-AUDIT §7-2 (e) 실측 수치는 수집 실행 후 기입 예정으로 명시.

## Threat Flags

없음 — 플랜 threat_model 범위 내. T-js2-01(normalize 화이트리스트 불변)·T-js2-02(cache_key 단일 소유)·T-js2-03(manifest rows/flag 불변 assert) 전부 테스트/verify 로 mitigate 확인. 과금·다운로드 실행은 RUN-SHEET 경유 오케스트레이터로 transfer (T-js2-04).

## Next

- 오케스트레이터: RUN-SHEET.md 시퀀스 실행 (Gemini 크레딧 확인 → dry-run → 검색쿼리 실체 검증 → belle 확인 → --curate → --collect → 사후 §7-2 (e) 실측 기입 + recollection_rounds status 갱신)

## Self-Check: PASSED

- [x] backend/training/datagen/curate_vision.py — fault_demo 포함 확인
- [x] backend/scripts/phase22_sources.yaml — curation_profile 포함 확인
- [x] backend/training/LICENSE-AUDIT.md — §7-2 존재 확인
- [x] .planning/quick/260714-js2-phase22-fault-yt-ig-cap/RUN-SHEET.md 존재
- [x] 커밋 5개 존재: 4b34a11 / e0ba31b / 2036a69 / 856ebf0 / 21fa47c
