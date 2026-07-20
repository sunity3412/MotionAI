// design.md §0 기본값 + §3 레이아웃 + §5 컴포넌트 스펙.

export { colors, gradients, sns } from './colors';
export { typography, fontFamily } from './typography';

export const radius = {
  button: 13, // 버튼/입력 (design.md §5-3)
  card: 15, // 카드 (§5-4)
  listItem: 8.58, // 리스트 아이템 카드 (§5-4)
  modal: 20, // 모달/팝업 (§0)
  // quick-260720-hn8 — 실패 알림창 카드/버튼 (Figma node 1:499 실측 30.33 / 9.175)
  dialog: 30,
  dialogButton: 9,
} as const;

export const spacing = {
  screenX: 20, // 화면 좌우 패딩 (§3)
  cardPadding: 16, // 카드 내부 (§3)
} as const;

export const layout = {
  baseWidth: 390, // 기준 프레임 (iPhone 14)
  baseHeight: 844,
  safeAreaTop: 59,
  safeAreaBottom: 34,
  bottomTabHeight: 83,
  ctaWidth: 330, // §5-3 CTA 버튼
  ctaHeight: 54,
  inputHeight: 54, // §5-3-1
  cardBorderWidth: 0.858, // §5-4
  // quick-260720-hn8 — 실패 알림창 (Figma node 1:499 실측). 폭 308.8 은 소형 기기
  // 대응으로 반응형(최대 320), 버튼 폭 98.6/153.7 은 비율(1:1.56)로 재현.
  dialogMaxWidth: 320,
  dialogIconSize: 30, // 30.33
  dialogButtonHeight: 44, // 43.58
  dialogCloseFlex: 1,
  dialogPrimaryFlex: 1.56, // 153.7 / 98.6
} as const;
