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

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  deriveResultSections,
  buildRecordMaps,
  pickExpandAnchorY,
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
