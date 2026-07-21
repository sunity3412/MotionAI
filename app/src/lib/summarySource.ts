// 요약 카드 3요소(잘한 점 / 오늘 고칠 것 / 다음 행동) 선정 순수 함수
// (32-07 Task 2 — 32-CONTEXT D-06/D-26 + 32-PLAN-REVIEW blocker 5).
//
// 순수 함수만 — react/expo 의존 0, AsyncStorage 무관, 부수효과 0. 단위 test 로 전부
// 검증 (pickerFailure.ts/alignmentWarp.ts 헤더 관례).
//
// 입력은 **구조적 타이핑 로컬 인터페이스**로 받는다 — 32-06 이 추가한 계약 타입
// (SummaryPraise/Mission/MissionOutcome/DeductionRecord, analysis.ts)에 컴파일
// 의존하지 않기 위해서다. TS 구조적 타이핑이라 32-11 배선 시 실 doc 필드가 이
// 인터페이스에 자연 결합한다 (analysis.ts import 0 — 계약 재정의가 아니라 소비 계약).
//
// 단일 원천 원칙(blocker 5): 잘한 점 헤드라인의 정본은 백엔드 방출 summaryPraise
// (32-05 phrasebook 조립 → 32-09 방출)다. 이 함수는 (1) doc summaryPraise 를 그대로
// 소비하고, (2) 스팟체크(32-13)가 불일치를 표시하면 강등하며, (3) legacy doc(방출
// 이전)일 때만 로컬 폴백 체인으로 파생한다. 그래서 스팟체크가 검증한 문장과 화면에
// 렌더되는 문장이 동일해진다.
//
// D-09 불변식: 헤드라인 문자열에 측정 수치를 넣지 않는다. 수치는 evidenceValue/
// evidenceUnit 구조 필드로만 분리하며, 렌더 여부·위치는 소비 컴포넌트(SummaryCard)
// 소관이다.

// ── 입력 (구조적 로컬 인터페이스 — analysis.ts 계약의 소비 형상, import 아님) ────

export type SummaryMode = 'mode1' | 'mode3';

// 백엔드 방출 잘한 점 (단일 원천). source enum 은 D-06 의 3가지 측정 근거.
export interface SummaryPraiseInput {
  source: 'mission_improved' | 'clean_dimension' | 'criteria_met';
  headline: string;
  evidenceValue?: number | null;
  evidenceUnit?: string | null;
}

// 지난 미션의 수치 outcome (mode3 전용, D-26).
export interface MissionOutcomeInput {
  improved: boolean;
  deltaPoints?: number | null;
  criterion?: string | null;
}

// 이번 회차 선정 미션 (오늘 고칠 것의 원천).
export interface MissionInput {
  criterion: string;
  recordId?: string | null;
  isSafety?: boolean;
}

// 차원별 측정 신호 — 칭찬 적격 판정용. score=null 은 미측정(칭찬 부적격).
export interface DimensionSignal {
  key: string;
  score: number | null;
  hasDeduction: boolean;
  metCriteria?: boolean; // 측정값이 규칙 허용 내(caller/32-09 가 실존 규칙에서 판정)
}

// 감점 record (오늘 고칠 것·다음 행동 문구의 원천). 문구는 32-05 phrasebook 산출.
export interface DeductionRecordInput {
  criterion: string;
  points: number; // signed negative
  recordId?: string | null;
  statusLine?: string | null; // 상태 (몸 말) — 오늘 고칠 것 헤드라인
  cueLine?: string | null; // 행동 큐 (외부 초점) — 다음 행동 1순위
  exerciseReason?: string | null; // 보완 운동 이유 — 다음 행동 2순위
  coachQuestion?: string | null; // 코치 질문 완성문 — 다음 행동 3순위 후보
}

export interface SummaryInput {
  mode: SummaryMode;
  summaryPraise?: SummaryPraiseInput | null;
  spotCheckPraiseMismatch?: boolean; // 32-13 스팟체크 불일치 → doc praise 강등
  missionOutcome?: MissionOutcomeInput | null;
  mission?: MissionInput | null;
  dimensionScores?: DimensionSignal[];
  coverageGaps?: string[]; // 측정 못한 차원 key (칭찬 부적격 가드)
  deductionRecords?: DeductionRecordInput[];
  safetyFlagCount?: number;
}

// ── 출력 ──────────────────────────────────────────────────────────────────

export interface SummaryPraiseResult {
  source: 'mission_improved' | 'clean_dimension' | 'criteria_met';
  headline: string;
  evidenceValue?: number | null;
  evidenceUnit?: string | null;
}

export interface SummaryTodayFix {
  headline: string;
  criterion: string;
  recordId?: string | null;
  gameFrame: boolean; // 안전 결함이면 false (게임 프레임 금지, D-14)
}

export interface SummaryNextAction {
  text: string;
}

export interface SummaryContent {
  praise: SummaryPraiseResult | null;
  todayFix: SummaryTodayFix | null;
  nextAction: SummaryNextAction | null;
}

// ── 카피 상수 (수치 미포함 — D-09. 변경 시 32-07 D-06 취지 유지) ──────────────

// 로컬 폴백 잘한 점 헤드라인 — 사람 말·응원 톤, 수치 0. 구체 관절/차원 문구는
// 백엔드 summaryPraise(phrasebook) 소관이라 폴백은 일반적이되 정직한 문장만 쓴다.
const PRAISE_HEADLINE: Record<SummaryPraiseResult['source'], string> = {
  mission_improved: '지난번보다 확실히 나아졌어요',
  clean_dimension: '이 부분은 기준에 맞게 잘 해냈어요',
  criteria_met: '측정된 자세에서 기본 기준은 지켰어요',
};

// 오늘 고칠 것 헤드라인 폴백 (매칭 record statusLine 부재 시 — fabrication 금지 최소문).
const TODAY_FIX_GENERIC = '오늘은 이 부분에 집중해봐요';

// 다음 행동 3순위 — cue·운동 이유 모두 부재(fail-closed)일 때 코치 질문 유도.
const NEXT_ACTION_COACH_PROMPT = '어떻게 연습할지 막히면 강사님께 여쭤보세요';

// ── 선정 로직 ────────────────────────────────────────────────────────────

// 잘한 점: doc 우선 → 스팟체크 불일치 시 강등 → 로컬 폴백 체인(개선→clean→충족→null).
function selectPraise(input: SummaryInput): SummaryPraiseResult | null {
  const doc = input.summaryPraise;
  // (1) 단일 원천 — doc summaryPraise 를 그대로 채택 (스팟체크 불일치 아닐 때만).
  if (doc && input.spotCheckPraiseMismatch !== true) {
    return {
      source: doc.source,
      headline: doc.headline,
      evidenceValue: doc.evidenceValue ?? null,
      evidenceUnit: doc.evidenceUnit ?? null,
    };
  }

  // (2) 로컬 폴백 체인 (legacy doc 또는 강등).
  // 2-1. mission_improved — D-26 1순위 (mode3 지난 미션 개선).
  const mo = input.missionOutcome;
  if (mo && mo.improved === true) {
    const delta =
      typeof mo.deltaPoints === 'number' && mo.deltaPoints > 0 ? mo.deltaPoints : null;
    return {
      source: 'mission_improved',
      headline: PRAISE_HEADLINE.mission_improved,
      evidenceValue: delta, // 수치는 구조 필드로만 (D-09)
      evidenceUnit: delta != null ? '점' : null,
    };
  }

  // 측정 존재 + 커버리지 갭 아님 차원만 칭찬 적격 (안 잰 것 칭찬 금지 — 리뷰 반영).
  const gaps = new Set(input.coverageGaps ?? []);
  const eligible = (input.dimensionScores ?? []).filter(
    (d) => d.score != null && !gaps.has(d.key),
  );

  // 2-2. clean_dimension — 감점 0 차원.
  if (eligible.some((d) => !d.hasDeduction)) {
    return {
      source: 'clean_dimension',
      headline: PRAISE_HEADLINE.clean_dimension,
      evidenceValue: null,
      evidenceUnit: null,
    };
  }

  // 2-3. criteria_met — 측정값이 규칙 허용 내(완전 clean 은 아님).
  if (eligible.some((d) => d.metCriteria === true)) {
    return {
      source: 'criteria_met',
      headline: PRAISE_HEADLINE.criteria_met,
      evidenceValue: null,
      evidenceUnit: null,
    };
  }

  // 2-4. 근거 없음 → null (정직 고지·시선 유도는 렌더 소관, D-06).
  return null;
}

// todayFix 원천 record 찾기 (recordId 우선, 없으면 criterion 매칭).
function findRecord(
  records: DeductionRecordInput[],
  recordId: string | null | undefined,
  criterion: string,
): DeductionRecordInput | undefined {
  if (recordId != null) {
    const byId = records.find((r) => r.recordId === recordId);
    if (byId) return byId;
  }
  return records.find((r) => r.criterion === criterion);
}

// 오늘 고칠 것: mission 있으면 mission 기반, 없으면 최대 감점 record.
function selectTodayFix(input: SummaryInput): SummaryTodayFix | null {
  const records = input.deductionRecords ?? [];
  const mission = input.mission;

  if (mission) {
    const rec = findRecord(records, mission.recordId, mission.criterion);
    return {
      headline: rec?.statusLine ?? TODAY_FIX_GENERIC,
      criterion: mission.criterion,
      recordId: mission.recordId ?? rec?.recordId ?? null,
      gameFrame: mission.isSafety !== true, // 안전 결함 = 게임 프레임 금지 (D-14)
    };
  }

  if (records.length > 0) {
    // 최대 감점 = points 가 가장 음수 (원본 불변 — 복제 후 정렬).
    const top = [...records].sort((a, b) => a.points - b.points)[0];
    return {
      headline: top.statusLine ?? TODAY_FIX_GENERIC,
      criterion: top.criterion,
      recordId: top.recordId ?? null,
      gameFrame: true,
    };
  }

  return null;
}

// 다음 행동: 오늘 고칠 것 원천 record 의 cueLine → 운동 이유 → 코치 질문 유도.
function selectNextAction(
  input: SummaryInput,
  todayFix: SummaryTodayFix | null,
): SummaryNextAction | null {
  if (!todayFix) return null;
  const records = input.deductionRecords ?? [];
  const rec = findRecord(records, todayFix.recordId, todayFix.criterion);
  if (rec) {
    if (rec.cueLine) return { text: rec.cueLine }; // 1순위 — 행동 큐(외부 초점)
    if (rec.exerciseReason) return { text: rec.exerciseReason }; // 2순위 — 보완 운동 이유
    if (rec.coachQuestion) return { text: rec.coachQuestion }; // 3순위 — 코치 질문 완성문
  }
  return { text: NEXT_ACTION_COACH_PROMPT }; // fail-closed — 코치 질문 유도 문구
}

// 요약 카드 3요소 선정. 렌더/수치 노출 여부는 소비 컴포넌트(SummaryCard) 소관.
export function deriveSummaryContent(input: SummaryInput): SummaryContent {
  const todayFix = selectTodayFix(input);
  return {
    praise: selectPraise(input),
    todayFix,
    nextAction: selectNextAction(input, todayFix),
  };
}
