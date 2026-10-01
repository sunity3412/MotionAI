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

// quick-260930-w9l(belle 2026-09-30): STEP 01 필수 4 = 체크 확인 · 동작 이름 · 레벨 · 파일.
// 선수 이름은 입력 칸이 아니라 초대 때 이름(읽기 전용), 콤보·선언 3 은 지웠다.
const STEP1_COMPLETE = {
  checkConfirmed: true,
  nameChoice: { kind: 'dict', motionId: 'ref-kip-up', name: 'kip-up' },
  level: 'basic',
  file: { name: 'kipup.mp4', sizeBytes: 24_000_000, durationSec: 8.2, format: 'mp4' },
} as const;

// STEP 02 필수 2 — 학습은 체크박스가 아니라 공급자 계약 안내 한 줄(w9l 항목 5·11).
const CONSENT_REQUIRED = { portrait: true, usage: true } as const;
// 2026-09-30 이전 doc 의 동의 기록 모양(silent·training 이 있다) — 비공개 doc fixture 전용.
const CONSENT_LEGACY = { portrait: true, usage: true, silent: true, training: false } as const;
const GIB = 1024 * 1024 * 1024; // = models.py REFERENCE_MAX_VIDEO_BYTES

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
      thumbnailS3Key: 'reference/uid-eunji/r-active-ok/thumb.jpg', // w9l — Pod 등록이 만든 썸네일
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
    // quick-261001-thx — 기계 판정 통과 뒤 사람 검수 대기. isActive false(수강생 비노출), 자기 재현성은 돈다.
    review: {
      ...PUBLIC_BASE,
      name: 'ayesha',
      level: 'advanced',
      isActive: false,
      registrationStatus: 'review',
      selfCheckStatus: 'done',
      selfScore: 94,
      videoS3Key: 'reference/uid-eunji/r-review/v1.mp4',
      thumbnailS3Key: 'reference/uid-eunji/r-review/thumb.jpg',
      createdAt: T0 + 9_000,
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
  // failedLowConfidence · unknownCode = 2026-09-30 이전 doc 모양(선언 4 · silent 있음) — 페이지는
  // 그 필드를 읽지 않는다. activeOk · failedTooLarge = w9l 뒤 새 모양.
  privateDocs: {
    failedLowConfidence: {
      supplierUid: UID,
      consent: { ...CONSENT_LEGACY, version: '2026-09-26', at: T0 + 2_000, uid: UID },
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
      consent: {
        ...CONSENT_REQUIRED,
        training: true,
        trainingBasis: 'supplier_contract',
        version: '2026-09-30',
        at: T0 + 4_000,
        uid: UID,
      },
      registrationError: null,
      techniqueRefId: 'ref-kip-up',
      clipRange: { execStartS: 1.5, execEndS: 7 },
      updatedAt: T0 + 4_100,
    },
    // 리뷰 R9 — 실제 객체 크기(head_object)가 1GB 초과: 클라이언트 메타는 통과했던 건
    failedTooLarge: {
      supplierUid: UID,
      consent: {
        ...CONSENT_REQUIRED,
        training: true,
        trainingBasis: 'supplier_contract',
        version: '2026-09-30',
        at: T0 + 500,
        uid: UID,
      },
      registrationError: {
        code: 'too_large',
        message: '용량이 너무 커요. 1GB 이하 영상으로 다시 올려주세요.',
      },
      techniqueRefId: null,
      updatedAt: T0 + 600,
    },
    // quick-261001-thx — 운영자가 검수에서 반려(review → failed). 사유는 reason 에 원문으로.
    rejected: {
      supplierUid: UID,
      consent: {
        ...CONSENT_REQUIRED,
        training: true,
        trainingBasis: 'supplier_contract',
        version: '2026-09-30',
        at: T0 + 9_000,
        uid: UID,
      },
      registrationError: {
        code: 'rejected',
        message: '검수에서 반려됐어요. 사유: 화면이 어두워요. 고쳐서 다시 올려 주세요.',
        reason: '화면이 어두워요',
      },
      review: { decision: 'rejected', by: 'ops:belle', at: T0 + 9_500, reason: '화면이 어두워요' },
      techniqueRefId: null,
      updatedAt: T0 + 9_500,
    },
    // reason 이 문자열이 아닌 이상 doc — 페이지는 사유를 버리고 사유 없는 문장으로 보인다.
    rejectedBadReason: {
      supplierUid: UID,
      registrationError: { code: 'rejected', message: 'x', reason: 42 },
      techniqueRefId: null,
      updatedAt: T0 + 9_600,
    },
    // 서버가 새 코드를 먼저 붙인 경우 — 페이지는 server_error 문구로 받는다(미지 코드 규칙)
    unknownCode: {
      supplierUid: UID,
      consent: { ...CONSENT_LEGACY, version: '2026-09-26', at: T0, uid: UID },
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
    { status: 400, code: 'too_large', expect: 'presignFail' }, // w9l — 1GB 문구지만 분기는 상태코드만 본다
    { status: 409, code: 'supplier_name_missing', expect: 'presignFail' }, // w9l — 화면이 먼저 막는다
    { status: 502, code: 'unknown', expect: 'presignFail' },
  ],

  // ── S3 PUT 결과 → 다음 화면 (A-5, 두 트랙 같은 전이표) ─────────────────────
  uploadOutcomes: [
    { outcome: 'ok', next: 'home' },
    { outcome: 'aborted', next: 'step2' },
    { outcome: 'failed', next: 'failPanel' },
  ],

  // ── 파일 검증 경계 (w9l: 공급자 5초~2분 · 1GB · mp4/mov, 콤보 구분 없음) ─────────
  files: [
    { name: 'a.mp4', sizeBytes: 10_000_000, durationSec: 4.9, expect: 'tooShort' },
    { name: 'b.mp4', sizeBytes: 10_000_000, durationSec: 5, expect: null },
    { name: 'c.mov', sizeBytes: 10_000_000, durationSec: 120, expect: null },
    { name: 'd.mp4', sizeBytes: 10_000_000, durationSec: 120.1, expect: 'tooLong' },
    { name: 'g.mp4', sizeBytes: 10_000_000, durationSec: 45, expect: null }, // 옛 30초 상한 밖 — 이제 통과
    { name: 'e.mp4', sizeBytes: GIB, durationSec: 12, expect: null }, // 정확히 1GB 는 통과(초과만 거부)
    { name: 'f.mp4', sizeBytes: GIB + 1, durationSec: 12, expect: 'tooLarge' },
    { name: 'i.avi', sizeBytes: 10_000_000, durationSec: 12, expect: 'format' },
    { name: 'j.mp4', sizeBytes: 101 * 1024 * 1024, durationSec: 12, expect: null }, // 옛 100MB 한도 밖 — 이제 통과
    { name: 'k.mp4', sizeBytes: 100 * 1024 * 1024, durationSec: 12, expect: null },
    { name: 'l.mp4', sizeBytes: 10_000_000, durationSec: null, expect: null }, // metadata 없음 = fail-open
    { name: 'M.MP4', sizeBytes: 10_000_000, durationSec: 12, expect: null }, // 확장자 대소문자 무관
    { name: 'n.avi', sizeBytes: GIB + 1, durationSec: 1, expect: 'format' }, // 순서: 형식 먼저
    { name: 'o.mp4', sizeBytes: GIB + 1, durationSec: 1, expect: 'tooLarge' }, // 순서: 용량이 길이보다 먼저
    { name: 'noext', sizeBytes: 10_000_000, durationSec: 12, expect: 'format' },
    { name: 'p.mp4', sizeBytes: 10_000_000, durationSec: Number.NaN, expect: null }, // 비유한 = 모름 = fail-open
  ],

  // ── STEP 01 상태 (필수 4 = 체크 확인·동작 이름·레벨·파일) ──
  step1: {
    complete: STEP1_COMPLETE,
    completeNewName: {
      ...STEP1_COMPLETE,
      nameChoice: { kind: 'new', name: '  새 동작 ' },
      level: 'advanced',
      file: { name: 'combo.mov', sizeBytes: 550_000_000, durationSec: null, format: 'mov' },
    },
    missingTwo: { ...STEP1_COMPLETE, level: null, file: null },
    empty: {
      checkConfirmed: false,
      nameChoice: null,
      level: null,
      file: null,
    },
    blankName: { ...STEP1_COMPLETE, nameChoice: { kind: 'new', name: '   ' } },
    longName: { ...STEP1_COMPLETE, nameChoice: { kind: 'new', name: '가'.repeat(31) } }, // > REFERENCE_NAME_MAX_LEN
  },

  consent: {
    allRequired: CONSENT_REQUIRED,
    missingUsage: { portrait: true, usage: false },
    missingPortrait: { portrait: false, usage: true },
    none: { portrait: false, usage: false },
  },

  // ── buildRequest 가 내야 할 정확한 형상 (ReferenceUploadUrlRequest — 선수 이름·선언·학습 없음) ──
  expectedRequest: {
    fromComplete: {
      name: 'kip-up',
      level: 'basic',
      techniqueRefId: 'ref-kip-up',
      consent: { portrait: true, usage: true },
      format: 'mp4',
      fileSizeBytes: 24_000_000,
      durationSec: 8.2,
    },
    fromCompleteNewName: {
      name: '새 동작',
      level: 'advanced',
      techniqueRefId: null,
      consent: { portrait: true, usage: true },
      format: 'mov',
      fileSizeBytes: 550_000_000,
      durationSec: null,
    },
  },

  // ── 다시 올리기 프리필 (URL/라우트 params — name · level · techniqueRefId 만) ──
  // 옛 링크(38-13 웹 번들)에 남은 athleteName·isCombo·isSplit… 는 무시된다.
  prefillParams: {
    failedRow: {
      name: 'kip-up',
      level: 'basic',
      athleteName: '정은지',
      isSplit: '1',
      hasHold: '0',
      standingStart: '1',
    },
    withDict: {
      name: 'kip-up',
      level: 'intermediate',
      techniqueRefId: 'ref-kip-up',
      isCombo: '1',
    },
    garbage: { name: '', level: 'expert', isSplit: 'maybe' },
  },
} as const;
