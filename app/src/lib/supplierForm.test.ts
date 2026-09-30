// supplierForm 순수 폼 규칙 검증 (Phase 38 리뷰 R14 · D-07 · D-08 · D-14 → quick-260930-w9l).
//
// 실행: node --test app/src/lib/supplierForm.test.ts
// pickerFailure.test.ts 와 같은 어법 — Node 24 type stripping, node:test / node:assert 만,
// `.ts` 확장자 import 명시(신규 npm 의존성 0). 입력은 전부 supplierFixtures 한 벌.
//
// 검증 축 (belle 2026-09-30 폰 확인 뒤 모양):
//   1) remainingRequired — 필수 4 개수(선수 이름은 개수에 없다). supplierNameMissing — 이름 없는
//      공급자는 '다음' 을 막는다(서버 409 supplier_name_missing 과 같은 규칙).
//   2) validateFile — 형식 → 용량 → 길이 순서, 5초 / 120초 / 1GB 경계, fail-open(길이 없음·비유한).
//   3) consentAllRequired — 필수 2(portrait·usage).
//   4) buildRequest — ReferenceUploadUrlRequest 정확한 형상(선수 이름·선언·학습 없음), 못 보내면 null.
//   5) parsePrefill / toPrefillParams — name · level · techniqueRefId 만 왕복, 옛 필드는 무시.
//   6) 상수 lockstep — models.py 의 같은 숫자를 텍스트로 대조, 콤보 상한·100MB export 없음.

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { supplierFixtures } from './supplierFixtures.ts';
import * as form from './supplierForm.ts';
import {
  buildRequest,
  consentAllRequired,
  emptyStep1,
  formatOf,
  parsePrefill,
  REFERENCE_MAX_DURATION_SEC,
  REFERENCE_MAX_VIDEO_BYTES,
  REFERENCE_MIN_DURATION_SEC,
  REFERENCE_NAME_MAX_LEN,
  remainingRequired,
  REQUIRED_FIELD_COUNT,
  supplierNameMissing,
  toPrefillParams,
  validateFile,
} from './supplierForm.ts';

const { step1, consent, files, expectedRequest, prefillParams } = supplierFixtures;

// ── 1) remainingRequired · supplierNameMissing ──────────────────────────────

test('빈 STEP 01 은 필수 4개가 남는다', () => {
  assert.equal(REQUIRED_FIELD_COUNT, 4);
  assert.equal(remainingRequired(step1.empty), REQUIRED_FIELD_COUNT);
  assert.equal(remainingRequired(emptyStep1()), 4);
  assert.deepEqual(Object.keys(emptyStep1()).sort(), ['checkConfirmed', 'file', 'level', 'nameChoice']);
});

test('전부 찬 STEP 01 은 0, 레벨·파일이 빠지면 2', () => {
  assert.equal(remainingRequired(step1.complete), 0);
  assert.equal(remainingRequired(step1.completeNewName), 0);
  assert.equal(remainingRequired(step1.missingTwo), 2);
});

test('이름은 공백만·30자 초과면 안 찬 것', () => {
  assert.equal(remainingRequired(step1.blankName), 1);
  assert.equal(remainingRequired(step1.longName), 1);
  assert.equal(REFERENCE_NAME_MAX_LEN, 30);
});

test('supplierNameMissing — 초대 이름이 null·빈칸이면 막는다, 있으면 통과', () => {
  assert.equal(supplierNameMissing(null), true);
  assert.equal(supplierNameMissing(undefined), true);
  assert.equal(supplierNameMissing(''), true);
  assert.equal(supplierNameMissing('   '), true);
  assert.equal(supplierNameMissing('정은지'), false);
});

// ── 2) validateFile ────────────────────────────────────────────────────────

test('validateFile — fixture 경계표 전부 (형식 → 용량 → 길이, 120초, 1GB, fail-open)', () => {
  for (const f of files) {
    assert.equal(validateFile(f), f.expect, `${f.name} ${f.sizeBytes} ${f.durationSec}`);
  }
});

test('validateFile — 길이 경계 4.9/5/120/120.1 과 용량 경계 1GB/1GB+1 을 이름으로 다시 확인', () => {
  const byName = (name: string) => files.find((f) => f.name === name);
  assert.equal(validateFile(byName('a.mp4')!), 'tooShort'); // 4.9
  assert.equal(validateFile(byName('b.mp4')!), null); // 5
  assert.equal(validateFile(byName('c.mov')!), null); // 120
  assert.equal(validateFile(byName('d.mp4')!), 'tooLong'); // 120.1
  assert.equal(validateFile(byName('e.mp4')!), null); // 1GB
  assert.equal(validateFile(byName('f.mp4')!), 'tooLarge'); // 1GB + 1
  assert.equal(validateFile(byName('j.mp4')!), null); // 101MB — 수강생 한도(100MB)와 다르다
});

test('formatOf — mp4/mov 만, 대소문자 무관, 확장자 없음은 null', () => {
  assert.equal(formatOf('a.mp4'), 'mp4');
  assert.equal(formatOf('B.MOV'), 'mov');
  assert.equal(formatOf('x.avi'), null);
  assert.equal(formatOf('noext'), null);
  assert.equal(formatOf('clip.final.MP4'), 'mp4');
});

// ── 3) consentAllRequired ──────────────────────────────────────────────────

test('consentAllRequired — 필수 2(초상·성명 / 영상 이용) 전부일 때만 true', () => {
  assert.equal(consentAllRequired(consent.allRequired), true);
  assert.equal(consentAllRequired(consent.missingUsage), false);
  assert.equal(consentAllRequired(consent.missingPortrait), false);
  assert.equal(consentAllRequired(consent.none), false);
});

// ── 4) buildRequest ────────────────────────────────────────────────────────

test('buildRequest — 사전 선택 동작은 techniqueRefId=motionId, 형상이 계약과 정확히 같다', () => {
  const req = buildRequest(step1.complete, consent.allRequired, step1.complete.file);
  assert.deepEqual(req, expectedRequest.fromComplete);
  assert.deepEqual(Object.keys(req!).sort(), [
    'consent',
    'durationSec',
    'fileSizeBytes',
    'format',
    'level',
    'name',
    'techniqueRefId',
  ]);
  for (const gone of ['athleteName', 'isCombo', 'isSplit', 'hasHold', 'standingStart', 'clipRange']) {
    assert.ok(!(gone in req!), gone);
  }
  assert.deepEqual(Object.keys(req!.consent).sort(), ['portrait', 'usage']);
});

test('buildRequest — 새 이름은 trim + techniqueRefId null, durationSec null 허용', () => {
  const req = buildRequest(step1.completeNewName, consent.allRequired, step1.completeNewName.file);
  assert.deepEqual(req, expectedRequest.fromCompleteNewName);
});

test('buildRequest — 못 보내는 상태는 null (필수 미완·필수 동의 하나라도 미완)', () => {
  assert.equal(buildRequest(step1.missingTwo, consent.allRequired, step1.complete.file), null);
  assert.equal(buildRequest(step1.complete, consent.missingUsage, step1.complete.file), null);
  assert.equal(buildRequest(step1.complete, consent.missingPortrait, step1.complete.file), null);
});

// ── 5) parsePrefill / toPrefillParams ──────────────────────────────────────

test('parsePrefill — 실패 행 프리필: 이름·레벨이 STEP 01 로, 체크·파일은 비어 있고 옛 필드는 무시', () => {
  const s = parsePrefill(prefillParams.failedRow);
  assert.deepEqual(s, {
    checkConfirmed: false,
    nameChoice: { kind: 'new', name: 'kip-up' },
    level: 'basic',
    file: null,
  });
});

test('parsePrefill — techniqueRefId 가 오면 사전 선택으로, 옛 isCombo 는 무시', () => {
  const s = parsePrefill(prefillParams.withDict);
  assert.deepEqual(s.nameChoice, { kind: 'dict', motionId: 'ref-kip-up', name: 'kip-up' });
  assert.equal(s.level, 'intermediate');
  assert.ok(!('isCombo' in s));
});

test('parsePrefill — 쓰레기 값은 null (이름 빈 문자열·레벨 밖)', () => {
  const s = parsePrefill(prefillParams.garbage);
  assert.equal(s.nameChoice, null);
  assert.equal(s.level, null);
  assert.deepEqual(parsePrefill({}), emptyStep1());
});

test('toPrefillParams → parsePrefill 왕복이 name · level · techniqueRefId 만 나른다', () => {
  const params = toPrefillParams({ name: 'kip-up', level: 'basic', techniqueRefId: 'ref-kip-up' });
  assert.deepEqual(params, { name: 'kip-up', level: 'basic', techniqueRefId: 'ref-kip-up' });
  const back = parsePrefill(params);
  assert.deepEqual(back.nameChoice, { kind: 'dict', motionId: 'ref-kip-up', name: 'kip-up' });
  assert.equal(back.level, 'basic');
  assert.deepEqual(toPrefillParams({ name: 'x', level: 'advanced', techniqueRefId: null }), {
    name: 'x',
    level: 'advanced',
  });
});

// ── 6) 상수 lockstep (models.py) ───────────────────────────────────────────

test('길이·용량·이름 상수가 models.py 와 같은 값이다 (lockstep, belle 09-30: 5초~2분 · 1GB)', () => {
  assert.equal(REFERENCE_MIN_DURATION_SEC, 5);
  assert.equal(REFERENCE_MAX_DURATION_SEC, 120);
  assert.equal(REFERENCE_MAX_VIDEO_BYTES, 1024 ** 3);
  // 콤보 상한(2026-09-30 삭제)과 수강생 100MB 상수는 이 모듈이 더는 내보내지 않는다.
  const exported = Object.keys(form);
  assert.ok(!exported.some((k) => k.includes('COMBO')), exported.join(','));
  assert.ok(!exported.includes('MAX_VIDEO_BYTES'));
  const models = fs.readFileSync(
    path.join(
      import.meta.dirname,
      '..', '..', '..', 'backend', 'shared', 'python', 'sunity_shared', 'models.py',
    ),
    'utf8',
  );
  assert.ok(models.includes('REFERENCE_MIN_DURATION_SEC = 5.0'));
  assert.ok(models.includes('REFERENCE_MAX_DURATION_SEC = 120.0'));
  assert.ok(models.includes('REFERENCE_MAX_VIDEO_BYTES = 1024 * 1024 * 1024'));
  assert.ok(models.includes(`REFERENCE_NAME_MAX_LEN = ${REFERENCE_NAME_MAX_LEN}`));
  assert.ok(!models.includes('COMBO_MAX_DURATION'));
});
