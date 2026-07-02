// 문제 부위 확대 비교 (belle 2026-06-21) — 깨진 3D 뷰어 대체.
//
// 결함 관절 부위만 worst-pose 시점에서 [내 영상 | 기준] 나란히 crop+zoom 한 합성
// 이미지(backend 렌더, result.faultZoomComparisons)를 carousel 로 보여준다. 한글
// 캡션/좌우 라벨은 앱이 부여(이미지엔 숫자 각도만 — 폰트 회피). 산출 출처=backend.
//
// 여러 결함이면 가로 스와이프로 넘긴다. 데이터 없으면 섹션 미렌더(빈 박스 금지).

import { useState } from 'react';
import {
  Image,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from 'react-native';

import { JOINT_LABEL_KO } from '../lib/deductionLabels';
import { colors, layout, radius, spacing } from '../theme';
import { typography } from '../theme/typography';
import type { FaultZoomComparison } from '../types/analysis';

// 관절 KO 라벨은 deductionLabels.JOINT_LABEL_KO 단일 출처 (quick-260702-q8q —
// 점수 계산 내역/편차표와 동일 맵 재사용, 중복 2벌 금지).
function caption(item: FaultZoomComparison): string {
  const label = JOINT_LABEL_KO[item.joint] ?? '문제 부위';
  // Mode3 — 지난 분석 대비 개선/악화 방향.
  if (item.kind === 'improved') return `${label} · 지난 분석보다 좋아졌어요`;
  if (item.kind === 'worsened') return `${label} · 지난 분석보다 아쉬워졌어요`;
  // Mode1 (deficit) — 기준 대비 부족 각도.
  if (typeof item.deficitDeg === 'number' && item.deficitDeg > 0) {
    return `${label} · 기준보다 ${Math.round(item.deficitDeg)}° 부족해요`;
  }
  return `${label} · 기준과 비교해 보세요`;
}

export function FaultZoomCompare({
  comparisons,
  rightLabel,
}: {
  comparisons?: FaultZoomComparison[] | null;
  // 우측 비교 대상 라벨 — Mode1='정은지', Mode3='지난 분석'.
  rightLabel: string;
}) {
  const { width } = useWindowDimensions();
  const [page, setPage] = useState(0);

  if (!comparisons || comparisons.length === 0) return null;

  // 카드 내부 가용 폭 = 화면폭 - 좌우 화면 패딩 - 카드 패딩.
  const cardInner = width - spacing.screenX * 2 - spacing.cardPadding * 2;
  // 합성 이미지 = [정사각 | 정사각] → 가로:세로 ≈ 2:1.
  const imgH = cardInner / 2;

  return (
    <>
      <Text style={styles.sectionTitle}>문제 부위 확대 비교</Text>
      <View style={styles.card}>
        <ScrollView
          horizontal
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          onMomentumScrollEnd={(e) => {
            const w = Math.max(1, cardInner);
            setPage(Math.round(e.nativeEvent.contentOffset.x / w));
          }}
        >
          {comparisons.map((item) => (
            <View key={item.joint} style={{ width: cardInner }}>
              <View style={[styles.imageWrap, { height: imgH }]}>
                <Image
                  source={{ uri: item.imageUrl }}
                  style={styles.image}
                  resizeMode="contain"
                  accessibilityLabel={`${caption(item)} 확대 비교 이미지`}
                />
                {/* 좌/우 반쪽 라벨 — 이미지엔 텍스트 없음(앱이 부여). */}
                <View style={[styles.halfLabel, styles.halfLabelLeft]}>
                  <Text style={styles.halfLabelText}>내 영상</Text>
                </View>
                <View style={[styles.halfLabel, styles.halfLabelRight]}>
                  <Text style={styles.halfLabelText}>{rightLabel}</Text>
                </View>
              </View>
              <Text style={styles.caption}>{caption(item)}</Text>
            </View>
          ))}
        </ScrollView>
        {comparisons.length > 1 && (
          <View style={styles.dots}>
            {comparisons.map((c, i) => (
              <View
                key={c.joint}
                style={[styles.dot, i === page && styles.dotActive]}
              />
            ))}
          </View>
        )}
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  sectionTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
    marginTop: 8,
    marginBottom: 8,
  },
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.card,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    padding: spacing.cardPadding,
  },
  imageWrap: {
    width: '100%',
    borderRadius: radius.listItem,
    overflow: 'hidden',
    backgroundColor: colors.divider,
  },
  image: { width: '100%', height: '100%' },
  halfLabel: {
    position: 'absolute',
    top: 8,
    backgroundColor: colors.brandOverlay,
    borderRadius: radius.listItem,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  halfLabelLeft: { left: 8 },
  halfLabelRight: { right: 8 },
  halfLabelText: { ...typography.caption, color: '#FFFFFF', fontWeight: '700' },
  caption: {
    ...typography.body,
    color: colors.textPrimary,
    marginTop: 10,
    textAlign: 'center',
  },
  dots: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 6,
    marginTop: 10,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: colors.divider,
  },
  dotActive: { backgroundColor: colors.brand },
});
