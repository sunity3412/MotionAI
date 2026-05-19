// design.md §2 타이포그래피. 단위 pt = RN 숫자값 그대로.
// letterSpacing = fontSize × -0.04 (design.md 레터스페이싱 패턴).

// Pretendard ttf는 추후 expo-font로 로드 예정 (plan.md 폰트 작업).
// 로드 전까지 fontFamily 미지정 → 시스템 폰트로 폴백. 로드 후 아래 이름으로 매핑.
export const fontFamily = {
  regular: 'Pretendard-Regular',
  bold: 'Pretendard-Bold',
} as const;

const track = (size: number) => size * -0.04;

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
} as const;
