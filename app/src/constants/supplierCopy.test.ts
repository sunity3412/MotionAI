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
//   4) 실패 9코드(rejected 포함)·만료·고지 문구가 비어 있지 않다(D-09, R4, R11, quick-261001-thx).
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
//  13) quick-260930-w9l(belle 2026-09-30 폰 확인) — 필수 표시 · 체크 4 · 동의 2 + 보기 · 학습 계약
//      안내 · 5초~2분 · 1GB · 소리 서버 제거 · 선언 3 삭제 · 선수 이름 고정 · 초급 + 지운 키.
//  15) quick-261002-pa2(belle 2026-10-02 결정 1·3·4·6) — 검토 요청 말(검토 중 · 하루 안 · 검토를 요청했어요),
//      요청 취소 확인창 · 취소 오류(models.py 와 같은 글자) · 취소됨, 메일 · 기한 약속 없음.

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
// pa2 — 취소 오류 문구는 서버 models.py 상수와 같은 글자여야 한다(앱은 code 로만 분기하지만 문구가 갈리면
// belle 이 두 곳을 봐야 한다). 텍스트로 읽어 대조한다.
const MODELS_PY = fs.readFileSync(
  path.join(HERE, '..', '..', '..', 'backend', 'shared', 'python', 'sunity_shared', 'models.py'),
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
  // w9l — s2·s3 제목이 바뀌었다(콤보·선언 3 삭제).
  assert.equal(supplierCopy.guide.s2.h, '길이와 시작');
  assert.equal(supplierCopy.guide.s3.h, '올릴 때 무엇을 적나요');
  assert.equal(supplierCopy.guide.s4.h, '올리면 무엇이 보이나요');
  assert.equal(supplierCopy.guide.s5.h, '권리와 동의');
  assert.equal(supplierCopy.guide.s7.h, '자주 틀리는 것');
  // 261001-thx — 등록 = 자동 읽기 + 운영팀 확인. 옛 '등록이 안 되는 4가지' → '잘 찍는 팁' 3줄.
  assert.equal(supplierCopy.guide.s4.tip.length, 3);
  assert.equal(supplierCopy.guide.s4.tipHead, '잘 찍는 팁');
  assert.equal(supplierCopy.guide.s6.h, '내 강사 코드를 수강생에게 알려 주는 법');
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
  'rejected',
] as const;

test('row.fail 9코드 각각 title·body 비공백 (D-09 + R9 too_large + thx rejected)', () => {
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

test('form.sec5 동의 = 필수 2 + 보기 + 필수 안내 + 학습 계약 안내 (w9l 항목 4·5·11)', () => {
  const c = supplierCopy.form.sec5;
  assert.equal(c.portrait, '초상·성명 사용 동의');
  assert.equal(c.usage, '영상 이용 동의');
  assert.equal(c.tagRequired, '[필수]');
  assert.equal(c.view, '보기');
  assert.equal(c.allHint, '필수 2개');
  assert.equal(c.requiredNote, '필수 항목에 동의하지 않으면 등록할 수 없어요.');
  assert.equal(
    c.trainingNotice,
    '올린 영상은 공급자 계약에 따라 Sunity AI 학습에도 쓰여요. 학습용 영상과 데이터는 외부에 공개하거나 넘기지 않아요.',
  );
  assert.equal(c.error, '필수 동의 2가지에 체크해주세요.');
  for (const gone of ['silent', 'training', 'trainingNote', 'withdraw', 'tagOptional']) {
    assert.equal(gone in c, false, `form.sec5.${gone}`);
  }
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

test('row.fail 8코드의 title + ". " + body 가 analysis.ts REGISTRATION_ERROR_MESSAGE 에 verbatim 존재', () => {
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
  // {joints} · {reason} 자리는 치환 전 원문 그대로 대조된다.
  assert.ok(supplierCopy.row.fail.low_confidence.body.includes('{joints}'));
  assert.ok(supplierCopy.row.fail.rejected.body.includes('{reason}'));
});

// ── 14) quick-261001-thx — 검수 중 · 반려 ───────────────────────────────────

test('thx — 승인 전 한 문구 · row.fail.rejected 글자 단위', () => {
  // belle 10-01 "아주 심플하게" — registering/queued/processing/review 를 한 문구로. 옛 키는 없다.
  // pa2(belle 10-02 결정 3) — 그 한 문구 = '검토 중'(앱인토스 콘솔 상태어 벤치).
  assert.equal(supplierCopy.row.status.checking, '검토 중');
  const st = supplierCopy.row.status as unknown as Record<string, unknown>;
  for (const gone of ['registering', 'queued', 'processing', 'review']) {
    assert.equal(gone in st, false, `row.status.${gone}`);
  }
  for (const [p, s] of ALL_STRINGS) {
    assert.ok(!s.includes('올린 영상 확인 중'), `${p}: ${s}`);
    assert.ok(!s.includes('운영팀 확인 중'), `${p}: ${s}`);
  }
  assert.deepEqual(supplierCopy.row.fail.rejected, {
    title: '운영팀 확인에서 등록되지 않았어요',
    body: '이유: {reason}. 고쳐서 다시 올려 주세요.',
  });
});

test('thx — 공급자 문구에 서 있는 시작 요구 · 내부어 검수 · 느낌표가 없다', () => {
  // 실패 패널의 no_standing_start 는 2026-10-01 이전 doc 용이라 예외(서버가 더 내지 않는다).
  for (const [p, s] of ALL_STRINGS) {
    if (p.startsWith('row.fail.no_standing_start')) continue;
    assert.ok(!s.includes('서 있는 자세에서 시작했'), `${p}: ${s}`);
    assert.ok(!s.includes('서 있는 시작이 없'), `${p}: ${s}`);
    assert.ok(!s.includes('검수'), `${p}: ${s}`);
    assert.ok(!s.includes('!'), `${p}: ${s}`);
  }
  assert.ok(!GUIDE_MD.includes('등록이 안 되는 4가지'));
  assert.deepEqual([...supplierCopy.guide.s4.items], [
    '올리면 관절을 자동으로 읽은 뒤, 운영팀이 확인하고 기준 동작으로 올려요. 확인 전에는 수강생에게 보이지 않아요.',
    '확인이 끝나면 앱의 기준 동작 목록에 올라가요. 다시 올려야 하면 이유를 함께 알려 드려요.',
  ]);
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
  assert.ok(supplierCopy.row.self.okBody.includes('저장이 일관돼요'));
  assert.equal(supplierCopy.row.self.title, '자기 영상 재분석');
  for (const [p, s] of ALL_STRINGS) {
    assert.ok(!s.includes('기준으로 쓸 수 있어요'), `${p}: 옛 R11 문구`);
  }
  assert.equal(supplierCopy.row.self.note, '동작 정확도는 시험 영상으로 따로 봐요.');
  assert.ok(supplierCopy.row.self.lowBody.includes('다시 찍어 주세요'));
  assert.ok(supplierCopy.row.status.selfLow.includes('다시 찍어 주세요'));
});

// ── 10) Figma 1:499 확정 다이얼로그 = pickerFailure.ts 원문 ──────────────────

test('dialog.format 은 pickerFailure.ts 와 같고 dialog.tooLarge 는 제목만 같다(1GB)', () => {
  const format = describePickFailure('format');
  const tooLarge = describePickFailure('tooLarge');
  assert.equal(supplierCopy.dialog.format.title, format.title);
  assert.deepEqual([...supplierCopy.dialog.format.lines], format.lines);
  // belle 2026-09-30(quick-260930-w9l 항목 7) — 공급자 기준 등록만 1GB 로 갈라졌다. 수강생 분석
  // 경로(pickerFailure.ts)는 100MB 그대로라 본문 첫 줄이 다르고, 제목은 같다.
  assert.equal(supplierCopy.dialog.tooLarge.title, tooLarge.title);
  assert.deepEqual([...supplierCopy.dialog.tooLarge.lines], [
    '1GB 이하 영상만 올릴 수 있어요.',
    '영상을 잘라서 다시 시도해 주세요.',
  ]);
  assert.notDeepEqual([...supplierCopy.dialog.tooLarge.lines], tooLarge.lines);
  assert.deepEqual([...supplierCopy.dialog.tooLong.lines], [
    '기준 동작은 2분 이내로 올릴 수 있어요.',
    '동작이 담긴 부분만 잘라서 다시 선택해주세요.',
  ]);
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
  assert.equal(c.form.sec5.allHint, '필수 2개'); // w9l — 필수 동의 3 → 2
  assert.equal(c.row.done.sub, '{name} · {athlete} 선수');
  assert.equal(c.row.self.title, '자기 영상 재분석');
  // 261001-thx 문구 다듬기 — '추출' 기술어 · '낮아요.' 단독 문장을 풀었다(Figma 282:506 원문과 다름).
  assert.equal(c.row.self.okBody, '관절 읽기와 저장이 일관돼요.');
  assert.equal(c.row.self.lowBody, '점수가 낮아요. 관절을 잘못 읽었을 수 있으니 다시 찍어 주세요.');
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
    '공급자 페이지는 Sunity가 초대한 강사·선수만 쓸 수 있어요. 초대 메일을 받은 Google 계정으로 로그인해 주세요.',
  );
  assert.equal(n.accountLabel, '지금 로그인한 계정');
  assert.equal(n.helpTitle, '초대가 필요하거나 계정이 헷갈리면');
  assert.equal(n.helpBody, '아래로 알려 주세요. 운영팀이 확인해 드려요.');
  assert.equal(n.kakaoTitle, '카카오톡 채널로 문의');
  assert.equal('kakaoSub' in n, false); // belle 09-30: 카카오 줄 부제 없음
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

// ── 13) quick-260930-w9l (belle 2026-09-30 폰 확인) ─────────────────────────

test('w9l — 필수 표시 · 촬영 전 체크 4 · 선수 이름 고정 · 초급 · 파일 알약', () => {
  const f = supplierCopy.form;
  assert.equal(f.requiredTag, '필수');
  assert.equal(f.remaining, '필수 항목 {n}개가 남았어요');
  assert.deepEqual([...f.sec1.items], [
    '· 세로로, 삼각대나 거치대에 고정해서 찍었어요. 손으로 들고 찍지 않았어요.',
    '· 폴 전체(천장~바닥)와 몸 전체가 동작 내내 화면 안에 있어요. 카메라는 약 4~5m 떨어져 있어요.',
    '· 한 사람만 나오고, 밝은 실내예요. 창을 등지지 않았어요.',
  ]);
  // 261001-thx — 서 있는 시작은 더 이상 등록 조건이 아니라 체크 항목에서 뺐다(4 → 3).
  assert.equal(f.sec1.confirm, '위 3가지를 확인했어요');
  assert.equal(
    supplierCopy.home.emptyBody,
    '올린 동작은 운영팀 확인 뒤 앱의 기준 동작 목록에 올라가요. 올리기 전에 촬영 전 체크 3가지를 확인해 주세요.',
  );
  assert.equal(
    f.sec2.name.helper,
    '동작 이름은 등록 정보로 보관해요. 지금은 정은지 선수 기준 영상과 같은 기본 비교 방식으로 채점해요. 동작별 채점 규칙은 다음 단계에서 더해요.',
  );
  assert.equal(
    f.sec2.athlete.helper,
    '초대할 때 확인한 실명이에요. 앱의 기준 동작 목록에 이 이름으로 보여요. 바꾸려면 운영팀에 알려주세요.',
  );
  assert.equal(f.sec2.athlete.missing, '선수 이름이 아직 등록되지 않았어요. 운영팀에 알려주시면 등록해 드려요.');
  assert.deepEqual(f.sec2.level.options, { basic: '초급', intermediate: '중급', advanced: '고급' });
  assert.deepEqual([...f.sec4.pill], [
    '기준 영상처럼 찍으세요(폴 전체와 전신이 들어오는 거리, 세로, 고정)',
    '5초~2분 · 1GB 이하 · 소리는 자동으로 지워요',
  ]);
  assert.equal(supplierCopy.row.tip[2], '· 길이는 5초~2분');
});

test('w9l — 지운 키가 없다 (콤보 · 선언 3 · 선수 이름 오류 · 상세 표 선언 행)', () => {
  const f = supplierCopy.form as unknown as Record<string, Record<string, unknown>>;
  assert.equal('sec3' in f, false, 'form.sec3');
  assert.equal('combo' in f.sec2, false, 'form.sec2.combo');
  assert.equal('error' in (f.sec2.athlete as Record<string, unknown>), false, 'form.sec2.athlete.error');
  const info = supplierCopy.row.done.info as unknown as Record<string, unknown>;
  for (const k of ['split', 'hold', 'stand']) {
    assert.equal(k in info, false, `row.done.info.${k}`);
  }
  // 30초·60초·무음·100MB 약속이 공급자 문구 어디에도 남지 않는다.
  for (const [p, s] of ALL_STRINGS) {
    for (const stale of ['30초', '60초', '5~30초', '100MB', '무음']) {
      assert.ok(!s.includes(stale), `${p} 에 '${stale}': ${s}`);
    }
  }
});

test('w9l — 가이드 s2 · s3 · s5 · s7 새 문구', () => {
  const g = supplierCopy.guide;
  assert.deepEqual([...g.s2.items], [
    '길이는 5초~2분이에요. 동작 하나도, 여러 동작을 이은 콤보도 올릴 수 있어요.',
    '가능하면 폴 옆에 서서 1초쯤 있다가 시작해 주세요. 서 있는 순간이 발 높이를 재는 기준이 돼요.',
    '소리는 신경 쓰지 않아도 돼요. 등록할 때 영상의 소리를 지워서 저장해요.',
    '영상 파일은 1GB까지 올릴 수 있어요.',
  ]);
  assert.equal(g.s3.items.length, 3);
  assert.ok(g.s3.items[2].startsWith('선수 이름: 초대할 때 확인한 실명으로 정해져 있어요.'));
  assert.equal(g.s5.items.length, 5);
  assert.equal(
    g.s5.items[2],
    'AI 학습: 공급자 계약에 따라 올린 영상을 Sunity AI 학습에도 써요. 학습용 영상과 데이터는 외부에 공개하거나 넘기지 않아요.',
  );
  assert.equal(g.s5.items[4], '필수 항목(초상·성명 사용, 영상 이용)에 동의하지 않으면 등록할 수 없어요.');
  assert.equal(g.s7.items.length, 4);
  // belle 10-01 — 강사 코드 입력은 quick-260930-o0u 로 나갔다. 옛 '다음 업데이트' 안내 삭제.
  assert.equal(g.s6.items[1], "수강생은 앱 마이 탭 '강사 코드' 칸에 넣어요. 그러면 회원님 수강생으로 연결돼요.");
  assert.ok(!GUIDE_MD.includes('다음 업데이트에서 열려요'));
  for (const it of g.s7.items) {
    assert.ok(!it.startsWith('음악'), it);
    assert.ok(!it.startsWith('여러 동작을 이어 찍기'), it);
  }
});

// ── 15) quick-261002-pa2 — 검토 요청 · 요청 취소 (belle 2026-10-02 결정 1·3·4·6) ──────────

test('pa2 — 검토 중 · 검토 중 패널 · 확인창 · 취소 오류 · 취소됨 · 업로드 토스트 글자 단위', () => {
  const r = supplierCopy.row;
  assert.equal(r.status.checking, '검토 중');
  assert.equal(r.status.cancelled, '요청 취소됨');
  assert.equal(r.pending.title, '검토 중이에요');
  assert.equal(
    r.pending.body,
    '검토는 보통 하루 안에 끝나요. 끝나면 바로 수강생에게 공개되고, 결과는 이 화면에서 볼 수 있어요.',
  );
  assert.equal(r.pending.cancel, '검토 요청 취소');
  assert.equal(r.cancelConfirm.title, '검토 요청을 취소할까요?');
  assert.deepEqual([...r.cancelConfirm.lines], [
    '취소하면 이 동작은 수강생에게 공개되지 않아요.',
    '다시 올리려면 새로 올려야 해요.',
  ]);
  assert.equal(r.cancelConfirm.confirm, '검토 요청 취소');
  assert.equal(r.cancelConfirm.busy, '취소하는 중...');
  assert.equal(r.cancelError.notCancellable, '지금은 취소할 수 없어요. 영상을 처리하는 중이거나 검토가 이미 끝났어요.');
  assert.equal(r.cancelError.notFound, '이 동작을 찾지 못했어요. 목록에서 다시 확인해 주세요.');
  assert.equal(r.cancelled.title, '검토 요청을 취소했어요');
  assert.equal(r.cancelled.body, '다시 올리려면 새로 올려 주세요.');
  assert.equal(supplierCopy.form.uploaded.toast, '검토를 요청했어요. 보통 하루 안에 끝나요.');
  // 확인창 닫기 라벨은 새 키 없이 common.close 를 쓴다.
  assert.equal(supplierCopy.common.close, '닫기');
});

test('pa2 — 취소 오류 문구 = models.py REFERENCE_* 상수와 같은 글자', () => {
  const e = supplierCopy.row.cancelError;
  assert.ok(MODELS_PY.includes(`REFERENCE_NOT_CANCELLABLE_MESSAGE = "${e.notCancellable}"`));
  assert.ok(MODELS_PY.includes(`REFERENCE_CANCEL_NOT_FOUND_MESSAGE = "${e.notFound}"`));
});

test('pa2 — 메일 · 기한 약속 없음 (결정 1 · 6 — 메일 인프라 없음, 실제 하루 안)', () => {
  const r = supplierCopy.row;
  const reviewTexts = [
    r.status.checking,
    r.pending.title,
    r.pending.body,
    ...r.cancelConfirm.lines,
    r.cancelled.title,
    r.cancelled.body,
    supplierCopy.form.uploaded.toast,
  ];
  for (const t of reviewTexts) {
    assert.ok(!t.includes('메일'), t);
    assert.ok(!t.includes('일 이내'), t);
  }
  // 공급자 문구 어디에도 '메일로 알려' 약속이 없다(문의 · 초대 메일 안내는 약속이 아니다).
  for (const [p, s] of ALL_STRINGS) {
    assert.ok(!s.includes('메일로 알려'), `${p}: ${s}`);
    assert.ok(!s.includes('출시하기'), `${p}: ${s}`); // 결정 2 — 승인 = 즉시 공개
  }
});

test('pa2 — 옛 승인 전 문구 · 옛 업로드 토스트가 없다', () => {
  for (const [p, s] of ALL_STRINGS) {
    assert.ok(!s.includes('확인 중 · 끝나면 수강생에게 보여요'), `${p}: ${s}`);
    assert.ok(!s.includes('운영팀 확인이 끝나면 앱에 보여요'), `${p}: ${s}`);
  }
});
