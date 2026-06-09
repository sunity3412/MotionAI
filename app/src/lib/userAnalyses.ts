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
import type { AnalysisDoc, AnalysisStatus } from '../types/analysis';

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
  return {
    analysisId: id,
    mode,
    status,
    fileName,
    createdAt,
    updatedAt,
    error: raw.error as AnalysisDoc['error'],
    result,
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
