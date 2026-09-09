import AsyncStorage from '@react-native-async-storage/async-storage';
import { useLocalSearchParams, useRouter } from 'expo-router';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
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
import { CoachingTipDetailModal } from '../../components/CoachingTipDetailModal';
import { RecommendedExerciseModal } from '../../components/RecommendedExerciseModal';
import {
  KeypointOverlay,
  KEYPOINT_DELTA_HIGHLIGHT_DEG,
} from '../../components/KeypointOverlay';
import { KeypointOverlayToggle } from '../../components/KeypointOverlayToggle';
import { DeductionDetailSheet } from '../../components/DeductionDetailSheet';
import {
  ResultHeaderBackdrop,
  ResultHeaderBar,
  useResultScale,
  useResultTopDelta,
} from '../../components/result/ResultHeader';
import { ResultScoreDial } from '../../components/result/ResultScoreDial';
import { ResultSummaryCard } from '../../components/result/ResultSummaryCard';
import { ResultMomentList } from '../../components/result/ResultMomentList';
import { ResultPointsCard } from '../../components/result/ResultPointsCard';
import { ResultPointModal } from '../../components/result/ResultPointModal';
import { ResultExerciseTab } from '../../components/result/ResultExerciseTab';
import { riskFlagCopy, topRiskFlag } from '../../components/InjuryRiskSection';
import { buildSummaryChips, summaryChipLabel } from '../../lib/resultSummary';
import { VideoCompare } from '../../components/VideoCompare';
import RenderedComparePlayer from '../../components/RenderedComparePlayer';
// ── 32-11 대배선 — 32-07/32-08/32-10 산출 컴포넌트·뷰모델 배선 ──────────────
import { ZoomCompositeImage } from '../../components/ZoomCompositeImage';
import { ResultCoachmarks } from '../../components/ResultCoachmarks';
import { hasSeenResultCoachmark, markResultCoachmarkSeen } from '../../lib/coachmark';
import {
  selectEstimatedZoomEntries,
} from '../../lib/resultSections';
import { buildCueWindows } from '../../lib/cueTrack';
import type { CueInput } from '../../lib/cueTrack';
import { buildRefSnapSecs } from '../../lib/voiceSnap';
// belle 09-07 — "코칭이 짚는 순간으로 뛰어들어가 손가락으로 확대해 본다" 진입점의
// 데이터. 초의 출처는 저장값 둘뿐이고(atVideoSec / refVideoSec) 조인 규칙 신설은
// 0 이다 — 상세는 lib/momentJump.ts 헤더.
import { buildMomentTargets, type MomentTarget } from '../../lib/momentJump';
import { normalizeMotionAlignment } from '../../lib/alignmentWarp';
import { legacyOffsetFromCompareFrames } from '../../lib/manualOffset';
import {
  ANGLE_VS_REFERENCE_PREFIX,
  KEYPOINT_FROM_ANGLE_KEY,
  buildDeductionMarkers,
  buildDeductionTicks,
  composeShortActionLabelKo,
  criterionLabelKo,
  formatDeductionNumber,
  formatDeductionRecord,
  matchZoomForDeductionRecord,
  projectDeductionRecordKeypoints,
  sortDeductionRecordsByMoment,
} from '../../lib/deductionLabels';
import {
  buildPartGroups,
  buildRegionSheetView,
  composeCueSubtitleKo,
} from '../../lib/deductionSheet';
import {
  useReferenceMotion,
} from '../../lib/referenceMotions';
import { useAnalysisDoc } from '../../lib/userAnalyses';
import { useBodyProfile } from '../../lib/bodyProfile';
import {
  resolveZoomImageUrl,
  resolveZoomPlainImageUrl,
  useFreshFaultZoomUrls,
  zoomCardKey,
} from '../../lib/faultZoomUrls';
import {
  requestPlaybackUrl,
  requestReferencePlaybackUrl,
} from '../../lib/api';
import {
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
// IN-01 (quick-260724-q6b) — 역립 저신뢰 시 확대비교 진입점 라벨. topFix 카드가
// 억제돼 확대비교가 도달 불가한 gap 을 메운다 (belle: "예상 부위"로 도달 가능해야
// 함). "AI 공부 중" 안내줄이 맥락을 주므로 추정임이 전달됨 — 확정 결함 단정 아님.
const ATTR_ZOOM_ESTIMATED_ENTRY_LABEL = '예상 부위 확대 비교 보기';
// quick-260903-ftg — IN-01 경로 예상 부위 사진 카드 제목. 시트 제목
// (DeductionDetailSheet ESTIMATED_AREA_TITLE)과 문자 동일하게 두어 카드→시트가
// 같은 hedge 로 읽힌다. 관절명 없음(IN-01 per-joint 단정 강등 락 — 260724-q6b).
// 접근성 라벨은 종전 ATTR_ZOOM_ESTIMATED_ENTRY_LABEL 을 계속 쓴다.
const ATTR_ZOOM_ESTIMATED_CARD_TITLE = '예상 부위 (참고)';


// 32-11 (D-17 확정 밀도 = 결함 구간당 1개) — 재생 중 자막 큐 윈도우 폭(초)과 상한.
// 결함 순간 전후 CUE_WINDOW_SEC/2 동안 자막 유지. maxCues 는 record 수로 두되(각
// record 1윈도우), 겹칠 땐 activeCue 가 시작 늦은(더 정확한) 큐를 우선한다.
const CUE_WINDOW_SEC = 1.6;





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

// belle 09-08 재디자인 — 상단 4탭. key 는 화면 내부용, label 은 시안 문구 그대로.
type ResultTabKey = 'summary' | 'compare' | 'points' | 'exercise';
const RESULT_TABS = [
  { key: 'summary', label: '요약' },
  { key: 'compare', label: '동작비교' },
  { key: 'points', label: '교정포인트' },
  { key: 'exercise', label: '보완운동' },
] as const;
// 점수 원 아래 한 줄 — 시안 문구 그대로("Today"). 한글 앱이지만 이 자리는 시안이
// 영문으로 고정했고 belle 지시가 "완전 동일하게" 다.
const DIAL_LABEL = 'Today';
// 요약 카드 헤드라인 아래 한 줄 — 시안 문구 그대로.
const SUMMARY_SUBLINE = '90점 이상이면 기준 자세에 가까워요';
// 탭별 콘텐츠 시작 y (safe-area 상단 기준 pt, 시안 실측). 탭 밑줄 아랫변이 125.6 이라
// 그보다 아래여야 한다 — 그 위로 올라오면 타이틀·탭에 가린다.
const RESULT_TAB_TOP: Record<ResultTabKey, number> = {
  summary: 150.1, // 점수 원 윗변
  compare: 165.3, // 영상 카드 윗변
  points: 150.0,
  exercise: 150.0,
};

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


// (구 DimensionScoreRow 제거 — D-03/D-12. 세부 점수 행/자세히 모달 폐기, 차원 수치는
//  감점 카드 게이지·심사 정보 코너로 흐른다.)

// (구 DIAGNOSIS_LABEL_KO / DimensionDiagnosisRow 제거 — D-03/D-12. 추상 지표
//  '동작 흐름'/'안정성' 나열 폐기, 심사 정보 코너로 대체.)




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
  // belle 09-08 재디자인 — 4탭 셸. 기존 섹션은 한 줄도 지우지 않고 탭으로 나눠 담았다
  // (요약/동작비교/교정포인트/보완운동). 탭별 첫 요소가 곡선 헤더 아래 어디서
  // 시작하는지는 시안 실측값이다 — RESULT_TAB_TOP.
  const [resultTab, setResultTab] = useState<ResultTabKey>('summary');
  const headerScale = useResultScale();
  // 곡선은 화면 상단 고정, 글자·콘텐츠만 상태바를 피해 내린다 (useResultTopDelta).
  const contentTop =
    useResultTopDelta() + RESULT_TAB_TOP[resultTab] * headerScale;
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
    // 260806-sjt — 아래 freshMyUrl 훅의 videoKey 형상 가드와 동일 규칙.
    // 지난 영상(prev) 슬롯도 비정식 키 doc 이면 재발급을 생략하고 doc 저장 URL 을 쓴다.
    const prevVideoKey = prevDoc.result?.myVideoKey;
    if (prevVideoKey && !prevVideoKey.startsWith('uploads/')) {
      setFreshPrevUrl(null);
      return;
    }
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
    // 260806-sjt — 비정식 videoKey(fixtures/... 등) doc 은 canonical 재발급 키
    // uploads/{uid}/{analysisId}.{ext} (s3keys.py:18) 에 객체가 없다. 백엔드는 객체
    // 존재 확인 없이 서명해 200 을 주므로(재발급 URL GET 404) 그 URL 이 doc 의
    // 유효한 myVideoUrl 을 덮어썼다. 키 부재 구 doc 은 canonical 일 가능성이 높아
    // 현행 재발급을 유지한다 — 그래서 조건은 양항이어야 한다.
    const myVideoKey = result.myVideoKey;
    if (myVideoKey && !myVideoKey.startsWith('uploads/')) {
      setFreshMyUrl(null);
      return;
    }
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

  // quick-260824-q6p — 확대 비교 PNG 재발급 훅 (freshMyUrl 선례 미러). doc 의
  // faultZoomComparisons[].imageUrl 은 분석 시점 7일 presigned 라 만료 후 비교
  // 패널이 회색이 된다 — 6일 초과 doc 은 배치 재서명(asset 'faultZoom')으로
  // fresh 맵을 받고, 시트 렌더 경계에서 `freshZoomUrls[key] ?? imageUrl` 로
  // 조회한다 (doc item 무변형, 실패 시 현행 회색 fail-closed 폴백 그대로).
  const { freshZoomUrls, freshZoomPlainUrls, onZoomImageError } =
    useFreshFaultZoomUrls({
    analysisId,
    createdAt,
    comparisons: result.faultZoomComparisons ?? null,
  });

  // Phase 35 (quick-260808-jix, contract.md §12.9) — 합성 비교 영상 분기 신호.
  // done + key 보유 doc 만 단일 mp4 재생 (리그 ALL PASS 만 done 이 된다).
  // 부재(legacy)/failed = 기존 듀얼 플레이어 폴백. renderedUnavailable 은 asset
  // URL fetch 실패(만료·404 등) 시 이 세션 한정 강등 — 분석 전환 시 리셋.
  // onSnapshot 구독이라 렌더가 세션 중 도착하면 자동으로 이 분기가 켜진다
  // (별도 폴링 금지 — 구독 기반).
  const renderedCompareReady =
    result.renderedCompare?.status === 'done' && !!result.renderedCompare.key;
  const [renderedUnavailable, setRenderedUnavailable] = useState(false);
  useEffect(() => {
    setRenderedUnavailable(false);
  }, [analysisId]);

  // Phase 20 (UI A1) — 비전 거부권으로 종합점수가 similarity 보다 낮아진 경우.
  // visionVeto.status==='applied' 가 1차 신호. 안전망: overallScore < similarity 면(어떤
  // 이유든) similarity 헤드라인이 octagon 과 모순되므로 절대 노출하지 않는다.
  const vetoApplied = result.visionVeto?.status === 'applied';
  // #3 (2026-06-21) — Gemini 가 식별한 실제 결함 keypoint(backend 매핑). 있으면
  // 마커를 각도편차 최대 관절이 아니라 진짜 결함 관절에 찍는다 (legacy doc=undefined).
  const vetoFaultJoints =
    result.visionVeto?.status === 'applied' ? result.visionVeto.faultJoints : undefined;

  // belle 08-07 #1 (quick-260807-fpw) — 감점 record 단일 출처 + 시간순 정렬.
  // 정렬 지점은 이 memo **한 곳뿐** (sortDeductionRecordsByMoment 는 여기서만 호출).
  // buildDeductionMarkers 가 입력 순회 순서대로 번호를 부여하므로, 입력을 측정
  // 순간(atVideoSec) 오름차순으로 정렬하면 영상 마커·재생바 틱·점수 계산 내역 행이
  // 함께 시간순 1..N 이 된다. atVideoSec 없는 record 는 뒤에 원순서 (fabricate 0).
  // 이하 record 소비자는 전부 이 배열을 쓴다 — breakdown 원본 배열 직접 접근
  // 재도입 금지 (정렬 전 배열과 index 조인이 어긋난다).
  const records = useMemo(
    () =>
      sortDeductionRecordsByMoment(result.deductionBreakdown?.records ?? []),
    [result.deductionBreakdown],
  );

  // 요약 카드 — 감점 칩은 '점수 계산 내역'과 **같은 라벨·수치 소스**를 쓴다(사본 0).
  const summaryChips = useMemo(() => buildSummaryChips(records), [records]);
  // 노란 경고 박스 = 실재하는 안전 신호(safetyFlags)뿐. 시안의 '레벨 대비 무리한 동작
  // 가능성' 은 이미 앱에 있는 level_mismatch 카피와 **글자까지 같다** — 시안이 이
  // 카피에서 나왔다. 없는 경고를 지어내지 않으므로 flag 가 없으면 박스도 없다.
  // 동작비교 탭 감점 목록 (시안 2). records 는 이미 시간순 정렬본이라 그대로 쓴다 —
  // 시안도 초 오름차순이다. 초는 저장값(atVideoSec)만, 없으면 칸을 비운다.
  const momentRows = useMemo(
    () =>
      records
        .filter(
          (r) => typeof r.points === 'number' && Number.isFinite(r.points) && r.points < 0,
        )
        .map((r) => ({
          recordId: typeof r.recordId === 'string' && r.recordId ? r.recordId : null,
          sec:
            typeof r.atVideoSec === 'number' && Number.isFinite(r.atVideoSec)
              ? r.atVideoSec
              : null,
          label: summaryChipLabel(r.criterion),
          pointsText: `−${formatDeductionNumber(Math.abs(r.points))}`,
        })),
    [records],
  );
  // 교정포인트 탭 (시안 3) — 같은 감점을 '점수 계산 내역'과 같은 값으로 보여주되,
  // 행을 펼치면 그 순간의 확대 짝 사진과 왜 감점인지 문장이 나온다. 사진·문장은 전부
  // doc 저장값이다(사진 = 그 record 의 확대 카드, 문장 = whyLine/cueLine) — 지어내지 않는다.
  const [expandedPointId, setExpandedPointId] = useState<string | null>(null);
  // 시안 5 (교정포인트2) — 전체화면 모달. null = 닫힘, 숫자 = pointRows 안의 위치.
  const [pointModalIndex, setPointModalIndex] = useState<number | null>(null);
  const pointRows = useMemo(
    () =>
      records
        .filter(
          (r) => typeof r.points === 'number' && Number.isFinite(r.points) && r.points < 0,
        )
        .map((r) => {
          const zoom = matchZoomForDeductionRecord(
            r,
            vetoFaultJoints,
            result.faultZoomComparisons ?? [],
          );
          return {
            recordId: typeof r.recordId === 'string' && r.recordId ? r.recordId : null,
            sec:
              typeof r.atVideoSec === 'number' && Number.isFinite(r.atVideoSec)
                ? r.atVideoSec
                : null,
            label: summaryChipLabel(r.criterion),
            pointsText: `−${formatDeductionNumber(Math.abs(r.points))}`,
            imageUrl: zoom ? resolveZoomImageUrl(zoom, freshZoomUrls) : null,
            caption: r.whyLine ?? null,
            lines: r.cueLine ? [r.cueLine] : [],
          };
        }),
    [records, vetoFaultJoints, result.faultZoomComparisons, freshZoomUrls],
  );
  // 시안 5 페이지 — 교정포인트 행과 **같은 순서·같은 record**. 문장은 전부 doc
  // 저장값(statusLine/whyLine/cueLine + 측정 근거 detailText)이고, 없는 칸은 그리지
  // 않는다. 이 화면이 지어내는 문장은 0이다.
  const pointPages = useMemo(
    () =>
      records
        .filter(
          (r) => typeof r.points === 'number' && Number.isFinite(r.points) && r.points < 0,
        )
        .map((r) => {
          const zoom = matchZoomForDeductionRecord(
            r,
            vetoFaultJoints,
            result.faultZoomComparisons ?? [],
          );
          const label = summaryChipLabel(r.criterion);
          const pts = formatDeductionNumber(Math.abs(r.points));
          return {
            chipText: `고칠 것 · ${label} ${pts}점`,
            headline: r.statusLine ?? null,
            sub: r.whyLine ?? null,
            imageUrl: zoom ? resolveZoomImageUrl(zoom, freshZoomUrls) : null,
            // belle 09-09 '관절선 끄기' (contract.md §11.11) — 표시 없는 판.
            // 없으면 null 이고 모달이 칩을 안 그린다 (legacy doc·렌더 실패 = 토글 불가).
            imageUrlPlain: zoom
              ? resolveZoomPlainImageUrl(zoom, freshZoomPlainUrls)
              : null,
            cue: r.cueLine ?? null,
            basis: formatDeductionRecord(r).detailText,
          };
        }),
    [
      records,
      vetoFaultJoints,
      result.faultZoomComparisons,
      freshZoomUrls,
      freshZoomPlainUrls,
    ],
  );
  // '강사에게 공유' 문구 (시안 4). 화면에 이미 보이는 값만 옮겨 담는다 — 새 문장을
  // 짓지 않는다. 감점이 없으면 목록 줄이 빠지고 점수 한 줄만 나간다.
  const shareMessage = useMemo(() => {
    const head =
      cmp.mode === 'mode1'
        ? `${cmp.athleteName} 선수 · ${cmp.referenceMotionName} 기준 분석`
        : '지난 영상과 비교한 분석';
    const lines = pointRows.map(
      (r) =>
        `- ${r.sec != null ? `${r.sec.toFixed(1)}s ` : ''}${r.label} ${r.pointsText}`,
    );
    return [head, `종합 ${Math.round(result.overallScore)}점`, ...lines].join('\n');
  }, [cmp, pointRows, result.overallScore]);
  const summaryWarning = useMemo(() => {
    const flag = topRiskFlag(result.safetyFlags);
    const copy = flag ? riskFlagCopy(flag.flagType) : null;
    return copy ? { title: copy.title, lines: [copy.why] } : null;
  }, [result.safetyFlags]);

  // quick-260704-fz4 — 2단 시각 언어 set 단일 조립 (표·마커·카드가 같은 소스 사용).
  // 빨강 = 확정 결함(감점 근거): deductionBreakdown records 의
  // angle_vs_reference__{jk} 관절 ∪ vetoFaultJoints (faultJoints 는 split_angle 등
  // 관절명 없는 vision record 의 관절 투영, CONTEXT locked).
  const confirmedKeypoints = useMemo(() => {
    const set = new Set<KeypointName>();
    for (const kp of vetoFaultJoints ?? []) set.add(kp);
    for (const r of records) {
      if (r.criterion.startsWith(ANGLE_VS_REFERENCE_PREFIX)) {
        const jk = r.criterion.slice(ANGLE_VS_REFERENCE_PREFIX.length);
        const kp = KEYPOINT_FROM_ANGLE_KEY[jk];
        if (kp) set.add(kp);
      }
    }
    return set;
  }, [vetoFaultJoints, records]);

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


  // IN-01 (quick-260724-q6b) — 역립/자기가림 저신뢰 게이트 단일 신호 (Task 3/4 공용).
  // unreliable 이면 per-joint 단정 표면(오버레이 마커·점수 내역·코칭 팁·확대비교 라벨·
  // topFix·접힘 카드·요약 헤드라인·심사 코너)을 전부 강등/억제한다. 점수 값
  // (overallScore/final/records)은 byte-불변 — 표현 전용. false/부재 시 렌더 diff 0.
  const attributionUnreliable = result.attributionReliability?.unreliable === true;

  // IN-01 — 예상 부위 단일 관절 (역립 저신뢰 오버레이 주황 점 최대 1개). angle_vs_
  // reference 감점 record 중 |points| 최대이며 keypoint 매핑되는 관절 1개, 폴백은
  // windowMedianAngleDeltas |delta_deg| 최대. 매핑 없으면 빈 배열(점 0개).
  const estimatedAreaKeypoints = useMemo<KeypointName[]>(() => {
    if (!attributionUnreliable) {
      return [];
    }
    let bestKp: KeypointName | null = null;
    let bestAbs = -1;
    for (const r of records) {
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
  }, [attributionUnreliable, records, result.visionVeto]);

  // IN-01 (quick-260724-q6b) — 예상 부위 확대비교 진입점이 열 record 의 index.
  // estimatedAreaKeypoints 의 record 경로(angle_vs_reference + keypoint 매핑, |points|
  // 최대)와 동일 선택 로직이므로 진입점과 오버레이 주황 점이 같은 관절을 가리킨다.
  // windowMedian 폴백 경로는 대응 record 가 없어 index 없음 → null(진입점 미렌더 —
  // graceful: 안내줄 + 정은지 비교는 그대로). false/부재 시 null.
  const estimatedAreaRecordIndex = useMemo<number | null>(() => {
    if (!attributionUnreliable) return null;
    let bestIdx: number | null = null;
    let bestAbs = -1;
    const recs = records;
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
  }, [attributionUnreliable, records]);

  // quick-260705-o0s — 영상 점 번호 ↔ 내역 행 번호 단일 소스 (buildDeductionMarkers).
  // 오버레이 markerNumbers 와 ScoreBreakdownSection recordNumbers 가 같은 결과물을
  // 소비해 항상 일치. markers.keypointNumbers 키는 confirmedKeypoints 의 부분집합
  // (동일 투영 규칙) — highlightKeypoints 는 기존 confirmedKeypointList 유지로 자동 정합.
  const markers = useMemo(
    () => buildDeductionMarkers(records, vetoFaultJoints),
    [records, vetoFaultJoints],
  );

  // 33-G S1/S3 (quick-260730-szk) — **부위 단위** 그룹 마커 + 부위 칩. 승인 목업 ① 은
  // 마커를 항목(부위) 단위 경계 1개로 묶고(2R#1 "동그라미가 7개") 그 아래에 부위 칩을
  // 둔다. 두 산출 모두 deductionSheet 의 원인 키 단일 출처를 소비하므로 마커 그룹 =
  // 칩 = 부위 시트가 같은 단위다 (두 번째 그룹핑 규칙 0).
  // quick-260802-mrg — 그 단일 출처가 부위 키에서 **원인 키**로 옮겨졌다(merge-only).
  const partGroups = useMemo(
    () => buildPartGroups(records, markers.recordNumbers, vetoFaultJoints),
    [records, markers.recordNumbers, vetoFaultJoints],
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
    const recs = records;
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
  }, [records, markers, vetoFaultJoints, actionLabels]);

  // quick-260705-r6v — 재생바 결함 시점 틱 (buildDeductionTicks — 같은 프레임의
  // 번호를 틱 1개로 병합).
  //
  // belle 09-07 정정 — 여기 있던 "veto 미적용/legacy/mode3 면 빈 배열"은 사실이
  // 아니었다. buildDeductionTicks(deductionLabels.ts:434-474)에는 mode 분기가 한
  // 줄도 없고 visionVeto 는 **atFrameIdx 없는 record 를 median 프레임에 얹는
  // 폴백**에만 쓰인다. 즉 번호를 받은 record 중 하나라도 atFrameIdx 를 들고 있으면
  // mode3 에서도 틱은 그려진다 — 실제로 mode3 의 상시 진입점이 이 틱이다.
  // 빈 배열이 되는 경우는 하나뿐: 번호 받은 record 전부가 atFrameIdx 를 갖지
  // 않고(비유한·음수·부재) veto median 폴백도 없을 때. 동작 변경 0 — 문서만 정정.
  const timelineTicks = useMemo(
    () =>
      buildDeductionTicks(records, markers.recordNumbers, result.visionVeto),
    [records, markers.recordNumbers, result.visionVeto],
  );

  // 33-13 (A-6, D-18 양방향 대응) — breakdown record 보유 doc 의 영상 위 빨강
  // 마커는 buildDeductionMarkers 투영(번호 점 관절 + 그룹 멤버)으로만 구성한다 —
  // record 와 짝 없는 마커(고아)는 미렌더. 종전 소스(confirmedKeypointList =
  // records 투영 ∪ vetoFaultJoints 전체)는 record 투영 밖 faultJoints 여분이
  // 무번호 빨강 점을 만들 수 있었다. breakdown 부재(legacy)는 기존 소스 유지
  // (record 가 없어 양방향 대응 자체가 정의 불가 — graceful 하위호환).
  const hasBreakdownRecords = records.length > 0;
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
  // unreliable 이면 **영상 위** 확정 빨강 점/번호/그룹과 전체화면 범례를 비우고
  // 예상 부위 주황 점 최대 1개(estimatedAreaKeypoints)만 남긴다.
  // false/부재 시 기존 소스 그대로 → 렌더 diff 0.
  //
  // quick-260806-wj3 — 종전에는 진행 바 **틱까지** 함께 비웠다("번호가 사라졌으므로
  // 범례/틱도 빈 배열"). 그 전제가 틀렸다: 번호는 저신뢰 doc 에서도 사라지지 않는다
  // (아래 overlayTimelineTicks 주석 참조). 틱만 강등에서 뺀다.
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
  // quick-260806-wj3 (belle 실기기 ②) — 진행 바 감점 틱은 저신뢰 doc 에서도 렌더한다.
  //
  // 왜 되살리나: 진행 바에 아무 표시가 없으면 사용자는 그것을 "분석이 틀렸다"로 읽는다
  // (belle 관측). 그리고 틱은 고아가 아니다 — 틱 번호는 markers.recordNumbers 파생이고,
  // 그 번호는 저신뢰 doc 에서도 점수 계산 내역 행·감점 시트에 그대로 렌더된다. 탭하면
  // 그 시점으로 seek + openRecordByNumber 로 해당 항목이 열린다(그 함수에 저신뢰
  // 게이트 없음). 즉 가리키는 대상이 실재한다.
  //
  // 비대칭은 **의도된** 것이다: 영상 위 마커/번호/그룹과 전체화면 범례는 계속 억제한다.
  // 저신뢰에서 관절 단정을 영상 위에 찍지 않는 것이 IN-01 승인 설계의 핵심인데, 진행 바
  // 틱은 그 단정이 아니라 **시점** 안내이기 때문이다. "영상 위에도 번호를"은 IN-01
  // 재논의 건이지 이 수리의 결함이 아니다.
  const overlayTimelineTicks = timelineTicks;





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
      records.map((rec) =>
        matchZoomForDeductionRecord(
          rec,
          vetoFaultJoints,
          result.faultZoomComparisons ?? [],
        ),
      ),
    [records, vetoFaultJoints, result.faultZoomComparisons],
  );
  // paircap 우측 라벨 — 승인본 6R 문형 `기준 (정은지)`. mode3 는 `지난 영상`.
  // (crop 위 halfLabel 용 rightLabel 은 기존 문형 `{name} 선수` 유지 — 두 표면의
  //  승인 문형이 서로 다르다.)
  const rightPairLabel =
    cmp.mode === 'mode1' ? `기준 (${cmp.athleteName})` : '지난 영상';
  const sheetView = useMemo(() => {
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
    records,
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

  // quick-260901-wbo — 코칭 문장 사후 도착 (zoomPending effect 1:1 미러).
  // coach_text 사후 스테이지가 result.tips 를 코칭 텍스트로 승격하면 useAnalysisDoc
  // onSnapshot 구독이 자동 rerender — 추가 폴링 0(안티패턴). updatedAt 갱신(사후
  // 부분 업데이트가 updatedAt 을 갱신)마다 타이머 재무장. 상한 초과·'failed'·부재
  // (legacy doc)·'done' 은 전부 기존 tips 렌더 그대로 — placeholder 만 숨고 섹션은
  // 비지 않는다 (tips 는 required 필드, pending 동안에도 수치 폴백이 실려 있음).

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

  // (구 참고 지표 occlusion badge 제거 — D-03/D-12. 가림 신호는 코칭 팁 추정
  //  표기(isAngleEstimated)로만 노출. lowReliabilityRatioVal 은 그 경로에서 소비.)

  // #4 (2026-06-21) — 3D 자세 뷰어 제거. RTMW joints3d 는 깊이 없음(y≈0)이라 진짜
  // 회전 3D 가 원리적으로 불가 → 평면 뼈대를 "3D" 로 보여주던 오인 UI 였다. belle:
  // "영상에서 돌릴 수 있어야"(camera-angle-AI). 리서치 결론: 충실한(자세 환각 없는)
  // 카메라각 합성 API 는 현재 없음(생성형=환각, in-house 메시=라이선스 차단) →
  // belle 방향 결정 대기. 그동안 깨진 뷰어는 즉시 제거(미루기 금지 원칙).






  // (구 vetoFixTip 제거 — quick-260831-lcc veto 카드 해체. "이렇게 교정해 보세요"
  //  줄은 코칭 팁 detail 의 verbatim 재출현이었다 — 코칭 팁 본문이 유일본.)

  // (구 deltaFor 제거 — DimensionScoreRow delta 행 폐기와 함께 미사용.)

  // ══════════════════════════════════════════════════════════════════════
  // 32-11 대배선 — 요약/섹션/조인 뷰모델 (리뷰 MEDIUM: 파생 계산 useMemo).
  // 위 기존 파생값(markers/actionLabels/joints/veto…)을 소비해 새 컴포넌트
  // (SummaryCard/DeductionCard/cueTrack)로 조립한다. 순서·가시성은 resultSections
  // 뷰모델 단일 지점이 결정하고, 카드 상호작용은 recordId 조인 맵으로만 잇는다.
  // ══════════════════════════════════════════════════════════════════════
  // (records/hasRecords memo 는 belle 08-07 #1 단일 출처화로 첫 사용 앞
  //  — confirmedKeypoints 위 — 로 이동했다. 여기 재선언 금지.)

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



  // 결함 zoom(userFrameIdx 보유) 조인 매처 — selectedZoom 과 동일 단일 출처
  // (deductionLabels.matchZoomForDeductionRecord — 33-12 A-5 criterion 키 일치
  // 1차 + legacy 교집합 폴백, advisory 제외). cueWindows·recordMaps 공용.
  const matchZoomForRecord = (rec: DeductionRecord): FaultZoomComparison | null =>
    matchZoomForDeductionRecord(
      rec,
      vetoFaultJoints,
      result.faultZoomComparisons ?? [],
    );


  // quick-260903-ftg — IN-01 저신뢰 경로의 예상 부위 사진 카드 목록(확정 카드 전부).
  // 종전 진입 링크는 estimatedAreaRecordIndex 1건의 시트만 열어 확정 카드가 2장이어도
  // 두 번째가 도달 불가였다 (09-03 시뮬 실측, belle pdshape 60점 doc). 선택 규칙
  // (primary 맨 앞·숨김 제외·같은 카드 dedupe)은 selectEstimatedZoomEntries 단일
  // 지점, 매칭은 recordMaps/cueWindows 와 같은 matchZoomForRecord 단일 출처(신규
  // 조인 규칙 0). 저신뢰가 아니면 빈 배열 — 그 경로 렌더 diff 0.
  const estimatedZoomEntries = useMemo(
    () =>
      attributionUnreliable
        ? selectEstimatedZoomEntries(
            records,
            (rec) => matchZoomForRecord(rec),
            zoomCardKey,
            isRecordHidden,
            estimatedAreaRecordIndex,
          )
        : [],
    // matchZoomForRecord/isRecordHidden 은 아래 deps 파생 (recordMaps memo 관례).
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      attributionUnreliable,
      records,
      result.faultZoomComparisons,
      vetoFaultJoints,
      hiddenRecordIds,
      estimatedAreaRecordIndex,
    ],
  );

  // 33-13 (A-6, D-13 대표 UX) — 음성 큐 recordId → 강조 부위 투영. cue 는
  // records 에서 태어나므로(cueWindows 조립) 항상 짝이 있다 — 못 찾으면 빈 배열
  // = 강조 0 (D-18 고아 가드). 투영 규칙 = projectDeductionRecordKeypoints 단일
  // 출처 (마커·크롭과 동일 부위 — 규칙 사본 0).
  //
  // belle 08-07 #4 (quick-260807-fpw) — IN-01 저신뢰 조기 반환(`attributionUnreliable
  // → []`) 제거. 이 함수의 소비처는 음성/큐 표면 2곳뿐(음성 중 강조 + 재생 중 큐
  // 빨간 점)이고, 음성이 이미 그 관절명을 발화하므로 음성 표면에는 부위 표시를
  // 허용한다. 정지 상태 마커 억제(overlayHighlightKeypoints/overlayMarkerNumbers/
  // overlayGroupMarkers/estimatedArea 강등)는 별도 파생이라 그대로 유지 — IN-01
  // 승인 설계의 정지 표면은 무접촉.
  const focusKeypointsForRecordId = (recordId: string): KeypointName[] => {
    const rec = records.find((r) => r.recordId === recordId);
    if (!rec) return [];
    return projectDeductionRecordKeypoints(rec, vetoFaultJoints);
  };

  // 강사 질문 — 자동 수집(result.coachQuestions, D-28) + legacy 폴백
  // (openQuestionsForCoach, coachQuestions 부재 doc만).
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


  // 재생 중 자막 큐 (D-18 자막 + D-17 밀도) — record 의 cueLine(부재 legacy=행동구
  // 폴백) + record 의 **인증된 측정 순간**(atVideoSec)으로 윈도우 산출.
  // 32-13: 스팟체크 숨김 record 는 큐에서도 제외 — 불일치 판정된 문장을 자막·
  // 오디오로 재생하는 것도 '틀린 말 내보내기' (D-23 동일 원칙, 표면 숨김의 일부).
  //
  // debug va-subtitle-audio-mismatch (belle 08-07 실기기 반려) — 큐는 **측정
  // 순간이 인증된 record 만** 자동 발화한다. 종전 앵커(매칭 zoom 의 userFrameIdx)는
  // 측정 순간이 없는 record(비전 산출 split 등)에서 가짜 시각(킵업 0.889s = 재생
  // 시작 직후, 실업로드 3건 동일 프레임 뭉침)을 만들었다. "이 사진이 감점
  // 부분이라 말하려면 인증(atMatched)이 필요하다" 게이트의 시간축 적용: 순간을
  // 지어내지 않는다 — 안내문은 감점 카드·시트에 그대로 있고, 재분석이 제 순간을
  // 만들면(gbk) 큐가 자동으로 돌아온다.
  const cueWindows = useMemo(() => {
    const inputs: CueInput[] = [];
    for (const rec of records) {
      if (isRecordHidden(rec)) continue;
      const atVideoSec = rec.atVideoSec;
      if (typeof atVideoSec !== 'number' || !Number.isFinite(atVideoSec)) {
        continue;
      }
      // quick-260802-mrg — 자막은 **결함이 먼저**다 (belle 실기기 2026-08-01:
      // "자막이 결함 대신 목표를 말한다"). 목표 절은 부위 상세 시트의 goalLine 이
      // 한 번 말한다. 조립 규칙은 lib/deductionSheet 소유 — 여기서 문자열을
      // 만들지 않는다. 폴백 행동구·방출 조건(`!text` 스킵)은 종전 그대로다.
      const text =
        composeCueSubtitleKo(
          rec,
          actionPhraseForRecord(rec, vetoFaultJoints, actionLabels),
        ) ?? '';
      if (!text) continue;
      inputs.push({
        centerSec: atVideoSec,
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

  // belle 08-07 (quick-260807-iwp, BELLE-0807-5) — 음성 멈춤 동안 기준(우) 패널
  // 짝 프레임 스냅 맵: recordId → 매칭 zoom 의 refVideoSec(기준 영상 도메인 초,
  // 백엔드 F-3 방출 — 재계산 금지 근거는 voiceSnap.ts 헤더). 조인은 cueWindows·
  // recordMaps 와 같은 matchZoomForRecord 단일 출처(신규 조인 규칙 0). 숨김
  // record 는 발화 자체가 없으니(cueWindows 동일 필터) 스냅 대상도 아니다.
  // refVideoSec 없는 record(refMatched=false 실업로드·legacy doc)는 빌더가
  // 드롭 — 스냅 생략 (순간 날조 0).
  const cueRefSnapSecs = useMemo(() => {
    const entries: { recordId?: string | null; refVideoSec?: number }[] = [];
    for (const rec of records) {
      if (isRecordHidden(rec)) continue;
      entries.push({
        recordId: rec.recordId,
        refVideoSec: matchZoomForRecord(rec)?.refVideoSec,
      });
    }
    return buildRefSnapSecs(entries);
    // matchZoomForRecord/isRecordHidden 은 아래 deps 파생 (cueWindows memo 관례).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [records, result.faultZoomComparisons, vetoFaultJoints, hiddenRecordIds]);

  // ── belle 09-07 "그 순간으로 뛰어들어가 직접 확대해 본다" 배선 ───────────────
  //
  // 왜 문 3개인가 (이 배선의 근거): 음성 멈춤 중에 뜨는 '크게 보기' pill 은 **오디오
  // 를 켠 사람에게만** 보인다 — 음성 토글 초기값이 false 다(학원 소음, VideoCompare
  // :622). belle 이 그 문을 한 번도 못 볼 수 있다는 뜻이다. 그래서 상시 열려 있는
  // 문을 둘 더 연다: (1) 감점 상세 시트의 보조 버튼, (2) 이미 화면에 있는 재생바 틱
  // → 시트 → 그 버튼. 틱은 mode 무관하게 그려진다(위 timelineTicks 주석 정정 참조).
  //
  // 데이터는 전부 momentJump.buildMomentTargets 가 만든다 — 이 화면이 이미 갖고 있는
  // 파생물(정렬된 records / faultZoomComparisons / vetoFaultJoints)을 그대로 먹인다.
  // 여기서 초를 계산하지도, 조인 규칙을 새로 만들지도 않는다
  // (docs/contract.md:1961-1962 — rep 프레임 인덱스로 초 재계산 금지).
  const momentTargets = useMemo(
    () =>
      buildMomentTargets(
        records,
        result.faultZoomComparisons ?? [],
        vetoFaultJoints,
      ),
    [records, result.faultZoomComparisons, vetoFaultJoints],
  );
  // recordId → 순간. 시트/틱 진입점이 조인 키 하나로 목표를 집는다.
  const momentByRecordId = useMemo(() => {
    const map = new Map<string, MomentTarget>();
    for (const t of momentTargets) map.set(t.recordId, t);
    return map;
  }, [momentTargets]);

  // VideoCompare 안의 명령(전체화면 열기 + 그 순간에 멈춰 세우기) 손잡이.
  // ref 인 이유는 VideoCompareProps.openFullscreenAtRef 주석 참조 — 같은 순간을
  // 두 번 눌러도 동작해야 하는 1회성 명령이라 상태 prop 으로 표현할 수 없다.
  // 듀얼 플레이어 가지가 안 그려질 땐(합성 영상 가지) null 로 남는다.
  const openFullscreenAtRef = useRef<((target: MomentTarget) => void) | null>(
    null,
  );

  // 시트에서 그 순간으로 — 시트를 **먼저 닫고** 전체화면을 연다. 순서가 반대면
  // 시트 Modal 위에 전체화면 Modal 이 얹혀 iOS 중첩 Modal 함정에 걸린다
  // (onLegendPress/onTickPress 가 closeFullscreen 을 선행하는 것과 같은 이유,
  // planner_findings 3 — 방향만 반대다).
  const openMomentForRecord = (recordId: string) => {
    const target = momentByRecordId.get(recordId);
    setDetailRecordIndex(null);
    if (!target) return; // 순간 미확정 record — 없는 초로 뛰지 않는다
    openFullscreenAtRef.current?.(target);
  };

  // 시트 버튼이 가리킬 순간의 조인 키. 상단 크롭을 낳은 대표 record 기준
  // (sheetPrimaryZoom 과 같은 record — 시트가 보여주고 있는 그 사진의 순간이다).
  // 순간이 없으면 null → 시트가 버튼을 **비활성으로** 그린다(숨기지 않는다:
  // 버튼이 사라졌다 나타났다 하면 "왜 어떤 항목엔 없지"가 된다).
  const sheetMomentRecordId =
    sheetView != null
      ? (() => {
          const rid = records[sheetView.primaryRecordIndex]?.recordId;
          return typeof rid === 'string' && momentByRecordId.has(rid)
            ? rid
            : null;
        })()
      : null;

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





  return (
    <View style={styles.container}>
      <ResultHeaderBackdrop />
      <ScrollView
        ref={scrollRef}
        contentContainerStyle={[styles.content, { paddingTop: contentTop }]}
        showsVerticalScrollIndicator={false}
      >
        {resultTab === 'summary' && (
          <>
            <View style={styles.dialWrap}>
              <ResultScoreDial
                score={result.overallScore}
                label={DIAL_LABEL}
                accessibilityLabel={`종합 ${Math.round(result.overallScore)}점`}
              />
            </View>
            <ResultSummaryCard
              total={summaryChips.total}
              chips={summaryChips.chips}
              overflow={summaryChips.overflow}
              subline={SUMMARY_SUBLINE}
              warning={summaryWarning}
              onSeePoints={() => setResultTab('points')}
              onChipPress={(recordId) => {
                const idx = records.findIndex((r) => r.recordId === recordId);
                if (idx >= 0) setDetailRecordIndex(idx);
              }}
            />

          </>
        )}
        {resultTab === 'compare' && (
          <>
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
            {renderedCompareReady && !renderedUnavailable ? (
              /* Phase 35 (quick-260808-jix, contract.md §12.9) — 합성 비교 영상
                 단일 mp4 재생 분기. 이 가지에서 VideoCompare 를 **렌더하지
                 않는다** — cueWindows·cueRefSnapSecs·audioAnalysisId·
                 timelineTicks 가 전부 VideoCompare props
                 이므로 앱 큐 오디오 prefetch·자막·틱 발화 경로가 **구조적으로
                 OFF** 된다 (이중 발화 방지의 구현 = 분기. 개별 prop 끄기 방식
                 금지 — mp4 에 음성·자막이 이미 구워져 있다). 오버레이 토글도
                 의미가 없어(구운 영상) 헤더에서 제외. PartChipsRow(감점 시트
                 진입점)·정렬 upsell 배너는 발화 없음 — 분기 밖 현행 유지. */
              <>
                <View style={styles.compareHeader}>
                  <Text style={styles.sectionTitle}>동작 비교</Text>
                </View>
                <RenderedComparePlayer
                  analysisId={analysisId}
                  onUnavailable={() => setRenderedUnavailable(true)}
                  // UI 라운드 — 정지 틱 데이터 (contract.md §12.9 freezes,
                  // 부재 구버전 doc = 틱 없이 재생만).
                  freezes={result.renderedCompare?.freezes}
                />
              </>
            ) : (
            <>
            {/* 폴백 가지 (renderedCompare 부재 legacy·failed·URL 실패 강등) —
                기존 듀얼 플레이어+라이브 동기 경로 그대로 (quick-260808-jix:
                이 가지 내부 코드 diff 0). */}
            {/* belle 09-09 재디자인 — 섹션 제목('동작 비교')과 관절선 토글을 여기서
                걷어냈다. 제목은 이제 탭 라벨이 대신하고(시안 2 에 섹션 제목이 없다),
                토글은 시안대로 재생 컨트롤 옆 옵션 행의 '관절선 표시' 칩으로 내려간다.
                상태(overlayVisible)의 소유는 여전히 이 화면이다 — 전체화면 헤더의
                같은 토글과 한 상태를 공유해야 하므로 옮기지 않고 넘겨준다. */}
            <VideoCompare
              // belle 09-09 재디자인 — 시안 2 는 감점 목록이 영상 카드 **안**, 옵션 행
              // 바로 아래에 온다. 카드 밖에 두면 부가 컨트롤(음성 안내·미세조정)이
              // 사이에 껴서 시안과 순서가 어긋난다.
              renderBelowControls={({ seekTo, activeRecordId }) => (
                <ResultMomentList
                  flat
                  rows={momentRows}
                  // belle 09-09 — 재생이 그 순간에 닿으면 그 행이 켜진다. 판정 값은
                  // VideoCompare 가 이미 갖고 있는 것(영상 위 색 반전과 같은 값)이라
                  // 목록과 영상이 같은 행을 짚는다 — 새 시간 규칙 0.
                  activeRecordId={activeRecordId}
                  // belle 09-09 — 진행바 틱이 하던 일을 행이 이어받는다: 그 초로 두
                  // 영상을 **함께** 옮기고(seekTo) 상세 시트를 연다. 초는 행에 이미
                  // 적혀 있어 눌렀을 때 어디로 가는지가 눈에 보인다.
                  onRowPress={(recordId) => {
                    const row = momentRows.find((r) => r.recordId === recordId);
                    if (row?.sec != null) seekTo(row.sec);
                    const idx = records.findIndex((r) => r.recordId === recordId);
                    if (idx >= 0) setDetailRecordIndex(idx);
                  }}
                />
              )}
              overlayOn={overlayVisible}
              onToggleOverlay={() => handleToggleOverlay(!overlayVisible)}
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
              leftOverlay={(player, opts) => {
                // quick-260807-k70 (BELLE-0807-9) — 재생 세션 "말하는 지점만" 표기.
                // belle 08-07 저녁 "가로에선 되려 동그라미가 너무 크니까 보기가
                // 너무 힘들어. 지점을 말해줄 때만 표기하는 건 어떨까?" — fpw #4 의
                // "재생 중 기본 흰 점" 접근을 이 정책으로 대체 (belle 재정의 우선).
                // 재생 세션 동안 기본 관절 점·스켈레톤을 숨기고 활성 음성 큐
                // record 의 투영 관절만 빨강(+기존 emphasis·dim). 큐 없으면 점 0.
                //
                // 세션 = 실재생 중 OR 음성 큐 발화 중. 음성 정지 중 playing 은
                // false 지만 voiceCueRecordId 가 non-null 이라 세션 유지. "정지
                // 상태 중 발화"(멈춤 없는 발화)도 이 식에 편입된다 — 표시-발화
                // 일치 원칙상 의도된 포함. 각 prop 삼항의 세션-밖 가지는 현행
                // 표현식 그대로 (세션 밖 렌더 byte 동치).
                const inPlaybackSession =
                  opts?.isPlaying === true || opts?.voiceCueRecordId != null;
                // 세션 중 빨강 대상 record: 발화 중엔 voiceCueRecordId 우선 (체인
                // 발화 중 activeCueWindowRecordId 는 멈춘 cL 기준이라 이전 큐를
                // 가리킬 수 있음 — VideoCompare 함정 a 주석 실증). 재생 중(발화
                // 없음)엔 활성 큐 윈도우. activeCueRecordId 는 발화 여부 무관
                // 윈도우 신호라 오디오 OFF 자막-만 재생에서도 성립.
                const sessionCueRecordId =
                  opts?.voiceCueRecordId ??
                  (opts?.isPlaying === true
                    ? (opts?.activeCueRecordId ?? null)
                    : null);
                const sessionCueKeypoints =
                  inPlaybackSession && sessionCueRecordId
                    ? focusKeypointsForRecordId(sessionCueRecordId)
                    : null;
                // playbackEmphasis 전달용은 실재생 중만 유지 — belle "크게 보니까
                // 진하기는 적당" = emphasis 강도(1.3배) 무변경이고, 음성 정지 중
                // 승인 dim·펄스 렌더에는 배율을 얹지 않는다.
                const playingInversion = opts?.isPlaying === true;
                return (
                  <KeypointOverlay
                    player={player}
                    keypointReport={userKeypointReport}
                    videoSize={overlayVideoSize}
                    // 33-13 (A-6, D-13) — 이 레이어 자체는 상시(visible): 음성 큐
                    // dim/강조가 여기 얹힌다. 추적 스켈레톤은 토글(기본 숨김).
                    visible={true}
                    // quick-260807-k70 (BELLE-0807-9) — 재생 세션 중 축 폴리라인·
                    // 본·흰 점·회색 점 전부 숨김 (토글 ON 이어도 — 토글은 정지
                    // 상태 표시 담당으로 강등). 세션 밖 = 현행 overlayVisible.
                    skeletonVisible={inPlaybackSession ? false : overlayVisible}
                    // 33-G F-8 (quick-260730-szk, D-42) — 감점 마커 계층은 상시가
                    // 아니다: 스켈레톤 토글 ON 또는 음성 큐 강조 중에만. 상시 진입점
                    // 은 아래 부위 칩이 대체한다. `focusKeypoints`(강조)·dim 은 이
                    // 게이트와 무관 — D-42 가 음성 큐 강조는 유지하라고 명시했다.
                    // quick-260807-k70 (BELLE-0807-9) — 세션 중엔 활성 큐 record
                    // 가 있을 때만 게이트를 연다 (큐 부위 빨간 점 — 없으면 점 0).
                    // 세션 밖 가지 overlayVisible 은 현행식의 축약 동치 (세션
                    // 밖에선 voiceCue null·isPlaying false 라 나머지 절 소거).
                    markersVisible={
                      inPlaybackSession
                        ? sessionCueRecordId != null
                        : overlayVisible
                    }
                    // 33-13 — record 보유 doc 은 각도편차(>20°) 폴백 강조 차단
                    // (record 와 짝 없는 고아 빨강 마커 금지, D-18). jointAngles 는
                    // 폴백 강조 산출 전용이라 미전달로 충분. legacy 는 기존 유지.
                    // quick-260807-k70 (BELLE-0807-9) — 세션 중 legacy 편차 폴백
                    // 빨강도 억제 (규칙 일관: 세션 중 빨강 = 활성 큐 부위뿐).
                    jointAngles={
                      inPlaybackSession
                        ? undefined
                        : hasBreakdownRecords
                          ? undefined
                          : userJointAngles
                    }
                    // #3 (2026-06-21) — 결함 keypoint 권위 강조. quick-260704-fz4:
                    // 소스를 vetoFaultJoints 단독 → confirmedKeypoints(감점 근거
                    // records ∪ vetoFaultJoints) 단일 조립으로 확장 — 표·마커·카드
                    // 가 같은 "빨강=확정 감점" 소스를 쓴다. 비면 기존 각도편차
                    // 폴백 (무회귀).
                    // IN-01 (quick-260724-q6b) — 역립 저신뢰 시 확정 빨강 점 제거
                    // (overlayHighlightKeypoints=[]) + 예상 주황 점 최대 1개로 강등.
                    // quick-260807-k70 (BELLE-0807-9) — 세션 중엔 활성 큐 record
                    // 투영 부위만 빨강 (focusKeypointsForRecordId 경유 — IN-01
                    // 저신뢰 doc 의 음성/큐 표면 허용은 fpw 정책 자동 계승).
                    highlightKeypoints={
                      inPlaybackSession
                        ? (sessionCueKeypoints ?? [])
                        : overlayHighlightKeypoints
                    }
                    // quick-260704-fz4 — 측정 초과·확인 권장(주황, 감점 아님) 마커.
                    // 표·확대 카드와 동일 단일 소스(attentionKeypoints memo).
                    // IN-01 — 역립 저신뢰 시 estimatedAreaKeypoints(최대 1개)로 치환.
                    // quick-260807-k70 — 세션 중 주황 억제 (지금 말하는 부위만).
                    attentionKeypoints={
                      inPlaybackSession ? [] : overlayAttentionKeypoints
                    }
                    // quick-260705-r6v — 스플릿(다리 4관절) 그룹 마커: 멤버 centroid
                    // 1점 + 번호. 영상 위 텍스트 pill 은 전면 제거(여백 범례/시트로
                    // 이동). 사용자 측만 전달 (정은지 측 무변경).
                    // IN-01 — 역립 저신뢰 시 빈 배열(번호 단정 제거).
                    // quick-260807-k70 — 세션 중 그룹 경계 억제 (정지 상태 전용).
                    groupMarkers={inPlaybackSession ? [] : overlayGroupMarkers}
                    // quick-260705-o0s — 감점 record 관절 번호 점 ('점수 계산 내역'
                    // 행 번호와 buildDeductionMarkers 단일 소스 — 항상 일치).
                    // IN-01 — 역립 저신뢰 시 빈 객체(번호 단정 제거).
                    // quick-260807-k70 — 세션 중 번호 억제 (정지 상태 전용).
                    markerNumbers={inPlaybackSession ? {} : overlayMarkerNumbers}
                    // quick-260705-r6v — 번호 점 탭 → 드릴다운 시트 (진입점 3).
                    // 전체화면(opts.sizeScale 존재)에선 시트가 중첩 Modal 이 되므로
                    // 콜백 미전달 — 전체화면 점 탭은 여백 범례가 대체(iOS 함정 회피).
                    onMarkerPress={
                      opts?.sizeScale ? undefined : openRecordByNumber
                    }
                    // Phase 20 (UI ②) — faultJoints 가 없을 때(매핑 0/legacy)만 폴백:
                    // 임계(20°) 넘는 관절이 없으면 편차 최대 2개 강제 강조 (마커 0개 모순 제거).
                    // 정타 영상은 0 → 오탐 0.
                    // IN-01 — 역립 저신뢰 시 0 (강제 강조 폴백 억제).
                    // quick-260807-k70 — 세션 중 0 (강제 강조도 큐 부위 규칙 밖).
                    forceHighlightWorstCount={
                      inPlaybackSession ? 0 : overlayForceHighlightWorstCount
                    }
                    // quick-260702-t0v — 가로 전체화면 뷰어가 opts.sizeScale=2.0 전달
                    // (각도 라벨 가독). 세로 카드는 opts 미전달 → 1 (무회귀).
                    sizeScale={opts?.sizeScale ?? 1}
                    // belle 08-07 (quick-260807-iwp, BELLE-0807-7) — "마커는 좀 더
                    // 진하면 좋을 듯": 재생 중에만 관절 점 크기·외곽선 강화. 음성
                    // 멈춤 중(isPlaying=false)·정지 상태는 false 라 승인 렌더
                    // (dim·펄스·번호 마커) byte 보존. 기준(우) 패널은 미전달.
                    playbackEmphasis={playingInversion}
                    // 33-13 (A-6, D-13 대표 UX) — 음성 큐 동안 해당 record 부위
                    // 강조 (VideoCompare 가 발화 recordId 를 opts 로 전달). 짝
                    // 없으면 빈 배열 = 강조 0 (고아 가드). voiceCueRecordId 는
                    // 음성 멈춤/발화 중에만 non-null → 재생 중 dim·펄스 미발동
                    // 자동 보장 (belle 08-07 #4 — prop 무변경).
                    focusKeypoints={
                      opts?.voiceCueRecordId
                        ? focusKeypointsForRecordId(opts.voiceCueRecordId)
                        : undefined
                    }
                  />
                );
              }}
              rightOverlay={(player, opts) => {
                // quick-260807-k70 (BELLE-0807-9) — 기준(우) 패널도 재생 세션 중
                // 스켈레톤 숨김. belle "동그라미가 너무 크니까 보기 힘들다"의
                // 표면은 양 패널이고, 정책 문언 "기본 관절 점·스켈레톤 표시를
                // 숨기고"는 무한정 — 기준 패널은 세션 중 점 0. 판정식은
                // leftOverlay 의 inPlaybackSession 과 **동일 식** (규칙 두 벌
                // 금지 — render prop 스코프가 달라 같은 식을 인라인 재계산).
                // 큐 record 투영 빨강은 학생 결함이라 좌측만 (fpw 관례 유지).
                // mode3 는 null 그대로 — 자동 무접촉.
                const inSession =
                  opts?.isPlaying === true || opts?.voiceCueRecordId != null;
                return cmp.mode === 'mode1' ? (
                  <KeypointOverlay
                    player={player}
                    keypointReport={referenceKeypointReport}
                    videoSize={overlayVideoSize}
                    visible={inSession ? false : overlayVisible}
                    // quick-260702-t0v — 전체화면 sizeScale 전달 (정은지 측 동일).
                    sizeScale={opts?.sizeScale ?? 1}
                  />
                ) : null;
              }}
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
              // belle 08-07 (quick-260807-iwp) — 음성 멈춤 동안 기준 패널 짝 프레임
              // 스냅 맵 (recordId → refVideoSec). 짝 없는 record 는 맵 미등재 =
              // 스냅 생략. cleanPass/legacy 면 빈 맵 (동작 diff 0).
              cueRefSnapSecs={cueRefSnapSecs}
              // 32-12 (D-18 B안) — coachAudio mp3 준비 doc 에서만 오디오 토글·재생
              // 활성(cueId=recordId 조인). failed/legacy 면 undefined → 자막만.
              audioAnalysisId={coachAudioAnalysisId}
              // belle 09-07 — 기준(우) 패널의 "짝을 못 찾았어요" 정직 문구를 켜는
              // 유일한 신호. 라벨 문자열로 모드를 추정하지 않는다(라벨은 표시 카피).
              compareMode={cmp.mode}
              // belle 09-07 — 시트 보조 버튼이 부를 명령 손잡이. VideoCompare 가
              // 자기 렌더에서 최신 핸들러를 꽂아 준다(이 가지가 그려질 때만).
              openFullscreenAtRef={openFullscreenAtRef}
            />
            </>
            )}
            {/* belle 09-09 — 부위 칩 행(33-G S3/F-8)과 legacy 재분석 유도 배너
                (28-CONTEXT D-05)를 여기서 걷어냈다. 시안 2 의 동작비교는 영상·컨트롤·
                옵션·감점 목록 넷뿐이고, 두 표면 모두 시안이 대체했다:
                  · 부위 칩 = 감점 항목으로 들어가는 진입점 → 감점 목록 행이 대체
                    (행이 초까지 들고 있어 더 낫다)
                  · 재분석 유도 = 보완운동 탭의 '다시 분석' 버튼이 대체
                감점 목록 행 탭이 부위 칩과 **같은 시트**(setDetailRecordIndex)를 여니
                잃는 경로가 없다. */}
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

        {/* IN-01 (quick-260724-q6b) — 역립 저신뢰 시 확대비교 진입점. topFix 카드·
            '다른 감점 항목' 목록이 억제돼(아래 !attributionUnreliable 게이트) 확대비교가
            도달 불가한 gap 을 메운다 (belle 07-24: "예상 부위라도 보여줘야").
            quick-260903-ftg (09-03 시뮬 실측, belle pdshape 60점 doc): 확정 카드가
            2장(왼팔꿈치·왼엉덩이)인데 종전 링크 1개는 |points| 최대 record 의 시트만
            열어 두 번째가 도달 불가였다 (belle 09-02 "왜 확대비교 사진이 하나밖에
            없어"). 지금은 확정 카드 **전부**를 "예상 부위 (참고)" 사진 카드로 인라인
            렌더한다 — 선택 규칙은 selectEstimatedZoomEntries 단일 지점.
            IN-01 락 유지(260724-q6b): 카드에 관절명·statusLine·감점 수치 없음 — 제목은
            시트 제목과 문자 동일한 hedge 라벨 1줄뿐. 탭 = 종전과 같은 시트(estimatedArea
            hedge). 매칭 카드 0 + pending 이면 placeholder 카드 1개(done 도착 시 onSnapshot
            으로 사진 카드로 교체), 둘 다 아니면 미렌더(빈 시트 열지 않음) — 안내줄 +
            정은지 비교는 그대로. false/부재 시 diff 0. */}
        {attributionUnreliable && estimatedZoomEntries.length > 0 ? (
          estimatedZoomEntries.map((entry) => (
            <Pressable
              key={zoomCardKey(entry.zoom)}
              onPress={() => setDetailRecordIndex(entry.recordIndex)}
              accessibilityRole="button"
              accessibilityLabel={ATTR_ZOOM_ESTIMATED_ENTRY_LABEL}
              hitSlop={8}
              style={({ pressed }) => [
                styles.estimatedZoomCard,
                pressed && styles.estimatedZoomEntryPressed,
              ]}
            >
              <View style={styles.estimatedZoomTitleRow}>
                <Text style={styles.estimatedZoomEntryText}>
                  {ATTR_ZOOM_ESTIMATED_CARD_TITLE}
                </Text>
                <Text style={styles.estimatedZoomEntryChevron}>›</Text>
              </View>
              <ZoomCompositeImage
                imageUrl={resolveZoomImageUrl(entry.zoom, freshZoomUrls)}
                rightLabel={
                  cmp.mode === 'mode1' ? `${cmp.athleteName} 선수` : '지난 영상'
                }
                onError={onZoomImageError}
                accessibilityLabel={`${ATTR_ZOOM_ESTIMATED_CARD_TITLE} 확대 비교 이미지`}
              />
            </Pressable>
          ))
        ) : attributionUnreliable &&
          zoomPending &&
          estimatedAreaRecordIndex != null ? (
          <Pressable
            onPress={() => setDetailRecordIndex(estimatedAreaRecordIndex)}
            accessibilityRole="button"
            accessibilityLabel={ATTR_ZOOM_ESTIMATED_ENTRY_LABEL}
            hitSlop={8}
            style={({ pressed }) => [
              styles.estimatedZoomCard,
              pressed && styles.estimatedZoomEntryPressed,
            ]}
          >
            <View style={styles.estimatedZoomTitleRow}>
              <Text style={styles.estimatedZoomEntryText}>
                {ATTR_ZOOM_ESTIMATED_CARD_TITLE}
              </Text>
              <Text style={styles.estimatedZoomEntryChevron}>›</Text>
            </View>
            <ZoomCompositeImage
              pending
              rightLabel={
                cmp.mode === 'mode1' ? `${cmp.athleteName} 선수` : '지난 영상'
              }
            />
          </Pressable>
        ) : null}

          </>
        )}
        {resultTab === 'points' && (
          <>
          {/* ── 시안 3 (교정포인트) — 기준 점수 100 → 펼침 행 → 종합 N점 ────────
              값은 '점수 계산 내역'과 같다(기준 100 에서 감점을 빼 종합). 시안이 더한
              것은 행을 펼쳤을 때의 확대 짝 사진과 왜 감점인지 문장뿐이다. */}
          <ResultPointsCard
            baselineText="100"
            rows={pointRows}
            totalText={`${Math.round(result.overallScore)}점`}
            expandedId={expandedPointId}
            onToggle={(id) =>
              setExpandedPointId((cur) => (cur === id ? null : id))
            }
            onImageError={onZoomImageError}
          />
          {/* 유지된점 — 백엔드 summaryPraise 단일 원천(사람 말, 수치 미포함).
              없으면 박스도 없다 — 잘한 점을 지어내지 않는다. */}
          {result.summaryPraise?.headline ? (
            <View style={styles.keptBox}>
              <Text style={styles.keptTitle}>유지된점</Text>
              <Text style={styles.keptBody}>{result.summaryPraise.headline}</Text>
            </View>
          ) : null}
          {/* 시안 3 CTA — 디자이너 확인(2026-09-08): 이걸 누르면 교정포인트2 화면이
              나온다. 첫 항목부터 1/N 페이징으로 넘긴다. */}
          {pointRows.length > 0 ? (
            <Pressable
              onPress={() => setPointModalIndex(0)}
              accessibilityRole="button"
              accessibilityLabel="교정 방법 자세히 보기"
              style={({ pressed }) => [
                styles.pointsCta,
                pressed && styles.pointsCtaPressed,
              ]}
            >
              <Text style={styles.pointsCtaText}>교정 방법 자세히 보기 &gt;</Text>
            </Pressable>
          ) : null}


          {/* ── 시안에 자리가 없지만 남기는 정직 표면 3개 (belle 09-09 판정) ────────
              belle: "중복만 없애고 정직 표면 3개는 남김". 시안이 대체한 것(점수 맥락
              카드·기존 요약 카드·나머지 감점 목록·오늘 고칠 것·점수 계산 내역·코칭 팁·
              기준 모션 메타·콤보 부분 점수)은 **전부 삭제**했다 — 시안은 중복을 덜어낸
              결과물이라 그 앞에 옛 목차를 끼워 두면 시안을 되돌리는 것이다.
              남기는 셋은 시안이 대체하지 않았고, 없으면 화면이 사용자에게 거짓이 된다:
                · 정확도 제한 배지 — 합성이 실패한 분석을 성공처럼 보이게 두지 않는다
                · 커버리지 갱 고지 — 못 잰 부분이 있는데 다 쟀다고 말하지 않는다
                · 강사 보조 1줄 — AI 가 강사를 대체하지 않는다는 포지셔닝(Phase 11 D-07)
              자리는 이 탭 맨 아래 — 시안 프레임 밖이라 조판을 건드리지 않는다. */}
          <AccuracyLimitBadge
            visible={hasSynthesisWarning(result, 'ai_synthesis_failed')}
          />
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
          <Text style={styles.coachPositioning}>
            이 분석은 강사 지도를 돕는 참고예요.
          </Text>

          </>
        )}
        {resultTab === 'exercise' && (
          <>
          {/* ── 시안 4 (보완운동) — 운동 카드 + 강사에게 확인할 점 + 다시분석/공유 ──
              내용은 전부 doc 저장값이다: 운동 = result.recommendedExercises(백엔드
              exercise_map 산출), 질문 = result.coachQuestions(D-28). 없으면 그 카드를
              그리지 않는다. 아래에 기존 상세 섹션(성장·심사 코너·참고코너)이 이어진다. */}
          <ResultExerciseTab
            exercises={result.recommendedExercises ?? []}
            // 기존 섹션과 **같은 소스**. result.coachQuestions 가 없는 doc 은
            // legacy 폴백(openQuestionsForCoach)이 채우고 사용자가 담은 질문도
            // 합쳐진다 — 두 표면이 다른 질문을 보여주면 안 된다.
            questions={autoQuestions}
            onSeeAllExercises={() => setExerciseModalOpen(true)}
            onReanalyze={() => router.replace('/(tabs)/analyze')}
            shareMessage={shareMessage}
          />

          </>
        )}
      </ScrollView>
      <ResultHeaderBar
        title="분석결과"
        tabs={RESULT_TABS}
        activeKey={resultTab}
        onTabPress={(k) => setResultTab(k as ResultTabKey)}
        onBack={() => router.back()}
      />
      {/* (구 DimensionDetailModal 제거 — D-03/D-12. 차원 세부 점수 모달 폐기.) */}
      {/* Phase 12.5 T9: 코칭 팁 "자세히 ›" 모달. tip=null 시 닫힘. */}
      {/* 시안 5 (교정포인트2) — 교정포인트 탭 CTA 로 열린다(디자이너 확인 2026-09-08). */}
      <ResultPointModal
        visible={pointModalIndex != null}
        index={pointModalIndex ?? 0}
        pages={pointPages}
        onIndexChange={setPointModalIndex}
        onClose={() => setPointModalIndex(null)}
        onSeeExercises={() => {
          setPointModalIndex(null);
          setResultTab('exercise');
        }}
        onImageError={onZoomImageError}
      />
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
        // quick-260802-tie — 기준 패널에 표시가 하나도 안 그려진 카드는 그렇다고
        // 말한다(카드는 그대로 둔다 — 사진은 여전히 정보다). 백엔드 인증값만 본다:
        // `=== false` 로 좁혀 **부재(legacy/advisory)는 종전대로 무문구**.
        refUnmarked={sheetPrimaryZoom?.refMarked === false}
        // quick-260903-upx — 학생 패널 표시 생략 카드 (userMarked===false). 부재=종전.
        userUnmarked={sheetPrimaryZoom?.userMarked === false}
        // IN-01 (quick-260724-q6b) — 역립 저신뢰 시 크롭 위 "예상 부위" 배지 (확정
        // 결함 아님). 크롭·수치·비교는 유지 (시트가 라벨 소유).
        estimatedArea={attributionUnreliable}
        // quick-260824-q6p — 7일 넘은 doc 의 확대 이미지 재발급 맵 + 로드 실패
        // 재발급 트리거. 부재/실패 = 종전 저장 imageUrl 폴백 (fail-closed).
        freshZoomUrls={freshZoomUrls}
        onZoomImageError={onZoomImageError}
        // 29-CONTEXT D-06 — mode3 드릴다운 비교 라벨도 지난/이번 계열 (정은지 미언급).
        rightLabel={cmp.mode === 'mode1' ? `${cmp.athleteName} 선수` : '지난 영상'}
        // belle 09-07 — 상시 열려 있는 확대 진입점. **VideoCompare 가 안 그려지는
        // 가지에서는 버튼 자체를 내보내지 않는다**. 눌러도 아무 일이 없는 버튼을
        // 놓지 않기 위해서다(openFullscreenAtRef 가 null 이면 옵셔널 체이닝이
        // 조용히 삼켜 시트만 닫힌다).
        //
        // 그런 가지가 둘이다 — 종전에는 첫째만 막고 있었다(belle 09-07 감사 수리):
        //   1) 합성 비교 영상 가지: 두 패널이 한 mp4 에 구워져 학생 도메인 초가
        //      없고(freezes[].outSec 는 출력 영상 시계다) ref 도 안 꽂힌다.
        //   2) mode3 첫 분석: 비교 대상이 없어 **섹션 전체가 미렌더**다(D-07,
        //      아래 `!(cmp.mode === 'mode3' && cmp.isFirst)` 게이트). 그런데
        //      momentTargets 는 atVideoSec 만 있으면 목표를 만들어 버튼이 활성으로
        //      그려졌다 — 누르면 시트만 닫히고 끝.
        onOpenMoment={
          (renderedCompareReady && !renderedUnavailable) ||
          (cmp.mode === 'mode3' && cmp.isFirst)
            ? undefined
            : openMomentForRecord
        }
        momentRecordId={sheetMomentRecordId}
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
  // belle 09-08 — 점수 원은 곡선 헤더에 걸치는 요소라 가운데 정렬만 한다
  // (세로 위치는 contentContainerStyle 의 paddingTop 이 정한다).
  dialWrap: { alignItems: 'center' },
  // 시안 3 — '유지된점' 박스 (실측 #EDF6F2) 와 그 아래 CTA.
  keptBox: {
    backgroundColor: colors.resultKeptBg,
    borderRadius: radius.resultBox,
    paddingVertical: 16,
    paddingHorizontal: 20,
    alignItems: 'center',
  },
  keptTitle: {
    ...typography.resultWarnTitle,
    color: colors.resultCoachGreen,
  },
  keptBody: {
    ...typography.resultSub,
    color: colors.textMid,
    textAlign: 'center',
    marginTop: 6,
  },
  pointsCta: {
    alignSelf: 'center',
    height: 40,
    paddingHorizontal: 24,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pointsCtaPressed: { opacity: 0.85 },
  pointsCtaText: { ...typography.resultChip, color: colors.textWhite },
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
  // (구 scoreCaption 제거 — quick-260831-lcc. "100점은 잘 나오지 않아요" 의미는
  //  JUDGE_SIM_DISCLAIMER 통합 면책에 병합.)
  // 29-CONTEXT D-05 — mode3 한계 고지 독립 1줄 (breakdown 부재 경로). caption 톤,
  // 토큰만 (하드코딩 금지). breakdown 경로는 ScoreBreakdownSection footnote 사용.
  // 33-15 (D-17) — 좌우 여백 통일: 최상위 텍스트 블록의 임의 paddingHorizontal 4
  // 제거 — 좌우 가장자리는 content 의 spacing.screenX 단일 기준.
  mode3LimitNotice: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  // IN-01 (quick-260724-q6b) — 역립 저신뢰 예상 부위 카드. advisoryOrange 톤
  // (확정 결함 아님 — "예상" 강조), 신규 색 금지. 토큰만.
  // quick-260903-ftg — 링크 1줄 → 제목 행 + 합성 PNG 인라인 카드. 카드 간 간격은
  // content 의 gap(14) 이 준다(종전 marginTop 4 제거).
  estimatedZoomCard: {
    backgroundColor: colors.advisoryOrangeBg,
    borderRadius: radius.card,
    padding: spacing.cardPadding,
    gap: 10,
  },
  estimatedZoomTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
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
  // quick-260831-lcc (빨강 규율) — refCard 중립화: 상세 영역의 참고 메타 카드라
  // 브랜드 톤 강조를 제거 (brandTint/brand → cardBg/divider, 기존 토큰 범위).
  refCard: {
    alignItems: 'flex-start',
    gap: 6,
    backgroundColor: colors.cardBg,
    borderColor: colors.divider,
  },
  refHead: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  refAthlete: { ...typography.boxLabel, color: colors.textPrimary },
  refLevel: {
    ...typography.captionSmall,
    color: colors.textMid,
    backgroundColor: colors.softBg,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
    overflow: 'hidden',
  },
  refName: { ...typography.listTitle, color: colors.textPrimary },
  refDesc: { ...typography.caption, color: colors.textSecondary, marginTop: 2 },
  // (구 refNote 제거 — quick-260831-lcc. "하나의 참고" 의미는 상단 면책 1줄
  //  coachPositioning 이 유일본.)
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
  // (구 exerciseNeutral 제거 — belle 2026-08-31 빈 상태 규칙. 빈 상태 가지 소멸.)
  // (구 vetoLeadCard 제거 — quick-260831-lcc 빨강 규율. veto LEAD 카드 해체 후
  //  유일 사용처였던 growth coachCard 가지도 중립 카드(styles.coachCard)로 전환.)
  // quick-260704-fwb → quick-260831-lcc — '가능한 원인' 블록 (veto 카드 해체 후
  // topFix 직하 중립 카드로 이동. vetoFixLine/vetoLeadNote 는 복제라 제거).
  rootCauseCard: { marginTop: 10 },
  vetoCauseLabel: { ...typography.boxLabel, color: colors.textPrimary },
  vetoCauseItem: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
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
  // quick-260831-lcc — 코칭 팁 반복 면책 통합 1줄 (보조 톤, 토큰만).
  tipMergedDisclaimer: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  // quick-260901-wbo — 코칭 작성 중 placeholder 카드 (zoom placeholder 시각 문법
  // 미러 — ActivityIndicator brand + 보조 톤 카피. 토큰만, 하드코딩 색 금지).
  coachPendingCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    paddingVertical: 24,
  },
  coachPendingText: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
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
  // 7. 보완 운동 — 우회 카드 + 가로 스크롤.
  // quick-260831-lcc (빨강 규율) — 안내 카드는 중립 톤 (brandTint/brand →
  // softBg/기본 divider 테두리·textPrimary).
  detourCard: {
    alignItems: 'flex-start',
    gap: 6,
    backgroundColor: colors.softBg,
  },
  detourHeadline: { ...typography.boxLabel, color: colors.textPrimary },
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
  // quick-260831-lcc — styles.card 의 alignItems:'center' 가 행을 내용 폭으로
  // 수축시켜 "심사 환산 점수80점" 붙음이 생겼다(before-screens/12 실측).
  // alignSelf:'stretch' 로 행이 카드 전폭을 쓰게 해 라벨 좌 / 값 우 분리.
  judgeRow: {
    alignSelf: 'stretch',
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
  // (구 judgeReason 제거 — quick-260831-lcc. whyLine 재출현은 DeductionCard·
  //  드릴다운 시트가 유일본.)
  // 33-15 (D-16) — 감점 수치 listTitle → metricNumber 강등 (수치는 근거, 헤드라인 아님).
  judgeDeduction: { ...typography.metricNumber, color: colors.brand },
  judgeTotalRow: {
    alignSelf: 'stretch',
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
