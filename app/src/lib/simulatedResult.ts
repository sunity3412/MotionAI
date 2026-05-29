// 분석 결과 시뮬레이션 (UI 개발/시연용 픽스처). 실 분석 doc 가 없을 때만 폴백.
// 계약(types/analysis.ts AnalysisResult) 모양 그대로라 백엔드 연결 시 재작업 없음.
//
// 점수 차원 = IPSF 실행 기준 (각도/라인/안정성). mode1 = 3차원, mode3 = 절대
// 차원(라인/안정성) — 자기 성장은 기준 없는 절대 지표로 발전을 비교.

import type {
  AnalysisMode,
  AnalysisResult,
  JointScore,
  ScoreDimension,
  SegmentScores,
} from '../types/analysis';

// ViTPose 평가 관절 (백엔드 skeleton 과 동일 key/라벨). 구조화 가이드 필드는
// 백엔드 NLF 실측이 채움 — 여기 값은 폴스포츠 동작에서 그럴듯한 시연용.
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

const TIPS = [
  {
    joint: 'left_knee',
    title: '왼쪽 무릎 신전',
    detail:
      '회전 진입 직전 왼쪽 무릎을 더 펴서 반동을 만들어 주세요. 다리가 충분히 펴져야 다음 회전으로 이어지는 추진력이 생깁니다.',
  },
  {
    joint: 'left_hip',
    title: '왼쪽 고관절 가동',
    detail:
      '왼쪽 고관절이 덜 열렸어요. 회전 전에 골반을 먼저 여는 느낌으로 시작하면 다음 동작 전환이 자연스러워집니다.',
  },
  {
    joint: 'left_elbow',
    title: '왼쪽 팔꿈치 정렬',
    detail:
      '그립 직후 왼쪽 팔꿈치가 더 굽었습니다. 팔을 길게 뻗어 상체 라인을 잡으면 회전축이 안정됩니다.',
  },
];

// mode1(정은지 비교)은 각도 정확도가 기준이라 후하지 않게. mode3 는 절대 3차원만.
type Dims = Partial<Record<ScoreDimension, number>>;
const DIMS_MODE1: Dims = { angle: 66, line: 74, stability: 64 };
const DIMS_MODE3: Dims = { line: 84, stability: 66 };
const OVERALL_MODE1 = 68;
const OVERALL_MODE3 = 75;

// 구간별 점수 시뮬 (reference-motions.md §7).
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
      overallScore: OVERALL_MODE1,
      dimensionScores: { ...DIMS_MODE1 },
      joints: JOINTS.map((j) => ({ ...j })),
      tips: TIPS.map((t) => ({ ...t })),
      myVideoUrl: '',
      comparison: {
        mode: 'mode1',
        referenceMotionId: 'ref-foxtop',
        referenceMotionName: '폭스탑',
        athleteName: '정은지',
        similarity: DIMS_MODE1.angle ?? OVERALL_MODE1, // 게이지 일치도 = 각도 정확도
      },
      referenceVideoUrl: '',
    };
  }

  // mode3 = 자기 성장. 이전 기록이 있다고 가정(발전 델타 표시 확인용).
  return {
    overallScore: OVERALL_MODE3,
    dimensionScores: { ...DIMS_MODE3 },
    joints: JOINTS.map((j) => ({ ...j })),
    tips: TIPS.map((t) => ({ ...t })),
    myVideoUrl: '',
    comparison: {
      mode: 'mode3',
      isFirst: false,
      previousAnalysisId: `${analysisId}-prev`,
      deltaFromPrevious: { line: 5, stability: -3 },
    },
  };
}

// ── 샘플 시연 시나리오 ──────────────────────────────────────────────────
// 영상 없이도 결과 화면을 다양한 점수대/모드로 보여주기 위한 픽스처.
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
  dims: Dims; // mode1=3차원, mode3=절대 차원(line/stability)
  // mode1
  referenceMotionId?: string;
  referenceMotionName?: string;
  // mode3
  isFirst?: boolean;
  deltaFromPrevious?: Dims; // 절대 차원 발전 델타
}

export const SAMPLE_SCENARIOS: readonly SampleScenario[] = [
  {
    id: 'mode1-climb-good',
    label: '정은지 · 클라임 · 우수',
    description: '입문 동작을 잘 따라한 학생 케이스 (82점)',
    mode: 'mode1',
    overall: 81,
    dims: { angle: 80, line: 86, stability: 78 },
    referenceMotionId: 'ref-climb',
    referenceMotionName: '클라임',
  },
  {
    id: 'mode1-sideway-mid',
    label: '정은지 · 사이드웨이 스핀 · 보통',
    description: '회전 진입은 되지만 가동 범위 부족 (65점)',
    mode: 'mode1',
    overall: 63,
    dims: { angle: 60, line: 68, stability: 62 },
    referenceMotionId: 'ref-sideway-spin',
    referenceMotionName: '사이드웨이 스핀',
  },
  {
    id: 'mode1-foxtop-low',
    label: '정은지 · 폭스탑(콤보) · 부족',
    description: '베이스(인버트)는 가능, 폭스탑 확장 구간에서 막힘 (48점)',
    mode: 'mode1',
    overall: 47,
    dims: { angle: 44, line: 52, stability: 46 },
    referenceMotionId: 'ref-foxtop',
    referenceMotionName: '폭스탑',
  },
  {
    id: 'mode3-first',
    label: '내 기록 · 첫 분석',
    description: '비교할 이전 기록이 없는 상태 (발전 델타 없음)',
    mode: 'mode3',
    overall: 75,
    dims: { line: 84, stability: 66 },
    isFirst: true,
  },
  {
    id: 'mode3-growth',
    label: '내 기록 · 발전 추세',
    description: '이전 분석 대비 전 차원이 올라간 케이스 (+5/+2/+3)',
    mode: 'mode3',
    overall: 79,
    dims: { line: 88, stability: 69 },
    isFirst: false,
    deltaFromPrevious: { line: 5, stability: 3 },
  },
  {
    id: 'mode3-plateau',
    label: '내 기록 · 정체기',
    description: '이전 대비 일부 차원이 떨어진 케이스 (-2/0/-3)',
    mode: 'mode3',
    overall: 71,
    dims: { line: 82, stability: 60 },
    isFirst: false,
    deltaFromPrevious: { line: -2, stability: -3 },
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
      dimensionScores: { ...scenario.dims },
      joints,
      tips,
      myVideoUrl: '',
      comparison: {
        mode: 'mode1',
        referenceMotionId: scenario.referenceMotionId ?? 'ref-foxtop',
        referenceMotionName: scenario.referenceMotionName ?? '폭스탑',
        athleteName: '정은지',
        similarity: scenario.dims.angle ?? scenario.overall,
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
          line: 0,
          stability: 0,
        },
      };
  return {
    overallScore: scenario.overall,
    dimensionScores: { ...scenario.dims },
    joints,
    tips,
    myVideoUrl: '',
    comparison,
  };
}
