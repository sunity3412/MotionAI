// Phase 12 Wave 1 (Plan 12-02 T2) — Phase 9 ForcePatternFinding 카드 1건.
//
// 책임:
//   - variant 'big' (finding[0], 358×168) / 'small' (finding[1..2], 174×110)
//   - 0/1/2/3 finding edge case 분기 (caller 책임 — fallback finding 주입 시
//     본 component 는 그대로 렌더. _FALLBACK_BODY 별도 export)
//   - pattern chip 색 매핑 (release/pull/push/brace/rotate = brand,
//     unknown = softBg)
//   - jointHint chip (있을 때만)
//   - confidence label "신뢰도 높음/보통/낮음"
//   - tap → onTap callback (caller 가 ForcePatternDetailModal open)
//
// 책임 분리 (canned KO 직접 표시 / D-12-B2):
//   - finding.interpretation 본문은 백엔드 force_pattern_copy.py canned KO.
//     본 component 는 그대로 렌더 — 카피 수정 X.
//   - Phase 11 통합 시 동일 interpretation 필드를 LLM 풍부화로 교체 — UI 변경 X.
//
// 토큰만 사용 (CLAUDE.md §4 / D-12-U5). brand #FF4B33 변경 0. 이모지 0.

import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme';
import type {
  ForceDirectionPattern,
  ForcePatternFinding,
} from '../types/analysis';

// UI-SPEC §6 pattern chip label 매핑. unknown = "정보" (high_jitter/high_jerk
// signal 은 부위 불명확 → 일반어로 차별).
const PATTERN_LABEL_KO: Record<ForceDirectionPattern, string> = {
  release: 'RELEASE',
  pull: 'PULL',
  push: 'PUSH',
  brace: 'BRACE',
  rotate: 'ROTATE',
  unknown: '정보',
};

// UI-SPEC §4 edge case — findings.length === 0 시 caller 가 fallback finding
// (interpretation = _FALLBACK_BODY, pattern='unknown', confidence=0) 생성 후
// variant='big' 1개 렌더. 본 const 를 export 해서 caller (result.tsx) 가 import.
export const _FALLBACK_BODY =
  '이 영상에서는 분명한 힘 흐름 이슈 신호가 보이지 않습니다. 강사와 함께 확인하는 것을 권장해요.';

function confidenceLabel(c: number): { text: string; color: string } {
  if (c >= 0.7) return { text: '신뢰도 높음', color: colors.brand };
  if (c >= 0.5) return { text: '신뢰도 보통', color: colors.textMid };
  return { text: '신뢰도 낮음', color: colors.textLo };
}

// Phase 12 Wave 2 (Plan 12-03 T3) — D-12-D3 박제. variant='big' 만.
// 채움 색 = label 컬러 (≥0.7 brand / 0.5~0.7 textMid / <0.5 textLo).
function confidenceFillColor(c: number): string {
  if (c >= 0.7) return colors.brand;
  if (c >= 0.5) return colors.textMid;
  return colors.textLo;
}

export type ForcePatternCardProps = {
  finding: ForcePatternFinding;
  rank: 0 | 1 | 2;
  variant: 'big' | 'small';
  onTap: () => void;
};

export function ForcePatternCard({
  finding,
  rank,
  variant,
  onTap,
}: ForcePatternCardProps) {
  const patternLabel = PATTERN_LABEL_KO[finding.pattern];
  const isUnknown = finding.pattern === 'unknown';
  const conf = typeof finding.confidence === 'number' ? finding.confidence : 0;
  const confLabel = confidenceLabel(conf);
  const a11yLabel = `실패 원인 ${rank + 1}, ${patternLabel}, ${
    finding.jointHint ?? '정보'
  }, 자세히 보려면 탭`;

  if (variant === 'big') {
    return (
      <Pressable
        onPress={onTap}
        accessibilityRole="button"
        accessibilityLabel={a11yLabel}
        hitSlop={8}
        style={({ pressed }) => [styles.bigCard, pressed && styles.pressed]}
      >
        <View style={styles.topRow}>
          <Text style={styles.rankBig}>{`#${rank + 1}`}</Text>
          <View
            style={[
              styles.chipBig,
              isUnknown ? styles.chipBigUnknown : styles.chipBigBrand,
            ]}
          >
            <Text
              style={[
                styles.chipBigText,
                isUnknown ? styles.chipBigTextUnknown : styles.chipBigTextBrand,
              ]}
            >
              {patternLabel}
            </Text>
          </View>
          {finding.jointHint ? (
            <View style={styles.jointHintChipBig}>
              <Text style={styles.jointHintChipBigText}>{finding.jointHint}</Text>
            </View>
          ) : null}
          <Text style={[styles.confLabelBig, { color: confLabel.color }]}>
            {confLabel.text}
          </Text>
        </View>
        {/* Phase 12 Wave 2 (Plan 12-03 T3) — D-12-D3 confidence 시각 바.
            variant='big' 전용. 높이 4pt + bg trackBg + fill = conf × 100%.
            UI-SPEC §4 박제. variant='small' 은 spacing 제약으로 미박제. */}
        <View style={styles.confBarTrackBig}>
          <View
            style={[
              styles.confBarFillBig,
              {
                width: `${Math.round(Math.max(0, Math.min(1, conf)) * 100)}%`,
                backgroundColor: confidenceFillColor(conf),
              },
            ]}
          />
        </View>
        <Text style={styles.bigBody}>{finding.interpretation}</Text>
        <Text style={styles.bigHint}>탭하여 자세히 보기 ›</Text>
      </Pressable>
    );
  }

  // variant === 'small'
  return (
    <Pressable
      onPress={onTap}
      accessibilityRole="button"
      accessibilityLabel={a11yLabel}
      hitSlop={8}
      style={({ pressed }) => [styles.smallCard, pressed && styles.pressed]}
    >
      <View style={styles.topRowSmall}>
        <Text style={styles.rankSmall}>{`#${rank + 1}`}</Text>
        <View
          style={[
            styles.chipSmall,
            isUnknown ? styles.chipSmallUnknown : styles.chipSmallBrand,
          ]}
        >
          <Text
            style={[
              styles.chipSmallText,
              isUnknown
                ? styles.chipSmallTextUnknown
                : styles.chipSmallTextBrand,
            ]}
          >
            {patternLabel}
          </Text>
        </View>
      </View>
      {finding.jointHint ? (
        <Text style={styles.smallJointHint}>{finding.jointHint}</Text>
      ) : null}
      <Text style={styles.smallBody} numberOfLines={2} ellipsizeMode="tail">
        {finding.interpretation}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.85 },

  // ── variant big — 358 × 168 (full width) ───────────────────────────────
  bigCard: {
    width: '100%',
    minHeight: 168,
    backgroundColor: colors.cardBg,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 20,
    gap: 12,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  rankBig: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.textLo,
  },
  chipBig: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 11,
  },
  chipBigBrand: { backgroundColor: colors.brand },
  chipBigUnknown: { backgroundColor: colors.softBg },
  chipBigText: { fontSize: 9, fontWeight: '600' },
  chipBigTextBrand: { color: colors.textWhite },
  chipBigTextUnknown: { color: colors.textMid },
  jointHintChipBig: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 11,
    backgroundColor: colors.softBg,
  },
  jointHintChipBigText: {
    fontSize: 11,
    fontWeight: '500',
    color: colors.textHi,
  },
  confLabelBig: {
    fontSize: 10,
    fontWeight: '500',
    marginLeft: 'auto',
  },
  // Phase 12 Wave 2 (Plan 12-03 T3) — D-12-D3 confidence 시각 바 (big 만).
  confBarTrackBig: {
    width: '100%',
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.trackBg,
    overflow: 'hidden',
  },
  confBarFillBig: {
    height: '100%',
    borderRadius: 2,
  },
  bigBody: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textHi,
    lineHeight: 22,
  },
  bigHint: {
    fontSize: 11,
    fontWeight: '400',
    color: colors.textLo,
    textAlign: 'right',
  },

  // ── variant small — 174 × 110 (half width 2-up) ───────────────────────
  smallCard: {
    flex: 1,
    minHeight: 110,
    backgroundColor: colors.cardBg,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 12,
    gap: 6,
  },
  topRowSmall: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  rankSmall: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.textLo,
  },
  chipSmall: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 9,
  },
  chipSmallBrand: { backgroundColor: colors.brandSoft },
  chipSmallUnknown: { backgroundColor: colors.softBg },
  chipSmallText: { fontSize: 9, fontWeight: '600' },
  chipSmallTextBrand: { color: colors.brand },
  chipSmallTextUnknown: { color: colors.textMid },
  smallJointHint: {
    fontSize: 10,
    fontWeight: '500',
    color: colors.textMid,
  },
  smallBody: {
    fontSize: 11,
    fontWeight: '400',
    color: colors.textHi,
    lineHeight: 17,
  },
});
