// normalizePose3d.normalizeFrames PRODUCTION 함수 standalone 검증 (TRUST-04, 19-03).
//
// 왜 LOCAL tsc 컴파일 + createRequire (19-REVIEWS iter-3 HIGH-1):
//   앱은 typescript devDep 만 있고 tsx/ts-node/esbuild 가 없다 (app/package.json).
//   따라서 .mjs 는 .ts 를 직접 import 할 수 없다. 직접 import 하면 런타임 실패,
//   알고리즘을 복제하면 production(joints.ts)이 틀려도 통과하는 false coverage
//   (iter-2 BLOCKER-2 회귀). 그래서 이 스크립트가 컴파일/import 경로를 스스로
//   소유한다: (1) 임시 dir 생성, (2) LOCAL node_modules/typescript/bin/tsc 로
//   normalizePose3d.ts 단독 컴파일, (3) createRequire 로 컴파일된 .js require,
//   (4) production normalizeFrames 존재 단언 후 케이스 실행, (5) finally cleanup.
//   알고리즘 복제 절대 금지 (no-copy grep gate).
//
// 종료 코드 규약 (19-REVIEWS iter-4 MEDIUM-1):
//   Node 의 process.exit() 은 try/finally 의 finally 를 unwind 하지 않아 temp dir
//   cleanup 을 건너뛴다. 따라서 inline process.exit() 절대 금지. assertion 은
//   throw new Error() 로만 실패 신호 → catch 가 exitCode=1 → finally 가 양쪽
//   경로(PASS/FAIL)에서 temp dir 삭제 → finally 이후 process.exitCode 확정.

import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);

// COCO-17 joint 이름 순서 (skeleton.KEYPOINT_NAMES 정합). hip/shoulder 인덱스를
// production 이 jointKeys.indexOf 로 도출하므로 동일 키셋을 넘긴다.
const COCO17_KEYS = [
  'nose',
  'left_eye',
  'right_eye',
  'left_ear',
  'right_ear',
  'left_shoulder',
  'right_shoulder',
  'left_elbow',
  'right_elbow',
  'left_wrist',
  'right_wrist',
  'left_hip',
  'right_hip',
  'left_knee',
  'right_knee',
  'left_ankle',
  'right_ankle',
];

function maxAbsCoord(framesOut) {
  let m = 0;
  for (const frame of framesOut) {
    for (const p of frame) {
      for (const v of p) {
        const a = Math.abs(v);
        if (a > m) m = a;
      }
    }
  }
  return m;
}

function allCoordsFinite(framesOut) {
  for (const frame of framesOut) {
    for (const p of frame) {
      for (const v of p) {
        if (!Number.isFinite(v)) return false;
      }
    }
  }
  return true;
}

// 중심 ~(320,240) 픽셀 스케일의 raw COCO-17 frame (실 RTMW 미정규화 모사).
// 17 keypoint 를 흩뿌리되 hip/shoulder 는 명시 위치를 준다.
function rawFrame(offset) {
  const frame = [];
  for (let j = 0; j < 17; j++) {
    frame.push([320 + offset + j * 4, 240 + offset + j * 3, 100 + j]);
  }
  // 명시 위치 — torso 가 EPSILON 보다 충분히 크도록.
  frame[5] = [310 + offset, 180 + offset, 100]; // left_shoulder
  frame[6] = [330 + offset, 182 + offset, 102]; // right_shoulder
  frame[11] = [314 + offset, 300 + offset, 105]; // left_hip
  frame[12] = [326 + offset, 302 + offset, 107]; // right_hip
  return frame;
}

// hip/shoulder 키가 없는 키셋 — production 이 fallback(centroid+bbox)으로 분기.
const NO_TORSO_KEYS = COCO17_KEYS.map((_, j) => `kp_${j}`);

const __dir = path.dirname(fileURLToPath(import.meta.url));
// cwd = app/ (verify 명령이 cd app). normalizePose3d.ts 절대경로.
const srcTs = path.resolve('src/lib/normalizePose3d.ts');
const tscBin = path.resolve('node_modules/typescript/bin/tsc');

let exitCode = 0;
const tmpDir = mkdtempSync(path.join(tmpdir(), 'sunity-norm-'));

try {
  // (2) LOCAL tsc 로 단독 컴파일 (npx/네트워크 금지). 실패 시 throw.
  execFileSync(
    process.execPath,
    [
      tscBin,
      srcTs,
      '--module',
      'commonjs',
      '--target',
      'ES2020',
      '--outDir',
      tmpDir,
      '--skipLibCheck',
    ],
    { stdio: 'pipe' },
  );

  // (3) 컴파일된 production .js require.
  const mod = require(path.join(tmpDir, 'normalizePose3d.js'));
  if (typeof mod.normalizeFrames !== 'function') {
    throw new Error('normalizeFrames export missing');
  }

  // (4) 케이스 — 모두 production mod.normalizeFrames 호출.

  // Case 1: synthetic raw COCO-17, 다중 frame.
  {
    const input = [rawFrame(0), rawFrame(2), rawFrame(-3)];
    const result = mod.normalizeFrames(input, COCO17_KEYS);
    if (result === null) {
      throw new Error('case1 primary: result null (expected normalized)');
    }
    if (result.length !== input.length) {
      throw new Error(
        `case1 frame count: ${result.length} !== ${input.length}`,
      );
    }
    const mx = maxAbsCoord(result);
    if (!(mx <= 3)) {
      throw new Error(`case1 maxAbsCoord: ${mx} > 3`);
    }
    if (!allCoordsFinite(result)) {
      throw new Error('case1 finite: non-finite coord present');
    }
  }

  // Case 2: fallback (hip/shoulder 키 누락) — frame 수 보존 + maxAbsCoord<=3.
  {
    const input = [rawFrame(0), rawFrame(1)];
    const result = mod.normalizeFrames(input, NO_TORSO_KEYS);
    if (result === null) {
      throw new Error('case2 fallback: result null (expected normalized)');
    }
    if (result.length !== input.length) {
      throw new Error(
        `case2 frame count: ${result.length} !== ${input.length}`,
      );
    }
    const mx = maxAbsCoord(result);
    if (!(mx <= 3)) {
      throw new Error(`case2 maxAbsCoord: ${mx} > 3`);
    }
    if (!allCoordsFinite(result)) {
      throw new Error('case2 finite: non-finite coord present');
    }
  }

  // Case 3: last-resort — 특정 frame 만 비유효 (NaN 으로 채움). drop 0,
  // 비유효 frame 이 prev-valid 복제 또는 zero-skeleton 으로 채워짐 + finite.
  {
    const invalidFrame = [];
    for (let j = 0; j < 17; j++) invalidFrame.push([NaN, NaN, NaN]);
    const input = [rawFrame(0), invalidFrame, rawFrame(2)];
    const result = mod.normalizeFrames(input, COCO17_KEYS);
    if (result === null) {
      throw new Error('case3 last-resort: result null (expected normalized)');
    }
    if (result.length !== input.length) {
      throw new Error(
        `case3 frame count: ${result.length} !== ${input.length}`,
      );
    }
    if (!allCoordsFinite(result)) {
      throw new Error('case3 finite: non-finite coord present (drop/null)');
    }
    const mx = maxAbsCoord(result);
    if (!(mx <= 3)) {
      throw new Error(`case3 maxAbsCoord: ${mx} > 3`);
    }
  }

  // Case 4: whole-null — 모든 frame 비유효 → normalizeFrames null 반환.
  {
    const invalidFrame = [];
    for (let j = 0; j < 17; j++) invalidFrame.push([NaN, NaN, NaN]);
    const input = [invalidFrame, invalidFrame];
    const result = mod.normalizeFrames(input, COCO17_KEYS);
    if (result !== null) {
      throw new Error('case4 whole-null: expected null, got non-null');
    }
  }

  console.log(
    'SMOKE_PASS maxAbsCoord<=3 + frame_count_stable + production_import',
  );
} catch (error) {
  exitCode = 1;
  console.error(error instanceof Error ? error.message : error);
} finally {
  rmSync(tmpDir, { recursive: true, force: true });
}

process.exitCode = exitCode;
