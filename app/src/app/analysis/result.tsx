import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { AccuracyLimitBadge } from '../../components/AccuracyLimitBadge';
import { InjuryRiskSection } from '../../components/InjuryRiskSection';
import { CoachingTipDetailModal } from '../../components/CoachingTipDetailModal';
import { RecommendedExerciseModal } from '../../components/RecommendedExerciseModal';
import { CORRECTIVE_LIBRARY_HAS_ITEMS } from '../../data/correctiveExercises';
import { DimensionDetailModal } from '../../components/DimensionDetailModal';
import {
  KeypointOverlay,
  KEYPOINT_DELTA_HIGHLIGHT_DEG,
} from '../../components/KeypointOverlay';
import { KeypointOverlayToggle } from '../../components/KeypointOverlayToggle';
import { DeductionDetailSheet } from '../../components/DeductionDetailSheet';
import { OctagonScore, scoreGrade } from '../../components/OctagonScore';
import { ScoreBreakdownSection } from '../../components/ScoreBreakdownSection';
import { VideoCompare } from '../../components/VideoCompare';
import { ReferenceCornerSection } from '../../components/ReferenceCornerSection';
import type {
  ReferenceCardState,
  RotationCardState,
} from '../../components/ReferenceCornerSection';
import { normalizeMotionAlignment } from '../../lib/alignmentWarp';
import { legacyOffsetFromCompareFrames } from '../../lib/manualOffset';
import {
  ANGLE_VS_REFERENCE_PREFIX,
  JOINT_LABEL_KO,
  KEYPOINT_FROM_ANGLE_KEY,
  REGION_MEMBER_KEYPOINTS,
  buildDeductionMarkers,
  buildDeductionTicks,
  composeDimensionDiagnosisKo,
  composeScoringBasisKo,
  composeShortActionLabelKo,
  criterionLabelKo,
  formatDeductionNumber,
  isCleanPass,
  projectDeductionRecordKeypoints,
} from '../../lib/deductionLabels';
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
  DIMENSION_LABEL_KO,
  DIMENSION_ORDER,
  DIMENSION_SUBLABEL_KO,
  DOMINANT_HAND_LABEL_KO,
  EXPERIENCE_LABEL_KO,
  PAIN_AREA_LABEL_KO,
} from '../../types/analysis';
import type {
  AnalysisResult,
  BodyProfile,
  CoachingTip,
  DeductionRecord,
  DimensionExplanation,
  FaultZoomComparison,
  JointDirection,
  JointScore,
  KeypointName,
  KeypointReport,
  ScoreDimension,
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

const REFERENCE_LEVEL_LABEL: Record<SkillLevel, string> = {
  basic: '기본기',
  intermediate: '중급',
  advanced: '고급',
};

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

function DimensionScoreRow({
  dim,
  score,
  delta,
  explanation,
  onDetailPress,
  contextNote,
  reframeVeto,
  labelSuffix,
}: {
  dim: ScoreDimension;
  score: number;
  delta?: number;
  // Phase 12.5: 차원별 baseline + deficitSummary. 옵셔널 — 이전 빌드 doc 호환.
  explanation?: DimensionExplanation;
  // Phase 12.5 v2 (belle 피드백): "자세히 ›" 링크 → 모달 (DimensionDetailModal).
  onDetailPress?: (dim: ScoreDimension) => void;
  // Phase 20 (UI ①): 비전 거부권 적용 시 점수 아래 맥락 (각도 100 오해 차단).
  contextNote?: string;
  // #2 (2026-06-21): 비전 거부권으로 종합이 낮아졌는데 이 차원 측정값이 높아(예: 각도
  // 100) "완벽" 으로 오인되는 경우. 숫자를 측정값 톤으로 낮추고 contextNote 를 강조
  // 콜아웃으로 띄운다 (흐린 한 줄로는 belle 가 오인 — 진짜 reframe).
  reframeVeto?: boolean;
  // quick-260705-o0s — ' (참고)' 접미 (angle/stability, 결과 화면 전용).
  // DIMENSION_LABEL_KO 자체를 오염시키지 않기 위한 렌더 시 접미 (다른 화면 무접촉).
  labelSuffix?: string;
}) {
  return (
    <View style={styles.partRow}>
      <View style={styles.partHead}>
        <Text style={styles.partLabel}>
          {`${DIMENSION_LABEL_KO[dim]}${labelSuffix ?? ''}`}
        </Text>
        {reframeVeto ? (
          <View style={styles.partScoreReframeWrap}>
            <Text style={styles.partScoreQualifier}>측정값</Text>
            <Text style={styles.partScoreMuted}>{score}</Text>
          </View>
        ) : (
          <Text style={styles.partScore}>{score}</Text>
        )}
      </View>
      {/* Phase 12.5 v2: delta row 분리 (점수 아래 별도 줄, deficit 과 시각 분리) */}
      {delta != null && delta !== 0 && (
        <Text
          style={[
            styles.partDelta,
            { color: delta > 0 ? colors.brand : colors.textSecondary },
          ]}
        >
          {delta > 0 ? `지난 분석 대비 +${delta}점` : `지난 분석 대비 ${delta}점`}
        </Text>
      )}
      <View style={styles.track}>
        <View style={[styles.trackFill, { width: `${Math.max(0, Math.min(100, score))}%` }]} />
      </View>
      {/* sub row: 차원 부제 + "자세히 ›" 링크 */}
      <View style={styles.partSubRow}>
        <Text style={styles.dimSublabel}>{DIMENSION_SUBLABEL_KO[dim]}</Text>
        {onDetailPress && (
          <Pressable
            onPress={() => onDetailPress(dim)}
            accessibilityRole="button"
            accessibilityLabel={`${DIMENSION_LABEL_KO[dim]} 자세히 보기`}
            hitSlop={8}
          >
            <Text style={styles.dimMore}>자세히 ›</Text>
          </Pressable>
        )}
      </View>
      {/* deficit summary — 측정값/진단 (코칭 팁과 분리: 코칭 팁 = 행동 지시) */}
      {explanation?.deficitSummary && (
        <Text style={styles.dimDeficit}>
          {highlightNumbers(explanation.deficitSummary)}
        </Text>
      )}
      {/* Phase 20 (UI ①)/#2 — 비전 거부권 맥락. 각도 100인데 종합 75 → "완벽" 오해
          차단. reframeVeto 면 강조 콜아웃(brandTint), 아니면 보조 톤 1줄. 토큰만. */}
      {contextNote &&
        (reframeVeto ? (
          <View style={styles.dimReframeCallout}>
            <Ionicons name="information-circle" size={15} color={colors.brand} />
            <Text style={styles.dimReframeText}>{contextNote}</Text>
          </View>
        ) : (
          <Text style={styles.dimContextNote}>{contextNote}</Text>
        ))}
    </View>
  );
}

// quick-260705-r6v — 참고 지표 진단 문장 미니 라벨 (결과 화면 전용, DIMENSION_LABEL_KO
// 원본 무접촉). belle 예시 "동작 흐름 / 안정성".
const DIAGNOSIS_LABEL_KO: Record<'angle' | 'stability', string> = {
  angle: '동작 흐름',
  stability: '안정성',
};

// quick-260705-r6v — 참고 지표 진단 문장 행 (숫자 카드 대체, mode1 한정).
// "각도 유사도 99 인데 47점" 모순 카피 해소 — 숫자 대신 감점 유무 × 지표값 구간
// 조건부 문장. 숫자는 '자세히' 모달로 이동. 토큰만 (하드코딩 금지).
function DimensionDiagnosisRow({
  dim,
  sentence,
  onDetailPress,
}: {
  dim: 'angle' | 'stability';
  sentence: string;
  onDetailPress: (dim: ScoreDimension) => void;
}) {
  return (
    <View style={styles.partRow}>
      <View style={styles.diagHead}>
        <Text style={styles.partLabel}>{DIAGNOSIS_LABEL_KO[dim]}</Text>
        <Pressable
          onPress={() => onDetailPress(dim)}
          accessibilityRole="button"
          accessibilityLabel={`${DIAGNOSIS_LABEL_KO[dim]} 자세히 보기`}
          hitSlop={8}
        >
          <Text style={styles.dimMore}>자세히 ›</Text>
        </Pressable>
      </View>
      <Text style={styles.diagSentence}>{sentence}</Text>
    </View>
  );
}

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
      <View style={styles.container}>
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

  // quick-260702-q8q → 29-CONTEXT D-01 — "점수 계산 내역" 섹션 렌더 가드.
  // 29-04: mode 무관화 — deductionBreakdown 보유 doc 만 (29-02 가 mode3 등록 동작
  // md 보유 시에만 방출하므로 미등록/legacy/빈 criteria 동작은 필드 부재 → 섹션
  // 자연 숨김, normalize 가 malformed 를 undefined 로 접음 — 크래시 0). mode1 전용
  // 조건 제거 근거 = 29-CONTEXT D-01 (mode3 투명 감점-합산 소비).
  const showBreakdownSection = result.deductionBreakdown != null;

  // Phase 20 (UI ④) — 점수 맥락 카드의 "교정 포인트". 비전 결함(primaryFault)
  // 우선, 없으면 top 코칭 팁 제목(가장 먼저 다듬을 관절). 둘 다 없으면 null →
  // 일반 격려 카피. 추가 fetch 0 (이미 result 에 있는 데이터만 사용).
  const correctionPoint =
    vetoPrimaryFault ?? result.tips[0]?.title ?? null;

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
  const dims = DIMENSION_ORDER.filter((d) => dimensionScores[d] != null);
  // Phase 12.5: 차원별 explanation. 이전 빌드 doc 호환 — 없으면 hasExplanation=false.
  const dimensionExplanation = result.dimensionExplanation;
  const hasExplanation =
    dimensionExplanation != null &&
    Object.keys(dimensionExplanation).length > 0;
  // Phase 12.5 T8: 차원 "자세히 ›" 모달 state. dim null = 닫힘.
  const [detailDim, setDetailDim] = useState<ScoreDimension | null>(null);
  const detailMode: 'mode1' | 'mode3' = cmp.mode === 'mode1' ? 'mode1' : 'mode3';
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
  const selectedRecord =
    detailRecordIndex != null
      ? result.deductionBreakdown?.records[detailRecordIndex] ?? null
      : null;
  const selectedRecordNumber =
    detailRecordIndex != null
      ? markers.recordNumbers[detailRecordIndex] ?? null
      : null;
  // zoom 매칭 — 선택 record 투영 keypoint ∩ faultZoomComparisons (joint 또는
  // REGION_MEMBER_KEYPOINTS[region]). tier='confirmed'(또는 tier 부재 legacy)만 —
  // advisory 는 감점 시트에 오매칭 금지 (planner_findings 7). 없으면 null (사진 없이
  // 수치·문구만 — graceful).
  const selectedZoom = useMemo<FaultZoomComparison | null>(() => {
    if (!selectedRecord) return null;
    const kps = new Set(
      projectDeductionRecordKeypoints(selectedRecord, vetoFaultJoints),
    );
    if (kps.size === 0) return null;
    for (const z of result.faultZoomComparisons ?? []) {
      if (z.tier === 'advisory') continue;
      const zoomKps: KeypointName[] = z.region
        ? [...(REGION_MEMBER_KEYPOINTS[z.region] ?? [])]
        : [z.joint];
      if (zoomKps.some((k) => kps.has(k))) return z;
    }
    return null;
  }, [selectedRecord, vetoFaultJoints, result.faultZoomComparisons]);
  // actionPhrase — 범례와 동일 소스 (문구 이중화 금지).
  const selectedActionPhrase = selectedRecord
    ? actionPhraseForRecord(selectedRecord, vetoFaultJoints, actionLabels)
    : null;

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
  // (정렬 활성 doc 은 VideoCompare 내부 dirty 가드가 무시 — offset 0 시작). fps 는
  // poseFrames 정본(:2105 부근)과 동일 환산: result.keypointReport?.fps || 9 /
  // referenceKeypointReport?.fps || 18 (9/18 신규 하드코딩 금지, SP-6). 유효 쌍 0 →
  // null → 0(오프셋 없음, 슬라이더만 제공).
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

  // Phase 12 Wave 2 (Plan 12-03 T2) — KeypointOverlay 토글 (D-12-C4 박제).
  // Pitfall 6 우회: useState(true) initial — 깜빡임 무시. OFF 사용자는 진입 시
  // 잠시 ON 보였다가 useEffect 가 AsyncStorage 읽어 false 로 전환 (수용 가능).
  //
  // AsyncStorage key '@sunity:keypoint_overlay_enabled' — Firebase Auth backing
  // store 와 namespace 충돌 0 ([[firebase-project-account]] 정합, T-12-03-T4).
  const [overlayVisible, setOverlayVisible] = useState<boolean>(true);
  useEffect(() => {
    AsyncStorage.getItem('@sunity:keypoint_overlay_enabled')
      .then((v) => {
        if (v === 'false') setOverlayVisible(false);
      })
      .catch(() => {
        /* graceful — 시각 토글 default 보존 */
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
  const showOcclusionBadge = lowReliabilityRatioVal >= 0.2;
  const occlusionPercent = Math.round(lowReliabilityRatioVal * 100);

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
    if (!vetoApplied) return result.tips;
    const CONTRADICTORY = ['거의 동일', '일치도 100', '거의 다 왔'];
    return result.tips.filter((tip) => {
      const text = `${tip.title} ${tip.detail}`;
      return !CONTRADICTORY.some((phrase) => text.includes(phrase));
    });
  }, [result.tips, vetoApplied]);

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

  const deltaFor = (dim: ScoreDimension): number | undefined =>
    cmp.mode === 'mode3' && !cmp.isFirst
      ? cmp.deltaFromPrevious?.[dim]
      : undefined;

  return (
    <View style={styles.container}>
      <ScrollView
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

        {/* ── Phase 12 Wave 1 (Plan 12-02 T4) — 영역 1: 점수 게이지 ─────── */}
        {/* Phase 20 TRUST-07 (iter2 HIGH-2) — Mode3 미보유/저신뢰 시 점수카드 전체를
            '기준 없음' state 로 대체. OctagonScore + gradeBadge + summary + LevelBenchmark +
            scoreCaption 전부 비억제(!isScoreSuppressed) 분기 아래에만 둔다 — octagon 만 숨기면
            grade/summary/caption 으로 confident 점수가 누출된다 (D-08 confident 97 차단). */}
        {isScoreSuppressed ? (
          <View style={styles.card}>
            <Text style={styles.suppressedTitle}>기준 없음</Text>
            <Text style={styles.suppressedBody}>{suppressedHeaderCopy}</Text>
          </View>
        ) : (
          <View style={styles.card}>
            <OctagonScore score={result.overallScore} size={168} />
            <View style={styles.gradeRow}>
              <Text style={styles.gradeBadge}>{grade}</Text>
              <Text style={styles.summary}>{summary}</Text>
            </View>
            {/* Phase 20 (UI ④) — 가짜 입문/중급/고급 티어 제거. 정은지 기준 거리 +
                교정 포인트(+ 손에 있는 self delta)로 점수에 의미 부여. */}
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
            {/* Phase 20 (UI B1) — 비전 거부권으로 점수가 내려갔을 때 "왜 내려갔는지"를
                점수 근처에 1줄로 노출 (belle: "내가 판단할 길이 없네"). primaryFault =
                Gemini 가 찾은 결함 DESCRIPTION(자연어, 숫자 아님). legacy doc 호환 —
                applied + primaryFault 있을 때만 렌더. 토큰만 (하드코딩 금지). */}
            {vetoPrimaryFault ? (
              <Text style={styles.scoringBasis}>
                AI 영상 분석에서 발견한 점: {vetoPrimaryFault}
              </Text>
            ) : null}
            {/* 260612-t9m: 점수 안내 캡션 — stability tol 25° 보정과 함께 "90+ 정상" 사용자 인지 정합 */}
            <Text style={styles.scoreCaption}>
              촬영 노이즈와 측정 허용 범위가 있어 100점은 잘 나오지 않아요. 90점 이상이면 정상 자세에 가깝습니다.
            </Text>
          </View>
        )}

        {/* 29-CONTEXT D-05 — mode3 한계 고지 (breakdown 부재 경로: 미등록/legacy/
            빈 criteria/suppressed). breakdown 표시 중이면 ScoreBreakdownSection
            footnote 로 렌더되므로 여기선 미표시 — !showBreakdownSection 게이트로
            mode3 결과에 한계 고지가 정확히 1곳 존재하도록 보장. mode1 무회귀. */}
        {cmp.mode === 'mode3' && !showBreakdownSection ? (
          <Text style={styles.mode3LimitNotice}>{MODE3_LIMIT_NOTICE}</Text>
        ) : null}

        {/* ── Phase 10 (10-02 D-08) — 부상 위험 신호 amber 경고 섹션 ────────
            점수 게이지 직후 + "동작 비교" 직전. 플래그 없으면 컴포넌트가 null 반환
            (섹션 OMIT, 안심 카피 금지). flagType 4종 카피맵 보유 → 10-03/10-04
            플래그 자동 렌더. result.safetyFlags 부재/구버전 doc → graceful no-render. */}
        <InjuryRiskSection flags={result.safetyFlags} />

        {/* ── quick-260705-o0s → 29-CONTEXT D-01: 감점 0 성공 축하 섹션 (belle
            추가 피드백 #2) — 100점 정타(records 빈 배열)면 축하가 주인공.
            refCard/vetoLeadCard 스타일 패턴 차용 (brandTint, 토큰만). 29-04:
            mode 무관 (mode3 등록 동작 clean 도 축하). 단 mode3 축하 카피는 mode1
            문구(정은지 유사 계열) 재사용 금지 — 발전/자세 형태 중심 별도 문구,
            29-CONTEXT D-05 금지어 배제. legacy/미등록은 여전히 false. */}
        {cleanPass && (
          <View style={[styles.card, styles.cleanPassCard]}>
            <Text style={styles.cleanPassTitle}>감점 항목이 없어요</Text>
            <Text style={styles.cleanPassBody}>
              {cmp.mode === 'mode3'
                ? '측정한 자세 형태 기준을 모두 통과했어요. 이 자세를 유지하고 다음 영상과 비교해 발전을 확인해보세요.'
                : '측정 기준을 모두 통과했어요. 이 자세를 그대로 유지하세요.'}
            </Text>
          </View>
        )}

        {/* ── quick-260705-o0s: 점수 계산 내역 — 종합 점수 직후로 승격 ─────
            47점의 공식 설명(감점 내역)이 첫 화면 주인공 (belle 3차 피드백 승인
            순서 ②). cleanPass 여도 렌더 유지 — "측정 감점 없음" 행이 100점의
            공식 근거 (투명성 원칙). 렌더 가드는 기존 showBreakdownSection 그대로
            (mode1 + breakdown 보유 doc 전용, legacy/mode3 숨김). 번호/기준문구는
            buildDeductionMarkers/composeScoringBasisKo 단일 소스.
            점수 원칙: [[scoring-must-be-transparent-deduction-tally]]. */}
        {showBreakdownSection && result.deductionBreakdown != null && (
          <>
            <Text style={styles.sectionTitle}>점수 계산 내역</Text>
            <ScoreBreakdownSection
              breakdown={result.deductionBreakdown}
              recordNumbers={markers.recordNumbers}
              basisLine={breakdownBasisLine}
              // 29-CONTEXT D-05 — mode3 한계 고지는 내역 카드 footnote 로 (mode1 미전달).
              limitNotice={cmp.mode === 'mode3' ? MODE3_LIMIT_NOTICE : undefined}
              // quick-260705-r6v — 내역 행 탭 → 드릴다운 시트 (진입점 1).
              onRecordPress={setDetailRecordIndex}
            />
          </>
        )}

        {/* ── 콤보 부분 점수 (mode1 콤보 모션 분석 시에만) — 점수 상세 계열이라
            내역 직후 배치 (quick-260705-o0s 재배치 재량 판단). ─────────── */}
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
                  visible={overlayVisible}
                  jointAngles={userJointAngles}
                  // #3 (2026-06-21) — 결함 keypoint 권위 강조. quick-260704-fz4:
                  // 소스를 vetoFaultJoints 단독 → confirmedKeypoints(감점 근거
                  // records ∪ vetoFaultJoints) 단일 조립으로 확장 — 표·마커·카드
                  // 가 같은 "빨강=확정 감점" 소스를 쓴다. 비면 기존 각도편차
                  // 폴백 (무회귀).
                  highlightKeypoints={confirmedKeypointList}
                  // quick-260704-fz4 — 측정 초과·확인 권장(주황, 감점 아님) 마커.
                  // 표·확대 카드와 동일 단일 소스(attentionKeypoints memo).
                  attentionKeypoints={attentionKeypoints}
                  // quick-260705-r6v — 스플릿(다리 4관절) 그룹 마커: 멤버 centroid
                  // 1점 + 번호. 영상 위 텍스트 pill 은 전면 제거(여백 범례/시트로
                  // 이동). 사용자 측만 전달 (정은지 측 무변경).
                  groupMarkers={markers.groupMarkers}
                  // quick-260705-o0s — 감점 record 관절 번호 점 ('점수 계산 내역'
                  // 행 번호와 buildDeductionMarkers 단일 소스 — 항상 일치).
                  markerNumbers={markers.keypointNumbers}
                  // quick-260705-r6v — 번호 점 탭 → 드릴다운 시트 (진입점 3).
                  // 전체화면(opts.sizeScale 존재)에선 시트가 중첩 Modal 이 되므로
                  // 콜백 미전달 — 전체화면 점 탭은 여백 범례가 대체(iOS 함정 회피).
                  onMarkerPress={opts?.sizeScale ? undefined : openRecordByNumber}
                  // Phase 20 (UI ②) — faultJoints 가 없을 때(매핑 0/legacy)만 폴백:
                  // 임계(20°) 넘는 관절이 없으면 편차 최대 2개 강제 강조 (마커 0개 모순 제거).
                  // 정타 영상은 0 → 오탐 0.
                  forceHighlightWorstCount={vetoApplied ? 2 : 0}
                  // quick-260702-t0v — 가로 전체화면 뷰어가 opts.sizeScale=2.0 전달
                  // (각도 라벨 가독). 세로 카드는 opts 미전달 → 1 (무회귀).
                  sizeScale={opts?.sizeScale ?? 1}
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
              fullscreenLegend={fullscreenLegend}
              timelineTicks={timelineTicks}
              tickFrameCount={anglesFrames ?? 0}
              // quick-260705-r6v — 여백 범례 탭 → 드릴다운 시트 (진입점 2).
              // VideoCompare 가 closeFullscreen 선행 후 콜백(iOS 중첩 Modal 회피).
              onLegendPress={openRecordByNumber}
            />
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
        {!cleanPass && vetoApplied && vetoPrimaryFault ? (
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
              {guide && (
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
              )}
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

        {/* ── Phase 11 (Plan 11-02, COACH-01 / D-06 / D-07 / HIGH-2):
            강사에게 확인할 점 섹션 ─────────────────────────────────────────
            두 리포트(force + body)의 openQuestionsForCoach 병합 결과(중복 제거 +
            최대 5개). 수강생이 강사에게 가져갈 질문 거리 → 학원 도입·강사 보조
            도구 포지셔닝 직접 지원. 질문이 1개 이상일 때만 섹션 렌더 (graceful —
            hook 없는 이전 doc / 한쪽 리포트만 hook 인 doc 도 크래시 0).
            섹션 헤더 sub 가 "AI = 강사 보조 도구" 톤을 강화한다 (D-07). */}
        {openQuestionsForCoach.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>강사에게 확인할 점</Text>
            <Text style={styles.coachSectionSub}>
              아래 질문을 강사와 함께 확인해보세요.
            </Text>
            <View style={[styles.card, styles.coachCard]}>
              {openQuestionsForCoach.map((q, i) => (
                <View key={`${q}-${i}`} style={styles.coachQuestionRow}>
                  <Ionicons
                    name="chatbubble-ellipses-outline"
                    size={16}
                    color={colors.brand}
                  />
                  <Text style={styles.coachQuestionText}>{q}</Text>
                </View>
              ))}
            </View>
          </>
        )}

        {/* ── Phase 13 (Plan 13-A, PERS-03): 보완 운동 섹션 ──────────────
            MEDIUM-1: 가시성 = 개인화 추천 있음 OR 라이브러리에 항목 있음.
            추천이 비어도 라이브러리가 있으면 "전체 보완 운동 보기" entry 유지
            (criteria 4 entry point 미소멸). 분기:
            (a) 추천 있음 → result.recommendedExercises 카드 (3~5 subset) +
                "다른 운동 보기" → 전체 라이브러리 모달.
            (b) 추천 없음 → neutral 한 줄 + "전체 보완 운동 보기" → 동일 모달. */}
        {((result.recommendedExercises?.length ?? 0) > 0 ||
          CORRECTIVE_LIBRARY_HAS_ITEMS) && (
          <>
            <Text style={styles.sectionTitle}>보완 운동</Text>
            {(result.recommendedExercises?.length ?? 0) > 0 ? (
              <>
                {result.recommendedExercises!.map((ex, i) => (
                  <View
                    key={`${ex.name}-${i}`}
                    style={[styles.card, styles.exerciseCard]}
                  >
                    <Text style={styles.exerciseName}>{ex.name}</Text>
                    <Text style={styles.exerciseSets}>{ex.setsReps}</Text>
                    <Text style={styles.exercisePurpose}>{ex.purpose}</Text>
                  </View>
                ))}
                <Pressable
                  onPress={() => setExerciseModalOpen(true)}
                  accessibilityRole="button"
                  accessibilityLabel="다른 보완 운동 보기"
                  hitSlop={8}
                  style={styles.tipMoreRow}
                >
                  <Text style={styles.tipMore}>다른 운동 보기 ›</Text>
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
        )}

        {/* ── Phase 31 (D-09): "참고하세요" 참고코너 ────────────────────────
            배치 = 보완 운동 **아래**, 참고 지표 근처 (31-08 Task 1 belle 승인
            option-a). 채점 관련 표면(점수카드·감점 내역·보완 운동)을 전부 지난
            뒤에 오므로 "점수 비반영"이 레이아웃만 봐도 드러난다 — 이게 D-09 의
            요구이고, 위로 올리면 비채점 생성물이 채점 근거처럼 읽힌다.
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
          // 사다리(WR-03/D-09). 시각 = kr 공간 인덱스 / kr.fps — joints3d(9fps)
          // 공간과 섞지 않는다 (2026-07-20 프레임 시점 버그 재발 방지).
          poseFrames={
            compareFrames
              ? {
                  user: {
                    url: freshMyUrl || result.myVideoUrl || undefined,
                    timeSec:
                      compareFrames.userIdx /
                      (result.keypointReport?.fps || 9),
                    report: userKeypointReport,
                    frameIdx: compareFrames.userIdx,
                    label: '내 자세',
                  },
                  reference: {
                    url:
                      freshRefUrl ||
                      result.referenceVideoUrl ||
                      refMotion?.videoUrl ||
                      undefined,
                    timeSec:
                      compareFrames.refIdx /
                      (referenceKeypointReport?.fps || 18),
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

        {/* ── quick-260705-o0s: 참고 지표 (구 '세부 점수', 맨 아래 강등) ──────
            belle 3차 피드백 승인 순서 ⑦ — 각도 유사도(DTW)/안정성은 참고 지표이지
            종합 점수 근거가 아님 (종합 = 감점 tally, Phase 24). angle/stability
            라벨에만 ' (참고)' 접미 — 결과 화면 렌더 접미라 DIMENSION_LABEL_KO
            원본/타 화면 무접촉. occlusion badge/자세히 모달/reframe 콜아웃 유지. */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>참고 지표</Text>
          {showOcclusionBadge && (
            <View style={styles.occlusionBadge}>
              <Ionicons name="warning" size={12} color={colors.warnAmber} />
              <Text style={styles.occlusionBadgeText}>
                {`가림 ${occlusionPercent}%`}
              </Text>
            </View>
          )}
        </View>
        <View style={styles.card}>
          {dims.map((dim) => {
            // quick-260705-r6v — mode1 + breakdown 보유 시 angle/stability 는 숫자
            // 카드 대신 진단 문장 행(감점 유무 × 지표값 구간 조건부). 문장 null(비유한
            // 값)이면 행 생략. line 차원 / mode3 경로 / mode1-legacy(breakdown 부재,
            // cleanPass 판단 불가)는 기존 숫자 행(DimensionScoreRow) 유지.
            const useDiagnosis =
              cmp.mode === 'mode1' &&
              result.deductionBreakdown != null &&
              (dim === 'angle' || dim === 'stability');
            if (useDiagnosis) {
              const sentence = composeDimensionDiagnosisKo(
                dim,
                cleanPass,
                dimensionScores[dim] as number,
              );
              if (sentence == null) return null;
              return (
                <DimensionDiagnosisRow
                  key={dim}
                  dim={dim}
                  sentence={sentence}
                  onDetailPress={(d) => setDetailDim(d)}
                />
              );
            }
            return (
              <DimensionScoreRow
                key={dim}
                dim={dim}
                score={dimensionScores[dim] as number}
                delta={deltaFor(dim)}
                explanation={dimensionExplanation?.[dim]}
                onDetailPress={(d) => setDetailDim(d)}
                // quick-260705-o0s — 각도 유사도/안정성에 ' (참고)' 접미 (결과 화면
                // 전용 렌더 접미 — DIMENSION_LABEL_KO 소비하는 다른 화면 오염 0).
                labelSuffix={
                  dim === 'angle' || dim === 'stability' ? ' (참고)' : undefined
                }
              // Phase 20 (UI ①)/#2 + Phase 24 — 비전 채점 적용 시 '각도' 측정값이 높아(예: 100)
              // "완벽" 으로 오인되는 문제. 측정값이 종합(감점 합산 final)보다 높을 때만 reframe:
              // 숫자를 '측정값' 톤으로 낮추고 강조 콜아웃으로 "각도로 안 드러나는 결함을
              // 발견해 종합을 낮췄다" 를 명시. 각도가 이미 종합 이하면 오인 없음 → 평범 표기.
              // Phase 24: 권위 점수원 = §10 deductionBreakdown.final(밴드 제거). 폴백 =
              // visionVeto.tallyFinal(applied audit mirror) → overallScore.
              reframeVeto={
                vetoApplied &&
                dim === 'angle' &&
                (dimensionScores[dim] as number) >
                  (result.deductionBreakdown?.final ??
                    (result.visionVeto?.status === 'applied'
                      ? result.visionVeto.tallyFinal
                      : result.overallScore ?? 0))
              }
              contextNote={
                vetoApplied &&
                dim === 'angle' &&
                (dimensionScores[dim] as number) >
                  (result.deductionBreakdown?.final ??
                    (result.visionVeto?.status === 'applied'
                      ? result.visionVeto.tallyFinal
                      : result.overallScore ?? 0))
                  ? // quick-260702-q8q 문구 사실 점검: "각도로 안 드러나는 자세 결함"
                    // 은 vision-측정 split 케이스에 사실 정합(각도 차원은 DTW 유사도,
                    // 감점은 vision 측정 — 거짓 아님) → 유지. quick-260705-o0s 재배치로
                    // 점수 계산 내역이 이 섹션보다 위 → 꼬리 문장 "아래"→"위" 수정.
                    `각도 측정은 기준에 가깝지만, AI 영상 분석이 각도로 안 드러나는 자세 결함을 발견해 종합 점수를 낮췄어요.${
                      showBreakdownSection
                        ? " 위 '점수 계산 내역'에서 감점 근거를 확인할 수 있어요."
                        : ''
                    }`
                  : undefined
              }
              />
            );
          })}
        </View>
        {/* #4 표시 정합 — 안정성은 보조 지표(종합 입력 제외, 표시 유지). 근거 Phase 19 D-01 / dimensions.py 헤더 */}
        {dims.includes('stability') && (
          <Text style={styles.auxCaption}>
            안정성은 자세 참고용 보조 지표예요. 종합 점수에는 직접 합산되지 않아요.
          </Text>
        )}

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
      {/* Phase 12.5 T8: 차원별 "자세히 ›" 모달. dim=null 시 닫힘.
          belle 피드백 (2026-06-07): 동작 이름 + 사용자 이름 동적 카피 — 모달이
          "폭스탑 동작에서 ... OO님의 분석을 반영하여" 식으로 자연어 안내. */}
      <DimensionDetailModal
        visible={detailDim != null}
        dim={detailDim}
        score={detailDim != null ? (dimensionScores[detailDim] ?? null) : null}
        explanation={detailDim != null ? dimensionExplanation?.[detailDim] : undefined}
        mode={detailMode}
        motionName={cmp.mode === 'mode1' ? cmp.referenceMotionName : undefined}
        userName={undefined /* TODO: Firebase displayName 박제 박제 박제 박제 */}
        lowReliabilityRatio={lowReliabilityRatioVal}
        scoringBasis={cmp.scoringBasis}
        scoringBasisLabel={cmp.scoringBasisLabel}
        onClose={() => setDetailDim(null)}
      />
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
        record={selectedRecord}
        recordNumber={selectedRecordNumber}
        actionPhrase={selectedActionPhrase}
        zoom={selectedZoom}
        zoomPending={zoomPending}
        // D-04 앱측 (28-05 공급) — DTW 대응 실패 시 ref 는 전신 폴백 이미지라
        // "같은 동작 순간을 못 찾았다"고 정직 고지. 부재(legacy)/'dtw'면 false → 캡션 없음.
        refMatchFailed={selectedZoom?.refMatch === 'failed'}
        // 29-CONTEXT D-06 — mode3 드릴다운 비교 라벨도 지난/이번 계열 (정은지 미언급).
        rightLabel={cmp.mode === 'mode1' ? `${cmp.athleteName} 선수` : '지난 영상'}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg, // 서브 화면 = 흰 배경 (§5-1)
  },
  content: {
    paddingTop: layout.safeAreaTop,
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
  mode3LimitNotice: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
    paddingHorizontal: 4,
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
  diagSentence: {
    ...typography.body,
    color: colors.textPrimary,
    lineHeight: 21,
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
});
