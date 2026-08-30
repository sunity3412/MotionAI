import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import SocialIcon from '../../components/SocialIcon';
import { authCopy } from '../../constants/authCopy';
import { SOCIAL_PROVIDERS, type SocialProviderId } from '../../constants/socialProviders';
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
// ★하단 약관 링크의 목적지는 아직 belle 확인 대기 (36-CONTEXT D-07 #4) — sunity.ai
// /terms 재사용 가능 여부 + 영상·자세 데이터가 그 약관에 덮이는지. 확인 전까지 링크는
// 텍스트 강조만 하고 이동시키지 않는다(틀린 문서로 보내는 것보다 낫다).
export default function Signup() {
  const router = useRouter();
  const [notice, setNotice] = useState<string | null>(null);

  const onProviderPress = (_id: SocialProviderId) => {
    setNotice(authCopy.notWiredYet);
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
            style={({ pressed }) => [
              styles.button,
              { backgroundColor: p.bg },
              p.border ? { borderWidth: 1, borderColor: p.border } : null,
              pressed && styles.pressed,
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
        <Text style={styles.termsLink}>{authCopy.signup.termsOfService}</Text>
        {authCopy.signup.termsMiddle}
        <Text style={styles.termsLink}>{authCopy.signup.privacyPolicy}</Text>
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
