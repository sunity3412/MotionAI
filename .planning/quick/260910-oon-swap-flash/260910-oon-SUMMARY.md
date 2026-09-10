---
id: 260910-oon
title: 관절선 토글 0초 깜빡임 제거
date: 2026-09-10
status: executed
commit: 1d313fc5
---

# 관절선 토글 0초 깜빡임 — 로딩 창 심기 (실행 결과)

**한 줄**: 소스 교체의 로딩 창 안에서 `player.currentTime` 을 1회 최선 노력으로 심어,
새 AVPlayerItem 이 꽂히는 그 순간에 이미 목표 위치에 서 있게 했다. 기존 절차는
한 줄도 바꾸지 않았다.

## 바뀐 줄 (1 파일, +37 / -0)

`app/src/components/RenderedComparePlayer.tsx` 만 건드렸다.

1. **import (:77)** — `clampSeekTarget` 을 `../lib/sourceSwapSeek` import 목록에 추가.
   새 클램프를 만들지 않았다. 기존 seek 이 쓰는 그 함수를 그대로 통과시킨다.

2. **지역 플래그 (:288-291)** — 토글 effect 안에 `let preSeeded = false;` 추가
   (`loadedDurationSec` 바로 아래). 세대(epoch) 스코프라 교체 1회당 1개다.

3. **`statusChange` 리스너 본문 (:419-450)** — 기존 `signalStatus = status; step();`
   **앞에** 심기 가지를 덧댔다:

   ```ts
   if (status === 'loading' && !preSeeded && alive()) {
     preSeeded = true;
     try {
       player.currentTime = clampSeekTarget(targetSec, loadedDurationSec);
     } catch {
       // 해제 직후 등 — 심기만 포기한다. 아래 절차는 그대로 간다.
     }
   }
   ```

   위에 네이티브 근거 주석(파일:줄 인용)을 붙였다 —
   `ios/VideoPlayer.swift:264` (main 큐 `replaceCurrentItem` 이 t=0 그림을 시작시킨다),
   `DangerousPropertiesStore.swift:1-2` 와 `ios/VideoPlayer.swift:49-53`, `:264-266`
   (로딩 중 대입이 담겼다가 교체 바로 다음 줄에서 적용된다),
   `ios/VideoPlayer.swift:242` (`ownerIsReplacing` 이 Swift Task 안에서 세팅되므로
   `replaceAsync` 호출 직후 대입은 창 **앞**에 떨어질 수 있다 → 그래서 `'loading'`).

`sourceSwapSeek.ts` · `VideoCompare.tsx` · 백엔드 · 계약 파일은 **무접촉**
(`git show --stat` = `RenderedComparePlayer.tsx` 1개, 삭제 0).

## 커밋

```
1d313fc52c8622fedf97e9070e8a88c423e2d544  (1d313fc5)
fix(quick-260910-oon): 관절선 토글 로딩 창에 재생 위치를 미리 심는다
1 file changed, 37 insertions(+)
```

단일 원자 커밋 1개. 이 SUMMARY 는 커밋하지 않았다(디렉터리 전체가 untracked).

## 실제 검증 숫자

| 항목 | 기준선 (변경 전, 이번에 직접 실행) | 변경 후 |
| --- | --- | --- |
| `npm run typecheck` (`tsc --noEmit`) | 오류 0 (exit 0) | **오류 0 (exit 0)** |
| `node --test $(find src -path '*__tests__*' -name '*.test.ts')` | tests 241 / pass 241 / fail 0 | **tests 241 / pass 241 / fail 0** |

두 수치 모두 변경 전후를 이번 세션에서 각각 돌려 얻은 값이다(인용이 아니다).
줄어든 것 없음.

## 왜 이 변경이 기존 절차를 안 깨는가

이 심기는 **판정에 들어가지 않는 부수효과**다. 절차의 상태 기계는 여전히
`signalStatus` 와 `step()` 이 전부 굴리고, 심기 가지는 그 두 줄 **앞에서** 값 하나를
대입하고 지나갈 뿐 `phase` · `attempts` · `observedSec` · `loadedDurationSec` 중
어느 것도 건드리지 않는다. 그래서 ready 대기 → seek → 되읽어 검증 → 재시도 → play
순서는 belle 이 실기기에서 통과시킨 모습 그대로 남아 있고, 심기가 먹든 안 먹든
**위치의 최종 책임은 여전히 그 절차에 있다** — 심기가 성공하면 아래 seek 은 이미
맞은 위치를 한 번 더 확인하는 셈이고(검증 오차 0.35s 안이므로 재시도도 안 난다),
실패하거나 창을 놓치면 종전과 똑같은 경로가 그대로 고쳐 준다. 실패 경로도 닫아
뒀다: `try/catch` 로 예외를 삼키고, `alive()` 로 옛 세대의 늦은 `'loading'` 이 새
교체를 되감지 못하게 막고, `preSeeded` 로 창이 닫힌 뒤의 두 번째 `'loading'` 대입이
실제 seek 가 되어 절차의 seek 와 겹치는 것을 막는다. 목표값도 새 규칙을 만들지 않고
기존 `clampSeekTarget` 을 통과시켜 NaN/음수가 네이티브로 새지 않으며(duration 을
아직 모르는 창이라 대개 원값 그대로 나가고 상한은 AVPlayer 가 자른다), `playbackRate`
재적용·새 의존성·듀얼 경로 접촉은 0 이다.

## 검증의 한계 (PLAN §검증의 한계 승계)

`tsc` 와 `node --test` 는 **화면을 못 본다.** 이 수리의 대상이 정확히 "화면에 무엇이
그려지는가" 라서, 위 241 pass / 오류 0 은 **고쳐졌다는 증거가 아니다.** 시뮬레이터
프레임 단위 확인은 이번에도 하지 않았다(녹화 도구와 조작 도구 충돌 — PLAN 기록 승계).
네이티브 근거는 `expo-video` 3.0.16 소스 읽기로 확정했지만, "로딩 창 대입이 iOS
실기기에서 실제로 첫 그림을 그 위치로 만드는가" 는 AVFoundation 런타임 사실이라
여기서 증명할 수 없다.

**따라서 "됐다" 가 아니라 여기까지다: 코드를 심었고 기준선을 안 깼다. 최종 판정은
belle 실기기.** 아직 OTA 로 내보내지 않았으므로 belle 이 볼 수 있는 상태도 아니다 —
배포는 별도 단계다.

## Self-Check

- `app/src/components/RenderedComparePlayer.tsx` — FOUND (수정 반영됨)
- 커밋 `1d313fc5` — FOUND (`git log -1`)
- `git show --stat 1d313fc5` = 1 file changed, 37 insertions(+), 삭제 0 — 확인
- SUMMARY 미커밋 — 확인 (`git status --short` 에 `.planning/quick/260910-oon-swap-flash/` 가 `??`)

## Self-Check: PASSED
