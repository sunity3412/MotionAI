// 공급자 페이지 순수 규칙의 공용 fixture 1벌 (Phase 38 리뷰 R14).
//
// 두 호스팅 후보(38-10/38-11 Expo 라우트 · 38-12 단일 HTML)와 규칙 테스트 셋
// (supplierRules.test.ts · supplierForm.test.ts · 38-12 rules.test.mjs)이 **이 한 벌만** 입력으로
// 쓴다 — 테스트 안에 리터럴 doc 을 다시 쓰지 않는다. 값은 UI-SPEC A-3 상태 표와
// analysis.ts 계약 타입(ReferenceMotion `// register` 필드 · ReferenceRegistrationPrivate ·
// ReferenceUploadUrlRequest)에서 그대로 가져왔다.
//
// 순수 데이터 — import 0 (38-12 의 type-strip → ESM 변환이 그대로 먹는다).
// 시각은 상대 순서만 뜻이 있다(정렬 테스트). `expect` 필드는 그 행에 규칙이 내야 할 답.

const T0 = 1_790_000_000_000; // epoch ms — 2026-09 근처, 절대값은 뜻 없음
const UID = 'uid-eunji';
const UPLOAD_EXPIRES_MS = 900_000; // = models.py REFERENCE_UPLOAD_EXPIRES_SEC(900) * 1000

// 공개 doc 공통부(picker 필수 3 + 등록 출처). 각 상태는 이 위에 상태 필드만 얹는다.
const PUBLIC_BASE = {
  supplierUid: UID,
  athleteName: '정은지',
  source: 'supplier-link',
} as const;

const STEP1_COMPLETE = {
  checkConfirmed: true,
  nameChoice: { kind: 'dict', motionId: 'ref-kip-up', name: 'kip-up' },
  athleteName: '정은지',
  level: 'basic',
  isCombo: false,
  isSplit: 'yes',
  hasHold: 'no',
  standingStart: 'yes',
  file: { name: 'kipup.mp4', sizeBytes: 24_000_000, durationSec: 8.2, format: 'mp4' },
} as const;

const CONSENT_REQUIRED = { portrait: true, usage: true, silent: true, training: false } as const;
const CONSENT_WITH_TRAINING = { portrait: true, usage: true, silent: true, training: true } as const;

export const supplierFixtures = {
  supplierUid: UID,

  // ── 공개 doc `reference/{refId}` — A-3 상태 표의 행 하나씩 ─────────────────
  rawDocs: {
    registering: {
      ...PUBLIC_BASE,
      name: 'kip-up',
      level: 'basic',
      isActive: false,
      registrationStatus: 'registering',
      createdAt: T0 + 8_000,
      uploadKey: 'reference/uid-eunji/r-registering/upload.mp4',
      uploadExpiresAt: T0 + 8_000 + UPLOAD_EXPIRES_MS,
    },
    queued: {
      ...PUBLIC_BASE,
      name: 'power-spin',
      level: 'intermediate',
      isActive: false,
      registrationStatus: 'queued',
      queuedReason: 'pod_down',
      createdAt: T0 + 7_000,
      uploadKey: 'reference/uid-eunji/r-queued/upload.mp4',
      uploadExpiresAt: T0 + 7_000 + UPLOAD_EXPIRES_MS,
    },
    processing: {
      ...PUBLIC_BASE,
      name: 'climb',
      level: 'advanced',
      isActive: false,
      registrationStatus: 'processing',
      jobId: 'job-processing',
      leaseUntil: T0 + 6_000 + UPLOAD_EXPIRES_MS,
      createdAt: T0 + 6_000,
    },
    activePending: {
      ...PUBLIC_BASE,
      name: 'invert',
      level: 'intermediate',
      isActive: true,
      registrationStatus: 'active',
      selfCheckStatus: 'pending',
      selfScore: null,
      selfCheckAnalysisId: 'an-active-pending',
      videoS3Key: 'reference/uid-eunji/r-active-pending/v1.mp4',
      createdAt: T0 + 5_000,
    },
    activeSelfQueued: {
      ...PUBLIC_BASE,
      name: 'foxtop',
      level: 'advanced',
      isActive: true,
      registrationStatus: 'active',
      selfCheckStatus: 'queued',
      selfScore: null,
      videoS3Key: 'reference/uid-eunji/r-active-self-queued/v1.mp4',
      createdAt: T0 + 4_500,
    },
    activeOk: {
      ...PUBLIC_BASE,
      name: 'kip-up',
      level: 'basic',
      isActive: true,
      registrationStatus: 'active',
      selfCheckStatus: 'done',
      selfScore: 97,
      videoS3Key: 'reference/uid-eunji/r-active-ok/v1.mp4',
      createdAt: T0 + 4_000,
    },
    activeLow: {
      ...PUBLIC_BASE,
      name: 'peter-pan',
      level: 'advanced',
      isActive: true,
      registrationStatus: 'active',
      selfCheckStatus: 'done',
      selfScore: 61,
      videoS3Key: 'reference/uid-eunji/r-active-low/v1.mov',
      createdAt: T0 + 3_000,
    },
    activeSelfFailed: {
      ...PUBLIC_BASE,
      name: 'sideway-spin',
      level: 'intermediate',
      isActive: true,
      registrationStatus: 'active',
      selfCheckStatus: 'failed',
      selfScore: null,
      videoS3Key: 'reference/uid-eunji/r-active-self-failed/v1.mp4',
      createdAt: T0 + 2_500,
    },
    failedLowConfidence: {
      ...PUBLIC_BASE,
      name: 'elbow-twist',
      level: 'intermediate',
      isActive: false,
      registrationStatus: 'failed',
      registrationUpdatedAt: T0 + 2_100,
      createdAt: T0 + 2_000,
    },
    expired: {
      ...PUBLIC_BASE,
      name: 'combo-1',
      level: 'basic',
      isActive: false,
      registrationStatus: 'expired',
      createdAt: T0 + 1_000,
      uploadKey: 'reference/uid-eunji/r-expired/upload.mp4',
      uploadExpiresAt: T0 + 1_000 + UPLOAD_EXPIRES_MS,
    },
    // 손 등록 11개 모양(seed) — supplierUid 없음 → 공급자 행이 아니다(null)
    legacySeed: {
      name: '파워스핀',
      athleteName: '정은지',
      level: 'advanced',
      isActive: true,
      videoS3Key: 'reference/ref-power-spin.mp4',
      createdAt: T0,
    },
    // 레벨이 SkillLevel 밖 — picker 가 버리는 doc 은 공급자 행도 만들지 않는다
    badLevel: {
      ...PUBLIC_BASE,
      name: 'x',
      level: 'expert',
      isActive: true,
      registrationStatus: 'active',
      createdAt: T0,
    },
  },

  // 자기 재현성 문턱 경계 — activeOk 위에 selfScore 만 바꿔 쓴다(표시값 = 반올림, 분기도 같은 값)
  selfScoreBoundary: [
    { selfScore: 100, expect: 'ok' },
    { selfScore: 90, expect: 'ok' },
    { selfScore: 89.6, expect: 'ok' }, // 반올림 90 — 화면에 90 이라 쓰고 '낮아요' 라 하지 않는다
    { selfScore: 89.4, expect: 'low' },
    { selfScore: 0, expect: 'low' },
  ],

  // ── 비공개 doc `reference/{refId}/private/registration` (리뷰 R13) ────────
  privateDocs: {
    failedLowConfidence: {
      supplierUid: UID,
      consent: { ...CONSENT_REQUIRED, version: '2026-09-26', at: T0 + 2_000, uid: UID },
      registrationError: {
        code: 'low_confidence',
        message:
          '일부 관절을 못 읽었어요. 잘 안 보인 부위: 왼쪽 발목 · 오른쪽 발목. 밝은 곳에서, 옷과 배경이 구분되게 다시 촬영해 주세요.',
        joints: ['왼쪽 발목', '오른쪽 발목'],
      },
      techniqueRefId: null,
      isCombo: false,
      isSplit: true,
      hasHold: false,
      standingStart: true,
      updatedAt: T0 + 2_100,
    },
    activeOk: {
      supplierUid: UID,
      consent: { ...CONSENT_WITH_TRAINING, version: '2026-09-26', at: T0 + 4_000, uid: UID },
      registrationError: null,
      techniqueRefId: 'ref-kip-up',
      isCombo: false,
      isSplit: false,
      hasHold: true,
      standingStart: true,
      clipRange: { execStartS: 1.5, execEndS: 7 },
      updatedAt: T0 + 4_100,
    },
    // 리뷰 R9 — 실제 객체 크기(head_object)가 100MB 초과: 클라이언트 메타는 통과했던 건
    failedTooLarge: {
      supplierUid: UID,
      consent: { ...CONSENT_REQUIRED, version: '2026-09-26', at: T0 + 500, uid: UID },
      registrationError: {
        code: 'too_large',
        message: '용량이 너무 커요. 100MB 이하 영상으로 다시 올려주세요.',
      },
      techniqueRefId: null,
      isCombo: false,
      isSplit: false,
      hasHold: false,
      standingStart: true,
      updatedAt: T0 + 600,
    },
    // 서버가 새 코드를 먼저 붙인 경우 — 페이지는 server_error 문구로 받는다(미지 코드 규칙)
    unknownCode: {
      supplierUid: UID,
      consent: { ...CONSENT_REQUIRED, version: '2026-09-26', at: T0, uid: UID },
      registrationError: { code: 'gpu_oom', message: '등록 중 문제가 생겼어요.' },
      techniqueRefId: null,
      isCombo: true,
      isSplit: false,
      hasHold: false,
      standingStart: true,
      updatedAt: T0 + 100,
    },
  },
  unknownErrorCodes: ['gpu_oom', '', 'NO_HUMAN'],
  lowConfidenceJoints: ['왼쪽 발목', '오른쪽 발목'],

  // ── presign 실패 → 화면 분기 (api.ts ApiError.status/code 형상) ─────────────
  apiFailures: [
    { status: 401, code: 'unauthorized', expect: 'sessionExpired' },
    { status: 403, code: 'not_invited', expect: 'notInvited' }, // quick-260930-lfw — 옛 forbidden 대체
    { status: 0, code: null, expect: 'offline' },
    { status: 0, code: 'unauthenticated', expect: 'sessionExpired' }, // api.ts: currentUser 없음
    { status: 500, code: 'server_error', expect: 'presignFail' },
    { status: 400, code: 'too_long', expect: 'presignFail' },
    { status: 502, code: 'unknown', expect: 'presignFail' },
  ],

  // ── S3 PUT 결과 → 다음 화면 (A-5, 두 트랙 같은 전이표) ─────────────────────
  uploadOutcomes: [
    { outcome: 'ok', next: 'home' },
    { outcome: 'aborted', next: 'step2' },
    { outcome: 'failed', next: 'failPanel' },
  ],

  // ── 파일 검증 경계 (D-14 공급자 5~30초 · 콤보 60 · 100MB · mp4/mov) ─────────
  files: [
    { name: 'a.mp4', sizeBytes: 10_000_000, durationSec: 4.9, isCombo: false, expect: 'tooShort' },
    { name: 'b.mp4', sizeBytes: 10_000_000, durationSec: 5, isCombo: false, expect: null },
    { name: 'c.mov', sizeBytes: 10_000_000, durationSec: 30, isCombo: false, expect: null },
    { name: 'd.mp4', sizeBytes: 10_000_000, durationSec: 30.1, isCombo: false, expect: 'tooLong' },
    { name: 'e.mp4', sizeBytes: 10_000_000, durationSec: 60, isCombo: true, expect: null },
    { name: 'f.mp4', sizeBytes: 10_000_000, durationSec: 60.1, isCombo: true, expect: 'tooLong' },
    { name: 'g.mp4', sizeBytes: 10_000_000, durationSec: 45, isCombo: false, expect: 'tooLong' },
    { name: 'h.mov', sizeBytes: 10_000_000, durationSec: 4.9, isCombo: true, expect: 'tooShort' }, // 콤보는 하한을 낮추지 않는다
    { name: 'i.avi', sizeBytes: 10_000_000, durationSec: 12, isCombo: false, expect: 'format' },
    { name: 'j.mp4', sizeBytes: 101 * 1024 * 1024, durationSec: 12, isCombo: false, expect: 'tooLarge' },
    { name: 'k.mp4', sizeBytes: 100 * 1024 * 1024, durationSec: 12, isCombo: false, expect: null }, // 정확히 100MB 는 통과(초과만 거부)
    { name: 'l.mp4', sizeBytes: 10_000_000, durationSec: null, isCombo: false, expect: null }, // metadata 없음 = fail-open
    { name: 'M.MP4', sizeBytes: 10_000_000, durationSec: 12, isCombo: false, expect: null }, // 확장자 대소문자 무관
    { name: 'n.avi', sizeBytes: 101 * 1024 * 1024, durationSec: 1, isCombo: false, expect: 'format' }, // 순서: 형식 먼저
    { name: 'o.mp4', sizeBytes: 101 * 1024 * 1024, durationSec: 1, isCombo: false, expect: 'tooLarge' }, // 순서: 용량이 길이보다 먼저
    { name: 'noext', sizeBytes: 10_000_000, durationSec: 12, isCombo: false, expect: 'format' },
    { name: 'p.mp4', sizeBytes: 10_000_000, durationSec: Number.NaN, isCombo: false, expect: null }, // 비유한 = 모름 = fail-open
  ],

  // ── STEP 01 상태 (필수 8 = 체크 확인·동작 이름·선수 이름·레벨·선언 3·파일) ──
  step1: {
    complete: STEP1_COMPLETE,
    completeNewName: {
      ...STEP1_COMPLETE,
      nameChoice: { kind: 'new', name: '  새 동작 ' },
      level: 'advanced',
      isCombo: true,
      hasHold: 'yes',
      file: { name: 'combo.mov', sizeBytes: 55_000_000, durationSec: null, format: 'mov' },
    },
    missingTwo: { ...STEP1_COMPLETE, level: null, file: null },
    empty: {
      checkConfirmed: false,
      nameChoice: null,
      athleteName: '',
      level: null,
      isCombo: false,
      isSplit: null,
      hasHold: null,
      standingStart: null,
      file: null,
    },
    standingNo: { ...STEP1_COMPLETE, standingStart: 'no' },
    blankName: { ...STEP1_COMPLETE, nameChoice: { kind: 'new', name: '   ' } },
    longName: { ...STEP1_COMPLETE, nameChoice: { kind: 'new', name: '가'.repeat(31) } }, // > REFERENCE_NAME_MAX_LEN
    blankAthlete: { ...STEP1_COMPLETE, athleteName: ' ' },
  },

  consent: {
    allRequired: CONSENT_REQUIRED,
    allWithTraining: CONSENT_WITH_TRAINING,
    missingSilent: { portrait: true, usage: true, silent: false, training: true },
    none: { portrait: false, usage: false, silent: false, training: false },
  },

  // ── buildRequest 가 내야 할 정확한 형상 (ReferenceUploadUrlRequest, clipRange 키 없음) ──
  expectedRequest: {
    fromComplete: {
      name: 'kip-up',
      athleteName: '정은지',
      level: 'basic',
      techniqueRefId: 'ref-kip-up',
      isCombo: false,
      isSplit: true,
      hasHold: false,
      standingStart: true,
      consent: { portrait: true, usage: true, silent: true, training: false },
      format: 'mp4',
      fileSizeBytes: 24_000_000,
      durationSec: 8.2,
    },
    fromCompleteNewName: {
      name: '새 동작',
      athleteName: '정은지',
      level: 'advanced',
      techniqueRefId: null,
      isCombo: true,
      isSplit: true,
      hasHold: true,
      standingStart: true,
      consent: { portrait: true, usage: true, silent: true, training: true },
      format: 'mov',
      fileSizeBytes: 55_000_000,
      durationSec: null,
    },
  },

  // ── 다시 올리기 프리필 (38-10/38-12 가 URL/라우트 params 로 보낸다, '1'|'0' 인코딩) ──
  prefillParams: {
    failedRow: {
      name: 'kip-up',
      athleteName: '정은지',
      level: 'basic',
      isSplit: '1',
      hasHold: '0',
      standingStart: '1',
    },
    withDict: {
      name: 'kip-up',
      athleteName: '정은지',
      level: 'intermediate',
      techniqueRefId: 'ref-kip-up',
      isCombo: '1',
      isSplit: '0',
      hasHold: '1',
      standingStart: '1',
    },
    garbage: { name: '', level: 'expert', isSplit: 'maybe', hasHold: '', standingStart: '1' },
  },
} as const;
