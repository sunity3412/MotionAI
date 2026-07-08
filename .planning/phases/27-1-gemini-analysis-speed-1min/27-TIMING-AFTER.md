# 27-09 — After 실측 + D-01 Hard Gate 판정 (프로덕션 배포)

**작성 시작:** 2026-07-08 06:10 UTC (배포 전 선기록) · 실측 본문은 배포/스윕 후 추가
**대조 상대:** 27-TIMING-BEFORE.md (wave 2 cold run, runId 1783469050) — 27-02 명기대로 "같은 조건의 그 run"이 before 정본 (오래된 baseline 과의 drift 는 pre-existing 분리)

---

## §0. Canary/Rollback 선기록 (Phase 22 DR-02 — Pod 변형 전 박제)

**belle 승인:** 수신 완료 ("27-09도 approved, 끝까지 진행해줘") — 배포 + gate sweep + Gemini 크레딧 + Flash 전용 키 반영(최소 변경 조건) 포함.

### 배포 대상

| 항목 | 값 |
|------|-----|
| 배포 커밋 | `87a9326` (= 승인 커밋 `eeac41a` + Flash 전용 키 `GEMINI_MOMENT_MODEL` 1커밋 — 27-08 권고 반영, 코드 diff 3파일 +41/−1) |
| 배포 전 Pod pin | `6eb73b5` (27-01 계측 코드 — wave 3~6 최적화 미포함) |
| Pod | `s7gyvvlc6u7ktz` (RTX 4090) · proxy `https://s7gyvvlc6u7ktz-8000.proxy.runpod.net` |
| 배포 전 서버 | PID 9108 (Jul07 기동), /health 200, 분석 in-flight 0 (서버 로그 = health 만, GPU util 0%) |

### Rollback 레버 (우선순위 순)

**레버 1 — env 만으로 순차 경로 복귀 (코드 롤백 불요, 즉시):**

```bash
# /workspace/start_server.sh 에서 아래 3줄 제거(또는 값 변경) 후 재시작
export GEMINI_UPLOAD_PREFETCH=0      # 학생 업로드 ∥ 겹치기 OFF → 동기 경로
export GEMINI_FANOUT_WORKERS=1       # veto fan-out 순차 등가
# export GEMINI_MOMENT_MODEL=...     # 줄 삭제 → extractor 는 기존 기본 모델(2.5-pro) 복귀
```

부분 레버: 429/부분완료 검출 시 `GEMINI_FANOUT_WORKERS=2` 축소 재실행 (T-27-15/T-27-27).
`STUDENT_FRAME_CACHE=0` — 프레임 재사용 캐시 단독 OFF (메모리 이슈 시).

**레버 2 — git revert (env 로 못 끄는 구조 변경 롤백):**

wave 3~6 최적화 커밋 범위 (revert 대상):

| wave | plan | 커밋 범위 |
|------|------|-----------|
| 3 | 27-03 (핸들 세션) | `cb3c0f1..fde6aac` |
| 4 | 27-04 (포즈∥비전 겹치기) | `96feecf..11d175f` |
| 5 | 27-05 (coach∥Cerebras) | `d360dfd..fcb7f67` |
| 6 | 27-06 (zoom 사후 분리) | `b67f54e..53256f3` |
| — | Flash 전용 키 | `87a9326` (단일) |

절차: 로컬 revert → push → Pod `git -C /workspace/SunityMotion pull && git checkout <hash>` → `bash /workspace/start_server.sh` → /health 200 확인. 완전 복귀 지점 = `6eb73b5` checkout (배포 전 pin).

### Canary 계획

- gate sweep 자체가 canary — 배포 직후 즉시 sweep (실사용자 트래픽 노출 최소화). belle "끝까지 진행" = 시간대 합의 완료. 실측 중 앱 분석 유입 없음 확인 후 착수.
- FAIL(무회귀 위반) 시: 레버 1 즉시 적용 → 순차 경로 복귀 확인 → 원인 gap SUMMARY 박제 → gap-closure 회부. 회귀 상태 프로덕션 방치 금지.

### 신규 env 박제 계획 (start_server.sh — git 밖, Pitfall 6)

```bash
export GEMINI_UPLOAD_PREFETCH=1     # 27-04 겹치기 (코드 default ON — 명시 박제)
export GEMINI_FANOUT_WORKERS=4      # 27-05 veto fan-out (코드 default 4 — 명시 박제)
export STUDENT_FRAME_CACHE=1        # 27-06 프레임 재사용 (RunPod ON / Lambda 는 0)
export GEMINI_MOMENT_MODEL=gemini-3.5-flash  # 27-08 D-05 채택분 — extractor 만 Flash (veto 는 GEMINI_MODEL 체인 = Pro 유지)
```

기존 박제 라인(GEMINI_VISION_VETO_ENABLED=1 / GEMINI_MAX_VETO_WALL_S=300) 무변경.

---

## §1. 배포 기록 (Task 2 — 2026-07-08 06:17~06:33 UTC)

### 배포 커밋

| 항목 | 값 |
|------|-----|
| 최종 배포 커밋 | **`3894bc8`** (fix: File API orphan 정리 — 스모크에서 발견, 하단 참조) |
| 구성 | `eeac41a`(승인분 waves 3~7) + `87a9326`(Flash 전용 키) + `af56fb2`(docs) + `3894bc8`(orphan fix) |
| Pod repo | `/workspace/SunityMotion` = origin/main `3894bc8`, clean |
| 서버 | PID 48103 (06:28 재기동), `/health` 200 `{"status":"ok","auth_configured":true,"pipeline_loaded":true}` — 로컬+proxy 양쪽 확인, `X-RunPod-Token` 로드 (len 64, Lambda env 동기) |

### start_server.sh diff (git 밖 — Pitfall 6 증빙, 백업 `/workspace/start_server.sh.bak27`)

```diff
 export GEMINI_MAX_VETO_WALL_S=300    # 검증된 sweep 설정과 동일(기본 120 은 미검증)
+# ── Phase 27-09 신규 env 박제 (git 밖 — Pitfall 6. 미주입=무음 비활성/기본값) ──
+export GEMINI_UPLOAD_PREFETCH=1     # 27-04 학생 업로드+scene_finder 를 포즈 그늘에 겹치기 (rollback: 0)
+export GEMINI_FANOUT_WORKERS=4      # 27-05 veto fan-out 동시성 (429 시 2, rollback: 1)
+export STUDENT_FRAME_CACHE=1        # 27-06 학생 프레임 재사용 — RunPod ON (Lambda 는 0)
+export GEMINI_MOMENT_MODEL=gemini-3.5-flash  # 27-08 D-05 — moment extractor 만 Flash. veto 는 GEMINI_MODEL 체인(Pro) 유지 (rollback: 줄 삭제)
```

라이브 uvicorn 프로세스 env 검증 (`/proc/PID/environ`): 6종 전부 주입 확인 — `GEMINI_UPLOAD_PREFETCH=1`, `GEMINI_FANOUT_WORKERS=4`, `STUDENT_FRAME_CACHE=1`, `GEMINI_MOMENT_MODEL=gemini-3.5-flash`, `GEMINI_VISION_VETO_ENABLED=1`, `GEMINI_MAX_VETO_WALL_S=300`.

### Flash 전용 키 반영 (27-08 이관분 — 채택)

- 코드: `gemini_moment_extractor.py` — `GEMINI_MOMENT_MODEL` 우선, 미설정 시 기존 `GEMINI_MODEL` 체인 fallback (커밋 `87a9326`, +테스트 2종: 전용 키 우선/veto 무접촉 + fallback 유지). `run_sweep.py`에 production mirror setdefault 동봉.
- 런타임 스코프 단언 (27-08 방식 승계): `[27-09-scope] extractor=gemini-3.5-flash veto=gemini-3.1-pro-preview` → scoped OK.
- 모델 attribution (스모크 httpx): recognizer+scene = `gemini-3.5-flash:generateContent` ×2, veto 4콜+coach+hook = `gemini-3.1-pro-preview:generateContent` ×6 — veto Pro 유지 기계 확인.
- rollback: start_server.sh 의 `GEMINI_MOMENT_MODEL` 줄 삭제 → 기존 기본 모델(2.5-pro) 복귀.

### 스모크 (kip-up fault 1건, in-process — 06:22~06:24 UTC)

| 검증 항목 | 결과 |
|-----------|------|
| status / 오류 | done, ERROR/Traceback 0 |
| stage_timing 방출 | 13라인 (11경계 + prefetch marker + 사후 fault_zoom) |
| **prefetch 순서 (HIGH-1)** | `stage=gemini_upload_prefetch_submit` 06:22:22.132 → `stage=rtmw` 완료 06:22:31.464 — **submit 이 rtmw 완료보다 9.3s 앞** (겹치기 발동) |
| 학생 영상 업로드 | 분석당 1회 (prefetch 06:22:23, 세션 핸들 재사용) |
| 세션 delete | close() 일괄 delete 확인 (06:24:20, zoom 이후 outer finally) |
| wall | 125.1s (before kip-up fault 198.9s — 참고치, 정식 표는 §3) |

### 스모크가 발견한 누수 1건 → 즉시 fix (Rule 1, fix-now)

- **증상:** ref 영상 세션 업로드 성공(06:22:50) 직후 `files.get` 폴링이 **503** → `_wait_for_active` 가 graceful None 반환 → caller 는 자체 업로드 폴백(정상)했지만 **이미 업로드된 파일(2.25MB)은 아무도 delete 하지 않음** — File API orphan 적체 (20GB 사고 계보, T-27-06 누수 0 위반).
- **fix:** `file_session.py` — None 반환 전 orphan best-effort delete (`3894bc8`, 테스트 2종). 배포 후 서버 재기동.
- **정리:** File API 잔존 25건 전량 삭제 (스모크 orphan 1 + 27-08 이전 코드 실행 잔재 24 — pre-existing, 03:16~04:02 타임스탬프) → **잔존 0**.

### Cold 격리 (27-02/27-08 동일 방법)

- PROMPT_VERSION/SCHEMA_VERSION bump 0. 스모크가 재적재한 fixture 캐시 2건(TechniqueCache 1 + VisionVetoCache 1) 삭제 → dry-run 재확인 **잔존 0** (`/workspace/eval_out/phase27/after_cache_isolate_{delete,verify}.json`).
- TechniqueCache model 라벨=상수(27-08 발견) 반영: Flash/Pro 산출물이 캐시로 섞이지 않도록 sweep 전 격리 완료 상태에서 착수.

---

## §2. D-01 Hard Gate 판정 (Task 3 — 2026-07-08 06:38~07:41 UTC)

### 실행 기록

| run | runId | 시각 (UTC) | 조건 |
|-----|-------|-----------|------|
| after **cold** | `1783492735` | 06:38~07:08 | §1 cold 격리 후 (fixture 캐시 잔존 0), EVAL18 6페어 SERIAL in-process |
| after **warm** | `1783494855` | 07:14~07:35 | cold 직후 같은 페어 재실행 (cold 가 재적재한 캐시에 hit) |

원자료: `/workspace/eval_out/phase27/after_sweep{,_warm}.log`, `/workspace/eval_out_after27/phase25/phase25_sweep_report{,_warm}.json` (EVAL_OUT_DIR 분리 — wave 2 리포트 무접촉).

### cold 증빙 + fan-out 완주 (Pitfall 7)

채점 10멤버 전원 `telemetry.cacheHit=false` + veto `completedCalls/plannedCalls = 4/4` (리포트 JSON 기계 확인). warm 은 전원 `cacheHit=true` + 4/4. climb 2멤버 = not_pole 게이트 차단 (baseline 동일). **HTTP 429 실검출 0** — cold/warm 로그 grep hit 각 1건은 `elapsed_ms=1429`/타임스탬프 `,429` 오탐. `GEMINI_FANOUT_WORKERS=4 최종 채택` (축소 폴백 불발동).

### (a) 무회귀 — before(wave 2 cold run 1783469050) 대조: **PASS**

12멤버 record 레벨 기계 대조 (status/overallScore/errorCode/activatedCriteria/faults):

| motion | before F/S | after F/S | verdict (after) | 대조 |
|--------|-----------|-----------|-----------------|------|
| power-spin | 57 / 80 | **52** / 80 | discriminate (margin 28↑) | fault 만 drift — vision 이 이번 run 에 split 을 짚음 (pointed=[left_knee,right_knee], −12) |
| peter-pan | 83 / 100 | 83 / 100 | discriminate (17) | 동일 |
| elbow-twist-sister | 61 / 100 | 61 / 100 | discriminate (39) | 동일 |
| pdshape | 54 / 100 | 54 / 100 | discriminate (46) | 동일 |
| kip-up | 100 / 100 | **80** / 100 | **discriminate (20)** — known FP(TIE) 가 이번 run 해소 | fault 만 drift — vision split 짚음 (−20) |
| climb | not_pole | not_pole | known_gate_blocked | 동일 |

- **success 멤버 5/5 완전 동일** (점수·criteria·faults record 레벨) — 위양성 방향 회귀 0.
- fault 멤버 drift 2건은 모두 **감점 증가(결함 검출) 방향**이고 출처는 Gemini vision 짚기의 run 간 변동 (27-02 §관측 계보 — before run 에서 kip-up fault=100 이 관측된 그 변동의 역방향). margin 은 전 페어 유지·확대 (kip-up TIE→discriminate 20, power-spin 23→28).
- **정본 `evals/phase18/assert_baseline.py` PASS** (6페어 fault-label/regression 소스 정합, 위양성 1·게이트차단 1 명시 추적).

### (b) cold/warm 결정론: **병렬화 귀속 위반 0 — PASS** (pre-existing 예외 1계보 발견·박제)

10/12 멤버 **점수+faults record(measuredValue 포함) byte-동일**. in-run 재실행 체크(pdshape success)도 cold/warm 100/100 identical. 예외 = power-spin 2멤버, 전부 `leg_extension` 한 criterion 에 국한:

| member | cold | warm | 표면 |
|--------|------|------|------|
| power-spin fault | 52 (leg_ext measured **78.27°**, raw −90) | 52 (measured **140.9°**, raw −22.9) | 관절당 상한 −20 이 가려 **점수 동일** |
| power-spin success | **80** (leg_ext measured 135.84°, raw −29→cap −20) | **100** (leg_ext 미발화) | 측정이 tol 안쪽으로 이동 → 점수 divergence |

**근본 원인 (코드 고고학으로 확정):** `gemini_technique_recognizer.py:383-392` `_profile_from_cache` 가 TechniqueCache hit 시 `hold_window` 를 복원하지 않는다 (fresh 경로는 `:329` 에서 moments×fps 로 설정). → `dimensions._select_window` 가 자동(분산 최소) window 로 폴백 → extension 측정 대표 프레임이 이동. RTMW/DTW 는 결정론 확인됨 (alignment distance `32.70473519421446` cold/warm byte-동일).

**pre-existing 증빙:** 해당 함수 마지막 실질 수정 = `fc3b6b7` (phase 8 Plan 08-03). phase 27 커밋 중 이 파일 접촉은 `11d175f` (핸들 파라미터 스레딩)뿐 — 캐시 재구성/채점 무접촉. 이번 phase 의 병렬화(fan-out/prefetch/Flash)가 도입한 비결정론이 아니라, **27-09 가 최초의 full cold/warm 대조 sweep 이라서 처음 관측**된 것. env rollback 레버로는 재현/해소 모두 불가한 캐시 경계 버그 → rollback 부적용, **gap-closure 회부** (`deferred-items.md` 기록). 프로덕션 노출면: 같은 영상 재분석(캐시 hit) 시 extension 계열 측정 창이 바뀜 — 수정은 채점 표면 변경이라 자체 EVAL 게이트 동반 필수.

### (c) 프로덕션 로그 검증 (SPD-02 / HIGH-1)

| 항목 | cold | warm | 판정 |
|------|------|------|------|
| 학생 영상 `files.upload` (분석당 1회) | 초기 upload POST 24 = 13분석 상당(12멤버+재실행 1)의 학생+기준 페어 — 중복 0 | 24 | PASS |
| 세션 delete (누수 0) | DELETE 24 — **업로드/삭제 24/24 균형** | 24/24 | PASS |
| **prefetch 순서 (HIGH-1)** | `stage=gemini_upload_prefetch_submit` 13/13 이 해당 분석 `stage=rtmw` 완료보다 **전원 앞** (예: 06:39:08.638 submit → 06:39:21.067 rtmw) | 13/13 앞 | PASS — 겹치기 발동 상태의 표만 §3 채택 |
| ERROR/Traceback | Cerebras 코치 1차 JSON 파손 3건 → 기존 재시도/수치 폴백 규율로 진행 (27-02/27-08 과 동일 양성 경로, 점수 무관) | 5건 동일 | 양성 |

### 종합 판정: **PASS**

무회귀(hard) PASS + fan-out 완주 PASS + 업로드/delete 균형 PASS + prefetch 순서 PASS + 결정론(병렬화 귀속) PASS. **rollback 불발동** — Pod 프로덕션 구성 유지 (배포 커밋 `3894bc8`, env 6종 박제 그대로, `/health` 200 재확인 07:41 이후). pre-existing hold_window 캐시 버그 1건만 gap-closure 회부.

---

## §3. Before/After 단계 실측 대조 (동일 페어·동일 단계 키, 단위 ms)

before = wave 2 cold (runId 1783469050, 27-TIMING-BEFORE.md `timingsMs`) · after = §2 cold (runId 1783492735). 둘 다 `result.timingsMs` + `stage_timing` 로그.

### 페어별 단계 표 — after cold

| stage | ps-F | ps-S | pp-F | pp-S | ets-F | ets-S | pd-F | pd-S | ku-F | ku-S |
|-------|------|------|------|------|-------|-------|------|------|------|------|
| s3_download | 4011 | 64556† | 3321 | 135759† | 4566 | 5213 | 3648 | 118502† | 3163 | 3254 |
| frame_extract | 10393 | 11418 | 7508 | 10101 | 19271 | 25022 | 19931 | 16994 | 7316 | 8572 |
| rtmw | 2035 | 2177 | 1398 | 1991 | 3320 | 4320 | 3997 | 2818 | 1397 | 1545 |
| scene_finder | 2077 | 2134 | 1762 | 2239 | 2247 | 2274 | 2599 | 2364 | 1954 | 1801 |
| recognizer | 5938 | 6088 | 7317 | 6692 | 5318 | 4905 | 6025 | 5549 | 5604 | 5465 |
| ref_fetch_download | 1375 | 1364 | 1023 | 1375 | 1451 | 1722 | 1570 | 1037 | 1162 | 969 |
| dtw_scoring | 33 | 32 | 21 | 22 | 136 | 133 | 61 | 70 | 19 | 18 |
| veto_collect | 36803 | 12511 | 19376 | 20883 | 27248 | 33371 | 26109 | 22104 | 21593 | 19836 |
| coach_dual | 31949 | 31234 | 30093 | 26106 | 12670 | 29914 | 32275 | 38233 | 29725 | 37778 |
| firestore_complete | 1361 | 1429 | 1225 | 1129 | 2276 | 2847 | 2575 | 2033 | 1106 | 1075 |
| fault_zoom (**사후** — complete 뒤) | 8621 | 7851 | 6643 | 3035 | 10362 | 10176 | 9367 | 7521 | 6042 | 5941 |

† s3_download 이상치 4건(성공 멤버) — 하단 "역행 단계" 참조.

climb (not_pole 게이트, 로그 전용): fault 총 25.2s (before 55.5s), success 96.0s (그중 s3 68.3s†; before 60.4s).

### 두-지표 분리 총계 (외부 리뷰 MEDIUM-3) — 단위 s

before 는 fault_zoom 이 complete **앞**에 실행됐으므로 time-to-first-result = wall (단일 지표). after 는 27-06 재배열로 두 지표가 분리된다.

| 지표 | ps-F | ps-S | pp-F | pp-S | ets-F | ets-S | pd-F | pd-S | ku-F | ku-S | median |
|------|------|------|------|------|-------|-------|------|------|------|------|--------|
| before wall (=TTFR=총시간) | 224.8 | 234.5 | 217.3 | 218.1 | 329.4 | 368.4 | 343.0 | 282.9 | 198.9 | 207.6 | 229.6 |
| **after time-to-first-result** (complete 도착) | 122.4 | 163.3 | 93.2 | 227.2 | 106.2 | 130.5 | 127.0 | 240.0 | 92.2 | 100.5 | **124.7** |
| after server task 총 시간 (zoom 포함) | 131.0 | 171.2 | 99.8 | 230.2 | 116.5 | 140.6 | 136.4 | 247.5 | 98.3 | 106.5 | 133.7 |
| zoom 추가 도착 시간 (first-result 후) | 8.6 | 7.9 | 6.6 | 3.0 | 10.4 | 10.2 | 9.4 | 7.5 | 6.0 | 5.9 | 7.7 |
| TTFR 델타 | −46% | −30% | −57% | **+4%**† | −68% | −65% | −63% | −15%† | −54% | −52% | **−46%** |

### 단계별 median 델타 (채점 10멤버)

| stage | before median | after median | 델타 | 레버 |
|-------|--------------|-------------|------|------|
| scene_finder | 22.2s | 2.2s | **−90%** | 27-04 prefetch 겹치기 (포즈 그늘에서 실행 — 잔여는 join 대기만) |
| recognizer | 35.5s | 5.8s | **−84%** | 27-03 세션 핸들(업로드 재사용) + 27-08/09 Flash 전용 키 |
| veto_collect | 87.2s | 21.9s | **−75%** | 27-05 fan-out 4-worker + 핸들 재사용 + still inline |
| coach_dual | 45.0s | 30.7s | −32% | 27-05 coach B∥Cerebras 동시화 |
| Gemini vision 그룹 (scene+recog+veto) | 138.5s | 29.9s | **−78%** | (wall 대비 60%→24%) |
| fault_zoom | 15.9s | 7.7s | −52% + **first-result 밖으로 이동** | 27-06 사후 분리 + 프레임 재사용 |
| frame_extract / rtmw / dtw | 10.4 / 2.2 / 0.03s | 10.9 / 2.1 / 0.03s | ±0 | 무접촉 (예상대로) |

**총계: 채점 10멤버 time-to-first-result median 229.6s → 124.7s (−46%), 합계 wall 2,624.9s → 1,478.0s (−43.7%).** 파일럿 피드백 "mode1 2.5~5.7분" → **1.5~4분(TTFR, s3 이상치 포함), s3 정규화 시 92~138s (median 104s = 1분 44초)**. 1분 목표(지향점) 대비: Gemini 레버는 계획 수확을 냈고 잔여 최대 항목은 coach_dual 30.7s > veto_collect 21.9s — D-01 스펙대로 시간은 보고 항목, hard 게이트 아님.

### 역행 단계 원인 (표 병기 의무)

- **s3_download 이상치 4건 (전부 success 멤버, 64.6~135.8s; before 3.4~16.7s):** 코드 원인 아님 — 근거: (1) 같은 파일이 warm run 에선 3.3~13초, before run 에서도 정상, (2) 같은 run 의 fault 멤버 6건은 전부 3.2~5.2s, (3) 해당 구간 로그는 재시도/오류 0 의 무음 대기 (boto3 GET 단독). Pod 아웃바운드 네트워크 일시 변동으로 판단. pp-S TTFR +4% 역행은 전액 s3 +128s 귀속 (s3 제외 시 ~99s = −55%). 관측 항목으로 deferred-items 에 기록 (레버 후보: S3 Transfer Acceleration/재시도 튜닝 — 이 phase 범위 밖).
- 그 외 역행 단계 0 — frame_extract/rtmw 는 오차 범위 내 동일.
