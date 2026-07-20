// pickerFailure 매핑 검증 (quick-260720-hn8).
//
// 실행: node --test app/src/lib/pickerFailure.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행된다 — 테스트 러너/트랜스파일러
// 등 **신규 npm 의존성 0** (belle: 1,120개 의존성 이유로 테스트 러너 승인 철회).
// 그래서 node:test / node:assert 표준 모듈만 쓰고 `.ts` 확장자 import 를 명시한다.
//
// 검증 축 2개:
//   1) Figma 확정 문구(용량초과·형식)가 **한 글자도 안 바뀌었는가** — 디자인 확정본이라
//      리팩터링 중 조용히 다듬어지는 것을 막는다. 'mp4, mov형식의' 붙임 포함.
//   2) 모든 실패가 행동 가능한 안내를 갖는가 — 본문이 비면 이 작업의 목적이 무너진다.

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

test('tooLarge: Figma 확정 문구 원문 일치', () => {
  const f = describePickFailure('tooLarge');
  assert.equal(f.title, '용량이 너무 커요');
  assert.deepEqual(f.lines, [
    '100MB 이하 영상만 업로드 할 수 있어요.',
    '영상을 잘라서 다시 시도해주세요.',
  ]);
  assert.equal(f.primaryLabel, '다른 파일 선택');
});

test('format: Figma 확정 문구 원문 일치 (mp4, mov형식의 붙임 유지)', () => {
  const f = describePickFailure('format');
  assert.equal(f.title, '지원할 수 없는 파일이에요');
  assert.deepEqual(f.lines, ['mp4, mov형식의 영상만', '업로드 가능해요.']);
  assert.equal(f.primaryLabel, '다른 파일 선택');
});

test('권한 거부 2종: 오른쪽 버튼이 설정 열기', () => {
  for (const kind of ['permissionLibrary', 'permissionCamera'] as const) {
    const f = describePickFailure(kind);
    assert.equal(f.primaryAction, 'openSettings', `${kind}`);
    assert.equal(f.primaryLabel, '설정 열기', `${kind}`);
  }
});

test('cameraOpen: 카메라 기인 실패는 앨범 재오픈하지 않음', () => {
  const f = describePickFailure('cameraOpen');
  assert.equal(f.primaryAction, 'dismiss');
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

test('모든 실패 종류가 제목·2줄 본문·버튼 라벨을 갖는다', () => {
  for (const kind of ALL_KINDS) {
    const f = describePickFailure(kind);
    assert.equal(f.kind, kind);
    assert.ok(f.title.length > 0, `${kind}: title 이 비어 있음`);
    assert.equal(f.lines.length, 2, `${kind}: 본문은 2줄 양식`);
    assert.ok(
      f.lines.every((l) => l.length > 0),
      `${kind}: 빈 본문 줄이 있음`,
    );
    assert.ok(f.primaryLabel.length > 0, `${kind}: 버튼 라벨이 비어 있음`);
  }
});
