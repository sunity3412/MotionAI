// 등재 10동작 일반화 스위프 — 부위 그룹 마커 · 부위 칩 · 강조 선/원 (quick-260730-szk Task 3).
//
// 실행:
//   node --test .planning/quick/260730-szk-33-g-c-2-2-s19-pulse-s1-s3-f-8/sweep_markers_focus.test.ts
//
// 왜 이 스위프가 존재하나 (D-41 / [[fix-generalize-beyond-discussed-motion]]):
// 승인 목업 ①·④ 는 파워스핀 한 동작의 컷만 보여준다. 그 컷에 맞춘 마커·칩·강조는
// "한 동작 매몰 수정"이고 belle 가 blocking 으로 금지한 패턴이다. 여기서는
// `backend/judging_data/criteria/*.yaml` **glob 파생**으로 등재 동작 전건을 훑어,
// 같은 코드가 동작별 데이터(criterion · jointKeys · source · deviationSource)만으로
// 갈리는지 확인한다 — 하드코딩 동작 목록 금지(0건이면 FAIL).
//
// 불변식 7종:
//   INV-1 criteria yaml 10개 발견 (glob 파생, 동작명 하드코딩 0)
//   INV-2 표시 수 == 항목 수 == 시트 수 — `partGroups` 수 == 감점 칩 수, 각 칩이
//         자기 부위 시트를 연다(partKey·title 문자 일치). 마커 없는 부위(투영 공집합
//         criterion)는 칩도 없고 시트만 남는다 = 의도된 차집합
//   INV-3 모든 감점 record 의 투영 keypoint 가 **자기 부위 그룹 정확히 하나**에 전부
//         들어간다 (record 쪼개짐·번호 중복·고아 0)
//   INV-3b keypoint 경계 중첩은 **복합 부위 ↔ 그 토큰 부위** 사이에서만 발생한다
//         (임의 부위 사이 중첩 = FAIL). 실측 = 동작당 2건, 전건 `shoulder+arm` ↔
//         `shoulder` — 근본원인·판정 위임은 SUMMARY N-19
//   INV-4 `badgeLabel` == 그 부위 멤버 번호 오름차순 조인
//   INV-5 `buildFocusShapes` 결과에 좌·우 관절이 함께 든 체인·원 0 (몸통 가로지르기 불가)
//   INV-6 전 관절 conf 0.9 → 체인 또는 원 ≥ 1 / 전 관절 conf 0.1 → 체인 0 · 원 0
//   INV-7 참고 칩 갈래 — 감점이 다리뿐인 최소 시나리오에서 손 attention → `참고: 팔` 1개
//
// 스위프 한계 (정직 기록): 좌표는 넣지 않는다 — `buildFocusShapes` 는 어느 관절을
// 어떤 형태로 그릴지만 정하고 좌표 환산은 오버레이 책임이다. 선이 실제 사지 위에
// 앉는지(해부학적 정합)는 시뮬 렌더 판정 대상이며 이 스위프의 축이 아니다.

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  buildDeductionMarkers,
  projectDeductionRecordKeypoints,
  KEYPOINT_FROM_ANGLE_KEY,
} from '../../../app/src/lib/deductionLabels.ts';
import {
  buildPartChips,
  buildPartGroups,
  buildRegionSheetView,
  partLabelKo,
  regionPartKeyForRecord,
} from '../../../app/src/lib/deductionSheet.ts';
import { buildFocusShapes } from '../../../app/src/lib/focusShape.ts';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '../../..');
const CRITERIA_DIR = path.join(REPO, 'backend/judging_data/criteria');
const OUT_JSON = path.join(HERE, 'sweep_markers_focus.json');

// ── criteria yaml 파생 (동작 목록·관절 목록 하드코딩 0) ───────────────────────
// 파싱 방식 = 1단위 `sweep_sheet_blocks.test.ts` 와 동일 (같은 파일 형식, 사본 아닌
// 동일 접근 — yaml 의존성 0).

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

type Rec = Parameters<typeof buildPartGroups>[0][number];

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
 * 그 동작에서 production 이 방출할 수 있는 angle key 집합 (1단위 스위프와 동일 규칙):
 *   (a) criteria yaml 의 관절 — IPSF absolute 트랙 (동작별로 다르고 0건일 수 있다)
 *   (b) 전 kismam angle key — reference_relative per-joint(quick-260626-jwu)은 편차가
 *       있는 전 관절에 `angle_vs_reference__{jk}` 를 만든다. 승인 목업의 어깨 카드가
 *       이 갈래다(파워스핀 yaml 에는 어깨 criterion 이 없다).
 * 단일 출처 = KEYPOINT_FROM_ANGLE_KEY (하드코딩 0).
 */
function angleKeysForMotion(spec: MotionSpec): string[] {
  return [...new Set([...spec.joints, ...Object.keys(KEYPOINT_FROM_ANGLE_KEY)])];
}

function recordsForMotion(spec: MotionSpec): Rec[] {
  const out: Rec[] = [];
  // (1) 관절별 기준 대비 각도 (reference_relative, mode1 주력 경로)
  for (const joint of angleKeysForMotion(spec)) {
    out.push(
      rec({
        criterion: `angle_vs_reference__${joint}`,
        source: 'geometry',
        deviationSource: 'reference_relative',
        points: -17.4,
      }),
    );
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
  // (4) 부위 투영 없는 collective / 폴백 — 마커·칩 없이 시트만 남는 갈래
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
  return angleKeysForMotion(spec).filter((j) => KEYPOINT_NAMES.has(j));
}

// ── 스위프 ────────────────────────────────────────────────────────────────

type Row = {
  motion: string;
  yamlJoints: number;
  records: number;
  partGroups: number;
  chipsDeduction: number;
  chipsAdvisory: number;
  advisoryBranchChips: number;
  sheets: number;
  mergedBadges: number;
  focusChains: number;
  focusCircles: number;
  crossSideChains: number;
  nestedOverlaps: number;
};

const specs = loadMotionSpecs();

test('INV-1: criteria yaml glob 파생 — 등재 동작 10개 발견 (하드코딩 목록 0)', () => {
  assert.ok(specs.length > 0, 'criteria yaml 0건 — glob 경로 확인 필요');
  assert.equal(specs.length, 10, `등재 동작 수 = ${specs.length}`);
  for (const s of specs) {
    assert.ok(s.motion.length > 0, s.file);
    assert.ok(
      angleKeysForMotion(s).length > 0,
      `${s.file} angle key 파생 0건 — 단일 출처 확인 필요`,
    );
  }
});

test('INV-2~7: 등재 전 동작에서 그룹·칩·시트·강조 형태 불변식 성립', () => {
  const rows: Row[] = [];

  for (const spec of specs) {
    const records = recordsForMotion(spec);
    const faultJoints = faultJointsForMotion(spec) as never;
    const markers = buildDeductionMarkers(records as never, faultJoints);
    const groups = buildPartGroups(records, markers.recordNumbers, faultJoints);
    const chips = buildPartChips({
      records,
      recordNumbers: markers.recordNumbers,
      faultJoints,
      // 참고 칩 — 감점 부위와 겹치지 않는 관절만 남게 전 keypoint 를 넣어본다
      // (production 은 windowMedianAngleDeltas 파생. 여기선 최대 집합으로 규칙만 밟음).
      attentionKeypoints: [...KEYPOINT_NAMES] as never,
      estimatedArea: false,
    });
    const deductionChips = chips.filter((c) => c.kind === 'deduction');
    const advisoryChips = chips.filter((c) => c.kind === 'advisory');

    // ── INV-2 표시 수 == 항목 수 == 시트 수 ────────────────────────────────
    assert.equal(
      groups.length,
      deductionChips.length,
      `${spec.motion} 그룹 ${groups.length} != 감점 칩 ${deductionChips.length}`,
    );
    assert.deepEqual(
      groups.map((g) => g.partKey),
      deductionChips.map((c) => c.partKey),
      `${spec.motion} 그룹·칩 부위 순서 불일치`,
    );
    for (const chip of deductionChips) {
      assert.ok(
        chip.firstRecordIndex != null,
        `${spec.motion} ${chip.partKey} 칩 진입점 없음 (탭 불가 칩 금지)`,
      );
      const view = buildRegionSheetView({
        records,
        recordNumbers: markers.recordNumbers,
        actionPhrases: records.map(() => null),
        zooms: records.map(() => null),
        selectedRecordIndex: chip.firstRecordIndex,
        rightPairLabel: '기준 (정은지)',
        faultJoints,
      });
      assert.ok(view, `${spec.motion} ${chip.partKey} 칩 → 시트 null`);
      assert.equal(
        view.partKey,
        chip.partKey,
        `${spec.motion} 칩이 다른 부위 시트를 연다`,
      );
      // 칩 라벨 == 시트 제목 (문자 동일 — 어휘 갈라짐 0).
      assert.equal(chip.label, partLabelKo(chip.partKey));
      assert.equal(view.title, chip.label);
    }
    // 마커 없는 부위 = 투영 공집합 criterion 뿐 (의도된 차집합).
    const allPartKeys = new Set(
      records.map((r) => regionPartKeyForRecord(r, faultJoints)),
    );
    const chipKeys = new Set(deductionChips.map((c) => c.partKey));
    for (const key of allPartKeys) {
      if (chipKeys.has(key)) continue;
      const memberIdx = records.findIndex(
        (r) => regionPartKeyForRecord(r, faultJoints) === key,
      );
      const projected = projectDeductionRecordKeypoints(
        records[memberIdx],
        faultJoints,
      );
      assert.equal(
        projected.length,
        0,
        `${spec.motion} 투영이 있는데 칩이 없다: ${key}`,
      );
    }

    // ── INV-3 record 귀속 — 고아·중복 0 ───────────────────────────────────
    // 축의 정확한 뜻: "각 감점 record 의 투영 keypoint 는 **자기 부위 그룹 정확히
    // 하나**에 전부 들어간다". record 가 두 그룹에 쪼개져 들어가거나(중복) 어느
    // 그룹에도 없는(고아) 일이 없어야 한다.
    const groupByPart = new Map(groups.map((g) => [g.partKey, g]));
    records.forEach((r, i) => {
      const projected = projectDeductionRecordKeypoints(r, faultJoints);
      if (projected.length === 0) return;
      if (markers.recordNumbers[i] == null) return;
      const partKey = regionPartKeyForRecord(r, faultJoints);
      const owner = groupByPart.get(partKey);
      assert.ok(
        owner,
        `${spec.motion} record ${i}(${r.criterion}) 의 부위 그룹이 없다 (고아)`,
      );
      for (const kp of projected) {
        assert.ok(
          owner.keypoints.includes(kp),
          `${spec.motion} record ${i}(${r.criterion}) 의 ${kp} 가 자기 부위 그룹에 없다`,
        );
      }
      // 자기 부위 외의 그룹은 이 record 의 번호를 갖지 않는다 (번호 중복 0).
      for (const g of groups) {
        if (g.partKey === partKey) continue;
        assert.ok(
          !g.numbers.includes(markers.recordNumbers[i] as number),
          `${spec.motion} record ${i} 번호가 ${g.partKey} 그룹에도 있다`,
        );
      }
    });

    // ── INV-3b keypoint 중첩은 **복합 부위 ↔ 그 토큰 부위** 사이에서만 ─────
    // 1단위 M-3 이 정한 부위 모델에서 한 record 가 두 부위 토큰에 걸치면
    // (`arm_extension` = 어깨+손) `shoulder+arm` 이라는 **별 부위**가 생긴다. 그
    // 부위의 경계는 자기 멤버 전부(어깨 포함)를 감싸야 옳으므로, `shoulder` 부위
    // 경계와 어깨 관절을 공유한다 = **경계 중첩**. 이 스위프는 그 중첩이
    // 구조적으로 설명 가능한 경우(복합 ↔ 토큰)만 발생하는지 고정한다. 임의 부위
    // 사이의 중첩은 FAIL. (중첩 자체의 시각 판정 = SUMMARY 시뮬 확인 요청 / N-19)
    let nestedOverlaps = 0;
    for (let a = 0; a < groups.length; a += 1) {
      for (let b = a + 1; b < groups.length; b += 1) {
        const shared = groups[a].keypoints.filter((kp) =>
          groups[b].keypoints.includes(kp),
        );
        if (shared.length === 0) continue;
        nestedOverlaps += shared.length;
        const tokensA = new Set(groups[a].partKey.split('+'));
        const tokensB = new Set(groups[b].partKey.split('+'));
        const subset =
          [...tokensA].every((t) => tokensB.has(t)) ||
          [...tokensB].every((t) => tokensA.has(t));
        assert.ok(
          subset,
          `${spec.motion} 설명 불가 경계 중첩: ${groups[a].partKey} ∩ ${groups[b].partKey} = ${shared.join(',')}`,
        );
      }
    }

    // ── INV-4 병합 배지 ──────────────────────────────────────────────────
    let mergedBadges = 0;
    for (const g of groups) {
      const expected = records
        .map((r, i) =>
          regionPartKeyForRecord(r, faultJoints) === g.partKey
            ? markers.recordNumbers[i]
            : null,
        )
        .filter((n): n is number => n != null)
        .sort((a, b) => a - b);
      assert.deepEqual(g.numbers, expected, `${spec.motion} ${g.partKey} numbers`);
      assert.equal(
        g.badgeLabel,
        expected.join('·'),
        `${spec.motion} ${g.partKey} badgeLabel`,
      );
      if (g.numbers.length >= 2) mergedBadges += 1;
    }

    // ── INV-5·6 강조 형태 (criterion 별) ──────────────────────────────────
    let focusChains = 0;
    let focusCircles = 0;
    let crossSideChains = 0;
    for (const r of records) {
      const focus = projectDeductionRecordKeypoints(r, faultJoints);
      const hi = buildFocusShapes({
        focusKeypoints: focus,
        confidenceOf: () => 0.9,
        threshold: 0.5,
      });
      const lo = buildFocusShapes({
        focusKeypoints: focus,
        confidenceOf: () => 0.1,
        threshold: 0.5,
      });
      // INV-5 — 좌·우 혼합 그룹 0 (선·원 모두).
      for (const group of [
        ...hi.chains.map((c) => c.keypoints),
        ...hi.circleGroups,
        ...lo.chains.map((c) => c.keypoints),
        ...lo.circleGroups,
      ]) {
        const hasLeft = group.some((kp) => kp.startsWith('left_'));
        const hasRight = group.some((kp) => kp.startsWith('right_'));
        if (hasLeft && hasRight) crossSideChains += 1;
        assert.ok(
          !(hasLeft && hasRight),
          `${spec.motion} ${r.criterion} 좌우 혼합: ${JSON.stringify(group)}`,
        );
      }
      // INV-6 — 고신뢰면 표시 ≥ 1 / 저신뢰면 표시 0 (환각 드로잉 0).
      if (focus.length > 0) {
        assert.ok(
          hi.chains.length + hi.circleGroups.length >= 1,
          `${spec.motion} ${r.criterion} 고신뢰인데 표시 0`,
        );
      }
      assert.equal(
        lo.chains.length,
        0,
        `${spec.motion} ${r.criterion} 저신뢰인데 선을 그었다`,
      );
      assert.equal(
        lo.circleGroups.length,
        0,
        `${spec.motion} ${r.criterion} 저신뢰인데 원을 그렸다`,
      );
      focusChains += hi.chains.length;
      focusCircles += hi.circleGroups.length;
    }

    // ── INV-7 참고 칩 갈래 ────────────────────────────────────────────────
    // 위 최대 시나리오는 shoulder·arm·leg 토큰을 전부 감점으로 덮어 참고 칩이 0이
    // 된다(정상 — 겹치면 제외). 참고 갈래를 실제로 밟기 위해 **감점이 다리뿐인**
    // 최소 시나리오를 같은 동작에서 한 번 더 돌린다.
    const legOnly = [rec({ criterion: 'leg_extension', points: -20 })];
    const legOnlyMarkers = buildDeductionMarkers(legOnly as never, faultJoints);
    const legOnlyChips = buildPartChips({
      records: legOnly,
      recordNumbers: legOnlyMarkers.recordNumbers,
      faultJoints,
      attentionKeypoints: ['left_hand'] as never,
      estimatedArea: false,
    });
    assert.deepEqual(
      legOnlyChips.map((c) => [c.partKey, c.label, c.kind]),
      [
        ['leg', '다리', 'deduction'],
        ['arm', '참고: 팔', 'advisory'],
      ],
      `${spec.motion} 참고 칩 갈래`,
    );
    assert.equal(legOnlyChips[1].firstRecordIndex, null);
    const advisoryBranchChips = legOnlyChips.filter(
      (c) => c.kind === 'advisory',
    ).length;

    rows.push({
      motion: spec.motion,
      yamlJoints: spec.joints.length,
      records: records.length,
      partGroups: groups.length,
      chipsDeduction: deductionChips.length,
      chipsAdvisory: advisoryChips.length,
      advisoryBranchChips,
      sheets: allPartKeys.size,
      mergedBadges,
      focusChains,
      focusCircles,
      crossSideChains,
      nestedOverlaps,
    });
  }

  // 결과 요약 표 (SUMMARY 인용용).
  const header =
    '| 동작 | yaml joint | record | 부위 그룹 | 감점 칩 | 참고 칩 | 참고칩(최소) | 시트 | 병합배지 | 선(hi) | 원(hi) | 좌우교차 | 경계중첩 |';
  const lines = [
    '',
    '### 스위프 요약 (등재 10동작 — 마커 그룹 · 칩 · 강조 형태)',
    '',
    header,
    '|---|---|---|---|---|---|---|---|---|---|---|---|---|',
    ...rows.map(
      (r) =>
        `| ${r.motion} | ${r.yamlJoints} | ${r.records} | ${r.partGroups} | ${r.chipsDeduction} | ${r.chipsAdvisory} | ${r.advisoryBranchChips} | ${r.sheets} | ${r.mergedBadges} | ${r.focusChains} | ${r.focusCircles} | ${r.crossSideChains} | ${r.nestedOverlaps} |`,
    ),
    '',
  ];
  console.log(lines.join('\n'));

  fs.writeFileSync(
    OUT_JSON,
    `${JSON.stringify(
      {
        generated_by: 'quick-260730-szk sweep_markers_focus.test.ts',
        criteria_dir: path.relative(REPO, CRITERIA_DIR),
        motions: rows.length,
        totals: {
          records: rows.reduce((a, r) => a + r.records, 0),
          part_groups: rows.reduce((a, r) => a + r.partGroups, 0),
          chips_deduction: rows.reduce((a, r) => a + r.chipsDeduction, 0),
          chips_advisory: rows.reduce((a, r) => a + r.chipsAdvisory, 0),
          advisory_branch_chips: rows.reduce(
            (a, r) => a + r.advisoryBranchChips,
            0,
          ),
          sheets: rows.reduce((a, r) => a + r.sheets, 0),
          merged_badges: rows.reduce((a, r) => a + r.mergedBadges, 0),
          focus_chains_high_conf: rows.reduce((a, r) => a + r.focusChains, 0),
          focus_circles_high_conf: rows.reduce((a, r) => a + r.focusCircles, 0),
          cross_side_chains: rows.reduce((a, r) => a + r.crossSideChains, 0),
          nested_boundary_overlaps: rows.reduce(
            (a, r) => a + r.nestedOverlaps,
            0,
          ),
        },
        rows,
      },
      null,
      2,
    )}\n`,
    'utf8',
  );

  // 스위프 자체가 무의미해지는 것 방지 — 동작 수·record 수 하한.
  assert.equal(rows.length, 10);
  assert.ok(rows.every((r) => r.records >= 10));
  assert.equal(
    rows.reduce((a, r) => a + r.crossSideChains, 0),
    0,
    '좌우 교차 체인 발생',
  );
});
