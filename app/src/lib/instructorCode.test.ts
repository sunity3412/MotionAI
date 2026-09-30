// instructorCode 순수 규칙 + 마이 탭 강사 코드 문구 잠금 (quick-260930-o0u, 38-DESIGN-v2 §W2).
//
// 실행: node --test app/src/lib/instructorCode.test.ts
// supplierRules.test.ts 와 같은 어법 — Node 24 type stripping, node:test / node:assert 만,
// `.ts` 확장자 import 명시(신규 npm 의존성 0).
//
// 검증 축:
//   1) normalizeInstructorCode / planLookup — 공백 제거 + 대문자, 형식 밖이면 네트워크 없이 invalid.
//   2) classifyCodeDoc — 없음·비활성·active 비-true·supplierUid 없음 → notFound, 그다음 본인 → self.
//   3) normalizeInstructorLink — 던지지 않고 null, linkedAt 은 Timestamp·{seconds} 둘 다 ms 로.
//   4) instructorName — displayName 이 비면 코드를 이름 자리에(플래너 결정 (d)).
//   5) mapFirestoreErrorCode — offline / denied / failed.
//   6) sheetReducer / canSubmit — 입력 → 확인 → 연결 단계 전이표.
//   7) profileCopy.instructorCode — offline 은 supplierCopy 와 같은 문장, 템플릿, 옛 문구 0.

import test from 'node:test';
import assert from 'node:assert/strict';
import { profileCopy } from '../constants/profileCopy.ts';
import { supplierCopy } from '../constants/supplierCopy.ts';
import {
  canSubmit,
  classifyCodeDoc,
  INITIAL_SHEET_STATE,
  instructorName,
  mapFirestoreErrorCode,
  normalizeInstructorCode,
  normalizeInstructorLink,
  planLookup,
  sheetReducer,
  type FoundCode,
  type SheetState,
} from './instructorCode.ts';

test('normalizeInstructorCode — 모든 공백류 제거 + 대문자', () => {
  assert.equal(normalizeInstructorCode('  be lle '), 'BELLE');
  assert.equal(normalizeInstructorCode('\tEun ji\n'), 'EUNJI');
  assert.equal(normalizeInstructorCode(''), '');
});

test('planLookup — 형식 밖이면 invalid(네트워크 0), 맞으면 정규화 코드로 fetch', () => {
  assert.deepEqual(planLookup(''), { kind: 'invalid' });
  assert.deepEqual(planLookup('ab'), { kind: 'invalid' });
  assert.deepEqual(planLookup('BELLE!'), { kind: 'invalid' });
  assert.deepEqual(planLookup('abcdefghi'), { kind: 'invalid' });
  assert.deepEqual(planLookup(' belle '), { kind: 'fetch', code: 'BELLE' });
  assert.deepEqual(planLookup('qz2t'), { kind: 'fetch', code: 'QZ2T' });
});

test('classifyCodeDoc — notFound 조건이 self 보다 먼저', () => {
  assert.deepEqual(classifyCodeDoc(null, 'me'), { kind: 'notFound' });
  assert.deepEqual(classifyCodeDoc({ active: false, supplierUid: 's' }, 'me'), { kind: 'notFound' });
  assert.deepEqual(classifyCodeDoc({ active: 'true', supplierUid: 's' }, 'me'), { kind: 'notFound' });
  assert.deepEqual(classifyCodeDoc({ active: true }, 'me'), { kind: 'notFound' });
  assert.deepEqual(classifyCodeDoc({ active: true, supplierUid: '' }, 'me'), { kind: 'notFound' });
  assert.deepEqual(classifyCodeDoc('x', 'me'), { kind: 'notFound' });
  assert.deepEqual(classifyCodeDoc({ active: true, supplierUid: 'me' }, 'me'), { kind: 'self' });
  assert.deepEqual(classifyCodeDoc({ active: false, supplierUid: 'me' }, 'me'), { kind: 'notFound' });
  assert.deepEqual(
    classifyCodeDoc({ active: true, supplierUid: 's', displayName: '정은지' }, 'me'),
    { kind: 'found', supplierUid: 's', displayName: '정은지' },
  );
  assert.deepEqual(
    classifyCodeDoc({ active: true, supplierUid: 's', displayName: '' }, 'me'),
    { kind: 'found', supplierUid: 's', displayName: null },
  );
  assert.deepEqual(
    classifyCodeDoc({ active: true, supplierUid: 's', displayName: 7 }, 'me'),
    { kind: 'found', supplierUid: 's', displayName: null },
  );
  // authUid 가 아직 없으면(세션 준비 중) self 판정은 하지 않는다 — 최종 판정은 규칙.
  assert.deepEqual(
    classifyCodeDoc({ active: true, supplierUid: 's', displayName: null }, null),
    { kind: 'found', supplierUid: 's', displayName: null },
  );
});

test('normalizeInstructorLink — 던지지 않고 null, linkedAt 두 모양', () => {
  assert.equal(normalizeInstructorLink(null), null);
  assert.equal(normalizeInstructorLink(undefined), null);
  assert.equal(normalizeInstructorLink({ code: 'be', supplierUid: 's' }), null);
  assert.equal(normalizeInstructorLink({ code: 'BELLE', supplierUid: 3 }), null);
  assert.deepEqual(
    normalizeInstructorLink({ code: 'BELLE', supplierUid: 's', displayName: null, linkedAt: { toMillis: () => 5 } }),
    { code: 'BELLE', supplierUid: 's', displayName: null, linkedAtMs: 5 },
  );
  assert.deepEqual(
    normalizeInstructorLink({ code: 'EUNJI', supplierUid: 's', displayName: '정은지', linkedAt: { seconds: 2, nanoseconds: 0 } }),
    { code: 'EUNJI', supplierUid: 's', displayName: '정은지', linkedAtMs: 2000 },
  );
  assert.deepEqual(
    normalizeInstructorLink({ code: 'BELLE', supplierUid: 's' }),
    { code: 'BELLE', supplierUid: 's', displayName: null, linkedAtMs: null },
  );
});

test('instructorName — 비면 코드', () => {
  assert.equal(instructorName('정은지', 'EUNJI'), '정은지');
  assert.equal(instructorName(null, 'BELLE'), 'BELLE');
  assert.equal(instructorName('  ', 'BELLE'), 'BELLE');
});

test('mapFirestoreErrorCode', () => {
  assert.equal(mapFirestoreErrorCode('unavailable'), 'offline');
  assert.equal(mapFirestoreErrorCode('deadline-exceeded'), 'offline');
  assert.equal(mapFirestoreErrorCode('permission-denied'), 'denied');
  assert.equal(mapFirestoreErrorCode('internal'), 'failed');
  assert.equal(mapFirestoreErrorCode(undefined), 'failed');
});

const FOUND: FoundCode = { code: 'BELLE', supplierUid: 's', displayName: null };

function confirmState(): SheetState {
  let s = sheetReducer(INITIAL_SHEET_STATE, { type: 'edit', value: ' belle ' });
  s = sheetReducer(s, { type: 'lookupStart' });
  return sheetReducer(s, { type: 'lookupDone', result: { kind: 'found', ...FOUND } });
}

test('sheetReducer / canSubmit — 입력 단계', () => {
  const edited = sheetReducer(INITIAL_SHEET_STATE, { type: 'edit', value: 'x' });
  assert.equal(edited.step, 'input');
  assert.equal(edited.value, 'x');
  assert.equal(edited.error, null);
  assert.equal(canSubmit(INITIAL_SHEET_STATE), false);
  assert.equal(canSubmit(edited), true);
  assert.equal(canSubmit(sheetReducer(INITIAL_SHEET_STATE, { type: 'edit', value: '   ' })), false);

  const busy = sheetReducer(edited, { type: 'lookupStart' });
  assert.equal(busy.busy, true);
  assert.equal(canSubmit(busy), false);

  const cases = [
    ['notFound', 'notFound'],
    ['self', 'selfCode'],
    ['offline', 'offline'],
    ['failed', 'failed'],
  ] as const;
  for (const [kind, error] of cases) {
    const s = sheetReducer(busy, { type: 'lookupDone', result: { kind } });
    assert.equal(s.step, 'input');
    assert.equal(s.error, error);
    assert.equal(s.busy, false);
    assert.equal(s.value, 'x');
    // 오류 상태에서 고치기 시작하면 오류가 걷힌다.
    assert.equal(sheetReducer(s, { type: 'edit', value: 'xy' }).error, null);
  }
});

test('sheetReducer — 확인 단계와 연결', () => {
  const c = confirmState();
  assert.equal(c.step, 'confirm');
  assert.equal(c.busy, false);
  if (c.step !== 'confirm') throw new Error('confirm 단계가 아니다');
  assert.deepEqual(c.found, FOUND);
  assert.equal(canSubmit(c), false);

  const back = sheetReducer(c, { type: 'cancel' });
  assert.equal(back.step, 'input');
  assert.equal(back.value, ' belle ');
  assert.equal(back.error, null);

  const linking = sheetReducer(c, { type: 'linkStart' });
  assert.equal(linking.step, 'confirm');
  assert.equal(linking.busy, true);
  assert.equal(linking.error, null);

  const off = sheetReducer(linking, { type: 'linkFailed', reason: 'offline' });
  assert.equal(off.step, 'confirm');
  assert.equal(off.error, 'offline');
  assert.equal(off.busy, false);

  const denied = sheetReducer(linking, { type: 'linkDenied' });
  assert.equal(denied.step, 'input');
  assert.equal(denied.error, 'notFound');
  assert.equal(denied.busy, false);

  assert.deepEqual(sheetReducer(linking, { type: 'reset' }), INITIAL_SHEET_STATE);
  // 맞지 않는 단계의 액션은 상태 그대로.
  assert.equal(sheetReducer(INITIAL_SHEET_STATE, { type: 'linkStart' }), INITIAL_SHEET_STATE);
  assert.equal(sheetReducer(c, { type: 'edit', value: 'zz' }), c);
});

function collectStrings(v: unknown, out: string[]): void {
  if (typeof v === 'string') out.push(v);
  else if (typeof v === 'function') out.push(String((v as (a: string, b: string) => unknown)('X', 'Y')));
  else if (v && typeof v === 'object') for (const x of Object.values(v)) collectStrings(x, out);
}

test('profileCopy.instructorCode — 템플릿과 문구 잠금', () => {
  const c = profileCopy.instructorCode;
  assert.equal(c.errors.offline, supplierCopy.common.offline);
  assert.equal(c.toastLinked('정은지'), '정은지 강사님과 연결됐어요');
  assert.equal(c.instructorTitle('BELLE'), 'BELLE 강사님');
  assert.equal(c.codeLine('BELLE'), '코드 BELLE');
  assert.equal(c.alreadyLinked('정은지'), '이미 정은지 강사님과 연결돼 있어요');
  assert.equal(c.hint, '수업에서 받은 코드를 넣으면 강사님과 연결돼요.');
  assert.equal(c.errors.notFound, '없는 코드예요. 강사님께 받은 코드를 다시 확인해 주세요.');
  assert.equal(c.errors.selfCode, '본인 코드는 넣을 수 없어요.');
  assert.equal(c.confirm.notice, '연결은 한 번만 할 수 있어요. 나중에 바꾸려면 cs@sunity.ai 로 알려 주세요.');
  const all: string[] = [];
  collectStrings(profileCopy, all);
  assert.ok(all.length > 10);
  for (const s of all) {
    assert.ok(!s.includes('다음 업데이트'), s);
    assert.ok(!s.includes('미입력'), s);
  }
});
