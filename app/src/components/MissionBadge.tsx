// 오늘의 미션 / mode3 기록 갱신 배지 (32-10 Task 1 — D-10 확정 3요소 중 2·3).
//
// GATE-DECISIONS D-10(안 B): 게임 프레임 3요소 = 목표 게이지 바(GoalGaugeBar) +
// 오늘의 미션 + mode3 기록 갱신 배지. 이 컴포넌트가 뒤 두 요소를 담당한다. 적용 범위
// (안 B)는 감점 카드 + 성장 탭까지 — 전면 확장(안 C)·추가 아이디어(목표 근접 링 등)는
// 미채택(이 파일 헤더가 채택 범위의 인용).
//
// D-14 정합: 안전 결함은 게임화 금지이므로, 안전 미션에서는 호출측(DeductionCard)이
// 이 배지를 렌더하지 않는다(mission.isMission && !mission.isSafety 조건은 호출측 소관).
// 이 컴포넌트 자체는 게임 프레임 요소이므로 안전 카드에 절대 합성되지 않는다.
//
// 톤 = 친숙하되 장난스럽지 않게(D-12) — "오늘의 미션" / "기록 갱신" 담백한 카피.
// AccuracyLimitBadge 전형(visible/null/토큰/accessibility) 복제. 카피는 상수 분리.
// 토큰만 사용 (CLAUDE.md §4). 이모지 0. 라이트 전용.

import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, typography } from '../theme';

export type MissionBadgeVariant = 'mission' | 'record';

// 카피·아이콘 상수 — 변경 시 D-12 톤(친숙하되 장난스럽지 않게) 유지.
const COPY: Record<MissionBadgeVariant, { title: string; icon: 'flag' | 'ribbon' }> = {
  mission: { title: '오늘의 미션', icon: 'flag' },
  record: { title: '기록 갱신', icon: 'ribbon' },
};

interface MissionBadgeProps {
  variant: MissionBadgeVariant;
  // AccuracyLimitBadge 전형 — false 면 null(렌더 diff 0). 기본 true.
  visible?: boolean;
  // 보조 라벨(예: 미션 대상 부위·연속 개선 표현). 수치 헤드라인 금지(D-09) —
  // 호출측이 수치 없는 사람 말만 전달한다.
  label?: string;
}

export function MissionBadge({ variant, visible = true, label }: MissionBadgeProps) {
  if (!visible) return null;
  const c = COPY[variant];
  return (
    <View
      style={[styles.pill, variant === 'record' ? styles.recordPill : styles.missionPill]}
      accessibilityRole="text"
      accessibilityLabel={label ? `${c.title}: ${label}` : c.title}
    >
      <Ionicons name={c.icon} size={16} color={colors.brand} />
      <Text style={styles.title}>{c.title}</Text>
      {label ? <Text style={styles.label}>{label}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'flex-start',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: radius.button,
  },
  missionPill: { backgroundColor: colors.brandTint },
  recordPill: { backgroundColor: colors.brandSoft },
  title: {
    ...typography.badge,
    color: colors.brand,
  },
  label: {
    ...typography.badge,
    fontWeight: '400',
    color: colors.textPrimary,
    flexShrink: 1,
  },
});
