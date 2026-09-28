// supplierRules 순수 규칙 검증 (Phase 38 리뷰 R14 · R4 · R11 · D-09 · D-10).
//
// 실행: node --test app/src/lib/supplierRules.test.ts
// pickerFailure.test.ts 와 같은 어법 — Node 24 type stripping, node:test / node:assert 만,
// `.ts` 확장자 import 명시(신규 npm 의존성 0). 입력은 전부 supplierFixtures 한 벌 —
// 리터럴 doc 을 여기 다시 쓰지 않는다(38-12 rules.test.mjs 도 같은 fixture).
//
// 검증 축:
//   1) normalizeRegistration — 필수 4(supplierUid·name·athleteName·level) 없으면 null, 있으면
//      공개 doc 필드만 담은 SupplierMotion(registering 기본).
//   2) rowSubtitle — A-3 상태 표 8행(expired 포함) 전부 `{레벨} {상태어}`.
//   3) selfCheckLine / selfCheckNote — R11 판 문구, 반올림, 문턱 경계.
//   4) failCopy / expiredCopy / normalizePrivate — {joints} 치환, too_large, 미지 코드 → server_error.
//   5) hasDetail / sortNewestFirst / mapPresignFailure / uploadOutcomeNext — 두 트랙 공용 전이표.

import test from 'node:test';
import assert from 'node:assert/strict';
import { supplierCopy } from '../constants/supplierCopy.ts';
import { supplierFixtures } from './supplierFixtures.ts';
import {
  expiredCopy,
  failCopy,
  hasDetail,
  LEVEL_LABEL_KO,
  mapPresignFailure,
  normalizePrivate,
  normalizeRegistration,
  presignFailureMessage,
  rowSubtitle,
  SELF_SCORE_OK_MIN,
  selfCheckLine,
  selfCheckNote,
  sortNewestFirst,
  uploadOutcomeNext,
  type SupplierMotion,
} from './supplierRules.ts';

const { rawDocs } = supplierFixtures;

function motion(key: keyof typeof rawDocs): SupplierMotion {
  const m = normalizeRegistration(`r-${key}`, rawDocs[key]);
  assert.ok(m, `fixture ${key} 가 null 로 정규화됐다`);
  return m;
}

// ── 1) normalizeRegistration ───────────────────────────────────────────────

test('필수 4 가 없으면 null — 손 등록 seed(supplierUid 없음)·레벨 밖 doc', () => {
  assert.equal(normalizeRegistration('seed', rawDocs.legacySeed), null);
  assert.equal(normalizeRegistration('bad', rawDocs.badLevel), null);
});

test('공개 doc 8상태가 SupplierMotion 으로 — 상태·점수·키 필드가 그대로, 없는 필드는 null', () => {
  const reg = motion('registering');
  assert.equal(reg.motionId, 'r-registering');
  assert.equal(reg.registrationStatus, 'registering');
  assert.equal(reg.isActive, false);
  assert.equal(reg.selfScore, null);
  assert.equal(reg.selfCheckStatus, null);
  assert.equal(reg.videoS3Key, null);
  assert.equal(reg.uploadExpiresAt, rawDocs.registering.uploadExpiresAt);
  assert.equal(reg.queuedReason, null);

  assert.equal(motion('queued').queuedReason, 'pod_down');
  assert.equal(motion('processing').registrationStatus, 'processing');

  const ok = motion('activeOk');
  assert.equal(ok.isActive, true);
  assert.equal(ok.selfScore, 97);
  assert.equal(ok.selfCheckStatus, 'done');
  assert.equal(ok.videoS3Key, rawDocs.activeOk.videoS3Key);
  assert.equal(ok.uploadExpiresAt, null);

  assert.equal(motion('activePending').selfCheckStatus, 'pending');
  assert.equal(motion('failedLowConfidence').registrationStatus, 'failed');
  assert.equal(motion('expired').registrationStatus, 'expired');
});

test('registrationStatus 가 없거나 미지 값이면 registering 기본', () => {
  const noStatus = { ...rawDocs.registering, registrationStatus: undefined };
  assert.equal(normalizeRegistration('x', noStatus)?.registrationStatus, 'registering');
  const weird = { ...rawDocs.registering, registrationStatus: 'uploading' };
  assert.equal(normalizeRegistration('y', weird)?.registrationStatus, 'registering');
});

// ── 2) rowSubtitle ─────────────────────────────────────────────────────────

test('rowSubtitle — A-3 상태 표 8행 = `{레벨} {상태어}` (expired 포함, R4)', () => {
  const s = supplierCopy.row.status;
  assert.equal(rowSubtitle(motion('registering')), '기본기 올린 영상 확인 중');
  assert.equal(rowSubtitle(motion('queued')), `${LEVEL_LABEL_KO.intermediate} ${s.queued}`);
  assert.equal(rowSubtitle(motion('processing')), `${LEVEL_LABEL_KO.advanced} ${s.processing}`);
  assert.equal(rowSubtitle(motion('activePending')), `${LEVEL_LABEL_KO.intermediate} ${s.newlyAdded}`);
  assert.equal(rowSubtitle(motion('activeSelfQueued')), `${LEVEL_LABEL_KO.advanced} ${s.newlyAdded}`);
  assert.equal(rowSubtitle(motion('activeOk')), '기본기 재현성 97점');
  assert.equal(rowSubtitle(motion('activeLow')), '고급 재현성 61점 · 다시 찍어 주세요');
  assert.equal(rowSubtitle(motion('failedLowConfidence')), `${LEVEL_LABEL_KO.intermediate} ${s.failed}`);
  assert.equal(rowSubtitle(motion('expired')), `${LEVEL_LABEL_KO.basic} ${s.expired}`);
  assert.deepEqual(LEVEL_LABEL_KO, { basic: '기본기', intermediate: '중급', advanced: '고급' });
});

// ── 3) selfCheckLine / selfCheckNote ────────────────────────────────────────

test('selfCheckLine — pending/queued/ok/low/failed 5분기 + 고지', () => {
  const c = supplierCopy.row.self;
  assert.equal(selfCheckLine(motion('activePending')), c.pending);
  assert.equal(selfCheckLine(motion('activeSelfQueued')), c.queued);
  assert.equal(selfCheckLine(motion('activeOk')), '자기 영상 재분석 97점 — 추출·저장이 일관돼요');
  assert.equal(selfCheckLine(motion('activeLow')), '본인 재현성 61점 · 낮아요. 다시 찍어 주세요');
  assert.equal(selfCheckLine(motion('activeSelfFailed')), c.failed);
  assert.equal(selfCheckNote(), c.note);
  assert.ok(!selfCheckLine(motion('activeOk')).includes('{score}'));
});

test('SELF_SCORE_OK_MIN 은 90 하나 — 경계는 반올림한 표시값으로 가른다', () => {
  assert.equal(SELF_SCORE_OK_MIN, 90);
  for (const { selfScore, expect } of supplierFixtures.selfScoreBoundary) {
    const m = normalizeRegistration('b', { ...rawDocs.activeOk, selfScore });
    assert.ok(m);
    const line = selfCheckLine(m);
    const rounded = String(Math.round(selfScore));
    assert.ok(line.includes(`${rounded}점`), `${selfScore} → ${line}`);
    if (expect === 'ok') {
      assert.ok(line.includes('일관돼요'), `${selfScore} 는 ok 여야: ${line}`);
      assert.ok(rowSubtitle(m).endsWith(`재현성 ${rounded}점`));
    } else {
      assert.ok(line.includes('다시 찍어 주세요'), `${selfScore} 는 low 여야: ${line}`);
      assert.ok(rowSubtitle(m).endsWith('다시 찍어 주세요'));
    }
  }
});

// ── 4) failCopy / expiredCopy / normalizePrivate ────────────────────────────

test('failCopy — low_confidence 는 {joints} 를 " · " 로 이어 치환, too_large 존재', () => {
  const low = failCopy('low_confidence', supplierFixtures.lowConfidenceJoints);
  assert.equal(low.title, '일부 관절을 못 읽었어요');
  assert.ok(low.body.includes('왼쪽 발목 · 오른쪽 발목'));
  assert.ok(!low.body.includes('{joints}'));

  const large = failCopy('too_large');
  assert.equal(large.title, supplierCopy.row.fail.too_large.title);
  assert.equal(large.body, supplierCopy.row.fail.too_large.body);

  const noHuman = failCopy('no_human');
  assert.equal(noHuman.title, supplierCopy.row.fail.no_human.title);
});

test('failCopy — 미지 코드는 server_error 문구, expiredCopy 는 row.expired', () => {
  for (const code of supplierFixtures.unknownErrorCodes) {
    assert.deepEqual(failCopy(code), {
      title: supplierCopy.row.fail.server_error.title,
      body: supplierCopy.row.fail.server_error.body,
    });
  }
  assert.deepEqual(expiredCopy(), {
    title: supplierCopy.row.expired.title,
    body: supplierCopy.row.expired.body,
  });
});

test('normalizePrivate — 실패 상세·선언 3·techniqueRefId 는 비공개 doc 에서만 (R13)', () => {
  const failed = normalizePrivate(supplierFixtures.privateDocs.failedLowConfidence);
  assert.ok(failed);
  assert.equal(failed.registrationError?.code, 'low_confidence');
  assert.deepEqual(failed.registrationError?.joints, ['왼쪽 발목', '오른쪽 발목']);
  assert.equal(failed.techniqueRefId, null);
  assert.equal(failed.isSplit, true);
  assert.equal(failed.hasHold, false);
  assert.equal(failed.standingStart, true);
  assert.equal(failed.isCombo, false);

  const ok = normalizePrivate(supplierFixtures.privateDocs.activeOk);
  assert.ok(ok);
  assert.equal(ok.registrationError, null);
  assert.equal(ok.techniqueRefId, 'ref-kip-up');
  assert.equal(ok.hasHold, true);

  const unknown = normalizePrivate(supplierFixtures.privateDocs.unknownCode);
  assert.equal(unknown?.registrationError?.code, 'server_error');
  assert.equal(unknown?.registrationError?.message, '등록 중 문제가 생겼어요.');

  assert.equal(normalizePrivate(null), null);
  assert.equal(normalizePrivate(undefined), null);
  assert.equal(normalizePrivate('x'), null);
});

// ── 5) hasDetail / sortNewestFirst / mapPresignFailure / uploadOutcomeNext ──

test('hasDetail — active/failed/expired 만 상세 패널(chevron)', () => {
  assert.equal(hasDetail(motion('activePending')), true);
  assert.equal(hasDetail(motion('activeOk')), true);
  assert.equal(hasDetail(motion('failedLowConfidence')), true);
  assert.equal(hasDetail(motion('expired')), true);
  assert.equal(hasDetail(motion('registering')), false);
  assert.equal(hasDetail(motion('queued')), false);
  assert.equal(hasDetail(motion('processing')), false);
});

test('sortNewestFirst — createdAt 내림차순, 입력 배열은 그대로', () => {
  const keys = ['expired', 'activeOk', 'registering', 'failedLowConfidence', 'queued'] as const;
  const input = keys.map((k) => motion(k));
  const before = input.map((m) => m.motionId);
  const sorted = sortNewestFirst(input);
  assert.deepEqual(
    sorted.map((m) => m.motionId),
    ['r-registering', 'r-queued', 'r-activeOk', 'r-failedLowConfidence', 'r-expired'],
  );
  assert.deepEqual(input.map((m) => m.motionId), before);
  assert.notEqual(sorted, input);
});

test('mapPresignFailure — 401 sessionExpired · 403 forbidden · 0 offline(unauthenticated 는 sessionExpired) · 그 외 presignFail', () => {
  for (const f of supplierFixtures.apiFailures) {
    assert.equal(mapPresignFailure(f), f.expect, `${f.status}/${f.code}`);
  }
});

test('presignFailureMessage — 분기별 문구 단일점, forbidden 은 문구 없이 A-2 로', () => {
  assert.equal(presignFailureMessage('sessionExpired'), supplierCopy.form.sessionExpired);
  assert.equal(presignFailureMessage('offline'), supplierCopy.common.offline);
  assert.equal(presignFailureMessage('presignFail'), supplierCopy.form.presignFail);
  assert.equal(presignFailureMessage('forbidden'), null);
});

test('uploadOutcomeNext — ok→home · aborted→step2(입력 유지) · failed→failPanel', () => {
  for (const o of supplierFixtures.uploadOutcomes) {
    assert.equal(uploadOutcomeNext(o.outcome), o.next);
  }
});
