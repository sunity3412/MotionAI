// 정은지 선수 기준 모션 시드 (plan.md #11, IA AC-ADMIN 관리자 등록).
//
// 사용법:
//   1) (최초 1회) gcloud auth application-default login  ← 키 파일 X, 브라우저 로그인
//      sunity3412@gmail.com (sunity-ai-coach 프로젝트 소유 계정) 선택
//   2) cd app && npm run seed:reference
//
// 보안 규칙(firestore.rules)이 reference/** 쓰기를 차단하므로 client SDK 로는
// 불가. Admin SDK + Application Default Credentials 로 규칙 우회 (관리자 컨텍스트).
//
// 모션 데이터:
//   - 파일럿 최소요건(루트 CLAUDE.md §2): 기초 1~2 + 중급 1
//   - motionId 는 안정적 슬러그(시뮬레이션과 호환). idempotent: 재실행해도 같은 doc 갱신.
//   - 키포인트 각도 등 분석용 데이터는 #7-follow ML 단에서 채움.

import { applicationDefault, initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';

const PROJECT_ID = 'sunity-ai-coach';
const ATHLETE = '정은지';

// motionId | name | level | description
const MOTIONS = [
  {
    motionId: 'ref-inside-leg-hang',
    name: '인사이드 레그 행',
    level: 'basic',
    description:
      '폴 안쪽 다리로 몸을 걸어 매달리는 기초 자세. 회전 진입 전 균형감 확인용.',
  },
  {
    motionId: 'ref-basic-grip',
    name: '기본 그립',
    level: 'basic',
    description:
      '폴 손잡이 자세의 기본형. 손가락 위치·팔꿈치 정렬을 익히는 단계.',
  },
  {
    motionId: 'ref-fireman-spin',
    name: '파이어맨 스핀',
    level: 'intermediate',
    description:
      '폴에 기대어 회전하는 중급 기술. 회전 진입 시 골반·무릎 가동이 핵심.',
  },
];

async function main() {
  initializeApp({ credential: applicationDefault(), projectId: PROJECT_ID });
  const db = getFirestore();

  console.log(`[seed] 프로젝트 ${PROJECT_ID} · reference/ 컬렉션에 ${MOTIONS.length}건 쓰기`);
  const batch = db.batch();
  for (const m of MOTIONS) {
    const ref = db.collection('reference').doc(m.motionId);
    batch.set(
      ref,
      {
        motionId: m.motionId,
        name: m.name,
        athleteName: ATHLETE,
        level: m.level,
        description: m.description,
        isActive: true,
        updatedAt: Date.now(),
      },
      { merge: true },
    );
    console.log(`  - ${m.motionId.padEnd(22)} ${m.level.padEnd(12)} ${m.name}`);
  }
  await batch.commit();

  // 결과 확인 — 앱이 보게 될 그대로 다시 읽어 출력.
  console.log('\n[verify] 컬렉션 현재 상태:');
  const snap = await db.collection('reference').get();
  if (snap.empty) {
    console.log('  (비어 있음 — 쓰기 권한 또는 프로젝트 ID 확인)');
  } else {
    snap.forEach((d) => {
      const v = d.data();
      console.log(`  - ${d.id.padEnd(22)} ${String(v.level).padEnd(12)} ${v.name}`);
    });
  }
  console.log('\n시드 완료. 앱에서 /analysis/reference 화면이 즉시 반영됨(onSnapshot).');
}

main().catch((err) => {
  console.error('\n[seed FAIL]', err?.message ?? err);
  if (String(err?.message ?? '').includes('Could not load the default credentials')) {
    console.error('→ ADC 미설정. 다음 명령 1회 실행 후 재시도:');
    console.error('    gcloud auth application-default login');
  }
  process.exit(1);
});
