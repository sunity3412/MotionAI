// Phase 13 (Plan 13-A, PERS-03) — "다른 운동 보기" 전체 보완 운동 라이브러리 모달.
//
// HIGH-1 (13-REVIEW-FIXES.md): 본 모달은 result.recommendedExercises(3~5 개인화
// subset)가 아니라 app/src/data/correctiveExercises.ts 의 전체 라이브러리를 browse
// 한다 (옵션 a). 결함 그룹 + 통증부위 그룹별 운동 카드 목록.
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
  type CorrectiveSection,
} from '../data/correctiveExercises';

interface Props {
  visible: boolean;
  onClose: () => void;
}

export function RecommendedExerciseModal({ visible, onClose }: Props) {
  const { height: winH } = useWindowDimensions();
  const sheetHeight = Math.round(winH * 0.88);

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
              보완 운동 라이브러리
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
            <Text style={styles.intro}>
              결함·통증부위별 보완 운동 전체 목록입니다. 통증이 있으면 회피 안내를
              먼저 확인하세요.
            </Text>
            {CORRECTIVE_SECTIONS.map((section) => (
              <SectionBlock key={`${section.kind}-${section.key}`} section={section} />
            ))}
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
      {section.exercises.map((ex, idx) => (
        <View key={`${ex.name}-${idx}`} style={styles.causeCard}>
          <Text style={styles.exerciseName}>{ex.name}</Text>
          <Text style={styles.exerciseSets}>{ex.setsReps}</Text>
          <Text style={styles.exercisePurpose}>{ex.purpose}</Text>
        </View>
      ))}
    </View>
  );
}

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
  exerciseName: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textPrimary,
    marginBottom: 4,
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
