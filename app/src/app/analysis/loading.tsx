import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { type ReactNode, useEffect, useRef, useState } from 'react';
import {
  Animated,
  Easing,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import Svg, { Defs, LinearGradient as SvgGradient, Path, Stop } from 'react-native-svg';
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

// AI 분석 로딩 (plan.md #5, design.md §5-9·§10, Figma 1:429/436/445).
// 라이트 테마 단독 예외 — 다크 네이비. 분석 중: 글로우 그라디언트 링(안에 텍스트)
// + 링 아래 단계 한 줄. 오류/완료: 하단 웨이브 그라디언트(오류 분홍/완료 민트).

const NAVY_TOP = '#13152B';
const NAVY_BOT = '#1E2348';
const RING_C1 = '#3FD8C8'; // 청록
const RING_C2 = '#5C7CFA'; // 파랑
const RING_C3 = '#A77BF3'; // 보라
const ERROR_RED = '#FF5A6A';
const DONE_TEAL = '#3FD8AE';
const TEXT_DIM = 'rgba(255,255,255,0.55)';

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

// 둘레가 살짝 울퉁한 닫힌 곡선(블롭). Catmull-Rom → cubic bezier 로 부드럽게.
function blobPath(r: number, variations: number[]): string {
  const n = variations.length;
  const pts = variations.map((v, i) => {
    const a = (i / n) * Math.PI * 2 - Math.PI / 2;
    const rad = r + v;
    return [50 + rad * Math.cos(a), 50 + rad * Math.sin(a)] as const;
  });
  let d = `M ${pts[0][0].toFixed(2)},${pts[0][1].toFixed(2)} `;
  for (let i = 0; i < n; i++) {
    const p0 = pts[(i - 1 + n) % n];
    const p1 = pts[i];
    const p2 = pts[(i + 1) % n];
    const p3 = pts[(i + 2) % n];
    const c1x = p1[0] + (p2[0] - p0[0]) / 6;
    const c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6;
    const c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += `C ${c1x.toFixed(2)},${c1y.toFixed(2)} ${c2x.toFixed(2)},${c2y.toFixed(2)} ${p2[0].toFixed(2)},${p2[1].toFixed(2)} `;
  }
  return `${d}Z`;
}

// 8점 + 작은 변형(±2.5) — 거의 원에 가깝게, 텍스트를 가리지 않게 r 도 키움.
const BLOB_A = blobPath(43, [2.5, 1.8, 0, -1.8, -2.5, -1.8, 0, 1.8]);
const BLOB_B = blobPath(43, [0, -1.8, -2.5, -1.8, 0, 1.8, 2.5, 1.8]);

// 액체/블롭 일렁이는 링 — 살짝 찌그러진 블롭 2겹을 다른 속도·방향으로 회전.
// 겹친 윤곽이 출렁이는 느낌(단순 스피너와 다름 — 형태 일렁임). 안에 children.
function BlobRing({ children }: { children: ReactNode }) {
  const spinA = useRef(new Animated.Value(0)).current;
  const spinB = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const a = Animated.loop(
      Animated.timing(spinA, {
        toValue: 1,
        duration: 7000,
        easing: Easing.linear,
        useNativeDriver: true,
      }),
    );
    const b = Animated.loop(
      Animated.timing(spinB, {
        toValue: 1,
        duration: 9500,
        easing: Easing.linear,
        useNativeDriver: true,
      }),
    );
    a.start();
    b.start();
    return () => {
      a.stop();
      b.stop();
    };
  }, [spinA, spinB]);
  const rotA = spinA.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });
  const rotB = spinB.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '-360deg'],
  });
  return (
    <View style={styles.ringWrap}>
      <Animated.View style={[styles.ringLayer, { transform: [{ rotate: rotA }] }]}>
        <Svg width={264} height={264} viewBox="0 0 100 100">
          <Defs>
            <SvgGradient id="blobGrad" x1="0" y1="1" x2="1" y2="0">
              <Stop offset="0" stopColor={RING_C1} />
              <Stop offset="0.5" stopColor={RING_C2} />
              <Stop offset="1" stopColor={RING_C3} />
            </SvgGradient>
          </Defs>
          <Path d={BLOB_A} stroke="url(#blobGrad)" strokeWidth={6} fill="none" />
        </Svg>
      </Animated.View>
      <Animated.View style={[styles.ringLayer, { transform: [{ rotate: rotB }] }]}>
        <Svg width={264} height={264} viewBox="0 0 100 100">
          <Path
            d={BLOB_B}
            stroke={RING_C2}
            strokeWidth={5}
            fill="none"
            opacity={0.4}
          />
        </Svg>
      </Animated.View>
      <View style={styles.ringContent}>{children}</View>
    </View>
  );
}

// 하단 웨이브 그라디언트 — 오류=분홍, 완료=민트 (Figma).
function WaveBackground({ tint }: { tint: string }) {
  return (
    <View style={styles.waveWrap} pointerEvents="none">
      <Svg
        width="100%"
        height="100%"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
      >
        <Path
          d="M0,40 Q26,26 52,38 T100,34 L100,100 L0,100 Z"
          fill={tint}
          fillOpacity={0.16}
        />
        <Path
          d="M0,58 Q30,44 58,56 T100,52 L100,100 L0,100 Z"
          fill={tint}
          fillOpacity={0.3}
        />
        <Path
          d="M0,76 Q28,64 56,74 T100,72 L100,100 L0,100 Z"
          fill={tint}
          fillOpacity={0.5}
        />
      </Svg>
    </View>
  );
}

export default function AnalysisLoading() {
  const router = useRouter();
  const { mode, name, analysisId, referenceMotionId, referenceMotionName } =
    useLocalSearchParams<{
      mode?: string;
      name?: string;
      analysisId?: string;
      referenceMotionId?: string;
      referenceMotionName?: string;
    }>();
  const { status, errorCode } = useSimulatedAnalysis();

  const failed = status === 'failed' || errorCode != null;
  const done = status === 'done';

  // 시뮬 종료 시 Firestore done 문서 저장 → 저장 끝나면 결과 화면 자동 전환
  // (Figma 완료 화면: "잠시만 기다려주세요"). 백엔드 붙으면 simulationWriter 폐기.
  const savingRef = useRef(false);
  useEffect(() => {
    if (!done || savingRef.current) return;
    savingRef.current = true;
    const analysisMode: AnalysisMode = mode === 'mode1' ? 'mode1' : 'mode3';
    let savedId: string | null = null;
    saveSimulatedAnalysis({
      mode: analysisMode,
      fileName: typeof name === 'string' ? name : '',
      referenceMotionId,
      referenceMotionName,
    })
      .then((id) => {
        savedId = id;
      })
      .catch((e) => {
        if (__DEV__) console.warn('[loading] saveSimulatedAnalysis failed', e);
      })
      .finally(() => {
        // 완료 화면을 잠깐 보여준 뒤 결과로 (저장 시간 + 최소 노출).
        setTimeout(() => {
          router.replace({
            pathname: '/analysis/result',
            params: {
              mode: mode ?? 'mode3',
              name,
              analysisId: savedId ?? analysisId,
              referenceMotionId,
              referenceMotionName,
            },
          });
        }, 900);
      });
  }, [done, mode, name, analysisId, referenceMotionId, referenceMotionName, router]);

  if (failed) {
    const code: AnalysisErrorCode = errorCode ?? 'server_error';
    const isNoHuman = code === 'no_human';
    return (
      <LinearGradient colors={[NAVY_TOP, NAVY_BOT]} style={styles.container}>
        <StatusBar style="light" />
        <WaveBackground tint="#E8657F" />
        <Pressable style={styles.inquiry} accessibilityRole="link" hitSlop={8}>
          <Text style={styles.inquiryText}>문의하기</Text>
        </Pressable>
        <View style={styles.center}>
          <View style={[styles.statusRing, { borderColor: ERROR_RED }]}>
            <Ionicons name="close" size={36} color={ERROR_RED} />
          </View>
          <Text style={styles.title}>
            {isNoHuman ? '사람을 찾지 못했어요' : '분석 중 문제가 발생했어요'}
          </Text>
          <Text style={styles.sub}>{ERROR_MESSAGE[code]}</Text>
          {isNoHuman && (
            <View style={styles.tipCard}>
              <View style={styles.tipHeadRow}>
                <Ionicons name="alert-circle" size={16} color={ERROR_RED} />
                <Text style={styles.tipHead}>촬영 TIP!</Text>
              </View>
              <Text style={styles.tipItem}>· 측면 45°, 2~3m 거리</Text>
              <Text style={styles.tipItem}>· 밝은 환경, 폴 전체로 보이게</Text>
              <Text style={styles.tipItem}>· 3초 이상, 동작 전체 포함</Text>
            </View>
          )}
        </View>
        <Pressable
          style={styles.cta}
          onPress={() => router.back()}
          accessibilityRole="button"
        >
          <Text style={styles.ctaText}>다시 분석하기</Text>
        </Pressable>
      </LinearGradient>
    );
  }

  if (done) {
    return (
      <LinearGradient colors={[NAVY_TOP, NAVY_BOT]} style={styles.container}>
        <StatusBar style="light" />
        <WaveBackground tint={DONE_TEAL} />
        <View style={styles.center}>
          <View style={[styles.statusRing, { borderColor: DONE_TEAL }]}>
            <Ionicons name="checkmark" size={36} color={DONE_TEAL} />
          </View>
          <Text style={styles.title}>{STATUS_MESSAGE.done}</Text>
          <Text style={styles.sub}>분석 결과를 준비하고 있어요.{'\n'}잠시만 기다려주세요.</Text>
        </View>
      </LinearGradient>
    );
  }

  const titleLine =
    mode === 'mode1'
      ? '전문가 동작과 내 포즈를\n분석하고 있어요.'
      : '내 포즈를\n분석하고 있어요.';

  return (
    <LinearGradient colors={[NAVY_TOP, NAVY_BOT]} style={styles.container}>
      <StatusBar style="light" />
      <View style={styles.center}>
        <BlobRing>
          <Text style={styles.ringTitle}>{titleLine}</Text>
          <Text style={styles.ringSub}>화면을 닫지 마세요.</Text>
        </BlobRing>
        <Text style={styles.stepLine}>{STATUS_MESSAGE[status]}</Text>
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: layout.safeAreaTop,
    paddingHorizontal: spacing.screenX,
    paddingBottom: layout.safeAreaBottom + 24,
  },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  // 분석 중 — 글로우 링
  ringWrap: {
    width: 264,
    height: 264,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ringLayer: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ringContent: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 44,
    gap: 10,
  },
  ringTitle: {
    ...typography.listTitle,
    color: '#FFFFFF',
    textAlign: 'center',
    lineHeight: 24,
  },
  ringSub: { ...typography.caption, color: TEXT_DIM, textAlign: 'center' },
  stepLine: {
    ...typography.caption,
    color: TEXT_DIM,
    marginTop: 44,
    textAlign: 'center',
  },
  // 오류/완료 공통
  title: {
    ...typography.heading,
    color: '#FFFFFF',
    textAlign: 'center',
    marginTop: 20,
  },
  sub: {
    ...typography.caption,
    color: TEXT_DIM,
    marginTop: 10,
    textAlign: 'center',
    lineHeight: 19,
  },
  statusRing: {
    width: 84,
    height: 84,
    borderRadius: 42,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  inquiry: { alignSelf: 'flex-end', marginTop: 4, padding: 4 },
  inquiryText: { ...typography.caption, color: TEXT_DIM },
  tipCard: {
    marginTop: 22,
    backgroundColor: 'rgba(0,0,0,0.35)',
    borderRadius: radius.card,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
    paddingVertical: 14,
    paddingHorizontal: 18,
    gap: 6,
    alignSelf: 'stretch',
  },
  tipHeadRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 2 },
  tipHead: { ...typography.boxLabel, color: '#FFFFFF' },
  tipItem: { ...typography.caption, color: 'rgba(255,255,255,0.78)' },
  waveWrap: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: '46%',
  },
  cta: {
    height: layout.ctaHeight,
    borderRadius: radius.button,
    backgroundColor: 'rgba(255,255,255,0.14)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.22)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaText: { ...typography.button, color: '#FFFFFF' },
});
