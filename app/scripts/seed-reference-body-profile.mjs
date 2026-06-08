// 정은지 reference 두 필드 (bodyNormalizationProfile + bodyComparisonSourcePose)
// atomic seed. JSON fixture (`reference-body-data.json`, Task 2 산출) → Firestore
// reference/{motionId} 두 필드 동시 merge.
//
// C5: --dry-run.
// R7 fix (2026-06-08 round-2): Step 1 parse/load/validate → Step 2 if --dry-run:
//   stdout proposed payload + exit 0 (Firebase init 호출 X — ADC 미설정 환경 호환)
//   → Step 3 real-run: Firebase Admin init + Firestore batch commit.
//
// 사용:
//   - 사전 (real-run 만): gcloud auth application-default login   # sunity3412@gmail.com
//   - dry-run 우선:  cd app && npm run seed:body-profile -- --profiles ../reference-body-data.json --dry-run
//   - commit:        cd app && npm run seed:body-profile -- --profiles ../reference-body-data.json
//   - --force        이미 박제된 reference 덮어쓰기 (default idempotent skip).
//
// per D-06-B2 + [[firebase-project-account]] + 06-PATTERNS.md §4 + R7 fix.

import { readFileSync } from 'node:fs';

const PROJECT_ID = 'sunity-ai-coach';

const REQUIRED_BODY_PROFILE_FIELDS = [
  'estimatedHeightScale',
  'armScale',
  'legScale',
  'torsoScale',
  'shoulderHipRatio',
  'confidence',
  'warnings',
];

const REQUIRED_SOURCE_POSE_FIELDS = [
  'jointKeys',
  'values',
  'frameIndex',
  'torsoPx',
  'confidence',
  'measuredAt',
];

function parseArgs(argv) {
  const out = { profiles: null, force: false, dryRun: false };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--profiles' && i + 1 < argv.length) {
      out.profiles = argv[i + 1];
      i++;
    } else if (argv[i] === '--force') {
      out.force = true;
    } else if (argv[i] === '--dry-run') {
      out.dryRun = true;
    } else if (argv[i] === '--help' || argv[i] === '-h') {
      console.log(
        'Usage: node seed-reference-body-profile.mjs --profiles <path> [--dry-run] [--force]',
      );
      process.exit(0);
    }
  }
  return out;
}

function validateBodyProfile(motionId, bp) {
  if (!bp || typeof bp !== 'object') {
    throw new Error(`[${motionId}] bodyNormalizationProfile 필드 없음`);
  }
  for (const f of REQUIRED_BODY_PROFILE_FIELDS) {
    if (!(f in bp)) {
      throw new Error(
        `[${motionId}] bodyNormalizationProfile 필수 필드 누락: ${f}`,
      );
    }
  }
  if (!Array.isArray(bp.warnings)) {
    throw new Error(`[${motionId}] bodyNormalizationProfile.warnings 가 array 가 아님`);
  }
  // [[firestore-nested-array-flat]] — warnings 안에 list 금지.
  for (let i = 0; i < bp.warnings.length; i++) {
    if (Array.isArray(bp.warnings[i])) {
      throw new Error(
        `[${motionId}] bodyNormalizationProfile.warnings[${i}] nested array 금지`,
      );
    }
  }
}

function validateSourcePose(motionId, sp) {
  if (sp === null || sp === undefined) {
    return; // partial backfill — graceful (R2 fix).
  }
  if (typeof sp !== 'object') {
    throw new Error(`[${motionId}] bodyComparisonSourcePose 가 object 가 아님`);
  }
  for (const f of REQUIRED_SOURCE_POSE_FIELDS) {
    if (!(f in sp)) {
      throw new Error(
        `[${motionId}] bodyComparisonSourcePose 필수 필드 누락: ${f}`,
      );
    }
  }
  if (!Array.isArray(sp.jointKeys) || !Array.isArray(sp.values)) {
    throw new Error(
      `[${motionId}] bodyComparisonSourcePose.jointKeys / values 가 array 아님`,
    );
  }
  const expected = 4 * sp.jointKeys.length;
  if (sp.values.length !== expected) {
    throw new Error(
      `[${motionId}] bodyComparisonSourcePose.values length must be 4 × ` +
        `len(jointKeys) = ${expected}, got ${sp.values.length}`,
    );
  }
  // values 안에 nested array 금지 (R2 flat float list).
  for (let i = 0; i < sp.values.length; i++) {
    if (Array.isArray(sp.values[i])) {
      throw new Error(
        `[${motionId}] bodyComparisonSourcePose.values[${i}] nested array 금지`,
      );
    }
  }
}

function loadProfilesPayload(path) {
  const raw = readFileSync(path, 'utf8');
  const data = JSON.parse(raw);
  if (!data.motions || typeof data.motions !== 'object') {
    throw new Error(`잘못된 profiles JSON 형식: ${path} (motions dict 없음)`);
  }
  // 각 motion 의 두 필드 schema validate.
  for (const [motionId, m] of Object.entries(data.motions)) {
    validateBodyProfile(motionId, m.bodyNormalizationProfile);
    validateSourcePose(motionId, m.bodyComparisonSourcePose ?? null);
  }
  return data;
}

async function main() {
  // ────────────────────────────────────────────────────────────────────
  // Step 1 — parse + load + validate (Firebase 미접촉, ADC 의존 X).
  //   R7 fix 핵심: validation 이 Firebase init 보다 먼저.
  // ────────────────────────────────────────────────────────────────────
  const args = parseArgs(process.argv.slice(2));
  if (!args.profiles) {
    console.error('--profiles <path> required');
    process.exit(1);
  }
  const payload = loadProfilesPayload(args.profiles);
  const entries = Object.entries(payload.motions);

  // ────────────────────────────────────────────────────────────────────
  // Step 2 — dry-run 분기. Firebase init 호출 전 early return.
  //   R7 fix: ADC 미설정 환경에서도 안전 (Firebase 호출 0회).
  // ────────────────────────────────────────────────────────────────────
  if (args.dryRun) {
    const proposed = entries.map(([motionId, data]) => ({
      motionId,
      bodyNormalizationProfile: data.bodyNormalizationProfile,
      bodyComparisonSourcePose: data.bodyComparisonSourcePose ?? null,
    }));
    console.log(
      JSON.stringify(
        {
          dryRun: true,
          willMerge: proposed.length,
          force: args.force,
          motions: proposed,
        },
        null,
        2,
      ),
    );
    return; // R7 — Firebase init 호출 X.
  }

  // ────────────────────────────────────────────────────────────────────
  // Step 3 — real-run. Firebase Admin SDK + ADC.
  // ────────────────────────────────────────────────────────────────────
  const { applicationDefault, initializeApp } = await import('firebase-admin/app');
  const { getFirestore } = await import('firebase-admin/firestore');

  initializeApp({ credential: applicationDefault(), projectId: PROJECT_ID });
  const db = getFirestore();
  const batch = db.batch();

  console.log(
    `[seed:body-profile] 프로젝트 ${PROJECT_ID} · reference/ ${entries.length}건 후보 (force=${args.force})`,
  );

  let queued = 0;
  let skipped = 0;
  for (const [motionId, data] of entries) {
    const ref = db.collection('reference').doc(motionId);

    // idempotent — --force 미설정 시 이미 박제된 doc skip.
    if (!args.force) {
      const snap = await ref.get();
      const existing = snap.exists ? snap.data() : null;
      if (
        existing &&
        existing.bodyNormalizationProfile !== undefined &&
        existing.bodyComparisonSourcePose !== undefined
      ) {
        console.log(`  - skip ${motionId} — already has both fields (use --force)`);
        skipped++;
        continue;
      }
    }

    const docPayload = {
      bodyNormalizationProfile: data.bodyNormalizationProfile,
      bodyNormalizationProfileUpdatedAt: Date.now(),
    };
    if (data.bodyComparisonSourcePose) {
      docPayload.bodyComparisonSourcePose = data.bodyComparisonSourcePose;
      docPayload.bodyComparisonSourcePoseUpdatedAt = Date.now();
    }
    batch.set(ref, docPayload, { merge: true });
    console.log(
      `  - queued ${motionId} body_conf=${data.bodyNormalizationProfile.confidence} ` +
        `source_pose=${data.bodyComparisonSourcePose ? 'true' : 'false'}`,
    );
    queued++;
  }

  if (queued > 0) {
    await batch.commit();
    console.log(`[seed:body-profile] batch.commit OK — queued=${queued} skipped=${skipped}`);
  } else {
    console.log(`[seed:body-profile] batch 비어있음 — skipped=${skipped}`);
  }

  // 읽기 검증 — 각 motion 의 두 필드 존재 확인.
  console.log('\n[verify] reference 컬렉션 현재 상태:');
  const snap = await db.collection('reference').get();
  snap.forEach((d) => {
    const v = d.data() || {};
    const hasBP = v.bodyNormalizationProfile !== undefined;
    const hasSP = v.bodyComparisonSourcePose !== undefined;
    console.log(
      `  - ${d.id.padEnd(22)} bodyNormalizationProfile=${hasBP} ` +
        `bodyComparisonSourcePose=${hasSP}`,
    );
  });
}

main().catch((err) => {
  console.error('\n[seed:body-profile FAIL]', err?.message ?? err);
  if (String(err?.message ?? '').includes('Could not load the default credentials')) {
    console.error('→ ADC 미설정. 다음 명령 1회 실행 후 재시도:');
    console.error('    gcloud auth application-default login');
  }
  process.exit(1);
});
