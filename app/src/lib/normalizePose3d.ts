// 3D 골격 좌표 정규화 — 순수 수학 single source (TRUST-04, Phase 19-03).
//
// 왜 필요한가 (19-03 PLAN objective + 19-RESEARCH Pattern 4 + Pitfall 3):
//   joints3d 는 RAW RTMW 좌표(x,y ~0-640 픽셀, uncentered, z MotionBert-scale,
//   pole_aligned 회전만)인데 PoseViewer3D 는 origin-centered normalized 좌표를
//   기대한다 (camera position [0,0,3], fov 50, sphere r=0.04). 골격 중심
//   ~(320,240) 의 수백 단위 spread 가 frustum 밖으로 나가 GL 이 빈 회색으로
//   clear → 골격이 보이지 않는 버그. 정규화를 읽는 쪽(joints.ts
//   reshapePose3dData)에 두어 backend·3중 계약 불변 + 과거 doc(raw 픽셀좌표)도
//   즉시 정규화한다.
//
// single source (19-REVIEWS iter-2 BLOCKER-2 / iter-3 HIGH-1):
//   정규화 순수 수학은 이 모듈이 유일한 source 다. joints.ts 와 smoke 스크립트가
//   둘 다 이 함수를 import 한다 (알고리즘 복제 금지). 그러려면 이 모듈은
//   react/expo/RN import 0 의 완전 standalone TS 여야 한다 — LOCAL tsc 로 단독
//   파일 컴파일이 가능해야 smoke 가 production 함수를 그대로 검증할 수 있다.
//   따라서 내장(Number/Math/Array)만 사용한다.
//
// hip/shoulder 인덱스 (19-REVIEWS iter-1 HIGH-3):
//   jointKeys 인자(joints3dKeys = COCO-17 skeleton.KEYPOINT_NAMES)에서
//   indexOf('left_hip') 등으로 도출한다. 8 angle JOINT_KEYS 참조 금지 —
//   그 키셋은 어깨/팔꿈치/엉덩이/무릎 8개라 인덱스가 다르다.
//
// frame 수 보존 (19-REVIEWS iter-2 HIGH-4):
//   PoseViewer3D 의 timeline(currentFrame / ipsfViolationFrames)이 frame 을
//   인덱싱하므로 per-frame null/drop 은 desync 를 일으킨다. 출력 frame 수는
//   반드시 입력과 같다. 정규화 불가 frame 의 last-resort = (1) 직전 valid 정규화
//   frame 복제 또는 (2) finite all-zero skeleton(J × [0,0,0]). 시퀀스 전체가
//   안전 정규화 불가면 whole-sequence null 을 반환한다.
//
// DoS 가드 (19-RESEARCH Security V5/DoS, threat T-19-05/06):
//   torso < epsilon → centroid+bbox fallback (0-div 차단). 모든 산출 좌표는
//   Number.isFinite 로 sanity 검증 (NaN/Inf 0건). raw passthrough 금지.

const HIP_LEFT = 'left_hip';
const HIP_RIGHT = 'right_hip';
const SHOULDER_LEFT = 'left_shoulder';
const SHOULDER_RIGHT = 'right_shoulder';

// torso length / scale 분모가 이보다 작으면 0-div 위험 → fallback.
const EPSILON = 1e-6;

interface JointIndices {
  li: number;
  ri: number;
  lsi: number;
  rsi: number;
}

function isFiniteXyz(p: unknown): p is number[] {
  return (
    Array.isArray(p) &&
    p.length === 3 &&
    Number.isFinite(p[0]) &&
    Number.isFinite(p[1]) &&
    Number.isFinite(p[2])
  );
}

function zeroSkeleton(jointCount: number): number[][] {
  const frame: number[][] = [];
  for (let j = 0; j < jointCount; j++) frame.push([0, 0, 0]);
  return frame;
}

// primary: hip midpoint center + torso(어깨중점↔엉덩이중점) length scale.
// hip/shoulder 모두 finite 여야 하고 torso >= EPSILON 이어야 한다.
function normalizePrimary(
  frame: number[][],
  idx: JointIndices,
): number[][] | null {
  const lh = frame[idx.li];
  const rh = frame[idx.ri];
  const ls = frame[idx.lsi];
  const rs = frame[idx.rsi];
  if (!isFiniteXyz(lh) || !isFiniteXyz(rh)) return null;
  if (!isFiniteXyz(ls) || !isFiniteXyz(rs)) return null;

  const hipMid = [
    (lh[0] + rh[0]) / 2,
    (lh[1] + rh[1]) / 2,
    (lh[2] + rh[2]) / 2,
  ];
  const shoulderMid = [
    (ls[0] + rs[0]) / 2,
    (ls[1] + rs[1]) / 2,
    (ls[2] + rs[2]) / 2,
  ];
  const dx = shoulderMid[0] - hipMid[0];
  const dy = shoulderMid[1] - hipMid[1];
  const dz = shoulderMid[2] - hipMid[2];
  const torso = Math.sqrt(dx * dx + dy * dy + dz * dz);
  if (!Number.isFinite(torso) || torso < EPSILON) return null;

  const out: number[][] = [];
  for (let j = 0; j < frame.length; j++) {
    const p = frame[j];
    if (!isFiniteXyz(p)) {
      // 개별 관절 누락은 hip-center 기준 0 (origin) 으로 둔다 — finite 보장.
      out.push([0, 0, 0]);
      continue;
    }
    out.push([
      (p[0] - hipMid[0]) / torso,
      (p[1] - hipMid[1]) / torso,
      (p[2] - hipMid[2]) / torso,
    ]);
  }
  return out;
}

// fallback: hip/shoulder index -1 또는 좌표 non-finite, 또는 torso < epsilon.
// finite 관절 centroid center + max-axis range scale 정규화 (raw passthrough 금지).
function normalizeFallback(frame: number[][]): number[][] | null {
  const finite: number[][] = [];
  for (let j = 0; j < frame.length; j++) {
    if (isFiniteXyz(frame[j])) finite.push(frame[j]);
  }
  if (finite.length === 0) return null;

  let sx = 0;
  let sy = 0;
  let sz = 0;
  let minX = Infinity;
  let minY = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let maxZ = -Infinity;
  for (const p of finite) {
    sx += p[0];
    sy += p[1];
    sz += p[2];
    if (p[0] < minX) minX = p[0];
    if (p[1] < minY) minY = p[1];
    if (p[2] < minZ) minZ = p[2];
    if (p[0] > maxX) maxX = p[0];
    if (p[1] > maxY) maxY = p[1];
    if (p[2] > maxZ) maxZ = p[2];
  }
  const cx = sx / finite.length;
  const cy = sy / finite.length;
  const cz = sz / finite.length;
  const range = Math.max(maxX - minX, maxY - minY, maxZ - minZ);
  if (!Number.isFinite(range) || range < EPSILON) return null;

  const out: number[][] = [];
  for (let j = 0; j < frame.length; j++) {
    const p = frame[j];
    if (!isFiniteXyz(p)) {
      out.push([0, 0, 0]);
      continue;
    }
    out.push([
      (p[0] - cx) / range,
      (p[1] - cy) / range,
      (p[2] - cz) / range,
    ]);
  }
  return out;
}

function allFinite(frame: number[][]): boolean {
  for (const p of frame) {
    if (!isFiniteXyz(p)) return false;
  }
  return true;
}

/**
 * (T, J, 3) raw 좌표를 origin-centered normalized 좌표로 정규화한다.
 *
 * frame 수 보존: 출력 길이 == 입력 길이 (또는 시퀀스 전체 정규화 불가 시 null).
 * per-frame null/drop 금지 — last-resort = prev valid 복제 또는 zero skeleton.
 *
 * @param frames (T, J, 3) raw 좌표.
 * @param jointKeys 길이 J 의 joint 이름 list (COCO-17 KEYPOINT_NAMES).
 * @returns origin-centered normalized (T, J, 3). 전체 불가 시 null.
 */
export function normalizeFrames(
  frames: number[][][],
  jointKeys: string[],
): number[][][] | null {
  if (!Array.isArray(frames) || frames.length === 0) return null;
  if (!Array.isArray(jointKeys)) return null;

  // hip/shoulder 인덱스를 jointKeys(COCO-17) 에서 1회 도출 (HIGH-3 — 8 angle
  // JOINT_KEYS 아님). -1 이면 normalizePrimary 가 fallback 으로 분기.
  const idx: JointIndices = {
    li: jointKeys.indexOf(HIP_LEFT),
    ri: jointKeys.indexOf(HIP_RIGHT),
    lsi: jointKeys.indexOf(SHOULDER_LEFT),
    rsi: jointKeys.indexOf(SHOULDER_RIGHT),
  };
  const hasTorsoKeys =
    idx.li >= 0 && idx.ri >= 0 && idx.lsi >= 0 && idx.rsi >= 0;

  const out: number[][][] = [];
  let prevValid: number[][] | null = null;
  let anyNormalized = false;

  for (let t = 0; t < frames.length; t++) {
    const frame = Array.isArray(frames[t]) ? frames[t] : [];
    const jointCount = frame.length;

    let normalized: number[][] | null = null;
    if (hasTorsoKeys) normalized = normalizePrimary(frame, idx);
    if (normalized === null) normalized = normalizeFallback(frame);

    if (normalized !== null && allFinite(normalized)) {
      // 산출 후 sanity 통과 — valid frame.
      out.push(normalized);
      prevValid = normalized;
      anyNormalized = true;
    } else if (
      prevValid !== null &&
      prevValid.length === (jointCount > 0 ? jointCount : jointKeys.length)
    ) {
      // last-resort (1): 직전 valid 정규화 frame 복제 (frame 수 보존).
      // WR-04: prevValid 의 관절 수가 현재 frame 기대치와 같을 때만 복제.
      // 다르면(잘린/깨진 frame) 복제 시 frame 별 관절 수가 어긋나 PoseViewer3D
      // 인덱싱이 out-of-bounds 될 수 있다 → 기대 관절 수의 zero-skeleton 폴백.
      out.push(prevValid.map((p) => [p[0], p[1], p[2]]));
    } else {
      // last-resort (2): finite all-zero skeleton (직전 valid 없음 또는 관절 수 불일치).
      out.push(zeroSkeleton(jointCount > 0 ? jointCount : jointKeys.length));
    }
  }

  // 시퀀스 전체가 정규화 불가 (모든 frame 이 zero-skeleton fallback) → null
  // (number[][][]|null 계약 준수, HIGH-4).
  if (!anyNormalized) return null;

  return out;
}
