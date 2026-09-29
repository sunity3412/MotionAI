// 소셜 로그인 — 웹 분기 (Phase 38-04, 호스팅 후보 (1) 측정용).
//
// 왜 별도 파일인가: 네이티브 `socialAuth.ts` 는 `@react-native-google-signin` 으로
// idToken 을 받는데, 그 라이브러리의 웹 구현은 `signIn` 에서 PLAY_SERVICES_NOT_AVAILABLE
// 로 throw 한다("Web support is only available to sponsors", 38-RESEARCH Q7 · Pitfall 9).
// 웹에서는 Firebase 가 직접 여는 Google 팝업(`signInWithPopup`/`linkWithPopup`)을 쓴다.
// Metro 는 web 번들에서 이 `.web.ts` 를 `socialAuth.ts` 대신 해석한다 — `src/lib` 은
// `src/app` 밖이라 비플랫폼 판과 짝이 없어도 허용된다(38-RESEARCH Q8, Expo Router
// platform-specific-modules). 호출부(`auth/login.tsx`)는 그대로 outcome 만 본다.
//
// ★리다이렉트 방식 로그인은 쓰지 않는다. S3/CloudFront 도메인에서는
// Safari 16.1+ · Chrome M115+ 의 제3자 저장소 차단으로 동작하지 않는다
// (38-RESEARCH §D, firebase redirect-best-practices). 팝업만.
//
// ★팝업은 클릭 직후 동기적으로 열려야 차단되지 않는다 — 그래서 아래 함수들은
// 팝업 호출 앞에 await 를 두지 않는다.
//
// export 이름·타입은 네이티브 판과 같다(`SocialAuthOutcome`, `SocialAuthResult`,
// `signInWithGoogle`, `signInWithApple`) — 화면 코드가 플랫폼을 몰라도 되게.

import {
  GoogleAuthProvider,
  linkWithPopup,
  signInWithCredential,
  signInWithPopup,
  type User,
} from 'firebase/auth';
import { auth } from './firebase';

/**
 * 로그인 결과 — 의미는 네이티브 `socialAuth.ts` 와 같다.
 *
 * - `linked`      게스트(익명) 계정에 Google 을 붙였다. uid 불변.
 * - `signed_in`   게스트가 아닌 상태에서 로그인했다.
 * - `switched`    그 Google 계정이 이미 다른 uid 에 붙어 있어 그 계정으로 들어갔다.
 *                 게스트 기록은 이전 uid 에 남는다 — 화면이 알린다.
 * - `cancelled`   사용자가 팝업을 닫았다. 오류가 아니다.
 */
export type SocialAuthOutcome =
  | 'linked'
  | 'signed_in'
  | 'switched'
  | 'cancelled';

export type SocialAuthResult = {
  outcome: SocialAuthOutcome;
  user: User | null;
};

// 팝업을 사용자가 닫은 경우. 오류로 올리지 않는다(네이티브 판 규율과 같다).
const CANCEL_CODES = new Set([
  'auth/popup-closed-by-user',
  'auth/cancelled-popup-request',
]);

// 이미 다른 uid 에 붙은 Google 계정 — 네이티브 판 attachOrSignIn 과 같은 두 코드.
const ALREADY_IN_USE_CODES = new Set([
  'auth/credential-already-in-use',
  'auth/email-already-in-use',
]);

function codeOf(e: unknown): string | undefined {
  const code = (e as { code?: unknown })?.code;
  return typeof code === 'string' ? code : undefined;
}

export async function signInWithGoogle(): Promise<SocialAuthResult> {
  const provider = new GoogleAuthProvider();
  const current = auth.currentUser;

  try {
    if (current?.isAnonymous) {
      try {
        const linked = await linkWithPopup(current, provider);
        return { outcome: 'linked', user: linked.user };
      } catch (e) {
        if (!ALREADY_IN_USE_CODES.has(codeOf(e) ?? '')) throw e;
        // 팝업에서 이미 받은 자격증명을 오류 객체에서 꺼내 그 계정으로 들어간다 —
        // 팝업을 한 번 더 띄우지 않는다.
        const credential = GoogleAuthProvider.credentialFromError(
          e as Parameters<typeof GoogleAuthProvider.credentialFromError>[0],
        );
        if (!credential) throw e;
        const signedIn = await signInWithCredential(auth, credential);
        return { outcome: 'switched', user: signedIn.user };
      }
    }

    const signedIn = await signInWithPopup(auth, provider);
    return { outcome: 'signed_in', user: signedIn.user };
  } catch (e) {
    if (CANCEL_CODES.has(codeOf(e) ?? '')) {
      return { outcome: 'cancelled', user: null };
    }
    // `auth/popup-blocked` 등은 FirebaseError 그대로 올린다 — `code` 가 보존되므로
    // 호출 화면이 차단 문구로 매핑할 수 있다.
    throw e;
  }
}

/**
 * Apple 로그인은 웹에서 지원하지 않는다.
 *
 * `expo-apple-authentication` 은 공식 문서상 웹 미지원이고, Firebase 웹의 Apple
 * provider 는 Services ID · 도메인 검증이 따로 필요하다(파일럿 범위 밖).
 */
export async function signInWithApple(): Promise<SocialAuthResult> {
  throw new Error('apple_web_unsupported');
}
