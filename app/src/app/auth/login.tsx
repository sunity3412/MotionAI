import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { signInAnonymously } from 'firebase/auth';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import SocialIcon from '../../components/SocialIcon';
import SunityWordmark from '../../components/SunityWordmark';
import { authCopy } from '../../constants/authCopy';
import {
  WIRED_SOCIAL_PROVIDERS,
  isWiredProvider,
  type SocialProviderId,
} from '../../constants/socialProviders';
import { auth } from '../../lib/firebase';
import { hasSeenTutorial } from '../../lib/onboarding';
import { signInWithApple, signInWithGoogle } from '../../lib/socialAuth';
import { colors, layout, radius, spacing, typography } from '../../theme';

// 로그인 — Figma node 1:550 (fileKey jrdI7kp245HkPfLB0nclsz).
//
// Phase 36-01 이 화면·라우팅을 세웠고, provider 는 36-02(Google)·36-03(Apple) 까지
// 배선됐다. 카카오·네이버는 36-04(Lambda 커스텀 토큰)·36-05 에서 붙는다 —
// 두 provider 는 Firebase 기본 제공이 아니라 커스텀 토큰 교환이 먼저 필요하다.
//
// Figma 대비 의도적 차이 3개 (36-CONTEXT D-07/D-08, belle 2026-09-01):
//   1. "이메일 로그인"(1:559) + 그 위 구분선(1:560) 을 **렌더하지 않는다** — 이메일 로그인은
//      belle 08-30 결정으로 이번 범위 밖이고, 눌러도 아무 일 없는 링크를 남기는 것이
//      가장 나쁘다(Phase 33 "표시마다 답 or 없앰"). 범위가 열리면 이 자리에 되살린다.
//   2. **뒤로가기 화살표를 추가**했다. Figma 1:550 에는 없는데, 그 시안은 로그인이 앱의
//      첫 화면인 구성이었다. 우리 구성에서는 인트로에서 push 로 들어오므로 돌아갈 길이
//      보여야 한다. 화살표 위치/톤은 같은 파일의 가입 화면(1:985)을 그대로 따랐다.
//      (문자 그대로의 첫 화면은 여전히 인트로고 이 화면은 push 로만 진입하므로 유효.)
//   3. **"게스트로 시작하기" 버튼을 추가**했다. Figma 1:550 에 없는 신규 요소 —
//      belle 2026-09-01 결정(로그인 화면 = 앱의 첫 관문, 로그인·회원가입·게스트 3구성).
//
// ★인사말: Figma 는 "희연님, 오늘도 한 발 더!" 로 이름을 쓴다. 그런데 로그인 **전**에는
// 이름을 알 수 없다(게스트는 displayName 이 없다). 그래서 지금은 이름 없는 변형을 쓴다 —
// 문구 확정은 belle 논의 대기 (authCopy.ts 주석 참조).
export default function Login() {
  const router = useRouter();
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Google(36-02) + Apple(36-03) 배선됨. 카카오·네이버는 36-05 에서 이 분기가 사라진다.
  const onProviderPress = async (id: SocialProviderId) => {
    // 화면은 배선된 provider 만 렌더하므로 평시엔 도달하지 않는다 — 목록과
    // 핸들러가 어긋나는 회귀를 막는 방어선으로 남긴다(단일 출처는 socialProviders).
    if (!isWiredProvider(id)) {
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

  // 게스트 진입 후 라우팅 — 스택 위생이 핵심. 이 화면은 push 로 얹혀 있어(스택
  // [intro, login]) 그냥 replace('/tutorial') 하면 인트로가 스택에 남고, tutorial.tsx
  // 종료 분기(canGoBack() ? back() : replace('/(tabs)'))가 홈이 아니라 인트로로
  // 떨어진다. 그래서 dismissAll 로 스택을 루트(인트로)까지 걷어낸 뒤 replace 한다
  // → 목적지 화면 단독 스택, 튜토리얼 종료가 홈으로 수렴.
  const routeAfterGuest = async () => {
    const seen = await hasSeenTutorial();
    if (router.canDismiss()) {
      router.dismissAll();
    }
    router.replace(seen ? '/(tabs)' : '/tutorial');
  };

  // 게스트로 시작하기 — belle 2026-09-01 (로그인·회원가입·게스트 3구성).
  // 익명 세션이 이미 있으면 signInAnonymously 는 **그 사용자를 그대로 반환**한다
  // (Firebase JS SDK 문서 동작) → uid 불변 = users/{uid}/analyses 게스트 기록 유지.
  // signOut/재발급 없음. 멤버 세션 방어 분기를 두지 않는 이유: 멤버는 인트로에서
  // 자동 홈 진입하고 마이 탭은 멤버에게 로그아웃만 노출하므로, 멤버 상태로 이 화면에
  // 도달하는 경로가 없다.
  const onGuestPress = async () => {
    setNotice(null);
    setBusy(true);
    try {
      await signInAnonymously(auth);
      await routeAfterGuest();
    } catch {
      setNotice(authCopy.login.guestError);
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
          {WIRED_SOCIAL_PROVIDERS.map((p) => (
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

        <Pressable
          onPress={onGuestPress}
          disabled={busy}
          style={({ pressed }) => [
            styles.guestBtn,
            (pressed || busy) && styles.pressed,
          ]}
          accessibilityRole="button"
          accessibilityLabel={authCopy.login.guestCta}
          accessibilityState={{ disabled: busy }}
        >
          <Text style={styles.guestText}>
            {busy ? authCopy.login.guestCtaLoading : authCopy.login.guestCta}
          </Text>
        </Pressable>

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
  // 게스트 버튼 — Figma 1:550 에 없는 미설계 요소라 화면 기존 톤 안에서 자체 판단
  // (design.md §0 보조 액션 = 테두리 1px inputBorder, 배경 투명). 위계: 소셜 타일
  // (주 행동)보다 낮고 하단 caption 링크보다 높은 3번째 요소 — 파일럿에선 수강생
  // 대부분이 게스트로 들어오므로 텍스트 링크로 숨기지 않는다.
  // marginTop 32 = 타일 리듬(48)과 하단 여백 사이 중간값.
  guestBtn: {
    height: layout.ctaHeight,
    borderRadius: radius.button,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    backgroundColor: 'transparent',
    alignSelf: 'stretch',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 32,
  },
  guestText: { ...typography.boxLabel, color: colors.textPrimary },
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
