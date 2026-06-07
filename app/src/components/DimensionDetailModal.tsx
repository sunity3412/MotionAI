// Phase 12.5 T8 — 차원별 "자세히 보기" 모달 (정적, frontend only).
//
// 사용자 의문 "왜 이 점수?" 해소. 코칭 팁 모달 (T9, LLM 동적) 과 명확히 분리:
// - 본 모달 = "점수 산출 설명" (객관: 산식 + 기준 + 측정값)
// - 코칭 팁 모달 (T9, 향후 Phase 13) = "지침/처방" (LLM 동적 생성)
//
// Figma 위계 정합 (디자인 초안 페이지, node 73:510):
// - bottom sheet 형식, 백드롭 dim 50%
// - 핸들 + 제목 + ✕ 닫기 + 한 줄 요약 + 산식 카드 + 기준/측정 dot list + 내 결과 카드 + CTA
//
// belle 피드백 (2026-06-07): 메타 텍스트 ("동등 비중", 가중치%) 본문 노출 X → 모달에서만.

import React from 'react';
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import {
  DIMENSION_LABEL_KO,
  DIMENSION_SUBLABEL_KO,
} from '../types/analysis';
import type {
  DimensionExplanation,
  ScoreDimension,
} from '../types/analysis';
import { colors, radius, spacing, typography } from '../theme';

interface Props {
  visible: boolean;
  dim: ScoreDimension | null;
  score: number | null;
  explanation?: DimensionExplanation;
  mode?: 'mode1' | 'mode3';
  // Phase 12.5 belle 피드백 (2026-06-07): 동작 이름 + 사용자 이름 동적 카피.
  // 예: "폭스탑 동작에서, 세계 심사 기준에서 180°에 얼마나 가까운지 측정합니다.
  //      그 기준에서 OO님의 분석을 반영하여 점수가 계산됩니다."
  motionName?: string; // 예: "폭스탑", "인사이드 레그 행". mode1 만.
  userName?: string; // 예: "OO" (Firebase displayName 또는 anon). 없으면 "회원"
  onClose: () => void;
}

// 차원별 한 줄 정의 — 사용자 친화 표현 (개발 용어 X)
const DIMENSION_DEFINITION_KO: Record<ScoreDimension, string> = {
  angle: '내 자세의 관절 각도가 기준 자세와 얼마나 일치하는지',
  line: '동작이 요구하는 만큼 팔/다리를 얼마나 폈는지',
  stability: '핵심 자세에서 떨림이 얼마나 작은지',
};

// 산식 설명 — 동작 이름 + 사용자 이름 동적 (belle 제안 형식)
function formulaFor(
  dim: ScoreDimension,
  motionName: string,
  userName: string,
): string {
  const me = userName ? `${userName}님` : '회원님';
  const motion = motionName || '이 동작';
  if (dim === 'angle') {
    return (
      `세계 심사 기준은 ${motion}의 정해진 관절 각도를 평가합니다. ` +
      `그 기준에 ${me}의 영상 자세를 반영해서 평균 차이를 점수로 환산합니다.`
    );
  }
  if (dim === 'line') {
    return (
      `세계 심사 기준은 ${motion}에서 팔/다리 펴기를 180° 기준으로 평가합니다. ` +
      `그 기준에 ${me}의 영상 자세를 반영하여 점수가 계산됩니다.`
    );
  }
  // stability
  return (
    `세계 심사 기준은 ${motion}에서 핵심 자세 (멈춘 순간) 의 떨림이 ` +
    `얼마나 작은지를 평가합니다. 그 기준에 ${me}의 영상을 반영하여 ` +
    `점수가 계산됩니다.`
  );
}

// 기준 카피 — mode 별 다름. 동작 이름 없으면 일반 표현.
function baselineFor(
  dim: ScoreDimension,
  mode: 'mode1' | 'mode3',
  motionName: string,
): string {
  const motion = motionName ? `${motionName} 기준 자세` : '기준 자세';
  if (mode === 'mode1') {
    if (dim === 'angle') return `${motion} + 세계 심사 기준 (IPSF) 참고`;
    if (dim === 'line') return `${motion} + 팔/다리 펴기 완성도`;
    return '핵심 자세 떨림 기준 (기준 영상 없이도 측정 가능)';
  }
  // mode3
  if (dim === 'angle') return '이전 영상의 같은 관절 각도 (일관성 비교)';
  if (dim === 'line') return '팔/다리 펴기 완성도 (기준 영상 없이도 측정 가능)';
  return '핵심 자세 떨림 (기준 영상 없이도 측정 가능)';
}

// 측정 항목 — 사용자 친화
const DIMENSION_MEASUREMENT_KO: Record<ScoreDimension, string> = {
  angle: '어깨 / 팔꿈치 / 엉덩이 / 무릎 8군데 평균 각도',
  line: '펴야 하는 관절 (팔꿈치/무릎) 의 펴진 정도',
  stability: '멈춘 순간의 관절 흔들림 정도',
};

export function DimensionDetailModal({
  visible,
  dim,
  score,
  explanation,
  mode = 'mode1',
  motionName,
  userName,
  onClose,
}: Props) {
  // useWindowDimensions: sheet 명시 height — ScrollView 가 그 안에서 flex:1 로
  // 정상 동작. maxHeight 만이면 layout 계산이 0 collapse 위험.
  const { height: winH } = useWindowDimensions();
  if (!dim) return null;
  const sheetHeight = Math.round(winH * 0.85);
  const label = DIMENSION_LABEL_KO[dim];
  const sublabel = DIMENSION_SUBLABEL_KO[dim];
  const definition = DIMENSION_DEFINITION_KO[dim];
  const formula = formulaFor(dim, motionName ?? '', userName ?? '');
  const baseline = baselineFor(dim, mode, motionName ?? '');
  const measurement = DIMENSION_MEASUREMENT_KO[dim];
  const deficit = explanation?.deficitSummary;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      {/* RN bottom sheet 정석: backdrop 위 빈 영역만 Pressable, sheet 자체는
          pure View (responder X) → ScrollView gesture 가 sheet 전체에서 정상 동작. */}
      <View style={styles.backdrop}>
        <Pressable style={styles.backdropTop} onPress={onClose} />
        <View style={[styles.sheet, { height: sheetHeight }]}>
          <View style={styles.handle} />
          <View style={styles.titleRow}>
            <Text style={styles.title}>{label}란?</Text>
            <Pressable
              onPress={onClose}
              accessibilityRole="button"
              accessibilityLabel="닫기"
              hitSlop={10}
              style={styles.closeBtn}
            >
              <Text style={styles.closeText}>✕</Text>
            </Pressable>
          </View>

          <ScrollView
            style={styles.scroll}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            <Text style={styles.definition}>{definition}</Text>

            <View style={styles.formulaCard}>
              <Text style={styles.formulaTitle}>내 점수 계산 방법</Text>
              <Text style={styles.formulaDetail}>{formula}</Text>
            </View>

            <View style={styles.dotRow}>
              <View style={styles.dot} />
              <Text style={styles.dotText}>
                <Text style={styles.dotLabel}>기준: </Text>
                {baseline}
              </Text>
            </View>

            <View style={styles.dotRow}>
              <View style={styles.dot} />
              <Text style={styles.dotText}>
                <Text style={styles.dotLabel}>측정: </Text>
                {measurement}
              </Text>
            </View>

            {score != null && (
              <View style={styles.resultCard}>
                <Text style={styles.resultTitle}>내 결과</Text>
                <View style={styles.resultScoreRow}>
                  <Text style={styles.resultScoreLabel}>점수</Text>
                  <Text style={styles.resultScoreValue}>{score}점</Text>
                </View>
                <View style={styles.resultSep} />
                <Text style={styles.resultMeta}>
                  <Text style={styles.resultMetaLabel}>심사평: </Text>
                  {deficit ?? sublabel}
                </Text>
              </View>
            )}

            <Text style={styles.coachNote}>
              자세한 교정 방법은 코칭 팁의 “자세히 보기”와 영상 (강사와 함께
              보면 더 정확) 으로 확인해 보세요.
            </Text>
          </ScrollView>

          <Pressable
            onPress={onClose}
            accessibilityRole="button"
            accessibilityLabel="닫기"
            style={({ pressed }) => [styles.cta, pressed && styles.ctaPressed]}
          >
            <Text style={styles.ctaText}>닫기</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  backdropTop: { flex: 1 },
  sheet: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingTop: 12,
    paddingBottom: 32,
    paddingHorizontal: 20,
    // height 는 useWindowDimensions 로 동적 (85%)
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: colors.divider,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 16,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  title: { fontSize: 18, fontWeight: '700', color: colors.textPrimary },
  closeBtn: { padding: 4 },
  closeText: { fontSize: 20, color: colors.textSecondary },
  // ScrollView: sheet 명시 height 가지므로 flex:1 로 남은 공간 채움 → 정상 스크롤
  scroll: { flex: 1 },
  scrollContent: { paddingBottom: 16 },
  definition: {
    fontSize: 14,
    fontWeight: '400',
    color: colors.textPrimary,
    lineHeight: 21,
    marginBottom: 16,
  },
  formulaCard: {
    backgroundColor: '#F7F7F7',
    borderRadius: radius.card,
    padding: 16,
    marginBottom: 16,
  },
  formulaTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: 6,
  },
  formulaDetail: {
    fontSize: 13,
    fontWeight: '400',
    color: colors.textSecondary,
    lineHeight: 19,
  },
  dotRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    marginBottom: 10,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.brand,
    marginTop: 7,
  },
  dotText: {
    flex: 1,
    fontSize: 13,
    fontWeight: '400',
    color: colors.textPrimary,
    lineHeight: 19,
  },
  dotLabel: { fontWeight: '600', color: colors.textPrimary },
  resultCard: {
    borderWidth: 1,
    borderColor: colors.brand,
    borderRadius: radius.card,
    padding: 16,
    marginTop: 8,
    marginBottom: 16,
    gap: 10,
  },
  resultTitle: { fontSize: 13, fontWeight: '700', color: colors.brand },
  resultScoreRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  resultScoreLabel: { fontSize: 12, color: colors.textSecondary },
  resultScoreValue: { fontSize: 18, fontWeight: '700', color: colors.brand },
  resultSep: { height: 1, backgroundColor: colors.divider },
  resultMeta: {
    fontSize: 13,
    fontWeight: '400',
    color: colors.textPrimary,
    lineHeight: 19,
  },
  resultMetaLabel: { fontWeight: '600' },
  resultMetaHint: {
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 2,
  },
  coachNote: {
    fontSize: 12,
    fontWeight: '400',
    color: colors.textSecondary,
    lineHeight: 18,
    marginTop: 8,
  },
  cta: {
    marginTop: 16,
    height: 50,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    justifyContent: 'center',
    alignItems: 'center',
  },
  ctaPressed: { opacity: 0.85 },
  ctaText: { fontSize: 16, fontWeight: '700', color: '#FFFFFF' },
});
