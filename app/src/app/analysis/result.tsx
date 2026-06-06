import { useLocalSearchParams, useRouter } from 'expo-router';
import React, { useEffect, useMemo, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { OctagonScore, scoreGrade } from '../../components/OctagonScore';
import { VideoCompare } from '../../components/VideoCompare';
import {
  LEVEL_EXPECTED_SCORE,
  LEVEL_LABEL_KO,
  levelStanding,
} from '../../lib/levels';
import { useReferenceMotion } from '../../lib/referenceMotions';
import { getSimulatedResult } from '../../lib/simulatedResult';
import { useAnalysisDoc } from '../../lib/userAnalyses';
import { requestPlaybackUrl } from '../../lib/api';
import {
  DIMENSION_LABEL_KO,
  DIMENSION_ORDER,
} from '../../types/analysis';
import type {
  AnalysisMode,
  AnalysisResult,
  JointDirection,
  JointScore,
  ScoreDimension,
  SegmentScores,
  SkillLevel,
} from '../../types/analysis';
import { colors, layout, radius, spacing, typography } from '../../theme';

const REFERENCE_LEVEL_LABEL: Record<SkillLevel, string> = {
  basic: '기본기',
  intermediate: '중급',
  advanced: '고급',
};

const LEVEL_ORDER: SkillLevel[] = ['basic', 'intermediate', 'advanced'];

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
// currentAngle 은 백엔드 NLF 가 아직 채우지 못해(시뮬 픽스처) 그대로 둔다 —
// reference 쪽만 정밀해져도 "기준 168° → 154°" 등 시연 임팩트가 크다(#7-follow).
function enrichJoints(
  joints: JointScore[],
  meanAngles: Record<string, number> | undefined,
): JointScore[] {
  if (!meanAngles) return joints;
  return joints.map((j) => {
    const target = meanAngles[j.key];
    if (typeof target !== 'number' || !Number.isFinite(target)) return j;
    // currentAngle 이 있으면 실측 target 으로 delta·direction 재계산.
    // currentAngle 이 없어도 target 자체는 표시 가능 — angleGuide() 가 둘 다 요구
    // 하므로 시뮬 픽스처에서 빠진 5개 관절은 결과 화면 코칭팁에 노출 안 됨
    // (그 5개는 score 만 표시; result.tips 가 골라낸 worst 3개에 대해서만 가이드).
    if (typeof j.currentAngle === 'number' && Number.isFinite(j.currentAngle)) {
      const signed = j.currentAngle - target;
      return {
        ...j,
        targetAngle: target,
        deltaDeg: signed,
        direction: directionFor(j.key, signed) ?? j.direction,
      };
    }
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
function mode1Summary(athleteName: string, similarity: number): string {
  const head = `${athleteName} 선수와 ${similarity}% 일치해요.`;
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
}: {
  dim: ScoreDimension;
  score: number;
  delta?: number;
}) {
  return (
    <View style={styles.partRow}>
      <View style={styles.partHead}>
        <Text style={styles.partLabel}>{DIMENSION_LABEL_KO[dim]}</Text>
        <View style={styles.partValueWrap}>
          <Text style={styles.partScore}>{score}</Text>
          {delta != null && delta !== 0 && (
            <Text
              style={[
                styles.partDelta,
                { color: delta > 0 ? colors.brand : colors.inputError },
              ]}
            >
              {delta > 0 ? `+${delta}` : `${delta}`}
            </Text>
          )}
        </View>
      </View>
      <View style={styles.track}>
        <View style={[styles.trackFill, { width: `${Math.max(0, Math.min(100, score))}%` }]} />
      </View>
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

  // refMotion.meanAngles 가 있으면 시뮬 픽스처의 targetAngle 을 정은지 실측 평균
  // 으로 덮어쓴다 (예: 168° → 153.74°). 코칭팁 angleGuide 가 자동으로 정밀치 표시.
  // mode3 는 refMotion=null 이라 시뮬 그대로 — 자기 비교는 reference 없음.
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

  // 표시할 차원 = 결과에 존재하는 차원만 (mode1=4, mode3 first=3, mode3 second+=4).
  // 재설계 이전 문서(옛 partScores·dimensionScores 없음)는 빈 객체로 폴백 — 크래시 방지.
  const dimensionScores = result.dimensionScores ?? {};
  const dims = DIMENSION_ORDER.filter((d) => dimensionScores[d] != null);

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

        {/* 점수 개요 (AC-RES-001-1) + 레벨 벤치마크 */}
        <View style={styles.card}>
          <OctagonScore score={result.overallScore} size={168} />
          <View style={styles.gradeRow}>
            <Text style={styles.gradeBadge}>{grade}</Text>
            <Text style={styles.summary}>{summary}</Text>
          </View>
          <LevelBenchmark score={result.overallScore} />
        </View>

        {/* 콤보 부분 점수 — 콤보 모션 분석 시에만 (reference-motions.md §7) */}
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

        {/* 세부 점수 — IPSF 실행 차원 (각도/라인/안정성). mode3 면 발전 델타 표시 */}
        <Text style={styles.sectionTitle}>세부 점수</Text>
        <View style={styles.card}>
          {dims.map((dim) => (
            <DimensionScoreRow
              key={dim}
              dim={dim}
              score={dimensionScores[dim] as number}
              delta={deltaFor(dim)}
            />
          ))}
        </View>

        {/* 동작 비교 — 좌(내 영상) / 우(정은지 or 지난 분석). mode3 첫 분석은 비교
            대상이 없어 섹션 자체를 생략. URL 이 들어오면 자동으로 슬롯에 끼워짐. */}
        {!(cmp.mode === 'mode3' && cmp.isFirst) && (
          <>
            <Text style={styles.sectionTitle}>동작 비교</Text>
            <VideoCompare
              leftLabel="내 영상"
              rightLabel={
                cmp.mode === 'mode1' ? `${cmp.athleteName} 선수` : '지난 분석'
              }
              leftUrl={result.myVideoUrl || undefined}
              // mode1: 저장된 referenceVideoUrl 우선, 없으면 reference doc 의 videoUrl.
              // mode3 second+: freshPrevUrl (만료 시 재발급) 우선, 없으면 prev doc 의 myVideoUrl.
              rightUrl={
                cmp.mode === 'mode1'
                  ? result.referenceVideoUrl || refMotion?.videoUrl || undefined
                  : freshPrevUrl || prevDoc?.result?.myVideoUrl || undefined
              }
            />
          </>
        )}

        {/* 코칭 팁 (AC-RES-001-3) */}
        <Text style={styles.sectionTitle}>코칭 팁</Text>
        {result.tips.map((tip, i) => {
          const joint = tip.joint
            ? joints.find((j) => j.key === tip.joint)
            : undefined;
          const guide = joint ? angleGuide(joint) : null;
          return (
            <View key={tip.joint ?? i} style={[styles.card, styles.tipCard]}>
              <View style={styles.tipHead}>
                <Text style={styles.tipIndex}>{i + 1}</Text>
                <Text style={styles.tipTitle}>{tip.title}</Text>
              </View>
              {guide && (
                <View style={styles.tipAngleRow}>
                  <Text style={styles.tipAngle}>{highlightNumbers(guide.line)}</Text>
                  {guide.cue && (
                    <Text style={styles.tipAngleCue}>{guide.cue}</Text>
                  )}
                </View>
              )}
              <Text style={styles.tipDetail}>{highlightNumbers(tip.detail)}</Text>
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
  sectionTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
    marginTop: 8,
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
  partValueWrap: { flexDirection: 'row', alignItems: 'baseline', gap: 6 },
  partScore: { ...typography.listTitle, color: colors.brand },
  partDelta: { ...typography.caption },
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
  tipCard: { alignItems: 'flex-start', gap: 8 },
  tipHead: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  tipAngleRow: { flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' },
  tipAngle: { ...typography.boxLabel, color: colors.brand },
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
