// 분석 데이터 계약 (앱 ↔ 백엔드 단일 소스). 사람용 명세: /docs/contract.md
// 근거: backend/CLAUDE.md(엔드포인트·S3흐름·Firestore), ml/CLAUDE.md(모드·오류·파이프라인),
//      design.md §8(결과 화면 데이터), 배포된 Firestore 보안 규칙(users/{uid} 격리).
// 이 파일이 바뀌면 docs/contract.md 와 백엔드도 같이 맞춰야 함.

// 분석 모드 (ml/CLAUDE.md Mode별 측정 방식)
//  mode1 = 정은지(전문가) 비교 / mode3 = 자기 성장 추적
export type AnalysisMode = 'mode1' | 'mode3';

export type VideoFormat = 'mp4' | 'mov';

export const MAX_VIDEO_BYTES = 100 * 1024 * 1024; // design.md: 100MB 초과 불가

// ── BodyProfile 자가입력 (Phase 3, Plan 03-01) — 3-way lockstep #1 ──────
// Python 미러: backend/shared/python/sunity_shared/models.py
//   (EXPERIENCE_LEVELS / DOMINANT_HANDS / PAIN_AREAS + normalize_body_profile).
// 사람용 명세: docs/contract.md "BodyProfile (자가입력)" 섹션.
// 이 셋이 바뀌면 동시 갱신 필수 (위 co-edit 명령 정합).
export type ExperienceLevel = 'beginner' | 'intermediate' | 'advanced';
export type DominantHand = 'left' | 'right' | 'both';
// 폴스포츠 고하중 관절 (docs/research/폴스포츠-지식.md 정합) — 통증부위 다중선택.
export type PainArea =
  | 'shoulder'
  | 'wrist'
  | 'lower_back'
  | 'knee'
  | 'ankle'
  | 'neck'
  | 'hip'
  | 'elbow';

// 게스트 자가입력 신체 프로필. 모든 측정값 nullable (부분 입력 graceful, D-06).
// 저장: 라이브 users/{uid}.bodyProfile + per-analysis SNAPSHOT (AnalysisDoc).
export interface BodyProfile {
  heightCm: number | null;
  // 보조 ONLY — 분석 단정·점수 가중 금지 (D-05). scoring consumer 모듈 유입 금지.
  weightKg: number | null;
  experience: ExperienceLevel | null;
  // flat scalar array — Firestore nested-array 안전 (top-level 보관, Pitfall 7).
  painAreas: PainArea[];
  dominantHand: DominantHand | null;
  updatedAt?: number; // 마지막 저장 epoch ms (saveBodyProfile merge)
  promptDismissedAt?: number; // 03-03 첫 분석 권유 모달 once-flag
}

// [WR-03] BodyProfile enum → KO 라벨 단일 출처 (DIMENSION_LABEL_KO 와 동일 패턴).
// profile.tsx / result.tsx / BodyProfileForm.tsx 가 동일 매핑을 각자 복제하면
// union 멤버 추가 시 한 곳을 놓쳐도 컴파일이 안 막히고 undefined 가 렌더된다.
// Record<Union, string> 로 여기 한 곳에 두면 멤버 추가 시 모든 소비처가 빌드에서
// 강제로 갱신된다 (라벨 lockstep). BodyProfileForm 의 옵션 배열은 표시 순서가
// 필요해 이 맵에서 label 을 끌어 쓰되 value 순서는 자체 배열로 유지한다.
export const EXPERIENCE_LABEL_KO: Record<ExperienceLevel, string> = {
  beginner: '초급',
  intermediate: '중급',
  advanced: '고급',
};
export const DOMINANT_HAND_LABEL_KO: Record<DominantHand, string> = {
  left: '왼손',
  right: '오른손',
  both: '양손',
};
// 폴스포츠 고하중 관절 KO 라벨 (docs/research/폴스포츠-지식.md 정합).
export const PAIN_AREA_LABEL_KO: Record<PainArea, string> = {
  shoulder: '어깨',
  wrist: '손목',
  lower_back: '허리',
  knee: '무릎',
  ankle: '발목',
  neck: '목',
  hip: '고관절',
  elbow: '팔꿈치',
};

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

// 차원 메인 라벨 — 사용자 친화 (Phase 12.5 belle 피드백: "라인·확장 / 안정성·홀딩"
// 묶음 라벨이 사용자에게 불명확. "팔다리 펴기" / "동작 안정성" 풀어 표현).
export const DIMENSION_LABEL_KO: Record<ScoreDimension, string> = {
  angle: '각도 정확도',
  line: '팔다리 펴기',
  stability: '동작 안정성',
};

// 차원 부제 — track bar 아래 secondary text (Phase 12.5).
// "이게 무슨 기준인지" 한 줄 안내. mode 분기는 result.tsx 에서 동적 처리 시 갱신.
export const DIMENSION_SUBLABEL_KO: Record<ScoreDimension, string> = {
  angle: '정은지 선수 자세 기준',
  line: '팔/다리 완전히 펴는 정도',
  stability: '핵심 자세에서 떨림 정도',
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
  // Phase 12 Wave 0A R2/R4 (Codex 직접 리뷰 2026-06-10) — target 산출 출처.
  //   reference_motion       = mode1 (정은지 measured)
  //   previous_analysis      = mode3_progress (이전 영상 measured)
  //   extension_requirement  = mode3_first 의 extension 필요 관절 (IPSF 180°)
  //   unavailable            = mode3_first 의 extension 불필요 관절 (기준 없음)
  // UI 의 "기준 N°" prefix 분기 (정은지 / 지난 영상 / IPSF 180° / 기준 없음).
  targetSource?:
    | 'reference_motion'
    | 'previous_analysis'
    | 'extension_requirement'
    | 'unavailable';
  issue?: string; // 사람 가독 폴백 (예: '기준 대비 평균 23° 차이'). 없으면 양호
}

export interface CoachingTip {
  joint?: string; // 관련 관절 key (선택)
  title: string; // KISMAM Top-3 교정 포인트 (예: '무릎 신전 부족')
  detail: string; // Cerebras 자연어 가이드 문장 (카드 본문 짧은 한 줄)
  // Phase 12.5 T9 (2026-06-07): "자세히 ›" 모달용 상세 박제. LLM 동적 생성.
  // 옵셔널 — backend graceful (LLM 실패 시 없음) + 이전 빌드 doc 호환.
  detail2?: CoachingTipDetail;
}

// Phase 12.5 T9: 코칭 팁 자세히 모달 데이터 (LLM 동적).
// belle 의도 (2026-06-07): "원인 후보 3~5 + 각 case 처방 + 부상 경고 + 코치 권고"
// = Phase 11 CoachCommentHook + Phase 13 보완 운동 라이브러리 결합의 압축 layer.
// Cerebras (gpt-oss-120b) 가 한 호출로 짧은 detail + 긴 detail2 둘 다 생성.
export interface CoachingTipDetail {
  // 원인 후보 3~5개. 각 case 별 진단 + 처방.
  // 사용자 input = 정확한 원인 모르므로 "이런 경우 박제 박제" 식으로 다중 제시.
  causes: CoachingCause[];
  // 부상 위험 경고 (해당 시). LLM 판단 — 없으면 omitted.
  injuryRisk?: string;
  // 코치 상의 권고 (마무리 한 줄). 항상 표시.
  coachNote: string;
}

export interface CoachingCause {
  title: string; // 원인 짧은 제목 (예: '받침 팔 힘 부족')
  explanation: string; // 왜 이 원인이 점수에 영향 (1~2문장)
  fix: string; // 이 case 인 경우 연습 방법 (1~2문장)
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

// Phase 12.5 (2026-06-07): 차원별 explanation. 결과 화면 "왜 이 점수인지" 가시화.
// point: backend 산식 source 와 동일 windowing 사용 (dimensions._select_window 공유) —
// line/stability deficit 가 점수 산출과 같은 frames 만 본다. 옵셔널 — 이전 빌드 doc 호환.
// 신 backend 는 빈 {} 라도 항상 emit. baseline 카피는 mode-aware (정은지 비교 mode1 vs
// 절대 지표 기반 mode3). weightPercent 는 정수, 모든 차원 합 = 100 (Largest Remainder).
export interface DimensionExplanation {
  weightPercent: number; // 정수 0~100. 모든 차원의 weightPercent 합 = 100.
  baseline: string; // mode-aware 기준 카피 (한국어)
  deficitSummary: string; // 산식과 동일 source 의 deficit 한 줄. 양호 시 수치 X.
}

// Phase 4 Wave 1 (Plan 04-01) — POSE-03 D-08 (R3 fix 3-way lockstep TS side).
// 합성 어댑터의 public warning enum. 3-way lockstep:
//   · backend/shared/python/sunity_shared/models.py SYNTHESIS_WARNING_CODES frozenset
//   · docs/contract.md §9.8 (Phase 4 신설 2)
//   · 본 TS union
// raw reason ('gemini_api_error' / 'gemini_parse_error' / 'g4_reference_guard' /
// 'exception' / 'invalid_input_shape' / 'model_resolve_failed' 등) 은
// aiSynthesisMeta.debugWarnings 에만 보존되고 본 union 에는 포함하지 않는다
// (HIGH-4 raw ↔ public 분리). UI 가 hasSynthesisWarning(result) 로 읽음.
export type SynthesisWarningCode =
  | 'ai_synthesis_failed'
  | 'ai_synthesis_partial';

// AiSynthesisMeta: result 내부 표시되는 합성 메타 (사용자에겐 블랙박스 D-05).
// R5 fix — 감사 필드 (modelId / modelVersion / promptHash) + cost 카운터 6개.
// 합성 자체가 발생하지 않은 분석은 본 필드를 채우지 않거나 비울 수 있음
// (옵셔널). 백엔드는 always-emit 가 아닌 conditional emit (occlusion 발견 시).
export interface AiSynthesisMeta {
  // 어떤 frame 들에 합성을 시도/적용했는지 (T 인덱스 list).
  synthesizedFrameCount: number;
  // 합성을 시도/적용한 keypoint 이름 list (COCO-17 부분 집합).
  synthesizedJointKeys: string[];
  // 사용한 합성 path. 'none' = 합성 미수행 (skipped 등).
  synthesisPath: 'gemini_view' | 'cylindrical_mesh' | 'none';
  // graceful degrade 발생 여부 — true 시 1차 RTMW 결과 그대로.
  degraded: boolean;
  // 감사 필드 (R5 fix). 후속 회귀 추적 + 버전 관리.
  // 04-02 HIGH-5 (4차 게이트 리뷰): backend payload 보다 좁지 않게 optional 로
  // 선언. normalize() 가 타입 검증 실패 시 undefined 로 두고, 합성 자체가
  // 발생하지 않은 분석 (path='none') 의 누락도 허용한다.
  modelId?: string; // 예: 'gemini-3.5-flash' / 'gemini-3.1-pro-preview'
  modelVersion?: string; // 예: 'v1' (Phase 4 박제 시점 버전 tag)
  promptHash?: string; // OCCLUDED_JOINT_REASONING_PROMPT sha256 앞 16자
  // Cost 카운터 6 (R5 fix). belle pricing visibility 박제 — 04-02 HIGH-5 optional.
  framesConsidered?: number; // 합성 대상 후보 frame 수
  framesSynthesized?: number; // 실제 합성된 frame 수
  geminiCalls?: number; // 호출 횟수
  framesSkipped?: number; // skip 된 frame 수
  framesFailed?: number; // 실패 frame 수
  estCostUsd?: number; // 추정 비용 (USD)
  // Public warning surface (canonical, BLOCKER-3). UI 가 읽는 enum.
  // raw reason 은 debugWarnings 에 분리 보존 — 본 list 는 public enum 만.
  warnings?: SynthesisWarningCode[];
  // Debug-only raw reason 보존 (HIGH-4 — public enum 오염 금지).
  // 예: ['gemini_api_error', 'g4_reference_guard']. UI 에 노출 안 함.
  debugWarnings?: string[];
}

export interface AnalysisResult {
  overallScore: number; // 0~100. mode1=3차원 평균, mode3=절대 차원 평균
  // IPSF 실행 차원 점수 (3차원: angle/line/stability).
  // mode1=3키 / mode3 first=2키 (line/stability — line 생략 가능 시 1키 stability)
  // / mode3 second+=3키 (+ angle 일관성). 표시는 DIMENSION_ORDER 순서로 존재 키만.
  dimensionScores: Partial<Record<ScoreDimension, number>>;
  // Phase 12.5: 차원별 weight/baseline/deficit 설명. 키는 dimensionScores 의 부분 집합.
  // 옵셔널 — 이전 빌드 doc 호환 (없으면 frontend 추가 라인 표시 X).
  dimensionExplanation?: Partial<Record<ScoreDimension, DimensionExplanation>>;
  joints: JointScore[]; // 관절별 (보통 8). 코칭 팁 근거(각도 편차)
  tips: CoachingTip[]; // 상위 3개
  comparison: Mode1Comparison | Mode3Comparison;
  myVideoUrl: string; // 재생용 서명 URL (design.md §8 좌: 내 영상)
  // 박제 (2026-06-06): myVideoUrl 의 S3 sign 은 7일 TTL. 일주일 뒤 mode3 prev
  // 영상 fetch 시 만료 → POST /playback-url 박제 재발급용 S3 key.
  myVideoKey?: string;
  referenceVideoUrl?: string; // mode1 우: 정은지 영상
  // Phase 6 (Plan 06-01) — D-06-B3. 체형 정규화 비교 리포트.
  // Plan 06-02 wiring 에서 backend pipeline 이 채움 (currently nullable).
  bodyComparisonReport?: BodyComparisonReport | null;
  // Phase 8 (Plan 08-01 revised — REVIEWS Cycle 1) — Force Signals umbrella.
  // Plan 08-02 wiring 에서 backend pipeline 이 채움 (currently nullable).
  // Plan 08-00 §9.0 contract (CoordinateSpace / ContactPrimitiveKind /
  // PoleAxisMeasurement / median_torso_length) 위에 박제.
  forceSignalsReport?: ForceSignalsReport | null;
  // Phase 9 (Plan 09-01) — §9.11 ForcePatternInference (D-09-D1 / D-09-U1).
  // Wave 0 = schema only. Wave 1 (Plan 09-02) 가 본체 함수 + canned + pipeline
  // wiring 박제. 본 필드는 Wave 1 wiring 이후 backend pipeline 이 채움.
  // 책임 경계: Phase 11 (CoachCommentHook) 가 findings[].interpretation 위
  // LLM 자연어 풍부화. Phase 12 가 raw 수치 UI 노출. Phase 9 자체는 canned 만.
  forcePatternInference?: ForcePatternInference | null;
  // Phase 12 Wave 0B (Plan 12-01) — §9.12 KeypointReport (D-12-E2 / D-12-U1).
  // 사용자 분석 영상의 keypoint flat 좌표 + axisData polyline + axisMask.
  // Wave 0B = schema only. Wave 1 KeypointOverlay 가 본 필드 소비.
  // mode1 reference overlay 는 별도 `ReferenceMotion.referenceKeypointReport`
  // 에서 직접 read (analysis doc 에 mirror X — H2 iter-4 / Firestore 1 MiB 안전 마진).
  keypointReport?: KeypointReport | null;
  // Phase 4 Wave 1 (Plan 04-01) — POSE-03 D-08 / R3 fix.
  // 합성 메타 — UI 는 hasSynthesisWarning(result) 로 warnings 만 surface.
  // 사용자에겐 블랙박스 (D-05). 합성이 발생하지 않은 분석은 옵셔널 omitted.
  aiSynthesisMeta?: AiSynthesisMeta;
  // Phase 4 Wave 1 (Plan 04-01, R3 fix) — joints3d flat 저장 (RTMW pose-aligned
  // T×17×3). 04-02 가 doc.result.joints3d 를 reshapePose3dData 로 읽음.
  // angles (AnalysisDoc top-level quirk) 와 별개 — joints3d 는 result 내부.
  // Firestore nested-array 금지로 flat (length = joints3dFrames * 17 * 3).
  joints3d?: number[];
  joints3dKeys?: string[]; // COCO-17 17 keypoint 이름 (length 17)
  joints3dFrames?: number; // T
  coordDim?: number; // = 3
  space?: 'rtmw3d' | 'pole_aligned'; // 좌표계 (to_coco17_array → pole_aligned)
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
  videoFormat?: VideoFormat; // 박제 (2026-06-06): playback-url 재발급 시 ext 박제
  // 분석-당시 자가입력 SNAPSHOT (live users/{uid}.bodyProfile 아님 — 결과 화면
  // 재현성, R1). 03-03 result.tsx 가 이 snapshot 을 우선 표시. loading.tsx 가
  // getBodyProfileOnce() (client normalize) 로 기록. painAreas 는 top-level
  // scalar array 라 AnalysisDoc 안에서도 nested-array 위반 없음 (Pitfall 7).
  bodyProfile?: BodyProfile | null;
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

  // Phase 6 (Plan 06-01, D-06-B2) — reference 측 BodyNormalizationProfile.
  // Plan 06-03 백필 (extract_reference_body_profiles.py + seed-reference-body-profile.mjs)
  // 가 채움. nullable — 백필 미완 reference 정합.
  bodyNormalizationProfile?: BodyNormalizationProfile | null;
  // Phase 6 (Plan 06-01, R2 fix round-2 reviews) — reference 측 대표 hold frame
  // keypoints (flat values, nested-array 회피). Plan 06-03 백필이 함께 저장.
  // mode1 + mode3 fallback path 가 본 필드를 fetch 해서 compare_body_profiles
  // 의 source_keypoints 인자로 to_keypoints_array() 변환 후 전달.
  bodyComparisonSourcePose?: BodyComparisonSourcePose | null;

  // Phase 12 Wave 0B (Plan 12-01, R3 iter-2) — mode1 split overlay 의 정은지 측
  // 오버레이 데이터. seed 시점 박제, missing 가능 (구 doc fallback).
  //
  // 의도 분리: `keypointReport` (사용자 분석 결과) vs `referenceKeypointReport`
  // (reference 영상의 keypoint) 의미 혼동 차단. H2 iter-4 — analysis doc 에
  // mirror X (Firestore 1 MiB 안전 마진 + single source-of-truth).
  //
  // UI 의 mode1 split 오버레이 = `analysisDoc.result.keypointReport` (사용자) +
  // `refMotion.referenceKeypointReport` (정은지) 양쪽 read.
  referenceKeypointReport?: KeypointReport | null;

  // Phase 14 (Plan 14-01, SC#2 / D-03) — reference 다운스트림 백필 필드.
  // 14-02/14-03 가 학생 _process 와 SAME sunity_shared 함수를 REFERENCE_V1_FORCE_CONFIG
  // (pinned) 로 거쳐 채운다 (위양성 방지 = reference·학생 동일 계산 경로, D-01).
  // 3-way lockstep: docs/contract.md §3 + 이 인터페이스 + Python source shapes
  // (force_pattern.ForcePatternInference / technique.TechniqueProfile). CLAUDE.md
  // Cross-cutting. 모두 OPTIONAL/nullable — 백필 미완 reference 와 normalize() 정합.
  // Pitfall 5 — T-scaled per-frame array 추가 금지 (40k index-entry 한도).
  //
  // EXTEND joint_expectations (FallbackRecognizer 산출). 채점 line 차원의 기준.
  // technique.TechniqueProfile.joint_expectations 형태 (JOINT_KEYS → EXTEND/BENT_OK/CONTACT).
  techniqueProfile?: {
    name: string;
    category: string;
    jointExpectations: Record<string, string>;
  } | null;
  // ForceDirectionPattern (infer_force_direction_pattern 산출). Phase 9 §9.11 의
  // ForcePatternInference shape 재사용. nullable.
  forceDirectionPattern?: ForcePatternInference | null;
  // D-03 / SC#4 — 단일시점 v1 reference 는 모두 captureViews=1. 다각도 부재 시
  // confidence 를 낮게 표기하기 위한 플래그 (RESEARCH A5 / Open-Q4 default).
  captureViews?: number;
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

// ── Phase 8 Coordinate/Scale Contract (Plan 08-00 신설, 2026-06-09) ────────
// REVIEWS Cycle 1 R1 / R2 / R3 blocker 해소.
//
// Python lockstep:
//   backend/shared/python/sunity_shared/analysis/pole_geometry.py
//     PoleLine2D / PoleAxisMeasurement / CoordinateSpace / ContactPrimitiveKind
//   backend/shared/python/sunity_shared/analysis/body_scale.py
//     median_torso_length
// docs/contract.md §9.0 Coordinate/Scale Contract.
//
// 박제 위치: PoleAxis 직후, BodyNormalizationProfile 직전. Plan 08-01 의
// ForceSignalsReport schema 가 본 contract 위에 박제.

/**
 * distance metric 의 좌표공간 enum (R1 + Suggestions §1).
 *   image_2d:     image 평면 normalized 0~1 좌표 (Phase 1 Hough 검출 공간)
 *   pole_aligned: PoleAxis 정렬 3D 좌표 (Keypoint3DAligned)
 *   world_3d:     metric world 3D 좌표 (Keypoint3D)
 *   unavailable:  계산 불가 — caller 가 numeric 필드 null + warning 박제
 */
export type CoordinateSpace = 'image_2d' | 'pole_aligned' | 'world_3d' | 'unavailable';

/**
 * 12 contact point 의 본질적 분류 (R3 blocker 해소).
 *   keypoint:     COCO-17 직접 가용 keypoint (left_hand 등 10 point)
 *   segment:      두 keypoint 의 mid-segment 거리 (left/right_inner_thigh 2 point)
 *   region_proxy: 다중 keypoint midpoint region proxy (hip 1 point)
 */
export type ContactPrimitiveKind = 'keypoint' | 'segment' | 'region_proxy';

/**
 * image 평면 (normalized 0~1) 의 폴 축 직선 (R1).
 *
 * Phase 1 HoughPoleDetector 가 이미 image 평면 검출 — 본 interface 는 그 표현
 * contract. axis distance 산출 = 점-직선 거리 공식 (image 2D).
 *
 * Python lockstep: pole_geometry.PoleLine2D (frozen dataclass).
 */
export interface PoleLine2D {
  /** 직선 위의 한 점 (x, y), image normalized 0~1. */
  pointImage: [number, number];
  /** 직선 방향 단위벡터 (dx, dy), norm ≈ 1.0. */
  directionImage: [number, number];
  /** 검출 신뢰도 [0.0, 1.0]. */
  confidence: number;
  /** 'detected' = Hough 성공, 'vertical_fallback' = 수직 가정. */
  source: 'detected' | 'vertical_fallback';
}

/**
 * axis_3d (PoleAxis, direction-only) + line (image 2D position) 묶음 (R1).
 *
 * invariant: line=null ↔ coordinateSpace='unavailable'. Python __post_init__
 * 가 강제. line 미가용 시 caller 가 axis distance 필드 null + warning
 * 'pole_line_missing' 박제.
 *
 * Python lockstep: pole_geometry.PoleAxisMeasurement.
 */
export interface PoleAxisMeasurement {
  /** Phase 1 PoleAxis (direction-only) — 본체 변경 0. */
  axis3d: PoleAxis;
  /** image 2D 선 (fallback 시 null). */
  line: PoleLine2D | null;
  /** distance 산출 좌표공간. line=null 시 'unavailable' 강제. */
  coordinateSpace: CoordinateSpace;
  /** video-level (Phase 1 D-10) 시 null. */
  frameIndex: number | null;
}

// ── Phase 8 Force Signals (Plan 08-01 revised — REVIEWS Cycle 1) ──────────
// Plan 08-00 박제 §9.0 contract (CoordinateSpace / ContactPrimitiveKind /
// PoleAxisMeasurement) 위에 박제. ForceSignalsReport = BodyLineTiltMetric +
// StabilityMetric + ContactStabilityMetric + PhaseBoundary 4종 metric umbrella.
//
// Python lockstep (Plan 08-02 신설 후 활성화 예정):
//   backend/shared/python/sunity_shared/analysis/force_signals.py
//   re-export via backend/shared/python/sunity_shared/models.py
// docs/contract.md §9 ForceSignalsReport.
//
// REVIEWS Cycle 1 반영:
//   R1/R2: BodyLineTiltMetric 의 distance 필드 nullable + coordinateSpace +
//          scaleDenominator 동행.
//   R3:    ContactStabilityMetric = evidence-with-confidence (estimatedStable
//          nullable, distanceToPoleNorm, nearPoleRatio, lostNearPoleAtMs,
//          measurementKind 박제).
//   R4:    PhaseBoundary 에 preflightLabelGatePassed 신설 (nullable).
//   R5:    StabilityMetric.jerkUnit='deg_per_sec_cubed' — FPS 정규화 박제.

/** 5단계 motion phase (research 02 §6/§7 정합). */
export type MotionPhase = 'entry' | 'lock' | 'transition' | 'final_shape' | 'hold';

/** 이탈 방향 — 좌표공간 (image_2d 시 image 평면) 기준. */
export type DeviationDirection =
  | 'up'
  | 'down'
  | 'left'
  | 'right'
  | 'outward'
  | 'inward'
  | 'unknown';

/** severity = 측정값 자체 크기 (low/medium/high). confidence 와 별 차원. */
export type SeverityLevel = 'low' | 'medium' | 'high';

/** confidence = 측정값 신뢰도. (research 02 finding-with-confidence 정합) */
export type MetricConfidence = 'low' | 'medium' | 'high';

/**
 * 12 contact point enum (docs §9.0.7 12 분류 표 source).
 * Plan 08-01 contact_points.yaml 박제 시 본 enum 의 name 사용.
 */
export type ContactPoint =
  | 'left_hand'
  | 'right_hand'
  | 'left_inner_thigh'
  | 'right_inner_thigh'
  | 'left_knee'
  | 'right_knee'
  | 'left_foot'
  | 'right_foot'
  | 'left_ankle'
  | 'right_ankle'
  | 'hip'
  | 'unknown';

/**
 * 5단계 motion-phase 경계 (Layer 1 휴리스틱 + Layer 2 Gemini key_moments 합성).
 *
 * REVIEWS R4 박제 — preflightLabelGatePassed 신설 nullable:
 *   null  = gate 미실행 (default — preflight CSV 채워지지 전).
 *   true  = gate PASS (≥80%, Layer 1 confidence='medium' 승급).
 *   false = gate FAIL (Layer 1 confidence='low' 강제 + warning
 *           'preflight_label_gate_failed').
 */
export interface PhaseBoundary {
  phase: MotionPhase;
  startFrameIdx: number;
  endFrameIdx: number;
  startMs: number;
  endMs: number;
  confidence: MetricConfidence;
  source: 'heuristic' | 'gemini_assisted' | 'heuristic_fallback';
  /** REVIEWS R4 — pre-flight 25-timestamp label gate 결과. nullable default. */
  preflightLabelGatePassed: boolean | null;
}

/**
 * Axis deviation metric per phase (Phase 8.1, 2026-06-09).
 * Phase 8.1 distance hard break — IPSF Code of Points 에 글로벌 distance 항목 부재
 * (NotebookLM citation 9, Aerial Pole CoP 2024-2025 Page 87 Glossary).
 * tilt-only metric. shoulderTilt / hipTilt = degrees, rotation-only / origin-invariant.
 * severity = max(shoulderTilt severity, hipTilt severity) per Wave 1 thresholds.
 *
 * Wave 0 transitional: shoulderTilt/hipTilt=null + severity='low' + warning
 * 'phase_8_1_wave_0_transitional'. compute_force_signals umbrella 가 본 warning
 * 검출 시 top-level warning 'axis_metric_transitional' 동행 박제 (Wave 2
 * production sweep 게이트 신호).
 *
 * naming history (C-MH1 resolved 2026-06-12): renamed from prior name
 * AxisDeviationMetric → BodyLineTiltMetric — tilt-only 의미 정합 (Phase 8.1
 * follow-up rename plan).
 *
 * per D-01.
 */
export interface BodyLineTiltMetric {
  phase: MotionPhase;
  /** degrees, rotation-only / origin-invariant. Wave 0 stub default null. */
  shoulderTilt: number | null;
  /** degrees, rotation-only / origin-invariant. Wave 0 stub default null. */
  hipTilt: number | null;
  severity: SeverityLevel;
  confidence: MetricConfidence;
  warnings: string[];
}

/**
 * 흔들림 metric — phase 별 측정.
 *
 * REVIEWS R5 박제:
 *   - jerkScore 단위 = deg/sec^3 (NOT deg/frame^3). FPS-normalized.
 *     Plan 08-02 의 _compute_jerk 가 dt=1/fps 정규화 강제 — 9 fps vs 18 fps
 *     동일 값 보장.
 *   - jerkUnit='deg_per_sec_cubed' 필드로 단위 contract 명시.
 *
 * jitterScore 단위 = deg (frame inter median wobble, unchanged from Plan 08-01 v1).
 */
export interface StabilityMetric {
  phase: MotionPhase;
  /** degrees (frame inter median wobble). dimensions.stability_wobble() 박제. */
  jitterScore: number;
  /** deg/sec^3 (FPS-normalized 3차 미분). */
  jerkScore: number;
  /** jerk 단위 contract — REVIEWS R5. */
  jerkUnit: 'deg_per_sec_cubed';
  /** hold phase 안 stability score (0~100). hold 외 phase 시 null. */
  holdStabilityScore: number | null;
  unstableBodyParts: string[];
  severity: SeverityLevel;
  confidence: MetricConfidence;
  warnings: string[];
}

/**
 * 접촉점 안정성 metric — (contact_point, phase) 별 측정.
 *
 * REVIEWS R3 박제 (evidence-with-confidence, NOT boolean truth):
 *   - estimatedStable: boolean | null — evidence 부족 시 null.
 *   - distanceToPoleNorm: number | null — observed_torso_length 정규화.
 *   - nearPoleRatio: number | null — phase 안 distance <= threshold frame 비율.
 *   - lostNearPoleAtMs: number | null — v1 의 lostContactAtMs 명칭 변경 (boolean
 *     truth 가 아닌 distance evidence 박제 정합).
 *   - measurementKind: 산출 방식 (Plan 08-00 ContactPrimitiveKind). motion_id 미인식 시 null.
 *   - coordinateSpace: distance 산출 좌표공간.
 */
export interface ContactStabilityMetric {
  phase: MotionPhase;
  contactPoint: ContactPoint;
  /** Plan 08-00 §9.0.2 ContactPrimitiveKind. motion_id 미인식 시 null. */
  measurementKind: ContactPrimitiveKind | null;
  /** evidence 부족 (line/scale 미가용 등) 시 null. */
  estimatedStable: boolean | null;
  distanceToPoleNorm: number | null;
  nearPoleRatio: number | null;
  /** v1 의 lostContactAtMs 명칭 변경 (REVIEWS R3 evidence 박제 정합). */
  lostNearPoleAtMs: number | null;
  coordinateSpace: CoordinateSpace;
  severity: SeverityLevel;
  confidence: MetricConfidence;
  warnings: string[];
}

/**
 * Phase 8 산출 umbrella — AnalysisResult.forceSignalsReport 로 저장.
 *
 * Phase 9 의 inferForceDirectionPattern + 실패 원인 후보 카드 의 입력 신호.
 * Plan 08-00 §9.0 contract 위에 박제 (CoordinateSpace / ContactPrimitiveKind /
 * PoleAxisMeasurement / median_torso_length).
 *
 * 20 warning code enum (docs §9.8):
 *   기존 13: occlusion_high_in_phase / layer2_unavailable /
 *           layer_disagreement_minor / layer_disagreement_major /
 *           layer2_call_failed / motion_unrecognized /
 *           motion_unrecognized_layer1_only / abnormal_release_during_hold /
 *           partial_motion_video / video_too_short / heavy_occlusion /
 *           entry_not_detected / all_frames_unreliable.
 *   Cycle 1 신설 6: pole_line_missing / scale_unavailable /
 *           preflight_label_gate_failed / fps_normalization_applied /
 *           contact_evidence_only / coordinate_space_unavailable.
 *   Cycle 2 신설 1: preflight_gate_pending (gate 미실행 default).
 */
export interface ForceSignalsReport {
  version: string;
  overallConfidence: MetricConfidence;
  warnings: string[];
  phaseBoundaries: PhaseBoundary[];
  axisMetrics: BodyLineTiltMetric[];
  stabilityMetrics: StabilityMetric[];
  contactMetrics: ContactStabilityMetric[];
}

// ── Phase 9 §9.11 ForcePatternInference (D-09-D1 / D-09-U1) ─────────────
//
// Source contract: docs/contract.md §9.11 + backend force_pattern.py (frozen dataclass).
// Phase 9 = canned KO only; Phase 11 가 LLM 자연어 풍부화. Phase 12 가 raw 수치 노출.
//
// Wave 0 (Plan 09-01) = TS interface + Python frozen dataclass + docs §9.11 +
// Firestore scoped validator + frontend null-guard 단일 atomic commit.
// Wave 1 (Plan 09-02) = `infer_force_direction_pattern` 본체 함수 + 18 canned 본문 +
// pipeline `_process` wiring.

export type ForceDirectionPattern =
  | 'pull'
  | 'push'
  | 'brace'
  | 'rotate'
  | 'release'
  | 'unknown';

export type ForceSourceSignal =
  | 'axis_tilt'
  | 'pelvis_drop'
  | 'late_contact'
  | 'high_jitter'
  | 'high_jerk'
  | 'abnormal_release';

export type ForcePatternModeContext = 'mode1' | 'mode3_first' | 'mode3_progress';

/**
 * Phase 9 Top-3 finding 카드 1건 (D-09-D1 — 8 필드).
 *
 * Python lockstep: backend/shared/python/sunity_shared/analysis/force_pattern.py
 *   ForcePatternFinding (frozen dataclass + __post_init__ validator).
 * docs lockstep: docs/contract.md §9.11.2.
 */
export interface ForcePatternFinding {
  pattern: ForceDirectionPattern;
  phase: MotionPhase;
  sourceSignal: ForceSourceSignal;
  /** EN 1 sentence — LLM input 용 (debug + Phase 11 풍부화 source). */
  reason: string;
  /** KO canned — D-09-D2 18 mapping, '가능성' 언어 (D-09-D3 grep gate). */
  interpretation: string;
  /** [0, 1] — D-09-A5 base × phase_metric_confidence_factor (motion_id boost 후). */
  confidence: number;
  /** 부위 키워드 (코어 / 고관절 / 광배 / 내전근 / null). */
  jointHint: string | null;
  /** signal-specific (예: 'axis_signal_unavailable'). list[str] only. */
  warnings: string[];
}

/**
 * Phase 9 추론 layer 의 단일 산출 (D-09-D1 — 5 필드).
 *
 * Firestore 저장 경로: `users/{uid}/analyses/{analysisId}.result.forcePatternInference`.
 * `_validate_force_pattern_inference` scoped validator 가 nested-array 차단.
 */
export interface ForcePatternInference {
  /** "1.0" 초기 (non-empty). */
  version: string;
  /** Top-3 cap — length [0, 3] (D-09-B4 fabrication 금지). */
  findings: ForcePatternFinding[];
  /** 0 finding 시 'low' + warning. */
  overallConfidence: MetricConfidence;
  /** pipeline `_process` 산출 (D-09-D6). */
  modeContext: ForcePatternModeContext;
  /** umbrella (예: 'no_significant_force_pattern_signal', 'phase_unavailable_for_inference',
   *  'axis_signal_unavailable'). */
  warnings: string[];
}

// ── Phase 12 §9.12 KeypointReport (D-12-E2 / D-12-U1) ────────────────────
//
// Source contract: docs/contract.md §9.12 + backend keypoint_frame.py
// (frozen dataclass).
// Wave 0B (Plan 12-01) = TS interface + Python frozen dataclass + docs §9.12 +
// Firestore scoped validator + frontend null-guard 단일 atomic commit (Phase 9
// D-09-U1 1:1 mirror).
// Wave 1+ = KeypointOverlay 컴포넌트 + mode1 split overlay.

/**
 * 8 body keypoint enum (R11 — axis 제외, axisData 별도 field).
 * `left_hand` / `right_hand` 는 COCO-17 의 `left_wrist` / `right_wrist` 매핑.
 */
export type KeypointName =
  | 'left_shoulder'
  | 'right_shoulder'
  | 'left_hip'
  | 'right_hip'
  | 'left_knee'
  | 'right_knee'
  | 'left_hand'
  | 'right_hand';

/**
 * Phase 12 신설 — KeypointOverlay 소비.
 *
 * 10 필드 (R10 + R7 iter-2 정합):
 *   - 8 body keypoint flat (T × 8 × 2) — `data`
 *   - axisData polyline (T × 3 × 2, shoulder_mid / hip_mid / knee_mid?,
 *     finite only — NaN 영구 0회, R7 iter-2)
 *   - axisMask (T × 3 bool, knee_mid 미가용 frame 은 `mask[2] = false`
 *     → UI 가 polyline 2-point 만 그림)
 *
 * Python lockstep: backend/shared/python/sunity_shared/analysis/keypoint_frame.py
 *   `KeypointReport` (frozen dataclass + __post_init__ validator).
 * docs lockstep: docs/contract.md §9.12.
 *
 * R1/R2/R3/R6/R7 Codex 리뷰 2026-06-10 정합.
 *
 * Firestore 저장 경로: `users/{uid}/analyses/{analysisId}.result.keypointReport`
 * (`_validate_keypoint_report` scoped validator 가 nested-array 차단).
 */
export interface KeypointReport {
  /** "1.0" 초기 (non-empty). */
  version: string;
  /** 8 body keypoint name (R11 — axis 제외). */
  joints: KeypointName[];
  /** T (>= 0). */
  frames: number;
  /** 영상 frame rate (> 0). R3 — default 제거, 운영 값 9.0. */
  fps: number;
  /** flat T × joints.length × 2 — finite only (H3 iter-4). */
  data: number[];
  /** flat T × joints.length — finite + [0, 1] (R6 visibility source). */
  confidence: number[];
  /** length T, item ∈ {'high','medium','low'}. */
  reliability: ReadonlyArray<'high' | 'medium' | 'low'>;
  /**
   * R2 + R7 iter-2 — 별도 polyline (shoulder_mid / hip_mid / knee_mid?).
   * flat T × 3 × 2 — finite only (NaN 영구 0회). knee_mid 미가용 frame 은
   * (0.0, 0.0) placeholder.
   */
  axisData: number[];
  /**
   * R7 iter-2 — knee_mid 가용 여부 bool.
   * flat T × 3 — UI 가 mask 참조해서 polyline 2-point or 3-point 분기.
   */
  axisMask: boolean[];
  /** signal-specific (예: 'axis_signal_unavailable'). list[str] only. */
  warnings: string[];
}

// ──────────────────────────────────────────────────────────────────────────

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
  /**
   * torso-relative proportion heuristic — 절대 키가 아니라 torso 길이 대비 사지 비율.
   * 산식: `estimatedHeightScale = (armScale + legScale + 1.0) / 3`.
   * Phase 6 coarse normalizer hint 로만 사용.
   * Contract: finite + strictly positive (>0). Python __post_init__ ValueError on violation (MEDIUM-2 v5).
   */
  estimatedHeightScale: number;
  /**
   * torso-relative proportion heuristic — torso 길이 대비 팔 segment 비율
   * (1.0 = torso 와 동일 길이). Phase 6 coarse normalizer hint 로만 사용.
   * Contract: finite + strictly positive (>0). Python __post_init__ ValueError on violation (MEDIUM-2 v5).
   */
  armScale: number;
  /**
   * torso-relative proportion heuristic — torso 길이 대비 다리 segment 비율.
   * Phase 6 coarse normalizer hint 로만 사용.
   * Contract: finite + strictly positive (>0). Python __post_init__ ValueError on violation (MEDIUM-2 v5).
   */
  legScale: number;
  /**
   * 몸통 정규화 단위 (self-reference 1.0).
   * Contract: finite + strictly positive (>0). Python __post_init__ ValueError on violation (MEDIUM-2 v5).
   */
  torsoScale: number;
  /**
   * 어깨너비 / 골반너비 비율 (체형 분류 단서).
   * Contract: finite + strictly positive (>0). Python __post_init__ ValueError on violation (MEDIUM-2 v5).
   */
  shoulderHipRatio: number;
  /** 측정 신뢰도 [0.0 ~ 1.0]. RTMW score 또는 측정기 자체 신뢰도. fallback path = 0.0. */
  confidence: number;
  /**
   * 측정 품질 이슈 enum (5종, Phase 2 BODY-01 박제). Phase 11 coach_writer 가 한국어 카피로 번역.
   *   - 'low_keypoint_confidence': 평균 confidence 가 0.4 미만 (영상 품질).
   *   - 'occluded_endpoint': endpoint conf<0.5 in >60% frame (가림).
   *   - 'insufficient_frames': frame<30 (짧은 클립, fallback 진입).
   *   - 'asymmetric_landmark_count': 좌우 valid frame 차이>30% (한쪽 가림).
   *   - 'pose_too_inverted': 인버트 자세 frame>50% (image y-down 좌표 직접 비교,
   *     PoleAxis.axisVector 부호와 독립적 — MEDIUM-3 v5).
   * 기본값 [].
   */
  warnings: string[];
}

/**
 * Phase 6 (2026-06-08, Plan 06-01) — D-06-B3 박제.
 * BodyComparisonReport family + BodyComparisonSourcePose (R2 fix round-2 reviews).
 *
 * Python lockstep:
 *   backend/shared/python/sunity_shared/analysis/body_normalizer.py
 *     BodyComparisonReport / BodyComparisonFinding / ScaleProfile /
 *     BodyComparisonSourcePose / ComparisonType
 * 변경 시 양쪽 + docs/contract.md §8 + §8.2 동시 갱신 (CLAUDE.md Cross-cutting).
 *
 * W1 (2026-06-08): 3 ComparisonType (mode1 / mode3_first / mode3_progress).
 *                  Gemini fallback 신호는 sibling boolean `usedReferenceFallback`.
 * C14 (2026-06-08 reviews): deficit code 'pose_reliability_low' (IPSF
 *                  judge-observation 'bad_angle' 과 의미 다름 — divergence docs §8.1).
 * R2 (2026-06-08 round-2): BodyComparisonSourcePose 신규 — Firestore reference
 *                  컬렉션 영속, flat values (nested-array 회피).
 * R8 (2026-06-08 round-2): backend compare_body_profiles extra_warnings 파라미터.
 * R9 (2026-06-08 round-2): 5 IPSF + Sunity pose_reliability_low. poor_transitions
 *                  v1.5 deferred (Phase 8 jerk/jitter 통합).
 */

/** 3 ComparisonType (W1 박제 — 4번째 케이스 금지. Gemini fallback 은 usedReferenceFallback boolean 으로 표현). */
export type ComparisonType = 'mode1' | 'mode3_first' | 'mode3_progress';

/**
 * 프로/수강생 체형 scale ratio (D-06-A3 — 5 필드 + apply 플래그).
 * 모든 numeric 필드 finite + strictly positive.
 */
export interface ScaleProfile {
  /** 전체 키 비율 (target/source). */
  estimatedHeightScale: number;
  /** 팔 길이 비율. */
  armScale: number;
  /** 다리 길이 비율. */
  legScale: number;
  /** 몸통 길이 비율. */
  torsoScale: number;
  /** 어깨너비/골반너비 비율 — 점수 차원 미적용 (D-06-A3, [[scoring-dimensions-ipsf]]). */
  shoulderHipRatio: number;
  /** 폭 보정 적용 여부 (foreshortening 시 false, W6). */
  shoulderHipRatioApplied: boolean;
}

/**
 * 단일 IPSF GeometricCriterion deficit (R9 fix: 5 IPSF + Sunity pose_reliability_low).
 *
 * deficitCode enum 6종 — '7 deficits' 옛 표현 X. poor_transitions v1.5 deferred:
 *   - 'knee_toe_alignment' (-0.2): kneecap → toe 180° 직선 정렬 실패
 *   - 'clean_lines' (-0.2): 팔/다리 fully extended 미충족
 *   - 'extension' (-0.2): 척추/목 라인 굽음
 *   - 'posture' (-0.2): 좌우 어깨 z 깊이 차이 (rounded shoulders)
 *   - 'body_placement' (-0.2): 폴 대비 잘못된 위치
 *   - 'pose_reliability_low' (-0.5): C14 fix — 구 'bad_angle' rename.
 *     본 시스템의 pose-estimation confidence frame 비율 측정. IPSF Page 21 의
 *     'bad angle' (judge-observation deduction) 과 의미 다름 (docs §8.1).
 *
 * body_type_adjusted: true = 정규화 좌표에서 측정, false = raw 좌표.
 * 체형 ratio 를 deductionScore 에 직접 곱하지 않음 (Notebook §3.3 IPSF 절대).
 */
export interface BodyComparisonFinding {
  deficitCode: string;
  jointKey?: string | null;
  measuredValue: number;
  deductionScore: number;
  confidence: number;
  bodyTypeAdjusted: boolean;
  // ── Phase 7 (Plan 07-01, 2026-06-08) 신설 4 필드 — D-07-A1 + D-07-C1 ──
  // iteration 2 WR-01 fix: backend measure_ipsf_absolute_deficits 의 6 호출
  // 위치는 placeholder 'uncertain' (fail-safe). Plan 02 classify_findings 재할당.
  /** 분류 결과 — D-07-A1 룰. 'body_type_allowed' = 체형 허용, 'needs_adjustment'
   * = 개선 필요, 'uncertain' = AI 확신 부족. */
  category: 'body_type_allowed' | 'needs_adjustment' | 'uncertain';
  /** v1 = 'hold' 단일 (D-07-C1). v2 (Phase 8 또는 Plan 13) 에서
   * 'entry'/'lock'/'transition'/'final_shape'/'release' 확장. nullable. */
  phase?: string | null;
  /** Korean canned interpretation — Phase 11 LLM 풍부화 입력 source. CR-01 fix
   * fallback path 시 null. */
  bodyTypeInterpretation?: string | null;
  /** Korean canned recommendation — mode prefix prepended. CR-01 fix fallback
   * path 시 unprefixed 단일 문장. */
  recommendation?: string | null;
}

/**
 * R2 fix (2026-06-08 round-2). reference 측 대표 hold frame keypoints
 * (17 joint × 4 channel x/y/z/confidence). Firestore reference 컬렉션의
 * `bodyComparisonSourcePose` 필드에 영속.
 *
 * nested-array 회피 위해 values 는 flat float array
 * (length = 4 × jointKeys.length, COCO-17 의 경우 68).
 * reshape 책임은 backend BodyComparisonSourcePose.to_keypoints_array().
 *
 * Plan 06-02 mode1 + mode3 fallback path 가 fetch 해서 backend
 * compare_body_profiles 의 source_keypoints 인자로 전달.
 */
export interface BodyComparisonSourcePose {
  jointKeys: string[];
  /** flat float array. length = 4 × jointKeys.length. 순서 [x_0, y_0, z_0, c_0, ...]. */
  values: number[];
  frameIndex: number;
  /** mid_shoulder ↔ mid_hip 픽셀 거리 (scale anchor). */
  torsoPx: number;
  /** 0~1 — 대표 frame 의 평균 keypoint confidence. */
  confidence: number;
  /** unix ms timestamp. */
  measuredAt: number;
}

/**
 * 체형 정규화 비교 리포트 (D-06-B3 통합 schema + W1 3 ComparisonType).
 *
 * 9 warning enum (WR-02 fix — target_torso_px_missing 추가):
 *   - 'low_confidence_normalization_off' / 'foreshortening_off' /
 *     'shoulder_hip_ratio_off' / 'temporal_variance_high' / 'spatial_dispersion_high' /
 *     'reference_profile_missing' / 'fallback_reference_not_found' /
 *     'reference_source_pose_missing' / 'target_torso_px_missing'
 *
 * usedReferenceFallback (W1): Gemini fallback 신호 (mode3_first 에서만 true 허용).
 *                            comparisonType 자체는 'mode3_first' 유지.
 */
export interface BodyComparisonReport {
  comparisonType: ComparisonType;
  /** 0.0~1.0 — D-06-U1 confidence-tiered hybrid 의 게이트. */
  bodyNormalizationConfidence: number;
  /** 정규화 OFF 시 null. */
  scaleProfile?: ScaleProfile | null;
  findings: BodyComparisonFinding[];
  warnings: string[];
  referenceMotionId?: string | null;
  referenceAthleteName?: string | null;
  /** mode3_progress 일 때만. null 시 backend 가 ValueError. */
  previousAnalysisId?: string | null;
  /** W1: Gemini fallback 신호 (mode3_first 에서만 true). default false. */
  usedReferenceFallback: boolean;
  // ── Phase 7 (Plan 07-01, 2026-06-08) 신설 2+1 필드 — D-07-B3 + WR-03 fix ──
  /** body_type_allowed 분류 finding 의 카피 aggregate. 결과 화면 "체형 허용 차이"
   * 박스 source. */
  doNotOverCorrect: string[];
  /** needs_adjustment + uncertain 분류 finding 의 카피 aggregate. 결과 화면
   * "개선 필요" 박스 source (Decision 1 — uncertain 통합). */
  recommendedFocus: string[];
  /** WR-03 fix — recommendedFocus[] 가 빈 list 일 때 단일 fallback 카피. Phase
   * 12 가 빈 박스 회피용으로 활용. backend copy_templates._EMPTY_FOCUS_FALLBACK
   * 박제. */
  recommendedFocusFallback?: string | null;
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
