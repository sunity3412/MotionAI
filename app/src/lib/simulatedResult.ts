// 분석 결과 시뮬레이션 (UI 개발용 픽스처). 백엔드 미연결 동안만 사용.
// loading.tsx 의 useSimulatedAnalysis 와 같은 취지 — 계약(docs/contract.md)
// 모양 그대로라 백엔드 연결 시 재작업 없음.
//
// TODO(#7-follow): 이 함수를 Firestore users/{uid}/analyses/{analysisId}
// 문서 onSnapshot 구독으로 교체. 출력 타입(AnalysisResult)은 동일하게 유지.

import type {
  AnalysisMode,
  AnalysisResult,
  BodyPart,
  JointScore,
  SegmentScores,
} from '../types/analysis';

// ViTPose 17 keypoint 중 평가 관절 (백엔드 skeleton 과 동일 key/라벨).
// 구조화 가이드 필드(currentAngle/targetAngle/deltaDeg/direction)는
// #7-follow 에서 ML 이 실측값으로 채움 — 여기 값은 폴스포츠 동작에서 그럴듯한 시연용.
//   - 무릎/팔꿈치: 180° 가 완전 신전. 사용자 각도 < 기준 → 'extend'(더 펴기)
//   - 고관절    : 큰 각도 = 더 열림. 사용자 < 기준 → 'open'(더 열기)
//   - 어깨      : 큰 각도 = 더 들림. 사용자 < 기준 → 'raise'(더 올리기)
const JOINTS: JointScore[] = [
  { key: 'left_shoulder', labelKo: '왼쪽 어깨', score: 88 },
  { key: 'right_shoulder', labelKo: '오른쪽 어깨', score: 84 },
  {
    key: 'left_elbow',
    labelKo: '왼쪽 팔꿈치',
    score: 72,
    currentAngle: 138,
    targetAngle: 152,
    deltaDeg: -14,
    direction: 'extend',
    issue: '기준 대비 평균 14° 차이',
  },
  { key: 'right_elbow', labelKo: '오른쪽 팔꿈치', score: 91 },
  {
    key: 'left_hip',
    labelKo: '왼쪽 고관절',
    score: 69,
    currentAngle: 78,
    targetAngle: 96,
    deltaDeg: -18,
    direction: 'open',
    issue: '기준 대비 평균 18° 차이',
  },
  { key: 'right_hip', labelKo: '오른쪽 고관절', score: 77 },
  {
    key: 'left_knee',
    labelKo: '왼쪽 무릎',
    score: 58,
    currentAngle: 145,
    targetAngle: 168,
    deltaDeg: -23,
    direction: 'extend',
    issue: '기준 대비 평균 23° 차이',
  },
  { key: 'right_knee', labelKo: '오른쪽 무릎', score: 81 },
];

// detail 은 #7-follow 에서 Cerebras 가 실제 키프레임·각속도까지 반영해 생성.
// 지금은 시연용으로 회전력/반동 같은 동적 큐도 한 줄씩 자연어로 섞어둠.
const TIPS = [
  {
    joint: 'left_knee',
    title: '왼쪽 무릎 신전',
    detail:
      '회전 진입 직전 왼쪽 무릎을 23° 더 펴서 반동을 만들어 주세요. 다리가 충분히 펴져야 다음 회전으로 이어지는 추진력이 생깁니다.',
  },
  {
    joint: 'left_hip',
    title: '왼쪽 고관절 가동',
    detail:
      '왼쪽 고관절이 18° 덜 열렸어요. 회전 전에 골반을 먼저 여는 느낌으로 시작하면 다음 동작 전환이 자연스러워집니다.',
  },
  {
    joint: 'left_elbow',
    title: '왼쪽 팔꿈치 정렬',
    detail:
      '그립 직후 왼쪽 팔꿈치가 14° 더 굽었습니다. 팔을 길게 뻗어 상체 라인을 잡으면 회전축이 안정됩니다.',
  },
];

// mode1(전문가 비교)은 정은지 선수가 기준이라 자기 비교(mode3)보다 박하게 평가됨.
// mode3 는 자기 성장 추적이라 절대치는 후한 편 — 두 모드 결과를 동시 시연했을
// 때 자연스럽도록 의도적으로 차이를 둠.
const SCORES_MODE1 = {
  overall: 71,
  parts: { 상체: 78, 코어: 65, 하체: 62 },
} as const;
const SCORES_MODE3 = {
  overall: 76,
  parts: { 상체: 84, 코어: 73, 하체: 70 },
} as const;

// 구간별 점수 시뮬 (reference-motions.md §7). 베이스 구간은 익숙해서 높고,
// 확장(고유) 구간은 어려워서 낮게 — 학생이 어디서 막혔는지 자연스럽게 드러남.
// #7-follow 에서 백엔드 segments.segment_scores 실측치로 교체.
export function simulatedSegmentScores(
  overallScore: number,
  baseMotionId: string,
  baseMotionName: string,
): SegmentScores {
  const clamp = (n: number) => Math.max(0, Math.min(100, n));
  return {
    base: clamp(overallScore + 8),
    extension: clamp(overallScore - 13),
    baseMotionId,
    baseMotionName,
  };
}

export function getSimulatedResult(
  mode: AnalysisMode,
  analysisId = 'sim-analysis',
): AnalysisResult {
  if (mode === 'mode1') {
    return {
      overallScore: SCORES_MODE1.overall,
      partScores: { ...SCORES_MODE1.parts },
      joints: JOINTS.map((j) => ({ ...j })),
      tips: TIPS.map((t) => ({ ...t })),
      myVideoUrl: '',
      comparison: {
        mode: 'mode1',
        referenceMotionId: 'ref-foxtop',
        referenceMotionName: '폭스탑',
        athleteName: '정은지',
        similarity: SCORES_MODE1.overall, // 게이지 점수 = 일치도
        // segmentScores 는 simulationWriter 가 고른 기술의 베이스 공유 여부를 보고 채움.
      },
      referenceVideoUrl: '',
    };
  }

  // mode3 = 자기 성장. 이전 기록이 있다고 가정(델타 표시 확인용).
  return {
    overallScore: SCORES_MODE3.overall,
    partScores: { ...SCORES_MODE3.parts },
    joints: JOINTS.map((j) => ({ ...j })),
    tips: TIPS.map((t) => ({ ...t })),
    myVideoUrl: '',
    comparison: {
      mode: 'mode3',
      isFirst: false,
      previousAnalysisId: `${analysisId}-prev`,
      deltaFromPrevious: { 상체: 5, 코어: 0, 하체: -3 },
    },
  };
}

// ── 샘플 시연 시나리오 ──────────────────────────────────────────────────
// 영상 없이도 결과 화면을 다양한 점수대/모드로 보여주기 위한 픽스처.
// 실 분석 파이프라인이 켜지면(#7-follow) 이 모듈 전체 폐기 대상이지만 그 전까지
// belle/직원 시연 검토 + 화면 회귀 점검용. JOINTS/TIPS 는 재사용하고 overall
// 변화량만큼 관절 점수도 함께 이동시켜 표시 정합성 유지.
export type SampleScenarioId =
  | 'mode1-climb-good'
  | 'mode1-sideway-mid'
  | 'mode1-foxtop-low'
  | 'mode3-first'
  | 'mode3-growth'
  | 'mode3-plateau';

export interface SampleScenario {
  id: SampleScenarioId;
  label: string; // 카드 상단 라벨
  description: string; // 카드 본문 한 줄
  mode: AnalysisMode;
  overall: number;
  parts: { 상체: number; 코어: number; 하체: number };
  // mode1
  referenceMotionId?: string;
  referenceMotionName?: string;
  // mode3
  isFirst?: boolean;
  deltaFromPrevious?: Record<BodyPart, number>;
}

export const SAMPLE_SCENARIOS: readonly SampleScenario[] = [
  {
    id: 'mode1-climb-good',
    label: '정은지 · 클라임 · 우수',
    description: '입문 동작을 잘 따라한 학생 케이스 (82점)',
    mode: 'mode1',
    overall: 82,
    parts: { 상체: 86, 코어: 80, 하체: 79 },
    referenceMotionId: 'ref-climb',
    referenceMotionName: '클라임',
  },
  {
    id: 'mode1-sideway-mid',
    label: '정은지 · 사이드웨이 스핀 · 보통',
    description: '회전 진입은 되지만 가동 범위 부족 (65점)',
    mode: 'mode1',
    overall: 65,
    parts: { 상체: 72, 코어: 60, 하체: 63 },
    referenceMotionId: 'ref-sideway-spin',
    referenceMotionName: '사이드웨이 스핀',
  },
  {
    id: 'mode1-foxtop-low',
    label: '정은지 · 폭스탑(콤보) · 부족',
    description: '베이스(인버트)는 가능, 폭스탑 확장 구간에서 막힘 (48점)',
    mode: 'mode1',
    overall: 48,
    parts: { 상체: 55, 코어: 45, 하체: 44 },
    referenceMotionId: 'ref-foxtop',
    referenceMotionName: '폭스탑',
  },
  {
    id: 'mode3-first',
    label: '내 기록 · 첫 분석',
    description: '비교할 이전 기록이 없는 상태 (델타 없음)',
    mode: 'mode3',
    overall: 76,
    parts: { 상체: 84, 코어: 73, 하체: 70 },
    isFirst: true,
  },
  {
    id: 'mode3-growth',
    label: '내 기록 · 성장 추세',
    description: '이전 분석 대비 전 파트가 올라간 케이스 (+5/+2/+3)',
    mode: 'mode3',
    overall: 78,
    parts: { 상체: 86, 코어: 75, 하체: 73 },
    isFirst: false,
    deltaFromPrevious: { 상체: 5, 코어: 2, 하체: 3 },
  },
  {
    id: 'mode3-plateau',
    label: '내 기록 · 정체기',
    description: '이전 대비 일부 파트가 떨어진 케이스 (-2/0/-3)',
    mode: 'mode3',
    overall: 73,
    parts: { 상체: 82, 코어: 71, 하체: 67 },
    isFirst: false,
    deltaFromPrevious: { 상체: -2, 코어: 0, 하체: -3 },
  },
];

// JOINTS 의 score 평균은 78. 시나리오 overall 과의 차이만큼 일괄 이동시켜
// 결과 화면 전체 점수와 관절별 점수가 어울리게 한다 (시연 정합성).
function shiftJoints(shift: number): JointScore[] {
  const clamp = (n: number) => Math.max(0, Math.min(100, Math.round(n)));
  return JOINTS.map((j) => ({ ...j, score: clamp(j.score + shift) }));
}

const JOINTS_BASE_AVG = 78;

export function getSimulatedResultFromScenario(
  scenario: SampleScenario,
  analysisId: string,
): AnalysisResult {
  const shift = scenario.overall - JOINTS_BASE_AVG;
  const joints = shiftJoints(shift);
  const tips = TIPS.map((t) => ({ ...t }));

  if (scenario.mode === 'mode1') {
    return {
      overallScore: scenario.overall,
      partScores: { ...scenario.parts },
      joints,
      tips,
      myVideoUrl: '',
      comparison: {
        mode: 'mode1',
        referenceMotionId: scenario.referenceMotionId ?? 'ref-foxtop',
        referenceMotionName: scenario.referenceMotionName ?? '폭스탑',
        athleteName: '정은지',
        similarity: scenario.overall,
        // segmentScores 는 simulationWriter 가 reference doc 의 sharedBaseMotionId 보고 채움.
      },
      referenceVideoUrl: '',
    };
  }

  // mode3
  const comparison: AnalysisResult['comparison'] = scenario.isFirst
    ? { mode: 'mode3', isFirst: true }
    : {
        mode: 'mode3',
        isFirst: false,
        previousAnalysisId: `${analysisId}-prev`,
        deltaFromPrevious: scenario.deltaFromPrevious ?? {
          상체: 0,
          코어: 0,
          하체: 0,
        },
      };
  return {
    overallScore: scenario.overall,
    partScores: { ...scenario.parts },
    joints,
    tips,
    myVideoUrl: '',
    comparison,
  };
}
