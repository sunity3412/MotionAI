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

import { colors, layout, radius, typography } from '../../theme';

const K = 390 / 467.206;

const D = {
  headerH: 65.7 * K, // 54.8
  rowH: 54.5, // 접힌 행 간격 실측
  // 좌우 안쪽 여백 — 시안 자체가 비대칭이다: 밴드('기준 점수'·'100') 36.70 / 접힌·펼친 행 32.97.
  // 종전엔 둘 다 36.6 이라 행 오른쪽 안쪽 여백이 시안 30~32 대비 38~39 로 넓었다 (audit 09-09).
  bandPadX: 36.6,
  rowPadX: 33.0,
  photoW: 241.7,
  photoH: 119.0,
  photoTop: 52.4, // 펼친 블록 top 기준
  captionTop: 186.4,
  // 캡션 라인박스 높이를 고정한다 — 아래 bodyTop 배선이 캡션 밑변에서 출발하므로 폰트의
  // 자연 line-height 에 맡기면 간격이 폰트 메트릭에 흔들린다 (관례 fontSize×1.3, typography.ts).
  captionLineH: typography.resultSub.fontSize * 1.3,
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
  /** null 이면 기준선 밴드를 그리지 않는다 — belle D-08 억제 상태 (result.tsx). */
  baselineText: string | null;
  rows: readonly ResultPointRow[];
  /** null 이면 종합 밴드를 그리지 않는다 — belle D-08 억제 상태 (result.tsx). */
  totalText: string | null;
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
      {/* D-08 — 기준선 100 · 감점 행 · 종합 N점 이 한 카드 안에서 뺄셈 항등식을
          이룬다. 억제 상태에서 하나만 가리면 나머지로 복원되므로 양 끝을 함께 비운다. */}
      {baselineText != null ? (
        <View style={styles.band}>
          <Text style={styles.bandLabel}>기준 점수</Text>
          <Text style={styles.bandValue}>{baselineText}</Text>
        </View>
      ) : null}

      {rows.map((r, i) => {
        const open = r.recordId != null && r.recordId === expandedId;
        const lines = r.lines ?? [];
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
              <Text style={[styles.points, open ? styles.pointsOpen : null]}>
                {r.pointsText}
              </Text>
              {r.recordId ? (
                // 방향은 시안을 따르지 않는다 — 시안은 접힌 행도 '∧' 인데, 펼친 행과 같은
                // 벡터를 재사용한 실수로 읽힌다(접힘·펼침이 같은 기호면 상태를 못 읽는다).
                // 접힘 ∨ / 펼침 ∧ 규약 유지 (260909-ji1 PLAN §6, 시안 미준수 2건 중 1).
                // 색은 시안대로 브랜드 빨강 — 같은 행의 초 텍스트와 같은 계열이다.
                <Ionicons
                  name={open ? 'chevron-up' : 'chevron-down'}
                  size={14}
                  color={colors.brand}
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
                {r.caption ? (
                  <Text style={styles.caption} lineBreakStrategyIOS="hangul-word">
                    {r.caption}
                  </Text>
                ) : null}
                {lines.length > 0 ? (
                  <View style={r.caption ? styles.bodyBlock : styles.bodyBlockNoCaption}>
                    {lines.map((l, k) => (
                      <Text
                        key={`ln-${k}`}
                        style={styles.bodyText}
                        lineBreakStrategyIOS="hangul-word"
                      >
                        {l}
                      </Text>
                    ))}
                  </View>
                ) : null}
              </View>
            ) : null}
          </View>
        );
      })}

      {totalText != null ? (
        <View style={[styles.band, styles.bandBottom]}>
          <Text style={styles.bandLabel}>종합</Text>
          <Text style={styles.totalValue}>{totalText}</Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.resultCard,
    // 시안 테두리 #6C6C6E · 0.83pt. 종전 hairline(0.33) × #D9D9D9 는 시각 무게가 1/7.6 이었다.
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.resultCardBorder,
    overflow: 'hidden',
  },
  // 위·아래 밴드 — 시안 실측 #F4F4F4 (softBg 와 같은 톤).
  band: {
    height: D.headerH,
    backgroundColor: colors.softBg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: D.bandPadX,
  },
  bandBottom: {
    borderTopWidth: layout.cardBorderWidth,
    borderTopColor: colors.resultDivider,
  },
  // 시안은 라벨 17 / 수치 20.6 으로 위계를 둔다 — 종전엔 넷 다 resultHeadline(18)이라 평탄했다.
  bandLabel: { ...typography.resultBandLabel, color: colors.textPrimary },
  bandValue: { ...typography.resultBandValue, color: colors.textPrimary },
  totalValue: { ...typography.resultBandValue, color: colors.brand },

  // 행 구분선 — 시안 ≈#A2A2A2 · 0.83pt (색은 비텍스트 3:1 로 낮춘 토큰, colors.ts).
  rowWrap: {
    borderTopWidth: layout.cardBorderWidth,
    borderTopColor: colors.resultDivider,
  },
  // 펼친 행은 블록 전체가 옅은 톤 (시안 실측 #FEF8F7).
  rowWrapOpen: { backgroundColor: colors.resultCardTint },
  rowHead: {
    minHeight: D.rowH,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: D.rowPadX,
    gap: 10,
  },
  sec: { ...typography.resultChip, color: colors.brand, width: 42 },
  label: { ...typography.resultChip, color: colors.textPrimary, flex: 1 },
  // 감점 수치 — 시안 #929292 는 흰 배경 3.11:1 로 AA 미달이라 명도만 낮춘 토큰(4.54:1).
  points: { ...typography.resultChip, color: colors.resultTextSub },
  // 펼친 행은 배경이 흰색이 아니라 resultCardTint(#FEF8F7)다. resultTextSub 는 흰 배경
  // 기준 토큰이라 그 위에선 4.32:1 로 AA 에 못 미친다 → 틴트 위에서도 통과하는(4.71:1)
  // 같은 중성 회색 계열 토큰으로 바꾼다. 두 값의 차이(#767676/#707071)는 눈으로 안 보인다.
  pointsOpen: { color: colors.resultTextMeta },

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
    // 종전 textSecondary(#ACACAC)는 펼친 행 배경 #FEF8F7 위 2.16:1 이었다. 시안 캡션 색은
    // audit 표에 없어, 틴트 위 AA 를 만족하는 가장 밝은 중성 회색 토큰(4.71:1)을 쓴다.
    color: colors.resultTextMeta,
    textAlign: 'center',
    lineHeight: D.captionLineH,
    marginTop: D.captionTop - D.photoTop - D.photoH,
  },
  // 설명 블록 — 시안 블록 top +209.6. 종전엔 D.bodyTop 이 선언만 있고 배선이 없어 설명이
  // 캡션 바로 밑(+198.3)에 붙었고 캡션–설명 간격이 13.5 → 7.5pt 로 좁았다 (audit 09-09).
  bodyBlock: { marginTop: D.bodyTop - D.captionTop - D.captionLineH },
  // 캡션이 없는 doc 이면 사진 밑변에서 같은 자리(+209.6)로 잰다.
  bodyBlockNoCaption: { marginTop: D.bodyTop - D.photoTop - D.photoH },
  bodyText: {
    ...typography.resultWarnBody,
    color: colors.textHi,
    textAlign: 'center',
    lineHeight: typography.resultWarnBody.fontSize * 1.7,
    paddingHorizontal: 24,
  },
});
