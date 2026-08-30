// 소셜 로그인 provider 메타 (Phase 36).
//
// 실제 아이콘 그림은 components/SocialIcon.tsx 가 소유한다 (벡터 3 + PNG 1).
// 여기에는 버튼 색과 Figma 실측 치수만 둔다.
//
// 버튼 배경/글자색은 src/theme 의 `sns` 토큰을 그대로 쓴다 — Figma 실측
// (#FEE500 / #03C75A / #FFFFFF / #000000) 과 **정확히 일치**함을 픽셀로 확인했다.
//
// 아이콘 치수가 화면마다 다른 이유: Figma 가 가입(전폭 버튼)과 로그인(정사각 타일)에서
// 서로 다른 크기를 쓴다. 비율은 두 곳 모두 원본과 같아 왜곡 없음.

import { sns } from '../theme';

export type SocialProviderId = 'kakao' | 'naver' | 'google' | 'apple';

export type SocialProvider = {
  id: SocialProviderId;
  /** 전폭 버튼(가입 1:961) 배경/글자. google 만 테두리가 있다. */
  bg: string;
  fg: string;
  border?: string;
  /** 가입 화면 전폭 버튼 안 아이콘 (Figma 실측) */
  buttonIcon: { width: number; height: number };
  /** 로그인 화면 정사각 타일 안 아이콘 (Figma 실측) */
  tileIcon: { width: number; height: number };
};

export const SOCIAL_PROVIDERS: readonly SocialProvider[] = [
  {
    id: 'kakao',
    bg: sns.kakao.bg,
    fg: sns.kakao.text,
    buttonIcon: { width: 20.1, height: 17.2 },
    tileIcon: { width: 23.7, height: 20.4 },
  },
  {
    id: 'naver',
    bg: sns.naver.bg,
    fg: sns.naver.text,
    buttonIcon: { width: 14.3, height: 14.3 },
    tileIcon: { width: 18.6, height: 18.5 },
  },
  {
    id: 'google',
    bg: sns.google.bg,
    fg: sns.google.text,
    border: sns.google.border,
    buttonIcon: { width: 19.8, height: 20.4 },
    tileIcon: { width: 25.5, height: 26.3 },
  },
  {
    id: 'apple',
    bg: sns.apple.bg,
    fg: sns.apple.text,
    buttonIcon: { width: 14.3, height: 17.2 },
    tileIcon: { width: 18.6, height: 22.2 },
  },
] as const;
