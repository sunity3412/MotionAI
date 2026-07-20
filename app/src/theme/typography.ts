// design.md §2 타이포그래피. 단위 pt = RN 숫자값 그대로.
// letterSpacing = 박제 (2026-06-06 belle): iOS 26+ 의 native style 회귀로 음수
// letterSpacing 이 SIGABRT (TestFlight 빌드 9 분석하기 버튼 튕김 root cause).
// design.md 의 -4% (`fontSize * -0.04`) 의도는 일부 손실되지만 crash 회피 우선.
// Pretendard 한글 폰트는 letterSpacing 0 으로도 자연 spacing 정합.
// 추후 iOS 27+ 박제 정합 시 또는 Platform.OS/Version 분기 박제 가능.

// Pretendard ttf는 추후 expo-font로 로드 예정 (plan.md 폰트 작업).
// 로드 전까지 fontFamily 미지정 → 시스템 폰트로 폴백. 로드 후 아래 이름으로 매핑.
export const fontFamily = {
  regular: 'Pretendard-Regular',
  bold: 'Pretendard-Bold',
} as const;

const track = (_size: number) => 0;

export const typography = {
  heading: { fontSize: 30, fontWeight: '700', letterSpacing: track(30) },
  body: { fontSize: 25, fontWeight: '400', letterSpacing: track(25) },
  bodyBold: { fontSize: 25, fontWeight: '700', letterSpacing: track(25) },
  button: { fontSize: 20, fontWeight: '700', letterSpacing: track(20) },
  buttonSecondary: { fontSize: 17, fontWeight: '400', letterSpacing: track(17) },
  sectionTitle: { fontSize: 20, fontWeight: '700', letterSpacing: track(20) },
  listTitle: { fontSize: 18, fontWeight: '700', letterSpacing: track(18) },
  boxLabel: { fontSize: 15, fontWeight: '700', letterSpacing: track(15) },
  caption: { fontSize: 12, fontWeight: '400', letterSpacing: track(12) },
  captionSmall: { fontSize: 10, fontWeight: '400' },
  score: { fontSize: 50, fontWeight: '700' },

  // ── quick-260720-hn8 신설 (Figma node 1:499 `Group 53` 실측) ────────────
  // 영상 선택 실패 알림창(카드형) 전용. fontSize/lineHeight 는 Figma 실측 그대로.
  // letterSpacing 만 위 박제 규칙에 따라 0 — Figma 는 각각 -0.72/-0.52/-0.6 이지만
  // 음수 letterSpacing 은 iOS 26+ 에서 SIGABRT(빌드 9 root cause)라 적용 금지.
  dialogTitle: { fontSize: 18, fontWeight: '700', lineHeight: 25, letterSpacing: track(18) },
  dialogBody: { fontSize: 13, fontWeight: '400', lineHeight: 23, letterSpacing: track(13) },
  dialogButton: { fontSize: 15, fontWeight: '700', lineHeight: 20, letterSpacing: track(15) },
  // 진단용 오류 원문 — 눈에 띄지 않아야 하므로 최소 크기.
  dialogDetail: { fontSize: 11, fontWeight: '400', lineHeight: 15 },
} as const;
