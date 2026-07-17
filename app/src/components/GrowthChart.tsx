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
import type { WeeklyPoint } from '../lib/growthSelectors';
import { colors } from '../theme';

// 홈 성장 그래프 — 주별 평균 점수 추이 꺾은선 (30-CONTEXT D-01).
// 데이터 의미 = 한 주의 분석들을 평균낸 점 1개(WeeklyPoint.avg). 분석 없는 주는
// 점 없음 — 등간격 x축은 '활동 주 순번'이지 달력 간격이 아니다(빈 주 0점 채움 금지,
// growthSelectors.weeklyAverages 계약). y축은 데이터 min~max 정규화라 변화가 잘 보임.
//
// 출처: design.md §6 "성장 그래프 카드 (흰색 bordered, 주간 꺾은선)". Figma MCP
// (get_design_context, fileKey jrdI7kp245HkPfLB0nclsz)는 이 실행 환경에서 미접근이라
// (ui-figma-first 폴백) 세부 비주얼은 기존 GrowthChart 골격 유지 + design.md §6 준수로
// 자체 판단: 주 라벨 = weekStart 로컬 월/일 파생('M/D주'), 마지막 점 강조는 기존 관례 유지.

const W = 320;
const H = 132;
const PAD_X = 18;
const PAD_TOP = 22; // 점수 라벨 공간
const PAD_BOT = 26; // 주 시작일 라벨 공간

export function GrowthChart({ points }: { points: WeeklyPoint[] }) {
  // points.length < 2 면 null (D-03 폴백 임계 2와 정합 — 비교선 없이 점 1개는 추이 무의미).
  if (points.length < 2) return null;

  const values = points.map((p) => p.avg);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1; // 전부 동점이면 평평하게
  const innerW = W - PAD_X * 2;
  const innerH = H - PAD_TOP - PAD_BOT;

  const pts = points.map((p, i) => {
    const x = PAD_X + (i / (points.length - 1)) * innerW;
    const y = PAD_TOP + (1 - (p.avg - min) / range) * innerH;
    return [x, y] as const;
  });
  const line = pts.map(([x, y]) => `${x},${y}`).join(' ');
  const area = `${PAD_X},${H - PAD_BOT} ${line} ${W - PAD_X},${H - PAD_BOT}`;

  // 주 시작일 라벨 — weekStart(월요일 00:00 로컬 millis)에서 월/일 파생.
  const weekLabel = (weekStart: number) => {
    const d = new Date(weekStart);
    return `${d.getMonth() + 1}/${d.getDate()}주`;
  };

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
            key={`v${i}`}
            x={x}
            y={y - 10}
            fontSize={10}
            fontWeight="700"
            fill={colors.textSecondary}
            textAnchor="middle"
          >
            {points[i].avg}
          </SvgText>
        ))}
        {pts.map(([x], i) => (
          <SvgText
            key={`w${i}`}
            x={x}
            y={H - 8}
            fontSize={9}
            fontWeight="400"
            fill={colors.textSecondary}
            textAnchor="middle"
          >
            {weekLabel(points[i].weekStart)}
          </SvgText>
        ))}
      </Svg>
    </View>
  );
}
