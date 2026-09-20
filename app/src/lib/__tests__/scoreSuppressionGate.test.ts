// D-08 게이트 — 점수를 그리는 화면은 억제 플래그를 반드시 읽는다 (quick-260920).
//
// 실행: node --test app/src/lib/__tests__/scoreSuppressionGate.test.ts
// Node 24 type stripping 으로 트랜스파일 없이 실행 — 신규 의존성 0
// (screenVocabulary.test.ts 선례. node:test / node:assert / node:fs 만).
//
// 왜 게이트인가
// ─────────────
// belle D-08 (`.planning/phases/20-v2-gemini/20-CONTEXT.md:35`):
//   "미보유(분기 3) 표시 = confident 점수 억제 + '기준 없음'. … **confident 97 금지**
//    (미보유에 확신 점수 = 신뢰 파괴)."
//
// 이 게이트는 2026-06-20(c09dd494)에 구현됐다가 **2026-09-09 재디자인(aadf0375)에서
// 조용히 사라졌다.** 시안이 옛 점수카드를 대체하면서 그 안에 있던 억제 분기가 같이
// 걷혔고, D-08 철회 기록은 없다. 그 사이 라이브 mode3 7건이 59~98 점을 띄웠다
// (중앙 97 — D-08 이 이름으로 금지한 바로 그 값).
//
// 개별 패치로는 또 샌다. 다음 재디자인도 같은 방식으로 지울 수 있기 때문이다.
// 그래서 **스캔이 상시 강제한다** (screenVocabulary.test.ts 와 같은 이유).
//
// 스코프
// ──────
// `result.overallScore` / `doc.result?.overallScore` 를 **화면에 그리는** 파일은
// 같은 파일에서 `scoreSuppressed` 를 반드시 참조해야 한다. 이 게이트는 "어떻게
// 가렸는지"까지는 검사하지 않는다 — UX 강도는 D-08 이 명시적으로 Claude 재량으로
// 열어둔 부분이다("점수 완전 숨김 vs 회색 처리 vs 배너"). 검사하는 것은 **게이트의
// 존재**뿐이고, 그것이 09-09 형태의 회귀를 막는다.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const APP_SRC = join(HERE, '..', '..');

// 점수를 사용자에게 보여주는 화면. 새 화면이 점수를 그리기 시작하면 여기에 추가한다
// — 목록을 늘리는 것이 게이트를 우회하는 것보다 쉬워야 한다.
const SCREENS = [
  'app/analysis/result.tsx',
  'app/(tabs)/index.tsx',
  'app/(tabs)/history.tsx',
  'app/(tabs)/profile.tsx',
];

function read(rel: string): string {
  const p = join(APP_SRC, rel);
  assert.ok(existsSync(p), `게이트 대상 파일이 없다: ${rel} (경로가 바뀌었으면 SCREENS 갱신)`);
  return readFileSync(p, 'utf8');
}

/** 줄 주석과 블록 주석을 지운다 — 주석 속 단어로 게이트가 통과하면 안 된다. */
function stripComments(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

test('D-08 게이트: 점수를 그리는 화면은 scoreSuppressed 를 읽는다', () => {
  const missing: string[] = [];
  for (const rel of SCREENS) {
    const code = stripComments(read(rel));
    const drawsScore = /overallScore/.test(code);
    const readsFlag = /scoreSuppressed/.test(code);
    if (drawsScore && !readsFlag) missing.push(rel);
  }
  assert.deepEqual(
    missing,
    [],
    `점수를 그리면서 억제 플래그를 안 읽는 화면이 있다 — belle D-08 위반.\n` +
      `  ${missing.join('\n  ')}\n` +
      `  (2026-09-09 에 이 게이트가 재디자인으로 사라져 라이브에 97점이 떴다. 같은 형태의 회귀다.)`,
  );
});

test('D-08 게이트: 결과화면이 다이얼·공유·교정포인트 세 표면을 모두 가린다', () => {
  // 숫자만 가리는 수리가 반드시 남기는 누출 셋. 옛 구현 주석이 이름으로 경고했다 —
  // "octagon 만 숨기면 grade/summary/caption 으로 confident 점수가 누출된다".
  // 지금 셸에서의 대응물 = 다이얼(숫자+진행 호+음성) / 공유 문구 / 교정포인트 탭 밴드.
  const code = stripComments(read('app/analysis/result.tsx'));
  const gated = code.match(/isScoreSuppressed/g) ?? [];
  assert.ok(
    gated.length >= 4,
    `결과화면의 억제 분기가 ${gated.length}곳뿐이다. 최소 4곳이어야 한다 — ` +
      `다이얼 / 요약 서브라인(척도 단언) / 공유 문구 / 교정포인트 밴드. ` +
      `하나라도 빠지면 그 표면으로 점수가 샌다.`,
  );
});

test('D-08 게이트: 성장 지표의 단일 관문이 살아 있다', () => {
  // growthSelectors.hasUsableGrowthScore 는 "결과화면이 숨긴 점수를 집계에 되살리지
  // 않는다"는 계약의 단일 관문이다. 이게 사라지면 홈 평균이 억제 점수를 되살린다.
  const code = stripComments(read('lib/growthSelectors.ts'));
  assert.match(
    code,
    /scoreSuppressed\s*===\s*true/,
    'growthSelectors 의 억제 필터가 사라졌다 — 홈 성장 지표가 숨긴 점수를 되살린다.',
  );
});
