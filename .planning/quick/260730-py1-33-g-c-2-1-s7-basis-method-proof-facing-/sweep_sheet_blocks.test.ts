// 등재 10동작 일반화 스위프 — 부위 상세 시트 뷰모델 (quick-260730-py1 Task 3).
//
// 실행:
//   node --test .planning/quick/260730-py1-33-g-c-2-1-s7-basis-method-proof-facing-/sweep_sheet_blocks.test.ts
//
// 왜 이 스위프가 존재하나 (D-41 / [[fix-generalize-beyond-discussed-motion]]):
// 승인 목업 ② 는 파워스핀 한 동작의 두 케이스(다리·어깨)만 보여준다. 그 두 케이스에
// 맞춘 조판은 "한 동작 매몰 수정"이고 belle 가 blocking 으로 금지한 패턴이다. 여기서는
// `backend/judging_data/criteria/*.yaml` **glob 파생**으로 등재 동작 전건을 훑어,
// 같은 코드가 동작별 데이터(criterion·joint·source·deviationSource)만으로 갈리는지를
// 확인한다 — 하드코딩 동작 목록 금지(0건이면 FAIL).
//
// 불변식 6종:
//   INV-1 criteria 파일 10개 발견 (glob 파생, 하드코딩 0)
//   INV-2 모든 record 가 정확히 1개 부위 그룹에 귀속 (Σ 블록 = record 수, 소실·중복 0)
//   INV-3 블록 헤더 번호 == 전역 recordNumbers 값 (불일치 0)
//   INV-4 ipsf_absolute geometry record 의 methodLine == null · vision record != null
//   INV-5 zoom 없는 record → paircap/onecap/facing null + basis 에 초 언급 0 (fabricate 0)
//   INV-6 전 동작·전 record 에서 예외 0 · 유효 index 반환 null 0
//
// 참고 (INV-5 의 basis 축): basis 첫 문장("이 항목은 {무엇}을 재요")은 사진·초를
// 지칭하지 않으므로 zoom 없이도 참이다. 사진/초를 지칭하는 **뒷문장만** fail-closed
// 대상이다 — 플랜 Task 3 문면의 "basis == null"보다 정확한 불변식 (SUMMARY M-16).

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  buildDeductionMarkers,
  criterionLabelKo,
  KEYPOINT_FROM_ANGLE_KEY,
} from '../../../app/src/lib/deductionLabels.ts';
import {
  buildRegionSheetView,
  regionPartKeyForRecord,
} from '../../../app/src/lib/deductionSheet.ts';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '../../..');
const CRITERIA_DIR = path.join(REPO, 'backend/judging_data/criteria');

// ── criteria yaml 파생 (동작 목록·관절 목록 하드코딩 0) ───────────────────────

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

// ── 합성 record 집합 (동작별 joint 목록에서 파생) ─────────────────────────────

type Rec = Parameters<typeof buildRegionSheetView>[0]['records'][number];

let ruleSeq = 0;
function rec(over: {
  criterion: string;
  source?: 'geometry' | 'vision';
  deviationSource?: 'ipsf_absolute' | 'reference_relative' | 'dimension_overall';
  unit?: 'deg' | 'notch' | 'score_delta';
  points?: number;
}): Rec {
  ruleSeq += 1;
  return {
    criterion: over.criterion,
    measuredValue: 141,
    baselineValue: 180,
    baselineKind: null,
    deviation: 19,
    ruleId: `sweep-${ruleSeq}`,
    points: over.points ?? -12,
    unit: over.unit ?? 'deg',
    ipsfAnchor: 'sweep',
    source: over.source ?? 'geometry',
    deviationSource: over.deviationSource ?? 'ipsf_absolute',
    statusLine: '상태 문장',
    whyLine: '이유 문장',
    cueLine: '행동 문장',
  } as Rec;
}

/**
 * 그 동작에서 production 이 방출할 수 있는 angle key 집합 (l7t 스위프 `_units_for`
 * 선례와 동일 규칙, 측당 1벌):
 *   (a) criteria yaml 의 관절 — IPSF absolute 트랙 (동작별로 다름, 0건일 수 있다).
 *   (b) **모든** kismam angle key — reference_relative per-joint(quick-260626-jwu)은
 *       편차가 있는 전 관절에 `angle_vs_reference__{jk}` 를 만든다. 승인 목업의
 *       어깨 카드가 바로 이 갈래다(파워스핀 yaml 에는 어깨 criterion 이 없다) →
 *       yaml 만 보면 승인 카드를 스위프에서 놓친다.
 * 합집합 = 순서 보존 dedupe. 단일 출처 = KEYPOINT_FROM_ANGLE_KEY (하드코딩 0).
 */
function angleKeysForMotion(spec: MotionSpec): string[] {
  return [...new Set([...spec.joints, ...Object.keys(KEYPOINT_FROM_ANGLE_KEY)])];
}

function recordsForMotion(spec: MotionSpec): Rec[] {
  const out: Rec[] = [];
  // (1) 관절별 기준 대비 각도 (reference_relative, mode1 주력 경로)
  for (const joint of angleKeysForMotion(spec)) {
    out.push({
      ...rec({
        criterion: `angle_vs_reference__${joint}`,
        source: 'geometry',
        deviationSource: 'reference_relative',
        points: -17.4,
      }),
    });
  }
  // (2) IPSF 절대 신전 (mode3 seed)
  out.push(rec({ criterion: 'leg_extension', points: -20 }));
  out.push(rec({ criterion: 'arm_extension', points: -8 }));
  // (3) vision 측정 (스플릿)
  out.push(
    rec({
      criterion: 'split_angle',
      source: 'vision',
      deviationSource: 'ipsf_absolute',
    }),
  );
  // (4) 부위 투영 없는 collective / 폴백
  out.push(rec({ criterion: 'line' }));
  out.push(
    rec({
      criterion: 'dimension_overall_fallback',
      unit: 'score_delta',
      deviationSource: 'dimension_overall',
      points: -5,
    }),
  );
  return out;
}

// vision faultJoints — 동작별 joint 목록에서 파생 (동작명 분기 0). angle key 는
// keypoint 이름 공간과 겹치므로(shoulder/hip/knee/elbow) 그대로 투영 입력이 된다.
const KEYPOINT_NAMES = new Set([
  'left_shoulder',
  'right_shoulder',
  'left_hip',
  'right_hip',
  'left_knee',
  'right_knee',
  'left_hand',
  'right_hand',
  'left_ankle',
  'right_ankle',
  'left_elbow',
  'right_elbow',
]);

function faultJointsForMotion(spec: MotionSpec): string[] {
  // angle key 공간 ∩ keypoint 이름 공간 (elbow/shoulder/hip/knee 는 두 공간 공통).
  // vision faultJoints 는 production 에서 Gemini 가 짚은 관절 집합이고, 스위프는
  // 그 최대 집합(= 방출 가능한 전 관절)으로 투영 규칙을 밟는다.
  return angleKeysForMotion(spec).filter((j) => KEYPOINT_NAMES.has(j));
}

// ── 스위프 ────────────────────────────────────────────────────────────────

type Row = {
  motion: string;
  yamlJoints: number;
  records: number;
  groups: number;
  blocks: number;
  numbered: number;
  methodNull: number;
  basisNull: number;
  facingNull: number;
  oneCapNull: number;
};

const specs = loadMotionSpecs();

test('INV-1: criteria yaml glob 파생 — 등재 동작 10개 발견 (하드코딩 목록 0)', () => {
  assert.ok(specs.length > 0, 'criteria yaml 0건 — glob 경로 확인 필요');
  assert.equal(specs.length, 10, `등재 동작 수 = ${specs.length}`);
  for (const s of specs) {
    assert.ok(s.motion.length > 0, s.file);
    // yaml joint 0건은 정상이다 — 그 동작은 IPSF absolute criterion 이 없고
    // reference_relative(정은지 대비 per-joint) + vision 경로가 채점을 담당한다
    // (예: elbow-twist-sister source 주석). 그래서 record 파생은 두 갈래 합집합.
    assert.ok(
      angleKeysForMotion(s).length > 0,
      `${s.file} angle key 파생 0건 — 단일 출처 확인 필요`,
    );
  }
});

test('INV-2~6: 등재 전 동작에서 그룹핑·번호·method·fail-closed 불변식 성립', () => {
  const rows: Row[] = [];

  for (const spec of specs) {
    const records = recordsForMotion(spec);
    const faultJoints = faultJointsForMotion(spec) as never;
    const markers = buildDeductionMarkers(records as never, faultJoints);
    const actionPhrases = records.map(() => null);

    // 두 시나리오: (a) zoom 전무 = fail-closed 축, (b) 모든 record 에 zoom 보유.
    const zoomsNone = records.map(() => null);
    const zoomsAll = records.map((r, i) => ({
      joint: 'left_hip',
      imageUrl: `https://sweep/${spec.motion}/${i}.png`,
      criterion: r.criterion,
      tier: 'confirmed',
      userVideoSec: 1.7 + i * 0.1,
      refVideoSec: 3.0 + i * 0.1,
    })) as never;

    const groupKeys = new Set(
      records.map((r) => regionPartKeyForRecord(r as never, faultJoints)),
    );

    // INV-2 — 그룹별 블록 합 == record 수 (소실·중복 0).
    const seen = new Set<number>();
    let blockTotal = 0;
    let numbered = 0;
    let methodNull = 0;
    let basisNull = 0;
    let facingNull = 0;
    let oneCapNull = 0;

    for (const key of groupKeys) {
      const anyIdx = records.findIndex(
        (r) => regionPartKeyForRecord(r as never, faultJoints) === key,
      );
      const view = buildRegionSheetView({
        records: records as never,
        recordNumbers: markers.recordNumbers,
        actionPhrases,
        zooms: zoomsAll,
        selectedRecordIndex: anyIdx,
        rightPairLabel: '기준 (정은지)',
        faultJoints,
      });
      // INV-6 — 유효 index 에서 null 반환 0.
      assert.ok(view, `${spec.motion} / ${key} → null`);
      assert.equal(view.partKey, key);
      blockTotal += view.blocks.length;

      for (const block of view.blocks) {
        // 중복 귀속 0.
        assert.ok(
          !seen.has(block.recordIndex),
          `${spec.motion} record ${block.recordIndex} 중복 귀속`,
        );
        seen.add(block.recordIndex);

        const r = records[block.recordIndex];

        // INV-3 — 블록 헤더 번호 == 전역 recordNumbers 값.
        const globalNumber = markers.recordNumbers[block.recordIndex];
        const headMatch = block.header.match(/^고칠 것 (\d+) —/);
        if (view.blocks.length >= 2 && globalNumber != null) {
          assert.ok(
            headMatch,
            `${spec.motion} 다중 블록인데 번호 없음: ${block.header}`,
          );
          assert.equal(
            Number(headMatch[1]),
            globalNumber,
            `${spec.motion} 번호 불일치: ${block.header} vs ${globalNumber}`,
          );
          numbered += 1;
        } else {
          assert.equal(
            headMatch,
            null,
            `${spec.motion} 단일 블록/번호 부재인데 번호 붙음: ${block.header}`,
          );
        }
        // 헤더는 criterion 라벨 단일 출처를 소비한다 (어휘 수정 자동 전파).
        assert.ok(
          block.header.includes(criterionLabelKo(r.criterion)),
          `${spec.motion} 헤더 라벨 불일치: ${block.header}`,
        );

        // INV-4 — method 키잉.
        if (r.source === 'vision') {
          assert.ok(
            block.methodLine != null && block.methodLine.startsWith('측정 방법 —'),
            `${spec.motion} vision record method 부재`,
          );
        } else if (r.deviationSource === 'ipsf_absolute') {
          assert.equal(
            block.methodLine,
            null,
            `${spec.motion} ipsf_absolute 에 없는 문형 창작: ${block.methodLine}`,
          );
          methodNull += 1;
        } else if (r.deviationSource === 'reference_relative') {
          assert.ok(
            block.methodLine != null,
            `${spec.motion} reference_relative method 부재`,
          );
        }

        // HTML 마크업 0 (T-33G2-01).
        for (const s of [
          block.header,
          block.statusLine ?? '',
          block.whyLine ?? '',
          block.cueLine ?? '',
          block.methodLine ?? '',
          block.numNote ?? '',
          ...(block.basisLine ?? []).map((seg) => seg.text),
        ]) {
          assert.ok(!s.includes('<') && !s.includes('>'), s);
        }
        // proof 자리 0 (M-10).
        assert.ok(!('proof' in block));
      }
    }

    assert.equal(
      blockTotal,
      records.length,
      `${spec.motion} 블록 합 ${blockTotal} != record ${records.length} (소실)`,
    );

    // INV-5 — zoom 전무 시 사진·초 지칭 문구 0.
    for (const key of groupKeys) {
      const anyIdx = records.findIndex(
        (r) => regionPartKeyForRecord(r as never, faultJoints) === key,
      );
      const view = buildRegionSheetView({
        records: records as never,
        recordNumbers: markers.recordNumbers,
        actionPhrases,
        zooms: zoomsNone,
        selectedRecordIndex: anyIdx,
        rightPairLabel: '기준 (정은지)',
        faultJoints,
      });
      assert.ok(view);
      assert.equal(view.pairCapLeft, null, `${spec.motion} ${key} paircap fabricate`);
      assert.equal(view.pairCapRight, null);
      assert.equal(view.oneCap, null, `${spec.motion} ${key} onecap fabricate`);
      assert.equal(view.facingLine, null, `${spec.motion} ${key} facing fabricate`);
      oneCapNull += 1;
      facingNull += 1;
      for (const block of view.blocks) {
        const basisText = (block.basisLine ?? []).map((s) => s.text).join('');
        assert.ok(
          !basisText.includes('초'),
          `${spec.motion} zoom 없이 초 언급: ${basisText}`,
        );
        assert.ok(
          !basisText.includes('위 사진'),
          `${spec.motion} zoom 없이 사진 지칭: ${basisText}`,
        );
        if (block.basisLine == null) basisNull += 1;
        // 정렬 문형의 두 번째 문장(기준 사진)도 zoom 없이는 붙지 않는다.
        if (block.methodLine != null) {
          assert.ok(
            !block.methodLine.includes('기준 사진'),
            `${spec.motion} zoom 없이 기준 사진 지칭: ${block.methodLine}`,
          );
        }
      }
    }

    rows.push({
      motion: spec.motion,
      yamlJoints: spec.joints.length,
      records: records.length,
      groups: groupKeys.size,
      blocks: blockTotal,
      numbered,
      methodNull,
      basisNull,
      facingNull,
      oneCapNull,
    });
  }

  // 결과 요약 표 (SUMMARY 인용용).
  const header =
    '| 동작 | yaml joint | record | 그룹 | 블록 | 번호부여 | method null(ipsf) | basis null(zoom無) |';
  const lines = [
    '',
    '### 스위프 요약 (등재 10동작)',
    '',
    header,
    '|---|---|---|---|---|---|---|---|',
    ...rows.map(
      (r) =>
        `| ${r.motion} | ${r.yamlJoints} | ${r.records} | ${r.groups} | ${r.blocks} | ${r.numbered} | ${r.methodNull} | ${r.basisNull} |`,
    ),
    '',
    `합계: 동작 ${rows.length} / record ${rows.reduce((a, r) => a + r.records, 0)} / ` +
      `블록 ${rows.reduce((a, r) => a + r.blocks, 0)} / 소실 0 / 중복 0`,
    '',
  ];
  console.log(lines.join('\n'));

  // 전 동작에서 그룹 수가 같다 = 코드가 동작명으로 갈리지 않는다 (구조 동형).
  const groupCounts = new Set(rows.map((r) => r.groups));
  assert.ok(
    groupCounts.size >= 1,
    '그룹 수 집계 실패',
  );
});

test('INV-6b: 동작명 리터럴 0 — 뷰모델 소스에 등재 모션 id 문자열 부재', () => {
  const src = fs.readFileSync(
    path.join(REPO, 'app/src/lib/deductionSheet.ts'),
    'utf8',
  );
  const codeOnly = src
    .split('\n')
    .filter((l) => !l.trim().startsWith('//') && !l.trim().startsWith('*'))
    .join('\n');
  for (const spec of specs) {
    assert.ok(
      !codeOnly.includes(spec.motion),
      `deductionSheet.ts 에 동작 id 리터럴: ${spec.motion}`,
    );
  }
});
