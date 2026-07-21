// 목표 게이지 기하 — 순수 함수만, react 의존 0 (32-10 Task 1, D-10/D-09 + 리뷰 HIGH).
//
// 왜 이 모듈이 존재하나 (리뷰 HIGH — 자의적 시각 비율 금지): D-09 는 사용자 측정
// 수치를 헤드라인/전면에 두는 것을 금지한다. 목표 게이지가 "목표까지 남은 정도를
// 길이로만" 표현하려면(D-10 belle 강한 교정) 그 길이(채움 비율·마커 위치)가 무엇을
// 의미하는지 정의된 스케일이 있어야 한다 — 정의 없이 눈대중 비율을 그리면 D-09 가
// 막으려던 자의적 숫자를 시각 비율로 재생산하게 된다. 그래서 스케일을 아래 한 도메인
// 규칙으로 못 박고 테스트(gaugeGeometry.test.ts)로 고정한다.
//
// 스케일 의미 (명문화):
//   도메인 = [min(current,target) − tolerance, max(current,target) + tolerance]
//   — 현재와 목표를 모두 포함하고, 규칙 허용 오차(tolerance)만큼 양쪽에 여유를 둔
//   실측 스케일. 모든 비율(ratio/targetRatio/tolBandStart/tolBandEnd)은 이 도메인의
//   선형 위치([0,1])로, 렌더 좌표(채움 폭·마커 left) 계산 전용이다. 사용자에게 노출
//   되는 문자열은 항상 단위 원문(GoalGaugeBar 소형 수치 배지) — 비율(%)은 노출 금지.
//
//   tolerance 는 백엔드가 실존 규칙 상수(ipsf_criteria CRITERION_GROUPS 등)에서 방출한
//   record.tolerance 만 사용한다. 임의 기본값을 지어내지 않는다 — 없거나(0/음수/비유한)
//   이면 null 을 반환하고, 호출측(GoalGaugeBar)은 게이지를 그리지 않는다(수치 배지+
//   텍스트로만 정직하게 폴백). 이것이 D-09 "자의 수치 금지"의 시각적 적용이다.

export interface GaugeGeometry {
  /** 현재값의 도메인 내 선형 위치 [0,1] (채움 폭·현재 마커). */
  ratio: number;
  /** 목표값의 도메인 내 선형 위치 [0,1] (목표 마커). */
  targetRatio: number;
  /** 허용 오차 밴드 시작 = (target − tolerance) 의 도메인 위치 [0,1]. */
  tolBandStart: number;
  /** 허용 오차 밴드 끝 = (target + tolerance) 의 도메인 위치 [0,1]. */
  tolBandEnd: number;
}

/**
 * 목표 게이지의 스케일·마커·채움 비율을 계산한다 (순수 함수, react 무관).
 *
 * @param current   현재 측정값 (record.measured)
 * @param target    목표값 (record.target — 기준 각도 등)
 * @param tolerance 규칙 상수 유래 허용 오차 (record.tolerance). > 0 유한값만 유효.
 * @returns 도메인 내 선형 비율 4종, 또는 표현 불가 시 null(게이지 미표시).
 *
 * null 반환 조건 (게이지 불가 — 호출측이 게이지를 생략하고 수치 배지로 폴백):
 *   - current/target 가 비유한(NaN/Infinity/부재)
 *   - tolerance 가 비유한 또는 0 이하 (규칙 상수 부재 = 자의 스케일 금지, D-09)
 */
export function computeGaugeGeometry(
  current: number,
  target: number,
  tolerance: number,
): GaugeGeometry | null {
  if (!Number.isFinite(current) || !Number.isFinite(target)) return null;
  // tolerance 는 규칙 상수만 — 없으면(0/음수/비유한) 자의 스케일을 만들지 않고 null.
  if (!Number.isFinite(tolerance) || tolerance <= 0) return null;

  const domainMin = Math.min(current, target) - tolerance;
  const domainMax = Math.max(current, target) + tolerance;
  const span = domainMax - domainMin;
  // 이론상 tolerance > 0 이면 span >= 2*tolerance > 0 — 방어적으로 한 번 더 확인.
  if (!(span > 0)) return null;

  const pos = (v: number): number => (v - domainMin) / span;

  return {
    ratio: pos(current),
    targetRatio: pos(target),
    tolBandStart: pos(target - tolerance),
    tolBandEnd: pos(target + tolerance),
  };
}
