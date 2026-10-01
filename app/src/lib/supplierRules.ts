// 공급자 페이지 순수 규칙 — 행 상태 · 자기 점수 분기 · 실패 문구 · presign 오류 매핑 ·
// 업로드 결과 전이 (Phase 38 리뷰 R14, UI-SPEC A-3 · A-3b · A-3c · A-5 · A-7).
//
// 두 호스팅 후보(38-10/38-11 Expo 라우트 · 38-12 단일 HTML)가 이 함수들을 import 만 한다 —
// 화면 파일에 규칙을 다시 쓰지 않는다. 그래서 순수: firebase / react / expo import 0,
// node --test 로 fixture 한 벌(supplierFixtures.ts)에 대해 검증된다.
// 값 import 는 supplierCopy 하나, 타입은 전부 `import type` — 38-12 의 type-strip → ESM 변환이
// 값 import 만 남기고 specifier 를 './copy.js' 로 바꾸는 전제(플랜 38-03 T3).
//
// 문자열은 전부 supplierCopy 참조 + String.replace(`{score}` `{joints}` `{reason}`) — HTML/JSX 로 해석하지
// 않는다(위협 T-38-03-2). 소비처(38-10/38-12)는 textContent / <Text> 로만 그린다.

import type {
  ReferenceRegistrationError,
  ReferenceRegistrationErrorCode,
  ReferenceRegistrationStatus,
  SelfCheckStatus,
  SkillLevel,
} from '../types/analysis.ts';
import { supplierCopy } from '../constants/supplierCopy.ts';

// 자기 재현성 문구 분기점(D-10). [ASSUMED RESEARCH A9 · 38-04 결정 절 selfScoreMin 이 바꾼다]
// 문구 분기점일 뿐, 목표 숫자 금지(메모리 chasing-the-number) — pass/fail 판정에 쓰지 않는다.
// 다른 파일에 이 숫자 리터럴을 두지 않는다. belle 이 다른 값을 주면 이 한 줄만 바뀐다.
export const SELF_SCORE_OK_MIN = 90;

// 레벨 라벨 — 앱 picker 탭(reference.tsx TABS)과 같은 문자열, 출처는 supplierCopy 하나.
export const LEVEL_LABEL_KO: Record<SkillLevel, string> =
  supplierCopy.form.sec2.level.options;

const REGISTRATION_STATUSES: readonly ReferenceRegistrationStatus[] = [
  'registering',
  'queued',
  'processing',
  'failed',
  'active',
  'expired',
  'review',
];
const SELF_CHECK_STATUSES: readonly SelfCheckStatus[] = ['pending', 'queued', 'done', 'failed'];
const FAIL_CODES = Object.keys(supplierCopy.row.fail) as ReferenceRegistrationErrorCode[];

// 공개 doc `reference/{refId}` 에서 페이지 목록·상세가 쓰는 필드만(공개 doc 은 인증자 전체가
// 읽는다 — 동의·실패 상세는 SupplierMotionPrivate, 리뷰 R13).
export interface SupplierMotion {
  motionId: string;
  name: string;
  athleteName: string;
  level: SkillLevel;
  isActive: boolean;
  registrationStatus: ReferenceRegistrationStatus;
  queuedReason: string | null;
  selfScore: number | null;
  selfCheckStatus: SelfCheckStatus | null;
  createdAt: number; // epoch ms, 없으면 0(목록 맨 뒤)
  videoS3Key: string | null;
  uploadExpiresAt: number | null;
  // quick-260930-w9l — Pod 등록이 만든 썸네일 키. 화면은 이 키로 POST /playback-url asset
  // 'thumbnail' 을 부른다(referenceThumbs.ts). 없으면 아이콘 자리.
  thumbnailS3Key: string | null;
}

// 비공개 doc `reference/{refId}/private/registration` — 상세 패널·다시 올리기 프리필 전용.
// 옛 선언 4(isCombo·isSplit·hasHold·standingStart)는 읽지 않는다 — 폼에서 지웠고 소비처가 없다(w9l).
export interface SupplierMotionPrivate {
  registrationError: ReferenceRegistrationError | null;
  techniqueRefId: string | null;
}

// notInvited = 403(quick-260930-lfw not_invited — 옛 서버의 forbidden 도 상태코드로 같이 받는다).
export type PresignFailureKind = 'sessionExpired' | 'notInvited' | 'offline' | 'presignFail';
export type UploadOutcome = 'ok' | 'aborted' | 'failed';
export type UploadNext = 'home' | 'step2' | 'failPanel';

function str(v: unknown): string | null {
  return typeof v === 'string' && v.length > 0 ? v : null;
}

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

function isLevel(v: unknown): v is SkillLevel {
  return typeof v === 'string' && v in LEVEL_LABEL_KO;
}

function isRegistrationStatus(v: unknown): v is ReferenceRegistrationStatus {
  return typeof v === 'string' && (REGISTRATION_STATUSES as readonly string[]).includes(v);
}

function isSelfCheckStatus(v: unknown): v is SelfCheckStatus {
  return typeof v === 'string' && (SELF_CHECK_STATUSES as readonly string[]).includes(v);
}

export function isRegistrationErrorCode(v: unknown): v is ReferenceRegistrationErrorCode {
  return typeof v === 'string' && (FAIL_CODES as readonly string[]).includes(v);
}

// Firestore 공개 doc → SupplierMotion. referenceMotions.normalize 와 같은 방어 어법 —
// 필수 4(supplierUid·name·athleteName·level)가 없으면 null(손 등록 seed 11개는 supplierUid 가
// 없어 여기서 걸러진다). 상태가 없거나 미지 값이면 'registering'(선작성 직후 모양).
export function normalizeRegistration(
  motionId: string,
  raw: Record<string, unknown>,
): SupplierMotion | null {
  const supplierUid = str(raw.supplierUid);
  const name = str(raw.name);
  const athleteName = str(raw.athleteName);
  if (!supplierUid || !name || !athleteName || !isLevel(raw.level)) return null;
  return {
    motionId,
    name,
    athleteName,
    level: raw.level,
    // 등록 doc 은 38-06 이 false 로 선작성하고 승인(active) 때 true — review 는 false. 명시된 true 만 참.
    isActive: raw.isActive === true,
    registrationStatus: isRegistrationStatus(raw.registrationStatus)
      ? raw.registrationStatus
      : 'registering',
    queuedReason: str(raw.queuedReason),
    selfScore: num(raw.selfScore),
    selfCheckStatus: isSelfCheckStatus(raw.selfCheckStatus) ? raw.selfCheckStatus : null,
    createdAt: num(raw.createdAt) ?? 0,
    videoS3Key: str(raw.videoS3Key),
    uploadExpiresAt: num(raw.uploadExpiresAt),
    thumbnailS3Key: str(raw.thumbnailS3Key),
  };
}

// 비공개 doc → SupplierMotionPrivate. 서버가 이 phase 뒤에 새 실패 코드를 붙이면 페이지는
// 아직 모르는 코드라 server_error 문구로 받는다(message 는 서버 원문 그대로 보존).
export function normalizePrivate(raw: unknown): SupplierMotionPrivate | null {
  if (!raw || typeof raw !== 'object') return null;
  const r = raw as Record<string, unknown>;
  let registrationError: ReferenceRegistrationError | null = null;
  const e = r.registrationError;
  if (e && typeof e === 'object') {
    const er = e as Record<string, unknown>;
    const joints = Array.isArray(er.joints)
      ? er.joints.filter((j): j is string => typeof j === 'string')
      : null;
    // quick-261001-thx — 반려 사유(운영자 원문). 문자열이 아니면 버린다.
    const reason = str(er.reason);
    registrationError = {
      code: isRegistrationErrorCode(er.code) ? er.code : 'server_error',
      message: str(er.message) ?? '',
      ...(joints ? { joints } : {}),
      ...(reason ? { reason } : {}),
    };
  }
  return {
    registrationError,
    techniqueRefId: str(r.techniqueRefId),
  };
}

// 자기 재현성 표시값 — selfCheck 가 끝났고(done, 또는 상태 없이 점수만 있는 옛 doc) 점수가
// 있을 때 반올림한 정수. 문턱 비교도 이 값으로 한다 — 화면에 90 이라 쓰고 '낮아요' 라고
// 하지 않게(표시와 분기가 같은 숫자).
function doneScore(m: SupplierMotion): number | null {
  if (m.selfScore == null) return null;
  if (m.selfCheckStatus !== 'done' && m.selfCheckStatus !== null) return null;
  return Math.round(m.selfScore);
}

function withScore(template: string, score: number): string {
  return template.replace('{score}', String(score));
}

function assertNever(x: never): never {
  throw new Error(`unreachable: ${String(x)}`);
}

// A-3 행 부제의 상태어(UI-SPEC A-3 상태 표 8행). active 는 자기 점수로 3분기 —
// 점수 없음(pending/queued/failed selfCheck)은 Figma `새로 추가됨`; selfCheck failed 의 사연은
// 상세 패널의 selfCheckView 가 말한다.
// quick-261001-thx(belle "아주 심플하게"): 승인 전 네 상태(registering · queued · processing · review)는
// 한 문구 `checking`. 운영자가 승인 뒤 내린(isActive false) doc 은 registrationStatus 가 active 그대로라
// 승인 뒤 문구를 그대로 쓴다(새 공급자 문구를 만들지 않는다 — 운영 예외 경로).
export function rowStatusWord(m: SupplierMotion): string {
  const s = supplierCopy.row.status;
  switch (m.registrationStatus) {
    case 'registering':
    case 'queued':
    case 'processing':
    case 'review':
      return s.checking;
    case 'failed':
      return s.failed;
    case 'expired':
      return s.expired;
    case 'active': {
      const score = doneScore(m);
      if (score == null) return s.newlyAdded;
      return withScore(score >= SELF_SCORE_OK_MIN ? s.self : s.selfLow, score);
    }
    default:
      return assertNever(m.registrationStatus);
  }
}

// 행 부제 = `{레벨} · {상태어}` (38-DESIGN A-3 행 부제, 색 없이 말로).
export function rowSubtitle(m: SupplierMotion): string {
  return `${LEVEL_LABEL_KO[m.level]} · ${rowStatusWord(m)}`;
}

// A-3c 재현성 카드(38-DESIGN A-3c) = 제목 + 오른쪽 `{score}점` + 본문. score 는 카드 오른쪽
// 한 자리에만 그린다 — 본문엔 숫자를 다시 쓰지 않는다(낮음이면 lowBody). ok 본문은 리뷰 R11
// 판(일관성 진단)이고 바로 아래 selfCheckNote() 가 항상 붙는다(D-11). done 인데 점수가 없으면
// 데이터 이상 → failed 문구(운영팀에 알려주세요).
// 표시와 분기가 같은 반올림 숫자 — 문턱 비교와 화면 `{score}점` 모두 doneScore 한 값이다.
export function selfCheckView(m: SupplierMotion): { score: number | null; body: string } {
  const c = supplierCopy.row.self;
  const score = doneScore(m);
  if (score != null) {
    return { score, body: score >= SELF_SCORE_OK_MIN ? c.okBody : c.lowBody };
  }
  if (m.selfCheckStatus === 'queued') return { score: null, body: c.queued };
  if (m.selfCheckStatus === 'failed' || m.selfCheckStatus === 'done') {
    return { score: null, body: c.failed };
  }
  return { score: null, body: c.pending };
}

export function selfCheckNote(): string {
  return supplierCopy.row.self.note;
}

// `{reason}` 이 든 문장(마침표까지)을 통째로 뺀다 — 사유 없는 rejected(데이터 이상)가 '사유: .' 로
// 보이지 않게. 문구 조각을 여기 다시 쓰지 않으려고 문장 단위로 지운다.
const REASON_SENTENCE = /[^.]*\{reason\}[^.]*\.\s*/;

// 실패 패널 문구(D-09 + R9). 미지 코드 → server_error. low_confidence 의 {joints} 는 부위명을
// ' · ' 로 잇는다(UI-SPEC §Copywriting) — 2026-10-01 이전 doc 의 registrationError.joints.
// rejected(quick-261001-thx) 의 {reason} 은 registrationError.reason(운영자 사유)으로 치환하고,
// 사유가 없거나 공백이면 그 문장을 뺀다.
export function failCopy(
  code: string,
  joints?: readonly string[],
  reason?: string,
): { title: string; body: string } {
  const key = isRegistrationErrorCode(code) ? code : 'server_error';
  const c = supplierCopy.row.fail[key];
  const joined = joints && joints.length > 0 ? joints.join(' · ') : '';
  const why = typeof reason === 'string' ? reason.trim() : '';
  const fill = (t: string): string => {
    const withJoints = t.replace('{joints}', joined);
    if (!withJoints.includes('{reason}')) return withJoints;
    return why ? withJoints.replace('{reason}', why) : withJoints.replace(REASON_SENTENCE, '');
  };
  return { title: fill(c.title), body: fill(c.body) };
}

// 만료 패널(리뷰 R4) — 코드 칩·TIP 없이 제목·본문 + 다시 올리기(같은 프리필).
export function expiredCopy(): { title: string; body: string } {
  return { title: supplierCopy.row.expired.title, body: supplierCopy.row.expired.body };
}

// 행 오른쪽 진행 점(38-DESIGN A-3) — 아직 끝나지 않은 상태. review(검수 중, quick-261001-thx)도
// 공급자에게는 기다리는 중이라 같은 점을 쓴다(상세 패널 없음).
export function isInProgress(m: SupplierMotion): boolean {
  const st = m.registrationStatus;
  return st === 'registering' || st === 'processing' || st === 'queued' || st === 'review';
}

// chevron → 상세 패널이 있는 상태(A-3 표): active(A-3c) · failed(A-3b) · expired(만료 패널).
// review 는 상세가 없다(검수 결과가 나면 active 또는 failed 로 바뀐다).
export function hasDetail(m: SupplierMotion): boolean {
  return (
    m.registrationStatus === 'active' ||
    m.registrationStatus === 'failed' ||
    m.registrationStatus === 'expired'
  );
}

// 목록 정렬 — 최신 등록 먼저(createdAt desc). 입력은 건드리지 않는다.
export function sortNewestFirst(list: readonly SupplierMotion[]): SupplierMotion[] {
  return [...list].sort((a, b) => b.createdAt - a.createdAt);
}

// POST /reference/upload-url 실패 → 화면 분기(UI-SPEC A-4 STEP 02 · A-7). 입력은 api.ts
// ApiError 의 {status, code}. status 0 = fetch 자체 실패(네트워크) — 단 api.ts 가 currentUser
// 없음을 status 0 + 'unauthenticated' 로 던지므로 그것만 세션 만료로 본다.
export function mapPresignFailure(failure: {
  status: number;
  code?: string | null;
}): PresignFailureKind {
  if (failure.status === 401) return 'sessionExpired';
  if (failure.status === 403) return 'notInvited';
  if (failure.status === 0) {
    return failure.code === 'unauthenticated' ? 'sessionExpired' : 'offline';
  }
  return 'presignFail';
}

// 분기별 문구(단일점). notInvited 는 문구가 아니라 A-2 화면 전환이라 null.
export function presignFailureMessage(kind: PresignFailureKind): string | null {
  switch (kind) {
    case 'sessionExpired':
      return supplierCopy.form.sessionExpired;
    case 'offline':
      return supplierCopy.common.offline;
    case 'presignFail':
      return supplierCopy.form.presignFail;
    case 'notInvited':
      return null;
    default:
      return assertNever(kind);
  }
}

// S3 PUT 결과 → 다음 화면(A-5). aborted(올리기 취소) = STEP 02 로 복귀·입력 유지,
// ok = A-3 + 토스트, failed = 실패 패널(다시 올리기 = 새 presign 부터). 두 트랙이 같은 표.
export function uploadOutcomeNext(outcome: UploadOutcome): UploadNext {
  switch (outcome) {
    case 'ok':
      return 'home';
    case 'aborted':
      return 'step2';
    case 'failed':
      return 'failPanel';
    default:
      return assertNever(outcome);
  }
}

// 크게 보기(38-DESIGN-v2 299:666) 코드 글자 크기 — 72pt 가 기본, 긴 코드(8자)가 좁은 폰(390 폭)에서
// 넘치지 않게 줄인다. 글자 폭 ≈ 0.78em(굵은 대문자 + 자간 8%). 하한 32pt.
export const BIG_CODE_MAX_PT = 72;
export const BIG_CODE_MIN_PT = 32;
export const BIG_CODE_CHAR_EM = 0.78;

export function bigCodeFontSize(codeLength: number, maxWidth: number): number {
  if (!(codeLength > 0)) return BIG_CODE_MAX_PT;
  const fit = Math.floor(maxWidth / (codeLength * BIG_CODE_CHAR_EM));
  return Math.min(BIG_CODE_MAX_PT, Math.max(BIG_CODE_MIN_PT, fit));
}
