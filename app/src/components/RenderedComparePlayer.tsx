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
//   · 정지 지점 틱 + 탭 점프 — doc renderedCompare.freezes[{rid, outSec}]
//     (contract.md §12.9 optional) 를 커스텀 씬 바 틱으로 표시, 탭하면 그 정지
//     직전(-0.5s)으로 시크. 구버전 doc(freezes 부재) = 틱 없이 재생만 (fail-open).
//
// URL 은 1시간 TTL asset 서명이라 저장·재사용하지 않고 mount(=analysisId)마다
// 재발급한다 (만료 재서명 = 기존 asset 패턴, H-02 URL 비저장).
// fetch 실패/404 → onUnavailable() — 화면이 기존 듀얼 플레이어로 강등
// (catch 삼킴 금지 — [[icloud-offload-breaks-original-asset-picker]] 교훈,
// __DEV__ warn 으로 원인 가시화).
import { useEffect, useRef, useState } from 'react';
import {
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { useVideoPlayer, VideoView, type VideoPlayer } from 'expo-video';

import { fetchVisualAssetUrl } from '../lib/api';
import type { RenderedCompareFreeze } from '../types/analysis';
import { colors, radius, spacing, typography } from '../theme';

// 정지 직전 여유 — 탭 점프가 정지 화면이 아니라 그 직전 재생부터 보이게
// (지정 -0.5s — freeze 진입 크로스페이드 0.17s 계열보다 넉넉).
const TICK_JUMP_LEAD_S = 0.5;

// 씬 바 틱 — 감점 정지의 출력 타임라인 위치 표시 + 탭 점프. duration 은
// player 메타데이터 로드 후에만 유효 — 250ms 폴링(VideoCompare 타임라인 선례)
// 으로 확보되면 중단. freezes 부재/duration 미확보 = 렌더 안 함 (fail-open 표시).
function FreezeTickBar({
  player,
  freezes,
}: {
  player: VideoPlayer;
  freezes: RenderedCompareFreeze[];
}) {
  const [duration, setDuration] = useState(0);
  useEffect(() => {
    setDuration(0);
    const id = setInterval(() => {
      const d = player.duration;
      if (d && d > 0) {
        setDuration(d);
        clearInterval(id);
      }
    }, 250);
    return () => clearInterval(id);
  }, [player]);

  if (freezes.length === 0 || duration <= 0) return null;
  return (
    <View style={styles.tickBar}>
      <View style={styles.tickTrack} />
      {freezes.map((f) => (
        <Pressable
          key={f.rid}
          accessibilityRole="button"
          accessibilityLabel={`감점 정지 지점으로 이동 (${f.rid})`}
          hitSlop={12}
          onPress={() => {
            // 정지 직전으로 시크 — nativeControls 스크럽과 동일 API.
            player.currentTime = Math.max(0, f.outSec - TICK_JUMP_LEAD_S);
          }}
          style={[
            styles.tick,
            { left: `${Math.min(98, (f.outSec / duration) * 100)}%` },
          ]}
        >
          <View style={styles.tickDot} />
        </Pressable>
      ))}
    </View>
  );
}

export default function RenderedComparePlayer({
  analysisId,
  onUnavailable,
  freezes,
}: {
  analysisId: string;
  onUnavailable: () => void;
  // doc renderedCompare.freezes — 부재(구버전 doc) = 틱 없이 재생만 (fail-open).
  freezes?: RenderedCompareFreeze[];
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  // onUnavailable 는 보통 인라인 콜백(매 렌더 새 참조)이라 effect deps 에 넣으면
  // 렌더마다 재발급이 돈다 — ref 로 최신 참조만 유지 (deps = analysisId 만).
  const onUnavailableRef = useRef(onUnavailable);
  onUnavailableRef.current = onUnavailable;

  useEffect(() => {
    let cancelled = false;
    setUrl(null); // 분석 전환 시 이전 영상 잔상 방지
    fetchVisualAssetUrl(analysisId, 'renderedCompare')
      .then((playbackUrl) => {
        if (!cancelled) setUrl(playbackUrl);
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

  // t0v 선례 — 90° 회전 컨테이너 치수 (portrait 고정 앱에서 가로 시뮬레이트,
  // useWindowDimensions = 반응형 hook 값 직접 사용).
  const { width: winW, height: winH } = useWindowDimensions();
  const fsShort = Math.min(winW, winH);
  const fsLong = Math.max(winW, winH);
  const validFreezes = freezes ?? [];

  return (
    <View style={styles.frame}>
      {url ? (
        <>
          <VideoView
            player={player}
            style={styles.video}
            // 두 패널 합성 mp4 — 오버레이·동기 로직 없이 nativeControls 만.
            nativeControls
            contentFit="contain"
            allowsPictureInPicture={false}
            accessibilityLabel="동작 비교 영상"
          />
          {/* 가로 크게 보기 진입 — 카드 우상단 (t0v 진입 버튼 관례) */}
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="가로로 크게 보기"
            hitSlop={10}
            onPress={() => setFullscreen(true)}
            style={styles.expandBtn}
          >
            <Ionicons name="expand" size={16} color={colors.textWhite} />
          </Pressable>
          <FreezeTickBar player={player} freezes={validFreezes} />
        </>
      ) : (
        <View style={styles.placeholder}>
          <Text style={styles.placeholderText}>비교 영상을 불러오고 있어요</Text>
        </View>
      )}

      {/* 가로 전체화면 — 260702-t0v 90° 회전 Modal 패턴 (portrait 고정 유지).
          같은 player 인스턴스에 두 번째 VideoView attach — 재생 위치·상태 공유
          (동기 로직 0). 탭 = 재생/일시정지 토글, 우상단 닫기, 하단 씬 바 틱. */}
      <Modal
        visible={fullscreen}
        animationType="fade"
        statusBarTranslucent
        supportedOrientations={['portrait']}
        onRequestClose={() => setFullscreen(false)}
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
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="재생 또는 일시정지"
              style={styles.fsVideoWrap}
              onPress={() => {
                if (player.playing) player.pause();
                else player.play();
              }}
            >
              <VideoView
                player={player}
                style={styles.fsVideo}
                contentFit="contain"
                nativeControls={false}
                allowsFullscreen={false}
                allowsPictureInPicture={false}
                accessibilityLabel="동작 비교 영상 (가로)"
              />
            </Pressable>
            <FreezeTickBar player={player} freezes={validFreezes} />
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="가로 보기 닫기"
              hitSlop={12}
              onPress={() => setFullscreen(false)}
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
  frame: {
    width: '100%',
    borderRadius: radius.card,
    overflow: 'hidden',
    // 영상 카드 배경 — design.md §5-1 다크 예외 토큰 (영상 콘텐츠 자체의 어두움).
    backgroundColor: colors.videoBg,
  },
  video: {
    width: '100%',
    // 렌더러 출력 = 세로 패널 2장 나란히 (PANEL_H 1080, 파일럿 세로 영상 기준
    // 약 1224x1080). 비율이 다른 소스는 contain 이 videoBg 위에 레터박스.
    aspectRatio: 1224 / 1080,
  },
  expandBtn: {
    position: 'absolute',
    top: 8,
    right: 8,
    padding: 6,
    borderRadius: radius.listItem,
    backgroundColor: colors.brandOverlay,
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
  // 씬 바 — 영상 아래 얇은 트랙 + 감점 정지 틱 (nativeControls 스크러버와
  // 겹치지 않게 프레임 하단 별도 행).
  tickBar: {
    height: 22,
    marginHorizontal: 12,
    justifyContent: 'center',
  },
  tickTrack: {
    height: 2,
    borderRadius: 1,
    backgroundColor: colors.divider,
    opacity: 0.5,
  },
  tick: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    justifyContent: 'center',
    // left 는 render 에서 % 주입 — 틱 점이 트랙 위 해당 시각 위치.
  },
  tickDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.brand,
    borderWidth: 1.5,
    borderColor: colors.textWhite,
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
  fsVideo: {
    width: '100%',
    height: '100%',
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
