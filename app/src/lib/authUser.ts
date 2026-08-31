// 로그인 상태를 화면에 공급한다 (Phase 36-06 — 마이 탭 로그인 입구).
//
// 왜 별도 모듈인가: 로그인 상태는 `socialAuth.ts` 가 갖고 있는 게 자연스러워 보이지만,
// 그 파일은 모듈 최상단에서 **네이티브 모듈**(expo-apple-authentication,
// @react-native-google-signin)을 import 하고 `GoogleSignin.configure()` 를 즉시 실행한다.
// 로그인 화면은 사용자가 들어갈 때만 평가되지만, 탭 화면이 그걸 import 하면 앱을 켜는
// 순간 그 네이티브 초기화가 따라 들어온다 — 마이 탭이 네이티브 사정으로 깨질 길을
// 새로 여는 셈이라 분리한다. 이 파일은 `firebase/auth` 만 쓴다.
//
// 데이터소스 격리(bodyProfile.ts:1-11)와 같은 규율: 화면은 onAuthStateChanged 를
// 직접 붙이지 않고 이 훅을 경유한다. 로그인·로그아웃 같은 **행위**는 화면이
// firebase/auth 를 직접 호출한다 (index.tsx 의 signInAnonymously 선례).

import { onAuthStateChanged, type User } from 'firebase/auth';
import { useEffect, useState } from 'react';
import { auth } from './firebase';

export type AuthUserState = {
  user: User | null;
  /**
   * 익명(게스트) 세션인가.
   *
   * ★로그인 전과 "user 없음"은 다르다 — 게스트도 엄연히 로그인된 Firebase 사용자다
   * (익명 인증). 그래서 `!user` 로 게스트를 판정하면 안 된다.
   */
  isGuest: boolean;
  /**
   * 첫 인증 상태 통지를 받았는가.
   *
   * Firebase 는 영속 세션을 복원하는 동안 잠깐 `currentUser === null` 이다. 그 사이에
   * "로그인하세요"를 그리면 게스트에게 한 번 깜빡인다 — ready 전에는 계정 영역을
   * 그리지 않는다 (인트로의 bootstrapping 과 같은 이유).
   */
  ready: boolean;
};

export function useAuthUser(): AuthUserState {
  const [user, setUser] = useState<User | null>(auth.currentUser);
  // currentUser 가 이미 있으면 복원이 끝난 것이므로 처음부터 ready.
  const [ready, setReady] = useState(!!auth.currentUser);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u);
      setReady(true);
    });
    return unsub;
  }, []);

  return { user, isGuest: !!user?.isAnonymous, ready };
}

/**
 * 로그인한 사용자의 표시 이름.
 *
 * belle 2026-08-30: 이름 자리는 **가입한 실명 또는 아이디**다. provider 가 이름을
 * 안 주는 경우(사용자가 제공 거부, Apple 은 최초 1회만 준다)를 대비해 이메일
 * 앞부분까지 훑고, 그래도 없으면 null 을 돌려 화면이 이름 없는 표기를 쓰게 한다.
 */
export function displayNameOf(user: User | null): string | null {
  if (!user) return null;
  const name = user.displayName?.trim();
  if (name) return name;
  const local = user.email?.split('@')[0]?.trim();
  return local || null;
}
