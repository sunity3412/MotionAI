// Firebase 연결 검증 (일회성/재사용 가능 헬스체크).
// 익명 로그인 → Firestore 쓰기 → 읽기 → 정리. CLI에서 실행:
//   cd app && node scripts/verify-firebase.mjs
// .env 의 EXPO_PUBLIC_FIREBASE_* 값을 읽어 RN 앱과 동일한 프로젝트로 접속한다.

import { readFileSync } from 'node:fs';
import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously } from 'firebase/auth';
import { deleteDoc, doc, getDoc, getFirestore, serverTimestamp, setDoc } from 'firebase/firestore';

function loadEnv(path) {
  const env = {};
  for (const line of readFileSync(path, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq === -1) continue;
    env[trimmed.slice(0, eq).trim()] = trimmed.slice(eq + 1).trim();
  }
  return env;
}

const env = loadEnv(new URL('../.env', import.meta.url));
const config = {
  apiKey: env.EXPO_PUBLIC_FIREBASE_API_KEY,
  authDomain: env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: env.EXPO_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: env.EXPO_PUBLIC_FIREBASE_APP_ID,
};

const missing = Object.entries(config).filter(([, v]) => !v).map(([k]) => k);
if (missing.length) {
  console.error('[FAIL] .env 누락 키:', missing.join(', '));
  process.exit(1);
}

const app = initializeApp(config);
const auth = getAuth(app);
const db = getFirestore(app);

try {
  console.log(`[1/4] 프로젝트: ${config.projectId} — 익명 로그인 시도...`);
  const cred = await signInAnonymously(auth);
  const uid = cred.user.uid;
  console.log(`[2/4] 익명 로그인 OK (uid=${uid})`);

  // 권장 보안 규칙(users/{uid} 하위만 허용)과 호환되는 경로 사용.
  const ref = doc(db, 'users', uid, '_healthcheck', 'ping');
  await setDoc(ref, { ts: serverTimestamp(), source: 'verify-firebase' });
  console.log(`[3/4] Firestore 쓰기 OK (users/${uid}/_healthcheck/ping)`);

  const snap = await getDoc(ref);
  if (!snap.exists()) throw new Error('쓴 문서를 다시 읽지 못함');
  console.log('[4/4] Firestore 읽기 OK');

  await deleteDoc(ref).catch(() => console.warn('  (정리: _healthcheck 문서 삭제 실패 — 무시 가능)'));

  console.log('\n✅ Firebase 연결 검증 성공 — 익명 인증 + Firestore 정상');
  process.exit(0);
} catch (err) {
  const code = err?.code ?? '(no code)';
  console.error(`\n❌ 검증 실패 [${code}]: ${err?.message ?? err}`);
  if (code === 'auth/operation-not-allowed')
    console.error('→ 콘솔 Authentication 에서 "익명" 로그인 방법이 꺼져 있음.');
  if (code === 'auth/configuration-not-found')
    console.error('→ Authentication 자체가 미설정. 콘솔에서 Authentication 시작하기.');
  if (code === 'permission-denied')
    console.error('→ Firestore 보안 규칙이 인증 사용자 쓰기를 막음 (production 모드 기본 규칙).');
  if (code === 'unavailable' || code === 'not-found')
    console.error('→ Firestore 데이터베이스가 아직 생성되지 않았을 수 있음.');
  process.exit(1);
}
