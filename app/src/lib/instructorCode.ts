// 마이 탭 강사 코드 — 순수 규칙 (quick-260930-o0u, 38-DESIGN-v2 §W2 · 38-SCENARIOS R2~R7).
//
// firebase · react-native 를 import 하지 않는다(supplierRules.ts 선례 — node --test 로 잠근다).
// Firestore 입출력은 instructorLink.ts, 화면은 components/InstructorCodeSheet.tsx.
//
// firestore.rules isValidInstructorLink 와 같은 규칙을 앱 쪽에서 먼저 거른다 — 오류 문구를
// 빨리 보여 주려는 것이고, 최종 판정은 규칙이다(앱이 통과시켜도 규칙이 막으면 막힌다).
//
// 플래너 결정:
//   (c) 연결 쓰기는 트랜잭션 — 이 파일의 sheetReducer 가 그 결과를 화면 상태로 옮긴다.
//   (d) displayName 이 없는 코드(BELLE)는 코드를 이름 자리에 쓴다 → instructorName.
//   (e) 조회 전 형식 검사 ^[A-Z0-9]{3,8}$ — 형식 밖이면 네트워크 없이 "없는 코드".

// backend models.SUPPLIER_CODES_COLLECTION / INSTRUCTOR_LINKS_COLLECTION 미러.
export const SUPPLIER_CODES_COLLECTION = 'supplierCodes';
export const INSTRUCTOR_LINKS_COLLECTION = 'instructorLinks';
// backend models.SUPPLIER_CODE_RE 미러(옛 규칙 — BELLE 의 L 을 받아야 한다) = 규칙 matches 와 같다.
export const INSTRUCTOR_CODE_RE = /^[A-Z0-9]{3,8}$/;

export function normalizeInstructorCode(raw: string): string {
  return raw.replace(/\s+/g, '').toUpperCase();
}

export type LookupPlan = { kind: 'invalid' } | { kind: 'fetch'; code: string };

export function planLookup(raw: string): LookupPlan {
  const code = normalizeInstructorCode(raw);
  return INSTRUCTOR_CODE_RE.test(code) ? { kind: 'fetch', code } : { kind: 'invalid' };
}

export type FoundCode = { code: string; supplierUid: string; displayName: string | null };

export type CodeClass =
  | { kind: 'notFound' }
  | { kind: 'self' }
  | { kind: 'found'; supplierUid: string; displayName: string | null };

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

function nonEmptyString(v: unknown): string | null {
  return typeof v === 'string' && v.trim() !== '' ? v : null;
}

// 순서: 없음 · active 가 true 가 아님 · supplierUid 없음 → notFound(비활성 코드는 본인 것이어도
// "없는 코드" — 회수된 코드의 존재를 알리지 않는다). 그다음 본인 코드 → self(SCENARIOS R5).
export function classifyCodeDoc(raw: unknown, authUid: string | null): CodeClass {
  if (!isRecord(raw) || raw.active !== true) return { kind: 'notFound' };
  const supplierUid = nonEmptyString(raw.supplierUid);
  if (supplierUid === null) return { kind: 'notFound' };
  if (authUid !== null && supplierUid === authUid) return { kind: 'self' };
  return { kind: 'found', supplierUid, displayName: nonEmptyString(raw.displayName) };
}

export type InstructorLink = {
  code: string;
  supplierUid: string;
  displayName: string | null;
  linkedAtMs: number | null;
};

function toMillis(v: unknown): number | null {
  if (!isRecord(v)) return null;
  if (typeof v.toMillis === 'function') {
    const ms = (v.toMillis as () => unknown)();
    return typeof ms === 'number' && Number.isFinite(ms) ? ms : null;
  }
  if (typeof v.seconds === 'number' && Number.isFinite(v.seconds)) {
    const ns = typeof v.nanoseconds === 'number' && Number.isFinite(v.nanoseconds) ? v.nanoseconds : 0;
    return v.seconds * 1000 + Math.floor(ns / 1e6);
  }
  return null;
}

// Firestore doc → InstructorLink. 던지지 않는다 — 모양이 틀리면 null(userAnalyses.normalize 규율).
export function normalizeInstructorLink(raw: unknown): InstructorLink | null {
  if (!isRecord(raw)) return null;
  const code = typeof raw.code === 'string' ? raw.code : null;
  if (code === null || !INSTRUCTOR_CODE_RE.test(code)) return null;
  const supplierUid = nonEmptyString(raw.supplierUid);
  if (supplierUid === null) return null;
  return {
    code,
    supplierUid,
    displayName: nonEmptyString(raw.displayName),
    linkedAtMs: toMillis(raw.linkedAt),
  };
}

// 화면에 쓰는 강사 이름 — 비면 코드(플래너 결정 (d)).
export function instructorName(displayName: string | null | undefined, code: string): string {
  const name = typeof displayName === 'string' ? displayName.trim() : '';
  return name !== '' ? name : code;
}

export type FirestoreFailure = 'offline' | 'denied' | 'failed';

export function mapFirestoreErrorCode(code?: string): FirestoreFailure {
  if (code === 'unavailable' || code === 'deadline-exceeded') return 'offline';
  if (code === 'permission-denied') return 'denied';
  return 'failed';
}

// ── 입력 시트 상태 ──
// 입력 단계 → (확인 누름) 조회 → 맞으면 같은 시트가 강사 확인 단계 → (연결하기) 트랜잭션.

export type InputError = 'notFound' | 'selfCode' | 'offline' | 'failed';

export type SheetState =
  | { step: 'input'; value: string; error: InputError | null; busy: boolean }
  | {
      step: 'confirm';
      value: string;
      found: FoundCode;
      error: 'offline' | 'failed' | null;
      busy: boolean;
    };

export type LookupResult =
  | ({ kind: 'found' } & FoundCode)
  | { kind: 'notFound' }
  | { kind: 'self' }
  | { kind: 'offline' }
  | { kind: 'failed' };

export type SheetAction =
  | { type: 'edit'; value: string }
  | { type: 'lookupStart' }
  | { type: 'lookupDone'; result: LookupResult }
  | { type: 'cancel' }
  | { type: 'linkStart' }
  | { type: 'linkFailed'; reason: 'offline' | 'failed' }
  | { type: 'linkDenied' }
  | { type: 'reset' };

export const INITIAL_SHEET_STATE: SheetState = { step: 'input', value: '', error: null, busy: false };

const LOOKUP_ERROR: Record<Exclude<LookupResult['kind'], 'found'>, InputError> = {
  notFound: 'notFound',
  self: 'selfCode',
  offline: 'offline',
  failed: 'failed',
};

// 맞지 않는 단계의 액션은 상태를 그대로 돌려준다(같은 객체 — 리렌더 없음).
export function sheetReducer(state: SheetState, action: SheetAction): SheetState {
  if (action.type === 'reset') return INITIAL_SHEET_STATE;
  if (state.step === 'input') {
    switch (action.type) {
      case 'edit':
        return state.busy ? state : { step: 'input', value: action.value, error: null, busy: false };
      case 'lookupStart':
        return { ...state, error: null, busy: true };
      case 'lookupDone': {
        const r = action.result;
        if (r.kind === 'found') {
          return {
            step: 'confirm',
            value: state.value,
            found: { code: r.code, supplierUid: r.supplierUid, displayName: r.displayName },
            error: null,
            busy: false,
          };
        }
        return { step: 'input', value: state.value, error: LOOKUP_ERROR[r.kind], busy: false };
      }
      default:
        return state;
    }
  }
  switch (action.type) {
    case 'cancel':
      return state.busy ? state : { step: 'input', value: state.value, error: null, busy: false };
    case 'linkStart':
      return { ...state, error: null, busy: true };
    case 'linkFailed':
      return { ...state, error: action.reason, busy: false };
    case 'linkDenied':
      // 그 사이 코드가 비활성화됐거나 규칙이 막았다 — 입력 단계로 돌려 "없는 코드".
      return { step: 'input', value: state.value, error: 'notFound', busy: false };
    default:
      return state;
  }
}

export function canSubmit(state: SheetState): boolean {
  return state.step === 'input' && !state.busy && normalizeInstructorCode(state.value) !== '';
}
