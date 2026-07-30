// 음성 큐 강조 형태 산출 — 사지 모양 선 / 부위 원 분기 (quick-260730-szk — 33-G S19).
//
// 승인 스펙 원본 = `.planning/phases/33-result-trust-recovery/mockups/index.html`
// (7R, belle 승인 2026-07-29):
//   `:219-228` `.legfx polyline{stroke:brand; stroke-width:5}` + `.halo{stroke-width:9}` /
//              `.legfx circle{stroke-width:4}` + `.halo{stroke-width:8}` /
//              `.legfx.pulse{animation:legpulse 1.4s ease-in-out infinite}`
//   `:219-221` "접힌 왼다리는 kp 게이트 미달+가림 → 모양 선을 긋지 않고 부위 원(circle)으로
//              표시 — '확신 없는 모양선은 긋지 않는다'"
//   `:442-443` 오른다리 hip/knee/ankle conf 0.63/0.69/0.79 = **선**,
//              왼다리 knee 0.43 · ankle 0.29 = **원** (한 컷 안에서 측별로 섞인다)
//   `:447-448` "오른다리 선 시작점 = hip 관절이 엉덩이 하단이라 선이 엉덩이를 가로질렀음
//              → hip→knee 실좌표 선분의 65% 지점부터 — 가시 다리 구간만"
//   `:449-450` "일반 규칙(A-5/33-12): 인접 관절이나 몸통을 가로지르는 연결선 금지.
//              record.jointKeys 로 키잉(동작명 하드코딩 금지)"
//
// 왜 순수 모듈인가: 이 분기는 "confidence 게이트 × 사지 체인 위 연속 구간" 이라는
// 기하 규칙이고 렌더 컴포넌트에 붙은 채로는 시뮬 없이 검증할 수 없다. 오버레이는
// 이 결과를 **좌표로 환산해 그리기만** 한다 (기하 규칙 사본 0).
//
// 자체 도출 결정 (재논의 없음 — D-39):
//   - N-10 근위 inset 은 **관절 역할로 키잉**한다: hip → 0.65 (승인본 실좌표 실측),
//     shoulder → 0 (승인본이 팔 체인 선을 제시하지 않았다 → 값 날조 금지). 역할
//     키잉이므로 등재 10동작에 같은 규칙이 흐른다 (동작명 분기 0, D-41).
//   - N-11 선의 점 집합 = focus 관절이 속한 사지 체인에서 **focus 를 포함하는 최장
//     연속 고신뢰 구간**. 승인본은 다리 record 의 jointKeys 에 ankle 이 없는데도
//     ankle 까지 그렸다(`:442`) → 규칙은 "focus 가 짚은 사지의 가시 구간 전체"이고
//     "가시 구간만" 문구가 곧 conf 게이트다.
//   - N-12 좌↔우 연결은 **체인 사전을 측별 사지 4개로만 정의**해 구조적으로 막는다.
//     조건문으로 막으면 새 criterion 에서 다시 뚫린다.
//
// 불변식:
//   - 좌표를 받지 않는다 — 좌표/여백/정규화는 오버레이 책임 (D-12 §12 "UI 단 좌표
//     산출 금지" 관례와 정합: 이 모듈은 **어느 관절을 어떤 형태로** 만 정한다).
//   - 신규 confidence 임계 0 — 호출부가 threshold 를 주입한다
//     (KeypointOverlay.KEYPOINT_LOW_CONFIDENCE_THRESHOLD 단일 선언 재사용).
//   - fail-closed: 확신 없으면 선을 원으로 강등하고, 원도 불가면 아무것도 반환하지
//     않는다 (환각 드로잉 0).
//   - RN import 0 (순수 모듈, node --test 직접 실행 가능).

import type { KeypointName } from '../types/analysis';

/** 사지 체인의 근위(몸통 쪽) 관절 역할. inset 값의 키. */
export type ProximalRole = 'hip' | 'shoulder';

export interface LimbChain {
  proximalRole: ProximalRole;
  /** 근위 → 원위 순서. 첫 원소가 근위 관절 (inset 적용 대상 판정의 전제). */
  keypoints: readonly KeypointName[];
}

/**
 * 측별 사지 4개 체인 (N-12). **좌·우가 섞인 체인은 정의하지 않는다** — 몸통을
 * 가로지르는 연결선이 자료구조 차원에서 불가능해야 한다.
 *
 * ⚠ `KeypointOverlay.BONES` 를 복사하지 말 것: BONES 는 추적 스켈레톤용이라
 * `shoulder↔shoulder` / `hip↔hip` / `shoulder↔hip` 같은 **몸통 쌍**을 포함한다.
 * 그 쌍들은 사지가 아니므로 강조 선의 체인이 될 수 없다.
 */
export const LIMB_CHAINS: readonly LimbChain[] = [
  { proximalRole: 'hip', keypoints: ['left_hip', 'left_knee', 'left_ankle'] },
  { proximalRole: 'hip', keypoints: ['right_hip', 'right_knee', 'right_ankle'] },
  {
    proximalRole: 'shoulder',
    keypoints: ['left_shoulder', 'left_elbow', 'left_hand'],
  },
  {
    proximalRole: 'shoulder',
    keypoints: ['right_shoulder', 'right_elbow', 'right_hand'],
  },
] as const;

/**
 * 근위 관절을 선의 끝점으로 쓰지 않고 다음 관절 쪽으로 밀어 넣는 비율 (N-10).
 *   hip 0.65      = 승인본 7R 실좌표 실측. hip(161.3,334.7)→knee 선분의 65% 지점이
 *                   (178.1,360.5) 이고 그것이 승인 polyline 의 시작점이다
 *                   (`mockups/index.html:447-448,452-453`).
 *   shoulder 0    = 승인본이 팔 체인 선을 제시하지 않았고, 어깨 관절 자체는 몸통을
 *                   가로지르지 않는다. **값을 만들어내지 않는다** (날조 금지).
 */
export const PROXIMAL_INSET_T: Record<ProximalRole, number> = {
  hip: 0.65,
  shoulder: 0,
};

/**
 * 강조 도형 깜빡임 주기 (ms). 승인본 `.legfx.pulse{animation:legpulse 1.4s
 * ease-in-out infinite}` + `@keyframes legpulse{0%,100%{opacity:1} 50%{opacity:.5}}`
 * 단일 선언 — 오버레이가 import 한다 (1.4s 사본 금지).
 */
export const PULSE_PERIOD_MS = 1400;

export interface FocusShapeInput {
  /** 그 음성 큐 record 가 지칭하는 관절 (projectDeductionRecordKeypoints 산출). */
  focusKeypoints: readonly KeypointName[];
  /** 현재 프레임의 keypoint confidence. 좌표 없음/결측이면 null. */
  confidenceOf: (kp: KeypointName) => number | null;
  /** 고신뢰 게이트 (호출부가 기존 상수 주입 — 신규 임계 신설 금지). */
  threshold: number;
}

export interface FocusChain {
  /** 근위 → 원위 순서의 선 점 집합 (2개 이상). */
  keypoints: KeypointName[];
  /**
   * 첫 점을 두 번째 점 쪽으로 밀어 넣을 비율. 런이 체인의 근위 관절에서 시작할
   * 때만 > 0 — knee 부터 시작하는 런은 이미 몸통 밖이라 0.
   */
  insetT: number;
}

export interface FocusShapes {
  chains: FocusChain[];
  /** 선을 그을 확신이 없는 부위 — 멤버 bounding 을 원(타원)으로 그린다. */
  circleGroups: KeypointName[][];
}

/**
 * focus 관절 → 강조 도형 분기 (순수 함수).
 *
 * 알고리즘:
 *   1. 체인마다 focus 와의 교집합이 비면 skip (그 사지는 이 큐가 지칭하지 않음).
 *   2. 체인 배열 위에서 **focus 관절을 포함하는 최장 연속 고신뢰 런**을 찾는다.
 *   3. 런 길이 ≥ 2 → 모양 선(chain). 첫 원소가 체인의 근위 관절이면 insetT 부여.
 *   4. 런 길이 < 2 → 그 체인의 focus ∩ 고신뢰 관절을 원 그룹 1묶음으로 강등.
 *      고신뢰가 0 이면 아무것도 넣지 않는다 (확신 없는 표시는 긋지 않는다).
 *   5. 어떤 체인에도 없는 focus 관절(미래 확장분)은 고신뢰인 것만 모아 원 1묶음.
 */
export function buildFocusShapes(input: FocusShapeInput): FocusShapes {
  const focus = input.focusKeypoints ?? [];
  if (focus.length === 0) return { chains: [], circleGroups: [] };

  const focusSet = new Set<KeypointName>(focus);
  const isHigh = (kp: KeypointName): boolean => {
    const c = input.confidenceOf(kp);
    return typeof c === 'number' && Number.isFinite(c) && c >= input.threshold;
  };

  const chains: FocusChain[] = [];
  const circleGroups: KeypointName[][] = [];
  const claimed = new Set<KeypointName>();

  for (const chain of LIMB_CHAINS) {
    const members = chain.keypoints;
    const touched = members.filter((kp) => focusSet.has(kp));
    if (touched.length === 0) continue;
    for (const kp of members) claimed.add(kp);

    // focus 를 포함하는 최장 연속 고신뢰 런.
    let bestStart = -1;
    let bestLen = 0;
    let runStart = -1;
    let runHasFocus = false;
    const flush = (endExclusive: number) => {
      if (runStart < 0 || !runHasFocus) return;
      const len = endExclusive - runStart;
      if (len > bestLen) {
        bestLen = len;
        bestStart = runStart;
      }
    };
    for (let i = 0; i < members.length; i += 1) {
      const kp = members[i];
      if (isHigh(kp)) {
        if (runStart < 0) {
          runStart = i;
          runHasFocus = false;
        }
        if (focusSet.has(kp)) runHasFocus = true;
      } else {
        flush(i);
        runStart = -1;
        runHasFocus = false;
      }
    }
    flush(members.length);

    if (bestLen >= 2) {
      const run = members.slice(bestStart, bestStart + bestLen);
      // 근위 관절에서 시작하는 런만 inset 대상 — 이미 몸통 밖(knee 시작)이면 0.
      const insetT = bestStart === 0 ? PROXIMAL_INSET_T[chain.proximalRole] : 0;
      chains.push({ keypoints: [...run], insetT });
      continue;
    }
    // 선 불가 → 부위 원으로 강등. 게이트를 통과한 focus 관절만 담는다.
    const circle = touched.filter((kp) => isHigh(kp));
    if (circle.length > 0) circleGroups.push(circle);
  }

  // 체인 밖 focus 관절 (미래 확장) — 원은 항상 안전한 표시.
  const orphan = focus.filter((kp) => !claimed.has(kp) && isHigh(kp));
  if (orphan.length > 0) {
    const dedup: KeypointName[] = [];
    for (const kp of orphan) if (!dedup.includes(kp)) dedup.push(kp);
    circleGroups.push(dedup);
  }

  return { chains, circleGroups };
}
