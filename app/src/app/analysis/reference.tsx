import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useReferenceMotions } from '../../lib/referenceMotions';
import type { ReferenceMotion, SkillLevel } from '../../types/analysis';
import { colors, layout, radius, spacing, typography } from '../../theme';

// 기준 모션 선택 (plan.md #9, IA AC-ANAL-001, design.md §6).
// Mode1(전문가 비교) 진입 시 사용. analyze.tsx → 영상 선택 → 모드 선택 → 여기 → /analysis/loading.
// 데이터 소스는 lib/referenceMotions 에 격리 (지금 Firestore, 나중에 GET /reference 로 교체 가능).

type Tab = SkillLevel;

const TABS: { key: Tab; label: string }[] = [
  { key: 'basic', label: '기본기' },
  { key: 'intermediate', label: '중급' },
  { key: 'advanced', label: '고급' },
];

export default function ReferenceSelect() {
  const router = useRouter();
  const { name, motionId: preselectId } = useLocalSearchParams<{
    name?: string;
    motionId?: string;
  }>();
  const { motions, loading, error } = useReferenceMotions();

  const [tab, setTab] = useState<Tab>('basic');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // 홈 챌린지 카드처럼 특정 동작을 지정해서 들어온 경우, motions 로딩이 끝나면
  // 1회만 해당 동작의 레벨 탭으로 점프하고 미리 선택. 이후 사용자 탭 전환은 그대로 둠.
  const preselectAppliedRef = useRef(false);
  useEffect(() => {
    if (preselectAppliedRef.current) return;
    if (!preselectId || motions.length === 0) return;
    const target = motions.find((m) => m.motionId === preselectId);
    if (!target) return;
    setTab(target.level);
    setSelectedId(target.motionId);
    preselectAppliedRef.current = true;
  }, [preselectId, motions]);

  const byLevel = useMemo(() => motions.filter((m) => m.level === tab), [motions, tab]);
  const selected = motions.find((m) => m.motionId === selectedId) ?? null;

  // 탭 전환 시 현재 선택이 다른 레벨이면 해제 (혼동 방지)
  const switchTab = (next: Tab) => {
    setTab(next);
    if (selected && selected.level !== next) setSelectedId(null);
  };

  const startAnalysis = () => {
    if (!selectedId) return;
    router.push({
      pathname: '/analysis/loading',
      params: {
        mode: 'mode1',
        name: name ?? '',
        referenceMotionId: selectedId,
        // 결과 화면 표시용. #7-follow 실데이터 붙으면 Firestore 결과 문서가
        // referenceMotionName 을 직접 들고 옴 → 이 param 은 자연스럽게 폐기.
        referenceMotionName: selected?.name ?? '',
      },
    });
  };

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>비교할 프로 동작을{'\n'}골라주세요.</Text>
      <Text style={styles.sub}>정은지 선수의 동작 중 하나를 기준으로 분석해요.</Text>

      <View style={styles.tabs}>
        {TABS.map((t) => {
          const active = t.key === tab;
          return (
            <Pressable
              key={t.key}
              onPress={() => switchTab(t.key)}
              accessibilityRole="button"
              accessibilityState={{ selected: active }}
              style={[styles.tab, active && styles.tabActive]}
            >
              <Text style={[styles.tabLabel, active && styles.tabLabelActive]}>
                {t.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <ScrollView
        style={styles.list}
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
      >
        {loading && <Text style={styles.placeholder}>불러오는 중...</Text>}
        {!loading && error && <Text style={styles.error}>{error}</Text>}
        {!loading && !error && byLevel.length === 0 && (
          <Text style={styles.placeholder}>
            아직 등록된 기준 동작이 없어요.
          </Text>
        )}
        {byLevel.map((m) => (
          <MotionCard
            key={m.motionId}
            motion={m}
            selected={m.motionId === selectedId}
            onPress={() => setSelectedId(m.motionId)}
          />
        ))}
      </ScrollView>

      <Pressable
        onPress={startAnalysis}
        disabled={!selectedId}
        accessibilityRole="button"
        accessibilityState={{ disabled: !selectedId }}
        style={({ pressed }) => [
          styles.cta,
          (!selectedId || pressed) && styles.ctaDimmed,
        ]}
      >
        <Text style={styles.ctaText}>
          {selected ? `${selected.name}으로 분석 시작` : '분석 시작'}
        </Text>
      </Pressable>
    </View>
  );
}

function MotionCard({
  motion,
  selected,
  onPress,
}: {
  motion: ReferenceMotion;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      style={({ pressed }) => [
        styles.card,
        selected && styles.cardSelected,
        pressed && styles.cardPressed,
      ]}
    >
      <View style={styles.cardText}>
        <Text style={styles.cardTitle}>{motion.name}</Text>
        <Text style={styles.cardAthlete}>{motion.athleteName}</Text>
        {motion.description && (
          <Text style={styles.cardDesc} numberOfLines={2}>
            {motion.description}
          </Text>
        )}
      </View>
      <Ionicons
        name={selected ? 'checkmark-circle' : 'ellipse-outline'}
        size={24}
        color={selected ? colors.brand : colors.divider}
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
    paddingTop: layout.safeAreaTop,
    paddingHorizontal: spacing.screenX,
    paddingBottom: layout.safeAreaBottom + 24,
  },
  heading: { ...typography.heading, color: colors.textPrimary, marginTop: 12 },
  sub: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 8,
  },
  tabs: {
    flexDirection: 'row',
    marginTop: 24,
    gap: 8,
  },
  tab: {
    flex: 1,
    height: 40,
    borderRadius: radius.button,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    backgroundColor: colors.bg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabActive: {
    backgroundColor: colors.brand,
    borderColor: colors.brand,
  },
  tabLabel: {
    ...typography.boxLabel,
    color: colors.textSecondary,
  },
  tabLabelActive: { color: colors.textWhite },
  list: { flex: 1, marginTop: 16 },
  listContent: { gap: 10, paddingBottom: 24 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
  },
  cardSelected: { borderColor: colors.brand, backgroundColor: colors.brandTint },
  cardPressed: { opacity: 0.6 },
  cardText: { flex: 1 },
  cardTitle: { ...typography.listTitle, color: colors.textPrimary },
  cardAthlete: {
    ...typography.caption,
    color: colors.brand,
    marginTop: 4,
  },
  cardDesc: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 6,
  },
  placeholder: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 32,
  },
  error: {
    ...typography.caption,
    color: colors.inputError,
    textAlign: 'center',
    marginTop: 32,
  },
  cta: {
    height: layout.ctaHeight,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaDimmed: { opacity: 0.4 },
  ctaText: { ...typography.button, color: colors.textWhite },
});
