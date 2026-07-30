import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
// 33-15 (D-17) — 본문↔상단 상태바 겹침 수정. 고정 layout.safeAreaTop(59) 을 스크롤
// 콘텐츠 안쪽 패딩으로 쓰면 스크롤 시 본문이 상태바 아래로 파고든다 — 컨테이너
// 레벨 실측 inset(useSafeAreaInsets)으로 뷰포트 자체를 상태바 아래에서 시작시킨다.
// SafeAreaProvider 는 expo-router 루트가 제공 (inquiry.tsx 선례).
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { AccuracyLimitBadge } from '../../components/AccuracyLimitBadge';
import { InjuryRiskSection } from '../../components/InjuryRiskSection';
import { CoachingTipDetailModal } from '../../components/CoachingTipDetailModal';
import { RecommendedExerciseModal } from '../../components/RecommendedExerciseModal';
import { CORRECTIVE_LIBRARY_HAS_ITEMS } from '../../data/correctiveExercises';
import {
  KeypointOverlay,
  KEYPOINT_DELTA_HIGHLIGHT_DEG,
} from '../../components/KeypointOverlay';
import { KeypointOverlayToggle } from '../../components/KeypointOverlayToggle';
import { DeductionDetailSheet } from '../../components/DeductionDetailSheet';
import { PartChipsRow } from '../../components/PartChipsRow';
import { DefectIllustration } from '../../components/DefectIllustration';
import { OctagonScore, scoreGrade } from '../../components/OctagonScore';
import { ScoreBreakdownSection } from '../../components/ScoreBreakdownSection';
import { VideoCompare } from '../../components/VideoCompare';
import { ReferenceCornerSection } from '../../components/ReferenceCornerSection';
import type {
  ReferenceCardState,
  RotationCardState,
} from '../../components/ReferenceCornerSection';
// ── 32-11 대배선 — 32-07/32-08/32-10 산출 컴포넌트·뷰모델 배선 ──────────────
import { SummaryCard } from '../../components/SummaryCard';
import { DeductionCard } from '../../components/DeductionCard';
import type { DeductionCardRecord } from '../../components/DeductionCard';
import { ResultCoachmarks } from '../../components/ResultCoachmarks';
import { hasSeenResultCoachmark, markResultCoachmarkSeen } from '../../lib/coachmark';
import { deriveSummaryContent } from '../../lib/summarySource';
import type { SummaryInput } from '../../lib/summarySource';
import {
  deriveResultSections,
  buildRecordMaps,
  recordKeyForIndex,
} from '../../lib/resultSections';
import type { ResultSectionKey, ResultSection } from '../../lib/resultSections';
import { buildCueWindows } from '../../lib/cueTrack';
import type { CueInput } from '../../lib/cueTrack';
import { normalizeMotionAlignment } from '../../lib/alignmentWarp';
import { legacyOffsetFromCompareFrames } from '../../lib/manualOffset';
import {
  ANGLE_VS_REFERENCE_PREFIX,
  JOINT_LABEL_KO,
  KEYPOINT_FROM_ANGLE_KEY,
  buildDeductionMarkers,
  buildDeductionTicks,
  composeScoringBasisKo,
  composeShortActionLabelKo,
  criterionLabelKo,
  formatDeductionNumber,
  isCleanPass,
  matchZoomForDeductionRecord,
  projectDeductionRecordKeypoints,
} from '../../lib/deductionLabels';
import {
  buildPartChips,
  buildPartGroups,
  buildRegionSheetView,
} from '../../lib/deductionSheet';
import { reshapePose3dData } from '../../lib/joints';
import {
  useReferenceMotion,
  useReferenceMotionDoc,
} from '../../lib/referenceMotions';
import { useAnalysisDoc } from '../../lib/userAnalyses';
import { useBodyProfile } from '../../lib/bodyProfile';
import {
  fetchVisualAssetUrl,
  requestPlaybackUrl,
  requestReferencePlaybackUrl,
  requestRotationVideo,
} from '../../lib/api';
import {
  CORRECTED_POSE_PENDING_TIMEOUT_MS,
  ROTATION_PENDING_TIMEOUT_MS,
  isDailyLimit,
  mapFrameIdx,
  pickCompareFrames,
  visualCardState,
} from '../../lib/visualCards';
import {
  DIMENSION_ORDER,
  DOMINANT_HAND_LABEL_KO,
  EXPERIENCE_LABEL_KO,
  PAIN_AREA_LABEL_KO,
} from '../../types/analysis';
import type {
  AnalysisResult,
  BodyProfile,
  CoachingTip,
  CoachQuestion,
  DeductionRecord,
  FaultZoomComparison,
  JointDirection,
  JointScore,
  KeypointName,
  KeypointReport,
  SegmentScores,
  SkillLevel,
  SynthesisWarningCode,
} from '../../types/analysis';
import { colors, layout, radius, spacing, typography } from '../../theme';

// Phase 27 D-06 (T-27-21 mitigation) — zoom 사후 도착의 pending 고아 방어 상한.
// 27-06 이 점수 complete 이후 faultZoomStatus='pending' → done/failed 로 부분
// 업데이트한다. done/failed 가 끝내 도착하지 않으면(렌더 크래시·write 유실) 앱이
// 무한 로딩에 빠질 수 있다 — doc.updatedAt(=complete 시점) 기준 경과가 이 상한을
// 넘으면 placeholder 대신 기존 숨김으로 폴백한다(무한 로딩 0). contract.md
// faultZoomStatus 절. 값 근거: 27-TIMING-BEFORE 실측 fault_zoom 렌더 = 13~33s
// (최장 elbow-twist-sister 32.6s). 상한은 그 최장값을 크게 상회하는 보수값(180s)
// — 정상 pending 을 조기 숨김하지 않음.
const FAULT_ZOOM_PENDING_TIMEOUT_MS = 180_000;

// 29-CONTEXT D-05 — mode3 한계 고지 (belle 승인 뼈대, 세부만 재량). 측정 범위
// (카메라로 잰 자세 형태 기준) + 다음 행동 유도(새 영상 발전 비교 / 코치님 비교)를
// 결합한 1줄. mode3 결과에는 breakdown 유/무 무관 항상 1곳에 도달한다. belle 이
// 지적한 D-05 금지어(사용자 미이해 + mode3 angle 차원 용어 충돌 + 강사 철학 충돌)를
// 배제 — "자세 형태" 로 대체. mode1 은 이 상수를 소비하지 않는다 (렌더 diff 0).
const MODE3_LIMIT_NOTICE =
  '카메라로 잰 자세 형태 기준이에요. 같은 동작을 새 영상으로 다시 올리면 이전 영상과 비교한 발전 분석이 본격 시작돼요. 그립·디테일 점검은 코치님 비교 분석을 이용해보세요.';

// IN-01 (quick-260724-q6b) — 역립/자기가림 저신뢰(attributionReliability.unreliable)
// 시 per-joint 단정을 강등하고 동작비교 영역에 "AI 공부 중" 안내 1줄을 정확히 1회
// 렌더. mode-aware (mode1 / mode3 progress / mode3 first). belle 확정 원칙: 저신뢰
// 시 가치를 삭제하지 않고 거짓 per-joint 단정도 하지 않는다 — 확신하는 것(점수·비교·
// 성장)을 앞세우고 per-joint 는 "예상" 으로 강등한다. 문구는 로직 무접촉 재조정용 상수.
const ATTR_GUIDANCE_MODE1 =
  '거꾸로 자세는 관절 하나하나까진 AI가 아직 공부 중이에요. 정은지 선수 영상을 자세히 비교해보세요.';
const ATTR_GUIDANCE_MODE3_PROGRESS =
  '점수 기준으로 이전보다 발전하고 있어요. 거꾸로 자세 세부 관절은 AI가 아직 공부 중이에요.';
const ATTR_GUIDANCE_MODE3_FIRST =
  '첫 분석이에요 — 다음부터 발전을 비교해드려요. 거꾸로 자세 세부는 AI가 공부 중이에요.';
// 점수 계산 내역 집계 문장 폴백 (백엔드 aggregateStatement 부재 시). 관절명 없음.
const ATTR_SCORE_AGGREGATE_FALLBACK =
  '거꾸로 자세라 관절별 감점 위치는 추정이에요. 종합 점수는 그대로예요.';
// 확대비교 크롭 "예상 부위" 배지 (확정 결함 아님 — 표시 전용).
const ATTR_ZOOM_ESTIMATED_LABEL = '예상 부위';
// IN-01 (quick-260724-q6b) — 역립 저신뢰 시 확대비교 진입점 라벨. topFix 카드가
// 억제돼 확대비교가 도달 불가한 gap 을 메운다 (belle: "예상 부위"로 도달 가능해야
// 함). "AI 공부 중" 안내줄이 맥락을 주므로 추정임이 전달됨 — 확정 결함 단정 아님.
const ATTR_ZOOM_ESTIMATED_ENTRY_LABEL = '예상 부위 확대 비교 보기';

const REFERENCE_LEVEL_LABEL: Record<SkillLevel, string> = {
  basic: '기본기',
  intermediate: '중급',
  advanced: '고급',
};

// 32-11 (D-17 확정 밀도 = 결함 구간당 1개) — 재생 중 자막 큐 윈도우 폭(초)과 상한.
// 결함 순간 전후 CUE_WINDOW_SEC/2 동안 자막 유지. maxCues 는 record 수로 두되(각
// record 1윈도우), 겹칠 땐 activeCue 가 시작 늦은(더 정확한) 큐를 우선한다.
const CUE_WINDOW_SEC = 1.6;

// 32-11 (D-03 확정 = 개인화 심사 시뮬레이션) — 지식전달형 금지. 내 실제 결함들에
// IPSF 감점 규칙(실존 규칙 곱셈)을 적용해 "실제 심사였다면" 을 보여주는 카피 상수.
const JUDGE_SIM_TITLE = '내 수행이 실제 심사였다면';
const JUDGE_SIM_INTRO =
  '국제 폴스포츠(IPSF) 심사 기준으로 내 자세를 채점하면, 위에서 짚은 결함들이 이렇게 감점으로 환산돼요.';
const JUDGE_SIM_DISCLAIMER =
  'AI가 추정한 감점 시뮬레이션이에요. 실제 심사·강사 평가와 함께 확인하면 가장 정확해요.';

// 32-11 (D-13) — 보완 운동 개편 카피. 전면 1개 + 이유 1줄, '다른 운동 보기' 가로 최대 3.
const EXERCISE_DETOUR_HEADLINE = '이 운동부터 해보면 쉬워져요';
const EXERCISE_DETOUR_BODY =
  '같은 부분이 두 번째도 잘 안 됐어요. 자세를 더 밀어붙이기보다, 먼저 이 보완 운동으로 필요한 힘·가동범위를 만들어봐요.';
const EXERCISE_MAX_ALT = 3;

// 32-11 (D-27 3회차) — 코치 카드 전면 승격 카피. "혼자 안 되는 건 자세가 아니라
// 방법 문제일 수 있어요" 톤.
const COACH_CARD_HEADLINE = '혼자 안 되는 건 자세가 아니라 방법 문제일 수 있어요';
const COACH_CARD_BODY =
  '같은 부분이 세 번째도 개선되지 않았어요. 이쯤이면 혼자 반복보다 강사님과 한 번 점검하는 게 빠를 수 있어요. 아래 질문을 그대로 가져가 보세요.';

// [R1] BodyProfile snapshot 요약 — 결과 화면은 분석-당시 SNAPSHOT(storedDoc.
// bodyProfile)을 source-of-truth 로 표기(재현성, live useBodyProfile 아님).
// weightKg 는 보조 ONLY (D-05) 라 요약에서 제외(점수 경로 무관 + 표기 노이즈 방지).
// 라벨은 analysis.ts 단일 출처(WR-03) — *_LABEL_KO 사용.
// 채워진 필드만 "·" 로 묶어 요약 (부분 입력 graceful). 전부 비면 null → 표기 생략.
function summarizeBodyProfile(profile: BodyProfile | null | undefined): string | null {
  if (!profile) return null;
  const parts: string[] = [];
  if (profile.heightCm != null) parts.push(`키 ${profile.heightCm}cm`);
  if (profile.experience) parts.push(`경력 ${EXPERIENCE_LABEL_KO[profile.experience]}`);
  if (profile.dominantHand) parts.push(`우세손 ${DOMINANT_HAND_LABEL_KO[profile.dominantHand]}`);
  if (profile.painAreas.length > 0) {
    parts.push(
      `통증 ${profile.painAreas.map((a) => PAIN_AREA_LABEL_KO[a]).join('·')}`,
    );
  }
  return parts.length > 0 ? parts.join(' · ') : null;
}

// 백엔드 direction → 한국어 코칭 동사. 동적 큐(회전력)는 CoachingTip.detail 문장.
const DIRECTION_LABEL: Record<JointDirection, string> = {
  extend: '더 펴주세요',
  flex: '더 굽혀주세요',
  raise: '더 올려주세요',
  lower: '더 내려주세요',
  open: '더 열어주세요',
  close: '더 모아주세요',
};

// kismam.JOINT_DIRECTION_PAIRS 동일 (계약 일치). signed delta < 0 → 첫 라벨.
//   delta = currentAngle - targetAngle.
const JOINT_DIRECTION_PAIRS: Record<string, [JointDirection, JointDirection]> = {
  left_knee: ['extend', 'flex'],
  right_knee: ['extend', 'flex'],
  left_elbow: ['extend', 'flex'],
  right_elbow: ['extend', 'flex'],
  left_hip: ['open', 'close'],
  right_hip: ['open', 'close'],
  left_shoulder: ['raise', 'lower'],
  right_shoulder: ['raise', 'lower'],
};

function directionFor(jointKey: string, signedDelta: number): JointDirection | undefined {
  const pair = JOINT_DIRECTION_PAIRS[jointKey];
  if (!pair || signedDelta === 0) return undefined;
  return signedDelta < 0 ? pair[0] : pair[1];
}

// 박제 (2026-06-06 belle): 분석 글 안 숫자 (각도/점수/거리) 를 브랜드 컬러
// (#FF4B33) 로 강조 박제. design.md §5-3 정합. tip.detail / guide.line 박제 시
// inline Text 분할 후 색 박제.
function highlightNumbers(text: string): React.ReactNode[] {
  const parts = text.split(/(\d+(?:\.\d+)?\s*(?:°|점|%|초|kg)?)/g);
  return parts.map((part, i) =>
    /\d/.test(part) ? (
      <Text key={i} style={{ color: colors.brand, fontWeight: '600' }}>
        {part}
      </Text>
    ) : (
      part
    ),
  );
}

// 결과 화면용 joint 보강: reference doc 의 실측 평균 각도(meanAngles)가 있으면
// JointScore.targetAngle/deltaDeg/direction 을 실측 기준으로 덮어쓴다.
//
// Wave 0 (Plan 12-01) wiring fix 후 j.currentAngle 박제 — 정상 path 는 백엔드
// (assemble.py) 가 실측치 채움. enrichJoints 는 reference meanAngles 가 박제
// 됐을 때 targetAngle / delta / direction 만 보강 (구 doc 호환 fallback).
function enrichJoints(
  joints: JointScore[],
  meanAngles: Record<string, number> | undefined,
): JointScore[] {
  if (!meanAngles) return joints;
  return joints.map((j) => {
    const target = meanAngles[j.key];
    if (typeof target !== 'number' || !Number.isFinite(target)) return j;
    if (typeof j.currentAngle === 'number' && Number.isFinite(j.currentAngle)) {
      const signed = j.currentAngle - target;
      return {
        ...j,
        targetAngle: target,
        deltaDeg: signed,
        direction: directionFor(j.key, signed) ?? j.direction,
      };
    }
    // currentAngle 미가용 시 (구 doc 호환) target 만 표시. angleGuide() 가 둘 다
    // 요구하므로 코칭팁 본문 노출 X — 차원 카드 score 는 정상 표시.
    return { ...j, targetAngle: target };
  });
}

// 구조화 가이드 한 줄. 데이터 부족하면 null → UI 가 노출 생략(폴백은 issue 텍스트).
function angleGuide(j: Pick<JointScore, 'currentAngle' | 'targetAngle' | 'deltaDeg' | 'direction'>):
  | { line: string; cue: string | null }
  | null {
  if (j.currentAngle == null || j.targetAngle == null) return null;
  const cue = j.direction ? DIRECTION_LABEL[j.direction] : null;
  return {
    line: `현재 ${Math.round(j.currentAngle)}° → 기준 ${Math.round(j.targetAngle)}°`,
    cue,
  };
}

// mode1 similarity 점수대별 요약 카피. 시연 시 점수 임팩트 강조용.
// 박제 (2026-06-06 belle): similarity = 관절각 차원 박제 (overall 박제 X — 모든
// 차원 평균). belle 의문 "94 vs 95% 갭" → label 박제 명확화 "관절각" 박제.
// quick-260705-o0s (belle 추가 피드백 #1): cleanPass(감점 0 = 100점 정타)면
// "거의 다 왔어요!" 류 보완 카피 금지 → 축하·유지 카피. 순수 함수 유지
// (cleanPass 를 파라미터로 받음 — isCleanPass 단일 신호 소비).
function mode1Summary(
  athleteName: string,
  similarity: number,
  cleanPass: boolean,
): string {
  if (cleanPass) {
    return `${athleteName} 선수와 동일한 수준이에요. 이 자세를 유지하세요!`;
  }
  const head = `${athleteName} 선수와 관절각 ${similarity}% 일치해요.`;
  if (similarity >= 75) return `${head} 거의 다 왔어요!`;
  if (similarity >= 50) return `${head} 핵심 구간을 다듬어 보세요.`;
  return `${head} 천천히 자세부터 잡아볼까요?`;
}

// Phase 20 (UI A1) — 비전 거부권으로 종합점수가 하향됐을 때의 Mode1 요약.
// 모순 차단(belle 디바이스 발견): 관절각 100% 일치인데 octagon 75 → "100% 일치/거의
// 다 왔어요" 가 점수와 충돌한다. veto applied 면 similarity 가 아니라 FINAL overallScore 를
// 반영하고 "교정할 점이 보인다"로 전환한다. similarity 수치 헤드라인 미노출.
function mode1VetoSummary(athleteName: string): string {
  return `${athleteName} 선수 기준으로 자세에서 교정할 점이 보여요.`;
}

// mode3 두 번째+ 요약 — '몇 % 일치'가 아니라 발전(progress)을 강조 (belle 피드백).
// 절대 차원 평균(overall)이 같은 척도라 지난 분석 대비 증감이 진짜 성장이다.
function mode3Summary(current: number, previous: number | undefined): string {
  if (previous == null) return '지난 분석과 비교했어요.';
  const d = current - previous;
  if (d > 0) return `지난 분석보다 ${d}점 발전했어요!`;
  if (d < 0)
    return `지난 분석보다 ${-d}점 내려갔어요. 아래 차원별 변화를 확인해보세요.`;
  return '지난 분석과 같은 수준을 유지했어요.';
}

// Phase 12 Wave 2 (Plan 12-03 T3) — D-12-D1/D2/D3 박제.
//
// joint 단위 평균 confidence — keypointReport.confidence flat (T × J) 의 j 열 평균.
// joint 가 KeypointName 인 경우 직접 lookup, JointScore.key (예: 'left_elbow') 인
// 경우 KeypointName 으로 매핑하지 않고 직접 매칭 시 indexOf=-1 → null 반환.
// 손 (kismam left_elbow) ↔ keypoint (left_hand) 매핑은 caller (각도 가이드 row)
// 가 책임. 본 helper 는 keypointReport.joints 의 KeypointName 만 받음.
function jointConfidenceFromReport(
  report: KeypointReport | null | undefined,
  keypointName: string,
): number | null {
  if (!report) return null;
  const j = report.joints.indexOf(keypointName as never);
  if (j < 0) return null;
  const J = report.joints.length;
  if (J <= 0 || report.frames <= 0) return null;
  let sum = 0;
  let count = 0;
  for (let t = 0; t < report.frames; t += 1) {
    const v = report.confidence[t * J + j];
    if (typeof v === 'number' && Number.isFinite(v)) {
      sum += v;
      count += 1;
    }
  }
  return count > 0 ? sum / count : null;
}

// reliability == 'low' frame 비율. D-12-D2 (≥ 0.20) / D-12-D1 (≥ 0.30) 분기 source.
function lowReliabilityRatio(report: KeypointReport | null | undefined): number {
  if (!report || report.frames <= 0) return 0;
  let low = 0;
  for (const r of report.reliability) {
    if (r === 'low') low += 1;
  }
  return low / report.frames;
}

// Phase 4 (04-02 BLOCKER-3 / MEDIUM-4 4차 게이트 리뷰) — 합성 경고 helper.
// canonical surface = result.aiSynthesisMeta.warnings (top-level
// result.warnings 아님). 본 helper 가 null/undefined guard 를 단일화해
// 호출 site 가 optional chain 을 중복 작성하지 않도록 한다.
function hasSynthesisWarning(
  result: AnalysisResult | undefined,
  code: SynthesisWarningCode,
): boolean {
  return (result?.aiSynthesisMeta?.warnings ?? []).includes(code);
}

// JointScore.key (kismam) → keypoint name 매핑은 deductionLabels.
// KEYPOINT_FROM_ANGLE_KEY 단일 출처 (quick-260704-fz4 — 로컬 중복 맵 제거).

// quick-260705-r6v → 29-PLAN-REVIEW HIGH-1 — record 투영 keypoint 규칙은
// deductionLabels.projectDeductionRecordKeypoints 공용 helper 1벌로 이관됨(로컬
// 사본 제거). 범례/시트 행동구·zoom 매칭이 record 를 관절로 되짚을 때 그 helper 를
// 그대로 소비한다 (규칙 1벌 — buildDeductionMarkers 와 동일 소스).

// quick-260705-r6v — record 행동구 resolver (범례·드릴다운 시트 공용 소스).
// 투영 keypoint(단일이면 그 관절, 그룹이면 멤버) 중 actionLabels 를 가진 첫 관절의
// 문구. 없으면 null (호출부가 criterionLabelKo 폴백 — fabricate 0).
function actionPhraseForRecord(
  rec: DeductionRecord,
  faultJoints: readonly KeypointName[] | undefined,
  actionLabels: Partial<Record<KeypointName, string>>,
): string | null {
  for (const kp of projectDeductionRecordKeypoints(rec, faultJoints)) {
    const label = actionLabels[kp];
    if (label) return label;
  }
  return null;
}

// 분석 결과 화면 (plan.md #8, design.md §8, ia AC-RES-001).
// 미설계 화면 → design.md §0 결정 트리로 자체 설계. 흰 배경(§5-1),
// 브랜드 포인트(colors.brand), 스피너/이모지 없음, 토큰만 사용.
//
// 데이터: Firestore users/{uid}/analyses/{analysisId} doc 단일 소스. 시뮬 폴백은
// Phase 26(F2/D-05)에서 샘플 미리보기 경로(샘플 화면 + 시뮬레이션 lib 2종)와
// 함께 제거됐다. doc.result 부재 시 wrapper(AnalysisResult)가 로딩/미보유 안내를
// 렌더하고, 자식(AnalysisResultContent)은 non-null result 로만 마운트해 렌더 간
// 훅 순서를 보장한다 (wrapper/Content 분리, 리뷰 HIGH-1). 실 분석 경로는
// loading.tsx 가 status='uploading' 부터 doc 를 쓴다.

// Phase 20 (UI ④) — 가짜 입문/중급/고급 65/78/88 티어 표시 제거 (belle 결정).
// 픽스처 평균치(구 lib/levels.ts)는 누적 데이터가 없어 의미가 없어 제거. 대신
// 점수에 의미를 주는 맥락을 보여준다:
//   Mode1: "정은지 기준 {score}점 — {교정 포인트} 보완하면 더 올라가요."
//          교정 포인트 = 비전 결함(primaryFault) 우선, 없으면 top 코칭 포인트.
//   self delta(지난 분석 대비 +N)는 데이터가 이미 손에 있을 때만(추가 fetch 0).
function ScoreContext({
  score,
  mode,
  athleteName,
  correctionPoint,
  selfDelta,
  cleanPass,
}: {
  score: number;
  mode: 'mode1' | 'mode3';
  athleteName: string | null;
  correctionPoint: string | null;
  selfDelta: number | null;
  // quick-260705-o0s (belle 추가 피드백 #1) — 감점 0(isCleanPass)이면 "보완하면
  // 더 올라가요" 조립 금지 (100점에 보완하라는 모순). correctionPoint 소스는
  // 무변경 — 카피 조립 단계에서만 게이트 (belle: "텍스트는 분석마다 달라져야지").
  cleanPass: boolean;
}) {
  // Mode1 1차 카피 — 정은지 기준 거리 + 교정 포인트. 교정 포인트 없으면 일반 격려.
  // cleanPass 면 correctionPoint 무시하고 통과 카피 (보완 카피는 감점 record 있을 때만).
  const primary =
    mode === 'mode1'
      ? cleanPass
        ? `${athleteName ?? '정은지'} 기준 ${score}점 — 감점 항목 없이 통과했어요.`
        : correctionPoint
          ? `${athleteName ?? '정은지'} 기준 ${score}점 — ${correctionPoint} 보완하면 더 올라가요.`
          : `${athleteName ?? '정은지'} 기준 ${score}점이에요.`
      : correctionPoint
        ? `이번 분석 ${score}점 — ${correctionPoint} 보완하면 더 올라가요.`
        : `이번 분석 ${score}점이에요.`;
  // self delta — 데이터가 손에 있을 때만 (지난 분석 doc 이미 구독 중). 없으면 생략.
  const deltaLine =
    selfDelta != null && selfDelta !== 0
      ? selfDelta > 0
        ? `지난 분석 대비 +${selfDelta}`
        : `지난 분석 대비 ${selfDelta}`
      : null;
  return (
    <View style={styles.bench}>
      <Text style={styles.benchSummary}>{highlightNumbers(primary)}</Text>
      {deltaLine && (
        <Text
          style={[
            styles.scoreDelta,
            { color: (selfDelta ?? 0) > 0 ? colors.brand : colors.textSecondary },
          ]}
        >
          {deltaLine}
        </Text>
      )}
    </View>
  );
}

// (구 DimensionScoreRow 제거 — D-03/D-12. 세부 점수 행/자세히 모달 폐기, 차원 수치는
//  감점 카드 게이지·심사 정보 코너로 흐른다.)

// (구 DIAGNOSIS_LABEL_KO / DimensionDiagnosisRow 제거 — D-03/D-12. 추상 지표
//  '동작 흐름'/'안정성' 나열 폐기, 심사 정보 코너로 대체.)

// 콤보 부분 점수 행 (베이스/확장). PartScoreRow 와 트랙 바를 공유하되 델타 없음.
function SegmentRow({ label, score }: { label: string; score: number }) {
  return (
    <View style={styles.partRow}>
      <View style={styles.partHead}>
        <Text style={styles.partLabel}>{label}</Text>
        <Text style={styles.partScore}>{score}</Text>
      </View>
      <View style={styles.track}>
        <View
          style={[
            styles.trackFill,
            { width: `${Math.max(0, Math.min(100, score))}%` },
          ]}
        />
      </View>
    </View>
  );
}

// 베이스/확장 점수 차이로 학습 경로 한 줄 안내 (reference-motions.md §7).
function segmentHint(seg: SegmentScores): string {
  if (seg.base < 65) {
    return `${seg.baseMotionName} 베이스가 아직 약해요. 베이스 동작을 먼저 다지면 이 콤보가 한결 안정됩니다.`;
  }
  if (seg.base - seg.extension >= 10) {
    return '베이스는 안정적이에요. 확장 구간에서 점수가 떨어지니 후반 동작을 집중해서 연습해보세요.';
  }
  return '베이스와 확장 구간이 고르게 나왔어요. 전체 흐름을 이어서 다듬어보세요.';
}

// Wrapper (default export) — 담당은 4가지: 파라미터 읽기, doc 구독, body profile
// 폴백 상태, 로딩/미보유 UI. doc.result 가 non-null 일 때만 자식을 마운트하므로
// 자식(AnalysisResultContent)의 훅 순서가 렌더 간 안정하다 (리뷰 HIGH-1).
// [2026-07-20] 회전 영상 기능 플래그. 백엔드 생성 Lambda 미배포 상태라 false.
// 되살릴 때 true 로 바꾸고 visual-worker/dispatch/request 를 함께 배포할 것.
const ROTATION_FEATURE_ENABLED = false;

export default function AnalysisResult() {
  const router = useRouter();
  // 33-15 (D-17) — safe-area 실측 inset (컨테이너 상단 패딩).
  const insets = useSafeAreaInsets();
  const { name, analysisId } = useLocalSearchParams<{
    name?: string;
    analysisId?: string;
  }>();
  // Firestore doc 단일 소스. 시뮬 폴백(dev 안전망)은 Phase 26(F2/D-05)에서
  // 샘플 경로와 함께 제거됐다 — doc.result 부재 시 시뮬 데이터를 렌더하지 않는다.
  const { doc: storedDoc, loading } = useAnalysisDoc(analysisId);
  // [R1] 결과 화면 BodyProfile 표기 = 분석-당시 SNAPSHOT (storedDoc.bodyProfile).
  // live useBodyProfile 을 기본 소스로 쓰지 않는다 (분석 이후 프로필을 바꿔도
  // 과거 결과 표기는 분석 당시 값으로 재현되어야 함). snapshot 이 없는 구 doc
  // 에서만 live read 를 fallback 으로 허용.
  const { profile: liveProfile } = useBodyProfile();
  // [IN-04] live 폴백은 snapshot 키가 진짜 부재(구 doc)일 때만. 신 doc 이
  // 의도적으로 빈 프로필(null)을 기록한 경우엔 폴백하지 않는다 — 분석-당시
  // 프로필이 없었으면 결과에도 없어야 재현성이 유지된다. userAnalyses 가 키
  // 부재 시 bodyProfile 을 undefined 로 두므로 undefined 만 폴백 트리거.
  const bodyProfileSnapshot =
    storedDoc?.bodyProfile === undefined
      ? liveProfile
      : storedDoc.bodyProfile;
  const bodyProfileSummary = useMemo(
    () => summarizeBodyProfile(bodyProfileSnapshot),
    [bodyProfileSnapshot],
  );

  // doc.result 가 있어야만 자식(실 데이터 렌더)을 마운트한다. 없는 동안:
  //  - loading: 구독 진행 중 → 로딩 안내
  //  - !loading: 최종 부재(문서 없음/실패) → 한국어 안내 + 홈 이동
  // 기존 에러 표시 계층 컨벤션 재사용. 시뮬 데이터는 렌더하지 않는다.
  if (!storedDoc?.result) {
    return (
      <View style={[styles.container, { paddingTop: insets.top }]}>
        <ScrollView
          contentContainerStyle={styles.content}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.header}>
            <Text style={styles.title}>분석 결과</Text>
            <Text style={styles.sub}>
              {loading
                ? '분석 결과를 불러오고 있어요.'
                : '분석 결과를 불러올 수 없어요. 다시 시도해 주세요.'}
            </Text>
          </View>
          {!loading && (
            <Pressable
              style={styles.cta}
              onPress={() => router.replace('/(tabs)')}
              accessibilityRole="button"
            >
              <Text style={styles.ctaText}>홈으로</Text>
            </Pressable>
          )}
        </ScrollView>
      </View>
    );
  }

  return (
    <AnalysisResultContent
      result={storedDoc.result}
      name={name}
      bodyProfileSummary={bodyProfileSummary}
      updatedAt={storedDoc.updatedAt}
      createdAt={storedDoc.createdAt}
      anglesFrames={storedDoc.anglesFrames}
      analysisId={storedDoc.analysisId}
    />
  );
}

// 결과 본문 — 항상 non-null result 로 마운트되므로 내부 훅 순서가 렌더 간 안정하다
// (로딩/미보유 상태는 wrapper 소관, 리뷰 HIGH-1). result 는 계약 타입 AnalysisResult
// non-nullable — 옵셔널/`| null` 금지 (타입으로 강제). referenceMotionId/Name·mode
// 파라미터는 시뮬 폴백 전용이었으므로 폴백 제거와 함께 소멸 (실 데이터의
// comparison 필드를 백엔드가 채움).
function AnalysisResultContent({
  result,
  name,
  bodyProfileSummary,
  updatedAt,
  createdAt,
  anglesFrames,
  analysisId,
}: {
  result: AnalysisResult;
  name?: string;
  bodyProfileSummary: string | null;
  // Phase 27 D-06 — pending 고아 시간 상한 폴백 기준(doc.updatedAt = complete 시점).
  updatedAt?: number;
  // 29-CONTEXT D-09 — mode1 referenceVideoUrl TTL 재발급 판단 기준(doc 생성 시각).
  createdAt?: number;
  // 29 리뷰 WR-01 — 재생바 결함 틱 초 환산 기준(doc top-level anglesFrames,
  // 9fps angles 공간 T). keypointReport.frames(18fps 업샘플)와 도메인이 달라
  // 이 값을 써야 틱이 실제 결함 시점에 찍힌다. 부재(구 doc)면 틱 생략.
  anglesFrames?: number;
  // 29 리뷰 WR-03 — 현재(좌측) 본인 영상 myVideoUrl TTL 재발급용 현재 doc ID.
  analysisId: string;
}) {
  const router = useRouter();
  // 33-15 (D-17) — safe-area 실측 inset (본문 컨테이너 상단 패딩, wrapper 와 동일).
  const insets = useSafeAreaInsets();
  const grade = scoreGrade(result.overallScore);
  const cmp = result.comparison;

  // Phase 20 TRUST-07 — Mode3 미보유/저신뢰 점수 억제 (점수카드 전체 대체).
  // iter3 HIGH-2: STRICTLY result.scoreSuppressed === true 단독 신호 — scoringBasis
  // 폴백 금지 (scoringBasis 는 source 라벨, suppression 은 display/trust 정책).
  // backend producer-contract 가 reference_free_absolute↔scoreSuppressed 를 fail-loud 로
  // 보장하므로 UI 는 이 플래그만 믿는다.
  const isScoreSuppressed =
    cmp.mode === 'mode3' && result.scoreSuppressed === true;
  // iter3 MEDIUM-1 / iter4 MEDIUM-1 — 억제 헤더 카피는 reason 이 소유 (reason-owns-copy).
  // reason 누락 시 default '기준 없음' 폴백 금지 — 중립 카피 (오라벨 방지).
  // 29-CONTEXT D-03 — "제공 불가" 단독 통보가 아니라 행동 유도(코치님 비교 /
  // 같은 동작 새 영상으로 이전 연습 비교)로 전진시킨다. belle 원문: "더 연습하고
  // 새로운 영상으로 같은 자세를 비교하면 본격 분석이 시작된다". D-05 금지어 배제.
  const suppressedHeaderCopy = isScoreSuppressed
    ? result.scoreSuppressedReason === 'recognition_low_confidence'
      ? '동작 인식 신뢰도가 낮아 기준을 확정하지 못했어요. 같은 동작을 더 또렷하게 담아 새 영상으로 다시 올려보세요.'
      : result.scoreSuppressedReason === 'unheld'
        ? '아직 이 동작의 기준 데이터가 없어요. 코치님(정은지) 영상과 비교하거나, 같은 동작을 새 영상으로 올려 이전 연습과 비교해보세요.'
        : '아직 이 동작의 기준을 확정하지 못했어요. 코치님 영상과 비교하거나, 같은 동작을 새 영상으로 올려 이전 연습과 비교해보세요.'
    : null;

  // mode1 메타 카드용 풀데이터. 시드 전이거나 로딩 중이면 motion=null →
  // 화면은 cmp.referenceMotionName / cmp.athleteName 으로 폴백 표시.
  const { motion: refMotion } = useReferenceMotion(
    cmp.mode === 'mode1' ? cmp.referenceMotionId : undefined,
  );

  // ── Phase 31 참고코너 (D-06/D-08/D-09/D-10) ────────────────────────────
  // 훅은 전부 무조건 호출한다 (리뷰 M-04) — mode 분기 안에서 훅을 부르면 mode1↔mode3
  // 사이에서 훅 순서가 달라져 React 가 상태를 잘못 연결한다. 분기는 훅에 넘기는
  // '인자'로만 표현한다.
  //
  // 신규 setInterval/폴링 0 (D-06 amended, belle option B) — 카드 갱신은 전적으로
  // useAnalysisDoc 의 onSnapshot 재렌더가 담당한다. 백그라운드 푸시 알림은 이번
  // phase 범위 밖이며, 사용자는 결과 화면을 다시 열어 완료를 확인한다.
  const nowMs = Date.now();

  // 교정 자세 이미지: 상태는 전용 correctedPoseUpdatedAtMs 로만 판정한다 (리뷰 H-06).
  // 공용 updatedAt 은 무관한 write 로도 갱신돼 pending 수명을 잘못 늘린다.
  const correctedPoseDerived = visualCardState(
    result.correctedPoseStatus,
    result.correctedPoseUpdatedAtMs,
    nowMs,
    CORRECTED_POSE_PENDING_TIMEOUT_MS,
  );
  const rotationDerived = visualCardState(
    result.rotationStatus,
    result.rotationUpdatedAtMs,
    nowMs,
    ROTATION_PENDING_TIMEOUT_MS,
  );

  // 표시 URL 은 Firestore 문서가 아니라 매번 재서명으로 받는다 (리뷰 H-02).
  // nonce 를 올리면 effect 가 다시 돌아 새 URL 을 발급한다 (만료 복구 경로).
  const [correctedPoseUrl, setCorrectedPoseUrl] = useState<string | null>(null);
  const [correctedPoseNonce, setCorrectedPoseNonce] = useState(0);
  const [correctedPoseRetried, setCorrectedPoseRetried] = useState(false);
  const [rotationUrl, setRotationUrl] = useState<string | null>(null);

  useEffect(() => {
    if (correctedPoseDerived !== 'done') {
      setCorrectedPoseUrl(null);
      return;
    }
    let alive = true;
    fetchVisualAssetUrl(analysisId, 'correctedPose')
      .then((url) => {
        if (alive) setCorrectedPoseUrl(url);
      })
      // 조용한 폴백 (D-08): 재서명 실패는 사용자에게 노출하지 않는다. URL 이 없으면
      // 카드가 로딩 자리표시로 남고 에러 문구는 뜨지 않는다.
      .catch(() => {
        if (alive) setCorrectedPoseUrl(null);
      });
    return () => {
      alive = false;
    };
  }, [correctedPoseDerived, analysisId, correctedPoseNonce]);

  useEffect(() => {
    if (rotationDerived !== 'done') {
      setRotationUrl(null);
      return;
    }
    let alive = true;
    fetchVisualAssetUrl(analysisId, 'rotation')
      .then((url) => {
        if (alive) setRotationUrl(url);
      })
      .catch(() => {
        if (alive) setRotationUrl(null);
      });
    return () => {
      alive = false;
    };
  }, [rotationDerived, analysisId]);

  // 만료/403 복구는 1회로 제한한다. 상한이 없으면 영구 실패하는 URL 에서
  // onError → 재발급 → onError 무한 루프가 돈다.
  const onCorrectedPoseImageError = () => {
    if (correctedPoseRetried) return;
    setCorrectedPoseRetried(true);
    setCorrectedPoseNonce((n) => n + 1);
  };

  // 회전 영상 온디맨드 요청 (D-06).
  const [rotationBusy, setRotationBusy] = useState(false);
  const [rotationJustRequested, setRotationJustRequested] = useState(false);
  const [rotationLimitNotice, setRotationLimitNotice] = useState<
    string | undefined
  >(undefined);

  const onRequestRotation = async () => {
    if (rotationBusy) return;
    setRotationBusy(true);
    setRotationLimitNotice(undefined);
    try {
      await requestRotationVideo(analysisId);
      // 낙관적 pending — 실제 동기화는 onSnapshot 이 한다.
      setRotationJustRequested(true);
    } catch (e) {
      // 한도 초과만 사용자에게 알린다 (인라인 1줄). code 로만 분기 —
      // message 문자열 파싱 금지 (리뷰 M-05).
      if (isDailyLimit(e)) {
        setRotationLimitNotice(
          '오늘 만들 수 있는 참고 영상을 모두 사용했어요. 내일 다시 시도할 수 있어요.',
        );
      }
      // feature_disabled / 네트워크 / 기타 → 조용히 버튼만 원복 (D-08).
      // "기능이 불안하다"는 인상을 남기지 않는다.
    } finally {
      setRotationBusy(false);
    }
  };

  const correctedPoseState: ReferenceCardState =
    correctedPoseDerived === 'hidden'
      ? 'hidden'
      : correctedPoseDerived === 'pending'
        ? 'pending'
        : correctedPoseUrl
          ? 'ready'
          : 'loading';

  const rotationState: RotationCardState = !ROTATION_FEATURE_ENABLED
    ? // [2026-07-20 belle 결정] 회전 영상은 이번 릴리스에서 끈다. 백엔드 생성
      // Lambda 3종을 배포하지 않았으므로 버튼을 누르면 실패한다 — 앱은 서버 flag 를
      // 알 수 없어 'requestable' 로 떨어지고 **없는 기능의 버튼이 노출됐다**(실기기 확인).
      //
      // 끈 이유는 품질이다: 실측 2건에서 sliding-spin 이 봉을 잡은 자세를 봉에서
      // 떨어진 다른 자세로 바꾸고 화면 자막까지 환각했다(`Sliding spin`→`Stafing spin`).
      // 회전 영상의 위험은 교정 이미지와 다르다 — **사용자가 그것을 자기 자세로
      // 착각한다.** 없는 결함을 만들어내는 시각물이라 미노출이 맞다.
      // 되살릴 때는 이 상수만 true 로 (31-CLOSEOUT.md §3).
      'hidden'
    : result.rotationStatus === undefined
      ? // 아직 요청 전 (legacy/미요청) — 온디맨드 기능의 진입점이므로 버튼을 보여준다.
        'requestable'
      : result.rotationStatus === 'failed'
        ? // 실패는 숨김. 모더레이션 차단은 재시도해도 대개 다시 막히고 과금만 든다 (D-08).
          'hidden'
        : rotationDerived === 'hidden'
          ? // pending 타임아웃 — 'failed' 와 달리 잡이 유실됐을 뿐이므로 다시 요청할 수
            // 있게 둔다. 여기서 'hidden' 으로 두면 이 분석 건에서 회전 영상 기능이
            // 영구히 사라진다 (서버가 dedupe 하므로 중복 과금 위험은 낮다).
            'requestable'
          : rotationDerived === 'pending' || rotationJustRequested
            ? 'pending'
            : rotationUrl
              ? 'ready'
              : 'pending';

  // 비교 뷰어 데이터 — mode3 는 targetRefId=null 로 내려 뷰어가 자연히 숨겨진다.
  // 정직한 강등(Pitfall 6): DTW 대응은 mode1 reference 에만 성립하므로, 학생 자세만
  // 그려놓고 "비교"라 부르지 않는다.
  const targetRefId = cmp.mode === 'mode1' ? cmp.referenceMotionId : null;
  const refDoc = useReferenceMotionDoc(targetRefId);

  const compareFrames = useMemo(
    () => pickCompareFrames(result.faultZoomComparisons),
    [result.faultZoomComparisons],
  );

  const userJoints3d = useMemo(
    () =>
      reshapePose3dData(
        result.joints3d,
        result.joints3dKeys,
        result.joints3dFrames,
      ),
    [result.joints3d, result.joints3dKeys, result.joints3dFrames],
  );

  // 프레임 인덱스는 keypointReport 프레임 공간이라 joints3d 공간으로 환산한다.
  // 원 공간 = keypointReport.frames. 부재/0 인 구 doc 은 anglesFrames, 그것도 없으면
  // 항등 매핑 폴백.
  const { viewerUserPose, viewerRefPose, viewerJointKeys } = useMemo(() => {
    const empty = {
      viewerUserPose: null as number[][] | null,
      viewerRefPose: null as number[][] | null,
      viewerJointKeys: [] as string[],
    };
    if (!compareFrames || !userJoints3d || userJoints3d.length === 0) return empty;
    const refFrames = refDoc.joints3d;
    if (!refFrames || refFrames.length === 0) return empty;

    const userKeys = result.joints3dKeys ?? refDoc.jointKeys;
    const refKeys = refDoc.jointKeys ?? result.joints3dKeys;
    if (!userKeys || !refKeys) return empty;
    // 두 문서의 keypoint 순서가 다르면 같은 인덱스가 다른 관절을 가리킨다 —
    // 뼈대가 엉뚱하게 이어진 스켈레톤을 그리느니 숨긴다 (31-08 reshape 강등과 동일 철학).
    if (
      userKeys.length !== refKeys.length ||
      userKeys.some((k, i) => k !== refKeys[i])
    ) {
      return empty;
    }

    // [fix 2026-07-20] 사용자/기준은 **서로 다른 프레임 공간**이다. 기준 인덱스를
    // 사용자 프레임 수로 환산하던 버그가 있었다: refFrameIdx(기준 keypointReport
    // 공간)를 srcFrames(사용자 anglesFrames)로 나누면, 기준 영상이 사용자보다 길 때
    // `idx >= fromFrames` 에 걸려 mapFrameIdx 가 null 을 반환하고 뷰어가 통째로
    // 숨는다. 실측: 사용자 anglesFrames 83 / refFrameIdx 90 → null → 미표시.
    // 기준(정은지)이 사용자 영상보다 긴 것은 흔하므로 대부분의 분석에서 재현됐다.
    //
    // 기준 측 원본 공간은 reference 문서의 keypointReport 프레임 수인데, 앱은 그
    // 값을 따로 들고 있지 않다. reference 의 joints3d 프레임 수(refFrames.length)가
    // 같은 공간이므로(둘 다 기준 영상 전체를 같은 샘플링으로 덮는다) 그것을 src 로
    // 쓴다 — 결과적으로 기준은 항등 매핑이 되고, 범위 검사만 유효하게 남는다.
    // [fix 2026-07-20 #2] faultZoom 인덱스의 원 공간 = **keypointReport 프레임 공간**.
    // 사용자 문서는 keypointReport 18fps(실측 frames=166) / joints3d·angles 9fps(83)
    // 로 두 공간이 갈라져 있는데, 종전 코드는 anglesFrames 를 원 공간으로 가정해
    // 항등 통과시켰다 — 뷰어가 2배 뒤 시점의 자세를 그렸다(실기기 2026-07-20,
    // 뭉개진 삼각형). reference 11건은 kr==joints3d==angles 단일 공간(전수 실측)이라
    // 아래 ref 쪽 항등 매핑은 무결. kr 부재/0 구 문서는 종전대로 anglesFrames 폴백.
    const krFrames = result.keypointReport?.frames;
    const userSrcFrames =
      (typeof krFrames === 'number' && krFrames > 0 ? krFrames : undefined) ??
      anglesFrames ??
      userJoints3d.length;
    const uIdx = mapFrameIdx(
      compareFrames.userIdx,
      userSrcFrames,
      userJoints3d.length,
    );
    const rIdx = mapFrameIdx(
      compareFrames.refIdx,
      refFrames.length,
      refFrames.length,
    );
    if (uIdx === null || rIdx === null) return empty;

    return {
      viewerUserPose: userJoints3d[uIdx] ?? null,
      viewerRefPose: refFrames[rIdx] ?? null,
      viewerJointKeys: userKeys,
    };
  }, [
    compareFrames,
    userJoints3d,
    refDoc.joints3d,
    refDoc.jointKeys,
    result.joints3dKeys,
    result.keypointReport,
    anglesFrames,
  ]);

  const correctedPoseJointLabel = result.correctedPoseJoint
    ? JOINT_LABEL_KO[result.correctedPoseJoint]
    : undefined;

  // refMotion.meanAngles 가 있으면 result.joints 의 targetAngle 을 정은지 실측
  // 평균으로 덮어쓴다 (예: 168° → 153.74°). 코칭팁 angleGuide 가 자동으로 정밀치
  // 표시. mode3 는 refMotion=null 이라 reference fallback path 미발동.
  // (Wave 0 wiring fix 후 currentAngle 박제 — enrichJoints 는 reference 측 보강만.)
  const joints = useMemo(
    () => enrichJoints(result.joints, refMotion?.meanAngles),
    [result.joints, refMotion?.meanAngles],
  );

  // mode3 두 번째+ 면 이전 분석 doc 구독 — 비교 영상(myVideoUrl)·발전 요약(overallScore)용.
  const prevAnalysisId =
    cmp.mode === 'mode3' && !cmp.isFirst ? cmp.previousAnalysisId : undefined;
  const { doc: prevDoc } = useAnalysisDoc(prevAnalysisId);

  // 박제 (2026-06-06 belle): prev doc 의 myVideoUrl S3 sign 7일 TTL 만료 시
  // (이전 분석이 6일+ 전이면) POST /playback-url 박제 재발급. fresh URL state 박제.
  const [freshPrevUrl, setFreshPrevUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!prevDoc) return;
    const SAFE_TTL_MS = 6 * 24 * 60 * 60 * 1000; // 6일 margin (7일 TTL 안전)
    const age = Date.now() - (prevDoc.createdAt || 0);
    if (age < SAFE_TTL_MS) {
      setFreshPrevUrl(null); // 만료 X — 기존 URL 사용
      return;
    }
    // 29 리뷰 WR-02 — videoFormat 은 어떤 생산 경로도 기록하지 않아(생산자 0 +
    // normalize 미매핑) 항상 undefined → ext 'mp4' 고정이었다. mov 업로드 prev
    // 재발급이 존재하지 않는 .mp4 키를 서명(서명은 객체 존재와 무관하게 성공)해
    // prev 영상이 조용히 안 떴다. 백엔드가 항상 기록하는 실측 키
    // result.myVideoKey(pipeline complete_analysis)에서 확장자를 파생한다.
    const ext = prevDoc.result?.myVideoKey?.endsWith('.mov') ? 'mov' : 'mp4';
    let cancelled = false;
    requestPlaybackUrl(prevDoc.analysisId, ext)
      .then((resp) => {
        if (!cancelled) setFreshPrevUrl(resp.playbackUrl);
      })
      .catch((err) => {
        if (__DEV__) console.warn('[playback-url] 재발급 실패', err);
      });
    return () => {
      cancelled = true;
    };
  }, [prevDoc?.analysisId, prevDoc?.createdAt, prevDoc?.result?.myVideoKey]);

  // 29 리뷰 WR-03 — 현재(좌측) 본인 영상 재발급. D-09 가 mode3 prev(freshPrevUrl)
  // 와 mode1 reference(freshRefUrl)만 배선하고 현재 doc 의 myVideoUrl 은 훅이
  // 없어, 7일 넘은 분석을 기록 탭에서 다시 열면 좌측 슬롯이 만료 URL 로 로드
  // 실패했다. freshPrevUrl 훅 1:1 미러 — 6일 초과면 현재 analysisId 로 재발급,
  // ext 는 WR-02 와 동일하게 실측 result.myVideoKey 에서 파생. 실패 시 기존
  // URL 폴백 유지(__DEV__ warn 만).
  const [freshMyUrl, setFreshMyUrl] = useState<string | null>(null);
  useEffect(() => {
    const SAFE_TTL_MS = 6 * 24 * 60 * 60 * 1000; // 6일 margin (7일 TTL 안전)
    const age = Date.now() - (createdAt || 0);
    if (age < SAFE_TTL_MS) {
      setFreshMyUrl(null); // 만료 X — 기존 myVideoUrl 사용
      return;
    }
    const ext = result.myVideoKey?.endsWith('.mov') ? 'mov' : 'mp4';
    let cancelled = false;
    requestPlaybackUrl(analysisId, ext)
      .then((resp) => {
        if (!cancelled) setFreshMyUrl(resp.playbackUrl);
      })
      .catch((err) => {
        if (__DEV__) console.warn('[playback-url] 내 영상 재발급 실패', err);
      });
    return () => {
      cancelled = true;
    };
  }, [analysisId, createdAt, result.myVideoKey]);

  // 29-CONTEXT D-09 — D1 fix (진단: presigned 7일 TTL 만료 확정 — 신선/구 mode1
  // doc 의 referenceVideoUrl 모두 AccessDenied "Request has expired" 실측).
  // mode1 우측(정은지) 영상 재발급 훅 — mode3 prev 훅(위) 미러. 분석 시점 서명
  // referenceVideoUrl 이 6일+ 경과면 referenceMotionId 로 재발급 (폴백
  // refMotion.videoUrl 은 시드 시점 서명이라 사실상 항상 만료 — 재발급이 정답).
  // 실패 시 기존 폴백 체인 유지 (__DEV__ warn 만).
  const referenceMotionIdForRefresh =
    cmp.mode === 'mode1' ? cmp.referenceMotionId : undefined;
  const [freshRefUrl, setFreshRefUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!referenceMotionIdForRefresh) return;
    const SAFE_TTL_MS = 6 * 24 * 60 * 60 * 1000; // 6일 margin (7일 TTL 안전)
    const age = Date.now() - (createdAt || 0);
    if (age < SAFE_TTL_MS) {
      setFreshRefUrl(null); // 만료 X — doc 의 referenceVideoUrl 사용
      return;
    }
    let cancelled = false;
    requestReferencePlaybackUrl(referenceMotionIdForRefresh)
      .then((resp) => {
        if (!cancelled) setFreshRefUrl(resp.playbackUrl);
      })
      .catch((err) => {
        if (__DEV__) console.warn('[playback-url] reference 재발급 실패', err);
      });
    return () => {
      cancelled = true;
    };
  }, [referenceMotionIdForRefresh, createdAt]);

  // Phase 20 (UI A1) — 비전 거부권으로 종합점수가 similarity 보다 낮아진 경우.
  // visionVeto.status==='applied' 가 1차 신호. 안전망: overallScore < similarity 면(어떤
  // 이유든) similarity 헤드라인이 octagon 과 모순되므로 절대 노출하지 않는다.
  const vetoApplied = result.visionVeto?.status === 'applied';
  const mode1Contradiction =
    cmp.mode === 'mode1' &&
    (vetoApplied || result.overallScore < cmp.similarity);
  // applied 시 결함 사유(자연어 DESCRIPTION). legacy doc 호환 — optional chaining.
  const vetoPrimaryFault =
    result.visionVeto?.status === 'applied' ? result.visionVeto.primaryFault : undefined;
  // #3 (2026-06-21) — Gemini 가 식별한 실제 결함 keypoint(backend 매핑). 있으면
  // 마커를 각도편차 최대 관절이 아니라 진짜 결함 관절에 찍는다 (legacy doc=undefined).
  const vetoFaultJoints =
    result.visionVeto?.status === 'applied' ? result.visionVeto.faultJoints : undefined;

  // quick-260704-fz4 — 2단 시각 언어 set 단일 조립 (표·마커·카드가 같은 소스 사용).
  // 빨강 = 확정 결함(감점 근거): deductionBreakdown records 의
  // angle_vs_reference__{jk} 관절 ∪ vetoFaultJoints (faultJoints 는 split_angle 등
  // 관절명 없는 vision record 의 관절 투영, CONTEXT locked).
  const confirmedKeypoints = useMemo(() => {
    const set = new Set<KeypointName>();
    for (const kp of vetoFaultJoints ?? []) set.add(kp);
    for (const r of result.deductionBreakdown?.records ?? []) {
      if (r.criterion.startsWith(ANGLE_VS_REFERENCE_PREFIX)) {
        const jk = r.criterion.slice(ANGLE_VS_REFERENCE_PREFIX.length);
        const kp = KEYPOINT_FROM_ANGLE_KEY[jk];
        if (kp) set.add(kp);
      }
    }
    return set;
  }, [vetoFaultJoints, result.deductionBreakdown]);

  // 주황 = 측정 초과·확인 권장(감점 아님, 표시 전용): veto applied 의
  // windowMedianAngleDeltas 중 |delta| > 20°(KEYPOINT_DELTA_HIGHLIGHT_DEG —
  // dimensions._LINE_TOL_DEG 정합, 신규 상수 0) 인데 확정에 없는 관절.
  // legacy/부재 → 빈 배열 (렌더 diff 0). 위양성 교훈 존중 — 감점 재해석 금지
  // ([[window-median-silent-seed-fp-reverted]]).
  const attentionKeypoints = useMemo<KeypointName[]>(() => {
    if (result.visionVeto?.status !== 'applied') return [];
    const deltas = result.visionVeto.windowMedianAngleDeltas?.deltas ?? [];
    const out: KeypointName[] = [];
    for (const d of deltas) {
      if (!Number.isFinite(d.delta_deg)) continue;
      if (Math.abs(d.delta_deg) <= KEYPOINT_DELTA_HIGHLIGHT_DEG) continue;
      const kp = KEYPOINT_FROM_ANGLE_KEY[d.joint];
      if (!kp || confirmedKeypoints.has(kp) || out.includes(kp)) continue;
      out.push(kp);
    }
    return out;
  }, [result.visionVeto, confirmedKeypoints]);

  // 마커 prop 용 배열 형태 (KeypointOverlay.highlightKeypoints). 빈 배열이면
  // 오버레이가 기존 각도편차(>20°)/worstCount 폴백으로 진행 (하위호환 동일).
  const confirmedKeypointList = useMemo(
    () => Array.from(confirmedKeypoints),
    [confirmedKeypoints],
  );

  // quick-260705-o0s → 29-CONTEXT D-01 — 감점 0 게이트 단일 신호 (belle 추가
  // 피드백 #2). 요약 카피·문제-계열 섹션 숨김·축하 섹션이 전부 이 값 하나를
  // 소비한다 (분기 산개 금지). 29-04: mode 무관화 — 29-02 가 mode3 등록 동작에
  // breakdown(records 0 + final 100)을 방출하므로 mode3 clean 도 축하 대상이다
  // (mode1 한정 제거). legacy/미등록/빈 criteria doc(breakdown 부재)은 여전히
  // false → 기존 렌더 무회귀. 감점 0 이면 veto applied 일 수 없지만(감점 record
  // 가 tally 의 실체) 각 소비처에 방어 게이트로 명시한다.
  const cleanPass = isCleanPass(result.deductionBreakdown);

  // IN-01 (quick-260724-q6b) — 역립/자기가림 저신뢰 게이트 단일 신호 (Task 3/4 공용).
  // unreliable 이면 per-joint 단정 표면(오버레이 마커·점수 내역·코칭 팁·확대비교 라벨·
  // topFix·접힘 카드·요약 헤드라인·심사 코너)을 전부 강등/억제한다. 점수 값
  // (overallScore/final/records)은 byte-불변 — 표현 전용. false/부재 시 렌더 diff 0.
  const attributionUnreliable = result.attributionReliability?.unreliable === true;

  // IN-01 — 예상 부위 단일 관절 (역립 저신뢰 오버레이 주황 점 최대 1개). angle_vs_
  // reference 감점 record 중 |points| 최대이며 keypoint 매핑되는 관절 1개, 폴백은
  // windowMedianAngleDeltas |delta_deg| 최대. 매핑 없으면 빈 배열(점 0개).
  const estimatedAreaKeypoints = useMemo<KeypointName[]>(() => {
    if (!attributionUnreliable) return [];
    let bestKp: KeypointName | null = null;
    let bestAbs = -1;
    for (const r of result.deductionBreakdown?.records ?? []) {
      if (!r.criterion.startsWith(ANGLE_VS_REFERENCE_PREFIX)) continue;
      const jk = r.criterion.slice(ANGLE_VS_REFERENCE_PREFIX.length);
      const kp = KEYPOINT_FROM_ANGLE_KEY[jk];
      if (!kp) continue;
      const abs = Math.abs(r.points);
      if (abs > bestAbs) {
        bestAbs = abs;
        bestKp = kp;
      }
    }
    if (!bestKp && result.visionVeto?.status === 'applied') {
      let bestDelta = -1;
      for (const d of result.visionVeto.windowMedianAngleDeltas?.deltas ?? []) {
        if (!Number.isFinite(d.delta_deg)) continue;
        const kp = KEYPOINT_FROM_ANGLE_KEY[d.joint];
        if (!kp) continue;
        const abs = Math.abs(d.delta_deg);
        if (abs > bestDelta) {
          bestDelta = abs;
          bestKp = kp;
        }
      }
    }
    return bestKp ? [bestKp] : [];
  }, [attributionUnreliable, result.deductionBreakdown, result.visionVeto]);

  // IN-01 (quick-260724-q6b) — 예상 부위 확대비교 진입점이 열 record 의 index.
  // estimatedAreaKeypoints 의 record 경로(angle_vs_reference + keypoint 매핑, |points|
  // 최대)와 동일 선택 로직이므로 진입점과 오버레이 주황 점이 같은 관절을 가리킨다.
  // windowMedian 폴백 경로는 대응 record 가 없어 index 없음 → null(진입점 미렌더 —
  // graceful: 안내줄 + 정은지 비교는 그대로). false/부재 시 null.
  const estimatedAreaRecordIndex = useMemo<number | null>(() => {
    if (!attributionUnreliable) return null;
    let bestIdx: number | null = null;
    let bestAbs = -1;
    const recs = result.deductionBreakdown?.records ?? [];
    for (let i = 0; i < recs.length; i++) {
      const r = recs[i];
      if (!r.criterion.startsWith(ANGLE_VS_REFERENCE_PREFIX)) continue;
      const jk = r.criterion.slice(ANGLE_VS_REFERENCE_PREFIX.length);
      const kp = KEYPOINT_FROM_ANGLE_KEY[jk];
      if (!kp) continue;
      const abs = Math.abs(r.points);
      if (abs > bestAbs) {
        bestAbs = abs;
        bestIdx = i;
      }
    }
    return bestIdx;
  }, [attributionUnreliable, result.deductionBreakdown]);

  // quick-260705-o0s — 영상 점 번호 ↔ 내역 행 번호 단일 소스 (buildDeductionMarkers).
  // 오버레이 markerNumbers 와 ScoreBreakdownSection recordNumbers 가 같은 결과물을
  // 소비해 항상 일치. markers.keypointNumbers 키는 confirmedKeypoints 의 부분집합
  // (동일 투영 규칙) — highlightKeypoints 는 기존 confirmedKeypointList 유지로 자동 정합.
  const markers = useMemo(
    () =>
      buildDeductionMarkers(
        result.deductionBreakdown?.records ?? [],
        vetoFaultJoints,
      ),
    [result.deductionBreakdown, vetoFaultJoints],
  );

  // 33-G S1/S3 (quick-260730-szk) — **부위 단위** 그룹 마커 + 부위 칩. 승인 목업 ① 은
  // 마커를 항목(부위) 단위 경계 1개로 묶고(2R#1 "동그라미가 7개") 그 아래에 부위 칩을
  // 둔다. 두 산출 모두 `regionPartKeyForRecord` 단일 출처를 소비하므로 마커 그룹 =
  // 칩 = 부위 시트가 같은 단위다 (두 번째 그룹핑 규칙 0).
  const partGroups = useMemo(
    () =>
      buildPartGroups(
        result.deductionBreakdown?.records ?? [],
        markers.recordNumbers,
        vetoFaultJoints,
      ),
    [result.deductionBreakdown, markers.recordNumbers, vetoFaultJoints],
  );
  // 부위 칩 — 입력은 전부 기존 판정 재사용 (새 게이트 신설 0): attentionKeypoints memo
  // (주황 = 감점 아님), attributionUnreliable (IN-01 저신뢰).
  const partChips = useMemo(
    () =>
      buildPartChips({
        records: result.deductionBreakdown?.records ?? [],
        recordNumbers: markers.recordNumbers,
        faultJoints: vetoFaultJoints,
        attentionKeypoints,
        estimatedArea: attributionUnreliable,
      }),
    [
      result.deductionBreakdown,
      markers.recordNumbers,
      vetoFaultJoints,
      attentionKeypoints,
      attributionUnreliable,
    ],
  );

  // quick-260705-o0s — 점수 계산 내역 상단 채점 기준 1줄 (deviationSource 자동 조립).
  const breakdownBasisLine = useMemo(
    () => composeScoringBasisKo(result.deductionBreakdown?.records ?? []),
    [result.deductionBreakdown],
  );

  // quick-260705-o0s/r6v — 문제 관절 행동 지시 문구 조립. quick-260705-r6v 부터
  // 소비처가 "영상 위 pill"(제거됨) → "전체화면 여백 범례 + 드릴다운 시트 행동구"
  // 로 이동한다. 문구는 composeShortActionLabelKo (각도 숫자 없는 짧은 행동구 —
  // 각도 수치는 '점수 계산 내역' 담당). signed delta 소스 우선순위 기존 유지:
  //   1. windowMedianAngleDeltas (mode1 veto applied — direction 의 원천)
  //   2. JointScore.deltaDeg (kismam 평균, Mode3 커버)
  // faultJointDeficits(부호 없음) 라벨 경로는 폐기 — 방향 fabricate 금지
  // (quick-260704-fwb). 부호 없는 관절은 번호 점만 — 번호가 내역 행으로
  // 안내하므로 정보 손실 아님.
  //
  // 라벨 후보 게이트:
  //   - mode1 + breakdown 보유: markers.keypointNumbers 에 있는 관절만 (감점
  //     record 관절 한정 — 영상 위 최소 표시 원칙).
  //   - mode3/legacy(breakdown 없음): 기존 소스 순서 유지, 문구만 교체.
  //   - attention(주황) 관절은 라벨 미부여 (감점 아님 — 점만).
  //   - dedupe: 동일 문자열 라벨이 2개 관절에 붙으면(hip 좌우 "다리 더 모으기"
  //     등) |delta| 큰 쪽만 라벨 유지, 나머지는 점만.
  // cleanPass 시 records 빈 배열 → markers/라벨 자연히 빈 결과 (별도 분기 불요).
  const actionLabels = useMemo<Partial<Record<KeypointName, string>>>(() => {
    // 29-CONTEXT D-01 — mode 무관화. breakdown 보유(mode1 또는 mode3 방출)면 감점
    // record 관절 한정. mode3 는 windowMedianAngleDeltas 없음(veto 미실행) — 2순위
    // JointScore.deltaDeg 경로가 커버하므로 소스 우선순위 로직 무변경.
    const hasBreakdown = result.deductionBreakdown != null;
    // quick-260705-r6v — 그룹 마커(스플릿 → 다리 4관절) 멤버 집합. 스플릿 멤버는
    // keypointNumbers 가 아니라 groupMarkers 로 이동했으므로, 게이트가 keypointNumbers
    // 만 보면 스플릿 행동구가 소멸한다(planner_findings 4). 멤버까지 라벨 후보로 허용.
    const groupMemberSet = new Set<KeypointName>();
    for (const g of markers.groupMarkers) {
      for (const kp of g.keypoints) groupMemberSet.add(kp);
    }
    // 후보 수집 — kp 당 1건 (높은 소스가 이김), dedupe 용 |delta| 동반.
    const candidates = new Map<KeypointName, { label: string; abs: number }>();
    const addCandidate = (
      angleKey: string,
      kp: KeypointName | undefined,
      signedDelta: number,
    ) => {
      if (!kp || candidates.has(kp)) return;
      if (!Number.isFinite(signedDelta)) return;
      // 감점 record 관절 한정 (breakdown 보유 시) — 번호 점(keypointNumbers) 또는
      // 그룹 마커 멤버(스플릿)인 관절만 라벨 후보.
      if (
        hasBreakdown &&
        markers.keypointNumbers[kp] == null &&
        !groupMemberSet.has(kp)
      )
        return;
      // attention(주황) = 감점 아님 → 라벨 미부여 (점만).
      if (attentionKeypoints.includes(kp)) return;
      const label = composeShortActionLabelKo(angleKey, signedDelta);
      if (label) candidates.set(kp, { label, abs: Math.abs(signedDelta) });
    };
    if (result.visionVeto?.status === 'applied') {
      for (const d of result.visionVeto.windowMedianAngleDeltas?.deltas ?? []) {
        addCandidate(d.joint, KEYPOINT_FROM_ANGLE_KEY[d.joint], d.delta_deg);
      }
    }
    for (const j of joints) {
      if (typeof j.deltaDeg !== 'number') continue;
      addCandidate(j.key, KEYPOINT_FROM_ANGLE_KEY[j.key], j.deltaDeg);
    }
    // dedupe — 같은 행동구는 |delta| 큰 관절 1개만 (좌우 구분은 마커 위치가 전달).
    const bestByLabel = new Map<string, { kp: KeypointName; abs: number }>();
    for (const [kp, { label, abs }] of candidates) {
      const cur = bestByLabel.get(label);
      if (!cur || abs > cur.abs) bestByLabel.set(label, { kp, abs });
    }
    const map: Partial<Record<KeypointName, string>> = {};
    for (const [label, { kp }] of bestByLabel) map[kp] = label;
    return map;
  }, [
    cmp.mode,
    result.deductionBreakdown,
    result.visionVeto,
    joints,
    markers,
    attentionKeypoints,
  ]);

  // quick-260705-r6v — 전체화면 여백 고정 범례 조립. 번호 있는 record 순서대로
  // "① 행동구 −감점". 행동구는 actionPhraseForRecord(범례·시트 동일 소스), 없으면
  // criterionLabelKo 폴백(fabricate 0). cleanPass/legacy 면 자연히 빈 배열.
  const fullscreenLegend = useMemo(() => {
    const recs = result.deductionBreakdown?.records ?? [];
    const out: { number: number; text: string }[] = [];
    recs.forEach((rec, i) => {
      const num = markers.recordNumbers[i];
      if (num == null) return;
      const phrase = actionPhraseForRecord(rec, vetoFaultJoints, actionLabels);
      const label = phrase ?? criterionLabelKo(rec.criterion);
      out.push({
        number: num,
        text: `${label} −${formatDeductionNumber(Math.abs(rec.points))}`,
      });
    });
    return out;
  }, [result.deductionBreakdown, markers, vetoFaultJoints, actionLabels]);

  // quick-260705-r6v — 재생바 결함 시점 틱 (buildDeductionTicks — window median
  // 시점 1개에 번호 병합). veto 미적용/legacy/mode3 면 빈 배열 (틱 생략).
  const timelineTicks = useMemo(
    () =>
      buildDeductionTicks(
        result.deductionBreakdown?.records ?? [],
        markers.recordNumbers,
        result.visionVeto,
      ),
    [result.deductionBreakdown, markers.recordNumbers, result.visionVeto],
  );

  // 33-13 (A-6, D-18 양방향 대응) — breakdown record 보유 doc 의 영상 위 빨강
  // 마커는 buildDeductionMarkers 투영(번호 점 관절 + 그룹 멤버)으로만 구성한다 —
  // record 와 짝 없는 마커(고아)는 미렌더. 종전 소스(confirmedKeypointList =
  // records 투영 ∪ vetoFaultJoints 전체)는 record 투영 밖 faultJoints 여분이
  // 무번호 빨강 점을 만들 수 있었다. breakdown 부재(legacy)는 기존 소스 유지
  // (record 가 없어 양방향 대응 자체가 정의 불가 — graceful 하위호환).
  const hasBreakdownRecords =
    (result.deductionBreakdown?.records.length ?? 0) > 0;
  const markerBackedKeypoints = useMemo<KeypointName[]>(() => {
    const set = new Set<KeypointName>();
    for (const kp of Object.keys(markers.keypointNumbers) as KeypointName[]) {
      set.add(kp);
    }
    for (const g of markers.groupMarkers) {
      for (const kp of g.keypoints) set.add(kp);
    }
    return Array.from(set);
  }, [markers]);

  // IN-01 (quick-260724-q6b) — 역립 저신뢰 시 오버레이 per-joint 마커 강등 파생.
  // unreliable 이면 확정 빨강 점/번호/그룹/범례/틱을 모두 비우고 예상 부위 주황 점
  // 최대 1개(estimatedAreaKeypoints)만 남긴다 — 번호가 사라졌으므로 범례/틱도 빈
  // 배열로 두어 모순 방지. false/부재 시 기존 소스 그대로 → 렌더 diff 0.
  const overlayHighlightKeypoints = attributionUnreliable
    ? []
    : hasBreakdownRecords
      ? markerBackedKeypoints
      : confirmedKeypointList;
  const overlayAttentionKeypoints = attributionUnreliable
    ? estimatedAreaKeypoints
    : attentionKeypoints;
  // 33-G S1 (quick-260730-szk) — breakdown record 보유 doc 은 **부위 단위 그룹 경계**를
  // 쓴다(승인 목업 ①). 그 경로에서는 개별 번호 점(markerNumbers)을 비워 그룹 배지가
  // 번호를 전담한다 (N-4 — 그룹 타원 + 멤버 빨강 원 동시 렌더가 S1 PARTIAL 의 실체).
  // legacy(breakdown 부재) doc 은 기존 groupMarkers/keypointNumbers 경로 그대로.
  const overlayGroupMarkers = attributionUnreliable
    ? []
    : hasBreakdownRecords
      ? partGroups.map((g) => ({
          // 탭·범례 조인은 번호로 하므로 대표 번호 = 최소 번호 (N-3, 틱 선례).
          number: g.numbers[0],
          keypoints: g.keypoints,
          badgeLabel: g.badgeLabel,
        }))
      : markers.groupMarkers;
  const overlayMarkerNumbers = attributionUnreliable
    ? {}
    : hasBreakdownRecords
      ? {}
      : markers.keypointNumbers;
  // 33-13 — record 보유 doc 은 강제 강조 폴백 0 (편차 최대 N 강조는 record 와
  // 짝 없는 고아 마커 — D-18). legacy(breakdown 부재)만 기존 폴백 유지.
  const overlayForceHighlightWorstCount = attributionUnreliable
    ? 0
    : hasBreakdownRecords
      ? 0
      : vetoApplied
        ? 2
        : 0;
  const overlayFullscreenLegend = attributionUnreliable ? [] : fullscreenLegend;
  const overlayTimelineTicks = attributionUnreliable ? [] : timelineTicks;

  // quick-260702-q8q → 29-CONTEXT D-01 — "점수 계산 내역" 섹션 렌더 가드.
  // 29-04: mode 무관화 — deductionBreakdown 보유 doc 만 (29-02 가 mode3 등록 동작
  // md 보유 시에만 방출하므로 미등록/legacy/빈 criteria 동작은 필드 부재 → 섹션
  // 자연 숨김, normalize 가 malformed 를 undefined 로 접음 — 크래시 0). mode1 전용
  // 조건 제거 근거 = 29-CONTEXT D-01 (mode3 투명 감점-합산 소비).
  const showBreakdownSection = result.deductionBreakdown != null;

  // 33-15 (D-16) — 각도 수치 이동 게이트. 점수 계산 내역 카드가 있을 때만 코칭 팁
  // 카드에서 각도 수치를 걷어낸다 (이동, 삭제 아님). legacy doc(내역 카드 부재)은
  // 코칭 팁의 각도 줄이 수치의 유일한 거처라 종전 렌더 유지 — 이동 불가 시 삭제
  // 금지 ([[scoring-must-be-transparent-deduction-tally]] 투명 공개 원칙).
  const angleNumbersRelocated = showBreakdownSection;

  // Phase 20 (UI ④) — 점수 맥락 카드의 "교정 포인트". 비전 결함(primaryFault)
  // 우선, 없으면 top 코칭 팁 제목(가장 먼저 다듬을 관절). 둘 다 없으면 null →
  // 일반 격려 카피. 추가 fetch 0 (이미 result 에 있는 데이터만 사용).
  // IN-01 (quick-260724-q6b) — 역립 저신뢰 시 헤드라인에 관절명이 새지 않도록 null.
  const correctionPoint = attributionUnreliable
    ? null
    : (vetoPrimaryFault ?? result.tips[0]?.title ?? null);

  const summary =
    cmp.mode === 'mode1'
      ? cleanPass
        ? mode1Summary(cmp.athleteName, cmp.similarity, true)
        : mode1Contradiction
          ? mode1VetoSummary(cmp.athleteName)
          : mode1Summary(cmp.athleteName, cmp.similarity, false)
      : cmp.isFirst
        ? '첫 분석이에요. 다음 분석부터 발전을 비교해드려요.'
        : mode3Summary(result.overallScore, prevDoc?.result?.overallScore);

  // 표시할 차원 = 결과에 존재하는 차원만 (mode1=3, mode3 first=2 또는 1, mode3 second+=3).
  // 재설계 이전 문서(옛 partScores·dimensionScores 없음)는 빈 객체로 폴백 — 크래시 방지.
  const dimensionScores = result.dimensionScores ?? {};
  // (구 dims/dimensionExplanation/detailDim/DimensionDetailModal 제거 — D-03/D-12.
  //  차원 수치는 summaryContent 칭찬 적격 판정·심사 정보 코너로만 흐른다.)
  // Phase 12.5 T9: 코칭 팁 "자세히 ›" 모달 state. tip null = 닫힘.
  const [detailTip, setDetailTip] = useState<CoachingTip | null>(null);
  // Phase 13 (Plan 13-A): "다른 운동 보기" 전체 라이브러리 모달 state. false = 닫힘.
  const [exerciseModalOpen, setExerciseModalOpen] = useState(false);

  // quick-260705-r6v — 감점 드릴다운 시트 state (record index). null = 닫힘.
  // 진입점 3개(내역 행/여백 범례/세로 카드 번호 점)가 이 state 하나를 연다.
  const [detailRecordIndex, setDetailRecordIndex] = useState<number | null>(null);
  // 번호 → recordIndex 역매핑 (번호 unique). 범례·번호 점 탭이 번호로 연다.
  const openRecordByNumber = (markerNumber: number) => {
    const idx = markers.recordNumbers.indexOf(markerNumber);
    if (idx >= 0) setDetailRecordIndex(idx);
  };
  // 33-G S6 (quick-260730-py1) — 시트는 **부위 단위**다. 진입점 7곳이 전부
  // detailRecordIndex 로 모이므로 진입점 수정 없이 여기서 record → 부위 뷰모델로
  // 승격한다. 조판·카피 조립은 lib/deductionSheet 소유 (사본 0).
  //
  // zoom 매칭 (33-12 A-5, seam #1) — criterion 키 일치 1차 + legacy 교집합 폴백.
  // 규칙 단일 출처 = deductionLabels.matchZoomForDeductionRecord (region-first
  // 첫 매치 추측 조인 제거 — defect #5 앱측 반쪽). advisory 는 감점 시트에
  // 오매칭 금지 (기존 규칙). 없으면 null (사진 없이 수치·문구만 — graceful).
  const sheetZooms = useMemo<(FaultZoomComparison | null)[]>(
    () =>
      (result.deductionBreakdown?.records ?? []).map((rec) =>
        matchZoomForDeductionRecord(
          rec,
          vetoFaultJoints,
          result.faultZoomComparisons ?? [],
        ),
      ),
    [result.deductionBreakdown, vetoFaultJoints, result.faultZoomComparisons],
  );
  // paircap 우측 라벨 — 승인본 6R 문형 `기준 (정은지)`. mode3 는 `지난 영상`.
  // (crop 위 halfLabel 용 rightLabel 은 기존 문형 `{name} 선수` 유지 — 두 표면의
  //  승인 문형이 서로 다르다.)
  const rightPairLabel =
    cmp.mode === 'mode1' ? `기준 (${cmp.athleteName})` : '지난 영상';
  const sheetView = useMemo(() => {
    const records = result.deductionBreakdown?.records ?? [];
    if (records.length === 0) return null;
    return buildRegionSheetView({
      records,
      recordNumbers: markers.recordNumbers,
      actionPhrases: records.map((rec) =>
        actionPhraseForRecord(rec, vetoFaultJoints, actionLabels),
      ),
      zooms: sheetZooms,
      selectedRecordIndex: detailRecordIndex,
      rightPairLabel,
      estimatedArea: attributionUnreliable,
      faultJoints: vetoFaultJoints,
    });
  }, [
    result.deductionBreakdown,
    markers.recordNumbers,
    vetoFaultJoints,
    actionLabels,
    sheetZooms,
    detailRecordIndex,
    rightPairLabel,
    attributionUnreliable,
  ]);
  // 상단 크롭 = 그룹 크롭을 낳은 record 의 카드. refMatch 정직 캡션도 이 카드 기준.
  const sheetPrimaryZoom =
    sheetView != null ? sheetZooms[sheetView.primaryRecordIndex] ?? null : null;
  // 블록 안 크롭 (M-5) — 상단 크롭과 다른 카드를 가진 블록만. 기존에 보이던
  // 증거를 조용히 잃지 않는다.
  const sheetBlockZooms = useMemo<Record<number, FaultZoomComparison | null>>(() => {
    const map: Record<number, FaultZoomComparison | null> = {};
    for (const block of sheetView?.blocks ?? []) {
      if (block.blockRecordIndexForCrop != null) {
        map[block.blockRecordIndexForCrop] =
          sheetZooms[block.blockRecordIndexForCrop] ?? null;
      }
    }
    return map;
  }, [sheetView, sheetZooms]);

  // Phase 27 D-06 — zoom 사후 도착. contract.md faultZoomStatus 절.
  // 27-06 이 점수/verdict/감점 내역을 status='done' 시점에 먼저 도착시키고, zoom PNG
  // 는 result.faultZoomStatus 'pending'→'done'/'failed' 부분 업데이트로 뒤따르게 했다.
  // 앱은 useAnalysisDoc onSnapshot 구독으로 자동 rerender — 추가 폴링 0(안티패턴).
  //   'pending' = 렌더 중 → 확대카드 자리에 로딩 placeholder (아래 zoomPending).
  //   'done'    = 도착 → faultZoomComparisons 유효 → selectedZoom 카드 자동 표시.
  //   'failed'/'done'-무매칭/필드 부재(legacy) = selectedZoom null → 기존 graceful 숨김.
  // T-27-21: pending 이 끝내 done/failed 로 전이되지 못하면(고아) placeholder 가
  //   무한 표시될 수 있다 — updatedAt(complete 시점) 기준 상한 경과 시 숨김으로 폴백.
  //   updatedAt 변경(zoom 부분 업데이트가 updatedAt 을 갱신)마다 타이머 재무장.
  const [zoomPendingTimedOut, setZoomPendingTimedOut] = useState(false);
  useEffect(() => {
    setZoomPendingTimedOut(false);
    if (result.faultZoomStatus !== 'pending') return;
    const elapsed = Date.now() - (updatedAt ?? 0);
    const remaining = FAULT_ZOOM_PENDING_TIMEOUT_MS - elapsed;
    if (remaining <= 0) {
      // 이미 상한 초과(예: 앱을 오래 뒤에 다시 열었을 때) — 즉시 숨김 폴백.
      setZoomPendingTimedOut(true);
      return;
    }
    const t = setTimeout(() => setZoomPendingTimedOut(true), remaining);
    return () => clearTimeout(t);
  }, [result.faultZoomStatus, updatedAt]);
  // pending 이고 아직 상한 이내면 placeholder 표시(도착 대기). zoom 이 실제 도착하면
  // faultZoomStatus='done' 으로 전이돼 이 값은 자연히 false 가 된다.
  const zoomPending =
    result.faultZoomStatus === 'pending' && !zoomPendingTimedOut;

  // 28-CONTEXT D-01 — malformed/legacy → null = 현행 절대시계 (ASVS V5 방어 소비).
  // result.motionAlignment 를 소비측 normalizeMotionAlignment 로 재검증 후 VideoCompare
  // alignment prop 으로 전달한다. 필드 부재(legacy)·모순(malformed) → null → VideoCompare
  // 가 기존 절대시계 재생 100% 보존(28-06 계약). 순수 함수라 재계산 비용은 미미하나
  // 관례상 useMemo(result 의존)로 감싼다.
  const videoAlignment = useMemo(
    () => normalizeMotionAlignment(result.motionAlignment ?? null),
    [result],
  );

  // quick-260705-o0s — Phase 9 힘-패턴 원인 카드 섹션 삭제 (belle 실기기 캡처
  // 확인: 코칭 팁 '먼저 교정할 점'과 중복). ForcePatternCard/
  // ForcePatternDetailModal + fallback finding/measuredEvidence 조립 연쇄 제거.
  // 시트 고유 정보 흡수처: 측정 방법 문구 → 채점 기준 1줄 + 내역 detailText /
  // 가능한 원인 → '먼저 교정할 점' vetoRootCauses / 관절별 현재→기준 각도 →
  // 코칭 팁 angleGuide. openQuestionsForCoach 는 forcePatternInference.
  // coachCommentHook 을 계속 소비 (다른 데이터 경로 — 유지).

  // Phase 11 (Plan 11-02, COACH-01 / D-06 / HIGH-2) — "강사에게 확인할 점" 섹션.
  // 두 리포트(forcePatternInference + bodyComparisonReport)의 coachCommentHook.
  // openQuestionsForCoach 를 **병합**한다. 첫 non-null array 만 고르는 `??`-chain
  // 금지 — array 는 nullish 가 아니라 force hook 존재 시 body 질문이 영구 누락된다
  // (review HIGH-2). 각 source 는 `?? []` 로 받고 concat → trim → Boolean filter →
  // de-dupe → slice(0,5).
  // D-06: openQuestionsForCoach 만 v1 화면에 노출한다. hook 의 나머지 LLM 요약/큐
  // 필드는 저장만 되고 v1 비노출, 강사 입력 필드(coachComment / reviewedBy)는 v2.
  const openQuestionsForCoach = useMemo(() => {
    const force =
      result.forcePatternInference?.coachCommentHook?.openQuestionsForCoach ??
      [];
    const body =
      result.bodyComparisonReport?.coachCommentHook?.openQuestionsForCoach ??
      [];
    return [...force, ...body]
      .map((q) => q.trim())
      .filter(Boolean)
      .filter((q, i, arr) => arr.indexOf(q) === i)
      .slice(0, 5);
  }, [
    result.forcePatternInference?.coachCommentHook,
    result.bodyComparisonReport?.coachCommentHook,
  ]);

  // Phase 12 Wave 1 (Plan 12-02 T4) — KeypointOverlay 박제 site (R7 render prop).
  // VideoCompare 가 player lifecycle 안에서 callback 호출. Wave 1 = 정적
  // frameIndex=0 + visible=true (토글 UI 는 Wave 2 책임).
  // videoSize 는 9:16 영상 native 비율 기본값 — VideoView contentFit="contain"
  // 위 normalized 0..1 좌표 그대로 박제 (KeypointOverlay viewBox 가 자동 scale).
  const overlayVideoSize = { width: 720, height: 1280 };

  const userKeypointReport = result.keypointReport ?? null;
  const referenceKeypointReport = refMotion?.referenceKeypointReport ?? null;

  // 32-02 (D-16) — legacy doc(정렬 disabled/부재) 자동 시작 오프셋(sec). faultZoomComparisons
  // 프레임 인덱스 쌍들의 median 으로 "대략 오프셋"을 산출해 VideoCompare 에 넘긴다
  // (정렬 활성 doc 은 VideoCompare 내부 dirty 가드가 무시 — offset 0 시작). 유효 쌍 0 →
  // null → 0(오프셋 없음, 슬라이더만 제공).
  //
  // ⚠ 33-G F-3 (quick-260730-py1): 구 주석의 "poseFrames 정본과 동일 환산" 선언은
  // **폐기**됐다. 참고코너 poseFrames 는 이제 백엔드 방출 초(userVideoSec/refVideoSec)
  // 를 쓰고 rep 인덱스÷fps 추정을 하지 않는다. 여기 남은 rep÷fps 환산은 VideoCompare
  // **정렬 시작 오프셋** 전용이며(동작 비교 거동 = 이미 PASS 표면) 이 단위 범위 밖이다 —
  // 폐기된 규칙을 다시 복제하지 말 것. 초 정합 확장은 백엔드 초 방출 범위가 넓어질 때
  // 별 단위로 판정한다.
  const legacyStartOffsetSec = useMemo(
    () =>
      legacyOffsetFromCompareFrames(
        result.faultZoomComparisons ?? null,
        result.keypointReport?.fps || 9,
        referenceKeypointReport?.fps || 18,
      ) ?? 0,
    [
      result.faultZoomComparisons,
      result.keypointReport?.fps,
      referenceKeypointReport,
    ],
  );

  // Phase 12 Wave 2 (Plan 12-03 T2) → 33-13 (A-6, D-13) — 스켈레톤 토글.
  // belle: "뭘 잡은거지" — 설명 없는 키포인트 12점 상시 노출 금지 → **기본 숨김 +
  // 옵트인**으로 반전 (useState(false), 저장값 'true' 일 때만 켬).
  //
  // 33-G F-8 (quick-260730-szk, D-42) — 종전 주석은 "감점 마커는 skeletonVisible 무관
  // 상시 렌더" 였다. belle 확인 ② 가 그것을 반려했다: 결과 화면에 들어오자마자 설명
  // 없는 표시가 영상을 덮는다. D-42 = **상시 마커 제거** → 마커 계층은 이 토글 ON
  // 또는 음성 큐 강조 중에만(`markersVisible`). 상시 진입점은 영상 카드 아래 **부위
  // 칩**(PartChipsRow)이 대체하고, 번호 ↔ 내역 행 양방향 대응(D-18)은 남은 4진입점
  // (칩·내역 행·재생바 틱·전체화면 여백 범례)이 유지한다.
  //
  // AsyncStorage key '@sunity:keypoint_overlay_enabled' — Firebase Auth backing
  // store 와 namespace 충돌 0 ([[firebase-project-account]] 정합, T-12-03-T4).
  const [overlayVisible, setOverlayVisible] = useState<boolean>(false);
  useEffect(() => {
    AsyncStorage.getItem('@sunity:keypoint_overlay_enabled')
      .then((v) => {
        if (v === 'true') setOverlayVisible(true);
      })
      .catch(() => {
        /* graceful — 시각 토글 default(숨김) 보존 */
      });
  }, []);
  const handleToggleOverlay = (next: boolean) => {
    setOverlayVisible(next);
    AsyncStorage.setItem(
      '@sunity:keypoint_overlay_enabled',
      next ? 'true' : 'false',
    ).catch(() => {
      /* graceful — UI 는 이미 반영 */
    });
  };

  // Phase 12 Wave 2 — 사용자 측 키포인트만 floating angle label 노출.
  // mode1 reference 측 jointAngles 는 미공급 (A2 deferred, 12-deferred-items.md).
  //
  // jointAngles 구성 = JointScore (kismam 산출) 의 평균 current/target 각도.
  // angle key (left_elbow 등) → KeypointOverlay 내부 JOINT_KEY_TO_ANGLE_KEY 가
  // KeypointName 으로 변환. 산출 출처 분리: backend 만 (UI 단 좌표/각도 산출 0).
  const userJointAngles = useMemo(() => {
    const map: Record<string, { current: number | null; target: number | null }> = {};
    for (const j of joints) {
      map[j.key] = {
        current: typeof j.currentAngle === 'number' ? j.currentAngle : null,
        target: typeof j.targetAngle === 'number' ? j.targetAngle : null,
      };
    }
    return map;
  }, [joints]);

  // Phase 12 Wave 2 (Plan 12-03 T3) — confidence/occlusion 표기 (D-12-D1/D2 박제).
  // 영상 전체 low reliability frame 비율 — 차원 카드 ⚠ badge (≥ 0.20) +
  // 코칭 팁 row 추정 표기 (≥ 0.30) 분기 source.
  const lowReliabilityRatioVal = useMemo(
    () => lowReliabilityRatio(userKeypointReport),
    [userKeypointReport],
  );
  // (구 참고 지표 occlusion badge 제거 — D-03/D-12. 가림 신호는 코칭 팁 추정
  //  표기(isAngleEstimated)로만 노출. lowReliabilityRatioVal 은 그 경로에서 소비.)

  // #4 (2026-06-21) — 3D 자세 뷰어 제거. RTMW joints3d 는 깊이 없음(y≈0)이라 진짜
  // 회전 3D 가 원리적으로 불가 → 평면 뼈대를 "3D" 로 보여주던 오인 UI 였다. belle:
  // "영상에서 돌릴 수 있어야"(camera-angle-AI). 리서치 결론: 충실한(자세 환각 없는)
  // 카메라각 합성 API 는 현재 없음(생성형=환각, in-house 메시=라이선스 차단) →
  // belle 방향 결정 대기. 그동안 깨진 뷰어는 즉시 제거(미루기 금지 원칙).

  // 코칭 팁 row 의 각도 표시 분기 = (joint 평균 confidence < 0.5) 또는
  // (low reliability frame 비율 ≥ 0.30). 추정 표기 + ⓘ tap → Alert.
  const isAngleEstimated = (jointKey: string): boolean => {
    if (lowReliabilityRatioVal >= 0.3) return true;
    const kpName = KEYPOINT_FROM_ANGLE_KEY[jointKey];
    if (!kpName) return false;
    const c = jointConfidenceFromReport(userKeypointReport, kpName);
    if (c == null) return false;
    return c < 0.5;
  };

  const showEstimateTooltip = () => {
    Alert.alert(
      '추정값',
      '이 구간은 가림 또는 측정 불확실로 추정값입니다.',
    );
  };

  // Phase 20 (UI ①) — 비전 거부권 적용 시 "거의 동일/일치도 100/거의 다 왔어요"
  // 류 모순 카피를 코칭 팁에서도 제거한다 (헤드라인은 mode1VetoSummary 로 이미
  // 차단됨). backend tip 본문이 75 헤드라인과 충돌하지 않도록 방어. veto 미적용
  // (정타) 영상은 원본 tips 그대로 — 정상 칭찬 카피 보존.
  const displayTips = useMemo(() => {
    const CONTRADICTORY = ['거의 동일', '일치도 100', '거의 다 왔'];
    const base = !vetoApplied
      ? result.tips
      : result.tips.filter((tip) => {
          const text = `${tip.title} ${tip.detail}`;
          return !CONTRADICTORY.some((phrase) => text.includes(phrase));
        });
    // IN-01 (quick-260724-q6b) — 역립 저신뢰 시 per-joint 팁(tip.joint != null) 제거
    // (관절 단정 금지). generic 팁만 남긴다. false/부재 시 base 그대로.
    return attributionUnreliable
      ? base.filter((tip) => tip.joint == null)
      : base;
  }, [result.tips, vetoApplied, attributionUnreliable]);

  // 33-15 (D-16) — 코칭 팁 카드에서 걷어낸 각도 수치의 새 거처 행 조립. 소스는
  // 종전 팁 각도 줄과 동일(displayTips 관절의 angleGuide) — 모순 카피 필터·IN-01
  // 저신뢰 per-joint 억제가 그대로 승계되므로 저신뢰 시 자연히 빈 배열(관절 단정 0).
  // 관절 라벨 = JOINT_LABEL_KO 데이터 키잉 (동작명 하드코딩 0, 10동작 공통).
  // isAngleEstimated 는 lowReliabilityRatioVal/userKeypointReport 파생.
  const angleReferenceRows = useMemo(() => {
    const out: {
      key: string;
      label: string;
      line: string;
      estimated: boolean;
    }[] = [];
    for (const tip of displayTips) {
      if (!tip.joint) continue;
      if (out.some((r) => r.key === tip.joint)) continue;
      const joint = joints.find((j) => j.key === tip.joint);
      if (!joint) continue;
      const guide = angleGuide(joint);
      if (!guide || joint.currentAngle == null || joint.targetAngle == null) {
        continue;
      }
      const estimated = isAngleEstimated(tip.joint);
      out.push({
        key: tip.joint,
        label: JOINT_LABEL_KO[tip.joint] ?? tip.joint,
        line: `${estimated ? '추정' : '현재'} ${Math.round(joint.currentAngle)}° → 기준 ${Math.round(joint.targetAngle)}°`,
        estimated,
      });
    }
    return out;
    // isAngleEstimated 는 아래 deps 파생 (lowReliabilityRatioVal/userKeypointReport).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayTips, joints, lowReliabilityRatioVal, userKeypointReport]);

  // quick-260704-fwb — '먼저 교정할 점' 카드 처방 구조. 상태(primaryFault) 아래
  // 원인 기전(rootCauseHypotheses 상위 2건, supportCount 내림차순, '~로 보임' 가설
  // 어투 그대로 — 측정 안 된 단정 금지) + 처방 연결(결함 관절 매칭 첫 팁 detail).
  // 전부 저장된 값만 사용 — 부재 시 섹션 생략/폴백 한 줄 (legacy doc 크래시 0).
  const vetoRootCauses = useMemo(() => {
    if (result.visionVeto?.status !== 'applied') return [];
    const hyps = result.visionVeto.rootCauseHypotheses ?? [];
    return hyps
      .filter((h) => typeof h.text === 'string' && h.text.length > 0)
      .slice()
      .sort(
        (a, b) =>
          (typeof b.supportCount === 'number' ? b.supportCount : 0) -
          (typeof a.supportCount === 'number' ? a.supportCount : 0),
      )
      .slice(0, 2);
  }, [result.visionVeto]);
  const vetoFixTip = useMemo(() => {
    if (!vetoApplied) return null;
    const faultJoints = vetoFaultJoints ?? [];
    if (faultJoints.length === 0) return null;
    return (
      displayTips.find(
        (tip) => tip.joint != null && faultJoints.some((j) => j === tip.joint),
      ) ?? null
    );
  }, [vetoApplied, vetoFaultJoints, displayTips]);

  // (구 deltaFor 제거 — DimensionScoreRow delta 행 폐기와 함께 미사용.)

  // ══════════════════════════════════════════════════════════════════════
  // 32-11 대배선 — 요약/섹션/조인 뷰모델 (리뷰 MEDIUM: 파생 계산 useMemo).
  // 위 기존 파생값(markers/actionLabels/joints/veto…)을 소비해 새 컴포넌트
  // (SummaryCard/DeductionCard/cueTrack)로 조립한다. 순서·가시성은 resultSections
  // 뷰모델 단일 지점이 결정하고, 카드 상호작용은 recordId 조인 맵으로만 잇는다.
  // ══════════════════════════════════════════════════════════════════════

  const records = useMemo(
    () => result.deductionBreakdown?.records ?? [],
    [result.deductionBreakdown],
  );
  const hasRecords = records.length > 0;

  // 32-13 (D-23) — 스팟체크 불일치 카드 숨김 recordId 집합. 표시 정책
  // (contract.md §12.8): status 'done' 일 때만 적용 — 부재(legacy)/pending/
  // skipped/failed 는 빈 집합 = 전 카드 표시 (fail-open). recordId 없는 legacy
  // record 는 조인 불가 = 표시 유지.
  //
  // ★숨김 경계 (채점 tally 불변): 이 집합은 감점 카드 **표면**(top-1 완결형,
  // 접힘 목록, 재생 중 큐 자막·오디오, 요약 카드 파생)에만 적용한다.
  // ScoreBreakdownSection(점수 계산 내역 투명 tally)과 DeductionDetailSheet
  // 드릴다운 내역은 절대 필터하지 않는다 — 점수·감점 합산의 투명성은 숨김
  // 권한 밖 ([[scoring-must-be-transparent-deduction-tally]], T-32-30).
  const hiddenRecordIds = useMemo(() => {
    const sc = result.spotCheck;
    if (sc?.status !== 'done') return new Set<string>();
    return new Set(sc.hiddenRecordIds);
  }, [result.spotCheck]);
  const isRecordHidden = (rec: DeductionRecord): boolean =>
    rec.recordId != null && hiddenRecordIds.has(rec.recordId);

  // top-1 감점 record index — 미션 record 우선(result.mission.recordId), 없으면 최대
  // 감점(points 가장 음수). cleanPass/legacy 면 -1. 스팟체크 숨김 record 는 top-1
  // 후보에서 제외 (숨긴 문장을 요약·완결형 카드로 되살리지 않음 — D-23).
  const topFixIndex = useMemo(() => {
    if (records.length === 0) return -1;
    const mid = result.mission?.recordId;
    if (mid && !hiddenRecordIds.has(mid)) {
      const i = records.findIndex((r) => r.recordId === mid);
      if (i >= 0) return i;
    }
    let best = -1;
    for (let i = 0; i < records.length; i += 1) {
      const rid = records[i].recordId;
      if (rid != null && hiddenRecordIds.has(rid)) continue;
      if (best < 0 || records[i].points < records[best].points) best = i;
    }
    return best;
  }, [records, result.mission?.recordId, hiddenRecordIds]);
  const topFixRecord = topFixIndex >= 0 ? records[topFixIndex] : null;
  const topFixKey =
    topFixIndex >= 0 ? recordKeyForIndex(records, topFixIndex) : null;

  // DeductionRecord(계약) → DeductionCardRecord(카드 로컬 모양) 매핑.
  const toCardRecord = (rec: DeductionRecord): DeductionCardRecord => ({
    recordId: rec.recordId,
    label: criterionLabelKo(rec.criterion),
    statusLine: rec.statusLine,
    whyLine: rec.whyLine,
    cueLine: rec.cueLine,
    points: rec.points,
    measured: rec.measuredValue,
    target: rec.baselineValue,
    unit: rec.unit,
    tolerance: rec.tolerance,
  });

  // 결함 zoom(userFrameIdx 보유) 조인 매처 — selectedZoom 과 동일 단일 출처
  // (deductionLabels.matchZoomForDeductionRecord — 33-12 A-5 criterion 키 일치
  // 1차 + legacy 교집합 폴백, advisory 제외). cueWindows·recordMaps 공용.
  const matchZoomForRecord = (rec: DeductionRecord): FaultZoomComparison | null =>
    matchZoomForDeductionRecord(
      rec,
      vetoFaultJoints,
      result.faultZoomComparisons ?? [],
    );

  // 33-13 (A-6, D-13 대표 UX) — 음성 큐 recordId → 강조 부위 투영. cue 는
  // records 에서 태어나므로(cueWindows 조립) 항상 짝이 있다 — 못 찾으면 빈 배열
  // = 강조 0 (D-18 고아 가드). 투영 규칙 = projectDeductionRecordKeypoints 단일
  // 출처 (마커·크롭과 동일 부위 — 규칙 사본 0). IN-01 역립 저신뢰 시 부위 단정
  // 강조 억제(빈 배열).
  const focusKeypointsForRecordId = (recordId: string): KeypointName[] => {
    if (attributionUnreliable) return [];
    const rec = records.find((r) => r.recordId === recordId);
    if (!rec) return [];
    return projectDeductionRecordKeypoints(rec, vetoFaultJoints);
  };

  // 강사 질문 — 자동 수집(result.coachQuestions, D-28) + legacy 폴백
  // (openQuestionsForCoach, coachQuestions 부재 doc만) + 사용자 담기(source 'user').
  const [userQuestions, setUserQuestions] = useState<CoachQuestion[]>([]);
  const autoQuestions = useMemo<CoachQuestion[]>(() => {
    const out: CoachQuestion[] = [];
    const seen = new Set<string>();
    for (const q of result.coachQuestions ?? []) {
      const t = q.text?.trim();
      if (!t || seen.has(t)) continue;
      seen.add(t);
      out.push({ text: t, source: q.source, recordId: q.recordId });
    }
    if ((result.coachQuestions?.length ?? 0) === 0) {
      for (const t of openQuestionsForCoach) {
        const trimmed = t.trim();
        if (!trimmed || seen.has(trimmed)) continue;
        seen.add(trimmed);
        out.push({ text: trimmed, source: 'unmeasured' });
      }
    }
    return out;
  }, [result.coachQuestions, openQuestionsForCoach]);
  const combinedCoachQuestions = useMemo<CoachQuestion[]>(() => {
    const seen = new Set(autoQuestions.map((q) => q.text));
    const extra = userQuestions.filter((q) => !seen.has(q.text));
    return [...autoQuestions, ...extra];
  }, [autoQuestions, userQuestions]);
  // '강사님께 물어보기' 담기 — recordId 로 완성문(record.coachQuestion) 또는 라벨 기반.
  const addUserQuestion = (recordId: string | null) => {
    const rec =
      recordId != null ? records.find((r) => r.recordId === recordId) : undefined;
    const text =
      rec?.coachQuestion ??
      (rec
        ? `${criterionLabelKo(rec.criterion)} 어떻게 교정하면 좋을지 강사님께 여쭤보고 싶어요`
        : '이 부분 어떻게 교정하면 좋을지 강사님께 여쭤보고 싶어요');
    setUserQuestions((prev) =>
      prev.some((q) => q.text === text)
        ? prev
        : [...prev, { text, source: 'user', recordId: recordId ?? undefined }],
    );
  };

  // recordId 조인 맵 — record→{questions, zoomPair, index, key}. 카드 점프·질문
  // 연결이 전부 이 맵의 안정 키를 쓴다(배열 index 조인 금지 — 리뷰 반영).
  const recordMaps = useMemo(
    () =>
      buildRecordMaps<DeductionRecord, FaultZoomComparison, CoachQuestion>(
        records,
        result.faultZoomComparisons ?? [],
        combinedCoachQuestions,
        (rec) => matchZoomForRecord(rec),
      ),
    // matchZoomForRecord 는 result.faultZoomComparisons/vetoFaultJoints 파생.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [records, result.faultZoomComparisons, combinedCoachQuestions, vetoFaultJoints],
  );

  // 재생 중 자막 큐 (D-18 자막 + D-17 밀도) — record 의 cueLine(부재 legacy=행동구
  // 폴백) + 매칭 zoom 의 userFrameIdx(학생 9fps) + 학생 fps 로 윈도우 산출.
  // 32-13: 스팟체크 숨김 record 는 큐에서도 제외 — 불일치 판정된 문장을 자막·
  // 오디오로 재생하는 것도 '틀린 말 내보내기' (D-23 동일 원칙, 표면 숨김의 일부).
  const cueWindows = useMemo(() => {
    const inputs: CueInput[] = [];
    for (const rec of records) {
      if (isRecordHidden(rec)) continue;
      const zoom = matchZoomForRecord(rec);
      const userFrameIdx = zoom?.userFrameIdx;
      if (typeof userFrameIdx !== 'number') continue;
      const text =
        rec.cueLine ??
        actionPhraseForRecord(rec, vetoFaultJoints, actionLabels) ??
        '';
      if (!text) continue;
      inputs.push({
        userFrameIdx,
        text,
        points: rec.points,
        recordId: rec.recordId,
      });
    }
    return buildCueWindows(
      inputs,
      result.keypointReport?.fps || 9,
      CUE_WINDOW_SEC,
      records.length,
    );
    // matchZoomForRecord/actionPhraseForRecord 는 아래 deps 파생.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    records,
    result.faultZoomComparisons,
    result.keypointReport?.fps,
    actionLabels,
    vetoFaultJoints,
    hiddenRecordIds,
  ]);

  // 32-12 (D-18 B안 재생 중 큐 오디오) — coachAudio mp3 가 준비된(status 'done' +
  // items 존재) 경우에만 VideoCompare 에 analysisId 를 넘겨 오디오 토글·재생을 켠다.
  // 'failed'(합성 실패 — 자막만)/부재(legacy doc)면 undefined → 오디오 표면 미렌더.
  // 재생 URL 재서명·prefetch·cueId 조인은 audioCue.ts 소유(화면은 게이트만 판정).
  const coachAudioAnalysisId =
    result.coachAudio?.status === 'done' &&
    (result.coachAudio.items?.length ?? 0) > 0
      ? analysisId
      : undefined;

  // 32-12 (D-29 부분 실패 정직 고지) — 측정 커버리지 갭 존재 신호. 32-09 가 방출하는
  // deductionBreakdown.coverageGaps(가려짐·화면 밖 등으로 못 잰 결함 유형). 존재 시
  // 요약 카드 아래에 "잰 범위만 확실히 분석했다"는 정직 고지 + 재촬영 팁을 렌더한다.
  // 못 잰 것은 coachQuestions(source 'unmeasured')로 자동 등재돼 표시되므로(32-09),
  // 여기서는 커버리지 자체의 정직 고지만 담당한다(미션 구성은 방출이 이미 담당).
  const hasCoverageGap =
    (result.deductionBreakdown?.coverageGaps?.length ?? 0) > 0;

  // 요약 카드 3요소 (deriveSummaryContent — 32-07). mode3 헤드라인=발전 델타 invariant
  // 는 summaryPraise(백엔드 사람 말)가 담당(D-26). 수치는 카드가 소형 배지 1곳만.
  const summaryContent = useMemo(() => {
    const gaps = (result.deductionBreakdown?.coverageGaps ?? []).map(
      (g) => g.faultType,
    );
    const dimSignals = DIMENSION_ORDER.filter(
      (d) => dimensionScores[d] != null,
    ).map((d) => ({
      key: d as string,
      score: dimensionScores[d] as number,
      // 감점 record 가 있으면 clean 칭찬 폴백 차단(모순 칭찬 0 — D-06). 백엔드
      // summaryPraise 가 있으면 이 폴백은 미사용(단일 원천 우선).
      hasDeduction: hasRecords,
      metCriteria: (dimensionScores[d] as number) >= 90,
    }));
    const input: SummaryInput = {
      mode: cmp.mode === 'mode1' ? 'mode1' : 'mode3',
      summaryPraise: result.summaryPraise ?? null,
      // 32-13 (D-22 잘한 점 교차검증) — 스팟체크가 headline 불일치를 판정하면
      // doc praise 를 강등하고 로컬 폴백 체인의 다음 소스로 (32-07 selectPraise).
      spotCheckPraiseMismatch: result.spotCheck?.praiseMismatch === true,
      missionOutcome: result.missionOutcome
        ? {
            improved: result.missionOutcome.improved,
            deltaPoints: result.missionOutcome.deltaPoints,
            criterion: result.missionOutcome.criterion,
          }
        : null,
      mission: result.mission
        ? {
            criterion: result.mission.criterion,
            recordId: result.mission.recordId,
            isSafety: result.mission.isSafety,
          }
        : null,
      dimensionScores: dimSignals,
      coverageGaps: gaps,
      // 32-13 — 숨김 record 는 요약 파생(오늘 고칠 것 헤드라인·다음 행동 문구)
      // 에서도 제외 (불일치 문장을 요약 카드로 되살리지 않음 — 카드 표면의 일부).
      deductionRecords: records
        .filter((r) => !isRecordHidden(r))
        .map((r) => ({
          criterion: r.criterion,
          points: r.points,
          recordId: r.recordId,
          statusLine: r.statusLine,
          cueLine: r.cueLine,
          exerciseReason: r.exerciseReason,
          coachQuestion: r.coachQuestion,
        })),
      safetyFlagCount: result.safetyFlags?.length ?? 0,
    };
    return deriveSummaryContent(input);
    // isRecordHidden 은 hiddenRecordIds 파생.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    result.summaryPraise,
    result.spotCheck,
    result.missionOutcome,
    result.mission,
    result.deductionBreakdown,
    result.safetyFlags,
    records,
    dimensionScores,
    hasRecords,
    cmp.mode,
    hiddenRecordIds,
  ]);

  // 섹션 순서·가시성 — resultSections 뷰모델 단일 결정 지점(node --test 고정).
  const sections = useMemo(
    () =>
      deriveResultSections({
        mode: cmp.mode === 'mode1' ? 'mode1' : 'mode3',
        isCleanPass: cleanPass,
        isScoreSuppressed,
        safetyFlagCount: result.safetyFlags?.length ?? 0,
        hasRecords,
        hasMission: result.mission != null,
        escalation: result.mission?.escalation ?? null,
        hasMissionOutcome: result.missionOutcome != null,
        hasPhrases: records.some(
          (r) => r.statusLine != null || r.cueLine != null,
        ),
        isMode3First: cmp.mode === 'mode3' && cmp.isFirst,
        hasQuestions: combinedCoachQuestions.length > 0,
        hasExercise:
          (result.recommendedExercises?.length ?? 0) > 0 ||
          CORRECTIVE_LIBRARY_HAS_ITEMS,
      }),
    [
      cmp,
      cleanPass,
      isScoreSuppressed,
      result.safetyFlags,
      hasRecords,
      result.mission,
      result.missionOutcome,
      result.recommendedExercises,
      records,
      combinedCoachQuestions,
    ],
  );
  const sectionMap = useMemo(() => {
    const m = new Map<ResultSectionKey, ResultSection>();
    for (const s of sections) m.set(s.key, s);
    return m;
  }, [sections]);
  const isVisible = (k: ResultSectionKey) => sectionMap.get(k)?.visible === true;
  const variantOf = (k: ResultSectionKey) => sectionMap.get(k)?.variant;

  // 첫 진입 코치마크 1회 (32-07 D-07) — hasSeenResultCoachmark 체크 후 표시/기록.
  const [coachmarkVisible, setCoachmarkVisible] = useState(false);
  useEffect(() => {
    let alive = true;
    hasSeenResultCoachmark().then((seen) => {
      if (alive && !seen) setCoachmarkVisible(true);
    });
    return () => {
      alive = false;
    };
  }, []);
  const dismissCoachmarks = () => {
    setCoachmarkVisible(false);
    markResultCoachmarkSeen();
  };

  // 카드 점프 — ScrollView ref + record 카드 y 기록(onLayout). 요약 '오늘 고칠 것'
  // 탭·질문 탭이 recordId 안정 키로 해당 카드 위치로 스크롤한다.
  const scrollRef = useRef<ScrollView>(null);
  const cardYRef = useRef<Map<string, number>>(new Map());
  const setCardY = (key: string, y: number) => {
    cardYRef.current.set(key, y);
  };
  const jumpToRecordKey = (key: string | null) => {
    if (!key) return;
    const y = cardYRef.current.get(key);
    if (typeof y === 'number') {
      scrollRef.current?.scrollTo({ y: Math.max(0, y - 12), animated: true });
    }
  };
  // 질문의 recordId → 안정 키 (records 에서 index 역산 폴백 포함).
  const jumpToQuestion = (recordId: string | undefined) => {
    if (!recordId) return;
    const idx = records.findIndex((r) => r.recordId === recordId);
    jumpToRecordKey(
      idx >= 0 ? recordKeyForIndex(records, idx) : recordId,
    );
  };

  // 33-15 (D-17) — 요약 카드 '자세히 보기' 토글. 종전엔 topFix 카드로만 점프해
  // (요약 바로 아래라 거의 안 움직임 + 재탭 무반응) belle 가 "재탭 안 접힘 /
  // 스크롤 오정지"로 지적. 펼침 = 점수 상세 영역(게이지 카드 → 내역 순 앵커,
  // onLayout 실측 y)으로 스크롤 + 라벨 '접기', 재탭 = 최상단 복귀 (접힘 상태 복원).
  // 앵커 키는 전용 setCardY 슬롯 — record 키와 충돌 없음.
  const DETAIL_ANCHOR_KEYS = ['anchor:scoreGauge', 'anchor:scoreBreakdown'];
  const [detailExpanded, setDetailExpanded] = useState(false);
  const toggleDetailExpanded = () => {
    if (detailExpanded) {
      setDetailExpanded(false);
      scrollRef.current?.scrollTo({ y: 0, animated: true });
      return;
    }
    setDetailExpanded(true);
    for (const key of DETAIL_ANCHOR_KEYS) {
      const y = cardYRef.current.get(key);
      if (typeof y === 'number') {
        scrollRef.current?.scrollTo({ y: Math.max(0, y - 12), animated: true });
        return;
      }
    }
    // 앵커 미기록(억제 + 내역 부재 등) — 상세가 아래쪽에 있으므로 끝으로 폴백.
    scrollRef.current?.scrollToEnd({ animated: true });
  };

  // 33-15 (D-17) — '오늘 고칠 것' 외 추가 감점 항목 스크롤 어포던스. 추가 항목은
  // 동작 비교(긴 영상 카드) 아래 '다른 감점 항목' 목록이라 발견이 어렵다 — top-1
  // 카드 아래에 개수 + 이동 링크를 제공한다 (표시 조건 = 목록 섹션과 동일 미러).
  const otherVisibleRecordCount = records.filter(
    (r, i) => i !== topFixIndex && !isRecordHidden(r),
  ).length;
  const jumpToCollapsedList = () => {
    const y = cardYRef.current.get('anchor:collapsedList');
    if (typeof y === 'number') {
      scrollRef.current?.scrollTo({ y: Math.max(0, y - 12), animated: true });
    }
  };

  // 보완 운동 (D-13) — 전면 1개(개인화 추천 top) + 이유 1줄(top-1 record.exerciseReason
  // 우선, 부재 시 운동 purpose) + 나머지 가로 최대 3.
  const recommendedExercises = result.recommendedExercises ?? [];
  const frontExercise = recommendedExercises[0] ?? null;
  const frontExerciseReason =
    topFixRecord?.exerciseReason ?? frontExercise?.purpose ?? null;
  const altExercises = recommendedExercises.slice(1, 1 + EXERCISE_MAX_ALT);
  const exerciseDetour = result.mission?.escalation === 'exercise_detour';

  // 심사 시뮬레이션 (D-03) — 내 실제 감점 record 를 IPSF 규칙 감점으로 환산.
  const judgeFinal = result.deductionBreakdown?.final ?? result.overallScore;

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <ScrollView
        ref={scrollRef}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Text style={styles.title}>분석 결과</Text>
          <Text style={styles.sub}>
            {cmp.mode === 'mode1'
              ? `${cmp.athleteName} 선수 · ${cmp.referenceMotionName} 기준으로 분석했어요.`
              : isScoreSuppressed
                ? `${name ? `${name} · ` : ''}${suppressedHeaderCopy}`
                : `${name ? `${name} · ` : ''}분석이 완료됐어요. 점수를 확인해보세요.`}
          </Text>
          {/* Phase 19 TRUST-03 — 채점 근거(scoringBasisLabel) 가시화. reference-free 일 때
              "기준 동작 없음 — 절대 자세 기준 평가" 가 사용자에게 보인다 (거짓 confident 점수
              차단). 백엔드가 채울 때만 1줄 표시 (graceful). 토큰만 (하드코딩 금지). */}
          {cmp.scoringBasisLabel ? (
            <Text style={styles.scoringBasis}>{cmp.scoringBasisLabel}</Text>
          ) : null}
          {/* Phase 4 (04-02 D-08 / BLOCKER-3) — 정확도 제한 배지.
              canonical surface = result.aiSynthesisMeta.warnings (top-level
              result.warnings 아님). 합성 경고 없는 정상 분석에서는 visible=false
              로 자동 미렌더 (블랙박스 R7 박제 — 사용자에게 내부 코드명 노출 X). */}
          <AccuracyLimitBadge
            visible={hasSynthesisWarning(result, 'ai_synthesis_failed')}
          />
          {/* [R1] 분석-당시 자가입력 SNAPSHOT 표기 — 채워진 필드만, 미입력이면
              생략(graceful). weightKg 보조 ONLY 라 요약에서 제외 (D-05). */}
          {bodyProfileSummary ? (
            <View style={styles.bodyProfileRow}>
              <Ionicons
                name="body-outline"
                size={14}
                color={colors.textSecondary}
              />
              <Text style={styles.bodyProfileText}>{bodyProfileSummary}</Text>
            </View>
          ) : null}
          {/* Phase 11 (Plan 11-02, FEED-03 / D-07) — AI = "강사 보조 도구"
              포지셔닝 상단 1줄. 가볍게 한 줄만 (전용 강조 배너 채택 안 함 —
              매 분석 반복 노출 거슬림, D-07). "강사에게 확인할 점" 섹션과 함께
              AI 가 강사를 대체하지 않고 지도를 돕는 참고임을 명확히 한다. */}
          <Text style={styles.coachPositioning}>
            이 분석은 강사 지도를 돕는 참고예요.
          </Text>
        </View>

        {/* mode1 전용: 기준 모션 메타 카드 (선수·동작·레벨·설명) */}
        {cmp.mode === 'mode1' && (
          <View style={[styles.card, styles.refCard]}>
            <View style={styles.refHead}>
              <Text style={styles.refAthlete}>{cmp.athleteName}</Text>
              {refMotion && (
                <Text style={styles.refLevel}>{REFERENCE_LEVEL_LABEL[refMotion.level]}</Text>
              )}
            </View>
            <Text style={styles.refName}>{cmp.referenceMotionName}</Text>
            {refMotion?.description && (
              <Text style={styles.refDesc}>{refMotion.description}</Text>
            )}
            {/* Phase 11 (Plan 11-02, ROADMAP SC#4) — 기준 모션은 절대 정답이
                아니라 하나의 참고. 정은지 비교 점수를 "전문가 기준 절대값"으로
                오인하지 않도록 라벨 근처에 명시 (강사 보조 도구 포지셔닝 정합). */}
            <Text style={styles.refNote}>
              기준 모션은 하나의 참고일 뿐이에요.
            </Text>
          </View>
        )}

        {/* ═══ 32-11 대배선 — D-02 확정 순서 (resultSections 뷰모델 단일 지점) ═══
            요약 → 위험 → 오늘 고칠 것 top-1 → 동작 비교 → 상세(접힘) → 성장 →
            보완 운동 → 강사 질문 → 심사 정보 → 참고하세요(31). 근거 = 32-GATE-
            DECISIONS D-02. 순서·가시성은 sections(resultSections)가 단일 지점에서
            결정하고, 카드 상호작용은 recordId 조인 맵(recordMaps)으로만 잇는다. */}

        {/* ── 1. 요약 카드 (D-01 첫 콘텐츠) ─────────────────────────────────
            suppressed → '기준 없음', 아니면 SummaryCard(잘한 점 사람 말 헤드라인 +
            오늘 고칠 것 + 다음 행동 + 점수 소형 배지 1곳). mode3 헤드라인=발전 델타
            invariant 는 summaryPraise(백엔드 사람 말)가 담당(D-26). 큰 점수 게이지는
            D-09 로 아래 상세 영역으로 강등(헤드라인 수치 금지). */}
        {variantOf('summary') === 'suppressed' ? (
          <View style={styles.card}>
            <Text style={styles.suppressedTitle}>기준 없음</Text>
            <Text style={styles.suppressedBody}>{suppressedHeaderCopy}</Text>
          </View>
        ) : (
          <SummaryCard
            praise={summaryContent.praise}
            // IN-01 (quick-260724-q6b) — 역립 저신뢰 시 "오늘 고칠 것" 헤드라인을
            // 관절명 없는 집계 문장으로 라우팅 (TODAY_NONE '고칠 것 없음' 폴백 금지 —
            // clean 오인 방지). "다음 행동" 은 record cueLine(관절-행동)이라 숨김.
            // praise/score 배지는 유지(확신 표면 — 리드). 신규 카피 0.
            todayFix={
              attributionUnreliable
                ? {
                    headline:
                      result.attributionReliability?.aggregateStatement ??
                      ATTR_SCORE_AGGREGATE_FALLBACK,
                    criterion: '',
                    gameFrame: false,
                  }
                : summaryContent.todayFix
            }
            nextAction={
              attributionUnreliable ? null : summaryContent.nextAction
            }
            score={result.overallScore}
            onPressTodayFix={() => jumpToRecordKey(topFixKey)}
            // 33-15 (D-17) — 자세히 보기 = 점수 상세 앵커 토글 (재탭 = 접기/복귀).
            onPressExpand={toggleDetailExpanded}
            expanded={detailExpanded}
          />
        )}

        {/* 32-12 (D-29 부분 실패 정직 고지) — 커버리지 갭이 있을 때만. 못 잰 부분을
            정직하게 알리고(과장·감춤 금지) 다음 행동(촬영 가이드)을 1줄로 잇는다.
            잰 범위 내 미션·질문은 32-09 방출이 담당 — 이 블록은 정직 고지 전담. */}
        {hasCoverageGap ? (
          <View style={styles.coverageCard}>
            <Text style={styles.coverageTitle}>
              이번엔 화면에 잘 잡힌 부분 위주로 분석했어요
            </Text>
            <Text style={styles.coverageBody}>
              가려지거나 화면 밖으로 나간 부분은 이번 영상에서 정확히 재기 어려웠어요.
              보이는 자세를 기준으로 확실히 잰 것만 짚었어요.
            </Text>
            <Pressable
              onPress={() => router.push('/tutorial')}
              accessibilityRole="button"
              accessibilityLabel="촬영 가이드 보기"
              hitSlop={8}
              style={styles.coverageTipRow}
            >
              <Text style={styles.coverageTip}>
                몸 전체가 화면에 들어오게 다시 촬영하면 더 많은 부분을 분석할 수 있어요.
                촬영 가이드 보기 ›
              </Text>
            </Pressable>
          </View>
        ) : null}

        {/* ── 2. 위험 결함 (D-14 트리아지) — 요약 직후 승격, 있을 때만. 컴포넌트
            self-null (플래그 0 → 미렌더). ── */}
        {isVisible('risk') ? <InjuryRiskSection flags={result.safetyFlags} /> : null}

        {/* ── 3. 오늘 고칠 것 top-1 (D-08 완결형 DeductionCard) ────────────────
            미션 record 우선/최대 감점 1건을 상태→왜→게이지→행동→미션→물어보기로
            완결 렌더. cleanPass 면 축하 카드가 대신(요약 clean variant). 확대 사진
            쌍은 드릴다운 시트(D-17 자세 비교 카드) 진입점으로 잇는다. onLayout 으로
            점프 y 기록(요약 '오늘 고칠 것' 탭 대상). */}
        {/* IN-01 — 역립 저신뢰 시 topFix "오늘 고칠 것" per-joint 카드 억제 (관절
            단정 방지). records 보유(cleanPass=false) 라 clean 카드 폴백도 미충족 →
            null. 점수·안내는 ScoreBreakdownSection aggregate + 안내 1줄이 대신 전달. */}
        {isVisible('topFix') && topFixRecord && !attributionUnreliable ? (
          <View
            onLayout={(e) =>
              setCardY(topFixKey ?? 'topFix', e.nativeEvent.layout.y)
            }
          >
            <DeductionCard
              record={toCardRecord(topFixRecord)}
              zoomPending={zoomPending}
              mission={
                result.mission
                  ? { isMission: true, isSafety: result.mission.isSafety }
                  : undefined
              }
              rightLabel={
                cmp.mode === 'mode1' ? `${cmp.athleteName} 선수` : '지난 영상'
              }
              expanded
              onAskCoach={(rid) => addUserQuestion(rid)}
            />
            {matchZoomForRecord(topFixRecord) || zoomPending ? (
              <Pressable
                onPress={() => setDetailRecordIndex(topFixIndex)}
                accessibilityRole="button"
                accessibilityLabel="확대 비교 자세히 보기"
                hitSlop={8}
                style={styles.tipMoreRow}
              >
                {/* IN-01 — 역립 저신뢰 시 "예상 부위" 라벨로 치환 (확정 결함 아님). */}
                <Text style={styles.tipMore}>
                  {attributionUnreliable
                    ? `${ATTR_ZOOM_ESTIMATED_LABEL} 확대 비교 ›`
                    : '확대 비교 자세히 보기 ›'}
                </Text>
              </Pressable>
            ) : null}
            {/* 33-15 (D-17) — 추가 감점 항목 스크롤 어포던스. 추가 항목이 동작
                비교(긴 카드) 아래 있어 발견이 어렵다 — 개수 + 이동 링크 1줄.
                표시 조건 = '다른 감점 항목' 섹션 렌더 조건 미러 (모순 링크 0). */}
            {isVisible('collapsed') && otherVisibleRecordCount > 0 ? (
              <Pressable
                onPress={jumpToCollapsedList}
                accessibilityRole="button"
                accessibilityLabel={`다른 감점 항목 ${otherVisibleRecordCount}개로 이동`}
                hitSlop={8}
                style={styles.tipMoreRow}
              >
                <Text style={styles.tipMore}>
                  {`아래에 다른 감점 항목 ${otherVisibleRecordCount}개 더 보기 ›`}
                </Text>
              </Pressable>
            ) : null}
          </View>
        ) : variantOf('summary') === 'clean' ? (
          <View style={[styles.card, styles.cleanPassCard]}>
            <Text style={styles.cleanPassTitle}>감점 항목이 없어요</Text>
            <Text style={styles.cleanPassBody}>
              {cmp.mode === 'mode3'
                ? '측정한 자세 형태 기준을 모두 통과했어요. 이 자세를 유지하고 다음 영상과 비교해 발전을 확인해보세요.'
                : '측정 기준을 모두 통과했어요. 이 자세를 그대로 유지하세요.'}
            </Text>
          </View>
        ) : null}

        {/* ── 영역 2: 영상 + 키포인트 오버레이 (D-12-A1 #2 / D-12-C1 mode 분기) ─
            mode1 = 사용자 + 정은지 split (둘 다 오버레이 박제).
            mode3 second+ = 사용자 + 지난 분석 split (오버레이는 사용자 측만).
            mode3 first = 비교 대상 없음 → 섹션 자체 미렌더.
            KeypointOverlay 가 keypointReport null 시 자동 return null
            (caller placeholder X — VideoCompare slot empty UI 가 fallback).
            Wave 2 (Plan 12-03 T1/T2): player 전달 → useEvent(player,'timeUpdate')
            로 frame index 자동 산출 + delta ≥ 10° 강조 + 토글 visible 제어. */}
        {!(cmp.mode === 'mode3' && cmp.isFirst) && (
          <>
            <View style={styles.compareHeader}>
              <Text style={styles.sectionTitle}>동작 비교</Text>
              <KeypointOverlayToggle
                value={overlayVisible}
                onValueChange={handleToggleOverlay}
              />
            </View>
            <VideoCompare
              // 29-CONTEXT D-06 — mode3 비교 = 본인 이전 영상 vs 이번 영상.
              // 좌/우 라벨을 지난/이번 쌍으로 명확히 (정은지 언급 없음). mode1 은
              // 좌 '내 영상' 유지.
              leftLabel={cmp.mode === 'mode3' ? '이번 영상' : '내 영상'}
              // 28-CONTEXT D-01 — 정은지(right) 재생을 학생(left) 마스터 시계에 동작
              // 기준으로 워핑(28-06 소비). videoAlignment=null(legacy/malformed)이면
              // VideoCompare 가 현행 절대시계로 100% 폴백 — 신규 doc 만 정렬이 흐른다.
              // 29-CONTEXT D-10 — mode3 워핑은 28-04 방출(mode1+mode3) + 이 mode
              // 무관 전달로 기흐름 (신규 워핑 구현 0). 신뢰도 사다리·배속 클램프는
              // 28 D-02 를 mode 무관하게 동일 적용 — 여기 mode 조건 추가 금지.
              alignment={videoAlignment}
              // 32-02 (D-16) — legacy doc 자동 시작 오프셋 + 분석 전환 리셋 키.
              // VideoCompare 가 dirty 가드로 사용자 조정 후엔 덮어쓰지 않는다.
              initialOffsetSec={legacyStartOffsetSec}
              resetKey={analysisId}
              rightLabel={
                cmp.mode === 'mode1' ? `${cmp.athleteName} 선수` : '지난 영상'
              }
              // 29 리뷰 WR-03 — 재발급 URL 최우선 (myVideoUrl 은 분석 시점 서명
              // 7일 TTL — 6일 초과 열람 시 freshMyUrl 재발급, 실패 시 기존 폴백).
              leftUrl={freshMyUrl || result.myVideoUrl || undefined}
              rightUrl={
                cmp.mode === 'mode1'
                  ? // 29-CONTEXT D-09 — 재발급 URL 최우선 (referenceVideoUrl 은
                    // 분석 시점 서명 7일 TTL, refMotion.videoUrl 은 시드 시점
                    // 서명이라 사실상 항상 만료 — 최후 폴백만).
                    freshRefUrl ||
                    result.referenceVideoUrl ||
                    refMotion?.videoUrl ||
                    undefined
                  : freshPrevUrl || prevDoc?.result?.myVideoUrl || undefined
              }
              leftOverlay={(player, opts) => (
                <KeypointOverlay
                  player={player}
                  keypointReport={userKeypointReport}
                  videoSize={overlayVideoSize}
                  // 33-13 (A-6, D-13) — 이 레이어 자체는 상시(visible): 음성 큐
                  // dim/강조가 여기 얹힌다. 추적 스켈레톤은 토글(기본 숨김).
                  visible={true}
                  skeletonVisible={overlayVisible}
                  // 33-G F-8 (quick-260730-szk, D-42) — 감점 마커 계층은 상시가
                  // 아니다: 스켈레톤 토글 ON 또는 음성 큐 강조 중에만. 상시 진입점
                  // 은 아래 부위 칩이 대체한다. `focusKeypoints`(강조)·dim 은 이
                  // 게이트와 무관 — D-42 가 음성 큐 강조는 유지하라고 명시했다.
                  markersVisible={
                    overlayVisible || opts?.voiceCueRecordId != null
                  }
                  // 33-13 — record 보유 doc 은 각도편차(>20°) 폴백 강조 차단
                  // (record 와 짝 없는 고아 빨강 마커 금지, D-18). jointAngles 는
                  // 폴백 강조 산출 전용이라 미전달로 충분. legacy 는 기존 유지.
                  jointAngles={hasBreakdownRecords ? undefined : userJointAngles}
                  // #3 (2026-06-21) — 결함 keypoint 권위 강조. quick-260704-fz4:
                  // 소스를 vetoFaultJoints 단독 → confirmedKeypoints(감점 근거
                  // records ∪ vetoFaultJoints) 단일 조립으로 확장 — 표·마커·카드
                  // 가 같은 "빨강=확정 감점" 소스를 쓴다. 비면 기존 각도편차
                  // 폴백 (무회귀).
                  // IN-01 (quick-260724-q6b) — 역립 저신뢰 시 확정 빨강 점 제거
                  // (overlayHighlightKeypoints=[]) + 예상 주황 점 최대 1개로 강등.
                  highlightKeypoints={overlayHighlightKeypoints}
                  // quick-260704-fz4 — 측정 초과·확인 권장(주황, 감점 아님) 마커.
                  // 표·확대 카드와 동일 단일 소스(attentionKeypoints memo).
                  // IN-01 — 역립 저신뢰 시 estimatedAreaKeypoints(최대 1개)로 치환.
                  attentionKeypoints={overlayAttentionKeypoints}
                  // quick-260705-r6v — 스플릿(다리 4관절) 그룹 마커: 멤버 centroid
                  // 1점 + 번호. 영상 위 텍스트 pill 은 전면 제거(여백 범례/시트로
                  // 이동). 사용자 측만 전달 (정은지 측 무변경).
                  // IN-01 — 역립 저신뢰 시 빈 배열(번호 단정 제거).
                  groupMarkers={overlayGroupMarkers}
                  // quick-260705-o0s — 감점 record 관절 번호 점 ('점수 계산 내역'
                  // 행 번호와 buildDeductionMarkers 단일 소스 — 항상 일치).
                  // IN-01 — 역립 저신뢰 시 빈 객체(번호 단정 제거).
                  markerNumbers={overlayMarkerNumbers}
                  // quick-260705-r6v — 번호 점 탭 → 드릴다운 시트 (진입점 3).
                  // 전체화면(opts.sizeScale 존재)에선 시트가 중첩 Modal 이 되므로
                  // 콜백 미전달 — 전체화면 점 탭은 여백 범례가 대체(iOS 함정 회피).
                  onMarkerPress={opts?.sizeScale ? undefined : openRecordByNumber}
                  // Phase 20 (UI ②) — faultJoints 가 없을 때(매핑 0/legacy)만 폴백:
                  // 임계(20°) 넘는 관절이 없으면 편차 최대 2개 강제 강조 (마커 0개 모순 제거).
                  // 정타 영상은 0 → 오탐 0.
                  // IN-01 — 역립 저신뢰 시 0 (강제 강조 폴백 억제).
                  forceHighlightWorstCount={overlayForceHighlightWorstCount}
                  // quick-260702-t0v — 가로 전체화면 뷰어가 opts.sizeScale=2.0 전달
                  // (각도 라벨 가독). 세로 카드는 opts 미전달 → 1 (무회귀).
                  sizeScale={opts?.sizeScale ?? 1}
                  // 33-13 (A-6, D-13 대표 UX) — 음성 큐 동안 해당 record 부위
                  // 강조 (VideoCompare 가 발화 recordId 를 opts 로 전달). 짝
                  // 없으면 빈 배열 = 강조 0 (고아 가드).
                  focusKeypoints={
                    opts?.voiceCueRecordId
                      ? focusKeypointsForRecordId(opts.voiceCueRecordId)
                      : undefined
                  }
                />
              )}
              rightOverlay={(player, opts) =>
                cmp.mode === 'mode1' ? (
                  <KeypointOverlay
                    player={player}
                    keypointReport={referenceKeypointReport}
                    videoSize={overlayVideoSize}
                    visible={overlayVisible}
                    // quick-260702-t0v — 전체화면 sizeScale 전달 (정은지 측 동일).
                    sizeScale={opts?.sizeScale ?? 1}
                  />
                ) : null
              }
              // quick-260702-t0v — 전체화면 상단 bar 에 오버레이 토글 유지.
              // state 단일 출처 = 본 화면 (토글 시 render prop 재실행으로 전체화면
              // 오버레이 즉시 반영). mode3 second+ (left 오버레이만) 도 동일.
              fullscreenHeaderExtra={
                <KeypointOverlayToggle
                  value={overlayVisible}
                  onValueChange={handleToggleOverlay}
                />
              }
              // quick-260705-r6v — 전체화면 여백 고정 범례 + 재생바 결함 틱.
              // cleanPass/legacy/mode3 면 자연히 빈 배열 (별도 분기 불요).
              // 29 리뷰 WR-01 — tickFrameCount = doc top-level anglesFrames
              // (9fps angles 공간 T). 틱 frameIndex(sourceFrameIndices)가 9fps
              // 인덱스인데 keypointReport.frames 는 18fps 업샘플이라 종전 배선은
              // 틱/seek 이 실제 시점의 절반 위치였다. 부재(구 doc)면 0 → 틱 생략.
              // IN-01 — 역립 저신뢰 시 빈 배열(번호가 사라져 범례/틱 모순 방지).
              fullscreenLegend={overlayFullscreenLegend}
              timelineTicks={overlayTimelineTicks}
              tickFrameCount={anglesFrames ?? 0}
              // quick-260705-r6v — 여백 범례 탭 → 드릴다운 시트 (진입점 2).
              // VideoCompare 가 closeFullscreen 선행 후 콜백(iOS 중첩 Modal 회피).
              onLegendPress={openRecordByNumber}
              // 33-13 (A-6, D-13) — 재생바 틱 탭 = 시점 seek + 그 감점 항목 열기
              // (진입점 4 — belle: "눌러도 뭔지 모름" 해소. 같은 시트 state 소비).
              onTickPress={openRecordByNumber}
              // 32-11 (D-18 자막 + D-17 밀도) — 재생 중 결함 구간 자막 큐. cueTrack
              // 산출(record cueLine + 매칭 zoom userFrameIdx + 학생 fps). 미전달
              // 시 기존 렌더 diff 0(opt-in). cleanPass/legacy 면 빈 배열.
              cueWindows={cueWindows}
              // 32-12 (D-18 B안) — coachAudio mp3 준비 doc 에서만 오디오 토글·재생
              // 활성(cueId=recordId 조인). failed/legacy 면 undefined → 자막만.
              audioAnalysisId={coachAudioAnalysisId}
            />
            {/* 33-G S3/F-8 (quick-260730-szk) — 부위 칩 행. 승인 목업 ① 은 칩을
                캡처 카드 **바로 아래**에 둔다(`.jointchips` = `.dcap` 다음 형제).
                F-8 로 상시 마커가 사라지므로 이 행이 상시 진입점을 대체한다 —
                감점 칩 탭 → 기존 부위 상세 시트 state(진입점 신설 아님, 5번째 추가).
                감점 0(cleanPass)·저신뢰(IN-01) doc 은 빌더가 빈 배열을 주므로 행
                자체가 렌더되지 않는다 (N-14 / S17 보호). */}
            {partChips.length > 0 ? (
              <PartChipsRow
                chips={partChips}
                onPressPart={setDetailRecordIndex}
              />
            ) : null}
            {/* 28-CONTEXT D-05 — 정렬 데이터는 새 분석부터, legacy 는 재분석 유도.
                조건 = motionAlignment 필드 부재(undefined)만. normalize null(데이터
                있으나 malformed)은 배너 아님 — 필드 자체 부재만 순수 legacy.
                W3: 신규 분석은 degenerate 라도 tier 'disabled'로 필드가 항상 실리므로
                (28-02) undefined 판정 = 순수 legacy — "재분석하면 적용" 과약속 루프 없음.
                tier 판정 금지 — disabled 안내는 VideoCompare 배지(28-06) 책임
                (배지=VideoCompare / 배너=화면 레벨 책임 분리, 28-RESEARCH Pattern 6). */}
            {/* 29-CONTEXT D-04 — 28 배너 통합 (재량). legacy mode3 doc(내역 없음)
                전용 배너를 신설하지 않고 이 Phase 28 배너에 통합한다. "breakdown
                부재 = legacy" 판정은 빈 criteria 4동작의 신선한 doc 에서도 참이 되어
                "재분석하면 내역이 나와요" 가 거짓 약속(Pitfall 1)이 되므로, 특정
                기능 약속 없이 "최신 분석 적용" 으로 일반화한다 (구간 맞춤 + 내역은
                등록 동작 한정으로 함께 따라옴). 판정 규칙(motionAlignment
                === undefined = 순수 legacy)은 아래 원 주석 승계. */}
            {result.motionAlignment === undefined ? (
              <View style={styles.alignUpsellBanner}>
                <Text style={styles.alignUpsellText}>
                  다시 분석하면 자동 구간 맞춤 등 최신 분석이 적용돼요
                </Text>
                <Pressable
                  onPress={() => router.replace('/(tabs)/analyze')}
                  accessibilityRole="button"
                  hitSlop={8}
                >
                  <Text style={styles.alignUpsellCta}>다시 분석하기</Text>
                </Pressable>
              </View>
            ) : null}
          </>
        )}

        {/* 29-CONTEXT D-07 — mode3 첫 분석(이전 영상 없음)은 비교 섹션 전체 숨김
            (위 게이트) + 그 자리에 안내 1줄. 정은지 폴백 금지(mode1 혼동 + 미보유
            동작 reference 부재 — D-07 기각 사유). D-05 고지와 톤 통일("~해요" 체,
            전진형). mode1/mode3 second+ 무회귀. */}
        {cmp.mode === 'mode3' && cmp.isFirst ? (
          <Text style={styles.mode3LimitNotice}>
            다음 분석부터 이전 영상과 비교해 발전을 확인해 드려요.
          </Text>
        ) : null}

        {/* IN-01 (quick-260724-q6b) — 역립 저신뢰 "AI 공부 중" 안내 1줄 (유일 인스턴스).
            동작비교 header 게이트 밖 top-level 이라 mode1/mode3-progress/mode3-first
            세 경로 모두에서 정확히 1회 렌더된다. mode-aware. 이 표현은 화면 전체에서
            이 한 곳에만 존재 — 다른 곳 추가 금지. false/부재 시 미렌더(diff 0). */}
        {attributionUnreliable ? (
          <Text style={styles.mode3LimitNotice}>
            {cmp.mode === 'mode1'
              ? ATTR_GUIDANCE_MODE1
              : cmp.isFirst
                ? ATTR_GUIDANCE_MODE3_FIRST
                : ATTR_GUIDANCE_MODE3_PROGRESS}
          </Text>
        ) : null}

        {/* IN-01 (quick-260724-q6b) — 역립 저신뢰 시 확대비교 진입점. topFix 카드가
            억제돼(위 !attributionUnreliable 게이트) 확대비교가 도달 불가한 gap 을
            메운다 (belle: "예상 부위"로 도달 가능해야 함). 안내줄이 이미 추정 맥락을
            주므로 확정 결함 단정 아님. 매칭 크롭이 없고 pending 도 아니면 미렌더(빈
            시트 열지 않음) — 안내줄 + 정은지 비교는 그대로. false/부재 시 diff 0. */}
        {attributionUnreliable &&
        estimatedAreaRecordIndex != null &&
        (matchZoomForRecord(records[estimatedAreaRecordIndex]) || zoomPending) ? (
          <Pressable
            onPress={() => setDetailRecordIndex(estimatedAreaRecordIndex)}
            accessibilityRole="button"
            accessibilityLabel={ATTR_ZOOM_ESTIMATED_ENTRY_LABEL}
            hitSlop={8}
            style={({ pressed }) => [
              styles.estimatedZoomEntry,
              pressed && styles.estimatedZoomEntryPressed,
            ]}
          >
            <Text style={styles.estimatedZoomEntryText}>
              {ATTR_ZOOM_ESTIMATED_ENTRY_LABEL}
            </Text>
            <Text style={styles.estimatedZoomEntryChevron}>›</Text>
          </Pressable>
        ) : null}

        {/* ══ 5. 나머지 감점(접힘) + 상세 영역 (D-02 #5 collapsed) ══════════════
            점수 게이지는 D-01/D-09 로 헤드라인에서 이 상세 영역으로 강등(요약 카드가
            점수 소형 배지를 담당). 투명 감점 내역(수치 삭제 금지)·구간 점수 유지. */}

        {/* 나머지 감점 카드 — 기본 접힘 목록(탭 → 드릴다운 시트로 펼침). top-1(위
            완결형) 제외. recordId 안정 키로 점프 y 기록 + 드릴다운 조인(index 조인
            금지 — recordMaps). records 2개 미만이면 목록 생략.
            32-13: 스팟체크 숨김 record 는 카드 표면에서 제외 (recordId 맵 기반 —
            아래 ScoreBreakdownSection 투명 내역은 미필터, 채점 tally 불변). */}
        {/* IN-01 — 역립 저신뢰 시 "다른 감점 항목" per-joint 목록 억제. */}
        {isVisible('collapsed') &&
        !attributionUnreliable &&
        records.length > 1 &&
        records.some((r, i) => i !== topFixIndex && !isRecordHidden(r)) ? (
          <>
            <Text
              style={styles.sectionTitle}
              // 33-15 (D-17) — 추가 감점 항목 어포던스 링크의 스크롤 목적지.
              onLayout={(e) =>
                setCardY('anchor:collapsedList', e.nativeEvent.layout.y)
              }
            >
              다른 감점 항목
            </Text>
            {records.map((rec, i) => {
              if (i === topFixIndex) return null;
              if (isRecordHidden(rec)) return null;
              const key = recordKeyForIndex(records, i);
              return (
                <View
                  key={key}
                  onLayout={(e) => setCardY(key, e.nativeEvent.layout.y)}
                >
                  <DeductionCard
                    record={toCardRecord(rec)}
                    rightLabel={
                      cmp.mode === 'mode1'
                        ? `${cmp.athleteName} 선수`
                        : '지난 영상'
                    }
                    expanded={false}
                    onToggle={() => setDetailRecordIndex(i)}
                  />
                </View>
              );
            })}
          </>
        ) : null}

        {/* 점수 게이지 (강등) — suppressed 는 요약 카드가 담당하므로 여기선 octagon
            블록만(비억제). grade/summary/caption/veto 근거 유지. */}
        {isScoreSuppressed ? null : (
          <View
            style={styles.card}
            // 33-15 (D-17) — '자세히 보기' 스크롤 앵커 1순위 (점수 상세 시작).
            onLayout={(e) =>
              setCardY('anchor:scoreGauge', e.nativeEvent.layout.y)
            }
          >
            <OctagonScore score={result.overallScore} size={168} />
            <View style={styles.gradeRow}>
              <Text style={styles.gradeBadge}>{grade}</Text>
              <Text style={styles.summary}>{summary}</Text>
            </View>
            <ScoreContext
              score={result.overallScore}
              mode={cmp.mode === 'mode1' ? 'mode1' : 'mode3'}
              athleteName={cmp.mode === 'mode1' ? cmp.athleteName : null}
              correctionPoint={correctionPoint}
              cleanPass={cleanPass}
              selfDelta={
                cmp.mode === 'mode3' &&
                !cmp.isFirst &&
                prevDoc?.result?.overallScore != null
                  ? result.overallScore - prevDoc.result.overallScore
                  : null
              }
            />
            {/* IN-01 — 역립 저신뢰 시 관절 단정(primaryFault) 표기 숨김. */}
            {vetoPrimaryFault && !attributionUnreliable ? (
              <Text style={styles.scoringBasis}>
                AI 영상 분석에서 발견한 점: {vetoPrimaryFault}
              </Text>
            ) : null}
            <Text style={styles.scoreCaption}>
              촬영 노이즈와 측정 허용 범위가 있어 100점은 잘 나오지 않아요. 90점 이상이면 정상 자세에 가깝습니다.
            </Text>
          </View>
        )}

        {/* 29-CONTEXT D-05 — mode3 한계 고지 (breakdown 부재 경로). breakdown 표시
            중이면 footnote 로 렌더되므로 여기선 !showBreakdownSection 게이트. */}
        {cmp.mode === 'mode3' && !showBreakdownSection ? (
          <Text style={styles.mode3LimitNotice}>{MODE3_LIMIT_NOTICE}</Text>
        ) : null}

        {/* 점수 계산 내역 — 투명 감점 tally(수치 삭제 금지). 렌더 가드/번호/기준문구
            기존 그대로. 내역 행 탭 → 드릴다운 시트(진입점 1).
            점수 원칙: [[scoring-must-be-transparent-deduction-tally]]. */}
        {showBreakdownSection && result.deductionBreakdown != null && (
          <>
            <Text
              style={styles.sectionTitle}
              // 33-15 (D-17) — '자세히 보기' 스크롤 앵커 2순위 (게이지 억제 시).
              onLayout={(e) =>
                setCardY('anchor:scoreBreakdown', e.nativeEvent.layout.y)
              }
            >
              점수 계산 내역
            </Text>
            <ScoreBreakdownSection
              breakdown={result.deductionBreakdown}
              recordNumbers={markers.recordNumbers}
              basisLine={breakdownBasisLine}
              limitNotice={cmp.mode === 'mode3' ? MODE3_LIMIT_NOTICE : undefined}
              onRecordPress={setDetailRecordIndex}
              // IN-01 (quick-260724-q6b) — 역립 저신뢰 시 per-joint 감점 행 대신
              // 관절명 없는 집계 문장 1줄로 강등 (= 종합 final 은 그대로 표기).
              aggregateMode={attributionUnreliable}
              aggregateText={
                result.attributionReliability?.aggregateStatement ??
                ATTR_SCORE_AGGREGATE_FALLBACK
              }
              // 33-15 (D-16) — 코칭 팁에서 이동해 온 관절 각도 참고 행 (이동, 삭제
              // 아님). IN-01 저신뢰 시 displayTips 필터 승계로 자연히 빈 배열.
              angleReference={angleReferenceRows}
            />
          </>
        )}

        {/* 콤보 부분 점수 (mode1 콤보 모션 분석 시에만). */}
        {cmp.mode === 'mode1' && cmp.segmentScores && (
          <>
            <Text style={styles.sectionTitle}>구간별 점수</Text>
            <View style={styles.card}>
              <SegmentRow
                label={`${cmp.segmentScores.baseMotionName} 베이스`}
                score={cmp.segmentScores.base}
              />
              <SegmentRow
                label="콤보 확장 구간"
                score={cmp.segmentScores.extension}
              />
              <Text style={styles.segmentHintText}>
                {segmentHint(cmp.segmentScores)}
              </Text>
            </View>
          </>
        )}

        {/* quick-260705-r6v — 메인 '문제 부위 확대 비교' 섹션 제거 (구 확대 비교
            컴포넌트 파일 삭제). 확대사진은 내역 행/여백 범례/(세로) 번호 점 탭 →
            DeductionDetailSheet 드릴다운으로 이동한다 (재생 중엔 점만, 설명은
            드릴다운으로). 진짜 3D 회전은 Phase 24(자체학습). */}

        {/* ── 영역 6: 각도 가이드 (코칭 팁) — Phase 12.5 + Wave 2 추정 표기 ─
            joint 평균 confidence < 0.5 또는 low reliability frame 비율 ≥ 30%
            → "추정 N°" + estimateGray + ⓘ tap → Alert (D-12-D1 박제). */}
        <Text style={styles.sectionTitle}>코칭 팁</Text>
        {/* Phase 20 (UI ①) — 비전 거부권 적용 시 코칭의 LEAD = 비전 결함(교정 대상).
            backend tip 이 "거의 동일/일치도 100" 으로 시작하면 75 헤드라인과 모순
            (belle 디바이스 finding). 거부권 결함을 맨 앞 카드로 노출해 "무엇을
            교정할지" 를 코칭 흐름의 머리로 둔다. primaryFault 있을 때만 (graceful).
            토큰만 (하드코딩 금지).
            quick-260705-o0s — cleanPass 방어 게이트: 감점 0 이면 veto applied 일 수
            없지만(감점 record 가 tally 실체) '먼저 교정할 점'은 문제-계열 섹션이라
            명시적으로 숨긴다 (isCleanPass 단일 신호). */}
        {/* IN-01 — 역립 저신뢰 시 '먼저 교정할 점' 카드 숨김 (관절 단정 방지). */}
        {!cleanPass && vetoApplied && vetoPrimaryFault && !attributionUnreliable ? (
          <View style={[styles.card, styles.tipCard, styles.vetoLeadCard]}>
            <View style={styles.tipHead}>
              <Ionicons name="alert-circle" size={20} color={colors.brand} />
              <Text style={styles.tipTitle}>먼저 교정할 점</Text>
            </View>
            <Text style={styles.tipDetail}>
              {highlightNumbers(vetoPrimaryFault)}
            </Text>
            {/* quick-260704-fwb — 원인 기전: '~로 보임' 가설 어투 그대로 (측정 안 된
                단정 금지). rootCauseHypotheses 부재 doc 은 섹션 생략 (graceful). */}
            {vetoRootCauses.length > 0 ? (
              <View style={styles.vetoCauseBlock}>
                <Text style={styles.vetoCauseLabel}>가능한 원인</Text>
                {vetoRootCauses.map((h, i) => (
                  <Text key={i} style={styles.vetoCauseItem}>
                    {`· ${h.text}`}
                  </Text>
                ))}
              </View>
            ) : null}
            {/* 처방 연결 — 결함 관절(faultJoints) 매칭 첫 팁의 실행 지시 한 줄.
                매칭 팁 없으면 코칭 팁 안내 폴백 (fabricate 0). */}
            {vetoFixTip ? (
              <Text style={styles.vetoFixLine}>
                <Text style={styles.vetoFixLabel}>이렇게 교정해 보세요: </Text>
                {vetoFixTip.detail}
              </Text>
            ) : (
              <Text style={styles.vetoFixLine}>
                아래 코칭 팁에서 관절별 교정 방법을 확인하세요.
              </Text>
            )}
            <Text style={styles.vetoLeadNote}>
              AI 영상 분석이 발견한 위 자세 차이가 종합 점수에 반영됐어요.
            </Text>
          </View>
        ) : null}
        {displayTips.map((tip, i) => {
          const joint = tip.joint
            ? joints.find((j) => j.key === tip.joint)
            : undefined;
          const guide = joint ? angleGuide(joint) : null;
          const estimated = tip.joint ? isAngleEstimated(tip.joint) : false;
          return (
            <View key={tip.joint ?? i} style={[styles.card, styles.tipCard]}>
              <View style={styles.tipHead}>
                <Text style={styles.tipIndex}>{i + 1}</Text>
                <Text style={styles.tipTitle}>{tip.title}</Text>
              </View>
              {/* 33-15 (D-16) — 각도 수치는 점수 계산 내역 '관절 각도 참고'로 이동.
                  내역 카드 보유 doc 은 행동 언어(cue)만 잔류. legacy(내역 부재)는
                  수치의 유일한 거처라 종전 각도 줄 유지 (이동 불가 시 삭제 금지). */}
              {guide && angleNumbersRelocated ? (
                guide.cue && !estimated ? (
                  <View style={styles.tipAngleRow}>
                    <Text style={styles.tipAngleCue}>{guide.cue}</Text>
                  </View>
                ) : null
              ) : guide ? (
                <View style={styles.tipAngleRow}>
                  {estimated && joint?.currentAngle != null ? (
                    <>
                      <Text style={styles.tipAngleEstimate}>
                        {`추정 ${Math.round(joint.currentAngle)}° → 기준 ${
                          joint.targetAngle != null
                            ? Math.round(joint.targetAngle)
                            : '-'
                        }°`}
                      </Text>
                      <Pressable
                        onPress={showEstimateTooltip}
                        accessibilityRole="button"
                        accessibilityLabel="추정값 안내"
                        hitSlop={8}
                      >
                        <Ionicons
                          name="information-circle"
                          size={14}
                          color={colors.estimateGray}
                        />
                      </Pressable>
                    </>
                  ) : (
                    <Text style={styles.tipAngle}>
                      {highlightNumbers(guide.line)}
                    </Text>
                  )}
                  {guide.cue && !estimated && (
                    <Text style={styles.tipAngleCue}>{guide.cue}</Text>
                  )}
                </View>
              ) : null}
              <Text style={styles.tipDetail}>{highlightNumbers(tip.detail)}</Text>
              {/* Phase 12.5 T9: detail2 (causes/injuryRisk/coachNote) 있을 때만
                  "자세히 ›" 링크 표시. LLM 응답 graceful 처리. */}
              {tip.detail2 && (
                <Pressable
                  onPress={() => setDetailTip(tip)}
                  accessibilityRole="button"
                  accessibilityLabel={`${tip.title} 자세히 보기`}
                  hitSlop={8}
                  style={styles.tipMoreRow}
                >
                  <Text style={styles.tipMore}>자세히 ›</Text>
                </Pressable>
              )}
            </View>
          );
        })}

        {/* ── 6. 성장·지난 미션 (D-26/D-27, mode3) — 미션→연습→확인 루프 상세.
            헤드라인은 요약 카드가 담당하므로 여기는 상세. coach_card(3회 미개선) 시
            코치 카드 전면 승격("혼자 안 되는 건 방법 문제일 수 있어요"). improved
            정직 표시(수치는 소형 배지 — D-09). ── */}
        {isVisible('growth') ? (
          <>
            <Text style={styles.sectionTitle}>성장·지난 미션</Text>
            {variantOf('growth') === 'coachCard' ? (
              <View style={[styles.card, styles.vetoLeadCard]}>
                <View style={styles.tipHead}>
                  <Ionicons
                    name="people-circle-outline"
                    size={20}
                    color={colors.brand}
                  />
                  <Text style={styles.tipTitle}>{COACH_CARD_HEADLINE}</Text>
                </View>
                <Text style={styles.growthBody}>{COACH_CARD_BODY}</Text>
                {combinedCoachQuestions.length > 0 ? (
                  <Pressable
                    onPress={() => jumpToQuestion(combinedCoachQuestions[0].recordId)}
                    accessibilityRole="button"
                    accessibilityLabel="강사에게 물어볼 질문 보기"
                    hitSlop={8}
                    style={styles.tipMoreRow}
                  >
                    <Text style={styles.tipMore}>물어볼 질문 보기 ›</Text>
                  </Pressable>
                ) : null}
              </View>
            ) : result.missionOutcome ? (
              <View style={[styles.card, styles.coachCard]}>
                <Text style={styles.growthHeadline}>
                  {result.missionOutcome.improved
                    ? '지난 미션이 개선됐어요'
                    : '지난 미션이 아직 남아있어요'}
                </Text>
                <Text style={styles.growthBody}>
                  {result.missionOutcome.improved
                    ? '지난번에 짚은 부분이 이번에 나아졌어요. 같은 방향으로 이어가요.'
                    : '같은 부분이 이번에도 남았어요. 아래 보완 운동으로 우회해봐요.'}
                </Text>
                {typeof result.missionOutcome.deltaPoints === 'number' &&
                result.missionOutcome.deltaPoints !== 0 ? (
                  <View style={styles.growthDeltaBadge}>
                    <Text style={styles.growthDeltaText}>
                      {result.missionOutcome.deltaPoints > 0
                        ? `+${result.missionOutcome.deltaPoints}점`
                        : `${result.missionOutcome.deltaPoints}점`}
                    </Text>
                  </View>
                ) : null}
              </View>
            ) : (
              <Text style={styles.mode3LimitNotice}>
                {cmp.mode === 'mode3' && cmp.isFirst
                  ? '다음 분석부터 이전 미션의 개선을 확인해 드려요.'
                  : '이번엔 이어갈 지난 미션이 없어요. 오늘 고칠 것 하나에 집중해봐요.'}
              </Text>
            )}
          </>
        ) : null}

        {/* ── 7. 보완 운동 (D-13 개편) — 전면 top-1 연결 1개 + 이유 1줄, '다른 운동
            보기' 탭 시 가로 스크롤 최대 3(5개 세로 나열 폐지). exercise_detour(2회차
            미개선) 시 우회 제안 카피 상단(D-27 2회차). 이유 1줄 = top-1 record
            exerciseReason 우선, 부재 시 운동 purpose. ── */}
        {isVisible('exercise') ? (
          <>
            <Text style={styles.sectionTitle}>보완 운동</Text>
            {exerciseDetour ? (
              <View style={[styles.card, styles.detourCard]}>
                <Text style={styles.detourHeadline}>
                  {EXERCISE_DETOUR_HEADLINE}
                </Text>
                <Text style={styles.detourBody}>{EXERCISE_DETOUR_BODY}</Text>
              </View>
            ) : null}
            {frontExercise ? (
              <>
                {/* 전면 1개 — top-1 결함 연결 운동 + 이유 1줄(필수). */}
                <View style={[styles.card, styles.exerciseCard]}>
                  <Text style={styles.exerciseName}>{frontExercise.name}</Text>
                  <Text style={styles.exerciseSets}>{frontExercise.setsReps}</Text>
                  {frontExerciseReason ? (
                    <Text style={styles.exercisePurpose}>
                      {frontExerciseReason}
                    </Text>
                  ) : null}
                </View>
                {/* '다른 운동 보기' — 가로 스크롤 최대 3(세로 나열 폐지). */}
                {altExercises.length > 0 ? (
                  <>
                    <Text style={styles.exerciseAltLabel}>다른 운동 보기</Text>
                    <ScrollView
                      horizontal
                      showsHorizontalScrollIndicator={false}
                      contentContainerStyle={styles.exerciseAltRow}
                    >
                      {altExercises.map((ex, i) => (
                        <View
                          key={`${ex.name}-${i}`}
                          style={[styles.card, styles.exerciseAltCard]}
                        >
                          <Text style={styles.exerciseName}>{ex.name}</Text>
                          <Text style={styles.exerciseSets}>{ex.setsReps}</Text>
                          <Text style={styles.exercisePurpose} numberOfLines={3}>
                            {ex.purpose}
                          </Text>
                        </View>
                      ))}
                    </ScrollView>
                  </>
                ) : null}
                <Pressable
                  onPress={() => setExerciseModalOpen(true)}
                  accessibilityRole="button"
                  accessibilityLabel="전체 보완 운동 보기"
                  hitSlop={8}
                  style={styles.tipMoreRow}
                >
                  <Text style={styles.tipMore}>전체 보완 운동 보기 ›</Text>
                </Pressable>
              </>
            ) : (
              <>
                <Text style={styles.exerciseNeutral}>
                  이번 분석에서는 뚜렷한 보완 운동 매핑이 없어요.
                </Text>
                <Pressable
                  onPress={() => setExerciseModalOpen(true)}
                  accessibilityRole="button"
                  accessibilityLabel="전체 보완 운동 보기"
                  hitSlop={8}
                  style={styles.tipMoreRow}
                >
                  <Text style={styles.tipMore}>전체 보완 운동 보기 ›</Text>
                </Pressable>
              </>
            )}
          </>
        ) : null}

        {/* ── 8. 강사 질문 (D-28) — 자동 수집(result.coachQuestions + legacy 폴백) +
            사용자 담기(source 'user') 통합. 질문 탭 → recordId 맵으로 해당 감점 카드
            scrollTo 점프(legacy는 점프 없음). 질문 1개 이상일 때만. ── */}
        {isVisible('questions') ? (
          <>
            <Text style={styles.sectionTitle}>강사에게 확인할 점</Text>
            <Text style={styles.coachSectionSub}>
              아래 질문을 강사와 함께 확인해보세요. 탭하면 해당 감점 카드로 이동해요.
            </Text>
            <View style={[styles.card, styles.coachCard]}>
              {combinedCoachQuestions.map((q, i) => {
                const jumpable = !!q.recordId;
                const inner = (
                  <View style={styles.coachQuestionRow}>
                    <Ionicons
                      name={
                        q.source === 'user'
                          ? 'bookmark'
                          : 'chatbubble-ellipses-outline'
                      }
                      size={16}
                      color={colors.brand}
                    />
                    <Text style={styles.coachQuestionText}>{q.text}</Text>
                    {jumpable ? (
                      <Ionicons
                        name="chevron-forward"
                        size={14}
                        color={colors.textSecondary}
                      />
                    ) : null}
                  </View>
                );
                return jumpable ? (
                  <Pressable
                    key={`${q.text}-${i}`}
                    onPress={() => jumpToQuestion(q.recordId)}
                    accessibilityRole="button"
                    accessibilityLabel={`${q.text} — 해당 감점 카드로 이동`}
                    hitSlop={4}
                  >
                    {inner}
                  </Pressable>
                ) : (
                  <View key={`${q.text}-${i}`}>{inner}</View>
                );
              })}
            </View>
          </>
        ) : null}

        {/* ── 9. 심사 정보 코너 (D-03 = 개인화 심사 시뮬레이션) ─────────────────
            지식전달형(심사 기준만 나열) 폐기. 내 실제 감점 record 를 IPSF 감점
            규칙으로 환산해 "내 수행이 실제 심사였다면" 을 보여준다. 수치는 실존
            규칙 감점(자의적 % 아님) → D-09 % 금지 무충돌. 채점 표면 뒤(참고코너
            앞, 순서 #9). 행 탭 → 드릴다운 시트(근거·사진 쌍). judgeInfo.visible
            (감점 record 있을 때만) — cleanPass/suppressed 면 미렌더. ──
            IN-01 — 역립 저신뢰 시 records.map per-joint 결함 행 섹션 전체 억제
            (특정 관절 단정 방지). */}
        {isVisible('judgeInfo') && !attributionUnreliable ? (
          <>
            <Text style={styles.sectionTitle}>{JUDGE_SIM_TITLE}</Text>
            <View style={styles.card}>
              <Text style={styles.judgeIntro}>{JUDGE_SIM_INTRO}</Text>
              {records.map((rec, i) => {
                const key = recordKeyForIndex(records, i);
                const fault = rec.statusLine ?? criterionLabelKo(rec.criterion);
                return (
                  <Pressable
                    key={key}
                    onPress={() => setDetailRecordIndex(i)}
                    accessibilityRole="button"
                    accessibilityLabel={`${fault} 심사 감점 ${formatDeductionNumber(
                      Math.abs(rec.points),
                    )}점 — 자세히 보기`}
                    hitSlop={4}
                    style={styles.judgeRow}
                  >
                    <View style={styles.judgeRowText}>
                      <Text style={styles.judgeFault} numberOfLines={2}>
                        {fault}
                      </Text>
                      {rec.whyLine ? (
                        <Text style={styles.judgeReason} numberOfLines={2}>
                          {rec.whyLine}
                        </Text>
                      ) : null}
                    </View>
                    <Text style={styles.judgeDeduction}>
                      {`−${formatDeductionNumber(Math.abs(rec.points))}`}
                    </Text>
                  </Pressable>
                );
              })}
              <View style={styles.judgeTotalRow}>
                <Text style={styles.judgeTotalLabel}>심사 환산 점수</Text>
                <Text style={styles.judgeTotalValue}>{`${judgeFinal}점`}</Text>
              </View>
              <Text style={styles.judgeDisclaimer}>{JUDGE_SIM_DISCLAIMER}</Text>
            </View>
          </>
        ) : null}

        {/* ── 10. Phase 31 (D-09): "참고하세요" 참고코너 ────────────────────────
            배치 = 채점 표면(점수·감점·보완 운동·심사 시뮬레이션) 전부 뒤 (31-08
            belle 승인 option-a / 31 D-09 invariant). "점수 비반영"이 레이아웃만 봐도
            드러난다 — 위로 올리면 비채점 생성물이 채점 근거처럼 읽힌다.
            세 카드가 모두 숨김이면 컴포넌트가 스스로 null 을 반환한다. */}
        <ReferenceCornerSection
          correctedPoseState={correctedPoseState}
          correctedPoseImageUrl={correctedPoseUrl ?? undefined}
          correctedPoseJointLabel={correctedPoseJointLabel}
          onCorrectedPoseImageError={onCorrectedPoseImageError}
          rotationState={rotationState}
          rotationVideoUrl={rotationUrl ?? undefined}
          onRequestRotation={onRequestRotation}
          rotationRequestBusy={rotationBusy}
          limitNotice={rotationLimitNotice}
          userPose={viewerUserPose}
          refPose={viewerRefPose}
          jointKeys={viewerJointKeys}
          // 2026-07-21 belle 결정 ("사람이 나와야지") — 스켈레톤 대신 비교 순간의
          // 실제 영상 프레임. URL 은 동작 비교(VideoCompare)와 같은 재발급 우선
          // 사다리(WR-03/D-09).
          //
          // 33-G F-3 (quick-260730-py1, M-11) — **초는 백엔드 방출값만**
          // (`userVideoSec`/`refVideoSec`). rep 인덱스를 rep.fps 로 나눠 초를
          // 추정하는 것 금지: rep(18fps) ↔ video(9fps) 타임베이스 불일치를 그대로
          // 먹어 "자세 비교 페어가 다른 순간"이 됐다(belle 확인 ② 반려 F-3).
          // frameIdx/report 는 오버레이 좌표계라 rep 공간 **그대로 유지**한다.
          //   userSec 부재 → 페어 전체 null (틀린 순간을 보여주지 않는다).
          //   refSec 부재 → reference.url 미지정 → 기존 framesReady=false 경로로
          //   스켈레톤 폴백 (신규 분기 0).
          poseFrames={
            compareFrames && compareFrames.userSec != null
              ? {
                  user: {
                    url: freshMyUrl || result.myVideoUrl || undefined,
                    timeSec: compareFrames.userSec,
                    report: userKeypointReport,
                    frameIdx: compareFrames.userIdx,
                    label: '내 자세',
                  },
                  reference: {
                    url:
                      compareFrames.refSec != null
                        ? freshRefUrl ||
                          result.referenceVideoUrl ||
                          refMotion?.videoUrl ||
                          undefined
                        : undefined,
                    timeSec: compareFrames.refSec ?? 0,
                    report: referenceKeypointReport,
                    frameIdx: compareFrames.refIdx,
                    label:
                      cmp.mode === 'mode1'
                        ? `${cmp.athleteName} 선수`
                        : '목표 자세',
                  },
                  videoSize: overlayVideoSize,
                }
              : null
          }
        />

        {/* ── (구 '참고 지표' = 세부 점수 dims.map 섹션 폐기 — D-03/D-12) ─────────
            belle 게이트 확정: 추상 지표('안정성'/'동작 흐름') 나열은 "지식전달형"이라
            폐기하고, 위 #9 심사 정보 코너(내 결함 → IPSF 감점 환산)로 대체했다. 차원
            수치는 감점 카드 게이지·심사 시뮬레이션 감점으로 흐르므로 표면에서 '안정성'
            류 추상 용어를 제거(D-12 일괄 적용). 종합 점수 산식(감점 tally)은 무변경. */}

        <Pressable
          style={styles.cta}
          onPress={() => router.replace('/(tabs)')}
          accessibilityRole="button"
        >
          <Text style={styles.ctaText}>완료</Text>
        </Pressable>
        <Pressable
          onPress={() => router.replace('/(tabs)/analyze')}
          accessibilityRole="button"
          hitSlop={8}
        >
          <Text style={styles.link}>다시 분석하기</Text>
        </Pressable>
      </ScrollView>
      {/* (구 DimensionDetailModal 제거 — D-03/D-12. 차원 세부 점수 모달 폐기.) */}
      {/* Phase 12.5 T9: 코칭 팁 "자세히 ›" 모달. tip=null 시 닫힘. */}
      <CoachingTipDetailModal
        visible={detailTip != null}
        tip={detailTip}
        onClose={() => setDetailTip(null)}
      />
      {/* Phase 13 (Plan 13-A): "다른 운동 보기" 전체 보완 운동 라이브러리 모달. */}
      <RecommendedExerciseModal
        visible={exerciseModalOpen}
        onClose={() => setExerciseModalOpen(false)}
      />
      {/* quick-260705-r6v — 감점 드릴다운 시트. 내역 행/여백 범례/(세로) 번호 점
          탭 → [내|정은지] 확대사진 + 수치 + 행동구. zoom 미매칭 시 수치·문구만. */}
      <DeductionDetailSheet
        visible={detailRecordIndex != null}
        onClose={() => setDetailRecordIndex(null)}
        view={sheetView}
        primaryZoom={sheetPrimaryZoom}
        blockZooms={sheetBlockZooms}
        zoomPending={zoomPending}
        // D-04 앱측 (28-05 공급) — DTW 대응 실패 시 ref 는 전신 폴백 이미지라
        // "같은 동작 순간을 못 찾았다"고 정직 고지. 부재(legacy)/'dtw'면 false → 캡션 없음.
        refMatchFailed={sheetPrimaryZoom?.refMatch === 'failed'}
        // IN-01 (quick-260724-q6b) — 역립 저신뢰 시 크롭 위 "예상 부위" 배지 (확정
        // 결함 아님). 크롭·수치·비교는 유지 (시트가 라벨 소유).
        estimatedArea={attributionUnreliable}
        // 29-CONTEXT D-06 — mode3 드릴다운 비교 라벨도 지난/이번 계열 (정은지 미언급).
        rightLabel={cmp.mode === 'mode1' ? `${cmp.athleteName} 선수` : '지난 영상'}
        // 33-14 (A-7, D-15) — 결함 → 일러스트 매핑. 키 = mode1 기준 모션 ID
        // (동작명 분기 0 — 데이터 맵). mode3/미검증 동작은 DefectIllustration 이
        // null 렌더 (silent hidden — 틀린 그림은 없는 것보다 나쁘다, D-18).
        // 33-G S13/S25 (quick-260731-2jt) — 부착 판정 입력 = **이 시트의 부위 키**.
        // 1단위 뷰모델이 이미 들고 있는 값이라 신규 상태·신규 계산 0이고, 마커 그룹·
        // 부위 칩과 같은 단위다 (두 번째 그룹핑 규칙 금지, P-1). 장면과 어긋나면
        // 슬롯 자체가 안 생긴다 (승인본 `:1114` — 빈 카드·플레이스홀더 아님).
        illustrationSlot={
          <DefectIllustration
            motionId={cmp.mode === 'mode1' ? cmp.referenceMotionId : null}
            partKey={sheetView?.partKey ?? null}
          />
        }
      />
      {/* 32-07 D-07 (32-11 배선) — 첫 진입 코치마크 1회. "오늘 고칠 건 하나만" +
          "자세히는 펼쳐요". hasSeenResultCoachmark 로 1회만, 탭 시 기록. */}
      <ResultCoachmarks visible={coachmarkVisible} onDismiss={dismissCoachmarks} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg, // 서브 화면 = 흰 배경 (§5-1)
  },
  // 33-15 (D-17) — 상단 inset 은 컨테이너(실측 insets.top)가 담당. 콘텐츠 안쪽
  // 고정 paddingTop(구 layout.safeAreaTop)은 스크롤 시 본문이 상태바와 겹치는
  // 원인이라 제거 (header marginTop 16 이 첫 요소 간격 담당).
  content: {
    paddingHorizontal: spacing.screenX,
    paddingBottom: layout.safeAreaBottom + 24,
    gap: 14,
  },
  header: { marginTop: 16, marginBottom: 2 },
  title: { ...typography.heading, color: colors.textPrimary },
  sub: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 8,
  },
  // Phase 19 TRUST-03 — 채점 근거 1줄. 보조 톤이라 textSecondary, 토큰만.
  scoringBasis: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 6,
  },
  // Phase 11 (Plan 11-02, D-07) — AI = "강사 보조 도구" 포지셔닝 상단 1줄.
  // 토큰만 (하드코딩 금지). 가벼운 보조 톤이라 textSecondary.
  coachPositioning: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 6,
  },
  // [R1] BodyProfile snapshot 요약 row — 토큰만 (하드코딩 금지, R3).
  bodyProfileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 8,
  },
  bodyProfileText: {
    ...typography.caption,
    color: colors.textSecondary,
    flexShrink: 1,
  },
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.card,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    padding: spacing.cardPadding,
    alignItems: 'center',
  },
  gradeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginTop: 14,
  },
  gradeBadge: {
    ...typography.boxLabel,
    color: colors.textWhite,
    backgroundColor: colors.brand,
    width: 30,
    height: 30,
    borderRadius: 15,
    textAlign: 'center',
    textAlignVertical: 'center',
    lineHeight: 30,
    overflow: 'hidden',
  },
  summary: {
    ...typography.boxLabel,
    color: colors.textPrimary,
    flexShrink: 1,
  },
  scoreCaption: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 12,
    lineHeight: 18,
    paddingHorizontal: 4,
  },
  // 29-CONTEXT D-05 — mode3 한계 고지 독립 1줄 (breakdown 부재 경로). caption 톤,
  // 토큰만 (하드코딩 금지). breakdown 경로는 ScoreBreakdownSection footnote 사용.
  // 33-15 (D-17) — 좌우 여백 통일: 최상위 텍스트 블록의 임의 paddingHorizontal 4
  // 제거 — 좌우 가장자리는 content 의 spacing.screenX 단일 기준.
  mode3LimitNotice: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  // IN-01 (quick-260724-q6b) — 역립 저신뢰 확대비교 진입점 카드. advisoryOrange 톤
  // (확정 결함 아님 — "예상" 강조), 신규 색 금지. 토큰만.
  estimatedZoomEntry: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.advisoryOrangeBg,
    borderRadius: radius.card,
    paddingVertical: 12,
    paddingHorizontal: spacing.cardPadding,
    marginTop: 4,
  },
  estimatedZoomEntryPressed: { opacity: 0.85 },
  estimatedZoomEntryText: {
    ...typography.bodyMdBold,
    color: colors.advisoryOrange,
    flexShrink: 1,
  },
  estimatedZoomEntryChevron: {
    ...typography.bodyMdBold,
    color: colors.advisoryOrange,
  },
  // Phase 20 TRUST-07 — 점수 억제 시 '기준 없음' state 카피. 토큰만 (하드코딩 금지).
  suppressedTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
    textAlign: 'center',
  },
  suppressedBody: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 18,
    paddingHorizontal: 4,
  },
  sectionTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
    marginTop: 8,
  },
  // Phase 12 Wave 2 (Plan 12-03 T2) — 동작 비교 헤더 row.
  // 좌측 sectionTitle + 우측 KeypointOverlayToggle (영역 2 카드 위, D-12-C4).
  compareHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  // Phase 12 Wave 2 (Plan 12-03 T3) — 차원 카드 영역 ⚠ amber badge 박제 row.
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  occlusionBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 9,
    backgroundColor: colors.softBg,
  },
  occlusionBadgeText: {
    ...typography.captionSmall,
    color: colors.warnAmber,
    fontWeight: '600',
  },
  // Phase 20 (UI ④) — 점수 맥락 카드 (구 LevelBenchmark 대체). 가짜 티어 칩 제거.
  bench: {
    width: '100%',
    marginTop: 14,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
    gap: 6,
  },
  benchSummary: {
    ...typography.caption,
    color: colors.textPrimary,
    textAlign: 'center',
    lineHeight: 18,
  },
  // self delta(지난 분석 대비 +N) — 상승 brand, 하락 textSecondary.
  scoreDelta: {
    ...typography.boxLabel,
    textAlign: 'center',
  },
  refCard: {
    alignItems: 'flex-start',
    gap: 6,
    backgroundColor: colors.brandTint, // 브랜드 톤 = 정은지 기준임을 시각화
    borderColor: colors.brand,
  },
  refHead: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  refAthlete: { ...typography.boxLabel, color: colors.brand },
  refLevel: {
    ...typography.captionSmall,
    color: colors.textWhite,
    backgroundColor: colors.brand,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
    overflow: 'hidden',
  },
  refName: { ...typography.listTitle, color: colors.textPrimary },
  refDesc: { ...typography.caption, color: colors.textSecondary, marginTop: 2 },
  // Phase 11 (Plan 11-02, ROADMAP SC#4) — 기준 모션 = 하나의 참고 문구.
  // refCard 가 brandTint 배경이라 brand 톤으로 강조 (절대값 오인 방지).
  refNote: { ...typography.captionSmall, color: colors.brand, marginTop: 4 },
  segmentHintText: {
    ...typography.caption,
    color: colors.textSecondary,
    alignSelf: 'flex-start',
    lineHeight: 18,
  },
  // #4 보조지표 안내 캡션 — segmentHintText 패턴 차용(typography.caption + textSecondary + lineHeight 18).
  auxCaption: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
    marginTop: 8,
    paddingHorizontal: 4,
  },
  partRow: { width: '100%', marginBottom: 14 },
  partHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    marginBottom: 8,
  },
  partLabel: { ...typography.boxLabel, color: colors.textPrimary },
  partScore: { ...typography.listTitle, color: colors.brand },
  // #2 (2026-06-21) — 비전 거부권 reframe: 측정값 톤다운(브랜드 트라이엄프 색 제거) +
  // "측정값" qualifier. 100 이 "완벽" 으로 안 읽히게.
  partScoreReframeWrap: { flexDirection: 'row', alignItems: 'flex-end' },
  partScoreMuted: { ...typography.listTitle, color: colors.textSecondary },
  partScoreQualifier: {
    ...typography.caption,
    color: colors.textSecondary,
    marginRight: 6,
    marginBottom: 3,
  },
  // Phase 12.5 v2: delta = 점수 아래 별도 row (deficit 과 시각 분리)
  partDelta: { ...typography.caption, textAlign: 'right', marginTop: 2 },
  // Phase 12.5 v2: track bar 아래 sub row (차원 부제 + 자세히 링크)
  partSubRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 6,
  },
  // 차원 부제 — "정은지 선수 자세 기준" 등 (DIMENSION_SUBLABEL_KO)
  dimSublabel: {
    ...typography.caption,
    color: colors.textSecondary,
  },
  // "자세히 ›" 링크 — brand color
  dimMore: {
    ...typography.caption,
    color: colors.brand,
    fontWeight: '600',
  },
  // quick-260705-r6v — 진단 문장 행 헤더 (라벨 + '자세히 ›').
  diagHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  // 진단 문장 (body 톤, 숫자 카드 대체).
  // 32-02 (D-03 최소 수리) — lineHeight 21 < fontSize 25(typography.body 상속)이라
  // '동작 흐름'/'안정성' 장문이 다중 행에서 줄겹침. lineHeight ≥ fontSize×1.3 규칙
  // (32-RESEARCH Pitfall 3)에 따라 35(=25×1.4)로 상향. 표현 전면 수정(심사 정보
  // 코너 전환)은 목업 게이트(32-04) 이후 32-11 소관 — 여기서는 겹침 해소만.
  diagSentence: {
    ...typography.body,
    color: colors.textPrimary,
    lineHeight: 35,
    marginTop: 6,
  },
  // 차원별 deficit summary (측정값/진단). 수치는 highlightNumbers 로 강조.
  dimDeficit: {
    ...typography.caption,
    color: colors.textPrimary,
    marginTop: 2,
  },
  // Phase 20 (UI ①) — 비전 거부권 적용 시 차원 점수 아래 맥락 1줄. 보조 톤.
  dimContextNote: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
    marginTop: 4,
  },
  // #2 (2026-06-21) — reframe 강조 콜아웃(brandTint 배경). 흐린 한 줄보다 강한 신호.
  dimReframeCallout: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    marginTop: 8,
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: 10,
    backgroundColor: colors.brandTint,
  },
  dimReframeText: {
    ...typography.caption,
    color: colors.textPrimary,
    lineHeight: 18,
    flex: 1,
  },
  track: {
    width: '100%',
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.divider,
    overflow: 'hidden',
  },
  trackFill: {
    height: '100%',
    borderRadius: 5,
    backgroundColor: colors.brand,
  },
  // quick-260705-o0s — 감점 0 성공 축하 카드 (refCard/vetoLeadCard 패턴 차용,
  // brandTint 배경 + brand 테두리, 토큰만). 이모지 0.
  cleanPassCard: {
    alignItems: 'flex-start',
    gap: 6,
    backgroundColor: colors.brandTint,
    borderColor: colors.brand,
  },
  cleanPassTitle: { ...typography.listTitle, color: colors.brand },
  cleanPassBody: {
    ...typography.caption,
    color: colors.textPrimary,
    lineHeight: 18,
  },
  // 32-12 (D-29) — 부분 실패 정직 고지 카드. 경고(빨강) 아님 — 차분한 정보 톤
  // (softBg + 좌측 정렬). D-05 하한 17 준수(bodyMdBold/bodySm). 오버클레임 금지.
  coverageCard: {
    backgroundColor: colors.softBg,
    borderRadius: radius.card,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.border,
    padding: spacing.cardPadding,
    alignItems: 'flex-start',
    gap: 8,
  },
  coverageTitle: { ...typography.bodyMdBold, color: colors.textPrimary },
  coverageBody: { ...typography.bodySm, color: colors.textMid },
  coverageTipRow: { alignSelf: 'stretch' },
  coverageTip: {
    ...typography.bodySm,
    color: colors.brand,
    fontWeight: '600',
  },
  tipCard: { alignItems: 'flex-start', gap: 8 },
  // Phase 11 (Plan 11-02, D-06 / D-07) — "강사에게 확인할 점" 섹션.
  // 섹션 헤더 sub = 강사 보조 도구 톤 (D-07). 카드 = 질문 리스트.
  coachSectionSub: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: -6,
  },
  coachCard: { alignItems: 'flex-start', gap: 10 },
  coachQuestionRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
  coachQuestionText: {
    ...typography.caption,
    color: colors.textPrimary,
    lineHeight: 18,
    flexShrink: 1,
  },
  // Phase 13 (Plan 13-A): 보완 운동 카드 + neutral state.
  exerciseCard: { alignItems: 'flex-start', gap: 4 },
  exerciseName: {
    ...typography.listTitle,
    color: colors.textPrimary,
  },
  exerciseSets: {
    ...typography.boxLabel,
    color: colors.brand,
    fontWeight: '700',
  },
  exercisePurpose: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  exerciseNeutral: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
    marginTop: 4,
  },
  // Phase 20 (UI ①) — 비전 거부권 LEAD 카드. brandTint 배경 + brand 테두리로
  // "먼저 봐야 할 것" 임을 시각 강조 (refCard 패턴 차용, 토큰만).
  vetoLeadCard: {
    backgroundColor: colors.brandTint,
    borderColor: colors.brand,
  },
  vetoLeadNote: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  // quick-260704-fwb — '먼저 교정할 점' 원인 기전 + 처방 연결 (토큰만).
  vetoCauseBlock: { gap: 4 },
  vetoCauseLabel: { ...typography.boxLabel, color: colors.textPrimary },
  vetoCauseItem: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  vetoFixLine: {
    ...typography.caption,
    color: colors.textPrimary,
    lineHeight: 18,
  },
  vetoFixLabel: { ...typography.boxLabel, color: colors.brand },
  tipHead: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  tipAngleRow: { flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' },
  tipAngle: { ...typography.boxLabel, color: colors.brand },
  // Phase 12 Wave 2 (Plan 12-03 T3) — D-12-D1 박제 저신뢰 추정 N° 컬러.
  tipAngleEstimate: { ...typography.boxLabel, color: colors.estimateGray },
  tipAngleCue: {
    ...typography.captionSmall,
    color: colors.textWhite,
    backgroundColor: colors.brand,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
    overflow: 'hidden',
  },
  tipIndex: {
    ...typography.caption,
    color: colors.textWhite,
    backgroundColor: colors.brand,
    width: 22,
    height: 22,
    borderRadius: 11,
    textAlign: 'center',
    lineHeight: 22,
    overflow: 'hidden',
  },
  tipTitle: { ...typography.listTitle, color: colors.textPrimary, flexShrink: 1 },
  tipDetail: { ...typography.caption, color: colors.textSecondary, lineHeight: 18 },
  // Phase 12.5 T9: 코칭 팁 "자세히 ›" 링크 (카드 우측 하단 정렬)
  tipMoreRow: { alignSelf: 'flex-end', marginTop: 4 },
  tipMore: { ...typography.caption, color: colors.brand, fontWeight: '600' },
  cta: {
    width: '100%',
    height: layout.ctaHeight,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 10,
  },
  ctaText: { ...typography.button, color: colors.textWhite },
  link: {
    ...typography.buttonSecondary,
    color: colors.brand,
    textAlign: 'center',
    marginTop: 14,
    textDecorationLine: 'underline',
  },
  // 28-CONTEXT D-05 — legacy 재분석 유도 배너 (dimReframeCallout/brandTint 선례,
  // 토큰만, 라이트 전용, 이모지 0). 안내 1줄 + 인라인 재분석 CTA.
  alignUpsellBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
    marginTop: 10,
    paddingVertical: 10,
    paddingHorizontal: spacing.cardPadding,
    borderRadius: radius.card,
    backgroundColor: colors.brandTint,
  },
  alignUpsellText: {
    ...typography.caption,
    color: colors.textPrimary,
    lineHeight: 18,
    flex: 1,
  },
  alignUpsellCta: {
    ...typography.buttonSecondary,
    color: colors.brand,
    textDecorationLine: 'underline',
  },
  // ── 32-11 대배선 신규 스타일 (토큰만, 하드코딩 금지) ───────────────────────
  // 6. 성장·지난 미션
  growthHeadline: { ...typography.listTitle, color: colors.textPrimary },
  growthBody: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  growthDeltaBadge: {
    alignSelf: 'flex-start',
    backgroundColor: colors.softBg,
    borderRadius: radius.listItem,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  growthDeltaText: { ...typography.badge, color: colors.textMid },
  // 7. 보완 운동 — 우회 카드 + 가로 스크롤
  detourCard: {
    alignItems: 'flex-start',
    gap: 6,
    backgroundColor: colors.brandTint,
    borderColor: colors.brand,
  },
  detourHeadline: { ...typography.boxLabel, color: colors.brand },
  detourBody: {
    ...typography.caption,
    color: colors.textPrimary,
    lineHeight: 18,
  },
  exerciseAltLabel: {
    ...typography.boxLabel,
    color: colors.textSecondary,
    marginTop: 4,
  },
  exerciseAltRow: { gap: 10, paddingVertical: 2, paddingRight: 4 },
  exerciseAltCard: {
    width: 200,
    alignItems: 'flex-start',
    gap: 4,
  },
  // 9. 심사 정보 코너 (개인화 심사 시뮬레이션)
  judgeIntro: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
    marginBottom: 4,
  },
  judgeRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 12,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
  },
  judgeRowText: { flex: 1, gap: 2 },
  judgeFault: { ...typography.boxLabel, color: colors.textPrimary },
  judgeReason: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 17,
  },
  // 33-15 (D-16) — 감점 수치 listTitle → metricNumber 강등 (수치는 근거, 헤드라인 아님).
  judgeDeduction: { ...typography.metricNumber, color: colors.brand },
  judgeTotalRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 8,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
  },
  judgeTotalLabel: { ...typography.boxLabel, color: colors.textPrimary },
  // 33-15 (D-16) — 환산 점수도 metricNumber 강등 (51점 헤드라인급 크기 해소).
  judgeTotalValue: { ...typography.metricNumber, color: colors.textPrimary },
  judgeDisclaimer: {
    ...typography.captionSmall,
    color: colors.textSecondary,
    lineHeight: 15,
    marginTop: 8,
  },
});
