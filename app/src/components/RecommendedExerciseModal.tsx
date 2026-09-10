// Phase 13 (Plan 13-A, PERS-03) — "다른 운동 보기" 보완 운동 모달.
//
// quick-260910-pbs (belle 2026-09-03 "뭐가 이렇게 많아. 뭘 다 나열해놨어"):
// 종전엔 props 가 {visible, onClose} 뿐이라 **어느 분석에서 열어도 라이브러리
// 14그룹 43행이 똑같이** 나왔다(이름 유니크 29 — 14행이 중복). 이제 모달은 이
// 분석의 결함 그룹 + 사용자 통증부위 그룹만 그린다. 전면 카드(ResultExerciseTab)가
// 대표 몇 개를 보여주고, 여기가 "그 그룹 안에 뭐가 더 있는지"를 보여주는 자리다.
//
// 선택·중복제거 규칙은 lib/exerciseSections.ts (순수 함수, node --test 로 검증).
// 부위 어휘를 TS 에 복제하지 않는다 — 백엔드가 이미 접어 놓은 recommendedExercises
// 이름으로 그룹을 되짚는다.
//
// scaffold = Phase 12.5 CoachingTipDetailModal 패턴 (backdrop = pure View +
// 위 빈 영역만 Pressable tap=close, sheet useWindowDimensions height, ScrollView
// gesture 함정 회피). theme 토큰만 — 하드코딩 금지, 라이트 테마.

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
import {
  CORRECTIVE_SECTIONS,
  exerciseKindLabel,
  type CorrectiveSection,
} from '../data/correctiveExercises';
import { buildExerciseSections, countExerciseRows } from '../lib/exerciseSections';
import type { RecommendedExercise } from '../types/analysis';

interface Props {
  visible: boolean;
  onClose: () => void;
  // 이 분석의 result.recommendedExercises (백엔드 exercise_map 산출).
  exercises: readonly RecommendedExercise[];
  // 분석 당시 bodyProfile.painAreas snapshot (없으면 빈 배열).
  painAreas: readonly string[];
}

export function RecommendedExerciseModal({
  visible,
  onClose,
  exercises,
  painAreas,
}: Props) {
  const { height: winH } = useWindowDimensions();
  const sheetHeight = Math.round(winH * 0.88);
  const sections = React.useMemo(
    () =>
      buildExerciseSections(CORRECTIVE_SECTIONS, {
        exerciseNames: exercises.map((e) => e.name),
        painAreas,
      }),
    [exercises, painAreas],
  );
  const rowCount = countExerciseRows(sections);

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.backdrop}>
        <Pressable style={styles.backdropTop} onPress={onClose} />
        <View style={[styles.sheet, { height: sheetHeight }]}>
          <View style={styles.handle} />
          <View style={styles.titleRow}>
            <Text style={styles.title} numberOfLines={2}>
              {rowCount > 0 ? '이 분석의 보완 운동' : '보완 운동'}
            </Text>
            <Pressable
              onPress={onClose}
              accessibilityRole="button"
              accessibilityLabel="닫기"
              hitSlop={10}
              style={styles.closeBtn}
            >
              <Text style={styles.closeText}>✕</Text>
            </Pressable>
          </View>

          <ScrollView
            style={styles.scroll}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            {sections.length > 0 ? (
              <>
                <Text style={styles.intro}>
                  이번 분석에서 짚인 부위의 보완 운동입니다. 통증이 있으면 회피
                  안내를 먼저 확인하세요.
                </Text>
                {sections.map((section) => (
                  <SectionBlock
                    key={`${section.kind}-${section.key}`}
                    section={section}
                  />
                ))}
              </>
            ) : (
              /* 화살표만 있고 아무것도 없는 화면은 만들지 않는다 — 왜 비었는지
                 말한다. 감점이 없으면 처방할 것도 없다는 게 정직한 상태다. */
              <View style={styles.emptyBox}>
                <Text style={styles.emptyTitle}>
                  이번 분석에서 짚인 보완 부위가 없어요.
                </Text>
                <Text style={styles.emptyBody}>
                  자세가 기준 범위 안에 있었거나, 판정할 수 있는 구간이 부족했어요.
                  다른 각도에서 다시 찍어 분석하면 더 구체적으로 짚어 드릴 수 있어요.
                </Text>
              </View>
            )}
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

function SectionBlock({ section }: { section: CorrectiveSection }) {
  return (
    <View style={styles.sectionBlock}>
      <Text style={styles.sectionHead}>{section.title}</Text>
      {section.note ? (
        <View style={styles.avoidBox}>
          <Text style={styles.avoidLabel}>회피</Text>
          <Text style={styles.avoidBody}>{section.note}</Text>
        </View>
      ) : null}
      {section.exercises.map((ex, idx) => {
        // 성격 표시 (quick-260910-vwh) — belle "스트레칭 뿐만 아니라 근력을 키우는
        // 헬스도 있을거고". 옛 doc 은 kind 가 없어 null → 칩을 그리지 않는다.
        // 표시일 뿐이며 선택/개수에는 관여하지 않는다.
        const kindLabel = exerciseKindLabel(ex.kind);
        return (
          <View key={`${ex.name}-${idx}`} style={styles.causeCard}>
            <View style={styles.exerciseHead}>
              <Text style={styles.exerciseName}>{ex.name}</Text>
              {kindLabel ? (
                <View style={styles.kindChip}>
                  <Text style={styles.kindChipText}>{kindLabel}</Text>
                </View>
              ) : null}
            </View>
            <Text style={styles.exerciseSets}>{ex.setsReps}</Text>
            <Text style={styles.exercisePurpose}>{ex.purpose}</Text>
          </View>
        );
      })}
    </View>
  );
}

// 성격 칩 높이 — 알약 모양을 만들 기준값 (결과 화면 칩 규칙 정합).
const KIND_CHIP_H = 18;

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  backdropTop: { flex: 1 },
  sheet: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingTop: 12,
    paddingBottom: 32,
    paddingHorizontal: 20,
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: colors.divider,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 16,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
    gap: 12,
  },
  title: {
    flex: 1,
    fontSize: 18,
    fontWeight: '700',
    color: colors.textPrimary,
    lineHeight: 24,
  },
  closeBtn: { padding: 4 },
  closeText: { fontSize: 20, color: colors.textSecondary },
  scroll: { flex: 1 },
  scrollContent: { paddingBottom: 16 },
  intro: {
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 19,
    marginBottom: 18,
  },
  emptyBox: { paddingVertical: 24 },
  emptyTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.textPrimary,
    lineHeight: 22,
    marginBottom: 8,
  },
  emptyBody: { fontSize: 13, color: colors.textSecondary, lineHeight: 20 },
  sectionBlock: { marginBottom: 18 },
  sectionHead: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: 8,
  },
  avoidBox: {
    backgroundColor: '#FFF8E7',
    borderWidth: 1,
    borderColor: '#F5C94C',
    borderRadius: 8,
    padding: 10,
    marginBottom: 10,
  },
  avoidLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#A06A00',
    marginBottom: 4,
  },
  avoidBody: { fontSize: 13, color: '#5C3A00', lineHeight: 19 },
  causeCard: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: 14,
    marginBottom: 10,
  },
  exerciseHead: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 4,
  },
  exerciseName: {
    flexShrink: 1,
    fontSize: 14,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  // 성격 칩 — 알약 모양(다른 결과 화면 칩과 같은 규칙: borderRadius = 높이/2).
  // 이름을 밀어내지 않게 flexShrink 는 이름 쪽에 준다.
  kindChip: {
    height: KIND_CHIP_H,
    paddingHorizontal: 7,
    borderRadius: KIND_CHIP_H / 2,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.resultChipBg,
  },
  // resultChipBg(#FCEFED) 위 resultChipMoreText 는 4.52:1 — 10pt 글자 AA 통과 토큰.
  kindChipText: {
    fontSize: 10,
    fontWeight: '700',
    color: colors.resultChipMoreText,
  },
  exerciseSets: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.brand,
    marginBottom: 6,
  },
  exercisePurpose: { fontSize: 13, color: colors.textPrimary, lineHeight: 19 },
  cta: {
    marginTop: 16,
    height: 50,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    justifyContent: 'center',
    alignItems: 'center',
  },
  ctaPressed: { opacity: 0.85 },
  ctaText: { fontSize: 16, fontWeight: '700', color: '#FFFFFF' },
});
