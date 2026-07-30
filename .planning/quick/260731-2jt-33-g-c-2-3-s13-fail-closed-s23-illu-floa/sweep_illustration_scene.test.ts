// 등재 10동작 일반화 스위프 — 일러스트 장면일치 판정 (quick-260731-2jt Task 1).
//
// 실행:
//   node --test .planning/quick/260731-2jt-33-g-c-2-3-s13-fail-closed-s23-illu-floa/sweep_illustration_scene.test.ts
//
// 왜 이 스위프가 존재하나 (D-41 / [[fix-generalize-beyond-discussed-motion]]):
// belle 반려 #8·#9·#11 은 파워스핀 한 분석에서 나왔다. 그 한 건만 보고 규칙을 맞추면
// "한 동작 매몰 수정"이고 blocking 안티패턴이다. 여기서는
// `backend/judging_data/criteria/*.yaml` **glob 파생**으로 등재 동작 전건 × 부위 키
// 전 조합을 훑어, **어느 항목에 붙고 어느 항목에 안 붙는지가 동작명 코드 분기 없이
// 데이터만으로 갈리는지** 확인하고 그 표를 JSON 으로 남긴다.
//
// 불변식 6종:
//   INV-1 criteria yaml 10개 발견 (glob 파생, 동작 목록 하드코딩 0) + 판정 모듈·이
//         스위프 소스에 동작명 조건 분기 0
//   INV-2 동작 × 부위 키 전 조합의 부착/미부착 판정 산출 → sweep_illustration_scene.json.
//         부위 키 = (a) 합성 record 에서 `regionPartKeyForRecord` 가 실제로 낸 키
//         (b) 부위 사전 치역의 전 비공집합 조합 (프로브) — 둘 다 하드코딩 목록 아님
//   INV-3 에셋 미보유 동작(= 장면 표에 없는 동작)은 전 부위 미부착. 그 집합이
//         33-14 미완 4동작과 정확히 일치 (검수 게이트를 건너뛴 유입 차단, T-33G4-01)
//   INV-4 부착 전건이 "항목 토큰 ⊆ 장면 토큰"을 만족 (반례 0) — 그리고 그 역도 성립
//         (덮이는데 안 붙는 false-negative 0)
//   INV-5 `criterion:*` 부착 0 · motionId 부재(mode3) 부착 0 (T-33G4-02)
//   INV-6 부착 케이스 ≥ 1 — 전멸이면 배선이 죽은 코드다. **억지 매칭으로 통과시키지
//         말 것**: FAIL 로 두고 SUMMARY 에 사실대로 보고하는 것이 규약이다
//
// 스위프 한계 (정직 기록): 이 스위프는 **판정 규칙**만 훑는다. 그림이 실제로 그
// 부위를 잘 그렸는지(해부학·구도)는 33-14 검수 게이트의 축이고, 시트·영상 위에
// 실제로 렌더되는지는 시뮬 렌더 판정 대상이다 — 둘 다 이 스위프의 축이 아니다.

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  ILLUSTRATION_SCENES,
  hasIllustrationFor,
  illustrationMotionForPart,
} from '../../../app/src/lib/illustrationScene.ts';
import { BODY_PART_OF_KEYPOINT } from '../../../app/src/lib/deductionLabels.ts';
import { regionPartKeyForRecord } from '../../../app/src/lib/deductionSheet.ts';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '../../..');
const CRITERIA_DIR = path.join(REPO, 'backend/judging_data/criteria');
const OUT_JSON = path.join(HERE, 'sweep_illustration_scene.json');
const SCENE_MODULE = path.join(REPO, 'app/src/lib/illustrationScene.ts');

// ── criteria yaml 파생 (동작 목록 하드코딩 0) ─────────────────────────────
// 파싱 방식 = 1·2단위 스위프와 동일 접근 (같은 파일 형식, yaml 의존성 0).

type MotionSpec = { motion: string; joints: string[]; file: string };

function loadMotionSpecs(): MotionSpec[] {
  const files = fs
    .readdirSync(CRITERIA_DIR)
    .filter((f) => f.endsWith('.yaml') || f.endsWith('.yml'))
    .sort();
  return files.map((file) => {
    const text = fs.readFileSync(path.join(CRITERIA_DIR, file), 'utf8');
    const motionMatch = text.match(/^motion:\s*(\S+)\s*$/m);
    const joints = [
      ...new Set(
        [...text.matchAll(/^\s*-\s*joint:\s*(\S+)\s*$/gm)].map((m) => m[1]),
      ),
    ];
    return {
      motion: motionMatch ? motionMatch[1] : file.replace(/\.ya?ml$/, ''),
      joints,
      file,
    };
  });
}

// ── 합성 record (2단위 스위프와 같은 갈래 집합) ───────────────────────────

type Rec = Parameters<typeof regionPartKeyForRecord>[0];

let ruleSeq = 0;
function rec(over: {
  criterion: string;
  source?: 'geometry' | 'vision';
  deviationSource?: 'ipsf_absolute' | 'reference_relative' | 'dimension_overall';
  unit?: 'deg' | 'notch' | 'score_delta';
}): Rec {
  ruleSeq += 1;
  return {
    criterion: over.criterion,
    measuredValue: 141,
    baselineValue: 180,
    baselineKind: null,
    deviation: 19,
    ruleId: `illu-sweep-${ruleSeq}`,
    points: -12,
    unit: over.unit ?? 'deg',
    ipsfAnchor: 'sweep',
    source: over.source ?? 'geometry',
    deviationSource: over.deviationSource ?? 'ipsf_absolute',
    statusLine: null,
    whyLine: null,
    cueLine: null,
  } as Rec;
}

/** 그 동작에서 production 이 방출할 수 있는 angle key 집합 (1·2단위와 동일 규칙). */
function angleKeysForMotion(spec: MotionSpec): string[] {
  return [...new Set([...spec.joints, ...Object.keys(ANGLE_KEY_SEED)])];
}

/** angle key 씨앗 = 부위 사전의 keypoint 이름 (별도 목록 선언 0). */
const ANGLE_KEY_SEED: Record<string, string> = Object.fromEntries(
  Object.keys(BODY_PART_OF_KEYPOINT).map((kp) => [kp, kp]),
);

function recordsForMotion(spec: MotionSpec): Rec[] {
  const out: Rec[] = [];
  for (const joint of angleKeysForMotion(spec)) {
    out.push(
      rec({
        criterion: `angle_vs_reference__${joint}`,
        deviationSource: 'reference_relative',
      }),
    );
  }
  out.push(rec({ criterion: 'leg_extension' }));
  out.push(rec({ criterion: 'arm_extension' }));
  out.push(rec({ criterion: 'split_angle', source: 'vision' }));
  out.push(rec({ criterion: 'line' }));
  out.push(
    rec({
      criterion: 'dimension_overall_fallback',
      unit: 'score_delta',
      deviationSource: 'dimension_overall',
    }),
  );
  return out;
}

// ── 부위 키 후보 ──────────────────────────────────────────────────────────
// (a) 파생 = 위 record 들이 실제로 낳는 키. (b) 프로브 = 부위 사전 치역의 전
// 비공집합 조합. 둘 다 `BODY_PART_OF_KEYPOINT` 파생이라 별도 목록 선언이 없다.
// 조합의 조인 순서 = 사전 선언 순서(shoulder→arm→leg) = production 키 형식과 동일.

const PART_TOKENS: string[] = [...new Set(Object.values(BODY_PART_OF_KEYPOINT))];

function probePartKeys(): string[] {
  const out: string[] = [];
  const n = PART_TOKENS.length;
  for (let mask = 1; mask < 1 << n; mask += 1) {
    const combo = PART_TOKENS.filter((_, i) => (mask >> i) & 1);
    out.push(combo.join('+'));
  }
  return out.sort((a, b) => a.split('+').length - b.split('+').length);
}

// ── 스위프 ────────────────────────────────────────────────────────────────

type Cell = {
  partKey: string;
  origin: 'derived' | 'probe';
  attached: boolean;
  motionIdUsed: string | null;
};

type Row = {
  motion: string;
  file: string;
  yamlJoints: number;
  records: number;
  hasScene: boolean;
  sceneParts: string[];
  derivedPartKeys: string[];
  attachedKeys: string[];
  cells: Cell[];
};

const specs = loadMotionSpecs();

test('INV-1: criteria yaml glob 파생 10동작 + 동작명 조건 분기 0', () => {
  assert.ok(specs.length > 0, 'criteria yaml 0건 — glob 경로 확인 필요');
  assert.equal(specs.length, 10, `등재 동작 수 = ${specs.length}`);
  for (const s of specs) {
    assert.ok(s.motion.length > 0, s.file);
  }

  // 판정 모듈·이 스위프 어디에도 "동작 id 로 갈리는 조건문"이 없어야 한다.
  // (거동은 데이터 맵으로만 갈린다 — Task 1 grep 게이트의 테스트 내 사본.)
  for (const file of [SCENE_MODULE, fileURLToPath(import.meta.url)]) {
    const body = fs
      .readFileSync(file, 'utf8')
      .split('\n')
      .filter((line) => !/^\s*\/\//.test(line))
      .join('\n');
    const branches = body.match(/if\s*\([^)]*'ref-/g) ?? [];
    assert.equal(
      branches.length,
      0,
      `${path.relative(REPO, file)} 에 동작명 조건 분기: ${branches.join(' | ')}`,
    );
  }
});

test('INV-2~6: 등재 전 동작 × 부위 키 전 조합 판정 산출', () => {
  const probes = probePartKeys();
  const rows: Row[] = [];
  let attachedTotal = 0;
  let criterionAttached = 0;
  let mode3Attached = 0;

  for (const spec of specs) {
    const records = recordsForMotion(spec);
    const derived = [
      ...new Set(records.map((r) => regionPartKeyForRecord(r, undefined))),
    ];
    const keys = [...new Set([...derived, ...probes])];
    const scene = Object.prototype.hasOwnProperty.call(
      ILLUSTRATION_SCENES,
      spec.motion,
    )
      ? ILLUSTRATION_SCENES[spec.motion]
      : null;

    const cells: Cell[] = [];
    for (const partKey of keys) {
      const motionIdUsed = illustrationMotionForPart(spec.motion, partKey);
      const attached = motionIdUsed !== null;

      // 두 공개 함수 일치 (규칙 사본 0).
      assert.equal(
        hasIllustrationFor(spec.motion, partKey),
        attached,
        `${spec.motion} × ${partKey} 두 함수 불일치`,
      );

      // ── INV-4 부착 ⇔ 항목 토큰 ⊆ 장면 토큰 (독립 계산) ─────────────────
      const isCriterionKey = partKey.startsWith('criterion:');
      const tokens = isCriterionKey ? [] : partKey.split('+').filter(Boolean);
      const covered =
        scene != null &&
        tokens.length > 0 &&
        tokens.every((t) => scene.parts.includes(t));
      assert.equal(
        attached,
        covered,
        `${spec.motion} × ${partKey} — 부착 판정(${attached})이 부분집합(${covered})과 어긋난다`,
      );
      if (attached) {
        assert.equal(motionIdUsed, spec.motion);
        attachedTotal += 1;
      }

      // ── INV-5 criterion 갈래·mode3 갈래 ────────────────────────────────
      if (isCriterionKey && attached) criterionAttached += 1;
      if (illustrationMotionForPart(null, partKey) !== null) mode3Attached += 1;

      cells.push({ partKey, origin: derived.includes(partKey) ? 'derived' : 'probe', attached, motionIdUsed });
    }

    rows.push({
      motion: spec.motion,
      file: spec.file,
      yamlJoints: spec.joints.length,
      records: records.length,
      hasScene: scene != null,
      sceneParts: scene ? [...scene.parts] : [],
      derivedPartKeys: derived,
      attachedKeys: cells.filter((c) => c.attached).map((c) => c.partKey),
      cells,
    });
  }

  // ── INV-3 에셋 미보유 동작 = 전 부위 미부착 + 33-14 미완 4동작과 일치 ────
  const missing = rows.filter((r) => !r.hasScene).map((r) => r.motion).sort();
  for (const row of rows.filter((r) => !r.hasScene)) {
    assert.equal(
      row.attachedKeys.length,
      0,
      `${row.motion} 은 에셋 미보유인데 부착 ${row.attachedKeys.length}건`,
    );
  }
  assert.deepEqual(
    missing,
    [
      'ref-elbow-twist-sister',
      'ref-pdshape',
      'ref-peter-pan',
      'ref-sideway-spin',
    ],
    '에셋 미보유 집합이 33-14 미완 4동작과 다르다 — 검수 게이트를 건너뛴 유입/이탈',
  );

  // ── INV-5 ────────────────────────────────────────────────────────────────
  assert.equal(criterionAttached, 0, 'criterion 단독 그룹에 그림이 붙었다');
  assert.equal(mode3Attached, 0, 'motionId 부재(mode3)에 그림이 붙었다');

  // ── INV-6 부착 하한 ─────────────────────────────────────────────────────
  assert.ok(
    attachedTotal >= 1,
    '부착 케이스 0건 — 배선이 죽은 코드다 (억지 매칭 금지, 사실대로 보고할 것)',
  );

  // 결과 요약 표 (SUMMARY 인용용).
  const header =
    '| 동작 | yaml joint | 에셋 | 장면 토큰 | 부위 키(파생) | 부착 키 | 미부착 키 |';
  const lines = [
    '',
    '### 스위프 요약 (등재 10동작 × 부위 키 — 일러스트 장면일치)',
    '',
    header,
    '|---|---|---|---|---|---|---|',
    ...rows.map((r) => {
      const notAttached = r.cells
        .filter((c) => !c.attached)
        .map((c) => c.partKey);
      return `| ${r.motion} | ${r.yamlJoints} | ${r.hasScene ? '있음' : '없음'} | ${r.sceneParts.join(',') || '—'} | ${r.derivedPartKeys.join(', ')} | ${r.attachedKeys.join(', ') || '(없음)'} | ${notAttached.length}건 |`;
    }),
    '',
  ];
  console.log(lines.join('\n'));

  fs.writeFileSync(
    OUT_JSON,
    `${JSON.stringify(
      {
        generated_by: 'quick-260731-2jt sweep_illustration_scene.test.ts',
        criteria_dir: path.relative(REPO, CRITERIA_DIR),
        motions: rows.length,
        part_tokens: PART_TOKENS,
        probe_part_keys: probes,
        totals: {
          cells: rows.reduce((a, r) => a + r.cells.length, 0),
          attached: attachedTotal,
          not_attached:
            rows.reduce((a, r) => a + r.cells.length, 0) - attachedTotal,
          motions_with_asset: rows.filter((r) => r.hasScene).length,
          motions_without_asset: missing.length,
          criterion_key_attached: criterionAttached,
          mode3_attached: mode3Attached,
        },
        asset_missing_motions: missing,
        rows,
      },
      null,
      2,
    )}\n`,
    'utf8',
  );

  // 스위프 자체가 무의미해지는 것 방지 — 하한.
  assert.equal(rows.length, 10);
  assert.ok(rows.every((r) => r.cells.length >= probes.length));
  assert.ok(probes.length >= 7, `프로브 조합 ${probes.length}건`);
});
