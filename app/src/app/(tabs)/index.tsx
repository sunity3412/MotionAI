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
import { GrowthChart } from '../../components/GrowthChart';
import { OctagonScore } from '../../components/OctagonScore';
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

// 도전 리스트 컨텍스트 카피 (Figma 1:719: "고급 새로 추가됨" / "중급 도전 추천" / "입문 기본기").
// 같은 레벨 2번째 이상은 단순 레벨명만.
function challengeCopy(motion: ReferenceMotion, isFirstOfLevel: boolean): string {
  const lv = LEVEL_LABEL[motion.level];
  if (!isFirstOfLevel) return lv;
  if (motion.level === 'basic') return `입문 ${lv}`;
  if (motion.level === 'intermediate') return `${lv} 도전 추천`;
  return `${lv} 새로 추가됨`;
}

// Figma 1:719: "마지막 접속일 | 2일 전" — 한 달 안은 상대, 더 오래는 절대.
function formatRelative(epochMs: number): string {
  const diffDays = Math.floor((Date.now() - epochMs) / (24 * 60 * 60 * 1000));
  if (diffDays <= 0) return '오늘';
  if (diffDays === 1) return '어제';
  if (diffDays < 7) return `${diffDays}일 전`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}주 전`;
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

  // 오늘 도전해볼 동작: 고급 우선 → 중급 → 기본기 (Figma 1:719 — 챌린지 욕구 자극 우선), 최대 3개
  const challenges = useMemo<ReferenceMotion[]>(() => {
    const order: SkillLevel[] = ['advanced', 'intermediate', 'basic'];
    return [...motions]
      .sort((a, b) => order.indexOf(a.level) - order.indexOf(b.level))
      .slice(0, 3);
  }, [motions]);

  // NEW 공지 배너: 가장 최근 updatedAt 모션. 모션이 없으면 배너 숨김.
  const newest = useMemo<ReferenceMotion | null>(() => {
    if (motions.length === 0) return null;
    return [...motions].sort(
      (a, b) => (b.updatedAt ?? 0) - (a.updatedAt ?? 0),
    )[0];
  }, [motions]);

  return (
    <View style={styles.container}>
      {/* 상단 브랜드 그라디언트 영역 (§6 상태 A 헤더 + Figma 1:719: 프로필 + NEW 배너) */}
      <LinearGradient
        colors={gradients.homeTop.colors}
        locations={gradients.homeTop.locations}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 0.08 }}
        style={styles.topArea}
      >
        <View style={styles.avatar}>
          <Ionicons name="person" size={24} color={colors.textWhite} />
        </View>
        <Text style={styles.sportTitle}>{SPORT_LABEL}</Text>
        <Text style={styles.sportSub}>
          {recent
            ? `마지막 접속일 | ${formatRelative(recent.createdAt)}${avg != null ? ` (평균 ${avg}점)` : ''}`
            : 'AI 코치와 함께 자세를 다듬어 보세요'}
        </Text>
        {newest && (
          <View style={styles.newsBanner}>
            <View style={styles.newsBadge}>
              <Text style={styles.newsBadgeText}>NEW</Text>
            </View>
            <Text style={styles.newsText} numberOfLines={1}>
              {newest.name} 기준모션이 추가되었어요.
            </Text>
          </View>
        )}
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

          <View style={styles.sectionHead}>
            <Text style={styles.sectionTitle}>
              {recent ? '오늘 도전해볼 동작' : '아래 동작으로 시작해보세요'}
            </Text>
            {motions.length > 0 && (
              <Pressable
                onPress={() => router.push('/analysis/reference')}
                accessibilityRole="link"
                hitSlop={8}
              >
                <Text style={styles.sectionMore}>전체보기 ›</Text>
              </Pressable>
            )}
          </View>
          {challenges.length > 0 ? (
            challenges.map((m, idx) => {
              const isFirstOfLevel = !challenges
                .slice(0, idx)
                .some((prev) => prev.level === m.level);
              return (
                <ChallengeRow
                  key={m.motionId}
                  motion={m}
                  contextCopy={challengeCopy(m, isFirstOfLevel)}
                  onPress={() =>
                    // 챌린지 카드 = 이 동작으로 mode1 분석하겠다는 의도. 모드 선택을
                    // 건너뛰고 분석탭의 영상 선택 단계로 바로 보낸다 (belle P1 #7).
                    router.push({
                      pathname: '/(tabs)/analyze',
                      params: { referenceMotionId: m.motionId },
                    })
                  }
                />
              );
            })
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
        <Text style={styles.recentDate}>최근 분석 | {formatRelative(doc.createdAt)}</Text>
      </View>
      <OctagonScore score={score} />
    </Pressable>
  );
}

function EmptyAnalysisCard({ onPress }: { onPress: () => void }) {
  // Figma 1:794: 좌측 제목+서브 / 우측 pill CTA. 보조 카피로 분석 흐름 예고.
  return (
    <View style={styles.emptyCard}>
      <View style={styles.emptyTextCol}>
        <Text style={styles.emptyTitle}>프로와 얼마나{'\n'}가까운지 확인해봐요!</Text>
        <Text style={styles.emptySub}>AI가 자세 분석을 시작해요.</Text>
      </View>
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
  contextCopy,
  onPress,
}: {
  motion: ReferenceMotion;
  contextCopy: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      style={({ pressed }) => [styles.challengeRow, pressed && styles.cardPressed]}
    >
      <View style={styles.challengeThumb} />
      <View style={styles.challengeText}>
        <Text style={styles.challengeName} numberOfLines={1}>
          {motion.name}
        </Text>
        <Text style={styles.challengeLevel}>{contextCopy}</Text>
      </View>
      <Ionicons name="chevron-forward" size={20} color={colors.textDisabled} />
    </Pressable>
  );
}

function GrowthCard({ analyses }: { analyses: AnalysisDoc[] }) {
  // 분석 점수(overallScore) 추이 꺾은선. Figma 1:719 — 차트 안 상단 라벨.
  const recent = analyses.slice(0, 6).reverse(); // 최근 6건, 오래된→최근
  const scores = recent.map((a) => a.result?.overallScore ?? 0);
  return (
    <View style={styles.growthCard}>
      <Text style={styles.growthHeader}>이번주 성장 그래프</Text>
      <GrowthChart scores={scores} />
    </View>
  );
}

function GrowthLockedCard() {
  // Figma 1:794: 솔리드 회색 박스 + 가운데 카피. 아이콘·점선 없음.
  return (
    <View style={styles.growthLocked}>
      <Text style={styles.growthLockedText}>
        분석을 2번 이상 하면{'\n'}AI 그래프가 보여요
      </Text>
    </View>
  );
}

const TOP_AREA_HEIGHT = 240; // Figma 1:719 — 프로필 + 종목 + 부텍스트 + NEW 배너 다 들어가는 높이

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  topArea: {
    height: TOP_AREA_HEIGHT,
    paddingTop: layout.safeAreaTop,
    paddingHorizontal: spacing.screenX,
    alignItems: 'center',
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(255,255,255,0.22)',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
    marginBottom: 8,
  },
  sportTitle: { ...typography.heading, color: colors.textWhite },
  sportSub: { ...typography.caption, color: colors.textWhite, marginTop: 6, opacity: 0.92 },
  newsBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'stretch',
    backgroundColor: 'rgba(255,255,255,0.16)',
    borderRadius: 999,
    paddingVertical: 6,
    paddingLeft: 6,
    paddingRight: 14,
    marginTop: 16,
  },
  newsBadge: {
    backgroundColor: colors.bg,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 3,
    marginRight: 10,
  },
  newsBadgeText: { ...typography.captionSmall, color: colors.brand, fontWeight: '700' },
  newsText: { ...typography.caption, color: colors.textWhite, flexShrink: 1 },
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
  emptyCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding + 4,
    gap: 12,
  },
  emptyTextCol: { flex: 1, gap: 6 },
  emptyTitle: { ...typography.listTitle, color: colors.textPrimary },
  emptySub: { ...typography.caption, color: colors.textSecondary },
  emptyCta: {
    paddingHorizontal: 18,
    paddingVertical: 11,
    borderRadius: 999, // pill (Figma 1:794)
  },
  emptyCtaText: { ...typography.button, color: colors.textWhite },
  sectionHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  sectionTitle: { ...typography.sectionTitle, color: colors.textPrimary },
  sectionMore: { ...typography.caption, color: colors.textSecondary },
  challengeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 10,
    borderBottomWidth: layout.cardBorderWidth,
    borderBottomColor: colors.divider,
  },
  challengeThumb: {
    width: 51.48,
    height: 51.48,
    borderRadius: radius.listItem,
    backgroundColor: '#D9D9D9',
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
    gap: 8,
  },
  growthHeader: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  growthLocked: {
    backgroundColor: '#EFEFEF', // Figma 1:794 — 솔리드 회색 박스
    borderRadius: radius.card,
    paddingVertical: spacing.cardPadding + 18,
    paddingHorizontal: spacing.cardPadding,
    alignItems: 'center',
    justifyContent: 'center',
  },
  growthLockedText: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
  },
});
