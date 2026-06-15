// Phase 14 reference 백필 무결성 스냅샷 (R2-1 broadened snapshot + R4 byte-level gate + D-02).
//
// 목적: 11개 정은지 reference 의 (a) ACTIVE-POSE (activeVersion/angles/joints3d/
// anglesJointKeys/anglesFrames) 바이트 단위 sha256 해시 + (b) FULL PHASE-14 FIELD STATE
// (meanAngles / techniqueProfile / bodyNormalizationProfile / forceDirectionPattern /
// captureViews + 각 *UpdatedAt + bodyComparisonSourcePose + optional forceDirectionPatternSource /
// forceSignalsWarnings) 를 {present, valueHash, value?} 로 박제한다.
//
//   --mode pre  → ../.planning/.../14-PRESEED-SNAPSHOT.json 작성 (gitignored; restore 용 raw value 포함)
//   --mode post → 같은 필드 재read + active-pose 해시를 pre 와 byte-level 비교 →
//                 ../.planning/.../14-BACKFILL-RUN-SUMMARY.json 작성
//                 { unchangedActivePoseCount, changedActivePoseCount,
//                   completeDownstreamFieldCount, seededMotionCount, perMotion:[...] }
//                 active-pose 해시 mismatch 가 하나라도 있으면 exit 1 (D-02/R4 — incident).
//
// 보안 (T-14-10): active-pose 의 raw angles/joints3d 는 절대 저장/출력하지 않는다 — length + sha256 만.
//   run log 는 해시만, value-bearing pre-seed JSON 은 gitignored. ADC/SA 내용 출력 금지.
//
// active-pose 필드는 백필이 절대 쓰지 않으므로 (ADD-only) pre/post 가 byte-identical 이어야 한다.
//
// 사용: cd app && node scripts/snapshot-reference-phase14-state.mjs --mode pre|post
// per D-02/R4/R2-1 + [[reference-library-phase4-all11]] + [[firebase-project-account]].

import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const PROJECT_ID = 'sunity-ai-coach';

// [[reference-library-phase4-all11]] — 5 originals + 6 later = 11. 절대 5-subset 금지.
const ALL_MOTION_IDS = [
  'ref-climb', 'ref-foxtop', 'ref-foxtop-split', 'ref-invert', 'ref-sideway-spin',
  'ref-combo', 'ref-elbow-twist-sister', 'ref-kip-up', 'ref-pdshape', 'ref-peter-pan', 'ref-power-spin',
];

// 백필이 절대 건드리면 안 되는 active-pose 필드 (D-02). pre/post byte-identical 필수.
const ACTIVE_POSE_FIELDS = ['activeVersion', 'angles', 'joints3d', 'anglesJointKeys', 'anglesFrames'];

// Phase-14 가 ADD-only 로 쓰거나 repair 할 수 있는 필드 + *UpdatedAt + bodyComparison + optional provenance.
// (R2-1 — bodyNormalizationProfile/bodyComparisonSourcePose 도 rollback set 에 반드시 포함.)
const PHASE14_FIELDS = [
  'meanAngles', 'meanAnglesUpdatedAt',
  'techniqueProfile', 'techniqueProfileUpdatedAt',
  'bodyNormalizationProfile', 'bodyNormalizationProfileUpdatedAt',
  'forceDirectionPattern', 'forceDirectionPatternUpdatedAt',
  'captureViews', 'captureViewsUpdatedAt',
  'bodyComparisonSourcePose', 'bodyComparisonSourcePoseUpdatedAt',
  'forceDirectionPatternSource', 'forceSignalsWarnings',
];

// SC#2 — reference 가 갖춰야 할 5개 필수 다운스트림 필드.
const PHASE14_REQUIRED = [
  'meanAngles', 'techniqueProfile', 'bodyNormalizationProfile', 'forceDirectionPattern', 'captureViews',
];

const PHASE_DIR = '../.planning/phases/14-reference-motion-registration';
const PRESEED_PATH = `${PHASE_DIR}/14-PRESEED-SNAPSHOT.json`;
const SUMMARY_PATH = `${PHASE_DIR}/14-BACKFILL-RUN-SUMMARY.json`;

// 결정적 직렬화 (key 정렬) → 동일 값이면 동일 바이트 → 동일 해시.
function stableStringify(v) {
  if (v === null || typeof v !== 'object') return JSON.stringify(v) ?? 'null';
  if (Array.isArray(v)) return '[' + v.map(stableStringify).join(',') + ']';
  const keys = Object.keys(v).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + stableStringify(v[k])).join(',') + '}';
}
function sha256(s) { return createHash('sha256').update(s).digest('hex'); }
function hashValue(v) { return sha256(stableStringify(v)); }

function present(data, field) {
  return data != null && data[field] !== undefined && data[field] !== null;
}

function nonEmpty(v) {
  if (v === null || v === undefined) return false;
  if (Array.isArray(v)) return v.length > 0;
  if (typeof v === 'object') return Object.keys(v).length > 0;
  return true; // scalar (e.g. captureViews=1)
}

// active-pose 필드 1개를 {present, length?, valueHash} 로 (raw value 미저장 — 보안 T-14-10).
function snapActiveField(data, field) {
  if (!present(data, field)) return { present: false };
  const v = data[field];
  const rec = { present: true, valueHash: hashValue(v) };
  if (Array.isArray(v)) rec.length = v.length;
  // activeVersion / anglesFrames 같은 작은 scalar 는 비밀 아님 — 가독성 위해 값 보존.
  if (typeof v !== 'object') rec.value = v;
  return rec;
}

// Phase-14 필드 1개를 {present, valueHash, value?} 로. value 는 pre 모드(restore 용)에서만 저장.
function snapPhase14Field(data, field, keepValue) {
  if (!present(data, field)) return { present: false };
  const v = data[field];
  const rec = { present: true, valueHash: hashValue(v) };
  if (keepValue) rec.value = v;
  return rec;
}

async function readAll(db) {
  const out = {};
  for (const motionId of ALL_MOTION_IDS) {
    const snap = await db.collection('reference').doc(motionId).get();
    if (!snap.exists) { out[motionId] = { exists: false }; continue; }
    const data = snap.data() || {};
    // versions/phase4_v1 subdoc 존재 여부 (active pose 가 거기 보관될 수도 있어 기록만).
    let versionsPhase4V1Exists = false;
    try {
      const vsnap = await db.collection('reference').doc(motionId).collection('versions').doc('phase4_v1').get();
      versionsPhase4V1Exists = vsnap.exists;
    } catch { /* subcollection 없을 수 있음 — graceful */ }
    out[motionId] = { exists: true, data, versionsPhase4V1Exists };
  }
  return out;
}

function buildSnapshot(state, keepValue) {
  const motions = {};
  for (const motionId of ALL_MOTION_IDS) {
    const s = state[motionId];
    if (!s || !s.exists) { motions[motionId] = { exists: false }; continue; }
    const activePose = {};
    for (const f of ACTIVE_POSE_FIELDS) activePose[f] = snapActiveField(s.data, f);
    const phase14 = {};
    for (const f of PHASE14_FIELDS) phase14[f] = snapPhase14Field(s.data, f, keepValue);
    motions[motionId] = {
      exists: true,
      versionsPhase4V1Exists: s.versionsPhase4V1Exists,
      activePose,
      phase14,
    };
  }
  return { motionCount: ALL_MOTION_IDS.length, motions };
}

async function main() {
  let mode = null;
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--mode' && i + 1 < argv.length) { mode = argv[i + 1]; i++; }
    else if (argv[i] === '--help' || argv[i] === '-h') {
      console.log('Usage: node scripts/snapshot-reference-phase14-state.mjs --mode pre|post');
      process.exit(0);
    }
  }
  if (mode !== 'pre' && mode !== 'post') {
    console.error('--mode pre|post required');
    process.exit(1);
  }

  const { applicationDefault, initializeApp } = await import('firebase-admin/app');
  const { getFirestore } = await import('firebase-admin/firestore');
  initializeApp({ credential: applicationDefault(), projectId: PROJECT_ID });
  const db = getFirestore();

  const state = await readAll(db);

  if (mode === 'pre') {
    // restore 용 raw value 포함 — gitignored 파일에만 저장.
    const snapshot = buildSnapshot(state, /* keepValue */ true);
    snapshot.mode = 'pre';
    writeFileSync(PRESEED_PATH, JSON.stringify(snapshot, null, 2));
    console.log(`[snapshot pre] ${PRESEED_PATH} 작성 — ${ALL_MOTION_IDS.length} motions`);
    // 콘솔에는 해시/존재만 (raw value 출력 X — 보안).
    for (const motionId of ALL_MOTION_IDS) {
      const m = snapshot.motions[motionId];
      if (!m.exists) { console.log(`  - ${motionId.padEnd(24)} (doc 없음)`); continue; }
      const av = m.activePose.activeVersion;
      const ang = m.activePose.angles;
      const reqPresent = PHASE14_REQUIRED.filter((f) => m.phase14[f]?.present).length;
      console.log(
        `  - ${motionId.padEnd(24)} activeVersion=${av.present ? av.value : '-'} ` +
          `anglesHash=${ang.present ? ang.valueHash.slice(0, 12) : '-'} ` +
          `phase14Required=${reqPresent}/${PHASE14_REQUIRED.length}`,
      );
    }
    return;
  }

  // ── mode post — pre 와 byte-level 비교 + summary 작성 ───────────────────
  let pre;
  try {
    pre = JSON.parse(readFileSync(PRESEED_PATH, 'utf8'));
  } catch (e) {
    console.error(`[snapshot post] pre snapshot 읽기 실패 (${PRESEED_PATH}) — pre 모드 먼저 실행 필요.`);
    process.exit(1);
  }
  const post = buildSnapshot(state, /* keepValue */ false);

  let unchangedActivePoseCount = 0;
  let changedActivePoseCount = 0;
  let completeDownstreamFieldCount = 0;
  let seededMotionCount = 0;
  const perMotion = [];

  for (const motionId of ALL_MOTION_IDS) {
    const pm = pre.motions?.[motionId];
    const qm = post.motions[motionId];
    const postData = state[motionId]?.exists ? state[motionId].data : null;

    // active-pose byte-level 비교 (presence + hash 동일해야 unchanged).
    const activeDiffs = [];
    for (const f of ACTIVE_POSE_FIELDS) {
      const a = pm?.activePose?.[f] ?? { present: false };
      const b = qm.activePose?.[f] ?? { present: false };
      if (a.present !== b.present || (a.present && a.valueHash !== b.valueHash)) {
        activeDiffs.push(f);
      }
    }
    const activePoseUnchanged = activeDiffs.length === 0;
    if (activePoseUnchanged) unchangedActivePoseCount++; else changedActivePoseCount++;

    // 다운스트림 완성도 (post 기준, present + non-empty).
    const downstreamComplete = PHASE14_REQUIRED.every((f) => present(postData, f) && nonEmpty(postData[f]));
    if (downstreamComplete) completeDownstreamFieldCount++;
    // seeded = 4 신필드 모두 존재 (captureViews 포함 시 == required).
    const seeded = PHASE14_REQUIRED.every((f) => present(postData, f));
    if (seeded) seededMotionCount++;

    perMotion.push({
      motionId,
      activePoseUnchanged,
      activeDiffs,
      downstreamComplete,
      fields: Object.fromEntries(PHASE14_REQUIRED.map((f) => [f, present(postData, f)])),
    });
  }

  const summary = {
    generatedMode: 'post',
    motionCount: ALL_MOTION_IDS.length,
    unchangedActivePoseCount,
    changedActivePoseCount,
    completeDownstreamFieldCount,
    seededMotionCount,
    perMotion,
  };
  writeFileSync(SUMMARY_PATH, JSON.stringify(summary, null, 2));
  console.log(`[snapshot post] ${SUMMARY_PATH} 작성`);
  console.log(
    `  unchangedActivePoseCount=${unchangedActivePoseCount} changedActivePoseCount=${changedActivePoseCount} ` +
      `completeDownstreamFieldCount=${completeDownstreamFieldCount} seededMotionCount=${seededMotionCount}`,
  );
  for (const r of perMotion) {
    console.log(
      `  - ${r.motionId.padEnd(24)} activeUnchanged=${r.activePoseUnchanged} ` +
        `downstreamComplete=${r.downstreamComplete}` +
        (r.activeDiffs.length ? ` CHANGED:${r.activeDiffs.join(',')}` : ''),
    );
  }

  // D-02/R4 — active-pose 가 하나라도 바뀌면 incident → exit 1.
  if (changedActivePoseCount !== 0) {
    console.error(`\n[snapshot post] FAIL — active-pose 변경 감지 (changedActivePoseCount=${changedActivePoseCount}). incident.`);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error('\n[snapshot FAIL]', err?.message ?? err);
  if (String(err?.message ?? '').includes('Could not load the default credentials')) {
    console.error('→ ADC 미설정. 다음 명령 1회 실행 후 재시도:');
    console.error('    gcloud auth application-default login   # sunity3412@gmail.com');
  }
  process.exit(1);
});
