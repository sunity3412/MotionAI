// Phase 12 Wave 1 (Plan 12-02 T3) — Phase 9 ForcePatternFinding 자세히 모달.
//
// 책임:
//   - ForcePatternCard tap → 본 BottomSheet open (UI-SPEC §7 1:1 mirror)
//   - finding.interpretation 본문 + chip + confidence + "어떻게 측정됐나" 카드 +
//     "관련 부위" + 강사 안내 + 닫기 버튼
//   - DimensionDetailModal.tsx pattern mirror (Phase 12.5 일관성, D-12-U1)
//
// Phase 11 통합 site:
//   - finding.interpretation = canned KO (현재) → LLM 풍부화 자동 교체.
//   - finding.reason = EN debug — 모달 안 KO 한 줄 정도 노출 (Phase 11 시 KO
//     자연어로 풍부화).
//   - 본 component 인터페이스 변경 X.
//
// 토큰만 사용 (CLAUDE.md §4 / D-12-U5). brand #FF4B33 변경 0. 이모지 0.

import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import { colors, radius } from '../theme';
import type {
  ForceDirectionPattern,
  ForcePatternFinding,
} from '../types/analysis';

const PATTERN_LABEL_KO: Record<ForceDirectionPattern, string> = {
  release: 'RELEASE',
  pull: 'PULL',
  push: 'PUSH',
  brace: 'BRACE',
  rotate: 'ROTATE',
  unknown: '정보',
};

function confidenceLabel(c: number): { text: string; color: string } {
  if (c >= 0.7) return { text: '신뢰도 높음', color: colors.brand };
  if (c >= 0.5) return { text: '신뢰도 보통', color: colors.textMid };
  return { text: '신뢰도 낮음', color: colors.textLo };
}

// quick-260702-q8q — 실측 근거 (veto fallback finding 전용, result.tsx 가 조립).
// 존재 시 아래 3개 템플릿 문구("추정한 가능성/확인 필요/거울 보며")를 실데이터로
// 교체 렌더. 없으면 현행 템플릿 그대로 (Phase 9 일반 finding/legacy doc 무회귀).
export type MeasuredEvidence = {
  measurementText: string;
  // 판정 일치 절대 횟수 — 분모(총 샘플 수)는 Firestore 에 없어 "N/M" 표기 불가
  // (플랜 planner_findings 6). null 이면 표본 문구 생략.
  supportCount: number | null;
  jointDeltas: {
    jointLabel: string;
    studentDeg: number;
    referenceDeg: number;
    deltaDeg: number;
    overTolerance: boolean; // |delta| > 20° (KEYPOINT_DELTA_HIGHLIGHT_DEG 정합)
  }[];
};

export type ForcePatternDetailModalProps = {
  visible: boolean;
  finding: ForcePatternFinding | null;
  rank?: number;
  measuredEvidence?: MeasuredEvidence;
  onClose: () => void;
};

export function ForcePatternDetailModal({
  visible,
  finding,
  rank,
  measuredEvidence,
  onClose,
}: ForcePatternDetailModalProps) {
  const { height: winH } = useWindowDimensions();
  // finding=null 시 visible=false 강제 — 깜빡임 방지 (조건부 렌더 X).
  const open = visible && finding != null;
  const sheetHeight = Math.round(winH * 0.85);

  // null 이면 Modal 자체는 mount 유지 (visible=false) — RN 권장 패턴.
  if (!finding) {
    return <Modal visible={false} transparent animationType="slide" />;
  }

  const patternLabel = PATTERN_LABEL_KO[finding.pattern];
  const isUnknown = finding.pattern === 'unknown';
  const conf = typeof finding.confidence === 'number' ? finding.confidence : 0;
  const confLabel = confidenceLabel(conf);
  const rankText = rank != null ? `실패 원인 #${rank + 1}` : '실패 원인';
  const reasonKo = finding.reason
    ? finding.reason
    : 'AI 가 동작 신호를 기반으로 추정한 가능성입니다.';

  return (
    <Modal
      visible={open}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.backdrop}>
        <Pressable
          style={styles.backdropTop}
          onPress={onClose}
          accessibilityRole="button"
          accessibilityLabel="닫기"
        />
        <View style={[styles.sheet, { height: sheetHeight }]}>
          <View style={styles.handle} />

          <View style={styles.titleRow}>
            <Text style={styles.title}>{rankText}</Text>
            <Pressable
              onPress={onClose}
              accessibilityRole="button"
              accessibilityLabel="닫기"
              hitSlop={10}
              style={styles.closeBtn}
            >
              <Ionicons name="close" size={22} color={colors.textMid} />
            </Pressable>
          </View>

          <ScrollView
            style={styles.scroll}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            <View style={styles.chipsRow}>
              <View
                style={[
                  styles.patternChip,
                  isUnknown
                    ? styles.patternChipUnknown
                    : styles.patternChipBrand,
                ]}
              >
                <Text
                  style={[
                    styles.patternChipText,
                    isUnknown
                      ? styles.patternChipTextUnknown
                      : styles.patternChipTextBrand,
                  ]}
                >
                  {patternLabel}
                </Text>
              </View>
              {finding.jointHint ? (
                <View style={styles.jointHintChip}>
                  <Text style={styles.jointHintChipText}>
                    {finding.jointHint}
                  </Text>
                </View>
              ) : null}
              <Text style={[styles.confLabel, { color: confLabel.color }]}>
                {confLabel.text}
              </Text>
            </View>

            <Text style={styles.body}>{finding.interpretation}</Text>

            <Text style={styles.coachLine}>
              강사가 함께 보면 더 구체적 피드백을 받을 수 있어요
            </Text>

            {/* quick-260702-q8q — 실측 근거 존재 시 템플릿 문구를 실데이터로 교체.
                evidence 없으면 현행 그대로 (Phase 9 일반 finding 무회귀). */}
            <View style={styles.measureCard}>
              <Text style={styles.measureTitle}>이 원인은 어떻게 측정됐나</Text>
              <Text style={styles.measureBody}>
                {measuredEvidence ? measuredEvidence.measurementText : reasonKo}
              </Text>
              {measuredEvidence != null &&
              measuredEvidence.supportCount != null ? (
                <Text style={styles.measureBody}>
                  {`분석 표본 ${measuredEvidence.supportCount}회에서 같은 결함이 확인됐어요.`}
                </Text>
              ) : null}
            </View>

            {measuredEvidence && measuredEvidence.jointDeltas.length > 0 ? (
              <View style={styles.deltaTable}>
                <Text style={styles.deltaTableTitle}>관련 부위 — 관절별 편차</Text>
                {measuredEvidence.jointDeltas.map((d, i) => (
                  <View
                    key={`${d.jointLabel}-${i}`}
                    style={styles.deltaRow}
                    accessibilityLabel={`${d.jointLabel} 내 ${d.studentDeg}도, 기준 ${d.referenceDeg}도, 차이 ${d.deltaDeg}도${d.overTolerance ? ', 허용오차 초과' : ''}`}
                  >
                    <Text
                      style={[
                        styles.deltaJoint,
                        d.overTolerance && styles.deltaOver,
                      ]}
                    >
                      {d.jointLabel}
                    </Text>
                    <Text
                      style={[
                        styles.deltaValues,
                        d.overTolerance && styles.deltaOver,
                      ]}
                    >
                      {`내 ${d.studentDeg}° / 기준 ${d.referenceDeg}° (차이 ${d.deltaDeg}°)`}
                    </Text>
                  </View>
                ))}
              </View>
            ) : (
              <View style={styles.dotRow}>
                <View style={styles.dot} />
                <Text style={styles.dotText}>
                  <Text style={styles.dotLabel}>관련 부위 — </Text>
                  {finding.jointHint ?? '확인 필요'}
                </Text>
              </View>
            )}
            <View style={styles.dotRow}>
              <View style={styles.dot} />
              <Text style={styles.dotText}>
                <Text style={styles.dotLabel}>확인하기 — </Text>
                {measuredEvidence
                  ? "위 '문제 부위 확대 비교'와 편차표의 강조 관절을 함께 확인"
                  : '거울 보며 동작 직접 재현'}
              </Text>
            </View>

            <View style={styles.footerCard}>
              <Text style={styles.footerBody}>
                AI 가 추정한 가능성이에요. 강사 수업과 함께 확인하면 가장 정확한
                피드백을 받을 수 있어요.
              </Text>
            </View>
          </ScrollView>

          <Pressable
            onPress={onClose}
            accessibilityRole="button"
            accessibilityLabel="닫기"
            style={({ pressed }) => [styles.cta, pressed && styles.ctaPressed]}
          >
            <Text style={styles.ctaText}>닫기</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },
  backdropTop: { flex: 1 },
  sheet: {
    backgroundColor: colors.bg,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingTop: 12,
    paddingBottom: 24,
    paddingHorizontal: 20,
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: colors.border,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 12,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.textHi,
  },
  closeBtn: { padding: 4 },
  scroll: { flex: 1 },
  scrollContent: { paddingBottom: 16, gap: 14 },

  chipsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  patternChip: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 11,
  },
  patternChipBrand: { backgroundColor: colors.brand },
  patternChipUnknown: { backgroundColor: colors.softBg },
  patternChipText: { fontSize: 10, fontWeight: '600' },
  patternChipTextBrand: { color: colors.textWhite },
  patternChipTextUnknown: { color: colors.textMid },
  jointHintChip: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 11,
    backgroundColor: colors.softBg,
  },
  jointHintChipText: {
    fontSize: 11,
    fontWeight: '500',
    color: colors.textHi,
  },
  confLabel: {
    fontSize: 11,
    fontWeight: '500',
    marginLeft: 'auto',
  },

  body: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textHi,
    lineHeight: 26,
  },
  coachLine: {
    fontSize: 12,
    fontWeight: '400',
    color: colors.textLo,
    lineHeight: 18,
  },

  measureCard: {
    backgroundColor: colors.softBg,
    borderRadius: 12,
    padding: 16,
    gap: 6,
  },
  measureTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textHi,
  },
  measureBody: {
    fontSize: 12,
    fontWeight: '400',
    color: colors.textMid,
    lineHeight: 18,
  },

  // quick-260702-q8q — 관절별 편차표 (라이브러리 추가 금지 — 단순 View 행 목록).
  deltaTable: {
    backgroundColor: colors.softBg,
    borderRadius: 12,
    padding: 16,
    gap: 8,
  },
  deltaTableTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textHi,
  },
  deltaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  deltaJoint: {
    fontSize: 12,
    fontWeight: '500',
    color: colors.textMid,
  },
  deltaValues: {
    fontSize: 12,
    fontWeight: '400',
    color: colors.textMid,
    flexShrink: 1,
    textAlign: 'right',
  },
  // 허용오차(20°) 초과 행 — brand 강조.
  deltaOver: {
    color: colors.brand,
    fontWeight: '600',
  },

  dotRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.brand,
    marginTop: 7,
  },
  dotText: {
    flex: 1,
    fontSize: 13,
    fontWeight: '500',
    color: colors.textHi,
    lineHeight: 19,
  },
  dotLabel: { fontWeight: '600', color: colors.textHi },

  footerCard: {
    backgroundColor: colors.brandSoft,
    borderRadius: 12,
    padding: 14,
    opacity: 0.6,
  },
  footerBody: {
    fontSize: 11,
    fontWeight: '400',
    color: colors.textHi,
    lineHeight: 17,
  },

  cta: {
    marginTop: 16,
    height: 54,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    justifyContent: 'center',
    alignItems: 'center',
  },
  ctaPressed: { opacity: 0.85 },
  ctaText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textWhite,
  },
});
