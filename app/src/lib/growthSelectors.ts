// 홈 성장 카드의 집계 계층 단일 출처 — 주별 평균(D-01)·모드 분리(D-02)·기본 모드
// 폴백(D-03)·동작별 점수 델타(D-05). 30-03(컴포넌트)/30-04(홈 카드) 가 이 계약만
// 소비한다 (interface-first). 30-CONTEXT Integration Points: "집계 selector 는 순수
// 함수로 분리해 테스트 가능하게" — alignmentWarp.ts 골격 analog.
//
// 순수 함수만 (react·데이터소스 훅 의존 0 — `tsc --noEmit` + assert-growth-selectors.mjs
// 만으로 검증 가능). import 는 타입 계약뿐.
//
// 불변 경계 (30-CONTEXT): 채점 로직 무접촉 — 표시·집계 계층만. 증감은 '점수 포인트
// 델타'만 계산하며 등락률(퍼센트) 산출·문자열은 어디에도 없다
// ([[mode3-progress-not-similarity]] / [[mode3-overall-exclude-angle-similarity]]
// 정합 — overallScore 만 소비, angle 유사도·deltaFromPrevious 는 소비하지 않음).
//
// D-07 (점수 이질성): legacy 채점 체계 문서(mode1 Phase 24 이전 / mode3 Phase 29
// tally 전환 이전)를 세대로 갈라내는 필터·특별 처리 코드를 넣지 않는다 — 전부 포함.
// 주의: scoreSuppressed 제외(HIGH-1)는 legacy 필터가 아니라 '결과화면과 동일한 표시
// 억제 정합'이므로 D-07 과 무모순 — legacy 는 채점 세대 구분(포함), suppressed 는
// 표시 억제 계약(제외).
import type { AnalysisDoc, AnalysisMode } from '../types/analysis';

// 주별 평균 점 1개 (D-01). weekStart = 해당 주 월요일 00:00 로컬시간 epoch millis.
export interface WeeklyPoint {
  weekStart: number;
  avg: number; // 표시용 정수 (Math.round). 델타 산출은 내부 raw 평균을 별도로 사용.
  count: number; // 그 주에 집계된 분석 수
}

// 동작별 증감 행 (D-04 화면층 / D-05). delta=null 은 첫 기록(비교 대상 없음).
export interface MotionDeltaRow {
  key: string; // mode1=referenceMotionId / mode3='self'
  label: string; // mode1=referenceMotionName / mode3='내 기록'
  badge: '프로 비교' | '내 기록'; // history.tsx modeBadge 카피 재사용
  latestAvg: number; // 최근 활동 주 평균 (Math.round)
  delta: number | null; // 최근 활동 주 평균 − 직전 활동 주 평균 (점수 포인트). 활동 주 1개=null
  lastAnalyzedAt: number; // 그룹 내 최신 createdAt (정렬 기준)
}

// AnalysisDoc.createdAt 은 이미 epoch millis(number) — userAnalyses.normalize 가
// number 로 정규화해 저장하므로(analysis.ts:643 createdAt: number), Firestore
// Timestamp 변환은 이 계층에서 불필요하다 (가정 아님 — 계약 확인).

// 월요일 시작 로컬 주 버킷. Date#getDay(): 0=일..6=토. 월요일 기준 offset 은
// 일요일(0)만 6, 나머지는 day-1 로 도출한다 — 모듈로 없이 계산(Task 1 부재 게이트:
// 등락률 퍼센트 문자뿐 아니라 모듈로 연산자 문자도 파일 전체 0건 강제).
export function weekStartOf(millis: number): number {
  const d = new Date(millis);
  const day = d.getDay(); // 0=일요일 .. 6=토요일
  const mondayOffset = day === 0 ? 6 : day - 1;
  return new Date(
    d.getFullYear(),
    d.getMonth(),
    d.getDate() - mondayOffset,
    0,
    0,
    0,
    0,
  ).getTime();
}

// (HIGH-1) 성장 지표에 쓸 수 있는 분석인지 단일 판별 predicate — 아래 세 selector 의
// 유일한 집계 자격 관문. 결과화면에서 숨긴 점수(mode3 scoreSuppressed)를 홈 성장
// 지표(평균·델타·기본모드)에도 되살리지 않는다 — result.tsx:657 isScoreSuppressed
// 과 동일 기준(신뢰 계약). 조건 = done AND 모드 일치 AND overallScore 유한수치 AND
// scoreSuppressed !== true.
export function hasUsableGrowthScore(
  doc: AnalysisDoc,
  mode: AnalysisMode,
): boolean {
  if (doc.status !== 'done') return false;
  if (doc.mode !== mode) return false;
  const result = doc.result;
  if (!result) return false;
  // result.tsx:657 과 동일 — mode3 결과화면이 점수카드를 숨긴 분석은 홈 지표에서도 제외.
  if (result.scoreSuppressed === true) return false;
  const score = result.overallScore;
  return typeof score === 'number' && Number.isFinite(score);
}

interface RawWeekBucket {
  weekStart: number;
  rawAvg: number; // 반올림 전 raw 평균 (델타 산출 정밀도 보존)
  count: number;
}

// 이미 자격 필터(hasUsableGrowthScore)를 통과한 문서만 받아 주별 raw 평균 버킷 산출
// (weekStart 오름차순). NaN 방어는 predicate 가 이미 했으나, 이 헬퍼도 방어적으로
// 유한수치만 합산한다 (단일 자격 관문 원칙 유지 — 여기서 새 자격 정의는 안 함).
function rawWeeklyBuckets(usable: AnalysisDoc[]): RawWeekBucket[] {
  const buckets = new Map<number, { sum: number; count: number }>();
  for (const doc of usable) {
    const score = doc.result?.overallScore;
    if (typeof score !== 'number' || !Number.isFinite(score)) continue;
    const ws = weekStartOf(doc.createdAt);
    const b = buckets.get(ws) ?? { sum: 0, count: 0 };
    b.sum += score;
    b.count += 1;
    buckets.set(ws, b);
  }
  const rows: RawWeekBucket[] = [];
  for (const [weekStart, b] of buckets) {
    rows.push({ weekStart, rawAvg: b.sum / b.count, count: b.count });
  }
  rows.sort((a, b) => a.weekStart - b.weekStart);
  return rows;
}

// (D-01/D-02) 선택 모드의 주별 평균 추이. hasUsableGrowthScore 통과 문서만 집계하므로
// scoreSuppressed·NaN·비수치·모드불일치는 전부 predicate 가 배제한다(혼합 평균 코드
// 경로 없음). 분석 없는 주는 요소 자체가 없음(빈 주 0점 채움 금지), weekStart 오름차순.
export function weeklyAverages(
  analyses: AnalysisDoc[],
  mode: AnalysisMode,
): WeeklyPoint[] {
  const usable = analyses.filter((doc) => hasUsableGrowthScore(doc, mode));
  return rawWeeklyBuckets(usable).map((r) => ({
    weekStart: r.weekStart,
    avg: Math.round(r.rawAvg),
    count: r.count,
  }));
}

// (D-03) 기본 성장 모드. 최신 문서(useMyAnalyses 는 최신순 → 배열 첫 요소)의 mode 를
// 우선하되, 그 모드 주별 점 2개 미만이면 데이터 있는 다른 모드로 폴백, 양쪽 다 2개
// 미만이면 null(호출부가 GrowthLockedCard 처리). weeklyAverages 가 predicate 로
// suppressed 를 이미 배제하므로 기본 모드 선정도 hasUsableGrowthScore 기반이다
// (별도 분기 불필요 — HIGH-1 정합).
export function defaultGrowthMode(
  analyses: AnalysisDoc[],
): AnalysisMode | null {
  const primary = analyses[0]?.mode ?? null;
  // 최신 모드 우선, 그다음 다른 모드. 분석 없음(primary=null)이면 임의 순서로 둘 다 검사.
  const order: AnalysisMode[] =
    primary === 'mode3' ? ['mode3', 'mode1'] : ['mode1', 'mode3'];
  for (const m of order) {
    if (weeklyAverages(analyses, m).length >= 2) return m;
  }
  return null;
}

// (D-04 화면층 / D-05) 동작별 점수 델타 행. 입력을 hasUsableGrowthScore 로 먼저
// 거른 뒤 그룹핑: mode1 은 comparison.referenceMotionId 를 key / referenceMotionName
// 을 label(배지 '프로 비교'), mode3 는 전부 key='self' / label='내 기록' 단일 그룹
// (history.tsx motionLabel/modeBadge 선례). 그룹별 주별 raw 평균으로
// delta = round(최근 활동 주 평균 − 직전 활동 주 평균); 활동 주 1개면 null(첫 기록).
// 정렬은 lastAnalyzedAt desc — 표시 순서 세부(동작 수 상한 등)는 30-03 이 Figma 확인
// 후 재량.
export function motionDeltas(analyses: AnalysisDoc[]): MotionDeltaRow[] {
  const usable = analyses.filter((doc) => hasUsableGrowthScore(doc, doc.mode));
  const groups = new Map<
    string,
    { label: string; badge: '프로 비교' | '내 기록'; docs: AnalysisDoc[] }
  >();
  for (const doc of usable) {
    const cmp = doc.result?.comparison;
    let key: string;
    let label: string;
    let badge: '프로 비교' | '내 기록';
    if (doc.mode === 'mode1' && cmp?.mode === 'mode1') {
      key = cmp.referenceMotionId;
      label = cmp.referenceMotionName;
      badge = '프로 비교';
    } else if (doc.mode === 'mode3') {
      key = 'self';
      label = '내 기록';
      badge = '내 기록';
    } else {
      // (30-REVIEW WR-03) mode1 인데 comparison 형상 불일치(런타임 Firestore 데이터는
      // TS 계약을 보증하지 않음) — '내 기록' 그룹에 합산하면 방어 경로에서 D-02 모드
      // 비혼합이 깨지므로 어느 그룹에도 넣지 않고 skip.
      continue;
    }
    const g = groups.get(key) ?? { label, badge, docs: [] };
    g.docs.push(doc);
    groups.set(key, g);
  }

  const rows: MotionDeltaRow[] = [];
  for (const [key, g] of groups) {
    const weeks = rawWeeklyBuckets(g.docs); // weekStart 오름차순
    if (weeks.length === 0) continue; // 방어 (자격 통과 문서라 사실상 도달 불가)
    const latest = weeks[weeks.length - 1];
    const prev = weeks.length >= 2 ? weeks[weeks.length - 2] : null;
    const latestAvg = Math.round(latest.rawAvg);
    const delta = prev ? Math.round(latest.rawAvg - prev.rawAvg) : null;
    let lastAnalyzedAt = 0;
    for (const doc of g.docs) {
      if (doc.createdAt > lastAnalyzedAt) lastAnalyzedAt = doc.createdAt;
    }
    rows.push({ key, label: g.label, badge: g.badge, latestAvg, delta, lastAnalyzedAt });
  }
  rows.sort((a, b) => b.lastAnalyzedAt - a.lastAnalyzedAt);
  return rows;
}
