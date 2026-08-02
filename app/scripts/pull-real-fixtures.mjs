// 실 분석 doc → 리포 fixture 박제 (quick-260802-czw Task 1).
//
// 왜 Node 인가: backend/.venv 에 firebase_admin 이 없고(실측) 이 사이클의 규약이
// 신규 의존성 0 이다. app/node_modules/firebase-admin 은 이미 있고
// app/scripts/seed-reference-motions.mjs 가 같은 선례다.
//
// 왜 리포에 커밋하는가: 이 사이클이 죽이려는 병이 "입력이 움직여서 무엇이 효과였는지
// 못 가리는 것"이다. Firestore doc 은 재분석마다 덮어써진다 — 07-31 §C-4 재산출이
// 실제로 덮었고 그때 점수가 80→60 으로 움직였다(원인 미분리). 입력이 리포에 고정돼
// 있지 않으면 하네스가 같은 병을 물려받는다.
//
// **이 스크립트는 읽기만 한다.** .set/.update/.delete/.create 를 이 파일에 쓰지 말 것.
//
// 사용법:
//   node app/scripts/pull-real-fixtures.mjs
//   node app/scripts/pull-real-fixtures.mjs --uid <uid> --ids a,b,c --out <dir>
//
// 인증: --sa <path> | FIREBASE_SA_PATH | <repo>/firebase-sa.json | ADC.

import { readFileSync, writeFileSync, mkdirSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { applicationDefault, cert, initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(HERE, '..', '..');

// 박제 대상 — belle 계정의 4 분석 (전부 mode1, visionVeto.status=applied).
// 기준 doc 은 여기 적지 않는다: 분석 doc 이 들고 있는 referenceMotionId 로 따라간다
// (분석과 기준이 어긋난 fixture 를 원천 차단).
const DEFAULT_UID = 'csKWYvI3WCPYPysNQ9KkWecaUvq1';
const DEFAULT_IDS = [
  'powerspinFault1785373695',
  'kipupFault1785373695',
  'pdshapeCorrect1785373695',
  'elbowtwistsisterFault1785373695',
];
const DEFAULT_OUT = join(REPO_ROOT, 'backend', 'evals', 'realfixture', 'fixtures');

// presigned URL 판별 토큰. **키 이름이 아니라 값 기준**이라 새 URL 필드가 생겨도
// 자동으로 잡힌다 (T-czw-01). presigned URL 은 X-Amz-Credential=AKIA… 로 AWS
// access key ID 를 품고 있어 리포에 들어가면 키 노출이다.
const SIGNED_URL_MARKER = 'X-Amz-Signature';

function parseArgs(argv) {
  const out = { uid: DEFAULT_UID, ids: [...DEFAULT_IDS], outDir: DEFAULT_OUT, sa: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--uid' && i + 1 < argv.length) out.uid = argv[++i];
    else if (a === '--ids' && i + 1 < argv.length) {
      out.ids = argv[++i].split(',').map((s) => s.trim()).filter(Boolean);
    } else if (a === '--out' && i + 1 < argv.length) out.outDir = resolve(argv[++i]);
    else if (a === '--sa' && i + 1 < argv.length) out.sa = argv[++i];
  }
  return out;
}

function initFirebase(saArg) {
  const candidates = [
    saArg,
    process.env.FIREBASE_SA_PATH,
    join(REPO_ROOT, 'firebase-sa.json'),
    // 워크트리에는 gitignore 된 키가 없다 — 메인 체크아웃의 것을 읽기 전용으로 참조.
    '/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json',
  ].filter(Boolean);
  for (const p of candidates) {
    try {
      statSync(p);
      const sa = JSON.parse(readFileSync(p, 'utf8'));
      initializeApp({ credential: cert(sa) });
      return `serviceAccount:${p}`;
    } catch {
      // 다음 후보
    }
  }
  initializeApp({ credential: applicationDefault() });
  return 'applicationDefault';
}

// ── 정규화 ────────────────────────────────────────────────────────────────
// (1) 전체 doc 을 그대로 쓴다 — 필드 화이트리스트 금지 (D-3). 부분 박제는
//     "왜 이 필드가 없지"가 조용한 truncation 으로 바뀌는 경로이고 그게 이
//     사이클이 없애려는 실패 유형 그 자체다.
// (2) 값이 presigned URL 이면 제거하고 dot-path 를 기록한다.
// (3) Firestore Timestamp → epoch ms 정수 (JSON 왕복 안정).
// (4) 부동소수는 가공하지 않는다 — 재현이 목적이므로 production 입력과 비트가 같아야 한다.
function isTimestampLike(v) {
  return (
    v &&
    typeof v === 'object' &&
    typeof v.toMillis === 'function' &&
    typeof v.seconds === 'number'
  );
}

function normalize(value, path, stripped) {
  if (value === null || value === undefined) return null;
  const t = typeof value;
  if (t === 'string') {
    if (value.includes(SIGNED_URL_MARKER)) {
      stripped.push(path);
      return null;
    }
    return value;
  }
  if (t === 'number' || t === 'boolean') return value;
  if (Array.isArray(value)) {
    return value.map((v, i) => normalize(v, `${path}[${i}]`, stripped));
  }
  if (t === 'object') {
    if (isTimestampLike(value)) return value.toMillis();
    const proto = Object.getPrototypeOf(value);
    if (proto !== Object.prototype && proto !== null) {
      // 조용한 truncation 방지 — 모르는 Firestore 타입은 죽는다.
      throw new Error(
        `미지원 Firestore 타입 at ${path}: ${value?.constructor?.name ?? 'unknown'}`
      );
    }
    const out = {};
    for (const [k, v] of Object.entries(value)) {
      out[k] = normalize(v, path ? `${path}.${k}` : k, stripped);
    }
    return out;
  }
  throw new Error(`미지원 값 타입 at ${path}: ${t}`);
}

function writeJson(path, obj) {
  mkdirSync(dirname(path), { recursive: true });
  // 줄 단위 diff 가능 — 입력이 언제 움직였는지 git 이 보여줘야 한다.
  writeFileSync(path, JSON.stringify(obj, null, 1) + '\n', 'utf8');
  return statSync(path).size;
}

function pick(obj, ...keys) {
  for (const k of keys) {
    let cur = obj;
    let ok = true;
    for (const part of k.split('.')) {
      if (cur && typeof cur === 'object' && part in cur) cur = cur[part];
      else {
        ok = false;
        break;
      }
    }
    if (ok && cur !== null && cur !== undefined) return cur;
  }
  return null;
}

// fps 파생 — 리터럴 금지. angles 와 keypointReport 는 둘 다 production 이 저장한
// 1급 산출물이고 fps 가 다르다(실측 학생 9 / 기준 18). 그 관계를 doc 에서 계산한다.
function deriveAnglesFps(anglesFrames, kr) {
  const krFps = Number(pick(kr ?? {}, 'fps'));
  const krFrames = Number(pick(kr ?? {}, 'frames'));
  if (!(krFps > 0) || !(krFrames > 0) || !(anglesFrames > 0)) return null;
  return (krFps * anglesFrames) / krFrames;
}

function assertSingleFps(label, values) {
  const uniq = [...new Set(values.map((v) => (v === null ? 'null' : v.toFixed(6))))];
  if (uniq.length !== 1 || uniq[0] === 'null') {
    console.error(`FATAL: ${label} 이 fixture 간 불일치 — ${JSON.stringify(values)}`);
    process.exit(1);
  }
  return Number(uniq[0]);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const credMode = initFirebase(args.sa);
  const db = getFirestore();

  const manifest = {
    generatedBy: 'app/scripts/pull-real-fixtures.mjs (quick-260802-czw)',
    fetchedAt: new Date().toISOString(),
    credentialMode: credMode,
    sourceUid: args.uid,
    strippedPaths: [],
    analyses: [],
    references: [],
  };

  const refIds = new Map(); // refId -> 참조한 분석 목록

  for (const id of args.ids) {
    const snap = await db.doc(`users/${args.uid}/analyses/${id}`).get();
    if (!snap.exists) {
      console.error(`FATAL: 분석 doc 없음 — users/${args.uid}/analyses/${id}`);
      process.exit(1);
    }
    const stripped = [];
    const doc = normalize(snap.data(), '', stripped);
    const bytes = writeJson(join(args.outDir, `${id}.json`), doc);
    manifest.strippedPaths.push(...stripped.map((p) => `${id}:${p}`));

    const kr = pick(doc, 'keypointReport', 'result.keypointReport');
    const anglesFrames = Number(pick(doc, 'anglesFrames')) || 0;
    const jointKeys = pick(doc, 'anglesJointKeys') || [];
    const refId = pick(doc, 'referenceMotionId', 'meta.referenceMotionId',
      'result.comparison.referenceMotionId');
    if (!refId) {
      console.error(`FATAL: referenceMotionId 를 못 찾음 — ${id}`);
      process.exit(1);
    }
    if (!refIds.has(refId)) refIds.set(refId, []);
    refIds.get(refId).push(id);

    // 정답지 — RECON 게이트가 대조할 대상. Firestore doc 이 나중에 덮어써져도
    // 정답지는 리포에 남는다.
    const records = pick(doc, 'result.deductionBreakdown.records') || [];
    const cards = pick(doc, 'result.faultZoomComparisons', 'faultZoomComparisons') || [];
    const breakdown = pick(doc, 'result.deductionBreakdown') || {};

    manifest.analyses.push({
      analysisId: id,
      docPath: `users/${args.uid}/analyses/${id}`,
      bytes,
      mode: pick(doc, 'mode'),
      referenceMotionId: refId,
      overallScore: pick(doc, 'result.overallScore'),
      visionVetoStatus: pick(doc, 'result.visionVeto.status'),
      motionId: pick(doc, 'result.mission.motionId'),
      anglesFrames,
      anglesJointKeys: Array.isArray(jointKeys) ? jointKeys.length : 0,
      keypointReport: kr
        ? { fps: pick(kr, 'fps'), frames: pick(kr, 'frames'), joints: (pick(kr, 'joints') || []).length }
        : null,
      joints3d: {
        keys: (pick(doc, 'joints3dKeys') || []).length,
        frames: pick(doc, 'joints3dFrames'),
      },
      anglesFps: deriveAnglesFps(anglesFrames, kr),
      deductionFinal: pick(breakdown, 'final'),
      sourceRecordCriteria: records.map((r) => ({
        criterion: r?.criterion ?? null,
        source: r?.source ?? null,
        unit: r?.unit ?? null,
        measuredValue: r?.measuredValue ?? null,
        baselineValue: r?.baselineValue ?? null,
        points: r?.points ?? null,
        ruleId: r?.ruleId ?? null,
        atFrameIdx: r?.atFrameIdx ?? null,
      })),
      sourceCardFrames: cards.map((c) => ({
        criterion: c?.criterion ?? null,
        joint: c?.joint ?? null,
        tier: c?.tier ?? null,
        region: c?.region ?? null,
        userFrameIdx: c?.userFrameIdx ?? null,
        refFrameIdx: c?.refFrameIdx ?? null,
        atMatched: c?.atMatched ?? null,
      })),
    });
  }

  for (const [refId, usedBy] of refIds) {
    const snap = await db.doc(`reference/${refId}`).get();
    if (!snap.exists) {
      console.error(`FATAL: 기준 doc 없음 — reference/${refId}`);
      process.exit(1);
    }
    const stripped = [];
    const doc = normalize(snap.data(), '', stripped);
    const bytes = writeJson(join(args.outDir, 'reference', `${refId}.json`), doc);
    manifest.strippedPaths.push(...stripped.map((p) => `reference/${refId}:${p}`));

    const kr = pick(doc, 'keypointReport', 'referenceKeypointReport');
    const jointKeys = pick(doc, 'anglesJointKeys') || [];
    const anglesFlat = pick(doc, 'angles') || [];
    const anglesFrames =
      Array.isArray(jointKeys) && jointKeys.length > 0
        ? Math.round(anglesFlat.length / jointKeys.length)
        : 0;

    manifest.references.push({
      motionId: refId,
      docPath: `reference/${refId}`,
      bytes,
      usedBy,
      anglesFrames,
      anglesJointKeys: Array.isArray(jointKeys) ? jointKeys.length : 0,
      keypointReport: kr
        ? { fps: pick(kr, 'fps'), frames: pick(kr, 'frames'), joints: (pick(kr, 'joints') || []).length }
        : null,
      referenceKeypointReport: pick(doc, 'referenceKeypointReport')
        ? {
            fps: pick(doc, 'referenceKeypointReport.fps'),
            frames: pick(doc, 'referenceKeypointReport.frames'),
            joints: (pick(doc, 'referenceKeypointReport.joints') || []).length,
          }
        : null,
      sharedBaseMotionId: pick(doc, 'sharedBaseMotionId'),
      baseUntilS: pick(doc, 'baseUntilS'),
      clipRange: pick(doc, 'clipRange'),
      anglesFps: deriveAnglesFps(anglesFrames, kr),
    });
  }

  // 4건 정합 assert — 이 값이 러너의 유일한 fps 출처다. 불일치는 경고가 아니라 죽음.
  manifest.studentAnglesFps = assertSingleFps(
    'studentAnglesFps',
    manifest.analyses.map((a) => a.anglesFps)
  );
  manifest.referenceAnglesFps = assertSingleFps(
    'referenceAnglesFps',
    manifest.references.map((r) => r.anglesFps)
  );

  const totalBytes =
    manifest.analyses.reduce((s, a) => s + a.bytes, 0) +
    manifest.references.reduce((s, r) => s + r.bytes, 0);
  manifest.totalBytes = totalBytes;

  writeJson(join(args.outDir, 'MANIFEST.json'), manifest);

  console.log(`분석 ${manifest.analyses.length}건 · 기준 ${manifest.references.length}건`);
  console.log(`strippedPaths ${manifest.strippedPaths.length}건`);
  console.log(
    `studentAnglesFps=${manifest.studentAnglesFps} referenceAnglesFps=${manifest.referenceAnglesFps}`
  );
  console.log(`총 ${Math.round(totalBytes / 1024)} KB`);
  for (const a of manifest.analyses) {
    console.log(
      `  ${a.analysisId} score=${a.overallScore} records=${a.sourceRecordCriteria.length} ` +
        `cards=${a.sourceCardFrames.length} angles=${a.anglesFrames}x${a.anglesJointKeys} ` +
        `kr=${JSON.stringify(a.keypointReport)} motionId=${a.motionId} ref=${a.referenceMotionId}`
    );
  }
  for (const r of manifest.references) {
    console.log(
      `  ref ${r.motionId} angles=${r.anglesFrames}x${r.anglesJointKeys} ` +
        `kr=${JSON.stringify(r.keypointReport)} refKr=${JSON.stringify(r.referenceKeypointReport)} ` +
        `sharedBase=${r.sharedBaseMotionId} baseUntilS=${r.baseUntilS}`
    );
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
