// 감점 record 드릴다운 시트 (quick-260705-r6v → 32-10 D-15 3단화 + gate ⑤ 참조 원형).
//
// 32-10(D-15): 메인 감점 카드와 같은 3단 원칙(상태→왜→행동)을 시트 상단에 얹고, 그
// 아래 기존 투명 감점 내역(측정값·기준·편차·규칙)을 "이 원인은 어떻게 측정됐나" 회색
// 근거 박스로 계층화한다 — 수치는 이 박스에만(D-09). 수치 삭제 금지(계층화만,
// [[scoring-must-be-transparent-deduction-tally]] 불변).
//
// gate ⑤ 참조 원형(belle Figma 결함 상세 시트): 수치 0 문구 헤드라인 + 결함 확대쌍
// 사진 + 회색 근거 박스(수치 여기만) + 확인하기 불릿 + 강사 연결 줄 + AI 추정 고지 박스.
// 폰트 피드백(GATE-DECISIONS): 이전 측정 문구 "상단 글자 잘림"(fontSize 25 / lineHeight
// 21 불일치)을 E2 토큰(bodySm 19/25 등, lineHeight = fontSize×1.3↑)로 교체해 방지.
//
// Props 는 무변경(result.tsx 배선은 32-11 — 이 플랜 무접촉). 신규 3단은 기존 record 의
// statusLine/whyLine/cueLine 옵셔널 필드를 읽고, 부재(legacy doc)면 기존 렌더 유지.
// 토큰만 사용 (CLAUDE.md §4). 이모지 0. 라이트 전용.

import React from 'react';
import {
  ActivityIndicator,
  Image,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';

import {
  ANGLE_VS_REFERENCE_PREFIX,
  circledNumberKo,
  criterionLabelKo,
  formatDeductionRecord,
} from '../lib/deductionLabels';
import { terminologyPlain, type TerminologyTerm } from '../lib/terminologyMap';
import { colors, radius, spacing, typography } from '../theme';
import type { DeductionRecord, FaultZoomComparison } from '../types/analysis';

interface Props {
  visible: boolean;
  onClose: () => void;
  record: DeductionRecord | null;
  recordNumber: number | null;
  actionPhrase: string | null;
  zoom: FaultZoomComparison | null;
  // Phase 27 D-06 — zoom 사후 도착 대기 중이면 true. 확대사진 자리에 로딩 placeholder.
  zoomPending?: boolean;
  // Phase 28 D-04 — DTW 기준 프레임 대응 실패 시 true. 전신 폴백 정직 캡션.
  refMatchFailed?: boolean;
  // 우측 비교 대상 라벨 — Mode1='정은지 선수', Mode3='지난 분석'.
  rightLabel: string;
}

// criterion → 심사 언어 용어(terminologyMap) 매핑. 미등록 criterion 은 null(용어줄 생략).
function criterionTerm(criterion: string): TerminologyTerm | null {
  if (criterion === 'split_angle') return 'split';
  if (criterion === 'body_relative_reach') return 'reach';
  if (criterion === 'leg_extension' || criterion === 'arm_extension' || criterion === 'line') {
    return 'line';
  }
  if (criterion.startsWith(ANGLE_VS_REFERENCE_PREFIX)) return 'angle';
  return null;
}

// gate ⑤ 하단 고지 박스 카피 (belle Figma 원형).
const AI_DISCLAIMER =
  'AI가 추정한 가능성이에요. 강사 수업과 함께 확인하면 가장 정확한 피드백을 받을 수 있어요.';
// gate ⑤ 강사 연결 줄.
const COACH_CONNECT = '강사가 함께 보면 더 구체적인 피드백을 받을 수 있어요';
const CHECK_BULLET = '확인하기 — 거울을 보며 동작을 직접 재현해 보세요';
const EVIDENCE_TITLE = '이 원인은 어떻게 측정됐나';

export function DeductionDetailSheet({
  visible,
  onClose,
  record,
  recordNumber,
  actionPhrase,
  zoom,
  zoomPending = false,
  refMatchFailed = false,
  rightLabel,
}: Props) {
  const { width, height: winH } = useWindowDimensions();
  if (!record) return null;

  const sheetHeight = Math.round(winH * 0.78);
  const row = formatDeductionRecord(record);
  // 합성 이미지 = [내 영상 | 기준] 정사각 2개 → 가로:세로 ≈ 2:1.
  const imgW = width - spacing.screenX * 2;
  const imgH = imgW / 2;

  // 3단 문구 (D-15) — statusLine/whyLine 상단, cueLine(부재 시 actionPhrase 폴백)은 행동 박스.
  const has3Dan = !!(record.statusLine || record.whyLine || record.cueLine);
  const effectiveCue = record.cueLine ?? actionPhrase ?? null;
  // 심사 언어 용어줄 (terminologyMap 적용 — "이 지표가 무엇인지").
  const term = criterionTerm(record.criterion);
  const termText = term ? terminologyPlain(term) : null;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      {/* RN bottom sheet 정석: backdrop 빈 영역만 Pressable, sheet 는 pure View. */}
      <View style={styles.backdrop}>
        <Pressable style={styles.backdropTop} onPress={onClose} />
        <View style={[styles.sheet, { height: sheetHeight }]}>
          <View style={styles.handle} />
          <View style={styles.titleRow}>
            <Text style={styles.title}>
              {recordNumber != null ? (
                <Text style={styles.titleNumber}>
                  {`${circledNumberKo(recordNumber)} `}
                </Text>
              ) : null}
              {criterionLabelKo(record.criterion)}
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
            {/* 3단 상단 — 상태(몸 말 헤드라인, 수치 0) → 왜(감점 이유). 부재 시 생략. */}
            {has3Dan ? (
              <View style={styles.threeStep}>
                {record.statusLine ? (
                  <Text style={styles.stepStatus}>{record.statusLine}</Text>
                ) : null}
                {record.whyLine ? (
                  <Text style={styles.stepWhy}>{record.whyLine}</Text>
                ) : null}
              </View>
            ) : null}

            {/* 확대 이미지 (구 확대 비교 컴포넌트 자산 이식) — zoom 있을 때만.
                합성 PNG 1장 + 좌 '내 영상'/우 rightLabel halfLabel 오버레이. */}
            {zoom ? (
              <>
                <View style={[styles.imageWrap, { height: imgH }]}>
                  <Image
                    source={{ uri: zoom.imageUrl }}
                    style={styles.image}
                    resizeMode="contain"
                    accessibilityLabel={`${criterionLabelKo(record.criterion)} 확대 비교 이미지`}
                  />
                  <View style={[styles.halfLabel, styles.halfLabelLeft]}>
                    <Text style={styles.halfLabelText}>내 영상</Text>
                  </View>
                  <View style={[styles.halfLabel, styles.halfLabelRight]}>
                    <Text style={styles.halfLabelText}>{rightLabel}</Text>
                  </View>
                </View>
                {/* Phase 28 D-04 — DTW 대응 실패 시 ref 는 전신 폴백이라 정직 고지. */}
                {refMatchFailed ? (
                  <Text style={styles.refMatchNote}>
                    같은 동작 순간을 찾지 못해 전신 화면으로 보여드려요
                  </Text>
                ) : null}
              </>
            ) : zoomPending ? (
              // Phase 27 D-06 — zoom 사후 도착 대기. 확대 이미지만 렌더 중이라 로딩
              // placeholder. 도착(onSnapshot) 시 자동으로 위 이미지 분기로 전환된다.
              <View
                style={[styles.imageWrap, styles.imagePending, { height: imgH }]}
                accessibilityRole="progressbar"
                accessibilityLabel="확대 비교 이미지를 준비하고 있어요"
              >
                <ActivityIndicator color={colors.brand} />
                <Text style={styles.pendingText}>확대 비교 이미지를 준비하고 있어요</Text>
              </View>
            ) : null}

            {/* 행동(외부 큐) — cueLine 우선, 부재 시 actionPhrase 폴백. 있을 때만. */}
            {effectiveCue ? (
              <View style={styles.actionRow}>
                <Text style={styles.actionLabel}>이렇게 교정해 보세요</Text>
                <Text style={styles.actionPhrase}>{effectiveCue}</Text>
              </View>
            ) : null}

            {/* 확인하기 불릿 (gate ⑤) + 심사 언어 용어줄(terminologyMap). */}
            <View style={styles.bullets}>
              {termText ? (
                <Text style={styles.bullet}>{`이 지표 — ${termText}`}</Text>
              ) : null}
              <Text style={styles.bullet}>{CHECK_BULLET}</Text>
            </View>

            {/* "이 원인은 어떻게 측정됐나" 회색 근거 박스 — 수치는 여기에만(D-09).
                기존 투명 감점 내역(측정값·기준·편차·규칙) 그대로 유지(삭제 0). */}
            <View style={styles.evidenceBox}>
              <Text style={styles.evidenceTitle}>{EVIDENCE_TITLE}</Text>
              <View style={styles.metricRow}>
                <Text style={styles.metricDetail}>{row.detailText}</Text>
                <Text style={styles.metricPoints}>{row.pointsText}</Text>
              </View>
            </View>

            {/* 강사 연결 줄 (gate ⑤). */}
            <Text style={styles.coachConnect}>{COACH_CONNECT}</Text>

            {/* AI 추정 고지 박스 (gate ⑤ 하단). */}
            <View style={styles.aiNoteBox}>
              <Text style={styles.aiNoteText}>{AI_DISCLAIMER}</Text>
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
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  backdropTop: { flex: 1 },
  sheet: {
    backgroundColor: colors.cardBg,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingTop: 12,
    paddingBottom: 32,
    paddingHorizontal: spacing.screenX,
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
    alignItems: 'center',
    marginBottom: 12,
  },
  title: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
    flexShrink: 1,
  },
  // 원문자 번호 — 영상 빨간 점(brand)과 같은 색으로 시각 연결.
  titleNumber: { ...typography.sectionTitle, color: colors.brand },
  closeBtn: { padding: 4 },
  closeText: { ...typography.sectionTitle, color: colors.textSecondary },
  scroll: { flex: 1 },
  scrollContent: { paddingBottom: 16, gap: 14 },
  // 3단 상단 블록 (D-15).
  threeStep: { gap: 6 },
  stepStatus: {
    ...typography.bodyLg, // 24/700 카드 헤드라인(몸 말/상태) — E2 토큰, 줄겹침 방지
    color: colors.textPrimary,
  },
  stepWhy: {
    ...typography.bodySm, // 19/400 왜·보조 본문 (lineHeight 25 — 잘림 방지)
    color: colors.textMid,
  },
  // 구 확대 비교 컴포넌트 이미지 pane 이식 — 2:1 합성 이미지.
  imageWrap: {
    width: '100%',
    borderRadius: radius.listItem,
    overflow: 'hidden',
    backgroundColor: colors.divider,
  },
  image: { width: '100%', height: '100%' },
  // Phase 27 D-06 — zoom 사후 도착 대기 placeholder (이미지 카드와 동일 컨테이너).
  imagePending: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  pendingText: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  // Phase 28 D-04 — refMatch='failed' 전신 폴백 정직 캡션.
  refMatchNote: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  halfLabel: {
    position: 'absolute',
    top: 8,
    backgroundColor: colors.brandOverlay,
    borderRadius: radius.listItem,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  halfLabelLeft: { left: 8 },
  halfLabelRight: { right: 8 },
  halfLabelText: { ...typography.caption, color: colors.textWhite, fontWeight: '700' },
  // 행동(외부 큐) 박스 — 브랜드 틴트 강조.
  actionRow: {
    backgroundColor: colors.brandTint,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
    gap: 4,
  },
  actionLabel: { ...typography.badge, fontWeight: '400', color: colors.textSecondary },
  actionPhrase: { ...typography.bodyMdBold, color: colors.textPrimary }, // 21/700 행동 큐
  // 확인하기 불릿 + 용어줄.
  bullets: { gap: 6 },
  bullet: {
    ...typography.bodySm, // 19/400 (lineHeight 25 — 잘림 방지)
    color: colors.textMid,
  },
  // "이 원인은 어떻게 측정됐나" 회색 근거 박스 — 수치는 여기에만(D-09).
  evidenceBox: {
    backgroundColor: colors.softBg,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
    gap: 8,
  },
  evidenceTitle: {
    ...typography.badge, // 17/600 — 소형 근거 박스 제목
    color: colors.textSecondary,
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
  },
  // 측정 문구 — bodySm(19/25) 로 교체해 상단 글자 잘림(구 body 25/lineHeight 21) 해소.
  metricDetail: {
    ...typography.bodySm,
    color: colors.textPrimary,
    flex: 1,
  },
  metricPoints: { ...typography.bodyMdBold, color: colors.brand },
  // 강사 연결 줄.
  coachConnect: {
    ...typography.bodySm,
    color: colors.textMid,
  },
  // AI 추정 고지 박스.
  aiNoteBox: {
    backgroundColor: colors.softBg,
    borderRadius: radius.listItem,
    padding: 12,
  },
  aiNoteText: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
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
  ctaText: { ...typography.button, color: colors.textWhite },
});
