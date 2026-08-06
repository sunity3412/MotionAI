---
phase: quick-260806-usc
plan: 01
subsystem: app-video-compare
tags: [playback, invariant, voice-cue, V-1, D-13]
requires:
  - app/src/components/VideoCompare.tsx (33-13 A-6 음성 큐 정지/재개 상태머신)
  - app/src/lib/manualOffset.ts (순수 함수 + node --test 관례)
provides:
  - decidePlaybackInvariant (재생 편측 판정 순수 함수)
  - RESUME_WATCH_TICKS / RESUME_PLAY_RETRIES (관찰창·재시도 상한)
affects:
  - 동작비교 탭 재생 제어 (tick 100ms)
tech-stack:
  added: []
  patterns: [순수판정+호출부집행 분리, 관찰창(bounded watch window), 재시도 상한 후 대칭 수렴]
key-files:
  created:
    - app/src/lib/playbackInvariant.ts
    - app/src/lib/__tests__/playbackInvariant.test.ts
  modified:
    - app/src/components/VideoCompare.tsx
decisions:
  - "V-1 원인 미규명 상태에서 결과 상태 수렴 수리를 택함 (시뮬 미재현 — 원인 추측 수리 금지)"
  - "재시도 3회(≈300ms) 초과 시 converge-pause — 어긋난 채 진행보다 대칭 정지 우선(정렬 보존)"
  - "관찰창은 재개 후 1초(10 tick)만 — 상시 감시는 정상 주행 개입 위험"
metrics:
  duration: ~35m
  completed: 2026-08-06
  tasks: 2
  commits: 3
  files_created: 2
  files_modified: 1
---

# quick-260806-usc: V-1 재생상태 편측 불일치 차단 Summary

동작비교의 재생 상태가 편측으로 갈라지는 것을 100ms tick 마다 감시·집행하는 순수 판정 함수(12축 테스트)와 VideoCompare tick 안 집행 블록을 넣었다 — 신규 타이머 0, 기존 줄 수정 0.

## 무엇을 했나

**Task 1 (TDD).** `app/src/lib/playbackInvariant.ts` — `decidePlaybackInvariant` 순수 함수 1개 + 타입 3개 + 상수 2개(`RESUME_WATCH_TICKS=10`, `RESUME_PLAY_RETRIES=3`). 판정 규칙 R1~R8 을 코드 순서로 그대로 배치해 읽는 사람이 우선순위를 코드에서 본다. RED(`3338b2b2`) → GREEN(`a3c14983`).

**Task 2 (배선).** `VideoCompare.tsx` tick 안에 집행 블록 1개 + 관찰창 ref 2개 + 제스처 4곳 창 닫기 (`d70355a4`). 집행 블록은 `followTick` 산출 직후 · follow/drift `if` 앞에 둔다 — 시작 홀드 판정에 `followTick` 이 필요하고, 집행 후 조기 return 이 stale `leftPlaying` 으로 도는 follow/drift 블록보다 앞서야 F-2(33-16)와 같은 mid-tick 레이스를 다시 만들지 않는다.

## 검증 (무엇을 어떻게 성립시켰나)

| 항목 | 어떻게 | 결과 |
|---|---|---|
| 불변식 12축 | `node --test .../playbackInvariant.test.ts` **돌려봤다** | 12 pass / 0 fail |
| typecheck | `npm --prefix app run typecheck` **돌려봤다** | GREEN(무출력), 기준선과 동일 |
| 기존 테스트 무회귀 | manualOffset / cueTrack **돌려봤다** | 6 pass / 7 pass (착수 전 기준선과 동일) |
| 순수성 | `grep -c "from 'react'\|expo-video\|setTimeout\|setInterval"` **재봤다** | 0건 |
| 집행 블록 배치 | 두 줄 번호 **재봤다** | call 800행 < rawComposedRef 849행 = PASS |
| 타이머 1개 유지 | `grep -c 'setInterval('` **재봤다** | 1 |
| 관찰창 생명주기 | `grep -c` **재봤다** | 닫기 5곳(제스처 4 + closeWatch 1) / 열기 1곳 |
| 기존 줄 무수정 | `git diff -U0 \| grep -c '^-[^-]'` **재봤다** | 0 (79 insertions, 0 deletions = 추가만) |

착수 전 기준선을 먼저 찍고(typecheck GREEN / 6 / 7) 착수 후 같은 명령으로 대조했다.

## 정직 박제 (honesty_gate)

- **실기기 실효 = UNVERIFIED.** 시뮬(iOS 26.5, 개발빌드 #29)에서 원 결함 V-1 이 재현되지 않는다(큐1 4.1/4.2 동시 정지 → 종료 후 양쪽 재개 → 큐2 6.7/6.7 → 최종 13.3/13.5 동기 주행 = 상태머신은 이상 조건에서 옳다). 따라서 시뮬 확인으로 증명되는 것은 **회귀 없음**뿐이다. **"V-1 이 고쳐졌다"고 말할 수 없다.** 현재 상태 = "불변식 감시를 넣었다 / 실효 미확인".
- **원인 미규명.** 이 수리는 원인(재버퍼 스톨 / mid-tick 레이스 / play() 무실효)을 가리지 않는다. 결과 상태를 수렴시킬 뿐이다. 원인 후보를 확정된 것처럼 쓰지 말 것(F-6 원칙).
- **converge-pause 는 트레이드오프다.** 느린 네트워크에서 재개가 300ms 를 넘으면 양쪽이 멈춘 채 사용자 조작을 기다린다 — 의도된 동작이다. belle 이 "음성 끝나면 자꾸 멈춘다"고 보고하면 조정 지점은 `RESUME_PLAY_RETRIES` / `RESUME_WATCH_TICKS` **상향**이다.
- **오케스트레이터 시뮬 확인 미실행(실행자 범위 밖).** 실행자에겐 시뮬 도구가 없다. (a)~(f) 항목은 오케스트레이터 몫으로 남는다.

**belle 실기기 확인 항목** — V-1 재현 doc(엘보)에서:
① 음성 종료 후 내 영상이 도는가 → ② 안 돌면 **양쪽이 같이 멈춰 있는가**(=집행 성공, 정렬 보존) → ③ 재생 버튼으로 다시 도는가.
②가 성립하면 편측 이탈은 차단된 것이고, 남은 문제는 재개 실효(별건)로 좁혀진다.

## 설계 판단 (왜 이렇게)

- **R5 가 "양쪽 정지"를 정상으로 본다.** play() 직후 두 플레이어가 spin-up 중이면 false/false 가 한두 tick 관측된다. 이걸 위반으로 세면 재개마다 재시도를 소진하고 converge-pause 로 수렴해 버린다. 위반은 "갈라진 것"이지 "안 도는 것"이 아니다.
- **R6 시작 홀드 면제는 단방향.** follow 블록이 정은지(right) 재생/정지를 소유하고(32-08 피드백 #1), 목표시각 음수 구간의 right 정지는 **의도된** 편측이다. 여기서 play() 를 쏘면 두 로직이 매 tick 싸운다. 역방향(left 정지·right 재생)은 시작 홀드로 설명되지 않으므로 면제하지 않는다.
- **관찰창 밖 무개입(R4).** D-13 이 규정하는 두 국면(음성 중 / 재개 직후)에만 개입한다. 상시 감시로 넓히면 정상 주행에 개입할 여지가 생긴다(T-usc-01).
- **시작 홀드 판정식을 재사용.** `targetRefTime(cL) < 0` — follow 블록의 `rawComposedRef` 와 같은 식. 판정 규칙을 두 벌 만들지 않는다.

## Deviations from Plan

계획대로 실행. 계획 밖 판단 2건(둘 다 문서 정확성, 동작 무관):

1. **주석의 행 번호 참조 제거** — 계획 문구는 "779행 rawComposedRef 와 같은 식"이었으나, 내 추가분이 그 줄을 849행으로 밀었다. 행 번호를 박으면 즉시 거짓이 되므로 식 자체(`targetRefTime(cL) < 0`)를 인용하도록 고쳤다.
2. **오타 1건 자체 발견·수정** — 오프셋 제스처 주석에 키릴 문자가 섞였다("제스ченder"). 즉시 고치고 touched 파일 3개 전체를 `grep -P '[\x{0400}-\x{04FF}]'` 로 재스캔(0건 확인).

## Known Stubs

없음. 이 계획의 산출물은 전부 실동작 배선이다(판정 함수 → tick 집행 → 제스처 생명주기).

## 범위 밖 (고의)

V-2(시작 직후 발화)·V-3(목록 미확보)·EAS OTA·실기기 확인·V-1 원인 규명.

## Self-Check: PASSED

- `app/src/lib/playbackInvariant.ts` FOUND
- `app/src/lib/__tests__/playbackInvariant.test.ts` FOUND
- `app/src/components/VideoCompare.tsx` FOUND (modified, 79 insertions / 0 deletions)
- 커밋 `3338b2b2` / `a3c14983` / `d70355a4` 전부 `git log` 에서 확인
