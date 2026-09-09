// 교정포인트 탭 카드 — 기준 점수 100 → 펼침 행(확대 짝 사진 + 설명) → 종합 N점.
// 피그마 `분석 디자인 업데이트` 시안 3 (belle 09-09).
//
// 이 카드는 앱에 이미 있던 '점수 계산 내역'(ScoreBreakdownSection)과 **같은 것을
// 말한다** — 기준 100 에서 감점을 빼 종합이 나온다는 투명 tally. 시안이 거기에 더한
// 것은 두 가지다: 행을 펼치면 (a) 그 순간의 확대 짝 사진과 (b) 왜 감점인지 문장이
// 나온다. 그래서 규칙을 새로 만들지 않고 같은 값을 다른 조판으로 보여준다.
//
// 시안 실측 (화면 좌상단 기준 px → pt, k = 390/467.206 = 0.83475):
//   카드        43.7, 182.2, 379.9 × 647.6px → 36.5, 152.1, 317.1 × 540.6pt
//   헤더 밴드    높이 65.7px → 54.8pt, bg #F4F4F4(= softBg)
//   펼친 블록    43.7, 247.9, 379.9 × 314.8px → 높이 262.8pt, bg #FEF8F7(= resultCardTint)
//     행 머리     블록 top +18.2pt
//     사진        블록 top +52.4pt, 241.7 × 119.0pt (카드 폭 317.1 안에서 가운데)
//     캡션        블록 top +186.4pt
//     설명 2줄    블록 top +209.6pt
//   접힌 행      간격 54.5pt (589.1 → 654.3 → 719.6px)
//   종합 행      카드 top +480pt
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { colors, radius, typography } from '../../theme';

const K = 390 / 467.206;

const D = {
  headerH: 65.7 * K, // 54.8
  rowH: 54.5, // 접힌 행 간격 실측
  padX: 36.6, // '기준 점수' 왼쪽 여백 (카드 좌변 기준)
  photoW: 241.7,
  photoH: 119.0,
  photoTop: 52.4, // 펼친 블록 top 기준
  captionTop: 186.4,
  bodyTop: 209.6,
} as const;

export interface ResultPointRow {
  recordId: string | null;
  /** 학생 영상 초. null = 잰 순간이 없는 criterion → 초 칸을 비운다(지어내지 않는다). */
  sec: number | null;
  label: string;
  pointsText: string;
  /** 확대 짝 사진(내 영상 | 기준 합성 1장). 없으면 사진 자리를 비운다. */
  imageUrl?: string | null;
  /** 사진 아래 한 줄 (왜 감점인지). */
  caption?: string | null;
  /** 설명 본문 — 줄 단위 배열. */
  lines?: readonly string[];
}

export interface ResultPointsCardProps {
  baselineText: string;
  rows: readonly ResultPointRow[];
  totalText: string;
  /** 펼쳐진 행의 recordId. null = 전부 접힘. */
  expandedId: string | null;
  onToggle: (recordId: string) => void;
  onImageError?: () => void;
}

function secText(sec: number | null | undefined): string {
  if (typeof sec !== 'number' || !Number.isFinite(sec) || sec < 0) return '';
  return `${sec.toFixed(1)}s`;
}

export function ResultPointsCard({
  baselineText,
  rows,
  totalText,
  expandedId,
  onToggle,
  onImageError,
}: ResultPointsCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.band}>
        <Text style={styles.bandLabel}>기준 점수</Text>
        <Text style={styles.bandValue}>{baselineText}</Text>
      </View>

      {rows.map((r, i) => {
        const open = r.recordId != null && r.recordId === expandedId;
        return (
          <View
            key={r.recordId ?? `pt-${i}`}
            style={[styles.rowWrap, open ? styles.rowWrapOpen : null]}
          >
            <Pressable
              onPress={() => r.recordId && onToggle(r.recordId)}
              disabled={!r.recordId}
              accessibilityRole="button"
              accessibilityState={{ expanded: open }}
              accessibilityLabel={`${secText(r.sec)} ${r.label} ${r.pointsText}점`}
              style={styles.rowHead}
            >
              <Text style={styles.sec}>{secText(r.sec)}</Text>
              <Text style={styles.label} numberOfLines={1}>
                {r.label}
              </Text>
              <Text style={styles.points}>{r.pointsText}</Text>
              {r.recordId ? (
                <Ionicons
                  name={open ? 'chevron-up' : 'chevron-down'}
                  size={14}
                  color={colors.textMid}
                />
              ) : null}
            </Pressable>

            {open ? (
              <View style={styles.body}>
                {r.imageUrl ? (
                  <Image
                    source={{ uri: r.imageUrl }}
                    style={styles.photo}
                    resizeMode="cover"
                    onError={onImageError}
                    accessibilityLabel={`${r.label} 확대 비교 사진`}
                  />
                ) : null}
                {r.caption ? <Text style={styles.caption}>{r.caption}</Text> : null}
                {(r.lines ?? []).map((l, k) => (
                  <Text key={`ln-${k}`} style={styles.bodyText}>
                    {l}
                  </Text>
                ))}
              </View>
            ) : null}
          </View>
        );
      })}

      <View style={[styles.band, styles.bandBottom]}>
        <Text style={styles.bandLabel}>종합</Text>
        <Text style={styles.totalValue}>{totalText}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.resultCard,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.divider,
    overflow: 'hidden',
  },
  // 위·아래 밴드 — 시안 실측 #F4F4F4 (softBg 와 같은 톤).
  band: {
    height: D.headerH,
    backgroundColor: colors.softBg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: D.padX,
  },
  bandBottom: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.divider,
  },
  bandLabel: { ...typography.resultHeadline, color: colors.textPrimary },
  bandValue: { ...typography.resultHeadline, color: colors.textPrimary },
  totalValue: { ...typography.resultHeadline, color: colors.brand },

  rowWrap: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.divider,
  },
  // 펼친 행은 블록 전체가 옅은 톤 (시안 실측 #FEF8F7).
  rowWrapOpen: { backgroundColor: colors.resultCardTint },
  rowHead: {
    minHeight: D.rowH,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: D.padX,
    gap: 10,
  },
  sec: { ...typography.resultChip, color: colors.brand, width: 42 },
  label: { ...typography.resultChip, color: colors.textPrimary, flex: 1 },
  points: { ...typography.resultChip, color: colors.textMid },

  body: { alignItems: 'center', paddingBottom: 18 },
  photo: {
    width: D.photoW,
    height: D.photoH,
    borderRadius: radius.resultBox,
    marginTop: D.photoTop - D.rowH,
    backgroundColor: colors.trackBg,
  },
  caption: {
    ...typography.resultSub,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: D.captionTop - D.photoTop - D.photoH,
  },
  bodyText: {
    ...typography.resultWarnBody,
    color: colors.textHi,
    textAlign: 'center',
    lineHeight: typography.resultWarnBody.fontSize * 1.7,
    paddingHorizontal: 24,
  },
});
