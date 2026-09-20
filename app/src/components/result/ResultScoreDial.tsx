// 분석 결과 점수 원 — 빨강 헤더 곡선 위에 걸치는 흰 원반 + 진행 호 (belle 09-08 시안).
//
// 치수는 피그마가 내보낸 SVG 원문에서 그대로 가져왔다 (눈대중 0):
//   원반  254:683 — r 146.312 / 지름 292.62px, 흰색
//         그림자  offset(7.164, 7.164) · blur stdDeviation 11.929 · rgba(4,0,0,0.2)
//   진행 호 254:685 — stroke-width 7.9632, round cap, 중심 반지름 118.9px
//         (바운딩 박스 **세로** 237.775px ÷ 2 = 118.89, 렌더 원피팅도 118.95 — 원반과 동심)
//         ★ 이전 값 113.7 의 근거 "stroke bbox 235.4 의 절반에서 반굵기를 뺀 값" 은 틀렸다.
//         235.4 는 259.8° 에서 잘린 호의 **가로 폭**이지 지름이 아니다 — 호가 왼쪽 아래를
//         못 채워 가로가 세로보다 좁고, 가로로 재면 반지름이 작게 나온다 (260909-ji1).
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
  arcR: 118.9 * K, // 99.3 호 중심 반지름
  arcW: 7.9632 * K, // 6.65 호 굵기
  shadowDx: 7.16368 * K, // 5.98
  shadowDy: 7.16368 * K,
  shadowBlur: 11.9288 * K, // 9.96
  // 숫자·라벨은 **시안 실측 위치에 못박는다**. 흐름 배치로 두면 글자 라인박스의
  // 여백(디센더 공간)이 더해져 둘 사이가 시안보다 30pt 넘게 벌어졌다 — 실측 확인.
  // 값은 시안 **잉크** 박스의 세로 중심(원 윗변 기준 px → pt):
  //   '75'    잉크 102.0..165.4px → 중심 133.7px → 111.6pt
  //   'Today' 잉크 181.1..206.7px → 중심 193.9px → 161.9pt
  scoreCenterY: 133.7 * K, // 111.6
  labelCenterY: 193.9 * K, // 161.9
} as const;

// ── 라인박스 ↔ 잉크 보정 (260909-ji1) ─────────────────────────────────────────
// 이전 구현은 위 잉크 중심에 **라인박스** 중심을 맞췄다. 그런데 잉크는 라인박스 가운데
// 있지 않다 — 숫자는 위쪽에, 'Today' 는 디센더('y') 때문에 아래쪽에 앉는다. 그래서
// 숫자↔Today 잉크 간격이 시안 50.3pt 인데 61.5pt 로 벌어졌다(09-09 대조 +9.7).
//
// 번들 Pretendard 실측(em, 어센더 선 기준. hhea asc 0.952 / desc 0.241 / lineGap 0):
//   자연 라인 = 1.193em, 그 중심 0.597
//   '75'(Bold)       잉크 0.245..0.962 → 중심 0.604 → 자연 중심에서 +0.007em
//   'Today'(Regular) 잉크 0.245..1.151 → 중심 0.698 → 자연 중심에서 +0.101em
//
// RN iOS 는 lineHeight ≥ 폰트 자연 라인일 때만 자연 라인을 라인박스 가운데 놓는다
// (RCTApplyBaselineOffset). 그보다 작으면 아래 정렬되고 위가 잘린다 — 이전 SCORE_LH 1.0
// 이 그 경우라 숫자 잉크가 6.7pt 위로 떴다. 그래서 둘 다 1.2(≥1.193)로 두어 "자연 라인
// 중심 = 라인박스 중심" 을 성립시킨 뒤, 잉크 중심을 자연 중심에서 위 offset 만큼 되돌린다:
//   top = 잉크중심 − 라인박스/2 − offset × fontSize
// 라인박스 높이를 명시하는 이유는 그대로다 — 기본값에 의존하면 기기·폰트마다 어긋난다.
const SCORE_LH = 1.2;
const LABEL_LH = 1.2;
const SCORE_INK_OFFSET = 0.007;
const LABEL_INK_OFFSET = 0.101;

export interface ResultScoreDialProps {
  /** 0~100. 벗어나면 잘라 쓴다. */
  score: number;
  /** 숫자 아래 한 줄. 시안은 'Today'. */
  label: string;
  accessibilityLabel?: string;
  /** belle D-08 — 기준 미보유/저신뢰. 숫자도 진행 호도 그리지 않고 안내문만 남긴다.
   *  원반 기하(지름·그림자·헤더 곡선을 덮는 위치)는 그대로 쓴다 — 치수를 복제하면
   *  다음 시안 갱신에서 어긋나고, 빈 자리가 곡선 경계에 걸쳐 고장처럼 보인다. */
  suppressed?: boolean;
  /** suppressed 일 때 원반 안에 들어갈 안내문. */
  suppressedCopy?: string;
}

export function ResultScoreDial({
  score,
  label,
  accessibilityLabel,
  suppressed = false,
  suppressedCopy,
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
      {suppressed ? (
        /* D-08 — 호도 숫자도 없다. 숫자만 지우면 호 길이가 점수를 그대로 그린다. */
        <View style={[styles.suppressed, { paddingHorizontal: size * 0.12 }]}>
          <Text style={styles.suppressedTitle}>기준 없음</Text>
          {suppressedCopy ? (
            <Text style={styles.suppressedBody} lineBreakStrategyIOS="hangul-word">
              {suppressedCopy}
            </Text>
          ) : null}
        </View>
      ) : (
        <>
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
              (typography.resultDialScore.fontSize * SCORE_LH * s) / 2 -
              typography.resultDialScore.fontSize * SCORE_INK_OFFSET * s,
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
              (typography.resultDialLabel.fontSize * LABEL_LH * s) / 2 -
              typography.resultDialLabel.fontSize * LABEL_INK_OFFSET * s,
          },
        ]}
        pointerEvents="none"
      >
        {label}
      </Text>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  // D-08 억제 상태 — 원반 안을 채운다. 배경은 원반 그대로(흰 cardBg)라 헤더 곡선을
  // 덮는 시안 구조가 유지되고, 색은 요약 카드의 주의 박스 토큰을 그대로 쓴다.
  suppressed: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
  },
  suppressedTitle: {
    ...typography.resultWarnTitle,
    color: colors.resultWarnTitle,
    textAlign: 'center',
    marginBottom: 8,
  },
  suppressedBody: {
    ...typography.resultSub,
    color: colors.resultWarnBody,
    textAlign: 'center',
  },
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
