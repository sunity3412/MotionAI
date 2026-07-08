// 정렬 목표시각 계산의 단일 출처 — `rightPlayer.currentTime =` 는 전부 여기 경유
// (28-RESEARCH Pitfall 7: warp 누락 경로가 있으면 스크럽 직후 drift 연발 stutter).
// 순수 함수만 (player/react 의존 0 — `tsc --noEmit` 만으로 검증 가능).
//
// 계약 원칙 (28-CONTEXT D-01/D-02): 학생(left)=master 로 시계 불변, 정은지(right)만
// warp(tStudent)→tRef 로 따라간다.
//   tier='warped'   = 구간 가변속도 (구간 기울기 clamp [RATE_MIN, RATE_MAX]).
//   tier='trim_only'= 트림+오프셋만 (가변속도 끔 — 첫 앵커 기준 평행이동).
//   tier='disabled' = 현행 절대시계 (워핑 없음, identity).
//
// MotionAlignment 계약의 단일 출처는 analysis.ts (28-03 이 이관 완료). 28-06 에서
// 로컬 정의를 제거하고 계약을 import + 재수출한다 — 기존 소비처(normalize/warp)
// 호환 유지 + 3-way lockstep(analysis.ts ↔ models.py ↔ contract.md §11) 단일 출처.
import type { MotionAlignment } from '../types/analysis';

export type { MotionAlignment };

// belle 고정값 (28-CONTEXT specifics) — 배속 클램프 0.5~2배. VideoCompare
// FULLSCREEN_ZOOM 승인값 주석 관례와 동일: 감으로 변경 금지, 출처 박제.
export const RATE_MIN = 0.5;
export const RATE_MAX = 2.0;

const VALID_TIERS = ['warped', 'trim_only', 'disabled'] as const;
const VALID_SOURCES = ['dtw', 'vlm'] as const;
// Firestore 40k index-entry 안전 상한 (28-RESEARCH Pitfall 2) — 백엔드 validator 와 대칭.
const MAX_ANCHOR_FLOATS = 512;

function clampRate(rate: number): number {
  return Math.min(RATE_MAX, Math.max(RATE_MIN, rate));
}

// anchors flat → (us, rs) 쌍 배열. anchorCount 를 신뢰하지 않고 anchors.length 로
// 직접 도출 (단일 출처 — 방어적 소비).
function readPairs(anchors: number[]): { us: number[]; rs: number[] } {
  const us: number[] = [];
  const rs: number[] = [];
  for (let k = 0; k + 1 < anchors.length; k += 2) {
    us.push(anchors[k]);
    rs.push(anchors[k + 1]);
  }
  return { us, rs };
}

/**
 * 학생 시각 tStudent → 정은지(기준) 목표 시각 tRef.
 * warped: 앵커 구간 선형보간 + 범위 밖 기울기 1.0 연장 (경계 특수분기 0).
 * trim_only: 첫 앵커 기준 오프셋만 (D-02 트림+오프셋). disabled: identity(절대시계).
 */
export function warpTime(a: MotionAlignment, tStudent: number): number {
  // disabled — 워핑 없음. 소비측은 호출하지 않지만 방어적 identity.
  if (a.tier === 'disabled') return tStudent;

  const { us, rs } = readPairs(a.anchors);
  const n = us.length;
  // 앵커 부재 방어 (정상 계약에선 warped/trim_only 는 앵커 보유).
  if (n === 0) return tStudent;

  // trim_only — 트림+오프셋만 (D-02 tier 2, 가변속도 끔): warp(t) = t - u0 + r0.
  if (a.tier === 'trim_only') return tStudent - us[0] + rs[0];

  // warped — 범위 밖은 기울기 1.0 연장 (오프셋 연속, 특수분기 없이 매끄러움).
  if (tStudent <= us[0]) return rs[0] - (us[0] - tStudent);
  if (tStudent >= us[n - 1]) return rs[n - 1] + (tStudent - us[n - 1]);
  // 구간 선형보간.
  for (let k = 0; k + 1 < n; k += 1) {
    if (tStudent >= us[k] && tStudent < us[k + 1]) {
      const slope = (rs[k + 1] - rs[k]) / (us[k + 1] - us[k]);
      return rs[k] + (tStudent - us[k]) * slope;
    }
  }
  return rs[n - 1]; // 도달 불가 방어
}

/**
 * 현재 구간의 정은지 재생 배속 = 구간 기울기 clamp(RATE_MIN, RATE_MAX).
 * trim_only / disabled → 1.0 (가변속도 끔, D-02). 범위 밖 → 1.0 (기울기 1.0 연장).
 */
export function segmentRate(a: MotionAlignment, tStudent: number): number {
  if (a.tier !== 'warped') return 1.0;
  const { us, rs } = readPairs(a.anchors);
  const n = us.length;
  if (n < 2) return 1.0;
  if (tStudent <= us[0] || tStudent >= us[n - 1]) return 1.0;
  for (let k = 0; k + 1 < n; k += 1) {
    if (tStudent >= us[k] && tStudent < us[k + 1]) {
      const slope = (rs[k + 1] - rs[k]) / (us[k + 1] - us[k]);
      return clampRate(slope);
    }
  }
  return 1.0;
}

/**
 * Firestore 미가공 alignment → 검증된 MotionAlignment | null (userAnalyses normalize 형상).
 * null = legacy 폴백 (필드 무시 후 현행 절대시계 — 크래시 0, V5 방어적 소비).
 * 비단조 u / NaN·Inf / 홀수 길이 / anchors < 4 float / 512 초과 / tier·source 미등재 → null.
 * 예외: tier==='disabled' 는 anchors.length===0 허용 (degenerate 방출 형상 — 짝수·4 이상
 *       규칙을 disabled 에 한해 면제. D-02 3단 안내가 배지로 살아야 함, 28-02 규칙 7 과 대칭).
 */
export function normalizeMotionAlignment(value: unknown): MotionAlignment | null {
  if (value == null || typeof value !== 'object') return null;
  const v = value as Record<string, unknown>;

  if (typeof v.version !== 'string') return null;
  if (
    typeof v.source !== 'string' ||
    !(VALID_SOURCES as readonly string[]).includes(v.source)
  ) {
    return null;
  }
  if (
    typeof v.tier !== 'string' ||
    !(VALID_TIERS as readonly string[]).includes(v.tier)
  ) {
    return null;
  }
  if (typeof v.distance !== 'number' || !Number.isFinite(v.distance)) return null;
  if (!Array.isArray(v.anchors)) return null;

  // anchors 전수 유한 검사 (NaN/Inf → null, DoS/크래시 가드 V5).
  const anchors: number[] = [];
  for (const x of v.anchors) {
    if (typeof x !== 'number' || !Number.isFinite(x)) return null;
    anchors.push(x);
  }
  if (anchors.length > MAX_ANCHOR_FLOATS) return null;
  if (anchors.length % 2 !== 0) return null; // 홀수 = 쌍 미형성

  const version = v.version;
  const source = v.source as MotionAlignment['source'];
  const tier = v.tier as MotionAlignment['tier'];
  const distance = v.distance;
  const reason = typeof v.reason === 'string' ? { reason: v.reason } : {};

  if (tier === 'disabled') {
    // degenerate 방출 형상 — anchors.length===0 허용. 비어있지 않으면 그대로 통과
    // (빈 배열 강제 아님) — 위 유한·짝수·상한 검사는 형식 안전상 통과해야 함.
    return {
      version,
      source,
      tier,
      ...reason,
      anchors,
      anchorCount: anchors.length / 2,
      distance,
    };
  }

  // warped / trim_only — 앵커 2쌍(4 float) 이상 + 단조성 필수 (워핑 유효 조건).
  if (anchors.length < 4) return null;
  const { us, rs } = readPairs(anchors);
  for (let k = 0; k + 1 < us.length; k += 1) {
    if (!(us[k] < us[k + 1])) return null; // u strictly increasing
    if (!(rs[k] <= rs[k + 1])) return null; // r non-decreasing
  }

  return {
    version,
    source,
    tier,
    ...reason,
    anchors,
    anchorCount: anchors.length / 2,
    distance,
  };
}
