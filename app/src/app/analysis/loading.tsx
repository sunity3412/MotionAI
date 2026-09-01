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
import { doc, setDoc } from 'firebase/firestore';
import { auth, db } from '../../lib/firebase';
import { requestUploadUrl, uploadToS3 } from '../../lib/api';
import { getBodyProfileOnce } from '../../lib/bodyProfile';
import { useAnalysisDoc } from '../../lib/userAnalyses';
import {
  type AnalysisErrorCode,
  type AnalysisMode,
  type AnalysisStatus,
  ERROR_MESSAGE,
  STATUS_MESSAGE,
  type VideoFormat,
} from '../../types/analysis';
import { layout, radius, spacing, typography } from '../../theme';

// AI 분석 로딩 (plan.md #5, design.md §5-9·§10, Figma 1:429/436/445).
// 라이트 테마 단독 예외 — 다크 네이비. 분석 중: 글로우 그라디언트 링(안에 텍스트)
// + 링 아래 단계 한 줄. 오류/완료: 하단 웨이브 그라디언트(오류 분홍/완료 민트).
//
// 동작:
//   ① analysisId 없이 uri 와 함께 진입 (analyze/reference 경로) — 실 업로드 흐름:
//      POST /upload-url → Firestore status='uploading' 문서 생성 → S3 PUT → 끝.
//      이후 백엔드(Lambda → RunPod)가 status 를 순차 갱신, 앱은 onSnapshot 구독.
//   ② analysisId 와 함께 진입 (samples 경로) — 업로드 없이 Firestore 만 구독.

const NAVY_TOP = '#13152B';
const NAVY_BOT = '#1E2348';
const RING_C1 = '#3FD8C8'; // 청록
const RING_C2 = '#5C7CFA'; // 파랑
const RING_C3 = '#A77BF3'; // 보라
const ERROR_RED = '#FF5A6A';
const DONE_TEAL = '#3FD8AE';
const TEXT_DIM = 'rgba(255,255,255,0.55)';

// 안심 카피 사이클 (belle P2 #10). 멈춤 인상 방지 — 분석이 흐르고 있다는 신호.
// 4초마다 다음 카피로 회전. 마지막 카피까지 가면 첫 번째로 돌아간다.
const REASSURANCE_COPIES: readonly string[] = [
  '분석 중이에요',
  '화면을 닫지 마세요',
  '조금만 기다려주세요',
] as const;
const COPY_ROTATE_MS = 4000;

// Phase 27 D-07 (v1) — 대기 중 폴스포츠 팁/동작 소개 로테이션. 피드백의 본질은
// "오래 걸리는데 아무 변화가 없다"는 체감(D-02)이라, 링 안 안심카피(REASSURANCE_COPIES)
// 와 별개로 화면 하단에서 읽을거리를 흘려 대기를 채운다. 규칙: 한국어, 이모지 금지,
// 부상·근력 단정 카피 금지(SAFE 규율 정합 — "이 동작이 근력을 키운다"류 의학/효능
// 단정 배제), 동작 소개는 학원 통용 명칭 사용. 문구는 D-07 명시 재량.
const POLE_TIPS: readonly string[] = [
  '폴 위에서는 시선을 먼저 보내면 몸이 자연스럽게 따라옵니다.',
  '천천히 내려오는 연습은 동작을 한결 안정적으로 만들어 줍니다.',
  '인버트는 거꾸로 매달리는 기본 동작으로, 여러 기술의 출발점이 됩니다.',
  '폭스탑은 폴 위에서 균형을 잡는 대표적인 자세예요.',
  '스핀 계열 동작은 회전 속도보다 라인이 곧은지가 더 중요해요.',
  '호흡을 멈추지 않고 이어가면 동작이 부드럽게 연결됩니다.',
  '그립을 바꾸는 타이밍이 동작 전체의 흐름을 결정합니다.',
  '거울보다 영상으로 확인하면 내 자세를 더 정확히 볼 수 있어요.',
  '작은 각도 차이가 자세의 차이를 만듭니다. 조금만 더 펴볼까요?',
  '오늘의 기록이 다음 분석에서 성장을 비교하는 기준이 됩니다.',
  '폴스포츠는 유연성과 리듬이 함께 어우러지는 종목이에요.',
  '분석이 끝나면 어느 부분을 더 다듬으면 좋을지 함께 짚어드릴게요.',
] as const;
// 안심카피(4000ms)와 어긋난 6000ms — 두 로테이터가 동시에 점프해 산만해 보이는
// 것을 막는다(주기를 서로소에 가깝게 두어 겹침 최소화).
const TIP_ROTATE_MS = 6000;

// 단계별 가짜 진행률 (belle P2 #9). 백엔드 status 머신 인덱스 기반.
// quick-260901-wbo — coach_dual(43.1s)+hook(~14s) 사후 분리 반영 재배분 (Phase 27
// D-02 규율 유지 — 값만 재배분, 단조 로직/creep 메커니즘 무변경). 2026-09-01 실측
// (analysis ea975e6e, timingsMs 91.7s) 에서 코칭 작성분이 빠진 뒤 기대 분포:
// frame_extraction ≈ s3_download 3.9 + frame_extract 15.0 ≈ 19s / pose_analysis ≈
// rtmw 2s / comparison ≈ scene 11.2 + veto 14.7 + 잔여 미계측 ~8 + firestore ~3 ≈
// 37~40s. 총 파이프라인 ≈ 60s — 구 실측 median 229.6s 서술(27-TIMING-BEFORE)은
// 코칭 동기 시절 값이라 폐기. comparison 이 여전히 최장 구간이지만 2분대 기어오름은
// 사라진다 — base 를 올리고 creep 을 촘촘히 해 ~38s 동안 눈에 보이게 전진.
const PROGRESS_PCT: Record<AnalysisStatus, number> = {
  uploading: 8, // 앱측 S3 PUT(백엔드 timing 밖) — 짧게.
  queued: 16, // SQS→파이프라인 대기 — 짧음.
  frame_extraction: 30, // 실측: s3_download 3.9s + frame_extract 15.0s (~19s).
  pose_analysis: 42, // 실측: rtmw ~2s — 매우 짧아 좁은 구간.
  comparison: 48, // 실측: scene+veto+잔여+firestore ≈ 37~40s — 최장 구간.
  done: 100,
  failed: 0,
};

// 각 단계 진행률 상한 — 표시값이 base 에서 이 값까지 천천히 기어오른다(멈춤 인상 방지).
// quick-260901-wbo — comparison base 48 → 상한 97 (49pt). +1/1.5s creep 로 기대
// ~38s 동안 48→~73 전진하고, 장영상 아웃라이어도 97 상한까지 계속 전진한다 —
// "comparison 142.5초 기어오름" 제거. 실제 완료(done) 전엔 100%에 닿지 않게 상한을
// 97 로 둔다(완료를 가짜로 만들지 않음 — 불변).
const PROGRESS_CEIL: Record<AnalysisStatus, number> = {
  uploading: 15,
  queued: 28,
  frame_extraction: 40,
  pose_analysis: 47,
  comparison: 97,
  done: 100,
  failed: 0,
};
// 표시값이 상한을 향해 +1 씩 오르는 간격(ms).
// quick-260901-wbo — 2500 → 1500: 총 파이프라인이 ~60s 로 줄어 creep 도 촘촘히.
const PROGRESS_CREEP_MS = 1500;

interface UploadInput {
  mode: AnalysisMode;
  fileName: string;
  uri: string;
  size: number;
  format: VideoFormat;
  referenceMotionId?: string;
  // Phase 26 (D-09) — 업로드 시점 학습활용 opt-in 동의값. 호출자가 라우트 param
  // learningOptIn === '1' 엄격 비교로 boolean 을 넘긴다 (param 유실/오염 시 false
  // 로 안전 강하 = 미동의 방향 fail-safe). 항상 boolean.
  learningOptIn: boolean;
}

// 영상 업로드 + Firestore 문서 생성. 성공 시 analysisId 리턴.
// 실패는 throw — 호출자가 화면 상태를 'failed' 로 전환.
async function startAnalysisUpload(input: UploadInput): Promise<string> {
  const uid = auth.currentUser?.uid;
  if (!uid) throw new Error('로그인이 필요합니다.');

  // 1) presigned URL + analysisId 발급
  const { analysisId, uploadUrl } = await requestUploadUrl({
    mode: input.mode,
    fileName: input.fileName,
    fileSizeBytes: input.size,
    format: input.format,
    referenceMotionId: input.referenceMotionId,
  });

  // 2) Firestore 문서 생성 (status='uploading') — 보안 규칙상 본인만 가능.
  //    이후 백엔드는 Admin SDK 로 같은 문서를 갱신한다.
  //    mode1 의 referenceMotionId 는 백엔드 pipeline 이 reference 모션을
  //    Firestore 에서 찾을 때 사용 (meta.get("referenceMotionId")). 이걸 빠뜨리면
  //    백엔드가 None 으로 받아 RuntimeError("기준 모션 또는 keyframe 데이터 없음").
  // Phase 3 (Plan 03-01, R1/R5) — 분석-당시 자가입력 프로필 SNAPSHOT.
  //   · getBodyProfileOnce() = client normalize + all-empty→null 규칙 박제.
  //     raw getDoc spread 금지 (오래된/dev-console 수정 raw 오염 차단, R5).
  //   · live cross-read 아니라 snapshot-at-creation — 이후 라이브 프로필이
  //     바뀌어도 이 분석 결과는 당시 값을 유지 (결과 화면 재현성).
  //   · null 이면 spread 안 함 (graceful + snapshot 생략). painAreas 는
  //     top-level scalar array 라 nested-array 위반 없음 (Pitfall 7).
  const bodyProfile = await getBodyProfileOnce();
  const now = Date.now();
  await setDoc(doc(db, 'users', uid, 'analyses', analysisId), {
    analysisId,
    mode: input.mode,
    status: 'uploading',
    fileName: input.fileName,
    createdAt: now,
    updatedAt: now,
    ...(input.referenceMotionId
      ? { referenceMotionId: input.referenceMotionId }
      : {}),
    ...(bodyProfile ? { bodyProfile } : {}),
    // Phase 26 (D-09) — 학습활용 opt-in 동의값을 항상 boolean 으로 기록한다
    //   (조건부 spread 아님: 부재≠false 를 없애 동의 증거를 명시적으로 남긴다).
    //   Phase 22 D-12 학습 플라이휠의 동의 근거 — Phase 22 manifest 게이트가
    //   learningOptIn===true 인 분석의 영상만 학습 후보로 삼아야 함 (게이트측
    //   필터는 Phase 22 후속 반영 필요, 현재 미집행). 3-way lockstep:
    //   types/analysis.ts + models.py + docs/contract.md §3.
    learningOptIn: input.learningOptIn,
  });

  // 3) S3 PUT — 끝나면 S3 ObjectCreated 가 SQS → Lambda → RunPod 위임을 트리거.
  //    format 을 Content-Type 헤더로 박아 S3 가 video/mp4 또는 video/quicktime
  //    으로 저장하게 한다. 안 그러면 결과 화면 expo-video 가 못 읽음(P0 #6).
  await uploadToS3(uploadUrl, input.uri, input.format);
  return analysisId;
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
  const {
    mode,
    name,
    uri,
    size,
    format,
    analysisId: presetAnalysisId,
    referenceMotionId,
    referenceMotionName,
    lowQuality,
    learningOptIn,
  } = useLocalSearchParams<{
    mode?: string;
    name?: string;
    uri?: string;
    size?: string;
    format?: string;
    analysisId?: string;
    referenceMotionId?: string;
    referenceMotionName?: string;
    // quick-260704-fwb — 저화질 경고를 승인('이대로 계속')한 업로드만 '1'.
    // not_pole_motion 실패 시 화질 우선 안내로 분기 (표시 전용, errorCode 무접촉).
    lowQuality?: string;
    // Phase 26 (D-09) — 학습활용 opt-in 동의값 ('1' | 미포함). 계약 필드와 단일
    // 네이밍 (리뷰 LOW-1). '1' 만 동의, 그 외/부재 = 미동의로 안전 강하.
    learningOptIn?: string;
  }>();

  // 분석 ID: samples 경로(이미 있음) 또는 업로드 후 발급. 발급 전엔 null.
  const [analysisId, setAnalysisId] = useState<string | null>(
    presetAnalysisId ?? null,
  );
  // 업로드 실패 등 로컬 단계 오류 — Firestore 까지 못 간 케이스용.
  const [localError, setLocalError] = useState<AnalysisErrorCode | null>(null);
  const startedRef = useRef(false);

  // 영상 업로드 흐름 (uri 가 있고 analysisId 가 아직 없을 때 한 번만).
  useEffect(() => {
    if (startedRef.current) return;
    if (analysisId) return; // samples 경로 — 업로드 스킵
    if (!uri) return; // 라우팅 사고 — 업로드할 영상 없음
    startedRef.current = true;

    const analysisMode: AnalysisMode = mode === 'mode1' ? 'mode1' : 'mode3';
    const sizeBytes = size ? parseInt(size, 10) : 0;
    const fmt: VideoFormat = format === 'mov' ? 'mov' : 'mp4';
    startAnalysisUpload({
      mode: analysisMode,
      fileName: typeof name === 'string' ? name : '',
      uri,
      size: sizeBytes,
      format: fmt,
      referenceMotionId,
      // Phase 26 (D-09) — '1' 엄격 비교로 param 유실/오염 시 false(미동의) 로 안전 강하.
      learningOptIn: learningOptIn === '1',
    })
      .then((id) => setAnalysisId(id))
      .catch((e) => {
        if (__DEV__) console.warn('[loading] upload failed', e);
        setLocalError('server_error');
      });
  }, [analysisId, uri, size, format, mode, name, referenceMotionId, learningOptIn]);

  // Firestore 분석 문서 실시간 구독 (백엔드가 상태 갱신).
  const { doc: storedDoc } = useAnalysisDoc(analysisId ?? undefined);

  // 표시할 상태: localError > Firestore doc > 업로드 전 기본.
  const status: AnalysisStatus = localError
    ? 'failed'
    : (storedDoc?.status ?? 'uploading');
  const errorCode: AnalysisErrorCode | null =
    localError ?? storedDoc?.error?.code ?? null;
  const failed = status === 'failed' || errorCode != null;
  const done = status === 'done';

  // done 도달 시 결과 화면 자동 이동 — 링 100%(700ms) → 완료 메시지 → 전환.
  useEffect(() => {
    if (!done) return;
    const t = setTimeout(() => {
      router.replace({
        pathname: '/analysis/result',
        params: {
          mode: mode ?? 'mode3',
          name,
          analysisId: analysisId ?? undefined,
          referenceMotionId,
          referenceMotionName,
        },
      });
    }, 1600);
    return () => clearTimeout(t);
  }, [done, mode, name, analysisId, referenceMotionId, referenceMotionName, router]);

  // 안심 카피 회전 (belle P2 #10) — 4초마다 인덱스 +1.
  // 모든 early return 이전에 호출돼야 React Hook 규칙(같은 순서) 유지.
  // failed/done 상태에선 링이 안 보이므로 카피 값은 안 쓰이지만 hook 자체는 호출.
  const [copyIdx, setCopyIdx] = useState(0);
  useEffect(() => {
    const t = setInterval(
      () => setCopyIdx((i) => (i + 1) % REASSURANCE_COPIES.length),
      COPY_ROTATE_MS,
    );
    return () => clearInterval(t);
  }, []);

  // Phase 27 D-07 — 폴스포츠 팁 회전 (6초마다 인덱스 +1). 안심카피와 동일하게 모든
  // early return 이전에 호출해 Hook 순서를 유지한다. 분석 중 화면에서만 렌더된다.
  const [tipIdx, setTipIdx] = useState(0);
  useEffect(() => {
    const t = setInterval(
      () => setTipIdx((i) => (i + 1) % POLE_TIPS.length),
      TIP_ROTATE_MS,
    );
    return () => clearInterval(t);
  }, []);

  // 표시 진행률 — 단계 base 로 점프한 뒤 상한까지 +1 씩 기어오른다(멈춤 인상 방지,
  // 실증 2026-07-06 "85% 에서 멈춘 줄 알고 앱 종료"). 단조 증가(Math.max)로 역행 없음.
  // done 은 100, failed/오류는 링이 안 보이므로 값 무의미. 실제 완료 전 100% 도달 금지.
  const [displayPct, setDisplayPct] = useState(0);
  useEffect(() => {
    if (failed) return;
    if (done) {
      setDisplayPct(100);
      return;
    }
    const base = PROGRESS_PCT[status] ?? 0;
    const ceil = PROGRESS_CEIL[status] ?? base;
    setDisplayPct((p) => Math.max(p, base));
    const t = setInterval(() => {
      setDisplayPct((p) => (p < ceil ? p + 1 : p));
    }, PROGRESS_CREEP_MS);
    return () => clearInterval(t);
  }, [status, done, failed]);

  // [fix 2026-07-20] 완료 시 100% 를 실제로 보여준다 — 종전엔 done 즉시 체크 화면으로
  // 갈아타 링이 중간값(실기기 55%)에서 사라져 "덜 끝났는데 넘어갔다"로 읽혔다.
  // done 후 700ms 동안 링(100%) 유지 → 체크 화면 → 결과 전환. 분석 완료의 근거는
  // 서버 status=done 이므로 이 유지 시간은 표시 전용이다.
  const [doneHeld, setDoneHeld] = useState(false);
  useEffect(() => {
    if (!done) {
      setDoneHeld(false);
      return;
    }
    const t = setTimeout(() => setDoneHeld(true), 700);
    return () => clearTimeout(t);
  }, [done]);

  if (failed) {
    const code: AnalysisErrorCode = errorCode ?? 'server_error';
    const isNoHuman = code === 'no_human';
    const isNotPole = code === 'not_pole_motion';
    // quick-260704-fwb — 저화질 경고를 승인하고 진행한 업로드가 not_pole 로 실패하면
    // "기준 동작과 너무 달라요" 대신 화질 우선 안내 (카톡 압축본 실패를 동작 문제로
    // 오해하는 것 방지). 플래그 없는 not_pole 은 기존 카피 그대로 (회귀 0).
    const isLowQualityNotPole = isNotPole && lowQuality === '1';
    // Phase 26 (D-01-ii) — 플래그 없는 not_pole 은 촬영 구도/거리 불일치가 흔한
    //   원인(A1: torso ratio 17~36배 오반려 실측). 화질 우선 분기(isLowQualityNotPole)
    //   와 배타 — 화질 승인 영상은 화질 안내가 먼저(D-07). 게이트/임계는 서버측이며
    //   불변(D-01), 여기선 안내 카피만 (백엔드 무접촉).
    const isPlainNotPole = isNotPole && !isLowQualityNotPole;
    // 32-12 (D-30 전체 실패 카피 정비) — 친숙·응원 톤 + 다음 행동 1개(하단 "다시
    // 분석하기" CTA + 분기별 확인 팁). 구조 재설계 금지 — 카피·톤만 정비한다
    // (32-CONTEXT D-30). 실패를 사용자 탓으로 돌리지 않고 "금방 된다"는 회복 톤.
    const errorTitle = isNoHuman
      ? '아직 자세를 찾지 못했어요'
      : isLowQualityNotPole
        ? '화질 때문에 분석이 어려웠어요'
        : isNotPole
          ? '기준 동작과 조금 달랐어요'
          : '잠깐 문제가 있었어요';
    const errorBody = isNoHuman
      ? '영상에서 아직 사람을 찾지 못했어요. 전신이 잘 보이게 다시 촬영하면 금방 분석할 수 있어요.'
      : isLowQualityNotPole
        ? '화질이 낮으면 자세를 정확히 읽기 어려워요. 원본 화질로 다시 올리거나 앱에서 직접 촬영하면 훨씬 잘 분석돼요.'
        : isPlainNotPole
          ? '촬영 구도나 거리가 기준 영상과 많이 다르면 이렇게 나올 수 있어요. 몸 전체가 화면에 들어오는 거리에서 정면으로 다시 찍어보면 좋아요.'
          : '분석 중 잠깐 문제가 있었어요. 잠시 후 다시 시도하면 대부분 잘 돼요.';
    return (
      <LinearGradient colors={[NAVY_TOP, NAVY_BOT]} style={styles.container}>
        <StatusBar style="light" />
        <WaveBackground tint="#E8657F" />
        <Pressable
          style={styles.inquiry}
          accessibilityRole="button"
          accessibilityLabel="문의하기"
          hitSlop={8}
          onPress={() =>
            router.push({ pathname: '/inquiry', params: { category: 'error' } })
          }
        >
          <Text style={styles.inquiryText}>문의하기</Text>
        </Pressable>
        <View style={styles.center}>
          <View style={[styles.statusRing, { borderColor: ERROR_RED }]}>
            <Ionicons name="close" size={36} color={ERROR_RED} />
          </View>
          <Text style={styles.title}>{errorTitle}</Text>
          <Text style={styles.sub}>{errorBody}</Text>
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
          {isNotPole && (
            <View style={styles.tipCard}>
              <View style={styles.tipHeadRow}>
                <Ionicons name="alert-circle" size={16} color={ERROR_RED} />
                <Text style={styles.tipHead}>확인해보세요</Text>
              </View>
              {isLowQualityNotPole ? (
                // 화질 우선 순서 — 원본 화질/직접 촬영 → 기준 동작 일치 → 전신.
                <>
                  <Text style={styles.tipItem}>
                    · 원본 화질 영상으로 다시 올리기 (카톡은 '원본' 전송)
                  </Text>
                  <Text style={styles.tipItem}>· 앱에서 직접 촬영하면 가장 정확해요</Text>
                  <Text style={styles.tipItem}>· 선택한 기준 동작이 영상과 같은지</Text>
                  <Text style={styles.tipItem}>· 전신이 다 보이는지</Text>
                </>
              ) : (
                // Phase 26 (D-01-ii / A1) — 구도·거리 항목 보강. 게이트 불변(D-01),
                // 카피만.
                <>
                  <Text style={styles.tipItem}>· 폴스포츠 연습 영상이 맞는지</Text>
                  <Text style={styles.tipItem}>
                    · 몸 전체가 화면에 들어오는 거리(약 2~3m)에서 정면으로 촬영했는지
                  </Text>
                  <Text style={styles.tipItem}>· 선택한 기준 동작이 영상과 같은지</Text>
                  <Text style={styles.tipItem}>· 전신이 다 보이는지</Text>
                </>
              )}
            </View>
          )}
        </View>
        {/* 32-12 (D-30) — 재업로드 동선. 두 진입 플로우 모두 push('/analysis/loading')
            이라 router.back()은 mode1(reference 경유)에서 분석탭이 아닌 기준선택 화면으로
            떨어진다. 실패 후 다음 행동은 어느 모드든 분석탭 재진입이 확실하므로 replace 로
            실패 스택을 정리하며 분석탭으로 보낸다(result.tsx 재분석 upsell 과 동일 패턴). */}
        <Pressable
          style={styles.cta}
          onPress={() => router.replace('/(tabs)/analyze')}
          accessibilityRole="button"
          accessibilityLabel="다시 분석하기"
        >
          <Text style={styles.ctaText}>다시 분석하기</Text>
        </Pressable>
      </LinearGradient>
    );
  }

  if (done && doneHeld) {
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

  // 카피 — 모드별 분기. 사용자 이름 인터폴, 게스트는 "회원님" fallback.
  // mode1 = 전문가(정은지) 비교 → "전문가와 ~ 분석", Figma 1:429/436/445 와 동일.
  // mode3 = 자기 동작/지난 비교 → "전문가" 가 어색해 본인 동작으로 한정(belle P1 #1).
  const rawName = auth.currentUser?.displayName?.trim() ?? '';
  const greetName = !rawName
    ? '회원님'
    : rawName.endsWith('님')
      ? rawName
      : `${rawName}님`;
  const isMode1 = mode === 'mode1';
  const titleLine = isMode1
    ? `전문가와 ${greetName}의\n포즈를 분석하고 있어요`
    : `${greetName}의 동작을\n분석하고 있어요`;

  return (
    <LinearGradient colors={[NAVY_TOP, NAVY_BOT]} style={styles.container}>
      <StatusBar style="light" />
      <View style={styles.center}>
        <BlobRing>
          <Text style={styles.ringPct}>{displayPct}%</Text>
          <Text style={styles.ringSub}>{REASSURANCE_COPIES[copyIdx]}</Text>
        </BlobRing>
        <Text style={styles.titleBelowRing}>{titleLine}</Text>
        <Text style={styles.stepLine}>{STATUS_MESSAGE[status]}</Text>
        {/* Phase 27 D-07 — 대기를 채우는 폴스포츠 팁 로테이션 (navy 예외 화면 위
            가독 색상, 음수 letterSpacing 금지). */}
        <Text style={styles.tipLine}>{POLE_TIPS[tipIdx]}</Text>
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
  // 진행률 큰 숫자 — 링 안 중앙. 멈춤 인상 방지(P2 #9).
  // letterSpacing 음수값이 iOS 26.4.2 의 RCTMountingManager NSCFNumber 처리에서
  // SIGABRT 를 일으킨 사례 확인 — 음수 letterSpacing 회피 (build 9 crash).
  ringPct: {
    color: '#FFFFFF',
    fontSize: 44,
    fontWeight: '700',
    textAlign: 'center',
  },
  ringSub: { ...typography.caption, color: TEXT_DIM, textAlign: 'center' },
  titleBelowRing: {
    ...typography.listTitle,
    color: '#FFFFFF',
    textAlign: 'center',
    lineHeight: 24,
    marginTop: 32,
  },
  stepLine: {
    ...typography.caption,
    color: TEXT_DIM,
    marginTop: 12,
    textAlign: 'center',
  },
  // Phase 27 D-07 — 팁 로테이션 한 줄. stepLine 보다 살짝 밝게(읽을거리 강조),
  // navy 위 가독. 음수 letterSpacing 금지(iOS SIGABRT 이력).
  tipLine: {
    ...typography.caption,
    color: 'rgba(255,255,255,0.72)',
    marginTop: 20,
    textAlign: 'center',
    lineHeight: 19,
    paddingHorizontal: 12,
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
