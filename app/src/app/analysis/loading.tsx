import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Animated, Pressable, StyleSheet, Text, View } from 'react-native';
import {
  type AnalysisErrorCode,
  type AnalysisStatus,
  ERROR_MESSAGE,
  PROGRESS_SEQUENCE,
  STATUS_MESSAGE,
} from '../../types/analysis';
import { colors, layout, radius, spacing, typography } from '../../theme';

// AI 분석 로딩 (plan.md #5, design.md §5-9·§6·§9).
// 계약(docs/contract.md) 기준: status 로 구동 → 백엔드 붙으면 시뮬레이터만
// users/{uid}/analyses/{analysisId} onSnapshot 구독으로 교체 (재작업 없음).
// 스피너 금지(§0): 단계별 메시지 + 브랜드 톤 펄스.

// design.md §5-9 표시 단계 (uploading/queued 는 준비 중으로 묶고 핵심 3단계 노출)
const STEPS: { status: AnalysisStatus; label: string }[] = [
  { status: 'frame_extraction', label: STATUS_MESSAGE.frame_extraction },
  { status: 'pose_analysis', label: STATUS_MESSAGE.pose_analysis },
  { status: 'comparison', label: STATUS_MESSAGE.comparison },
];

// TODO(#6~7): 백엔드 연결 시 이 훅을 Firestore onSnapshot 구독으로 교체.
// 계약상 입력은 analysisId, 출력은 { status, errorCode } 로 동일하게 유지할 것.
function useSimulatedAnalysis(): {
  status: AnalysisStatus;
  errorCode: AnalysisErrorCode | null;
} {
  const [status, setStatus] = useState<AnalysisStatus>('queued');
  useEffect(() => {
    const order = PROGRESS_SEQUENCE.filter((s) => s !== 'uploading');
    let i = 0;
    const timer = setInterval(() => {
      i += 1;
      if (i >= order.length) {
        clearInterval(timer);
        setStatus('done');
        return;
      }
      setStatus(order[i]);
    }, 1300);
    return () => clearInterval(timer);
  }, []);
  return { status, errorCode: null };
}

function PulseDot() {
  const v = useRef(new Animated.Value(0.3)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(v, { toValue: 1, duration: 600, useNativeDriver: true }),
        Animated.timing(v, { toValue: 0.3, duration: 600, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [v]);
  return <Animated.View style={[styles.dot, { opacity: v }]} />;
}

export default function AnalysisLoading() {
  const router = useRouter();
  const { mode, name, analysisId } = useLocalSearchParams<{
    mode?: string;
    name?: string;
    analysisId?: string;
  }>();
  const { status, errorCode } = useSimulatedAnalysis();

  const failed = status === 'failed' || errorCode != null;
  const done = status === 'done';
  const currentIndex = PROGRESS_SEQUENCE.indexOf(status);

  if (failed) {
    const code: AnalysisErrorCode = errorCode ?? 'server_error';
    return (
      <View style={styles.container}>
        <View style={styles.center}>
          <Ionicons name="alert-circle-outline" size={56} color={colors.inputError} />
          <Text style={styles.title}>분석에 실패했어요</Text>
          <Text style={styles.sub}>{ERROR_MESSAGE[code]}</Text>
        </View>
        <Pressable
          style={styles.cta}
          onPress={() => router.back()}
          accessibilityRole="button"
        >
          <Text style={styles.ctaText}>다시 시도</Text>
        </Pressable>
      </View>
    );
  }

  if (done) {
    return (
      <View style={styles.container}>
        <View style={styles.center}>
          <Ionicons name="checkmark-circle" size={64} color={colors.brand} />
          <Text style={styles.title}>{STATUS_MESSAGE.done}</Text>
          <Text style={styles.sub}>분석 결과를 확인할 수 있어요.</Text>
        </View>
        <Pressable
          style={styles.cta}
          onPress={() =>
            router.replace({
              pathname: '/analysis/result',
              params: { mode: mode ?? 'mode3', name, analysisId },
            })
          }
          accessibilityRole="button"
        >
          <Text style={styles.ctaText}>결과 보기</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>AI가 분석하고 있어요</Text>
        <Text style={styles.sub}>
          {name ? `${name} · ` : ''}보통 30~60초 정도 걸려요.
        </Text>
      </View>

      <View style={styles.steps}>
        {STEPS.map((step) => {
          const stepIndex = PROGRESS_SEQUENCE.indexOf(step.status);
          const stepDone = currentIndex > stepIndex;
          const active = currentIndex === stepIndex;
          return (
            <View key={step.status} style={styles.stepRow}>
              {stepDone ? (
                <Ionicons name="checkmark-circle" size={22} color={colors.brand} />
              ) : active ? (
                <PulseDot />
              ) : (
                <View style={styles.dotPending} />
              )}
              <Text
                style={[
                  styles.stepLabel,
                  stepDone && styles.stepLabelDone,
                  active && styles.stepLabelActive,
                ]}
              >
                {step.label}
              </Text>
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg, // 서브 화면 = 흰 배경 (§5-1)
    paddingTop: layout.safeAreaTop,
    paddingHorizontal: spacing.screenX,
    paddingBottom: layout.safeAreaBottom + 24,
  },
  header: { marginTop: 24 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  title: { ...typography.heading, color: colors.textPrimary },
  sub: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 8,
    textAlign: 'center',
  },
  steps: { marginTop: 48, gap: 22 },
  stepRow: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  dot: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.brand,
  },
  dotPending: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: colors.divider,
  },
  stepLabel: { ...typography.listTitle, color: colors.textDisabled },
  stepLabelActive: { color: colors.brand },
  stepLabelDone: { color: colors.textPrimary },
  cta: {
    height: layout.ctaHeight,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaText: { ...typography.button, color: colors.textWhite },
});
