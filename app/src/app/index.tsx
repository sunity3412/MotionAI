import { useRouter } from 'expo-router';
import { onAuthStateChanged, signInAnonymously } from 'firebase/auth';
import { useEffect, useState } from 'react';
import { ImageBackground, Pressable, StyleSheet, Text, View } from 'react-native';
import SunityWordmark from '../components/SunityWordmark';
import { authCopy } from '../constants/authCopy';
import { auth } from '../lib/firebase';
import { hasSeenTutorial } from '../lib/onboarding';
import { colors, layout, radius, spacing, typography } from '../theme';

// 인트로 — Figma node 1:142 (fileKey jrdI7kp245HkPfLB0nclsz).
//
// Phase 36 (계정 시스템) 개편. belle 2026-08-30 결정:
//   "시작하기" = **게스트 진입 그대로**(가입 벽 없음, CLAUDE.md §2 파일럿 요건),
//   하단 "이미 계정이 있으신가요? 로그인하기" = 로그인 화면.
// 즉 Figma 레이아웃은 1픽셀도 안 바꾸고 '시작하기'의 뜻만 게스트 시작으로 둔다.
//
// 게스트 = Firebase 익명 인증 (영속 → 재실행 시 자동 진입). 이 동작은 개편 전과 동일하다.
//
// ★배경: Figma 는 다크레드 사진이고 CLAUDE.md §4 / design.md §10 은 "다크 배경 금지"라
// 충돌한다. belle 이 "디자인은 피그마를 따라줘"(08-28) 라고 해서 Figma 를 따랐고,
// 36-CONTEXT D-07 #1 에 belle 판정 대기 항목으로 올려뒀다. 판정이 '원복'이면 이 파일의
// ImageBackground 를 LinearGradient(gradients.homeTop) 로 되돌리면 된다.
export default function Intro() {
  const router = useRouter();
  // 영속된 게스트 세션 복원을 기다리는 동안 인트로 깜빡임 방지.
  const [bootstrapping, setBootstrapping] = useState(true);
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle');

  useEffect(() => {
    // 인증 상태가 생기면(신규 게스트 로그인 or 복원) 라우팅. 내비게이션을 한 곳에 집중.
    // D-03/26-UI-SPEC S1: 첫 실행 게스트는 홈 진입 전에 기대설정 튜토리얼을 1회 본다.
    // hasSeenTutorial() 이 비동기라 bootstrapping state 로 CTA/라우팅을 보류해
    // 플래그 로드 전 깜빡임을 막는다 (기존 인트로 스플래시 패턴 재사용).
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (user) {
        hasSeenTutorial().then((seen) => {
          router.replace(seen ? '/(tabs)' : '/tutorial');
        });
      } else {
        setBootstrapping(false);
      }
    });
    return unsubscribe;
  }, [router]);

  const startAsGuest = () => {
    setStatus('loading');
    signInAnonymously(auth).catch(() => setStatus('error'));
    // 성공 시 onAuthStateChanged 가 라우팅 담당.
  };

  const loading = status === 'loading';

  return (
    <ImageBackground
      source={require('../../assets/auth/intro-bg.jpg')}
      resizeMode="cover"
      style={styles.container}
    >
      <View style={styles.center}>
        <SunityWordmark variant="white" width={140} height={48} />
        <View style={styles.divider} />
        <Text style={styles.taglineTop}>{authCopy.intro.taglineTop}</Text>
        <Text style={styles.taglineBottom}>{authCopy.intro.taglineBottom}</Text>
      </View>

      {/* 게스트 세션 복원 대기 중에는 CTA를 숨겨 스플래시처럼 보이게 (스피너 금지 §0). */}
      {!bootstrapping && (
        <View style={styles.bottom}>
          <Pressable
            style={({ pressed }) => [
              styles.cta,
              (pressed || loading) && styles.ctaDimmed,
            ]}
            onPress={startAsGuest}
            disabled={loading}
            accessibilityRole="button"
            accessibilityState={{ disabled: loading }}
          >
            <Text style={styles.ctaText}>
              {loading ? authCopy.intro.ctaLoading : authCopy.intro.cta}
            </Text>
          </Pressable>

          {status === 'error' ? (
            <Text style={styles.subtle}>{authCopy.intro.error}</Text>
          ) : (
            <Text style={styles.subtle}>
              {authCopy.intro.haveAccount}
              <Text
                style={styles.link}
                onPress={() => router.push('/auth/login')}
                accessibilityRole="link"
              >
                {authCopy.intro.loginLink}
              </Text>
            </Text>
          )}
        </View>
      )}
    </ImageBackground>
  );
}

// Figma 1:142 실측 (390×844 기준):
//   logo   x125 y262.08  139.97×47.63
//   line   x184 y328.73  21.78×1
//   본문   x86  y341.18  218×61 (2줄)
//   CTA    x27  y664.24  335×75  (채움 없음 + 흰 헤어라인)
//   하단링크 x80 y763    230×20
const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: layout.safeAreaTop,
    paddingBottom: layout.safeAreaBottom + 24,
    paddingHorizontal: spacing.screenX,
  },
  // Figma 는 본문 블록(y262~402)이 화면 중앙(422)보다 90pt 위에 있다.
  // 하단 블록이 고정 높이라 flex:1 중앙 정렬만으로 근사되고, 기기 높이에 따라 자연 조정된다.
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  divider: {
    width: 22,
    height: 1,
    backgroundColor: colors.textWhite,
    marginTop: 19,
    marginBottom: 12,
  },
  taglineTop: {
    ...typography.bodySm,
    color: colors.textWhite,
    textAlign: 'center',
  },
  taglineBottom: {
    ...typography.bodyLg,
    color: colors.textWhite,
    textAlign: 'center',
  },
  bottom: { gap: 20 },
  cta: {
    height: 75,
    borderRadius: radius.button,
    backgroundColor: 'transparent', // Figma 1:159 = 채움 없음 (사진이 그대로 비친다)
    borderWidth: 1,
    borderColor: colors.introCtaBorder,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaDimmed: { opacity: 0.4 }, // design.md §9 버튼 비활성/피드백
  ctaText: { ...typography.button, color: colors.textWhite },
  subtle: {
    ...typography.caption,
    color: colors.textWhite,
    textAlign: 'center',
    opacity: 0.85,
  },
  link: { color: colors.brand, fontFamily: typography.caption.fontFamily },
});
