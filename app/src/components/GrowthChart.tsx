import { View } from 'react-native';
import Svg, {
  Circle,
  Defs,
  LinearGradient,
  Polygon,
  Polyline,
  Stop,
  Text as SvgText,
} from 'react-native-svg';
import { colors } from '../theme';

// 홈 성장 그래프 — 분석 점수 추이 꺾은선 (design.md §6 + Figma 1:719).
// 점수(overallScore)는 KISMAM 실측값이라 #7-follow 후에도 그대로 유효.
// scores: 시간순(오래된→최근). y축은 데이터 min~max 기준이라 변화가 잘 보임.

const W = 320;
const H = 132;
const PAD_X = 18;
const PAD_TOP = 22; // 점수 라벨 공간
const PAD_BOT = 14;

export function GrowthChart({ scores }: { scores: number[] }) {
  if (scores.length < 2) return null;

  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const range = max - min || 1; // 전부 동점이면 평평하게
  const innerW = W - PAD_X * 2;
  const innerH = H - PAD_TOP - PAD_BOT;

  const pts = scores.map((s, i) => {
    const x = PAD_X + (i / (scores.length - 1)) * innerW;
    const y = PAD_TOP + (1 - (s - min) / range) * innerH;
    return [x, y] as const;
  });
  const line = pts.map(([x, y]) => `${x},${y}`).join(' ');
  const area = `${PAD_X},${H - PAD_BOT} ${line} ${W - PAD_X},${H - PAD_BOT}`;

  return (
    <View>
      <Svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`}>
        <Defs>
          <LinearGradient id="growthArea" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor={colors.brand} stopOpacity={0.2} />
            <Stop offset="1" stopColor={colors.brand} stopOpacity={0} />
          </LinearGradient>
        </Defs>
        <Polygon points={area} fill="url(#growthArea)" />
        <Polyline
          points={line}
          fill="none"
          stroke={colors.brand}
          strokeWidth={2.5}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {pts.map(([x, y], i) => {
          const isLast = i === pts.length - 1;
          return (
            <Circle
              key={`c${i}`}
              cx={x}
              cy={y}
              r={isLast ? 4.5 : 3.5}
              fill={isLast ? colors.brand : colors.bg}
              stroke={colors.brand}
              strokeWidth={2}
            />
          );
        })}
        {pts.map(([x, y], i) => (
          <SvgText
            key={`t${i}`}
            x={x}
            y={y - 10}
            fontSize={10}
            fontWeight="700"
            fill={colors.textSecondary}
            textAnchor="middle"
          >
            {scores[i]}
          </SvgText>
        ))}
      </Svg>
    </View>
  );
}
