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
// 묶음 라벨이 사용자에게 불명확. "팔다리 펴기" 풀어 표현).
// quick-260705-o0s 개명: angle '각도 정확도' → '각도 유사도' (측정 실체 = DTW
// 유사도 — 진실한 개명), stability '동작 안정성' → '안정성'. 표시 문자열만 변경,
// 계약 키(ScoreDimension) 무접촉 — contract.md 미러 대상 아님. " (참고)" 접미는
// 결과 화면 렌더에서만 붙인다 (다른 소비처 오염 금지).
export const DIMENSION_LABEL_KO: Record<ScoreDimension, string> = {
  angle: '각도 유사도',
  line: '팔다리 펴기',
  stability: '안정성',
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
//
// Phase 13-C (2026-06-16, [[section-dual-coach-report]]): 출처별 섹션 듀얼 coach.
// 형상 불변(3-way lockstep) — 출처는 별도 데이터(source 필드)가 아니라 백엔드
// 섹션 조립 결과로만 표현. 자세히 모달은 4개 "기능 라벨" 섹션으로 세로 스택 렌더하며
// AI/벤더명(Gemini/Cerebras)은 절대 노출하지 않는다:
//   원인        = causes[].title + causes[].explanation  (Gemini 조립)
//   교정 처방    = causes[].fix                            (Cerebras 조립)
//   부상 위험    = injuryRisk                              (Cerebras 조립, 옵셔널)
//   강사 확인    = coachNote                               (Gemini 조립)
// 한쪽 writer 실패 시 다른 writer 가 그 섹션을 cross-fill (빈 섹션 0), 둘 다 실패
// 시 detail2 생략 → 수치 폴백.
export interface CoachingTipDetail {
  // 원인 후보 3~5개. 각 case 별 진단(원인) + 처방(교정 처방).
  // 사용자 input = 정확한 원인 모르므로 "이런 경우 ..." 식으로 다중 제시.
  causes: CoachingCause[];
  // 부상 위험 경고 (해당 시). LLM 판단 — 없으면 omitted (섹션 자체 생략).
  injuryRisk?: string;
  // 강사 확인 — 코치 상의 권고 (마무리 한 줄). 항상 표시.
  coachNote: string;
}

export interface CoachingCause {
  title: string; // 원인 짧은 제목 (예: '받침 팔 힘 부족')
  explanation: string; // 왜 이 원인이 점수에 영향 (1~2문장)
  fix: string; // 이 case 인 경우 연습 방법 (1~2문장)
}

// Phase 13 (Plan 13-A, PERS-03): 보완 운동 1건. 분석 결과(힘 패턴 findings +
// 통증부위)에 맞춰 backend exercise_map.map_exercises 가 산출 → Firestore
// result.recommendedExercises (3~5 subset). plain camelCase scalar — nested 금지
// (firestore-nested-array-flat / _validate_recommended_exercises scoped validator).
// 3-way lockstep: 본 interface ↔ backend models.py recommendedExercises 계약 ↔
// docs/contract.md §4 (CoachingCause 모양 정합). 전체 라이브러리 browse 는 별도
// app/src/data/correctiveExercises.ts (backend fixture byte-copy mirror).
export interface RecommendedExercise {
  name: string; // 운동명 (예: 'Farmer's Walk')
  setsReps: string; // 세트/반복 (예: '왕복', '8~12회')
  purpose: string; // 한 줄 목적 (왜 이 운동인지)
  sourceRef?: string; // 출처 cite (예: 'NotebookLM e688fb4e [1]'). 옵셔널.
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
  // Phase 19 ITER-4 HIGH-1 — Mode1 의 scoringBasis 는 항상 reference_motion (정은지
  // reference 각도와 실제 비교). OPTIONAL (legacy doc 호환) — 신규 doc 은 build_mode1 이
  // 항상 채운다. Mode3Comparison 에는 이 값이 없음 (reference_motion 은 Mode1 전용).
  scoringBasis?: 'reference_motion';
  scoringBasisLabel?: string; // 사용자 표시용 한국어 라벨 (예: '정은지 측정 각도 기준 비교')
}

export interface Mode3Comparison {
  mode: 'mode3';
  isFirst: boolean; // 첫 분석이면 절대값만 (비교 대상 없음)
  previousAnalysisId?: string;
  // 발전(progress) = 절대 차원(라인/안정성)의 이전 대비 증감(±). isFirst면 없음.
  // '몇 % 일치'가 아니라 발전을 보여주는 게 mode3 의 핵심.
  deltaFromPrevious?: Partial<Record<ScoreDimension, number>>;
  // Phase 19 TRUST-03 — 실제 채점 SOURCE 라벨 (Mode3 4-value enum). OPTIONAL (legacy 호환).
  //   reference_free_absolute              : first + 미등록 동작 → 절대트랙(line+stability)
  //   recognized_motion_absolute           : first + 등재 동작 → 절대트랙 (first 는 reference 각도 미사용)
  //   previous_analysis_plus_absolute      : progress + 등재 → 이전 영상 각도 일관성 + 절대트랙
  //   previous_analysis_plus_reference_free_absolute : progress + 미등록 → composite (HIGH-3 lossy 금지)
  // reference_motion 은 Mode1 전용이라 이 union 에 없음 (first 는 reference motion 비교가 아님).
  scoringBasis?:
    | 'reference_free_absolute'
    | 'recognized_motion_absolute'
    | 'previous_analysis_plus_absolute'
    | 'previous_analysis_plus_reference_free_absolute';
  scoringBasisLabel?: string; // 사용자 표시용 한국어 라벨 (정확한 채점 source 노출)
  // Phase 30 (30-CONTEXT D-04) — mode3 인식 동작 데이터 적립(이번 phase 화면 미소비,
  // Phase 16이 소비). 부재(legacy doc/인식 실패)=앱은 '내 기록' 단일 그룹. Python
  // lockstep: assemble.build_mode3 + models.py + docs/contract.md §4와 동시 갱신.
  recognizedMotionId?: string;
  recognizedMotionName?: string;
}

// Phase 12.5 (2026-06-07): 차원별 explanation. 결과 화면 "왜 이 점수인지" 가시화.
// point: backend 산식 source 와 동일 windowing 사용 (dimensions._select_window 공유) —
// line/stability deficit 가 점수 산출과 같은 frames 만 본다. 옵셔널 — 이전 빌드 doc 호환.
// 신 backend 는 빈 {} 라도 항상 emit. baseline 카피는 mode-aware (정은지 비교 mode1 vs
// 절대 지표 기반 mode3). weightPercent 는 정수, 모든 차원 합 = 100 (Largest Remainder).
export interface DimensionExplanation {
  weightPercent: number; // 정수 0~100. 기여 차원(angle/line)의 weightPercent 합 = 100. stability=0.
  baseline: string; // mode-aware 기준 카피 (한국어)
  deficitSummary: string; // 산식과 동일 source 의 deficit 한 줄. 양호 시 수치 X.
  // Phase 19 D-01 — 해당 차원이 종합점수에 기여하는지 (overall = min-of-core(angle/line)).
  // 옵셔널: 미존재(legacy doc)→ true (옛 overall 은 stability 포함). 신 backend 항상 emit,
  // 비기여(stability)=false. weightPercent 도 contributesToOverall=false 면 0.
  contributesToOverall?: boolean;
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

// Phase 20 SCORE-08 (TRUST-08) + Phase 24 (ND-01, 밴드 제거) — 비전 채점 audit (discriminated union).
// status 가 채점 실행을 증명한다 (부재 ≠ 실행, HIGH-1). status='applied' 시 severity +
// tallyFinal 컴파일-타임 강제 (applied without tallyFinal 차단). Phase 24: severity→고정천장
// 밴드 제거 — applied audit 는 감점 합산 tally final(tallyFinal)을 동반한다.
// 점수 자체는 §10 deductionBreakdown.final 이며 visionVeto.tallyFinal 는 그 audit mirror.
// 객관성: 사람/AI 점수 라벨 아님 — status/severity enum + tallyFinal(측정규칙 산출 정수)만.
// primaryFault(UI B1) = Gemini 비전이 찾은 지배적 결함 DESCRIPTION(자연어) — "왜 점수가
// 내려갔는지" 노출용. 점수/숫자 절대 금지(객관성). applied 시에만 동반, legacy doc 호환 위해
// optional(string | undefined). 3-way lockstep: models.py VISION_VETO_STATUSES + docs/contract.md §4.
// faultJoints(#3, 2026-06-21) = Gemini differences[].body_part 를 정식 keypoint 로 매핑한
// 결과(backend 산출). 앱 마커가 진짜 결함 관절을 강조하게 한다 — 각도편차 최대 관절 폴백 대체.
// applied 시에만 동반 가능, 매핑 0 이면 부재(앱은 forceHighlightWorstCount 폴백).
// faultJointDeficits(2026-06-21) = {keypoint: Gemini 시각 추정 deviation deg} — fault-zoom
// deficit 숫자 source(kismam delta 는 veto 결함을 못 잡아 과소). applied 시에만 동반 가능.
// VisionVetoTelemetry (Phase 23-01) — fan-out 샘플링 audit. resource_limited 분기에서만
// 동반 (부분 샘플로 verdict 확정 금지 — D-13 HIGH-2 Option A 의 비결정성 차단을 audit 로 증명).
export interface VisionVetoTelemetry {
  completedCalls?: number;
  plannedCalls?: number;
  samplingComplete?: boolean;
}
// Phase 23-02 (D-02/D-04/D-12 HIGH-1) — 정량화 DESCRIPTIVE 타입. score/0-100/percent 금지
// (객관성 hard gate). 각도(도)/칸/원인가설 텍스트 + source provenance 만.
// frame-specific 각도 (verdict 프레임 쌍 user/ref_frame_idx 의 행 값 — DTW median 아님, D-10 HIGH-3).
export interface VisionAngleDelta {
  joint: string;
  student_deg: number;
  reference_deg: number;
  delta_deg: number;
  direction: string;
  source: 'geometry';
}
// 결정적 칸/층 (keypoint+baseline → 정수/분수 칸, Gemini 미산출, source=geometry, D-08 H2).
export interface VisionBodyRelativeNotch {
  keypoint: string;
  student_notches: number;
  reference_notches: number;
  delta_notches: number;
  baseline_kind: 'floor' | 'pole_vertical' | 'hip_line';
  source: 'geometry';
}
// robustness 용 window median (still 정확 각도 아님 — 별도 키 + sourceFrameIndices/windowPolicy, D-10 HIGH-3).
export interface VisionWindowMedianAngleDeltas {
  deltas: VisionAngleDelta[];
  sourceFrameIndices: { user: number[]; reference: number[] };
  windowPolicy: string;
}
// support-gated 원인 가설 (source=vision_hypothesis, "~로 보임" 가설형, D-13 MED-1). 점수 아님.
export interface VisionRootCauseHypothesis {
  text: string;
  faultKey: { part_scope: string; side: string; keypoint_set: string; fault_kind: string };
  supportCount: number;
}
export type VisionVeto =
  // Phase 23-02 — applied 시에만 정량화 동반 (discriminated). quantificationStatus 는 applied
  // audit 에 필수 — 'unavailable' 이면 angleDeltas/bodyRelativeNotches 부재 + status='applied'
  // +tallyFinal 유지(강등 금지). score 타입 0 — DESCRIPTIVE(deg/칸/text) + source enum.
  | { status: 'applied'; severity: 'minor' | 'moderate' | 'major'; tallyFinal: number; primaryFault?: string; faultJoints?: KeypointName[]; faultJointDeficits?: Partial<Record<KeypointName, number>>; quantificationStatus?: 'available' | 'unavailable'; angleDeltas?: VisionAngleDelta[]; bodyRelativeNotches?: VisionBodyRelativeNotch[]; windowMedianAngleDeltas?: VisionWindowMedianAngleDeltas; rootCauseHypotheses?: VisionRootCauseHypothesis[] }
  | { status: 'not_applicable'; severity?: 'minor' | 'moderate' | 'major'; tallyFinal?: never; primaryFault?: never; faultJoints?: never; faultJointDeficits?: never; quantificationStatus?: never; angleDeltas?: never; bodyRelativeNotches?: never; windowMedianAngleDeltas?: never; rootCauseHypotheses?: never }
  // Phase 23-01 D-03/H4 — 정렬 신뢰도 낮아 보류(거짓결함 fabricate 안 함). score-free.
  | { status: 'low_alignment_confidence'; severity?: never; tallyFinal?: never; primaryFault?: never; faultJoints?: never; faultJointDeficits?: never; telemetry?: never; quantificationStatus?: never; angleDeltas?: never; bodyRelativeNotches?: never; windowMedianAngleDeltas?: never; rootCauseHypotheses?: never }
  // Phase 23-01 D-09 MED-1 — 예산 소진 fail-closed. severity/tallyFinal/primaryFault/
  // angleDeltas/bodyRelativeNotches/rootCauseHypotheses 부재, telemetry 만 허용.
  | { status: 'resource_limited'; severity?: never; tallyFinal?: never; primaryFault?: never; faultJoints?: never; faultJointDeficits?: never; telemetry?: VisionVetoTelemetry; quantificationStatus?: never; angleDeltas?: never; bodyRelativeNotches?: never; windowMedianAngleDeltas?: never; rootCauseHypotheses?: never }
  | { status: 'disabled' | 'skipped_error' | 'missing_local_video' | 'mode3_held' | 'missing_reference'; severity?: never; tallyFinal?: never; primaryFault?: never; faultJoints?: never; faultJointDeficits?: never; quantificationStatus?: never; angleDeltas?: never; bodyRelativeNotches?: never; windowMedianAngleDeltas?: never; rootCauseHypotheses?: never };

// Phase 20 (TRUST-07) — Mode3 미보유/저신뢰 점수 억제 (discriminated suppression type).
// iter4 MEDIUM-1: scoreSuppressed=true 면 scoreSuppressedReason REQUIRED, false/부재면
// reason never. UI 카피가 reason-specific 이므로 reason 은 더 이상 optional 아님.
// 프런트 isScoreSuppressed 는 STRICTLY scoreSuppressed===true (scoringBasis 폴백 금지 —
// iter3 HIGH-2). 'unheld'=미보유(is_reference_free branch metadata) → '기준 없음' 카피,
// 'recognition_low_confidence'=recognizer 신뢰도 낮음(동작은 알 수 있어도 분류 불확실) →
// '동작 인식 신뢰도가 낮아 기준을 확정할 수 없어요' 카피. iter5 HIGH-2: suppression reason
// 이 scoringBasisLabel 까지 소유 — recognition_low_confidence 면 scoringBasisLabel 이
// '기준 동작 없음' 미노출. 3-way lockstep: models.py SCORE_SUPPRESSED_REASONS + contract.md.
export type ScoreSuppression =
  | { scoreSuppressed: true; scoreSuppressedReason: 'unheld' | 'recognition_low_confidence' }
  | { scoreSuppressed?: false; scoreSuppressedReason?: never };

// Phase 20 iter5 MEDIUM-2 — A2 reconcile audit. recognizer category 와 branch
// is_reference_free 출처가 달라 불일치 시 단일 structured 필드로 보고(log.warning 대안 폐기).
// resolvedReason = resolver 의 최종 reason. 3-way lockstep: models.py SCORE_SUPPRESSION_AUDIT_KEYS.
export interface ScoreSuppressionAudit {
  recognizerCategory: string;
  branchReferenceFree: boolean;
  resolvedReason: 'unheld' | 'recognition_low_confidence';
}

// 문제 부위 확대 비교 (belle 2026-06-21) — 결함 관절 부위만 worst-pose 시점에서 학생 vs
// 기준(정은지) 나란히 crop+zoom 한 합성 이미지(backend 렌더, S3). 한글 캡션은 앱이 joint+
// deficitDeg 로 구성(이미지엔 숫자만). 여러 개면 carousel. Python lockstep: pipeline
// _attach_fault_zoom_comparisons + fault_zoom.py. 깨진 3D 뷰어 대체.
export interface FaultZoomComparison {
  /** 결함/변화 keypoint (left_knee 등) — 앱이 한글 라벨/캡션 구성. */
  joint: KeypointName;
  /** 기준 대비 부족 각도(도). 없으면 null (마커만, Mode3 등). */
  deficitDeg?: number | null;
  /** [학생|기준(Mode1)] 또는 [현재|지난(Mode3)] 합성 PNG presigned GET URL. */
  imageUrl: string;
  /** 캡션 종류 — Mode1='deficit'(기준보다 부족) / Mode3='improved'|'worsened'(지난 대비). */
  kind?: 'deficit' | 'improved' | 'worsened';
  /**
   * 같은 결함에서 온 좌+우 관절 묶음 카드 (quick-260702-sic — 스플릿=양다리).
   * joint 는 대표 keypoint 유지 (S3 key/캐러셀 key 계약 불변), 캡션은 region 우선
   * (REGION_LABEL_KO). Python lockstep: fault_zoom.build_fault_zoom_comparisons +
   * pipeline _render_fault_zoom. list 필드 금지(Firestore flat 제약,
   * _validate_dict_only_scalars)라 scalar region 만. legacy doc 은 부재.
   */
  region?: 'legs' | 'arms' | null;
  /**
   * 2단 시각 언어 tier (quick-260704-fz4, CONTEXT locked) —
   * 'confirmed'=확정 결함(감점 근거, 빨강) / 'advisory'=측정 초과·확인 권장
   * (감점 아님, 주황 + "참고 · 감점 아님" 배지, 표시 전용). 부재(legacy doc)=
   * confirmed 취급 — advisory 카드 미생성 하위호환. Python lockstep: pipeline
   * _render_fault_zoom tier 방출 (region 선례와 동일 — contract.md 섹션 없음,
   * TS 주석 + Python 방출부 주석 lockstep).
   */
  tier?: 'confirmed' | 'advisory' | null;
  /**
   * D-04 — 기준(정은지) 측 프레임 대응 provenance. 'failed'=DTW 대응 실패로
   * 전신 폴백(앱은 "동작 대응 실패 — 전신 비교" 캡션 렌더), 부재(legacy)=캡션 없음.
   * Phase 28 (ALGN-03) 신설 — 동작 기반 정렬로 부위-정합 crop 을 시도했으나 실패한
   * 케이스를 사용자에게 조용히 숨기지 않고 명시. Python lockstep: pipeline
   * fault_zoom refMatch 방출 (region/tier 선례와 동일 — contract.md FaultZoomComparison 절).
   */
  refMatch?: 'dtw' | 'failed';
  /**
   * Phase 31 (D-10) — DTW 대응 프레임 쌍. `keypointReport` 프레임 공간(9fps
   * angles 도메인)의 정수 인덱스로, 2D 비교 뷰어가 "이 카드가 가리키는 순간"을
   * 좌/우 각각 어느 프레임에서 그릴지 결정하는 소스다. crop PNG(imageUrl)와
   * 달리 뷰어는 좌표를 직접 렌더하므로 프레임 인덱스가 필요.
   * userFrameIdx=학생 측 / refFrameIdx=기준(정은지) 측 / refMatched=기준 측
   * 대응 성공 여부(false 면 뷰어가 학생 단독 렌더 — refMatch 'failed' 와 정합).
   * 부재(legacy doc)=뷰어 프레임 동기화 없음(하위호환, tier?/refMatch? 선례).
   * 31-03 이 방출. Python lockstep: fault_zoom 방출부 + contract.md
   * FaultZoomComparison 절.
   */
  userFrameIdx?: number;
  refFrameIdx?: number;
  refMatched?: boolean;
}

// Phase 28 (ALGN-01 동작 기반 비교 정렬) — 학생(left)=master 시계 불변, 정은지(right)만
// warp(tStudent)→tRef 로 따라가는 정렬 맵. `result.motionAlignment` 로 방출되며
// VideoCompare 가 소비(alignmentWarp.ts 순수 함수).
// (a) anchors = flat [u0,r0, u1,r1, ...] — 학생초(u)/기준초(r) 쌍, u 단조 증가·r 비감소
//     ([[firestore-nested-array-flat]] — nested list 금지, flat scalar 만).
// (b) 부재(legacy doc) = 현행 절대시계 동작 (하위호환, tier? 선례와 동일 규칙 — no migration).
// (c) source 'vlm' = Phase 22 v1 time_anchors 상위 호환 축 (22-01 REPORT_KEYS time_anchors 동형).
// (d) Python lockstep: models.py MOTION_ALIGNMENT_KEYS + docs/contract.md §11.
// (e) 역불변식 (리뷰 MEDIUM-3): 빈 anchors 는 tier 'disabled'(degenerate 방출 형상)만 유효 —
//     'warped'/'trim_only' 는 최소 2쌍(4 float). firestore_admin._validate_motion_alignment
//     가 저장 전 강제 (앱 normalizeMotionAlignment 와 대칭 — alignmentWarp.ts).
export interface MotionAlignment {
  version: string;
  source: 'dtw' | 'vlm';
  tier: 'warped' | 'trim_only' | 'disabled';
  reason?: string;
  anchors: number[]; // flat [u0,r0, u1,r1, ...] 초 단위 float 쌍 (u 단조 증가, r 비감소)
  anchorCount: number; // len(anchors)/2 (reshape 메타 — anglesFrames 선례)
  distance: number;
}

// Phase 32 (Plan 32-06 — 32-CONTEXT D-19/D-26/D-27/D-14) — 미션 루프 계약.
// backend analysis/mission.py 순수 함수가 산출, 32-09 파이프라인이 result.mission
// 으로 방출. 부재(legacy doc) = 미션 표면 미렌더 (하위호환, tier? 선례 — no migration).
// faultKey = `{motionId}::{ruleId}::{criterion}` 결정적 조합 — criterion 이 좌우
// 관절을 내장(angle_vs_reference__left_knee)해 좌우 구분이 승계된다 (리뷰 blocker 1).
// baseline*(baselinePoints/baselineDeviation/targetValue/unit) = 다음 분석의
// 개선량 계산 재료 (D-26). isSafety=true 는 streak 1 고정 + escalation 'none'
// 강제 — 안전은 안내 전용, 게임·에스컬레이션 제외 (D-14).
// Python lockstep: models.py MISSION_KEYS/MISSION_SELECTED_BY/MISSION_ESCALATIONS
// + docs/contract.md §12.1.
export interface Mission {
  faultKey: string;
  criterion: string;
  ruleId?: string | null;
  // 선정 record 의 안정 조인 키 (부재 시 null — §12.3 recordId 참조).
  recordId?: string | null;
  selectedBy: 'safety' | 'repeat' | 'max_deduction';
  streak: number; // 1..99 — 같은 faultKey 미개선 연속 회차 (doc 체인 전파)
  isSafety: boolean;
  escalation: 'none' | 'exercise_detour' | 'coach_card'; // D-27 (2회차/3회차+)
  motionId?: string | null;
  baselinePoints: number; // 선정 record |points| — 다음 분석 개선량 계산 기준
  baselineDeviation?: number | null; // |measured−target| (둘 다 있을 때만)
  targetValue?: number | null;
  unit?: string | null;
}

// Phase 32 (Plan 32-06 — D-26) — 지난 미션의 수치 outcome (mode3 전용).
// **수치·bool·키만** — 사람 문장은 백엔드 phrasebook 조립(summaryPraise)·앱 렌더
// 소관 (계산/카피 책임 분리, 리뷰 반영). 수치 렌더는 D-09 invariant 준수 —
// 헤드라인 금지, 소형 보조 표기만.
// Python lockstep: models.py MISSION_OUTCOME_KEYS + docs/contract.md §12.2.
export interface MissionOutcome {
  improved: boolean;
  faultKey: string;
  criterion: string;
  baselinePoints: number; // prev mission 저장값
  currentPoints: number; // 잔존 시 |points|, 소멸 시 0
  deltaPoints: number; // baseline − current (양수 = 개선, 음수 = 악화)
  baselineDeviation?: number | null;
  currentDeviation?: number | null;
  deltaDeviation?: number | null;
}

// Phase 32 (Plan 32-06 — D-06/D-26 + 리뷰 blocker 5) — 잘한 점 후보 단일 원천.
// 백엔드가 phrasebook 으로 산출·방출(32-09) — 앱은 소비하고 legacy doc 만 로컬
// 폴백 파생(32-07 summarySource). 스팟체크(32-13)가 이 headline 을 교차검증하므로
// 앱이 렌더하는 문장과 검증 대상 문장이 동일해진다.
// headline 은 사람 말 — **수치 미포함** (D-09: 수치는 evidenceValue/evidenceUnit
// 구조 필드로만 분리, 렌더 여부·위치는 소비 컴포넌트 소관).
// Python lockstep: models.py SUMMARY_PRAISE_KEYS/SUMMARY_PRAISE_SOURCES +
// docs/contract.md §12.4.
export interface SummaryPraise {
  source: 'mission_improved' | 'clean_dimension' | 'criteria_met';
  headline: string;
  evidenceValue?: number | null;
  evidenceUnit?: string | null;
}

// Phase 32 (Plan 32-06 — D-28/D-29) — 코치 질문 자동 등재 항목. list[dict-of-
// scalars] 라 Firestore 허용 (nested array 아님 — safetyFlags 선례). recordId
// 조인으로 해당 감점 카드 점프 (부재 = 점프 없음).
// **source 'user' 는 클라이언트 로컬 전용** ('강사님께 물어보기' 담기) — 백엔드
// 방출·validator 에 도달하지 않는다 (백엔드 방출 가능값은 나머지 3종).
// Python lockstep: models.py COACH_QUESTION_SOURCES + docs/contract.md §12.5.
export interface CoachQuestion {
  text: string; // 문구집 스타일 완성문 (D-28)
  source: 'safety' | 'mission_stuck' | 'unmeasured' | 'user';
  recordId?: string;
}

// Phase 32 (Plan 32-16 — D-18 B안 클라우드 TTS) — 재생 중 큐 오디오 조인 목록.
// 백엔드가 분석 **사후** 스테이지에서 records 의 cueLine(승인 문구집 골격 —
// D-09 무수치)을 AWS Polly(neural)로 사전 합성해 S3 에 저장하고
// update_analysis_coach_audio 부분 갱신으로 도착시킨다 (faultZoomStatus 사후
// 분리 선례). 부재(legacy doc) = 오디오 표면 미렌더 (하위호환, tier? 서술 모범
// — no migration).
//   status: 'done' = 합성 완료 (items 유효 — 빈 리스트 = 재생할 큐 없음) /
//   'failed' = 합성 실패 (자막만 — 조용한 폴백, 분석 무훼손 SP-3).
//   items[].recordId = §12.3 recordId — 32-12 audioCue prefetch 의 cueId 조인 키.
//   items[].key = canonical S3 키 (results/ prefix). URL 은 저장하지 않는다 —
//   재생 URL 은 POST /playback-url { asset: 'coachAudio', recordId } 재서명으로만
//   발급 (리뷰 H-02 — 서버 구성 canonical key + 저장 key exact 비교).
// Python lockstep: models.py COACH_AUDIO_KEYS 블록 +
// firestore_admin.update_analysis_coach_audio + docs/contract.md §12.7.
export interface CoachAudioItem {
  recordId: string;
  key: string; // S3 key (results/{uid}/{analysisId}/coach_audio_{recordId}.mp3). URL 아님.
}

export interface CoachAudio {
  status: 'done' | 'failed';
  items: CoachAudioItem[];
}

// Phase 24 (SCORE-10~16, ND-01/ND-07) — 투명 감점-합산 채점.
// 점수 = baseline(100) − Σ(criterion별 측정편차 × 명시규칙 감점). severity→고정밴드
// (Phase 20 visionVeto 의 옛 cap 필드) 제거. 보고서가 감점 내역("−X −Y −Z = 점수")을 노출하는 게 핵심
// ([[scoring-must-be-transparent-deduction-tally]]).
// HIGH-3: baselineValue(수치 측정 기준 — 180/160/reference_notches, REQUIRED) +
//   baselineKind(per-move floor/pole_vertical/hip_line — reach 만, present-but-nullable)
//   가 분리됨. 단일 baseline 으로 DeductionBreakdown.baseline=100 과 충돌 금지.
// HIGH-2: points 는 SIGNED NEGATIVE (UX −X). source ∈ {'geometry','vision'} — belle
//   2026-06-29 결정 A: geometric 측정 불가 결함(split, kip-up keypoint saturate)은 Gemini
//   vision-측정값으로 점수화하되 source='vision' 으로 provenance 투명 표기
//   (deduction_engine.py tally() 방출 정합). 점수 산식은 동일 규칙(tol×slope) — Gemini
//   점수 아님(ND-02 유지). MEDIUM-2: record 내부 STRICT(baselineKind nullable, ipsfAnchor/
//   baselineValue REQUIRED). 3-way lockstep: models.py DEDUCTION_RECORD_KEYS + contract.md §10.
export interface DeductionRecord {
  criterion: string;
  measuredValue: number;
  baselineValue: number;
  baselineKind: 'floor' | 'pole_vertical' | 'hip_line' | null;
  deviation: number;
  ruleId: string;
  points: number; // SIGNED NEGATIVE (감점). final = max(0, round(100 + Σ points)).
  unit: 'deg' | 'notch' | 'score_delta';
  ipsfAnchor: string;
  source: 'geometry' | 'vision';
  deviationSource: 'ipsf_absolute' | 'reference_relative' | 'dimension_overall';
  // per-record 감점 상한 -20 (quick-260705-k8h, belle 승인 2026-07-05). 상한이 적용된
  // record 에만 쌍으로 방출 — 미적용 record 는 키 생략(기존 11필드 byte-호환, legacy
  // doc 부재 안전). Python lockstep = models.DEDUCTION_RECORD_OPTIONAL_KEYS +
  // contract.md §10.2. fallback record(dimension_overall_fallback)는 클램프 비대상.
  rawPoints?: number; // SIGNED NEGATIVE — 관절당 상한(-20) 적용 전 원 감점. capApplied 시에만.
  capApplied?: true; // 이 record 의 감점이 관절당 상한 -20 으로 클램프됨 (투명 내역 유지).
  // ── Phase 32 (Plan 32-06 — D-08/D-10 + 리뷰 blocker 5) additive optional ──
  // 부재 = legacy doc (32-09 방출 이전) — 전부 하위호환. Python lockstep =
  // models.py DEDUCTION_RECORD_EXTENSION_KEYS + docs/contract.md §12.3. record
  // 검증은 scalar 라 기존 _validate_dict_only_scalars 경로 자동 통과.
  // 주의 — 이 interface 블록 주석에는 word-colon 패턴·중괄호 금지
  // (test_deduction_engine.test_contract_lockstep 의 regex 필드 추출과 충돌).
  //
  // recordId — 방출 시 1회 각인되는 안정 조인 키. 형식은 r + 2자리 index +
  // 콜론 + criterion (contract.md §12.3, 32-09 각인). 정렬·필터·숨김(32-13
  // 스팟체크 hiddenRecordIds)에 배열 index 대신 사용.
  recordId?: string;
  // 감점 카드 3단 문구 (D-08 상태→왜→행동) + 코치 질문·운동 연결 (D-13/D-28).
  // phrasebook(32-05) 골격 산출 — fail-closed 조합은 cueLine/exerciseId/
  // exerciseReason 생략 (일반론 조언 fabrication 차단).
  statusLine?: string; // 상태 (몸 말, 관절명 허용 — 이해용)
  whyLine?: string; // 왜 (감점·위험 이유 1줄, 심사 언어)
  cueLine?: string; // 행동 (외부 큐 — 수행용)
  coachQuestion?: string; // '강사님께 물어보기' 완성문 (D-28)
  exerciseId?: string; // 연결 보완 운동 id (D-13)
  exerciseReason?: string; // 왜 이 운동인지 결함→운동 연결 이유 1줄 (D-13 필수 짝)
  // 규칙 상수 유래 허용 오차 — 게이지 스케일 재료 (D-10). 자의적 수치 아님 —
  // 32-09 가 실존 규칙 상수(CRITERION_GROUPS 등)에서만 방출 (있을 때만).
  tolerance?: number;
}
// HIGH-1: OBJECT shape (bare list 아님). final = max(0, round(100 + Σ record.points)) —
// final 단위 clamp 은 max(0,…) 뿐(final 밴드 없음). record 단위로는 관절당 감점 상한 -20
// (quick-260705-k8h)이 points 에 이미 적용돼 있다 — rawPoints/capApplied 참조.
// MEDIUM-1: fallback='quantification_unavailable'
// 면 records 에 dimension_overall_fallback record 1개로 추적성 유지. MEDIUM-3: coverageGaps
// entry 는 flat-scalar provenance(bodyPart/faultState/keypointSet/ruleId) 동반.
export interface DeductionBreakdown {
  baseline: 100;
  records: DeductionRecord[];
  final: number;
  coverageGaps?: {
    faultType: string;
    reason: string;
    bodyPart?: string;
    faultState?: string;
    keypointSet?: string;
    ruleId?: string;
  }[];
  fallback?: 'quantification_unavailable' | 'gemini_silent';
}

export type AnalysisResult = ScoreSuppression & {
  // Phase 27 SPD-01 — 단계별 소요(ms). backend/audit 전용, 사용자 비노출(UI 소비 금지).
  // Python lockstep: pipeline app.py `_stage` + contract.md timingsMs 절. flat
  // Record<string, number> (nested 금지 — [[firestore-nested-array-flat]]). 키는 자유
  // (status enum 아님) — 단계 추가는 비파괴. OPTIONAL — legacy doc 호환(부재 = 계측 이전 doc).
  timingsMs?: Record<string, number>;
  // Phase 24: overallScore = deductionBreakdown.final (측정-기하 substrate 위 tally 출력,
  // min-of-core-possibly-capped 아님). legacy doc 은 deductionBreakdown 부재 가능.
  overallScore: number; // 0~100 종합. Phase 24 = deductionBreakdown.final. (legacy: min-of-core).
  // Phase 20 SCORE-08 — 비전 하향 거부권 audit. OPTIONAL (legacy doc 호환).
  visionVeto?: VisionVeto;
  // Phase 24 (ND-01/ND-07) — 투명 감점-합산 내역 OBJECT. OPTIONAL (legacy doc 호환,
  // no migration). consumers read result.deductionBreakdown?.final.
  deductionBreakdown?: DeductionBreakdown;
  // 문제 부위 확대 비교 carousel (belle 2026-06-21). OPTIONAL (Mode1 + 결함 있을 때만).
  faultZoomComparisons?: FaultZoomComparison[];
  // Phase 27 SPD-04 (D-06) — zoom 사후 분리 로딩 상태. 점수/verdict/감점 내역은
  // status='done' 시점에 확정되고, zoom PNG 는 그 이후 부분 업데이트로 도착한다.
  // 'pending'=렌더 중(카드 자리 placeholder) / 'done'=도착(faultZoomComparisons 유효)
  // / 'failed'=실패(카드 숨김 — pending 고아 방지). 부재(legacy doc)=faultZoomComparisons
  // 유무로 판정 — 사후 분리 이전 doc 하위호환 (tier? 서술 모범 준수). Python lockstep:
  // models.py FAULT_ZOOM_STATUSES + firestore_admin.update_analysis_fault_zoom +
  // contract.md faultZoomStatus 절.
  faultZoomStatus?: 'pending' | 'done' | 'failed';
  // Phase 31 (D-05) — 교정된 자세 이미지(결함 top-1 부위의 순간 프레임 → 고친 폼).
  // 분석 완료 시 자동 생성되어 사후 부분 업데이트로 도착한다 (faultZoomStatus 와
  // 동일한 사후 분리 패턴).
  // 'pending'=생성 중(카드 자리 placeholder) / 'done'=도착(카드 표시) /
  // 'failed'·부재(legacy doc)=카드 숨김 — 실패를 사용자에게 에러로 노출하지 않는
  // 조용한 폴백(D-08). 무한 pending 고아는 correctedPoseUpdatedAtMs 로 판정.
  //
  // URL 은 저장하지 않는다 — 표시 URL 은 POST /playback-url 의
  // `asset: 'correctedPose'` 재서명으로만 발급 (리뷰 H-02). 문서에 presigned URL 을
  // 박제하면 TTL 만료 후 죽은 URL 이 남고, 클라이언트가 임의 key 를 서명시킬 여지가
  // 생긴다. 문서에는 S3 key 만 두고 서버가 asset 종류로 key 를 선택한다.
  //
  // 타임아웃/dedupe 판정 기준은 이 correctedPoseUpdatedAtMs 이며 공용 updatedAt 이
  // 아니다 (리뷰 H-06 — 공용 updatedAt 은 무관한 write 로도 갱신돼 pending 수명을
  // 잘못 늘린다).
  //
  // Python lockstep: models.py VISUAL_STATUSES + firestore_admin.update_analysis_visual
  // + contract.md "visual 교정 시각물 필드" 절.
  correctedPoseStatus?: 'pending' | 'done' | 'failed';
  correctedPoseKey?: string; // S3 key (results/{uid}/{analysisId}/ prefix). URL 아님.
  correctedPoseJoint?: string; // 교정 대상 top-1 결함 keypoint (앱이 한글 라벨 구성).
  correctedPoseUpdatedAtMs?: number; // epoch ms — 이 필드 전용 타임아웃/dedupe 기준.
  // Phase 31 (D-06) — 카메라앵글 회전 참고 영상. 건당 수분·과금이라 자동이 아니라
  // 온디맨드(POST /visual/rotation) → 백그라운드 생성 → 카드 갱신이다. 대기 중에는
  // R3F 수학 3D 뷰어가 즉시 대체재로 표시된다.
  // 상태 의미·URL 비저장 원칙·전용 timestamp 기준은 correctedPose* 와 동일
  // (리뷰 H-02 / H-06). 표시 URL 은 asset: 'rotation' 재서명.
  //
  // 점수 비반영 invariant: 회전 산출물은 채점에 절대 들어가지 않는다
  // ([[camera-angle-scoring-stretch-reference-corner]]) — 결과 화면에서도 점수 내역
  // 아래 "참고하세요" 섹션에 분리 배치(D-09).
  //
  // Python lockstep: models.py VISUAL_STATUSES + firestore_admin.update_analysis_visual
  // + contract.md "visual 교정 시각물 필드" / "POST /visual/rotation" 절.
  rotationStatus?: 'pending' | 'done' | 'failed';
  rotationVideoKey?: string; // S3 key (results/{uid}/{analysisId}/ prefix). URL 아님.
  rotationUpdatedAtMs?: number; // epoch ms — 이 필드 전용 타임아웃/dedupe 기준.
  // Phase 28 (ALGN-01) — 동작 기반 비교 정렬 맵. OPTIONAL (부재=현행 절대시계, legacy
  // 하위호환, no migration). VideoCompare 가 소비(alignmentWarp.ts warpTime/segmentRate).
  // Python lockstep: models.py MOTION_ALIGNMENT_KEYS + firestore_admin._validate_motion_alignment
  // + contract.md §11. source:'vlm'=Phase 22 v1 time_anchors 상위 호환 축.
  motionAlignment?: MotionAlignment;
  // Phase 32 (Plan 32-06 — D-19/D-26/D-27/D-08/D-28) — 미션 루프 + 번역 레이어.
  // 전부 OPTIONAL — 32-09 방출 이전 legacy doc 부재 하위호환 (백엔드는 None 시
  // 키 생략 방출). "result 안으로 흐른다" — complete_analysis 신규 kwarg 0,
  // firestore_admin scoped validator(_validate_mission 등)로만 검증.
  // Python lockstep: models.py MISSION_KEYS 블록 + docs/contract.md §12.
  mission?: Mission;
  missionOutcome?: MissionOutcome; // mode3 전용 — mode1/prev 부재 시 키 생략
  summaryPraise?: SummaryPraise; // 잘한 점 단일 원천 (리뷰 blocker 5)
  coachQuestions?: CoachQuestion[]; // 자동 등재 (≤10) — 'user' 담기는 로컬 전용
  // Phase 32 (Plan 32-16 — D-18 B안) — 재생 중 큐 오디오. complete 이후 사후 부분
  // 업데이트로 도착 (fault_zoom 선례). 부재(legacy doc)=오디오 표면 미렌더.
  coachAudio?: CoachAudio;
  // Phase 20 iter5 MEDIUM-2 — A2 reconcile audit (reconcile 관측). OPTIONAL.
  scoreSuppressionAudit?: ScoreSuppressionAudit;
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
  // Phase 10 (Plan 10-01) — 결정론 부상 위험 신호 (D-01 / SAFE-01). 기존 LLM
  // 코칭 프로즈 레이어와 독립. 옵셔널/nullable — 이전 빌드 doc 호환 + graceful-omit.
  // Wave 0 = schema only. 10-02/03/04 가 firing rule 산출 후 pipeline 이 채움.
  safetyFlags?: SafetyFlag[] | null;
  // Phase 9 (Plan 09-01) — §9.11 ForcePatternInference (D-09-D1 / D-09-U1).
  // Wave 0 = schema only. Wave 1 (Plan 09-02) 가 본체 함수 + canned + pipeline
  // wiring 박제. 본 필드는 Wave 1 wiring 이후 backend pipeline 이 채움.
  // 책임 경계: Phase 11 (CoachCommentHook) 가 findings[].interpretation 위
  // LLM 자연어 풍부화. Phase 12 가 raw 수치 UI 노출. Phase 9 자체는 canned 만.
  forcePatternInference?: ForcePatternInference | null;
  // Phase 13 (Plan 13-A, PERS-03) — 보완 운동 3~5개 개인화 subset.
  // backend exercise_map.map_exercises(findings + painAreas + motion_id) 산출 →
  // _validate_recommended_exercises scoped validator → result.recommendedExercises.
  // 옵셔널 — 이전 빌드 doc 호환 (dimensionExplanation 패턴). 빈/부재 시 result.tsx
  // 는 전체 라이브러리 모달 browse entry 만 유지 (MEDIUM-1). 전체 라이브러리는
  // app/src/data/correctiveExercises.ts (backend fixture byte-copy mirror) 가 source.
  recommendedExercises?: RecommendedExercise[];
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
  // 업로드 시점 학습활용 동의값 (Phase 26, D-08/D-09). belle 결정(2026-07-08,
  // 26-06 실기기 확인)으로 opt-out: 앱 UI 기본값 = 동의(체크 ON), 사용자가
  // 해제하면 false 로 기록된다. 필드 부재(Phase 26 이전 문서) 또는 라우트 param
  // 유실 = 동의 없음(false)으로 해석해야 한다 (fail-safe = 미동의). Phase 22 D-12 학습
  // 플라이휠의 동의 근거 — Phase 22 manifest 게이트는 learningOptIn === true 인
  // 분석의 영상만 학습 후보로 삼아야 한다 (의무 계약 — 현 22-04 게이트는
  // anonymized/등록 여부만 필터하고 learningOptIn 은 아직 읽지 않으므로, 이
  // 필터는 Phase 22 후속에서 반영해야 함). loading.tsx 가 항상 boolean 으로 기록.
  // 3-way lockstep: models.py + docs/contract.md §3 과 동시 갱신 (계약 변경 규약).
  learningOptIn?: boolean;
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
 * Phase 9 의 inferForceDirectionPattern 의 입력 신호 (원인 카드 UI 는
 * quick-260705-o0s 에서 코칭 팁 흡수로 삭제 — coachCommentHook 소비는 유지).
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

// ── Phase 10 §N SafetyFlag (D-01 / SAFE-01) ─────────────────────────────
//
// Source contract: docs/contract.md §N + backend safety_flags.py (frozen dataclass).
// 결정론(LLM 무관) 부상 위험 신호. CONTEXT D-01 — 기존 LLM 코칭 프로즈
// (CoachingTipDetail 의 부상 위험 텍스트) 레이어와 독립 (대체/주입 X). 발화 =
// (자세 조건) AND (통제 상실 지표) (D-02). 모든 필드 scalar — nested array 금지.
// severity = SeverityLevel / confidence = MetricConfidence 재사용 (재정의 금지).
//
// 변경 시 backend safety_flags.py + docs/contract.md §N 동시 갱신 (CLAUDE.md
// Cross-cutting 3-way lockstep).
export type SafetyFlagType =
  | 'asymmetry'
  | 'trunk_hyperextension'
  | 'joint_hyperextension'
  | 'level_mismatch';

export interface SafetyFlag {
  flagType: SafetyFlagType;
  bodyRegion: string;
  severity: SeverityLevel;
  confidence: MetricConfidence;
  modeScope: 'both' | 'mode1_only';
  postureCondition: string;
  controlLossSignal: string;
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
  /** Phase 11 (COACH-01) — 리포트별 LLM 코칭 코멘트 hook. v1 nullable (백필 전 / 미생성). */
  coachCommentHook?: CoachCommentHook | null;
}

/**
 * Phase 11 (COACH-01) — 리포트 1건에 부착되는 LLM 코칭 코멘트 hook (D-02 per-report 단위).
 *
 * Python lockstep: backend/shared/python/sunity_shared/analysis/coach_hook.py
 *   CoachCommentHook (frozen dataclass + __post_init__ validator).
 * docs lockstep: docs/contract.md §9.11.7 (+ §8 BodyComparisonReport 부착 표기).
 *
 * list 필드 = string[] 전용 (nested array 금지 — [[firestore-nested-array-flat]]).
 * coachComment / reviewedBy = v2 강사 콘솔 입력용 — v1 항상 null (D-06).
 */
export interface CoachCommentHook {
  /** LLM 자연어 요약 (findings interpretation 번역). non-empty. */
  autoFindingsSummary: string;
  /** 강사에게 던지는 질문 (string[] only). */
  openQuestionsForCoach: string[];
  /** 수강생용 큐 (string[] only). */
  suggestedCues: string[];
  /** v2 강사 입력 — v1 항상 null (D-06). */
  coachComment?: string | null;
  /** v2 리뷰어 — v1 항상 null (D-06). */
  reviewedBy?: string | null;
  /** provenance scalar ('forcePatternInference' / 'bodyComparisonReport') — v2 콘솔 집계 (D-02). */
  sourceReport?: string | null;
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
  /** Phase 11 (COACH-01) — 리포트별 LLM 코칭 코멘트 hook. v1 nullable (백필 전 / 미생성). */
  coachCommentHook?: CoachCommentHook | null;
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
