---
status: resolved
trigger: "33-16 시뮬 게이트 발견 결함 2건 — F-1: 음성 큐 종료 후 자동 재개 실패. F-2: 큐 정지 중 기준(정은지/right) 영상 계속 재생. OTA가 이 2건에 차단된 상태."
created: 2026-07-30
updated: 2026-07-30
---

## Symptoms

DATA_START
- **expected**: 33-13 A-6 시퀀스 — 재생 중 큐 시작(영상 정지 + dim + 부위 강조 + "음성 중 — 잠시 멈춤" pill + 자막) → 음성 종료(강조 해제 + **자동 재개**). 정지 중에는 좌(학생)·우(정은지) 두 player 모두 pause.
- **actual (F-1)**: 큐 발화(정지+dim+pill+강조+자막)와 음성 종료 후 강조·pill 해제까지는 정상. 그러나 영상이 3.1s 정지 상태로 영구 유지 — 자동 재개 미발화. CUE_PAUSE_MAX_MS=15000 안전 상한 강제 재개도 2분+ 관찰 동안 미발화. 수동 재생(▶ 탭)은 가능. 재생 버튼은 ▶(paused) 상태로 복귀해 있음.
- **actual (F-2)**: 큐 정지 중 좌(학생)는 3.1s에 멈췄지만 우(정은지) 영상은 계속 재생 (스크린샷 간 4.0→7.8s 진행, 끝까지 도달). 코드상 rightPlayer?.pause() 호출됨(VideoCompare.tsx ~line 655)에도 불구.
- **errors**: Metro 콘솔에 관련 에러/경고 0 (expo-video allowsFullscreen deprecation 2건뿐). 앱은 조용한 폴백 설계라 콘솔 출력 없음.
- **timeline**: 33-13(A-6)에서 신설된 기능 — 첫 실검증이 이번 33-16 시뮬 게이트. 이전에 동작한 적 있는지 불명(신규 표면).
- **reproduction**:
  1. iPhone 16 Pro 시뮬(873D7CB3-8BE4-4F74-A1C2-4E34D9BD1801) + Metro(localhost:8081, cd app && npx expo start), Debug 빌드 설치됨, main e4031d5.
  2. 시뮬 앱 익명 uid = fvcNXzEqKjgqVxRPVSj1iwFnIpn2, 기록 탭에 kipupFault1785373695 doc 복사본 존재 (coachAudio mp3 S3 복사 + doc key 동기 완료 — POST /playback-url 200 확인).
  3. 기록 → 킵업(79) → 영상 섹션 스크롤 → 음성 안내 켜짐(영속) → 재생.
  4. ~3.1s에 큐 발화(정지+dim+pill+강조) → mp3 5.57s 재생 후 강조 해제 → **영상 3.1s 정지 고착** + 재생 중 우측 패널은 계속 진행.
  - 주의: powerspinFault doc은 큐 창 3개가 같은 순간(0.2s)에 겹쳐 재생 중 전환이 원리적으로 없음 — 재현은 kipupFault(창 시작 ~3.1s)로 할 것.
- **evidence**: .planning/phases/33-result-trust-recovery/33-PHASE-GATE-EVIDENCE.md §7-2, scratchpad sim_cue_kipup.mp4 (f_30~38=정지 상태, f_39~41), sim_23_after.png(해제 후 고착), sim_24_now.png(2분 후 동일).
- **suspect code**:
  - app/src/components/VideoCompare.tsx ~line 636-691: 큐 상태머신 — speakCue started → pause + voicePauseRef/voicePauseStartRef; 재개 조건 `if (voicePauseRef.current && !scrubbingRef.current) { if (!isCueSpeaking() || overMax) { ...play()... } }`.
  - tick = setInterval(tick, TICK_INTERVAL_MS) ~line 807 (정지 중에도 구동될 것으로 기대).
  - ~line 801 shouldPauseAtEnd 분기 — F-2에서 ref가 끝까지 가면 pause 유발 가능.
  - drift-sync/feedforward(28-06, rightPlayer.playbackRate·play 제어) — F-2 유력 용의: 큐 pause 직후 tick이 rightPlayer를 되살릴 가능성.
  - app/src/lib/audioCue.ts: isCueSpeaking()은 didJustFinish 이벤트 기반 — 시뮬 expo-audio에서 didJustFinish 미발화 시 speaking=true 고착 가능. 단 그 경우에도 overMax(15s)가 재개시켜야 하는데 미발화 — voicePauseStartRef 재스탬프 또는 voicePauseRef가 다른 경로에서 false로 리셋된 뒤 재개 분기 자체가 안 타는 시나리오 의심.
  - 가설 후보: 큐 전환 재발화 루프(같은 큐 재-speakCue로 voicePauseStartRef 갱신), voicePauseRef 리셋 경로, tick effect 재설치(deps 변화 시 clearInterval 후 상태 소실), expo-audio didJustFinish 시뮬 미발화 + overMax 분기 도달 불가 조합.
DATA_END

## Current Focus

reasoning_checkpoint:
  hypothesis: "tick 내부 stale 재생상태 로컬이 근인. (F-2) 큐 시작 tick 에서 큐 블록이 both pause 한 뒤, 같은 tick 의 follow 블록(703-714)이 tick 시작 시 캡처된 stale leftPlaying=true 로 진입 → 홀드해제 분기(731)가 right 를 즉시 play() 부활. (F-1) 부활한 right 가 음성 정지 중 native end 도달 → 음성 종료 tick 에서 재개 분기(675-682)가 play() 하지만 같은 tick 의 shouldPauseAtEnd(801)가 stale cR(=dR)로 eitherReachedOwnEnd=true → 즉시 both pause = 재개 삼킴. voicePauseRef 는 이미 false 라 overMax 안전망도 영구 미도달."
  confirming_evidence:
    - "재현(제스처 0) 중 right 를 되살릴 수 있는 코드 경로는 731 단 하나 (play() 전 호출지점 grep 배제) — F-2 관측 자체가 이 분기 실행 증명"
    - "강조·pill 해제 관측 = 재개 분기(676) 실행 증명 (제스처 0 에서 voicePauseRef=false 쓰기는 676뿐) — 그런데 영상 미재개 = 같은 tick 후단 pause 만이 설명 가능, 그 후단은 shouldPauseAtEnd(801-804)뿐"
    - "스크린샷: right 가 drift snap-back 없이 4.0→7.8 자유 주행 = 부활 후 tick 들이 leftPlaying=false 로 ④ 스킵하는 예측과 일치. ▶버튼 paused·수동재생 0초 리셋 가능도 예측과 일치"
  falsification_test: "수정 전 라이브 재현에서 큐 정지 중 right 시각이 함께 동결되거나, 음성 종료 후 left 가 자동 재개된다면 가설 기각. 수정 후 재현에서 큐 정지 중 right 동결 + 음성 종료 후 양쪽 자동 재개가 안 나오면 fix 무효."
  fix_rationale: "mid-tick 플레이어 상태 변이(큐 pause / 재개 play) 직후 tick 을 조기 종료(return)해, 변이 이전에 캡처된 stale 로컬(leftPlaying/bothPlaying/cR)이 후단 블록(follow 홀드해제·shouldPauseAtEnd)에 흘러가지 않게 한다. 다음 tick(100ms 뒤)은 신선한 상태로 판정 — drift 보정 1 tick 지연은 무해. 증상(right 부활·재개 삼킴) 각각을 개별 패치하는 대신 공통 근인(stale 상태 소비)을 차단."
  blind_spots: "큐가 영상 말미(right 이미 own-end)에서 발화하는 엣지는 재개 직후 다음 tick 에 end-pause 로 다시 멈춤 — 단 followTick 에선 right own-end 도달 시 이미 both pause 상태라 leftPlaying=true 로 큐 pause 가 걸릴 수 없어 실질 도달 불가. 시뮬 라이브 재검증으로 확인 예정. legacy(followTick=false) 경로는 731 미실행이라 F-2 자체가 없고 return 추가는 no-op."
- next_action: 없음 — 세션 종결. 사람 검증 완료(confirmed fixed, 2026-07-30), 커밋 + resolved/ 아카이브 + knowledge base 기록 완료.

## Evidence

- timestamp: 2026-07-30
  checked: VideoCompare.tsx tick 함수 전문(608-823) — 실행 순서 = ① 상태 캡처(cL/cR/dL/dR/leftPlaying/bothPlaying, 611-628) ② 큐 전환 블록(635-666) ③ 음성 재개 블록(668-690) ④ follow/drift 블록(692-764) ⑤ rate feedforward(766-777) ⑥ shouldPauseAtEnd(779-804)
  found: leftPlaying/bothPlaying/cR 은 tick "시작 시점" 캡처 로컬. 큐 블록(654-655)이 mid-tick 에 both pause 해도, 같은 tick 의 ④번 블록은 stale leftPlaying=true 로 진입한다. ④의 홀드해제 분기(731) `if (!rightPlayer.playing) rightPlayer.play()` 가 방금 pause 된 right 를 즉시 되살림.
  implication: F-2 메커니즘 확정 — 큐 시작 tick 1회에서 right 부활. 이후 tick 은 leftPlaying=false 라 ④ 스킵 → right 를 다시 멈추는 코드가 없어 자기 native end 까지 자유 주행 (스크린샷 4.0→7.8 진행, drift snap-back 없음과 정확히 일치).

- timestamp: 2026-07-30
  checked: rightPlayer.play() 전 호출 지점 grep — 680(재개), 731(홀드해제), 888/906/911(togglePlay), 1040(scrub release), 1088(오프셋 적용 완료)
  found: 재현 시나리오(제스처 0)에서 음성 정지 중 right 를 되살릴 수 있는 경로는 731 단 하나. F-2 가 관측됐다는 사실 자체가 followTick=true(kipupFault 정렬 활성) + 731 실행을 증명.
  implication: F-2 근인 = 731 홀드해제 분기의 stale leftPlaying 진입. 다른 경로 배제 완료.

- timestamp: 2026-07-30
  checked: voicePauseRef=false 쓰기 전 지점 — 676(재개 분기), 851/855(togglePlay), 958(seekBoth), 1077(오프셋 조작)
  found: 851 이후는 전부 사용자 제스처 경로. 재현 중 제스처 없음 → 강조·pill 해제가 관측된 유일한 경로는 676 재개 분기 실행뿐 (else-if 683 은 voiceCueRecordId 를 null 로 만들 뿐 voicePauseRef 를 못 바꿈 — 이미 false 여야 진입).
  implication: 재개 분기는 "실행됐다". play() 호출 후 같은 tick ⑥ shouldPauseAtEnd 가 stale cR(=dR, F-2 로 right 가 끝 도달)로 eitherReachedOwnEnd=true → 즉시 both pause = 재개 삼킴. 이후 voicePauseRef=false 라 재개 분기·overMax(15s) 안전망 모두 영원히 미진입 — "2분+ 강제 재개 미발화" 관측과 일치. 다음 tick setPlaying(false) → ▶ 버튼 paused 표시 일치. togglePlay 의 isAtEnd(followActive: right-own-end)=true → 수동 ▶ 은 0초 리셋 재생 가능 — "수동 재생 가능" 관측 일치.

## Eliminated

- hypothesis: expo-audio didJustFinish 시뮬 미발화 → speechActive true 고착
  evidence: 강조·pill 해제가 mp3 종료 직후 정상 관측됨. 해제 경로(676 또는 683)는 둘 다 !isCueSpeaking() 필요 → didJustFinish 는 발화됨.
  timestamp: 2026-07-30
- hypothesis: voicePauseStartRef 반복 재스탬프로 overMax 미도달
  evidence: 재스탬프는 큐 텍스트 전환 + started + leftPlaying=true 조합에서만(658). 음성 정지 중 left 는 pause 상태(leftPlaying=false) + cL 동결이라 큐 텍스트 불변 → 재스탬프 경로 자체가 막혀 있음.
  timestamp: 2026-07-30
- hypothesis: voicePauseRef 가 scrub/toggle/offset 등 다른 경로에서 리셋돼 재개 분기 스킵
  evidence: 해당 리셋(851/855/958/1077)은 전부 사용자 제스처 필요 — 재현 중 제스처 0. 리셋은 재개 분기(676) 자신이 수행한 것.
  timestamp: 2026-07-30
- hypothesis: tick effect 재설치(deps 변화)로 interval 소실 → 재개 판정 정지
  evidence: deps [hasAny,hasLeft,hasRight,leftPlayer,rightPlayer] 는 재현 중 불변. 또한 right 시각 라벨이 계속 갱신됨(4.0→7.8 스크린샷) = tick 구동 중.
  timestamp: 2026-07-30

## Resolution

- root_cause: VideoCompare.tsx tick 의 intra-tick stale 재생상태. tick 시작 시 캡처한 leftPlaying/bothPlaying/cR 로컬을, 큐 블록의 mid-tick both-pause(654-655)와 재개 분기의 mid-tick both-play(679-680) 이후 블록들이 그대로 소비. (F-2) 큐 시작 tick — follow 블록이 stale leftPlaying=true 로 진입, 홀드해제 분기(731)가 방금 pause 된 right 를 부활시켜 음성 정지 중 자기 native end 까지 주행. (F-1) 음성 종료 tick — 재개 분기가 play() 후, 같은 tick 의 shouldPauseAtEnd(801)가 stale cR(=dR·F-2 산물)로 either-own-end=true → 즉시 both pause = 자동 재개 삼킴. voicePauseRef 는 이미 false 라 overMax(15s) 안전망도 영구 미도달.
- fix: VideoCompare.tsx tick 에 조기 종료(return) 2곳 추가 — (1) 큐 pause 상태 진입 직후(F-2: stale leftPlaying 으로 follow 홀드해제 분기가 right 부활 차단), (2) 음성 종료 자동 재개 play() 직후(F-1: stale cR 로 shouldPauseAtEnd 가 재개를 즉시 삼키는 것 차단). mid-tick 플레이어 상태 변이 후에는 다음 tick(100ms)이 신선한 상태로 판정. typecheck 통과.
- verification: (1) 자체 검증 — 시뮬 라이브 재현(iPhone 16 Pro, Metro dev 번들 재로드) — 기록→킵업(79)→동작 비교→재생. 타임라인: t+4s/t+6s/t+8s = 큐 발화 중 "음성 중 — 잠시 멈춤" pill+자막 표시, **양쪽 시각 라벨 0:03.1 동결**(F-2 해소 — 수정 전엔 우측이 4.0→7.8 진행) → t+10.5s = pill·자막 해제 + ⏸(재생중) 버튼 + **양쪽 0:05.4 동기 진행**(F-1 해소 — 자동 재개 발화) → t+13s = 양쪽 0:06.7 native end 정상 종료(기존 end-pause 동작 회귀 없음). typecheck 통과. 스크린샷: scratchpad p_t04/p_t06/p_t08/p_t10/p_t13.png. (2) 사람 검증(2026-07-30, confirmed fixed) — 오케스트레이터 독립 재검증(앱 재실행 후 fresh 재현): 킵업 doc 재생 → 3.1s 큐 발화 시 양쪽 패널 모두 0:03 동결(pill+자막 표시, ref 주행 없음 = F-2 해소) → 정지 플래토 정확히 5.5초(mp3 길이) → 자동 재개 후 양쪽 0:04.6 동기 진행(F-1 해소) → 정상 종료. 증거 = scratchpad fix_verify.mp4 (f_48~58 정지 플래토, f_62 재개).
- files_changed: [app/src/components/VideoCompare.tsx]
