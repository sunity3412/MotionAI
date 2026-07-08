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

*(이하 §1 배포 기록, §2 게이트 판정, §3 before/after 표는 실측 후 추가)*
