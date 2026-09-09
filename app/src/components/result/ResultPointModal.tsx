// 교정포인트2 — 전체화면 모달, 1/N 페이징. 피그마 시안 5 (belle 09-09).
//
// 언제 열리나: 교정포인트 탭의 '교정 방법 자세히 보기 >' 를 누를 때. 디자이너 확인
// (2026-09-08, belle 전달): "교정포인트 1번은 자세히보기 눌렀을 때 자세한 화면들이
// 나오는거제? 교정포인트 2번으로?" → "네".
//
// 시안 실측 (화면 좌상단 기준 px → pt, k = 390/467.206 = 0.83475):
//   시트        0, 138.9, 467.2 × 908.8px → 0, 115.9, 390 × 758.6pt (윗모서리만 둥글게)
//   페이지 표시  177.9, 205.2 → 148.5, 171.3
//   칩          123.6, 246.8, 220.2 × 36.4px → 103.2, 206.0, 183.8 × 30.4pt
//   헤드라인 2줄 78.4, 315.9, 309.6 × 62.6px → 65.4, 263.7, 258.4 × 52.3pt (≈20pt bold)
//   서브 2줄     94.8, 399.1, 278.1 × 35.6px → 79.1, 333.1, 232.1 × 29.7pt (≈11pt)
//   사진        38.2, 450.7, 391.0 × 199.0px → 31.9, 376.2, 326.4 × 166.1pt
//   '이렇게 해보세요' 37.6, 668.5, 392.2 × 114.8px → 31.4, 558.0, 327.4 × 95.8pt (bg #FEF8F7)
//   '어디서 재나요?'  37.6, 793.1, 같은 크기 → 31.4, 662.0 (bg #F4F4F6 = softBg)
//   CTA         37.6, 934.0, 392.2 × 71.3px → 31.4, 779.7, 327.4 × 59.5pt
//
// 시트 뒤로 헤더가 비쳐 어두워진다 — 시안 실측 #74261B 은 브랜드 빨강에 검정 50%가
// 얹힌 값이다(233·77·55 의 정확히 절반). 그래서 스크림은 rgba(0,0,0,0.5) 하나면 된다.
//
// 문장은 전부 doc 저장값이다 — 이 화면이 지어내는 문장은 0이다. 없는 칸은 그리지 않는다.
import { useEffect, useState } from 'react';
import { Image, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { colors, radius, typography } from '../../theme';

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

  const page = pages[index];
  if (!visible || !page) return null;
  const total = pages.length;
  const canPrev = index > 0;
  const canNext = index < total - 1;

  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      {/* 스크림 — 시트 위쪽으로 헤더가 어둡게 비친다. 탭하면 닫힌다. */}
      <Pressable style={styles.scrim} onPress={onClose} accessibilityRole="button" accessibilityLabel="닫기" />
      <View style={styles.sheet}>
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
            <Ionicons name="chevron-back" size={13} color={colors.textMid} />
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
            <Ionicons name="chevron-forward" size={13} color={colors.textMid} />
          </Pressable>
        </View>

        <ScrollView
          contentContainerStyle={styles.body}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.chip}>
            <Text style={styles.chipText}>{page.chipText}</Text>
          </View>
          {page.headline ? <Text style={styles.headline}>{page.headline}</Text> : null}
          {page.sub ? <Text style={styles.sub}>{page.sub}</Text> : null}
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
              <Text style={styles.boxBodyCue}>{page.cue}</Text>
            </View>
          ) : null}
          {page.basis ? (
            <View style={[styles.box, styles.boxBasis]}>
              <Text style={styles.boxTitleBasis}>어디서 재나요?</Text>
              <Text style={styles.boxBodyBasis}>{page.basis}</Text>
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

const SHEET_TOP_RATIO = 115.9 / 844; // 시안 시트 윗변 / 화면 높이 — 기기 높이에 비례

const styles = StyleSheet.create({
  scrim: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.5)' },
  sheet: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    top: `${SHEET_TOP_RATIO * 100}%`,
    backgroundColor: colors.cardBg,
    borderTopLeftRadius: radius.modal,
    borderTopRightRadius: radius.modal,
  },
  grip: {
    alignSelf: 'center',
    width: 36,
    height: 3,
    borderRadius: 2,
    backgroundColor: colors.divider,
    marginTop: 12,
  },
  close: { position: 'absolute', right: 20, top: 26 },
  pager: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    marginTop: 22,
  },
  pagerBtn: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 1,
    borderColor: colors.divider,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pagerBtnOff: { opacity: 0.35 },
  pagerText: { ...typography.resultChip, color: colors.textMid },

  body: { alignItems: 'center', paddingHorizontal: 31.4, paddingBottom: 32 },
  chip: {
    marginTop: 22,
    paddingHorizontal: 16,
    height: 30.4,
    borderRadius: 30.4 / 2,
    backgroundColor: colors.resultChipBg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chipText: { ...typography.resultChip, color: colors.brand },
  // 폭을 시안 텍스트 블록 폭으로 묶는다 — 상자 폭(327.4)을 그대로 쓰면 줄바꿈 자리가
  // 달라져 "…차이가 있어 / 요" 처럼 어색하게 끊긴다. 시안 실측: 헤드라인 258.4pt,
  // 서브 232.1pt.
  headline: {
    ...typography.title,
    fontSize: 20,
    lineHeight: 26,
    maxWidth: 258.4,
    color: colors.textPrimary,
    textAlign: 'center',
    marginTop: 24,
  },
  sub: {
    ...typography.resultWarnBody,
    fontSize: 11,
    lineHeight: 15,
    maxWidth: 232.1,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 14,
  },
  photoWrap: { width: '100%', marginTop: 20 },
  photo: {
    width: '100%',
    aspectRatio: 326.4 / 166.1,
    borderRadius: radius.resultBox,
    backgroundColor: colors.trackBg,
  },
  // 사진 위에 얹는 칩 — 시안은 흰 알약. 사진이 밝든 어둡든 읽히도록 흰 배경 위
  // 진한 글씨(§12 "밝은 반투명 위에 밝은 것을 겹치지 말 것").
  jointChip: {
    position: 'absolute',
    right: 8.4,
    bottom: 8.4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    backgroundColor: colors.cardBg,
  },
  jointChipText: { ...typography.captionSmall, color: colors.textMid },
  box: {
    width: '100%',
    borderRadius: radius.resultBox,
    paddingVertical: 14,
    paddingHorizontal: 18,
    alignItems: 'center',
    marginTop: 14,
  },
  boxCue: { backgroundColor: colors.resultCardTint },
  boxBasis: { backgroundColor: colors.softBg },
  boxTitleCue: { ...typography.resultChip, color: colors.brand },
  boxBodyCue: {
    ...typography.resultWarnBody,
    fontSize: 11,
    lineHeight: 17,
    color: colors.brand,
    textAlign: 'center',
    marginTop: 6,
  },
  boxTitleBasis: { ...typography.resultChip, color: colors.textMid },
  boxBodyBasis: {
    ...typography.resultWarnBody,
    fontSize: 11,
    lineHeight: 17,
    color: colors.textMid,
    textAlign: 'center',
    marginTop: 6,
  },
  cta: {
    width: '100%',
    height: 59.5,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 22,
  },
  ctaPressed: { opacity: 0.85 },
  ctaText: { ...typography.resultCta, color: colors.textWhite },
});
