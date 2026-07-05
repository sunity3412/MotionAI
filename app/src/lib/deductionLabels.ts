// 점수 계산 내역 라벨/포맷터 (quick-260702-q8q) — 감점 record 표시의 단일 출처.
//
// 채점 원칙 ([[scoring-must-be-transparent-deduction-tally]]): 점수 = 100 − Σ(측정편차
// × 명시규칙 감점)이고 보고서가 "−X −Y −Z = 점수" 내역을 노출한다. 본 모듈은 저장된
// record 값을 **그대로** 표기만 한다 — 앱에서 점수/판정 재계산·재해석 금지 (객관성).
//
// criterion id 는 contract.md §10.2 카탈로그 + angle_vs_reference__{joint}
// (quick-260626-jwu 신설, 관절별 reference_relative) generic 파싱. 미등록 id 는 id
// 그대로 노출 (숨기지 않음 — 투명성).

import type {
  DeductionBreakdown,
  DeductionRecord,
  KeypointName,
} from '../types/analysis';

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

// 각도 숫자 없는 짧은 행동구 (quick-260705-o0s) — belle: "각도를 여기서 하기보단
// '다리를 더 모으세요' 등으로만. 각도는 세부 점수에서 어차피 나옴". 재생 중
// 오버레이 라벨은 행동만 전달하고, 각도 수치는 '점수 계산 내역'이 담당한다.
// 방향 의미는 composeActionLabelKo 와 동일 계승 (features.py _DIR_MORE_BENT/
// _EXTENDED + kismam JOINT_DIRECTION_PAIRS 미러 — 관절 기하 사전):
//   signed delta = student − reference. delta < 0 = 더 굽음/닫힘 → 펴기/벌리기.
// 순수 함수 — backend signed delta 그대로 (UI 재계산 금지).
export function composeShortActionLabelKo(
  angleKey: string,
  signedDeltaDeg: number,
): string | null {
  if (!Number.isFinite(signedDeltaDeg)) return null;
  // 라운딩 후 1° 미만 = 실질 편차 없음 → 라벨 생략 (마커만).
  if (Math.round(Math.abs(signedDeltaDeg)) < 1) return null;
  const part = JOINT_LABEL_KO[angleKey];
  if (!part) return null;
  const moreBent = signedDeltaDeg <= 0;
  switch (angleKey) {
    // 굽힘 관절 (팔꿈치/무릎) — 각 작음 = 더 굽음 → 펴기. 명사형 종결.
    case 'left_elbow':
    case 'right_elbow':
    case 'left_knee':
    case 'right_knee':
      return moreBent ? `${part} 더 펴기` : `${part} 더 굽히기`;
    // 다리 벌림 (몸통-허벅지 개방각, ANGLE_MEANING_KO 정합) — 좌우 구분은
    // 마커 위치가 전달하므로 부위어는 '다리' (기존 관례).
    case 'left_hip':
    case 'right_hip':
      return moreBent ? '다리 더 벌리기' : '다리 더 모으기';
    // 겨드랑이 벌림 (팔-몸통 사이 각) — 각 작음 = 팔이 몸에 붙음 → 벌리기.
    case 'left_shoulder':
    case 'right_shoulder':
      return moreBent ? '팔 더 벌리기' : '팔 더 모으기';
    default:
      return null;
  }
}

// 점수 계산 내역 상단 "채점 기준" 1줄 자동 조립 (quick-260705-o0s).
// 하드코딩 조건 분기를 이 순수 helper 한 곳에 격리 — record 의 deviationSource
// 를 1차 신호로 사용 (contract.md §10.2). ipsfAnchor 필드도 record 에 있으나
// 신호 이중화 금지 원칙으로 여기서는 참조하지 않는다 (deviationSource 단독).
// records 빈 배열 / fallback(dimension_overall)만 → null (표기 생략).
export function composeScoringBasisKo(
  records: DeductionRecord[],
): string | null {
  const hasRef = records.some(
    (r) => r.deviationSource === 'reference_relative',
  );
  const hasIpsf = records.some((r) => r.deviationSource === 'ipsf_absolute');
  if (hasRef && hasIpsf) {
    return '세계챔피언 정은지 선수 시연 대비 편차 + IPSF 국제심사 기준으로 감점을 계산했어요.';
  }
  if (hasRef) {
    return '세계챔피언 정은지 선수 시연 대비 편차를 기준으로 감점을 계산했어요.';
  }
  if (hasIpsf) {
    return 'IPSF 국제심사 기준으로 감점을 계산했어요.';
  }
  return null;
}

// 영상 점 ↔ 내역 행 번호 매핑의 단일 출처 (quick-260705-o0s) — quick-260704-fz4
// confirmedKeypoints 와 같은 "표·마커 동일 소스" 패턴. 오버레이 빨간 점 안 숫자와
// 점수 계산 내역 행의 원문자(①②③)가 여기 한 함수 결과에서 나와 항상 일치한다.
//
// 규칙 (전부 저장값 read-only — 재계산/재해석 0):
//   - record 순회는 저장 순서 그대로 (엔진이 결정적 정렬, 재정렬 금지).
//   - 관절 투영: (a) angle_vs_reference__{jk} → KEYPOINT_FROM_ANGLE_KEY 단일
//     keypoint / (b) 관절명 없는 vision record(split_angle 등, source='vision')
//     → faultJoints 전체 (fz4 confirmedKeypoints 와 동일 규칙, CONTEXT locked) /
//     (c) dimension_overall_fallback 또는 unit='score_delta' → 투영 없음.
//   - 번호는 "새 keypoint 를 최소 1개 확보한 record" 에만 1부터 순차 부여.
//     이미 앞 record 가 번호를 붙인 keypoint 는 첫 번호가 이긴다 (first-wins —
//     점 하나에 숫자 하나). 투영 실패/전부 선점된 record 는 recordNumbers[i]=null
//     (내역 행에 번호 없이 표기 — 정직, fabricate 0).
//   - 같은 record 가 여러 keypoint 로 투영되면(스플릿 → 양쪽 hip 등) 전부 같은
//     번호 (같은 감점의 시각 분산 — 거짓 아님).
export function buildDeductionMarkers(
  records: DeductionRecord[],
  faultJoints: readonly KeypointName[] | undefined,
): {
  recordNumbers: (number | null)[];
  keypointNumbers: Partial<Record<KeypointName, number>>;
} {
  const keypointNumbers: Partial<Record<KeypointName, number>> = {};
  const recordNumbers: (number | null)[] = [];
  let next = 1;
  for (const rec of records) {
    let projected: KeypointName[] = [];
    if (
      rec.criterion === 'dimension_overall_fallback' ||
      rec.unit === 'score_delta'
    ) {
      projected = [];
    } else if (rec.criterion.startsWith(ANGLE_VS_REFERENCE_PREFIX)) {
      const jk = rec.criterion.slice(ANGLE_VS_REFERENCE_PREFIX.length);
      const kp = KEYPOINT_FROM_ANGLE_KEY[jk];
      projected = kp ? [kp] : [];
    } else if (rec.source === 'vision') {
      projected = [...(faultJoints ?? [])];
    }
    const fresh = projected.filter((kp) => keypointNumbers[kp] == null);
    if (fresh.length === 0) {
      recordNumbers.push(null);
      continue;
    }
    const num = next;
    next += 1;
    recordNumbers.push(num);
    for (const kp of fresh) keypointNumbers[kp] = num;
  }
  return { recordNumbers, keypointNumbers };
}

// 감점 0 게이트의 단일 신호 (quick-260705-o0s, belle 추가 피드백 #2 — "100점인데
// 보완하라"는 모순 카피/2° 노이즈 카드 해소). 요약 카피·문제-계열 섹션 게이트·
// 축하 섹션이 전부 이 함수 하나를 소비한다 (분기 산개 금지).
//
// 규칙:
//   - breakdown 존재 + records 빈 배열일 때만 true.
//   - breakdown 부재(legacy doc/mode3) → false (게이트 미발동 = 기존 렌더 유지,
//     판단 불가 시 보수적).
//   - dimension_overall_fallback record 도 실감점이므로 records 존재 = clean 아님.
//   - advisory(주황, 감점 아님) 카드는 records 에 없으므로 advisory-only 영상은
//     자동으로 clean — belle 의도(감점 0 이면 2° 노이즈 참고 카드도 숨김)와 정합.
export function isCleanPass(
  breakdown: DeductionBreakdown | null | undefined,
): boolean {
  return breakdown != null && breakdown.records.length === 0;
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
