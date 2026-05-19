// 분석 결과 시뮬레이션 (UI 개발용 픽스처). 백엔드 미연결 동안만 사용.
// loading.tsx 의 useSimulatedAnalysis 와 같은 취지 — 계약(docs/contract.md)
// 모양 그대로라 백엔드 연결 시 재작업 없음.
//
// TODO(#7-follow): 이 함수를 Firestore users/{uid}/analyses/{analysisId}
// 문서 onSnapshot 구독으로 교체. 출력 타입(AnalysisResult)은 동일하게 유지.

import type {
  AnalysisMode,
  AnalysisResult,
  JointScore,
} from '../types/analysis';

// ViTPose 17 keypoint 중 평가 관절 (백엔드 skeleton 과 동일 key/라벨)
const JOINTS: JointScore[] = [
  { key: 'left_shoulder', labelKo: '왼쪽 어깨', score: 88 },
  { key: 'right_shoulder', labelKo: '오른쪽 어깨', score: 84 },
  { key: 'left_elbow', labelKo: '왼쪽 팔꿈치', score: 72, issue: '기준 대비 평균 14° 차이' },
  { key: 'right_elbow', labelKo: '오른쪽 팔꿈치', score: 91 },
  { key: 'left_hip', labelKo: '왼쪽 고관절', score: 69, issue: '기준 대비 평균 18° 차이' },
  { key: 'right_hip', labelKo: '오른쪽 고관절', score: 77 },
  { key: 'left_knee', labelKo: '왼쪽 무릎', score: 58, issue: '기준 대비 평균 23° 차이' },
  { key: 'right_knee', labelKo: '오른쪽 무릎', score: 81 },
];

const TIPS = [
  {
    joint: 'left_knee',
    title: '왼쪽 무릎 신전',
    detail:
      '왼쪽 무릎 각도가 기준과 평균 23° 차이가 납니다. 다리를 펴는 구간을 천천히 교정해 보세요.',
  },
  {
    joint: 'left_hip',
    title: '왼쪽 고관절 가동',
    detail:
      '왼쪽 고관절이 충분히 열리지 않았어요. 회전 진입 전 골반을 먼저 여는 느낌으로 연습해 보세요.',
  },
  {
    joint: 'left_elbow',
    title: '왼쪽 팔꿈치 정렬',
    detail:
      '왼쪽 팔꿈치가 기준보다 14° 더 굽었습니다. 그립 직후 팔을 길게 뻗어 보세요.',
  },
];

const PART_SCORES = { 상체: 84, 코어: 73, 하체: 70 } as const;

export function getSimulatedResult(
  mode: AnalysisMode,
  analysisId = 'sim-analysis',
): AnalysisResult {
  const base = {
    overallScore: 76,
    partScores: { ...PART_SCORES },
    joints: JOINTS.map((j) => ({ ...j })),
    tips: TIPS.map((t) => ({ ...t })),
    myVideoUrl: '', // 시뮬레이션 — 실제 서명 URL 없음(화면은 플레이스홀더)
  };

  if (mode === 'mode1') {
    return {
      ...base,
      comparison: {
        mode: 'mode1',
        referenceMotionId: 'ref-inside-leg-hang',
        referenceMotionName: '인사이드 레그 행',
        athleteName: '정은지',
        similarity: 76,
      },
      referenceVideoUrl: '', // 시뮬레이션 — 플레이스홀더
    };
  }

  // mode3 = 자기 성장. 이전 기록이 있다고 가정(델타 표시 확인용).
  return {
    ...base,
    comparison: {
      mode: 'mode3',
      isFirst: false,
      previousAnalysisId: `${analysisId}-prev`,
      deltaFromPrevious: { 상체: 5, 코어: 0, 하체: -3 },
    },
  };
}
