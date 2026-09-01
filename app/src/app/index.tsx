import { useRouter } from 'expo-router';
import { onAuthStateChanged } from 'firebase/auth';
import { useEffect, useState } from 'react';
import { ImageBackground, Pressable, StyleSheet, Text, View } from 'react-native';
import SunityWordmark from '../components/SunityWordmark';
import { authCopy } from '../constants/authCopy';
import { auth } from '../lib/firebase';
import { hasSeenTutorial } from '../lib/onboarding';
import { colors, layout, radius, spacing, typography } from '../theme';

// 인트로 — Figma node 1:142 (fileKey jrdI7kp245HkPfLB0nclsz).
//
// belle 2026-09-01 결정 (08-30 "시작하기=게스트 진입 그대로"를 **대체**):
//   "시작하기" = 로그인 게이트(/auth/login)로 이동 — 게스트 버튼은 로그인 화면에 있다
//   (로그인·회원가입·게스트 3구성). 익명(게스트) 세션은 자동 진입하지 않는다
//   (로그인 입구 상시 노출), **멤버(비익명) 세션만** 자동 홈 진입한다.
// Figma 레이아웃은 그대로 — CTA 의 목적지만 바뀐다. 가입 벽 없음은 유지
// (CLAUDE.md §2: 게스트는 로그인 화면에서 버튼 1탭).
//
// ★배경: Figma 는 다크레드 사진이고 CLAUDE.md §4 / design.md §10 은 "다크 배경 금지"라
// 충돌한다. belle 이 "디자인은 피그마를 따라줘"(08-28) 라고 해서 Figma 를 따랐고,
// 36-CONTEXT D-07 #1 에 belle 판정 대기 항목으로 올려뒀다. 판정이 '원복'이면 이 파일의
// ImageBackground 를 LinearGradient(gradients.homeTop) 로 되돌리면 된다.
export default function Intro() {
  const router = useRouter();
  // 멤버 세션 복원 판정을 기다리는 동안 인트로 깜빡임 방지 (스플래시 패턴 유지).
  const [bootstrapping, setBootstrapping] = useState(true);

  useEffect(() => {
    // 복원 판정은 **첫 발화 1회만**(one-shot) 처리한다. 로그인 화면이 push 로 위에
    // 얹힌 동안 인트로가 살아있으므로, 이후의 auth 변화(소셜 로그인·switched)에
    // 인트로가 반응해 라우팅을 가로채면 로그인 화면의 notice(특히 switched 안내)를
    // 선점 이탈시킨다 — 진입 후 라우팅의 소유권은 로그인 화면에 있다.
    // 자기-unsubscribe 패턴은 초기화 전 참조(TDZ) 위험이 있어 쓰지 않는다;
    // useEffect 반환값의 unsubscribe 는 언마운트 정리용.
    //
    // 멤버(비익명)만 자동 진입: 익명(게스트) 세션·무세션은 CTA 를 노출해 로그인
    // 게이트를 거치게 한다 (belle 2026-09-01). 멤버 튜토리얼 분기는 기존 그대로
    // (D-03/26-UI-SPEC S1, hasSeenTutorial 비동기 → bootstrapping 으로 깜빡임 방지).
    let handled = false;
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (handled) return;
      handled = true;
      if (user && !user.isAnonymous) {
        hasSeenTutorial().then((seen) => {
          router.replace(seen ? '/(tabs)' : '/tutorial');
        });
      } else {
        setBootstrapping(false);
      }
    });
    return unsubscribe;
  }, [router]);

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

      {/* 멤버 복원 판정 대기 중에는 CTA를 숨겨 스플래시처럼 보이게 (스피너 금지 §0). */}
      {!bootstrapping && (
        <View style={styles.bottom}>
          {/* push 인 이유: 로그인 화면의 뒤로가기 화살표가 인트로로 복귀할 수 있어야 한다. */}
          <Pressable
            style={({ pressed }) => [styles.cta, pressed && styles.ctaDimmed]}
            onPress={() => router.push('/auth/login')}
            accessibilityRole="button"
          >
            <Text style={styles.ctaText}>{authCopy.intro.cta}</Text>
          </Pressable>

          {/* CTA 와 같은 목적지로 의도적 수렴 — Figma 1:142 충실도 우선이고,
              계정 보유자 멘탈모델("로그인하기")에 맞는 문구라 해롭지 않다. */}
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
