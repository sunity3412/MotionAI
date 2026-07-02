// 점수 계산 내역 라벨/포맷터 (quick-260702-q8q) — 감점 record 표시의 단일 출처.
//
// 채점 원칙 ([[scoring-must-be-transparent-deduction-tally]]): 점수 = 100 − Σ(측정편차
// × 명시규칙 감점)이고 보고서가 "−X −Y −Z = 점수" 내역을 노출한다. 본 모듈은 저장된
// record 값을 **그대로** 표기만 한다 — 앱에서 점수/판정 재계산·재해석 금지 (객관성).
//
// criterion id 는 contract.md §10.2 카탈로그 + angle_vs_reference__{joint}
// (quick-260626-jwu 신설, 관절별 reference_relative) generic 파싱. 미등록 id 는 id
// 그대로 노출 (숨기지 않음 — 투명성).

import type { DeductionRecord } from '../types/analysis';

// 관절 한국어 라벨 — keypoint 이름(left_hand 등, FaultZoomCompare 표기)과 kismam
// angle key(left_elbow 등, angle_vs_reference__{jk}/windowMedianAngleDeltas.joint)
// 양쪽 키 공간을 한 맵으로 커버 (중복 2벌 금지 — FaultZoomCompare 가 import).
export const JOINT_LABEL_KO: Record<string, string> = {
  left_shoulder: '왼쪽 어깨',
  right_shoulder: '오른쪽 어깨',
  left_hip: '왼쪽 엉덩이',
  right_hip: '오른쪽 엉덩이',
  left_knee: '왼쪽 무릎',
  right_knee: '오른쪽 무릎',
  left_hand: '왼쪽 팔',
  right_hand: '오른쪽 팔',
  left_elbow: '왼쪽 팔꿈치',
  right_elbow: '오른쪽 팔꿈치',
};

// 결함단위(region) 카드 한국어 라벨 (quick-260702-sic) — 좌+우 관절 묶음 카드
// (FaultZoomComparison.region, 스플릿 → 'legs'). FaultZoomCompare 가 import —
// JOINT_LABEL_KO 와 같은 단일 출처 파일 (중복 2벌 금지).
export const REGION_LABEL_KO: Record<string, string> = {
  legs: '양다리',
  arms: '양팔',
};

// IPSF 각도 허용오차 20° 는 KeypointOverlay.KEYPOINT_DELTA_HIGHLIGHT_DEG 가 단일
// 선언 (dimensions.py _LINE_TOL_DEG 정합) — 여기 중복 선언 금지, 소비처가 import.

// criterion id → 한국어 라벨 (contract.md §10.2 카탈로그 고정분).
const CRITERION_LABEL_KO: Record<string, string> = {
  split_angle: '다리 스플릿 각도',
  leg_extension: '다리 신전(펴짐)',
  arm_extension: '팔 신전(펴짐)',
  line: '바디 라인',
  body_relative_reach: '리치(도달 거리)',
  dimension_overall_fallback: '측정 기하 종합(정량화 불가 폴백)',
};

const ANGLE_VS_REFERENCE_PREFIX = 'angle_vs_reference__';

// criterion id → 한국어 라벨. angle_vs_reference__{jk} 는 generic 파싱 (A 작업으로
// 관절별 record 증가 — 개별 등록 없이 자동 라벨). 미등록 id 는 그대로 노출.
export function criterionLabelKo(criterion: string): string {
  const fixed = CRITERION_LABEL_KO[criterion];
  if (fixed) return fixed;
  if (criterion.startsWith(ANGLE_VS_REFERENCE_PREFIX)) {
    const jointKey = criterion.slice(ANGLE_VS_REFERENCE_PREFIX.length);
    const jointLabel = JOINT_LABEL_KO[jointKey];
    if (jointLabel) return `${jointLabel}(정은지 대비 각도)`;
  }
  return criterion;
}

// 숫자 표기 — 저장값 그대로 (재계산 금지). 정수면 정수, 아니면 소수 1자리.
export function formatDeductionNumber(n: number): string {
  if (!Number.isFinite(n)) return String(n);
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

export interface DeductionRowFormat {
  label: string;
  pointsText: string; // 예: '−12' (감점, U+2212)
  detailText: string;
}

// record → 행 표시 포맷. detailText 는 deviationSource/unit 별 실측 근거 문구.
//
// tolerance 는 record 에 직접 없음 — 역산 (플랜 planner_findings 8):
//   reference_relative: raw 편차 = measuredValue(baselineValue=0) → tol = measured − deviation.
//   ipsf_absolute:      raw 편차 = baselineValue − measuredValue → tol = raw − deviation.
// 단 split 160° 0-fail 불연속 record 는 역산이 성립하지 않음(over 가 cap 도출값) —
// 역산 tol 이 음수/비유한이면 허용오차 구문을 생략한다.
export function formatDeductionRecord(record: DeductionRecord): DeductionRowFormat {
  const label = criterionLabelKo(record.criterion);
  const fmt = formatDeductionNumber;
  const pointsText = `−${fmt(Math.abs(record.points))}`;

  let detailText: string;
  if (record.unit === 'score_delta') {
    // dimension_overall fallback — 측정 기하 종합 점수 기준 환산.
    detailText = `측정 기하 종합 ${fmt(record.measuredValue)}점 기준 환산`;
  } else if (record.unit === 'notch') {
    detailText = `도달 부족 ${fmt(record.deviation)}칸`;
  } else if (record.deviationSource === 'reference_relative') {
    const tol = record.measuredValue - record.deviation;
    detailText =
      Number.isFinite(tol) && tol >= 0
        ? `기준 대비 ${fmt(record.measuredValue)}° 차이 (허용 ${fmt(tol)}° 초과 ${fmt(record.deviation)}°)`
        : `기준 대비 ${fmt(record.measuredValue)}° 차이`;
  } else if (record.deviationSource === 'ipsf_absolute') {
    detailText = `측정 ${fmt(record.measuredValue)}° (기준 ${fmt(record.baselineValue)}°, 허용 초과 ${fmt(record.deviation)}°)`;
  } else {
    // 미등록 조합 — 저장값 그대로 정직 노출 (숨기지 않음).
    detailText = `측정 ${fmt(record.measuredValue)} (편차 ${fmt(record.deviation)})`;
  }

  // vision-측정 provenance 투명 노출 (contract.md §10.2 source='vision').
  if (record.source === 'vision') {
    detailText = `${detailText} (영상 비교 측정)`;
  }

  return { label, pointsText, detailText };
}
