/**
 * 러너 기동 확인용 스모크 (31-11 Task 1 acceptance).
 * 실질 검증은 visualCards.test.ts / ReferenceCornerSection.test.tsx 가 담당한다.
 */
import { describe, expect, it } from '@jest/globals';

describe('jest runner', () => {
  it('boots', () => {
    expect(true).toBe(true);
  });
});
