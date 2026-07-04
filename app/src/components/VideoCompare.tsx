// 분석 결과 동작 비교 — 좌(내 영상) / 우(기준) 나란히 + 동기 재생.
//
// 영상 URL 이 비어 있을 때도 같은 레이아웃의 자리표시를 보여줘서, #7-follow 에서
// 실 영상이 들어오면 그대로 슬롯에 들어간다 ([[sim-scaffold-not-decorate]]).
//
// 동기 재생: 단일 Play/Pause 가 양 플레이어를 동시에 제어. 타임라인은 좌측을
// 기준으로 표시하되 seek 는 양쪽 동일 시각으로 보낸다. 영상 길이가 서로 달라도
// 짧은 쪽이 끝나면 일시정지(루프 X) — 비교 시 동기 어긋남 방지.

import { Ionicons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';
import { useVideoPlayer, VideoView, type VideoPlayer } from 'expo-video';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  type LayoutChangeEvent,
  Modal,
  PanResponder,
  Pressable,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import { colors, layout, radius, spacing, typography } from '../theme';

type SlotProps = {
  label: string;
  url?: string;
  player: VideoPlayer | null;
  /**
   * Phase 12 신설 (Plan 12-02 T4 / R7 render prop).
   * 영상 위 absolute overlay layer (KeypointOverlay 등). pointerEvents 'none'.
   * VideoCompare 가 player lifecycle 안에서 callback 호출 — caller (result.tsx)
   * 가 player state 별도 관리 X (R7 dual-state pattern 차단).
   * Wave 2 가 KeypointOverlay 내부 useEvent(player, 'timeUpdate') 박제 site.
   *
   * quick-260702-t0v — 2번째 인자 opts.sizeScale 확장. 세로 카드는 opts 생략
   * (기존 렌더 무회귀), 가로 전체화면 뷰어가 { sizeScale: 2.0 } 전달.
   */
  overlay?: OverlayRenderProp;
};

// quick-260702-t0v — overlay render prop 단일 타입 (VideoCompareProps + SlotProps 공유).
type OverlayRenderProp = (
  player: VideoPlayer | null,
  opts?: { sizeScale?: number },
) => React.ReactNode;

function fmtTime(s: number): string {
  if (!isFinite(s) || s < 0) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

// Phase 12 후속 B — currentTime 은 0.1s 정밀 표시. belle 요구: "0.0초 단위".
function fmtTimeDecimal(s: number): string {
  if (!isFinite(s) || s < 0) return '0:00.0';
  const m = Math.floor(s / 60);
  const sec = s - m * 60;
  return `${m}:${sec.toFixed(1).padStart(4, '0')}`;
}

function VideoSlot({ label, url, player, overlay }: SlotProps) {
  return (
    <View style={styles.slot}>
      <View style={styles.slotFrame}>
        {url && player ? (
          <>
            <VideoView
              player={player}
              style={styles.video}
              contentFit="contain"
              nativeControls={false}
              allowsFullscreen={false}
              allowsPictureInPicture={false}
            />
            {overlay && (
              <View style={styles.overlayContainer} pointerEvents="none">
                {overlay(player)}
              </View>
            )}
          </>
        ) : (
          <View style={styles.slotEmpty}>
            <Ionicons
              name="videocam-outline"
              size={22}
              color={colors.textDisabled}
            />
            <Text style={styles.slotEmptyText}>준비 중</Text>
          </View>
        )}
      </View>
      <Text style={styles.slotLabel}>{label}</Text>
    </View>
  );
}

export type VideoCompareProps = {
  leftLabel: string;
  rightLabel: string;
  leftUrl?: string;
  rightUrl?: string;
  /**
   * Phase 12 신설 (Plan 12-02 T4) — 영상 위 absolute layer (KeypointOverlay 등).
   * pointerEvents 'none'. R7 render prop — result.tsx 가 player state 들지 않고
   * VideoCompare 가 자기 player lifecycle 안에서 callback 호출. Wave 2 가
   * KeypointOverlay 내부 useEvent(player, 'timeUpdate') 박제 site (B3 iter-4 정합).
   *
   * quick-260702-t0v — 2번째 인자 opts.sizeScale 확장 (전체화면 뷰어가 2.0 전달).
   */
  leftOverlay?: OverlayRenderProp;
  rightOverlay?: OverlayRenderProp;
  /**
   * quick-260702-t0v — 가로 전체화면 뷰어 상단 bar 우측 슬롯 (닫기 버튼 왼쪽).
   * result.tsx 가 KeypointOverlayToggle 을 전달 → 전체화면에서도 오버레이 토글
   * 유지 (state 단일 출처 = caller, 토글 시 render prop 재실행으로 즉시 반영).
   */
  fullscreenHeaderExtra?: React.ReactNode;
};

// UAT 4차 (Build 14) finding 1+2 drift/replay 보정 상수 — Build 16 (iter-2).
//
// Build 15 → Build 16 변경 (UAT 5차에서 drift 1-2s 잔존 + 반복 재생 멈춤 + 랜덤 버벅):
//   - tick interval 250ms → 100ms — drift 누적 전 빨리 잡음
//   - DRIFT_CORRECT_THRESHOLD_S 0.3 → 0.2 — 더 일찍 보정 진입
//   - hysteresis (DRIFT_RESET_THRESHOLD_S + correctingDriftRef) 제거 —
//     매 tick drift > 0.2 면 즉시 보정 (stutter 위험 < 동기화 우선)
//   - REPLAY_SEEK_DELAY_MS 60 → 200 — 정은지 영상 S3 buffer reset 충분 시간
//   - togglePlay 시작 시 강제 sync — play() 전 둘이 currentTime 다르면 작은 값
//     으로 맞춤. 초기 drift 0 보장.
const TICK_INTERVAL_MS = 100;
const DRIFT_CORRECT_THRESHOLD_S = 0.2;
const REPLAY_SEEK_DELAY_MS = 200;
const START_SYNC_THRESHOLD_S = 0.05;

// Phase 12 후속 B — VideoCompare scrub/step 컨트롤.
//   STEP_SECONDS: ← / → 버튼 한 번 = 0.1s 이동 (belle "0.0초 단위" 요구).
//   THUMB_RADIUS: timeline 위 drag 손잡이 hit area 반지름. 트랙 두께 4 + 손잡이 12.
const STEP_SECONDS = 0.1;
const THUMB_DIAMETER = 14;

// quick-260702-t0v (belle TestFlight #27 — 각도 라벨 가독) — 전체화면 오버레이 배율.
// KeypointOverlay 는 viewBox 정규화 구조라 라벨 유효 크기 = 14 × 렌더높이/1280.
// 세로 카드(높이 ~290pt) → 가로 전체화면(~393pt) 전환만으로는 ~1.35배뿐이라
// 판독 불가 잔존 → sizeScale 2.0 병행. belle 실기기 확인 후 미세조정 가능하도록
// 상수화 (부족하면 상향).
const FULLSCREEN_OVERLAY_SCALE = 2.0;

export function VideoCompare({
  leftLabel,
  rightLabel,
  leftUrl,
  rightUrl,
  leftOverlay,
  rightOverlay,
  fullscreenHeaderExtra,
}: VideoCompareProps) {
  // expo-video: source 가 null 이면 자원만 잡고 재생 가능 상태 아님 — 훅 순서를
  // 깨지 않으면서 빈 URL 도 안전. 음소거 + 루프 끄기(비교에 방해 안 되게).
  //
  // Phase 12 Wave 2 (Plan 12-03 T1): timeUpdateEventInterval=0.033 (~30fps).
  // KeypointOverlay 가 useEvent(player, 'timeUpdate') 로 native emit 구독 →
  // frame index 자동 산출. 기존 250ms 폴링(타임라인 label) 과 공존 — 타임라인은
  // 250ms / 오버레이는 33ms 분기 (R10 iter-2 정합, D-12-C5).
  const leftPlayer = useVideoPlayer(leftUrl ?? null, (p) => {
    p.muted = true;
    p.loop = false;
    p.timeUpdateEventInterval = 0.033;
  });
  const rightPlayer = useVideoPlayer(rightUrl ?? null, (p) => {
    p.muted = true;
    p.loop = false;
    p.timeUpdateEventInterval = 0.033;
  });

  const hasLeft = !!leftUrl;
  const hasRight = !!rightUrl;
  const hasAny = hasLeft || hasRight;

  // currentTime 폴링 — expo-video 는 prop 변경 이벤트가 따로 없음. 재생 중에만
  // 250ms 마다 갱신 → 타임라인 따라잡기. 정지 상태면 폴링 멈춰 배터리 보호.
  //
  // 12-deferred §12-C — 두 영상 native duration / fps 가 다르면 단일 타임라인이
  // drift 시각화 가림. left/right currentTime + duration 분리 상태로 저장 → 시간
  // 라벨 두 개 동시 표시 (progress bar 는 짧은 쪽 기준 단일 유지).
  const [leftCurrent, setLeftCurrent] = useState(0);
  const [leftDuration, setLeftDuration] = useState(0);
  const [rightCurrent, setRightCurrent] = useState(0);
  const [rightDuration, setRightDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Build 16 (iter-2): hysteresis 제거. UAT 5차에서 보정 후 0.15 미만 안 들어와
  // 다음 보정 못 하는 사이 drift 1-2s 누적 finding. 매 tick drift > 0.2 면 즉시
  // 보정 (stutter 위험 < 동기화 우선). 보정 직후 100ms 안에 또 보정 진입은 fine.

  // Phase 12 후속 B — scrub 중일 때 drift correction 우회. PanResponder 가
  // 양쪽 currentTime 을 동일 값으로 setter — 다음 tick 의 drift > 0.2 가짜로
  // 잡혀 또 seek 보내면 stutter. drag 중에는 보정 skip.
  const scrubbingRef = useRef(false);
  const wasPlayingBeforeScrubRef = useRef(false);
  const trackWidthRef = useRef(0);

  // quick-260702-t0v (belle TestFlight #27 — 각도 라벨 가독) — 가로 전체화면 뷰어.
  // portrait 고정(app.json orientation) 유지 + Modal 안 뷰 90° 회전으로 가로
  // 레이아웃 시뮬레이트 (expo-screen-orientation = native 모듈 추가라 금지, OTA 전제).
  // 같은 leftPlayer/rightPlayer 인스턴스에 두 번째 VideoView 를 attach → 재생
  // 위치/상태 연속, drift 보정 tick·togglePlay·seekBoth 가 양 레이아웃을 그대로 제어.
  const [fullscreen, setFullscreen] = useState(false);
  // 전체화면 타임라인 track 은 폭이 다름 — scrubAtX 가 활성 레이아웃의 폭을 읽도록
  // ref 분리 (portrait track 은 Modal 뒤에 mount 유지라 onLayout 재발화 없음).
  const fullscreenRef = useRef(false);
  const fsTrackWidthRef = useRef(0);
  const { width: winW, height: winH } = useWindowDimensions();
  const openFullscreen = () => {
    fullscreenRef.current = true;
    setFullscreen(true);
  };
  const closeFullscreen = () => {
    fullscreenRef.current = false;
    setFullscreen(false);
  };

  useEffect(() => {
    if (!hasAny) return;
    const tick = () => {
      const cL = leftPlayer?.currentTime ?? 0;
      const cR = rightPlayer?.currentTime ?? 0;
      const dL = leftPlayer?.duration ?? 0;
      const dR = rightPlayer?.duration ?? 0;
      setLeftCurrent(cL);
      setRightCurrent(cR);
      setLeftDuration(dL);
      setRightDuration(dR);
      // 비교 기준 길이 = 둘 중 짧은 쪽. 짧은 쪽 끝나면 함께 멈추도록.
      const shorter =
        dL > 0 && dR > 0 ? Math.min(dL, dR) : Math.max(dL, dR);
      const ref = hasLeft ? leftPlayer : rightPlayer;
      const bothPlaying = !!leftPlayer?.playing && !!rightPlayer?.playing;
      setPlaying(!!ref?.playing);

      // UAT 4차 Finding 1 — drift 보정 (Build 16 iter-2).
      //   tick 100ms 마다 매번 drift > 0.2s 면 즉시 보정. hysteresis 없음.
      //   조건: 둘 다 재생 중 + 둘 다 native duration 산정됨 + 끝부분 진입 전.
      //   Phase 12 후속 B — scrub 중에는 보정 skip (PanResponder 가 동시 seek 한
      //   상태에서 또 보정 들어가면 stutter).
      if (
        hasLeft &&
        hasRight &&
        bothPlaying &&
        !scrubbingRef.current &&
        dL > 0 &&
        dR > 0 &&
        shorter > 0 &&
        Math.max(cL, cR) < shorter - 0.1 &&
        leftPlayer &&
        rightPlayer
      ) {
        const drift = Math.abs(cL - cR);
        if (drift > DRIFT_CORRECT_THRESHOLD_S) {
          // 느린 쪽 시각을 authoritative time 으로 사용 (빠른 쪽 back-seek).
          const slowerTime = Math.min(cL, cR);
          if (cL > cR) {
            leftPlayer.currentTime = slowerTime;
          } else {
            rightPlayer.currentTime = slowerTime;
          }
        }
      }

      // UAT 4차 Finding 2 — 짧은 쪽 끝났는데 다른 쪽이 계속 가는 상황 방지.
      //   이전 (Build 14): OR (`cL >= shorter || cR >= shorter`) — 빠른 쪽이
      //   먼저 도달하면 양쪽 pause → 느린 쪽은 실 native duration 못 채운 채
      //   pause, 다음 replay 시 빠른 쪽은 이미 자기 native end 넘어 진행 X.
      //   현재 (Build 15): AND-like (Math.min 둘 다 도달) — drift 보정 위와 결합.
      //   드물게 둘 중 한 쪽만 end 도달하면 보정 fail 케이스 → safety net 으로
      //   max 가 자기 native duration 도달 시도 같이 pause (둘 다 native end).
      const minReachedShortEnd = shorter > 0 && Math.min(cL, cR) >= shorter - 0.05;
      const leftReachedOwnEnd = dL > 0 && cL >= dL - 0.05;
      const rightReachedOwnEnd = dR > 0 && cR >= dR - 0.05;
      const bothReachedOwnEnd =
        (!hasLeft || leftReachedOwnEnd) && (!hasRight || rightReachedOwnEnd);
      if (minReachedShortEnd || bothReachedOwnEnd) {
        leftPlayer?.pause();
        rightPlayer?.pause();
      }
    };
    tick();
    tickRef.current = setInterval(tick, TICK_INTERVAL_MS);
    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
      tickRef.current = null;
    };
  }, [hasAny, hasLeft, hasRight, leftPlayer, rightPlayer]);

  // progress bar / restart 등 단일 기준 값 — 짧은 쪽 기준 (기존 로직 보존).
  const current = hasLeft ? leftCurrent : rightCurrent;
  const duration =
    hasLeft && hasRight
      ? leftDuration > 0 && rightDuration > 0
        ? Math.min(leftDuration, rightDuration)
        : Math.max(leftDuration, rightDuration)
      : hasLeft
        ? leftDuration
        : rightDuration;

  const togglePlay = () => {
    if (!hasAny) return;
    if (playing) {
      leftPlayer?.pause();
      rightPlayer?.pause();
      setPlaying(false);
    } else {
      // UAT 4차 Finding 2 — 끝난 상태에서 다시 재생 시 정은지 영상 멈춤 finding.
      //   이전 (Build 14): `current` (= leftCurrent) 한쪽만 검사 → 우측이 자기
      //   native end 넘어가 있어도 reset 발동 안 함. 또한 seek = 0 직후 즉시
      //   play() → expo-video 가 seek 적용 전에 play 호출 받아 우측 정지.
      //   현재 (Build 15):
      //     1) 끝 판정 = Math.max(leftCurrent, rightCurrent) — 어느 한쪽이라도
      //        end 도달했으면 둘 다 reset.
      //     2) reset 시 explicit seek=0 + REPLAY_SEEK_DELAY_MS 후 play() — seek
      //        완료 보장 (60ms 는 한 frame 보다 살짝 길게).
      //     3) drift 보정 상태 reset (`correctingDriftRef`).
      const maxCurrent = Math.max(leftCurrent, rightCurrent);
      const isAtEnd = duration > 0 && maxCurrent >= duration - 0.05;
      // Build 16 iter-2: 시작/재시작 강제 sync — play() 호출 전 둘이 currentTime
      // 다르면 작은 값으로 맞춤. 초기 drift 0 보장.
      const drift = Math.abs(leftCurrent - rightCurrent);
      const needsStartSync =
        hasLeft && hasRight && drift > START_SYNC_THRESHOLD_S;
      if (isAtEnd) {
        if (leftPlayer) leftPlayer.currentTime = 0;
        if (rightPlayer) rightPlayer.currentTime = 0;
        // Build 16: seek 적용 시간 확보 후 play (60→200ms — 정은지 S3 buffer reset).
        setTimeout(() => {
          leftPlayer?.play();
          rightPlayer?.play();
          setPlaying(true);
        }, REPLAY_SEEK_DELAY_MS);
      } else if (needsStartSync && leftPlayer && rightPlayer) {
        // 중간 정지 후 다시 재생 시 두 player drift 가 있으면 동기화 먼저.
        const slowerTime = Math.min(leftCurrent, rightCurrent);
        leftPlayer.currentTime = slowerTime;
        rightPlayer.currentTime = slowerTime;
        setTimeout(() => {
          leftPlayer.play();
          rightPlayer.play();
          setPlaying(true);
        }, REPLAY_SEEK_DELAY_MS);
      } else {
        leftPlayer?.play();
        rightPlayer?.play();
        setPlaying(true);
      }
    }
  };

  const restart = () => {
    if (!hasAny) return;
    if (leftPlayer) leftPlayer.currentTime = 0;
    if (rightPlayer) rightPlayer.currentTime = 0;
    setLeftCurrent(0);
    setRightCurrent(0);
  };

  // Phase 12 후속 B — 양쪽 동시 seek (drift 0 보장). target 은 짧은 쪽 duration
  // 으로 clamp — 비교 기준 길이를 넘어가지 않게.
  const seekBoth = useCallback(
    (target: number) => {
      const dL = leftPlayer?.duration ?? 0;
      const dR = rightPlayer?.duration ?? 0;
      const maxAllowed =
        hasLeft && hasRight && dL > 0 && dR > 0
          ? Math.min(dL, dR)
          : hasLeft
            ? dL
            : dR;
      const safe = Math.max(0, Math.min(maxAllowed > 0 ? maxAllowed : target, target));
      if (leftPlayer) leftPlayer.currentTime = safe;
      if (rightPlayer) rightPlayer.currentTime = safe;
      // 폴링은 다음 tick 까지 0~100ms 지연 — 즉시 라벨 갱신.
      if (hasLeft) setLeftCurrent(safe);
      if (hasRight) setRightCurrent(safe);
    },
    [hasLeft, hasRight, leftPlayer, rightPlayer],
  );

  // 0.1s 앞/뒤 step. 현재 시각 = 둘 중 작은 값 (slower side 가 진짜 sync 위치).
  const stepBy = useCallback(
    (deltaS: number) => {
      if (!hasAny) return;
      const base =
        hasLeft && hasRight
          ? Math.min(leftCurrent, rightCurrent)
          : hasLeft
            ? leftCurrent
            : rightCurrent;
      seekBoth(base + deltaS);
    },
    [hasAny, hasLeft, hasRight, leftCurrent, rightCurrent, seekBoth],
  );

  // PanResponder — timeline track drag = scrub. locationX 가 track element 내부
  // 좌표를 반환 → trackWidthRef 측정값과 비율 계산. drag 중 재생 중이면 pause,
  // release 시 wasPlaying 복원.
  const onTrackLayout = useCallback((e: LayoutChangeEvent) => {
    trackWidthRef.current = e.nativeEvent.layout.width;
  }, []);

  // quick-260702-t0v — 전체화면 track 폭 분리 측정 (회전 컨테이너 안 폭이 다름).
  const onFsTrackLayout = useCallback((e: LayoutChangeEvent) => {
    fsTrackWidthRef.current = e.nativeEvent.layout.width;
  }, []);

  const scrubAtX = useCallback(
    (x: number) => {
      // quick-260702-t0v — 활성 레이아웃(세로/전체화면)의 track 폭 사용.
      // PanResponder 의 locationX 는 RN 이 transform 반영 로컬 좌표로 매핑하므로
      // 회전 뷰에서도 그대로 유효.
      const w = fullscreenRef.current
        ? fsTrackWidthRef.current
        : trackWidthRef.current;
      if (w <= 0 || duration <= 0) return;
      const ratio = Math.max(0, Math.min(1, x / w));
      seekBoth(duration * ratio);
    },
    [duration, seekBoth],
  );

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => hasAny,
        onMoveShouldSetPanResponder: () => hasAny,
        onPanResponderGrant: (e) => {
          scrubbingRef.current = true;
          wasPlayingBeforeScrubRef.current = playing;
          if (playing) {
            leftPlayer?.pause();
            rightPlayer?.pause();
            setPlaying(false);
          }
          scrubAtX(e.nativeEvent.locationX);
        },
        onPanResponderMove: (e) => {
          scrubAtX(e.nativeEvent.locationX);
        },
        onPanResponderRelease: () => {
          scrubbingRef.current = false;
          if (wasPlayingBeforeScrubRef.current) {
            // seek 적용 후 play — 빠른 release 시 seek 미반영 stall 방지.
            setTimeout(() => {
              leftPlayer?.play();
              rightPlayer?.play();
              setPlaying(true);
            }, REPLAY_SEEK_DELAY_MS);
          }
        },
        onPanResponderTerminate: () => {
          scrubbingRef.current = false;
        },
      }),
    [hasAny, leftPlayer, playing, rightPlayer, scrubAtX],
  );

  const progressPct =
    duration > 0 ? Math.min(100, (current / duration) * 100) : 0;

  // quick-260702-t0v — 컨트롤 공유 (로직 중복 0). 세로 카드와 가로 전체화면이
  // 같은 핸들러(togglePlay/stepBy/seekBoth/restart/panResponder)와 같은 JSX 를
  // 공유. dark=true(전체화면)면 어두운 배경 위 색만 토큰 분기.
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
          size={20}
          color={colors.textWhite}
        />
      </Pressable>
      {/* Phase 12 후속 B — 0.1s 앞/뒤 step.
          자세 미세 비교 시 1-frame 수준 정렬용. belle 요구: "0.0초 단위". */}
      <Pressable
        onPress={() => stepBy(-STEP_SECONDS)}
        accessibilityRole="button"
        accessibilityLabel="0.1초 뒤로"
        hitSlop={8}
        style={[styles.stepBtn, dark && styles.stepBtnDark]}
      >
        <Ionicons
          name="play-back"
          size={16}
          color={dark ? colors.textWhite : colors.textSecondary}
        />
      </Pressable>
      <Pressable
        onPress={() => stepBy(STEP_SECONDS)}
        accessibilityRole="button"
        accessibilityLabel="0.1초 앞으로"
        hitSlop={8}
        style={[styles.stepBtn, dark && styles.stepBtnDark]}
      >
        <Ionicons
          name="play-forward"
          size={16}
          color={dark ? colors.textWhite : colors.textSecondary}
        />
      </Pressable>
      <View style={styles.timeline}>
        {/* Phase 12 후속 B — track 자체가 PanResponder. drag 시 양쪽 동시
            seek + scrubbingRef 가 drift 보정 우회 (tick 가드). */}
        <View
          style={styles.timelineTrack}
          onLayout={dark ? onFsTrackLayout : onTrackLayout}
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
        {/* 12-deferred §12-C — 두 영상 timeline 분리 표시.
            progress bar 는 단일 (짧은 쪽 기준), 시간 라벨은 좌·우 분리.
            Phase 12 후속 B — 0.1s 정밀 표시(소수 1자리). */}
        <Text
          style={[styles.timeText, dark && styles.timeTextDark]}
          numberOfLines={1}
        >
          {hasLeft
            ? `${leftLabel} ${fmtTimeDecimal(leftCurrent)} / ${fmtTime(leftDuration)}`
            : ''}
          {hasLeft && hasRight ? '  ·  ' : ''}
          {hasRight
            ? `${rightLabel} ${fmtTimeDecimal(rightCurrent)} / ${fmtTime(rightDuration)}`
            : ''}
        </Text>
      </View>
      <Pressable
        onPress={restart}
        accessibilityRole="button"
        accessibilityLabel="처음으로"
        hitSlop={8}
      >
        <Ionicons
          name="refresh"
          size={20}
          color={dark ? colors.textWhite : colors.textSecondary}
        />
      </Pressable>
    </View>
  );

  // quick-260702-t0v — 전체화면 슬롯. 새 useVideoPlayer 호출 금지 — 기존 player
  // 인스턴스에 두 번째 VideoView attach (expo-video 다중 VideoView 지원).
  // 오버레이는 sizeScale=FULLSCREEN_OVERLAY_SCALE 로 호출 (각도 라벨 확대).
  const renderFullscreenSlot = (
    label: string,
    url: string | undefined,
    player: VideoPlayer | null,
    overlay?: OverlayRenderProp,
  ) => (
    <View style={styles.fsSlot}>
      <View style={styles.fsSlotFrame}>
        {url && player ? (
          <>
            <VideoView
              player={player}
              style={styles.video}
              contentFit="contain"
              nativeControls={false}
              allowsFullscreen={false}
              allowsPictureInPicture={false}
            />
            <View style={styles.overlayContainer} pointerEvents="none">
              {overlay?.(player, { sizeScale: FULLSCREEN_OVERLAY_SCALE })}
            </View>
          </>
        ) : (
          <View style={styles.slotEmpty}>
            <Ionicons
              name="videocam-outline"
              size={22}
              color={colors.textDisabled}
            />
            <Text style={styles.slotEmptyText}>준비 중</Text>
          </View>
        )}
      </View>
      <Text style={styles.fsSlotLabel}>{label}</Text>
    </View>
  );

  return (
    <View style={styles.card}>
      <View style={styles.row}>
        <VideoSlot
          label={leftLabel}
          url={leftUrl}
          player={leftPlayer}
          overlay={leftOverlay}
        />
        <VideoSlot
          label={rightLabel}
          url={rightUrl}
          player={rightPlayer}
          overlay={rightOverlay}
        />
      </View>

      {/* Phase 20 (UI A4) — "자동 구간 맞춤" 신뢰 배지.
          belle 가 서로 다른 시작점의 두 영상을 자동 정렬한 점을 호평 → 이 정렬이
          의도된 것임을 사용자에게 정직하게 알린다. 두 영상이 모두 있을 때만 노출
          (단일 영상은 정렬 대상 없음).

          LIGHT 버전(이번 plan): 정적 배지 + 한 줄 설명만. 신규 백엔드 데이터 /
          수치 신뢰도(alignment confidence) 없음 — 가짜 수치 금지.
          TODO(deferred-backend): 실 정렬 신뢰도(DTW 매칭 품질 등)를 백엔드가
          내려주면 배지에 수치/강도를 표시. 현재는 contract 에 필드 없어 정적. */}
      {hasLeft && hasRight && (
        <View style={styles.alignBadgeRow}>
          <View style={styles.alignBadge}>
            <Ionicons
              name="git-compare-outline"
              size={12}
              color={colors.brand}
            />
            <Text style={styles.alignBadgeText}>자동 구간 맞춤</Text>
          </View>
          <Text style={styles.alignBadgeHint}>
            서로 다른 시작점을 핵심 구간 기준으로 자동 정렬했어요.
          </Text>
        </View>
      )}

      {/* quick-260702-t0v (belle TestFlight #27 — 각도 라벨 가독) — 가로 전체화면
          진입 버튼. 세로 나란히 2개 레이아웃에선 각도 라벨이 판독 불가 → 탭 시
          두 영상을 좌우로 크게 보는 전체화면 뷰어. */}
      {hasAny && (
        <Pressable
          onPress={openFullscreen}
          accessibilityRole="button"
          accessibilityLabel="가로 전체화면으로 크게 보기"
          hitSlop={8}
          style={styles.fullscreenBtn}
        >
          <Ionicons name="expand" size={16} color={colors.brand} />
          <Text style={styles.fullscreenBtnText}>가로로 크게 보기</Text>
        </Pressable>
      )}

      {hasAny ? (
        renderControls(false)
      ) : (
        <Text style={styles.hint}>
          분석 서버가 연결되면 두 영상을 동시에 재생하며 관절 차이를 비교할 수
          있어요.
        </Text>
      )}

      {/* quick-260702-t0v — 가로 전체화면 뷰어. portrait 고정 유지 + 뷰 90° 회전
          (검증된 가로 시뮬레이트 패턴). 조건부 렌더 — 닫힌 동안 native 리소스 0
          (T-t0v-01). 같은 player 라 열고 닫아도 재생 위치·상태 자동 연속. */}
      {fullscreen && (
        <Modal
          visible
          transparent={false}
          animationType="fade"
          statusBarTranslucent
          supportedOrientations={['portrait']}
          onRequestClose={closeFullscreen}
        >
          {/* 모달 unmount 시 root _layout 의 StatusBar 로 자연 복귀 */}
          <StatusBar hidden />
          <View style={styles.fsRoot}>
            <View
              style={[
                styles.fsRotated,
                {
                  width: winH,
                  height: winW,
                  left: (winW - winH) / 2,
                  top: (winH - winW) / 2,
                },
              ]}
            >
              <View style={styles.fsTopBar}>
                {fullscreenHeaderExtra}
                <Pressable
                  onPress={closeFullscreen}
                  accessibilityRole="button"
                  accessibilityLabel="전체화면 닫기"
                  hitSlop={12}
                  style={styles.fsCloseBtn}
                >
                  <Ionicons name="close" size={22} color={colors.textWhite} />
                </Pressable>
              </View>
              <View style={styles.fsVideoRow}>
                {renderFullscreenSlot(leftLabel, leftUrl, leftPlayer, leftOverlay)}
                {renderFullscreenSlot(
                  rightLabel,
                  rightUrl,
                  rightPlayer,
                  rightOverlay,
                )}
              </View>
              {renderControls(true)}
            </View>
          </View>
        </Modal>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.card,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    padding: spacing.cardPadding,
    gap: 12,
    width: '100%',
  },
  row: {
    flexDirection: 'row',
    gap: 8,
  },
  slot: {
    flex: 1,
    gap: 6,
  },
  // 폴스포츠 = 세로 영상 위주(design.md §10-4). 9:16 비율 슬롯에 contain 으로
  // 가로/세로 모두 안전하게 들어옴.
  slotFrame: {
    width: '100%',
    aspectRatio: 9 / 16,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: colors.divider,
    borderWidth: 1,
    borderColor: colors.divider,
  },
  video: {
    width: '100%',
    height: '100%',
  },
  // Phase 12 신설 (Plan 12-02 T4) — KeypointOverlay 박제 site. pointerEvents
  // 'none' 박제 — overlay 가 영상 tap/pinch 막지 않음.
  overlayContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  slotEmpty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: '#F4F4F4',
  },
  slotEmptyText: {
    ...typography.captionSmall,
    color: colors.textDisabled,
  },
  slotLabel: {
    ...typography.captionSmall,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  controls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  playBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // Phase 12 후속 B — 0.1s 앞/뒤 step 버튼.
  stepBtn: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.divider,
    alignItems: 'center',
    justifyContent: 'center',
  },
  timeline: {
    flex: 1,
    gap: 6,
  },
  // Phase 12 후속 B — track 이 PanResponder 박힘 site. 두께 12 로 키워 drag hit
  // area 확보 (시각 트랙 4 + 손잡이 14 가 안쪽에 박힘). overflow 'visible' 가
  // 손잡이 위/아래로 비집고 나옴.
  timelineTrack: {
    width: '100%',
    height: 14,
    justifyContent: 'center',
  },
  timelineRail: {
    position: 'absolute',
    top: 5,
    left: 0,
    right: 0,
    height: 4,
    backgroundColor: colors.divider,
    borderRadius: 2,
  },
  timelineFill: {
    position: 'absolute',
    top: 5,
    left: 0,
    height: 4,
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
  hint: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  // Phase 20 (UI A4) — 자동 정렬 신뢰 배지 + 한 줄 설명 (정적, 토큰만).
  alignBadgeRow: {
    gap: 4,
  },
  alignBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 9,
    backgroundColor: colors.brandTint,
  },
  alignBadgeText: {
    ...typography.captionSmall,
    color: colors.brand,
    fontWeight: '700',
  },
  alignBadgeHint: {
    ...typography.captionSmall,
    color: colors.textSecondary,
    lineHeight: 15,
  },
  // ── quick-260702-t0v — 가로 전체화면 뷰어 (belle TestFlight #27) ─────────
  // 진입 버튼: 전체 너비 pill (brandTint 배경 + brand 텍스트, 토큰만).
  fullscreenBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    width: '100%',
    paddingVertical: 10,
    borderRadius: radius.button,
    backgroundColor: colors.brandTint,
  },
  fullscreenBtnText: {
    ...typography.caption,
    color: colors.brand,
    fontWeight: '700',
  },
  // 몰입형 영상 전체화면 배경 — videoFullscreenBg 토큰 (다크 배경 금지 원칙의
  // 의도적 예외, colors.ts 주석 참조).
  fsRoot: {
    flex: 1,
    backgroundColor: colors.videoFullscreenBg,
  },
  // 90° 회전 컨테이너 — width/height/left/top 은 render 에서 winW/winH 로 주입.
  fsRotated: {
    position: 'absolute',
    transform: [{ rotate: '90deg' }],
    paddingHorizontal: spacing.cardPadding,
    paddingVertical: 10,
    gap: 8,
  },
  fsTopBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 16,
  },
  fsCloseBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.videoBg,
  },
  fsVideoRow: {
    flex: 1,
    flexDirection: 'row',
    gap: 12,
  },
  fsSlot: {
    flex: 1,
    gap: 4,
  },
  fsSlotFrame: {
    flex: 1,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: colors.videoFullscreenBg,
  },
  fsSlotLabel: {
    ...typography.captionSmall,
    color: colors.textWhite,
    textAlign: 'center',
  },
  // 어두운 배경 위 컨트롤 색 분기 (dark variant) — 토큰만.
  stepBtnDark: {
    backgroundColor: colors.videoBg,
  },
  timeTextDark: {
    color: colors.textWhite,
  },
});
