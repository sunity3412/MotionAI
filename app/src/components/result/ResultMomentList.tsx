// 동작비교 탭 감점 목록 — "8.0s | 왼쪽 무릎 접힘 각도 | −9.4" (belle 09-09 시안 2).
//
// 세 칸이 각각 무엇인지가 이 컴포넌트의 전부다:
//   초    = DeductionRecord.atVideoSec (백엔드가 파이프라인 fps 로 나눠 준 값).
//           **앱은 초를 계산하지 않는다** — rep 프레임 인덱스에서 초를 되짚는 경로는
//           엘보 fixture 에서 3.78초 어긋난다(docs/contract.md:1961-1962).
//           그래서 atVideoSec 이 없는 record 는 초 칸을 비운다(지어내지 않는다).
//   이름  = resultSummary.summaryChipLabel — 요약 칩과 **같은 라벨**을 쓴다.
//   감점  = deductionLabels 포맷 그대로 (U+2212).
//
// 행 탭 = 그 항목의 상세 시트. 시안에는 화살표가 없지만 탭은 살아 있다(요약 칩과
// 같은 규약) — 목록에서 바로 상세로 갈 수 없으면 목록이 막다른 길이 된다.
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, typography } from '../../theme';

export interface ResultMomentRow {
  recordId: string | null;
  /** 학생 영상 초. null = 잰 순간이 없는 criterion (fail-closed) → 초 칸 생략. */
  sec: number | null;
  label: string;
  pointsText: string;
}

export interface ResultMomentListProps {
  rows: readonly ResultMomentRow[];
  onRowPress?: (recordId: string) => void;
  /**
   * 다른 카드 **안**에 들어갈 때 (시안 2: 영상 카드 안 옵션 행 아래). 카드 껍데기
   * (테두리·모서리·배경)를 벗고, 감싼 카드의 좌우 여백만큼 밖으로 물려 행이 카드
   * 폭을 꽉 채우게 한다 — 시안의 구분선이 카드 끝에서 끝까지 간다.
   */
  flat?: boolean;
}

/** 시안 표기 — 소수 1자리 + 's'. 저장값을 그대로 쓰고 반올림만 한다. */
export function formatMomentSec(sec: number | null | undefined): string {
  if (typeof sec !== 'number' || !Number.isFinite(sec) || sec < 0) return '';
  return `${sec.toFixed(1)}s`;
}

export function ResultMomentList({ rows, onRowPress, flat }: ResultMomentListProps) {
  if (rows.length === 0) return null;
  return (
    <View style={flat ? styles.flat : styles.card}>
      {rows.map((r, i) => {
        const secText = formatMomentSec(r.sec);
        const body = (
          <View
            style={[styles.row, i > 0 || flat ? styles.rowDivided : null]}
          >
            <Text style={styles.sec}>{secText}</Text>
            <Text style={styles.label} numberOfLines={1}>
              {r.label}
            </Text>
            <Text style={styles.points}>{r.pointsText}</Text>
          </View>
        );
        const key = r.recordId ?? `moment-${i}`;
        return r.recordId && onRowPress ? (
          <Pressable
            key={key}
            onPress={() => onRowPress(r.recordId as string)}
            accessibilityRole="button"
            accessibilityLabel={`${secText ? `${secText} ` : ''}${r.label} ${r.pointsText}점 상세 보기`}
          >
            {body}
          </Pressable>
        ) : (
          <View key={key}>{body}</View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  // 감싼 카드 안에 들어갈 때 — VideoCompare 카드의 padding 16 만큼 좌우로 물린다.
  flat: { marginHorizontal: -16, marginTop: 10 },
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.resultCard,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.divider,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    minHeight: 52,
    paddingHorizontal: 18,
    gap: 12,
  },
  rowDivided: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.divider,
  },
  // 초는 시안에서 브랜드색 굵은 글씨. 폭을 고정해 이름 칸의 시작선이 흔들리지 않게 한다.
  sec: {
    ...typography.resultChip,
    color: colors.brand,
    width: 46,
  },
  label: {
    ...typography.boxLabel,
    color: colors.textPrimary,
    flex: 1,
  },
  points: {
    ...typography.resultChip,
    color: colors.textMid,
  },
});
