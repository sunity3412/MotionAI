// unjudgedJoints 정규화 검증 (quick-260910-sus).
//
// 실행: cd app && node --test src/lib/__tests__/unjudgedJoints.test.ts
//
// ★ 왜 순수 헬퍼가 아니라 normalize() 를 통째로 통과시키는가
// userAnalyses.ts 의 normalize() 는 **덮어쓰기(overlay)** 다: `let result = raw.result`
// 로 raw 키를 전부 물고 시작해 `{...result, ...}` 로 아는 필드만 덮는다. 즉 목록에 없는
// 필드는 버려지는 게 아니라 **검증 없이 raw 그대로 통과**한다. 헬퍼만 따로 테스트하면
// 이 통과 경로가 안 잡히므로, 모든 축이 normalize() 를 거친다.
//
// (이 파일이 태어난 계기는 "unjudgedJoints 가 정규화에서 버려진다" 는 진단이었는데,
//  실측 결과 그건 **사실이 아니었다** — 정상 배열은 이 줄 없이도 통과한다. 남는 실제
//  구멍은 malformed 값이 무검증으로 새는 쪽이고, 축4~6 이 그것을 고정한다.)
//
// ★ 왜 registerHooks 하네스가 필요한가
// userAnalyses.ts 는 화면 훅과 한 파일에 있어 './firebase' 를 import 하고, 그 모듈은
// import 시점에 initializeApp + async-storage(RN 전용)를 건드려 plain node 에서 죽는다.
// firebase/firestore·firebase/auth·react 는 node 에서 그대로 import 되므로, 우리 소유
// 모듈인 './firebase' **하나만** 스텁하고 확장자 없는 상대 import 를 .ts 로 이어준다.
// resolve 훅은 parentURL 이 app/src 아래일 때만 개입한다 (node_modules 의 CJS 해석을
// 건드리면 @grpc 가 깨진다). 훅은 app 코드에 영향이 없다 — node --test 는 파일마다
// 별도 프로세스다.

import test from 'node:test';
import assert from 'node:assert/strict';
import { registerHooks } from 'node:module';

const FIREBASE_STUB =
  'export const app={};export const auth={currentUser:null};export const db={};' +
  'export const firebaseConfigured=false;';

registerHooks({
  resolve(spec, ctx, next) {
    const parent = ctx?.parentURL ?? '';
    if (!parent.includes('/app/src/')) return next(spec, ctx);
    if (spec === './firebase')
      return { url: 'stub:firebase', shortCircuit: true };
    if (/^\.{1,2}\//.test(spec) && !/\.[a-z]+$/.test(spec))
      return next(spec + '.ts', ctx);
    return next(spec, ctx);
  },
  load(url, ctx, next) {
    if (url === 'stub:firebase')
      return { format: 'module', source: FIREBASE_STUB, shortCircuit: true };
    return next(url, ctx);
  },
});

const { normalize } = await import('../userAnalyses.ts');

// normalize() 가 null 을 뱉지 않는 최소 doc. mode/status/fileName/createdAt 이 전부
// 있어야 통과한다 (fileName 은 빈 문자열도 유효).
function docWith(resultPatch: Record<string, unknown>): Record<string, unknown> {
  return {
    mode: 'mode1',
    status: 'done',
    fileName: 'take-01.mp4',
    createdAt: 1757400000000,
    updatedAt: 1757400000000,
    result: { overallScore: 72, ...resultPatch },
  };
}

function unjudgedOf(raw: Record<string, unknown>) {
  return normalize('a1', raw)?.result?.unjudgedJoints;
}

test('축1 정상 배열 → 원소가 그대로 보존되고 length 가 유지된다', () => {
  const out = unjudgedOf(
    docWith({
      unjudgedJoints: [
        { joint: 'right_elbow', reason: 'collapse' },
        { joint: 'left_knee', reason: 'collapse' },
      ],
    }),
  );
  assert.deepEqual(out, [
    { joint: 'right_elbow', reason: 'collapse' },
    { joint: 'left_knee', reason: 'collapse' },
  ]);
});

test('축2 빈 배열 → 빈 배열 (undefined 로 접으면 안 된다)', () => {
  // "봤는데 붕괴 0" 과 "안 봤다" 는 다른 사실이다. 정규화가 둘을 뭉개면 나중에
  // 그 구분으로 분기하는 소비처가 생겼을 때 조용히 틀린다 (analysis.ts 주석 정본).
  const out = unjudgedOf(docWith({ unjudgedJoints: [] }));
  assert.ok(Array.isArray(out), '빈 배열이 배열로 남아야 한다');
  assert.equal(out?.length, 0);
});

test('축3 부재 → undefined (legacy doc / 판정기 미산출 경로)', () => {
  assert.equal(unjudgedOf(docWith({})), undefined);
});

test('축4 배열이 아니면 undefined (객체·문자열·number·null)', () => {
  for (const bad of [{ joint: 'right_elbow' }, 'right_elbow', 3, null]) {
    assert.equal(
      unjudgedOf(docWith({ unjudgedJoints: bad })),
      undefined,
      `배열 아님(${JSON.stringify(bad)})은 undefined 여야 한다`,
    );
  }
});

test('축5 malformed 원소 → 그 원소만 제외하고 나머지는 보존', () => {
  const out = unjudgedOf(
    docWith({
      unjudgedJoints: [
        { joint: 'right_elbow', reason: 'collapse' }, // 정상
        { joint: 42, reason: 'collapse' }, // joint 가 숫자
        { joint: '', reason: 'collapse' }, // joint 가 빈 문자열
        { joint: 'left_knee', reason: 'occluded' }, // reason 미허용값
        { joint: 'left_hip' }, // reason 부재
        'left_ankle', // 객체가 아님
        null,
        { joint: 'right_knee', reason: 'collapse' }, // 정상
      ],
    }),
  );
  assert.deepEqual(out, [
    { joint: 'right_elbow', reason: 'collapse' },
    { joint: 'right_knee', reason: 'collapse' },
  ]);
});

test('축6 전원 malformed → 빈 배열 (undefined 아님)', () => {
  // 백엔드가 배열을 보냈다는 사실 자체는 "봤다" 는 뜻이다. 원소가 다 깨졌다고
  // "안 봤다"(=부재)로 승격시키지 않는다.
  const out = unjudgedOf(
    docWith({ unjudgedJoints: [{ joint: 42 }, 'x', null, {}] }),
  );
  assert.ok(Array.isArray(out));
  assert.equal(out?.length, 0);
});

test('축7 정규화 경유 통합 — 실물 doc 모양에서 소비처가 세는 수가 맞는다', () => {
  // 검증본 doc(users/qdeLN9Ur1yMFb9duNT2ep3g4pmT2/analyses/c64afae69fd24366b4b5f375aa0a91fb)
  // 에 가까운 형상. 이웃 필드(joints·attributionReliability)를 같이 실어, 이 추가가
  // 같은 overlay 블록의 다른 필드를 깨지 않는지도 함께 본다.
  //
  // 정상 1개 + 미허용 reason 1개를 섞는다. 정규화가 없으면 소비처의 `?.length ?? 0`
  // 이 2 를 세어 "2곳을 못 봤어요" 라고 말한다 — 없는 관절을 세어 말하는 쪽이
  // 이 층의 실제 위험이다 (필드가 사라지는 게 아니라).
  const doc = normalize(
    'c64afae69fd24366b4b5f375aa0a91fb',
    docWith({
      unjudgedJoints: [
        { joint: 'right_elbow', reason: 'collapse' },
        { joint: 'left_knee', reason: 'occluded' },
      ],
      joints: [
        { key: 'right_elbow', score: 61 },
        { key: 'left_elbow', score: 88 },
        { key: 'right_knee', score: 74 },
      ],
      attributionReliability: {
        unreliable: false,
        geminiSilent: false,
        overTolJointCount: 2,
        visibility: 0.91,
        dtwDistance: 12.5,
      },
    }),
  );

  // result.tsx:856-857 의 소비 표현과 같은 계산.
  const hidden = doc?.result?.unjudgedJoints?.length ?? 0;
  const total = doc?.result?.joints?.length ?? 0;
  assert.equal(hidden, 1, '미허용 reason 이 세어지면 안 된다');
  assert.equal(total, 3);
  assert.deepEqual(doc?.result?.unjudgedJoints, [
    { joint: 'right_elbow', reason: 'collapse' },
  ]);
  // 같은 overlay 블록의 이웃 필드가 이 추가로 깨지지 않았는지 (회귀 가드).
  assert.equal(doc?.result?.attributionReliability?.unreliable, false);
  assert.equal(doc?.result?.attributionReliability?.overTolJointCount, 2);
});
