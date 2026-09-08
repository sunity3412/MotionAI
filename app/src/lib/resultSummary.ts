// 요약 탭 조립 — 순수 함수 (belle 09-08 재디자인 시안 1).
//
// react/react-native/expo 의존 0 — `tsc --noEmit` + `node --test` 로만 검증되는
// 순수 계층 (voiceSnap.ts / momentJump.ts 관례).
//
// 시안의 요약 카드는 감점을 **칩 3개 + "+N"** 으로 보여준다. 규칙을 새로 만들지 않는다:
// 라벨·수치 포맷은 이미 '점수 계산 내역'이 쓰는 deductionLabels 의 함수를 그대로
// 소비한다(사본 금지 — 두 표면이 같은 감점을 다르게 부르면 안 된다). 칩이 표에서
// 덜어내는 것은 괄호 안 설명뿐이다: 표는 "오른쪽 팔꿈치(정은지 대비 각도)" 로 쓰고
// 칩은 좁아서 "오른쪽 팔꿈치" 만 쓴다.

import type { DeductionRecord } from '../types/analysis';
import {
  ANGLE_VS_REFERENCE_PREFIX,
  JOINT_LABEL_KO,
  criterionLabelKo,
  formatDeductionNumber,
} from './deductionLabels.ts';

export interface SummaryChip {
  /** 조인 키. 칩을 눌러 같은 항목의 상세로 갈 때 쓴다. */
  recordId: string | null;
  /** 부위 이름만 (괄호 설명 제외). */
  label: string;
  /** 감점 표기 — 표와 같은 포맷(U+2212). 예: '−11.6' */
  pointsText: string;
  /** 정렬·판정용 절대 감점. */
  magnitude: number;
}

export interface SummaryChips {
  chips: SummaryChip[];
  /** 칩으로 못 보여준 나머지 개수. 0 이면 '+N' 칩을 그리지 않는다. */
  overflow: number;
  /** 감점 record 총 개수 — 헤드라인 "분석에서 N개…" 와 CTA 가 같이 쓴다. */
  total: number;
}

/**
 * 칩에 쓸 짧은 부위 이름.
 *
 * angle_vs_reference__{jk} 는 표에서 "관절명(정은지 대비 각도)" 로 쓰지만 칩은
 * 폭이 좁아 관절명만 쓴다 — 괄호 안은 **설명**이지 이름이 아니므로 덜어내도
 * 같은 것을 가리킨다. 그 밖의 criterion 은 표와 완전히 같은 라벨을 쓴다.
 */
export function summaryChipLabel(criterion: string): string {
  if (typeof criterion !== 'string' || criterion.length === 0) return '';
  if (criterion.startsWith(ANGLE_VS_REFERENCE_PREFIX)) {
    const jointKey = criterion.slice(ANGLE_VS_REFERENCE_PREFIX.length);
    const jointLabel = JOINT_LABEL_KO[jointKey];
    if (jointLabel) return jointLabel;
  }
  return criterionLabelKo(criterion);
}

/**
 * 감점 record 목록 → 요약 칩.
 *
 * - **감점이 큰 순**으로 고른다(시안이 11.6 / 9.4 / 7.2 순). 입력 배열은 화면이
 *   시간순으로 정렬한 것이라 여기서 다시 정렬하지만, 원본을 변형하지 않는다.
 * - 동점은 입력 순서를 지킨다(결정성 — 같은 doc 이 두 번 다르게 보이지 않는다).
 * - `points` 가 유한한 음수가 아닌 record 는 제외한다. 감점이 아닌 것을 감점 칩으로
 *   보여줄 수 없다.
 * - `total` 은 **칩 후보 전체**다. 헤드라인의 N 과 CTA 의 N 이 칩 개수가 아니라
 *   실제 교정할 점의 수여야 한다.
 */
export function buildSummaryChips(
  records: readonly DeductionRecord[] | null | undefined,
  max = 3,
): SummaryChips {
  if (!Array.isArray(records) || records.length === 0) {
    return { chips: [], overflow: 0, total: 0 };
  }
  const limit = Number.isFinite(max) && max > 0 ? Math.floor(max) : 3;

  const usable: { rec: DeductionRecord; order: number; magnitude: number }[] = [];
  records.forEach((rec, order) => {
    if (rec == null) return;
    const pts = rec.points;
    if (typeof pts !== 'number' || !Number.isFinite(pts) || pts >= 0) return;
    usable.push({ rec, order, magnitude: Math.abs(pts) });
  });

  // 감점 큰 순 → 동점이면 원래 순서 (안정 정렬을 직접 보장).
  usable.sort((a, b) => b.magnitude - a.magnitude || a.order - b.order);

  const chips = usable.slice(0, limit).map(({ rec, magnitude }) => ({
    recordId: typeof rec.recordId === 'string' && rec.recordId.length > 0 ? rec.recordId : null,
    label: summaryChipLabel(rec.criterion),
    pointsText: `−${formatDeductionNumber(magnitude)}`,
    magnitude,
  }));

  return {
    chips,
    overflow: Math.max(0, usable.length - chips.length),
    total: usable.length,
  };
}
