// 분석 결과 시뮬레이션 (UI 개발/시연용 픽스처). 실 분석 doc 가 없을 때만 폴백.
// 계약(types/analysis.ts AnalysisResult) 모양 그대로라 백엔드 연결 시 재작업 없음.
//
// 점수 차원 = IPSF 실행 기준 (각도/라인/안정성). mode1 = 3차원, mode3 = 절대
// 차원(라인/안정성) — 자기 성장은 기준 없는 절대 지표로 발전을 비교.

import type {
  AnalysisMode,
  AnalysisResult,
  DimensionExplanation,
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

// Phase 12.5 T9: detail2 (자세히 모달 시뮬). 실 backend = Cerebras LLM 동적 생성.
// 시뮬은 시연용 정적 카피 — UI 렌더링 동작 검증.
const TIPS = [
  {
    joint: 'left_knee',
    title: '왼쪽 무릎 신전',
    detail:
      '회전 진입 직전 왼쪽 무릎을 더 펴서 반동을 만들어 주세요. 다리가 충분히 펴져야 다음 회전으로 이어지는 추진력이 생깁니다.',
    detail2: {
      causes: [
        {
          title: '받침 다리 힘이 부족할 때',
          explanation:
            '받침 다리 (디딤발) 의 대퇴 힘이 부족하면 회전 진입에서 무릎이 자연스럽게 굽혀집니다. 안정적인 자세보다는 빠르게 다음 동작으로 넘어가려는 보상 동작입니다.',
          fix: '월 시트 (Wall Sit) 또는 스플릿 스쿼트로 받침 다리 힘 보강 후 다시 시도해 보세요.',
        },
        {
          title: '회전 타이밍이 빠를 때',
          explanation:
            '회전 시작 타이밍이 빠르면 다리가 완전히 펴지기 전에 다음 동작이 시작돼서 무릎이 굽은 채 진입합니다.',
          fix: '"1·2·셋" 카운트로 디딤발 펴는 단계를 따로 두고 연습해 보세요.',
        },
        {
          title: '햄스트링 유연성이 부족할 때',
          explanation:
            '뒤허벅지가 짧으면 다리를 끝까지 펴기 어렵습니다. 신전 부족이 통증이 아닌 유연성 한계인 경우입니다.',
          fix: '폼롤러 햄스트링 풀기 + 후방 사슬 스트레칭 5분 워밍업을 매 연습 전에 해보세요.',
        },
      ],
      coachNote:
        '정확한 원인은 영상에서 디딤발과 골반 움직임을 함께 봐야 보입니다. 강사와 함께 확인해 보세요.',
    },
  },
  {
    joint: 'left_hip',
    title: '왼쪽 고관절 가동',
    detail:
      '왼쪽 고관절이 덜 열렸어요. 회전 전에 골반을 먼저 여는 느낌으로 시작하면 다음 동작 전환이 자연스러워집니다.',
    detail2: {
      causes: [
        {
          title: '고관절 가동 범위가 부족할 때',
          explanation:
            '고관절 외회전이 좁으면 골반이 충분히 열리지 못해서 다리 각도가 작게 나옵니다. 유연성 한계입니다.',
          fix: '나비 자세 + 90/90 스트레칭으로 외회전 가동 범위 늘리기를 매일 5분씩 해보세요.',
        },
        {
          title: '코어 안정성이 부족할 때',
          explanation:
            '코어가 약하면 골반을 분리해서 움직이기 어렵습니다. 다리를 열기보다 몸통이 같이 돌아가는 보상 동작입니다.',
          fix: '데드 버그 (Dead Bug) 와 버드 독 (Bird Dog) 으로 코어 안정성을 먼저 잡아 보세요.',
        },
        {
          title: '동작 인지가 부족할 때',
          explanation:
            '"골반을 먼저 연다" 감각이 익숙하지 않으면 무릎부터 먼저 들리는 경우가 많습니다.',
          fix: '바닥에서 골반만 들어 회전 시작을 따로 연습한 다음 폴에 적용해 보세요.',
        },
      ],
      injuryRisk:
        '고관절을 강제로 열면 서혜부에 무리가 갈 수 있습니다. 통증이 있으면 즉시 멈추고 강사에게 알려 주세요.',
      coachNote:
        '유연성과 코어 중 어느 쪽이 우선인지 강사와 함께 확인해 보세요.',
    },
  },
  {
    joint: 'left_elbow',
    title: '왼쪽 팔꿈치 정렬',
    detail:
      '그립 직후 왼쪽 팔꿈치가 더 굽었습니다. 팔을 길게 뻗어 상체 라인을 잡으면 회전축이 안정됩니다.',
    detail2: {
      causes: [
        {
          title: '그립 힘이 부족할 때',
          explanation:
            '그립 힘이 부족하면 팔꿈치가 굽혀서 폴을 끌어당기는 보상 동작이 나옵니다.',
          fix: '데드 행 (Dead Hang) 30초 × 3세트로 그립 지구력을 보강하세요.',
        },
        {
          title: '상체 라인 인지가 부족할 때',
          explanation:
            '팔을 길게 뻗는다는 감각이 약하면 자연스럽게 팔꿈치를 굽혀 안정감을 만듭니다.',
          fix: '거울 앞에서 팔만 뻗는 자세를 10초 holding 으로 연습해 보세요.',
        },
        {
          title: '광배근 활성화가 부족할 때',
          explanation:
            '광배근이 활성화되지 않으면 어깨가 솟아오르고 팔꿈치가 굽혀집니다.',
          fix: '시저 행 (Scissor Hang) 또는 패시브 행으로 광배근 인지를 먼저 깨우세요.',
        },
      ],
      coachNote:
        '팔꿈치 정렬은 영상에서 어깨·골반과 함께 봐야 정확합니다. 강사와 함께 확인해 보세요.',
    },
  },
];

// mode1(정은지 비교)은 각도 정확도가 기준이라 후하지 않게. mode3 는 절대 3차원만.
type Dims = Partial<Record<ScoreDimension, number>>;
const DIMS_MODE1: Dims = { angle: 66, line: 74, stability: 64 };
const DIMS_MODE3: Dims = { line: 84, stability: 66 };
const OVERALL_MODE1 = 68;
const OVERALL_MODE3 = 75;

// ── Phase 12.5: dimensionExplanation 시뮬 ─────────────────────────────────
// backend 의 assemble.build_dimension_explanation 출력 모양 그대로. baseline 카피
// 와 deficitSummary 카피는 backend 와 동일 — 실 분석 doc 진입 전 UI 검토용.

// Phase 12.5 v2 (belle 피드백): baseline 카피 = 자세히 모달용 (사용자가 "자세히 ›"
// 누르면 표시). 차원 카드 본문에는 노출 X — 차원 카드는 sublabel (DIMENSION_SUBLABEL_KO)
// 사용. baseline 은 추가 정보 layer.
const SIM_BASELINE_MODE1: Record<ScoreDimension, string> = {
  angle: '정은지 선수 자세 기준 + IPSF 실행 기준 참고',
  line: '정은지 선수 자세 기준 + 팔/다리 펴기 완성도',
  stability: 'hold 구간 떨림 (절대 지표)',
};
const SIM_BASELINE_MODE3: Record<ScoreDimension, string> = {
  angle: '이전 영상 대비 관절 각도 일관성',
  line: '팔/다리 펴기 완성도 (실행 기준 참고)',
  stability: 'hold 구간 떨림 (절대 지표)',
};

// 양호 시 "심사평" — 평가 + 이유 + 결정 3박자 (belle 톤, 점수 ≥ 80)
const SIM_GOOD_BY_DIM: Record<ScoreDimension, string> = {
  angle:
    '관절 각도가 기준에 안정적으로 맞아 있고, 동작 전반에서 일관된 자세를 ' +
    '유지하셨습니다. 자세 일치도에서 좋은 평가를 드렸습니다.',
  line:
    '팔과 다리를 펴야 하는 구간에서 180° 기준에 거의 도달하여 동작의 ' +
    '라인을 잘 만들어 주셨습니다. 펴기 완성도에서 안정적인 점수를 드렸습니다.',
  stability:
    '핵심 자세 구간에서 흔들림 없이 자세를 유지하셨고, 마무리까지 ' +
    '안정성이 이어졌습니다. 동작 안정성에서 좋은 평가를 드렸습니다.',
};

// 점수 < 80 시 "심사평" — 평가 + 이유 + 결정 3박자 (belle 톤)
// 코칭 팁과 분리: 여기는 "심사평/진단" (사실), 코칭 팁은 "행동/처방" (지시).
const SIM_DEFICIT_BY_DIM: Record<ScoreDimension, string> = {
  angle:
    '오른쪽 어깨 각도가 기준에서 22° 벗어났고, 핵심 자세 구간에서도 같은 ' +
    '차이가 이어져 자세 일치도가 부족했습니다. 이 차이가 누적되어 높은 ' +
    '점수를 드리기 어려웠습니다.',
  line:
    '왼쪽 무릎이 끝까지 펴지지 않았고, 핵심 자세 구간에서도 같은 부족함이 ' +
    '이어져 다리 라인이 완성되지 않았습니다. 펴기 기준에서 높은 점수를 ' +
    '드리기 어려웠습니다.',
  stability:
    '오른쪽 무릎이 핵심 자세 구간에서 미세하게 흔들렸고, 그 흔들림이 자세 ' +
    '마무리까지 이어져 안정성에 영향을 주었습니다. 이로 인해 동작 안정성 ' +
    '점수가 낮아졌습니다.',
};

// 모든 차원이 점수 ≥ 80 박제 박제 시 = 양호 카피만 (수치 X).
const GOOD_SCORE_THRESHOLD = 80;

function buildExplanationForSim(
  dims: Dims,
  mode: AnalysisMode,
): Partial<Record<ScoreDimension, DimensionExplanation>> {
  const keys = (Object.keys(dims) as ScoreDimension[]).filter(
    (k) => dims[k] != null,
  );
  const n = keys.length;
  if (n === 0) return {};
  // Phase 19 D-01 — stability 는 종합 비기여 (backend overall_from_dimensions = min-of-core).
  // weightPercent largest-remainder 는 기여 차원(angle/line)에만 분배 (합 100), stability=0.
  const contributing = keys.filter((k) => k === 'angle' || k === 'line');
  const c = contributing.length;
  // Largest Remainder Method — 기여 차원 한정 (backend build_dimension_explanation 와 동일 산식).
  const base = c > 0 ? Math.floor(100 / c) : 0;
  const remainder = c > 0 ? 100 - base * c : 0;
  const pctByDim: Partial<Record<ScoreDimension, number>> = {};
  contributing.forEach((key, i) => {
    pctByDim[key] = i < remainder ? base + 1 : base;
  });
  const baselines = mode === 'mode1' ? SIM_BASELINE_MODE1 : SIM_BASELINE_MODE3;
  const out: Partial<Record<ScoreDimension, DimensionExplanation>> = {};
  keys.forEach((key) => {
    const score = dims[key] ?? 0;
    const good = score >= GOOD_SCORE_THRESHOLD;
    const contributes = key === 'angle' || key === 'line';
    out[key] = {
      weightPercent: pctByDim[key] ?? 0,
      baseline: baselines[key],
      deficitSummary: good ? SIM_GOOD_BY_DIM[key] : SIM_DEFICIT_BY_DIM[key],
      contributesToOverall: contributes,
    };
  });
  return out;
}

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
      // Phase 12.5: 차원별 baseline + weightPercent + deficit (시뮬용).
      dimensionExplanation: buildExplanationForSim(DIMS_MODE1, 'mode1'),
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
    dimensionExplanation: buildExplanationForSim(DIMS_MODE3, 'mode3'),
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
      // Phase 12.5: 시나리오 점수 기반 explanation (각 차원 동등 비중).
      dimensionExplanation: buildExplanationForSim(scenario.dims, 'mode1'),
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
    dimensionExplanation: buildExplanationForSim(scenario.dims, 'mode3'),
    joints,
    tips,
    myVideoUrl: '',
    comparison,
  };
}
