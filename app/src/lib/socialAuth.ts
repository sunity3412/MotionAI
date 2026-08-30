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

import {
  GoogleSignin,
  isErrorWithCode,
  statusCodes,
} from '@react-native-google-signin/google-signin';
import {
  GoogleAuthProvider,
  linkWithCredential,
  signInWithCredential,
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

/**
 * 로그인한 사용자의 표시 이름.
 *
 * belle 2026-08-30: 로그인 화면 인사말의 "희연" 자리는 **가입한 실명 또는 아이디**다.
 * provider 가 이름을 안 주는 경우(사용자가 제공 거부)를 대비해 이메일 앞부분까지 훑고,
 * 그래도 없으면 null 을 돌려 화면이 이름 없는 인사말을 쓰게 한다.
 */
export function displayNameOf(user: User | null): string | null {
  if (!user) return null;
  const name = user.displayName?.trim();
  if (name) return name;
  const local = user.email?.split('@')[0]?.trim();
  return local || null;
}
