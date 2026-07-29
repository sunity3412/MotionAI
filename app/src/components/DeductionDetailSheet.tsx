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
  // IN-01 (quick-260724-q6b) — 역립 저신뢰 시 true. 크롭은 유지하되 "예상 부위"
  // 배지를 얹어 확정 결함이 아니라 추정 부위임을 표시 (크롭·수치·비교 삭제 0).
  estimatedArea?: boolean;
  // 우측 비교 대상 라벨 — Mode1='정은지 선수', Mode3='지난 분석'.
  rightLabel: string;
  // 33-14 (A-7, D-15) — 결함 일러스트 슬롯. 매핑(결함→일러스트)은 caller(result.tsx)
  // 소유, 시트는 자리만 제공. 승인 목업 ② "확대 크롭 + 감점근거 글 + 일러스트 슬롯".
  // 부재/미검증 = 렌더 0 (DefectIllustration 이 자체 hidden — 시트는 관여하지 않음).
  illustrationSlot?: React.ReactNode;
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
// 33-15 (D-16) — 대시 나열("확인하기 — …") 문장화.
const CHECK_BULLET = '거울을 보며 동작을 직접 재현해서 확인해 보세요';
const EVIDENCE_TITLE = '이 원인은 어떻게 측정됐나';

// 33-15 (D-16) — 대시 나열("이 지표 — …") 문장화용 목적격 조사(을/를) 선택.
// termText 값이 받침 유무로 갈려("힘"→을, "크기"→를) 고정 조사는 오표기 유발
// (ReferenceCornerSection 조사 함정 주석 선례). 마지막 글자의 한글 종성 유무로
// 판정, 비한글은 '를' 폴백 (terminologyPlain 미등록 원문 노출 관례).
function objectJosa(text: string): string {
  const last = text.charCodeAt(text.length - 1);
  if (last >= 0xac00 && last <= 0xd7a3) {
    return (last - 0xac00) % 28 > 0 ? '을' : '를';
  }
  return '를';
}

// 33-15 (A-6 이관, 6R 확정 문형) — 초 표기 라벨: 본문 + 괄호 보조설명(브랜드 컬러).
// 사진 속 초 = 백엔드 _stamp_time(학생 상시 · 회전류 기준측 stamp_ref, 33-12) 베이크.
// 라벨은 criterion 보유 카드(33-12+ 파이프라인 산출 = 초 베이크 보장)에서만 렌더 —
// 구 PNG(초 미베이크)에 없는 배지를 지칭하는 거짓 라벨 방지 (데이터 키잉 게이트).
const TIME_STAMP_NOTE_MAIN = '사진 속 초는 영상에서 이 순간을 찾는 위치예요';
const TIME_STAMP_NOTE_PAREN = '(감점 부분)';
// IN-01 (quick-260724-q6b) — 역립 저신뢰 시 크롭 위 "예상 부위" 배지 카피 (시트가
// 실제 라벨 소유). 확정 결함 아님 — advisoryOrange 톤(표시 전용).
const ESTIMATED_AREA_LABEL = '예상 부위';
// IN-01 — 저신뢰 시 관절을 단정하지 않는 시트 제목(정확한 관절 assert 금지).
const ESTIMATED_AREA_TITLE = '예상 부위 (참고)';
// IN-01 — 저신뢰 시 특정 관절에 −X 감점을 귀속할 수 없어 수치 대신 노출하는 안내.
// 크롭·배지는 유지하되 거짓 정밀도(관절별 감점 숫자)만 제거.
const ESTIMATED_AREA_POINTS_NOTE =
  '이 부위는 추정이라 관절별 감점 수치는 종합 점수로만 반영돼요';

export function DeductionDetailSheet({
  visible,
  onClose,
  record,
  recordNumber,
  actionPhrase,
  zoom,
  zoomPending = false,
  refMatchFailed = false,
  estimatedArea = false,
  rightLabel,
  illustrationSlot,
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
              {/* IN-01 — 저신뢰 시 원문자 번호 억제(오버레이 마커 번호도 억제돼
                  대응 점이 없다) + 관절 단정 대신 "예상 부위" 제목. */}
              {recordNumber != null && !estimatedArea ? (
                <Text style={styles.titleNumber}>
                  {`${circledNumberKo(recordNumber)} `}
                </Text>
              ) : null}
              {estimatedArea
                ? ESTIMATED_AREA_TITLE
                : criterionLabelKo(record.criterion)}
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
                {/* IN-01 (quick-260724-q6b) — 역립 저신뢰 시 크롭 위 "예상 부위"
                    배지 (확정 결함 아님, advisoryOrange 톤). 크롭·수치·비교는 유지. */}
                {estimatedArea ? (
                  <View style={styles.estimatedBadge}>
                    <Text style={styles.estimatedBadgeText}>
                      {ESTIMATED_AREA_LABEL}
                    </Text>
                  </View>
                ) : null}
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
                {/* 33-15 (A-6 이관, 6R 확정 문형) — 초 표기 라벨. 괄호 보조설명 =
                    브랜드 컬러 (목업 .pnote 정합). IN-01 저신뢰(estimatedArea)는
                    확정 결함이 아니라 "감점 부분" 단정 라벨 미표시. criterion 부재
                    (legacy 크롭 = 초 미베이크 가능)도 미표시 — 거짓 지칭 방지. */}
                {zoom.criterion && !estimatedArea ? (
                  <Text style={styles.timeStampNote}>
                    {`${TIME_STAMP_NOTE_MAIN} `}
                    <Text style={styles.timeStampNoteParen}>
                      {TIME_STAMP_NOTE_PAREN}
                    </Text>
                  </Text>
                ) : null}
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

            {/* 33-14 (A-7) — 목표 자세 일러스트. 말 없이 뭘 하라는지 보여주는
                장치(D-05: 라벨 텍스트 없이 그림만). 미검증/mode3 = 슬롯 자체가
                null 을 렌더 (silent hidden). */}
            {illustrationSlot ?? null}

            {/* 확인하기 안내 (gate ⑤) + 심사 언어 용어줄(terminologyMap).
                33-15 (D-16) — 대시 나열을 문장화 (조사는 objectJosa 로 받침 판정). */}
            <View style={styles.bullets}>
              {termText ? (
                <Text style={styles.bullet}>
                  {`이 지표는 ${termText}${objectJosa(termText)} 봐요`}
                </Text>
              ) : null}
              <Text style={styles.bullet}>{CHECK_BULLET}</Text>
            </View>

            {/* "이 원인은 어떻게 측정됐나" 회색 근거 박스 — 수치는 여기에만(D-09).
                기존 투명 감점 내역(측정값·기준·편차·규칙) 그대로 유지(삭제 0). */}
            <View style={styles.evidenceBox}>
              <Text style={styles.evidenceTitle}>{EVIDENCE_TITLE}</Text>
              {/* IN-01 — 저신뢰 시 관절별 감점 수치(−X)를 특정 관절에 귀속할 수
                  없어 거짓 정밀도를 제거하고 안내로 대체. 크롭·배지는 유지. */}
              {estimatedArea ? (
                <Text style={styles.estimatedPointsNote}>
                  {ESTIMATED_AREA_POINTS_NOTE}
                </Text>
              ) : (
                <View style={styles.metricRow}>
                  <Text style={styles.metricDetail}>{row.detailText}</Text>
                  <Text style={styles.metricPoints}>{row.pointsText}</Text>
                </View>
              )}
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
  // 33-15 (A-6 이관) — 초 표기 라벨. 본문 = 보조 톤, 괄호 보조설명 = 브랜드 컬러
  // + bold (목업 .pnote 정합 — 6R 확정 문형).
  timeStampNote: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  timeStampNoteParen: {
    color: colors.brand,
    fontWeight: '700',
  },
  // IN-01 (quick-260724-q6b) — 역립 저신뢰 "예상 부위" 배지 (advisoryOrange 재사용,
  // 신규 색 금지). 크롭 이미지 위 칩.
  estimatedBadge: {
    alignSelf: 'flex-start',
    backgroundColor: colors.advisoryOrangeBg,
    borderRadius: radius.listItem,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  estimatedBadgeText: {
    ...typography.caption,
    color: colors.advisoryOrange,
    fontWeight: '700',
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
  // 33-15 (D-16) — 감점 수치 bodyMdBold(21) → metricNumber(17) 강등 (수치는 근거).
  metricPoints: { ...typography.metricNumber, color: colors.brand },
  // IN-01 (quick-260724-q6b) — 저신뢰 시 감점 수치 대신 노출하는 안내(거짓 정밀도
  // 제거). 근거 박스 내부라 textMid 본문 톤. 토큰만.
  estimatedPointsNote: {
    ...typography.bodySm,
    color: colors.textMid,
  },
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
