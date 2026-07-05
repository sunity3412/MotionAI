// 점수 계산 내역 라벨/포맷터 (quick-260702-q8q) — 감점 record 표시의 단일 출처.
//
// 채점 원칙 ([[scoring-must-be-transparent-deduction-tally]]): 점수 = 100 − Σ(측정편차
// × 명시규칙 감점)이고 보고서가 "−X −Y −Z = 점수" 내역을 노출한다. 본 모듈은 저장된
// record 값을 **그대로** 표기만 한다 — 앱에서 점수/판정 재계산·재해석 금지 (객관성).
//
// criterion id 는 contract.md §10.2 카탈로그 + angle_vs_reference__{joint}
// (quick-260626-jwu 신설, 관절별 reference_relative) generic 파싱. 미등록 id 는 id
// 그대로 노출 (숨기지 않음 — 투명성).

import type { DeductionRecord, KeypointName } from '../types/analysis';

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

// kismam 관절각의 의미 한 단어 설명 (quick-260704-fz4, CONTEXT locked — 8관절
// 고정 사전으로 충분). belle: "168.9° 가 무슨 각인지 이해 불가" 해소. 기하 근거
// (backend skeleton.JOINT_ANGLES — vertex 에서 (a-vertex)·(c-vertex) 사이 각):
//   elbow    = 어깨-팔꿈치-손목  → 팔꿈치 굽힘
//   shoulder = 팔꿈치-어깨-엉덩이 → 겨드랑이 벌림 (팔-몸통 사이 각)
//   hip      = 어깨-엉덩이-무릎  → 다리 벌림 (몸통-허벅지 사이 각, 스플릿 개방)
//   knee     = 엉덩이-무릎-발목  → 무릎 굽힘
export const ANGLE_MEANING_KO: Record<string, string> = {
  left_elbow: '팔꿈치 굽힘',
  right_elbow: '팔꿈치 굽힘',
  left_shoulder: '겨드랑이 벌림',
  right_shoulder: '겨드랑이 벌림',
  left_hip: '다리 벌림',
  right_hip: '다리 벌림',
  left_knee: '무릎 굽힘',
  right_knee: '무릎 굽힘',
};

// angle key(kismam) → keypoint 이름 역매핑 (quick-260704-fz4) — 단일 출처.
// backend pipeline _KISMAM_TO_KEYPOINT / KeypointOverlay JOINT_KEY_TO_ANGLE_KEY
// 의 역방향 정합: elbow 각은 손(left_hand=COCO wrist)이 시각 proxy, 나머지 1:1.
export const KEYPOINT_FROM_ANGLE_KEY: Record<string, KeypointName> = {
  left_elbow: 'left_hand',
  right_elbow: 'right_hand',
  left_shoulder: 'left_shoulder',
  right_shoulder: 'right_shoulder',
  left_hip: 'left_hip',
  right_hip: 'right_hip',
  left_knee: 'left_knee',
  right_knee: 'right_knee',
};

// 결함단위(region) 카드의 멤버 keypoint (quick-260704-fz4) — backend
// fault_zoom._REGION_JOINTS 의 8-keypoint(KeypointName) 부분집합 미러
// (legs: hips+knees / arms: shoulders+hands). 편차행 ↔ region 카드 매칭용.
export const REGION_MEMBER_KEYPOINTS: Record<
  'legs' | 'arms',
  readonly KeypointName[]
> = {
  legs: ['left_hip', 'right_hip', 'left_knee', 'right_knee'],
  arms: ['left_shoulder', 'right_shoulder', 'left_hand', 'right_hand'],
};

// 행동 지시 라벨 조립 (quick-260705-k8y) — belle: "절대각 숫자(158°)는 수강생이
// 못 알아듣는다". 오버레이 문제 관절에 "왼쪽 무릎 23° 더 펴야" 형태(편차+방향)만
// 표시. 순수 함수 — 입력은 backend signed delta 그대로 (UI 재계산 금지), 문구
// 사전은 여기 한 곳에 격리 (후속 리서치로 문구만 교체 가능하게).
//
// 방향 의미 근거 (backend features.py _DIR_MORE_BENT/_EXTENDED + kismam
// JOINT_DIRECTION_PAIRS 미러 — 관절 기하 사전이지 동작명 하드코딩 아님):
//   signed delta = student − reference.
//   delta < 0 = 기준보다 각이 작음(더 굽음/닫힘) → 펴야/벌려야
//   delta > 0 = 기준보다 각이 큼(더 펴짐/열림)   → 굽혀야/모아야
//   kismam 페어: elbow/knee=(extend,flex), hip=(open,close), shoulder=(raise,lower)
export function composeActionLabelKo(
  angleKey: string,
  signedDeltaDeg: number,
): string | null {
  if (!Number.isFinite(signedDeltaDeg)) return null;
  const n = Math.round(Math.abs(signedDeltaDeg));
  // 라운딩 후 1° 미만 = 실질 편차 없음 → 라벨 생략 (마커만).
  if (n < 1) return null;
  const part = JOINT_LABEL_KO[angleKey];
  if (!part) return null;
  // delta === 0 인데 n >= 1 은 라운딩상 불가 — 방어적으로 delta <= 0 을 "굽음"
  // 쪽으로 폴백 처리 (방향 미상 시 별도 composeDeviationOnlyLabelKo 사용).
  const moreBent = signedDeltaDeg <= 0;
  switch (angleKey) {
    // 굽힘 관절 (팔꿈치 굽힘/무릎 굽힘) — 각 작음 = 더 굽음 → 펴야.
    case 'left_elbow':
    case 'right_elbow':
    case 'left_knee':
    case 'right_knee':
      return moreBent ? `${part} ${n}° 더 펴야` : `${part} ${n}° 더 굽혀야`;
    // 다리 벌림 (몸통-허벅지 개방각, ANGLE_MEANING_KO 정합) — 좌우 구분은 마커
    // 위치가 전달하므로 부위어는 '다리' (belle 예시 "다리 더 올려야" 와 동의,
    // 사전 단어 '벌림' 과 정합 우선).
    case 'left_hip':
    case 'right_hip':
      return moreBent ? `다리 ${n}° 더 벌려야` : `다리 ${n}° 더 모아야`;
    // 겨드랑이 벌림 (팔-몸통 사이 각) — 각 작음 = 팔이 몸에 붙음 → 벌려야.
    case 'left_shoulder':
    case 'right_shoulder':
      return moreBent ? `팔 ${n}° 더 벌려야` : `팔 ${n}° 더 모아야`;
    default:
      return null;
  }
}

// 방향 생략 폴백 (quick-260705-k8y) — faultJointDeficits 는 Gemini 시각 추정
// 편차 "크기"만 있고 부호가 없다. 방향을 지어내지 않는다 (거짓 구체성 금지,
// quick-260704-fwb) — 편차 크기만 정직하게 표기.
export function composeDeviationOnlyLabelKo(
  angleKey: string,
  deviationDeg: number,
): string | null {
  if (!Number.isFinite(deviationDeg)) return null;
  const n = Math.round(Math.abs(deviationDeg));
  if (n < 1) return null;
  const part = JOINT_LABEL_KO[angleKey];
  if (!part) return null;
  return `${part} 기준과 ${n}° 차이`;
}

// criterion id → 한국어 라벨 (contract.md §10.2 카탈로그 고정분).
const CRITERION_LABEL_KO: Record<string, string> = {
  split_angle: '다리 스플릿 각도',
  leg_extension: '다리 신전(펴짐)',
  arm_extension: '팔 신전(펴짐)',
  line: '바디 라인',
  body_relative_reach: '리치(도달 거리)',
  dimension_overall_fallback: '측정 기하 종합(정량화 불가 폴백)',
};

// export (quick-260704-fz4) — result.tsx confirmedKeypoints 조립이 감점 record
// criterion 에서 관절을 파싱할 때 재사용 (prefix 문자열 중복 2벌 금지).
export const ANGLE_VS_REFERENCE_PREFIX = 'angle_vs_reference__';

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
