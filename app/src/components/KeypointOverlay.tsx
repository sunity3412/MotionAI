// Phase 12 Wave 2 (Plan 12-03 T1) — 영상 위 키포인트 오버레이 (frame sync).
//
// 책임 (Wave 2):
//   - 8 body keypoint (좌우 어깨/엉덩이/무릎/손) + axisData polyline 렌더
//   - player prop 전달 시 useEvent(player, 'timeUpdate') 로 frame index 자동 산출.
//     player 미전달 시 props.frameIndex (default 0) 의 정적 렌더 (Wave 1 호환).
//   - jointAngles prop 으로 current/target 받아 delta ≥ deltaThresholdDeg 강조 +
//     floating angle label (highlighted joint 만, brand bg + WHITE 10pt, D-12-C3)
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

// D-12-C3 — Phase 9 IPSF tolerance 20° 와 분리. UX 시각 강조 임계 (Wave 2 가 소비).
export const KEYPOINT_DELTA_HIGHLIGHT_DEG = 10.0;

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
  /** default 10 (D-12-C3, KEYPOINT_DELTA_HIGHLIGHT_DEG). */
  deltaThresholdDeg?: number;
  /** Wave 2 floating label 표시, default true. */
  showAngleLabels?: boolean;
};

type Point = { x: number; y: number };
type KeypointPoint = Point & { confidence: number };

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
  const RADIUS = 10 / H;
  const STROKE_BASE = 1.8 / H;
  const STROKE_HI = 3 / H;
  const STROKE_CIRCLE_OUTLINE = 1.5 / H;

  // Wave 2: player 전달 시 useEvent.currentTime → frameIndex 자동 산출.
  // player 없거나 frameIndex prop 명시 시 override.
  const frameIndex = useMemo(() => {
    if (typeof frameIndexProp === 'number') return frameIndexProp;
    if (!keypointReport || keypointReport.frames < 1) return 0;
    const currentTime = timeUpdate?.currentTime ?? 0;
    const fps = keypointReport.fps > 0 ? keypointReport.fps : 1;
    const idx = Math.floor(currentTime * fps);
    return Math.min(Math.max(idx, 0), keypointReport.frames - 1);
  }, [frameIndexProp, timeUpdate?.currentTime, keypointReport]);

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
    if (!jointAngles || !keypointReport) return set;
    for (const kp of keypointReport.joints) {
      const angleKey = JOINT_KEY_TO_ANGLE_KEY[kp];
      if (!angleKey) continue;
      const pair = jointAngles[angleKey];
      if (!pair) continue;
      const cur = pair.current;
      const tgt = pair.target;
      if (cur == null || tgt == null) continue;
      if (!Number.isFinite(cur) || !Number.isFinite(tgt)) continue;
      if (Math.abs(cur - tgt) >= deltaThresholdDeg) {
        set.add(kp);
      }
    }
    return set;
  }, [jointAngles, keypointReport, deltaThresholdDeg]);

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
          const dashArray = isLowConf ? `${4 / W} ${4 / W}` : undefined;
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

        {/* 8 keypoint circles. 저신뢰 keypoint 는 estimateGray (12-deferred §12-D). */}
        {Array.from(positions.entries()).map(([joint, p]) => {
          const isLowConf = p.confidence < KEYPOINT_LOW_CONFIDENCE_THRESHOLD;
          const isHi = highlightedJoints.has(joint);
          const fill = isLowConf
            ? colors.estimateGray
            : isHi
              ? colors.brand
              : '#FFFFFF';
          const stroke = isLowConf
            ? colors.estimateGray
            : isHi
              ? colors.brand
              : 'rgba(0,0,0,0.6)';
          return (
            <Circle
              key={`kp-${joint}`}
              cx={p.x}
              cy={p.y}
              r={RADIUS}
              fill={fill}
              fillOpacity={isLowConf ? 0.7 : 1.0}
              stroke={stroke}
              strokeWidth={STROKE_CIRCLE_OUTLINE}
            />
          );
        })}

        {/* Floating angle label (Wave 2 책임 — highlighted Set 비면 미렌더).
            jointAngles 미공급 시 highlightedJoints 빈 Set → 노출 X.
            UI-SPEC §5: 48 × 18 brand bg pill + WHITE 10pt Math.round(°). */}
        {showAngleLabels &&
          Array.from(highlightedJoints).map((joint) => {
            const p = positions.get(joint);
            const angleKey = JOINT_KEY_TO_ANGLE_KEY[joint];
            const pair = angleKey ? jointAngles?.[angleKey] : undefined;
            if (!p || !pair || pair.current == null) return null;
            // 12-deferred §12-D — 저신뢰 keypoint 의 각도는 불신뢰 → label 숨김.
            if (p.confidence < KEYPOINT_LOW_CONFIDENCE_THRESHOLD) return null;
            const labelW = 48 / W;
            const labelH = 18 / H;
            // keypoint 우측 +12pt offset.
            const lx = p.x + 12 / W;
            const ly = p.y - labelH / 2;
            return (
              <G key={`label-${joint}`}>
                <Rect
                  x={lx}
                  y={ly}
                  width={labelW}
                  height={labelH}
                  rx={9 / H}
                  ry={9 / H}
                  fill={colors.brand}
                />
                <SvgText
                  x={lx + labelW / 2}
                  y={ly + labelH * 0.7}
                  fill="#FFFFFF"
                  fontSize={10 / H}
                  fontWeight="600"
                  textAnchor="middle"
                >
                  {`${Math.round(pair.current)}°`}
                </SvgText>
              </G>
            );
          })}
      </Svg>
    </View>
  );
}
