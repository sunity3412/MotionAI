---
phase: 32-result-readability-3-omni
plan: 14
subsystem: backend-pipeline, contract, ui, deploy
tags: [d22, d23, rtmw, keypoint-report, display-promotion, backward-compat, validator, pod-deploy, d23-sweep, python, typescript]

# Dependency graph
requires:
  - phase: 32-13
    provides: "스윕 기준선 (runId 1784660795) + 배포·스윕 관례 (run_sweep_3213.sh mirror)"
  - phase: 12-01
    provides: "KeypointReport 스키마·_KEYPOINT_NAMES 단일 출처·scoped validator (확장 대상)"
provides:
  - "keypointReport.joints 12 방출 (+left/right_ankle, +left/right_elbow) — version 1.1, 전 소비처 len() 파생 자동 추종"
  - "firestore_admin._validate_keypoint_report 길이 정합 신설 (joints ∈ {8,12} + data/confidence frames×J — legacy 하위호환 green)"
  - "계약 3면 lockstep: 'joints 배열 = capability source' 명문 (contract.md §9.12 + analysis.ts + keypoint_frame/models)"
  - "신규 관절 conf 분포 실측 (동작별) — 32-15/2단 감점 편입 게이트 재료"
  - "keypoint_augmenter elbow 매핑 활성 (audit 대조·mirror hint — 쓰기측은 보수 유지)"
affects: [32-15 (belle 최종 확인 — 신규 분석에서 12관절 오버레이 실기기), 2단 감점 편입 게이트 (후속 phase — conf 분포가 입력)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "표시층 확장 = 단일 출처 tuple append + len() 파생 자동 추종 (하드코딩 12 금지) — 소비처 전수가 배열 길이로 자연 분기"
    - "validator cross-field 정합 = scoped validator 내부 post-loop 블록 (본체 _validate_dict_only_scalars 무변경 박제 유지)"

key-files:
  created:
    - backend/tests/phase32/test_keypoint_report_expansion.py
  modified:
    - backend/shared/python/sunity_shared/analysis/keypoint_frame.py
    - backend/shared/python/sunity_shared/analysis/assemble.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - backend/shared/python/sunity_shared/models.py
    - backend/shared/python/sunity_shared/gemini/keypoint_augmenter.py
    - backend/functions/pipeline/app.py (주석만 — 산식·판정 기록)
    - docs/contract.md
    - app/src/types/analysis.ts
    - app/src/components/KeypointOverlay.tsx
    - app/src/lib/deductionLabels.ts

key-decisions:
  - "version bump = '1.0'→'1.1' (참고용) — 하위호환 판별은 joints 배열 길이(capability source)로 명문화. 기존 값 실측 '1.0' 확인 후 bump"
  - "신규 4관절의 앱 delta-강조 배선 = null (표시 전용 점): ankle 각은 kismam에 없고 elbow 각의 시각 proxy는 legacy 손 매핑 유지(이중 강조 방지) — 강조 시맨틱 무변경, 2단 게이트 후 재검토"
  - "pipeline 쓰기측 elbow 반영(_apply_keypoint_refinement_to_report)은 None 의도적 유지 — augmenter 매핑 활성은 읽기(대조·mirror hint) 전용, 신규 관절 좌표 덮어쓰기는 2단 게이트 뒤 (fail-safe)"
  - "OTA 미발행 (이 플랜) — 앱 변경분은 방어적(Record 키 추가·라벨)이며 구 번들도 신규 12관절 doc을 배열 길이 기반으로 크래시 없이 소비(전 소비처 동적 조회 코드추적). 12관절 오버레이 실기기 확인은 32-15 (belle 최종 확인 웨이브)가 신규 분석으로 소비"

patterns-established:
  - "'데이터는 있는데 렌더 0' 재발 방지 절차 = 백엔드·앱 소비처 전수 grep audit + 수정/유지 판정 목록 기록 (31 화살표 원인 구조 해소)"

requirements-completed: [D-22]

# Metrics
duration: ~1h 50m (스윕 70분 포함)
completed: 2026-07-22
---

# Phase 32 Plan 14: RTMW 측정층 표시 승격 8→12 (D-22 1단) Summary

**RTMW 백본이 이미 검출하던 발목·팔꿈치 좌표를 keypointReport 표시층(joints 8→12, version 1.1)으로 승격 — 감점·각도층 완전 무접촉(diff 0), validator 길이 정합 신설로 legacy 8 doc 하위호환 증명, 계약 3면에 "joints 배열 = capability source" 명문, Pod 배포 후 6동작 전수 스윕 DIFF 0 + 전 done doc 12관절 방출·validator PASS·신규 관절 conf 분포 실측(2단 게이트 재료) 완료**

## Task Commits

| Task | 내용 | 커밋 |
|---|---|---|
| 1 (RED) | 확장 실패 테스트 16건 (방출 12·validator 정합·매핑·augmenter) | `753c324` |
| 1 (GREEN) | 8→12 확장 + validator 신설 + augmenter + 계약 3면 + phase12 테스트 파생화 (atomic) | `f2b6ec1` |
| 2 | 앱 하위호환 — Record 4키(null) + 발목 라벨 + 주석 하드코딩 서술 제거 | `0975210` |
| 3 | 용량·인덱스·배포·스윕 (코드 무수정 — 본 SUMMARY가 기록) | (docs 커밋) |

## D-23 전수 스윕 (Task 3 — 배포 게이트)

- **일시:** 2026-07-21 23:34:45 ~ 2026-07-22 00:45 UTC (~70분, SERIAL — [[pipeline-not-concurrency-safe-eval-serial]])
- **runId:** `1784676884` / uid `phase25eval` / Pod `6seluxc43awmqi` (RTX 4090)
- **기질:** run_sweep_3213.sh mirror (`/workspace/eval32/run_sweep_3214.sh`, LD_LIBRARY_PATH 미설정=CPU EP — 32-13 기준선과 동일 기질)
- **배포:** push `e7705a7..0975210` → Pod pull(`0975210`) → start_server.sh 재기동(aws_env 소싱 — 아래 deviation 2) → `/health` 200 (`auth_configured: true, pipeline_loaded: true`) + proxy 외부 경로 200. 스윕 후 재확인 200.

### 점수·verdict·criteria diff (diff_3209.py — 32-13 기준선 runId 1784660795 대비): **DIFF_MEMBERS=0 (PASS)**

| member | 기준선 → 신규 | crit/err | baseSyncMs | newSyncMs |
|---|---|---|---|---|
| power-spin fault | 55 → **55** | OK | 224,859 | 210,573 |
| power-spin success | 100 → **100** | OK | 280,746 | 261,582 |
| peter-pan fault | 79 → **79** | OK | 180,347 | 173,856 |
| peter-pan success | 100 → **100** | OK | 230,790 | 218,695 |
| elbow-twist-sister fault | 66 → **66** | OK | 413,171 | 401,270 |
| elbow-twist-sister success | 100 → **100** | OK | 515,474 | 510,580 |
| pdshape fault | 58 → **58** | OK | 460,054 | 436,047 |
| pdshape success | 100 → **100** | OK | 374,702 | 360,736 |
| kip-up fault | 80 → **80** | OK | 190,765 | 186,110 |
| kip-up success | 100 → **100** | OK | 212,891 | 203,666 |
| climb fault/success | gate → gate | OK | — | — |

표시층만 바뀌었으므로 완전 동일이 정답 분포 — 전 멤버 점수·activatedCriteria·status 일치, 전 멤버 sync 소요는 기준선 대비 소폭 빠름(네트워크 노이즈 범위, 회귀 0).

### keypointReport 방출 실측 (fetch_docs_3214.py — `/workspace/eval32/kp12_docs.json`)

| member | doc | joints | version | frames | fps | krKiB | docKiB | validator |
|---|---|---|---|---|---|---|---|---|
| power-spin fault | done | **12** | 1.1 | 166 | 18.0 | 141 | 246 | PASS |
| power-spin success | done | **12** | 1.1 | 212 | 18.0 | 181 | 292 | PASS |
| peter-pan fault | done | **12** | 1.1 | 124 | 18.0 | 105 | 191 | PASS |
| peter-pan success | done | **12** | 1.1 | 174 | 18.0 | 147 | 238 | PASS |
| elbow-twist-sister fault | done | **12** | 1.1 | 360 | 18.0 | 305 | 498 | PASS |
| elbow-twist-sister success | done | **12** | 1.1 | 440 | 18.0 | **375** | **585** | PASS |
| pdshape fault | done | **12** | 1.1 | 364 | 18.0 | 309 | 507 | PASS |
| pdshape success | done | **12** | 1.1 | 318 | 18.0 | 271 | 428 | PASS |
| kip-up fault | done | **12** | 1.1 | 136 | 18.0 | 116 | 205 | PASS |
| kip-up success | done | **12** | 1.1 | 134 | 18.0 | 134 | 222 | PASS |
| climb fault/success | comparison (gate — complete 미도달, 기준선과 동일 정상) | — | — | — | — | — | — | — |

- **reliability 붕괴 없음:** 12관절 확장 시 keypoints_2d 키 부재 → any_missing → 전 프레임 "low" 강제 위험을 실측 반박 — power-spin fault {medium 70, high 63, low 33} / kip-up success {high 134, medium 18, low 6} / elbow success {medium 212, low 140, high 88} (RTMW 어댑터가 COCO-17 전수를 채우는 구조 확인과 일치).

### 신규 관절 conf 분포 (동작별 — 2단 감점 편입 게이트 재료, ref = 같은 doc의 left_knee)

| member | l_ankle mean/≥0.5 | r_ankle | l_elbow | r_elbow | (ref l_knee) |
|---|---|---|---|---|---|
| power-spin fault | 0.58 / 0.59 | 0.61 / 0.73 | 0.63 / 0.69 | 0.64 / 0.78 | 0.57 / 0.65 |
| power-spin success | 0.57 / 0.59 | 0.57 / 0.60 | 0.63 / 0.68 | 0.69 / 0.84 | 0.54 / 0.55 |
| peter-pan fault | 0.81 / 0.98 | 0.78 / 0.98 | 0.74 / 0.90 | 0.74 / 0.93 | 0.77 / 0.96 |
| peter-pan success | 0.76 / 0.89 | 0.70 / 0.83 | 0.67 / 0.74 | 0.66 / 0.79 | 0.71 / 0.87 |
| elbow-twist fault | 0.53 / 0.57 | 0.60 / 0.68 | 0.55 / 0.63 | 0.52 / 0.51 | 0.50 / 0.53 |
| elbow-twist success | 0.49 / 0.47 | 0.55 / 0.59 | 0.56 / 0.64 | 0.51 / 0.52 | 0.46 / 0.43 |
| pdshape fault | 0.51 / 0.52 | 0.53 / 0.56 | 0.62 / 0.79 | 0.58 / 0.73 | 0.50 / 0.55 |
| pdshape success | 0.47 / 0.35 | 0.51 / 0.41 | 0.60 / 0.69 | 0.57 / 0.65 | 0.46 / 0.33 |
| kip-up fault | 0.83 / 0.96 | 0.84 / 0.96 | 0.76 / 0.95 | 0.78 / 0.98 | 0.78 / 0.94 |
| kip-up success | 0.82 / 0.96 | 0.83 / 0.96 | 0.78 / 0.98 | 0.78 / 0.94 | 0.77 / 0.93 |

- **판독:** 신규 관절 conf는 같은 영상의 legacy 무릎과 같은 밴드에서 움직인다(동작·화질 종속이지 관절 종속이 아님). kip-up/peter-pan은 ≥0.5 비율 0.9+, elbow-twist/pdshape는 0.4~0.7 (가림 많은 동작). 2단 감점 편입 판단 시 "동작별·관절별" 게이트가 필요하다는 실측 근거.

## 용량·인덱스 (Task 3 — A7 + 리뷰 MEDIUM 실측)

- **사전 근사 (합성 7자리 float):** 30s@18fps J=12 keypointReport ≈ 233 KiB / 60s ≈ 467 KiB — 1MiB 대비 각각 77%/54% 여유.
- **실측 (Admin SDK read → JSON 직렬화):** 실 좌표는 float 자릿수가 길어 근사보다 큼 — 최대 doc = elbow-twist success(24.4s 영상): keypointReport **375 KiB**, **doc 전체 585 KiB → 1MiB 여유율 42.9%**. 초당 증가 실측 ≈ 24 KiB/s(doc 전체).
- **breakeven 관찰 (비차단):** 실측 비율로 doc 1MiB 도달 ≈ **~40초대 영상**. 업로드에 시간 상한이 없어(100MB만) 장영상 리스크는 J=8 시절부터 존재(그때 ≈ ~50초대) — J=12가 1.24배 앞당김. 파일럿 시나리오(10~30s)는 여유. **후속 제안:** 좌표 소수 라운딩(예: 4자리 = 서브픽셀 유지) 시 data/confidence 바이트 ~50% 절감 — 별도 plan 후보로 기록 (fps 다운샘플·분리 저장보다 최소 침습).
- **18fps reference (forward-looking — 재처리는 phase 밖):** 30s 기준 J=12 ≈ 233 KiB(근사)/375 KiB(실측 비율) — referenceMotions doc은 분석 부속 필드가 적어 1MiB 여유 충분.
- **인덱스 면제 (gcloud 실측, analyses collection-group):** `result.keypointReport` + 리프 `data`/`confidence`/`axisData`/`axisMask` 전부 indexes=0 (면제) — J=12는 필드 경로 불변이라 기존 면제가 그대로 커버. 비면제 잔여(reliability T + joints 12)는 60s에도 ~1.1k 엔트리로 40k 한도 무관. pipeline/app.py 18fps 선택 주석의 J=8 산식을 J=12 기준으로 갱신(면제 의존 명시).

## 시뮬레이터 확인 (Task 3)

- typecheck clean + node --test 40건 pass + **Metro production 번들(`expo export -p ios`) 성공** + 시뮬레이터(iPhone 16 Pro) 앱 부팅·인트로 렌더 스크린샷(`/tmp/sim3214_intro2.png`) — [[verify-ui-on-simulator-before-ota]] 32-13 선례 수준.
- **12관절 doc 오버레이 실기기/시뮬 실렌더는 이 세션 미수행(정직 기록):** 시뮬레이터 앱의 익명 uid로는 스윕 doc(phase25eval)을 볼 수 없고, 스윕 중 신규 업로드는 동시성 금지. 렌더 정합은 코드추적으로 증명(전 소비처 `joints.length`/`indexOf`/`includes` 동적 — 하드코딩 0) — **32-15 belle 최종 확인 웨이브가 신규 분석으로 12관절 오버레이(발목·팔꿈치 점 4개 추가)를 실기기에서 본다.** OTA 미발행 결정 근거는 key-decisions 참조 (구 번들도 신규 doc 크래시 경로 0).

## 백엔드·앱 소비처 전수 audit (리뷰 HIGH — 수정/유지 판정 목록)

| 위치 | 발견 | 판정 |
|---|---|---|
| keypoint_frame.py Literal·_KEYPOINT_NAMES·docstring "len == 8"(:90)·NUM 주석 | 길이 서술 | **수정** (12 + legacy 병기) |
| assemble.build_keypoint_report docstring "8 body" + version "1.0" | 방출부 | **수정** (12 + 1.1 bump) |
| models.py re-export 주석 "8 body keypoint" | 계약 미러 | **수정** |
| firestore_admin._validate_keypoint_report | 길이 비검사 (실측 — 리뷰 HIGH 전제 정정과 일치) | **신설** (joints {8,12} + frames×J 정합) |
| keypoint_augmenter._SCHEMA_TO_REPORT_JOINT elbow None + 주석 3곳 | audit-only 매핑 | **수정** (elbow 활성 — 읽기 전용) |
| pipeline/app.py `_apply_keypoint_refinement_to_report` 로컬 schema_to_report elbow None | 쓰기측 반영 | **유지(None)** — 의도적 보수, 판정 주석 기록 |
| pipeline/app.py 18fps 선택 주석 40k 산식 (J=8) | stale 산식 | **수정** (J=12 산식 + 면제 의존 명시) |
| tests/phase12 5파일 (lockstep 8 단언·joints 하드코딩·길이 16/32 리터럴) | 좌초/의도 마스킹 | **수정** (_KEYPOINT_NAMES/NUM 파생) |
| skeleton.JOINT_ANGLES·JOINT_KEYS 8 (각도층) + ipsf_criteria/coach_hook_builder/gemini schemas·reference_extractor JointKeyLiteral 8 | 각도·감점층 | **유지** (이 플랜 무접촉 원칙 — acceptance diff 0) |
| vision_veto._HIGHLIGHT_KEYPOINTS 8 (독립 tuple, _KEYPOINT_NAMES 비파생) | 마커 소스 | **유지** (신규 관절 마커 편입은 2단 게이트 뒤; legacy 앱 호환 유지) |
| skeleton.NUM_KEYPOINTS=17 (COCO-17) / phase04 conftest 17 | 별개 이름공간 | **유지** (무관) |
| **앱**: KeypointOverlay `Record<KeypointName>` (typecheck 강제) | exhaustive map | **수정** (4키 null) |
| 앱 나머지 소비처 (result.tsx·PoseCompareFrames/Viewer·cueTrack·manualOffset·visualCards·userAnalyses·referenceMotions) | 전수 grep | **기능적 하드코딩 8 = 0건** (전부 배열 파생 — 유지) |
| KeypointOverlay 헤더 주석 "T × 8 × 2"·"8 keypoint" 서술 | stale 문서 | **수정** (joints.length 파생 서술) |

- **부수 발견 (표시 승격의 소비 실현):** `fault_zoom._leg_line_pts`가 이미 `left/right_ankle`을 knee 폴백으로 조회 중(:382-386) — 신규 12관절 doc부터 다리 라인이 (conf ≥ _KP_CONF_MIN 게이트 뒤) 무릎이 아닌 **발목까지 연장**된다. 사후 스테이지 PNG 표시 전용, 채점 무접촉 (스윕 diff 0가 증명). ARROW_JOINT_MAP은 무수정 (SEED ⑪ — 화살표 부활 방향 작업 0).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - 좌초] phase12 기존 테스트 5파일이 NUM 상수 확장으로 좌초 → 파생 구성으로 갱신**
- **Found during:** Task 1 GREEN (suite 실행)
- **Issue:** `NUM_KEYPOINTS_PHASE12`(=12)와 하드코딩 8-이름 joints 리스트/길이 리터럴(16·32)을 섞어 쓰던 테스트가 길이 불일치로 실패하거나, confidence range 테스트가 길이 오류에 가려 **의도와 다른 이유로 통과**(마스킹)
- **Fix:** joints를 `_KEYPOINT_NAMES` 파생으로, bad 배열 길이를 `T*J` 파생으로 — lockstep 테스트는 12 + legacy 8 prefix 순서 불변 단언으로 강화
- **Files modified:** tests/phase12 5파일 — **Commit:** `f2b6ec1`

**2. [Rule 3 - blocking] Pod 재기동 시 AWS 자격 증명 부재 → aws_env 소싱 후 재기동**
- **Found during:** Task 3 배포 (start_server.sh 1차 실행)
- **Issue:** 신규 SSH 세션에는 AWS env가 없어 SSM/Lambda 조회 실패 → `auth_configured: false`로 기동 (Lambda 위임 인증 불가 상태)
- **Fix:** `source /workspace/aws_env.sh && bash start_server.sh` 재실행 → `auth_configured: true` + proxy 200 확인
- **Files modified:** 없음 (운영 절차)

**3. [Rule 2 - audit 정확성] 범위 밖 파일 2곳의 stale 주석 갱신 (pipeline/app.py)**
- **Found during:** Task 1 전수 audit
- **Issue:** 18fps 선택 근거 주석의 40k 인덱스 산식이 J=8 기준(확장 후 사실과 다름), `_apply_keypoint_refinement_to_report`의 "elbow는 KeypointReport에 없음" 주석이 확장 후 거짓 — 31 "데이터는 있는데" 류 혼동 재발 소지
- **Fix:** 주석만 갱신 (J=12 산식 + 면제 의존 / 쓰기측 None 의도적 유지 판정 기록) — 코드 무변경
- **Files modified:** backend/functions/pipeline/app.py — **Commit:** `f2b6ec1`

**Total deviations:** 3 auto-fixed. **Impact:** 전부 정합성·운영 절차 — scope creep 0, 채점 경로 무접촉 유지.

## Verification

- `pytest tests/phase32` → **171 passed** (기존 155 + 신규 16) / `tests/phase12` + augmenter 포함 141 passed
- **전체 suite 무회귀 엄밀 증명:** full run 61 failures = **pre-change 기준 커밋(4f9d234) worktree에서 같은 커맨드 실행한 61 failures와 목록 diff 0** (전부 pre-existing: 풀-스위트 import 오염·로컬 env 결손·phase06 NotPole gate 등 — baseline 초과 0)
- 감점·각도층 무접촉: `git diff skeleton.py dimensions.py kismam.py fault_zoom.py` = **empty** (ARROW_JOINT_MAP 포함)
- `npm run typecheck` clean + node --test 40건 + Metro production 번들 성공 + 시뮬레이터 부팅 렌더
- Pod `/health` 200 (배포 전·후·스윕 후 + proxy 외부 경로)
- 6동작 스윕 DIFF_MEMBERS=0 + 전 done doc joints 12·version 1.1·validator PASS + conf 분포·실측 바이트 기록
- STATE.md/ROADMAP.md 무접촉 (orchestrator 소관)

## TDD Gate Compliance

- RED `753c324` (test — 10 failed 확인 후 커밋) → GREEN `f2b6ec1` (feat — 16/16 green). REFACTOR 커밋 없음(불필요). 통과 잔존분 6건은 하위호환 단언(양측 green이 정답인 검사)으로 RED 신호와 무관.

## Known Stubs

없음 — 신규 4관절은 RTMW 실좌표·실 confidence가 방출·영속되는 실데이터 (placeholder 0 좌표는 키 부재 시 기존 graceful 경로 그대로).

## Threat Flags

없음 — 플랜 threat_model 3건 전부 mitigate 이행: T-32-34(감점 유입) = 각도·감점층 diff 0 + augmenter 무영향 스윕 증명, T-32-35(1MB/인덱스) = 실측 42.9% 여유 + 면제 gcloud 확인, T-32-36(legacy 크래시) = validator legacy green + 앱 길이 판별.

## 산출물 (Pod, repo 밖 — baseline 무접촉 관례)

`/workspace/eval32/kp12/phase25/phase25_sweep_report.json` + `kp12_docs.json` + `kp12_sweep.log` + `run_sweep_3214.sh` / `fetch_docs_3214.py` (로컬 사본 `/tmp/kp12_docs.json`, 스크린샷 `/tmp/sim3214_intro2.png`)

## Next Plan Readiness

- **32-15 (belle 최종 확인):** 신규 분석부터 12관절 방출이 프로덕션 가동 중 — 실기기에서 오버레이 점 12개(발목·팔꿈치 추가)와 fault-zoom 다리 라인 발목 연장을 확인 가능. 앱 라벨(발목)은 커밋됨 — 실기기 반영은 다음 OTA에 자연 동승.
- **2단(감점 편입) 게이트 재료:** 위 conf 분포 표 — 동작별 편차가 커(0.35~0.98 ≥0.5 비율) 관절 단위가 아닌 동작×관절 게이트 설계 근거 확보.
- **비차단 후속 후보:** 좌표 소수 라운딩으로 doc 바이트 ~50% 절감 (장영상 1MiB breakeven ~40s → ~80s대) — quick 후보.

## Self-Check: PASSED

- FOUND: backend/tests/phase32/test_keypoint_report_expansion.py
- FOUND: .planning/phases/32-result-readability-3-omni/32-14-SUMMARY.md
- FOUND commits: 753c324 / f2b6ec1 / 0975210 (git log 확인)
- 파일 삭제 0 (커밋 3건 전부 add/modify만)
- Pod HEAD 0975210 = origin/main, /health 200, 스윕 산출물 Pod 존재 확인

---
*Phase: 32-result-readability-3-omni*
*Completed: 2026-07-22*
