import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import { colors, typography } from '../../theme';

// 바텀탭 4개 (design.md §5-2). 활성 #FF4B33 / 비활성 #A5A5A5 / 흰 배경.
export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.tabActive,
        tabBarInactiveTintColor: colors.tabInactive,
        tabBarStyle: { backgroundColor: colors.bg },
        tabBarLabelStyle: { fontSize: 11, letterSpacing: typography.caption.letterSpacing },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: '홈',
          tabBarIcon: ({ color, size }) => <Ionicons name="home-outline" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="analyze"
        options={{
          title: '분석',
          tabBarIcon: ({ color, size }) => <Ionicons name="analytics-outline" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: '기록',
          tabBarIcon: ({ color, size }) => <Ionicons name="time-outline" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: '마이',
          tabBarIcon: ({ color, size }) => <Ionicons name="person-outline" size={size} color={color} />,
        }}
      />
    </Tabs>
  );
}
