// Phase 35 (quick-260808-jix) — 합성 비교 영상 단일 mp4 플레이어.
//
// 서버(Pod 사후 스테이지)가 user·ref 두 패널 + 감점 정지·코칭 음성·자막을 이미
// 한 mp4 에 구워 놓았다 (contract.md §12.9 — 리그 ALL PASS 만 도착). 여기는
// **재생만** 한다 — 오버레이·동기·스냅·재개 로직 0 (그 계열 버그가 재생기
// 차원에서 소멸하는 것이 돌파 ① 의 목적). 신규 화면 디자인 아님 — 기존
// '동작 비교' 섹션 내 재생원 교체.
//
// UI 라운드 (belle 실기기):
//   · 가로 크게 보기 — 260702-t0v 90° 회전 Modal 패턴 재사용 (portrait 고정
//     유지, JS-only OTA 가능). 단일 플레이어라 동기 로직 불요 — 같은 player
//     인스턴스에 두 번째 VideoView attach (expo-video 다중 VideoView, t0v 선례
//     — 새 useVideoPlayer 호출 금지).
//
// quick-260809-jnb — 조작 UI 복귀 (belle 08-09 실기기 반려):
//   증상 = "조작 UI가 이상해져 있다". 원인 = `nativeControls`(iOS 기본, 몇 초 뒤
//   자동 숨김) + 얇은 틱 바 조합이라, 컨트롤이 숨은 뒤엔 **트랙 위에 점 하나만
//   남아 멈춘 재생바로 읽혔다**(belle 화면 실측: 영상 18.53s / 정지 5.13s =
//   27.7% 지점 = 스크린샷의 그 점). 트랙+점은 "재생 위치"의 시각 문법인데 실제
//   의미는 "감점 정지 지점"이라 의미가 충돌한 것.
//   → 듀얼 플레이어(VideoCompare)의 컨트롤 세트를 그대로 가져온다: 재생/일시정지
//     · 실제 스크럽 트랙(rail/fill/thumb + 드래그) · 시간 · 처음으로. 정지 틱은
//     트랙 **위 별도 줄**에 번호(①②③)를 달아 표시 — 아래 진짜 스크러버가 있으면
//     번호 달린 마커는 재생바로 오독되지 않는다(듀얼 플레이어에서 검증된 배치).
//   ★ 정렬 미세조정 컨트롤(0.1초 뒤로/앞으로 · 시작점 오프셋 슬라이더 · 초기화)은
//     **의도적으로 안 가져온다** — belle 08-09: "알아서 짜맞춰서 비교해줄거면
//     뒤로 조정 앞으로 조정 없어도 될 것 같다". 그것들은 두 영상을 사람이 손으로
//     맞추던 시절의 장치이고, 서버가 정렬해 한 파일로 굽는 지금은 대상이 없다.
//
// URL 은 1시간 TTL asset 서명이라 저장·재사용하지 않고 mount(=analysisId)마다
// 재발급한다 (만료 재서명 = 기존 asset 패턴, H-02 URL 비저장).
// fetch 실패/404 → onUnavailable() — 화면이 기존 듀얼 플레이어로 강등
// (catch 삼킴 금지 — [[icloud-offload-breaks-original-asset-picker]] 교훈,
// __DEV__ warn 으로 원인 가시화).
//
// belle 09-07 — 가로 전체화면에 손가락 확대(핀치) + 탭 멈춤을 얹는다. 이 가지에도
// 필요한 이유: 어느 가지가 그려질지는 기기의 실시간 Firestore 상태가 정한다
// (renderedCompareReady — result.tsx:1094). 듀얼 플레이어에만 확대를 달면 합성
// 영상이 도착한 분석에서는 belle 이 그 기능을 아예 만나지 못한다.
//
// ★ 이 가지의 한계 — 감추지 않고 적어 둔다 (듀얼 플레이어와 같은 것을 주지 못한다):
//   1) 두 패널이 **한 프레임에 이미 구워져** 있다. 그래서 핀치는 좌·우를 따로
//      확대하지 못하고 둘을 함께 키운다. 왼쪽만 크게 보려면 손가락으로 확대한 뒤
//      밀어서(팬) 그쪽으로 옮겨야 한다.
//   2) **인증된 짝 순간으로 뛰어드는 진입점이 없다.** 이 가지가 가진 유일한 시각은
//      freezes[].outSec 인데 그것은 **출력 mp4 의 시계**이지 학생 영상 초가 아니다
//      (학생 도메인 초 = DeductionRecord.atVideoSec — 여기엔 없다). 그래서
//      momentJump/openFullscreenAtRef 배선을 하지 않고, 기준 짝 정직 문구도 띄우지
//      않는다. 짝을 말할 근거가 없는데 말하면 그것이 곧 날조다. 대신 기존 정지 틱
//      (outSec 기반, 출력 시계 안에서는 정확)이 그 순간으로 데려다 준다.
//   3) 기본 배율은 **1.0** 이다. 듀얼 플레이어의 1.35 는 세로 인물 영상을 위해
//      belle 이 승인한 프레이밍이고, 여기 소스는 가로로 나란한 패널 2장이라 같은
//      값을 쓰면 승인된 적 없는 크롭이 된다 (오늘 화면과 픽셀 동일 = 1.0).
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Modal,
  PanResponder,
  Pressable,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
  type LayoutChangeEvent,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { useVideoPlayer, VideoView, type VideoPlayer } from 'expo-video';

import { fetchVisualAssetUrls } from '../lib/api';
import {
  hasSeenFullscreenPinchHint,
  markFullscreenPinchHintSeen,
} from '../lib/coachmark';
import { MIN_ZOOM, type ZoomState } from '../lib/pinchZoom';
import {
  SWAP_READY_TIMEOUT_MS,
  decideSwapSeek,
  type PlayerStatus,
  type SwapPhase,
} from '../lib/sourceSwapSeek';
import type { RenderedCompareFreeze } from '../types/analysis';
import { colors, layout, radius, spacing, typography } from '../theme';
import { compareCardControls } from '../theme/compareControls';
import { ZoomPinchLayer } from './ZoomPinchLayer';

// 정지 직전 여유 — 틱 탭이 정지 화면이 아니라 그 직전 재생부터 보이게
// (지정 -0.5s — freeze 진입 크로스페이드 0.17s 계열보다 넉넉).
const TICK_JUMP_LEAD_S = 0.5;

// 재생 위치 폴링 — VideoCompare 와 동일 주기(같은 체감 부드러움).
const TICK_INTERVAL_MS = 100;
const THUMB_DIAMETER = 14;
// 가로 전체화면 텍스트 배율 (t0v 관례 — 세로 대비 크게).
const FULLSCREEN_TEXT_SCALE = 1.6;

// belle 09-07 — 이 가지의 확대 출발점·복귀점. 1.0 = 오늘 화면과 픽셀 동일
// (파일 헤더 한계 3 참조 — 듀얼 플레이어의 1.35 를 여기 가져오면 승인된 적 없는
// 크롭이 된다). 팬은 1.0 에서 clampZoom 이 0 으로 강제하므로 오늘과 완전히 같다.
const freshRenderedZoom = (): ZoomState => ({ scale: MIN_ZOOM, tx: 0, ty: 0 });

// 첫 전체화면 진입 안내 pill 자동 소멸 시간(ms). VideoCompare 의 같은 안내와 같은
// 값·같은 문구·같은 1회 플래그(coachmark.ts)를 쓴다 — 사용자에게는 같은 제스처를
// 배우는 한 번의 경험이라, 가지가 둘이라고 두 번 가르치면 안 된다.
const PINCH_HINT_AUTO_DISMISS_MS = 4000;

// 소스 교체 seek 를 되읽어 검증하기까지의 유예(ms). expo-video 의 seek 는
// 비동기라 대입 직후 읽으면 옛 값이 나온다. 220ms 는 듀얼 플레이어의 재재생
// seek 유예(REPLAY_SEEK_DELAY_MS 200ms — replaySettle.ts 헤더)와 같은 자리수이고,
// 실패해도 SWAP_SEEK_ATTEMPTS 만큼 다시 쏘므로 짧게 잡아 체감을 지킨다.
const SWAP_VERIFY_DELAY_MS = 220;

function fmtTime(s: number): string {
  if (!isFinite(s) || s < 0) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

// 0.1초 정밀 (belle 기존 요구 "0.0초 단위" 승계).
// 감점 목록도 같은 시계를 찍어야 해서 내보낸다 (belle 09-09).
export function fmtTimeDecimal(s: number): string {
  if (!isFinite(s) || s < 0) return '0:00.0';
  const m = Math.floor(s / 60);
  const sec = s - m * 60;
  return `${m}:${sec.toFixed(1).padStart(4, '0')}`;
}


export default function RenderedComparePlayer({
  analysisId,
  onUnavailable,
  freezes,
  leftLabel,
  rightLabel,
  renderBelowControls,
}: {
  analysisId: string;
  onUnavailable: () => void;
  // doc renderedCompare.freezes — 부재(구버전 doc) = 틱 없이 재생만 (fail-open).
  freezes?: RenderedCompareFreeze[];
  /** 영상 좌상단 역할 알약 — 합성 mp4 의 왼쪽 패널이 학생이다 (시안 2). */
  leftLabel: string;
  /** 영상 우상단 역할 알약. 없으면 그 알약을 그리지 않는다 (문구를 지어내지 않는다). */
  rightLabel?: string | null;
  /** 시안 2 — 감점 목록은 옵션 행 바로 아래, 카드 **안**에 온다. */
  renderBelowControls?: (api: {
    /** 감점 행 → 그 정지 지점으로 이동. 짝 없으면 false. */
    seekToRecord: (recordId: string) => boolean;
    /** 지금 재생 중인 정지의 rid (없으면 null) — 그 행을 켠다. */
    activeRid: string | null;
    /**
     * 그 감점이 **이 합성본에서** 몇 초인지 (belle 09-09 지적).
     * 목록이 원본 초를 찍으면 바로 위 재생기 시간과 다른 숫자가 된다 —
     * 정지가 끼어 합성본이 더 길기 때문이다. 짝이 없으면 null (초 칸 생략).
     */
    outSecOf: (recordId: string) => number | null;
  }) => React.ReactNode;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [slowMotion, setSlowMotion] = useState(false);
  // belle 09-09 '관절선' — 이 가지의 표시는 mp4 픽셀에 구워져 있어 앱이 지울 수
  // 없다. 그래서 서버가 **표시 없는 판**을 함께 굽고(contract §12.9 keyPlain)
  // 토글은 두 소스를 갈아끼운다. plain 이 없는 doc(구버전·업로드 실패)에서는
  // 칩 자체를 그리지 않는다 — 눌러도 아무 일 없는 버튼을 두지 않는다.
  const [urlPlain, setUrlPlain] = useState<string | null>(null);
  const [overlayOn, setOverlayOn] = useState(true);
  // belle 09-09 '음성 온오프'. 이 mp4 의 오디오가 코칭 음성 그 자체라(파일 헤더)
  // player.muted 가 곧 음성 스위치다 — 앱이 따로 재생하는 음성이 없다.
  const [audioOn, setAudioOn] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);
  // onUnavailable 는 보통 인라인 콜백(매 렌더 새 참조)이라 effect deps 에 넣으면
  // 렌더마다 재발급이 돈다 — ref 로 최신 참조만 유지 (deps = analysisId 만).
  const onUnavailableRef = useRef(onUnavailable);
  onUnavailableRef.current = onUnavailable;

  useEffect(() => {
    let cancelled = false;
    setUrl(null); // 분석 전환 시 이전 영상 잔상 방지
    setUrlPlain(null);
    fetchVisualAssetUrls(analysisId, 'renderedCompare')
      .then(({ url: playbackUrl, urlPlain: plain }) => {
        if (cancelled) return;
        setUrl(playbackUrl);
        setUrlPlain(plain);
      })
      .catch((err) => {
        // 404(부재/failed/stale) 포함 전부 폴백 강등 — 조용한 실패 금지.
        if (__DEV__) console.warn('[renderedCompare] URL 발급 실패 — 듀얼 플레이어 강등', err);
        if (!cancelled) onUnavailableRef.current();
      });
    return () => {
      cancelled = true;
    };
  }, [analysisId]);

  // expo-video: 훅은 조건부 호출 불가 — 항상 호출하고 URL 유무로 제어
  // (VideoCompare/ReferenceCornerSection 선례). 음성이 구워져 있으므로 muted
  // 금지 — 이 mp4 의 오디오가 코칭 음성 그 자체다.
  const player = useVideoPlayer(url, (p) => {
    p.loop = false;
  });

  // 시안 2 '0.5배속' — 듀얼 플레이어와 같은 규약(VideoCompare:782).
  useEffect(() => {
    if (player) player.playbackRate = slowMotion ? 0.5 : 1;
  }, [slowMotion, player]);

  // '관절선' 토글 — 표시 있는 판 ↔ 없는 판 소스 교체 (belle 09-09).
  //
  // 재생 위치와 재생 상태를 **그대로 이어받는다**. 그러지 않으면 관절선을 끄는
  // 순간 영상이 처음으로 돌아가 "무엇이 달라졌는지"를 비교할 수 없다 — 이 토글의
  // 목적 자체가 같은 순간을 표시 유무로 견주는 것이다.
  // urlPlain 이 없으면 이 효과는 아무것도 하지 않는다(칩도 안 그려진다).
  //
  // ★ belle 09-10 실기기 반려(TestFlight/LTE) — "관절선을 누르면 처음부터 재생된다,
  //   그런데 가끔은 정상". 맥 시뮬레이터에서는 09-09 에 정상으로만 관측됐다.
  //   종전 구현은 `await player.replaceAsync(next)` 바로 뒤에 `currentTime = at` 을
  //   대입했다. **그 대입은 기기에서 버려진다.** expo-video 3.0.16 네이티브 근거:
  //     · `replaceAsync`(ios/VideoModule.swift:330-333)가 부르는 async
  //       `replaceCurrentItem`(ios/VideoPlayer.swift:236-268)은 main 큐 블록을
  //       **예약만 하고 반환**한다. 프로미스 해소는 "아이템이 꽂혔다"까지지
  //       "아이템이 익었다"가 아니다 — `DangerousPropertiesStore`
  //       (ios/VideoPlayer/DangerousPropertiesStore.swift:1-2, 7-14) 주석 그대로
  //       "아직 안 꽂혔다"만 막고 "아직 안 익었다"는 안 막는다.
  //     · 그래서 status `.unknown` 인 새 AVPlayerItem 에 exact seek
  //       (ios/VideoPlayer.swift:55)이 날아간다. 새 아이템은 아무것도 프리로드하지
  //       않으므로(ios/VideoPlayerItem.swift:27 `automaticallyLoadedAssetKeys: nil`)
  //       원격 S3 presigned mp4 의 moov 도착까지의 창이 맥에서는 ~0, LTE 폰에서는
  //       초 단위다 — **sim 은 되고 기기는 안 되던 축이 여기서 기계적으로 나온다.**
  //     · 또 `replaceCurrentItem` 에는 pause 가 없고 `rate` 는 AVPlayer 레벨
  //       (ios/VideoPlayer.swift:32-35)이라 아이템 교체를 넘어 유지된다. 재생 중에
  //       토글하면 새 아이템이 ready 되는 즉시 0초부터 돈다. 종전의
  //       `if (wasPlaying) player.play()` 는 rate 가 0 이 된 적이 없어 무의미했다.
  //   → 순서를 **교체 전 pause → ready 대기 → seek → 되읽어 검증 → 재시도 →
  //     그 다음에만 play** 로 바꾼다. 판정은 lib/sourceSwapSeek.ts 가 갖고(순수
  //     모듈, node --test 8축) 여기서는 호출만 한다.
  //
  // ★ 재적용 금지 — 교체 뒤에 `playbackRate`/`muted`/`loop`/`volume` 을 다시
  //   대입하지 않는다. 전부 AVPlayer 레벨이라 교체를 넘어 유지되고, 특히
  //   `playbackRate` 의 iOS `didSet` 은 **값이 같아도 무조건** `ref.rate` 를 쓴다
  //   (ios/VideoPlayer.swift:26-36) — 재적용하면 정지 상태에서 재생이 시작된다.
  const overlayOnRef = useRef(overlayOn);
  // 교체 진행 중 — ref 는 폴링이 매 tick 읽고, state 는 칩 잠금을 화면에 보인다.
  const swappingRef = useRef(false);
  const [swapping, setSwapping] = useState(false);
  // 세대 — 연타/재실행 시 옛 콜백을 전부 무효화한다(늦게 온 seek 가 새 교체를
  // 되감는 것을 막는다).
  const swapEpochRef = useRef(0);
  useEffect(() => {
    const prevOverlayOn = overlayOnRef.current;
    if (prevOverlayOn === overlayOn) return;
    overlayOnRef.current = overlayOn;
    const next = overlayOn ? url : urlPlain;
    if (!player || !next) return;

    // 1) 교체 **전에** 읽는다. 교체 뒤의 값은 옛 아이템 값이거나 0 이다.
    let targetSec = 0;
    let wasPlaying = false;
    try {
      targetSec = player.currentTime ?? 0;
      wasPlaying = player.playing;
    } catch {
      // 해제 직후 접근 — 0 부터 시작해도 토글 자체는 성립한다.
    }

    // 2) 교체 **전에** 멈춘다. 살아남는 rate 가 새 아이템을 0초부터 돌리는 것을
    //    막고(축 2), 로드를 기다리는 동안 옛 아이템이 계속 진행해 targetSec 이
    //    낡는 것도 같이 막는다.
    try {
      player.pause();
    } catch {
      // 해제 직후 — 아래 절차가 어차피 무해하게 끝난다.
    }

    // 3) 세대 증가.
    const epoch = swapEpochRef.current + 1;
    swapEpochRef.current = epoch;
    const alive = () => swapEpochRef.current === epoch;

    swappingRef.current = true;
    setSwapping(true);

    let phase: SwapPhase = 'awaitingReady';
    let attempts = 0;
    let observedSec: number | null = null;
    let loadedDurationSec = 0;
    // ready 판정은 **이벤트가 말한 것**만 믿는다. `player.status` 를 직접 읽으면
    // 옛 아이템의 'readyToPlay' 가 그대로 남아 있어(iOS status didSet 은 값이
    // 바뀔 때만 emit) 익지 않은 새 아이템을 익은 것으로 오독한다 — 그것이 이
    // 결함의 축 1 이다.
    let signalStatus: PlayerStatus = 'loading';
    const startedAt = Date.now();
    const subs: { remove: () => void }[] = [];
    let readyTimer: ReturnType<typeof setTimeout> | null = null;
    let verifyTimer: ReturnType<typeof setTimeout> | null = null;

    const stopWatching = () => {
      for (const sub of subs) sub.remove();
      subs.length = 0;
      if (readyTimer) {
        clearTimeout(readyTimer);
        readyTimer = null;
      }
      if (verifyTimer) {
        clearTimeout(verifyTimer);
        verifyTimer = null;
      }
    };

    const endSwap = () => {
      phase = 'done';
      stopWatching();
      swappingRef.current = false;
      setSwapping(false);
    };

    // 실패 시 칩 되돌림. **ref 를 먼저** 되돌려야 재실행된 effect 가 맨 위
    // 가드에서 즉시 return 해 되감기 루프가 생기지 않는다.
    const revertChip = () => {
      overlayOnRef.current = prevOverlayOn;
      setOverlayOn(prevOverlayOn);
    };

    const step = () => {
      if (!alive() || phase === 'done') return;
      let durationSec = loadedDurationSec;
      if (!(durationSec > 0)) {
        try {
          durationSec = player.duration ?? 0;
        } catch {
          endSwap();
          return;
        }
      }
      const decision = decideSwapSeek({
        phase,
        status: signalStatus,
        targetSec,
        durationSec,
        wasPlaying,
        observedSec,
        attempts,
        waitedMs: Date.now() - startedAt,
      });
      if (decision.action === 'wait') return;
      if (decision.action === 'abort') {
        // 로드 실패 — seek 도 play 도 하지 않는다. 조용한 0초 재생으로 강등하면
        // 사용자는 "관절선을 껐더니 처음부터 돈다"로 읽는다.
        endSwap();
        revertChip();
        return;
      }
      if (decision.action === 'seek') {
        phase = 'seeking';
        attempts += 1;
        observedSec = null;
        try {
          player.currentTime = decision.seekSec;
        } catch {
          endSwap();
          return;
        }
        if (verifyTimer) clearTimeout(verifyTimer);
        verifyTimer = setTimeout(() => {
          verifyTimer = null;
          if (!alive() || phase !== 'seeking') return;
          try {
            observedSec = player.currentTime ?? null;
          } catch {
            endSwap();
            return;
          }
          step();
        }, SWAP_VERIFY_DELAY_MS);
        return;
      }
      // finish — 재생 재개는 **여기서만** 한다.
      const shouldPlay = decision.play;
      endSwap();
      if (shouldPlay) {
        try {
          player.play();
        } catch {
          // 해제 직후 — 사용자가 영상을 탭해 다시 재생할 수 있다.
        }
      }
    };

    // 4) 리스너를 `replaceAsync` **전에** 건다 — Android 는 statusChange('loading')
    //    이 프로미스 해소보다 먼저 나간다(android/.../VideoModule.kt:356-374).
    //    `sourceLoad` 가 정본이다: iOS 는 새 아이템이 `.readyToPlay`(또는 `.error`)
    //    에 닿았을 때만 이 이벤트를 낸다(ios/VideoPlayerObserver.swift:419-421 →
    //    ios/VideoPlayer.swift:387). `statusChange` 는 보조 — 먼저 오는 쪽이 이긴다.
    //    `sourceLoad` 는 `.error` 로도 오므로 `statusChange` 의 error 를 반드시
    //    같이 구독한다.
    try {
      subs.push(
        player.addListener('sourceLoad', ({ duration }) => {
          if (duration > 0) loadedDurationSec = duration;
          // 오류 로드도 sourceLoad 로 온다. iOS 는 `.error` 를 이 이벤트보다 먼저
          // status 에 반영하므로(VideoPlayerObserver.swift:412-421) 여기서 가른다.
          let failed = false;
          try {
            failed = player.status === 'error';
          } catch {
            failed = true;
          }
          signalStatus = failed ? 'error' : 'readyToPlay';
          step();
        }),
      );
      subs.push(
        player.addListener('statusChange', ({ status }) => {
          signalStatus = status;
          step();
        }),
      );
    } catch {
      // 리스너 등록 실패 — 아래 폴백 타이머만으로 절차를 마친다(멈추지 않는다).
    }

    // ready 신호가 끝내 오지 않아도 칩이 잠긴 채 남지 않게 하는 상한. 여기 걸리면
    // 판정이 마지막으로 한 번 seek 를 쏘고 절차를 진행시킨다.
    readyTimer = setTimeout(() => {
      readyTimer = null;
      step();
    }, SWAP_READY_TIMEOUT_MS + 50);

    void player.replaceAsync(next).catch(() => {
      if (!alive()) return;
      // 교체 자체가 실패 = 소스는 옛것 그대로다. 칩을 되돌리고, 우리가 멈춘
      // 재생만 원래대로 돌려 놓는다(위치는 건드린 적이 없다).
      endSwap();
      revertChip();
      if (wasPlaying) {
        try {
          player.play();
        } catch {
          // 해제 직후 — 사용자가 영상을 탭해 다시 재생할 수 있다.
        }
      }
    });

    return () => {
      stopWatching();
      swappingRef.current = false;
      setSwapping(false);
    };
  }, [overlayOn, url, urlPlain, player]);

  useEffect(() => {
    if (player) player.muted = !audioOn;
  }, [audioOn, player]);


  // ── 재생 상태 폴링 (커스텀 컨트롤의 유일한 상태원) ────────────────────────
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  // 드래그 중에는 폴링이 썸을 되돌리지 않게 차단 (VideoCompare scrubbingRef 선례).
  const scrubbingRef = useRef(false);

  useEffect(() => {
    setPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    const id = setInterval(() => {
      // 소스 교체 중에는 화면을 갱신하지 않는다. 교체 순간의 `currentTime = 0` /
      // `playing = false` 가 그대로 쓰이면 시간 텍스트·트랙 fill·activeRid 파생
      // 감점 행이 한 tick 깜빡이고, belle 은 그 깜빡임을 "처음으로 돌아갔다"로
      // 읽는다 — seek 이 성공한 경우에도 그렇다. 듀얼 경로(VideoCompare)의
      // replaySettleTicksRef 방어와 같은 취지다.
      if (swappingRef.current) return;
      try {
        const d = player.duration;
        if (d && d > 0) setDuration(d);
        setPlaying(player.playing);
        if (!scrubbingRef.current) setCurrentTime(player.currentTime ?? 0);
      } catch {
        // player 해제 직후 접근 — 폴링은 다음 tick 에서 정상화 (무해).
      }
    }, TICK_INTERVAL_MS);
    return () => clearInterval(id);
  }, [player]);

  const togglePlay = () => {
    if (player.playing) player.pause();
    else player.play();
  };
  const seekTo = (sec: number) => {
    const clamped = Math.max(0, duration > 0 ? Math.min(sec, duration) : sec);
    player.currentTime = clamped;
    setCurrentTime(clamped);
  };

  /** 감점 행 → 이 합성본에서의 초. 짝이 없으면 null (초 칸을 비운다). */
  const outSecOf = (recordId: string): number | null =>
    freezeOutSecByRid.get(recordId.split(':')[0]) ?? null;

  /** 감점 행 → 그 정지 지점. 짝이 없으면 false — 아무 데도 안 뛴다(지어내지 않는다). */
  const seekToRecord = (recordId: string): boolean => {
    const rid = recordId.split(':')[0];
    const outSec = freezeOutSecByRid.get(rid);
    if (outSec == null) return false;
    seekTo(Math.max(0, outSec - TICK_JUMP_LEAD_S));
    return true;
  };

  // 트랙 드래그 스크럽 — 세로/가로가 각자 폭을 재고(회전 컨테이너라 폭이 다름)
  // 같은 핸들러를 쓴다.
  const trackWidthRef = useRef(0);
  const fsTrackWidthRef = useRef(0);
  const draggingFsRef = useRef(false);
  const onTrackLayout = (e: LayoutChangeEvent) => {
    trackWidthRef.current = e.nativeEvent.layout.width;
  };
  const onFsTrackLayout = (e: LayoutChangeEvent) => {
    fsTrackWidthRef.current = e.nativeEvent.layout.width;
  };

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => true,
        onMoveShouldSetPanResponder: () => true,
        onPanResponderGrant: (e) => {
          scrubbingRef.current = true;
          const w = draggingFsRef.current
            ? fsTrackWidthRef.current
            : trackWidthRef.current;
          if (w > 0 && duration > 0) {
            seekTo((e.nativeEvent.locationX / w) * duration);
          }
        },
        onPanResponderMove: (e) => {
          const w = draggingFsRef.current
            ? fsTrackWidthRef.current
            : trackWidthRef.current;
          if (w > 0 && duration > 0) {
            const x = Math.max(0, Math.min(w, e.nativeEvent.locationX));
            seekTo((x / w) * duration);
          }
        },
        onPanResponderRelease: () => {
          scrubbingRef.current = false;
        },
        onPanResponderTerminate: () => {
          scrubbingRef.current = false;
        },
      }),
    // duration 이 잡힌 뒤 재생성되어야 초 환산이 유효 (0 이면 no-op).
    [duration],
  );

  // t0v 선례 — 90° 회전 컨테이너 치수 (portrait 고정 앱에서 가로 시뮬레이트,
  // useWindowDimensions = 반응형 hook 값 직접 사용).
  const { width: winW, height: winH } = useWindowDimensions();
  const fsShort = Math.min(winW, winH);
  const fsLong = Math.max(winW, winH);
  const validFreezes = freezes ?? [];

  // 260909-ji1 — 감점 행 탭 = 그 지점으로 이동 (belle 09-09 "유튜브 스크립트처럼").
  //
  // 매핑은 이미 계약에 있다 (contract.md §12.9): freezes[].rid = recordId 의 콜론 앞
  // 축약, outSec = 그 정지가 시작하는 **출력 mp4** 초(= 렌더 리포트 voiceStartOutS).
  // 내가 앞서 "학생 영상 초와 도메인이 달라 못 뛴다"고 한 것은 틀렸다 — 출력 영상
  // 안에서 뛰는 데는 outSec 이 정확한 좌표이고, 방금 걷어낸 번호 틱이 바로 그 일을
  // 하고 있었다.
  //
  // ★ 0.8초 — 정지·음성은 **결함 순간보다 0.8초 먼저** 시작한다(창 반폭 0.8s,
  //   260731-iis 판정). 그래서 outSec 으로 뛰면 해설이 시작하는 지점에 선다.
  //   여기서 다시 TICK_JUMP_LEAD_S(0.5s)를 빼는 것은 정지 화면이 아니라 **그 직전
  //   움직임부터** 보이게 하려는 것이다(계약 §12.9 "탭 점프 -0.5s 시크", 260809-jnb).
  const freezeOutSecByRid = useMemo(() => {
    const m = new Map<string, number>();
    for (const f of validFreezes) if (!m.has(f.rid)) m.set(f.rid, f.outSec);
    return m;
  }, [validFreezes]);

  /**
   * 지금 재생 위치가 들어 있는 정지의 rid — 그 감점 행이 켜진다 (belle 09-09 f7e9da4e).
   * 듀얼 경로에만 있던 표식을 이 경로에도 준다. 근거는 doc 의 freezes[outSec, freezeS]
   * 구간뿐이라 지어내는 값이 0 이다. 어느 구간에도 없으면 null(아무 행도 안 켠다).
   */
  const activeRid = useMemo(() => {
    for (const f of validFreezes) {
      const s0 = f.outSec;
      const s1 = s0 + (typeof f.freezeS === 'number' ? f.freezeS : 0);
      if (currentTime >= s0 && currentTime < s1) return f.rid;
    }
    return null;
  }, [validFreezes, currentTime]);


  // ── belle 09-07 손가락 확대 (파일 헤더의 한계 3건과 함께 읽을 것) ────────────
  //
  // 확대 상태는 여기가 소유하고, 배율·팬 수학은 lib/pinchZoom, 제스처 배선은
  // components/ZoomPinchLayer 가 갖는다 (듀얼 플레이어와 같은 3분할 — 사본 0).
  const [zoom, setZoom] = useState<ZoomState>(freshRenderedZoom);
  // ZoomPinchLayer 는 클리핑 박스의 **숫자** 치수를 요구한다(퍼센트 금지 —
  // 90° 회전 absolute 컨테이너 안에서 퍼센트가 축소 렌더된다, t0v 실측). 이 가지의
  // 영상 자리는 컨트롤 높이에 따라 달라져 미리 계산할 수 없으므로 실측한다.
  const [fsBox, setFsBox] = useState({ w: 0, h: 0 });
  const onFsVideoLayout = (e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    setFsBox((prev) =>
      prev.w === Math.round(width) && prev.h === Math.round(height)
        ? prev
        : { w: Math.round(width), h: Math.round(height) },
    );
  };
  // 기본 프레이밍에서 벗어났는가 = '원래대로' 노출 조건. 배율 1.0 에서는 팬이
  // clampZoom 에 의해 0 으로 강제되므로 사실상 배율 판정이지만, 판정 문법은
  // 듀얼 플레이어와 같게 둔다(두 곳이 다른 규칙을 갖지 않는다).
  const zoomTouched =
    Math.abs(zoom.scale - MIN_ZOOM) > 0.001 || zoom.tx !== 0 || zoom.ty !== 0;

  // 첫 진입 1회 안내. 낙관적 초기값 true(=이미 봄)라 AsyncStorage 읽기 전에
  // 한 프레임 깜빡이지 않고, 읽기 실패도 true 로 수렴한다(coachmark.ts 계약).
  const [pinchHintSeen, setPinchHintSeen] = useState(true);
  const pinchHintSeenRef = useRef(true);
  pinchHintSeenRef.current = pinchHintSeen;
  const [pinchHintVisible, setPinchHintVisible] = useState(false);
  const pinchHintTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let alive = true;
    hasSeenFullscreenPinchHint()
      .then((seen) => {
        if (alive) setPinchHintSeen(seen);
      })
      .catch(() => {
        /* graceful — 실패 시 초기값 true 유지(안내 미노출) */
      });
    return () => {
      alive = false;
    };
  }, []);
  useEffect(
    () => () => {
      if (pinchHintTimerRef.current) clearTimeout(pinchHintTimerRef.current);
    },
    [],
  );

  // 안내 종료 = 실제 핀치 / 영상 탭 / 4초 경과. 어느 경로든 "봤다"로 기록해 다음
  // 진입부터 뜨지 않는다 (쓰기는 fire-and-forget — coachmark.ts 계약).
  const dismissPinchHint = useCallback(() => {
    if (pinchHintTimerRef.current) {
      clearTimeout(pinchHintTimerRef.current);
      pinchHintTimerRef.current = null;
    }
    setPinchHintVisible(false);
    if (!pinchHintSeenRef.current) {
      pinchHintSeenRef.current = true;
      setPinchHintSeen(true);
      markFullscreenPinchHintSeen();
    }
  }, []);

  const openFullscreen = () => {
    setFullscreen(true);
    if (!pinchHintSeenRef.current) {
      setPinchHintVisible(true);
      if (pinchHintTimerRef.current) clearTimeout(pinchHintTimerRef.current);
      pinchHintTimerRef.current = setTimeout(() => {
        pinchHintTimerRef.current = null;
        dismissPinchHint();
      }, PINCH_HINT_AUTO_DISMISS_MS);
    }
  };
  const closeFullscreen = () => {
    setFullscreen(false);
    // 닫으면 기본 프레이밍으로 복귀 — 다음에 열었을 때 지난번 확대가 남아 있으면
    // "왜 이렇게 크게 나오지"가 된다 (듀얼 플레이어 closeFullscreen 과 같은 처분).
    setZoom(freshRenderedZoom());
    if (pinchHintTimerRef.current) {
      clearTimeout(pinchHintTimerRef.current);
      pinchHintTimerRef.current = null;
    }
    setPinchHintVisible(false);
  };
  const progressPct =
    duration > 0 ? Math.max(0, Math.min(100, (currentTime / duration) * 100)) : 0;

  // 컨트롤 공유 (t0v renderControls(dark) 선례 — 로직 중복 0). dark=true 는
  // 가로 전체화면: 어두운 배경 위 색·배율만 토큰 분기.
  const renderControls = (dark: boolean) => (
    <View style={styles.controls}>
      <Pressable
        onPress={togglePlay}
        accessibilityRole="button"
        accessibilityLabel={playing ? '일시정지' : '재생'}
        hitSlop={8}
        style={styles.playBtn}
      >
        <Ionicons
          name={playing ? 'pause' : 'play'}
          size={12}
          color={colors.textWhite}
        />
      </Pressable>
      <View style={styles.timeline}>
        {/* 260909-ji1 — 번호 틱(①②③) 줄을 뺐다. 시안 2 의 진행바는 트랙 하나뿐이다.
            그 순간으로 가는 길은 아래 감점 목록의 행이 대신한다. */}
        <View
          style={styles.timelineTrack}
          onLayout={dark ? onFsTrackLayout : onTrackLayout}
          onTouchStart={() => {
            draggingFsRef.current = dark;
          }}
          {...panResponder.panHandlers}
        >
          <View style={styles.timelineRail} pointerEvents="none" />
          <View
            style={[styles.timelineFill, { width: `${progressPct}%` }]}
            pointerEvents="none"
          />
          <View
            style={[styles.timelineThumb, { left: `${progressPct}%` }]}
            pointerEvents="none"
          />
        </View>
        <Text style={[styles.timeText, dark && styles.timeTextDark]} numberOfLines={1}>
          {`${fmtTimeDecimal(currentTime)} / ${fmtTime(duration)}`}
        </Text>
      </View>
    </View>
  );

  return (
    <View style={styles.card}>
      <View style={styles.frame}>
        {url ? (
          <>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="재생 또는 일시정지"
              onPress={togglePlay}
              style={styles.videoBox}
            >
              <VideoView
                player={player}
                style={styles.video}
                // 두 패널 합성 mp4 — 오버레이·동기 로직 없이 재생만.
                // nativeControls=false: 자동 숨김 컨트롤이 아래 커스텀 컨트롤과
                // 이중으로 겹쳐 "조작 UI가 이상하다"의 원인이었다 (260809-jnb).
                nativeControls={false}
                contentFit="contain"
                allowsPictureInPicture={false}
                // iOS 가 일시정지 프레임에 라이브 텍스트(스캔) 단추를 얹는다 —
                // 시안에 없는 물건이고 영상 우하단을 가린다 (belle 09-09 시뮬).
                allowsVideoFrameAnalysis={false}
                accessibilityLabel="동작 비교 영상"
              />
            </Pressable>
            {/* 260909-ji1 — 시안 2 의 역할 라벨. 합성 mp4 는 좌=학생 / 우=기준으로
                구워져 있으므로(contract.md §12.9) 그 위에 알약을 얹는다. 이게 없으면
                어느 쪽이 자기 영상인지 알 수 없다 — 듀얼 플레이어 가지에는 있었는데
                이 가지에만 없었다. */}
            <View style={[styles.slotPill, styles.slotPillLeft]} pointerEvents="none">
              <Text style={styles.slotPillText} numberOfLines={1}>
                {leftLabel}
              </Text>
            </View>
            {rightLabel ? (
              <View
                style={[styles.slotPill, styles.slotPillRight]}
                pointerEvents="none"
              >
                <Text style={styles.slotPillText} numberOfLines={1}>
                  {rightLabel}
                </Text>
              </View>
            ) : null}
          </>
        ) : (
          <View style={styles.placeholder}>
            <Text style={styles.placeholderText}>비교 영상을 불러오고 있어요</Text>
          </View>
        )}
      </View>
      {url ? <View style={styles.controlsWrap}>{renderControls(false)}</View> : null}
      {/* 시안 2 의 옵션 칩 행 — 0.5배속 · 관절선(표시 없는 판이 있을 때만) · 음성 ·
          전체화면. 영상을 탭하면 재생/일시정지다. belle 09-09 요구대로 작게 한 줄. */}
      {url ? (
        <View style={styles.optionRow}>
          <Pressable
            onPress={() => setSlowMotion((v) => !v)}
            accessibilityRole="button"
            accessibilityState={{ selected: slowMotion }}
            accessibilityLabel="0.5배속으로 보기"
            hitSlop={8}
            style={[styles.optionPill, slowMotion ? styles.optionPillOn : null]}
          >
            <Text
              style={[
                styles.optionPillText,
                slowMotion ? styles.optionPillTextOn : null,
              ]}
            >
              0.5배속
            </Text>
          </Pressable>
          {urlPlain ? (
            // 교체가 끝나기 전에 또 누르면 절차가 겹친다 — 세대 ref 가 옛 콜백을
            // 무효화하긴 하지만, 잠금이 **눈에 보여야** belle 이 "안 눌린다"로
            // 읽지 않는다 (opacity 로 잠긴 상태를 드러낸다).
            <Pressable
              onPress={() => setOverlayOn((v) => !v)}
              disabled={swapping}
              accessibilityRole="switch"
              accessibilityLabel="관절선 표시"
              accessibilityState={{ checked: overlayOn, disabled: swapping }}
              hitSlop={10}
              style={[
                styles.optionPill,
                overlayOn ? styles.optionPillOn : null,
                swapping ? styles.optionPillBusy : null,
              ]}
            >
              <Text
                style={[
                  styles.optionPillText,
                  overlayOn ? styles.optionPillTextOn : null,
                ]}
              >
                관절선
              </Text>
            </Pressable>
          ) : null}
          <Pressable
            onPress={() => setAudioOn((v) => !v)}
            accessibilityRole="switch"
            accessibilityLabel="재생 중 음성 안내"
            accessibilityState={{ checked: audioOn }}
            hitSlop={10}
            style={[styles.optionPill, audioOn ? styles.optionPillOn : null]}
          >
            <Ionicons
              name={audioOn ? 'volume-high' : 'volume-mute'}
              size={12}
              color={audioOn ? colors.brand : colors.textMid}
            />
            <Text
              style={[styles.optionPillText, audioOn ? styles.optionPillTextOn : null]}
            >
              음성
            </Text>
          </Pressable>
          <Pressable
            onPress={openFullscreen}
            accessibilityRole="button"
            accessibilityLabel="가로 전체화면으로 크게 보기"
            hitSlop={10}
            style={styles.optionPill}
          >
            <Ionicons name="expand" size={12} color={colors.textMid} />
            <Text style={styles.optionPillText}>전체화면</Text>
          </Pressable>
        </View>
      ) : null}
      {/* 260909-ji1 — 시안 2 는 감점 목록이 영상 카드 **안**, 옵션 행 바로 아래다.
          듀얼 플레이어 가지에는 이미 그렇게 들어가 있었는데 이 가지에만 없었다
          (belle 09-09: "시안이 있는데도 왜 삭제만하고 반영을 안해"). */}
      {/* URL 도착 전에는 목록도 함께 늦춘다 — 컨트롤·칩만 늦게 나오면 URL 이 붙는
          순간 목록이 그 높이만큼 아래로 튄다 (260909-ji1). */}
      {url ? renderBelowControls?.({ seekToRecord, activeRid, outSecOf }) : null}

      {/* 가로 전체화면 — 260702-t0v 90° 회전 Modal 패턴 (portrait 고정 유지).
          같은 player 인스턴스에 두 번째 VideoView attach — 재생 위치·상태 공유
          (동기 로직 0). 탭 = 재생/일시정지 토글, 우상단 닫기, 하단 컨트롤 공유.
          belle 09-07 — 영상 표면은 ZoomPinchLayer 가 감싼다(손가락 확대 + 탭 멈춤). */}
      <Modal
        visible={fullscreen}
        animationType="fade"
        statusBarTranslucent
        supportedOrientations={['portrait']}
        onRequestClose={closeFullscreen}
      >
        <StatusBar hidden />
        <View style={styles.fsRoot}>
          <View
            style={[
              styles.fsRotated,
              {
                width: fsLong,
                height: fsShort,
                left: (fsShort - fsLong) / 2,
                top: (fsLong - fsShort) / 2,
              },
            ]}
          >
            {/* 종전의 Pressable 래퍼는 걷어냈다 — 같은 표면이 핀치·팬도 받아야
                하는데 Pressable 과 PanResponder 가 responder 를 두고 다투면 확대
                도중 탭이 끼어들어 재생이 토글된다. 탭 멈춤은 ZoomPinchLayer 의
                onTap(움직이지 않은 짧은 접촉)으로 옮겼고, 보조기술용 재생/일시정지
                버튼은 아래 fsControls 안에 accessibilityRole="button" 으로 이미
                따로 있다(중복 표면을 잃은 것이지 기능을 잃은 것이 아니다). */}
            <View style={styles.fsVideoWrap} onLayout={onFsVideoLayout}>
              {fsBox.w > 0 && fsBox.h > 0 ? (
                <ZoomPinchLayer
                  boxW={fsBox.w}
                  boxH={fsBox.h}
                  state={zoom}
                  onChange={setZoom}
                  onTap={() => {
                    dismissPinchHint();
                    togglePlay();
                  }}
                  onPinchStart={dismissPinchHint}
                  style={styles.fsVideoBox}
                  accessibilityLabel="재생 또는 일시정지"
                >
                  <VideoView
                    player={player}
                    style={styles.fsVideo}
                    contentFit="contain"
                    nativeControls={false}
                    allowsVideoFrameAnalysis={false}
                    // allowsFullscreen 은 expo-video 에서 deprecated(경고 발생)이고,
                    // nativeControls=false 면 전체화면 진입 UI 자체가 없어 무의미하다.
                    allowsPictureInPicture={false}
                    accessibilityLabel="동작 비교 영상 (가로)"
                  />
                </ZoomPinchLayer>
              ) : null}
            </View>
            <View style={styles.fsControls}>{renderControls(true)}</View>
            {/* belle 09-07 — 첫 진입 1회 안내. 손가락 확대는 화면에 단서가 없는
                제스처라 처음 한 번은 말해 준다. 핀치·탭·4초 중 무엇이든 오면
                사라지고 다시 뜨지 않는다(듀얼 플레이어와 같은 1회 플래그). */}
            {pinchHintVisible ? (
              <View style={styles.fsPinchHintWrap} pointerEvents="box-none">
                <Pressable
                  onPress={dismissPinchHint}
                  accessibilityRole="button"
                  accessibilityLabel="확대 안내 닫기"
                  hitSlop={8}
                  style={styles.fsPinchHintPill}
                >
                  <Ionicons name="resize" size={12} color={colors.textWhite} />
                  <Text style={styles.fsPinchHintText}>
                    두 손가락으로 벌리면 크게 보여요
                  </Text>
                </Pressable>
              </View>
            ) : null}
            {/* belle 09-07 — 벌린 뒤 원래 프레이밍(1.0)으로 되돌리는 길. 닫기
                버튼 왼쪽에 두어 우상단 두 손잡이가 겹치지 않는다. */}
            {zoomTouched ? (
              <Pressable
                onPress={() => setZoom(freshRenderedZoom())}
                accessibilityRole="button"
                accessibilityLabel="확대 원래대로"
                hitSlop={8}
                style={styles.fsZoomResetPill}
              >
                <Ionicons name="contract" size={12} color={colors.textWhite} />
                <Text style={styles.fsZoomResetText}>원래대로</Text>
              </Pressable>
            ) : null}
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="가로 보기 닫기"
              hitSlop={12}
              onPress={closeFullscreen}
              style={styles.fsCloseBtn}
            >
              <Ionicons name="close" size={22} color={colors.textWhite} />
            </Pressable>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  // 260909-ji1 — 시안 2 의 흰 카드. 듀얼 플레이어 가지(VideoCompare.card)와 같은
  // 규약이라 두 가지가 같은 화면으로 읽힌다.
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.resultVideoCard,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.resultCardBorder,
    padding: spacing.cardPadding,
    gap: 12,
    width: '100%',
  },
  // 시안 2 — 영상 블록은 카드 안쪽 좌우 20.9pt.
  slotPill: {
    position: 'absolute',
    top: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
  },
  slotPillLeft: { left: 13.83, backgroundColor: colors.brand },
  slotPillRight: { right: 13.77, backgroundColor: colors.videoBg },
  slotPillText: {
    ...typography.captionSmall,
    fontWeight: '700',
    color: colors.textWhite,
  },
  optionRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    flexWrap: 'wrap',
    gap: 5,
  },
  // 듀얼 플레이어 가지와 같은 크기·규약 (VideoCompare.optionPill 주석에 근거).
  optionPill: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 3,
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: radius.button,
    borderWidth: 1,
    borderColor: colors.divider,
    backgroundColor: colors.cardBg,
  },
  optionPillOn: { borderColor: colors.brand, backgroundColor: colors.resultChipBg },
  // 소스 교체 중 잠금 표시 — 색을 새로 만들지 않고 불투명도만 낮춘다
  // (design.md 토큰 추가 없이 "지금은 못 누른다"만 전한다).
  optionPillBusy: { opacity: 0.6 },
  optionPillText: { ...typography.caption, color: colors.textMid },
  optionPillTextOn: { color: colors.brand },
  // 260909-ji1 — 블록 비는 시안 2 실측(276.04 x 177.90 = 1.5517). 듀얼 플레이어
  // 가지와 같은 값이라 두 가지가 같은 크기로 보인다.
  frame: {
    width: '100%',
    marginHorizontal: compareCardControls.blockInset - spacing.cardPadding,
    borderRadius: 12,
    overflow: 'hidden',
    justifyContent: 'center',
    // 영상 카드 배경 — design.md §5-1 다크 예외 토큰 (영상 콘텐츠 자체의 어두움).
    backgroundColor: colors.videoBg,
    aspectRatio: 276.04 / 177.9,
  },
  // 합성 mp4 는 세로 패널 2장 나란히(약 1224x1080)라 시안 블록보다 세로로 길다.
  // 그 비율 그대로의 박스를 블록 안에 두고 폭을 100% 로 편 뒤 블록이 위아래를 자른다
  // — `contain` 으로 두면 좌우에 띠가 생겨 시안처럼 꽉 차지 않는다. 듀얼 플레이어
  // 가지(VideoCompare.slotVideoBox)와 같은 수법.
  videoBox: {
    width: '100%',
    aspectRatio: 1224 / 1080,
  },
  video: {
    width: '100%',
    height: '100%',
  },
  placeholder: {
    width: '100%',
    aspectRatio: 1224 / 1080,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.cardPadding,
  },
  placeholderText: {
    ...typography.caption,
    color: colors.textWhite,
    textAlign: 'center',
  },
  // ── 컨트롤 (VideoCompare 세트 이식 — 정렬 미세조정 버튼만 제외) ────────────
  // 260909-ji1 — 시안 2 컨트롤 치수. 듀얼 플레이어와 같은 값이라 두 경로가
  // 같은 화면으로 읽힌다 (재생 원 22.4 · 트랙 4.8 · 행 좌우 인셋 42.8).
  controlsWrap: {
    paddingTop: 10,
  },
  controls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginHorizontal: compareCardControls.controlsInset - spacing.cardPadding,
  },
  playBtn: {
    width: compareCardControls.playDiameter,
    height: compareCardControls.playDiameter,
    borderRadius: compareCardControls.playDiameter / 2,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // 시안은 [재생] [트랙] [시간] 이 **한 줄**이다. gap 세로 배치면 시간이 아래로
  // 떨어져 시안과 다른 조판이 된다 (260909-ji1).
  timeline: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  timelineTrack: {
    flex: 1,
    height: 14,
    justifyContent: 'center',
  },
  timelineRail: {
    position: 'absolute',
    top: (compareCardControls.trackRowHeight - compareCardControls.trackHeight) / 2,
    left: 0,
    right: 0,
    height: compareCardControls.trackHeight,
    backgroundColor: colors.divider,
    borderRadius: 2,
  },
  timelineFill: {
    position: 'absolute',
    top: (compareCardControls.trackRowHeight - compareCardControls.trackHeight) / 2,
    left: 0,
    height: compareCardControls.trackHeight,
    backgroundColor: colors.brand,
    borderRadius: 2,
  },
  timelineThumb: {
    position: 'absolute',
    top: (14 - THUMB_DIAMETER) / 2,
    width: THUMB_DIAMETER,
    height: THUMB_DIAMETER,
    borderRadius: THUMB_DIAMETER / 2,
    backgroundColor: colors.brand,
    marginLeft: -THUMB_DIAMETER / 2,
    borderWidth: 2,
    borderColor: colors.cardBg,
  },
  timeText: {
    ...typography.captionSmall,
    color: colors.textSecondary,
  },
  timeTextDark: {
    color: colors.textWhite,
    fontSize: typography.captionSmall.fontSize * FULLSCREEN_TEXT_SCALE,
    lineHeight: typography.captionSmall.fontSize * FULLSCREEN_TEXT_SCALE * 1.3,
  },
  // ── 가로 전체화면 (t0v 90° 회전 패턴) ──────────────────────────────────
  fsRoot: {
    flex: 1,
    backgroundColor: colors.videoBg,
  },
  fsRotated: {
    position: 'absolute',
    transform: [{ rotate: '90deg' }],
    paddingVertical: 6,
  },
  fsVideoWrap: {
    flex: 1,
  },
  // belle 09-07 — ZoomPinchLayer 의 클리핑 래퍼에 얹는 배경. overflow:'hidden' 은
  // 레이어가 갖고 있으므로 여기서 덮지 않는다 (색만 호출측 몫 — 그 파일에 색 0).
  fsVideoBox: {
    backgroundColor: colors.videoBg,
  },
  fsVideo: {
    // 확대 박스(ZoomPinchLayer 내부 absolute, 숫자 치수)를 채운다 — 퍼센트의
    // 기준이 그 숫자 박스라 회전 컨테이너의 퍼센트 축소 함정에 걸리지 않는다.
    width: '100%',
    height: '100%',
  },
  // belle 09-07 — 첫 진입 안내 pill / '원래대로' pill. 문법은 듀얼 플레이어와
  // 동일(videoBg + textWhite + radius.button + Ionicons — 신규 색 0).
  fsPinchHintWrap: {
    position: 'absolute',
    top: 56,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  fsPinchHintPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: radius.button,
    backgroundColor: colors.videoBg,
  },
  fsPinchHintText: {
    ...typography.captionSmall,
    fontSize: typography.captionSmall.fontSize * FULLSCREEN_TEXT_SCALE,
    color: colors.textWhite,
    fontWeight: '700',
  },
  fsZoomResetPill: {
    position: 'absolute',
    top: 10,
    // 닫기 버튼(right 12, padding 8 × 2 + icon 22 = 38) 왼쪽에 8 간격으로.
    right: 12 + 38 + 8,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: radius.button,
    backgroundColor: colors.videoBg,
  },
  fsZoomResetText: {
    ...typography.captionSmall,
    fontSize: typography.captionSmall.fontSize * FULLSCREEN_TEXT_SCALE,
    color: colors.textWhite,
    fontWeight: '700',
  },
  fsControls: {
    paddingHorizontal: 16,
    paddingTop: 6,
  },
  fsCloseBtn: {
    position: 'absolute',
    top: 10,
    right: 12,
    padding: 8,
    borderRadius: radius.listItem,
    backgroundColor: colors.brandOverlay,
  },
});
