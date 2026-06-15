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
import { CoachingTipDetailModal } from '../../components/CoachingTipDetailModal';
import { DimensionDetailModal } from '../../components/DimensionDetailModal';
import {
  ForcePatternCard,
  _FALLBACK_BODY,
} from '../../components/ForcePatternCard';
import { ForcePatternDetailModal } from '../../components/ForcePatternDetailModal';
import { KeypointOverlay } from '../../components/KeypointOverlay';
import { KeypointOverlayToggle } from '../../components/KeypointOverlayToggle';
import { OctagonScore, scoreGrade } from '../../components/OctagonScore';
import { PoseViewer3D } from '../../components/PoseViewer3D';
import { VideoCompare } from '../../components/VideoCompare';
import {
  LEVEL_EXPECTED_SCORE,
  LEVEL_LABEL_KO,
  levelStanding,
} from '../../lib/levels';
import { reshapePose3dData } from '../../lib/joints';
import { useReferenceMotion } from '../../lib/referenceMotions';
import { getSimulatedResult } from '../../lib/simulatedResult';
import { useAnalysisDoc } from '../../lib/userAnalyses';
import { useBodyProfile } from '../../lib/bodyProfile';
import { requestPlaybackUrl } from '../../lib/api';
import {
  DIMENSION_LABEL_KO,
  DIMENSION_ORDER,
  DIMENSION_SUBLABEL_KO,
} from '../../types/analysis';
import type {
  AnalysisMode,
  AnalysisResult,
  BodyProfile,
  CoachingTip,
  DimensionExplanation,
  DominantHand,
  ExperienceLevel,
  ForcePatternFinding,
  JointDirection,
  JointScore,
  KeypointReport,
  PainArea,
  ScoreDimension,
  SegmentScores,
  SkillLevel,
  SynthesisWarningCode,
} from '../../types/analysis';
import { colors, layout, radius, spacing, typography } from '../../theme';

const REFERENCE_LEVEL_LABEL: Record<SkillLevel, string> = {
  basic: '기본기',
  intermediate: '중급',
  advanced: '고급',
};

const LEVEL_ORDER: SkillLevel[] = ['basic', 'intermediate', 'advanced'];

// [R1] BodyProfile snapshot 요약 라벨 (analysis.ts union / BodyProfileForm 정합).
// 결과 화면은 분석-당시 SNAPSHOT(storedDoc.bodyProfile)을 source-of-truth 로
// 표기 — live useBodyProfile 아님 (재현성). weightKg 는 보조 ONLY (D-05) 라
// 요약에 포함하지 않는다 (점수 경로 무관 + 표기 노이즈 방지).
const BODY_EXPERIENCE_LABEL: Record<ExperienceLevel, string> = {
  beginner: '초급',
  intermediate: '중급',
  advanced: '고급',
};
const BODY_HAND_LABEL: Record<DominantHand, string> = {
  left: '왼손',
  right: '오른손',
  both: '양손',
};
const BODY_PAIN_AREA_LABEL: Record<PainArea, string> = {
  shoulder: '어깨',
  wrist: '손목',
  lower_back: '허리',
  knee: '무릎',
  ankle: '발목',
  neck: '목',
  hip: '고관절',
  elbow: '팔꿈치',
};

// 채워진 필드만 "·" 로 묶어 요약 (부분 입력 graceful). 전부 비면 null → 표기 생략.
function summarizeBodyProfile(profile: BodyProfile | null | undefined): string | null {
  if (!profile) return null;
  const parts: string[] = [];
  if (profile.heightCm != null) parts.push(`키 ${profile.heightCm}cm`);
  if (profile.experience) parts.push(`경력 ${BODY_EXPERIENCE_LABEL[profile.experience]}`);
  if (profile.dominantHand) parts.push(`우세손 ${BODY_HAND_LABEL[profile.dominantHand]}`);
  if (profile.painAreas.length > 0) {
    parts.push(
      `통증 ${profile.painAreas.map((a) => BODY_PAIN_AREA_LABEL[a]).join('·')}`,
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
function mode1Summary(athleteName: string, similarity: number): string {
  const head = `${athleteName} 선수와 관절각 ${similarity}% 일치해요.`;
  if (similarity >= 75) return `${head} 거의 다 왔어요!`;
  if (similarity >= 50) return `${head} 핵심 구간을 다듬어 보세요.`;
  return `${head} 천천히 자세부터 잡아볼까요?`;
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

// JointScore.key (kismam: left_elbow / left_knee 등) → keypoint name (left_hand 등).
// 손 = elbow angle key 의 시각 keypoint. shoulder/hip/knee 는 1:1.
const ANGLE_KEY_TO_KEYPOINT: Record<string, string> = {
  left_shoulder: 'left_shoulder',
  right_shoulder: 'right_shoulder',
  left_hip: 'left_hip',
  right_hip: 'right_hip',
  left_knee: 'left_knee',
  right_knee: 'right_knee',
  left_elbow: 'left_hand',
  right_elbow: 'right_hand',
};

// 분석 결과 화면 (plan.md #8, design.md §8, ia AC-RES-001).
// 미설계 화면 → design.md §0 결정 트리로 자체 설계. 흰 배경(§5-1),
// 브랜드 포인트(#FF4B33), 스피너/이모지 없음, 토큰만 사용.
//
// 데이터: Firestore users/{uid}/analyses/{analysisId} doc (백엔드 갱신) 우선.
// getSimulatedResult 폴백은 dev 안전망 — 샘플 시드 누락·딥링크·새로고침 등 doc 가
// 아직 없는 케이스에서만 발동. 실 분석 경로는 loading.tsx 가 status='uploading'
// 부터 doc 를 쓰므로 폴백이 활성화될 일은 없다.

function LevelBenchmark({ score }: { score: number }) {
  // 입문 65 / 중급 78 / 고급 88 픽스처 대비 사용자 위치. KISMAM 자체가 절대 평가라
  // 점수의 의미를 한눈에 보이게 하는 보조 표시 — 데이터 누적되면 실 평균치로 교체.
  const standing = levelStanding(score);
  return (
    <View style={styles.bench}>
      <View style={styles.benchChips}>
        {LEVEL_ORDER.map((lv) => {
          const active = standing.band === lv;
          return (
            <View
              key={lv}
              style={[styles.benchChip, active && styles.benchChipActive]}
            >
              <Text
                style={[
                  styles.benchChipLabel,
                  active && styles.benchChipLabelActive,
                ]}
              >
                {LEVEL_LABEL_KO[lv]}
              </Text>
              <Text
                style={[
                  styles.benchChipScore,
                  active && styles.benchChipScoreActive,
                ]}
              >
                {LEVEL_EXPECTED_SCORE[lv]}
              </Text>
            </View>
          );
        })}
      </View>
      <Text style={styles.benchSummary}>{standing.summary}</Text>
    </View>
  );
}

function DimensionScoreRow({
  dim,
  score,
  delta,
  explanation,
  onDetailPress,
}: {
  dim: ScoreDimension;
  score: number;
  delta?: number;
  // Phase 12.5: 차원별 baseline + deficitSummary. 옵셔널 — 이전 빌드 doc 호환.
  explanation?: DimensionExplanation;
  // Phase 12.5 v2 (belle 피드백): "자세히 ›" 링크 → 모달 (DimensionDetailModal).
  onDetailPress?: (dim: ScoreDimension) => void;
}) {
  return (
    <View style={styles.partRow}>
      <View style={styles.partHead}>
        <Text style={styles.partLabel}>{DIMENSION_LABEL_KO[dim]}</Text>
        <Text style={styles.partScore}>{score}</Text>
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

export default function AnalysisResult() {
  const router = useRouter();
  const { mode, name, analysisId, referenceMotionId, referenceMotionName } =
    useLocalSearchParams<{
      mode?: AnalysisMode;
      name?: string;
      analysisId?: string;
      referenceMotionId?: string;
      referenceMotionName?: string;
    }>();
  // Firestore doc 가 권위 있는 소스. 없을 때만 시뮬 폴백(dev 안전망).
  const { doc: storedDoc } = useAnalysisDoc(analysisId);
  // [R1] 결과 화면 BodyProfile 표기 = 분석-당시 SNAPSHOT (storedDoc.bodyProfile).
  // live useBodyProfile 을 기본 소스로 쓰지 않는다 (분석 이후 프로필을 바꿔도
  // 과거 결과 표기는 분석 당시 값으로 재현되어야 함). snapshot 이 없는 구 doc
  // 에서만 live read 를 fallback 으로 허용.
  const { profile: liveProfile } = useBodyProfile();
  const bodyProfileSnapshot = storedDoc?.bodyProfile ?? liveProfile;
  const bodyProfileSummary = useMemo(
    () => summarizeBodyProfile(bodyProfileSnapshot),
    [bodyProfileSnapshot],
  );
  const analysisMode: AnalysisMode = mode === 'mode1' ? 'mode1' : 'mode3';
  const result: AnalysisResult = useMemo(() => {
    if (storedDoc?.result) return storedDoc.result;
    const r = getSimulatedResult(analysisMode);
    // 폴백 시 사용자가 #9 에서 고른 기준 모션 정보로 덮어씀.
    if (r.comparison.mode === 'mode1' && referenceMotionId) {
      r.comparison = {
        ...r.comparison,
        referenceMotionId,
        referenceMotionName:
          referenceMotionName || r.comparison.referenceMotionName,
      };
    }
    return r;
  }, [storedDoc, analysisMode, referenceMotionId, referenceMotionName]);

  const grade = scoreGrade(result.overallScore);
  const cmp = result.comparison;

  // mode1 메타 카드용 풀데이터. 시드 전이거나 로딩 중이면 motion=null →
  // 화면은 cmp.referenceMotionName / cmp.athleteName 으로 폴백 표시.
  const { motion: refMotion } = useReferenceMotion(
    cmp.mode === 'mode1' ? cmp.referenceMotionId : undefined,
  );

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
    const ext = prevDoc.videoFormat || 'mp4';
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
  }, [prevDoc?.analysisId, prevDoc?.createdAt, prevDoc?.videoFormat]);

  const summary =
    cmp.mode === 'mode1'
      ? mode1Summary(cmp.athleteName, cmp.similarity)
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
  // Phase 12 Wave 1 (Plan 12-02 T4) — ForcePatternCard tap → 자세히 모달 state.
  // finding null = 닫힘. modeContext 별 mode 분기 코드 X (D-12-U3 — backend 자동).
  const [detailFinding, setDetailFinding] = useState<ForcePatternFinding | null>(
    null,
  );

  // Phase 12 Wave 1 (Plan 12-02 T4) — Phase 9 finding Top-3 + 0-finding fallback.
  // findings.length ∈ {0, 1, 2, 3}: D-12-B1 박제 (0 → fallback big / 1 → big /
  // 2 → big + small × 1 / 3 → big + small × 2). 본 useMemo 가 fallback finding
  // 생성 (interpretation = _FALLBACK_BODY, pattern='unknown', confidence=0).
  const forcePatternFindings: ForcePatternFinding[] = useMemo(() => {
    const list = result.forcePatternInference?.findings ?? [];
    if (list.length > 0) return list.slice(0, 3);
    const fallback: ForcePatternFinding = {
      pattern: 'unknown',
      phase: 'hold',
      sourceSignal: 'high_jitter',
      reason: '',
      interpretation: _FALLBACK_BODY,
      confidence: 0,
      jointHint: null,
      warnings: [],
    };
    return [fallback];
  }, [result.forcePatternInference]);

  // Phase 12 Wave 1 (Plan 12-02 T4) — KeypointOverlay 박제 site (R7 render prop).
  // VideoCompare 가 player lifecycle 안에서 callback 호출. Wave 1 = 정적
  // frameIndex=0 + visible=true (토글 UI 는 Wave 2 책임).
  // videoSize 는 9:16 영상 native 비율 기본값 — VideoView contentFit="contain"
  // 위 normalized 0..1 좌표 그대로 박제 (KeypointOverlay viewBox 가 자동 scale).
  const overlayVideoSize = { width: 720, height: 1280 };

  const userKeypointReport = result.keypointReport ?? null;
  const referenceKeypointReport = refMotion?.referenceKeypointReport ?? null;

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

  // Phase 4 (04-02 R3) — 3D 자세 뷰어 데이터 소스. doc.result.joints3d (04-01
  // 신설 flat 필드) → (T, J, 3) reshape. angles 는 절대 전달 금지 — 관절각
  // (T, J) 스칼라이므로 좌표 reshape 불가. reshapePose3dData 의 length guard
  // 가 잡지만 source 단계에서 차단.
  const joints3d = useMemo(
    () =>
      reshapePose3dData(
        result.joints3d ?? null,
        result.joints3dKeys ?? [],
        result.joints3dFrames ?? 0,
      ),
    [result.joints3d, result.joints3dKeys, result.joints3dFrames],
  );
  const [currentFrame, setCurrentFrame] = useState(0);

  // 코칭 팁 row 의 각도 표시 분기 = (joint 평균 confidence < 0.5) 또는
  // (low reliability frame 비율 ≥ 0.30). 추정 표기 + ⓘ tap → Alert.
  const isAngleEstimated = (jointKey: string): boolean => {
    if (lowReliabilityRatioVal >= 0.3) return true;
    const kpName = ANGLE_KEY_TO_KEYPOINT[jointKey];
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
              : `${name ? `${name} · ` : ''}분석이 완료됐어요. 점수를 확인해보세요.`}
          </Text>
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
          </View>
        )}

        {/* ── Phase 12 Wave 1 (Plan 12-02 T4) — 영역 1: 점수 게이지 ─────── */}
        <View style={styles.card}>
          <OctagonScore score={result.overallScore} size={168} />
          <View style={styles.gradeRow}>
            <Text style={styles.gradeBadge}>{grade}</Text>
            <Text style={styles.summary}>{summary}</Text>
          </View>
          <LevelBenchmark score={result.overallScore} />
          {/* 260612-t9m: 점수 안내 캡션 — stability tol 25° 보정과 함께 "90+ 정상" 사용자 인지 정합 */}
          <Text style={styles.scoreCaption}>
            촬영 노이즈와 측정 허용 범위가 있어 100점은 잘 나오지 않아요. 90점 이상이면 정상 자세에 가깝습니다.
          </Text>
        </View>

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
              leftLabel="내 영상"
              rightLabel={
                cmp.mode === 'mode1' ? `${cmp.athleteName} 선수` : '지난 분석'
              }
              leftUrl={result.myVideoUrl || undefined}
              rightUrl={
                cmp.mode === 'mode1'
                  ? result.referenceVideoUrl || refMotion?.videoUrl || undefined
                  : freshPrevUrl || prevDoc?.result?.myVideoUrl || undefined
              }
              leftOverlay={(player) => (
                <KeypointOverlay
                  player={player}
                  keypointReport={userKeypointReport}
                  videoSize={overlayVideoSize}
                  visible={overlayVisible}
                  jointAngles={userJointAngles}
                />
              )}
              rightOverlay={(player) =>
                cmp.mode === 'mode1' ? (
                  <KeypointOverlay
                    player={player}
                    keypointReport={referenceKeypointReport}
                    videoSize={overlayVideoSize}
                    visible={overlayVisible}
                  />
                ) : null
              }
            />
          </>
        )}

        {/* ── Phase 4 (04-02 Task 4) — Stage 3 사용자 3D 자세 뷰어 ─────────
            joints3d null = Phase 4 이전 doc / joints3d 없는 분석 → 섹션 자체
            graceful 생략 (UI-SPEC §Surface 1 상태별 UI). reshapePose3dData 가
            형식 불일치 / 누락 시 null 반환. R3 박제 — angles 절대 미사용,
            joints3d 전용. HIGH-3 박제 — referenceJoints 는 Wave 2 에서 전달 X
            (PoseViewer3D props 에 예약만 두고 follow-up plan 에서 mode1 overlay
            활성화). R8 박제 — Canvas/GL 충돌은 PoseViewer3D 내부 ErrorBoundary
            가 격리. */}
        {joints3d && (
          <PoseViewer3D
            joints={joints3d}
            currentFrame={currentFrame}
            onFrameChange={setCurrentFrame}
          />
        )}

        {/* ── 영역 3: Phase 9 실패 원인 카드 Top-3 (D-12-B1 박제) ───────────
            findings.length=0 → fallback big × 1.
            findings.length=1 → big × 1 (작은 카드 slot 비움).
            findings.length=2 → big × 1 + small × 1 (왼쪽).
            findings.length=3 → big × 1 + small × 2.
            interpretation 본문 = backend canned KO (force_pattern_copy.py).
            Phase 11 통합 시 동일 필드 LLM 풍부화 자동 교체 (D-12-B2). */}
        <Text style={styles.sectionTitle}>실패 원인 후보</Text>
        <ForcePatternCard
          finding={forcePatternFindings[0]}
          rank={0}
          variant="big"
          onTap={() => setDetailFinding(forcePatternFindings[0])}
        />
        {forcePatternFindings.length >= 2 && (
          <View style={styles.findingSmallRow}>
            <ForcePatternCard
              finding={forcePatternFindings[1]}
              rank={1}
              variant="small"
              onTap={() => setDetailFinding(forcePatternFindings[1])}
            />
            {forcePatternFindings.length >= 3 ? (
              <ForcePatternCard
                finding={forcePatternFindings[2]}
                rank={2}
                variant="small"
                onTap={() => setDetailFinding(forcePatternFindings[2])}
              />
            ) : (
              <View style={styles.findingSmallSpacer} />
            )}
          </View>
        )}

        {/* ── 영역 4: 콤보 부분 점수 (mode1 콤보 모션 분석 시에만) ───────── */}
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

        {/* ── 영역 5: 차원 점수 (Phase 12.5 + Wave 2 ⚠ amber occlusion badge) ─
            영상 reliability=='low' frame 비율 ≥ 20% → 카드 상단 우측 ⚠ amber
            badge 노출 (D-12-D2). 카드 tap 시 DimensionDetailModal 안 occlusion
            한 줄 동행. */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>세부 점수</Text>
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
          {dims.map((dim) => (
            <DimensionScoreRow
              key={dim}
              dim={dim}
              score={dimensionScores[dim] as number}
              delta={deltaFor(dim)}
              explanation={dimensionExplanation?.[dim]}
              onDetailPress={(d) => setDetailDim(d)}
            />
          ))}
        </View>

        {/* ── 영역 6: 각도 가이드 (코칭 팁) — Phase 12.5 + Wave 2 추정 표기 ─
            joint 평균 confidence < 0.5 또는 low reliability frame 비율 ≥ 30%
            → "추정 N°" + estimateGray + ⓘ tap → Alert (D-12-D1 박제). */}
        <Text style={styles.sectionTitle}>코칭 팁</Text>
        {result.tips.map((tip, i) => {
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
        onClose={() => setDetailDim(null)}
      />
      {/* Phase 12.5 T9: 코칭 팁 "자세히 ›" 모달. tip=null 시 닫힘. */}
      <CoachingTipDetailModal
        visible={detailTip != null}
        tip={detailTip}
        onClose={() => setDetailTip(null)}
      />
      {/* Phase 12 Wave 1 (Plan 12-02 T4): Phase 9 finding 자세히 모달.
          ForcePatternCard tap → setDetailFinding(finding). null 시 닫힘. */}
      <ForcePatternDetailModal
        visible={detailFinding != null}
        finding={detailFinding}
        rank={
          detailFinding != null
            ? forcePatternFindings.findIndex((f) => f === detailFinding)
            : undefined
        }
        onClose={() => setDetailFinding(null)}
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
  bench: {
    width: '100%',
    marginTop: 14,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
    gap: 8,
  },
  benchChips: { flexDirection: 'row', gap: 6 },
  benchChip: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 6,
    borderRadius: radius.listItem,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    backgroundColor: colors.bg,
    alignItems: 'center',
    gap: 2,
  },
  benchChipActive: { backgroundColor: colors.brand, borderColor: colors.brand },
  benchChipLabel: { ...typography.captionSmall, color: colors.textSecondary },
  benchChipLabelActive: { color: colors.textWhite },
  benchChipScore: { ...typography.boxLabel, color: colors.textPrimary },
  benchChipScoreActive: { color: colors.textWhite },
  benchSummary: {
    ...typography.caption,
    color: colors.textSecondary,
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
  segmentHintText: {
    ...typography.caption,
    color: colors.textSecondary,
    alignSelf: 'flex-start',
    lineHeight: 18,
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
  // 차원별 deficit summary (측정값/진단). 수치는 highlightNumbers 로 강조.
  dimDeficit: {
    ...typography.caption,
    color: colors.textPrimary,
    marginTop: 2,
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
  // Phase 12 Wave 1 (Plan 12-02 T4) — Phase 9 finding 작은 카드 row.
  // 두 개 가로 정렬 (gap 8). 단일 small 카드인 경우 오른쪽 spacer 로 균형.
  findingSmallRow: {
    flexDirection: 'row',
    gap: 8,
  },
  findingSmallSpacer: { flex: 1 },
  tipCard: { alignItems: 'flex-start', gap: 8 },
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
});
