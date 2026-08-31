// 기준 모션 썸네일 (2026-08-31, belle 승인).
//
// 그림의 출처: 정은지 선수 **기준 영상의 실제 프레임**이다. 아이콘·일러스트가 아니라
// 실사인 이유 — (1) 기준 영상이 이미 있어 추가 제작비 0, (2) belle 승인이 "만들어
// 보여주기"가 아니라 "고르기" 한 번으로 끝난다, (3) "정은지 선수처럼"이 제품의 약속이라
// 도전 목록에 그 선수의 실제 자세가 걸리는 편이 강하다.
//
// 순간 선택 규율 (belle 2026-08-31): 처음엔 저장된 execPeakS(동작 완성 순간)를 썼는데
// 11장 중 5장만 통과했다. belle 이 든 기각 사유는 **"민망한 자세" 또는 "사람이 거꾸로"** —
// 우리 데이터에 없는 축이라 나머지 6개는 구간 전체를 펼쳐 belle 이 직접 골랐다.
// 그래서 이 표의 시각은 "동작이 가장 잘 보이는 순간"이 아니라 **belle 이 고른 순간**이다.
// 새 기준 모션이 추가되면 같은 방식으로 물어볼 것 — 자동 선택으로 되돌리지 말 것.
//
// 링크가 아니라 **번들 asset** 인 이유: S3 presigned URL 은 7일이면 만료돼 화면이
// 깨진다(2026-08-24 확대비교에서 같은 함정을 겪었다). require() 된 asset 은 OTA
// 업데이트에도 함께 실려 만료가 없다. 대신 새 기준 모션의 썸네일은 새 빌드가 필요하다 —
// CloudFront 등 공개 URL 경로가 생기면 그때 URL 방식으로 옮길 수 있다.

/** motionId → 썸네일 asset. 없는 동작은 undefined (화면이 회색 자리로 폴백). */
const MOTION_THUMBS: Record<string, number> = {
  'ref-climb': require('../../assets/motion-thumbs/ref-climb.jpg'),
  'ref-combo': require('../../assets/motion-thumbs/ref-combo.jpg'),
  'ref-elbow-twist-sister': require('../../assets/motion-thumbs/ref-elbow-twist-sister.jpg'),
  'ref-foxtop': require('../../assets/motion-thumbs/ref-foxtop.jpg'),
  'ref-foxtop-split': require('../../assets/motion-thumbs/ref-foxtop-split.jpg'),
  'ref-invert': require('../../assets/motion-thumbs/ref-invert.jpg'),
  'ref-kip-up': require('../../assets/motion-thumbs/ref-kip-up.jpg'),
  'ref-pdshape': require('../../assets/motion-thumbs/ref-pdshape.jpg'),
  'ref-peter-pan': require('../../assets/motion-thumbs/ref-peter-pan.jpg'),
  'ref-power-spin': require('../../assets/motion-thumbs/ref-power-spin.jpg'),
  'ref-sideway-spin': require('../../assets/motion-thumbs/ref-sideway-spin.jpg'),
};

/**
 * 기준 모션 썸네일 asset | null.
 *
 * 등재되지 않은 motionId(새로 추가된 기준 모션)는 null 을 돌려주고, 화면은 종전의
 * 회색 자리를 그대로 그린다 — 그림이 없다고 화면이 깨지지 않는다(fail-safe).
 */
export function motionThumb(motionId: string): number | null {
  return MOTION_THUMBS[motionId] ?? null;
}
