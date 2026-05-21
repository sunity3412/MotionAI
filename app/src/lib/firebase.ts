// Firebase 연결 (CLAUDE.md §3 기술 스택: DB = Firebase Firestore).
// firebase JS SDK v12 모듈러 API. Expo SDK 54는 firebase@12+ 만 지원.
// config 값은 EXPO_PUBLIC_ 환경변수에서 주입 (.env / .env.example 참고).
// 웹 config는 비밀값이 아니며, 실제 보안은 Firestore 보안 규칙으로 한다.

import ReactNativeAsyncStorage from '@react-native-async-storage/async-storage';
import { getApp, getApps, initializeApp, type FirebaseOptions } from 'firebase/app';
import { Firestore, getFirestore } from 'firebase/firestore';
import {
  type Auth,
  getAuth,
  initializeAuth,
  // @ts-expect-error getReactNativePersistence는 firebase v12 RN 빌드에만 있고
  // 기본 타입 정의에는 누락돼 있다. Metro가 RN 빌드를 해석하므로 런타임은 정상.
  getReactNativePersistence,
} from 'firebase/auth';

const firebaseConfig: FirebaseOptions = {
  apiKey: process.env.EXPO_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.EXPO_PUBLIC_FIREBASE_APP_ID,
};

// .env 가 아직 안 채워졌으면 (= Firebase 프로젝트 연결 전) 명확히 경고.
// 하드 throw 하지 않음 — 연결 전에도 다른 화면 개발은 가능해야 하므로.
export const firebaseConfigured = Boolean(
  firebaseConfig.apiKey && firebaseConfig.projectId && firebaseConfig.appId,
);

if (!firebaseConfigured && __DEV__) {
  console.warn(
    '[firebase] EXPO_PUBLIC_FIREBASE_* 미설정. app/.env 를 채울 것 (가이드: .env.example).',
  );
}

// Fast Refresh 시 중복 초기화 방지.
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApp();

// Auth 인스턴스를 globalThis 에 캐싱한다.
//   Expo Router + Fast Refresh 로 이 모듈이 재평가되면 initializeAuth 가
//   재호출되어 auth/already-initialized 가 발생, getAuth 폴백을 타며 불필요한
//   경고가 찍힌다. globalThis 캐시로 initializeAuth 를 런타임당 한 번만 호출 —
//   RN AsyncStorage 영속성 인스턴스를 일관되게 재사용한다.
declare global {
  // eslint-disable-next-line no-var
  var __sunityAuth: Auth | undefined;
}

function resolveAuth(): Auth {
  if (globalThis.__sunityAuth) return globalThis.__sunityAuth;
  try {
    globalThis.__sunityAuth = initializeAuth(app, {
      persistence: getReactNativePersistence(ReactNativeAsyncStorage),
    });
  } catch {
    // 이미 초기화된 경우 — firebase 내부에 등록된 기존 인스턴스를 재사용.
    globalThis.__sunityAuth = getAuth(app);
  }
  return globalThis.__sunityAuth;
}

const auth: Auth = resolveAuth();
const db: Firestore = getFirestore(app);

export { app, auth, db };
