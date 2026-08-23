// split_angle 플립 교차표 측정 (quick-260824-bxf Task 1) — Firestore **읽기 전용**.
//
// 판정 규칙 = SPLIT-FLIP-CROSSTAB.md "## 판정 규칙 (측정 전 박제)" (이 파일과
// 같은 커밋 — measure-first: 규칙 커밋이 측정 결과 커밋보다 먼저다). 이
// 스크립트는 그 규칙의 기계 실행일 뿐이며, 규칙에 없는 판단을 추가하지 않는다.
// 페어 구성·criterion 첫-record 선택·비유한값 skip 규칙 = measure_noise.mjs
// (quick-260822-oe1) 와 동일 — 표본만 split_angle 로 한정.
//
// 실행:
//   GOOGLE_APPLICATION_CREDENTIALS=/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json \
//     node .planning/quick/260824-bxf-criterion-split-angle-12-split-21/measure_split_flip.mjs
//
// PII 방어 (T-bxf-01):
//   - select() 필드 마스크로 필요한 필드만 fetch — bodyProfile·영상 URL·키는
//     읽지도 않는다.
//   - 출력 uid 는 앞 6자 + '…' 절단.
// 쓰기 API 호출 0 (T-bxf-02) — get/listDocuments 만. Task 1 grep 게이트가
// 쓰기 메서드 호출 부재를 기계 검증하므로 집계 컨테이너도 Map 대신 평범한
// 객체를 쓴다 (Map 채우기 메서드가 게이트 패턴과 표기가 겹친다).

import { createRequire } from 'node:module';

// firebase-admin 은 app/node_modules 의 devDependency — app 쪽 resolution 을
// 빌린다 (measure_noise.mjs 앵커 패턴 그대로 — 경로는 resolution 기준일 뿐).
const require = createRequire(
  new URL('../../../app/scripts/measure_noise_anchor.mjs', import.meta.url),
);
const { initializeApp, applicationDefault } = require('firebase-admin/app');
const { getFirestore } = require('firebase-admin/firestore');

// ── 판정 규칙 상수 (SPLIT-FLIP-CROSSTAB.md 박제값 — measure_noise.mjs 동일) ──
/** 결정론 ON 경계 (quick-260809-i0q — RTMW_DETERMINISTIC=1 실업로드 경로 박제). */
const DETERMINISM_ON_MS = Date.parse('2026-08-09T00:00:00+09:00');
/** (b) 세션 페어 최대 간격. */
const SESSION_PAIR_MAX_GAP_MS = 48 * 3600 * 1000;
/** 표본 criterion — 이 스크립트는 split_angle 만 본다. */
const CRITERION = 'split_angle';

function truncUid(uid) {
  return `${String(uid).slice(0, 6)}…`;
}

/**
 * doc 의 records 에서 split_angle delta = |baseline − measured|.
 * unit 'deg' + criterion 정확 일치 **첫 유효 record** (비유한값 skip —
 * measure_noise.mjs degDeltasByCriterion / Task 2 extractCriterionMeasure 와
 * 같은 선택 규칙). 없으면 null.
 */
function splitDelta(records) {
  if (!Array.isArray(records)) return null;
  for (const r of records) {
    if (r == null || typeof r !== 'object') continue;
    if (r.unit !== 'deg') continue;
    if (r.criterion !== CRITERION) continue;
    const m = r.measuredValue;
    const b = r.baselineValue;
    if (typeof m !== 'number' || typeof b !== 'number') continue;
    if (!Number.isFinite(m) || !Number.isFinite(b)) continue;
    return Math.abs(b - m);
  }
  return null;
}

/** nearest-rank 백분위 — 오름차순 정렬 후 index max(0, ceil(q·N) − 1). */
function percentileNearestRank(sorted, q) {
  if (sorted.length === 0) return null;
  const idx = Math.max(0, Math.ceil(q * sorted.length) - 1);
  return sorted[idx];
}

function distStats(values) {
  if (values.length === 0) return null;
  const s = [...values].sort((a, b) => a - b);
  return {
    n: s.length,
    min: s[0],
    median: percentileNearestRank(s, 0.5),
    p95: percentileNearestRank(s, 0.95),
    max: s[s.length - 1],
  };
}

function fmt(v) {
  return v == null ? '-' : v.toFixed(2);
}

function pct(num, den) {
  if (den === 0) return '-';
  return `${((num / den) * 100).toFixed(1)}%`;
}

async function main() {
  initializeApp({ credential: applicationDefault() });
  const db = getFirestore();

  // users/*/analyses 순회 — listDocuments 는 "missing" 컨테이너 doc 도 반환한다.
  const userRefs = await db.collection('users').listDocuments();
  const docs = []; // 추출 튜플
  let totalDone = 0;

  for (const userRef of userRefs) {
    const snap = await userRef
      .collection('analyses')
      .select(
        'mode',
        'status',
        'createdAt',
        'fileName',
        'anglesFrames',
        'result.comparison.referenceMotionId',
        'result.deductionBreakdown.records',
      )
      .get();
    for (const d of snap.docs) {
      const raw = d.data();
      if (raw.status !== 'done') continue;
      totalDone += 1;
      const records = raw?.result?.deductionBreakdown?.records;
      if (!Array.isArray(records) || records.length === 0) continue;
      docs.push({
        uid: userRef.id,
        analysisId: d.id,
        mode: raw.mode ?? null,
        referenceMotionId: raw?.result?.comparison?.referenceMotionId ?? null,
        createdAt: typeof raw.createdAt === 'number' ? raw.createdAt : null,
        fileName: typeof raw.fileName === 'string' ? raw.fileName : '',
        anglesFrames:
          typeof raw.anglesFrames === 'number' ? raw.anglesFrames : null,
        split: splitDelta(records), // number | null
      });
    }
  }

  // ── (a) 같은-영상 재분석 페어 — measure_noise.mjs 와 동일한 그룹 규칙 ────
  // 같은 uid + 같은 fileName(비어있지 않음) + 같은 anglesFrames + 같은 mode
  // (mode1 이면 같은 referenceMotionId 까지). 페어 구성은 전체 deg-record doc
  // 모집단으로 하고, split_angle 보유 필터는 표본 수집 단계에서 건다 —
  // (b) 인접성 판정이 measure_noise.mjs 와 어긋나지 않게.
  const groupsA = Object.create(null);
  for (const doc of docs) {
    if (!doc.fileName || doc.anglesFrames == null || doc.createdAt == null)
      continue;
    const refPart = doc.mode === 'mode1' ? doc.referenceMotionId ?? '' : '';
    const key = [doc.uid, doc.fileName, doc.anglesFrames, doc.mode, refPart].join(
      ' ',
    );
    if (groupsA[key] == null) groupsA[key] = [];
    groupsA[key].push(doc);
  }

  const pairKey = (x, y) => [x.analysisId, y.analysisId].sort().join('|');
  const pairsA = [];
  const seenPairs = new Set();
  for (const group of Object.values(groupsA)) {
    for (let i = 0; i < group.length; i++) {
      for (let j = i + 1; j < group.length; j++) {
        const a = group[i];
        const b = group[j];
        const deterministic =
          a.createdAt >= DETERMINISM_ON_MS && b.createdAt >= DETERMINISM_ON_MS;
        pairsA.push({ a, b, kind: deterministic ? 'deterministic' : 'historical' });
        seenPairs.add(pairKey(a, b));
      }
    }
  }

  // ── (b) 48h 세션 페어 — 같은 (uid, referenceMotionId) mode1, 인접 연속 짝 ──
  const groupsB = Object.create(null);
  for (const doc of docs) {
    if (doc.mode !== 'mode1' || !doc.referenceMotionId || doc.createdAt == null)
      continue;
    const key = [doc.uid, doc.referenceMotionId].join(' ');
    if (groupsB[key] == null) groupsB[key] = [];
    groupsB[key].push(doc);
  }
  const pairsB = [];
  for (const group of Object.values(groupsB)) {
    group.sort((x, y) => x.createdAt - y.createdAt);
    for (let i = 0; i + 1 < group.length; i++) {
      const a = group[i];
      const b = group[i + 1];
      if (b.createdAt - a.createdAt > SESSION_PAIR_MAX_GAP_MS) continue;
      if (seenPairs.has(pairKey(a, b))) continue; // (a) 이중 계상 금지
      pairsB.push({ a, b, kind: 'session48h' });
    }
  }

  // ── 표본 = 두 doc 모두 split_angle delta 보유인 페어 ───────────────────
  const allPairs = [...pairsA, ...pairsB];
  const splitPairs = [];
  for (const p of allPairs) {
    if (p.a.split == null || p.b.split == null) continue;
    splitPairs.push({
      kind: p.kind,
      da: p.a.split,
      db: p.b.split,
      flip: p.a.split !== p.b.split, // 정확 부등 (규칙 정의)
      uid6: truncUid(p.a.uid),
    });
  }

  // ── 리포트 (markdown — SPLIT-FLIP-CROSSTAB.md 에 붙이는 형태) ───────────
  const KINDS = ['historical', 'deterministic', 'session48h'];
  const KIND_LABEL = {
    historical: 'same-video historical',
    deterministic: 'same-video deterministic',
    session48h: 'session48h',
  };
  const lines = [];
  lines.push(`측정 시각: ${new Date().toISOString()}`);
  lines.push('');
  lines.push(`- 전체 done doc: ${totalDone}`);
  lines.push(`- deg record 보유 doc (페어 모집단): ${docs.length}`);
  lines.push(
    `- split_angle delta 보유 doc: ${docs.filter((d) => d.split != null).length}`,
  );
  lines.push(
    `- (a) 같은-영상 페어: ${pairsA.length} (deterministic ${pairsA.filter((p) => p.kind === 'deterministic').length} / historical ${pairsA.filter((p) => p.kind === 'historical').length})`,
  );
  lines.push(`- (b) 48h 세션 페어: ${pairsB.length}`);
  lines.push(
    `- **두 doc 모두 split_angle 보유 페어 (표본): ${splitPairs.length}**`,
  );
  lines.push('');

  lines.push('### 페어 종류별 (delta_i, delta_j) 값 조합 교차표');
  lines.push('');
  for (const kind of KINDS) {
    const rows = splitPairs.filter((p) => p.kind === kind);
    lines.push(`**${KIND_LABEL[kind]}** (페어 ${rows.length}):`);
    lines.push('');
    if (rows.length === 0) {
      lines.push('- 표본 0');
      lines.push('');
      continue;
    }
    const combos = Object.create(null); // comboKey -> { count, flip }
    for (const p of rows) {
      const lo = Math.min(p.da, p.db);
      const hi = Math.max(p.da, p.db);
      const key = `${fmt(lo)} | ${fmt(hi)}`;
      if (combos[key] == null) combos[key] = { count: 0, flip: p.flip };
      combos[key].count += 1;
    }
    lines.push('| delta 조합 (min, max) | 페어 수 | 플립 |');
    lines.push('|----------------------|--------|------|');
    for (const key of Object.keys(combos).sort()) {
      const e = combos[key];
      lines.push(`| ${key} | ${e.count} | ${e.flip ? 'O' : '-'} |`);
    }
    const flips = rows.filter((p) => p.flip).length;
    lines.push('');
    lines.push(
      `- 플립 비율: ${flips}/${rows.length} = **${pct(flips, rows.length)}**`,
    );
    lines.push('');
  }

  lines.push('### split_angle |Δdelta| 분포 (deg)');
  lines.push('');
  lines.push('| kind | n | min | median | P95 | max |');
  lines.push('|------|---|-----|--------|-----|-----|');
  for (const kind of KINDS) {
    const vals = splitPairs
      .filter((p) => p.kind === kind)
      .map((p) => Math.abs(p.da - p.db));
    const st = distStats(vals);
    if (st == null) {
      lines.push(`| ${KIND_LABEL[kind]} | 0 | - | - | - | - |`);
    } else {
      lines.push(
        `| ${KIND_LABEL[kind]} | ${st.n} | ${fmt(st.min)} | ${fmt(st.median)} | ${fmt(st.p95)} | ${fmt(st.max)} |`,
      );
    }
  }
  const pooled = splitPairs.map((p) => Math.abs(p.da - p.db));
  const pooledStats = distStats(pooled);
  if (pooledStats == null) {
    lines.push('| 전체 | 0 | - | - | - | - |');
  } else {
    lines.push(
      `| 전체 | ${pooledStats.n} | ${fmt(pooledStats.min)} | ${fmt(pooledStats.median)} | ${fmt(pooledStats.p95)} | ${fmt(pooledStats.max)} |`,
    );
  }
  lines.push('');

  process.stdout.write(lines.join('\n') + '\n');
}

main().catch((err) => {
  console.error('measure_split_flip 실패:', err?.message ?? err);
  process.exitCode = 1;
});
