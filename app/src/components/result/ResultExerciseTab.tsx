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

import { colors, fontFamily, layout, radius, typography } from '../../theme';
import { CORRECTIVE_EXERCISES } from '../../data/correctiveExercises';
import { exerciseBadgeLabel } from '../../lib/resultSummary';
import type { CoachQuestion, RecommendedExercise } from '../../types/analysis';

const K = 390 / 467.206;

// belle 09-09 — 시안 4 는 운동 카드가 **3개**다. 백엔드는 3~5개를 내려주므로
// (exercise_map 산출) 넘치는 것은 아래 화살표(전체 보완 운동 보기)가 맡는다.
const MAX_ROWS = 3;

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
  // 질문 행 들여쓰기 — '?' 원이 카드 좌단 +30.06pt 에서 시작한다(구분선보다 ~10.6 안쪽).
  // 종전엔 들여쓰기 0 이라 구분선과 같은 선(+19.3)에서 시작했다 (audit 09-09).
  qIndent: 30.06 - 19.1 - layout.cardBorderWidth, // 10.1
  qTextGap: 15.4, // '?' 원 ↔ 질문 텍스트 (종전 12 → 실측 11.67)
  btnH: 71.3 * K, // 59.5
  // 세로 간격 — 시안 4 실측. 운동 카드 밑변 501.7 → 강사 카드 윗변 519.2 = 17.5 /
  // 강사 카드 밑변 742.8 → 버튼 윗변 768.1 = 25.3. 부모(result.tsx)의 공통 gap 에 맡기지
  // 않고 이 탭이 직접 갖는다 — 아래 컴포넌트 주석 참조.
  cardGap: 17.6,
  btnGap: 25.2,
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
  const hasExercises = exercises.length > 0;
  const hasQuestions = questions.length > 0;
  // 종전엔 fragment 라 부모 ScrollView 의 공통 gap 이 카드↔카드·카드↔버튼줄에 똑같이
  // 들어갔다(14). 시안은 둘이 다르다(17.6 / 25.2). View 로 감싸 부모 gap 은 탭 위에 한 번만
  // 걸리게 하고, 안쪽 간격은 이 탭이 갖는다 — 부모 gap 이 바뀌어도 여기 값은 흔들리지 않는다.
  return (
    <View>
      {hasExercises ? (
        <View style={styles.card}>
          {exercises.slice(0, MAX_ROWS).map((ex, i) => {
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
                  <Text
                    style={styles.purpose}
                    numberOfLines={2}
                    lineBreakStrategyIOS="hangul-word"
                  >
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
              {/* 시안 잉크 24.2×12.5pt. Ionicons 셰브론은 잉크가 박스의 약 45% 라 size 20 은
                  잉크 13.3×7.7 로 절반이었다(잉크/박스 혼동, audit 09-09) → 30. */}
              <Ionicons name="chevron-down" size={30} color={colors.brand} />
            </Pressable>
          ) : null}
        </View>
      ) : null}

      {hasQuestions ? (
        <View style={[styles.card, hasExercises ? styles.cardGap : null]}>
          <View style={styles.pill}>
            <Text style={styles.pillText}>강사에게 확인할 점</Text>
          </View>
          {questions.map((q, i) => (
            <View key={`q-${i}`} style={[styles.qRow, i > 0 ? styles.qDivided : null]}>
              <View style={styles.qMark}>
                <Text style={styles.qMarkText}>?</Text>
              </View>
              <Text style={styles.qText} lineBreakStrategyIOS="hangul-word">
                {q.text}
              </Text>
            </View>
          ))}
        </View>
      ) : null}

      {onReanalyze || shareMessage ? (
        <View style={[styles.btnRow, hasExercises || hasQuestions ? styles.btnGap : null]}>
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
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.resultCard,
    // 시안 테두리 #6C6C6E · 0.83pt — 교정포인트 카드와 같은 근거(hairline 은 시각 무게 1/7.6).
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.resultCardBorder,
    padding: D.cardPad,
  },
  cardGap: { marginTop: D.cardGap },
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
  // 굵게는 fontFamily 로 — 정적 TTF 패밀리명(Pretendard-Regular)을 지정한 상태라 iOS 는
  // fontWeight 만으론 굵기를 바꾸지 않는다. 종전엔 이 때문에 시안 대비 획이 33% 얇았다
  // (채움률 0.400 → 0.267, audit 09-09). fontWeight 는 폰트 로드 실패 시 폴백용으로 남긴다.
  badgeText: {
    ...typography.captionSmall,
    fontSize: 9,
    lineHeight: 11,
    fontWeight: '700',
    fontFamily: fontFamily.bold,
    color: colors.textWhite,
    textAlign: 'center',
  },
  col: { flex: 1, marginLeft: D.colLeft },
  // 시안 ≈값(이름 ≈17 / 용량 ≈9 / 설명 ≈8)은 09-08 에 '한글 ≈ 1em' 가정으로 역산한 것이다.
  // 번들 Pretendard 의 한글 advance 는 0.864em 이라(typography.ts) 폭 기반 역산이면 0.864 로
  // 나눈 19.7 / 10.4 / 9.3 이 맞다. 09-09 audit 30건에 이 셋은 없어 재실측 전 — 값은 두고
  // 근거만 정정한다. 설명은 앱 최소 크기(captionSmall 10) 아래라 9 로 잡아 두었다.
  name: { ...typography.listTitle, fontSize: 16, color: colors.textPrimary },
  dose: { ...typography.resultChip, fontSize: 11, color: colors.brand, marginTop: 2 },
  purpose: {
    ...typography.captionSmall,
    fontSize: 9,
    lineHeight: 13,
    // 운동 행 배경은 resultCardTint(#FEF8F7)다. 종전 textSecondary(#ACACAC)는 그 위 2.16:1 —
    // 9pt 본문에 AA 미달이라 틴트 위에서 통과하는 가장 밝은 중성 회색 토큰(4.71:1)으로.
    color: colors.resultTextMeta,
    marginTop: 4,
  },
  // 시안: 셰브론 잉크 윗변이 마지막 운동 행 밑변에서 19pt 아래 (종전 10).
  more: { alignItems: 'center', paddingTop: 19 },

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
  // 시안 16.0 (종전 resultWarnTitle 12). 흰 글자 on #6E9985 = 3.20:1 — 16pt bold 는
  // large text 라 3:1 로 통과한다.
  pillText: { ...typography.resultCoachPill, color: colors.textWhite },
  qRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingLeft: D.qIndent,
    gap: D.qTextGap,
    minHeight: D.qGap,
  },
  // 질문 구분선 — 카드 안쪽 여백선에서 끝까지. 색·두께는 교정포인트 행 구분선과 같은 토큰.
  qDivided: {
    borderTopWidth: layout.cardBorderWidth,
    borderTopColor: colors.resultDivider,
  },
  qMark: {
    width: 18.4,
    height: 18.4,
    borderRadius: 9.2,
    backgroundColor: colors.resultCoachGreen,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // badgeText 와 같은 이유로 fontFamily.bold — fontWeight 만으론 iOS 가 굵기를 무시한다.
  qMarkText: {
    ...typography.captionSmall,
    fontSize: 10,
    fontWeight: '700',
    fontFamily: fontFamily.bold,
    color: colors.textWhite,
  },
  qText: { ...typography.resultSub, fontSize: 11, color: colors.textHi, flex: 1 },

  btnRow: { flexDirection: 'row', gap: 12 },
  btnGap: { marginTop: D.btnGap },
  btnGhost: {
    width: 114.6,
    height: D.btnH,
    borderRadius: radius.button,
    backgroundColor: colors.resultChipBg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // 시안 글자색은 빨강(#E94D37 → 브랜드 #FF4B33). 종전 검정은 옆 '강사에게 공유'(빨강 채움
  // +흰 글자)와의 빨강 페어를 깼다. 브랜드 on #FCEFED 는 2.97:1 로 large-text 3:1 에 살짝
  // 못 미치지만 브랜드색이라 못 바꾼다 (260909-ji1 PLAN §7, belle 보고 항목).
  btnGhostText: { ...typography.resultCta, color: colors.brand },
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
