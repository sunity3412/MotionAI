# 27-08 — Pro→Flash 조건부 전환 실험 판정 (D-05)

**실험일:** 2026-07-08 03:16~04:02 UTC · **runId:** 1783480611 · **tag:** cold
**범위:** belle 승인 "approved 1순위만" — **moment extractor(recognizer)만**. coach B(2순위) 미실행, veto fan-out 제외(기본 보류 — 점수 직결 경로).

## 판정 요약

| 후보 | 전환 모델 | EVAL18 대조 | 게이트(D-05) | 프로덕션 반영 |
|------|----------|------------|--------------|---------------|
| 1순위 moment extractor | `gemini-3.5-flash` | 12멤버 record 레벨 **diff 0** | **통과 (완전 동일)** | **채택 — 단 반영 보류** (공유 env 제약, 하단 §반영 제약) |
| 2순위 coach B | — | 미실행 | — | 범위 외 (belle 승인 = 1순위만) |
| veto fan-out | — | 미실행 | — | 기본 보류 (D-05 명시) |

**결론: 게이트는 통과했으나(verdict·점수·faults 완전 동일 + recognizer 단계 median 8.5s 절감), env 한 줄 반영이 불가능한 구조적 제약이 실험 중 발견되어 프로덕션 반영은 보류한다.** 기각이 아니라 "채택 자격 획득 + 반영 이관"이다. 반영 경로는 §반영 제약 참조.

## 실행 환경 (박제)

| 항목 | 값 |
|------|-----|
| Pod | `s7gyvvlc6u7ktz` (RTX 4090) — repo pinned `6eb73b5` (= wave 2 Pro run과 파이프라인 코드 byte-동일, wave 3~6 최적화 미포함) |
| 하니스 | `backend/evals/phase25/run_sweep.py` (EVAL18 6페어 양멤버 mode1, in-process SERIAL) — wave 2와 동일 |
| EVAL_OUT_DIR | `/workspace/eval_out_flash27` (리포 밖 + wave 2 리포트 덮어쓰기 방지 분리) |
| 분석 in-flight | 0 확인 후 착수 (서버 로그 = 23:55 기동 후 health만, GPU util 0%) |
| RTMW_DETERMINISTIC | 1 (하니스 setdefault) |

## env override 방식 — 발견된 제약과 스코핑 (계획 대비 교정 2건)

**교정 1 — 플랜 전제 "`gemini/config.py`의 `GEMINI_*_MODEL` 패턴" 부정확:** moment extractor는 config.py(`resolve_model`)를 쓰지 않는다. 실제 키는 `GEMINI_MODEL`(`gemini_moment_extractor.py:58`, module-import 시점 캡처)이고, 현행 기본값은 vision-only 박제 예외인 2.5 계열 stable Pro다(같은 파일 53~58행 주석 — 3.x video-capable 대기).

**교정 2 — `GEMINI_MODEL`은 veto와 공유:** `gemini_vision_scorer.py:102`(`DEFAULT_VISION_MODEL`)도 같은 `GEMINI_MODEL` env를 읽는다. 프로세스 전역 export는 **veto fan-out까지 Flash로 flip**시키므로(이번 실험 명시 제외 대상) 금지.

**해법 (신규 env 발명 0, 파이프라인 코드 무접촉):** eval 전용 wrapper `/workspace/phase27_flash_moment_sweep.py` — extractor 모듈을 `GEMINI_MODEL=gemini-3.5-flash` 상태에서 먼저 import(flash 캡처)한 뒤 env 삭제 → vision_scorer import(기본 `gemini-3.1-pro-preview` 캡처) → run_sweep.py 실행. 런타임 단언 통과:

```
[flash-scope] extractor=gemini-3.5-flash veto=gemini-3.1-pro-preview (scoped OK)
```

**모델 attribution 기계 증거 (sweep 로그 httpx 집계):** `gemini-3.1-pro-preview:generateContent` 62콜(veto 4×10 + coach B + hook) / `gemini-3.5-flash:generateContent` 25콜(scene_finder + recognizer). veto가 Pro로 유지된 채 recognizer만 Flash로 실행됐음을 확인.

## Cold 격리 (27-02 방식 — 조작 전량 박제)

- PROMPT_VERSION/SCHEMA_VERSION bump 0. 실행 전 fixture 12개 hash 한정 gemini_cache **22건 삭제** → dry-run 재확인 잔존 0 (`/workspace/eval_out/phase27/flash_cache_isolate_{delete,verify}.json`).
- cold 증빙: 채점 10멤버 전원 `telemetry.cacheHit=false` + veto fan-out `completedCalls/plannedCalls = 4/4`. climb 2멤버 = not_pole 게이트(대조 기준과 동일).
- in-run 결정론 체크(pdshape 재실행): cold/warm 100/100, criteria selection identical.

## 대조 결과 (a) wave 2 Pro run — 같은 코드·같은 하니스·같은 cold 조건

기계 대조(compare_flash.py): 멤버별 status / overallScore / errorCode / activatedCriteria / deduction records(criterion·joint·severity·deduction) + 페어 verdict — **12멤버 전 필드 diff 0**.

| motion | fault | success | verdict (Flash) | verdict (wave 2 Pro) |
|--------|-------|---------|-----------------|----------------------|
| power-spin | 57 | 80 | discriminate (margin 23) | 동일 |
| peter-pan | 83 | 100 | discriminate (margin 17) | 동일 |
| elbow-twist-sister | 61 | 100 | discriminate (margin 39) | 동일 |
| pdshape | 54 | 100 | discriminate (margin 46) | 동일 |
| kip-up | 100 | 100 | TIE | 동일 |
| climb | not_pole | not_pole | gate/err | 동일 |

run 간 drift(wave 2에서 관측된 kip-up fault=100, power-spin success=80)까지 **그대로 재현**됐다 — Flash 전환이 채점 표면에 0 영향이라는 가장 강한 형태의 증거.

## 대조 결과 (b) evals/phase18 정본 baseline

- `assert_baseline.py` PASS (6페어 fault-label/regression 소스 정합).
- verdict 클래스 전 페어 일치: discriminate ×4, kip-up TIE(=정본 known_false_positive 계보), climb known_gate_blocked.
- 정본(2026-06-18) 점수 절대값과의 차이는 Flash run과 wave 2 Pro run이 **완전히 같은 차이**를 공유 → 전부 pre-existing drift(phase25 재튜닝 + Gemini run 간 변동)이고 Flash 효과가 아님. "Flash diffs match neither → 기각" 조건에 해당 없음.

## 레이턴시 델타 — recognizer 단계 (timingsMs, 둘 다 최적화 전 코드 주의)

| member | Flash ms | Pro ms (wave 2) | 절감 |
|--------|----------|-----------------|------|
| power-spin F/S | 24267 / 25432 | 30942 / 35533 | −6.7s / −10.1s |
| peter-pan F/S | 18491 / 21900 | 28126 / 27947 | −9.6s / −6.0s |
| elbow-twist-sister F/S | 34126 / 36010 | 38855 / 45037 | −4.7s / −9.0s |
| pdshape F/S | 33460 / 31579 | 48574 / 38063 | −15.1s / −6.5s |
| kip-up F/S | 20057 / 20358 | 27953 / 35397 | −7.9s / −15.0s |

**recognizer 단계 절감: median 8.46s / mean 9.08s / range 4.7~15.1s** (분석당). 양쪽 모두 wave 3~6 최적화 이전 코드(업로드 중복 포함)의 수치 — 27-09 배포 후에는 업로드 겹치기와 중첩되므로 실효 절감은 재실측 필요.

## 반영 제약 — 채택인데 왜 env 반영을 보류하나

plan의 반영 절차(start_server.sh에 `GEMINI_MODEL` export 한 줄)는 교정 2 때문에 **veto까지 Flash로 바꾼다** — belle 승인 범위(1순위만)와 D-05(veto 기본 보류, 점수 직결)를 동시에 위반. import 순서 wrapper를 프로덕션 서버 기동에 심는 것은 env 한 줄이 아니라 기동 방식 변경이라 범위 초과로 판단.

**권고 반영 경로 (후속, 27-09 또는 별도 1줄 플랜):** `gemini_moment_extractor.py:58`에 전용 env 키(예: `GEMINI_MOMENT_MODEL`, 미설정 시 기존 `GEMINI_MODEL` fallback) 1줄 추가 → start_server.sh에 `export GEMINI_MOMENT_MODEL=gemini-3.5-flash`. 단 27-09의 after-sweep EVAL18 게이트와 같은 사이클로 검증할 것(이번 등가 증명은 6eb73b5 코드 기준).

## Pod env 종료 상태 (원상 증빙)

- `start_server.sh`: `GEMINI_MODEL` 라인 0건 — **변경 이력 자체가 없음** (실험은 별도 프로세스 env로만 수행, diff 0).
- 라이브 uvicorn(PID 9108, 23:55 기동 그대로 — 재시작 없음): 프로세스 env에 `GEMINI_MODEL` 없음 → 프로덕션 extractor는 기존 기본 모델 유지.
- `/health` 200 (`{"status":"ok","auth_configured":true,"pipeline_loaded":true}`), repo `6eb73b5` clean.

## 캐시 오염 0 — 근거 교정 + 운영적 완화 (T-27-25)

plan 전제 "TechniqueCache 키에 model명 포함 → 자동 네임스페이스 분리"는 부정확: Firestore doc id는 video_hash뿐이고, `model` 필드는 recognizer가 **상수 문자열**(`gemini_technique_recognizer.py:220` `"gemini-3.1-pro"`, `technique_cache.py:195` 동일 상수)로 store — 실제 사용 모델을 반영하지 않는다. 즉 Flash 산출 moments가 Pro run의 lookup에 hit될 수 있는 구조.

완화(실행함): **sweep 종료 후 fixture 12개 hash 한정 gemini_cache 22건 재삭제 → 잔존 0** (`/workspace/eval_out/phase27/flash_cache_restore_{delete,verify}.json`). 프로덕션 사용자 영상은 hash가 달라 원천 무접촉 — 오염 표면은 fixture eval 한정이었고 그마저 제거 완료. 전용 env 키 반영 시 이 상수 라벨도 실모델 문자열로 함께 고치는 것을 권고.

## 원자료

- Pod: `/workspace/eval_out_flash27/phase25/phase25_sweep_report.json` + `phase25_breakdowns.json`, `/workspace/eval_out/phase27/flash_sweep.log`, `/workspace/eval_out/phase27/flash_cache_{isolate,restore}_{delete,verify}.json`, wrapper `/workspace/phase27_flash_moment_sweep.py`
- 대조 기준: `/workspace/eval_out/phase25/phase25_sweep_report.json` (wave 2 Pro run, 27-TIMING-BEFORE) + `backend/evals/phase18/baseline/eval18_serial_baseline.json` (정본)
