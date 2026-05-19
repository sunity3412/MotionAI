import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

// 라이트 테마 전용 (CLAUDE.md §4 / design.md §10). 다크 배경 금지.
export default function RootLayout() {
  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }} />
    </>
  );
}
