// pickerFailure 매핑 검증 (quick-260720-hn8).
//
// 실행: node --test app/src/lib/pickerFailure.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행된다 — 테스트 러너/트랜스파일러
// 등 **신규 npm 의존성 0** (belle: 1,120개 의존성 이유로 테스트 러너 승인 철회).
// 그래서 node:test / node:assert 표준 모듈만 쓰고 `.ts` 확장자 import 를 명시한다.
//
// 검증 대상은 "안내가 실제로 행동 가능한가" — 해결단계가 비어 있으면 이 작업의
// 목적(사용자가 다음에 뭘 할지 알게 하기)이 무너지므로 전 kind 를 순회해 막는다.

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  describePickFailure,
  type PickFailureKind,
} from './pickerFailure.ts';

const ALL_KINDS: PickFailureKind[] = [
  'permissionCamera',
  'permissionLibrary',
  'format',
  'tooLarge',
  'libraryOpen',
  'cameraOpen',
  'processFailed',
];

test('permissionLibrary: 사진 권한 안내 + 설정 열기 액션', () => {
  const f = describePickFailure('permissionLibrary');
  assert.ok(f.title.includes('사진'), '제목이 사진 권한을 가리켜야 함');
  assert.equal(f.action.kind, 'openSettings');
  assert.ok(f.steps.length >= 2, '해결단계가 2개 이상이어야 함');
});

test('format: mp4 를 언급하고 액션은 dismiss', () => {
  const f = describePickFailure('format');
  assert.ok(
    f.steps.some((s) => s.includes('mp4')),
    '해결단계에 지원 형식(mp4)이 드러나야 함',
  );
  assert.equal(f.action.kind, 'dismiss');
});

test('tooLarge: 용량 한도 100MB 가 문구에 드러남', () => {
  const f = describePickFailure('tooLarge');
  assert.ok(
    f.title.includes('100MB') || f.cause.includes('100MB'),
    '제목이나 원인설명에 100MB 한도가 있어야 함',
  );
});

test('libraryOpen: detail 원문이 가공 없이 그대로 실림', () => {
  const raw = '원본: PHAsset export failed / 변환: timeout';
  const f = describePickFailure('libraryOpen', raw);
  assert.equal(f.detail, raw);
});

test('detail 미전달 시 detail 은 undefined', () => {
  const f = describePickFailure('libraryOpen');
  assert.equal(f.detail, undefined);
});

test('모든 실패 종류가 제목·원인·해결단계를 갖는다', () => {
  for (const kind of ALL_KINDS) {
    const f = describePickFailure(kind);
    assert.equal(f.kind, kind);
    assert.ok(f.title.length > 0, `${kind}: title 이 비어 있음`);
    assert.ok(f.cause.length > 0, `${kind}: cause 가 비어 있음`);
    assert.ok(f.steps.length >= 1, `${kind}: 해결단계가 없음`);
    assert.ok(f.action.label.length > 0, `${kind}: 액션 라벨이 비어 있음`);
  }
});
