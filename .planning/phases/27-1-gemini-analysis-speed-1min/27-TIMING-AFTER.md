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

*(이하 §2 게이트 판정, §3 before/after 표는 sweep 완료 후 추가)*
