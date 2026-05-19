import { StyleSheet, Text, View } from 'react-native';
import { colors, spacing, typography } from '../theme';

// 임시 빈 화면. 각 탭 실제 구현은 plan.md 우선순위에 따라 대체.
export function ScreenPlaceholder({ title }: { title: string }) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.note}>준비 중인 화면입니다</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.screenX,
  },
  title: { ...typography.heading, color: colors.textPrimary },
  note: { ...typography.caption, color: colors.textSecondary, marginTop: 8 },
});
