// 교정포인트2 — 전체화면 모달, 1/N 페이징. 피그마 시안 5 (belle 09-09).
//
// 언제 열리나: 교정포인트 탭의 '교정 방법 자세히 보기 >' 를 누를 때. 디자이너 확인
// (2026-09-08, belle 전달): "교정포인트 1번은 자세히보기 눌렀을 때 자세한 화면들이
// 나오는거제? 교정포인트 2번으로?" → "네".
//
// 시안 실측 (화면 좌상단 기준 px → pt, k = 390/467.206 = 0.83475). 위치·크기는 이 k 로
// 환산한 값이 맞는다. **글자 크기는 아니다** — 벡터 잉크폭을 글자수로 나눌 때 한글
// advance 0.864em 을 넣어야 한다(typography.ts 주석, 260909-ji1 WAVE 1 정정). 아래
// 괄호의 글자 pt 는 그 재역산값이고, 토큰(resultModal* / resultPager)이 정본이다.
//   시트        0, 138.9, 467.2 × 908.8px → 0, 115.9, 390 × 758.6pt (윗모서리만 둥글게)
//   페이지 표시  177.9, 205.2 → 148.5, 171.3 ('1 / 5' 15.5pt regular)
//   칩          123.6, 246.8, 220.2 × 36.4px → 103.2, 206.0, 183.8 × 30.4pt
//   헤드라인 2줄 78.4, 315.9, 309.6 × 62.6px → 65.4, 263.7, 258.4 × 52.3pt (23pt bold)
//   서브 2줄     94.8, 399.1, 278.1 × 35.6px → 79.1, 333.1, 232.1 × 29.7pt (14.5pt)
//   사진        38.2, 450.7, 391.0 × 199.0px → 31.9, 376.2, 326.4 × 166.1pt
//   '이렇게 해보세요' 37.6, 668.5, 392.2 × 114.8px → 31.4, 558.0, 327.4 × 95.8pt (bg #FEF8F7, 본문 15.5pt)
//   '어디서 재나요?'  37.6, 793.1, 같은 크기 → 31.4, 662.0 (bg #F4F4F6 = softBg, 본문 15.5pt)
//   CTA         37.6, 934.0, 392.2 × 71.3px → 31.4, 779.7, 327.4 × 59.5pt
//
// 시트 뒤로 헤더가 비쳐 어두워진다 — 시안 실측 #74261B 은 브랜드 빨강에 검정 50%가
// 얹힌 값이다(233·77·55 의 정확히 절반). 그래서 스크림은 rgba(0,0,0,0.5) 하나면 된다.
//
// 문장은 전부 doc 저장값이다 — 이 화면이 지어내는 문장은 0이다. 없는 칸은 그리지 않는다.
import { useEffect, useState } from 'react';
import { Image, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { colors, fontFamily, radius, typography } from '../../theme';
import { useResultScale, useResultTopDelta } from './ResultHeader';

/**
 * 시안 세로 앵커 — 전부 **시안 화면 상단(y=0) 기준 pt** 다. marginTop 은 여기서 차분으로
 * 계산한다(다른 result 컴포넌트의 D 규약). 하드코딩 marginTop 열 개로 두었을 때는
 * 칩 −5.0 / 헤드라인 −8.4 / 서브 −11.8 / 페이저 −14.3pt 씩 어긋났다(09-09 대조).
 *
 * 텍스트 앵커(헤드라인·서브)는 벡터 **잉크** 상단이고 marginTop 은 라인박스 상단을
 * 놓으므로 fontSize × 0.15 를 빼서 맞춘다(PLAN §3 라인박스 보정). 줄수는 시안대로 2줄
 * 기준 — 문장은 doc 값이라 1줄·3줄이면 그 아래가 그만큼 당겨지거나 밀린다.
 */
const D = {
  sheetTop: 115.9,
  gripTop: 24,
  gripW: 41,
  gripH: 1.4,
  pagerTop: 171.27,
  pagerDia: 18,
  chipTop: 205.98,
  chipH: 30.4,
  headlineTop: 263.69,
  headlineLines: 2,
  subTop: 333.16,
  subLines: 2,
  photoTop: 376.22,
  photoW: 326.4,
  photoH: 166.1,
  box1Top: 558.04,
  boxH: 95.8,
  box2Top: 662.02,
  ctaTop: 779.64,
  ctaH: 59.5,
  bodyPadX: 31.4,
  /** X 닫기 — 시안은 카드 우변보다 6.5pt 안쪽. 종전 right 20 은 7.3pt 바깥이었다. */
  closeRight: 37.7,
  closeTop: 26,
  /** 사진 위 pill 들의 사진 모서리로부터의 인셋 — 관절선 칩 실측(8.4)과 같은 값. */
  photoPillInset: 8.4,
} as const;

// 줄 높이 — fontSize × 1.3 이상(typography.ts Pitfall 3, 줄겹침 방지).
const HEADLINE_LH = 30; // 23 × 1.3
const SUB_LH = 19; // 14.5 × 1.3
const BODY_LH = 21; // 15.5 × 1.35
const inkTop = (fontSize: number) => fontSize * 0.15;

const headlineBoxTop = D.headlineTop - inkTop(typography.resultModalHeadline.fontSize);
const subBoxTop = D.subTop - inkTop(typography.resultModalSub.fontSize);

/**
 * 앵커 차분 = marginTop.
 * ★ 페이저: PLAN §3 표는 40 이라 적었지만 앵커로 계산하면 171.27 − (115.9 + 24 + 1.4) =
 *   30.0 이다. 40 이면 페이저가 시안보다 10pt 내려간다. 앵커가 실측 정본이라 차분을 쓴다.
 */
const GAP = {
  pager: D.pagerTop - (D.sheetTop + D.gripTop + D.gripH), // 30.0
  chip: D.chipTop - (D.pagerTop + D.pagerDia), // 16.7
  headline: headlineBoxTop - (D.chipTop + D.chipH), // 23.9
  sub: subBoxTop - (headlineBoxTop + HEADLINE_LH * D.headlineLines), // 10.7
  photo: D.photoTop - (subBoxTop + SUB_LH * D.subLines), // 7.2
  box1: D.box1Top - (D.photoTop + D.photoH), // 15.7
  box2: D.box2Top - (D.box1Top + D.boxH), // 8.2
  cta: D.ctaTop - (D.box2Top + D.boxH), // 21.8
} as const;

export interface ResultPointPage {
  /** 칩 문구 — "고칠 것 · 오른쪽 팔꿈치 11.6점". */
  chipText: string;
  /** 굵은 2줄. 없으면 칩 아래가 바로 사진이다. */
  headline: string | null;
  /** 헤드라인 아래 회색 보조 문장. */
  sub: string | null;
  imageUrl: string | null;
  /**
   * belle 09-09 '관절선 끄기' — 표시 없는 판 (contract.md §11.11). 백엔드가 같은
   * crop 을 한 번 더 합성한 것이라 갈아끼워도 그림이 튀지 않는다.
   * **null 이면 칩을 그리지 않는다** — 안 되는 버튼을 놓지 않는다(fail-closed).
   */
  imageUrlPlain: string | null;
  /**
   * 사진 오른쪽 반쪽(기준 선수) 위 pill 문구 — 기준 선수명. 시안 5 는 좌 '내 영상' /
   * 우 선수명 두 알약으로 어느 쪽이 자기 영상인지 알린다. **없으면 오른쪽 pill 을
   * 그리지 않는다** — 문구를 지어내지 않는다. optional 이라 호출부 무수정으로 컴파일된다.
   */
  referenceLabel?: string | null;
  /** '이렇게 해보세요' 본문 (행동 큐). */
  cue: string | null;
  /** '어디서 재나요?' 본문 (측정 근거). */
  basis: string | null;
}

export interface ResultPointModalProps {
  visible: boolean;
  /** 0-based. pages 범위를 벗어나면 렌더하지 않는다. */
  index: number;
  pages: readonly ResultPointPage[];
  onIndexChange: (next: number) => void;
  onClose: () => void;
  /** '보완 운동 보기' — 보완운동 탭으로. 미전달 시 버튼 미렌더. */
  onSeeExercises?: () => void;
  onImageError?: () => void;
}

export function ResultPointModal({
  visible,
  index,
  pages,
  onIndexChange,
  onClose,
  onSeeExercises,
  onImageError,
}: ResultPointModalProps) {
  // 관절선 표시 상태. 페이지를 넘기면 되돌린다 — 다음 항목은 표시를 보고 시작하는
  // 것이 기본이고, 앞 항목에서 끈 상태가 따라오면 "왜 표시가 없지"가 된다.
  const [jointsHidden, setJointsHidden] = useState(false);
  useEffect(() => {
    setJointsHidden(false);
  }, [index]);
  // 시트 윗변 — 탭·콘텐츠와 같은 규약(useResultTopDelta + 시안 y × s). 종전 '115.9/844
  // 비율' 은 시트가 120.0pt 에서 시작해 117.7~133.4pt 에 있는 탭 라벨을 덮었고, 분모 844
  // 도 시안 프레임 높이(875.0)가 아니었다. 시안은 탭 아래 10.8pt 를 띄운다.
  const topDelta = useResultTopDelta();
  const s = useResultScale();

  const page = pages[index];
  if (!visible || !page) return null;
  const total = pages.length;
  const canPrev = index > 0;
  const canNext = index < total - 1;
  const referenceLabel = page.referenceLabel ?? null;

  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      {/* 스크림 — 시트 위쪽으로 헤더가 어둡게 비친다. 탭하면 닫힌다. */}
      <Pressable style={styles.scrim} onPress={onClose} accessibilityRole="button" accessibilityLabel="닫기" />
      <View style={[styles.sheet, { top: topDelta + D.sheetTop * s }]}>
        <View style={styles.grip} />
        <Pressable
          onPress={onClose}
          accessibilityRole="button"
          accessibilityLabel="닫기"
          hitSlop={16}
          style={styles.close}
        >
          <Ionicons name="close" size={18} color={colors.textPrimary} />
        </Pressable>

        <View style={styles.pager}>
          <Pressable
            onPress={() => canPrev && onIndexChange(index - 1)}
            disabled={!canPrev}
            accessibilityRole="button"
            accessibilityLabel="이전 교정 포인트"
            hitSlop={12}
            style={[styles.pagerBtn, !canPrev && styles.pagerBtnOff]}
          >
            <Ionicons name="chevron-back" size={12} color={colors.resultPagerChevron} />
          </Pressable>
          <Text style={styles.pagerText}>
            {index + 1} / {total}
          </Text>
          <Pressable
            onPress={() => canNext && onIndexChange(index + 1)}
            disabled={!canNext}
            accessibilityRole="button"
            accessibilityLabel="다음 교정 포인트"
            hitSlop={12}
            style={[styles.pagerBtn, !canNext && styles.pagerBtnOff]}
          >
            <Ionicons name="chevron-forward" size={12} color={colors.resultPagerChevron} />
          </Pressable>
        </View>

        <ScrollView
          contentContainerStyle={styles.body}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.chip}>
            <Text style={styles.chipText}>{page.chipText}</Text>
          </View>
          {/* hangul-word — '셰이/프와'·'무너/지는' 처럼 어절이 줄 끝에서 쪼개지던 것
              (SummaryCard 선례, RN 0.81 iOS). */}
          {page.headline ? (
            <Text style={styles.headline} lineBreakStrategyIOS="hangul-word">
              {page.headline}
            </Text>
          ) : null}
          {page.sub ? (
            <Text style={styles.sub} lineBreakStrategyIOS="hangul-word">
              {page.sub}
            </Text>
          ) : null}
          {page.imageUrl ? (
            <View style={styles.photoWrap}>
              <Image
                source={{
                  uri:
                    jointsHidden && page.imageUrlPlain
                      ? page.imageUrlPlain
                      : page.imageUrl,
                }}
                style={styles.photo}
                resizeMode="cover"
                onError={onImageError}
                accessibilityLabel={
                  jointsHidden
                    ? '확대 비교 사진 (관절선 없음)'
                    : '확대 비교 사진'
                }
              />
              {/* 역할 라벨 — 백엔드 합성물은 좌(내 영상)·우(기준) 반쪽이 붙은 한 장이라
                  라벨이 없으면 어느 쪽이 자기 영상인지 알 수 없다(09-09 대조). 시안 5 는
                  좌상단 브랜드 pill '내 영상', 우상단 어두운 pill 에 기준 선수명. 합성물
                  자체는 손대지 않고 위에 얹는다. 오른쪽 문구는 doc 에서 온 referenceLabel
                  뿐 — 없으면 그 pill 을 그리지 않는다. */}
              <View style={[styles.rolePill, styles.rolePillMine]} pointerEvents="none">
                <Text style={styles.rolePillText} numberOfLines={1}>
                  내 영상
                </Text>
              </View>
              {referenceLabel ? (
                <View style={[styles.rolePill, styles.rolePillRef]} pointerEvents="none">
                  <Text style={styles.rolePillText} numberOfLines={1}>
                    {referenceLabel}
                  </Text>
                </View>
              ) : null}
              {/* 표시 없는 판이 있는 카드에만. 사진 오른쪽 아래 (시안 실측
                  289.4, 514.0 — 사진 우하단에서 8.4pt 안쪽). */}
              {page.imageUrlPlain ? (
                <Pressable
                  onPress={() => setJointsHidden((v) => !v)}
                  accessibilityRole="button"
                  accessibilityState={{ selected: jointsHidden }}
                  accessibilityLabel={
                    jointsHidden ? '관절선 다시 보기' : '관절선 끄기'
                  }
                  hitSlop={10}
                  style={styles.jointChip}
                >
                  <Text style={styles.jointChipText}>
                    {jointsHidden ? '관절선 보기' : '관절선 끄기'}
                  </Text>
                </Pressable>
              ) : null}
            </View>
          ) : null}
          {page.cue ? (
            <View style={[styles.box, styles.boxCue]}>
              <Text style={styles.boxTitleCue}>이렇게 해보세요.</Text>
              <Text style={styles.boxBodyCue} lineBreakStrategyIOS="hangul-word">
                {page.cue}
              </Text>
            </View>
          ) : null}
          {page.basis ? (
            <View style={[styles.box, styles.boxBasis]}>
              <Text style={styles.boxTitleBasis}>어디서 재나요?</Text>
              <Text style={styles.boxBodyBasis} lineBreakStrategyIOS="hangul-word">
                {page.basis}
              </Text>
            </View>
          ) : null}
          {onSeeExercises ? (
            <Pressable
              onPress={onSeeExercises}
              accessibilityRole="button"
              accessibilityLabel="보완 운동 보기"
              style={({ pressed }) => [styles.cta, pressed && styles.ctaPressed]}
            >
              <Text style={styles.ctaText}>보완 운동 보기</Text>
            </Pressable>
          ) : null}
        </ScrollView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  scrim: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.5)' },
  // top 은 렌더에서 (기기 delta + 시안 y × s) 로 얹는다 — 위 topDelta 주석.
  sheet: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: colors.cardBg,
    borderTopLeftRadius: radius.resultSheet,
    borderTopRightRadius: radius.resultSheet,
  },
  grip: {
    alignSelf: 'center',
    width: D.gripW,
    height: D.gripH,
    borderRadius: D.gripH / 2,
    backgroundColor: colors.resultGrip,
    marginTop: D.gripTop,
  },
  close: { position: 'absolute', right: D.closeRight, top: D.closeTop },
  // 행 높이를 원 지름으로 고정해 아래 칩의 차분 계산이 글꼴 메트릭에 흔들리지 않게 한다.
  pager: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    height: D.pagerDia,
    marginTop: GAP.pager,
  },
  pagerBtn: {
    width: D.pagerDia,
    height: D.pagerDia,
    borderRadius: D.pagerDia / 2,
    borderWidth: 1,
    borderColor: colors.resultPagerLine,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // 시안을 따르지 않는 곳 — 시안은 1/5 에서도 좌우가 같지만, 비활성을 안 보이면 누를 수
  // 있는 것처럼 읽힌다. 다만 종전 0.35 는 원이 거의 사라져 "버튼이 없다"로도 읽혔다 —
  // 0.5 면 셰브론(#2F2F2F)이 회색으로 남아 '있지만 지금은 아님' 으로 읽힌다.
  pagerBtnOff: { opacity: 0.5 },
  pagerText: { ...typography.resultPager, lineHeight: D.pagerDia, color: colors.resultPagerLine },

  body: { alignItems: 'center', paddingHorizontal: D.bodyPadX, paddingBottom: 32 },
  chip: {
    marginTop: GAP.chip,
    paddingHorizontal: 16,
    height: D.chipH,
    borderRadius: D.chipH / 2,
    backgroundColor: colors.resultChipBg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chipText: { ...typography.resultChip, color: colors.brand },
  // 폭을 시안 텍스트 블록 폭으로 묶는다 — 상자 폭(327.4)을 그대로 쓰면 줄바꿈 자리가
  // 달라져 "…차이가 있어 / 요" 처럼 어색하게 끊긴다. 시안 실측: 헤드라인 258.4pt,
  // 서브 232.1pt.
  headline: {
    ...typography.resultModalHeadline,
    lineHeight: HEADLINE_LH,
    maxWidth: 258.4,
    color: colors.textPrimary,
    textAlign: 'center',
    marginTop: GAP.headline,
  },
  sub: {
    ...typography.resultModalSub,
    lineHeight: SUB_LH,
    maxWidth: 232.1,
    color: colors.resultTextSub,
    textAlign: 'center',
    marginTop: GAP.sub,
  },
  photoWrap: { width: '100%', marginTop: GAP.photo },
  photo: {
    width: '100%',
    aspectRatio: D.photoW / D.photoH,
    borderRadius: radius.resultBox,
    backgroundColor: colors.trackBg,
  },
  // 역할 pill — 왼쪽 브랜드 채움, 오른쪽은 영상 카드 라벨과 같은 어두운 pill(videoBg,
  // VideoCompare slotLabelPillMuted 와 동일). 흰 글자.
  rolePill: {
    position: 'absolute',
    top: D.photoPillInset,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
  },
  rolePillMine: { left: D.photoPillInset, backgroundColor: colors.brand },
  rolePillRef: { right: D.photoPillInset, backgroundColor: colors.videoBg },
  rolePillText: {
    ...typography.captionSmall,
    fontFamily: fontFamily.bold,
    fontWeight: '700',
    color: colors.textWhite,
  },
  // 사진 위에 얹는 칩 — 시안은 흰 알약. 사진이 밝든 어둡든 읽히도록 흰 배경 위
  // 진한 글씨(§12 "밝은 반투명 위에 밝은 것을 겹치지 말 것").
  jointChip: {
    position: 'absolute',
    right: D.photoPillInset,
    bottom: D.photoPillInset,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    backgroundColor: colors.cardBg,
  },
  jointChipText: { ...typography.captionSmall, color: colors.textMid },
  // minHeight 로 시안 높이를 하한으로 둔다 — 아래 상자·CTA 의 차분이 이 높이를 전제한다.
  box: {
    width: '100%',
    minHeight: D.boxH,
    borderRadius: radius.resultModalBox,
    paddingVertical: 14,
    paddingHorizontal: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  boxCue: { backgroundColor: colors.resultCardTint, marginTop: GAP.box1 },
  boxBasis: { backgroundColor: colors.softBg, marginTop: GAP.box2 },
  boxTitleCue: { ...typography.resultChip, color: colors.brand },
  boxBodyCue: {
    ...typography.resultModalBody,
    lineHeight: BODY_LH,
    color: colors.brand,
    textAlign: 'center',
    marginTop: 6,
  },
  boxTitleBasis: { ...typography.resultChip, color: colors.resultTextMeta },
  boxBodyBasis: {
    ...typography.resultModalBody,
    lineHeight: BODY_LH,
    color: colors.resultTextMeta,
    textAlign: 'center',
    marginTop: 6,
  },
  cta: {
    width: '100%',
    height: D.ctaH,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: GAP.cta,
  },
  ctaPressed: { opacity: 0.85 },
  ctaText: { ...typography.resultCta, color: colors.textWhite },
});
