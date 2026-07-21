---
phase: 32-result-readability-3-omni
plan: 13
subsystem: backend-pipeline, ui, deploy
tags: [spot-check, d22, d23, gemini, post-stage, record-hiding, praise-crosscheck, pod-deploy, d23-sweep, ota, python, typescript]

# Dependency graph
requires:
  - phase: 32-09
    provides: "recordId 각인 + 3단 문구(statusLine/cueLine) + summaryPraise.headline 방출 — 스팟체크의 대조 대상·조인 키"
  - phase: 32-12
    provides: "runtime 1.1.0 OTA 경로 (native 빌드 1.1.0/29) — 앱 숨김 소비층 배포 경로"
  - phase: 32-16
    provides: "32-16 스윕 기준선 (runId 1784649897) + coach_audio 사후 스테이지 선례"
  - phase: 32-07
    provides: "summarySource.spotCheckPraiseMismatch 강등 입력 (selectPraise 폴백 체인 사전 배선)"
provides:
  - "spot_check.py 어댑터 — 분석당 1콜 스팟체크 (strict response_schema + temp 0 + 보수 후처리: 누락/환각/enum밖 = uncertain 표시)"
  - "pipeline spot_check 사후 스테이지 (firestore_complete·fault_zoom 이후 — 동기 경로 신규 외부 호출 0 소스 고정)"
  - "result.spotCheck 계약 3면 (§12.8 표시 정책 명문: 부재/pending/skipped/failed = fail-open 전 카드 표시)"
  - "앱 recordId 맵 기반 카드 표면 숨김 (top-1·접힘 목록·재생 중 큐) + praiseMismatch → praise 강등 — 투명 tally 미필터"
  - "6동작 전수 스윕 DIFF 0 + 전 done 멤버 spotCheck 방출 실측 (runId 1784660795)"
affects: [32-14 (다음 엔진 레버 — 같은 배포·스윕 관례), 32-15 (belle 최종 확인 — 이 상태 실기기)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "사후 검수 스테이지 = fault_zoom/coach_audio 뼈대 3벌째 (complete 이후 단일 field-path 부분 갱신 + 전 경로 graceful no-op)"
    - "LLM 판정 보수 후처리 = 보낸 recordId만 인정·응답 누락=uncertain·숨김은 명백 mismatch만 — 환각 id가 숨김 권한을 얻지 못하는 구조"
    - "숨김-정합 불변식 validator = hiddenRecordIds ⊆ mismatch verdicts (write 시점 강제 — T-32-30)"

key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/spot_check.py
    - backend/tests/phase32/test_spot_check.py
  modified:
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - backend/shared/python/sunity_shared/models.py
    - docs/contract.md
    - app/src/types/analysis.ts
    - app/src/lib/userAnalyses.ts
    - app/src/app/analysis/result.tsx

key-decisions:
  - "판정 모델 = gemini-3.1-pro-preview (플랜 지정 폴백): gemini-omni-flash-preview 는 generate_content 400 'This model only supports Interactions API' — 텍스트 판정 경로 자체 부재로 형식 게이트 탈락. env GEMINI_SPOTCHECK_MODEL 로 재배포 없이 스왑 가능 (flash 참고 실측 동봉)"
  - "프롬프트에 '기준 = IPSF 절대 자세 기준' 정의 명시 — 1차 스모크에서 이 정의 없이는 절대-기준 문장까지 전부 uncertain(판정 무력화) 실측. 비교-측정 record(deviationSource != ipsf_absolute)는 '(비교 측정)' 마커로 uncertain 규칙 명시"
  - "재생 중 큐(자막·오디오)에도 동일 숨김 적용 — 불일치 문장을 소리내 읽는 것도 '틀린 말 내보내기' (D-23 동일 원칙, 카드 표면의 일부)"
  - "스팟체크 캐시 없음(의도) — 입력(그 분석의 프레임+문장)이 분석마다 고유해 교차-분석 적중 구조적 0. PROMPT_VERSION 은 방출 감사 필드 + bump 규율로 유지 (Pitfall 8)"
  - "프레임 예산 = clamp(2×판정 record 수, 4..8) hold-window 균등 — record별 개별 시간창이 계약에 없어 'record당 최대 2'를 예산 산술로 구현 (dimensions._select_window 공유 — 측정과 동일 소스)"

patterns-established:
  - "검수 레이어 fail-open 계약 명문화 — 부가 레이어 장애가 제품 표면을 비우지 못하게 표시 정책을 계약(§12.8)에 고정"

requirements-completed: [D-22, D-23]

# Metrics
duration: ~4h 15m (스윕 82분 + 사전 대기 포함)
completed: 2026-07-22
---

# Phase 32 Plan 13: omni 스팟체크 — 문장↔영상 일치 검수 + 칭찬 교차검증 Summary

**감점 카드 문장(statusLine/cueLine)과 summaryPraise.headline(앱이 렌더하는 그 문장)을 분석 사후 스테이지에서 Gemini 판정(분석당 1콜, strict 스키마, 보수 기준)으로 검수해 명백 불일치 카드만 recordId 기반으로 표면에서 숨기는 D-23 운영 자가검증을 가동 — 동기 경로 신규 호출 0(속도 예산 구조 보호), 6동작 전수 스윕 DIFF 0 + 전 done 멤버 spotCheck 방출·오숨김 0 실측, runtime 1.1.0 OTA 발행**

## Task Commits

| Task | 내용 | 커밋 |
|---|---|---|
| 1 | spot_check.py 어댑터 + 멀티모달 스모크(모델 확정) + 테스트 20건 | `13bc3c7` |
| 2 | 사후 스테이지 배선 + 계약 3면(§12.8) + 앱 recordId 숨김 소비 + 테스트 16건 | `e8292c5` |
| 3 | Pod 배포 + 6동작 전수 스윕 + OTA (코드 무수정 — 본 SUMMARY가 기록) | (docs 커밋) |

## 멀티모달 스모크 실측 (Task 1 — 판정 모델 확정)

power-spin fault fixture 프레임 4장(640px JPEG) + 실 phrasebook record 문장 + praise 문장, strict response_schema 1콜씩:

| 모델 | 결과 | 근거 |
|---|---|---|
| gemini-omni-flash-preview | **탈락 (형식 불충족)** | generate_content **400 INVALID_ARGUMENT "This model only supports Interactions API"** — 텍스트 판정·response_schema 경로 자체가 없음 (영상 생성 전용, spike 004 [ASSUMED A1] 해소) |
| **gemini-3.1-pro-preview (채택)** | strict JSON 준수 + **판별력 실증** | 실결함 문장 2건 match / **조작 거짓 문장(그립 이탈) mismatch** / praise 부재 not_given. 11.9~14.6s, 토큰 in ~4.9K / out ~240 (분석당 비용 수 센트 미만) |
| gemini-3.5-flash (참고) | 동일 verdict·동일 형식 | 5.6~6.6s — env `GEMINI_SPOTCHECK_MODEL` 스왑 비용 레버로 기록 |

- **프롬프트 설계 실측 (스모크 1차→2차):** '기준' 정의 없이는 절대-기준 문장("기준보다 덜 펴져")까지 전부 uncertain — **판정 무력화**. '기준 = IPSF 절대 자세 기준(무릎 완전 신전 180° 등)' 정의 추가 후 실결함 match / 조작 거짓 mismatch 판별 성립. 비교-측정 record 는 `(비교 측정)` 마커로 uncertain 규칙 명시(프레임만으로 반증 불가 — 정직한 통과).

## D-23 전수 스윕 (Task 3 — 배포 게이트)

- **일시:** 2026-07-21 19:06 ~ 20:28 UTC (82분, SERIAL — [[pipeline-not-concurrency-safe-eval-serial]])
- **runId:** `1784660795` / uid `phase25eval` / Pod `6seluxc43awmqi` (RTX 4090)
- **기질:** run_sweep_3216.sh mirror (`/workspace/eval32/run_sweep_3213.sh` + `GEMINI_SPOTCHECK_MODEL`) — CPU EP, 32-16 audio 기준선(runId 1784649897)과 동일 기질.
- **배포:** push `39155c0..e8292c5` → Pod git pull(`e8292c5`) → start_server.sh 에 `GEMINI_SPOTCHECK_MODEL=gemini-3.1-pro-preview` 박제 + 재기동 → `/health` 200 (`auth_configured: true, pipeline_loaded: true`, proxy 외부 경로 200 확인).

### 점수·verdict diff (diff_3209.py — 32-16 기준선 대비): **DIFF_MEMBERS=0 (PASS)**

| member | 기준선 → 신규 | crit/err | baseSyncMs | newSyncMs |
|---|---|---|---|---|
| power-spin fault | 55 → **55** | OK | 206,493 | 224,859 |
| power-spin success | 100 → **100** | OK | 281,421 | 280,746 |
| peter-pan fault | 79 → **79** | OK | 175,903 | 180,347 |
| peter-pan success | 100 → **100** | OK | 226,644 | 230,790 |
| elbow-twist-sister fault | 66 → **66** | OK | 406,206 | 413,171 |
| elbow-twist-sister success | 100 → **100** | OK | 521,312 | 515,474 |
| pdshape fault | 58 → **58** | OK | 450,397 | 460,054 |
| pdshape success | 100 → **100** | OK | 369,075 | 374,702 |
| kip-up fault | 80 → **80** | OK | 195,130 | 190,765 |
| kip-up success | 100 → **100** | OK | 213,674 | 212,891 |
| climb fault/success | gate → gate | OK | — | — |

- **동기 경로 회귀 0 (구조 증명):** 저장 doc `timingsMs` 에 `spot_check` 키 **부재 실측** (complete 시 직렬화 — 스테이지는 그 이후). 최대 편차 power-spin fault +8.9%는 stage 분해로 **s3_download +9.4s + coach_dual(LLM 네트워크) +8.4s** — 이 멤버의 역대 스윕 변동(32-09 223.5s → 32-16 206.5s → 지금 224.9s = 32-09 수준 회귀) 범위 내 네트워크 노이즈. spot_check 소요는 stage 로그로만: **6.5~13.2s/분석** (11회, 실패 0).

### spotCheck 방출 실측 (fetch_docs_3213.py — `/workspace/eval32/spot_docs.json`)

| member | doc | spotCheck | hidden | praiseMismatch | verdicts (match/uncertain/mismatch) | recordId 정합 | validator |
|---|---|---|---|---|---|---|---|
| power-spin fault | done | done | 0 | False | **1**/2/0 (r00:leg_extension **match** — "무릎이 완전히 펴지지 않고 구부러진 모습" 실측 확인) | 완전 | PASS |
| peter-pan fault | done | done | 0 | False | 0/3/0 | 완전 | PASS |
| elbow-twist-sister fault | done | done | 0 | False | 0/7/0 | 완전 | PASS |
| pdshape fault | done | done | 0 | False | 0/7/0 | 완전 | PASS |
| kip-up fault | done | done | 0 | False | 0/1/0 | 완전 | PASS |
| success 5종 | done | done | 0 | False | 0/0/0 (praise-only 콜 — clean_dimension headline 검증 통과) | — | PASS |
| climb fault/success | gate | 부재 (complete 미도달 — 정상) | — | — | — | — | — |

- **판정 분포 총계: match 1 / uncertain 20 / mismatch 0 — 오숨김(정타·실결함 카드 숨김) 0.** fixture 문장은 전부 실측 결함이므로 숨김 0이 정답 분포. mismatch 경로의 판별력은 스모크의 조작 거짓 문장(mismatch 판정)과 단위 테스트가 커버.
- **recordId 정합:** 전 멤버 verdicts recordId ⊆ 방출 record recordId (환각 id 0) + hidden ⊆ mismatch (숨김-정합 불변식) + `_validate_spot_check` 재검증 전 doc PASS.
- uncertain 사유 2종: ①비교-측정 record(`(비교 측정)` 마커 — 프레임 반증 불가, 설계대로) ②모델 응답 누락(elbow/pdshape 7-record 멤버 일부 — 보수 후처리가 uncertain=표시로 통과, fail-open 방향). ②는 프롬프트 개선 후보로 기록(모든 recordId 에 1항목 강제 지시) — 숨김 방향 위험 0이라 이번 조정·재스윕 불요.

### 앱 변경 OTA (runtime 1.1.0 — 32-12 확립 경로)

- **시뮬레이터 확인 선행:** typecheck clean + node --test 33건 pass + **Metro production 번들(`expo export -p ios`) 성공** + 시뮬레이터(iPhone 16 Pro) 앱 부팅·인트로 렌더 스크린샷 실증 ([[verify-ui-on-simulator-before-ota]] — 변경은 result 화면 조건부 필터라 legacy doc 에서 렌더 diff 0).
- **발행:** production 그룹 `66233574-d937-40ce-ac45-e65cfa0d3475` + preview 그룹 `666ca0e0-59d7-42c9-a691-ece8f3171730` (둘 다 runtime 1.1.0, commit e8292c5).
- **롤백 대상:** production `713a28d8-e6f3-48c9-b847-700f0f50f823` (32-12 — `npx eas update:republish --group <id>` 1분 경로).

## Accomplishments

- **spot_check.py (Task 1):** gemini_vision_scorer 관례 복제 — lazy client 싱글톤(top-level genai import 0, 소스 단언 테스트), SPOTCHECK_PROMPT_VERSION, env 모델 주입, strict response_schema(자유 텍스트 파싱 0), temp 0, 분석당 1콜 고정, records 상한 8(감점 큰 순 — 초과분 미판정 통과), 보수 후처리(응답 누락·환각 id·enum 밖 = uncertain 표시). 무키 skipped / API 실패 failed — 전부 no-op raise 0 (SP-3).
- **사후 스테이지 + 계약 (Task 2):** `_run_deferred_spot_check`(fault_zoom/coach_audio 뼈대 3벌째) — firestore_complete·fault_zoom **이후** 소스 고정(`run_spot_check(` 호출 지점 1곳 단언 테스트), 프레임 = `inputs.frames` 재사용(재디코딩 0), mismatch 구조 로그 적재(D-23). `update_analysis_spot_check` = `result.spotCheck` 단일 field-path + 숨김-정합 불변식. 계약 3면 lockstep(§12.8 표시 정책 명문) + 어댑터↔models 상수 lockstep 테스트.
- **앱 소비 (Task 2):** `normalizeSpotCheck` 방어 파싱(status 화이트리스트·verdict enum·malformed=undefined 강등) + result.tsx 숨김 = status 'done' 일 때만, recordId 맵 기반 — top-1 선정·접힘 목록·재생 중 큐·요약 카드 파생에 적용, **ScoreBreakdownSection 투명 tally·드릴다운 내역은 미필터** (채점 불변 경계 주석). praiseMismatch → summarySource 강등(32-07 사전 배선 소비).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - D-23 동일 원칙] 재생 중 큐(자막·오디오)에도 숨김 적용**
- **Found during:** Task 2 (cueWindows 배선 검토)
- **Issue:** 플랜은 "감점 카드 목록" 숨김만 명시 — 그러나 불일치 판정된 record 의 cueLine 은 재생 중 자막·음성으로도 그대로 나감 ("틀린 말을 내보내느니 안 보여줌" 원칙과 모순)
- **Fix:** cueWindows 입력에서 hidden record 제외 — 같은 hidden 집합, 같은 fail-open 게이트. 표면(카드·큐)만이며 tally 무접촉
- **Files modified:** app/src/app/analysis/result.tsx
- **Commit:** `e8292c5`

**2. [Rule 1 - graceful] 프레임 라벨 fps 소스 부재 폴백**
- **Found during:** Task 2 (로컬 단위 테스트 — `_pipeline_frame_fps` 폴백 경로가 frame_extractor(imageio, 로컬 dev env 부재)를 import)
- **Fix:** fps 취득을 try/except 로 감싸고 실패 시 초 라벨 대신 프레임 인덱스 라벨 강등 (라벨은 프롬프트 표기 전용 — fps 단일 출처 규율(I1)·리터럴 9.0 금지 유지). 프로덕션(Pod)은 어댑터 초기화로 항상 초 라벨
- **Files modified:** backend/functions/pipeline/app.py
- **Commit:** `e8292c5`

**3. [Rule 1 - 표시 정합] all-hidden 시 '다른 감점 항목' 빈 섹션 헤더 방지**
- **Found during:** Task 2 (접힘 목록 필터 후 edge 검토)
- **Fix:** 표시 가능한 비-top record 존재 시에만 섹션 렌더 (헤더만 남는 빈 목록 0)
- **Files modified:** app/src/app/analysis/result.tsx
- **Commit:** `e8292c5`

### 플랜 경로 내 확정 (deviation 아님 — 기록)

- **omni 탈락 → pro 폴백:** 플랜이 명시한 분기 그대로 ("실패·형식 불충족 시 gemini-3.1-pro-preview 폴백 확정"). 스모크 2콜(omni 1 + pro 1) + 판별력 검증 2콜(pro/flash) 추가 실측.

**Total deviations:** 3 auto-fixed. **Impact:** 전부 D-23 일관성·graceful 견고성 — scope creep 0.

## Verification

- `pytest tests/phase32` → **155 passed** (기존 119 + 신규 36) / 회귀 selection(firestore·lockstep·contract·deduction) 428 passed / 1 failed — **기존과 동일한 pre-existing 실패**(phase06 NotPole gate, 라인 5117 — 스팟체크 무관) + 12 collection errors(로컬 imageio 부재, 32-06/32-09 기록과 동일. baseline 초과 실패 0)
- `npm run typecheck` clean + node --test lib 33건 pass + Metro production 번들 성공 + 시뮬레이터 부팅 렌더 실증
- Pod `/health` 200 (배포 전·후·스윕 후 + proxy 외부 경로)
- 6동작 스윕 DIFF_MEMBERS=0 + 전 done 멤버 spotCheck done·validator PASS·recordId 정합·오숨김 0
- OTA production/preview 발행 (runtime 1.1.0) + 롤백 group 기록
- STATE.md/ROADMAP.md 무접촉 (orchestrator 소관)

## Known Stubs

없음 — 스팟체크는 실 Gemini 판정·실 계약 소비. 숨김이 발동하는 실사례(mismatch)는 프로덕션 오문장 발생 시에만 나타나는 것이 정의상 정상 (fixture 정답 분포 = 숨김 0).

## Threat Flags

없음 — 신규 표면(Gemini 판정 → 카드 숨김, 사후 쓰기)은 전부 플랜 threat_model(T-32-30/31/32/33) mitigate 경계 안: 판정 권한 = 표면 숨김만(tally 무접촉), 숨김-정합 불변식 validator, graceful fail-open, 기존 vision 데이터 경계 재사용(신규 노출면 0), 단일 field-path 쓰기.

## 산출물 (Pod, repo 밖 — baseline 무접촉 관례)

`/workspace/eval32/spot/phase25/phase25_sweep_report.json` + `spot_docs.json` + `spot_sweep.log` + `run_sweep_3213.sh` / `fetch_docs_3213.py`

## Next Plan Readiness

- 32-15 belle 최종 확인이 이 상태(spotCheck 방출 + 앱 숨김 소비 OTA)를 실기기로 본다 — 신규 분석에서 `result.spotCheck` 필드 방출 시작.
- 프롬프트 개선 후보(비차단): 모델 응답 누락 record 0건화 지시(모든 recordId 에 1항목 강제) — 변경 시 SPOTCHECK_PROMPT_VERSION bump.
- 모델 비용 레버: `GEMINI_SPOTCHECK_MODEL=gemini-3.5-flash` 스왑 가능 (동일 verdict 실측 동봉) — belle 판단 재료.

## Self-Check: PASSED

- FOUND: backend/shared/python/sunity_shared/analysis/spot_check.py
- FOUND: backend/tests/phase32/test_spot_check.py
- FOUND: .planning/phases/32-result-readability-3-omni/32-13-SUMMARY.md
- FOUND commits: 13bc3c7 / e8292c5 (git log 확인)
- 파일 삭제 0 (커밋 2건 전부 add/modify만)
- Pod HEAD e8292c5 = origin/main + OTA 66233574(production)/666ca0e0(preview) 발행 확인

---
*Phase: 32-result-readability-3-omni*
*Completed: 2026-07-22*
