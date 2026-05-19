import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useMemo } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { ScoreGauge, scoreGrade } from '../../components/ScoreGauge';
import { getSimulatedResult } from '../../lib/simulatedResult';
import type { AnalysisMode, BodyPart } from '../../types/analysis';
import { colors, layout, radius, spacing, typography } from '../../theme';

// 분석 결과 화면 (plan.md #8, design.md §8, ia AC-RES-001).
// 미설계 화면 → design.md §0 결정 트리로 자체 설계. 흰 배경(§5-1),
// 브랜드 포인트(#FF4B33), 스피너/이모지 없음, 토큰만 사용.
// 데이터는 시뮬레이션(getSimulatedResult) — 백엔드 연결 시 동일 타입으로 교체.

const PARTS: BodyPart[] = ['상체', '코어', '하체'];

function PartScoreRow({
  part,
  score,
  delta,
}: {
  part: BodyPart;
  score: number;
  delta?: number;
}) {
  return (
    <View style={styles.partRow}>
      <View style={styles.partHead}>
        <Text style={styles.partLabel}>{part}</Text>
        <View style={styles.partValueWrap}>
          <Text style={styles.partScore}>{score}</Text>
          {delta != null && delta !== 0 && (
            <Text
              style={[
                styles.partDelta,
                { color: delta > 0 ? colors.brand : colors.inputError },
              ]}
            >
              {delta > 0 ? `+${delta}` : `${delta}`}
            </Text>
          )}
        </View>
      </View>
      <View style={styles.track}>
        <View style={[styles.trackFill, { width: `${Math.max(0, Math.min(100, score))}%` }]} />
      </View>
    </View>
  );
}

export default function AnalysisResult() {
  const router = useRouter();
  const { mode, name } = useLocalSearchParams<{
    mode?: AnalysisMode;
    name?: string;
  }>();
  const analysisMode: AnalysisMode = mode === 'mode1' ? 'mode1' : 'mode3';
  const result = useMemo(
    () => getSimulatedResult(analysisMode),
    [analysisMode],
  );

  const grade = scoreGrade(result.overallScore);
  const cmp = result.comparison;

  // ia AC-RES-001-2: 틀린 관절 하이라이트 — issue 있는 관절 중 최저점
  const worstJoint = useMemo(
    () =>
      result.joints
        .filter((j) => j.issue)
        .sort((a, b) => a.score - b.score)[0],
    [result.joints],
  );

  const summary =
    cmp.mode === 'mode1'
      ? `${cmp.athleteName} 선수와 ${cmp.similarity}% 일치해요.`
      : cmp.isFirst
        ? '첫 분석이에요. 다음 분석부터 성장을 비교해드려요.'
        : '지난 분석과 파트별로 비교했어요.';

  const deltaFor = (part: BodyPart): number | undefined =>
    cmp.mode === 'mode3' && !cmp.isFirst
      ? cmp.deltaFromPrevious?.[part]
      : undefined;

  const rightLabel =
    cmp.mode === 'mode1' ? `${cmp.athleteName} 기준` : '지난 분석';

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Text style={styles.title}>분석 결과</Text>
          <Text style={styles.sub}>
            {name ? `${name} · ` : ''}분석이 완료됐어요. 점수를 확인해보세요.
          </Text>
        </View>

        {/* 점수 개요 (AC-RES-001-1) */}
        <View style={styles.card}>
          <ScoreGauge score={result.overallScore} />
          <View style={styles.gradeRow}>
            <Text style={styles.gradeBadge}>{grade}</Text>
            <Text style={styles.summary}>{summary}</Text>
          </View>
        </View>

        {/* 세부 점수 (AC-RES-001-4) */}
        <Text style={styles.sectionTitle}>세부 점수</Text>
        <View style={styles.card}>
          {PARTS.map((part) => (
            <PartScoreRow
              key={part}
              part={part}
              score={result.partScores[part]}
              delta={deltaFor(part)}
            />
          ))}
        </View>

        {/* 동작 비교 (AC-RES-001-2) */}
        <Text style={styles.sectionTitle}>동작 비교</Text>
        <View style={styles.card}>
          <View style={styles.compareRow}>
            <View style={styles.compareCol}>
              <View style={styles.videoBox}>
                <Ionicons
                  name="play-circle-outline"
                  size={36}
                  color={colors.textDisabled}
                />
              </View>
              <Text style={styles.compareLabel}>내 동작</Text>
            </View>
            <View style={styles.compareCol}>
              <View style={styles.videoBox}>
                <Ionicons
                  name="play-circle-outline"
                  size={36}
                  color={colors.textDisabled}
                />
              </View>
              <Text style={styles.compareLabel}>{rightLabel}</Text>
            </View>
          </View>
          {worstJoint && (
            <View style={styles.highlight}>
              <Ionicons name="alert-circle" size={16} color={colors.brand} />
              <Text style={styles.highlightText}>
                {worstJoint.labelKo} {worstJoint.issue}
              </Text>
            </View>
          )}
          <Text style={styles.note}>
            영상 나란히 보기는 분석 서버 연결 후 표시돼요.
          </Text>
        </View>

        {/* 코칭 팁 (AC-RES-001-3) */}
        <Text style={styles.sectionTitle}>코칭 팁</Text>
        {result.tips.map((tip, i) => (
          <View key={tip.joint ?? i} style={[styles.card, styles.tipCard]}>
            <View style={styles.tipHead}>
              <Text style={styles.tipIndex}>{i + 1}</Text>
              <Text style={styles.tipTitle}>{tip.title}</Text>
            </View>
            <Text style={styles.tipDetail}>{tip.detail}</Text>
          </View>
        ))}

        <Pressable
          style={styles.cta}
          onPress={() => router.replace('/(tabs)')}
          accessibilityRole="button"
        >
          <Text style={styles.ctaText}>완료</Text>
        </Pressable>
        <Pressable
          onPress={() => router.replace('/(tabs)/analyze')}
          accessibilityRole="button"
          hitSlop={8}
        >
          <Text style={styles.link}>다시 분석하기</Text>
        </Pressable>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg, // 서브 화면 = 흰 배경 (§5-1)
  },
  content: {
    paddingTop: layout.safeAreaTop,
    paddingHorizontal: spacing.screenX,
    paddingBottom: layout.safeAreaBottom + 24,
    gap: 14,
  },
  header: { marginTop: 16, marginBottom: 2 },
  title: { ...typography.heading, color: colors.textPrimary },
  sub: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 8,
  },
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.card,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    padding: spacing.cardPadding,
    alignItems: 'center',
  },
  gradeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginTop: 14,
  },
  gradeBadge: {
    ...typography.boxLabel,
    color: colors.textWhite,
    backgroundColor: colors.brand,
    width: 30,
    height: 30,
    borderRadius: 15,
    textAlign: 'center',
    textAlignVertical: 'center',
    lineHeight: 30,
    overflow: 'hidden',
  },
  summary: {
    ...typography.boxLabel,
    color: colors.textPrimary,
    flexShrink: 1,
  },
  sectionTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
    marginTop: 8,
  },
  partRow: { width: '100%', marginBottom: 14 },
  partHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    marginBottom: 8,
  },
  partLabel: { ...typography.boxLabel, color: colors.textPrimary },
  partValueWrap: { flexDirection: 'row', alignItems: 'baseline', gap: 6 },
  partScore: { ...typography.listTitle, color: colors.brand },
  partDelta: { ...typography.caption },
  track: {
    width: '100%',
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.divider,
    overflow: 'hidden',
  },
  trackFill: {
    height: '100%',
    borderRadius: 5,
    backgroundColor: colors.brand,
  },
  compareRow: { flexDirection: 'row', gap: 12, width: '100%' },
  compareCol: { flex: 1, alignItems: 'center', gap: 8 },
  videoBox: {
    width: '100%',
    aspectRatio: 9 / 16, // 폴스포츠 세로 영상 (design.md §10)
    borderRadius: radius.listItem,
    backgroundColor: '#FFF0EE', // homeCard 하단 톤 (라이트, 다크 금지)
    alignItems: 'center',
    justifyContent: 'center',
  },
  compareLabel: { ...typography.caption, color: colors.textSecondary },
  highlight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 14,
    alignSelf: 'flex-start',
  },
  highlightText: {
    ...typography.caption,
    color: colors.textPrimary,
    flexShrink: 1,
  },
  note: {
    ...typography.captionSmall,
    color: colors.textSecondary,
    marginTop: 10,
    alignSelf: 'flex-start',
  },
  tipCard: { alignItems: 'flex-start', gap: 8 },
  tipHead: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  tipIndex: {
    ...typography.caption,
    color: colors.textWhite,
    backgroundColor: colors.brand,
    width: 22,
    height: 22,
    borderRadius: 11,
    textAlign: 'center',
    lineHeight: 22,
    overflow: 'hidden',
  },
  tipTitle: { ...typography.listTitle, color: colors.textPrimary, flexShrink: 1 },
  tipDetail: { ...typography.caption, color: colors.textSecondary, lineHeight: 18 },
  cta: {
    width: '100%',
    height: layout.ctaHeight,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 10,
  },
  ctaText: { ...typography.button, color: colors.textWhite },
  link: {
    ...typography.buttonSecondary,
    color: colors.brand,
    textAlign: 'center',
    marginTop: 14,
    textDecorationLine: 'underline',
  },
});
