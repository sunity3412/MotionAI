// 실 doc 방출 집계 — 어느 (동작 × 부위) 시트가 실제로 열리는가 (quick-260731-plf Task 2).
//
// 실행:
//   node .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/emit_census.ts \
//     > .planning/quick/260731-plf-33-g-c-4-item3-shoulder-and-elbow-defect/emit_census.json
//
// 왜 이 프로브인가: "어느 동작에 어깨 그림이 필요한가"를 동작명 감으로 정하면
// single-motion-fixation 이다. 화면이 실제로 여는 시트만이 근거다. 규칙 사본을 만들지
// 않기 위해 **앱의 실제 함수**(`regionPartKeyForRecord` ← `projectDeductionRecordKeypoints`)
// 를 그대로 import 해서 접는다 — result.tsx:1852 가 화면에서 하는 것과 문자 그대로 같은
// 호출이다(같은 faultJoints 인자 규칙 포함: visionVeto.status==='applied' 일 때만 전달).

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { regionPartKeyForRecord } from '../../../app/src/lib/deductionSheet.ts';
import type { DeductionRecord, KeypointName } from '../../../app/src/types/analysis.ts';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '../../..');
const DOCS_DIR = path.join(
  REPO,
  '.planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/docs_after',
);

type Emitted = {
  partKey: string;
  criterion: string;
  points: number | null;
  source: string | null;
};

type DocRow = {
  file: string;
  analysisId: string | null;
  mode: string | null;
  referenceMotionId: string | null;
  overallScore: number | null;
  records: number;
  faultZoomCards: number;
  visionVetoStatus: string | null;
  emitted: Emitted[];
  partKeys: Record<string, Emitted[]>;
};

const rows: DocRow[] = [];

for (const file of fs.readdirSync(DOCS_DIR).filter((f) => f.endsWith('.json')).sort()) {
  const doc = JSON.parse(fs.readFileSync(path.join(DOCS_DIR, file), 'utf8'));
  const result = doc?.result ?? {};
  const records: DeductionRecord[] = result?.deductionBreakdown?.records ?? [];
  // result.tsx:1017 과 동일 조건 — applied 일 때만 faultJoints 를 넘긴다.
  const faultJoints: readonly KeypointName[] | undefined =
    result?.visionVeto?.status === 'applied'
      ? result.visionVeto.faultJoints
      : undefined;

  const emitted: Emitted[] = records.map((rec) => ({
    partKey: regionPartKeyForRecord(rec, faultJoints),
    criterion: rec.criterion,
    points: typeof rec.points === 'number' ? rec.points : null,
    source: (rec as { source?: string }).source ?? null,
  }));

  const partKeys: Record<string, Emitted[]> = {};
  for (const e of emitted) {
    (partKeys[e.partKey] ??= []).push(e);
  }

  rows.push({
    file,
    analysisId: doc?.analysisId ?? null,
    mode: doc?.mode ?? null,
    referenceMotionId: doc?.referenceMotionId ?? null,
    overallScore: typeof result?.overallScore === 'number' ? result.overallScore : null,
    records: records.length,
    faultZoomCards: Array.isArray(result?.faultZoomComparisons)
      ? result.faultZoomComparisons.length
      : 0,
    visionVetoStatus: result?.visionVeto?.status ?? null,
    emitted,
    partKeys,
  });
}

// (동작 × 부위) 합산 — 이 표가 생성 대상 Tier 1 의 1차 근거다.
const combos: Record<string, { motionId: string; partKey: string; docs: string[]; records: number }> = {};
for (const row of rows) {
  if (!row.referenceMotionId) continue;
  for (const [partKey, list] of Object.entries(row.partKeys)) {
    const key = `${row.referenceMotionId}|${partKey}`;
    const slot = (combos[key] ??= {
      motionId: row.referenceMotionId,
      partKey,
      docs: [],
      records: 0,
    });
    slot.docs.push(row.file);
    slot.records += list.length;
  }
}

process.stdout.write(
  `${JSON.stringify(
    {
      generated_by: 'quick-260731-plf emit_census.ts',
      docs_dir: path.relative(REPO, DOCS_DIR),
      rule_source:
        'app/src/lib/deductionSheet.ts::regionPartKeyForRecord (실 앱 함수 import — 규칙 사본 0)',
      docs: rows,
      combos: Object.values(combos).sort((a, b) =>
        `${a.motionId}|${a.partKey}`.localeCompare(`${b.motionId}|${b.partKey}`),
      ),
    },
    null,
    2,
  )}\n`,
);
