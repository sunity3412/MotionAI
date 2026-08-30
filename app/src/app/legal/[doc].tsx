import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { authCopy } from '../../constants/authCopy';
import { legalDocuments, type LegalDocKey } from '../../constants/legalIndex';
import type { LegalDocument } from '../../constants/legalTypes';
import { colors, radius, spacing, typography } from '../../theme';

// 약관 · 개인정보처리방침 화면 (Phase 36).
//
// 문서 두 개를 한 화면이 그린다 — 라우트 파라미터로 고른다:
//   /legal/terms   → 서비스 이용약관
//   /legal/privacy → 개인정보처리방침
//
// 파일럿에서는 앱 안에 두는 것이 맞다. 외부 배포(sunity.ai 페이지 추가 등)에 묶이지 않고
// 가입 화면 링크가 바로 살아난다. ★정식 출시 때는 App Store Connect 가 **공개 URL** 을
// 요구하므로 그때 같은 문안을 정적 페이지로 내보내야 한다 (36-LEGAL-GAP.md 결정 B).
//
// 본문 규약: "· " 로 시작하는 줄은 목록 항목으로 그린다. 마크다운 렌더러를 들이지 않기
// 위한 최소 규약이고, 계약은 constants/legalTypes.ts 에 있다.
export default function Legal() {
  const router = useRouter();
  const { doc } = useLocalSearchParams<{ doc: string }>();

  const key: LegalDocKey = doc === 'terms' ? 'terms' : 'privacy';
  const document: LegalDocument = legalDocuments[key];

  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
      <View style={styles.header}>
        <Ionicons
          name="chevron-back"
          size={25}
          color={colors.textDisabled}
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel={authCopy.legal.back}
        />
        <Text style={styles.headerTitle} numberOfLines={1}>
          {document.title}
        </Text>
      </View>

      <ScrollView
        contentContainerStyle={styles.body}
        showsVerticalScrollIndicator={false}
      >
        {document.status === 'draft' && (
          <View style={styles.draftBanner}>
            <Text style={styles.draftText}>{authCopy.legal.draftNotice}</Text>
          </View>
        )}

        <Text style={styles.effective}>{document.effectiveNote}</Text>

        {document.intro.map((line, i) => (
          <Text key={`intro-${i}`} style={styles.intro}>
            {line}
          </Text>
        ))}

        {document.sections.map((section) => (
          <View key={section.heading} style={styles.section}>
            <Text style={styles.heading}>{section.heading}</Text>
            {section.body.map((line, i) =>
              line.startsWith('· ') ? (
                <View key={i} style={styles.bulletRow}>
                  <Text style={styles.bulletDot}>·</Text>
                  <Text style={styles.bulletText}>{line.slice(2)}</Text>
                </View>
              ) : (
                <Text key={i} style={styles.paragraph}>
                  {line}
                </Text>
              ),
            )}
          </View>
        ))}

        <Text style={styles.version}>{document.version}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: spacing.screenX,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  headerTitle: { ...typography.listTitle, color: colors.textPrimary, flex: 1 },
  body: {
    paddingHorizontal: spacing.screenX,
    paddingTop: 18,
    paddingBottom: 48,
  },
  // 법무 검토 전이라는 사실을 숨기지 않는다 — 검토가 끝나면 문서의 status 만 바꾼다.
  draftBanner: {
    backgroundColor: colors.infoTealBg,
    borderWidth: 1,
    borderColor: colors.infoTealBorder,
    borderRadius: radius.listItem,
    padding: 12,
    marginBottom: 16,
  },
  draftText: { ...typography.badge, color: colors.infoTeal, lineHeight: 24 },
  effective: { ...typography.caption, color: colors.textLo, marginBottom: 14 },
  intro: {
    ...typography.bodySm,
    color: colors.textMid,
    lineHeight: 28,
    marginBottom: 12,
  },
  section: { marginTop: 28 },
  heading: {
    ...typography.bodyLg,
    color: colors.textPrimary,
    marginBottom: 10,
  },
  // 본문은 Phase 32 D-05 가 정한 하한 17pt(badge)를 지킨다 — 약관은 통독하는 글이라
  // caption(12pt)으로 두면 읽히지 않는다. belle "폰트 젤 작은 것들 정말 너무 작음" 계열.
  paragraph: {
    ...typography.badge,
    color: colors.textMid,
    lineHeight: 27,
    marginBottom: 9,
  },
  bulletRow: { flexDirection: 'row', gap: 8, marginBottom: 9 },
  bulletDot: { ...typography.badge, color: colors.textLo, lineHeight: 27 },
  bulletText: {
    ...typography.badge,
    color: colors.textMid,
    lineHeight: 27,
    flex: 1,
  },
  version: {
    ...typography.captionSmall,
    color: colors.textLo,
    marginTop: 28,
    textAlign: 'center',
  },
});
