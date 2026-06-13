// Phase 4 Wave 2 — PoseViewer3DSmokeScreen (R8 blocking checkpoint 전용).
//
// 박제 정신 (04-02 PLAN Task 1, R8):
//   · result.tsx 에 PoseViewer3D 를 통합하기 전, R3F Canvas (@react-three/fiber/native) +
//     expo-gl + 제스처 입력이 실기기 (iOS TestFlight) 에서 정상 마운트/회전되는지
//     단독 smoke 검증을 수행하기 위한 feature-flag 전용 컴포넌트.
//   · 실기기 검증 (Task 2 checkpoint) 통과 전에는 결과 화면(result.tsx)에 절대 연결하지
//     않는다 — GL 초기화 실패가 결과 화면 전체 route 를 죽이는 회귀 차단 (R8).
//   · 본 파일은 검증 후에도 보존 — Wave 5+ 회귀 검증, 신규 기기 추가, R3F 버전 업
//     이후 재검증 시 재사용.
//
// 다크 배경 금지 (CLAUDE.md §4 / design.md §10): 캔버스 배경 colors.softBg (#F5F5F5).
// /native import 경로 필수 (RESEARCH Pitfall 2): @react-three/fiber/native 사용.
//   web path (@react-three/fiber) 사용 시 RN 에서 'window is not defined' 즉시 crash.
//
// 박제: Task 1 단계에서 본 파일은 Task 3 에서 신설할 viewer3dBg/viewer3dJointNormal
// alias 토큰 (현 시점 미존재) 에 의존하지 않는다. 동일 hex (softBg, textSecondary)
// 의 기존 토큰을 직접 사용 — Wave 분리 invariant 유지.

import { Canvas } from '@react-three/fiber/native';
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing, typography } from '../theme';

// ── GL/Canvas ErrorBoundary (R8) ────────────────────────────────────────
// expo-gl GL 컨텍스트 초기화 실패 / Three.js 마운트 충돌 / 구형 기기 호환성
// 이슈로 throw 가 나도 result.tsx route 전체가 죽지 않도록 격리. fallback 은
// design.md §0 빈 상태 패턴 정합 — 별도 CTA 없이 일반 결과 확인 안내.
interface SmokeErrorBoundaryProps {
  children: React.ReactNode;
}
interface SmokeErrorBoundaryState {
  hasError: boolean;
}
class SmokeErrorBoundary extends React.Component<
  SmokeErrorBoundaryProps,
  SmokeErrorBoundaryState
> {
  constructor(props: SmokeErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(): SmokeErrorBoundaryState {
    return { hasError: true };
  }
  componentDidCatch(error: Error): void {
    if (__DEV__) console.warn('[PoseViewer3DSmokeScreen] GL/Canvas init failed', error);
  }
  render() {
    if (this.state.hasError) {
      return (
        <View style={styles.fallback}>
          <Text style={styles.fallbackTitle}>3D 뷰어를 불러오지 못했어요.</Text>
          <Text style={styles.fallbackHint}>일반 결과는 아래에서 확인하세요.</Text>
        </View>
      );
    }
    return this.props.children;
  }
}

// ── 간단 stick figure (sanity check 용) ────────────────────────────────
// 정식 SkeletonMesh 는 Task 4 PoseViewer3D 에서 구현. 본 smoke 화면은 R3F /
// expo-gl 컨텍스트가 살아 있는지만 검증하므로 sphere 3개 + line 1개로 최소화.
function SmokeStickFigure() {
  return (
    <>
      {/* 머리 */}
      <mesh position={[0, 1, 0]}>
        <sphereGeometry args={[0.15, 16, 16]} />
        <meshStandardMaterial color={colors.textSecondary} />
      </mesh>
      {/* 어깨 */}
      <mesh position={[-0.3, 0.4, 0]}>
        <sphereGeometry args={[0.08, 12, 12]} />
        <meshStandardMaterial color={colors.textSecondary} />
      </mesh>
      <mesh position={[0.3, 0.4, 0]}>
        <sphereGeometry args={[0.08, 12, 12]} />
        <meshStandardMaterial color={colors.textSecondary} />
      </mesh>
      {/* 골반 */}
      <mesh position={[0, -0.4, 0]}>
        <sphereGeometry args={[0.08, 12, 12]} />
        <meshStandardMaterial color={colors.textSecondary} />
      </mesh>
    </>
  );
}

export function PoseViewer3DSmokeScreen() {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.sectionTitle}>3D 뷰어 smoke</Text>
        <Text style={styles.hint}>손가락으로 돌려보세요</Text>
      </View>
      <SmokeErrorBoundary>
        <View
          style={styles.canvas}
          accessibilityRole="image"
          accessibilityLabel="3D 자세 뷰어 smoke, 손가락으로 회전 가능"
        >
          {/* /native Canvas — expo-gl GLView 기반 */}
          <Canvas
            camera={{ position: [0, 0, 3], fov: 50 }}
            gl={{ powerPreference: 'high-performance' }}
          >
            {/* Three.js scene background = colors.softBg (#F5F5F5).
                다크 배경 금지 박제 — colors.softBg 와 동일 hex int. */}
            <color attach="background" args={[colors.softBg]} />
            <ambientLight intensity={0.6} />
            <directionalLight position={[2, 2, 2]} intensity={0.4} />
            <SmokeStickFigure />
          </Canvas>
        </View>
      </SmokeErrorBoundary>
      <Text style={styles.footnote}>
        smoke 통과 시 PoseViewer3D 본체를 결과 화면에 통합할 수 있어요.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.bg,
    borderRadius: radius.card,
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
    height: 280,
    backgroundColor: colors.softBg,
  },
  footnote: {
    ...typography.caption,
    color: colors.textSecondary,
    paddingHorizontal: spacing.screenX,
    paddingVertical: 12,
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
  },
  fallbackHint: {
    ...typography.caption,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 4,
  },
});
