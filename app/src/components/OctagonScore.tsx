import { StyleSheet, Text, View } from 'react-native';
import Svg, { Defs, LinearGradient, Polygon, Stop } from 'react-native-svg';
import { colors } from '../theme';

// 점수 위젯 — 정팔각형 게이지 (design.md §5-5 + Figma 1:719).
// 회색 트랙 옥타곤 위에 점수(0~100)만큼 브랜드 그라디언트로 채워지는 게이지.
// 홈 최근분석 카드(size 95)와 결과 화면 점수 개요(size 168) 공용.

const VIEW = 100;
const STROKE = 7;
// 정팔각형 — 상단 변 중점(50,7.5)에서 시작해 시계방향. 첫 점을 변 중점으로 잡아
// dash 게이지가 12시에서 시작하게 함 (나머지는 정점, 반지름 46).
const POINTS =
  '50,7.5 67.6,7.5 92.5,32.4 92.5,67.6 67.6,92.5 32.4,92.5 7.5,67.6 7.5,32.4 32.4,7.5';
const PERIMETER = 281.7; // 8변 정팔각형 둘레 (정점 반지름 46)

// ia AC-RES-001-1: 0~100 → 등급 A/B/C/D
export function scoreGrade(score: number): 'A' | 'B' | 'C' | 'D' {
  if (score >= 90) return 'A';
  if (score >= 75) return 'B';
  if (score >= 60) return 'C';
  return 'D';
}

export function OctagonScore({
  score,
  size = 95,
}: {
  score: number;
  size?: number;
}) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  const dashOffset = PERIMETER * (1 - clamped / 100);
  return (
    <View style={[styles.wrap, { width: size, height: size }]}>
      <Svg width={size} height={size} viewBox={`0 0 ${VIEW} ${VIEW}`}>
        <Defs>
          <LinearGradient id="octaScoreGrad" x1="0" y1="0" x2="1" y2="1">
            <Stop offset="0" stopColor="#FFB5AB" />
            <Stop offset="1" stopColor="#FF604B" />
          </LinearGradient>
        </Defs>
        {/* 트랙 — 회색 옥타곤 전체 */}
        <Polygon
          points={POINTS}
          fill="none"
          stroke={colors.divider}
          strokeWidth={STROKE}
          strokeLinejoin="round"
        />
        {/* 진행 — 점수만큼 브랜드 그라디언트로 채움 (12시 시작 시계방향) */}
        <Polygon
          points={POINTS}
          fill="none"
          stroke="url(#octaScoreGrad)"
          strokeWidth={STROKE}
          strokeLinejoin="round"
          strokeLinecap="round"
          strokeDasharray={PERIMETER}
          strokeDashoffset={dashOffset}
        />
      </Svg>
      <Text style={[styles.value, { fontSize: size >= 140 ? 52 : 36 }]}>
        {clamped}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  value: {
    fontWeight: '700',
    color: colors.brand,
    position: 'absolute',
  },
});
