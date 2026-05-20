import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { useMemo } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useReferenceMotions } from '../../lib/referenceMotions';
import { useMyAnalyses } from '../../lib/userAnalyses';
import type { AnalysisDoc, ReferenceMotion, SkillLevel } from '../../types/analysis';
import {
  colors,
  gradients,
  layout,
  radius,
  spacing,
  typography,
} from '../../theme';

// 메인 홈 (design.md §6 "4가지 상태" 확정 스펙).
// 파일럿: 게스트 + 폴스포츠 고정 → 상태 A(분석 기록 있음) / B(첫 분석 전)만 사용.
// 상태 C/D 는 멀티종목·온보딩 영역(루트 CLAUDE.md "MVP 범위 밖").

const SPORT_LABEL = '폴스포츠';
const LEVEL_LABEL: Record<SkillLevel, string> = {
  basic: '기본기',
  intermediate: '중급',
  advanced: '고급',
};

function formatDate(epochMs: number): string {
  const d = new Date(epochMs);
  return `${d.getMonth() + 1}월 ${d.getDate()}일`;
}

function averageScore(analyses: AnalysisDoc[]): number | null {
  const scores = analyses
    .map((a) => a.result?.overallScore)
    .filter((s): s is number => typeof s === 'number');
  if (scores.length === 0) return null;
  return Math.round(scores.reduce((sum, s) => sum + s, 0) / scores.length);
}

export default function Home() {
  const router = useRouter();
  const { analyses } = useMyAnalyses({ doneOnly: true });
  const { motions } = useReferenceMotions();

  const recent = analyses[0] ?? null;
  const avg = useMemo(() => averageScore(analyses), [analyses]);
  const hasGrowth = analyses.length >= 2;

  // 오늘 도전해볼 동작: 기본기 우선 → 중급 → 고급, 최대 3개
  const challenges = useMemo<ReferenceMotion[]>(() => {
    const order: SkillLevel[] = ['basic', 'intermediate', 'advanced'];
    return [...motions]
      .sort((a, b) => order.indexOf(a.level) - order.indexOf(b.level))
      .slice(0, 3);
  }, [motions]);

  return (
    <View style={styles.container}>
      {/* 상단 브랜드 그라디언트 영역 (§6 상태 A 헤더) */}
      <LinearGradient
        colors={gradients.homeTop.colors}
        locations={gradients.homeTop.locations}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 0.08 }}
        style={styles.topArea}
      >
        <Text style={styles.sportTitle}>{SPORT_LABEL}</Text>
        <Text style={styles.sportSub}>
          {recent
            ? `최근 분석 ${formatDate(recent.createdAt)}${avg != null ? ` · 평균 ${avg}점` : ''}`
            : 'AI 코치와 함께 자세를 다듬어 보세요'}
        </Text>
      </LinearGradient>

      {/* 카드 영역 (흰→#FFF0EE) */}
      <LinearGradient
        colors={gradients.homeCard.colors}
        style={styles.cardArea}
      >
        <ScrollView
          contentContainerStyle={styles.cardContent}
          showsVerticalScrollIndicator={false}
        >
          {recent ? (
            <RecentAnalysisCard
              doc={recent}
              onPress={() =>
                router.push({
                  pathname: '/analysis/result',
                  params: {
                    mode: recent.mode,
                    name: recent.fileName,
                    analysisId: recent.analysisId,
                    referenceMotionId:
                      recent.result?.comparison.mode === 'mode1'
                        ? recent.result.comparison.referenceMotionId
                        : undefined,
                    referenceMotionName:
                      recent.result?.comparison.mode === 'mode1'
                        ? recent.result.comparison.referenceMotionName
                        : undefined,
                  },
                })
              }
            />
          ) : (
            <EmptyAnalysisCard onPress={() => router.push('/(tabs)/analyze')} />
          )}

          <Text style={styles.sectionTitle}>오늘 도전해볼 동작</Text>
          {challenges.length > 0 ? (
            challenges.map((m) => (
              <ChallengeRow
                key={m.motionId}
                motion={m}
                onPress={() =>
                  router.push({
                    pathname: '/analysis/reference',
                  })
                }
              />
            ))
          ) : (
            <View style={styles.challengeEmpty}>
              <Text style={styles.challengeEmptyText}>
                기준 동작이 곧 추가돼요. 먼저 내 영상부터 분석해볼 수도 있어요.
              </Text>
            </View>
          )}

          <Text style={styles.sectionTitle}>성장 그래프</Text>
          {hasGrowth ? (
            <GrowthCard analyses={analyses} />
          ) : (
            <GrowthLockedCard />
          )}
        </ScrollView>
      </LinearGradient>
    </View>
  );
}

function RecentAnalysisCard({
  doc,
  onPress,
}: {
  doc: AnalysisDoc;
  onPress: () => void;
}) {
  const motionName =
    doc.result?.comparison.mode === 'mode1'
      ? doc.result.comparison.referenceMotionName
      : '내 동작 분석';
  const score = doc.result?.overallScore ?? 0;
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      style={({ pressed }) => [styles.recentCard, pressed && styles.cardPressed]}
    >
      <View style={styles.recentLeft}>
        <Text style={styles.recentSport}>{SPORT_LABEL}</Text>
        <Text style={styles.recentMotion} numberOfLines={1}>
          {motionName}
        </Text>
        <Text style={styles.recentDate}>{formatDate(doc.createdAt)}</Text>
      </View>
      <View style={styles.recentScore}>
        <Text style={styles.recentScoreValue}>{score}</Text>
      </View>
    </Pressable>
  );
}

function EmptyAnalysisCard({ onPress }: { onPress: () => void }) {
  // design.md §6 상태 B: "프로와 얼마나 가까운지 확인해봐요!" + 첫 분석하기 그라디언트 버튼
  return (
    <View style={styles.emptyCard}>
      <Text style={styles.emptyTitle}>프로와 얼마나{'\n'}가까운지 확인해봐요!</Text>
      <Pressable onPress={onPress} accessibilityRole="button">
        <LinearGradient
          colors={gradients.brandButton.colors}
          locations={gradients.brandButton.locations}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={styles.emptyCta}
        >
          <Text style={styles.emptyCtaText}>첫 분석하기</Text>
        </LinearGradient>
      </Pressable>
    </View>
  );
}

function ChallengeRow({
  motion,
  onPress,
}: {
  motion: ReferenceMotion;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      style={({ pressed }) => [styles.challengeRow, pressed && styles.cardPressed]}
    >
      <View style={styles.challengeThumb}>
        <Ionicons name="play" size={22} color={colors.brand} />
      </View>
      <View style={styles.challengeText}>
        <Text style={styles.challengeName} numberOfLines={1}>
          {motion.name}
        </Text>
        <Text style={styles.challengeLevel}>{LEVEL_LABEL[motion.level]}</Text>
      </View>
      <Ionicons name="chevron-forward" size={20} color={colors.textDisabled} />
    </Pressable>
  );
}

function GrowthCard({ analyses }: { analyses: AnalysisDoc[] }) {
  // MVP: 실제 꺾은선 차트는 #7-follow Victory Native (CLAUDE.md 차트 라이브러리).
  // 지금은 최근 5건 점수 텍스트 라인으로 간이 표시 — 데이터 있음을 보여주는 정도.
  const last5 = analyses.slice(0, 5).reverse();
  return (
    <View style={styles.growthCard}>
      <View style={styles.growthBars}>
        {last5.map((a) => {
          const score = a.result?.overallScore ?? 0;
          return (
            <View key={a.analysisId} style={styles.growthCol}>
              <View
                style={[
                  styles.growthBar,
                  { height: `${Math.max(10, Math.min(100, score))}%` },
                ]}
              />
              <Text style={styles.growthLabel}>{score}</Text>
            </View>
          );
        })}
      </View>
      <Text style={styles.growthCaption}>최근 {last5.length}회 분석 점수</Text>
    </View>
  );
}

function GrowthLockedCard() {
  return (
    <View style={styles.growthLocked}>
      <Ionicons name="bar-chart-outline" size={28} color={colors.brand} />
      <Text style={styles.growthLockedText}>
        분석을 2번 이상 하면 성장 그래프를 볼 수 있어요.
      </Text>
    </View>
  );
}

const TOP_AREA_HEIGHT = 160;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  topArea: {
    height: TOP_AREA_HEIGHT,
    paddingTop: layout.safeAreaTop,
    paddingHorizontal: spacing.screenX,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sportTitle: { ...typography.heading, color: colors.textWhite },
  sportSub: { ...typography.caption, color: colors.textWhite, marginTop: 6, opacity: 0.92 },
  cardArea: {
    flex: 1,
    borderTopLeftRadius: 17.16,
    borderTopRightRadius: 17.16,
    marginTop: -16, // 상단과 살짝 겹쳐 그라디언트 카드 모서리 강조 (§6)
  },
  cardContent: {
    paddingTop: 20,
    paddingHorizontal: spacing.screenX,
    paddingBottom: 24,
    gap: 14,
  },
  recentCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
    gap: 14,
  },
  cardPressed: { opacity: 0.6 },
  recentLeft: { flex: 1, gap: 4 },
  recentSport: { ...typography.boxLabel, color: colors.brand },
  recentMotion: { ...typography.listTitle, color: colors.textPrimary },
  recentDate: { ...typography.caption, color: colors.textSecondary, marginTop: 2 },
  recentScore: {
    width: 95,
    height: 95,
    borderRadius: 47.5,
    backgroundColor: colors.brandTint,
    alignItems: 'center',
    justifyContent: 'center',
  },
  recentScoreValue: { ...typography.score, color: colors.brand },
  emptyCard: {
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding + 4,
    gap: 16,
    alignItems: 'flex-start',
  },
  emptyTitle: { ...typography.listTitle, color: colors.textPrimary },
  emptyCta: {
    paddingHorizontal: 22,
    paddingVertical: 12,
    borderRadius: 999, // pill (design.md §6 상태 B)
  },
  emptyCtaText: { ...typography.button, color: colors.textWhite },
  sectionTitle: { ...typography.sectionTitle, color: colors.textPrimary, marginTop: 4 },
  challengeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: 12,
  },
  challengeThumb: {
    width: 51.48,
    height: 51.48,
    borderRadius: radius.listItem,
    backgroundColor: colors.brandTint,
    alignItems: 'center',
    justifyContent: 'center',
  },
  challengeText: { flex: 1, gap: 4 },
  challengeName: { ...typography.listTitle, color: colors.textPrimary },
  challengeLevel: { ...typography.caption, color: colors.textSecondary },
  challengeEmpty: {
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
  },
  challengeEmptyText: { ...typography.caption, color: colors.textSecondary },
  growthCard: {
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
    gap: 12,
  },
  growthBars: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 8,
    height: 120,
  },
  growthCol: { flex: 1, alignItems: 'center', gap: 6 },
  growthBar: {
    width: '70%',
    backgroundColor: colors.brand,
    borderRadius: 6,
  },
  growthLabel: { ...typography.captionSmall, color: colors.textSecondary },
  growthCaption: { ...typography.caption, color: colors.textSecondary },
  growthLocked: {
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderStyle: 'dashed', // §6 상태 B "점선 테두리"
    borderRadius: radius.card,
    padding: spacing.cardPadding + 6,
    alignItems: 'center',
    gap: 10,
  },
  growthLockedText: { ...typography.caption, color: colors.textSecondary, textAlign: 'center' },
});
