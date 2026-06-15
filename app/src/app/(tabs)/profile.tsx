import Constants from 'expo-constants';
import { Ionicons } from '@expo/vector-icons';
import { useMemo, useState } from 'react';
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { auth } from '../../lib/firebase';
import { useMyAnalyses } from '../../lib/userAnalyses';
import { useBodyProfile } from '../../lib/bodyProfile';
import BodyProfileForm from '../../components/BodyProfileForm';
import type {
  AnalysisDoc,
  BodyProfile,
  DominantHand,
  ExperienceLevel,
  PainArea,
} from '../../types/analysis';
import { colors, layout, radius, spacing, typography } from '../../theme';

// 마이 탭 — 파일럿 단순 정보. (IA AC-MY-* 의 프로필 편집·구독·알림 등은 MVP 밖.)
// 게스트 모드(익명 인증) 상태와 분석 통계, 폴스포츠 고정 표시.

function averageScore(analyses: AnalysisDoc[]): number | null {
  const scores = analyses
    .map((a) => a.result?.overallScore)
    .filter((s): s is number => typeof s === 'number');
  if (scores.length === 0) return null;
  return Math.round(scores.reduce((sum, s) => sum + s, 0) / scores.length);
}

function shortenUid(uid: string): string {
  return uid.length <= 8 ? uid : `${uid.slice(0, 4)}…${uid.slice(-4)}`;
}

// BodyProfile 요약 라벨 (analysis.ts union 정합, BodyProfileForm 과 동일 KO 매핑).
const EXPERIENCE_LABEL: Record<ExperienceLevel, string> = {
  beginner: '초급',
  intermediate: '중급',
  advanced: '고급',
};
const HAND_LABEL: Record<DominantHand, string> = {
  left: '왼손',
  right: '오른손',
  both: '양손',
};
const PAIN_AREA_LABEL: Record<PainArea, string> = {
  shoulder: '어깨',
  wrist: '손목',
  lower_back: '허리',
  knee: '무릎',
  ankle: '발목',
  neck: '목',
  hip: '고관절',
  elbow: '팔꿈치',
};

// 채워진 필드만 "·" 로 묶어 요약 (부분 입력 graceful, D-06). 전부 비면 null.
function summarizeBodyProfile(profile: BodyProfile | null): string | null {
  if (!profile) return null;
  const parts: string[] = [];
  if (profile.heightCm != null) parts.push(`${profile.heightCm}cm`);
  if (profile.experience) parts.push(EXPERIENCE_LABEL[profile.experience]);
  if (profile.dominantHand) parts.push(HAND_LABEL[profile.dominantHand]);
  if (profile.painAreas.length > 0) {
    parts.push(profile.painAreas.map((a) => PAIN_AREA_LABEL[a]).join('·'));
  }
  return parts.length > 0 ? parts.join(' · ') : null;
}

export default function Profile() {
  const { analyses } = useMyAnalyses({ doneOnly: true });
  const { profile } = useBodyProfile();
  const uid = auth.currentUser?.uid ?? null;
  const avg = useMemo(() => averageScore(analyses), [analyses]);
  const appVersion = Constants.expoConfig?.version ?? '1.0.0';

  const [editing, setEditing] = useState(false);
  const summary = useMemo(() => summarizeBodyProfile(profile), [profile]);

  return (
    <View style={styles.container}>
      <Text style={styles.headerTitle}>마이</Text>
      <Text style={styles.headerSub}>파일럿 게스트 모드</Text>

      <ScrollView
        contentContainerStyle={styles.body}
        showsVerticalScrollIndicator={false}
      >
        {/* 게스트 카드 */}
        <View style={styles.card}>
          <View style={styles.avatar}>
            <Ionicons name="person-outline" size={26} color={colors.brand} />
          </View>
          <View style={styles.profileText}>
            <Text style={styles.profileName}>게스트</Text>
            <Text style={styles.profileMeta}>
              {uid ? `ID ${shortenUid(uid)}` : '익명 세션 준비 중'}
            </Text>
          </View>
        </View>

        {/* 내 몸 정보 — 미입력=권유 / 입력됨=요약+수정 (D-01/D-02/D-06) */}
        <Pressable
          onPress={() => setEditing(true)}
          accessibilityRole="button"
          accessibilityLabel={
            summary ? `내 몸 정보 수정, 현재 ${summary}` : '내 몸 정보 입력하기'
          }
          style={({ pressed }) => [
            summary ? styles.bodyCard : styles.bodyPrompt,
            pressed && styles.bodyCardPressed,
          ]}
        >
          <View style={styles.bodyCardText}>
            <Text style={styles.bodyCardTitle}>내 몸 정보</Text>
            <Text
              style={summary ? styles.bodyCardSummary : styles.bodyPromptText}
              numberOfLines={1}
            >
              {summary ?? '키·경력·통증부위를 입력하면 코칭이 더 정확해져요'}
            </Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color={colors.brand} />
        </Pressable>

        {/* 통계 */}
        <View style={styles.stats}>
          <StatBox label="분석 횟수" value={`${analyses.length}`} suffix="회" />
          <StatBox
            label="평균 점수"
            value={avg != null ? `${avg}` : '–'}
            suffix={avg != null ? '점' : ''}
          />
        </View>

        {/* 정보 리스트 */}
        <View style={styles.infoList}>
          {[
            { label: '주 종목', value: '폴스포츠' },
            { label: '레벨', value: '입문 (기본값)' },
            { label: '앱 버전', value: appVersion },
          ].map((row, i, arr) => (
            <InfoRow
              key={row.label}
              label={row.label}
              value={row.value}
              isLast={i === arr.length - 1}
            />
          ))}
        </View>

        {/* MVP 범위 안내 */}
        <View style={styles.notice}>
          <Ionicons name="information-circle-outline" size={18} color={colors.textSecondary} />
          <Text style={styles.noticeText}>
            로그인·결제·알림 설정은 정식 출시 단계에서 열려요.
          </Text>
        </View>
      </ScrollView>

      {/* 내 몸 정보 편집 — 전체화면 폼 (기존값 prefill, 저장 후 onSnapshot 자동 갱신) */}
      <Modal
        visible={editing}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setEditing(false)}
      >
        <SafeAreaView style={styles.modalSafe} edges={['top']}>
          <BodyProfileForm
            initial={profile}
            onClose={() => setEditing(false)}
            onSaved={() => setEditing(false)}
          />
        </SafeAreaView>
      </Modal>
    </View>
  );
}

function StatBox({
  label,
  value,
  suffix,
}: {
  label: string;
  value: string;
  suffix: string;
}) {
  return (
    <View style={styles.statBox}>
      <Text style={styles.statLabel}>{label}</Text>
      <View style={styles.statValueRow}>
        <Text style={styles.statValue}>{value}</Text>
        {suffix ? <Text style={styles.statSuffix}>{suffix}</Text> : null}
      </View>
    </View>
  );
}

function InfoRow({
  label,
  value,
  isLast,
}: {
  label: string;
  value: string;
  isLast?: boolean;
}) {
  return (
    <View style={[styles.infoRow, isLast && styles.infoRowLast]}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
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
  body: { paddingVertical: 18, paddingBottom: 24, gap: 14 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.brandTint,
    alignItems: 'center',
    justifyContent: 'center',
  },
  profileText: { flex: 1, gap: 4 },
  profileName: { ...typography.listTitle, color: colors.textPrimary },
  profileMeta: { ...typography.caption, color: colors.textSecondary },
  bodyCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
  },
  bodyPrompt: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.brandTint,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
  },
  bodyCardPressed: { opacity: 0.7 },
  bodyCardText: { flex: 1, gap: 4 },
  bodyCardTitle: { ...typography.listTitle, color: colors.textPrimary },
  bodyCardSummary: { ...typography.caption, color: colors.textSecondary },
  bodyPromptText: { ...typography.caption, color: colors.textPrimary },
  modalSafe: { flex: 1, backgroundColor: colors.bg },
  stats: { flexDirection: 'row', gap: 10 },
  statBox: {
    flex: 1,
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
    gap: 8,
  },
  statLabel: { ...typography.caption, color: colors.textSecondary },
  statValueRow: { flexDirection: 'row', alignItems: 'baseline', gap: 4 },
  statValue: { ...typography.score, fontSize: 28, color: colors.brand },
  statSuffix: { ...typography.caption, color: colors.textSecondary },
  infoList: {
    backgroundColor: colors.cardBg,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    borderRadius: radius.card,
    paddingHorizontal: spacing.cardPadding,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
  infoRowLast: { borderBottomWidth: 0 },
  infoLabel: { ...typography.caption, color: colors.textSecondary },
  infoValue: { ...typography.boxLabel, color: colors.textPrimary },
  notice: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    padding: spacing.cardPadding,
    backgroundColor: colors.brandTint,
    borderRadius: radius.card,
  },
  noticeText: { ...typography.caption, color: colors.textPrimary, flex: 1 },
});
