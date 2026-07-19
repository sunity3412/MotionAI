---
phase: 31-api-visual-correction
plan: 04
subsystem: contract
tags: [contract, types, docs, visual-correction]
requires: []
provides:
  - correctedPose*/rotation* optional 계약 필드 (TS 측)
  - FaultZoomComparison 뷰어 프레임 소스 3필드
  - POST /visual/rotation 계약 절
  - POST /playback-url asset 확장 계약 절
affects:
  - 31-02 (Python 측 VISUAL_STATUSES — 동시 진행, 본 명세가 단일 기준)
  - 31-03 (userFrameIdx/refFrameIdx/refMatched 방출)
  - 31-08 / 31-11 (앱 소비)
  - 31-09 / 31-10 (backend 방출 + 엔드포인트 구현)
tech-stack:
  added: []
  patterns:
    - faultZoomStatus 사후 분리 패턴 mirror (optional scalar + 부재=legacy)
    - normalize 방어 파싱 (화이트리스트 + prefix 검증 + typeof)
key-files:
  created: []
  modified:
    - app/src/types/analysis.ts
    - app/src/lib/userAnalyses.ts
    - docs/contract.md
decisions:
  - "URL 은 계약에 없음 — 표시 URL 은 playback-url asset 재서명으로만 (리뷰 H-02)"
  - "pending 타임아웃 기준은 전용 *UpdatedAtMs (공용 updatedAt 아님 — 리뷰 H-06)"
  - "daily_limit = 사용자 3건/일 + 전역 30건/일, KST 자정 리셋 (리뷰 M-06)"
  - "명칭은 correctedPose (실루엣 아님 — 리뷰 L-02)"
metrics:
  duration: ~25m
  tasks: 2
  files: 3
  completed: 2026-07-20
---

# Phase 31 Plan 04: 계약 3면 TS/문서 측 확정 Summary

교정 시각물(correctedPose/rotation) 계약을 URL 비저장·전용 timestamp 원칙 위에 TS 타입 + 앱 방어 파싱 + contract.md 3절로 확정해, backend 방출(31-09/31-10)과 앱 소비(31-08/31-11)가 서로를 기다리지 않고 병렬 진행할 수 있는 단일 기준을 만들었다.

## What Was Built

### Task 1 — analysis.ts 필드 + userAnalyses.ts normalize (`57cea6b`)

`AnalysisResult` 에 optional 7필드 추가 (전부 flat scalar, 부재=legacy 숨김):
- `correctedPoseStatus` / `correctedPoseKey` / `correctedPoseJoint` / `correctedPoseUpdatedAtMs`
- `rotationStatus` / `rotationVideoKey` / `rotationUpdatedAtMs`

`FaultZoomComparison` 에 `userFrameIdx?` / `refFrameIdx?` / `refMatched?` 추가 — 2D 비교 뷰어가 좌표를 직접 렌더하므로 crop PNG 와 달리 프레임 인덱스가 필요. 주석에 9fps angles 도메인임을 명시(18fps 업샘플 공간과 혼동 방지 — §11 fps 도메인 선례).

주석은 `faultZoomStatus` 형식을 따라 값 의미 / 부재=legacy / URL 비저장(H-02) / 전용 timestamp(H-06) / Python lockstep 대상을 전부 기술.

`normalize()` 방어 파싱 (T-31-12 Tampering mitigate):
- status 2종 — 3값 literal 화이트리스트만 통과, 그 외 `undefined` (알 수 없는 상태는 표시하느니 숨김, D-08)
- key 2종 — `results/` prefix 아니면 `undefined` 로 조용히 강등
- `*UpdatedAtMs` — `Number.isFinite` (NaN/Infinity 는 비교 시 영구 pending 유발)
- 프레임 인덱스 2종 — `Number.isInteger && >= 0`, `refMatched` — `typeof boolean`

필드 부재 시 `undefined` 유지 — drop 하지 않는다.

### Task 2 — contract.md 3절 (`04915bd`)

1. **visual 교정 시각물 필드 절** — 7필드 + FaultZoomComparison 확장 3필드 정의, 자동(D-05) vs 온디맨드(D-06) 생성 시점 차이, URL 비저장 원칙과 그 이유(죽은 URL + 임의 key 서명 여지), 점수 비반영 invariant, `visualJobs`/`quotaDateKey` 를 앱 비노출 내부 구현 노트로 기술.
2. **POST /visual/rotation 절** — 202/200/401/400/404/429/503 전부. 404 는 존재·소유·상태 가드 합산 단일 응답(leak 0), 200 에도 URL 미포함, `daily_limit` 은 KST 자정 리셋 근거(파일럿 사용자 전원 한국 → UTC 자정은 한국 오전 9시 리셋)까지 명시.
3. **POST /playback-url asset 확장 절** — `asset?: 'correctedPose' | 'rotation'`, server-selected key + prefix 정확 검증 + 1시간 presign, 미지정 시 기존 동작 100% 보존.

파일 관례에 따라 하단 변경 이력 한 줄 추가.

## Key Decisions

- **URL 필드를 계약에 두지 않음** — 문서에 presigned URL 을 박제하면 TTL 만료 후 죽은 URL 이 남고 클라이언트가 임의 key 를 서명시킬 여지가 생긴다. key 만 저장하고 서버가 asset 종류로 key 를 선택.
- **전용 `*UpdatedAtMs`** — 공용 `updatedAt` 은 무관한 write 로도 갱신돼 pending 수명을 잘못 늘린다.
- **`failed` 와 부재를 앱에서 동일 처리** — 모더레이션 차단(~10%)을 에러로 노출하지 않는 조용한 폴백(D-08).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] worktree 가 예상 base 가 아닌 조상 커밋에 위치**

- **Found during:** 실행 시작 (worktree_branch_check)
- **Issue:** worktree HEAD 가 `c8dd21c` (47c1d77 의 조상)여서 phase 31 플랜 파일이 존재하지 않았다 — 31-04-PLAN.md 를 읽을 수 없음.
- **Fix:** branch-check 프로토콜이 규정한 `git reset --hard 47c1d77` 수행 (working tree clean 상태라 손실 없음).
- **Files modified:** 없음 (worktree 상태만)

**2. [Rule 3 - Blocking] worktree 에 node_modules 부재로 typecheck 불가**

- **Found during:** Task 1 verify
- **Issue:** `npm run typecheck` 가 `sh: tsc: command not found` 로 실패 — worktree 에 `node_modules` 가 없다.
- **Fix:** 메인 repo 의 `app/node_modules` 를 심볼릭 링크로 연결해 typecheck 실행 후 **즉시 제거**. 신규 패키지 설치는 없음(기존 의존성 재사용). `app/.gitignore` 의 `node_modules/` 는 trailing slash 라 심볼릭 링크에는 매칭되지 않아 `?? node_modules` 로 노출됐고, 커밋 전에 제거해 worktree 를 clean 상태로 되돌렸다.
- **Files modified:** 없음 (커밋된 변경 없음)

> 후속 실행자 참고: 이 worktree 패턴에서 앱 typecheck 가 필요하면 동일 조치가 필요하며, 심볼릭 링크는 **커밋 전 반드시 제거**해야 한다.

## Verification

- `cd app && npm run typecheck` → exit 0 (심볼릭 링크 연결 상태에서 실행 확인)
- `grep -q daily_limit && grep -q feature_disabled && grep -q correctedPose docs/contract.md` → PASS
- `correctedPoseStatus` 3면 존재 확인 — analysis.ts(1) / userAnalyses.ts(1) / contract.md(2)
- 응답 코드 7종(202/200/401/400/404/429/503) contract.md 존재 확인
- 신규 `*Url` 필드 0 확인 (`correctedPoseUrl|rotationUrl|rotationVideoUrl` 매치 없음)

## Scope Notes

Python 측(`backend/shared/python/sunity_shared/models.py`)은 31-02 가 동시 진행 — 본 플랜에서 Python 파일은 **전혀 건드리지 않았다**. objective 에 박제된 필드명 명세를 그대로 구현했으며 임의 개명/추가 없음.

STATE.md / ROADMAP.md 미수정 (오케스트레이터 소유).

## Self-Check: PASSED

- FOUND: app/src/types/analysis.ts
- FOUND: app/src/lib/userAnalyses.ts
- FOUND: docs/contract.md
- FOUND: 57cea6b
- FOUND: 04915bd
