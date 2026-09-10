// 분석 시각 한 줄 표기 검증 (quick-260910-hsk, belle 2026-09-10 승인).
//
// 실행: node --test app/src/lib/__tests__/analysisDate.test.ts
// Node type stripping — 신규 npm 의존성 0 (replaySettle.test.ts 선례).
// node:test / node:assert 표준 모듈 + `.ts` import 만.
//
// 시각은 전부 `new Date(y, m, d, h, min)` 로 만든다 — created 와 now 를 같은
// 로컬 타임존에서 만들므로 실행 기기의 TZ 와 무관하게 결정론이다.
//
// 검증 축:
//   1) 같은 날 → `오늘 HH:MM`, 시각이 2자리로 채워짐 (`09:05`).
//   2) 자정을 사이에 둔 20분 차이 → `어제` (경과시간이 아니라 달력 기준임을 못박는 축).
//   3) 2일 전 → `2일 전`, 6일 전 → `6일 전`.
//   4) 7일 전 → `M월 D일` (경계 축 — 6 과 7 이 갈리는지).
//   5) 미래 시각 → `오늘` (기기 시계 오차. "-1일 전" 금지).
//   6) NaN / undefined 취급값(0·undefined) / 음수 → `''`.
//   7) 연말 경계 — 12월 28일 분석을 1월 3일에 열기 (일수 계산이 연도를 넘어 맞는지).

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ABSOLUTE_DATE_FROM_DAYS,
  formatAnalysisMoment,
} from '../analysisDate.ts';

/** 로컬 시각 → epoch ms. 월은 1-based 로 받는다(읽기 쉬우라고). */
function at(y: number, m: number, d: number, h = 0, min = 0): number {
  return new Date(y, m - 1, d, h, min, 0, 0).getTime();
}

// ── Test 1: 같은 날 → `오늘 HH:MM` ──────────────────────────────────────────

test('formatAnalysisMoment: 같은 날이면 오늘 + 시각, 시:분은 2자리 고정', () => {
  assert.equal(
    formatAnalysisMoment(at(2026, 9, 10, 10, 24), at(2026, 9, 10, 18, 0)),
    '오늘 10:24',
  );
  // 한 자리 시/분은 0 을 채운다 (history.tsx:20 과 같은 형식).
  assert.equal(
    formatAnalysisMoment(at(2026, 9, 10, 9, 5), at(2026, 9, 10, 9, 6)),
    '오늘 09:05',
  );
  // 자정 직후에 찍고 곧바로 열어도 같은 날이다.
  assert.equal(
    formatAnalysisMoment(at(2026, 9, 10, 0, 0), at(2026, 9, 10, 23, 59)),
    '오늘 00:00',
  );
});

// ── Test 2: 자정을 사이에 둔 20분 → `어제` ──────────────────────────────────

test('formatAnalysisMoment: 20분 차이라도 자정을 넘었으면 어제', () => {
  // 경과시간 기준이면 "오늘"이 나온다 — 달력 기준임을 못박는 축.
  assert.equal(
    formatAnalysisMoment(at(2026, 9, 9, 23, 50), at(2026, 9, 10, 0, 10)),
    '어제 23:50',
  );
  // 반대로 23시간 차이여도 같은 날이면 오늘이다.
  assert.equal(
    formatAnalysisMoment(at(2026, 9, 10, 0, 30), at(2026, 9, 10, 23, 30)),
    '오늘 00:30',
  );
  // 어제에도 시각을 붙인다 (같은 날 여러 건 구분 문제는 어제에도 동일).
  assert.equal(
    formatAnalysisMoment(at(2026, 9, 9, 7, 3), at(2026, 9, 10, 21, 0)),
    '어제 07:03',
  );
});

// ── Test 3: 2~6일 전 → `N일 전` ─────────────────────────────────────────────

test('formatAnalysisMoment: 2~6일 전은 N일 전 (시각 없음)', () => {
  assert.equal(
    formatAnalysisMoment(at(2026, 9, 8, 10, 24), at(2026, 9, 10, 0, 5)),
    '2일 전',
  );
  assert.equal(
    formatAnalysisMoment(at(2026, 9, 7, 23, 59), at(2026, 9, 10, 0, 1)),
    '3일 전',
  );
  assert.equal(
    formatAnalysisMoment(at(2026, 9, 4, 10, 24), at(2026, 9, 10, 18, 0)),
    '6일 전',
  );
});

// ── Test 4: 7일 경계 → `M월 D일` ────────────────────────────────────────────

test('formatAnalysisMoment: 7일째부터 날짜로 (6↔7 경계)', () => {
  assert.equal(
    formatAnalysisMoment(at(2026, 9, 3, 10, 24), at(2026, 9, 10, 18, 0)),
    '9월 3일',
  );
  // 경계 바로 앞은 상대 표기.
  assert.equal(
    formatAnalysisMoment(at(2026, 9, 4, 10, 24), at(2026, 9, 10, 18, 0)),
    '6일 전',
  );
  // 더 오래된 것도 날짜. 월은 1-based 로 나온다(0월 금지).
  assert.equal(
    formatAnalysisMoment(at(2026, 1, 5, 8, 0), at(2026, 9, 10, 18, 0)),
    '1월 5일',
  );
  assert.equal(ABSOLUTE_DATE_FROM_DAYS, 7);
});

// ── Test 5: 미래 시각 → `오늘` ──────────────────────────────────────────────

test('formatAnalysisMoment: 미래 시각은 오늘로 접는다', () => {
  // 같은 날 안에서 앞선 시각.
  assert.equal(
    formatAnalysisMoment(at(2026, 9, 10, 23, 0), at(2026, 9, 10, 9, 0)),
    '오늘 23:00',
  );
  // 날짜 자체가 미래여도 "-1일 전" 을 만들지 않는다.
  assert.equal(
    formatAnalysisMoment(at(2026, 9, 12, 6, 7), at(2026, 9, 10, 9, 0)),
    '오늘 06:07',
  );
});

// ── Test 6: 결측/비유한 → `''` ──────────────────────────────────────────────

test('formatAnalysisMoment: createdAt 이 없거나 유한수가 아니면 빈 문자열', () => {
  const now = at(2026, 9, 10, 18, 0);
  assert.equal(formatAnalysisMoment(Number.NaN, now), '');
  // 화면은 `createdAt ?? 0` 으로 넘긴다 — 0 이 "없음"의 관용 표기다.
  assert.equal(formatAnalysisMoment(0, now), '');
  assert.equal(formatAnalysisMoment(undefined as unknown as number, now), '');
  assert.equal(formatAnalysisMoment(-1, now), '');
  assert.equal(formatAnalysisMoment(Number.POSITIVE_INFINITY, now), '');
  // now 쪽이 망가져도 빈 문자열 (거짓 날짜를 만들지 않는다).
  assert.equal(formatAnalysisMoment(at(2026, 9, 10, 10, 24), Number.NaN), '');
});

// ── Test 7: 연말 경계 ───────────────────────────────────────────────────────

test('formatAnalysisMoment: 연도를 넘는 일수 계산', () => {
  // 12/28 → 1/3 = 6일 (29,30,31,1,2,3). 상대 표기 유지.
  assert.equal(
    formatAnalysisMoment(at(2025, 12, 28, 20, 30), at(2026, 1, 3, 9, 0)),
    '6일 전',
  );
  // 하루 더 지나면 7일째 — 날짜로 넘어간다.
  assert.equal(
    formatAnalysisMoment(at(2025, 12, 28, 20, 30), at(2026, 1, 4, 9, 0)),
    '12월 28일',
  );
  // 해가 바뀐 직후의 어제/오늘도 달력 기준으로 맞다.
  assert.equal(
    formatAnalysisMoment(at(2025, 12, 31, 23, 50), at(2026, 1, 1, 0, 10)),
    '어제 23:50',
  );
});
