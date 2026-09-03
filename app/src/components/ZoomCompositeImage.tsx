// 확대비교 합성 PNG 1장 렌더 — 프레임(정확 종횡비) + 좌/우 태그 + 로딩 skeleton +
// 실패 캡션 + onError 재발급 트리거 + 사후 도착 대기 placeholder (quick-260903-ftg).
//
// 왜 컴포넌트로 뽑았나: quick-260903-f2w 가 이 렌더를 DeductionCard(topFix 카드)
// 안에 넣었는데, 역립 저신뢰(IN-01, quick-260724-q6b) 경로는 topFix 카드·'다른 감점
// 항목' 목록이 억제돼 같은 사진을 "예상 부위 (참고)" 카드로 따로 내야 한다 (09-03
// 실측: 확정 카드 2장인데 링크 1개 뒤 시트로 1장만 도달). 렌더 규칙(종횡비·태그·
// 로딩·실패·재발급·pending)을 두 곳에 적으면 사본이 생기므로 이 컴포넌트가 소유하고
// DeductionCard 와 result.tsx IN-01 카드가 같은 것을 소비한다 (사본 0).
//
// 모양은 DeductionCard 에서 이동한 것 그대로 (f2w 실행자 판단 승계 — 로드 실패
// 상태에서는 좌/우 태그를 숨겨 실패 캡션 위에 비교 라벨이 남는 모순 표시를 피한다).
// 훅은 조기 반환 전에 호출(Rules of Hooks). 토큰만 (CLAUDE.md §4). 이모지 0. 라이트 전용.

import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Image, StyleSheet, Text, View } from 'react-native';

import { colors, radius, typography } from '../theme';

const IMG_FAILED_CAPTION = '이미지를 불러오지 못했어요';
const ZOOM_PENDING_CAPTION = '확대 비교 이미지를 준비하고 있어요';
const DEFAULT_LEFT_LABEL = '내 영상';

// 합성 PNG 종횡비 — 백엔드 fault_zoom._compose lockstep: `_OUT=360` 정사각 crop 2장
// + `gap=6` 흰 구분선 → 캔버스 (726, 360). 프레임은 이 정확 비율로 컨테이너를 잡아
// contain 레터박스 0 (시트는 imgW/2 근사를 쓴다 — 정확값은 여기서만). 백엔드
// 상수가 바뀌면 같이 바꾼다.
export const ZOOM_COMPOSITE_ASPECT = (360 * 2 + 6) / 360;

interface ZoomCompositeImageProps {
  // 합성 PNG URL (호출부가 resolveZoomImageUrl 로 fresh 우선 조회해 넘긴다).
  // 부재 + pending 이면 placeholder, 둘 다 아니면 null.
  imageUrl?: string;
  // 줌 사후 도착 대기(result.faultZoomStatus='pending') — onSnapshot 으로 done 이
  // 도착하면 호출부가 imageUrl 을 넘겨 같은 프레임이 사진으로 교체된다.
  pending?: boolean;
  // 좌/우 반쪽 태그. 좌 기본 '내 영상', 우 = Mode1 '{선수} 선수' / Mode3 '지난 영상'.
  leftLabel?: string;
  rightLabel: string;
  // 이미지 로드 실패 시 재발급 트리거 — useFreshFaultZoomUrls.onZoomImageError
  // (훅이 single-flight 로 무한 루프를 막는다). 실패 캡션은 여기서 렌더.
  onError?: () => void;
  accessibilityLabel?: string;
}

export function ZoomCompositeImage({
  imageUrl,
  pending = false,
  leftLabel = DEFAULT_LEFT_LABEL,
  rightLabel,
  onError,
  accessibilityLabel,
}: ZoomCompositeImageProps) {
  // 로딩/실패 추적 (만료 presigned URL 방어). 재발급으로 imageUrl 이 바뀌면
  // (onError → fresh 맵 갱신) 실패 캡션이 남지 않게 리셋 — 새 URL 로 다시 시도.
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setLoading(true);
    setFailed(false);
  }, [imageUrl]);

  if (imageUrl) {
    return (
      <View style={styles.frame}>
        {failed ? (
          <View style={styles.fallback}>
            <Text style={styles.fallbackText}>{IMG_FAILED_CAPTION}</Text>
          </View>
        ) : (
          <>
            <Image
              source={{ uri: imageUrl }}
              style={styles.image}
              resizeMode="contain"
              onLoadEnd={() => setLoading(false)}
              onError={() => {
                setFailed(true);
                setLoading(false);
                onError?.();
              }}
              accessibilityLabel={
                accessibilityLabel ?? `${leftLabel} · ${rightLabel} 확대 비교 이미지`
              }
            />
            {loading ? (
              <View style={styles.skeleton}>
                <ActivityIndicator color={colors.brand} />
              </View>
            ) : null}
            <View style={[styles.tag, styles.tagLeft]}>
              <Text style={styles.tagText}>{leftLabel}</Text>
            </View>
            <View style={[styles.tag, styles.tagRight]}>
              <Text style={styles.tagText}>{rightLabel}</Text>
            </View>
          </>
        )}
      </View>
    );
  }

  if (pending) {
    return (
      <View
        style={[styles.frame, styles.pending]}
        accessibilityRole="progressbar"
        accessibilityLabel={ZOOM_PENDING_CAPTION}
      >
        <ActivityIndicator color={colors.brand} />
        <Text style={styles.pendingText}>{ZOOM_PENDING_CAPTION}</Text>
      </View>
    );
  }

  return null;
}

const styles = StyleSheet.create({
  // 인라인 확대비교 컨테이너 — 합성 PNG 정확 종횡비 (fault_zoom._compose lockstep).
  frame: {
    width: '100%',
    aspectRatio: ZOOM_COMPOSITE_ASPECT,
    borderRadius: radius.listItem,
    overflow: 'hidden',
    backgroundColor: colors.softBg,
    position: 'relative',
  },
  image: { width: '100%', height: '100%' },
  // 로딩 중 skeleton 오버레이 (토큰 배경).
  skeleton: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.softBg,
  },
  // onError 폴백 — 이미지 숨김 + 소형 캡션(빈 깨짐 0).
  fallback: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 8,
    backgroundColor: colors.softBg,
  },
  fallbackText: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  // 사후 도착 대기 placeholder — 이미지와 같은 컨테이너(frame) 위에 스피너 +
  // 캡션 (시트 imagePending 미러).
  pending: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  pendingText: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  // 좌/우 반쪽 태그 — 시트 halfLabel 미러.
  tag: {
    position: 'absolute',
    top: 8,
    backgroundColor: colors.brandOverlay,
    borderRadius: radius.listItem,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  tagLeft: { left: 8 },
  tagRight: { right: 8 },
  tagText: {
    ...typography.caption,
    color: colors.textWhite,
    fontWeight: '700',
  },
});
