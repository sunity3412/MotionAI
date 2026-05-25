import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { saveSampleAnalysis } from '../../lib/simulationWriter';
import {
  SAMPLE_SCENARIOS,
  type SampleScenario,
} from '../../lib/simulatedResult';
import { colors, layout, radius, spacing, typography } from '../../theme';

// 샘플 결과 미리보기 — 영상 없이 결과 화면을 다양한 시나리오로 시연/검토.
// 실 분석 파이프라인(#7-follow) 켜지면 simulationWriter 와 함께 폐기 대상.

export default function AnalysisSamples() {
  const router = useRouter();
  const [busyId, setBusyId] = useState<string | null>(null);

  const pickScenario = async (scenario: SampleScenario) => {
    if (busyId) return;
    setBusyId(scenario.id);
    try {
      const analysisId = await saveSampleAnalysis(scenario);
      if (!analysisId) {
        setBusyId(null);
        return;
      }
      router.replace({
        pathname: '/analysis/result',
        params: {
          mode: scenario.mode,
          name: `샘플 · ${scenario.label}`,
          analysisId,
          referenceMotionId: scenario.referenceMotionId,
          referenceMotionName: scenario.referenceMotionName,
        },
      });
    } catch (e) {
      if (__DEV__) console.warn('[samples] saveSampleAnalysis failed', e);
      setBusyId(null);
    }
  };

  return (
    <View style={styles.container}>
      <Pressable
        onPress={() => router.back()}
        accessibilityRole="button"
        accessibilityLabel="뒤로 가기"
        hitSlop={10}
        style={({ pressed }) => [styles.backBtn, pressed && styles.backBtnPressed]}
      >
        <Ionicons name="chevron-back" size={26} color={colors.textPrimary} />
      </Pressable>
      <Text style={styles.heading}>샘플 결과{'\n'}미리보기</Text>
      <Text style={styles.sub}>
        영상 없이 결과 화면을 다양한 시나리오로 확인할 수 있어요. 시연·검토용입니다.
      </Text>

      <ScrollView
        style={styles.list}
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
      >
        {SAMPLE_SCENARIOS.map((s) => (
          <ScenarioCard
            key={s.id}
            scenario={s}
            busy={busyId === s.id}
            disabled={busyId != null && busyId !== s.id}
            onPress={() => pickScenario(s)}
          />
        ))}
      </ScrollView>
    </View>
  );
}

function ScenarioCard({
  scenario,
  busy,
  disabled,
  onPress,
}: {
  scenario: SampleScenario;
  busy: boolean;
  disabled: boolean;
  onPress: () => void;
}) {
  const modeLabel = scenario.mode === 'mode1' ? '프로 비교' : '내 기록';
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || busy}
      accessibilityRole="button"
      accessibilityState={{ disabled: disabled || busy }}
      style={({ pressed }) => [
        styles.card,
        (pressed || disabled) && styles.cardDimmed,
      ]}
    >
      <View style={styles.cardText}>
        <View style={styles.cardHeadRow}>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{modeLabel}</Text>
          </View>
          <Text style={styles.scoreText}>{scenario.overall}점</Text>
        </View>
        <Text style={styles.cardTitle}>{scenario.label}</Text>
        <Text style={styles.cardDesc} numberOfLines={2}>
          {scenario.description}
        </Text>
      </View>
      <Ionicons
        name={busy ? 'hourglass-outline' : 'chevron-forward'}
        size={20}
        color={busy ? colors.brand : colors.textDisabled}
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
  backBtn: {
    width: 40,
    height: 40,
    marginLeft: -8,
    marginTop: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backBtnPressed: { opacity: 0.5 },
  heading: { ...typography.heading, color: colors.textPrimary, marginTop: 4 },
  sub: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 8,
  },
  list: { flex: 1, marginTop: 20 },
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
  cardDimmed: { opacity: 0.4 },
  cardText: { flex: 1, gap: 6 },
  cardHeadRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 999,
    backgroundColor: colors.brandTint,
  },
  badgeText: {
    ...typography.caption,
    color: colors.brand,
    fontWeight: '600',
  },
  scoreText: {
    ...typography.boxLabel,
    color: colors.textPrimary,
  },
  cardTitle: { ...typography.listTitle, color: colors.textPrimary },
  cardDesc: {
    ...typography.caption,
    color: colors.textSecondary,
  },
});
