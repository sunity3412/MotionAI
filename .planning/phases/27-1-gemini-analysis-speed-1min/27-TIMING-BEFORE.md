# 27-02 — Before Cold Baseline 실측 (최적화 착수 전)

**측정일:** 2026-07-08 00:04~00:53 UTC · **runId:** 1783469050 · **tag:** cold
**목적:** D-01 무회귀 게이트(27-09)의 before 수치 + wave 3~6 레버 우선순위 실측 교정 (27-RESEARCH Open Q1/Q2 답).

## 실행 환경 (박제)

| 항목 | 값 |
|------|-----|
| Pod | `s7gyvvlc6u7ktz` (RTX 4090 24GB, Network Volume /workspace) |
| Pod repo pinned commit | `c398cf1` — 파이프라인 코드 = 27-01 계측 커밋(`a67356e`/`bab4666`)과 byte-동일. c398cf1 은 eval 하니스 관측 tee(`backend/evals/phase25/run_sweep.py`)만 추가 (read-only, 채점/파이프라인 무접촉) |
| 하니스 | `backend/evals/phase25/run_sweep.py` (EVAL18 6페어 양멤버 mode1, in-process `_process`, SERIAL) |
| EVAL_OUT_DIR | `/workspace/eval_out` (리포 밖 — baseline 오염 0) |
| 서버 | sweep 전 재시작(계측 코드 라이브), /health 200, 실측 중 프로덕션 분석 in-flight 0 (직전 분석 23:31 완료 확인 + belle 승인 "지금 시작 OK") |
| RTMW_DETERMINISTIC | 1 (하니스 setdefault) |

## Pod env 스냅샷 (27-RESEARCH Open Q2 검증)

`/workspace/start_server.sh`(git 밖) + 라이브 uvicorn 프로세스 env 대조 — 값 일치:

| env | 값 | 의미 |
|-----|-----|------|
| RECOGNIZER_BACKEND | `gemini` | recognizer = Gemini moment extractor (영상 업로드 #2 발생) |
| GEMINI_VISION_VETO_ENABLED | `1` | veto ON (학생+기준 영상 업로드 #3) |
| GEMINI_MAX_VETO_WALL_S | `300` | veto 예산 300s |
| GEMINI_COACH_ENABLED | `1` | coach B = Gemini (영상 업로드 #4) |
| GEMINI_*_MODEL override | 없음 | 기본값 사용 |

관측된 모델 인벤토리 (sweep 로그 httpx 라인): veto/coach/hook = `gemini-3.1-pro-preview`, scene_finder = `gemini-3.5-flash`, recognizer(moment extractor) = `gemini-2.5-pro` (**박제된 의도적 예외** — `gemini_moment_extractor.py:53-58`, vision-only 2.5 경로).
**결론: 인벤토리의 "학생 영상 업로드 4~5회" 가정 = 실환경에서 확정** (scene_finder + recognizer + veto + coach B 전 토글 ON).

## Cold 격리 기록 (T-27-03 mitigation — 조작 전량 박제)

- **PROMPT_VERSION/SCHEMA_VERSION bump 0** (프로덕션 캐시 오염 금지 준수). 현행 v11.2/v8.1/agg4 불변.
- 하니스에 캐시 무효화 옵션 부재 → 옵션 (b): Firestore `gemini_cache` 컬렉션에서 **fixture 12개 hash 한정** 문서 삭제 — TechniqueCache(doc id = video sha256) 12건 + VisionVetoCache(doc id prefix `vision_veto:{student_hash}:`, 全 버전·granularity 변형) 105건 = **117건 삭제** (스크립트 `/workspace/phase27_cache_isolate.py`, 산출 `/workspace/eval_out/phase27/cache_isolate_delete.json`). 삭제 후 dry-run 재확인 = 잔존 0.
- 프로덕션 사용자 영상 hash 무접촉 (fixture bytes sha256 prefix 매칭만).
- in-memory 캐시 = sweep 프로세스 신규 기동으로 자연 0.
- sweep 실행이 동일 키를 재적재함(코드 pin 상태의 결정론 출력) — 캐시 상태는 실측 후 원복과 등가.

## cold 증빙 — telemetry.cacheHit (멤버별)

10 채점 멤버 전원 `cacheHit=false` + veto fan-out `completedCalls/plannedCalls = 4/4`:

| member | cacheHit | vetoCalls | 비고 |
|--------|----------|-----------|------|
| power-spin fault/success | false / false | 4/4, 4/4 | |
| peter-pan fault/success | false / false | 4/4, 4/4 | |
| elbow-twist-sister fault/success | false / false | 4/4, 4/4 | |
| pdshape fault/success | false / false | 4/4, 4/4 | |
| kip-up fault/success | false / false | 4/4, 4/4 | |
| climb fault/success | n/a | n/a | not_pole 게이트로 veto 도달 전 중단 (baseline known_gate_blocked 동일) |
| pdshape success (하니스 내장 재실행) | **true** | — | 하니스 결정론 체크 전용 — **타이밍 표본 아님** (in-run 재실행 = 당연 warm). cold/warm 점수 identical (100/100, criteria []) |

## 페어별 단계 실측 (stage × elapsed_ms)

출처: `result.timingsMs` (27-01 계측, Firestore flat dict) + `stage_timing` 로그 라인 (`firestore_complete` 는 로그 전용). 단위 ms.

| stage | ps-F | ps-S | pp-F | pp-S | ets-F | ets-S | pd-F | pd-S | ku-F | ku-S |
|-------|------|------|------|------|-------|-------|------|------|------|------|
| s3_download | 3888 | 3376 | 6918 | 7576 | 3651 | 4174 | 4978 | 16682 | 13149 | 3953 |
| frame_extract | 8973 | 11518 | 6754 | 9280 | 20052 | 23216 | 19670 | 17029 | 7354 | 8619 |
| rtmw | 2143 | 2190 | 1325 | 1733 | 3693 | 4310 | 3686 | 2823 | 1401 | 1582 |
| scene_finder | 22125 | 22237 | 16714 | 21933 | 40659 | 37093 | 40814 | 29409 | 17172 | 18031 |
| recognizer | 30942 | 35533 | 28126 | 27947 | 38855 | 45037 | 48574 | 38063 | 27953 | 35397 |
| ref_fetch_download | 1366 | 1364 | 1283 | 1274 | 1719 | 1623 | 1862 | 1034 | 1171 | 1016 |
| dtw_scoring | 33 | 33 | 22 | 22 | 137 | 132 | 62 | 71 | 19 | 18 |
| veto_collect | 75681 | 86742 | 87661 | 74145 | 112017 | 140952 | 108099 | 94168 | 64674 | 70569 |
| coach_dual | 42766 | 35934 | 43164 | 45411 | 58551 | 66724 | 62581 | 46348 | 43282 | 44565 |
| assemble_misc | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| fault_zoom | 16320 | 14642 | 13592 | 15497 | 29850 | 32642 | 31325 | 24149 | 12893 | 14447 |
| firestore_complete | 1377 | 1688 | 1049 | 1094 | 2272 | 2624 | 2494 | 2102 | 1096 | 1085 |
| **wall (벽시계)** | **224800** | **234468** | **217299** | **218093** | **329374** | **368361** | **343048** | **282927** | **198907** | **207588** |
| 미계상 (wall−합계) | 19186 | 19211 | 10691 | 12181 | 17918 | 9834 | 18903 | 11049 | 8742 | 8305 |

(ps=power-spin, pp=peter-pan, ets=elbow-twist-sister, pd=pdshape, ku=kip-up; F=fault, S=success)

climb (not_pole 게이트 — 로그 전용 부분 계측): fault = s3 3558 / extract 7576 / rtmw 1450 / scene 16872 / recognizer 23010 / ref 1134 / dtw 50 → NotPoleMotionError, wall 55538. success = s3 3912 / extract 8729 / rtmw 1677 / scene 16957 / recognizer 26058 / ref 1154 / dtw 62 → NotPoleMotionError, wall 60426.

**총 소요:** 12 멤버 wall 합 2,740.8s (45.7분), sweep 전체 벽시계(첫 stage 00:04:23 → 마지막 firestore_complete 00:53:01) ≈ 48.6분. 채점 10멤버 평균 wall **262.5s (4분 22초)** — 파일럿 피드백 "mode1 2.5~5.7분" 실측 재현.

## 집계 (채점 10멤버, median 기준)

| 그룹 | median | wall 대비 |
|------|--------|-----------|
| pose (s3_download+frame_extract+rtmw) | 20.2s | 9% |
| **Gemini vision (scene_finder+recognizer+veto_collect)** | **138.5s** | **60%** |
| coach_dual (Gemini B + Cerebras 순차) | 45.0s | 20% |
| fault_zoom | 15.9s | 7% |
| 미계상 (hook 等) | 13.2s | 6% |
| median wall | 229.6s | 100% |

단계별 median: veto_collect 87.2s(38%) > coach_dual 45.0s(20%) > recognizer 35.5s(15%) > scene_finder 22.2s(10%) > fault_zoom 15.9s(7%) > frame_extract 10.4s(4.5%) > s3_download 4.6s > rtmw 2.2s > ref_fetch 1.3s > dtw 0.03s.

## 152s/197s 로그 재구성 추정 대비 (27-RESEARCH Open Q1 답)

추정(A4: 포즈 51 + 비전 52 + 후처리 49 = 152s, 총 197s, 미계상 ~45s)은 배분이 크게 어긋났다:

1. **포즈 51s → 실측 ~20s (과대 2.5배).** RTMW 자체는 1.3~4.3s에 불과 — 추정이 비전 대기를 포즈로 오귀속.
2. **비전 52s → 실측 ~139s (과소 2.7배). 전체의 60%가 Gemini 라운드트립** — veto_collect 단독 65~141s (영상 2 업로드+폴링 + 4콜 순차 + still 추출), recognizer 28~49s (업로드 #2), scene_finder 17~41s (업로드 #1). 업로드 1회+핸들 공유(27-03)와 포즈∥비전 겹치기(27-04)의 기대 수확이 추정보다 크다.
3. **미계상 ~45s의 정체 = coach_dual (36~67s).** coach B 영상 업로드 #4 + generate + Cerebras 순차 실행. 27-05(coach∥Cerebras 동시화 + 핸들 재사용) 근거 확정. 잔여 미계상 8~19s = hook Gemini text 호출(~14s 관측, 00:11:26→00:11:40 구간) + body profile/status write 등.
4. **후처리 49s → fault_zoom 실측 13~33s + firestore_complete 1~2.6s.** D-06 사후 분리(27-06)의 수확은 유효하되 추정보다 작음 — 우선순위는 Gemini 레버(27-03/04/05)가 앞선다.
5. **영상 길이 의존:** elbow-twist-sister/pdshape (긴 영상)는 전 단계 비례 증가 — wall 283~368s. 업로드·디코딩 비용이 길이에 선형.

**레버 우선순위 실측 교정: veto_collect > coach_dual > recognizer ≥ scene_finder > fault_zoom > pose.**

## 점수·verdict 참고 사본 (27-09 무회귀 대조용 — 정본 baseline 은 evals/phase18/25 기존 것)

| motion | fault | success | verdict |
|--------|-------|---------|---------|
| power-spin | 57 | 80 | discriminate (margin 23) |
| peter-pan | 83 | 100 | discriminate (margin 17) |
| elbow-twist-sister | 61 | 100 | discriminate (margin 39) |
| pdshape | 54 | 100 | discriminate (margin 46) |
| kip-up | 100 | 100 | TIE |
| climb | not_pole | not_pole | known_gate_blocked (baseline 동일) |

**관측 (27-09 대조 시 주의, 이 plan 범위 밖):** 이번 cold run 에서 kip-up fault=100 (phase25 sweep 47), power-spin success=80 (leg_extension 감점; 과거 100) — Gemini 비전 짚기의 run 간 변동으로 보임 (pointed=[] 관측). 27-09 의 before/after 는 **같은 조건의 이 run 을 before 로** 대조할 것 (오래된 baseline 과의 drift 는 pre-existing, 본 계측 코드는 점수 무접촉 — 27-01 무회귀 검증 완료).

## 원자료 위치

- Pod: `/workspace/eval_out/phase27/before_sweep.log` (stage_timing 로그 라인 146개 + full run 로그), `/workspace/eval_out/phase25/phase25_sweep_report.json` (timingsMs/wallMs/vetoTelemetry 포함 rich 리포트), `/workspace/eval_out/phase27/cache_isolate_{delete,verify}.json`
- 실측 후 Pod 상태: repo = origin/main `c398cf1` (파이프라인 = 27-01 코드), 서버 재기동 상태 유지 (/health 200)
