// Phase 14 reference 백필 RESTORE-aware 롤백 (R2-1 + R4 incident 대응).
//
// 목적: pre-seed 스냅샷(14-PRESEED-SNAPSHOT.json)을 읽어, 11개 reference 의 Phase-14 필드
// (meanAngles / techniqueProfile / bodyNormalizationProfile / forceDirectionPattern /
// captureViews + 각 *UpdatedAt + bodyComparisonSourcePose + optional provenance) 를
// 백필 직전 상태로 되돌린다:
//   - seed 전 ABSENT (snapshot present:false) 였던 필드 → FieldValue.delete()
//   - seed 전 EXISTED (snapshot present:true) 였던 필드 → set(merge) 로 정확한 이전 value 복원
// delete-only 롤백은 --force overwrite / repair 이전 값을 잃으므로 restore-aware 가 필수다 (R2-1).
//
// active-pose (joints3d/angles/activeVersion/anglesJointKeys/anglesFrames) 는 절대 건드리지 않는다
// (애초에 관리 필드 목록에 없음). active 필드가 바뀌었다면 그건 별도 incident 이며 이 스크립트로 복구 금지.
//
// --dry-run (default) → 무엇을 delete/restore 할지 미리보기, Firestore 미접촉.
// --confirm           → 실제 실행.
//
// 사용: cd app && node scripts/rollback-reference-downstream.mjs [--confirm] [--motions a,b]
// per R2-1/R4 + [[firebase-project-account]].

import { readFileSync } from 'node:fs';

const PROJECT_ID = 'sunity-ai-coach';

const ALL_MOTION_IDS = [
  'ref-climb', 'ref-foxtop', 'ref-foxtop-split', 'ref-invert', 'ref-sideway-spin',
  'ref-combo', 'ref-elbow-twist-sister', 'ref-kip-up', 'ref-pdshape', 'ref-peter-pan', 'ref-power-spin',
];

// 롤백이 관리하는 Phase-14 필드 (active-pose 는 의도적으로 제외 — 절대 touch 안 함).
const PHASE14_FIELDS = [
  'meanAngles', 'meanAnglesUpdatedAt',
  'techniqueProfile', 'techniqueProfileUpdatedAt',
  'bodyNormalizationProfile', 'bodyNormalizationProfileUpdatedAt',
  'forceDirectionPattern', 'forceDirectionPatternUpdatedAt',
  'captureViews', 'captureViewsUpdatedAt',
  'bodyComparisonSourcePose', 'bodyComparisonSourcePoseUpdatedAt',
  'forceDirectionPatternSource', 'forceSignalsWarnings',
];

// 절대 롤백 대상이 아닌 active-pose 필드 (가드 — payload 에 절대 못 들어가게).
const ACTIVE_POSE_FIELDS = new Set(['activeVersion', 'angles', 'joints3d', 'anglesJointKeys', 'anglesFrames']);

const PRESEED_PATH = '../.planning/phases/14-reference-motion-registration/14-PRESEED-SNAPSHOT.json';

function parseArgs(argv) {
  const out = { confirm: false, motions: null };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--confirm') out.confirm = true;
    else if (argv[i] === '--motions' && i + 1 < argv.length) { out.motions = argv[i + 1].split(',').map((s) => s.trim()).filter(Boolean); i++; }
    else if (argv[i] === '--help' || argv[i] === '-h') {
      console.log('Usage: node scripts/rollback-reference-downstream.mjs [--confirm] [--motions a,b]');
      process.exit(0);
    }
  }
  return out;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  let pre;
  try {
    pre = JSON.parse(readFileSync(PRESEED_PATH, 'utf8'));
  } catch (e) {
    console.error(`[rollback] pre-seed 스냅샷이 없습니다 (${PRESEED_PATH}). 스냅샷 없이는 복원 불가 — 중단.`);
    process.exit(1);
  }

  const targets = args.motions ?? ALL_MOTION_IDS;

  // 계획 수립 (Firestore 미접촉) — 각 필드 delete vs restore.
  const plan = [];
  for (const motionId of targets) {
    const m = pre.motions?.[motionId];
    if (!m || !m.exists) { console.log(`  - ${motionId} (pre 스냅샷에 doc 없음 — skip)`); continue; }
    const deletes = [];
    const restores = [];
    for (const f of PHASE14_FIELDS) {
      if (ACTIVE_POSE_FIELDS.has(f)) continue; // 가드 (절대 발생 안 함).
      const rec = m.phase14?.[f];
      if (!rec) continue;
      if (rec.present) {
        if (!('value' in rec)) {
          console.error(`[rollback] ${motionId}.${f} present:true 인데 value 없음 — pre 스냅샷이 keepValue=true 로 안 찍힘. 중단.`);
          process.exit(1);
        }
        restores.push({ field: f, value: rec.value });
      } else {
        deletes.push(f);
      }
    }
    plan.push({ motionId, deletes, restores });
  }

  console.log(`[rollback] pre-seed 스냅샷 기준 복원 계획 (${args.confirm ? 'CONFIRM 실행' : 'dry-run'}):`);
  for (const p of plan) {
    console.log(`  - ${p.motionId.padEnd(24)} delete=${p.deletes.length} restore=${p.restores.length}` +
      (p.deletes.length ? ` [del: ${p.deletes.join(',')}]` : ''));
  }

  if (!args.confirm) {
    console.log('\n[rollback] dry-run — Firestore 미접촉. 실제 복원하려면 --confirm.');
    return;
  }

  const { applicationDefault, initializeApp } = await import('firebase-admin/app');
  const { getFirestore, FieldValue } = await import('firebase-admin/firestore');
  initializeApp({ credential: applicationDefault(), projectId: PROJECT_ID });
  const db = getFirestore();
  const batch = db.batch();

  let ops = 0;
  for (const p of plan) {
    const ref = db.collection('reference').doc(p.motionId);
    const payload = {};
    for (const f of p.deletes) payload[f] = FieldValue.delete();
    for (const r of p.restores) payload[r.field] = r.value;
    // 가드 재확인 — active-pose 필드가 payload 에 절대 없어야 함.
    for (const k of Object.keys(payload)) {
      if (ACTIVE_POSE_FIELDS.has(k)) {
        console.error(`[rollback] FATAL — payload 에 active-pose 필드 ${k} 포함됨. 중단 (절대 발생 금지).`);
        process.exit(1);
      }
    }
    if (Object.keys(payload).length === 0) continue;
    batch.set(ref, payload, { merge: true });
    ops += Object.keys(payload).length;
  }

  if (ops > 0) {
    await batch.commit();
    console.log(`\n[rollback] batch.commit OK — ${ops} field ops (delete absent-before + restore present-before).`);
  } else {
    console.log('\n[rollback] 변경할 필드 없음.');
  }
}

main().catch((err) => {
  console.error('\n[rollback FAIL]', err?.message ?? err);
  if (String(err?.message ?? '').includes('Could not load the default credentials')) {
    console.error('→ ADC 미설정: gcloud auth application-default login   # sunity3412@gmail.com');
  }
  process.exit(1);
});
