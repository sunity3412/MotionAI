# 38-04 probe — 호스팅 후보 (2) 측정 전용

**페이지 구현이 아니다.** 공급자 페이지 후보 (2)(정적 단일 페이지)가 시뮬레이터 Mobile Safari 에서
같은 4가지를 할 수 있는지 재기 위한 최소 화면이다(리뷰 R14 — 후보 (1) web export 와 같은 실험).

| # | 실험 | probe 에서 보는 것 |
|---|---|---|
| 1 | Google 팝업 로그인 | 로그에 `login ok: uid=…` 또는 `login 실패: code=…` |
| 2 | `.mov` 파일 선택 | 로그에 `file: name=… size=… type=…` + `duration=…s` |
| 3 | presigned PUT | `POST /upload-url 200` → `setDoc ok` → `PUT 진행 …%` → `PUT 200` |
| 4 | onSnapshot | `onSnapshot: status=queued` (Pod 가 꺼져 있으면 뒤이어 `failed` 정상) |

앱과 같은 순서를 따른다(`app/src/app/analysis/loading.tsx` startAnalysisUpload):
`POST /upload-url` → `setDoc(users/{uid}/analyses/{analysisId}, status 'uploading')` → PUT → 구독.

## 실행

`config.js` 는 **커밋하지 않는다**(값은 공개 웹 config 라 비밀은 아니지만 리포에 두지 않는다).
측정 전에 리포 루트에서 한 줄로 만든다:

```bash
node -e "const fs=require('fs');const e={};for(const l of fs.readFileSync('app/.env','utf8').split('\n')){const t=l.trim();if(!t||t.startsWith('#'))continue;const i=t.indexOf('=');if(i>0)e[t.slice(0,i).trim()]=t.slice(i+1).trim();}const c={apiKey:e.EXPO_PUBLIC_FIREBASE_API_KEY,authDomain:e.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN,projectId:e.EXPO_PUBLIC_FIREBASE_PROJECT_ID,storageBucket:e.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET,messagingSenderId:e.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,appId:e.EXPO_PUBLIC_FIREBASE_APP_ID};fs.writeFileSync('.planning/phases/38-supplier-link/38-04-probe/config.js','export const firebaseConfig = '+JSON.stringify(c)+';\nexport const apiBaseUrl = '+JSON.stringify(e.EXPO_PUBLIC_API_BASE_URL)+';\n')"
python3 -m http.server 8083 --directory .planning/phases/38-supplier-link/38-04-probe
```

시뮬레이터 Safari 에서 `http://localhost:8083/`. `localhost` 는 Firebase 기본 Authorized domain 이라
로컬에선 팝업이 허용된다 — 실기기 LAN IP 는 등록돼 있지 않아 안 된다(실기기는 38-13 배포 뒤).
측정이 끝나면 `config.js` 를 지운다.

## 왜 지우지 않는가

38-04 Task 3 호스팅 결정의 근거(결정표의 후보 (2) 4행)를 다시 잴 수 있게 남긴다.
38-12(후보 (2) 선택 시 실제 페이지)는 이 파일을 확장하지 않고 새로 만든다.
