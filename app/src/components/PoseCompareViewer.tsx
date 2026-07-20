// 자세 비교 뷰어 — 카메라 평면 고정 2D 중첩 (Phase 31, 31-08).
//
// 근거: 31-CONTEXT D-10 [AMENDED 2026-07-19, belle — 31-PLAN-REVIEW B-01 재결정].
// 원안은 손가락 드래그로 시점을 바꾸는 뷰어였으나, RTMW 출력에는 실측 깊이가
// 없어(2D 백본 — z 전 관절 0) 시점을 바꾸면 실제로는 존재하지 않는 정보를
// 사용자에게 사실처럼 보여주게 된다. 그래서 이 뷰어는 카메라 평면을 고정하고
// "어디가 다른지" 만 보여준다. result.tsx:1191 의 구 R3F 뷰어 제거 결정과 정합.
//
// 이 파일은 three / @react-three/fiber 를 import 하지 않는다 — react-native-svg 만
// 사용한다 (OctagonScore / GrowthChart 선례). 시점 변경이 필요한 사용자 니즈는
// amended D-04 의 Wan2.7 합성 영상 카드가 전담하며, 이 컴포넌트는 그 문구를
// 일절 쓰지 않는다 (정직한 계약 = 하는 일만 말한다).
//
// 렌더 가드는 caller 소유 관례 (ScoreBreakdownSection 선례) — 데이터가 부족하면
// 여기서 null 을 반환하고, 카드/문구를 숨기는 판단은 참고코너 섹션이 한다.
// 하드코딩 색상 0 (theme 토큰만). 이모지 0. 라이트 전용.

import Svg, { Circle, Line } from 'react-native-svg';
import { StyleSheet, View } from 'react-native';

import { colors, radius } from '../theme';

// ── 투영 축 ──────────────────────────────────────────────────────────────
// [fix 2026-07-20] 가로는 두 세대 모두 축 0(x). 세로는 **문서 세대에 따라 축이
// 다르다** — 컴파일타임 상수가 이 버그의 원인이었다.
//
// joints3d 는 라벨만 "pole_aligned" 이고 실제 축 의미는 처리 시점 환경에 따라
// 두 세대가 Firestore 에 공존한다 (2026-07-20 전수 실측):
//   · y-era: 세로 = 축 1, 축 2 ≡ 0 — RTMW 2D 백본이 z 를 0 패딩하고
//     (rtmw_engine.py) 프로덕션 Pod 에 scipy 가 없어 폴 정렬(y→z 회전)이
//     ImportError 폴백으로 no-op (rtmw_133_to_coco17.py). 현 Pod 신규 분석 +
//     reference 6건 (power-spin/kip-up/combo/elbow-twist-sister/pdshape/peter-pan).
//   · z-era: 세로 = 축 2, 축 1 ≡ 0 — 정렬이 실제 수행되던 환경 산출.
//     reference 5건 (climb/foxtop/foxtop-split/invert/sideway-spin) + 구 분석.
//     구 주석 "z spread ~235, y≈0"(c49a075, phase 20 구 R3F 뷰어)은 이 세대 실측.
//
// 그래서 세로축은 포즈별 런타임 선택이다: 축 1/축 2 중 분산이 있는 쪽이 세로,
// 나머지(실측 전 문서에서 정확히 상수 0)는 버린다. 상수를 어느 쪽으로 골라도
// 반대 세대 문서가 가로 한 줄로 깔린다 (AXIS_V=2 시절 이 파일의 버그가 그것).
// 31-08 이 세로 "부호"를 런타임 결정(어깨가 고관절 위)한 것과 같은 철학의 축
// 버전이고, phase 20 remapFrameForFrontView 가 같은 증상을 같은 방식으로 고친
// 선례다. 진짜 3D(양축 동시 분산) 문서는 현 코퍼스에 0건 — 그런 데이터가 오면
// "더 큰 분산" 선택이 최선 근사다.
const AXIS_H = 0;

/**
 * 포즈별 세로축 선택: 축 1(y-era) vs 축 2(z-era) 중 분산이 큰 쪽.
 *
 * 실측 코퍼스에서는 두 후보 중 정확히 한 축이 상수 0 이라 판별이 무모호하다.
 * 유한값이 하나도 없거나 분산이 같으면 축 1 — 이후 몸통 길이 가드가 퇴화
 * 포즈를 null 로 걸러 뷰어를 숨긴다 (억지로 그리지 않는다).
 */
function pickVerticalAxis(pose: number[][]): 1 | 2 {
  let min1 = Infinity;
  let max1 = -Infinity;
  let min2 = Infinity;
  let max2 = -Infinity;
  for (const p of pose) {
    if (!Array.isArray(p)) continue;
    const v1 = p[1];
    const v2 = p[2];
    if (Number.isFinite(v1)) {
      if (v1 < min1) min1 = v1;
      if (v1 > max1) max1 = v1;
    }
    if (Number.isFinite(v2)) {
      if (v2 < min2) min2 = v2;
      if (v2 > max2) max2 = v2;
    }
  }
  const spread1 = max1 - min1; // 유한값 없으면 -Infinity
  const spread2 = max2 - min2;
  return spread2 > spread1 ? 2 : 1;
}

// ── COCO-17 인접 bone ────────────────────────────────────────────────────
// 이름으로 선언하고 jointKeys 로 인덱스를 해석한다 — 배열 순서를 맹신하면
// 키 순서가 바뀐 문서에서 엉뚱한 관절이 이어진다.
const BONES: readonly [string, string][] = [
  ['left_shoulder', 'right_shoulder'],
  ['left_shoulder', 'left_elbow'],
  ['left_elbow', 'left_wrist'],
  ['right_shoulder', 'right_elbow'],
  ['right_elbow', 'right_wrist'],
  ['left_shoulder', 'left_hip'],
  ['right_shoulder', 'right_hip'],
  ['left_hip', 'right_hip'],
  ['left_hip', 'left_knee'],
  ['left_knee', 'left_ankle'],
  ['right_hip', 'right_knee'],
  ['right_knee', 'right_ankle'],
];

// 뷰박스는 정사각 100 단위. 몸통(어깨중점~고관절중점) 길이를 아래 값으로
// 맞춰 두 자세를 같은 축척으로 겹친다 (체격 차이가 아니라 "형태" 비교).
const VIEW = 100;
const CENTER = VIEW / 2;
const TORSO_UNITS = 26;

type Pt = { x: number; y: number };

function isFinitePt(p: Pt | null): p is Pt {
  return p != null && Number.isFinite(p.x) && Number.isFinite(p.y);
}

function midpoint(a: Pt | null, b: Pt | null): Pt | null {
  if (!isFinitePt(a) || !isFinitePt(b)) return null;
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}

/**
 * 단일 프레임 (17,3) → 뷰박스 좌표로 정규화된 관절 맵.
 *
 * 1) 카메라 평면 2축으로 투영 — 세로축은 포즈별 런타임 선택(pickVerticalAxis),
 *    퇴화축(상수 0)은 폐기 (좌표계 축 가정 회피)
 * 2) 고관절 중점을 원점으로 이동
 * 3) 몸통 길이로 스케일 → 두 자세가 같은 크기로 겹침
 * 4) 어깨가 항상 고관절보다 위에 오도록 세로 부호 결정 (좌표계 부호 가정 회피)
 *
 * 필수 기준점(양 어깨/양 고관절)이 없거나 몸통 길이가 0 에 가까우면 null —
 * 축척을 정할 수 없는 자세를 억지로 그리지 않는다.
 */
function normalizePose(
  pose: number[][],
  indexOf: Map<string, number>,
): Map<string, Pt> | null {
  // 사용자/기준이 서로 다른 세대일 수 있어(구 분석 × 현 참조) 포즈마다 고른다.
  const axisV = pickVerticalAxis(pose);
  const rawAt = (name: string): Pt | null => {
    const i = indexOf.get(name);
    if (i == null) return null;
    const p = pose[i];
    if (!Array.isArray(p)) return null;
    const x = p[AXIS_H];
    const y = p[axisV];
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
    return { x, y };
  };

  const hipMid = midpoint(rawAt('left_hip'), rawAt('right_hip'));
  const shoulderMid = midpoint(rawAt('left_shoulder'), rawAt('right_shoulder'));
  if (!isFinitePt(hipMid) || !isFinitePt(shoulderMid)) return null;

  const torso = Math.hypot(
    shoulderMid.x - hipMid.x,
    shoulderMid.y - hipMid.y,
  );
  if (!Number.isFinite(torso) || torso < 1e-6) return null;
  const scale = TORSO_UNITS / torso;

  // 어깨가 고관절보다 화면 위(작은 y)에 오도록. SVG 는 y 가 아래로 증가하므로
  // 원좌표에서 어깨가 큰 값이면 뒤집는다.
  const vSign = shoulderMid.y >= hipMid.y ? -1 : 1;

  const out = new Map<string, Pt>();
  for (const name of indexOf.keys()) {
    const raw = rawAt(name);
    if (!isFinitePt(raw)) continue;
    out.set(name, {
      x: CENTER + (raw.x - hipMid.x) * scale,
      y: CENTER + (raw.y - hipMid.y) * scale * vSign,
    });
  }
  return out;
}

function Skeleton({
  points,
  stroke,
  strokeWidth,
  opacity,
  showJoints,
}: {
  points: Map<string, Pt>;
  stroke: string;
  strokeWidth: number;
  opacity: number;
  showJoints: boolean;
}) {
  return (
    <>
      {BONES.map(([a, b]) => {
        const pa = points.get(a) ?? null;
        const pb = points.get(b) ?? null;
        if (!isFinitePt(pa) || !isFinitePt(pb)) return null;
        return (
          <Line
            key={`${a}-${b}`}
            x1={pa.x}
            y1={pa.y}
            x2={pb.x}
            y2={pb.y}
            stroke={stroke}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            opacity={opacity}
          />
        );
      })}
      {showJoints &&
        [...points.entries()].map(([name, p]) =>
          isFinitePt(p) ? (
            <Circle
              key={name}
              cx={p.x}
              cy={p.y}
              r={strokeWidth * 0.7}
              fill={stroke}
              opacity={opacity}
            />
          ) : null,
        )}
    </>
  );
}

/**
 * 내 자세(브랜드색 실선) 위에 목표 자세(반투명 보조색)를 겹쳐 그린다.
 *
 * userPose / refPose 는 각각 단일 프레임 (17,3) — 어느 순간을 그릴지(DTW 대응
 * 프레임 쌍)는 caller 가 FaultZoomComparison.userFrameIdx / refFrameIdx 로
 * 골라 넘긴다. 둘 중 하나라도 없으면 null (섹션이 뷰어를 숨긴다).
 */
export function PoseCompareViewer({
  userPose,
  refPose,
  jointKeys,
}: {
  userPose: number[][] | null;
  refPose: number[][] | null;
  jointKeys: string[];
}) {
  if (!userPose || !refPose || jointKeys.length === 0) return null;

  const indexOf = new Map<string, number>();
  jointKeys.forEach((k, i) => indexOf.set(k, i));

  const user = normalizePose(userPose, indexOf);
  const target = normalizePose(refPose, indexOf);
  if (!user || !target) return null;

  return (
    <View style={styles.canvas}>
      <Svg width="100%" height="100%" viewBox={`0 0 ${VIEW} ${VIEW}`}>
        {/* 목표 자세를 먼저(뒤에) — 내 자세가 항상 위로 읽히게. */}
        <Skeleton
          points={target}
          stroke={colors.neutralDark}
          strokeWidth={3}
          opacity={0.4}
          showJoints={false}
        />
        <Skeleton
          points={user}
          stroke={colors.brand}
          strokeWidth={3}
          opacity={1}
          showJoints
        />
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  canvas: {
    aspectRatio: 1,
    width: '100%',
    backgroundColor: colors.softBg,
    borderRadius: radius.listItem,
    overflow: 'hidden',
  },
});
