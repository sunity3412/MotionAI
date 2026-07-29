// design.md §2 타이포그래피. 단위 pt = RN 숫자값 그대로.
// letterSpacing = 박제 (2026-06-06 belle): iOS 26+ 의 native style 회귀로 음수
// letterSpacing 이 SIGABRT (TestFlight 빌드 9 분석하기 버튼 튕김 root cause).
// design.md 의 -4% (`fontSize * -0.04`) 의도는 일부 손실되지만 crash 회피 우선.
// Pretendard 한글 폰트는 letterSpacing 0 으로도 자연 spacing 정합.
// 추후 iOS 27+ 박제 정합 시 또는 Platform.OS/Version 분기 박제 가능.

// 32-12 (D-05) — Pretendard 실제 로드. 공식 배포본(github.com/orioncactus/pretendard
// releases v1.3.9)의 static TTF 4웨이트를 app/assets/fonts 에 번들하고 _layout 의
// expo-font useFonts 로 로드한다(라이선스 SIL OFL — 무료·상용 OK). 아래 fontFamily
// 이름은 _layout 의 useFonts 키와 정확히 일치해야 한다(불일치 시 시스템 폰트 폴백).
// 각 토큰에 weight→family 매핑을 붙여 앱 전역이 Pretendard 로 렌더된다. fontWeight 는
// 유지 — 폰트 로드 실패 시 시스템 폰트 + weight 로 graceful 폴백된다(가짜 굵기 방지).
export const fontFamily = {
  regular: 'Pretendard-Regular',
  medium: 'Pretendard-Medium',
  semibold: 'Pretendard-SemiBold',
  bold: 'Pretendard-Bold',
} as const;

const track = (_size: number) => 0;

export const typography = {
  heading: { fontSize: 30, fontWeight: '700', fontFamily: fontFamily.bold, letterSpacing: track(30) },
  body: { fontSize: 25, fontWeight: '400', fontFamily: fontFamily.regular, letterSpacing: track(25) },
  bodyBold: { fontSize: 25, fontWeight: '700', fontFamily: fontFamily.bold, letterSpacing: track(25) },
  button: { fontSize: 20, fontWeight: '700', fontFamily: fontFamily.bold, letterSpacing: track(20) },
  buttonSecondary: { fontSize: 17, fontWeight: '400', fontFamily: fontFamily.regular, letterSpacing: track(17) },
  sectionTitle: { fontSize: 20, fontWeight: '700', fontFamily: fontFamily.bold, letterSpacing: track(20) },
  listTitle: { fontSize: 18, fontWeight: '700', fontFamily: fontFamily.bold, letterSpacing: track(18) },
  boxLabel: { fontSize: 15, fontWeight: '700', fontFamily: fontFamily.bold, letterSpacing: track(15) },
  caption: { fontSize: 12, fontWeight: '400', fontFamily: fontFamily.regular, letterSpacing: track(12) },
  captionSmall: { fontSize: 10, fontWeight: '400', fontFamily: fontFamily.regular },
  score: { fontSize: 50, fontWeight: '700', fontFamily: fontFamily.bold },

  // ── quick-260720-hn8 신설 (Figma node 1:499 `Group 53` 실측) ────────────
  // 영상 선택 실패 알림창(카드형) 전용. fontSize/lineHeight 는 Figma 실측 그대로.
  // letterSpacing 만 위 박제 규칙에 따라 0 — Figma 는 각각 -0.72/-0.52/-0.6 이지만
  // 음수 letterSpacing 은 iOS 26+ 에서 SIGABRT(빌드 9 root cause)라 적용 금지.
  dialogTitle: { fontSize: 18, fontWeight: '700', fontFamily: fontFamily.bold, lineHeight: 25, letterSpacing: track(18) },
  dialogBody: { fontSize: 13, fontWeight: '400', fontFamily: fontFamily.regular, lineHeight: 23, letterSpacing: track(13) },
  dialogButton: { fontSize: 15, fontWeight: '700', fontFamily: fontFamily.bold, lineHeight: 20, letterSpacing: track(15) },
  // 진단용 오류 원문 — 눈에 띄지 않아야 하므로 최소 크기.
  dialogDetail: { fontSize: 11, fontWeight: '400', fontFamily: fontFamily.regular, lineHeight: 15 },

  // ── Phase 32 (32-07 D-05) 결과 화면 강조 토큰 (E2 스케일, 하한 17) ───────
  // 출처: 32-GATE-DECISIONS.md D-05 = "E2(강, 하한 17)" + mockups/emphasis-tokens.md
  // (index.html ⑤ 탭 승인본). 문제 = 현행 12~20 사이 본문용 중간 단계 부재 →
  // 화면 대부분이 caption(12)/boxLabel(15)로 조판 = belle "전반이 너무 작음".
  // 해법 = 옵션 b(신규 단계 추가만, 전역값 상향 아님 — 전 화면 파급 리스크 통제).
  // 전역 토큰(caption 12 등) 무변경 — 결과 화면부터 적용 후 32-11/32-12 에서 확산.
  //
  // 하한 17: belle "폰트 젤 작은 것들 정말 너무 작음"(로딩 화면) 직격. emphasis-tokens
  // E2 열의 badge 16 은 이 하한을 위반하므로 17 로 올려 채택 (사유 = 게이트 확정 하한).
  // lineHeight = fontSize×1.3 이상 (Pitfall 3 — 줄겹침 방지). letterSpacing = track()=0
  // (음수 letterSpacing 은 iOS 26+ SIGABRT :2-6). 강조 강(800)은 우리가 배포하는
  // 폰트 파일(Pretendard SemiBold/Bold)에 맞춰 매핑 — 크기+웨이트 계층으로 강조.
  // 32-12 (D-05) — Pretendard 실제 로드 완료: 아래 토큰도 weight→family 매핑 적용.
  badge: { fontSize: 17, fontWeight: '600', fontFamily: fontFamily.semibold, lineHeight: 23, letterSpacing: track(17) }, // 측정 수치 소형 배지(D-09)
  bodySm: { fontSize: 19, fontWeight: '400', fontFamily: fontFamily.regular, lineHeight: 25, letterSpacing: track(19) }, // 왜/보조 본문
  bodyMd: { fontSize: 21, fontWeight: '400', fontFamily: fontFamily.regular, lineHeight: 28, letterSpacing: track(21) }, // 기본 본문
  bodyMdBold: { fontSize: 21, fontWeight: '700', fontFamily: fontFamily.bold, lineHeight: 28, letterSpacing: track(21) }, // 행동 큐(외부 초점)
  bodyLg: { fontSize: 24, fontWeight: '700', fontFamily: fontFamily.bold, lineHeight: 32, letterSpacing: track(24) }, // 카드 헤드라인(몸 말/상태)
  title: { fontSize: 26, fontWeight: '700', fontFamily: fontFamily.bold, lineHeight: 34, letterSpacing: track(26) }, // 섹션 타이틀
  headline: { fontSize: 30, fontWeight: '700', fontFamily: fontFamily.bold, lineHeight: 39, letterSpacing: track(30) }, // 요약 카드 대표 문장

  // ── 33-15 (D-16) 수치 강등 토큰 ─────────────────────────────────────────
  // 감점/점수 숫자(−17.4·−20·51점)는 헤드라인이 아니라 근거다 — 점수 계산 내역·
  // 심사 코너·근거 박스의 숫자는 headline 스케일(bodyLg 24↑) 아래 badge 스케일
  // (D-05 하한 17)로 고정한다. bold 유지(숫자 가독), 크기만 강등. letterSpacing 은
  // track()=0 박제 유지 (음수 = iOS 26+ SIGABRT, :2-6).
  metricNumber: { fontSize: 17, fontWeight: '700', fontFamily: fontFamily.bold, lineHeight: 23, letterSpacing: track(17) },

  // ── 33-15 (D-17/D-22) OctagonScore 중앙 수치 토큰화 ─────────────────────
  // 인라인 fontSize 52/36 하드코딩 제거(타입 스케일 전수 점검) — 값 불변 토큰화.
  // 점수 게이지는 D-09 로 이미 상세 영역으로 위치 강등된 채점 표면이라 크기 유지,
  // fontFamily 만 Pretendard 정합(시스템 폰트 잔재 해소).
  scoreGaugeLg: { fontSize: 52, fontWeight: '700', fontFamily: fontFamily.bold },
  scoreGaugeSm: { fontSize: 36, fontWeight: '700', fontFamily: fontFamily.bold },
} as const;
