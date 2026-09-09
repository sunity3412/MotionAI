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
// 행 탭 = 그 초로 두 영상을 함께 옮기고(seekTo) 상세 시트를 연다. 종전에 진행바 위
// 틱이 하던 일을 belle 09-09 판정으로 이 행이 이어받았다 — 행에 초가 이미 적혀 있어
// 눌렀을 때 어디로 가는지가 눈에 보인다.
//
// ── 활성 표식 (belle 09-09: "8초가 됬을 때 테두리? 같은 간단한 표시") ──────────
//
// belle 이 말한 '테두리'는 **수단을 바꿔** 구현했다. RN 의 `borderWidth` 는 레이아웃에
// 참여해 행 높이를 밀고(52 → 55), 그렇다고 절대배치 아웃라인을 그리면 행 위·아래에
// 이미 있는 hairline 구분선과 1pt 안에 평행선 3개가 겹쳐 **상태가 아니라 렌더 깨짐**
// 으로 읽힌다. 게다가 4변 brand 둘레는 헤더·초 숫자·CTA 의 빨강과 정면으로 싸운다.
//
// 대신 **채움**을 쓴다. 활성 행 위·아래에는 이미 hairline 이 그려져 있어서, 그 사이를
// 채우면 두 선이 띠의 위·아래 변이 된다 — 획을 새로 긋지 않고 얻는 테두리다. 색은
// 이미 이 화면이 쓰는 `resultChipBg`(감점 칩과 같은 색)라 새 토큰·새 도형이 0이다.
// belle 이 "너무 조용하다"고 하면 다음 수는 획이 아니라 좌우를 물린 둥근 판이다.
//
// 두 번째 신호로 감점 수치의 대비를 올린다(textMid → textPrimary). 색상이 아니라
// **휘도** 채널이라 색약·저모션에서도 남는다 — 채움만으로는 그 두 경우에 신호가 0 이다.
//
// 모션은 진입 180ms / 이탈 140ms 페이드뿐이다. 스프링·펄스·루프를 쓰지 않는 이유:
// 그 순간 영상은 **멈춘다**. 화면에서 움직이는 것이 하나도 없을 때 행 하나가 계속
// 깜빡이면 그것만 유일한 움직임이 되어 오류 표시로 읽힌다. 나갈 때가 들어올 때보다
// 빠른 것은 다음 행의 등장이 눈을 가져야 하기 때문이다.
//
// `backgroundColor` 를 직접 애니메이션하지 않는다 — native driver 가 안 받아 JS
// 드라이버로 떨어지고, 하필 정지 프레임 순간에 프레임을 떨어뜨린다. 그래서 채움은
// 별도 절대 레이어의 opacity 다(노드 1개의 대가로 그 위험이 0 이 된다).
import { useEffect, useRef, useState } from 'react';
import {
  AccessibilityInfo,
  Animated,
  Easing,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { colors, radius, typography } from '../../theme';

const FADE_IN_MS = 180;
const FADE_OUT_MS = 140;

/**
 * 저모션 설정. 켜져 있으면 페이드를 돌리지 않고 값을 즉시 확정한다 —
 * 표식 자체는 한 픽셀도 바뀌지 않는다(채움·대비는 정적 차이라 모션을 걷어내도
 * 잃는 것이 0). 펄스·글로우 기반 표식이었다면 저모션에서 표식이 사라졌을 것이다.
 */
function useReduceMotion(): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    let alive = true;
    AccessibilityInfo.isReduceMotionEnabled()
      .then((v) => {
        if (alive) setOn(v);
      })
      .catch(() => {
        /* 조회 실패 = 기본값(끔) — 표식은 그대로 동작한다 */
      });
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setOn);
    return () => {
      alive = false;
      sub.remove();
    };
  }, []);
  return on;
}

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
  /** 지금 코칭이 짚고 있는 record. 그 행에 표식이 켜진다. */
  activeRecordId?: string | null;
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

function MomentRow({
  row,
  divided,
  active,
  onPress,
}: {
  row: ResultMomentRow;
  divided: boolean;
  active: boolean;
  onPress?: (recordId: string) => void;
}) {
  const reduceMotion = useReduceMotion();
  const fade = useRef(new Animated.Value(active ? 1 : 0)).current;

  useEffect(() => {
    if (reduceMotion) {
      fade.setValue(active ? 1 : 0);
      return;
    }
    Animated.timing(fade, {
      toValue: active ? 1 : 0,
      duration: active ? FADE_IN_MS : FADE_OUT_MS,
      easing: active ? Easing.out(Easing.quad) : Easing.in(Easing.quad),
      useNativeDriver: true,
    }).start();
  }, [active, reduceMotion, fade]);

  const secText = formatMomentSec(row.sec);
  const body = (
    <View style={[styles.row, divided ? styles.rowDivided : null]}>
      {/* 채움 — 행 뒤에 깔리는 절대 레이어. pointerEvents none 이 아니면 행 탭을 먹는다. */}
      <Animated.View
        style={[styles.fill, { opacity: fade }]}
        pointerEvents="none"
      />
      <View style={styles.content}>
        <Text style={styles.sec}>{secText}</Text>
        <Text style={styles.label} numberOfLines={1}>
          {row.label}
        </Text>
        <Text style={[styles.points, active ? styles.pointsActive : null]}>
          {row.pointsText}
        </Text>
      </View>
    </View>
  );

  if (!row.recordId || !onPress) return <View>{body}</View>;
  const recordId = row.recordId;
  return (
    <Pressable
      onPress={() => onPress(recordId)}
      accessibilityRole="button"
      // 상태는 라벨 문자열이 아니라 state 로 — VoiceOver 가 "선택됨"으로 읽는다.
      accessibilityState={{ selected: active }}
      accessibilityLabel={`${secText ? `${secText} ` : ''}${row.label} ${row.pointsText}점 상세 보기`}
    >
      {body}
    </Pressable>
  );
}

export function ResultMomentList({
  rows,
  onRowPress,
  activeRecordId,
  flat,
}: ResultMomentListProps) {
  if (rows.length === 0) return null;
  return (
    <View style={flat ? styles.flat : styles.card}>
      {rows.map((r, i) => (
        <MomentRow
          key={r.recordId ?? `moment-${i}`}
          row={r}
          divided={i > 0 || !!flat}
          active={r.recordId != null && r.recordId === activeRecordId}
          onPress={onRowPress}
        />
      ))}
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
  // 행 자체에는 좌우 여백을 두지 않는다 — 채움 레이어가 행 폭을 꽉 채워야 하는데,
  // Yoga 가 절대 자식에 부모 padding 을 적용하는지가 버전마다 갈려 여백이 남으면
  // 채움이 좌우로 짧아진다. 여백은 아래 content 가 갖는다(시각 차이 0).
  row: {
    minHeight: 52,
    justifyContent: 'center',
  },
  rowDivided: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.divider,
  },
  fill: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: colors.resultChipBg,
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 18,
    gap: 12,
  },
  // 초는 시안에서 브랜드색 굵은 글씨. 폭을 고정해 이름 칸의 시작선이 흔들리지 않게 한다.
  sec: {
    ...typography.resultChip,
    color: colors.brand,
    width: 46,
  },
  label: {
    ...typography.resultChip,
    color: colors.textPrimary,
    flex: 1,
  },
  points: {
    ...typography.resultChip,
    color: colors.textMid,
  },
  // 두 번째 신호 — 휘도 채널(#5A5A5A → #0C0C0C). 색약·저모션에서 채움이 사라져도 남는다.
  pointsActive: { color: colors.textPrimary },
});
