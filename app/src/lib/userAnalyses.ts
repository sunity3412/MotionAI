// 분석 기록 데이터 소스 레이어 (홈 탭 최근 분석 + 기록 탭 리스트).
//
// users/{uid}/analyses 컬렉션 onSnapshot 구독. 화면은 데이터 소스에 무지하도록 격리 —
// 나중에 GraphQL/REST 로 바꿔도 이 파일만 교체(referenceMotions.ts 와 동일 패턴).
//
// 익명 인증(게스트)도 정상 — 보안 규칙: users/{uid}/{**} 본인만 read/write.

import {
  collection,
  doc,
  onSnapshot,
  query,
  orderBy,
  type FirestoreError,
} from 'firebase/firestore';
import { onAuthStateChanged } from 'firebase/auth';
import { useEffect, useState } from 'react';
import { auth, db } from './firebase';
import { normalizeBodyProfile } from './bodyProfile';
import type {
  AnalysisDoc,
  AnalysisStatus,
  AttributionReliability,
  CoachAudio,
  CoachAudioItem,
  CoachCommentHook,
  CoachQuestion,
  DeductionBreakdown,
  DeductionRecord,
  Mission,
  MissionOutcome,
  SpotCheck,
  SpotCheckVerdict,
  SummaryPraise,
} from '../types/analysis';

// Phase 11 (Plan 11-02, COACH-01) — CoachCommentHook null-guard normalize.
// forcePatternInference / recommendedExercises null-guard precedent 의 1:1 mirror:
// 이전 빌드 doc 은 hook 자체가 없고(키 부재 시 caller 가 호출 자체 skip),
// hook 은 있으나 malformed 인 doc 은 graceful 보정한다 (T-11-03 DoS mitigate).
//   · autoFindingsSummary: 문자열 아니면 '' (UI 비노출 필드 — D-06)
//   · openQuestionsForCoach / suggestedCues: list[str] 만 통과 (string 외 항목 제거)
//   · coachComment / reviewedBy: v2 강사 입력 — string 아니면 null (D-06)
//   · sourceReport: provenance scalar — string 아니면 null
// 입력이 객체가 아니면 null 반환 (Firestore raw 방어).
function normalizeStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((v): v is string => typeof v === 'string');
}

function normalizeCoachHook(value: unknown): CoachCommentHook | null {
  if (value == null || typeof value !== 'object') return null;
  const hook = value as Record<string, unknown>;
  return {
    autoFindingsSummary:
      typeof hook.autoFindingsSummary === 'string'
        ? hook.autoFindingsSummary
        : '',
    openQuestionsForCoach: normalizeStringArray(hook.openQuestionsForCoach),
    suggestedCues: normalizeStringArray(hook.suggestedCues),
    coachComment:
      typeof hook.coachComment === 'string' ? hook.coachComment : null,
    reviewedBy: typeof hook.reviewedBy === 'string' ? hook.reviewedBy : null,
    sourceReport:
      typeof hook.sourceReport === 'string' ? hook.sourceReport : null,
  };
}

// Phase 31 (D-05/D-06/D-08) — visual 교정 시각물 필드 방어 파싱 헬퍼.
// backend 방출값을 신뢰하지 않는다 (T-31-12 Tampering): 임의 값은 undefined 로
// 조용히 강등하고, 필드를 drop 하지는 않는다 (부재 = legacy doc 하위호환).
const VISUAL_STATUSES = ['pending', 'done', 'failed'] as const;
type VisualStatus = (typeof VISUAL_STATUSES)[number];

function normalizeVisualStatus(value: unknown): VisualStatus | undefined {
  return VISUAL_STATUSES.includes(value as VisualStatus)
    ? (value as VisualStatus)
    : undefined;
}

// S3 key 방어: 결과물 key 는 반드시 `results/` prefix 다. 그 외(오염 데이터·타 prefix)
// 는 undefined 로 강등 — 앱이 임의 key 를 재서명 요청에 실어 보내는 경로를 원천 차단
// (리뷰 H-02: 재서명은 server-selected asset type 으로만).
function normalizeResultKey(value: unknown): string | undefined {
  return typeof value === 'string' && value.startsWith('results/')
    ? value
    : undefined;
}

// 전용 timestamp (리뷰 H-06) — 공용 updatedAt 이 아니라 이 값으로 pending 타임아웃을
// 판정하므로 유한 number 만 통과시킨다 (NaN/Infinity 는 비교 시 영구 pending 유발).
function normalizeFiniteMs(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value)
    ? value
    : undefined;
}

// 프레임 인덱스 — 배열 인덱스로 쓰이므로 음수/소수/NaN 전부 거부.
function normalizeFrameIdx(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0
    ? value
    : undefined;
}

// ── Phase 32 (Plan 32-06 — D-19/D-26/D-27/D-08/D-28) 방어 파싱 헬퍼 ──────
// backend 방출값을 신뢰하지 않는다 (T-32-14 DoS mitigate): 임의 값은 undefined
// 로 조용히 강등하고, 필드를 drop 하지는 않는다 (부재 = legacy doc 하위호환 —
// visual 필드 3종 헬퍼 관례). enum 은 models.py 상수와 lockstep
// (test_mission_contract_lockstep.py 가 drift 차단).
const MISSION_SELECTED_BY = ['safety', 'repeat', 'max_deduction'] as const;
const MISSION_ESCALATIONS = ['none', 'exercise_detour', 'coach_card'] as const;
const SUMMARY_PRAISE_SOURCES = [
  'mission_improved',
  'clean_dimension',
  'criteria_met',
] as const;
const COACH_QUESTION_SOURCES = [
  'safety',
  'mission_stuck',
  'unmeasured',
  'user', // 클라이언트 로컬 전용 — 백엔드 방출엔 없음 (contract.md §12.5)
] as const;

// 유한 number 만 (normalizeFiniteMs 와 동일 로직 — 이름이 timestamp 전용이라
// 범용 별칭을 둔다. tolerance/baseline 수치용).
function normalizeFiniteNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value)
    ? value
    : undefined;
}

function normalizeNonEmptyString(value: unknown): string | undefined {
  return typeof value === 'string' && value.length > 0 ? value : undefined;
}

function normalizeMission(value: unknown): Mission | undefined {
  if (value == null || typeof value !== 'object' || Array.isArray(value))
    return undefined;
  const m = value as Record<string, unknown>;
  const faultKey = normalizeNonEmptyString(m.faultKey);
  const criterion = normalizeNonEmptyString(m.criterion);
  const selectedBy = MISSION_SELECTED_BY.includes(
    m.selectedBy as Mission['selectedBy'],
  )
    ? (m.selectedBy as Mission['selectedBy'])
    : undefined;
  const escalation = MISSION_ESCALATIONS.includes(
    m.escalation as Mission['escalation'],
  )
    ? (m.escalation as Mission['escalation'])
    : undefined;
  const streak =
    typeof m.streak === 'number' && Number.isInteger(m.streak) && m.streak >= 1
      ? m.streak
      : undefined;
  const baselinePoints =
    typeof m.baselinePoints === 'number' &&
    Number.isFinite(m.baselinePoints) &&
    m.baselinePoints >= 0
      ? m.baselinePoints
      : undefined;
  // 필수 골격이 malformed 면 미션 전체를 undefined 강등 (섹션 숨김 — 잘못된
  // 미션을 표시하느니 조용히 감춘다, D-08 조용한 폴백 정합).
  if (
    !faultKey ||
    !criterion ||
    !selectedBy ||
    !escalation ||
    streak === undefined ||
    baselinePoints === undefined
  )
    return undefined;
  return {
    faultKey,
    criterion,
    selectedBy,
    streak,
    escalation,
    baselinePoints,
    isSafety: m.isSafety === true,
    ruleId: typeof m.ruleId === 'string' ? m.ruleId : null,
    recordId: typeof m.recordId === 'string' ? m.recordId : null,
    motionId: typeof m.motionId === 'string' ? m.motionId : null,
    baselineDeviation: normalizeFiniteNumber(m.baselineDeviation) ?? null,
    targetValue: normalizeFiniteNumber(m.targetValue) ?? null,
    unit: typeof m.unit === 'string' ? m.unit : null,
  };
}

function normalizeMissionOutcome(value: unknown): MissionOutcome | undefined {
  if (value == null || typeof value !== 'object' || Array.isArray(value))
    return undefined;
  const o = value as Record<string, unknown>;
  const faultKey = normalizeNonEmptyString(o.faultKey);
  const criterion = normalizeNonEmptyString(o.criterion);
  const baselinePoints = normalizeFiniteNumber(o.baselinePoints);
  const currentPoints = normalizeFiniteNumber(o.currentPoints);
  const deltaPoints = normalizeFiniteNumber(o.deltaPoints);
  if (
    typeof o.improved !== 'boolean' ||
    !faultKey ||
    !criterion ||
    baselinePoints === undefined ||
    currentPoints === undefined ||
    deltaPoints === undefined
  )
    return undefined;
  return {
    improved: o.improved,
    faultKey,
    criterion,
    baselinePoints,
    currentPoints,
    deltaPoints,
    baselineDeviation: normalizeFiniteNumber(o.baselineDeviation) ?? null,
    currentDeviation: normalizeFiniteNumber(o.currentDeviation) ?? null,
    deltaDeviation: normalizeFiniteNumber(o.deltaDeviation) ?? null,
  };
}

function normalizeSummaryPraise(value: unknown): SummaryPraise | undefined {
  if (value == null || typeof value !== 'object' || Array.isArray(value))
    return undefined;
  const p = value as Record<string, unknown>;
  const source = SUMMARY_PRAISE_SOURCES.includes(
    p.source as SummaryPraise['source'],
  )
    ? (p.source as SummaryPraise['source'])
    : undefined;
  const headline = normalizeNonEmptyString(p.headline);
  if (!source || !headline) return undefined;
  return {
    source,
    headline,
    evidenceValue: normalizeFiniteNumber(p.evidenceValue) ?? null,
    evidenceUnit: typeof p.evidenceUnit === 'string' ? p.evidenceUnit : null,
  };
}

function normalizeCoachQuestions(value: unknown): CoachQuestion[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const out: CoachQuestion[] = [];
  for (const item of value) {
    if (item == null || typeof item !== 'object' || Array.isArray(item))
      continue; // malformed 항목만 제거 — 나머지는 보존 (필드 drop 없음 원칙)
    const q = item as Record<string, unknown>;
    const text = normalizeNonEmptyString(q.text);
    const source = COACH_QUESTION_SOURCES.includes(
      q.source as CoachQuestion['source'],
    )
      ? (q.source as CoachQuestion['source'])
      : undefined;
    if (!text || !source) continue;
    out.push({
      text,
      source,
      ...(typeof q.recordId === 'string' ? { recordId: q.recordId } : {}),
    });
  }
  return out;
}

// Phase 32 (Plan 32-16 — D-18 B안) — coachAudio 방어 파싱. 백엔드 방출값을
// 신뢰하지 않는다: status 는 2값 화이트리스트, item 은 recordId 비어있지 않은
// string + key `results/` prefix(normalizeResultKey 재사용 — H-02, 앱이 임의
// key 를 재서명 요청에 실을 경로 원천 차단)일 때만 통과. malformed item 은
// 드롭, 형상 전체 malformed 는 undefined (부재=legacy doc 하위호환 —
// visual 필드 헬퍼 관례).
function normalizeCoachAudio(value: unknown): CoachAudio | undefined {
  if (value == null || typeof value !== 'object' || Array.isArray(value))
    return undefined;
  const a = value as Record<string, unknown>;
  const status =
    a.status === 'done' || a.status === 'failed' ? a.status : undefined;
  if (!status) return undefined;
  const rawItems = Array.isArray(a.items) ? a.items : [];
  const items: CoachAudioItem[] = [];
  for (const item of rawItems) {
    if (item == null || typeof item !== 'object' || Array.isArray(item))
      continue;
    const it = item as Record<string, unknown>;
    const recordId = normalizeNonEmptyString(it.recordId);
    const key = normalizeResultKey(it.key); // results/ prefix 강등 (H-02)
    if (!recordId || !key) continue; // malformed item 드롭 (방어)
    items.push({ recordId, key });
  }
  return { status, items };
}

// Phase 32 (Plan 32-13 — D-23) — spotCheck 방어 파싱. 백엔드 방출값을 신뢰하지
// 않는다: status 3값 화이트리스트, hiddenRecordIds 는 비어있지 않은 string 만,
// verdict 는 enum 만 통과 (malformed 항목 드롭). 형상 전체 malformed 는
// undefined = 부재(legacy) 와 동일한 전 카드 표시 fail-open (contract.md §12.8
// 표시 정책 — 오염된 숨김 목록이 카드를 잘못 감추는 것을 방어, T-32-30).
const SPOT_CHECK_STATUSES = ['done', 'skipped', 'failed'] as const;
const SPOT_CHECK_VERDICTS = ['match', 'mismatch', 'uncertain'] as const;

function normalizeSpotCheck(value: unknown): SpotCheck | undefined {
  if (value == null || typeof value !== 'object' || Array.isArray(value))
    return undefined;
  const s = value as Record<string, unknown>;
  const status = SPOT_CHECK_STATUSES.includes(s.status as SpotCheck['status'])
    ? (s.status as SpotCheck['status'])
    : undefined;
  if (!status) return undefined;
  const hiddenRecordIds = normalizeStringArray(s.hiddenRecordIds).filter(
    (id) => id.length > 0,
  );
  const verdicts: SpotCheckVerdict[] = [];
  if (Array.isArray(s.verdicts)) {
    for (const item of s.verdicts) {
      if (item == null || typeof item !== 'object' || Array.isArray(item))
        continue;
      const v = item as Record<string, unknown>;
      const recordId = normalizeNonEmptyString(v.recordId);
      const verdict = SPOT_CHECK_VERDICTS.includes(
        v.verdict as SpotCheckVerdict['verdict'],
      )
        ? (v.verdict as SpotCheckVerdict['verdict'])
        : undefined;
      if (!recordId || !verdict) continue; // malformed 항목만 드롭
      verdicts.push({
        recordId,
        verdict,
        ...(typeof v.reason === 'string' ? { reason: v.reason } : {}),
      });
    }
  }
  return {
    status,
    hiddenRecordIds,
    verdicts,
    praiseMismatch: s.praiseMismatch === true,
    ...(typeof s.model === 'string' ? { model: s.model } : {}),
    ...(typeof s.promptVersion === 'string'
      ? { promptVersion: s.promptVersion }
      : {}),
  };
}

// IN-01 (quick-260724-q6b) — attributionReliability 방어 파싱. 백엔드 방출값을
// 신뢰하지 않는다: 객체 아니거나 unreliable/geminiSilent 가 boolean 아니면 undefined
// (malformed doc 렌더 크래시 0 — normalizeSpotCheck 관례). visibility/dtwDistance 는
// 유한 number 아니면 null, overTolJointCount 는 유한 number 아니면 0, aggregateStatement
// 는 비어있지 않은 string 일 때만 보존.
// quick-260802-nfd — 백엔드가 **발화 여부와 무관하게** 마커를 싣는다(게이트 입력 상시
// 기록). 그래서 정상 doc 도 이제 `{unreliable:false, ...}` 를 들고 온다 — boolean 게이트를
// 통과해 그대로 보존되고, aggregateStatement 는 애초에 부재다. 렌더 diff 는 여전히 0:
// 화면 강등은 result.tsx 의 `?.unreliable === true` 엄격 비교 하나가 결정하며, 필드 존재로
// 분기하는 소비처는 없다. 부재(legacy doc / vision 컨텍스트 미산출)=undefined 도 그대로.
function normalizeAttributionReliability(
  value: unknown,
): AttributionReliability | undefined {
  if (value == null || typeof value !== 'object' || Array.isArray(value))
    return undefined;
  const a = value as Record<string, unknown>;
  if (typeof a.unreliable !== 'boolean' || typeof a.geminiSilent !== 'boolean')
    return undefined;
  const aggregateStatement = normalizeNonEmptyString(a.aggregateStatement);
  return {
    unreliable: a.unreliable,
    geminiSilent: a.geminiSilent,
    overTolJointCount: normalizeFiniteNumber(a.overTolJointCount) ?? 0,
    visibility: normalizeFiniteNumber(a.visibility) ?? null,
    dtwDistance: normalizeFiniteNumber(a.dtwDistance) ?? null,
    ...(aggregateStatement ? { aggregateStatement } : {}),
  };
}

// DeductionRecord 확장 키 통과 파싱 (Plan 32-06 §12.3) — recordId/3단 문구는
// string, tolerance 는 유한 number 만. malformed 는 undefined 강등하되 record
// 자체와 기존 필드는 보존 (카드는 계속 렌더 — 문구만 조용히 포기).
function normalizeRecordPhraseFields(rec: DeductionRecord): DeductionRecord {
  const raw = rec as unknown as Record<string, unknown>;
  return {
    ...rec,
    recordId: normalizeNonEmptyString(raw.recordId),
    statusLine: normalizeNonEmptyString(raw.statusLine),
    whyLine: normalizeNonEmptyString(raw.whyLine),
    cueLine: normalizeNonEmptyString(raw.cueLine),
    // quick-260814-rcz — 원인 가설 절. 빈 문자열/비문자열은 undefined 강등이라
    // 조립기(composeCueSubtitleKo)가 "없는 것처럼" 처리하는 fail-closed 와 같은
    // 결론에 도달한다 (한 곳에서 두 번 막는다).
    causeLine: normalizeNonEmptyString(raw.causeLine),
    coachQuestion: normalizeNonEmptyString(raw.coachQuestion),
    exerciseId: normalizeNonEmptyString(raw.exerciseId),
    exerciseReason: normalizeNonEmptyString(raw.exerciseReason),
    tolerance: normalizeFiniteNumber(raw.tolerance),
    // quick-260801-gbk — 측정 순간. atFrameIdx 는 프레임 배열 인덱스로 쓰이므로
    // 유한수만으로는 부족하다 (정수·비음수 게이트). 실패는 undefined 강등 —
    // 그 record 는 "잰 순간" 절만 잃고 나머지는 그대로 렌더된다.
    atFrameIdx: normalizeFrameIndex(raw.atFrameIdx),
    atVideoSec: normalizeFiniteNumber(raw.atVideoSec),
  };
}

/** 프레임 배열 인덱스 — 유한 정수 + 비음수만 통과. 그 외 undefined. */
function normalizeFrameIndex(value: unknown): number | undefined {
  const n = normalizeFiniteNumber(value);
  if (n === undefined || !Number.isInteger(n) || n < 0) return undefined;
  return n;
}

export interface UserAnalysesState {
  analyses: AnalysisDoc[]; // createdAt 내림차순
  loading: boolean;
  error: string | null;
}

function normalize(id: string, raw: Record<string, unknown>): AnalysisDoc | null {
  const mode = raw.mode === 'mode1' || raw.mode === 'mode3' ? raw.mode : null;
  const status = raw.status as AnalysisStatus | undefined;
  // fileName 은 빈 문자열일 수 있다(영상 파일명 미전달). 빈 문자열도 유효한
  // 문서이므로 null(필드 자체가 없거나 문자열 아님)일 때만 제외.
  const fileName = typeof raw.fileName === 'string' ? raw.fileName : null;
  const createdAt = typeof raw.createdAt === 'number' ? raw.createdAt : null;
  const updatedAt = typeof raw.updatedAt === 'number' ? raw.updatedAt : createdAt;
  if (
    !mode ||
    !status ||
    fileName === null ||
    createdAt == null ||
    updatedAt == null
  )
    return null;
  // Phase 6 (2026-06-08, Plan 06-02): AnalysisResult.bodyComparisonReport 는 TS
  // 타입 정합으로 자동 정상화 (defensive validation 없음 — backend validator
  // (_validate_flat_dict_no_nested_array, W5) 가 nested-array 차단 보장).
  // Plan 06-02 I2 positive assertion — literal "bodyComparisonReport" 표기.
  //
  // Phase 7 (2026-06-08, Plan 07-02 Task 3 WR-02 fix): old Firestore doc 호환성 —
  // bodyComparisonReport 의 신설 4+3 필드 (Plan 01 Task 3 lockstep) default 처리.
  // iteration 1 의 B1 fix (Plan 02 Task 3 삭제) retract — old doc 가 신설 필드 없어도 crash X.
  // TS interface 는 non-optional 유지 (production 데이터는 항상 보유, normalize() 가 compat layer).
  let result = raw.result as AnalysisDoc['result'] | undefined;
  if (result?.bodyComparisonReport) {
    const report = result.bodyComparisonReport;
    result = {
      ...result,
      bodyComparisonReport: {
        ...report,
        doNotOverCorrect: report.doNotOverCorrect ?? [],
        recommendedFocus: report.recommendedFocus ?? [],
        recommendedFocusFallback: report.recommendedFocusFallback ?? null,
        findings: (report.findings ?? []).map((f) => ({
          ...f,
          category: f.category ?? 'uncertain',
          phase: f.phase ?? 'hold',
        })),
        // Phase 11 (Plan 11-02, COACH-01) — coachCommentHook null-guard.
        // Wave 1 backend 가 두 리포트에 hook 을 부착하지만 이전 빌드 doc /
        // hook 미생성 분석은 필드 부재 → 키 부재 시 추가 안 함 (TS contract
        // `coachCommentHook?: CoachCommentHook | null` 가 undefined 허용).
        // malformed hook (필드 누락/타입 불일치) → normalizeCoachHook 가
        // graceful 보정 (T-11-03 DoS mitigate).
        ...('coachCommentHook' in report
          ? { coachCommentHook: normalizeCoachHook(report.coachCommentHook) }
          : {}),
      },
    };
  }
  // Phase 8 (2026-06-09, Plan 08-03) — forceSignalsReport null-guard.
  // Plan 08-01 박제 optional interface (TS interface: optional + nullable) 위 compat layer.
  // old Firestore doc (Phase 8 wiring 전) 박제 forceSignalsReport 없어도 crash X.
  // Phase 7 WR-02 B1 패턴 정합 — immutable spread + ?? null fallback.
  if (result?.forceSignalsReport) {
    const report = result.forceSignalsReport;
    result = {
      ...result,
      forceSignalsReport: {
        version: report.version ?? '1.0',
        overallConfidence: report.overallConfidence ?? 'low',
        warnings: report.warnings ?? [],
        phaseBoundaries: report.phaseBoundaries ?? [],
        axisMetrics: report.axisMetrics ?? [],
        stabilityMetrics: report.stabilityMetrics ?? [],
        contactMetrics: report.contactMetrics ?? [],
      },
    };
  }
  // Phase 9 §9.11 forcePatternInference null-guard (D-09-D1 / RESEARCH Pitfall 8 / R1).
  // Mirrors forceSignalsReport pattern at lines 74-88. forcePatternInference 는
  // result 내부 필드 — 이미 narrowing 된 result 변수를 사용해야 typecheck PASS
  // (R1 Codex iter-2: raw.result 는 unknown 이라 raw?.result?.forcePatternInference
  // 접근 시 tsc 실패).
  // 필드 자체가 missing 이면 undefined 유지 — TS contract
  // `forcePatternInference?: ForcePatternInference | null` 가 undefined 허용.
  if (result?.forcePatternInference) {
    const inference = result.forcePatternInference;
    result = {
      ...result,
      forcePatternInference: {
        ...inference,
        findings: (inference.findings ?? []).map((f) => ({
          ...f,
          warnings: f.warnings ?? [],
          jointHint: f.jointHint ?? null,
        })),
        warnings: inference.warnings ?? [],
        // Phase 11 (Plan 11-02, COACH-01) — coachCommentHook null-guard.
        // bodyComparisonReport 블록과 동일 패턴 (Wave 1 backend 가 두 리포트에
        // hook 부착). 키 부재 시 추가 안 함 → undefined 유지 (TS contract 허용).
        ...('coachCommentHook' in inference
          ? { coachCommentHook: normalizeCoachHook(inference.coachCommentHook) }
          : {}),
      },
    };
  }
  // Phase 13 (Plan 13-A, PERS-03) recommendedExercises null-guard.
  // forcePatternInference 패턴 mirror — backend validator
  // (_validate_recommended_exercises) 가 len<=5 + flat scalar 강제하므로
  // 여기선 list 여부만 확인. 부재/비-list 면 undefined 유지 (TS contract
  // recommendedExercises?: RecommendedExercise[] 가 undefined 허용).
  if (Array.isArray(result?.recommendedExercises)) {
    result = {
      ...result,
      recommendedExercises: result.recommendedExercises,
    };
  }
  // Phase 10 (10-02 SAFE-01) safetyFlags null-guard.
  // forcePatternInference / recommendedExercises 패턴 mirror — backend
  // (_validate_safety_flags) 가 scalar-only list[dict] 강제하므로 여기선 list 여부만
  // 확인. 부재/비-list 면 undefined 유지 (TS contract safetyFlags?: SafetyFlag[] | null
  // 가 undefined 허용). 구버전 doc(Phase 10 wiring 전) 박제 없어도 crash X.
  if (Array.isArray(result?.safetyFlags)) {
    result = {
      ...result,
      safetyFlags: result.safetyFlags,
    };
  }
  // Phase 24 §10 deductionBreakdown null-guard (quick-260702-q8q, T-q8q-01).
  // safetyFlags / recommendedExercises 패턴 mirror — backend validator
  // (_validate_deduction_breakdown) 가 flat scalar 를 강제하므로 깊은 검증은 하지
  // 않는다 (기존 관례). 객체 + records 배열이면 통과(records 각 항목은 객체만
  // 필터), malformed(비객체/records 비배열)면 undefined 로 두어 optional 유지 —
  // 구/malformed doc 에서 ScoreBreakdownSection 렌더 경로 크래시 0 (섹션 숨김).
  if (result?.deductionBreakdown !== undefined) {
    const bd: unknown = result.deductionBreakdown;
    const isValidShape =
      bd != null &&
      typeof bd === 'object' &&
      !Array.isArray(bd) &&
      Array.isArray((bd as { records?: unknown }).records);
    if (isValidShape) {
      const raw = bd as DeductionBreakdown;
      result = {
        ...result,
        deductionBreakdown: {
          ...raw,
          // Phase 32 (Plan 32-06 §12.3) — record 확장 키(recordId/3단 문구/
          // tolerance) 통과 파싱. 기존 필드·record 는 보존(필드 drop 없음).
          records: raw.records
            .filter(
              (r): r is DeductionRecord => r != null && typeof r === 'object',
            )
            .map(normalizeRecordPhraseFields),
        },
      };
    } else {
      result = { ...result, deductionBreakdown: undefined };
    }
  }
  // Phase 12 §9.12 keypointReport null-guard (D-12-E2 / Phase 9 D-09-U1 mirror).
  // Mirrors forcePatternInference pattern (lines 96-110). Wave 0B = schema only,
  // Wave 1 KeypointOverlay 가 본 필드 소비.
  // 필드 자체가 missing 이면 undefined 유지 — TS contract
  // `keypointReport?: KeypointReport | null` 가 undefined 허용.
  if (result?.keypointReport) {
    const kr = result.keypointReport;
    result = {
      ...result,
      keypointReport: {
        version: kr.version ?? '1.0',
        joints: kr.joints ?? [],
        frames: kr.frames ?? 0,
        fps: kr.fps ?? 9.0, // R3 — 운영 값. default 30 박제 금지.
        data: kr.data ?? [],
        confidence: kr.confidence ?? [],
        reliability: kr.reliability ?? [],
        axisData: kr.axisData ?? [], // R2 — 별도 polyline (finite only, R7 iter-2)
        axisMask: kr.axisMask ?? [], // R7 iter-2 — knee_mid 가용 여부 bool
        warnings: kr.warnings ?? [],
      },
    };
  }
  // Phase 4 (04-02 R3) — joints3d Firestore flat null-guard.
  // 04-01 신설 joints3d / joints3dKeys / joints3dFrames / coordDim / space 필드.
  // angles 는 이 compat block 에서 절대 읽지 않는다 — 관절각 스칼라이므로
  // 3D 좌표 소스 불가. result.tsx → reshapePose3dData 가 joints3d 만 read.
  //
  // BLOCKER-1 (4차 게이트 리뷰): AnalysisResult 의 joints3d 계열 필드는 nullable
  // 이 아니라 optional — 형식 불일치 시 null 대입 금지, undefined 로 두어 optional 유지.
  if (
    result?.joints3d !== undefined ||
    result?.joints3dKeys !== undefined ||
    result?.joints3dFrames !== undefined
  ) {
    result = {
      ...result,
      joints3d: Array.isArray(result.joints3d) ? result.joints3d : undefined,
      joints3dKeys: Array.isArray(result.joints3dKeys)
        ? result.joints3dKeys
        : undefined,
      joints3dFrames:
        typeof result.joints3dFrames === 'number'
          ? result.joints3dFrames
          : undefined,
      coordDim: result.coordDim === 3 ? 3 : undefined,
      space:
        result.space === 'rtmw3d' || result.space === 'pole_aligned'
          ? result.space
          : undefined,
    };
  }
  // Phase 4 (04-02 BLOCKER-3 / HIGH-2 / HIGH-5) — aiSynthesisMeta compat layer.
  //   · canonical warning surface = aiSynthesisMeta.warnings (top-level
  //     result.warnings 금지). AccuracyLimitBadge 는 hasSynthesisWarning(result)
  //     helper 로만 읽는다.
  //   · HIGH-2: Wave 1 pipeline 이 raw reason 을 public/debug 분류 매핑한
  //     debugWarnings 를 normalize 가 절대 드롭하면 안 된다 (운영/리뷰 근거).
  //   · HIGH-5: 감사/비용 필드 (modelId / modelVersion / promptHash / framesConsidered
  //     / framesSynthesized / geminiCalls / framesSkipped / framesFailed / estCostUsd)
  //     도 보존. UI 미사용이어도 debug/audit boundary 유지.
  //   · Firestore raw 방어: 타입 검증 후 통과만 보존, 실패 시 undefined.
  if (result?.aiSynthesisMeta) {
    const meta = result.aiSynthesisMeta;
    result = {
      ...result,
      aiSynthesisMeta: {
        synthesizedFrameCount: meta.synthesizedFrameCount ?? 0,
        synthesizedJointKeys: meta.synthesizedJointKeys ?? [],
        synthesisPath: meta.synthesisPath ?? 'none',
        degraded: meta.degraded ?? true,
        // BLOCKER-3 canonical warning surface (public enum 만).
        warnings: Array.isArray(meta.warnings) ? meta.warnings : [],
        // HIGH-2 raw debug warnings (UI 비노출, 운영 근거).
        debugWarnings: Array.isArray(meta.debugWarnings)
          ? meta.debugWarnings
          : [],
        // HIGH-5 감사 필드 (optional 보존).
        modelId: typeof meta.modelId === 'string' ? meta.modelId : undefined,
        modelVersion:
          typeof meta.modelVersion === 'string' ? meta.modelVersion : undefined,
        promptHash:
          typeof meta.promptHash === 'string' ? meta.promptHash : undefined,
        // HIGH-5 비용 카운터.
        framesConsidered:
          typeof meta.framesConsidered === 'number'
            ? meta.framesConsidered
            : undefined,
        framesSynthesized:
          typeof meta.framesSynthesized === 'number'
            ? meta.framesSynthesized
            : undefined,
        geminiCalls:
          typeof meta.geminiCalls === 'number' ? meta.geminiCalls : undefined,
        framesSkipped:
          typeof meta.framesSkipped === 'number'
            ? meta.framesSkipped
            : undefined,
        framesFailed:
          typeof meta.framesFailed === 'number'
            ? meta.framesFailed
            : undefined,
        estCostUsd:
          typeof meta.estCostUsd === 'number' ? meta.estCostUsd : undefined,
      },
    };
  }
  // Phase 31 (D-05/D-06/D-08) — correctedPose*/rotation* 방어 파싱 (T-31-12).
  // faultZoomStatus 사후 분리 패턴의 mirror. 세 규칙:
  //   · status 2종은 3값 화이트리스트만 통과 — 그 외(오타/신규 값/비문자열)는
  //     undefined → 카드 숨김. 알 수 없는 상태를 표시하느니 조용히 감춘다(D-08).
  //   · key 2종은 `results/` prefix 검증 — 오염 key 조용히 강등 (리뷰 H-02).
  //   · *UpdatedAtMs 는 유한 number 만 — pending 타임아웃 기준 (리뷰 H-06).
  // 필드 부재(legacy doc)면 전부 undefined 로 남아 기존 화면과 동일하게 동작한다.
  if (result) {
    const r = result as Record<string, unknown>;
    result = {
      ...result,
      correctedPoseStatus: normalizeVisualStatus(r.correctedPoseStatus),
      correctedPoseKey: normalizeResultKey(r.correctedPoseKey),
      correctedPoseJoint:
        typeof r.correctedPoseJoint === 'string'
          ? r.correctedPoseJoint
          : undefined,
      correctedPoseUpdatedAtMs: normalizeFiniteMs(r.correctedPoseUpdatedAtMs),
      rotationStatus: normalizeVisualStatus(r.rotationStatus),
      rotationVideoKey: normalizeResultKey(r.rotationVideoKey),
      rotationUpdatedAtMs: normalizeFiniteMs(r.rotationUpdatedAtMs),
    };
  }
  // Phase 31 (D-10) — FaultZoomComparison 의 뷰어 프레임 소스 방어 파싱.
  // 항목 자체는 보존하고(카드는 계속 렌더) 신규 3필드만 검증한다 — 잘못된 인덱스로
  // 뷰어가 크래시하느니 프레임 동기화만 조용히 포기(부재=legacy 와 동일 경로).
  if (Array.isArray(result?.faultZoomComparisons)) {
    result = {
      ...result,
      faultZoomComparisons: result.faultZoomComparisons.map((c) => {
        const raw = c as unknown as Record<string, unknown>;
        return {
          ...c,
          userFrameIdx: normalizeFrameIdx(raw.userFrameIdx),
          refFrameIdx: normalizeFrameIdx(raw.refFrameIdx),
          refMatched:
            typeof raw.refMatched === 'boolean' ? raw.refMatched : undefined,
          // quick-260801-gbk — 표시 프레임 == 측정 프레임 인증. **true 화이트리스트**:
          // 백엔드는 일치할 때만 true 를 넣고 그 외엔 키를 생략하므로, false 나
          // 비-boolean 은 전부 undefined 로 접는다 (fail-closed → basis 절 생략).
          atMatched: raw.atMatched === true ? true : undefined,
        };
      }),
    };
  }
  // Phase 32 (Plan 32-06 — D-19/D-26/D-27/D-08/D-28) — 미션 루프·잘한 점·코치
  // 질문 방어 파싱. 임의 값은 undefined 강등 + 필드 drop 없음 (부재=legacy doc
  // 하위호환 — visual 필드 블록 mirror). 방출은 32-09 부터라 현행 doc 은 전부
  // undefined 로 통과한다 (렌더 diff 0).
  if (result) {
    const r = result as Record<string, unknown>;
    result = {
      ...result,
      mission: normalizeMission(r.mission),
      missionOutcome: normalizeMissionOutcome(r.missionOutcome),
      summaryPraise: normalizeSummaryPraise(r.summaryPraise),
      coachQuestions: normalizeCoachQuestions(r.coachQuestions),
      // Phase 32 (Plan 32-16 — D-18) — 사후 도착 오디오 조인 목록 (부재=legacy).
      coachAudio: normalizeCoachAudio(r.coachAudio),
      // Phase 32 (Plan 32-13 — D-23) — 사후 도착 스팟체크 (부재=전 카드 표시).
      spotCheck: normalizeSpotCheck(r.spotCheck),
      // IN-01 (quick-260724-q6b) — 역립 저신뢰 per-joint 귀속 마커 (부재=정상 동작,
      // unreliable=false/부재 시 렌더 diff 0). 앱 표현 강등 전용, 점수 무접촉.
      attributionReliability: normalizeAttributionReliability(
        r.attributionReliability,
      ),
    };
  }
  return {
    analysisId: id,
    mode,
    status,
    fileName,
    createdAt,
    updatedAt,
    error: raw.error as AnalysisDoc['error'],
    result,
    // Phase 3 (Plan 03-01, R1) — 분석-당시 자가입력 SNAPSHOT 보존. 같은 단일
    // normalizer(bodyProfile.ts)로 graceful 정규화 → 결과 화면이
    // storedDoc?.bodyProfile 로 snapshot 을 읽음 (live 프로필 아님, 재현성).
    //
    // [IN-04] "키 없음(구 doc)" 과 "빈 프로필(신 doc, 의도적 null)" 을 구분한다.
    // normalize 가 all-empty → null 로 접으므로 둘 다 null 이 되면, 결과 화면의
    // `?? liveProfile` 폴백이 분석-당시 프로필이 없던 신 doc 에도 발동해 현재
    // live 프로필을 과거 결과에 잘못 표기한다(재현성 위반). bodyProfile 키가
    // raw 에 실제로 있을 때만 필드를 세팅(null 가능)하고, 키가 없으면 undefined
    // 로 둔다 → 결과 화면은 undefined(키 부재=구 doc)일 때만 live 로 폴백.
    ...('bodyProfile' in raw
      ? {
          bodyProfile: normalizeBodyProfile(
            raw.bodyProfile as Record<string, unknown> | undefined,
          ),
        }
      : {}),
    // [IN-03] Phase 26 (D-08/D-09) — 업로드 시점 학습활용 동의값. boolean 일 때만
    // 매핑(방어) — 필드 부재/타입 불일치면 키 생략해 undefined 유지 (angles 류처럼
    // 조용히 탈락시키지 않고 명시적으로 통과시킨다). 향후 동의 상태 표시 UI 가
    // AnalysisDoc.learningOptIn 을 읽을 때 정합. 계약 필드와 동일 명칭 (analysis.ts:619).
    ...(typeof raw.learningOptIn === 'boolean'
      ? { learningOptIn: raw.learningOptIn }
      : {}),
    // 29 리뷰 WR-01 — 재생바 결함 틱 초 환산 기준. visionVeto 의
    // sourceFrameIndices 는 9fps angles 배열 공간 인덱스인데 keypointReport.frames
    // 는 18fps 업샘플 저장이라 도메인이 다르다(틱이 절반 시각에 찍힘). top-level
    // anglesFrames(T, 9fps 공간)를 통과시켜 결과 화면이 tickFrameCount 로 쓴다
    // (learningOptIn 매핑 패턴 미러 — number 일 때만, 부재 시 undefined 유지).
    ...(typeof raw.anglesFrames === 'number'
      ? { anglesFrames: raw.anglesFrames }
      : {}),
  };
}

// 단일 분석 문서 구독 (결과 화면 등). analysisId 없으면 doc=null·loading=false.
export function useAnalysisDoc(analysisId: string | undefined): {
  doc: AnalysisDoc | null;
  loading: boolean;
} {
  const [docState, setDocState] = useState<AnalysisDoc | null>(null);
  const [loading, setLoading] = useState<boolean>(!!analysisId);
  const [uid, setUid] = useState<string | null>(auth.currentUser?.uid ?? null);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => setUid(u?.uid ?? null));
    return unsub;
  }, []);

  useEffect(() => {
    if (!uid || !analysisId) {
      setDocState(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    const ref = doc(db, 'users', uid, 'analyses', analysisId);
    const unsub = onSnapshot(
      ref,
      (snap) => {
        if (!snap.exists()) {
          setDocState(null);
        } else {
          const a = normalize(snap.id, snap.data() as Record<string, unknown>);
          setDocState(a);
        }
        setLoading(false);
      },
      (err: FirestoreError) => {
        if (__DEV__) console.warn('[useAnalysisDoc] error', err);
        setDocState(null);
        setLoading(false);
      },
    );
    return unsub;
  }, [uid, analysisId]);

  return { doc: docState, loading };
}

export function useMyAnalyses(opts?: { doneOnly?: boolean }): UserAnalysesState {
  const doneOnly = opts?.doneOnly ?? false;
  const [analyses, setAnalyses] = useState<AnalysisDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uid, setUid] = useState<string | null>(auth.currentUser?.uid ?? null);

  // 인트로에서 (tabs)로 진입 후엔 currentUser 보장되지만, 콜드스타트 race 대비.
  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => setUid(u?.uid ?? null));
    return unsub;
  }, []);

  useEffect(() => {
    if (!uid) {
      setAnalyses([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    const q = query(
      collection(db, 'users', uid, 'analyses'),
      orderBy('createdAt', 'desc'),
    );
    const unsub = onSnapshot(
      q,
      (snap) => {
        const list: AnalysisDoc[] = [];
        snap.forEach((d) => {
          const a = normalize(d.id, d.data() as Record<string, unknown>);
          if (a && (!doneOnly || a.status === 'done')) list.push(a);
        });
        setAnalyses(list);
        setLoading(false);
        setError(null);
      },
      (err: FirestoreError) => {
        if (__DEV__) console.warn('[userAnalyses] onSnapshot error', err);
        setLoading(false);
        setError('분석 기록을 불러오지 못했어요.');
      },
    );
    return unsub;
  }, [uid, doneOnly]);

  return { analyses, loading, error };
}
