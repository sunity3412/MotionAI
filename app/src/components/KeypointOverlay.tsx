// Phase 12 Wave 2 (Plan 12-03 T1) — 영상 위 키포인트 오버레이 (frame sync).
//
// 책임 (Wave 2):
//   - 8 body keypoint (좌우 어깨/엉덩이/무릎/손) + axisData polyline 렌더
//   - player prop 전달 시 useEvent(player, 'timeUpdate') 로 frame index 자동 산출.
//     player 미전달 시 props.frameIndex (default 0) 의 정적 렌더 (Wave 1 호환).
//   - jointAngles prop 으로 current/target 받아 delta ≥ deltaThresholdDeg 강조.
//     Phase 20 (UI A2): pill/글자 확대 + 흰 외곽선으로 가독성 개선.
//     quick-260705-k8y: floating 라벨은 절대각 숫자 → actionLabels prop 의 행동
//     지시 문구("왼쪽 무릎 23° 더 펴야")로 전면 대체. jointAngles 는 강조 산출
//     전용으로 유지.
//   - keypointReport 미가용 시 null return → caller 가 placeholder 표시 (D-12-U6)
//
// MVP 단순화 (R5 iter-2 정합): delta 강조 = 영상 전체 대표 편차. jointAngles =
// JointScore 의 평균 currentAngle/targetAngle 입력. frame-level delta + DTW
// alignment 는 v2 (12-deferred-items.md 박제).
//
// 좌표계 약속 (Wave 0B KeypointReport schema §9.12):
//   - keypointReport.data = flat T × 8 × 2, image normalized 0..1
//   - keypointReport.axisData = flat T × 3 × 2, shoulder_mid / hip_mid / knee_mid?
//   - keypointReport.axisMask[idx*3 + 2] === false → polyline 2-point (knee_mid 생략)
//   - UI 단 좌표 산출 절대 X (백엔드 산출만 read, D-12 §12 안티 패턴)
//
// 토큰만 사용 (CLAUDE.md §4 / D-12-U5). brand #FF4B33 변경 0.

import React, { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import Svg, { Circle, G, Line, Rect, Text as SvgText } from 'react-native-svg';
import { useEvent } from 'expo';
import type { VideoPlayer } from 'expo-video';
import { colors } from '../theme';
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
const JOINT_KEY_TO_ANGLE_KEY: Record<KeypointName, string | null> = {
  left_shoulder: 'left_shoulder',
  right_shoulder: 'right_shoulder',
  left_hip: 'left_hip',
  right_hip: 'right_hip',
  left_knee: 'left_knee',
  right_knee: 'right_knee',
  left_hand: 'left_elbow',
  right_hand: 'right_elbow',
};

// UI-SPEC §5 + RESEARCH §Code Examples §1. 8 keypoint + 8 bone.
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
  /** 행동 지시 라벨 전체 on/off 게이트 (quick-260705-k8y 로 의미 갱신), default true. */
  showAngleLabels?: boolean;
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
   * quick-260705-k8y — 문제 관절의 행동 지시 문구 (result.tsx 가 실측 데이터로
   * 조립). 라벨은 highlighted(빨강)∪attention(주황) 관절 중 이 맵에 항목이 있는
   * 것만 렌더 — 없으면 마커만 (안전 폴백, Mode3 데이터 부재 대응). 절대각 숫자
   * 라벨은 본 prop 도입으로 전면 제거 (belle: "각도로는 무슨 말인지 못 알아듣는다").
   */
  actionLabels?: Partial<Record<KeypointName, string>>;
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

// 라벨 pill 동적 폭 추정 (quick-260705-k8y) — RN SVG 는 텍스트 measure API 가
// 없어 문자 폭 근사: 한글 14 / 그 외(숫자·°·공백) 8 + 좌우 패딩 16. fontSize 14
// bold 기준 근사 — 다소 넉넉해도 pill 형태라 무해. 순수 함수.
function labelTextWidth(text: string): number {
  let w = 16;
  for (const ch of text) {
    w += /[가-힣]/.test(ch) ? 14 : 8;
  }
  return w;
}

// frame=0 (또는 prop frameIndex) 의 8 keypoint 좌표 + confidence reshape.
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

export function KeypointOverlay({
  player,
  keypointReport,
  videoSize,
  visible,
  frameIndex: frameIndexProp,
  jointAngles,
  deltaThresholdDeg = KEYPOINT_DELTA_HIGHLIGHT_DEG,
  showAngleLabels = true,
  forceHighlightWorstCount = 0,
  highlightKeypoints,
  attentionKeypoints,
  actionLabels,
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
  const timeUpdate = useEvent(
    (player ?? null) as unknown as Parameters<typeof useEvent>[0],
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

  // D-12-U6 fallback — caller 가 placeholder 표시.
  if (!visible || keypointReport == null) return null;
  if (!positions) return null;

  return (
    <View
      style={StyleSheet.absoluteFillObject}
      pointerEvents="none"
      accessibilityElementsHidden={!visible}
    >
      <Svg
        width="100%"
        height="100%"
        viewBox="0 0 1 1"
        preserveAspectRatio="none"
      >
        {/* axisData polyline — UI-SPEC §5: 2-point (mask=false) or 3-point */}
        {axis &&
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
                stroke="#FFFFFF"
                strokeWidth={STROKE_BASE}
                strokeOpacity={0.85}
                strokeLinecap="round"
              />
            );
          })}

        {/* Bones (8). 12-deferred §12-D 분기 우선순위:
            1. 저신뢰 (endpoint 한쪽이라도 conf < 0.5) → estimateGray + dashed
            2. 강조 (highlighted joint 포함) → brand
            3. 기본 → 흰색 */}
        {BONES.map(([a, b], i) => {
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
              : '#FFFFFF';
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

        {/* 8 keypoint circles. 저신뢰 keypoint 는 estimateGray (12-deferred §12-D).
            quick-260704-fz4 — attention(주황) 은 강조와 동일 스케일(RADIUS_HI +
            흰 외곽선, Phase 20 A2 가독 선례)이되 fill=advisoryOrange. 저신뢰가
            항상 우선 (advisory 승격 금지). */}
        {Array.from(positions.entries()).map(([joint, p]) => {
          const isLowConf = p.confidence < KEYPOINT_LOW_CONFIDENCE_THRESHOLD;
          const isHi = highlightedJoints.has(joint);
          const isAttn = !isHi && attentionJoints.has(joint);
          const fill = isLowConf
            ? colors.estimateGray
            : isHi
              ? colors.brand
              : isAttn
                ? colors.advisoryOrange
                : '#FFFFFF';
          // Phase 20 (UI A2) — 강조(brand) 원의 외곽선을 brand→흰색으로 교체.
          // 같은 brand 색 외곽선은 영상 위에서 윤곽이 사라져 "안 보임" finding 의
          // 원인. 흰색 테두리가 brand 점을 분주한 배경에서 분리해 가독성 ↑.
          const stroke = isLowConf
            ? colors.estimateGray
            : isHi || isAttn
              ? '#FFFFFF'
              : 'rgba(0,0,0,0.6)';
          // Phase 20 (UI A2) — 강조(brand) 관절은 더 큰 반지름 + 두꺼운 외곽선
          // 으로 가독성 ↑. 정상/저신뢰 원은 기존 크기 유지.
          const emphasized = (isHi || isAttn) && !isLowConf;
          return (
            <Circle
              key={`kp-${joint}`}
              cx={p.x}
              cy={p.y}
              r={emphasized ? RADIUS_HI : RADIUS}
              fill={fill}
              fillOpacity={isLowConf ? 0.7 : 1.0}
              stroke={stroke}
              strokeWidth={
                emphasized
                  ? STROKE_CIRCLE_OUTLINE_HI
                  : STROKE_CIRCLE_OUTLINE
              }
            />
          );
        })}

        {/* 행동 지시 라벨 (quick-260705-k8y — 절대각 숫자 라벨 전면 대체).
            belle: "158° 절대각은 무슨 말인지 못 알아듣는다" → 문제 관절(빨강 확정
            ∪ 주황 측정초과)에만 "왼쪽 무릎 23° 더 펴야" 형태 행동 문구. 문구는
            caller(result.tsx)가 실측 주입 데이터로만 조립 — actionLabels 에 항목
            없는 관절은 마커만 (안전 폴백, Mode3 데이터 부재 대응).

            Phase 20 (UI A2) 가독 메커니즘 유지: pill + 흰 외곽선 + WHITE 14pt
            bold + 얇은 흰 텍스트 stroke. 문구 길이가 가변이라 pill 폭은
            labelTextWidth 로 동적 산출.

            quick-260704-fz4 — attention(주황) 관절 pill 배경 = advisoryOrange
            (2단 시각 언어 — 빨강 pill='확정 감점' 의미 보존). */}
        {showAngleLabels &&
          [...highlightedJoints, ...attentionJoints].map((joint) => {
            const p = positions.get(joint);
            const text = actionLabels?.[joint];
            if (!p || !text) return null;
            // 12-deferred §12-D — 저신뢰 keypoint 의 측정은 불신뢰 → label 숨김.
            if (p.confidence < KEYPOINT_LOW_CONFIDENCE_THRESHOLD) return null;
            const labelW = (labelTextWidth(text) * S) / W;
            const labelH = (26 * S) / H;
            // keypoint 우측 +14pt offset (강조 원이 커졌으므로 겹침 회피).
            let lx = p.x + (14 * S) / W;
            // 우측 overflow 클램프 — 긴 문구가 화면(viewBox 1×1) 밖으로 나가면
            // keypoint 왼쪽에 배치 (줌 클리핑과 중첩되는 전체화면에서 특히 중요).
            if (lx + labelW > 1) {
              lx = p.x - (14 * S) / W - labelW;
            }
            const ly = p.y - labelH / 2;
            return (
              <G key={`label-${joint}`}>
                <Rect
                  x={lx}
                  y={ly}
                  width={labelW}
                  height={labelH}
                  rx={(13 * S) / H}
                  ry={(13 * S) / H}
                  fill={
                    highlightedJoints.has(joint)
                      ? colors.brand
                      : colors.advisoryOrange
                  }
                  stroke="#FFFFFF"
                  strokeWidth={(1.4 * S) / H}
                />
                <SvgText
                  x={lx + labelW / 2}
                  y={ly + labelH * 0.68}
                  fill="#FFFFFF"
                  // 텍스트 외곽에 얇은 흰 stroke — 영상 디테일 위에서도 글자
                  // 가장자리가 또렷해 판독성 ↑ (brand pill 안 흰 글씨 대비 보강).
                  stroke="#FFFFFF"
                  strokeWidth={(0.6 * S) / H}
                  fontSize={(14 * S) / H}
                  fontWeight="700"
                  textAnchor="middle"
                >
                  {text}
                </SvgText>
              </G>
            );
          })}
      </Svg>
    </View>
  );
}
