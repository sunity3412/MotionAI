import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import SocialIcon from '../../components/SocialIcon';
import { authCopy } from '../../constants/authCopy';
import { SOCIAL_PROVIDERS, type SocialProviderId } from '../../constants/socialProviders';
import { signInWithApple, signInWithGoogle } from '../../lib/socialAuth';
import { colors, layout, radius, spacing, typography } from '../../theme';

// 회원가입 — Figma node 1:961 (fileKey jrdI7kp245HkPfLB0nclsz).
//
// Phase 36-01 은 화면과 라우팅만. provider 배선은 36-02~05.
//
// Figma 대비 의도적 차이 1개 (36-CONTEXT D-08):
//   "이메일로 가입하기"(1:970) + 밑줄(1:984) 을 **렌더하지 않는다**. 이메일 가입
//   (STEP01/02)은 belle 08-30 결정으로 이번 범위 밖 — 눌러도 아무 일 없는 링크를
//   남기지 않는다(Phase 33 "표시마다 답 or 없앰"). 범위가 열리면 이 자리에 되살린다.
//
// 하단 약관 링크는 **앱 안 문서**로 간다 (`/legal/terms`, `/legal/privacy`).
// belle 2026-08-30: 기존 sunity.ai 약관은 펀딩·커뮤니티 기준이라 그대로 못 쓴다 →
// 모션분석·AI 서비스용으로 새로 썼다. 근거·격차 = 36-LEGAL-GAP.md.
// 문서가 아직 법무 검토 전이라 화면 상단에 검토 중 배너가 뜬다.
export default function Signup() {
  const router = useRouter();
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Google(36-02) + Apple(36-03) 배선됨. 카카오·네이버는 36-05 에서 이 분기가 사라진다.
  const onProviderPress = async (id: SocialProviderId) => {
    if (id !== 'google' && id !== 'apple') {
      setNotice(authCopy.notWiredYet);
      return;
    }
    setNotice(null);
    setBusy(true);
    try {
      // provider 별 차이는 자격증명을 얻는 방법뿐 — 그 뒤(게스트 승계·결과 분기)는
      // socialAuth 안에서 같은 헬퍼를 지나므로 여기서는 outcome 만 본다.
      const { outcome } =
        id === 'apple' ? await signInWithApple() : await signInWithGoogle();
      if (outcome === 'cancelled') return; // 사용자가 닫은 것 — 오류가 아니다
      if (outcome === 'switched') {
        // 게스트 기록이 다른 uid 에 남는다는 사실을 알린 뒤 넘어간다.
        setNotice(authCopy.result.switched);
        return;
      }
      router.replace('/(tabs)');
    } catch {
      setNotice(authCopy.result.failed);
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
      <Pressable
        style={styles.back}
        onPress={() => router.back()}
        accessibilityRole="button"
        accessibilityLabel={authCopy.signup.back}
        hitSlop={12}
      >
        <Ionicons name="chevron-back" size={25} color={colors.textDisabled} />
      </Pressable>

      <Text style={styles.title}>{authCopy.signup.title}</Text>
      <Text style={styles.subtitle}>{authCopy.signup.subtitle}</Text>

      <View style={styles.buttons}>
        {SOCIAL_PROVIDERS.map((p) => (
          <Pressable
            key={p.id}
            onPress={() => onProviderPress(p.id)}
            disabled={busy}
            style={({ pressed }) => [
              styles.button,
              { backgroundColor: p.bg },
              p.border ? { borderWidth: 1, borderColor: p.border } : null,
              (pressed || busy) && styles.pressed,
            ]}
            accessibilityRole="button"
            accessibilityLabel={authCopy.providers[p.id].start}
          >
            <SocialIcon id={p.id} width={p.buttonIcon.width} height={p.buttonIcon.height} />
            <Text style={[styles.buttonLabel, { color: p.fg }]}>
              {authCopy.providers[p.id].start}
            </Text>
          </Pressable>
        ))}
      </View>

      {notice ? <Text style={styles.notice}>{notice}</Text> : null}

      <View style={styles.spacer} />

      <Text style={styles.terms}>
        {authCopy.signup.termsPrefix}
        <Text
          style={styles.termsLink}
          onPress={() => router.push('/legal/terms')}
          accessibilityRole="link"
        >
          {authCopy.signup.termsOfService}
        </Text>
        {authCopy.signup.termsMiddle}
        <Text
          style={styles.termsLink}
          onPress={() => router.push('/legal/privacy')}
          accessibilityRole="link"
        >
          {authCopy.signup.privacyPolicy}
        </Text>
        {authCopy.signup.termsSuffix}
      </Text>
    </SafeAreaView>
  );
}

// Figma 1:961 실측 (390×844 기준):
//   화살표   x25.08 y66.56  24.96×24.96
//   제목     x30    y125.77 171×36
//   부제     x30    y168.79 216×50 (2줄)
//   버튼 4개 x30    y249 / 321.24 / 392 / 464.24  각 330×54 (간격 ≈18)
//   아이콘   왼쪽 x120.6~123.8, 라벨 x156  → 아이콘+라벨 가운데 묶음, 사이 ≈16
//   약관안내 x52    y760.37 288×14
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg, // Figma 실측도 #FFFFFF — design.md §5-1 과 일치
    paddingHorizontal: spacing.screenX,
  },
  back: { alignSelf: 'flex-start', paddingVertical: 8 },
  title: { ...typography.headline, color: colors.textPrimary, marginTop: 26 },
  subtitle: { ...typography.bodySm, color: colors.textPrimary, marginTop: 12 },
  buttons: { marginTop: 30, gap: 18 },
  button: {
    height: layout.ctaHeight,
    borderRadius: radius.button,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
  },
  pressed: { opacity: 0.6 },
  buttonLabel: { ...typography.boxLabel },
  notice: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 16,
  },
  spacer: { flex: 1 },
  terms: {
    ...typography.caption,
    color: colors.textPrimary,
    textAlign: 'center',
    marginBottom: 24,
  },
  termsLink: { color: colors.brand, fontFamily: typography.caption.fontFamily },
});
