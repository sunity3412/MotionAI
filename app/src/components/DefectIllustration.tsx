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
// 33-G S13/S25 (quick-260731-2jt) — **장면일치 게이트 추가**. 종전에는 motionId
// 하나만 키로 써서 동작당 1장을 그 동작의 **모든 항목**에 공통 부착했다 → 어깨
// 항목 상세에 다리 일러스트 (belle 확인 ② #8·#9·#11 = 승인본 위반). 승인 목업의
// `DETAILS` 는 일러스트를 항목(부위)별 데이터로 두고(`:1047` `:1073` `:1081`),
// 불일치는 슬롯 DOM 자체를 만들지 않는다(`:1114`).
//  · P-2 — 부착 조건 = **항목 부위 토큰 ⊆ 에셋 장면 토큰**. 부분 겹침은 불일치.
//  · P-3 — 투영 공집합(criterion 단독 그룹)은 규칙 앞에서 즉시 미부착.
//  · D-43 — 적합한 에셋이 없으면 **아무것도 안 붙이는 것이 정답**이다. 이 변경으로
//    부착 건수가 주는 것은 결함이 아니라 목적이다.
// 판정 규칙 본체는 `lib/illustrationScene` 가 소유한다 (P-5 — require('*.jpg') 가
// 있는 이 파일은 node --test 로 실행할 수 없어 규칙을 떼어내야 검증 가능). 이
// 파일은 **에셋 맵만** 소유하고 판정을 소비한다. 두 표의 키 목록 일치 = grep 게이트.
//
// §C-4 3번 (quick-260731-plf) — **키가 motionId 에서 에셋 키로 바뀌었다.** 승인 목업의
// legs/shoulder/refonly 시트가 서로 다른 일러스트 값을 두므로 한 동작이 부위별로 여러
// 장을 갖는다. 종전 `Record<motionId, require>` 에는 그 자리가 없었다. 아래 맵의 키는
// 이제 `illustrationScene.ILLUSTRATION_SCENES[].asset` 이며, 33-14 통과 6장은 승인 자산
// 무접촉을 위해 `asset === motionId` 로 남아 파일 경로·바이트가 그대로다. 신규분만
// `{motionId}--{부위}` 형태를 쓴다.
//
// ScoreBreakdownSection 표준형: named export + inline prop 타입 + 헤더 주석 +
// StyleSheet 하단 + theme 토큰만. 하드코딩 색상/간격/반경 0. 이모지 0. 라이트 전용.

import { Image, StyleSheet, View } from 'react-native';

import { illustrationAssetForPart } from '../lib/illustrationScene';
import { radius } from '../theme';

// 검수 PASS 에셋 맵 — RN 정적 require (번들 포함). 키 = 장면 표의 `asset`.
// 항목 추가 = 33-14 게이트 재수행 후에만 (틀린 그림 유입 차단).
const VERIFIED_ILLUSTRATIONS: Record<string, number> = {
  'ref-power-spin': require('../../assets/illustrations/ref-power-spin.jpg'),
  'ref-kip-up': require('../../assets/illustrations/ref-kip-up.jpg'),
  'ref-climb': require('../../assets/illustrations/ref-climb.jpg'),
  'ref-invert': require('../../assets/illustrations/ref-invert.jpg'),
  'ref-foxtop': require('../../assets/illustrations/ref-foxtop.jpg'),
  'ref-foxtop-split': require('../../assets/illustrations/ref-foxtop-split.jpg'),
  // §C-4 3번 (quick-260731-plf) — 어깨·팔 부위별 신규분.
  'ref-power-spin--shoulder': require('../../assets/illustrations/ref-power-spin--shoulder.jpg'),
  'ref-kip-up--shoulder': require('../../assets/illustrations/ref-kip-up--shoulder.jpg'),
  'ref-elbow-twist-sister--arm': require('../../assets/illustrations/ref-elbow-twist-sister--arm.jpg'),
};

export function DefectIllustration({
  motionId,
  partKey,
}: {
  /** mode1 기준 모션 ID. null/미등록 = silent hidden (렌더 0). */
  motionId: string | null | undefined;
  /**
   * 이 항목의 부위 키 (`deductionSheet.regionPartKeyForRecord` — 마커 그룹·부위
   * 칩·부위 시트와 **같은 단위**). 그림 장면과 어긋나면 silent hidden (S13/S25).
   */
  partKey: string | null | undefined;
}) {
  // 장면일치 통과분만 조회 키가 된다 (P-2/P-3). 불일치·미등재·mode3 → null.
  const matched = illustrationAssetForPart(motionId, partKey);
  const source = matched ? VERIFIED_ILLUSTRATIONS[matched] : undefined;
  if (source == null) return null; // 'hidden' — 미검증/불일치는 조용히 생략 (D-15/D-18/D-43)

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
