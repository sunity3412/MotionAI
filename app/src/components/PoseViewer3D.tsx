// Phase 4 Wave 2 — Stage 3 사용자 3D 뷰어 (react-three-fiber + expo-three).
//
// Spike 005 VALIDATED-ARCHITECTURE (2026-06-13). 04-02 PLAN Task 4.
//
// /native import 경로 필수 — web path (@react-three/fiber) 사용 시 RN 에서
// "window is not defined" 즉시 crash (RESEARCH Pitfall 2).
// drei OrbitControls /native export 가용 확인 완료 (04-02 PLAN Task 1 →
// blocking checkpoint resume-signal "approved OrbitControls:true" 박제).
// 따라서 본 컴포넌트는 PanResponder fallback 없이 drei OrbitControls 직접 사용.
//
// 배경 색: viewer3dBg (#F5F5F5, softBg alias) — 다크 배경 금지
// (CLAUDE.md §4 / design.md §10). Three.js scene.background 도 동일 hex int.
//
// 데이터 소스 (R3):
//   joints prop = number[][][] = (T, J, 3) — caller 가 reshapePose3dData 로
//   doc.result.joints3d (Phase 4 Wave 1 신설 flat 필드) 를 reshape 해 전달.
//   result.angles (관절각 (T, J) 스칼라) 는 절대 전달 금지 — 좌표 아님.
//
// Wave 2 = user-only 3D viewer (HIGH-3 4차 게이트 리뷰). referenceJoints prop
// 은 예약만 두고 본 wave 에서는 caller 가 omit. ReferenceMotion 타입 +
// referenceMotions.ts normalize 가 joints3d 를 흘리는 follow-up plan (04-05+)
// 이후 활성화.
//
// R8 (Canvas/GL ErrorBoundary): GL 컨텍스트 초기화 실패 / Three.js 마운트 충돌
// 시 result.tsx route 전체가 죽지 않도록 본 컴포넌트 Canvas 를 class
// ErrorBoundary 가 격리. fallback = design.md §0 빈 상태 패턴.

import { Ionicons } from '@expo/vector-icons';
import { Canvas } from '@react-three/fiber/native';
import { OrbitControls } from '@react-three/drei/native';
import React, { useMemo, useRef } from 'react';
import {
  type GestureResponderEvent,
  type LayoutChangeEvent,
  PanResponder,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { colors, radius, spacing, typography } from '../theme';

// ── Camera preset ────────────────────────────────────────────────────────
// UI-SPEC §Surface 1 Camera Preset 4개. 폴스포츠 시점 매핑.
type CameraPresetKey = 'front' | 'side' | 'back' | 'top';
interface CameraPreset {
  key: CameraPresetKey;
  label: string;
  position: [number, number, number];
}
const CAMERA_PRESETS: readonly CameraPreset[] = [
  { key: 'front', label: '정면', position: [0, 0, 3] },
  { key: 'side', label: '측면', position: [3, 0, 0] },
  { key: 'back', label: '후면', position: [0, 0, -3] },
  { key: 'top', label: '위', position: [0, 3, 0] },
];

// ── COCO-17 bone topology ────────────────────────────────────────────────
// reshapePose3dData 결과의 joint 인덱스 (joints3dKeys 순서, COCO-17 정합).
// SkeletonMesh 가 본 pair 를 line segment 로 그린다.
const COCO17_BONES: readonly [number, number][] = [
  [5, 6], // shoulders
  [5, 7], // L shoulder→elbow
  [7, 9], // L elbow→wrist
  [6, 8], // R shoulder→elbow
  [8, 10], // R elbow→wrist
  [5, 11], // L shoulder→hip
  [6, 12], // R shoulder→hip
  [11, 12], // hips
  [11, 13], // L hip→knee
  [13, 15], // L knee→ankle
  [12, 14], // R hip→knee
  [14, 16], // R knee→ankle
];

// ── Canvas / GL ErrorBoundary (R8) ───────────────────────────────────────
// expo-gl GL 컨텍스트 초기화 실패 / Three.js 마운트 충돌 / 구형 기기 호환성
// 이슈로 throw 가 나도 result.tsx route 전체가 죽지 않도록 격리. fallback 은
// design.md §0 빈 상태 패턴 정합 — CTA 없이 일반 결과 확인 안내.
interface ErrorBoundaryProps {
  children: React.ReactNode;
}
interface ErrorBoundaryState {
  hasError: boolean;
}
class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }
  componentDidCatch(error: Error): void {
    if (__DEV__) console.warn('[PoseViewer3D] GL/Canvas init failed', error);
  }
  render() {
    if (this.state.hasError) {
      return (
        <View style={styles.fallback}>
          <Ionicons
            name="cube-outline"
            size={32}
            color={colors.textSecondary}
          />
          <Text style={styles.fallbackTitle}>3D 뷰어를 불러오지 못했어요.</Text>
          <Text style={styles.fallbackHint}>
            일반 결과는 아래에서 확인하세요.
          </Text>
        </View>
      );
    }
    return this.props.children;
  }
}

// ── SkeletonMesh ─────────────────────────────────────────────────────────
// 단일 frame 의 (J, 3) joint 좌표 → sphere (joint) + line segments (bones).
// 정상 관절: viewer3dJointNormal. IPSF 위반 관절: viewer3dJoint (brand).
// 뼈대 line: viewer3dBone.
interface SkeletonMeshProps {
  frame: number[][]; // (J, 3) — frame[j] = [x, y, z]
  isIpsfViolation: boolean;
}
function SkeletonMesh({ frame, isIpsfViolation }: SkeletonMeshProps) {
  const jointColor = isIpsfViolation
    ? colors.viewer3dJoint
    : colors.viewer3dJointNormal;

  // Bones: line segment vertices flat array. Three.js BufferGeometry expects
  // Float32Array. line segments = pair of vertices per segment.
  const boneVertices = useMemo(() => {
    const verts: number[] = [];
    for (const [a, b] of COCO17_BONES) {
      if (
        a < frame.length &&
        b < frame.length &&
        frame[a]?.length === 3 &&
        frame[b]?.length === 3
      ) {
        verts.push(frame[a][0], frame[a][1], frame[a][2]);
        verts.push(frame[b][0], frame[b][1], frame[b][2]);
      }
    }
    return new Float32Array(verts);
  }, [frame]);

  return (
    <>
      {/* joints */}
      {frame.map((p, j) => {
        if (!Array.isArray(p) || p.length !== 3) return null;
        return (
          <mesh key={j} position={[p[0], p[1], p[2]]}>
            <sphereGeometry args={[0.04, 12, 12]} />
            <meshStandardMaterial color={jointColor} />
          </mesh>
        );
      })}
      {/* bones — line segments */}
      {boneVertices.length > 0 && (
        <lineSegments>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              args={[boneVertices, 3]}
            />
          </bufferGeometry>
          <lineBasicMaterial color={colors.viewer3dBone} />
        </lineSegments>
      )}
    </>
  );
}

// ── CameraPresetBar ──────────────────────────────────────────────────────
// 4개 preset 버튼. 활성 시 brand 1pt 테두리 + brand text, 비활성 시 softBg
// 배경 + textPrimary text. UI-SPEC §Surface 1 정합.
interface CameraPresetBarProps {
  active: CameraPresetKey;
  onSelect: (key: CameraPresetKey) => void;
}
function CameraPresetBar({ active, onSelect }: CameraPresetBarProps) {
  return (
    <View style={styles.presetBar}>
      {CAMERA_PRESETS.map((preset) => {
        const isActive = preset.key === active;
        return (
          <Pressable
            key={preset.key}
            onPress={() => onSelect(preset.key)}
            style={[styles.presetButton, isActive && styles.presetButtonActive]}
            accessibilityRole="button"
            accessibilityLabel={`${preset.label} 시점으로 전환`}
            accessibilityState={{ selected: isActive }}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <Text
              style={[
                styles.presetText,
                isActive && styles.presetTextActive,
              ]}
            >
              {preset.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

// ── TimelineScrubber ─────────────────────────────────────────────────────
// PanResponder 기반 드래그 → frame index 계산. UI-SPEC §Surface 1 정합.
// scrubber 높이 36, track 두께 4, handle (현재 위치) brand 색.
interface TimelineScrubberProps {
  totalFrames: number;
  currentFrame: number;
  onFrameChange: (frame: number) => void;
}
function TimelineScrubber({
  totalFrames,
  currentFrame,
  onFrameChange,
}: TimelineScrubberProps) {
  const trackWidthRef = useRef<number>(0);

  const handleLayout = (e: LayoutChangeEvent) => {
    trackWidthRef.current = e.nativeEvent.layout.width;
  };

  const seekToLocationX = (locationX: number) => {
    const w = trackWidthRef.current;
    if (!w || totalFrames <= 0) return;
    const ratio = Math.max(0, Math.min(1, locationX / w));
    const f = Math.round(ratio * (totalFrames - 1));
    onFrameChange(f);
  };

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => totalFrames > 1,
        onMoveShouldSetPanResponder: () => totalFrames > 1,
        onPanResponderGrant: (e: GestureResponderEvent) =>
          seekToLocationX(e.nativeEvent.locationX),
        onPanResponderMove: (e: GestureResponderEvent) =>
          seekToLocationX(e.nativeEvent.locationX),
      }),
    // seekToLocationX 는 totalFrames / onFrameChange 의존. eslint disable 없이
    // dependency array 명시.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [totalFrames, onFrameChange],
  );

  const progress =
    totalFrames > 1
      ? Math.max(0, Math.min(1, currentFrame / (totalFrames - 1)))
      : 0;

  return (
    <View
      style={styles.scrubberContainer}
      accessibilityRole="adjustable"
      accessibilityLabel="자세 시간 조절"
      accessibilityValue={{
        min: 0,
        max: Math.max(0, totalFrames - 1),
        now: currentFrame,
      }}
    >
      <View
        style={styles.scrubberTrack}
        onLayout={handleLayout}
        {...panResponder.panHandlers}
      >
        <View style={styles.scrubberTrackBg} />
        <View
          style={[
            styles.scrubberTrackFill,
            { width: `${progress * 100}%` },
          ]}
        />
        <View
          style={[
            styles.scrubberHandle,
            { left: `${progress * 100}%` },
          ]}
        />
      </View>
    </View>
  );
}

// ── PoseViewer3D (메인) ──────────────────────────────────────────────────
interface PoseViewer3DProps {
  joints: number[][][] | null; // (T, J, 3) — reshapePose3dData 결과
  // Wave 2 = user-only viewer (HIGH-3). caller 가 omit. 예약 prop.
  referenceJoints?: number[][][] | null;
  ipsfViolationFrames?: number[];
  currentFrame: number;
  onFrameChange: (frame: number) => void;
}

export function PoseViewer3D({
  joints,
  // referenceJoints: 본 wave 미사용 (HIGH-3). 의도적으로 destructure 만.
  referenceJoints: _referenceJoints,
  ipsfViolationFrames,
  currentFrame,
  onFrameChange,
}: PoseViewer3DProps) {
  // joints null = Phase 4 이전 분석 doc / joints3d 없는 분석 — 섹션 graceful
  // 생략. (UI-SPEC §Surface 1 상태별 UI 박제).
  if (!joints || joints.length === 0) return null;

  const totalFrames = joints.length;
  const safeFrameIdx = Math.max(0, Math.min(totalFrames - 1, currentFrame));
  const frame = joints[safeFrameIdx];
  const isIpsfViolation =
    ipsfViolationFrames?.includes(safeFrameIdx) ?? false;

  // CameraPresetBar active state — 본 wave 에서는 button tap 시 OrbitControls
  // 가 사용자 제스처로 다시 회전시키므로 단순 시각적 토글로 유지.
  // 카메라 위치 자체는 Canvas camera prop 으로 1회 설정 + drei OrbitControls
  // 가 사용자 입력 수신.
  const [activePreset, setActivePreset] =
    React.useState<CameraPresetKey>('front');

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.sectionTitle}>3D 자세 뷰어</Text>
        <Text style={styles.hint}>손가락으로 돌려보세요</Text>
      </View>
      <ErrorBoundary>
        <View
          style={styles.canvas}
          accessibilityRole="image"
          accessibilityLabel="3D 자세 뷰어, 손가락으로 회전 가능"
        >
          <Canvas
            camera={{
              position: CAMERA_PRESETS.find((p) => p.key === activePreset)
                ?.position ?? [0, 0, 3],
              fov: 50,
            }}
            gl={{ powerPreference: 'high-performance' }}
          >
            {/* scene.background = viewer3dBg (#F5F5F5). 다크 배경 금지. */}
            <color attach="background" args={[colors.viewer3dBg]} />
            <ambientLight intensity={0.6} />
            <directionalLight position={[2, 2, 2]} intensity={0.4} />
            <SkeletonMesh frame={frame} isIpsfViolation={isIpsfViolation} />
            {/* drei OrbitControls /native 직접 사용 (resume-signal
                "approved OrbitControls:true" 박제). UI-SPEC §인터랙션 — 회전 /
                줌 / 더블탭 리셋. */}
            <OrbitControls enableRotate enableZoom enablePan={false} />
          </Canvas>
        </View>
      </ErrorBoundary>
      <CameraPresetBar active={activePreset} onSelect={setActivePreset} />
      <TimelineScrubber
        totalFrames={totalFrames}
        currentFrame={safeFrameIdx}
        onFrameChange={onFrameChange}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.bg,
    borderRadius: radius.card, // 15
    borderWidth: 1,
    borderColor: colors.divider,
    overflow: 'hidden',
    marginTop: 16,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.screenX,
    paddingVertical: 12,
  },
  sectionTitle: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
  },
  hint: {
    ...typography.captionSmall,
    color: colors.textSecondary,
  },
  canvas: {
    height: 280, // UI-SPEC 고정값
    backgroundColor: colors.viewer3dBg,
  },
  fallback: {
    height: 280,
    backgroundColor: colors.bg,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.screenX,
  },
  fallbackTitle: {
    ...typography.boxLabel,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 8,
  },
  fallbackHint: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 4,
  },
  presetBar: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: spacing.screenX,
    paddingVertical: 12,
  },
  presetButton: {
    flex: 1,
    height: 36,
    borderRadius: radius.button,
    backgroundColor: colors.softBg,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'transparent',
  },
  presetButtonActive: {
    borderColor: colors.brand,
  },
  presetText: {
    ...typography.boxLabel,
    color: colors.textPrimary,
  },
  presetTextActive: {
    color: colors.brand,
  },
  scrubberContainer: {
    paddingHorizontal: spacing.screenX,
    paddingBottom: 16,
  },
  scrubberTrack: {
    height: 36,
    justifyContent: 'center',
  },
  scrubberTrackBg: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 4,
    backgroundColor: colors.trackBg,
    borderRadius: 2,
  },
  scrubberTrackFill: {
    position: 'absolute',
    left: 0,
    height: 4,
    backgroundColor: colors.brand,
    borderRadius: 2,
  },
  scrubberHandle: {
    position: 'absolute',
    width: 14,
    height: 14,
    marginLeft: -7,
    borderRadius: 7,
    backgroundColor: colors.brand,
  },
});
