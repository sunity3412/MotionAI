// 38-04 후보 (2) 측정 probe (리뷰 R14 — 두 후보를 같은 4가지로 잰다).
//
// 앱(app/src/app/analysis/loading.tsx startAnalysisUpload)과 같은 순서를 vanilla 로 따른다:
//   POST /upload-url → setDoc(users/{uid}/analyses/{analysisId}, status 'uploading')
//   → XHR PUT(Content-Type = video/mp4 | video/quicktime) → onSnapshot 으로 status 구독.
// `queued` 가 찍히면 PUT + S3 알림 + 구독 셋 다 산 것이다. Pod 가 꺼져 있으면 뒤이어
// `failed` 가 오는 것이 정상이다.
//
// 로그인은 Google 팝업만(signInWithPopup). 익명 로그인 없음 — 화이트리스트 재료가
// 아니다(D-03). 리다이렉트 방식은 S3/CloudFront 도메인에서 Safari 가 막으므로 쓰지 않는다
// (38-RESEARCH §D).
//
// Firebase JS SDK 는 gstatic CDN ESM 12.13.0 — app/package-lock.json 의 firebase 와 같은
// 버전(38-UI-SPEC Registry Safety). DOM 에는 textContent 로만 쓴다.
//
// config.js 는 커밋하지 않는다(README.md — app/.env 에서 실행자가 한 줄로 만든다).

import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.13.0/firebase-app.js';
import {
  GoogleAuthProvider,
  getAuth,
  onAuthStateChanged,
  signInWithPopup,
} from 'https://www.gstatic.com/firebasejs/12.13.0/firebase-auth.js';
import {
  doc,
  getFirestore,
  onSnapshot,
  setDoc,
} from 'https://www.gstatic.com/firebasejs/12.13.0/firebase-firestore.js';

const logEl = document.getElementById('log');

function log(msg) {
  const t = new Date().toISOString().slice(11, 19);
  logEl.textContent += `[${t}] ${msg}\n`;
}

window.addEventListener('error', (ev) => log(`window error: ${ev.message}`));
window.addEventListener('unhandledrejection', (ev) =>
  log(`unhandled: ${ev.reason && (ev.reason.code || ev.reason.message || ev.reason)}`),
);

let config;
try {
  config = await import('./config.js');
} catch (e) {
  log(`config.js 없음 — README.md 의 생성 한 줄을 먼저 실행: ${e && e.message}`);
  throw e;
}

const app = initializeApp(config.firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
log(`firebase init ok · project=${config.firebaseConfig.projectId}`);

onAuthStateChanged(auth, (u) => {
  if (!u) {
    log('auth: 로그인 안 됨');
    return;
  }
  log(`auth: uid=${u.uid} anonymous=${u.isAnonymous} email=${u.email ?? '-'}`);
});

// ① Google 팝업 로그인 — 팝업 호출 앞에 await 를 두지 않는다(차단 방지).
document.getElementById('login').addEventListener('click', () => {
  log('login: signInWithPopup 호출');
  signInWithPopup(auth, new GoogleAuthProvider())
    .then((cred) => log(`login ok: uid=${cred.user.uid}`))
    .catch((e) => log(`login 실패: code=${e && e.code} message=${e && e.message}`));
});

// ② 파일 선택
let picked = null;
document.getElementById('file').addEventListener('change', (ev) => {
  const f = ev.target.files && ev.target.files[0];
  picked = f || null;
  if (!f) {
    log('file: 선택 없음');
    return;
  }
  log(`file: name=${f.name} size=${f.size} type=${f.type || '(빈 값)'}`);
  // 길이(duration)는 웹 picker 가 주지 않는다(38-RESEARCH Pitfall 5) — <video> 메타데이터로 읽는다.
  const url = URL.createObjectURL(f);
  const v = document.createElement('video');
  v.preload = 'metadata';
  v.onloadedmetadata = () => {
    log(`file: duration=${v.duration.toFixed(2)}s`);
    URL.revokeObjectURL(url);
  };
  v.onerror = () => {
    log('file: duration 읽기 실패(<video> 메타데이터 오류)');
    URL.revokeObjectURL(url);
  };
  v.src = url;
});

function formatOf(file) {
  const name = file.name.toLowerCase();
  if (name.endsWith('.mov') || file.type === 'video/quicktime') return 'mov';
  return 'mp4';
}

const CONTENT_TYPE = { mp4: 'video/mp4', mov: 'video/quicktime' };

function putWithProgress(url, file, contentType) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', url);
    xhr.setRequestHeader('Content-Type', contentType);
    let lastPct = -1;
    xhr.upload.onprogress = (ev) => {
      if (!ev.lengthComputable) return;
      const pct = Math.floor((ev.loaded / ev.total) * 100);
      if (pct >= lastPct + 25 || pct === 100) {
        lastPct = pct;
        log(`PUT 진행 ${pct}%`);
      }
    };
    xhr.onload = () => resolve(xhr.status);
    xhr.onerror = () => reject(new Error(`PUT 네트워크 오류 status=${xhr.status}`));
    xhr.send(file);
  });
}

// ③ 업로드 + ④ 구독
document.getElementById('upload').addEventListener('click', async () => {
  const user = auth.currentUser;
  if (!user) {
    log('upload: 먼저 로그인');
    return;
  }
  if (!picked) {
    log('upload: 먼저 영상 선택');
    return;
  }
  const format = formatOf(picked);
  try {
    const token = await user.getIdToken();
    const res = await fetch(`${config.apiBaseUrl}/upload-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        mode: 'mode3',
        fileName: picked.name,
        fileSizeBytes: picked.size,
        format,
      }),
    });
    const text = await res.text();
    if (!res.ok) {
      log(`POST /upload-url ${res.status}: ${text.slice(0, 200)}`);
      return;
    }
    const { analysisId, uploadUrl, s3Key } = JSON.parse(text);
    log(`POST /upload-url 200 · analysisId=${analysisId} · s3Key=${s3Key}`);

    const now = Date.now();
    const ref = doc(db, 'users', user.uid, 'analyses', analysisId);
    await setDoc(ref, {
      analysisId,
      mode: 'mode3',
      status: 'uploading',
      fileName: picked.name,
      createdAt: now,
      updatedAt: now,
      learningOptIn: false,
    });
    log('setDoc ok (status=uploading)');

    // 구독을 PUT 전에 건다 — queued 전이를 놓치지 않게.
    onSnapshot(
      ref,
      (snap) => {
        const d = snap.data();
        // 실패 코드는 contract.md §3 `error: {code, message}` (types/analysis.ts AnalysisDoc.error).
        const err = d && d.error && d.error.code ? ` error.code=${d.error.code}` : '';
        log(`onSnapshot: status=${d ? d.status : '(doc 없음)'}${err}`);
      },
      (e) => log(`onSnapshot 오류: code=${e && e.code} message=${e && e.message}`),
    );

    const status = await putWithProgress(uploadUrl, picked, CONTENT_TYPE[format]);
    log(`PUT ${status}`);
  } catch (e) {
    log(`upload 실패: code=${e && e.code} message=${e && e.message}`);
  }
});
