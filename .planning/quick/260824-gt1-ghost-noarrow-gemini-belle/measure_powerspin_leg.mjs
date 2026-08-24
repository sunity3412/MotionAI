// 파워스핀 다리 record 방향·크기 분포 측정 (quick-260824-gt1 Task 1) —
// Firestore **읽기 전용**.
//
// 목적 (D-01): ghost-noarrow 잔상(오류) 자세 서술을 실측에서 도출한다 —
// 실측 없이 자세를 지어내지 않는다. 이 스크립트는 실사용 doc 의
// leg_extension / split_angle record 의 부호(방향)와 크기 분포만 뽑는다.
// 골격 = bxf measure_split_flip.mjs (앵커 createRequire + listDocuments 순회
// + select() 필드 마스크). 페어 로직은 버리고 단일-doc 분포 측정으로 단순화.
//
// 실행:
//   GOOGLE_APPLICATION_CREDENTIALS=/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json \
//     node .planning/quick/260824-gt1-ghost-noarrow-gemini-belle/measure_powerspin_leg.mjs
//
// PII 방어 (T-gt1-01):
//   - select() 필드 마스크로 필요한 5개 필드만 fetch — bodyProfile·영상 URL·키는
//     읽지도 않는다.
//   - 출력 uid 는 앞 6자 + '…' 절단.
// 쓰기 API 호출 0 (T-gt1-02) — get/listDocuments 만. Task 1 grep 게이트가
// 쓰기 메서드 호출 부재를 기계 검증하므로 집계 컨테이너는 평범한 객체/배열만
// 쓴다 — Set/Map 금지, Object 정적 헬퍼 중 게이트 패턴과 표기가 겹치는 것도
// 피한다 (bxf 관행 승계 + 강화).

import { createRequire } from 'node:module';

// firebase-admin 은 app/node_modules 의 devDependency — app 쪽 resolution 을
// 빌린다 (앵커 파일은 존재하지 않으며 resolution 기준 경로일 뿐, app/ 무접촉).
const require = createRequire(
  new URL('../../../app/scripts/measure_noise_anchor.mjs', import.meta.url),
);
const { initializeApp, applicationDefault } = require('firebase-admin/app');
const { getFirestore } = require('firebase-admin/firestore');

// ── 표본 정의 (플랜 Task 1 박제값) ────────────────────────────────────────
/** 대상 기준 모션 — 파워스핀 1종 (D-04). */
const TARGET_REF = 'ref-power-spin';
/** 대상 criterion — 이 두 개의 deg record 전건. */
const CRITERIA = ['leg_extension', 'split_angle'];

// 실사용 필터 (코퍼스 제외 — 플랜이 박제한 정확히 이 목록).
const UID_PREFIX_EXCLUDE = ['phase', 'mock', 'genpod', 'e2e', 'sweep', 'eval', 'test'];
const UID_EXACT_EXCLUDE = ['det', 'kipdia', 'devdia', 'solo', 'pode2e'];
const DOCID_PREFIX_EXCLUDE = ['p34', 'p35', 'kipupFault', 'testprogress'];

function isCorpusUid(uid) {
  const s = String(uid);
  for (const p of UID_PREFIX_EXCLUDE) {
    if (s.startsWith(p)) return true;
  }
  for (const e of UID_EXACT_EXCLUDE) {
    if (s === e) return true;
  }
  return false;
}

function isCorpusDocId(id) {
  const s = String(id);
  for (const p of DOCID_PREFIX_EXCLUDE) {
    if (s.startsWith(p)) return true;
  }
  return false;
}

function truncUid(uid) {
  return `${String(uid).slice(0, 6)}…`;
}

/** nearest-rank 백분위 — 오름차순 정렬 후 index max(0, ceil(q·N) − 1). */
function percentileNearestRank(sorted, q) {
  if (sorted.length === 0) return null;
  const idx = Math.max(0, Math.ceil(q * sorted.length) - 1);
  return sorted[idx];
}

function fmt(v) {
  return v == null ? '-' : v.toFixed(2);
}

async function main() {
  initializeApp({ credential: applicationDefault() });
  const db = getFirestore();

  // users/*/analyses 순회 — listDocuments 는 "missing" 컨테이너 doc 도 반환한다.
  const userRefs = await db.collection('users').listDocuments();

  // criterion -> [{ delta(signed, measured-baseline), baseline, measured, uid6, docId }]
  const samples = { leg_extension: [], split_angle: [] };
  let scannedUsers = 0;
  let excludedUsers = 0;
  let excludedDocs = 0;
  let totalDone = 0;
  let powerspinDone = 0;

  for (const userRef of userRefs) {
    if (isCorpusUid(userRef.id)) {
      excludedUsers += 1;
      continue;
    }
    scannedUsers += 1;
    const snap = await userRef
      .collection('analyses')
      .select(
        'mode',
        'status',
        'createdAt',
        'result.comparison.referenceMotionId',
        'result.deductionBreakdown.records',
      )
      .get();
    for (const d of snap.docs) {
      if (isCorpusDocId(d.id)) {
        excludedDocs += 1;
        continue;
      }
      const raw = d.data();
      if (raw.status !== 'done') continue;
      totalDone += 1;
      const refId = raw?.result?.comparison?.referenceMotionId ?? null;
      if (refId !== TARGET_REF) continue;
      powerspinDone += 1;
      const records = raw?.result?.deductionBreakdown?.records;
      if (!Array.isArray(records)) continue;
      // 해당 criterion **전 record** (bxf 의 첫-record 규칙과 다름 — 플랜 명시).
      // 비유한값 skip 은 bxf 선택 규칙 승계.
      for (const r of records) {
        if (r == null || typeof r !== 'object') continue;
        if (r.unit !== 'deg') continue;
        if (CRITERIA.indexOf(r.criterion) === -1) continue;
        const m = r.measuredValue;
        const b = r.baselineValue;
        if (typeof m !== 'number' || typeof b !== 'number') continue;
        if (!Number.isFinite(m) || !Number.isFinite(b)) continue;
        samples[r.criterion].push({
          delta: m - b,
          baseline: b,
          measured: m,
          uid6: truncUid(userRef.id),
          docId: d.id,
        });
      }
    }
  }

  // ── 리포트 (markdown — PREDICTION.md 실측 절에 붙이는 형태) ──────────────
  const lines = [];
  lines.push(`측정 시각: ${new Date().toISOString()}`);
  lines.push('');
  lines.push(`- 스캔 사용자: ${scannedUsers} (코퍼스 uid 제외 ${excludedUsers})`);
  lines.push(`- 코퍼스 doc id 제외: ${excludedDocs}`);
  lines.push(`- 실사용 done doc: ${totalDone}`);
  lines.push(`- 그중 ref-power-spin done doc: ${powerspinDone}`);
  lines.push('');

  lines.push('### criterion 별 signed delta(measured − baseline) 분포 (deg)');
  lines.push('');
  lines.push(
    '| criterion | n | 부족(m<b) | 초과(m>b) | min | median | P95 | max | \\|delta\\| median |',
  );
  lines.push('|---|---|---|---|---|---|---|---|---|');
  for (const crit of CRITERIA) {
    const rows = samples[crit];
    if (rows.length === 0) {
      lines.push(`| ${crit} | 0 | - | - | - | - | - | - | - |`);
      continue;
    }
    const deltas = rows.map((r) => r.delta).sort((a, b) => a - b);
    const absDeltas = rows.map((r) => Math.abs(r.delta)).sort((a, b) => a - b);
    const below = rows.filter((r) => r.delta < 0).length;
    const above = rows.filter((r) => r.delta > 0).length;
    lines.push(
      `| ${crit} | ${rows.length} | ${below} | ${above} | ${fmt(deltas[0])} | ${fmt(
        percentileNearestRank(deltas, 0.5),
      )} | ${fmt(percentileNearestRank(deltas, 0.95))} | ${fmt(
        deltas[deltas.length - 1],
      )} | ${fmt(percentileNearestRank(absDeltas, 0.5))} |`,
    );
  }
  lines.push('');

  lines.push('### record 전건 (uid 6자 절단)');
  lines.push('');
  lines.push('| criterion | uid | baseline | measured | delta |');
  lines.push('|---|---|---|---|---|');
  for (const crit of CRITERIA) {
    const rows = [...samples[crit]].sort((a, b) => a.delta - b.delta);
    for (const r of rows) {
      lines.push(
        `| ${crit} | ${r.uid6} | ${fmt(r.baseline)} | ${fmt(r.measured)} | ${fmt(r.delta)} |`,
      );
    }
  }
  lines.push('');

  process.stdout.write(lines.join('\n') + '\n');
}

main().catch((err) => {
  console.error('measure_powerspin_leg 실패:', err?.message ?? err);
  process.exitCode = 1;
});
