import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { onAuthStateChanged, signInAnonymously } from 'firebase/auth';
import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { auth } from '../lib/firebase';
import { hasSeenTutorial } from '../lib/onboarding';
import { colors, gradients, layout, radius, spacing, typography } from '../theme';

// 인트로 — 파일럿 최소 게스트 진입 (plan.md #3, design.md §1·§5-1·§6·§10).
// 회원가입/로그인/레벨/플랜 스킵. 게스트 = Firebase 익명 인증 (영속 → 재실행 시 자동 진입).
// 배경: 브랜드 그라디언트 전체화면 (다크 배경 금지 — design.md §1·§10).
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
    <LinearGradient
      colors={gradients.homeTop.colors}
      locations={gradients.homeTop.locations}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 0.08 }}
      style={styles.container}
    >
      <View style={styles.center}>
        <Text style={styles.logo}>Sunity</Text>
        <Text style={styles.tagline}>
          AI 코치와 함께하는{'\n'}폴스포츠 자세 교정
        </Text>
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
              {loading ? '시작하는 중...' : '게스트로 시작하기'}
            </Text>
          </Pressable>
          <Text style={styles.subtle}>
            {status === 'error'
              ? '연결에 실패했어요. 잠시 후 다시 시도해주세요.'
              : '가입 없이 바로 시작해요'}
          </Text>
        </View>
      )}
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: layout.safeAreaTop,
    paddingBottom: layout.safeAreaBottom + 24,
    paddingHorizontal: spacing.screenX,
  },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  logo: { ...typography.heading, color: colors.textWhite },
  tagline: {
    ...typography.body,
    color: colors.textWhite,
    textAlign: 'center',
    marginTop: 12,
    opacity: 0.9,
  },
  bottom: { gap: 12 },
  cta: {
    height: layout.ctaHeight,
    borderRadius: radius.button,
    backgroundColor: colors.bg, // 그라디언트 위 → 흰 버튼 + 브랜드 텍스트 (§0 결정트리)
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaDimmed: { opacity: 0.4 }, // design.md §9 버튼 비활성/피드백
  ctaText: { ...typography.button, color: colors.brand },
  subtle: {
    ...typography.caption,
    color: colors.textWhite,
    textAlign: 'center',
    opacity: 0.85,
  },
});
