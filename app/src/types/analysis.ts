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

// ml/CLAUDE.md 분석 오류 처리 = design.md §6 오류 4종
export type AnalysisErrorCode =
  | 'no_human'
  | 'size_exceeded'
  | 'unsupported_format'
  | 'server_error';

export type BodyPart = '상체' | '코어' | '하체'; // design.md §8 파트별 점수

export interface JointScore {
  key: string; // ViTPose 17 keypoint 이름 (예: 'left_knee')
  labelKo: string; // 표시용 (예: '왼쪽 무릎')
  score: number; // 0~100
  issue?: string; // 문제 설명 (예: '무릎이 20° 덜 펴짐'). 없으면 양호
}

export interface CoachingTip {
  joint?: string; // 관련 관절 key (선택)
  title: string; // KISMAM Top-3 교정 포인트 (예: '무릎 신전 부족')
  detail: string; // Cerebras 자연어 가이드 문장
}

export interface Mode1Comparison {
  mode: 'mode1';
  referenceMotionId: string;
  referenceMotionName: string; // 예: '인사이드 레그 행'
  athleteName: string; // 예: '정은지'
  similarity: number; // 0~100
}

export interface Mode3Comparison {
  mode: 'mode3';
  isFirst: boolean; // 첫 분석이면 절대값만 (비교 대상 없음)
  previousAnalysisId?: string;
  deltaFromPrevious?: Record<BodyPart, number>; // 이전 대비 증감(±). isFirst면 없음
}

export interface AnalysisResult {
  overallScore: number; // 0~100 (KISMAM 정규화)
  partScores: Record<BodyPart, number>; // 상체/코어/하체 0~100
  joints: JointScore[]; // 관절별 (보통 17)
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
}

// 기준 모션 (Firestore: reference/motions/{motionId}, 읽기 전용)
export type SkillLevel = 'basic' | 'intermediate' | 'advanced';
export interface ReferenceMotion {
  motionId: string;
  name: string; // 동작명
  athleteName: string; // '정은지'
  level: SkillLevel;
  description?: string;
  thumbnailUrl?: string;
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
