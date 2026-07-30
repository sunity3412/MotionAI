// Phase 12 Wave 2 (Plan 12-03 T1) — 영상 위 키포인트 오버레이 (frame sync).
//
// 책임 (Wave 2):
//   - body keypoint (joints 배열 파생 — legacy 8: 좌우 어깨/엉덩이/무릎/손,
//     32-14 확장 12: +좌우 발목/팔꿈치) + axisData polyline 렌더
//   - player prop 전달 시 useEvent(player, 'timeUpdate') 로 frame index 자동 산출.
//     player 미전달 시 props.frameIndex (default 0) 의 정적 렌더 (Wave 1 호환).
//   - jointAngles prop 으로 current/target 받아 delta ≥ deltaThresholdDeg 강조.
//     Phase 20 (UI A2): pill/글자 확대 + 흰 외곽선으로 가독성 개선.
//     quick-260705-r6v: 영상 위 텍스트 pill(행동 지시 라벨) 전면 제거 — Tempo 공식
//     문서("폼 피드백 상시 노출은 demoralizing") 계열 UX. 재생 중엔 번호 점만 두고
//     행동 문구는 위 검은 여백 고정 범례/드릴다운 시트로 옮긴다(result.tsx 소비).
//     jointAngles 는 강조 산출 전용으로 유지.
//   - groupMarkers: 관절명 없는 vision record(스플릿 → 다리 4관절)를 멤버 centroid
//     1점으로 표시("번호 다 1" 해소). onMarkerPress: 번호 점 탭 → 드릴다운 시트.
//   - keypointReport 미가용 시 null return → caller 가 placeholder 표시 (D-12-U6)
//
// quick-260730-szk (33-G S1/S2/S19/F-8 — 승인 목업 7R 대조 수리):
//   - 음성 큐 강조가 **부위 원 하나**였다(S19 FAIL). 승인본 `.legfx` 는 kp 게이트를
//     통과하면 **사지 모양 선**(가시 구간만), 미달이면 **부위 원**이고 둘 다 1.4초
//     주기로 깜빡인다. 형태 분기 규칙 = `lib/focusShape`(순수), 여기선 좌표 환산·드로잉.
//   - 감점 마커를 **부위 단위 그룹 1경계**로 통일 (2R#1 "동그라미가 7개"). 그룹에
//     흡수된 관절은 개별 강조 원·번호를 렌더하지 않는다 (N-4).
//   - 참고(advisory) 그룹은 점선 경계 (승인본 `.mkg.adv`).
//   - `markersVisible` 신설 (F-8/D-42) — 상시 마커 제거. 마커 계층은 스켈레톤 토글
//     ON 또는 음성 큐 강조 중에만. 숨김 시 탭 타깃도 0 (N-15).
//
// MVP 단순화 (R5 iter-2 정합): delta 강조 = 영상 전체 대표 편차. jointAngles =
// JointScore 의 평균 currentAngle/targetAngle 입력. frame-level delta + DTW
// alignment 는 v2 (12-deferred-items.md 박제).
//
// 좌표계 약속 (Wave 0B KeypointReport schema §9.12):
//   - keypointReport.data = flat T × joints.length × 2 (8 legacy | 12 32-14),
//     image normalized 0..1 — joints 배열이 capability source (하드코딩 8 금지)
//   - keypointReport.axisData = flat T × 3 × 2, shoulder_mid / hip_mid / knee_mid?
//   - keypointReport.axisMask[idx*3 + 2] === false → polyline 2-point (knee_mid 생략)
//   - UI 단 좌표 산출 절대 X (백엔드 산출만 read, D-12 §12 안티 패턴)
//
// 토큰만 사용 (CLAUDE.md §4 / D-12-U5). brand #FF4B33 변경 0.

import React, { useEffect, useMemo, useRef } from 'react';
import { Animated, Easing, Pressable, StyleSheet, View } from 'react-native';
import Svg, {
  Circle,
  Ellipse,
  G,
  Line,
  Polyline,
  Rect,
  Text as SvgText,
} from 'react-native-svg';
import { useEvent } from 'expo';
import type { VideoPlayer } from 'expo-video';
// quick-260731-2jt (P-12, 2단위 이월) — 이 파일의 흰색 hex 리터럴 11곳을
// `colors.textWhite` 로 일괄 교체했다. 값이 토큰과 문자 그대로 같아 렌더 결과는
// 불변이고(app/CLAUDE.md 하드코딩 금지 정합), 형태·pulse·게이트 로직은 무접촉이다.
// 잔여: `rgba(0,0,0,0.6)`(저신뢰 원 외곽) 은 대응 알파 토큰이 없어 유지 —
// 알파 토큰 신설은 수리 사이클 밖(새 범위 금지).
import { colors } from '../theme';
import { PULSE_PERIOD_MS, buildFocusShapes } from '../lib/focusShape';
import type { KeypointName, KeypointReport } from '../types/analysis';

// D-12-C3 갱신 (#2) — IPSF 채점 허용오차(dimensions.py _LINE_TOL_DEG = 20°)와 동일 값으로 정합.
// 감점에 기여한 관절에만 강조 → '100점인데 빨강' 신뢰 모순 제거. (구 10° = early attention rationale 폐기)
export const KEYPOINT_DELTA_HIGHLIGHT_DEG = 20.0;

// 12-deferred §12-D — confidence 미만이면 회색 stroke + dashed line.
// 사용자 혼동 방지 (occluded keypoint 가 정상과 같은 표시였던 finding 박제).
export const KEYPOINT_LOW_CONFIDENCE_THRESHOLD = 0.5;

// Wave 2 (Plan 12-03 T1) — KeypointName → JointScore.key 매핑.
// 손은 시각 keypoint, elbow 는 kismam angle key (delta 산출 source).
// 어깨/엉덩이/무릎 = 1:1, 손 = elbow 로 reuse (v1, wrist 신설 v2).
// [32-14 D-22 1단] 신규 4관절(ankle/elbow keypoint)은 null — 각도 delta 강조
// 배선 없음(표시 전용 점). ankle 각은 kismam 에 없고, elbow 각의 시각 proxy 는
// legacy 손 매핑 유지(이중 강조 방지). 감점 편입(2단) 게이트 후 재검토.
const JOINT_KEY_TO_ANGLE_KEY: Record<KeypointName, string | null> = {
  left_shoulder: 'left_shoulder',
  right_shoulder: 'right_shoulder',
  left_hip: 'left_hip',
  right_hip: 'right_hip',
  left_knee: 'left_knee',
  right_knee: 'right_knee',
  left_hand: 'left_elbow',
  right_hand: 'right_elbow',
  left_ankle: null,
  right_ankle: null,
  left_elbow: null,
  right_elbow: null,
};

// UI-SPEC §5 + RESEARCH §Code Examples §1. 8 bone (32-14: 신규 4관절은
// 점만 렌더 — bone 확장은 2단 게이트 후 재검토).
// shoulder ↔ shoulder, hip ↔ hip, shoulder ↔ hip (좌/우), hip ↔ knee (좌/우),
// shoulder ↔ hand (좌/우).
const BONES: readonly [KeypointName, KeypointName][] = [
  ['left_shoulder', 'right_shoulder'],
  ['left_shoulder', 'left_hip'],
  ['right_shoulder', 'right_hip'],
  ['left_hip', 'right_hip'],
  ['left_hip', 'left_knee'],
  ['right_hip', 'right_knee'],
  ['left_shoulder', 'left_hand'],
  ['right_shoulder', 'right_hand'],
];

// Wave 1/2/UI-SPEC 단일 잠금 contract (B3 iter-4 박제).
// Wave 1 = player 생략 + frameIndex 명시 (정적).
// Wave 2 = player 전달 + frameIndex 생략 (component 내부 useEvent 산출).
export type KeypointOverlayProps = {
  /** Wave 2 박제 — 공급 시 component 내부 useEvent('timeUpdate') 가 frame index 자동 산출. */
  player?: VideoPlayer | null;
  /** 사용자 또는 reference 영상의 KeypointReport (Wave 0B schema). null = 미가용. */
  keypointReport: KeypointReport | null;
  /** 비디오 native size — viewBox 산출 (예: { width: 720, height: 1280 }). */
  videoSize: { width: number; height: number };
  /** 토글 OFF 시 SVG 렌더 0 (성능 절약, D-12-C4). */
  visible: boolean;
  /** Wave 1 = 0 (정적), Wave 2 = 생략 (component 내부 산출). */
  frameIndex?: number;
  /** Wave 2 — delta 강조용. JointScore.{currentAngle,targetAngle} 변환. */
  jointAngles?: Record<string, { current: number | null; target: number | null }>;
  /** default 20 (IPSF 허용오차 정합, KEYPOINT_DELTA_HIGHLIGHT_DEG). */
  deltaThresholdDeg?: number;
  /**
   * Phase 20 (UI ②) — 비전 거부권 적용(실제 결함 존재)인데 임계(20°)를 넘는 관절이
   * 0개일 때, 편차가 가장 큰 N개 관절을 강제로 강조한다 (belle: "표기가 하나도 없다").
   * 0(기본) = 강제 강조 없음 = 정타 영상은 기존 >20° 규칙만 (오탐 0).
   */
  forceHighlightWorstCount?: number;
  /**
   * Phase 20 (#3, 2026-06-21) — Gemini 가 식별한 실제 결함 keypoint(backend
   * visionVeto.faultJoints). 제공·비공백이면 이 keypoint 들만 **권위 강조**하고
   * 각도편차(>20°)·worstCount 폴백을 무시한다. 마커가 각도편차 최대 관절(어깨/
   * 팔꿈치)이 아니라 진짜 결함 관절(다리/팔)에 찍히게 하는 fix. 이 영상 joints 에
   * 하나도 없으면(이론상 드묾) 기존 편차/worstCount 폴백으로 진행.
   */
  highlightKeypoints?: readonly KeypointName[];
  /**
   * quick-260704-fz4 — 2단 시각 언어의 2단(주황): 측정 초과·확인 권장 keypoint
   * (windowMedianAngleDeltas 중 |delta|>20° 인데 감점 없는 관절 — 감점 아님, 표시
   * 전용). 마커 점만 advisoryOrange (bone 은 빨강='확정' 의미 보존을 위해 무변경).
   * highlighted(빨강)와 겹치면 확정이 이긴다. 저신뢰(conf<0.5)는 estimateGray 가
   * 우선 (advisory 승격 금지). prop 미전달 시 렌더 diff 0 (하위호환).
   */
  attentionKeypoints?: readonly KeypointName[];
  /**
   * quick-260705-r6v — 관절명 없는 vision record(스플릿 → 다리 4관절)의 그룹 마커
   * (buildDeductionMarkers.groupMarkers). 각 entry 를 멤버 keypoint 들의 현재 frame
   * 위치 산술 평균(centroid) 1점에 강조 원 + 흰 bold 숫자로 렌더한다 → 다리 4관절
   * 4점에 같은 번호를 찍던 "번호 다 1" 혼란 해소. centroid 는 표시 배치용 평균이지
   * 좌표/각도 산출이 아님(D-12 §12 안티패턴 아님 — 백엔드 좌표의 시각 배치).
   * prop 미전달/빈 배열이면 렌더 diff 0.
   */
  /**
   * quick-260730-szk (33-G S1/S2, N-2) — 확장 2필드 (둘 다 optional → 기존 호출 무회귀):
   *   badgeLabel — 한 부위에 감점 2건이면 `2·3` 병합 배지. 미전달 시 `String(number)`.
   *   advisory   — 참고(감점 아님) 그룹이면 점선 경계 + advisoryOrange (승인 목업
   *                `.mkg.adv{border-style:dashed}`). 미전달 = 실선 brand (감점).
   */
  groupMarkers?: {
    number: number;
    keypoints: KeypointName[];
    badgeLabel?: string;
    advisory?: boolean;
  }[];
  /**
   * quick-260705-r6v — 번호 점 탭 콜백 (드릴다운 시트 오픈). 전달 시 SVG 위에 형제
   * 히트 레이어(box-none)를 두고 번호 있는 마커(keypointNumbers 관절 + groupMarkers
   * centroid) 위치에 고정 44pt Pressable 을 배치한다. 미전달 시 렌더 diff 0.
   */
  onMarkerPress?: (markerNumber: number) => void;
  /**
   * quick-260705-o0s — 감점 record 관절의 번호 점 (buildDeductionMarkers.
   * keypointNumbers — 점수 계산 내역 행 번호와 단일 소스). 값이 있는 관절은
   * 빨간 원 중앙에 흰 bold 숫자를 그린다. 키는 caller 가 highlightKeypoints
   * 에도 포함해 전달 (기존 emphasized 분기로 RADIUS_HI 충족 — 오버레이 내부
   * set 재구성 금지, 이중 소스 금지). prop 미전달 시 렌더 diff 0 (하위호환 —
   * Mode3/legacy doc 은 기존 highlightKeypoints/편차 폴백 그대로).
   */
  markerNumbers?: Partial<Record<KeypointName, number>>;
  /**
   * 33-13 (A-6, D-13) — 추적 스켈레톤(전 관절 흰 점 + bone + 축 polyline) 표시 여부.
   * belle: "뭘 잡은거지" — 설명 없는 12점 상시 노출 금지 → 기본 숨김 + 옵트인
   * 토글(result.tsx AsyncStorage). 감점 마커(항목 단위 그룹 경계·번호 점·참고 점)는
   * 이 값과 무관하게 렌더 — 마커는 감점 record 와 양방향 대응(D-18)이라 스스로
   * 답한다. default true (기존 소비처 렌더 diff 0 — reference 측 스켈레톤 소비 등).
   */
  skeletonVisible?: boolean;
  /**
   * quick-260730-szk (33-G F-8, D-42) — **감점 마커 계층**(부위 그룹 경계 + 번호 배지 +
   * 확정/참고 개별 강조 원 + 탭 히트 레이어) 표시 여부. default `true` (기존 소비처
   * 렌더 diff 0).
   *
   * belle 확인 ② 반려 F-8: 종전 `result.tsx` 는 "감점 마커는 skeletonVisible 무관
   * 상시 렌더" 였다 — 결과 화면에 들어오자마자 설명 없는 표시가 영상을 덮었다.
   * D-42 = **상시 마커 제거**. 마커는 스켈레톤 토글 ON 또는 음성 큐 강조 중에만.
   * 상시 진입점은 영상 카드 아래 **부위 칩**(PartChipsRow)이 대체한다.
   *
   * ⚠ `focusKeypoints`(음성 큐 강조)·dim·스켈레톤에는 영향 주지 않는다 — D-42 는
   * 음성 큐 강조를 유지하라고 명시했다.
   */
  markersVisible?: boolean;
  /**
   * 33-13 (A-6, D-13 대표 UX 패턴) — 음성 큐 동안 강조할 부위(해당 큐 record 의
   * 투영 keypoint). 비어있지 않고 고신뢰 멤버가 1개 이상이면 전체 프레임을
   * 어둡게(dim) 깔고 그 부위의 그룹 경계만 강조 렌더한다 (승인 목업 ④ 컷 2 —
   * 음성 중 정지 + 부위 강조). 짝 없는 큐는 caller 가 빈 배열/미전달로 강조 0
   * (D-18 고아 가드). 고신뢰 멤버 0 = 강조 미렌더 (확신 없는 표시는 긋지 않는다).
   */
  focusKeypoints?: readonly KeypointName[];
  /**
   * quick-260702-t0v — 마커/라벨 크기 배율 (default 1 = 기존 렌더와 수치 동일).
   * viewBox "0 0 1 1" 정규화 구조라 모든 크기 상수(라벨 64×26, fontSize 14,
   * 원 반지름 10/14 등)가 렌더 크기에 비례 축소됨 → 세로 카드(높이 ~290pt)에선
   * 유효 폰트 ~3pt 급으로 판독 불가. 가로 전체화면 뷰어가 2.0 을 전달해 각도
   * 라벨 가독을 확보한다. 좌표(positions/axis)는 스케일하지 않음 — 크기만.
   */
  sizeScale?: number;
};

type Point = { x: number; y: number };
type KeypointPoint = Point & { confidence: number };

// frame=0 (또는 prop frameIndex) 의 keypoint 좌표 + confidence reshape (J = joints.length).
// flat array 전체 reshape 회피 — 한 frame 만 slice (T × J × 2 → J point).
// confidence flat array (T × J) 도 동일 frame slice 동시 read (12-deferred §12-D).
function readFramePositions(
  report: KeypointReport,
  frameIdx: number,
): Map<KeypointName, KeypointPoint> | null {
  const T = report.frames;
  const J = report.joints.length;
  if (T <= 0 || J <= 0) return null;
  const idx = Math.min(Math.max(frameIdx, 0), T - 1);
  const base = idx * J * 2;
  const confBase = idx * J;
  if (report.data.length < base + J * 2) return null;
  const hasConf = report.confidence.length >= confBase + J;
  const map = new Map<KeypointName, KeypointPoint>();
  for (let j = 0; j < J; j += 1) {
    const x = report.data[base + j * 2];
    const y = report.data[base + j * 2 + 1];
    if (typeof x !== 'number' || typeof y !== 'number') continue;
    // confidence 누락 frame 은 1.0 (강조 분기 영향 X) 대신 high-conf 가정.
    const c = hasConf ? report.confidence[confBase + j] : 1.0;
    map.set(report.joints[j], { x, y, confidence: typeof c === 'number' ? c : 1.0 });
  }
  return map;
}

// axisData polyline (T × 3 × 2) + axisMask (T × 3) 의 frame=idx 슬라이스.
// knee_mid 미가용 frame 은 mask[idx*3 + 2] === false → 2-point polyline.
type AxisPolyline = { points: Point[]; hasKnee: boolean };

function readFrameAxis(
  report: KeypointReport,
  frameIdx: number,
): AxisPolyline | null {
  const T = report.frames;
  if (T <= 0) return null;
  const idx = Math.min(Math.max(frameIdx, 0), T - 1);
  const baseData = idx * 3 * 2;
  const baseMask = idx * 3;
  if (report.axisData.length < baseData + 6) return null;
  if (report.axisMask.length < baseMask + 3) return null;
  const points: Point[] = [];
  // shoulder_mid
  points.push({
    x: report.axisData[baseData + 0],
    y: report.axisData[baseData + 1],
  });
  // hip_mid
  points.push({
    x: report.axisData[baseData + 2],
    y: report.axisData[baseData + 3],
  });
  // knee_mid (mask 분기)
  const hasKnee = report.axisMask[baseMask + 2] === true;
  if (hasKnee) {
    points.push({
      x: report.axisData[baseData + 4],
      y: report.axisData[baseData + 5],
    });
  }
  return { points, hasKnee };
}

// [fix 2026-07-21] Wave 1(정적) 렌더용 no-op 이벤트 소스 — useEvent 는 1st arg 가
// null 이면 내부 addListener 호출에서 크래시한다. 구독 인터페이스만 흉내내는 상수를
// 모듈 레벨에 두어 참조 안정성(리렌더마다 재구독 방지)도 함께 확보한다.
const NOOP_EVENT_SOURCE = {
  addListener: () => ({ remove: () => {} }),
  removeListener: () => {},
  removeAllListeners: () => {},
  emit: () => {},
  listenerCount: () => 0,
};

export function KeypointOverlay({
  player,
  keypointReport,
  videoSize,
  visible,
  frameIndex: frameIndexProp,
  jointAngles,
  deltaThresholdDeg = KEYPOINT_DELTA_HIGHLIGHT_DEG,
  forceHighlightWorstCount = 0,
  highlightKeypoints,
  attentionKeypoints,
  groupMarkers,
  onMarkerPress,
  markerNumbers,
  skeletonVisible = true,
  markersVisible = true,
  focusKeypoints,
  sizeScale = 1,
}: KeypointOverlayProps) {
  // Hooks 순서 안정성 — early return 전에 모든 hook 호출 (React rules of hooks).
  //
  // Wave 2 frame sync — useEvent(player, 'timeUpdate'):
  //   - player 전달 시 native ~30fps emit (timeUpdateEventInterval=0.033) 으로
  //     currentTime 받아 frame index 산출.
  //   - player 없으면 initial value (0) 만 emit → 정적 렌더 (Wave 1 호환).
  //   - Pitfall 5 우회: initial value = player?.currentTime ?? 0.
  //   - Pitfall 1 (iOS seek bug) 검증 = T4 belle UAT.
  //
  // useEvent 1st arg 타입은 EventEmitter<TEventsMap> — VideoPlayer 가 그 shape
  // 을 구현하지만 expo 의 public 타입에 명시적 변환이 필요. unknown 경유 cast.
  //
  // [fix 2026-07-21] Wave 1(정적, player 미전달) 크래시 — useEvent 는 1st arg 에
  // null 이 오면 내부 addListener 호출에서 죽는다 (Render Error: Cannot read
  // property 'addListener' of null, PoseCompareFrames 정적 소비에서 실측). 문서상
  // "Wave 1 = player 생략" 지원이었지만 실제 정적 소비처가 지금까지 없어 잠복했다.
  // player 부재 시 no-op emitter 를 대신 넘겨 hook 순서를 유지한다 — 이벤트는
  // 오지 않고 initial value 만 쓰이므로 정적 렌더 의미 그대로.
  const timeUpdate = useEvent(
    (player ?? NOOP_EVENT_SOURCE) as unknown as Parameters<
      typeof useEvent
    >[0],
    'timeUpdate',
    { currentTime: player?.currentTime ?? 0 } as Parameters<typeof useEvent>[2],
  ) as { currentTime: number } | null;

  // viewBox 단위 산출 — early return 이전 보호 (videoSize=0 안전).
  const W = Math.max(1, videoSize.width);
  const H = Math.max(1, videoSize.height);
  // Phase 20 (UI A2) — 강조 keypoint 가독성 ↑ (belle: "붉은색이 뭐라고 써있는지
  // 보이지도 않고"). 강조 관절 원을 더 크게(14) + 외곽선 두껍게(2.4) 해서 분주한
  // 영상 위에서도 눈에 띄게. 비강조 원은 기존 10 유지(번잡함 방지).
  //
  // quick-260702-t0v — sizeScale(default 1) 을 화면상 크기를 갖는 모든 정규화
  // 상수에 곱한다. 1 이면 기존과 픽셀 동일(무회귀), 전체화면 뷰어는 2.0.
  const S = sizeScale;
  const RADIUS = (10 * S) / H;
  const RADIUS_HI = (14 * S) / H;
  const STROKE_BASE = (1.8 * S) / H;
  const STROKE_HI = (3 * S) / H;
  const STROKE_CIRCLE_OUTLINE = (1.5 * S) / H;
  const STROKE_CIRCLE_OUTLINE_HI = (2.4 * S) / H;
  // quick-260705-o0s/r6v — 번호 점(keypointNumbers) + 그룹 중점(groupMarkers) 공용
  // 폰트 크기. sizeScale 곱으로 세로 카드/가로 전체화면 동일 규칙 자동.
  const NUM_FONT_SIZE = (13 * S) / H;

  // Wave 2: player 전달 시 useEvent.currentTime → frameIndex 자동 산출.
  // player 없거나 frameIndex prop 명시 시 override.
  //
  // 12-KEYPOINT-DRIFT-ROOT-CAUSE-REVIEW.md Fix A — fps 라벨 drift hotfix.
  //   FfmpegFrameExtractor 의 step 정수 양자화로 keypointReport.fps (target_fps 라벨)
  //   ≠ 실효 fps (src_fps / step). 실효 fps 는 frames / duration 으로 직접 산출.
  //   player.duration 미가용 시 라벨 fallback (Fix B 배포 후 정직 라벨이 채워짐).
  const frameIndex = useMemo(() => {
    if (typeof frameIndexProp === 'number') return frameIndexProp;
    if (!keypointReport || keypointReport.frames < 1) return 0;
    const currentTime = timeUpdate?.currentTime ?? 0;
    const duration = player?.duration ?? 0;
    const effectiveFps = duration > 0
      ? keypointReport.frames / duration
      : (keypointReport.fps > 0 ? keypointReport.fps : 1);
    const idx = Math.floor(currentTime * effectiveFps);
    return Math.min(Math.max(idx, 0), keypointReport.frames - 1);
  }, [frameIndexProp, timeUpdate?.currentTime, keypointReport, player?.duration]);

  const positions = useMemo(
    () =>
      keypointReport
        ? readFramePositions(keypointReport, frameIndex)
        : null,
    [keypointReport, frameIndex],
  );

  const axis = useMemo(
    () =>
      keypointReport
        ? readFrameAxis(keypointReport, frameIndex)
        : null,
    [keypointReport, frameIndex],
  );

  // Wave 1 = jointAngles 미공급 → 빈 Set (highlighted 없음).
  // Wave 2 = jointAngles 받아 delta ≥ deltaThresholdDeg 분기 (D-12-C3).
  //
  // D-12 §12 안티 패턴 가드: props.jointAngles 만 사용. Math.sin/cos/atan2 등
  // UI 단 각도/좌표 산출 0 — backend (kismam) 산출만 read.
  const highlightedJoints = useMemo(() => {
    const set = new Set<KeypointName>();
    if (!keypointReport) return set;
    // #3 (2026-06-21) — Gemini 가 식별한 결함 keypoint 가 있으면 그것만 권위 강조.
    // 각도편차(>20°)·worstCount 폴백을 무시해 마커가 진짜 결함 관절에 찍히게 한다.
    // 이 영상 joints 에 하나라도 있으면 그 set 확정; 하나도 없으면 폴백 진행.
    if (highlightKeypoints && highlightKeypoints.length > 0) {
      for (const kp of highlightKeypoints) {
        if (keypointReport.joints.includes(kp)) set.add(kp);
      }
      if (set.size > 0) return set;
    }
    if (!jointAngles) return set;
    // 임계(20°) 초과 관절 강조 + 편차 수집 (worst-N fallback 용).
    const deviations: { kp: KeypointName; dev: number }[] = [];
    for (const kp of keypointReport.joints) {
      const angleKey = JOINT_KEY_TO_ANGLE_KEY[kp];
      if (!angleKey) continue;
      const pair = jointAngles[angleKey];
      if (!pair) continue;
      const cur = pair.current;
      const tgt = pair.target;
      if (cur == null || tgt == null) continue;
      if (!Number.isFinite(cur) || !Number.isFinite(tgt)) continue;
      const dev = Math.abs(cur - tgt);
      deviations.push({ kp, dev });
      if (dev >= deltaThresholdDeg) {
        set.add(kp);
      }
    }
    // Phase 20 (UI ②) — 거부권 적용인데 임계 초과 관절이 0개면 편차 최대 N개를
    // 강제 강조 (실제 결함이 있는데 마커가 0개인 모순 제거). 정타 영상은
    // forceHighlightWorstCount=0 → 이 분기 미발동 → 오탐 마커 0.
    if (set.size === 0 && forceHighlightWorstCount > 0 && deviations.length > 0) {
      deviations
        .sort((a, b) => b.dev - a.dev)
        .slice(0, forceHighlightWorstCount)
        .forEach(({ kp }) => set.add(kp));
    }
    return set;
  }, [jointAngles, keypointReport, deltaThresholdDeg, forceHighlightWorstCount, highlightKeypoints]);

  // quick-260704-fz4 — attention(주황) set: prop 중 이 report 에 존재하고
  // highlighted(빨강)에 없는 것만 (겹치면 확정이 이긴다). highlighted 계산은
  // 무수정 — prop 미전달 시 빈 Set = 렌더 diff 0.
  const attentionJoints = useMemo(() => {
    const set = new Set<KeypointName>();
    if (!keypointReport || !attentionKeypoints) return set;
    for (const kp of attentionKeypoints) {
      if (keypointReport.joints.includes(kp) && !highlightedJoints.has(kp)) {
        set.add(kp);
      }
    }
    return set;
  }, [attentionKeypoints, keypointReport, highlightedJoints]);

  // 33-G S19 (quick-260730-szk) — 음성 큐 강조 **형태 분기**. 승인 목업 ④ 컷 2 는
  // 한 컷 안에서 뻗은 다리는 사지 모양 선, 접혀서 가려진 다리는 부위 원으로 갈린다.
  // 기하 규칙은 `lib/focusShape` 소유(순수 함수, node --test 로 고정) — 여기서는
  // 좌표 환산과 그리기만 한다(규칙 사본 0).
  const focusShapes = useMemo(() => {
    if (!positions || !focusKeypoints || focusKeypoints.length === 0) {
      return { chains: [], circleGroups: [] };
    }
    return buildFocusShapes({
      focusKeypoints,
      confidenceOf: (kp) => positions.get(kp)?.confidence ?? null,
      threshold: KEYPOINT_LOW_CONFIDENCE_THRESHOLD,
    });
  }, [positions, focusKeypoints]);
  const hasFocusHighlight =
    focusShapes.chains.length + focusShapes.circleGroups.length > 0;

  // 33-G S19 — pulse (승인본 `.legfx.pulse{animation:legpulse 1.4s ease-in-out
  // infinite}` + `@keyframes legpulse{0%,100%{opacity:1} 50%{opacity:.5}}`).
  //
  // N-7 구현 선택: 강조 도형만 별 `Animated.View` 로 감싸고 **View opacity** 를
  // `useNativeDriver: true` 로 애니메이트한다. react-native-svg prop 애니메이션은
  // native driver 를 쓸 수 없어 JS 구동이 되고, 그러면 매 프레임 리렌더 + RN 경고
  // 위험이 있다(결과 화면에 이미 정체 미상 LogBox 배너가 있어 새 경고를 얹지 않는다).
  // 의존성은 **boolean 1개** — 좌표 배열을 넣으면 프레임마다 재구독한다.
  const pulse = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    if (!hasFocusHighlight) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 0.5,
          duration: PULSE_PERIOD_MS / 2,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 1,
          duration: PULSE_PERIOD_MS / 2,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => {
      loop.stop();
      pulse.setValue(1);
    };
  }, [hasFocusHighlight, pulse]);

  // D-12-U6 fallback — caller 가 placeholder 표시.
  if (!visible || keypointReport == null) return null;
  if (!positions) return null;

  // 33-13 (A-6, belle 확인 ① 승인 목업 ①) — 부위 경계 산출 공용 helper.
  // 고신뢰(conf≥0.5) 멤버 keypoint 들의 bounding 을 항목(부위) 단위 타원 경계로
  // 만든다 — 관절원 나열/거대 타원 금지, 부위 형상(실좌표 bounding) 추종.
  // 유효 멤버 0 = null (저신뢰 구간 그룹 자동 생략 — 확신 없는 표시는 긋지 않는다).
  // bounding 은 백엔드 좌표의 시각 배치이지 좌표/각도 산출이 아님 (D-12 §12 무관).
  const boundsFor = (
    kps: readonly KeypointName[],
  ): { cx: number; cy: number; rx: number; ry: number } | null => {
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    let n = 0;
    for (const kp of kps) {
      const p = positions.get(kp);
      if (!p) continue;
      if (p.confidence < KEYPOINT_LOW_CONFIDENCE_THRESHOLD) continue;
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x);
      maxY = Math.max(maxY, p.y);
      n += 1;
    }
    if (n === 0) return null;
    // 여백 = 강조 원 반지름 스케일 (x 축은 W, y 축은 H 정규화 — viewBox 0 0 1 1).
    const padX = (18 * S) / W;
    const padY = (18 * S) / H;
    return {
      cx: (minX + maxX) / 2,
      cy: (minY + maxY) / 2,
      rx: (maxX - minX) / 2 + padX,
      ry: (maxY - minY) / 2 + padY,
    };
  };

  // quick-260705-r6v → 33-13 — 그룹 마커: 멤버 centroid 1점(구) 대신 항목 단위
  // 부위 경계 타원(승인 목업 ① mkg). 번호는 경계 상단 배지로 유지 — 점수 계산
  // 내역 행 번호와의 양방향 대응(단일 소스 buildDeductionMarkers)은 불변.
  //
  // quick-260730-szk (33-G F-8) — `markersVisible === false` 면 경계 자체를 만들지
  // 않는다 (렌더 skip + 탭 타깃 0).
  const groupBounds: {
    number: number;
    badgeLabel: string;
    advisory: boolean;
    cx: number;
    cy: number;
    rx: number;
    ry: number;
  }[] = [];
  if (markersVisible) {
    for (const g of groupMarkers ?? []) {
      const b = boundsFor(g.keypoints);
      if (b) {
        groupBounds.push({
          number: g.number,
          badgeLabel: g.badgeLabel ?? String(g.number),
          advisory: g.advisory === true,
          ...b,
        });
      }
    }
  }

  // quick-260730-szk (33-G S1 / N-4) — 그룹 경계에 흡수된 관절 집합. 이 관절들은
  // 개별 브랜드 강조 원·번호를 렌더하지 않는다 (2R#1 "관절 원 나열 금지" — 현
  // 구현이 그룹 타원 + 멤버 빨강 원을 동시에 그리던 것이 S1 PARTIAL 의 실체).
  // 스켈레톤 ON 이면 일반 흰 점으로만 남는다(추적 스켈레톤 소속).
  const groupedKeypoints = new Set<KeypointName>();
  for (const g of groupMarkers ?? []) {
    for (const kp of g.keypoints) groupedKeypoints.add(kp);
  }

  // 33-G S19 (quick-260730-szk) — 강조 형태를 좌표로 환산.
  //   선: 체인 점 배열. 첫 원소가 근위 관절이면 다음 점 쪽으로 insetT 만큼 밀어
  //       넣는다 (승인본 65% 규칙 — hip 관절이 엉덩이 하단이라 선이 몸통을 가로지름).
  //   원: 기존 boundsFor 타원 (부위 형상 추종 — 규칙 재사용, 신규 상수 0).
  const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
  const focusPolylines: string[] = [];
  for (const chain of focusShapes.chains) {
    const pts = chain.keypoints
      .map((kp) => positions.get(kp))
      .filter((p): p is KeypointPoint => p != null);
    if (pts.length < 2) continue;
    const head =
      chain.insetT > 0
        ? {
            x: lerp(pts[0].x, pts[1].x, chain.insetT),
            y: lerp(pts[0].y, pts[1].y, chain.insetT),
          }
        : { x: pts[0].x, y: pts[0].y };
    const rest = pts.slice(1).map((p) => ({ x: p.x, y: p.y }));
    focusPolylines.push(
      [head, ...rest].map((p) => `${p.x},${p.y}`).join(' '),
    );
  }
  const focusCircles: { cx: number; cy: number; rx: number; ry: number }[] = [];
  for (const group of focusShapes.circleGroups) {
    const b = boundsFor(group);
    if (b) focusCircles.push(b);
  }
  const hasFocusDraw = focusPolylines.length + focusCircles.length > 0;
  // 승인본 굵기 비 — polyline halo:core = 9:5 / circle halo:core = 8:4.
  // 절대 px 신규 상수 0: 기존 STROKE_HI 파생이라 sizeScale 규칙을 자동 계승한다.
  const FOCUS_LINE_CORE = STROKE_HI * 1.4;
  const FOCUS_LINE_HALO = (FOCUS_LINE_CORE * 9) / 5;
  const FOCUS_CIRCLE_CORE = STROKE_HI * 1.4;
  const FOCUS_CIRCLE_HALO = (FOCUS_CIRCLE_CORE * 8) / 4;

  // quick-260705-r6v — 번호 점 탭 타깃 (keypointNumbers 관절 + 그룹 경계 중심).
  // 번호 렌더 규칙(highlighted + 고신뢰)과 정합. onMarkerPress 없으면 빈 배열.
  // quick-260730-szk (N-15) — 마커가 숨겨졌으면 타깃도 0 (보이지 않는 44pt
  // Pressable 이 남으면 belle 반려 계열 결함: 안 보이는 곳이 눌린다).
  const tapTargets: { number: number; x: number; y: number }[] = [];
  if (onMarkerPress && markersVisible) {
    for (const [joint, p] of positions.entries()) {
      if (p.confidence < KEYPOINT_LOW_CONFIDENCE_THRESHOLD) continue;
      if (!highlightedJoints.has(joint)) continue;
      // N-15 — 그룹에 흡수돼 개별 원을 그리지 않는 관절엔 탭 타깃도 두지 않는다
      // (그룹 경계 중심 타깃이 그 부위를 대표한다).
      if (groupedKeypoints.has(joint)) continue;
      const num = markerNumbers?.[joint];
      if (num != null) tapTargets.push({ number: num, x: p.x, y: p.y });
    }
    for (const g of groupBounds) {
      tapTargets.push({ number: g.number, x: g.cx, y: g.cy });
    }
  }

  return (
    <View
      style={StyleSheet.absoluteFillObject}
      // quick-260705-r6v — onMarkerPress 전달 시 box-none 으로 전환해 번호 점
      // Pressable 히트 레이어가 탭을 받게 한다 (영상 본체엔 제스처 없어 무해,
      // planner_findings 2). 미전달 시 기존 'none' (렌더/터치 diff 0).
      pointerEvents={onMarkerPress ? 'box-none' : 'none'}
      accessibilityElementsHidden={!visible}
    >
      <Svg
        width="100%"
        height="100%"
        viewBox="0 0 1 1"
        preserveAspectRatio="none"
        // SVG 는 터치 비대상 — 번호 점 탭은 아래 형제 Pressable 레이어가 받는다.
        pointerEvents="none"
      >
        {/* axisData polyline — UI-SPEC §5: 2-point (mask=false) or 3-point.
            33-13 — 스켈레톤 옵트인 (기본 숨김, D-13). */}
        {skeletonVisible &&
          axis &&
          axis.points.length >= 2 &&
          axis.points.slice(0, -1).map((p, i) => {
            const q = axis.points[i + 1];
            return (
              <Line
                key={`axis-${i}`}
                x1={p.x}
                y1={p.y}
                x2={q.x}
                y2={q.y}
                stroke={colors.textWhite}
                strokeWidth={STROKE_BASE}
                strokeOpacity={0.85}
                strokeLinecap="round"
              />
            );
          })}

        {/* Bones (8). 12-deferred §12-D 분기 우선순위:
            1. 저신뢰 (endpoint 한쪽이라도 conf < 0.5) → estimateGray + dashed
            2. 강조 (highlighted joint 포함) → brand
            3. 기본 → 흰색
            33-13 — 스켈레톤 옵트인: bone 도 추적 스켈레톤의 일부라 기본 숨김.
            결함 부위 표시는 항목 단위 그룹 경계/번호 점이 담당 (승인 목업 ①). */}
        {skeletonVisible && BONES.map(([a, b], i) => {
          const pa = positions.get(a);
          const pb = positions.get(b);
          if (!pa || !pb) return null;
          const isLowConf =
            pa.confidence < KEYPOINT_LOW_CONFIDENCE_THRESHOLD ||
            pb.confidence < KEYPOINT_LOW_CONFIDENCE_THRESHOLD;
          const isHi = highlightedJoints.has(a) || highlightedJoints.has(b);
          const stroke = isLowConf
            ? colors.estimateGray
            : isHi
              ? colors.brand
              : colors.textWhite;
          const strokeWidth = isHi && !isLowConf ? STROKE_HI : STROKE_BASE;
          // dasharray viewBox 1×1 normalize → 짧은 dash + gap.
          const dashArray = isLowConf
            ? `${(4 * S) / W} ${(4 * S) / W}`
            : undefined;
          return (
            <Line
              key={`bone-${i}`}
              x1={pa.x}
              y1={pa.y}
              x2={pb.x}
              y2={pb.y}
              stroke={stroke}
              strokeWidth={strokeWidth}
              strokeOpacity={isLowConf ? 0.7 : 0.95}
              strokeLinecap="round"
              strokeDasharray={dashArray}
            />
          );
        })}

        {/* keypoint circles (J = joints.length — 8 legacy | 12). 저신뢰는 estimateGray (12-deferred §12-D).
            quick-260704-fz4 — attention(주황) 은 강조와 동일 스케일(RADIUS_HI +
            흰 외곽선, Phase 20 A2 가독 선례)이되 fill=advisoryOrange. 저신뢰가
            항상 우선 (advisory 승격 금지). */}
        {Array.from(positions.entries()).map(([joint, p]) => {
          const isLowConf = p.confidence < KEYPOINT_LOW_CONFIDENCE_THRESHOLD;
          // quick-260730-szk — (a) F-8: markersVisible=false 면 강조 계층 전체 off,
          // (b) S1/N-4: 그룹 경계에 흡수된 관절은 개별 강조·번호를 렌더하지 않는다.
          const suppressed = !markersVisible || groupedKeypoints.has(joint);
          const isHi = !suppressed && highlightedJoints.has(joint);
          const isAttn =
            !suppressed && !isHi && attentionJoints.has(joint);
          // 33-13 — 스켈레톤 숨김 시 마커 관절(확정 빨강/참고 주황, 고신뢰)만
          // 렌더. 저신뢰 회색 점·일반 흰 점은 추적 스켈레톤 소속 — 기본 숨김
          // (저신뢰 관절 위 확정 마커도 미렌더: 확신 없는 표시는 긋지 않는다).
          if (!skeletonVisible && (isLowConf || !(isHi || isAttn))) return null;
          const fill = isLowConf
            ? colors.estimateGray
            : isHi
              ? colors.brand
              : isAttn
                ? colors.advisoryOrange
                : colors.textWhite;
          // Phase 20 (UI A2) — 강조(brand) 원의 외곽선을 brand→흰색으로 교체.
          // 같은 brand 색 외곽선은 영상 위에서 윤곽이 사라져 "안 보임" finding 의
          // 원인. 흰색 테두리가 brand 점을 분주한 배경에서 분리해 가독성 ↑.
          // 33-13 — 참고(advisory) 점은 점선 윤곽 원 (승인 목업 ① "점선 = 참고" —
          // 감점 아님을 형태로도 구분. 채움 없는 주황 점선 + 흰 분리 유지 불필요).
          const stroke = isLowConf
            ? colors.estimateGray
            : isAttn
              ? colors.advisoryOrange
              : isHi
                ? colors.textWhite
                : 'rgba(0,0,0,0.6)';
          // Phase 20 (UI A2) — 강조(brand) 관절은 더 큰 반지름 + 두꺼운 외곽선
          // 으로 가독성 ↑. 정상/저신뢰 원은 기존 크기 유지.
          const emphasized = (isHi || isAttn) && !isLowConf;
          // quick-260705-o0s — 감점 record 번호 점: highlighted(빨강) 원 중앙에
          // 흰 bold 숫자. 원 자체가 ①의 원 역할 (작은 원 안 가독을 위해 원문자
          // 유니코드 대신 SVG 숫자 렌더). fontSize 13*S — sizeScale 곱으로 세로
          // 카드/가로 전체화면 동일 규칙 자동 (quick-260702-t0v 메커니즘 재사용).
          // 저신뢰(회색) 원에는 숫자 미표기 — 측정 불신뢰 위 확정 번호 금지.
          const num = isHi && !isLowConf ? markerNumbers?.[joint] : undefined;
          const isAdvisoryDashed = isAttn && !isLowConf;
          return (
            <G key={`kp-${joint}`}>
              <Circle
                cx={p.x}
                cy={p.y}
                r={emphasized ? RADIUS_HI : RADIUS}
                // 33-13 — 참고 점은 채움 없는 점선 원 (목업 ① mk.adv).
                fill={isAdvisoryDashed ? 'none' : fill}
                fillOpacity={isLowConf ? 0.7 : 1.0}
                stroke={stroke}
                strokeWidth={
                  emphasized
                    ? STROKE_CIRCLE_OUTLINE_HI
                    : STROKE_CIRCLE_OUTLINE
                }
                strokeDasharray={
                  isAdvisoryDashed ? `${(3 * S) / W} ${(3 * S) / W}` : undefined
                }
              />
              {num != null && (
                <SvgText
                  x={p.x}
                  // 세로 중앙 보정 — fontSize*0.35 근사 (기존 pill 텍스트 0.68
                  // 배치 관례 참고, cap-height 중심 정렬).
                  y={p.y + NUM_FONT_SIZE * 0.35}
                  fill={colors.textWhite}
                  fontSize={NUM_FONT_SIZE}
                  fontWeight="700"
                  textAnchor="middle"
                >
                  {String(num)}
                </SvgText>
              )}
            </G>
          );
        })}

        {/* quick-260705-r6v → 33-13 (A-6, 승인 목업 ①) — 항목 단위 그룹 마커.
            관절명 없는 record(스플릿 → 다리 4관절 / mode3 부위 record)를 멤버
            keypoint 실좌표 bounding 의 부위 경계 타원으로 렌더한다 — 관절원
            나열·중점 1점 대신 부위 형상 추종(belle 확인 ① 확정). 번호 배지는
            경계 상단 — 점수 계산 내역 행 번호와 단일 소스(buildDeductionMarkers)
            양방향 대응 유지. 흰 halo + brand 선 (목업 mkg 시각 규칙). */}
        {groupBounds.map((g) => {
          const badgeY = Math.max(RADIUS_HI, g.cy - g.ry);
          // quick-260730-szk (33-G S2 / N-5) — 참고 그룹은 **점선 + advisoryOrange**.
          // 승인본 CSS 는 회색(#8b93a1)이지만 앱은 주황 2단 시각 언어를 이미 3표면
          // (편차표·확대 카드·마커)에서 쓰고 있어(quick-260704-fz4, PASS) 색을 바꾸면
          // 그 표면들이 어긋난다. S2 의 판정축은 **형태**(실선/점선) 구분이다.
          const stroke = g.advisory ? colors.advisoryOrange : colors.brand;
          const dash = g.advisory
            ? `${(3 * S) / W} ${(3 * S) / W}`
            : undefined;
          // quick-260730-szk (N-2) — 한 부위에 감점 2건이면 `2·3` 병합 배지.
          // 2글자 이상은 원 대신 pill(Rect) 로 그려 숫자가 잘리지 않게 한다.
          const wideBadge = g.badgeLabel.length >= 2;
          const badgeRx = (RADIUS_HI * H) / W;
          const badgeH = RADIUS_HI * 2;
          const badgeW = ((10 + 9 * g.badgeLabel.length) * S) / W;
          return (
            <G key={`group-${g.number}`}>
              <Ellipse
                cx={g.cx}
                cy={g.cy}
                rx={g.rx}
                ry={g.ry}
                fill="none"
                stroke={colors.textWhite}
                strokeWidth={STROKE_HI + STROKE_CIRCLE_OUTLINE_HI}
                strokeOpacity={0.55}
              />
              <Ellipse
                cx={g.cx}
                cy={g.cy}
                rx={g.rx}
                ry={g.ry}
                fill="none"
                stroke={stroke}
                strokeWidth={STROKE_HI}
                strokeDasharray={dash}
              />
              {wideBadge ? (
                <Rect
                  x={g.cx - badgeW / 2}
                  y={badgeY - badgeH / 2}
                  width={badgeW}
                  height={badgeH}
                  rx={badgeRx}
                  ry={RADIUS_HI}
                  fill={stroke}
                  stroke={colors.textWhite}
                  strokeWidth={STROKE_CIRCLE_OUTLINE_HI}
                />
              ) : (
                <Circle
                  cx={g.cx}
                  cy={badgeY}
                  r={RADIUS_HI}
                  fill={stroke}
                  stroke={colors.textWhite}
                  strokeWidth={STROKE_CIRCLE_OUTLINE_HI}
                />
              )}
              <SvgText
                x={g.cx}
                y={badgeY + NUM_FONT_SIZE * 0.35}
                fill={colors.textWhite}
                fontSize={NUM_FONT_SIZE}
                fontWeight="700"
                textAnchor="middle"
              >
                {g.badgeLabel}
              </SvgText>
            </G>
          );
        })}

        {/* 33-13 (A-6, D-13 대표 UX) — 음성 큐 부위 강조. 전체 프레임 dim 위에
            해당 record 부위의 경계만 올린다 (승인 목업 ④ 컷 2 — 음성 중 정지 +
            부위 강조). 고신뢰 멤버 0 이면 focusBounds=null → dim 자체를 깔지
            않는다 (강조 없는 어두운 화면 금지 — 자막·음성만). */}
        {/* quick-260730-szk (N-8) — dim 은 이 정적 `<Svg>` 에 남긴다. 승인본 `.dim` 은
            `.legfx.pulse` **밖의 별 div** 라 깜빡이지 않는다. 화면 전체가 밝기
            진동하면 S18(음성 중 정지+dim, 이미 PASS)의 표현이 깨진다. */}
        {hasFocusDraw && (
          <Rect
            x={0}
            y={0}
            width={1}
            height={1}
            fill="#000000"
            fillOpacity={0.34}
          />
        )}
      </Svg>
      {/* 33-G S19 (quick-260730-szk) — 강조 도형 전용 pulse 레이어.
          승인본 `.legfx.pulse` = 1.4초 주기 opacity 1 → 0.5 → 1. 흰 halo 아래 +
          브랜드 코어 위(굵기 비 polyline 9:5 / circle 8:4, `:222-226,452-455`).
          별 `Animated.View` 인 이유 = N-7 (native driver 로 View opacity 만 구동). */}
      {hasFocusDraw && (
        <Animated.View
          style={[StyleSheet.absoluteFillObject, { opacity: pulse }]}
          pointerEvents="none"
        >
          <Svg
            width="100%"
            height="100%"
            viewBox="0 0 1 1"
            preserveAspectRatio="none"
            pointerEvents="none"
          >
            {focusPolylines.map((points, i) => (
              <G key={`focus-line-${i}`}>
                <Polyline
                  points={points}
                  fill="none"
                  stroke={colors.textWhite}
                  strokeOpacity={0.72}
                  strokeWidth={FOCUS_LINE_HALO}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <Polyline
                  points={points}
                  fill="none"
                  stroke={colors.brand}
                  strokeWidth={FOCUS_LINE_CORE}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </G>
            ))}
            {focusCircles.map((c, i) => (
              <G key={`focus-circle-${i}`}>
                <Ellipse
                  cx={c.cx}
                  cy={c.cy}
                  rx={c.rx}
                  ry={c.ry}
                  fill="none"
                  stroke={colors.textWhite}
                  strokeOpacity={0.72}
                  strokeWidth={FOCUS_CIRCLE_HALO}
                />
                <Ellipse
                  cx={c.cx}
                  cy={c.cy}
                  rx={c.rx}
                  ry={c.ry}
                  fill="none"
                  stroke={colors.brand}
                  strokeWidth={FOCUS_CIRCLE_CORE}
                />
              </G>
            ))}
          </Svg>
        </Animated.View>
      )}
      {/* quick-260705-r6v — 번호 점 탭 히트 레이어 (SVG 위 형제, box-none).
          번호 있는 마커 위치에 고정 44pt Pressable 을 정규화 좌표(x100 퍼센트)로
          배치. onMarkerPress 미전달 시 이 블록 자체가 없어 렌더 diff 0. */}
      {onMarkerPress && tapTargets.length > 0 && (
        <View style={StyleSheet.absoluteFillObject} pointerEvents="box-none">
          {tapTargets.map((t, i) => (
            <Pressable
              key={`tap-${t.number}-${i}`}
              onPress={() => onMarkerPress(t.number)}
              accessibilityRole="button"
              accessibilityLabel={`${t.number}번 감점 상세 보기`}
              hitSlop={8}
              style={{
                position: 'absolute',
                left: `${t.x * 100}%`,
                top: `${t.y * 100}%`,
                width: 44,
                height: 44,
                marginLeft: -22,
                marginTop: -22,
              }}
            />
          ))}
        </View>
      )}
    </View>
  );
}
