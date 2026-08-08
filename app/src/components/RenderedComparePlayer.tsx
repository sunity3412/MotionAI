// Phase 35 (quick-260808-jix) — 합성 비교 영상 단일 mp4 플레이어.
//
// 서버(Pod 사후 스테이지)가 user·ref 두 패널 + 감점 정지·코칭 음성·자막을 이미
// 한 mp4 에 구워 놓았다 (contract.md §12.9 — 리그 ALL PASS 만 도착). 여기는
// **재생만** 한다 — 오버레이·동기·스냅·재개 로직 0 (그 계열 버그가 재생기
// 차원에서 소멸하는 것이 돌파 ① 의 목적). 신규 화면 디자인 아님 — 기존
// '동작 비교' 섹션 내 재생원 교체.
//
// URL 은 1시간 TTL asset 서명이라 저장·재사용하지 않고 mount(=analysisId)마다
// 재발급한다 (만료 재서명 = 기존 asset 패턴, H-02 URL 비저장).
// fetch 실패/404 → onUnavailable() — 화면이 기존 듀얼 플레이어로 강등
// (catch 삼킴 금지 — [[icloud-offload-breaks-original-asset-picker]] 교훈,
// __DEV__ warn 으로 원인 가시화).
import { useEffect, useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useVideoPlayer, VideoView } from 'expo-video';

import { fetchVisualAssetUrl } from '../lib/api';
import { colors, radius, spacing, typography } from '../theme';

export default function RenderedComparePlayer({
  analysisId,
  onUnavailable,
}: {
  analysisId: string;
  onUnavailable: () => void;
}) {
  const [url, setUrl] = useState<string | null>(null);
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

  return (
    <View style={styles.frame}>
      {url ? (
        <VideoView
          player={player}
          style={styles.video}
          // 두 패널 합성 mp4 — 오버레이·동기 로직 없이 nativeControls 만.
          nativeControls
          contentFit="contain"
          allowsPictureInPicture={false}
          accessibilityLabel="동작 비교 영상"
        />
      ) : (
        <View style={styles.placeholder}>
          <Text style={styles.placeholderText}>비교 영상을 불러오고 있어요</Text>
        </View>
      )}
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
});
