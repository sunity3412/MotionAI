import { StyleSheet, Text, View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { colors, typography } from '../theme';

// 원형 점수 게이지 (design.md §8 + app/CLAUDE.md: 외곽 트랙 + 채워지는 원호
// + 중앙 점수). 스피너 아님(§0). #8 Mode3 / #10 Mode1 공용.

// ia AC-RES-001-1: 0~100 + 등급 A/B/C/D
export function scoreGrade(score: number): 'A' | 'B' | 'C' | 'D' {
  if (score >= 90) return 'A';
  if (score >= 75) return 'B';
  if (score >= 60) return 'C';
  return 'D';
}

type Props = {
  score: number; // 0~100
  size?: number;
  strokeWidth?: number;
  caption?: string;
};

export function ScoreGauge({
  score,
  size = 168,
  strokeWidth = 14,
  caption = '점',
}: Props) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  const r = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - clamped / 100);
  const center = size / 2;

  return (
    <View style={{ width: size, height: size }}>
      <Svg width={size} height={size}>
        <Circle
          cx={center}
          cy={center}
          r={r}
          stroke={colors.divider}
          strokeWidth={strokeWidth}
          fill="none"
        />
        <Circle
          cx={center}
          cy={center}
          r={r}
          stroke={colors.brand}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${center} ${center})`}
        />
      </Svg>
      <View style={[StyleSheet.absoluteFill, styles.center]}>
        <Text style={styles.score}>{clamped}</Text>
        <Text style={styles.caption}>{caption}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: 'center', justifyContent: 'center' },
  score: { ...typography.score, color: colors.brand },
  caption: { ...typography.caption, color: colors.textSecondary, marginTop: 2 },
});
