// 일러스트 부착 판정 골든 프로브 (quick-260731-plf Task 1 — 33-G §C-4 3번).
//
// 실행:
//   node .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/golden_probe.ts
//   (stdout = 정렬된 JSON. 리다이렉트해서 golden_before / golden_after 로 남긴다.)
//
// 왜 이게 필요한가: 이 플랜은 장면 표의 **자료구조를 바꾼다**(Record<motionId> →
// IllustrationScene[]). 구조를 바꾸면서 동시에 에셋을 추가하면, 나중에 거동이 변했을 때
// 그 원인이 "구조 전환" 인지 "신규 에셋" 인지 갈라낼 수 없다. Task 1 은 신규 에셋 0으로
// 구조만 바꾸고 이 프로브 전/후 diff 가 0 임을 증명한다 — 이후 거동 변화의 원인이
// **신규 에셋 하나로 단일 귀속**된다.
//
// 축은 여기 하드코딩한다(모듈에서 파생하지 않는다). 파생하면 Task 3 에서 장면 표가
// 커질 때 축까지 같이 커져서 before/after 대조가 성립하지 않는다.

import { hasIllustrationFor } from '../../../app/src/lib/illustrationScene.ts';

/** 등재 6동작 + 33-14 미완 4동작 = criteria yaml 등재 10동작. */
const MOTIONS: (string | null | undefined)[] = [
  'ref-power-spin',
  'ref-kip-up',
  'ref-climb',
  'ref-invert',
  'ref-foxtop',
  'ref-foxtop-split',
  'ref-peter-pan',
  'ref-elbow-twist-sister',
  'ref-pdshape',
  'ref-sideway-spin',
  'ref-unknown-move',
  '',
  '__proto__',
  'constructor',
  'toString',
  null,
  undefined,
];

/** 실 production 키(부위 토큰·criterion 단독) + 오타·공백 등 fail-closed 갈래. */
const PART_KEYS: (string | null | undefined)[] = [
  'leg',
  'shoulder',
  'arm',
  'shoulder+arm',
  'criterion:line',
  'criterion:split_angle',
  'criterion:dimension_overall_fallback',
  '',
  '   ',
  '+',
  '++',
  'legs',
  'LEG',
  null,
  undefined,
];

const cells: Record<string, { has: boolean }> = {};
for (const motionId of MOTIONS) {
  for (const partKey of PART_KEYS) {
    cells[`${String(motionId)}|${String(partKey)}`] = {
      has: hasIllustrationFor(motionId, partKey),
    };
  }
}

const sorted: Record<string, { has: boolean }> = {};
for (const key of Object.keys(cells).sort()) sorted[key] = cells[key];

process.stdout.write(`${JSON.stringify(sorted, null, 2)}\n`);
