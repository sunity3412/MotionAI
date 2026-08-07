// 드리프트 보정 히스테리시스 — 순수 판정 + 상수 단일 출처 (quick-260807-iwp).
//
// 순수 함수만 (player/react/타이머 의존 0 — `tsc --noEmit` + `node --test` 검증).
// playbackInvariant.ts 관례와 동일: 상수·판정을 순수 모듈이 소유하고 VideoCompare
// 는 import 해 호출만 한다. "언제 보정 seek 를 쏘는가"만 정하고, 실제 seek 는
// VideoCompare 의 tick 이 한다.
//
// **재균형 이력 (판정 근거)**
//
// Build 16(iter-2)은 UAT 5차에서 drift 1-2s 누적(보정 후 0.15 미만으로 안 들어와
// 다음 보정을 못 하는 사이 누적) finding 으로 hysteresis 를 제거하고 "stutter 위험
// < 동기화 우선" 절충을 택했다 — 매 tick(100ms) drift > 0.2s 면 즉시 seek.
//
// belle 08-07 실기기 "정은지 선수 영상이 끊겨 가지구" 관측이 재균형 근거다: 잦은
// 보정 seek 자체가 기준(우) 패널 스터터로 읽힌다. 재균형 =
//   - 임계 0.2 → 0.3s (경미한 drift 는 관용)
//   - 보정 seek 최소 간격 0.8s (연속 seek 금지 — 간격 내엔 대기)
// 간격 내엔 대기하고 간격 경과 후 여전히 초과면 반드시 보정하므로(tick 100ms 상시
// 재판정) Build 16 이 막으려던 "보정 불능 drift 누적"은 재발하지 않는다 — 수렴은
// 보장되고 보정 빈도만 초당 최대 ~1.25회로 제한된다.

// 보정 진입 임계(초). Build 16 의 0.2 에서 0.3 으로 완화 (belle 08-07 재균형).
export const DRIFT_CORRECT_THRESHOLD_S = 0.3;

// 보정 seek 최소 간격(ms). 직전 보정 seek 후 이 간격이 지나기 전엔 임계를 넘어도
// 대기한다 (연속 seek 로 인한 기준 패널 스터터 완화).
export const DRIFT_SEEK_MIN_INTERVAL_MS = 800;

/**
 * 이번 tick 에 보정 seek 를 쏠지 판정.
 *
 * true 조건 (둘 다 만족):
 *   - driftS 가 유한 수이고 임계(DRIFT_CORRECT_THRESHOLD_S) **초과** (기존
 *     `drift >` 판정 보존 — 정확히 임계는 보정 안 함)
 *   - (nowMs - lastSeekAtMs) >= DRIFT_SEEK_MIN_INTERVAL_MS (경계 포함 — 정확히
 *     간격만큼 경과했으면 보정. lastSeekAtMs=0 최초 상태는 epoch now 대비 항상
 *     간격 초과라 즉시 허용)
 * NaN/비유한 drift 는 false (크래시 0 — 판정 불가 시 seek 안 쏨이 안전).
 */
export function shouldCorrectDrift(
  driftS: number,
  nowMs: number,
  lastSeekAtMs: number,
): boolean {
  if (!Number.isFinite(driftS)) return false;
  if (driftS <= DRIFT_CORRECT_THRESHOLD_S) return false;
  return nowMs - lastSeekAtMs >= DRIFT_SEEK_MIN_INTERVAL_MS;
}
