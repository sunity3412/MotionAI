// Phase 12 Wave 1 (Plan 12-02 T1) — 영상 위 키포인트 오버레이 (정적 렌더).
//
// 책임 (Wave 1):
//   - 8 body keypoint (좌우 어깨/엉덩이/무릎/손) + axisData polyline 정적 렌더
//   - props 로 받은 frameIndex (Wave 1 = 0 고정) 의 좌표 그대로 박제
//   - delta 강조 / floating angle label / useEvent frame sync 는 Wave 2 (Plan 12-03)
//   - keypointReport 미가용 시 null return → caller 가 placeholder 표시 (D-12-U6)
//
// 책임 분리 (Wave 2 진입 site):
//   - player prop 전달 + frameIndex 생략 → KeypointOverlay 내부 useEvent(player, 'timeUpdate')
//   - jointAngles prop 으로 current/target 받아 delta ≥ deltaThresholdDeg 강조
//   - floating angle label (highlighted joint 만, brand bg + WHITE 10pt)
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
import type { VideoPlayer } from 'expo-video';
import { colors } from '../theme';
import type { KeypointName, KeypointReport } from '../types/analysis';

// D-12-C3 — Phase 9 IPSF tolerance 20° 와 분리. UX 시각 강조 임계 (Wave 2 가 소비).
export const KEYPOINT_DELTA_HIGHLIGHT_DEG = 10.0;

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

// frame=0 (또는 prop frameIndex) 의 8 keypoint 좌표 reshape.
// flat array 전체 reshape 회피 — 한 frame 만 slice (T × J × 2 → J point).
function readFramePositions(
  report: KeypointReport,
  frameIdx: number,
): Map<KeypointName, Point> | null {
  const T = report.frames;
  const J = report.joints.length;
  if (T <= 0 || J <= 0) return null;
  const idx = Math.min(Math.max(frameIdx, 0), T - 1);
  const base = idx * J * 2;
  if (report.data.length < base + J * 2) return null;
  const map = new Map<KeypointName, Point>();
  for (let j = 0; j < J; j += 1) {
    const x = report.data[base + j * 2];
    const y = report.data[base + j * 2 + 1];
    if (typeof x !== 'number' || typeof y !== 'number') continue;
    map.set(report.joints[j], { x, y });
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
  player: _player,
  keypointReport,
  videoSize,
  visible,
  frameIndex = 0,
  jointAngles,
  deltaThresholdDeg = KEYPOINT_DELTA_HIGHLIGHT_DEG,
  showAngleLabels = true,
}: KeypointOverlayProps) {
  // D-12-U6 fallback — caller 가 placeholder 표시.
  if (!visible || keypointReport == null) {
    return null;
  }

  // KeypointReport 좌표계 = image normalized 0..1 (Wave 0B contract).
  // viewBox = "0 0 1 1" + Svg width/height = videoSize 로 자동 scale.
  // 실제 좌표는 viewBox 안에서 normalized 그대로 박제.
  const W = Math.max(1, videoSize.width);
  const H = Math.max(1, videoSize.height);
  // viewBox 축 = 1 normalized → keypoint 좌표 그대로. circle r 도 normalized 단위.
  // r = 10pt / native height = 10 / H. bone strokeWidth 동일 분율.
  const RADIUS = 10 / H;
  const STROKE_BASE = 1.8 / H;
  const STROKE_HI = 3 / H;
  const STROKE_CIRCLE_OUTLINE = 1.5 / H;

  const positions = useMemo(
    () => readFramePositions(keypointReport, frameIndex),
    [keypointReport, frameIndex],
  );

  const axis = useMemo(
    () => readFrameAxis(keypointReport, frameIndex),
    [keypointReport, frameIndex],
  );

  // Wave 1 = jointAngles 미공급 → 빈 Set (highlighted 없음).
  // Wave 2 가 jointAngles 받아 delta ≥ deltaThresholdDeg 분기.
  const highlightedJoints = useMemo(() => {
    const set = new Set<KeypointName>();
    if (!jointAngles) return set;
    for (const joint of keypointReport.joints) {
      const pair = jointAngles[joint];
      if (!pair) continue;
      const cur = pair.current;
      const tgt = pair.target;
      if (cur == null || tgt == null) continue;
      if (!Number.isFinite(cur) || !Number.isFinite(tgt)) continue;
      if (Math.abs(cur - tgt) >= deltaThresholdDeg) {
        set.add(joint);
      }
    }
    return set;
  }, [jointAngles, keypointReport.joints, deltaThresholdDeg]);

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

        {/* Bones (8). 강조된 joint 한쪽이라도 포함되면 brand. */}
        {BONES.map(([a, b], i) => {
          const pa = positions.get(a);
          const pb = positions.get(b);
          if (!pa || !pb) return null;
          const isHi = highlightedJoints.has(a) || highlightedJoints.has(b);
          return (
            <Line
              key={`bone-${i}`}
              x1={pa.x}
              y1={pa.y}
              x2={pb.x}
              y2={pb.y}
              stroke={isHi ? colors.brand : '#FFFFFF'}
              strokeWidth={isHi ? STROKE_HI : STROKE_BASE}
              strokeOpacity={0.95}
              strokeLinecap="round"
            />
          );
        })}

        {/* 8 keypoint circles. */}
        {Array.from(positions.entries()).map(([joint, p]) => {
          const isHi = highlightedJoints.has(joint);
          return (
            <Circle
              key={`kp-${joint}`}
              cx={p.x}
              cy={p.y}
              r={RADIUS}
              fill={isHi ? colors.brand : '#FFFFFF'}
              stroke={isHi ? colors.brand : 'rgba(0,0,0,0.6)'}
              strokeWidth={STROKE_CIRCLE_OUTLINE}
            />
          );
        })}

        {/* Floating angle label (Wave 2 책임 — highlighted Set 비면 미렌더).
            Wave 1 호출 = jointAngles 미공급 → highlightedJoints 빈 Set → 노출 X.
            Wave 2 가 enable. */}
        {showAngleLabels &&
          Array.from(highlightedJoints).map((joint) => {
            const p = positions.get(joint);
            const pair = jointAngles?.[joint];
            if (!p || !pair || pair.current == null) return null;
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
