import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useFonts } from 'expo-font';

// 라이트 테마 전용 (CLAUDE.md §4 / design.md §10). 다크 배경 금지.
//
// 32-12 (D-05) — Pretendard 실제 로드. app/assets/fonts 의 static TTF 4웨이트를
// expo-font 로 로드한다(키 = typography.fontFamily 이름과 정확히 일치). 로드 완료(또는
// 실패) 전까지 렌더를 보류해 시스템 폰트로 먼저 그렸다가 Pretendard 로 재조판되는
// 깜빡임을 막는다. useFonts 는 항상 loaded|error 로 귀결하므로 이 게이트는 멈추지
// 않는다(스플래시 hang 위험 0 — expo-splash-screen 미도입). 로드 실패(fontError)여도
// 계속 진행: fontFamily 미해결 → 시스템 폰트 + fontWeight 폴백(앱 차단 금지, graceful).
export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    'Pretendard-Regular': require('../../assets/fonts/Pretendard-Regular.ttf'),
    'Pretendard-Medium': require('../../assets/fonts/Pretendard-Medium.ttf'),
    'Pretendard-SemiBold': require('../../assets/fonts/Pretendard-SemiBold.ttf'),
    'Pretendard-Bold': require('../../assets/fonts/Pretendard-Bold.ttf'),
  });

  if (!fontsLoaded && !fontError) return null;

  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }} />
    </>
  );
}
