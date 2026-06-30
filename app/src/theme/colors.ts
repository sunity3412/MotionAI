// design.md §4 컬러 시스템 — 피그마 추출 확정값. 하드코딩 금지, 이 토큰만 사용.

export const colors = {
  // 브랜드
  brand: '#FF4B33',
  brandGradientStart: '#FFB5AB',
  brandGradientEnd: '#FF604B',
  brandButtonDisabled: '#FFB7AD',
  brandOverlay: 'rgba(255,75,51,0.4)',
  brandTint: 'rgba(255,75,51,0.15)',

  // 배경
  bg: '#FFFFFF',
  cardBg: '#FFFFFF',

  // 텍스트
  textPrimary: '#0C0C0C',
  textWhite: '#FFFFFF',
  textSecondary: '#ACACAC',
  textDisabled: '#B1B6BE',
  textBrand: '#FF4B33',

  // 상태 (오류는 의도적으로 틸 — 브랜드 레드와 혼동 방지)
  inputValid: '#FF4B33',
  inputError: '#54B8CD',
  labelRequired: '#54B8CD',
  labelOptional: '#B1B6BE',

  // UI 요소
  divider: '#D9D9D9',
  inputBorder: '#B1B6BE',
  tabActive: '#FF4B33',
  tabInactive: '#A5A5A5',
  highlight: '#006FFD',
  neutralDark: '#1F2024',

  // ── Phase 12 신설 토큰 (UI-SPEC §1) ──────────────────────────────────
  // 기존 brand #FF4B33 는 변경 0 (CLAUDE.md §4 / D-12-U5). 신규 키만 추가.
  // Phase 9 카드 / KeypointOverlay / ForcePatternCard / 영상 카드 전용.
  brandSoft: '#FFD9D2', // Phase 9 작은 카드 chip 배경
  brandBg: '#FFE5E0', // 옥타곤 outer ring 톤
  softBg: '#F5F5F5', // jointHint chip 배경
  estimateGray: '#B0B0B0', // 저신뢰 "추정 N°" 컬러
  progressGreen: '#22B47A', // mode3_progress +N점 발전
  progressRed: '#E64545', // mode3_progress -N점 후퇴
  warnAmber: '#E6A300', // ⚠ occlusion badge
  videoBg: '#2A2A2A', // 영상 카드 배경 (design.md §5-1 다크 예외)
  textHi: '#1A1A1A', // Phase 12 본문
  textMid: '#5A5A5A', // Phase 12 sub 본문
  textLo: '#888888', // Phase 12 hint / footer
  border: '#E0E0E0', // Phase 12 카드 테두리
  trackBg: '#EBEBEB', // Phase 12 점수 트랙 배경

  // ── Phase 4 신설 토큰 (04-UI-SPEC §Color) ─────────────────────────────
  // alias 방식 — 기존 토큰 hex 복사 (softBg / neutralDark / brand / textSecondary
  // / warnAmber 의 의미 alias). 라이트 배경 + 다크 배경 금지 (CLAUDE.md §4).
  viewer3dBg: '#F5F5F5', // 3D 캔버스 배경 (softBg alias)
  viewer3dBone: '#1F2024', // stick figure 뼈대 (neutralDark alias)
  viewer3dJoint: '#FF4B33', // IPSF 위반 관절 highlight (brand alias)
  viewer3dJointNormal: '#ACACAC', // 정상 관절 점 (textSecondary alias)
  accuracyLimitBg: '#F5F5F5', // 정확도 제한 배지 배경 (softBg alias)
  accuracyLimitText: '#E6A300', // 정확도 제한 배지 텍스트 (warnAmber alias)

  // ── Phase 10 신설 토큰 (10-UI-SPEC §Color, 2026-06-30) ────────────────
  // 부상 위험 SafetyFlag 경고 배너 amber tint 배경. 기존 warnAmber(#E6A300)
  // 텍스트 톤과 짝. brand #FF4B33 변경 0 (CLAUDE.md §4). 라이트 배경 유지.
  warnAmberBg: '#FFF6E5', // 부상 위험 경고 배너 배경 (D-08)
} as const;

// 그라디언트 (expo-linear-gradient의 colors prop 등에 사용)
export const gradients = {
  // linear-gradient(111.41deg, #FFB1A6 11.93%, #FF6651 89.96%)
  brandButton: {
    colors: ['#FFB1A6', '#FF6651'] as const,
    locations: [0.1193, 0.8996] as const,
  },
  // linear-gradient(94.36deg, #FFB5AB 1.74%, #FF604B 90.6%)
  homeTop: {
    colors: ['#FFB5AB', '#FF604B'] as const,
    locations: [0.0174, 0.906] as const,
  },
  // linear-gradient(to-bottom, #FFFFFF, #FFF0EE)
  homeCard: {
    colors: ['#FFFFFF', '#FFF0EE'] as const,
  },
} as const;

// SNS 버튼 (design.md §4)
export const sns = {
  kakao: { bg: '#FEE500', text: '#0C0C0C' },
  naver: { bg: '#03C75A', text: '#FFFFFF' },
  google: { bg: '#FFFFFF', border: '#B1B6BE', text: '#0C0C0C' },
  apple: { bg: '#000000', text: '#FFFFFF' },
} as const;
