// Phase 20-03 TRUST-07 — result.tsx 점수 억제 정적 단언 (RN render test 대체).
//
// 앱(app/package.json)에 Jest/RN 테스트 스택이 없다(iter3 HIGH-1). mid-phase 도입하지
// 않고, result.tsx 소스를 파싱해 점수카드 전체 억제 + reason-owns-copy 를 정적으로 단언한다.
//
// 사용법 (cwd-independent — iter4 MEDIUM-2):
//   cd app && node scripts/assert-result-score-suppression.mjs --self-test
//   cd app && node scripts/assert-result-score-suppression.mjs
//   repo root 에서 실행해도 동일 (result.tsx 경로는 import.meta.url 로 해석).
//
// 단언 (iter2 HIGH-2 / iter3 HIGH-2 / iter5 HIGH-2):
//   (a) 점수카드 6요소(OctagonScore / gradeBadge / LevelBenchmark / scoreCaption /
//       score-derived summary / '점수를 확인해보세요' 헤더 카피)가 isScoreSuppressed
//       비억제 분기 가드 아래인지 — 하나라도 비조건부 렌더이면 위반.
//   (b) recognition_low_confidence 분기가 reference-free '기준 동작 없음' 라벨을
//       하드코딩 렌더하지 않는지 (reason-owns-copy reason leak 차단).
//   위반 시 non-zero exit + 어떤 요소가 위반인지 출력.

import { readFileSync } from 'node:fs';

const RESULT_TSX_URL = new URL(
  '../src/app/analysis/result.tsx',
  import.meta.url,
);

// 점수카드 confident 표시 요소 — 전부 isScoreSuppressed 비억제(else) 분기 아래여야 한다.
// JSX 렌더 형태(`<Component`)/스타일 참조로 import 라인 오탐 회피.
// '점수를 확인해보세요' 헤더 카피는 별도(헤더 삼항에서 isScoreSuppressed 로 분기)로 검사.
const SCORE_CARD_TOKENS = [
  '<OctagonScore',
  'styles.gradeBadge',
  '<LevelBenchmark',
  'styles.scoreCaption',
  'styles.summary',
];

const HEADER_COPY = '점수를 확인해보세요';

// reference-free 전용 라벨 — recognition_low_confidence 분기에 하드코딩되면 안 된다.
const REFERENCE_FREE_LABELS = ['기준 동작 없음', '기준 없음'];

/**
 * `isScoreSuppressed ? (A) : (B)` 삼항의 else(B) 분기 텍스트를 추출한다.
 * 균형 괄호 스캐너 — 점수카드를 감싸는 삼항(SCORE_CARD_TOKENS 를 포함하는 분기)을 찾는다.
 * @param {string} source
 * @returns {string | null} else 분기 텍스트 (없으면 null)
 */
function extractScoreCardElseBranch(source) {
  const marker = 'isScoreSuppressed ? (';
  let from = 0;
  for (;;) {
    const start = source.indexOf(marker, from);
    if (start === -1) return null;
    // then(A) 분기 괄호 균형 스캔.
    let i = start + marker.length;
    let depth = 1;
    while (i < source.length && depth > 0) {
      const ch = source[i];
      if (ch === '(') depth += 1;
      else if (ch === ')') depth -= 1;
      i += 1;
    }
    // 이제 i 는 then 분기 ')' 다음. ' : (' 를 찾는다.
    const rest = source.slice(i);
    const elseMatch = rest.match(/^\s*:\s*\(/);
    if (elseMatch) {
      const elseStart = i + elseMatch[0].length;
      let j = elseStart;
      let edepth = 1;
      while (j < source.length && edepth > 0) {
        const ch = source[j];
        if (ch === '(') edepth += 1;
        else if (ch === ')') edepth -= 1;
        j += 1;
      }
      const elseBranch = source.slice(elseStart, j - 1);
      // 점수카드를 포함하는 삼항이면 반환, 아니면 다음 삼항 탐색.
      if (elseBranch.includes('OctagonScore')) return elseBranch;
    }
    from = start + marker.length;
  }
}

/**
 * 억제 가드 정적 검사 (self-test 와 실행이 공유하는 단일 함수).
 * @param {string} source result.tsx 소스
 * @returns {{ ok: boolean, violations: string[] }}
 */
export function assertSuppressionGuards(source) {
  const violations = [];

  // isScoreSuppressed 식별자 정의 존재 (STRICTLY scoreSuppressed===true).
  if (!/const\s+isScoreSuppressed\s*=/.test(source)) {
    violations.push('isScoreSuppressed 식별자 정의 부재');
  }
  // iter3 HIGH-2 — scoringBasis 폴백 금지. isScoreSuppressed 정의 라인에 scoringBasis/
  // reference_free 토큰이 있으면 label-drives-policy 회귀.
  const defLine = source
    .split('\n')
    .find((l) => /const\s+isScoreSuppressed\s*=/.test(l));
  if (defLine && /scoringBasis|reference_free/.test(defLine)) {
    violations.push(
      'isScoreSuppressed 정의에 scoringBasis/reference_free 폴백 — STRICTLY scoreSuppressed===true 위반 (iter3 HIGH-2)',
    );
  }

  // (a-1) 점수카드 5요소가 isScoreSuppressed else(비억제) 분기 안에만 존재하는지.
  // 점수카드를 감싸는 삼항의 else 분기를 추출 → 각 토큰이 (1) 소스에 존재 + (2) 그 토큰의
  // 모든 등장이 else 분기 안인지 확인 (가드 밖 비조건부 렌더 차단).
  const elseBranch = extractScoreCardElseBranch(source);
  if (elseBranch === null) {
    violations.push(
      '점수카드를 감싸는 isScoreSuppressed ? (...) : (...) 삼항 부재 — octagon-only 억제이거나 비조건부 (iter2 HIGH-2)',
    );
  } else {
    for (const token of SCORE_CARD_TOKENS) {
      const total = source.split(token).length - 1;
      const inElse = elseBranch.split(token).length - 1;
      if (total === 0) {
        violations.push(`점수카드 요소 '${token}' 부재 (result.tsx 변경?)`);
      } else if (inElse !== total) {
        // else 분기 밖에서도 등장 = 비조건부/이중 렌더 의심.
        violations.push(
          `'${token}' 가 isScoreSuppressed else 가드 밖에서도 렌더 (비조건부 — iter2 HIGH-2 위반)`,
        );
      }
    }
  }

  // (a-2) 헤더 카피('점수를 확인해보세요')는 isScoreSuppressed 삼항 안에서만 등장해야 한다.
  // 휴리스틱: 헤더 카피가 있는 라인 ± 2줄 윈도우에 isScoreSuppressed 가드가 있어야 한다.
  // (라인 기반 — return(...) 같은 구문 경계를 넘는 광역 오탐 회피.)
  const lines = source.split('\n');
  const headerLineIdx = lines.findIndex((l) => l.includes(HEADER_COPY));
  if (headerLineIdx === -1) {
    violations.push(`헤더 카피 '${HEADER_COPY}' 부재 (result.tsx 변경?)`);
  } else {
    const lo = Math.max(0, headerLineIdx - 2);
    // 정의 라인(const isScoreSuppressed =)은 가드로 치지 않는다 — 삼항/논리 사용만 가드.
    const windowText = lines
      .slice(lo, headerLineIdx + 1)
      .filter((l) => !/const\s+isScoreSuppressed\s*=/.test(l))
      .join('\n');
    if (!/isScoreSuppressed\s*(\?|&&)/.test(windowText)) {
      violations.push(
        `헤더 카피 '${HEADER_COPY}' 가 isScoreSuppressed 삼항/가드 밖 (비조건부 — iter2 HIGH-2 위반)`,
      );
    }
  }

  // (b) recognition_low_confidence 분기에 reference-free 라벨 하드코딩 leak 차단.
  const lowConfIdx = source.indexOf("'recognition_low_confidence'");
  if (lowConfIdx !== -1) {
    // recognition_low_confidence 식별 직후 ~120자 윈도우(해당 분기 카피)에 reference-free
    // 라벨이 없어야 한다 (reason-owns-copy — iter5 HIGH-2).
    const window = source.slice(lowConfIdx, lowConfIdx + 120);
    for (const leak of REFERENCE_FREE_LABELS) {
      if (window.includes(leak)) {
        violations.push(
          `recognition_low_confidence 분기에 reference-free 라벨 '${leak}' leak (reason-owns-copy 위반 — iter5 HIGH-2)`,
        );
      }
    }
  }

  return { ok: violations.length === 0, violations };
}

// ── --self-test: in-memory fixture 로 검사 로직 자체검증 (iter4 MEDIUM-2 / iter5 HIGH-2) ──
const GUARDED_SAMPLE = `
  const isScoreSuppressed = cmp.mode === 'mode3' && result.scoreSuppressed === true;
  const suppressedHeaderCopy = isScoreSuppressed
    ? result.scoreSuppressedReason === 'recognition_low_confidence'
      ? '동작 인식 신뢰도가 낮아 기준을 확정할 수 없어요.'
      : '기준 데이터가 없어요.'
    : null;
  return (
    <Text>{isScoreSuppressed ? suppressedHeaderCopy : '분석이 완료됐어요. 점수를 확인해보세요.'}</Text>
    {isScoreSuppressed ? (
      <View><Text>기준 없음</Text></View>
    ) : (
      <View>
        <OctagonScore />
        <Text style={styles.gradeBadge}>{grade}</Text>
        <Text style={styles.summary}>{summary}</Text>
        <LevelBenchmark />
        <Text style={styles.scoreCaption}>caption</Text>
      </View>
    )}
  );
`;

// OctagonScore 가 가드 밖에서도 한 번 더 렌더 (이중/비조건부 — else 분기 외부 등장).
const UNGUARDED_OCTAGON_SAMPLE = `
  const isScoreSuppressed = cmp.mode === 'mode3' && result.scoreSuppressed === true;
  return (
    <Text>{isScoreSuppressed ? '기준 없음' : '분석이 완료됐어요. 점수를 확인해보세요.'}</Text>
    <OctagonScore />
    {isScoreSuppressed ? (
      <View><Text>기준 없음</Text></View>
    ) : (
      <View>
        <OctagonScore />
        <Text style={styles.gradeBadge}>{grade}</Text>
        <Text style={styles.summary}>{summary}</Text>
        <LevelBenchmark />
        <Text style={styles.scoreCaption}>caption</Text>
      </View>
    )}
  );
`;

// 헤더 카피가 isScoreSuppressed 가드 밖에 비조건부로 렌더.
const UNGUARDED_HEADER_SAMPLE = `
  const isScoreSuppressed = cmp.mode === 'mode3' && result.scoreSuppressed === true;
  return (
    <Text>분석이 완료됐어요. 점수를 확인해보세요.</Text>
    {isScoreSuppressed ? (
      <View><Text>기준 없음</Text></View>
    ) : (
      <View>
        <OctagonScore />
        <Text style={styles.gradeBadge}>{grade}</Text>
        <Text style={styles.summary}>{summary}</Text>
        <LevelBenchmark />
        <Text style={styles.scoreCaption}>caption</Text>
      </View>
    )}
  );
`;

// recognition_low_confidence 분기가 reference-free '기준 동작 없음' 라벨로 떨어짐.
const LOW_CONF_LEAK_SAMPLE = `
  const isScoreSuppressed = cmp.mode === 'mode3' && result.scoreSuppressed === true;
  const suppressedHeaderCopy = isScoreSuppressed
    ? result.scoreSuppressedReason === 'recognition_low_confidence' ? '기준 동작 없음' : '기준 데이터가 없어요.'
    : null;
  return (
    <Text>{isScoreSuppressed ? suppressedHeaderCopy : '분석이 완료됐어요. 점수를 확인해보세요.'}</Text>
    {isScoreSuppressed ? (
      <View><Text>기준 없음</Text></View>
    ) : (
      <View>
        <OctagonScore />
        <Text style={styles.gradeBadge}>{grade}</Text>
        <Text style={styles.summary}>{summary}</Text>
        <LevelBenchmark />
        <Text style={styles.scoreCaption}>caption</Text>
      </View>
    )}
  );
`;

function runSelfTest() {
  const cases = [
    { name: 'guarded sample', source: GUARDED_SAMPLE, expectOk: true },
    {
      name: 'unguarded OctagonScore sample',
      source: UNGUARDED_OCTAGON_SAMPLE,
      expectOk: false,
    },
    {
      name: 'unguarded header copy sample',
      source: UNGUARDED_HEADER_SAMPLE,
      expectOk: false,
    },
    {
      name: 'low-confidence reason-leak sample',
      source: LOW_CONF_LEAK_SAMPLE,
      expectOk: false,
    },
  ];
  let failed = false;
  for (const c of cases) {
    const { ok } = assertSuppressionGuards(c.source);
    if (ok !== c.expectOk) {
      failed = true;
      console.error(
        `[self-test] FAIL '${c.name}' — 기대 ok=${c.expectOk}, 실제 ok=${ok}`,
      );
    } else {
      console.log(`[self-test] PASS '${c.name}' (ok=${ok})`);
    }
  }
  if (failed) {
    console.error('[self-test] 검사 함수 자체검증 실패 — 가드 로직 수정 필요');
    process.exit(1);
  }
  console.log('[self-test] 4 fixture 모두 기대대로 — 검사 함수 정상');
}

function runOnResultTsx() {
  const source = readFileSync(RESULT_TSX_URL, 'utf8');
  const { ok, violations } = assertSuppressionGuards(source);
  if (!ok) {
    for (const v of violations) {
      console.error(`[suppression] ${v}`);
    }
    console.error('[suppression] result.tsx 점수 억제 가드 위반 — non-zero exit');
    process.exit(1);
  }
  console.log('[suppression] result.tsx 점수카드 전체 억제 + reason-owns-copy 가드 통과');
}

if (process.argv.includes('--self-test')) {
  runSelfTest();
} else {
  runOnResultTsx();
}
