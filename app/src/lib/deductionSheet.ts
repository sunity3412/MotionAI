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
/** advisory(참고 부위) onecap — 기하 무단정이라 승인 원문 그대로. */
const ADVISORY_ONE_CAP =
  '참고 부위예요 — 점수 감점은 되지 않지만 회전·힘 같은 전체 동작에 영향을 줄 수 있어요. 눈에 띈 차이만 보여드려요';
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
  /** `고칠 것 2 — 다리 신전(펴짐) (−20점)` — 번호 절은 그룹 2건 이상일 때만. */
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

function titleForPartKey(partKey: string): string {
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

function pairCapWithSec(label: string, sec: number | null): string {
  const secLabel = formatVideoSecKo(sec);
  return secLabel ? `${label} · ${secLabel}` : label;
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

  const partKey = regionPartKeyForRecord(selected, input.faultJoints);
  const memberIndexes: number[] = [];
  records.forEach((rec, i) => {
    if (regionPartKeyForRecord(rec, input.faultJoints) === partKey) {
      memberIndexes.push(i);
    }
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

  const title = titleForPartKey(partKey);
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
    oneCap = ADVISORY_ONE_CAP;
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
    const blockUserSec = videoSecOf(blockZoom?.userVideoSec);
    const blockRefSec = videoSecOf(blockZoom?.refVideoSec);
    const subject = measuredSubjectKo(rec.criterion);

    // basis (M-7) — 재는 대상 + 그 값을 잰 순간. 구간 축은 §C-4 이관.
    let basisLine: TextSegment[] | null = null;
    const blockUserSecLabel = formatVideoSecKo(blockUserSec);
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
      cueLine: rec.cueLine ?? input.actionPhrases?.[i] ?? null,
      methodLine,
      numNote,
      blockRecordIndexForCrop,
    };
  });

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
    blocks,
    pairCapLeft,
    pairCapRight,
    oneCap,
    facingLine,
    isAdvisoryOnly,
  };
}
