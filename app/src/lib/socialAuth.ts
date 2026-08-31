// 소셜 로그인 (Phase 36-02~05).
//
// 이 모듈이 지는 책임 하나: **provider 자격증명을 받아 Firebase 계정으로 바꾸고,
// 게스트였으면 그 계정을 승계시킨다.** 화면은 결과만 보고 문구를 고른다.
//
// 게스트 승계가 핵심이다. 익명 계정에 자격증명을 link 하면 **uid 가 그대로 유지**되므로
// `users/{uid}/analyses` 에 쌓인 기록이 하나도 사라지지 않는다. 새로 signIn 하면 uid 가
// 바뀌어 기록이 끊긴다 — 그래서 게스트 상태에서는 반드시 link 를 먼저 시도한다.
//
// 클라이언트 ID 는 비밀값이 아니다(앱 번들에 그대로 실린다). Firebase 프로젝트에
// 묶인 고정값이라 env 로 빼지 않고 여기 둔다 — app.json 의 `iosUrlScheme` 과
// **같은 값을 써야 하므로** 한 곳에서 보이는 편이 안전하다.

import * as AppleAuthentication from 'expo-apple-authentication';
import * as Crypto from 'expo-crypto';
import {
  GoogleSignin,
  isErrorWithCode,
  statusCodes,
} from '@react-native-google-signin/google-signin';
import {
  GoogleAuthProvider,
  OAuthProvider,
  linkWithCredential,
  signInWithCredential,
  updateProfile,
  type AuthCredential,
  type User,
} from 'firebase/auth';
import { auth } from './firebase';

// Firebase 콘솔에서 Google provider 를 켜면 자동 생성된 OAuth 클라이언트들.
//   iOS   = GoogleService-Info.plist 의 CLIENT_ID
//   web   = Auth provider 설정의 clientId (idToken 의 audience 가 된다)
// ★app.json 의 `iosUrlScheme` 은 iOS 클라이언트의 REVERSED_CLIENT_ID 여야 한다.
const IOS_CLIENT_ID =
  '965554697584-jp90s17qk6tuqf17ucgj41h83bvg4jn2.apps.googleusercontent.com';
const WEB_CLIENT_ID =
  '965554697584-ma70ao3t2ppejbpg490q22mef6dq5m0k.apps.googleusercontent.com';

GoogleSignin.configure({
  iosClientId: IOS_CLIENT_ID,
  webClientId: WEB_CLIENT_ID,
});

/**
 * 로그인 결과.
 *
 * - `linked`      게스트 계정을 그대로 승계했다. uid 불변 = 기록 전부 유지.
 * - `signed_in`   게스트가 아닌 상태에서 로그인했다.
 * - `switched`    이미 가입된 계정이라 승계하지 못하고 그 계정으로 들어갔다.
 *                 ★게스트로 보던 기록은 다른 uid 에 남아 더 이상 보이지 않는다 —
 *                 화면이 이 사실을 사용자에게 반드시 알려야 한다(조용히 넘어가지 말 것).
 * - `cancelled`   사용자가 로그인 창을 닫았다. 오류가 아니다.
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

/** 익명 계정에 붙이거나(link), 안 되면 그 자격증명으로 로그인한다. */
async function attachOrSignIn(credential: AuthCredential): Promise<SocialAuthResult> {
  const current = auth.currentUser;

  if (current?.isAnonymous) {
    try {
      const linked = await linkWithCredential(current, credential);
      return { outcome: 'linked', user: linked.user };
    } catch (e) {
      // 이미 그 소셜 계정으로 가입한 적이 있으면 link 가 거부된다.
      // 이때 게스트 기록을 새 계정으로 옮기는 것은 서버 작업이라 파일럿 범위 밖 —
      // 지금은 기존 계정으로 들여보내고 화면이 그 사실을 알린다 (36-CONTEXT D-07 #6).
      const code = (e as { code?: string })?.code;
      if (
        code === 'auth/credential-already-in-use' ||
        code === 'auth/email-already-in-use'
      ) {
        const signedIn = await signInWithCredential(auth, credential);
        return { outcome: 'switched', user: signedIn.user };
      }
      throw e;
    }
  }

  const signedIn = await signInWithCredential(auth, credential);
  return { outcome: 'signed_in', user: signedIn.user };
}

export async function signInWithGoogle(): Promise<SocialAuthResult> {
  try {
    // iOS 는 항상 true 를 돌려주지만, Android 에서 Play 서비스가 없으면 여기서 걸린다.
    await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });

    const response = await GoogleSignin.signIn();

    // v16 부터 취소가 예외가 아니라 type: 'cancelled' 로 온다.
    if (response.type === 'cancelled') {
      return { outcome: 'cancelled', user: null };
    }

    const idToken = response.data?.idToken;
    if (!idToken) {
      throw new Error('Google 로그인에서 idToken 을 받지 못했습니다.');
    }

    return await attachOrSignIn(GoogleAuthProvider.credential(idToken));
  } catch (e) {
    // 구형 경로: 취소가 예외로 오는 경우도 오류로 올리지 않는다.
    if (isErrorWithCode(e) && e.code === statusCodes.SIGN_IN_CANCELLED) {
      return { outcome: 'cancelled', user: null };
    }
    throw e;
  }
}

// ── Apple 로그인 (Phase 36-03) ────────────────────────────────────────────────
//
// 사전 조건 (belle 2026-08-31 완료): Apple Developer 의 App ID(com.sunity.aicoach)에
// Sign In with Apple capability ON + Firebase Auth 의 Apple provider Enabled.
// iOS 네이티브 흐름이라 Services ID / OAuth key 는 불필요하다 (그건 웹·안드로이드용).

/** nonce 로 쓸 암호학적 난수 문자열. */
function randomNonce(byteLength = 32): string {
  const bytes = Crypto.getRandomBytes(byteLength);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Apple 로그인.
 *
 * ★nonce 를 두 곳에 **서로 다른 형태로** 넘겨야 한다:
 *   · Apple(signInAsync) 에는 **SHA256 해시**를 준다 → 애플이 그 해시를 identityToken
 *     안에 박아 돌려준다.
 *   · Firebase(credential) 에는 **원본(raw)** 을 준다 → Firebase 가 직접 해시해서
 *     토큰 안의 값과 대조한다.
 *   둘을 바꿔 넣으면 `auth/invalid-credential` 로 떨어진다. 이게 이 연동에서 가장
 *   흔한 실패다 — 재현이 안 되는 게 아니라 항상 실패한다.
 *
 * ★이름(fullName)은 **최초 1회만** 온다 (Expo 문서 명시: requestedScopes 는 첫 로그인
 *   에서만 제공되고 이후 null). 그래서 받은 그 자리에서 Firebase displayName 에
 *   저장한다 — 여기서 안 잡으면 그 사용자의 이름은 영영 못 받는다. 이미 이름이 있으면
 *   덮어쓰지 않는다(사용자가 나중에 바꿨을 수 있다).
 *
 * 취소는 오류가 아니다 — 구글 경로와 같은 규율로 `cancelled` 를 돌려준다.
 * iOS 전용(Apple 요구). 안드로이드에서는 isAvailableAsync 가 false 다.
 */
export async function signInWithApple(): Promise<SocialAuthResult> {
  const available = await AppleAuthentication.isAvailableAsync();
  if (!available) {
    throw new Error('이 기기에서는 Apple 로그인을 쓸 수 없습니다.');
  }

  const rawNonce = randomNonce();
  const hashedNonce = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    rawNonce,
  );

  let appleCredential: AppleAuthentication.AppleAuthenticationCredential;
  try {
    appleCredential = await AppleAuthentication.signInAsync({
      requestedScopes: [
        AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
        AppleAuthentication.AppleAuthenticationScope.EMAIL,
      ],
      nonce: hashedNonce,
    });
  } catch (e) {
    if ((e as { code?: string })?.code === 'ERR_REQUEST_CANCELED') {
      return { outcome: 'cancelled', user: null };
    }
    throw e;
  }

  const identityToken = appleCredential.identityToken;
  if (!identityToken) {
    throw new Error('Apple 로그인에서 identityToken 을 받지 못했습니다.');
  }

  const credential = new OAuthProvider('apple.com').credential({
    idToken: identityToken,
    rawNonce,
  });
  const result = await attachOrSignIn(credential);

  // 최초 1회 이름 저장 (위 docstring). 실패해도 로그인 자체는 성공이므로 삼킨다 —
  // 이름은 인사말 표시용이지 인증 조건이 아니다.
  const appleName = appleCredential.fullName;
  if (result.user && !result.user.displayName?.trim() && appleName) {
    const name = [appleName.familyName, appleName.givenName]
      .filter((part): part is string => !!part?.trim())
      .join('')
      .trim();
    if (name) {
      try {
        await updateProfile(result.user, { displayName: name });
      } catch {
        // 이름 저장 실패는 로그인 결과를 바꾸지 않는다.
      }
    }
  }
  return result;
}

// `displayNameOf` 는 `lib/authUser.ts` 로 옮겼다 (36-06). 이유: 탭 화면이 표시 이름을
// 쓰는데, 이 파일을 import 하면 상단의 네이티브 모듈 초기화가 앱 시작 경로로 딸려
// 들어온다. 표시 이름은 순수 함수라 네이티브와 무관한 곳이 제자리다.
