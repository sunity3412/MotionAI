// 자세 비교 — 감점 비교 순간의 "실제 영상 프레임" 쌍 (2026-07-21 belle 결정:
// "사람이 나와야지" — 스켈레톤 추상화가 아니라 사람이 보여야 한다).
//
// 동작 원리: 동작 비교(VideoCompare)와 같은 영상 URL 을 쓰되, 각 영상을 결함
// 비교 순간(faultZoom userFrameIdx/refFrameIdx 의 시각)으로 seek 해 정지 상태로
// 보여준다. 그 위에 KeypointOverlay 정적 모드(frameIndex 명시, player 미전달)로
// 관절점을 얹는다 — 확대비교(관절 클로즈업)와 달리 전신이 그 순간에 어떤
// 자세인지를 보여주는 카드다.
//
// 시점 좌표계 주의: frameIdx 는 keypointReport 프레임 공간(사용자 18fps 실측),
// 초 = frameIdx / report.fps. joints3d(9fps)와 섞지 말 것 — 2026-07-20 뷰어
// 프레임 시점 버그(코드의 데이터 가정 vs 실제 보유 불일치)의 재발 방지 주석.
//
// 실패 폴백: URL 이 없거나 로드가 안 되면 caller(ReferenceCornerSection)가
// 스켈레톤 뷰어(PoseCompareViewer)로 폴백한다 — 카드가 비지 않는다 (D-08 조용한
// 폴백과 동일 철학).

import { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useEvent } from 'expo';
import { useVideoPlayer, VideoView, type VideoPlayer } from 'expo-video';

import { KeypointOverlay } from './KeypointOverlay';
import { colors, radius, typography } from '../theme';
import type { KeypointReport } from '../types/analysis';

/** 한쪽 슬롯의 표시 재료. report/frameIdx 는 같은 keypointReport 공간이어야 한다. */
export type PoseFrameSlot = {
  url?: string;
  /** 결함 비교 순간 (초) = frameIdx / keypointReport.fps */
  timeSec: number;
  report: KeypointReport | null;
  /** keypointReport 프레임 공간 인덱스 (joints3d 공간 아님) */
  frameIdx: number;
  label: string;
};

/**
 * 로드 완료 시점에 비교 순간으로 seek 후 정지. expo-video 는 소스 로드 전
 * currentTime 설정이 무시될 수 있어 statusChange(readyToPlay)에 맞춰 적용한다.
 */
function useSeekPaused(player: VideoPlayer, timeSec: number) {
  // useVideoPlayer 는 source 가 null 이어도 항상 player 인스턴스를 반환하므로
  // (ReferenceCornerSection rotationPlayer 선례) null 은 여기 못 온다. useEvent 에
  // null 을 넘기면 내부 addListener 에서 크래시 — 2026-07-21 시뮬레이터 게이트에서
  // 실측 (Render Error: Cannot read property 'addListener' of null).
  // 1st arg 타입은 EventEmitter — VideoPlayer 가 그 shape 을 구현하지만 expo
  // public 타입에 명시 변환이 필요 (KeypointOverlay 선례와 동일 cast).
  const status = (
    useEvent(
      player as unknown as Parameters<typeof useEvent>[0],
      'statusChange',
      { status: player.status } as Parameters<typeof useEvent>[2],
    ) as { status: string } | null
  )?.status;
  useEffect(() => {
    if (status !== 'readyToPlay') return;
    try {
      player.currentTime = timeSec;
      player.pause();
    } catch {
      // 만료 URL 등 — 조용히 둔다. 화면엔 로딩 배경만 남고 카드 구조는 유지.
    }
  }, [player, status, timeSec]);
}

function FrameSlot({
  slot,
  videoSize,
}: {
  slot: PoseFrameSlot;
  videoSize: { width: number; height: number };
}) {
  const player = useVideoPlayer(slot.url ?? null, (p) => {
    p.muted = true;
    p.loop = false;
  });
  useSeekPaused(player, slot.timeSec);

  return (
    <View style={styles.slot}>
      <View style={styles.frameBox}>
        <VideoView
          player={player}
          style={styles.video}
          contentFit="contain"
          nativeControls={false}
        />
        <View style={styles.overlayLayer} pointerEvents="none">
          <KeypointOverlay
            keypointReport={slot.report}
            videoSize={videoSize}
            visible
            frameIndex={slot.frameIdx}
          />
        </View>
      </View>
      <Text style={styles.slotLabel}>{slot.label}</Text>
    </View>
  );
}

/** 감점 비교 순간의 실제 프레임 쌍. 양쪽 URL 이 있을 때만 caller 가 렌더한다. */
export function PoseCompareFrames({
  user,
  reference,
  videoSize,
}: {
  user: PoseFrameSlot;
  reference: PoseFrameSlot;
  videoSize: { width: number; height: number };
}) {
  return (
    <View style={styles.row}>
      <FrameSlot slot={user} videoSize={videoSize} />
      <FrameSlot slot={reference} videoSize={videoSize} />
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 8 },
  slot: { flex: 1 },
  // ReferenceCornerSection 내부 미디어 컨벤션 mirror (correctedImage/rotationVideo
  // 상당) — radius.listItem + softBg. 비율만 9:16 (동작 비교 슬롯과 동일 화면비).
  frameBox: {
    width: '100%',
    aspectRatio: 9 / 16,
    borderRadius: radius.listItem,
    overflow: 'hidden',
    backgroundColor: colors.softBg,
  },
  video: { width: '100%', height: '100%' },
  overlayLayer: { ...StyleSheet.absoluteFillObject },
  slotLabel: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 6,
  },
});
