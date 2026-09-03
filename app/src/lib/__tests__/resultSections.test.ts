// 결과 화면 섹션 순서·가시성·recordId 조인 순수 뷰모델 검증 (32-11 Task 1).
//
// 실행: node --test app/src/lib/__tests__/resultSections.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행 — 신규 npm 의존성 0
// (summarySource.test.ts / cueTrack.test.ts 선례). node:test / node:assert 표준
// 모듈 + `.ts` 확장자 import 만.
//
// 왜 이 테스트가 존재하나(리뷰 MEDIUM): result.tsx 는 2,700줄 대배선이라 typecheck
// 만으로는 "섹션이 D-02 확정 순서로, 조건대로 보인다"를 보증하지 못한다. 순서·가시성·
// legacy 분기·recordId 조인을 순수 함수로 격리해 여기서 고정한다.
//
// 검증 축 5개 (플랜 behavior 1~5):
//   1) deriveResultSections(정상 mode1) → 섹션 키 배열 = 게이트 확정 순서
//   2) 조건 가시성 — safetyFlags 0 → risk 부재 / isCleanPass → 문제 섹션 부재 + 축하
//   3) legacy(3단 문구 부재) → topFix legacy 표식, 전 섹션 계산(크래시 0)
//   4) mode3 — missionOutcome → growth outcome, escalation coach_card → coachCard 승격
//   5) buildRecordMaps — recordId 조인 맵 + 'idx:N' 폴백 + 질문 조인, 충돌 0
//   6) pickExpandAnchorY — F-7 펼침/접기 앵커 선택 (33-G, quick-260731-cum)
//   7) selectEstimatedZoomEntries — IN-01 저신뢰 경로 예상 부위 사진 카드 선택
//      (quick-260903-ftg: primary 맨 앞 / 숨김 제외 / 같은 키 dedupe / 빈 입력)

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  deriveResultSections,
  buildRecordMaps,
  pickExpandAnchorY,
  selectEstimatedZoomEntries,
  RESULT_SECTION_ORDER,
  type ResultSectionsInput,
} from '../resultSections.ts';

// 정상 mode1 기본 입력 (감점 다수, 문구 방출, 미션 있음).
const NORMAL_MODE1: ResultSectionsInput = {
  mode: 'mode1',
  isCleanPass: false,
  safetyFlagCount: 0,
  hasRecords: true,
  hasMission: true,
  escalation: 'none',
  hasMissionOutcome: false,
  hasPhrases: true,
  isMode3First: false,
  hasQuestions: true,
  hasExercise: true,
};

// ── Test 1: 순서 = 게이트 확정 순서 ──────────────────────────────────────────
test('Test 1 (순서): deriveResultSections(정상 mode1) 섹션 키 = 게이트 확정 순서', () => {
  const sections = deriveResultSections(NORMAL_MODE1);
  const keys = sections.map((s) => s.key);
  assert.deepEqual(keys, [
    'summary',
    'risk',
    'topFix',
    'compare',
    'collapsed',
    'growth',
    'exercise',
    'questions',
    'judgeInfo',
    'referenceCorner',
  ]);
  // RESULT_SECTION_ORDER 단일 출처와 일치.
  assert.deepEqual(keys, RESULT_SECTION_ORDER);
});

// ── Test 2: 조건 가시성 (위험 트리아지 + cleanPass 축하) ─────────────────────
test('Test 2 (가시성): safetyFlags 0 → risk 부재; isCleanPass → 문제 섹션 부재 + 축하', () => {
  // safetyFlags 0 → risk.visible false.
  const noRisk = deriveResultSections(NORMAL_MODE1);
  const risk = noRisk.find((s) => s.key === 'risk');
  assert.equal(risk?.visible, false);

  // safetyFlags 있으면 risk 표시.
  const withRisk = deriveResultSections({ ...NORMAL_MODE1, safetyFlagCount: 2 });
  assert.equal(withRisk.find((s) => s.key === 'risk')?.visible, true);

  // isCleanPass → topFix(문제 섹션) 부재 + summary 축하 variant + collapsed 부재.
  const clean = deriveResultSections({
    ...NORMAL_MODE1,
    isCleanPass: true,
    hasRecords: false,
  });
  assert.equal(clean.find((s) => s.key === 'topFix')?.visible, false);
  assert.equal(clean.find((s) => s.key === 'collapsed')?.visible, false);
  assert.equal(clean.find((s) => s.key === 'summary')?.variant, 'clean');
  // judgeInfo(감점 시뮬레이션)도 감점 없으면 부재.
  assert.equal(clean.find((s) => s.key === 'judgeInfo')?.visible, false);
});

// ── Test 3: legacy(3단 문구 부재) → 폴백 표식 + 전 섹션 계산 ──────────────────
test('Test 3 (legacy): 문구 부재 doc → topFix legacy 표식, 전 섹션 계산(크래시 0)', () => {
  const legacy = deriveResultSections({
    ...NORMAL_MODE1,
    hasPhrases: false,
    hasMission: false,
  });
  // 전 섹션이 계산돼 있다 (10개 — 부분 계산으로 인한 렌더 크래시 0).
  assert.equal(legacy.length, RESULT_SECTION_ORDER.length);
  const topFix = legacy.find((s) => s.key === 'topFix');
  assert.equal(topFix?.visible, true);
  assert.equal(topFix?.variant, 'legacy');
  // 문구 방출 doc 은 phrased 표식.
  const phrased = deriveResultSections(NORMAL_MODE1).find((s) => s.key === 'topFix');
  assert.equal(phrased?.variant, 'phrased');
});

// ── Test 4: mode3 성장/미션 표식 + 코치 카드 승격 ────────────────────────────
test('Test 4 (mode3): missionOutcome → growth outcome; escalation coach_card → coachCard', () => {
  const base: ResultSectionsInput = {
    ...NORMAL_MODE1,
    mode: 'mode3',
    isMode3First: false,
  };
  // mode1 은 성장 섹션 부재.
  assert.equal(
    deriveResultSections(NORMAL_MODE1).find((s) => s.key === 'growth')?.visible,
    false,
  );
  // mode3 + missionOutcome → growth outcome 표식.
  const withOutcome = deriveResultSections({ ...base, hasMissionOutcome: true });
  const growth = withOutcome.find((s) => s.key === 'growth');
  assert.equal(growth?.visible, true);
  assert.equal(growth?.variant, 'outcome');
  // escalation coach_card → coachCard 승격 표식(outcome 보다 우선).
  const escalated = deriveResultSections({
    ...base,
    hasMissionOutcome: true,
    escalation: 'coach_card',
  });
  assert.equal(escalated.find((s) => s.key === 'growth')?.variant, 'coachCard');
});

// ── Test 5: buildRecordMaps — recordId 조인 + idx 폴백 + 질문 조인 (충돌 0) ──
test('Test 5 (recordId 맵): recordId 조인 + idx 폴백 + 질문 조인, 충돌 0', () => {
  const records = [
    { recordId: 'r00:leg_extension', criterion: 'leg_extension', points: -20 },
    { recordId: 'r01:split_angle', criterion: 'split_angle', points: -10 },
    { criterion: 'line', points: -5 }, // legacy — recordId 부재
  ];
  const questions = [
    { text: '무릎 어떻게 펴요', source: 'mission_stuck', recordId: 'r00:leg_extension' },
    { text: '전신 질문', source: 'safety' }, // recordId 부재 — 어느 record 에도 안 붙음
  ];
  const maps = buildRecordMaps(records, null, questions);

  // 안정 조인 키 존재.
  assert.ok(maps.has('r00:leg_extension'));
  assert.ok(maps.has('r01:split_angle'));
  // recordId 부재 legacy record 는 index 폴백 키.
  assert.ok(maps.has('idx:2'));
  // 키 충돌 0 (3개 record → 3개 엔트리).
  assert.equal(maps.size, 3);

  // 질문 조인 — recordId 일치하는 질문만 해당 record 에.
  assert.equal(maps.get('r00:leg_extension')?.questions.length, 1);
  assert.equal(maps.get('r00:leg_extension')?.questions[0].text, '무릎 어떻게 펴요');
  assert.equal(maps.get('r01:split_angle')?.questions.length, 0);
  // recordId 부재 질문은 어느 record 에도 붙지 않음.
  assert.equal(maps.get('idx:2')?.questions.length, 0);

  // index 보존 (점프 y 조인용).
  assert.equal(maps.get('idx:2')?.index, 2);

  // recordId 중복 방어 — 같은 recordId 두 번이면 두 번째는 idx 폴백으로 강등(충돌 0).
  const dup = buildRecordMaps(
    [
      { recordId: 'rX', criterion: 'a', points: -1 },
      { recordId: 'rX', criterion: 'b', points: -2 },
    ],
    null,
    null,
  );
  assert.equal(dup.size, 2);
  assert.ok(dup.has('rX'));
  assert.ok(dup.has('idx:1'));
});

// ── Test 7: belle 2026-08-31 빈 상태 규칙 — 내용 '없음' 섹션 미렌더 ────────────
test('Test 7 (빈 상태): growth 는 outcome/coachCard 있을 때만, exercise 는 개인화 매핑 있을 때만', () => {
  // 정당화 (belle 2026-08-31 빈 상태 규칙, quick-260831-lcc): mode3 라도
  // missionOutcome/coach_card 실체가 없으면 성장 섹션 미렌더. 구 규칙(mode3 면
  // 항상 렌더)은 "이어갈 지난 미션이 없어요" 빈 안내문이 자리를 차지했고, 그
  // 의미는 mode3-first 안내문(동작 비교 자리 1줄)과 중복 — 정보 손실 0.
  const emptyGrowth = deriveResultSections({
    ...NORMAL_MODE1,
    mode: 'mode3',
    hasMissionOutcome: false,
    escalation: 'none',
  });
  assert.equal(emptyGrowth.find((s) => s.key === 'growth')?.visible, false);
  // outcome 실체가 있으면 렌더 (기존 outcome 경로 무회귀).
  const withOutcome = deriveResultSections({
    ...NORMAL_MODE1,
    mode: 'mode3',
    hasMissionOutcome: true,
  });
  assert.equal(withOutcome.find((s) => s.key === 'growth')?.visible, true);
  // coach_card 승격은 outcome 없어도 렌더 (D-27 3회차 무회귀).
  const coachCard = deriveResultSections({
    ...NORMAL_MODE1,
    mode: 'mode3',
    hasMissionOutcome: false,
    escalation: 'coach_card',
  });
  assert.equal(coachCard.find((s) => s.key === 'growth')?.visible, true);

  // 정당화 (belle 2026-08-31 빈 상태 규칙): hasExercise 의미 = "개인화 전면
  // 운동(frontExercise) 존재". 구 규칙 `!== false`(미전달=표시)는 "매핑이
  // 없어요" 빈 카드를 낳았다 — 미전달/false 모두 미렌더로 전환.
  const noExercise = deriveResultSections({ ...NORMAL_MODE1, hasExercise: false });
  assert.equal(noExercise.find((s) => s.key === 'exercise')?.visible, false);
  const undefExercise = deriveResultSections({
    ...NORMAL_MODE1,
    hasExercise: undefined,
  });
  assert.equal(undefExercise.find((s) => s.key === 'exercise')?.visible, false);
  // 개인화 매핑 존재 doc 은 종전대로 렌더.
  assert.equal(
    deriveResultSections(NORMAL_MODE1).find((s) => s.key === 'exercise')?.visible,
    true,
  );
});

// ── Test 6: F-7 펼침/접기 앵커 선택 (33-G F-7, quick-260731-cum) ───────────────
test('Test 6 (F-7 앵커): 첫 키 우선 / 두 번째 폴백 / 전무 → null / 음수 클램프', () => {
  const KEYS = ['anchor:summaryCard', 'anchor:scoreGauge', 'anchor:scoreBreakdown'];

  // 6-1. 첫 키가 기록돼 있으면 그것을 쓴다 — 요약 카드가 화면에 남아야 "펼쳐졌다"가
  //      자명해진다(D-05 ②). 아래 앵커가 같이 있어도 첫 키가 이긴다.
  const both = new Map<string, number>([
    ['anchor:summaryCard', 420],
    ['anchor:scoreGauge', 1880],
  ]);
  assert.equal(pickExpandAnchorY(both, KEYS, 12), 408);

  // 6-2. 첫 키 미기록 → 다음 키로 폴백 (기존 동작 경로를 지우지 않는다).
  const onlyGauge = new Map<string, number>([['anchor:scoreGauge', 1880]]);
  assert.equal(pickExpandAnchorY(onlyGauge, KEYS, 12), 1868);

  // 6-3. 하나도 기록 안 됨 → null (호출측이 scrollToEnd / y:0 으로 폴백).
  assert.equal(pickExpandAnchorY(new Map<string, number>(), KEYS, 12), null);

  // 6-4. pad 가 y 보다 크면 0 으로 클램프 (음수 스크롤 금지).
  const top = new Map<string, number>([['anchor:summaryCard', 4]]);
  assert.equal(pickExpandAnchorY(top, KEYS, 12), 0);
});

// ── Test 7: IN-01 예상 부위 사진 카드 선택 (quick-260903-ftg) ──────────────────
// 09-03 실측: belle pdshape 60점 doc(unreliable=true)은 확정 카드 2장인데 종전
// 링크 1개는 |points| 최대 record 1건의 시트만 열어 두 번째가 도달 불가였다.
// 이 함수가 "확정 카드 전부, primary 먼저, 숨김·미매칭·중복 제외" 를 고정한다.
// 제네릭이라 record 내용(관절명·수치)에는 접근하지 않는다 — IN-01 락 유지.
type ZoomRec = { recordId: string; joint: string };
type ZoomCard = { key: string; imageUrl: string };
const ZOOM_RECS: ZoomRec[] = [
  { recordId: 'r0', joint: 'left_hip' },
  { recordId: 'r1', joint: 'left_elbow' },
  { recordId: 'r2', joint: 'left_knee' },
];
const zoomPerJoint = (r: ZoomRec): ZoomCard | null => ({
  key: `conf:${r.joint}`,
  imageUrl: `https://x/${r.joint}.png`,
});
const keyOf = (z: ZoomCard) => z.key;
const nobodyHidden = () => false;

test('Test 7-1 (primary 맨 앞): primaryIndex 가 records 순서와 무관하게 첫 엔트리, 나머지는 원 순서', () => {
  const out = selectEstimatedZoomEntries(ZOOM_RECS, zoomPerJoint, keyOf, nobodyHidden, 1);
  assert.deepEqual(
    out.map((e) => e.recordIndex),
    [1, 0, 2],
  );
  assert.equal(out[0].zoom.key, 'conf:left_elbow');
  assert.equal(out[0].zoom.imageUrl, 'https://x/left_elbow.png');
  // primary 없음(null) → 원 배열 순서 그대로, 전부 포함.
  const noPrimary = selectEstimatedZoomEntries(ZOOM_RECS, zoomPerJoint, keyOf, nobodyHidden, null);
  assert.deepEqual(
    noPrimary.map((e) => e.recordIndex),
    [0, 1, 2],
  );
  // 범위 밖 primary(폴백 경로 등) 는 무시 — 원 순서.
  const outOfRange = selectEstimatedZoomEntries(ZOOM_RECS, zoomPerJoint, keyOf, nobodyHidden, 9);
  assert.deepEqual(
    outOfRange.map((e) => e.recordIndex),
    [0, 1, 2],
  );
});

test('Test 7-2 (숨김 제외): 스팟체크 숨김 record 는 사진이 있어도 카드에서 빠진다 — primary 여도', () => {
  const hideR0 = (r: ZoomRec) => r.recordId === 'r0';
  const out = selectEstimatedZoomEntries(ZOOM_RECS, zoomPerJoint, keyOf, hideR0, null);
  assert.deepEqual(
    out.map((e) => e.recordIndex),
    [1, 2],
  );
  // primary 가 숨김이면 그것도 빠지고 다음 record 가 첫 엔트리.
  const primaryHidden = selectEstimatedZoomEntries(ZOOM_RECS, zoomPerJoint, keyOf, hideR0, 0);
  assert.deepEqual(
    primaryHidden.map((e) => e.recordIndex),
    [1, 2],
  );
});

test('Test 7-3 (같은 키 dedupe): 좌+우 묶음 카드가 두 record 에 매칭돼도 첫 등장만', () => {
  // r0(left_hip)·r1(right_hip) 이 같은 묶음 카드(conf:hip_pair)로 매칭, r2 는 별개.
  const pairRecs: ZoomRec[] = [
    { recordId: 'r0', joint: 'left_hip' },
    { recordId: 'r1', joint: 'right_hip' },
    { recordId: 'r2', joint: 'left_elbow' },
  ];
  const pairZoom = (r: ZoomRec): ZoomCard | null =>
    r.joint.endsWith('_hip')
      ? { key: 'conf:hip_pair', imageUrl: 'https://x/hip_pair.png' }
      : { key: `conf:${r.joint}`, imageUrl: `https://x/${r.joint}.png` };
  const out = selectEstimatedZoomEntries(pairRecs, pairZoom, keyOf, nobodyHidden, null);
  assert.deepEqual(
    out.map((e) => e.recordIndex),
    [0, 2],
  );
  assert.deepEqual(
    out.map((e) => e.zoom.key),
    ['conf:hip_pair', 'conf:left_elbow'],
  );
  // primary 가 r1 이면 묶음 카드는 r1 에 붙고 r0 은 dedupe — 카드 수는 그대로 2.
  const primaryR1 = selectEstimatedZoomEntries(pairRecs, pairZoom, keyOf, nobodyHidden, 1);
  assert.deepEqual(
    primaryR1.map((e) => e.recordIndex),
    [1, 2],
  );
});

test('Test 7-4 (빈 입력): 매칭 0 = 빈 배열, records null/undefined/빈 배열 = 빈 배열(matchZoom 미호출)', () => {
  const noMatch = selectEstimatedZoomEntries(ZOOM_RECS, () => null, keyOf, nobodyHidden, 0);
  assert.deepEqual(noMatch, []);

  let calls = 0;
  const counting = (r: ZoomRec): ZoomCard | null => {
    calls += 1;
    return zoomPerJoint(r);
  };
  assert.deepEqual(selectEstimatedZoomEntries(null, counting, keyOf, nobodyHidden, 0), []);
  assert.deepEqual(selectEstimatedZoomEntries(undefined, counting, keyOf, nobodyHidden, 0), []);
  assert.deepEqual(selectEstimatedZoomEntries([], counting, keyOf, nobodyHidden, 0), []);
  assert.equal(calls, 0);
});
