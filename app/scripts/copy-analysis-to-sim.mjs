// 분석 doc 1건을 다른 uid(시뮬레이터 게스트 계정) 아래로 복사 — 결과 화면 실물 확인용.
//
// 왜: 시뮬 게스트 계정에는 분석이 0건이라 확대비교·감점 카드 같은 doc 의존 화면을
// 시뮬에서 열어볼 수 없다. Pod 를 띄워 재분석하는 대신(시연 때만 — belle 08-28)
// 이미 있는 doc 을 복사해 같은 화면을 시뮬에서 연다. 원본은 읽기만 한다.
//
// 실행 (리포 루트에서, 서비스 계정 = firebase-sa.json):
//   cd app && node scripts/copy-analysis-to-sim.mjs <srcUid> <analysisId> <dstUid>
// 인자 생략 시 기본값 = belle pdshape 60점(09-02) → 시뮬 iPhone 16 Pro 게스트 uid.
//
// 출력은 요약(status/점수/확대 카드 tier)만 — doc 본문은 찍지 않는다.
// 복사본에는 `simCopyOf` 필드를 남겨 평가 배치·통계에서 구분할 수 있게 한다.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { cert, initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';

// 리포 루트의 firebase-sa.json — 스크립트 위치 기준(어느 cwd 에서 실행해도 같은 파일).
const SA_PATH = fileURLToPath(new URL('../../firebase-sa.json', import.meta.url));
const [
  srcUid = 'csKWYvI3WCPYPysNQ9KkWecaUvq1',
  analysisId = '813abf24f2b64038b7178bd3c7a8396f',
  dstUid = 'k9fQlhw2Picwql31ooLlmmAcwbm2',
] = process.argv.slice(2);

const sa = JSON.parse(readFileSync(SA_PATH, 'utf8'));
initializeApp({ credential: cert(sa) });
const db = getFirestore();

const src = await db.doc(`users/${srcUid}/analyses/${analysisId}`).get();
if (!src.exists) {
  console.error(`source missing: users/${srcUid}/analyses/${analysisId}`);
  process.exit(1);
}
const data = src.data();
const zooms = data?.result?.faultZoomComparisons ?? [];
const records = data?.result?.deductionBreakdown?.records ?? [];
console.log(
  [
    `status=${data.status}`,
    `mode=${data.mode}`,
    `score=${data?.result?.overallScore}`,
    `faultZoomStatus=${data?.result?.faultZoomStatus}`,
    `zoomCards=${zooms.length} [${zooms.map((z) => `${z.tier ?? 'legacy'}:${z.criterion ?? z.joint}`).join(', ')}]`,
    `records=${records.length} [${records.map((r) => r.criterion).join(', ')}]`,
  ].join('\n'),
);

await db
  .doc(`users/${dstUid}/analyses/${analysisId}`)
  .set({ ...data, simCopyOf: `${srcUid}/${analysisId}` });
const back = await db.doc(`users/${dstUid}/analyses/${analysisId}`).get();
console.log(`copied -> users/${dstUid}/analyses/${analysisId} exists=${back.exists}`);
process.exit(0);
