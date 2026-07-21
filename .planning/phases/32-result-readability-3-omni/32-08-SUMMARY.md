---
phase: 32-result-readability-3-omni
plan: 08
subsystem: ui
tags: [expo-video, react-native, cue-track, video-compare, tts, polly, gemini-image, sample-gate]

# Dependency graph
requires:
  - phase: 32-02
    provides: VideoCompare manualOffset/followActive 로직 (음수 오프셋 버그의 진원 + 수정 대상)
  - phase: 32-05
    provides: 승인 문구집(phrasebook.json cueLine) — 큐 자막·TTS 샘플 문장 원천
  - phase: 32-03
    provides: D-17 실물 게이트 확정(재생 중 큐 밀도 = 결함 구간당 1개)
provides:
  - cueTrack 순수 함수(buildCueWindows/activeCue) — 결함 프레임 인덱스 → 큐 윈도우 (recordId 조인)
  - VideoCompare 재생 중 자막 큐 오버레이(opt-in cueWindows prop) + 음수 오프셋 재시작 루프 수정 + "적용중" 표시
  - 샘플 게이트 재료(TTS 2종 + 일러스트 3안 + provenance) + belle D-18/D-21 확정 적재
  - 32-16-PLAN.md (B안 백엔드 TTS 물리 분리 — wave 7)
affects: [32-11, 32-12, 32-16]

# Tech tracking
tech-stack:
  added: []  # 신규 npm/pip 의존성 0 (샘플은 CLI/API로 오프라인 제작)
  patterns:
    - "cue-window 순수 함수 + 기존 tick 재사용 (신규 타이머 0)"
    - "음수 오프셋 시작 홀드 (0-클램프 seek 루프 대신 pause+resume)"
    - "샘플 게이트 provenance (생성 도구·프롬프트·사용권·likeness 회피 기록)"

key-files:
  created:
    - app/src/lib/cueTrack.ts
    - app/src/lib/__tests__/cueTrack.test.ts
    - .planning/phases/32-result-readability-3-omni/samples/ (TTS 2 + 일러스트 3 + gallery + README)
    - .planning/phases/32-result-readability-3-omni/32-16-PLAN.md
  modified:
    - app/src/components/VideoCompare.tsx
    - .planning/phases/32-result-readability-3-omni/32-GATE-DECISIONS.md

key-decisions:
  - "오디오(D-18) = B안 클라우드 TTS(AWS Polly neural) — belle 확정, 최종 음성은 32-16 구현 시 belle 청취 확정"
  - "일러스트(D-21) = 도입, 2안 준실사 스타일 — belle 확정('셋다 너무 멋진디'), 1안 다리 3개 해부학 오류 지적"
  - "신규 품질 게이트: AI 일러스트 해부학 검수 + belle 최종 승인 필수 (32-12 acceptance 반영 기록)"
  - "음수 오프셋 재시작 루프 = 목표 0-클램프 seek 루프 — hold(pause+0)/resume 로 수정 (실기기 피드백 #1)"

patterns-established:
  - "cueTrack: 프레임→초 환산은 fps 인자로만(9/18 하드코딩 금지), react/player 의존 0 순수 함수 + node --test"
  - "VideoCompare opt-in prop(cueWindows/busyLabel): 미전달 시 기존 렌더 diff 0"
  - "checkpoint:decision(blocking) — 배경 executor는 샘플 전량 커밋 후 report 반환, 오케스트레이터 relay"

requirements-completed: [D-18, D-21, D-09]  # D-18/D-21 = 게이트 확정 + D-18 자막 절반 (오디오·일러스트 구현은 32-12/32-16)

# Metrics
duration: ~32min (샘플 제작 + 체크포인트 relay 포함)
completed: 2026-07-21
---

# Phase 32 Plan 08: 재생 중 자막 큐 + 샘플 게이트 Summary

**cueTrack 순수 함수 + VideoCompare 자막 큐 오버레이·음수 오프셋 재시작 루프 수정, 그리고 belle 샘플 게이트 확정(오디오 B안 Polly / 일러스트 2안 도입)과 B안 백엔드 분리(32-16) 생성**

## Performance

- **Duration:** ~32 min (샘플 제작 + belle 체크포인트 relay 포함)
- **Started:** 2026-07-21T12:08:05Z
- **Completed:** 2026-07-21T12:40:00Z
- **Tasks:** 3 (Task 1 TDD 다중 커밋 + Task 2 + Task 3 체크포인트)
- **Files modified:** 12 (10 created, 2 modified)

## Accomplishments

- **cueTrack.ts 순수 함수** — `buildCueWindows`(결함 프레임 인덱스 → [startSec,endSec) 큐 윈도우, fps 인자·recordId 승계·D-17 밀도 제한) + `activeCue`(재생 시각 → 현재 큐 1개/null, 겹침 시 시작 늦은 큐 우선). node --test 7/7 pass, react/player 의존 0.
- **VideoCompare 자막 큐 오버레이** — 기존 tick(100ms)에서 activeCue 판정 → 하단 자막 pill(opt-in cueWindows prop, 미전달 시 diff 0). 수치 미포함(D-09), recordId 조인 가능(fault zoom·오디오 안정 키). 신규 타이머 0.
- **실기기 피드백 #1 수정** — 슬라이더 − 방향 "정은지 재시작 루프": 목표시각이 음수인 구간에서 매 tick `seek(0)` 하던 것을, 그 구간엔 정은지(right)를 pause+0 홀드하고 학생이 |offset| 지나면 resume. legacy 경로 byte-보존.
- **실기기 피드백 #2** — 오프셋 적용 중 정은지 슬롯에 "적용중입니다" 오버레이(디바운스 setTimeout).
- **샘플 게이트 재료** — TTS A안 참고 녹음(비대표)+실기기 절차 / B안 Polly mp3 / 일러스트 3안(gemini-3-pro-image ×2, gemini-3.1-flash-image ×1, 익명·형태감·likeness 회피) + gallery + provenance README.
- **belle 확정 적재 + 32-16 분리** — 오디오 B안, 일러스트 2안 도입, 해부학 검수 게이트 신설 기록. B안 백엔드 TTS(32-12 Task 2)를 32-16-PLAN.md(wave 7)로 물리 분리.

## Task Commits

1. **Task 1a (RED): cueTrack 실패 테스트** - `b633169` (test)
2. **Task 1b (GREEN): cueTrack 순수 함수** - `3c0af19` (feat)
3. **Task 1c: 음수 오프셋 수정 + 적용중 표시** - `a60b8ce` (fix)
4. **Task 1d: 재생 중 자막 큐 오버레이** - `5493451` (feat)
5. **Task 2: 샘플 게이트 재료** - `4176f10` (docs)
6. **Task 3a: 샘플 게이트 제출 기록** - `fdaa155` (docs)
7. **Task 3b: belle 확정 적재 + 32-16 분리** - `2cd0855` (docs)

**Plan metadata:** 이 SUMMARY 커밋 (docs)

_TDD: Task 1 은 test(RED) → feat(GREEN) → fix/feat 순 다중 커밋._

## Files Created/Modified

- `app/src/lib/cueTrack.ts` - 큐 윈도우 산출 순수 함수(buildCueWindows/activeCue)
- `app/src/lib/__tests__/cueTrack.test.ts` - node --test 7케이스(산식·겹침·밀도·크래시 0)
- `app/src/components/VideoCompare.tsx` - 자막 큐 오버레이 + 음수 오프셋 홀드/resume + "적용중" 표시
- `.planning/phases/32-result-readability-3-omni/samples/` - TTS 2종·일러스트 3안·gallery·README(provenance)
- `.planning/phases/32-result-readability-3-omni/32-GATE-DECISIONS.md` - 샘플 게이트 확정(D-18 B안 / D-21 2안 도입 / 해부학 게이트)
- `.planning/phases/32-result-readability-3-omni/32-16-PLAN.md` - B안 백엔드 TTS 물리 분리 플랜(wave 7)

## Decisions Made

- **오디오(D-18) = B안 (Polly neural).** belle "억양·자연스러움 + 전 사용자 동일 음질" 이유로 확정. 최종 음성은 32-16 구현 시 belle 청취 확정(부속).
- **일러스트(D-21) = 도입, 2안 준실사.** belle "셋다 너무 멋진디, 상상이상"; 1안에서 다리 3개 해부학 오류 지적.
- **★신규 품질 게이트:** AI 일러스트 해부학 검수 + belle 최종 승인 필수 — 무검수 자동 반영 금지. 32-12 일러스트 acceptance 에 반영(GATE-DECISIONS 단일 출처, 32-12-PLAN.md 미수정).
- **W-2 분리:** 32-12 Task 2(백엔드 TTS)를 32-16 으로 물리 분리 — 파일 소유권 충돌 방지 위해 32-12 본문 미수정, 32-12 executor 가 GATE-DECISIONS 읽고 skip.
- **큐 밀도 파라미터화:** D-17 "구간당 1개"는 activeCue 가 큐 1개만 반환하는 것으로, maxCues 는 전체 상한(감점 큰 순)으로 분리 구현.

## Deviations from Plan

None - plan executed exactly as written. (Task 3 checkpoint 은 belle 확정 후 정상 완결 — 오디오 B / 일러스트 2안 도입 / 해부학 게이트 신설 + 32-16 분리.)

**참고 — 계획 대비 도구 제약 대응(deviation 아님, 계획 내 허용 경로):** 배경 executor 는 MCP 이미지 생성 도구가 stripped(anthropics/claude-code#13898)이라, 플랜이 지정한 "사용 가능한 생성 MCP" 대신 **Gemini 이미지 API(REST via curl, SSM 키)** 로 일러스트를 생성했다. 결과물 품질·익명·likeness 회피 기준은 동일하게 충족(belle 도입 확정). TTS 는 플랜 명시대로 macOS say(A 참고) + AWS Polly CLI(B).

## Issues Encountered

- **일러스트 확장자:** Gemini 이미지 모델이 mime `image/jpeg` 로 반환 → `.jpg` 로 정확히 명명(플랜의 "PNG/HTML"은 `illust_gallery.html` 로도 충족). 뷰어 열람·품질 판정에 영향 없음.
- **worktree typecheck:** worktree 에 node_modules 부재 → main node_modules 임시 symlink(gitignored)로 tsc 실행 후 제거(32-06 선례, 커밋 0). 최종 tree clean.

## User Setup Required

None - 이 플랜은 외부 서비스 설정 불요. (B안 오디오의 SAM/Pod 배포·belle 음성 확정은 32-16 소관.)

## Next Phase Readiness

- **32-11 (배선):** cueTrack.buildCueWindows 로 records(cueLine=text, recordId) → cueWindows 산출해 VideoCompare 에 주입하면 자막 큐 활성. result.tsx fps 환산 정본(:2130) 사용, cueLine 부재 legacy 는 buildDeductionMarkers 폴백.
- **32-12 (구현):** 오디오 B안(audioCue.ts B-branch, expo-audio) + 일러스트 2안 도입(app/assets/illustrations/ 정적 번들, **해부학 검수+belle 승인 게이트 필수** — GATE-DECISIONS 기록 반영). Task 2 는 '32-16 에서 수행'으로 skip.
- **32-16 (신설, wave 7):** B안 백엔드 Polly 합성 스테이지+playback asset+SAM/Pod 배포+6동작 스윕. 32-12 오디오 배선의 백엔드 선행 — 32-12 오디오보다 먼저 실행 필요.
- **주의:** STATE.md/ROADMAP.md 는 오케스트레이터 소유(이 플랜 미접촉). result.tsx·shared artifacts 무접촉 확인됨.

## Self-Check: PASSED

- 생성 파일 8/8 확인 (cueTrack.ts·test·VideoCompare·samples·32-16-PLAN·SUMMARY 등)
- 커밋 7/7 확인 (b633169·3c0af19·a60b8ce·5493451·4176f10·fdaa155·2cd0855)
- node --test cueTrack 7/7 pass · npm run typecheck clean · setInterval 개수 base=4 동일
- result.tsx 무접촉 · STATE/ROADMAP/phrasebook/analysis.ts/theme 무접촉 · working tree clean

---
*Phase: 32-result-readability-3-omni*
*Completed: 2026-07-21*
