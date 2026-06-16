// Phase 12.5 T9 — 코칭 팁 "자세히 보기" 모달 (LLM 동적).
//
// belle 의도 (2026-06-07): 코칭 팁 = 행동 지시 + 다중 원인 후보 + 각 case 처방 +
// 부상 경고 + 코치 권고. 사용자가 정확한 원인 모르므로 "이런 경우 어깨가 내려갈
// 수 있어요" 식으로 가능성 제시 → 학생이 자기 케이스 추정 가능.
//
// 데이터 source: backend coach_writer (Cerebras gpt-oss-120b) → JSON 출력 →
// CoachingTip.detail2 = CoachingTipDetail. graceful: detail2 없으면 모달 진입 X.

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
import type { CoachingTip, CoachingTipDetail } from '../types/analysis';

interface Props {
  visible: boolean;
  tip: CoachingTip | null;
  onClose: () => void;
}

export function CoachingTipDetailModal({ visible, tip, onClose }: Props) {
  // useWindowDimensions: sheet 에 명시 height 부여해야 ScrollView 가 그 안에서
  // 정상 동작. maxHeight 만 두면 flexShrink:1 일 때 layout 계산이 collapse.
  const { height: winH } = useWindowDimensions();
  if (!tip) return null;
  const detail2 = tip.detail2;
  const sheetHeight = Math.round(winH * 0.88);

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      {/* RN bottom sheet 정석 패턴: backdrop 위 빈 영역만 Pressable (tap=close),
          sheet 자체는 pure View — touch responder 가 ScrollView gesture 를
          가로채지 않게 함. Pressable + onStartShouldSetResponder 는 sheet 일부
          영역에서만 gesture 인식되는 부작용 (이전 함정). */}
      <View style={styles.backdrop}>
        <Pressable style={styles.backdropTop} onPress={onClose} />
        <View style={[styles.sheet, { height: sheetHeight }]}>
          <View style={styles.handle} />
          <View style={styles.titleRow}>
            <Text style={styles.title} numberOfLines={2}>
              {tip.title}
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
            {/* 카드 본문 한 줄 재인용 (모달 상단에 컨텍스트 박제) */}
            <Text style={styles.intro}>{tip.detail}</Text>

            {detail2 ? (
              <CausesSection detail2={detail2} />
            ) : (
              <Text style={styles.noDetailNote}>
                자세한 원인 분석은 다음 분석에서 제공될 예정입니다. 강사와
                함께 영상을 보며 확인해 보세요.
              </Text>
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

// Phase 13-C (2026-06-16, [[section-dual-coach-report]]) — 섹션형 듀얼 coach 렌더.
// 자세히 모달이 4개 "기능 라벨" 섹션을 세로 스택으로 순서대로 렌더한다:
//   원인 → 교정 처방 → 부상 위험(있을 때만) → 강사 확인.
// 라벨은 기능 라벨만 — AI/벤더명(Gemini/Cerebras) 텍스트 0 (13-C locked).
// 탭/아코디언 기각 — 원인+처방 동시 비교가 핵심 (13-C locked).
// 색/radius/spacing 은 theme 토큰만. 화면 하단 보완운동 카드(13-A)는 별도 유지.
function CausesSection({ detail2 }: { detail2: CoachingTipDetail }) {
  const fixes = detail2.causes
    .map((c) => c.fix)
    .filter((f) => typeof f === 'string' && f.trim().length > 0);

  return (
    <>
      {/* 섹션 1 — 원인 (causes title + explanation) */}
      <Text style={styles.sectionHead}>원인</Text>
      <Text style={styles.sectionSub}>
        정확한 원인은 케이스마다 다르므로 몇 가지 가능성을 제시합니다.
      </Text>
      {detail2.causes.map((c, idx) => (
        <View key={idx} style={styles.causeCard}>
          <View style={styles.causeHead}>
            <View style={styles.causeNum}>
              <Text style={styles.causeNumText}>{idx + 1}</Text>
            </View>
            <Text style={styles.causeTitle}>{c.title}</Text>
          </View>
          <Text style={styles.causeBody}>{c.explanation}</Text>
        </View>
      ))}

      {/* 섹션 2 — 교정 처방 (각 cause.fix 모음, 13-A 보완운동 카드와 자연 연결) */}
      {fixes.length > 0 ? (
        <View style={styles.fixSection}>
          <Text style={styles.sectionHead}>교정 처방</Text>
          <Text style={styles.sectionSub}>
            추정 원인별로 이렇게 연습해 보세요.
          </Text>
          {fixes.map((fix, idx) => (
            <View key={idx} style={styles.fixBox}>
              <Text style={styles.fixLabel}>{idx + 1}번 원인 처방</Text>
              <Text style={styles.fixBody}>{fix}</Text>
            </View>
          ))}
        </View>
      ) : null}

      {/* 섹션 3 — 부상 위험 (injuryRisk 있을 때만 — 없으면 섹션 자체 생략) */}
      {detail2.injuryRisk ? (
        <View style={styles.riskSection}>
          <Text style={styles.sectionHead}>부상 위험</Text>
          <View style={styles.injuryCard}>
            <Text style={styles.injuryLabel}>주의</Text>
            <Text style={styles.injuryBody}>{detail2.injuryRisk}</Text>
          </View>
        </View>
      ) : null}

      {/* 섹션 4 — 강사 확인 (coachNote) */}
      <View style={styles.coachSection}>
        <Text style={styles.sectionHead}>강사 확인</Text>
        <Text style={styles.coachNote}>{detail2.coachNote}</Text>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  // backdrop 위 빈 영역 = 닫기 trigger. sheet 자체는 responder X → ScrollView 정상 동작.
  backdropTop: { flex: 1 },
  sheet: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingTop: 12,
    paddingBottom: 32,
    paddingHorizontal: 20,
    // height 는 컴포넌트에서 useWindowDimensions 로 동적 주입 (88%)
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
  // ScrollView: sheet 가 명시 height 가지므로 flex:1 로 남은 공간 채움 →
  // content 초과 시 정상 스크롤. (sheet 가 maxHeight 만이면 flex:1 = collapse.)
  scroll: { flex: 1 },
  scrollContent: { paddingBottom: 16 },
  intro: {
    fontSize: 14,
    color: colors.textPrimary,
    lineHeight: 21,
    marginBottom: 18,
  },
  noDetailNote: {
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 19,
    paddingVertical: 12,
  },
  sectionHead: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: 4,
  },
  sectionSub: {
    fontSize: 12,
    color: colors.textSecondary,
    lineHeight: 17,
    marginBottom: 14,
  },
  // Phase 13-C — 4 섹션 세로 스택 간격 (원인 → 교정 처방 → 부상 위험 → 강사 확인).
  fixSection: { marginTop: 8 },
  riskSection: { marginTop: 8 },
  coachSection: { marginTop: 8 },
  causeCard: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: colors.divider,
    borderRadius: radius.card,
    padding: 14,
    marginBottom: 10,
  },
  causeHead: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 8,
  },
  causeNum: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.brand,
    justifyContent: 'center',
    alignItems: 'center',
  },
  causeNumText: { fontSize: 11, fontWeight: '700', color: '#FFFFFF' },
  causeTitle: {
    flex: 1,
    fontSize: 14,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  causeBody: {
    fontSize: 13,
    color: colors.textPrimary,
    lineHeight: 19,
    marginBottom: 10,
  },
  fixBox: {
    backgroundColor: '#F7F7F7',
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
  },
  fixLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.brand,
    marginBottom: 4,
  },
  fixBody: { fontSize: 13, color: colors.textPrimary, lineHeight: 19 },
  injuryCard: {
    backgroundColor: '#FFF8E7',
    borderWidth: 1,
    borderColor: '#F5C94C',
    borderRadius: radius.card,
    padding: 14,
  },
  injuryLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#A06A00',
    marginBottom: 4,
  },
  injuryBody: { fontSize: 13, color: '#5C3A00', lineHeight: 19 },
  coachNote: {
    fontSize: 12,
    color: colors.textSecondary,
    lineHeight: 18,
    marginTop: 8,
  },
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
