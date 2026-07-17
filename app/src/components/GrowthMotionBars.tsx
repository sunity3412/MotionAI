import { StyleSheet, Text, View } from 'react-native';
import type { MotionDeltaRow } from '../lib/growthSelectors';
import { colors, radius, spacing, typography } from '../theme';

// 동작별 상승/하락 리스트 — 주식창식 ▲▼ 델타 (30-CONTEXT D-05/D-06/D-09).
// D-09 통합 리스트: mode1 동작 행들 + '내 기록' 행을 배지(row.badge)로 구분해 한
// 리스트에 그린다. 각 행의 델타는 그룹 내부에서만 계산돼(growthSelectors.motionDeltas)
// 모드 혼합 왜곡이 없다.
//
// D-05 증감 = 점수 포인트 델타('+N점'/'−N점') — 등락률·일치율 표기 금지
// ([[mode3-progress-not-similarity]] invariant). 활동 주 1개뿐(delta=null)은 '첫 기록
// N점 (비교 전)'. D-06 노이즈 임계 없음 — 전달된 모든 행을 그대로 노출(필터·숨김 없음),
// 색은 주식창 관례: 상승 ▲=colors.brand / 하락 ▼=colors.declineBlue (기존 mode3 발전/후퇴
// 토큰은 부호-색이 반대라 성장 카드 재사용 금지). 유지(delta=0)는 중립 colors.textSecondary.
//
// 조합 근거 (30-PATTERNS No Analog — 정확한 선례 없음): 행 구조 = history.tsx 행
// (배지+제목+우측 수치)의 시각을 재사용, 델타 막대는 GrowthChart 의 svg 대신 폭 계산
// View 로 렌더(부재 게이트 폭 대응 — 퍼센트 폭 문자열 금지, 픽셀 number 폭 사용).
// Figma MCP(fileKey jrdI7kp245HkPfLB0nclsz)는 이 실행 환경에서 미접근이라 막대 세부
// (두께·정렬)는 design.md 카드 관례 기반 자체 판단.

// 막대 기하 상수 (GrowthChart 의 W/H/PAD 선례와 동일 — 도메인 기하값, 색·간격 토큰과 별개).
const BAR_UNIT = 5; // 점수 1점당 막대 픽셀
const BAR_MAX = 90; // 막대 최대 픽셀
const BAR_HEIGHT = 6;

interface DeltaVisual {
  text: string;
  color: string;
  barWidth: number;
  a11y: string;
}

// 델타 → 표기 텍스트·색·막대폭·a11y 문구. delta 부호로만 분기(임계·숨김 없음, D-06).
function deltaVisual(row: MotionDeltaRow): DeltaVisual {
  const { delta, latestAvg } = row;
  if (delta === null) {
    // 활동 주 1개 — 비교 대상 없음 (D-05 첫 기록).
    return {
      text: `첫 기록 ${latestAvg}점 (비교 전)`,
      color: colors.textSecondary,
      barWidth: 0,
      a11y: `첫 기록 ${latestAvg}점, 비교 전`,
    };
  }
  if (delta > 0) {
    return {
      text: `▲ +${delta}점`,
      color: colors.brand,
      barWidth: Math.min(delta * BAR_UNIT, BAR_MAX),
      a11y: `${delta}점 상승`,
    };
  }
  if (delta < 0) {
    const mag = Math.abs(delta);
    return {
      text: `▼ −${mag}점`,
      color: colors.declineBlue,
      barWidth: Math.min(mag * BAR_UNIT, BAR_MAX),
      a11y: `${mag}점 하락`,
    };
  }
  return {
    text: '±0점',
    color: colors.textSecondary,
    barWidth: 0,
    a11y: '변화 없음',
  };
}

export function GrowthMotionBars({ rows }: { rows: MotionDeltaRow[] }) {
  return (
    <View style={styles.list}>
      {rows.map((row) => {
        const v = deltaVisual(row);
        return (
          <View
            key={row.key}
            style={styles.row}
            accessibilityRole="text"
            accessibilityLabel={`${row.label}, ${row.badge}, ${v.a11y}`}
          >
            <Text style={styles.badge}>{row.badge}</Text>
            <Text style={styles.label} numberOfLines={1}>
              {row.label}
            </Text>
            <View style={styles.deltaWrap}>
              {v.barWidth > 0 && (
                <View
                  style={[
                    styles.bar,
                    { width: v.barWidth, backgroundColor: v.color },
                  ]}
                />
              )}
              <Text style={[styles.deltaText, { color: v.color }]}>
                {v.text}
              </Text>
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  list: { gap: 10 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 8,
    borderBottomWidth: 0.858,
    borderBottomColor: colors.divider,
  },
  badge: {
    ...typography.captionSmall,
    color: colors.textWhite,
    backgroundColor: colors.brand,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: radius.listItem,
    overflow: 'hidden',
  },
  label: {
    ...typography.listTitle,
    color: colors.textPrimary,
    flex: 1,
  },
  deltaWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.cardPadding / 2,
  },
  bar: {
    height: BAR_HEIGHT,
    borderRadius: BAR_HEIGHT / 2,
  },
  deltaText: {
    ...typography.caption,
    fontWeight: '700',
    minWidth: 64,
    textAlign: 'right',
  },
});
