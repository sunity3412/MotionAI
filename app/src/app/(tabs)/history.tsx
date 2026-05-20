import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useMyAnalyses } from '../../lib/userAnalyses';
import type { AnalysisDoc } from '../../types/analysis';
import { colors, layout, radius, spacing, typography } from '../../theme';

// 분석 기록 탭 (IA AC-REC-001).
// 파일럿: 리스트 + 빈 상태만. 필터·삭제·전후비교는 MVP 범위 밖 — IA 5장 참고.

function formatDate(epochMs: number): string {
  const d = new Date(epochMs);
  const yy = String(d.getFullYear()).slice(2);
  return `${yy}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
}

function motionLabel(doc: AnalysisDoc): string {
  if (doc.result?.comparison.mode === 'mode1') {
    return doc.result.comparison.referenceMotionName;
  }
  return '내 동작 분석';
}

function modeBadge(doc: AnalysisDoc): string {
  return doc.mode === 'mode1' ? '프로 비교' : '내 기록';
}

export default function History() {
  const router = useRouter();
  const { analyses, loading, error } = useMyAnalyses({ doneOnly: true });

  if (loading) {
    return (
      <View style={styles.container}>
        <Text style={styles.headerTitle}>기록</Text>
        <Text style={styles.placeholder}>불러오는 중...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <Text style={styles.headerTitle}>기록</Text>
        <Text style={styles.error}>{error}</Text>
      </View>
    );
  }

  if (analyses.length === 0) {
    return (
      <View style={styles.container}>
        <Text style={styles.headerTitle}>기록</Text>
        <View style={styles.emptyWrap}>
          <Ionicons name="time-outline" size={48} color={colors.brand} />
          <Text style={styles.emptyTitle}>아직 분석 기록이 없어요</Text>
          <Text style={styles.emptySub}>
            첫 분석을 시작해보세요. 분석이 끝나면 여기서 다시 볼 수 있어요.
          </Text>
          <Pressable
            onPress={() => router.push('/(tabs)/analyze')}
            accessibilityRole="button"
            style={({ pressed }) => [styles.cta, pressed && styles.ctaDimmed]}
          >
            <Text style={styles.ctaText}>분석 시작하기</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.headerTitle}>기록</Text>
      <Text style={styles.headerSub}>총 {analyses.length}건</Text>
      <ScrollView
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
      >
        {analyses.map((doc) => (
          <Pressable
            key={doc.analysisId}
            onPress={() =>
              router.push({
                pathname: '/analysis/result',
                params: {
                  mode: doc.mode,
                  name: doc.fileName,
                  analysisId: doc.analysisId,
                  referenceMotionId:
                    doc.result?.comparison.mode === 'mode1'
                      ? doc.result.comparison.referenceMotionId
                      : undefined,
                  referenceMotionName:
                    doc.result?.comparison.mode === 'mode1'
                      ? doc.result.comparison.referenceMotionName
                      : undefined,
                },
              })
            }
            accessibilityRole="button"
            style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
          >
            <View style={styles.rowText}>
              <View style={styles.rowHead}>
                <Text style={styles.rowBadge}>{modeBadge(doc)}</Text>
                <Text style={styles.rowDate}>{formatDate(doc.createdAt)}</Text>
              </View>
              <Text style={styles.rowMotion} numberOfLines={1}>
                {motionLabel(doc)}
              </Text>
            </View>
            <Text style={styles.rowScore}>{doc.result?.overallScore ?? 0}</Text>
            <Ionicons name="chevron-forward" size={20} color={colors.textDisabled} />
          </Pressable>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
    paddingTop: layout.safeAreaTop,
    paddingHorizontal: spacing.screenX,
    paddingBottom: layout.safeAreaBottom,
  },
  headerTitle: { ...typography.heading, color: colors.textPrimary, marginTop: 8 },
  headerSub: { ...typography.caption, color: colors.textSecondary, marginTop: 6 },
  list: { gap: 10, paddingVertical: 18, paddingBottom: 24 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
  },
  rowPressed: { opacity: 0.6 },
  rowText: { flex: 1, gap: 6 },
  rowHead: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  rowBadge: {
    ...typography.captionSmall,
    color: colors.textWhite,
    backgroundColor: colors.brand,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
    overflow: 'hidden',
  },
  rowDate: { ...typography.caption, color: colors.textSecondary },
  rowMotion: { ...typography.listTitle, color: colors.textPrimary },
  rowScore: { ...typography.bodyBold, color: colors.brand, minWidth: 44, textAlign: 'right' },
  placeholder: { ...typography.caption, color: colors.textSecondary, marginTop: 32, textAlign: 'center' },
  error: { ...typography.caption, color: colors.inputError, marginTop: 32, textAlign: 'center' },
  emptyWrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    paddingHorizontal: 12,
    paddingBottom: 60,
  },
  emptyTitle: { ...typography.listTitle, color: colors.textPrimary, marginTop: 4 },
  emptySub: { ...typography.caption, color: colors.textSecondary, textAlign: 'center', lineHeight: 18 },
  cta: {
    marginTop: 16,
    paddingHorizontal: 26,
    paddingVertical: 14,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
  },
  ctaDimmed: { opacity: 0.4 },
  ctaText: { ...typography.button, color: colors.textWhite },
});
