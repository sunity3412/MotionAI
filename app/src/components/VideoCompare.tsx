// 분석 결과 동작 비교 — 좌(내 영상) / 우(기준) 나란히 + 동기 재생.
//
// 영상 URL 이 비어 있을 때도 같은 레이아웃의 자리표시를 보여줘서, #7-follow 에서
// 실 영상이 들어오면 그대로 슬롯에 들어간다 ([[sim-scaffold-not-decorate]]).
//
// 동기 재생: 단일 Play/Pause 가 양 플레이어를 동시에 제어. 타임라인은 좌측을
// 기준으로 표시하되 seek 는 양쪽 동일 시각으로 보낸다. 영상 길이가 서로 달라도
// 짧은 쪽이 끝나면 일시정지(루프 X) — 비교 시 동기 어긋남 방지.

import { Ionicons } from '@expo/vector-icons';
import { useVideoPlayer, VideoView, type VideoPlayer } from 'expo-video';
import React, { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
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
   */
  overlay?: (player: VideoPlayer | null) => React.ReactNode;
};

function fmtTime(s: number): string {
  if (!isFinite(s) || s < 0) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
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
   * pointerEvents 'none'. R7 render prop — (player: VideoPlayer | null) =>
   * React.ReactNode. result.tsx 가 player state 들지 않고 VideoCompare 가 자기
   * player lifecycle 안에서 callback 호출. Wave 2 가 KeypointOverlay 내부
   * useEvent(player, 'timeUpdate') 박제 site (B3 iter-4 정합).
   */
  leftOverlay?: (player: VideoPlayer | null) => React.ReactNode;
  rightOverlay?: (player: VideoPlayer | null) => React.ReactNode;
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

export function VideoCompare({
  leftLabel,
  rightLabel,
  leftUrl,
  rightUrl,
  leftOverlay,
  rightOverlay,
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
      if (
        hasLeft &&
        hasRight &&
        bothPlaying &&
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

  const progressPct =
    duration > 0 ? Math.min(100, (current / duration) * 100) : 0;

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

      {hasAny ? (
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
          <View style={styles.timeline}>
            <View style={styles.timelineTrack}>
              <View
                style={[styles.timelineFill, { width: `${progressPct}%` }]}
              />
            </View>
            {/* 12-deferred §12-C — 두 영상 timeline 분리 표시.
                progress bar 는 단일 (짧은 쪽 기준), 시간 라벨은 좌·우 분리. */}
            <Text style={styles.timeText} numberOfLines={1}>
              {hasLeft
                ? `${leftLabel} ${fmtTime(leftCurrent)} / ${fmtTime(leftDuration)}`
                : ''}
              {hasLeft && hasRight ? '  ·  ' : ''}
              {hasRight
                ? `${rightLabel} ${fmtTime(rightCurrent)} / ${fmtTime(rightDuration)}`
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
              color={colors.textSecondary}
            />
          </Pressable>
        </View>
      ) : (
        <Text style={styles.hint}>
          분석 서버가 연결되면 두 영상을 동시에 재생하며 관절 차이를 비교할 수
          있어요.
        </Text>
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
    gap: 12,
  },
  playBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  timeline: {
    flex: 1,
    gap: 4,
  },
  timelineTrack: {
    width: '100%',
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.divider,
    overflow: 'hidden',
  },
  timelineFill: {
    height: '100%',
    backgroundColor: colors.brand,
    borderRadius: 2,
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
});
