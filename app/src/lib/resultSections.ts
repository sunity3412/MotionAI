// 결과 화면 섹션 순서·표시 여부·legacy 분기 순수 뷰모델 (32-11 Task 1 — 리뷰 MEDIUM).
//
// 순수 함수만 — react/expo 의존 0, AsyncStorage 무관, 부수효과 0. `node --test` +
// `tsc --noEmit` 검증 (summarySource.ts / cueTrack.ts 헤더 관례).
//
// 왜: result.tsx 는 2,700줄 대배선이라 "섹션이 D-02 확정 순서로, 조건대로 보인다"를
// typecheck 만으로 보증할 수 없다. 순서·가시성·legacy 분기·recordId 조인을 이 파일이
// 단일 결정 지점으로 소유하고, result.tsx 는 이 결과를 소비해 같은 순서로 렌더한다.
//
// 확정 순서 원천 = 32-GATE-DECISIONS.md D-02 (10항 순서 승인 + 세로 스크롤):
//   요약 → 위험(있을 때만) → 오늘 고칠 것 top-1 → 동작 비교 → 나머지 감점(접힘) →
//   성장·지난 미션 → 보완 운동 → 강사 질문 → 심사 정보 코너 → 참고하세요(31).
// 근거 = Shneiderman overview-first + 위험 트리아지(Kaia) + 31 D-09 invariant
// (참고코너는 채점 표면 전부 뒤).
//
// 입력은 **구조적 타이핑 로컬 인터페이스**로 받는다 (summarySource.ts 관례) — 32-06
// 계약 타입에 컴파일 의존하지 않고, result.tsx 배선 시 실 doc 파생값이 자연 결합한다.

// ── 섹션 키 (D-02 확정 순서 단일 출처) ──────────────────────────────────────

export type ResultSectionKey =
  | 'summary'
  | 'risk'
  | 'topFix'
  | 'compare'
  | 'collapsed'
  | 'growth'
  | 'exercise'
  | 'questions'
  | 'judgeInfo'
  | 'referenceCorner';

export const RESULT_SECTION_ORDER: ResultSectionKey[] = [
  'summary',
  'risk',
  'topFix',
  'compare',
  'collapsed',
  'growth',
  'exercise',
  'questions',
  'judgeInfo',
  'referenceCorner',
];

// ── 입력 (구조적 로컬 인터페이스 — 계약 import 아님) ─────────────────────────

export interface ResultSectionsInput {
  mode: 'mode1' | 'mode3';
  // 감점 0 게이트 (isCleanPass 단일 신호) — 문제 섹션 숨김 + 요약 축하 전환.
  isCleanPass: boolean;
  // mode3 미보유/저신뢰 억제 — 채점 표면 대체.
  isScoreSuppressed?: boolean;
  safetyFlagCount: number;
  // deductionBreakdown records 존재 (top-1·접힘·심사 시뮬레이션 재료).
  hasRecords: boolean;
  hasMission: boolean;
  // D-27 — 2회차 exercise_detour / 3회차 coach_card.
  escalation?: 'none' | 'exercise_detour' | 'coach_card' | null;
  hasMissionOutcome: boolean;
  // 3단 문구(statusLine/cueLine 방출) 존재 — 부재면 legacy 폴백 렌더.
  hasPhrases: boolean;
  // mode3 첫 분석 (이전 영상 없음 — 동작 비교 부재).
  isMode3First?: boolean;
  // 강사 질문(자동 수집 + 사용자 담기) 존재.
  hasQuestions?: boolean;
  // 보완 운동 — belle 2026-08-31 빈 상태 규칙: 의미를 "개인화 전면 운동
  // (frontExercise) 존재"로 좁힘. 부재 시 섹션 전체 숨김 ("매핑이 없어요" 빈
  // 안내 카드가 자리를 차지하던 것 제거 — 전체 라이브러리 진입점은 존재 여부와
  // 무관하게 이 섹션의 존재 이유가 아니다).
  hasExercise?: boolean;
  // 게이트 확정과 다른 순서를 강제해야 할 때만(후속 재조정 훅). 부재 = 확정 순서.
  gateOrder?: ResultSectionKey[];
}

export interface ResultSection {
  key: ResultSectionKey;
  visible: boolean;
  variant?: string;
}

// gateOrder 정규화 — 알려진 키만, 중복 제거, 누락 canonical 키는 뒤에 승계(전 섹션
// 계산 보장 — Test 3 "부분 계산 크래시 0"). 부재/빈 배열 = 확정 순서 그대로.
function normalizeOrder(gateOrder: ResultSectionKey[] | undefined): ResultSectionKey[] {
  if (!Array.isArray(gateOrder) || gateOrder.length === 0) {
    return RESULT_SECTION_ORDER;
  }
  const known = new Set(RESULT_SECTION_ORDER);
  const seen = new Set<ResultSectionKey>();
  const out: ResultSectionKey[] = [];
  for (const k of gateOrder) {
    if (known.has(k) && !seen.has(k)) {
      seen.add(k);
      out.push(k);
    }
  }
  for (const k of RESULT_SECTION_ORDER) {
    if (!seen.has(k)) out.push(k);
  }
  return out;
}

// ── 섹션 순서·가시성·variant 결정 (단일 지점) ───────────────────────────────

export function deriveResultSections(input: ResultSectionsInput): ResultSection[] {
  const isMode3 = input.mode === 'mode3';
  const suppressed = input.isScoreSuppressed === true;
  const clean = input.isCleanPass === true;
  const isMode3First = input.isMode3First === true;

  // 요약 카드 — 항상 첫 콘텐츠. 억제 > 축하(clean) > 기본.
  const summaryVariant = suppressed ? 'suppressed' : clean ? 'clean' : 'default';

  // 성장 — mode3 전용. coach_card 승격이 outcome 보다 우선(D-27 3회차).
  const growthVariant =
    input.escalation === 'coach_card'
      ? 'coachCard'
      : input.hasMissionOutcome
        ? 'outcome'
        : isMode3First
          ? 'first'
          : 'default';

  const build: Record<ResultSectionKey, ResultSection> = {
    summary: { key: 'summary', visible: true, variant: summaryVariant },
    risk: { key: 'risk', visible: input.safetyFlagCount > 0 },
    topFix: {
      key: 'topFix',
      visible: !clean && !suppressed && input.hasRecords,
      variant: input.hasPhrases ? 'phrased' : 'legacy',
    },
    compare: { key: 'compare', visible: !isMode3First },
    collapsed: { key: 'collapsed', visible: !clean && input.hasRecords },
    // belle 2026-08-31 빈 상태 규칙 — 내용이 '없음'인 성장 섹션 미렌더:
    // missionOutcome 실체 또는 coach_card 승격이 있을 때만. 구 빈 안내문("이어갈
    // 지난 미션이 없어요"/"다음 분석부터 이전 미션…")은 mode3-first 안내문과
    // 의미 중복이라 렌더 경로 차단 (정보 손실 0 — 의미 잔존처 실재).
    growth: {
      key: 'growth',
      visible:
        isMode3 &&
        (input.escalation === 'coach_card' || input.hasMissionOutcome),
      variant: growthVariant,
    },
    // belle 2026-08-31 빈 상태 규칙 — 개인화 전면 운동 존재 시만 (hasExercise
    // 의미 축소와 lockstep). 구 `!== false`(미전달=표시)는 빈 상태 카드를 낳았다.
    exercise: { key: 'exercise', visible: input.hasExercise === true },
    questions: { key: 'questions', visible: input.hasQuestions === true },
    judgeInfo: {
      key: 'judgeInfo',
      visible: !suppressed && input.hasRecords,
    },
    // ReferenceCornerSection 은 세 카드 모두 숨김이면 스스로 null 반환 — 여기선 항상
    // 배치 슬롯을 열어둔다(채점 표면 뒤, 31 D-09 invariant).
    referenceCorner: { key: 'referenceCorner', visible: true },
  };

  return normalizeOrder(input.gateOrder).map((k) => build[k]);
}

// ── recordId 조인 맵 (정렬·필터·숨김 안전 — 배열 index 금지, 리뷰 반영) ────────

// 조인 대상 최소 구조 (계약 부분집합 — result.tsx 가 실 타입을 넘긴다).
export interface RecordLike {
  recordId?: string | null;
}
export interface CoachQuestionLike {
  recordId?: string | null;
}
export interface ZoomLike {
  recordId?: string | null;
}

// Z 는 제약 없음(기본 ZoomLike) — 실 zoom 계약(FaultZoomComparison)이 recordId 를
// 갖지 않아도 매처(matchZoom) 주입 경로로 조인하기 위함. weak-type 회피.
export interface RecordMapEntry<R extends RecordLike, Z, Q extends CoachQuestionLike> {
  record: R;
  key: string; // 안정 조인 키 (recordId 또는 'idx:N')
  index: number; // 원 배열 index (점프 y 조인·legacy 폴백용)
  questions: Q[]; // recordId 로 조인된 질문 (부재 record = 빈 배열)
  zoomPair: Z | null; // 매칭 확대쌍 (없으면 null)
}

/**
 * records → recordId 조인 맵. 키는 record.recordId(비어있지 않을 때) 또는 'idx:N'
 * 폴백. 같은 recordId 가 두 번 나오면 두 번째는 'idx:N' 으로 강등해 **키 충돌 0**.
 *
 * - questions: recordId 가 일치하는 질문만 해당 record 엔트리에 조인. recordId 부재
 *   질문은 어느 record 에도 붙지 않는다(안전 질문 등 — 별도 렌더).
 * - zoomPair: matchZoom 제공 시 그 결과(result.tsx 가 keypoint 투영 매처 주입).
 *   미제공 시 zoom.recordId === record.recordId 조인(향후 recordId 각인 zoom 대비).
 */
export function buildRecordMaps<
  R extends RecordLike,
  Z = ZoomLike,
  Q extends CoachQuestionLike = CoachQuestionLike,
>(
  records: readonly R[] | null | undefined,
  zooms: readonly Z[] | null | undefined,
  questions: readonly Q[] | null | undefined,
  matchZoom?: (record: R, index: number) => Z | null,
): Map<string, RecordMapEntry<R, Z, Q>> {
  const map = new Map<string, RecordMapEntry<R, Z, Q>>();
  const used = new Set<string>();
  const recs = Array.isArray(records) ? records : [];
  const qs = Array.isArray(questions) ? questions : [];
  const zs = Array.isArray(zooms) ? zooms : [];

  recs.forEach((record, index) => {
    const rid =
      typeof record.recordId === 'string' && record.recordId.length > 0
        ? record.recordId
        : null;
    // 안정 키 — recordId 우선, 충돌·부재 시 'idx:N' 폴백.
    let key = rid ?? `idx:${index}`;
    if (used.has(key)) key = `idx:${index}`;
    used.add(key);

    const joinedQuestions =
      rid != null ? qs.filter((q) => q.recordId === rid) : [];

    let zoomPair: Z | null = null;
    if (matchZoom) {
      zoomPair = matchZoom(record, index);
    } else if (rid != null) {
      // Z 는 제약 없음 — 폴백 recordId 조인은 구조적 캐스트로만(향후 recordId 각인 zoom).
      zoomPair =
        zs.find((z) => (z as ZoomLike).recordId === rid) ?? null;
    }

    map.set(key, { record, key, index, questions: joinedQuestions, zoomPair });
  });

  return map;
}

// ── F-7 펼침/접기 스크롤 앵커 (33-G F-7, quick-260731-cum) ────────────────────

/**
 * '자세히 보기'/'접기' 전환 시 스크롤할 목표 y. 주어진 키 순서대로 **처음으로
 * 기록된** 앵커의 `max(0, y - pad)` 를 반환하고, 하나도 없으면 `null`(호출측 폴백).
 *
 * 왜 순수 함수인가: 종전 result.tsx 의 인라인 루프는 펼치기 **전에** 측정된
 * `anchor:scoreGauge` y 로 곧장 점프해 요약 카드에서 한참 아래로 내려갔고
 * (belle "확 내려감"), 그 y 자체도 stale 이었다. 호출측이 요약 카드 앵커를 1순위로
 * 넘기면 누른 줄이 화면에 남는다 — 그 선택 규칙을 여기서 테스트 가능한 한 지점으로
 * 소유한다.
 */
export function pickExpandAnchorY(
  cardY: ReadonlyMap<string, number>,
  keys: readonly string[],
  pad: number,
): number | null {
  for (const key of keys) {
    const y = cardY.get(key);
    if (typeof y === 'number' && Number.isFinite(y)) {
      return Math.max(0, y - pad);
    }
  }
  return null;
}

// index → 안정 키 역산 (result.tsx 가 legacy index 폴백 조인 시 사용).
export function recordKeyForIndex(
  records: readonly RecordLike[] | null | undefined,
  index: number,
): string {
  const rec = Array.isArray(records) ? records[index] : undefined;
  const rid =
    rec && typeof rec.recordId === 'string' && rec.recordId.length > 0
      ? rec.recordId
      : null;
  return rid ?? `idx:${index}`;
}

// ── IN-01 저신뢰 경로 예상 부위 사진 카드 선택 (quick-260903-ftg) ────────────────

export interface EstimatedZoomEntry<Z> {
  recordIndex: number; // 원 배열 index — 탭 시 setDetailRecordIndex 조인(종전 링크와 동일)
  zoom: Z; // 매칭된 확정 확대비교 카드 (result.tsx 가 resolveZoomImageUrl 로 URL 조회)
}

/**
 * 역립 저신뢰(IN-01, quick-260724-q6b) 경로에서 확정 확대비교 카드 **전부**를
 * "예상 부위 (참고)" 카드로 내는 선택 규칙의 단일 지점.
 *
 * 왜: 그 경로는 topFix 카드·'다른 감점 항목' 목록이 억제돼 확대비교 진입점이
 * "예상 부위 확대 비교 보기" 링크 1개(|points| 최대 record 1건의 시트)뿐이었다 —
 * 확정 카드가 2장(왼팔꿈치·왼엉덩이)이어도 두 번째는 도달 불가 (09-03 시뮬 실측,
 * belle 09-02 "왜 확대비교 사진이 하나밖에 없어"). belle 07-24 결정("예상 부위라도
 * 보여줘야")의 연장: 같은 hedge 라벨로 사진을 링크 뒤가 아니라 인라인에, 그리고
 * 전부. 관절명·statusLine·수치는 여기서 내지 않는다 — 제네릭이라 record 내용에
 * 접근할 수 없고 순서·포함 여부만 결정한다 (IN-01 per-joint 단정 강등 락 유지).
 *
 * 규칙:
 * - records 순서로 훑되 `primaryIndex`(estimatedAreaRecordIndex — |points| 최대,
 *   오버레이 주황 점과 같은 record)가 유효하면 **맨 앞**.
 * - 숨김 record(스팟체크 `isHidden`) 제외 — 카드 표면 규칙(D-23)과 동일.
 * - 매칭 zoom 없음 제외 (빈 시트 열지 않음 — 종전 링크와 동일).
 * - 같은 카드(`zoomKey` 동일 — 좌+우 region 묶음 카드가 두 record 에 매칭되는
 *   경우)는 첫 등장만.
 * - records null/undefined/빈 배열 = 빈 배열 (matchZoom 미호출).
 */
export function selectEstimatedZoomEntries<R, Z>(
  records: readonly R[] | null | undefined,
  matchZoom: (record: R, index: number) => Z | null,
  zoomKey: (zoom: Z) => string,
  isHidden: (record: R) => boolean,
  primaryIndex: number | null,
): EstimatedZoomEntry<Z>[] {
  const recs = Array.isArray(records) ? records : [];
  if (recs.length === 0) return [];

  // 순회 순서 — 유효한 primary 먼저, 나머지는 원 배열 순서.
  const hasPrimary =
    primaryIndex != null &&
    Number.isInteger(primaryIndex) &&
    primaryIndex >= 0 &&
    primaryIndex < recs.length;
  const order: number[] = hasPrimary ? [primaryIndex as number] : [];
  for (let i = 0; i < recs.length; i += 1) {
    if (hasPrimary && i === primaryIndex) continue;
    order.push(i);
  }

  const seen = new Set<string>();
  const out: EstimatedZoomEntry<Z>[] = [];
  for (const i of order) {
    const rec = recs[i];
    if (isHidden(rec)) continue;
    const zoom = matchZoom(rec, i);
    if (zoom == null) continue;
    const key = zoomKey(zoom);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ recordIndex: i, zoom });
  }
  return out;
}
