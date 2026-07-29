// 결함 일러스트 (A-7, 33-14 — D-15).
//
// 근거:
//  · D-15 — 일러스트는 검수 통과본만 배선한다. VERIFIED_ILLUSTRATIONS 에 없는
//    동작은 'hidden' = 아무것도 렌더하지 않는다 (Alert/Toast/에러 배너 0,
//    ReferenceCornerSection 표준의 조용한 폴백). 틀린 그림은 없는 것보다 나쁘다.
//  · D-18 — 등록본 = 33-14 검수 게이트 4종(익명·자세 충실·가이드 선·해부학)
//    육안 전수 통과본만. 미완 4동작(peter-pan, elbow-twist-sister, pdshape,
//    sideway-spin)은 의도된 부재 — 33-14-SUMMARY 검수 표가 기록 원본.
//  · D-05 — 일러스트는 말을 대체한다. 캡션/라벨 텍스트를 덧붙이지 않는다.
//  · 승인 불변식 ② (33-11, 장면-일러스트 일치 게이트) — 각 에셋의 입력은 해당
//    동작 기준 영상의 국면 완성 프레임 (33-A1 표 국면 데이터 키잉). 생성 경로 =
//    gemini-3-pro-image 이미지 투 이미지, 스타일 앵커 = 7R 후보 1 경로.
//  · 키 = reference 라이브러리 motionId (동작명 코드 분기 0 — 데이터 맵).
//    mode3/미등재 동작은 motionId 부재 → 자동 hidden (fail-closed).
//
// ScoreBreakdownSection 표준형: named export + inline prop 타입 + 헤더 주석 +
// StyleSheet 하단 + theme 토큰만. 하드코딩 색상/간격/반경 0. 이모지 0. 라이트 전용.

import { Image, StyleSheet, View } from 'react-native';

import { radius } from '../theme';

// 검수 PASS 에셋 맵 — RN 정적 require (번들 포함). 항목 추가 = 33-14 게이트
// 재수행 후에만 (틀린 그림 유입 차단).
const VERIFIED_ILLUSTRATIONS: Record<string, number> = {
  'ref-power-spin': require('../../assets/illustrations/ref-power-spin.jpg'),
  'ref-kip-up': require('../../assets/illustrations/ref-kip-up.jpg'),
  'ref-climb': require('../../assets/illustrations/ref-climb.jpg'),
  'ref-invert': require('../../assets/illustrations/ref-invert.jpg'),
  'ref-foxtop': require('../../assets/illustrations/ref-foxtop.jpg'),
  'ref-foxtop-split': require('../../assets/illustrations/ref-foxtop-split.jpg'),
};

export function DefectIllustration({
  motionId,
}: {
  /** mode1 기준 모션 ID. null/미등록 = silent hidden (렌더 0). */
  motionId: string | null | undefined;
}) {
  const source = motionId ? VERIFIED_ILLUSTRATIONS[motionId] : undefined;
  if (source == null) return null; // 'hidden' — 미검증 동작은 조용히 생략 (D-15/D-18)

  return (
    <View style={styles.card}>
      <Image
        source={source}
        style={styles.image}
        resizeMode="cover"
        accessibilityLabel="목표 자세 일러스트"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    width: '100%',
    borderRadius: radius.card,
    overflow: 'hidden',
  },
  // 에셋 원본 비율 3:4 (720x964) — cover 크롭 없이 그대로 앉게 비율 고정.
  image: {
    width: '100%',
    aspectRatio: 3 / 4,
  },
});
