---
phase: quick-260824-q6p
plan: 01
subsystem: backend+app
tags: [playback-url, fault-zoom, presigned-ttl, s3keys, react-native]

requires:
  - phase: quick-260704-fz4
    provides: 2단 tier(confirmed/advisory) + zoom_adv_ S3 키 분리 — canonical 재구성의 tier 축
  - phase: "33-12"
    provides: criterion-keyed 카드 (S3 key_base = criterion or joint) — canonical 재구성의 key_base 축
  - phase: quick-260808-jix
    provides: asset 'renderedCompare' 재서명 선례 (H-02 done+exact 이중 가드) — 4번째 asset 종류의 규율 원형
provides:
  - POST /playback-url asset 'faultZoom' 배치 재서명 (done 게이트 + canonical exact 비교, 가드 위반 동일 404)
  - s3keys.build_fault_zoom_key 단일 출처 (pipeline 저장측 인라인 f-string 제거 — drift 0) + parse_result_key_from_presigned_url 소급 파서
  - 신규 doc faultZoomComparisons[].imageKey 방출 (이후 재발급은 URL 파싱 없이 key exact 비교)
  - 앱 useFreshFaultZoomUrls 훅 + DeductionDetailSheet fresh 맵 배선 (fail-closed — 실패 시 현행 회색 폴백)
affects: [result-screen, deduction-sheet, playback-url-lambda, pipeline-lambda, sam-deploy, ota-publish]

tech-stack:
  added: []
  patterns:
    - "asset 재서명 확장 4번째 종류 — H-02(URL 비저장·열람 시점 재서명)·H-05(클라이언트 key 미전송)·M2-01(canonical exact 비교) 선례 복제"
    - "소급 = 서버측 URL 파싱 (파서는 후보 추출 전용 — 서명 게이트는 canonical exact 비교가 전담, 백필 0)"
    - "훅 순수 함수 분리 + './api' 지연 동적 import — node --test 가 firebase 초기화 체인 없이 순수 함수 로드"

key-files:
  created:
    - backend/tests/test_playback_url_fault_zoom.py
    - app/src/lib/faultZoomUrls.ts
    - app/src/lib/__tests__/faultZoomUrls.test.ts
  modified:
    - backend/shared/python/sunity_shared/s3keys.py
    - backend/shared/python/sunity_shared/models.py
    - backend/functions/pipeline/app.py
    - backend/functions/playback-url/app.py
    - docs/contract.md
    - app/src/types/analysis.ts
    - app/src/lib/api.ts
    - app/src/app/analysis/result.tsx
    - app/src/components/DeductionDetailSheet.tsx

decisions:
  - "재발급 구조 = 기존 POST /playback-url asset 확장 (배경 제안의 신규 HTTP API POST /media-urls 불요 — 선례 3건과 동일 패턴)"
  - "소급은 서버가 저장 imageUrl 을 파싱 — 클라이언트 key 전송 0 (H-05 유지), doc 백필 0"
  - "앱 join 키 = zoomCardKey(tier×(criterion|joint)) — 서버 canonical 유일성 축과 동형, S3 key 문자열 재구성 없음"
  - "훅 실패 = 맵 비움 유지 (fail-closed) — 백엔드 배포 전 앱이 먼저 나가도 400 → 현행 회색 폴백, 순서 독립"

metrics:
  duration: ~35min
  completed: 2026-08-24
---

# Quick Task 260824-q6p: 확대비교 presigned 만료 수리 (asset 'faultZoom' 재발급) Summary

**One-liner:** faultZoomComparisons[].imageUrl 7일 presigned 만료로 비교 패널이 전부 회색이 되던 결함을, POST /playback-url asset 'faultZoom' 배치 재서명(서버 canonical exact 비교 + 소급 URL 파싱) + 앱 열람 시점 재발급 훅(fail-closed 폴백)으로 수리 — 기존 doc 백필 0, 클라이언트 key 전송 0.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | 백엔드 — key 단일 출처 + asset 'faultZoom' 재서명 + imageKey 방출 (계약 3중 동시) | 4246f07 | s3keys.py, models.py, pipeline/app.py, playback-url/app.py, test_playback_url_fault_zoom.py, contract.md, analysis.ts |
| 2 | 앱 — fetchFaultZoomUrls + 재발급 훅 + 시트 배선 (fail-closed) | 1bd2622 | api.ts, faultZoomUrls.ts, faultZoomUrls.test.ts, result.tsx, DeductionDetailSheet.tsx |
| 3 | 전량 게이트 (검증 전용 — 변경 0) | — | — |

## What Was Built

### 백엔드 (Task 1)

- **`s3keys.build_fault_zoom_key(uid, analysis_id, tier, key_base)`** — 단일 출처. tier `'advisory'` → `zoom_adv_`, 그 외(confirmed/None/legacy) → `zoom_`. 기존 pipeline 인라인 규칙과 byte-동일 (테스트 (h) 직접 검증). `zoom_adv_` 리터럴이 s3keys 밖 코드에 0 (grep 게이트, 주석 포함 0).
- **`s3keys.parse_result_key_from_presigned_url(url)`** — virtual-hosted/path-style 양쪽 파싱, 실패 = None. 파서 출력은 비신뢰 — canonical exact 비교가 서명 게이트 (T-q6p-03).
- **pipeline `_fault_zoom_upload_items`** — `key_prefix` 파라미터 삭제(tier 파생), 호출측 2곳(`_render_fault_zoom` 말미 루프 + `_run_gated_card_inherit`) 시그니처 갱신. item 에 `"imageKey": skey` 방출 (scalar str — flat 제약 통과, `update_analysis_fault_zoom` validator 무수정 실측 확인).
- **playback-url `_handle_fault_zoom`** — done 게이트 → item 순회: `imageKey`(비어있지 않은 str) 우선, 부재 시 imageUrl 파싱(소급) → canonical exact 일치분만 서명(1시간, image/png) → `{items: [{joint, playbackUrl, tier?, criterion?}], expiresInSec: 3600}`. 서명 0건 = 404. lambda_handler 분기는 renderedCompare 뒤·VISUAL_JOB_KINDS 검사 앞 — 기존 asset 종류 응답 바이트 불변.
- **계약 3면 동시** — contract.md `asset: 'faultZoom'` 절 + §11.10 imageKey / analysis.ts `FaultZoomComparison.imageKey?` (lockstep 주석) / 백엔드 방출·재서명부. userAnalyses.ts normalize 는 `...c` spread 라 통과 (수정 불요 — 실측 확인).

### 앱 (Task 2)

- **`api.fetchFaultZoomUrls`** — `{analysisId, asset: 'faultZoom'}` POST. items 비-배열 = malformed_response throw, 불량 item 은 조용히 filter (배치 부분 성공 보존).
- **`faultZoomUrls.ts`** — 순수 `zoomCardKey`(`adv:`/`conf:` + criterion||joint — 서버 canonical 유일성 축 동형) + `buildFreshZoomUrlMap` + `useFreshFaultZoomUrls` 훅 (6일 마진 자동 재발급 — freshMyUrl :973 선례 동일, `onZoomImageError` 나이 무관 재발급 ref single-flight, 실패 = `__DEV__` warn 만 + 맵 비움 유지). `'./api'` 는 지연 동적 import — node --test 가 firebase 초기화 체인 없이 순수 함수를 로드한다.
- **배선** — result.tsx 훅 호출(freshRefUrl 블록 인접) → DeductionDetailSheet props. `renderCrop` Image = `freshZoomUrls?.[zoomCardKey(zoom)] ?? zoom.imageUrl` + `onError`. imageUrl 렌더 지점 전수 grep = 1곳(:146) 확인. props 부재 = 종전 동작 (하위호환). `deductionSheet.ts:838` imageUrl 동일성 비교는 doc 저장값끼리 — 무접촉 (맵은 렌더 경계 전용, doc item 무변형).

## Verification (전량 게이트 — Task 3)

- **backend pytest 대상 모듈**: `test_playback_url_fault_zoom.py`(20) + `test_playback_url_reference.py`(11) + `test_fault_zoom_deferred.py` = **44 passed / 신규 실패 0**. `grep -rln "_fault_zoom_upload_items\|build_fault_zoom_key" backend/tests` = 신규 테스트뿐 (시그니처 변경 여파 전수 확인).
- **app**: `npm run typecheck` GREEN + `node --test src/lib/__tests__/*.test.ts *.test.mjs` = **207 pass / fail 0** (기준선 201 + 신규 6).
- prefix 리터럴 단일 출처: `zoom_adv_` s3keys 밖 0 (주석 포함 0).
- 신규 pytest 커버: done+exact 서명(a) / 소급 virtual-hosted·path-style 파싱(b,c) / stale key 부분 제외·전체 404(d) / status 게이트 + leak 0 동일 body(e) / cross-uid 차단 imageKey·imageUrl 양경로(f) / advisory prefix·criterion 우선·joint 폴백(g) / 순수 함수 직접(h) / asset 미지정 무회귀(i).

## Known Baseline Failures (신규 아님)

`test_fault_zoom_deferred.py` 2건 (`test_extract_calls_reuse_cached_user_frames_runpod_path` / `test_extract_calls_reextract_without_cache_lambda_path`) — dev 머신 `imageio_ffmpeg` 미설치로 `compare_render.py:37` import 실패. 실패 지점(`app.py:3245 → compare_render`)은 HEAD 와 동일한 무접촉 코드 (`git show HEAD` 대조 실측) — 본 작업과 무관한 환경 기준선.

## Deviations from Plan

**1. [Rule 1 - Bug] node 테스트 strict deepEqual 타입 좁힘으로 typecheck 실패**
- **Found during:** Task 2 verify (tsc)
- **Issue:** `assert.deepEqual`(strict) 이 assertion 함수라 `map` 이 기대 리터럴 타입으로 좁혀져 이후 string 인덱싱이 TS7053
- **Fix:** join 동형성 조회를 deepEqual 앞으로 재배치 (로직 동일)
- **Files modified:** app/src/lib/__tests__/faultZoomUrls.test.ts
- **Commit:** 1bd2622

그 외 플랜 그대로 실행.

## 배포 준비 (실행은 범위 밖 — belle/오케스트레이터 확인 후)

- **백엔드**: `cd backend && sam build --use-container && sam deploy` — Mac 네이티브 함정으로 `--use-container` 필수. 템플릿 변경 0 (함수 코드 + SharedLayer 만).
- **앱 OTA**: 발행은 belle 결정 대기 ([[verify-ui-on-simulator-before-ota]] — 시뮬 실증은 오케스트레이터 후속).
- **순서 독립**: 앱 먼저 나가도 미배포 Lambda 의 400 bad_request → 훅 catch → 저장 imageUrl 폴백 (현행 회색 그대로, 크래시 0). 백엔드 먼저 나가도 구 앱 무영향 (asset 미지정 경로 바이트 불변 — 테스트 (i)).
- **소급 실증 항목**: 배포 후 belle 의 7-30 분석(비교 패널 회색이던 doc)을 열어 확대 비교 이미지 표시 확인 — imageKey 없는 legacy doc 의 imageUrl 파싱 → canonical exact → 재서명 경로의 실물 검증.

## Known Stubs

없음 — 신규 표면 전부 배선 완료 (훅 → 시트 → 이미지 소스). 미배포 상태의 앱 동작은 스텁이 아니라 설계된 fail-closed 폴백.

## Threat Flags

없음 — 신규 표면은 plan `<threat_model>` 의 T-q6p-01~04·T-q6p-SC 범위 내 (신규 의존성 0, stdlib urllib.parse 만).

## Self-Check: PASSED

- [x] backend/tests/test_playback_url_fault_zoom.py 존재
- [x] app/src/lib/faultZoomUrls.ts 존재
- [x] app/src/lib/__tests__/faultZoomUrls.test.ts 존재
- [x] 커밋 4246f07 존재 (Task 1)
- [x] 커밋 1bd2622 존재 (Task 2)
- [x] 게이트 실측: pytest 44 pass 신규 실패 0 / typecheck GREEN / node --test 207 pass fail 0
