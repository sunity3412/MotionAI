// 점수 계산 내역 섹션 (quick-260702-q8q) — 투명 감점-합산 tally 를 화면에 노출.
//
// belle 실기기 피드백(TestFlight #27, kip-up fault 88점): 점수는 투명 규칙
// (100 − 12 = 88)으로 계산되는데 앱이 내역을 안 보여줘 신뢰가 깎임. 채점 원칙
// ([[scoring-must-be-transparent-deduction-tally]] — "보고서가 −X−Y−Z=50 내역 노출")
// 의 UI 배선. 렌더 가드는 caller(result.tsx: mode1 + deductionBreakdown 존재).
//
// quick-260705-o0s — recordNumbers/basisLine prop 신설: 각 record 행에 영상의
// 빨간 점과 같은 번호(①②③, buildDeductionMarkers 단일 소스)를 접두하고 카드
// 최상단에 채점 기준 1줄(composeScoringBasisKo)을 표시한다. 두 prop 모두
// 미전달 시 렌더 diff 0 (다른 소비처/legacy 무회귀).
//
// 객관성: 저장된 record 값을 그대로 표기 — 합계 검증(100 + Σpoints ≠ final)이
// 어긋나도 UI 가 숫자를 조작하지 않는다 (있는 그대로 + final 우선).
// 토큰만 사용 (CLAUDE.md §4). 이모지 0. 라이트 전용.

import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import {
  circledNumberKo,
  formatDeductionRecord,
  formatDeductionNumber,
} from '../lib/deductionLabels';
import { colors, fontFamily, layout, radius, spacing, typography } from '../theme';
import type { DeductionBreakdown } from '../types/analysis';

// quick-260705-r6v — 원문자(①②③) 는 deductionLabels.circledNumberKo 단일 소스
// (범례/시트/내역 행이 같은 규칙 — 중복 2벌 제거).

// 33-15 (D-16) — 코칭 팁 카드에서 이동해 온 관절 각도 수치 행 (참고 영역).
// "각도 수치 = 점수 상세(참고 영역)로만" — 수치는 삭제가 아니라 이동
// ([[scoring-must-be-transparent-deduction-tally]] 투명 공개 원칙 유지).
export interface AngleReferenceRow {
  key: string; // angle key (left_knee 등) — 데이터 키잉, 동작명 하드코딩 0
  label: string; // JOINT_LABEL_KO 결과 (한국어 관절명)
  line: string; // "현재 148° → 기준 154°" / "추정 148° → 기준 154°"
  estimated: boolean; // 가림·측정 불확실 구간 (estimateGray 톤 + 각주)
}

export function ScoreBreakdownSection({
  breakdown,
  recordNumbers,
  basisLine,
  limitNotice,
  onRecordPress,
  aggregateMode,
  aggregateText,
  angleReference,
}: {
  breakdown: DeductionBreakdown;
  /** records 인덱스 정렬 번호 (null = 번호 없음). 영상 빨간 점과 동일 소스. */
  recordNumbers?: (number | null)[];
  /** 채점 기준 1줄 (composeScoringBasisKo). null/미전달 시 생략. */
  basisLine?: string | null;
  /**
   * IN-01 (quick-260724-q6b) — 역립 저신뢰 시 per-joint 감점 행을 단정하지 않도록
   * 집계 모드로 전환. truthy 면 records.map(+ empty-state)를 aggregateText 한 줄로
   * 치환하고 번호↔영상 각주를 숨긴다. baseline/= 종합 final 은 두 분기 공통 유지
   * (final 값 불변). 미전달(기존 caller) 시 렌더 diff 0.
   */
  aggregateMode?: boolean;
  /** aggregateMode 시 records 대신 렌더할 집계 문장(관절명 없음). */
  aggregateText?: string;
  /**
   * 29-CONTEXT D-05 — mode3 한계 고지 1줄 (측정 범위 + 다음 행동 유도). 카드
   * 최하단 footnote 슬롯에 기존 footnote 토큰으로 렌더. 미전달 시 렌더 diff 0
   * (mode1 호출부 무변경 — legacy/다른 소비처 무회귀).
   */
  limitNotice?: string;
  /**
   * quick-260705-r6v — record 행 탭 → 드릴다운 시트 오픈 (확대사진+수치+행동구).
   * 전달 시 record 행을 Pressable 로 감싸고 우측에 chevron 미니 표기(행 밀도 유지).
   * 미전달 시 렌더 diff 0 (다른 소비처/legacy 무회귀).
   */
  onRecordPress?: (recordIndex: number) => void;
  /**
   * 33-15 (D-16) — 관절 각도 참고 행 (코칭 팁 카드에서 이동). 미전달/빈 배열 시
   * 렌더 diff 0 (다른 소비처/legacy 무회귀). IN-01 저신뢰 시 caller 의 displayTips
   * 필터가 per-joint 팁을 제거하므로 자연히 빈 배열 (관절 단정 0).
   */
  angleReference?: AngleReferenceRow[];
}) {
  const gapCount = breakdown.coverageGaps?.length ?? 0;
  // 번호 매핑은 설명 없이는 발견되지 않는 규칙 — 번호가 1개 이상일 때만 각주.
  const hasAnyNumber = (recordNumbers ?? []).some((n) => n != null);
  return (
    <View style={styles.card}>
      {/* 채점 기준 1줄 (quick-260705-o0s) — 기준 점수 행 위 caption 톤. */}
      {basisLine ? <Text style={styles.basisLine}>{basisLine}</Text> : null}

      {/* 헤더 행 — baseline (미감점 천장 100, contract.md §10.1) */}
      <View
        style={styles.row}
        accessibilityLabel={`기준 점수 ${breakdown.baseline}점`}
      >
        <Text style={styles.baselineLabel}>기준 점수</Text>
        <Text style={styles.baselineValue}>{breakdown.baseline}</Text>
      </View>

      {/* IN-01 (quick-260724-q6b) — 역립 저신뢰 집계 모드: per-joint 감점 행 대신
          관절명 없는 집계 문장 1줄. records.map / empty-state 전체를 치환한다
          (번호가 없으므로 아래 각주도 hasAnyNumber 로 자동 숨김). = 종합 final 은
          아래 finalRow 에서 그대로 표기 (점수 불변). */}
      {aggregateMode ? (
        <Text style={styles.aggregateLine}>{aggregateText}</Text>
      ) : breakdown.records.length === 0 ? (
        <Text style={styles.emptyText}>
          측정 감점 없음 — 기준 점수 그대로예요.
        </Text>
      ) : (
        breakdown.records.map((rec, i) => {
          const row = formatDeductionRecord(rec);
          const num = recordNumbers?.[i] ?? null;
          const a11y =
            num != null
              ? `${num}번 ${row.label} 감점 ${formatDeductionNumber(Math.abs(rec.points))}점`
              : `${row.label} 감점 ${formatDeductionNumber(Math.abs(rec.points))}점`;
          const inner = (
            <>
              <View style={styles.recordLeft}>
                <Text style={styles.recordLabel}>
                  {/* 원문자 접두 — brand 색으로 "영상의 빨간 점과 같은 번호"
                      시각 연결 (quick-260705-o0s). null 이면 접두 없음. */}
                  {num != null ? (
                    <Text style={styles.recordNumber}>
                      {`${circledNumberKo(num)} `}
                    </Text>
                  ) : null}
                  {row.label}
                </Text>
                <Text style={styles.recordDetail}>{row.detailText}</Text>
              </View>
              <Text style={styles.recordPoints}>{row.pointsText}</Text>
              {/* quick-260705-r6v — 탭 진입점 chevron (onRecordPress 시만). */}
              {onRecordPress ? (
                <Ionicons
                  name="chevron-forward"
                  size={16}
                  color={colors.textSecondary}
                  style={styles.recordChevron}
                />
              ) : null}
            </>
          );
          // onRecordPress 전달 시 Pressable 로 감싸 시트 오픈 (미전달 시 렌더 diff 0).
          return onRecordPress ? (
            <Pressable
              key={`${rec.criterion}-${i}`}
              style={styles.row}
              onPress={() => onRecordPress(i)}
              accessibilityRole="button"
              accessibilityLabel={`${row.label} 감점 상세 보기`}
              hitSlop={4}
            >
              {inner}
            </Pressable>
          ) : (
            <View key={`${rec.criterion}-${i}`} style={styles.row} accessibilityLabel={a11y}>
              {inner}
            </View>
          );
        })
      )}

      {/* 번호 ↔ 영상 마커 매핑 안내 각주 (record 목록 아래, 합계 행 위).
          IN-01 — aggregateMode 시 번호 행 자체가 없으므로 각주도 숨김. */}
      {!aggregateMode && hasAnyNumber && (
        <Text style={styles.footnote}>
          번호는 위 영상의 빨간 점 위치와 같아요.
        </Text>
      )}

      {/* 합계 행 — final = breakdown.final (overallScore 재사용 금지) */}
      <View
        style={[styles.row, styles.finalRow]}
        accessibilityLabel={`종합 ${breakdown.final}점`}
      >
        <Text style={styles.finalLabel}>= 종합</Text>
        <Text style={styles.finalValue}>{breakdown.final}점</Text>
      </View>

      {/* 33-15 (D-16) — 관절 각도 참고 영역: 코칭 팁 카드에서 이동해 온 각도 수치의
          새 거처 (이동, 삭제 아님 — 투명 공개). 수치 톤 = badge 스케일 보조
          (D-09 헤드라인 수치 금지). 추정(가림·저신뢰) 행은 estimateGray + 각주. */}
      {angleReference && angleReference.length > 0 ? (
        <View style={styles.angleRefBlock}>
          <Text style={styles.angleRefTitle}>관절 각도 참고</Text>
          {angleReference.map((r) => (
            <View key={r.key} style={styles.angleRefRow}>
              <Text style={styles.angleRefLabel}>{r.label}</Text>
              <Text
                style={[
                  styles.angleRefValue,
                  r.estimated && styles.angleRefValueEstimated,
                ]}
              >
                {r.line}
              </Text>
            </View>
          ))}
          {angleReference.some((r) => r.estimated) ? (
            <Text style={styles.footnote}>
              추정 표시는 가림·측정 불확실 구간의 값이에요.
            </Text>
          ) : null}
        </View>
      ) : null}

      {/* coverage gap 각주 — 정직한 커버리지 노출 (fabricate 금지, ND-06 정신) */}
      {gapCount > 0 && (
        <Text style={styles.footnote}>
          {`측정하지 못해 점수에 반영하지 않은 항목이 ${gapCount}건 있어요.`}
        </Text>
      )}
      {breakdown.fallback === 'quantification_unavailable' && (
        <Text style={styles.footnote}>
          정밀 정량화가 불가해 측정 기하 종합으로 환산했어요.
        </Text>
      )}
      {/* 29-CONTEXT D-05 — mode3 한계 고지 (측정 범위 + 다음 행동 유도). caller 가
          mode3 일 때만 전달 → mode1 렌더 diff 0. */}
      {limitNotice ? <Text style={styles.footnote}>{limitNotice}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  // 기존 result 카드 패턴 mirror (result.tsx styles.card 상당) — 토큰만.
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.card,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    padding: spacing.cardPadding,
    gap: 12,
  },
  // 채점 기준 1줄 — caption 톤 (quick-260705-o0s).
  basisLine: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  // IN-01 (quick-260724-q6b) — 역립 저신뢰 집계 문장 1줄. basisLine 토큰 패턴 mirror
  // (caption + textSecondary, 색 하드코딩 금지).
  aggregateLine: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    width: '100%',
    gap: 12,
  },
  baselineLabel: { ...typography.boxLabel, color: colors.textPrimary },
  baselineValue: { ...typography.boxLabel, color: colors.textPrimary },
  // quick-260705-r6v — 탭 진입점 chevron (행 우측, 밀도 유지 미니 표기).
  recordChevron: { alignSelf: 'center', marginLeft: 2 },
  recordLeft: { flex: 1, gap: 2 },
  recordLabel: { ...typography.boxLabel, color: colors.textPrimary },
  // 원문자 번호 접두 — 영상 빨간 점(brand)과 같은 색으로 시각 연결.
  recordNumber: { ...typography.boxLabel, color: colors.brand },
  // detailText 2줄 허용 — 실측 근거(측정값/허용오차/초과분) 문구.
  recordDetail: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  // 감점 수치 — brand 계열 강조. 33-15 (D-16): listTitle → metricNumber 강등
  // (수치는 헤드라인이 아니라 근거 — badge 스케일 고정, 하드코딩 크기 0).
  recordPoints: { ...typography.metricNumber, color: colors.brand },
  finalRow: {
    borderTopWidth: 1,
    borderTopColor: colors.divider,
    paddingTop: 12,
    alignItems: 'flex-end',
  },
  finalLabel: { ...typography.boxLabel, color: colors.textPrimary },
  finalValue: { ...typography.metricNumber, color: colors.brand },
  // 33-15 (D-16) — 관절 각도 참고 영역 (코칭 팁 각도 수치의 새 거처). 참고 톤 —
  // 수치 강등 원칙(badge 스케일, D-05 하한 17) + estimateGray 재사용 (신규 색 0).
  angleRefBlock: {
    borderTopWidth: 1,
    borderTopColor: colors.divider,
    paddingTop: 10,
    gap: 6,
  },
  angleRefTitle: { ...typography.badge, color: colors.textSecondary },
  angleRefRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
  },
  angleRefLabel: {
    ...typography.badge,
    fontWeight: '400',
    fontFamily: fontFamily.regular,
    color: colors.textPrimary,
  },
  angleRefValue: { ...typography.badge, color: colors.textMid },
  angleRefValueEstimated: { color: colors.estimateGray },
  emptyText: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  footnote: {
    ...typography.captionSmall,
    color: colors.textSecondary,
    lineHeight: 16,
  },
});
