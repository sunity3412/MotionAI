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
//   - 정은지 선수 실영상 5개 분석 결과 (사이드웨이/클라임/인버트/폭스탑/폭스탑 스플릿).
//   - motionId 는 안정적 슬러그 = doc ID = S3 키. idempotent: 재실행해도 같은 doc 갱신.
//   - clipRange/checkpoints 는 분석 런타임 입력. keyframe 각도(angles)는 #7-follow ML 단.
//   - 구간 공유 트리: ref-invert → ref-foxtop → ref-foxtop-split (베이스 공유).
//   - ⚠ checkpoint 가중치·peak·자유 다리 좌우 등은 추정 — MVP 시연 후 정은지 선수와 일괄 수정.

import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { applicationDefault, initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';

// 선택 인자 --angles <path>: backend/scripts/extract_reference_angles.py 가 만든
// JSON. 있으면 angles + anglesUpdatedAt + jointKeys 필드를 doc 에 함께 쓴다.
// 없으면 angles 는 건드리지 않음(기존 값 유지) — presigned URL 만 갱신하는 주간
// 재시드 시 안전. backend/functions/pipeline/app.py 가 ref["angles"] 를 읽는다.
//
// 선택 인자 --keypoint-reports <path>: Phase 12 Wave 0B (Plan 12-01, R3 iter-2).
// 정은지 영상을 production analysis 1 회 돌린 결과의 result.keypointReport 를
// motionId 별로 모은 JSON. 있으면 referenceKeypointReport 필드를 doc 에 함께
// 쓴다. 없으면 건드리지 않음 (구 doc fallback — useReferenceMotion null-guard).
function parseArgs(argv) {
  const out = { anglesPath: null, keypointReportsPath: null };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--angles' && i + 1 < argv.length) {
      out.anglesPath = argv[i + 1];
      i++;
    } else if (argv[i] === '--keypoint-reports' && i + 1 < argv.length) {
      out.keypointReportsPath = argv[i + 1];
      i++;
    }
  }
  return out;
}

function loadAnglesPayload(path) {
  const raw = readFileSync(path, 'utf8');
  const data = JSON.parse(raw);
  if (!data.motions || !Array.isArray(data.jointKeys)) {
    throw new Error(`잘못된 angles JSON 형식: ${path}`);
  }
  return data;
}

// Phase 12 Wave 0B (Plan 12-01, R3 iter-2) — keypoint_reports payload loader.
// 형식: { "motions": { "ref-sideway-spin": { version, joints, frames, fps,
//   data, confidence, reliability, axisData, axisMask, warnings }, ... } }
// 10 필드 모두 박제 강제 — 누락 시 Firestore validator 가 reject.
function loadKeypointReportsPayload(path) {
  const raw = readFileSync(path, 'utf8');
  const data = JSON.parse(raw);
  if (!data.motions || typeof data.motions !== 'object') {
    throw new Error(`잘못된 keypoint-reports JSON 형식: ${path}`);
  }
  const required = [
    'version',
    'joints',
    'frames',
    'fps',
    'data',
    'confidence',
    'reliability',
    'axisData',
    'axisMask',
    'warnings',
  ];
  for (const [motionId, report] of Object.entries(data.motions)) {
    if (!report || typeof report !== 'object') {
      throw new Error(`keypoint-reports[${motionId}] 가 object 아님`);
    }
    for (const key of required) {
      if (!(key in report)) {
        throw new Error(
          `keypoint-reports[${motionId}] 누락 필드: ${key} (10 필드 모두 박제 강제)`,
        );
      }
    }
  }
  return data;
}

const PROJECT_ID = 'sunity-ai-coach';
const ATHLETE = '정은지';

// S3 reference 영상을 7일 서명 URL 로 발급해 Firestore videoUrl 에 저장한다.
// 만료(7일) 뒤엔 앱 동작 비교가 멈추므로, 시연 직전 1주일 안에 재시드 필수.
// 서명 발급에 aws CLI 가 ~/.aws/credentials (sunity-api) 를 사용한다.
const S3_BUCKET = 'sunity-motion-pilot-videos';
const S3_PREFIX_KEY = 'reference';
const S3_REGION = 'ap-northeast-2';
const PRESIGN_EXPIRES_SEC = 7 * 24 * 60 * 60; // 7일 = AWS 서명 최대 (sig v4 + IAM 사용자 키)

function presignReferenceUrl(motionId) {
  const s3Uri = `s3://${S3_BUCKET}/${S3_PREFIX_KEY}/${motionId}.mp4`;
  try {
    const url = execFileSync(
      'aws',
      [
        's3',
        'presign',
        s3Uri,
        '--expires-in',
        String(PRESIGN_EXPIRES_SEC),
        '--region',
        S3_REGION,
      ],
      { encoding: 'utf8' },
    ).trim();
    if (!url.startsWith('https://')) {
      throw new Error(`presign 결과가 https URL 이 아님: ${url}`);
    }
    return url;
  } catch (err) {
    const msg = err?.stderr?.toString() || err?.message || String(err);
    throw new Error(`[presign FAIL] ${motionId}: ${msg}`);
  }
}

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
    name: '폭스탑 스플릿',
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
  // ── 정은지 추가 영상 6 motion (2026-06-12 belle 결정, claude.ai + Gemini Vision 매칭) ──
  // 학원 통용명 그대로 사용. IPSF 정식 등재 strict 매칭 X — 분기 2 (정은지 reference 측정값 = 채점 기준).
  // CROSS-CHECK: .planning/research/new-motions-ipsf-matching-2026-06-12/CROSS-CHECK.md
  {
    motionId: 'ref-kip-up',
    name: '킵업',
    level: 'basic',
    entryType: 'swing_entry',
    entryDescription:
      '폴 옆에서 양손 그립 셋업 후 점프 이륙. 다리 사이드 스윕 후방 통과 시 와이드 스트래들로 진입.',
    description:
      '폴에 양손으로 매달려 다리 반동으로 회전을 만드는 동적 entry 스킬. 인버전 (머리 골반 아래) 없이 머리 위·발 아래 자세 유지하며 약 3-3.5회전 (1080-1260°). 콤보 연결기 또는 코어/팔 근력 트레이닝용. IPSF 미등재 dynamic transition.',
    clipRange: {
      prepStartS: 0,
      execStartS: 1,
      execPeakS: 4,
      landEndS: 7.2,
      recommendedRecordS: 10,
    },
    checkpoints: [
      { joint: 'left_shoulder', weight: 0.2, note: '풀업 그립 측 견갑 안정성. 어깨 처지면 다리 스윙 추진력 손실' },
      { joint: 'right_shoulder', weight: 0.2, note: '푸시 그립 측 견갑 안정성. 보조 지지 약하면 회전축 흔들림' },
      { joint: 'left_hip', weight: 0.15, note: '스윙 추진력 핵심. 후방 통과 시 와이드 스트래들 폭 결정' },
      { joint: 'right_hip', weight: 0.15, note: '좌우 대칭 스트래들. 비대칭이면 회전이 한쪽으로 기울어짐' },
      { joint: 'left_knee', weight: 0.1, note: '스윙 시 무릎 신전. 굽으면 추진 모멘트 작아짐' },
      { joint: 'right_knee', weight: 0.1, note: '좌우 무릎 신전 대칭. 짧아지면 다리 라인 흐트러짐' },
      { joint: 'spine_mid', weight: 0.1, note: '상체 후굴 + 다리 모음 사이클. 흉추 안 열리면 회전이 끊김' },
    ],
  },
  {
    motionId: 'ref-peter-pan',
    name: '피터팬',
    level: 'basic',
    entryType: 'swing_entry',
    entryDescription:
      '폴 옆에서 상하 스플릿 그립(위쪽 손 head 위, 아래 손 가슴~골반 높이) 셋업 후 공중에 매달려 셰이프 정리.',
    description:
      '상하 스플릿 그립으로 매달린 채 한 다리 무릎을 폴에 hook, 다른 다리는 뒤로 길게 펴는 스태그(stag) 셰이프. 약 4회전 연속 hold-in-rotation. 하늘을 나는 피터팬 실루엣 닮음. 한국/세계 학원 통용 기초 스핀. IPSF 미등재.',
    clipRange: {
      prepStartS: 0,
      execStartS: 0.7,
      execPeakS: 4,
      landEndS: 7.4,
      recommendedRecordS: 10,
    },
    checkpoints: [
      { joint: 'left_shoulder', weight: 0.2, note: '위쪽 그립 측 견갑. 회전 중 어깨 떨어지면 셰이프 라인 무너짐' },
      { joint: 'right_shoulder', weight: 0.15, note: '아래 보조 그립. 두 손 거리 유지 안 되면 셰이프 불안정' },
      { joint: 'left_hip', weight: 0.2, note: '폴 hook 측 골반 외전. 깊게 접혀야 hook 안정' },
      { joint: 'right_hip', weight: 0.2, note: '뒤로 펴는 자유 다리 측 고관절 신전. 신전 부족하면 피터팬 실루엣 안 나옴' },
      { joint: 'left_knee', weight: 0.1, note: 'hook 측 무릎 굽힘 각도. 너무 펴면 hook 풀림' },
      { joint: 'right_knee', weight: 0.1, note: '자유 다리 무릎 신전. 굽으면 라인 짧아짐' },
      { joint: 'spine_mid', weight: 0.05, note: '척추 정렬. 측면 plank 라인 유지' },
    ],
  },
  {
    motionId: 'ref-power-spin',
    name: '파워스핀',
    level: 'intermediate',
    entryType: 'swing_entry',
    entryDescription:
      '폴 옆에서 양손 스플릿 그립(오른손 위·왼손 아래) 셋업 후 푸시오프로 공중 진입. 다리 턱(tuck)으로 회전력 만들기.',
    description:
      '스플릿 그립으로 양손 매달려 다리를 턱↔extension 으로 반복(펌핑)하며 약 3.5-4회전. 후반(약 6.6s 이후)에 오른다리 폴 따라 수직 위로, 왼다리 아래로 펴는 vertical split 자세로 약 2.5회전 hold. 강한 원심력을 버티는 split 그립 dynamic 회전. IPSF 미등재.',
    clipRange: {
      prepStartS: 0,
      execStartS: 0.5,
      execPeakS: 7,
      landEndS: 9.9,
      recommendedRecordS: 12,
    },
    checkpoints: [
      { joint: 'left_shoulder', weight: 0.2, note: '아래 푸시 그립 측 견갑. 강한 원심력을 버티는 핵심 — 무너지면 split 라인 불안정' },
      { joint: 'right_shoulder', weight: 0.2, note: '위쪽 풀업 그립 측 견갑. 회전축 기준 — 떨어지면 vertical split 한쪽으로 기울어짐' },
      { joint: 'left_hip', weight: 0.15, note: '아래 다리 측 고관절. 펌핑 시 신전→굴곡 부드러움이 회전 모멘텀 결정' },
      { joint: 'right_hip', weight: 0.15, note: '위 다리(폴 따라 수직) 측 고관절. 후반 split 의 vertical alignment' },
      { joint: 'left_knee', weight: 0.1, note: '아래 다리 무릎 신전. 굽으면 split 라인 짧아짐' },
      { joint: 'right_knee', weight: 0.1, note: '위 다리 무릎 신전. 굽으면 수직 라인 무너짐' },
      { joint: 'spine_mid', weight: 0.1, note: '몸통 정렬. 펌핑 ↔ split 전환 사이 흉추 안정성' },
    ],
  },
  {
    motionId: 'ref-elbow-twist-sister',
    name: '엘보 트위스트 시스터',
    level: 'advanced',
    entryType: 'lift_entry',
    entryDescription:
      '공중에서 양손 그립 + 다리 셰이프 변화로 진입. 1.5~5.5s 사이 다리를 폴에 hook 하며 상체 뒤로 젖혀 점진적 도립.',
    description:
      '인버트 + 무릎 hook + 엘보 백 그립 + 윗다리 수직 익스텐션의 결합. 5.5~9.5s 빌드업(프리암 → 엘보 그립 → 다리 익스텐션) 후 9.5~17.5s 메인 hold 약 8초 — 도립 + 백벤드 + 트위스트 + 수직 익스텐션 유지하며 회전 지속. 17.5s 이후 릴리즈→ 직립 복귀. IPSF 미등재 (Inverted Inner Thigh Hook/Scorpio + Elbow back grip + split 결합 변형).',
    clipRange: {
      prepStartS: 0,
      execStartS: 5.5,
      execPeakS: 13,
      landEndS: 21.9,
      recommendedRecordS: 25,
    },
    checkpoints: [
      { joint: 'left_shoulder', weight: 0.15, note: '엘보 백 그립 측 견갑. 등 뒤로 돌린 팔의 안정성 — hold 8초 핵심' },
      { joint: 'right_shoulder', weight: 0.15, note: '폴 그립 측 견갑. 도립+트위스트 유지의 주 지지점' },
      { joint: 'left_hip', weight: 0.15, note: '무릎 hook 측 고관절. 도립 자세 잠금' },
      { joint: 'right_hip', weight: 0.2, note: '윗다리(수직 익스텐션) 측 고관절 신전. Pencil/Vertical 라인 결정' },
      { joint: 'left_knee', weight: 0.1, note: 'hook 무릎 굽힘 깊이. 풀리면 도립 자세 무너짐' },
      { joint: 'right_knee', weight: 0.15, note: '윗다리 무릎 완전 신전. 굽으면 vertical 라인 손상 — 채점 핵심' },
      { joint: 'spine_mid', weight: 0.1, note: '백벤드 곡률. 흉추까지 열려야 트위스트 깊이 살아남' },
    ],
  },
  {
    motionId: 'ref-pdshape',
    name: 'pdshape',
    level: 'advanced',
    entryType: 'lift_entry',
    entryDescription:
      '영상 시작 시점에 이미 인버전 + 회전 상태 (지면→공중 entry 영상 밖). 다리 셰이프 정리(턱 → 신전 → 스트래들 경유)로 hold 진입.',
    description:
      '정식 명칭 없는 연계 동작 — 학원에서 "pdshape" 로 통용. 0~3.5s 인버전 셰이프 정리 후 3.5~11.5s 메인 클로즈드 셰이프 hold 약 8초 — 한 다리 hip-knee hook + 다른 다리 굽힘(folded) + 양손 폴 + 비대칭 inverted hold + 회전 유지. 11.5~13.7s 오픈 레그 라인 변형 (시저→수평 신전). 12회전+ 등속. IPSF 미등재 (Inverted Torso Hook/Butterfly + Scorpio variation 결합).',
    clipRange: {
      prepStartS: 0,
      execStartS: 3.5,
      execPeakS: 8,
      landEndS: 15,
      recommendedRecordS: 18,
    },
    checkpoints: [
      { joint: 'left_shoulder', weight: 0.2, note: '한쪽 폴 그립 측 견갑. 메인 hold 8초 동안 비대칭 체중 받치는 핵심' },
      { joint: 'right_shoulder', weight: 0.15, note: '보조 폴 그립 측 견갑. 비대칭 안정성' },
      { joint: 'left_hip', weight: 0.2, note: 'hook 측 고관절. 한 다리 hook 깊이 — 클로즈드 셰이프 잠금' },
      { joint: 'right_hip', weight: 0.15, note: '굽힌 다리 측 고관절. folded position 의 좌우 균형' },
      { joint: 'left_knee', weight: 0.1, note: 'hook 측 무릎. 풀리면 hold 무너짐' },
      { joint: 'right_knee', weight: 0.1, note: '굽힌 다리 무릎 각도. 너무 펴거나 굽으면 셰이프 흐트러짐' },
      { joint: 'spine_mid', weight: 0.1, note: '척추 비대칭 정렬. 회전 중 라인 변형 (오픈 레그) 시 흉추 안정성' },
    ],
  },
  {
    motionId: 'ref-combo',
    name: '콤보',
    level: 'advanced',
    entryType: 'swing_entry',
    entryDescription:
      '스탠딩 준비(0~1.5s) → 워크어라운드(팔 벌려 진입) → 스핀 콤보 시작. 약 62초 multi-segment 연계.',
    description:
      '여러 IPSF 등재/미등재 기술을 끊김 없이 연결한 콤보. 10 segment 박힘: Spin sequence(1.5~13.5s, 5-6개 다리 셰이프 변경) → Climb(13.5~18.5s) → Inverted entry V/chopper(18.5~20.5s) → Leg Hang hold + 익스텐션(28~37.5s, 33s 아웃사이드 레그 행 명확) → Butterfly 계열(37.5~44s, 익스텐디드 버터플라이) → 인버티드 셰이프 전환(44~53s) → Finale display(53~57.5s) → Dismount(57.5~62s). IPSF Dynamic Combinations 카테고리 + Outside Leg Hang + Butterfly 등 등재 카테고리 mix.',
    clipRange: {
      prepStartS: 0,
      execStartS: 1.5,
      execPeakS: 33,
      landEndS: 57.5,
      recommendedRecordS: 65,
    },
    checkpoints: [
      { joint: 'left_shoulder', weight: 0.15, note: '주 그립 측 견갑. 62초 multi-segment 전체에 걸친 지지점. 클라임~버터플라이 전환 핵심' },
      { joint: 'right_shoulder', weight: 0.15, note: '보조 그립 측 견갑. 다양한 그립 전환(스플릿/엘보/하이 그립) 안정성' },
      { joint: 'left_hip', weight: 0.15, note: '레그 행 + 버터플라이 + 셰이프 전환의 좌측 골반. 다양한 hook 깊이 변동 큰 구간' },
      { joint: 'right_hip', weight: 0.15, note: '우측 골반. 좌우 다리 교대 hook 시 비대칭 변화 큼' },
      { joint: 'left_knee', weight: 0.1, note: '훅/익스텐션 사이 무릎 변화량 큰 segment 마다 신전' },
      { joint: 'right_knee', weight: 0.1, note: '우측 무릎. 다리 교대 시 풀림→hook 부드러움' },
      { joint: 'spine_mid', weight: 0.2, note: '척추 정렬. 직립→인버트→백벤드 등 다양한 정렬 변화 — 콤보 흐름의 핵심 신호' },
    ],
  },
];

async function main() {
  const { anglesPath, keypointReportsPath } = parseArgs(
    process.argv.slice(2),
  );
  const anglesPayload = anglesPath ? loadAnglesPayload(anglesPath) : null;
  const keypointReportsPayload = keypointReportsPath
    ? loadKeypointReportsPayload(keypointReportsPath)
    : null;

  initializeApp({ credential: applicationDefault(), projectId: PROJECT_ID });
  const db = getFirestore();

  const expiresAt = new Date(Date.now() + PRESIGN_EXPIRES_SEC * 1000);
  console.log(`[seed] 프로젝트 ${PROJECT_ID} · reference/ 컬렉션에 ${MOTIONS.length}건 쓰기`);
  console.log(`[presign] S3 서명 만료: ${expiresAt.toISOString()} (7일 뒤 — 시연 임박해 재시드 필요)`);
  if (anglesPayload) {
    const count = Object.keys(anglesPayload.motions).length;
    console.log(
      `[angles] ${anglesPath} 로드 — ${count}건 angles 포함 (${anglesPayload.jointKeys.join(', ')})`,
    );
  } else {
    console.log('[angles] --angles 인자 없음 — angles 필드는 건드리지 않음(기존 값 유지)');
  }
  if (keypointReportsPayload) {
    const count = Object.keys(keypointReportsPayload.motions).length;
    console.log(
      `[keypoint-reports] ${keypointReportsPath} 로드 — ${count}건 referenceKeypointReport 포함 (Phase 12 Wave 0B)`,
    );
  } else {
    console.log(
      '[keypoint-reports] --keypoint-reports 인자 없음 — referenceKeypointReport 필드는 건드리지 않음(기존 값 유지, Wave 0B follow-up)',
    );
  }
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
      videoUrl: presignReferenceUrl(m.motionId), // 7일 서명 URL (HTTPS)
      videoUrlExpiresAt: expiresAt.getTime(), // epoch ms — 앱이 만료 임박 안내에 활용 가능
      videoS3Key: `${S3_PREFIX_KEY}/${m.motionId}.mp4`, // 백엔드 pipeline 이 비교 영상 서명 URL 발급에 사용
      clipRange: m.clipRange,
      checkpoints: m.checkpoints,
      isActive: true,
      updatedAt: Date.now(),
    };
    if (m.sharedBaseMotionId) {
      doc.sharedBaseMotionId = m.sharedBaseMotionId;
      doc.baseUntilS = m.baseUntilS;
    }
    if (anglesPayload && anglesPayload.motions[m.motionId]) {
      const a = anglesPayload.motions[m.motionId];
      // Firestore 는 nested array(배열의 배열)를 허용 안 함 → flat 으로 저장.
      // 백엔드는 anglesJointKeys 길이로 (T, J) 로 reshape.
      doc.angles = a.angles.flat();
      doc.anglesUpdatedAt = Date.now();
      doc.anglesFrames = a.numFrames;
      doc.anglesJointKeys = anglesPayload.jointKeys;
    }
    if (
      keypointReportsPayload
      && keypointReportsPayload.motions[m.motionId]
    ) {
      // Phase 12 Wave 0B (Plan 12-01, R3 iter-2) — referenceKeypointReport 박제.
      // 10 필드 모두 flat (Firestore nested-array 회피). 백엔드 validator 가
      // 동일 schema 강제 (_validate_keypoint_report — keypointReport path 와
      // 동일 strictness, reference 측은 별도 path 라 collection 검증 X).
      doc.referenceKeypointReport
        = keypointReportsPayload.motions[m.motionId];
      doc.referenceKeypointReportUpdatedAt = Date.now();
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
