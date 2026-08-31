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

// 실제로 **배선된** provider (2026-08-31). SOCIAL_PROVIDERS 는 Figma 원안 4종을
// 그대로 보존하는 카탈로그이고, 화면은 아래 목록만 렌더한다.
//
// 왜 가르나: 배선 안 된 버튼을 그려 두면 누를 때마다 "아직 연결 중이에요"가 뜬다 —
// 눌러도 아무 일 없는 표시를 남기지 않는다는 기존 규율(Phase 33 "표시마다 답 or
// 없앰", 36-CONTEXT D-08 의 이메일 링크 미렌더와 같은 판단)과 어긋난다.
// belle 2026-08-31 결정: 카카오·네이버는 출시 준비 때 붙인다(각자 개발자 콘솔 등록 +
// Firebase 미지원이라 커스텀 토큰 교환 필요). 그때 이 배열에 id 두 개만 되돌리면
// 화면은 자동으로 4개가 된다 — Figma 치수·색은 위 카탈로그에 그대로 남아 있다.
//
// 순서는 Figma 원안(카카오·네이버·Google·Apple)의 상대 순서를 유지한다. 두 버튼은
// 크기·노출이 동일하므로 Apple 의 "동등하게 노출" 요건도 충족한다 — 나중에 4개로
// 돌아가도 Apple 이 화면 밖으로 밀리지 않는지 확인할 것.
export const WIRED_PROVIDER_IDS: readonly SocialProviderId[] = ['google', 'apple'];

export const WIRED_SOCIAL_PROVIDERS: readonly SocialProvider[] =
  SOCIAL_PROVIDERS.filter((p) => WIRED_PROVIDER_IDS.includes(p.id));

export function isWiredProvider(id: SocialProviderId): boolean {
  return WIRED_PROVIDER_IDS.includes(id);
}
