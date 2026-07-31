// 목표 게이지 바 (32-10 Task 1 — D-10 belle 강한 교정 + D-09 무수치 헤드라인).
//
// belle 강한 교정(GATE-DECISIONS D-10): "왜 자꾸 무릎각도를 둬 다르게 표현하자니깐."
//   · 사용자 측정 수치(각도)는 절대 전면/헤드라인 금지 — "이렇게 분석됐다" 근거로만.
//   · 게이지도 각도 숫자 확대 금지 — 목표까지 남은 정도를 길이(bar)로만 표현.
// 따라서 이 컴포넌트는 "목표까지 남은 정도"를 트랙 위 길이·마커로 표현하고, 수치는
// 하단 소형 배지 1곳("94°→71°")에만 둔다 — 이 배지가 게이지의 유일한 수치 노출점이다.
//
// 스케일은 자의적이지 않다(리뷰 HIGH): gaugeGeometry.computeGaugeGeometry 가 규칙
// 상수(record.tolerance) 기반 도메인으로만 비율을 계산하고, 규칙 상수가 없으면
// (null) 이 컴포넌트는 **null 을 반환**한다 — 호출측(DeductionCard)이 게이지 없이
// 수치 배지+텍스트로 정직하게 폴백한다.
//
// 채움/마커 위치는 백분율 문자열로 배치한다(트랙 내부 좌표 계산 — SegmentRow 선례).
// 이 백분율(%)은 렌더 좌표일 뿐 사용자에게 노출하지 않는다 — 화면 문자열은 단위 원문
// 배지("94°→71°")뿐이다(% 환산 금지, D-09).
//
// 토큰만 사용 (CLAUDE.md §4). 이모지 0. 라이트 전용.

import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { computeGaugeGeometry } from '../lib/gaugeGeometry';
import { colors, radius, typography } from '../theme';

// 단위 표기 매핑 — 'deg' 만 기호(°)로, 그 외 unit 은 원문 그대로(화이트리스트 강제로
// 실존 unit 을 배제하지 않는다 — 리뷰 반영). 순수 helper, DeductionCard 폴백도 공유.
export function unitSymbol(unit?: string): string {
  if (unit === 'deg') return '°';
  return unit ?? '';
}

// 저장값 그대로 표기 — 정수면 정수, 아니면 소수 1자리 (재계산 0, formatDeductionNumber 관례).
export function formatGaugeNumber(n: number): string {
  if (!Number.isFinite(n)) return String(n);
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

// 게이지 소형 수치 배지 문자열의 단일 출처 — 게이지가 그려질 때(여기)와 게이지 불가
// 폴백(DeductionCard)에서 **동일 문자열**을 쓰기 위해 export 한다. belle 원문
// "측정기준 94도→71도 이런 식으로 작게나마".
export function formatGoalBadge(current: number, target: number, unit?: string): string {
  const sym = unitSymbol(unit);
  return `${formatGaugeNumber(current)}${sym}→${formatGaugeNumber(target)}${sym}`;
}

interface GoalGaugeBarProps {
  current: number;
  target: number;
  /** 규칙 상수 유래 허용 오차(record.tolerance). 부재/무효 시 게이지 미표시(null). */
  tolerance?: number;
  /** 표시 단위(record.unit). 'deg'→° 매핑, 그 외 원문. */
  unit?: string;
  /** 방향은 시각 표기(힌트 문구)만 다르게 — 기하는 대칭. */
  direction?: 'increase' | 'decrease';
}

// 도메인 위치(비율)를 트랙 내부 백분율 문자열로 — 렌더 좌표 전용(사용자 비노출).
// 반환 타입 `${number}%` = RN DimensionValue 호환(left/width). 기하가 [0,1] 을
// 보장하나 부동소수 드리프트 방어로 clamp (SegmentRow 인라인 백분율 선례).
function pctStr(ratio: number): `${number}%` {
  const clamped = ratio < 0 ? 0 : ratio > 1 ? 1 : ratio;
  return `${clamped * 100}%`;
}

export function GoalGaugeBar({
  current,
  target,
  tolerance,
  unit,
  direction,
}: GoalGaugeBarProps) {
  // 규칙 상수(tolerance) 없으면 geometry=null → 게이지 미표시(호출측이 수치 폴백).
  const geo = computeGaugeGeometry(current, target, tolerance ?? Number.NaN);
  if (!geo) return null;

  const sym = unitSymbol(unit);
  const badge = formatGoalBadge(current, target, unit);
  // 방향 문구는 **화면에서 빠지고 스크린 리더에만** 남는다 (F-5). 화면은 기호에
  // 이름을 붙이는 쪽(범례)이 belle 지시이고, 문장을 하나 더 얹으면 D-05 문장 수
  // 규칙에 걸린다 — 방향 정보는 기하(점이 선의 좌/우)와 이 라벨이 함께 진다.
  const directionHint =
    direction === 'increase'
      ? '목표까지 늘리기'
      : direction === 'decrease'
        ? '목표까지 줄이기'
        : '목표까지';

  return (
    <View
      style={styles.wrap}
      accessibilityRole="progressbar"
      accessibilityLabel={`현재 ${formatGaugeNumber(current)}${sym}, 목표 ${formatGaugeNumber(target)}${sym} — ${directionHint}`}
    >
      <View style={styles.track}>
        {/* 허용 오차 밴드 = 목표 주변 "닿으면 되는" 구간 (goal zone, 브랜드 틴트). */}
        <View
          style={[
            styles.tolBand,
            { left: pctStr(geo.tolBandStart), width: pctStr(geo.tolBandEnd - geo.tolBandStart) },
          ]}
        />
        {/* 목표 마커 — 세로 선(브랜드). "여기까지" 지점. */}
        <View style={[styles.targetMarker, { left: pctStr(geo.targetRatio) }]} />
        {/* 현재 위치 마커 — 점(중립 다크 + 흰 링). 목표와의 간격 = 남은 거리(D-10). */}
        <View style={[styles.currentMarker, { left: pctStr(geo.ratio) }]} />
      </View>
      <View style={styles.legendRow}>
        {/* F-5 (33-G) — belle: "붉은 세로선 vs 검은 점 의미 불명. 기호만으로
            현재/허용선 구분 불가. 라벨 명시". 기호에 이름을 붙인다. 스와치는 위
            마커와 **같은 스타일 소스**(MARKER_FILL)에서 파생한다 — 스와치가 마커와
            어긋나면 라벨이 오히려 거짓이 된다. 크기만 줄인다.
            밴드(tolBand)에는 이름을 붙이지 않는다 — belle 이 지목한 건 두 기호이고,
            요소를 늘리면 D-07 ⑥(화면이 전보다 단순해야)에 어긋난다. */}
        <View style={styles.legendItems}>
          <View style={styles.legendItem}>
            <View style={styles.currentSwatch} />
            <Text style={styles.legendLabel}>지금</Text>
          </View>
          <View style={styles.legendItem}>
            <View style={styles.targetSwatch} />
            <Text style={styles.legendLabel}>목표</Text>
          </View>
        </View>
        {/* 소형 수치 배지 — 게이지의 유일한 수치 노출점(D-09). % 환산 없음. */}
        <View style={styles.badgePill}>
          <Text style={styles.badgeText}>{badge}</Text>
        </View>
      </View>
    </View>
  );
}

// 마커 채움 = 마커와 범례 스와치의 **단일 스타일 소스** (F-5, Q-16). 두 곳이 각자
// 색을 적으면 한쪽만 바뀌었을 때 라벨이 거짓이 된다 — 여기서 한 벌만 파생한다.
// 기하(위치·크기)는 각자 다르지만 "무엇으로 채워졌는가"는 반드시 같아야 한다.
const MARKER_FILL = {
  current: {
    backgroundColor: colors.neutralDark,
    borderWidth: 2,
    borderColor: colors.cardBg,
  },
  target: {
    backgroundColor: colors.brand,
    borderRadius: 2,
  },
} as const;

const styles = StyleSheet.create({
  wrap: { gap: 8, marginTop: 4 },
  track: {
    height: 14,
    borderRadius: 7,
    backgroundColor: colors.trackBg,
    position: 'relative',
  },
  tolBand: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    backgroundColor: colors.brandTint,
    borderRadius: 7,
  },
  targetMarker: {
    ...MARKER_FILL.target,
    position: 'absolute',
    top: -3,
    bottom: -3,
    width: 3,
    marginLeft: -1.5,
  },
  currentMarker: {
    ...MARKER_FILL.current,
    position: 'absolute',
    top: -2,
    width: 18,
    height: 18,
    marginLeft: -9,
    borderRadius: 9,
  },
  legendRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  legendItems: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flexShrink: 1,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  // 스와치 = 마커와 같은 채움, 크기만 축소 (currentMarker 18 → 12 / 세로선 높이 14 → 12).
  currentSwatch: {
    ...MARKER_FILL.current,
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  targetSwatch: {
    ...MARKER_FILL.target,
    width: 3,
    height: 12,
  },
  legendLabel: {
    ...typography.badge,
    fontWeight: '400',
    color: colors.textSecondary,
  },
  badgePill: {
    backgroundColor: colors.softBg,
    borderRadius: radius.listItem,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  badgeText: {
    ...typography.badge,
    color: colors.textPrimary,
  },
});
