import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { GrowthChart } from '../../components/GrowthChart';
import { GrowthMotionBars } from '../../components/GrowthMotionBars';
import { OctagonScore } from '../../components/OctagonScore';
import {
  defaultGrowthMode,
  motionDeltas,
  weeklyAverages,
} from '../../lib/growthSelectors';
import { useReferenceMotions } from '../../lib/referenceMotions';
import { useMyAnalyses } from '../../lib/userAnalyses';
import type {
  AnalysisDoc,
  AnalysisMode,
  ReferenceMotion,
  SkillLevel,
} from '../../types/analysis';
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

// 홈 헤더 "(평균 N점)" — 전체 누적 평균(모드 혼합). 성장 그래프(D-02 모드 분리)와
// 성격이 다르므로 유지 결정(30-CONTEXT Claude's Discretion / D-01 재량): 헤더는
// "지금까지 전체 누적" 맥락이라 그래프의 모드별 주별 평균과 역할이 구분되고, 삭제 시
// 정보 손실이라 유지가 더 정확하다. 그래프 카드에는 이 혼합 평균을 절대 노출하지 않는다.
// (30-REVIEW WR-01) NaN·scoreSuppressed 방어는 growthSelectors.hasUsableGrowthScore
// 와 동일 기준(HIGH-1 신뢰 계약) — typeof NaN === 'number' 라 Number.isFinite 필수,
// 결과화면에서 숨긴 점수(scoreSuppressed)는 헤더 평균에도 되살리지 않는다.
function averageScore(analyses: AnalysisDoc[]): number | null {
  const scores = analyses
    .map((a) => a.result)
    .filter((r): r is NonNullable<typeof r> => !!r && r.scoreSuppressed !== true)
    .map((r) => r.overallScore)
    .filter((s): s is number => typeof s === 'number' && Number.isFinite(s));
  if (scores.length === 0) return null;
  return Math.round(scores.reduce((sum, s) => sum + s, 0) / scores.length);
}

export default function Home() {
  const router = useRouter();
  const { analyses } = useMyAnalyses({ doneOnly: true });
  const { motions } = useReferenceMotions();

  const recent = analyses[0] ?? null;
  const avg = useMemo(() => averageScore(analyses), [analyses]);
  // (D-03 null 분기) 성장 카드 렌더 게이트 = defaultGrowthMode !== null. 단순 건수
  // (analyses.length>=2)가 아니라 "어느 한 모드라도 주별 점 2개 이상"이 기준 — 같은 주
  // 2건은 주별 평균 점 1개뿐이라 추이를 못 그리므로, 주별 기준과 정합하는 게이트로 교체한다.
  const growthBaseMode = useMemo(() => defaultGrowthMode(analyses), [analyses]);

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
              {newest.name} 기준모션 추가
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
          {growthBaseMode !== null ? (
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
  // mode3 제목 구체화 (belle 08-31) — history.tsx motionLabel 과 같은 규칙:
  // recognizedMotionId → 기준 모션 한글명 (recognizedMotionName 은 원시 id 라 표시 불가).
  const { motions } = useReferenceMotions();
  const comparison = doc.result?.comparison;
  const recognizedName =
    comparison?.mode === 'mode3' && comparison.recognizedMotionId
      ? motions.find((m) => m.motionId === comparison.recognizedMotionId)?.name
      : undefined;
  const motionName =
    comparison?.mode === 'mode1'
      ? comparison.referenceMotionName
      : recognizedName ?? '내 동작 분석';
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

// 보기 전환 탭 (D-08) — [추이]/[동작별]. 모드 토글(D-02)은 [추이]에만 노출(D-09).
const VIEW_OPTIONS = [
  { value: 'trend', label: '추이' },
  { value: 'byMotion', label: '동작별' },
] as const;
// 모드 토글 카피 = history.tsx modeBadge 재사용 ('프로 비교'=mode1 / '내 기록'=mode3, D-02).
const MODE_OPTIONS: ReadonlyArray<{ value: AnalysisMode; label: string }> = [
  { value: 'mode1', label: '프로 비교' },
  { value: 'mode3', label: '내 기록' },
];
// 동작별 리스트 표시 상한 (Claude 재량 — 카드 높이 폭주 방지, 최신 활동순 상위만).
// 델타·평균은 재계산하지 않고 growthSelectors.motionDeltas 결과를 slice 만 한다.
const MOTION_ROW_CAP = 4;
// 추이 차트 표시 주 상한 (30-REVIEW WR-02 — 구 구현 slice(0,6) 상한 정신 계승).
// GrowthChart viewBox 폭 320(innerW 284)에서 주 라벨("12/29주" fontSize 9 ≈ 30px)이
// 겹치지 않는 상한 = 8. 최근 주 우선(slice 음수 인덱스), 평균·델타 재계산 없음 —
// MOTION_ROW_CAP 과 동일한 표시층 slice 패턴. 카드 높이(GROWTH_CARD_CONTENT_HEIGHT)
// 계약(D-08)은 무접촉.
const TREND_WEEK_CAP = 8;
// 콘텐츠 영역 단일 높이 상수 (D-08 / MEDIUM-1). [추이](GrowthChart H=132)·[동작별]·
// 빈 상태·GrowthLockedCard 본문이 전부 이 값을 minHeight 로 공유해 보기·상태 전환 시
// 카드 바깥 레이아웃이 흔들리지 않는다. 값 = GrowthChart 132 + 여백 20 기준.
const GROWTH_CARD_CONTENT_HEIGHT = 152;

// 성장 카드 전용 소형 세그먼트 토글 (BodyProfileForm Segmented analog — import 대신
// 이식해 스타일 결합 방지, RecentAnalysisCard 선례). 활성 탭 = chipSelected 관례
// (colors.brandTint bg + colors.brand border/text, D-03 "활성 브랜드색 명확 표시").
function GrowthToggle<T extends string>({
  options,
  selected,
  groupLabel,
  onSelect,
}: {
  options: ReadonlyArray<{ value: T; label: string }>;
  selected: T;
  groupLabel: string;
  onSelect: (v: T) => void;
}) {
  return (
    <View style={styles.toggleRow}>
      {options.map((opt) => {
        const isSel = selected === opt.value;
        return (
          <Pressable
            key={opt.value}
            onPress={() => onSelect(opt.value)}
            accessibilityRole="button"
            accessibilityState={{ selected: isSel }}
            accessibilityLabel={`${groupLabel} ${opt.label}${isSel ? ', 선택됨' : ''}`}
            hitSlop={6}
            style={[styles.toggleTab, isSel && styles.toggleTabSelected]}
          >
            <Text style={[styles.toggleTabText, isSel && styles.toggleTabTextSelected]}>
              {opt.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

function GrowthCard({ analyses }: { analyses: AnalysisDoc[] }) {
  // 2층 토글 (30-CONTEXT D-02/D-03/D-08/D-09): 보기(추이/동작별) × 모드(프로 비교/내 기록).
  const [view, setView] = useState<'trend' | 'byMotion'>('trend');
  // 모드는 사용자가 토글을 누른 뒤에만 non-null(override). 기본값에 defaultGrowthMode 를
  // 넣지 않는다 — analyses 가 비동기 도착이라 useState 초기화 시점엔 [] 여서 stale 됨.
  const [modeOverride, setModeOverride] = useState<AnalysisMode | null>(null);

  // 유효 모드 = override(사용자 선택) ?? defaultGrowthMode(마지막 분석 모드 + 폴백, D-03).
  // GrowthCard 는 부모 게이트(defaultGrowthMode !== null)를 통과했을 때만 렌더되므로
  // baseMode 는 사실상 non-null. 'mode3' 폴백은 타입 방어(도달 불가).
  const baseMode = useMemo(() => defaultGrowthMode(analyses), [analyses]);
  const effectiveMode: AnalysisMode = modeOverride ?? baseMode ?? 'mode3';

  const trendPoints = useMemo(
    () => weeklyAverages(analyses, effectiveMode).slice(-TREND_WEEK_CAP),
    [analyses, effectiveMode],
  );
  const motionRows = useMemo(
    () => motionDeltas(analyses).slice(0, MOTION_ROW_CAP),
    [analyses],
  );

  return (
    <View style={styles.growthCard}>
      <Text style={styles.growthHeader}>주별 평균 성장 그래프</Text>
      <GrowthToggle
        options={VIEW_OPTIONS}
        selected={view}
        groupLabel="성장 보기"
        onSelect={setView}
      />
      {/* 모드 토글은 [추이] 보기에만 (D-09: [동작별]은 통합 리스트가 배지로 모드 구분). */}
      {view === 'trend' && (
        <GrowthToggle
          options={MODE_OPTIONS}
          selected={effectiveMode}
          groupLabel="비교 모드"
          onSelect={setModeOverride}
        />
      )}
      <View style={styles.growthBody}>
        {view === 'trend' ? (
          // 주별 점 2개 이상이면 추이선, 미만이면 같은 높이 안내(D-03: 명시 선택 모드가
          // 부족해도 빈 화면 금지 — 기본값 폴백과 달리 사용자 선택은 존중하되 안내 카피).
          trendPoints.length >= 2 ? (
            <GrowthChart points={trendPoints} />
          ) : (
            <View style={styles.growthEmpty}>
              <Text style={styles.growthEmptyText}>
                이 모드는 주별 데이터가{'\n'}아직 부족해요
              </Text>
            </View>
          )
        ) : motionRows.length > 0 ? (
          <GrowthMotionBars rows={motionRows} />
        ) : (
          <View style={styles.growthEmpty}>
            <Text style={styles.growthEmptyText}>
              동작별로 비교할 기록이{'\n'}아직 부족해요
            </Text>
          </View>
        )}
      </View>
    </View>
  );
}

function GrowthLockedCard() {
  // Figma 1:794: 솔리드 회색 박스 + 가운데 카피. 아이콘·점선 없음.
  // (D-03 null 분기) 카피 정정: "분석을 2번 이상 하면"은 주별 평균 기준과 불일치
  // (같은 주 2건 = 주별 점 1개)하므로 서로 다른 주 기준으로 바로잡는다. 본문 minHeight 는
  // GrowthCard 본문과 동일한 GROWTH_CARD_CONTENT_HEIGHT 를 공유(카드 높이 일정, MEDIUM-1).
  return (
    <View style={styles.growthLocked}>
      <Text style={styles.growthLockedText}>
        서로 다른 주에 분석을 2번 이상 하면{'\n'}성장 그래프가 보여요
      </Text>
    </View>
  );
}

// Figma 1:719 — 프로필 + 종목 + 부텍스트 + NEW 배너 다 들어가는 높이.
// F4(26-05): NEW 배너 아래쪽이 -16 겹침(cardArea marginTop)으로 카드 상단과 밀착돼
// 있어 높이를 240→260 으로 +20 보정 — 배너 하단과 카드 상단 사이 간격을 12 이상
// 확보한다 (배너 위쪽 간격 marginTop 16 은 유지). 배너 비주얼 자체는 불변.
const TOP_AREA_HEIGHT = 260;

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
  toggleRow: { flexDirection: 'row', gap: 8 },
  toggleTab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    borderRadius: radius.button,
    backgroundColor: colors.bg,
  },
  // 활성 탭 = chipSelected 관례 (brandTint bg + brand border/text) — D-03 브랜드색 명확 표시.
  toggleTabSelected: { backgroundColor: colors.brandTint, borderColor: colors.brand },
  toggleTabText: { ...typography.buttonSecondary, color: colors.textPrimary },
  toggleTabTextSelected: { color: colors.brand },
  // [추이]/[동작별] 공통 본문 컨테이너 — 단일 높이 상수로 카드 높이 고정 (MEDIUM-1).
  growthBody: {
    minHeight: GROWTH_CARD_CONTENT_HEIGHT,
    justifyContent: 'center',
  },
  growthEmpty: { alignItems: 'center', justifyContent: 'center' },
  growthEmptyText: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
  },
  growthLocked: {
    backgroundColor: '#EFEFEF', // Figma 1:794 — 솔리드 회색 박스
    borderRadius: radius.card,
    minHeight: GROWTH_CARD_CONTENT_HEIGHT, // GrowthCard 본문과 동일 높이 공유 (MEDIUM-1)
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
