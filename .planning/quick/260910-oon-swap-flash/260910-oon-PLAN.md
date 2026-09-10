---
id: 260910-oon
title: 관절선 토글 0초 깜빡임 제거
date: 2026-09-10
status: planned
---

# 관절선 토글 시 영상이 0초를 한 번 스치는 것 제거

**belle 2026-09-10 실기기 확인**: 관절선 수리는 성립했다("둘다 잘 된다"). 다만
*"관절선 칩 눌렀을 떄 살짝 맨 처음으로 잠깐 0.몇 초 갔다가 돌아오긴 하지만 괜찮을 듯...
잡을 수 있음 잡으면 좋아."* → 기능 결함 아님, 체감 결함. **낮은 우선순위, 낮은 위험으로만.**

## 남은 창이 왜 생기는가 (코드 사실)

현재 절차(`RenderedComparePlayer.tsx` 토글 effect)는
pause → 리스너 등록 → `replaceAsync` → **ready 신호 대기** → seek → 검증 → play 다.

`ready 신호 대기` 는 정확했지만, 그 사이에 **새 AVPlayerItem 이 이미 화면에 꽂힌다.**
`ios/VideoPlayer.swift:264` 의 `ref.replaceCurrentItem(with: playerItem)` 이 main 큐에서 실행되는
순간 VideoView 는 새 소스를 t=0 부터 그리기 시작하고, 우리 seek 은 그보다 **뒤**에 온다.
그래서 belle 이 본 "0.몇 초 갔다가 돌아온다"가 남는다. 시간 표시는 이미 막았지만
(`swappingRef` 폴링 억제) **그림 자체**는 못 막았다.

## 처방 — 순서를 뒤집는다: 아이템이 꽂히는 그 순간에 이미 위치가 가 있게 한다

expo-video iOS 에는 이 목적의 장치가 이미 있다 —
`ios/VideoPlayer/DangerousPropertiesStore.swift:1-2`:

> "Contains player properties that have been set **while the current item was being loaded**
>  and which can be **correctly applied only after the player has set it's item**. For now it's
>  only currentTime"

`ios/VideoPlayer.swift:49-53` 의 `currentTime` setter 가 `ownerIsReplacing == true` 일 때
값을 그 store 에 넣고, `:264-266` 이 `replaceCurrentItem` **바로 다음 줄**에서 꺼내 적용한다.
즉 **로딩 창 안에서 currentTime 을 한 번 세팅해 두면, 새 아이템은 처음부터 그 위치로 꽂힌다.**

지금 코드는 그 창을 안 쓴다. ready 를 기다린 뒤에야 세팅하기 때문이다.

**★ 왜 "replaceAsync 호출 직후 곧바로 세팅"이 아니라 `statusChange('loading')` 인가**
`ownerIsReplacing = true` 는 Swift Task 안에서 세팅되고(`:242`), JS 의 currentTime setter 는
JS 스레드에서 **동기 실행**된다(`expo-modules-core` PropertyDefinition, `.runOnQueue` 없음).
둘 사이 순서 보장이 없어서 호출 직후 세팅은 창 **앞**에 떨어질 수 있다(그러면 옛 아이템을
seek 하고 교체에 지워진다 — 무해하지만 효과도 없다). `'loading'` 상태 통지는 로딩이
시작된 뒤에 나가므로 창 **안**에 있는 것이 보장된다.

## Task 1 — 로딩 창에서 위치를 미리 심는다

**files**: `app/src/components/RenderedComparePlayer.tsx`

**action**:
이미 걸려 있는 `statusChange` 리스너(약 `:412-418`) 안에서, `status === 'loading'` 일 때
**한 번만** `player.currentTime = <클램프된 목표>` 를 시도한다.

- **최선 노력(best-effort)이다.** try/catch 로 감싸고 실패해도 아무것도 바꾸지 않는다.
  이건 **기존 절차를 대체하는 것이 아니라 앞에 덧대는 것**이다. ready 대기 → seek → 검증 →
  재시도 → play 는 **그대로 둔다.** 이 심기가 먹으면 깜빡임이 사라지고, 안 먹어도 기존
  절차가 그대로 고쳐 준다.
- **한 번만.** `loading` 이 여러 번 올 수 있으므로 지역 플래그로 1회 제한.
- 세대(epoch) 가드 안에서만. 이미 있는 `alive()` 를 쓴다.
- 목표값은 기존 seek 이 쓰는 **같은 클램프 함수**를 통과시킨다 (`sourceSwapSeek.ts` 의
  `clampSeekTarget`). 새 클램프 로직을 만들지 마라. `duration` 을 아직 모르면 기존 규약대로.
- `signalStatus` / `step()` 흐름은 **건드리지 마라.** 심기는 부수효과일 뿐 판정에 안 들어간다.

**주석**: 왜 `'loading'` 시점인지(위 ★ 이유)를 네이티브 파일:줄 인용과 함께 적어라.
이 파일의 기존 한글 서술체·주석 밀도를 따를 것. 이모지 금지.

**verify**:
```bash
cd app && npm run typecheck
cd app && node --test $(find src -path '*__tests__*' -name '*.test.ts')
```
현재 기준선 = typecheck 0 / 테스트 241 pass. **줄어들면 안 된다.**

**done**: 타입체크 0, 테스트 241 이상 전건 통과, `'loading'` 심기가 1회 제한·epoch 가드·
try/catch 안에 있고 기존 절차가 무손상.

## ★ 하지 말 것

- `sourceSwapSeek.ts` 의 판정 규칙을 바꾸지 마라. 이번 변경은 **판정이 아니라 부수 심기**다.
- ready 대기·검증·재시도·play 순서를 건드리지 마라. belle 이 실기기에서 통과시킨 절차다.
- `playbackRate` 를 재적용하지 마라 (iOS didSet 이 값이 같아도 `ref.rate` 를 써서 정지 중
  재생을 시작시킨다 — `ios/VideoPlayer.swift:26-36`).
- 새 npm 의존성 0. `expo-image` 로 썸네일을 덮는 방법은 **네이티브 모듈이라 OTA 로 못 간다** —
  이번 범위 밖이고 belle 승인 사항이다.
- `VideoCompare.tsx`(듀얼 경로)·백엔드·계약 무접촉.

## 검증의 한계

`tsc` 와 `node --test` 는 **화면을 못 본다.** 이 수리의 대상이 정확히 "화면에 무엇이
그려지는가" 라서, 통과해도 **고쳐졌다는 증거가 아니다.**
시뮬레이터 프레임 단위 확인은 이번에 녹화 도구와 조작 도구가 충돌해 못 했다.
**최종 판정은 belle 실기기.** "됐다"고 보고하지 말고 "belle 이 볼 수 있게 내보냈다"까지만 적어라.
