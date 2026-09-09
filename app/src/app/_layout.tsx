import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useFonts } from 'expo-font';
import * as Updates from 'expo-updates';

// 라이트 테마 전용 (CLAUDE.md §4 / design.md §10). 다크 배경 금지.
//
// 32-12 (D-05) — Pretendard 실제 로드. app/assets/fonts 의 static TTF 4웨이트를
// expo-font 로 로드한다(키 = typography.fontFamily 이름과 정확히 일치). 로드 완료(또는
// 실패) 전까지 렌더를 보류해 시스템 폰트로 먼저 그렸다가 Pretendard 로 재조판되는
// 깜빡임을 막는다. useFonts 는 항상 loaded|error 로 귀결하므로 이 게이트는 멈추지
// 않는다(스플래시 hang 위험 0 — expo-splash-screen 미도입). 로드 실패(fontError)여도
// 계속 진행: fontFamily 미해결 → 시스템 폰트 + fontWeight 폴백(앱 차단 금지, graceful).

/**
 * 켤 때 OTA 를 받아 바로 새로고침한다 (260909-ji1).
 *
 * 왜: expo-updates 기본값은 "켤 때 확인 → 백그라운드로 내려받기 → **다음 실행에 적용**"
 * 이다. 그래서 새 OTA 를 쏘면 belle 이 앱을 두 번 껐다 켜야 보였고, 빨리 껐다 켜면
 * 다운로드가 끝나기 전이라 세 번을 껐다 켜도 그대로였다(belle 09-09 "두번 끄고 세번
 * 끄고 다 했는디"). 캡처를 주고받으며 고치는 지금 작업 방식에서 이 왕복이 매번 붙는다.
 *
 * 그래서 켤 때 **한 번만** 확인해 새 것이 있으면 받아서 즉시 reload 한다. 사용자는
 * 한 번만 켜면 된다.
 *
 * 안전장치:
 * - `Updates.isEnabled` 가 false 인 개발(Metro) 실행에서는 아무것도 하지 않는다.
 * - 네트워크 실패·서버 오류는 전부 삼킨다 — 업데이트 확인 실패로 앱을 막지 않는다.
 * - 렌더를 막지 않는다(비동기). 받을 게 없으면 화면은 그대로 뜬다.
 * - reload 는 받은 직후 한 번뿐이라 루프가 생기지 않는다(다음 실행엔 이미 최신).
 */
function useApplyUpdateOnLaunch() {
  useEffect(() => {
    if (!Updates.isEnabled) return;
    let cancelled = false;
    void (async () => {
      try {
        const check = await Updates.checkForUpdateAsync();
        if (cancelled || !check.isAvailable) return;
        await Updates.fetchUpdateAsync();
        if (cancelled) return;
        await Updates.reloadAsync();
      } catch {
        // 업데이트는 부가 기능이다 — 실패해도 앱은 그대로 쓴다.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    'Pretendard-Regular': require('../../assets/fonts/Pretendard-Regular.ttf'),
    'Pretendard-Medium': require('../../assets/fonts/Pretendard-Medium.ttf'),
    'Pretendard-SemiBold': require('../../assets/fonts/Pretendard-SemiBold.ttf'),
    'Pretendard-Bold': require('../../assets/fonts/Pretendard-Bold.ttf'),
  });

  useApplyUpdateOnLaunch();

  if (!fontsLoaded && !fontError) return null;

  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }} />
    </>
  );
}
