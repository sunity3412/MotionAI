// 정은지 reference 11개의 downstream 4필드 (meanAngles + techniqueProfile +
// bodyNormalizationProfile + forceDirectionPattern) ADD-only merge seeder.
// JSON fixture (backfill_reference_downstream.py 산출, R2-5 split) → Firestore
// reference/{motionId} merge.
//
// R2-5 핵심: fixture 의 `seedPayload` 만 읽는다. `diagnostics` (hashes/deltas/
//   forceSignalsReportSummary/force-config provenance) 는 읽거나 검증하거나 seed
//   하지 않는다.
// R3 — skip rule: PHASE14_REQUIRED 전부 present+valid AND --force false 일 때만 skip.
//   default = repair-missing (누락 필드만 merge). --force = 기존 valid 필드도 덮어쓰기.
//   dry-run summary = skippedComplete / repairMissing / forceOverwrite 분리.
// R5 — all-or-nothing: --motions 미지정 real-run 은 seedPayload 가 정확히 11 id 일 때만.
//   부분 repair 는 명시적 `--motions <ids> --repair-missing` 로만.
// R3-1 — forceDirectionPattern 은 SCOPED validator (Python _validate_force_pattern_inference
//   mirror): top-level warnings:string[] + findings:[whitelisted] + findings[].warnings:
//   string[] 허용. meanAngles/techniqueProfile/bodyNormalizationProfile 는 generic
//   nested-array rejection.
//
// 사용:
//   - 사전 (real-run 만): gcloud auth application-default login   # sunity3412@gmail.com
//   - dry-run:  cd app && node scripts/seed-reference-downstream.mjs --input ../reference-downstream-backfill.json --dry-run
//   - commit:   cd app && node scripts/seed-reference-downstream.mjs --input ../reference-downstream-backfill.json
//   - --force   기존 valid 필드 덮어쓰기 (default = repair-missing).
//   - --verify  11개 reference 의 4 신필드 + captureViews 존재/완전성 read-back.
//
// per D-02 + D-04 + R3 + R5 + R2-5 + R3-1 + [[firebase-project-account]] +
//   [[firestore-nested-array-flat]] + Plan 14-02 Task 2.

import { readFileSync } from 'node:fs';

const PROJECT_ID = 'sunity-ai-coach';

// 11-id 전체 (Pitfall 1 / [[reference-library-phase4-all11]]).
const ALL_MOTION_IDS = [
  'ref-climb',
  'ref-foxtop',
  'ref-foxtop-split',
  'ref-invert',
  'ref-sideway-spin',
  'ref-combo',
  'ref-elbow-twist-sister',
  'ref-kip-up',
  'ref-pdshape',
  'ref-peter-pan',
  'ref-power-spin',
];

// Phase-14 필수 set — 이 5개가 모두 present+valid 면 'complete'.
const PHASE14_REQUIRED = [
  'meanAngles',
  'techniqueProfile',
  'bodyNormalizationProfile',
  'forceDirectionPattern',
  'captureViews',
];

// forceDirectionPattern.findings[] 의 whitelisted scalar key (R3-1 —
// Python _validate_force_pattern_finding_dict / _FORCE_PATTERN_FINDING_KEYS mirror).
const FORCE_PATTERN_FINDING_KEYS = new Set([
  'pattern',
  'phase',
  'sourceSignal',
  'reason',
  'interpretation',
  'confidence',
  'jointHint',
  'warnings',
]);

function parseArgs(argv) {
  const out = {
    input: null,
    force: false,
    dryRun: false,
    verify: false,
    repairMissing: false,
    motions: null,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--input' && i + 1 < argv.length) {
      out.input = argv[++i];
    } else if (a === '--force') {
      out.force = true;
    } else if (a === '--dry-run') {
      out.dryRun = true;
    } else if (a === '--verify') {
      out.verify = true;
    } else if (a === '--repair-missing') {
      out.repairMissing = true;
    } else if (a === '--motions' && i + 1 < argv.length) {
      out.motions = argv[++i]
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
    } else if (a === '--help' || a === '-h') {
      console.log(
        'Usage: node seed-reference-downstream.mjs --input <json> ' +
          '[--dry-run] [--force] [--verify] [--repair-missing] [--motions <ids>]',
      );
      process.exit(0);
    }
  }
  return out;
}

// ── generic nested-array rejection (3 flat dict) ───────────────────────────
function rejectNestedArray(motionId, field, value) {
  if (value === null || value === undefined) {
    return;
  }
  if (typeof value !== 'object') {
    return; // scalar.
  }
  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i++) {
      if (Array.isArray(value[i])) {
        throw new Error(
          `[${motionId}] ${field}[${i}] nested array 금지 (firestore-nested-array-flat)`,
        );
      }
      if (value[i] !== null && typeof value[i] === 'object') {
        // flat dict 안 list[dict] 의 entry 는 scalar only.
        rejectNestedDictEntry(motionId, `${field}[${i}]`, value[i]);
      }
    }
    return;
  }
  // dict — 재귀.
  for (const [k, v] of Object.entries(value)) {
    rejectNestedArray(motionId, `${field}.${k}`, v);
  }
}

function rejectNestedDictEntry(motionId, field, entry) {
  for (const [k, v] of Object.entries(entry)) {
    if (v !== null && typeof v === 'object') {
      throw new Error(
        `[${motionId}] ${field}.${k} list-of-dict entry 안 nested 금지 ` +
          `(firestore-nested-array-flat)`,
      );
    }
  }
}

// ── scoped forceDirectionPattern validator (R3-1) ──────────────────────────
// Python _validate_force_pattern_inference mirror: top-level warnings:string[] +
// findings:[whitelisted objects] + findings[].warnings:string[] 허용; 그 외 nested
// list/dict 또는 unknown finding key reject.
function validateForceDirectionPattern(motionId, fdp) {
  if (fdp === null || fdp === undefined) {
    throw new Error(`[${motionId}] forceDirectionPattern 없음`);
  }
  if (typeof fdp !== 'object' || Array.isArray(fdp)) {
    throw new Error(`[${motionId}] forceDirectionPattern 가 object 아님`);
  }
  for (const [key, value] of Object.entries(fdp)) {
    if (value === null || ['string', 'number', 'boolean'].includes(typeof value)) {
      continue; // scalar.
    }
    if (Array.isArray(value)) {
      if (key === 'warnings') {
        assertStringArray(motionId, `forceDirectionPattern.${key}`, value);
        continue;
      }
      if (key === 'findings') {
        if (value.length > 3) {
          throw new Error(
            `[${motionId}] forceDirectionPattern.findings length > 3 ` +
              `(D-09-B4 fabrication 금지)`,
          );
        }
        value.forEach((f, i) =>
          validateFinding(motionId, `forceDirectionPattern.findings[${i}]`, f),
        );
        continue;
      }
      throw new Error(
        `[${motionId}] forceDirectionPattern.${key} unexpected list ` +
          `(only 'warnings' / 'findings' allowed)`,
      );
    }
    // nested dict at top-level — reject.
    throw new Error(
      `[${motionId}] forceDirectionPattern.${key} unexpected nested dict`,
    );
  }
}

function validateFinding(motionId, path, finding) {
  if (finding === null || typeof finding !== 'object' || Array.isArray(finding)) {
    throw new Error(`[${motionId}] ${path} must be object`);
  }
  for (const [k, v] of Object.entries(finding)) {
    if (!FORCE_PATTERN_FINDING_KEYS.has(k)) {
      throw new Error(
        `[${motionId}] ${path}.${k} key not in force_pattern_finding whitelist`,
      );
    }
    if (v === null || ['string', 'number', 'boolean'].includes(typeof v)) {
      continue;
    }
    if (Array.isArray(v)) {
      if (k !== 'warnings') {
        throw new Error(
          `[${motionId}] ${path}.${k} list field not in finding whitelist ` +
            `(only 'warnings' list allowed)`,
        );
      }
      assertStringArray(motionId, `${path}.${k}`, v);
      continue;
    }
    throw new Error(
      `[${motionId}] ${path}.${k} nested dict in finding entry not allowed`,
    );
  }
}

function assertStringArray(motionId, path, arr) {
  for (let i = 0; i < arr.length; i++) {
    const item = arr[i];
    if (Array.isArray(item) || (item !== null && typeof item === 'object')) {
      throw new Error(`[${motionId}] ${path}[${i}] nested 금지 (list[str] only)`);
    }
    if (typeof item !== 'string' || item.length === 0) {
      throw new Error(
        `[${motionId}] ${path}[${i}] must be non-empty string warning code`,
      );
    }
  }
}

// ── per-motion seedPayload 검증 ────────────────────────────────────────────
function validateSeedEntry(motionId, entry) {
  if (!entry || typeof entry !== 'object') {
    throw new Error(`[${motionId}] seedPayload entry 가 object 아님`);
  }
  for (const f of PHASE14_REQUIRED) {
    if (!(f in entry)) {
      throw new Error(`[${motionId}] seedPayload 필수 필드 누락: ${f}`);
    }
  }
  if (
    !entry.meanAngles ||
    typeof entry.meanAngles !== 'object' ||
    Object.keys(entry.meanAngles).length === 0
  ) {
    throw new Error(`[${motionId}] meanAngles 비어있음/잘못됨`);
  }
  // 3 flat dict — generic nested-array rejection.
  rejectNestedArray(motionId, 'meanAngles', entry.meanAngles);
  rejectNestedArray(motionId, 'techniqueProfile', entry.techniqueProfile);
  rejectNestedArray(
    motionId,
    'bodyNormalizationProfile',
    entry.bodyNormalizationProfile,
  );
  // forceDirectionPattern — SCOPED validator (R3-1).
  validateForceDirectionPattern(motionId, entry.forceDirectionPattern);
  if (typeof entry.captureViews !== 'number') {
    throw new Error(`[${motionId}] captureViews 가 number 아님`);
  }
}

// fixture 의 seedPayload 만 로드 + 검증 (R2-5 — diagnostics 미접촉).
function loadSeedPayload(path) {
  const raw = readFileSync(path, 'utf8');
  const data = JSON.parse(raw);
  if (!data.seedPayload || typeof data.seedPayload !== 'object') {
    throw new Error(
      `잘못된 fixture: ${path} — seedPayload 객체 없음 (R2-5 split fixture 필요)`,
    );
  }
  for (const [motionId, entry] of Object.entries(data.seedPayload)) {
    validateSeedEntry(motionId, entry);
  }
  return data.seedPayload; // diagnostics 는 절대 반환/검증하지 않는다.
}

// 기존 doc 가 PHASE14_REQUIRED 전부 present+valid 인지 (skip 판정용, R3).
function hasAllRequired(existing) {
  if (!existing) {
    return false;
  }
  return PHASE14_REQUIRED.every(
    (f) => existing[f] !== undefined && existing[f] !== null,
  );
}

async function main() {
  // ──────────────────────────────────────────────────────────────────────
  // Step 1 — parse + load + validate (Firebase 미접촉, ADC 의존 X).
  // ──────────────────────────────────────────────────────────────────────
  const args = parseArgs(process.argv.slice(2));
  if (!args.input) {
    console.error('--input <json> required');
    process.exit(1);
  }
  const seedPayload = loadSeedPayload(args.input);
  const ids = Object.keys(seedPayload);

  // R5 — all-or-nothing: --motions 미지정 real-run 은 정확히 11 id 일 때만.
  const isSubsetRun = args.motions && args.motions.length > 0;
  if (!args.dryRun && !args.verify && !isSubsetRun) {
    if (ids.length !== ALL_MOTION_IDS.length) {
      console.error(
        `[seed FAIL] seedPayload 가 ${ids.length}개 — real-run 은 정확히 ` +
          `${ALL_MOTION_IDS.length}개 필요 (R5 all-or-nothing). 부분 repair 는 ` +
          `'--motions <ids> --repair-missing' 로만.`,
      );
      process.exit(1);
    }
  }

  // 대상 id — subset run 이면 명시 id 만, 아니면 전체 seedPayload.
  const targetIds = isSubsetRun
    ? args.motions.filter((m) => ids.includes(m))
    : ids;
  if (isSubsetRun && !args.repairMissing && !args.dryRun) {
    console.error(
      '[seed FAIL] --motions subset real-run 은 --repair-missing 명시 필요 (R5).',
    );
    process.exit(1);
  }

  // ──────────────────────────────────────────────────────────────────────
  // Step 2 — dry-run 분기 (Firebase init 전 early return, ADC-safe).
  //   R3 — skippedComplete / repairMissing / forceOverwrite 분리.
  //   dry-run 은 기존 doc 상태를 모르므로 (Firebase 미접촉) 잠재 분류만 표기.
  // ──────────────────────────────────────────────────────────────────────
  if (args.dryRun) {
    console.log(
      JSON.stringify(
        {
          dryRun: true,
          force: args.force,
          inputIds: ids,
          targetIds,
          note:
            '실제 skippedComplete/repairMissing/forceOverwrite 분류는 real-run 시 ' +
            '기존 doc 상태로 결정. dry-run 은 Firebase 미접촉 (ADC-safe).',
          willConsider: targetIds.length,
        },
        null,
        2,
      ),
    );
    return; // Firebase init 호출 X.
  }

  // ──────────────────────────────────────────────────────────────────────
  // Step 3 — real-run / verify. Firebase Admin SDK + ADC.
  // ──────────────────────────────────────────────────────────────────────
  const { applicationDefault, initializeApp } = await import('firebase-admin/app');
  const { getFirestore } = await import('firebase-admin/firestore');

  initializeApp({ credential: applicationDefault(), projectId: PROJECT_ID });
  const db = getFirestore();

  // --verify — 11개 reference 의 4 신필드 + captureViews 존재/완전성 read-back.
  if (args.verify) {
    console.log('[verify] reference downstream 4필드 + captureViews 현황:');
    let completeCount = 0;
    for (const motionId of ALL_MOTION_IDS) {
      const snap = await db.collection('reference').doc(motionId).get();
      const v = snap.exists ? snap.data() || {} : {};
      const present = PHASE14_REQUIRED.map(
        (f) => `${f}=${v[f] !== undefined && v[f] !== null}`,
      );
      const complete = hasAllRequired(v);
      if (complete) completeCount++;
      console.log(`  - ${motionId.padEnd(24)} ${present.join(' ')} complete=${complete}`);
    }
    console.log(
      `[verify] completeRequiredSet = ${completeCount}/${ALL_MOTION_IDS.length}`,
    );
    return;
  }

  const batch = db.batch();
  let queuedComplete = 0; // skippedComplete
  let queuedRepair = 0; // repairMissing
  let queuedOverwrite = 0; // forceOverwrite
  const now = Date.now();

  for (const motionId of targetIds) {
    const entry = seedPayload[motionId];
    const ref = db.collection('reference').doc(motionId);
    const snap = await ref.get();
    const existing = snap.exists ? snap.data() : null;
    const complete = hasAllRequired(existing);

    // R3 skip rule — 전부 present+valid AND --force false → skip.
    if (complete && !args.force) {
      console.log(`  - skipComplete ${motionId} (전 필드 valid, --force 로 덮어쓰기)`);
      queuedComplete++;
      continue;
    }

    // 어떤 필드를 쓸지: --force → 전체, 아니면 누락 필드만 (repair-missing).
    const docPayload = {};
    for (const f of PHASE14_REQUIRED) {
      const fieldMissing = !existing || existing[f] === undefined || existing[f] === null;
      if (args.force || fieldMissing) {
        docPayload[f] = entry[f];
        docPayload[`${f}UpdatedAt`] = now;
      }
    }
    if (Object.keys(docPayload).length === 0) {
      console.log(`  - skipComplete ${motionId} (쓸 필드 없음)`);
      queuedComplete++;
      continue;
    }
    // ADD-only — joints3d/angles/activeVersion 절대 미포함 (Pitfall 4 / D-02).
    batch.set(ref, docPayload, { merge: true });
    if (args.force) {
      queuedOverwrite++;
      console.log(`  - forceOverwrite ${motionId} fields=${Object.keys(docPayload).length}`);
    } else {
      queuedRepair++;
      console.log(`  - repairMissing ${motionId} fields=${Object.keys(docPayload).length}`);
    }
  }

  const queued = queuedRepair + queuedOverwrite;
  if (queued > 0) {
    await batch.commit();
  }
  console.log(
    `[seed:downstream] batch.commit ${queued > 0 ? 'OK' : '(empty)'} — ` +
      `skippedComplete=${queuedComplete} repairMissing=${queuedRepair} ` +
      `forceOverwrite=${queuedOverwrite}`,
  );
}

main().catch((err) => {
  console.error('\n[seed:downstream FAIL]', err?.message ?? err);
  if (String(err?.message ?? '').includes('Could not load the default credentials')) {
    console.error('→ ADC 미설정. 다음 명령 1회 실행 후 재시도:');
    console.error('    gcloud auth application-default login');
  }
  process.exit(1);
});
