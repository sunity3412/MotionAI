import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import SocialIcon from '../../components/SocialIcon';
import SunityWordmark from '../../components/SunityWordmark';
import { authCopy } from '../../constants/authCopy';
import { SOCIAL_PROVIDERS, type SocialProviderId } from '../../constants/socialProviders';
import { signInWithGoogle } from '../../lib/socialAuth';
import { colors, radius, spacing, typography } from '../../theme';

// 로그인 — Figma node 1:550 (fileKey jrdI7kp245HkPfLB0nclsz).
//
// Phase 36-01 은 화면과 라우팅만 세운다. provider 배선은 36-02(Google)·36-03(Apple)·
// 36-04(Lambda 커스텀 토큰)·36-05(카카오·네이버)에서 붙는다.
//
// Figma 대비 의도적 차이 2개 (36-CONTEXT D-07/D-08):
//   1. "이메일 로그인"(1:559) + 그 위 구분선(1:560) 을 **렌더하지 않는다** — 이메일 로그인은
//      belle 08-30 결정으로 이번 범위 밖이고, 눌러도 아무 일 없는 링크를 남기는 것이
//      가장 나쁘다(Phase 33 "표시마다 답 or 없앰"). 범위가 열리면 이 자리에 되살린다.
//   2. **뒤로가기 화살표를 추가**했다. Figma 1:550 에는 없는데, 그 시안은 로그인이 앱의
//      첫 화면인 구성이었다. 우리 구성에서는 인트로에서 push 로 들어오므로 돌아갈 길이
//      보여야 한다. 화살표 위치/톤은 같은 파일의 가입 화면(1:985)을 그대로 따랐다.
//
// ★인사말: Figma 는 "희연님, 오늘도 한 발 더!" 로 이름을 쓴다. 그런데 로그인 **전**에는
// 이름을 알 수 없다(게스트는 displayName 이 없다). 그래서 지금은 이름 없는 변형을 쓴다 —
// 문구 확정은 belle 논의 대기 (authCopy.ts 주석 참조).
export default function Login() {
  const router = useRouter();
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Google 만 배선돼 있다 (36-02). 나머지는 36-03~05 에서 이 분기가 하나씩 사라진다.
  const onProviderPress = async (id: SocialProviderId) => {
    if (id !== 'google') {
      setNotice(authCopy.notWiredYet);
      return;
    }
    setNotice(null);
    setBusy(true);
    try {
      const { outcome } = await signInWithGoogle();
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
        accessibilityLabel={authCopy.login.back}
        hitSlop={12}
      >
        <Ionicons name="chevron-back" size={25} color={colors.textDisabled} />
      </Pressable>

      <View style={styles.center}>
        <SunityWordmark variant="brand" width={110} height={37} />
        <Text style={styles.greeting}>{authCopy.login.greetingNoName}</Text>
        <Text style={styles.welcome}>{authCopy.login.welcomeBack}</Text>

        <View style={styles.tileRow}>
          {SOCIAL_PROVIDERS.map((p) => (
            <Pressable
              key={p.id}
              onPress={() => onProviderPress(p.id)}
              disabled={busy}
              style={({ pressed }) => [
                styles.tile,
                { backgroundColor: p.bg },
                p.border ? { borderWidth: 1, borderColor: p.border } : null,
                (pressed || busy) && styles.pressed,
              ]}
              accessibilityRole="button"
              accessibilityLabel={authCopy.providers[p.id].login}
            >
              <SocialIcon id={p.id} width={p.tileIcon.width} height={p.tileIcon.height} />
            </Pressable>
          ))}
        </View>

        {notice ? <Text style={styles.notice}>{notice}</Text> : null}
      </View>

      <Text style={styles.bottomText}>
        {authCopy.login.newHere}
        <Text
          style={styles.link}
          onPress={() => router.push('/auth/signup')}
          accessibilityRole="link"
        >
          {authCopy.login.signupLink}
        </Text>
      </Text>
    </SafeAreaView>
  );
}

// Figma 1:550 실측 (390×844 기준):
//   로고     x140   y133     110.31×37.42
//   인사말   x122   y224     146×61 (2줄, 가운데)
//   WELCOME  x134   y295.77  123×20
//   타일 4개 x96.99 y364     각 40.70×40.70, 간격 11.10
//   하단링크 x140   y743.07  110×14
const TILE = 40.7;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.authLoginBg,
    paddingHorizontal: spacing.screenX,
  },
  back: { alignSelf: 'flex-start', paddingVertical: 8 },
  // Figma 는 로고가 y=133(프레임 상단 15.8%)이라 수직 중앙이 아니다.
  // 상태바(47)와 뒤로가기 행(41)을 빼고 45pt 아래에서 시작.
  center: { flex: 1, alignItems: 'center', marginTop: 45 },
  greeting: {
    ...typography.title,
    color: colors.textPrimary,
    textAlign: 'center',
    marginTop: 54,
  },
  welcome: {
    ...typography.boxLabel,
    color: colors.textDisabled,
    textAlign: 'center',
    marginTop: 11,
  },
  tileRow: { flexDirection: 'row', gap: 11.1, marginTop: 48 },
  tile: {
    width: TILE,
    height: TILE,
    borderRadius: radius.listItem,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: { opacity: 0.6 },
  notice: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 20,
  },
  bottomText: {
    ...typography.caption,
    color: colors.textPrimary,
    textAlign: 'center',
    marginBottom: 24,
  },
  link: { color: colors.brand, fontFamily: typography.caption.fontFamily },
});
