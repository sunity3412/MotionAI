// reference 컬렉션 11개 doc 의 백필 필드 존재 여부 read-only 감사 (A2 해소).
//
// 목적: Phase 14 백필(14-02/14-03) 진입 전에, 11개 정은지 reference 가
// meanAngles / EXTEND(techniqueProfile) / bodyNormalizationProfile /
// forceDirectionPattern / captureViews 등 다운스트림 필드를 이미 갖고 있는지
// (또는 누락했는지) 운영자(belle)가 GPU 없이 즉시 확인할 수 있게 한다.
// 14-RESEARCH A2: 나중에 추가된 6개(ref-combo / ref-elbow-twist-sister /
// ref-kip-up / ref-pdshape / ref-peter-pan / ref-power-spin)는
// extract_reference_body_profiles.py DEFAULT_MOTION_IDS 가 원래 5개라
// bodyNormalizationProfile 이 없을 가능성이 큼 — 이 스크립트가 그 사실을 확정한다.
//
// D-04 (admin CLI — 운영자가 CLI 로 등록/백필) + [[reference-library-phase4-all11]]
// (전체 11개 = phase4_v1 active, reprocess 스크립트 default 가 5라 신규는 명시 필요)
// + Pitfall 1 (default-5 motion-ID trap — 절대 5개 subset 으로 돌리지 말 것).
//
// 보안: T-14-01 (Information Disclosure) — ADC/SA 자격증명 내용은 절대 출력하지 않는다.
// 필드의 "존재 여부(키)"만 로깅하고 "값"은 로깅하지 않는다.
//
// READ-ONLY: .get() 읽기만 수행. set/merge/batch 호출 0회 (T-14-03 — Tampering 방지).
// 현재 Firestore 상태 그대로를 읽으므로 오늘 바로 실행 가능.
//
// 사용:
//   - 사전: gcloud auth application-default login   # sunity3412@gmail.com
//   - 실행: cd app && node scripts/audit-reference-fields.mjs
//
// per D-04 + [[reference-library-phase4-all11]] + [[firebase-project-account]] + A2.

const PROJECT_ID = 'sunity-ai-coach';

// [[reference-library-phase4-all11]] + Pitfall 1 — 5개 subset 절대 금지.
// 원래 5개 (Wave-5 originals) + 나중에 추가된 6개 = 전체 11개 union 을 명시.
const ALL_MOTION_IDS = [
  // 원래 5개 (extract_reference_body_profiles.py DEFAULT_MOTION_IDS)
  'ref-climb',
  'ref-foxtop',
  'ref-foxtop-split',
  'ref-invert',
  'ref-sideway-spin',
  // 나중에 추가된 6개 (A2 — bodyNormalizationProfile 미보유 의심 대상)
  'ref-combo',
  'ref-elbow-twist-sister',
  'ref-kip-up',
  'ref-pdshape',
  'ref-peter-pan',
  'ref-power-spin',
];

// 존재 여부를 점검할 필드 목록 (top-level mirror 기준).
const AUDIT_FIELDS = [
  'meanAngles',
  'angles',
  'anglesJointKeys',
  'anglesFrames',
  'bodyNormalizationProfile',
  'bodyComparisonSourcePose',
  'techniqueProfile',
  'forceDirectionPattern',
  'captureViews',
  'activeVersion',
];

// R3 seeder skip 규칙 — 14-02 Task 2 가 skipComplete vs repairMissing 를
// 구분할 수 있도록, Phase-14 가 요구하는 5개 필드가 모두 있는 reference 를 센다.
const PHASE14_REQUIRED_FIELDS = [
  'meanAngles',
  'techniqueProfile',
  'bodyNormalizationProfile',
  'forceDirectionPattern',
  'captureViews',
];

function hasField(data, field) {
  // 존재 = 키가 정의되어 있고 null/undefined 가 아님.
  return data != null && data[field] !== undefined && data[field] !== null;
}

async function main() {
  // ADC 의존 — lazy import (validate-before-init 패턴, seed-reference-body-profile.mjs 정합).
  const { applicationDefault, initializeApp } = await import('firebase-admin/app');
  const { getFirestore } = await import('firebase-admin/firestore');

  initializeApp({ credential: applicationDefault(), projectId: PROJECT_ID });
  const db = getFirestore();

  console.log(
    `[audit] 프로젝트 ${PROJECT_ID} · reference/ ${ALL_MOTION_IDS.length}개 read-only 감사\n`,
  );

  // per-field present count + completeRequiredSet count 집계.
  const fieldPresentCount = Object.fromEntries(
    AUDIT_FIELDS.map((f) => [f, 0]),
  );
  let completeRequiredSet = 0;
  let missingDocs = 0;

  // 헤더 — 필드 약어 (값 아님, 키만).
  const header = ['motionId'.padEnd(24), ...AUDIT_FIELDS.map((f) => f.slice(0, 6).padEnd(7))].join(
    ' ',
  );
  console.log(header);
  console.log('-'.repeat(header.length));

  for (const motionId of ALL_MOTION_IDS) {
    // READ ONLY — .get() 만 사용.
    const snap = await db.collection('reference').doc(motionId).get();
    if (!snap.exists) {
      missingDocs++;
      console.log(`${motionId.padEnd(24)} (doc 없음)`);
      continue;
    }
    const data = snap.data() || {};

    const cells = AUDIT_FIELDS.map((f) => {
      const present = hasField(data, f);
      if (present) fieldPresentCount[f]++;
      return (present ? 'Y' : '-').padEnd(7);
    });
    console.log([motionId.padEnd(24), ...cells].join(' '));

    const complete = PHASE14_REQUIRED_FIELDS.every((f) => hasField(data, f));
    if (complete) completeRequiredSet++;
  }

  // 요약 — per-field present-count + completeRequiredSet.
  console.log('\n[summary] per-field present-count (Y / 11):');
  for (const f of AUDIT_FIELDS) {
    console.log(`  - ${f.padEnd(28)} ${fieldPresentCount[f]} / ${ALL_MOTION_IDS.length}`);
  }
  console.log(
    `\n[summary] completeRequiredSet (${PHASE14_REQUIRED_FIELDS.join(' + ')} 모두 보유): ` +
      `${completeRequiredSet} / ${ALL_MOTION_IDS.length}`,
  );
  if (missingDocs > 0) {
    console.log(`[summary] doc 자체 없음: ${missingDocs}`);
  }
  console.log(
    '\n[summary] 14-02 Task 2 백필: completeRequiredSet 외 reference 는 repairMissing 대상, ' +
      'complete 는 --force 없으면 skipComplete.',
  );
}

main().catch((err) => {
  // T-14-01 — 자격증명 내용 출력 금지. message 만 노출.
  console.error('\n[audit FAIL]', err?.message ?? err);
  if (String(err?.message ?? '').includes('Could not load the default credentials')) {
    console.error('→ ADC 미설정. 다음 명령 1회 실행 후 재시도:');
    console.error('    gcloud auth application-default login   # sunity3412@gmail.com');
  }
  process.exit(1);
});
