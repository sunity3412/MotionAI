// S12 화면 어휘 게이트 — 앱 렌더 표면 전수 스캔 (33-G §C-2 4단위, quick-260731-cum).
//
// 실행: node --test app/src/lib/__tests__/screenVocabulary.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행 — 신규 npm 의존성 0
// (summarySource.test.ts 선례). node:test / node:assert / node:fs 표준 모듈만.
//
// 왜 게이트인가: 승인 목업 7R#1 "'마무리 스플릿 국면' 같은 채점 내부 용어(국면·신전·
// 재신전·완성도)를 화면 문장에서 제거하고 강사 화법으로. … 일반 규칙 2건 박제 = …
// 화면 어휘 게이트". 33-G 는 잔재를 3곳으로 적었으나 실측은 7파일 16곳이었다 —
// 개별 패치는 다음 라운드에 또 샌다. 스캔이 상시 강제한다.
//
// 단일 출처(Q-6): 금지어 목록을 앱에 적어두지 않는다. backend/data/phrasebook.json
// `_meta.screenVocabularyGate.words` 를 **읽어서** 쓴다 (백엔드 게이트
// backend/tests/phase33/test_phrasebook_motion_specific.py::test_screen_vocabulary_gate
// 와 같은 데이터). 목록을 복제하면 다음 라운드에 drift 한다. 이 파일은 테스트 전용
// 경로라 앱 번들에 backend 경로가 들어가지 않는다.
//
// 스코프(Q-2): **`<Text>` 로 도달 가능한 문자열**만. 주석·타입 주석·소비자 0 데이터
// 필드는 대상 밖 — 목업 7R#1 "record 원문·수치는 대조 표에 보존(사실값 불변)".
// 그래서 .ts/.tsx 는 주석을 지운 뒤 검사하고, 제외는 아래 EXCLUSIONS 레지스트리에
// **소비자 0 grep 증거를 주석으로 달아** 명시적으로만 넣는다.

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const HERE = import.meta.dirname; // <repo>/app/src/lib/__tests__
const APP_SRC = path.join(HERE, '..', '..'); // <repo>/app/src
const REPO_ROOT = path.join(HERE, '..', '..', '..', '..'); // <repo>
const PHRASEBOOK_PATH = path.join(REPO_ROOT, 'backend', 'data', 'phrasebook.json');

/**
 * 제외 레지스트리 — `APP_SRC 기준 상대경로` → 면제할 **객체 속성 이름** 목록.
 * 면제 범위는 그 속성의 문자열 리터럴 값 하나뿐이다 (파일 통째 면제 금지).
 *
 * 항목을 늘리려면 "그 필드가 어떤 렌더 경로로도 반환되지 않는다"는 grep 증거가
 * 있어야 하고, SUMMARY 에 근거를 적는다.
 */
const EXCLUSIONS: Record<string, readonly string[]> = {};

// ── 금지어 (단일 출처) ────────────────────────────────────────────────────

function forbiddenWords(): string[] {
  const raw = JSON.parse(fs.readFileSync(PHRASEBOOK_PATH, 'utf8'));
  const words = raw?._meta?.screenVocabularyGate?.words;
  assert.ok(
    Array.isArray(words) && words.length > 0,
    'phrasebook.json _meta.screenVocabularyGate.words 부재 — 어휘 게이트 데이터 소실',
  );
  return words as string[];
}

// ── 소스 수집 ────────────────────────────────────────────────────────────

function listFiles(): { rel: string; abs: string; kind: 'ts' | 'json' }[] {
  const out: { rel: string; abs: string; kind: 'ts' | 'json' }[] = [];
  for (const entry of fs.readdirSync(APP_SRC, {
    recursive: true,
    withFileTypes: true,
  })) {
    if (!entry.isFile()) continue;
    const abs = path.join(entry.parentPath, entry.name);
    const rel = path.relative(APP_SRC, abs);
    if (rel.split(path.sep).includes('__tests__')) continue; // 테스트는 스캔 대상 밖
    if (entry.name.endsWith('.ts') || entry.name.endsWith('.tsx')) {
      out.push({ rel, abs, kind: 'ts' });
    } else if (entry.name.endsWith('.json')) {
      out.push({ rel, abs, kind: 'json' });
    }
  }
  return out;
}

// ── 주석 제거 (줄 번호 보존 — 주석 문자를 공백으로 치환) ────────────────────

/**
 * `//` 줄 주석과 `/* *\/` 블록 주석을 공백으로 치환한다. 문자열/템플릿 리터럴 안의
 * `//` 는 주석이 아니므로 상태 기계로 문자열 구간을 건너뛴다. 개행은 보존해
 * 위반 보고의 줄 번호가 원본과 일치한다.
 */
function stripComments(src: string): string {
  const out = src.split('');
  const blank = (from: number, to: number) => {
    for (let i = from; i < to && i < out.length; i += 1) {
      if (out[i] !== '\n') out[i] = ' ';
    }
  };
  let i = 0;
  const n = src.length;
  while (i < n) {
    const c = src[i];
    const c2 = src[i + 1];
    if (c === '/' && c2 === '/') {
      let j = i;
      while (j < n && src[j] !== '\n') j += 1;
      blank(i, j);
      i = j;
    } else if (c === '/' && c2 === '*') {
      let j = i + 2;
      while (j < n && !(src[j] === '*' && src[j + 1] === '/')) j += 1;
      blank(i, Math.min(j + 2, n));
      i = j + 2;
    } else if (c === "'" || c === '"' || c === '`') {
      const quote = c;
      let j = i + 1;
      while (j < n) {
        if (src[j] === '\\') {
          j += 2;
          continue;
        }
        if (src[j] === quote) break;
        // 홑/겹따옴표는 개행에서 끊는다 (미종료 리터럴이 파일 끝까지 먹는 것 방지).
        if (quote !== '`' && src[j] === '\n') break;
        j += 1;
      }
      i = j + 1;
    } else {
      i += 1;
    }
  }
  return out.join('');
}

/**
 * 제외 속성의 **문자열 리터럴 값**만 공백 처리 (줄 번호 보존).
 * `provenance:\n  '…'` 처럼 값이 다음 줄에서 시작하는 형태도 덮는다.
 */
function blankExcludedFields(src: string, fields: readonly string[]): string {
  let out = src;
  for (const field of fields) {
    const rx = new RegExp(
      `(^|[\\s{,])${field}\\s*:\\s*('(?:[^'\\\\]|\\\\.)*'|"(?:[^"\\\\]|\\\\.)*"|\`(?:[^\`\\\\]|\\\\.)*\`)`,
      'g',
    );
    out = out.replace(rx, (m, lead: string) => {
      const body = m.slice(lead.length);
      const blanked = body.replace(/[^\n]/g, ' ');
      return lead + blanked;
    });
  }
  return out;
}

// ── JSON: 문자열 "값"만 (키 제외) ──────────────────────────────────────────

function jsonStringValues(node: unknown, at: string, acc: { path: string; text: string }[]): void {
  if (typeof node === 'string') {
    acc.push({ path: at, text: node });
  } else if (Array.isArray(node)) {
    node.forEach((v, idx) => jsonStringValues(v, `${at}[${idx}]`, acc));
  } else if (node && typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      jsonStringValues(v, at ? `${at}.${k}` : k, acc);
    }
  }
}

// 원문에서 위반 값이 있는 줄 번호 (JSON 위반 보고용). 값 문자열 자체로 찾고,
// 여러 줄로 쪼개져 못 찾으면 금지어로 폴백한다.
function firstLineWith(raw: string, value: string, word: string): number {
  const lines = raw.split('\n');
  for (let i = 0; i < lines.length; i += 1) {
    if (lines[i].includes(value)) return i + 1;
  }
  for (let i = 0; i < lines.length; i += 1) {
    if (lines[i].includes(word)) return i + 1;
  }
  return 0;
}

// ── 게이트 ───────────────────────────────────────────────────────────────

interface Violation {
  file: string;
  line: number;
  word: string;
}

function scan(): { violations: Violation[]; scanned: number } {
  const words = forbiddenWords();
  const files = listFiles();
  const violations: Violation[] = [];

  for (const f of files) {
    const raw = fs.readFileSync(f.abs, 'utf8');
    if (f.kind === 'ts') {
      let body = stripComments(raw);
      const excluded = EXCLUSIONS[f.rel.split(path.sep).join('/')];
      if (excluded) body = blankExcludedFields(body, excluded);
      const lines = body.split('\n');
      lines.forEach((lineText, idx) => {
        for (const w of words) {
          if (lineText.includes(w)) {
            violations.push({ file: f.rel, line: idx + 1, word: w });
          }
        }
      });
    } else {
      const parsed = JSON.parse(raw);
      const values: { path: string; text: string }[] = [];
      jsonStringValues(parsed, '', values);
      const excluded = new Set(EXCLUSIONS[f.rel.split(path.sep).join('/')] ?? []);
      for (const v of values) {
        const leaf = v.path.split('.').pop()?.replace(/\[\d+\]$/, '') ?? '';
        if (excluded.has(leaf)) continue;
        for (const w of words) {
          if (v.text.includes(w)) {
            violations.push({
              file: f.rel,
              line: firstLineWith(raw, v.text, w),
              word: w,
            });
          }
        }
      }
    }
  }
  return { violations, scanned: files.length };
}

test('S12 게이트 데이터: 금지어 목록은 backend/data/phrasebook.json 단일 출처에서 온다', () => {
  const words = forbiddenWords();
  // 앱에 목록 리터럴을 복제하지 않는다 — 값 자체를 단언하지 않고 형상만 본다.
  assert.ok(words.every((w) => typeof w === 'string' && w.length > 0));
  assert.ok(words.length >= 4, `금지어가 ${words.length}개 — 게이트 무의미 의심`);
});

test('S12 sanity: 스캔 대상 파일이 비어있지 않다 (glob 붕괴 = 게이트 무의미 회귀 차단)', () => {
  const files = listFiles();
  assert.ok(files.length >= 50, `스캔 파일 ${files.length}개 — 경로/필터 확인`);
  assert.ok(
    files.some((f) => f.kind === 'json'),
    'app/src 하위 json 이 스캔되지 않음',
  );
});

test('S12 주석 스트리퍼: 주석은 지우고 코드 문자열은 남긴다 (줄 번호 보존)', () => {
  const src = ["// 국면 주석", "const a = '완성도';", "/* 신전", "블록 */", "const b = 1;"].join(
    '\n',
  );
  const out = stripComments(src);
  const lines = out.split('\n');
  assert.equal(lines.length, 5, '개행 보존 실패 — 줄 번호가 어긋난다');
  assert.ok(!lines[0].includes('국면'), '줄 주석이 남았다');
  assert.ok(lines[1].includes('완성도'), '코드 문자열이 지워졌다');
  assert.ok(!lines[2].includes('신전'), '블록 주석이 남았다');
  assert.ok(lines[4].includes('const b'), '블록 주석 종료 후 코드가 지워졌다');
});

test('S12 제외 레지스트리: 지정 필드의 문자열 값만 면제된다 (파일 통째 면제 아님)', () => {
  const src = ["const x = {", "  provenance:", "    '신전 근거',", "  label: '신전 라벨',", "};"].join(
    '\n',
  );
  const out = blankExcludedFields(src, ['provenance']);
  assert.ok(!out.includes('신전 근거'), 'provenance 값이 면제되지 않았다');
  assert.ok(out.includes('신전 라벨'), '다른 필드까지 면제됐다 — 게이트 무력화');
  assert.equal(out.split('\n').length, 5, '개행 보존 실패');
});

test('S12 화면 어휘 게이트: 앱 렌더 표면에 채점 내부 용어 0 (7R#1)', () => {
  const { violations, scanned } = scan();
  const report = violations.map((v) => `${v.file}:${v.line}:${v.word}`).join('\n');
  assert.equal(
    violations.length,
    0,
    `화면 어휘 게이트 위반 ${violations.length}건 (스캔 ${scanned}파일):\n${report}`,
  );
});
