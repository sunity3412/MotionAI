// 분석 데이터 계약 (앱 ↔ 백엔드 단일 소스). 사람용 명세: /docs/contract.md
// 근거: backend/CLAUDE.md(엔드포인트·S3흐름·Firestore), ml/CLAUDE.md(모드·오류·파이프라인),
//      design.md §8(결과 화면 데이터), 배포된 Firestore 보안 규칙(users/{uid} 격리).
// 이 파일이 바뀌면 docs/contract.md 와 백엔드도 같이 맞춰야 함.

// 분석 모드 (ml/CLAUDE.md Mode별 측정 방식)
//  mode1 = 정은지(전문가) 비교 / mode3 = 자기 성장 추적
export type AnalysisMode = 'mode1' | 'mode3';

export type VideoFormat = 'mp4' | 'mov';

export const MAX_VIDEO_BYTES = 100 * 1024 * 1024; // design.md: 100MB 초과 불가

// ── 1. 업로드 URL 발급 (POST /upload-url) ──────────────────────────────
// 앱이 S3에 직접 PUT 하기 위한 presigned URL 요청. (Lambda 경유 업로드 금지)
export interface UploadUrlRequest {
  mode: AnalysisMode;
  fileName: string;
  fileSizeBytes: number;
  format: VideoFormat;
  referenceMotionId?: string; // mode1 필수: 비교할 정은지 동작 ID
}

export interface UploadUrlResponse {
  analysisId: string; // 이 분석 건 ID = Firestore 문서 ID
  uploadUrl: string; // S3 presigned PUT URL
  s3Key: string; // 업로드될 S3 객체 키
  expiresInSec: number; // presigned URL 만료(초)
}

// ── 2. 분석 진행/결과 (Firestore: users/{uid}/analyses/{analysisId}) ───
// 앱이 문서를 'uploading'으로 생성 → S3 트리거 후 백엔드(Admin SDK)가 상태/결과 갱신.
// 앱은 이 문서를 구독(onSnapshot)하며 로딩 화면 단계를 표시.
export type AnalysisStatus =
  | 'uploading' // 앱이 S3 업로드 중 (앱이 설정)
  | 'queued' // S3 트리거됨, 파이프라인 대기
  | 'frame_extraction' // 프레임 추출
  | 'pose_analysis' // YOLO11 + ViTPose-S
  | 'comparison' // MotionDTW 비교 + 점수
  | 'done'
  | 'failed';

// ml/CLAUDE.md 분석 오류 처리 = design.md §6 오류 4종 + 비폴 차단(belle P1 #8)
export type AnalysisErrorCode =
  | 'no_human'
  | 'size_exceeded'
  | 'unsupported_format'
  | 'server_error'
  | 'not_pole_motion'; // mode1 비교 similarity 가 임계값 미만

// 점수 차원 = IPSF 폴스포츠 실행 심사기준 (docs/research/폴스포츠-지식.md 보고서 5·6).
// 신체 부위(상체/코어/하체)가 아니라 심판이 실제로 보는 실행 차원.
//   angle     각도 정확도 : 관절각 vs 기준(reference). reference 필요 → mode1·mode3 second+.
//   line      라인·확장   : 기술이 신전 요구하는 사지의 완성도. 절대 지표(기준 불필요).
//   stability 안정성·홀딩 : 피크 구간 떨림. 절대 지표.
// 2026-05-29 'balance(좌우대칭)' 제거 — IPSF 근거 없음(의도적 비대칭 동작을 깎는 위양성).
// 절대 차원(line/stability)은 기준 없이 산출 → mode3 자기 성장의 세션 간 발전 델타가
// 같은 척도로 비교됨.
export type ScoreDimension = 'angle' | 'line' | 'stability';

export const DIMENSION_LABEL_KO: Record<ScoreDimension, string> = {
  angle: '각도 정확도',
  line: '라인·확장',
  stability: '안정성·홀딩',
};

// 표시 순서. mode1 = 3차원 전부, mode3 = 절대 차원(line/stability)(+ second+ 면 angle 일관성).
export const DIMENSION_ORDER: readonly ScoreDimension[] = [
  'angle',
  'line',
  'stability',
];

// 사용자가 무엇을 더 해야 하는지(코칭 방향). 백엔드가 joint 종류 + signed delta로 결정.
//  extend/flex : 관절 펴기/굽히기 (무릎·팔꿈치)
//  raise/lower : 더 올리기/내리기 (다리·팔)
//  open/close  : 더 열기/모으기 (고관절·어깨 외전/내전)
// 회전·반동(각속도) 류 동적 큐는 별도 필드 만들지 않고 CoachingTip.detail (LLM 문장).
export type JointDirection = 'extend' | 'flex' | 'raise' | 'lower' | 'open' | 'close';

export interface JointScore {
  key: string; // ViTPose 17 keypoint 이름 (예: 'left_knee')
  labelKo: string; // 표시용 (예: '왼쪽 무릎')
  score: number; // 0~100
  // 구조화 가이드 (있으면 UI가 "현재 145°→기준 168°·더 펴주세요" 형태로 표시).
  // 백엔드가 채울 수 없을 때 옵셔널로 비울 수 있음(UI는 issue 폴백).
  currentAngle?: number; // 분석 영상의 평균/대표 각도(deg)
  targetAngle?: number; // 기준 동작의 평균/대표 각도(deg)
  deltaDeg?: number; // signed = currentAngle - targetAngle
  direction?: JointDirection;
  issue?: string; // 사람 가독 폴백 (예: '기준 대비 평균 23° 차이'). 없으면 양호
}

export interface CoachingTip {
  joint?: string; // 관련 관절 key (선택)
  title: string; // KISMAM Top-3 교정 포인트 (예: '무릎 신전 부족')
  detail: string; // Cerebras 자연어 가이드 문장
}

// 구간별 점수 (reference-motions.md §7 공유 베이스 모션).
// 일부 기술은 다른 기술의 베이스 구간을 공유함 (인버트 → 폭스탑 → 폭스탑 스플릿).
// 한 기술 안에서 베이스 구간과 확장 구간을 나눠 평가해, 학생이 어느 단계에서
// 막혔는지 보여줌.
export interface SegmentScores {
  base: number; // 공유 베이스 구간 점수 0~100
  extension: number; // 확장(고유) 구간 점수 0~100
  baseMotionId: string; // 베이스를 공유하는 모션 ID (학습 경로 가이드용)
  baseMotionName: string; // 그 모션 이름 (예: '인버트')
}

export interface Mode1Comparison {
  mode: 'mode1';
  referenceMotionId: string;
  referenceMotionName: string; // 예: '사이드웨이 스핀'
  athleteName: string; // 예: '정은지'
  similarity: number; // 0~100
  // 베이스 구간을 공유하는 기술을 분석한 경우에만 채워짐. 단일 기술이면 없음.
  segmentScores?: SegmentScores;
}

export interface Mode3Comparison {
  mode: 'mode3';
  isFirst: boolean; // 첫 분석이면 절대값만 (비교 대상 없음)
  previousAnalysisId?: string;
  // 발전(progress) = 절대 차원(라인/안정성)의 이전 대비 증감(±). isFirst면 없음.
  // '몇 % 일치'가 아니라 발전을 보여주는 게 mode3 의 핵심.
  deltaFromPrevious?: Partial<Record<ScoreDimension, number>>;
}

export interface AnalysisResult {
  overallScore: number; // 0~100. mode1=4차원 평균, mode3=절대 3차원 평균
  // IPSF 실행 차원 점수. mode1=angle+line+stability, mode3=line/stability
  // (+second+ 면 angle 일관성). 표시는 DIMENSION_ORDER 순서로 존재하는 키만.
  dimensionScores: Partial<Record<ScoreDimension, number>>;
  joints: JointScore[]; // 관절별 (보통 8). 코칭 팁 근거(각도 편차)
  tips: CoachingTip[]; // 상위 3개
  comparison: Mode1Comparison | Mode3Comparison;
  myVideoUrl: string; // 재생용 서명 URL (design.md §8 좌: 내 영상)
  referenceVideoUrl?: string; // mode1 우: 정은지 영상
}

// Firestore 문서 전체 모양
export interface AnalysisDoc {
  analysisId: string;
  mode: AnalysisMode;
  status: AnalysisStatus;
  fileName: string;
  createdAt: number; // epoch ms
  updatedAt: number; // epoch ms
  error?: { code: AnalysisErrorCode; message: string }; // status==='failed'
  result?: AnalysisResult; // status==='done'
  // 추출된 관절각 flat 저장 (백엔드 전용 — mode3 가 '이전 영상' 기준 DTW 비교에 사용).
  // Firestore nested-array 금지 회피로 flat. 앱 UI 는 사용 안 함(normalize 제외).
  angles?: number[]; // 길이 = anglesFrames * anglesJointKeys.length
  anglesJointKeys?: string[]; // 길이 J (보통 8)
  anglesFrames?: number; // T
}

// 기준 모션 (Firestore: reference/{motionId}, 읽기 전용)
// 스키마 단일 진실: docs/reference-motions.md §3. 새 모션은 거기 §6 절차로 등록.
export type SkillLevel = 'basic' | 'intermediate' | 'advanced';

// 동작 진입 방식 (reference-motions.md §2). UX 가이드 + entry_type 자동판별 학습용.
export type EntryType =
  | 'step_entry'
  | 'jump_entry'
  | 'swing_entry'
  | 'lift_entry'
  | 'invert_entry'
  | 'combo_entry';

// reference 영상의 구간 시점(초). 분석 런타임은 execStartS~landEndS 만 사용
// (reference-motions.md §4). prepStartS 는 사용자 촬영 UX 가이드용.
export interface ClipRange {
  prepStartS: number;
  execStartS: number;
  execPeakS: number; // 시각적 피크 — heroFrame 추출 시점
  landEndS: number;
  recommendedRecordS: number; // 사용자 권장 촬영 길이
}

// KISMAM 채점 가중 관절 (reference-motions.md §3). weight 합 = 1.0.
export interface Checkpoint {
  joint: string; // ViTPose 17 keypoint 이름 (spine_mid 등 보간 관절 포함)
  weight: number;
  note?: string;
}

export interface ReferenceMotion {
  motionId: string;
  name: string; // 동작명
  athleteName: string; // '정은지'
  level: SkillLevel;
  entryType?: EntryType;
  entryDescription?: string; // 진입 방식 상세 (사용자 안내용)
  description?: string;
  videoUrl?: string; // s3://... — 분석 시 reference 시퀀스 추출 원본
  thumbnailUrl?: string;
  clipRange?: ClipRange;
  checkpoints?: Checkpoint[];
  // 공유 베이스 (reference-motions.md §7). 이 기술이 다른 기술의 베이스
  // 구간을 공유하면 그 기술 ID + 공유가 끝나는 시점(초). 단일 기술이면 없음.
  //   ref-invert → ref-foxtop(baseUntilS:6) → ref-foxtop-split(baseUntilS:18)
  sharedBaseMotionId?: string;
  baseUntilS?: number;
  updatedAt?: number; // epoch ms — 시드/관리자 등록 시 갱신. NEW 배너 정렬용

  // NLF 추출 시퀀스 (extract_reference_angles.py 결과를 seed-reference-motions
  // 가 Firestore 에 채움). nested-array 금지 회피로 flat 저장 — 백엔드/앱에서
  // anglesJointKeys 길이로 reshape. 결과 화면 코칭팁이 reference 실측 각도를
  // 표시하려면 meanAngles 가 필요. 시드 전이거나 등록 안 된 모션은 모두 undef.
  anglesJointKeys?: string[]; // 길이 = J (보통 8)
  anglesFrames?: number; // T (디버깅용; angles.length === T*J 인지 확인)
  // 시퀀스 평균 각도(deg). 결과 화면이 targetAngle 로 사용. meanAngles 필드를
  // 시드에서 미리 채우거나 (없으면) 앱이 angles 에서 derive — 둘 다 지원.
  meanAngles?: Record<string, number>; // key -> degrees
}

// ── Pose Engine 데이터 계약 (Phase 1, D-04/D-05/D-11/D-12) ─────────────────
//
// PoseFrame/PoleAxis 는 backend/shared/python/sunity_shared/analysis/pose_frame.py 의
// dataclass 와 lockstep (CLAUDE.md Cross-cutting). 변경 시 양쪽 + docs/contract.md §6 모두 갱신.
// M-1: rawVisibility/rawPresence 는 별도 필드 (D-05).
// H-3: PoseFrame.poleAxis 필수 (D-12).
// H-4: PoseFrame.reliability 필수 (D-05 저신뢰 게이트).

// M-2 D-11 박제: PoleAxis.confidenceLevel 과 PoseFrame.reliability 둘 다 동일 값 도메인.
// 의도 분리를 위해 두 alias 로 선언.
export type ConfidenceLevel = 'high' | 'medium' | 'low';
export type ReliabilityLevel = 'high' | 'medium' | 'low';

// H-3 reviewer 명세: D-09/D-11.
// 'detected' = Hough 검출 성공, 'vertical_fallback' = 검출 실패 수직 가정.
export type PoleAxisSource = 'detected' | 'vertical_fallback';

/**
 * MediaPipe 33 raw world landmark (metric 3D).
 * M-1 D-05: raw_visibility / raw_presence 별도 필드 (visibility / presence 단축명 없음).
 */
export interface Landmark3D {
  x: number;
  y: number;
  z: number;
  /** MediaPipe API: Landmark.visibility — D-05 */
  rawVisibility: number;
  /** MediaPipe API: Landmark.presence — D-05 */
  rawPresence: number;
}

/**
 * COCO-17 keypoint. confidence = rawVisibility x rawPresence (D-05).
 * uncertaintyProxy = 1 - confidence.
 */
export interface Keypoint3D {
  x: number;
  y: number;
  z: number;
  confidence: number;
  uncertaintyProxy: number;
}

/**
 * 폴 축 정렬된 좌표 (D-12). 신뢰도는 keypoints3D 의 같은 키로 lookup.
 */
export interface Keypoint3DAligned {
  x: number;
  y: number;
  z: number;
}

/**
 * image normalized 0~1 (D-03 UI 오버레이용).
 * image landmark 는 raw_presence 별도 API 미제공 → visibility 한 필드.
 */
export interface Keypoint2D {
  x: number;
  y: number;
  visibility: number;
}

/**
 * 폴 확장 랜드마크 — toe / heel / grip (D-04).
 * 가림 발생이 잦아 confidence 게이트 별도 저장.
 */
export interface PoleExtensionLandmark {
  x: number;
  y: number;
  z: number;
  confidence: number;
}

/**
 * 폴 축 메타 (H-3 + D-09/D-11/D-12 박제).
 * axisVector: 3D 단위 벡터.
 * confidenceLevel: M-2 D-11 enum — 검출 실패 시 'low'.
 * source: D-09/D-11 — 'detected' | 'vertical_fallback'.
 * frameIndex: null 이면 video-level (D-10 영상 전체 평균 축 1개).
 */
export interface PoleAxis {
  axisVector: { x: number; y: number; z: number };
  /** M-2 D-11: 검출 실패 시 'low' */
  confidenceLevel: ConfidenceLevel;
  source: PoleAxisSource;
  /** D-10: null = video-level (모든 frame 공유) */
  frameIndex?: number | null;
}

/**
 * 체형 정규화 프로파일 (D-19 RTMW pivot — SMPL-X β 없이 segment 비율).
 *
 * Python lockstep: backend/shared/python/sunity_shared/analysis/body_normalization.py
 *   BodyNormalizationProfile
 * 변경 시 양쪽 + docs/contract.md §6 동시 갱신 (CLAUDE.md Cross-cutting).
 *
 * SMPL-X β / shape_params 필드는 **영구히 도입하지 않는다** (D-19).
 * NLF_SMPLX R&D path 에서 β 가 필요하면 R&D 전용 별도 타입을 둘 것 — 본 contract 아님.
 *
 * Consumer 예고 (Phase 2 BODY-01): segment-ratio 측정기가 채운 profile 을
 * PoseFrame.bodyShape 로 주입한다. Phase 1 단계에는 측정기 미구현.
 */
export interface BodyNormalizationProfile {
  /** 추정 신장 비율 (1.0 = 평균). RTMW segment 합으로 산출. */
  estimatedHeightScale: number;
  /** 팔 segment 비율 (1.0 = 평균). */
  armScale: number;
  /** 다리 segment 비율 (1.0 = 평균). */
  legScale: number;
  /** 몸통 segment 비율 (1.0 = 평균). */
  torsoScale: number;
  /** 어깨너비 / 골반너비 비율 (체형 분류 단서). */
  shoulderHipRatio: number;
  /** 측정 신뢰도 [0.0 ~ 1.0]. RTMW score 또는 측정기 자체 신뢰도. */
  confidence: number;
  /** 측정 품질 이슈 (예: 'short_arm_clip'). 기본값 []. */
  warnings: string[];
}

/**
 * 영상 한 프레임 포즈 계약 (D-04/D-05/D-11/D-12/D-21 + H-3/H-4).
 *
 * Python lockstep: backend/shared/python/sunity_shared/analysis/pose_frame.py PoseFrame
 * camelCase ↔ snake_case 1:1 매핑 — 10개 필드:
 *   frameIndex, timestampMs, rawLandmarks33, keypoints3D, keypoints3DPoleAligned,
 *   keypoints2D, poleExtensionLandmarks, poleAxis, reliability,
 *   bodyShape (D-21 RTMW pivot — nullable)
 */
export interface PoseFrame {
  frameIndex: number;
  timestampMs: number;
  /** D-04 원본 보존 (MediaPipe 33 또는 RTMW 133) */
  rawLandmarks33?: Record<string, Landmark3D>;
  /** COCO-17 분석용 */
  keypoints3D: Record<string, Keypoint3D>;
  /** D-12 폴 축 정렬 좌표 */
  keypoints3DPoleAligned: Record<string, Keypoint3DAligned>;
  /** D-03 UI 오버레이용 */
  keypoints2D?: Record<string, Keypoint2D>;
  /** D-04 폴 확장 (toe/heel/grip) */
  poleExtensionLandmarks?: Record<string, PoleExtensionLandmark>;
  /** H-3 D-12: video-level PoleAxis 메타 (모든 frame 공유) */
  poleAxis: PoleAxis | null;
  /** H-4 D-05: frame-level 신뢰 게이트 — 'low' 시 단정형 코멘트 금지 */
  reliability: ReliabilityLevel;
  /**
   * D-21 RTMW pivot: 체형 정규화 프로파일.
   * - RTMW 운영 path = null (Phase 1 단계 측정기 미구현)
   * - NLF_SMPLX R&D path = BodyNormalizationProfile 채움
   */
  bodyShape: BodyNormalizationProfile | null;
}

// ── 표시 매핑 (design.md §5-9 단계별 메시지 / §6 오류) ──────────────────
export const STATUS_MESSAGE: Record<AnalysisStatus, string> = {
  uploading: '영상을 올리는 중...',
  queued: '분석을 준비하는 중...',
  frame_extraction: '영상 프레임 추출 중...',
  pose_analysis: '포즈 데이터 분석 중...',
  comparison: '기준 모션과 비교 중...',
  done: '분석이 완료되었어요!',
  failed: '분석에 실패했어요',
};

export const ERROR_MESSAGE: Record<AnalysisErrorCode, string> = {
  no_human: '영상에서 사람을 찾지 못했어요. 전신이 보이게 다시 촬영해주세요.',
  size_exceeded: '100MB 이하 영상만 분석할 수 있어요.',
  unsupported_format: 'mp4, mov 형식의 영상만 분석할 수 있어요.',
  server_error: '분석 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.',
  not_pole_motion:
    '선택한 기준 동작과 너무 달라요. 폴스포츠 동작이 맞는지 확인하고 다시 시도해주세요.',
};

// 로딩 화면 단계 진행 순서 (design.md §5-9). failed 는 별도 처리.
export const PROGRESS_SEQUENCE: readonly AnalysisStatus[] = [
  'uploading',
  'queued',
  'frame_extraction',
  'pose_analysis',
  'comparison',
  'done',
] as const;
