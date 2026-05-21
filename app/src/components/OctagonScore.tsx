import { StyleSheet, Text, View } from 'react-native';
import Svg, { Polygon } from 'react-native-svg';
import { colors, typography } from '../theme';

// 홈 최근분석 카드의 점수 위젯 (design.md §5-5 보강 — Figma 1:719: 옥타곤 외곽선).
// 95.43px × 95.43px 정팔각형 + 중앙 점수 텍스트. 외곽선 두께 3px.
// 정점 좌표는 viewBox 100 기준으로 미리 계산한 정팔각형 (inset 4 — stroke 잘림 방지).

const SIZE = 95;
const STROKE = 3;
const VIEW = 100;
// 정팔각형 8개 정점 (중심 50, 반지름 46, 시작각 22.5°).
// 각도 22.5° + n*45°. inset 4 → 시각적으로 stroke 끝까지 화면 안.
const POINTS = '92.5,67.6 67.6,92.5 32.4,92.5 7.5,67.6 7.5,32.4 32.4,7.5 67.6,7.5 92.5,32.4';

export function OctagonScore({ score }: { score: number }) {
  return (
    <View style={styles.wrap}>
      <Svg width={SIZE} height={SIZE} viewBox={`0 0 ${VIEW} ${VIEW}`}>
        <Polygon
          points={POINTS}
          fill={colors.bg}
          stroke={colors.brand}
          strokeWidth={STROKE}
          strokeLinejoin="round"
        />
      </Svg>
      <Text style={styles.value}>{score}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: SIZE,
    height: SIZE,
    alignItems: 'center',
    justifyContent: 'center',
  },
  value: {
    ...typography.score,
    color: colors.brand,
    position: 'absolute',
  },
});
