// 정은지 reference 의 **두 필드 (bodyNormalizationProfile + bodyComparisonSourcePose,
// R2 정합)** 제거 (rollback). C12 fix (2026-06-08 reviews).
//
// 백필이 잘못된 데이터로 reference 컬렉션을 오염시킬 경우 실행. FieldValue.delete()
// 로 두 필드 모두 제거 — reference doc 자체는 유지. idempotent.
//
// 사용 예:
//   - dry-run 1차 (안전 기본값 — --commit 없으면 강제 dry-run):
//       cd app && npm run revert:body-profile -- --motion-ids ref-climb,ref-foxtop --dry-run
//   - 실 실행:
//       cd app && npm run revert:body-profile -- --motion-ids ref-climb,ref-foxtop --commit
//   - ADC 필수 (sunity3412@gmail.com, real-run only).
//
// per C12 (2026-06-08 reviews LOW) + R2 (round-2 — 두 필드 모두).

import { applicationDefault, initializeApp } from 'firebase-admin/app';
import { getFirestore, FieldValue } from 'firebase-admin/firestore';

const PROJECT_ID = 'sunity-ai-coach';

function parseArgs(argv) {
  const out = { motionIds: [], dryRun: false, commit: false };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--motion-ids' && i + 1 < argv.length) {
      out.motionIds = argv[i + 1]
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
      i++;
    } else if (argv[i] === '--dry-run') {
      out.dryRun = true;
    } else if (argv[i] === '--commit') {
      out.commit = true;
    } else if (argv[i] === '--help' || argv[i] === '-h') {
      console.log(
        'Usage: node revert-reference-body-profile.mjs --motion-ids <id1,id2,...> [--dry-run|--commit]',
      );
      process.exit(0);
    }
  }
  return out;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args.motionIds.length === 0) {
    throw new Error('--motion-ids required (no bulk-revert allowed)');
  }

  // 안전 기본값 — --dry-run / --commit 중 어느 것도 명시되지 않으면 강제 dry-run.
  if (!args.dryRun && !args.commit) {
    console.log('No --commit flag — forcing --dry-run for safety');
    args.dryRun = true;
  }

  // dry-run: Firebase 미접촉 (ADC 의존 X — R7 정신 정합).
  if (args.dryRun) {
    console.log(
      JSON.stringify(
        {
          dryRun: true,
          willDelete: args.motionIds.map((id) => ({
            motionId: id,
            fields: [
              'bodyNormalizationProfile',
              'bodyNormalizationProfileUpdatedAt',
              'bodyComparisonSourcePose',
              'bodyComparisonSourcePoseUpdatedAt',
            ],
          })),
        },
        null,
        2,
      ),
    );
    return;
  }

  // real-run.
  initializeApp({ credential: applicationDefault(), projectId: PROJECT_ID });
  const db = getFirestore();
  const batch = db.batch();

  for (const id of args.motionIds) {
    // R2 정합 — 두 필드 모두 FieldValue.delete().
    batch.update(db.collection('reference').doc(id), {
      bodyNormalizationProfile: FieldValue.delete(),
      bodyNormalizationProfileUpdatedAt: FieldValue.delete(),
      bodyComparisonSourcePose: FieldValue.delete(),
      bodyComparisonSourcePoseUpdatedAt: FieldValue.delete(),
    });
    console.log(
      `  - revert ${id} — bodyNormalizationProfile + bodyComparisonSourcePose 제거 (FieldValue.delete)`,
    );
  }
  await batch.commit();
  console.log(`reverted ${args.motionIds.length} reference docs (두 필드 모두)`);
}

main().catch((err) => {
  console.error('\n[revert:body-profile FAIL]', err?.message ?? err);
  if (String(err?.message ?? '').includes('Could not load the default credentials')) {
    console.error('→ ADC 미설정. 다음 명령 1회 실행 후 재시도:');
    console.error('    gcloud auth application-default login');
  }
  process.exit(1);
});
