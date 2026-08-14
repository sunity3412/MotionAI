// 부위 단위 감점 상세 시트 뷰모델 + 블록 카피 조립 (quick-260730-py1 — 33-G S6/S7).
//
// 승인 스펙 원본 = `.planning/phases/33-result-trust-recovery/mockups/index.html`
// (7R, belle 승인 2026-07-29) `DETAILS` + `renderDetail`. 이 파일은 그 구조를
// **데이터로** 재현한다 — 승인본 문구는 상수로 원문 박제하고 자리표시자만 치환한다.
//
// 왜 순수 모듈인가 (resultSections.ts 선례): 시트 조판은 "부위에 감점 2건이면
// 시트 1개·블록 2개" 같은 구조 규칙과 "데이터 없으면 문구를 만들지 않는다"는
// fail-closed 규칙의 합이고, 둘 다 typecheck 로 보증되지 않는다. 컴포넌트는
// 이 결과를 **렌더만** 한다 (조판 분기 사본 0).
//
// 불변식:
//   - 저장값 read-only. 점수/판정 재계산·재해석 0 (deductionLabels 헤더 계승).
//   - 동작명 분기 0. 키잉은 record.criterion / record.source / record.deviationSource /
//     projectDeductionRecordKeypoints / zoom.tier 만 — 모션 id 리터럴 금지 (D-41).
//   - 초는 **백엔드 방출값**(`FaultZoomComparison.userVideoSec/refVideoSec`)만.
//     프레임 인덱스를 fps 로 나눠 초를 추정하는 것이 F-3 의 근본원인이었다.
//   - fail-closed: basis·method·facing·oneCap·paircap 은 데이터가 성립할 때만 방출.
//     거짓 근거는 신뢰 붕괴(belle 확인 ② 반려)이므로 **공백이 정답**이다.
//   - HTML 금지 (T-33G2-01): RN 은 마크업을 해석하지 않아 `<b>` 가 화면에 그대로
//     노출된다. 강조는 `{ text, bold }` 세그먼트로 방출하고 렌더가 중첩 Text 로 그린다.
//
// 미구현(의도된 공백):
//   - proof 증거 3컷 (M-10) — 백엔드는 카드당 합성 PNG 1장만 방출한다. "좋았던/감점/
//     마무리" 분류는 측정 판단이고 doc 에 없다. 앱이 각도 시계열을 뒤져 정하면 판정
//     재해석이므로 **자리도 두지 않는다**. 백엔드 3컷 방출은 §C-4 이관.
//   - basis 의 구간 축("실제 재생 6.3~8.2초 구간") — 계약상 측정창은 record별이 아니라
//     공유 단일 창이고(visionVeto.windowMedianAngleDeltas), 창 인덱스→초 변환 fps 가
//     앱에 없다. record별 measureWindow*Sec 방출을 조건으로 §C-4 이관.

import {
  ANGLE_MEANING_KO,
  ANGLE_VS_REFERENCE_PREFIX,
  BODY_PART_LABEL_KO,
  BODY_PART_OF_KEYPOINT,
  criterionLabelKo,
  formatDeductionNumber,
  formatDeductionRecord,
  projectDeductionRecordKeypoints,
} from './deductionLabels.ts';
import type {
  DeductionRecord,
  FaultZoomComparison,
  KeypointName,
} from '../types/analysis';

// ── 승인 확정 문구 (원문 유지 대상 — 임의 수정 금지) ─────────────────────────
// 출처 = 승인 목업 `DETAILS`(1002-1085) + `renderDetail`(1086-1117).

/** 블록 번호 헤더 (4R#2). 번호 절은 그룹에 감점 2건 이상일 때만. */
const BLOCK_HEAD_PREFIX = '고칠 것';
/** paircap 좌측 고정 라벨 (6R). 우측은 caller 가 비교 대상 라벨을 준다. */
const PAIR_CAP_SELF_LABEL = '내 자세';
/** basis 문두 (5R#2) — 굵게. */
const BASIS_LABEL = '어디서 재나요:';
/** numnote 문두 (2R 수치 강등). */
const NUM_NOTE_PREFIX = '측정 수치(참고) — ';
/** facing 문두 (7R). */
const FACING_PREFIX = '두 사진이 달라 보이는 이유 — ';
/** method(vision) 정직 라벨 (5R#3) — 프레임 측정이 아니라는 고백. */
const METHOD_VISION =
  '측정 방법 — 이 항목은 특정 순간을 잰 프레임 측정이 아니라, 두 영상 전체를 견준 AI 시각 판단이에요.';
/** method(정렬) 첫 문장 (5R#3). 두 번째 문장은 기준 초가 있을 때만 붙는다. */
const METHOD_ALIGNED =
  '측정 방법 — 이 항목은 한 순간이 아니라 두 영상의 전 구간을 정렬해 견준 값이에요.';
/**
 * 참고(advisory) 긴 안내 문형 — 승인 목업 legend "점선 = 참고 — 점수 감점은 되지
 * 않지만 회전·힘 같은 전체 동작에 영향을 줄 수 있는 부위예요" 계열. 기하 무단정이라
 * 승인 원문 그대로.
 *
 * 33-G S2 (quick-260730-szk) — **전 표면 단일 소스로 승격**(값 변경 0). advisory
 * 시트 onecap · 부위 칩 인라인 안내가 같은 이 상수를 소비한다 (T-33G3-02 —
 * 사본이 생기면 표면마다 문형이 갈라지고 그것이 3R#3 반려의 실체였다).
 */
export const ADVISORY_NOTE_KO =
  '참고 부위예요 — 점수 감점은 되지 않지만 회전·힘 같은 전체 동작에 영향을 줄 수 있어요. 눈에 띈 차이만 보여드려요';

/**
 * 참고(advisory) 짧은 칩형 — 승인 목업 `:1091` + 마커 title `:336` 과 문자 동일.
 * 33-G S2 — `DeductionDetailSheet` 의 local 사본을 지우고 이 상수를 import 한다.
 */
export const ADVISORY_CHIP_KO = '참고 — 감점은 아니지만 회전·힘에 영향';
/**
 * IN-01 (quick-260724-q6b) — 역립 저신뢰 시 관절별 감점 수치를 특정 관절에
 * 귀속할 수 없어 거짓 정밀도 대신 노출하는 안내. 종전 시트 근거 박스가 소유했던
 * 카피를 numnote 자리로 이관 (수치의 승인 거처 = 블록 맨 뒤 작은 회색 줄).
 */
const ESTIMATED_AREA_POINTS_NOTE =
  '이 부위는 추정이라 관절별 감점 수치는 종합 점수로만 반영돼요';

/** criterion 단독 그룹 키 접두 (부위 투영이 공집합인 criterion). */
const CRITERION_GROUP_PREFIX = 'criterion:';

/**
 * 부위 토큰 정렬 순서 (머리→발). 한 record 가 두 부위에 걸치면(mode3
 * `arm_extension` = 어깨+손) 이 순서로 결합해 결정적 그룹 키를 만든다.
 */
const PART_ORDER: readonly string[] = ['shoulder', 'arm', 'leg'];

/**
 * criterion → "무엇을 재는가" 사람 말. angle 계열은 ANGLE_MEANING_KO 가 소유하고
 * (겨드랑이 벌림·무릎 굽힘…), 여기엔 각도 사전이 커버하지 못하는 항목만 둔다.
 */
const MEASURED_SUBJECT_KO: Record<string, string> = {
  split_angle: '두 다리를 벌린 정도',
};

/**
 * 사람 말로 "무엇을 재는지" 말할 수 없는 criterion — basis/oneCap 생략 대상.
 * 라벨이 채점 내부 표현이라 화면 문장에 넣으면 뜻이 전달되지 않는다.
 */
const SUBJECT_UNSPEAKABLE: readonly string[] = ['dimension_overall_fallback'];

// ── 공개 타입 ─────────────────────────────────────────────────────────────

/** 강조 구간 세그먼트 — 렌더가 중첩 `<Text>` 로 그린다 (HTML 금지, T-33G2-01). */
export interface TextSegment {
  text: string;
  bold?: boolean;
}

export interface RegionSheetBlock {
  /** 원 records 배열 인덱스 (recordId 조인·번호 대조용). */
  recordIndex: number;
  /** `고칠 것 2 — 다리 펴기 (−20점)` — 번호 절은 그룹 2건 이상일 때만. */
  header: string;
  statusLine: string | null;
  whyLine: string | null;
  /** `어디서 재나요:` 굵게 + 본문 세그먼트. 데이터 미충족 시 null. */
  basisLine: TextSegment[] | null;
  cueLine: string | null;
  methodLine: string | null;
  numNote: string | null;
  /**
   * 이 블록 안에 렌더할 크롭의 record 인덱스. primary 블록(시트 상단 크롭)과
   * 같은 카드면 null — 중복 렌더 금지. 기존에 보이던 증거를 잃지 않기 위한 자리.
   */
  blockRecordIndexForCrop: number | null;
}

export interface RegionSheetView {
  /** 부위 그룹 키 (`leg` / `shoulder` / `shoulder+arm` / `criterion:{id}`). */
  partKey: string;
  /** 화면 제목용 부위 라벨 (`다리` / `어깨` / criterion 라벨). */
  title: string;
  /** 시트 상단 크롭을 낳은 record 인덱스 (블록 순서의 첫 항목). */
  primaryRecordIndex: number;
  /**
   * 그 record 의 criterion id. 시트 하단 심사 언어 용어줄(terminologyMap)이
   * criterion 키로 매핑되므로 뷰모델이 원 키를 함께 나른다 — 렌더가 라벨
   * 문자열에서 criterion 을 역파싱하면 라벨 규칙 사본이 생긴다.
   */
  primaryCriterion: string;
  /**
   * 이 항목이 **무엇을 하려는 동작인지** 한 문장 (quick-260802-mrg). 묶인 항목의
   * head 에서 한 번만 말한다 — 같은 목표 문장을 블록마다 N번 반복하지 않는 것이
   * "한 항목처럼 한 문장으로 설명"의 실체다. 저장된 cueLine 의 목표 절을 그대로
   * 옮긴 것이고 창작 0 — 목표 절이 없으면 `null`(자리도 두지 않는다).
   */
  goalLine: string | null;
  blocks: RegionSheetBlock[];
  pairCapLeft: string | null;
  pairCapRight: string | null;
  oneCap: string | null;
  facingLine: string | null;
  /** 상단 크롭이 참고(감점 아님) 카드인가 — chip/onecap 톤 결정. */
  isAdvisoryOnly: boolean;
}

export interface RegionSheetInput {
  records: readonly DeductionRecord[];
  /** 전역 마커 번호 (`buildDeductionMarkers().recordNumbers`) — 번호 단일 출처. */
  recordNumbers: readonly (number | null)[];
  /** 범례와 동일 소스의 행동구 (record.cueLine 부재 시 폴백). */
  actionPhrases: readonly (string | null)[];
  /** records[i] 에 매칭된 확대 카드 (조인은 caller 의 matchZoomForDeductionRecord). */
  zooms: readonly (FaultZoomComparison | null)[];
  selectedRecordIndex: number | null;
  /** paircap 우측 라벨 — mode1 `기준 (정은지)` / mode3 `지난 영상`. */
  rightPairLabel: string;
  /** IN-01 역립 저신뢰 — 번호·관절별 수치 억제. */
  estimatedArea?: boolean;
  /** vision faultJoints — 부위 투영 입력 (projectDeductionRecordKeypoints). */
  faultJoints?: readonly KeypointName[];
}

// ── 순수 helper ───────────────────────────────────────────────────────────

/**
 * 목적격 조사(을/를) 선택. 받침 유무로 갈리므로("힘"→을, "크기"→를) 고정 조사는
 * 오표기를 낸다. 마지막 글자의 한글 종성 유무로 판정, 비한글은 '를' 폴백.
 * (구 DeductionDetailSheet.objectJosa 를 여기로 승격 — 사본 2벌 금지.)
 */
export function objectJosaKo(text: string): string {
  if (text.length === 0) return '를';
  const last = text.charCodeAt(text.length - 1);
  if (last >= 0xac00 && last <= 0xd7a3) {
    return (last - 0xac00) % 28 > 0 ? '을' : '를';
  }
  return '를';
}

/**
 * 실영상 초 라벨 — `실 1.7초`. 소수 1자리는 백엔드 `_timestamp_label`(`f"{s:.1f}s"`)과
 * 같은 자릿수라 PNG 베이크 표기와 불일치가 0이다. 비유한/음수 → null (라벨 생략).
 */
export function formatVideoSecKo(
  sec: number | null | undefined,
): string | null {
  if (typeof sec !== 'number' || !Number.isFinite(sec) || sec < 0) return null;
  return `실 ${sec.toFixed(1)}초`;
}

function videoSecOf(sec: number | null | undefined): number | null {
  if (typeof sec !== 'number' || !Number.isFinite(sec) || sec < 0) return null;
  return sec;
}

/**
 * 부위 그룹 키 (M-3). 투영 keypoint 를 부위 토큰 집합으로 접고, 공집합이면
 * criterion 단독 그룹으로 떨어뜨린다 (숨기지 않는다 — 투명성 관례).
 * 좌우 미분할 = 승인본 '다리' 그룹 규칙.
 */
export function regionPartKeyForRecord(
  record: DeductionRecord,
  faultJoints: readonly KeypointName[] | undefined,
): string {
  const tokens = new Set<string>();
  for (const kp of projectDeductionRecordKeypoints(record, faultJoints)) {
    const token = BODY_PART_OF_KEYPOINT[kp];
    if (token) tokens.add(token);
  }
  if (tokens.size === 0) return `${CRITERION_GROUP_PREFIX}${record.criterion}`;
  return PART_ORDER.filter((t) => tokens.has(t)).join('+');
}

/**
 * 같은 원인에서 나온 감점을 **화면에서 한 항목으로** 묶는 그룹 키 (quick-260802-mrg).
 * record 마다 1개씩, 입력과 같은 길이·같은 순서로 돌려준다.
 *
 * 왜 필요한가: belle 실기기(2026-08-01) — 어깨 항목과 팔꿈치 항목이 **한 잘못**인데
 * 화면에 따로 보인다. 부위 토큰만으로는 어깨와 팔이 영영 갈라져 있다.
 *
 * **표시 전용이다.** 점수는 이 함수를 지나지 않는다 — `overallScore`·
 * `deductionBreakdown.final`·record 의 `points`/`measuredValue` 는 무접촉이고,
 * 점수 내역(ScoreBreakdownSection)은 record 1:1 로 남는다. 묶어 보여줘도 각 감점의
 * 크기는 블록마다 그대로 보인다(투명 합산 — belle 원칙).
 *
 * 병합 키 = `record.exerciseId`. 신규 계약 0 — 이미 실 doc 의 전 record 에 실려
 * 있다(`models.py DEDUCTION_PHRASE_KEYS` 각인, 저장 fixture 4건 전건 확인).
 * 백엔드 변경도 재분석도 필요 없다.
 *
 * 규칙 (merge-only — 오늘 한 그룹인 것이 갈라지는 경로가 없다):
 *   ① 오늘의 부위 키(`regionPartKeyForRecord`)를 먼저 구한다 — 그 함수는 손대지 않는다.
 *   ② `criterion:` 단독 그룹이 아닌 부위 키마다 멤버 record 의 exerciseId 를 모은다.
 *   ③ exerciseId 를 하나라도 공유하는 부위 키끼리 union-find 로 합친다.
 *   ④ 클러스터 키 = 멤버 부위 키들의 토큰 합집합을 `PART_ORDER` 로 결합. 기존 키
 *      문법 그대로라 `partLabelKo` 가 이미 '어깨·팔' 을 만든다(신규 어휘 0).
 *   ⑤ `criterion:` 키와, exerciseId 를 하나도 못 가진 부위 키는 자기 키를 유지한다.
 *
 * **부위 그룹을 쪼개지 않는다.** exerciseId 로 새로 나누면 한 동작에서 엉덩이
 * (hip_hamstring_tight)와 무릎(legs_not_extended)이 **둘 다 '다리' 칩**이 되어 같은
 * 이름 칩 2개가 생긴다. 그래서 병합은 부위 키 단위로만 일어나고, 한 부위 키의
 * record 는 exerciseId 보유 여부와 무관하게 **같은 클러스터 키를 받는다**.
 * (record 단위로 갈랐다면 '어깨'와 '어깨·팔' 칩이 동시에 서는 분열이 생긴다.)
 *
 * **시간 근접은 쓰지 않는다 — 병합 기준으로도, veto 로도.** 실 fixture 실측:
 * `left_elbow`(27프레임) ↔ `left_shoulder`(67프레임) = 40프레임 차,
 * `right_elbow`(44) ↔ `right_shoulder`(27) = 17프레임 차 — 어깨·팔꿈치를 둘 다 가진
 * 유일한 fixture 에서 시간 규칙은 병합을 0건 만든다. 반대로 `left_elbow`(27)와
 * `right_shoulder`(27)는 정확히 같은 프레임인데 반대측이고, power-spin
 * `leg_extension`(72)과 `left_shoulder`(66)는 0.67초 차인데 다리↔어깨다. 한 원인이
 * 서로 다른 순간에 드러나는 것이 실측이고, 그것이 belle 이 지목한 형태다.
 */
export function buildCauseGroupKeys(
  records: readonly DeductionRecord[],
  faultJoints: readonly KeypointName[] | undefined,
): string[] {
  const list = records ?? [];
  const baseKeys = list.map((rec) => regionPartKeyForRecord(rec, faultJoints));

  // ② 부위 키 → 그 키가 보유한 exerciseId 집합.
  // 빈 문자열·비문자열은 간선을 만들지 않는다 (억지 병합 금지 — 조건이 불확실하면
  // 따로 보여준다). legacy doc(필드 부재)은 여기서 자동으로 전부 걸러진다.
  const exerciseIdsByPart = new Map<string, Set<string>>();
  list.forEach((rec, i) => {
    const partKey = baseKeys[i];
    if (partKey.startsWith(CRITERION_GROUP_PREFIX)) return;
    const exerciseId =
      typeof rec.exerciseId === 'string' ? rec.exerciseId.trim() : '';
    if (exerciseId.length === 0) return;
    let bucket = exerciseIdsByPart.get(partKey);
    if (!bucket) {
      bucket = new Set<string>();
      exerciseIdsByPart.set(partKey, bucket);
    }
    bucket.add(exerciseId);
  });

  // ③ union-find (부위 키 위에서만 — record 위가 아니다).
  const parent = new Map<string, string>();
  const find = (key: string): string => {
    let root = key;
    while ((parent.get(root) ?? root) !== root) root = parent.get(root) as string;
    let cur = key;
    while ((parent.get(cur) ?? cur) !== cur) {
      const next = parent.get(cur) as string;
      parent.set(cur, root);
      cur = next;
    }
    return root;
  };
  const union = (a: string, b: string): void => {
    const ra = find(a);
    const rb = find(b);
    if (ra !== rb) parent.set(rb, ra);
  };

  const partKeyByExerciseId = new Map<string, string>();
  for (const [partKey, ids] of exerciseIdsByPart) {
    if (!parent.has(partKey)) parent.set(partKey, partKey);
    for (const id of ids) {
      const seen = partKeyByExerciseId.get(id);
      if (seen == null) partKeyByExerciseId.set(id, partKey);
      else union(seen, partKey);
    }
  }

  // ④ 클러스터 대표 키 = 멤버 부위 키들의 토큰 합집합 (PART_ORDER 순 — 결정적).
  const tokensByRoot = new Map<string, Set<string>>();
  for (const partKey of exerciseIdsByPart.keys()) {
    const root = find(partKey);
    let bucket = tokensByRoot.get(root);
    if (!bucket) {
      bucket = new Set<string>();
      tokensByRoot.set(root, bucket);
    }
    for (const token of partKey.split('+')) bucket.add(token);
  }
  const mergedKeyByRoot = new Map<string, string>();
  for (const [root, tokens] of tokensByRoot) {
    const merged = PART_ORDER.filter((t) => tokens.has(t)).join('+');
    mergedKeyByRoot.set(root, merged.length > 0 ? merged : root);
  }

  // ⑤ 부위 키 → 클러스터 키는 **함수**다 (한 부위 키가 한 출력 키로만 간다).
  // 그래서 distinct 출력 키 수는 distinct 부위 키 수를 넘을 수 없다 = merge-only.
  return baseKeys.map((partKey) => {
    if (partKey.startsWith(CRITERION_GROUP_PREFIX)) return partKey;
    if (!exerciseIdsByPart.has(partKey)) return partKey;
    return mergedKeyByRoot.get(find(partKey)) ?? partKey;
  });
}

/** 목표 절 접두 (33-13 `_meta.goalFirstCueLine`, belle 4R 승인 문형). */
const GOAL_CLAUSE_PREFIX = '목표는';
/** 목표 절과 행동 절의 구분자 — 동작 전용 entry 54건 전건이 보유(전수 확인). */
const GOAL_CLAUSE_SEPARATOR = '. ';

/**
 * cueLine 을 목표 절 / 행동 절로 나눈다 (quick-260802-mrg).
 *
 * **phrasebook 은 읽지도 고치지도 않는다.** 목표-선행 문형은 33-11 4R belle 승인 →
 * 33-13 구현 → `test_motion_specific_cueline_goal_first` 전수 핀이다. 문구를 되돌리면
 * 승인·핀·기존 doc·이미 합성된 mp3 가 전부 깨진다. 앱이 **렌더 시점에** 말하는
 * 자리만 옮긴다 — 저장 문자열은 그대로 두고, 자막에서는 결함을 먼저 말하고
 * 목표 문장은 묶인 항목 head 에서 한 번만 말한다.
 *
 * fail-closed — 접두(`목표는`)와 구분자(`. `)가 **둘 다** 성립할 때만 자른다:
 *   - `__common__` 문형(동작 미해석 폴백)에는 목표 절이 없다 → 원문 그대로.
 *   - 자른 뒤 행동 절이 비면 자르지 않는다 (빈 자막을 만들지 않는다).
 * `actionLine` 은 **항상 원 cueLine 의 부분 문자열**이다 — 음성 mp3 가 말하지 않은
 * 말을 자막이 만들어내지 않는다.
 */
export function splitGoalClause(cueLine: string | null | undefined): {
  goalLine: string | null;
  actionLine: string;
} {
  if (typeof cueLine !== 'string' || cueLine.length === 0) {
    return { goalLine: null, actionLine: '' };
  }
  if (!cueLine.startsWith(GOAL_CLAUSE_PREFIX)) {
    return { goalLine: null, actionLine: cueLine };
  }
  const cut = cueLine.indexOf(GOAL_CLAUSE_SEPARATOR);
  if (cut < 0) return { goalLine: null, actionLine: cueLine };
  const actionLine = cueLine.slice(cut + GOAL_CLAUSE_SEPARATOR.length);
  if (actionLine.length === 0) return { goalLine: null, actionLine: cueLine };
  return { goalLine: cueLine.slice(0, cut + 1), actionLine };
}

/**
 * 재생 중 자막 1줄 조립 (quick-260802-mrg) — **결함이 먼저**.
 *
 * belle 실기기(2026-08-01): 자막이 결함 대신 목표를 말한다. 자막은 3줄로 하드
 * 클립되는데(`VideoCompare` `numberOfLines={3}`) 목표 절이 앞에 있으면 잘리는 쪽이
 * 행동 절이고 결함은 애초에 자막에 없다.
 *
 * 규칙: `statusLine`(증상) → `causeLine`(원인, 선택) → `actionLine`(목표 절을 뺀
 * 행동). 목표 문장은 자막에서 빠지고 묶인 항목 head(`RegionSheetView.goalLine`)에서
 * 한 번만 말한다.
 *
 * 자막 유무 조건은 **바꾸지 않는다** — 오늘과 똑같이 행동구가 있어야 자막이 뜬다
 * (`cueTrack.buildCueWindows` 의 입력 집합·타이밍·밀도 무접촉). statusLine·causeLine
 * 은 붙는 접두일 뿐 자막을 새로 만들어내지 않는다.
 *
 * 절 사이에는 **문장 경계(마침표)** 를 넣는다 (belle 08-07 실기기 반려 — 경계 없이
 * 이으면 자막이 한 문장으로 이어지고 음성(Polly)은 run-on 낭독한다: "…좁아요 다리를
 * 와이드…"). 앞 절이 이미 문장부호로 끝나면 중복하지 않는다. 원인 절이 생긴 뒤에도
 * **같은 경계 규칙**이 절 공용으로 적용된다 (새 이음매에서 run-on 이 뚫리지 않게).
 *
 * `causeLine` (quick-260814-rcz, belle 08-14 "앞뒤로 설명이 필요"): 선택 절이며
 * 문자열이 아니거나 비면 **아예 없는 것처럼** 동작해 오늘과 문자 단위 동일한 2문장을
 * 낸다(무회귀 1급). 순서는 고정 — 원인을 행동 뒤에 두면 3줄 클립에서 가장 먼저
 * 잘리는 것이 행동절이 되어 2026-08-01 반려가 재발한다. 원인은 **측정값이 아니라
 * 가설**이고 문면은 승인 문구집(backend/data/phrasebook.json)이 소유한다.
 *
 * **Python lockstep** (debug va-subtitle-audio-mismatch 2026-08-07): Polly 음성
 * 합성 텍스트가 이 조립식을 그대로 미러한다 —
 * `backend/shared/python/sunity_shared/analysis/cue_text.py`
 * `coach_audio_speech_text` (+ `goal_clause_action_line` = `splitGoalClause` 미러,
 * GOAL_CLAUSE_PREFIX/SEPARATOR 상수·마침표 경계 규칙·causeLine 절 포함). 여기 조립
 * 규칙을 바꾸면 반드시 함께 바꿀 것 — 한쪽만 바뀌면 음성과 자막이 다시 갈라진다
 * (mrg 미검증 #4 의 재발). 대조는 눈으로 하지 않는다: 같은 fixture 를 양쪽 엔진에
 * 실제로 통과시키는 프로브가 있다 (backend/tests/phase32/compose_cue_probe.mjs).
 */
export function composeCueSubtitleKo(
  record: DeductionRecord,
  fallbackActionPhrase: string | null | undefined,
): string | null {
  const { actionLine } = splitGoalClause(record?.cueLine);
  const action =
    actionLine.length > 0
      ? actionLine
      : typeof fallbackActionPhrase === 'string'
        ? fallbackActionPhrase
        : '';
  if (action.length === 0) return null;
  const clauses: string[] = [];
  for (const value of [record?.statusLine, record?.causeLine]) {
    if (typeof value === 'string' && value.length > 0) clauses.push(value);
  }
  clauses.push(action);
  return clauses.reduce(
    (head, clause) => `${head}${/[.!?]$/.test(head) ? '' : '.'} ${clause}`,
  );
}

/**
 * 부위 키 → 화면 라벨. 33-G S3 (quick-260730-szk) — private `titleForPartKey` 에서
 * export 로 승격. **칩 라벨과 시트 제목이 문자 단위로 같아야** 승인본 어휘가 두
 * 표면에서 갈라지지 않는다(칩을 눌렀는데 다른 이름의 시트가 열리면 신뢰 결함).
 */
export function partLabelKo(partKey: string): string {
  if (partKey.startsWith(CRITERION_GROUP_PREFIX)) {
    return criterionLabelKo(partKey.slice(CRITERION_GROUP_PREFIX.length));
  }
  return partKey
    .split('+')
    .map((t) => BODY_PART_LABEL_KO[t] ?? t)
    .join('·');
}

/**
 * 비교 대상 명사 — `기준 (정은지)` → `기준`, `지난 영상` → `지난 영상`.
 * 승인 문형("기준 자세와 견줘요")은 mode1 라벨에서 그대로 재현되고, mode3 는
 * 자기 라벨로 흐른다 (mode 리터럴 분기 0).
 */
function compareNounKo(rightPairLabel: string): string {
  const cut = rightPairLabel.indexOf('(');
  const base = (cut >= 0 ? rightPairLabel.slice(0, cut) : rightPairLabel).trim();
  return base.length > 0 ? base : rightPairLabel.trim();
}

/** "무엇을 재는가" 사람 말. 말할 수 없으면 null (fail-closed). */
function measuredSubjectKo(criterion: string): string | null {
  if (criterion.startsWith(ANGLE_VS_REFERENCE_PREFIX)) {
    const jointKey = criterion.slice(ANGLE_VS_REFERENCE_PREFIX.length);
    return ANGLE_MEANING_KO[jointKey] ?? null;
  }
  const fixed = MEASURED_SUBJECT_KO[criterion];
  if (fixed) return fixed;
  if (SUBJECT_UNSPEAKABLE.includes(criterion)) return null;
  const label = criterionLabelKo(criterion);
  // criterionLabelKo 는 미등록 id 를 id 그대로 돌려준다 → 사람 말 아님 → 생략.
  return label !== criterion ? label : null;
}

/**
 * 블록에 쓸 행동 절 (quick-260802-mrg). cueLine 이 있으면 목표 절을 뺀 행동 절,
 * 없으면 기존 legacy 폴백(범례 행동구). 둘 다 없으면 null — 종전 동작 그대로다
 * (`rec.cueLine ?? actionPhrases[i] ?? null` 의 방출 조건 무변화).
 */
function actionLineOf(
  record: DeductionRecord,
  fallbackActionPhrase: string | null | undefined,
): string | null {
  const { actionLine } = splitGoalClause(record?.cueLine);
  if (actionLine.length > 0) return actionLine;
  return fallbackActionPhrase ?? null;
}

function pairCapWithSec(label: string, sec: number | null): string {
  const secLabel = formatVideoSecKo(sec);
  return secLabel ? `${label} · ${secLabel}` : label;
}

// ── 부위 그룹 마커 (33-G S1 / quick-260730-szk) ────────────────────────────

/**
 * 영상 위 **항목(부위) 단위 그룹 마커** 1건. 승인 목업 ① `.mkg` — "1라운드는 관절
 * 단위 원 7개 … 항목은 3개인데 동그라미가 7개라 혼란(belle) → **항목 단위 그룹
 * 3개**"(`mockups/index.html:314-317,331-335`).
 */
export interface PartGroupMarker {
  /** 부위 키 — 칩·시트와 **같은 단위**(`regionPartKeyForRecord` 단일 출처). */
  partKey: string;
  /** 이 부위에 속한 감점 record 의 전역 마커 번호 (오름차순). */
  numbers: number[];
  /** 배지 표기. 2건 이상이면 `2·3` 병합 (N-2 — 재생바 틱의 번호 병합 선례 계승). */
  badgeLabel: string;
  /** 경계 bounding 산출용 멤버 keypoint 합집합. */
  keypoints: KeypointName[];
}

/**
 * 감점 record → 부위 단위 그룹 마커 (N-1). **마커 그룹 = 부위 칩 = 부위 시트**가 같은
 * 단위여야 승인본의 "화면의 표시 수 = 항목 수"(`:349`)가 성립한다.
 *
 * 왜 `deductionLabels` 가 아니라 여기인가 (N-16): 부위 키 산출(`regionPartKeyForRecord`)
 * 이 이 파일 소유이고 `deductionSheet` → `deductionLabels` 는 이미 한 방향 의존이라
 * 반대 방향 import 는 순환이 된다. 두 번째 그룹핑 규칙을 쓰지 않기 위해 함수를 규칙
 * 쪽으로 옮겼다 — 부위 키 사본 0벌.
 *
 * 규칙 (전부 저장값 read-only — 재계산·재해석 0):
 *   - 순서 = 부위 첫 등장 순 (record 저장 순서 승계 — 엔진이 결정적 정렬).
 *   - `numbers` = 그 부위 멤버 record 중 번호가 부여된 것만, 오름차순.
 *   - `keypoints` = 멤버 record 투영의 합집합 (누락 0).
 *   - 번호 0개 부위는 제외 (번호 없는 경계 = 내역 행과 짝 없는 고아 표시, D-18).
 *   - 투영 keypoint 0개 부위(`line` 같은 collective criterion)도 제외 — 그릴 자리 없음.
 */
export function buildPartGroups(
  records: readonly DeductionRecord[],
  recordNumbers: readonly (number | null)[],
  faultJoints: readonly KeypointName[] | undefined,
): PartGroupMarker[] {
  const order: string[] = [];
  const byPart = new Map<
    string,
    { numbers: number[]; keypoints: KeypointName[] }
  >();
  const list = records ?? [];
  // quick-260802-mrg — 그룹 키의 단일 출처. 마커·칩·시트 세 소비처가 **같은 배열**을
  // 쓰므로 "마커 그룹 = 부위 칩 = 상세 시트"(33-G S1/S3)가 원인 단위에서도 유지된다.
  const groupKeys = buildCauseGroupKeys(list, faultJoints);
  list.forEach((rec, i) => {
    const partKey = groupKeys[i];
    let bucket = byPart.get(partKey);
    if (!bucket) {
      bucket = { numbers: [], keypoints: [] };
      byPart.set(partKey, bucket);
      order.push(partKey);
    }
    const num = recordNumbers?.[i];
    if (num != null) bucket.numbers.push(num);
    for (const kp of projectDeductionRecordKeypoints(rec, faultJoints)) {
      if (!bucket.keypoints.includes(kp)) bucket.keypoints.push(kp);
    }
  });

  const out: PartGroupMarker[] = [];
  for (const partKey of order) {
    const bucket = byPart.get(partKey);
    if (!bucket) continue;
    if (bucket.numbers.length === 0) continue;
    if (bucket.keypoints.length === 0) continue;
    const numbers = [...bucket.numbers].sort((a, b) => a - b);
    out.push({
      partKey,
      numbers,
      badgeLabel: numbers.join('·'),
      keypoints: bucket.keypoints,
    });
  }
  return out;
}

// ── 부위 칩 (33-G S3 / quick-260730-szk) ───────────────────────────────────

/** 승인 목업 ① `.jointchips` 의 버튼 1개. */
export interface PartChip {
  partKey: string;
  /** 감점 칩 = `partLabelKo` (시트 제목과 문자 동일) / 참고 칩 = `참고: {부위}`. */
  label: string;
  kind: 'deduction' | 'advisory';
  /**
   * 탭 시 열 시트의 record 인덱스. 그 부위의 **최소 번호** record (N-3 — 재생바 틱
   * `onTickPress(tick.numbers[0])` 선례). 부위 시트라 어느 멤버로 열어도 같은 시트.
   * 참고 칩은 record 가 없어 null (인라인 안내 토글, N-6).
   */
  firstRecordIndex: number | null;
  numbers: number[];
}

export interface PartChipsInput {
  records: readonly DeductionRecord[];
  /** 전역 마커 번호 (`buildDeductionMarkers().recordNumbers`) — 번호 단일 출처. */
  recordNumbers: readonly (number | null)[];
  /** 측정 초과·확인 권장 관절 (감점 아님) — 참고 칩 입력. */
  attentionKeypoints: readonly KeypointName[];
  /** IN-01 역립 저신뢰 — 부위 단정 칩 억제. */
  estimatedArea: boolean;
  faultJoints?: readonly KeypointName[];
}

/**
 * 부위 칩 행 (승인 목업 ① `:338-342` `다리` `어깨` `참고: 손`, `:317` "그룹이나 아래
 * **부위 버튼**을 누르면 ② 상세로 이동해요").
 *
 * F-8(D-42)로 상시 마커가 사라지므로 이 칩 행이 **상시 진입점**을 대체한다. 부위
 * 정의는 `buildPartGroups` 를 그대로 소비 — 두 번째 그룹핑 규칙 금지.
 *
 * fail-closed:
 *   - `records` 0 → `[]` (N-14. 승인본 ① 은 감점 항목 화면이고, 칩 0개 빈 행은
 *     "기본 화면 새 문장 0"(D-05·S5) 위반).
 *   - `estimatedArea` → `[]` (IN-01 전용 진입점 카드가 이미 있고, 저신뢰에서 부위를
 *     단정하는 칩은 S17 PASS 를 깬다).
 */
export function buildPartChips(input: PartChipsInput): PartChip[] {
  const records = input.records ?? [];
  if (records.length === 0) return [];
  if (input.estimatedArea === true) return [];

  const groups = buildPartGroups(
    records,
    input.recordNumbers ?? [],
    input.faultJoints,
  );
  // quick-260802-mrg — 그룹 키는 buildPartGroups 와 **같은 함수**에서 나온다
  // (두 번째 그룹핑 규칙 금지 — 사본이 생기면 칩과 마커가 다른 단위가 된다).
  const groupKeys = buildCauseGroupKeys(records, input.faultJoints);

  const chips: PartChip[] = [];
  const claimedTokens = new Set<string>();
  for (const g of groups) {
    // 최소 번호를 가진 멤버 record 의 인덱스 (N-3).
    const target = g.numbers[0];
    let firstRecordIndex: number | null = null;
    records.forEach((_rec, i) => {
      if (firstRecordIndex != null) return;
      if (groupKeys[i] !== g.partKey) return;
      if (input.recordNumbers?.[i] === target) firstRecordIndex = i;
    });
    chips.push({
      partKey: g.partKey,
      label: partLabelKo(g.partKey),
      kind: 'deduction',
      firstRecordIndex,
      numbers: g.numbers,
    });
    if (!g.partKey.startsWith(CRITERION_GROUP_PREFIX)) {
      for (const token of g.partKey.split('+')) claimedTokens.add(token);
    }
  }

  // 참고 칩 — attention keypoint 를 부위 토큰으로 접고 감점 부위와 겹치면 제외.
  // 순서 = PART_ORDER (머리→발), 라벨 = 승인본 `참고: 손` 형식.
  const advisoryTokens = new Set<string>();
  for (const kp of input.attentionKeypoints ?? []) {
    const token = BODY_PART_OF_KEYPOINT[kp];
    if (!token) continue;
    if (claimedTokens.has(token)) continue;
    advisoryTokens.add(token);
  }
  for (const token of PART_ORDER) {
    if (!advisoryTokens.has(token)) continue;
    chips.push({
      partKey: token,
      label: `참고: ${BODY_PART_LABEL_KO[token] ?? token}`,
      kind: 'advisory',
      firstRecordIndex: null,
      numbers: [],
    });
  }
  return chips;
}

// ── 뷰모델 조립 ───────────────────────────────────────────────────────────

export function buildRegionSheetView(
  input: RegionSheetInput,
): RegionSheetView | null {
  const records = input.records ?? [];
  const selectedIndex = input.selectedRecordIndex;
  if (records.length === 0) return null;
  if (selectedIndex == null || !Number.isInteger(selectedIndex)) return null;
  if (selectedIndex < 0 || selectedIndex >= records.length) return null;
  const selected = records[selectedIndex];
  if (!selected) return null;

  // quick-260802-mrg — 시트 그룹도 원인 단위. 칩·마커와 같은 함수를 쓴다.
  const groupKeys = buildCauseGroupKeys(records, input.faultJoints);
  const partKey = groupKeys[selectedIndex];
  const memberIndexes: number[] = [];
  records.forEach((_rec, i) => {
    if (groupKeys[i] === partKey) memberIndexes.push(i);
  });
  if (memberIndexes.length === 0) return null;

  const zoomOf = (i: number): FaultZoomComparison | null =>
    input.zooms?.[i] ?? null;

  // M-5 — 그룹 크롭 = 저장순 첫 매치 카드. 블록 순서 = 그 record 먼저, 나머지 저장순
  // (승인본 주석 "사진의 마킹이 가리키는 결함 먼저"를 불변식으로 옮긴 것).
  const primaryRecordIndex =
    memberIndexes.find((i) => zoomOf(i) != null) ?? memberIndexes[0];
  const orderedIndexes = [
    primaryRecordIndex,
    ...memberIndexes.filter((i) => i !== primaryRecordIndex),
  ];
  const primaryZoom = zoomOf(primaryRecordIndex);

  const title = partLabelKo(partKey);
  const compareNoun = compareNounKo(input.rightPairLabel);
  const estimatedArea = input.estimatedArea === true;

  // ── 크롭 카드 (chip → cropimg → paircap → onecap) ────────────────────────
  const userSec = videoSecOf(primaryZoom?.userVideoSec);
  const refSec = videoSecOf(primaryZoom?.refVideoSec);
  const pairCapLeft = primaryZoom
    ? pairCapWithSec(PAIR_CAP_SELF_LABEL, userSec)
    : null;
  const pairCapRight = primaryZoom
    ? pairCapWithSec(input.rightPairLabel, refSec)
    : null;

  const isAdvisoryOnly = primaryZoom?.tier === 'advisory';
  // M-6 — 어떤 마킹이 실제 베이크됐는지는 doc 에 없다(각도 베이크는 일부 카드만).
  // "빨간 두 줄 / 꼭짓점 = 겨드랑이"를 상시 문구로 넣으면 대부분 카드에서 거짓
  // 지칭이 된다 → **무엇을 견주는지만** 말한다.
  let oneCap: string | null = null;
  if (isAdvisoryOnly) {
    oneCap = ADVISORY_NOTE_KO;
  } else if (primaryZoom) {
    const subject = measuredSubjectKo(records[primaryRecordIndex].criterion);
    if (subject) {
      oneCap = `이 사진은 ${subject}${objectJosaKo(subject)} ${compareNoun} 자세와 견줘요`;
    }
  }

  // ── 결함 블록 N개 ────────────────────────────────────────────────────────
  // M-4 — 번호는 전역 마커 번호(recordNumbers)를 그대로 쓴다. "영상 위 점 안 숫자 =
  // 내역 행 원문자 = 블록 번호"가 한 소스에서 나온다. 그룹 1건이면 번호 절 생략
  // (승인본 shoulder 형식), estimatedArea 면 번호 억제(오버레이 번호도 억제됨).
  const useNumbers = !estimatedArea && orderedIndexes.length >= 2;

  const blocks: RegionSheetBlock[] = orderedIndexes.map((i) => {
    const rec = records[i];
    const row = formatDeductionRecord(rec);
    const number = input.recordNumbers?.[i] ?? null;
    const label = criterionLabelKo(rec.criterion);
    const points = formatDeductionNumber(Math.abs(rec.points));
    const header =
      useNumbers && number != null
        ? `${BLOCK_HEAD_PREFIX} ${number} — ${label} (−${points}점)`
        : `${BLOCK_HEAD_PREFIX} — ${label} (−${points}점)`;

    const blockZoom = zoomOf(i);
    const blockRefSec = videoSecOf(blockZoom?.refVideoSec);
    const subject = measuredSubjectKo(rec.criterion);

    // basis (M-7) — 재는 대상 + 그 값을 잰 순간. 구간 축은 §C-4 이관.
    //
    // quick-260801-gbk — "잰 순간" 절의 출처와 방출 조건을 함께 바꾼다.
    // 출처: 표시 프레임의 초(zoom.userVideoSec)가 아니라 **이 감점을 잰 초**
    //   (rec.atVideoSec). 종전엔 두 값이 항상 같았지만, 그 이유는 모든 카드가
    //   worst_seconds 한 시각에서 잘렸기 때문이었다 — 문장은 맞고 사진이 틀렸다.
    // 조건: 그 행에 사진이 있고(blockZoom), 그 사진이 **바로 그 순간임을 백엔드가
    //   인증**했을 때만(atMatched). 출처만 바꾸면 사진 없는 행(line·카드 4장 초과분)과
    //   앵커 미채택 카드까지 절을 얻어, 없애려던 거짓을 역방향으로 재생산한다.
    // 인증은 앱이 계산하지 않는다 — 초 차이를 앱이 빼면 fps·프레임 공간을 앱이
    //   알아야 하고 그 구조가 정확히 §11.8 F-3 을 만들었다.
    let basisLine: TextSegment[] | null = null;
    const blockMeasuredSec =
      blockZoom != null && blockZoom.atMatched === true
        ? videoSecOf(rec.atVideoSec)
        : null;
    const blockUserSecLabel = formatVideoSecKo(blockMeasuredSec);
    if (subject || blockUserSecLabel) {
      const segments: TextSegment[] = [{ text: BASIS_LABEL, bold: true }];
      if (subject) {
        segments.push({
          text: ` 이 항목은 ${subject}${objectJosaKo(subject)} 재요.`,
        });
        if (blockUserSecLabel) {
          segments.push({
            text: ` 위 사진은 그 값을 잰 순간(${blockUserSecLabel})이에요.`,
          });
        }
      } else if (blockUserSecLabel) {
        segments.push({
          text: ` 위 사진은 이 항목을 잰 순간(${blockUserSecLabel})이에요.`,
        });
      }
      basisLine = segments;
    }

    // method (M-8) — source × deviationSource 키잉. ipsf_absolute 는 승인본에
    // 해당 문형이 없어 미방출 (없는 문구를 창작하지 않는다 — basis 가 그 역할).
    let methodLine: string | null = null;
    if (rec.source === 'vision') {
      methodLine = METHOD_VISION;
    } else if (
      rec.source === 'geometry' &&
      rec.deviationSource === 'reference_relative'
    ) {
      const blockRefSecLabel = formatVideoSecKo(blockRefSec);
      methodLine = blockRefSecLabel
        ? `${METHOD_ALIGNED} 기준 사진은 그 정렬이 실제로 짝지은 순간(${compareNoun} ${blockRefSecLabel})이에요.`
        : METHOD_ALIGNED;
    }

    // numnote (M-13) — 수치의 승인 거처. formatDeductionRecord 는 수정하지 않는다
    // (ScoreBreakdownSection 공유 — PASS 표면 보호).
    const numNote = estimatedArea
      ? ESTIMATED_AREA_POINTS_NOTE
      : `${NUM_NOTE_PREFIX}${row.detailText} → ${row.pointsText}점`;

    const blockRecordIndexForCrop =
      i !== primaryRecordIndex &&
      blockZoom != null &&
      blockZoom.imageUrl !== primaryZoom?.imageUrl
        ? i
        : null;

    return {
      recordIndex: i,
      header,
      statusLine: rec.statusLine ?? null,
      whyLine: rec.whyLine ?? null,
      basisLine,
      // quick-260802-mrg — 블록은 **행동 절만** 말한다. 목표 절은 시트 head 의
      // goalLine 이 한 번 말한다 (같은 문장 N번 반복 금지). 목표 절이 없는 문형
      // (__common__)은 splitGoalClause 가 원문을 그대로 돌려주므로 무변화.
      cueLine: actionLineOf(rec, input.actionPhrases?.[i]),
      methodLine,
      numNote,
      blockRecordIndexForCrop,
    };
  });

  // ── goalLine (quick-260802-mrg) ─────────────────────────────────────────
  // 대표 record = 그룹에서 |points| 최대(동점이면 저장 순서 앞선). 그 record 의
  // 목표 절만 쓴다 — 다른 멤버를 뒤져 문장을 찾지 않는다(대표는 하나).
  // 실 데이터상 목표 절은 **동작 단위 속성**이라(phrasebook 동작별 distinct 목표
  // 절 = 전 동작 1개, 전수 확인) 대표를 누구로 잡아도 문장이 갈리지 않는다.
  let goalRecordIndex: number | null = null;
  let goalBestAbs = -1;
  // memberIndexes 는 저장 순서 오름차순이라 strict `>` 가 곧 "동점이면 앞선 것".
  for (const i of memberIndexes) {
    const abs = Math.abs(records[i]?.points ?? 0);
    if (!Number.isFinite(abs)) continue;
    if (abs > goalBestAbs) {
      goalBestAbs = abs;
      goalRecordIndex = i;
    }
  }
  const goalLine =
    goalRecordIndex == null
      ? null
      : splitGoalClause(records[goalRecordIndex]?.cueLine).goalLine;

  // ── facing (M-9) ────────────────────────────────────────────────────────
  // 승인본 분포(어깨 = 있음 / 다리 = 없음)를 **데이터로** 재현한다: 기준 정렬로 잰
  // 항목(reference_relative)이 그룹에 있고 두 초를 다 알 때만. 승인본의 "정은지는
  // 무릎을 모아 폴에 붙인 고정 회전 자세" 절은 그 동작·그 순간의 관찰이라 제외한다
  // (single-motion-fixation 금지).
  const hasReferenceRelative = orderedIndexes.some(
    (i) => records[i].deviationSource === 'reference_relative',
  );
  let facingLine: string | null = null;
  if (hasReferenceRelative && userSec != null && refSec != null) {
    const userDigits = userSec.toFixed(1);
    const refDigits = refSec.toFixed(1);
    if (userDigits !== refDigits) {
      facingLine =
        `${FACING_PREFIX}두 장면은 같은 동작의 서로 다른 순간이에요(내 ${userDigits}초 ↔ ${compareNoun} ${refDigits}초). ` +
        `분석이 같은 구간으로 짝지은 순간이라, 몸 방향이 달라 보여도 ${title} 각도만 견줘 보세요.`;
    }
  }

  return {
    partKey,
    title,
    primaryRecordIndex,
    primaryCriterion: records[primaryRecordIndex].criterion,
    goalLine,
    blocks,
    pairCapLeft,
    pairCapRight,
    oneCap,
    facingLine,
    isAdvisoryOnly,
  };
}
