// 분석 결과 점수 원 — 빨강 헤더 곡선 위에 걸치는 흰 원반 + 진행 호 (belle 09-08 시안).
//
// 치수는 피그마가 내보낸 SVG 원문에서 그대로 가져왔다 (눈대중 0):
//   원반  254:683 — r 146.312 / 지름 292.62px, 흰색
//         그림자  offset(7.164, 7.164) · blur stdDeviation 11.929 · rgba(4,0,0,0.2)
//   진행 호 254:685 — stroke-width 7.9632, round cap, 중심 반지름 113.7px
//         (노드 stroke bbox 235.4px 의 절반에서 반굵기를 뺀 값 — 원반과 동심)
//
// 호의 각도: 시안은 위(-90°)에서 시계방향으로 259.8° 그려져 있고 점수는 75 였다.
// 360° × 0.75 = 270° 와 거의 같아, **위에서 시작해 점수 비율만큼 시계방향**으로 읽는다.
// (시안의 숫자는 임의값이다 — belle 09-08 "화면만 하면돼 임의 숫자임".)
//
// 색: 호는 브랜드 #FF4B33. 시안 SVG 의 stroke 는 #E94D37 이었으나 쓰지 않는다
// (belle 09-08 판정 — colors.ts result* 토큰 주석 참조).
import { StyleSheet, Text, View, useWindowDimensions } from 'react-native';
import Svg, { Circle } from 'react-native-svg';

import { colors, typography } from '../../theme';

const DESIGN_W = 390;
const K = 390 / 467.206; // 시안 px → pt

// 시안 px → pt (미확대 기준).
const D = {
  size: 292.62 * K, // 244.3 원반 지름
  arcR: 113.7 * K, // 94.9 호 중심 반지름
  arcW: 7.9632 * K, // 6.65 호 굵기
  shadowDx: 7.16368 * K, // 5.98
  shadowDy: 7.16368 * K,
  shadowBlur: 11.9288 * K, // 9.96
  // 숫자·라벨은 **시안 실측 위치에 못박는다**. 흐름 배치로 두면 글자 라인박스의
  // 여백(디센더 공간)이 더해져 둘 사이가 시안보다 30pt 넘게 벌어졌다 — 실측 확인.
  // 값은 시안 잉크 박스의 세로 중심(원 윗변 기준 px → pt):
  //   '75'    잉크 102.0..165.4px → 중심 133.7px → 111.6pt
  //   'Today' 잉크 181.1..206.7px → 중심 193.9px → 161.9pt
  scoreCenterY: 133.7 * K, // 111.6
  labelCenterY: 193.9 * K, // 161.9
} as const;

// 라인박스 높이 — 중심 정렬 계산에 쓰므로 명시한다(기본값에 의존하면 기기·폰트마다
// 어긋난다). 숫자는 디센더가 없어 1.0em, 라벨은 'y' 가 있어 1.2em.
const SCORE_LH = 1.0;
const LABEL_LH = 1.2;

export interface ResultScoreDialProps {
  /** 0~100. 벗어나면 잘라 쓴다. */
  score: number;
  /** 숫자 아래 한 줄. 시안은 'Today'. */
  label: string;
  accessibilityLabel?: string;
}

export function ResultScoreDial({
  score,
  label,
  accessibilityLabel,
}: ResultScoreDialProps) {
  const { width } = useWindowDimensions();
  const s = width / DESIGN_W;

  const size = D.size * s;
  const r = D.arcR * s;
  const strokeW = D.arcW * s;
  const c = size / 2;
  const circumference = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, Number.isFinite(score) ? score : 0)) / 100;
  // 위(12시)에서 시작해 시계방향. SVG 원의 0° 는 3시라 -90° 회전한다.
  const dash = circumference * pct;

  return (
    <View
      style={[
        styles.wrap,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          shadowOffset: { width: D.shadowDx * s, height: D.shadowDy * s },
          shadowRadius: D.shadowBlur * s,
        },
      ]}
      accessibilityRole="image"
      accessibilityLabel={accessibilityLabel ?? `${Math.round(score)}점 ${label}`}
    >
      <Svg width={size} height={size} style={StyleSheet.absoluteFill}>
        <Circle
          cx={c}
          cy={c}
          r={r}
          stroke={colors.brand}
          strokeWidth={strokeW}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
          fill="none"
          transform={`rotate(-90 ${c} ${c})`}
        />
      </Svg>
      <Text
        style={[
          styles.score,
          {
            fontSize: typography.resultDialScore.fontSize * s,
            lineHeight: typography.resultDialScore.fontSize * SCORE_LH * s,
            top:
              D.scoreCenterY * s -
              (typography.resultDialScore.fontSize * SCORE_LH * s) / 2,
          },
        ]}
        pointerEvents="none"
      >
        {Math.round(pct * 100)}
      </Text>
      <Text
        style={[
          styles.label,
          {
            fontSize: typography.resultDialLabel.fontSize * s,
            lineHeight: typography.resultDialLabel.fontSize * LABEL_LH * s,
            top:
              D.labelCenterY * s -
              (typography.resultDialLabel.fontSize * LABEL_LH * s) / 2,
          },
        ]}
        pointerEvents="none"
      >
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: colors.cardBg,
    alignItems: 'center',
    justifyContent: 'center',
    // 시안 그림자 — feDropShadow(7.16, 7.16, blur 11.93, rgba(4,0,0,0.2)).
    // RN 은 색·불투명도를 나눠 받으므로 alpha 를 shadowOpacity 로 옮긴다.
    shadowColor: colors.textPrimary,
    shadowOpacity: 0.2,
    elevation: 6,
  },
  score: {
    ...typography.resultDialScore,
    position: 'absolute',
    left: 0,
    right: 0,
    color: colors.brand,
    textAlign: 'center',
  },
  label: {
    ...typography.resultDialLabel,
    position: 'absolute',
    left: 0,
    right: 0,
    color: colors.brand,
    textAlign: 'center',
  },
});
