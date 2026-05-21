import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  Animated,
  Easing,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import Svg, { Circle, Defs, LinearGradient, Stop } from 'react-native-svg';
import { StatusBar } from 'expo-status-bar';
import { saveSimulatedAnalysis } from '../../lib/simulationWriter';
import {
  type AnalysisErrorCode,
  type AnalysisMode,
  type AnalysisStatus,
  ERROR_MESSAGE,
  PROGRESS_SEQUENCE,
  STATUS_MESSAGE,
} from '../../types/analysis';
import { layout, radius, spacing, typography } from '../../theme';

// AI 분석 로딩 (plan.md #5, design.md §5-9·§10).
// design.md §10: 이 화면만 다크 네이비 + 파랑→보라 그라디언트 링 (라이트 테마 단독 예외).
// 스피너 금지(§0) — 그라디언트 링은 장식, 단계별 메시지가 실제 진행 정보.
// status 구동 → 백엔드 붙으면 useSimulatedAnalysis 만 onSnapshot 으로 교체(계약 동일).

// 다크 로딩 화면 전용 색 (단독 예외 화면이라 theme 토큰 대신 로컬 상수).
const NAVY_BG = '#161A33';
const RING_FROM = '#5C7CFA';
const RING_TO = '#A77BF3';
const BRAND = '#FF4B33';
const ERROR = '#FF5A5A';
const TEXT_DIM = 'rgba(255,255,255,0.55)';
const TRACK_DIM = 'rgba(255,255,255,0.10)';

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

// 파랑→보라 그라디언트 링 — 천천히 회전(장식). design.md §10.
function GradientRing() {
  const spin = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.timing(spin, {
        toValue: 1,
        duration: 1800,
        easing: Easing.linear,
        useNativeDriver: true,
      }),
    );
    loop.start();
    return () => loop.stop();
  }, [spin]);
  const rotate = spin.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });
  const C = 2 * Math.PI * 42;
  return (
    <Animated.View style={{ transform: [{ rotate }] }}>
      <Svg width={132} height={132} viewBox="0 0 100 100">
        <Defs>
          <LinearGradient id="loadingRing" x1="0" y1="0" x2="1" y2="1">
            <Stop offset="0" stopColor={RING_FROM} />
            <Stop offset="1" stopColor={RING_TO} />
          </LinearGradient>
        </Defs>
        <Circle
          cx={50}
          cy={50}
          r={42}
          stroke={TRACK_DIM}
          strokeWidth={6}
          fill="none"
        />
        <Circle
          cx={50}
          cy={50}
          r={42}
          stroke="url(#loadingRing)"
          strokeWidth={6}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={`${C * 0.68} ${C}`}
        />
      </Svg>
    </Animated.View>
  );
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
  const { mode, name, analysisId, referenceMotionId, referenceMotionName } =
    useLocalSearchParams<{
      mode?: string;
      name?: string;
      analysisId?: string;
      // mode1 진입 시 기준 모션 ID (plan.md #9). 실제 활용은 #7-follow
      // (POST /upload-url 호출 시 본문에 포함). 지금은 받기만 + 결과로 전달.
      referenceMotionId?: string;
      referenceMotionName?: string;
    }>();
  const { status, errorCode } = useSimulatedAnalysis();

  const failed = status === 'failed' || errorCode != null;
  const done = status === 'done';
  const currentIndex = PROGRESS_SEQUENCE.indexOf(status);

  // 시뮬 종료 시 Firestore 에 done 문서 1건 저장 → 홈/기록 탭이 즉시 반영.
  // 백엔드 실 파이프라인 켜지면 lib/simulationWriter 와 함께 제거(스캐폴드).
  const savedAnalysisIdRef = useRef<string | null>(null);
  const savingRef = useRef(false);
  useEffect(() => {
    if (!done || savingRef.current) return;
    savingRef.current = true;
    const analysisMode: AnalysisMode = mode === 'mode1' ? 'mode1' : 'mode3';
    saveSimulatedAnalysis({
      mode: analysisMode,
      fileName: typeof name === 'string' ? name : '',
      referenceMotionId,
      referenceMotionName,
    })
      .then((id) => {
        if (id) savedAnalysisIdRef.current = id;
      })
      .catch((e) => {
        if (__DEV__) console.warn('[loading] saveSimulatedAnalysis failed', e);
      });
  }, [done, mode, name, referenceMotionId, referenceMotionName]);

  if (failed) {
    const code: AnalysisErrorCode = errorCode ?? 'server_error';
    return (
      <View style={styles.container}>
        <StatusBar style="light" />
        <View style={styles.center}>
          <Ionicons name="alert-circle-outline" size={56} color={ERROR} />
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
        <StatusBar style="light" />
        <View style={styles.center}>
          <Ionicons name="checkmark-circle" size={64} color={RING_FROM} />
          <Text style={styles.title}>{STATUS_MESSAGE.done}</Text>
          <Text style={styles.sub}>분석 결과를 확인할 수 있어요.</Text>
        </View>
        <Pressable
          style={styles.cta}
          onPress={() =>
            router.replace({
              pathname: '/analysis/result',
              params: {
                mode: mode ?? 'mode3',
                name,
                // 저장이 끝났으면 새 analysisId 사용, 아직이면 호출시 들어온 값 폴백.
                analysisId: savedAnalysisIdRef.current ?? analysisId,
                referenceMotionId,
                referenceMotionName,
              },
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
      <StatusBar style="light" />
      <View style={styles.header}>
        <Text style={styles.title}>AI가 분석하고 있어요</Text>
        <Text style={styles.sub}>
          {name ? `${name} · ` : ''}보통 30~60초 정도 걸려요.
        </Text>
      </View>

      <View style={styles.ringWrap}>
        <GradientRing />
      </View>

      <View style={styles.steps}>
        {STEPS.map((step) => {
          const stepIndex = PROGRESS_SEQUENCE.indexOf(step.status);
          const stepDone = currentIndex > stepIndex;
          const active = currentIndex === stepIndex;
          return (
            <View key={step.status} style={styles.stepRow}>
              {stepDone ? (
                <Ionicons name="checkmark-circle" size={22} color={RING_FROM} />
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
    backgroundColor: NAVY_BG, // design.md §10 — 로딩 화면 단독 다크 예외
    paddingTop: layout.safeAreaTop,
    paddingHorizontal: spacing.screenX,
    paddingBottom: layout.safeAreaBottom + 24,
  },
  header: { marginTop: 24 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  ringWrap: { alignItems: 'center', marginTop: 56 },
  title: { ...typography.heading, color: '#FFFFFF' },
  sub: {
    ...typography.caption,
    color: TEXT_DIM,
    marginTop: 8,
    textAlign: 'center',
  },
  steps: { marginTop: 56, gap: 22 },
  stepRow: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  dot: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: RING_FROM,
  },
  dotPending: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: TRACK_DIM,
  },
  stepLabel: { ...typography.listTitle, color: TEXT_DIM },
  stepLabelActive: { color: '#FFFFFF' },
  stepLabelDone: { color: 'rgba(255,255,255,0.82)' },
  cta: {
    height: layout.ctaHeight,
    borderRadius: radius.button,
    backgroundColor: BRAND,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaText: { ...typography.button, color: '#FFFFFF' },
});
