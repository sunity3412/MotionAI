// 보완운동 탭 — 운동 카드 3개 + '강사에게 확인할 점' + 다시 분석/공유.
// 피그마 `분석 디자인 업데이트` 시안 4 (belle 09-09).
//
// 내용은 전부 doc 저장값이다 — 운동은 `result.recommendedExercises`(백엔드
// exercise_map 산출), 질문은 `result.coachQuestions`(D-28 자동 등재). 없으면 그 카드를
// 그리지 않는다. 배지("손목 보완")는 운동 이름을 fixture 의 결함표에 되짚어 얻는다
// (resultSummary.exerciseBadgeLabel) — 못 찾으면 배지 없이 그린다.
//
// 시안 실측 (화면 좌상단 기준 px → pt, k = 390/467.206 = 0.83475):
//   운동 카드      43.7, 182.3, 379.9 × 418.7px → 36.5, 152.2, 317.1 × 349.5pt
//     운동 행      66.6, 207.4, 334.1 × 97.4px → 55.6, 173.1, 278.9 × 81.3pt (카드 안 19.1 여백)
//     행 간격      110.9px → 92.6pt
//     배지 원      54.0 × 54.0px → 45.1pt (행 좌 +22.4, 상 +19.9)
//     텍스트 열    행 좌 +83.2pt
//   강사 카드      43.7, 622.0, 379.9 × 267.9px → 36.5, 519.2, 317.1 × 223.6pt
//     초록 pill    247.4 × 35.6px → 206.5 × 29.7pt (카드 상 +25.0, 가운데)
//     질문 간격    61.3px → 51.0pt (첫 질문 카드 상 +81.8)
//   버튼          41.9, 920.1, 137.3 × 71.3px → 35.0, 768.1, 114.6 × 59.5pt
import { Pressable, Share, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { colors, radius, typography } from '../../theme';
import { CORRECTIVE_EXERCISES } from '../../data/correctiveExercises';
import { exerciseBadgeLabel } from '../../lib/resultSummary';
import type { CoachQuestion, RecommendedExercise } from '../../types/analysis';

const K = 390 / 467.206;

const D = {
  cardPad: 19.1,
  rowH: 97.4 * K, // 81.3
  rowGap: 110.9 * K - 97.4 * K, // 11.3
  badge: 54.0 * K, // 45.1
  badgeLeft: 22.4,
  colLeft: 83.2 - 22.4 - 45.1, // 배지 오른쪽 ~ 텍스트 열 사이 간격 = 15.7
  pillW: 247.4 * K, // 206.5
  pillH: 35.6 * K, // 29.7
  qGap: 61.3 * K, // 51.2
  btnH: 71.3 * K, // 59.5
} as const;

export interface ResultExerciseTabProps {
  exercises: readonly RecommendedExercise[];
  questions: readonly CoachQuestion[];
  /** '전체 보완 운동 보기' — 기존 라이브러리 모달. 미전달 시 미렌더. */
  onSeeAllExercises?: () => void;
  /** '다시 분석' */
  onReanalyze?: () => void;
  /** 공유 문구. 미전달 시 공유 버튼 미렌더. */
  shareMessage?: string | null;
}

export function ResultExerciseTab({
  exercises,
  questions,
  onSeeAllExercises,
  onReanalyze,
  shareMessage,
}: ResultExerciseTabProps) {
  return (
    <>
      {exercises.length > 0 ? (
        <View style={styles.card}>
          {exercises.map((ex, i) => {
            const badge = exerciseBadgeLabel(ex.name, CORRECTIVE_EXERCISES);
            return (
              <View
                key={`${ex.name}-${i}`}
                style={[styles.row, i > 0 ? styles.rowGap : null]}
              >
                <View style={styles.badge}>
                  {badge ? (
                    <Text style={styles.badgeText} numberOfLines={2}>
                      {badge.replace(' ', '\n')}
                    </Text>
                  ) : (
                    <Ionicons name="barbell" size={18} color={colors.textWhite} />
                  )}
                </View>
                <View style={styles.col}>
                  <Text style={styles.name} numberOfLines={1}>
                    {ex.name}
                  </Text>
                  <Text style={styles.dose} numberOfLines={1}>
                    {ex.setsReps}
                  </Text>
                  <Text style={styles.purpose} numberOfLines={2}>
                    {ex.purpose}
                  </Text>
                </View>
              </View>
            );
          })}
          {onSeeAllExercises ? (
            <Pressable
              onPress={onSeeAllExercises}
              accessibilityRole="button"
              accessibilityLabel="전체 보완 운동 보기"
              hitSlop={10}
              style={styles.more}
            >
              <Ionicons name="chevron-down" size={20} color={colors.brand} />
            </Pressable>
          ) : null}
        </View>
      ) : null}

      {questions.length > 0 ? (
        <View style={styles.card}>
          <View style={styles.pill}>
            <Text style={styles.pillText}>강사에게 확인할 점</Text>
          </View>
          {questions.map((q, i) => (
            <View key={`q-${i}`} style={[styles.qRow, i > 0 ? styles.qDivided : null]}>
              <View style={styles.qMark}>
                <Text style={styles.qMarkText}>?</Text>
              </View>
              <Text style={styles.qText}>{q.text}</Text>
            </View>
          ))}
        </View>
      ) : null}

      {onReanalyze || shareMessage ? (
        <View style={styles.btnRow}>
          {onReanalyze ? (
            <Pressable
              onPress={onReanalyze}
              accessibilityRole="button"
              accessibilityLabel="다시 분석"
              style={({ pressed }) => [styles.btnGhost, pressed && styles.pressed]}
            >
              <Text style={styles.btnGhostText}>다시 분석</Text>
            </Pressable>
          ) : null}
          {shareMessage ? (
            <Pressable
              onPress={() => {
                void Share.share({ message: shareMessage });
              }}
              accessibilityRole="button"
              accessibilityLabel="강사에게 공유"
              style={({ pressed }) => [styles.btnBrand, pressed && styles.pressed]}
            >
              <Ionicons name="share-outline" size={16} color={colors.textWhite} />
              <Text style={styles.btnBrandText}>강사에게 공유</Text>
            </Pressable>
          ) : null}
        </View>
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.resultCard,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.divider,
    padding: D.cardPad,
  },
  row: {
    minHeight: D.rowH,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.resultCardTint,
    borderRadius: radius.resultBox,
    paddingLeft: D.badgeLeft,
    paddingRight: 14,
  },
  rowGap: { marginTop: D.rowGap },
  badge: {
    width: D.badge,
    height: D.badge,
    borderRadius: D.badge / 2,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeText: {
    ...typography.captionSmall,
    fontSize: 9,
    lineHeight: 11,
    fontWeight: '700',
    color: colors.textWhite,
    textAlign: 'center',
  },
  col: { flex: 1, marginLeft: D.colLeft },
  // 시안 실측: 이름 ≈17pt / 용량 ≈9 / 설명 ≈8. 설명은 앱 최소 크기(captionSmall 10)
  // 아래라 9 로 올렸다 — 더 줄이면 읽히지 않는다.
  name: { ...typography.listTitle, fontSize: 16, color: colors.textPrimary },
  dose: { ...typography.resultChip, fontSize: 11, color: colors.brand, marginTop: 2 },
  purpose: {
    ...typography.captionSmall,
    fontSize: 9,
    lineHeight: 13,
    color: colors.textSecondary,
    marginTop: 4,
  },
  more: { alignItems: 'center', paddingTop: 10 },

  // '강사에게 확인할 점' — 시안 실측 초록 #6E9985.
  pill: {
    alignSelf: 'center',
    width: D.pillW,
    height: D.pillH,
    borderRadius: D.pillH / 2,
    backgroundColor: colors.resultCoachGreen,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pillText: { ...typography.resultWarnTitle, color: colors.textWhite },
  qRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    minHeight: D.qGap,
  },
  qDivided: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.divider,
  },
  qMark: {
    width: 18.4,
    height: 18.4,
    borderRadius: 9.2,
    backgroundColor: colors.resultCoachGreen,
    alignItems: 'center',
    justifyContent: 'center',
  },
  qMarkText: {
    ...typography.captionSmall,
    fontSize: 10,
    fontWeight: '700',
    color: colors.textWhite,
  },
  qText: { ...typography.resultSub, fontSize: 11, color: colors.textHi, flex: 1 },

  btnRow: { flexDirection: 'row', gap: 12 },
  btnGhost: {
    width: 114.6,
    height: D.btnH,
    borderRadius: radius.button,
    backgroundColor: colors.resultChipBg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnGhostText: { ...typography.resultCta, color: colors.textPrimary },
  btnBrand: {
    flex: 1,
    height: D.btnH,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  btnBrandText: { ...typography.resultCta, color: colors.textWhite },
  pressed: { opacity: 0.85 },
});
