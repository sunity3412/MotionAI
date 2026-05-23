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
import { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, layout, radius, spacing, typography } from '../theme';

type SlotProps = {
  label: string;
  url?: string;
  player: VideoPlayer | null;
};

function fmtTime(s: number): string {
  if (!isFinite(s) || s < 0) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

function VideoSlot({ label, url, player }: SlotProps) {
  return (
    <View style={styles.slot}>
      <View style={styles.slotFrame}>
        {url && player ? (
          <VideoView
            player={player}
            style={styles.video}
            contentFit="contain"
            nativeControls={false}
            allowsFullscreen={false}
            allowsPictureInPicture={false}
          />
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
};

export function VideoCompare({
  leftLabel,
  rightLabel,
  leftUrl,
  rightUrl,
}: VideoCompareProps) {
  // expo-video: source 가 null 이면 자원만 잡고 재생 가능 상태 아님 — 훅 순서를
  // 깨지 않으면서 빈 URL 도 안전. 음소거 + 루프 끄기(비교에 방해 안 되게).
  const leftPlayer = useVideoPlayer(leftUrl ?? null, (p) => {
    p.muted = true;
    p.loop = false;
  });
  const rightPlayer = useVideoPlayer(rightUrl ?? null, (p) => {
    p.muted = true;
    p.loop = false;
  });

  const hasLeft = !!leftUrl;
  const hasRight = !!rightUrl;
  const hasAny = hasLeft || hasRight;

  // currentTime 폴링 — expo-video 는 prop 변경 이벤트가 따로 없음. 재생 중에만
  // 250ms 마다 갱신 → 타임라인 따라잡기. 정지 상태면 폴링 멈춰 배터리 보호.
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!hasAny) return;
    const tick = () => {
      const ref = hasLeft ? leftPlayer : rightPlayer;
      if (!ref) return;
      setCurrent(ref.currentTime ?? 0);
      const dL = leftPlayer?.duration ?? 0;
      const dR = rightPlayer?.duration ?? 0;
      // 비교 기준 길이 = 둘 중 짧은 쪽. 짧은 쪽 끝나면 함께 멈추도록.
      const shorter =
        dL > 0 && dR > 0 ? Math.min(dL, dR) : Math.max(dL, dR);
      setDuration(shorter);
      setPlaying(!!ref.playing);
      // 짧은 쪽이 끝났는데 다른 쪽이 계속 가는 상황 방지.
      if (shorter > 0 && (ref.currentTime ?? 0) >= shorter - 0.05) {
        leftPlayer?.pause();
        rightPlayer?.pause();
      }
    };
    tick();
    tickRef.current = setInterval(tick, 250);
    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
      tickRef.current = null;
    };
  }, [hasAny, hasLeft, leftPlayer, rightPlayer]);

  const togglePlay = () => {
    if (!hasAny) return;
    if (playing) {
      leftPlayer?.pause();
      rightPlayer?.pause();
      setPlaying(false);
    } else {
      // 끝까지 재생됐으면 처음부터.
      if (duration > 0 && current >= duration - 0.05) {
        if (leftPlayer) leftPlayer.currentTime = 0;
        if (rightPlayer) rightPlayer.currentTime = 0;
      }
      leftPlayer?.play();
      rightPlayer?.play();
      setPlaying(true);
    }
  };

  const restart = () => {
    if (!hasAny) return;
    if (leftPlayer) leftPlayer.currentTime = 0;
    if (rightPlayer) rightPlayer.currentTime = 0;
    setCurrent(0);
  };

  const progressPct =
    duration > 0 ? Math.min(100, (current / duration) * 100) : 0;

  return (
    <View style={styles.card}>
      <View style={styles.row}>
        <VideoSlot label={leftLabel} url={leftUrl} player={leftPlayer} />
        <VideoSlot label={rightLabel} url={rightUrl} player={rightPlayer} />
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
            <Text style={styles.timeText}>
              {fmtTime(current)} / {fmtTime(duration)}
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
