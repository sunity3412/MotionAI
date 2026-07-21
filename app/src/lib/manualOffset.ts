// 동작 비교 수동 오프셋 합성 + legacy 폴백 오프셋 산출 (32-02 D-16).
//
// 순수 함수만 (player/react/expo 의존 0 — `tsc --noEmit` + `node --test` 로 검증).
// alignmentWarp.ts 헤더 관례와 동일: warp 목표시각 계산은 순수 함수로 격리해,
// 재생 제어(rate/seek/tick)의 부작용과 분리한다.
//
// D-16 (32-CONTEXT): DTW 신뢰가 낮아도 정렬을 "끄지" 않는다 — 구간 시작 오프셋을
// 자동 적용("대략 맞춤")하고, 사용자가 ±초 슬라이더로 미세조정한다. 두 조작 모두
// 여기서 산출한 스칼라 초(sec) 오프셋으로 표현되어 VideoCompare 의 단일 warp
// 경유 지점(clampRefTarget)에서 합성된다.
//
// fps 도메인 분리 (SP-6): 프레임↔초 환산은 호출부가 각자의 keypointReport.fps 로
// 넘긴다. 9/18 하드코딩 금지 — user(9fps angles)/ref(18fps kr) 공간 혼합 방지.

/**
 * warp 목표시각(raw)에 수동/legacy 오프셋(sec)을 합성하고 [0, durationRef] 로 클램프.
 *
 * - durationRef 가 유효(양수)면 [0, durationRef] 로 클램프한다.
 * - durationRef 가 0/음수/NaN(아직 duration 미산정 등)이면 상한 없이 max(0, composed)
 *   로만 방어한다 — 음수 seek 로 인한 재생 루프 크래시/버벅 0 (T-32-04).
 * - raw/manualOffsetSec 가 비유한(NaN/Inf)이면 0 으로 폴백해 NaN 을 방출하지 않는다
 *   (released player·미초기화 값 방어).
 */
export function composeRefTarget(
  raw: number,
  manualOffsetSec: number,
  durationRef: number,
): number {
  const base = Number.isFinite(raw) ? raw : 0;
  const off = Number.isFinite(manualOffsetSec) ? manualOffsetSec : 0;
  const composed = base + off;
  return durationRef > 0
    ? Math.max(0, Math.min(composed, durationRef))
    : Math.max(0, composed);
}

/**
 * legacy doc(정렬 disabled/부재)에서 faultZoomComparisons 프레임 인덱스 쌍들로부터
 * "대략" 시작 오프셋(sec)을 산출한다. 각 유효 쌍의 오프셋
 *   refFrameIdx / refFps − userFrameIdx / userFps
 * 를 구해 그 **median** 을 반환한다 (리뷰 MEDIUM — 단일 쌍이 아니라 배열 전체로 받아
 * 이상치 1개가 오프셋을 지배하지 못하게 한다).
 *
 * 유효 쌍 = userFrameIdx·refFrameIdx 가 정수(≥0) + refMatched !== false
 * (legacy doc 은 refMatched 필드 부재 가능 → 부재는 유효로 취급). 유효 쌍이 0 이면
 * null 을 반환한다 (폴백 불가 — 이 경우 화면은 수동 슬라이더만 제공).
 *
 * fps 는 인자로만 받는다 (9/18 하드코딩 금지, SP-6). 0/음수/비유한 fps 는 나눗셈이
 * 불가하므로 null.
 */
export function legacyOffsetFromCompareFrames(
  comparisons:
    | { userFrameIdx?: number; refFrameIdx?: number; refMatched?: boolean }[]
    | null,
  userFps: number,
  refFps: number,
): number | null {
  if (!Array.isArray(comparisons) || comparisons.length === 0) return null;
  if (!Number.isFinite(userFps) || userFps <= 0) return null;
  if (!Number.isFinite(refFps) || refFps <= 0) return null;

  const offsets: number[] = [];
  for (const c of comparisons) {
    if (!c) continue;
    const u = c.userFrameIdx;
    const r = c.refFrameIdx;
    if (typeof u !== 'number' || !Number.isInteger(u) || u < 0) continue;
    if (typeof r !== 'number' || !Number.isInteger(r) || r < 0) continue;
    if (c.refMatched === false) continue; // 대응 실패 쌍 제외 (부재는 유효)
    offsets.push(r / refFps - u / userFps);
  }
  if (offsets.length === 0) return null;
  return median(offsets);
}

// 정렬 후 중앙값. 짝수 개면 두 중앙값의 평균 (이상치 견고 — mean 대비).
function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0
    ? sorted[mid]
    : (sorted[mid - 1] + sorted[mid]) / 2;
}
