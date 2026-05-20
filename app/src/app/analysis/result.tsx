import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useMemo } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { ScoreGauge, scoreGrade } from '../../components/ScoreGauge';
import {
  LEVEL_EXPECTED_SCORE,
  LEVEL_LABEL_KO,
  levelStanding,
} from '../../lib/levels';
import { useReferenceMotion } from '../../lib/referenceMotions';
import { getSimulatedResult } from '../../lib/simulatedResult';
import { useAnalysisDoc } from '../../lib/userAnalyses';
import type {
  AnalysisMode,
  AnalysisResult,
  BodyPart,
  JointDirection,
  JointScore,
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

// 분석 결과 화면 (plan.md #8, design.md §8, ia AC-RES-001).
// 미설계 화면 → design.md §0 결정 트리로 자체 설계. 흰 배경(§5-1),
// 브랜드 포인트(#FF4B33), 스피너/이모지 없음, 토큰만 사용.
// 데이터는 시뮬레이션(getSimulatedResult) — 백엔드 연결 시 동일 타입으로 교체.

const PARTS: BodyPart[] = ['상체', '코어', '하체'];

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

function PartScoreRow({
  part,
  score,
  delta,
}: {
  part: BodyPart;
  score: number;
  delta?: number;
}) {
  return (
    <View style={styles.partRow}>
      <View style={styles.partHead}>
        <Text style={styles.partLabel}>{part}</Text>
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
  // analysisId 가 있으면 Firestore 저장값을 권위 있는 소스로 사용 (홈/기록에서
  // 들어왔거나, 시뮬이 저장 완료된 경우). 없으면 시뮬 폴백(deep link 등).
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

  // ia AC-RES-001-2: 틀린 관절 하이라이트 — issue 있는 관절 중 최저점
  const worstJoint = useMemo(
    () =>
      result.joints
        .filter((j) => j.issue)
        .sort((a, b) => a.score - b.score)[0],
    [result.joints],
  );

  const summary =
    cmp.mode === 'mode1'
      ? mode1Summary(cmp.athleteName, cmp.similarity)
      : cmp.isFirst
        ? '첫 분석이에요. 다음 분석부터 성장을 비교해드려요.'
        : '지난 분석과 파트별로 비교했어요.';

  const deltaFor = (part: BodyPart): number | undefined =>
    cmp.mode === 'mode3' && !cmp.isFirst
      ? cmp.deltaFromPrevious?.[part]
      : undefined;

  const rightLabel =
    cmp.mode === 'mode1' ? `${cmp.athleteName} 기준` : '지난 분석';

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
          <ScoreGauge score={result.overallScore} />
          <View style={styles.gradeRow}>
            <Text style={styles.gradeBadge}>{grade}</Text>
            <Text style={styles.summary}>{summary}</Text>
          </View>
          <LevelBenchmark score={result.overallScore} />
        </View>

        {/* 세부 점수 (AC-RES-001-4) */}
        <Text style={styles.sectionTitle}>세부 점수</Text>
        <View style={styles.card}>
          {PARTS.map((part) => (
            <PartScoreRow
              key={part}
              part={part}
              score={result.partScores[part]}
              delta={deltaFor(part)}
            />
          ))}
        </View>

        {/* 동작 비교 (AC-RES-001-2) */}
        <Text style={styles.sectionTitle}>동작 비교</Text>
        <View style={styles.card}>
          <View style={styles.compareRow}>
            <View style={styles.compareCol}>
              <View style={styles.videoBox}>
                <Ionicons
                  name="play-circle-outline"
                  size={36}
                  color={colors.textDisabled}
                />
              </View>
              <Text style={styles.compareLabel}>내 동작</Text>
            </View>
            <View style={styles.compareCol}>
              <View style={styles.videoBox}>
                <Ionicons
                  name="play-circle-outline"
                  size={36}
                  color={colors.textDisabled}
                />
              </View>
              <Text style={styles.compareLabel}>{rightLabel}</Text>
            </View>
          </View>
          {worstJoint && (
            <View style={styles.highlightBlock}>
              <View style={styles.highlight}>
                <Ionicons name="alert-circle" size={16} color={colors.brand} />
                <Text style={styles.highlightText}>
                  {worstJoint.labelKo} {worstJoint.issue}
                </Text>
              </View>
              {(() => {
                const g = angleGuide(worstJoint);
                if (!g) return null;
                return (
                  <Text style={styles.highlightAngle}>
                    {g.line}
                    {g.cue ? `  ·  ${g.cue}` : ''}
                  </Text>
                );
              })()}
            </View>
          )}
          <Text style={styles.note}>
            영상 나란히 보기는 분석 서버 연결 후 표시돼요.
          </Text>
        </View>

        {/* 코칭 팁 (AC-RES-001-3) */}
        <Text style={styles.sectionTitle}>코칭 팁</Text>
        {result.tips.map((tip, i) => {
          const joint = tip.joint
            ? result.joints.find((j) => j.key === tip.joint)
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
                  <Text style={styles.tipAngle}>{guide.line}</Text>
                  {guide.cue && (
                    <Text style={styles.tipAngleCue}>{guide.cue}</Text>
                  )}
                </View>
              )}
              <Text style={styles.tipDetail}>{tip.detail}</Text>
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
  compareRow: { flexDirection: 'row', gap: 12, width: '100%' },
  compareCol: { flex: 1, alignItems: 'center', gap: 8 },
  videoBox: {
    width: '100%',
    aspectRatio: 9 / 16, // 폴스포츠 세로 영상 (design.md §10)
    borderRadius: radius.listItem,
    backgroundColor: '#FFF0EE', // homeCard 하단 톤 (라이트, 다크 금지)
    alignItems: 'center',
    justifyContent: 'center',
  },
  compareLabel: { ...typography.caption, color: colors.textSecondary },
  highlightBlock: {
    marginTop: 14,
    alignSelf: 'stretch',
    gap: 4,
  },
  highlight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'flex-start',
  },
  highlightText: {
    ...typography.caption,
    color: colors.textPrimary,
    flexShrink: 1,
  },
  highlightAngle: {
    ...typography.captionSmall,
    color: colors.brand,
    marginLeft: 22, // alert-circle 아이콘 들여쓰기와 정렬
  },
  note: {
    ...typography.captionSmall,
    color: colors.textSecondary,
    marginTop: 10,
    alignSelf: 'flex-start',
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
