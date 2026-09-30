// supplierCopy 문구 단일점 검증 (Phase 38 D-09·D-13·D-15·D-18, 리뷰 R7·R11).
//
// 실행: node --test app/src/constants/supplierCopy.test.ts
// pickerFailure.test.ts 와 같은 어법 — Node 24 type stripping 으로 트랜스파일 없이 실행된다.
// node:test / node:assert / node:fs 표준 모듈만 쓰고 `.ts` 확장자 import 를 명시한다
// (신규 npm 의존성 0).
//
// 검증 축:
//   1) docs/supplier-guide.md(정본)와 guide.* 가 글자 단위로 같다 — md 를 fs 로 읽어 verbatim 포함.
//   2) 고정 각도·거리 문구(45°·2~3 미터·측면)·이모지가 값 어디에도 없다(D-15·D-16).
//   3) D-15 문장이 TIP 첫 줄(row.tip[0])과 파일 알약(form.sec4.pill[0])에 있다.
//   4) 실패 8코드·만료·고지 문구가 비어 있지 않다(D-09, R4, R11).
//   5) 동의 문안 4건 = 기획안 §6 원문(D-08).
//   6) ui-checker flags 적용값(#1 #2 #3)이 §Copywriting 원문 대신 들어갔다.
//   7) 크레딧·결제 문구 없음(D-13).
//   8) 실패 문구 3원 일치 — row.fail.<code>.title + '. ' + body 가 analysis.ts
//      REGISTRATION_ERROR_MESSAGE(= models.py = contract.md §5) 텍스트에 verbatim 존재.
//      analysis.ts 는 타입 파일이라 import 하지 않고 텍스트로 읽는다.
//   9) R7/R11 정직 문구 — 선언은 보관만, 자기 점수는 일관성 진단.
//  10) Figma 1:499 확정 다이얼로그 2종이 pickerFailure.ts 와 같은 원문이다.
//  11) 38-DESIGN.md(Figma 282:506, 2026-09-30) 새/바뀐 문구 키 값 잠금 + 지운 키가 없다.
//  12) 38-DESIGN-v2(quick-260930-lfw) A-2 초대받은 분만 · 강사 코드 줄 · 크게 보기 문구 + 지운 키.

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { supplierCopy } from './supplierCopy.ts';
import { describePickFailure } from '../lib/pickerFailure.ts';

const HERE = import.meta.dirname; // <repo>/app/src/constants
const GUIDE_MD = fs.readFileSync(
  path.join(HERE, '..', '..', '..', 'docs', 'supplier-guide.md'),
  'utf8',
);
const ANALYSIS_TS = fs.readFileSync(
  path.join(HERE, '..', 'types', 'analysis.ts'),
  'utf8',
);

// 값 트리의 모든 문자열을 (경로, 값) 로 모은다 — 배열·중첩 객체 포함.
function collectStrings(
  node: unknown,
  prefix: string,
  out: Array<[string, string]>,
): void {
  if (typeof node === 'string') {
    out.push([prefix, node]);
    return;
  }
  if (Array.isArray(node)) {
    node.forEach((v, i) => collectStrings(v, `${prefix}[${i}]`, out));
    return;
  }
  if (node && typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      collectStrings(v, prefix ? `${prefix}.${k}` : k, out);
    }
  }
}

const ALL_STRINGS: Array<[string, string]> = [];
collectStrings(supplierCopy, '', ALL_STRINGS);

const D15_SENTENCE = '기준 영상처럼 찍으세요(폴 전체와 전신이 들어오는 거리, 세로, 고정)';

// ── 1) guide.* ↔ docs/supplier-guide.md ───────────────────────────────────

test('guide.* 의 모든 문자열이 docs/supplier-guide.md 에 verbatim 으로 들어 있다', () => {
  const guideStrings: Array<[string, string]> = [];
  collectStrings(supplierCopy.guide, 'guide', guideStrings);
  assert.ok(guideStrings.length >= 40, `guide 문자열 수 ${guideStrings.length}`);
  for (const [p, s] of guideStrings) {
    assert.ok(GUIDE_MD.includes(s), `md 에 없음: ${p} = ${s}`);
  }
});

test('md 의 ## 제목 7개가 guide.s1..s7.h 와 같은 순서·같은 글자다', () => {
  const headings = GUIDE_MD.split('\n')
    .filter((line) => line.startsWith('## '))
    .map((line) => line.slice(3));
  const expected = [
    supplierCopy.guide.s1.h,
    supplierCopy.guide.s2.h,
    supplierCopy.guide.s3.h,
    supplierCopy.guide.s4.h,
    supplierCopy.guide.s5.h,
    supplierCopy.guide.s6.h,
    supplierCopy.guide.s7.h,
  ].map((h, i) => `${i + 1}. ${h}`);
  assert.deepEqual(headings, expected);
});

test('guide 섹션 7개 = D-18 7항목 제목 그대로', () => {
  assert.equal(supplierCopy.guide.s1.h, '어떻게 찍나요');
  assert.equal(supplierCopy.guide.s2.h, '영상 하나에 동작 하나');
  assert.equal(supplierCopy.guide.s3.h, '올릴 때 왜 4가지를 묻나요');
  assert.equal(supplierCopy.guide.s4.h, '올리면 무엇이 보이나요');
  assert.equal(supplierCopy.guide.s5.h, '권리와 동의');
  assert.equal(supplierCopy.guide.s6.h, '내 코드를 수강생에게 알려주는 법');
  assert.equal(supplierCopy.guide.s7.h, '자주 틀리는 것');
  assert.equal(supplierCopy.guide.s4.tip.length, 4);
  assert.equal(supplierCopy.guide.s4.tipHead, '등록이 안 되는 4가지');
});

// ── 2) 고정 각도·거리·이모지 없음 ───────────────────────────────────────────

// 38-02 정정 게이트(`grep -rn` 로 app/src·docs 에서 옛 거리 문구 0건)가 이 테스트 파일까지
// 잡으므로 거리 토큰은 조각으로 붙인다 — 값을 검사하는 문자열 자체는 같다.
const BANNED_TOKENS = ['45°', ['2~3', 'm'].join(''), '측면'] as const;

test('값 어디에도 45° · 2~3 미터 · 측면 · 이모지가 없다 (D-15·D-16)', () => {
  const emoji = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
  for (const [p, s] of ALL_STRINGS) {
    for (const banned of BANNED_TOKENS) {
      assert.ok(!s.includes(banned), `${p} 에 '${banned}': ${s}`);
    }
    assert.ok(!emoji.test(s), `${p} 에 이모지: ${s}`);
  }
  for (const banned of BANNED_TOKENS) {
    assert.ok(!GUIDE_MD.includes(banned), `md 에 '${banned}'`);
  }
});

// ── 3) D-15 문장 자리 ──────────────────────────────────────────────────────

test('D-15 문장이 row.tip[0] 과 form.sec4.pill[0] 에 있다', () => {
  assert.ok(supplierCopy.row.tip[0].includes(D15_SENTENCE));
  assert.ok(supplierCopy.form.sec4.pill[0].includes(D15_SENTENCE));
  assert.equal(supplierCopy.row.tip.length, 3);
  assert.equal(supplierCopy.form.sec4.pill.length, 2);
});

// ── 4) 실패·만료·고지 문구 비공백 ──────────────────────────────────────────

const FAIL_CODES = [
  'no_human',
  'multiple_people',
  'no_standing_start',
  'low_confidence',
  'too_short',
  'too_long',
  'too_large',
  'server_error',
] as const;

test('row.fail 8코드 각각 title·body 비공백 (D-09 + R9 too_large)', () => {
  for (const code of FAIL_CODES) {
    const c = supplierCopy.row.fail[code];
    assert.ok(c.title.trim().length > 0, `${code}.title`);
    assert.ok(c.body.trim().length > 0, `${code}.body`);
    assert.ok(!c.title.endsWith('.'), `${code}.title 끝 마침표 없음(조인 규칙)`);
    assert.ok(c.body.endsWith('.'), `${code}.body 는 마침표로 끝난다(조인 규칙)`);
  }
  assert.deepEqual(Object.keys(supplierCopy.row.fail), [...FAIL_CODES]);
});

test('row.status.expired · row.expired.* · row.self.note 비공백 (R4/R11)', () => {
  assert.ok(supplierCopy.row.status.expired.length > 0);
  assert.ok(supplierCopy.row.expired.title.length > 0);
  assert.ok(supplierCopy.row.expired.body.length > 0);
  assert.ok(supplierCopy.row.self.note.length > 0);
  assert.ok(supplierCopy.row.status.expired.startsWith(supplierCopy.row.expired.title));
});

// ── 5) 동의 문안 = 기획안 §6 원문 ─────────────────────────────────────────

test('form.sec5 동의 문안 4건이 기획안 §6 원문과 같다 (D-08)', () => {
  assert.equal(supplierCopy.form.sec5.portrait, '초상·성명 사용 동의(앱 내 표시·재생)');
  assert.equal(
    supplierCopy.form.sec5.usage,
    '영상 이용 허락 — 분석 기준 사용 · 프레임 추출·표시 · 썸네일',
  );
  assert.equal(supplierCopy.form.sec5.silent, '무음 영상 확인(음악·안무 라이선스 회피)');
  assert.equal(supplierCopy.form.sec5.training, '학습 사용 동의');
});

// ── 6) ui-checker flags 적용값 ─────────────────────────────────────────────

test('ui-checker flags #2 적용값 (§Decisions 표가 §Copywriting 원문보다 우선)', () => {
  // #1(common.copy)·#3(codePending*) 은 38-DESIGN-v2 가 코드 카드를 지우며 키째 빠졌다 — 12) 가 잠근다.
  assert.equal(supplierCopy.common.cancel, '올리기 취소');
  // 38-DESIGN A-3: '>' 대신 쉐브론 아이콘
  assert.equal(supplierCopy.home.upload, '동작 올리기');
  assert.ok(!supplierCopy.home.upload.includes('>'));
});

// ── 7) 크레딧·결제 없음 ─────────────────────────────────────────────────────

test('크레딧·결제·금액 문구가 값 어디에도 없다 (D-13)', () => {
  // '원' 은 '회원님'·'운영팀' 같은 낱말에 들어가므로 금액 어법(숫자 뒤 원)만 잡는다.
  const money = /\d[\d,]*\s*원/;
  for (const [p, s] of ALL_STRINGS) {
    assert.ok(!s.includes('크레딧'), `${p}: ${s}`);
    assert.ok(!s.includes('결제'), `${p}: ${s}`);
    assert.ok(!money.test(s), `${p} 에 금액: ${s}`);
  }
});

// ── 8) 실패 문구 3원 일치 (no_human 제외) ──────────────────────────────────

test('row.fail 7코드의 title + ". " + body 가 analysis.ts REGISTRATION_ERROR_MESSAGE 에 verbatim 존재', () => {
  // no_human 은 D-09 예외 — 계약(models.py·analysis.ts)은 기존 ERROR_MESSAGE.no_human
  // ('영상에서 사람을 찾지 못했어요. …')을 객체 참조로 재사용하고, 페이지는 Figma 1:479
  // 원문('영상 안에 사람이 보이지 않아요')을 쓴다. 두 문구가 다른 것이 의도된 상태라
  // 대조하지 않는다(38-01 SUMMARY · contract.md §5).
  const block = ANALYSIS_TS.slice(ANALYSIS_TS.indexOf('export const REGISTRATION_ERROR_MESSAGE'));
  assert.ok(block.length > 0, 'REGISTRATION_ERROR_MESSAGE 블록을 찾지 못했다');
  const body = block.slice(0, block.indexOf('\n};'));
  for (const code of FAIL_CODES) {
    if (code === 'no_human') continue;
    const c = supplierCopy.row.fail[code];
    const joined = `${c.title}. ${c.body}`;
    assert.ok(body.includes(joined), `analysis.ts 에 없음: ${code} = ${joined}`);
    assert.ok(body.includes(`${code}:`), `analysis.ts 키 없음: ${code}`);
  }
  // {joints} 자리는 치환 전 원문 그대로 대조된다.
  assert.ok(supplierCopy.row.fail.low_confidence.body.includes('{joints}'));
});

// ── 9) R7/R11 정직 문구 ────────────────────────────────────────────────────

test('R7 — 선언은 등록 정보로 보관, 채점 규칙 약속 문구 없음', () => {
  assert.ok(supplierCopy.form.sec2.name.helper.includes('등록 정보로 보관'));
  assert.ok(supplierCopy.guide.s3.items[0].includes('등록 정보로 보관'));
  for (const [p, s] of ALL_STRINGS) {
    assert.ok(
      !s.includes('채점 규칙(펴야 하는 관절, 실수 문장)이 같이 붙어요'),
      `${p}: 옛 R7 문구`,
    );
  }
});

test('R11 — 자기 점수는 일관성 진단, 고지 문장 고정, low 는 다시 찍기 유지', () => {
  assert.ok(supplierCopy.row.self.okBody.includes('추출·저장이 일관돼요'));
  assert.equal(supplierCopy.row.self.title, '자기 영상 재분석');
  for (const [p, s] of ALL_STRINGS) {
    assert.ok(!s.includes('기준으로 쓸 수 있어요'), `${p}: 옛 R11 문구`);
  }
  assert.equal(supplierCopy.row.self.note, '동작 정확도는 시험 영상으로 따로 봐요.');
  assert.ok(supplierCopy.row.self.lowBody.includes('다시 찍어 주세요'));
  assert.ok(supplierCopy.row.status.selfLow.includes('다시 찍어 주세요'));
});

// ── 10) Figma 1:499 확정 다이얼로그 = pickerFailure.ts 원문 ──────────────────

test('dialog.format · dialog.tooLarge 가 pickerFailure.ts 의 Figma 확정 문구와 같다', () => {
  const format = describePickFailure('format');
  const tooLarge = describePickFailure('tooLarge');
  assert.equal(supplierCopy.dialog.format.title, format.title);
  assert.deepEqual([...supplierCopy.dialog.format.lines], format.lines);
  assert.equal(supplierCopy.dialog.tooLarge.title, tooLarge.title);
  assert.deepEqual([...supplierCopy.dialog.tooLarge.lines], tooLarge.lines);
  assert.equal(supplierCopy.form.sec4.repick, format.primaryLabel);
  for (const kind of ['format', 'tooLarge', 'tooShort', 'tooLong', 'unreadable'] as const) {
    assert.equal(supplierCopy.dialog[kind].lines.length, 2, `${kind} 는 2줄`);
  }
});

// ── 11) 38-DESIGN.md 새/바뀐 문구 키 ────────────────────────────────────────

test('38-DESIGN.md 새/바뀐 문구 키', () => {
  const c = supplierCopy;
  assert.equal(c.login.chip, '강사·선수 전용');
  assert.equal(c.home.count, '{n}개');
  assert.equal(c.home.upload, '동작 올리기');
  assert.equal(c.form.sec5.allHint, '필수 3개');
  assert.equal(c.row.done.sub, '{name} · {athlete} 선수');
  assert.equal(c.row.self.title, '자기 영상 재분석');
  assert.equal(c.row.self.okBody, '추출·저장이 일관돼요.');
  assert.equal(c.row.self.lowBody, '낮아요. 다시 찍어 주세요.');
  assert.equal(c.row.self.scoreText, '{score}점');
  assert.equal(c.form.uploading.progressLabel, '올리는 중');
  assert.equal(c.form.uploading.pct, '{pct}%');
  assert.equal(c.form.uploading.keepOpen, '화면을 닫지 마세요. 다 올라가면 목록으로 돌아가요.');
  assert.equal(c.form.uploading.summaryTitle, '{name} · {level}');
  assert.equal(c.form.uploading.summaryMeta, '{file} · {meta}');
  assert.equal(c.form.sec1.guideLink, '자세한 가이드');
  // 한 줄 문구를 둘로 나눈 키 — 옛 키가 남아 있으면 소비처가 옛 문구를 계속 읽을 수 있다.
  assert.equal('progress' in c.form.uploading, false);
  assert.equal('codePending' in c.home, false);
  assert.equal('ok' in c.row.self, false);
  assert.equal('low' in c.row.self, false);
});

// ── 12) 38-DESIGN-v2 (quick-260930-lfw) ─────────────────────────────────────

test('38-DESIGN-v2 A-2 초대받은 분만 — 문구 글자 단위', () => {
  const n = supplierCopy.noAccess;
  assert.equal(n.title, '초대받은 분만 쓸 수 있어요');
  assert.equal(
    n.body,
    '공급자 페이지는 Sunity 가 초대한 강사·선수만 쓸 수 있어요. 초대받으셨다면 초대받은 Google 계정으로 로그인해 주세요.',
  );
  assert.equal(n.accountLabel, '지금 로그인한 계정');
  assert.equal(n.helpTitle, '초대가 필요하거나 계정이 헷갈리면');
  assert.equal(n.helpBody, '아래로 알려 주세요. 운영팀이 확인해 드려요.');
  assert.equal(n.kakaoTitle, '카카오톡 채널로 문의');
  assert.equal(n.kakaoSub, 'pf.kakao.com/_CyNxkn');
  assert.equal(n.kakaoUrl, 'http://pf.kakao.com/_CyNxkn');
  assert.equal(n.mailTitle, '메일로 문의');
  assert.equal(n.mailSub, 'cs@sunity.ai');
  assert.equal(n.mailUrl, 'mailto:cs@sunity.ai');
  assert.equal(n.checking, '확인하는 중...');
});

test('38-DESIGN-v2 A-3 강사 코드 줄 · 크게 보기 문구', () => {
  assert.deepEqual(supplierCopy.home.codeRow, { label: '내 강사 코드', copy: '복사', big: '크게 보기' });
  assert.deepEqual(supplierCopy.bigCode, {
    title: '{name} 강사님의 코드',
    titleNoName: '내 강사 코드',
    how: 'Sunity 앱 → 마이 → 강사 코드에\n이 코드를 넣어 주세요',
  });
  assert.equal(supplierCopy.common.copied, '복사됐어요');
});

test('38-DESIGN-v2 가 지운 키가 없다 (옛 ID 닭-달걀 절차 · 코드 카드 · 빌드 라벨)', () => {
  const c = supplierCopy as unknown as Record<string, Record<string, unknown>>;
  for (const k of ['idLabel', 'copyId', 'refresh', 'stillNo', 'refreshHint']) {
    assert.equal(k in c.noAccess, false, `noAccess.${k}`);
  }
  for (const k of ['codeTitle', 'athlete', 'sport', 'codeHow', 'codePendingTitle', 'codePendingBody']) {
    assert.equal(k in c.home, false, `home.${k}`);
  }
  for (const k of ['build', 'copy', 'copiedShort']) {
    assert.equal(k in c.common, false, `common.${k}`);
  }
});
