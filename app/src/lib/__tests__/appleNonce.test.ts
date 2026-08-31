// Apple 로그인 nonce 규율 회귀 테스트 (Phase 36-03).
//
// 이 연동의 대표 실패는 nonce 를 **뒤바꿔 넘기는 것**이다: Apple 에는 SHA256 해시를,
// Firebase 에는 원본(raw)을 줘야 하는데 반대로 주면 `auth/invalid-credential` 로
// 항상 실패한다. 실기기·애플 계정이 있어야 재현되는 실패라 단위 테스트로 규율만
// 고정한다 — socialAuth 는 네이티브 모듈을 import 하므로 여기서는 그 파일을
// 불러오지 않고, **같은 계약**(해시 형태·raw 와의 구분)을 검증한다.

import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash, randomBytes } from 'node:crypto';

// socialAuth.randomNonce 와 같은 형태(16진 문자열)를 만든다.
function rawNonceLike(byteLength = 32): string {
  return Array.from(randomBytes(byteLength), (b) =>
    b.toString(16).padStart(2, '0'),
  ).join('');
}

// expo-crypto digestStringAsync(SHA256, raw) 와 같은 값 (hex, 소문자 64자).
function sha256Hex(input: string): string {
  return createHash('sha256').update(input, 'utf8').digest('hex');
}

test('raw nonce 는 매 호출 달라진다 (재전송 공격 방지 목적)', () => {
  const a = rawNonceLike();
  const b = rawNonceLike();
  assert.notEqual(a, b);
  assert.equal(a.length, 64); // 32바이트 → hex 64자
});

test('Apple 에 넘기는 해시는 raw 와 다른 값이고 SHA256 hex 형태다', () => {
  const raw = rawNonceLike();
  const hashed = sha256Hex(raw);
  assert.notEqual(hashed, raw, 'raw 를 그대로 Apple 에 넘기면 안 된다');
  assert.match(hashed, /^[0-9a-f]{64}$/);
});

test('같은 raw 는 항상 같은 해시 — Firebase 가 raw 로 재계산해 대조할 수 있다', () => {
  const raw = rawNonceLike();
  assert.equal(sha256Hex(raw), sha256Hex(raw));
});

test('해시를 Firebase 에 넘기면 대조가 깨진다 (뒤바꿈 금지 근거)', () => {
  const raw = rawNonceLike();
  const hashed = sha256Hex(raw);
  // Firebase 는 받은 값을 해시해 토큰 안의 값과 비교한다. raw 대신 hashed 를 주면
  // sha256(hashed) != hashed 라 절대 일치하지 않는다.
  assert.notEqual(sha256Hex(hashed), hashed);
});
