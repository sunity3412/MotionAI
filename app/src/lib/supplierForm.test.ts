// supplierForm 순수 폼 규칙 검증 (Phase 38 리뷰 R14 · D-07 · D-08 · D-14).
//
// 실행: node --test app/src/lib/supplierForm.test.ts
// pickerFailure.test.ts 와 같은 어법 — Node 24 type stripping, node:test / node:assert 만,
// `.ts` 확장자 import 명시(신규 npm 의존성 0). 입력은 전부 supplierFixtures 한 벌.
//
// 검증 축:
//   1) remainingRequired — 필수 8 개수, standingStart 'no' 는 개수와 별개로 blocked.
//   2) validateFile — 형식 → 용량 → 길이 순서, 5/30/60 경계, fail-open(길이 없음·비유한).
//   3) consentAllRequired — 필수 3 만(training 무관, D-08).
//   4) buildRequest — ReferenceUploadUrlRequest 정확한 형상(clipRange 키 없음), 못 보내는 상태는 null.
//   5) parsePrefill / toPrefillParams — '1'|'0' 인코딩 왕복, 쓰레기 값은 null.
//   6) 상수 lockstep — models.py 의 같은 숫자를 텍스트로 대조.

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { supplierFixtures } from './supplierFixtures.ts';
import {
  buildRequest,
  consentAllRequired,
  emptyStep1,
  formatOf,
  MAX_VIDEO_BYTES,
  parsePrefill,
  REFERENCE_COMBO_MAX_DURATION_SEC,
  REFERENCE_MAX_DURATION_SEC,
  REFERENCE_MIN_DURATION_SEC,
  REFERENCE_NAME_MAX_LEN,
  remainingRequired,
  REQUIRED_FIELD_COUNT,
  toPrefillParams,
  validateFile,
} from './supplierForm.ts';

const { step1, consent, files, expectedRequest, prefillParams } = supplierFixtures;

// ── 1) remainingRequired ───────────────────────────────────────────────────

test('빈 STEP 01 은 필수 8개가 남는다, blocked 아님', () => {
  assert.deepEqual(remainingRequired(step1.empty), { count: REQUIRED_FIELD_COUNT, blocked: false });
  assert.equal(REQUIRED_FIELD_COUNT, 8);
  assert.deepEqual(remainingRequired(emptyStep1()), { count: 8, blocked: false });
});

test('전부 찬 STEP 01 은 0, 레벨·파일이 빠지면 2', () => {
  assert.deepEqual(remainingRequired(step1.complete), { count: 0, blocked: false });
  assert.deepEqual(remainingRequired(step1.completeNewName), { count: 0, blocked: false });
  assert.deepEqual(remainingRequired(step1.missingTwo), { count: 2, blocked: false });
});

test("standingStart 'no' 는 개수 0 이어도 blocked (D-09 사전 차단)", () => {
  assert.deepEqual(remainingRequired(step1.standingNo), { count: 0, blocked: true });
});

test('이름은 공백만·30자 초과면 안 찬 것, 선수 이름 공백도 안 찬 것', () => {
  assert.equal(remainingRequired(step1.blankName).count, 1);
  assert.equal(remainingRequired(step1.longName).count, 1);
  assert.equal(remainingRequired(step1.blankAthlete).count, 1);
  assert.equal(REFERENCE_NAME_MAX_LEN, 30);
});

// ── 2) validateFile ────────────────────────────────────────────────────────

test('validateFile — fixture 경계표 전부 (형식 → 용량 → 길이, 콤보 60, fail-open)', () => {
  for (const f of files) {
    assert.equal(validateFile(f), f.expect, `${f.name} ${f.durationSec} combo=${f.isCombo}`);
  }
});

test('validateFile — 길이 경계 4.9/5/30/30.1/60/60.1 을 이름으로 다시 확인', () => {
  const byName = (name: string) => files.find((f) => f.name === name);
  assert.equal(validateFile(byName('a.mp4')!), 'tooShort'); // 4.9
  assert.equal(validateFile(byName('b.mp4')!), null); // 5
  assert.equal(validateFile(byName('c.mov')!), null); // 30
  assert.equal(validateFile(byName('d.mp4')!), 'tooLong'); // 30.1
  assert.equal(validateFile(byName('e.mp4')!), null); // 60 콤보
  assert.equal(validateFile(byName('f.mp4')!), 'tooLong'); // 60.1 콤보
});

test('formatOf — mp4/mov 만, 대소문자 무관, 확장자 없음은 null', () => {
  assert.equal(formatOf('a.mp4'), 'mp4');
  assert.equal(formatOf('B.MOV'), 'mov');
  assert.equal(formatOf('x.avi'), null);
  assert.equal(formatOf('noext'), null);
  assert.equal(formatOf('clip.final.MP4'), 'mp4');
});

// ── 3) consentAllRequired ──────────────────────────────────────────────────

test('consentAllRequired — 필수 3 전부일 때만 true, training 은 무관 (D-08)', () => {
  assert.equal(consentAllRequired(consent.allRequired), true);
  assert.equal(consentAllRequired(consent.allWithTraining), true);
  assert.equal(consentAllRequired(consent.missingSilent), false);
  assert.equal(consentAllRequired(consent.none), false);
});

// ── 4) buildRequest ────────────────────────────────────────────────────────

test('buildRequest — 사전 선택 동작은 techniqueRefId=motionId, 형상이 계약과 정확히 같다', () => {
  const req = buildRequest(step1.complete, consent.allRequired, step1.complete.file);
  assert.deepEqual(req, expectedRequest.fromComplete);
  assert.ok(req && !('clipRange' in req));
});

test('buildRequest — 새 이름은 trim + techniqueRefId null, 콤보 true, durationSec null 허용', () => {
  const req = buildRequest(step1.completeNewName, consent.allWithTraining, step1.completeNewName.file);
  assert.deepEqual(req, expectedRequest.fromCompleteNewName);
});

test('buildRequest — 못 보내는 상태는 null (필수 미완·서 있는 시작 아니오·필수 동의 미완)', () => {
  assert.equal(buildRequest(step1.missingTwo, consent.allRequired, step1.complete.file), null);
  assert.equal(buildRequest(step1.standingNo, consent.allRequired, step1.complete.file), null);
  assert.equal(buildRequest(step1.complete, consent.missingSilent, step1.complete.file), null);
});

// ── 5) parsePrefill / toPrefillParams ──────────────────────────────────────

test('parsePrefill — 실패 행 프리필: 이름·선수·레벨·선언 3 이 STEP 01 로, 체크·파일은 비어 있다', () => {
  const s = parsePrefill(prefillParams.failedRow);
  assert.deepEqual(s.nameChoice, { kind: 'new', name: 'kip-up' });
  assert.equal(s.athleteName, '정은지');
  assert.equal(s.level, 'basic');
  assert.equal(s.isCombo, false);
  assert.equal(s.isSplit, 'yes');
  assert.equal(s.hasHold, 'no');
  assert.equal(s.standingStart, 'yes');
  assert.equal(s.checkConfirmed, false);
  assert.equal(s.file, null);
});

test('parsePrefill — techniqueRefId 가 오면 사전 선택으로, isCombo 1 이면 콤보', () => {
  const s = parsePrefill(prefillParams.withDict);
  assert.deepEqual(s.nameChoice, { kind: 'dict', motionId: 'ref-kip-up', name: 'kip-up' });
  assert.equal(s.level, 'intermediate');
  assert.equal(s.isCombo, true);
  assert.equal(s.isSplit, 'no');
  assert.equal(s.hasHold, 'yes');
});

test('parsePrefill — 쓰레기 값은 null (이름 빈 문자열·레벨 밖·yes/no 밖)', () => {
  const s = parsePrefill(prefillParams.garbage);
  assert.equal(s.nameChoice, null);
  assert.equal(s.athleteName, '');
  assert.equal(s.level, null);
  assert.equal(s.isSplit, null);
  assert.equal(s.hasHold, null);
  assert.equal(s.standingStart, 'yes');
  assert.deepEqual(parsePrefill({}), emptyStep1());
});

test('toPrefillParams → parsePrefill 왕복이 선언·이름·레벨을 보존한다', () => {
  const params = toPrefillParams({
    name: 'kip-up',
    athleteName: '정은지',
    level: 'basic',
    techniqueRefId: 'ref-kip-up',
    isCombo: false,
    isSplit: true,
    hasHold: false,
    standingStart: true,
  });
  assert.deepEqual(params, {
    name: 'kip-up',
    athleteName: '정은지',
    level: 'basic',
    techniqueRefId: 'ref-kip-up',
    isCombo: '0',
    isSplit: '1',
    hasHold: '0',
    standingStart: '1',
  });
  const back = parsePrefill(params);
  assert.deepEqual(back.nameChoice, { kind: 'dict', motionId: 'ref-kip-up', name: 'kip-up' });
  assert.equal(back.isSplit, 'yes');
  assert.equal(back.hasHold, 'no');
  assert.equal(back.standingStart, 'yes');
  assert.equal(back.isCombo, false);
});

// ── 6) 상수 lockstep (models.py) ───────────────────────────────────────────

test('길이·용량·이름 상수가 models.py 와 같은 값이다 (lockstep)', () => {
  assert.equal(REFERENCE_MIN_DURATION_SEC, 5);
  assert.equal(REFERENCE_MAX_DURATION_SEC, 30);
  assert.equal(REFERENCE_COMBO_MAX_DURATION_SEC, 60);
  assert.equal(MAX_VIDEO_BYTES, 100 * 1024 * 1024);
  const models = fs.readFileSync(
    path.join(
      import.meta.dirname,
      '..', '..', '..', 'backend', 'shared', 'python', 'sunity_shared', 'models.py',
    ),
    'utf8',
  );
  assert.ok(models.includes('REFERENCE_MIN_DURATION_SEC = 5.0'));
  assert.ok(models.includes('REFERENCE_MAX_DURATION_SEC = 30.0'));
  assert.ok(models.includes('REFERENCE_COMBO_MAX_DURATION_SEC = 60.0'));
  assert.ok(models.includes(`REFERENCE_NAME_MAX_LEN = ${REFERENCE_NAME_MAX_LEN}`));
  assert.ok(models.includes('MAX_VIDEO_BYTES = 100 * 1024 * 1024'));
});
