// 감점 record 드릴다운 시트 (quick-260705-r6v) — belle 실기기 4차 피드백 + 해외
// 사례(Frame.io 챕터 점프/HomeCourt 드릴다운) 수렴 설계.
//
// 메인 화면의 '문제 부위 확대 비교' 섹션을 없애고, 점수 계산 내역 행/전체화면
// 여백 범례/(세로 카드) 번호 점을 탭하면 이 시트가 열린다. 구 확대 비교 컴포넌트의
// 확대 이미지 자산을 이 시트로 이식했다(섹션 → 드릴다운). 재생 중 화면은 점만,
// 설명은 드릴다운으로 옮기는 UX (Tempo "폼 피드백 상시 노출 demoralizing" 계열).
//
// 콘텐츠 (위→아래): 원문자 번호 + 기준 라벨 헤더 → [내 확대사진 | 정은지 확대사진]
// (zoom 있을 때만) → 측정 수치 1줄(formatDeductionRecord, 신규 수치 조립 0) →
// 행동구 1줄(있을 때). zoom 미매칭이면 사진 없이 수치·문구만 (graceful).
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
  circledNumberKo,
  criterionLabelKo,
  formatDeductionRecord,
} from '../lib/deductionLabels';
import { colors, radius, spacing, typography } from '../theme';
import type { DeductionRecord, FaultZoomComparison } from '../types/analysis';

interface Props {
  visible: boolean;
  onClose: () => void;
  record: DeductionRecord | null;
  recordNumber: number | null;
  actionPhrase: string | null;
  zoom: FaultZoomComparison | null;
  // Phase 27 D-06 — zoom 사후 도착 대기 중(result.faultZoomStatus='pending')이고
  // 아직 시간 상한 이내면 true. 확대사진 자리에 로딩 placeholder 를 렌더한다.
  // zoom 이 실제 도착하면 result.tsx 가 zoom(!=null)+zoomPending(false)로 전환.
  zoomPending?: boolean;
  // Phase 28 D-04 — DTW 기준 프레임 대응 실패(refMatch='failed', 28-05 공급). true 면
  // 확대 이미지 아래에 "전신 화면으로 보여드려요" 정직 캡션을 렌더한다. 'dtw'/legacy
  // (부재)=false → 캡션 없음. 판정은 호출측(result.tsx)이 zoom.refMatch 로 계산.
  refMatchFailed?: boolean;
  // 우측 비교 대상 라벨 — Mode1='정은지 선수', Mode3='지난 분석'.
  rightLabel: string;
}

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

  const sheetHeight = Math.round(winH * 0.7);
  const row = formatDeductionRecord(record);
  // 합성 이미지 = [내 영상 | 기준] 정사각 2개 → 가로:세로 ≈ 2:1.
  const imgW = width - spacing.screenX * 2;
  const imgH = imgW / 2;

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
                {/* Phase 28 D-04 — DTW 대응 실패 시 ref 는 전신 폴백(28-05)이라 어느
                    순간인지 단정하지 않고 정직 고지. 'dtw'/legacy 면 캡션 없음. */}
                {refMatchFailed ? (
                  <Text style={styles.refMatchNote}>
                    같은 동작 순간을 찾지 못해 전신 화면으로 보여드려요
                  </Text>
                ) : null}
              </>
            ) : zoomPending ? (
              // Phase 27 D-06 — zoom 사후 도착 대기. 점수/내역은 이미 도착했고
              // 확대 이미지만 렌더 중이라 카드 자리에 로딩 placeholder 를 둔다.
              // 도착(onSnapshot) 시 자동으로 위 이미지 분기로 전환된다. 이미지 카드와
              // 동일 컨테이너 스타일 재사용 + ActivityIndicator + 안내 카피(토큰만).
              <View
                style={[styles.imageWrap, styles.imagePending, { height: imgH }]}
                accessibilityRole="progressbar"
                accessibilityLabel="확대 비교 이미지를 준비하고 있어요"
              >
                <ActivityIndicator color={colors.brand} />
                <Text style={styles.pendingText}>확대 비교 이미지를 준비하고 있어요</Text>
              </View>
            ) : null}

            {/* 측정 수치 1줄 — formatDeductionRecord 재사용 (신규 수치 조립 0). */}
            <View style={styles.metricRow}>
              <Text style={styles.metricDetail}>{row.detailText}</Text>
              <Text style={styles.metricPoints}>{row.pointsText}</Text>
            </View>

            {/* 행동구 1줄 — 있을 때만 (예: '다리 더 벌리기'). */}
            {actionPhrase ? (
              <View style={styles.actionRow}>
                <Text style={styles.actionLabel}>이렇게 교정해 보세요</Text>
                <Text style={styles.actionPhrase}>{actionPhrase}</Text>
              </View>
            ) : null}
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
  // Phase 28 D-04 — refMatch='failed' 전신 폴백 정직 캡션 (pendingText 패턴 차용, 토큰만).
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
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
  },
  metricDetail: {
    ...typography.body,
    color: colors.textPrimary,
    flex: 1,
    lineHeight: 21,
  },
  metricPoints: { ...typography.listTitle, color: colors.brand },
  actionRow: {
    backgroundColor: colors.brandTint,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
    gap: 4,
  },
  actionLabel: { ...typography.captionSmall, color: colors.textSecondary },
  actionPhrase: { ...typography.boxLabel, color: colors.textPrimary },
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
