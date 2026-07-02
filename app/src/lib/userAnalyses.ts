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
  CoachCommentHook,
  DeductionBreakdown,
  DeductionRecord,
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
          records: raw.records.filter(
            (r): r is DeductionRecord => r != null && typeof r === 'object',
          ),
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
