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
  // 보완 운동 진입점 존재 (개인화 추천 또는 라이브러리).
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
    growth: { key: 'growth', visible: isMode3, variant: growthVariant },
    exercise: { key: 'exercise', visible: input.hasExercise !== false },
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
