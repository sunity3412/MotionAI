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
import { useReferenceMotions } from '../../lib/referenceMotions';
import type { AnalysisDoc } from '../../types/analysis';
import { colors, layout, radius, spacing, typography } from '../../theme';

// 분석 기록 탭 (IA AC-REC-001).
// 파일럿: 리스트 + 빈 상태만. 필터·삭제·전후비교는 MVP 범위 밖 — IA 5장 참고.

// 같은 날 여러 건이 나란히 뜨면 날짜만으로는 구분이 안 된다(belle 08-31,
// quick-260831-lcc 점검 발견) — 시:분까지 표기해 행을 식별 가능하게 한다.
function formatDate(epochMs: number): string {
  const d = new Date(epochMs);
  const yy = String(d.getFullYear()).slice(2);
  const date = `${yy}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
  return `${date} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

// mode3 제목 구체화 (belle 08-31 "기록 제목 고쳐라") — 백엔드가 인식한 동작
// id(comparison.recognizedMotionId)를 기준 모션 목록의 한글명으로 매핑한다.
// recognizedMotionName 필드는 실데이터에서 원시 id("ref-peter-pan")가 들어와
// 표시용으로 못 쓴다 — id→name 매핑이 정본. 미인식/미로딩이면 기존 라벨 유지.
function motionLabel(
  doc: AnalysisDoc,
  referenceNameById: ReadonlyMap<string, string>,
): string {
  const comparison = doc.result?.comparison;
  if (comparison?.mode === 'mode1') {
    return comparison.referenceMotionName;
  }
  if (comparison?.mode === 'mode3' && comparison.recognizedMotionId) {
    const name = referenceNameById.get(comparison.recognizedMotionId);
    if (name) return name;
  }
  return '내 동작 분석';
}

function modeBadge(doc: AnalysisDoc): string {
  return doc.mode === 'mode1' ? '프로 비교' : '내 기록';
}

export default function History() {
  const router = useRouter();
  const { analyses, loading, error } = useMyAnalyses({ doneOnly: true });
  // mode3 제목 매핑용 — 홈/분석 탭과 같은 구독이라 추가 네트워크 비용 없음.
  const { motions } = useReferenceMotions();
  const referenceNameById = new Map(motions.map((m) => [m.motionId, m.name]));

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
                {motionLabel(doc, referenceNameById)}
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
