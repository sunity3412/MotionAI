// 측정 용어(차원·지표) → 심사 언어 사람 말 (32-CONTEXT D-12).
//
// **단일 출처 = backend/data/terminology_map.json.** 이 파일은 그 JSON 의 미러이며
// (값 문자열 동일), backend/tests/phase32/test_terminology_lockstep.py 가 양방향
// 텍스트 대조로 drift 를 차단한다 (주석 정합이 아니라 테스트 정합 — D-12).
//
// 톤 = 친숙하되 장난스럽지 않게 (belle 원문). '안정성'·'각도 유사도' 같은 차원·
// 지표 추상 용어를 심판이 실제로 보는 사람 말로 통일한다. 키 = ScoreDimension
// (angle/line/stability, analysis.ts) + 지표 용어(reach/split). 실제 라벨 확정은
// 32-05 belle 감수(D-11/D-12)에서 조정될 수 있다.

export const TERMINOLOGY_MAP = {
  angle: '동작의 전체 흐름이 기준 자세와 얼마나 나란히 이어지는지',
  line: '팔다리를 끝까지 펴서 만드는 라인',
  stability: '핵심 자세에서 흔들림 없이 버티는 힘',
  reach: '목표 지점까지 몸을 뻗어 닿는 정도',
  split: '다리를 벌려 만드는 각도의 크기',
} as const;

export type TerminologyTerm = keyof typeof TERMINOLOGY_MAP;

// 미등록 용어는 원문 그대로 노출 (투명성 — deductionLabels.criterionLabelKo 관례).
export function terminologyPlain(term: string): string {
  return (TERMINOLOGY_MAP as Record<string, string>)[term] ?? term;
}
