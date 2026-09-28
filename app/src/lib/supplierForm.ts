// 공급자 올리기 폼 순수 규칙 — 필수 개수 · 파일 검증 · 동의 · 요청 조립 · 프리필
// (Phase 38 리뷰 R14, UI-SPEC A-4 STEP 01/02 · 검증 다이얼로그, D-07 · D-08 · D-14).
//
// 두 호스팅 후보(38-10/38-11 Expo 라우트 · 38-12 단일 HTML)가 import 만 한다 — 화면 파일에
// 규칙을 다시 쓰지 않는다. 순수: firebase / react / expo import 0, 값 import 0(타입만),
// node --test 로 fixture 한 벌(supplierFixtures.ts)에 대해 검증된다.
//
// 이 검사는 UX 용(위협 T-38-03-3) — 진짜 상한은 서버 validation.validate_reference_upload_request
// (38-01) + 파이프라인 head_object/probe(38-07). 상수는 models.py 와 lockstep(아래 주석,
// supplierForm.test.ts 가 models.py 텍스트를 대조한다).

import type {
  ReferenceUploadUrlRequest,
  SkillLevel,
  VideoFormat,
} from '../types/analysis.ts';

// lockstep: models.py REFERENCE_MIN_DURATION_SEC / REFERENCE_MAX_DURATION_SEC /
// REFERENCE_COMBO_MAX_DURATION_SEC / MAX_VIDEO_BYTES / REFERENCE_NAME_MAX_LEN (38-01).
export const REFERENCE_MIN_DURATION_SEC = 5;
export const REFERENCE_MAX_DURATION_SEC = 30;
export const REFERENCE_COMBO_MAX_DURATION_SEC = 60;
export const MAX_VIDEO_BYTES = 100 * 1024 * 1024; // = analyze.tsx MAX_BYTES (design.md 100MB)
export const REFERENCE_NAME_MAX_LEN = 30;
// STEP 01 필수 8 = 체크 확인 · 동작 이름 · 선수 이름 · 레벨 · 선언 3(스플릿·유지·서 있는 시작) · 파일
export const REQUIRED_FIELD_COUNT = 8;

const FORMATS: readonly VideoFormat[] = ['mp4', 'mov'];
const LEVELS: readonly SkillLevel[] = ['basic', 'intermediate', 'advanced']; // = REFERENCE_LEVELS

export type YesNo = 'yes' | 'no';

// 동작 이름 — 사전(GET /reference 활성 동작)에서 고르면 dict + motionId(등록 정보로만 보관,
// 리뷰 R7), 새 이름이면 new.
export type NameChoice =
  | { kind: 'dict'; motionId: string; name: string }
  | { kind: 'new'; name: string };

// 선택한 파일 메타. 업로드 본체(Expo 는 file URI, 웹은 File/Blob)는 규칙 층이 안 만진다.
export interface FormFile {
  name: string;
  sizeBytes: number;
  durationSec: number | null; // <video> metadata 를 못 읽으면 null (fail-open, RESEARCH A12)
  format: VideoFormat;
  uri?: string;
  blob?: unknown;
}

export interface Step1State {
  checkConfirmed: boolean;
  nameChoice: NameChoice | null;
  athleteName: string;
  level: SkillLevel | null;
  isCombo: boolean;
  isSplit: YesNo | null;
  hasHold: YesNo | null;
  standingStart: YesNo | null;
  file: FormFile | null;
}

// STEP 02 — 필수 3(portrait·usage·silent) + training(선택, 기본 꺼짐, D-08).
export interface ConsentState {
  portrait: boolean;
  usage: boolean;
  silent: boolean;
  training: boolean;
}

// 검증 다이얼로그 kind(supplierCopy.dialog 의 키와 같다; unreadable 은 metadata 읽기 실패라
// 화면이 따로 낸다).
export type FileFailureKind = 'format' | 'tooLarge' | 'tooShort' | 'tooLong';

export function emptyStep1(): Step1State {
  return {
    checkConfirmed: false,
    nameChoice: null,
    athleteName: '',
    level: null,
    isCombo: false,
    isSplit: null,
    hasHold: null,
    standingStart: null,
    file: null,
  };
}

function trimmedName(choice: NameChoice | null): string {
  return choice ? choice.name.trim() : '';
}

function isNameFilled(choice: NameChoice | null): boolean {
  const n = trimmedName(choice);
  return n.length > 0 && n.length <= REFERENCE_NAME_MAX_LEN;
}

// 남은 필수 개수(`필수 항목 {n}개가 남았어요`, 비활성 CTA 의 이유) + 서 있는 시작 '아니오'
// 차단(D-09 사전 차단 — 개수와 별개, 화면은 form.sec3.stand.blocked 를 띄운다).
export function remainingRequired(s: Step1State): { count: number; blocked: boolean } {
  const filled = [
    s.checkConfirmed,
    isNameFilled(s.nameChoice),
    s.athleteName.trim().length > 0,
    s.level !== null,
    s.isSplit !== null,
    s.hasHold !== null,
    s.standingStart !== null,
    s.file !== null,
  ];
  const count = filled.filter((f) => !f).length;
  return { count, blocked: s.standingStart === 'no' };
}

// 파일명 확장자 → VideoFormat. mp4/mov 밖(확장자 없음 포함)은 null.
export function formatOf(name: string): VideoFormat | null {
  const dot = name.lastIndexOf('.');
  if (dot < 0) return null;
  const ext = name.slice(dot + 1).toLowerCase();
  return (FORMATS as readonly string[]).includes(ext) ? (ext as VideoFormat) : null;
}

// 형식 → 용량 → 길이 순서(analyze.tsx validate 와 같은 규율 — 종류만 돌려주고 문구는
// supplierCopy.dialog). 길이는 값이 유한할 때만 본다 — null/NaN 은 "모른다" 라 통과(fail-open).
export function validateFile(input: {
  name: string;
  sizeBytes: number;
  durationSec: number | null;
  isCombo: boolean;
}): FileFailureKind | null {
  if (formatOf(input.name) === null) return 'format';
  if (input.sizeBytes > MAX_VIDEO_BYTES) return 'tooLarge';
  const d = input.durationSec;
  if (d == null || !Number.isFinite(d)) return null;
  if (d < REFERENCE_MIN_DURATION_SEC) return 'tooShort';
  const max = input.isCombo ? REFERENCE_COMBO_MAX_DURATION_SEC : REFERENCE_MAX_DURATION_SEC;
  if (d > max) return 'tooLong';
  return null;
}

// 전체 동의 = 필수 3 만(D-08 학습 사용은 별도·기본 꺼짐, UI-SPEC Decisions 14).
export function consentAllRequired(c: ConsentState): boolean {
  return c.portrait && c.usage && c.silent;
}

// POST /reference/upload-url 요청 조립 — ReferenceUploadUrlRequest 정확한 형상(uid/refId 없음,
// clipRange 없음 — 폼은 구간을 받지 않는다 D-06). 아직 보낼 수 없는 상태(필수 미완·서 있는
// 시작 아니오·필수 동의 미완)면 null — 화면이 CTA 를 비활성으로 두는 조건과 같은 규칙.
export function buildRequest(
  step1: Step1State,
  consent: ConsentState,
  file: FormFile,
): ReferenceUploadUrlRequest | null {
  const { count, blocked } = remainingRequired({ ...step1, file });
  if (count > 0 || blocked) return null;
  if (!consentAllRequired(consent)) return null;
  if (!step1.nameChoice || !step1.level) return null;
  const d = file.durationSec;
  return {
    name: trimmedName(step1.nameChoice),
    athleteName: step1.athleteName.trim(),
    level: step1.level,
    techniqueRefId: step1.nameChoice.kind === 'dict' ? step1.nameChoice.motionId : null,
    isCombo: step1.isCombo,
    isSplit: step1.isSplit === 'yes',
    hasHold: step1.hasHold === 'yes',
    standingStart: step1.standingStart === 'yes',
    consent: {
      portrait: consent.portrait,
      usage: consent.usage,
      silent: consent.silent,
      training: consent.training,
    },
    format: file.format,
    fileSizeBytes: file.sizeBytes,
    durationSec: d != null && Number.isFinite(d) ? d : null,
  };
}

// ── 다시 올리기 프리필 (A-3b/만료 패널 → A-4). 라우트 params / URL query 는 문자열이라
// yes/no 는 '1'|'0' 으로 나른다. 인코더·디코더가 한 파일에 있어 두 트랙이 같은 규칙을 쓴다.

export interface PrefillInput {
  name: string;
  athleteName: string;
  level: SkillLevel;
  techniqueRefId?: string | null;
  isCombo: boolean;
  isSplit: boolean;
  hasHold: boolean;
  standingStart: boolean;
}

export function toPrefillParams(input: PrefillInput): Record<string, string> {
  const params: Record<string, string> = {
    name: input.name,
    athleteName: input.athleteName,
    level: input.level,
    isCombo: input.isCombo ? '1' : '0',
    isSplit: input.isSplit ? '1' : '0',
    hasHold: input.hasHold ? '1' : '0',
    standingStart: input.standingStart ? '1' : '0',
  };
  if (input.techniqueRefId) params.techniqueRefId = input.techniqueRefId;
  return params;
}

function paramString(params: Record<string, unknown>, key: string): string {
  const v = params[key];
  if (typeof v === 'string') return v;
  // expo-router useLocalSearchParams 는 같은 키가 겹치면 string[] 을 준다 — 첫 값만.
  if (Array.isArray(v) && typeof v[0] === 'string') return v[0];
  return '';
}

function paramYesNo(params: Record<string, unknown>, key: string): YesNo | null {
  const v = paramString(params, key);
  if (v === '1') return 'yes';
  if (v === '0') return 'no';
  return null;
}

// params → STEP 01 상태. 체크 확인·파일은 항상 비운다(다시 올리는 사람이 다시 확인·선택).
// 쓰레기 값(레벨 밖·'1'/'0' 밖·빈 이름)은 null — 화면이 그 칸을 다시 묻는다.
export function parsePrefill(params: Record<string, unknown>): Step1State {
  const name = paramString(params, 'name').trim();
  const techniqueRefId = paramString(params, 'techniqueRefId').trim();
  const level = paramString(params, 'level');
  let nameChoice: NameChoice | null = null;
  if (name) {
    nameChoice = techniqueRefId
      ? { kind: 'dict', motionId: techniqueRefId, name }
      : { kind: 'new', name };
  }
  return {
    ...emptyStep1(),
    nameChoice,
    athleteName: paramString(params, 'athleteName').trim(),
    level: (LEVELS as readonly string[]).includes(level) ? (level as SkillLevel) : null,
    isCombo: paramString(params, 'isCombo') === '1',
    isSplit: paramYesNo(params, 'isSplit'),
    hasHold: paramYesNo(params, 'hasHold'),
    standingStart: paramYesNo(params, 'standingStart'),
  };
}
