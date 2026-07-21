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
  VisionVeto,
} from '../types/analysis';

// 1..9 원문자 (UI 원문자 텍스트 — 이모지 아님). 초과분은 `(n)` 폴백.
// quick-260705-r6v — ScoreBreakdownSection 이 소유하던 CIRCLED_DIGITS 로직을 여기로
// 승격한다. 점수 계산 내역 행(①②③)·전체화면 여백 범례·시트 헤더가 전부 이 한
// 함수를 import 해 원문자 규칙이 1벌만 존재한다 (중복 2벌 금지).
const CIRCLED_DIGITS_KO = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨'] as const;

export function circledNumberKo(n: number): string {
  return n >= 1 && n <= 9 ? CIRCLED_DIGITS_KO[n - 1] : `(${n})`;
}

// 관절 한국어 라벨 — keypoint 이름(left_hand 등, 확대 비교 자산 표기)과 kismam
// angle key(left_elbow 등, angle_vs_reference__{jk}/windowMedianAngleDeltas.joint)
// 양쪽 키 공간을 한 맵으로 커버 (중복 2벌 금지 — 드릴다운 시트가 import).
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
  // 32-14 (D-22 1단) — keypointReport 12관절 확장분. elbow 는 angle key 로
  // 기존재 → keypoint 키 공간에서도 동일 항목 재사용 (이중 키 공간 커버 관례).
  left_ankle: '왼쪽 발목',
  right_ankle: '오른쪽 발목',
};

// 결함단위(region) 카드 한국어 라벨 (quick-260702-sic) — 좌+우 관절 묶음 카드
// (FaultZoomComparison.region, 스플릿 → 'legs'). 드릴다운 시트/result 가 import —
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

// 29-PLAN-REVIEW HIGH-1 / 29-CONTEXT D-01·D-08 — ipsf_absolute criterion id →
// 결함단위(region) keypoint 매핑. mode3 감점 record 는 관절 필드를 나르지 않고
// criterion id(leg_extension/arm_extension/split_angle/line, ipsf_criteria.
// _MEASURABLE_SEED_IDS)만 가지므로, 마커·행동구·zoom 매칭이 성립하려면 id 를
// 부위로 투영해야 한다. 값은 REGION_MEMBER_KEYPOINTS 재사용(중복 선언 0).
//   leg_extension → legs / arm_extension → arms / split_angle → legs
//   (split 은 양다리 부위 — 기존 vision-split legs 투영과 동일 부위).
//   line → 매핑 없음 (의도된 결정): collective 전신 라인 criterion(joint_keys
//     빈 튜플)이라 특정 관절 마커가 오도하고 zoom region 도 없다 — 29-03 backend
//     무방출 결정과 정합. 테이블 미등록 id 도 자동 [] (fabricate 0).
// **cross-side 계약:** 이 표는 29-03 backend zoom region 파생 표
//   (_build_mode3_fault_zoom_comparisons)와 항목 동일해야 한다 (측당 1벌).
export const CRITERION_REGION_KEYPOINTS: Record<string, readonly KeypointName[]> = {
  leg_extension: REGION_MEMBER_KEYPOINTS.legs,
  arm_extension: REGION_MEMBER_KEYPOINTS.arms,
  split_angle: REGION_MEMBER_KEYPOINTS.legs,
};

// 각도 숫자 없는 짧은 행동구 (quick-260705-o0s) — belle: "각도를 여기서 하기보단
// '다리를 더 모으세요' 등으로만. 각도는 세부 점수에서 어차피 나옴". 재생 중
// 오버레이 라벨은 행동만 전달하고, 각도 수치는 '점수 계산 내역'이 담당한다.
// 방향 의미는 구 composeActionLabelKo(quick-260705-k8y — 본 함수로 대체 후 삭제)
// 를 그대로 계승 (features.py _DIR_MORE_BENT/_EXTENDED + kismam
// JOINT_DIRECTION_PAIRS 미러 — 관절 기하 사전이지 동작명 하드코딩 아님):
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
//   - 관절 투영은 projectDeductionRecordKeypoints 공용 helper 1벌 (규칙 사본 0):
//     angle_vs_reference__{jk} → 단일 keypoint / source='vision' → faultJoints 전체 /
//     ipsf_absolute geometry criterion(mode3 leg/arm/split) → 부위 keypoint /
//     dimension_overall_fallback·score_delta·line → 투영 없음.
//   - 번호는 "새 keypoint 를 최소 1개 확보한 record" 에만 1부터 순차 부여.
//     이미 앞 record 가 번호를 붙인 keypoint 는 첫 번호가 이긴다 (first-wins —
//     점 하나에 숫자 하나). 투영 실패/전부 선점된 record 는 recordNumbers[i]=null
//     (내역 행에 번호 없이 표기 — 정직, fabricate 0).
//   - 같은 record 가 여러 keypoint 로 투영되면(스플릿 → 양쪽 hip 등) 전부 같은
//     번호 (같은 감점의 시각 분산 — 거짓 아님).
//
// quick-260705-r6v → 29-PLAN-REVIEW HIGH-1 — groupMarkers 확장 (additive, 하위호환).
// record 가 2개 이상 keypoint 로 투영되면(스플릿=다리 4관절 / mode3 leg_extension=
// legs 4관절 — "번호 다 1" 근본원인) 멤버 각각에 keypointNumbers 를 찍지 않고 groupMarkers 에
// 1 entry(번호 1개 + 멤버 배열)로 방출한다 → 뷰어가 멤버 centroid 1점만 번호로
// 표시. 멤버는 점유(first-wins)해 뒤 record 가 재번호 못 붙인다. recordNumbers 의
// 번호 부여 순서/규칙은 불변 — 그룹 record 도 번호를 받는다(내역 행 ①과 중점 점
// ①이 일치). 기존 소비처는 groupMarkers 를 무시해도 컴파일된다.
// 29-PLAN-REVIEW HIGH-1 / 29-CONTEXT D-01·D-08 — record → keypoint 투영 규칙의
// 공용 helper 1벌. 종전 두 사본(buildDeductionMarkers 내부 · result.tsx
// recordProjectedKeypoints)의 규칙을 여기로 이관해 "동일 규칙" 페어링을 실현한다
// (규칙 1벌). 전부 저장값 read-only — 재계산/재해석 0.
//
// **평가 순서 고정 (mode1 무회귀):** 기존 3규칙에 전부 비매치인 record 에만
// ipsf_absolute criterion 테이블을 적용 — 분기 순서상 마지막. mode1 의
// vision-sourced split_angle record 는 종전대로 (3) vision 분기에서 faultJoints
// (vision 확정 부분집합)로 투영되고, 테이블의 legs 고정 4관절로 절대 바뀌지 않는다
// (테이블을 vision 앞에 두면 mode1 그룹 마커 멤버·centroid 가 조용히 드리프트 — 금지).
//   (1) dimension_overall_fallback · unit='score_delta' → []
//   (2) angle_vs_reference__{jk} → KEYPOINT_FROM_ANGLE_KEY 단일 keypoint
//   (3) source==='vision' → faultJoints 전체
//   (4) ipsf_absolute geometry criterion → CRITERION_REGION_KEYPOINTS(부위) / line·미등록 → []
export function projectDeductionRecordKeypoints(
  record: DeductionRecord,
  faultJoints: readonly KeypointName[] | undefined,
): KeypointName[] {
  if (
    record.criterion === 'dimension_overall_fallback' ||
    record.unit === 'score_delta'
  ) {
    return [];
  }
  if (record.criterion.startsWith(ANGLE_VS_REFERENCE_PREFIX)) {
    const jk = record.criterion.slice(ANGLE_VS_REFERENCE_PREFIX.length);
    const kp = KEYPOINT_FROM_ANGLE_KEY[jk];
    return kp ? [kp] : [];
  }
  if (record.source === 'vision') return [...(faultJoints ?? [])];
  // 위 3규칙 전부 비매치 — ipsf_absolute geometry criterion(mode3 seed).
  const region = CRITERION_REGION_KEYPOINTS[record.criterion];
  return region ? [...region] : [];
}

export function buildDeductionMarkers(
  records: DeductionRecord[],
  faultJoints: readonly KeypointName[] | undefined,
): {
  recordNumbers: (number | null)[];
  keypointNumbers: Partial<Record<KeypointName, number>>;
  groupMarkers: { number: number; keypoints: KeypointName[] }[];
} {
  const keypointNumbers: Partial<Record<KeypointName, number>> = {};
  const groupMarkers: { number: number; keypoints: KeypointName[] }[] = [];
  const recordNumbers: (number | null)[] = [];
  // 점유 집합 — keypointNumbers 또는 groupMarkers 멤버로 이미 잡힌 keypoint.
  // first-wins 판정을 두 마커 종류에 걸쳐 단일화한다 (점 하나에 숫자 하나).
  const occupied = new Set<KeypointName>();
  let next = 1;
  for (const rec of records) {
    const projected = projectDeductionRecordKeypoints(rec, faultJoints);
    // quick-260705-r6v → 29-PLAN-REVIEW HIGH-1: 2관절 이상 투영 = 그룹(중점) 마커.
    // source==='vision'(스플릿) 한정에서 projected.length>=2 로 일반화 — mode3
    // leg_extension 의 legs 4관절도 개별 4점(전부 같은 번호)이 아닌 centroid 그룹
    // 1점으로 표시된다 (quick-260705-r6v "번호 다 1" 근본원인의 일반화).
    const isGroup = projected.length >= 2;
    const fresh = projected.filter((kp) => !occupied.has(kp));
    if (fresh.length === 0) {
      recordNumbers.push(null);
      continue;
    }
    const num = next;
    next += 1;
    recordNumbers.push(num);
    if (isGroup) {
      // 중점 1점 그룹 마커 — 멤버 각각엔 keypointNumbers 미기록 (개별 번호 없음).
      groupMarkers.push({ number: num, keypoints: fresh });
      for (const kp of fresh) occupied.add(kp);
    } else {
      for (const kp of fresh) {
        keypointNumbers[kp] = num;
        occupied.add(kp);
      }
    }
  }
  return { recordNumbers, keypointNumbers, groupMarkers };
}

// quick-260705-r6v — 재생바 결함 틱 데이터 (해외 사례: Frame.io 챕터 점프 계열).
// 재생 중 영상 위엔 점만 두고, "언제 그 결함이 나왔는지"는 재생바 틱으로 전달한다
// (탭 = 양쪽 영상 동기 seek). 전부 저장값 read-only — 초 환산은 VideoCompare 가
// 수행(frame 도메인만 방출). 29 리뷰 WR-01 — 여기서 방출하는 frameIndex 는
// sourceFrameIndices.user = 9fps angles 배열 공간 인덱스. 초 환산 분모는
// keypointReport.frames(18fps 업샘플)가 아니라 doc top-level anglesFrames(9fps T),
// 기준 duration 은 leftDuration(사용자 영상 도메인)이어야 한다.
//
// 규칙:
//   - visionVeto.status==='applied' 이고 windowMedianAngleDeltas.sourceFrameIndices
//     .user 가 비어있지 않을 때만 틱 방출. 그 외(veto 미적용/legacy/mode3)는 빈
//     배열 — 틱 생략 (fabricate 0).
//   - 현 계약상 window 는 레코드별이 아닌 공유 단일 시점 → user 배열의 median
//     (정렬 후 중앙값, 짝수면 낮은 쪽 = 결정적) 1개 frame 에, 번호가 부여된
//     (recordNumbers[i]!=null) record 전부의 번호를 오름차순 병합해 틱 1개로 방출.
//   - 반환 구조를 배열로 잡는 이유: 백엔드가 record별 측정 시점을 내려주게 되면
//     틱을 record별로 분리 확장(같은 시점은 번호 병합)하기 위함.
export function buildDeductionTicks(
  records: DeductionRecord[],
  recordNumbers: (number | null)[],
  visionVeto: VisionVeto | null | undefined,
): { numbers: number[]; frameIndex: number }[] {
  if (!visionVeto || visionVeto.status !== 'applied') return [];
  const user = visionVeto.windowMedianAngleDeltas?.sourceFrameIndices?.user ?? [];
  const frames = user.filter((f) => Number.isFinite(f));
  if (frames.length === 0) return [];
  // median (정렬 후 중앙값, 짝수면 낮은 쪽 index → 결정적).
  const sorted = [...frames].sort((a, b) => a - b);
  const mid = Math.floor((sorted.length - 1) / 2);
  const frameIndex = sorted[mid];
  // 번호가 부여된 record 전부의 번호를 오름차순 병합.
  const numbers = recordNumbers
    .filter((n): n is number => n != null)
    .sort((a, b) => a - b);
  if (numbers.length === 0) return [];
  return [{ numbers, frameIndex }];
}

// quick-260705-r6v — 참고 지표 진단 문장 (belle 승인 카피 그대로, 임의 수정 금지).
// belle: "각도 유사도 99 인데 47점" 모순 해소 — 숫자 카드 대신 감점 유무 × 지표값
// 구간 조건부 문장. "유사도 <90 이면 위 문장이 거짓" → 값 구간 분기 필수.
// 순수 함수 (저장된 dimension 점수 read-only). value 비유한이면 null (행 생략).
export const DIMENSION_DIAGNOSIS_HIGH_THRESHOLD = 90;

export function composeDimensionDiagnosisKo(
  dim: 'angle' | 'stability',
  cleanPass: boolean,
  value: number,
): string | null {
  if (!Number.isFinite(value)) return null;
  const high = value >= DIMENSION_DIAGNOSIS_HIGH_THRESHOLD;
  if (dim === 'angle') {
    if (!high) {
      // 낮은 값에 "기준대로 타고 있어요" 거짓 문장 차단.
      return '동작 흐름 자체가 기준과 차이가 있어요. 전체 동작을 기준 영상과 비교하며 따라가 보세요.';
    }
    if (!cleanPass) {
      return '동작 전체 흐름은 기준대로 타고 있어요 — 감점은 특정 순간의 자세에서 나왔어요. 위 항목만 교정하면 됩니다.';
    }
    return '동작 흐름과 순간 자세 모두 기준과 일치해요.';
  }
  // stability (안정성)
  if (!high) {
    return '버티는 구간에서 흔들림이 있어요. 자세 교정과 함께 버티는 힘을 길러 보세요.';
  }
  if (!cleanPass) {
    // 틀린 자세로 안정 = 자산 재프레임 (belle 승인).
    return '떨림 없이 버티는 힘은 좋아요 — 자세를 교정하면 그대로 안정된 자세로 정착할 수 있어요.';
  }
  return '버티는 구간도 흔들림 없이 유지했어요.';
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
