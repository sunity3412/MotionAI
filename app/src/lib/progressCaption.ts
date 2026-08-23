// 발전 캡션 판정 — 순수 함수만 (quick-260822-oe1, belle 08-21 승인).
//
// belle 원문 (2026-08-21): "수치 하면 체감은 못하지만 다음 검증때 20도→18도로
// 줄면 발전적인 부분이 보인다. 캡션에 '저번보다 더 벌어졌어요' 담으면 된다."
// 수치의 역할 = 발전 추적 — 한 번 본 수치는 체감이 안 되지만 다음 검증에서
// 줄어든 것이 보이면 수치가 의미를 갖는다.
//
// 규율 (BELLE-0821-P1~P4):
//   P1 — 비교 대상 = 같은 동작(mode1 referenceMotionId 동일)의 직전 done 분석,
//        같은 criterion 의 편차(delta = |target − measured|).
//   P2 — 문구 = 앵커의 progressSentence 원문 그대로 (단일 소스 — illustrationHow
//        HOW_ANCHORS). 변형·수치 삽입·악화 문구 발명 금지.
//   P3 — 노이즈 문턱의 유일한 출처 = 실측 (아래 상수 주석). 측정 전에 정한 수치 0.
//   P4 — fail-closed: 직전 없음 / 값 없음 / unit 불일치 / 문턱 미만 / 악화 →
//        캡션 없음. 오버레이 fail-closed(<3°/값 없음)는 별도 독립 게이트
//        (buildHowOverlay 소유) — 캡션은 오버레이가 있는 곳에서만 소비된다.
//
// RN/firebase import 0, types/analysis 는 type-only — node --test 실행 가능
// (illustrationHow 선례).

import type { AnalysisDoc } from '../types/analysis.ts';
import { HOW_ANCHORS, type HowAnchors } from './illustrationHow.ts';

/**
 * criterion별 노이즈 문턱 구조 (quick-260824-bxf, belle 08-24 승인).
 * 규칙 = `문턱_c = max(전역 defaultDeg, ceil(해당 criterion 자체 노이즈 P95_c) + 1)`
 * — "split 은 21" 은 숫자 예외가 아니라 이 규칙의 산출이다.
 * **defaultDeg 가 null 이면 캡션 전면 비활성** — byCriterion 오버라이드가
 * 있어도 꺼진다 (측정 불충분 = fail-closed, BELLE-0821-P3 계승).
 */
export interface ProgressNoiseThresholds {
  defaultDeg: number | null;
  byCriterion: Readonly<Record<string, number>>;
}

/**
 * 노이즈 문턱 (deg). **유일한 출처 = 실측 원장** (측정 전에 정한 수치 0).
 *
 * defaultDeg 12 = `.planning/quick/260822-oe1-progress-caption/NOISE-MEASUREMENT.md`
 *   (측정일 2026-08-22 · 페어 282 · |Δdelta| 표본 1017 · 풀링 P95 = 11.60
 *   → max(1, ceil) = 12). 재측정 도구 = 같은 디렉터리 measure_noise.mjs.
 *
 * split_angle 21 = 규칙 `max(전역 12, ceil(P95_c) + 1)` (belle 08-24 승인).
 *   P95_c = 20.00 (같은 원장 criterion 표, n=103 — 20° 양자화 요동) → 21.
 *   플립 근거 원장 =
 *   `.planning/quick/260824-bxf-criterion-split-angle-12-split-21/SPLIT-FLIP-CROSSTAB.md`
 *   (측정일 2026-08-24 — 같은-영상 historical 플립 29/55, 최대 요동 20°).
 *   재측정 도구 = 같은 디렉터리 measure_split_flip.mjs.
 *
 * 문턱보다 작은 "개선"은 촬영·RTMW·측정창 요동과 구분되지 않으므로 캡션을
 * 붙이지 않는다. 타 criterion 오버라이드 추가는 belle 결정 후에만
 * (SPLIT-FLIP-CROSSTAB.md 관측 노트 — 짜맞추기 방지).
 */
export const PROGRESS_NOISE_THRESHOLDS: ProgressNoiseThresholds = {
  defaultDeg: 12,
  byCriterion: { split_angle: 21 },
};

/**
 * criterion 으로 문턱 조회 (순수 함수). defaultDeg 가 null 이면 **무조건 null**
 * — 오버라이드가 있어도 전면 비활성이 우선한다 (fail-closed, BELLE-0821-P3).
 * 아니면 byCriterion 정확 일치 유한값 오버라이드, 없으면 defaultDeg.
 */
export function resolveProgressNoiseThresholdDeg(
  criterion: string,
  thresholds: ProgressNoiseThresholds = PROGRESS_NOISE_THRESHOLDS,
): number | null {
  if (thresholds.defaultDeg == null) return null;
  const override = thresholds.byCriterion[criterion];
  if (typeof override === 'number' && Number.isFinite(override)) return override;
  return thresholds.defaultDeg;
}

/** record 에서 뽑은 측정 재료 — DefectIllustration `how` prop 과 같은 모양. */
export interface CriterionMeasure {
  measured: number | null;
  target: number | null;
  unit: string | null;
}

/** 캡션 판정 입력 — 값이 없어도 크래시 없이 null 로 닫힌다 (방어). */
export type MeasureLike = {
  measured?: number | null;
  target?: number | null;
  unit?: string | null;
} | null | undefined;

/**
 * 같은 동작의 직전 분석 — createdAt 이 현재보다 **작은** 것 중 가장 최신의
 * done mode1 + 같은 referenceMotionId doc. 자기 자신(analysisId 동일) 제외.
 * mode3/타 동작/미완료 doc 무시. 없으면 null.
 *
 * 입력 배열의 정렬에 의존하지 않는다 (useMyAnalyses 는 desc 로 주지만,
 * 판정은 createdAt 최대값 선택으로 자체 결정).
 */
export function findPreviousComparable(
  analyses: readonly AnalysisDoc[],
  current: { analysisId: string; createdAt: number; referenceMotionId: string },
): AnalysisDoc | null {
  let best: AnalysisDoc | null = null;
  for (const doc of analyses) {
    if (doc.analysisId === current.analysisId) continue;
    if (doc.status !== 'done') continue;
    if (typeof doc.createdAt !== 'number' || doc.createdAt >= current.createdAt)
      continue;
    const cmp = doc.result?.comparison;
    if (cmp == null || cmp.mode !== 'mode1') continue;
    if (cmp.referenceMotionId !== current.referenceMotionId) continue;
    if (best == null || doc.createdAt > best.createdAt) best = doc;
  }
  return best;
}

/**
 * doc 의 감점 records 에서 criterion **정확 일치 첫 record** 의
 * { measured, target, unit }. records 없음/불일치 → null.
 * (측정 산출 measure_noise.mjs 의 선택 규칙과 동일 — 측정과 소비가 같은
 * record 를 봐야 문턱이 의미를 갖는다.)
 */
export function extractCriterionMeasure(
  doc: AnalysisDoc | null | undefined,
  criterion: string,
): CriterionMeasure | null {
  const records = doc?.result?.deductionBreakdown?.records;
  if (!Array.isArray(records)) return null;
  for (const r of records) {
    if (r == null || typeof r !== 'object') continue;
    if (r.criterion !== criterion) continue;
    return {
      measured: typeof r.measuredValue === 'number' ? r.measuredValue : null,
      target: typeof r.baselineValue === 'number' ? r.baselineValue : null,
      unit: typeof r.unit === 'string' ? r.unit : null,
    };
  }
  return null;
}

/**
 * 발전 캡션 판정. 개선 = prevDelta − curDelta (delta = |target − measured| —
 * 차이형(50°→0°)·절대각형(94°→71°) 두 record 모양 다 성립, buildHowOverlay
 * docstring 계승). 개선 ≥ 문턱이고 두 쪽 다 unit 'deg' + 유한값이고 앵커에
 * progressSentence 있으면 → 그 문장 (원문 그대로, BELLE-0821-P2).
 *
 * 문턱은 record 의 criterion 으로 조회한다 (quick-260824-bxf —
 * resolveProgressNoiseThresholdDeg: 기본 12 + split_angle 21). criterion 이
 * null/undefined/빈 문자열이면 캡션 null — 배선 불일치를 기본 문턱으로 덮지
 * 않는다 (fail-closed, BELLE-0821-P4 계승).
 *
 * fail-closed 전 축 각각 null (BELLE-0821-P4):
 *   defaultDeg null(측정 불충분 = 전면 비활성) / criterion 부재 /
 *   current·prev null / unit 'deg' 아님 / non-finite / 개선 < 문턱 /
 *   악화(개선 음수) / 미등록 asset /
 *   progressSentence 없는 앵커(rotate 포함 — 데이터 opt-in).
 *
 * thresholds·anchors 는 테스트 주입용 마지막 인자 (기본 = 상수/단일 소스 —
 * 프로덕션 호출은 인자 4개만 쓴다).
 */
export function buildProgressCaption(
  asset: string | null | undefined,
  criterion: string | null | undefined,
  current: MeasureLike,
  prev: MeasureLike,
  thresholds: ProgressNoiseThresholds = PROGRESS_NOISE_THRESHOLDS,
  anchors: Readonly<Record<string, HowAnchors>> = HOW_ANCHORS,
): string | null {
  if (!criterion) return null;
  const thresholdDeg = resolveProgressNoiseThresholdDeg(criterion, thresholds);
  if (thresholdDeg == null || !Number.isFinite(thresholdDeg)) return null;
  if (!asset) return null;
  const a = anchors[asset];
  if (a == null || a.kind !== 'baked' || !a.progressSentence) return null;
  if (current == null || prev == null) return null;
  if (current.unit !== 'deg' || prev.unit !== 'deg') return null;
  const cm = current.measured;
  const ct = current.target;
  const pm = prev.measured;
  const pt = prev.target;
  if (
    typeof cm !== 'number' ||
    typeof ct !== 'number' ||
    typeof pm !== 'number' ||
    typeof pt !== 'number'
  )
    return null;
  if (![cm, ct, pm, pt].every(Number.isFinite)) return null;
  const improvement = Math.abs(pt - pm) - Math.abs(ct - cm);
  if (improvement < thresholdDeg) return null; // 미달·악화(음수) 공통으로 닫힘
  return a.progressSentence;
}
