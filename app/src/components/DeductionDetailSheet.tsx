// 부위 상세 시트 (승인 목업 7R ② 구조 — quick-260730-py1, 33-G S6/S7).
//
// 종전 구조는 **record 단위**였다 (부위에 감점 2건이면 시트가 2개 열렸다). 승인
// 목업 ② 는 **부위 단위**다: 칩 → 크롭 1쌍 → paircap(좌우 실영상 초) → onecap →
// 결함 블록 N개(다리 = "고칠 것 1"·"고칠 것 2") → facing → 일러스트.
// belle 확인 ② 반려의 "무릎 피는 거 하나 어디 갔냐"(4R#2)가 이 구조의 이유다.
//
// 조판·카피 조립은 `lib/deductionSheet.ts buildRegionSheetView` 가 소유한다 (순수
// 함수, node --test 로 고정). 호출은 caller(result.tsx)가 하고 이 컴포넌트는 그
// 결과(`RegionSheetView`)를 **렌더만** 한다 — 조판 분기 사본 0.
//
// 승인 CSS → 앱 토큰 매핑 (M-14 — 목업 px 는 데스크톱 스케일, 앱은 토큰 우선.
// 색 실측값은 theme/colors.ts 에 출처와 함께 박제 — 여기 hex 리터럴 0):
//   .fault-head (15/800 brand on brand-tint + 하단 보더) → boxLabel + brandTint
//   .headline (bodyLg 800) → typography.bodyLg
//   .why (bodySm ink-2) → bodySm + textMid
//   .basis (연회색 배경 + line 보더, b=진한 잉크) → softBg + border + bold 세그먼트
//   .cue (bodyMd 800 brand on brand-tint radius 12) → bodyMdBold brand + brandTint
//   .methodline (틸 박스) → caption 스케일 본문 + infoTeal 토큰 3종
//   .numnote (12.5 ink-3) → caption + textSecondary
//   .paircap (12/800 회색 space-between) → caption 700 + textMid
//   .onecap (caption ink-2 center) → caption + textMid + center
//   .facing (틸 박스, bodySm) → bodySm + infoTeal 토큰 3종
// 신규 폰트 크기 리터럴 0 (CLAUDE.md §4). 이모지 0. 라이트 전용.
//
// 유지되는 승인 원형(gate ⑤ belle Figma, M-13): bullets(용어줄·확인하기) ·
// coachConnect · aiNoteBox — 위치만 일러스트 뒤로 이동. 삭제 금지.
// 대체된 것: 하단 "이 원인은 어떻게 측정됐나" 근거 박스 → 블록 맨 뒤 numnote
// (2R 수치 강등 — 수치의 승인 거처가 바뀐 것이지 수치가 사라진 게 아니다).
//
// 제거된 것 (M-1): 사진 속 베이크 초를 지칭하던 안내 라벨 2개(구 33-15 A-6 이관분).
// 초 표기의 정본은 승인 7R 의 paircap 텍스트다 — 두 곳에 같은 초를 쓰면 이중 표기가
// 되고, PNG 재생성(§C-4) 후에는 사진 속 표기 자체가 사라진다.

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

import { ANGLE_VS_REFERENCE_PREFIX } from '../lib/deductionLabels';
import { objectJosaKo, type RegionSheetView } from '../lib/deductionSheet';
import { terminologyPlain, type TerminologyTerm } from '../lib/terminologyMap';
import { colors, radius, spacing, typography } from '../theme';
import type { FaultZoomComparison } from '../types/analysis';

interface Props {
  visible: boolean;
  onClose: () => void;
  /** 부위 단위 뷰모델 (lib/deductionSheet.buildRegionSheetView). null = 미렌더. */
  view: RegionSheetView | null;
  /** 시트 상단 크롭 (view.primaryRecordIndex 의 카드). */
  primaryZoom: FaultZoomComparison | null;
  /** 블록 안 크롭 — key = recordIndex (view.blocks[].blockRecordIndexForCrop). */
  blockZooms?: Record<number, FaultZoomComparison | null>;
  // Phase 27 D-06 — zoom 사후 도착 대기 중이면 true. 확대사진 자리에 로딩 placeholder.
  zoomPending?: boolean;
  // Phase 28 D-04 — DTW 기준 프레임 대응 실패 시 true. 전신 폴백 정직 캡션.
  refMatchFailed?: boolean;
  // IN-01 (quick-260724-q6b) — 역립 저신뢰 시 true. 크롭은 유지하되 "예상 부위"
  // 배지를 얹어 확정 결함이 아니라 추정 부위임을 표시 (크롭·수치·비교 삭제 0).
  estimatedArea?: boolean;
  // 우측 비교 대상 라벨 — Mode1='정은지 선수', Mode3='지난 영상'. 크롭 위 halfLabel 용
  // (paircap 우측 라벨은 뷰모델이 소유 — rightPairLabel).
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
// 승인 목업 ② 크롭 카드 칩 (renderDetail chip.brand / chip.gray).
const CHIP_TODAY_FIX = '오늘 고칠 것';
const CHIP_ADVISORY = '참고 — 감점은 아니지만 회전·힘에 영향';
// 시트 제목 접미 (부위 단위 재구성 — 승인본 ② 는 부위 시트다).
const SHEET_TITLE_SUFFIX = ' 부위 상세';
// IN-01 (quick-260724-q6b) — 역립 저신뢰 시 크롭 위 "예상 부위" 배지 카피 (시트가
// 실제 라벨 소유). 확정 결함 아님 — advisoryOrange 톤(표시 전용).
const ESTIMATED_AREA_LABEL = '예상 부위';
// IN-01 — 저신뢰 시 관절을 단정하지 않는 시트 제목(정확한 관절 assert 금지).
const ESTIMATED_AREA_TITLE = '예상 부위 (참고)';

export function DeductionDetailSheet({
  visible,
  onClose,
  view,
  primaryZoom,
  blockZooms,
  zoomPending = false,
  refMatchFailed = false,
  estimatedArea = false,
  rightLabel,
  illustrationSlot,
}: Props) {
  const { width, height: winH } = useWindowDimensions();
  if (!view) return null;

  const sheetHeight = Math.round(winH * 0.78);
  // 합성 이미지 = [내 영상 | 기준] 정사각 2개 → 가로:세로 ≈ 2:1.
  const imgW = width - spacing.screenX * 2;
  const imgH = imgW / 2;

  // 심사 언어 용어줄 (terminologyMap 적용 — "이 지표가 무엇인지"). 부위 시트라
  // 기준 record = 상단 크롭을 낳은 블록의 criterion (뷰모델이 원 키를 나른다).
  const term = criterionTerm(view.primaryCriterion);
  const termText = term ? terminologyPlain(term) : null;

  const renderCrop = (zoom: FaultZoomComparison) => (
    <View style={[styles.imageWrap, { height: imgH }]}>
      <Image
        source={{ uri: zoom.imageUrl }}
        style={styles.image}
        resizeMode="contain"
        accessibilityLabel={`${view.title} 확대 비교 이미지`}
      />
      <View style={[styles.halfLabel, styles.halfLabelLeft]}>
        <Text style={styles.halfLabelText}>내 영상</Text>
      </View>
      <View style={[styles.halfLabel, styles.halfLabelRight]}>
        <Text style={styles.halfLabelText}>{rightLabel}</Text>
      </View>
    </View>
  );

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
            {/* IN-01 — 저신뢰 시 관절 단정 대신 "예상 부위" 제목 (S17 PASS 보존). */}
            <Text style={styles.title}>
              {estimatedArea
                ? ESTIMATED_AREA_TITLE
                : `${view.title}${SHEET_TITLE_SUFFIX}`}
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
            {/* ── 크롭 카드 (승인본 card: chip → cropimg → paircap → onecap) ── */}
            {primaryZoom ? (
              <View style={styles.cropCard}>
                {/* IN-01 (M-21) — 역립 저신뢰에서는 "오늘 고칠 것" 확정 칩을 걸지
                    않는다. 바로 아래 "예상 부위" 배지와 서로 모순되고, IN-01 은
                    확정 단정 표면을 강등하는 결정이다 (S17 PASS 보존). 승인 목업 ②
                    에는 추정 케이스가 없어 이 분기의 정답은 승인본이 아니라
                    IN-01 원칙에서 나온다. */}
                {estimatedArea ? null : (
                  <View
                    style={[
                      styles.chip,
                      view.isAdvisoryOnly ? styles.chipGray : styles.chipBrand,
                    ]}
                  >
                    <Text
                      style={[
                        styles.chipText,
                        view.isAdvisoryOnly
                          ? styles.chipTextGray
                          : styles.chipTextBrand,
                      ]}
                    >
                      {view.isAdvisoryOnly ? CHIP_ADVISORY : CHIP_TODAY_FIX}
                    </Text>
                  </View>
                )}
                {/* IN-01 — 역립 저신뢰 시 크롭 위 "예상 부위" 배지 (확정 결함 아님,
                    advisoryOrange 톤). 크롭·수치·비교는 유지. */}
                {estimatedArea ? (
                  <View style={styles.estimatedBadge}>
                    <Text style={styles.estimatedBadgeText}>
                      {ESTIMATED_AREA_LABEL}
                    </Text>
                  </View>
                ) : null}
                {renderCrop(primaryZoom)}
                {/* paircap (6R) — 좌 '내 자세 · 실 N초' / 우 '기준 (정은지) · 실 N초'.
                    초는 백엔드 방출값만 (뷰모델 소유 — 앱 재계산 금지, F-3). */}
                {view.pairCapLeft || view.pairCapRight ? (
                  <View style={styles.pairCapRow}>
                    <Text style={styles.pairCapText}>{view.pairCapLeft}</Text>
                    <Text style={styles.pairCapText}>{view.pairCapRight}</Text>
                  </View>
                ) : null}
                {/* onecap — 무엇을 견주는 사진인지 1줄. 마킹 기하 단정 0 (M-6). */}
                {view.oneCap ? (
                  <Text style={styles.oneCap}>{view.oneCap}</Text>
                ) : null}
                {/* Phase 28 D-04 — DTW 대응 실패 시 ref 는 전신 폴백이라 정직 고지. */}
                {refMatchFailed ? (
                  <Text style={styles.refMatchNote}>
                    같은 동작 순간을 찾지 못해 전신 화면으로 보여드려요
                  </Text>
                ) : null}
              </View>
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

            {/* ── 결함 블록 N개 (승인본 card.fault) ────────────────────────── */}
            {view.blocks.map((block) => {
              const blockZoom =
                block.blockRecordIndexForCrop != null
                  ? blockZooms?.[block.blockRecordIndexForCrop] ?? null
                  : null;
              return (
                <View key={block.recordIndex} style={styles.faultCard}>
                  {/* fault-head — 번호 헤더 (4R#2, 블록 매몰 방지). */}
                  <View style={styles.faultHead}>
                    <Text style={styles.faultHeadText}>{block.header}</Text>
                  </View>
                  <View style={styles.faultBody}>
                    {block.statusLine ? (
                      <Text style={styles.headline}>{block.statusLine}</Text>
                    ) : null}
                    {block.whyLine ? (
                      <Text style={styles.why}>{block.whyLine}</Text>
                    ) : null}
                    {/* basis (5R#2) — "어디서 재나요" 굵은 문두 + 본문. 세그먼트를
                        중첩 Text 로 그린다 (RN 은 HTML 을 해석하지 않는다). */}
                    {block.basisLine ? (
                      <View style={styles.basisBox}>
                        <Text style={styles.basisText}>
                          {block.basisLine.map((seg, i) => (
                            <Text
                              key={i}
                              style={seg.bold ? styles.basisBold : undefined}
                            >
                              {seg.text}
                            </Text>
                          ))}
                        </Text>
                      </View>
                    ) : null}
                    {block.cueLine ? (
                      <View style={styles.cueBox}>
                        <Text style={styles.cueText}>{block.cueLine}</Text>
                      </View>
                    ) : null}
                    {/* methodline (5R#3) — 측정 방법 정직 라벨. */}
                    {block.methodLine ? (
                      <View style={styles.infoBox}>
                        <Text style={styles.infoText}>{block.methodLine}</Text>
                      </View>
                    ) : null}
                    {/* numnote (2R) — 수치는 블록 맨 뒤 작은 회색 줄. */}
                    {block.numNote ? (
                      <Text style={styles.numNote}>{block.numNote}</Text>
                    ) : null}
                    {/* 이 블록만의 확대 카드 (M-5) — 상단 크롭과 다른 카드일 때만.
                        기존에 보이던 증거를 조용히 잃지 않는다. */}
                    {blockZoom ? renderCrop(blockZoom) : null}
                  </View>
                </View>
              );
            })}

            {/* facing — 두 사진이 달라 보이는 이유 (기준 정렬로 잰 항목이 있을 때만). */}
            {view.facingLine ? (
              <View style={styles.infoBox}>
                <Text style={styles.infoText}>{view.facingLine}</Text>
              </View>
            ) : null}

            {/* 33-14 (A-7) — 목표 자세 일러스트. 말 없이 뭘 하라는지 보여주는
                장치(D-05: 라벨 텍스트 없이 그림만). 미검증/mode3 = 슬롯 자체가
                null 을 렌더 (silent hidden). */}
            {illustrationSlot ?? null}

            {/* 확인하기 안내 (gate ⑤) + 심사 언어 용어줄(terminologyMap).
                33-15 (D-16) — 대시 나열을 문장화 (조사는 objectJosaKo 로 받침 판정). */}
            <View style={styles.bullets}>
              {termText ? (
                <Text style={styles.bullet}>
                  {`이 지표는 ${termText}${objectJosaKo(termText)} 봐요`}
                </Text>
              ) : null}
              <Text style={styles.bullet}>{CHECK_BULLET}</Text>
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
  closeBtn: { padding: 4 },
  closeText: { ...typography.sectionTitle, color: colors.textSecondary },
  scroll: { flex: 1 },
  scrollContent: { paddingBottom: 16, gap: 14 },
  // ── 크롭 카드 (승인본 .card) ─────────────────────────────────────────────
  cropCard: {
    backgroundColor: colors.cardBg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
    gap: 8,
    alignItems: 'stretch',
  },
  // 승인본 .chip (radius 999 = pill).
  chip: {
    alignSelf: 'flex-start',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  chipBrand: { backgroundColor: colors.brandTint },
  chipGray: { backgroundColor: colors.softBg },
  chipText: { ...typography.caption, fontWeight: '700' },
  chipTextBrand: { color: colors.brand },
  chipTextGray: { color: colors.textMid },
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
  // 승인본 .paircap — 12/800 space-between (좌 내 자세 / 우 기준).
  pairCapRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  pairCapText: {
    ...typography.caption,
    fontWeight: '700',
    color: colors.textMid,
    // 좁은 기기에서 좌우 라벨이 서로 밀어내지 않고 줄바꿈되도록 (space-between 유지).
    flexShrink: 1,
  },
  // 승인본 .onecap — caption ink-2 center.
  oneCap: {
    ...typography.caption,
    color: colors.textMid,
    textAlign: 'center',
    lineHeight: 18,
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
  // ── 결함 블록 (승인본 .card.fault + .fault-head) ─────────────────────────
  faultCard: {
    backgroundColor: colors.cardBg,
    borderWidth: 1.5,
    borderColor: colors.brandTint,
    borderRadius: radius.card,
    overflow: 'hidden',
  },
  faultHead: {
    backgroundColor: colors.brandTint,
    borderBottomWidth: 1,
    borderBottomColor: colors.brandSoft,
    paddingHorizontal: spacing.cardPadding,
    paddingVertical: 11,
  },
  faultHeadText: {
    ...typography.boxLabel, // 15/700 — 승인본 .fault-head 15/800
    color: colors.brand,
  },
  faultBody: {
    padding: spacing.cardPadding,
    gap: 8,
  },
  headline: {
    ...typography.bodyLg, // 24/700 카드 헤드라인(몸 말/상태) — E2 토큰
    color: colors.textPrimary,
  },
  why: {
    ...typography.bodySm, // 19/400 왜·보조 본문 (lineHeight 25 — 잘림 방지)
    color: colors.textMid,
  },
  // 승인본 .basis — 연회색 배경 + line 보더 (기존 softBg + border 재사용).
  basisBox: {
    backgroundColor: colors.softBg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.listItem,
    paddingHorizontal: 11,
    paddingVertical: 9,
  },
  basisText: {
    ...typography.bodySm,
    color: colors.textMid,
  },
  basisBold: {
    fontWeight: '700',
    color: colors.textPrimary,
  },
  // 승인본 .cue — inline-block brand-tint 박스, brand 텍스트 (라벨 없음).
  cueBox: {
    alignSelf: 'flex-start',
    backgroundColor: colors.brandTint,
    borderRadius: radius.button,
    paddingHorizontal: 13,
    paddingVertical: 9,
  },
  cueText: { ...typography.bodyMdBold, color: colors.brand }, // 21/700 행동 큐
  // 승인본 .methodline / .facing — 정직 정보 톤 (infoTeal 토큰, 승인 CSS 실측).
  infoBox: {
    backgroundColor: colors.infoTealBg,
    borderWidth: 1,
    borderColor: colors.infoTealBorder,
    borderRadius: radius.listItem,
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  infoText: {
    ...typography.bodySm,
    color: colors.infoTeal,
  },
  // 승인본 .numnote — 블록 맨 뒤 작은 회색 줄 (2R 수치 강등).
  numNote: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  // 확인하기 불릿 + 용어줄.
  bullets: { gap: 6 },
  bullet: {
    ...typography.bodySm, // 19/400 (lineHeight 25 — 잘림 방지)
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
