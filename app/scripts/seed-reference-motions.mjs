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
// 모션 데이터 — 단일 진실: docs/reference-motions.md §5.
//   - 정은지 선수 실영상 5개 분석 결과 (사이드웨이/클라임/인버트/폭스탑/폭스탑스플릿).
//   - motionId 는 안정적 슬러그 = doc ID = S3 키. idempotent: 재실행해도 같은 doc 갱신.
//   - clipRange/checkpoints 는 분석 런타임 입력. keyframe 각도(angles)는 #7-follow ML 단.
//   - 구간 공유 트리: ref-invert → ref-foxtop → ref-foxtop-split (베이스 공유).
//   - ⚠ checkpoint 가중치·peak·자유 다리 좌우 등은 추정 — MVP 시연 후 정은지 선수와 일괄 수정.

import { applicationDefault, initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';

const PROJECT_ID = 'sunity-ai-coach';
const ATHLETE = '정은지';
const VIDEO_PREFIX = 's3://sunity-motion-pilot-videos/reference';

// 정은지 선수 명칭 확정(2026-05-22) 전의 구 motionId — 새 ID 로 교체되며 폐기.
// 시드 시 함께 삭제. batch.delete 는 문서가 없어도 에러 없음 → idempotent.
const OBSOLETE_MOTION_IDS = [
  'ref-ballerina-spin',
  'ref-front-hook-spin',
  'ref-plank-spin',
  'ref-invert-butterfly-combo',
  'ref-gemini-to-ayesha-combo',
];

// reference-motions.md §5 등록된 모션 5개. checkpoints weight 합 = 1.0.
const MOTIONS = [
  {
    motionId: 'ref-sideway-spin',
    name: '사이드웨이 스핀',
    level: 'intermediate',
    entryType: 'swing_entry',
    entryDescription:
      '폴 옆에서 오른팔 상단 그립을 잡은 뒤 다리 스윙으로 회전력을 만들어 진입. 점프보다 스윙으로 만든 각운동량으로 폴을 감아오르며 시계 방향 회전 시작.',
    description:
      '상단 그립을 잡고 몸을 뒤로 아치한 채 한 다리를 연장한 자세로 연속 회전하는 중급 기술. 하나의 자세를 유지하는 것이 아니라 회전 중 백 아치 라인과 다리 라인이 자연스럽게 변형되며 이어진다.',
    clipRange: {
      prepStartS: 0,
      execStartS: 2,
      execPeakS: 9,
      landEndS: 18,
      recommendedRecordS: 22,
    },
    checkpoints: [
      { joint: 'right_shoulder', weight: 0.2, note: '주 지지 팔(오른손 상단 그립)의 견갑 안정성. 어깨가 올라가면 회전축이 흔들려 백 아치 라인이 흐트러짐' },
      { joint: 'spine_mid', weight: 0.25, note: '척추 아치 곡률. 허리만 꺾이지 않고 흉추까지 함께 열려야 발레 라인이 살아남' },
      { joint: 'left_hip', weight: 0.2, note: '자유 다리 측 고관절 신전. 신전 부족하면 아치가 얕아짐 (자유 다리 좌우는 추정)' },
      { joint: 'left_knee', weight: 0.2, note: '자유 다리 신전. 무릎 굽으면 발레 라인이 무너지고 chair spin처럼 보임 (좌우 추정)' },
      { joint: 'right_hip', weight: 0.15, note: '폴 측 고관절 정렬. 회전 중 골반이 닫히면 백 아치가 깊어지지 못함' },
    ],
  },
  {
    motionId: 'ref-climb',
    name: '클라임',
    level: 'basic',
    entryType: 'swing_entry',
    entryDescription:
      '폴 옆에서 오른팔 상단 그립을 잡은 뒤 다리 스윙으로 반동을 만들어 몸을 띄우며 양 무릎을 X자 형태로 폴에 건다.',
    description:
      '상단 그립을 잡고 양 무릎을 폴 앞뒤에 X자로 걸어 연속 회전하는 기초 스핀. 왼쪽 무릎이 폴 앞, 오른쪽 무릎이 폴 뒤를 잡아 두 무릎이 폴을 사이에 두고 교차한다. 두 무릎의 접촉 안정성이 체공 시간과 회전 매끄러움을 결정한다.',
    clipRange: {
      prepStartS: 0,
      execStartS: 1.5,
      execPeakS: 5,
      landEndS: 15,
      recommendedRecordS: 18,
    },
    checkpoints: [
      { joint: 'left_knee', weight: 0.25, note: '폴 앞쪽 훅 다리. 먼저 걸리는 쪽이라 진입 안정성 핵심. 깊게 닿지 않으면 X자 잠금이 약해져 미끄러짐' },
      { joint: 'right_knee', weight: 0.2, note: '폴 뒤쪽 훅 다리. 앞 무릎과 X자로 폴 잠금 완성. 풀리면 회전이 느려지며 떨어짐' },
      { joint: 'right_shoulder', weight: 0.2, note: '주 지지 팔(오른손 상단 그립) 견갑 안정성. 어깨가 으쓱하면 회전축이 흔들려 X자 훅이 풀리기 쉬움' },
      { joint: 'left_hip', weight: 0.15, note: '앞 다리 측 골반 외전. 골반 닫히면 앞 무릎이 폴에서 떨어짐' },
      { joint: 'right_hip', weight: 0.1, note: '뒤 다리 측 골반 정렬. X자 형태가 한쪽으로 기울지 않게 받쳐줌' },
      { joint: 'spine_mid', weight: 0.1, note: '측면 자세 유지. 상체 기울면 chair spin처럼 보이며 라인 무너짐' },
    ],
  },
  {
    motionId: 'ref-invert',
    name: '인버트',
    level: 'intermediate',
    entryType: 'lift_entry',
    entryDescription:
      '폴 옆에서 양손 그립을 잡은 뒤 팔을 굽혀(리프트) 몸을 끌어올리며 돌아 진입. 팔 근력으로 가슴을 폴에 붙이며 측면 자세로 올라감.',
    description:
      '양손 그립을 유지한 채 두 단계로 회전. 1단계는 가슴을 폴에 붙이고 머리는 다리 위로 둔 측면 플랭크 라인, 2단계는 머리를 아래로 떨어뜨려 인버트로 전환하며 양 다리를 일자로 찢는 스플릿. 리프트 안정성과 단계 전환의 매끄러움이 채점 핵심.',
    clipRange: {
      prepStartS: 0,
      execStartS: 1,
      execPeakS: 7,
      landEndS: 15,
      recommendedRecordS: 18,
    },
    checkpoints: [
      { joint: 'left_shoulder', weight: 0.2, note: '주 지지 팔(왼손 상단 그립) 견갑 안정성. 리프트 진입과 인버트 전환 모두에서 가장 중요한 지지점' },
      { joint: 'right_shoulder', weight: 0.15, note: '보조 지지 팔. 회전 중 양 어깨 균형 깨지면 회전축이 흔들림' },
      { joint: 'left_hip', weight: 0.2, note: '인버트 스플릿 시 왼다리 측 골반 외전 각도. 골반 닫히면 다리 찢기가 짧아져 스플릿 라인 손상' },
      { joint: 'right_hip', weight: 0.2, note: '인버트 스플릿 시 오른다리 측 골반 외전. 좌우 비대칭이면 다리 찢기가 한쪽으로 기울어 보임' },
      { joint: 'right_knee', weight: 0.1, note: '1단계 신전 다리 + 2단계 스플릿 한쪽 다리. 무릎 굽으면 라인 흐려짐' },
      { joint: 'spine_mid', weight: 0.15, note: '측면 → 인버트 전환 시 몸통 정렬. 허리 꺾이면 단계 연결이 거칠어 보임' },
    ],
  },
  {
    motionId: 'ref-foxtop',
    name: '폭스탑',
    level: 'advanced',
    entryType: 'lift_entry',
    entryDescription:
      '인버트와 동일한 리프트 진입을 사용. 측면 플랭크 → 인버트 다리 찢기까지가 공유 베이스. 이후 다리 교환과 수직 스플릿으로 이어짐.',
    description:
      '앞 6초까지는 인버트와 동일(측면 플랭크 → 인버트 다리 찢기). 이후 다리 교환(왼 무릎 hook ↔ 오른 무릎 hook)과 수직 스플릿으로 이어지며 마지막에 폴 감싸기로 회전 종료. 다리 교환 매끄러움과 수직 스플릿 좌우 대칭이 채점 핵심.',
    sharedBaseMotionId: 'ref-invert',
    baseUntilS: 6,
    clipRange: {
      prepStartS: 0,
      execStartS: 1,
      execPeakS: 18,
      landEndS: 27,
      recommendedRecordS: 30,
    },
    checkpoints: [
      { joint: 'left_shoulder', weight: 0.2, note: '주 지지 팔(왼손 상단 그립) 견갑 안정성. 전 구간 주 지지점. 무너지면 다리 교환·수직 스플릿 모두 진입 불가' },
      { joint: 'right_shoulder', weight: 0.15, note: '보조 지지 팔. 다리 교환 순간 양 어깨 균형 깨지면 회전축 흔들림' },
      { joint: 'left_hip', weight: 0.15, note: '다리 교환 시 왼쪽 무릎 감싸기 측 골반 외전. 수직 스플릿 시 위로 가는 다리(왼쪽)의 신전 시작점' },
      { joint: 'right_hip', weight: 0.15, note: '다리 교환 시 오른쪽 무릎 감싸기 측 골반 외전. 좌우 비대칭이면 수직 스플릿 라인이 한쪽으로 기울어짐' },
      { joint: 'left_knee', weight: 0.1, note: '왼 무릎 감싸기(6~9초) + 수직 스플릿 시 위 다리 무릎 신전' },
      { joint: 'right_knee', weight: 0.1, note: '오른 무릎 감싸기(9~12초) + 수직 스플릿 시 아래 다리 무릎 신전' },
      { joint: 'spine_mid', weight: 0.15, note: '전 구간 인버트 정렬. 다리 교환·수직 스플릿 전환 중 허리 꺾이면 단계 연결이 어색해 보임' },
    ],
  },
  {
    motionId: 'ref-foxtop-split',
    name: '폭스탑스플릿',
    level: 'advanced',
    entryType: 'lift_entry',
    entryDescription:
      '인버트 / 폭스탑과 동일한 리프트 진입. 팔을 굽혀 가슴을 폴에 붙이며 측면 플랭크 라인으로 끌어올림.',
    description:
      '앞 18초까지는 폭스탑과 동일 흐름(측면 플랭크 → 인버트 → 다리 교환 → 스플릿). 이후 자세 전환 후 양팔 펼침 / 수평 라인 자세를 슬로우 로테이션으로 유지하며 마무리. 채점 피크는 11~13초의 양 다리 좌우 펼침(스플릿) 자세.',
    sharedBaseMotionId: 'ref-foxtop',
    baseUntilS: 18,
    clipRange: {
      prepStartS: 0,
      execStartS: 1,
      execPeakS: 12,
      landEndS: 30,
      recommendedRecordS: 35,
    },
    checkpoints: [
      { joint: 'left_shoulder', weight: 0.2, note: '주 지지 팔(왼손 상단 그립). 0~26초 거의 전 구간 주 지지점. 18~26초 추가 자세 + 슬로우 로테이션에서 무너지면 양팔 펼침 라인이 즉시 흐트러짐' },
      { joint: 'right_shoulder', weight: 0.15, note: '보조 지지 팔. 다리 교환 + 추가 자세 + 30초 그립 교체에서 핵심. 슬로우 로테이션 시 균형 깨지면 수평 라인이 한쪽으로 기움' },
      { joint: 'spine_mid', weight: 0.2, note: '인버트 정렬 + 슬로우 로테이션 자세 유지의 핵심. 회전 모멘텀이 줄어드는 22~26초 구간에서 가장 먼저 무너지는 지점' },
      { joint: 'left_hip', weight: 0.15, note: '스플릿 피크(11~13초) 좌우 대칭 + 추가 자세 다리 신전 시작점 (자세별 다리 좌우는 추정)' },
      { joint: 'right_hip', weight: 0.15, note: '스플릿 피크 좌우 대칭. 비대칭이면 채점 피크 라인이 한쪽으로 기울어짐 (좌우 추정)' },
      { joint: 'left_knee', weight: 0.08, note: '다리 hook + 펼침 시 무릎 신전. 굽으면 라인이 흐려져 자세가 흐트러짐' },
      { joint: 'right_knee', weight: 0.07, note: '다리 hook + 펼침 시 무릎 신전. 굽으면 라인이 흐려져 자세가 흐트러짐' },
    ],
  },
];

async function main() {
  initializeApp({ credential: applicationDefault(), projectId: PROJECT_ID });
  const db = getFirestore();

  console.log(`[seed] 프로젝트 ${PROJECT_ID} · reference/ 컬렉션에 ${MOTIONS.length}건 쓰기`);
  const batch = db.batch();
  for (const id of OBSOLETE_MOTION_IDS) {
    batch.delete(db.collection('reference').doc(id));
    console.log(`  - (삭제) ${id}`);
  }
  for (const m of MOTIONS) {
    const ref = db.collection('reference').doc(m.motionId);
    // Firestore Admin SDK 는 undefined 값을 거부 → 콤보 전용 필드는 조건부로만 포함.
    const doc = {
      motionId: m.motionId,
      name: m.name,
      athleteName: ATHLETE,
      level: m.level,
      entryType: m.entryType,
      entryDescription: m.entryDescription,
      description: m.description,
      videoUrl: `${VIDEO_PREFIX}/${m.motionId}.mp4`,
      clipRange: m.clipRange,
      checkpoints: m.checkpoints,
      isActive: true,
      updatedAt: Date.now(),
    };
    if (m.sharedBaseMotionId) {
      doc.sharedBaseMotionId = m.sharedBaseMotionId;
      doc.baseUntilS = m.baseUntilS;
    }
    batch.set(ref, doc, { merge: true });
    const combo = m.sharedBaseMotionId ? ` ← ${m.sharedBaseMotionId} 베이스` : '';
    console.log(`  - ${m.motionId.padEnd(26)} ${m.level.padEnd(12)} ${m.name}${combo}`);
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
